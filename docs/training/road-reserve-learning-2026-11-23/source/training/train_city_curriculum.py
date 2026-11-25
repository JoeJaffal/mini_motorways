"""Bounded PPO continuation of the same city policy on native practice or a mix."""
import argparse
from functools import partial
import json
from pathlib import Path
from time import monotonic
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.logger import configure
from city_curriculum import CityCurriculumEnv, STAGES
from prepare_city_policy import sha256
from train_city_score_pilot import EPISODE_FIELDS, RecordEpisodes


def worker(dll, stage, rank, count, seed, collapse):
    return Monitor(CityCurriculumEnv(dll,stage,rank,count,seed,collapse_forced_wait=collapse), info_keywords=(*EPISODE_FIELDS,'exercise'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','parent','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--stage',choices=STAGES,required=True)
    parser.add_argument('--collapse-forced-wait',action='store_true')
    parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--rollouts',type=int,default=16)
    parser.add_argument('--seed-start',type=int,required=True)
    parser.add_argument('--learning-rate',type=float,default=1e-5)
    args=parser.parse_args()
    if min(args.workers,args.rollouts)<1 or not np.isfinite(args.learning_rate) or args.learning_rate<=0:
        parser.error('Positive counts and finite positive learning rate required')
    torch.set_num_threads(1)
    args.output.mkdir(parents=True,exist_ok=False)
    config=vars(args).copy()
    config={k:str(v) if isinstance(v,Path) else v for k,v in config.items()}
    config.update(parent_sha256=sha256(args.parent),host_sha256=sha256(args.dll),decision_budget=args.workers*128*args.rollouts)
    (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    env=SubprocVecEnv([partial(worker,args.dll,args.stage,i,args.workers,args.seed_start,args.collapse_forced_wait) for i in range(args.workers)],start_method='forkserver')
    try:
        model=MaskablePPO.load(args.parent,env=env,device='cuda',learning_rate=args.learning_rate,n_steps=128)
        start=model.num_timesteps
        model.set_logger(configure(str(args.output),['csv']))
        then=monotonic();saves=[]
        with (args.output/'episodes.jsonl').open('x') as stream:
            callback=RecordEpisodes(stream)
            for i in range(args.rollouts):
                model.learn(total_timesteps=args.workers*128,reset_num_timesteps=False,callback=callback)
                metrics=model.logger.name_to_value
                if not all(np.isfinite(metrics[k]) for k in ('train/loss','train/approx_kl','train/value_loss')):
                    raise RuntimeError('Nonfinite PPO loss')
                model.logger.dump(step=model.num_timesteps)
                print(f'PPO | {args.stage} | {model.num_timesteps-start} decisions | {callback.completed} episodes',flush=True)
                if i+1 in {max(1,args.rollouts//2),args.rollouts}:
                    name='final' if i+1==args.rollouts else 'midpoint'
                    path=args.output/(name+'.zip');model.save(path)
                    saves.append(dict(path=str(path),sha256=sha256(path),added_decisions=model.num_timesteps-start,episodes=callback.completed,seconds=monotonic()-then))
                    (args.output/'checkpoints.json').write_text(json.dumps(saves,indent=2)+'\n')
        assert model.num_timesteps-start == config['decision_budget']
        assert sha256(args.parent)==config['parent_sha256'] and sha256(args.dll)==config['host_sha256']
        (args.output/'complete.json').write_text(json.dumps(dict(checkpoints=saves,seconds=monotonic()-then),indent=2)+'\n')
    finally:env.close()

if __name__=='__main__':main()
