from pathlib import Path
import subprocess,sys,os,json,time
from evaluate_city_service import summarize
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24';dll='output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
def wait(path):
 for _ in range(720):
  if path.exists():return
  time.sleep(10)
 raise TimeoutError(str(path))
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def extract(source,target,index):
 target.mkdir(exist_ok=False);s=json.loads((source/'summary.json').read_text());name=s['models'][index]
 rows=[dict(r,model=0) for r in map(json.loads,(source/'games.jsonl').read_text().splitlines()) if r['model']==index]
 s.update(models=[name],sha256={name:s['sha256'][name]},results=summarize(rows,1),derived_from=str(source),source_model_index=index)
 (target/'summary.json').write_text(json.dumps(s,indent=2)+'\n');(target/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows));(target/'suite.json').write_text((source/'suite.json').read_text())
wait(out/'city-strategy-bridge-longer-baseline-01/summary.json')
extract(out/'city-strategy-bridge-initial-development-01',out/'city-strategy-bridge-conserved-baseline-01',1)
extract(out/'city-strategy-bridge-longer-baseline-01',out/'city-strategy-bridge-conserved-longer-baseline-01',1)
for label in ('midpoint','final'):
 candidate=out/f'city-strategy-bridge-balanced-01/segment-001/{label}.zip';wait(candidate)
 for horizon,reference,own in [(600,'city-strategy-bridge-initial-development-01','city-strategy-bridge-conserved-baseline-01'),(1200,'city-strategy-bridge-longer-baseline-01','city-strategy-bridge-conserved-longer-baseline-01')]:
  name=f'city-strategy-bridge-{label}-{horizon}-development-01'
  run(name,['training/evaluate_city_service.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--games','32','--seed','950241','--workers','8','--horizon',str(horizon),'--allow-bridges'])
  for ref,tag in [(reference,'reference'),(own,'start')]:
   run(name+'-'+tag,[str(rec/'compare.py'),'--parent',str(out/ref),'--candidate',str(out/name),'--output',str(rec/f'bridge-{label}-{horizon}-comparison-{tag}.json')])
 name=f'city-strategy-bridge-{label}-skill-01'
 run(name,['training/evaluate_city_curriculum.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--count','16','--seed-start','141000000','--workers','8'])
 run(name+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'bridge-{label}-audit.json')])
(rec/'bridge-balanced-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
