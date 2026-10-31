import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from edit_guard import decide, decideStop  # noqa: E402


def entry(aKind, aBlock):
    return {'type': aKind, 'message': {'content': [aBlock]}}


def tool(aName, **aInput):
    return entry('assistant', {'type': 'tool_use', 'name': aName, 'input': aInput})


def transcript(aFolder, *aTexts, aRouted=True, aState=None, aEntries=()):
    lines = [tool('Skill', skill='ai-native-sdlc:ai-native-sdlc')] if aRouted else []
    lines += [tool('Read', file_path=str(aState))] if aState else []
    lines += list(aEntries)
    lines += [entry('assistant', {'type': 'text', 'text': t}) for t in aTexts]
    handle, path = tempfile.mkstemp(suffix='.jsonl', dir=aFolder)
    os.close(handle)
    Path(path).write_text('\n'.join(json.dumps(l) for l in lines), encoding='utf-8')
    return path


def change(aFolder, aSlug, aState):
    path = Path(aFolder) / '.sdlc' / 'changes' / aSlug / 'state.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(aState.encode('utf-8'))
    return path


APPROVED = 'approvals:\n' + ''.join(f'  - gate: {g}\n' for g in ('intent', 'design', 'plan'))


class EditGuardTest(unittest.TestCase):
    def test_decisions(self):
        with tempfile.TemporaryDirectory() as folder:
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / 'payments.py')}, 'cwd': folder}
            heredoc = {'tool_name': 'Bash', 'tool_input': {'command': "cat > payments.py <<'EOF'\nx\nEOF"}, 'cwd': folder}
            read = {'tool_name': 'Bash', 'tool_input': {'command': 'python -m pytest -q 2>&1 > /dev/null; ls'}, 'cwd': folder}
            sdlc = {'tool_name': 'Write', 'tool_input': {'file_path': str(Path(folder) / '.sdlc' / 'changes' / 'x' / 'spec.md')}, 'cwd': folder}
            # Outside an ai-native-sdlc session nothing is blocked.
            self.assertIsNone(decide({**edit, 'transcript_path': transcript(folder, aRouted=False)}))
            # Undeclared lane blocks writes but not reads or lifecycle files.
            path = transcript(folder)
            self.assertIsNotNone(decide({**edit, 'transcript_path': path}))
            self.assertIsNone(decide({**read, 'transcript_path': path}))
            self.assertIsNone(decide({**sdlc, 'transcript_path': path}))
            # Fast is allowed; Controlled is blocked, including shell writes, until a plan approval exists.
            for said in ('Lane: Fast.', 'Fast lane.', 'The lane is Fast.', 'Lane for this: Fast'):
                self.assertIsNone(decide({**edit, 'transcript_path': transcript(folder, said)}), said)
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder, 'Going Fast.')}))
            # Brief mode states the lane through SendUserMessage instead of a text block.
            brief = transcript(folder, aEntries=(tool('SendUserMessage', message='Lane: Fast.'),))
            self.assertIsNone(decide({**edit, 'transcript_path': brief}))
            # The statement in the same message as the call can reach the transcript after the hook starts.
            late = Path(transcript(folder))
            line = '\n' + json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'Lane: Fast.'}]}})
            timer = threading.Timer(0.3, lambda: late.write_text(late.read_text(encoding='utf-8') + line, encoding='utf-8'))
            timer.start()
            self.assertIsNone(decide({**edit, 'transcript_path': str(late)}))
            timer.join()
            path = transcript(folder, '**Lane:** Controlled, because this is a payment API.')
            self.assertIsNotNone(decide({**edit, 'transcript_path': path}))
            self.assertIsNotNone(decide({**heredoc, 'transcript_path': path}))
            state = change(folder, 'x', 'lane: controlled\napprovals:\n  - gate: intent\n')
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder, aState=state)}))
            # Writing lifecycle and code files in one command is not a lifecycle-only write.
            mixed = {'tool_name': 'Bash', 'cwd': folder, 'tool_input': {'command':
                     "cat > .sdlc/changes/x/state.md <<'EOF'\nx > y\nEOF\npython - <<'EOF'\nopen('payments.py','w')\nEOF"}}
            lifecycle = {'tool_name': 'Bash', 'cwd': folder, 'tool_input': {'command':
                         "cat > .sdlc/changes/x/spec.md <<'EOF'\na >= b, touch base\nEOF"}}
            self.assertIsNotNone(decide({**mixed, 'transcript_path': transcript(folder, aState=state)}))
            self.assertIsNone(decide({**lifecycle, 'transcript_path': transcript(folder, aState=state)}))
            # Controlled needs intent, design, and plan approvals; plan alone is not enough.
            state.write_text('lane: controlled\napprovals:\n  - {gate: plan, at: 2026-09-29T06:22:53Z}\n', encoding='utf-8')
            self.assertIsNotNone(decide({**heredoc, 'transcript_path': transcript(folder, aState=state)}))
            state.write_text('lane: controlled\n' + APPROVED, encoding='utf-8')
            self.assertIsNone(decide({**heredoc, 'transcript_path': transcript(folder, aState=state)}))
            # Stop: a Controlled change may not end mid-build or mid-review, except after one nudge.
            stop = {'hook_event_name': 'Stop', 'cwd': folder, 'transcript_path': transcript(folder, aState=state)}
            for status, blocked in (('reviewing', True), ('building', True), ('blocked', False), ('verified', False)):
                state.write_text(f'status: {status}\nlane: controlled\n', encoding='utf-8')
                self.assertEqual(decideStop(stop) is not None, blocked, status)
            state.write_text('status: reviewing\nlane: controlled\n', encoding='utf-8')
            self.assertIsNone(decideStop({**stop, 'stop_hook_active': True}))
            state.write_text('status: reviewing\nlane: fast\n', encoding='utf-8')
            self.assertIsNone(decideStop(stop))

    def test_routing(self):
        # Only a real invocation routes: the installed-skill listing, quoted file contents, and other skills do not.
        with tempfile.TemporaryDirectory() as folder:
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / 'a.py')}, 'cwd': folder}
            listing = {'type': 'attachment', 'attachment': {'type': 'skill_listing',
                                                            'content': '- ai-native-sdlc:ai-native-build: Implement'}}
            quoted = entry('user', {'type': 'tool_result', 'tool_use_id': 't',
                                    'content': '<command-name>/ai-native-sdlc:ai-native-sdlc</command-name>'})
            other = tool('Skill', skill='superpowers:brainstorming')
            path = transcript(folder, 'Lane: Standard', aRouted=False, aEntries=(listing, quoted, other))
            self.assertIsNone(decide({**edit, 'transcript_path': path}))
            slash = {'type': 'user', 'message': {'content': '<command-name>/ai-native-sdlc:ai-native-sdlc</command-name>'}}
            path = transcript(folder, 'Lane: Standard', aRouted=False, aEntries=(slash,))
            self.assertIsNotNone(decide({**edit, 'transcript_path': path}))

    def test_active_change(self):
        # Only the change this session read or wrote counts; other change folders are ignored.
        with tempfile.TemporaryDirectory() as folder:
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / 'a.py')}, 'cwd': folder}
            change(folder, 'old', 'status: released\nlane: standard\n' + APPROVED)
            change(folder, 'stale', 'status: verified\nlane: standard\ncurrent_gate: verify\n')
            new = change(folder, 'new', 'status: draft\nlane: controlled\napprovals: []\n')
            pending = change(folder, 'pending', 'status: planned\nlane: standard\ncurrent_gate: plan\napprovals: []\n')
            # An unrelated change's approvals do not unlock the active one.
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Controlled', aState=new)}))
            # A change this session never touched does not set the lane: Fast work passes.
            self.assertIsNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Fast')}))
            # current_gate and rejected decisions are not approvals.
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Standard', aState=pending)}))
            pending.write_text('lane: standard\napprovals:\n  - gate: plan\n    decision: rejected\n', encoding='utf-8')
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Standard', aState=pending)}))
            pending.write_text('lane: standard\napprovals:\n  - gate: plan\n    decision: accepted\n', encoding='utf-8')
            self.assertIsNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Standard', aState=pending)}))
            # The stricter of the stated and the recorded lane applies, so restating a lower lane clears nothing.
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Controlled', aState=pending)}))
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Fast', aState=new)}))
            # The state.md written last is active; reading another change's state.md for context does not switch.
            path = transcript(folder, 'Lane: Standard', aEntries=(tool('Write', file_path=str(pending), content='x'),
                                                                  tool('Bash', command='grep -n lane .sdlc/changes/new/state.md')))
            self.assertIsNone(decide({**edit, 'transcript_path': path}))
            # A write elsewhere in the command, or "CP" in a grep pattern, does not make a read a write.
            path = transcript(folder, 'Lane: Standard', aEntries=(tool('Write', file_path=str(new), content='x'), tool(
                'Bash', command='grep -n "CP 3" .sdlc/changes/pending/state.md; rm -f out.log')))
            self.assertIsNotNone(decide({**edit, 'transcript_path': path}))
            # A shell write counts as a write, so a later heredoc to another change's state.md switches to it.
            for heredoc in ("cat > .sdlc/changes/new/state.md <<'EOF'\nstatus: draft\nEOF",
                            "cd x && python - <<'EOF'\np = '.sdlc/changes/new/state.md'\nopen(p, 'w').write('x')\nEOF"):
                path = transcript(folder, 'Lane: Standard', aEntries=(tool('Write', file_path=str(pending), content='x'),
                                                                      tool('Bash', command=heredoc)))
                self.assertIsNotNone(decide({**edit, 'transcript_path': path}), heredoc)
            # With no write, the state.md read last is active, from a relative or an absolute shell path.
            path = transcript(folder, 'Lane: Standard', aEntries=(tool('Bash', command='cat .sdlc/changes/pending/state.md'),))
            self.assertIsNone(decide({**edit, 'transcript_path': path}))
            path = transcript(folder, 'Lane: Standard', aEntries=(tool('Bash', command=f'type "{pending}"'),))
            with tempfile.TemporaryDirectory() as elsewhere:
                self.assertIsNone(decide({**edit, 'cwd': elsewhere, 'transcript_path': path}))

    def test_approvals(self):
        # Only entries of the approvals list count: not current_gate, notes below the list, or rejected entries.
        with tempfile.TemporaryDirectory() as folder:
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / 'a.py')}, 'cwd': folder}
            for text, allowed in (
                    ('lane: standard\napprovals: []\ncurrent_gate: plan\n', False),
                    ('lane: standard\napprovals: []\n\n- 2026-10-30: asked at the gate: plan; no answer yet\n', False),
                    ('lane: standard\napprovals:\n  - gate: plan\n    evidence:\n      - rev 2\n    decision: rejected\n', False),
                    ('lane: standard\napprovals:\n  - gate: intent\n    evidence: "gate: plan comes later"\n', False),
                    ('Lane: Standard\r\nApprovals:\r\n  - gate: plan (spec.md at 9e036fa)\r\n    by: Sam\r\n', True),
                    ('lane: standard\napprovals:\n- gate: plan\n  decision: accepted\n\nNotes: none.\n', True)):
                change(folder, 'x', text)
                path = transcript(folder, 'Lane: Standard', aState=Path(folder) / '.sdlc' / 'changes' / 'x' / 'state.md')
                self.assertEqual(decide({**edit, 'transcript_path': path}) is None, allowed, text)

    def test_project_root(self):
        # The state file is found from a subdirectory cwd and from CLAUDE_PROJECT_DIR, not only from the root.
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as elsewhere:
            change(folder, 'x', 'lane: standard\napprovals:\n  - gate: plan\n')
            sub = Path(folder) / 'out' / 'sub'
            sub.mkdir(parents=True)
            bash = {'tool_name': 'Bash', 'tool_input': {'command': 'echo x > a.txt'}}
            path = transcript(folder, 'Lane: Standard', aEntries=(tool('Bash', command='cat .sdlc/changes/x/state.md'),))
            self.assertIsNone(decide({**bash, 'cwd': str(sub), 'transcript_path': path}))
            with mock.patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': folder}):
                self.assertIsNone(decide({**bash, 'cwd': elsewhere, 'transcript_path': path}))
            with mock.patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': elsewhere}):
                self.assertIsNotNone(decide({**bash, 'cwd': elsewhere, 'transcript_path': path}))

    def test_stop_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            state = change(folder, 'x', 'Status: Building\nLane: Standard\n')
            change(folder, 'stale', 'status: building\nlane: standard\n')
            stop = {'hook_event_name': 'Stop', 'cwd': folder, 'transcript_path': transcript(folder, aState=state)}
            # Keys and values match case-insensitively.
            self.assertIsNotNone(decideStop(stop))
            self.assertIsNotNone(decideStop({**stop, 'background_tasks': []}))
            # A turn that ends while background work runs is paused, not finished.
            running = [{'id': 'b1', 'type': 'subagent', 'status': 'running', 'description': 'builder'}]
            self.assertIsNone(decideStop({**stop, 'background_tasks': running}))
            # No nudge outside a plugin session, or for a change this session never touched.
            self.assertIsNone(decideStop({**stop, 'transcript_path': transcript(folder, aRouted=False, aState=state)}))
            self.assertIsNone(decideStop({**stop, 'transcript_path': transcript(folder)}))


if __name__ == '__main__':
    unittest.main()
