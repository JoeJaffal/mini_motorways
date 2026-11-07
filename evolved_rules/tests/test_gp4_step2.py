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


# --- task 4: place_tree in the evolution loop ----------------------------------------------------------------

import json  # noqa: E402
import pickle  # noqa: E402

from evolved_rules import evolve as evo  # noqa: E402
from evolved_rules.evolve import Config, read_checkpoint, read_jsonl  # noqa: E402
from evolved_rules.tests.test_evolve import SMALL, fake, run  # noqa: E402,F401 (fake is a fixture)

REFERENCE = gp.SEPARATED_TEXT


def _place_cfg(**kw) -> Config:
    return Config(**{**SMALL, "remove_tree": True, "place_tree": True, **kw})


def test_place_tree_population():
    cfg = Config(remove_tree=True, place_tree=True, pop=12, seed_texts=(_seed("gp2"), _seed("light")))
    cfg.check()
    random.seed(cfg.seed)
    pop = evo.initial_population(cfg)
    assert len(pop) == 12 and all(len(t.splitlines()) == 5 for t in pop)
    assert pop[:3] == [gp.with_place(t) for t in (gp.HAND_TEXT, gp.SEPARATED_TEXT, gp.CLEAN_TEXT)]
    assert pop[3:5] == [gp.with_place(_seed("gp2")), gp.with_place(_seed("light"))]
    assert len(set(pop)) == 12 and cfg.trees == 5
    for t in pop:  # every text is canonical and has the five trees in order
        assert gp.individual_text(gp.individual_from_text(t)) == t
        assert [ln.split(":")[0] for ln in t.splitlines()] == list(gp.ALL_TREE_NAMES)
    # the same seed text twice, or a seed equal to a hand rule, is kept once
    dup = Config(remove_tree=True, place_tree=True, pop=6, seed_texts=(_seed("light"), _seed("light"), gp.HAND_TEXT))
    random.seed(dup.seed)
    three = [gp.with_place(t) for t in (gp.HAND_TEXT, gp.SEPARATED_TEXT, gp.CLEAN_TEXT)]
    assert evo.initial_population(dup)[:4] == three + [_seed("light").strip()]


def test_place_tree_needs_remove_tree():
    with pytest.raises(ValueError, match="place_tree needs remove_tree"):
        Config(place_tree=True).check()
    with pytest.raises(ValueError, match="place_tree must be a bool"):
        Config(remove_tree=True, place_tree=1).check()
    _place_cfg().check()


def test_five_tree_seed_needs_place_tree():
    with pytest.raises(ValueError, match="5-tree seed text needs place_tree"):
        Config(remove_tree=True, place_tree=False, seed_texts=(_seed("light"),)).check()
    with pytest.raises(ValueError, match="5-tree seed text needs place_tree"):
        Config(seed_texts=(_seed("light"),)).check()  # not even remove_tree
    with pytest.raises(ValueError, match="5-tree reference text needs place_tree"):
        Config(remove_tree=True, hof=3, reference_text=_seed("light")).check()
    # a 4-tree text still needs only remove_tree, and with place_tree 3-, 4- and 5-tree texts all pass
    Config(remove_tree=True, seed_texts=(GP3_FINAL_CANON,)).check()
    with pytest.raises(ValueError, match="4-tree seed text needs remove_tree"):
        Config(seed_texts=(GP3_FINAL_CANON,)).check()
    _place_cfg(seed_texts=(HAND_TEXT, GP3_FINAL_CANON, _seed("light")), hof=3, reference_text=_seed("gp2")).check()


def test_canonical_reference_is_five_trees():
    gp3_final = GP3_FINAL_PATH.read_text(encoding="utf-8")
    cfg = _place_cfg()
    assert evo.canonical(cfg, gp3_final).endswith("place: -1.0")
    assert evo.canonical(cfg, gp3_final) == _five("-1.0") and len(evo.canonical(cfg, HAND_TEXT).splitlines()) == 5
    assert evo.canonical(cfg, _seed("light")) == _seed("light").strip()  # a 5-tree text stays as it is
    # without place_tree nothing changes: gp-3's 4-tree form and gp-2's 3-tree form
    assert evo.canonical(Config(remove_tree=True), gp3_final) == GP3_FINAL_CANON
    assert evo.canonical(Config(), HAND_TEXT) == HAND_CANON
    # the hall of fame starts from the canonical reference and seeds
    hall = evo.initial_hof(_place_cfg(hof=3, reference_text=gp3_final, seed_texts=(_seed("light"),)))
    assert [m["text"] for m in hall] == [_five("-1.0"), _seed("light").strip()]


def test_place_checkpoint_format(fake, tmp_path):  # noqa: F811
    assert evo.PLACE_CHECKPOINT_FORMAT == 5
    run(tmp_path, "place", _place_cfg(min_gens=50, max_gens=1))
    ckpt = read_checkpoint(tmp_path / "place")
    assert ckpt["format"] == 5 and "hof" not in ckpt
    assert all(len(t.splitlines()) == 5 for t in ckpt["population"])
    # a hall keeps format 5 (the format says "place tree"; the hall is still in the state)
    run(tmp_path, "placehall", _place_cfg(min_gens=50, max_gens=1, hof=3, reference_text=REFERENCE))
    ckpt = read_checkpoint(tmp_path / "placehall")
    assert ckpt["format"] == 5 and ckpt["hof"] and all(len(m["text"].splitlines()) == 5 for m in ckpt["hof"])
    # the older formats are unchanged
    run(tmp_path, "three", Config(**{**SMALL, "min_gens": 50, "max_gens": 1}))
    run(tmp_path, "four", Config(**{**SMALL, "min_gens": 50, "max_gens": 1, "remove_tree": True}))
    run(tmp_path, "hall", Config(**{**SMALL, "min_gens": 50, "max_gens": 1, "hof": 3, "reference_text": REFERENCE}))
    assert [read_checkpoint(tmp_path / n)["format"] for n in ("three", "four", "hall")] == [3, 3, 4]
    # a place-tree run resumes (with or without its hall) and keeps its 5 trees
    for name in ("place", "placehall"):
        cfg, state = evo.load(tmp_path / name, overrides={"max_gens": 2})
        assert cfg.place_tree and state["format"] == 5
        run(tmp_path, name, resume=True, overrides={"max_gens": 2})
        ckpt = read_checkpoint(tmp_path / name)
        assert ckpt["generation"] == 2 and all(len(t.splitlines()) == 5 for t in ckpt["population"])


def test_checkpoint_formats_3_4_and_5_are_read_and_others_refused(tmp_path):
    for fmt in (3, 4, 5):
        (tmp_path / evo.CHECKPOINT).write_bytes(pickle.dumps({"format": fmt}))
        assert read_checkpoint(tmp_path)["format"] == fmt
    (tmp_path / evo.CHECKPOINT).write_bytes(pickle.dumps({"format": 6}))
    with pytest.raises(ValueError, match="checkpoint format 6, expected 3, 4 or 5"):
        read_checkpoint(tmp_path)


def test_a_place_checkpoint_that_does_not_match_the_config_is_refused(fake, tmp_path):  # noqa: F811
    run(tmp_path, "a", _place_cfg(min_gens=50, max_gens=1))
    path = tmp_path / "a" / evo.CONFIG
    config = json.loads(path.read_text(encoding="utf-8"))
    config["params"]["place_tree"] = False  # as if the flag were dropped: the 5-tree state must not resume as 4
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        evo.load(tmp_path / "a")


def test_place_tree_cannot_change_on_resume(fake, tmp_path):  # noqa: F811
    run(tmp_path, "a", _place_cfg(min_gens=50, max_gens=1))
    with pytest.raises(ValueError, match="--place-tree"):
        evo.load(tmp_path / "a", overrides={"place_tree": False})


def test_a_run_made_before_place_tree_existed_resumes_without_it(fake, tmp_path):  # noqa: F811
    run(tmp_path, "a", Config(**{**SMALL, "min_gens": 50, "max_gens": 1, "remove_tree": True}))
    path = tmp_path / "a" / evo.CONFIG
    config = json.loads(path.read_text(encoding="utf-8"))
    config["params"].pop("place_tree", None)
    path.write_text(json.dumps(config), encoding="utf-8")
    cfg, state = evo.load(tmp_path / "a", overrides={"place_tree": False, "max_gens": 2})
    assert cfg.place_tree is False and cfg.trees == 4 and state["format"] == 3


def test_a_place_run_keeps_5_tree_individuals_including_immigrants(fake, tmp_path):  # noqa: F811
    cfg = _place_cfg(pop=10, dedup=True, immigrants=3, validate_top=2, max_gens=2, min_gens=5,
                     seed_texts=(_seed("light"),))
    fake["game"] = lambda text, seed, cap_s: {"trips": 50 + len(text) % 3, "seconds": 300.0, "commands": 5,
                                              "tiles_built": 4}  # 3 behaviours: duplicates and immigrants
    run(tmp_path, "p", cfg)
    gens = read_jsonl(tmp_path / "p" / evo.GENERATIONS)
    assert len(gens) == 2 and all(r["immigrants"] > 0 for r in gens)
    pop = read_checkpoint(tmp_path / "p")["population"]
    assert all(len(gp.individual_from_text(t)) == 5 for t in pop)
    assert all(len(t.splitlines()) == 5 for t, _ in fake["plays"])
    best = (tmp_path / "p" / evo.BEST).read_text(encoding="utf-8").strip()
    assert len(best.splitlines()) == 5


def test_cli_place_tree_flag(fake, tmp_path, monkeypatch):  # noqa: F811
    from evolved_rules.engine import Engine
    assert evo.FLAG_NAMES["place_tree"] == "--place-tree"
    monkeypatch.setattr(evo, "EVOLVE_DIR", tmp_path)
    monkeypatch.setattr(evo, "_make_engine", lambda cfg, run_dir: Engine(workers=2, cache_path=run_dir / evo.CACHE))
    seed_file = tmp_path / "light.txt"
    seed_file.write_text(_seed("light"), encoding="utf-8")
    common = ["--pop", "8", "--first-seeds", "2", "--more-seeds", "2", "--racing-top", "4", "--validate-top", "2",
              "--validation", "1500-1502", "--max-gens", "1", "--workers", "2"]
    assert evo.main(["--run", "c5", *common, "--remove-tree", "--place-tree", "--seed-text", str(seed_file)]) == 0
    params = json.loads((tmp_path / "c5" / evo.CONFIG).read_text())["params"]
    assert params["place_tree"] is True and params["remove_tree"] is True
    assert read_checkpoint(tmp_path / "c5")["format"] == 5
    # --place-tree without --remove-tree is refused up front; so is a 5-tree seed without --place-tree
    with pytest.raises(SystemExit):
        evo.main(["--run", "c5b", *common, "--place-tree"])
    with pytest.raises(SystemExit):
        evo.main(["--run", "c5c", *common, "--remove-tree", "--seed-text", str(seed_file)])
    # a resume carries the flag from the saved run
    assert evo.main(["--run", "c5", "--resume", "--max-gens", "2"]) == 0
    assert read_checkpoint(tmp_path / "c5")["generation"] == 2


def _game_with(trips: int, **counts: int) -> dict:
    return {"trips": trips, "seconds": 300.0, "commands": 9, "tiles_built": 4, "action_counts": dict(counts)}


def test_validation_record_counts_placements():
    cfg = Config(validation=(1500, 1501))
    games = [_game_with(100, draw=7, TrafficLight=3), _game_with(120, draw=5, Roundabout=1)]
    rec = evo._validation_record(cfg, 4, "text", 12, games)
    assert rec["lights"] == [3, 0] and rec["roundabouts"] == [0, 1]
    assert rec["trips"] == [100, 120] and rec["mean"] == 110.0  # the older fields are as before
    # a result with no action_counts (an old cache line, a fake game) counts 0
    bare = evo._validation_record(cfg, 4, "text", 12, [{"trips": 1, "seconds": 2.0}, {"trips": 3, "seconds": 4.0}])
    assert bare["lights"] == [0, 0] and bare["roundabouts"] == [0, 0]


def test_the_engine_keeps_action_counts_in_what_it_caches(tmp_path, monkeypatch):
    # the engine stores the whole game summary, action_counts included, so placements survive the cache
    from concurrent.futures import ThreadPoolExecutor
    from evolved_rules import engine as en
    monkeypatch.setattr(en, "_make_worker", lambda: ThreadPoolExecutor(max_workers=1))
    monkeypatch.setattr(en, "_play_job", lambda text, seed, cap_s: _game_with(10, TrafficLight=2, Roundabout=1))
    path = tmp_path / "cache.jsonl"
    eng = en.Engine(workers=1, cache_path=path)
    first = eng.play([(HAND_TEXT, 1)])[0]
    eng.close()
    assert first["action_counts"] == {"TrafficLight": 2, "Roundabout": 1}
    eng = en.Engine(workers=1, cache_path=path)
    try:
        assert eng.cached(HAND_TEXT, 1)["action_counts"] == {"TrafficLight": 2, "Roundabout": 1}
    finally:
        eng.close()


def test_place_run_reports_the_incumbents_lights_and_roundabouts(fake, tmp_path):  # noqa: F811
    cfg = _place_cfg(min_gens=50, max_gens=2)
    fake["game"] = lambda text, seed, cap_s: {
        "trips": 100 + len(text) % 7, "seconds": 300.0, "commands": 5, "tiles_built": 4,
        "action_counts": {"TrafficLight": seed % 3, "Roundabout": 1 if seed % 2 else 0}}
    run(tmp_path, "r", cfg)
    vals = read_jsonl(tmp_path / "r" / evo.VALIDATION)
    assert vals and all(len(v["lights"]) == len(v["roundabouts"]) == 3 for v in vals)
    assert vals[0]["lights"] == [s % 3 for s in cfg.validation]
    assert vals[0]["roundabouts"] == [s % 2 for s in cfg.validation]
    gens = read_jsonl(tmp_path / "r" / evo.GENERATIONS)
    inc = gens[-1]["incumbent"]
    mine = next(v for v in vals if v["hash"] == inc["hash"])
    assert inc["lights"] == pytest.approx(sum(mine["lights"]) / 3)
    assert inc["roundabouts"] == pytest.approx(sum(mine["roundabouts"]) / 3)
    line = evo.format_record(gens[-1], cfg)
    assert f"{inc['lights']:.1f} lights" in line and f"{inc['roundabouts']:.1f} roundabouts" in line


def test_old_configs_print_and_record_as_before(fake, tmp_path):  # noqa: F811
    cfg = Config(**{**SMALL, "min_gens": 50, "max_gens": 2})
    run(tmp_path, "old", cfg)
    gens = read_jsonl(tmp_path / "old" / evo.GENERATIONS)
    assert "lights" not in gens[-1]["incumbent"] and "roundabouts" not in gens[-1]["incumbent"]
    line = evo.format_record(gens[-1], cfg)
    assert "lights" not in line and "roundabouts" not in line
