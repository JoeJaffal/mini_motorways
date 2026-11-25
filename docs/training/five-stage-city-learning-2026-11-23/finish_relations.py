"""Bounded mixed-city follow-up and frozen comparisons for the narrower repair."""
from pathlib import Path
import os,subprocess,sys,time
root=Path(__file__).resolve().parents[3];os.chdir(root)
b=root/'output/training';dll=root/'output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
parent=b/'city-five-stage-relations-01/final.zip'
deadline=time.monotonic()+3600
while not (parent.parent/'complete.json').exists():
 if time.monotonic()>deadline:raise RuntimeError('Relation training did not finish')
 time.sleep(5)

def launch(script,name,paths,extra):
 out=b/name;log=out.with_suffix('.log').open('x')
 p=subprocess.Popen([sys.executable,'-u','training/'+script,'--dll',str(dll),'--output',str(out),'--checkpoints',*map(str,paths),*extra],env=env,stdout=log,stderr=subprocess.STDOUT)
 return p,log

jobs=[launch('evaluate_city_curriculum.py','city-five-stage-relations-review-01',[parent],['--count','8','--workers','4'])]
out=b/'city-five-stage-relations-mixed-01'
with out.with_suffix('.log').open('x') as log:
 subprocess.run([sys.executable,'-u','training/train_city_curriculum.py','--dll',str(dll),'--parent',str(parent),'--output',str(out),'--stage','mixed','--seed-start','120000000','--rollouts','2','--workers','16','--learning-rate','.003','--collapse-forced-wait'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Mixed relation candidate saved.',flush=True)
final=out/'final.zip'
jobs.append(launch('evaluate_city_service.py','city-five-stage-relations-final-city-01',[parent,final],['--games','32','--seed','826341']))
original=b/'city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip'
initial=b/'city-five-stage-relations-initial-02/start.zip'
jobs.append(launch('evaluate_city_curriculum.py','city-five-stage-relations-confirmation-01',[original,initial,final],['--count','8','--workers','8','--seed-start','118400000','--controls']))
for p,log in jobs:
 code=p.wait();log.close()
 if code:raise RuntimeError('Relation review failed')
print('All relation candidate reviews completed.',flush=True)
