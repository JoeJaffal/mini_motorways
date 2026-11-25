"""Regenerate three paired reserved-evaluation games as offline browser replays."""

import argparse
import json
from pathlib import Path
from statistics import mean

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import FORWARD, CityRoadEnv
from prepare_city_policy import masked_probs, sha256
from visible_observation import WIDTH

ROOT = Path(__file__).resolve().parents[1]


def frame(raw, description, edge=None):
    return dict(
        practice_bounds=[raw[key] for key in ('playableXMin', 'playableXMax', 'playableYMin', 'playableYMax')],
        time=raw['time'], score=raw['tripsCompleted'], road_stock=raw['inventory'][0],
        description=description, edge=edge, focus=[],
        connections=[[i, bits] for i, bits in enumerate(raw['connections']) if bits],
        buildings=[{key: b[key] for key in ('cell', 'width', 'height', 'color', 'isHouse', 'demand')}
                   for b in raw['buildings']],
        cars=[{key: v[key] for key in ('x', 'y', 'color')}
              for v in raw['vehicles'] if v['visible']],
    )


def action_endpoints(action):
    cell, direction = divmod(action-1, 4)
    x, y = cell % WIDTH, cell // WIDTH
    dx, dy = FORWARD[direction]
    return (x, y), (x+dx, y+dy)


def replay(env, model, expected):
    obs, info = env.reset(options={'scenario_seed': expected['seed']})
    rng = np.random.default_rng(expected['action_seed'])
    terrain = [[i, kind] for i, kind in enumerate(env.raw['terrain']) if kind]
    frames = [frame(env.raw, 'The city starts with an empty road network.')]
    actions = []
    first_score = None
    while not env.done:
        mask = env.action_masks()
        p = masked_probs(model, obs, mask).astype(np.float64)
        if not np.isfinite(p).all() or p[~mask].any():
            raise RuntimeError('Invalid native masked probabilities')
        action = int(rng.choice(len(p), p=p/p.sum()))
        previous_awards = info['weekly_awards']
        obs, reward, terminal, truncated, info = env.step(action)
        edge = action_endpoints(action) if action else None
        description = f'Build road {edge[0]} → {edge[1]}' if action else 'Wait'
        if reward:
            description += f' · {int(reward)} delivered'
            if first_score is None:
                first_score = info['seconds']
        if info['weekly_awards'] > previous_awards:
            description += ' · weekly road award'
        frames.append(frame(env.raw, description, edge))
        actions.append(action)
    actual = dict(**info, first_score=first_score, native_game_over=terminal, truncated=truncated)
    for key in ('seed', 'seconds', 'trips', 'road_stock', 'buildings', 'weekly_awards',
                'road_actions', 'wait_actions', 'first_score', 'native_game_over', 'truncated'):
        if actual[key] != expected[key]:
            raise RuntimeError(f'Replay disagrees with archived result for {key}: {actual[key]} vs {expected[key]}')
    return frames, terrain, actions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll', 'checkpoint', 'evaluation', 'summary', 'output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    model = MaskablePPO.load(args.checkpoint, device='cpu')
    reference = json.loads(args.summary.read_text())
    checkpoint_hash = sha256(args.checkpoint)
    if checkpoint_hash not in reference['checkpoints'].values() or sha256(args.dll) != reference['host_sha256']:
        raise RuntimeError('Use the exact checkpoint and simulator from the reserved evaluation')
    rows = [json.loads(line) for line in args.evaluation.read_text().splitlines()]
    sampled = [row for row in rows if row['checkpoint_decisions']==model.num_timesteps and not row['greedy']]
    if not sampled:
        raise RuntimeError('No sampled games match the supplied checkpoint')
    average = mean(row['trips'] for row in sampled)
    chosen = {
        'best': max(sampled, key=lambda row: row['trips']),
        'average': min(sampled, key=lambda row: abs(row['trips']-average)),
        'worst': min(sampled, key=lambda row: (row['trips'], row['seconds'])),
    }
    template = (ROOT/'training/stage1_replay.html').read_text()
    args.output.mkdir(parents=True, exist_ok=False)
    env = CityRoadEnv(args.dll)
    traces = {}
    try:
        for label, expected in chosen.items():
            frames, terrain, actions = replay(env, model, expected)
            ending = 'Evaluation stopped at 10 minutes with the city still alive.' if expected['truncated'] else 'Native game-over.'
            replay_data = dict(
                title=f'{label.title()} game · {expected["trips"]} deliveries',
                intro=f'Los Angeles · seed {expected["seed"]} · final score {expected["trips"]} · {ending}',
                speed='16', ending=ending, frames=frames, terrain=terrain,
            )
            encoded = json.dumps(replay_data, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
            page = args.output/f'{label}.html'
            page.write_text(template.replace('/*REPLAY_DATA*/', encoded))
            traces[label] = dict(episode=expected, actions=actions, replay_sha256=sha256(page))
            print(f'{label} | seed {expected["seed"]} | {expected["trips"]} deliveries | {len(actions)} verified decisions',
                  flush=True)
    finally:
        env.close()
    (args.output/'selection.json').write_text(json.dumps(dict(
        games_in_evaluation=len(sampled), mean=average, checkpoint_sha256=checkpoint_hash,
        host_sha256=reference['host_sha256'], evaluation_sha256=sha256(args.evaluation), traces=traces,
    ), indent=2)+'\n')


if __name__ == '__main__':
    main()
