"""Verify the unchanged parameters in head-specific PPO runs."""

import argparse
import json
from pathlib import Path

import torch
from sb3_contrib import MaskablePPO


def compare(run):
    config = json.loads((run / 'config.json').read_text())
    first = MaskablePPO.load(run / 'initial.zip', device='cpu').policy.action_net.state_dict()
    last = MaskablePPO.load(run / 'latest.zip', device='cpu').policy.action_net.state_dict()
    if first.keys() != last.keys():
        raise RuntimeError(f'Actor parameter keys changed for {run.name}')
    unchanged = [key for key in first if torch.equal(first[key], last[key])]
    changed = [key for key in first if key not in unchanged]
    fixed = [key for key in first if
             (config.get('train_wait_only') and key.startswith('edge.')) or
             (config.get('train_roads_only') and key.startswith('wait'))]
    if not set(fixed).issubset(unchanged):
        raise RuntimeError(f'A fixed actor parameter changed for {run.name}')
    if fixed and not changed:
        raise RuntimeError(f'No actor parameters learned in {run.name}')
    return dict(fixed=fixed, changed=changed, same=unchanged)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', type=Path, nargs='+')
    args = parser.parse_args()
    torch.set_num_threads(2)
    print(json.dumps({run.name: compare(run) for run in args.runs}, indent=2))


if __name__ == '__main__':
    main()
