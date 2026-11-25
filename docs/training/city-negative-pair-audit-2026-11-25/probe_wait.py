import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from pair_audit_env import CityPairAuditEnv,CASES
from prepare_city_policy import sha256
r=Path('docs/training/city-negative-pair-audit-2026-11-25');torch.set_num_threads(1)
dll='output/pair-city-audit-build-01/artifacts/bin/TrafficHost/release/TrafficHost.dll'
models={'original':'output/training/city-whole-initial-01/start.zip','focused_final':'output/training/mini-fixed-route-01/training/final.zip'}
env=CityPairAuditEnv(dll,horizon=60,observation_horizon=600);rows=[]
try:
 for label,path in models.items():
  model=MaskablePPO.load(path,device='cpu')
  for case in CASES:
   for seed in range(243000000,243000016):
    obs,_=env.reset(options=dict(case=case,scenario_seed=seed));mask=env.action_masks();tensor,_=model.policy.obs_to_tensor(obs)
    with torch.no_grad():
     d=model.policy.get_distribution(tensor,action_masks=mask)
     p=d.distribution.probs[0].cpu().numpy()
     # Probe only the live distribution object: constant road-logit changes
     # should cancel under the already implemented conditional normalization.
     raw=d.raw_logits.clone();d.raw_logits[:,1:]+=10;d.apply_masking(mask)
     shifted=d.distribution.probs[0].cpu().numpy().copy();d.raw_logits=raw;d.apply_masking(mask)
     rows.append(dict(model=label,case=case,seed=seed,wait_probability=float(p[0]),conditional_road_shift_wait_probability=float(shifted[0]),legal_roads=int(mask[1:].sum()),road_shift_max_probability_difference=float(np.max(np.abs(p-shifted)))))
finally:env.close()
(r/'wait-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
for label in models:
 for case in CASES:
  g=[x for x in rows if x['model']==label and x['case']==case]
  print(label,case,'Wait min/mean/max',min(x['wait_probability'] for x in g),np.mean([x['wait_probability'] for x in g]),max(x['wait_probability'] for x in g),'shift maxerror',max(x['road_shift_max_probability_difference'] for x in g))
