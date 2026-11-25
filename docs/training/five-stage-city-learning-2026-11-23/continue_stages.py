"""Run the remaining authorized bounded candidates; never promotes a checkpoint."""
from pathlib import Path
import os,subprocess,sys,time
root=Path(__file__).resolve().parents[3]
os.chdir(root)
base=root/'output/training'
dll=root/'output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
parent=base/'city-five-stage-connections-01/final.zip'
# The already-running connection pilot must complete successfully first.
deadline=time.monotonic()+1800
while not (parent.parent/'complete.json').exists():
 if time.monotonic()>deadline:raise RuntimeError('Connection pilot did not complete in the bounded wait')
 time.sleep(5)
for stage,seed in [('waiting',111000000),('traffic',112000000),('mixed',113000000)]:
 out=base/f'city-five-stage-{stage}-01'
 with (base/f'city-five-stage-{stage}-01.log').open('x') as log:
  subprocess.run([sys.executable,'-u','training/train_city_curriculum.py','--dll',str(dll),'--parent',str(parent),'--output',str(out),'--stage',stage,'--seed-start',str(seed),'--rollouts','16','--workers','16','--learning-rate','0.000001' if stage=='mixed' else '0.00001'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 parent=out/'final.zip'
 print(f'COMPLETE | {stage} | {parent}',flush=True)
print('All bounded candidate stages complete. Evaluation and promotion remain separate.',flush=True)
