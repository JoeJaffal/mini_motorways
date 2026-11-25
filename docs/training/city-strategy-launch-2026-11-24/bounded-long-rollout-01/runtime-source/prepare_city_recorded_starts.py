"""Record native city starting states via policy action histories, not labels."""
import argparse,json,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from city_recorded_starts import raw_digest,observation_digest
from prepare_city_policy import masked_probs,sha256


def collect(dll,checkpoint,seeds,seconds,horizon):
    torch.set_num_threads(1)
    model=MaskablePPO.load(checkpoint,device='cpu')
    env=CityRoadEnv(dll,horizon=horizon,observation_horizon=600,allow_bridges=True)
    rows=[]
    try:
        for seed in seeds:
            obs,info=env.reset(options=dict(scenario_seed=seed))
            rng=np.random.default_rng(seed ^ 0x5a17);actions=[]
            while not env.done and info['seconds']<seconds:
                mask=env.action_masks()
                p=mask.astype(np.float64) if mask.sum()==1 else masked_probs(model,obs,mask).astype(np.float64)
                action=int(rng.choice(len(p),p=p/p.sum()));actions.append(action)
                obs,_,_,_,info=env.step(action)
                if len(actions)>20000:raise RuntimeError('Prefix exceeded decision bound')
            keep=not env.done and info['trips']>0
            row=dict(seed=seed,seconds=info['seconds'],trips=info['trips'],road_stock=info['road_stock'],kept=keep)
            if keep:row.update(actions=actions,raw_sha256=raw_digest(env.raw),observation_sha256=observation_digest(obs))
            else:row['reason']='Native game ended or no completed service at fixed prefix time'
            rows.append(row)
            print(f'PREFIX | {seed} | kept={keep} | score={info["trips"]} | time={info["seconds"]}',flush=True)
    finally:env.close()
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','checkpoint','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--seed-start',type=int,required=True);p.add_argument('--count',type=int,default=128)
    p.add_argument('--workers',type=int,default=8);p.add_argument('--seconds',type=int,default=280)
    p.add_argument('--horizon',type=int,default=1200)
    a=p.parse_args()
    if min(a.count,a.workers,a.seconds)<1 or not a.seconds<a.horizon<=3600:p.error('Invalid prefix bounds')
    a.output.mkdir(parents=True,exist_ok=False);identity=sha256(a.checkpoint);host=sha256(a.dll)
    seeds=list(range(a.seed_start,a.seed_start+a.count));count=min(a.workers,a.count)
    with ProcessPoolExecutor(max_workers=count,mp_context=mp.get_context('spawn')) as pool:
        tasks=[pool.submit(collect,a.dll,a.checkpoint,seeds[i::count],a.seconds,a.horizon) for i in range(count)]
        rows=sorted([r for task in tasks for r in task.result()],key=lambda r:r['seed'])
    assert sha256(a.checkpoint)==identity and sha256(a.dll)==host
    starts=[r for r in rows if r['kept']]
    result=dict(schema='native-city-starts-v1',host_sha256=host,checkpoint=str(a.checkpoint),checkpoint_sha256=identity,
                prefix_seconds=a.seconds,seed_start=a.seed_start,requested=a.count,allow_bridges=True,
                starts=starts,excluded=[r for r in rows if not r['kept']],
                note='Prefix actions only reconstruct an initial state during reset; never imitation targets, learner actions, or reward. No future state selected the prefix actions.')
    (a.output/'starts.json').write_text(json.dumps(result,indent=2)+'\n')
    if not starts:raise RuntimeError('No live serving prefixes; do not train from this manifest')
    print(json.dumps(dict(kept=len(starts),excluded=len(rows)-len(starts),path=str(a.output/'starts.json'))))
if __name__=='__main__':main()
