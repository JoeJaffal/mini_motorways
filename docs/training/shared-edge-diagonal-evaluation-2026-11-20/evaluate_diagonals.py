"""Evaluate a frozen shared-edge policy on isolated native diagonal fixtures."""
import argparse
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


def build(env, action):
    _, reward, terminated, truncated, info = env.step(int(action))
    if not terminated or truncated or info['new_connections'] != 1 or info['seconds'] != 0:
        raise RuntimeError('Expected one native build and natural diagnostic termination')
    return int(reward)


def run(args):
    torch.set_num_threads(2)
    payload = read_checkpoint(args.checkpoint)
    fingerprint = payload['policy_sha256']
    config = payload['config']
    # Verify the checkpoint against its actual training host before applying
    # those exact frozen weights to the test-only reset distribution.
    reference = ConnectionPractice(host_dll=args.native_host, stage=SINGLE_BUILD_STAGE)
    try:
        policy = checkpoint_policy(reference, lambda _: 0., config)
        saved = load_frozen(args.checkpoint, policy, identity(reference))
        if saved['policy_sha256'] != fingerprint:
            raise RuntimeError('Checkpoint changed while loading')
    finally:
        reference.close()

    env = DiagonalPractice(host_dll=args.fixture_host, stage=SINGLE_BUILD_STAGE, split='validation')
    try:
        rows = []
        for seed in range(20100, 20200):
            observations, _ = env.reset(seed=seed)
            obs_hash = observation_hash(observations)
            mask = env.action_masks()
            a, b = gap(env)
            dx, dy = b[0] - a[0], b[1] - a[1]
            if abs(dx) != 1 or abs(dy) != 1:
                raise RuntimeError('Fixture needs a diagonal repair')
            target, = [int(i) for i in np.flatnonzero(mask)
                       if set(env.direct_endpoints(i)) == {a, b}]
            with torch.inference_mode():
                inputs, _ = policy.obs_to_tensor(observations)
                probs = policy.get_distribution(inputs, action_masks=mask).distribution.probs[0]
            rng = torch.Generator().manual_seed(100000 + seed)
            uniform_rng = torch.Generator().manual_seed(100000 + seed)
            legal = np.flatnonzero(mask)
            choices = dict(
                scripted=target,
                sampled=int(torch.multinomial(probs, 1, generator=rng).item()),
                greedy=int(probs.argmax().item()),
                uniform=int(legal[torch.randint(len(legal), (1,), generator=uniform_rng).item()]),
            )
            row = dict(seed=seed, slope=dx * dy, missing_endpoints=[a, b], target=target,
                       legal_builds=len(legal), exact_gap_probability=float(probs[target]))
            for label, action in choices.items():
                obs, _ = env.reset(seed=seed)
                if observation_hash(obs) != obs_hash or not np.array_equal(mask, env.action_masks()):
                    raise RuntimeError('Fixture or legal mask changed between comparison arms')
                row[label] = dict(action=action, exact_gap=action == target, connected=build(env, action))
            if row['scripted']['connected'] != 1:
                raise RuntimeError('Correct fixture repair failed')
            rows.append(row)
        if policy_fingerprint(policy) != fingerprint:
            raise RuntimeError('Frozen evaluation changed the policy')
        return dict(
            checkpoint_policy_sha256=fingerprint,
            fixture_host_sha256=hashlib.sha256(Path(args.fixture_host).read_bytes()).hexdigest(),
            original_host_sha256=config['environment']['dll_sha256'],
            evaluation_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            changed_weights=False,
            trials=rows,
        )
    finally:
        env.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--native-host', required=True)
    parser.add_argument('--fixture-host', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    if Path(arguments.output).exists():
        parser.error('Choose a new output path')
    result = run(arguments)
    with Path(arguments.output).open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
