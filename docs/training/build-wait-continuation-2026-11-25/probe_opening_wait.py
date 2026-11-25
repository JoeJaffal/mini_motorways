"""Compare Wait choices on identical successful own-policy opening prefixes."""
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv, SMALL_OFFSET
from city_recorded_starts import raw_digest, observation_digest
from prepare_city_policy import masked_probs, sha256

torch.set_num_threads(1)
root = Path.cwd()
out = Path(__file__).parent/'opening-wait-probe'
out.mkdir(exist_ok=False)
dll = root/'output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
bank_path = root/'docs/training/mini-task-repair-2026-11-25/start-bank/starts.json'
bank = json.loads(bank_path.read_text())
assert sha256(dll) == bank['host_sha256']
paths = {'wait32k': root/'output/training/build-wait-01/training/final.zip',
         'wait98k': root/'output/training/build-wait-02/training/final.zip'}
models = {name: MaskablePPO.load(path, device='cpu') for name, path in paths.items()}
config = dict(host_sha256=sha256(dll), bank_sha256=sha256(bank_path),
              models={name: dict(path=str(path), sha256=sha256(path)) for name, path in paths.items()},
              limits='Selected training-bank states, not fresh evaluation. Inflight prefix is after the last construction before observed first delivery; remaining recorded actions are Wait.')
(out/'config.json').write_text(json.dumps(config, indent=2)+'\n')
env = CityCurriculumEnv(str(dll), small_city_horizon=300, allow_bridges=True)
rows = []
try:
    for prefix in bank['starts']:
        if prefix['exercise'] != SMALL_OFFSET:
            continue
        obs, info = env.reset(options=dict(exercise=prefix['exercise'], scenario_seed=prefix['seed']))
        last_build = max(i for i, action in enumerate(prefix['actions']) if action)
        assert all(action == 0 for action in prefix['actions'][last_build+1:])
        captured = []
        for i, action in enumerate(prefix['actions']):
            obs, _, terminal, truncated, info = env.step(action)
            assert not (terminal or truncated)
            phases = []
            if i == last_build:
                phases.append('inflight')
            if i == len(prefix['actions'])-1:
                phases.append('working')
            for phase in phases:
                mask = env.action_masks()
                assert mask[1:].any() and info['road_stock'] > 0 and info['buildings'] == 2
                probs = {name: masked_probs(model, obs, mask).astype(float) for name, model in models.items()}
                for name in probs:
                    probs[name] /= probs[name].sum()
                a, b = (probs[name][1:]/probs[name][1:].sum() for name in ('wait32k', 'wait98k'))
                error = float(abs(a-b).max())
                assert error < 1e-5
                tensor, _ = models['wait32k'].policy.obs_to_tensor(obs)
                with torch.no_grad():
                    context, _ = models['wait32k'].policy.features_extractor.strategy_context(tensor)
                row = dict(prefix_id=prefix['id'], seed=prefix['seed'], phase=phase,
                           seconds=env.raw['time'], trips=info['trips'], stock=info['road_stock'],
                           raw_sha256=raw_digest(env.raw), observation_sha256=observation_digest(obs),
                           wait={name: float(p[0]) for name, p in probs.items()},
                           conditional_road_error=error,
                           context_summary=context[0, -10:].tolist())
                rows.append(row)
                captured.append(phase)
        assert captured == ['inflight', 'working']
        assert raw_digest(env.raw) == prefix['raw_sha256']
        assert observation_digest(obs) == prefix['observation_sha256']
        assert info['trips'] > 0
        print('PREFIX PROBE', prefix['id'], flush=True)
    assert len(rows) == 124
    (out/'states.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    summary = {}
    for phase in ('inflight', 'working'):
        group = [row for row in rows if row['phase'] == phase]
        summary[phase] = dict(states=len(group), scenarios=len({row['seed'] for row in group}),
                             models={name: dict(mean_wait=float(np.mean([row['wait'][name] for row in group])),
                                                below_half=sum(row['wait'][name] < .5 for row in group))
                                     for name in models},
                             largest_drop=min(group, key=lambda row: row['wait']['wait98k']-row['wait']['wait32k']))
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    for name, path in paths.items():
        assert sha256(path) == config['models'][name]['sha256']
    print(json.dumps(summary, indent=2))
finally:
    env.close()
