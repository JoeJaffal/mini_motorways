"""Frozen city transfer and held-out practice reviews of the bounded candidates."""
from pathlib import Path
import os,subprocess,sys,time
root=Path(__file__).resolve().parents[3];os.chdir(root)
b=root/'output/training';dll=root/'output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')

def wait_complete(name):
 deadline=time.monotonic()+7200
 while not (b/name/'complete.json').exists():
  if time.monotonic()>deadline:raise RuntimeError('Stage did not finish: '+name)
  time.sleep(5)
 return b/name/'final.zip'

def launch(script,name,paths,extra):
 out=b/name;log=out.with_suffix('.log').open('x')
 job=subprocess.Popen([sys.executable,'-u','training/'+script,'--dll',str(dll),'--checkpoints',*map(str,paths),'--output',str(out),*extra],env=env,stdout=log,stderr=subprocess.STDOUT)
 return job,log

pre=wait_complete('city-five-stage-waiting-03')
jobs=[launch('evaluate_city_service.py','city-five-stage-city-preexploration-01',[pre],['--games','32','--seed','826341'])]
final=wait_complete('city-five-stage-mixed-01')
traffic=b/'city-five-stage-traffic-01/final.zip'
jobs.append(launch('evaluate_city_service.py','city-five-stage-city-final-01',[traffic,final],['--games','32','--seed','826341']))
initial=b/'city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip'
jobs.append(launch('evaluate_city_curriculum.py','city-five-stage-confirmation-01',[initial,pre,final],['--count','8','--workers','8','--seed-start','118300000','--controls']))
for job,log in jobs:
 result=job.wait();log.close()
 if result:raise RuntimeError('A frozen final review failed')
print('All final reviews completed.',flush=True)
