"""GP representation (Phase 2 Task 3): primitive sets, terminal scaling, text round trip, TreePolicy, variation."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import pickle
import random

import pytest
from deap import gp as dgp

from evolved_rules import agent, gp
from evolved_rules.agent import decide, play_game
from evolved_rules.candidates import RouteCandidate
from evolved_rules.features import candidate_features, global_features, offer_features
from evolved_rules.rules import HandRule, SeparatedPreference
from evolved_rules.state import Offer, parse_observation
from evolved_rules.tests.helpers import house, make_obs, shop
from evolved_rules.tests.test_features import PHASE1_GAMES

SLOW = os.environ.get("EVOLVED_RULES_SLOW") == "1"


# --- terminals and scaling -----------------------------------------------------------------------------------

def _state():
    return parse_observation(make_obs(
        buildings=[house(1, 0, 5, 5, 0), shop(2, 0, 10, 5, 2, 2, [(10, 5, 4)])],
        roads={(6, 5): 0}, offers=[{"type": 1, "amount": 1, "roads": 3}], time=30.0))


def _cand():
    return RouteCandidate(kind="direct", house_id=1, shop_ids=(2,), path=((6, 5), (7, 5), (8, 5), (9, 5)),
                          tiles_needed=3, bridges_needed=0, turns=0, new_junctions=0, shared_cells=0, strokes=())


def test_terminal_lists_match_the_feature_dicts_in_order():
    state = _state()
    cand = candidate_features(state, _cand())
    glob = global_features(state)
    offer = offer_features(state.offers[0], state)
    def kept(d):
        return tuple(k for k in d if k not in gp.DROPPED_TERMS)

    assert gp.CANDIDATE_TERMS == kept(cand)
    assert gp.GLOBAL_TERMS == kept(glob)
    assert gp.OFFER_TERMS == kept(offer)
    # the dropped inputs are still computed by features.py: they are left out of the trees only
    assert gp.DROPPED_TERMS == {"type_5"}  # pending_refunds is back for gp-3 (removals make it vary)
    assert gp.DROPPED_TERMS <= set(glob) | set(offer)
    assert not gp.DROPPED_TERMS & (set(gp.PRIORITY_TERMS) | set(gp.HOLD_TERMS) | set(gp.UPGRADE_TERMS))
    assert gp.PRIORITY_TERMS == gp.CANDIDATE_TERMS + gp.GLOBAL_TERMS
    assert gp.HOLD_TERMS == gp.GLOBAL_TERMS
    assert gp.UPGRADE_TERMS == gp.OFFER_TERMS + gp.GLOBAL_TERMS
    # merged dicts never overwrite a key
    assert not set(cand) & set(glob) and not set(offer) & set(glob)


def test_every_terminal_has_a_power_of_two_divisor():
    terms = set(gp.CANDIDATE_TERMS) | set(gp.GLOBAL_TERMS) | set(gp.OFFER_TERMS) | set(gp.REMOVAL_TERMS)
    assert set(gp.SCALE) == terms
    for k, d in gp.SCALE.items():
        m, e = math.frexp(d)
        assert m == 0.5 and d >= 1, (k, d)  # exact power of two
    flags = {"is_attach", "is_direct", "is_separated", "house_served", "is_clean", "ends_near_shop",
             "rm_links_doorstep"} | {f"type_{t}" for t in range(5)}
    assert all(gp.SCALE[k] == 1 for k in flags)
    assert gp.SCALE["tiles_needed"] == 64 and gp.SCALE["road_stock"] == 64 and gp.SCALE["time"] == 4096


def test_primitive_sets_and_functions():
    assert [p.name for p in gp.PRIORITY_SET.primitives[gp.PRIORITY_SET.ret]] == list(gp.FUNCTION_NAMES)
    for pset, terms in ((gp.PRIORITY_SET, gp.PRIORITY_TERMS), (gp.HOLD_SET, gp.HOLD_TERMS),
                        (gp.UPGRADE_SET, gp.UPGRADE_TERMS)):
        assert tuple(pset.arguments) == terms
    assert gp.if_gt(2, 1, 10, 20) == 10 and gp.if_gt(1, 1, 10, 20) == 20
    assert gp.if_gt(float("nan"), 1, 10, 20) == 20
    assert gp.pdiv(3.0, 0.0) == 1.0 and gp.pdiv(3.0, 2.0) == 1.5
    assert gp.pdiv(1e308, 1e-10) == math.inf
    assert gp.neg(2.0) == -2.0 and gp.add(1, 2) == 3 and gp.sub(1, 2) == -1 and gp.mul(2, 3) == 6
    assert gp.min_(1, 2) == 1 and gp.max_(1, 2) == 2


def test_ephemeral_constants():
    random.seed(3)
    values = [gp.ephemeral_constant() for _ in range(2000)]
    assert all(isinstance(v, float) for v in values)
    fixed = [v for v in values if v in gp.CONST_CHOICES]
    assert set(fixed) == set(gp.CONST_CHOICES)
    assert all(-1.0 <= v <= 1.0 and round(v, 2) == v for v in values if v not in gp.CONST_CHOICES)
    assert all(math.copysign(1.0, v) == 1.0 for v in values if v == 0.0)  # never -0.0
    assert pickle.loads(pickle.dumps(gp.ephemeral_constant)) is gp.ephemeral_constant


# --- individuals and text ------------------------------------------------------------------------------------

def test_hand_and_separated_texts_round_trip():
    for text in (gp.HAND_TEXT, gp.SEPARATED_TEXT):
        ind = gp.individual_from_text(text)
        assert isinstance(ind, gp.creator.RulesIndividual) and len(ind) == 3
        assert all(isinstance(t, dgp.PrimitiveTree) for t in ind)
        assert gp.individual_text(ind) == text
    assert gp.HAND_TEXT == "priority: neg(tiles_needed)\nhold: sub(0.0625, road_stock)\nupgrade: offer_roads"
    assert gp.size(gp.individual_from_text(gp.HAND_TEXT)) == 2 + 3 + 1


def test_individual_fitness_weights():
    ind = gp.individual_from_text(gp.HAND_TEXT)
    assert ind.fitness.weights == (1.0, 1.0) and not ind.fitness.valid
    ind.fitness.values = (10.0, 300.0)
    other = gp.individual_from_text(gp.HAND_TEXT)
    other.fitness.values = (10.0, 200.0)
    assert ind.fitness > other.fitness


def test_constants_reloaded_from_text_are_ephemerals_and_parsing_does_not_draw():
    random.seed(5)
    before = random.getstate()
    ind = gp.individual_from_text(gp.SEPARATED_TEXT)
    assert random.getstate() == before
    consts = [n for t in ind for n in t if isinstance(type(n), dgp.MetaEphemeral)]
    assert sorted(n.value for n in consts) == [0.0625, 15.625]
    # integers in text become floats: one canonical text per tree
    t = gp.individual_text(gp.individual_from_text("priority: mul(2, tiles_needed)\nhold: 1\nupgrade: -1"))
    assert t == "priority: mul(2.0, tiles_needed)\nhold: 1.0\nupgrade: -1.0"


@pytest.mark.parametrize("text", [
    "priority: neg(tiles_needed)\nhold: road_stock",  # two trees
    "hold: road_stock\npriority: neg(tiles_needed)\nupgrade: offer_roads",  # wrong order
    "priority: neg(tiles_needed)\nhold: tiles_needed\nupgrade: offer_roads",  # candidate term in hold
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: random",  # not a terminal or a number
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: True",
    "priority: neg(tiles_needed, road_stock)\nhold: road_stock\nupgrade: offer_roads",  # wrong arity
    "priority: add(tiles_needed)\nhold: road_stock\nupgrade: offer_roads",  # incomplete
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: nan",
    # extra nodes after a complete expression (from_string keeps them; str() and compile drop them)
    "priority: neg(tiles_needed)\nhold: road_stock neg\nupgrade: offer_roads",
    "priority: neg(tiles_needed)\nhold: road_stock, neg\nupgrade: offer_roads",
    "priority: neg(tiles_needed)\nhold: neg(road_stock) neg\nupgrade: offer_roads",
    # parentheses and commas out of place (from_string ignores them)
    "priority: neg(tiles_needed)\nhold: (road_stock\nupgrade: offer_roads",
    "priority: neg(tiles_needed)\nhold: road_stock)\nupgrade: offer_roads",
    "priority: neg tiles_needed\nhold: road_stock\nupgrade: offer_roads",
    "priority: add(tiles_needed tiles_needed)\nhold: road_stock\nupgrade: offer_roads",
    # tokens from_string would eval(): no ZeroDivisionError or OverflowError, no hex
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: 1/0",
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: 10**400",
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: 2**9999",
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: 1e400",
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: 0x10",
    "priority: neg(tiles_needed)\nhold: road_stock\nupgrade: const_upgrade",  # the ephemeral class itself
])
def test_individual_from_text_rejects_bad_texts(text):
    with pytest.raises(ValueError):
        gp.individual_from_text(text)


def test_individual_from_text_accepts_spacing_variants_canonically():
    t = gp.individual_from_text("priority:add( tiles_needed ,-1 )\nhold: road_stock\nupgrade:  offer_roads ")
    assert gp.individual_text(t) == "priority: add(tiles_needed, -1.0)\nhold: road_stock\nupgrade: offer_roads"


def test_negative_zero_reloads_as_zero():
    t = gp.individual_text(gp.individual_from_text("priority: -0.0\nhold: -0.0\nupgrade: mul(-0, offer_roads)"))
    assert t == "priority: 0.0\nhold: 0.0\nupgrade: mul(0.0, offer_roads)"


def test_random_individuals_are_valid_and_round_trip():
    random.seed(11)
    for _ in range(50):
        ind = gp.random_individual()
        assert all(2 <= t.height <= 4 for t in ind)
        text = gp.individual_text(ind)
        assert gp.individual_text(gp.individual_from_text(text)) == text
        assert gp.size(ind) == sum(len(t) for t in ind)


def test_random_individuals_are_deterministic_given_the_rng():
    random.seed(7)
    a = [gp.individual_text(gp.random_individual()) for _ in range(5)]
    random.seed(7)
    b = [gp.individual_text(gp.random_individual()) for _ in range(5)]
    assert a == b


# --- variation -----------------------------------------------------------------------------------------------

def _pop(n, seed):
    random.seed(seed)
    return [gp.random_individual(2, 6) for _ in range(n)]


def test_mate_changes_at_most_one_tree_index_and_respects_the_depth_limit():
    pop = _pop(40, 1)
    random.seed(2)
    changed_any = False
    for a, b in zip(pop[::2], pop[1::2]):
        a0, b0 = [str(t) for t in a], [str(t) for t in b]
        ca, cb = gp.mate(a, b)
        assert ca is a and cb is b
        diff = {i for i in range(3) if str(a[i]) != a0[i]} | {i for i in range(3) if str(b[i]) != b0[i]}
        assert len(diff) <= 1
        changed_any |= bool(diff)
        assert all(t.height <= gp.MAX_DEPTH for t in (*a, *b))
        assert not a.fitness.valid and not b.fitness.valid
    assert changed_any


def test_mutate_changes_at_most_one_tree_and_respects_the_depth_limit():
    pop = _pop(60, 3)
    random.seed(4)
    changed = 0
    for ind in pop:
        before = [str(t) for t in ind]
        (out,) = gp.mutate(ind)
        assert out is ind
        diff = [i for i in range(3) if str(ind[i]) != before[i]]
        assert len(diff) <= 1
        changed += bool(diff)
        assert all(t.height <= gp.MAX_DEPTH for t in ind)
        assert not ind.fitness.valid
    assert changed >= 40


def test_depth_limit_restores_the_parent_tree():
    deep = "add(" * 7 + "road_stock" + ", road_stock)" * 7
    parent = gp.individual_from_text(gp.HAND_TEXT)
    child = gp.individual_from_text(gp.HAND_TEXT)
    child[1] = dgp.PrimitiveTree.from_string(deep, gp.HOLD_SET)
    assert child[1].height == 7
    gp.limit_depth(child, parent)
    assert gp.individual_text(child) == gp.HAND_TEXT


def test_mutate_ephemeral_on_seeded_constants():
    """Seeded constants reload as ephemerals, so mutEphemeral can tune them."""
    random.seed(0)
    seen = set()
    for _ in range(200):
        ind = gp.individual_from_text(gp.HAND_TEXT)
        gp.mutate(ind)
        seen.add(str(ind[1]))
    assert any(s.startswith("sub(") and s != "sub(0.0625, road_stock)" for s in seen)


ONE_NODE_TEXT = "priority: tiles_needed\nhold: road_stock\nupgrade: offer_roads"


def test_mutate_changes_one_node_trees():
    """mutNodeReplacement never touches the root, so a one-node tree falls back to uniform mutation."""
    unchanged = {gp.HAND_TEXT: 0, ONE_NODE_TEXT: 0}
    for text in unchanged:
        for s in range(200):
            random.seed(s)
            ind = gp.individual_from_text(text)
            gp.mutate(ind)
            unchanged[text] += gp.individual_text(ind) == text
    # before the fallback about 23% (hand) and 67% (one node) of the mutations were clones
    assert unchanged[gp.HAND_TEXT] <= 20 and unchanged[ONE_NODE_TEXT] <= 20, unchanged


def test_mate_draws_a_tree_index_where_crossover_applies():
    """cxOnePoint does nothing on a one-node tree, so such indices are never drawn."""
    unchanged = 0
    for s in range(200):
        random.seed(s)
        b = gp.random_individual()
        a = gp.individual_from_text(gp.HAND_TEXT)
        gp.mate(a, b)
        assert str(a[2]) == "offer_roads"  # the one-node upgrade tree is never drawn
        unchanged += gp.individual_text(a) == gp.HAND_TEXT
    assert unchanged <= 20  # before: about 35%
    a, b = gp.individual_from_text(ONE_NODE_TEXT), gp.individual_from_text(gp.HAND_TEXT)
    a.fitness.values = b.fitness.values = (1.0, 1.0)
    assert gp.mate(a, b) == (a, b)  # no index qualifies: unchanged, fitnesses still invalidated
    assert gp.individual_text(a) == ONE_NODE_TEXT and gp.individual_text(b) == gp.HAND_TEXT
    assert not a.fitness.valid and not b.fitness.valid


def test_variation_is_deterministic_given_the_rng():
    def run():
        pop = _pop(10, 9)
        random.seed(10)
        for a, b in zip(pop[::2], pop[1::2]):
            gp.mate(a, b)
        for ind in pop:
            gp.mutate(ind)
        return [gp.individual_text(i) for i in pop]
    assert run() == run()


def test_size_counts_all_nodes():
    ind = gp.individual_from_text(gp.SEPARATED_TEXT)
    assert gp.size(ind) == len(ind[0]) + len(ind[1]) + len(ind[2]) == 6 + 3 + 1


def test_individuals_pickle():
    ind = gp.individual_from_text(gp.SEPARATED_TEXT)
    ind.fitness.values = (1.0, 2.0)
    back = pickle.loads(pickle.dumps(ind))
    assert gp.individual_text(back) == gp.SEPARATED_TEXT and back.fitness.values == (1.0, 2.0)
    clone = copy.deepcopy(ind)
    assert gp.individual_text(clone) == gp.SEPARATED_TEXT


# --- TreePolicy ----------------------------------------------------------------------------------------------

def _merged(state, cand=None):
    g = global_features(state)
    c = {**candidate_features(state, cand or _cand()), **g}
    o = {**offer_features(state.offers[0], state), **g}
    return c, g, o


def test_tree_policy_attributes():
    p = gp.TreePolicy(gp.HAND_TEXT)
    assert p.coverage is True and p.wants_globals is True and p.name == "tree" and p.text == gp.HAND_TEXT
    assert p.remove({}) == -1.0
    assert gp.TreePolicy(gp.HAND_TEXT, coverage=False).coverage is False
    trees = gp.HAND_TEXT.splitlines()
    assert gp.TreePolicy([t.split(": ", 1)[1] for t in trees]).text == gp.HAND_TEXT


def test_tree_policy_hand_values_are_the_hand_rule_scaled_by_64():
    state = _state()
    c, g, o = _merged(state)
    p, h = gp.TreePolicy(gp.HAND_TEXT), HandRule()
    assert p.priority(c) == h.priority(c) / 64
    assert p.hold(g) == h.hold(g) / 64
    assert p.upgrade(o) == h.upgrade(o) / 64
    s, hs = gp.TreePolicy(gp.SEPARATED_TEXT), SeparatedPreference()
    sep = RouteCandidate(kind="separated", house_id=1, shop_ids=(2,), path=_cand().path, tiles_needed=3,
                         bridges_needed=0, turns=0, new_junctions=0, shared_cells=0, strokes=())
    cs, _, _ = _merged(state, sep)
    assert s.priority(cs) == hs.priority(cs) / 64 and s.priority(c) == hs.priority(c) / 64


def test_tree_policy_reads_scaled_terminals():
    state = _state()
    c, g, o = _merged(state)
    p = gp.TreePolicy("priority: add(time, path_cost_s)\nhold: next_offer_s\nupgrade: add(stock_of_type, type_1)")
    assert p.priority(c) == c["time"] / 4096 + c["path_cost_s"] / 1024
    assert p.hold(g) == g["next_offer_s"] / 1024
    assert p.upgrade(o) == o["stock_of_type"] / 64 + 1.0


def test_tree_policy_non_finite_scores():
    state = _state()
    c, g, o = _merged(state)
    p = gp.TreePolicy("priority: pdiv(1e308, 1e-300)\nhold: sub(mul(1e308, 1e308), mul(1e308, 1e308))\n"
                      "upgrade: sub(mul(1e308, 1e308), mul(1e308, 1e308))")
    assert p.priority(c) == -math.inf and p.upgrade(o) == -math.inf
    assert math.isnan(p.hold(g))  # agent.decide never acts on a non-finite hold


def test_tree_policy_needs_the_merged_globals():
    p = gp.TreePolicy("priority: road_stock\nhold: road_stock\nupgrade: road_stock")
    state = _state()
    with pytest.raises(KeyError):
        p.priority(candidate_features(state, _cand()))


def test_compiled_trees_are_cached_per_process():
    gp.TreePolicy(gp.HAND_TEXT)
    hits = gp._compile.cache_info().hits
    gp.TreePolicy(gp.HAND_TEXT)
    assert gp._compile.cache_info().hits == hits + 3


def test_decide_passes_globals_to_tree_policies(monkeypatch):
    """wants_globals: candidate and offer dicts carry the global terms; Phase 1 policies get the old dicts."""
    state = _state()
    seen = []

    class Probe(HandRule):
        wants_globals = True

        def priority(self, f):
            seen.append(("p", set(f)))
            return super().priority(f)

        def upgrade(self, f):
            seen.append(("u", set(f)))
            return super().upgrade(f)

    class Session:
        done = False
        memory = None

        def __init__(self):
            self.state = state

    monkeypatch.setattr(agent, "take_offer", lambda s, i: setattr(s, "state", s.state))
    monkeypatch.setattr(agent, "unserved_targets", lambda st: [(st.buildings[0], (st.buildings[1],))])
    monkeypatch.setattr(agent, "route_candidates", lambda st, h, s: [_cand()])
    monkeypatch.setattr(agent, "execute_route", lambda s, c: (setattr(s, "done", True), True)[1])
    decide(Session(), Probe())
    kinds = {k for k, _ in seen}
    assert kinds == {"p", "u"}
    for _, keys in seen:
        assert set(gp.GLOBAL_TERMS) <= keys
    seen.clear()

    class Plain(Probe):
        wants_globals = False

    decide(Session(), Plain())
    assert seen and all(not (set(gp.GLOBAL_TERMS) & keys) for _, keys in seen)


# --- real games: the trees play exactly the Phase 1 rules ----------------------------------------------------

TREE_GAMES = [g for g in PHASE1_GAMES if g[0] in ("hand", "separated")]
FAST_TREE_GAMES = {("hand", 1000), ("hand", 2000), ("separated", 1000), ("separated", 2000)}


@pytest.mark.host
@pytest.mark.parametrize("name, seed, trips, commands, sha",
                         [g for g in TREE_GAMES if SLOW or (g[0], g[1]) in FAST_TREE_GAMES])
def test_tree_texts_play_the_phase1_rules_byte_identically(host, name, seed, trips, commands, sha):
    """Set EVOLVED_RULES_SLOW=1 to include seed 2004 (the longest games)."""
    text = gp.HAND_TEXT if name == "hand" else gp.SEPARATED_TEXT
    r = play_game(host, seed, gp.TreePolicy(text, coverage=False))
    digest = hashlib.sha256(json.dumps(r.recording["actions"], sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    assert (r.trips, r.commands, digest) == (trips, commands, sha)


@pytest.mark.host
def test_coverage_tree_policy_plays_a_game(host):
    r = play_game(host, 2000, gp.TreePolicy(gp.HAND_TEXT), cap_s=300.0, record=False)
    assert r.commands > 0 and r.trips > 0
