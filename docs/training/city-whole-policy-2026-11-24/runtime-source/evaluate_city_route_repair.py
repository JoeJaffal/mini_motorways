"""Paired native-score checks for the route repair curriculum and the full city."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from audit_city_roads import audit
from city_road_pilot import CityRoadEnv
from evaluate_limited_route_ppo import practice_game
from prepare_city_policy import sha256
from train_limited_route_ppo import EXERCISES, PARTIAL_EXERCISES, LimitedRouteEnv

COHORTS = (*PARTIAL_EXERCISES,*EXERCISES,'city')


def suite(practice_games,city_games,seed,cohorts=COHORTS,zone_offset=0):
    rng=np.random.default_rng(seed)
    jobs=[]
    for index,exercise in enumerate(COHORTS):
        if exercise not in cohorts:
            continue
        count=city_games if exercise=='city' else practice_games
        zone=88_000_000 if exercise=='city' else 87_000_000+100_000*index
        for candidate in rng.choice(100000,count,replace=False):
            jobs.append(dict(exercise=exercise,seed=zone+zone_offset+int(candidate),
                             action_seed=int(rng.integers(100_000_000,2**31))))
    return jobs


def worker(dll,city_dll,checkpoints,jobs):
    torch.set_num_threads(1)
    models=[MaskablePPO.load(path,device='cpu') for path in checkpoints]
    practice=LimitedRouteEnv(dll,validation=True)
    city=CityRoadEnv(city_dll,include_connectivity=True)
    rows=[]
    try:
        for job in jobs:
            scores=[]
            for index,model in enumerate(models):
                result=(audit(city,job['seed'],job['action_seed'],model=model)
                        if job['exercise']=='city' else practice_game(practice,model,job))
                rows.append(dict(result,cohort=job['exercise'],model=index,action_seed=job['action_seed']))
                scores.append(result['trips'])
            print(f'EVAL | {job["exercise"]} {job["seed"]} | {scores}',flush=True)
        return rows
    finally:
        city.close()
        practice.close()


def summarize(rows,count,cohorts):
    values={}
    for index in range(count):
        values[index]={}
        for exercise in cohorts:
            cohort=[r for r in rows if r['cohort']==exercise and r['model']==index]
            parent={r['seed']:r['trips'] for r in rows if r['cohort']==exercise and r['model']==0}
            scores=np.array([r['trips'] for r in cohort])
            deltas=scores-np.array([parent[r['seed']] for r in cohort])
            resamples=np.random.default_rng(803207).integers(len(cohort),size=(10000,len(cohort)))
            row=dict(
                games=len(cohort), scoring=int((scores>0).sum()), mean_score=float(scores.mean()),
                wins=int((deltas>0).sum()), losses=int((deltas<0).sum()),
                paired_mean_delta=float(deltas.mean()),
                paired_bootstrap_95=np.quantile(deltas[resamples].mean(axis=1),[.025,.975]).tolist(),
            )
            if exercise=='city':
                row.update(mean_paid_roads=float(np.mean([r['paid_road_units'] for r in cohort])),
                           mean_outside_observed_routes=float(np.mean([r['paid_units_outside_observed_trip_routes'] for r in cohort])),
                           early_stockouts=sum(r['first_stockout'] is not None and r['first_stockout']<=14 for r in cohort))
            if exercise in ('route-delay','route-gate-two'):
                stocks=[r['gate_stock'] for r in cohort if r['gate_stock'] is not None]
                row.update(retained_stock=sum(n>0 for n in stocks),
                           mean_stock=float(np.mean(stocks)) if stocks else None)
            values[index][exercise]=row
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','city-dll','output'):
        parser.add_argument(f'--{name}',type=Path,required=True)
    parser.add_argument('--checkpoints',type=Path,nargs='+',required=True)
    parser.add_argument('--practice-games',type=int,default=24)
    parser.add_argument('--city-games',type=int,default=16)
    parser.add_argument('--seed',type=int,default=778512)
    parser.add_argument('--zone-offset',type=int,default=0)
    parser.add_argument('--cohorts',nargs='+',choices=COHORTS,default=COHORTS)
    parser.add_argument('--workers',type=int,default=10)
    args=parser.parse_args()
    if min(args.practice_games,args.city_games,args.workers)<1:
        parser.error('Choose positive game and worker counts')
    jobs=suite(args.practice_games,args.city_games,args.seed,args.cohorts,args.zone_offset)
    hashes={str(path):sha256(path) for path in args.checkpoints}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'suite.json').write_text(json.dumps(jobs,indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context('spawn')) as pool:
        futures=[pool.submit(worker,args.dll,args.city_dll,args.checkpoints,jobs[i::args.workers])
                 for i in range(args.workers)]
        rows=[row for future in futures for row in future.result()]
    if len(rows)!=len({(r['model'],r['seed']) for r in rows}) or len(rows)!=len(jobs)*len(args.checkpoints):
        raise RuntimeError('Incomplete or duplicate paired runs')
    if any(sha256(Path(p))!=digest for p,digest in hashes.items()):
        raise RuntimeError('A checkpoint changed during evaluation')
    rows.sort(key=lambda r:(r['cohort'],r['seed'],r['model']))
    (args.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary=dict(games=len(rows),models=[str(path) for path in args.checkpoints],sha256=hashes,
                 results=summarize(rows,len(args.checkpoints),args.cohorts),host_sha256=sha256(args.dll),
                 city_host_sha256=sha256(args.city_dll))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
