from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from midgame_timing_policy import MidgameTimingFeatures
from prepare_city_policy import masked_probs

torch.set_num_threads(1)
paths=['output/training/city-five-stage-cold-initial-01/candidate.zip','output/training/city-road-reserve-pilot-01/final.zip','output/training/city-road-reserve-repaired-01/candidate.zip']
models=[MaskablePPO.load(p,device='cpu') for p in paths]
seed,action_seed=json.loads(Path('output/training/city-road-reserve-city-candidate-01/suite.json').read_text())[1]
e=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll');rows=[]
try:
 obs,_=e.reset(options=dict(scenario_seed=seed));rng=np.random.default_rng(action_seed)
 while not e.done and len(rows)<3:
  mask=e.action_masks();old=models[1];tensor,_=old.policy.obs_to_tensor(obs);f=old.policy.features_extractor
  with torch.no_grad():ev=f.reserve_evidence(tensor);blocked=bool(MidgameTimingFeatures.waiting_context(f,tensor['grid']))
  p=masked_probs(old,obs,mask).astype(float);p/=p.sum()
  if ev[0,4] and not blocked and mask[1:].any():
   probs=[masked_probs(m,obs,mask) for m in models]
   np.testing.assert_allclose(probs[0],probs[2],atol=2e-6,rtol=2e-5)
   rows.append(dict(time=e.raw['time'],stock=e.raw['inventory'][0],wait_parent=float(probs[0][0]),wait_unrepaired=float(probs[1][0]),wait_repaired=float(probs[2][0]),fallback_exact_within_float_tolerance=True))
  obs,*_=e.step(int(rng.choice(len(p),p=p)))
finally:e.close()
assert len(rows)==3
Path('docs/training/road-reserve-learning-2026-11-23/context-repair-native-check.json').write_text(json.dumps(dict(seed=seed,rows=rows),indent=2)+'\n');print(rows)
