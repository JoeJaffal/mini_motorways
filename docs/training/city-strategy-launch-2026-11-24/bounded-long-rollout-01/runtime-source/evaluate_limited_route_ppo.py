"""Compare route exercise checkpoints and measure retention in fresh growing cities."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import CityRoadEnv
from prepare_city_policy import frozen_game, masked_probs, sha256
from train_limited_route_ppo import EXERCISES, LimitedRouteEnv, VALIDATION_START

LABELS = ('parent','openings','mixed-delay')


def practice_game(env, model, job):
    obs, _ = env.reset(options=dict(scenario_seed=job['seed'],exercise=job['exercise']))
    rng = np.random.default_rng(job['action_seed'])
    reward_total = 0
    delayed = job['exercise'] in ('route-delay','route-gate-two')
    blocked = env.raw['terrain'].count(2) if delayed else None
    gate_time = gate_stock = None
    while not env.done:
        mask = env.action_masks()
        p = masked_probs(model,obs,mask).astype(np.float64)
        if not np.isfinite(p).all() or p[~mask].any():
            raise RuntimeError('Policy violated the native exercise mask')
        action = int(rng.choice(len(p),p=p/p.sum()))
        obs, reward, _, _, info = env.step(action)
        reward_total += reward
        if delayed and gate_time is None and env.raw['terrain'].count(2) < blocked:
            gate_time, gate_stock = info['seconds'], info['road_stock']
    if reward_total != info['trips']:
        raise RuntimeError('Exercise reward disagreed with native deliveries')
    return dict(**info, gate_time=gate_time, gate_stock=gate_stock)


def evaluate_worker(dll, city_dll, paths, jobs):
    torch.set_num_threads(1)
    models = [MaskablePPO.load(path,device='cpu') for path in paths]
    practice = LimitedRouteEnv(dll,validation=True)
    city = CityRoadEnv(city_dll)
    rows = []
    try:
        for job in jobs:
            results = []
            for label, model in zip(LABELS,models):
                result = (frozen_game(city,model,job['seed'],action_seed=job['action_seed'])
                          if job['exercise']=='city' else practice_game(practice,model,job))
                results.append(result['trips'])
                rows.append(dict(**result,cohort=job['exercise'],model=label,
                                 action_seed=job['action_seed']))
            print(f'EVAL | {job["exercise"]} {job["seed"]} | {results}',flush=True)
        return rows
    finally:
        city.close()
        practice.close()


def summarize(rows):
    groups = {}
    for label in LABELS:
        groups[label] = {}
        for cohort in (*EXERCISES,'city'):
            games = [r for r in rows if r['model']==label and r['cohort']==cohort]
            parent = {r['seed']:r for r in rows if r['model']=='parent' and r['cohort']==cohort}
            scores = np.array([r['trips'] for r in games])
            deltas = scores - np.array([parent[r['seed']]['trips'] for r in games])
            draws = np.random.default_rng(158730).integers(len(games),size=(10000,len(games)))
            scoring = [r for r in games if r['trips']>0]
            entry = dict(total=len(games),scoring=len(scoring),score_mean=float(scores.mean()),
                         median_seconds=float(np.median([r['seconds'] for r in games])),
                         paired_wins=int((deltas>0).sum()),paired_ties=int((deltas==0).sum()),
                         paired_losses=int((deltas<0).sum()),mean_delta=float(deltas.mean()),
                         paired_bootstrap_95=np.quantile(deltas[draws].mean(axis=1),[.025,.975]).tolist())
            if cohort != 'city':
                entry.update(mean_paid_units=float(np.mean([r['spent'] for r in games])),
                             mean_paid_units_on_success=(float(np.mean([r['spent'] for r in scoring]))
                                                         if scoring else None))
            if cohort == 'route-delay':
                stocks = [r['gate_stock'] for r in games if r['gate_stock'] is not None]
                entry.update(games_reaching_gate=len(stocks),
                             games_with_stock_when_gate_opens=sum(stock > 0 for stock in stocks),
                             mean_stock_when_gate_opens=float(np.mean(stocks)) if stocks else None)
            groups[label][cohort] = entry
    return groups


def make_suite():
    rng = np.random.default_rng(655103)
    jobs = []
    for index, exercise in enumerate(EXERCISES):
        for i in range(32):
            jobs.append(dict(exercise=exercise,seed=VALIDATION_START+index*100+i,
                             action_seed=int(rng.integers(100_000_000,2**31))))
    for seed in rng.choice(100000,16,replace=False):
        jobs.append(dict(exercise='city',seed=int(seed)+85_100_000,
                         action_seed=int(rng.integers(100_000_000,2**31))))
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--city-dll',type=Path,required=True)
    parser.add_argument('--checkpoints',type=Path,nargs=3,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=8)
    args = parser.parse_args()
    jobs = make_suite()
    if not 1<=args.workers<=len(jobs):
        parser.error('Choose a positive number of workers up to the number of games')
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'suite.json').write_text(json.dumps(jobs,indent=2)+'\n')
    identities = {str(p):sha256(p) for p in args.checkpoints}
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context('spawn')) as pool:
        futures = [pool.submit(evaluate_worker,args.dll,args.city_dll,args.checkpoints,jobs[i::args.workers])
                   for i in range(args.workers)]
        rows = [row for future in futures for row in future.result()]
    if len(rows)!=len({(r['seed'],r['cohort'],r['model']) for r in rows}) or len(rows)!=3*len(jobs):
        raise RuntimeError('Incomplete paired games')
    if any(sha256(Path(p))!=h for p,h in identities.items()):
        raise RuntimeError('Unexpected evaluation checkpoint change')
    rows.sort(key=lambda r:(r['cohort'],r['seed'],r['model']))
    (args.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary = dict(games=len(rows),groups=summarize(rows),checkpoints=identities,
                   practice_host_sha256=sha256(args.dll),city_host_sha256=sha256(args.city_dll))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
