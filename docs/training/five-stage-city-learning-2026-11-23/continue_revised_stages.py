"""Remaining bounded experiments after the diagnosed exploration failure."""
from pathlib import Path
import os,subprocess,sys,time
root=Path(__file__).resolve().parents[3];os.chdir(root)
base=root/'output/training';dll=root/'output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
parent=base/'city-five-stage-connections-02/final.zip'
deadline=time.monotonic()+1800
while not (parent.parent/'complete.json').exists():
 if time.monotonic()>deadline:raise RuntimeError('Higher-rate connection pilot did not finish')
 time.sleep(5)

def train(stage,name,seed,rollouts,rate,source):
 out=base/name
 with (base/(name+'.log')).open('x') as log:
  subprocess.run([sys.executable,'-u','training/train_city_curriculum.py','--dll',str(dll),'--parent',str(source),'--output',str(out),'--stage',stage,'--seed-start',str(seed),'--rollouts',str(rollouts),'--workers','16','--learning-rate',str(rate)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('COMPLETE | '+name,flush=True)
 return out/'final.zip'

parent=train('waiting','city-five-stage-waiting-02',115000000,8,.0003,parent)
initial=base/'city-five-stage-traffic-initial-01'
subprocess.run([sys.executable,'docs/training/five-stage-city-learning-2026-11-23/prepare_exploration.py','--dll',str(dll),'--parent',str(parent),'--output',str(initial),'--temperature','20'],env=env,check=True)
parent=train('traffic','city-five-stage-traffic-01',112000000,32,.0003,initial/'start.zip')
parent=train('mixed','city-five-stage-mixed-01',113000000,16,.00001,parent)
print('Bounded experiments finished; no promotion or long run is automatic.',flush=True)
