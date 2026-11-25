"""Native PPO road updates must leave shared-state Wait probabilities intact."""
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_wait_decision import CityWaitDecisionEnv, SCHEDULE
from prepare_city_policy import masked_probs, sha256

torch.set_num_threads(1)
parent = Path('output/training/road-heads-after-wait-smoke-initial-01/start.zip')
candidate = Path('output/training/road-heads-after-wait-ppo-smoke-01/final.zip')
dll = Path('output/wait-decision-build-02/artifacts/bin/TrafficHost/release/TrafficHost.dll')
a = MaskablePPO.load(parent, device='cpu')
b = MaskablePPO.load(candidate, device='cpu')
env = CityWaitDecisionEnv(str(dll))
rows = []
try:
    for i, case in enumerate(SCHEDULE):
        obs, _ = env.reset(options=dict(case=case, scenario_seed=244007000+i))
        mask = env.action_masks()
        x = masked_probs(a, obs, mask)
        y = masked_probs(b, obs, mask)
        error = float(abs(x[0]-y[0]))
        assert error < 1e-6
        conditional_error = float(abs(x[1:]/x[1:].sum()-y[1:]/y[1:].sum()).max())
        rows.append(dict(case=case, wait_error=error, conditional_road_change=conditional_error))
    assert max(row['conditional_road_change'] for row in rows) > 1e-7
    report = dict(parent_sha256=sha256(parent), candidate_sha256=sha256(candidate), host_sha256=sha256(dll),
                  shared_states=rows, max_wait_error=max(row['wait_error'] for row in rows),
                  max_conditional_road_change=max(row['conditional_road_change'] for row in rows),
                  limits='Disposable native PPO integration check. Shared-state invariance does not mean identical trajectories after different road actions.')
    (Path(__file__).parent/'wait-invariance-checks.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
finally:
    env.close()
