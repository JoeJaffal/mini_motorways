import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs
from export_city_replays import action_endpoints

torch.set_num_threads(1)
review=json.loads(Path('output/training/city-learning-long-01/segment-02/review.json').read_text())
models=[MaskablePPO.load(p,device='cpu') for p in review['models'][1:]]
rows=[json.loads(s) for s in (Path(review['folder'])/'games.jsonl').read_text().splitlines()]
env=CityRoadEnv('output/city-network-service-build.NdaqGi/bin/TrafficHost/release/TrafficHost.dll')
results=[]
try:
 for seed in (99161630,99312933,99324387):
  games=[]
  for index,model in enumerate(models):
   expected=next(r for r in rows if r['seed']==seed and r['model']==index+1)
   obs,info=env.reset(options={'scenario_seed':seed})
   rng=np.random.default_rng(expected['action_seed'])
   actions=[];first=None;stockout=None
   while not env.done:
    mask=env.action_masks(); p=masked_probs(model,obs,mask).astype(float);p/=p.sum()
    action=int(rng.choice(len(p),p=p))
    actions.append(dict(action=action,time=info['seconds'],stock=info['road_stock'],score=info['trips'],probability=float(p[action]),
                        edge=action_endpoints(action) if action else None))
    obs,reward,_,_,info=env.step(action)
    if reward and first is None:first=info['seconds']
    if info['road_stock']==0 and stockout is None:stockout=info['seconds']
   assert all(info[k]==expected[k] for k in info)
   games.append(dict(model=index+1,ending=info,first_delivery=first,first_stockout=stockout,actions=actions))
  divergence=[]
  for other in (1,2):
   pair=next(((i,a,b) for i,(a,b) in enumerate(zip(games[0]['actions'],games[other]['actions'])) if a['action']!=b['action']),None)
   divergence.append(dict(model=other+1,first_difference=pair))
  results.append(dict(seed=seed,games=games,divergence=divergence))
finally:env.close()
Path('docs/training/city-regression-repair-2026-11-23/replays.json').write_text(json.dumps(results,indent=2)+'\n')
