"""Sample one repeated training fixture; this is not generalization evidence."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_repeated_mini import CityRepeatedMiniEnv
from city_recorded_starts import raw_digest,observation_digest
from prepare_city_policy import masked_probs,sha256


def worker(dll,checkpoint,seed,jobs,horizon):
    torch.set_num_threads(1);model=MaskablePPO.load(checkpoint,device='cpu')
    env=CityRepeatedMiniEnv(dll,repeat_mini_seed=seed,validation=False,small_city_horizon=horizon,
        collapse_forced_wait=True,fast_small_city_tail=True)
    rows=[]
    try:
        for action_seed in jobs:
            obs,info=env.reset();initial_raw=raw_digest(env.raw);initial_obs=observation_digest(obs)
            rng=np.random.default_rng(action_seed);total=0
            while not env.done:
                mask=env.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
                action=int(rng.choice(len(p),p=p/p.sum()))
                obs,reward,terminal,truncated,info=env.step(action);total+=reward
            assert terminal and not truncated and total==info['trips']
            rows.append(dict(seed=seed,action_seed=action_seed,score=total,success=total>0,
                road_actions=info['road_actions'],remaining_stock=info['road_stock'],seconds=info['seconds'],
                initial_raw_sha256=initial_raw,initial_observation_sha256=initial_obs))
            print('FIXED',seed,action_seed,total,flush=True)
        return rows
    finally:env.close()


def main():
    parser=argparse.ArgumentParser()
    for name in ('dll','checkpoint','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--seed',type=int,required=True);parser.add_argument('--count',type=int,default=32)
    parser.add_argument('--action-seed',type=int,default=622000);parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--horizon',type=int,default=300);a=parser.parse_args()
    if min(a.count,a.workers)<1:parser.error('Positive count/workers required')
    a.output.mkdir(parents=True,exist_ok=False);digest=sha256(a.checkpoint);host=sha256(a.dll)
    config=dict(checkpoint=str(a.checkpoint),checkpoint_sha256=digest,host_sha256=host,seed=a.seed,
        action_seeds=list(range(a.action_seed,a.action_seed+a.count)),horizon=a.horizon,split='train',
        limits='Repeated training fixture with new action draws; not held-out geometry or city transfer.')
    (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool:
        fs=[pool.submit(worker,str(a.dll),str(a.checkpoint),a.seed,config['action_seeds'][k::a.workers],a.horizon) for k in range(a.workers)]
        rows=[r for f in fs for r in f.result()]
    assert sha256(a.checkpoint)==digest and sha256(a.dll)==host
    assert len({r['initial_raw_sha256'] for r in rows})==1 and len({r['initial_observation_sha256'] for r in rows})==1
    (a.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary=dict(games=len(rows),successes=sum(r['success'] for r in rows),mean_score=float(np.mean([r['score'] for r in rows])),**config)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
