"""Checks on the skill files that both hosts load (stdlib only)."""

import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / 'skills'


class SkillFilesTest(unittest.TestCase):
    def test_skill_fits_after_compaction(self):
        # After compaction Claude Code re-attaches an invoked skill cut at 20,000 characters, so the rules below the
        # cut are lost for the rest of the session. The limit here leaves room.
        for skill in sorted(SKILLS.glob('*/SKILL.md')):
            self.assertLess(len(skill.read_bytes()), 15000, skill.parent.name)


if __name__ == '__main__':
    unittest.main()
