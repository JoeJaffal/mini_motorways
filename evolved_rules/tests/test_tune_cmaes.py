"""CMA-ES control (Phase 2 Task 6): weight vector <-> text, the shared stop rule, the loop, resume, a real game."""
from __future__ import annotations

import math

import hashlib
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from evolved_rules.tests.helpers import TEST_SIM

from evolved_rules import engine as en
from evolved_rules import evolve as evo
from evolved_rules import gp
from evolved_rules import tune_cmaes as tc
from evolved_rules.agent import play_game
from evolved_rules.candidates import RouteCandidate
from evolved_rules.engine import Engine
from evolved_rules.evolve import read_checkpoint, read_jsonl
from evolved_rules.rules import HandRule, SeparatedPreference
from evolved_rules.tests.test_features import PHASE1_GAMES, SLOW
from evolved_rules.tests.test_gp import _cand, _merged, _state
from evolved_rules.tune_cmaes import CmaConfig


# --- weight vector <-> text ------------------------------------------------------------------------------------

def test_layout_covers_every_terminal_of_every_tree_in_order():
    assert tc.DIM == len(gp.PRIORITY_TERMS) + 1 + len(gp.HOLD_TERMS) + len(gp.UPGRADE_TERMS) == 81
    assert [t for i, t in tc.LAYOUT if i == 0] == list(gp.PRIORITY_TERMS)
    assert [t for i, t in tc.LAYOUT if i == 1] == [tc.BIAS, *gp.HOLD_TERMS]
    assert [t for i, t in tc.LAYOUT if i == 2] == list(gp.UPGRADE_TERMS)


def test_weight_vector_text_round_trip():
    rng = random.Random(4)
    for _ in range(100):
        w = [rng.uniform(-6.0, 6.0) for _ in range(tc.DIM)]
        text = tc.weights_to_text(w)
        assert en.canonical_text(text) == text  # the engine's cache key is the text itself
        assert tc.text_to_weights(text) == tc.snap(w)
        assert tc.weights_to_text(tc.text_to_weights(text)) == text
    for w in tc.X0.values():
        assert tc.text_to_weights(tc.weights_to_text(w)) == w


def test_linear_texts_are_valid_shallow_individuals_of_constant_size():
    for w in (tc.HAND_WEIGHTS, [4.99] * tc.DIM):
        ind = gp.individual_from_text(tc.weights_to_text(w))
        # balanced sums: about log2(terms) + 2 levels, not one level per term. The GP depth limit (MAX_DEPTH)
        # applies only to variation (mate/mutate), which a CMA-ES text never goes through.
        assert max(t.height for t in ind) <= math.ceil(math.log2(len(gp.PRIORITY_TERMS))) + 2
        assert gp.size(ind) == tc.SIZE


def test_snap_clips_rounds_and_never_writes_negative_zero():
    w = tc.snap([7.0, -9.0, 0.123456, -0.00001] + [0.0] * (tc.DIM - 4))
    assert w[:4] == (5.0, -5.0, 0.1235, 0.0) and str(w[3]) == "0.0"
    with pytest.raises(ValueError):
        tc.snap([0.0] * (tc.DIM - 1))
    with pytest.raises(ValueError):
        tc.snap([float("nan")] + [0.0] * (tc.DIM - 1))


def test_text_to_weights_rejects_texts_weights_to_text_would_not_write():
    good = tc.weights_to_text(tc.HAND_WEIGHTS)
    bad = [
        gp.HAND_TEXT,  # an individual, but not a linear one
        good.replace("mul(-1.0, tiles_needed)", "mul(-1.00001, tiles_needed)", 1),  # off the 4-decimal grid
        good.replace("mul(-1.0, tiles_needed)", "mul(-7.0, tiles_needed)", 1),  # out of bounds
        good.replace("mul(0.0, bridges_needed)", "mul(0.0, path_len)", 1),  # a terminal twice, one missing
        # no bias: the hold sum's first leaf is the bias constant, whatever the depth of the balanced sum
        good.replace("(0.0625, mul(-1.0, road_stock))", "(road_stock, mul(-1.0, road_stock))", 1),
    ]
    assert bad[4] != good
    for text in bad:
        with pytest.raises(ValueError):
            tc.text_to_weights(text)
    with pytest.raises(ValueError):
        tc.weights_from({"hold": {"tiles_needed": 1.0}})  # not a hold terminal


def test_weights_by_tree_names_every_weight():
    d = tc.weights_by_tree(tc.SEPARATED_WEIGHTS)
    assert list(d) == list(gp.TREE_NAMES)
    assert d["priority"]["is_separated"] == 5.0 and d["hold"][tc.BIAS] == 0.0625
    assert tc.weights_from(d) == tc.SEPARATED_WEIGHTS


def test_linear_phase1_vectors_score_like_the_phase1_rules():
    """The hand vector gives exactly HandRule / 64 (zero terms add exactly 0); separated orders the same."""
    state = _state()
    c, g, o = _merged(state)
    p, h = gp.TreePolicy(tc.weights_to_text(tc.HAND_WEIGHTS)), HandRule()
    assert p.priority(c) == h.priority(c) / 64
    assert p.hold(g) == h.hold(g) / 64
    assert p.upgrade(o) == h.upgrade(o) / 64
    s = gp.TreePolicy(tc.weights_to_text(tc.SEPARATED_WEIGHTS))
    sep = RouteCandidate(kind="separated", house_id=1, shop_ids=(2,), path=_cand().path, tiles_needed=3,
                         bridges_needed=0, turns=0, new_junctions=0, shared_cells=0, strokes=())
    cs, _, _ = _merged(state, sep)
    assert s.priority(cs) == -3 / 64 + 5.0 and s.priority(c) == h.priority(c) / 64
    assert SeparatedPreference().priority(cs) > SeparatedPreference().priority(c) and s.priority(cs) > s.priority(c)


LINEAR_GAMES = [g for g in PHASE1_GAMES if g[0] in ("hand", "separated")]


@pytest.mark.host
@pytest.mark.parametrize("name, seed, trips, commands, sha",
                         [g for g in LINEAR_GAMES if SLOW or (g[0], g[1]) == ("hand", 2000)])
def test_linear_phase1_vectors_play_the_phase1_games(host, name, seed, trips, commands, sha):
    """The default run plays hand on seed 2000; EVOLVED_RULES_SLOW=1 plays every hand and separated game."""
    w = tc.HAND_WEIGHTS if name == "hand" else tc.SEPARATED_WEIGHTS
    r = play_game(host, seed, gp.TreePolicy(tc.weights_to_text(w), coverage=False))
    digest = hashlib.sha256(json.dumps(r.recording["actions"], sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    assert (r.trips, r.commands, digest) == (trips, commands, sha)


# --- configuration and ranks ------------------------------------------------------------------------------------

def test_config_checks():
    CmaConfig().check()
    assert CmaConfig().validation == evo.Config().validation
    for name in ("min_gens", "patience", "min_gain_frac", "min_gain_trips", "sig_alpha", "max_hours", "max_gens",
                 "cap_s"):
        assert getattr(CmaConfig(), name) == getattr(evo.Config(), name)  # the same stop rule defaults
    for bad in [dict(popsize=1), dict(seed=0), dict(sigma0=0.0), dict(sigma0=6.0), dict(x0="best"),
                dict(n_train=0), dict(patience=0), dict(max_hours=0), dict(validation=(5,)),
                dict(validation=(1500, 1500)), dict(cap_s=0.0), dict(popsize=2.5)]:
        with pytest.raises(ValueError):
            CmaConfig(**bad).check()
    cfg = CmaConfig(popsize=8, validation=(1500, 1501))
    assert CmaConfig.from_json(json.loads(json.dumps(cfg.to_json()))) == cfg


def test_rank_values_are_lexicographic_with_shared_ties():
    fitness = {"a": (10.0, 100.0), "b": (10.0, 900.0), "c": (11.0, 0.0), "d": (10.0, 100.0)}
    assert tc.rank_values(["a", "b", "c", "d"], fitness) == [2.0, 1.0, 0.0, 2.0]


def test_the_stop_rule_is_evolves():
    assert tc.Convergence is evo.Convergence and tc.stop_reason is evo.stop_reason


# --- the loop on a fake engine ------------------------------------------------------------------------------------

def _h(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16)


def synthetic(text: str, seed: int, cap_s: float) -> dict:
    """A deterministic fake game: a per-text quality plus per-(text, seed) noise."""
    trips = _h(text) % 200 + _h(f"{text}|{seed}") % 40
    return {"trips": trips, "seconds": 300.0 + trips, "commands": 10 + trips, "tiles_built": 5 + trips // 3}


@pytest.fixture
def fake(monkeypatch):
    """The real Engine (cache included) with in-process worker slots and a synthetic game."""
    log = {"plays": [], "game": synthetic}
    lock = threading.Lock()

    def job(text, seed, cap_s):
        with lock:
            log["plays"].append((text, seed))
        return {**log["game"](text, seed, cap_s), "simulator_version": TEST_SIM}

    monkeypatch.setattr(en, "_make_worker", lambda: ThreadPoolExecutor(max_workers=1))
    monkeypatch.setattr(en, "_play_job", job)
    return log


# sig_alpha=0: these tests pin the mean-gain stop rule; the paired test is covered in test_evolve.py
SMALL = dict(popsize=6, n_train=2, validation=(1500, 1501, 1502), workers=2, seed=7, sig_alpha=0.0)


def small(**kw) -> CmaConfig:
    return CmaConfig(**{**SMALL, **kw})


def run(tmp_path, name, cfg=None, resume=False, overrides=None, engine=None, **kw):
    run_dir = tmp_path / name
    eng = engine or Engine(workers=2, cap_s=(cfg.cap_s if cfg else 3600.0), cache_path=run_dir / evo.CACHE)
    try:
        return tc.tune(cfg, run_dir, resume=resume, overrides=overrides, engine=eng, log=lambda s: None, **kw)
    finally:
        if engine is None:
            eng.close()


DETERMINISTIC = ("gen", "seeds", "distinct", "train", "best", "sigma", "cma_stop", "validated", "improved",
                 "incumbent", "anchor", "required_gain", "gens_since_improvement")


def det(records):
    return [{k: r[k] for k in DETERMINISTIC} for r in records]


def test_run_folder_records_and_budget_stop(fake, tmp_path):
    status = run(tmp_path, "a", small(min_gens=50, max_gens=3))
    d = tmp_path / "a"
    assert status["status"] == "budget" and status["generations"] == 3
    config = json.loads((d / evo.CONFIG).read_text())
    assert config["method"] == tc.METHOD and config["dim"] == tc.DIM and config["params"]["popsize"] == 6
    assert config["code_version"] == en.CODE_VERSION and {"commit", "dirty", "packages"} <= set(config)
    gens = read_jsonl(d / evo.GENERATIONS)
    assert [g["gen"] for g in gens] == [0, 1, 2]
    for g in gens:
        assert len(g["seeds"]) == 2 and all(1 <= s <= 999 for s in g["seeds"])
        assert g["distinct"] == 6 and g["sigma"] > 0 and isinstance(g["cma_stop"], list)
    vals = read_jsonl(d / evo.VALIDATION)
    best = max(vals, key=lambda v: (v["mean"], v["mean_seconds"], -v["size"]))
    assert (d / evo.BEST).read_text().strip() == best["text"]
    weights = json.loads((d / tc.WEIGHTS).read_text())
    assert tc.weights_from(weights) == tc.text_to_weights(best["text"])
    assert read_checkpoint(d)["generation"] == 3


def test_every_candidate_plays_the_same_training_seeds_and_the_best_is_validated(fake, tmp_path):
    cfg = small(min_gens=50, max_gens=1, n_train=3)
    run(tmp_path, "a", cfg)
    g = read_jsonl(tmp_path / "a" / evo.GENERATIONS)[0]
    train = [(t, s) for t, s in fake["plays"] if s not in cfg.validation]
    texts = list(dict.fromkeys(t for t, _ in train))
    assert len(texts) == cfg.popsize
    for t in texts:
        assert sorted(s for u, s in train if u == t) == sorted(g["seeds"])
    means = {t: (sum(synthetic(t, s, 0)["trips"] for s in g["seeds"]) / 3) for t in texts}
    top = max(texts, key=lambda t: means[t])
    assert g["best"]["hash"] == g["validated"]["hash"] == evo.text_hash(top)
    assert g["best"]["train_mean"] == pytest.approx(means[top])
    assert {s for t, s in fake["plays"] if t == top and s in cfg.validation} == set(cfg.validation)


def test_stop_rule_triggers_exactly_when_specified(fake, tmp_path):
    status = run(tmp_path, "a", small(min_gens=4, patience=3, max_gens=60))
    gens = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
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
    status = run(tmp_path, "a", small(min_gens=5, patience=2, max_gens=60))
    assert status["status"] == "converged" and status["generations"] == 5
    assert [g["improved"] for g in read_jsonl(tmp_path / "a" / evo.GENERATIONS)] == [True] + [False] * 4


def test_cma_climbs_a_synthetic_objective(fake, tmp_path):
    """Trips grow with one weight: the ranks told to CMA-ES must move its mean that way."""
    k = tc.LAYOUT.index((0, "shop_rate"))

    def game(text, seed, cap_s):
        trips = int(1000 + 100 * tc.text_to_weights(text)[k])
        return {"trips": trips, "seconds": 500.0, "tiles_built": 10, "commands": 5}

    fake["game"] = game
    cfg = small(popsize=8, n_train=1, validation=(1500,), min_gens=50, max_gens=12, x0="zero", sigma0=0.5)
    run(tmp_path, "a", cfg)
    es = __import__("pickle").loads(read_checkpoint(tmp_path / "a")["es"])
    assert es.mean[k] > 1.0
    gens = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
    assert gens[-1]["incumbent"]["mean"] > gens[0]["validated"]["mean"] + 100


def test_resume_after_a_kill_mid_generation_matches_an_uninterrupted_run(fake, tmp_path):
    cfg = small(min_gens=50, max_gens=5)
    run(tmp_path, "full", cfg)
    full = det(read_jsonl(tmp_path / "full" / evo.GENERATIONS))

    class Killed(BaseException):
        pass

    class Dying:
        """An engine that dies at its 5th play call (in generation 2 or 3)."""

        def __init__(self, inner):
            self.inner, self.calls = inner, 0

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def play(self, jobs):
            self.calls += 1
            if self.calls == 5:
                raise Killed()
            return self.inner.play(jobs)

    inner = Engine(workers=2, cache_path=tmp_path / "kill" / evo.CACHE)
    with pytest.raises(Killed):
        run(tmp_path, "kill", cfg, engine=Dying(inner))
    inner.close()
    assert 1 <= len(read_jsonl(tmp_path / "kill" / evo.GENERATIONS)) < 5
    assert run(tmp_path, "kill", resume=True)["status"] == "budget"
    assert det(read_jsonl(tmp_path / "kill" / evo.GENERATIONS)) == full
    assert read_jsonl(tmp_path / "kill" / evo.VALIDATION) == read_jsonl(tmp_path / "full" / evo.VALIDATION)
    assert (tmp_path / "kill" / evo.BEST).read_text() == (tmp_path / "full" / evo.BEST).read_text()
    a, b = read_checkpoint(tmp_path / "full"), read_checkpoint(tmp_path / "kill")
    for key in ("generation", "rng", "convergence", "validated"):
        assert a[key] == b[key]
    assert all(np.array_equal(x, y) for x, y in zip(a["np_rng"], b["np_rng"]))
    ea, eb = __import__("pickle").loads(a["es"]), __import__("pickle").loads(b["es"])
    assert np.array_equal(ea.mean, eb.mean) and ea.sigma == eb.sigma


def test_resume_can_extend_the_budget_but_not_change_the_run(fake, tmp_path):
    run(tmp_path, "a", small(min_gens=50, max_gens=2))
    with pytest.raises(ValueError, match="popsize"):
        run(tmp_path, "a", resume=True, overrides={"popsize": 16})
    status = run(tmp_path, "a", resume=True, overrides={"max_gens": 3, "workers": 3})
    assert status["status"] == "budget" and status["generations"] == 3


def test_a_gp_run_folder_is_not_resumed_as_cma(fake, tmp_path):
    evo.evolve(evo.Config(pop=4, n_s4=1, n_s8=1, racing_top=2, elites=1, validation=(1500,), max_gens=1,
                          workers=2, validate_top=1), tmp_path / "gp",
               engine=Engine(workers=2, cache_path=tmp_path / "gp" / evo.CACHE), log=lambda s: None)
    with pytest.raises(ValueError, match="not a cma-es run"):
        run(tmp_path, "gp", resume=True)
    with pytest.raises(evo.RunExistsError):
        run(tmp_path, "gp", small(max_gens=1))



def test_a_cma_run_folder_is_not_resumed_as_gp(fake, tmp_path):
    run(tmp_path, "cma", small(min_gens=50, max_gens=1))
    before = {name: (tmp_path / "cma" / name).read_bytes() for name in (evo.CONFIG, evo.STATUS)}
    with pytest.raises(ValueError, match="holds a cma-es run, not a GP run"):
        evo.evolve(None, tmp_path / "cma", resume=True, overrides={"max_gens": 2},
                   engine=Engine(workers=2, cache_path=tmp_path / "cma" / evo.CACHE), log=lambda s: None)
    assert {name: (tmp_path / "cma" / name).read_bytes() for name in before} == before  # folder untouched
    assert not (tmp_path / "cma" / "error.txt").exists()
    assert run(tmp_path, "cma", resume=True, overrides={"max_gens": 2})["generations"] == 2


def test_cli(fake, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tc, "CMAES_DIR", tmp_path)
    args = ["--run", "cli", "--popsize", "4", "--n-train", "1", "--min-gens", "40", "--max-gens", "2",
            "--validation", "1500-1501", "--workers", "2", "--seed", "5", "--x0", "hand"]
    assert tc.main(args) == 0
    assert "budget after 2 generations" in capsys.readouterr().out
    assert tc.main(args) == evo.EXISTING_RUN_EXIT_CODE
    assert tc.main(["--run", "cli", "--resume", "--max-gens", "3"]) == 0
    assert len(read_jsonl(tmp_path / "cli" / evo.GENERATIONS)) == 3
    assert tc.main(["--run", "cli", "--resume", "--popsize", "9"]) == evo.EXISTING_RUN_EXIT_CODE
    assert tc.main(["--run", "missing", "--resume"]) == evo.EXISTING_RUN_EXIT_CODE
    with pytest.raises(SystemExit):
        tc.main(["--run", "bad", "--seed", "0"])
    with pytest.raises(SystemExit):
        tc.main(["--run", "../x"])


# --- a real tiny run ------------------------------------------------------------------------------------------

@pytest.mark.host
def test_real_tiny_run(host_dll, tmp_path):
    cfg = CmaConfig(popsize=2, n_train=1, validation=(1500,), max_gens=1, min_gens=5, cap_s=150.0, workers=2,
                    seed=3)
    status = tc.tune(cfg, tmp_path / "real", log=lambda s: None)
    assert status["status"] == "budget"
    val = read_jsonl(tmp_path / "real" / evo.VALIDATION)[0]
    assert val["seeds"] == [1500] and val["seconds"][0] <= 150.0 + 1e-6
    tc.text_to_weights((tmp_path / "real" / evo.BEST).read_text())


def test_the_run_keeps_the_machine_awake_and_releases_it(fake, tmp_path, monkeypatch):
    from evolved_rules import power
    calls = []
    monkeypatch.setattr(power, "_api", lambda: (lambda flags: calls.append(flags) or 1))
    seen = []
    real_step = tc.generation

    def step(*a, **kw):
        seen.append(list(calls))
        return real_step(*a, **kw)

    monkeypatch.setattr(tc, "generation", step)
    run(tmp_path, "a", small(max_gens=2))
    assert seen == [[power.KEEP_AWAKE]] * 2
    assert calls == [power.KEEP_AWAKE, power.ES_CONTINUOUS]
