"""Collect reset states from a frozen policy's own successful native games.

Recorded actions reconstruct initial states only; they are never PPO labels.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT, SMALL_OFFSET
from city_recorded_starts import raw_digest, observation_digest
from environment import DIRS
from prepare_city_policy import masked_probs, sha256

def collect(dll, checkpoint, jobs):
    torch.set_num_threads(1);model=MaskablePPO.load(checkpoint,device='cpu')
    env=CityCurriculumEnv(dll);starts=[];games=[]
    try:
        for ex,seed,action_seed in jobs:
            obs,info=env.reset(options=dict(exercise=ex,scenario_seed=seed))
            pts=[]
            for b in env.raw['buildings']:
                d=DIRS[b['drivewayDirection']];p=b['entrance'];pts.append((p['x']+d[0],p['y']+d[1]))
            distance=max(abs(a-b) for a,b in zip(*pts));rng=np.random.default_rng(action_seed)
            actions=[];states=[];first=None;first_index=None;initial=info['road_stock']
            while not env.done:
                mask=env.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
                action=int(rng.choice(len(p),p=p/p.sum()));obs,_,_,_,info=env.step(action);actions.append(action)
                states.append(dict(raw_sha256=raw_digest(env.raw),observation_sha256=observation_digest(obs),seconds=env.raw['time'],trips=info['trips'],stock=info['road_stock'],buildings=len(env.raw['buildings']),builds=info['road_actions']))
                if first is None and info['trips']>0:first=states[-1];first_index=len(states)-1
                if len(actions)>2000:raise RuntimeError('Unexpected nontermination')
            shops=[b for b in env.raw['buildings'] if not b['isHouse']]
            both=len(shops)==2 and all(b['served']>0 for b in shops)
            selected=None
            if ex==SMALL_TIGHT and first is not None and distance>6:
                # A partial sequence with no deliveries: finishing still requires choices.
                target=max(1,first['builds']//2)
                selected=next((i for i,s in enumerate(states) if s['builds']>=target and s['trips']==0 and s['stock']>0),None)
            elif ex==SMALL_OFFSET and both and first is not None and first['buildings']==2 and first['stock']>0:
                selected=first_index
            row=dict(exercise=ex,seed=seed,action_seed=action_seed,score=info['trips'],first_served=first is not None,both_served=both,approach_distance=distance,initial_stock=initial,selected=selected is not None)
            games.append(row)
            if selected is not None:
                starts.append(dict(id=f'{ex}-{seed}-{action_seed}',exercise=ex,seed=seed,actions=actions[:selected+1],**states[selected]))
            print('BANK',ex,seed,action_seed,info['trips'],row['selected'],flush=True)
        return games,starts
    finally:env.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--count',type=int,default=128);p.add_argument('--seed-start',type=int,default=232000000);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    jobs=[(ex,a.seed_start+i,301000+j*1000+i) for ex in (SMALL_TIGHT,SMALL_OFFSET) for j in range(2) for i in range(a.count)]
    config=dict(schema='native-mini-starts-v1',host_sha256=sha256(Path(a.dll)),checkpoint=a.checkpoint,checkpoint_sha256=sha256(Path(a.checkpoint)),seed_start=a.seed_start,count=a.count,selection='Successful long tight single: halfway through own construction before delivery. Successful two-pair game: first delivery before second pair exists. No reference actions or training labels.')
    (a.output/'config.json').write_text(json.dumps(config,indent=2))
    with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
        results=[f.result() for f in [pool.submit(collect,a.dll,a.checkpoint,jobs[k::8]) for k in range(8)]]
    games=[g for gs,_ in results for g in gs];starts=[s for _,ss in results for s in ss]
    (a.output/'games.jsonl').write_text(''.join(json.dumps(g)+'\n' for g in games))
    (a.output/'starts.json').write_text(json.dumps(dict(config,starts=starts),indent=2))
    assert sha256(Path(a.dll))==config['host_sha256'] and sha256(Path(a.checkpoint))==config['checkpoint_sha256']
    print('COMPLETE',len(games),'games;',len(starts),'starts',flush=True)

if __name__=='__main__':main()
