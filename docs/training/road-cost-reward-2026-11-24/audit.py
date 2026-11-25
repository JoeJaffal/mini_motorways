from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import masked_probs,sha256
r=Path('docs/training/road-cost-reward-2026-11-24');out=Path('output/training/road-cost-reward-fit-01');torch.set_num_threads(1)
p=Path('output/training/city-whole-initial-01/start.zip');base=MaskablePPO.load(p,device='cpu');models={a:MaskablePPO.load(out/a/'final.zip',device='cpu') for a in ['control','mild','strong']};reports={};preupdate={}
for arm,m in models.items():
 changes={k:float((v-base.policy.state_dict()[k]).abs().max()) for k,v in m.policy.state_dict().items() if not torch.equal(v,base.policy.state_dict()[k])}
 assert changes and all('growth_strategy_' in k or k.startswith('value_net.') for k in changes);assert all(torch.isfinite(v).all() for v in m.policy.state_dict().values())
 relative={k:float((v-models['control'].policy.state_dict()[k]).abs().max()) for k,v in m.policy.state_dict().items() if not torch.equal(v,models['control'].policy.state_dict()[k])}
 reports[arm]=dict(differences_vs_control=relative,sha256=sha256(out/arm/'final.zip'),changed_tensors=changes,optimizer_steps=int(next(iter(m.policy.optimizer.state.values()))['step']),states=[])
 count=json.loads((out/arm/'checkpoints.json').read_text())[0]['episodes'];episodes=list(map(json.loads,(out/arm/'episodes.jsonl').read_text().splitlines()))
 preupdate[arm]=[{k:v for k,v in e.items() if k not in ['r','road_cost','shaped_return','t']} for e in episodes[:count]]
 for e in episodes:assert abs(e['r']-(e['trips']-e['road_cost']*e['paid_units']))<2e-5
assert preupdate['control']==preupdate['mild']==preupdate['strong']
e=CityCurriculumEnv('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',validation=True)
try:
 for condition in ['small-city-offset-single','small-city-offset-stock']:
  for seed in range(199000000,199000008):
   obs,_=e.reset(options=dict(exercise=condition,scenario_seed=seed));mask=e.action_masks();x=masked_probs(base,obs,mask);c=masked_probs(models['control'],obs,mask)
   for arm,m in models.items():
    y=masked_probs(m,obs,mask);assert not y[~mask].any();reports[arm]['states'].append(dict(exercise=condition,seed=seed,tv_vs_control=float(np.abs(y-c).sum()/2),wait_before=float(x[0]),wait_after=float(y[0]),conditional_road_tv=float(np.abs(x[1:]/x[1:].sum()-y[1:]/y[1:].sum()).sum()/2)))
finally:e.close()
report=dict(parent_sha256=sha256(p),exact_preupdate_native_episodes=len(preupdate['control']),all_episode_reward_ledgers_pass=True,policies=reports)
(r/'policy-audit.json').write_text(json.dumps(report,indent=2)+'\n');print({a:dict(optimizer_steps=x['optimizer_steps'],changed_tensors=len(x['changed_tensors']),mean_road_tv=float(np.mean([v['conditional_road_tv'] for v in x['states']])),mean_wait_change=float(np.mean([v['wait_after']-v['wait_before'] for v in x['states']]))) for a,x in reports.items()})
