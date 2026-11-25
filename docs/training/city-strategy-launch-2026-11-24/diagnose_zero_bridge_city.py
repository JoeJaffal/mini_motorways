from pathlib import Path
import json,torch
from sb3_contrib import MaskablePPO
import audit_city_service as audit
from city_road_pilot import CityRoadEnv
root=Path.cwd();out=root/'docs/training/city-strategy-launch-2026-11-24/bridge-zero-city-traffic.json';assert not out.exists()
torch.set_num_threads(1);frames=[]
class Capture(CityRoadEnv):
 def step(self,action):
  result=super().step(action)
  if not frames or int(self.raw['time']//10)>int(frames[-1]['time']//10) or self.done:
   frames.append({k:self.raw[k] for k in ('time','tripsCompleted','failed','inventory','vehicles','buildings','connections','terrain','infrastructure')})
  return result
m=MaskablePPO.load('output/training/city-five-stage-cold-initial-01/candidate.zip',device='cpu');audit.CityRoadEnv=Capture
r=audit.trace('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',m,99020130,1849124851,estimate=False,horizon=1200,allow_bridges=True)
assert r['trips']==0 and r['seconds']==144.95000000000002
out.write_text(json.dumps(dict(result=r,frames=frames),indent=2)+'\n')
for f in frames:
 print('FRAME',f['time'],[(v['id'],v['stage'],v['at'],round(v['speed'],3),v['obstacle'],len(v['route'])) for v in f['vehicles'] if v['shopId']==0],flush=True)
