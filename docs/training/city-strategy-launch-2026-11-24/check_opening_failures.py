from pathlib import Path
import sys,json,torch,numpy as np
sys.path.insert(0,str(Path.cwd()/'training'))
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs
root=Path.cwd();torch.set_num_threads(1)
rows=[json.loads(x) for x in (root/'output/training/city-strategy-confirmation-02/games.jsonl').read_text().splitlines()]
jobs=[r for r in rows if r['model']==0 and r['trips']==0]
m=MaskablePPO.load('output/training/city-strategy-initial-01/start.zip',device='cpu');env=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll');result=[]
try:
 for r in jobs:
  obs,info=env.reset(options=dict(scenario_seed=r['seed']));rng=np.random.default_rng(r['action_seed']);active=steps=0;first_active=None
  while not env.done:
   with torch.no_grad():
    tensor,_=m.policy.obs_to_tensor(obs);_,gate=m.policy.features_extractor.strategy_context(tensor)
   on=bool(gate.item());active+=on;steps+=1
   if on and first_active is None:first_active=info['seconds']
   p=masked_probs(m,obs,env.action_masks()).astype(float);action=int(rng.choice(len(p),p=p/p.sum()));obs,_,_,_,info=env.step(action)
  assert info['trips']==r['trips'] and info['road_actions']==r['road_actions']
  record=dict(seed=r['seed'],action_seed=r['action_seed'],trips=info['trips'],decisions=steps,trainable_gate_active=active,first_active=first_active,road_actions=info['road_actions'],seconds=info['seconds']);result.append(record);print(record,flush=True)
finally:env.close()
(root/'docs/training/city-strategy-launch-2026-11-24/opening-failures.json').write_text(json.dumps(dict(note='Post-confirmation diagnostic, same frozen initial policy trajectories. No training on these seeds.',rows=result),indent=2)+'\n')
