"""Bounded pilot reviews only; never launches further training."""
from pathlib import Path
import subprocess,sys,os,json,time
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
def wait(path):
 for _ in range(720):
  if path.exists():return
  status=out/'city-strategy-recorded-city-01/status.json'
  if status.exists() and json.loads(status.read_text())['status'] in ('interrupted','failed','error','regression_stop'):
   raise RuntimeError('Trainer stopped before required checkpoint: '+str(path))
  time.sleep(10)
 raise TimeoutError(str(path))
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for label in ('midpoint','final'):
 candidate=out/f'city-strategy-recorded-city-01/segment-001/{label}.zip';wait(candidate)
 name=f'city-strategy-recorded-{label}-longer-01'
 run(name,['training/evaluate_city_service.py','--dll','output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',str(candidate),'--output',str(out/name),'--games','32','--seed','950241','--workers','8','--horizon','1200','--allow-bridges'])
 run(name+'-comparison',[str(rec/'compare.py'),'--parent',str(out/'city-strategy-bridge-longer-baseline-01'),'--candidate',str(out/name),'--output',str(rec/f'recorded-{label}-longer-comparison.json')])
 run(name+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'recorded-{label}-audit.json')])
(rec/'recorded-city-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
