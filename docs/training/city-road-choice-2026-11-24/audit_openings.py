from pathlib import Path
import argparse,json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs
p=argparse.ArgumentParser();p.add_argument('--save',choices=['midpoint','final'],required=True);a=p.parse_args()
torch.set_num_threads(1);r=Path('docs/training/city-road-choice-2026-11-24')
b=MaskablePPO.load('output/training/city-road-choice-initial-01/start.zip',device='cpu');m=MaskablePPO.load(f'output/training/city-road-choice-fit-02/roads/{a.save}.zip',device='cpu');rows=[]
e=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=600,allow_bridges=True)
try:
 for seed in list(range(184000000,184000008))+list(range(185000000,185000008)):
  obs,_=e.reset(options=dict(scenario_seed=seed));mask=e.action_masks();x=masked_probs(b,obs,mask);y=masked_probs(m,obs,mask)
  row=dict(seed=seed,wait_error=float(abs(x[0]-y[0])),conditional_road_tv=float(np.abs(x[1:]/x[1:].sum()-y[1:]/y[1:].sum()).sum()/2));rows.append(row)
 assert max(x['wait_error'] for x in rows)<1e-6
finally:e.close()
result=dict(save=a.save,mean_conditional_road_tv=float(np.mean([x['conditional_road_tv'] for x in rows])),max_wait_error=max(x['wait_error'] for x in rows),rows=rows)
(r/f'{a.save}-opening-audit.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
