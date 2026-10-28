"""Archive a completed investigation's small evidence; never includes weights."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import re
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def prune_replay_duplicates(value):
    if isinstance(value,dict):return {k:prune_replay_duplicates(v) for k,v in value.items() if k!='episode_replay'}
    if isinstance(value,list):return [prune_replay_duplicates(v) for v in value]
    return value


def copy_evidence(source,target,provenance):
    target.parent.mkdir(parents=True,exist_ok=True)
    raw=source.read_bytes();changed=False;rewritten=None;transformations=[]
    if b'"episode_replay"' in raw:
        text=raw.decode('utf-8-sig')
        if source.suffix=='.json':
            rewritten=json.dumps(prune_replay_duplicates(json.loads(text)),indent=2)+'\n';changed=True
        elif source.suffix=='.jsonl':
            rewritten=''.join(json.dumps(prune_replay_duplicates(json.loads(l)))+'\n' for l in text.splitlines());changed=True
        elif source.suffix=='.log':
            lines=[]
            for line in text.splitlines():
                if line.startswith('RESULT '):
                    try:line='RESULT '+json.dumps(prune_replay_duplicates(json.loads(line[7:])));changed=True
                    except json.JSONDecodeError:pass
                lines.append(line)
            rewritten='\n'.join(lines)+'\n'
    if changed:transformations.append('Removed duplicated episode_replay keys; dedicated exact replay files retained')
    if source.suffix=='.log' and source.name.startswith('unity-'):
        text=rewritten if rewritten is not None else raw.decode('utf-8-sig')
        private=re.compile(r'licens|(?:session|correlation|machine)\s*id\s*:|UnityPers|access.?token|cbmMachineId',re.I)
        sanitized='\n'.join('[Unity runtime identity/licensing line redacted]' if private.search(line) else line for line in text.splitlines())+'\n'
        if any(private.search(line) for line in text.splitlines()):
            rewritten=sanitized;changed=True;transformations.append('Redacted Unity runtime device/session/licensing identifiers')
    if changed:target.write_text(rewritten,encoding='utf-8')
    else:shutil.copyfile(source,target)
    provenance[str(target)]=dict(source=str(source),source_sha256=hashlib.sha256(raw).hexdigest(),
                               transformation='; '.join(transformations) if transformations else 'byte-for-byte copy')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--run',action='append')
    p.add_argument('--experiments',type=Path)
    p.add_argument('--verify',action='store_true',help='Read-only verification of evidence and report manifests')
    a=p.parse_args()
    if a.verify:
        manifests=[(a.destination/'manifest.json',a.destination)]
        report=a.destination/'report-manifest.json'
        if report.exists():manifests.append((report,a.destination.parent))
        count=0
        for path,base in manifests:
            data=json.loads(path.read_text());entries=data['files'] if isinstance(data,dict) else data
            for entry in entries:
                f=base/entry['path']
                if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=entry['sha256']:
                    raise SystemExit(f'Archive mismatch: {f}')
                count+=1
        print(f'PASS: {count} evidence/report manifest entries verified; no training or writes')
        return
    if not a.run or a.experiments is None:p.error('Archiving requires --run and --experiments')
    if a.destination.exists():p.error('Choose a fresh archive directory')
    for run in a.run:
        if not (ROOT/'output/training'/run/'summary.json').exists():p.error(f'Incomplete run: {run}')
    a.destination.mkdir(parents=True)
    provenance={}
    for run in a.run:
        source=ROOT/'output/training'/run
        for f in source.rglob('*'):
            if not f.is_file() or f.suffix not in {'.json','.jsonl','.csv','.py'}:continue
            # Per-seed duplicates are redundant; keep the overall exact best game.
            if 'seeds' in f.relative_to(source).parts:continue
            target=a.destination/'runs'/run/f.relative_to(source)
            copy_evidence(f,target,provenance)
    for f in a.experiments.rglob('*'):
        if not f.is_file() or f.suffix not in {'.json','.jsonl','.log','.err','.txt'}:continue
        target=a.destination/'experiments'/f.relative_to(a.experiments)
        copy_evidence(f,target,provenance)
    files=[dict(path=f.relative_to(a.destination).as_posix(),bytes=f.stat().st_size,
                sha256=hashlib.sha256(f.read_bytes()).hexdigest(),**provenance[str(f)]) for f in sorted(a.destination.rglob('*')) if f.is_file()]
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),runs=a.run,files=files,
                  weights='Local-only output/training/<run>/*.zip; intentionally excluded',
                  purpose='Completed three-hour investigation, including negative results and exact ordinary-command replays')
    (a.destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Archived {len(files)} evidence files to {a.destination}')


if __name__=='__main__':main()
