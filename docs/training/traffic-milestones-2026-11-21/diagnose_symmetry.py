"""Frozen reflection control for an orientation-sensitive junction policy."""

import argparse
from pathlib import Path

import numpy as np
import torch

from connection_practice import ARENA_SIZE
from construction_practice import EDGE_END, edge_id, endpoints, inside
from environment import DIRS
from traffic_ppo import evaluate
from traffic_practice import TrafficEnvironment

DIRECTIONS = [8 + DIRS.index((-x, y)) for x, y in DIRS]
ACTIONS = np.arange(EDGE_END)


def reflect_point(point):
    x, y = point
    return ARENA_SIZE - 1 - x, y


for index in range(1, EDGE_END):
    start, end = endpoints(index)
    if inside(end):
        ACTIONS[index] = edge_id(reflect_point(start), reflect_point(end))
if not np.array_equal(ACTIONS[ACTIONS], np.arange(EDGE_END)):
    raise RuntimeError('Reflecting action coordinates twice must restore each index')


class ShopSideEnvironment:
    def __init__(self, *args, **kwargs):
        self.practice = TrafficEnvironment(*args, **kwargs)
        self.env = self.practice.env

    def actor_view(self, obs):
        if not self.reflect:
            return obs
        grid = obs['grid'][..., ::-1].copy()
        grid[8:16] = grid[DIRECTIONS]
        grid[22] = 2 - grid[22]
        shops = obs['shops'].copy()
        shops[:, 0] = ARENA_SIZE - 1 - shops[:, 0]
        present = dict(obs, grid=grid, shops=shops)
        if 'roots' in obs:
            present['roots'] = obs['roots'][..., ::-1].copy()
        return present

    def reset(self, **kwargs):
        obs, info = self.practice.reset(**kwargs)
        house_columns = np.nonzero(obs['grid'][2:5].any(axis=0))[1]
        self.reflect = obs['shops'][:, 0].mean() < house_columns.mean()
        return self.actor_view(obs), info

    def action_masks(self):
        mask = self.practice.action_masks()
        return mask[ACTIONS] if self.reflect else mask

    def step(self, action):
        world_action = int(ACTIONS[action]) if self.reflect else action
        obs, reward, done, truncated, info = self.practice.step(world_action)
        return self.actor_view(obs), reward, done, truncated, info

    def close(self):
        self.practice.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--stages', nargs='+', required=True)
    parser.add_argument('--offset', type=int, default=2800)
    parser.add_argument('--count', type=int, default=24)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    if args.output.exists() or min(args.count, args.workers) < 1:
        parser.error('Use a new results file and positive dimensions')
    torch.set_num_threads(2)
    args.mode, args.exercise = 'evaluate', 'junction'
    args.horizon, args.wait_ticks, args.warm_seconds = 120, 100, 36
    evaluate(args, args.stages, environment_class=ShopSideEnvironment)


if __name__ == '__main__':
    main()
