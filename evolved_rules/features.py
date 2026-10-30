"""Feature dicts the rules read: one per route candidate, one global, one per upgrade offer (PLAN.md section 4).

Phase 1 values are raw (not normalised). Phase 2 may add keys; it never renames these.
"""
from __future__ import annotations

from .candidates import RouteCandidate
from .state import CityState, Offer

N_ITEM_TYPES = 6  # inventory: roads, bridges, motorways, traffic lights, roundabouts, unused


def candidate_features(state: CityState, cand: RouteCandidate) -> dict[str, float]:
    """Features of one route. path_len counts steps (cells - 1); the kind is one-hot."""
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


def global_features(state: CityState) -> dict[str, float]:
    """unserved_houses: houses that have a shop of their colour but do not reach any of them."""
    shop_colours = {s.color for s in state.shops()}
    unserved = sum(1 for h in state.houses() if h.color in shop_colours and not state.house_connected(h))
    inv = state.inventory
    return {
        "road_stock": float(inv[0] if len(inv) > 0 else 0),
        "bridge_stock": float(inv[1] if len(inv) > 1 else 0),
        "time": float(state.time),
        "unserved_houses": float(unserved),
    }


def offer_features(offer: Offer) -> dict[str, float]:
    f = {"offer_roads": float(offer.road_value), "amount": float(offer.amount)}
    for t in range(N_ITEM_TYPES):
        f[f"type_{t}"] = 1.0 if offer.type == t else 0.0
    return f
