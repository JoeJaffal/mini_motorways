from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();rec=root/'docs/training/city-whole-policy-2026-11-24';torch.set_num_threads(1)
base=MaskablePPO.load(root/'output/training/city-strategy-wide-initial-01/start.zip',device='cpu')
e=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=600,allow_bridges=True);reports={}
try:
 for arm in ('gated','whole'):
  p=root/f'output/training/city-whole-fit-01/{arm}/final.zip';m=MaskablePPO.load(p,device='cpu')
  changes={k:float((v-base.policy.state_dict()[k]).abs().max()) for k,v in m.policy.state_dict().items() if not torch.equal(v,base.policy.state_dict()[k])}
  assert changes and all('growth_strategy_' in k or k.startswith('value_net.') for k in changes)
  assert all(torch.isfinite(v).all() for v in m.policy.state_dict().values())
  rows=[]
  for seed in list(range(184000000,184000008))+list(range(185000000,185000008)):
   obs,_=e.reset(options=dict(scenario_seed=seed));mask=e.action_masks();a=masked_probs(base,obs,mask);b=masked_probs(m,obs,mask);assert not b[~mask].any()
   if arm=='gated':np.testing.assert_array_equal(a,b)
   rows.append(dict(seed=seed,wait_before=float(a[0]),wait_after=float(b[0]),probability_total_variation=float(np.abs(a-b).sum()/2),road_total_variation=float(np.abs(a[1:]/a[1:].sum()-b[1:]/b[1:].sum()).sum()/2)))
  if arm=='whole':assert any(x['probability_total_variation']>0 for x in rows)
  reports[arm]=dict(checkpoint=str(p),sha256=sha256(p),changed_parameters=changes,opening_states=rows,optimizer_steps=int(next(iter(m.policy.optimizer.state.values()))['step']))
finally:e.close()
(rec/'trained-policy-audit.json').write_text(json.dumps(reports,indent=2)+'\n');print({k:dict(changed_tensors=len(v['changed_parameters']),mean_opening_tv=float(np.mean([x['probability_total_variation'] for x in v['opening_states']])),optimizer_steps=v['optimizer_steps']) for k,v in reports.items()})
