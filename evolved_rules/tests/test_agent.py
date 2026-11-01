import os, json, subprocess, sys, pytest
from evolved_rules.rules import HandRule, DoNothing
from evolved_rules.agent import EventTracker, play_game
from evolved_rules.state import parse_observation
from evolved_rules.tests.helpers import make_obs, house, shop

def test_hand_rule_values():
    r = HandRule()
    assert r.priority({"tiles_needed": 6}) == -6 and r.hold({"road_stock": 25}) == -21
    assert r.upgrade({"offer_roads": 30}) > r.upgrade({"offer_roads": 20}) and r.remove({}) < 0

def test_separated_preference_name_and_priority():
    from evolved_rules.rules import SeparatedPreference
    from evolved_rules import evaluate as ev
    p = SeparatedPreference()
    assert p.name == "separated" and HandRule.name == "hand"
    assert p.priority({"tiles_needed": 6, "is_separated": 0.0}) == -6
    assert p.priority({"tiles_needed": 6, "is_separated": 1.0}) == 994
    # a separated route outranks any non-separated one; among separated routes the cheaper one wins
    assert p.priority({"tiles_needed": 40, "is_separated": 1.0}) > p.priority({"tiles_needed": 0, "is_separated": 0.0})
    assert p.priority({"tiles_needed": 3, "is_separated": 1.0}) > p.priority({"tiles_needed": 4, "is_separated": 1.0})
    # everything else is the hand rule's
    h = HandRule()
    for g in ({"road_stock": 25}, {"road_stock": 0}):
        assert p.hold(g) == h.hold(g)
    assert p.upgrade({"offer_roads": 30}) == h.upgrade({"offer_roads": 30}) and p.remove({}) == h.remove({})
    assert ev.POLICIES["separated"] is SeparatedPreference and "separated" in ev.POLICY_NAMES

def test_event_tracker():
    t = EventTracker()
    s0 = parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4)], time=5.0))
    assert t.should_decide(s0) is True
    assert t.should_decide(parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4)], time=6.0))) is False
    s2 = parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4), house(2, 0, 25, 13, 4)], time=7.0))
    assert t.should_decide(s2) is True
    assert t.should_decide(parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4), house(2, 0, 25, 13, 4)], time=17.0))) is True

@pytest.mark.host
def test_do_nothing_loses_around_140s(host):
    r = play_game(host, 2000, DoNothing())
    assert r.trips == 0 and r.terminated and 135 <= r.seconds <= 160

@pytest.mark.host
def test_hand_rule_scores_and_replays(host, verifier, tmp_path):
    from evolved_rules.verify import verify_recording
    r = play_game(host, 1000, HandRule(), cap_s=300.0)
    assert r.trips > 0 and all(a["ticks"] == 20 for a in r.recording["actions"])
    p = tmp_path / "g.json"; p.write_text(json.dumps(r.recording))
    assert verify_recording(p)[0]
    # GameResult wiring against the recording (fix round 1)
    acts = r.recording["actions"]
    assert r.truncated and not r.terminated and r.seconds >= 300.0
    assert r.commands == len(acts) and sum(r.action_counts.values()) == r.commands
    assert r.rejected_actions == sum(1 for a in acts if not a["accepted"])

@pytest.mark.host
def test_same_game_in_two_processes(host_dll):
    code = ("from evolved_rules.host import Host;from evolved_rules.agent import play_game;"
            "from evolved_rules.rules import HandRule;import json;"
            "h=Host();r=play_game(h,1000,HandRule(),cap_s=200.0);h.close();"
            "print(json.dumps(r.recording['actions']))")
    outs = [subprocess.check_output([sys.executable, "-c", code],
                                    env={**os.environ, "PYTHONHASHSEED": str(s)}) for s in (1, 2)]
    assert outs[0] == outs[1]


# ---------------------------------------------------------------------------------------------------------
# Focused tests (no host unless marked): event triggers, decide() with fakes, GameResult.
# ---------------------------------------------------------------------------------------------------------
from types import SimpleNamespace
from evolved_rules import agent
from evolved_rules.agent import GameResult, decide, FALLBACK_S, OVERCROWD_EVENT_S, MAX_ROUTES_PER_DECISION
from evolved_rules.candidates import RouteCandidate
from evolved_rules.features import candidate_features, global_features, offer_features, route_features
from evolved_rules.session import GameSession
from evolved_rules.state import Offer


def _shop(id=5, over=0.0, upgraded=False):
    d = shop(id, 0, 30, 10, 2, 2, [(30, 11, 4)])
    d["overcrowdedFor"], d["upgraded"] = over, upgraded
    return d


def _state(time, buildings=(), **kw):
    return parse_observation(make_obs(buildings=list(buildings), time=time, **kw))


def _primed(*buildings, **kw):
    """A tracker that has already fired once at t = 0 on the given buildings."""
    t = EventTracker()
    assert t.should_decide(_state(0.0, buildings, **kw)) is True
    return t


def test_event_tracker_fires_while_offers_present():
    h = house(1, 0, 20, 13, 4)
    t = _primed(h)
    offer = [{"type": 0, "amount": 0, "roads": 30}]
    assert t.should_decide(_state(1.0, [h], offers=offer)) is True
    assert t.should_decide(_state(2.0, [h], offers=offer)) is True  # still pending: fires again
    assert t.should_decide(_state(3.0, [h])) is False


def test_event_tracker_overcrowd_crossing_fires_once_while_above():
    t = _primed(_shop(over=0.0))
    assert t.should_decide(_state(1.0, [_shop(over=19.9)])) is False
    assert t.should_decide(_state(2.0, [_shop(over=20.0)])) is True  # crosses upward (>=)
    assert t.should_decide(_state(3.0, [_shop(over=25.0)])) is False  # stays above
    assert t.should_decide(_state(4.0, [_shop(over=10.0)])) is False  # falling never fires
    assert t.should_decide(_state(5.0, [_shop(over=21.0)])) is True  # crosses again


def test_event_tracker_upgraded_flip():
    t = _primed(_shop(upgraded=False))
    assert t.should_decide(_state(1.0, [_shop(upgraded=False)])) is False
    assert t.should_decide(_state(2.0, [_shop(upgraded=True)])) is True
    assert t.should_decide(_state(3.0, [_shop(upgraded=True)])) is False


def test_event_tracker_road_stock_rise():
    h = house(1, 0, 20, 13, 4)
    t = _primed(h, inventory=(25, 1, 0, 0, 0, 0))
    assert t.should_decide(_state(1.0, [h], inventory=(20, 1, 0, 0, 0, 0))) is False  # spending: no
    assert t.should_decide(_state(2.0, [h], inventory=(21, 1, 0, 0, 0, 0))) is True  # refund: yes
    assert t.should_decide(_state(3.0, [h], inventory=(21, 1, 0, 0, 0, 0))) is False


def test_event_tracker_fallback_counts_from_last_true():
    h = house(1, 0, 20, 13, 4)
    t = _primed(h)
    assert t.should_decide(_state(9.9, [h])) is False
    assert t.should_decide(_state(10.0, [h])) is True
    assert t.should_decide(_state(19.0, [h])) is False


# --- decide() with a fake session -------------------------------------------------------------------------

def _cand(house_id, tiles, tag=0):
    return RouteCandidate(kind="attach", house_id=house_id, shop_ids=(), path=((0, tag), (1, tag)),
                          tiles_needed=tiles, bridges_needed=0, turns=0, new_junctions=0, shared_cells=0, strokes=())


class _FakeSession:
    """Just what decide() reads; targets, candidates and execution are monkeypatched into agent."""

    memory = None  # the patched feature functions below ignore the per-game memory

    def __init__(self, targets, cands, offers=(), road_stock=25):
        self.targets = list(targets)  # [(house, shops)]
        self.cands = cands  # house id -> [RouteCandidate]
        self.served = set()
        self.reached = set()  # (house id, shop id) pairs a house reaches (coverage tests)
        self.road_stock = road_stock
        self.done = False
        self.log = []
        self.state = None
        self.install(offers=tuple(offers), road_stock=road_stock)

    def install(self, **changes):
        """Install a new state, as each real command does. Like CityState, it is a snapshot: shop_served
        answers from the served set as it is now, so code that keeps reading an old state sees old answers."""
        fields = {"offers": (), "road_stock": self.road_stock} if self.state is None else \
            {"offers": self.state.offers, "road_stock": self.state.road_stock}
        fields.update(changes)
        frozen = frozenset(self.served)
        self.state = SimpleNamespace(**fields, shop_served=lambda s: s.id in frozen,
                                     reached=frozenset(self.reached))


def _b(id):
    return SimpleNamespace(id=id)


def _patch(monkeypatch, sess, outcome=None):
    """outcome: house id -> (execute_route result, whether its target shops become served). Default: success."""
    outcome = outcome or {}

    def execute(session, cand):
        session.log.append(("route", cand.house_id, cand.path[0][1]))
        ok, serve = outcome.get(cand.house_id, (True, True))
        if serve:
            for h, shops in list(session.targets):
                if h.id == cand.house_id:
                    session.targets.remove((h, shops))
                    session.served.update(s.id for s in shops)
        session.install()
        return ok

    def offer(session, i):
        session.log.append(("offer", i))
        return True

    monkeypatch.setattr(agent, "unserved_targets", lambda state: list(sess.targets))
    monkeypatch.setattr(agent, "route_candidates", lambda state, h, shops: list(sess.cands.get(h.id, [])))
    monkeypatch.setattr(agent, "global_features", lambda state, memory=None: {"road_stock": float(sess.road_stock)})
    # The fake states are SimpleNamespaces: score candidates and offers on their state-free Phase 1 features.
    monkeypatch.setattr(agent, "candidate_features", lambda state, cand, memory=None: route_features(cand))
    monkeypatch.setattr(agent, "offer_features", lambda offer, state=None: offer_features(offer))
    monkeypatch.setattr(agent, "execute_route", execute)
    monkeypatch.setattr(agent, "take_offer", offer)


@pytest.mark.parametrize("offers, expected", [
    ((Offer(0, 0, 0, 30), Offer(1, 1, 1, 30)), 0),  # equal offer_roads: lower index
    ((Offer(0, 1, 1, 20), Offer(1, 0, 0, 30)), 1),  # higher offer_roads wins
    ((Offer(0, 0, 10, 20), Offer(1, 0, 0, 30)), 0),  # a type-0 amount counts as roads: 30 vs 30 -> index 0
])
def test_decide_offer_choice_and_ties(monkeypatch, offers, expected):
    sess = _FakeSession([], {}, offers=offers)
    _patch(monkeypatch, sess)
    decide(sess, HandRule())
    assert sess.log == [("offer", expected)]


def test_decide_always_takes_an_offer_even_with_non_finite_scores(monkeypatch):
    class NanUpgrade(HandRule):
        def upgrade(self, f):
            return float("nan") if f["type_0"] else float("-inf")
    sess = _FakeSession([], {}, offers=(Offer(0, 0, 0, 30), Offer(1, 1, 1, 20)))
    _patch(monkeypatch, sess)
    decide(sess, NanUpgrade())
    assert sess.log == [("offer", 0)]


def test_decide_hold_stops_routing(monkeypatch):
    # HandRule: hold = 4 - 5 = -1. Priority -1 (1 tile) clears it (>=); priority -2 does not.
    h1, h2, s = _b(1), _b(2), _b(100)
    sess = _FakeSession([(h1, (s,)), (h2, (s,))], {1: [_cand(1, 1)], 2: [_cand(2, 2)]}, road_stock=5)
    _patch(monkeypatch, sess)
    decide(sess, HandRule())
    assert sess.log == [("route", 1, 0)]


def test_decide_route_ties_prefer_earlier_target_then_earlier_candidate(monkeypatch):
    h1, h2 = _b(1), _b(2)
    sess = _FakeSession([(h2, (_b(100),)), (h1, (_b(101),))],
                        {1: [_cand(1, 3, tag=0)], 2: [_cand(2, 3, tag=7), _cand(2, 3, tag=8)]})
    _patch(monkeypatch, sess)
    decide(sess, HandRule())
    assert sess.log == [("route", 2, 7), ("route", 1, 0)]


def test_decide_skips_non_finite_priorities(monkeypatch):
    class NanFirst(HandRule):
        def priority(self, f):
            return float("nan") if f["tiles_needed"] == 1 else -f["tiles_needed"]
    sess = _FakeSession([(_b(1), (_b(100),))], {1: [_cand(1, 1, tag=0), _cand(1, 2, tag=1)]})
    _patch(monkeypatch, sess)
    decide(sess, NanFirst())
    assert sess.log == [("route", 1, 1)]


def test_decide_does_not_retry_a_failed_house(monkeypatch):
    # Ruling 1: house 1's cheaper route fails; it is not tried again in this call, but house 2 still is.
    h1, h2 = _b(1), _b(2)
    sess = _FakeSession([(h1, (_b(100),)), (h2, (_b(101),))], {1: [_cand(1, 1)], 2: [_cand(2, 3)]})
    _patch(monkeypatch, sess, {1: (False, False)})
    decide(sess, HandRule())
    assert sess.log == [("route", 1, 0), ("route", 2, 0)]


def test_decide_treats_a_still_unserved_target_shop_as_failed(monkeypatch):
    # A house already connected elsewhere (execute_route True) whose target shop stays unserved is not retried.
    sess = _FakeSession([(_b(1), (_b(100),))], {1: [_cand(1, 1)]})
    _patch(monkeypatch, sess, {1: (True, False)})
    decide(sess, HandRule())
    assert sess.log == [("route", 1, 0)]


def test_decide_route_limit(monkeypatch):
    houses = [_b(i) for i in range(1, 30)]  # 29 targets, all buildable
    sess = _FakeSession([(h, (_b(1000 + h.id),)) for h in houses], {h.id: [_cand(h.id, 0)] for h in houses})
    _patch(monkeypatch, sess)
    decide(sess, HandRule())
    assert len(sess.log) == 20


def test_decide_stops_when_the_game_ends(monkeypatch):
    sess = _FakeSession([(_b(1), (_b(100),))], {1: [_cand(1, 1)]}, offers=(Offer(0, 0, 0, 30),))
    _patch(monkeypatch, sess)

    def offer_then_over(session, i):
        session.log.append(("offer", i))
        session.done = True
    monkeypatch.setattr(agent, "take_offer", offer_then_over)
    monkeypatch.setattr(agent, "unserved_targets", lambda state: pytest.fail("planned after the game ended"))
    decide(sess, HandRule())
    assert sess.log == [("offer", 0)]

    sess.log.clear()
    decide(sess, HandRule())  # already over: nothing at all, not even the pending offer
    assert sess.log == []


# --- GameResult / play_game -------------------------------------------------------------------------------

def test_game_result_summary_excludes_recording():
    r = GameResult(trips=1, seconds=2.0, rejected_actions=0, commands=3, action_counts={"wait": 3},
                   mean_car_wait=0.0, max_car_wait=0.0, terminated=False, truncated=True, scenario_seed=7,
                   city="LosAngeles", deterministic=True, failed_shop=None, road_tiles_at_failure=None,
                   recording={"actions": []})
    s = r.summary()
    assert "recording" not in s and r.recording == {"actions": []}
    assert set(s) == set(GameResult.__dataclass_fields__) - {"recording"}
    json.dumps(s)


def test_play_game_failure_fields_from_final_state(monkeypatch):
    """failed_shop = the shop with the largest overcrowded_for (lower id on ties); road tiles = inventory[0]."""
    final = make_obs(buildings=[_shop(5, over=50.2), _shop(9, over=50.2), _shop(3, over=12.0), house(1, 0, 20, 13, 4)],
                     inventory=(7, 0, 0, 0, 0, 0), time=88.0)

    class Over(GameSession):
        def reset(self):
            self.raw, self.state, self.terminated = final, parse_observation(final), True
            return self.state

    monkeypatch.setattr(agent, "GameSession", Over)
    r = play_game(None, 4, HandRule(), record=False)
    assert (r.failed_shop, r.road_tiles_at_failure, r.terminated, r.truncated) == (5, 7, True, False)
    assert (r.recording, r.scenario_seed, r.city, r.deterministic, r.mean_car_wait) == (None, 4, "LosAngeles", True, 0.0)


@pytest.mark.host
def test_terminated_game_reports_failure(host):
    r = play_game(host, 2000, DoNothing())
    assert r.terminated and not r.truncated and r.road_tiles_at_failure == 25  # DoNothing never spends or takes offers
    assert r.recording["source"] == "evolved-rules:nothing" and r.recording["terminated"]
    # The same game played by hand ends in the same state: failed_shop is its most overcrowded shop.
    s = GameSession(host, 2000)
    s.reset()
    while not s.done:
        s.wait()
    worst = max(s.state.shops(), key=lambda b: (b.overcrowded_for, -b.id))
    assert r.failed_shop == worst.id and worst.overcrowded_for >= 50.0
    assert r.summary()["failed_shop"] == worst.id and "recording" not in r.summary()


# --- Fix round 1: spec literals, features, non-finite scores, loop shape, GameResult wiring ----------------

def test_spec_constants():
    assert (FALLBACK_S, OVERCROWD_EVENT_S, MAX_ROUTES_PER_DECISION) == (10.0, 20.0, 20)


def test_policy_names():
    assert HandRule.name == "hand" and DoNothing.name == "nothing"
    assert HandRule().name == "hand" and DoNothing().name == "nothing"


def test_event_tracker_first_call_fires_with_no_buildings():
    assert EventTracker().should_decide(_state(0.0, [])) is True


def test_event_tracker_upgraded_flip_back_fires():
    t = _primed(_shop(upgraded=True))
    assert t.should_decide(_state(1.0, [_shop(upgraded=False)])) is True
    assert t.should_decide(_state(2.0, [_shop(upgraded=False)])) is False


@pytest.mark.parametrize("kind, onehot", [
    ("attach", (1.0, 0.0, 0.0)), ("direct", (0.0, 1.0, 0.0)), ("separated", (0.0, 0.0, 1.0)),
])
def test_candidate_features_exact(kind, onehot):
    # Pairwise-distinct values (none 0 or 1), so a feature read from the wrong field or squashed to a flag shows.
    path = ((0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2))  # 6 cells, 5 steps
    c = RouteCandidate(kind=kind, house_id=1, shop_ids=(5,), path=path, tiles_needed=3, bridges_needed=2,
                       turns=7, new_junctions=4, shared_cells=6, strokes=())
    phase1 = {
        "tiles_needed": 3.0, "bridges_needed": 2.0, "path_len": 5.0, "turns": 7.0, "new_junctions": 4.0,
        "shared_cells": 6.0, "is_attach": onehot[0], "is_direct": onehot[1], "is_separated": onehot[2]}
    assert route_features(c) == phase1
    # Phase 2 only appends keys: the Phase 1 ones come first, in order, with the same values.
    f = candidate_features(parse_observation(make_obs()), c)
    assert dict(list(f.items())[:len(phase1)]) == phase1 and list(f)[:len(phase1)] == list(phase1)


def test_global_features_exact():
    # House 1 (colour 0) is linked to shop 5's entrance through (29, 11); houses 2 and 4 (colour 0) are not
    # linked, so 2 houses (1 colour) are unserved; house 3 (colour 1) has no shop of its colour, so is not counted.
    s = parse_observation(make_obs(
        buildings=[shop(5, 0, 30, 10, 2, 2, [(30, 11, 4)]), house(1, 0, 28, 11, 0), house(2, 0, 20, 13, 4),
                   house(3, 1, 22, 13, 4), house(4, 0, 20, 20, 4)],
        roads={(28, 11): 1 << 0, (29, 11): (1 << 0) | (1 << 4), (30, 11): 1 << 4},
        inventory=(17, 3, 0, 0, 0, 0), time=42.5))
    by_id = {b.id: b for b in s.buildings}
    assert s.house_connected(by_id[1]) and not s.house_connected(by_id[2]) and not s.house_connected(by_id[4])
    g = global_features(s)
    phase1 = {"road_stock": 17.0, "bridge_stock": 3.0, "time": 42.5, "unserved_houses": 2.0}
    assert dict(list(g.items())[:4]) == phase1 and list(g)[:4] == list(phase1)  # Phase 2 only appends keys


def test_offer_features_exact():
    # type 3, amount 2: amount differs from the type and from 1, so neither a constant 1 nor offer.type passes
    phase1 = {"offer_roads": 20.0, "amount": 2.0,
              "type_0": 0.0, "type_1": 0.0, "type_2": 0.0, "type_3": 1.0, "type_4": 0.0, "type_5": 0.0}
    f = offer_features(Offer(0, 3, 2, 20))
    assert dict(list(f.items())[:8]) == phase1 and list(f)[:8] == list(phase1)  # Phase 2 only appends keys
    for t in range(6):
        f = offer_features(Offer(1, t, 2, 10))
        assert [f[f"type_{i}"] for i in range(6)] == [1.0 if i == t else 0.0 for i in range(6)]
    assert offer_features(Offer(0, 0, 10, 20))["offer_roads"] == 30.0  # type 0: amount counts as roads


def test_decide_finite_offer_beats_nan(monkeypatch):
    class P(HandRule):
        def upgrade(self, f):
            return float("nan") if f["type_0"] else 5.0
    sess = _FakeSession([], {}, offers=(Offer(0, 0, 0, 30), Offer(1, 1, 1, 20)))
    _patch(monkeypatch, sess)
    decide(sess, P())
    assert sess.log == [("offer", 1)]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_decide_non_finite_hold_builds_nothing(monkeypatch, bad):
    class P(HandRule):
        def hold(self, g):
            return bad
    sess = _FakeSession([(_b(1), (_b(100),))], {1: [_cand(1, 0)]})
    _patch(monkeypatch, sess)
    decide(sess, P())
    assert sess.log == []


def test_decide_failed_route_not_retried_even_if_target_shop_served(monkeypatch):
    # Ruling 1 on its own: execute_route returns False although the target shop is now served (by some other
    # house), and the target stays listed. The failing house must not be redrawn in this call.
    sess = _FakeSession([(_b(1), (_b(100),))], {1: [_cand(1, 1)]})
    _patch(monkeypatch, sess)

    def execute(session, cand):
        session.log.append(("route", cand.house_id, 0))
        session.served.add(100)
        session.install()
        return False
    monkeypatch.setattr(agent, "execute_route", execute)
    decide(sess, HandRule())
    assert sess.log == [("route", 1, 0)]


def _restate(sess, **changes):
    """Replace sess.state by a new snapshot state (as a real command does), with some fields changed."""
    sess.install(**changes)


def _patch_stock(monkeypatch, sess, offer_roads=0):
    """Like _patch, but road stock lives on the state object: building spends tiles_needed, an offer adds
    offer_roads, and each command replaces session.state, so a hold read from an old state is stale."""
    _patch(monkeypatch, sess)
    _restate(sess, road_stock=sess.road_stock)
    monkeypatch.setattr(agent, "global_features", lambda state, memory=None: {"road_stock": float(state.road_stock)})

    def execute(session, cand):
        session.log.append(("route", cand.house_id, cand.path[0][1]))
        session.targets = [t for t in session.targets if t[0].id != cand.house_id]
        session.served.add(1000 + cand.house_id)
        _restate(session, road_stock=session.state.road_stock - cand.tiles_needed)
        return True

    def offer(session, i):
        session.log.append(("offer", i))
        _restate(session, offers=(), road_stock=session.state.road_stock + offer_roads)
        return True
    monkeypatch.setattr(agent, "execute_route", execute)
    monkeypatch.setattr(agent, "take_offer", offer)


def test_decide_hold_is_re_evaluated_after_each_route(monkeypatch):
    # HandRule keeps 4 tiles: stock 5 -> hold -1, a 1-tile route (priority -1) is built; stock 4 -> hold 0, stop.
    houses = [_b(1), _b(2)]
    sess = _FakeSession([(h, (_b(1000 + h.id),)) for h in houses], {h.id: [_cand(h.id, 1)] for h in houses},
                        road_stock=5)
    _patch_stock(monkeypatch, sess)
    decide(sess, HandRule())
    assert sess.log == [("route", 1, 0)]


def test_decide_hold_reads_the_state_after_the_offer_and_each_route(monkeypatch):
    # Stock 0 (hold 4: nothing buildable) until the offer adds 6: hold -2, -1, then 0 after two 1-tile routes.
    # A hold from the pre-offer state builds nothing; one computed once per decision builds all three.
    houses = [_b(1), _b(2), _b(3)]
    sess = _FakeSession([(h, (_b(1000 + h.id),)) for h in houses], {h.id: [_cand(h.id, 1)] for h in houses},
                        offers=(Offer(0, 0, 0, 6),), road_stock=0)
    _patch_stock(monkeypatch, sess, offer_roads=6)
    decide(sess, HandRule())
    assert sess.log == [("offer", 0), ("route", 1, 0), ("route", 2, 0)]


@pytest.mark.parametrize("first_served", [100, 101])
def test_decide_house_target_served_by_one_of_two_shops_stays_eligible(monkeypatch, first_served):
    # A house-type target lists both shops of its colour. The first route reaches only `first_served`; the house
    # is then relisted for the other shop (as unserved_targets does) and must be routed again in this decision.
    # Each route installs a new snapshot state, so a check that reads the pre-route state sees nothing served.
    h, other = _b(1), 101 if first_served == 100 else 100
    sess = _FakeSession([(h, (_b(100), _b(101)))], {1: [_cand(1, 1)]})
    _patch(monkeypatch, sess)

    def execute(session, cand):
        session.log.append(("route", cand.house_id, 0))
        if first_served not in session.served:
            session.served.add(first_served)
            session.targets = [(h, (_b(other),))]
        else:
            session.served.add(other)
            session.targets = []
        session.install()
        return True
    monkeypatch.setattr(agent, "execute_route", execute)
    decide(sess, HandRule())
    assert sess.log == [("route", 1, 0), ("route", 1, 0)]


def _fake_game(monkeypatch, obs, terminated, **counters):
    """Patch agent.GameSession so reset() lands on `obs` with the given counters (no host)."""
    class S(GameSession):
        def reset(self):
            self._clear()
            self.raw, self.state, self.terminated = obs, parse_observation(obs), terminated
            for k, v in counters.items():
                setattr(self, k, v)
            return self.state
    monkeypatch.setattr(agent, "GameSession", S)
    return S


def test_play_game_copies_session_counters(monkeypatch):
    _fake_game(monkeypatch, make_obs(buildings=[_shop(5, over=51.0)], time=50.0), True,
               wait_sum=6.0, wait_n=4, max_wait=3.0, commands=7, rejected=2, action_counts={"wait": 5, "Road": 2})
    r = play_game(None, 1, HandRule(), record=False)
    assert (r.mean_car_wait, r.max_car_wait, r.commands, r.rejected_actions, r.action_counts, r.seconds) == \
        (1.5, 3.0, 7, 2, {"wait": 5, "Road": 2}, 50.0)


def test_play_game_truncated_at_cap_has_no_failure_fields(monkeypatch):
    _fake_game(monkeypatch, make_obs(buildings=[_shop(5, over=30.0)], time=100.0), False)
    r = play_game(None, 1, HandRule(), cap_s=100.0, record=False)
    assert (r.truncated, r.terminated, r.failed_shop, r.road_tiles_at_failure) == (True, False, None, None)


def test_play_game_terminated_at_cap_is_not_truncated(monkeypatch):
    _fake_game(monkeypatch, make_obs(buildings=[_shop(5, over=51.0)], time=100.0), True)
    r = play_game(None, 1, HandRule(), cap_s=100.0, record=False)
    assert (r.truncated, r.terminated, r.failed_shop, r.road_tiles_at_failure) == (False, True, 5, 25)


def test_play_game_no_wait_after_a_decision_that_ends_the_game(monkeypatch):
    S = _fake_game(monkeypatch, make_obs(buildings=[house(1, 0, 20, 13, 4)], time=0.0), False)
    calls, waits = [], []
    real_wait = S.wait

    def counting_wait(self):
        waits.append(self.state.time)
        return real_wait(self)  # on a finished game this raises GameSession's RuntimeError
    monkeypatch.setattr(S, "wait", counting_wait)

    def fake_decide(session, policy):
        calls.append(session.state.time)
        session.terminated = True
    monkeypatch.setattr(agent, "decide", fake_decide)
    r = play_game(None, 1, HandRule(), record=False)
    assert calls == [0.0] and waits == [] and r.terminated


def test_play_game_do_nothing_never_decides(monkeypatch):
    offer = [{"type": 0, "amount": 0, "roads": 30}]
    S = _fake_game(monkeypatch, make_obs(buildings=[house(1, 0, 20, 13, 4)], time=0.0, offers=offer), False)
    monkeypatch.setattr(agent, "decide", lambda s, p: pytest.fail("DoNothing decided"))
    monkeypatch.setattr(S, "wait", lambda self: setattr(self, "terminated", True))
    r = play_game(None, 1, DoNothing(), record=False)
    assert r.terminated


# --- decide() for coverage policies (Phase 2, task 2) -------------------------------------------------------

class _Cover(HandRule):
    """The hand rule with coverage targets."""

    name = "cover"
    coverage = True


def _patch_cover(monkeypatch, sess, outcome=None, keep=False):
    """Coverage fakes: targets come from coverage_targets; a candidate's tag is its first target shop id;
    outcome: (house id, shop id) -> (execute_route result, shop ids the house reaches afterwards). Default:
    success, the house reaches the tagged shop. Targets with a reached pair are dropped (as coverage_targets
    does) unless keep. house_reaches reads the installed snapshot, as the real one reads session.state."""
    _patch(monkeypatch, sess)
    outcome = outcome or {}
    sess.asked = []

    def cands(state, h, shops):
        sess.asked.append((h.id, tuple(s.id for s in shops)))
        return [_cand(h.id, 1, tag=shops[0].id)]

    def execute(session, cand):
        hid, sid = cand.house_id, cand.path[0][1]
        session.log.append(("route", hid, sid))
        ok, reached = outcome.get((hid, sid), (True, (sid,)))
        session.reached.update((hid, r) for r in reached)
        if not keep:
            session.targets = [(h, sh) for h, sh in session.targets
                               if not any((h.id, s.id) in session.reached for s in sh)]
        session.install()
        return ok

    monkeypatch.setattr(agent, "unserved_targets", lambda state: pytest.fail("a coverage policy used Phase 1 targets"))
    monkeypatch.setattr(agent, "coverage_targets", lambda state: list(sess.targets))
    monkeypatch.setattr(agent, "route_candidates", cands)
    monkeypatch.setattr(agent, "execute_route", execute)
    monkeypatch.setattr(agent, "house_reaches",
                        lambda state, hid, shops: any((hid, s.id) in state.reached for s in shops))


def test_decide_phase1_policy_never_uses_coverage_targets(monkeypatch):
    sess = _FakeSession([(_b(1), (_b(100),))], {1: [_cand(1, 1)]})
    _patch(monkeypatch, sess)
    monkeypatch.setattr(agent, "coverage_targets", lambda state: pytest.fail("Phase 1 policy used coverage"))
    monkeypatch.setattr(agent, "house_reaches", lambda *a: pytest.fail("Phase 1 policy used the coverage rule"))
    decide(sess, HandRule())
    assert sess.log == [("route", 1, 0)]


def test_decide_coverage_routes_one_house_to_two_shops(monkeypatch):
    # The same (served) house is a target for two shops it does not reach: both routes are built.
    h = _b(1)
    sess = _FakeSession([(h, (_b(100),)), (h, (_b(101),))], {})
    _patch_cover(monkeypatch, sess)
    decide(sess, _Cover())
    assert sess.log == [("route", 1, 100), ("route", 1, 101)]


def test_decide_coverage_failure_excludes_the_pair_not_the_house(monkeypatch):
    # (1, 100) fails: under Phase 1 rules house 1 would be dropped; here only that pair is, so (1, 101) is
    # still built, and (1, 100), still listed, is not redrawn in this decision.
    h = _b(1)
    sess = _FakeSession([(h, (_b(100),)), (h, (_b(101),))], {})
    _patch_cover(monkeypatch, sess, {(1, 100): (False, ())})
    decide(sess, _Cover())
    assert sess.log == [("route", 1, 100), ("route", 1, 101)]


def test_decide_coverage_success_means_the_house_reaches_a_target_shop(monkeypatch):
    # execute_route reports the house connected (to some shop), but it does not reach shop 100: a failure,
    # so the still-listed target is not redrawn.
    sess = _FakeSession([(_b(1), (_b(100),))], {})
    _patch_cover(monkeypatch, sess, {(1, 100): (True, ())}, keep=True)
    decide(sess, _Cover())
    assert sess.log == [("route", 1, 100)]


def test_decide_coverage_success_even_if_execute_route_reports_failure(monkeypatch):
    # The house reaches shop 100 (the success rule) although execute_route says False: not excluded. The fake
    # keeps listing the target (the real coverage_targets would drop it), so it is drawn up to the route limit.
    sess = _FakeSession([(_b(1), (_b(100),))], {})
    _patch_cover(monkeypatch, sess, {(1, 100): (False, (100,))}, keep=True)
    decide(sess, _Cover())
    assert sess.log == [("route", 1, 100)] * MAX_ROUTES_PER_DECISION


def test_decide_coverage_excluded_pairs_filter_a_target_shop_list(monkeypatch):
    # (1, 100) fails; the still-listed target (1, (100, 101)) is then planned towards shop 101 alone.
    h = _b(1)
    sess = _FakeSession([(h, (_b(100),)), (h, (_b(100), _b(101)))], {})
    _patch_cover(monkeypatch, sess, {(1, 100): (False, ())})
    decide(sess, _Cover())
    assert sess.asked == [(1, (100,)), (1, (100, 101)), (1, (101,))]
    assert sess.log == [("route", 1, 100), ("route", 1, 101)]


def test_decide_coverage_skips_target_whose_pairs_are_all_excluded(monkeypatch):
    h = _b(1)
    sess = _FakeSession([(h, (_b(100),))], {})
    _patch_cover(monkeypatch, sess, {(1, 100): (False, ())})
    decide(sess, _Cover())
    assert sess.log == [("route", 1, 100)] and sess.asked == [(1, (100,))]


@pytest.mark.host
def test_coverage_policy_game_is_a_valid_repeatable_replay(host, verifier, tmp_path, monkeypatch):
    """A real coverage game (hand rule + coverage) builds coverage routes, verifies as a replay and repeats
    exactly on the same host."""
    from evolved_rules.verify import verify_recording
    from evolved_rules import candidates
    calls = {"extra": 0, "reached": 0}
    extra_keys: set = set()
    real_targets, real_reaches = agent.coverage_targets, agent.house_reaches

    def counting(state):
        out = real_targets(state)
        # Only entries past the Phase 1 prefix are coverage extras; unserved_targets entries do not count.
        extras = out[len(candidates.unserved_targets(state)):]
        extra_keys.clear()
        extra_keys.update((h.id, tuple(s.id for s in sh)) for h, sh in extras)
        calls["extra"] += len(extras)
        return out

    def reaching(state, house_id, shops):
        ok = real_reaches(state, house_id, shops)
        if ok and (house_id, tuple(s.id for s in shops)) in extra_keys:
            calls["reached"] += 1  # a route for a coverage-only pair was built and now reaches its shop
        return ok
    monkeypatch.setattr(agent, "coverage_targets", counting)
    monkeypatch.setattr(agent, "house_reaches", reaching)
    a = play_game(host, 1000, _Cover(), cap_s=300.0)
    assert calls["extra"] > 0  # coverage-only pairs were offered to the policy
    assert calls["reached"] > 0  # and at least one was routed successfully
    monkeypatch.setattr(agent, "coverage_targets", real_targets)
    monkeypatch.setattr(agent, "house_reaches", real_reaches)
    b = play_game(host, 1000, _Cover(), cap_s=300.0)
    assert a.recording["actions"] == b.recording["actions"] and a.trips == b.trips > 0
    p = tmp_path / "g.json"; p.write_text(json.dumps(a.recording))
    assert verify_recording(p)[0]
