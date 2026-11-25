"""Archive small training evidence for documentation; never runs a model.

Existing snapshots are immutable. Use a new destination for revised evidence.
Checkpoints, simulator binaries and private reference files are never copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--verify',action='store_true',help='Verify existing archive without writes')
    args=parser.parse_args()
    destination=args.destination.resolve()
    if args.verify:
        manifest=json.loads((destination/'manifest.json').read_text())
        for item in manifest:
            path=destination/item['archived']
            if path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
                raise RuntimeError(f'Archive mismatch: {path}')
        print(f'PASS: {len(manifest)} archived files match SHA-256 hashes')
        return
    destination.mkdir(parents=True,exist_ok=False)
    manifest=[]
    def copy(source,target):
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        manifest.append(dict(source=source.relative_to(ROOT).as_posix(),
                             archived=target.relative_to(destination).as_posix(),
                             bytes=source.stat().st_size,
                             sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    for run in sorted((ROOT/'output/training').iterdir()):
        if not run.is_dir():continue
        names=['config.json','summary.json','status.json','seed-summary.json',
               'episodes.jsonl','progress.csv','monitor.csv','best-game.json']
        files=[run/name for name in names if (run/name).is_file()]
        files+=sorted(run.glob('*.monitor.csv'))
        for source in sorted(set(files)):
            copy(source,destination/'runs'/run.name/source.name)
    benchmark=ROOT/'output/benchmarks/parallel-first/results.json'
    if benchmark.exists():copy(benchmark,destination/'parallel-benchmark.json')
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Archived {len(manifest)} evidence files; no training performed: {destination}')


if __name__=='__main__':main()
