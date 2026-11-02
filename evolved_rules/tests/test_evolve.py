"""Evolution loop (Phase 2 Task 5): stop rule, budget, selection, elitism, files, resume and a real tiny run."""
from __future__ import annotations

import hashlib
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from evolved_rules import engine as en
from evolved_rules import evolve as evo
from evolved_rules import gp
from evolved_rules.engine import Engine
from evolved_rules.evolve import Config, Convergence, read_checkpoint, read_jsonl, stop_reason


def _h(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16)


def synthetic(text: str, seed: int, cap_s: float) -> dict:
    """A deterministic fake game: a per-text quality plus per-(text, seed) noise."""
    trips = _h(text) % 200 + _h(f"{text}|{seed}") % 40
    return {"trips": trips, "seconds": 300.0 + trips, "commands": 10 + trips, "tiles_built": 5 + trips // 3,
            "trips_per_tile": 0.0, "scenario_seed": seed}


@pytest.fixture
def fake(monkeypatch):
    """The real Engine (cache included) with in-process worker slots and a synthetic game."""
    log = {"plays": [], "game": synthetic}
    lock = threading.Lock()

    def job(text, seed, cap_s):
        with lock:
            log["plays"].append((text, seed))
        return log["game"](text, seed, cap_s)

    monkeypatch.setattr(en, "_make_worker", lambda: ThreadPoolExecutor(max_workers=1))
    monkeypatch.setattr(en, "_play_job", job)
    return log


SMALL = dict(pop=8, n_s4=2, n_s8=2, racing_top=4, elites=2, validation=(1500, 1501, 1502), workers=2, seed=7)


def small(**kw) -> Config:
    return Config(**{**SMALL, **kw})


def run(tmp_path, name, cfg=None, resume=False, overrides=None, engine=None, **kw):
    run_dir = tmp_path / name
    eng = engine or Engine(workers=2, cap_s=(cfg.cap_s if cfg else 3600.0), cache_path=run_dir / evo.CACHE)
    try:
        return evo.evolve(cfg, run_dir, resume=resume, overrides=overrides, engine=eng, log=lambda s: None, **kw)
    finally:
        if engine is None:
            eng.close()


DETERMINISTIC = ("gen", "seeds", "distinct", "s4", "best", "elites", "validated", "improved", "incumbent", "anchor",
                 "required_gain", "gens_since_improvement")


def det(records):
    return [{k: r[k] for k in DETERMINISTIC} for r in records]


# --- the stop rule ---------------------------------------------------------------------------------------------

def conv(min_gens=5, patience=3, frac=0.02, trips=3.0) -> Convergence:
    return Convergence(min_gens, patience, frac, trips)


def test_required_gain_is_the_larger_of_trips_and_fraction_of_the_anchor():
    c = conv()
    c.observe(0, "a", 250.0, 600.0, 5)
    assert c.required_gain() == pytest.approx(5.0)
    assert not c.observe(1, "b", 254.99, 600.0, 5)
    assert c.observe(2, "c", 255.0, 600.0, 5) and c.anchor == 255.0 and c.since == 0
    c = conv()
    c.observe(0, "a", 100.0, 600.0, 5)
    assert c.required_gain() == 3.0
    assert not c.observe(1, "b", 102.9, 600.0, 5)
    assert c.observe(2, "c", 103.0, 600.0, 5)


def test_converges_exactly_after_min_gens_and_patience():
    c = conv(min_gens=5, patience=3)
    flags = []
    for g in range(6):
        c.observe(g, "same", 100.0, 500.0, 3)
        flags.append(c.converged())
    # since after gen g is g; converged needs 5 observations and since >= 3: first at the 5th observation
    assert flags == [False, False, False, False, True, True]


def test_patience_counts_from_the_last_counted_improvement():
    c = conv(min_gens=3, patience=4)
    means = [100, 101, 110, 111, 112, 112.5, 112.9, 112.0]
    flags = []
    for g, m in enumerate(means):
        c.observe(g, f"t{g}", float(m), 500.0, 3)
        flags.append(c.converged())
    # improvements at gen 0 and 2 (110 >= 103); later means stay under 110 + 3; since reaches 4 at gen 6
    assert flags == [False, False, False, False, False, False, True, True]
    assert c.incumbent["text"] == "t6" and c.anchor == 110.0


def test_slow_creep_adds_up_to_an_improvement():
    c = conv(min_gens=1, patience=10)
    for g, m in enumerate([250.0, 252.0, 254.0, 256.0]):
        improved = c.observe(g, f"t{g}", m, 500.0, 3)
    assert improved and c.anchor == 256.0 and c.since == 0  # 256 >= 250 + 5, though each step was 2


def test_with_zero_minimum_gains_only_a_strictly_higher_mean_counts():
    c = conv(min_gens=1, patience=2, frac=0.0, trips=0.0)
    assert c.observe(0, "a", 100.0, 500.0, 3)
    assert not c.observe(1, "a", 100.0, 500.0, 3)  # the anchor's own text, re-validated from the cache
    assert not c.observe(2, "a", 100.0, 500.0, 3) and c.converged()
    assert c.observe(3, "b", 100.5, 500.0, 3) and c.since == 0


def test_incumbent_ties_prefer_longer_games_then_smaller_trees_then_the_first():
    c = conv()
    c.observe(0, "a", 100.0, 500.0, 9)
    c.observe(1, "b", 100.0, 600.0, 9)
    assert c.incumbent["text"] == "b"
    c.observe(2, "c", 100.0, 600.0, 4)
    assert c.incumbent["text"] == "c"
    c.observe(3, "d", 100.0, 600.0, 4)
    assert c.incumbent["text"] == "c" and c.incumbent["gen"] == 2


def test_state_round_trip():
    c = conv()
    c.observe(0, "a", 100.0, 500.0, 9)
    assert Convergence.from_state(json.loads(json.dumps(c.state()))) == c


def test_stop_reason_converged_wins_over_budget_and_budget_is_never_converged():
    cfg = Config(min_gens=2, patience=1, max_gens=2, max_hours=1.0)
    c = Convergence(2, 1, 0.02, 3.0)
    c.observe(0, "a", 100.0, 500.0, 3)
    assert stop_reason(cfg, c, 1, 0.0) is None
    c.observe(1, "a", 100.0, 500.0, 3)
    assert stop_reason(cfg, c, 2, 99999.0)[0] == "converged"
    c2 = Convergence(2, 1, 0.02, 3.0)
    c2.observe(0, "a", 100.0, 500.0, 3)
    c2.observe(1, "b", 200.0, 500.0, 3)  # an improvement: not converged
    assert stop_reason(cfg, c2, 2, 0.0)[0] == "budget"
    assert stop_reason(Config(max_gens=50, max_hours=1.0), c2, 2, 3600.0)[0] == "budget"
    assert stop_reason(Config(max_gens=50, max_hours=1.0), c2, 2, 3599.0) is None


# --- selection ------------------------------------------------------------------------------------------------

def test_rank_breaks_ties_by_size_then_first_appearance():
    score = {"a": (10.0, 1.0), "b": (10.0, 1.0), "c": (10.0, 1.0), "d": (12.0, 0.0)}
    sizes = {"a": 5, "b": 3, "c": 3, "d": 50}
    assert evo.rank(["a", "b", "c", "a", "d"], score, sizes) == ["d", "b", "c", "a"]


def test_tournament_parsimony_tie_break(monkeypatch):
    fitness = {"big": (10.0, 1.0), "small": (10.0, 1.0), "small2": (10.0, 1.0), "bad": (9.0, 9.0)}
    sizes = {"big": 9, "small": 3, "small2": 3, "bad": 1}
    draws = iter(["big", "bad", "small", "small2"])
    monkeypatch.setattr(evo.random, "choice", lambda seq: next(draws))
    assert evo.tournament(list(fitness), fitness, sizes, 4) == "small"  # smaller wins, first of equals


def test_tournament_fitness_is_lexicographic(monkeypatch):
    fitness = {"x": (10.0, 100.0), "y": (10.0, 900.0), "z": (11.0, 0.0)}
    sizes = {"x": 1, "y": 99, "z": 99}
    draws = iter(["x", "y"])
    monkeypatch.setattr(evo.random, "choice", lambda seq: next(draws))
    assert evo.tournament(list(fitness), fitness, sizes, 2) == "y"  # seconds before size


def test_breed_keeps_elites_first_and_unchanged():
    random.seed(3)
    cfg = small(pop=12, elites=3)
    pop = evo.initial_population(cfg)
    sizes = {t: gp.size(gp.individual_from_text(t)) for t in pop}
    fitness = {t: (float(i), 0.0) for i, t in enumerate(pop)}
    elites = [pop[5], pop[2], pop[0]]
    nxt = evo.breed(pop, fitness, sizes, elites, cfg)
    assert len(nxt) == 12 and nxt[:3] == elites
    for t in nxt:
        ind = gp.individual_from_text(t)
        assert gp.individual_text(ind) == t and max(tree.height for tree in ind) <= gp.MAX_DEPTH


def test_initial_population_is_seeded_with_the_phase1_rules():
    random.seed(1)
    pop = evo.initial_population(Config())
    assert len(pop) == 64 and pop[0] == gp.HAND_TEXT and pop[1] == gp.SEPARATED_TEXT


def test_config_checks():
    Config().check()
    for bad in [dict(pop=1), dict(elites=0), dict(elites=64), dict(patience=0), dict(max_hours=0),
                dict(validation=(5,)), dict(validation=(1500, 1500)), dict(n_s4=0), dict(cxpb=1.5),
                dict(cap_s=0.0), dict(pop=2.5), dict(elites=5, racing_top=4)]:
        with pytest.raises(ValueError):
            Config(**bad).check()


def test_parse_validation():
    assert evo.parse_validation("1500-1502") == (1500, 1501, 1502)
    assert evo.parse_validation("1500-1501, 1600") == (1500, 1501, 1600)


# --- the loop on a fake engine --------------------------------------------------------------------------------

def test_run_folder_records_and_budget_stop(fake, tmp_path):
    cfg = small(min_gens=50, max_gens=4)
    status = run(tmp_path, "a", cfg)
    d = tmp_path / "a"
    assert status["status"] == "budget" and status["generations"] == 4
    assert json.loads((d / evo.STATUS).read_text())["status"] == "budget"
    config = json.loads((d / evo.CONFIG).read_text())
    assert config["params"]["pop"] == 8 and config["code_version"] == en.CODE_VERSION
    assert {"commit", "dirty", "packages", "python"} <= set(config)
    gens = read_jsonl(d / evo.GENERATIONS)
    assert [g["gen"] for g in gens] == [0, 1, 2, 3]
    for g in gens:
        assert len(g["seeds"]["s4"]) == 2 and len(g["seeds"]["s8"]) == 2
        assert all(1 <= s <= 999 for s in g["seeds"]["s4"] + g["seeds"]["s8"])
        assert {"best", "mean", "median"} <= set(g["s4"])
        assert g["wall_s"] >= 0 and g["games_played"] >= 0 and g["cache_hits"] >= 0
    vals = read_jsonl(d / evo.VALIDATION)
    assert len(vals) == sum(g["validated"]["new"] for g in gens)
    assert all(v["seeds"] == [1500, 1501, 1502] and len(v["trips"]) == 3 for v in vals)
    best = max(vals, key=lambda v: (v["mean"], v["mean_seconds"], -v["size"]))
    assert (d / evo.BEST).read_text().strip() == best["text"]
    assert gens[-1]["incumbent"]["hash"] == best["hash"]
    ckpt = read_checkpoint(d)
    assert ckpt["generation"] == 4 and len(ckpt["population"]) == 8


def test_every_individual_plays_s4_and_the_racing_top_plays_s8(fake, tmp_path):
    cfg = small(min_gens=50, max_gens=1, racing_top=3)
    run(tmp_path, "a", cfg)
    gen = read_jsonl(tmp_path / "a" / evo.GENERATIONS)[0]
    s4, s8 = set(gen["seeds"]["s4"]), set(gen["seeds"]["s8"])
    texts4 = {t for t, s in fake["plays"] if s in s4}
    texts8 = {t for t, s in fake["plays"] if s in s8}
    assert len(texts4) == gen["distinct"] and len(texts8) == 3 and texts8 <= texts4


def _independent_rank(texts, games_of, sizes):
    """Distinct texts best first by (mean trips, mean seconds), then smaller size, then first appearance."""
    def key(i_t):
        i, t = i_t
        g = games_of(t)
        return (-sum(x["trips"] for x in g) / len(g), -sum(x["seconds"] for x in g) / len(g), sizes[t], i)

    return [t for _, t in sorted(enumerate(dict.fromkeys(texts)), key=key)]


def test_racing_plays_the_s4_top_and_ranks_elites_and_best_by_all_12_games(fake, tmp_path):
    """S4 and S8 rank the individuals differently, so each selection step must use the right score."""
    cfg = small(pop=12, racing_top=5, elites=3, n_s4=4, n_s8=8, min_gens=50, max_gens=1, seed=11)
    run(tmp_path, "probe", cfg)
    seeds = read_jsonl(tmp_path / "probe" / evo.GENERATIONS)[0]["seeds"]  # gen 0's draw does not depend on fitness
    s4, s8 = set(seeds["s4"]), set(seeds["s8"])

    def game(text, seed, cap_s):
        if seed in s4:
            trips = _h(f"A|{text}") % 200
        elif seed in s8:
            trips = _h(f"B|{text}") % 200 + _h(f"{text}|{seed}") % 7
        else:
            trips = _h(f"V|{text}") % 100
        return {"trips": trips, "seconds": 300.0 + trips, "commands": 5, "tiles_built": 4}

    fake["game"] = game
    fake["plays"].clear()
    run(tmp_path, "a", cfg)
    g = read_jsonl(tmp_path / "a" / evo.GENERATIONS)[0]
    assert g["seeds"] == seeds
    random.seed(cfg.seed)
    population = evo.initial_population(cfg)
    sizes = {t: gp.size(gp.individual_from_text(t)) for t in population}
    played = {}
    for t, sd in fake["plays"]:
        played.setdefault(t, set()).add(sd)

    def games4(t):
        return [game(t, sd, 0) for sd in seeds["s4"]]

    def games8(t):
        return [game(t, sd, 0) for sd in seeds["s8"]]

    def games12(t):
        return games4(t) + games8(t)

    by_s4 = _independent_rank(population, games4, sizes)
    top = by_s4[:cfg.racing_top]
    # (a) exactly the S4 top plays S8
    assert {t for t, sds in played.items() if sds & s8} == set(top)
    by_12 = _independent_rank(top, games12, sizes)
    # the scores really disagree, so the assertions below can tell the selection rules apart
    assert by_12[:cfg.elites] != by_s4[:cfg.elites] and by_12[0] != by_s4[0]
    assert by_12[:cfg.elites] != _independent_rank(top, games8, sizes)[:cfg.elites]
    assert set(top) != set(list(dict.fromkeys(population))[:cfg.racing_top])
    # (b) elites and the validated best are the top by the 12-game mean
    assert g["elites"] == [evo.text_hash(t) for t in by_12[:cfg.elites]]
    assert g["best"]["hash"] == g["validated"]["hash"] == evo.text_hash(by_12[0])
    assert read_jsonl(tmp_path / "a" / evo.VALIDATION)[0]["text"] == by_12[0]
    # (c) the racing mean is over the 4 + 8 games
    assert g["best"]["racing_mean"] == pytest.approx(sum(x["trips"] for x in games12(by_12[0])) / 12)
    assert g["best"]["s4_mean"] == pytest.approx(sum(x["trips"] for x in games4(by_12[0])) / 4)
    assert [evo.text_hash(t) for t in read_checkpoint(tmp_path / "a")["population"][:3]] == g["elites"]


def test_stop_rule_triggers_exactly_when_specified(fake, tmp_path):
    cfg = small(min_gens=4, patience=3, max_gens=60)
    status = run(tmp_path, "a", cfg)
    gens = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
    # independent re-derivation of the rule from the recorded validated means
    anchor, since, stop_at = None, 0, None
    for i, g in enumerate(gens):
        m = g["validated"]["mean"]
        if anchor is None or m >= anchor + max(3.0, 0.02 * anchor):
            anchor, since = m, 0
        else:
            since += 1
        assert g["gens_since_improvement"] == since and g["anchor"] == anchor
        if i + 1 >= 4 and since >= 3:
            stop_at = i + 1
            break
    assert status["status"] == "converged" and stop_at == len(gens) == status["generations"]


def test_constant_fitness_converges_at_min_gens(fake, tmp_path):
    fake["game"] = lambda text, seed, cap_s: {"trips": 100, "seconds": 500.0, "tiles_built": 10, "commands": 5}
    status = run(tmp_path, "a", small(min_gens=6, patience=2, max_gens=60))
    assert status["status"] == "converged" and status["generations"] == 6
    gens = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
    assert [g["improved"] for g in gens] == [True] + [False] * 5


def test_a_text_is_validated_once(fake, tmp_path):
    """Constant fitness keeps the same best (the smallest tree, carried as an elite): validated only at gen 0."""
    fake["game"] = lambda text, seed, cap_s: {"trips": 100, "seconds": 500.0, "tiles_built": 10, "commands": 5}
    cfg = small(min_gens=50, max_gens=5)
    inner = Engine(workers=2, cache_path=tmp_path / "a" / evo.CACHE)
    eng = Logging(inner)
    run(tmp_path, "a", cfg, engine=eng)
    inner.close()
    gens = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
    assert len({g["validated"]["hash"] for g in gens}) == 1
    assert [g["validated"]["new"] for g in gens] == [True, False, False, False, False]
    vals = read_jsonl(tmp_path / "a" / evo.VALIDATION)
    assert len(vals) == 1 and vals[0]["hash"] == gens[0]["validated"]["hash"]
    asked = [s for b in eng.batches for _, s in b if s in cfg.validation]
    assert len(asked) == len(cfg.validation)  # validation games are never requested again, not even from the cache


def test_validation_records_match_the_new_flags(fake, tmp_path):
    run(tmp_path, "a", small(min_gens=50, max_gens=8))
    gens = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
    seen, expected = [], []
    for g in gens:
        h = g["validated"]["hash"]
        assert g["validated"]["new"] == (h not in seen)
        if h not in seen:
            seen.append(h)
            expected.append((g["gen"], h))
    vals = read_jsonl(tmp_path / "a" / evo.VALIDATION)
    assert [(v["gen"], v["hash"]) for v in vals] == expected
    assert any(not g["validated"]["new"] for g in gens)  # the synthetic run does repeat a best (elitism)


def test_wall_clock_budget(fake, tmp_path):
    ticks = iter(range(0, 10**6, 1000))
    status = run(tmp_path, "a", small(min_gens=50, max_hours=0.5), clock=lambda: next(ticks))
    assert status["status"] == "budget" and "wall clock" in status["reason"] and status["generations"] == 2


class Logging:
    """An engine wrapper that keeps every play() batch."""

    def __init__(self, inner):
        self.inner, self.batches = inner, []

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def play(self, jobs):
        self.batches.append(list(jobs))
        return self.inner.play(jobs)


def test_elites_are_carried_unchanged_and_rescored_on_new_seeds(fake, tmp_path):
    cfg = small(min_gens=50, max_gens=4, elites=3)
    inner = Engine(workers=2, cache_path=tmp_path / "a" / evo.CACHE)
    eng = Logging(inner)
    run(tmp_path, "a", cfg, engine=eng)
    inner.close()
    gens = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
    s4_batches = [b for b in eng.batches if b and b[0][1] in gens[0]["seeds"]["s4"]][:1]
    for g in gens[1:]:
        s4_batches += [b for b in eng.batches if b and {s for _, s in b} == set(g["seeds"]["s4"])][:1]
    assert len(s4_batches) == 4
    for g, batch in zip(gens, s4_batches[1:]):
        opening = list(dict.fromkeys(t for t, _ in batch))[:3]  # the next population opens with the elites
        assert [evo.text_hash(t) for t in opening] == g["elites"]
    ckpt = read_checkpoint(tmp_path / "a")
    assert [evo.text_hash(t) for t in ckpt["population"][:3]] == gens[-1]["elites"]


def test_resume_after_a_kill_mid_generation_matches_an_uninterrupted_run(fake, tmp_path):
    cfg = small(min_gens=50, max_gens=5)
    run(tmp_path, "full", cfg)
    full = det(read_jsonl(tmp_path / "full" / evo.GENERATIONS))

    class Killed(BaseException):
        pass

    class Dying:
        """An engine that dies at its 8th play call (generation 2's S8 batch)."""

        def __init__(self, inner):
            self.inner, self.calls = inner, 0

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def play(self, jobs):
            self.calls += 1
            if self.calls == 8:
                raise Killed()
            return self.inner.play(jobs)

    inner = Engine(workers=2, cache_path=tmp_path / "kill" / evo.CACHE)
    with pytest.raises(Killed):
        run(tmp_path, "kill", cfg, engine=Dying(inner))
    inner.close()
    partial = read_jsonl(tmp_path / "kill" / evo.GENERATIONS)
    assert 1 <= len(partial) < 5
    status = run(tmp_path, "kill", resume=True)
    assert status["status"] == "budget"
    assert det(read_jsonl(tmp_path / "kill" / evo.GENERATIONS)) == full
    va = [{k: v for k, v in r.items()} for r in read_jsonl(tmp_path / "full" / evo.VALIDATION)]
    assert read_jsonl(tmp_path / "kill" / evo.VALIDATION) == va
    assert (tmp_path / "kill" / evo.BEST).read_text() == (tmp_path / "full" / evo.BEST).read_text()
    a, b = read_checkpoint(tmp_path / "full"), read_checkpoint(tmp_path / "kill")
    for k in ("generation", "population", "rng", "convergence", "validated"):
        assert a[k] == b[k]


def test_resume_after_a_kill_between_records_and_checkpoint(fake, tmp_path, monkeypatch):
    cfg = small(min_gens=50, max_gens=5)
    run(tmp_path, "full", cfg)
    full_records = read_jsonl(tmp_path / "full" / evo.GENERATIONS)
    full = det(full_records)
    # Kill right after the records of the first later generation that validated a new text: its validation
    # record is then orphaned (written, not checkpointed) and must be dropped on resume, not duplicated.
    k = next(g["gen"] for g in full_records[1:] if g["validated"]["new"])
    assert k < 4
    real = evo.write_checkpoint
    calls = {"n": 0}

    def dying(run_dir, state):
        calls["n"] += 1
        if calls["n"] == k + 2:  # call 1 = start, call n = after gen n - 2: gen k's records are already written
            raise KeyboardInterrupt
        real(run_dir, state)

    monkeypatch.setattr(evo, "write_checkpoint", dying)
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, "kill", cfg)
    assert json.loads((tmp_path / "kill" / evo.STATUS).read_text())["status"] == "interrupted"
    assert len(read_jsonl(tmp_path / "kill" / evo.GENERATIONS)) == k + 1  # gen k recorded, not checkpointed
    assert read_jsonl(tmp_path / "kill" / evo.VALIDATION)[-1]["gen"] == k  # and its validation record
    monkeypatch.setattr(evo, "write_checkpoint", real)
    before = len(fake["plays"])
    run(tmp_path, "kill", resume=True)
    assert det(read_jsonl(tmp_path / "kill" / evo.GENERATIONS)) == full
    assert read_jsonl(tmp_path / "kill" / evo.VALIDATION) == read_jsonl(tmp_path / "full" / evo.VALIDATION)
    assert (tmp_path / "kill" / evo.BEST).read_text() == (tmp_path / "full" / evo.BEST).read_text()
    a, b = read_checkpoint(tmp_path / "full"), read_checkpoint(tmp_path / "kill")
    for key in ("generation", "population", "rng", "convergence", "validated"):
        assert a[key] == b[key]
    # generation k replays nothing: every game it needs is in the cache
    gens = read_jsonl(tmp_path / "kill" / evo.GENERATIONS)
    assert gens[k]["games_played"] == 0 and gens[k]["cache_hits"] > 0
    assert len(fake["plays"]) > before  # later generations still play


def test_resume_can_extend_the_budget_but_not_change_the_run(fake, tmp_path):
    run(tmp_path, "a", small(min_gens=50, max_gens=2))
    with pytest.raises(ValueError, match="pop"):
        run(tmp_path, "a", resume=True, overrides={"pop": 16})
    status = run(tmp_path, "a", resume=True, overrides={"max_gens": 3, "pop": 8, "workers": 3})
    assert status["status"] == "budget" and status["generations"] == 3
    config = json.loads((tmp_path / "a" / evo.CONFIG).read_text())
    assert config["params"]["max_gens"] == 3 and config["params"]["workers"] == 3
    assert config["resumes"][-1]["changed"] == {"max_gens": 3, "workers": 3}


def test_a_converged_run_resumes_to_its_status(fake, tmp_path):
    fake["game"] = lambda text, seed, cap_s: {"trips": 100, "seconds": 500.0}
    run(tmp_path, "a", small(min_gens=3, patience=2))
    n = len(fake["plays"])
    status = run(tmp_path, "a", resume=True)
    assert status["status"] == "converged" and len(fake["plays"]) == n


def test_a_fresh_run_never_overwrites(fake, tmp_path):
    run(tmp_path, "a", small(max_gens=1))
    with pytest.raises(evo.RunExistsError):
        run(tmp_path, "a", small(max_gens=1))
    with pytest.raises(FileNotFoundError):
        run(tmp_path, "nothing-here", resume=True)


def test_a_kill_during_start_leaves_a_folder_a_fresh_start_reuses(fake, tmp_path, monkeypatch):
    real = evo.write_checkpoint

    def dying(run_dir, state):
        raise KeyboardInterrupt

    monkeypatch.setattr(evo, "write_checkpoint", dying)
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, "a", small(max_gens=1))
    assert (tmp_path / "a" / evo.CONFIG).exists() and not (tmp_path / "a" / evo.CHECKPOINT).exists()
    monkeypatch.setattr(evo, "write_checkpoint", real)
    with pytest.raises(FileNotFoundError):
        run(tmp_path, "a", resume=True)
    assert run(tmp_path, "a", small(max_gens=1))["status"] == "budget"
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "notes.txt").write_text("not a run")
    with pytest.raises(evo.RunExistsError):
        run(tmp_path, "b", small(max_gens=1))


def test_failure_marks_the_status(fake, tmp_path):
    def broken(text, seed, cap_s):
        raise RuntimeError("host fell over")

    fake["game"] = broken
    with pytest.raises(en.EngineError):
        run(tmp_path, "a", small(max_gens=1))
    status = json.loads((tmp_path / "a" / evo.STATUS).read_text())
    assert status["status"] == "failed" and "EngineError" in status["reason"]
    assert (tmp_path / "a" / "error.txt").exists()
    fake["game"] = synthetic
    assert run(tmp_path, "a", resume=True)["status"] == "budget"
    assert not (tmp_path / "a" / "error.txt").exists()


def test_cli(fake, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evo, "EVOLVE_DIR", tmp_path)
    args = ["--run", "cli", "--pop", "6", "--min-gens", "40", "--max-gens", "2", "--validation", "1500-1501",
            "--workers", "2", "--seed", "5"]
    assert evo.main(args) == 0
    assert "budget after 2 generations" in capsys.readouterr().out
    assert evo.main(args) == evo.EXISTING_RUN_EXIT_CODE
    assert evo.main(["--run", "cli", "--resume", "--max-gens", "3"]) == 0
    assert len(read_jsonl(tmp_path / "cli" / evo.GENERATIONS)) == 3
    assert evo.main(["--run", "cli", "--resume", "--pop", "9"]) == evo.EXISTING_RUN_EXIT_CODE
    with pytest.raises(SystemExit):
        evo.main(["--run", "../x"])
    with pytest.raises(SystemExit):
        evo.main(["--run", "bad", "--pop", "1"])


def test_cli_maps_only_resume_errors_to_exit_2(fake, tmp_path, monkeypatch, capsys):
    """An error inside a resumed run propagates with its traceback; it is not reported as 'cannot resume'."""
    monkeypatch.setattr(evo, "EVOLVE_DIR", tmp_path)
    assert evo.main(["--run", "r", "--pop", "6", "--max-gens", "1", "--validation", "1500", "--workers", "2"]) == 0
    assert evo.main(["--run", "missing", "--resume"]) == evo.EXISTING_RUN_EXIT_CODE
    assert "cannot resume" in capsys.readouterr().err

    def broken(*a, **kw):
        raise ValueError("mid-run failure")

    monkeypatch.setattr(evo, "run_loop", broken)
    with pytest.raises(ValueError, match="mid-run failure"):
        evo.main(["--run", "r", "--resume", "--max-gens", "2"])


# --- a real tiny run ------------------------------------------------------------------------------------------

@pytest.mark.host
def test_real_tiny_run(host_dll, tmp_path):
    cfg = Config(pop=3, n_s4=1, n_s8=1, racing_top=2, elites=1, validation=(1500,), max_gens=1, min_gens=5,
                 cap_s=150.0, workers=2, seed=3)
    status = evo.evolve(cfg, tmp_path / "real", log=lambda s: None)
    assert status["status"] == "budget"
    gen = read_jsonl(tmp_path / "real" / evo.GENERATIONS)[0]
    val = read_jsonl(tmp_path / "real" / evo.VALIDATION)[0]
    assert val["seeds"] == [1500] and val["seconds"][0] <= 150.0 + 1e-6
    assert gen["games_played"] >= 3
    gp.individual_from_text((tmp_path / "real" / evo.BEST).read_text())


def test_the_run_keeps_the_machine_awake_and_releases_it(fake, tmp_path, monkeypatch):
    from evolved_rules import power
    calls = []
    monkeypatch.setattr(power, "_api", lambda: (lambda flags: calls.append(flags) or 1))
    seen = []
    real_step = evo.generation

    def step(*a, **kw):
        seen.append(list(calls))
        return real_step(*a, **kw)

    monkeypatch.setattr(evo, "generation", step)
    run(tmp_path, "a", small(max_gens=2))
    assert seen == [[power.KEEP_AWAKE]] * 2  # held through every generation
    assert calls == [power.KEEP_AWAKE, power.ES_CONTINUOUS]
    fake["game"] = lambda text, seed, cap_s: (_ for _ in ()).throw(RuntimeError("host fell over"))
    calls.clear()
    with pytest.raises(en.EngineError):
        run(tmp_path, "b", small(max_gens=1))
    assert calls == [power.KEEP_AWAKE, power.ES_CONTINUOUS]  # released on a failure too
