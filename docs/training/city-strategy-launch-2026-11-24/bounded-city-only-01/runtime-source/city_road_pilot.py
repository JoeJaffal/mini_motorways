"""Ordinary single-edge roads and Wait in the growing native city."""

import argparse
import json
from pathlib import Path

import gymnasium as gym
import numpy as np

from environment import DIRS, Host
from visible_observation import CELLS, HEIGHT, WIDTH, VisibleObservation, observation_space

FORWARD = DIRS[:4]
FIXTURE_SEED = 2004
FIXTURE_ROAD = ((11, 10), (12, 9), (13, 8), (14, 8), (15, 8))


def edge_action(start, end):
    delta = end[0] - start[0], end[1] - start[1]
    if delta not in DIRS:
        raise ValueError('Road endpoints must be neighbors')
    if delta not in FORWARD:
        start, end = end, start
        delta = -delta[0], -delta[1]
    if not all(0 <= x < WIDTH and 0 <= y < HEIGHT for x, y in (start, end)):
        raise ValueError('Road outside the map')
    return 1 + (start[1] * WIDTH + start[0]) * 4 + FORWARD.index(delta)


class CityRoadEnv(gym.Env):
    """Gymnasium interface for the first road-only Maskable PPO pilot."""

    def __init__(self, dll, horizon=600, *, observation_horizon=None, include_connectivity=False):
        if not 0 < horizon <= 3600:
            raise ValueError('Choose a positive horizon up to 3600 seconds')
        self.horizon = horizon
        self.observation_horizon = horizon if observation_horizon is None else observation_horizon
        if not 0 < self.observation_horizon <= 3600:
            raise ValueError('Choose a positive observation horizon up to 3600 seconds')
        self.include_connectivity = include_connectivity
        self.host = Host('dotnet', dll)
        self.encoder = VisibleObservation()
        self.observation_space = observation_space()
        self.action_space = gym.spaces.Discrete(1 + CELLS * 4)
        self.done = True

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.scenario_seed = (options or {}).get('scenario_seed')
        if self.scenario_seed is None:
            self.scenario_seed = int(self.np_random.integers(0, 2**31))
        result = self.host.call(command='reset', version='OriginalReference',
                                scenario='LosAngeles', seed=self.scenario_seed,
                                includeConnectivity=self.include_connectivity)
        self.raw = result['observation']
        self.encoder.reset()
        self.done = False
        self.weekly_awards = 0
        self.road_actions = 0
        self.wait_actions = 0
        return self.observation(), self.info()

    def observation(self):
        return self.encoder.encode(self.raw, horizon=self.observation_horizon)

    def info(self):
        return dict(seed=self.scenario_seed, seconds=self.raw['time'],
                    trips=self.raw['tripsCompleted'], road_stock=self.raw['inventory'][0],
                    buildings=len(self.raw['buildings']), weekly_awards=self.weekly_awards,
                    road_actions=self.road_actions, wait_actions=self.wait_actions)

    def action_masks(self):
        mask = np.zeros(self.action_space.n, dtype=bool)
        if not self.done:
            result = self.host.call(command='cityRoadMask')
            mask[0] = True
            mask[1:] = result['connections']
        return mask

    def step(self, action):
        if self.done or not self.action_space.contains(action):
            raise ValueError('Choose an in-range action in a live game')
        before = self.raw
        if action == 0:
            outcome = self.host.call(command='wait', horizonSeconds=self.horizon)
            self.wait_actions += 1
        else:
            index, direction = divmod(int(action) - 1, 4)
            x, y = index % WIDTH, index // WIDTH
            dx, dy = FORWARD[direction]
            outcome = self.host.call(command='cityRoad', x=x, y=y, toX=x+dx, toY=y+dy)
            self.road_actions += 1
        if not outcome['accepted']:
            raise ValueError(outcome['message'])
        self.raw = outcome['observation']
        reward = outcome['tripsDelta']
        if action and self.raw['time'] != before['time']:
            raise RuntimeError('Construction advanced game time')
        if self.raw['upgradeChoices'] and not outcome['terminated']:
            offers = self.raw['upgradeChoices']
            gains = [offer['roads'] + (offer['amount'] if offer['type'] == 0 else 0)
                     for offer in offers]
            choice = gains.index(max(gains))
            stock = self.raw['inventory'][0]
            award = self.host.call(command='upgrade', choice=choice)
            self.raw = award['observation']
            if not award['accepted'] or self.raw['inventory'][0] != stock + gains[choice]:
                raise RuntimeError('Weekly road stock disagreed with the selected native package')
            if self.raw['upgradeChoices'] or award['tripsDelta'] or self.raw['time'] != outcome['observation']['time']:
                raise RuntimeError('Weekly selection unexpectedly changed gameplay time or score')
            self.weekly_awards += 1
        if reward != self.raw['tripsCompleted'] - before['tripsCompleted']:
            raise RuntimeError('Reward disagreed with native deliveries')
        terminated = bool(outcome['terminated'])
        truncated = not terminated and self.raw['time'] + 0.05 > self.horizon + 1e-9
        self.done = terminated or truncated
        return self.observation(), float(reward), terminated, truncated, self.info()

    def close(self):
        self.host.close()


def verify(dll):
    env = CityRoadEnv(dll)
    try:
        obs, initial = env.reset(options={'scenario_seed': FIXTURE_SEED})
        print(f'RESET | {initial["buildings"]} buildings | {initial["road_stock"]} road units', flush=True)
        if any(env.raw['connections']) or initial['trips'] or not env.observation_space.contains(obs):
            raise RuntimeError('Expected an unbuilt city and a valid initial observation')
        rewards = 0.
        peak_buildings = initial['buildings']
        for start, end in zip(FIXTURE_ROAD, FIXTURE_ROAD[1:]):
            action = edge_action(start, end)
            before = env.info()
            if not env.action_masks()[action]:
                raise RuntimeError(f'Fixture road is unavailable from {start} to {end}')
            obs, reward, terminal, truncated, info = env.step(action)
            if terminal or truncated or info['road_stock'] != before['road_stock'] - 1:
                raise RuntimeError('Fixture draw did not cost exactly one road unit')
            if env.action_masks()[action] or not env.observation_space.contains(obs):
                raise RuntimeError('Built edge remained available or observation was invalid')
            rewards += reward
        print(f'BUILD | {info["road_actions"]} individual connections | {info["road_stock"]} road units', flush=True)
        seen_delivery = False
        first_award_reported = False
        while not env.done:
            obs, reward, terminal, truncated, info = env.step(0)
            rewards += reward
            if not env.observation_space.contains(obs) or rewards != info['trips']:
                raise RuntimeError('Invalid observation or cumulative reward')
            if reward and not seen_delivery:
                seen_delivery = True
                print(f'DELIVERY | first score at {info["seconds"]:.2f}s', flush=True)
            if info['buildings'] > peak_buildings:
                peak_buildings = info['buildings']
                print(f'GROWTH | {peak_buildings} buildings at {info["seconds"]:.2f}s', flush=True)
            if info['weekly_awards'] and not first_award_reported:
                first_award_reported = True
                print(f'WEEKLY | stock increased to {info["road_stock"]} at {info["seconds"]:.2f}s', flush=True)
        if not terminal or not seen_delivery or not info['weekly_awards'] or peak_buildings <= initial['buildings']:
            raise RuntimeError(f'Missing expected delivery, growth, weekly award or native game-over: {info}')
        if env.action_masks().any():
            raise RuntimeError('Terminal state exposed legal actions')
        return dict(result='PASS', native_game_over=terminal, reward=rewards,
                    starting_buildings=initial['buildings'], peak_buildings=peak_buildings, **info)
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.dll), indent=2))


if __name__ == '__main__':
    main()
