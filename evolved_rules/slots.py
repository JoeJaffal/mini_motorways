"""gp-7-lite (plan 2026-11-14 section 3.4): slot-tree proposals, the zero-game screen, the race and the insertion.

K = 4 live slots: 0 priority (over gp.PRIORITY7_TERMS), 1 hold (gp.HOLD_TERMS), 2 cost (per cell, gp.COST_SLOT_TERMS),
3 target (per pair, gp.TARGET_SLOT_TERMS). Slot trees have at most MAX_NODES nodes and depth <= MAX_DEPTH, over
add, sub, mul, pdiv, min, max, neg, if_gt and gate (gp.V7_FUNCTIONS); constants change by Gaussian steps.

Each epoch (the end of every EPOCH_EVERY-th generation after the fork), only for slots still empty:
  1. propose(): about PROPOSALS trees (subtree mutation of a random tree, constant steps, the gate wrapper
     mul(gate(stress, theta), F), random depth 1-3 trees); exact copies of the fixed templates are rejected;
  2. screen(): zero games, on the trend-monitor decision records of the epoch:
       priority / hold: w0 = the smallest |w| (bisection on [0, W_MAX]) at which adding w * tree changes 10% of the
         logged first-pass choices (priority: the chosen candidate; hold: build or not); the proposal must change at
         least 3% at w0 (it never reaches 3% within W_MAX -> rejected);
       target: the same on the logged top pairs (the top pair changes);
       cost: within-decision variance of the tree over the logged cells > 0 and |r| < 0.9 with stopped_on and with
         cars_on; w0 = 1 / its median within-decision standard deviation;
     the top KEEP survive: priority/hold/target by the smallest w0 x spread (the weight needed in normalised units),
     then cost ones by the lowest correlation with the plain car counts;
  3. race(): on RACE_MAPS fresh probe maps (10000+ by counter, used once): the current in-bounds mean and each kept
     proposal inserted at +w0 and at -w0 (5 texts x 24 = 120 games); a proposal is accepted if its better sign
     beats the mean with a one-sided paired t p < RACE_P; at most one per slot (the lower p);
  4. insert(): scale_k from the tree's spread on the records (1/spread, normalised like linear.scales_for_x0 and
     clipped to [0.1, 10]), mask_k = 1, es.mean[k] = clip(sign * w0 / scale_k, -4.5, 4.5), its variance left.
Every random draw uses random.Random(f"{seed}:{gen}") so an epoch is deterministic and a resume repeats it exactly.
"""
from __future__ import annotations

import dataclasses
import math
import random
import statistics

from deap import gp as dgp

from . import gp, linear
from .agent import _LOG_CAND_TERMS, _LOG_GLOBAL_TERMS

EPOCH_EVERY = 5
PROPOSALS = 60
KEEP = 2
RACE_MAPS = 24
RACE_P = 0.10
MAX_NODES, MAX_DEPTH = 15, 4
W_MAX = 50.0
CHANGE_AT_W0, CHANGE_MIN = 0.10, 0.03
SLOT_KINDS = ("priority", "hold", "cost", "target")
SLOT_PSETS = (gp.PRIORITY7_SET, gp.HOLD7_SET, gp.COST_SLOT_SET, gp.TARGET_SLOT_SET)
SLOT_TERMS = (gp.PRIORITY7_TERMS, gp.HOLD_TERMS, gp.COST_SLOT_TERMS, gp.TARGET_SLOT_TERMS)
STRESS = {0: ("worst_overcrowded", "shop_overcrowded"), 1: ("worst_overcrowded",), 2: ("worst_overcrowded",),
          3: ("shop_overcrowded",)}


def templates(theta: float) -> set[str]:
    out = {f"mul({a}, {b})" for a, b in linear.PRIORITY_TEMPLATES}
    out.add(f"mul(gate(worst_overcrowded, {float(theta)!r}), stopped_on)")
    out.add("mul(shop_overcrowded, detour_ratio)")
    return out


def _canon(expr: str, k: int) -> str | None:
    try:
        t = gp._parse_tree(expr, 0, pset=SLOT_PSETS[k], name=f"{SLOT_KINDS[k]} slot")
    except ValueError:
        return None
    if len(t) > MAX_NODES or t.height > MAX_DEPTH:
        return None
    return str(t)


def _random_tree(k: int, rng: random.Random, lo: int = 1, hi: int = 3) -> str:
    state = random.getstate()
    random.seed(rng.random())
    try:
        return str(dgp.PrimitiveTree(dgp.genHalfAndHalf(SLOT_PSETS[k], lo, hi)))
    finally:
        random.setstate(state)


def _const_step(expr: str, rng: random.Random) -> str:
    toks = gp._TOKEN.findall(expr)
    idx = [i for i, t in enumerate(toks) if _is_num(t)]
    if not idx:
        return expr
    i = rng.choice(idx)
    toks[i] = repr(round(float(toks[i]) + rng.gauss(0.0, 0.5), 3) + 0.0)
    out = ""
    for t in toks:
        out += t if t in "()" else (", " + t if out and out[-1] not in "(" and t != "," else t)
    return out.replace(",,", ",").replace(", ,", ",")


def _is_num(t: str) -> bool:
    try:
        float(t)
        return True
    except ValueError:
        return False


def _mutate(expr: str, k: int, rng: random.Random) -> str:
    state = random.getstate()
    random.seed(rng.random())
    try:
        t = dgp.PrimitiveTree.from_string(expr, SLOT_PSETS[k])
        dgp.mutUniform(t, expr=lambda pset, type_: dgp.genFull(pset, 0, 2, type_), pset=SLOT_PSETS[k])
        return str(t)
    except Exception:
        return expr
    finally:
        random.setstate(state)


def propose(empty_slots: list[int], theta: float, rng: random.Random, n: int = PROPOSALS) -> list[tuple[int, str]]:
    """About n distinct (slot, tree) proposals spread over the empty slots."""
    if not empty_slots:
        return []
    banned = templates(theta)
    out: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    tries = 0
    while len(out) < n and tries < 40 * n:
        tries += 1
        k = empty_slots[tries % len(empty_slots)]
        op = rng.random()
        base = _random_tree(k, rng, 1, 3)
        if op < 0.35:
            cand = base
        elif op < 0.6:
            cand = _mutate(base, k, rng)
        elif op < 0.8:
            cand = _const_step(base, rng)
        else:
            stress = rng.choice(STRESS[k])
            cand = f"mul(gate({stress}, {round(rng.uniform(0.0, 0.1), 3)!r}), {_random_tree(k, rng, 1, 2)})"
        c = _canon(cand, k)
        if c is None or c in banned or (k, c) in seen or _is_num(c):
            continue
        seen.add((k, c))
        out.append((k, c))
    return out


# --- the zero-game screen ------------------------------------------------------------------------------------

def _compile(k: int, expr: str):
    return dgp.compile(expr, SLOT_PSETS[k])


def _safe(fn, args) -> float:
    try:
        v = float(fn(*args))
    except (OverflowError, ZeroDivisionError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


def _priority_values(fn, rec) -> list[float]:
    """The slot tree on each logged candidate (priority terms scaled as gp's reader does: candidate row + globals)."""
    ci = {t: i for i, t in enumerate(_LOG_CAND_TERMS)}
    gi = {t: i for i, t in enumerate(_LOG_GLOBAL_TERMS)}
    out = []
    for row in rec["rows"]:
        args = []
        for t in gp.PRIORITY7_TERMS:
            raw = row[ci[t]] if t in ci else rec["g"][gi[t]]
            args.append(raw / gp.SCALE[t])
        out.append(_safe(fn, args))
    return out


def _hold_value(fn, rec) -> float:
    gi = {t: i for i, t in enumerate(_LOG_GLOBAL_TERMS)}
    return _safe(fn, [rec["g"][gi[t]] / gp.SCALE[t] for t in gp.HOLD_TERMS])


def _changes(k: int, fn, recs: list[dict], w: float) -> float:
    n = ch = 0
    for r in recs:
        if k == 0:
            if len(r.get("rows") or []) < 2 or r.get("best", -1) < 0:
                continue
            vals = _priority_values(fn, r)
            q = [p + w * v if (p is not None and math.isfinite(p)) else -math.inf for p, v in zip(r["p"], vals)]
            new = max(range(len(q)), key=lambda i: (q[i], -i))
            n += 1
            ch += new != r["best"]
        elif k == 1:
            if r.get("best", -1) < 0 or not math.isfinite(r.get("hold", math.nan)):
                continue
            pb = r["p"][r["best"]]
            n += 1
            ch += (pb >= r["hold"]) != (pb >= r["hold"] + w * _hold_value(fn, r))
        elif k == 3:
            pairs = r.get("pairs_top") or []
            if len(pairs) < 2:
                continue
            q = [p[2] + w * _safe(fn, [p[3], p[4], p[6], p[5], p[7] if len(p) > 7 else 0.0]) for p in pairs]
            n += 1
            ch += max(range(len(q)), key=lambda i: (q[i], -i)) != 0
    return ch / n if n else 0.0


def _w0(k: int, fn, recs) -> float | None:
    for sign in (1.0, -1.0):
        if _changes(k, fn, recs, sign * W_MAX) >= CHANGE_AT_W0:
            break
    else:
        top = max(_changes(k, fn, recs, W_MAX), _changes(k, fn, recs, -W_MAX))
        return None if top < CHANGE_MIN else W_MAX
    lo, hi = 0.0, W_MAX
    for _ in range(30):
        mid = (lo + hi) / 2
        if max(_changes(k, fn, recs, mid), _changes(k, fn, recs, -mid)) >= CHANGE_AT_W0:
            hi = mid
        else:
            lo = mid
    return hi


def _cost_stats(fn, recs) -> tuple[float, float, float, float]:
    """(median within-decision variance, |r| with stopped_on, |r| with cars_on, median sd) over logged cells."""
    vs, sds, xs, st, ca = [], [], [], [], []
    for r in recs:
        c = r.get("cells")
        if not c:
            continue
        vals = [_safe(fn, [a, b, n, c["wo"]]) for a, b, n in c["cars"]]
        e_near, e_far = _safe(fn, [0.0, 0.0, 1.0, c["wo"]]), _safe(fn, [0.0, 0.0, 0.0, c["wo"]])
        allv = vals + [e_near] * c["empty_near"] + [e_far] * c["empty_far"]
        if len(allv) >= 2:
            vs.append(statistics.pvariance(allv))
            sds.append(statistics.pstdev(allv))
        xs += vals
        st += [b for _, b, _ in c["cars"]]
        ca += [a for a, _, _ in c["cars"]]

    def corr(a, b):
        if len(a) < 3 or statistics.pstdev(a) == 0 or statistics.pstdev(b) == 0:
            return 1.0 if len(a) >= 3 and statistics.pstdev(a) == 0 else 0.0
        return abs(statistics.correlation(a, b))
    return (statistics.median(vs) if vs else 0.0, corr(xs, st), corr(xs, ca), statistics.median(sds) if sds else 0.0)


def screen(props: list[tuple[int, str]], recs: list[dict]) -> list[dict]:
    """Survivors of the zero-game screen, best first, at most KEEP: dicts with slot, tree, w0 and the measure."""
    ok = []
    for k, tree in props:
        fn = _compile(k, tree)
        if k == 2:
            var, r_st, r_ca, sd = _cost_stats(fn, recs)
            if var > 0 and r_st < 0.9 and r_ca < 0.9 and sd > 0:
                ok.append({"slot": k, "tree": tree, "w0": 1.0 / sd, "key": (1, max(r_st, r_ca)), "var": var})
        else:
            w0 = _w0(k, fn, recs)
            spread = slot_spread(k, tree, recs) if w0 is not None else 0.0
            if w0 is not None and spread > 0:
                ok.append({"slot": k, "tree": tree, "w0": w0, "key": (0, w0 * spread), "spread": spread,
                           "change_at_w0": max(_changes(k, fn, recs, w0), _changes(k, fn, recs, -w0))})
    ok.sort(key=lambda d: (d["key"], d["slot"], d["tree"]))
    return ok[:KEEP]


def slot_spread(k: int, tree: str, recs: list[dict]) -> float:
    fn = _compile(k, tree)
    if k == 2:
        return _cost_stats(fn, recs)[3]
    sds = []
    for r in recs:
        if k == 0 and len(r.get("rows") or []) >= 2:
            sds.append(statistics.pstdev(_priority_values(fn, r)))
        elif k == 3 and len(r.get("pairs_top") or []) >= 2:
            sds.append(statistics.pstdev([_safe(fn, [p[3], p[4], p[6], p[5], p[7] if len(p) > 7 else 0.0])
                                          for p in r["pairs_top"]]))
    if k == 1:
        vals = [_hold_value(fn, r) for r in recs if r.get("g")]
        return statistics.pstdev(vals) if len(vals) >= 2 else 0.0
    sds = [s for s in sds if s > 0]
    return statistics.median(sds) if sds else 0.0


def inserted_space(space: linear.Space, k: int, tree: str, scale: float) -> linear.Space:
    scales = list(space.scales)
    scales[linear.INDEX[f"slot{k}"]] = scale
    masks = list(space.masks)
    masks[k] = 1.0
    trees = list(space.slot_trees)
    trees[k] = tree
    return dataclasses.replace(space, scales=tuple(scales), masks=tuple(masks), slot_trees=tuple(trees))


def slot_scale(spread: float, norm: float) -> float:
    if not (spread > 0 and math.isfinite(spread)):
        return 1.0
    return min(10.0, max(0.1, (1.0 / spread) / norm))
