"""Frozen cue substitutions and native bypass traversal checks.

Run from the repository root with PYTHONPATH=training and the project venv.
The hidden link endpoints below are read only by the offline travel audit.
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from bend_ppo import digest, write
from construction_practice import endpoints, tile
from hierarchy_rollout import policy_fingerprint
from traffic_practice import TrafficEnvironment, visible_traffic

STAGES = ('traffic-junction-low-live', 'traffic-junction-high-live')
FEATURES = ('native', 'traffic', 'demand', 'traffic_and_demand')


def snapshot(env, stage, seed):
    obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
    return obs, env.action_masks(), env.env.controls()


def substitute(obs, other, feature):
    changed = {key: value.copy() for key, value in obs.items()}
    if feature in ('traffic', 'traffic_and_demand'):
        changed['grid'][19:24] = other['grid'][19:24]
        changed['clock'][3] = other['clock'][3]
    if feature in ('demand', 'traffic_and_demand'):
        changed['grid'][16:18] = other['grid'][16:18]
        changed['shops'][:, 2:4] = other['shops'][:, 2:4]
    return changed


def cue_audit(env, policy, seed, stages):
    low, high = [snapshot(env, stage, seed) for stage in stages]
    if not np.array_equal(low[1], high[1]) or low[2] != high[2]:
        raise RuntimeError('The paired boards have different legal edits')
    if not np.array_equal(low[0]['grid'][:16], high[0]['grid'][:16]):
        raise RuntimeError('The paired boards have different built layouts')
    labels = dict(wait=0, **low[2])
    result = {}
    for stage, item, other in zip(stages, (low, high), (high, low)):
        obs, mask, _ = item
        trials = {}
        for feature in FEATURES:
            state = substitute(obs, other[0], feature)
            with torch.inference_mode():
                values = policy.obs_to_tensor(state)[0]
                probabilities = policy.get_distribution(values, action_masks=mask).distribution.probs[0]
                trials[feature] = dict({label: float(probabilities[action]) for label, action in labels.items()},
                                       top_action=int(probabilities.argmax()))
        result[stage] = trials
    return result


def travel_audit(env, seed, mode, stage):
    _, _, labels = snapshot(env, stage, seed)
    w = env.env
    new_edge = frozenset((x+w.x0, y+w.y0) for x, y in endpoints(labels['separate-exit']))
    b_id = 1
    crossers = set()
    trips = set()
    _, _, done, _, info = env.step(labels.get(mode, 0))
    while not done:
        for car in visible_traffic(w.raw):
            if car['shopId'] != b_id:
                continue
            trips.add(car['id'])
            if frozenset((tile(car['at']), tile(car['next']))) == new_edge and car['speed'] > .01:
                crossers.add(car['id'])
        _, _, done, _, info = env.step(0)
    return dict(b_cars_seen=len(trips), b_cars_observed_crossing=len(crossers), served=info['served'])


def visibility_audit(env, seed, stages):
    initial_warmup = env.warm_seconds
    result = {}
    try:
        for time in (0, 15, 25, 36):
            env.warm_seconds = time
            a, b = [snapshot(env, stage, seed)[:2] for stage in stages]
            states_match = np.array_equal(a[1], b[1]) and all(
                np.array_equal(a[0][key], b[0][key]) for key in a[0])
            if time <= 15 and not states_match:
                raise RuntimeError('The surge leaked into an observation before it occurred')
            result[time] = dict(same_policy_input=states_match, visible=[dict(
                cars=float(state['grid'][19].sum()*4), stopped=float(state['grid'][20].sum()*4),
                pins=float(state['shops'][:, 2].sum())) for state, _ in (a, b)])
    finally:
        env.warm_seconds = initial_warmup
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--start', type=int, default=79200)
    parser.add_argument('--count', type=int, default=32)
    parser.add_argument('--stages', nargs=2, default=STAGES, metavar=('LIGHT', 'HEAVY'))
    parser.add_argument('--visibility-audit', action='store_true', help='Check paired observations before and after demand changes')
    args = parser.parse_args()
    if args.output.exists() or args.count < 1:
        parser.error('Use a new results file and a positive count')
    torch.set_num_threads(2)
    model = MaskablePPO.load(args.checkpoint, device='cpu')
    policy = model.policy
    policy.set_training_mode(False)
    fingerprint = policy_fingerprint(policy)
    use_roots = 'roots' in model.observation_space.spaces
    env = TrafficEnvironment(args.dll, warm_seconds=36, horizon=120, wait_ticks=100, use_roots=use_roots)
    travel = TrafficEnvironment(args.dll, warm_seconds=36, horizon=62, wait_ticks=20, use_roots=use_roots)
    try:
        cues = {}
        crossings = {}
        visibility = {}
        for seed in range(args.start, args.start+args.count):
            cues[seed] = cue_audit(env, policy, seed, args.stages)
            crossings[seed] = {mode: travel_audit(travel, seed, mode, args.stages[-1])
                               for mode in ('feeder', 'separate-exit')}
            if args.visibility_audit:
                visibility[seed] = visibility_audit(env, seed, args.stages)
    finally:
        env.close()
        travel.close()
    if policy_fingerprint(policy) != fingerprint:
        raise RuntimeError('Frozen audit changed weights')
    write(args.output, dict(checkpoint_sha256=digest(args.checkpoint), fingerprint=fingerprint,
                            native_sha256=digest(args.dll), cues=cues, crossings=crossings,
                            visibility=visibility))


if __name__ == '__main__':
    main()
