"""Compare the opening pilot with its frozen overnight parent."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import CityRoadEnv
from diagnose_city_policy import play
from prepare_city_policy import sha256
from train_city_opening_pilot import DEV_END, DEV_START, HORIZON, OBSERVATION_HORIZON, opening_has_route


def create_suite(dll, per_cohort):
    rng = np.random.default_rng(702093)
    candidates = iter(rng.choice(DEV_END-DEV_START, size=500, replace=False) + DEV_START)
    env = CityRoadEnv(dll)
    jobs = []
    try:
        for cohort in ('closed', 'ordinary'):
            for _ in range(per_cohort):
                while True:
                    seed = int(next(candidates))
                    env.reset(options={'scenario_seed':seed})
                    closed = not opening_has_route(env.raw, env.action_masks())
                    if cohort == 'ordinary' or closed:
                        break
                jobs.append(dict(index=len(jobs), cohort=cohort, seed=seed, closed_mask=closed,
                                 action_seed=int(rng.integers(100_000_000, 2**31)), horizon=HORIZON))
    finally:
        env.close()
    return dict(scenario_seed_range=[DEV_START, DEV_END], generator_seed=702093, jobs=jobs)


def shard(dll, paths, jobs):
    torch.set_num_threads(1)
    models = [MaskablePPO.load(path, device='cpu') for path in paths]
    env = CityRoadEnv(dll, horizon=HORIZON, observation_horizon=OBSERVATION_HORIZON,
                      include_connectivity=True)
    try:
        rows = []
        for job in jobs:
            scores = []
            for label, model in zip(('parent', 'midpoint', 'final'), models):
                result = play(env, model, job)
                scores.append(result['trips'])
                rows.append(dict(model=label, model_decisions=model.num_timesteps, **result))
            print(f'DEV | {job["cohort"]} {job["seed"]} | scores {scores}', flush=True)
        return rows
    finally:
        env.close()


def measure(games, parent):
    scores = np.array([g['trips'] for g in games])
    deltas = scores - np.array([parent[g['seed']]['trips'] for g in games])
    draws = np.random.default_rng(28811).integers(len(games), size=(10000, len(games)))
    first = [g['first_score'] for g in games if g['first_score'] is not None]
    return dict(
        episodes=len(games), mean_score=float(scores.mean()), scoring_games=int((scores > 0).sum()),
        score_by_600=float(np.mean([g['score_by_600'] for g in games])),
        median_first_delivery=float(np.median(first)) if first else None,
        early_stockouts=sum(g['first_stockout'] is not None and g['first_stockout']<=14 for g in games),
        no_route=sum(g['first_route'] is None for g in games),
        survived_ten_minutes=sum(g['seconds']>600 for g in games),
        unsupplied_end_after_ten_minutes=sum(g['seconds']>600 and g['native_game_over']
                                          and not g['worst_destination']['supplied'] for g in games),
        mean_score_after_600=float(np.mean([g['trips']-g['score_by_600'] for g in games])),
        paired_wins=int((deltas>0).sum()), paired_ties=int((deltas==0).sum()),
        paired_losses=int((deltas<0).sum()), paired_mean_delta=float(deltas.mean()),
        paired_bootstrap_95=np.quantile(deltas[draws].mean(axis=1), [.025,.975]).tolist(),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--build-suite', type=int, metavar='GAMES_PER_COHORT')
    parser.add_argument('--checkpoints', nargs=3, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if args.build_suite is not None:
        if not 1 <= args.build_suite <= 32:
            parser.error('Choose between one and 32 games per cohort')
        with args.suite.open('x') as file:
            json.dump(create_suite(args.dll,args.build_suite),file,indent=2)
            file.write('\n')
        return
    if not args.checkpoints or not args.output:
        parser.error('Evaluation requires parent, midpoint and final checkpoints and a fresh output directory')
    jobs = json.loads(args.suite.read_text())['jobs']
    if not 1 <= args.workers <= len(jobs) or len({j['seed'] for j in jobs})!=len(jobs):
        parser.error('Choose a worker count supported by the distinct scenario seeds')
    identities = {str(path):sha256(path) for path in args.checkpoints}
    args.output.mkdir(parents=True, exist_ok=False)
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context('spawn')) as pool:
        futures = [pool.submit(shard,args.dll,args.checkpoints,jobs[i::args.workers]) for i in range(args.workers)]
        rows = [row for future in futures for row in future.result()]
    rows.sort(key=lambda row:(row['index'],row['model_decisions']))
    if len({(g['model'],g['seed']) for g in rows})!=3*len(jobs) or len(rows)!=3*len(jobs):
        raise RuntimeError('Incomplete paired evaluation')
    if any(sha256(Path(path))!=digest for path,digest in identities.items()):
        raise RuntimeError('Checkpoint changed during evaluation')
    parent = {g['seed']:g for g in rows if g['model']=='parent'}
    results = {
        model:{cohort:measure([g for g in rows if g['model']==model and (cohort=='all' or g['cohort']==cohort)],
                              parent)
               for cohort in ('closed','ordinary','all')}
        for model in ('parent','midpoint','final')
    }
    summary = dict(games=len(rows), host_sha256=sha256(args.dll), suite_sha256=sha256(args.suite),
                   checkpoints=identities, groups=results)
    (args.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
