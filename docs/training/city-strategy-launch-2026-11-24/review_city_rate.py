from pathlib import Path
import subprocess,sys,os,json,time
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for _ in range(720):
 if (rec/'city-only-reviews-complete.json').exists():break
 time.sleep(10)
else:raise TimeoutError('city-only reviews')
for _ in range(720):
 status=out/'city-strategy-city-rate-01/status.json'
 if status.exists() and json.loads(status.read_text()).get('phase')=='finished':break
 time.sleep(10)
else:raise TimeoutError('rate trainer finished')
for label in ('final',):
 candidate=out/f'city-strategy-city-rate-01/segment-001/{label}.zip'
 for _ in range(720):
  if candidate.exists():break
  time.sleep(10)
 else:raise TimeoutError(str(candidate))
 names=[]
 for suffix,games,seed,reference in [('development',32,950241,'city-strategy-development-parent-01'),('broader-development',64,950242,'city-strategy-confirmation-02')]:
  name=f'city-strategy-city-rate-{label}-{suffix}-01';names.append(out/name)
  run(name,['training/evaluate_city_service.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',str(candidate),'--output',str(out/name),'--games',str(games),'--seed',str(seed),'--workers','16'])
  run(name+'-comparison',[str(rec/'compare.py'),'--parent',str(out/reference),'--candidate',str(out/name),'--output',str(rec/f'city-rate-{label}-{suffix}-comparison.json')])
 run(f'city-rate-{label}-pooled',[str(rec/'pool_development.py'),'--references',str(out/'city-strategy-development-parent-01'),str(out/'city-strategy-confirmation-02'),'--candidates',*map(str,names),'--output',str(rec/f'city-rate-{label}-pooled-development.json')])
 name=f'city-strategy-city-rate-{label}-skill-01'
 run(name,['training/evaluate_city_curriculum.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',str(candidate),'--output',str(out/name),'--count','16','--seed-start','141000000','--workers','16'])
 run(name+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'city-rate-{label}-audit.json')])
(rec/'city-rate-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
