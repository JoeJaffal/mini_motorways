"""Frozen first-delivery practice evaluation; no reference route queries."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_route_outcome import CityRouteOutcomeEnv
from city_curriculum import SMALL_TIGHT, SMALL_STOCK
from prepare_city_policy import masked_probs, sha256


def play(dll, checkpoint, exercise, seed, action_seed):
    torch.set_num_threads(1)
    model = MaskablePPO.load(checkpoint, device='cpu')
    env = CityRouteOutcomeEnv(dll, validation=True, fast_small_city_tail=True)
    try:
        obs, info = env.reset(options=dict(exercise=exercise, scenario_seed=seed))
        rng = np.random.default_rng(action_seed)
        total = 0.
        decisions = 0
        while not env.done:
            mask = env.action_masks()
            probs = mask.astype(float) if mask.sum() == 1 else masked_probs(model, obs, mask).astype(float)
            action = int(rng.choice(len(probs), p=probs/probs.sum()))
            obs, reward, terminal, truncated, info = env.step(action)
            total += reward
            decisions += 1
            assert decisions < 1000 and not truncated
        assert terminal and total == info['task_return']
        return dict(info, action_seed=action_seed, decisions=decisions)
    finally:
        env.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dll', 'checkpoint', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--count', type=int, default=32)
    p.add_argument('--seed-start', type=int, default=249000000)
    a = p.parse_args()
    if min(a.workers, a.count) < 1:
        p.error('Positive workers/count required')
    a.output.mkdir(parents=True, exist_ok=False)
    config = dict(checkpoint=str(a.checkpoint), checkpoint_sha256=sha256(a.checkpoint),
                  host_sha256=sha256(a.dll), seed_start=a.seed_start, count=a.count,
                  scope='Development practice, not city score or independent confirmation')
    (a.output/'config.json').write_text(json.dumps(config, indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context('spawn')) as pool:
        jobs = [pool.submit(play, str(a.dll), str(a.checkpoint), exercise, a.seed_start+i, 641000+i)
                for exercise in (SMALL_TIGHT, SMALL_STOCK) for i in range(a.count)]
        rows = [job.result() for job in jobs]
    summary = {}
    for exercise in (SMALL_TIGHT, SMALL_STOCK):
        games = [row for row in rows if row['exercise'] == exercise]
        summary[exercise] = dict(games=len(games), successes=sum(r['task_success'] for r in games),
            mean_return=float(np.mean([r['task_return'] for r in games])),
            mean_paid=float(np.mean([r['paid_units'] for r in games])),
            mean_builds=float(np.mean([r['road_actions'] for r in games])),
            mean_decisions=float(np.mean([r['decisions'] for r in games])))
    assert sha256(a.checkpoint) == config['checkpoint_sha256'] and sha256(a.dll) == config['host_sha256']
    (a.output/'games.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    (a.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
