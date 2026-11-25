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
wait_for(out/'city-strategy-short-delay-midpoint-easy-skill-01/summary.json')
for label in ('midpoint','final'):
 candidate=out/f'city-strategy-value-balance-01/segment-001/{label}.zip';wait_for(candidate);name='city-strategy-value-balance-'+label+'-development-01'
 run(name,['training/evaluate_city_service.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--games','32','--seed','950241','--workers','8'])
 for reference,ref in [('city-strategy-development-parent-01','parent'),('city-strategy-extension-midpoint-development-01','extension')]:
  run(name+'-comparison-'+ref,[str(rec/'compare.py'),'--parent',str(out/reference),'--candidate',str(out/name),'--output',str(rec/f'value-balance-{label}-comparison-{ref}-01.json')])
 run(name+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'value-balance-{label}-audit-01.json')])
 name='city-strategy-value-balance-'+label+'-skill-01'
 run(name,['training/evaluate_city_curriculum.py','--dll',dll,'--checkpoints',str(candidate),'--output',str(out/name),'--count','16','--seed-start','141000000','--workers','8'])
 name='city-strategy-value-balance-'+label+'-easy-skill-01'
 run(name,['training/evaluate_city_curriculum.py','--dll','output/city-strategy-short-delay-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints','output/training/city-strategy-balanced-extension-01/segment-001/midpoint.zip',str(candidate),'--output',str(out/name),'--lessons','midgame-network-reserve','--reserve-delay-seconds','2','--count','16','--seed-start','154300000','--controls','--workers','8'])
(rec/'value-balance-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
