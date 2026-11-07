"""gp-4 step 1, task 1: the new build commands are allowed, and roundabouts and car waiting times are parsed."""
from evolved_rules.session import _replayable
from evolved_rules.state import Roundabout, parse_observation
from evolved_rules.tests.helpers import make_obs


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
