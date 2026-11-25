from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path.cwd();out=root/'docs/training/city-strategy-launch-2026-11-24'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,kind):
 target=out/kind/p.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
artifacts=[]
for path in sorted((root/'output/training').glob('city-strategy-*')):
 for f in ([path] if path.is_file() else sorted(path.rglob('*'))):
  if not f.is_file():continue
  if f.suffix=='.zip':artifacts.append(dict(path=str(f.relative_to(root)),sha256=sha(f),bytes=f.stat().st_size,local_only=True))
  elif f.suffix in {'.json','.jsonl','.csv','.log','.txt'}:copy(f,'measurements')
for f in root.glob('output/city-strategy-*.log'):copy(f,'measurements')
for f in (root/'training').glob('*.py'):copy(f,'source')
for f in (root/'simulation/Assets/Simulation').glob('*.cs'):copy(f,'source')
for name in ('simulation/Headless/Program.cs','simulation/Headless/TrafficHost.csproj'):copy(root/name,'source')
for name in ['output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','output/training/city-five-stage-cold-initial-01/candidate.zip','output/city-strategy-short-delay-build-01/bin/TrafficHost/release/TrafficHost.dll','output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll']:
 f=root/name;artifacts.append(dict(path=name,sha256=sha(f),bytes=f.stat().st_size,local_only=True))
(out/'local-artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
(out/'source-context.json').write_text(json.dumps(dict(branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),note='Current dirty source snapshot includes inherited code. Ongoing run snapshots are provisional; weights/binaries remain local.'),indent=2)+'\n')
manifest=[dict(path=str(f.relative_to(out)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(out.rglob('*')) if f.is_file() and f.name not in {'manifest.json','wide-queue.json'} and '__pycache__' not in f.parts and 'live-run' not in f.relative_to(out).parts]
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(dict(files=len(manifest),bytes=sum(x['bytes'] for x in manifest),local_artifacts=len(artifacts)))
