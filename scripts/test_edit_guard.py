import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
import edit_guard  # noqa: E402
from edit_guard import decide, decideStop  # noqa: E402


def entry(aKind, aBlock):
    return {'type': aKind, 'message': {'content': [aBlock]}}


def tool(aName, **aInput):
    return entry('assistant', {'type': 'tool_use', 'name': aName, 'input': aInput})


def transcript(aFolder, *aTexts, aRouted=True, aState=None, aEntries=()):
    lines = [tool('Skill', skill='ai-native-sdlc:ai-native-sdlc')] if aRouted else []
    lines += [tool('Read', file_path=str(aState))] if aState else []
    for item in aEntries:
        # A copy, so an entry reused across transcripts gets its result each time.
        item = json.loads(json.dumps(item))
        lines.append(item)
        # A tool call without an id ran and succeeded; one with an id brings its own result, or none.
        for block in item.get('message', {}).get('content', []) if item.get('type') == 'assistant' else []:
            if block.get('type') == 'tool_use' and 'id' not in block:
                block['id'] = f'call{len(lines)}'
                lines.append(entry('user', {'type': 'tool_result', 'tool_use_id': block['id']}))
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

    def test_shell_write_detection(self):
        # Standard lane with no plan approval: a detected write outside .sdlc/ is denied, and nothing else is.
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as elsewhere:
            (Path(folder) / '.git').mkdir()
            path = transcript(folder, 'Lane: Standard')
            inside, outside = Path(folder).as_posix(), Path(elsewhere).as_posix()

            def denied(aCommand):
                return decide({'tool_name': 'Bash', 'tool_input': {'command': aCommand}, 'cwd': folder, 'transcript_path': path})

            allowed = [
                # Lifecycle files written through a shell variable.
                "d=.sdlc/changes/x && mkdir -p $d && cat > $d/spec.md <<'EOF'\n# Spec\nEOF\ncat > \"${d}/state.md\" <<'EOF'\nstatus: draft\nEOF",
                "cat <<'EOF' > .sdlc/changes/x/spec.md\n# Spec\nEOF",
                # Lifecycle files written after a cd into the change folder.
                "mkdir -p .sdlc/changes/x && cd .sdlc/changes/x && cat > intent.md <<'EOF'\n# Intent\nEOF\ncat > spec.md <<'EOF'\n# Spec\nEOF\nls",
                f'cd "{inside}/.sdlc/changes/x" && sed -i \'s/pytest/unittest/\' plan.md && grep -n unittest plan.md',
                f'cd {outside} && python -m pytest -q > run.log',
                # An absolute cd to the project root, other commands, then a relative cd into the change folder.
                f'cd "{inside}" && cd .sdlc/changes/x && cat > spec.md <<EOF\n# Spec\nEOF',
                f'cd "{inside}" && ls && cd .sdlc/changes/x && cat > spec.md <<EOF\n# Spec\nEOF',
                # A command substitution that changes no directory leaves the cd following alone.
                f'cd "{inside}" && mkdir -p .sdlc/changes/x && cd .sdlc/changes/x && D=$(date +%Y-%m-%d) &&\n'
                f'cat > spec.md <<\'EOF\'\n# Spec $D\nEOF\ncat > plan.md <<\'EOF\'\n# Plan\nEOF',
                f'cd {inside} && D=$(date +%F) && cd .sdlc/changes/x && cat > spec.md <<EOF\n# Spec\nEOF',
                "cd .sdlc/changes/x && D=$(date +%F); cat > spec.md <<EOF\n# Spec\nEOF",
                # Closing a change: every target is under .sdlc/.
                'git mv .sdlc/changes/x .sdlc/archive/x',
                'mkdir -p .sdlc/archive && mv .sdlc/changes/x .sdlc/archive/x',
                'Move-Item .sdlc/changes/x .sdlc/archive/x',
                'rm -rf ".sdlc/changes/x"',
                "sed -i 's/^status: .*/status: closed/' .sdlc/changes/x/state.md",
                # Operators and command names inside quoted arguments are not writes.
                "jq '.[] | select(.n > 3)' data.json",
                "grep -n 'rm -rf' scripts/*.sh",
                "awk '$3 > 10 {print $1}' data.txt",
                'node -e "console.log([1, 2].map(x => x + 1))"',
                'git log --grep "cp -r" --oneline',
                f'cd {inside} && git commit -q -m "fix: x\n\nCo-Authored-By: A <a@example.com>" && gh pr create --body "$(cat body.md)"',
                # A flag is not a command, and opening a file to read is not a write.
                'docker run --rm alpine true',
                "python -c \"print(open('analysis.json').read())\"",
                "python -c \"import os; print(open(os.path.join('data', 'analysis.json')).read())\"",
                # A log redirected outside the project is not a project write.
                f'python -m pytest -q > {outside}/run.log 2>&1',
                'python -m pytest -q > /tmp/run.log',
                'python -m pytest -q > nul',
                'python x.py 2>$null',
                # A PowerShell here-string may hold a bare apostrophe.
                "@'\nit's done\n'@ | Set-Content .sdlc/changes/x/notes.md",
                "python -c \"import subprocess; print(subprocess.run(['git', 'status'], capture_output=True).stdout)\"",
                # Script-write names inside quoted text are data; a shell word that runs a file does not open quotes.
                "grep -n 'WriteAllText' hooks/edit_guard.py",
                'git commit -m "fix: detect WriteAllLines"',
                'bash scripts/test.sh && git commit -m "fix: a -> b"',
                'git commit -m "fix: guard subprocess calls; mv logic to helper"',
                # PowerShell lifecycle writes with a value or type argument.
                "Set-Content -Path .sdlc/changes/x/state.md -Value 'lane: fast'",
                'New-Item -ItemType Directory -Force .sdlc/changes/x',
            ]
            blocked = [
                'echo x > src/app.py',
                # A redirect after the heredoc marker is still a redirect.
                "cat <<'EOF' > src/app.py\nx\nEOF",
                # An empty heredoc does not swallow the commands after it.
                "cat > /tmp/empty.txt <<'EOF'\nEOF\ncat > src/app.py <<'EOF'\nx\nEOF",
                "[IO.File]::WriteAllLines('src/app.py', $lines)",
                # Outside the project is not enough: a sibling clone is still project work. Only temp folders pass.
                'echo x > /srv/other/app.py',
                'cd /srv/other && echo x > src/app.py',
                # A cd moves relative targets; where it cannot be followed, they count as project files.
                'cd src && echo x > app.py',
                f'cd {inside} && echo x > app.py',
                "cd .sdlc/changes/x && cat > ../../../src/app.py <<'EOF'\nx\nEOF",
                '(cd .sdlc/changes/x && ls); echo x > app.py',
                'cd .sdlc/changes/x && cd - && echo x > app.py',
                'cd .sdlc/changes/x && cd "$UNSET" && echo x > app.py',
                f'echo x > {inside}/src/app.py',
                "d=src && cat > $d/app.py <<'EOF'\nx\nEOF",
                'echo x > $UNSET/app.py',
                'mv .sdlc/changes/x/plan.md plan.md',
                'mv src/app.py .sdlc/changes/x/app.py',
                'rm -rf .sdlc/../src',
                'echo x > .sdlc/../src/app.py',
                "bash -c 'echo x > src/app.py'",
                "python -c \"open('a.py', 'w').write('x')\"",
                "python -c \"open('a.bin', mode='r+b').write(b'x')\"",
                'find . -name "*.pyc" | xargs rm',
                # Quotes that do not pair, or that quote the command itself, hide nothing.
                "# Don't touch the tests\nrm -rf src\necho 'ok'",
                "@'\nit's done\n'@ | Set-Content src/app.py; Write-Host 'ok'",
                "echo don\\'t; rm -rf src; echo 'done'",
                '"rm" -rf src',
                "find . -name '*.py' -exec 'rm' '{}' ';'",
                "iex 'Set-Content src/a.py x'",
                "python -c \"import os; os.system('rm -rf src')\"",
                'echo "$(echo x > src/app.py)"',
                # A cd segment is still checked, a single & separates commands, and a cd inside a substitution does not count.
                'cd . > src/app.py',
                'cd src & echo x > app.py',
                'echo $(true; cd .sdlc/changes/x); echo x > app.py',
                # Option-attached operands, and variables used before they are assigned.
                'cp --target-directory=src .sdlc/changes/x/a.py',
                'Copy-Item .sdlc/changes/x/a.py -Destination:src/a.py',
                'echo x > ${d:-src}/app.py; d=.sdlc/changes/x',
                'echo x > $d/app.py; d=.sdlc/changes/x',
                f"$env:TEMP = '{inside}/src'; 'x' > $env:TEMP/a.py",
                # Script writes in other spellings.
                "python -c \"from pathlib import Path; Path('src/a.py').open('w').write('x')\"",
                '[io.file]::writealltext("src/a.py", $t)',
                "cat <<'END-OF' > src/a.py\nbody\nEND-OF\necho 'done'",
                # Odd input must deny, not crash.
                'echo x > \x005\x00',
                # A cd is followed only while every directory change is a plain one at the start of a segment and
                # nothing runs in a subshell or group; otherwise relative targets stay plain relative paths.
                "cd .sdlc/changes/x && (echo hi); cat > intent.md <<'EOF'\n# Intent\nEOF",
                'cd .sdlc && (cd .. && rm -rf src)',
                'cd .sdlc && { cd ..; rm -rf src; }',
                'cd .sdlc && bash -c "cd .. && rm -rf src"',
                'Push-Location src; Set-Location .sdlc; Pop-Location; Remove-Item a.py',
                'cd .sdlc && git -C .. rm src/a.py',
                # The same chain with a command substitution is still checked: the write lands outside .sdlc/, the
                # directory is outside the project, a cd runs in a subshell or substitution, or the path climbs out of .sdlc/.
                f'cd "{inside}" && ls && cd .sdlc/changes/x && D=$(date +%F) && cat > ../../../src/app.py <<EOF\nx\nEOF',
                f'cd "{inside}" && D=$(date +%F) && echo x > src/app.py',
                'cd /srv/other && ls && cd src && D=$(date +%F) && echo x > app.py',
                f'cd "{inside}" && (cd .sdlc/changes/x && ls); D=$(date +%F); echo x > app.py',
                f'cd "{inside}" && echo $(cd .sdlc/changes/x && pwd); D=$(date +%F); echo x > app.py',
                'cd .sdlc/changes/x && D=$(echo hi > ../../../src/a.py)',
                f'cd "{inside}" && D=$(date +%F) && cd .sdlc/../src && echo x > app.py',
                f'cd "{inside}" && D=$(date +%F) && echo x > .sdlc/../src/app.py',
                f'cd "{inside}" && ls && cd .sdlc/changes/x && cd ../../.. && echo x > app.py',
                # A backslash before a quote is not an escape in PowerShell or in bash single quotes.
                'Get-ChildItem "C:\\proj\\" ; Remove-Item -Recurse src ; Get-ChildItem "C:\\tmp\\"',
                "echo 'x\\' ; rm -rf src ; echo 'y\\'",
                # A comment-looking line inside a quoted string is not a comment.
                'echo "a\n# " > src/x.py',
                'gh pr create --title t --body "Summary\n## Notes" ; rm -rf src',
                # Only an assignment in command position counts, and a name assigned twice stays unresolved.
                'echo PWD=.sdlc; echo x > $PWD/src/a.py',
                'd=src; [ -f x ] || d=.sdlc; echo 1 > $d/a.py',
                'd=.sdlc; d+=/../src; echo x > $d/a.py',
                'd=.sdlc; declare d=src; echo x > $d/a.py',
                # A command word spelled with quotes or backslashes is still that word.
                'cd .sdlc && c""d .. && rm -rf src',
                'cd .sdlc && c\\d .. && rm -rf src',
                # Interpreters with a suffix or a runner.
                "python.exe -c \"open('src/a.py','w').write('x')\"",
                "python3.12 -c \"open('src/a.py','w').write('x')\"",
                "npx tsx -e \"require('fs').writeFileSync('src/a.ts','x')\"",
            ]
            if os.name == 'nt':
                # Git Bash spells a drive as /c/, WSL as /mnt/c/.
                drive, rest = outside.split(':', 1)
                allowed.append(f'echo x > /{drive.lower()}{rest}/run.log')
                drive, rest = inside.split(':', 1)
                blocked.append(f'echo x > /{drive.lower()}{rest}/src/app.py')
                blocked.append(f'echo x > /mnt/{drive.lower()}{rest}/src/app.py')
            for command in allowed:
                self.assertIsNone(denied(command), command)
            # The temp folder variables resolve from the environment.
            with mock.patch.dict(os.environ, {'TEMP': elsewhere}):
                self.assertIsNone(denied('python -m pytest -q > "$TEMP/run.log" 2>&1'))
            with mock.patch.dict(os.environ, {'TEMP': folder}):
                self.assertIsNotNone(denied('python -m pytest -q > "$TEMP/run.log" 2>&1'))
            for command in blocked:
                self.assertIsNotNone(denied(command), command)
            # The denial names what it detected.
            self.assertIn('src/app.py', denied('echo x > src/app.py'))
            self.assertIn('rm', denied('find . -name "*.pyc" | xargs rm'))
            # The project is found from a subfolder too, so a temp-folder project is not scratch.
            sub = Path(folder) / 'out' / 'sub'
            sub.mkdir(parents=True)
            event = {'tool_name': 'Bash', 'tool_input': {'command': f'echo x > {inside}/other.txt'}, 'cwd': str(sub), 'transcript_path': path}
            self.assertIsNotNone(decide(event))
            # An edit tool path that leaves .sdlc/ again is not a lifecycle file.
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / '.sdlc' / '..' / 'a.py')}, 'cwd': folder, 'transcript_path': path}
            self.assertIsNotNone(decide(edit))
            # Long input stays fast: an unterminated heredoc and a long token must not take seconds.
            started = time.perf_counter()
            self.assertIsNotNone(denied('cat <<A > x.py' + '\n' * 40000))
            self.assertIsNotNone(denied('echo ' + 'a' * 40000 + ' > x.py'))
            self.assertLess(time.perf_counter() - started, 2.0)

    def test_state_through_variable(self):
        # A state.md written through a shell variable still makes its change the active one.
        with tempfile.TemporaryDirectory() as folder:
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / 'a.py')}, 'cwd': folder}
            change(folder, 'y', 'lane: standard\napprovals:\n  - gate: plan\n')
            written = "d=.sdlc/changes/y; cat > $d/state.md <<'EOF'\nlane: standard\nEOF"
            path = transcript(folder, 'Lane: Standard', aEntries=(tool('Bash', command=written),))
            self.assertIsNone(decide({**edit, 'transcript_path': path}))
            # So does one written after a cd into the change folder, even when another change was read before.
            change(folder, 'z', 'lane: standard\napprovals: []\n')
            moved = "cd .sdlc/changes/y && cat > state.md <<'EOF'\nlane: standard\nEOF"
            path = transcript(folder, 'Lane: Standard', aEntries=(tool('Bash', command='cat .sdlc/changes/z/state.md'),
                                                                  tool('Bash', command=moved)))
            self.assertIsNone(decide({**edit, 'transcript_path': path}))

    def test_archived_change(self):
        # After a change is archived its state.md is gone; the denial says so instead of "none read or written".
        with tempfile.TemporaryDirectory() as folder:
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / 'a.py')}, 'cwd': folder}
            gone = Path(folder) / '.sdlc' / 'changes' / 'gone' / 'state.md'
            reason = decide({**edit, 'transcript_path': transcript(folder, 'Lane: Standard', aState=gone)})
            self.assertIn('.sdlc/changes/gone/state.md', reason)
            self.assertIn('not found', reason)

    def test_verified_claim(self):
        # Standard and Controlled work records status: verified only after this session invoked the verify skill on
        # the code that its last review saw. The hook logs skill calls with a fingerprint of the project files.
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as data, \
                mock.patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': data}):
            project, counter = Path(folder), iter(range(10 ** 6))

            def run(aSteps, aState='status: reviewing\nlane: standard\napprovals:\n  - gate: plan\n', aClaim=None, aRouter=True):
                """Play steps in a new session of a new change and return the decision on the claim.
                R, V: the review and verify skills. W: a code change. C: a claim that must pass and is then written.
                f: a claim that passes the hook but is never written. e: evidence added to the state file.
                B: the change is reopened. G: a commit.
                r, v: the same skills inside a sub-agent. t: verify typed as a command. b: a verify skill of
                another origin. O: a claim on another change that went through."""
                slug = f'c{next(counter)}'
                state = change(folder, slug, aState)
                session = {'session_id': slug, 'cwd': folder, 'transcript_path': transcript(folder, aState=state)}
                claim = aClaim(state) if aClaim else {'tool_name': 'Write', 'tool_input': {
                    'file_path': str(state), 'content': 'status: verified\nlane: standard\n'}}
                if aRouter:
                    edit_guard.main_event({**session, 'hook_event_name': 'PostToolUse', 'tool_name': 'Skill',
                                           'tool_input': {'skill': 'ai-native-sdlc:ai-native-sdlc'}, 'tool_response': {'success': True}})
                for step in aSteps:
                    if step in 'RVrv':
                        name = 'ai-native-sdlc:ai-native-' + ('review' if step in 'Rr' else 'verify')
                        edit_guard.main_event({**session, 'hook_event_name': 'PostToolUse', 'tool_name': 'Skill',
                                               'tool_input': {'skill': name}, 'tool_response': {'success': True},
                                               **({'agent_id': 'sub1'} if step in 'rv' else {})})
                    elif step == 't':
                        edit_guard.main_event({**session, 'hook_event_name': 'UserPromptExpansion',
                                               'command_name': 'ai-native-sdlc:ai-native-verify'})
                    elif step == 'b':
                        edit_guard.main_event({**session, 'hook_event_name': 'PostToolUse', 'tool_name': 'Skill',
                                               'tool_input': {'skill': 'ai-native-verify'}, 'tool_response': {'success': True}})
                    elif step == 'G':
                        for args in (('add', '-A'), ('commit', '-q', '-m', 'step')):
                            subprocess.run(['git', *args], cwd=folder, check=True, capture_output=True)
                    elif step == 'f':
                        self.assertIsNone(decide({**session, **claim}), aSteps)
                    elif step == 'x':
                        self.assertIsNone(decide({**session, **claim}), aSteps)
                        edit_guard.pending(session).write_text('{', encoding='utf-8')
                        self.assertIsNone(decide({**session, 'tool_name': 'Bash', 'tool_input': {'command': 'ls'}}))
                        self.assertFalse(edit_guard.pending(session).exists())
                    elif step == 'O':
                        edit_guard.record(session, claim=['another-change'], tree={})
                    elif step == 'W':
                        (project / 'a.py').write_text(f'x = {next(counter)}\n', encoding='utf-8')
                    elif step == 'C':
                        self.assertIsNone(decide({**session, **claim}), aSteps)
                        state.write_text('status: verified\nlane: standard\n', encoding='utf-8')
                    elif step == 'B':
                        reopened = aState.replace('reviewing', 'building')
                        self.assertIsNone(decide({**session, 'tool_name': 'Write', 'tool_input': {'file_path': str(state), 'content': reopened}}))
                        state.write_text(reopened, encoding='utf-8')
                    elif step == 'e':
                        state.write_text(aState + 'Evidence: python check.py exited 0\n', encoding='utf-8')
                return decide({**session, **claim}) or ''

            for git in (False, True):
                if git:
                    for args in (('init', '-q'), ('config', 'user.email', 'f@example.invalid'), ('config', 'user.name', 'F'),
                                 ('add', '-A'), ('commit', '-q', '-m', 'base')):
                        subprocess.run(['git', *args], cwd=folder, check=True, capture_output=True)
                # No verify: denied, and the reason names review first when code changed since the last review.
                self.assertIn('ai-native-verify skill first', run(''))
                self.assertIn('ai-native-verify skill first', run('R'))
                self.assertIn('ai-native-verify skill first', run('WR'))
                self.assertIn('ai-native-review', run('W'))
                self.assertIn('ai-native-review', run('RW'))
                # Verify on the code the review saw passes; a change between them needs a new review.
                for allowed in ('V', 'RV', 'WRV', 'RWRV', 'WRVW', 'RVW'):
                    self.assertEqual(run(allowed), '', allowed)
                for denied in ('WV', 'RWV', 'WRWV'):
                    self.assertIn('ai-native-review', run(denied), denied)
                # Once the review saw the current code, only verify is missing.
                self.assertIn('ai-native-verify skill again', run('RWVR'))
                self.assertNotIn('ai-native-review', run('RWVR'))
                self.assertEqual(run('RWVRV'), '')
                self.assertIn('ai-native-review', run('WVRW'))
                # A recorded claim uses up the verify before it: a reopened change needs review and verify again.
                self.assertIn('ai-native-review', run('WRVCBW'))
                self.assertIn('ai-native-review', run('WRVCBWV'))
                self.assertIn('ai-native-verify skill first', run('WRVCBWR'))
                self.assertEqual(run('WRVCBWRV'), '')
                # A claim that never landed (a refused or failed write) used nothing up, and neither did a claim on
                # another change.
                self.assertEqual(run('RVf'), '')
                self.assertEqual(run('RVfe'), '')
                self.assertEqual(run('RVO'), '')
                # The denial names the files that changed, so output that is not code can be ignored or removed.
                self.assertIn('a.py', run('RWV'))
                # A session whose record starts at verify has no reviewed code to compare with.
                self.assertIn('ai-native-review', run('V', aRouter=False))
                self.assertIn('ai-native-review', run('', aRouter=False))
                self.assertEqual(run('RV', aRouter=False), '')
                if git:
                    # A commit changes nothing about which code the review saw.
                    self.assertEqual(run('WRGV'), '')
                    self.assertEqual(run('WGRV'), '')
                    self.assertIn('ai-native-review', run('WRWGV'))
                    self.assertIn('ai-native-review', run('GRWGV'))
                # Skills that ran inside a sub-agent do not count, nor does a skill of that name from elsewhere; a
                # typed command does.
                self.assertIn('ai-native-verify skill first', run('Rb'))
                self.assertIn('ai-native-verify skill first', run('rv'))
                self.assertEqual(run('Rt'), '')
            # Files that Git ignores, and the lifecycle folder, are not code.
            (project / '.gitignore').write_text('*.log\n__pycache__/\n', encoding='utf-8')
            subprocess.run(['git', 'commit', '-q', '-a', '-m', 'ignore'], cwd=folder, capture_output=True)
            subprocess.run(['git', 'add', '.gitignore'], cwd=folder, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-q', '-m', 'ignore'], cwd=folder, check=True, capture_output=True)
            noise = run('R')
            (project / 'test.log').write_text('noise\n', encoding='utf-8')
            (project / '__pycache__').mkdir()
            (project / '__pycache__' / 'a.pyc').write_bytes(b'\0')
            (project / '.sdlc' / 'changes' / 'notes.md').write_text('n\n', encoding='utf-8')
            self.assertEqual(edit_guard.fingerprint(project), edit_guard.fingerprint(project))
            before = edit_guard.fingerprint(project)
            (project / 'test.log').write_text('more noise\n', encoding='utf-8')
            self.assertEqual(edit_guard.fingerprint(project), before)
            (project / 'new.py').write_text('y = 1\n', encoding='utf-8')
            self.assertNotEqual(edit_guard.fingerprint(project), before)
            self.assertTrue(noise)

            # An unknown fingerprint never denies, and neither does a record that cannot be written.
            with mock.patch.object(edit_guard, 'fingerprint', return_value=None):
                self.assertEqual(run('RWV'), '')
            # A project with no code yet is known, not unknown: its first code needs a review like any other.
            with tempfile.TemporaryDirectory() as empty:
                (Path(empty) / '.sdlc').mkdir()
                self.assertEqual(edit_guard.fingerprint(Path(empty)), {})
                self.assertEqual(edit_guard.changed({}, {'app.py': '1'}), ['app.py'])
                self.assertEqual(edit_guard.changed(None, {'app.py': '1'}), [])
            # A claim that landed is recorded before the skills that follow it, also when no write came between,
            # and a damaged note of a claim is dropped (checked inside the step).
            self.assertIn('ai-native-verify skill first', run('WRVCBR'))
            self.assertEqual(run('WRVCRVB'), '')
            # The claim behind a damaged note counts as made, so claiming again needs the skills again.
            self.assertIn('ai-native-verify skill first', run('RVx'))
            with mock.patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': str(project / 'a.py')}):
                self.assertEqual(run('W'), '')
            # A project in a subfolder of its repository: a changed tracked file is seen, and so is every file of a
            # large project, so a denial can always name what changed.
            with tempfile.TemporaryDirectory() as outer:
                inner = Path(outer) / 'apps' / 'web'
                (inner / '.sdlc').mkdir(parents=True)
                (inner / 'a.py').write_text('x = 1\n', encoding='utf-8')
                for args in (('init', '-q'), ('config', 'user.email', 'f@example.invalid'), ('config', 'user.name', 'F'),
                             ('add', '-A'), ('commit', '-q', '-m', 'base')):
                    subprocess.run(['git', *args], cwd=outer, check=True, capture_output=True)
                seen = edit_guard.fingerprint(inner)
                self.assertEqual(set(seen), {'a.py'})
                (inner / 'a.py').write_text('x = 2\n', encoding='utf-8')
                self.assertEqual(edit_guard.changed(seen, edit_guard.fingerprint(inner)), ['a.py'])
                for number in range(5200):
                    (inner / f'f{number}.txt').write_text('', encoding='utf-8')
                self.assertEqual(len(edit_guard.fingerprint(inner)), 5201)
            # Without Git, folders that hold no code are left out, also when the project root holds no file.
            with tempfile.TemporaryDirectory() as bare:
                for name in ('src/a.py', '.sdlc/changes/x/state.md', 'node_modules/m/index.js', 'build/out.js'):
                    (Path(bare) / name).parent.mkdir(parents=True, exist_ok=True)
                    (Path(bare) / name).write_text('x\n', encoding='utf-8')
                self.assertEqual(set(edit_guard.fingerprint(Path(bare))), {'src/a.py'})

            # What counts as the claim.
            def edit(aOld, aNew):
                return lambda aState: {'tool_name': 'Edit', 'tool_input': {'file_path': str(aState), 'old_string': aOld, 'new_string': aNew}}

            def shell(aCommand, aTool='Bash'):
                return lambda aState: {'tool_name': aTool, 'tool_input': {'command': aCommand.replace('SLUG', aState.parent.name)}}

            def write(aContent):
                return lambda aState: {'tool_name': 'Write', 'tool_input': {'file_path': str(aState), 'content': aContent}}
            sed = "sed -i 's/status: reviewing/status: verified/' .sdlc/changes/SLUG/state.md"
            for claim in (edit('status: reviewing', 'status: verified'), edit('reviewing', 'verified'), shell(sed),
                          shell("cat > .sdlc/changes/SLUG/state.md <<'EOF'\nstatus: verified\nlane: standard\nEOF")):
                self.assertIn('ai-native-verify', run('', aClaim=claim))
                self.assertEqual(run('RV', aClaim=claim), '')
            # Reading the state file, another status, and prose that mentions the status are not claims.
            for claim in (shell('grep -n "status: verified" .sdlc/changes/SLUG/state.md'),
                          shell('grep -c "status: verified" .sdlc/changes/SLUG/state.md > /dev/null'),
                          shell("sed -i 's/status: reviewing/status: blocked/' .sdlc/changes/SLUG/state.md"),
                          write('status: blocked\n'),
                          write('status: building\nnext_action: verify, then status: verified\nEvidence: was status: verified on Monday\n')):
                self.assertEqual(run('', aClaim=claim), '')
            # A change that is already verified on disk can be rewritten or closed without a new verify, as ship
            # does in a later session.
            done = 'status: verified\nlane: standard\nnext_action: deliver\napprovals:\n  - gate: plan\n'
            close = "sed -i 's/^status: verified/status: closed/' .sdlc/changes/SLUG/state.md"
            for claim in (write('status: verified\nlane: standard\nnext_action: open PR\n'),
                          edit('status: verified\nlane: standard\nnext_action: deliver', 'status: verified\nlane: standard\nnext_action: open PR'),
                          shell(close), shell(close + ' && git mv .sdlc/changes/SLUG .sdlc/archive/SLUG'),
                          shell("cd .sdlc/changes/SLUG && sed -i 's/^status: verified/status: closed/' state.md"),
                          shell("(Get-Content .sdlc/changes/SLUG/state.md) -replace 'status: verified','status: closed' | Set-Content .sdlc/changes/SLUG/state.md", 'PowerShell')):
                self.assertEqual(run('', aState=done, aClaim=claim), '')
            # Fast work and an undeclared lane are not checked, and an undeclared lane does not wait for late text.
            self.assertEqual(run('', aState='lane: fast\n'), '')
            started = time.monotonic()
            self.assertEqual(run('', aState='status: reviewing\n'), '')
            self.assertLess(time.monotonic() - started, 1)
            # The approvals gate still comes first for a write outside .sdlc/.
            outside = lambda aState: {'tool_name': 'Edit', 'tool_input': {'file_path': str(project / 'a.py')}}
            self.assertIn('plan', run('', aState='lane: standard\n', aClaim=outside))

    def test_scratch_files(self):
        # A throwaway file is not project code: the system temp folder and files that Git ignores are open before
        # the plan is approved, in every way of writing, so probes need no place under .sdlc/.
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as scratch:
            project, temp = Path(folder), Path(scratch).as_posix()
            path = transcript(folder, 'Lane: Standard', aState=change(folder, 'x', 'lane: standard\n'))
            decided = lambda aTool, **aInput: decide({'tool_name': aTool, 'tool_input': aInput, 'cwd': folder, 'transcript_path': path})
            for git in (False, True):
                self.assertIsNone(decided('Write', file_path=f'{temp}/probe.ts', content='x'))
                self.assertIsNone(decided('Edit', file_path=f'{temp}/probe.ts', old_string='x', new_string='y'))
                for command in (f'cp a.py {temp}/b.py', f'sed -i s/a/b/ {temp}/b.py', f'rm {temp}/b.py', f'cd {temp} && cp b.py c.py',
                                f'cp scripts/balance.ts {temp}/_hm.ts', 'cp a.py .sdlc/changes/x/probe.py',
                                f'Copy-Item a.py -Destination {temp}/b.py', f'cp -rt {temp} src'):
                    self.assertIsNone(decided('Bash', command=command), command)
                for command in (f'mv a.py {temp}/b.py', f'cp {temp}/b.py a.py', 'cp a.py b.py', f'cp {temp}/b.py .',
                                f'cp -T {temp}/b.py a.py', f'cp -t . {temp}/b.py', f'cp -at . {temp}/b.py'):
                    self.assertIn('plan', decided('Bash', command=command), command)
                reason = decided('Write', file_path=str(project / 'src.py'), content='x')
                self.assertIn('plan', reason)
                self.assertIn('temp folder', reason)
                self.assertEqual(decided('Write', file_path=str(project / 'scratch' / 'p.py'), content='x') is None, git)
                if not git:
                    (project / '.gitignore').write_text('scratch/\n', encoding='utf-8')
                    subprocess.run(['git', 'init', '-q'], cwd=folder, check=True, capture_output=True)

        # A repository further up that ignores the whole project says nothing about the project's own files.
        with tempfile.TemporaryDirectory() as outer:
            (Path(outer) / '.gitignore').write_text('/*\n', encoding='utf-8')
            subprocess.run(['git', 'init', '-q'], cwd=outer, check=True, capture_output=True)
            inner = Path(outer) / 'project'
            path = transcript(outer, 'Lane: Standard', aState=change(inner, 'x', 'lane: standard\n'))
            self.assertIn('plan', decide({'tool_name': 'Write', 'tool_input': {'file_path': str(inner / 'app.py'), 'content': 'x'},
                                          'cwd': str(inner), 'transcript_path': path}))

    def test_hook_registration(self):
        # The hook handles exactly the events it is registered for, each with a time limit: without one a slow
        # hook holds the tool call for the host default of ten minutes.
        root = Path(__file__).resolve().parents[1]
        registered = json.loads((root / '.claude-plugin' / 'hooks.json').read_text(encoding='utf-8'))['hooks']
        self.assertEqual(set(registered), {'PreToolUse', 'PostToolUse', 'UserPromptExpansion', 'Stop'})
        self.assertEqual(registered['PostToolUse'][0]['matcher'], 'Skill')
        for event, entries in registered.items():
            for handler in (h for e in entries for h in e['hooks']):
                self.assertEqual(handler['command'], 'python "${CLAUDE_PLUGIN_ROOT}/hooks/edit_guard.py"', event)
                self.assertLessEqual(handler['timeout'], 60, event)
        self.assertTrue((root / 'hooks' / 'edit_guard.py').is_file())
        # An event the hook is not registered for, or does not know, is handled as a write check and blocks nothing.
        self.assertIsNone(edit_guard.main_event({'hook_event_name': 'SessionStart'}))

    def test_guard_failure(self):
        def run(aInput, aBroken=None):
            out, err = io.StringIO(), io.StringIO()
            patches = [mock.patch('sys.stdin', io.StringIO(aInput)), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err)]
            patches += [mock.patch.object(edit_guard, aBroken, side_effect=RuntimeError('boom'))] if aBroken else []
            with contextlib.ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                try:
                    edit_guard.main()
                    code = 0
                except SystemExit as stop:
                    # sys.exit(text) prints the text to stderr and exits 1.
                    err.write(stop.code)
                    code = 1
            return code, out.getvalue(), err.getvalue()

        with tempfile.TemporaryDirectory() as folder:
            state = change(folder, 'x', 'lane: standard\nstatus: building\n')
            routed = transcript(folder, 'Lane: Standard', aState=state)
            edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(Path(folder) / 'a.py')}, 'cwd': folder}
            # The hook as Claude Code runs it: a gated write in a plugin session is denied.
            code, out, _ = run(json.dumps({**edit, 'transcript_path': routed}))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)['hookSpecificOutput']['permissionDecision'], 'deny')
            # A crash once the session is known to use the plugin denies the write and names the failure.
            code, out, _ = run(json.dumps({**edit, 'transcript_path': routed}), 'approvedGates')
            self.assertEqual(code, 0)
            decision = json.loads(out)['hookSpecificOutput']
            self.assertEqual(decision['permissionDecision'], 'deny')
            self.assertIn('guard failed', decision['permissionDecisionReason'])
            self.assertIn('RuntimeError: boom', decision['permissionDecisionReason'])
            # Before that, a crash blocks nothing but says the guard is inactive: unreadable input, or a failure
            # while reading the transcript or the command. A transcript line the hook cannot parse stays in the
            # transcript, so denying on it would deny every later write of the session, Fast lane included.
            later = transcript(folder, 'Lane: Fast', aEntries=[tool('Bash', command='ls')])
            bad = Path(transcript(folder, 'Lane: Fast'))
            bad.write_text(bad.read_text(encoding='utf-8') + '\n[1]', encoding='utf-8')
            for raw, broken in (('notjson', None), ('[]', None),
                                (json.dumps({**edit, 'transcript_path': later}), 'expandVars'),
                                (json.dumps({**edit, 'transcript_path': str(bad)}), None),
                                (json.dumps({**edit, 'transcript_path': routed}), 'readSession'),
                                (json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'rm a.py'},
                                             'transcript_path': routed, 'cwd': folder}), 'shellWritesOutsideSdlc')):
                code, out, err = run(raw, broken)
                self.assertEqual((code, out), (1, ''), raw[:40])
                self.assertIn('guard is inactive', err)
            # A missing transcript is not a crash: nothing shows the session uses the plugin.
            self.assertEqual(run(json.dumps({**edit, 'transcript_path': str(Path(folder) / 'none.jsonl')})), (0, '', ''))
            # A crash at the end of a turn never blocks the stop, so the agent can always hand back.
            code, out, err = run(json.dumps({'hook_event_name': 'Stop', 'transcript_path': routed, 'cwd': folder}), 'readState')
            self.assertEqual((code, out), (1, ''))
            self.assertIn('guard is inactive', err)


if __name__ == '__main__':
    unittest.main()
