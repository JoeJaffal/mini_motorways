"""Frozen behavioral audit using city actions; no reference edits queried."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
import city_curriculum as cc
from prepare_city_policy import masked_probs, sha256
from audit_city_roads import assigned_edges
from export_city_replays import action_endpoints, frame

EXERCISES = ('adjacent', 'bend', 'clear', 'obstacle', 'small-city-offset-single', 'small-city-offset-stock', 'small-city-offset-pairs')
ROOT = Path(__file__).resolve().parents[1]

def worker(dll, checkpoint, label, seeds, output):
    torch.set_num_threads(1)
    model = MaskablePPO.load(checkpoint, device='cpu')
    # Audit old geometry using current city Wait semantics, not automatic Finish.
    cc.LESSONS = cc.LESSONS + EXERCISES[:4]
    env = cc.CityCurriculumEnv(dll, validation=True)
    rows = []
    try:
        for ex, seed in seeds:
            obs, info = env.reset(options=dict(exercise=ex, scenario_seed=seed))
            rng = np.random.default_rng(seed+103)
            initial = info['road_stock']; first_time = None; paid = 0
            before_first = 0; after_first = 0; used = set(); purchases = []
            first_arrival_stock = None; frames = [frame(env.raw, 'Start')]
            actions = []; total = 0; zero_time = None
            initial_ids = {b['id'] for b in env.raw['buildings'] if not b['isHouse']}
            for step in range(2000):
                mask = env.action_masks()
                probs = mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
                assert np.isfinite(probs).all() and not probs[~mask].any()
                action = int(rng.choice(len(probs),p=probs/probs.sum()))
                stock = info['road_stock']; native = env.raw['tripsCompleted']
                obs,reward,_,_,info = env.step(action)
                assert reward == env.raw['tripsCompleted']-native
                cost = stock-info['road_stock'] if action else 0
                paid += cost
                if first_time is None: before_first += cost
                else: after_first += cost
                if action: purchases.append((tuple(sorted(action_endpoints(action))),cost))
                total += reward
                if first_time is None and total: first_time = env.raw['time']
                if zero_time is None and info['road_stock']==0: zero_time=env.raw['time']
                shops = [b for b in env.raw['buildings'] if not b['isHouse']]
                if first_arrival_stock is None and any(b['id'] not in initial_ids for b in shops):
                    first_arrival_stock=info['road_stock']
                used.update(assigned_edges(env.raw))
                actions.append(dict(action=action,time=env.raw['time'],reward=reward,cost=cost,stock=info['road_stock']))
                if seed%16==0: frames.append(frame(env.raw,'Build' if action else 'Wait',action_endpoints(action) if action else None))
                if env.done: break
            else: raise RuntimeError('Audit did not terminate')
            assert total==info['trips'] and initial-paid==info['road_stock']
            later=[b for b in shops if b['id'] not in initial_ids]
            row=dict(model=label,exercise=ex,seed=seed,action_seed=seed+103,score=total,success=bool(total),first_delivery=first_time,
                initial_stock=initial,paid=paid,before_first=before_first,after_first=after_first,
                remaining_stock=info['road_stock'],stock_at_arrival=first_arrival_stock,zero_time=zero_time,
                later_exists=bool(later),later_served=any(b['served'] for b in later),
                outside_routes=sum(cost for edge,cost in purchases if edge not in used),decisions=len(actions))
            rows.append(row)
            if seed%16==0:
                data=dict(title=f'{label}: {ex}',intro='Frozen city policy on mini-task geometry; native Wait, 60 seconds.',speed='8',ending='Audit end',frames=frames,terrain=[[i,t] for i,t in enumerate(env.raw['terrain']) if t])
                name=f'{label}-{ex}-{seed}'
                (output/(name+'.json')).write_text(json.dumps(dict(result=row,actions=actions,replay=data)))
                template=(ROOT/'training/stage1_replay.html').read_text()
                (output/(name+'.html')).write_text(template.replace('/*REPLAY_DATA*/',json.dumps(data).replace('<','\\u003c')))
            print('AUDIT',label,ex,seed,total,before_first,after_first,flush=True)
        return rows
    finally: env.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoints',nargs='+',required=True);p.add_argument('--labels',nargs='+',required=True)
    p.add_argument('--count',type=int,default=16);p.add_argument('--seed-start',type=int,default=231000000)
    a=p.parse_args();assert len(a.labels)==len(a.checkpoints)
    a.output.mkdir(parents=True,exist_ok=False);(a.output/'replays').mkdir()
    config=dict(dll=a.dll,host_sha256=sha256(Path(a.dll)),models={l:dict(path=c,sha256=sha256(Path(c))) for l,c in zip(a.labels,a.checkpoints)},exercises=EXERCISES,count=a.count,seed_start=a.seed_start,reference_queries=False,old_geometry_uses_city_wait_60_seconds=True)
    (a.output/'config.json').write_text(json.dumps(config,indent=2))
    jobs=[(ex,a.seed_start+i) for ex in EXERCISES for i in range(a.count)]
    with ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn')) as pool:
        fs=[pool.submit(worker,a.dll,c,l,jobs[k::4],a.output/'replays') for l,c in zip(a.labels,a.checkpoints) for k in range(4)]
        rows=[row for f in fs for row in f.result()]
    (a.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary={}
    for l in a.labels:
        summary[l]={}
        for ex in EXERCISES:
            group=[r for r in rows if r['model']==l and r['exercise']==ex]
            summary[l][ex]={k:float(np.mean([r[k] for r in group])) for k in ('score','success','paid','before_first','after_first','remaining_stock','outside_routes','later_exists','later_served')}
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2))
    assert sha256(Path(a.dll))==config['host_sha256']
    assert all(sha256(Path(c))==config['models'][l]['sha256'] for l,c in zip(a.labels,a.checkpoints))

if __name__=='__main__':main()
