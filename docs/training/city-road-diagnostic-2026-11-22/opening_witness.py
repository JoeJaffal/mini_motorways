"""Find and test a legal opening route as an offline feasibility witness."""

import argparse
from collections import defaultdict, deque
import json
from pathlib import Path

import numpy as np

from city_road_pilot import FORWARD, CityRoadEnv
from diagnose_city_policy import routes
from visible_observation import WIDTH


def build_graph(env):
    graph = defaultdict(list)
    for action in np.flatnonzero(env.action_masks()[1:]) + 1:
        cell, direction = divmod(int(action) - 1, 4)
        x, y = cell % WIDTH, cell // WIDTH
        dx, dy = FORWARD[direction]
        a, b = (x, y), (x+dx, y+dy)
        graph[a].append((b, int(action)))
        graph[b].append((a, int(action)))
    return graph


def shortest_path(graph, home, shop):
    start = home['cell']['x'], home['cell']['y']
    targets = {(p['x'], p['y']) for p in shop['entrances']}
    queue = deque([start])
    previous = {start: None}
    while queue:
        cell = queue.popleft()
        if cell in targets:
            break
        for neighbor, action in graph[cell]:
            if neighbor not in previous:
                previous[neighbor] = (cell, action)
                queue.append(neighbor)
    else:
        return [], []
    cells, actions = [cell], []
    while cell != start:
        cell, action = previous[cell]
        cells.append(cell)
        actions.append(action)
    return list(reversed(cells)), list(reversed(actions))


def witness(env, seed):
    attempts = []
    for build_time in range(0, 101, 5):
        env.reset(options={'scenario_seed': seed})
        while env.info()['seconds'] < build_time and not env.done:
            env.step(0)
        if env.done:
            break
        graph = build_graph(env)
        buildings = env.raw['buildings']
        candidates = [(cells, actions, shop['id']) for home in buildings if home['isHouse']
                      for shop in buildings if not shop['isHouse'] and shop['color'] == home['color']
                      for cells, actions in [shortest_path(graph, home, shop)] if actions]
        if not candidates:
            attempts.append(dict(seconds=build_time, path_in_static_mask=False))
            continue
        cells, actions, shop_id = min(candidates, key=lambda item: len(item[1]))
        initial_stock = env.info()['road_stock']
        for index, action in enumerate(actions):
            cell, direction = divmod(action - 1, 4)
            if env.raw['connections'][cell] & (1 << direction):
                # Laying the neighboring road can attach a parcel entrance for free.
                continue
            if not env.action_masks()[action]:
                attempts.append(dict(seconds=build_time, path_in_static_mask=True, blocked_link=index,
                                     links=len(actions), stock=env.info()['road_stock']))
                break
            env.step(action)
        else:
            connected = shop_id in routes(env)['suppliedDestinationIds']
            stock_used = initial_stock - env.info()['road_stock']
            while not env.done and not env.info()['trips']:
                env.step(0)
            if env.info()['trips']:
                return dict(seed=seed, attempts=attempts, built_at=build_time, connected=connected,
                            opening_stock=initial_stock, stock_used=stock_used, path=cells,
                            first_delivery_seconds=env.info()['seconds'])
            attempts.append(dict(seconds=build_time, built=True, connected=connected,
                                 stock_used=stock_used, first_delivery_seconds=None))
    return dict(seed=seed, attempts=attempts, first_delivery_seconds=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--suite', type=Path, required=True)
    args = parser.parse_args()
    seeds = [row['seed'] for row in json.loads(args.suite.read_text())['jobs']
             if row['cohort']=='opening' and row['original']]
    env = CityRoadEnv(args.dll, include_connectivity=True)
    try:
        print(json.dumps([witness(env, seed) for seed in seeds], indent=2))
    finally:
        env.close()


if __name__ == '__main__':
    main()
