"""Claude Code hook for ai-native-sdlc sessions: block file writes until the lane allows them, and record the
plugin's skill calls so that status: verified follows a review and a verify of the same code (stdlib only)."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EDIT_TOOLS = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit'}
SHELL_TOOLS = {'Bash', 'PowerShell'}
LANES = ('fast', 'standard', 'controlled')
LANE = re.compile(r'\b(fast|standard|controlled)\b[^.\n]{0,20}\blane\b|\blane\b[^.\n]{0,20}?\b(fast|standard|controlled)\b', re.I)
REDIRECT = re.compile(r'\d?>>?\s*([^\s;&|<>]+)')
# Group 2 is the rest of the marker line, which the shell still runs (`cat <<EOF > file`). The body may be empty.
HEREDOC = re.compile(r'<<-?\s*[\'"]?([\w-]+)[\'"]?([^\n]*)\n(?:[^\n]*\n)*?[ \t]*\1[ \t]*(?=\n|$)')
# ponytail: shell write detection is a heuristic; a command that writes through an unlisted program slips past.
SHELL_WRITE = re.compile(r'(?<![\w-])(tee|sed\s+-i|cp|mv|rm|touch|truncate|Set-Content|Out-File|Add-Content|New-Item|'
                         r'Remove-Item|Copy-Item|Move-Item)\b', re.I)
SCRIPT_WRITE = re.compile(r'write_text|writeFile|(?:Write|Append)All(?:Text|Lines|Bytes)|'
                          r'open\((?:[^)]{0,500},)?\s*(?:mode\s*=\s*)?[\'"](?:[wa][bt+]{0,2}|r[bt]?\+[bt]?)[\'"]', re.I)
# PowerShell here-strings first, then ordinary strings. A quote escaped outside a string is removed before this runs.
QUOTED = re.compile(r'@\'[\s\S]*?\n\'@|@"[\s\S]*?\n"@|"(?:\\.|[^"\\])*"|\'[^\']*\'')
# An assignment counts only in command position, so `echo PWD=.sdlc` assigns nothing.
ASSIGN = re.compile(r'(?:^|[;&|\n(])[ \t]*(?:export\s+|local\s+)?\$?(?:env:)?(\w+)\s*=\s*("[^"\n]*"|\'[^\'\n]*\'|[^\s;&|]+)')
# Programs that run their quoted argument as code, so that argument is scanned like the rest of the command.
NESTED = re.compile(r'(?<![\w.-])(?:bash|sh|zsh|dash|ksh|pwsh|powershell|cmd|wsl)(?:\.exe)?\s+(?:-\w*c\b|-Command\b|/c\b|-e\b)'
                    r'|(?<![\w.-])(?:eval|iex|invoke-expression|start-process)(?![\w.-])', re.I)
CODE = re.compile(r'os\.system\(|subprocess\.\w+\(|execSync\(|spawnSync\(|popen\(', re.I)
# Other ways a shell variable gets a value; such a name is then set more than once and stays unresolved.
RESET = re.compile(r'(?:^|[;&|\n(])[ \t]*(?:declare|typeset|local|export|readonly|read|set)\s+(?:-\w+\s+)*\$?(\w+)|(?<!\w)(\w{1,64})\+=')
INTERPRETER = re.compile(r'(?<![\w.-])(?:python[\d.]*|py|node|deno|bun|npx|tsx|ts-node|ruby|perl|php|pwsh|powershell)(?:\.exe)?(?![\w-])', re.I)
CD = re.compile(r'(?<![\w.-])(?:cd|pushd|popd|chdir|sl|Set-Location|Push-Location|Pop-Location)(?![\w.-])|\s-C\s', re.I)
# The option of cp and Copy-Item that names the destination.
DESTINATION = re.compile(r'(?:-[A-Za-z]*t|(?i:--target-directory|-Destination))(?=$|[=:])')
STATE = r'\.sdlc[\\/]+changes[\\/]+[\w.-]+[\\/]+state\.md'
STATE_FILE = re.compile(STATE + '$')
STATE_TOKEN = re.compile(r'[^\s"\'`;&|<>]{0,512}' + STATE + r'(?![\w.])')
GATES = {'standard': ('plan',), 'controlled': ('intent', 'design', 'plan')}
# Folders that hold no project code, for a project that Git does not track.
NOT_CODE = {'.git', '.sdlc', 'node_modules', '__pycache__', '.venv', 'venv', '.pytest_cache', '.mypy_cache', 'dist', 'build', 'target'}
CLAIM = re.compile(r'status:\s*["\']?verified\b', re.I)
STATUS = re.compile(r'^[ \t]*status:\s*["\']?verified\b', re.I | re.M)
# Non-empty once decide() has read the whole transcript and seen this session invoke the plugin. A failure while
# reading it must not deny: the transcript only grows, so one bad line would deny every later write, Fast included.
ROUTED = []


def inSdlc(aTarget):
    parts = re.split(r'[\\/]+', aTarget)
    return '.sdlc' in parts and '..' not in parts


def inScratch(aTarget, aRoots):
    """An absolute path under a temp folder and not under the project. A sibling clone is still project work."""
    def norm(aPath):
        # Git Bash spells a drive as /c/, WSL as /mnt/c/, Cygwin as /cygdrive/c/.
        return re.sub(r'^/(?:mnt/|cygdrive/)?([a-z])/', r'\1:/', str(aPath).replace('\\', '/').lower()).rstrip('/') + '/'
    target = norm(aTarget)
    temps = [os.environ.get(n) for n in ('TEMP', 'TMP', 'TMPDIR')] + ['/tmp', '/var/tmp', '/dev']
    return ('..' not in target.split('/') and any(target.startswith(norm(t)) for t in temps if t)
            and not any(target.startswith(norm(r)) for r in aRoots))


def projectRoots(aEvent):
    starts = [Path(p) for p in (aEvent.get('cwd'), os.environ.get('CLAUDE_PROJECT_DIR')) if p]
    return starts + [d for s in starts for d in s.parents if (d / '.git').exists() or (d / '.sdlc').exists()]


def expandVars(aCommand):
    # Resolve a variable from the assignment that precedes its use, so `d=.sdlc/changes/x; cat > $d/spec.md` shows
    # its real target. The temp folder comes from the environment, so "$TEMP/run.log" shows as a scratch file.
    assigns = [(-1, n, os.environ[n]) for n in ('TEMP', 'TMP', 'TMPDIR') if os.environ.get(n)]
    assigns += [(m.start(), m.group(1), m.group(2).strip('"\'')) for m in ASSIGN.finditer(aCommand)]
    assigns += [(m.start(), m.group(1) or m.group(2), '') for m in RESET.finditer(aCommand)]

    def value(aMatch):
        name = aMatch.group(1) or aMatch.group(2)
        known = [v for p, n, v in assigns if n == name and p < aMatch.start()]
        # A name assigned more than once may depend on a condition, so it stays unresolved.
        return known[-1] if len(known) == 1 == sum(n == name for _, n, _ in assigns) else aMatch.group()
    return re.sub(r'\$(?:env:)?(\w+)|\$\{(\w+)\}', value, aCommand)


def shellWritesOutsideSdlc(aCommand, aRoots=()):
    """Return what in the command writes a project file outside .sdlc/, or '' when nothing does."""
    # A shell argument cannot hold NUL, so NUL is free to mark the hidden quoted strings below. A comment line without
    # quotes is dropped; one with a quote, or an escaped quote, could pair with a later quote, so such a command is
    # scanned without hiding anything.
    outer = expandVars(HEREDOC.sub(r'<<\2', str(aCommand).replace('\0', '')))
    stray = re.search(r'(?m)\\[\'"]|^[ \t]*#[^\n]*[\'"]', outer)
    outer = re.sub(r'(?m)^[ \t]*#[^\'"\n]*$', '', outer)
    quoted = []
    bare = QUOTED.sub(lambda m: quoted.append(m.group().strip('@\'"')) or f'\0{len(quoted) - 1}\0', outer)
    # Operators and command names inside a quoted argument are data, unless a program runs that argument or a quote
    # is left unpaired.
    runs = stray or NESTED.search(bare) or CODE.search(outer) or re.search(r'[\'"]', bare) or any('$(' in q or '`' in q for q in quoted)
    segments = re.split(r'&&|\|\||[;&|\n]', outer if runs else bare)
    # Relative targets follow a cd only while every directory change is a plain one at the start of a segment and
    # nothing runs in a subshell, a group, or another program. A `$(...)` with no directory change in it leaves the
    # directory as it is (`D=$(date +%F)`), and its inner commands are still scanned as segments.
    flat = re.sub(r'\$\(([^()`]*)\)', lambda m: m.group() if CD.search(m.group(1)) else '', bare)
    track = not runs and not re.search(r'[(){}`]', flat) and all(not CD.search(s) or CD.match(s.lstrip()) for s in segments)
    here = ''

    def unquote(aToken):
        return re.sub(r'\0(\d+)\0', lambda m: quoted[int(m.group(1))] if int(m.group(1)) < len(quoted) else '', aToken).strip('"\'')

    def resolve(aToken):
        target = unquote(aToken)
        return target if not here or re.match(r'[/\\~$]|[A-Za-z]:', target) else f'{here}/{target}'
    for segment in segments:
        # The word in command position is the command itself, however it is quoted or escaped (`"rm"`, `c""d`, `c\d`).
        segment = re.sub(r'^(\s*)(\S+)', lambda m: m.group(1) + re.sub(r'\\(\w)', r'\1', unquote(m.group(2))), segment, count=1)
        segment = re.sub(r'(-exec\s+)\0(\d+)\0', lambda m: m.group(1) + unquote(m.group()[len(m.group(1)):]), segment)
        if track and CD.match(segment.lstrip()):
            moved = re.match(r'\s*\S+\s+(\S+)\s*$', segment)
            here = resolve(moved.group(1)) if moved and not re.search(r'^[-~]|[$*]', unquote(moved.group(1))) else ''
        # A redirect with nothing after it is a stray `>` in text, not a write.
        for target in map(resolve, filter(unquote, REDIRECT.findall(segment))):
            null = re.search(r'(?:^|/)(?:dev/null|nul|\$null)$', target.lower())
            if not null and not inSdlc(target) and not inScratch(target, aRoots):
                return f'redirect to {target}'
        found = SHELL_WRITE.search(segment)
        if not found:
            continue
        operands, skip, named, into = [], False, False, None
        for token in REDIRECT.sub('', segment[found.end():]).split():
            attached = re.match(r'-[\w-]*[=:](.+)', token)
            if skip:
                skip = False
            elif attached:
                operands.append(resolve(attached.group(1)))
                into = operands[-1] if DESTINATION.match(token) else into
            elif DESTINATION.fullmatch(token):
                named = True
            elif re.match(r'-(?:Value|Encoding|ItemType|Type|Filter)$', token, re.I):
                # The next token is a value, not a path.
                skip = True
            elif not re.match(r'-|.*[<>]', token):
                operands.append(resolve(token))
                into, named = (operands[-1], False) if named else (into, False)
        # sed's first operand is its script, not a path.
        operands = operands[1:] if found.group(1).lower().startswith('sed') else operands
        # A copy writes its destination only, the last operand unless an option names it; the others are read.
        operands = [into or operands[-1]] if operands and re.match(r'cp|copy-item', found.group(1), re.I) else operands
        if not operands or not all(inSdlc(o) or inScratch(o, aRoots) for o in operands):
            return found.group(1)
    # A script write inside quoted text is data, unless an interpreter or heredoc could run it.
    found = SCRIPT_WRITE.search(str(aCommand) if runs or INTERPRETER.search(bare) or '<<' in bare else bare)
    return found.group() if found else ''


def statePath(aToken):
    return Path(aToken) if Path(aToken).is_absolute() else Path(aToken[aToken.find('.sdlc'):])


def edits(aInput):
    return ([aInput] if 'old_string' in aInput else []) + [e for e in aInput.get('edits') or [] if isinstance(e, dict)]


def claimText(aTool, aInput):
    """Whether the text of this tool call writes status: verified into a state.md, without a look at the file."""
    if aTool in EDIT_TOOLS:
        new = [aInput.get('content')] + [e.get('new_string') for e in edits(aInput)]
        return bool(STATE_FILE.search(str(aInput.get('file_path') or ''))
                    and STATUS.search('\n'.join(str(n) for n in new if n)))
    command = str(aInput.get('command') or '')
    # A command that only reads the state file (grep, cat) writes nothing into it.
    # ponytail: literal text only; a command that writes the status another way (cp of a prepared file, a replace of
    # the word alone) slips past.
    return bool(aTool in SHELL_TOOLS and CLAIM.search(command) and 'state.md' in command
                and (SHELL_WRITE.search(command) or SCRIPT_WRITE.search(command)
                     or any('state.md' in t for t in REDIRECT.findall(command))))


def claimsVerified(aTool, aInput, aRoots):
    """Whether this tool call changes a change's state.md from another status to verified."""
    if aTool in EDIT_TOOLS:
        path = str(aInput.get('file_path') or '')
        if not STATE_FILE.search(path):
            return False
        # Replay the edit, so a change of the status word alone counts and a rewrite of a verified file does not.
        before = readState(Path(path))
        after = str(aInput['content']) if 'content' in aInput else before
        for edit in edits(aInput):
            after = after.replace(str(edit.get('old_string') or ''), str(edit.get('new_string') or ''),
                                  -1 if edit.get('replace_all') else 1)
        return bool(STATUS.search(after) and not STATUS.search(before))
    # A shell command cannot be replayed. A file that is already verified is being rewritten or closed.
    named = [statePath(t) for t in STATE_TOKEN.findall(str(aInput.get('command') or ''))]
    done = [any(STATUS.search(readState(f)) for f in ([p] if p.is_absolute() else [root / p for root in aRoots])) for p in named]
    return claimText(aTool, aInput) and not (done and all(done))


def changesNamed(aInput):
    """The change folders whose state.md this tool call names."""
    return set(re.findall(r'changes[\\/]+([\w.-]+)[\\/]+state\.md', str(aInput.get('file_path') or aInput.get('command') or '')))


def git(aRoot, *aArgs, aInput=None):
    done = subprocess.run(['git', '-C', str(aRoot), *aArgs], input=aInput, capture_output=True, timeout=20)
    if done.returncode:
        raise ValueError(done.stderr[:200])
    return done.stdout


def fingerprint(aRoot):
    """The project's files outside .sdlc/, each with a hash of its content, or None when they cannot be read.
    Files that Git ignores are left out. A commit, a stash, or a checkout changes nothing unless the files change."""
    try:
        names = lambda *aArgs: {n for n in git(aRoot, *aArgs, '-z', '--', '.', ':(exclude).sdlc').split(b'\0') if n}
        try:
            tracked = names('ls-files', '-s')
        except (ValueError, FileNotFoundError):
            tracked = None
        # Inside a repository, a file that Git cannot read leaves the fingerprint unknown: hashes from a folder walk
        # would differ from the ones recorded before.
        if tracked is not None:
            tree = {entry.partition(b'\t')[2]: entry.split()[1] for entry in tracked}
            gone = names('ls-files', '-d')
            # The index holds the hash of every unchanged file; only changed and new files are read.
            fresh = sorted(n for n in (names('diff-files', '--relative', '--name-only') | names('ls-files', '-o', '--exclude-standard')) - gone
                           if (Path(aRoot) / os.fsdecode(n)).is_file() and b'\n' not in n)
            if fresh:
                # Full paths: Git reads these names from the repository root, not from the project folder.
                paths = b'\n'.join(os.fsencode(str(Path(aRoot).resolve() / os.fsdecode(n))) for n in fresh) + b'\n'
                tree.update(zip(fresh, git(aRoot, 'hash-object', '--stdin-paths', aInput=paths).split()))
            tree = {os.fsdecode(n): h.decode()[:16] for n, h in tree.items() if n not in gone}
        else:
            # shortcut: no Git, so every file is read; a project over 2,000 files gets no fingerprint.
            tree = {}
            for folder, folders, files in os.walk(aRoot):
                folders[:] = [f for f in folders if f not in NOT_CODE]
                for name in files:
                    file = Path(folder) / name
                    with open(file, 'rb') as content:
                        digest = hashlib.sha256()
                        for block in iter(lambda: content.read(1 << 20), b''):
                            digest.update(block)
                    tree[file.relative_to(aRoot).as_posix()] = digest.hexdigest()[:16]
                if len(tree) > 2000:
                    return None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return tree


def changed(aSeen, aNow):
    """The files that differ between two fingerprints. An unknown fingerprint differs from nothing."""
    if aSeen is None or aNow is None:
        return []
    return sorted(k for k in {*aSeen, *aNow} if aSeen.get(k) != aNow.get(k))


def logPath(aEvent):
    """This session's record of skill calls and claims. The transcript lags the conversation and leaves out sub-agents."""
    base = os.environ.get('CLAUDE_PLUGIN_DATA') or Path(tempfile.gettempdir()) / 'ai-native-sdlc'
    return Path(base) / 'sessions' / (re.sub(r'[^\w-]', '_', str(aEvent.get('session_id') or 'none')) + '.jsonl')


def record(aEvent, **aEntry):
    path = logPath(aEvent)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            # A record holds a hash per project file; sessions older than two weeks are done.
            for old in path.parent.iterdir():
                if time.time() - old.stat().st_mtime > 14 * 86400:
                    old.unlink()
        with open(path, 'a', encoding='utf-8') as log:
            log.write(json.dumps(aEntry) + '\n')
    except OSError:
        # Without a place to write, the verify check stays off (see readLog); it must not lock the session out.
        pass


def readLog(aEvent):
    """This session's records, or None when they cannot be kept: the folder cannot be written."""
    path = logPath(aEvent)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.is_file() else []
    except (OSError, ValueError):
        return None


def projectRoot(aEvent):
    roots = projectRoots(aEvent)
    return next((r for r in roots if (r / '.sdlc').is_dir()), next((r for r in roots if (r / '.git').exists()), roots[0] if roots else Path('.')))


def note(aEvent):
    """Record a skill of this plugin that the main agent invoked, with the code it starts from."""
    settle(aEvent)
    typed = aEvent.get('hook_event_name') == 'UserPromptExpansion'
    name = str(aEvent.get('command_name') if typed else (aEvent.get('tool_input') or {}).get('skill') or '')
    ran = typed or aEvent.get('tool_name') == 'Skill' and (aEvent.get('tool_response') or {}).get('success', True) is not False
    # A skill inside a sub-agent is not the session's own review or verify.
    if ran and not aEvent.get('agent_id') and name.startswith('ai-native-sdlc:'):
        record(aEvent, skill=name.removeprefix('ai-native-sdlc:'), tree=fingerprint(projectRoot(aEvent)))


def verifyGap(aRecords, aChanges, aTree):
    """Return the skill this session must still invoke before it records status: verified, or ''."""
    if aRecords is None:
        return ''
    # An earlier write of status: verified for the same change used up the skills before it. A write that named
    # no change folder (a bare state.md after a cd) counts for any change.
    used = max((i for i, r in enumerate(aRecords) if 'claim' in r
                and (not r['claim'] or not aChanges or set(r['claim']) & aChanges)), default=-1)
    since = [r for r in aRecords[used + 1:] if 'skill' in r]
    review = lambda aBefore: next((r for r in reversed(since[:aBefore]) if r['skill'] == 'ai-native-review'), None)

    def unseen(aBefore, aNow):
        """The files in aNow that the last review before aBefore did not see, or None when all were seen."""
        # Without a review, the code that needs none is the code the session, or the earlier claim, started from.
        seen = review(aBefore) or (aRecords[used] if used >= 0 else since[0] if aBefore else None)
        if seen is None:
            return 'no review ran in this session'
        files = changed(seen.get('tree'), aNow)
        return ('changed since the last review: ' + ', '.join(files[:5]) + (f' and {len(files) - 5} more' if len(files) > 5 else '')) if files else None
    both = ('so invoke the ai-native-review skill on the full diff, then ai-native-verify. A changed file that is not code: '
            'remove it, or let Git ignore it')
    verify = max((i for i, r in enumerate(since) if r['skill'] == 'ai-native-verify'), default=None)
    # A code change after verify started is part of verification (a check added, a fix reversed to prove it and restored).
    before = verify is not None and unseen(verify, since[verify].get('tree'))
    if verify is not None and not before:
        return ''
    now = unseen(len(since), aTree())
    if verify is None:
        return f'{now}, {both}' if now else 'invoke the ai-native-verify skill first'
    if not now and review(len(since)) is not review(verify):
        return 'the review of the last code change ran after verify, so invoke the ai-native-verify skill again'
    return f'{now or before}, {both}'


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
                        bodies, here = [], ''
                        outer = expandVars(HEREDOC.sub(lambda m: bodies.append(m.group()) or f'\0{len(bodies) - 1}\0',
                                                       str(args.get('command') or '').replace('\0', '')))
                        for part in re.split(r'&&|\|\||[;|\n]', outer):
                            segment = re.sub(r'\0(\d+)\0', lambda m: bodies[int(m.group(1))], part)
                            moved = re.match(r'\s*(?:cd|pushd)\s+["\']?([^\s"\']+)["\']?\s*$', part)
                            if moved:
                                # After a cd into a change folder, a bare state.md is that change's state file.
                                here = moved.group(1) if re.search(r'\.sdlc[\\/]+changes[\\/]+[\w.-]+$', moved.group(1)) else ''
                                continue
                            if here and re.search(r'(?<![\w/\\.-])\.?/?state\.md(?![\w.])', segment):
                                segment = re.sub(r'(?<![\w/\\.-])\.?/?(state\.md)(?![\w.])', lambda m: f'{here}/state.md', segment)
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


def gitIgnores(aRoot, aTarget):
    """Whether Git ignores the target for a reason inside the project: a repository further up that ignores the
    whole project says nothing about the project's files."""
    try:
        ignored = lambda aPath: subprocess.run(['git', '-C', str(aRoot), 'check-ignore', '-q', '--', str(aPath)],
                                               capture_output=True, timeout=10).returncode == 0
        return bool(aTarget) and ignored(aTarget) and not ignored(aRoot)
    except (OSError, subprocess.SubprocessError):
        return False


def pending(aEvent):
    return logPath(aEvent).with_suffix('.claim')


def settle(aEvent):
    """Record a status: verified write that this hook let through, once the state file shows it."""
    try:
        if not pending(aEvent).is_file():
            return
        try:
            claim = json.loads(pending(aEvent).read_text(encoding='utf-8'))
            landed = STATUS.search(readState(Path(claim.pop('state'))))
        except (ValueError, KeyError, TypeError, AttributeError):
            # A note that cannot be read is dropped, and the claim it stood for counts as made.
            claim, landed = {'claim': [], 'tree': None}, True
        if landed:
            record(aEvent, **claim)
            pending(aEvent).unlink()
    except OSError:
        pass


def decide(aEvent, aAttempt=0):
    tool, args = aEvent.get('tool_name'), aEvent.get('tool_input') or {}
    settle(aEvent)
    detected, claim = '', claimsVerified(tool, args, projectRoots(aEvent))
    if tool in EDIT_TOOLS:
        target = str(args.get('file_path') or args.get('notebook_path') or '')
        if not inSdlc(target) and inScratch(target, projectRoots(aEvent)):
            return None
        lifecycle = inSdlc(target)
    elif tool in SHELL_TOOLS:
        detected = shellWritesOutsideSdlc(str(args.get('command') or ''), projectRoots(aEvent))
        lifecycle = not detected
        detected = f' Detected write: {detected[:80]}.' if detected else ''
    else:
        return None
    # A lifecycle write is checked only when it records status: verified.
    if lifecycle and not claim:
        return None
    try:
        routed, texts, path = readSession(aEvent)
    except OSError:
        return None
    if not routed:
        return None
    target = Path(str(args.get('file_path') or '')) if tool in EDIT_TOOLS and claim else path
    tree = lambda: fingerprint(projectRoot(aEvent))
    gap = verifyGap(readLog(aEvent), changesNamed(args), tree) if claim else ''
    ROUTED.append(True)
    state = readState(path)
    # A shell command that names no state file (a bare state.md after a cd) writes the active change's file.
    if tool in SHELL_TOOLS and not changesNamed(args) and STATUS.search(state):
        gap = ''
    stated = [(m.group(1) or m.group(2)).lower() for m in LANE.finditer('\n'.join(texts))]
    recorded = [r.lower() for r in re.findall(r'^lane:\s*(\w+)', state, re.M | re.I)]
    lanes = [l for l in stated[-1:] + recorded[:1] if l in LANES]
    # Text in the same message as this tool call can reach the transcript up to ~1 s after the hook starts.
    if not lanes and lifecycle:
        return None
    # A throwaway file is not project code: Git ignores it. Asked only when the write would be denied.
    if not aAttempt and tool in EDIT_TOOLS and gitIgnores(projectRoot(aEvent), str(args.get('file_path') or args.get('notebook_path') or '')):
        return None
    if not lanes and aAttempt < 20:
        time.sleep(0.1)
        return decide(aEvent, aAttempt + 1)
    if not lanes:
        return ('State the lane (Fast, Standard, or Controlled) in a message before changing files, for example "Lane: Fast".'
                + detected)
    # The stricter of the stated and the recorded lane applies, so stating a lower lane never clears a gate.
    lane = max(lanes, key=LANES.index)
    missing = [] if lifecycle else [g for g in GATES.get(lane, ()) if g not in approvedGates(state)]
    if not missing:
        if not claim or lane not in GATES:
            return None
        if gap:
            return f'{lane.capitalize()} work records status: verified only after this session ran review and verification: {gap}.'
        # Recorded once the write is seen to have reached the file (see settle): a refused write used nothing up.
        claimed = {'claim': sorted(changesNamed(args)), 'tree': tree()}
        try:
            pending(aEvent).write_text(json.dumps({'state': str(target or ''), **claimed}), encoding='utf-8')
        except OSError:
            record(aEvent, **claimed)
        return None
    where = "this session's change state.md (none read or written yet)"
    if path:
        where = f'.sdlc/changes/{path.parent.name}/state.md' + ('' if state else ' (not found: archived or moved?)')
    return (f'{lane.capitalize()} work changes no files outside .sdlc/ until {where} records these approvals: '
            f'{", ".join(missing)}. Invoke the next ai-native skill instead; write lifecycle files with separate commands. '
            'A throwaway file (a probe, a benchmark, captured output) goes in the system temp folder or a folder that Git ignores.'
            + detected)


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


def main_event(aEvent):
    """Handle one hook event and return what to print, or None."""
    kind = aEvent.get('hook_event_name')
    if kind in ('PostToolUse', 'UserPromptExpansion'):
        return note(aEvent)
    if kind == 'Stop':
        reason = decideStop(aEvent)
        return {'decision': 'block', 'reason': reason} if reason else None
    reason = decide(aEvent)
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                   'permissionDecisionReason': reason}} if reason else None


def main():
    event = None
    ROUTED.clear()
    try:
        event = json.load(sys.stdin)
        output = main_event(event)
    except Exception as error:
        failure = f'{type(error).__name__}: {error}'
        # A failure blocks nothing unless this session is known to use the plugin (ADR-003). Only a write is denied.
        if not ROUTED or event.get('hook_event_name') not in (None, 'PreToolUse'):
            sys.exit(f'ai-native-sdlc guard is inactive for this call ({failure}).')
        output = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': (
            f"The ai-native-sdlc guard failed ({failure}), so it cannot check this lane's approvals and denies the "
            'write. Retrying will not help: report this to the user, who can fix or disable the plugin hook.')}}
    if output:
        print(json.dumps(output))


if __name__ == '__main__':
    main()
