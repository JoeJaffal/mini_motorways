"""gp-7 evolvable planner, C4-min (plan 2026-11-14 section 3.1): cost head cell map, target head, v7 features.

Only texts with a `planner:` trailer (gp.Planner, moves=v7) reach this module; the v6 path never imports it.

Cost head. candidates.EvoCost with M[n] = w_car*cars_on[n] + w_stop*stopped_on[n] + w_qstop*gate*stopped_on[n],
gate = 1[worst_overcrowded > theta] (the cost template). cars_on counts driving cars per cell (the cell a car's
position falls in), stopped_on the stuck ones (features.is_stuck). The map is colour-neutral and rebuilt from
each state the route loop sees (a pass that executed a route sees a new state).

Target head. Over every (house, same-colour shop) pair, in shop-id then house-id order:
    t(h,s) = b_t + w_con*pair_connected + w_det*detour_ratio + w_dem*shop_demand/64 + w_over*shop_overcrowded/1024
             + w_ttmpl*(shop_overcrowded/1024)*detour_ratio            (the target template)
detour_ratio = current network path length (steps, from the house cell to the shop's access) / Chebyshev distance
to the nearest access cell, for connected pairs at the DETOUR_SHOPS shops with the highest overcrowded_for (then
demand, then lowest id); 0 otherwise. The picked pairs are the top M_eff (gp.Planner.m_eff) with t > 0 that were not
tried yet in this decision, by (-t, house id, shop id).
"""
from __future__ import annotations

import math
from collections import deque

from .candidates import EvoCost
from .features import GameMemory, is_driving, is_stuck
from .gp import Planner
from .state import DIRS, Cell, CityState, _in_grid

DETOUR_SHOPS = 6
PAIR_TERMS = ("pair_connected", "detour_ratio", "shop_demand", "shop_overcrowded")
PAIR_DIVISORS = (1.0, 1.0, 64.0, 1024.0)


def cell_maps(state: CityState) -> tuple[dict[Cell, int], dict[Cell, int]]:
    """(cars_on, stopped_on): driving cars and stuck cars per cell (cells without cars left out)."""
    cars: dict[Cell, int] = {}
    stopped: dict[Cell, int] = {}
    for c in state.cars:
        if not is_driving(c):
            continue
        cell = (math.floor(c.x), math.floor(c.y))
        if not _in_grid(cell):
            continue
        cars[cell] = cars.get(cell, 0) + 1
        if is_stuck(c):
            stopped[cell] = stopped.get(cell, 0) + 1
    return cars, stopped


def worst_overcrowded(state: CityState) -> float:
    return max((float(s.overcrowded_for) for s in state.shops()), default=0.0)


def evo_cost(state: CityState, planner: Planner) -> EvoCost:
    """The pass's EvoCost: the planner's cost weights plus the cell map M (None when every entry is 0)."""
    c = planner.c
    w_car, w_stop, w_q = c("w_car"), c("w_stop"), c("w_qstop")
    gate = 1.0 if worst_overcrowded(state) > planner.theta else 0.0
    M: dict[Cell, float] = {}
    if w_car or w_stop or (w_q and gate):
        cars, stopped = cell_maps(state)
        for cell, n in cars.items():
            s = stopped.get(cell, 0)
            v = w_car * n + w_stop * s + w_q * gate * s
            if v:
                M[cell] = v
    return EvoCost(w_paid=c("w_paid"), w_reuse=c("w_reuse"), w_step=c("w_step"), w_jn=c("w_jn"), w_jl=c("w_jl"),
                   w_ns=c("w_ns"), w_for=c("w_for"), M=M or None)


def shop_steps(state: CityState, memory: GameMemory, shop) -> dict[Cell, int]:
    """Cell -> steps over existing links to the shop's access cells (pending cells not expanded), cached per
    road network (GameMemory keeps the network object while links, pending removals and buildings are unchanged)."""
    net = memory.analysis(state).net
    cache = net.__dict__.setdefault("_steps7", {})
    d = cache.get(shop.id)
    if d is None:
        d = {}
        q = deque()
        for a in sorted(set(shop.access)):
            if _in_grid(a) and a not in d:
                d[a] = 0
                q.append(a)
        while q:
            x, y = q.popleft()
            if int(state.pending[y, x]) == 1:
                continue
            mask = int(state.conn[y, x])
            for k, (dx, dy) in enumerate(DIRS):
                if not (mask >> k) & 1:
                    continue
                n = (x + dx, y + dy)
                if n in d or not _in_grid(n) or int(state.pending[n[1], n[0]]) == 1:
                    continue
                d[n] = d[(x, y)] + 1
                q.append(n)
        cache[shop.id] = d
    return d


def detour_ratio(state: CityState, memory: GameMemory, house, shop) -> float:
    steps = shop_steps(state, memory, shop).get(house.cell)
    if steps is None:
        return 0.0
    cheb = min((max(abs(house.cell[0] - a[0]), abs(house.cell[1] - a[1])) for a in shop.access), default=0)
    return steps / cheb if cheb > 0 else 0.0


def pair_rows(state: CityState, memory: GameMemory, planner: Planner) -> list[tuple]:
    """Every (house, same-colour shop) pair as (t, house, shop, connected, terms), in shop-id then house-id order."""
    a = memory.analysis(state)
    shops = a.shops
    detour_ids = {s.id for s in sorted(shops, key=lambda s: (-s.overcrowded_for, -s.demand, s.id))[:DETOUR_SHOPS]}
    t = planner.t
    b_t, w_con, w_det, w_dem, w_over, w_tt = (t("b_t"), t("w_con"), t("w_det"), t("w_dem"), t("w_over"),
                                              t("w_ttmpl"))
    rows = []
    for s in shops:
        dem, over = s.demand / 64.0, s.overcrowded_for / 1024.0
        for h in a.houses:
            if h.color != s.color:
                continue
            connected = a.net.reaches(h, s)
            det = detour_ratio(state, memory, h, s) if connected and s.id in detour_ids else 0.0
            con = 1.0 if connected else 0.0
            score = b_t + w_con * con + w_det * det + w_dem * dem + w_over * over + w_tt * (over * det)
            rows.append((score, h, s, connected, (con, det, dem, over)))
    return rows


def picked_pairs(rows: list[tuple], planner: Planner, tried: set) -> list[tuple]:
    """The top M_eff rows with t > 0 whose (house id, shop id) is not in `tried`, by (-t, house id, shop id)."""
    m = planner.m_eff
    if m <= 0:
        return []
    ok = [r for r in rows if r[0] > 0 and math.isfinite(r[0]) and (r[1].id, r[2].id) not in tried]
    ok.sort(key=lambda r: (-r[0], r[1].id, r[2].id))
    return ok[:m]


def v7_features(cand) -> dict[str, float]:
    """The three v7 priority terms of a candidate (0 for legacy kinds)."""
    return {"is_evo": 1.0 if cand.kind == "evo" else 0.0,
            "pair_connected": 1.0 if cand.pair_connected else 0.0,
            "tiles_saved": float(cand.tiles_saved)}
