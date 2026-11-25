from pathlib import Path
import json,numpy as np
from city_curriculum import CityCurriculumEnv
from city_road_pilot import CityRoadEnv,edge_action
R=Path('docs/training/small-city-service-2026-11-24');DLL='output/small-city-offset-build-01/bin/TrafficHost/release/TrafficHost.dll'
# Fixture-only feasibility witness, never imported by the learner. Straight
# cardinal pairs by construction; no search, optimization or training labels.
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
 e=CityCurriculumEnv(DLL,validation=split=='validation')
 try:
  for seed in range(190900000,190900016):
   for exercise in ['small-city-single','small-city-offset-pairs']:
    for mode in ['connect','wait']:
     obs,info=e.reset(options=dict(exercise=exercise,scenario_seed=seed));assert len(e.raw['buildings'])==2
     assert not e.host.call(command='curriculumReference')['edits'];assert not any(e.raw['connections'])
     total=0
     while not e.done:
      mask=e.action_masks();edges=witness_edges(e.raw) if mode=='connect' else []
      action=next((a for a in edges if mask[a]),0);obs,reward,_,_,info=e.step(action);total+=reward
      assert e.observation_space.contains(obs)
     shops=[b for b in e.raw['buildings'] if not b['isHouse']];served=sum(b['served']>0 for b in shops);want=2 if exercise.endswith('pairs') else 1
     assert total==info['trips']==sum(b['served'] for b in shops)
     assert (served==want if mode=='connect' else served==0),(split,seed,exercise,mode,info)
     assert len(shops)==want
     rows.append(dict(split=split,seed=seed,exercise=exercise,mode=mode,served=served,score=total,initial_stock=info['stock_initial'],remaining_stock=info['road_stock']))
 finally:e.close()
# Ordinary-city behavior must remain byte-for-byte equal on shared transitions.
a=CityRoadEnv(DLL,allow_bridges=True);b=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',allow_bridges=True);count=0
try:
 for seed in [2004,184000000]:
  x,_=a.reset(options=dict(scenario_seed=seed));y,_=b.reset(options=dict(scenario_seed=seed));rng=np.random.default_rng(412)
  for _ in range(80):
   assert a.raw==b.raw
   for k in x:np.testing.assert_array_equal(x[k],y[k])
   np.testing.assert_array_equal(a.action_masks(),b.action_masks());action=int(rng.choice(np.flatnonzero(a.action_masks())))
   x,ra,ta,ua,ia=a.step(action);y,rb,tb,ub,ib=b.step(action);assert (ra,ta,ua,ia)==(rb,tb,ub,ib);count+=1
finally:a.close();b.close()
(R/'offset-preflight.json').write_text(json.dumps(dict(controls=rows,ordinary_city_exact_transitions=count,notes='No policy training or reference labels. Empty initial connection arrays; no curriculumReference edits. Reset alternating pair/single also checks pending spawn isolation.'),indent=2)+'\n');print('PASS',len(rows),'fixture controls;',count,'ordinary transitions')
