"""gp-7 statistics and the pre-registered headline rule (plan 2026-11-14 sections 2.2-2.4).

decide_headline() is the rule, exactly:
  1. Validation selects only. Every challenger is paired by seed with L on the validation seeds (all seeds of the
     validation block that are complete for every challenger and L). C* = the challenger with the largest paired
     mean difference vs L; no p-value. If every difference is <= 0, the headline is L ("no measurable
     improvement") and the test is optional and descriptive.
  2. The test decides, once. n = the largest multiple of 100 such that every seed in test_start..test_start+n-1 is
     complete for both C* and L (completeness alone decides n, never results), capped at test_max. If n < min_n
     the headline is L. Otherwise H0: mu(C*) - mu(L) <= 0 with a one-sided paired t at alpha; C* is adopted only if
     p < alpha. The BCa 90% lower bound (one-sided 95%) and the one-sided Wilcoxon signed-rank p are reported
     alongside, never decide.
Empirical Bayes (eb_shrink) is only for quoting numbers; Holm (holm) for the secondary results (plan 2.4).
All bootstrap draws use a fixed seed, so every number is reproducible.
"""
from __future__ import annotations

import math
import statistics

import numpy as np
from scipy import stats as st

BOOT_B = 10000
BOOT_SEED = 20261114


def paired_diffs(a: dict[int, float], b: dict[int, float], seeds) -> list[float]:
    return [float(a[s]) - float(b[s]) for s in seeds]


def paired_t_one_sided(d: list[float]) -> dict:
    """One-sided paired t for H0: mean(d) <= 0. Returns mean, se, t, df, p."""
    n = len(d)
    mean = statistics.fmean(d)
    sd = statistics.stdev(d) if n > 1 else math.nan
    se = sd / math.sqrt(n) if n > 1 else math.nan
    if not (se > 0):
        t = math.inf if mean > 0 else (-math.inf if mean < 0 else 0.0)
        p = 0.0 if mean > 0 else 1.0
    else:
        t = mean / se
        p = float(st.t.sf(t, n - 1))
    return {"n": n, "mean": mean, "sd": sd, "se": se, "t": t, "df": n - 1, "p": p}


def paired_t_two_sided(d: list[float]) -> dict:
    r = paired_t_one_sided(d)
    r["p"] = min(1.0, 2 * min(r["p"], 1 - r["p"])) if math.isfinite(r["t"]) else (0.0 if r["mean"] != 0 else 1.0)
    return r


def bca_interval(d: list[float], level: float = 0.90, B: int = BOOT_B, seed: int = BOOT_SEED) -> tuple[float, float]:
    """Two-sided BCa interval for the mean of d at `level` (its lower end is the one-sided (1+level)/2 bound)."""
    x = np.asarray(d, dtype=float)
    n = len(x)
    theta = x.mean()
    rng = np.random.default_rng(seed)
    boots = x[rng.integers(0, n, size=(B, n))].mean(axis=1)
    prop = np.clip((boots < theta).mean() + 0.5 * (boots == theta).mean(), 1.0 / B, 1 - 1.0 / B)
    z0 = st.norm.ppf(prop)
    jack = np.array([(x.sum() - x[i]) / (n - 1) for i in range(n)])
    jm = jack.mean()
    num, den = ((jm - jack) ** 3).sum(), 6.0 * (((jm - jack) ** 2).sum() ** 1.5)
    acc = num / den if den > 0 else 0.0
    alpha = (1 - level) / 2
    out = []
    for z in (st.norm.ppf(alpha), st.norm.ppf(1 - alpha)):
        q = st.norm.cdf(z0 + (z0 + z) / (1 - acc * (z0 + z)))
        out.append(float(np.quantile(boots, q)))
    return out[0], out[1]


def wilcoxon_one_sided(d: list[float]) -> float:
    if all(v == 0 for v in d):
        return 1.0
    return float(st.wilcoxon(d, alternative="greater", zero_method="wilcox").pvalue)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values (step-down, monotone, capped at 1)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def eb_shrink(means: dict[str, float], ses: dict[str, float]) -> dict[str, float]:
    """Normal-normal empirical Bayes posterior means (for quoting only): prior mean = precision-weighted grand mean,
    prior variance tau^2 = max(0, var(means) - mean(se^2)) (method of moments)."""
    ks = list(means)
    if len(ks) < 2:
        return dict(means)
    m = np.array([means[k] for k in ks])
    s2 = np.array([ses[k] ** 2 for k in ks])
    tau2 = max(0.0, float(m.var(ddof=1) - s2.mean()))
    w = 1.0 / np.maximum(s2, 1e-12)
    grand = float((w * m).sum() / w.sum())
    if tau2 == 0:
        return {k: grand for k in ks}
    return {k: float(grand + tau2 / (tau2 + s2[i]) * (m[i] - grand)) for i, k in enumerate(ks)}


def complete_n(c: dict[int, float], L: dict[int, float], start: int, max_n: int, chunk: int = 100) -> int:
    """The largest multiple of `chunk` (<= max_n) with every seed start..start+n-1 present in both c and L."""
    n = 0
    while n + chunk <= max_n and all(s in c and s in L for s in range(start + n, start + n + chunk)):
        n += chunk
    return n


def decide_headline(val: dict[str, dict[int, float]], val_L: dict[int, float],
                    test_c: dict[int, float] | None, test_L: dict[int, float], *, alpha: float = 0.05,
                    min_n: int = 400, test_start: int = 6100, test_max: int = 900) -> dict:
    """The pre-registered headline rule (module docstring). `val` maps challenger name -> seed -> trips; test_c is
    C*'s test games (seed -> trips), None if not played. Returns a dict with every number used and `headline`."""
    common = sorted(set(val_L).intersection(*(set(v) for v in val.values()))) if val else []
    diffs = {k: statistics.fmean(paired_diffs(v, val_L, common)) for k, v in val.items()} if common else {}
    out: dict = {"validation_seeds": len(common), "validation_mean_diff": diffs}
    if not diffs or max(diffs.values()) <= 0:
        out.update(c_star=None, headline="L", reason="every validation difference <= 0: no measurable improvement")
        return out
    c_star = max(sorted(diffs), key=lambda k: diffs[k])
    out["c_star"] = c_star
    n = complete_n(test_c or {}, test_L, test_start, test_max)
    out["test_n"] = n
    if n < min_n:
        out.update(headline="L", reason=f"test n = {n} < {min_n} complete seeds at T_freeze")
        return out
    seeds = list(range(test_start, test_start + n))
    d = paired_diffs(test_c, test_L, seeds)
    t = paired_t_one_sided(d)
    lo, hi = bca_interval(d, 0.90)
    out["test"] = {**t, "bca90": [lo, hi], "bca_lower_one_sided_95": lo, "wilcoxon_p_one_sided": wilcoxon_one_sided(d),
                   "mean_c": statistics.fmean(test_c[s] for s in seeds), "mean_L": statistics.fmean(test_L[s] for s in seeds)}
    adopt = t["p"] < alpha
    out.update(headline=c_star if adopt else "L",
               reason=(f"one-sided paired t p = {t['p']:.4g} < {alpha}" if adopt
                       else f"one-sided paired t p = {t['p']:.4g} >= {alpha}: C* not adopted"))
    return out
