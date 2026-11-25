from pathlib import Path
import json
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_wait_decision import CityWaitDecisionEnv,SCHEDULE
from prepare_city_wait_repair import optimizer_by_name,assert_state_equal
from prepare_city_policy import sha256
from train_city_wait_decision import is_wait
r=Path('docs/training/build-wait-ppo-2026-11-25');torch.set_num_threads(1)
parent=Path('output/training/build-wait-smoke-initial-01/start.zip');final=Path('output/training/build-wait-smoke-01/final.zip')
a=MaskablePPO.load(parent,device='cpu');b=MaskablePPO.load(final,device='cpu')
sa=optimizer_by_name(a.policy);sb=optimizer_by_name(b.policy)
assert_state_equal(sa,{k:v for k,v in sb.items() if not is_wait(k)})
changed=[]
for key,value in a.policy.state_dict().items():
 other=b.policy.state_dict()[key];assert torch.isfinite(other).all()
 if is_wait(key):
  if not torch.equal(value,other):changed.append(key)
 else:torch.testing.assert_close(value,other,rtol=0,atol=0)
assert changed and b.num_timesteps==a.num_timesteps+128
assert {int(s['step']) for k,s in sb.items() if is_wait(k)}=={4}
env=CityWaitDecisionEnv('output/wait-decision-build-02/artifacts/bin/TrafficHost/release/TrafficHost.dll');errors=[];wait_deltas=[]
try:
 for i,case in enumerate(SCHEDULE):
  obs,_=env.reset(options=dict(case=case,scenario_seed=244002000+i));mask=env.action_masks()
  tensor,_=a.policy.obs_to_tensor(obs)
  with torch.no_grad():
   da=a.policy.get_distribution(tensor,action_masks=mask);db=b.policy.get_distribution(tensor,action_masks=mask)
   torch.testing.assert_close(da.raw_logits[:,1:],db.raw_logits[:,1:],rtol=0,atol=0)
   pa=da.distribution.probs[0].numpy();pb=db.distribution.probs[0].numpy()
   errors.append(float(np.max(abs(pa[1:]/pa[1:].sum()-pb[1:]/pb[1:].sum()))));wait_deltas.append(float(abs(pa[0]-pb[0])))
   assert not b.policy.predict_values(tensor).count_nonzero()
finally:env.close()
report=dict(parent_sha256=sha256(parent),smoke_sha256=sha256(final),decisions=128,wait_adam_steps=4,preserved_other_adam_states=len(sa),all_other_weights_exact=True,road_logits_exact=True,max_conditional_road_probability_error=max(errors),max_wait_probability_change=max(wait_deltas),changed_wait_state_keys=changed,zero_baseline=True,finite=True,limits='Disposable actual PPO factory smoke; excluded from production candidates. Training collection accuracy is not a post-update performance claim.')
(r/'smoke-reload-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
