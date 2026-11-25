"""Check the preserved stock-only policy on an independent seed cohort."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
import argparse
import json

import torch
from sb3_contrib import MaskablePPO

import spare_road_ppo
from bend_ppo import digest
from evaluate_edit_limit import run_layout
from hierarchy_rollout import policy_fingerprint
from spare_road_ppo import SpareRoadEnvironment


def evaluate(args):
    data = json.loads(Path(args.checkpoint).with_name('config.json').read_text())
    if data['native_sha256'] != digest(args.dll) or data['source_sha256'] != digest(spare_road_ppo.__file__):
        raise ValueError('Checkpoint host or source changed')
    torch.set_num_threads(2)
    model = MaskablePPO.load(args.checkpoint, device='cpu')
    policy = model.policy
    before = policy_fingerprint(policy)
    envs = []
    arms = {}
    mutex = Lock()
    try:
        for _ in range(10):
            envs.append(SpareRoadEnvironment(args.dll))
        with ThreadPoolExecutor(max_workers=len(envs)) as pool:
            for mode in ('greedy', 'sampled'):
                rows = []
                for start in range(36200, 36300, len(envs)):
                    rows.extend(pool.map(lambda item: run_layout(
                        item[0], policy, mutex, item[1], 1, mode=='greedy'),
                        zip(envs, range(start, start+len(envs)))))
                arms[mode] = rows
    finally:
        for env in envs:
            env.close()
    if policy_fingerprint(policy) != before:
        raise RuntimeError('Evaluation changed weights')
    if any(sum(s['paid'] for s in row['steps']) > row['stock']
           for rows in arms.values() for row in rows):
        raise RuntimeError('Original paid road stock exceeded')
    return dict(checkpoint_fingerprint=before, stock_violations=0, changed_weights=False,
                native_sha256=digest(args.dll), source_sha256=digest(__file__), arms=arms)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with Path(args.output).open('x') as out:
        json.dump(evaluate(args), out, indent=2)
        out.write('\n')
