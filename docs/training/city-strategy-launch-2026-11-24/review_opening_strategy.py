from pathlib import Path
import subprocess,sys,os,json,time
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for label in ('midpoint','final'):
 candidate=out/f'city-strategy-opening-01/segment-001/{label}.zip'
 for _ in range(720):
  if candidate.exists():break
  time.sleep(10)
 else:raise TimeoutError(str(candidate))
 names=[]
 for suffix,games,seed,reference in [('development',32,950241,'city-strategy-development-parent-01'),('broader-development',64,950242,'city-strategy-confirmation-02')]:
  name=f'city-strategy-opening-{label}-{suffix}-01';names.append(out/name)
  run(name,['training/evaluate_city_service.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',str(candidate),'--output',str(out/name),'--games',str(games),'--seed',str(seed),'--workers','8'])
  run(name+'-comparison',[str(rec/'compare.py'),'--parent',str(out/reference),'--candidate',str(out/name),'--output',str(rec/f'opening-{label}-{suffix}-comparison.json')])
 run(f'opening-{label}-pooled',[str(rec/'pool_development.py'),'--references',str(out/'city-strategy-development-parent-01'),str(out/'city-strategy-confirmation-02'),'--candidates',*map(str,names),'--output',str(rec/f'opening-{label}-pooled-development.json')])
 name=f'city-strategy-opening-{label}-skill-01'
 run(name,['training/evaluate_city_curriculum.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',str(candidate),'--output',str(out/name),'--count','16','--seed-start','141000000','--workers','8'])
 run(name+'-audit',[str(rec/'audit_opening_strategy.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'opening-{label}-audit.json')])
(rec/'opening-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
