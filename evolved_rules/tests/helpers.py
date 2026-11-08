"""Synthetic observation builders in host JSON shape, for tests that run without the host."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

W, H = 50, 30
Cell = tuple[int, int]


import functools

import pytest

from evolved_rules.host import PRE_VERSIONING, default_host_dll, simulator_version

SIM7 = "2026-11-08.7"  # gp-5: main 8025a60

TEST_SIM = "test-sim"  # gp-5: the simulator version fake games report (conftest pins the engine to it)



@functools.lru_cache(maxsize=None)
def _host_version() -> str:
    return simulator_version(default_host_dll())


def for_simulator(table: dict):
    """table[the simulatorVersion of the host DLL under test]; skips when nothing is pinned for that version.

    Frozen game fingerprints depend on the simulator: the old ones (PRE_VERSIONING, the e6119eb engine of
    phases 1-4) stay, and each new simulator gets its own entry, so the same tests guard either host.
    """
    version = _host_version()
    if version not in table:
        pytest.skip(f"no fingerprints pinned for simulator {version!r}")
    return table[version]


def _xy(x: int, y: int) -> dict:
    return {"x": x, "y": y}


def _excluded_building_fields(feasible: float) -> dict:
    """Fields the real host emits per building that the agent must never read (PLAN section 7)."""
    return {
        "upgradeAt": None, "plannedDemandMultiplier": 1, "originalDemandInterval": 0,
        "feasibleDemandInterval": feasible, "feasibilityVerified": feasible > 0,
    }


def house(id: int, color: int, x: int, y: int, dir: int) -> dict:
    return {
        "id": id, "color": color, "isHouse": True,
        "cell": _xy(x, y), "width": 1, "height": 1,
        "entrance": _xy(x, y), "entrances": [], "entranceDirections": [],
        "drivewayDirection": dir,
        "demand": 0, "reserved": 0, "demandCapacity": 6, "overcrowdedFor": 0,
        "upgraded": False, "carparkId": -1,
        **_excluded_building_fields(0),
    }


def shop(id: int, color: int, x: int, y: int, w: int, h: int, entrances: list[tuple[int, int, int]]) -> dict:
    ex, ey, edir = entrances[0]
    return {
        "id": id, "color": color, "isHouse": False,
        "cell": _xy(x, y), "width": w, "height": h,
        "entrance": _xy(ex, ey),
        "entrances": [_xy(a, b) for a, b, _ in entrances],
        "entranceDirections": [d for _, _, d in entrances],
        "drivewayDirection": edir,
        "demand": 0, "reserved": 0, "demandCapacity": 6, "overcrowdedFor": 0,
        "upgraded": False, "carparkId": 0,
        **_excluded_building_fields(51.911754903260444),
    }


def make_obs(
    buildings: Iterable[dict] = (),
    roads: Mapping[Cell, int] | None = None,
    terrain: Mapping[Cell, int] | None = None,
    infra: Mapping[Cell, int] | None = None,
    pending: Iterable[Cell] = (),
    inventory: Iterable[int] = (25, 1, 0, 0, 0, 0),
    bounds: tuple[int, int, int, int] = (0, 0, 50, 30),
    time: float = 0.0,
    offers: Iterable[dict] = (),
    vehicles: Iterable[dict] = (),
    roundabouts: Iterable[tuple[Cell, Iterable[Cell]]] = (),
) -> dict:
    """A full observation dict.

    roads maps cell -> link mask (bit d = link towards DIRS[d]). Such a cell gets infrastructure 1
    unless it lies inside a building footprint; an explicit infra entry overrides that default.
    offers are upgradeChoices entries ({type, amount, roads}); vehicles are vehicle dicts
    ({color, stage, waiting}). roundabouts are (centre, ring) pairs, the ring in host order N, W, S, E; each
    is written in the host's snapshot shape and sets infrastructure 3 on its five cells. Like the real host,
    the observation also carries fields the agent must never read: scheduledSpawns/randomAlgorithm/randomDraws,
    the per-building fields from _excluded_building_fields, offer generation fields and vehicle
    route/returnRoute.
    """
    buildings = list(buildings)
    roads, terrain, infra = dict(roads or {}), dict(terrain or {}), dict(infra or {})
    roundabouts = [(centre, list(ring)) for centre, ring in roundabouts]

    def idx(c: Cell) -> int:
        return c[1] * W + c[0]

    kinds, colors = [0] * (W * H), [-1] * (W * H)
    for b in buildings:
        bx, by = b["cell"]["x"], b["cell"]["y"]
        for y in range(by, by + b["height"]):
            for x in range(bx, bx + b["width"]):
                kinds[idx((x, y))] = 1 if b["isHouse"] else 2
                colors[idx((x, y))] = b["color"]

    infra_grid = [0] * (W * H)
    for c in roads:
        if kinds[idx(c)] == 0:
            infra_grid[idx(c)] = 1
    for centre, ring in roundabouts:
        for c in (centre, *ring):
            infra_grid[idx(c)] = 3
    for c, v in infra.items():
        infra_grid[idx(c)] = v

    conn_grid, terrain_grid, pending_grid = [0] * (W * H), [0] * (W * H), [0] * (W * H)
    for c, mask in roads.items():
        conn_grid[idx(c)] = mask
    for c, v in terrain.items():
        terrain_grid[idx(c)] = v
    for c in pending:
        pending_grid[idx(c)] = 1

    x0, y0, x1, y1 = bounds
    return {
        "width": W, "height": H, "time": time, "tripsCompleted": 0, "failed": False,
        "version": "OriginalReference", "unlimitedConstruction": False,
        "inventory": list(inventory),
        "upgradeChoices": [
            {"weight": 1, "firstWeek": 1, "lastWeek": 8, "maximum": 3, **o} for o in offers
        ],
        "terrain": terrain_grid, "infrastructure": infra_grid, "connections": conn_grid,
        "pendingRemovals": pending_grid, "buildingKinds": kinds, "buildingColors": colors,
        "buildings": buildings,
        "vehicles": [
            {"route": [_xy(1, 1), _xy(2, 1)], "returnRoute": [_xy(2, 1), _xy(1, 1)], **v} for v in vehicles
        ],
        "scheduledSpawns": [{"time": 12.5, "color": 0, "isHouse": True}],
        "randomAlgorithm": "MSWS reference stream", "randomDraws": 713,
        "roundabouts": [
            {"center": _xy(*centre), "ring": [_xy(*c) for c in ring], "pendingRemoval": False}
            for centre, ring in roundabouts
        ],
        "playableXMin": x0, "playableYMin": y0, "playableXMax": x1, "playableYMax": y1,
    }
