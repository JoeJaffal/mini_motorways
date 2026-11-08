"""Failure autopsy (autopsy.py): plays exactly like play_game, tallies inputs and names a cause."""
from __future__ import annotations

import pytest

from evolved_rules.host import PRE_VERSIONING
from evolved_rules.tests.helpers import SIM7, for_simulator

from evolved_rules import autopsy
from evolved_rules.agent import play_game
from evolved_rules.gp import HAND_TEXT, TreePolicy
from evolved_rules.rules import HandRule

CAUSES = {"not_connected", "slow_arrival", "gridlock", "car_shortage", "unreachable_cars", "dispatch_gap", "cap"}


@pytest.mark.host
def test_autopsy_plays_the_same_game_and_names_a_cause(host, monkeypatch):
    monkeypatch.setattr(autopsy, "_HOST", host)
    out = autopsy.play("hand", 2000)
    row = out["row"]
    # the Phase 1 fingerprint of hand on 2000, per simulator
    assert (row["trips"], round(row["seconds"], 1)) == for_simulator({PRE_VERSIONING: (57, 404.8), SIM7: (210, 690.1)})
    assert row["cause"] in CAUSES and row["cause"] != "cap"
    assert row["houses_reaching"] <= row["houses_of_color"] and row["cars_busy"] <= row["cars_of_color"]
    tally = out["tally"]
    assert tally["tiles_needed"]["n"] > 0 and tally["road_stock"]["n"] > 0


@pytest.mark.host
def test_the_watched_policy_passes_every_attribute_the_agent_reads(host, monkeypatch):
    # a tree policy reads merged globals (wants_globals) and plans coverage: the wrapper must keep both
    monkeypatch.setattr(autopsy, "_HOST", host)
    text = "priority: neg(tiles_needed)\nhold: sub(0.0625, road_stock)\nupgrade: offer_roads"
    monkeypatch.setattr(autopsy, "make_policy", lambda spec: TreePolicy(text))
    row = autopsy.play("tree:x", 1000, cap_s=200.0)["row"]
    ref = play_game(host, 1000, TreePolicy(text), cap_s=200.0, record=False)
    assert (row["trips"], row["seconds"], row["tiles_built"]) == (ref.trips, ref.seconds, ref.tiles_built)
    assert row["tiles_built"] > 0  # the coverage policy built roads, so the comparison is not vacuous


def test_watched_copies_the_policy_switches():
    w = autopsy._Watched(TreePolicy(HAND_TEXT), autopsy._Tally())
    assert (w.coverage, w.wants_globals, w.acts) == (True, True, True)
    w = autopsy._Watched(HandRule(), autopsy._Tally())
    assert (w.coverage, w.wants_globals, w.acts) == (False, False, True)


def test_tally_counts_values_and_distinct_ones():
    t = autopsy._Tally()
    for v in (0.0, 2.0, 2.0, 5.0):
        t.add({"x": v})
    s = t.stats["x"]
    assert (s["n"], s["nonzero"], s["min"], s["max"], sorted(s["values"])) == (4, 3, 0.0, 5.0, [0.0, 2.0, 5.0])
