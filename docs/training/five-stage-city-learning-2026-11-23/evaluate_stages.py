"""Evaluate each saved stage on fixed paired development lessons."""
from pathlib import Path
import os,subprocess,sys,time
root=Path(__file__).resolve().parents[3];os.chdir(root)
b=root/'output/training';dll=root/'output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
traffic=['traffic-priority-established','traffic-priority-established-swap','traffic-junction-low-live','traffic-junction-high-live']
jobs=[('waiting-01',['midgame-network-delay','midgame-network-quiet']),('connections-02',['midgame-network-join','midgame-network-route']),('waiting-02',['midgame-network-delay','midgame-network-quiet']),('traffic-initial-01',traffic),('traffic-01',traffic)]
for name,lessons in jobs:
 run=b/('city-five-stage-'+name)
 source=run/('start.zip' if 'initial' in name else 'final.zip')
 ready=run/('config.json' if 'initial' in name else 'complete.json')
 deadline=time.monotonic()+3600
 while not ready.exists():
  if time.monotonic()>deadline:raise RuntimeError('Expected stage did not finish: '+name)
  time.sleep(5)
 output=b/('city-five-stage-'+name+'-review')
 with output.with_suffix('.log').open('x') as log:
  subprocess.run([sys.executable,'-u','training/evaluate_city_curriculum.py','--dll',str(dll),'--checkpoints',str(source),'--output',str(output),'--count','8','--workers','4','--lessons',*lessons],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('EVALUATED | '+name,flush=True)
