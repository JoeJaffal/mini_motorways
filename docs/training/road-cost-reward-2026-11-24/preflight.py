from pathlib import Path
import json,numpy as np
from city_curriculum import CityCurriculumEnv
from city_road_cost_env import CityRoadCostEnv
from city_road_pilot import edge_action
R=Path('docs/training/road-cost-reward-2026-11-24');DLL='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
def witness_edges(raw):
 edges=[]
 for shop in [b for b in raw['buildings'] if not b['isHouse']]:
  homes=[b for b in raw['buildings'] if b['isHouse'] and b['color']==shop['color']]
  if not homes:continue
  a=homes[0]['cell'];b=shop['entrance'];x,y=a['x'],a['y'];dx=int(np.sign(b['x']-x));dy=int(np.sign(b['y']-y));
  while (x,y)!=(b['x'],b['y']):
   dx=int(np.sign(b['x']-x));dy=int(np.sign(b['y']-y));edges.append(edge_action((x,y),(x+dx,y+dy)));x+=dx;y+=dy
 return edges

rows=[]
for split in ['train','validation']:
 for cost in [0.,.01,.04]:
  e=CityRoadCostEnv(DLL,road_cost=cost,validation=split=='validation')
  try:
   for seed in range(198900000,198900008):
    for exercise in ['small-city-offset-single','small-city-offset-stock']:
     for mode in ['connect','wait']:
      obs,info=e.reset(options=dict(exercise=exercise,scenario_seed=seed));assert not any(e.env.raw['connections']);assert not e.env.host.call(command='curriculumReference')['edits'];total=0
      while not e.env.done:
       mask=e.action_masks();action=next((a for a in witness_edges(e.env.raw) if mask[a]),0) if mode=='connect' else 0
       obs,reward,_,_,info=e.step(action);total+=reward
       assert len(e.env.raw['buildings'])==2
       assert e.observation_space.contains(obs)
      assert abs(total-(info['trips']-cost*info['paid_units']))<1e-6
      assert (info['trips']>0 and total>0) if mode=='connect' else (info['trips']==0 and total==0)
      rows.append(dict(split=split,seed=seed,exercise=exercise,cost=cost,mode=mode,native_score=info['trips'],paid_units=info['paid_units'],return_=total,initial_stock=info['stock_initial']))
  finally:e.close()
# Same actions must yield exact same native state/observation, differing only in reward.
a=CityRoadCostEnv(DLL,road_cost=0.);b=CityRoadCostEnv(DLL,road_cost=.04);transitions=0
try:
 for seed in range(198900020,198900024):
  a.reset(options=dict(exercise='small-city-offset-stock',scenario_seed=seed));b.reset(options=dict(exercise='small-city-offset-stock',scenario_seed=seed));rng=np.random.default_rng(seed)
  while not a.env.done:
   assert a.env.raw==b.env.raw;np.testing.assert_array_equal(a.action_masks(),b.action_masks());action=int(rng.choice(np.flatnonzero(a.action_masks())))
   x,rx,tx,ux,ix=a.step(action);y,ry,ty,uy,iy=b.step(action)
   assert (tx,ux)==(ty,uy)
   for k in x:np.testing.assert_array_equal(x[k],y[k])
   transitions+=1
finally:a.close();b.close()
(R/'preflight.json').write_text(json.dumps(dict(controls=rows,exact_native_transitions=transitions,max_initial_stock=max(x['initial_stock'] for x in rows),minimum_success_return=min(x['return_'] for x in rows if x['mode']=='connect'),analytic_worst_success_return=1-.04*18),indent=2)+'\n');print('PASS',len(rows),'controls;',transitions,'exact transitions')
