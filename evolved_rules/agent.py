"""The agent: event trigger, one decision (offers, then routes) and the game loop (PLAN.md sections 3.2, 3.4, 4).

Every choice is made by an explicit, deterministic order (scores, then list positions); nothing depends on
hash or set order, so a (policy, seed) game is identical in any process (PLAN.md section 5, Determinism).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .candidates import route_candidates, unserved_targets
from .executor import execute_route, take_offer
from .features import candidate_features, global_features, offer_features
from .host import Host
from .rules import Policy
from .session import GameSession
from .state import CityState

FALLBACK_S = 10.0
OVERCROWD_EVENT_S = 20.0
MAX_ROUTES_PER_DECISION = 20


class EventTracker:
    """Decides when to decide (PLAN.md section 3.2). Its memory is updated on every call."""

    def __init__(self) -> None:
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
        )

        self._ids, self._overcrowded, self._upgraded, self._road_stock = ids, overcrowded, upgraded, road_stock
        if decide:
            self._last_decision = state.time
        return decide


def _finite_or(x: float, default: float) -> float:
    x = float(x)
    return x if math.isfinite(x) else default


def decide(session: GameSession, policy: Policy) -> None:
    """One decision: take a pending offer, then build routes while the best priority clears the hold threshold.

    Returns as soon as the game is over. A house whose route fails is not tried again in this decision (the
    executor never retries; the next decision re-plans). Phase 1 never removes roads.
    """
    if session.done:
        return
    offers = session.state.offers
    if offers:
        # Highest score, then the lower index. A non-finite score ranks lowest; an offer is always taken.
        best = max(offers, key=lambda o: (_finite_or(policy.upgrade(offer_features(o)), -math.inf), -o.index))
        take_offer(session, best.index)

    excluded: set[int] = set()  # house ids whose route failed in this call
    for _ in range(MAX_ROUTES_PER_DECISION):
        if session.done:
            return
        state = session.state
        best = None  # (priority, candidate, target shops); strict > keeps the earliest target, then candidate
        for house, shops in unserved_targets(state):
            if house.id in excluded:
                continue
            for cand in route_candidates(state, house, shops):
                p = float(policy.priority(candidate_features(state, cand)))
                if not math.isfinite(p):
                    continue  # PLAN section 4: a non-finite score is never chosen
                if best is None or p > best[0]:
                    best = (p, cand, shops)
        if best is None:
            return
        hold = float(policy.hold(global_features(state)))
        # PLAN section 4 (line 159) covers candidate scores; a broken (non-finite) threshold never causes an action.
        if not math.isfinite(hold) or best[0] < hold:
            return
        _, cand, shops = best
        ok = execute_route(session, cand)
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

    def summary(self) -> dict:
        """Every field except the recording (JSON-ready)."""
        d = asdict(self)
        del d["recording"]
        return d


def play_game(host: Host, seed: int, policy: Policy, cap_s: float = 3600.0, record: bool = True) -> GameResult:
    """Reset, then decide when the event tracker says so and wait otherwise, until terminated or at cap_s."""
    session = GameSession(host, seed, cap_s=cap_s, record=record)
    session.reset()
    tracker = EventTracker()
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
    )
