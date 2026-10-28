"""Archive a completed investigation's small evidence; never includes weights."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--run',action='append',required=True)
    p.add_argument('--experiments',type=Path,required=True)
    a=p.parse_args()
    if a.destination.exists():p.error('Choose a fresh archive directory')
    for run in a.run:
        if not (ROOT/'output/training'/run/'summary.json').exists():p.error(f'Incomplete run: {run}')
    a.destination.mkdir(parents=True)
    for run in a.run:
        source=ROOT/'output/training'/run
        for f in source.rglob('*'):
            if not f.is_file() or f.suffix not in {'.json','.jsonl','.csv','.py'}:continue
            # Per-seed duplicates are redundant; keep the overall exact best game.
            if 'seeds' in f.relative_to(source).parts:continue
            target=a.destination/'runs'/run/f.relative_to(source)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    for f in a.experiments.rglob('*'):
        if not f.is_file() or f.suffix not in {'.json','.jsonl','.log','.err','.txt'}:continue
        target=a.destination/'experiments'/f.relative_to(a.experiments)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    files=[dict(path=f.relative_to(a.destination).as_posix(),bytes=f.stat().st_size,
                sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in sorted(a.destination.rglob('*')) if f.is_file()]
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),runs=a.run,files=files,
                  weights='Local-only output/training/<run>/*.zip; intentionally excluded',
                  purpose='Completed three-hour investigation, including negative results and exact ordinary-command replays')
    (a.destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Archived {len(files)} evidence files to {a.destination}')


if __name__=='__main__':main()
