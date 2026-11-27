"""Checks on the skill files that both hosts load (stdlib only)."""

import hashlib
import re
import unittest
from pathlib import Path

from behavior_check import CASES

SKILLS = Path(__file__).resolve().parents[1] / 'skills'
REFERENCES = SKILLS / 'ai-native-sdlc' / 'references'
SECURITY = REFERENCES / 'security.md'
STAGES = ('shape', 'plan', 'build', 'review', 'verify')
FLAGS = re.IGNORECASE | re.MULTILINE


def chunks(aText):
    # A chunk is a paragraph or a single list item.
    return [c for c in re.split(r'\n\s*\n|\n(?=\s*(?:[-*+]|\d+\.)\s)', aText) if c.strip()]


def stageSections(aText):
    # Maps each stage to the text under its heading or bold label at the start of a line.
    label = re.compile(r'^(?:[-*]\s+)?(?:#{1,6}\s+|\*\*|__)\s*(' + '|'.join(STAGES) + r')\b', FLAGS)
    marks = [(m.start(), m.group(1).lower()) for m in label.finditer(aText)]
    ends = [start for start, _ in marks[1:]] + [len(aText)]
    return {stage: aText[start:end] for (start, stage), end in zip(marks, ends)}


def fileSection(aText, aName):
    match = re.search(r'^## `' + re.escape(aName) + r'`.*?(?=^## |\Z)', aText, re.DOTALL | re.MULTILINE)
    return match.group(0) if match else ''


class SkillFilesTest(unittest.TestCase):
    def test_skill_fits_after_compaction(self):
        # After compaction Claude Code re-attaches an invoked skill cut at 20,000 characters, so the rules below the
        # cut are lost for the rest of the session. The limit here leaves room.
        for skill in sorted(SKILLS.glob('*/SKILL.md')):
            self.assertLess(len(skill.read_bytes()), 15000, skill.parent.name)

    def test_router_makes_a_dependency_change_at_least_standard(self):
        text = (SKILLS / 'ai-native-sdlc' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(
            any(re.search(r'dependenc', c, FLAGS) and re.search(r'at least\s+standard', c, FLAGS) for c in chunks(text)),
            'no paragraph or list item ties a dependency change to "at least Standard"')

    def test_router_points_at_the_dependency_record(self):
        folder = SKILLS / 'ai-native-sdlc'
        text = (folder / 'SKILL.md').read_text(encoding='utf-8')
        lane = [c for c in chunks(text) if re.search(r'dependenc', c, FLAGS) and re.search(r'at least\s+standard', c, FLAGS)]
        self.assertTrue(lane, 'no paragraph or list item ties a dependency change to "at least Standard"')
        self.assertTrue(
            any(re.search(r'dependency record', c, FLAGS)
                and any((folder / t).resolve() == SECURITY.resolve() and SECURITY.is_file()
                        for t in re.findall(r'[\w./-]*security\.md', c))
                for c in lane),
            'the chunk that ties a dependency change to "at least Standard" must link a security.md that resolves '
            'to references/security.md and mention the dependency record')

    def test_router_reports_outside_instructions_and_does_not_follow_them(self):
        text = (SKILLS / 'ai-native-sdlc' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(
            any(re.search(r'\breport(?:ed|s)?\b', c, FLAGS)
                and re.search(r"(?:not|never|n't)\s+(?:be\s+)?follow(?:ed)?\b", c, FLAGS)
                and re.search(r'outside|authority', c, FLAGS)
                and re.search(r'\b(?:in|inside|within)\s+(?:this|the)\s+repository\b', c, FLAGS) for c in chunks(text)),
            'no paragraph or list item says an instruction from outside text is reported and not followed')

    def test_router_limits_what_repository_instructions_authorize(self):
        text = (SKILLS / 'ai-native-sdlc' / 'SKILL.md').read_text(encoding='utf-8')
        terms = (r'repository instructions', r'download', r'not read', r'hooks', r'MCP', r'settings', r'request asks',
                 r'lockfile', r'build or test', r'unless')
        self.assertTrue(
            any(all(re.search(t, c, FLAGS) for t in terms) for c in chunks(text)),
            'no paragraph or list item says repository instructions cannot authorize downloads, unread scripts, '
            'or agent-configuration changes')

    def test_router_says_built_ins_do_not_count(self):
        text = (SKILLS / 'ai-native-sdlc' / 'SKILL.md').read_text(encoding='utf-8')
        for name in ('review', 'verify', 'ship'):
            self.assertIn('ai-native-sdlc:ai-native-' + name, text)
        self.assertTrue(
            any(all(re.search(t, c, FLAGS) for t in (r'built-in', r'/ship', r'/verify', r'(?:do|does) not count'))
                for c in chunks(text)),
            'no paragraph or list item says the built-in /ship and /verify do not count')
        self.assertTrue(
            any(re.search(r'built-in', c, FLAGS) and re.search(r'gates of .*ai-native-ship.* did not run', c, FLAGS)
                for c in chunks(text)),
            'no paragraph or list item says to report a delivery made with a built-in command')

    def test_security_reference_has_one_duty_per_stage(self):
        self.assertTrue(SECURITY.is_file(), 'references/security.md is missing')
        sections = stageSections(SECURITY.read_text(encoding='utf-8'))
        for stage in STAGES:
            self.assertGreater(len(sections.get(stage, '').split()), 3, 'no duty under ' + stage)
        self.assertRegex(sections['shape'], re.compile(r'abuse case', FLAGS))
        for term in (r'registry', r'install script', r'lockfile', r'release date|cooldown'):
            self.assertRegex(sections['plan'], re.compile(term, FLAGS))
        for term in (r'plan', r'install'):
            self.assertRegex(sections['build'], re.compile(term, FLAGS))
        for term in (r'lockfile', r'plan'):
            self.assertRegex(sections['review'], re.compile(term, FLAGS))
        self.assertRegex(sections['verify'], re.compile(r'limitation', FLAGS))

    def test_security_reference_stays_small(self):
        # Fast work never reads this file; the limit keeps the cost low for the Standard and Controlled work that does.
        self.assertTrue(SECURITY.is_file(), 'references/security.md is missing')
        self.assertLess(len(SECURITY.read_bytes()), 4000)

    def test_each_leaf_skill_links_security_reference(self):
        for name in ('shape', 'plan', 'build', 'review', 'verify'):
            with self.subTest(name):
                folder = SKILLS / ('ai-native-' + name)
                text = (folder / 'SKILL.md').read_text(encoding='utf-8')
                targets = re.findall(r'[\w./-]*security\.md', text)
                self.assertTrue(any((folder / t).resolve() == SECURITY.resolve() and SECURITY.is_file() for t in targets),
                                name + ' does not link a security.md that resolves to references/security.md')
                self.assertTrue(
                    any(re.search(r'security\.md', c) and re.search(r'controlled', c, FLAGS) and re.search(r'dependenc', c, FLAGS)
                        for c in chunks(text)),
                    name + ' does not tie the security.md link to Controlled work or a dependency change')

    def test_artifact_contracts_lists_abuse_cases_and_dependency_record(self):
        text = (REFERENCES / 'artifact-contracts.md').read_text(encoding='utf-8')
        self.assertRegex(fileSection(text, 'spec.md'), re.compile(r'abuse case', FLAGS))
        self.assertRegex(fileSection(text, 'plan.md'), re.compile(r'dependency record|registry|lockfile', FLAGS))

    def test_enforcement_table_follows_the_router_and_names_real_enforcers(self):
        root = SKILLS.parent
        doc = (root / 'docs' / 'tracking' / 'ARCHITECTURE.md').read_text(encoding='utf-8')
        section = re.search(r'^## Enforcement\n.*?(?=^## |\Z)', doc, re.DOTALL | re.MULTILINE)
        self.assertTrue(section, 'docs/tracking/ARCHITECTURE.md has no Enforcement section')
        router = (SKILLS / 'ai-native-sdlc' / 'SKILL.md').read_text(encoding='utf-8')
        invariants = re.search(r'^## Invariants\n(.*?)(?=^## )', router, re.DOTALL | re.MULTILINE).group(1).strip()
        digest = hashlib.sha256(invariants.encode('utf-8')).hexdigest()[:12]
        self.assertEqual(re.findall(r'^Invariants digest: `(\w+)`$', section.group(0), re.MULTILINE), [digest],
                         'a router invariant changed: check each row of the table, then record this digest')
        rows = [r for r in section.group(0).splitlines() if r.startswith('| ')][2:]
        # 5 is the number of lane gates the table lists below the invariants.
        self.assertEqual(len(rows), len(re.findall(r'^- ', invariants, re.MULTILINE)) + 5)
        guard = (root / 'hooks' / 'edit_guard.py').read_text(encoding='utf-8')
        for row in rows:
            cell = row.rstrip('|').rsplit('|', 1)[1].strip()
            tokens = re.findall(r'`([^`]+)`', cell)
            self.assertTrue(tokens or cell == 'none', row)
            for token in tokens:
                with self.subTest(token):
                    if token.startswith('case:'):
                        found = token[5:] in CASES
                    elif token.startswith('edit_guard.'):
                        found = re.search(rf'^def {re.escape(token[11:])}\(', guard, re.MULTILINE)
                    else:
                        stem, method = token.split('.')
                        found = stem.startswith('test_') and method.startswith('test_') and re.search(
                            rf'^    def {re.escape(method)}\(', (root / 'scripts' / f'{stem}.py').read_text(encoding='utf-8'),
                            re.MULTILINE)
                    self.assertTrue(found, 'the table names an enforcer that does not exist')


if __name__ == '__main__':
    unittest.main()
