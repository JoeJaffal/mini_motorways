"""Phase 2 task 1: features v2 (candidate, global, offer), DemandTracker, per-game memory and game metrics.

Hand-made states use helpers.make_obs (no host). The host-marked tests pin Phase 1 behaviour: the games of
HandRule / SeparatedPreference / DoNothing must stay byte-identical to commit 87256e6.
"""
import hashlib
import json
import math
import os

import pytest

from evolved_rules import agent
from evolved_rules.agent import GameResult, play_game, trips_per_tile
from evolved_rules.candidates import RouteCandidate
from evolved_rules.evaluate import run_reference
from evolved_rules.features import (
    CARS_PER_HOUSE, OFFER_PERIOD_S, TRIP_OVERHEAD_S, DemandTracker, GameMemory, candidate_features, disconnected_components,
    global_features, offer_features, route_cost,
)
from evolved_rules.rules import DoNothing, HandRule, SeparatedPreference
from evolved_rules.session import GameSession
from evolved_rules.state import DIRS, Offer, parse_observation
from evolved_rules.host import PRE_VERSIONING
from evolved_rules.tests.helpers import SIM7, for_simulator, house, make_obs, shop

E, SE, S, SW, W_, NW, N, NE = range(8)

CANDIDATE_V2 = ["path_cost_s", "house_served", "shop_demand", "shop_unassigned", "shop_capacity",
                "shop_overcrowded", "shop_rate", "shop_houses", "colour_margin",
                # gp-3 traffic inputs
                "is_clean", "near_shop_junctions", "ends_near_shop", "shop_doorstep_degree", "shop_heading",
                "shop_stuck"]
GLOBAL_V2 = ["pending_refunds", "next_offer_s", "disconnected_components", "unserved_shops", "edge_distance",
             "worst_overcrowded", "worst_margin", "shops", "houses",
             # gp-3 traffic inputs
             "worst_doorstep_degree", "most_stuck_near_shop", "stuck_cars"]


def _links(*cells):
    """Road masks for a polyline of adjacent cells, linked both ways (as TrafficWorld.Link does)."""
    roads: dict = {}
    for a, b in zip(cells, cells[1:]):
        d = DIRS.index((b[0] - a[0], b[1] - a[1]))
        roads[a] = roads.get(a, 0) | 1 << d
        roads[b] = roads.get(b, 0) | 1 << ((d + 4) % 8)
    return roads


def _merge(*roads):
    out: dict = {}
    for r in roads:
        for c, m in r.items():
            out[c] = out.get(c, 0) | m
    return out


def _cand(path, shop_ids, house_id=1, kind="direct"):
    return RouteCandidate(kind=kind, house_id=house_id, shop_ids=tuple(shop_ids), path=tuple(path), tiles_needed=1,
                          bridges_needed=0, turns=0, new_junctions=0, shared_cells=0, strokes=())


def _row(x0, x1, y):
    return [(x, y) for x in range(x0, x1 + 1)]


def _shop(id, color, x, y, demand=0, reserved=0, over=0.0):
    """A 2x2 shop whose single entrance (x, y + 1) faces west: its outside cell is (x - 1, y + 1)."""
    d = shop(id, color, x, y, 2, 2, [(x, y + 1, W_)])
    d["demand"], d["reserved"], d["overcrowdedFor"] = demand, reserved, over
    return d


# --- key sets ------------------------------------------------------------------------------------------------

def test_new_keys_are_appended_after_the_phase1_keys():
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 20, 11, E)]))
    f = candidate_features(s, _cand(_row(20, 29, 11), (5,)))
    assert list(f)[9:] == CANDIDATE_V2
    assert list(global_features(s))[4:] == GLOBAL_V2
    assert list(offer_features(Offer(0, 1, 1, 20), s))[8:] == ["stock_of_type"]
    assert all(isinstance(v, float) and math.isfinite(v) for v in [*f.values(), *global_features(s).values()])


# --- path_cost_s and route_cost ------------------------------------------------------------------------------

def test_route_cost_straight_turn_diagonal_and_sharp():
    s = parse_observation(make_obs())
    assert route_cost(s, ((5, 5),)) == 0.0
    assert route_cost(s, tuple(_row(5, 9, 5))) == 8.0  # 4 orthogonal steps
    # E, E, then S (a 90 degree turn: x1.5), then SE (45 degrees from S: no factor, diagonal 2.83)
    assert route_cost(s, ((5, 5), (6, 5), (7, 5), (7, 6), (8, 7))) == pytest.approx(2 + 2 + 3 + 2.83)
    # E then SW: a 135 degree turn costs x3 on the diagonal step
    assert route_cost(s, ((5, 5), (6, 5), (5, 6))) == pytest.approx(2 + 2.83 * 3)


def test_route_cost_doubles_a_step_into_a_new_junction():
    # A vertical road through (25, 11): linking (24, 11) to it gives it 3 links, so that step costs 2 x 2.
    s = parse_observation(make_obs(roads=_links((25, 10), (25, 11), (25, 12))))
    assert route_cost(s, ((23, 11), (24, 11), (25, 11))) == 2 + 4
    # entering the end cell (25, 10) adds 1 link to its 1: degree 2, no junction
    assert route_cost(s, ((25, 8), (25, 9), (25, 10))) == 4


def test_path_cost_direct_route_adds_the_step_into_the_shop():
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 20, 11, E)]))
    f = candidate_features(s, _cand(_row(20, 29, 11), (5,)))  # 9 steps to the outside cell (29, 11)
    assert f["path_cost_s"] == 18 + 2


def test_path_cost_direct_route_counts_the_access_link_toward_the_end_junction():
    # The outside cell (29, 11) already has a road south to (29, 12), not linked to the shop. The draw links it
    # west (to the path) and east (into the access cell (30, 11)): 3 links, so the step into it costs x2.
    roads = _links((29, 11), (29, 12))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 20, 11, E)], roads=roads))
    f = candidate_features(s, _cand(_row(20, 29, 11), (5,)))
    assert f["path_cost_s"] == 16 + 4 + 2
    assert route_cost(s, tuple(_row(20, 29, 11))) == 18  # without the exit link the end has only 2 links
    assert route_cost(s, tuple(_row(20, 29, 11)), exit_cell=(30, 11)) == 20


def test_path_cost_attach_route_continues_over_existing_roads():
    # Shop 5's entrance (30, 11) is linked west to (27, 11); house 2 (also colour 0) hangs on that road.
    roads = _links((27, 11), (28, 11), (29, 11), (30, 11))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 20, 11, E)], roads=roads))
    f = candidate_features(s, _cand(_row(20, 27, 11), (5,), kind="attach"))
    assert f["path_cost_s"] == 14 + 6  # 7 new steps, then (27,11) -> (30,11): 3 steps, no junctions


def test_target_shop_is_the_cheapest_reached_then_lowest_id():
    # Shops 7 and 5 (colour 0) are both reached from the end (27, 11): shop 7 at 1 step, shop 5 at 3 steps.
    roads = _merge(_links((27, 11), (28, 11), (29, 11), (30, 11)), _links((27, 11), (27, 10)))
    near = _shop(7, 0, 27, 8, demand=2)
    near["entrances"], near["entranceDirections"], near["entrance"] = [{"x": 27, "y": 9}], [S], {"x": 27, "y": 9}
    roads = _merge(roads, _links((27, 10), (27, 9)))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10, demand=4), near, house(1, 0, 20, 11, E)],
                                   roads=roads))
    f = candidate_features(s, _cand(_row(20, 27, 11), (5, 7), kind="attach"))
    # (27, 11) has 3 links once the path joins (E, N, and W to the path): entering it costs x2
    assert f["shop_demand"] == 2.0 and f["path_cost_s"] == 12 + 4 + 2 + 2
    # equal costs: two identical shops in mirror positions -> the lower id
    roads = _merge(_links((25, 11), (26, 11), (27, 11)), _links((25, 11), (24, 11), (23, 11)))
    a = _shop(9, 0, 27, 10, demand=1)
    b = shop(3, 0, 22, 10, 2, 2, [(23, 11, E)])  # entrance (23, 11): 2 steps west of (25, 11), as shop 9 east
    b["demand"] = 6
    s = parse_observation(make_obs(buildings=[a, b, house(1, 0, 25, 20, N)], roads=roads))
    f = candidate_features(s, _cand([(25, 20)] + [(25, y) for y in range(19, 10, -1)], (3, 9), kind="attach"))
    assert f["shop_demand"] == 6.0  # shop 3


def test_path_cost_with_no_reachable_shop_is_the_path_alone():
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 20, 11, E)]))
    f = candidate_features(s, _cand(_row(20, 25, 11), (5,)))  # ends nowhere near shop 5
    assert f["path_cost_s"] == 10.0 and f["shop_demand"] == f["shop_capacity"] == f["shop_houses"] == 0.0


# --- target-shop terms, house_served, colour_margin ----------------------------------------------------------

def _served_city(demand=4, reserved=1, over=12.5):
    """Shop 5 (colour 0) linked to house 2 at (28, 11); house 1 (colour 0) and house 3 (colour 1) unlinked."""
    roads = _links((28, 11), (29, 11), (30, 11))
    return make_obs(buildings=[_shop(5, 0, 30, 10, demand, reserved, over), house(1, 0, 20, 11, E),
                               house(2, 0, 28, 11, E), house(3, 1, 20, 20, E)], roads=roads)


def test_shop_terms_and_house_served():
    s = parse_observation(_served_city())
    mem = GameMemory()
    mem.observe(s)  # first sight of demand 4: 4 pins over a span floored at 20 s -> 12 per minute
    f = candidate_features(s, _cand(_row(20, 29, 11), (5,)), mem)
    assert (f["shop_demand"], f["shop_unassigned"], f["shop_capacity"], f["shop_overcrowded"]) == (4, 3, 6, 12.5)
    assert f["shop_rate"] == 12.0 and f["shop_houses"] == 1.0 and f["house_served"] == 0.0
    f2 = candidate_features(s, _cand([(28, 11), (29, 11)], (5,), house_id=2), mem)
    assert f2["house_served"] == 1.0


def test_colour_margin_supply_minus_rate():
    s = parse_observation(_served_city(demand=3))
    mem = GameMemory()
    mem.observe(s)
    # house 2: one way (28,11) -> (30,11) = 2 + 2 s; round trip 2 x 4 + 11 s; 2 cars;
    # shop rate: 3 pins at first sight over the 20 s floor = 9 per minute
    expected = CARS_PER_HOUSE * 60.0 / (2 * 4 + TRIP_OVERHEAD_S) - 9.0
    f = candidate_features(s, _cand(_row(20, 29, 11), (5,)), mem)
    assert f["colour_margin"] == pytest.approx(expected)
    g = global_features(s, mem)
    assert g["worst_margin"] == pytest.approx(expected)  # colour 1 has no shop: not counted


def test_worst_margin_is_the_minimum_over_colours_with_a_shop():
    roads = _merge(_links((28, 11), (29, 11), (30, 11)), _links((28, 21), (29, 21), (30, 21)))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10, demand=1), _shop(6, 1, 30, 20, demand=9),
                                              house(2, 0, 28, 11, E), house(4, 1, 28, 21, E)], roads=roads))
    mem = GameMemory()
    mem.observe(s)
    supply = CARS_PER_HOUSE * 60.0 / (2 * 4 + TRIP_OVERHEAD_S)
    assert global_features(s, mem)["worst_margin"] == pytest.approx(supply - 27)  # 9 pins / 20 s floor
    assert global_features(parse_observation(make_obs()))["worst_margin"] == 0.0


# --- global features -----------------------------------------------------------------------------------------

def test_pending_refunds_counts_pending_cells():
    s = parse_observation(make_obs(roads=_links((5, 5), (6, 5), (7, 5)), pending=[(6, 5), (7, 5)]))
    assert global_features(s)["pending_refunds"] == 2.0


def test_next_offer_counts_offers_taken():
    s = parse_observation(make_obs(time=300.0))
    mem = GameMemory()
    assert global_features(s, mem)["next_offer_s"] == 0.0  # 140 x 1 - 300 < 0
    mem.offers_taken = 2
    s2 = parse_observation(make_obs(time=300.0))
    assert global_features(s2, mem)["next_offer_s"] == 120.0  # 140 x 3 - 300
    assert global_features(parse_observation(make_obs(time=12.5)))["next_offer_s"] == 127.5


def _network(color_shop, color_house, y):
    """A shop of one colour and a house of another (or the same) linked on row y; ids from y."""
    return ([_shop(100 + y, color_shop, 30, y - 1), house(y, color_house, 28, y, E)],
            _links((28, y), (29, y), (30, y)))


@pytest.mark.parametrize("nets, expected", [
    ([], 0),
    ([(0, 0)], 0),  # one served network
    ([(0, 0), (1, 1)], 1),  # two networks, two colours
    ([(0, 0), (0, 0)], 0),  # two networks but one colour between them
    ([(0, 0), (0, 0), (1, 1)], 2),
    ([(0, 0), (1, 2)], 0),  # the second network matches no colour: not served
])
def test_disconnected_components(nets, expected):
    buildings, roads = [], {}
    for i, (cs, ch) in enumerate(nets):
        b, r = _network(cs, ch, 3 + 4 * i)
        buildings += b
        roads = _merge(roads, r)
    s = parse_observation(make_obs(buildings=buildings, roads=roads))
    assert disconnected_components(s) == expected
    assert global_features(s)["disconnected_components"] == float(expected)


@pytest.mark.parametrize("joined, expected", [(True, 0), (False, 1)])
def test_one_network_serving_two_colours_is_one_component(joined, expected):
    # colour 0 on row 11, colour 1 on row 13; joined by (15, 11)-(15, 12)-(15, 13) they form one network
    roads = _merge(_links(*_row(10, 20, 11)), _links(*_row(10, 20, 13)))
    if joined:
        roads = _merge(roads, _links((15, 11), (15, 12), (15, 13)))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 20, 10), _shop(6, 1, 20, 12), house(1, 0, 10, 11, E),
                                              house(2, 1, 10, 13, E)], roads=roads))
    assert disconnected_components(s) == expected


def test_unserved_shops_matches_shop_served():
    roads = _links((28, 11), (29, 11), (30, 11))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), _shop(6, 0, 40, 20), _shop(7, 1, 10, 20),
                                              house(2, 0, 28, 11, E)], roads=roads))
    g = global_features(s)
    assert g["unserved_shops"] == float(sum(1 for x in s.shops() if not s.shop_served(x))) == 2.0
    assert (g["shops"], g["houses"]) == (3.0, 1.0)


def test_edge_distance_and_worst_overcrowded():
    # playable x 5..44, y 3..26 (max exclusive); house at (8, 20): 3 from the left border; shop 2x2 at (30, 10)
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10, over=7.5), _shop(6, 1, 20, 5, over=31.0),
                                              house(1, 0, 8, 20, E)], bounds=(5, 3, 45, 27)))
    g = global_features(s)
    assert g["edge_distance"] == 2.0  # shop 6 spans y 5..6: 2 tiles from y = 3
    assert g["worst_overcrowded"] == 31.0
    empty = global_features(parse_observation(make_obs()))
    assert empty["edge_distance"] == 0.0 and empty["worst_overcrowded"] == 0.0 and empty["shops"] == 0.0


def test_house_served_and_unserved_counts_agree_with_city_state():
    """The shared component labels give the same answers as CityState's per-house searches."""
    roads = _merge(_links((28, 11), (29, 11), (30, 11)), _links((20, 11), (21, 11)), _links((10, 5), (11, 5), (12, 5)))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), _shop(6, 1, 12, 4), house(1, 0, 20, 11, E),
                                              house(2, 0, 28, 11, E), house(3, 1, 10, 5, E),
                                              house(4, 1, 40, 25, W_)], roads=roads))
    mem = GameMemory()
    for h in s.houses():
        f = candidate_features(s, _cand([h.cell], (), house_id=h.id), mem)
        assert f["house_served"] == float(s.house_connected(h))
    assert global_features(s, mem)["unserved_houses"] == 2.0  # houses 1 and 4


# --- offer features ------------------------------------------------------------------------------------------

def test_offer_stock_of_type():
    s = parse_observation(make_obs(inventory=(17, 3, 0, 2, 1, 0)))
    assert offer_features(Offer(0, 1, 1, 20), s)["stock_of_type"] == 3.0
    assert offer_features(Offer(0, 3, 2, 20), s)["stock_of_type"] == 2.0
    assert offer_features(Offer(0, 0, 0, 30), s)["stock_of_type"] == 17.0
    assert offer_features(Offer(0, 1, 1, 20))["stock_of_type"] == 0.0  # no state


# --- DemandTracker -------------------------------------------------------------------------------------------

def _demand_state(t, **demands):
    shops = []
    for i, (name, d) in enumerate(sorted(demands.items())):
        sid = int(name[1:])
        shops.append(_shop(sid, 0, 10 + 5 * i, 10, demand=d))
    return parse_observation(make_obs(buildings=shops, time=t))


def test_demand_tracker_window():
    t = DemandTracker()
    assert t.rate(5) == 0.0
    t.update(_demand_state(0.0, s5=0))
    t.update(_demand_state(10.0, s5=2))
    assert t.rate(5) == 6.0  # +2 over a 10 s span, floored at 20 s: 2 x 60 / 20
    for time, d in [(20.0, 1), (30.0, 3)]:  # a pickup at 20 (ignored), +2 at 30
        t.update(_demand_state(time, s5=d))
    assert t.rate(5) == 8.0  # +4 over the 30 s the shop has been watched, not over the full 60 s window
    t.update(_demand_state(65.0, s5=3))
    assert t.rate(5) == 4.0  # window (5, 65]
    t.update(_demand_state(70.0, s5=3))
    assert t.rate(5) == 2.0  # the +2 at 10 is at the window edge (10 <= 70 - 60): dropped
    t.update(_demand_state(90.0, s5=3))
    assert t.rate(5) == 0.0


def test_demand_tracker_first_sight_and_independent_shops():
    t = DemandTracker()
    t.update(_demand_state(0.0, s5=0))
    t.update(_demand_state(1.0, s5=1, s9=3))  # shop 9 appears holding 3 pins
    assert (t.rate(5), t.rate(9)) == (3.0, 9.0)  # both spans floored at 20 s
    t.update(_demand_state(41.0, s5=1, s9=3))
    assert (t.rate(5), t.rate(9)) == (60.0 / 41.0, 4.5)  # each shop's own span: 41 s and 40 s
    t.update(_demand_state(100.0, s5=1, s9=3, s12=2))  # a shop appearing late is not diluted by the game's age
    assert t.rate(12) == 6.0
    other = DemandTracker()
    assert other.rate(9) == 0.0


# --- per-game memory in GameSession -------------------------------------------------------------------------

class _ScriptHost:
    """Steps 1 s each. Shop 5's demand follows `demands` (one per observation); a draw spends `spend` roads;
    an accepted upgrade adds 30 roads; upgrades are accepted unless `reject_upgrades`."""

    def __init__(self, demands, spend=3, reject_upgrades=False):
        self.demands, self.spend, self.reject = demands, spend, reject_upgrades
        self.t, self.roads = 0, 25

    def _obs(self):
        d = self.demands[min(self.t, len(self.demands) - 1)]
        return make_obs(buildings=[_shop(5, 0, 30, 10, demand=d)], time=float(self.t),
                        inventory=(self.roads, 1, 0, 0, 0, 0))

    def reset(self, seed, scenario="LosAngeles"):
        self.t, self.roads = 0, 25
        return {"observation": self._obs(), "terminated": False, "truncated": False}

    def call(self, **req):
        if req["command"] == "step":
            self.t += 1
            return {"observation": self._obs(), "terminated": False, "truncated": False}
        if req["command"] == "draw":
            self.roads -= self.spend
            return {"accepted": True}
        if req["command"] == "upgrade":
            if self.reject:
                return {"accepted": False}
            self.roads += 30
            return {"accepted": True}
        raise AssertionError(req)


DRAW = {"command": "draw", "x": 1, "y": 1, "toX": 2, "toY": 1}


def test_session_memory_sees_every_observation_and_resets_per_game():
    sess = GameSession(_ScriptHost([0, 1, 2, 3, 4]), 1, record=False)
    sess.reset()
    first = sess.memory
    sess.wait()
    sess.command(DRAW)
    sess.wait()
    assert first.demand.rate(5) == 9.0  # 3 increases after reset, a wait and a command; span floored at 20 s
    sess.reset()
    assert sess.memory is not first and sess.memory.demand.rate(5) == 0.0 and sess.memory.offers_taken == 0
    assert sess.tiles_built == 0


def test_session_counts_accepted_offers_and_tiles_built():
    sess = GameSession(_ScriptHost([0], spend=4), 1, record=False)
    sess.reset()
    sess.command(DRAW)
    sess.command({"command": "upgrade", "choice": 0})
    sess.command(DRAW)
    assert sess.tiles_built == 8 and sess.memory.offers_taken == 1  # the +30 from the offer is not a refund
    rej = GameSession(_ScriptHost([0], reject_upgrades=True), 1, record=False)
    rej.reset()
    rej.command({"command": "upgrade", "choice": 0})
    assert rej.memory.offers_taken == 0


def test_play_game_uses_a_fresh_memory_per_game(monkeypatch):
    memories = []

    def fake_decide(session, policy):
        memories.append(session.memory)
        session.terminated = True
    monkeypatch.setattr(agent, "decide", fake_decide)
    host = _ScriptHost([0, 2])
    play_game(host, 1, HandRule(), record=False)
    play_game(host, 1, HandRule(), record=False)
    assert len(memories) == 2 and memories[0] is not memories[1]


# --- game metrics --------------------------------------------------------------------------------------------

def test_trips_per_tile_and_summary_fields():
    assert trips_per_tile(57, 37) == 57 / 37 and trips_per_tile(5, 0) == 0.0
    r = GameResult(1, 2.0, 0, 3, {"wait": 3}, 0.0, 0.0, False, True, 7, "LosAngeles", True, None, None, None)
    assert (r.tiles_built, r.trips_per_tile) == (0, 0.0)
    assert list(r.summary())[-3:] == ["tiles_built", "trips_per_tile", "simulator_version"]


def test_play_game_reports_tiles_built(monkeypatch):
    def fake_decide(session, policy):
        session.command(DRAW)
        session.command(DRAW)
        session.terminated = True
    monkeypatch.setattr(agent, "decide", fake_decide)
    r = play_game(_ScriptHost([0], spend=5), 1, HandRule(), record=False)
    assert r.tiles_built == 10 and r.trips_per_tile == 0.0 and r.summary()["tiles_built"] == 10


class _RefHost(_ScriptHost):
    """run_reference fake: each reference spends 6 roads (the one at t >= 2 is rejected but still spends 2)."""

    def call(self, **req):
        if req["command"] == "reference":
            self.roads -= 6 if self.t < 2 else 2
            return {"accepted": self.t < 2}
        return super().call(**req)


def test_run_reference_reports_tiles_built():
    r = run_reference(_RefHost([0]), 1, cap_s=12.0)  # references at t = 0 and t = 10
    assert r["tiles_built"] == 8 and r["trips_per_tile"] == 0.0


# --- real games: Phase 1 frozen, features on real states -----------------------------------------------------

# name seed trips commands sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")))
# Old simulator: produced by agent.play_game at commit 87256e6 (output/evolved_rules/phase1-fingerprints.txt).
# Simulator 2026-11-08.7: produced by agent.play_game at gp-5's merge of main 8025a60.
PHASE1_GAMES_OLD = [
    ("hand", 1000, 90, 503, "ee5fd682d0e79e1ba71c24634ab3db6836cbb7cf7cb99acecbb96153010637c2"),
    ("hand", 2000, 57, 405, "129fcde363f3ebff72dddb1aadb52f9820c498ef75527f7a8a57ac82ea055fea"),
    ("hand", 2004, 288, 867, "e0d2cd28f861fb36173ee9c879835564306cbea481077151a7f8d695e3ff5ef6"),
    ("separated", 1000, 34, 367, "245aff09e186118852d2dfa9a45a7af66c623c50672b3d9af80705a29f770fa4"),
    ("separated", 2000, 135, 571, "39a9c5a3d54437325de8de0debc5be48ac0f269cca9c7944874a59b4d668b17b"),
    ("separated", 2004, 302, 893, "c2cfc82096382abb0fcc580151b9e8f5f8d6f097bb987f25a70105e3f1f34094"),
    ("nothing", 2000, 0, 141, "286e175d407a7b30394169705d47c5c1332ab526bf6d1241441fa68887b4b15b"),
]
PHASE1_GAMES_SIM7 = [
    ("hand", 1000, 394, 981, "78442c3e5f33d9455b3fa9844ea89b4502c8aa6c5eb9844fb8002df20b5b8c93"),
    ("hand", 2000, 210, 691, "84d98db590141f3f9506a501c521e4f3e31b00c5421609bdaba909c997ce84b2"),
    ("hand", 2004, 381, 932, "f1314847b9d46b769ca5f60e551df9753267b17b9626fe6f4a06dfd13f25b4ce"),
    ("separated", 1000, 405, 979, "eef0ac694ad59fda56875cc22e6cbd1189eb447d6301bd6872862d716d15629d"),
    ("separated", 2000, 476, 1030, "67fa39584cbf57932b7e73c8ded8724ea399c8863760d347358fa7214ce3af39"),
    ("separated", 2004, 499, 1057, "68d08981cf5918c7b1785217f80428daa3cba6ca05c3737b68855871b2676d4e"),
    ("nothing", 2000, 0, 140, "21624c226b17e15d0a457a5f632abdae1ccf9302ad816b4d28c4eba41e09ec2c"),
]
PHASE1_BY_SIMULATOR = {PRE_VERSIONING: {(g[0], g[1]): g[2:] for g in PHASE1_GAMES_OLD},
                       SIM7: {(g[0], g[1]): g[2:] for g in PHASE1_GAMES_SIM7}}
PHASE1_GAMES = [(g[0], g[1]) for g in PHASE1_GAMES_OLD]  # (name, seed); the pinned values come from phase1_pin
# road tiles hand spends on seed 2000: 37 counted by hand on the old final map; 52 from play_game on .7
HAND_2000_TILES = {PRE_VERSIONING: 37, SIM7: 52}


def phase1_pin(name: str, seed: int) -> tuple:
    """(trips, commands, sha) of a Phase 1 game on the simulator under test (skips if none is pinned)."""
    return for_simulator(PHASE1_BY_SIMULATOR)[(name, seed)]
FAST_GAMES = {("hand", 2000), ("separated", 2000)}
SLOW = os.environ.get("EVOLVED_RULES_SLOW") == "1"
POLICIES = {"hand": HandRule, "separated": SeparatedPreference, "nothing": DoNothing}


@pytest.mark.host
@pytest.mark.parametrize("name, seed", [g for g in PHASE1_GAMES if SLOW or g in FAST_GAMES])
def test_phase1_games_byte_identical(host, name, seed):
    """Set EVOLVED_RULES_SLOW=1 to check all 7 games; the default run plays hand and separated on seed 2000."""
    trips, commands, sha = phase1_pin(name, seed)
    r = play_game(host, seed, POLICIES[name]())
    digest = hashlib.sha256(json.dumps(r.recording["actions"], sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    assert (r.trips, r.commands, digest) == (trips, commands, sha)
    if (name, seed) == ("hand", 2000):
        tiles = for_simulator(HAND_2000_TILES)  # this game never removes roads
        assert r.tiles_built == tiles and r.trips_per_tile == trips / tiles


class _Probe(HandRule):
    """The hand rule, logging every feature dict it is shown (Phase 2 features included)."""

    name = "probe"

    def __init__(self):
        self.log = []

    def priority(self, f):
        self.log.append(("p", tuple(sorted(f.items()))))
        return super().priority(f)

    def hold(self, g):
        self.log.append(("h", tuple(sorted(g.items()))))
        return super().hold(g)

    def upgrade(self, f):
        self.log.append(("u", tuple(sorted(f.items()))))
        return super().upgrade(f)


@pytest.mark.host
def test_features_on_real_games_are_finite_and_do_not_leak_between_games(host):
    """Game A, game B, game A again on one host: A's feature stream repeats exactly (no memory carried over)."""
    runs = []
    for seed in (2000, 2004, 2000):
        p = _Probe()
        play_game(host, seed, p, cap_s=200.0, record=False)
        runs.append(p.log)
    assert runs[0] == runs[2] and runs[0] != runs[1]
    values = [v for _, items in runs[1] for _, v in items]
    assert values and all(math.isfinite(v) for v in values)
    keys = {k for kind, items in runs[1] if kind == "h" for k, _ in items}
    assert set(GLOBAL_V2) <= keys
    # decide() must hand the features the session's memory, not a throwaway one: with a throwaway memory
    # shop_rate is always 0, and next_offer_s is 0 after t = 140 because no accepted offer is counted.
    priority = [dict(items) for kind, items in runs[1] if kind == "p"]
    hold = [dict(items) for kind, items in runs[1] if kind == "h"]
    assert any(d["shop_rate"] > 0 for d in priority)
    assert any(d["next_offer_s"] > 0 for d in hold if d["time"] > OFFER_PERIOD_S)
