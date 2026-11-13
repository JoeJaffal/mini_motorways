"""Bounded goal proposals translated to ordinary OriginalReference commands."""

from __future__ import annotations

import heapq
import hashlib
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np


WIDTH, HEIGHT = 50, 30
MAX_DESTINATIONS = 20
MAX_CANDIDATES = 48
RAW_CANDIDATES = 128
DIRS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
TOOLS = ("Road", "Bridge", "TrafficLight", "Roundabout", "Remove")
ACTION_WIDTH = 26
_PATH_CACHE = OrderedDict()
_CONNECT_CACHE = OrderedDict()
_CACHE_LOCK = threading.RLock()


def clear_caches():
    with _CACHE_LOCK:
        _PATH_CACHE.clear()
        _CONNECT_CACHE.clear()


def _remember(cache, key, value):
    with _CACHE_LOCK:
        cache[key] = value
        cache.move_to_end(key)
        if len(cache) > 4096:
            cache.popitem(last=False)


def _lookup(cache, key):
    with _CACHE_LOCK:
        if key not in cache:
            return None
        cache.move_to_end(key)
        return cache[key]


def _context(obs, occupied):
    if os.environ.get("TRAFFIC_DISABLE_PROPOSAL_CACHE") == "1":
        return None
    digest = hashlib.sha256()
    for name in ("terrain", "infrastructure", "connections", "pendingRemovals"):
        digest.update(np.asarray(obs[name], dtype=np.uint8).tobytes())
    digest.update(repr((obs["playableXMin"],obs["playableXMax"],obs["playableYMin"],obs["playableYMax"],
                       obs["inventory"][1] > 0,sorted(occupied),
                       [[(c["x"],c["y"]) for c in line["cells"]] for line in obs.get("railLines",[])])).encode())
    return digest.digest()


@dataclass(frozen=True)
class Candidate:
    request: dict
    label: str
    features: tuple[float, ...]
    priority: float = 0


def _cell(value: dict) -> tuple[int, int]:
    return int(value["x"]), int(value["y"])


def _index(cell: tuple[int, int]) -> int:
    return cell[1] * WIDTH + cell[0]


def _playable(cell: tuple[int, int], obs: dict) -> bool:
    x, y = cell
    return (obs["playableXMin"] <= x < obs["playableXMax"]
            and obs["playableYMin"] <= y < obs["playableYMax"])


def _connected(start: tuple[int, int], goal: tuple[int, int], connections: list[int], context=None) -> bool:
    cache_key = (context,start,goal)
    cached = _lookup(_CONNECT_CACHE, cache_key) if context is not None else None
    if cached is not None:
        return cached
    if start == goal:
        return True
    todo, seen = [start], {start}
    while todo:
        x, y = todo.pop()
        bits = connections[_index((x, y))]
        for direction, (dx, dy) in enumerate(DIRS):
            if not bits & (1 << direction):
                continue
            nxt = (x + dx, y + dy)
            if nxt == goal:
                if context is not None:
                    _remember(_CONNECT_CACHE,cache_key,True)
                return True
            if 0 <= nxt[0] < WIDTH and 0 <= nxt[1] < HEIGHT and nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    if context is not None:
        _remember(_CONNECT_CACHE,cache_key,False)
    return False


def reachable_pairs(obs: dict) -> int:
    """Compatible house/destination pairs linked by the actual graph."""
    parent = list(range(WIDTH * HEIGHT))

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for index, bits in enumerate(obs["connections"]):
        x, y = index % WIDTH, index // WIDTH
        for direction, (dx, dy) in enumerate(DIRS):
            nx, ny = x + dx, y + dy
            if bits & (1 << direction) and 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                parent[root(index)] = root(ny * WIDTH + nx)
    houses = [b for b in obs["buildings"] if b["isHouse"]]
    shops = [b for b in obs["buildings"] if not b["isHouse"]]
    count = 0
    for house in houses:
        source = root(_index(_cell(house["cell"])))
        for shop in shops:
            if house["color"] != shop["color"]:
                continue
            entrances = shop["entrances"] or [shop["entrance"]]
            if any(root(_index(_cell(entry))) == source for entry in entrances):
                count += 1
    return count


def _crossed_diagonal(a: tuple[int, int], b: tuple[int, int], obs: dict) -> bool:
    dx, dy = b[0] - a[0], b[1] - a[1]
    if not dx or not dy:
        return False
    bits = obs["connections"][_index(a)]
    if bits & (1 << DIRS.index((dx, dy))):
        return False
    cross_a, cross_b = (a[0], b[1]), (b[0], a[1])
    direction = DIRS.index((cross_b[0] - cross_a[0], cross_b[1] - cross_a[1]))
    return bool(obs["connections"][_index(cross_a)] & (1 << direction))


def _path(start: tuple[int, int], goal: tuple[int, int], obs: dict,
          occupied: set[tuple[int, int]], avoid: tuple[int, int] | None = None, context=None) -> list[tuple[int, int]]:
    cache_key = (context,start,goal,avoid)
    cached = _lookup(_PATH_CACHE, cache_key) if context is not None else None
    if cached is not None:
        return list(cached)
    terrain, infrastructure = obs["terrain"], obs["infrastructure"]
    rail = {_cell(cell) for line in obs.get("railLines", []) for cell in line["cells"]}
    roundabout_centers = {_cell(r["center"]) for r in obs.get("roundabouts", [])}
    heuristic = lambda cell: 0.2 * max(abs(goal[0] - cell[0]), abs(goal[1] - cell[1]))
    queue = [(heuristic(start), 0.0, start)]
    cost = {start: 0.0}
    previous = {}
    while queue:
        _, current_cost, current = heapq.heappop(queue)
        if current_cost > cost[current] + 1e-9:
            continue
        if current == goal:
            result = [goal]
            while result[-1] != start:
                result.append(previous[result[-1]])
            result = result[::-1]
            if context is not None:
                _remember(_PATH_CACHE,cache_key,tuple(result))
            return result
        x, y = current
        for dx, dy in DIRS:
            nxt = (x + dx, y + dy)
            nx, ny = nxt
            if not (0 <= nx < WIDTH and 0 <= ny < HEIGHT and _playable(nxt, obs)):
                continue
            if (nxt in occupied and nxt != goal) or nxt == avoid or nxt in roundabout_centers:
                continue
            if _crossed_diagonal(current, nxt, obs):
                continue
            idx = _index(nxt)
            if terrain[idx] == 2 or obs["pendingRemovals"][idx]:
                continue
            if terrain[idx] == 1 and not infrastructure[idx] and obs["inventory"][1] <= 0:
                continue
            # A bridge is expensive in finite stock; prefer existing infrastructure.
            tile_cost = 0.2 if infrastructure[idx] else (4.0 if terrain[idx] == 1 else 1.0)
            new_cost = current_cost + tile_cost + (0.4 if dx and dy else 0) + (2 if nxt in rail else 0)
            if new_cost + 1e-9 < cost.get(nxt, float("inf")):
                cost[nxt], previous[nxt] = new_cost, current
                heapq.heappush(queue, (new_cost + heuristic(nxt), new_cost, nxt))
    if context is not None:
        _remember(_PATH_CACHE,cache_key,())
    return []


def _next_stroke(path: list[tuple[int, int]], obs: dict, max_length: int = 5) -> tuple[tuple[int, int], tuple[int, int]] | None:
    if len(path) < 2:
        return None
    connections = obs["connections"]
    for index, (current, nxt) in enumerate(zip(path, path[1:])):
        dx, dy = nxt[0] - current[0], nxt[1] - current[1]
        direction = DIRS.index((dx, dy))
        if connections[_index(current)] & (1 << direction):
            continue
        end = index + 1
        while end + 1 < len(path) and end - index < max_length:
            a, b = path[end], path[end + 1]
            if (b[0] - a[0], b[1] - a[1]) != (dx, dy):
                break
            end += 1
        return current, path[end]
    return None


def _line_cells(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    count = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    return [(round(a[0] + (b[0] - a[0]) * i / count),
             round(a[1] + (b[1] - a[1]) * i / count)) for i in range(count + 1)] if count else [a]


def _features(kind: int, start=(0, 0), end=(0, 0), urgency=0.0, length=0.0,
              stock=0.0, tool: str | None = None, offer: dict | None = None,
              ident: int = 0) -> tuple[float, ...]:
    offer = offer or {}
    return (
        *(float(kind == i) for i in range(9)),
        *(float(tool == name) for name in TOOLS),
        start[0] / WIDTH, start[1] / HEIGHT, end[0] / WIDTH, end[1] / HEIGHT,
        min(1.0, urgency / 10), min(1.0, length / 20), min(1.0, stock / 100),
        float(offer.get("type", -1) + 1) / 6,
        float(offer.get("amount", 0)) / 30,
        float(offer.get("roads", 0)) / 30,
        min(1.0, ident / 100),
    )


def candidates(obs: dict, limit: int = MAX_CANDIDATES) -> list[Candidate]:
    """Return deterministic proposals; no future/diagnostic observation fields are read."""
    if obs["version"] != "OriginalReference":
        raise ValueError("Initial candidate generator targets OriginalReference")
    result = [Candidate({"command": "wait"}, "wait", _features(0))]
    for index, offer in enumerate(obs["upgradeChoices"]):
        motorway_bonus = 25 if offer["type"] == 2 else 0
        result.append(Candidate({"command": "upgrade", "choice": index},
                                f"upgrade {index}", _features(2, urgency=10, offer=offer),
                                100 + offer["roads"] + motorway_bonus))
    buildings = obs["buildings"]
    houses = [b for b in buildings if b["isHouse"]]
    shops = [b for b in buildings if not b["isHouse"]]
    shops.sort(key=lambda b: (-(b["demand"] + b["reserved"]), b["id"]))
    occupied = set()
    for b in buildings:
        x, y = _cell(b["cell"])
        for oy in range(b["height"]):
            for ox in range(b["width"]):
                occupied.add((x + ox, y + oy))
    seen_requests = set()
    context = _context(obs,occupied)
    motorway_endpoints = {_cell(m[end]) for m in obs.get("motorways", [])
                          for end in ("start", "end")}
    roundabout_centers = {_cell(r["center"]) for r in obs.get("roundabouts", [])}
    for shop in shops[:MAX_DESTINATIONS]:
        entrances = shop["entrances"] or [shop["entrance"]]
        entry_directions = shop["entranceDirections"] or [shop["drivewayDirection"]]
        access_pairs = [(_cell(entry), direction) for entry, direction in zip(entrances, entry_directions)]
        if not access_pairs:
            continue
        anchor = access_pairs[0][0]
        compatible = [h for h in houses if h["color"] == shop["color"]]
        compatible.sort(key=lambda h: (abs(h["cell"]["x"] - anchor[0]) +
                                        abs(h["cell"]["y"] - anchor[1]), h["id"]))
        for house in compatible[:5]:
            start = _cell(house["cell"])
            if any(_connected(start, target, obs["connections"],context) for target, _ in access_pairs):
                if obs["inventory"][2] > 0:
                    access = (start[0] + DIRS[house["drivewayDirection"]][0],
                              start[1] + DIRS[house["drivewayDirection"]][1])
                    for target, entry_direction in access_pairs:
                        dx, dy = DIRS[entry_direction]
                        outside = (target[0] + dx, target[1] + dy)
                        if not (_playable(access, obs) and _playable(outside, obs)):
                            continue
                        if access in occupied or outside in occupied or access in motorway_endpoints or outside in motorway_endpoints:
                            continue
                        a_idx, b_idx = _index(access), _index(outside)
                        if (obs["terrain"][a_idx] != 0 or obs["terrain"][b_idx] != 0
                                or obs["infrastructure"][a_idx] != 1 or obs["infrastructure"][b_idx] != 1
                                or obs["pendingRemovals"][a_idx] or obs["pendingRemovals"][b_idx]):
                            continue
                        length = max(abs(outside[0] - access[0]), abs(outside[1] - access[1]))
                        if length < 10 or not _connected(access, outside, obs["connections"],context):
                            continue
                        key = (*access, *outside)
                        if key in seen_requests:
                            continue
                        seen_requests.add(key)
                        urgency = shop["demand"] + shop["reserved"]
                        request = {"command": "motorway", "x": access[0], "y": access[1],
                                   "toX": outside[0], "toY": outside[1]}
                        result.append(Candidate(request,
                                                f"motorway house {house['id']} -> shop {shop['id']}",
                                                _features(3, access, outside, urgency, length,
                                                          obs["inventory"][2]),
                                                urgency * 10 + length - 15))
                continue
            if obs["inventory"][0] <= 0:
                continue
            direction = house["drivewayDirection"]
            access = (start[0] + DIRS[direction][0], start[1] + DIRS[direction][1])
            if (not _playable(access, obs) or access in occupied or
                    obs["terrain"][_index(access)] != 0):
                continue
            routes = []
            for target, entry_direction in access_pairs:
                dx, dy = DIRS[entry_direction]
                outside = (target[0] + dx, target[1] + dy)
                if (not _playable(outside, obs) or outside in occupied or
                        obs["terrain"][_index(outside)] != 0):
                    continue
                route = _path(access, outside, obs, occupied,context=context)
                if route:
                    routes.append(route + [target])
                    if len(route) > 5:
                        alternate = _path(access, outside, obs, occupied, avoid=route[len(route) // 2],context=context)
                        if alternate and alternate != route:
                            routes.append(alternate + [target])
            if not routes:
                continue
            for route in sorted(routes, key=len)[:2]:
                path = [start] + route
                if _crossed_diagonal(start, route[0], obs):
                    continue
                stroke = _next_stroke(path, obs, max_length=8)
                if stroke is None:
                    continue
                a, b = stroke
                key = (*a, *b)
                if key in seen_requests:
                    continue
                seen_requests.add(key)
                length = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
                line = _line_cells(a, b)
                roads = sum(obs["infrastructure"][_index(cell)] == 0 and obs["terrain"][_index(cell)] == 0
                            and cell not in occupied for cell in line)
                bridges = sum(obs["infrastructure"][_index(cell)] == 0 and obs["terrain"][_index(cell)] == 1
                              and cell not in occupied for cell in line)
                if roads + bridges > obs["inventory"][0] or bridges > obs["inventory"][1]:
                    continue
                request = {"command": "draw", "x": a[0], "y": a[1], "toX": b[0], "toY": b[1]}
                urgency = shop["demand"] + shop["reserved"]
                priority = urgency * 10 - len(path) + (15 if len(path) <= 9 else 0) + (4 if a == start else 0)
                result.append(Candidate(request, f"house {house['id']} -> shop {shop['id']}",
                                        _features(1, a, b, urgency, length, obs["inventory"][0]), priority))
    # Local edits are proposed around current demand and traffic, rather than all 1500 cells.
    hot = []
    used_roads = set()
    for v in obs["vehicles"]:
        x, y = int(v["x"]), int(v["y"])
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            hot.append((x, y, 2 + float(v.get("waiting", 0))))
            # Evidence of current road use, including queued/stopped traffic.
            # At-home/parked cars and missing stage data do not qualify.
            if (v.get("stage") not in (None, "Home", "Parking")
                    and obs["infrastructure"][_index((x, y))]):
                used_roads.add((x, y))
    for shop in shops[:MAX_DESTINATIONS]:
        x, y = _cell(shop["entrance"])
        hot.append((x, y, 1 + shop["demand"] + shop["reserved"]))
    hot.sort(key=lambda item: -item[2])
    inspected = set()
    for x, y, urgency in hot[:20]:
        for dx, dy in ((0, 0), *DIRS):
            cell = (x + dx, y + dy)
            if cell in inspected or not _playable(cell, obs):
                continue
            inspected.add(cell)
            idx = _index(cell)
            tile = obs["infrastructure"][idx]
            if obs["pendingRemovals"][idx] or cell in occupied:
                continue
            if tile == 0 and obs["terrain"][idx] in (0, 1):
                tool = "Bridge" if obs["terrain"][idx] == 1 else "Road"
                stock = obs["inventory"][1 if tool == "Bridge" else 0]
                if stock > 0 and (tool != "Bridge" or obs["inventory"][0] > 0):
                    result.append(Candidate({"command": "build", "tool": tool, "x": cell[0], "y": cell[1]},
                                            f"build {tool} {cell}", _features(4, cell, urgency=urgency, stock=stock, tool=tool), urgency - 2))
            elif tile:
                if (tile == 1 and cell not in motorway_endpoints and obs["inventory"][3] > 0
                        and obs["connections"][idx].bit_count() >= 3):
                    result.append(Candidate({"command": "build", "tool": "TrafficLight", "x": cell[0], "y": cell[1]},
                                            f"light {cell}", _features(4, cell, urgency=urgency, tool="TrafficLight"), urgency))
                ring = [(cell[0] + ddx, cell[1] + ddy) for ddx, ddy in DIRS[::2]]
                ring_ok = all(_playable(c, obs) and c not in occupied and
                              obs["terrain"][_index(c)] == 0 and not obs["pendingRemovals"][_index(c)]
                              and obs["infrastructure"][_index(c)] != 4 and c not in motorway_endpoints for c in ring)
                if tile == 1 and cell not in motorway_endpoints and obs["inventory"][4] > 0 and ring_ok:
                    result.append(Candidate({"command": "build", "tool": "Roundabout", "x": cell[0], "y": cell[1]},
                                            f"roundabout {cell}", _features(4, cell, urgency=urgency, tool="Roundabout"), urgency - 1))
                if obs["connections"][idx].bit_count() <= 1:
                    result.append(Candidate({"command": "build", "tool": "Remove", "x": cell[0], "y": cell[1]},
                                            f"remove {cell}", _features(4, cell, urgency=urgency, tool="Remove"), urgency - 8))
                if cell in roundabout_centers:
                    continue
                for ddx, ddy in DIRS:
                    other = (cell[0] + ddx, cell[1] + ddy)
                    if not _playable(other, obs) or other in roundabout_centers:
                        continue
                    oi = _index(other)
                    if obs["infrastructure"][oi] and not obs["pendingRemovals"][oi] and not (obs["connections"][idx] & (1 << DIRS.index((ddx, ddy)))):
                        if ddx and ddy:
                            cross_a, cross_b = (cell[0], other[1]), (other[0], cell[1])
                            cross_direction = DIRS.index((cross_b[0] - cross_a[0], cross_b[1] - cross_a[1]))
                            if obs["connections"][_index(cross_a)] & (1 << cross_direction):
                                continue
                        usage_bonus = 2 if cell in used_roads or other in used_roads else 0
                        result.append(Candidate({"command": "connect", "x": cell[0], "y": cell[1], "toX": other[0], "toY": other[1]},
                                                f"connect {cell} {other}", _features(5, cell, other, urgency), urgency + usage_bonus))
    for house in houses[:12]:
        start = _cell(house["cell"])
        old_delta=DIRS[house["drivewayDirection"]]
        old_outside=(start[0]+old_delta[0],start[1]+old_delta[1])
        blocked=(not _playable(old_outside,obs) or old_outside in occupied or
                 obs["terrain"][_index(old_outside)]!=0 or obs["pendingRemovals"][_index(old_outside)]
                 or old_outside in roundabout_centers)
        compatible=[shop for shop in shops if shop["color"]==house["color"]]
        targets=[_cell(entry) for shop in compatible for entry in (shop["entrances"] or [shop["entrance"]])]
        serves=any(_connected(start,target,obs["connections"],context) for target in targets)
        for direction, (dx, dy) in enumerate(DIRS):
            if direction == house["drivewayDirection"]:
                continue
            outside = (start[0] + dx, start[1] + dy)
            if (_playable(outside, obs) and outside not in occupied and
                    obs["terrain"][_index(outside)] == 0 and not obs["pendingRemovals"][_index(outside)]
                    and outside not in roundabout_centers):
                traversable=bool(obs["infrastructure"][_index(outside)]) or outside in motorway_endpoints
                adds_service=traversable and not serves and any(_connected(outside,target,obs["connections"],context) for target in targets)
                old_wait=sum(v.get("waiting",0) for v in obs["vehicles"]
                             if (int(v["x"]),int(v["y"]))==old_outside)
                new_wait=sum(v.get("waiting",0) for v in obs["vehicles"]
                             if (int(v["x"]),int(v["y"]))==outside)
                relieves_queue=traversable and old_wait>5 and new_wait<old_wait/2
                if not (blocked or adds_service or relieves_queue):
                    continue
                result.append(Candidate({"command": "driveway", "id": house["id"], "x": start[0], "y": start[1],
                                         "toX": outside[0], "toY": outside[1]}, f"driveway {house['id']} {direction}",
                                        _features(6, start, outside, ident=house["id"]), 25 if adds_service else 5))
    for motorway in obs["motorways"]:
        if motorway["pendingRemoval"]:
            continue
        start, end = _cell(motorway["start"]), _cell(motorway["end"])
        result.append(Candidate({"command": "removeMotorway", "id": motorway["id"]},
                                f"remove motorway {motorway['id']}", _features(8, start, end, ident=motorway["id"]), -5))
        for dx, dy in DIRS[:4]:
            other = (end[0] + dx, end[1] + dy)
            if (_playable(other, obs) and other not in occupied and obs["terrain"][_index(other)] == 0
                    and not obs["pendingRemovals"][_index(other)] and other not in motorway_endpoints
                    and obs["infrastructure"][_index(other)] != 4
                    and max(abs(other[0] - start[0]), abs(other[1] - start[1])) >= 2):
                old_degree=obs["connections"][_index(end)].bit_count()
                new_degree=obs["connections"][_index(other)].bit_count()
                if obs["infrastructure"][_index(other)]!=1 or new_degree<=old_degree:
                    continue
                result.append(Candidate({"command": "editMotorway", "id": motorway["id"], "x": start[0], "y": start[1],
                                         "toX": other[0], "toY": other[1]}, f"edit motorway {motorway['id']} {other}",
                                        _features(7, start, other, ident=motorway["id"]), -2))
    ordered = sorted(result[1:], key=lambda c: (-c.priority, c.label, tuple(c.request.values())))
    # Reserve room for each available command family before filling by priority.
    selected, types = [], set()
    for item in ordered:
        command = item.request["command"]
        family = (command, item.request.get("tool", ""))
        if family not in types and len(selected) < limit - 1:
            selected.append(item); types.add(family)
    for item in ordered:
        if len(selected) >= limit - 1:
            break
        if item not in selected:
            selected.append(item)
    result = result[:1] + selected
    return result


def candidate_matrix(items: list[Candidate], limit: int = MAX_CANDIDATES) -> tuple[np.ndarray, np.ndarray]:
    if len(items) > limit:
        raise ValueError("Too many candidates")
    values = np.zeros((limit, ACTION_WIDTH), dtype=np.float32)
    mask = np.zeros(limit, dtype=np.bool_)
    for i, candidate in enumerate(items):
        values[i, :-1] = candidate.features
        values[i, -1] = candidate.priority / 100
        mask[i] = True
    return values, mask
