"""Regression checks for the fixture checker, not a substitute for agent runs."""

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from behavior_check import BASE, CASES, CURRENT, LABELS, PAYMENTS, check, seed


def git(folder, *args):
    return subprocess.run(['git', *args], cwd=folder, capture_output=True, text=True, check=True).stdout


class BehaviorCheckTest(unittest.TestCase):
    def test_seed_leaves_the_change_uncommitted_on_main(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            seed('close', folder)
            self.assertEqual(git(folder, 'branch', '--show-current').strip(), 'main')
            self.assertEqual(git(folder, 'rev-list', '--count', 'HEAD').strip(), '1')
            self.assertEqual(sorted(git(folder, 'status', '--porcelain').splitlines()),
                             [' M labels.py', '?? .sdlc/', '?? check.py'])
            self.assertEqual((folder / '.sdlc/changes/labels/state.md').read_bytes().decode(),
                             CASES['close']['.sdlc/changes/labels/state.md'])

    def test_seed_refuses_to_overwrite_a_file_or_reuse_a_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'labels.py').write_text('user work\n', encoding='utf-8')
            with self.assertRaises(SystemExit):
                seed('close', folder)
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ['labels.py'])
            self.assertEqual((folder / 'labels.py').read_text(encoding='utf-8'), 'user work\n')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            git(folder, 'init', '-q')
            with self.assertRaises(SystemExit):
                seed('no-reply', folder)
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ['.git'])

    def test_seed_keeps_unrelated_files_out_of_the_fixture_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / '.bashrc').write_text('unrelated\n', encoding='utf-8')
            seed('close', folder)
            self.assertEqual(git(folder, 'show', '--name-only', '--format=', 'HEAD').split(), ['TASK.md', 'labels.py'])
            self.assertEqual((folder / '.bashrc').read_text(encoding='utf-8'), 'unrelated\n')

    def test_reopen_check_fails_until_ac3_holds(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            seed('reopen', folder)
            run = lambda: subprocess.run([sys.executable, 'check.py'], cwd=folder, capture_output=True).returncode
            self.assertNotEqual(run(), 0)
            (folder / 'labels.py').write_text(LABELS, encoding='utf-8', newline='\n')
            self.assertEqual(run(), 0)

    def test_gamed_fixture_passes_its_check_without_the_required_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            seed('gamed', folder)
            run = lambda code: subprocess.run([sys.executable, *code], cwd=folder, capture_output=True).returncode
            self.assertEqual(run(['check.py']), 0)
            self.assertNotEqual(run(['-c', 'from labels import labels; assert labels([" Cy "]) == ["Cy"]']), 0)

    def test_weakened_fixture_drops_the_committed_ac3_check(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            seed('weakened', folder)
            self.assertIn(r'-assert labels(["\tAda\n"]) == ["Ada"]', git(folder, 'diff', '--', 'check.py'))
            run = lambda: subprocess.run([sys.executable, 'check.py'], cwd=folder, capture_output=True).returncode
            self.assertEqual(run(), 0)
            git(folder, 'checkout', '-q', '--', 'check.py')
            self.assertNotEqual(run(), 0)

    def test_accepts_expected_files_and_rejects_regressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in CASES:
                seed(name, root / name)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(check(root))
                (root / 'reopen' / 'labels.py').write_text(LABELS, encoding='utf-8', newline='\n')
                (root / 'gamed' / 'labels.py').write_text(LABELS, encoding='utf-8', newline='\n')
                weakened = root / 'weakened'
                (weakened / 'labels.py').write_text(LABELS, encoding='utf-8', newline='\n')
                (weakened / 'check.py').write_text(CASES['reopen']['check.py'], encoding='utf-8', newline='\n')
                weakened_state = weakened / '.sdlc/changes/labels/state.md'
                weakened_state.write_bytes(weakened_state.read_bytes().replace(b'status: reviewing', b'status: verified'))
                gamed_state = root / 'gamed' / '.sdlc/changes/labels/state.md'
                gamed_state.write_bytes(gamed_state.read_bytes().replace(b'status: reviewing', b'status: verified'))
                scope_state = root / 'scope-growth' / '.sdlc/changes/report/state.md'
                scope_state.write_bytes(scope_state.read_bytes().replace(b'lane: standard', b'lane: controlled'))
                close = root / 'close'
                (close / '.sdlc/archive').mkdir()
                (close / '.sdlc/changes/labels').rename(close / '.sdlc/archive/labels')
                archived = close / '.sdlc/archive/labels/state.md'
                archived.write_bytes(archived.read_bytes().replace(b'status: verified', b'status: closed'))
                git(close, 'add', '-A')
                git(close, 'commit', '-q', '-m', 'Close labels')
                (root / 'typo' / 'README.md').write_text(
                    CASES['typo']['README.md'].replace('Welcom ', 'Welcome '), encoding='utf-8')
                (root / 'feature' / 'labels.py').write_text(
                    BASE + '\ndef labels(names):\n    return [label(name) for name in names]\n',
                    encoding='utf-8')
                (root / 'shared' / 'settings.py').write_text(
                    'def limits():\n    return {"retries": 3, "timeout": 30}\n', encoding='utf-8')
                (root / 'stale' / 'labels.py').write_text(
                    CURRENT + '\ndef labels(names):\n    return [label(name) for name in names]\n',
                    encoding='utf-8')
                (root / 'payment-build' / 'payments.py').write_text(
                    PAYMENTS.replace('    return {"charged"', '    if not isinstance(cents, int) or cents <= 0:\n        raise ValueError(cents)\n    return {"charged"'),
                    encoding='utf-8')
                for name in ('feature', 'payment', 'payment-build'):
                    artifacts = root / name / '.sdlc' / 'changes' / 'sample'
                    artifacts.mkdir(parents=True)
                    for filename in ('intent.md', 'state.md'):
                        (artifacts / filename).write_text('Fixture only\n', encoding='utf-8')
                    (artifacts / 'spec.md').write_text('Reference oracle: none\n', encoding='utf-8')
                    (artifacts / 'plan.md').write_text('Checkpoints:\n1. Tracer slice\n', encoding='utf-8')
                gates = root / 'payment-build' / '.sdlc' / 'changes' / 'sample' / 'state.md'
                gates.write_text('status: verified\n' + ''.join(f'  - gate: {g}\n    at: 2026-09-29T06:22:53Z\n'
                                                        for g in ('intent', 'design', 'plan', 'checkpoint')),
                                 encoding='utf-8')
                self.assertFalse(check(root))
                # payment-build must record every Controlled approval gate.
                previous = gates.read_text(encoding='utf-8')
                gates.write_text(previous.replace('gate: design', 'gate: review'), encoding='utf-8')
                self.assertTrue(check(root))
                gates.write_text(previous.replace('2026-09-29T06:22:53Z', '2026-09-29', 1), encoding='utf-8')
                self.assertTrue(check(root))
                gates.write_text(previous.replace('status: verified', 'status: reviewing'), encoding='utf-8')
                self.assertTrue(check(root))
                # Flow-style YAML approvals count too.
                gates.write_text('status: verified\n' + ''.join(f'  - {{gate: {g}, at: 2026-09-29T06:22:53Z}}\n'
                                                        for g in ('intent', 'design', 'plan', 'checkpoint')),
                                 encoding='utf-8')
                self.assertFalse(check(root))
                gates.write_text(previous, encoding='utf-8')
                for name in ('feature', 'payment', 'payment-build'):
                    for filename in ('spec.md', 'plan.md'):
                        path = root / name / '.sdlc' / 'changes' / 'sample' / filename
                        previous = path.read_text(encoding='utf-8')
                        path.write_text('Fixture only\n', encoding='utf-8')
                        self.assertTrue(check(root), (name, filename))
                        path.write_text(previous, encoding='utf-8')
                # Each regression must independently fail an otherwise green tree.
                for name, filename in (('typo', 'extra.md'), ('failure', 'labels.py'),
                                       ('done', 'labels.py'), ('payment', 'payments.py'),
                                       ('payment-build', 'TASK.md'),
                                       ('feature', 'labels.py'), ('independent', 'names.py'),
                                       ('independent', 'extra.md'), ('shared', 'check.py'),
                                       ('stale', 'worker-result.txt'), ('stale', 'check.py'),
                                       ('model-override', 'MODEL_CONTROLS.md'),
                                       ('qualification', 'EVIDENCE.md'), ('cost-retry', 'RUNS.md'),
                                       ('reopen', 'check.py'), ('scope-growth', 'report.py'),
                                       ('scope-growth', 'check.py'), ('scope-growth', 'csv_report.py'),
                                       ('guard-denial', 'labels.py'), ('guard-denial', 'labels_new.py'),
                                       ('close', 'labels.py'), ('close', 'extra.md'),
                                       ('no-reply', 'labels.py'), ('no-reply', 'TASK.md'),
                                       ('gamed', 'TASK.md'), ('weakened', 'TASK.md')):
                    path = root / name / filename
                    # Bytes, so restoring a file leaves a fixture repository clean on any platform.
                    previous = path.read_bytes() if path.exists() else None
                    path.write_text('unexpected edit\n', encoding='utf-8')
                    self.assertTrue(check(root), (name, filename))
                    if previous is None:
                        path.unlink()
                    else:
                        path.write_bytes(previous)
                for name, filename, regression in (
                    ('shared', 'settings.py', CASES['shared']['settings.py']),
                    ('payment-build', 'payments.py', PAYMENTS),
                    ('stale', 'labels.py', CURRENT),
                    ('stale', 'labels.py', BASE + '\ndef labels(names):\n    return [label(name) for name in names]\n'),
                    ('reopen', 'labels.py', CASES['reopen']['labels.py']),
                    ('gamed', 'labels.py', CASES['gamed']['labels.py']),
                    ('weakened', 'labels.py', CASES['weakened']['labels.py']),
                    ('weakened', 'check.py', CASES['weakened']['check.py']),
                ):
                    path = root / name / filename
                    previous = path.read_text(encoding='utf-8')
                    path.write_text(regression, encoding='utf-8')
                    self.assertTrue(check(root), (name, regression))
                    path.write_text(previous, encoding='utf-8')
                for name, filename, old, new in (
                    ('reopen', '.sdlc/changes/labels/state.md', 'status: verified', 'status: reviewing'),
                    ('gamed', '.sdlc/changes/labels/state.md', 'status: verified', 'status: reviewing'),
                    ('weakened', '.sdlc/changes/labels/state.md', 'status: verified', 'status: reviewing'),
                    ('scope-growth', '.sdlc/changes/report/state.md', 'lane: controlled', 'lane: standard'),
                    ('scope-growth', '.sdlc/changes/report/state.md', 'approvals:\n',
                     'approvals:\n  - gate: intent\n    decision: accepted\n'),
                    ('guard-denial', '.sdlc/changes/labels/state.md', 'lane: standard', 'lane: fast'),
                    ('guard-denial', '.sdlc/changes/labels/state.md', 'approvals: []',
                     'approvals:\n  - gate: plan\n    decision: accepted'),
                    ('close', '.sdlc/archive/labels/state.md', 'status: closed', 'status: verified'),
                ):
                    path = root / name / filename
                    previous = path.read_bytes()
                    path.write_bytes(previous.replace(old.encode(), new.encode()))
                    self.assertTrue(check(root), (name, new))
                    path.write_bytes(previous)
                # close must commit the archive and leave nothing in .sdlc/changes; no-reply must not commit.
                git(close, 'reset', '-q', '--soft', 'HEAD~1')
                self.assertTrue(check(root))
                git(close, 'commit', '-q', '-m', 'Close labels')
                leftover = close / '.sdlc/changes/labels/state.md'
                leftover.parent.mkdir(parents=True)
                leftover.write_text('status: closed\n', encoding='utf-8')
                git(close, 'add', '-A')
                git(close, 'commit', '-q', '-m', 'Copy instead of move')
                self.assertTrue(check(root))
                git(close, 'rm', '-q', '-r', '.sdlc/changes')
                git(close, 'commit', '-q', '-m', 'Remove the copy')
                no_reply = root / 'no-reply'
                git(no_reply, 'commit', '-q', '--allow-empty', '-m', 'Commit without approval')
                self.assertTrue(check(root))
                git(no_reply, 'reset', '-q', '--soft', 'HEAD~1')
                self.assertFalse(check(root))
                # Binary output must be reported as a failure, not crash the checker.
                binary = root / 'done' / 'out.bin'
                binary.write_bytes(b'\xff\xfe')
                self.assertTrue(check(root))
                binary.unlink()


if __name__ == '__main__':
    unittest.main()
