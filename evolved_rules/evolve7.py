"""cma-7: sep-CMA-ES over the gp-7 live coordinates (plan 2026-11-14 section 3.3; a fork of tune_cmaes).

  PY -m evolved_rules.evolve7 --run cma-7 --x0 X0.json --stop-at 2026-11-19T01:22:00+02:00
        [--workers 10] [--popsize 24] [--maps 12] [--sigma0 0.3] [--seed 1] [--log-gen0] [--force-cut]
  PY -m evolved_rules.evolve7 --run cma-7 --resume [--workers N] [--stop-at ...]

X0.json holds {"x": [...], "space": linear.Space.to_json()} (written by the pre-registration step): the start point
x0* in scaled coordinates and the frozen decoder (L, scales, theta, lights). Engine: pycma 4.5.0 with
CMA_diagonal=True (sep-CMA), CMA_mirrors=True (about 0.16 x popsize mirrored samples, pycma's selective mirroring)
and CMA_stds (rule coordinates start at RULE_STD_FACTOR x the std of the other coordinates); bounds [-5, 5] in x.

One generation:
 1. m maps drawn fresh from 1-999 with the run's `random` (shared by every sample).
 2. es.ask() lambda samples, decoded to texts (linear.text_from_x).
 3. Phase A: every distinct sample text on the first CUT_MAPS maps, plus the trend monitor (the in-bounds mean,
    es.boundary_handler.repair(es.mean), before tell) on all m maps. Early cut: a sample whose CUT_MAPS-map mean is
    below CUT_FRACTION x the median CUT_MAPS-map mean stops (--force-cut, test only: also the worst one).
 4. Phase B: the remaining samples on the other m - CUT_MAPS maps.
 5. tell(): completed samples ranked by (m-map mean trips, mean seconds), best first; cut samples below all
    completed ones, by their CUT_MAPS-map mean. Values are ranks (the number of samples strictly better).
 6. Record (generations.jsonl): the trend-monitor mean's text hash and m-map mean, the POPULATION AVERAGE next to the
    BEST of the completed sample means, cuts, sigma, the rule/planner std ratio, the cumulative ledger, wall time.
    final_mean.txt / final_mean.json always hold the in-bounds mean after the last completed tell (the
    recommendation). No per-generation validation, no best-sample promotion.
sigma0 rule (plan 3.3): after generation 0, if more than 20% of samples were cut, or (with --log-gen0) fewer than 25%
of samples built evo routes in at least 2% of decisions, sigma0 is halved once and generation 0 is redone.

Stop: before each generation, and if the last generation's wall time would cross it, at the earlier of --stop-at
and <run>/stop_at.txt (an ISO timestamp with UTC offset; write the file to move T_stop earlier, no kill needed).
The run then ends with status `budget`.
Resume: config.json records `git rev-parse HEAD` and CODE_VERSION; --resume refuses if either differs. Only
--workers and --stop-at may change. Every generation restarts from the checkpointed state (pickled strategy and
RNG states), so a resumed run repeats the interrupted generation exactly; the cache makes its games free.
Ledger: every distinct (text, seed) job a generation requests is charged once (cache hits within the run included,
resume replays not, since the state is restored). Run folder: output/evolved_rules/evolve7/<run>/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pickle
import random
import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import cma

from . import evaluate as ev
from . import evolve as evo
from . import linear, slots
from .engine import CODE_VERSION, Engine, map_id
from .host import ROOT, check_scenario

EVOLVE7_DIR = ROOT / "output" / "evolved_rules" / "evolve7"
FORMAT = "evolve7-1"
CUT_MAPS = 4
CUT_FRACTION = 0.6
RULE_STD_FACTOR = 0.25
CONFIG, CHECKPOINT, GENERATIONS, STATUS = "config.json", "checkpoint.pkl", "generations.jsonl", "status.json"
CACHE, STOP_FILE = "cache.jsonl", "stop_at.txt"
RESUMABLE = ("workers", "stop_at")


def _git_head() -> str | None:
    out = ev._git("rev-parse", "HEAD")
    return out.strip() if out is not None else None


def parse_time(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.strip())
    if t.tzinfo is None:
        raise ValueError(f"stop time {s!r} needs a UTC offset")
    return t


def effective_stop(cfg: dict, run_dir: Path) -> dt.datetime:
    t = parse_time(cfg["stop_at"])
    f = run_dir / STOP_FILE
    if f.exists():
        try:
            t = min(t, parse_time(f.read_text(encoding="utf-8")))
        except ValueError as e:
            print(f"ignoring unreadable {f}: {e}", file=sys.stderr)
    return t


def cma_opts(cfg: dict) -> dict:
    stds = [RULE_STD_FACTOR if g == "rule" else 1.0 for g in linear.GROUPS]
    return {"popsize": cfg["popsize"], "bounds": [-linear.BOUND, linear.BOUND], "seed": cfg["seed"],
            "CMA_diagonal": True, "CMA_mirrors": True, "CMA_stds": stds,
            "verbose": -9, "verb_log": 0, "verb_disp": 0}


def std_ratio(es) -> float:
    s = np.asarray(es.stds)
    rule = [s[i] for i, g in enumerate(linear.GROUPS) if g == "rule"]
    other = [s[i] for i, g in enumerate(linear.GROUPS) if g in ("light", "round", "cost", "target", "newterm", "template")]
    return float(np.mean(rule) / np.mean(other))


def start(cfg: dict, run_dir: Path, x0: list[float], space: linear.Space) -> dict:
    run_dir = Path(run_dir)
    if (run_dir / CHECKPOINT).exists() or (run_dir / CONFIG).exists():
        raise evo.RunExistsError(f"run folder {run_dir} already holds a run (use --resume)")
    run_dir.mkdir(parents=True, exist_ok=True)
    if len(x0) != linear.DIM or any(abs(v) > linear.BOUND for v in x0):
        raise ValueError(f"x0 needs {linear.DIM} entries inside [-{linear.BOUND}, {linear.BOUND}]")
    status = ev._git("status", "--porcelain")
    config = {"format": FORMAT, "params": cfg, "code_version": CODE_VERSION, "commit": _git_head(),
              "dirty": bool(status.strip()) if status is not None else None, "cma_version": cma.__version__,
              "packages": {n: ev._package_version(n) for n in ev.PACKAGES}, "python": sys.version,
              "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"), "x0": list(x0), "space": space.to_json(),
              "cma_opts": cma_opts(cfg), "dim": linear.DIM}
    evo._write_json(run_dir / CONFIG, config)
    random.seed(cfg["seed"])
    es = cma.CMAEvolutionStrategy(list(x0), cfg["sigma0"], cma_opts(cfg))
    state = {"format": FORMAT, "generation": 0, "es": pickle.dumps(es, protocol=pickle.HIGHEST_PROTOCOL),
             "np_rng": np.random.get_state(), "rng": random.getstate(), "ledger": 0, "elapsed_s": 0.0,
             "games_played": 0, "cache_hits": 0, "sigma0": cfg["sigma0"], "sigma0_halved": False,
             "x0": [float(v) for v in x0]}
    (run_dir / GENERATIONS).write_bytes(b"")
    evo.write_checkpoint(run_dir, state)
    _status(run_dir, "running", "started", state)
    return state


def load(run_dir: Path, overrides: dict) -> tuple[dict, dict, linear.Space]:
    run_dir = Path(run_dir)
    config = json.loads((run_dir / CONFIG).read_text(encoding="utf-8"))
    if config.get("format") != FORMAT:
        raise ValueError(f"{run_dir} is not an evolve7 run")
    if config["code_version"] != CODE_VERSION:
        raise ValueError(f"run used CODE_VERSION {config['code_version']}, this code is {CODE_VERSION}: "
                         "never resume across a code change (fork into a new run instead)")
    head = _git_head()
    if config["commit"] != head:
        raise ValueError(f"run started at commit {config['commit']}, HEAD is {head}: never resume across a code "
                         "change (run it from its frozen worktree)")
    bad = set(overrides) - set(RESUMABLE)
    if bad:
        raise ValueError(f"only {', '.join(RESUMABLE)} may change on resume, not {sorted(bad)}")
    cfg = {**config["params"], **overrides}
    with open(run_dir / CHECKPOINT, "rb") as f:
        state = pickle.load(f)
    if state.get("format") != FORMAT:
        raise ValueError("checkpoint format mismatch")
    evo._trim_jsonl(run_dir / GENERATIONS, state["generation"])
    return cfg, state, linear.Space.from_json(config["space"])


def _scale_norm(tconf: dict) -> float:
    """The scale normaliser frozen at launch (x0.json's scale_norm; 1.0 if absent)."""
    try:
        return float(json.loads(Path(tconf["params"]["x0_file"]).read_text(encoding="utf-8")).get("scale_norm", 1.0))
    except (KeyError, OSError, ValueError):
        return 1.0


def fork(trunk_dir: Path, run_dir: Path, workers: int, stop_at: str | None) -> tuple[dict, dict, linear.Space]:
    """gp-7 arm (plan 3.4 fork procedure): a new run folder that starts from the trunk's checkpoint at a generation
    boundary, under this code's CODE_VERSION and commit. Both arms keep the trunk's ledger."""
    trunk_dir, run_dir = Path(trunk_dir), Path(run_dir)
    if (run_dir / CHECKPOINT).exists() or (run_dir / CONFIG).exists():
        raise evo.RunExistsError(f"run folder {run_dir} already holds a run")
    tconf = json.loads((trunk_dir / CONFIG).read_text(encoding="utf-8"))
    with open(trunk_dir / CHECKPOINT, "rb") as f:
        tstate = pickle.load(f)
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg = {**tconf["params"], "workers": workers, "arm": "gp7", "fork_gen": tstate["generation"],
           "forked_from": str(trunk_dir), "log_gen0": False}
    if stop_at:
        cfg["stop_at"] = stop_at
    status = ev._git("status", "--porcelain")
    config = {**tconf, "params": cfg, "code_version": CODE_VERSION, "commit": _git_head(),
              "dirty": bool(status.strip()) if status is not None else None, "forked_from": {
                  "run": str(trunk_dir), "generation": tstate["generation"], "commit": tconf["commit"],
                  "code_version": tconf["code_version"]}}
    evo._write_json(run_dir / CONFIG, config)
    space = linear.Space.from_json(tconf["space"])
    state = {**tstate, "space": space.to_json(), "probe_next": PROBE_FIRST,
             "scale_norm": _scale_norm(tconf)}
    import shutil
    shutil.copyfile(trunk_dir / GENERATIONS, run_dir / GENERATIONS)
    evo.write_checkpoint(run_dir, state)
    _status(run_dir, "running", f"forked from {trunk_dir} at generation {tstate['generation']}", state)
    return cfg, state, space


def _status(run_dir: Path, status: str, reason: str, state: dict) -> None:
    evo._write_json(run_dir / STATUS, {"status": status, "reason": reason, "generations": state["generation"],
                                       "ledger": state["ledger"], "elapsed_s": state["elapsed_s"],
                                       "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z")})


def _mean(games: list[dict]) -> tuple[float, float]:
    return evo._means(games)


def rank_values(order_keys: list[tuple]) -> list[float]:
    """Values for tell (minimised): per sample, the number of samples with a strictly better key (larger is better)."""
    return [float(sum(1 for o in order_keys if o > k)) for k in order_keys]


def _evo_rate(decision_dir: Path, text: str, seeds: list[int]) -> float:
    import gzip
    n = hit = 0
    for s in seeds:
        f = decision_dir / f"{evo.text_hash(text)}_{s}.jsonl.gz"
        if not f.exists():
            continue
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                n += 1
                hit += bool(r.get("evo_built"))
    return hit / n if n else 0.0


def draw_maps(cfg: dict) -> list[int]:
    """The generation's map ids (engine.map_id). One city (the default, Los Angeles): m seeds from 1-999, exactly
    gp-7's draw. gp-8, several cities: m / k seeds from 1-999 per city (drawn in cfg order), interleaved one per
    city at a time, so the first CUT_MAPS maps hold one of each city when k = CUT_MAPS."""
    m, cities = cfg["maps"], cfg.get("cities") or ["LosAngeles"]
    if cities == ["LosAngeles"]:
        return random.sample(range(1, 1000), m)
    if m % len(cities):
        raise ValueError(f"maps ({m}) must be a multiple of the number of cities ({len(cities)})")
    per = {c: random.sample(range(1, 1000), m // len(cities)) for c in cities}
    return [map_id(c, per[c][j]) for j in range(m // len(cities)) for c in cities]


def generation(cfg: dict, state: dict, engine, run_dir: Path, space: linear.Space, clock=time.monotonic) -> dict:
    t0 = clock()
    played0, hits0 = engine.games_played, engine.cache_hits
    gen = state["generation"]
    if state.get("space") is not None:  # gp-7 arm: scales, masks and slot trees change at insertions
        space = linear.Space.from_json(state["space"])
    random.setstate(state["rng"])
    np.random.set_state(state["np_rng"])
    es = pickle.loads(state["es"])
    seeds = draw_maps(cfg)
    xs = es.ask()
    texts = [linear.text_from_x(x, space) for x in xs]
    distinct = list(dict.fromkeys(texts))
    mean_x = es.boundary_handler.repair(np.asarray(es.mean))
    mean_text = linear.text_from_x(mean_x, space)
    logged = gen == 0 and cfg.get("log_gen0") and not state["sigma0_halved"]
    play = (lambda jobs: engine.play_logged(jobs, run_dir / "decisions_gen0")) if logged else engine.play
    a_seeds, b_seeds = seeds[:CUT_MAPS], seeds[CUT_MAPS:]
    jobs_a = [(t, s) for t in distinct for s in a_seeds] + [(mean_text, s) for s in seeds]
    res_a = play(jobs_a)
    if cfg.get("arm") == "gp7":  # the trend monitor's decision records feed the slot screen
        engine.play_logged([(mean_text, s) for s in seeds], run_dir / "decisions_tm" / f"gen{gen}")
    k = len(distinct) * len(a_seeds)
    four = {t: _mean(res_a[i * len(a_seeds):(i + 1) * len(a_seeds)]) for i, t in enumerate(distinct)}
    trend_games = res_a[k:]
    med = statistics.median(v[0] for v in four.values())
    cut = {t for t in distinct if four[t][0] < CUT_FRACTION * med}
    if cfg.get("force_cut") and len(distinct) > 1:
        cut.add(min(distinct, key=lambda t: (four[t], t)))
    keep = [t for t in distinct if t not in cut]
    res_b = play([(t, s) for t in keep for s in b_seeds]) if b_seeds else []
    full = {}
    nb = len(b_seeds)
    for i, t in enumerate(keep):
        ga = res_a[distinct.index(t) * len(a_seeds):(distinct.index(t) + 1) * len(a_seeds)]
        full[t] = _mean(ga + res_b[i * nb:(i + 1) * nb])
    keys = [(1, *full[t]) if t in full else (0, *four[t]) for t in texts]
    es.tell(xs, rank_values(keys))
    charged = len(set(jobs_a)) + len(keep) * nb
    halve = False
    evo_ok = None
    if gen == 0 and not state["sigma0_halved"]:
        frac_cut = len(cut) / len(distinct)
        if logged:
            rates = [_evo_rate(run_dir / "decisions_gen0", t, seeds if t in full else a_seeds) for t in distinct]
            evo_ok = sum(1 for r in rates if r >= 0.02) / len(rates)
        halve = frac_cut > 0.20 or (evo_ok is not None and evo_ok < 0.25)
    final_x = es.boundary_handler.repair(np.asarray(es.mean))
    sample_means = [full[t][0] for t in keep]
    wall = clock() - t0
    played, hits = engine.games_played - played0, engine.cache_hits - hits0
    rec = {
        "gen": gen, "seeds": seeds, "distinct": len(distinct), "cut": len(cut), "completed": len(keep),
        "population": {"average": statistics.fmean(sample_means) if sample_means else None,
                       "best": max(sample_means) if sample_means else None,
                       "average_4map_all": statistics.fmean(v[0] for v in four.values())},
        "trend_monitor": {"hash": evo.text_hash(mean_text), "mean": _mean(trend_games)[0],
                          "mean_seconds": _mean(trend_games)[1], "trips": [g["trips"] for g in trend_games]},
        "sigma": float(es.sigma), "std_ratio_rule_to_planner": std_ratio(es),
        "ledger": state["ledger"] + charged, "charged": charged, "wall_s": wall, "games_played": played,
        "cache_hits": hits, "sigma0": state["sigma0"],
        "gen0_check": ({"frac_cut": len(cut) / len(distinct), "frac_samples_evo_ge_2pct": evo_ok, "halve": halve}
                       if gen == 0 and not state["sigma0_halved"] else None),
        "final_mean_hash": evo.text_hash(linear.text_from_x(final_x, space)),
    }
    evo._append_jsonl(run_dir / GENERATIONS, rec)
    common = {"np_rng": np.random.get_state(), "rng": random.getstate(), "ledger": state["ledger"] + charged,
              "elapsed_s": state["elapsed_s"] + wall, "games_played": state["games_played"] + played,
              "cache_hits": state["cache_hits"] + hits, "last_wall_s": wall}
    if halve:
        es2 = cma.CMAEvolutionStrategy(list(state["x0"]), state["sigma0"] / 2, cma_opts(cfg))
        return {**state, **common, "es": pickle.dumps(es2, protocol=pickle.HIGHEST_PROTOCOL), "generation": 0,
                "sigma0": state["sigma0"] / 2, "sigma0_halved": True}
    nxt = {**state, **common, "es": pickle.dumps(es, protocol=pickle.HIGHEST_PROTOCOL), "generation": gen + 1}
    if cfg.get("arm") == "gp7" and (gen + 1 - cfg["fork_gen"]) % slots.EPOCH_EVERY == 0 and gen + 1 > cfg["fork_gen"]:
        nxt = slot_epoch(cfg, nxt, engine, run_dir, space, gen)
        es = pickle.loads(nxt["es"])
        if nxt.get("space") is not None:
            space = linear.Space.from_json(nxt["space"])
        final_x = es.boundary_handler.repair(np.asarray(es.mean))
    final_text = linear.text_from_x(final_x, space)
    evo._atomic_write(run_dir / "final_mean.txt", (final_text + "\n").encode("utf-8"))
    evo._write_json(run_dir / "final_mean.json", {"gen": gen, "x": [float(v) for v in final_x],
                                                  "hash": evo.text_hash(final_text)})
    return nxt


PROBE_FIRST, PROBE_LAST = 10000, 49999  # gp-7 race probes: 10000+ by counter, never above 49999


def slot_epoch(cfg: dict, state: dict, engine, run_dir: Path, space: linear.Space, gen: int) -> dict:
    """gp-7-lite epoch (slots.py): propose, zero-game screen on the last EPOCH_EVERY generations' trend-monitor
    records, race on RACE_MAPS fresh probe maps, insert accepted trees. Appends one record to slots.jsonl."""
    import gzip
    from . import stats7
    rng = random.Random(f"{cfg['seed']}:{gen}")
    empty = [k for k in range(linear.N_SLOTS) if space.masks[k] == 0]
    recs = []
    for g in range(gen - slots.EPOCH_EVERY + 1, gen + 1):
        for f in sorted((run_dir / "decisions_tm" / f"gen{g}").glob("*.jsonl.gz")):
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                recs += [json.loads(line) for line in fh if line.strip()]
    props = slots.propose(empty, space.theta, rng)
    kept = slots.screen(props, recs)
    es = pickle.loads(state["es"])
    mean_x = np.asarray(es.boundary_handler.repair(np.asarray(es.mean)), dtype=float)
    probe0 = state.get("probe_next", PROBE_FIRST)
    if probe0 + slots.RACE_MAPS - 1 > PROBE_LAST:  # the probe block ends at 49999: no race, nothing inserted
        evo._append_jsonl(run_dir / "slots.jsonl", {"gen": gen, "empty": empty, "skipped": "probe seeds exhausted",
                                                     "probe_next": probe0, "charged": 0})
        return state
    probes = list(range(probe0, probe0 + slots.RACE_MAPS))
    texts = {"mean": linear.text_from_x(mean_x, space)}
    cand_spaces = {}
    for j, d in enumerate(kept):
        k = d["slot"]
        scale = slots.slot_scale(slots.slot_spread(k, d["tree"], recs), state.get("scale_norm", 1.0))
        sp_k = slots.inserted_space(space, k, d["tree"], scale)
        for sign in (1.0, -1.0):
            x = mean_x.copy()
            x[linear.INDEX[f"slot{k}"]] = float(np.clip(sign * d["w0"] / scale, -4.5, 4.5))
            texts[f"{j}{'+' if sign > 0 else '-'}"] = linear.text_from_x(x, sp_k)
            cand_spaces[f"{j}{'+' if sign > 0 else '-'}"] = (sp_k, x[linear.INDEX[f"slot{k}"]], k)
    names = list(texts)
    res = engine.play([(texts[n], s) for n in names for s in probes])
    trips = {n: {s: res[i * len(probes) + q]["trips"] for q, s in enumerate(probes)} for i, n in enumerate(names)}
    tested = []
    for n in names[1:]:
        t = stats7.paired_t_one_sided(stats7.paired_diffs(trips[n], trips["mean"], probes))
        tested.append((t["p"], n, t["mean"]))
    best_per_slot: dict[int, tuple] = {}
    for p, n, m in sorted(tested):
        k = cand_spaces[n][2]
        if p < slots.RACE_P and k not in best_per_slot:
            best_per_slot[k] = (p, n, m)
    new_space = space
    accepted = []
    for k, (p, n, m) in sorted(best_per_slot.items()):
        sp_k, xk, _ = cand_spaces[n]
        new_space = slots.inserted_space(new_space, k, sp_k.slot_trees[k], sp_k.scales[linear.INDEX[f"slot{k}"]])
        es.mean[linear.INDEX[f"slot{k}"]] = xk
        accepted.append({"slot": k, "tree": sp_k.slot_trees[k], "name": n, "p": p, "diff": m, "x": xk})
    charged = len(names) * len(probes)
    evo._append_jsonl(run_dir / "slots.jsonl", {
        "gen": gen, "empty": empty, "records": len(recs), "proposals": len(props), "kept": kept,
        "probes": [probes[0], probes[-1]], "tested": [{"name": n, "p": p, "diff": m} for p, n, m in tested],
        "accepted": accepted, "charged": charged})
    return {**state, "es": pickle.dumps(es, protocol=pickle.HIGHEST_PROTOCOL), "space": new_space.to_json(),
            "probe_next": probe0 + slots.RACE_MAPS, "ledger": state["ledger"] + charged}


def format_record(rec: dict) -> str:
    p, tm = rec["population"], rec["trend_monitor"]
    avg = f"{p['average']:6.1f}" if p["average"] is not None else "   n/a"
    best = f"{p['best']:6.1f}" if p["best"] is not None else "   n/a"
    return (f"gen {rec['gen']:3d} | population average {avg} best {best} (m-map sample means) | trend-monitor mean "
            f"{tm['mean']:6.1f} | cut {rec['cut']}/{rec['distinct']} | sigma {rec['sigma']:.3f} ratio "
            f"{rec['std_ratio_rule_to_planner']:.2f} | ledger {rec['ledger']} | {rec['wall_s']:.0f} s")


def run(cfg: dict, state: dict, run_dir: Path, space: linear.Space, engine=None, now=None, log=print) -> dict:
    run_dir = Path(run_dir)
    now = now or (lambda: dt.datetime.now().astimezone())
    own = engine is None
    if own:
        engine = Engine(workers=cfg["workers"], cap_s=cfg.get("cap_s", ev.DEFAULT_CAP_S), cache_path=run_dir / CACHE,
                        randomness=cfg.get("randomness", "stream"))
    try:
        while True:
            if cfg.get("max_gens") and state["generation"] >= cfg["max_gens"]:
                _status(run_dir, "budget", f"max_gens {cfg['max_gens']} reached (smoke only)", state)
                log(f"budget: max_gens {cfg['max_gens']}")
                return state
            stop = effective_stop(cfg, run_dir)
            last = state.get("last_wall_s", 0.0)
            if now() + dt.timedelta(seconds=last) >= stop:
                _status(run_dir, "budget", f"stop time {stop.isoformat()} reached", state)
                log(f"budget: stop time {stop.isoformat()} (generations {state['generation']})")
                return state
            _status(run_dir, "running", f"generation {state['generation']}", state)
            state = generation(cfg, state, engine, run_dir, space)
            evo.write_checkpoint(run_dir, state)
            recs = evo.read_jsonl(run_dir / GENERATIONS)
            if recs:
                log(format_record(recs[-1]))
    finally:
        if own:
            engine.close()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m evolved_rules.evolve7", description=__doc__.splitlines()[0])
    p.add_argument("--run", required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--fork-from", dest="fork_from", help="gp-7 arm: the trunk run folder to fork from")
    p.add_argument("--x0", help="X0.json (x and space)")
    p.add_argument("--stop-at", dest="stop_at")
    p.add_argument("--workers", type=int)
    p.add_argument("--popsize", type=int, default=24)
    p.add_argument("--maps", type=int, default=12)
    p.add_argument("--sigma0", type=float, default=0.3)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--log-gen0", action="store_true")
    p.add_argument("--force-cut", action="store_true", help="test only: always cut the worst sample")
    p.add_argument("--max-gens", type=int, default=0, help="test only: stop after this many generations")
    p.add_argument("--cities", default="LosAngeles",
                   help="gp-8: comma-separated training cities (CITY_SCENARIOS spelling); maps must be a multiple")
    p.add_argument("--randomness", default="stream", choices=("stream", "keyed"), help="gp-8: simulator randomness")
    p.add_argument("--cap", type=float, default=ev.DEFAULT_CAP_S, help="episode cap in simulated seconds (smoke only)")
    a = p.parse_args(argv)
    ev._check_run_name(a.run)
    run_dir = EVOLVE7_DIR / a.run
    try:
        if a.fork_from and not a.resume:
            if not a.workers:
                p.error("--fork-from needs --workers")
            cfg, state, space = fork(Path(a.fork_from), run_dir, a.workers, a.stop_at)
        elif a.resume:
            overrides = {k: v for k, v in (("workers", a.workers), ("stop_at", a.stop_at)) if v is not None}
            if "stop_at" in overrides:
                parse_time(overrides["stop_at"])
            cfg, state, space = load(run_dir, overrides)
        else:
            if not (a.x0 and a.stop_at and a.workers):
                p.error("a fresh run needs --x0, --stop-at and --workers")
            parse_time(a.stop_at)
            x0doc = json.loads(Path(a.x0).read_text(encoding="utf-8"))
            space = linear.Space.from_json(x0doc["space"])
            cfg = {"popsize": a.popsize, "maps": a.maps, "sigma0": a.sigma0, "seed": a.seed, "workers": a.workers,
                   "stop_at": a.stop_at, "log_gen0": a.log_gen0, "force_cut": a.force_cut,
                   "cap_s": float(a.cap), "x0_file": str(a.x0), "max_gens": a.max_gens,
                   "cities": [check_scenario(c) for c in a.cities.split(",")], "randomness": a.randomness}
            if a.maps % len(cfg["cities"]):
                p.error("--maps must be a multiple of the number of cities")
            state = start(cfg, run_dir, x0doc["x"], space)
    except evo.RunExistsError as e:
        print(str(e), file=sys.stderr)
        return evo.EXISTING_RUN_EXIT_CODE
    except (FileNotFoundError, ValueError) as e:
        print(f"cannot {'resume' if a.resume else 'start'}: {e}", file=sys.stderr)
        return evo.EXISTING_RUN_EXIT_CODE
    state = run(cfg, state, run_dir, space)
    print(f"{run_dir}: budget after {state['generation']} generations; final_mean.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
