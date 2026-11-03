"""gp-3 traffic moves (EXPERIMENTS.md): clean routes, traffic inputs, removal candidates and the removal step.

Older rules must play exactly as before: Phase 1 rules (test_features' fingerprints), and gp-2's best rule, whose
validation games are pinned below.
"""
from __future__ import annotations

import pytest

from evolved_rules import agent
from evolved_rules.agent import decide, play_game
from evolved_rules.candidates import (
    DOORSTEP_RADIUS, RemovalCandidate, _becomes_junction, _junction_link, doorsteps, keeps_connections,
    removal_candidates, route_candidates,
)
from evolved_rules.features import GameMemory, candidate_features, global_features, removal_features
from evolved_rules.gp import TreePolicy
from evolved_rules.rules import CleanHand, CleanRemoveHand, SeparatedPreference
from evolved_rules.state import parse_observation
from evolved_rules.tests.helpers import house, make_obs
from evolved_rules.tests.test_features import _links, _merge, _row, _shop

E, SE, S, SW, W_, NW, N, NE = range(8)

# Red shop 5 at (30, 10) (2x2), entrance (30, 11) facing west: doorstep (29, 11). Red house 1 at (19, 11) drives
# east along row 11 to the doorstep. A small loop (28,11)-(28,10)-(29,10)-(29,11) and a stub (29,12) also meet the
# doorstep, which so carries 4 links: west, the entrance, north and south.
ROADS = _merge(_links(*_row(19, 30, 11)), _links((28, 11), (28, 10), (29, 10), (29, 11)), _links((29, 12), (29, 11)))


def _state(vehicles=(), extra=()):
    return parse_observation(make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 19, 11, E), *extra], roads=ROADS,
                                      vehicles=vehicles))


def _car(stage, x, y, speed, shop_id=5, color=0):
    return {"color": color, "stage": stage, "waiting": 0, "homeId": 1, "shopId": shop_id, "x": x, "y": y,
            "speed": speed}


# --- junction links ------------------------------------------------------------------------------------------

def test_junction_link_also_counts_links_added_to_an_existing_junction():
    s = _state()
    assert s.road_cell((29, 11))
    # the doorstep already has 4 links: _becomes_junction ignores it, _junction_link counts a new one
    assert not _becomes_junction(s, (29, 11), ((28, 12),))
    assert _junction_link(s, (29, 11), ((28, 12),))
    # an existing link adds nothing
    assert not _junction_link(s, (29, 11), ((28, 11),))
    assert doorsteps(s) == ((29, 11),)


# --- traffic inputs ------------------------------------------------------------------------------------------

def test_traffic_counts_doorstep_links_junctions_heading_and_stuck_cars():
    cars = [_car("Outbound", 28.5, 11.0, 0.01),  # stuck near the shop, heading there
            _car("Outbound", 22.0, 11.0, 0.5),  # heading there, moving, far
            _car("Parking", 30.5, 11.2, 0.0),  # parked: neither heading nor stuck
            _car("Returning", 27.0, 11.0, 0.0, shop_id=-1)]  # stuck near the shop, not heading
    s = _state(vehicles=cars)
    g = global_features(s, GameMemory())
    a = GameMemory().analysis(s)
    door, junctions, heading, stuck = a.traffic()[5]
    assert door == 4
    assert junctions == 2  # (29, 11) with 4 links and (28, 11) with 3, both within 3 tiles of the doorstep
    assert (heading, stuck) == (2, 2)
    assert (g["worst_doorstep_degree"], g["most_stuck_near_shop"], g["stuck_cars"]) == (4.0, 2.0, 2.0)


# --- clean routes --------------------------------------------------------------------------------------------

def _near_house_state():
    # a second red house close to the shop: the cheapest attach ends at the loop, next to the doorstep
    return _state(extra=[house(2, 0, 31, 7, S)])


def test_clean_off_is_exactly_the_phase1_candidate_list():
    s = _near_house_state()
    h2 = next(b for b in s.houses() if b.id == 2)
    shop5 = next(b for b in s.shops() if b.id == 5)
    plain = route_candidates(s, h2, (shop5,))
    assert route_candidates(s, h2, (shop5,), clean=False) == plain
    with_clean = route_candidates(s, h2, (shop5,), clean=True)
    assert with_clean[:len(plain)] == plain


def test_a_clean_route_ends_outside_every_doorstep_zone():
    s = _near_house_state()
    h2 = next(b for b in s.houses() if b.id == 2)
    shop5 = next(b for b in s.shops() if b.id == 5)
    plain = route_candidates(s, h2, (shop5,))
    assert any(c.ends_near_shop for c in plain)  # the cheap routes end by the doorstep
    cands = route_candidates(s, h2, (shop5,), clean=True)
    clean = [c for c in cands if c.kind == "clean"]
    assert len(clean) == 1
    end = clean[0].path[-1]
    assert max(abs(end[0] - 29), abs(end[1] - 11)) > DOORSTEP_RADIUS and not clean[0].ends_near_shop
    assert clean[0].near_shop_junctions <= min(c.near_shop_junctions for c in plain)
    f = candidate_features(s, clean[0], GameMemory())
    assert f["is_clean"] == 1.0 and f["ends_near_shop"] == 0.0 and f["shop_doorstep_degree"] == 4.0


# --- removal candidates --------------------------------------------------------------------------------------

def test_removal_candidates_are_doorstep_feeders_that_keep_every_connection():
    s = _state()
    cells = [rc.cell for rc in removal_candidates(s)]
    # (29, 10) and the stub (29, 12) feed the 4-link doorstep and the row keeps house 1 connected without them
    assert cells == [(29, 10), (29, 12)]
    # (28, 11) is a junction near the doorstep, but the house's only way to the shop runs through it
    assert not keeps_connections(s, (28, 11))
    rc = removal_candidates(s)[0]
    assert (rc.shop_id, rc.dist, rc.degree, rc.links_doorstep, rc.doorstep_degree) == (5, 1, 2, True, 4)
    f = removal_features(s, rc, GameMemory())
    assert f["rm_links_doorstep"] == 1.0 and f["rm_doorstep_degree"] == 4.0 and f["rm_shop_junctions"] == 2.0


def test_no_removal_candidates_without_shops():
    s = parse_observation(make_obs(buildings=[house(1, 0, 19, 11, E)], roads=_links(*_row(19, 25, 11))))
    assert removal_candidates(s) == []


# --- the removal step in decide() ----------------------------------------------------------------------------

class _Session:
    """Just enough of GameSession for decide(): commands are recorded, the state never changes."""

    def __init__(self, state):
        self.state, self.memory, self.done, self.sent = state, GameMemory(), False, []

    def command(self, request):
        self.sent.append(request)
        return True, self.state


def test_a_removing_policy_removes_its_best_candidate():
    sess = _Session(_state(vehicles=[_car("Outbound", 28.5, 11.0, 0.0), _car("Outbound", 29.0, 12.4, 0.0)]))
    decide(sess, CleanRemoveHand())  # nothing to route (house 1 is served); 2 cars stuck by a 4-link doorstep
    assert sess.sent == [{"command": "build", "tool": "Remove", "x": 29, "y": 10}]


def test_removal_waits_for_stuck_cars_and_other_policies_never_look(monkeypatch):
    sess = _Session(_state())
    decide(sess, CleanRemoveHand())  # no stuck cars: the hand rule's remove score stays -1
    assert sess.sent == []
    monkeypatch.setattr(agent, "removal_candidates", lambda state: (_ for _ in ()).throw(AssertionError("looked")))
    for policy in (CleanHand(), SeparatedPreference(), TreePolicy(GP2_BEST)):
        decide(_Session(_state()), policy)  # none has `removes`: removal_candidates is never called


# --- older rules play exactly as before ------------------------------------------------------------------------

# gp-2's best rule at generation 14 (245.1 trips on 1500-1549) and its two shortest validation games, as gp-2
# recorded them at b8e82a0.
GP2_BEST = (
    "priority: neg(sub(add(sub(add(sub(worst_margin, shops), mul(path_cost_s, disconnected_components)), "
    "neg(neg(shop_demand))), sub(path_cost_s, bridge_stock)), neg(neg(shop_demand))))\n"
    "hold: sub(mul(if_gt(neg(unserved_houses), min(houses, unserved_shops), max(shops, next_offer_s), "
    "mul(worst_margin, bridge_stock)), sub(if_gt(bridge_stock, houses, edge_distance, 0.72), "
    "min(bridge_stock, 0.49))), neg(sub(mul(worst_overcrowded, houses), if_gt(houses, -0.82, "
    "disconnected_components, shops))))\n"
    "upgrade: sub(sub(edge_distance, time), add(pdiv(next_offer_s, type_4), disconnected_components))")
GP2_GAMES = {1540: (33, 359.55), 1511: (100, 514.65)}


@pytest.mark.host
@pytest.mark.parametrize("seed", sorted(GP2_GAMES))
def test_gp2_best_still_plays_its_validation_games(host, seed):
    r = play_game(host, seed, TreePolicy(GP2_BEST), record=False)
    assert (r.trips, round(r.seconds, 2)) == GP2_GAMES[seed]


# --- 4-tree individuals and the gp-3 evolution options ------------------------------------------------------

import pickle  # noqa: E402
import random  # noqa: E402

from evolved_rules import evolve as evo  # noqa: E402
from evolved_rules import gp  # noqa: E402
from evolved_rules.evolve import Config, read_checkpoint, read_jsonl  # noqa: E402
from evolved_rules.tests.test_evolve import SMALL, fake, run  # noqa: E402,F401 (fixture)


def test_with_remove_turns_a_3_tree_text_into_a_never_removing_4_tree_text():
    t4 = gp.with_remove(gp.HAND_TEXT)
    assert t4.splitlines()[-1] == "remove: -1.0" and len(t4.splitlines()) == 4
    assert gp.with_remove(t4) == t4
    p = TreePolicy(t4)
    # a constant remove tree <= 0 can never remove, so the removal step is skipped (removes False)
    assert (p.trees, p.removes, p.clean_routes) == (4, False, True)
    assert p.remove({k: 1.0 for k in gp.REMOVE_TERMS}) == -1.0
    assert TreePolicy(t4, clean_routes=False).clean_routes is False
    with pytest.raises(ValueError):
        gp.individual_from_text(t4 + "\nremove: -1.0")  # five lines


def test_a_remove_tree_scores_scaled_removal_inputs():
    p = TreePolicy(gp.HAND_TEXT + "\nremove: sub(rm_doorstep_degree, 0.25)")
    f = {k: 0.0 for k in gp.REMOVE_TERMS}
    f["rm_doorstep_degree"] = 4.0
    assert p.remove(f) == pytest.approx(4.0 / 8 - 0.25)
    assert TreePolicy(gp.HAND_TEXT + "\nremove: pdiv(1.0, rm_dist)").remove({**f, "rm_dist": 0.0}) == 1.0  # pdiv


def test_the_clean_text_is_clean_hand_scaled_by_1_64():
    p = TreePolicy(gp.with_remove(gp.CLEAN_TEXT))
    for tiles, sep, clean in ((3, 0, 1), (5, 1, 0), (7, 0, 0)):
        f = {**{k: 0.0 for k in gp.PRIORITY_TERMS}, "tiles_needed": float(tiles), "is_separated": float(sep),
             "is_clean": float(clean)}
        assert p.priority(f) == CleanHand().priority(f) / 64


def test_4_tree_variation_reaches_the_remove_tree():
    random.seed(2)
    touched = 0
    for _ in range(60):
        ind = gp.random_individual(trees=4)
        before = str(ind[3])
        gp.mutate(ind)
        touched += str(ind[3]) != before
        assert len(ind) == 4 and all(t.height <= gp.MAX_DEPTH for t in ind)
    assert touched > 0
    a, b = gp.random_individual(trees=4), gp.random_individual(trees=4)
    gp.mate(a, b)
    assert len(a) == len(b) == 4


def test_gp3_initial_population_holds_the_seeds_as_4_tree_texts():
    cfg = Config(**{**SMALL, "remove_tree": True, "seed_texts": (GP2_BEST,)})
    cfg.check()
    random.seed(cfg.seed)
    pop = evo.initial_population(cfg)
    assert pop[:4] == [gp.with_remove(t) for t in (gp.HAND_TEXT, gp.SEPARATED_TEXT, gp.CLEAN_TEXT, GP2_BEST)]
    assert len(pop) == cfg.pop and len(set(pop)) == cfg.pop
    assert all(len(gp.individual_from_text(t)) == 4 for t in pop)
    # without remove_tree a seed text is added as it is (3 trees)
    cfg3 = Config(**{**SMALL, "seed_texts": (GP2_BEST,)})
    random.seed(cfg3.seed)
    assert evo.initial_population(cfg3)[2] == gp.individual_text(gp.individual_from_text(GP2_BEST))


def test_seed_texts_are_checked():
    with pytest.raises(ValueError, match="bad seed text"):
        Config(**{**SMALL, "seed_texts": ("priority: nonsense",)}).check()
    with pytest.raises(ValueError, match="needs remove_tree"):
        Config(**{**SMALL, "seed_texts": (gp.with_remove(gp.HAND_TEXT),)}).check()
    cfg = Config(**{**SMALL, "remove_tree": True, "seed_texts": (GP2_BEST,)})
    assert Config.from_json(cfg.to_json()) == cfg


def test_a_gp3_run_keeps_4_tree_individuals_including_immigrants(fake, tmp_path):  # noqa: F811
    cfg = Config(**{**SMALL, "pop": 10, "remove_tree": True, "dedup": True, "immigrants": 3, "validate_top": 2,
                    "max_gens": 2, "min_gens": 5})
    fake["game"] = lambda text, seed, cap_s: {"trips": 50 + len(text) % 3, "seconds": 300.0, "commands": 5,
                                              "tiles_built": 4}  # 3 behaviours: duplicates and immigrants
    run(tmp_path, "g3", cfg)
    gens = read_jsonl(tmp_path / "g3" / evo.GENERATIONS)
    assert len(gens) == 2 and all(r["immigrants"] > 0 for r in gens)
    pop = read_checkpoint(tmp_path / "g3")["population"]
    assert all(len(gp.individual_from_text(t)) == 4 for t in pop)
    assert all(len(t.splitlines()) == 4 for t, _ in fake["plays"])


def test_a_format_2_checkpoint_is_refused_with_the_gp2_commit(tmp_path):
    (tmp_path / evo.CHECKPOINT).write_bytes(pickle.dumps({"format": 2}))
    with pytest.raises(ValueError, match="b8e82a0"):
        read_checkpoint(tmp_path)


def test_cli_gp3_options(fake, tmp_path, monkeypatch):  # noqa: F811
    from evolved_rules.engine import Engine
    seed_file = tmp_path / "seed.txt"
    seed_file.write_text(GP2_BEST + "\n", encoding="utf-8")
    monkeypatch.setattr(evo, "EVOLVE_DIR", tmp_path)
    monkeypatch.setattr(evo, "_make_engine", lambda cfg, run_dir: Engine(workers=2, cache_path=run_dir / evo.CACHE))
    assert evo.main(["--run", "c3", "--pop", "8", "--first-seeds", "2", "--more-seeds", "2", "--racing-top", "4",
                     "--validate-top", "2", "--remove-tree", "--seed-text", str(seed_file),
                     "--validation", "1500-1502", "--max-gens", "1", "--workers", "2"]) == 0
    import json
    p = json.loads((tmp_path / "c3" / evo.CONFIG).read_text())["params"]
    assert p["remove_tree"] is True and p["seed_texts"] == [GP2_BEST]


# --- review fixes (2026-11-03) -----------------------------------------------------------------------------------

def test_stuck_cars_count_by_their_cell_so_the_zone_is_symmetric():
    # cars report cell centres (x + 0.5): a car 3 cells east or south of the doorstep (29, 11) is near, 4 is not
    cars = [_car("Outbound", 32.5, 11.5, 0.0), _car("Outbound", 29.5, 14.5, 0.0),  # 3 east, 3 south: near
            _car("Outbound", 33.5, 11.5, 0.0), _car("Outbound", 25.5, 11.5, 0.0)]  # 4 east, 4 west: not
    assert GameMemory().analysis(_state(vehicles=cars)).traffic()[5][3] == 2


def test_tiles_pending_removal_no_longer_count_as_links():
    obs = make_obs(buildings=[_shop(5, 0, 30, 10), house(1, 0, 19, 11, E)], roads=ROADS, pending=[(29, 10)])
    s = parse_observation(obs)
    a = GameMemory().analysis(s)
    assert a.traffic()[5][0] == 3  # the doorstep's link north leads to a pending tile
    rcs = removal_candidates(s)
    assert [rc.cell for rc in rcs] == [(29, 12)] and rcs[0].doorstep_degree == 3


def test_a_constant_non_positive_remove_tree_skips_the_removal_step():
    assert TreePolicy(gp.with_remove(gp.HAND_TEXT)).removes is False  # remove: -1.0
    assert TreePolicy(gp.HAND_TEXT + "\nremove: 0.0").removes is False
    assert TreePolicy(gp.HAND_TEXT + "\nremove: 0.25").removes is True
    assert TreePolicy(gp.HAND_TEXT + "\nremove: rm_degree").removes is True


def test_pending_refunds_is_an_input_again_and_type_5_is_still_dropped():
    assert "pending_refunds" in gp.GLOBAL_TERMS and "type_5" not in gp.OFFER_TERMS
    t = gp.individual_text(gp.individual_from_text(gp.HAND_TEXT.replace("offer_roads", "add(offer_roads, type_5)")))
    assert t.splitlines()[2] == "upgrade: add(offer_roads, 0.0)"


@pytest.mark.host
def test_a_game_with_an_accepted_removal_passes_the_replay_verifier(host, tmp_path):
    import json

    from evolved_rules.rules import SeparatedRemoveHand
    from evolved_rules.verify import verify_recording
    r = play_game(host, 1515, SeparatedRemoveHand(), cap_s=900.0, record=True)
    removes = [a for a in r.recording["actions"] if a["command"] == "build" and a["tool"] == "Remove"]
    assert removes and any(a["accepted"] for a in removes)
    path = tmp_path / "1515.json"
    path.write_text(json.dumps(r.recording), encoding="utf-8")
    ok, out = verify_recording(path)
    assert ok, out


@pytest.mark.host
@pytest.mark.skipif(not __import__("os").environ.get("EVOLVED_RULES_SLOW"), reason="long game: EVOLVED_RULES_SLOW=1")
def test_gp2_best_still_plays_a_long_validation_game(host):
    r = play_game(host, 1503, TreePolicy(GP2_BEST), record=False)
    assert (r.trips, round(r.seconds, 1)) == (407, 994.9)
