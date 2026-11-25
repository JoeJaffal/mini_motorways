from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,LESSONS

torch.set_num_threads(1);m=MaskablePPO.load('output/training/city-strategy-initial-01/start.zip',device='cpu')
e=CityCurriculumEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True);rows=[]
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(exercise=lesson,scenario_seed=141000000));mask=e.action_masks()[1:]
  tensor,_=m.policy.obs_to_tensor(obs)
  with torch.no_grad():evidence=m.policy.features_extractor.relation_evidence(tensor['grid'])[0].numpy()[mask]
  unique,counts=np.unique(evidence,axis=0,return_counts=True)
  rows.append(dict(lesson=lesson,legal_roads=int(mask.sum()),distinct_trainable_relation_inputs=len(unique),largest_indistinguishable_group=int(counts.max()),note='Global context is identical across roads. Learned residual cannot change relative preference inside each equal-input group. Inherited frozen scores can differ.'))
finally:e.close()
Path('docs/training/city-strategy-launch-2026-11-24/feature-aliases.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
