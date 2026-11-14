"""gp-7 (plan 2026-11-14 section 3.1) fast tests: text trailers, cache keys, flags, the evo edge cost's bit
identity with the legacy separated cost, A* identity at the separated vector, light-only decision times, the
target head's ordering, and the no-op guard. The game-level identity gates are evolved_rules/ops/identity7.py."""
from __future__ import annotations

import copy
import itertools
import math
import pickle
from pathlib import Path
from types import SimpleNamespace

import pytest

from evolved_rules import candidates as C
from evolved_rules import gp, planner7
from evolved_rules.agent import EventTracker
from evolved_rules.engine import canonical_text
from evolved_rules.state import parse_observation
from evolved_rules.tests.helpers import house, make_obs, shop

SEEDS = Path(__file__).resolve().parents[1] / "seeds" / "gp7"
L = (SEEDS / "cma1_3tree.txt").read_text().strip()
OFF_PLANNER = ("planner: cost=1.0,0.15,0.05,0.5,0.0,0.0,3.0,0.0,0.0,0.0; target=0.0,0.0,0.0,0.0,0.0,0.0,0.0; "
               "theta=600.0")
FLAGS0 = "flags: clean=0 lights=0 roundabouts=0"


# --- text format ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", sorted(SEEDS.glob("*.txt")), ids=lambda p: p.name)
def test_texts_without_trailers_canonicalise_as_before(path):
    t = path.read_text().strip()
    ind = gp.individual_from_text(t)
    assert ind.flags is None and ind.planner is None
    assert gp.individual_text(ind) == gp.individual_text(gp.individual_from_text(gp.individual_text(ind)))
    assert "flags:" not in gp.individual_text(ind) and "planner:" not in gp.individual_text(ind)


def test_hand_and_separated_texts_unchanged():
    for t in (gp.HAND_TEXT, gp.SEPARATED_TEXT, gp.CLEAN_TEXT):
        assert gp.individual_text(gp.individual_from_text(t)) == t


def test_trailers_round_trip_pickle_and_deepcopy():
    t = f"{L}\n{FLAGS0}\n{OFF_PLANNER}"
    ind = gp.individual_from_text(t)
    assert gp.individual_text(ind) == t
    assert gp.individual_text(pickle.loads(pickle.dumps(ind))) == t
    assert gp.individual_text(copy.deepcopy(ind)) == t
    assert isinstance(ind.planner, gp.Planner) and ind.planner.c("w_for") == 3.0 and ind.planner.theta == 600.0


def test_planner_floats_are_canonicalised_with_repr():
    t = f"{L}\nplanner: cost=1,0.15,.05,0.5,0,-0,3,0,0,0; target=0,0,0,0,0,0,1.9; theta=6e2"
    out = gp.individual_text(gp.individual_from_text(t))
    assert out.endswith("planner: cost=1.0,0.15,0.05,0.5,0.0,0.0,3.0,0.0,0.0,0.0; "
                        "target=0.0,0.0,0.0,0.0,0.0,0.0,1.9; theta=600.0")
    assert gp.individual_text(gp.individual_from_text(out)) == out


@pytest.mark.parametrize("bad", [
    f"{L}\n{OFF_PLANNER}\n{FLAGS0}",                                       # out of order
    f"{L}\n{FLAGS0}\n{FLAGS0}",                                            # repeated
    f"{L}\nflags: clean=0 lights=0",                                       # malformed flags
    f"{L}\nflags: clean=2 lights=0 roundabouts=0",                         # not 0/1
    f"{L}\nflags: clean=0 lights=1 roundabouts=0",                         # lights without a place tree
    f"{L}\nplanner: cost=1.0; target=0.0; theta=1.0",                      # wrong counts
    f"{L}\n" + OFF_PLANNER.replace("theta=600.0", "theta=inf"),           # non-finite
    f"{L}\n" + OFF_PLANNER.replace("cost=1.0", "cost=nan"),
    f"{L}\nmotorways: 1",                                                  # unknown trailer = a 4th tree line
])
def test_bad_trailers_raise(bad):
    with pytest.raises(ValueError):
        gp.individual_from_text(bad)


def test_v7_priority_terms_only_with_a_planner():
    t = L.replace("priority: add(", "priority: add(mul(1.0, is_evo), add(", 1).replace("\nhold:", ")\nhold:", 1)
    with pytest.raises(ValueError):
        gp.individual_from_text(t)
    ind = gp.individual_from_text(f"{t}\n{OFF_PLANNER}")
    assert "is_evo" in str(ind[0])


def test_cache_keys_tell_trailers_apart():
    a, b = canonical_text(L), canonical_text(f"{L}\n{FLAGS0}\n{OFF_PLANNER}")
    assert a == L and a != b and canonical_text(b) == b


def test_flags_override_tree_count_defaults():
    five = gp.with_place(L, "if_gt(pl_is_light, 0.5, pl_stopped_near, -1.0)")
    p = gp.TreePolicy(five)
    assert p.clean_routes and p.places_lights and p.places_roundabouts and not p.v7
    q = gp.TreePolicy(f"{five}\nflags: clean=0 lights=1 roundabouts=0")
    assert not q.clean_routes and q.places_lights and not q.places_roundabouts and not q.removes
    r = gp.TreePolicy(f"{L}\n{FLAGS0}\n{OFF_PLANNER}")
    assert r.v7 and r.moves == "v7" and not r.clean_routes and not r.places_lights and r.planner.m_eff == 0


@pytest.mark.parametrize("n_t,m", [(-3.0, 0), (0.0, 0), (0.99, 0), (1.2, 1), (2.0, 2), (5.9, 5), (6.0, 6), (40.0, 6)])
def test_m_eff_clip(n_t, m):
    p = gp.Planner((0.0,) * 10, (0.0,) * 6 + (n_t,), 0.0)
    assert p.m_eff == m


# --- edge cost: bit identity with the legacy separated search ----------------------------------------------

def _legacy_separated(diagonal, paid, ju, jn_target, foreign):
    """The legacy step cost, copied from candidates._astar (clean False, separated True)."""
    cost = (C.DIAG_BASE if diagonal else 1.0) * (1.0 if paid else C.ROAD_FACTOR) + C.STEP_EXTRA
    if ju:
        cost += C.JUNCTION_PENALTY
    if jn_target:
        cost += C.JUNCTION_PENALTY
    if foreign:
        cost += C.FOREIGN_PENALTY
    return cost


def test_evo_step_is_bit_identical_to_legacy_at_the_separated_vector(monkeypatch):
    u, prev = (10, 10), (9, 10)
    for (dx, dy), paid, ju, jn, foreign in itertools.product(
            [d for d in C.DIRS], (False, True), (False, True), (False, True), (False, True)):
        n = (u[0] + dx, u[1] + dy)
        diagonal = dx != 0 and dy != 0
        monkeypatch.setattr(C, "_becomes_junction", lambda st, c, nb, _ju=ju, _jn=jn: _ju if c == u else _jn)
        monkeypatch.setattr(C, "_foreign", lambda served, c, color, _f=foreign: _f)
        monkeypatch.setattr(C, "_junction_link", lambda *a: True)  # w_jl = w_ns = 0: must not matter
        got = C._evo_step(None, C.SEPARATED_EVO, 0, {}, frozenset({n}) if jn else frozenset(), frozenset(), prev,
                          u, n, diagonal, paid)
        want = _legacy_separated(diagonal, paid, ju, jn, foreign)
        assert got == want and math.copysign(1, got) == math.copysign(1, want), ((dx, dy), paid, ju, jn, foreign)


def test_evo_step_floor_keeps_astar_admissible(monkeypatch):
    monkeypatch.setattr(C, "_becomes_junction", lambda *a: False)
    monkeypatch.setattr(C, "_foreign", lambda *a: False)
    cheap = C.EvoCost(w_paid=-5.0, w_reuse=-5.0, w_step=-5.0, w_jn=0.0, w_jl=0.0, w_ns=0.0, w_for=0.0,
                      M={(11, 10): -3.0})
    assert C._evo_step(None, cheap, 0, {}, frozenset(), frozenset(), None, (10, 10), (11, 10), False, True) == C._MIN_ORTH
    assert C._evo_step(None, cheap, 0, {}, frozenset(), frozenset(), None, (10, 10), (11, 11), True, False) == C._MIN_DIAG


def test_evo_step_new_terms(monkeypatch):
    monkeypatch.setattr(C, "_becomes_junction", lambda *a: False)
    monkeypatch.setattr(C, "_foreign", lambda *a: False)
    monkeypatch.setattr(C, "_junction_link", lambda st, c, nb: c == (10, 10))
    e = C.EvoCost(w_paid=1.0, w_reuse=0.5, w_step=0.0, w_jn=0.0, w_jl=2.0, w_ns=4.0, w_for=0.0, M={(11, 10): 0.25})
    near = frozenset({(10, 10)})
    got = C._evo_step(None, e, 0, {}, frozenset(), near, (9, 10), (10, 10), (11, 10), False, False)
    assert got == 0.5 + 2.0 + 4.0 + 0.25


# --- A* at the separated vector equals the legacy separated search -----------------------------------------

def _city():
    # two colours; a road strip of colour 1 between the house of colour 0 and its shop, so separated detours
    b = [house(1, 0, 5, 5, 0), shop(2, 0, 30, 5, 2, 2, [(30, 6, 4)]), house(3, 1, 5, 15, 0),
         shop(4, 1, 30, 15, 2, 2, [(30, 16, 4)])]
    roads = {}
    for x in range(10, 25):
        roads[(x, 10)] = (1 << C.DIRS.index((1, 0))) | (1 << C.DIRS.index((-1, 0)))
    return parse_observation(make_obs(buildings=b, roads=roads, inventory=(80, 2, 0, 0, 0, 0)))


def test_astar_evo_separated_equals_legacy_separated():
    st = _city()
    h = next(b for b in st.houses() if b.id == 1)
    shops = tuple(s for s in st.shops() if s.color == h.color)
    served = C._served_colours(st)
    targets = frozenset(o for s in shops for o in s.outside)
    a = C._astar(st, h, targets, frozenset(), frozenset(), served, separated=True)
    b = C._astar(st, h, targets, frozenset(), frozenset(), served, separated=False, evo=C.SEPARATED_EVO)
    assert a == b and a is not None


def test_route_candidates_evo_off_vector_adds_nothing():
    st = _city()
    for h in st.houses():
        shops = tuple(s for s in st.shops() if s.color == h.color)
        assert C.route_candidates(st, h, shops) == C.route_candidates(st, h, shops, evo=C.SEPARATED_EVO)


def test_evo_route_is_offered_when_it_differs_and_adds_links():
    st = _city()
    h = next(b for b in st.houses() if b.id == 1)
    shops = tuple(s for s in st.shops() if s.color == h.color)
    odd = C.EvoCost(w_paid=1.0, w_reuse=1.0, w_step=0.05, w_jn=0.5, w_jl=0.0, w_ns=0.0, w_for=0.0,
                    M={(x, y): 5.0 for x in range(6, 30) for y in range(4, 8)})
    out = C.route_candidates(st, h, shops, evo=odd)
    evo = [c for c in out if c.kind == "evo"]
    assert len(evo) == 1 and C.new_links(st, evo[0].path) >= 1
    assert all(evo[0].path != c.path for c in out if c.kind != "evo")


def test_new_links_counts_only_unlinked_steps():
    st = _city()
    assert C.new_links(st, ((10, 10), (11, 10), (12, 10))) == 0
    assert C.new_links(st, ((10, 10), (11, 10), (12, 11))) == 1
    assert C.new_links(st, ((10, 10), (11, 10), (12, 11)), frozenset({((11, 10), (12, 11))})) == 0


# --- light-only head with no light stock decides at v6 times -------------------------------------------------

def test_light_head_without_light_stock_decides_at_v6_times():
    from evolved_rules.tests.helpers import make_obs as mk
    veh = [{"color": 0, "stage": "Outbound", "waiting": 9.0, "speed": 0.0, "x": 6.5, "y": 5.5, "shopId": 2}]
    b = [house(1, 0, 5, 5, 0), shop(2, 0, 30, 5, 2, 2, [(30, 6, 4)])]
    states = [parse_observation(mk(buildings=b, time=t, vehicles=veh, inventory=(5, 1, 0, 0, 0, 0)))
              for t in (0.0, 3.0, 6.0, 9.0, 10.0, 13.0, 20.0, 26.0, 31.0)]
    plain, light = EventTracker(), EventTracker(kinds=(True, False))
    assert [plain.should_decide(s) for s in states] == [light.should_decide(s) for s in states]


# --- target head ---------------------------------------------------------------------------------------------

def test_picked_pairs_order_threshold_m_eff_and_tried():
    P = gp.Planner((0.0,) * 10, (0.0,) * 6 + (2.5,), 0.0)
    H = lambda i: SimpleNamespace(id=i)
    rows = [(0.5, H(3), H(9), False, ()), (0.7, H(4), H(9), False, ()), (0.5, H(1), H(8), True, ()),
            (-0.1, H(2), H(8), False, ()), (math.nan, H(5), H(8), False, ())]
    got = [(r[1].id, r[2].id) for r in planner7.picked_pairs(rows, P, set())]
    assert got == [(4, 9), (1, 8)]  # top 2 (m_eff = floor(2.5)), ties by house id; t <= 0 and nan never
    got = [(r[1].id, r[2].id) for r in planner7.picked_pairs(rows, P, {(4, 9)})]
    assert got == [(1, 8), (3, 9)]
    assert planner7.picked_pairs(rows, gp.Planner((0.0,) * 10, (0.0,) * 7, 0.0), set()) == []


def test_cell_maps_and_evo_cost_map():
    veh = [{"color": 0, "stage": "Outbound", "waiting": 0.0, "speed": 0.0, "x": 6.5, "y": 5.5, "shopId": 2},
           {"color": 0, "stage": "Outbound", "waiting": 0.0, "speed": 0.4, "x": 6.2, "y": 5.9, "shopId": 2},
           {"color": 0, "stage": "Home", "waiting": 0.0, "speed": 0.0, "x": 5.5, "y": 5.5, "shopId": -1}]
    b = [house(1, 0, 5, 5, 0), shop(2, 0, 30, 5, 2, 2, [(30, 6, 4)])]
    st = parse_observation(make_obs(buildings=b, vehicles=veh))
    cars, stopped = planner7.cell_maps(st)
    assert cars == {(6, 5): 2} and stopped == {(6, 5): 1}
    P = gp.Planner((1.0, 0.15, 0.05, 0.5, 0.0, 0.0, 3.0, 0.1, 0.5, 2.0), (0.0,) * 7, -1.0)  # gate open (0 > -1)
    e = planner7.evo_cost(st, P)
    assert e.M == {(6, 5): 0.1 * 2 + 0.5 * 1 + 2.0 * 1.0 * 1}
    off = planner7.evo_cost(st, gp.Planner((1.0, 0.15, 0.05, 0.5, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0), (0.0,) * 7, 0.0))
    assert off.M is None and off == C.SEPARATED_EVO
