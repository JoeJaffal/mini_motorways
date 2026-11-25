"""Bounded PPO practice for completing a service route on limited stock."""

import argparse
from functools import partial
import json
from pathlib import Path
from time import perf_counter

import gymnasium as gym
import numpy as np
from sb3_contrib import MaskablePPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

from city_road_pilot import CityRoadEnv, edge_action
from export_city_replays import action_endpoints
from prepare_city_policy import sha256
from train_city_score_pilot import EPISODE_FIELDS, RecordEpisodes

EXERCISES = ('route-short', 'route-long', 'route-delay')
PARTIAL_EXERCISES = ('route-gap-one', 'route-gap-two', 'route-gate-two', 'route-gap-three')
TRAIN_START = 84_000_000
VALIDATION_START = 84_500_000
HORIZON = 55


class LimitedRouteEnv(CityRoadEnv):
    def __init__(self, dll, worker=0, workers=1, *, validation=False):
        super().__init__(dll, horizon=HORIZON, observation_horizon=600)
        self.worker = worker
        self.workers = workers
        self.cursor = (VALIDATION_START if validation else TRAIN_START) + worker
        self.split = 'validation' if validation else 'train'
        self.with_delay = False
        self.mask = None

    def enable_delayed(self):
        self.with_delay = True

    def reset(self, *, seed=None, options=None):
        gym.Env.reset(self, seed=seed)
        if options is None:
            self.scenario_seed = self.cursor
            if self.cursor >= VALIDATION_START:
                raise RuntimeError('Training seed range exhausted')
            self.cursor += self.workers
            self.exercise = EXERCISES[self.worker % 2]
            if self.with_delay and self.worker % 4 == 0:
                self.exercise = 'route-delay'
        else:
            self.scenario_seed = options['scenario_seed']
            self.exercise = options['exercise']
            if self.exercise not in (*EXERCISES, *PARTIAL_EXERCISES):
                raise ValueError('Unknown limited route exercise')
        response = self.host.call(
            command='reset', version='OriginalReference', practice=True,
            practiceStage='curriculum-' + self.exercise, practiceSplit=self.split, seed=self.scenario_seed,
            includeConnectivity=False,
        )
        self.raw = response['observation']
        self.encoder.reset()
        self.done = False
        self.mask = None
        self.weekly_awards = self.road_actions = self.wait_actions = 0
        self.initial_stock = self.raw['inventory'][0]
        if not response['accepted'] or self.raw['time'] or len(self.raw['buildings']) != 2:
            raise RuntimeError('Invalid limited route fixture reset')
        return self.observation(), self.info()

    def info(self):
        return dict(**super().info(), exercise=self.exercise, spent=self.initial_stock-self.raw['inventory'][0])

    def action_masks(self):
        if self.done:
            return np.zeros(self.action_space.n, dtype=bool)
        if self.mask is None:
            result = self.host.call(command='curriculumMask')
            self.mask = np.asarray([True, *result['connections']], dtype=bool)
        return self.mask

    def step(self, action):
        if not self.action_space.contains(action) or not self.action_masks()[action]:
            raise RuntimeError(f'Action outside the native limited route mask: {action}')
        action = int(action)
        before = self.raw
        if action:
            (x,y),(tx,ty) = action_endpoints(action)
            result = self.host.call(command='draw', x=x, y=y, toX=tx, toY=ty)
            self.road_actions += 1
        else:
            result = self.host.call(command='wait', horizonSeconds=HORIZON)
            self.wait_actions += 1
        self.raw = result['observation']
        self.mask = None
        if action:
            cell, direction = divmod(action - 1, 4)
            if not self.raw['connections'][cell] & (1 << direction):
                raise RuntimeError('Native action did not create the selected connection')
        reward = result['tripsDelta']
        if (not result['accepted'] or result['truncated']
                or reward != self.raw['tripsCompleted']-before['tripsCompleted']
                or action and self.raw['time'] != before['time']):
            raise RuntimeError('Invalid native exercise transition')
        terminal = bool(result['terminated'] or self.raw['tripsCompleted'] or self.raw['time'] >= HORIZON)
        self.done = terminal
        return self.observation(), float(reward), terminal, False, self.info()


def make_env(dll, worker, workers):
    return Monitor(LimitedRouteEnv(dll, worker, workers), info_keywords=(*EPISODE_FIELDS, 'exercise', 'spent'))


def verify_fixtures(dll):
    """Native scoring witnesses are reserved for fixture checks."""
    report = []
    env = LimitedRouteEnv(dll, validation=True)
    try:
        for index, exercise in enumerate(EXERCISES):
            for seed in range(VALIDATION_START+900+index*100, VALIDATION_START+912+index*100):
                obs, _ = env.reset(options=dict(scenario_seed=seed, exercise=exercise))
                if not env.observation_space.contains(obs):
                    raise RuntimeError('Unexpected exercise observation')
                reference = env.host.call(command='curriculumReference')['edits']
                actions = [edge_action((edge['x'],edge['y']),(edge['toX'],edge['toY'])) for edge in reference]
                mask = env.action_masks()
                blocked = [action for action in actions if not mask[action]]
                if (exercise == 'route-delay') != bool(blocked):
                    raise RuntimeError('Expected a genuine gate only on delayed layouts')
                if exercise == 'route-delay':
                    while not all(env.action_masks()[action] for action in blocked) and not env.done:
                        env.step(0)
                opened = env.raw['time']
                for action in actions:
                    if env.action_masks()[action]:
                        env.step(action)
                    else:
                        raise RuntimeError('A paid reference edge remained blocked')
                while not env.done:
                    env.step(0)
                if env.raw['tripsCompleted'] < 1:
                    raise RuntimeError(f'Fixture {exercise} {seed} did not deliver')
                report.append(dict(seed=seed, opened=opened, legal_at_start=int(mask[1:].sum()), **{
                    k:v for k,v in env.info().items() if k!='seed'}))
        return report
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--rollouts-per-stage', type=int, default=10)
    args = parser.parse_args()
    if args.workers < 4 or args.workers % 4 or args.rollouts_per_stage < 1:
        parser.error('Choose a positive rollout count and a worker count divisible by four')
    if not torch.cuda.is_available():
        parser.error('CUDA is required for this pilot')
    torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=False)
    witnesses = verify_fixtures(args.dll)
    (args.output/'fixture-verification.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    print(f'PREFLIGHT | {len(witnesses)} native scoring witnesses', flush=True)
    parent_hash = sha256(args.parent)
    env = SubprocVecEnv([partial(make_env,args.dll,i,args.workers) for i in range(args.workers)],
                        start_method='forkserver')
    try:
        model = MaskablePPO.load(args.parent,env=env,device='cuda',force_reset=True,seed=247631,learning_rate=1e-4)
        parent_steps, parent_epochs = model.num_timesteps, model._n_updates
        if not parent_steps or not model.policy.optimizer.state:
            raise RuntimeError('Use the trained city checkpoint and its Adam state')
        stage_size = args.workers*model.n_steps*args.rollouts_per_stage
        config = dict(parent=str(args.parent), parent_sha256=parent_hash, host=str(args.dll),
                      host_sha256=sha256(args.dll), workers=args.workers, seed=247631, horizon=HORIZON,
                      observation_horizon=600, learning_rate=1e-4, batch_size=model.batch_size, epochs=model.n_epochs,
                      gamma=model.gamma, gae_lambda=model.gae_lambda, entropy=model.ent_coef, target_kl=model.target_kl,
                      rollout_steps=model.n_steps, rollouts_per_stage=args.rollouts_per_stage,
                      added_decisions=2*stage_size, training_seed_range=[TRAIN_START,VALIDATION_START],
                      exercise_seed_split='train', validation_seed_split='validation')
        (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        model.set_logger(configure(str(args.output), ['stdout','csv']))
        start = perf_counter()
        saves = []
        with (args.output/'training-episodes.jsonl').open('x') as file:
            callback = RecordEpisodes(file)
            for stage in ('openings','mixed-delay'):
                if stage == 'mixed-delay':
                    env.env_method('enable_delayed')
                    model.set_env(env, force_reset=True)
                model.learn(total_timesteps=stage_size,reset_num_timesteps=False,callback=callback)
                model.logger.dump(step=model.num_timesteps)
                added = model.num_timesteps-parent_steps
                save = args.output/f'{stage}.zip'
                model.save(save,exclude=['_last_obs','_last_episode_starts','ep_info_buffer','ep_success_buffer'])
                saves.append(dict(stage=stage, added_decisions=added, path=save.name, sha256=sha256(save),
                                  games=callback.completed, elapsed_seconds=perf_counter()-start))
                print(f'SAVED | {save} | {added} added decisions | {callback.completed} games',flush=True)
        if model.num_timesteps!=parent_steps+2*stage_size or sha256(args.parent)!=parent_hash:
            raise RuntimeError('Pilot budget or parent checkpoint changed')
        (args.output/'status.json').write_text(json.dumps(dict(result='COMPLETE',saved=saves,
            added_epochs=model._n_updates-parent_epochs,elapsed_seconds=perf_counter()-start),indent=2)+'\n')
    finally:
        env.close()


if __name__=='__main__':
    main()
