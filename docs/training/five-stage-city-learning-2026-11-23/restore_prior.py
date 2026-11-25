"""Evaluate learned corrections in original logit units, retaining old priors.

This is a separately saved transfer/calibration, not an additional PPO update.
Optimizer moments are reset because the relation parameters are rescaled.
"""
from pathlib import Path
import json,numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,JOIN,ROUTE,LOW,HIGH,PRIORITY
from prepare_city_policy import masked_probs,sha256

torch.set_num_threads(1)
parent=Path('output/training/city-five-stage-relations-mixed-01/final.zip')
out=Path('output/training/city-five-stage-retained-prior-01');out.mkdir(exist_ok=False)
m=MaskablePPO.load(parent,device='cpu')
old=MaskablePPO.load('output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip',device='cpu')
f=m.policy.features_extractor;scale=float(f.growth_road_temperature)
weights=f.growth_relations.weight.detach().clone()
with torch.no_grad():f.growth_road_temperature.fill_(1);f.growth_relations.weight.zero_()
e=CityCurriculumEnv('output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True)
try:
 for ex in [JOIN,ROUTE,LOW,HIGH,PRIORITY]:
  obs,_=e.reset(options=dict(exercise=ex,scenario_seed=118200000));mask=e.action_masks()
  np.testing.assert_allclose(masked_probs(m,obs,mask),masked_probs(old,obs,mask),atol=1e-6,rtol=1e-5)
finally:e.close()
with torch.no_grad():f.growth_relations.weight.copy_(weights*scale)
m.policy.optimizer.state.clear()
m.save(out/'candidate.zip')
(out/'config.json').write_text(json.dumps(dict(source=str(parent),source_sha256=sha256(parent),candidate_sha256=sha256(out/'candidate.zip'),relation_scale=scale,generic_temperature=1,prior_parity_without_relations=True,optimizer='reset after parameter rescaling; evaluation candidate'),indent=2)+'\n')
