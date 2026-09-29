import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from edit_guard import decide, decideStop  # noqa: E402


def transcript(aFolder, *aTexts, aRouted=True):
    lines = [{'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Skill',
                                                              'input': {'skill': 'ai-native-sdlc:ai-native-sdlc'}}]}}] if aRouted else []
    lines += [{'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': t}]}} for t in aTexts]
    path = Path(aFolder) / 't.jsonl'
    path.write_text('\n'.join(json.dumps(l) for l in lines), encoding='utf-8')
    return str(path)


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
            self.assertIsNone(decide({**edit, 'transcript_path': transcript(folder, 'Lane: Fast.')}))
            path = transcript(folder, '**Lane:** Controlled, because this is a payment API.')
            self.assertIsNotNone(decide({**edit, 'transcript_path': path}))
            self.assertIsNotNone(decide({**heredoc, 'transcript_path': path}))
            state = Path(folder) / '.sdlc' / 'changes' / 'x' / 'state.md'
            state.parent.mkdir(parents=True)
            state.write_text('lane: controlled\napprovals:\n  - gate: intent\n', encoding='utf-8')
            self.assertIsNotNone(decide({**edit, 'transcript_path': transcript(folder)}))
            # Writing lifecycle and code files in one command is not a lifecycle-only write.
            mixed = {'tool_name': 'Bash', 'cwd': folder, 'tool_input': {'command':
                     "cat > .sdlc/changes/x/state.md <<'EOF'\nx > y\nEOF\npython - <<'EOF'\nopen('payments.py','w')\nEOF"}}
            lifecycle = {'tool_name': 'Bash', 'cwd': folder, 'tool_input': {'command':
                         "cat > .sdlc/changes/x/spec.md <<'EOF'\na >= b, touch base\nEOF"}}
            self.assertIsNotNone(decide({**mixed, 'transcript_path': transcript(folder)}))
            self.assertIsNone(decide({**lifecycle, 'transcript_path': transcript(folder)}))
            # Controlled needs intent, design, and plan approvals; plan alone is not enough.
            state.write_text('lane: controlled\napprovals:\n  - {gate: plan, at: 2026-09-29T06:22:53Z}\n', encoding='utf-8')
            self.assertIsNotNone(decide({**heredoc, 'transcript_path': transcript(folder)}))
            state.write_text('lane: controlled\napprovals:\n' + ''.join(f'  - gate: {g}\n' for g in ('intent', 'design', 'plan')),
                             encoding='utf-8')
            self.assertIsNone(decide({**heredoc, 'transcript_path': transcript(folder)}))
            # Stop: a Controlled change may not end mid-build or mid-review, except after one nudge.
            stop = {'hook_event_name': 'Stop', 'cwd': folder}
            for status, blocked in (('reviewing', True), ('building', True), ('blocked', False), ('verified', False)):
                state.write_text(f'status: {status}\nlane: controlled\n', encoding='utf-8')
                self.assertEqual(decideStop(stop) is not None, blocked, status)
            state.write_text('status: reviewing\nlane: controlled\n', encoding='utf-8')
            self.assertIsNone(decideStop({**stop, 'stop_hook_active': True}))
            state.write_text('status: reviewing\nlane: fast\n', encoding='utf-8')
            self.assertIsNone(decideStop(stop))


if __name__ == '__main__':
    unittest.main()
