"""Compare starting and trained city checkpoints on the same development seeds."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import CityRoadEnv
from prepare_city_policy import frozen_game, sha256


def evaluate_shard(dll, checkpoints, shard):
    torch.set_num_threads(1)
    policies = [MaskablePPO.load(path, device='cpu') for path in checkpoints]
    env = CityRoadEnv(dll)
    rows = []
    try:
        for seed, action_seed in shard:
            start = len(rows)
            for model in policies:
                for greedy in (False, True):
                    game = frozen_game(env, model, seed, greedy=greedy, action_seed=action_seed)
                    rows.append(dict(checkpoint_decisions=model.num_timesteps, action_seed=action_seed, **game))
            scores = [row['trips'] for row in rows[start:]]
            print(f'DEV | {seed} | sampled/greedy per checkpoint {scores}', flush=True)
        return rows
    finally:
        env.close()


def summarize(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row['checkpoint_decisions'], row['greedy']), []).append(row)
    for (decisions, greedy), games in sorted(groups.items()):
        scores = np.array([row['trips'] for row in games])
        initial = {row['seed']: row['trips'] for row in groups[(0, greedy)]}
        deltas = scores - np.array([initial[row['seed']] for row in games])
        resamples = np.random.default_rng(84283).integers(len(games), size=(10000, len(games)))
        yield dict(
            checkpoint_decisions=decisions, mode='greedy' if greedy else 'sampled',
            total_games=len(games), scoring_games=int((scores > 0).sum()),
            mean_score=float(scores.mean()), median_score=float(np.median(scores)), best_score=int(scores.max()),
            median_survival_seconds=float(np.median([r['seconds'] for r in games])),
            mean_road_units=float(np.mean([r['road_actions'] for r in games])),
            mean_wait_actions=float(np.mean([r['wait_actions'] for r in games])),
            games_with_weekly_award=sum(r['weekly_awards'] > 0 for r in games),
            games_with_no_roads=sum(r['road_actions'] == 0 for r in games),
            games_with_empty_stock=sum(r['road_stock'] == 0 for r in games),
            horizon_truncations=sum(r['truncated'] for r in games),
            paired_score_delta=float(deltas.mean()), paired_wins=int((deltas > 0).sum()),
            paired_ties=int((deltas == 0).sum()), paired_losses=int((deltas < 0).sum()),
            paired_bootstrap_95_percent=np.quantile(deltas[resamples].mean(axis=1), [.025, .975]).tolist(),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--checkpoints', type=Path, nargs='+', required=True)
    parser.add_argument('--seed-suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    suite = json.loads(args.seed_suite.read_text())
    seeds = [(entry['scenario_seed'], entry['action_seed']) for entry in suite['games']]
    if not 1 <= args.workers <= len(seeds) or len({seed for seed, _ in seeds}) != len(seeds):
        parser.error('Use unique scenario seeds and at most one worker per seed')
    identities = {str(path): sha256(path) for path in args.checkpoints}
    args.output.mkdir(parents=True, exist_ok=False)
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context('spawn')) as pool:
        jobs = [pool.submit(evaluate_shard, args.dll, args.checkpoints, seeds[i::args.workers])
                for i in range(args.workers)]
        rows = [row for job in jobs for row in job.result()]
    matches = {(r['checkpoint_decisions'], r['seed'], r['greedy']) for r in rows}
    expected = len(seeds) * len(args.checkpoints) * 2
    if len(rows) != expected or len(matches) != expected:
        raise RuntimeError('Incomplete or duplicate paired city evaluation')
    if any(sha256(Path(path)) != digest for path, digest in identities.items()):
        raise RuntimeError('Checkpoint changed during evaluation')
    rows.sort(key=lambda r: (r['checkpoint_decisions'], r['greedy'], r['seed']))
    result = dict(games=len(rows), checkpoints=identities, host_sha256=sha256(args.dll),
                  suite_sha256=sha256(args.seed_suite), measurements=list(summarize(rows)))
    (args.output / 'episodes.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
