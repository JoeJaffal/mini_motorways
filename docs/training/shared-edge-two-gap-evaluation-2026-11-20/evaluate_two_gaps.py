"""Evaluate two sequential builds with a frozen one-build shared-edge policy."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import gymnasium
import numpy as np
import torch

from checkpoint_tools import load_frozen, read_checkpoint
from connection_practice import ConnectionPractice, DIRECT_STAGE, SINGLE_BUILD_STAGE, WAIT
from edge_policy import checkpoint_policy
from environment import DIRS
from hierarchy_rollout import policy_fingerprint
from practice_replay import identity, observation_hash
from practice_reward import connection_potential


class TwoGapPractice(ConnectionPractice):
    def __init__(self, host, diagonal):
        super().__init__(host_dll=host, split='validation', stage=DIRECT_STAGE)
        self.fixture = 'two-gap-diagonal' if diagonal else 'two-gap-axis'

    def reset(self, *, seed):
        gymnasium.Env.reset(self, seed=seed)
        self.scenario_seed = seed
        self.visible_encoder.reset()
        self.practice_bounds = None
        self.practice_area.fill(True)
        self._generation += 1
        self.done = False
        self.paused_tokens = self.edit_count = self.decisions = 0
        self.focus = [None, None]
        self.role = 'executor'
        self._clear_operands()
        self.training_reward_total = self.reward_road_units = self.shaping_total = self.road_cost_total = 0.
        self.timings.clear()
        result = self._call(command='reset', version='OriginalReference', practice=True,
                            practiceSplit=self.split, practiceStage=self.fixture, seed=seed)
        self._set_practice_area()
        if (not result['accepted'] or result['terminated'] or result['truncated']
                or self.raw['time'] != 0 or self.raw['tripsCompleted'] != 0
                or self.raw['inventory'] != [2, 0, 0, 0, 0, 0] or self.connected()):
            raise RuntimeError('Expected disconnected two-gap fixture with two road units')
        return self.encode()

    def action_masks(self):
        mask = super().action_masks()
        mask[WAIT] = False
        return mask

    def connected(self):
        return bool(connection_potential(self.raw, self.practice_area))


def locate_gaps(env):
    house, = (b for b in env.raw['buildings'] if b['isHouse'])
    shop, = (b for b in env.raw['buildings'] if not b['isHouse'])
    hx, hy = house['cell']['x'], house['cell']['y']
    dx, dy = DIRS[shop['drivewayDirection']]
    tx, ty = shop['entrance']['x'] + dx, shop['entrance']['y'] + dy
    dx, dy = (tx > hx) - (tx < hx), (ty > hy) - (ty < hy)
    steps = max(abs(tx - hx), abs(ty - hy))
    if hx + steps * dx != tx or hy + steps * dy != ty:
        raise RuntimeError('Expected a straight road')
    direction = DIRS.index((dx, dy))
    slots = []
    edges = []
    for i in range(steps):
        x, y = hx + i * dx, hy + i * dy
        if not env.raw['connections'][y * 50 + x] & (1 << direction):
            slots.append(i)
            edges.append(frozenset(((x, y), (x + dx, y + dy))))
    if len(slots) != 2 or slots[0] < 1 or slots[1] >= steps - 1 or slots[1] - slots[0] < 2:
        raise RuntimeError('Expected two distinct interior gaps with a road segment between them')
    if dx and dy:
        label = 'down-right' if dx * dy > 0 else 'down-left'
    else:
        label = 'horizontal' if dx else 'vertical'
    return edges, label


def play_build(env, action):
    obs, reward, terminated, truncated, info = env.step(action)
    if (terminated or truncated or reward != 0 or info['seconds'] != 0
            or info['new_connections'] != 1 or info['road_units_spent'] != 1):
        raise RuntimeError('Expected one paused new connection costing one road unit')
    return obs, env.connected()


def native_deliveries(env):
    result = env._call(command='step', ticks=round(env.seconds / .05))
    raw = result['observation']
    if result['truncated'] or not (raw['failed'] or np.isclose(raw['time'], env.seconds)):
        raise RuntimeError('Expected the native horizon or game over')
    return dict(trips=raw['tripsCompleted'], seconds=raw['time'],
                ending='game_over' if raw['failed'] else 'task_horizon')


def choose_actions(policy, observations, masks, expected, environments, generators, mode):
    if mode == 'scripted':
        return [
            next(int(a) for a in np.flatnonzero(mask) if frozenset(env.direct_endpoints(a)) == edge)
            for env, mask, edge in zip(environments, masks, expected)
        ]
    if mode == 'uniform':
        legal_actions = [np.flatnonzero(mask) for mask in masks]
        return [int(legal[torch.randint(len(legal), (1,), generator=rng).item()])
                for legal, rng in zip(legal_actions, generators)]
    batch = {k: np.stack([item[k] for item in observations]) for k in observations[0]}
    with torch.inference_mode():
        inputs, _ = policy.obs_to_tensor(batch)
        probabilities = policy.get_distribution(inputs, action_masks=np.stack(masks)).distribution.probs
    if mode == 'greedy':
        return probabilities.argmax(dim=1).tolist()
    return [int(torch.multinomial(row, 1, generator=rng).item()) for row, rng in zip(probabilities, generators)]


def compare_group(policy, pool, workers, seeds):
    group = list(zip(workers, seeds))
    observations = list(pool.map(lambda item: item[0].reset(seed=item[1]), group))
    proofs = [observation_hash(o) for o in observations]
    masks = list(pool.map(lambda env: env.action_masks(), workers))
    gaps, directions = zip(*(locate_gaps(env) for env in workers))
    for env, legal, edges in zip(workers, masks, gaps):
        candidates = {frozenset(env.direct_endpoints(a)) for a in np.flatnonzero(legal)}
        if not set(edges) <= candidates:
            raise RuntimeError('A fixture gap is missing from the native legal mask')
    rows = [dict(seed=seed, direction=direction, missing_endpoints=[sorted(edge) for edge in edges],
                 initial_legal_builds=int(mask.sum()))
            for seed, direction, edges, mask in zip(seeds, directions, gaps, masks)]

    for mode in ('scripted', 'sampled', 'greedy', 'uniform'):
        current_obs = list(pool.map(lambda item: item[0].reset(seed=item[1]), group))
        current_masks = list(pool.map(lambda env: env.action_masks(), workers))
        if any(observation_hash(o) != h or not np.array_equal(a, b)
               for o, h, a, b in zip(current_obs, proofs, current_masks, masks)):
            raise RuntimeError('Fixture or action mask changed across modes')
        generators = [torch.Generator().manual_seed(100000 + seed) for seed in seeds]
        attempts = [dict(actions=[], exact=[], connected=[]) for _ in seeds]
        for step in range(2):
            actions = choose_actions(policy, current_obs, current_masks, [g[step] for g in gaps],
                                     workers, generators, mode)
            for env, action, expected, record in zip(workers, actions, gaps, attempts):
                record['actions'].append(action)
                record['exact'].append(frozenset(env.direct_endpoints(action)) in expected)
            results = list(pool.map(lambda pair: play_build(*pair), zip(workers, actions)))
            current_obs = [o for o, _ in results]
            for (_, connected), record in zip(results, attempts):
                record['connected'].append(connected)
            if step == 0:
                current_masks = list(pool.map(lambda env: env.action_masks(), workers))
        deliveries = list(pool.map(native_deliveries, workers))
        for row, attempt, deliveries_result in zip(rows, attempts, deliveries):
            if mode == 'scripted' and attempt['connected'] != [False, True]:
                raise RuntimeError('Scripted fixture must require both builds')
            row[mode] = dict(attempt, **deliveries_result)
    return rows


def compare_family(policy, host, seeds, diagonal, width):
    environments = []
    try:
        for _ in range(width):
            environments.append(TwoGapPractice(host, diagonal))
        with ThreadPoolExecutor(max_workers=width) as pool:
            return [row for start in range(0, len(seeds), width)
                    for row in compare_group(policy, pool, environments[:len(seeds[start:start+width])],
                                             seeds[start:start+width])]
    finally:
        for env in environments:
            env.close()


def evaluate(args):
    torch.set_num_threads(2)
    config = read_checkpoint(args.checkpoint)['config']
    reference = ConnectionPractice(host_dll=args.native_host, stage=SINGLE_BUILD_STAGE)
    try:
        policy = checkpoint_policy(reference, lambda _: 0., config)
        saved = load_frozen(args.checkpoint, policy, identity(reference))
    finally:
        reference.close()
    axes = compare_family(policy, args.fixture_host, list(range(20000, 20100)), False, args.workers)
    print('Completed 100 axis-aligned two-gap layouts', flush=True)
    diagonals = compare_family(policy, args.fixture_host, list(range(20100, 20200)), True, args.workers)
    print('Completed 100 diagonal two-gap layouts', flush=True)
    if policy_fingerprint(policy) != saved['policy_sha256']:
        raise RuntimeError('Evaluation changed frozen weights')
    return dict(policy_sha256=saved['policy_sha256'], changed_weights=False,
                fixture_host_sha256=hashlib.sha256(Path(args.fixture_host).read_bytes()).hexdigest(),
                native_host_sha256=config['environment']['dll_sha256'],
                evaluation_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                horizon_seconds=180, workers=args.workers, layouts=axes + diagonals)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--native-host', required=True)
    parser.add_argument('--fixture-host', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1 or Path(args.output).exists():
        parser.error('Use a positive worker count and a fresh output path')
    data = evaluate(args)
    with Path(args.output).open('x') as out:
        json.dump(data, out, separators=(',', ':'))
        out.write('\n')
