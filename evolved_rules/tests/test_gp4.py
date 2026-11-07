"""gp-4 step 1: the new build commands are allowed, roundabouts and car waiting times are parsed (task 1), routes
use roundabout rings (task 2), placement candidates for lights and roundabouts (task 3), their features (task 4),
the placement step (task 5) and the hand rules with their policy names (task 6)."""
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from evolved_rules import agent, autopsy, candidates
from evolved_rules import evaluate as ev
from evolved_rules.agent import EventTracker, decide, places, play_game
from evolved_rules.candidates import link_degree, removal_candidates, route_candidates, unserved_targets
from evolved_rules.features import (
    GameMemory, candidate_features, global_features, is_driving, is_stuck, offer_features, placement_features,
    removal_features,
)
from evolved_rules.gp import TreePolicy
from evolved_rules.placement import (
    LIGHT, PLACE_CAP, PLACE_RADIUS, ROUNDABOUT, PlacementCandidate, cars_near, is_stopped, placement_candidates,
    ring_new_links, ring_of,
)
from evolved_rules.rules import (
    CleanHand, CleanRemoveHand, GPHand, HandRule, LightHand, LightRoundHand, RoundHand, SeparatedPreference,
    hand_place, package_upgrade,
)
from evolved_rules.session import _replayable
from evolved_rules.state import Car, Offer, Roundabout, parse_observation
from evolved_rules.tests.helpers import house, make_obs, shop
from evolved_rules.tests.test_evaluate import fake_runs  # noqa: F401  (a fixture)
from evolved_rules.tests.test_features import _links, _merge, _row, _shop
from evolved_rules.tests.test_gp3 import GP2_BEST, ROADS, _car, _Session, _state

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

def test_driving_and_stuck_are_one_predicate_for_features_and_placement():
    assert is_stopped is is_stuck                                              # the step-1 name is an alias
    stages = ("Outbound", "EnteringParking", "Returning", "Home", "Parking")
    assert [is_driving(Car(0, st, 1, 5, 1.0, 1.0, 0.0)) for st in stages] == [True, True, True, False, False]
    assert is_stuck(Car(0, "EnteringParking", 1, 5, 1.0, 1.0, 0.0))
    assert not is_stuck(Car(0, "Home", 1, 5, 1.0, 1.0, 0.0))
    assert not is_stuck(Car(0, "Parking", 1, 5, 1.0, 1.0, 0.0))
    assert not is_stuck(Car(0, "Outbound", 1, 5, 1.0, 1.0, 0.05))              # strictly below STUCK_SPEED


def test_stopped_and_cars_near_use_the_stage_the_speed_and_the_cell():
    assert is_stopped(Car(0, "Outbound", 1, 5, 29.5, 11.5, 0.0))
    assert is_stopped(Car(0, "Returning", 1, 5, 1.0, 1.0, 0.049))
    assert not is_stopped(Car(0, "Outbound", 1, 5, 29.5, 11.5, 0.05))          # strictly below STUCK_SPEED
    assert not is_stopped(Car(0, "Parking", 1, 5, 29.5, 11.5, 0.0))
    assert not is_stopped(Car(0, "Home", 1, 5, 0.5, 0.5, 0.0))
    cars = (Car(0, "Outbound", 1, 5, 31.99, 13.0, 0.0),   # cell (31, 13): 2 from (29, 11), inside
            Car(0, "Outbound", 1, 5, 32.0, 11.0, 0.0),    # cell (32, 11): 3 away, outside
            Car(0, "Home", 1, 5, 27.0, 9.2, 1.0),         # cell (27, 9): 2 away, inside, but parked: not near
            Car(0, "Outbound", 1, 5, 28.99, 10.99, 0.0))  # cell (28, 10): inside
    s = replace(parse_observation(make_obs()), cars=cars)
    assert PLACE_RADIUS == 2
    assert cars_near(s, ((29, 11),)) == (cars[0], cars[3])                          # observation order, driving only
    # a car near two footprint cells is listed once, whatever the footprint order
    assert cars_near(s, ((29, 11), (29, 14))) == cars_near(s, ((29, 14), (29, 11))) == (cars[0], cars[3])
    assert cars_near(parse_observation(make_obs()), ((29, 11),)) == ()


def test_cars_near_skips_parked_cars():
    cars = [_waiting(_car("Outbound", 29.5, 11.5, 0.0), 6.0),     # driving, near
            _waiting(_car("Home", 28.5, 12.5, 0.0), 30.0),        # parked at home, near
            _waiting(_car("Parking", 30.5, 13.5, 0.0), 20.0)]     # parked at a shop, near
    s = _stocked(vehicles=cars)
    pc = _at(s, LIGHT, (29, 11))
    assert len(s.cars) == 3
    assert len(cars_near(s, pc.footprint)) == 1
    f = placement_features(s, pc)
    assert f["pl_cars_near"] == 1.0
    assert (f["pl_max_wait_near"], f["pl_mean_wait_near"]) == (6.0, 6.0)   # a parked car's wait is not counted


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


# --- placement features -----------------------------------------------------------------------------------------

PLACEMENT_KEYS = {
    "pl_is_light", "pl_is_roundabout", "pl_degree", "pl_doorstep", "pl_cars_near", "pl_stopped_near",
    "pl_max_wait_near", "pl_mean_wait_near", "pl_dist_worst_shop", "pl_worst_colour_stuck", "pl_new_links",
    "pl_joins_separated", "pl_tiles_lost", "pl_light_stock", "pl_round_stock",
}
STOCK = (25, 1, 0, 2, 1, 0)  # roads, bridges, motorways, lights, roundabouts, unused


def _waiting(car, wait):
    return {**car, "waiting": wait}


def _stocked(vehicles=(), extra=()):
    return replace(_state(vehicles=vehicles, extra=extra), inventory=STOCK)


def _at(s, tool, cell):
    return next(c for c in placement_candidates(s, True, True) if c.tool == tool and c.cell == cell)


def test_placement_features_have_the_named_keys_and_values():
    s = _stocked(vehicles=[_waiting(_car("Outbound", 29.5, 11.5, 0.0), 6.0)])
    pc = _at(s, LIGHT, (29, 11))     # not [0]: (28, 11) comes first when the car stands on (29, 11)
    f = placement_features(s, pc)
    assert set(f) == PLACEMENT_KEYS and all(type(v) is float for v in f.values())
    assert (f["pl_is_light"], f["pl_is_roundabout"]) == (1, 0)
    assert (f["pl_degree"], f["pl_doorstep"]) == (4, 1)
    assert (f["pl_cars_near"], f["pl_stopped_near"]) == (1, 1)
    assert (f["pl_max_wait_near"], f["pl_mean_wait_near"]) == (6.0, 6.0)
    assert (f["pl_dist_worst_shop"], f["pl_worst_colour_stuck"]) == (0, 1)   # the red car stands at the red doorstep
    assert (f["pl_new_links"], f["pl_joins_separated"], f["pl_tiles_lost"]) == (0, 0, 0)
    assert (f["pl_light_stock"], f["pl_round_stock"]) == (2, 1)
    assert placement_features(s, pc, GameMemory()) == f


def test_a_roundabout_spot_reports_the_candidate_and_its_footprint():
    s = _stocked(vehicles=[_car("Outbound", 27.5, 9.5, 0.0)])   # cell (27, 9): in the ring of (28, 10)
    pc = _at(s, ROUNDABOUT, (28, 10))
    f = placement_features(s, pc)
    assert set(f) == PLACEMENT_KEYS
    assert (f["pl_is_light"], f["pl_is_roundabout"]) == (0, 1)
    assert (f["pl_degree"], f["pl_new_links"], f["pl_tiles_lost"]) == (3, 3, 3)
    assert f["pl_joins_separated"] == 0
    assert f["pl_doorstep"] == 1                                   # ring cell (28, 11) is next to the doorstep (29, 11)
    assert f["pl_dist_worst_shop"] == 1                            # from the centre (28, 10) to (29, 11)
    assert (f["pl_cars_near"], f["pl_stopped_near"]) == (1, 1)
    assert placement_features(s, replace(pc, joins_separated=True))["pl_joins_separated"] == 1


def test_waits_cover_exactly_the_cars_near_the_footprint():
    cars = [_waiting(_car("Outbound", 29.5, 11.5, 0.0), 6.0),     # stopped, near
            _waiting(_car("Outbound", 27.5, 12.5, 0.5), 2.0),     # moving, near (cell (27, 12))
            _waiting(_car("Parking", 30.5, 13.5, 0.0), 1.0),      # parked: not a car near
            _waiting(_car("Outbound", 33.5, 11.5, 0.0), 40.0)]    # cell (33, 11): 4 away, not near
    s = _stocked(vehicles=cars)
    f = placement_features(s, _at(s, LIGHT, (29, 11)))
    assert (f["pl_cars_near"], f["pl_stopped_near"]) == (2, 1)
    assert (f["pl_max_wait_near"], f["pl_mean_wait_near"]) == (6.0, 4.0)
    quiet = placement_features(s, PlacementCandidate(LIGHT, (5, 5), ((5, 5),), 3, 0, False, 0))
    assert (quiet["pl_cars_near"], quiet["pl_stopped_near"], quiet["pl_max_wait_near"],
            quiet["pl_mean_wait_near"]) == (0, 0, 0, 0)


def test_doorstep_and_distance_for_a_spot_away_from_the_shop():
    far = PlacementCandidate(LIGHT, (5, 5), ((5, 5),), 3, 0, False, 0)
    f = placement_features(_stocked(), far)
    assert f["pl_doorstep"] == 0 and f["pl_dist_worst_shop"] == 24    # doorstep (29, 11): max(24, 6)
    at = lambda c: placement_features(_stocked(), replace(far, cell=c, footprint=(c,)))["pl_doorstep"]
    assert (at((27, 11)), at((28, 12)), at((30, 12))) == (0, 1, 1)    # within 1 of the doorstep, or not


def _second_shop(over_second, over_first=0.0):
    first = _shop(5, 0, 30, 10, over=over_first)
    second = _shop(7, 1, 40, 20, over=over_second)                # blue shop, doorstep (39, 21)
    return parse_observation(make_obs(
        buildings=[first, second, house(1, 0, 19, 11, E)], roads=ROADS, inventory=STOCK,
        vehicles=[_car("Outbound", 29.5, 11.5, 0.0, color=0), _car("Outbound", 30.5, 12.5, 0.0, color=0),
                  _car("Outbound", 28.5, 10.5, 0.0, color=1), _car("Outbound", 28.5, 12.5, 0.5, color=1)]))


def test_the_worst_shop_is_the_most_overcrowded_then_the_lowest_id():
    spot = PlacementCandidate(LIGHT, (29, 11), ((29, 11),), 4, 0, False, 0)
    # shop 7 is the most overcrowded: its doorstep (39, 21) is 10 away; of the cars near the spot, one blue car
    # is stopped and the other is moving
    f = placement_features(_second_shop(over_second=3.0), spot)
    assert (f["pl_dist_worst_shop"], f["pl_worst_colour_stuck"]) == (10, 1)
    # equal overcrowding: the lowest id (red shop 5, doorstep (29, 11)) is the worst; two red cars are stopped
    f = placement_features(_second_shop(over_second=3.0, over_first=3.0), spot)
    assert (f["pl_dist_worst_shop"], f["pl_worst_colour_stuck"]) == (0, 2)
    # nobody overcrowded: still the lowest id
    f = placement_features(_second_shop(over_second=0.0), spot)
    assert (f["pl_dist_worst_shop"], f["pl_worst_colour_stuck"]) == (0, 2)
    # the first shop is the most overcrowded: it wins whatever its id
    f = placement_features(_second_shop(over_second=1.0, over_first=2.0), spot)
    assert (f["pl_dist_worst_shop"], f["pl_worst_colour_stuck"]) == (0, 2)


def test_without_a_shop_the_worst_shop_terms_are_neutral():
    s = parse_observation(make_obs(roads=ROADS, inventory=STOCK, vehicles=[_car("Outbound", 29.5, 11.5, 0.0)]))
    pc = placement_candidates(s, True, False)[0]
    f = placement_features(s, pc)
    assert (f["pl_dist_worst_shop"], f["pl_worst_colour_stuck"], f["pl_doorstep"]) == (64.0, 0.0, 0.0)
    assert (f["pl_stopped_near"], f["pl_light_stock"]) == (1, 2)


# --- task 5: the placement step and its decision trigger ------------------------------------------------------

class _Places:
    """A policy that only places: lights (and, if asked, roundabouts) at the spot its `place` score likes best."""

    name = "places"

    def __init__(self, score=lambda f: f["pl_stopped_near"], lights=True, roundabouts=False, wants_globals=False):
        self.place, self.places_lights, self.places_roundabouts = score, lights, roundabouts
        self.wants_globals = wants_globals

    def priority(self, f):
        return float("-inf")

    def hold(self, g):
        return float("inf")

    def upgrade(self, f):
        return 0.0

    def remove(self, f):
        return -1.0


def _with_stock(vehicles=(), inventory=(25, 1, 0, 1, 0, 0)):
    return replace(_state(vehicles=vehicles), inventory=inventory)


def _decided(policy, state):
    sess = _Session(state)
    decide(sess, policy)
    return sess.sent


def _light(x, y):
    return {"command": "build", "tool": "TrafficLight", "x": x, "y": y}


def test_a_placing_policy_places_its_best_spot():
    # A stopped car by the shop's south side is within 2 tiles of the doorstep junction (29, 11), not of (28, 11).
    # Both are light spots; the one with the stopped car near it scores 1, the other 0.
    s = _with_stock([_car("Outbound", 31.5, 12.5, 0.0)])
    assert _decided(_Places(), s) == [_light(29, 11)]


def test_the_best_score_wins_over_the_list_order_and_a_tie_keeps_the_earlier_spot():
    # a car on the doorstep is near both junctions: equal scores, so the earlier spot of the list, (28, 11)
    assert _decided(_Places(), _with_stock([_car("Outbound", 29.5, 11.5, 0.0)])) == [_light(28, 11)]
    # no cars: (28, 11) (degree 3) comes first in the list, but (29, 11) (degree 4) scores higher
    assert _decided(_Places(lambda f: f["pl_degree"]), _with_stock()) == [_light(29, 11)]


@pytest.mark.parametrize("score", [0.0, -1.0, float("nan"), float("inf"), float("-inf")])
def test_a_score_that_is_not_finite_and_positive_places_nothing(score):
    assert _decided(_Places(lambda f: score), _with_stock([_car("Outbound", 31.5, 12.5, 0.0)])) == []


def test_a_roundabout_policy_places_a_roundabout_from_its_own_stock():
    pol = _Places(lambda f: f["pl_is_roundabout"] + f["pl_stopped_near"], lights=False, roundabouts=True)
    sent = _decided(pol, _with_stock([_car("Outbound", 31.5, 12.5, 0.0)], inventory=(25, 1, 0, 2, 1, 0)))
    assert len(sent) == 1 and sent[0]["tool"] == "Roundabout" and sent[0]["command"] == "build"
    # the lights in stock are not its business: a light-only stock sends nothing
    assert _decided(pol, _with_stock(inventory=(25, 1, 0, 2, 0, 0))) == []


def test_a_policy_with_globals_sees_them_beside_the_placement_features():
    pol = _Places(lambda f: f["road_stock"] + f["pl_degree"], wants_globals=True)
    assert _decided(pol, _with_stock()) == [_light(29, 11)]


def test_places_reads_the_policy_flags_with_defaults():
    assert places(_Places(roundabouts=True)) == (True, True)
    assert places(_Places(lights=False)) == (False, False)
    assert places(_Places(lights=False, roundabouts=True)) == (False, True)
    for policy in (SeparatedPreference(), HandRule(), CleanHand(), CleanRemoveHand(), TreePolicy(GP2_BEST)):
        assert places(policy) == (False, False)
    assert (agent.MAX_PLACEMENTS_PER_DECISION, agent.PLACE_WAIT_S, agent.PLACE_EVERY_S) == (1, 3.0, 5.0)


FINAL = Path(agent.__file__).resolve().parent / "final"


def _final_text(name):
    return (FINAL / f"{name}.txt").read_text(encoding="utf-8")


def test_no_stock_or_no_flag_never_looks(monkeypatch):
    def looked(*args, **kwargs):
        raise AssertionError("placement_candidates was called")

    monkeypatch.setattr(agent, "placement_candidates", looked)
    both = (25, 1, 0, 2, 2, 0)
    cases = [
        (_Places(), _with_stock(inventory=(25, 1, 0, 0, 2, 0))),  # lights only, none in stock
        (_Places(lights=False, roundabouts=True), _with_stock(inventory=(25, 1, 0, 2, 0, 0))),
        (_Places(), _with_stock(inventory=(25,))),  # a short inventory counts as no stock
        (SeparatedPreference(), _with_stock(inventory=both)),
        (TreePolicy(GP2_BEST), _with_stock(inventory=both)),
        (TreePolicy(_final_text("gp3_final")), _with_stock(inventory=both)),
        (TreePolicy(_final_text("cma_final")), _with_stock(inventory=both)),
    ]
    for policy, state in cases:
        assert _decided(policy, state) == []


def test_placement_comes_after_routes_and_before_removal():
    class Everything(_Places):
        removes = True

        def remove(self, f):
            return 1.0

    # house 1 is served; two cars stuck at the doorstep make both a light and a removal worthwhile
    cars = [_car("Outbound", 28.5, 11.0, 0.0), _car("Outbound", 29.0, 12.4, 0.0)]
    sent = _decided(Everything(), _with_stock(cars))
    assert [r["tool"] for r in sent] == ["TrafficLight", "Remove"]


# The tracker before this task, as a function over the same tracker fields (a copy of the old should_decide).
def _old_should_decide(t, state):
    ids = frozenset(b.id for b in state.buildings)
    overcrowded = {s.id: s.overcrowded_for >= agent.OVERCROWD_EVENT_S for s in state.shops()}
    upgraded = {b.id: b.upgraded for b in state.buildings}
    road_stock = state.inventory[0] if state.inventory else 0

    decide = (
        t._last_decision is None
        or bool(ids - t._ids)
        or bool(state.offers)
        or any(now and not t._overcrowded.get(i, False) for i, now in overcrowded.items())
        or any(i in t._upgraded and t._upgraded[i] != now for i, now in upgraded.items())
        or (t._road_stock is not None and road_stock > t._road_stock)
        or state.time - t._last_decision >= agent.FALLBACK_S
    )

    t._ids, t._overcrowded, t._upgraded, t._road_stock = ids, overcrowded, upgraded, road_stock
    if decide:
        t._last_decision = state.time
    return decide


def _tick(time, inventory=(25, 1, 0, 0, 0, 0), wait=None):
    """The same house all game; a car stopped beside the shop that has waited `wait` seconds (no car if None)."""
    cars = [] if wait is None else [_waiting(_car("Outbound", 29.5, 11.5, 0.0), wait)]
    return parse_observation(make_obs(buildings=[house(1, 0, 19, 11, E)], roads=ROADS, time=time,
                                      inventory=inventory, vehicles=cars))


def test_the_tracker_is_unchanged_without_places():
    lights, round_ = (25, 1, 0, 2, 0, 0), (25, 1, 0, 0, 1, 0)
    states = [_tick(0.0, lights), _tick(1.0, lights, 4.0), _tick(6.0, lights, 4.0),
              _tick(10.0, (25, 1, 0, 0, 0, 0), 4.0), _tick(16.0, round_, 9.0), _tick(21.0, lights, 9.0)]
    old_t, new_t, flagged_off = EventTracker(), EventTracker(), EventTracker(kinds=(False, False))
    old = [_old_should_decide(old_t, s) for s in states]
    assert old == [True, False, False, True, False, True]  # the sequence has long waits and stock but no event
    assert [new_t.should_decide(s) for s in states] == old
    assert [flagged_off.should_decide(s) for s in states] == old


LIGHTS, ROUNDABOUTS, BOTH = (True, False), (False, True), (True, True)


@pytest.mark.parametrize("kinds, time, inventory, wait, expected", [
    (LIGHTS, 4.9, (25, 1, 0, 1, 0, 0), 4.0, False),  # not 5 s since the last decision
    (LIGHTS, 5.0, (25, 1, 0, 1, 0, 0), 4.0, True),
    (LIGHTS, 5.0, (25, 1, 0, 1, 0, 0), 2.9, False),  # nobody has waited 3 s
    (LIGHTS, 5.0, (25, 1, 0, 1, 0, 0), 3.0, True),
    (LIGHTS, 5.0, (25, 1, 0, 0, 0, 0), 4.0, False),  # nothing to place
    (ROUNDABOUTS, 5.0, (25, 1, 0, 0, 1, 0), 4.0, True),  # a roundabout in stock is enough for a roundabout placer
    (LIGHTS, 5.0, (25, 1, 0, 0, 1, 0), 4.0, False),  # ...but not for a lights-only policy
    (ROUNDABOUTS, 5.0, (25, 1, 0, 1, 0, 0), 4.0, False),  # ...and a light is no use to a roundabouts-only one
    (BOTH, 5.0, (25, 1, 0, 1, 0, 0), 4.0, True),
    (BOTH, 5.0, (25, 1, 0, 0, 1, 0), 4.0, True),
    (BOTH, 5.0, (25, 1, 0, 0, 0, 0), 4.0, False),
    (LIGHTS, 5.0, (25, 1, 0, 1, 0, 0), None, False),  # no car at all
    (LIGHTS, 5.0, (25,), 4.0, False),  # a short inventory has no stock
])
def test_with_places_a_waiting_car_and_stock_trigger_a_decision(kinds, time, inventory, wait, expected):
    for tracker_kinds, want in ((kinds, expected), ((False, False), False)):  # no kinds: 5 s is no event at all
        t = EventTracker(kinds=tracker_kinds)
        assert t.should_decide(_tick(0.0, inventory)) is True  # the first call always decides
        assert t.should_decide(_tick(time, inventory, wait)) is want


@pytest.mark.parametrize("kinds, stock", [(LIGHTS, (25, 1, 0, 0, 2, 0)), (ROUNDABOUTS, (25, 1, 0, 2, 0, 0))])
def test_stock_of_a_kind_the_policy_does_not_place_changes_nothing(kinds, stock):
    # long waits and stock all game, but of the wrong kind: the tracker keeps the Phase 1 timing, fallback included
    states = [_tick(0.0, stock), _tick(1.0, stock, 4.0), _tick(6.0, stock, 4.0), _tick(9.0, stock, 9.0),
              _tick(10.0, stock, 9.0), _tick(16.0, stock, 9.0), _tick(21.0, stock, 9.0)]
    old_t, t = EventTracker(), EventTracker(kinds=kinds)
    old = [_old_should_decide(old_t, s) for s in states]
    assert old == [True, False, False, False, True, False, True]
    assert [t.should_decide(s) for s in states] == old


def test_the_placement_trigger_counts_from_the_last_decision():
    t = EventTracker(kinds=LIGHTS)
    lights = (25, 1, 0, 1, 0, 0)
    assert [t.should_decide(_tick(s, lights, 4.0)) for s in (0.0, 4.0, 5.0, 9.0, 10.0, 14.9)] == [
        True, False, True, False, True, False]


@pytest.mark.parametrize("module", [agent, autopsy], ids=["play_game", "autopsy"])
@pytest.mark.parametrize("policy, expected", [
    (_Places(), (True, False)), (_Places(lights=False, roundabouts=True), (False, True)),
    (_Places(roundabouts=True), (True, True)), (_Places(lights=False), (False, False)),
    (HandRule(), (False, False)), (TreePolicy(GP2_BEST), (False, False)),
])
def test_both_game_loops_build_the_tracker_from_the_policy(monkeypatch, module, policy, expected):
    """play_game and the autopsy's copy of its loop must give the tracker the same `kinds` (here: a probe that
    records it and stops the game)."""
    seen = []

    class Stop(Exception):
        pass

    def tracker(**kwargs):
        seen.append(kwargs)
        raise Stop

    monkeypatch.setattr(module, "EventTracker", tracker)
    monkeypatch.setattr(module, "GameSession", lambda *a, **k: SimpleNamespace(reset=lambda: None))
    with pytest.raises(Stop):
        if module is agent:
            play_game(None, 1, policy, record=False)
        else:
            monkeypatch.setattr(autopsy, "make_policy", lambda spec: policy)
            autopsy.play("x", 1)
    assert seen == [{"kinds": expected}]


def test_the_watched_policy_passes_the_placement_switches_and_scores():
    w = autopsy._Watched(_Places(lights=True, roundabouts=True), autopsy._Tally())
    assert places(w) == (True, True)
    assert places(autopsy._Watched(HandRule(), autopsy._Tally())) == (False, False)
    assert w.place({"pl_stopped_near": 2.0, "pl_degree": 3.0, "road_stock": 9.0}) == 2.0
    assert set(w.tally.stats) == {"pl_stopped_near", "pl_degree"}  # the globals are tallied by hold


# gp-3's and the CMA-ES final rules play their test games (seeds 7000-7099) exactly as recorded before gp-4: the two
# shortest games of each, as (seed, trips, seconds rounded to 2) from the runs test-gp and test-cma.
FINAL_GAMES = [
    ("gp3_final", 7045, 74, 444.45), ("gp3_final", 7006, 106, 497.95),
    ("cma_final", 7019, 95, 501.8), ("cma_final", 7081, 109, 526.1),
]


@pytest.mark.host
@pytest.mark.parametrize("name, seed, trips, seconds", FINAL_GAMES)
def test_final_rules_still_play_their_test_games(host, name, seed, trips, seconds):
    r = play_game(host, seed, TreePolicy(_final_text(name)), record=False)
    assert (r.trips, round(r.seconds, 2)) == (trips, seconds)


# --- task 6: the hand rules and their policy names ------------------------------------------------------------

GP3_FINAL = _final_text("gp3_final")
NEW_NAMED = [("light", LightHand, (True, False)), ("round", RoundHand, (False, True)),
             ("lightround", LightRoundHand, (True, True))]
GP_SPECS = [("gppkg", (False, False)), ("gplight", (True, False)), ("gpround", (False, True)),
            ("gplightround", (True, True))]


def _upgrade_choices(policy, offers):
    """The offers `decide` takes from a state that has them (the lights, roundabouts and roads of STOCK in hand)."""
    sent = _decided(policy, replace(_state(), offers=tuple(offers), inventory=STOCK))
    return [r["choice"] for r in sent if r["command"] == "upgrade"]


def test_package_rule_prefers_the_enabled_package():
    offers = [Offer(0, 3, 2, 20), Offer(1, 4, 1, 20), Offer(2, 0, 30, 0)]  # lights x2 + 20 roads, roundabout + 20, 30 roads
    assert [offer_features(o)["offer_roads"] for o in offers] == [20, 20, 30]
    assert _upgrade_choices(LightHand(), offers) == [0]
    assert _upgrade_choices(RoundHand(), offers) == [1]
    assert _upgrade_choices(LightRoundHand(), offers) == [0]       # both packages score the same: the lower index
    assert _upgrade_choices(GPHand(GP3_FINAL, False, False, "gppkg"), offers) == [2]
    assert _upgrade_choices(GPHand(GP3_FINAL, True, False, "gplight"), offers) == [0]
    assert _upgrade_choices(GPHand(GP3_FINAL, False, True, "gpround"), offers) == [1]
    assert _upgrade_choices(HandRule(), offers) == _upgrade_choices(SeparatedPreference(), offers) == [2]
    # apart from the package only the roads count: the bigger package wins among the enabled ones
    bigger = [Offer(0, 3, 2, 20), Offer(1, 3, 1, 30), Offer(2, 0, 90, 0)]
    assert _upgrade_choices(LightHand(), bigger) == [1] and _upgrade_choices(RoundHand(), bigger) == [2]


def test_package_upgrade_scores():
    light = {"type_3": 1.0, "type_4": 0.0, "offer_roads": 20.0}
    round_ = {"type_3": 0.0, "type_4": 1.0, "offer_roads": 20.0}
    roads = {"type_3": 0.0, "type_4": 0.0, "offer_roads": 30.0}
    assert [package_upgrade(f, True, False) for f in (light, round_, roads)] == [1020.0, 20.0, 30.0]
    assert [package_upgrade(f, False, True) for f in (light, round_, roads)] == [20.0, 1020.0, 30.0]
    assert [package_upgrade(f, True, True) for f in (light, round_, roads)] == [1020.0, 1020.0, 30.0]
    assert [package_upgrade(f, False, False) for f in (light, round_, roads)] == [20.0, 20.0, 30.0]


def test_hand_place_skips_merging_roundabouts():
    light = {"pl_is_light": 1.0, "pl_is_roundabout": 0.0, "pl_stopped_near": 2.0, "pl_joins_separated": 0.0}
    round_ = {"pl_is_light": 0.0, "pl_is_roundabout": 1.0, "pl_stopped_near": 3.0, "pl_joins_separated": 0.0}
    merging = {**round_, "pl_joins_separated": 1.0}
    # an enabled tool scores the number of stopped cars; a tool that is not enabled scores -1
    assert [hand_place(f, True, True) for f in (light, round_)] == [2.0, 3.0]
    assert [hand_place(f, True, False) for f in (light, round_)] == [2.0, -1.0]
    assert [hand_place(f, False, True) for f in (light, round_)] == [-1.0, 3.0]
    assert [hand_place(f, False, False) for f in (light, round_)] == [-1.0, -1.0]
    # a roundabout that would join separated networks is never placed; the same flag does not matter for a light
    assert [hand_place(merging, a, b) for a, b in ((True, True), (False, True), (True, False))] == [-1.0] * 3
    assert hand_place({**light, "pl_joins_separated": 1.0}, True, False) == 2.0
    # nobody stopped: 0 is not above 0, so nothing is placed
    assert hand_place({**light, "pl_stopped_near": 0.0}, True, True) == 0.0


def test_the_hand_rules_place_where_cars_are_stopped_and_only_what_they_place():
    stopped = [_car("Outbound", 31.5, 12.5, 0.0)]
    lights, roundabouts, both = (25, 1, 0, 1, 0, 0), (25, 1, 0, 0, 1, 0), (25, 1, 0, 1, 1, 0)
    assert _decided(LightHand(), _with_stock(stopped, lights)) == [_light(29, 11)]
    assert _decided(LightHand(), _with_stock([_car("Outbound", 31.5, 12.5, 0.5)], lights)) == []   # a moving car
    assert _decided(LightHand(), _with_stock(inventory=lights)) == []                               # no car
    assert _decided(LightHand(), _with_stock(stopped, roundabouts)) == []                           # not its stock
    assert _decided(RoundHand(), _with_stock(stopped, lights)) == []
    sent = _decided(RoundHand(), _with_stock(stopped, roundabouts))
    assert [(r["command"], r["tool"]) for r in sent] == [("build", "Roundabout")]
    sent = _decided(LightRoundHand(), _with_stock(stopped, both))
    assert len(sent) == 1 and sent[0]["tool"] in ("TrafficLight", "Roundabout")
    # the package-only GPHand never places, whatever is in stock
    pkg = GPHand(GP3_FINAL, False, False, "gppkg")
    assert _decided(pkg, _with_stock(stopped, both)) == []


def test_hand_rule_classes_and_flags():
    for name, cls, flags in NEW_NAMED:
        p = cls()
        assert isinstance(p, SeparatedPreference) and p.name == name and places(p) == flags
        assert not hasattr(p, "coverage") and not hasattr(p, "removes") and not hasattr(p, "wants_globals")
        h = SeparatedPreference()          # everything else is the separated preference's
        f = {"tiles_needed": 6.0, "is_separated": 1.0}
        assert p.priority(f) == h.priority(f) and p.hold({"road_stock": 3.0}) == h.hold({"road_stock": 3.0})
        assert p.remove({}) == -1.0


def test_gphand_keeps_the_tree_priority_and_hold():
    s = _roundabout_state()                       # an unserved house: there are route candidates
    cands = route_candidates(s, *unserved_targets(s)[0])
    assert cands
    memory = GameMemory()
    g = global_features(s, memory)
    tree = TreePolicy(GP3_FINAL)
    for flags in ((False, False), (True, False), (False, True), (True, True)):
        hand = GPHand(GP3_FINAL, *flags, "gpx")
        assert hand.name == "gpx" and places(hand) == flags
        for cand in cands:
            f = {**candidate_features(s, cand, memory), **g}
            assert hand.priority(f) == tree.priority(f) and tree.priority(f) != float("-inf")
        assert hand.hold(g) == tree.hold(g)
        assert (hand.coverage, hand.clean_routes, hand.removes, hand.wants_globals) == (
            tree.coverage, tree.clean_routes, tree.removes, tree.wants_globals) == (True, True, False, True)
    # a remove tree that can fire is the tree policy's (two cars are stuck at the doorstep)
    jam = _state(vehicles=[_car("Outbound", 28.5, 11.0, 0.0), _car("Outbound", 29.0, 12.4, 0.0)])
    removing = GP3_FINAL.replace("remove: -1.0", "remove: rm_shop_stuck")
    hand, tree = GPHand(removing, True, True, "x"), TreePolicy(removing)
    scores = []
    for rc in removal_candidates(jam):
        f = {**removal_features(jam, rc, memory), **global_features(jam, memory)}
        assert hand.remove(f) == tree.remove(f)
        scores.append(hand.remove(f))
    assert hand.removes is True and max(scores) > 0
    # a 3-tree text keeps its Phase 1 routes and never removes
    old = GPHand(GP2_BEST, True, True, "x")
    assert (old.removes, old.clean_routes) == (False, False)


def test_the_hand_rules_are_registered_by_name():
    for name, cls, _ in NEW_NAMED:
        assert ev.POLICIES[name] is cls and name in ev.POLICY_NAMES


def _spec_file(tmp_path, text=GP3_FINAL, name="p.txt"):
    f = tmp_path / "src" / name
    f.parent.mkdir(exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


@pytest.mark.parametrize("make", [ev.make_policy, autopsy.make_policy], ids=["evaluate", "autopsy"])
def test_specs_resolve(tmp_path, make):
    for name, cls, flags in NEW_NAMED:
        p = make(name)
        assert type(p) is cls and p.name == name and places(p) == flags
    f = _spec_file(tmp_path)
    tree = TreePolicy(GP3_FINAL)
    for name, flags in GP_SPECS:
        p = make(f"{name}:{f}")
        assert type(p) is GPHand and p.name == name and places(p) == flags
        assert p.tree.text == tree.text
        assert (p.coverage, p.clean_routes, p.removes, p.wants_globals) == (True, True, False, True)
    # the old specs are what they were
    assert [type(make(n)) for n in ("hand", "separated", "clean", "cleanrm")] == [
        HandRule, SeparatedPreference, CleanHand, CleanRemoveHand]
    assert isinstance(make(f"tree:{f}"), TreePolicy) and places(make(f"tree:{f}")) == (False, False)


@pytest.mark.parametrize("check", [ev.check_policy, autopsy.make_policy], ids=["evaluate", "autopsy"])
def test_bad_gp_specs_are_refused(tmp_path, check):
    bad_text = _spec_file(tmp_path, "priority: neg(tiles_needed)", "bad.txt")
    for spec in ["gplight:", "gppkg:", f"gpround:{tmp_path / 'nope.txt'}", f"gplightround:{bad_text}", "gplight",
                 "gp:x", "GPLIGHT:x", "gplightx:x"]:
        with pytest.raises(ValueError):          # evaluate: before any run folder is claimed; autopsy: fail fast
            check(spec)


@pytest.mark.parametrize("prefix, flags", GP_SPECS)
def test_gp_specs_run_from_a_copy_in_the_run_folder(fake_runs, prefix, flags):  # noqa: F811
    tmp_path, calls = fake_runs
    f = _spec_file(tmp_path, "\n" + GP3_FINAL.replace("\n", "\n\n") + "\n\n")   # canonicalised on the way in
    spec = f"{prefix}:{f}"
    assert ev.main(["--policy", spec, "--seeds", "3100-3101", "--run", "g", "--workers", "2", "--verify"]) == 0
    run = tmp_path / "g"
    canonical = ev.read_tree_policy(spec)
    assert (run / "policy.txt").read_text(encoding="utf-8") == canonical + "\n"
    jobs = [c for c in calls if c != "build"]
    assert sorted(c[1] for c in jobs) == [3100, 3101]
    assert {c[0] for c in jobs} == {f"{prefix}:{run / 'policy.txt'}"}      # never the caller's file
    cfg = json.loads((run / "summary.json").read_text())["config"]
    assert cfg["policy"] == spec and cfg["policy_text"] == canonical and cfg["workers"] == 2
    assert "build" in calls and all(c[3] for c in jobs)                   # recorded and verified like the others
    worker_policy = ev.make_policy(f"{prefix}:{run / 'policy.txt'}")      # what a worker builds from its job
    assert (worker_policy.name, places(worker_policy)) == (prefix, flags)


@pytest.mark.parametrize("spec", ["gplight:", "gppkg"])
def test_a_bad_gp_spec_claims_no_run_folder(fake_runs, capsys, spec):  # noqa: F811
    tmp_path, calls = fake_runs
    with pytest.raises(ValueError):
        ev.evaluate(spec, [3100], workers=1, run="x", verify=False)
    with pytest.raises(SystemExit) as e:
        ev.main(["--policy", spec, "--seeds", "3100", "--run", "x"])
    assert e.value.code == 2 and "policy" in capsys.readouterr().err.lower()
    assert calls == [] and list(tmp_path.iterdir()) == []


def test_the_autopsy_counts_lights_and_roundabouts_at_the_end():
    ring = [(25, 10), (24, 11), (25, 12), (26, 11)]
    s = parse_observation(make_obs(infra={(5, 5): 4, (6, 6): 4, (7, 7): 2, (8, 8): 1}, roundabouts=[((25, 11), ring)]))
    assert autopsy.placed_at_end(s) == {"lights_end": 2, "roundabouts_end": 1}   # a ring is infrastructure 3, not a light
    assert autopsy.placed_at_end(parse_observation(make_obs())) == {"lights_end": 0, "roundabouts_end": 0}


def test_the_autopsy_summary_reports_the_mean_lights_and_roundabouts():
    rows = [{"trips": 10, "seconds": 90.0, "cause": "cap", "lights_end": 1, "roundabouts_end": 0},
            {"trips": 20, "seconds": 80.0, "cause": "cap", "lights_end": 2, "roundabouts_end": 1}]
    lines = autopsy.summarise(rows, {}).splitlines()
    assert "lights 1.50, roundabouts 0.50" in lines[2]


def _placements(recording):
    """The accepted traffic light and roundabout builds of a recording, in order."""
    return [a["tool"] for a in recording["actions"]
            if a["command"] == "build" and a["tool"] in ("TrafficLight", "Roundabout") and a["accepted"]]


@pytest.mark.host
def test_a_game_with_placements_passes_the_replay_verifier(host, tmp_path):
    from evolved_rules.verify import verify_recording
    seed = 3100  # LightRoundHand places 6 lights and a roundabout on 3100, so the first seed of the range will do
    r = play_game(host, seed, LightRoundHand(), record=True)
    assert _placements(r.recording)
    path = tmp_path / f"{seed}.json"
    path.write_text(json.dumps(r.recording), encoding="utf-8")
    ok, out = verify_recording(path)
    assert ok, out


@pytest.mark.host
def test_the_autopsy_row_counts_what_the_game_placed(host, monkeypatch):
    monkeypatch.setattr(autopsy, "_HOST", host)
    row = autopsy.play("lightround", 3100, cap_s=450.0)["row"]       # by 450 s: 4 lights and a roundabout
    r = play_game(host, 3100, LightRoundHand(), cap_s=450.0, record=True)
    placed = _placements(r.recording)
    assert (row["trips"], row["seconds"]) == (r.trips, r.seconds)    # the autopsy plays the same game
    assert (row["lights_end"], row["roundabouts_end"]) == (placed.count("TrafficLight"), placed.count("Roundabout"))
    assert row["lights_end"] > 0 and row["roundabouts_end"] > 0
