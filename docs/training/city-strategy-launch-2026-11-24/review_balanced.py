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
wait_for(rec/'balanced-launch.json')
for label,path in [('mixed-midpoint','city-strategy-mixed-pilot-01/midpoint.zip'),('balanced-midpoint','city-strategy-balanced-pilot-01/midpoint.zip'),('balanced-final','city-strategy-balanced-pilot-01/final.zip')]:
 candidate=out/path;wait_for(candidate);name='city-strategy-'+label+'-development-02'
 run(name,['training/evaluate_city_service.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--games','32','--seed','950241','--workers','8'])
 for reference,ref in [('city-strategy-development-parent-01','parent'),('city-strategy-wide-development-final-03','wide')]:
  run(name+'-comparison-'+ref,[str(rec/'compare.py'),'--parent',str(out/reference),'--candidate',str(out/name),'--output',str(rec/f'{label}-comparison-{ref}-02.json')])
 run(name+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'{label}-audit-02.json')])
 name='city-strategy-'+label+'-skill-02'
 run(name,['training/evaluate_city_curriculum.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--count','16','--seed-start','141000000','--workers','8'])
(rec/'balanced-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
