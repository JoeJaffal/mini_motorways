"""Where a traffic light or a roundabout could be placed, and what each spot would do (gp-4, step 1).

Spec: evolved_rules/plans/2026-11-07-gp4-lights-roundabouts.md. The rules mirror the host
(simulation/Assets/Simulation/TrafficWorld.cs):
  * a light needs an existing ordinary road tile (lines 151-154); the planner also asks for a live junction
    (`link_degree >= 3`), the only place a light can change anything;
  * a roundabout needs its centre and four ring cells in the grid, on land, clear of buildings, roundabouts, lights
    and tiles pending removal (`AddRoundabout`, lines 185-188; terrain 1 is water, 2 is blocked);
  * building one links every ring cell to each in-bounds 8-neighbour outside the footprint that has infrastructure
    and is not part of a roundabout (lines 198-203): `ring_new_links` lists those links.
Two planner-side rules keep the list short and the roads usable: a footprint never covers a building's outside cell
(a doorstep or a driveway cell: the host would reroute every car that uses it), and a roundabout is only offered
where it could matter (a footprint cell with a live junction, or within DOORSTEP_RADIUS of a doorstep).

The list is ordered by trouble near the spot (stopped cars, then cars), then lights before roundabouts, then
position, and cut to PLACE_CAP. Everything is deterministic: grids are scanned row by row and sets only answer
membership questions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .candidates import DOORSTEP_RADIUS, _served_colours, doorsteps, link_degree, near_cells
from .features import STUCK_SPEED
from .state import DIRS, Car, Cell, CityState, H, W, _in_grid

LIGHT = "TrafficLight"
ROUNDABOUT = "Roundabout"
PLACE_CAP = 32  # candidates kept, after sorting
PLACE_RADIUS = 2  # Chebyshev radius around a footprint cell in which a car counts as near the spot
_TOOL_RANK = {LIGHT: 0, ROUNDABOUT: 1}


@dataclass(frozen=True)
class PlacementCandidate:
    tool: str  # LIGHT or ROUNDABOUT
    cell: Cell  # the light cell, or the roundabout centre
    footprint: tuple[Cell, ...]  # the cell, or the centre followed by the ring in N, W, S, E order
    degree: int  # the highest link_degree over the footprint
    new_links: int  # links the build adds (ring_new_links); 0 for a light
    joins_separated: bool  # the build merges networks that together serve two or more colours
    tiles_lost: int  # footprint cells that are road or bridge tiles now


def ring_of(centre: Cell) -> tuple[Cell, Cell, Cell, Cell]:
    """The four ring cells of a roundabout centred on `centre`, in host order N, W, S, E (TrafficWorld.cs:183-184)."""
    x, y = centre
    return ((x, y - 1), (x - 1, y), (x, y + 1), (x + 1, y))


def ring_new_links(state: CityState, centre: Cell) -> list[tuple[Cell, Cell]]:
    """The links a roundabout at `centre` would add, as (ring cell, neighbour) pairs (TrafficWorld.cs:198-203).

    Ring cells in N, W, S, E order, then neighbours in DIRS order. A neighbour counts when it is in the grid, outside
    the footprint, has infrastructure that is not a roundabout, and is not linked to the ring cell yet.
    """
    ring = ring_of(centre)
    footprint = (centre, *ring)
    out: list[tuple[Cell, Cell]] = []
    for r in ring:
        if not _in_grid(r):
            continue
        mask = int(state.conn[r[1], r[0]])
        for d, (dx, dy) in enumerate(DIRS):
            n = (r[0] + dx, r[1] + dy)
            if not _in_grid(n) or n in footprint or (mask >> d) & 1:
                continue
            if int(state.infra[n[1], n[0]]) not in (0, 3):
                out.append((r, n))
    return out


def is_stopped(car: Car) -> bool:
    """A driving car (not Home, not Parking) slower than STUCK_SPEED."""
    return car.stage not in ("Home", "Parking") and car.speed < STUCK_SPEED


def cars_near(state: CityState, footprint: tuple[Cell, ...]) -> tuple[Car, ...]:
    """Cars, in observation order, whose cell (floor of x, y) is within PLACE_RADIUS of any footprint cell."""
    out = []
    for car in state.cars:
        cx, cy = math.floor(car.x), math.floor(car.y)
        if any(max(abs(cx - fx), abs(cy - fy)) <= PLACE_RADIUS for fx, fy in footprint):
            out.append(car)
    return tuple(out)


def _light_cells(state: CityState) -> list[Cell]:
    """Playable ordinary road tiles, not pending removal, with at least three live links, row by row."""
    cells = [(int(x), int(y)) for y, x in np.argwhere(state.infra == 1)]
    return [c for c in cells if state.playable(c) and link_degree(state, c) >= 3]


def _plus_all(g: np.ndarray) -> np.ndarray:
    """For every centre in the grid's interior: the cell and its four orthogonal neighbours are all set in g."""
    return g[1:-1, 1:-1] & g[:-2, 1:-1] & g[2:, 1:-1] & g[1:-1, :-2] & g[1:-1, 2:]


def _plus_any(g: np.ndarray) -> np.ndarray:
    """For every centre in the grid's interior: some cell of the plus is set in g."""
    return g[1:-1, 1:-1] | g[:-2, 1:-1] | g[2:, 1:-1] | g[1:-1, :-2] | g[1:-1, 2:]


def _roundabout_centres(state: CityState) -> list[Cell]:
    """Centres whose whole footprint is buildable, off every outside cell, and worth a roundabout, row by row."""
    x0, y0, x1, y1 = state.bounds
    clear = np.zeros((H, W), dtype=bool)
    clear[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)] = True
    clear &= ((state.terrain != 1) & (state.terrain != 2) & (state.kinds == 0)
              & (state.infra != 3) & (state.infra != 4) & (state.pending != 1))
    outside = np.zeros((H, W), dtype=bool)
    for b in state.buildings:
        for ox, oy in b.outside:
            if _in_grid((ox, oy)):
                outside[oy, ox] = True
    useful = np.zeros((H, W), dtype=bool)
    for y, x in np.argwhere(state.conn != 0):
        if link_degree(state, (int(x), int(y))) >= 3:
            useful[y, x] = True
    for x, y in near_cells(doorsteps(state), DOORSTEP_RADIUS):
        useful[y, x] = True
    ok = _plus_all(clear) & ~_plus_any(outside) & _plus_any(useful)
    return [(int(x) + 1, int(y) + 1) for y, x in np.argwhere(ok)]


class _Networks:
    """The road networks (CityState.component) met so far, and the colours each serves."""

    def __init__(self, state: CityState):
        self._state = state
        self._served = _served_colours(state)
        self._ids: dict[Cell, int] = {}
        self._colours: list[frozenset[int]] = []

    def _network(self, c: Cell) -> int:
        i = self._ids.get(c)
        if i is None:
            i = len(self._colours)
            for member in self._state.component(c):
                self._ids[member] = i
            self._colours.append(self._served.get(c, frozenset()))
        return i

    def join_separated(self, cells: list[Cell]) -> bool:
        """The cells lie in two or more networks that serve two or more colours between them."""
        ids = {self._network(c) for c in cells}
        return len(ids) >= 2 and len(frozenset().union(*(self._colours[i] for i in ids))) >= 2


def _light(state: CityState, cell: Cell) -> PlacementCandidate:
    return PlacementCandidate(LIGHT, cell, (cell,), link_degree(state, cell), 0, False, 1)


def _roundabout(state: CityState, centre: Cell, networks: _Networks) -> PlacementCandidate:
    footprint = (centre, *ring_of(centre))
    links = ring_new_links(state, centre)
    touched = [c for c in footprint if state.road_cell(c)] + [n for _, n in links]
    return PlacementCandidate(
        ROUNDABOUT, centre, footprint,
        max(link_degree(state, c) for c in footprint), len(links), networks.join_separated(touched),
        sum(1 for c in footprint if int(state.infra[c[1], c[0]]) in (1, 2)),
    )


def _order_key(state: CityState, cand: PlacementCandidate) -> tuple[int, int, int, int, int]:
    near = cars_near(state, cand.footprint) if state.cars else ()
    return (-sum(1 for c in near if is_stopped(c)), -len(near), _TOOL_RANK[cand.tool], cand.cell[1], cand.cell[0])


def placement_candidates(state: CityState, lights: bool, roundabouts: bool) -> list[PlacementCandidate]:
    """Light spots (if `lights`) and roundabout spots (if `roundabouts`), most troubled first, at most PLACE_CAP."""
    cands: list[PlacementCandidate] = []
    if lights:
        cands.extend(_light(state, c) for c in _light_cells(state))
    if roundabouts:
        centres = _roundabout_centres(state)
        if centres:
            networks = _Networks(state)
            cands.extend(_roundabout(state, c, networks) for c in centres)
    cands.sort(key=lambda cand: _order_key(state, cand))
    return cands[:PLACE_CAP]
