"""Compare frozen action distributions on identical native replay states."""
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256

root=Path('docs/training/mini-task-repair-2026-11-25');replays=root/'reset-regression-replay'
selection=json.loads((replays/'selection.json').read_text())
torch.set_num_threads(1)
models={label:MaskablePPO.load(meta['path'],device='cpu') for label,meta in selection['models'].items()}
dll='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
rows=[]
for trajectory in models:
    expected=selection[trajectory];env=CityRoadEnv(dll,horizon=600,observation_horizon=600,allow_bridges=True)
    try:
        obs,info=env.reset(options=dict(scenario_seed=expected['seed']))
        for step in map(json.loads,(replays/trajectory/'steps.jsonl').read_text().splitlines()):
            mask=env.action_masks();action=step['action'];assert mask[action]
            if mask[1:].any():
                p={label:masked_probs(model,obs,mask).astype(float) for label,model in models.items()}
                road={label:value[1:]/value[1:].sum() for label,value in p.items() if value[1:].sum()>0}
                rows.append(dict(trajectory=trajectory,seconds=info['seconds'],stock=info['road_stock'],
                    original_wait=float(p['original'][0]),reset_wait=float(p['reset_final'][0]),
                    conditional_road_tv=float(np.abs(road['original']-road['reset_final']).sum()/2) if len(road)==2 else None,
                    action=action,original_probability=float(p['original'][action]),reset_probability=float(p['reset_final'][action])))
            obs,reward,_,_,info=env.step(action)
            assert (info['seconds'],info['road_stock'],reward)==(step['time'],step['stock'],step['reward'])
            if info['seconds']>=150 or env.done:break
    finally:env.close()
summary={}
for trajectory in models:
    summary[trajectory]={}
    for label,cutoff in [('first14seconds',14),('opening31seconds',31),('all_probed',150)]:
        group=[r for r in rows if r['trajectory']==trajectory and r['seconds']<=cutoff]
        summary[trajectory][label]=dict(states=len(group),
            original_wait=float(np.mean([r['original_wait'] for r in group])),
            reset_wait=float(np.mean([r['reset_wait'] for r in group])),
            conditional_road_tv=float(np.mean([r['conditional_road_tv'] for r in group if r['conditional_road_tv'] is not None])))
for label,meta in selection['models'].items():assert sha256(Path(meta['path']))==meta['sha256']
(root/'reset-policy-drift.json').write_text(json.dumps(dict(summary=summary,rows=rows,
    limits='Two selected trajectories from one development city; distribution changes are measured on identical states, not a causal ablation or generalization estimate.'),indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
