"""One frozen build, then native simulation of deliveries without policy waits."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from checkpoint_tools import load_frozen, read_checkpoint
from connection_practice import ConnectionPractice, SINGLE_BUILD_STAGE
from edge_policy import checkpoint_policy
from hierarchy_rollout import policy_fingerprint
from practice_replay import identity, observation_hash
from test_one_gap import gap


class DiagonalPractice(ConnectionPractice):
    def _call(self, **request):
        if request['command'] == 'reset':
            request['practiceStage'] = 'diagonal-single-build'
        return super()._call(**request)


def rollout(env, seed, action, expected_hash, mask, edge):
    obs, _ = env.reset(seed=seed)
    if observation_hash(obs) != expected_hash or not np.array_equal(mask, env.action_masks()):
        raise RuntimeError('Reset changed the observation or the legal mask')
    connected = False
    exact_gap = False
    if action is not None:
        exact_gap = set(env.direct_endpoints(action)) == edge
        _, reward, terminated, truncated, info = env.step(action)
        if not terminated or truncated or info['seconds'] != 0 or info['new_connections'] != 1:
            raise RuntimeError('Expected precisely one native build')
        connected = reward == 1
    # The single-build wrapper is terminal; the native world can still run
    # the repaired network without any further policy actions.
    result = env._call(command='step', ticks=round(env.seconds / .05))
    raw = result['observation']
    failed = bool(raw['failed'])
    if result['truncated'] or not (failed or np.isclose(raw['time'], env.seconds)):
        raise RuntimeError('Native delivery run stopped before a natural ending')
    return dict(action=action, exact_gap=exact_gap, connected=connected,
                trips=raw['tripsCompleted'], seconds=raw['time'],
                ending='game_over' if failed else 'task_horizon')


def inspect_layout(env, seed):
    observation, _ = env.reset(seed=seed)
    a, b = gap(env)
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx and dy:
        direction = 'down-right' if dx * dy > 0 else 'down-left'
    else:
        direction = 'horizontal' if dx else 'vertical'
    return observation, env.action_masks(), {a, b}, direction


def compare_family(policy, env_type, host, seeds, workers):
    environments = []
    try:
        for _ in range(workers):
            environments.append(env_type(host_dll=host, stage=SINGLE_BUILD_STAGE, split='validation'))
        rows = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for start in range(0, len(seeds), workers):
                group = list(zip(environments, seeds[start:start+workers]))
                layouts = list(pool.map(lambda pair: inspect_layout(*pair), group))
                obs, masks, edges, directions = zip(*layouts)
                inputs = {k: np.stack([o[k] for o in obs]) for k in obs[0]}
                with torch.inference_mode():
                    tensor, _ = policy.obs_to_tensor(inputs)
                    probabilities = policy.get_distribution(tensor, action_masks=np.stack(masks)).distribution.probs
                choices = {
                    'sampled': [int(torch.multinomial(p, 1, generator=torch.Generator().manual_seed(100000+seed)).item())
                                for p, (_, seed) in zip(probabilities, group)],
                    'greedy': probabilities.argmax(dim=1).tolist(),
                    'no_build': [None] * len(group),
                }
                results = {}
                hashes = [observation_hash(o) for o in obs]
                for mode, actions in choices.items():
                    arguments = [(env, seed, action, digest, mask, edge)
                                 for (env, seed), action, digest, mask, edge
                                 in zip(group, actions, hashes, masks, edges)]
                    results[mode] = list(pool.map(lambda args: rollout(*args), arguments))
                for i, (_, seed) in enumerate(group):
                    rows.append(dict(seed=seed, direction=directions[i], missing_endpoints=sorted(edges[i]),
                                     **{mode: entries[i] for mode, entries in results.items()}))
        return rows
    finally:
        for env in environments:
            env.close()


def evaluate(args):
    torch.set_num_threads(2)
    config = read_checkpoint(args.checkpoint)['config']
    verification = ConnectionPractice(host_dll=args.native_host, stage=SINGLE_BUILD_STAGE)
    try:
        policy = checkpoint_policy(verification, lambda _: 0., config)
        saved = load_frozen(args.checkpoint, policy, identity(verification))
    finally:
        verification.close()
    rows = compare_family(policy, ConnectionPractice, args.native_host, list(range(20000, 20100)), args.workers)
    rows.extend(compare_family(policy, DiagonalPractice, args.fixture_host, list(range(20100, 20200)), args.workers))
    if policy_fingerprint(policy) != saved['policy_sha256']:
        raise RuntimeError('Frozen evaluation changed weights')
    return dict(policy_sha256=saved['policy_sha256'],
                fixture_host_sha256=hashlib.sha256(Path(args.fixture_host).read_bytes()).hexdigest(),
                normal_host_sha256=config['environment']['dll_sha256'],
                evaluation_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                workers=args.workers, simulated_horizon_seconds=180, changed_weights=False, layouts=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--native-host', required=True)
    parser.add_argument('--fixture-host', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--workers', type=int, default=8)
    options = parser.parse_args()
    if options.workers < 1 or Path(options.output).exists():
        parser.error('Provide a positive worker count and a fresh output file')
    results = evaluate(options)
    with Path(options.output).open('x') as f:
        json.dump(results, f, indent=2)
        f.write('\n')
