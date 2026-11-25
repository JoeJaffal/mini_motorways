"""Paired evaluation of road spending and new-destination service on fresh cities."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from audit_city_service import trace
from prepare_city_policy import sha256

REVIEW_START = 99_000_000


def worker(dll, checkpoints, jobs, horizon=600):
    torch.set_num_threads(1)
    models = [MaskablePPO.load(path, device='cpu') for path in checkpoints]
    rows = []
    for seed, action_seed in jobs:
        scores = []
        for index, model in enumerate(models):
            result = trace(dll,model,seed,action_seed,estimate=False,horizon=horizon)
            result['model'] = index
            rows.append(result)
            scores.append((result['trips'], sum(t['served']>0 for t in result['targets'])))
        print(f'EVAL | {seed} | deliveries and new targets served {scores}',flush=True)
    return rows


def summarize(rows,count):
    groups = {}
    indices = sorted({r['seed'] for r in rows})
    draw = np.random.default_rng(142915).integers(len(indices),size=(12000,len(indices)))
    ref = {r['seed']:r for r in rows if r['model']==0}

    def served(row):
        return sum(t['served']>0 for t in row['targets'])

    def metrics(candidate, measure):
        pair = np.array([measure(candidate[seed])-measure(ref[seed]) for seed in indices])
        return [float(pair.mean()),np.quantile(pair[draw].mean(axis=1),[.025,.975]).tolist()]

    for index in range(count):
        games={r['seed']:r for r in rows if r['model']==index}
        targets=[t for r in games.values() for t in r['targets']]
        service=[t for t in targets if t['served']]
        paid=sum(r['paid_units'] for r in games.values())
        unused=sum(r['outside_routes'] for r in games.values())
        groups[index]=dict(
            games=len(games), scoring_games=sum(r['trips']>0 for r in games.values()),
            mean_score=float(np.mean([r['trips'] for r in games.values()])),
            new_targets=len(targets), new_targets_served=len(service),
            new_target_stockouts=sum(t['arrival_stock']==0 for t in targets),
            median_new_service_delay=(float(np.median([t['first_delivery']-t['first_seen'] for t in service]))
                                      if service else None),
            mean_paid_units=paid/len(games), mean_outside_observed_routes=unused/len(games),
            outside_route_share=unused/paid if paid else 0.,
            paired_score_delta_and_interval=metrics(games,lambda r:r['trips']),
            paired_new_targets_served_delta_and_interval=metrics(games,served),
            paired_outside_observed_routes_delta_and_interval=metrics(games,lambda r:r['outside_routes']),
        )
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--checkpoints',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--games',type=int,default=24)
    parser.add_argument('--seed',type=int,default=274698)
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--horizon',type=int,default=600)
    args=parser.parse_args()
    if not 1<=args.games<=500000 or args.workers<1:
        parser.error('Use positive game and worker counts')
    if not 0<args.horizon<=3600:
        parser.error('Horizon must be between one and 3600 seconds')
    count=min(args.workers,args.games)
    rng=np.random.default_rng(args.seed)
    jobs=[(REVIEW_START+int(seed),int(rng.integers(100_000_000,2**31)))
          for seed in rng.choice(500000,args.games,replace=False)]
    identities={str(path):sha256(path) for path in args.checkpoints}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'suite.json').write_text(json.dumps(jobs,indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=count,mp_context=mp.get_context('spawn')) as pool:
        batches=[pool.submit(worker,args.dll,args.checkpoints,jobs[i::count],args.horizon) for i in range(count)]
        rows=[row for result in batches for row in result.result()]
    if len(rows)!=len({(r['model'],r['seed']) for r in rows}) or len(rows)!=len(jobs)*len(args.checkpoints):
        raise RuntimeError('Missing or duplicate matched games')
    if any(sha256(Path(path))!=digest for path,digest in identities.items()):
        raise RuntimeError('A frozen checkpoint changed during the review')
    rows.sort(key=lambda row:(row['model'],row['seed']))
    (args.output/'games.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    summary=dict(models=list(identities),sha256=identities,host_sha256=sha256(args.dll),horizon=args.horizon,
                 results=summarize(rows,len(args.checkpoints)))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
