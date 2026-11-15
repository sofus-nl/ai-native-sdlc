"""Replay the guard's package-add detection over local Claude Code transcripts (stdlib only).

Run before a release that changes the detection: python scripts/replay_guard.py ~/.claude/projects
Read every command it prints. A restore among them (an install with no package name) is a false denial."""

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from edit_guard import packageAdded  # noqa: E402


def commands(aPath):
    """Yield whether the session has used the plugin so far, and each shell command it ran."""
    routed = False
    with open(aPath, encoding='utf-8', errors='replace') as transcript:
        for line in transcript:
            if '"tool_use"' not in line and 'ai-native-sdlc:' not in line:
                continue
            try:
                content = json.loads(line)['message']['content']
            except (ValueError, KeyError, TypeError):
                continue
            if isinstance(content, str):
                routed = routed or '<command-name>/ai-native-sdlc:' in content
                continue
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                args = block.get('input') if isinstance(block.get('input'), dict) else {}
                if block.get('type') == 'text':
                    routed = routed or '<command-name>/ai-native-sdlc:' in str(block.get('text') or '')
                elif block.get('name') == 'Skill':
                    routed = routed or str(args.get('skill', '')).startswith('ai-native-sdlc:')
                elif block.get('name') in ('Bash', 'PowerShell'):
                    yield routed, str(args.get('command') or '')
    # A session whose last entry invoked the plugin, or that ran no shell command, still counts as a plugin session.
    yield routed, ''


def main(aRoot):
    sessions, hits = collections.Counter(), collections.Counter()
    for path in sorted(Path(aRoot).expanduser().rglob('*.jsonl')):
        found = routed = False
        try:
            for routed, command in commands(path):
                added = packageAdded(command)
                if added:
                    found = True
                    hits[('plugin session' if routed else 'other session', added, ' '.join(command.split())[:160])] += 1
        except OSError:
            continue
        sessions['all'] += 1
        sessions['used the plugin'] += routed
        sessions['with a package-add'] += found
    print(dict(sessions))
    for (kind, added, command), count in sorted(hits.items()):
        print(f'{count:4d}  {kind}  package add: {added}\n      {command}')
    print(f'commands classed as a package-add: {sum(hits.values())}')
    print('restores classed as a package-add: read the list above; expected 0')


if __name__ == '__main__':
    main(sys.argv[1])
