"""Train visible geometry and timing with progressively less route assistance."""

import argparse
from collections import deque
from functools import partial
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import configure
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

from city_route_repair_policy import RouteProgressPolicy, RouteRepairFeatures, RouteRepairPolicy
from environment import DIRS
from prepare_city_policy import sha256
from train_city_score_pilot import EPISODE_FIELDS
from train_limited_route_ppo import LimitedRouteEnv
from visible_observation import WIDTH

STAGES = (
    ('route-gap-one', 'route-gap-two', 'route-gap-one', 'route-gate-two'),
    ('route-short', 'route-long', 'route-gap-two', 'route-gate-two'),
    ('route-short', 'route-long', 'route-delay', 'route-gate-two'),
)
FRONTIER_STAGES = (
    ('route-gap-one', 'route-gap-two', 'route-gap-three', 'gate-already-open'),
    ('route-short', 'route-gap-three', 'gate-already-open', 'route-gate-two'),
    ('route-long', 'route-gap-three', 'route-delay', 'route-gate-two'),
)
SEED_START = 86_000_000
SEED_END = 87_000_000


def gap_potential(raw):
    """Estimate the gap between visible terminal components for training credit."""
    home, = [b for b in raw['buildings'] if b['isHouse']]
    shop, = [b for b in raw['buildings'] if not b['isHouse']]

    def access(building, point):
        dx,dy=DIRS[building['drivewayDirection']]
        return point['x']+dx,point['y']+dy

    def component(start):
        visited = {start}
        pending = deque([start])
        while pending:
            x,y = pending.popleft()
            bits = raw['connections'][y*WIDTH+x]
            for d,(dx,dy) in enumerate(DIRS):
                point = x+dx,y+dy
                if bits & (1<<d) and point not in visited:
                    visited.add(point)
                    pending.append(point)
        return visited

    a = component(access(home,home['cell']))
    b = component(access(shop,shop['entrance']))
    gap = min(max(abs(x-tx),abs(y-ty)) for x,y in a for tx,ty in b)
    deficit = max(0,gap-raw['inventory'][0])
    return -.18*gap - .10*deficit


class RepairPractice(LimitedRouteEnv):
    def __init__(self,dll,worker,workers,seed_start,frontier):
        super().__init__(dll,worker,workers)
        self.cursor=seed_start+worker
        self.level=0
        self.stages=FRONTIER_STAGES if frontier else STAGES
        self.sampler=np.random.default_rng(95261+worker)

    def set_level(self,level):
        self.level=level

    def reset(self,*,seed=None,options=None):
        if self.cursor>=SEED_END:
            raise RuntimeError('Route repair seed range exhausted')
        variant=self.stages[self.level][int(self.sampler.integers(4))]
        self.started_after_gate=variant=='gate-already-open'
        exercise='route-gate-two' if self.started_after_gate else variant
        options=dict(scenario_seed=self.cursor,exercise=exercise)
        self.cursor+=self.workers
        observation,info=super().reset(seed=seed,options=options)
        if self.started_after_gate:
            blocked=self.raw['terrain'].count(2)
            while self.raw['terrain'].count(2)==blocked and not self.done:
                observation,_,_,_,info=super().step(0)
            if self.done:
                raise RuntimeError('Delayed route ended before its gate could open')
            self.wait_actions=0
        self.potential=gap_potential(self.raw)
        self.initial_potential=self.potential
        return observation,info

    def step(self,action):
        obs,reward,done,truncated,info=super().step(action)
        potential=0. if done else gap_potential(self.raw)
        shaped=reward+potential-self.potential
        self.potential=potential
        if done:
            info['reward_constant']=-self.initial_potential
            info['started_after_gate']=self.started_after_gate
        return obs,shaped,done,truncated,info


def make_env(dll,rank,workers,seed_start,frontier):
    return Monitor(RepairPractice(dll,rank,workers,seed_start,frontier),
                   info_keywords=(*EPISODE_FIELDS,'exercise','spent','reward_constant','started_after_gate'))


class TrainingLog(BaseCallback):
    def __init__(self,file):
        super().__init__()
        self.file=file
        self.games=0

    def _on_step(self):
        for info in self.locals['infos']:
            if 'episode' in info:
                row=info['episode']
                if abs(row['r']-row['trips']-row['reward_constant'])>1e-5:
                    raise RuntimeError('Potential reward did not telescope back to native deliveries')
                self.file.write(json.dumps(dict(decisions=self.num_timesteps,**row))+'\n')
                self.games+=1
        return True

    def _on_rollout_end(self):
        self.file.flush()
        self.logger.record('route/games',self.games)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','parent','output'):
        parser.add_argument(f'--{name}',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=32)
    parser.add_argument('--rollouts',type=int,default=8)
    parser.add_argument('--frontier',action='store_true',help='Use visible connected-road features and recalibrated opening exploration')
    parser.add_argument('--progress',action='store_true',help='Couple Wait to evidence in the legal road actions')
    parser.add_argument('--seed-start',type=int,default=SEED_START)
    args=parser.parse_args()
    if not torch.cuda.is_available() or min(args.workers,args.rollouts)<1:
        parser.error('Positive worker and rollout counts and CUDA are required')
    if args.progress and not args.frontier:
        parser.error('Progress requires the connected-road features')
    if not SEED_START<=args.seed_start<SEED_END:
        parser.error('Choose a fresh start within the training seed range')
    torch.set_num_threads(1)
    parent=MaskablePPO.load(args.parent,device='cpu')
    parent_hash=sha256(args.parent)
    args.output.mkdir(parents=True,exist_ok=False)
    env=SubprocVecEnv([partial(make_env,args.dll,i,args.workers,args.seed_start,args.frontier) for i in range(args.workers)],
                     start_method='forkserver')
    try:
        lr, entropy = (.0006,.018) if args.frontier else (.0003,.007)
        model=MaskablePPO(
            RouteProgressPolicy if args.progress else RouteRepairPolicy,env,device='cuda',seed=764921,
            policy_kwargs=dict(features_extractor_class=RouteRepairFeatures,normalize_images=False,
                               features_extractor_kwargs=dict(frontier=args.frontier,progress=args.progress)),
            learning_rate=lr,n_steps=128,batch_size=64,n_epochs=4,gamma=1,gae_lambda=.97,
            ent_coef=entropy,target_kl=.035,
        )
        missing,extra=model.policy.load_state_dict(parent.policy.state_dict(),strict=False)
        new_prefixes=('features_extractor.route_', 'pi_features_extractor.route_', 'vf_features_extractor.route_')
        if extra or not missing or any(not name.startswith(new_prefixes) for name in missing):
            raise RuntimeError(f'Unexpected transfer identities: {missing} {extra}')
        if args.frontier:
            torch.nn.init.zeros_(model.policy.value_net[-1].weight)
            torch.nn.init.zeros_(model.policy.value_net[-1].bias)
        model.set_logger(configure(str(args.output),['stdout','csv']))
        stages=FRONTIER_STAGES if args.frontier else STAGES
        steps=args.workers*model.n_steps*args.rollouts
        config=dict(parent=str(args.parent),parent_sha256=parent_hash,host_sha256=sha256(args.dll),
                    workers=args.workers,rollout_steps=model.n_steps,rollouts=args.rollouts,
                    curriculum=stages,seed=764921,seed_range=[args.seed_start,SEED_END],
                    added_decisions=steps*len(stages),gamma=1,gae_lambda=.97,ent_coef=entropy,
                    learning_rate=lr,frontier=args.frontier,progress=args.progress,batch_size=64,epochs=4,target_kl=.035,
                    potential=dict(distance_weight=.18,stock_deficit_weight=.10,terminal=0),
                    architecture='visible opening-only correction with frozen base actor')
        if args.progress:
            initial=args.output/'initialized.zip'
            model.save(initial,exclude=['_last_obs','_last_episode_starts','ep_info_buffer','ep_success_buffer'])
            config['initial_sha256']=sha256(initial)
        (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        start=perf_counter()
        saved=[]
        with (args.output/'training-episodes.jsonl').open('x') as file:
            callback=TrainingLog(file)
            for level in range(len(stages)):
                env.env_method('set_level',level)
                model.set_env(env,force_reset=True)
                model.learn(total_timesteps=steps,reset_num_timesteps=False,callback=callback)
                model.logger.dump(step=model.num_timesteps)
                checkpoint=args.output/f'route-level-{level+1}.zip'
                model.save(checkpoint,exclude=['_last_obs','_last_episode_starts','ep_info_buffer','ep_success_buffer'])
                saved.append(dict(path=checkpoint.name,sha256=sha256(checkpoint),
                                  decisions=model.num_timesteps,games=callback.games,
                                  elapsed_seconds=perf_counter()-start))
                print(f'SAVED | {checkpoint} | {model.num_timesteps} decisions',flush=True)
        if sha256(args.parent)!=parent_hash or model.num_timesteps!=config['added_decisions']:
            raise RuntimeError('Parent or requested training budget changed')
        (args.output/'status.json').write_text(json.dumps(dict(result='COMPLETE',saved=saved,
            elapsed_seconds=perf_counter()-start),indent=2)+'\n')
    finally:
        env.close()


if __name__=='__main__':
    main()
