from pathlib import Path
import subprocess,sys,os,time,json
root=Path.cwd(); out=root/'output/training'; rec=root/'docs/training/city-strategy-launch-2026-11-24'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
parent='output/training/city-five-stage-cold-initial-01/candidate.zip'; first='output/training/city-strategy-pilot-01/final.zip'; candidate='output/training/city-strategy-longer-pilot-02/final.zip'; dll='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll'
for _ in range(180):
 if (root/'output/training/city-strategy-longer-pilot-02/complete.json').exists():break
 os.kill(150630,0);time.sleep(10)
else:raise TimeoutError('Continuation incomplete')
def run(name, command):
 with (out/(name+'.log')).open('x') as stream:subprocess.run([sys.executable,'-u',*command],cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
run('city-strategy-longer-audit-02',[str(rec/'audit.py'),'--candidate',candidate,'--output',str(rec/'longer-audit-02.json')])
run('city-strategy-longer-development-02',['training/evaluate_city_service.py','--dll',dll,'--checkpoints',candidate,'--output',str(out/'city-strategy-longer-development-02'),'--games','32','--seed','950241','--workers','8'])
run('city-strategy-longer-review-02',['training/evaluate_city_service.py','--dll',dll,'--checkpoints',parent,first,candidate,'--output',str(out/'city-strategy-longer-review-02'),'--games','32','--seed','950244','--workers','8','--horizon','1200'])
run('city-strategy-skill-review-02',['training/evaluate_city_curriculum.py','--dll',dll,'--checkpoints',parent,first,candidate,'--output',str(out/'city-strategy-skill-review-02'),'--count','16','--seed-start','141000000','--workers','8','--controls'])
(rec/'longer-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
