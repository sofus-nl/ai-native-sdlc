"""PreToolUse guard: in an ai-native-sdlc session, block file writes until the lane allows them (stdlib only)."""

import json
import re
import sys
from pathlib import Path

EDIT_TOOLS = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit'}
SHELL_TOOLS = {'Bash', 'PowerShell'}
LANE = re.compile(r'\b(fast|standard|controlled)\b[^.\n]{0,20}\blane\b|\blane\b\W{0,6}(fast|standard|controlled)\b', re.I)
REDIRECT = re.compile(r'\d?>>?\s*([^\s;&|<>]+)')
HEREDOC = re.compile(r'<<-?\s*[\'"]?(\w+)[\'"]?[^\n]*\n.*?\n\s*\1\b', re.S)
# ponytail: shell write detection is a heuristic; a command that writes through an unlisted program slips past.
SHELL_WRITE = re.compile(r'\b(tee|sed\s+-i|cp|mv|rm|touch|truncate|Set-Content|Out-File|Add-Content|New-Item|'
                         r'Remove-Item|Copy-Item|Move-Item)\b', re.I)
SCRIPT_WRITE = re.compile(r'write_text|writeFile|open\([^)]*[\'"][wa]')
GATES = {'standard': ('plan',), 'controlled': ('intent', 'design', 'plan')}


def shellWritesOutsideSdlc(aCommand):
    outer = HEREDOC.sub('<<', aCommand)
    targets = [t for t in REDIRECT.findall(outer) if not t.startswith('&') and t.lower() not in ('/dev/null', 'nul', '$null')]
    unknown = SHELL_WRITE.search(outer) or SCRIPT_WRITE.search(aCommand)
    return bool(unknown) or any('.sdlc' not in t for t in targets)


def decide(aEvent):
    tool, args = aEvent.get('tool_name'), aEvent.get('tool_input') or {}
    if tool in EDIT_TOOLS:
        if '.sdlc' in Path(args.get('file_path') or args.get('notebook_path') or '').parts:
            return None
    elif tool in SHELL_TOOLS:
        command = args.get('command', '')
        if not shellWritesOutsideSdlc(command):
            return None
    else:
        return None
    texts, routed = [], False
    try:
        with open(aEvent.get('transcript_path') or '', encoding='utf-8', errors='replace') as transcript:
            for line in transcript:
                routed = routed or 'ai-native-sdlc:ai-native-' in line
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get('type') == 'assistant':
                    texts += [c.get('text', '') for c in entry['message'].get('content', []) if c.get('type') == 'text']
    except OSError:
        return None
    if not routed:
        return None
    states = [p.read_text(encoding='utf-8', errors='replace')
              for p in Path(aEvent.get('cwd') or '.').glob('.sdlc/changes/*/state.md')]
    lanes = [m.group(1) or m.group(2) for m in LANE.finditer('\n'.join(texts + states))]
    if not lanes:
        return 'State the lane (Fast, Standard, or Controlled) in a message before changing files.'
    lane = lanes[-1].lower()
    missing = [g for g in GATES.get(lane, ()) if not any(re.search(rf'gate:\s*["\']?{g}\b', s) for s in states)]
    if not missing:
        return None
    return (f'{lane.capitalize()} work changes no files outside .sdlc/ until state.md records these approvals: '
            f'{", ".join(missing)}. Invoke the next ai-native skill instead; write lifecycle files with separate commands.')


def decideStop(aEvent):
    # One nudge per stop: a second stop after a block is allowed, so the agent can hand back to the human.
    if aEvent.get('stop_hook_active'):
        return None
    for path in Path(aEvent.get('cwd') or '.').glob('.sdlc/changes/*/state.md'):
        state = path.read_text(encoding='utf-8', errors='replace')
        lane = re.search(r'^lane:\s*(\w+)', state, re.M | re.I)
        status = re.search(r'^status:\s*(\w+)', state, re.M)
        if lane and lane.group(1).lower() in GATES and status and status.group(1) in ('building', 'reviewing'):
            return (f'{path.parent.name} is at status: {status.group(1)}. Finish the lifecycle before stopping: invoke '
                    'the ai-native-review skill on the full diff, then ai-native-verify; or, if you need the human, '
                    'set status: blocked with a blocker and next_action.')
    return None


def main():
    event = json.load(sys.stdin)
    if event.get('hook_event_name') == 'Stop':
        reason = decideStop(event)
        if reason:
            print(json.dumps({'decision': 'block', 'reason': reason}))
        return
    reason = decide(event)
    if reason:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                                 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': reason}}))


if __name__ == '__main__':
    main()
