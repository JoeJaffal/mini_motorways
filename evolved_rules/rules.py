"""Decision rules: the Policy interface, the hand-written rule and the do-nothing baseline (PLAN.md section 4)."""
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
