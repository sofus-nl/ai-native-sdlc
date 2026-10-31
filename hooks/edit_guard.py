"""PreToolUse guard: in an ai-native-sdlc session, block file writes until the lane allows them (stdlib only)."""

import json
import os
import re
import sys
import time
from pathlib import Path

EDIT_TOOLS = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit'}
SHELL_TOOLS = {'Bash', 'PowerShell'}
LANES = ('fast', 'standard', 'controlled')
LANE = re.compile(r'\b(fast|standard|controlled)\b[^.\n]{0,20}\blane\b|\blane\b[^.\n]{0,20}?\b(fast|standard|controlled)\b', re.I)
REDIRECT = re.compile(r'\d?>>?\s*([^\s;&|<>]+)')
HEREDOC = re.compile(r'<<-?\s*[\'"]?(\w+)[\'"]?[^\n]*\n.*?\n\s*\1\b', re.S)
# ponytail: shell write detection is a heuristic; a command that writes through an unlisted program slips past.
SHELL_WRITE = re.compile(r'\b(tee|sed\s+-i|cp|mv|rm|touch|truncate|Set-Content|Out-File|Add-Content|New-Item|'
                         r'Remove-Item|Copy-Item|Move-Item)\b', re.I)
SCRIPT_WRITE = re.compile(r'write_text|writeFile|open\([^)]*[\'"][wa]')
STATE = r'\.sdlc[\\/]+changes[\\/]+[\w.-]+[\\/]+state\.md'
STATE_FILE = re.compile(STATE + '$')
STATE_TOKEN = re.compile(r'[^\s"\'`;&|<>]*' + STATE + r'(?![\w.])')
GATES = {'standard': ('plan',), 'controlled': ('intent', 'design', 'plan')}


def shellWritesOutsideSdlc(aCommand):
    outer = HEREDOC.sub('<<', aCommand)
    targets = [t for t in REDIRECT.findall(outer) if not t.startswith('&') and t.lower() not in ('/dev/null', 'nul', '$null')]
    unknown = SHELL_WRITE.search(outer) or SCRIPT_WRITE.search(aCommand)
    return bool(unknown) or any('.sdlc' not in t for t in targets)


def statePath(aToken):
    return Path(aToken) if Path(aToken).is_absolute() else Path(aToken[aToken.find('.sdlc'):])


def readSession(aEvent):
    """Return whether this session invoked the plugin, its assistant text, and the state.md of its active change."""
    routed, texts, written, referenced = False, [], [], []
    with open(aEvent.get('transcript_path') or '', encoding='utf-8', errors='replace') as transcript:
        for line in transcript:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            message = entry.get('message')
            content = message.get('content') if isinstance(message, dict) else None
            if entry.get('type') == 'user':
                # A typed slash command. Tool results are skipped: quoted file contents can contain the marker.
                said = content if isinstance(content, str) else ' '.join(
                    c.get('text', '') for c in content or [] if isinstance(c, dict) and c.get('type') == 'text')
                routed = routed or '<command-name>/ai-native-sdlc:' in said
            elif entry.get('type') == 'assistant' and isinstance(content, list):
                for c in content:
                    if not isinstance(c, dict):
                        continue
                    name, args = c.get('name'), c.get('input') if isinstance(c.get('input'), dict) else {}
                    if c.get('type') == 'text':
                        texts.append(c.get('text', ''))
                    elif c.get('type') != 'tool_use':
                        continue
                    elif name == 'Skill':
                        routed = routed or str(args.get('skill', '')).startswith('ai-native-sdlc:')
                    # Brief mode sends user-facing text through SendUserMessage (alias Brief), not text blocks.
                    elif name in ('SendUserMessage', 'Brief'):
                        texts.append(str(args.get('message', '')))
                    elif name in SHELL_TOOLS:
                        # A state file is written when a segment redirects into it, or starts with a write command that names it.
                        # A heredoc body stays with the segment that opens it, so a script that writes the path counts.
                        bodies = []
                        outer = HEREDOC.sub(lambda m: bodies.append(m.group()) or f'\0{len(bodies) - 1}\0', str(args.get('command', '')))
                        for part in re.split(r'&&|\|\||[;|\n]', outer):
                            segment = re.sub(r'\0(\d+)\0', lambda m: bodies[int(m.group(1))], part)
                            found = [statePath(t) for t in STATE_TOKEN.findall(segment)]
                            targets = [statePath(STATE_TOKEN.search(t).group()) for t in REDIRECT.findall(segment) if STATE_TOKEN.search(t)]
                            referenced += found
                            written += targets or (found if SHELL_WRITE.match(segment.strip()) or SCRIPT_WRITE.search(segment) else [])
                    elif STATE_FILE.search(str(args.get('file_path') or args.get('notebook_path') or args.get('path') or '')):
                        referenced.append(Path(args.get('file_path') or args.get('notebook_path') or args.get('path')))
                        written += referenced[-1:] if name in EDIT_TOOLS else []
    # The change whose state.md this session last wrote is active; failing that, the one it last read.
    # Agents often write it through the shell, and read other changes' state.md for context.
    active = (written or referenced or [None])[-1]
    if active is None or active.is_absolute():
        return routed, texts, active
    starts = [Path(p) for p in (aEvent.get('cwd'), os.environ.get('CLAUDE_PROJECT_DIR')) if p]
    root = next((d for s in starts for d in (s, *s.parents) if (d / '.sdlc').is_dir()), None)
    return routed, texts, root / active if root else None


def readState(aPath):
    try:
        return aPath.read_text(encoding='utf-8', errors='replace') if aPath and aPath.is_file() else ''
    except OSError:
        return ''


def approvedGates(aState):
    lines = aState.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r'approvals:', l, re.I)), len(lines))
    block = []
    # The list ends at the first blank or unindented line, so notes below the header never count as approvals.
    for line in lines[start + 1:]:
        if not re.match(r'\s+\S|-\s', line):
            break
        block.append(line)
    indent = next((re.match(r'\s*', l).group() for l in block if re.match(r'\s*-\s', l)), '')
    entries = re.split(rf'\n(?={re.escape(indent)}-\s)', '\n'.join(block))
    return {m.group(1).lower() for e in entries if not re.search(r'decision:\s*["\']?rejected', e, re.I)
            for m in [re.match(r'\s*-\s*\{?\s*gate:\s*["\']?(\w+)', e, re.I)] if m}


def decide(aEvent, aAttempt=0):
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
    try:
        routed, texts, path = readSession(aEvent)
    except OSError:
        return None
    if not routed:
        return None
    state = readState(path)
    stated = [(m.group(1) or m.group(2)).lower() for m in LANE.finditer('\n'.join(texts))]
    recorded = [r.lower() for r in re.findall(r'^lane:\s*(\w+)', state, re.M | re.I)]
    lanes = [l for l in stated[-1:] + recorded[:1] if l in LANES]
    # Text in the same message as this tool call can reach the transcript up to ~1 s after the hook starts.
    if not lanes and aAttempt < 20:
        time.sleep(0.1)
        return decide(aEvent, aAttempt + 1)
    if not lanes:
        return 'State the lane (Fast, Standard, or Controlled) in a message before changing files, for example "Lane: Fast".'
    # The stricter of the stated and the recorded lane applies, so stating a lower lane never clears a gate.
    lane = max(lanes, key=LANES.index)
    missing = [g for g in GATES.get(lane, ()) if g not in approvedGates(state)]
    if not missing:
        return None
    where = f'.sdlc/changes/{path.parent.name}/state.md' if state else "this session's change state.md (none read or written yet)"
    return (f'{lane.capitalize()} work changes no files outside .sdlc/ until {where} records these approvals: '
            f'{", ".join(missing)}. Invoke the next ai-native skill instead; write lifecycle files with separate commands.')


def decideStop(aEvent):
    # One nudge per stop: a second stop after a block is allowed, so the agent can hand back to the human.
    # A turn that ends while background tasks run is paused, not finished.
    # shortcut: a long-running background shell (a dev server) also counts and suppresses the nudge; filter by type if logs show it.
    if aEvent.get('stop_hook_active') or aEvent.get('background_tasks'):
        return None
    try:
        routed, _, path = readSession(aEvent)
    except OSError:
        return None
    state = readState(path) if routed else ''
    lane = re.search(r'^lane:\s*(\w+)', state, re.M | re.I)
    status = re.search(r'^status:\s*(\w+)', state, re.M | re.I)
    if lane and lane.group(1).lower() in GATES and status and status.group(1).lower() in ('building', 'reviewing'):
        return (f'{path.parent.name} is at status: {status.group(1)}. Finish the lifecycle before stopping: invoke '
                'the ai-native-review skill on the full diff, then ai-native-verify; or, if you need a human decision, '
                'set status: blocked with a blocker and next_action. Blocked means waiting on a human only.')
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
