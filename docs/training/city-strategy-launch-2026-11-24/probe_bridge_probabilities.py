from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv,FORWARD
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();rec=root/'docs/training/city-strategy-launch-2026-11-24';torch.set_num_threads(1)
paths=['output/training/city-five-stage-cold-initial-01/candidate.zip','output/training/city-strategy-original-delay-01/segment-001/final.zip','output/training/city-strategy-opening-01/segment-001/final.zip'];models=[MaskablePPO.load(p,device='cpu') for p in paths]
seeds=[r['seed'] for r in json.loads((rec/'opening-failures.json').read_text())['rows']];e=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',allow_bridges=True);rows=[]
try:
 for seed in [2004,*seeds]:
  obs,_=e.reset(options=dict(scenario_seed=seed));mask=e.action_masks();water=np.zeros_like(mask)
  for action in np.flatnonzero(mask[1:])+1:
   cell,d=divmod(int(action)-1,4);x,y=cell%50,cell//50;dx,dy=FORWARD[d];water[action]=e.raw['terrain'][cell]==1 or e.raw['terrain'][(y+dy)*50+x+dx]==1
  values=[]
  for model in models:
   p=masked_probs(model,obs,mask).astype(float);p/=p.sum();assert np.isfinite(p).all() and not p[~mask].any();values.append(dict(wait=float(p[0]),water_probability=float(p[water].sum()),conditional_water_probability=float(p[water].sum()/p[1:].sum()),top_road_is_water=bool(water[1+np.argmax(p[1:])])) )
  rows.append(dict(seed=seed,legal_roads=int(mask.sum()-1),legal_water_connections=int(water.sum()),models=values));print(rows[-1],flush=True)
finally:e.close()
(rec/'bridge-initial-probabilities.json').write_text(json.dumps(dict(models=paths,sha256={p:sha256(Path(p)) for p in paths},rows=rows,note='Frozen initial-observation probes only; not rollout success or training labels.'),indent=2)+'\n')
