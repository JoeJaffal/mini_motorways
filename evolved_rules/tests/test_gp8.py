"""gp-8: multi-city map ids, per-city generation draws, the roundabout head."""
import random

import pytest

from evolved_rules import engine, evolve7, gp, linear


def test_map_ids_round_trip_and_la_is_the_plain_seed():
    assert engine.map_id("LosAngeles", 123) == 123
    assert engine.split_map(123) == ("LosAngeles", 123)
    for c in ("Beijing", "Tokyo", "DarEsSalaam"):
        assert engine.split_map(engine.map_id(c, 999)) == (c, 999)
    with pytest.raises(ValueError):
        engine.map_id("Paris", 1)
    with pytest.raises(ValueError):
        engine.map_id("Tokyo", engine.MAP_STRIDE)
    with pytest.raises(ValueError):
        engine.split_map(9 * engine.MAP_STRIDE)


def test_one_city_draw_is_gp7s():
    random.seed(5)
    a = evolve7.draw_maps({"maps": 12})
    random.seed(5)
    assert a == random.sample(range(1, 1000), 12)


def test_four_city_draw_interleaves_one_per_city():
    cities = ["LosAngeles", "Beijing", "Tokyo", "DarEsSalaam"]
    random.seed(5)
    ids = evolve7.draw_maps({"maps": 12, "cities": cities})
    got = [engine.split_map(i) for i in ids]
    assert [c for c, _ in got] == cities * 3
    assert [c for c, _ in got[:evolve7.CUT_MAPS]] == cities
    assert all(1 <= s <= 999 for _, s in got)
    with pytest.raises(ValueError):
        evolve7.draw_maps({"maps": 10, "cities": cities})


def test_roundabout_head_text_parses_and_flags_both_tools():
    sp = linear.Space(l_text=open(linear.__file__.replace("linear.py", "seeds/gp7/cma1_3tree.txt")).read(),
                      lights=True, roundabouts=True)
    x = linear.x_from_l(sp)
    x[linear.INDEX["bias"]] = -3.0
    x[linear.INDEX["round.bias"]] = -4.0
    t = linear.text_from_x(x, sp)
    assert "flags: clean=0 lights=1 roundabouts=1" in t
    assert "if_gt(pl_is_roundabout, 0.5" in t and "pl_placed" in t
    pol = gp.TreePolicy(t)
    assert (pol.places_lights, pol.places_roundabouts) == (True, True)
    base = {k: 0.0 for k in gp.PLACE_TERMS}
    assert pol.place({**base, "pl_is_light": 1.0}) == -3.0
    assert pol.place({**base, "pl_is_roundabout": 1.0}) == -4.0
    only_r = linear.text_from_x(x, linear.Space(l_text=sp.l_text, roundabouts=True))
    assert gp.TreePolicy(only_r).place({**base, "pl_is_light": 1.0}) == -1.0
