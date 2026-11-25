"""Compare frozen checkpoints on the same new-destination and full-city cases."""

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
from prepare_city_policy import masked_probs, sha256
from train_midgame_service import DELAY, OPEN, MidgameServiceEnv

COHORTS = (OPEN, DELAY, 'city')


def exercise_game(env, model, job, *, hold_for_gate=False):
    if hold_for_gate and job['cohort'] != DELAY:
        raise ValueError('Gate timing control requires a delayed fixture')
    obs, _ = env.reset(options={'scenario_seed':job['seed'],'exercise':job['cohort']})
    rng = np.random.default_rng(job['action_seed'])
    total = 0
    while not env.done:
        mask = env.action_masks()
        p = masked_probs(model,obs,mask).astype(np.float64)
        if not np.isfinite(p).all() or p[~mask].any():
            raise RuntimeError('Invalid masked selection')
        action = int(rng.choice(len(p),p=p/p.sum()))
        if hold_for_gate and env.stock_at_gate is None:
            action = 0
        obs, reward, _, _, info = env.step(action)
        total += reward
    if total!=info['trips'] or total!=info['new_deliveries']+info['existing_deliveries']:
        raise RuntimeError('Native destination and total scores differ')
    return info


def worker(dll, city_dll, checkpoints, jobs):
    torch.set_num_threads(1)
    models = [MaskablePPO.load(path,device='cpu') for path in checkpoints]
    env = MidgameServiceEnv(dll,validation=True)
    city = CityRoadEnv(city_dll,include_connectivity=True)
    rows = []
    try:
        for job in jobs:
            scores=[]
            for index,model in enumerate(models):
                result=(audit(city,job['seed'],job['action_seed'],model=model)
                        if job['cohort']=='city' else exercise_game(env,model,job))
                rows.append(dict(result,model=index,cohort=job['cohort'],action_seed=job['action_seed']))
                scores.append(result.get('new_deliveries',result['trips']))
            print(f'EVAL | {job["cohort"]} {job["seed"]} | {scores}',flush=True)
        return rows
    finally:
        city.close()
        env.close()


def summarize(rows, count):
    result = {}
    for index in range(count):
        result[index]={}
        for cohort in COHORTS:
            games=[row for row in rows if row['model']==index and row['cohort']==cohort]
            baseline={row['seed']:row for row in rows if row['model']==0 and row['cohort']==cohort}
            scope='trips' if cohort=='city' else 'new_deliveries'
            scores=np.array([r[scope] for r in games])
            deltas=scores-np.array([baseline[r['seed']][scope] for r in games])
            draws=np.random.default_rng(504978).integers(len(games),size=(12000,len(games)))
            row=dict(games=len(games),scoring=int((scores>0).sum()),mean_score=float(scores.mean()),
                     paired_mean_delta=float(deltas.mean()),
                     paired_bootstrap_95=np.quantile(deltas[draws].mean(axis=1),[.025,.975]).tolist())
            if cohort=='city':
                row.update(paid_units=float(np.mean([g['paid_road_units'] for g in games])),
                           outside_routes=float(np.mean([g['paid_units_outside_observed_trip_routes'] for g in games])))
            else:
                served=[g for g in games if g['new_deliveries']>0]
                row.update(existing_mean=float(np.mean([g['existing_deliveries'] for g in games])),
                           total_mean=float(np.mean([g['trips'] for g in games])),
                           first_delivery_seconds=float(np.median([g['first_new_delivery'] for g in served])) if served else None,
                           paid_at_first=float(np.mean([g['paid_at_first_new_delivery'] for g in served])) if served else None,
                           paid_all=float(np.mean([g['stock_initial']-g['road_stock'] for g in games])))
                if cohort==DELAY:
                    row['retained_at_gate']=sum((g['stock_at_gate'] or 0)>0 for g in games)
            result[index][cohort]=row
    return result


def create_suite():
    rng=np.random.default_rng(665352)
    jobs=[]
    for cohort,first,count in ((OPEN,94_500_000,24),(DELAY,94_600_000,24),('city',95_100_000,20)):
        for offset in rng.choice(100000,count,replace=False):
            jobs.append(dict(cohort=cohort,seed=first+int(offset),
                             action_seed=int(rng.integers(100_000_000,2**31))))
    return jobs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','city-dll','output'):
        parser.add_argument(f'--{name}',type=Path,required=True)
    parser.add_argument('--checkpoints',nargs='+',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=10)
    args=parser.parse_args()
    jobs=create_suite()
    if not 1<=args.workers<=len(jobs):
        parser.error('Worker count must fit the evaluation suite')
    identities={str(p):sha256(p) for p in args.checkpoints}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'suite.json').write_text(json.dumps(jobs,indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context('spawn')) as pool:
        futures=[pool.submit(worker,args.dll,args.city_dll,args.checkpoints,jobs[i::args.workers])
                 for i in range(args.workers)]
        rows=[row for future in futures for row in future.result()]
    if len(rows)!=len(jobs)*len(args.checkpoints) or len(rows)!=len({(r['model'],r['seed']) for r in rows}):
        raise RuntimeError('Incomplete matched evaluation')
    if any(sha256(Path(p))!=h for p,h in identities.items()):
        raise RuntimeError('A checkpoint changed during evaluation')
    rows.sort(key=lambda r:(r['cohort'],r['seed'],r['model']))
    (args.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary=dict(games=len(rows),models=list(identities),sha256=identities,
                 results=summarize(rows,len(args.checkpoints)),host_sha256=sha256(args.dll),
                 city_host_sha256=sha256(args.city_dll))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
