"""Check source-control hygiene, local Markdown links and Unity source metadata.

Checks indexed and non-ignored new files, not local ignored build caches. Uses
only Python's standard library and Git; run from any working directory.
"""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


def main():
    root = Path(__file__).resolve().parents[1]
    output = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=root,
    )
    files = sorted(set(output.decode('utf-8').rstrip('\0').split('\0')))
    failures = []
    ignored_parts = {
        'Library', 'Temp', 'Obj', 'Logs', 'UserSettings', 'Builds',
        'bin', 'obj', '__pycache__', 'PrivateExtracts', 'AssetInspection',
        'ReferenceRuns', 'MotorwaysResearch', 'tmp', 'output',
    }
    binary_suffixes = {'.exe', '.dll', '.pdb'}
    markdown_count = 0
    unity_guids = {}
    for name in files:
        relative = Path(name)
        path = root / relative
        if ignored_parts.intersection(relative.parts) or path.suffix.lower() in binary_suffixes:
            failures.append(f'Generated/private file selected for Git: {name}')
        if relative.name.startswith('gameJournal_') and relative.suffix == '.dat':
            failures.append(f'Raw original journal selected for Git: {name}')
        if not path.is_file():
            failures.append(f'Indexed file missing from working tree: {name}')
            continue
        if name.startswith('simulation/Assets/') and relative.suffix == '.cs':
            if name + '.meta' not in files:
                failures.append(f'Missing Unity metadata: {name}.meta')
        if name.startswith('simulation/Assets/') and relative.suffix == '.meta':
            match = re.search(r'^guid: ([0-9a-f]{32})$', path.read_text(), re.MULTILINE)
            if not match:
                failures.append(f'Missing or invalid Unity GUID: {name}')
            elif match.group(1) in unity_guids:
                failures.append(f'Duplicate Unity GUID: {name} and {unity_guids[match.group(1)]}')
            else:
                unity_guids[match.group(1)] = name
        if relative.suffix.lower() != '.md':
            continue
        markdown_count += 1
        content = path.read_text(encoding='utf-8-sig')
        for target in re.findall(r'\[[^\]]*\]\(([^\n)]+)\)', content):
            target = target.strip().split(' "', 1)[0].strip('<>')
            if target.startswith('#') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            target = unquote(target.split('#', 1)[0])
            if target and not (path.parent / target).exists():
                failures.append(f'Broken local link in {name}: {target}')
    if failures:
        raise SystemExit('\n'.join(failures))
    print(f'PASS: {len(files)} source files, {markdown_count} Markdown documents; '
          'no selected caches/private binaries, broken local links or missing/duplicate Unity metadata.')


if __name__ == '__main__':
    main()
