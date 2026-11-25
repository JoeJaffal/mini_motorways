"""Evaluate a frozen city checkpoint and legal-action controls on paired fresh seeds."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from city_road_pilot import CityRoadEnv
from prepare_city_policy import frozen_game, masked_probs, sha256


def uniform_edges(_model, _obs, mask):
    """Match the starting policy's 50% overall Wait probability."""
    probabilities = mask.astype(np.float64)
    roads = int(mask[1:].sum())
    if roads:
        probabilities[1:] *= .5 / roads
        probabilities[0] = .5
    return probabilities


def uniform_actions(_model, _obs, mask):
    return mask / mask.sum()


def evaluate_shard(dll, checkpoint, shard, destination):
    torch.set_num_threads(1)
    selected = MaskablePPO.load(checkpoint, device='cpu')
    env = CityRoadEnv(dll)
    try:
        scratch = MaskablePPO(selected.policy_class, env, policy_kwargs=selected.policy_kwargs,
                              seed=selected.seed, device='cpu')
        if selected.num_timesteps or selected.policy.optimizer.state:
            raise RuntimeError('Expected the frozen starting checkpoint')
        trials = (
            ('transfer_sampled', selected, masked_probs, False),
            ('transfer_greedy', selected, masked_probs, True),
            ('scratch_sampled', scratch, masked_probs, False),
            ('uniform_edges_matched_wait', None, uniform_edges, False),
            ('uniform_legal_actions', None, uniform_actions, False),
        )
        rows = []
        with destination.open('x') as output:
            for seed, action_seed in shard:
                for name, model, probabilities, greedy in trials:
                    result = frozen_game(env, model, seed, greedy=greedy,
                                         probabilities=probabilities, action_seed=action_seed)
                    row = dict(control=name, action_seed=action_seed, **result)
                    output.write(json.dumps(row) + '\n')
                    rows.append(row)
                output.flush()
                scores = ', '.join(str(row['trips']) for row in rows[-len(trials):])
                print(f'SEED | {seed} | scores [{scores}]', flush=True)
        return rows
    finally:
        env.close()


def summarize(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row['control'], []).append(row)
    stats = {}
    for name, games in groups.items():
        scores = [game['trips'] for game in games]
        stats[name] = dict(
            games=len(games), scoring_games=sum(score > 0 for score in scores),
            mean_score=float(np.mean(scores)), median_score=float(np.median(scores)), best_score=max(scores),
            median_survival_seconds=float(np.median([row['seconds'] for row in games])),
            mean_road_units=float(np.mean([row['road_actions'] for row in games])),
            median_peak_buildings=float(np.median([row['peak_buildings'] for row in games])),
            games_with_weekly_award=sum(row['weekly_awards'] > 0 for row in games),
            native_game_overs=sum(row['native_game_over'] for row in games),
            horizon_truncations=sum(row['truncated'] for row in games),
        )
    transfer = {row['seed']: row['trips'] for row in groups['transfer_sampled']}
    resamples = np.random.default_rng(71299).integers(0, len(transfer), (10000, len(transfer)))
    paired = {}
    for name, games in groups.items():
        if name == 'transfer_sampled':
            continue
        deltas = np.array([transfer[row['seed']] - row['trips'] for row in games])
        paired[name] = dict(wins=int((deltas > 0).sum()), ties=int((deltas == 0).sum()),
                           losses=int((deltas < 0).sum()), mean_score_delta=float(deltas.mean()),
                           paired_bootstrap_95_percent=np.quantile(deltas[resamples].mean(axis=1),
                                                                  [.025, .975]).tolist())
    return stats, paired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--seed-suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    suite = json.loads(args.seed_suite.read_text())
    seeds = [(entry['scenario_seed'], entry['action_seed']) for entry in suite['games']]
    if not 1 <= args.workers <= len(seeds) or len({seed for seed, _ in seeds}) != len(seeds):
        parser.error('Use a nonempty suite of unique scenario seeds and at most one worker per seed')
    checkpoint_hash = sha256(args.checkpoint)
    args.output.mkdir(parents=True, exist_ok=False)
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context('spawn')) as pool:
        jobs = [pool.submit(evaluate_shard, args.dll, args.checkpoint, seeds[i::args.workers],
                            args.output / f'worker-{i:02d}.jsonl') for i in range(args.workers)]
        rows = [row for job in jobs for row in job.result()]
    rows.sort(key=lambda row: (row['seed'], row['control']))
    if len(rows) != len(seeds) * 5 or len({(r['seed'], r['control']) for r in rows}) != len(rows):
        raise RuntimeError('The evaluation did not complete every paired trial exactly once')
    if sha256(args.checkpoint) != checkpoint_hash:
        raise RuntimeError('The starting checkpoint changed during evaluation')
    groups, paired = summarize(rows)
    result = dict(
        games=len(rows), device='cpu', workers=args.workers, elapsed_seconds=perf_counter()-start,
        checkpoint_sha256=checkpoint_hash, host_sha256=sha256(args.dll), suite_sha256=sha256(args.seed_suite),
        groups=groups, transfer_sampled_paired_comparisons=paired,
    )
    (args.output / 'episodes.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
