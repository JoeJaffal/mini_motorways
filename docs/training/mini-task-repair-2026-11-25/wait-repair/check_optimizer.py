"""Disposable optimizer update: preserve Wait while roads/encoder learn."""
from copy import deepcopy
import json
from pathlib import Path
import torch
import numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs, sha256

torch.set_num_threads(1)
archive=Path('docs/training/mini-task-repair-2026-11-25/wait-repair')
checkpoint=Path('output/training/mini-reset-wait-repair-01/start.zip')
digest=sha256(checkpoint)
model=MaskablePPO.load(checkpoint,device='cpu')
env=CityRoadEnv('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',horizon=600,allow_bridges=True)
try:
    obs,_=env.reset(options=dict(scenario_seed=184000001));states=[]
    rng=np.random.default_rng(193352)
    for step in range(12):
        mask=env.action_masks();prob=masked_probs(model,obs,mask)
        states.append((deepcopy(obs),mask.copy(),prob.copy()))
        obs,*_=env.step(int(rng.choice(len(prob),p=prob.astype(float)/prob.sum(dtype=float))))
    before={key:value.clone() for key,value in model.policy.state_dict().items()}
    obs,mask,prob=states[0];inputs,_=model.policy.obs_to_tensor(obs)
    road=1+int(prob[1:].argmax())
    distribution=model.policy.get_distribution(inputs,mask)
    loss=-distribution.log_prob(torch.tensor([road])).mean()+1e-5*model.policy.predict_values(inputs).square().mean()
    model.policy.optimizer.zero_grad();loss.backward()
    params=[p for group in model.policy.optimizer.param_groups for p in group['params']]
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in params)
    torch.nn.utils.clip_grad_norm_(params,.5);model.policy.optimizer.step()
    changed=[key for key,value in model.policy.state_dict().items() if not torch.equal(value,before[key])]
    assert changed and all(any(part in key for part in ('growth_strategy_roads','growth_strategy_spatial','value_net')) for key in changed)
    assert any('growth_strategy_spatial.' in key for key in changed)
    errors=[];tvs=[]
    for obs,mask,p in states:
        q=masked_probs(model,obs,mask)
        errors.append(float(abs(q[0]-p[0])))
        if p[1:].sum()>0:tvs.append(float(abs(q[1:]/q[1:].sum()-p[1:]/p[1:].sum()).sum()/2))
    assert max(errors)<1e-6 and max(tvs)>0
    assert {int(state['step']) for state in model.policy.optimizer.state.values()}=={8193}
    assert sha256(checkpoint)==digest
    saved=MaskablePPO.load(checkpoint,device='cpu')
    assert {int(state['step']) for state in saved.policy.optimizer.state.values()}=={8192}
    report=dict(checkpoint_sha256=digest,states=len(states),max_wait_error=max(errors),max_road_tv=max(tvs),
        changed_tensors=changed,disposable_adam_step=8193,saved_adam_step=8192,
        limits='One disposable update checks invariance and continuation mechanics, not training effectiveness. Saved checkpoint unchanged.')
    (archive/'optimizer-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
finally:env.close()
