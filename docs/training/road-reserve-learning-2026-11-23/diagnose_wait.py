from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from midgame_timing_policy import MidgameTimingFeatures
from prepare_city_policy import masked_probs

torch.set_num_threads(1);model=MaskablePPO.load('output/training/city-road-reserve-pilot-01/final.zip',device='cpu')
suite=json.loads(Path('output/training/city-road-reserve-city-candidate-01/suite.json').read_text());rows=[]
for seed,action_seed in suite[:2]:
 env=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll');counts={};samples=[]
 try:
  obs,_=env.reset(options=dict(scenario_seed=seed));rng=np.random.default_rng(action_seed)
  while not env.done:
   tensor,_=model.policy.obs_to_tensor(obs);f=model.policy.features_extractor
   with torch.no_grad():
    evidence=f.reserve_evidence(tensor)[0];visible_gate=bool(MidgameTimingFeatures.waiting_context(f,tensor['grid']))
   key='quiet' if evidence[0] else 'available' if evidence[2] else 'unavailable' if evidence[4] else 'opening'
   mask=env.action_masks();probs=masked_probs(model,obs,mask).astype(float);probs/=probs.sum()
   if key=='unavailable' and not visible_gate and mask[1:].any() and len(samples)<8:
    samples.append(dict(time=env.raw['time'],stock=env.raw['inventory'][0],wait=float(probs[0]),legal_builds=int(mask[1:].sum()),visible_blocker=visible_gate))
   counts[key]=counts.get(key,0)+1
   obs,*_=env.step(int(rng.choice(len(probs),p=probs)))
  rows.append(dict(seed=seed,score=env.raw['tripsCompleted'],states=counts,unavailable_without_visible_gate=samples))
 finally:env.close()
Path('docs/training/road-reserve-learning-2026-11-23/wait-context-diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
