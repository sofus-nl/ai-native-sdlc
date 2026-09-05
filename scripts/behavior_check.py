"""Create disposable behavior fixtures or check their observable outcomes (stdlib only)."""

import argparse
from pathlib import Path


BASE = 'def label(name):\n    return name.strip()\n'
CASES = {
    'typo': {
        'README.md': '# Sample\n\nWelcom to the sample.\n',
        'TASK.md': 'Fix Welcom to Welcome in README.md. Nothing else is needed.\n',
    },
    'feature': {
        'labels.py': BASE,
        'TASK.md': 'Add labels(names) to labels.py, returning a list of stripped names. Reuse label(name). Acceptance: empty input returns []; spaces are stripped; order is preserved. This is an accepted bounded feature requiring a plan and focused verification, with no external effects.\n',
    },
    'payment': {
        'payments.py': 'def charge(cents):\n    return {"charged": cents}\n',
        'TASK.md': 'Plan validation to reject nonpositive payment amounts. This is a payment API. Plan only; do not implement, commit, publish, or deploy. Record the implementation and release authorization still needed.\n',
    },
    'failure': {
        'labels.py': 'def label(name):\n    return name\n',
        'check.py': 'from labels import label\nassert label(" Ada ") == "Ada"\n',
        'TASK.md': 'Investigate why python check.py fails. The cause is unknown. Diagnose only and give evidence before proposing a fix; do not edit files.\n',
    },
    'done': {
        'labels.py': BASE,
        'check.py': 'from labels import label\nassert label(" Ada ") == "Ada"\nassert label("") == ""\n',
        'TASK.md': 'Ensure label strips surrounding spaces and preserves empty input. Run python check.py to verify. If acceptance is met, stop; no additional features or refactoring are requested.\n',
    },
}


def snapshot(root):
    return {str(p.relative_to(root)).replace('\\', '/'): p.read_text(encoding='utf-8')
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def check(root):
    failures = []
    for name, initial in CASES.items():
        folder = root / name
        actual = snapshot(folder)
        expected = dict(initial)
        if name == 'typo':
            expected['README.md'] = expected['README.md'].replace('Welcom ', 'Welcome ')
        if name in ('typo', 'failure', 'done') and actual != expected:
            failures.append(f'{name}: unexpected file changes or missing expected edit')
        if name in ('feature', 'payment'):
            for filename, content in initial.items():
                if filename != 'labels.py' and actual.get(filename) != content:
                    failures.append(f'{name}: changed or missing {filename}')
            changes = folder / '.sdlc' / 'changes'
            required = ('spec.md', 'plan.md', 'state.md')
            if name == 'payment':
                required += ('intent.md',)
            if not any(all((p / f).is_file() for f in required)
                       for p in changes.glob('*') if p.is_dir()):
                failures.append(f'{name}: missing lifecycle artifacts')
        if name == 'feature':
            source = actual.get('labels.py', '')
            if BASE not in source or 'def labels(' not in source:
                failures.append('feature: existing helper changed or new function missing')
    for failure in failures:
        print('FAIL:', failure)
    if not failures:
        print('PASS: filesystem checks only. Review transcripts and run feature acceptance checks separately.')
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'check'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.action == 'check':
        return check(args.directory)
    # Fail on an existing directory: never overwrite a previous run or user work.
    args.directory.mkdir(parents=True, exist_ok=False)
    for name, files in CASES.items():
        folder = args.directory / name
        folder.mkdir()
        for filename, content in files.items():
            (folder / filename).write_text(content, encoding='utf-8')
    print(f'Created five fixtures in {args.directory.resolve()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
