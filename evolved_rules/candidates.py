"""Candidate road routes from a house to its shops, and their split into draw strokes.

One A* routine runs with three cost models / target sets (attach, direct, separated). It follows the
rules `draw` enforces (PLAN.md section 3.3; TrafficWorld.cs DrawRoad -> Build -> Connect) so that the
strokes from `split_strokes` reproduce the planned cells and links exactly (PLAN.md section 3.4).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass

from .state import DIRS, Building, Cell, CityState, _in_grid

KIND_ORDER = {"attach": 0, "direct": 1, "separated": 2, "clean": 3}
MAX_CANDIDATES = 3  # of the Phase 1 kinds; a clean route (gp-3, opt-in) is offered on top of these

# gp-3 "clean" routes (EXPERIMENTS.md): the separated cost model plus heavy charges for junction links, above all
# within NEAR_SHOP_RADIUS of a shop's doorstep, and never ending inside DOORSTEP_RADIUS of a doorstep unless that
# doorstep has at most one link (so ending there makes no junction).
NEAR_SHOP_RADIUS = 3
DOORSTEP_RADIUS = 1
CLEAN_JUNCTION_PENALTY = 2.0  # any junction link (cf. JUNCTION_PENALTY 0.5 for new junctions only)
CLEAN_NEAR_SHOP_PENALTY = 6.0  # extra for a junction link near a doorstep

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
    near_shop_junctions: int = 0  # path cells near a doorstep that gain a link and end with >= 3 (gp-3 input)
    ends_near_shop: bool = False  # the route ends within DOORSTEP_RADIUS of a shop's doorstep (gp-3 input)


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


def _junction_link(state: CityState, c: Cell, neighbours: tuple[Cell, ...]) -> bool:
    """True if existing road cell c gains a link from its path neighbours and ends with >= 3 links.

    Wider than _becomes_junction: adding a road to a cell that already is a junction counts too. That is how
    shop doorsteps pile up 3-4 links (gp-2 autopsy, EXPERIMENTS.md), and every link there slows the cars of
    the shop.
    """
    if not _is_road(state, c):
        return False
    mask = int(state.conn[c[1], c[0]])
    new = mask
    for nb in neighbours:
        new |= 1 << _direction(c, nb)
    return new != mask and _popcount(new) >= 3


def link_degree(state: CityState, c: Cell) -> int:
    """Live links of cell c: links to in-grid neighbours that are not pending removal (0 outside the grid or for
    a pending cell). A tile waiting for its committed cars keeps its link bits (TrafficWorld.cs:55-57) but no new
    route uses it, so counting it would make a doorstep that is already being thinned look as crowded as before."""
    if not _in_grid(c) or int(state.pending[c[1], c[0]]) == 1:
        return 0
    x, y = c
    mask = int(state.conn[y, x])
    return sum(1 for d, (dx, dy) in enumerate(DIRS)
               if (mask >> d) & 1 and _in_grid((x + dx, y + dy)) and int(state.pending[y + dy, x + dx]) != 1)


def doorsteps(state: CityState) -> tuple[Cell, ...]:
    """The outside cell of every shop entrance (the cell every car of that shop passes), in shop-id order."""
    return tuple(o for s in state.shops() for o in s.outside if _in_grid(o))


def near_cells(centres: tuple[Cell, ...], radius: int) -> frozenset[Cell]:
    """Grid cells within Chebyshev `radius` of any centre."""
    out = set()
    for cx, cy in centres:
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if _in_grid((x, y)):
                    out.add((x, y))
    return frozenset(out)


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
    clean: bool = False,
    near_shop: frozenset[Cell] = frozenset(),
) -> tuple[tuple[Cell, ...], int] | None:
    """Cheapest path from the house cell to any target. Returns (path, spans_used) or None.

    clean (gp-3): junction links (_junction_link) cost CLEAN_JUNCTION_PENALTY, plus CLEAN_NEAR_SHOP_PENALTY in
    `near_shop`, instead of the plain new-junction term. With clean False the costs are exactly Phase 1's.
    """
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
            if clean:
                if prev is not None and _junction_link(state, u, (prev, n)):
                    cost += CLEAN_JUNCTION_PENALTY + (CLEAN_NEAR_SHOP_PENALTY if u in near_shop else 0.0)
                if n in targets and _junction_link(state, n, (u,)):
                    cost += CLEAN_JUNCTION_PENALTY + (CLEAN_NEAR_SHOP_PENALTY if n in near_shop else 0.0)
            else:
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


def _near_shop_junctions(state: CityState, path: tuple[Cell, ...], near_shop: frozenset[Cell]) -> int:
    return sum(
        1 for i, c in enumerate(path)
        if c in near_shop and _junction_link(state, c, tuple(path[j] for j in (i - 1, i + 1) if 0 <= j < len(path)))
    )


def route_candidates(
    state: CityState,
    house: Building,
    shops: tuple[Building, ...],
    planned: frozenset[Cell] = frozenset(),
    *,
    planned_links: frozenset[Link] = frozenset(),
    clean: bool = False,
) -> list[RouteCandidate]:
    """Up to 3 routes from `house` to `shops`, plus with `clean` (gp-3) one clean route if it is new.

    `planned` holds cells of routes already chosen in this decision (treated as road); `planned_links`
    holds their steps (see path_links), so that no diagonal crosses a planned diagonal.

    A clean route uses the separated cost model with _astar's clean junction charges, and its targets leave
    out every cell within DOORSTEP_RADIUS of any shop's doorstep, except a target shop's own doorstep that
    has at most one link (ending there makes no junction). It is appended after the (sorted, capped) Phase 1
    candidates when its path differs from theirs, so with clean False the result is exactly Phase 1's.
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
    steps = doorsteps(state)
    near_shop = near_cells(steps, NEAR_SHOP_RADIUS)

    def make(kind: str, found) -> RouteCandidate | None:
        path, spans = found
        tiles = sum(1 for c in path[1:] if not _is_road(state, c) and c not in planned)
        if tiles > road_stock:
            return None
        strokes = split_strokes(path)
        return RouteCandidate(
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
            near_shop_junctions=_near_shop_junctions(state, path, near_shop),
            ends_near_shop=any(max(abs(path[-1][0] - d[0]), abs(path[-1][1] - d[1])) <= DOORSTEP_RADIUS
                               for d in steps),
        )

    out: list[RouteCandidate] = []
    seen: set[tuple[Cell, ...]] = set()
    reachable = False
    for kind in ("attach", "direct", "separated"):  # KIND_ORDER: dedup keeps the lowest kind
        found = _astar(
            state, house, direct_targets if kind == "direct" else attach_targets, planned, planned_links, served,
            separated=kind == "separated",
        )
        if found is None:
            if kind == "attach":
                break  # same edges, and the other target sets are subsets: nothing else is reachable
            continue
        reachable = True
        if found[0] in seen:
            continue
        seen.add(found[0])
        cand = make(kind, found)
        if cand is not None:
            out.append(cand)
    out.sort(key=lambda c: (c.tiles_needed, len(c.path), KIND_ORDER[c.kind]))
    out = out[:MAX_CANDIDATES]
    if clean and reachable:
        zone = near_cells(steps, DOORSTEP_RADIUS)
        own_steps = {o for s in shops for o in s.outside}
        targets = frozenset(c for c in attach_targets
                            if c not in zone or (c in own_steps and link_degree(state, c) <= 1))
        found = _astar(state, house, targets, planned, planned_links, served, separated=True, clean=True,
                       near_shop=near_shop)
        if found is not None and found[0] not in seen:
            cand = make("clean", found)
            if cand is not None:
                out.append(cand)
    return out


# --- Coverage targets (Phase 2, decision P2-6) ---------------------------------------------------------------

COVERAGE_TARGET_CAP = 24  # targets per coverage_targets call; each costs up to three A* searches


def _house_components(state: CityState) -> dict[int, frozenset[Cell]]:
    """House id -> its road component. Houses in one component share it: links are undirected (the simulator
    links both ends, TrafficWorld.Link), so component(b) == component(a) for every b in component(a)."""
    by_cell: dict[Cell, frozenset[Cell]] = {}
    out: dict[int, frozenset[Cell]] = {}
    for h in state.houses():
        comp = by_cell.get(h.cell)
        if comp is None:
            comp = state.component(h.cell)
            for c in comp:
                by_cell.setdefault(c, comp)
        out[h.id] = comp
    return out


def house_reaches(state: CityState, house_id: int, shops: tuple[Building, ...]) -> bool:
    """True if the house reaches the access cells of at least one of `shops` over roads (False for no shops or
    an unknown house). This is the coverage success rule: a route for (house, shops) worked when it holds."""
    house = next((b for b in state.buildings if b.id == house_id), None)
    if house is None:
        return False
    comp = state.component(house.cell)
    return any(a in comp for s in shops for a in s.access)


def coverage_targets(state: CityState) -> list[tuple[Building, tuple[Building, ...]]]:
    """Phase 1 targets, then every (house, same-colour shop) pair where the house does not reach that shop.

    The Phase 1 entries (unserved_targets) come first, in their order. Then, for each shop in id order, each
    same-colour house in id order (state.buildings is id-sorted) that does not reach the shop's access cells
    becomes the target (house, (shop,)), unless that pair is already covered by an earlier entry. This lets a
    policy add car supply to a starving shop from a house that already serves another shop. The list is cut
    to its first COVERAGE_TARGET_CAP entries (silently: the next decision re-plans from the new state).
    Used only by policies with `coverage = True`; Phase 1 policies keep unserved_targets.
    """
    out = unserved_targets(state)
    if len(out) >= COVERAGE_TARGET_CAP:
        return out[:COVERAGE_TARGET_CAP]
    listed = {(h.id, s.id) for h, shops in out for s in shops}
    houses = state.houses()
    comps: dict[int, frozenset[Cell]] | None = None
    for s in state.shops():
        for h in houses:
            if h.color != s.color or (h.id, s.id) in listed:
                continue
            if comps is None:
                comps = _house_components(state)
            if any(a in comps[h.id] for a in s.access):
                continue
            listed.add((h.id, s.id))
            out.append((h, (s,)))
            if len(out) == COVERAGE_TARGET_CAP:
                return out
    return out


# --- Removal candidates (gp-3) -------------------------------------------------------------------------------

@dataclass(frozen=True)
class RemovalCandidate:
    """A road tile whose removal would thin out the junctions at a shop's doorstep (gp-3).

    cell is the tile; shop_id the shop with the nearest doorstep (ties: lowest id); dist its Chebyshev distance
    to that doorstep; degree the tile's links; links_doorstep whether the tile is linked to a doorstep that has
    >= 3 links (removing it takes one away); doorstep_degree the links of that nearest doorstep.
    """

    cell: Cell
    shop_id: int
    dist: int
    degree: int
    links_doorstep: bool
    doorstep_degree: int


def _labels_without(state: CityState, starts: list[Cell], blocked: Cell) -> dict[Cell, int]:
    """Component label of every cell reached from `starts` over links, never entering `blocked` or a cell
    pending removal (like CityState.component). Starts are visited in the given order."""
    label: dict[Cell, int] = {}
    lab = -1
    for start in starts:
        if start in label or start == blocked:
            continue
        lab += 1
        label[start] = lab
        stack = [start]
        while stack:
            x, y = stack.pop()
            mask = int(state.conn[y, x])
            for d, (dx, dy) in enumerate(DIRS):
                if not (mask >> d) & 1:
                    continue
                n = (x + dx, y + dy)
                if n == blocked or n in label or not _in_grid(n) or int(state.pending[n[1], n[0]]) == 1:
                    continue
                label[n] = lab
                stack.append(n)
    return label


def _pairs_to_keep(state: CityState) -> list[tuple[Building, Building]]:
    """Every (house, same-colour shop) pair whose house reaches that shop now."""
    now = _house_components(state)
    return [(h, s) for h in state.houses() for s in state.shops()
            if s.color == h.color and any(a in now[h.id] for a in s.access)]


def keeps_connections(state: CityState, cell: Cell, need: list | None = None) -> bool:
    """True if removing road tile `cell` leaves every house reaching every same-colour shop it reaches now.

    need: _pairs_to_keep(state), passed in when many cells of one state are checked."""
    need = _pairs_to_keep(state) if need is None else need
    if not need:
        return True
    label = _labels_without(state, [h.cell for h in state.houses()], cell)
    return all(
        h.cell in label and any(label.get(a) == label[h.cell] for a in s.access)
        for h, s in need
    )


def removal_candidates(state: CityState) -> list[RemovalCandidate]:
    """Plain road tiles near a shop doorstep that feed a junction there, and whose removal keeps every
    connection (keeps_connections). In (y, x) order.

    A tile qualifies if it lies within NEAR_SHOP_RADIUS of a doorstep, is not itself a doorstep, carries a plain
    road (infra 1: not a bridge, roundabout or traffic light) and is not pending removal, and either is a
    junction (>= 3 links) or is linked to a doorstep with >= 3 links.
    """
    shops = state.shops()
    steps = [(o, s) for s in shops for o in s.outside if _in_grid(o)]
    if not steps:
        return []
    step_cells = {o for o, _ in steps}
    need = None  # the pairs to keep, computed once, on the first cell that gets that far
    out: list[RemovalCandidate] = []
    for c in sorted(near_cells(tuple(step_cells), NEAR_SHOP_RADIUS), key=lambda c: (c[1], c[0])):
        x, y = c
        if c in step_cells or int(state.infra[y, x]) != 1 or int(state.pending[y, x]) == 1 \
                or int(state.kinds[y, x]) != 0:
            continue
        degree = link_degree(state, c)
        mask = int(state.conn[y, x])
        feeds = any(((mask >> d) & 1) and (x + dx, y + dy) in step_cells
                    and link_degree(state, (x + dx, y + dy)) >= 3 for d, (dx, dy) in enumerate(DIRS))
        if degree < 3 and not feeds:
            continue
        o, s = min(steps, key=lambda p: (max(abs(p[0][0] - x), abs(p[0][1] - y)), p[1].id))
        if need is None:
            need = _pairs_to_keep(state)
        if not keeps_connections(state, c, need):
            continue
        out.append(RemovalCandidate(cell=c, shop_id=s.id, dist=max(abs(o[0] - x), abs(o[1] - y)), degree=degree,
                                    links_doorstep=feeds, doorstep_degree=link_degree(state, o)))
    return out
