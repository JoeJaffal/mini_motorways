"""Decision rules: the Policy interface, the hand-written rule, its separated-route variant, the gp-4 rules that place
traffic lights and roundabouts and the do-nothing baseline (PLAN.md section 4)."""
from __future__ import annotations

from typing import Protocol


class Policy(Protocol):
    """What agent.decide reads from a policy.

    Optional attributes (read with getattr and a default, so a policy without them never reaches the code they
    switch on): acts, coverage, clean_routes, wants_globals, removes (gp-3: also needs remove), and, for gp-4,
    places_lights and places_roundabouts. A policy with either of the last two also provides

        place(f: dict[str, float]) -> float

    the score of one placement candidate (features.placement_features, "pl_*"; with wants_globals the global
    features too): the highest score above 0 is built, at most once per decision. The agent only offers a kind
    that the policy places and the game has in stock.
    """

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


def package_upgrade(f: dict[str, float], lights: bool, roundabouts: bool) -> float:
    """gp-4 upgrade rule: take an offer of an enabled package (type 3 = traffic lights, type 4 = roundabout) before
    anything else, and otherwise the offer with the most roads (the hand rule's upgrade)."""
    return 1000.0 * ((lights and f["type_3"] == 1) or (roundabouts and f["type_4"] == 1)) + f["offer_roads"]


def hand_place(f: dict[str, float], lights: bool, roundabouts: bool) -> float:
    """gp-4 placement rule: the number of cars stopped near the spot, for a tool that is enabled.

    A roundabout that would join separated networks scores -1, and so does a tool that is not enabled. The agent
    places only above 0, so a spot is used once 1 or more cars are stopped at it.
    """
    if lights and f["pl_is_light"] == 1:
        return f["pl_stopped_near"]
    if roundabouts and f["pl_is_roundabout"] == 1 and f["pl_joins_separated"] != 1:
        return f["pl_stopped_near"]
    return -1.0


class _PackageHand(SeparatedPreference):
    """The separated preference that also takes the enabled packages and places them (hold, remove unchanged).

    The subclasses switch the two tools on; this base has both off, so it never places (the agent then never looks
    at placement for it).
    """

    name = "package"
    places_lights = False
    places_roundabouts = False

    def upgrade(self, f: dict[str, float]) -> float:
        return package_upgrade(f, self.places_lights, self.places_roundabouts)

    def place(self, f: dict[str, float]) -> float:
        return hand_place(f, self.places_lights, self.places_roundabouts)


class LightHand(_PackageHand):
    """gp-4 hand rule: the separated preference plus traffic lights where cars are stopped."""

    name = "light"
    places_lights = True


class RoundHand(_PackageHand):
    """gp-4 hand rule: the separated preference plus roundabouts where cars are stopped (never one that merges)."""

    name = "round"
    places_roundabouts = True


class LightRoundHand(_PackageHand):
    """gp-4 hand rule: the separated preference plus both tools."""

    name = "lightround"
    places_lights = True
    places_roundabouts = True


class GPHand:
    """An evolved text (gp.TreePolicy) for routes, hold and remove, with the hand rules' package upgrade and placement.

    GPHand(text, lights, roundabouts, name): priority, hold, remove and the coverage / clean_routes / removes /
    wants_globals switches are the tree policy's; upgrade is package_upgrade and place is hand_place with the two
    flags, which are also places_lights and places_roundabouts. With neither flag it only swaps the text's upgrade
    tree for the roads rule and never places.
    """

    def __init__(self, text: str, lights: bool, roundabouts: bool, name: str) -> None:
        from .gp import TreePolicy  # lazy: gp loads deap, which the other policies here do not need

        self.tree = TreePolicy(text)
        self.name = name
        self.places_lights, self.places_roundabouts = bool(lights), bool(roundabouts)
        self.coverage, self.clean_routes = self.tree.coverage, self.tree.clean_routes
        self.removes, self.wants_globals = self.tree.removes, self.tree.wants_globals

    def priority(self, f: dict[str, float]) -> float:
        return self.tree.priority(f)

    def hold(self, g: dict[str, float]) -> float:
        return self.tree.hold(g)

    def upgrade(self, f: dict[str, float]) -> float:
        return package_upgrade(f, self.places_lights, self.places_roundabouts)

    def remove(self, f: dict[str, float]) -> float:
        return self.tree.remove(f)

    def place(self, f: dict[str, float]) -> float:
        return hand_place(f, self.places_lights, self.places_roundabouts)


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
