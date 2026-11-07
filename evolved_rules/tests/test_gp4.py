"""gp-4 step 1, task 1: the new build commands are allowed, and roundabouts and car waiting times are parsed."""
from evolved_rules import candidates
from evolved_rules.candidates import route_candidates, unserved_targets
from evolved_rules.session import _replayable
from evolved_rules.state import Roundabout, parse_observation
from evolved_rules.tests.helpers import house, make_obs
from evolved_rules.tests.test_features import _links, _merge, _row, _shop

E = 0


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
