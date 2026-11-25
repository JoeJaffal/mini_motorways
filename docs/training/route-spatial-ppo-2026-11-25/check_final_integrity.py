"""Check the completed spatial checkpoint without updating it."""
import json
from pathlib import Path
import torch
from sb3_contrib import MaskablePPO
from prepare_city_policy import sha256
from prepare_city_wait_repair import optimizer_by_name, assert_state_equal
r=Path('docs/training/route-spatial-run-2026-11-25')
out=Path('output/training/route-spatial-01')
assert json.loads((r/'status.json').read_text())['status']=='complete'
torch.set_num_threads(1)
initial=MaskablePPO.load(out/'initial/start.zip',device='cpu')
final=MaskablePPO.load(out/'training/final.zip',device='cpu')
a=dict(initial.policy.named_parameters()); b=dict(final.policy.named_parameters())
trainable={n for n,p in final.policy.named_parameters() if p.requires_grad}
assert len(trainable)==22
for n in a:
    if n not in trainable: torch.testing.assert_close(a[n],b[n],rtol=0,atol=0)
old=optimizer_by_name(initial.policy); new=optimizer_by_name(final.policy)
assert_state_equal({k:v for k,v in old.items() if k not in trainable},{k:v for k,v in new.items() if k not in trainable})
assert all(torch.isfinite(v).all() for v in final.policy.state_dict().values())
for v in new.values():
    for t in v.values():
        if isinstance(t,torch.Tensor): assert torch.isfinite(t).all()
assert final.num_timesteps-initial.num_timesteps==262144
changes={n:float((b[n]-a[n]).abs().max()) for n in trainable}
assert all(new[n]['step']>old.get(n,{}).get('step',0) for n in trainable)
completion=json.loads((out/'training/complete.json').read_text())
report=dict(final_sha256=sha256(out/'training/final.zip'),lifetime_timesteps=final.num_timesteps,
    added_decisions=final.num_timesteps-initial.num_timesteps,frozen_weights_exact=True,
    frozen_adam_exact=True,finite_reload_and_adam=True,
    trainable_max_weight_changes=changes,adam_steps={k:int(v['step']) for k,v in new.items()},
    training_episodes=sum(1 for _ in (out/'training/episodes.jsonl').open()),
    elapsed_seconds=completion['elapsed_seconds'],
    limits='Implementation/checkpoint integrity; does not establish task mastery or city transfer.')
assert report['final_sha256']==completion['checkpoints'][-1]['sha256']
(r/'final-integrity.json').open('x').write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
