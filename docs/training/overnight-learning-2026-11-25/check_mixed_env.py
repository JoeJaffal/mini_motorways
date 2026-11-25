from pathlib import Path
import json,numpy as np,torch
from sb3_contrib import MaskablePPO
from mixed_city_road_cost_env import MixedCityRoadCostEnv
from city_road_cost_env import CityRoadCostEnv
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import masked_probs
r=Path('docs/training/overnight-learning-2026-11-25');torch.set_num_threads(1)
dll='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
m=MaskablePPO.load('output/training/road-cost-continuation-01/strong/checkpoint-000262144.zip',device='cpu');rows=[]
for exercise in ('city','small-city-offset-single','small-city-offset-stock'):
 for i in range(2):
  new=MixedCityRoadCostEnv(dll)
  old=(CityCurriculumEnv(dll,stage='city',allow_bridges=True,collapse_forced_wait=True) if exercise=='city' else CityRoadCostEnv(dll,road_cost=.04,allow_bridges=True,collapse_forced_wait=True))
  rng=np.random.default_rng(281125+i);total=0;steps=0
  try:
   options=dict(exercise=exercise,scenario_seed=212000000+i)
   x,ix=old.reset(options=options);y,iy=new.reset(options=options)
   while True:
    assert all(np.array_equal(x[k],y[k]) for k in x)
    mask=old.action_masks();assert np.array_equal(mask,new.action_masks())
    probs=masked_probs(m,x,mask);action=int(rng.choice(len(probs),p=probs/probs.sum()))
    x,rx,tx,ux,ix=old.step(action);y,ry,ty,uy,iy=new.step(action)
    assert rx==ry and (tx,ux)==(ty,uy)
    assert ix['trips']==iy['trips'] and ix['road_stock']==iy['road_stock']
    total+=ry;steps+=1
    if ty or uy:break
   assert abs(total-iy['shaped_return'])<1e-5
   assert iy['road_cost']==(0 if exercise=='city' else .04)
   if exercise!='city':assert ty and not uy
   rows.append(dict(exercise=exercise,seed=212000000+i,steps=steps,score=iy['trips'],cost=iy['road_cost'],paid=iy['paid_units'],total_return=total))
  finally:old.close();new.close()
print(json.dumps(rows,indent=2));(r/'mixed-env-check.json').write_text(json.dumps(dict(exact_observation_mask_reward_termination_parity=True,games=rows),indent=2)+'\n')
