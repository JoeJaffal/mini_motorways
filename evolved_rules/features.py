"""Feature dicts the rules read: one per route candidate, one global, one per upgrade offer (PLAN.md section 4).

Values are raw floats (not normalised; scaling is the GP terminal layer's job). Phase 1 keys and values are
frozen: Phase 2 only adds keys, after the Phase 1 ones, and never renames or changes those.

Phase 2 features need more than one observation (a demand-rate estimate, the number of offers taken) and
road-graph facts that are costly to recompute for every candidate. `GameMemory` holds both: one per game
(GameSession creates a fresh one on every reset), updated after every observation, so nothing is shared
between games. Everything is deterministic: buildings are visited in id order, heaps break ties on cells.
"""
from __future__ import annotations

import heapq
from collections import deque

import numpy as np

from .candidates import RouteCandidate
from .state import DIRS, Building, Cell, CityState, Offer, _in_grid

N_ITEM_TYPES = 6  # inventory: roads, bridges, motorways, traffic lights, roundabouts, unused

# --- Phase 2 constants (PLAN.md section 3.5 game facts) ------------------------------------------------------
DEMAND_WINDOW_S = 60.0  # DemandTracker sliding window
DEMAND_MIN_SPAN_S = 20.0  # floor on the observed span a young shop's rate is divided by
ORTHO_STEP_S = 2.0  # lane speed 0.5 tiles/s
DIAG_STEP_S = 2.83  # 2 * sqrt(2)
TURN_90_FACTOR = 1.5  # lane speed x 2/3 on a 90 degree turn
TURN_SHARP_FACTOR = 3.0  # lane speed x 1/3 on a sharper turn
JUNCTION_FACTOR = 2.0  # lane speed x 0.5 entering a junction of degree >= 3
CARS_PER_HOUSE = 2
TRIP_OVERHEAD_S = 11.0  # 3 s service + 8 s, the simulator's own feasibility overhead (CityDemand.cs:117-118)
OFFER_PERIOD_S = 140.0  # an offer is generated when time >= 140 x (offers granted + 1)


# --- Per-game memory -----------------------------------------------------------------------------------------

class DemandTracker:
    """Estimated pin rate per shop: positive increases of `demand` in a sliding window (plan section 9 default).

    `OriginalDemandInterval` is excluded from the observation (decision P2-8), so the rate is measured. A pickup
    and a new pin within one 20-tick step cancel out, so the estimate is a lower bound. A shop first seen with
    demand d counts d as an increase at that moment (shops start with no pins).

    The sum is divided by the span the shop has actually been watched, capped at the window: dividing by the
    full window would read a shop's first minute (and the game's) far too low (+2 pins at t = 10 is ~12/min,
    not 2/min). The span is floored at DEMAND_MIN_SPAN_S so one early pin does not read as a huge rate.
    """

    def __init__(self, window_s: float = DEMAND_WINDOW_S, min_span_s: float = DEMAND_MIN_SPAN_S) -> None:
        self.window_s, self.min_span_s = window_s, min_span_s
        self._last: dict[int, int] = {}  # shop id -> demand at the last update
        self._first_seen: dict[int, float] = {}  # shop id -> time of the first update that saw it
        self._events: dict[int, deque[tuple[float, int]]] = {}  # shop id -> (time, increase), oldest first
        self._now = 0.0  # time of the last update

    def update(self, state: CityState) -> None:
        """Record one observation. Call it after every observation, in game order."""
        t = state.time
        self._now = float(t)
        for s in state.shops():
            self._first_seen.setdefault(s.id, float(t))
            prev = self._last.get(s.id, 0)
            if s.demand > prev:
                self._events.setdefault(s.id, deque()).append((t, s.demand - prev))
            self._last[s.id] = s.demand
        cutoff = t - self.window_s
        for q in self._events.values():
            while q and q[0][0] <= cutoff:
                q.popleft()

    def rate(self, shop_id: int) -> float:
        """Pins per minute over the window ending at the last update (0.0 for an unseen shop)."""
        q = self._events.get(shop_id)
        if not q:
            return 0.0
        span = min(self.window_s, max(self.min_span_s, self._now - self._first_seen[shop_id]))
        return float(sum(n for _, n in q)) * 60.0 / span


class GameMemory:
    """What features need beyond the current observation, for one game.

    offers_taken counts accepted upgrade commands (GameSession increments it). The road-network analysis of
    the last network seen and the per-state analysis of the last state seen are cached here: most decisions
    see an unchanged network, and one decision scores many candidates on the same state.
    """

    def __init__(self) -> None:
        self.demand = DemandTracker()
        self.offers_taken = 0
        self._net_key: tuple | None = None
        self._net: _Network | None = None
        self._state: CityState | None = None
        self._analysis: _Analysis | None = None

    def observe(self, state: CityState) -> None:
        self.demand.update(state)

    def analysis(self, state: CityState) -> _Analysis:
        if self._state is not state:
            key = _network_key(state)
            if self._net is None or self._net_key != key:
                self._net, self._net_key = _Network(state), key
            self._analysis, self._state = _Analysis(state, self._net, self), state
        return self._analysis


# --- Road-network analysis (depends only on links, pending removals and buildings) ---------------------------

def _network_key(state: CityState) -> tuple:
    return (state.conn.tobytes(), state.pending.tobytes(),
            tuple((b.id, b.color, b.cell, b.access) for b in state.buildings))


def _popcount(mask: int) -> int:
    return bin(mask).count("1")


def _step_s(d: int) -> float:
    return DIAG_STEP_S if d % 2 == 1 else ORTHO_STEP_S


def _direction(a: Cell, b: Cell) -> int:
    return DIRS.index((b[0] - a[0], b[1] - a[1]))


class _Network:
    """Components reached from house cells, which shops each house reaches, and congestion-free costs.

    Components are those of CityState.component (link bits, pending cells skipped). One component is shared by
    every house cell in it: the simulator links both ends of every connection (TrafficWorld.Link), so the
    graph is undirected and component(a) == component(b) for any b in component(a).
    """

    def __init__(self, state: CityState) -> None:
        self.state = state
        self.label: dict[Cell, int] = {}
        self.components: list[frozenset[Cell]] = []
        for h in state.houses():  # id order: labels are deterministic
            if h.cell in self.label:
                continue
            comp = state.component(h.cell)
            for c in comp:
                self.label.setdefault(c, len(self.components))
            self.components.append(comp)
        self.shop_labels: dict[int, frozenset[int]] = {
            s.id: frozenset(self.label[a] for a in s.access if a in self.label) for s in state.shops()}
        self._shop_dist: dict[int, dict[Cell, float]] = {}
        self._colour_dist: dict[int, dict[Cell, float]] = {}

    def reaches(self, h: Building, s: Building) -> bool:
        """The house reaches the shop's access over roads (as CityState.house_connected, for one shop)."""
        return self.label.get(h.cell, -1) in self.shop_labels.get(s.id, frozenset())

    def shop_dist(self, s: Building) -> dict[Cell, float]:
        d = self._shop_dist.get(s.id)
        if d is None:
            d = self._shop_dist[s.id] = _cost_to(self.state, s.access)
        return d

    def colour_dist(self, color: int) -> dict[Cell, float]:
        d = self._colour_dist.get(color)
        if d is None:
            sources = [a for s in self.state.shops() if s.color == color for a in s.access]
            d = self._colour_dist[color] = _cost_to(self.state, sources)
        return d


def _cost_to(state: CityState, sources) -> dict[Cell, float]:
    """Cell -> congestion-free seconds to drive from that cell to the nearest source over existing roads.

    Reverse Dijkstra: the forward step u -> v costs the step time x JUNCTION_FACTOR if v has >= 3 links.
    Turns are ignored here (a state per cell, not per heading); route_cost charges them on planned paths.
    """
    dist: dict[Cell, float] = {}
    heap = [(0.0, c[1], c[0]) for c in sorted(set(sources)) if _in_grid(c)]
    heapq.heapify(heap)
    while heap:
        d, y, x = heapq.heappop(heap)
        if (x, y) in dist:
            continue
        dist[(x, y)] = d
        if int(state.pending[y, x]) == 1:
            continue  # as CityState.component: a pending cell is not expanded
        mask = int(state.conn[y, x])
        step_factor = JUNCTION_FACTOR if _popcount(mask) >= 3 else 1.0
        for k, (dx, dy) in enumerate(DIRS):
            if not (mask >> k) & 1:
                continue
            nx, ny = x + dx, y + dy
            if not _in_grid((nx, ny)) or (nx, ny) in dist or int(state.pending[ny, nx]) == 1:
                continue
            heapq.heappush(heap, (d + _step_s(k) * step_factor, ny, nx))
    return dist


def route_cost(state: CityState, path: tuple[Cell, ...], exit_cell: Cell | None = None) -> float:
    """Congestion-free seconds along a planned path (PLAN.md 3.5 lane speeds, approximately).

    Each step costs 2 s (orthogonal) or 2.83 s (diagonal), x1.5 when it leaves a 90 degree turn, x3 after a
    sharper one, and x2 when it enters a cell that will have >= 3 links once the path is built. exit_cell is
    a cell the draw also links the last cell to (a direct route's shop access cell): that link counts toward
    the last cell's degree. The step into exit_cell itself is not charged here.
    """
    n = len(path)
    if n < 2:
        return 0.0
    dirs = [_direction(path[i], path[i + 1]) for i in range(n - 1)]
    total = 0.0
    for i in range(n - 1):
        f = 1.0
        if i > 0:
            turn = abs(dirs[i] - dirs[i - 1]) % 8
            turn = min(turn, 8 - turn)
            if turn == 2:
                f *= TURN_90_FACTOR
            elif turn > 2:
                f *= TURN_SHARP_FACTOR
        v = path[i + 1]
        mask = int(state.conn[v[1], v[0]]) if _in_grid(v) else 0
        mask |= 1 << _direction(v, path[i])
        if i + 2 < n:
            mask |= 1 << _direction(v, path[i + 2])
        elif exit_cell is not None:
            mask |= 1 << _direction(v, exit_cell)
        if _popcount(mask) >= 3:
            f *= JUNCTION_FACTOR
        total += _step_s(dirs[i]) * f
    return total


# --- Per-state analysis --------------------------------------------------------------------------------------

class _Analysis:
    """Facts of one state that every candidate and the hold rule share (computed lazily, once)."""

    def __init__(self, state: CityState, net: _Network, memory: GameMemory) -> None:
        self.state, self.net, self.memory = state, net, memory
        self.by_id = {b.id: b for b in state.buildings}
        self.shops = state.shops()
        self.houses = state.houses()
        self._served: dict[int, bool] | None = None
        self._shop_houses: dict[int, int] | None = None
        self._margins: dict[int, float] | None = None

    def house_served(self, h: Building) -> bool:
        if self._served is None:
            self._served = {
                x.id: any(self.net.reaches(x, s) for s in self.shops if s.color == x.color) for x in self.houses}
        return self._served.get(h.id, False)

    def shop_houses(self, s: Building) -> int:
        if self._shop_houses is None:
            self._shop_houses = {
                y.id: sum(1 for h in self.houses if h.color == y.color and self.net.reaches(h, y))
                for y in self.shops}
        return self._shop_houses.get(s.id, 0)

    def margins(self) -> dict[int, float]:
        """Colour (with a shop, ascending) -> car-supply margin in trips per minute.

        Supply: each house of the colour that reaches one of its shops adds CARS_PER_HOUSE x 60 / round trip,
        round trip = 2 x one-way cost to its nearest same-colour shop + TRIP_OVERHEAD_S (so the 'estimated
        round trip' of the colour is the harmonic mean over its houses). Demand: the estimated pin rates of the
        colour's shops. Congestion is ignored, so this is an optimistic bound (PLAN.md section 4).
        """
        if self._margins is None:
            out: dict[int, float] = {}
            for color in sorted({s.color for s in self.shops}):
                dist = self.net.colour_dist(color)
                supply = 0.0
                for h in self.houses:
                    if h.color != color or not self.house_served(h):
                        continue
                    one_way = dist.get(h.cell)
                    if one_way is not None:
                        supply += CARS_PER_HOUSE * 60.0 / (2.0 * one_way + TRIP_OVERHEAD_S)
                demand = sum(self.memory.demand.rate(s.id) for s in self.shops if s.color == color)
                out[color] = supply - demand
            self._margins = out
        return self._margins


def _shop_route_cost(state: CityState, net: _Network, shop: Building, path: tuple[Cell, ...],
                     path_s: float) -> float | None:
    """Seconds from a path's first cell to the shop, or None if the path's end does not reach it.

    If the end already reaches the shop over existing roads: path_s plus that road cost. Otherwise, for a
    direct route ending on a shop's outside cell: the path re-costed with the link into the access cell
    counted at its end (it can make the end a junction), plus the one step into the access cell.
    """
    end = path[-1]
    d = net.shop_dist(shop).get(end)
    if d is not None:
        return path_s + d
    best = None
    for a, k in zip(shop.access, shop.access_dirs):
        if (a[0] + DIRS[k][0], a[1] + DIRS[k][1]) == end:
            c = route_cost(state, path, exit_cell=a) + _step_s(k)
            best = c if best is None else min(best, c)
    return best


def _analysis_of(state: CityState, memory: GameMemory | None) -> _Analysis:
    return (memory if memory is not None else GameMemory()).analysis(state)


# --- Feature dicts -------------------------------------------------------------------------------------------

def route_features(cand: RouteCandidate) -> dict[str, float]:
    """The Phase 1 candidate features (a function of the candidate alone). path_len counts steps (cells - 1)."""
    return {
        "tiles_needed": float(cand.tiles_needed),
        "bridges_needed": float(cand.bridges_needed),
        "path_len": float(max(0, len(cand.path) - 1)),
        "turns": float(cand.turns),
        "new_junctions": float(cand.new_junctions),
        "shared_cells": float(cand.shared_cells),
        "is_attach": 1.0 if cand.kind == "attach" else 0.0,
        "is_direct": 1.0 if cand.kind == "direct" else 0.0,
        "is_separated": 1.0 if cand.kind == "separated" else 0.0,
    }


def candidate_features(state: CityState, cand: RouteCandidate, memory: GameMemory | None = None) -> dict[str, float]:
    """Phase 1 route features, then the route's cost and its target shop (Phase 2).

    The target shop is the reached shop (cand.shop_ids) with the lowest house-to-shop cost, ties by lowest id:
    dispatch sends the idle car with the lowest route cost, so that is the shop the new link serves best.
    path_cost_s is that cost (planned path, then existing roads); with no reachable shop it is the path alone
    and the shop terms are 0.
    """
    a = _analysis_of(state, memory)
    f = route_features(cand)
    path_s = route_cost(state, cand.path)
    best: tuple[float, int] | None = None
    for sid in cand.shop_ids:
        shop = a.by_id.get(sid)
        if shop is None or not cand.path:
            continue
        cost = _shop_route_cost(state, a.net, shop, cand.path, path_s)
        if cost is not None and (best is None or (cost, sid) < best):
            best = (cost, sid)
    house = a.by_id.get(cand.house_id)
    f["path_cost_s"] = best[0] if best is not None else path_s
    f["house_served"] = 1.0 if house is not None and a.house_served(house) else 0.0
    if best is not None:
        s = a.by_id[best[1]]
        f["shop_demand"] = float(s.demand)
        f["shop_unassigned"] = float(s.demand - s.reserved)
        f["shop_capacity"] = float(s.capacity)
        f["shop_overcrowded"] = float(s.overcrowded_for)
        f["shop_rate"] = a.memory.demand.rate(s.id)
        f["shop_houses"] = float(a.shop_houses(s))
    else:
        for k in ("shop_demand", "shop_unassigned", "shop_capacity", "shop_overcrowded", "shop_rate",
                  "shop_houses"):
            f[k] = 0.0
    f["colour_margin"] = float(a.margins().get(house.color, 0.0)) if house is not None else 0.0
    return f


def _edge_distance(state: CityState) -> float:
    """Tiles between the building nearest the playable border and that border (0.0 with no buildings)."""
    x0, y0, x1, y1 = state.bounds
    ds = [min(b.cell[0] - x0, x1 - (b.cell[0] + b.width), b.cell[1] - y0, y1 - (b.cell[1] + b.height))
          for b in state.buildings]
    return float(max(0, min(ds))) if ds else 0.0


def disconnected_components(state: CityState, memory: GameMemory | None = None) -> int:
    """The simulator's disconnectedColorComponents (RoadNetwork.cs:237-257), computed from connections.

    Networks that each hold a house and a shop of one colour count as served; the result is their number
    minus 1, or 0 if fewer than 2 networks are served or they serve only one colour between them. A served
    network always holds a house cell, so the components reached from house cells are all that matter.
    """
    a = _analysis_of(state, memory)
    return _disconnected(a)


def _disconnected(a: _Analysis) -> int:
    served: list[set[int]] = []
    for i, comp in enumerate(a.net.components):
        homes = {h.color for h in a.houses if a.net.label.get(h.cell) == i}
        shops = {s.color for s in a.shops if i in a.net.shop_labels.get(s.id, ())}
        both = homes & shops
        if both:
            served.append(both)
    if len(served) < 2 or len(set().union(*served)) < 2:
        return 0
    return len(served) - 1


def global_features(state: CityState, memory: GameMemory | None = None) -> dict[str, float]:
    """unserved_houses: houses that have a shop of their colour but do not reach any of them."""
    shop_colours = {s.color for s in state.shops()}
    unserved = sum(1 for h in state.houses() if h.color in shop_colours and not state.house_connected(h))
    inv = state.inventory
    g = {
        "road_stock": float(inv[0] if len(inv) > 0 else 0),
        "bridge_stock": float(inv[1] if len(inv) > 1 else 0),
        "time": float(state.time),
        "unserved_houses": float(unserved),
    }
    a = _analysis_of(state, memory)
    margins = a.margins()
    g["pending_refunds"] = float(np.count_nonzero(state.pending == 1))
    g["next_offer_s"] = max(0.0, OFFER_PERIOD_S * (a.memory.offers_taken + 1) - float(state.time))
    g["disconnected_components"] = float(_disconnected(a))
    g["unserved_shops"] = float(sum(1 for s in a.shops if a.shop_houses(s) == 0))
    g["edge_distance"] = _edge_distance(state)
    g["worst_overcrowded"] = max((float(s.overcrowded_for) for s in a.shops), default=0.0)
    g["worst_margin"] = min(margins.values(), default=0.0)
    g["shops"] = float(len(a.shops))
    g["houses"] = float(len(a.houses))
    return g


def offer_features(offer: Offer, state: CityState | None = None) -> dict[str, float]:
    """Phase 1 offer features, then stock_of_type: the current stock of the offered item (0.0 without a state)."""
    f = {"offer_roads": float(offer.road_value), "amount": float(offer.amount)}
    for t in range(N_ITEM_TYPES):
        f[f"type_{t}"] = 1.0 if offer.type == t else 0.0
    inv = state.inventory if state is not None else ()
    f["stock_of_type"] = float(inv[offer.type]) if 0 <= offer.type < len(inv) else 0.0
    return f
