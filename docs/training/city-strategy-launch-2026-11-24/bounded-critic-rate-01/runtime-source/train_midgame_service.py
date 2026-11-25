"""Train native-score PPO to serve a new destination in an established network."""

import argparse
from functools import partial
import json
from pathlib import Path
from time import perf_counter

import gymnasium as gym
import numpy as np
from stable_baselines3.common.logger import configure
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

from city_road_pilot import CityRoadEnv, edge_action
from export_city_replays import action_endpoints
from midgame_timing_policy import MidgameTimingFeatures, MidgameTimingPolicy
from prepare_city_policy import sha256
from run_city_growth_pilot import CITY_CRITIC, load_initial
from train_city_score_pilot import EPISODE_FIELDS, RecordEpisodes

OPEN, DELAY = 'midgame-open', 'midgame-delay'
NETWORK_LESSONS = ('midgame-network-join', 'midgame-network-route', 'midgame-network-delay')
TRAIN_FIRST, TRAIN_END = 94_000_000, 94_400_000
SERVICE_SECONDS = 60
SERVICE_FIELDS = ('exercise', 'stock_initial', 'new_deliveries', 'existing_deliveries',
                  'first_new_delivery', 'paid_at_first_new_delivery', 'stock_at_gate')


class MidgameServiceEnv(CityRoadEnv):
    def __init__(self, dll, worker=0, workers=1, *, validation=False):
        super().__init__(dll, horizon=SERVICE_SECONDS, observation_horizon=600)
        self.worker = worker
        self.workers = workers
        self.cursor = TRAIN_FIRST + worker
        self.split = 'validation' if validation else 'train'
        self.with_delay = False
        self.timing_lesson = False

    def enable_delay(self):
        self.with_delay = True

    def enable_timing_lesson(self):
        self.timing_lesson = True
        self.cursor += 200_000

    def reset(self, *, seed=None, options=None):
        gym.Env.reset(self, seed=seed)
        if options is None:
            if self.cursor >= TRAIN_END:
                raise RuntimeError('Exhausted training-only scenario seeds')
            self.scenario_seed = self.cursor
            self.cursor += self.workers
            delayed = self.timing_lesson or (self.with_delay and self.worker % 2)
            self.exercise = DELAY if delayed else OPEN
        else:
            self.scenario_seed, self.exercise = options['scenario_seed'], options['exercise']
        result = self.host.call(command='reset', version='OriginalReference', practice=True,
                                practiceStage='curriculum-'+self.exercise, practiceSplit=self.split,
                                seed=self.scenario_seed)
        self.raw = result['observation']
        targets = [row for row in self.raw['buildings'] if not row['isHouse']]
        if (not result['accepted'] or result['terminated'] or len(targets)!=2
                or targets[0]['served']<1 or targets[1]['served']!=0):
            raise RuntimeError('Expected a working network and an unserved new destination')
        self.start_time = self.raw['time']
        self.horizon = self.start_time + SERVICE_SECONDS
        self.start_score = self.raw['tripsCompleted']
        self.start_existing = targets[0]['served']
        self.stock_initial = self.raw['inventory'][0]
        self.blocked_at_start = self.raw['terrain'].count(2)
        self.first_new = self.paid_at_first_new = self.stock_at_gate = None
        self.weekly_awards = self.road_actions = self.wait_actions = 0
        self.done = False
        self.cached_mask = None
        self.encoder.reset()
        return self.observation(), self.info()

    def info(self):
        row = super().info()
        existing, new = [b for b in self.raw['buildings'] if not b['isHouse']]
        row.update(seconds=row['seconds']-self.start_time, trips=row['trips']-self.start_score,
                   exercise=self.exercise, stock_initial=self.stock_initial,
                   new_deliveries=new['served'], existing_deliveries=existing['served']-self.start_existing,
                   first_new_delivery=self.first_new, paid_at_first_new_delivery=self.paid_at_first_new,
                   stock_at_gate=self.stock_at_gate)
        return row

    def action_masks(self):
        if self.done:
            return np.zeros(self.action_space.n, dtype=bool)
        if self.cached_mask is None:
            native = self.host.call(command='curriculumMask')
            self.cached_mask = np.array([True, *native['connections']], dtype=bool)
        return self.cached_mask

    def step(self, action):
        if not self.action_space.contains(action) or not self.action_masks()[action]:
            raise ValueError(f'Action unavailable in the native exercise: {action}')
        action = int(action)
        before = self.raw
        if action:
            (x,y),(tx,ty) = action_endpoints(action)
            result = self.host.call(command='draw', x=x, y=y, toX=tx, toY=ty)
            self.road_actions += 1
        else:
            result = self.host.call(command='wait', horizonSeconds=self.horizon)
            self.wait_actions += 1
        self.raw = result['observation']
        self.cached_mask = None
        if action:
            cell, direction = divmod(action-1, 4)
            if self.raw['time'] != before['time'] or not self.raw['connections'][cell] & (1<<direction):
                raise RuntimeError('Draw did not create the exact paused connection')
        reward = result['tripsDelta']
        if not result['accepted'] or result['truncated'] or reward != self.raw['tripsCompleted']-before['tripsCompleted']:
            raise RuntimeError('Invalid native score transition')
        row = self.info()
        if self.first_new is None and row['new_deliveries']:
            self.first_new = row['seconds']
            self.paid_at_first_new = self.stock_initial-row['road_stock']
        if (self.exercise in (DELAY, NETWORK_LESSONS[-1]) and self.stock_at_gate is None
                and self.raw['terrain'].count(2)<self.blocked_at_start):
            self.stock_at_gate = row['road_stock']
        self.done = bool(result['terminated'] or self.raw['time']+0.05 > self.horizon+1e-9)
        return self.observation(), float(reward), self.done, False, self.info()


def make_env(dll, rank, workers):
    return Monitor(MidgameServiceEnv(dll, rank, workers),
                   info_keywords=(*EPISODE_FIELDS, *SERVICE_FIELDS))


def verify_fixtures(dll):
    verification = []
    env = MidgameServiceEnv(dll, validation=True)
    try:
        for index, exercise in enumerate((OPEN,DELAY)):
            for seed in range(94_800_000+index*100,94_800_008+index*100):
                obs, _ = env.reset(options=dict(scenario_seed=seed,exercise=exercise))
                if not env.observation_space.contains(obs):
                    raise RuntimeError('Unexpected fixture input')
                reference = env.host.call(command='curriculumReference')['edits']
                actions = [edge_action((e['x'],e['y']),(e['toX'],e['toY'])) for e in reference]
                if all(env.action_masks()[a] for a in actions) != (exercise==OPEN):
                    raise RuntimeError('Unexpected delayed gate')
                for action in actions:
                    while not env.action_masks()[action] and not env.done:
                        env.step(0)
                    env.step(action)
                while not env.done:
                    env.step(0)
                info = env.info()
                if not info['new_deliveries'] or not info['existing_deliveries']:
                    raise RuntimeError(f'Witness failed: {info}')
                verification.append(info)
        return verification
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll','parent','output'):
        parser.add_argument(f'--{name}',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=32)
    parser.add_argument('--rollouts-per-stage',type=int,default=8)
    parser.add_argument('--timing',action='store_true',help='Isolate the visible-blocker Wait correction')
    args = parser.parse_args()
    if min(args.workers,args.rollouts_per_stage)<1 or args.workers%2 or not torch.cuda.is_available():
        parser.error('Use CUDA with an even worker count and a positive rollout budget')
    if not args.dll.is_file():
        parser.error('Supply a built headless simulator DLL')
    args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    witnesses=verify_fixtures(args.dll)
    (args.output/'fixture-verification.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    print(f'PREFLIGHT | {len(witnesses)} scoring fixtures that retained existing service',flush=True)
    parent_hash=sha256(args.parent)
    settings=dict(device='cuda',seed=761051,n_steps=128,batch_size=64,n_epochs=4,
                  learning_rate=1e-4,gamma=1,gae_lambda=.97,ent_coef=.01,target_kl=.03)
    stage_size=args.workers*settings['n_steps']*args.rollouts_per_stage
    stages=('timing',) if args.timing else ('immediate','mixed-delay')
    config=dict(parent=str(args.parent),parent_sha256=parent_hash,host=str(args.dll),host_sha256=sha256(args.dll),
                training_seed_range=[TRAIN_FIRST+(200_000 if args.timing else 0),TRAIN_END],service_horizon_seconds=SERVICE_SECONDS,
                workers=args.workers, added_decisions=len(stages)*stage_size,settings=settings,timing=args.timing,
                critic_sha256=sha256(CITY_CRITIC))
    (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    env=SubprocVecEnv([partial(make_env,args.dll,i,args.workers) for i in range(args.workers)],
                     start_method='forkserver')
    try:
        transfer = {'policy_class':MidgameTimingPolicy,'features_class':MidgameTimingFeatures} if args.timing else {}
        model=load_initial(args.parent,env,settings,critic=CITY_CRITIC,**transfer)
        if args.timing:
            env.env_method('enable_timing_lesson')
            model.save(args.output/'timing-initial.zip')
        original=model.num_timesteps
        model.set_logger(configure(str(args.output),['stdout','csv']))
        saves=[]
        start=perf_counter()
        with (args.output/'training-episodes.jsonl').open('x') as file:
            callback=RecordEpisodes(file)
            for stage in stages:
                if stage=='mixed-delay':
                    env.env_method('enable_delay')
                    model.set_env(env,force_reset=True)
                model.learn(total_timesteps=stage_size,reset_num_timesteps=False,callback=callback)
                model.logger.dump(step=model.num_timesteps)
                path=args.output/f'{stage}.zip'
                model.save(path,exclude=['_last_obs','_last_episode_starts','ep_info_buffer','ep_success_buffer'])
                saves.append(dict(path=path.name,sha256=sha256(path),added_decisions=model.num_timesteps-original,
                                  episodes=callback.completed,elapsed_seconds=perf_counter()-start))
                print(f'SAVED | {path} | {model.num_timesteps-original} added decisions',flush=True)
        if model.num_timesteps-original!=config['added_decisions'] or sha256(args.parent)!=parent_hash:
            raise RuntimeError('Training budget or source checkpoint changed')
        (args.output/'status.json').write_text(json.dumps(dict(result='COMPLETE',saved=saves,
            elapsed_seconds=perf_counter()-start),indent=2)+'\n')
    finally:
        env.close()


if __name__=='__main__':
    main()
