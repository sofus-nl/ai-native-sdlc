"""Regression checks for the fixture checker, not a substitute for agent runs."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from behavior_check import BASE, CASES, CURRENT, PAYMENTS, check


class BehaviorCheckTest(unittest.TestCase):
    def test_accepts_expected_files_and_rejects_regressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, files in CASES.items():
                (root / name).mkdir()
                for filename, content in files.items():
                    (root / name / filename).write_text(content, encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(check(root))
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
                gates.write_text(''.join(f'  - gate: {g}\n    at: 2026-09-29T06:22:53Z\n'
                                         for g in ('intent', 'design', 'plan', 'checkpoint')),
                                 encoding='utf-8')
                self.assertFalse(check(root))
                # payment-build must record every Controlled approval gate.
                previous = gates.read_text(encoding='utf-8')
                gates.write_text(previous.replace('gate: design', 'gate: review'), encoding='utf-8')
                self.assertTrue(check(root))
                gates.write_text(previous.replace('2026-09-29T06:22:53Z', '2026-09-29', 1), encoding='utf-8')
                self.assertTrue(check(root))
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
                                       ('qualification', 'EVIDENCE.md'), ('cost-retry', 'RUNS.md')):
                    path = root / name / filename
                    previous = path.read_text(encoding='utf-8') if path.exists() else None
                    path.write_text('unexpected edit\n', encoding='utf-8')
                    self.assertTrue(check(root), name)
                    if previous is None:
                        path.unlink()
                    else:
                        path.write_text(previous, encoding='utf-8')
                for name, filename, regression in (
                    ('shared', 'settings.py', CASES['shared']['settings.py']),
                    ('payment-build', 'payments.py', PAYMENTS),
                    ('stale', 'labels.py', CURRENT),
                    ('stale', 'labels.py', BASE + '\ndef labels(names):\n    return [label(name) for name in names]\n'),
                ):
                    path = root / name / filename
                    previous = path.read_text(encoding='utf-8')
                    path.write_text(regression, encoding='utf-8')
                    self.assertTrue(check(root), (name, regression))
                    path.write_text(previous, encoding='utf-8')
                self.assertFalse(check(root))
                # Binary output must be reported as a failure, not crash the checker.
                binary = root / 'done' / 'out.bin'
                binary.write_bytes(b'\xff\xfe')
                self.assertTrue(check(root))
                binary.unlink()


if __name__ == '__main__':
    unittest.main()
