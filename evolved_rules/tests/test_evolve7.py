"""evolve7 (cma-7), linear and stats7 unit tests with a fake engine (no host)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from evolved_rules import evolve7 as E
from evolved_rules import gp, linear, stats7

L = (Path(__file__).resolve().parents[1] / "seeds" / "gp7" / "cma1_3tree.txt").read_text().strip()


class FakeEngine:
    """Deterministic fake results per (text, seed); counts games and cache hits like Engine."""

    def __init__(self):
        self.cache, self.games_played, self.cache_hits = {}, 0, 0

    def _game(self, text, seed):
        h = int(hashlib.sha256(f"{text}|{seed}".encode()).hexdigest()[:8], 16)
        return {"trips": 400 + h % 900, "seconds": 900.0 + h % 700, "rejected_actions": 0}

    def play(self, jobs):
        out = []
        for key in jobs:
            if key in self.cache:
                self.cache_hits += 1
            else:
                self.cache[key] = self._game(*key)
                self.games_played += 1
            out.append(dict(self.cache[key]))
        return out

    def play_logged(self, jobs, out_dir):
        return self.play(jobs)

    def close(self):
        pass


def _space():
    return linear.Space(l_text=L)


def _cfg(**kw):
    c = {"popsize": 6, "maps": 6, "sigma0": 0.3, "seed": 1, "workers": 2, "stop_at": "2099-01-01T00:00:00+00:00",
         "log_gen0": False, "force_cut": True, "cap_s": 3600.0}
    c.update(kw)
    return c


def _strip(r):
    return {k: v for k, v in r.items() if k not in ("wall_s", "cache_hits", "games_played")}


def test_linear_l_point_keeps_l_trees_and_round_trips():
    sp = _space()
    t = linear.text_from_x(linear.x_from_l(sp), sp)
    lines = t.splitlines()
    assert lines[1] == L.splitlines()[1] and lines[2] == L.splitlines()[2]
    assert lines[0].startswith("priority: add(" + L.splitlines()[0][len("priority: "):])
    assert gp.individual_text(gp.individual_from_text(t)) == t
    assert linear.DIM == 97 and len(linear.UNIT_SCALE) == 9 + 4 + 4 + 1  # gp-8: +2 light terms, +11 round head


def test_linear_scales_keep_x0_in_bounds():
    sp = _space()
    named = {**linear.l_rule_weights(sp), **linear.SEPARATED_COST}
    spreads = {i: 0.001 for i in range(linear.DIM)}  # tiny spreads -> raw scales huge, clipped at 10
    spreads[linear.INDEX["priority.is_separated"]] = 1e6  # huge spread -> scale tiny; x0 would leave the bounds
    s = linear.scales_for_x0(spreads, named)
    x0 = linear.x_from_weights(named, linear.Space(l_text=L, scales=s))
    assert max(abs(v) for v in x0) <= 4.5 + 1e-9
    assert all(s[i] == 1.0 for i in linear.UNIT_SCALE)


def test_generation_records_cut_ledger_and_population_average(tmp_path):
    sp = _space()
    cfg = _cfg()
    x0 = linear.x_from_l(sp)
    state = E.start(cfg, tmp_path, x0, sp)
    eng = FakeEngine()
    state = E.generation(cfg, state, eng, tmp_path, sp)
    rec = json.loads((tmp_path / E.GENERATIONS).read_text().splitlines()[-1])
    assert rec["cut"] >= 1 and rec["completed"] == rec["distinct"] - rec["cut"]
    assert rec["population"]["average"] is not None and rec["population"]["best"] >= rec["population"]["average"]
    assert rec["ledger"] == rec["charged"] > 0 and state["ledger"] == rec["ledger"]
    assert (tmp_path / "final_mean.txt").exists() and state["generation"] == 1


def test_resume_repeats_generations_exactly(tmp_path):
    sp = _space()
    cfg = _cfg()
    x0 = linear.x_from_l(sp)
    a, b = tmp_path / "a", tmp_path / "b"
    sa = E.start(cfg, a, x0, sp)
    ea = FakeEngine()
    for _ in range(3):
        sa = E.generation(cfg, sa, ea, a, sp)
    sb = E.start(cfg, b, x0, sp)
    eb = FakeEngine()
    sb = E.generation(cfg, sb, eb, b, sp)
    E.evo.write_checkpoint(b, sb)
    # "kill" mid-generation 1: run it once, then throw its result away and resume from the checkpoint
    E.generation(cfg, sb, eb, b, sp)
    cfg_b, sb, _ = E.load(b, {})
    for _ in range(2):
        sb = E.generation(cfg_b, sb, eb, b, sp)
    ra = [_strip(json.loads(x)) for x in (a / E.GENERATIONS).read_text().splitlines()]
    rb = [_strip(json.loads(x)) for x in (b / E.GENERATIONS).read_text().splitlines()]
    assert ra == rb
    import pickle
    ma, mb = pickle.loads(sa["es"]), pickle.loads(sb["es"])
    assert np.array_equal(ma.mean, mb.mean) and ma.sigma == mb.sigma


def test_stop_time_and_stop_file(tmp_path):
    sp = _space()
    cfg = _cfg(stop_at="2030-01-01T00:00:00+00:00")
    state = E.start(cfg, tmp_path, linear.x_from_l(sp), sp)
    now = lambda: dt.datetime(2029, 12, 31, 23, 0, tzinfo=dt.timezone.utc)
    (tmp_path / E.STOP_FILE).write_text("2029-12-31T22:00:00+00:00")
    out = E.run(cfg, state, tmp_path, sp, engine=FakeEngine(), now=now, log=lambda *a: None)
    assert out["generation"] == 0
    assert json.loads((tmp_path / E.STATUS).read_text())["status"] == "budget"


def test_resume_refuses_code_change_and_other_overrides(tmp_path, monkeypatch):
    sp = _space()
    E.start(_cfg(), tmp_path, linear.x_from_l(sp), sp)
    with pytest.raises(ValueError):
        E.load(tmp_path, {"popsize": 8})
    monkeypatch.setattr(E, "CODE_VERSION", "other")
    with pytest.raises(ValueError):
        E.load(tmp_path, {})


def test_rank_values_order():
    keys = [(1, 900.0, 1.0), (0, 1200.0, 1.0), (1, 1000.0, 1.0), (1, 1000.0, 1.0)]
    assert E.rank_values(keys) == [2.0, 3.0, 0.0, 0.0]  # cut sample below all completed ones


# --- stats7 ----------------------------------------------------------------------------------------------------

def test_decide_headline_rules():
    vl = {s: 1000.0 for s in range(1550, 1750)}
    worse = {s: 990.0 for s in vl}
    r = stats7.decide_headline({"a": worse}, vl, None, {})
    assert r["headline"] == "L" and r["c_star"] is None
    rng = np.random.default_rng(0)
    better = {s: 1000.0 + 50 + float(rng.normal(0, 200)) for s in vl}
    tL = {s: 1000.0 + float(rng.normal(0, 250)) for s in range(6100, 7000)}
    tc = {s: tL[s] + 60 + float(rng.normal(0, 250)) for s in range(6100, 6650)}  # 550 complete -> n = 500
    r = stats7.decide_headline({"a": worse, "b": better}, vl, tc, tL)
    assert r["c_star"] == "b" and r["test_n"] == 500 and r["headline"] == "b" and r["test"]["p"] < 0.05
    r = stats7.decide_headline({"b": better}, vl, {s: tc[s] for s in range(6100, 6450)}, tL)
    assert r["test_n"] == 300 and r["headline"] == "L"


def test_holm_and_bca():
    h = stats7.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert h == {"a": 0.03, "c": 0.06, "b": 0.06}
    lo, hi = stats7.bca_interval([1.0, 2.0, 3.0, 4.0, 5.0] * 20, 0.90)
    assert lo < 3.0 < hi


# --- gp-7 arm (fork, epochs, insertion) ----------------------------------------------------------------------

def _trunk(tmp_path, gens=1):
    sp = _space()
    cfg = _cfg(force_cut=False)
    t = tmp_path / "trunk"
    st = E.start(cfg, t, linear.x_from_l(sp), sp)
    eng = FakeEngine()
    for _ in range(gens):
        st = E.generation(cfg, st, eng, t, sp)
    E.evo.write_checkpoint(t, st)
    return t, eng


def test_fork_with_empty_slots_decodes_like_the_trunk(tmp_path):
    t, eng = _trunk(tmp_path)
    cfg, st, sp = E.fork(t, tmp_path / "arm", workers=1, stop_at=None)
    assert cfg["arm"] == "gp7" and cfg["fork_gen"] == 1 and st["ledger"] == json.loads(
        (t / E.GENERATIONS).read_text().splitlines()[-1])["ledger"]
    import pickle
    es = pickle.loads(st["es"])
    xs = es.ask()
    space = linear.Space.from_json(st["space"])
    assert [linear.text_from_x(x, space) for x in xs] == [linear.text_from_x(x, _space()) for x in xs]


def test_epoch_runs_every_fifth_generation_and_charges_the_race(tmp_path):
    t, _ = _trunk(tmp_path)
    cfg, st, sp = E.fork(t, tmp_path / "arm", workers=1, stop_at=None)
    eng = FakeEngine()
    for _ in range(5):
        st = E.generation(cfg, st, eng, tmp_path / "arm", sp)
    recs = [json.loads(x) for x in (tmp_path / "arm" / "slots.jsonl").read_text().splitlines()]
    assert len(recs) == 1 and recs[0]["gen"] == 5 and st["probe_next"] == 10000 + 24
    assert recs[0]["charged"] == 24 * (1 + 2 * len(recs[0]["kept"]))


def test_probe_seeds_never_pass_49999(tmp_path):
    t, _ = _trunk(tmp_path)
    cfg, st, sp = E.fork(t, tmp_path / "arm", workers=1, stop_at=None)
    st = {**st, "probe_next": E.PROBE_LAST - 24 + 1}  # the last full race fits exactly: 49976-49999
    eng = FakeEngine()
    for _ in range(10):  # epochs at gens 5 and 10
        st = E.generation(cfg, st, eng, tmp_path / "arm", sp)
    recs = [json.loads(x) for x in (tmp_path / "arm" / "slots.jsonl").read_text().splitlines()]
    assert recs[0]["probes"] == [49976, 49999] and st["probe_next"] == 50000
    assert recs[1]["skipped"] == "probe seeds exhausted" and recs[1]["charged"] == 0
    assert max(s for _, s in eng.cache) <= 49999


def test_accepted_slot_is_inserted(tmp_path, monkeypatch):
    t, _ = _trunk(tmp_path)
    cfg, st, sp = E.fork(t, tmp_path / "arm", workers=1, stop_at=None)
    from evolved_rules import slots, stats7
    monkeypatch.setattr(slots, "screen", lambda props, recs: [
        {"slot": 2, "tree": "mul(stopped_on, near_shop)", "w0": 0.5, "key": (1, 0.0)}])
    monkeypatch.setattr(slots, "slot_spread", lambda k, tree, recs: 0.25)
    monkeypatch.setattr(stats7, "paired_t_one_sided", lambda d: {"p": 0.01, "mean": 5.0})
    eng = FakeEngine()
    for _ in range(5):
        st = E.generation(cfg, st, eng, tmp_path / "arm", sp)
    space = linear.Space.from_json(st["space"])
    assert space.masks[2] == 1.0 and space.slot_trees[2] == "mul(stopped_on, near_shop)"
    import pickle
    es = pickle.loads(st["es"])
    k = linear.INDEX["slot2"]
    assert es.mean[k] == pytest.approx(0.5 / space.scales[k])
    assert "cslot=mul(" in (tmp_path / "arm" / "final_mean.txt").read_text()


def test_resume_across_an_epoch_is_exact(tmp_path):
    t, _ = _trunk(tmp_path)
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    cfg, sa, sp = E.fork(t, a_dir, workers=1, stop_at=None)
    ea = FakeEngine()
    for _ in range(6):
        sa = E.generation(cfg, sa, ea, a_dir, sp)
    cfg_b, sb, _ = E.fork(t, b_dir, workers=1, stop_at=None)
    eb = FakeEngine()
    for _ in range(4):
        sb = E.generation(cfg_b, sb, eb, b_dir, sp)
    E.evo.write_checkpoint(b_dir, sb)
    E.generation(cfg_b, sb, eb, b_dir, sp)  # the epoch generation, then "killed"
    cfg_b, sb, _ = E.load(b_dir, {})
    for _ in range(2):
        sb = E.generation(cfg_b, sb, eb, b_dir, sp)
    strip = lambda p: [_strip(json.loads(x)) for x in p.read_text().splitlines()]
    assert strip(a_dir / E.GENERATIONS) == strip(b_dir / E.GENERATIONS)
    import pickle
    assert np.array_equal(pickle.loads(sa["es"]).mean, pickle.loads(sb["es"]).mean)


def test_slot_proposals_deterministic_bounded_and_no_templates():
    import random
    from evolved_rules import slots
    a = slots.propose([0, 2], 0.0, random.Random("1:5"))
    b = slots.propose([0, 2], 0.0, random.Random("1:5"))
    assert a == b and len(a) == slots.PROPOSALS and {k for k, _ in a} == {0, 2}
    banned = slots.templates(0.0)
    for k, t in a:
        tree = gp._parse_tree(t, 0, pset=slots.SLOT_PSETS[k], name="slot")
        assert len(tree) <= slots.MAX_NODES and tree.height <= slots.MAX_DEPTH
        assert t not in banned and not slots._is_num(t)
    assert slots.propose([], 0.0, random.Random(1)) == []


def test_slot_screen_rejects_without_records():
    from evolved_rules import slots
    assert slots.screen([(0, "mul(is_evo, worst_overcrowded)"), (2, "mul(stopped_on, near_shop)")], []) == []
