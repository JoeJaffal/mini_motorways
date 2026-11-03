"""GP evolution loop with racing, elitism, a validation incumbent and a convergence stop (Phase 2 Task 5).

    PY -m evolved_rules.evolve --run NAME [--resume] [--workers 10] [--pop 64] [--seed 1] [--min-gens 30]
        [--patience 20] [--min-gain-frac 0.02] [--min-gain-trips 3] [--max-hours 72] [--max-gens 400]
        [--validation 1500-1549] [--cap 3600] [--first-seeds 8] [--more-seeds 24] [--racing-top 16]
        [--validate-top 3] [--immigrants 8] [--sig-alpha 0.005] [--no-dedup] [--remove-tree] [--seed-text FILE]
        [--hof 8 --reference FILE [--hof-se 1]]

One generation (decisions P2-1..P2-4 of plans/2026-11-01-phase2-evolution.md, as changed for gp-2 in
EXPERIMENTS.md; the gp-1 values are in brackets, and --first-seeds 4 --more-seeds 8 --validate-top 1
--sig-alpha 0 --no-dedup runs gp-1's loop exactly, though its random trees differ: gp.DROPPED_TERMS changed
the terminal set):

1. Draw n_s4 + n_s8 = 8 + 24 [4 + 8] training seeds from LA 1-999 with the run's RNG. (The names S4/S8 and
   the records' "s4"/"s8" keys date from gp-1: they mean the first-round and the extra second-round seeds.)
2. Every distinct tree text in the population plays the first-round seeds. Its fitness is (mean trips, mean
   seconds) there, compared lexicographically; ties go to the smaller individual (parsimony), then to the
   earlier text. Fitnesses are never carried over: every generation scores everyone, elites included.
3. Behavioural de-duplication [off]: texts whose first-round games are identical (trips, seconds, commands on
   every seed) count once (the best-ranked, i.e. the smallest, represents them) in steps 4-6.
4. The top 16 representatives by first-round fitness also play the extra seeds. Their racing score is the
   mean over all 32 [12] games.
5. The best 3 [1] by racing score are validated on the fixed validation seeds (LA 1500-1549), in one batch,
   unless a text was validated before (validation is cached by text). The incumbent is the best validated
   individual so far, by (validation mean trips, mean seconds, -size); it is the run's final model (best.txt).
   Because it is the maximum of many noisy validation means, report its score on held-out seeds.
6. Next population: the 3 best representatives by racing score unchanged (elitism), then offspring:
   tournament (size 4, with replacement) over the representatives on first-round fitness with parsimony,
   then DEAP's varAnd scheme: crossover of consecutive pairs with probability 0.5, then mutation of each
   offspring with probability 0.3 (gp.mate / gp.mutate keep every tree within the depth limit of 6). With
   de-duplication an offspring that repeats a text is mutated again, and each behavioural duplicate found
   buys one fresh random immigrant in the last slots (at most `immigrants`, and at least one offspring).

Hall of fame (gp-3.3, hof > 0; plans/2026-11-03-gp33-hall-of-fame.md). gp-3.2 lost its best rule to one bad 8-seed
first round and drifted to rules that are lucky on 32 seeds. With hof > 0, steps 5 and 6 change:
- A fixed reference rule (reference_text) plays all n_s4 + n_s8 training seeds of every generation. A rule's
  score on a seed is its trips minus the reference's there, which removes seed difficulty, so scores from
  different generations can be pooled.
- The hall's members play every generation's training seeds too and keep all their per-seed differences.
  Candidates are the members, the racing top and the reference; the hall ranks them by a lower confidence bound,
  mean difference - hof_se * its standard error, then mean, then -size. A newcomer's first differences leave out
  the first-round seeds it was picked on. Candidates with identical games this generation count once (a member
  first, then the reference), and the best `hof` form the next hall. Texts that leave the hall keep their record
  in an archive, so a text that comes back does not start afresh.
- Probation: the elites are the hall's re-tested members first (members since an earlier generation), then the
  rest of the hall, then the racing top; the validated individuals are its top `validate_top` re-tested members.
  Breeding is unchanged. Generation 0's hall is the reference and the seed texts (they count as re-tested).
hof = 0 is the loop above exactly (checkpoint format 3); hof > 0 writes format 4.

Stop rule (P2-1, class Convergence; tune_cmaes.py uses the same class, stop_reason and run_loop). A validated
individual counts as an improvement when its mean is at least `anchor + max(min_gain_trips, min_gain_frac *
anchor)` and strictly above the anchor, where the anchor is the validated mean at the last counted improvement
(generation 0 sets it); with sig_alpha > 0 [0] it must also beat the anchor individual seed by seed (one-sided
paired t on the validation seeds, level sig_alpha), because a 50-seed mean is itself uncertain by about +-13
trips. The strict part only matters when both minimum gains are 0: re-validating the anchor's own (cached)
text must not reset the count. Measuring gains from the anchor, not from the moving incumbent, means a slow
creep of small gains still adds up to an improvement once it is big enough, while noise-sized wiggles never
reset the count. The run has converged when at least min_gens generations are done and the last `patience`
generations brought no improvement. The backstop (max_gens generations or max_hours of wall clock, summed
over resumes) stops the run as `budget`, never as converged.

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
import math
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
from .power import keep_awake

EVOLVE_DIR = ROOT / "output" / "evolved_rules" / "evolve"  # /output/ is git-ignored
# 2 (gp-2): per-seed validation trips in the state, the stop rule's significance test, the terminal set without
# gp.DROPPED_TERMS. A format-1 run (gp-1) can only be resumed with the code it was made with (commit 49c8197).
# 3 (gp-3 code): the terminal sets grew (traffic inputs) and individuals may have 4 trees, so a format-2 run (gp-2)
# would draw different random trees here; resume it with the code of commit b8e82a0.
CHECKPOINT_FORMAT = 3
# 4 (gp-3.3): a run with a hall of fame (hof > 0) also checkpoints the hall; older code must refuse it, since it
# would resume the run without one.
HOF_CHECKPOINT_FORMAT = 4
EXISTING_RUN_EXIT_CODE = 2
# Config fields whose command-line flag is not simply --field-name (for error messages)
FLAG_NAMES = {"n_s4": "--first-seeds", "n_s8": "--more-seeds", "dedup": "--no-dedup", "seed_texts": "--seed-text",
              "remove_tree": "--remove-tree", "cap_s": "--cap", "reference_text": "--reference"}
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
    # The field names n_s4 / n_s8 (and the records' "s4"/"s8" keys) date from gp-1, which used 4 + 8 seeds; they
    # mean "first-round seeds" and "extra seeds of the racing top". gp-2 defaults (EXPERIMENTS.md): 8 + 24.
    n_s4: int = 8  # seeds every individual plays (first round)
    n_s8: int = 24  # extra seeds the racing top plays (second round)
    racing_top: int = 16
    elites: int = 3
    tournament: int = 4
    cxpb: float = 0.5
    mutpb: float = 0.3
    train_lo: int = 1  # training seeds are drawn from train_lo..train_hi (inclusive)
    train_hi: int = 999
    validate_top: int = 3  # how many of the racing top are validated per generation (gp-1: 1)
    dedup: bool = True  # behavioural de-duplication and unique texts in the next population (gp-1: off)
    immigrants: int = 8  # at most this many fresh random individuals per generation, one per duplicate found
    sig_alpha: float = 0.005  # stop rule's one-sided paired-test level (0: mean gain only, the gp-1 rule)
    # gp-3 (plans/2026-11-03-gp3-traffic.md): 4-tree individuals (a remove tree; clean routes and removals on)
    remove_tree: bool = False
    seed_texts: tuple[str, ...] = ()  # extra individuals for generation 0 (3-tree texts get remove = -1)
    # gp-3.3 (plans/2026-11-03-gp33-hall-of-fame.md): a hall of fame re-tested every generation (0: off)
    hof: int = 0
    reference_text: str = ""  # the rule whose per-seed trips are subtracted (needed with hof)
    hof_se: float = 1.0  # the hall ranks by mean difference - hof_se * standard error

    def check(self) -> None:
        """ValueError for a parameter the loop cannot run with."""
        def need(ok: bool, what: str) -> None:
            if not ok:
                raise ValueError(what)

        ints = ("pop", "seed", "min_gens", "patience", "max_gens", "workers", "n_s4", "n_s8", "racing_top",
                "elites", "tournament", "train_lo", "train_hi", "validate_top", "immigrants", "hof")
        for name in ints:
            v = getattr(self, name)
            need(isinstance(v, int) and not isinstance(v, bool), f"{name} must be an int, got {v!r}")
        need(isinstance(self.dedup, bool), f"dedup must be a bool, got {self.dedup!r}")
        need(isinstance(self.remove_tree, bool), f"remove_tree must be a bool, got {self.remove_tree!r}")
        need(isinstance(self.seed_texts, tuple) and all(isinstance(s, str) for s in self.seed_texts),
             "seed_texts must be a tuple of individual texts")
        for s in self.seed_texts:
            try:
                ind = gp.individual_from_text(s)
            except ValueError as e:
                raise ValueError(f"bad seed text: {e}") from None
            need(len(ind) == 3 or self.remove_tree, "a 4-tree seed text needs remove_tree")
        need(self.hof >= 0, f"hof must be >= 0, got {self.hof}")
        need(isinstance(self.reference_text, str), "reference_text must be an individual text")
        need(isinstance(self.hof_se, (int, float)) and not isinstance(self.hof_se, bool)
             and math.isfinite(self.hof_se) and self.hof_se >= 0, f"hof_se must be a finite number >= 0, got "
             f"{self.hof_se!r}")
        if self.hof:
            need(bool(self.reference_text.strip()), "hof needs a reference_text (--reference)")
            try:
                ref = gp.individual_from_text(self.reference_text)
            except ValueError as e:
                raise ValueError(f"bad reference text: {e}") from None
            need(len(ref) == 3 or self.remove_tree, "a 4-tree reference text needs remove_tree")
            need(self.hof >= self.elites and self.hof >= self.validate_top,
                 f"hof ({self.hof}) must be at least elites ({self.elites}) and validate_top ({self.validate_top}): "
                 f"both come from the hall")
            need(self.n_s8 >= 2, f"hof needs at least 2 extra seeds (--more-seeds), got {self.n_s8}: a newcomer is "
                 f"scored on those only, and a lower bound needs two")
        else:
            need(not self.reference_text, "reference_text is only used with hof > 0")
        need(1 <= self.validate_top <= self.racing_top,
             f"validate_top must be in 1..racing_top ({self.racing_top}), got {self.validate_top}")
        need(self.immigrants >= 0, f"immigrants must be >= 0, got {self.immigrants}")  # breed caps it per generation
        need(isinstance(self.sig_alpha, (int, float)) and 0.0 <= self.sig_alpha < 0.5,
             f"sig_alpha must be in [0, 0.5), got {self.sig_alpha!r}")
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
        d["seed_texts"] = list(self.seed_texts)
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Config":
        known = {f.name for f in fields(cls)}
        kw = {k: v for k, v in d.items() if k in known}
        kw["validation"] = tuple(kw.get("validation", ()))
        kw["seed_texts"] = tuple(kw.get("seed_texts", ()))
        return cls(**kw)

    @property
    def trees(self) -> int:
        return 4 if self.remove_tree else 3


# --- the stop rule (shared with tune_cmaes.py) ---------------------------------------------------------------

def _validation_key(mean: float, mean_seconds: float, size: int) -> tuple:
    return (mean, mean_seconds, -size)


def paired_t(trips: list, anchor_trips: list) -> float:
    """One-sample t statistic of the per-seed differences trips - anchor_trips (same validation seeds).

    +inf / -inf / 0 when every difference is equal (no spread) and positive / negative / zero.
    """
    d = [float(a) - float(b) for a, b in zip(trips, anchor_trips)]
    mean = statistics.fmean(d)
    sd = statistics.stdev(d) if len(d) > 1 else 0.0
    if sd == 0.0:
        return math.inf if mean > 0 else (-math.inf if mean < 0 else 0.0)
    return mean / (sd / math.sqrt(len(d)))


def critical_t(alpha: float, n: int) -> float:
    """One-sided critical t for n paired differences (Student t, n - 1 degrees of freedom); 0 when alpha is 0."""
    if alpha <= 0:
        return 0.0
    if n < 2:
        return math.inf  # one seed cannot show a significant gain
    from scipy.stats import t as student_t
    return float(student_t.ppf(1.0 - alpha, n - 1))


@dataclass
class Convergence:
    """The stop rule of decision P2-1 and the validation incumbent (see the module docstring).

    observe() / observe_many() are called once per generation with that generation's validated individuals (a
    text seen before passes its cached scores: it can never count twice, since a counted improvement moves the
    anchor up to its mean and the next one must be strictly above it).

    sig_alpha > 0 (gp-2 onwards) adds a significance test. A candidate counts only if it also beats the anchor
    individual seed by seed: the one-sided paired t of (candidate - anchor) trips on the validation seeds must
    reach the critical t for sig_alpha. Why: a 50-seed validation mean is itself noisy (per-seed SD about 90
    trips, so about +-13), far more than a 2% margin (about 4 trips), so without the test luck alone would count
    as an improvement in most generations and the run would never converge (gp-1 finding, EXPERIMENTS.md). With
    sig_alpha = 0 the rule is exactly the gp-1 rule (mean gain only).
    """

    min_gens: int
    patience: int
    min_gain_frac: float
    min_gain_trips: float
    sig_alpha: float = 0.0  # one-sided significance level of the paired test (0: no test, the gp-1 rule)
    generations: int = 0  # generations observed
    since: int = 0  # generations since the last counted improvement
    anchor: float | None = None  # incumbent's validation mean at the last counted improvement
    anchor_trips: list | None = None  # the anchor individual's per-seed validation trips (for the paired test)
    incumbent: dict | None = None  # {"text", "hash", "mean", "mean_seconds", "size", "gen"}

    def required_gain(self) -> float:
        """Smallest gain over the anchor that counts as an improvement (min_gain_trips before any anchor)."""
        if self.anchor is None:
            return float(self.min_gain_trips)
        return max(float(self.min_gain_trips), self.min_gain_frac * self.anchor)

    def test(self, mean: float, trips: list | None = None) -> dict:
        """How a validated individual compares with the anchor: {"gain", "t", "t_crit", "counts"}.

        Before any anchor everything counts. With sig_alpha > 0 the paired test needs per-seed trips on the
        anchor's seeds; when they are missing (a caller with means only) only the mean gain decides.
        """
        if self.anchor is None:
            return {"gain": None, "t": None, "t_crit": None, "counts": True}
        gain = mean - self.anchor  # for the record only: the decision below uses gp-1's exact expression
        enough = mean >= self.anchor + self.required_gain() and mean > self.anchor  # same rounding as gp-1
        t = t_crit = None
        if self.sig_alpha > 0 and trips is not None and self.anchor_trips is not None \
                and len(trips) == len(self.anchor_trips):
            t = paired_t(trips, self.anchor_trips)
            t_crit = critical_t(self.sig_alpha, len(trips))
            # an infinite critical t (a single seed) can never be reached, not even by an infinite t
            enough = enough and math.isfinite(t_crit) and t >= t_crit
        return {"gain": gain, "t": t, "t_crit": t_crit, "counts": enough}

    def observe_many(self, gen: int, cands: list[dict]) -> bool:
        """Record one generation's validated individuals; True when one of them counts as an improvement.

        cands: dicts with text, mean, mean_seconds, size and (for the paired test) trips. Every candidate can
        become the incumbent (best by mean, seconds, -size). Of those that count, the best by the same key
        becomes the new anchor. Each candidate's comparison is stored under "test" in its dict.
        """
        if not cands:
            raise ValueError("observe_many needs at least one validated individual")
        for c in cands:
            c["test"] = self.test(c["mean"], c.get("trips"))
        for c in cands:
            key = _validation_key(c["mean"], c["mean_seconds"], c["size"])
            inc = self.incumbent
            if inc is None or key > _validation_key(inc["mean"], inc["mean_seconds"], inc["size"]):
                self.incumbent = {"text": c["text"], "hash": text_hash(c["text"]), "mean": c["mean"],
                                  "mean_seconds": c["mean_seconds"], "size": c["size"], "gen": gen}
        counting = [c for c in cands if c["test"]["counts"]]
        if counting:
            best = max(counting, key=lambda c: _validation_key(c["mean"], c["mean_seconds"], c["size"]))
            self.anchor = best["mean"]
            self.anchor_trips = list(best["trips"]) if best.get("trips") is not None else None
            self.since = 0
        else:
            self.since += 1
        self.generations += 1
        return bool(counting)

    def observe(self, gen: int, text: str, mean: float, mean_seconds: float, size: int,
                trips: list | None = None) -> bool:
        """Record one generation's single validated individual; True when it counts as an improvement."""
        return self.observe_many(gen, [{"text": text, "mean": mean, "mean_seconds": mean_seconds, "size": size,
                                        "trips": trips}])

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
        test = f" passing the paired test at alpha {conv.sig_alpha:g}" if conv.sig_alpha > 0 else ""
        return "converged", (f"no validation gain of at least {conv.required_gain():.2f} trips over "
                             f"{conv.anchor:.2f}{test} in the last {conv.since} generations "
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


UNIQUE_TRIES = 10  # extra mutations tried to make an offspring's text differ from every text already kept


def breed(population: list[str], fitness: dict, sizes: dict, elites: list[str], cfg: Config,
          immigrants: int = 0) -> list[str]:
    """Next population (canonical texts): elites unchanged, varied tournament winners, then fresh immigrants.

    immigrants (capped at pop - len(elites) - 1, so at least one offspring remains) fresh random individuals take
    the last slots. With cfg.dedup an offspring whose text is already in the next population is mutated again
    (up to UNIQUE_TRIES times) so the population holds no exact copies. With dedup off and no immigrants this
    is exactly the gp-1 scheme, draw for draw.
    """
    immigrants = max(0, min(immigrants, cfg.pop - len(elites) - 1))
    picks = [tournament(population, fitness, sizes, cfg.tournament)
             for _ in range(cfg.pop - len(elites) - immigrants)]
    offspring = [gp.individual_from_text(t) for t in picks]  # fresh trees: mate and mutate work in place
    for i in range(1, len(offspring), 2):
        if random.random() < cfg.cxpb:
            gp.mate(offspring[i - 1], offspring[i])
    for ind in offspring:
        if random.random() < cfg.mutpb:
            gp.mutate(ind)
    out = list(elites)
    seen = set(out)
    for ind in offspring:
        text = gp.individual_text(ind)
        if cfg.dedup:
            for _ in range(UNIQUE_TRIES):
                if text not in seen:
                    break
                gp.mutate(ind)
                text = gp.individual_text(ind)
        out.append(text)
        seen.add(text)
    for _ in range(immigrants):
        text = gp.individual_text(gp.random_individual(trees=cfg.trees))
        for _ in range(UNIQUE_TRIES):
            if text not in seen:
                break
            text = gp.individual_text(gp.random_individual(trees=cfg.trees))
        out.append(text)
        seen.add(text)
    return out


def behaviours(texts: list[str], games: dict, fitness: dict, sizes: dict) -> list[str]:
    """One representative per behaviour: texts whose games on the round's seeds are identical (same trips,
    seconds and commands on every seed) play the same way there and count once. The representative is the
    first by rank (best fitness, then smallest, then first appearance); the result keeps that rank order."""
    reps: dict[tuple, str] = {}
    for t in rank(texts, fitness, sizes):
        sig = tuple((g["trips"], g["seconds"], g.get("commands")) for g in games[t])
        reps.setdefault(sig, t)
    return list(reps.values())


def initial_population(cfg: Config) -> list[str]:
    """The hand rule, the separated preference, then random individuals (P2-9), from the global `random`.

    With remove_tree (gp-3): those two and the clean rule (gp.CLEAN_TEXT), then cfg.seed_texts, all as 4-tree
    texts (a 3-tree text gets remove = -1, never), then 4-tree random individuals. Repeated texts are kept once.
    """
    if not cfg.remove_tree:
        texts = [gp.individual_text(gp.individual_from_text(gp.HAND_TEXT)),
                 gp.individual_text(gp.individual_from_text(gp.SEPARATED_TEXT))]
        texts += [gp.individual_text(gp.individual_from_text(s)) for s in cfg.seed_texts]
    else:
        texts = [gp.with_remove(s) for s in (gp.HAND_TEXT, gp.SEPARATED_TEXT, gp.CLEAN_TEXT, *cfg.seed_texts)]
    texts = list(dict.fromkeys(texts))[:cfg.pop]
    while len(texts) < cfg.pop:
        texts.append(gp.individual_text(gp.random_individual(trees=cfg.trees)))
    return texts


def canonical(cfg: Config, text: str) -> str:
    """text as the population writes it (initial_population's form: with remove_tree, always 4 trees)."""
    return gp.with_remove(text) if cfg.remove_tree else gp.individual_text(gp.individual_from_text(text))


def initial_hof(cfg: Config) -> list[dict]:
    """Generation 0's hall of fame: the reference, then the seed texts, each with no differences yet."""
    texts = dict.fromkeys(canonical(cfg, t) for t in (cfg.reference_text, *cfg.seed_texts))
    return [{"text": t, "diffs": {}, "gen": 0} for t in texts]


def hof_score(diffs: dict, se_weight: float) -> tuple[float, float]:
    """(mean, lower bound) of a rule's per-seed differences from the reference: mean - se_weight * standard
    error. With fewer than 2 seeds the error is unknown and the bound is -inf."""
    d = list(diffs.values())
    mean = float(statistics.fmean(d))
    if len(d) < 2:
        return mean, -math.inf
    return mean, mean - se_weight * statistics.stdev(d) / math.sqrt(len(d))


HOF_ROUND = 9  # bounds and means are compared rounded, so float noise cannot break an exact tie


def update_hof(cfg: Config, hof: list[dict], ranked: list[str], games: dict, ref: str, seeds: list,
               sizes: dict, gen: int, skip_new: int = 0,
               archive: dict | None = None) -> tuple[list[dict], list[dict], dict]:
    """The next hall of fame, its records and the updated archive (plans/2026-11-03-gp33-hall-of-fame.md).

    hof: the current members ({"text", "diffs": {seed: trips - reference trips}, "gen": generation joined}).
    ranked: the racing top, best first. games: every candidate's games on `seeds` (in that order), the
    reference's included. archive: the records of texts that left the hall or never got in ({text: {"diffs",
    "gen"}}), so a text that comes back keeps its record instead of starting afresh.

    Candidates whose games this generation are identical count once, chosen before any ranking: a member (the
    longest record first) over the reference over the racing top (in its order), so a copy that is lucky on a
    short record cannot replace a member's long one. Each candidate adds this generation's differences to its
    record; a text that was not a member skips the first `skip_new` seeds (the racing top was picked on the
    first-round seeds, so its games there flatter it). They are ranked by (lower bound, mean, -size), rounded to
    HOF_ROUND places; the sort is stable, so full ties keep candidate order. The best cfg.hof form the hall.
    Each record says whether the text was already a member ("tested": it has been re-tested since it joined).
    """
    archive = dict(archive or {})
    ref_trips = [g["trips"] for g in games[ref]]
    old = {m["text"]: m for m in hof}
    members = sorted(old, key=lambda t: -len(old[t]["diffs"]))  # stable: equal records keep hall order
    def record(t: str) -> tuple[dict, int]:
        prev = old.get(t) or archive.get(t)
        diffs = dict(prev["diffs"]) if prev else {}
        first = 0 if t in old else skip_new
        for s, g, r in zip(seeds[first:], games[t][first:], ref_trips[first:]):
            diffs[s] = float(g["trips"] - r)  # a seed drawn again plays the same game: same difference
        return diffs, (prev["gen"] if prev else gen)

    chosen, seen = [], set()
    for t in dict.fromkeys([*members, ref, *ranked]):
        sig = tuple((g["trips"], g["seconds"], g.get("commands")) for g in games[t])
        if sig not in seen:
            seen.add(sig)
            chosen.append(t)
        elif t in old or t in archive:  # a copy with a record of its own keeps it, in the archive
            diffs, joined = record(t)
            archive[t] = {"diffs": diffs, "gen": joined}
    cands = []
    for t in chosen:
        diffs, joined = record(t)
        mean, lcb = hof_score(diffs, cfg.hof_se)
        cands.append({"text": t, "diffs": diffs, "gen": joined, "mean": mean, "lcb": lcb, "size": sizes[t],
                      "tested": t in old})
    cands.sort(key=lambda c: (round(c["lcb"], HOF_ROUND), round(c["mean"], HOF_ROUND), -c["size"]), reverse=True)
    kept, dropped = cands[:cfg.hof], cands[cfg.hof:]
    for c in kept:
        archive.pop(c["text"], None)
    for c in dropped:
        archive[c["text"]] = {"diffs": c["diffs"], "gen": c["gen"]}
    hall = [{"text": c["text"], "diffs": c["diffs"], "gen": c["gen"]} for c in kept]
    rows = [{"hash": text_hash(c["text"]), "size": c["size"], "gen": c["gen"], "tested": c["tested"],
             "seeds": len(c["diffs"]), "mean_diff": c["mean"], "lcb": _num(c["lcb"]),
             "trips": float(statistics.fmean(g["trips"] for g in games[c["text"]]))} for c in kept]
    return hall, rows, archive


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
    if state.get("format") not in (CHECKPOINT_FORMAT, HOF_CHECKPOINT_FORMAT):
        hint = {1: " (a gp-1 run: resume it with the code of commit 49c8197)",
                2: " (a gp-2 run: resume it with the code of commit b8e82a0)"}.get(state.get("format"), "")
        raise ValueError(f"checkpoint format {state.get('format')!r}, expected {CHECKPOINT_FORMAT} or "
                         f"{HOF_CHECKPOINT_FORMAT}{hint}")
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
    conv = Convergence(cfg.min_gens, cfg.patience, cfg.min_gain_frac, cfg.min_gain_trips, sig_alpha=cfg.sig_alpha)
    state = {"format": CHECKPOINT_FORMAT, "generation": 0, "population": population, "rng": random.getstate(),
             "convergence": conv.state(), "validated": {}, "elapsed_s": 0.0, "games_played": 0,
             "cache_hits": 0}
    if cfg.hof:
        state["format"] = HOF_CHECKPOINT_FORMAT
        state["hof"], state["hof_archive"] = initial_hof(cfg), {}
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
    defaults = config_cls().to_json()  # a run made before a field existed ran with its default
    changed = {}
    for name, value in (overrides or {}).items():
        if isinstance(value, tuple):
            value = list(value)  # config.json holds lists
        if value is None or params.get(name, defaults.get(name)) == value:
            continue
        if name not in RESUMABLE_FIELDS:
            flag = FLAG_NAMES.get(name, "--" + name.replace("_", "-"))
            raise ValueError(f"{flag} {value!r} differs from the saved run "
                             f"({params.get(name)!r}); only {', '.join(RESUMABLE_FIELDS)} may change on resume")
        changed[name] = value
    params.update(changed)
    cfg = config_cls.from_json(params)
    cfg.check()
    state = read_checkpoint(run_dir)
    if (state["format"] == HOF_CHECKPOINT_FORMAT) != bool(getattr(cfg, "hof", 0)):
        raise ValueError(f"checkpoint format {state['format']} does not match hof = {getattr(cfg, 'hof', 0)} "
                         f"in {run_dir / CONFIG}")
    for name in (GENERATIONS, VALIDATION):
        _trim_jsonl(run_dir / name, state["generation"])
    (run_dir / "error.txt").unlink(missing_ok=True)  # a failure being resumed is no longer the run's state
    config["params"] = cfg.to_json()
    config.setdefault("resumes", []).append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                             "generation": state["generation"], "changed": changed})
    _write_json(run_dir / CONFIG, config)
    return cfg, state


def _num(x):
    """A finite float, or None (JSON has no infinity; a paired t is infinite when every difference is equal)."""
    return None if x is None or not math.isfinite(x) else x


def _validate(cfg: Config, engine, gen: int, text: str, size: int) -> dict:
    """Play text on the validation seeds; returns its validation.jsonl record."""
    return _validate_many(cfg, engine, gen, [text], {text: size})[0]


def _validate_many(cfg: Config, engine, gen: int, texts: list[str], sizes: dict) -> list[dict]:
    """Play every text on the validation seeds in one batch (all workers busy); their validation records."""
    n = len(cfg.validation)
    games = engine.play([(t, s) for t in texts for s in cfg.validation])
    return [_validation_record(cfg, gen, t, sizes[t], games[i * n:(i + 1) * n]) for i, t in enumerate(texts)]


def _validation_record(cfg: Config, gen: int, text: str, size: int, games: list[dict]) -> dict:
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

    # Behavioural de-duplication: texts that played identical games on the first-round seeds count once, for
    # the racing top, the elites and the tournament alike; each duplicate found buys one immigrant (capped).
    reps = behaviours(distinct, by4, fitness, sizes) if cfg.dedup else distinct
    duplicates = len(distinct) - len(reps)
    top = rank(reps, fitness, sizes)[:cfg.racing_top]
    # With a hall of fame, its members and the reference not in the racing top play every training seed, in the
    # same batch as the racing top's extra seeds (games already played come from the cache).
    ref = canonical(cfg, cfg.reference_text) if cfg.hof else None
    extra = [t for t in dict.fromkeys([*(m["text"] for m in state["hof"]), ref]) if t not in top] if cfg.hof else []
    for t in extra:
        sizes.setdefault(t, gp.size(gp.individual_from_text(t)))
    pairs8 = [(t, s) for t in top for s in s8]
    pairs_x = [(t, s) for t in extra for s in seeds]
    played8 = engine.play(pairs8 + pairs_x) if pairs8 or pairs_x else []
    games8 = played8[:len(pairs8)]
    racing_games = {t: by4[t] + games8[i * cfg.n_s8:(i + 1) * cfg.n_s8] for i, t in enumerate(top)}
    racing = {t: _means(racing_games[t]) for t in top}
    ranked = rank(top, racing, sizes)
    best = ranked[0]
    if cfg.hof:
        n = len(seeds)
        hof_games = {**racing_games, **{t: played8[len(pairs8) + i * n:len(pairs8) + (i + 1) * n]
                                        for i, t in enumerate(extra)}}
        hall, hof_rows, archive = update_hof(cfg, state["hof"], ranked, hof_games, ref, seeds, sizes, gen,
                                             skip_new=cfg.n_s4, archive=state["hof_archive"])
        racing_all = {t: _means(g) for t, g in hof_games.items()}
        # Probation: a text that just joined the hall is ranked by the luckiest of the racing top's records, so
        # elites and validation take re-tested members first (H-5). Elites then fill up from the rest of the hall
        # and the racing top; validation falls back to the hall's top only when no member has been re-tested.
        tested = [m["text"] for m, r in zip(hall, hof_rows) if r["tested"]]
        elites = list(dict.fromkeys([*tested, *(m["text"] for m in hall), *ranked]))[:cfg.elites]
        chosen = tested[:cfg.validate_top] or [m["text"] for m in hall[:cfg.validate_top]]
    else:
        racing_all = racing
        elites = ranked[:cfg.elites]
        chosen = ranked[:cfg.validate_top]

    validated = dict(state["validated"])
    fresh = [t for t in chosen if t not in validated]
    for record in (_validate_many(cfg, engine, gen, fresh, sizes) if fresh else []):
        _append_jsonl(run_dir / VALIDATION, record)
        validated[record["text"]] = {"mean": record["mean"], "mean_seconds": record["mean_seconds"], "gen": gen,
                                     "trips": record["trips"]}
    cands = [{"text": t, "mean": validated[t]["mean"], "mean_seconds": validated[t]["mean_seconds"],
              "size": sizes[t], "trips": validated[t].get("trips"), "new": t in fresh} for t in chosen]
    conv = Convergence.from_state(state["convergence"])
    improved = conv.observe_many(gen, cands)
    top_val = max(cands, key=lambda c: _validation_key(c["mean"], c["mean_seconds"], c["size"]))

    pool = reps if cfg.dedup else population  # gp-1: every copy in the population had its own tournament ticket
    n_immigrants = max(0, min(cfg.immigrants, duplicates, cfg.pop - len(elites) - 1)) if cfg.dedup else 0
    next_population = breed(pool, fitness, sizes, elites, cfg, immigrants=n_immigrants)
    wall = clock() - t0
    played, hits = engine.games_played - played0, engine.cache_hits - hits0
    best_games = racing_games[best]
    tiles = sum(g.get("tiles_built", 0) for g in best_games)
    inc = conv.incumbent
    rec = {
        "gen": gen, "seeds": {"s4": s4, "s8": s8}, "distinct": len(distinct), "behaviours": len(reps),
        "immigrants": n_immigrants,
        "s4": _stats([fitness[t][0] for t in population]),
        "best": {"hash": text_hash(best), "size": sizes[best], "racing_mean": racing[best][0],
                 "racing_seconds": racing[best][1], "s4_mean": fitness[best][0],
                 "trips_per_tile": (sum(g["trips"] for g in best_games) / tiles) if tiles > 0 else 0.0},
        "elites": [text_hash(t) for t in elites],
        # the best validated of this generation (by mean, seconds, -size); validated_all lists each with its test
        "validated": {"hash": text_hash(top_val["text"]), "new": top_val["new"], "mean": top_val["mean"],
                      "mean_seconds": top_val["mean_seconds"]},
        "validated_all": [{"hash": text_hash(c["text"]), "new": c["new"], "mean": c["mean"],
                           "racing_mean": racing_all[c["text"]][0], "gain": c["test"]["gain"],
                           "t": _num(c["test"]["t"]), "t_crit": _num(c["test"]["t_crit"]),
                           "counts": c["test"]["counts"]} for c in cands],
        "improved": improved,
        "incumbent": {"hash": inc["hash"], "mean": inc["mean"], "mean_seconds": inc["mean_seconds"],
                      "size": inc["size"], "gen": inc["gen"]},
        "anchor": conv.anchor, "required_gain": conv.required_gain(), "gens_since_improvement": conv.since,
        "wall_s": wall, "games_played": played, "cache_hits": hits,
    }
    if cfg.hof:
        rec["reference_trips"] = racing_all[ref][0]  # the reference's mean on this generation's training seeds
        rec["hof"] = hof_rows  # the next hall, best first: its top elites are the elites above
    _append_jsonl(run_dir / GENERATIONS, rec)
    _atomic_write(run_dir / BEST, (inc["text"] + "\n").encode("utf-8"))
    nxt = {**state, "generation": gen + 1, "population": next_population, "rng": random.getstate(),
           "convergence": conv.state(), "validated": validated, "elapsed_s": state["elapsed_s"] + wall,
           "games_played": state["games_played"] + played, "cache_hits": state["cache_hits"] + hits}
    if cfg.hof:
        nxt["hof"], nxt["hof_archive"] = hall, archive
    return nxt


def format_record(rec: dict, cfg: Config) -> str:
    """The one line printed per generation."""
    v, inc = rec["validated"], rec["incumbent"]
    beh = f" ({rec['behaviours']} behaviours, {rec['immigrants']} immigrants)" if "behaviours" in rec else ""
    hall = ""
    if rec.get("hof"):
        h = rec["hof"][0]
        lcb = "-inf" if h["lcb"] is None else f"{h['lcb']:+.1f}"
        hall = f" | hall top {h['hash'][:8]} {h['mean_diff']:+.1f} (bound {lcb}, {h['seeds']} seeds)"
    return (f"gen {rec['gen']:3d} | round-1 best {rec['s4']['best']:6.1f} mean {rec['s4']['mean']:6.1f}{beh}{hall} | "
            f"racing best {rec['best']['racing_mean']:6.1f} size {rec['best']['size']:3d} | "
            f"val {v['mean']:6.1f}{' new' if v['new'] else ' old'}{' +' if rec['improved'] else ''} | "
            f"incumbent {inc['mean']:6.1f} (gen {inc['gen']}) | since {rec['gens_since_improvement']}/"
            f"{cfg.patience} | {rec['wall_s']:.0f} s, {rec['games_played']} games, {rec['cache_hits']} hits")


def run_loop(cfg: Config, state: dict, engine, run_dir: Path, clock=time.monotonic, log=print,
             step=None, fmt=None) -> dict:
    """Generations until the stop rule or the budget; returns the final status dict (also status.json).

    step(cfg, state, engine, run_dir, clock=...) plays one generation and fmt(record, cfg) prints its line
    (default: this module's generation and format_record; tune_cmaes passes its own, sharing everything else:
    the stop rule, the budget, checkpoints and the status file). The machine is kept awake throughout
    (power.keep_awake; restored on any exit), which covers both CLIs.
    """
    run_dir = Path(run_dir)
    step = generation if step is None else step
    fmt = format_record if fmt is None else fmt
    with keep_awake():
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
    parser.add_argument("--first-seeds", type=int, dest="n_s4", help=f"seeds every individual plays (default {d.n_s4})")
    parser.add_argument("--more-seeds", type=int, dest="n_s8",
                        help=f"extra seeds the racing top plays (default {d.n_s8})")
    parser.add_argument("--racing-top", type=int, help=f"individuals that play the extra seeds (default {d.racing_top})")
    parser.add_argument("--validate-top", type=int, help=f"individuals validated per generation (default {d.validate_top})")
    parser.add_argument("--immigrants", type=int,
                        help=f"most fresh random individuals per generation, with de-duplication only "
                             f"(default {d.immigrants})")
    parser.add_argument("--sig-alpha", type=float,
                        help=f"stop rule's paired-test level, 0 = mean gain only (default {d.sig_alpha:g})")
    parser.add_argument("--no-dedup", action="store_const", const=False, dest="dedup",
                        help="turn off behavioural de-duplication (the gp-1 scheme)")
    parser.add_argument("--remove-tree", action="store_const", const=True, dest="remove_tree",
                        help="gp-3: 4-tree individuals with a remove tree (clean routes and removals on)")
    parser.add_argument("--seed-text", action="append", dest="seed_files", metavar="FILE",
                        help="an individual text file added to generation 0 (repeatable)")
    parser.add_argument("--hof", type=int, help=f"gp-3.3: hall of fame size, 0 = off (default {d.hof})")
    parser.add_argument("--reference", dest="reference_file", metavar="FILE",
                        help="the hall of fame's reference rule (an individual text file; needed with --hof)")
    parser.add_argument("--hof-se", type=float,
                        help=f"the hall ranks by mean difference - this * standard error (default {d.hof_se:g})")
    args = parser.parse_args(argv)
    given = {k: v for k, v in vars(args).items()
             if k not in ("run", "resume", "seed_files", "reference_file") and v is not None}
    try:
        ev._check_run_name(args.run)
        if args.seed_files:
            given["seed_texts"] = tuple(Path(f).read_text(encoding="utf-8").strip() for f in args.seed_files)
        if args.reference_file:
            given["reference_text"] = Path(args.reference_file).read_text(encoding="utf-8").strip()
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
           "EVOLVE_DIR", "RunExistsError", "read_jsonl", "read_checkpoint", "canonical", "initial_hof", "hof_score",
           "update_hof"]
