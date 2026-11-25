"""Frozen native curriculum checks; named reference edits are evaluation controls only."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv, LESSONS, JOIN, ROUTE, DELAY, QUIET, PRIORITY, SWAP
from city_road_pilot import edge_action
from prepare_city_policy import masked_probs, sha256


def play(env, exercise, seed, action_seed, model=None, control='wait'):
    obs,initial=env.reset(options=dict(scenario_seed=seed,exercise=exercise))
    controls=env.host.call(command='curriculumReference')['edits']
    labels={r['kind']:edge_action((r['x'],r['y']),(r['toX'],r['toY'])) for r in controls}
    sequence=[edge_action((r['x'],r['y']),(r['toX'],r['toY'])) for r in controls] if control=='route' else ([labels[control]] if control in labels else [])
    rng=np.random.default_rng(action_seed); reward=0.;first_probs=None; decisions=0
    while not env.done:
        mask=env.action_masks()
        if model is not None:
            p=masked_probs(model,obs,mask).astype(float);p/=p.sum()
            if first_probs is None:first_probs={'wait':p[0],**{key:p[slot] for key,slot in labels.items()}}
            action=int(rng.choice(len(p),p=p))
        else:
            action=sequence.pop(0) if sequence and mask[sequence[0]] else 0
        obs,r,_,_,info=env.step(action);reward+=r;decisions+=1
        if decisions>1000:raise RuntimeError('Unexpected nontermination')
        if not env.observation_space.contains(obs):raise RuntimeError('Invalid observation')
    assert reward==info['trips']==sum(info['served'].values())
    info.update(action_seed=action_seed,first_probabilities=first_probs,
                first_road=next((k for k,a in labels.items() if a==info['first_action']), 'other' if info['first_action'] else 'wait'),
                success=info['urgent_deliveries']>0 if exercise in (PRIORITY,SWAP) else info['new_deliveries']>0)
    return info


def worker(dll, paths, exercise, seed, action_seed, controls):
    torch.set_num_threads(1)
    env=CityCurriculumEnv(dll,validation=True)
    try:
        rows=[]
        for index,path in enumerate(paths):
            row=play(env,exercise,seed,action_seed,MaskablePPO.load(path,device='cpu'))
            rows.append(dict(row,model=str(index)))
        if controls:
            names=('wait','route') if exercise in (JOIN,ROUTE,DELAY) else ('wait',) if exercise==QUIET else ('wait','upper','lower') if exercise in (PRIORITY,SWAP) else ('wait','feeder','separate-exit')
            for name in names:rows.append(dict(play(env,exercise,seed,action_seed,control=name),model=name))
        print(f'EVAL | {exercise} | {seed} | '+str([(r['model'],r['trips']) for r in rows]),flush=True)
        return rows
    finally:env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dll',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoints',type=Path,nargs='*',default=[])
    p.add_argument('--lessons',nargs='+',choices=LESSONS,default=LESSONS)
    p.add_argument('--count',type=int,default=8);p.add_argument('--seed-start',type=int,default=118200000)
    p.add_argument('--controls',action='store_true');p.add_argument('--workers',type=int,default=8)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    if args.count<1 or args.workers<1: p.error('Positive counts required')
    config=dict(models=list(map(str,args.checkpoints)),hashes={str(x):sha256(x) for x in args.checkpoints},dll=str(args.dll),host_sha256=sha256(args.dll),seed_start=args.seed_start,count=args.count,lessons=args.lessons)
    (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    jobs=[(ex,args.seed_start+i,74111+i) for ex in args.lessons for i in range(args.count)]
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(worker,args.dll,args.checkpoints,*job,args.controls) for job in jobs]
        rows=[r for f in futures for r in f.result()]
    (args.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary={}
    for ex in args.lessons:
        summary[ex]={}
        for index in sorted({r['model'] for r in rows if r['exercise']==ex}):
            games=[r for r in rows if r['exercise']==ex and r['model']==index]
            summary[ex][index]=dict(games=len(games),mean_score=float(np.mean([r['trips'] for r in games])),successes=sum(r['success'] for r in games),mean_builds=float(np.mean([r['road_actions'] for r in games])),mean_stock=float(np.mean([r['road_stock'] for r in games])),mean_urgent_deliveries=float(np.mean([r['urgent_deliveries'] for r in games])))
    assert all(sha256(Path(x))==h for x,h in config['hashes'].items()) and sha256(args.dll)==config['host_sha256']
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')

if __name__=='__main__':main()
