"""CMA-ES control: a linear policy tuned by CMA-ES, validated and stopped exactly like the GP run (Phase 2 Task 6).

    PY -m evolved_rules.tune_cmaes --run NAME [--resume] [--workers 10] [--popsize 16] [--seed 1] [--sigma0 0.5]
        [--x0 separated] [--n-train 8] [--min-gens 30] [--patience 20] [--min-gain-frac 0.02]
        [--min-gain-trips 3] [--max-hours 72] [--max-gens 400] [--validation 1500-1549] [--cap 3600]

Why a control. The GP run searches tree shapes and constants at once; this run keeps the shape fixed (a weighted
sum of the same scaled terminals) and searches only the weights. If GP beats it, the tree structure is earning
its keep; if not, the terminals alone carry the gain.

The policy (a vector of DIM = 63 weights, each bounded to [-5, 5]; 67 before gp.DROPPED_TERMS):

    priority = sum_i w_i * t_i   over the candidate + global terminals (gp.PRIORITY_TERMS)
    hold     = b + sum_j v_j * g_j over the global terminals (gp.HOLD_TERMS), b a bias
    upgrade  = sum_k u_k * o_k   over the offer + global terminals (gp.UPGRADE_TERMS)

It is written as an ordinary individual text (weights_to_text): each tree a balanced sum of `mul(w, term)`
nodes (the hold bias a bare constant), so it plays through the same Engine, cache and TreePolicy as GP, and
best.txt runs with `evaluate.py --policy tree:best.txt`. Weights are rounded to 4 decimals (snap), so a weight
vector and its text convert exactly both ways (text_to_weights is the strict inverse). Every feature is finite
and adding a zero term is exact, so the hand rule's vector plays exactly HandRule (coverage off; tested). The
separated preference's 1000 bonus (15.625 scaled) does not fit the bound; SEPARATED_WEIGHTS uses 5, which
plays the same choices while a route needs fewer than 317 tiles (candidates order the same below 320; the
hold check `best >= 0.0625 - road_stock` keeps a separated route up to 316 + stock tiles instead of 996 + stock).

One generation (decision P2-3's CMA-ES variant):

1. Draw n_train (8) training seeds from LA 1-999 with the run's `random`.
2. es.ask() popsize (16) candidates (cma's BoundTransform keeps them inside the bounds); snap each.
3. Every candidate plays the same training seeds. Its fitness is (mean trips, mean seconds), lexicographic
   (P2-4). CMA-ES only uses the order of the values it is told, so it is told ranks: the number of
   candidates strictly better (ties share a rank). That is the lexicographic order exactly, with no weighting
   of seconds against trips.
4. The best candidate by fitness is validated (P2-2) unless its text was validated before, and the shared
   stop rule (evolve.Convergence, evolve.stop_reason) decides convergence: identical to evolve.py.

cma's own termination criteria (tolfun, tolx, ...) do not stop the run; they are recorded per generation
(cma_stop). The validation plateau is the one stop rule, as for GP.

Run folder output/evolved_rules/cmaes/<run>/ holds the files of an evolve.py run (config.json,
generations.jsonl, validation.jsonl, best.txt, checkpoint.pkl, status.json, cache.jsonl), written by the same
helpers, plus best_weights.json (the incumbent's weights by tree and terminal).

Resume. The checkpoint holds the pickled CMAEvolutionStrategy and Python's `random` state (the seed draws).
The RNG cma samples from travels inside the pickled strategy: its opts['randn'] is the bound method
np.random.randn, and pickling it pickles a copy of the RandomState, so after unpickling, es.ask() draws from
that private copy and numpy's global state has no effect on it. The checkpoint also keeps numpy's global RNG
state (np_rng) and restores it each generation, only as a safeguard for any direct np.random.* call inside
cma. Every generation, the uninterrupted run included, unpickles the strategy and restores the RNG states
from the state it was given, so a resumed run produces the same generations as an uninterrupted one; the
cache makes the replayed games free.
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import random
import re
import sys
import time
import warnings
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np

with warnings.catch_warnings():
    warnings.simplefilter("ignore")  # cma warns that matplotlib is missing: only cma.plot needs it
    import cma

from . import evaluate as ev
from . import evolve as evo
from . import gp
from .engine import Engine
from .evolve import Convergence, stop_reason
from .host import ROOT

CMAES_DIR = ROOT / "output" / "evolved_rules" / "cmaes"  # /output/ is git-ignored
METHOD = "cma-es"
WEIGHTS = "best_weights.json"

BOUND = 5.0  # every weight lies in [-BOUND, BOUND]
DECIMALS = 4  # weights are rounded to this many decimals: exact text <-> vector, and short texts
BIAS = "bias"

# The vector layout: (tree index, terminal) per weight. Hold's bias comes first in its tree.
LAYOUT: tuple[tuple[int, str], ...] = (
    tuple((0, t) for t in gp.PRIORITY_TERMS)
    + ((1, BIAS),) + tuple((1, t) for t in gp.HOLD_TERMS)
    + tuple((2, t) for t in gp.UPGRADE_TERMS)
)
DIM = len(LAYOUT)


# --- weight vector <-> individual text -------------------------------------------------------------------

def snap(x) -> tuple[float, ...]:
    """A weight vector clipped to the bounds and rounded to DECIMALS (never -0.0). ValueError if malformed."""
    values = list(x)
    if len(values) != DIM:
        raise ValueError(f"a weight vector has {DIM} entries, got {len(values)}")
    out = []
    for v in values:
        v = float(v)
        if not math.isfinite(v):
            raise ValueError(f"weights must be finite, got {v!r}")
        out.append(round(min(BOUND, max(-BOUND, v)), DECIMALS) + 0.0)  # + 0.0 turns -0.0 into 0.0
    return tuple(out)


def _balanced(items: list[str]) -> str:
    """A balanced add() tree over items, in order (depth log2(n), not n: a 31-term chain would be 31 deep)."""
    if len(items) == 1:
        return items[0]
    mid = (len(items) + 1) // 2
    return f"add({_balanced(items[:mid])}, {_balanced(items[mid:])})"


def weights_to_text(w) -> str:
    """The canonical individual text of a weight vector (snapped first)."""
    w = snap(w)
    items: tuple[list[str], ...] = ([], [], [])
    for (tree, term), v in zip(LAYOUT, w):
        items[tree].append(repr(v) if term == BIAS else f"mul({v!r}, {term})")
    return "\n".join(f"{name}: {_balanced(it)}" for name, it in zip(gp.TREE_NAMES, items))


_MUL = re.compile(r"mul\(([^\s(),]+), ([A-Za-z_][A-Za-z0-9_]*)\)")
_TOKEN = re.compile(r"[^\s(),]+")


def text_to_weights(text: str) -> tuple[float, ...]:
    """Inverse of weights_to_text. ValueError for a text that weights_to_text would not write."""
    ind = gp.individual_from_text(text)  # ValueError for anything that is not an individual text
    exprs = [str(t) for t in ind]
    found: list[dict[str, float]] = []
    for i, expr in enumerate(exprs):
        terms: dict[str, float] = {}
        for const, name in _MUL.findall(expr):
            if name in terms:
                raise ValueError(f"not a linear policy: {name} appears twice in the {gp.TREE_NAMES[i]} tree")
            terms[name] = float(const)
        rest = [tok for tok in _TOKEN.findall(_MUL.sub("", expr)) if tok != "add"]
        if i == 1:
            if len(rest) != 1:
                raise ValueError("not a linear policy: the hold tree needs exactly one bias constant")
            terms[BIAS] = float(rest[0])
        elif rest:
            raise ValueError(f"not a linear policy: {rest[0]!r} outside a mul() in the {gp.TREE_NAMES[i]} tree")
        found.append(terms)
    try:
        w = tuple(found[tree][term] for tree, term in LAYOUT)
    except KeyError as e:
        raise ValueError(f"not a linear policy: terminal {e.args[0]} has no weight") from None
    if weights_to_text(w) != gp.individual_text(ind):
        raise ValueError("not a linear policy text (layout, order, bounds or rounding differ from weights_to_text)")
    return w


def weights_from(by_tree: dict[str, dict[str, float]]) -> tuple[float, ...]:
    """A weight vector from {tree name: {terminal (or 'bias'): weight}}; unnamed weights are 0."""
    known = {(gp.TREE_NAMES[tree], term) for tree, term in LAYOUT}
    for name, terms in by_tree.items():
        for term in terms:
            if (name, term) not in known:
                raise ValueError(f"no weight {term!r} in the {name} tree")
    return snap(by_tree.get(gp.TREE_NAMES[tree], {}).get(term, 0.0) for tree, term in LAYOUT)


def weights_by_tree(w) -> dict[str, dict[str, float]]:
    """{tree name: {terminal: weight}} in layout order (best_weights.json)."""
    out: dict[str, dict[str, float]] = {name: {} for name in gp.TREE_NAMES}
    for (tree, term), v in zip(LAYOUT, snap(w)):
        out[gp.TREE_NAMES[tree]][term] = v
    return out


# The Phase 1 rules as weight vectors (in gp's scaled units: see gp.HAND_TEXT).
HAND_WEIGHTS = weights_from({"priority": {"tiles_needed": -1.0},
                             "hold": {BIAS: 0.0625, "road_stock": -1.0},
                             "upgrade": {"offer_roads": 1.0}})
SEPARATED_WEIGHTS = weights_from({"priority": {"tiles_needed": -1.0, "is_separated": BOUND},
                                  "hold": {BIAS: 0.0625, "road_stock": -1.0},
                                  "upgrade": {"offer_roads": 1.0}})
X0 = {"separated": SEPARATED_WEIGHTS, "hand": HAND_WEIGHTS, "zero": snap([0.0] * DIM)}
SIZE = gp.size(gp.individual_from_text(weights_to_text(X0["zero"])))  # every linear text has this many nodes


# --- configuration -----------------------------------------------------------------------------------------

@dataclass(frozen=True)
class CmaConfig:
    """Every parameter of a CMA-ES run (config.json). Stop-rule defaults are evolve.Config's (P2-1, P2-2)."""

    popsize: int = 16
    seed: int = 1  # Python's random (seed draws) and cma's numpy seed; cma reads 0 as "random", so >= 1
    sigma0: float = 0.5
    x0: str = "separated"
    n_train: int = 8
    min_gens: int = 30
    patience: int = 20
    min_gain_frac: float = 0.02
    min_gain_trips: float = 3.0
    sig_alpha: float = 0.005  # the stop rule's paired test (evolve.Convergence), as in evolve.Config
    max_hours: float = 72.0
    max_gens: int = 400
    validation: tuple[int, ...] = tuple(range(1500, 1550))
    workers: int = 10
    cap_s: float = ev.DEFAULT_CAP_S
    train_lo: int = 1
    train_hi: int = 999

    def check(self) -> None:
        """ValueError for a parameter the loop cannot run with."""
        def need(ok: bool, what: str) -> None:
            if not ok:
                raise ValueError(what)

        for name in ("popsize", "seed", "n_train", "min_gens", "patience", "max_gens", "workers", "train_lo",
                     "train_hi"):
            v = getattr(self, name)
            need(isinstance(v, int) and not isinstance(v, bool), f"{name} must be an int, got {v!r}")
        need(self.popsize >= 2, f"popsize must be at least 2, got {self.popsize}")
        need(self.seed >= 1, f"seed must be at least 1 (cma treats 0 as a random seed), got {self.seed}")
        need(isinstance(self.sigma0, (int, float)) and math.isfinite(self.sigma0) and 0 < self.sigma0 <= BOUND,
             f"sigma0 must be in (0, {BOUND:g}], got {self.sigma0!r}")
        need(self.x0 in X0, f"x0 must be one of {', '.join(X0)}, got {self.x0!r}")
        need(self.n_train >= 1, f"n_train must be at least 1, got {self.n_train}")
        need(self.min_gens >= 1 and self.patience >= 1 and self.max_gens >= 1,
             "min_gens, patience and max_gens must be at least 1")
        need(self.min_gain_frac >= 0 and self.min_gain_trips >= 0, "minimum gains must be >= 0")
        need(isinstance(self.sig_alpha, (int, float)) and 0.0 <= self.sig_alpha < 0.5,
             f"sig_alpha must be in [0, 0.5), got {self.sig_alpha!r}")
        need(self.max_hours > 0, f"max_hours must be > 0, got {self.max_hours}")
        need(1 <= self.train_lo <= self.train_hi, "need 1 <= train_lo <= train_hi")
        need(self.n_train <= self.train_hi - self.train_lo + 1, "more training seeds than the range")
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
    def from_json(cls, d: dict) -> "CmaConfig":
        known = {f.name for f in fields(cls)}
        kw = {k: v for k, v in d.items() if k in known}
        kw["validation"] = tuple(kw.get("validation", ()))
        return cls(**kw)


def cma_options(cfg: CmaConfig) -> dict:
    """cma options: popsize, bounds, seed; silent (no screen output, no outcmaes files)."""
    return {"popsize": cfg.popsize, "bounds": [-BOUND, BOUND], "seed": cfg.seed,
            "verbose": -9, "verb_log": 0, "verb_disp": 0}


# --- the run -------------------------------------------------------------------------------------------------

def start(cfg: CmaConfig, run_dir: Path) -> dict:
    """Claim run_dir for a fresh run: config.json, the generation-0 checkpoint and status. Returns the state."""
    cfg.check()
    run_dir = Path(run_dir)
    if evo._holds_run(run_dir):
        raise evo.RunExistsError(f"run folder {run_dir} already holds a run (use --resume to continue it)")
    run_dir.mkdir(parents=True, exist_ok=True)
    config = evo._run_config(cfg)
    config.update({"method": METHOD, "dim": DIM, "bound": BOUND, "decimals": DECIMALS,
                   "layout": [[gp.TREE_NAMES[t], term] for t, term in LAYOUT], "cma_version": cma.__version__})
    evo._write_json(run_dir / evo.CONFIG, config)
    random.seed(cfg.seed)
    es = cma.CMAEvolutionStrategy(list(X0[cfg.x0]), cfg.sigma0, cma_options(cfg))  # seeds numpy's global RNG
    conv = Convergence(cfg.min_gens, cfg.patience, cfg.min_gain_frac, cfg.min_gain_trips, sig_alpha=cfg.sig_alpha)
    state = {"format": evo.CHECKPOINT_FORMAT, "method": METHOD, "generation": 0,
             "es": pickle.dumps(es, protocol=pickle.HIGHEST_PROTOCOL), "np_rng": np.random.get_state(),
             "rng": random.getstate(), "convergence": conv.state(), "validated": {}, "elapsed_s": 0.0,
             "games_played": 0, "cache_hits": 0}
    for name in (evo.GENERATIONS, evo.VALIDATION):
        (run_dir / name).write_bytes(b"")
    evo.write_checkpoint(run_dir, state)
    evo._write_status(run_dir, "running", "started", state)
    return state


def load(run_dir: Path, overrides: dict | None = None) -> tuple[CmaConfig, dict]:
    """Config and checkpoint of an existing CMA-ES run (evolve.load's rules: only workers and budgets change)."""
    run_dir = Path(run_dir)
    config_path = run_dir / evo.CONFIG
    if (run_dir / evo.CHECKPOINT).exists() and config_path.exists():
        method = json.loads(config_path.read_text(encoding="utf-8")).get("method")
        if method != METHOD:
            raise ValueError(f"{run_dir} holds a {method or 'GP'} run, not a {METHOD} run")
    return evo.load(run_dir, overrides, config_cls=CmaConfig)


def rank_values(texts: list[str], fitness: dict) -> list[float]:
    """CMA-ES values (minimised): per candidate, how many candidates are strictly better by fitness."""
    return [float(sum(1 for u in texts if fitness[u] > fitness[t])) for t in texts]


def generation(cfg: CmaConfig, state: dict, engine, run_dir: Path, clock=time.monotonic) -> dict:
    """Play one generation, append its records and return the next state (not yet checkpointed)."""
    t0 = clock()
    played0, hits0 = engine.games_played, engine.cache_hits
    gen = state["generation"]
    random.setstate(state["rng"])
    np.random.set_state(state["np_rng"])
    es = pickle.loads(state["es"])  # our own checkpoint bytes

    seeds = random.sample(range(cfg.train_lo, cfg.train_hi + 1), cfg.n_train)
    xs = es.ask()
    texts = [weights_to_text(x) for x in xs]
    distinct = list(dict.fromkeys(texts))
    n = cfg.n_train
    games = engine.play([(t, s) for t in distinct for s in seeds])
    by = {t: games[i * n:(i + 1) * n] for i, t in enumerate(distinct)}
    fitness = {t: evo._means(by[t]) for t in distinct}
    es.tell(xs, rank_values(texts, fitness))
    cma_stop = sorted(str(k) for k in es.stop())

    sizes = {t: SIZE for t in distinct}
    best = evo.rank(distinct, fitness, sizes)[0]
    validated = dict(state["validated"])
    new = best not in validated
    if new:
        record = evo._validate(cfg, engine, gen, best, SIZE)
        evo._append_jsonl(run_dir / evo.VALIDATION, record)
        validated[best] = {"mean": record["mean"], "mean_seconds": record["mean_seconds"], "gen": gen,
                           "trips": record["trips"]}
    v = validated[best]
    conv = Convergence.from_state(state["convergence"])
    improved = conv.observe(gen, best, v["mean"], v["mean_seconds"], SIZE, trips=v.get("trips"))

    wall = clock() - t0
    played, hits = engine.games_played - played0, engine.cache_hits - hits0
    tiles = sum(g.get("tiles_built", 0) for g in by[best])
    inc = conv.incumbent
    rec = {
        "gen": gen, "seeds": seeds, "distinct": len(distinct),
        "train": evo._stats([fitness[t][0] for t in texts]),
        "best": {"hash": evo.text_hash(best), "size": SIZE, "train_mean": fitness[best][0],
                 "train_seconds": fitness[best][1],
                 "trips_per_tile": (sum(g["trips"] for g in by[best]) / tiles) if tiles > 0 else 0.0},
        "sigma": float(es.sigma), "cma_stop": cma_stop,
        "validated": {"hash": evo.text_hash(best), "new": new, "mean": v["mean"], "mean_seconds": v["mean_seconds"]},
        "improved": improved,
        "incumbent": {"hash": inc["hash"], "mean": inc["mean"], "mean_seconds": inc["mean_seconds"],
                      "size": inc["size"], "gen": inc["gen"]},
        "anchor": conv.anchor, "required_gain": conv.required_gain(), "gens_since_improvement": conv.since,
        "wall_s": wall, "games_played": played, "cache_hits": hits,
    }
    evo._append_jsonl(run_dir / evo.GENERATIONS, rec)
    evo._atomic_write(run_dir / evo.BEST, (inc["text"] + "\n").encode("utf-8"))
    evo._write_json(run_dir / WEIGHTS, weights_by_tree(text_to_weights(inc["text"])))
    return {**state, "generation": gen + 1, "es": pickle.dumps(es, protocol=pickle.HIGHEST_PROTOCOL),
            "np_rng": np.random.get_state(), "rng": random.getstate(), "convergence": conv.state(),
            "validated": validated, "elapsed_s": state["elapsed_s"] + wall,
            "games_played": state["games_played"] + played, "cache_hits": state["cache_hits"] + hits}


def format_record(rec: dict, cfg: CmaConfig) -> str:
    """The one line printed per generation."""
    v, inc = rec["validated"], rec["incumbent"]
    return (f"gen {rec['gen']:3d} | train best {rec['train']['best']:6.1f} mean {rec['train']['mean']:6.1f} | "
            f"sigma {rec['sigma']:.3f} | val {v['mean']:6.1f}{' new' if v['new'] else ' old'}"
            f"{' +' if rec['improved'] else ''} | incumbent {inc['mean']:6.1f} (gen {inc['gen']}) | "
            f"since {rec['gens_since_improvement']}/{cfg.patience} | {rec['wall_s']:.0f} s, "
            f"{rec['games_played']} games, {rec['cache_hits']} hits")


def open_run(cfg: CmaConfig | None, run_dir: Path, resume: bool = False,
             overrides: dict | None = None) -> tuple[CmaConfig, dict]:
    """Start a fresh run (needs cfg) or, with resume, load one (takes only `overrides`); (config, state)."""
    if resume:
        return load(Path(run_dir), overrides)
    return cfg, start(cfg, Path(run_dir))


def play_run(cfg: CmaConfig, state: dict, run_dir: Path, engine=None, clock=time.monotonic, log=print) -> dict:
    """Play an opened run to its stop with evolve's loop (stop rule, budget, checkpoints); returns the status."""
    run_dir = Path(run_dir)
    own = engine is None
    if own:
        engine = Engine(workers=cfg.workers, cap_s=cfg.cap_s, cache_path=run_dir / evo.CACHE)
    try:
        return evo.run_loop(cfg, state, engine, run_dir, clock=clock, log=log, step=generation, fmt=format_record)
    finally:
        if own:
            engine.close()


def tune(cfg: CmaConfig | None, run_dir: Path, resume: bool = False, overrides: dict | None = None,
         engine=None, clock=time.monotonic, log=print) -> dict:
    """Start (or with resume, continue) the run in run_dir and play it to its stop; returns the status."""
    cfg, state = open_run(cfg, run_dir, resume=resume, overrides=overrides)
    return play_run(cfg, state, run_dir, engine=engine, clock=clock, log=log)


# --- CLI -----------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evolved_rules.tune_cmaes", description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="run folder name under output/evolved_rules/cmaes")
    parser.add_argument("--resume", action="store_true", help="continue the run from its checkpoint")
    d = CmaConfig()
    # Defaults are None so a resume can tell an option given on the command line from one left out.
    parser.add_argument("--workers", type=int, help=f"host processes (default {d.workers})")
    parser.add_argument("--popsize", type=int, help=f"CMA-ES population (default {d.popsize})")
    parser.add_argument("--seed", type=int, help=f"RNG seed, at least 1 (default {d.seed})")
    parser.add_argument("--sigma0", type=float, help=f"initial step size (default {d.sigma0:g})")
    parser.add_argument("--x0", choices=tuple(X0), help=f"initial mean (default {d.x0})")
    parser.add_argument("--n-train", type=int, help=f"training seeds per generation (default {d.n_train})")
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
            given["validation"] = evo.parse_validation(given["validation"])
        cfg = None if args.resume else CmaConfig(**given)
        if cfg is not None:
            cfg.check()
    except ValueError as e:
        parser.error(str(e))
    run_dir = CMAES_DIR / args.run
    try:
        cfg, state = open_run(cfg, run_dir, resume=args.resume, overrides=given if args.resume else None)
    except evo.RunExistsError as e:
        print(str(e), file=sys.stderr)
        return evo.EXISTING_RUN_EXIT_CODE
    except (FileNotFoundError, ValueError) as e:
        if not args.resume:
            raise
        print(f"cannot resume: {e}", file=sys.stderr)
        return evo.EXISTING_RUN_EXIT_CODE
    status = play_run(cfg, state, run_dir)
    inc = status.get("incumbent") or {}
    print(f"{run_dir}: {status['status']} after {status['generations']} generations; incumbent "
          f"{inc.get('mean', float('nan')):.1f} trips (gen {inc.get('gen')}), best.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["CmaConfig", "Convergence", "stop_reason", "LAYOUT", "DIM", "BOUND", "DECIMALS", "SIZE", "snap",
           "weights_to_text", "text_to_weights", "weights_from", "weights_by_tree", "HAND_WEIGHTS",
           "SEPARATED_WEIGHTS", "X0", "cma_options", "rank_values", "start", "load", "generation", "open_run",
           "play_run", "tune", "main", "CMAES_DIR"]
