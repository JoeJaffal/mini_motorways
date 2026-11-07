"""gp-4 step 2: the place tree (task 2). A 5-tree text places lights and roundabouts; older texts play as before."""
from __future__ import annotations

import math
import random
from pathlib import Path

import pytest
from deap import gp as deap_gp

from evolved_rules import gp
from evolved_rules.gp import HAND_TEXT, SEPARATED_TEXT, TreePolicy

GP3_FINAL_PATH = Path(__file__).resolve().parent.parent / "final" / "gp3_final.txt"
# the canonical text of final/gp3_final.txt before the place tree existed
GP3_FINAL_CANON = (
    "priority: add(sub(neg(shop_demand), add(sub(path_cost_s, shop_demand), sub(path_cost_s, bridge_stock))), "
    "mul(15.625, is_separated))\n"
    "hold: sub(worst_margin, shops)\n"
    "upgrade: sub(sub(unserved_shops, amount), neg(unserved_houses))\n"
    "remove: -1.0"
)
HAND_CANON = "priority: neg(tiles_needed)\nhold: sub(0.0625, road_stock)\nupgrade: offer_roads"
SEPARATED_CANON = ("priority: add(neg(tiles_needed), mul(15.625, is_separated))\n"
                   "hold: sub(0.0625, road_stock)\nupgrade: offer_roads")


def _five(place: str) -> str:
    return gp.with_place(GP3_FINAL_CANON, place)


def _place_dict(**values: float) -> dict[str, float]:
    f = {k: 0.0 for k in gp.PLACE_TERMS}
    f.update(values)
    return f


# --- older texts are unchanged -------------------------------------------------------------------------------

def test_old_texts_are_unchanged():
    gp3_final = GP3_FINAL_PATH.read_text()
    # (text, canonical text, removes, clean_routes) as before the place tree
    cases = [(HAND_TEXT, HAND_CANON, False, False), (SEPARATED_TEXT, SEPARATED_CANON, False, False),
             (gp3_final, GP3_FINAL_CANON, False, True)]
    for text, canon, removes, clean in cases:
        assert gp.individual_text(gp.individual_from_text(text)) == canon
        p = TreePolicy(text)
        assert p.text == canon
        assert p.places_lights is False and p.places_roundabouts is False
        assert p.place({}) == -1.0
        assert (p.removes, p.clean_routes) == (removes, clean)


def test_with_place_round_trip():
    five = gp.with_place(GP3_FINAL_CANON)
    lines = five.splitlines()
    assert len(lines) == 5 and lines[-1] == "place: -1.0"
    assert "\n".join(lines[:4]) == GP3_FINAL_CANON
    assert gp.with_place(five) == five
    hand5 = gp.with_place(HAND_TEXT)
    assert hand5.splitlines()[3:] == ["remove: -1.0", "place: -1.0"]
    assert hand5.splitlines()[:3] == HAND_CANON.splitlines()
    # a given place tree is written in canonical form; a 5-tree text is returned canonical
    assert gp.with_place(HAND_TEXT, "pl_stopped_near").splitlines()[4] == "place: pl_stopped_near"
    messy = five.replace("place: -1.0", "  place:   neg( pl_degree )  ")
    assert gp.with_place(messy).splitlines()[4] == "place: neg(pl_degree)"


# --- flags, scores -------------------------------------------------------------------------------------------

def test_place_flags():
    never = TreePolicy(_five("-1.0"))
    assert never.trees == 5
    assert never.places_lights is False and never.places_roundabouts is False
    always = TreePolicy(_five("pl_stopped_near"))
    assert always.places_lights is True and always.places_roundabouts is True
    zero = TreePolicy(_five("0.0"))
    assert zero.places_lights is False and zero.places_roundabouts is False
    assert TreePolicy(_five("0.25")).places_lights is True


def test_five_tree_texts_remove_and_clean_like_four_tree_texts():
    p = TreePolicy(_five("pl_stopped_near"))
    assert p.removes is False and p.clean_routes is True  # remove: -1.0
    removing = TreePolicy(gp.with_place(gp.with_remove(HAND_TEXT, "rm_shop_stuck"), "pl_degree"))
    assert removing.trees == 5 and removing.removes is True and removing.clean_routes is True
    assert removing.remove(dict.fromkeys(gp.REMOVE_TERMS, 128.0)) == 2.0  # rm_shop_stuck: COUNT 64
    assert TreePolicy(_five("-1.0"), clean_routes=False).clean_routes is False


def test_place_scores_are_scaled():
    p = TreePolicy(_five("pl_stopped_near"))
    assert p.place(_place_dict(pl_stopped_near=3.0)) == 3 / 64
    q = TreePolicy(_five("add(pl_dist_worst_shop, pl_degree)"))
    assert q.place(_place_dict(pl_dist_worst_shop=64.0, pl_degree=4.0)) == 1.0 + 0.5


def test_place_non_finite_is_minus_inf():
    p = TreePolicy(_five("mul(pl_max_wait_near, 1e308)"))
    assert p.place(_place_dict(pl_max_wait_near=1e10)) == -math.inf
    nan = TreePolicy(_five("sub(mul(pl_max_wait_near, 1e308), mul(pl_max_wait_near, 1e308))"))
    assert nan.place(_place_dict(pl_max_wait_near=1e10)) == -math.inf


def test_place_terminals_and_scales():
    assert gp.PLACEMENT_TERMS == (
        "pl_is_light", "pl_is_roundabout", "pl_degree", "pl_doorstep", "pl_cars_near", "pl_stopped_near",
        "pl_max_wait_near", "pl_mean_wait_near", "pl_dist_worst_shop", "pl_worst_colour_stuck", "pl_new_links",
        "pl_joins_separated", "pl_tiles_lost", "pl_light_stock", "pl_round_stock")
    assert gp.PLACE_TERMS == gp.PLACEMENT_TERMS + gp.GLOBAL_TERMS
    assert gp.ALL_TREE_NAMES == ("priority", "hold", "upgrade", "remove", "place")
    assert gp.ALL_TREE_TERMS[4] == gp.PLACE_TERMS and gp.ALL_PSETS[4] is gp.PLACE_SET
    assert gp.TREE_COUNTS == (3, 4, 5)
    assert gp.NEVER_PLACE == "-1.0"
    expected = {"pl_is_light": gp.FLAG, "pl_is_roundabout": gp.FLAG, "pl_doorstep": gp.FLAG,
                "pl_joins_separated": gp.FLAG, "pl_degree": gp.DEGREE, "pl_new_links": gp.DEGREE,
                "pl_tiles_lost": gp.DEGREE, "pl_cars_near": gp.COUNT, "pl_stopped_near": gp.COUNT,
                "pl_worst_colour_stuck": gp.COUNT, "pl_light_stock": gp.COUNT, "pl_round_stock": gp.COUNT,
                "pl_max_wait_near": gp.SHORT_S, "pl_mean_wait_near": gp.SHORT_S, "pl_dist_worst_shop": gp.TILES}
    assert set(expected) == set(gp.PLACEMENT_TERMS)
    assert {k: gp.SCALE[k] for k in expected} == expected
    assert (gp.FLAG, gp.DEGREE, gp.COUNT, gp.SHORT_S, gp.TILES) == (1, 8, 64, 1024, 64)


# --- parsing -------------------------------------------------------------------------------------------------

def test_bad_place_name_rejected():
    with pytest.raises(ValueError):
        gp.individual_from_text(_five("-1.0").replace("place: -1.0", "place: tiles_needed"))
    with pytest.raises(ValueError):
        TreePolicy(["neg(tiles_needed)", "road_stock", "offer_roads", "-1.0", "rm_degree"])
    # and a placement name is bad in every other tree
    with pytest.raises(ValueError):
        gp.individual_from_text(HAND_TEXT.replace("offer_roads", "pl_degree"))


def test_text_and_expression_forms_take_three_four_or_five_trees():
    five = _five("pl_degree")
    exprs = [ln.split(": ", 1)[1] for ln in five.splitlines()]
    assert TreePolicy(exprs).text == five
    assert TreePolicy(exprs[:4]).trees == 4 and TreePolicy(exprs[:3]).trees == 3
    for bad in (exprs[:2], [*exprs, "-1.0"]):
        with pytest.raises(ValueError, match="3, 4 or 5"):
            TreePolicy(bad)
    with pytest.raises(ValueError, match="3, 4 or 5"):
        gp.individual_from_text("\n".join(five.splitlines()[:2]))
    with pytest.raises(ValueError, match="3, 4 or 5"):
        gp.individual_from_text(five + "\nplace: -1.0")
    with pytest.raises(ValueError, match="3, 4 or 5"):
        gp.random_individual(trees=6)
    with pytest.raises(ValueError, match="3, 4 or 5"):
        gp.individual_text(gp.random_individual(trees=5)[:2])


# --- variation -----------------------------------------------------------------------------------------------

def _check_terminals(ind) -> None:
    assert len(ind) == 5
    for i, tree in enumerate(ind):
        assert tree.height <= gp.MAX_DEPTH
        terms = set(gp.ALL_TREE_TERMS[i])
        for node in tree:
            if isinstance(node, deap_gp.Primitive) or isinstance(type(node), deap_gp.MetaEphemeral):
                continue
            assert node.value in terms, (gp.ALL_TREE_NAMES[i], node.value)


def test_random_individual_has_five_trees_over_their_terminal_sets():
    random.seed(0)
    for _ in range(100):
        ind = gp.random_individual(trees=5)
        _check_terminals(ind)
        assert gp.individual_text(gp.individual_from_text(gp.individual_text(ind))) == gp.individual_text(ind)
    assert len(gp.random_individual()) == 3 and len(gp.random_individual(trees=4)) == 4


def test_mutation_keeps_terminal_sets():
    random.seed(0)
    ind = gp.random_individual(trees=5)
    for _ in range(2000):
        gp.mutate(ind)
        _check_terminals(ind)
    a, b = gp.random_individual(trees=5), gp.random_individual(trees=5)
    for _ in range(500):
        gp.mate(a, b)
        _check_terminals(a)
        _check_terminals(b)
        assert len(a) == len(b) == 5


# --- task 3: the seed texts (the step-1 hand rules written as trees) -------------------------------------------

SEED_DIR = Path(__file__).resolve().parent.parent / "seeds" / "gp4"
GP2_NOCLEAN_PATH = Path(__file__).resolve().parents[2] / "output" / "evolved_rules" / "gp2-best-noclean.txt"
# seed name -> (lights, roundabouts) of the hand rule it is written from
SEEDS = {"light": (True, False), "lightround": (True, True), "gplight": (True, False), "gplightround": (True, True)}
GP_SEEDS = ("gplight", "gplightround")


def _seed(name: str) -> str:
    return (SEED_DIR / f"{name}.txt").read_text(encoding="utf-8")


def _first(scores: list[float]) -> int:
    """The index of the largest score, ties going to the first (max keeps the first of equal keys)."""
    return max(range(len(scores)), key=scores.__getitem__)


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def test_seed_files_are_canonical_five_tree_texts():
    for name in ("gp2", *SEEDS):
        text = _seed(name).strip()
        assert len(text.splitlines()) == 5, name
        assert gp.individual_text(gp.individual_from_text(text)) == text, name
        assert TreePolicy(text).text == text and TreePolicy(text).trees == 5, name
    # gp2 never places; the others have a place tree (so both flags are on: the flags do not tell lights from
    # roundabouts, the place tree does, by scoring the other kind -1)
    gp2 = TreePolicy(_seed("gp2"))
    assert (gp2.places_lights, gp2.places_roundabouts) == (False, False) and gp2.place(_place_dict()) == -1.0
    for name in SEEDS:
        p = TreePolicy(_seed(name))
        assert (p.places_lights, p.places_roundabouts) == (True, True), name
    # light / lightround have SEPARATED_TEXT's priority and hold, gplight / gplightround gp3_final's
    separated = gp.individual_text(gp.individual_from_text(SEPARATED_TEXT)).splitlines()
    gp3_final = GP3_FINAL_CANON.splitlines()
    for name in SEEDS:
        lines = _seed(name).strip().splitlines()
        want = gp3_final if name in GP_SEEDS else separated
        assert lines[:2] == want[:2], name
        assert lines[3] == "remove: -1.0", name


@pytest.mark.skipif(not GP2_NOCLEAN_PATH.exists(), reason="output/evolved_rules/gp2-best-noclean.txt is not here")
def test_gp2_seed_is_gp2s_rule_with_a_never_place_tree():
    assert _seed("gp2").strip() == gp.with_place(GP2_NOCLEAN_PATH.read_text(encoding="utf-8"))


def _place_features(rng: random.Random) -> dict[str, float]:
    light = rng.randint(0, 1)
    return _place_dict(pl_is_light=float(light), pl_is_roundabout=float(1 - light),
                       pl_joins_separated=float(rng.randint(0, 1)), pl_stopped_near=float(rng.randint(0, 6)))


@pytest.mark.parametrize("name, lights, roundabouts", [(n, *flags) for n, flags in SEEDS.items()])
def test_seed_place_trees_match_hand_place(name, lights, roundabouts):
    from evolved_rules.rules import hand_place
    p = TreePolicy(_seed(name))
    rng = random.Random(7)
    dicts = [_place_features(rng) for _ in range(200)]
    tree = [p.place(f) for f in dicts]
    hand = [hand_place(f, lights, roundabouts) for f in dicts]
    assert [_sign(x) for x in tree] == [_sign(x) for x in hand]
    assert any(x > 0 for x in hand) and any(x < 0 for x in hand) and any(x == 0 for x in hand)
    for i in range(0, 200, 8):
        assert _first(tree[i:i + 8]) == _first(hand[i:i + 8]), i


@pytest.mark.parametrize("name, lights, roundabouts", [(n, *flags) for n, flags in SEEDS.items()])
def test_seed_upgrade_trees_match_package_upgrade(name, lights, roundabouts):
    from evolved_rules.features import offer_features
    from evolved_rules.rules import package_upgrade
    from evolved_rules.state import Offer
    p = TreePolicy(_seed(name))
    rng = random.Random(11)
    dicts = []
    for _ in range(200):
        f = dict.fromkeys(gp.GLOBAL_TERMS, 0.0)
        f.update(offer_features(Offer(0, rng.randint(0, 5), rng.randint(1, 3), rng.randint(0, 40))))
        dicts.append(f)
    tree = [p.upgrade(f) for f in dicts]
    hand = [package_upgrade(f, lights, roundabouts) for f in dicts]
    assert [64 * x for x in tree] == hand        # 1000/64 and offer_roads/64 are exact
    assert {f["type_3"] for f in dicts} == {0.0, 1.0} and {f["type_4"] for f in dicts} == {0.0, 1.0}
    for i in range(0, 200, 8):
        assert _first(tree[i:i + 8]) == _first(hand[i:i + 8]), i


# --- task 3: the games (host) --------------------------------------------------------------------------------

def _same_game(a, b) -> None:
    assert (a.trips, a.seconds, a.commands, a.action_counts) == (b.trips, b.seconds, b.commands, b.action_counts)


@pytest.mark.host
def test_place_minus_one_plays_like_four_trees(host):
    from evolved_rules.agent import play_game
    text = GP3_FINAL_PATH.read_text(encoding="utf-8")
    four = play_game(host, 3100, TreePolicy(text), record=False)
    five = play_game(host, 3100, TreePolicy(gp.with_place(text)), record=False)
    assert four.trips > 0
    _same_game(four, five)


@pytest.mark.host
def test_gplightround_tree_plays_like_gphand(host):
    from evolved_rules.agent import play_game
    from evolved_rules.rules import GPHand
    text = GP3_FINAL_PATH.read_text(encoding="utf-8")
    tree = play_game(host, 3100, TreePolicy(_seed("gplightround")), record=True)
    hand = play_game(host, 3100, GPHand(text, True, True, "gplightround"), record=True)
    placed = [a for a in tree.recording["actions"]
              if a["command"] == "build" and a["tool"] in ("TrafficLight", "Roundabout") and a["accepted"]]
    assert placed  # the games place something, so this is not the identity of two games that never place
    _same_game(tree, hand)
