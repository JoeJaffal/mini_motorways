"""Bounded PPO continuation of the same city policy on native practice or a mix."""
import argparse
from functools import partial
import json
import shutil
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


def publish(path, value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)


def worker(dll, stage, rank, count, seed, collapse, horizon):
    return Monitor(CityCurriculumEnv(dll,stage,rank,count,seed,collapse_forced_wait=collapse,city_horizon=horizon), info_keywords=(*EPISODE_FIELDS,'exercise'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','parent','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--stage',choices=STAGES,required=True)
    parser.add_argument('--collapse-forced-wait',action='store_true')
    parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--rollouts',type=int,default=16)
    parser.add_argument('--seed-start',type=int,required=True)
    parser.add_argument('--learning-rate',type=float,default=1e-5)
    parser.add_argument('--rollout-steps',type=int,default=128)
    parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--gae-lambda',type=float,default=None)
    parser.add_argument('--horizon',type=int,default=600)
    parser.add_argument('--record-dir',type=Path,default=None)
    parser.add_argument('--save-every-rollouts',type=int,default=0)
    args=parser.parse_args()
    if min(args.workers,args.rollouts,args.rollout_steps,args.batch_size)<1 or not np.isfinite(args.learning_rate) or args.learning_rate<=0:
        parser.error('Positive counts and finite positive learning rate required')
    if args.gae_lambda is not None and not 0<=args.gae_lambda<=1:
        parser.error('GAE lambda must be between zero and one')
    if args.workers*args.rollout_steps % args.batch_size:
        parser.error('Batch size must divide the rollout size')
    if not 0<args.horizon<=3600:
        parser.error('Horizon must be between one and 3600 seconds')
    if args.save_every_rollouts<0:
        parser.error('Checkpoint interval cannot be negative')
    torch.set_num_threads(1)
    args.output.mkdir(parents=True,exist_ok=False)
    if args.record_dir is not None:
        args.record_dir.mkdir(parents=True,exist_ok=False)
    def archive_progress():
        if args.record_dir is not None:
            for name in ('config.json','checkpoints.json','complete.json','episodes.jsonl','progress.csv'):
                source=args.output/name
                if source.exists():shutil.copy2(source,args.record_dir/name)
    config=vars(args).copy()
    config={k:str(v) if isinstance(v,Path) else v for k,v in config.items()}
    config.update(parent_sha256=sha256(args.parent),host_sha256=sha256(args.dll),decision_budget=args.workers*args.rollout_steps*args.rollouts)
    publish(args.output/'config.json',config)
    archive_progress()
    env=SubprocVecEnv([partial(worker,args.dll,args.stage,i,args.workers,args.seed_start,args.collapse_forced_wait,args.horizon) for i in range(args.workers)],start_method='forkserver')
    try:
        overrides={} if args.gae_lambda is None else dict(gae_lambda=args.gae_lambda)
        model=MaskablePPO.load(args.parent,env=env,device='cuda',learning_rate=args.learning_rate,n_steps=args.rollout_steps,batch_size=args.batch_size,**overrides)
        start=model.num_timesteps
        model.set_logger(configure(str(args.output),['csv']))
        then=monotonic();saves=[]
        with (args.output/'episodes.jsonl').open('x') as stream:
            callback=RecordEpisodes(stream)
            for i in range(args.rollouts):
                model.learn(total_timesteps=args.workers*args.rollout_steps,reset_num_timesteps=False,callback=callback)
                metrics=model.logger.name_to_value
                if not all(np.isfinite(metrics[k]) for k in ('train/loss','train/approx_kl','train/value_loss')):
                    raise RuntimeError('Nonfinite PPO loss')
                model.logger.dump(step=model.num_timesteps)
                scores=[episode['r'] for episode in model.ep_info_buffer]
                mean=float(np.mean(scores)) if scores else float('nan')
                print(f'PPO | {args.stage} | {model.num_timesteps-start} decisions | {callback.completed} episodes | recent mean score {mean:.2f} | last scores {scores[-8:]}',flush=True)
                if i+1 in {max(1,args.rollouts//2),args.rollouts} or (args.save_every_rollouts and (i+1)%args.save_every_rollouts==0):
                    name='final' if i+1==args.rollouts else 'midpoint' if i+1==max(1,args.rollouts//2) else f'checkpoint-{model.num_timesteps-start:09d}'
                    path=args.output/(name+'.zip')
                    pending=args.output/(name+'.pending.zip');model.save(pending);pending.replace(path)
                    saves.append(dict(path=str(path),sha256=sha256(path),added_decisions=model.num_timesteps-start,episodes=callback.completed,seconds=monotonic()-then))
                    publish(args.output/'checkpoints.json',saves)
                    archive_progress()
        assert model.num_timesteps-start == config['decision_budget']
        assert sha256(args.parent)==config['parent_sha256'] and sha256(args.dll)==config['host_sha256']
        publish(args.output/'complete.json',dict(checkpoints=saves,seconds=monotonic()-then))
        archive_progress()
    finally:env.close()

if __name__=='__main__':main()
