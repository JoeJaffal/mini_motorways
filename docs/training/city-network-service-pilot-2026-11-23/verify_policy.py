"""Confirm masked opening parity and reproduce the earlier city-road decision."""

import argparse
import json
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import CityRoadEnv, edge_action
from prepare_city_policy import masked_probs, sha256
from train_limited_route_ppo import LimitedRouteEnv


def verify_opening(dll, models):
    env = LimitedRouteEnv(dll, validation=True)
    protected = []
    try:
        for index, exercise in enumerate(('route-short', 'route-long', 'route-delay', 'route-gate-two')):
            for seed in range(108_300_000 + index*20, 108_300_008 + index*20):
                obs, _ = env.reset(options={'scenario_seed':seed, 'exercise':exercise})
                reference = env.host.call(command='curriculumReference')['edits']
                actions = [edge_action((e['x'], e['y']), (e['toX'], e['toY'])) for e in reference]
                cursor = 0
                while not env.done and cursor < len(actions):
                    mask = env.action_masks()
                    parent, _ = models[0].policy.obs_to_tensor(obs)
                    with torch.no_grad():
                        coupling = models[0].policy.features_extractor(parent)[0, -1].item()
                    if coupling:
                        reference_probs = masked_probs(models[0], obs, mask)
                        for model in models[1:]:
                            np.testing.assert_array_equal(reference_probs, masked_probs(model, obs, mask))
                        protected.append((exercise, seed, env.raw['time']))
                    action = actions[cursor]
                    if mask[action]:
                        cursor += 1
                    else:
                        action = 0
                    obs, *_ = env.step(action)
        assert len(protected) >= 32
        return dict(layouts=32, protected_states=len(protected), cohorts=sorted({r[0] for r in protected}))
    finally:
        env.close()


def verify_witness(evidence, dll, models, paths):
    record = json.loads((evidence/'same-state-policy-probabilities.json').read_text())
    games = json.loads((evidence/'one-edge-witness.json').read_text())['games']
    witness = next(row for row in games if row['seed']==record['seed'])
    options = record['ignored_connections']
    env = CityRoadEnv(dll)
    try:
        obs, _ = env.reset(options={'scenario_seed':witness['seed']})
        for action in witness['actions'][:options[0]['decision']]:
            obs, _, _, _, info = env.step(action)
        assert info['seconds']==record['seconds'] and info['road_stock']==record['road_stock']
        mask = env.action_masks()
        legal = [row['alternative'] for row in options]
        choice = options[0]['sampled']
        assert mask[choice] and all(mask[action] for action in legal)
        rows = []
        for model, path in zip(models, paths):
            p = masked_probs(model, obs, mask).astype(np.float64)
            p /= p.sum()
            rows.append(dict(model=str(path), joins_probability=float(p[legal].sum()),
                             wait_probability=float(p[0]), comparison_edge_probability=float(p[choice]),
                             best_join_road_rank=1+int((p[1:]>p[legal].max()).sum())))
        return dict(seed=witness['seed'], decision=options[0]['decision'], rows=rows)
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--checkpoints', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    models = [MaskablePPO.load(path, device='cpu') for path in args.checkpoints]
    result = dict(
        sha256={str(path):sha256(path) for path in args.checkpoints}, host_sha256=sha256(args.dll),
        opening=verify_opening(args.dll, models),
        city_witness=verify_witness(args.evidence, args.dll, models, args.checkpoints),
    )
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
