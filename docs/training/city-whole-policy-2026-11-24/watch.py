from pathlib import Path
import argparse,json,torch
from sb3_contrib import MaskablePPO
import audit_city_service as audit
from city_road_pilot import CityRoadEnv
from export_city_replays import frame,action_endpoints
from prepare_city_policy import sha256
p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--action-seed',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True);torch.set_num_threads(1)
frames=[];browser=[];actions=[];terrain=None
class Capture(CityRoadEnv):
 def record(self,description,edge=None):
  global terrain
  raw=self.raw
  if terrain is None:terrain=[[i,k] for i,k in enumerate(raw['terrain']) if k]
  frames.append({k:raw[k] for k in ('time','tripsCompleted','failed','inventory','vehicles','buildings','connections','terrain','infrastructure')})
  browser.append(frame(raw,description,edge))
 def reset(self,**kwargs):
  result=super().reset(**kwargs);self.record('Native city start');return result
 def step(self,action):
  before=self.raw['time'];result=super().step(action);obs,reward,terminated,truncated,info=result
  actions.append(dict(action=int(action),before_seconds=before,after_seconds=self.raw['time'],reward=reward,stock=self.raw['inventory'][0]))
  if action or self.done or self.raw['time']>=frames[-1]['time']+10:
   edge=action_endpoints(action) if action else None;self.record(f'Build {edge}' if action else f'Wait · {reward} deliveries',edge)
  return result
m=MaskablePPO.load(a.checkpoint,device='cpu');audit.CityRoadEnv=Capture
result=audit.trace('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',m,a.seed,a.action_seed,estimate=False,horizon=600,allow_bridges=True)
data=dict(result=result,checkpoint=a.checkpoint,checkpoint_sha256=sha256(Path(a.checkpoint)),frames=frames,actions=actions)
(a.output/'trace.json').write_text(json.dumps(data)+'\n')
page=dict(title=f'Observed game · seed {a.seed} · score {result["trips"]}',intro='Frozen policy in the native simulator. Frames show builds and roughly ten-second intervals; full actions are saved separately. No scripted road choices.',speed='16',ending='Native game-over' if result['native_game_over'] else '600-second evaluation limit',frames=browser,terrain=terrain)
template=Path('training/stage1_replay.html').read_text().replace('Decision ${index}', 'Frame ${index}');(a.output/'replay.html').write_text(template.replace('/*REPLAY_DATA*/',json.dumps(page).replace('<','\\u003c')))
print(json.dumps(result,indent=2))
