"""gp-6/cma-6 close-out analysis (operative plan 2026-11-14, section 2.1): per-arm means and the choice of L.

Reads <arm>/games.jsonl in this folder (LA 5100-5299, gp6-v1 code). Prints every arm's mean, median, sd, SE, mean
seconds, and the paired difference vs cma-1 3-tree (mean, paired SD, paired SE, paired t, r). L = the arm with the
highest mean among the learned candidates; if its paired difference vs cma-1 3-tree is within 1 paired SE, L = cma-1
3-tree (tie rule). Run: python evolved_rules/closeout/gp6/analyze.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = "c6-cma1-3tree"
CANDIDATES = ("c6-cma1-3tree", "c6-cma1-5tree", "c6-cma6-mean", "c6-cma6-best", "c6-gp6-7fa4b2ec")
TEXTS = {"c6-cma1-3tree": "cma1_3tree.txt", "c6-cma1-5tree": "cma1_5tree.txt", "c6-cma6-mean": "cma6_mean.txt",
         "c6-cma6-best": "cma6_best.txt", "c6-gp6-7fa4b2ec": "gp6_7fa4b2ec.txt", "c6-separated": "(builtin separated)",
         "c6-hand": "(builtin hand)"}


def load(arm: str) -> dict[int, dict]:
    rows = [json.loads(l) for l in (HERE / arm / "games.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return {int(r["scenario_seed"]): r for r in rows}


def stats(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    return m, sd


def main() -> None:
    arms = sorted(p.name for p in HERE.iterdir() if (p / "games.jsonl").exists())
    data = {a: load(a) for a in arms}
    ref = data[REF]
    print(f"{'arm':18} {'n':>4} {'mean':>7} {'median':>7} {'sd':>6} {'SE':>5} {'secs':>7} | "
          f"{'diff':>6} {'pSD':>6} {'pSE':>5} {'t':>6} {'r':>5}")
    res = {}
    for a in arms:
        d = data[a]
        trips = [d[s]["trips"] for s in sorted(d)]
        m, sd = stats(trips)
        med = sorted(trips)[len(trips) // 2] if len(trips) % 2 else sum(sorted(trips)[len(trips) // 2 - 1:len(trips) // 2 + 1]) / 2
        secs = stats([d[s]["seconds"] for s in d])[0]
        common = sorted(set(d) & set(ref))
        diffs = [d[s]["trips"] - ref[s]["trips"] for s in common]
        dm, dsd = stats(diffs)
        pse = dsd / math.sqrt(len(diffs)) if diffs else float("nan")
        t = dm / pse if pse > 0 else float("nan")
        x = [d[s]["trips"] for s in common]; y = [ref[s]["trips"] for s in common]
        mx, sx = stats(x); my, sy = stats(y)
        r = (sum((a_ - mx) * (b - my) for a_, b in zip(x, y)) / (len(x) - 1) / (sx * sy)) if sx > 0 and sy > 0 else float("nan")
        res[a] = (m, dm, pse)
        print(f"{a:18} {len(trips):4d} {m:7.1f} {med:7.1f} {sd:6.1f} {sd / math.sqrt(len(trips)):5.1f} {secs:7.1f} | "
              f"{dm:6.1f} {dsd:6.1f} {pse:5.1f} {t:6.2f} {r:5.2f}")
    cands = [a for a in CANDIDATES if a in res]
    lead = max(cands, key=lambda a: res[a][0])
    m, dm, pse = res[lead]
    if lead != REF and (pse != pse or dm <= pse):
        L, why = REF, f"tie rule: leader {lead} is +{dm:.1f} vs cma-1 3-tree, within 1 paired SE ({pse:.1f})"
    else:
        L, why = lead, ("highest mean" if lead == REF else f"+{dm:.1f} vs cma-1 3-tree, beyond 1 paired SE ({pse:.1f})")
    missing = [a for a in CANDIDATES if a not in res]
    print(f"\nL = {L} ({TEXTS[L]}): {why}" + (f"   [missing arms: {missing}]" if missing else ""))


if __name__ == "__main__":
    main()
