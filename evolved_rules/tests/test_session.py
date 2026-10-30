import json, re, pytest
import numpy as np
from evolved_rules.host import ROOT
from evolved_rules.state import W, H, DIRS, Building, CityState
from evolved_rules.session import Recorder, GameSession
from evolved_rules.executor import execute_route, take_offer
from evolved_rules.candidates import unserved_targets, route_candidates, RouteCandidate, Stroke

AI_REPLAY_CS = ROOT / "simulation" / "Assets" / "Simulation" / "AiReplay.cs"


def _csharp_fields(cls: str) -> set[str]:
    """Public field names of a class in AiReplay.cs (the replay schema authority)."""
    src = AI_REPLAY_CS.read_text(encoding="utf-8")
    body = re.search(r"class\s+%s\s*\{(.*?)\n\s*\}" % cls, src, re.S).group(1)
    names: set[str] = set()
    for m in re.finditer(r"public\s+[\w\[\]]+\s+([\w,\s]+);", body):
        names.update(n.strip() for n in m.group(1).split(","))
    return names


class _SpyHost:
    """Delegates to the real host, records every call, and can rewrite each `step` reply."""

    def __init__(self, host, patch=None):
        self._host, self._patch, self.calls, self.steps = host, patch, [], 0

    def reset(self, *a, **k):
        return self._host.reset(*a, **k)

    def call(self, **request):
        self.calls.append(request)
        reply = self._host.call(**request)
        if request["command"] == "step":
            self.steps += 1
            if self._patch is not None:
                reply = self._patch(reply, self.steps)
        return reply


def _city(inventory=(25, 1, 0, 0, 0, 0), links=(), water=(), infra=None, pending=()) -> CityState:
    """A real CityState on an empty 50 x 30 grid, for executor tests that need no host.

    water: cells with water terrain; infra: {cell: infra value}; pending: cells pending removal;
    links: (a, b) cell pairs whose connection bit a -> b is set.
    """
    terrain = np.zeros((H, W), dtype=np.int64)
    infra_grid = np.zeros((H, W), dtype=np.int64)
    pending_grid = np.zeros((H, W), dtype=np.int64)
    conn = np.zeros((H, W), dtype=np.int64)
    for x, y in water:
        terrain[y, x] = 1
    for (x, y), v in (infra or {}).items():
        infra_grid[y, x] = v
    for x, y in pending:
        pending_grid[y, x] = 1
    for a, b in links:
        conn[a[1], a[0]] |= 1 << DIRS.index((b[0] - a[0], b[1] - a[1]))
    house = Building(id=0, color=0, is_house=True, cell=(0, 0), width=1, height=1, access=((0, 0),),
                     access_dirs=(0,), demand=0, reserved=0, capacity=0, overcrowded_for=0.0, upgraded=False)
    return CityState(
        time=0.0, trips=0, failed=False, inventory=tuple(inventory), offers=(), bounds=(0, 0, W, H),
        terrain=terrain, infra=infra_grid, conn=conn, pending=pending_grid, kinds=np.zeros((H, W), dtype=np.int64),
        buildings=(house,), vehicles_busy={}, vehicles_waiting=())


class _FakeSession:
    """Stands in for GameSession in executor unit tests: every command is accepted and the state never changes."""

    def __init__(self, state):
        self.state, self.sent, self.done = state, [], False

    def command(self, request):
        self.sent.append(request)
        return True, self.state


def _row_links(x0, x1, y):
    return [((x, y), (x + 1, y)) for x in range(x0, x1)]


def _route(*strokes) -> RouteCandidate:
    return RouteCandidate("direct", 0, (), (), 0, 0, 0, 0, 0, tuple(strokes))


def test_recorder_logs_wait_and_remove_casing():
    r = Recorder(7)
    r.log(None, True, {"tripsCompleted": 0, "time": 1.0})
    r.log({"command": "build", "tool": "Remove", "x": 3, "y": 4}, False, {"tripsCompleted": 0, "time": 2.0})
    a = r.recording({"tripsCompleted": 0, "time": 2.0, "failed": False}, "test")["actions"]
    assert a[0]["command"] == "wait" and a[0]["ticks"] == 20
    assert a[1]["tool"] == "Remove" and a[1]["accepted"] is False and a[1]["afterTime"] == 2.0


def test_recording_fields_match_csharp_schema_and_save_round_trips(tmp_path):
    r = Recorder(7)
    r.log(None, True, {"tripsCompleted": 0, "time": 1.0})
    r.log({"command": "draw", "x": 1, "y": 2, "toX": 5, "toY": 2}, True, {"tripsCompleted": 3, "time": 2.0})
    r.log({"command": "upgrade", "choice": 2}, True, {"tripsCompleted": 3, "time": 3.0})
    final = {"tripsCompleted": 3, "time": 3.0, "failed": True}
    rec = r.recording(final, "unit-test")

    assert set(rec) == _csharp_fields("AiReplayRecording")
    for action in rec["actions"]:
        assert set(action) == _csharp_fields("AiReplayAction")
    assert [a["command"] for a in rec["actions"]] == ["wait", "draw", "upgrade"]
    draw = rec["actions"][1]
    assert (draw["x"], draw["y"], draw["toX"], draw["toY"], draw["tool"], draw["id"], draw["choice"]) == (1, 2, 5, 2, "", 0, 0)
    assert draw["afterTrips"] == 3 and draw["afterTime"] == 2.0
    assert rec["actions"][2]["choice"] == 2

    assert rec["schemaVersion"] == 1 and rec["version"] == "OriginalReference"
    assert rec["scenario"] == "LosAngeles" and rec["variation"] == "SameMap" and rec["seed"] == 7
    assert rec["score"] == 3 and rec["duration"] == 3.0 and rec["terminated"] is True and rec["truncated"] is False
    assert rec["source"] == "unit-test" and rec["policySchema"] == "evolved-rules-v1"
    assert rec["policySteps"] == 3 and rec["episode"] == 0 and rec["ranking"] == ""
    assert isinstance(rec["simulatorCommit"], str)

    path = tmp_path / "game.json"
    r.save(path, final, "unit-test")
    assert json.loads(path.read_bytes().decode("utf-8")) == rec


@pytest.mark.host
def test_wait_advances_and_logs(host):
    g = GameSession(host, 1000); g.reset()
    st = g.wait()
    assert st.time == 1.0 and g.commands == 1 and g.action_counts == {"wait": 1}


@pytest.mark.host
def test_command_with_tool_counts_under_the_tool_name(host):
    g = GameSession(host, 1000); g.reset()
    accepted, st = g.command({"command": "build", "tool": "Remove", "x": 0, "y": 0})
    assert g.action_counts == {"Remove": 1} and g.commands == 1
    assert st.time == 1.0 and g.state is st
    assert g.rejected == (0 if accepted else 1)
    logged = g.recorder.actions[0]
    assert logged["command"] == "build" and logged["tool"] == "Remove"
    assert logged["accepted"] is accepted and logged["ticks"] == 20 and logged["afterTime"] == 1.0
    g.command({"command": "draw", "x": -5, "y": 0, "toX": -1, "toY": 0})
    assert g.action_counts == {"Remove": 1, "draw": 1}


@pytest.mark.host
def test_command_and_wait_raise_once_done(host):
    g = GameSession(host, 1000, cap_s=2.0); g.reset()
    assert g.done is False
    g.wait()
    assert g.done is False
    g.wait()
    assert g.done is True and g.terminated is False
    with pytest.raises(RuntimeError):
        g.wait()
    with pytest.raises(RuntimeError):
        g.command({"command": "draw", "x": 0, "y": 0, "toX": 1, "toY": 0})
    assert g.commands == 2 and len(g.recorder.actions) == 2


@pytest.mark.host
def test_first_route_connects_house(host):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    cand = route_candidates(s, h, shops)[0]
    assert execute_route(g, cand) is True
    assert all(a["ticks"] == 20 for a in g.recorder.actions)


@pytest.mark.host
def test_execute_route_stops_when_stock_runs_out(host):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    real = route_candidates(s, h, shops)[0]
    # Fake a candidate whose later strokes need far more tiles than the 25 in stock.
    long = RouteCandidate("direct", h.id, real.shop_ids, real.path, 999, 0, 0, 0, 0,
                          real.strokes + tuple(Stroke(0, y, 49, y) for y in range(3)))
    before = g.commands
    assert execute_route(g, long) in (True, False)
    assert g.commands - before <= len(real.strokes) + 1  # stopped, did not loop
    # Stricter than the line above: the real strokes were sent and the first oversize stroke was not.
    assert g.commands - before == len(real.strokes)


@pytest.mark.host
def test_execute_route_stops_at_first_stroke_that_creates_no_links(host):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    real = route_candidates(s, h, shops)[0]
    # An off-map stroke is rejected and links nothing; the real strokes after it must not be sent.
    bad = RouteCandidate("direct", h.id, real.shop_ids, real.path, 0, 0, 0, 0, 0,
                         (Stroke(-5, 0, -1, 0),) + real.strokes)
    assert execute_route(g, bad) is False
    assert g.commands == 1 and g.rejected == 1
    assert g.action_counts == {"draw": 1}
    assert g.recorder.actions[0]["x"] == -5 and g.recorder.actions[0]["accepted"] is False


@pytest.mark.host
def test_take_offer_sends_an_upgrade_command(host):
    g = GameSession(host, 1000); g.reset()
    accepted = take_offer(g, 1)  # no offers exist at the start, so the host rejects it; the request is still logged
    assert accepted is False and g.rejected == 1
    assert g.action_counts == {"upgrade": 1}
    logged = g.recorder.actions[0]
    assert logged["command"] == "upgrade" and logged["choice"] == 1 and logged["accepted"] is False


def test_take_offer_sends_the_given_choice_under_the_key_choice():
    s = _FakeSession(_city())
    take_offer(s, 2)
    assert s.sent == [{"command": "upgrade", "choice": 2}]


def test_score_and_duration_come_from_final_obs():
    r = Recorder(7)
    r.log(None, True, {"tripsCompleted": 1, "time": 1.0})
    r.log(None, True, {"tripsCompleted": 2, "time": 2.0})
    r.log(None, True, {"tripsCompleted": 4, "time": 3.0})
    # trips (9), time (42.0), number of actions (3) and the last action's afterTrips/afterTime (4, 3.0) all differ.
    rec = r.recording({"tripsCompleted": 9, "time": 42.0, "failed": False}, "x")
    assert rec["score"] == 9 and rec["duration"] == 42.0 and rec["terminated"] is False
    assert rec["policySteps"] == 3 and rec["actions"][-1]["afterTrips"] == 4


@pytest.mark.host
def test_terminated_step_ends_the_game(host):
    spy = _SpyHost(host, lambda reply, n: {**reply, "terminated": True})
    g = GameSession(spy, 1000); g.reset()
    assert g.done is False
    g.wait()
    assert g.terminated is True and g.done is True and g.state.time < g.cap_s
    with pytest.raises(RuntimeError):
        g.wait()
    with pytest.raises(RuntimeError):
        g.command({"command": "draw", "x": 0, "y": 0, "toX": 1, "toY": 0})
    assert g.commands == 1 and spy.steps == 1  # the refused calls sent nothing


@pytest.mark.host
def test_wait_stats_use_every_vehicle_after_each_step(host):
    waits = {1: [1.5, 4.0, 2.5], 2: [0.5], 3: []}

    def patch(reply, n):
        reply["observation"]["vehicles"] = [{"color": 0, "stage": "Home", "waiting": w} for w in waits[n]]
        return reply

    g = GameSession(_SpyHost(host, patch), 1000); g.reset()
    assert (g.wait_sum, g.wait_n, g.max_wait) == (0.0, 0, 0.0)  # nothing is counted at reset
    g.wait()
    assert (g.wait_sum, g.wait_n, g.max_wait) == (8.0, 3, 4.0)
    g.wait()
    assert (g.wait_sum, g.wait_n, g.max_wait) == (8.5, 4, 4.0)
    g.wait()  # a step with no vehicles changes nothing
    assert (g.wait_sum, g.wait_n, g.max_wait) == (8.5, 4, 4.0)


@pytest.mark.parametrize("request_", [
    {"command": "observe"},
    {"command": "step", "ticks": 7},
    {"command": "reset", "seed": 1},
    {"command": "connect", "x": 0, "y": 0, "toX": 1, "toY": 0},
    {"command": "reference"},
    {"command": "driveway", "id": 0, "x": 0, "y": 0, "toX": 1, "toY": 0},
    {"command": "motorway", "x": 0, "y": 0, "toX": 5, "toY": 0},
    {"command": "build", "tool": "remove", "x": 0, "y": 0},   # wrong casing: the host accepts it, the replay does not
    {"command": "build", "x": 5, "y": 5},                     # no tool: the host builds Road, the replay rejects ""
    {"command": "build", "tool": "Road", "x": 5, "y": 5},
    {"command": "build", "tool": "Motorway", "x": 5, "y": 5},
    {"command": "wait"},
    {},
    None,
])
@pytest.mark.host
def test_command_refuses_requests_the_replay_cannot_reproduce(host, request_):
    spy = _SpyHost(host)
    g = GameSession(spy, 1000); g.reset()
    with pytest.raises(ValueError):
        g.command(request_)
    assert spy.calls == []  # nothing was sent, so the game and the recording are untouched
    assert g.commands == 0 and g.recorder.actions == [] and g.state.time == 0.0


@pytest.mark.host
def test_command_allows_draw_remove_and_upgrade(host):
    spy = _SpyHost(host)
    g = GameSession(spy, 1000); g.reset()
    g.command({"command": "draw", "x": 0, "y": 0, "toX": 1, "toY": 0})
    g.command({"command": "build", "tool": "Remove", "x": 0, "y": 0})
    g.command({"command": "upgrade", "choice": 0})
    assert [c["command"] for c in spy.calls] == ["draw", "step", "build", "step", "upgrade", "step"]
    assert g.action_counts == {"draw": 1, "Remove": 1, "upgrade": 1}


@pytest.mark.host
def test_execute_route_stops_after_an_accepted_stroke_that_left_a_gap(host):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    real = route_candidates(s, h, shops)[0]
    shop = s.shops()[0]
    sx, sy = shop.cell
    # A stroke across a shop footprint builds the road either side and links around the building, not through it:
    # the host reports accepted=True although a link in the middle is missing.
    gapped = Stroke(sx - 3, sy, sx + shop.width + 2, sy)
    cand = RouteCandidate("direct", h.id, real.shop_ids, real.path, 0, 0, 0, 0, 0, (gapped,) + real.strokes)
    assert execute_route(g, cand) is False
    assert g.recorder.actions[0]["accepted"] is True and g.rejected == 0
    assert g.commands == 1  # stopped after the gapped stroke; none of the real strokes were sent


def test_link_check_covers_every_pair_of_the_stroke():
    # Only the first of the stroke's three steps is linked, though the command was accepted.
    s = _FakeSession(_city(links=_row_links(0, 1, 5)))
    execute_route(s, _route(Stroke(0, 5, 3, 5), Stroke(3, 5, 3, 8)))
    assert len(s.sent) == 1
    # Control: with every step linked, both strokes go out.
    s = _FakeSession(_city(links=_row_links(0, 3, 5) + [((3, y), (3, y + 1)) for y in range(5, 8)]))
    execute_route(s, _route(Stroke(0, 5, 3, 5), Stroke(3, 5, 3, 8)))
    assert len(s.sent) == 2


@pytest.mark.parametrize("bridges, water, infra, expected_sent", [
    (0, [], {}, 2),                                  # dry land needs no bridge item
    (0, [(3, 5)], {}, 0),                            # one span, no bridge item
    (1, [(3, 5)], {}, 2),                            # one span, one item
    (1, [(3, 5), (4, 5)], {}, 2),                    # a run of water cells is a single span
    (1, [(2, 5), (5, 5)], {}, 0),                    # two separate runs need two items
    (2, [(2, 5), (5, 5)], {}, 2),
    (0, [(3, 5)], {(3, 5): 2}, 2),                   # the water cell is already a bridge
    (0, [(3, 5)], {(3, 4): 2}, 2),                   # an orthogonal neighbour is an existing bridge
    (0, [(3, 5)], {(2, 4): 2}, 0),                   # a diagonal neighbour does not count
    (0, [(3, 5)], {(3, 4): 1}, 0),                   # a plain road next to the water is not a bridge
    (0, [(1, 5)], {}, 0),                            # the stroke's very first step goes into the water
    (0, [(6, 6)], {}, 1),                            # the second stroke leaves the bank straight into water
    (1, [(6, 6)], {}, 2),
])
def test_execute_route_checks_bridge_stock_before_a_stroke(bridges, water, infra, expected_sent):
    links = _row_links(0, 6, 5) + [((6, y), (6, y + 1)) for y in range(5, 8)]
    s = _FakeSession(_city(inventory=(25, bridges, 0, 0, 0, 0), links=links, water=water, infra=infra))
    execute_route(s, _route(Stroke(0, 5, 6, 5), Stroke(6, 5, 6, 8)))
    assert len(s.sent) == expected_sent  # how many strokes went out before the bridge stock stopped the route


def test_pending_bridge_still_counts_as_an_orthogonal_bridge_neighbour():
    # Same rule as candidates' bridge_at: infra == 2 counts, whether or not the bridge is pending removal.
    links = _row_links(0, 6, 5) + [((6, y), (6, y + 1)) for y in range(5, 8)]
    s = _FakeSession(_city(inventory=(25, 0, 0, 0, 0, 0), links=links, water=[(3, 5)],
                           infra={(3, 4): 2}, pending=[(3, 4)]))
    execute_route(s, _route(Stroke(0, 5, 6, 5), Stroke(6, 5, 6, 8)))
    assert len(s.sent) == 2


def test_road_tile_count_matches_candidates_for_traffic_lights_and_pending_cells():
    links = _row_links(0, 3, 5)
    # Traffic lights (infra 4) are existing road for candidates, so they cost no stock.
    s = _FakeSession(_city(inventory=(0, 1, 0, 0, 0, 0), links=links, infra={(1, 5): 4, (2, 5): 4, (3, 5): 1}))
    execute_route(s, _route(Stroke(0, 5, 3, 5)))
    assert len(s.sent) == 1
    # A road cell pending removal is not road: it needs a new tile.
    s = _FakeSession(_city(inventory=(0, 1, 0, 0, 0, 0), links=links, infra={(1, 5): 1, (2, 5): 1, (3, 5): 1},
                           pending=[(2, 5)]))
    execute_route(s, _route(Stroke(0, 5, 3, 5)))
    assert s.sent == []


@pytest.mark.host
def test_execute_route_stops_when_the_session_reaches_its_cap_mid_route(host):
    g = GameSession(host, 1000, cap_s=3.0); s = g.reset()
    h, shops = unserved_targets(s)[0]
    cand = route_candidates(s, h, shops)[0]
    assert len(cand.strokes) > 3
    execute_route(g, cand)  # must stop quietly, not raise RuntimeError on the next stroke
    assert g.commands == 3 and g.done


# ---------------------------------------------------------------------------------------------------------
# Final-review fixes: a mid-game truncated reply raises; only the five city scenarios are accepted
# ---------------------------------------------------------------------------------------------------------
from evolved_rules.host import CITY_SCENARIOS, ScenarioRejected
from evolved_rules.agent import play_game
from evolved_rules.rules import DoNothing
from evolved_rules.tests.helpers import make_obs


class _RejectingHost:
    """Fake host: 1 s per 20-tick step. From step `reject_at` on, every reply says truncated and time stops,
    as TrafficWorld.Step does once ScenarioRejected is set. A command reply can be made truncated too."""

    MAX_CALLS = 1000  # a game loop that ignores truncated would spin here forever; fail the test instead

    def __init__(self, reject_at=None, reject_command=False):
        self.t, self.reject_at, self.reject_command, self.calls = 0, reject_at, reject_command, []

    def _rejected(self):
        return self.reject_at is not None and self.t >= self.reject_at

    def reset(self, seed, scenario="LosAngeles"):
        return {"observation": make_obs(time=0.0), "terminated": False, "truncated": False}

    def call(self, **req):
        self.calls.append(req)
        assert len(self.calls) < self.MAX_CALLS, "the game loop kept going after a truncated reply"
        if req["command"] == "step":
            if not self._rejected():
                self.t += 1
            return {"observation": make_obs(time=float(self.t)), "terminated": False,
                    "truncated": self._rejected(), "message": "infeasible"}
        return {"accepted": True, "terminated": False, "truncated": self.reject_command,
                "observation": make_obs(time=float(self.t)), "message": "infeasible"}


def test_truncated_step_mid_game_raises_scenario_rejected():
    g = GameSession(_RejectingHost(reject_at=3), 2000, record=True)
    g.reset()
    g.wait(); g.wait()
    with pytest.raises(ScenarioRejected, match="truncated reply to 'step'"):
        g.wait()
    assert g.commands == 2 and len(g.recorder.actions) == 2  # the rejected step is neither counted nor logged


def test_truncated_command_reply_raises_before_the_step():
    host = _RejectingHost(reject_command=True)
    g = GameSession(host, 2000)
    g.reset()
    with pytest.raises(ScenarioRejected, match="truncated reply to 'upgrade'"):
        g.command({"command": "upgrade", "choice": 0})
    assert host.calls == [{"command": "upgrade", "choice": 0}] and g.commands == 0


def test_play_game_raises_instead_of_looping_when_the_scenario_is_rejected():
    host = _RejectingHost(reject_at=5)
    with pytest.raises(ScenarioRejected):
        play_game(host, 2000, DoNothing(), cap_s=3600.0)
    assert len(host.calls) == 5


def test_untruncated_replies_play_to_the_cap():
    host = _RejectingHost()
    r = play_game(host, 2000, DoNothing(), cap_s=10.0)
    assert r.seconds == 10.0 and r.truncated and r.commands == 10


def test_city_scenarios_match_the_csharp_city_catalog():
    src = (ROOT / "simulation" / "Assets" / "Simulation" / "CityCatalog.cs").read_text(encoding="utf-8")
    maps = re.search(r"Maps\s*=\s*\{(.*?)\}", src).group(1)
    assert tuple(re.findall(r"ScenarioKind\.(\w+)", maps)) == CITY_SCENARIOS


@pytest.mark.parametrize("scenario", CITY_SCENARIOS)
def test_city_scenarios_are_accepted(scenario):
    assert GameSession(None, 1, scenario=scenario).scenario == scenario
    assert Recorder(1, scenario).scenario == scenario


@pytest.mark.parametrize("scenario", ["ReferenceLab", "EmptyLab", "losangeles", "LOSANGELES", "Los Angeles",
                                      " LosAngeles", "0", "", "Atlantis", None, 0])
def test_other_scenarios_are_value_errors(scenario):
    with pytest.raises(ValueError, match="scenario"):
        GameSession(None, 1, scenario=scenario)
    with pytest.raises(ValueError, match="scenario"):
        Recorder(1, scenario)


def test_default_scenario_is_los_angeles():
    assert GameSession(None, 1).scenario == "LosAngeles" and Recorder(1).scenario == "LosAngeles"
