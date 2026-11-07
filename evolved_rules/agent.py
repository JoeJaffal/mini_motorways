"""The agent: event trigger, one decision (offers, routes, then, for policies that ask for them, a placement and a
removal) and the game loop (PLAN.md sections 3.2, 3.4, 4).

Every choice is made by an explicit, deterministic order (scores, then list positions); nothing depends on
hash or set order, so a (policy, seed) game is identical in any process (PLAN.md section 5, Determinism).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .candidates import coverage_targets, house_reaches, removal_candidates, route_candidates, unserved_targets
from .executor import execute_route, place_item, remove_tile, take_offer
from .features import (candidate_features, global_features, is_driving, offer_features, placement_features,
                       removal_features)
from .host import Host
from .placement import placement_candidates
from .rules import Policy
from .session import GameSession
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


def _build_routes(session: GameSession, policy: Policy, memory, merge: bool) -> None:
    """The route part of decide(): build routes while the best priority clears the hold threshold."""
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

    def summary(self) -> dict:
        """Every field except the recording (JSON-ready)."""
        d = asdict(self)
        del d["recording"]
        return d


def trips_per_tile(trips: int, tiles_built: int) -> float:
    """Trips per road tile spent; 0.0 when no tile was spent (JSON has no infinity)."""
    return trips / tiles_built if tiles_built > 0 else 0.0


def play_game(host: Host, seed: int, policy: Policy, cap_s: float = 3600.0, record: bool = True) -> GameResult:
    """Reset, then decide when the event tracker says so and wait otherwise, until terminated or at cap_s.

    The session's GameMemory (and so its DemandTracker) is created fresh by reset(): one per game.
    """
    session = GameSession(host, seed, cap_s=cap_s, record=record)
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
    )
