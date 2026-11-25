"""Check the opt-in reward/ending against identical native transitions."""
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_route_outcome import CityRouteOutcomeEnv
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT, SMALL_STOCK
from city_recorded_starts import raw_digest, observation_digest
from prepare_city_policy import masked_probs, sha256

torch.set_num_threads(1)
root = Path.cwd()
dll = root/'output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
checkpoint = root/'output/training/mini-fixed-route-01/training/final.zip'
model = MaskablePPO.load(checkpoint, device='cpu')
rows = []
transitions = 0
for fast in (False, True):
    env = CityRouteOutcomeEnv(str(dll), fast_small_city_tail=fast)
    base = CityCurriculumEnv(str(dll), stage='single-connection', allow_bridges=True,
                             collapse_forced_wait=True, small_city_horizon=300,
                             fast_small_city_tail=fast)
    try:
        jobs = [(case, 244008000+i, False) for case in (SMALL_TIGHT, SMALL_STOCK) for i in range(8)]
        jobs += [(SMALL_TIGHT, 244008100, True), (SMALL_STOCK, 244008101, True)]
        for case, seed, only_wait in jobs:
            options = dict(exercise=case, scenario_seed=seed)
            obs, info = env.reset(options=options)
            native_obs, _ = base.reset(options=options)
            rng = np.random.default_rng(seed+4000)
            native_total = task_total = 0.
            zero_cost = 0
            count = 0
            while not env.done:
                assert raw_digest(env.raw) == raw_digest(base.raw)
                assert observation_digest(obs) == observation_digest(native_obs)
                np.testing.assert_array_equal(env.action_masks(), base.action_masks())
                mask = env.action_masks()
                p = mask.astype(float) if mask.sum() == 1 else masked_probs(model, obs, mask).astype(float)
                action = 0 if only_wait else int(rng.choice(len(p), p=p/p.sum()))
                stock = info['road_stock']
                obs, reward, terminal, truncated, info = env.step(action)
                native_obs, native_reward, base_terminal, base_truncated, native_info = base.step(action)
                count += 1
                transitions += 1
                assert count < 2000
                assert raw_digest(env.raw) == raw_digest(base.raw)
                assert observation_digest(obs) == observation_digest(native_obs)
                assert native_reward == info['native_reward']
                for key in ('trips', 'new_deliveries', 'road_stock', 'road_actions', 'wait_actions', 'weekly_awards'):
                    assert info[key] == native_info[key]
                native_total += native_reward
                task_total += reward
                zero_cost += bool(action and info['road_stock'] == stock)
                assert zero_cost == info['zero_cost_builds']
                success = native_info['new_deliveries'] > 0
                expected = 1.+.2*info['road_stock']/info['stock_initial']+.05/(1+info['road_actions']) if success else 0.
                assert abs(reward-expected) < 1e-12
                assert terminal == (success or base_terminal or base_truncated)
                assert not truncated
                if only_wait:
                    assert not success and reward == 0 and info['road_actions'] == 0
            assert native_total == info['trips'] and task_total == info['task_return']
            assert (1 <= task_total <= 1.25) if info['task_success'] else task_total == 0
            rows.append(dict(case=case, seed=seed, only_wait=only_wait, fast=fast,
                             decisions=count, native_trips=info['trips'], native_seconds=info['seconds'],
                             task_return=task_total, success=info['task_success'], paid_units=info['paid_units'],
                             builds=info['road_actions'], zero_cost_builds=zero_cost,
                             forced_tail=info['terminal_observation_may_follow_forced_tail']))
            print('ROUTE CONTRACT', case, seed, fast, info['task_success'], count, flush=True)
    finally:
        env.close()
        base.close()
assert any(row['success'] for row in rows) and any(not row['success'] for row in rows)
assert any(row['zero_cost_builds'] for row in rows)
report = dict(host_sha256=sha256(dll), checkpoint_sha256=sha256(checkpoint),
              matched_native_transitions=transitions, games=rows,
              bounds_and_zero_failure_reward=True, native_states_masks_and_observations_exact=True,
              finite_task_no_bootstrap=True,
              limits='Reward/termination contract only. Frozen existing policy used to generate legal actions; no teacher routes, new learner or performance claim.')
(Path(__file__).parent/'environment-checks.json').write_text(json.dumps(report, indent=2)+'\n')
print('PASS', transitions, 'native transitions', len(rows), 'games', flush=True)
