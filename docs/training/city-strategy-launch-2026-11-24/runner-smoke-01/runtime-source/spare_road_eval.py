"""Frozen evaluation of a spare-stock PPO checkpoint at temperature one."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

import clear_road_ppo
import spare_road_ppo
from bend_ppo import digest


class FrozenView:
    def __init__(self, policy):
        self.policy = policy
        self.observation_space = policy.observation_space

    def state_dict(self):
        return self.policy.state_dict()

    def obs_to_tensor(self, observation):
        temperature = np.ones((len(observation['grid']), 1), dtype=np.float32)
        return self.policy.obs_to_tensor(dict(observation, temperature=temperature))

    def get_distribution(self, obs, *, action_masks):
        return self.policy.get_distribution(obs, action_masks=action_masks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--eval-workers', type=int, default=10)
    parser.add_argument('--extra-stock', action='store_true')
    args = parser.parse_args()
    if args.eval_workers < 1:
        parser.error('Worker count must be positive')
    output = Path(args.output)
    config = json.loads(Path(args.checkpoint).with_name('config.json').read_text())
    if config['native_sha256'] != digest(args.dll) or config['source_sha256'] != digest(spare_road_ppo.__file__):
        raise ValueError('Checkpoint or evaluator host identity differs')
    output.mkdir(parents=True)
    torch.set_num_threads(2)
    model = MaskablePPO.load(args.checkpoint, device='cpu')
    model.policy = FrozenView(model.policy)
    args.eval_offset = 0
    if args.extra_stock:
        clear_road_ppo.EVAL_SEEDS['clear-spare-two'] = clear_road_ppo.EVAL_SEEDS['clear']
        args.stages = ['clear-spare-two']
    else:
        args.stages = ['clear', 'bend', 'adjacent']
    clear_road_ppo.evaluate(args, model, output)


if __name__ == '__main__':
    main()
