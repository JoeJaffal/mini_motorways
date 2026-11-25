from pathlib import Path
import json,numpy as np
from city_curriculum import CityCurriculumEnv
from city_road_pilot import edge_action
def witness_edges(raw):
 edges=[]
 for shop in [b for b in raw['buildings'] if not b['isHouse']]:
  homes=[b for b in raw['buildings'] if b['isHouse'] and b['color']==shop['color']]
  if not homes:continue
  a=homes[0]['cell'];b=shop['entrance'];x,y=a['x'],a['y'];dx=int(np.sign(b['x']-x));dy=int(np.sign(b['y']-y));assert dx==0 or dy==0
  while (x,y)!=(b['x'],b['y']):
   edges.append(edge_action((x,y),(x+dx,y+dy)));x+=dx;y+=dy
 return edges

rows=[]
for seed in range(188900020,188900028):
 results=[]
 for collapse in [False,True]:
  e=CityCurriculumEnv('output/small-city-service-build-01/bin/TrafficHost/release/TrafficHost.dll',collapse_forced_wait=collapse)
  try:
   e.reset(options=dict(exercise='small-city-pairs',scenario_seed=seed));reward=0;steps=0
   while not e.done:
    mask=e.action_masks();action=next((a for a in witness_edges(e.raw) if mask[a]),0)
    _,r,_,_,_=e.step(action);reward+=r;steps+=1
   results.append((e.raw,reward,steps))
  finally:e.close()
 assert results[0][:2]==results[1][:2]
 rows.append(dict(seed=seed,reward=results[0][1],plain_steps=results[0][2],compressed_steps=results[1][2]))
Path('docs/training/small-city-service-2026-11-24/compression-check.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
