import json
import os
import sys
import tempfile
import threading
import time
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


if __name__ == '__main__':
    unittest.main()
