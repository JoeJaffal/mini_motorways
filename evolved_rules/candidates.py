"""Candidate road routes from a house to its shops, and their split into draw strokes.

One A* routine runs with three cost models / target sets (attach, direct, separated). It follows the
rules `draw` enforces (PLAN.md section 3.3; TrafficWorld.cs DrawRoad -> Build -> Connect) so that the
strokes from `split_strokes` reproduce the planned cells and links exactly (PLAN.md section 3.4).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass

from .state import DIRS, Building, Cell, CityState, _in_grid

KIND_ORDER = {"attach": 0, "direct": 1, "separated": 2}
MAX_CANDIDATES = 3

DIAG_BASE = 1.414
ROAD_FACTOR = 0.15  # existing (or planned) road costs this fraction of the base step
STEP_EXTRA = 0.05
JUNCTION_PENALTY = 0.5  # the path turns an existing road cell into a junction of degree >= 3
FOREIGN_PENALTY = 3.0  # separated mode: a cell in a network that serves any other colour

_MIN_ORTH = 1.0 * ROAD_FACTOR + STEP_EXTRA
_MIN_DIAG = DIAG_BASE * ROAD_FACTOR + STEP_EXTRA
_ORTHO = tuple(d for d in DIRS if d[0] == 0 or d[1] == 0)

Link = tuple[Cell, Cell]


@dataclass(frozen=True)
class Stroke:
    x: int
    y: int
    to_x: int
    to_y: int

    def request(self) -> dict:
        return {"command": "draw", "x": self.x, "y": self.y, "toX": self.to_x, "toY": self.to_y}


@dataclass(frozen=True)
class RouteCandidate:
    kind: str
    house_id: int
    shop_ids: tuple[int, ...]
    path: tuple[Cell, ...]
    tiles_needed: int
    bridges_needed: int
    turns: int
    new_junctions: int
    shared_cells: int
    strokes: tuple[Stroke, ...]


def _direction(a: Cell, b: Cell) -> int:
    return DIRS.index((b[0] - a[0], b[1] - a[1]))


def _link_key(a: Cell, b: Cell) -> Link:
    return (a, b) if a <= b else (b, a)


def path_links(path: tuple[Cell, ...]) -> frozenset[Link]:
    """The steps of a path as order-independent (sorted) cell pairs, for route_candidates(planned_links=...)."""
    return frozenset(_link_key(a, b) for a, b in zip(path, path[1:]))


def split_strokes(path: tuple[Cell, ...]) -> tuple[Stroke, ...]:
    """One stroke per maximal run of an identical step direction (8-direction straight lines)."""
    if len(path) < 2:
        return ()
    strokes: list[Stroke] = []
    start, run_dir = path[0], _direction(path[0], path[1])
    for i in range(1, len(path) - 1):
        d = _direction(path[i], path[i + 1])
        if d != run_dir:
            strokes.append(Stroke(start[0], start[1], path[i][0], path[i][1]))
            start, run_dir = path[i], d
    strokes.append(Stroke(start[0], start[1], path[-1][0], path[-1][1]))
    return tuple(strokes)


def _is_road(state: CityState, c: Cell) -> bool:
    """Any existing road tile (infra != 0: road, bridge, roundabout, traffic light), not pending removal.

    Read infra directly: CityState.road_cell covers only infra 1/2. Roundabout cells (3) are never
    enterable, so on a path this means road, bridge or traffic light.
    """
    return _in_grid(c) and int(state.infra[c[1], c[0]]) != 0 and int(state.pending[c[1], c[0]]) != 1


def _popcount(mask: int) -> int:
    return bin(mask).count("1")


def _becomes_junction(state: CityState, c: Cell, neighbours: tuple[Cell, ...]) -> bool:
    """True if existing road cell c has < 3 links and reaches >= 3 once linked to its path neighbours."""
    if not _is_road(state, c):
        return False
    mask = int(state.conn[c[1], c[0]])
    if _popcount(mask) >= 3:
        return False
    for nb in neighbours:
        mask |= 1 << _direction(c, nb)
    return _popcount(mask) >= 3


def _water(state: CityState, c: Cell) -> bool:
    return _in_grid(c) and int(state.terrain[c[1], c[0]]) == 1


def _enterable(state: CityState, c: Cell) -> bool:
    if not _in_grid(c) or not state.playable(c):
        return False
    x, y = c
    return (
        int(state.terrain[y, x]) != 2
        and int(state.kinds[y, x]) == 0
        and int(state.pending[y, x]) == 0
        and int(state.infra[y, x]) != 3
    )


def _served_colours(state: CityState) -> dict[Cell, frozenset[int]]:
    """Cell -> colours of the shops whose access cells lie in that cell's road component."""
    acc: dict[Cell, set[int]] = {}
    for s in state.shops():
        for a in s.access:
            for c in state.component(a):
                acc.setdefault(c, set()).add(s.color)
    return {c: frozenset(v) for c, v in acc.items()}


def _foreign(served: dict[Cell, frozenset[int]], c: Cell, color: int) -> bool:
    """c lies in a network serving some colour other than `color` (whether or not it also serves `color`)."""
    return any(col != color for col in served.get(c, ()))


def unserved_targets(state: CityState) -> list[tuple[Building, tuple[Building, ...]]]:
    houses, shops = state.houses(), state.shops()
    out: list[tuple[Building, tuple[Building, ...]]] = []
    for h in houses:
        same = tuple(s for s in shops if s.color == h.color)
        if same and not state.house_connected(h):
            out.append((h, same))
    listed = {h.id for h, _ in out}  # each house appears at most once across all entries
    for s in shops:
        same_houses = [h for h in houses if h.color == s.color]
        if not same_houses or state.shop_served(s):
            continue
        ax, ay = s.access[0]
        nearest = min(same_houses, key=lambda h: (abs(h.cell[0] - ax) + abs(h.cell[1] - ay), h.id))
        if nearest.id not in listed:
            listed.add(nearest.id)
            out.append((nearest, (s,)))
    return out


def _astar(
    state: CityState,
    house: Building,
    targets: frozenset[Cell],
    planned: frozenset[Cell],
    planned_links: frozenset[Link],
    served: dict[Cell, frozenset[int]],
    separated: bool,
) -> tuple[tuple[Cell, ...], int] | None:
    """Cheapest path from the house cell to any target. Returns (path, spans_used) or None."""
    if not targets:
        return None
    max_spans = state.inventory[1] if len(state.inventory) > 1 else 0
    target_list = sorted(targets)
    h_cache: dict[Cell, float] = {}

    def heuristic(c: Cell) -> float:
        v = h_cache.get(c)
        if v is None:
            v = min(
                _MIN_ORTH * (max(dx, dy) - min(dx, dy)) + _MIN_DIAG * min(dx, dy)
                for dx, dy in ((abs(t[0] - c[0]), abs(t[1] - c[1])) for t in target_list)
            )
            h_cache[c] = v
        return v

    def bridge_at(c: Cell) -> bool:
        # An existing bridge tile, or a planned water cell (it will be a bridge before this route is drawn).
        return _in_grid(c) and (int(state.infra[c[1], c[0]]) == 2 or (c in planned and _water(state, c)))

    start = house.cell
    linked = int(state.conn[start[1], start[0]]) != 0
    start_key = (start[0], start[1], 0)
    best_g: dict[tuple[int, int, int], float] = {start_key: 0.0}
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None] = {start_key: None}
    closed: set[tuple[int, int, int]] = set()
    heap = [(heuristic(start), 0.0, start[1], start[0], 0)]

    while heap:
        _, g, y, x, spans = heapq.heappop(heap)
        key = (x, y, spans)
        if key in closed:
            continue
        closed.add(key)
        u = (x, y)
        if u != start and u in targets:
            path: list[Cell] = []
            k: tuple[int, int, int] | None = key
            while k is not None:
                path.append((k[0], k[1]))
                k = parent[k]
            return tuple(reversed(path)), spans
        u_water = _water(state, u)
        pk = parent[key]
        prev = (pk[0], pk[1]) if pk is not None else None
        for dx, dy in DIRS:
            n = (x + dx, y + dy)
            if u == start and linked and n != house.outside[0]:
                continue  # a linked house keeps its driveway
            if not _enterable(state, n):
                continue
            n_water = _water(state, n)
            if u == start and n_water:
                continue  # SetHouseDriveway rejects a driveway onto water
            diagonal = dx != 0 and dy != 0
            if diagonal:
                if u_water or n_water:
                    continue
                a, b = (n[0], y), (x, n[1])  # the other diagonal of this 2x2 block, existing or planned
                if (int(state.conn[a[1], a[0]]) >> _direction(a, b)) & 1 or _link_key(a, b) in planned_links:
                    continue
            n_spans = spans
            if n_water and not (
                bridge_at(n) or u_water or any(bridge_at((n[0] + ox, n[1] + oy)) for ox, oy in _ORTHO)
            ):
                n_spans = spans + 1  # starts a new bridge span: one bridge item
                if n_spans > max_spans:
                    continue
            n_key = (n[0], n[1], n_spans)
            if n_key in closed:
                continue
            road_n = _is_road(state, n)
            cost = (DIAG_BASE if diagonal else 1.0) * (ROAD_FACTOR if road_n or n in planned else 1.0) + STEP_EXTRA
            # Junction term, an approximation that keeps the state at (cell, spans): u is charged on its
            # outgoing edge using its fixed parent (u is closed, so its in-link is known), and a target n
            # (the path ends there) is charged on its incoming edge. Each path cell is thus charged at most
            # once, exactly as new_junctions counts it, but a cheaper junction-free predecessor of u that
            # was not u's best-g parent is never considered.
            if prev is not None and _becomes_junction(state, u, (prev, n)):
                cost += JUNCTION_PENALTY
            if n in targets and _becomes_junction(state, n, (u,)):
                cost += JUNCTION_PENALTY
            if separated and _foreign(served, n, house.color):
                cost += FOREIGN_PENALTY
            ng = g + cost
            if ng < best_g.get(n_key, float("inf")):
                best_g[n_key] = ng
                parent[n_key] = key
                heapq.heappush(heap, (ng + heuristic(n), ng, n[1], n[0], n_spans))
    return None


def _new_junctions(state: CityState, path: tuple[Cell, ...]) -> int:
    return sum(
        1 for i, c in enumerate(path)
        if _becomes_junction(state, c, tuple(path[j] for j in (i - 1, i + 1) if 0 <= j < len(path)))
    )


def route_candidates(
    state: CityState,
    house: Building,
    shops: tuple[Building, ...],
    planned: frozenset[Cell] = frozenset(),
    *,
    planned_links: frozenset[Link] = frozenset(),
) -> list[RouteCandidate]:
    """Up to 3 routes from `house` to `shops`.

    `planned` holds cells of routes already chosen in this decision (treated as road); `planned_links`
    holds their steps (see path_links), so that no diagonal crosses a planned diagonal.
    """
    shops = tuple(shops)
    served = _served_colours(state)
    road_stock = state.inventory[0] if len(state.inventory) > 0 else 0
    # Target cell -> ids of the given shops a route ending there connects the house to.
    reaches: dict[Cell, set[int]] = {}
    for s in shops:
        for o in s.outside:
            reaches.setdefault(o, set()).add(s.id)
    direct_targets = frozenset(reaches)
    for s in shops:
        if s.color != house.color:
            continue
        for a in s.access:
            for c in state.component(a):
                if _is_road(state, c):
                    reaches.setdefault(c, set()).add(s.id)
    attach_targets = frozenset(reaches)

    out: list[RouteCandidate] = []
    seen: set[tuple[Cell, ...]] = set()
    for kind in ("attach", "direct", "separated"):  # KIND_ORDER: dedup keeps the lowest kind
        found = _astar(
            state, house, direct_targets if kind == "direct" else attach_targets, planned, planned_links, served,
            separated=kind == "separated",
        )
        if found is None:
            if kind == "attach":
                break  # same edges, and the other target sets are subsets: nothing else is reachable
            continue
        path, spans = found
        if path in seen:
            continue
        seen.add(path)
        tiles = sum(1 for c in path[1:] if not _is_road(state, c) and c not in planned)
        if tiles > road_stock:
            continue
        strokes = split_strokes(path)
        out.append(RouteCandidate(
            kind=kind,
            house_id=house.id,
            shop_ids=tuple(sorted(reaches.get(path[-1], ()))),
            path=path,
            tiles_needed=tiles,
            bridges_needed=spans,
            turns=max(0, len(strokes) - 1),
            new_junctions=_new_junctions(state, path),
            shared_cells=sum(1 for c in path if _foreign(served, c, house.color)),
            strokes=strokes,
        ))
    out.sort(key=lambda c: (c.tiles_needed, len(c.path), KIND_ORDER[c.kind]))
    return out[:MAX_CANDIDATES]
