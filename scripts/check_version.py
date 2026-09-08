"""Check SemVer syntax and package version consistency (stdlib only)."""

import argparse
import json
from pathlib import Path
import re


# SemVer 2.0.0 grammar: numeric prerelease identifiers cannot have leading zeroes.
NUMBER = r'(?:0|[1-9][0-9]*)'
IDENTIFIER = rf'(?:{NUMBER}|[0-9]*[A-Za-z-][0-9A-Za-z-]*)'
SEMVER = re.compile(
    rf'{NUMBER}\.{NUMBER}\.{NUMBER}'
    rf'(?:-{IDENTIFIER}(?:\.{IDENTIFIER})*)?'
    r'(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?'
)


def validate(claude, codex, marketplace, changelog):
    versions = [claude['version'], codex['version']]
    for plugin in marketplace['plugins']:
        if plugin['name'] == claude['name'] and 'version' in plugin:
            versions.append(plugin['version'])
    if any(not isinstance(v, str) or not SEMVER.fullmatch(v) for v in versions):
        raise ValueError('Invalid SemVer version')
    if len(set(versions)) != 1:
        raise ValueError('Plugin versions differ')
    headings = re.findall(r'^## (\S+) - (Unreleased|[0-9]{4}-[0-9]{2}-[0-9]{2})$',
                          changelog, re.MULTILINE)
    if not headings or headings[0][0] != versions[0]:
        raise ValueError('First versioned changelog entry must match the manifests')
    return versions[0]


def self_test():
    for value in ('0.5.0', '1.0.0-rc.1', '1.0.0-0', '1.0.0-x-y.01a+001',
                  '1.0.0+build.001'):
        assert SEMVER.fullmatch(value), value
    for value in ('01.0.0', '1.01.0', '1.0.01', '1.0', 'v1.0.0',
                  '1.0.0-01', '1.0.0-rc..1', '1.0.0+', '1.0.0\n', '１.0.0'):
        assert not SEMVER.fullmatch(value), value
    manifest = {'name': 'sample', 'version': '0.5.0'}
    marketplace = {'plugins': [{'name': 'sample'}]}
    changelog = '## 0.5.0 - Unreleased\n'
    assert validate(manifest, manifest, marketplace, changelog) == '0.5.0'
    for codex, market, log in (
        ({**manifest, 'version': '0.4.0'}, marketplace, changelog),
        (manifest, {'plugins': [{**manifest, 'version': '0.4.0'}]}, changelog),
        (manifest, marketplace, '## 0.4.0 - 2026-09-05\n'),
        ({**manifest, 'version': None}, marketplace, changelog),
    ):
        try:
            validate(manifest, codex, market, log)
        except ValueError:
            continue
        raise AssertionError('Invalid package accepted')
    print('Version self-checks passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        root = Path(__file__).resolve().parents[1]
        def read_json(path):
            return json.loads((root / path).read_text(encoding='utf-8'))
        version = validate(read_json('.claude-plugin/plugin.json'),
                           read_json('.codex-plugin/plugin.json'),
                           read_json('.claude-plugin/marketplace.json'),
                           (root / 'docs/changelogs/CHANGELOG.md').read_text(encoding='utf-8'))
        print(f'Version checks passed: {version}')
