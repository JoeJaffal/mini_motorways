"""Immutable view of one host observation: parsing and road-graph queries.

Only allow-listed observation fields are read (see PLAN.md section 3.1 and the
plan's Global Constraints); everything else in the reply is ignored.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

W = 50
H = 30
Cell = tuple[int, int]
# Direction d = 0..7 is E, SE, S, SW, W, NW, N, NE; +y goes down the rows.
DIRS: tuple[tuple[int, int], ...] = (
    (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1),
)
N_COLORS = 8


def _in_grid(c: Cell) -> bool:
    return 0 <= c[0] < W and 0 <= c[1] < H


@dataclass(frozen=True)
class Building:
    id: int
    color: int
    is_house: bool
    cell: Cell
    width: int
    height: int
    access: tuple[Cell, ...]
    access_dirs: tuple[int, ...]
    demand: int
    reserved: int
    capacity: int
    overcrowded_for: float
    upgraded: bool

    @property
    def outside(self) -> tuple[Cell, ...]:
        """The cell each access cell attaches to: access + DIRS[dir]."""
        return tuple((x + DIRS[d][0], y + DIRS[d][1]) for (x, y), d in zip(self.access, self.access_dirs))


@dataclass(frozen=True)
class Offer:
    index: int
    type: int
    amount: int
    roads: int

    @property
    def road_value(self) -> int:
        return self.roads + (self.amount if self.type == 0 else 0)


# eq=False: the numpy fields make a generated __eq__/__hash__ unusable.
@dataclass(frozen=True, eq=False)
class CityState:
    time: float
    trips: int
    failed: bool
    inventory: tuple[int, ...]
    offers: tuple[Offer, ...]
    bounds: tuple[int, int, int, int]
    terrain: np.ndarray
    infra: np.ndarray
    conn: np.ndarray
    pending: np.ndarray
    kinds: np.ndarray
    buildings: tuple[Building, ...]
    vehicles_busy: dict[int, int]
    vehicles_waiting: tuple[float, ...]

    def playable(self, c: Cell) -> bool:
        x0, y0, x1, y1 = self.bounds
        return x0 <= c[0] < x1 and y0 <= c[1] < y1

    def houses(self) -> tuple[Building, ...]:
        return tuple(b for b in self.buildings if b.is_house)

    def shops(self) -> tuple[Building, ...]:
        return tuple(b for b in self.buildings if not b.is_house)

    def component(self, c: Cell) -> frozenset[Cell]:
        """Cells reachable from c over link bits, skipping cells pending removal.

        c itself is included (a pending c is not expanded); an out-of-grid c has an empty component.
        """
        if not _in_grid(c):
            return frozenset()
        if self.pending[c[1], c[0]] == 1:
            return frozenset({c})
        seen = {c}
        queue = deque([c])
        while queue:
            x, y = queue.popleft()
            mask = int(self.conn[y, x])
            for d, (dx, dy) in enumerate(DIRS):
                if not (mask >> d) & 1:
                    continue
                nx, ny = x + dx, y + dy
                if not _in_grid((nx, ny)) or (nx, ny) in seen:
                    continue
                if self.pending[ny, nx] == 1:
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))
        return frozenset(seen)

    def house_connected(self, h: Building) -> bool:
        comp = self.component(h.cell)
        return any(a in comp for s in self.shops() if s.color == h.color for a in s.access)

    def shop_served(self, s: Building) -> bool:
        return any(
            any(a in comp for a in s.access)
            for comp in (self.component(h.cell) for h in self.houses() if h.color == s.color)
        )

    def road_cell(self, c: Cell) -> bool:
        """Road or bridge, not pending removal. False for any cell outside the 50 x 30 grid."""
        return _in_grid(c) and int(self.infra[c[1], c[0]]) in (1, 2) and int(self.pending[c[1], c[0]]) != 1


def _grid(obs: dict, key: str) -> np.ndarray:
    flat = obs[key]
    if len(flat) != W * H:
        raise ValueError(f"{key}: expected {W * H} cells, got {len(flat)}")
    arr = np.asarray(flat, dtype=np.int64).reshape(H, W)
    arr.flags.writeable = False
    return arr


def _check_color(color: int) -> int:
    if not 0 <= color < N_COLORS:
        raise ValueError(f"colour {color} outside 0..{N_COLORS - 1}")
    return color


def _cell(d: dict) -> Cell:
    return (int(d["x"]), int(d["y"]))


def _building(b: dict) -> Building:
    cell = _cell(b["cell"])
    if b["isHouse"]:
        access: tuple[Cell, ...] = (cell,)
        access_dirs: tuple[int, ...] = (int(b["drivewayDirection"]),)
    else:
        access = tuple(_cell(e) for e in b["entrances"]) or (_cell(b["entrance"]),)
        access_dirs = tuple(int(d) for d in b["entranceDirections"]) or (int(b["drivewayDirection"]),) * len(access)
    return Building(
        id=int(b["id"]),
        color=_check_color(int(b["color"])),
        is_house=bool(b["isHouse"]),
        cell=cell,
        width=int(b["width"]),
        height=int(b["height"]),
        access=access,
        access_dirs=access_dirs,
        demand=int(b["demand"]),
        reserved=int(b["reserved"]),
        capacity=int(b["demandCapacity"]),
        overcrowded_for=float(b["overcrowdedFor"]),
        upgraded=bool(b["upgraded"]),
    )


def parse_observation(obs: dict) -> CityState:
    if obs["width"] != W or obs["height"] != H:
        raise ValueError(f"expected a {W}x{H} grid, got {obs['width']}x{obs['height']}")
    buildings = tuple(sorted((_building(b) for b in obs["buildings"]), key=lambda b: b.id))
    busy: dict[int, int] = {}
    waiting: list[float] = []
    for v in obs["vehicles"]:
        color = _check_color(int(v["color"]))
        if v["stage"] != "Home":
            busy[color] = busy.get(color, 0) + 1
        waiting.append(float(v["waiting"]))
    return CityState(
        time=float(obs["time"]),
        trips=int(obs["tripsCompleted"]),
        failed=bool(obs["failed"]),
        inventory=tuple(int(n) for n in obs["inventory"]),
        offers=tuple(
            Offer(i, int(o["type"]), int(o["amount"]), int(o["roads"])) for i, o in enumerate(obs["upgradeChoices"])
        ),
        bounds=(int(obs["playableXMin"]), int(obs["playableYMin"]), int(obs["playableXMax"]), int(obs["playableYMax"])),
        terrain=_grid(obs, "terrain"),
        infra=_grid(obs, "infrastructure"),
        conn=_grid(obs, "connections"),
        pending=_grid(obs, "pendingRemovals"),
        kinds=_grid(obs, "buildingKinds"),
        buildings=buildings,
        vehicles_busy=busy,
        vehicles_waiting=tuple(waiting),
    )
