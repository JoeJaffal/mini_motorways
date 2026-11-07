"""gp-4 step 1: the new build commands are allowed, roundabouts and car waiting times are parsed (task 1), routes
use roundabout rings (task 2), and placement candidates for lights and roundabouts (task 3)."""
from dataclasses import replace

from evolved_rules import candidates
from evolved_rules.candidates import link_degree, route_candidates, unserved_targets
from evolved_rules.placement import (
    LIGHT, PLACE_CAP, PLACE_RADIUS, ROUNDABOUT, cars_near, is_stopped, placement_candidates, ring_new_links, ring_of,
)
from evolved_rules.session import _replayable
from evolved_rules.state import Car, Roundabout, parse_observation
from evolved_rules.tests.helpers import house, make_obs, shop
from evolved_rules.tests.test_features import _links, _merge, _row, _shop
from evolved_rules.tests.test_gp3 import ROADS, _car, _state

E, S, N = 0, 2, 6


def test_only_the_new_build_tools_are_allowed():
    ok = [{"command": "build", "tool": t, "x": 1, "y": 1} for t in ("Remove", "TrafficLight", "Roundabout")]
    bad = [{"command": "build", "tool": t, "x": 1, "y": 1} for t in ("trafficlight", "Road", "Bridge", None)]
    bad += [{"command": "connect"}, {"command": "motorway"}]
    assert all(_replayable(r) for r in ok) and not any(_replayable(r) for r in bad)


def test_roundabouts_and_car_waiting_are_parsed():
    obs = make_obs(roundabouts=[((25, 11), [(25, 10), (24, 11), (25, 12), (26, 11)])],
                   vehicles=[{"color": 0, "stage": "Outbound", "waiting": 4.5}])
    s = parse_observation(obs)
    assert s.roundabouts == (Roundabout((25, 11), ((25, 10), (24, 11), (25, 12), (26, 11)), False),)
    assert s.centres() == frozenset({(25, 11)})
    assert s.ring_next()[(24, 11)] == (25, 12) and s.ring_next()[(26, 11)] == (25, 10)
    assert s.cars[0].waiting == 4.5


def test_an_observation_without_roundabouts_parses_to_none():
    obs = make_obs(); obs.pop("roundabouts", None)
    assert parse_observation(obs).roundabouts == ()


# --- task 2: routes around and through roundabouts ------------------------------------------------------------

# test_gp3's layout (red shop 5 at (30, 10), doorstep (29, 11); red house 1 at (19, 11) facing east, unlinked) with a
# roundabout in the way: centre (25, 11), ring N (25, 10), W (24, 11), S (25, 12), E (26, 11). Row 11 is road from
# 20 to 23 (linked into ring W) and from 27 to 29 (linked from ring E to the doorstep and the shop entrance).
_RING = [(25, 10), (24, 11), (25, 12), (26, 11)]
_ROUNDABOUT_ROADS = _merge(_links(*_row(20, 24, 11)), _links(*_row(26, 30, 11)), _links(*_RING, _RING[0]))


def _roundabout_state():
    return parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 19, 11, E)],
                                      roads=_ROUNDABOUT_ROADS, roundabouts=[((25, 11), _RING)]))


def test_a_route_uses_the_ring_in_driving_order_and_never_the_centre():
    s = _roundabout_state()
    paths = [c.path for c in route_candidates(s, *unserved_targets(s)[0])]
    assert paths and all((25, 11) not in p for p in paths)
    through = [p for p in paths if (24, 11) in p and (26, 11) in p]
    assert through and all((25, 12) in p and (25, 10) not in p for p in through)  # W -> S -> E, not W -> N -> E


def test_the_centre_is_not_road_and_ring_cells_are():
    s = _roundabout_state()
    assert not candidates._is_road(s, (25, 11)) and candidates._is_road(s, (24, 11))
    assert not candidates._enterable(s, (25, 11)) and candidates._enterable(s, (24, 11))


# --- task 3: placement candidates -----------------------------------------------------------------------------
# test_gp3's layout: the doorstep (29, 11) carries 4 links, (28, 11) carries 3; house 1 at (19, 11) faces east, so
# its outside cell is (20, 11).

def _gp3_obs(**kw):
    return parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 19, 11, E)], roads=ROADS, **kw))


def _centres(s, **kw):
    return [c.cell for c in placement_candidates(s, **{"lights": False, "roundabouts": True, **kw})]


def test_light_spots_are_live_junctions_only():
    s = _state()                                   # test_gp3 layout: the doorstep (29, 11) has 4 links
    cells = [c.cell for c in placement_candidates(s, lights=True, roundabouts=False)]
    assert (29, 11) in cells and all(link_degree(s, c) >= 3 for c in cells)
    assert sorted(cells) == [(28, 11), (29, 11)]
    # a light converts its own road tile and the build refunds the road, so it costs the network nothing
    assert all(c.tool == LIGHT and c.tiles_lost == 0 and c.new_links == 0 and not c.joins_separated
               for c in placement_candidates(s, lights=True, roundabouts=False))
    assert placement_candidates(s, lights=False, roundabouts=False) == []


def test_a_light_spot_is_an_ordinary_playable_road_that_is_not_pending():
    assert (29, 11) in [c.cell for c in placement_candidates(_gp3_obs(), True, False)]
    for kw in ({"pending": [(29, 11)]}, {"infra": {(29, 11): 2}}, {"infra": {(29, 11): 3}}, {"infra": {(29, 11): 4}},
               {"bounds": (0, 0, 29, 30)}):
        assert (29, 11) not in [c.cell for c in placement_candidates(_gp3_obs(**kw), True, False)], kw
    # a pending neighbour no longer counts as a live link: (28, 11) drops from 3 links to 2, (29, 11) keeps 4
    cells = [c.cell for c in placement_candidates(_gp3_obs(pending=[(28, 10)]), True, False)]
    assert cells == [(29, 11)]


def test_no_roundabout_over_a_doorstep_or_driveway_cell():
    s = _state()
    cands = placement_candidates(s, lights=False, roundabouts=True)
    assert cands
    for c in cands:
        assert (29, 11) not in c.footprint and (20, 11) not in c.footprint   # doorstep; house 1's outside cell
    centres = [c.cell for c in cands]
    assert (28, 12) in centres and (29, 11) not in centres and (28, 11) not in centres


def test_a_houses_outside_cell_removes_every_roundabout_that_covers_it():
    # house 2 at (27, 13) faces north: its outside cell is (27, 12), the west ring cell of centre (28, 12)
    assert (28, 12) in _centres(_state())
    assert (28, 12) not in _centres(_state(extra=[house(2, 0, 27, 13, N)]))


def test_roundabout_spots_mirror_the_host_footprint_rules():
    assert (28, 12) in _centres(_gp3_obs())
    blocked = {
        "water": {"terrain": {(27, 12): 1}}, "blocked terrain": {"terrain": {(28, 13): 2}},
        "pending": {"pending": [(29, 12)]}, "traffic light": {"infra": {(28, 11): 4}},
        "roundabout": {"roundabouts": [((28, 14), [(28, 13), (27, 14), (28, 15), (29, 14)])]},
        "outside the playable area": {"bounds": (0, 0, 29, 30)},
    }
    for name, kw in blocked.items():
        assert (28, 12) not in _centres(_gp3_obs(**kw)), name
    # a building in the footprint: a house on the south ring cell (28, 13)
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 19, 11, E), house(2, 0, 28, 13, E)],
                                   roads=ROADS))
    assert (28, 12) not in _centres(s)
    # no ring may leave the grid: a junction on the top edge is only reachable from centres inside it
    edge = parse_observation(make_obs(roads=_merge(_links(*_row(0, 4, 0)), _links((1, 0), (1, 1)))))
    centres = _centres(edge)
    assert centres and (1, 0) not in centres and all(1 <= x <= 48 and 1 <= y <= 28 for x, y in centres)


def test_a_roundabout_spot_must_be_useful():
    assert placement_candidates(parse_observation(make_obs()), True, True) == []   # no junction, no doorstep
    centres = _centres(_state())
    assert (28, 13) in centres and (30, 13) in centres   # a ring or centre cell within 1 of the doorstep (29, 11)
    assert (31, 13) not in centres and (22, 11) not in centres   # nothing within reach: no junction, no doorstep


# (ring cell, neighbour) pairs of the host rule for centre (25, 12), written by hand (TrafficWorld.cs:198-203).
# Ring N (25, 11), W (24, 12), S (25, 13), E (26, 12); a neighbour counts when it is in the grid, not in the
# footprint, has infrastructure, is not a roundabout, and is not linked to the ring cell yet. Red road: row 11 from
# the red shop's entrance (19, 11) to (24, 11). Blue road: row 13 from (25, 13) to the blue shop's entrance (28, 13).
#   N (25, 11): W (24, 11) is road, not linked                          -> ((25, 11), (24, 11))
#   W (24, 12): NW (23, 11) and N (24, 11) are road, not linked         -> ((24, 12), (23, 11)), ((24, 12), (24, 11))
#   S (25, 13): E (26, 13) is road but already linked (its own road)    -> none
#   E (26, 12): SE (27, 13) and S (26, 13) are road, not linked         -> ((26, 12), (27, 13)), ((26, 12), (26, 13))
EXPECTED_LINKS = [
    ((25, 11), (24, 11)),
    ((24, 12), (23, 11)), ((24, 12), (24, 11)),
    ((26, 12), (27, 13)), ((26, 12), (26, 13)),
]


def _two_colour_state(second_colour=1, stub=None):
    red = shop(6, 0, 18, 10, 2, 2, [(19, 11, E)])          # entrance (19, 11) facing east, outside (20, 11)
    other = _shop(7, second_colour, 28, 12)                # entrance (28, 13) facing west, outside (27, 13)
    roads = _merge(_links(*_row(19, 24, 11)), _links(*_row(25, 28, 13)), *([_links(*stub)] if stub else []))
    return parse_observation(make_obs(buildings=[red, other], roads=roads))


def test_ring_new_links_mirror_the_host_and_flag_merged_colours():
    s = _two_colour_state()   # red road on row 11 ending at (24, 11); blue road on row 13 ending at (25, 13)
    cand = next(c for c in placement_candidates(s, False, True) if c.cell == (25, 12))
    assert ring_new_links(s, (25, 12)) == EXPECTED_LINKS   # exact pairs for this layout, in (ring cell, dir) order
    assert cand.joins_separated and cand.new_links == len(EXPECTED_LINKS)
    assert cand.footprint == ((25, 12), (25, 11), (24, 12), (25, 13), (26, 12)) == ((25, 12), *ring_of((25, 12)))
    assert (cand.tool, cand.tiles_lost, cand.degree) == (ROUNDABOUT, 1, 1)


def test_a_roundabout_inside_one_network_does_not_join_separated_networks():
    s = _state()
    cand = next(c for c in placement_candidates(s, False, True) if c.cell == (28, 12))
    # footprint (28, 12), N (28, 11), W (27, 12), S (28, 13), E (29, 12): two road cells, the junction among them
    assert (cand.tiles_lost, cand.degree) == (2, 3)
    # N (28, 11) gains only the unlinked diagonal (29, 10); W (27, 12) reaches (26, 11) and (27, 11) of row 11; the E
    # ring cell's links to (29, 11) and its own road already exist, so they are not new
    assert ring_new_links(s, (28, 12)) == [((28, 11), (29, 10)), ((27, 12), (26, 11)), ((27, 12), (27, 11))]
    assert cand.new_links == 3 and not cand.joins_separated
    assert not any(c.joins_separated for c in placement_candidates(s, False, True))


def test_two_networks_of_one_colour_are_not_a_separated_join():
    s = _two_colour_state(second_colour=0)                 # both roads serve red only
    cand = next(c for c in placement_candidates(s, False, True) if c.cell == (25, 12))
    assert cand.new_links == len(EXPECTED_LINKS) and not cand.joins_separated


def test_one_network_serving_two_colours_is_not_a_separated_join_either():
    # a blue shop whose entrance (28, 8) hangs off the same road network as red shop 5: one network, two colours
    blue = shop(7, 1, 28, 7, 2, 2, [(28, 8, S)])          # outside (28, 9)
    roads = _merge(ROADS, _links((28, 10), (28, 9), (28, 8)))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 19, 11, E), blue], roads=roads))
    cands = placement_candidates(s, False, True)
    assert any(c.cell == (28, 12) for c in cands)
    assert not any(c.joins_separated for c in cands)


def test_a_stub_that_serves_no_colour_is_not_a_network_to_join():
    # the one-network layout above plus a stub (25, 12)-(26, 12) with no shop access: centre (28, 12) links to it
    # through its west ring cell (27, 12), so it touches two networks, but only one of them serves any colour
    blue = shop(7, 1, 28, 7, 2, 2, [(28, 8, S)])
    roads = _merge(ROADS, _links((28, 10), (28, 9), (28, 8)), _links((26, 12), (25, 12)))
    s = parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 19, 11, E), blue], roads=roads))
    assert ((27, 12), (26, 12)) in ring_new_links(s, (28, 12))
    cand = next(c for c in placement_candidates(s, False, True) if c.cell == (28, 12))
    assert not cand.joins_separated
    # beside two networks that do serve a colour each, a stub changes nothing: red + blue still joins
    stubbed = _two_colour_state(stub=[(27, 11), (27, 10)])
    assert ((26, 12), (27, 11)) in ring_new_links(stubbed, (25, 12))
    assert next(c for c in placement_candidates(stubbed, False, True) if c.cell == (25, 12)).joins_separated
    # two networks of one colour plus a stub: still no join
    one = _two_colour_state(second_colour=0, stub=[(27, 11), (27, 10)])
    assert not next(c for c in placement_candidates(one, False, True) if c.cell == (25, 12)).joins_separated


# --- order and cap ----------------------------------------------------------------------------------------------

def test_stopped_and_cars_near_use_the_stage_the_speed_and_the_cell():
    assert is_stopped(Car(0, "Outbound", 1, 5, 29.5, 11.5, 0.0))
    assert is_stopped(Car(0, "Returning", 1, 5, 1.0, 1.0, 0.049))
    assert not is_stopped(Car(0, "Outbound", 1, 5, 29.5, 11.5, 0.05))          # strictly below STUCK_SPEED
    assert not is_stopped(Car(0, "Parking", 1, 5, 29.5, 11.5, 0.0))
    assert not is_stopped(Car(0, "Home", 1, 5, 0.5, 0.5, 0.0))
    cars = (Car(0, "Outbound", 1, 5, 31.99, 13.0, 0.0),   # cell (31, 13): 2 from (29, 11), inside
            Car(0, "Outbound", 1, 5, 32.0, 11.0, 0.0),    # cell (32, 11): 3 away, outside
            Car(0, "Home", 1, 5, 27.0, 9.2, 1.0),         # cell (27, 9): 2 away, inside, not stopped
            Car(0, "Outbound", 1, 5, 28.99, 10.99, 0.0))  # cell (28, 10): inside
    s = replace(parse_observation(make_obs()), cars=cars)
    assert PLACE_RADIUS == 2
    assert cars_near(s, ((29, 11),)) == (cars[0], cars[2], cars[3])                 # observation order
    # a car near two footprint cells is listed once, whatever the footprint order
    assert cars_near(s, ((29, 11), (29, 14))) == cars_near(s, ((29, 14), (29, 11))) == (cars[0], cars[2], cars[3])
    assert cars_near(parse_observation(make_obs()), ((29, 11),)) == ()


def test_spots_are_ordered_by_stopped_cars_then_position():
    # a stopped car in cell (31, 12): within 2 of the light spot (29, 11) but 3 from (28, 11)
    s = _state(vehicles=[_car("Outbound", 31.5, 12.5, 0.0)])
    assert [c.cell for c in placement_candidates(s, True, False)] == [(29, 11), (28, 11)]
    # in cell (29, 11) it is within 2 of both: equal counts, so y then x decides
    s = _state(vehicles=[_car("Outbound", 29.5, 11.5, 0.0)])
    assert [c.cell for c in placement_candidates(s, True, False)] == [(28, 11), (29, 11)]
    assert [c.cell for c in placement_candidates(_state(), True, False)] == [(28, 11), (29, 11)]


def test_a_stopped_car_outranks_any_number_of_moving_cars():
    moving = [_car("Outbound", 26.5, 11.5, 0.5)] * 2       # cell (26, 11): within 2 of (28, 11) only
    stopped = _car("Outbound", 31.5, 12.5, 0.0)            # within 2 of (29, 11) only
    with_stopped = placement_candidates(_state(vehicles=[*moving, stopped]), True, False)
    assert [c.cell for c in with_stopped] == [(29, 11), (28, 11)]
    parked = _car("Parking", 26.5, 11.5, 0.0)              # parked cars count as cars, never as stopped
    with_parked = placement_candidates(_state(vehicles=[*moving, parked]), True, False)
    assert [c.cell for c in with_parked] == [(28, 11), (29, 11)]
    assert [c.cell for c in placement_candidates(_state(vehicles=[parked]), True, False)] == [(28, 11), (29, 11)]


def test_lights_come_before_roundabouts_when_nothing_else_differs():
    cands = placement_candidates(_state(), True, True)
    tools = [c.tool for c in cands]
    assert LIGHT == "TrafficLight" and ROUNDABOUT == "Roundabout"
    assert len(cands) > 2 and tools[:2] == [LIGHT, LIGHT] and set(tools[2:]) == {ROUNDABOUT}
    assert [(c.cell[1], c.cell[0]) for c in cands[2:]] == sorted((c.cell[1], c.cell[0]) for c in cands[2:])


def test_the_list_is_cut_to_the_cap_after_sorting():
    comb = _merge(_links(*_row(2, 46, 11)), *[_links((x, 11), (x, 12)) for x in range(3, 46)])   # 43 junctions
    s = parse_observation(make_obs(roads=comb, vehicles=[_car("Outbound", 45.5, 11.5, 0.0)]))
    out = placement_candidates(s, True, False)
    assert PLACE_CAP == 32 and len(out) == PLACE_CAP
    # the stopped car in cell (45, 11) makes (43..45, 11) the first three; then plain (y, x) order, cut at the cap
    assert [c.cell for c in out] == [(43, 11), (44, 11), (45, 11)] + [(x, 11) for x in range(3, 32)]
