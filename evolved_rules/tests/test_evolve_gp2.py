"""gp-2 changes to the evolution loop (EXPERIMENTS.md): paired-test stop rule, behavioural de-duplication,
immigrants, validating the racing top 3, the new defaults and the checkpoint format."""
from __future__ import annotations

import json
import pickle
import random

import pytest

from evolved_rules import evolve as evo
from evolved_rules import gp
from evolved_rules.engine import Engine
from evolved_rules.evolve import Config, Convergence, read_checkpoint, read_jsonl
from evolved_rules.tests.test_evolve import DETERMINISTIC, SMALL, fake, run, synthetic  # noqa: F401 (fixture)

GP2 = dict(validate_top=3, dedup=True, immigrants=8, sig_alpha=0.005)


def small2(**kw) -> Config:
    return Config(**{**SMALL, "pop": 12, "racing_top": 5, "elites": 2, **GP2, **kw})


# --- the paired-test stop rule ------------------------------------------------------------------------------

def test_paired_t_and_critical_t():
    assert evo.paired_t([3, 5, 7], [1, 2, 3]) == pytest.approx(3.0 / (1.0 / 3 ** 0.5))  # diffs 2, 3, 4
    assert evo.paired_t([5, 5], [1, 1]) == float("inf") and evo.paired_t([1, 1], [5, 5]) == float("-inf")
    assert evo.paired_t([2, 2], [2, 2]) == 0.0
    assert evo.critical_t(0.0, 50) == 0.0 and evo.critical_t(0.005, 1) == float("inf")
    assert evo.critical_t(0.005, 50) == pytest.approx(2.68, abs=0.01)  # one-sided 0.5 %, 49 degrees of freedom


def _conv(alpha=0.005):
    return Convergence(1, 2, 0.02, 3.0, sig_alpha=alpha)


BASE = [200 + (i % 10) * 10 for i in range(50)]  # mean 245, so the 2 % margin is 4.9 trips


def _mean(xs):
    return sum(xs) / len(xs)


def test_a_noise_sized_gain_does_not_count_with_the_paired_test():
    # +6 trips on average, above the margin, but +-90 from seed to seed (25 seeds +96, 25 seeds -84): t about 0.5
    noisy = [b + (96 if i % 2 else -84) for i, b in enumerate(BASE)]
    assert _mean(noisy) - _mean(BASE) == pytest.approx(6.0)
    c = _conv()
    assert c.observe(0, "a", _mean(BASE), 600.0, 5, trips=BASE)
    assert not c.observe(1, "b", _mean(noisy), 600.0, 5, trips=noisy) and c.since == 1
    assert c.anchor == _mean(BASE) and c.anchor_trips == BASE
    assert c.incumbent["text"] == "b"  # the incumbent is still the best validated mean
    # without the test the same candidate counts: exactly the gp-1 rule
    c0 = _conv(alpha=0.0)
    c0.observe(0, "a", _mean(BASE), 600.0, 5, trips=BASE)
    assert c0.observe(1, "b", _mean(noisy), 600.0, 5, trips=noisy)


def test_a_consistent_gain_counts_and_becomes_the_new_anchor():
    better = [b + 20 + (i % 3) for i, b in enumerate(BASE)]  # +21 on average, every seed better
    c = _conv()
    c.observe(0, "a", _mean(BASE), 600.0, 5, trips=BASE)
    assert c.observe(1, "b", _mean(better), 650.0, 5, trips=better)
    assert c.anchor == pytest.approx(_mean(better)) and c.anchor_trips == better and c.since == 0


def test_a_significant_gain_below_the_margin_does_not_count():
    tiny = [b + 2 for b in BASE]  # every seed +2: t infinite, but 2 < max(3, 4.9)
    c = _conv()
    c.observe(0, "a", _mean(BASE), 600.0, 5, trips=BASE)
    assert not c.observe(1, "b", _mean(tiny), 600.0, 5, trips=tiny)


def test_observe_many_counts_any_and_anchors_the_best_counting_candidate():
    c = _conv()
    c.observe(0, "a", _mean(BASE), 600.0, 5, trips=BASE)
    lucky_trips = [b + (2750 if i == 0 else 0) for i, b in enumerate(BASE)]  # +55 on average, all from one seed
    solid_trips = [b + 12 + (i % 2) for i, b in enumerate(BASE)]  # +12.5 on every seed
    lucky = {"text": "lucky", "mean": _mean(lucky_trips), "mean_seconds": 600.0, "size": 5, "trips": lucky_trips}
    solid = {"text": "solid", "mean": _mean(solid_trips), "mean_seconds": 600.0, "size": 5, "trips": solid_trips}
    assert c.observe_many(1, [lucky, solid])
    assert not lucky["test"]["counts"] and lucky["test"]["t"] < lucky["test"]["t_crit"]
    assert solid["test"]["counts"]
    assert c.anchor == solid["mean"] and c.anchor_trips == solid_trips
    assert c.incumbent["text"] == "lucky"  # the highest validated mean is still the incumbent
    with pytest.raises(ValueError):
        c.observe_many(2, [])


@pytest.mark.parametrize("anchor, mean", [(152.0, 155.04), (125.14, 128.14)])
def test_without_the_test_exact_margin_ties_round_like_gp1(anchor, mean):
    # gp-1 decided `mean >= anchor + required_gain`; computing the gain first rounds differently at these ties
    assert mean >= anchor + max(3.0, 0.02 * anchor)
    c = Convergence(1, 2, 0.02, 3.0, sig_alpha=0.0)
    c.observe(0, "a", anchor, 600.0, 5)
    assert c.observe(1, "b", mean, 600.0, 5)


def test_a_single_validation_seed_never_shows_a_significant_gain():
    c = _conv()
    c.observe(0, "a", 100.0, 600.0, 5, trips=[100])
    assert not c.observe(1, "b", 500.0, 600.0, 5, trips=[500])  # t and t_crit both infinite


def test_the_paired_state_round_trips():
    c = _conv()
    c.observe(0, "a", _mean(BASE), 600.0, 5, trips=BASE)
    assert Convergence.from_state(json.loads(json.dumps(c.state()))) == c


# --- behaviours and breeding -----------------------------------------------------------------------------------

def _games(*trips):
    return [{"trips": x, "seconds": 100.0 + x, "commands": 10} for x in trips]


def test_behaviours_keep_one_smallest_representative_per_identical_game_set():
    games = {"big": _games(5, 6), "small": _games(5, 6), "other": _games(7, 1), "late": _games(5, 6)}
    fitness = {k: evo._means(v) for k, v in games.items()}
    sizes = {"big": 9, "small": 3, "other": 4, "late": 3}
    reps = evo.behaviours(["big", "small", "other", "late"], games, fitness, sizes)
    # "small" beats "big" on size and "late" on first appearance; reps keep rank order (5.5 trips > 4.0 trips)
    assert reps == ["small", "other"]


@pytest.mark.parametrize("asked, expected", [(3, 3), (99, 12 - 2 - 1)])
def test_breed_with_dedup_has_no_copies_and_respects_the_immigrant_cap(monkeypatch, asked, expected):
    random.seed(3)
    cfg = small2(pop=12, elites=2)
    texts = list(dict.fromkeys(evo.initial_population(cfg)[:4]))
    fitness = {t: (float(i), 0.0) for i, t in enumerate(texts)}
    sizes = {t: gp.size(gp.individual_from_text(t)) for t in texts}
    elites = texts[:2]
    made = []
    real = gp.random_individual

    def counted(*a, **kw):
        ind = real(*a, **kw)
        made.append(gp.individual_text(ind))
        return ind

    monkeypatch.setattr(gp, "random_individual", counted)
    nxt = evo.breed(texts, fitness, sizes, elites, cfg, immigrants=asked)
    assert len(nxt) == 12 and nxt[:2] == elites and len(set(nxt)) == 12
    # exactly the last `expected` slots are fresh random trees (only immigrants call random_individual)
    assert all(t in made for t in nxt[12 - expected:])
    assert not any(t in made for t in nxt[2:12 - expected])
    assert 12 - 2 - expected >= 1  # at least one offspring survives the cap


def _breed_gp1(population, fitness, sizes, elites, cfg):
    """A frozen copy of breed() as it was at 49c8197 (gp-1)."""
    picks = [evo.tournament(population, fitness, sizes, cfg.tournament) for _ in range(cfg.pop - len(elites))]
    offspring = [gp.individual_from_text(t) for t in picks]
    for i in range(1, len(offspring), 2):
        if random.random() < cfg.cxpb:
            gp.mate(offspring[i - 1], offspring[i])
    for ind in offspring:
        if random.random() < cfg.mutpb:
            gp.mutate(ind)
    return list(elites) + [gp.individual_text(ind) for ind in offspring]


@pytest.mark.parametrize("seed", [4, 5, 6])
def test_breed_without_dedup_is_the_gp1_scheme_draw_for_draw(seed):
    cfg = Config(**SMALL)  # dedup off, no immigrants
    random.seed(9)
    texts = evo.initial_population(cfg)
    texts = texts + texts[:3]  # copies, which gp-1 kept
    fitness = {t: (float(len(t) % 7), 0.0) for t in texts}
    sizes = {t: gp.size(gp.individual_from_text(t)) for t in texts}
    random.seed(seed)
    a = evo.breed(texts, fitness, sizes, texts[:2], cfg)
    state_a = random.getstate()
    random.seed(seed)
    b = _breed_gp1(texts, fitness, sizes, texts[:2], cfg)
    assert a == b and random.getstate() == state_a


# --- whole generations -------------------------------------------------------------------------------------------

def test_one_behaviour_means_one_racing_entry_and_immigrants(fake, tmp_path):  # noqa: F811
    # every text plays the same games: one behaviour, so the racing top, elites and validation shrink to it
    fake["game"] = lambda text, seed, cap_s: {"trips": 100 + seed % 7, "seconds": 400.0, "commands": 5,
                                              "tiles_built": 10}
    cfg = small2(max_gens=1, min_gens=5)
    run(tmp_path, "same", cfg)
    g = read_jsonl(tmp_path / "same" / evo.GENERATIONS)[0]
    assert g["behaviours"] == 1
    assert g["immigrants"] == min(cfg.immigrants, g["distinct"] - 1, cfg.pop - 1 - 1)
    assert len(g["validated_all"]) == 1
    s8 = set(g["seeds"]["s8"])
    assert len({t for t, s in fake["plays"] if s in s8}) == 1  # copies never play the second round
    nxt = read_checkpoint(tmp_path / "same")["population"]
    assert len(nxt) == cfg.pop and len(set(nxt)) == cfg.pop


def test_three_behaviours_are_validated_each_with_its_paired_test(fake, tmp_path):  # noqa: F811
    run(tmp_path, "mixed", small2(max_gens=3, min_gens=5))
    gens = read_jsonl(tmp_path / "mixed" / evo.GENERATIONS)
    assert all(len(r["validated_all"]) == 3 for r in gens)
    assert all(v["counts"] and v["t"] is None for v in gens[0]["validated_all"])  # no anchor yet
    assert all(v["gain"] is not None and v["t_crit"] is not None for r in gens[1:] for v in r["validated_all"])
    best = max(gens[0]["validated_all"], key=lambda v: v["mean"])
    assert gens[0]["validated"]["mean"] == best["mean"] == gens[0]["anchor"]
    vals = read_jsonl(tmp_path / "mixed" / evo.VALIDATION)
    assert len(vals) == sum(v["new"] for r in gens for v in r["validated_all"])
    assert len({v["hash"] for v in vals}) == len(vals)  # a text is validated once
    assert all(len(v["trips"]) == 3 for v in vals)
    # each later candidate counts exactly when it clears the margin over the previous anchor and the paired test
    for prev, r in zip(gens, gens[1:]):
        margin = max(3.0, 0.02 * prev["anchor"])
        for v in r["validated_all"]:
            t = v["t"] if v["t"] is not None else (float("inf") if v["gain"] > 0 else float("-inf"))
            assert v["counts"] == (v["gain"] >= margin and v["gain"] > 0 and t >= v["t_crit"])
        assert r["improved"] == any(v["counts"] for v in r["validated_all"])


def clustered(text: str, seed: int, cap_s: float) -> dict:
    """Texts fall into 5 behaviours (by hash), so de-duplication and immigrants are exercised every generation."""
    k = int.from_bytes(text.encode("utf-8")[-4:], "little") % 5
    trips = 50 + 30 * k + (seed * (k + 1)) % 17
    return {"trips": trips, "seconds": 300.0 + trips, "commands": 10 + k, "tiles_built": 5 + k}


@pytest.mark.parametrize("game, kill_at", [("synthetic", 5), ("clustered", 5), ("clustered", 7)])
def test_a_gp2_run_resumed_after_a_kill_matches_an_uninterrupted_run(fake, tmp_path, game, kill_at):  # noqa: F811
    fake["game"] = synthetic if game == "synthetic" else clustered
    cfg = small2(min_gens=50, max_gens=4)
    run(tmp_path, "full", cfg)
    if game == "clustered":
        recs = read_jsonl(tmp_path / "full" / evo.GENERATIONS)
        assert all(r["behaviours"] < r["distinct"] and r["immigrants"] > 0 for r in recs)
    keys = DETERMINISTIC + ("behaviours", "immigrants", "validated_all")
    full = [{k: r[k] for k in keys} for r in read_jsonl(tmp_path / "full" / evo.GENERATIONS)]

    class Killed(BaseException):
        pass

    class Dying:
        def __init__(self, inner):
            self.inner, self.calls = inner, 0

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def play(self, jobs):
            self.calls += 1
            if self.calls == kill_at:  # inside generation 1 (round 1, round 2 or validation)
                raise Killed()
            return self.inner.play(jobs)

    inner = Engine(workers=2, cache_path=tmp_path / "kill" / evo.CACHE)
    with pytest.raises(Killed):
        run(tmp_path, "kill", cfg, engine=Dying(inner))
    inner.close()
    run(tmp_path, "kill", resume=True)
    again = [{k: r[k] for k in keys} for r in read_jsonl(tmp_path / "kill" / evo.GENERATIONS)]
    assert again == full
    a, b = read_checkpoint(tmp_path / "full"), read_checkpoint(tmp_path / "kill")
    for k in ("generation", "population", "rng", "convergence", "validated"):
        assert a[k] == b[k]


# --- configuration, format, CLI ----------------------------------------------------------------------------------

def test_gp2_defaults_and_checks():
    d = Config()
    assert (d.n_s4, d.n_s8, d.racing_top, d.validate_top, d.dedup, d.immigrants, d.sig_alpha) == \
        (8, 24, 16, 3, True, 8, 0.005)
    d.check()
    for bad in [dict(validate_top=0), dict(validate_top=17), dict(immigrants=-1), dict(sig_alpha=0.5),
                dict(sig_alpha=-0.1), dict(dedup=1)]:
        with pytest.raises(ValueError):
            Config(**bad).check()


def test_a_format_1_checkpoint_is_refused_with_a_hint(tmp_path):
    (tmp_path / evo.CHECKPOINT).write_bytes(pickle.dumps({"format": 1}))
    with pytest.raises(ValueError, match="49c8197"):
        read_checkpoint(tmp_path)


def test_cli_gp2_options(fake, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setattr(evo, "EVOLVE_DIR", tmp_path)
    monkeypatch.setattr(evo, "_make_engine", lambda cfg, run_dir: Engine(workers=2, cache_path=run_dir / evo.CACHE))
    assert evo.main(["--run", "c", "--pop", "8", "--first-seeds", "2", "--more-seeds", "2", "--racing-top", "4",
                     "--validate-top", "2", "--immigrants", "1", "--sig-alpha", "0", "--no-dedup",
                     "--validation", "1500-1502", "--max-gens", "1", "--workers", "2"]) == 0
    p = json.loads((tmp_path / "c" / evo.CONFIG).read_text())["params"]
    assert (p["n_s4"], p["n_s8"], p["racing_top"], p["validate_top"], p["immigrants"], p["sig_alpha"], p["dedup"]) \
        == (2, 2, 4, 2, 1, 0.0, False)
