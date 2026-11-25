"""Replay final-policy city misses and test single-edge alternatives with the native simulator."""

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from audit_city_service import tile
from city_road_pilot import CityRoadEnv, edge_action
from export_city_replays import action_endpoints
from prepare_city_policy import masked_probs, sha256


def component(graph, sources):
    seen = set(sources)
    pending = list(seen)
    while pending:
        for cell in graph[pending.pop()]:
            if cell not in seen:
                seen.add(cell)
                pending.append(cell)
    return seen


def built_graph(raw):
    edges = defaultdict(set)
    for index, links in enumerate(raw['connections']):
        for direction in range(4):
            if links & (1 << direction):
                start, end = action_endpoints(1 + 4 * index + direction)
                edges[start].add(end)
                edges[end].add(start)
    return edges


def single_joins(raw, target, mask, graph):
    starts = [tile(b['cell']) for b in raw['buildings'] if b['isHouse'] and b['color'] == target['color']]
    if not starts:
        return ()
    home = component(graph, starts)
    shop = component(graph, map(tile, target['entrances']))
    if home & shop:
        return ()
    return sorted({edge_action(a, b) for a in home for b in shop
                   if max(abs(a[0]-b[0]), abs(a[1]-b[1])) == 1 and mask[edge_action(a, b)]})


def check_alternative(env, game, target_id, actions, option):
    env.reset(options={'scenario_seed': game['seed']})
    for action in actions[:option['decision']]:
        env.step(action)
    assert env.raw['time'] == option['second']
    assert env.action_masks()[option['alternative']]
    previous_stock = env.raw['inventory'][0]
    env.step(option['alternative'])
    paid = previous_stock - env.raw['inventory'][0]
    while not env.done and env.raw['time'] < option['second'] + 90:
        env.step(0)
        target = next(b for b in env.raw['buildings'] if b['id'] == target_id)
        if target['served']:
            return dict(native_road_cost=paid, first_delivery_second=env.raw['time'])
    return dict(native_road_cost=paid, first_delivery_second=None)


def replay(dll, checkpoint, expected):
    torch.set_num_threads(1)
    model = MaskablePPO.load(checkpoint, device='cpu')
    env = CityRoadEnv(dll)
    focus = {t['id']: t for t in expected['targets']
             if t['arrival_stock'] and not t['served'] and expected['seconds'] - t['first_seen'] >= 90}
    try:
        obs, info = env.reset(options={'scenario_seed': expected['seed']})
        rng = np.random.default_rng(expected['action_seed'])
        choices = defaultdict(dict)
        actions = []
        while not env.done:
            mask = env.action_masks()
            probabilities = masked_probs(model, obs, mask).astype(np.float64)
            probabilities /= probabilities.sum()
            action = int(rng.choice(len(probabilities), p=probabilities))
            pending = [b for b in env.raw['buildings'] if b['id'] in focus and not b['served']]
            if pending:
                graph = built_graph(env.raw)
                for target in pending:
                    options = single_joins(env.raw, target, mask, graph)
                    seen = choices[target['id']]
                    if action in options or len(seen) >= 4:
                        continue
                    for alternative in options[:4-len(seen)]:
                        seen.setdefault(alternative, dict(
                            decision=len(actions), second=env.raw['time'], road_stock=info['road_stock'],
                            sampled=action, alternative=alternative, edge=action_endpoints(alternative),
                            alternative_probability=float(probabilities[alternative]),
                            all_direct_join_probability=float(probabilities[options].sum()),
                            wait_probability=float(probabilities[0]),
                        ))
            actions.append(action)
            obs, _, terminated, truncated, info = env.step(action)
        assert all(info[key] == expected[key] for key in info)
        assert (terminated, truncated) == (expected['native_game_over'], expected['truncated'])
        assert all(not b['served'] for b in env.raw['buildings'] if b['id'] in focus)
        results = []
        for target, options in choices.items():
            tested = []
            for option in options.values():
                tested.append(option | check_alternative(env, expected, target, actions, option))
            results.append(dict(id=target, candidates=tested))
        return dict(seed=expected['seed'], action_seed=expected['action_seed'],
                    original_deliveries=expected['trips'], focus=sorted(focus),
                    actions=actions, results=results)
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    review = json.loads((args.review/'review.json').read_text())
    checkpoint = review['models'][-1]
    assert sha256(Path(checkpoint)) == review['sha256'][checkpoint]
    assert sha256(args.dll) == review['host_sha256']
    rows = [json.loads(line) for line in (args.review/'games.jsonl').read_text().splitlines()]
    qualifying = [g for g in rows if g['model'] == len(review['models'])-1 and any(
        t['arrival_stock'] and not t['served'] and g['seconds'] - t['first_seen'] >= 90 for t in g['targets'])]
    with ProcessPoolExecutor(max_workers=6, mp_context=multiprocessing.get_context('spawn')) as pool:
        jobs = [pool.submit(replay, args.dll, checkpoint, game) for game in qualifying]
        games = [job.result() for job in jobs]
    with args.output.open('x') as stream:
        json.dump(dict(checkpoint=checkpoint, checkpoint_sha256=review['sha256'][checkpoint],
                       host_sha256=review['host_sha256'], games=games), stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
