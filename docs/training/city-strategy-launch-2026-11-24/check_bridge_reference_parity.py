"""Verify preserved wide initialization against calibrated actor on bridge rollouts."""
from pathlib import Path
import json, torch, numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();record=root/'docs/training/city-strategy-launch-2026-11-24/bridge-reference-wide-parity.json'
assert not record.exists()
torch.set_num_threads(1)
paths=[Path('output/training/city-five-stage-cold-initial-01/candidate.zip'),Path('output/training/city-strategy-wide-initial-01/start.zip')]
models=[MaskablePPO.load(p,device='cpu') for p in paths]
suite=json.loads(Path('output/training/city-strategy-bridge-longer-baseline-01/suite.json').read_text())[:8]
e=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=1200,observation_horizon=600,allow_bridges=True)
rows=[]
try:
 for seed,action_seed in suite:
  obs,info=e.reset(options=dict(scenario_seed=seed));rng=np.random.default_rng(action_seed);count=0
  while not e.done and count<128:
   mask=e.action_masks();a,b=[masked_probs(m,obs,mask) for m in models]
   np.testing.assert_array_equal(a,b)
   prob=a.astype(np.float64);prob/=prob.sum();action=int(rng.choice(len(prob),p=prob))
   obs,_,_,_,info=e.step(action);count+=1
  rows.append(dict(seed=seed,observations=count,last_seconds=info['seconds'],trips=info['trips']))
finally:e.close()
record.write_text(json.dumps(dict(checkpoints={str(p):sha256(p) for p in paths},actor_exact=True,observations=sum(r['observations'] for r in rows),rows=rows,limit='Sampled development trajectories; no claim that these checks prove generalization or new learning.'),indent=2)+'\n')
print(record.read_text())
