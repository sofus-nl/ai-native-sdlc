"""Regression checks for the fixture checker, not a substitute for agent runs."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from behavior_check import BASE, CASES, check


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
                for name in ('feature', 'payment'):
                    artifacts = root / name / '.sdlc' / 'changes' / 'sample'
                    artifacts.mkdir(parents=True)
                    for filename in ('intent.md', 'spec.md', 'plan.md', 'state.md'):
                        (artifacts / filename).write_text('Fixture only\n', encoding='utf-8')
                self.assertFalse(check(root))
                # Each regression must independently fail an otherwise green tree.
                for name, filename in (('typo', 'extra.md'), ('failure', 'labels.py'),
                                       ('done', 'labels.py'), ('payment', 'payments.py'),
                                       ('feature', 'labels.py')):
                    path = root / name / filename
                    previous = path.read_text(encoding='utf-8') if path.exists() else None
                    path.write_text('unexpected edit\n', encoding='utf-8')
                    self.assertTrue(check(root), name)
                    if previous is None:
                        path.unlink()
                    else:
                        path.write_text(previous, encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
