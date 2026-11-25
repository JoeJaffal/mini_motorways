"""Read a frozen actor on native low and high snapshots across the surge."""

import argparse
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from bend_ppo import digest, write
from hierarchy_rollout import policy_fingerprint
from traffic_practice import TrafficEnvironment


def audit(args, policy):
    env = TrafficEnvironment(args.dll, warm_seconds=0, horizon=140, wait_ticks=100, use_roots=True)
    result = {}
    try:
        for time in args.times:
            env.warm_seconds = time
            rows = []
            for seed in range(args.start, args.start+args.count):
                states = []
                for stage in args.stages:
                    obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
                    mask = env.action_masks()
                    refs = env.env.controls()
                    with torch.inference_mode():
                        probabilities = policy.get_distribution(policy.obs_to_tensor(obs)[0],
                                                                action_masks=mask).distribution.probs[0]
                    states.append((obs, mask, {'wait': float(probabilities[0]),
                        'feeder': float(probabilities[refs['feeder']]),
                        'bypass': float(probabilities[refs['separate-exit']]),
                        'cars': float(obs['grid'][19].sum()*4), 'pins': float(obs['shops'][:, 2].sum())}))
                (low, lm, lp), (high, hm, hp) = states
                same = np.array_equal(lm, hm) and all(np.array_equal(low[k], high[k]) for k in low)
                if time <= 15 and not same:
                    raise RuntimeError('The model inputs differ before the earliest surge')
                rows.append(dict(seed=seed, equal_inputs=same, light=lp, heavy=hp))
            result[str(time)] = rows
    finally:
        env.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stages', nargs=2, required=True, metavar=('LIGHT', 'HEAVY'))
    parser.add_argument('--start', type=int, default=95200)
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--times', type=int, nargs='+', default=(0, 15, 25, 35, 45))
    args = parser.parse_args()
    if args.output.exists() or args.count < 1:
        parser.error('Choose a new evidence file and a positive count')
    torch.set_num_threads(2)
    policy = MaskablePPO.load(args.checkpoint, device='cpu').policy
    policy.set_training_mode(False)
    before = policy_fingerprint(policy)
    rows = audit(args, policy)
    if policy_fingerprint(policy) != before:
        raise RuntimeError('The frozen probe changed weights')
    write(args.output, dict(stages=args.stages, native_sha256=digest(args.dll),
                            checkpoint_sha256=digest(args.checkpoint), fingerprint=before, snapshots=rows))


if __name__ == '__main__':
    main()
