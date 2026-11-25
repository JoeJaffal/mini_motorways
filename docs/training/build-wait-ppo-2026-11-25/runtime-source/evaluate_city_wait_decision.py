"""Separate first-decision correctness from repeated native play behavior."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_wait_decision import CityWaitDecisionEnv, SCHEDULE, NEEDS_BUILD
from prepare_city_policy import masked_probs, sha256


def worker(dll, checkpoint, jobs, native):
    torch.set_num_threads(1); model = MaskablePPO.load(checkpoint, device='cpu')
    env = CityWaitDecisionEnv(dll, validation=True, bandit=not native); rows = []
    try:
        for case, seed in jobs:
            obs, info = env.reset(options=dict(case=case, scenario_seed=seed))
            initial_stock = info['road_stock']; initial_time = info['seconds']
            initial_served = {b['id']: b['served'] for b in env.raw['buildings'] if not b['isHouse']}
            initial_unserved = [k for k, v in initial_served.items() if v == 0]
            rng = np.random.default_rng(seed+7000)
            mask = env.action_masks(); p = masked_probs(model, obs, mask).astype(float); p /= p.sum()
            correct_probability = 1-p[0] if case in NEEDS_BUILD else p[0]
            first_action = int(rng.choice(len(p), p=p)); first_correct = (first_action != 0) == (case in NEEDS_BUILD)
            obs, reward, terminal, truncated, info = env.step(first_action)
            total = reward
            decisions = 1
            while not env.done:
                if decisions >= 1000:
                    raise RuntimeError('Native review exceeded its decision bound')
                mask = env.action_masks()
                p = mask.astype(float) if mask.sum() == 1 else masked_probs(model, obs, mask).astype(float)
                action = int(rng.choice(len(p), p=p/p.sum()))
                obs, reward, terminal, truncated, info = env.step(action); total += reward
                decisions += 1
            if native:
                assert total == info['native_trips_since_reset']
            else:
                assert total == float(first_correct) and terminal and not truncated
            assert info['weekly_awards'] == 0
            final_served = {b['id']: b['served'] for b in env.raw['buildings'] if not b['isHouse']}
            assert final_served.keys() == initial_served.keys()
            row = dict(case=case, seed=seed, action_seed=seed+7000, first_action=first_action,
                first_correct=first_correct, first_correct_probability=float(correct_probability),
                initial_stock=initial_stock, initial_time=initial_time, final_time=info['seconds'],
                builds=info['road_actions'], remaining_stock=info['road_stock'],
                native_deliveries=info['native_trips_since_reset'],
                native_game_over=terminal if native else info['native_terminated'],
                decisions=decisions,
                all_targets_served=bool(final_served) and all(v > 0 for v in final_served.values()),
                initially_unserved_targets=initial_unserved,
                initially_unserved_now_served=(all(final_served[k] > 0 for k in initial_unserved)
                                              if initial_unserved else None),
                no_build=info['road_actions'] == 0, mode='native' if native else 'one-decision')
            rows.append(row)
            print('WAIT REVIEW', case, seed, 'correct', first_correct, 'builds', row['builds'],
                  'native deliveries', row['native_deliveries'], flush=True)
    finally:
        env.close()
    return rows


def main():
    p = argparse.ArgumentParser()
    for name in ('dll', 'checkpoint', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--workers', type=int, default=2); p.add_argument('--count', type=int, default=16)
    p.add_argument('--seed-start', type=int, default=246000000); p.add_argument('--native', action='store_true')
    a = p.parse_args()
    if min(a.count, a.workers) < 1:
        p.error('Positive count/workers required')
    a.output.mkdir(parents=True, exist_ok=False)
    digest = sha256(a.checkpoint); host = sha256(a.dll)
    jobs = [(case, a.seed_start+i) for case in sorted(set(SCHEDULE)) for i in range(a.count)]
    config = dict(checkpoint=str(a.checkpoint), checkpoint_sha256=digest, host_sha256=host,
        native=a.native, jobs=jobs, workers=a.workers, split='validation', observation_horizon=600,
        limits='First-group correctness and native60second behavior are different metrics. No native city promotion inferred.')
    (a.output/'config.json').write_text(json.dumps(config, indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context('spawn')) as pool:
        futures = [pool.submit(worker, str(a.dll), str(a.checkpoint), jobs[k::a.workers], a.native) for k in range(a.workers)]
        rows = [r for f in futures for r in f.result()]
    assert sha256(a.checkpoint) == digest and sha256(a.dll) == host and len(rows) == len(jobs)
    (a.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    report = {}
    for case in sorted(set(SCHEDULE)):
        g = [r for r in rows if r['case'] == case]
        report[case] = dict(games=len(g), first_correct=sum(r['first_correct'] for r in g),
            mean_correct_probability=float(np.mean([r['first_correct_probability'] for r in g])),
            no_build=sum(r['no_build'] for r in g), scoring=sum(r['native_deliveries'] > 0 for r in g),
            all_targets_served=sum(r['all_targets_served'] for r in g),
            mean_builds=float(np.mean([r['builds'] for r in g])),
            mean_native_deliveries=float(np.mean([r['native_deliveries'] for r in g])))
    (a.output/'summary.json').write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
