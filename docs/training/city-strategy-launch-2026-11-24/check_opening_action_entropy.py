from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();torch.set_num_threads(1)
path=root/'output/training/city-strategy-initial-01/start.zip';m=MaskablePPO.load(path,device='cpu')
rows=[json.loads(x) for x in (root/'output/training/city-strategy-confirmation-02/games.jsonl').read_text().splitlines()]
jobs=[r for r in rows if r['model']==0 and r['trips']==0]
e=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll');records=[]
try:
 for r in jobs:
  obs,info=e.reset(options=dict(scenario_seed=r['seed']));rng=np.random.default_rng(r['action_seed']);steps=[]
  while not e.done:
   mask=e.action_masks();p=masked_probs(m,obs,mask).astype(float);p/=p.sum()
   with torch.no_grad():tensor,_=m.policy.obs_to_tensor(obs);_,gate=m.policy.features_extractor.strategy_context(tensor)
   q=p[1:][mask[1:]];q=q/q.sum() if q.sum() else q;nonzero=q[q>0]
   action=int(rng.choice(len(p),p=p))
   steps.append(dict(time=info['seconds'],stock=info['road_stock'],buildings=info['buildings'],gate=bool(gate.item()),legal_roads=int(mask[1:].sum()),wait_probability=float(p[0]),conditional_top_road=float(q.max()) if len(q) else None,road_entropy=float(-(nonzero*np.log(nonzero)).sum()),action=action))
   obs,_,_,_,info=e.step(action)
  assert info['trips']==r['trips'] and info['road_actions']==r['road_actions']
  active=[x for x in steps if x['legal_roads'] and not x['gate']]
  choices=[x for x in active if x['action']]
  row=dict(seed=r['seed'],action_seed=r['action_seed'],trips=info['trips'],road_actions=info['road_actions'],seconds=info['seconds'],pre_gate_choices=len(active),pre_gate_roads=len(choices),mean_pre_gate_wait=float(np.mean([x['wait_probability'] for x in active])) if active else None,nearly_deterministic_road_states=sum(x['conditional_top_road']>.999 for x in active),mean_road_entropy=float(np.mean([x['road_entropy'] for x in active])) if active else None,first_build_time=choices[0]['time'] if choices else None,last_pre_gate_build_time=choices[-1]['time'] if choices else None,steps=steps)
  records.append(row);print({k:v for k,v in row.items() if k!='steps'},flush=True)
finally:e.close()
(root/'docs/training/city-strategy-launch-2026-11-24/opening-action-entropy.json').write_text(json.dumps(dict(checkpoint=str(path),sha256=sha256(path),note='Replay of already-seen zero-score confirmation02 cases using frozen initial actor. Diagnostic selection data only. No teaching actions or training.',rows=records),indent=2)+'\n')
