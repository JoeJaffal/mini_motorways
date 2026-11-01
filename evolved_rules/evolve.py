"""GP evolution loop with racing, elitism, a validation incumbent and a convergence stop (Phase 2 Task 5).

    PY -m evolved_rules.evolve --run NAME [--resume] [--workers 10] [--pop 64] [--seed 1] [--min-gens 30]
        [--patience 20] [--min-gain-frac 0.02] [--min-gain-trips 3] [--max-hours 72] [--max-gens 400]
        [--validation 1500-1549] [--cap 3600]

One generation (decisions P2-1..P2-4 of plans/2026-11-01-phase2-evolution.md):

1. Draw 4 + 8 training seeds (S4, S8) from LA 1-999 with the run's RNG.
2. Every distinct tree text in the population plays S4. Its fitness is (mean trips, mean seconds) on S4,
   compared lexicographically; ties go to the smaller individual (parsimony), then to the earlier text.
   Fitnesses are never carried over: every generation scores everyone, elites included, on its new seeds.
3. The top 16 distinct texts by S4 also play S8. Their racing score is the mean over all 12 games.
4. The best by racing score is validated on the fixed validation seeds (LA 1500-1549) unless that text was
   validated before (validation is cached by text). The incumbent is the best validated individual so far,
   by (validation mean trips, mean seconds, -size); it is the run's final model (best.txt).
5. Next population: the 3 best distinct texts by racing score unchanged (elitism), then pop - 3 offspring:
   tournament (size 4, with replacement) on the S4 fitness with parsimony, then DEAP's varAnd scheme:
   crossover of consecutive pairs with probability 0.5, then mutation of each offspring with probability
   0.3 (gp.mate / gp.mutate keep every tree within the depth limit of 6).

Stop rule (P2-1, class Convergence; tune_cmaes.py uses the same class, stop_reason and run_loop). A generation counts as an improvement when its validated mean is at
least `anchor + max(min_gain_trips, min_gain_frac * anchor)` and strictly above the anchor, where the anchor
is the validated mean at the last counted improvement (generation 0 sets it). The strict part only matters when
both minimum gains are 0: re-validating the anchor's own (cached) text must not reset the count. Measuring gains from the anchor, not from the
moving incumbent, means a slow creep of small gains still adds up to an improvement once it is big enough,
while noise-sized wiggles never reset the count. The run has converged when at least min_gens generations are
done and the last `patience` generations brought no improvement. The backstop (max_gens generations or
max_hours of wall clock, summed over resumes) stops the run as `budget`, never as converged.

Run folder output/evolved_rules/evolve/<run>/:
    config.json        every parameter, git commit and dirty flag, package versions, CODE_VERSION; resumes
    generations.jsonl  one record per generation (seeds, S4 stats, racing best, validation, incumbent, stop
                       counters, wall time, games played, cache hits)
    validation.jsonl   one record per validated text (per-seed trips and seconds, means, efficiency)
    best.txt           the incumbent's individual text (evaluate.py --policy tree:best.txt plays it)
    checkpoint.pkl     the next generation's population (texts), RNG state, incumbent, counters; atomic
    status.json        running / converged / budget (or failed / interrupted) with a reason
    cache.jsonl        the engine's game cache (engine.py)

Resume. The checkpoint is written atomically at the end of every generation and holds exactly what the next
generation consumes: the population as canonical texts (re-parsed every generation, so an uninterrupted run
and a resumed one start each generation from identical trees), the global `random` state (DEAP's operators and
the seed draws both use it), the stop-rule state and the validation cache. Records of a generation that was
interrupted before its checkpoint are dropped on resume and written again, identically: every game it had
finished is in the cache, so it costs nothing. Only wall time, games played and cache hits differ.

The max_hours budget sums the wall time of checkpointed generations only: time spent in a generation that
crashed or was killed is not counted (its replay after the resume is cheap, thanks to the cache). After crashes
the budget therefore under-counts real wall time; it is a backstop, not an accounting.

A fresh run refuses a folder that holds a run. A folder with no checkpoint.pkl and only the files start() writes
before it (a kill during start) holds no run and is reused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import random
import statistics
import sys
import time
import traceback
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from . import evaluate as ev
from . import gp
from .engine import CODE_VERSION, Engine
from .host import ROOT, default_host_dll

EVOLVE_DIR = ROOT / "output" / "evolved_rules" / "evolve"  # /output/ is git-ignored
CHECKPOINT_FORMAT = 1
EXISTING_RUN_EXIT_CODE = 2
RESUMABLE_FIELDS = ("workers", "max_hours", "max_gens")  # may change on --resume: they never change a generation

# Files of a run folder.
CONFIG, GENERATIONS, VALIDATION, BEST, CHECKPOINT, STATUS, CACHE = (
    "config.json", "generations.jsonl", "validation.jsonl", "best.txt", "checkpoint.pkl", "status.json",
    "cache.jsonl")


class RunExistsError(FileExistsError):
    """A fresh run was asked for a folder that already holds a run."""


@dataclass(frozen=True)
class Config:
    """Every parameter of a run (config.json). Defaults are the Phase 2 decisions."""

    pop: int = 64
    seed: int = 1
    min_gens: int = 30
    patience: int = 20
    min_gain_frac: float = 0.02
    min_gain_trips: float = 3.0
    max_hours: float = 72.0
    max_gens: int = 400
    validation: tuple[int, ...] = tuple(range(1500, 1550))
    workers: int = 10
    cap_s: float = ev.DEFAULT_CAP_S
    n_s4: int = 4  # seeds every individual plays
    n_s8: int = 8  # extra seeds the racing top plays
    racing_top: int = 16
    elites: int = 3
    tournament: int = 4
    cxpb: float = 0.5
    mutpb: float = 0.3
    train_lo: int = 1  # training seeds are drawn from train_lo..train_hi (inclusive)
    train_hi: int = 999

    def check(self) -> None:
        """ValueError for a parameter the loop cannot run with."""
        def need(ok: bool, what: str) -> None:
            if not ok:
                raise ValueError(what)

        ints = ("pop", "seed", "min_gens", "patience", "max_gens", "workers", "n_s4", "n_s8", "racing_top",
                "elites", "tournament", "train_lo", "train_hi")
        for name in ints:
            v = getattr(self, name)
            need(isinstance(v, int) and not isinstance(v, bool), f"{name} must be an int, got {v!r}")
        need(self.pop >= 2, f"pop must be at least 2, got {self.pop}")
        need(1 <= self.elites < self.pop, f"elites must be in 1..pop-1, got {self.elites}")
        need(self.racing_top >= 1, f"racing_top must be at least 1, got {self.racing_top}")
        need(self.elites <= self.racing_top,
             f"elites ({self.elites}) must not exceed racing_top ({self.racing_top}): elites come from the racing top")
        need(self.tournament >= 1, f"tournament must be at least 1, got {self.tournament}")
        need(self.min_gens >= 1 and self.patience >= 1 and self.max_gens >= 1,
             "min_gens, patience and max_gens must be at least 1")
        need(self.min_gain_frac >= 0 and self.min_gain_trips >= 0, "minimum gains must be >= 0")
        need(self.max_hours > 0, f"max_hours must be > 0, got {self.max_hours}")
        need(0.0 <= self.cxpb <= 1.0 and 0.0 <= self.mutpb <= 1.0, "cxpb and mutpb must be in [0, 1]")
        need(self.n_s4 >= 1 and self.n_s8 >= 0, "n_s4 must be at least 1 and n_s8 at least 0")
        need(1 <= self.train_lo <= self.train_hi, "need 1 <= train_lo <= train_hi")
        need(self.n_s4 + self.n_s8 <= self.train_hi - self.train_lo + 1, "more training seeds than the range")
        need(len(self.validation) >= 1, "no validation seeds")
        need(len(set(self.validation)) == len(self.validation), "duplicate validation seeds")
        need(all(isinstance(s, int) and not isinstance(s, bool) for s in self.validation),
             "validation seeds must be ints")
        need(not set(self.validation) & set(range(self.train_lo, self.train_hi + 1)),
             "validation seeds must lie outside the training range")
        ev._check_cap(self.cap_s)

    def to_json(self) -> dict:
        d = asdict(self)
        d["validation"] = list(self.validation)
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Config":
        known = {f.name for f in fields(cls)}
        kw = {k: v for k, v in d.items() if k in known}
        kw["validation"] = tuple(kw.get("validation", ()))
        return cls(**kw)


# --- the stop rule (shared with tune_cmaes.py) ---------------------------------------------------------------

def _validation_key(mean: float, mean_seconds: float, size: int) -> tuple:
    return (mean, mean_seconds, -size)


@dataclass
class Convergence:
    """The stop rule of decision P2-1 and the validation incumbent (see the module docstring).

    observe() is called once per generation, with that generation's validated individual (a text seen
    before passes its cached scores: it can never count twice, since a counted improvement moves the anchor
    up to its mean and the next one must be strictly above it).
    """

    min_gens: int
    patience: int
    min_gain_frac: float
    min_gain_trips: float
    generations: int = 0  # generations observed
    since: int = 0  # generations since the last counted improvement
    anchor: float | None = None  # incumbent's validation mean at the last counted improvement
    incumbent: dict | None = None  # {"text", "hash", "mean", "mean_seconds", "size", "gen"}

    def required_gain(self) -> float:
        """Smallest gain over the anchor that counts as an improvement (min_gain_trips before any anchor)."""
        if self.anchor is None:
            return float(self.min_gain_trips)
        return max(float(self.min_gain_trips), self.min_gain_frac * self.anchor)

    def observe(self, gen: int, text: str, mean: float, mean_seconds: float, size: int) -> bool:
        """Record one generation's validated individual; True when it counts as an improvement."""
        key = _validation_key(mean, mean_seconds, size)
        inc = self.incumbent
        if inc is None or key > _validation_key(inc["mean"], inc["mean_seconds"], inc["size"]):
            self.incumbent = {"text": text, "hash": text_hash(text), "mean": mean, "mean_seconds": mean_seconds,
                              "size": size, "gen": gen}
        improved = self.anchor is None or (mean >= self.anchor + self.required_gain() and mean > self.anchor)
        if improved:
            self.anchor = mean
            self.since = 0
        else:
            self.since += 1
        self.generations += 1
        return improved

    def converged(self) -> bool:
        return self.generations >= self.min_gens and self.since >= self.patience

    def state(self) -> dict:
        return asdict(self)

    @classmethod
    def from_state(cls, d: dict) -> "Convergence":
        return cls(**d)


def stop_reason(cfg: Config, conv: Convergence, generations_done: int, elapsed_s: float) -> tuple[str, str] | None:
    """(status, reason) when the run must stop now, else None. Convergence wins over the budget."""
    if conv.converged():
        return "converged", (f"no validation gain of at least {conv.required_gain():.2f} trips over "
                             f"{conv.anchor:.2f} in the last {conv.since} generations "
                             f"(after {conv.generations} generations)")
    if generations_done >= cfg.max_gens:
        return "budget", f"budget: {generations_done} generations (max_gens {cfg.max_gens})"
    if elapsed_s >= cfg.max_hours * 3600.0:
        return "budget", f"budget: {elapsed_s / 3600.0:.2f} h wall clock (max_hours {cfg.max_hours:g})"
    return None


# --- selection and variation ---------------------------------------------------------------------------------

def text_hash(text: str) -> str:
    """Short stable id of an individual text (the records' hash field)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def rank(texts: list[str], score: dict, sizes: dict) -> list[str]:
    """Distinct texts best first by (score, -size); full ties keep their first-appearance order."""
    distinct = list(dict.fromkeys(texts))
    return sorted(distinct, key=lambda t: (score[t], -sizes[t]), reverse=True)  # sort is stable in reverse too


def tournament(population: list[str], fitness: dict, sizes: dict, k: int) -> str:
    """k aspirants drawn with replacement; the best by (fitness, -size) wins, the first drawn on a full tie."""
    aspirants = [random.choice(population) for _ in range(k)]
    return max(aspirants, key=lambda t: (fitness[t], -sizes[t]))  # max keeps the first maximal element


def breed(population: list[str], fitness: dict, sizes: dict, elites: list[str], cfg: Config) -> list[str]:
    """Next population: elites unchanged, then pop - len(elites) varied tournament winners (canonical texts)."""
    picks = [tournament(population, fitness, sizes, cfg.tournament) for _ in range(cfg.pop - len(elites))]
    offspring = [gp.individual_from_text(t) for t in picks]  # fresh trees: mate and mutate work in place
    for i in range(1, len(offspring), 2):
        if random.random() < cfg.cxpb:
            gp.mate(offspring[i - 1], offspring[i])
    for ind in offspring:
        if random.random() < cfg.mutpb:
            gp.mutate(ind)
    return list(elites) + [gp.individual_text(ind) for ind in offspring]


def initial_population(cfg: Config) -> list[str]:
    """The hand rule, the separated preference, then random individuals (P2-9), from the global `random`."""
    texts = [gp.individual_text(gp.individual_from_text(gp.HAND_TEXT)),
             gp.individual_text(gp.individual_from_text(gp.SEPARATED_TEXT))][:cfg.pop]
    while len(texts) < cfg.pop:
        texts.append(gp.individual_text(gp.random_individual()))
    return texts


def _means(games: list[dict]) -> tuple[float, float]:
    return (float(statistics.fmean(g["trips"] for g in games)), float(statistics.fmean(g["seconds"] for g in games)))


def _stats(values: list[float]) -> dict:
    return {"best": max(values), "mean": float(statistics.fmean(values)), "median": float(statistics.median(values))}


# --- files ---------------------------------------------------------------------------------------------------

def _atomic_write(path: Path, data: bytes) -> None:
    """Write via a temporary file and os.replace (retried briefly: Windows refuses while a reader has it open)."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1)


def _write_json(path: Path, obj) -> None:
    _atomic_write(path, (json.dumps(obj, indent=2) + "\n").encode("utf-8"))


def _append_jsonl(path: Path, obj) -> None:
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: Path) -> list[dict]:
    """Every well-formed line (a torn last line from a kill is skipped)."""
    if not path.exists():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(raw))
        except ValueError:
            continue
    return out


def _trim_jsonl(path: Path, next_gen: int) -> None:
    """Keep only records of generations before next_gen (those after the checkpoint are played again)."""
    kept = [r for r in read_jsonl(path) if isinstance(r, dict) and r.get("gen", next_gen) < next_gen]
    _atomic_write(path, "".join(json.dumps(r) + "\n" for r in kept).encode("utf-8"))


def write_checkpoint(run_dir: Path, state: dict) -> None:
    _atomic_write(run_dir / CHECKPOINT, pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))


def read_checkpoint(run_dir: Path) -> dict:
    with open(run_dir / CHECKPOINT, "rb") as f:
        state = pickle.load(f)  # our own file, written by write_checkpoint
    if state.get("format") != CHECKPOINT_FORMAT:
        raise ValueError(f"checkpoint format {state.get('format')!r}, expected {CHECKPOINT_FORMAT}")
    return state


def _write_status(run_dir: Path, status: str, reason: str, state: dict) -> None:
    conv = state["convergence"]
    _write_json(run_dir / STATUS, {
        "status": status, "reason": reason, "generations": state["generation"],
        "incumbent": None if conv["incumbent"] is None else {k: v for k, v in conv["incumbent"].items()
                                                             if k != "text"},
        "elapsed_s": state["elapsed_s"], "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })


def _run_config(cfg: Config) -> dict:
    commit = ev._git("rev-parse", "HEAD")
    status = ev._git("status", "--porcelain")
    return {
        "params": cfg.to_json(),
        "code_version": CODE_VERSION,
        "commit": commit.strip() if commit is not None else None,
        "dirty": bool(status.strip()) if status is not None else None,
        "packages": {name: ev._package_version(name) for name in ev.PACKAGES},
        "python": sys.version,
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
        "host_dll": str(default_host_dll()),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "resumes": [],
    }


# --- the run -------------------------------------------------------------------------------------------------

# What start() writes before the generation-0 checkpoint: a folder holding only these (and no checkpoint) is
# what a kill during start() leaves behind, and a fresh start may reuse it.
_START_FILES = frozenset({CONFIG, CONFIG + ".tmp", GENERATIONS, VALIDATION, CHECKPOINT + ".tmp"})


def _holds_run(run_dir: Path) -> bool:
    """True when run_dir holds a run (or anything else) a fresh start must not overwrite."""
    if not run_dir.exists():
        return False
    names = {p.name for p in run_dir.iterdir()}
    return CHECKPOINT in names or not names <= _START_FILES


def start(cfg: Config, run_dir: Path) -> dict:
    """Claim run_dir for a fresh run: config.json, the generation-0 checkpoint and status. Returns the state."""
    cfg.check()
    run_dir = Path(run_dir)
    if _holds_run(run_dir):
        raise RunExistsError(f"run folder {run_dir} already holds a run (use --resume to continue it)")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / CONFIG, _run_config(cfg))
    random.seed(cfg.seed)
    population = initial_population(cfg)
    conv = Convergence(cfg.min_gens, cfg.patience, cfg.min_gain_frac, cfg.min_gain_trips)
    state = {"format": CHECKPOINT_FORMAT, "generation": 0, "population": population, "rng": random.getstate(),
             "convergence": conv.state(), "validated": {}, "elapsed_s": 0.0, "games_played": 0,
             "cache_hits": 0}
    for name in (GENERATIONS, VALIDATION):
        (run_dir / name).write_bytes(b"")
    write_checkpoint(run_dir, state)
    _write_status(run_dir, "running", "started", state)
    return state


def load(run_dir: Path, overrides: dict | None = None, config_cls=Config) -> tuple[Config, dict]:
    """Config and checkpoint state of an existing run, with records after the checkpoint dropped.

    overrides may change only RESUMABLE_FIELDS (ValueError otherwise); a change is logged in config.json.
    config_cls reads the saved parameters (tune_cmaes.CmaConfig for a CMA-ES run: same files, same rules).
    """
    run_dir = Path(run_dir)
    if not (run_dir / CHECKPOINT).exists():
        raise FileNotFoundError(f"no checkpoint in {run_dir}: nothing to resume")
    config = json.loads((run_dir / CONFIG).read_text(encoding="utf-8"))
    if config_cls is Config and config.get("method") is not None:
        # Refuse before touching the folder: a GP resume of another method's run would log a resume in its
        # config.json, then fail on the foreign checkpoint and mark that run failed.
        raise ValueError(f"{run_dir} holds a {config['method']} run, not a GP run")
    params = dict(config["params"])
    changed = {}
    for name, value in (overrides or {}).items():
        if isinstance(value, tuple):
            value = list(value)  # config.json holds lists
        if value is None or params.get(name) == value:
            continue
        if name not in RESUMABLE_FIELDS:
            raise ValueError(f"--{name.replace('_', '-')} {value!r} differs from the saved run "
                             f"({params.get(name)!r}); only {', '.join(RESUMABLE_FIELDS)} may change on resume")
        changed[name] = value
    params.update(changed)
    cfg = config_cls.from_json(params)
    cfg.check()
    state = read_checkpoint(run_dir)
    for name in (GENERATIONS, VALIDATION):
        _trim_jsonl(run_dir / name, state["generation"])
    (run_dir / "error.txt").unlink(missing_ok=True)  # a failure being resumed is no longer the run's state
    config["params"] = cfg.to_json()
    config.setdefault("resumes", []).append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                             "generation": state["generation"], "changed": changed})
    _write_json(run_dir / CONFIG, config)
    return cfg, state


def _validate(cfg: Config, engine, gen: int, text: str, size: int) -> dict:
    """Play text on the validation seeds; returns its validation.jsonl record."""
    games = engine.play([(text, s) for s in cfg.validation])
    trips = [g["trips"] for g in games]
    seconds = [g["seconds"] for g in games]
    tiles = [g.get("tiles_built", 0) for g in games]
    return {
        "gen": gen, "hash": text_hash(text), "text": text, "size": size, "seeds": list(cfg.validation),
        "trips": trips, "seconds": seconds, "tiles_built": tiles, "commands": [g.get("commands") for g in games],
        "mean": float(statistics.fmean(trips)), "mean_seconds": float(statistics.fmean(seconds)),
        "trips_per_tile": (sum(trips) / sum(tiles)) if sum(tiles) > 0 else 0.0,
    }


def generation(cfg: Config, state: dict, engine, run_dir: Path, clock=time.monotonic) -> dict:
    """Play one generation, append its records and return the next state (not yet checkpointed)."""
    t0 = clock()
    played0, hits0 = engine.games_played, engine.cache_hits
    gen = state["generation"]
    random.setstate(state["rng"])
    population = [gp.individual_text(gp.individual_from_text(t)) for t in state["population"]]
    distinct = list(dict.fromkeys(population))
    sizes = {t: gp.size(gp.individual_from_text(t)) for t in distinct}

    seeds = random.sample(range(cfg.train_lo, cfg.train_hi + 1), cfg.n_s4 + cfg.n_s8)
    s4, s8 = seeds[:cfg.n_s4], seeds[cfg.n_s4:]
    games4 = engine.play([(t, s) for t in distinct for s in s4])
    by4 = {t: games4[i * cfg.n_s4:(i + 1) * cfg.n_s4] for i, t in enumerate(distinct)}
    fitness = {t: _means(by4[t]) for t in distinct}

    top = rank(distinct, fitness, sizes)[:cfg.racing_top]
    games8 = engine.play([(t, s) for t in top for s in s8]) if s8 else []
    racing_games = {t: by4[t] + games8[i * cfg.n_s8:(i + 1) * cfg.n_s8] for i, t in enumerate(top)}
    racing = {t: _means(racing_games[t]) for t in top}
    ranked = rank(top, racing, sizes)
    elites = ranked[:cfg.elites]
    best = ranked[0]

    validated = dict(state["validated"])
    new = best not in validated
    if new:
        record = _validate(cfg, engine, gen, best, sizes[best])
        _append_jsonl(run_dir / VALIDATION, record)
        validated[best] = {"mean": record["mean"], "mean_seconds": record["mean_seconds"], "gen": gen}
    v = validated[best]
    conv = Convergence.from_state(state["convergence"])
    improved = conv.observe(gen, best, v["mean"], v["mean_seconds"], sizes[best])

    next_population = breed(population, fitness, sizes, elites, cfg)
    wall = clock() - t0
    played, hits = engine.games_played - played0, engine.cache_hits - hits0
    best_games = racing_games[best]
    tiles = sum(g.get("tiles_built", 0) for g in best_games)
    inc = conv.incumbent
    rec = {
        "gen": gen, "seeds": {"s4": s4, "s8": s8}, "distinct": len(distinct),
        "s4": _stats([fitness[t][0] for t in population]),
        "best": {"hash": text_hash(best), "size": sizes[best], "racing_mean": racing[best][0],
                 "racing_seconds": racing[best][1], "s4_mean": fitness[best][0],
                 "trips_per_tile": (sum(g["trips"] for g in best_games) / tiles) if tiles > 0 else 0.0},
        "elites": [text_hash(t) for t in elites],
        "validated": {"hash": text_hash(best), "new": new, "mean": v["mean"], "mean_seconds": v["mean_seconds"]},
        "improved": improved,
        "incumbent": {"hash": inc["hash"], "mean": inc["mean"], "mean_seconds": inc["mean_seconds"],
                      "size": inc["size"], "gen": inc["gen"]},
        "anchor": conv.anchor, "required_gain": conv.required_gain(), "gens_since_improvement": conv.since,
        "wall_s": wall, "games_played": played, "cache_hits": hits,
    }
    _append_jsonl(run_dir / GENERATIONS, rec)
    _atomic_write(run_dir / BEST, (inc["text"] + "\n").encode("utf-8"))
    return {**state, "generation": gen + 1, "population": next_population, "rng": random.getstate(),
            "convergence": conv.state(), "validated": validated, "elapsed_s": state["elapsed_s"] + wall,
            "games_played": state["games_played"] + played, "cache_hits": state["cache_hits"] + hits}


def format_record(rec: dict, cfg: Config) -> str:
    """The one line printed per generation."""
    v, inc = rec["validated"], rec["incumbent"]
    return (f"gen {rec['gen']:3d} | S4 best {rec['s4']['best']:6.1f} mean {rec['s4']['mean']:6.1f} | "
            f"racing best {rec['best']['racing_mean']:6.1f} size {rec['best']['size']:3d} | "
            f"val {v['mean']:6.1f}{' new' if v['new'] else ' old'}{' +' if rec['improved'] else ''} | "
            f"incumbent {inc['mean']:6.1f} (gen {inc['gen']}) | since {rec['gens_since_improvement']}/"
            f"{cfg.patience} | {rec['wall_s']:.0f} s, {rec['games_played']} games, {rec['cache_hits']} hits")


def run_loop(cfg: Config, state: dict, engine, run_dir: Path, clock=time.monotonic, log=print,
             step=None, fmt=None) -> dict:
    """Generations until the stop rule or the budget; returns the final status dict (also status.json).

    step(cfg, state, engine, run_dir, clock=...) plays one generation and fmt(record, cfg) prints its line
    (default: this module's generation and format_record; tune_cmaes passes its own, sharing everything else:
    the stop rule, the budget, checkpoints and the status file).
    """
    run_dir = Path(run_dir)
    step = generation if step is None else step
    fmt = format_record if fmt is None else fmt
    try:
        while True:
            conv = Convergence.from_state(state["convergence"])
            stop = stop_reason(cfg, conv, state["generation"], state["elapsed_s"])
            if stop is not None:
                _write_status(run_dir, *stop, state)
                log(f"stopped: {stop[0]} ({stop[1]})")
                return json.loads((run_dir / STATUS).read_text(encoding="utf-8"))
            _write_status(run_dir, "running", f"generation {state['generation']}", state)
            state = step(cfg, state, engine, run_dir, clock=clock)
            write_checkpoint(run_dir, state)
            log(fmt(read_jsonl(run_dir / GENERATIONS)[-1], cfg))
    except KeyboardInterrupt:
        _write_status(run_dir, "interrupted", "KeyboardInterrupt (resume with --resume)", state)
        raise
    except Exception as e:
        _write_status(run_dir, "failed", f"{type(e).__name__}: {e}", state)
        (run_dir / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise


def _make_engine(cfg: Config, run_dir: Path) -> Engine:
    return Engine(workers=cfg.workers, cap_s=cfg.cap_s, cache_path=run_dir / CACHE)


def open_run(cfg: Config | None, run_dir: Path, resume: bool = False,
             overrides: dict | None = None) -> tuple[Config, dict]:
    """Start a fresh run (needs cfg) or, with resume, load one (takes only `overrides`); (config, state)."""
    if resume:
        return load(Path(run_dir), overrides)
    return cfg, start(cfg, Path(run_dir))


def play_run(cfg: Config, state: dict, run_dir: Path, engine=None, clock=time.monotonic, log=print) -> dict:
    """Play an opened run to its stop; returns the status.

    engine defaults to an Engine on the run's cache (closed at the end); a given engine is not closed.
    """
    run_dir = Path(run_dir)
    os.environ["PYTHONHASHSEED"] = "0"
    own = engine is None
    if own:
        engine = _make_engine(cfg, run_dir)
    try:
        return run_loop(cfg, state, engine, run_dir, clock=clock, log=log)
    finally:
        if own:
            engine.close()


def evolve(cfg: Config | None, run_dir: Path, resume: bool = False, overrides: dict | None = None,
           engine=None, clock=time.monotonic, log=print) -> dict:
    """Start (or with resume, continue) the run in run_dir and play it to its stop; returns the status."""
    cfg, state = open_run(cfg, run_dir, resume=resume, overrides=overrides)
    return play_run(cfg, state, run_dir, engine=engine, clock=clock, log=log)


# --- CLI -----------------------------------------------------------------------------------------------------

def parse_validation(spec: str) -> tuple[int, ...]:
    """'1500-1549', '1500-1509 1600' or '1500-1509,1600' -> seeds."""
    return tuple(ev.parse_seeds(spec.replace(",", " ").split()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evolved_rules.evolve", description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="run folder name under output/evolved_rules/evolve")
    parser.add_argument("--resume", action="store_true", help="continue the run from its checkpoint")
    d = Config()
    # Defaults are None so a resume can tell an option given on the command line from one left out.
    parser.add_argument("--workers", type=int, help=f"host processes (default {d.workers})")
    parser.add_argument("--pop", type=int, help=f"population size (default {d.pop})")
    parser.add_argument("--seed", type=int, help=f"RNG seed (default {d.seed})")
    parser.add_argument("--min-gens", type=int, help=f"generations before convergence can stop (default {d.min_gens})")
    parser.add_argument("--patience", type=int, help=f"generations without improvement to stop (default {d.patience})")
    parser.add_argument("--min-gain-frac", type=float, help=f"gain fraction of the anchor (default {d.min_gain_frac})")
    parser.add_argument("--min-gain-trips", type=float, help=f"minimum gain in trips (default {d.min_gain_trips:g})")
    parser.add_argument("--max-hours", type=float, help=f"wall-clock budget (default {d.max_hours:g})")
    parser.add_argument("--max-gens", type=int, help=f"generation budget (default {d.max_gens})")
    parser.add_argument("--validation", help="validation seeds, e.g. 1500-1549 (default 1500-1549)")
    parser.add_argument("--cap", type=float, dest="cap_s", help=f"episode cap in simulated seconds (default {d.cap_s:g})")
    args = parser.parse_args(argv)
    given = {k: v for k, v in vars(args).items() if k not in ("run", "resume") and v is not None}
    try:
        ev._check_run_name(args.run)
        if "validation" in given:
            given["validation"] = parse_validation(given["validation"])
        cfg = None if args.resume else Config(**given)
        if cfg is not None:
            cfg.check()
    except ValueError as e:
        parser.error(str(e))
    run_dir = EVOLVE_DIR / args.run
    # Only opening the run maps to exit code 2; an error inside the run itself propagates with its traceback.
    try:
        cfg, state = open_run(cfg, run_dir, resume=args.resume, overrides=given if args.resume else None)
    except RunExistsError as e:
        print(str(e), file=sys.stderr)
        return EXISTING_RUN_EXIT_CODE
    except (FileNotFoundError, ValueError) as e:
        if not args.resume:
            raise
        print(f"cannot resume: {e}", file=sys.stderr)
        return EXISTING_RUN_EXIT_CODE
    status = play_run(cfg, state, run_dir)
    inc = status.get("incumbent") or {}
    print(f"{run_dir}: {status['status']} after {status['generations']} generations; incumbent "
          f"{inc.get('mean', float('nan')):.1f} trips (gen {inc.get('gen')}), best.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["Config", "Convergence", "stop_reason", "rank", "tournament", "breed", "initial_population",
           "text_hash", "start", "load", "open_run", "play_run", "generation", "run_loop", "evolve", "main",
           "EVOLVE_DIR", "RunExistsError", "read_jsonl", "read_checkpoint"]
