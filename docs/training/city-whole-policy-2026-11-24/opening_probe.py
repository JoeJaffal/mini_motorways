from pathlib import Path
import json,torch,numpy as np
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from sb3_contrib import MaskablePPO
import audit_city_service as audit
from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256
models={'reference':'output/training/city-strategy-wide-initial-01/start.zip','midpoint':'output/training/city-whole-fit-01/whole/midpoint.zip','final':'output/training/city-whole-fit-01/whole/final.zip'}
def worker(jobs):
 torch.set_num_threads(1);loaded={k:MaskablePPO.load(v,device='cpu') for k,v in models.items()};holder=[]
 class Capture(CityRoadEnv):
  def __init__(self,*args,**kwargs):
   super().__init__(*args,**kwargs);self.first_delivery=None;holder[:]=[self]
  def step(self,action):
   result=super().step(action)
   if self.first_delivery is None and result[1]>0:self.first_delivery=self.raw['time']
   return result
 audit.CityRoadEnv=Capture;rows=[]
 for action_seed in jobs:
  for label,m in loaded.items():
   r=audit.trace('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',m,184000000,action_seed,estimate=False,horizon=180,allow_bridges=True)
   rows.append(dict(model=label,action_seed=action_seed,score=r['trips'],first_delivery=holder[0].first_delivery))
  print('OPENING',action_seed,[(x['model'],x['score']) for x in rows[-3:]],flush=True)
 return rows
if __name__=='__main__':
 rec=Path('docs/training/city-whole-policy-2026-11-24');jobs=list(range(194000,194032))
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  futures=[pool.submit(worker,jobs[i::8]) for i in range(8)];rows=[x for f in futures for x in f.result()]
 result={}
 for label in models:
  group=[x for x in rows if x['model']==label];result[label]=dict(games=len(group),scoring=sum(x['score']>0 for x in group),mean_score=float(np.mean([x['score'] for x in group])),delivery_by60=sum(x['first_delivery'] is not None and x['first_delivery']<=60 for x in group))
 (rec/'opening-probe.json').write_text(json.dumps(dict(seed=184000000,horizon=180,scope='One training-layout opening reliability; not cross-city generalization',checkpoints={k:dict(path=v,sha256=sha256(Path(v))) for k,v in models.items()},results=result,rows=rows),indent=2)+'\n');print(result)
