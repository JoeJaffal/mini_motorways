from pathlib import Path
import subprocess,sys,os,time,json
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24';env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'));dll='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll'
def wait_for(path):
 for _ in range(720):
  if path.exists():return
  time.sleep(10)
 raise TimeoutError(str(path))
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],env=env,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
wait_for(rec/'wide-reviews-complete.json')
for kind in ('midpoint','final'):
 candidate=out/f'city-strategy-mixed-pilot-01/{kind}.zip';wait_for(candidate)
 name=f'city-strategy-mixed-development-{kind}-01'
 run(name,['training/evaluate_city_service.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--games','32','--seed','950241','--workers','8'])
 for reference,label in [('city-strategy-development-parent-01','parent'),('city-strategy-wide-development-final-03','wide')]:
  run(name+'-comparison-'+label,[str(rec/'compare.py'),'--parent',str(out/reference),'--candidate',str(out/name),'--output',str(rec/f'mixed-{kind}-comparison-{label}-01.json')])
 run(name+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'mixed-{kind}-audit-01.json')])
 name=f'city-strategy-mixed-skill-{kind}-01'
 run(name,['training/evaluate_city_curriculum.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--count','16','--seed-start','141000000','--workers','8'])
(rec/'mixed-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
