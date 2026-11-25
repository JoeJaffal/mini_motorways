from pathlib import Path
import subprocess,sys,os,time,json
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24';env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
for _ in range(720):
 if (rec/'longer-reviews-complete.json').exists() and (out/'city-strategy-wide-pilot-03/complete.json').exists():break
 time.sleep(10)
else:raise TimeoutError('Dependencies did not complete')
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],env=env,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
for kind in ('midpoint','final'):
 candidate=str(out/f'city-strategy-wide-pilot-03/{kind}.zip');name=f'city-strategy-wide-development-{kind}-03'
 run(name,['training/evaluate_city_service.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',candidate,'--output',str(out/name),'--games','32','--seed','950241','--workers','8'])
 run(name+'-comparison',[str(rec/'compare.py'),'--parent','output/training/city-strategy-development-parent-01','--candidate',str(out/name),'--output',str(rec/f'wide-{kind}-comparison-03.json')])
 run(name+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',candidate,'--output',str(rec/f'wide-{kind}-audit-03.json')])
(rec/'wide-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
