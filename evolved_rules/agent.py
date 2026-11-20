"""The agent: event trigger, one decision (offers, routes, then, for policies that ask for them, a placement and a
removal) and the game loop (PLAN.md sections 3.2, 3.4, 4).

Every choice is made by an explicit, deterministic order (scores, then list positions); nothing depends on
hash or set order, so a (policy, seed) game is identical in any process (PLAN.md section 5, Determinism).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .candidates import (coverage_targets, house_reaches, pair_candidate, removal_candidates, route_candidates,
                         unserved_targets)
from .executor import execute_route, place_item, remove_tile, take_offer
from .features import (candidate_features, global_features, is_driving, offer_features, placement_features,
                       removal_features)
from .gp import CANDIDATE_TERMS, GLOBAL_TERMS, V7_CANDIDATE_TERMS
from .host import Host
from .placement import placement_candidates
from .rules import Policy
from .session import DEFAULT_SCENARIO, GameSession
from .state import CityState

FALLBACK_S = 10.0
OVERCROWD_EVENT_S = 20.0
MAX_ROUTES_PER_DECISION = 20
MAX_REMOVALS_PER_DECISION = 1  # gp-3
MAX_PLACEMENTS_PER_DECISION = 1  # gp-4
PLACE_WAIT_S = 3.0  # gp-4: a car that has waited this long (Car.waiting) makes a placing policy look for a spot
PLACE_EVERY_S = 5.0  # gp-4: ...at most once per this many seconds since the last decision


def places(policy: Policy) -> tuple[bool, bool]:
    """gp-4: (places traffic lights, places roundabouts). A policy without the attributes places nothing."""
    return (getattr(policy, "places_lights", False), getattr(policy, "places_roundabouts", False))


def _stock(state: CityState, item: int) -> int:
    """Inventory slot `item` (3 traffic lights, 4 roundabouts); 0 when the observation has no such slot."""
    return state.inventory[item] if len(state.inventory) > item else 0


class EventTracker:
    """Decides when to decide (PLAN.md section 3.2). Its memory is updated on every call.

    `kinds` (gp-4) is (places lights, places roundabouts), as agent.places(policy) gives it. For each kind the
    policy places, the tracker also decides when that kind is in stock, some car has waited PLACE_WAIT_S, and
    PLACE_EVERY_S have passed since the last decision; stock of a kind the policy does not place is no event.
    With (False, False), the default, the trigger is exactly the Phase 1 one.
    """

    def __init__(self, kinds: tuple[bool, bool] = (False, False)) -> None:
        self._lights, self._roundabouts = bool(kinds[0]), bool(kinds[1])
        self._last_decision: float | None = None  # time of the last call that returned True
        self._ids: frozenset[int] = frozenset()
        self._overcrowded: dict[int, bool] = {}  # shop id -> overcrowded_for >= OVERCROWD_EVENT_S
        self._upgraded: dict[int, bool] = {}  # building id -> upgraded
        self._road_stock: int | None = None

    def should_decide(self, state: CityState) -> bool:
        ids = frozenset(b.id for b in state.buildings)
        overcrowded = {s.id: s.overcrowded_for >= OVERCROWD_EVENT_S for s in state.shops()}
        upgraded = {b.id: b.upgraded for b in state.buildings}
        road_stock = state.inventory[0] if state.inventory else 0

        decide = (
            self._last_decision is None
            or bool(ids - self._ids)
            or bool(state.offers)
            # crosses upward: below the threshold last call (or unseen) and at/above it now
            or any(now and not self._overcrowded.get(i, False) for i, now in overcrowded.items())
            or any(i in self._upgraded and self._upgraded[i] != now for i, now in upgraded.items())
            or (self._road_stock is not None and road_stock > self._road_stock)
            or state.time - self._last_decision >= FALLBACK_S
            or ((self._lights or self._roundabouts) and self._placement_due(state))
        )

        self._ids, self._overcrowded, self._upgraded, self._road_stock = ids, overcrowded, upgraded, road_stock
        if decide:
            self._last_decision = state.time
        return decide

    def _placement_due(self, state: CityState) -> bool:
        """Stock of a kind the policy places, PLACE_EVERY_S since the last decision, and a car that has waited
        PLACE_WAIT_S. Only driving cars count: the host never resets a car's Waiting once it parks or is home.
        Only reached after the first decision (the first call always decides)."""
        return (((self._lights and _stock(state, 3) > 0) or (self._roundabouts and _stock(state, 4) > 0))
                and state.time - self._last_decision >= PLACE_EVERY_S
                and any(is_driving(car) and car.waiting >= PLACE_WAIT_S for car in state.cars))


def _finite_or(x: float, default: float) -> float:
    x = float(x)
    return x if math.isfinite(x) else default


def decide(session: GameSession, policy: Policy) -> None:
    """One decision: take a pending offer, then build routes while the best priority clears the hold threshold,
    then place a light or a roundabout (gp-4, policies that place), then remove a tile (gp-3, policies that remove).

    Returns as soon as the game is over. A house whose route fails is not tried again in this decision (the
    executor never retries; the next decision re-plans). Phase 1 never removes roads. Features read the
    session's per-game memory (demand rates, offers taken, cached road-network analysis).

    A policy with a true `coverage` attribute (Phase 2, decision P2-6) plans over coverage_targets instead, and
    exclusion is per (house, shop) pair: a route for (house, shops) succeeds when the house now reaches one of
    those shops; otherwise each of those pairs is excluded, and a later target drops its excluded shops (it is
    skipped when none is left). Policies without the attribute run the Phase 1 code path unchanged.

    A policy with a true `wants_globals` attribute (gp.TreePolicy: its priority and upgrade trees read global
    terminals) gets every candidate and offer dict merged with the global features of the same state (the
    keys never overlap), and its hold sees that same global dict. Phase 1 policies get the Phase 1 dicts.
    """
    if session.done:
        return
    memory = session.memory
    merge = bool(getattr(policy, "wants_globals", False))
    offers = session.state.offers
    if offers:
        # Highest score, then the lower index. A non-finite score ranks lowest; an offer is always taken.
        state = session.state
        g = global_features(state, memory) if merge else {}
        best = max(offers, key=lambda o: (_finite_or(policy.upgrade({**offer_features(o, state), **g}),
                                                     -math.inf), -o.index))
        take_offer(session, best.index)

    _build_routes(session, policy, memory, merge)
    if any(places(policy)):
        _place_one(session, policy, memory, merge)
    if getattr(policy, "removes", False):
        _remove_one(session, policy, memory, merge)


def _place_one(session: GameSession, policy: Policy, memory, merge: bool) -> None:
    """gp-4 (policies with `places_lights` / `places_roundabouts`): place the best placement candidate if its score
    is above 0.

    Only the kinds the policy places and the game has in stock are offered (placement_candidates is not even
    called with neither). At most MAX_PLACEMENTS_PER_DECISION per decision (a placement changes the network, so
    the next one is re-planned at the next decision). Ties keep the earlier candidate of placement_candidates'
    order; a non-finite score never places anything.
    """
    want_lights, want_roundabouts = places(policy)
    for _ in range(MAX_PLACEMENTS_PER_DECISION):
        if session.done:
            return
        state = session.state
        lights = want_lights and _stock(state, 3) > 0
        roundabouts = want_roundabouts and _stock(state, 4) > 0
        if not (lights or roundabouts):
            return
        g = global_features(state, memory) if merge else {}
        best = None
        for pc in placement_candidates(state, lights, roundabouts):
            score = float(policy.place({**placement_features(state, pc, memory), **g}))
            if math.isfinite(score) and score > 0 and (best is None or score > best[0]):
                best = (score, pc)
        if best is None:
            return
        place_item(session, best[1])


def _remove_one(session: GameSession, policy: Policy, memory, merge: bool) -> None:
    """gp-3 (policies with `removes`): remove the best removal candidate if its score is above 0.

    At most MAX_REMOVALS_PER_DECISION tiles per decision (each removal changes the network, so the next one is
    re-planned at the next decision). Ties keep the earliest candidate in removal_candidates' (y, x) order; a
    non-finite score never removes anything.
    """
    for _ in range(MAX_REMOVALS_PER_DECISION):
        if session.done:
            return
        state = session.state
        g = global_features(state, memory) if merge else {}
        best = None
        for rc in removal_candidates(state):
            score = float(policy.remove({**removal_features(state, rc, memory), **g}))
            if math.isfinite(score) and score > 0 and (best is None or score > best[0]):
                best = (score, rc)
        if best is None:
            return
        remove_tile(session, best[1].cell)


_LOG_CAND_TERMS = CANDIDATE_TERMS + V7_CANDIDATE_TERMS  # raw values logged per candidate (decision records)
_LOG_GLOBAL_TERMS = GLOBAL_TERMS
def _octile64(h, s) -> float:
    """Octile distance from the house cell to the shop's nearest access cell, / 64 (gp-7-lite target-slot input)."""
    if not s.access:
        return 0.0
    dx = min(abs(h.cell[0] - a[0]) for a in s.access)
    dy = min(abs(h.cell[1] - a[1]) for a in s.access)
    return round((max(dx, dy) - min(dx, dy) + 1.414 * min(dx, dy)) / 64.0, 6)


def _cell_summary(state) -> dict:
    """gp-7-lite cost-slot inputs of one decision: [cars_on, stopped_on, near_shop] per cell with cars, the counts of
    playable cells without cars near / not near a doorstep, and worst_overcrowded/1024."""
    from . import planner7
    from .candidates import NEAR_SHOP_RADIUS, doorsteps, near_cells
    cars, stopped = planner7.cell_maps(state)
    near = near_cells(doorsteps(state), NEAR_SHOP_RADIUS)
    playable_near = sum(1 for c in near if state.playable(c))
    cars_near = sum(1 for c in cars if c in near)
    H, W = state.conn.shape
    playable = sum(1 for y in range(H) for x in range(W) if state.playable((x, y)))
    return {"cars": [[n, stopped.get(c, 0), 1 if c in near else 0] for c, n in sorted(cars.items())],
            "empty_near": playable_near - cars_near, "empty_far": playable - playable_near - (len(cars) - cars_near),
            "wo": planner7.worst_overcrowded(state) / 1024.0}


EVO_TARGETS = 8  # gp-7: the evo route is searched for the first EVO_TARGETS (non-excluded) targets of a pass


def _build_routes_v7(session: GameSession, policy, memory, merge: bool) -> None:
    """gp-7 (moves=v7, a text with a planner trailer): the v6 route loop plus the evolvable planner (plan 3.1).

    Each pass offers, after the legacy candidates of each target, an evo route (EvoCost search) for the first
    EVO_TARGETS targets, and after all targets one route per picked target-head pair (planner7.picked_pairs), each
    pair tried at most once per decision (tried_pairs; excluded_pairs keeps its v6 meaning). Every candidate's
    priority also reads the v7 terms. Ties keep the earliest candidate, as in v6. With a `decision_log` list on
    the policy, one record per decision is appended (planner7 / decision logging, plan 3.1).
    """
    from . import planner7  # only v7 texts need it

    coverage = bool(getattr(policy, "coverage", False))
    clean = bool(getattr(policy, "clean_routes", False))
    pl = policy.planner
    log = getattr(policy, "decision_log", None)
    rec = None
    excluded: set[int] = set()
    excluded_pairs: set[tuple[int, int]] = set()
    tried_pairs: set[tuple[int, int]] = set()
    built: list[str] = []
    for pass_i in range(MAX_ROUTES_PER_DECISION):
        if session.done:
            break
        state = session.state
        g = global_features(state, memory) if merge else {}
        evo = planner7.evo_cost(state, pl)
        first = log is not None and pass_i == 0
        rows: list | None = [] if first else None
        best = None  # (priority, candidate, target shops, row index, source)
        n_evo = 0

        def consider(cand, shops, src):
            nonlocal best
            f = {**candidate_features(state, cand, memory), **planner7.v7_features(cand), **g}
            p = float(policy.priority(f))
            if rows is not None:
                rows.append((src if src == "pair" else cand.kind, p, [round(float(f[k]), 4) for k in _LOG_CAND_TERMS]))
            if not math.isfinite(p):
                return
            if best is None or p > best[0]:
                best = (p, cand, shops, len(rows) - 1 if rows is not None else -1, src)

        for house, shops in (coverage_targets(state) if coverage else unserved_targets(state)):
            if coverage:
                shops = tuple(s for s in shops if (house.id, s.id) not in excluded_pairs)
                if not shops:
                    continue
            elif house.id in excluded:
                continue
            use_evo = n_evo < EVO_TARGETS
            n_evo += 1
            for cand in route_candidates(state, house, shops, clean=clean, evo=evo if use_evo else None):
                consider(cand, shops, "target")
        pair_rows = planner7.pair_rows(state, memory, pl) if (pl.m_eff > 0 or first) else []
        for _, h, s, connected, _ in planner7.picked_pairs(pair_rows, pl, tried_pairs):
            tried_pairs.add((h.id, s.id))
            net_steps = planner7.shop_steps(state, memory, s).get(h.cell) if connected else None
            cand = pair_candidate(state, h, s, connected, evo, net_steps)
            if cand is not None:
                consider(cand, (s,), "pair")
        hold = float(policy.hold(g if merge else global_features(state, memory))) if best is not None else math.nan
        if first:
            b_t = pl.t("b_t")
            top = sorted(pair_rows, key=lambda r: (-r[0], r[1].id, r[2].id))[:10]
            rec = {"t": float(state.time), "g": [round(float(g[k]), 4) for k in _LOG_GLOBAL_TERMS] if g else [],
                   "kind": [r[0] for r in rows], "p": [r[1] for r in rows], "rows": [r[2] for r in rows],
                   "hold": hold, "best": best[3] if best is not None else -1,
                   "pairs_n": len(pair_rows),
                   "pair_tmax_nobias": max((r[0] - b_t for r in pair_rows), default=None),
                   "pairs_top": [[r[1].id, r[2].id, r[0], *r[4], _octile64(r[1], r[2])] for r in top],
                   "cells": _cell_summary(state),
                   "cars": sum(1 for c in state.cars if is_driving(c)),
                   "stopped": sum(1 for c in state.cars if is_driving(c) and c.speed < 0.05)}
        if best is None:
            break
        if not math.isfinite(hold) or best[0] < hold:
            break
        _, cand, shops, _, src = best
        ok = execute_route(session, cand)
        built.append("pair" if src == "pair" else cand.kind)
        if coverage:
            if not house_reaches(session.state, cand.house_id, shops):
                excluded_pairs.update((cand.house_id, s.id) for s in shops)
            continue
        if not ok or not any(session.state.shop_served(s) for s in shops):
            excluded.add(cand.house_id)
    if log is not None:
        if rec is None:
            rec = {"t": float(session.state.time), "kind": [], "p": [], "rows": [], "best": -1}
        rec["built"] = built
        rec["evo_built"] = any(k in ("evo", "pair") for k in built)
        log.append(rec)


def _build_routes(session: GameSession, policy: Policy, memory, merge: bool) -> None:
    """The route part of decide(): build routes while the best priority clears the hold threshold."""
    if getattr(policy, "v7", False):
        return _build_routes_v7(session, policy, memory, merge)
    coverage = bool(getattr(policy, "coverage", False))
    clean = bool(getattr(policy, "clean_routes", False))  # gp-3: also offer a clean (junction-averse) route
    excluded: set[int] = set()  # Phase 1: house ids whose route failed in this call
    excluded_pairs: set[tuple[int, int]] = set()  # coverage: (house id, shop id) pairs whose route failed
    for _ in range(MAX_ROUTES_PER_DECISION):
        if session.done:
            return
        state = session.state
        g = global_features(state, memory) if merge else {}
        best = None  # (priority, candidate, target shops); strict > keeps the earliest target, then candidate
        for house, shops in (coverage_targets(state) if coverage else unserved_targets(state)):
            if coverage:
                shops = tuple(s for s in shops if (house.id, s.id) not in excluded_pairs)
                if not shops:
                    continue
            elif house.id in excluded:
                continue
            cands = route_candidates(state, house, shops, clean=True) if clean else route_candidates(state, house, shops)
            for cand in cands:
                p = float(policy.priority({**candidate_features(state, cand, memory), **g}))
                if not math.isfinite(p):
                    continue  # PLAN section 4: a non-finite score is never chosen
                if best is None or p > best[0]:
                    best = (p, cand, shops)
        if best is None:
            return
        hold = float(policy.hold(g if merge else global_features(state, memory)))
        # PLAN section 4 (line 159) covers candidate scores; a broken (non-finite) threshold never causes an action.
        if not math.isfinite(hold) or best[0] < hold:
            return
        _, cand, shops = best
        ok = execute_route(session, cand)
        if coverage:
            # ok (reaches any shop of the colour) is ignored on purpose: coverage success means reaching one
            # of the target shops, which house_reaches checks.
            if not house_reaches(session.state, cand.house_id, shops):
                excluded_pairs.update((cand.house_id, s.id) for s in shops)
            continue
        # execute_route reports whether the house reaches a shop of its colour. For a target from an unserved
        # shop the house may have been connected already, so also require that one of the target shops is
        # served now; otherwise the same target would be re-planned (and redrawn) up to the route limit.
        if not ok or not any(session.state.shop_served(s) for s in shops):
            excluded.add(cand.house_id)


@dataclass
class GameResult:
    trips: int
    seconds: float
    rejected_actions: int
    commands: int
    action_counts: dict
    mean_car_wait: float
    max_car_wait: float
    terminated: bool
    truncated: bool
    scenario_seed: int
    city: str
    deterministic: bool
    failed_shop: int | None
    road_tiles_at_failure: int | None
    recording: dict | None
    # Phase 2 game metrics (defaults keep positional construction of the Phase 1 fields working).
    tiles_built: int = 0  # road tiles spent by draws (GameSession.tiles_built)
    trips_per_tile: float = 0.0  # trips / tiles_built; 0.0 when no tile was built
    simulator_version: str | None = None  # gp-5: the host's simulatorVersion (host.PRE_VERSIONING for old hosts)

    def summary(self) -> dict:
        """Every field except the recording (JSON-ready)."""
        d = asdict(self)
        del d["recording"]
        return d


def trips_per_tile(trips: int, tiles_built: int) -> float:
    """Trips per road tile spent; 0.0 when no tile was spent (JSON has no infinity)."""
    return trips / tiles_built if tiles_built > 0 else 0.0


def play_game(host: Host, seed: int, policy: Policy, cap_s: float = 3600.0, record: bool = True,
              scenario: str = DEFAULT_SCENARIO) -> GameResult:
    """Reset, then decide when the event tracker says so and wait otherwise, until terminated or at cap_s.

    The session's GameMemory (and so its DemandTracker) is created fresh by reset(): one per game.
    """
    session = GameSession(host, seed, cap_s=cap_s, record=record, scenario=scenario)
    session.reset()
    tracker = EventTracker(kinds=places(policy))
    acts = getattr(policy, "acts", True)
    # Always advances: a decision that sends nothing leaves the state unchanged, and the tracker never fires
    # twice on an unchanged state (offers would fire again, but a decision with offers always sends a command).
    while not session.done:
        if acts and tracker.should_decide(session.state):
            decide(session, policy)
        else:
            session.wait()

    state = session.state
    failed_shop = road_tiles_at_failure = None
    if session.terminated:
        shops = state.shops()
        if shops:
            failed_shop = max(shops, key=lambda s: (s.overcrowded_for, -s.id)).id
        road_tiles_at_failure = state.inventory[0]
    return GameResult(
        trips=state.trips,
        seconds=state.time,
        rejected_actions=session.rejected,
        commands=session.commands,
        action_counts=dict(session.action_counts),
        mean_car_wait=session.wait_sum / session.wait_n if session.wait_n else 0.0,
        max_car_wait=session.max_wait,
        terminated=session.terminated,
        truncated=not session.terminated and state.time >= cap_s,
        scenario_seed=seed,
        city=session.scenario,
        deterministic=True,
        failed_shop=failed_shop,
        road_tiles_at_failure=road_tiles_at_failure,
        recording=(session.recorder.recording(session.raw, "evolved-rules:" + policy.name)
                   if session.recorder is not None else None),
        tiles_built=session.tiles_built,
        trips_per_tile=trips_per_tile(state.trips, session.tiles_built),
        simulator_version=getattr(host, "simulator_version", None),
    )
