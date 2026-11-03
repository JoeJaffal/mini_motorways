"""Execute a route candidate on a GameSession, one draw stroke at a time."""
from __future__ import annotations

from .candidates import _ORTHO, RouteCandidate, Stroke, _is_road, _water
from .session import GameSession
from .state import DIRS, Cell, CityState, _in_grid


def stroke_cells(s: Stroke) -> list[Cell]:
    """The cells a draw covers, endpoints included: the host's TrafficWorld.RasterLine (an exact
    8-direction run for the straight strokes the candidates produce)."""
    n = max(abs(s.to_x - s.x), abs(s.to_y - s.y))
    if n == 0:
        return [(s.x, s.y)]
    return [(round(s.x + (s.to_x - s.x) * i / n), round(s.y + (s.to_y - s.y) * i / n)) for i in range(n + 1)]


def _linked(state: CityState, a: Cell, b: Cell) -> bool:
    """True if the road graph has the link a -> b: conn[a] has the bit of the direction a -> b."""
    if not (_in_grid(a) and _in_grid(b)):
        return False
    delta = (b[0] - a[0], b[1] - a[1])
    return delta in DIRS and bool(int(state.conn[a[1], a[0]]) & (1 << DIRS.index(delta)))


def _new_tiles(state: CityState, cells: list[Cell]) -> int:
    """Road tiles the stroke has to build. cells[0] is the house or the previous stroke's end, never a new
    tile; counting cells[1:] matches candidates' tiles_needed (path[1:]), with the same road predicate."""
    return sum(1 for c in cells[1:] if not _is_road(state, c))


def _new_spans(state: CityState, cells: list[Cell]) -> int:
    """Bridge items the stroke needs, counted as candidates' A* does: an unbuilt water cell starts a new span
    unless the previous cell on the path is water, or an orthogonal neighbour is already a bridge."""
    def bridge_at(c: Cell) -> bool:
        return _in_grid(c) and int(state.infra[c[1], c[0]]) == 2

    spans = 0
    for prev, c in zip(cells, cells[1:]):
        if not _water(state, c) or _is_road(state, c) or _water(state, prev):
            continue
        if any(bridge_at((c[0] + dx, c[1] + dy)) for dx, dy in _ORTHO):
            continue
        spans += 1
    return spans


def execute_route(session: GameSession, cand: RouteCandidate) -> bool:
    """Send cand.strokes in order; True if the candidate's house ends up connected to a same-colour shop.

    Stops early (never retries; the next decision re-plans) when the game is over, when the road or bridge
    stock cannot pay for the next stroke, or when a stroke leaves any of its steps unlinked.
    """
    for stroke in cand.strokes:
        if session.done:
            break
        cells = stroke_cells(stroke)
        state = session.state
        bridge_stock = state.inventory[1] if len(state.inventory) > 1 else 0
        if _new_tiles(state, cells) > state.inventory[0] or _new_spans(state, cells) > bridge_stock:
            break
        _, state = session.command(stroke.request())
        if not all(_linked(state, a, b) for a, b in zip(cells, cells[1:])):
            break
    house = next(b for b in session.state.buildings if b.id == cand.house_id)
    return session.state.house_connected(house)


def remove_tile(session: GameSession, cell: Cell) -> bool:
    """Remove one road tile (build with tool "Remove", one command + 20 ticks). Returns whether it was accepted.

    The tile is released and refunded at once if no car is committed to it; otherwise it is closed to new
    routes and released when those cars are home (PLAN.md section 3.4).
    """
    accepted, _ = session.command({"command": "build", "tool": "Remove", "x": cell[0], "y": cell[1]})
    return accepted


def take_offer(session: GameSession, choice: int) -> bool:
    """Choose upgrade offer `choice` (one command + 20 ticks). Returns whether the host accepted it."""
    accepted, _ = session.command({"command": "upgrade", "choice": choice})
    return accepted
