from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path.cwd();rec=root/'docs/training/small-city-service-2026-11-24';artifacts=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in sorted((root/'output/training').glob('small-city-*')):
 for f in ([p] if p.is_file() else p.rglob('*')):
  if not f.is_file():continue
  if f.suffix=='.zip':artifacts.append(dict(path=str(f.relative_to(root)),sha256=sha(f),local_only=True))
  elif f.suffix in ('.json','.jsonl','.csv','.log'):
   dest=rec/'measurements'/f.relative_to(root);dest.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(f,dest)
for name in ['output/training/city-whole-initial-01/start.zip','output/training/city-whole-fit-01/whole/final.zip','output/training/city-strategy-wide-initial-01/start.zip','output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll']:
 f=root/name;artifacts.append(dict(path=name,sha256=sha(f),local_only=True))
for name in ['city_curriculum.py','city_strategy_policy.py','city_wide_strategy_policy.py','city_whole_strategy_policy.py','city_repeated_seeds.py','train_city_curriculum.py']:
 dest=rec/'current-source'/name;dest.parent.mkdir(exist_ok=True);shutil.copy2(root/'training'/name,dest)

for f in (root/'simulation/Assets/Simulation').glob('*.cs'):
 dest=rec/'native-source'/f.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(f,dest)
for build in ['small-city-service-build-01','small-city-offset-build-01']:
 f=root/f'output/{build}/bin/TrafficHost/release/TrafficHost.dll';artifacts.append(dict(path=str(f.relative_to(root)),sha256=sha(f),local_only=True))

(rec/'local-artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
(rec/'source-context.json').write_text(json.dumps(dict(branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),note='Inherited dirty work preserved; runtime-source freezes this experiment; no weights or native binaries archived.'),indent=2)+'\n')
manifest=[dict(path=str(f.relative_to(rec)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(rec.rglob('*')) if f.is_file() and f.name!='manifest.json' and '__pycache__' not in f.parts]
(rec/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(dict(files=len(manifest),local_artifacts=len(artifacts)))
