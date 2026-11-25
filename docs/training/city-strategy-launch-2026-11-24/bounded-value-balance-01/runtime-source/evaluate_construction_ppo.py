"""Evaluate frozen construction PPO at the original native paid road stock."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

import torch
from sb3_contrib import MaskablePPO

from bend_ppo import digest, write
from hierarchy_rollout import policy_fingerprint
from spare_road_ppo import SpareRoadEnvironment

SEEDS = {'obstacle': 38000, 'clear': 36200, 'adjacent': 30000, 'bend': 32000, 'driveway': 34000}
SEEDS.update({f'pair-{case}': 42000 for case in ('match', 'mismatch', 'homes', 'destinations', 'blue-red')})
SEEDS.update({'obstacle-wide': 50000, 'obstacle-offset': 51000})
SEEDS.update({'pair-triad-left': 54000, 'pair-triad-right': 54000})
SEEDS.update({'pair-triad-left-gap': 56000, 'pair-triad-right-gap': 56000})
SEEDS.update({f'pair-triad-{side}-{kind}': seed for side in ('left', 'right')
              for kind, seed in [('double', 57000), ('triple', 58000)]})


def play(env, policy, lock, stage, seed, greedy, sampled_prefix=0):
    obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
    practice = env.env
    # Permit both free attachments; the native mask still enforces paid stock.
    if stage == 'clear' or stage.startswith('obstacle'):
        practice.edit_limit += 1
    started_connected = practice.connected()
    stock = practice.inventory
    generator = torch.Generator().manual_seed(seed + 100000)
    actions = []
    while True:
        mask = env.action_masks()
        with lock, torch.inference_mode():
            tensor, _ = policy.obs_to_tensor(obs)
            probs = policy.get_distribution(tensor, action_masks=mask).distribution.probs[0]
            legal = mask.nonzero()[0]
            legal_probs = probs[legal]
            take_max = greedy and len(actions) >= sampled_prefix
            action = int(legal[legal_probs.argmax() if take_max else torch.multinomial(
                legal_probs, 1, generator=generator).item()])
        if not mask[action]:
            raise RuntimeError('Policy chose an off-mask action')
        actions.append(action)
        obs, _, done, truncated, info = env.step(action)
        if truncated:
            raise RuntimeError('Unexpected construction truncation')
        if done:
            break
    trips, seconds = practice.deliveries()
    spent = info['road_units_spent']
    if not 0 <= spent <= stock:
        raise RuntimeError('Original native paid stock exceeded')
    return dict(seed=seed, connected=info['connected'], trips=trips, seconds=seconds,
                stock=stock, spent=spent, actions=actions, started_connected=started_connected,
                success=info.get('success', info['connected']),
                buildings=[dict(role='house' if b['isHouse'] else 'destination', color=b['color'])
                           for b in practice.raw['buildings']])


def evaluate(model, env_factory, stages, count, offset, workers, sampled_prefixes=()):
    policy = model.policy
    policy.set_training_mode(False)
    fingerprint = policy_fingerprint(policy)
    envs = []
    lock = Lock()
    results = {}
    modes = ([(f'sample-{n}-then-greedy', True, n) for n in sampled_prefixes]
             if sampled_prefixes else [('greedy', True, 0), ('sampled', False, 0)])
    try:
        for _ in range(workers):
            envs.append(env_factory())
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for stage in stages:
                for mode, greedy, sampled_prefix in modes:
                    first = SEEDS[stage] + offset
                    rows = []
                    for start in range(first, first + count, workers):
                        seeds = range(start, min(start + workers, first + count))
                        rows.extend(pool.map(lambda pair: play(
                            pair[0], policy, lock, stage, pair[1], greedy, sampled_prefix), zip(envs, seeds)))
                    results[f'{stage}/{mode}'] = rows
                    print(f'{stage}/{mode}: {sum(r["success"] for r in rows)}/{len(rows)} passed; '
                          f'{sum(r["trips"] >= 3 for r in rows)} with at least three trips', flush=True)
    finally:
        for env in envs:
            env.close()
    if policy_fingerprint(policy) != fingerprint:
        raise RuntimeError('Frozen evaluation changed model weights')
    return dict(fingerprint=fingerprint, stock_violations=0, results=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stages', nargs='+', choices=tuple(SEEDS), default=['obstacle'])
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if min(args.count, args.workers) < 1 or args.offset < 0 or args.output.exists():
        parser.error('Use positive count/workers, a nonnegative offset and a new output path')
    torch.set_num_threads(2)
    model = MaskablePPO.load(args.checkpoint, device='cpu')
    if 'target_roles' in model.observation_space.spaces:
        from triad_ppo import SelectionEnvironment
        env_class = SelectionEnvironment
    elif 'terrain' in model.observation_space.spaces:
        from terrain_ppo import TerrainDriveEnvironment, TerrainPairEnvironment
        env_class = TerrainPairEnvironment if 'parcel_colors' in model.observation_space.spaces else TerrainDriveEnvironment
    elif 'parcel_colors' in model.observation_space.spaces:
        from pair_ppo import PairEnvironment
        env_class = PairEnvironment
    elif 'driveway' in model.observation_space.spaces:
        from driveway_ppo import DrivewayEnvironment
        env_class = DrivewayEnvironment
    else:
        env_class = SpareRoadEnvironment
    report = evaluate(model, lambda: env_class(args.dll), args.stages, args.count, args.offset, args.workers)
    write(args.output, dict(report, native_sha256=digest(args.dll),
                            checkpoint_sha256=digest(args.checkpoint), evaluator_sha256=digest(__file__)))


if __name__ == '__main__':
    main()
