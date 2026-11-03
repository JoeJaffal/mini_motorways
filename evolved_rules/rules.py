"""Decision rules: the Policy interface, the hand-written rule, its separated-route variant and the do-nothing baseline (PLAN.md section 4)."""
from __future__ import annotations

from typing import Protocol


class Policy(Protocol):
    name: str

    def priority(self, f: dict[str, float]) -> float:
        """Score of one route candidate (candidate_features); the highest is built."""

    def hold(self, g: dict[str, float]) -> float:
        """Threshold (global_features): build only while the best priority is at least this."""

    def upgrade(self, f: dict[str, float]) -> float:
        """Score of one offer (offer_features); the highest is taken."""

    def remove(self, f: dict[str, float]) -> float:
        """Score of one road segment; a removal runs only above 0 (Phase 1 never removes)."""


class HandRule:
    """Cheapest route first, keep a reserve of 4 road tiles, take the offer with the most roads, never remove."""

    name = "hand"

    def priority(self, f: dict[str, float]) -> float:
        return -f["tiles_needed"]

    def hold(self, g: dict[str, float]) -> float:
        return 4 - g["road_stock"]

    def upgrade(self, f: dict[str, float]) -> float:
        return f["offer_roads"]

    def remove(self, f: dict[str, float]) -> float:
        return -1.0


class SeparatedPreference(HandRule):
    """The hand rule, but always build a separated candidate when there is one (hold, upgrade, remove unchanged).

    priority = -tiles_needed + 1000 * is_separated. This is the policy of the Phase 1 run phase1-separated
    (PLAN.md section 7), which registered it at runtime from a scratch driver.
    """

    name = "separated"

    def priority(self, f: dict[str, float]) -> float:
        return -f["tiles_needed"] + 1000.0 * f["is_separated"]


class CleanHand(SeparatedPreference):
    """gp-3 hand baseline: coverage targets and clean routes; a clean route first, then a separated one.

    priority = -tiles_needed + 1000 * is_separated + 2000 * is_clean. A clean route avoids adding junction links
    near shop doorsteps (candidates.route_candidates). Hold, upgrade and remove are the hand rule's. With the
    +1000 / +2000 offsets the 4-tile reserve applies only to the other routes, as for SeparatedPreference.
    """

    name = "clean"
    coverage = True
    clean_routes = True

    def priority(self, f: dict[str, float]) -> float:
        return -f["tiles_needed"] + 1000.0 * f["is_separated"] + 2000.0 * f.get("is_clean", 0.0)


class CleanRemoveHand(CleanHand):
    """CleanHand plus untangling: remove a tile that feeds a crowded doorstep while cars are stuck there.

    remove = doorstep links + stuck cars when the tile links to a doorstep with >= 3 links and at least
    REMOVE_STUCK cars are stuck near that shop; -1 (never) otherwise. Only tiles whose removal keeps every
    house connected to every shop it reaches are ever offered (candidates.removal_candidates).
    """

    name = "cleanrm"
    removes = True
    REMOVE_STUCK = 2

    def remove(self, f: dict[str, float]) -> float:
        if f["rm_links_doorstep"] and f["rm_doorstep_degree"] >= 3 and f["rm_shop_stuck"] >= self.REMOVE_STUCK:
            return f["rm_doorstep_degree"] + f["rm_shop_stuck"]
        return -1.0


class SeparatedRemoveHand(CleanRemoveHand):
    """Separated preference with coverage targets plus CleanRemoveHand's untangling, without clean routes.

    Measures the removal move on its own (gp-3 step 2): the priority is SeparatedPreference's.
    """

    name = "seprm"
    clean_routes = False

    def priority(self, f: dict[str, float]) -> float:
        return SeparatedPreference.priority(self, f)


class DoNothing:
    """Baseline that never acts: play_game only waits (offers are never taken, nothing is built)."""

    name = "nothing"
    acts = False  # play_game never calls decide() for a policy with acts = False

    def priority(self, f: dict[str, float]) -> float:
        return float("-inf")

    def hold(self, g: dict[str, float]) -> float:
        return float("inf")

    def upgrade(self, f: dict[str, float]) -> float:
        return 0.0

    def remove(self, f: dict[str, float]) -> float:
        return -1.0
