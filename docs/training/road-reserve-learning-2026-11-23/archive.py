"""Preserve local experiment evidence without checkpoint/binary payloads."""
from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path.cwd();out=root/'docs/training/road-reserve-learning-2026-11-23'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,kind):
 dst=out/kind/p.relative_to(root);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
local=[]
for p in sorted((root/'output/training').glob('city-road-reserve-*')):
 for f in ([p] if p.is_file() else sorted(p.rglob('*'))):
  if not f.is_file():continue
  if f.suffix=='.zip':local.append(dict(path=str(f.relative_to(root)),sha256=sha(f),bytes=f.stat().st_size))
  elif f.suffix in {'.json','.jsonl','.csv','.log','.txt'}:copy(f,'measurements')
for p in root.glob('output/city-road-reserve-*.log'):copy(p,'measurements')
for pattern in ['training/*.py','simulation/Assets/Simulation/*.cs','simulation/Headless/*.cs','simulation/Headless/*.csproj']:
 for p in root.glob(pattern):copy(p,'source')
for name in ['output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','output/training/city-five-stage-cold-initial-01/candidate.zip','output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip']:
 p=root/name;local.append(dict(path=name,sha256=sha(p),bytes=p.stat().st_size))
(out/'local-only-artifacts.json').write_text(json.dumps(local,indent=2)+'\n')
(out/'source-context.json').write_text(json.dumps(dict(branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),note='Dirty checkout, pre-existing work preserved. Source snapshot includes inherited code, not only this task.'),indent=2)+'\n')
manifest=[dict(path=str(p.relative_to(out)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
assert all(sha(out/r['path'])==r['sha256'] for r in manifest)
print(dict(files=len(manifest),bytes=sum(r['bytes'] for r in manifest)))
