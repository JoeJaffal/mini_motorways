"""Paired color swaps with two homes and one destination, using frozen PPO."""

import argparse
from functools import partial
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from bend_ppo import digest, write
from construction_practice import advance, edge_id, tile
from environment import DIRS
from evaluate_construction_ppo import SEEDS, evaluate
from hierarchy_rollout import policy_fingerprint
from pair_ppo import PairEnvironment, PairPractice
from practice_reward import connection_potential

STAGES = ('pair-triad-left', 'pair-triad-right')
GAP_STAGES = ('pair-triad-left-gap', 'pair-triad-right-gap')
MULTIPLE_STAGES = {count: tuple(f'pair-triad-{side}-{kind}' for side in ('left', 'right'))
                   for count, kind in ((2, 'double'), (3, 'triple'))}


class TriadPractice(PairPractice):
    def __init__(self, dll, oracle=False):
        super().__init__(dll)
        self.oracle = oracle

    def reset_pair(self, case, split, seed):
        if not case.startswith('triad-'):
            return super().reset_pair(case, split, seed)
        self.stage, self.case, self.seed = 'pair-' + case, case, seed
        self.edits = 0
        result = self.call(command='reset', version='OriginalReference', practice=True,
                           practiceStage='curriculum-' + case, practiceSplit=split, seed=seed)
        if not result['accepted'] or result['terminated'] or self.raw['time'] != 0:
            raise RuntimeError('Expected a fresh native triad')
        buildings = self.raw['buildings']
        self.shop, = (b for b in buildings if not b['isHouse'])
        self.homes = [b for b in buildings if b['isHouse']]
        if len(self.homes) != 2:
            raise RuntimeError('Expected two real homes')
        self.match, = (b for b in self.homes if b['color'] == self.shop['color'])
        self.house = self.match if self.oracle else self.homes[0]
        self.compatible = True
        self.prepare_arena(buildings)

    def connected(self):
        if not self.stage.startswith('pair-triad-'):
            return super().connected()
        return bool(connection_potential(dict(self.raw, buildings=[self.match, self.shop]), self.area))


class TriadEnvironment(PairEnvironment):
    def __init__(self, dll, oracle=False):
        super().__init__(dll)
        self.env.close()
        self.env = TriadPractice(dll, oracle)


def feasibility(dll, stages, count, empty_stages=STAGES):
    env = TriadEnvironment(dll)
    rows = []
    try:
        for stage in stages:
            for seed in range(SEEDS[stage], SEEDS[stage] + count):
                env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
                world = env.env
                actions = witness(world) if stage in empty_stages else world.reference()
                for action in actions:
                    if not env.action_masks()[action]:
                        raise RuntimeError(f'Illegal test witness for {stage}/{seed}')
                    _, reward, done, _, info = env.step(action)
                trips, _ = world.deliveries()
                if not done or reward != 1 or trips < 3 or info['road_units_spent'] > world.inventory:
                    raise RuntimeError(f'Triad witness failed for {stage}/{seed}')
                rows.append(dict(seed=seed, stage=stage, trips=trips, stock=world.inventory,
                                 spent=info['road_units_spent']))
    finally:
        env.close()
    return rows


def witness(world):
    heading = DIRS[world.shop['drivewayDirection']]
    side = (-heading[1], heading[0])
    home = advance(tile(world.match['cell']), world.match['drivewayDirection'])
    shop = advance(tile(world.shop['entrance']), world.shop['drivewayDirection'])
    diff = np.subtract(home, shop)
    axial, lateral = int(diff @ heading), int(diff @ side)
    path = [home]
    while axial > 0:
        axial -= 1
        lateral -= int(np.sign(lateral))
        path.append(tuple(np.asarray(shop) + axial * np.asarray(heading) + lateral * np.asarray(side)))
    return [edge_id(world.local(first), world.local(second)) for first, second in zip(path, path[1:])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--offset', type=int, default=0)
    difficulty = parser.add_mutually_exclusive_group()
    difficulty.add_argument('--gaps', action='store_true')
    difficulty.add_argument('--gap-count', type=int, choices=(2, 3))
    diagnostics = parser.add_mutually_exclusive_group()
    diagnostics.add_argument('--oracle', action='store_true', help='Diagnostic matching anchor, outside policy play')
    diagnostics.add_argument('--preferred-component', action='store_true',
                             help='Use only the highest-weight learned target component in the frozen head')
    diagnostics.add_argument('--sample-prefix', type=int, nargs='+',
                             help='Sample the first N edits, then choose the highest-probability action')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if min(args.workers, args.count, *(args.sample_prefix or [1])) < 1 or args.output.exists():
        parser.error('Use positive counts and a fresh output')
    torch.set_num_threads(2)
    stages = MULTIPLE_STAGES[args.gap_count] if args.gap_count else GAP_STAGES if args.gaps else STAGES
    if args.verify_only:
        results = feasibility(args.dll, stages, args.count)
    else:
        model = MaskablePPO.load(args.checkpoint, device='cpu')
        if 'target_roles' in model.observation_space.spaces:
            from triad_ppo import SelectionEnvironment, SelectionHead

            if args.preferred_component:
                before = policy_fingerprint(model.policy)
                old = model.policy.action_net
                head = SelectionHead(old.base)
                head.load_state_dict(old.state_dict(), strict=True)
                head.select_component = True
                model.policy.action_net = head
                if policy_fingerprint(model.policy) != before:
                    raise RuntimeError('Component decoding changed frozen weights')
            env_factory = partial(SelectionEnvironment, args.dll)
        else:
            if args.preferred_component:
                parser.error('Learned target weights are required for component decoding')
            env_factory = partial(TriadEnvironment, args.dll, args.oracle)
        results = evaluate(model, env_factory, stages, args.count, args.offset, args.workers, args.sample_prefix)
    write(args.output, dict(results=results, oracle=args.oracle, preferred_component=args.preferred_component,
                            native_sha256=digest(args.dll),
                            checkpoint_sha256=digest(args.checkpoint), evaluator_sha256=digest(__file__)))


if __name__ == '__main__':
    main()
