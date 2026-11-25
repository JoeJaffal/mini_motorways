"""Check exact inference and separation of actor/value gradient paths."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256

torch.set_num_threads(1)
root=Path('docs/training/mini-task-repair-2026-11-25/critic-detach')
checkpoint=Path('output/training/mini-road-detached-initial-01/start.zip')
parent=Path('output/training/mini-reset-wait-repair-01/start.zip')
digest=sha256(checkpoint)
m=MaskablePPO.load(checkpoint,device='cpu');a=MaskablePPO.load(parent,device='cpu')
env=CityRoadEnv('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',horizon=600,allow_bridges=True)
try:
    obs,_=env.reset(options=dict(scenario_seed=184000001));rng=np.random.default_rng(193352);states=[]
    for _ in range(12):
        mask=env.action_masks();p=masked_probs(a,obs,mask);q=masked_probs(m,obs,mask)
        np.testing.assert_array_equal(p,q)
        inputs,_=m.policy.obs_to_tensor(obs)
        with torch.no_grad():torch.testing.assert_close(m.policy.predict_values(inputs),a.policy.predict_values(inputs),rtol=0,atol=0)
        states.append((deepcopy(obs),mask.copy(),p.copy()))
        obs,*_=env.step(int(rng.choice(len(p),p=p.astype(float)/p.sum(dtype=float))))
    obs,mask,_=states[0];inputs,_=m.policy.obs_to_tensor(obs)
    before={key:value.clone() for key,value in m.policy.state_dict().items()}
    m.policy.optimizer.zero_grad(set_to_none=True)
    (m.policy.predict_values(inputs)-30).square().mean().backward()
    value_names=[name for name,p in m.policy.named_parameters() if p.grad is not None]
    assert value_names and all(name.startswith('value_net.') for name in value_names)
    m.policy.optimizer.step()
    changed=[key for key,value in m.policy.state_dict().items() if not torch.equal(value,before[key])]
    assert changed and all(key.startswith('value_net.') for key in changed)
    for obs,mask,p in states:np.testing.assert_array_equal(masked_probs(m,obs,mask),p)
    m=MaskablePPO.load(checkpoint,device='cpu')
    obs,mask,p=states[0];inputs,_=m.policy.obs_to_tensor(obs)
    m.policy.optimizer.zero_grad(set_to_none=True)
    dist=m.policy.get_distribution(inputs,mask)
    (-dist.log_prob(torch.tensor([1+int(p[1:].argmax())])).mean()).backward()
    actor_names=[name for name,p in m.policy.named_parameters() if p.grad is not None]
    assert actor_names and not any(name.startswith('value_net.') or 'strategy_wait' in name or 'visual_wait' in name for name in actor_names)
    norms={name:float(sum(p.grad.square().sum() for p in getattr(m.policy.features_extractor,name).parameters() if p.grad is not None).sqrt()) for name in ('growth_strategy_roads','growth_strategy_spatial','growth_strategy_spatial_roads')}
    assert norms['growth_strategy_spatial']>1e-8
    assert sha256(checkpoint)==digest
    report=dict(checkpoint_sha256=digest,exact_action_and_value_states=len(states),
        value_only_gradient_names=value_names,value_only_update_changed=changed,
        actions_exact_after_value_only_update=True,actor_gradient_names=actor_names,actor_gradient_norms=norms,
        saved_checkpoint_unchanged=True,limits='Disposable gradient/optimizer checks only; no effectiveness claim.')
    (root/'gradient-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
finally:env.close()
