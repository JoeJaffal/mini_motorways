"""Read-only terminal-state diagnostics; no actions or routes supplied to learner."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp,json,torch,numpy as np
from sb3_contrib import MaskablePPO
import audit_city_service as audit
from city_road_pilot import CityRoadEnv
from environment import DIRS
from collections import Counter
OUT=Path('docs/training/city-strategy-launch-2026-11-24/bridge-reference-ending-diagnostics.json')
def inspect(raw):
 # Reachability of already-built links only. This is not a candidate-road planner.
 parent=list(range(1500))
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 for i,bits in enumerate(raw['connections']):
  x,y=i%50,i//50
  for d,(dx,dy) in enumerate(DIRS):
   xx,yy=x+dx,y+dy
   if bits&(1<<d) and 0<=xx<50 and 0<=yy<30:parent[find(i)]=find(yy*50+xx)
 def cell(p):return p['y']*50+p['x']
 shops=[]
 for s in raw['buildings']:
  if s['isHouse']:continue
  roots={find(cell(p)) for p in s['entrances']}
  homes=[h for h in raw['buildings'] if h['isHouse'] and h['color']==s['color']]
  connected=[h['id'] for h in homes if find(cell(h['cell'])) in roots]
  cars=[v for v in raw['vehicles'] if v['shopId']==s['id']]
  shops.append(dict(id=s['id'],color=s['color'],cell=s['cell'],demand=s['demand'],capacity=s['demandCapacity'],overcrowded_seconds=s['overcrowdedFor'],served=s['served'],matching_homes=len(homes),built_graph_connected_homes=len(connected),assigned_cars=len(cars),assigned_waiting_cars=sum(v['waiting']>1 for v in cars),max_assigned_wait=max((v['waiting'] for v in cars),default=0)))
 return dict(shops=sorted(shops,key=lambda s:s['overcrowded_seconds'],reverse=True),vehicle_stages=dict(Counter(v['stage'] for v in raw['vehicles'])),vehicle_obstacles=dict(Counter(v['obstacle'] for v in raw['vehicles'] if v['obstacle'])),mean_native_waiting=raw['meanWaiting'])
def worker(row):
 torch.set_num_threads(1);snap={}
 class Capture(CityRoadEnv):
  def close(self):
   if hasattr(self,'raw'):snap.update(inspect(self.raw))
   super().close()
 audit.CityRoadEnv=Capture
 m=MaskablePPO.load('output/training/city-five-stage-cold-initial-01/candidate.zip',device='cpu')
 result=audit.trace('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',m,row['seed'],row['action_seed'],estimate=False,horizon=1200,allow_bridges=True)
 assert result==row_without_model(row),'Instrumentation changed replay'
 print('DIAGNOSTIC',row['seed'],result['trips'],flush=True)
 return dict(seed=row['seed'],score=row['trips'],seconds=row['seconds'],native_game_over=row['native_game_over'],terminal=snap)
def row_without_model(row):return {k:v for k,v in row.items() if k!='model'}
if __name__=='__main__':
 assert not OUT.exists()
 rows=[json.loads(s) for s in Path('output/training/city-strategy-bridge-longer-baseline-01/games.jsonl').read_text().splitlines()];rows=sorted([r for r in rows if r['model']==0],key=lambda r:(r['trips'],r['seed']))
 jobs=[rows[i] for i in (0,4,8,12,16,20,24,31)]
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:results=list(pool.map(worker,jobs))
 OUT.write_text(json.dumps(dict(selection='Eight score-ordered representatives at indices0,4,8,12,16,20,24,31 of32 consumed development cities; descriptive only',instrumentation_exact=True,limit='Built-link graph reachability alone does not prove native vehicle routing or sufficient service capacity. No diagnostic routes/actions are used by the learner.',results=results),indent=2)+'\n')
