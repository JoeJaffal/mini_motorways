"""Archive small evidence and exact sources; run from repository root after reviews."""
from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path.cwd();out=root/'docs/training/five-stage-city-learning-2026-11-23'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,category):
 dst=out/category/p.relative_to(root);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
artifacts=[]
for p in sorted((root/'output/training').glob('city-five-stage-*')):
 for f in ([p] if p.is_file() else sorted(p.rglob('*'))):
  if not f.is_file():continue
  if f.suffix=='.zip':artifacts.append(dict(path=str(f.relative_to(root)),sha256=sha(f),bytes=f.stat().st_size,local_only=True))
  elif f.suffix in {'.json','.jsonl','.csv','.log','.txt'}:copy(f,'measurements')
for f in [root/'output/city-five-stage-build-01.log']:copy(f,'measurements')
# Local training modules and simulator sources needed to reproduce checkpoint classes
# and native fixture behavior. These include inherited work; snapshots are NOT a
# claim that every line was introduced by this experiment.
for pattern in ['training/*.py','simulation/Assets/Simulation/*.cs','simulation/Assets/Simulation/TrafficPractice.cs.meta','simulation/Headless/*.cs','simulation/Headless/*.csproj']:
 for p in root.glob(pattern):copy(p,'source')
for name in ['output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll','output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip','output/training/traffic-live-junction-host-01/simulation/Assets/Simulation/TrafficPractice.cs']:
 p=root/name;artifacts.append(dict(path=name,sha256=sha(p),bytes=p.stat().st_size,local_only=True))
(out/'local-artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
(out/'source-context.json').write_text(json.dumps(dict(branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),note='Dirty checkout, pre-existing edits preserved. Snapshots include inherited work. No weights or binaries archived.'),indent=2)+'\n')
(out/'working-tree-status.txt').write_text(subprocess.check_output(['git','status','--short'],text=True))
# Entire relevant native diff includes pre-existing changes, explicitly labeled.
(out/'native-tracked-context.diff').write_text(subprocess.check_output(['git','diff','--','simulation/Assets/Simulation','simulation/Headless'],text=True))
manifest=[dict(path=str(p.relative_to(out)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for row in manifest:assert sha(out/row['path'])==row['sha256']
print(json.dumps(dict(files=len(manifest),bytes=sum(r['bytes'] for r in manifest),local_artifacts=len(artifacts))))
