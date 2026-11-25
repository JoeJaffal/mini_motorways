"""gp-8 headline and secondaries (plan 2026-11-21 section 5), fixed before the test is looked at.

  PY -m evolved_rules.ops.headline8 --cstar RUNS --baselines BASE --out OUT.json
  PY -m evolved_rules.ops.headline8 --dry-run --cstar RUNS --out OUT.json     (tracker data, 9900-9924)

Inputs are run folders, each with summary.json and games.jsonl (one evaluate run of 50 seeds in one city):
  RUNS/c8-<city>-Cstar-<start>      C* on validation 9500 and test 9600, 9650, 9700, 9750
  RUNS/c8-<city>-CstarOff-9500      C* with lights and roundabouts off, validation
  BASE/b8-<city>-B7-<start>         B7 baselines (both halves: the M1's LA + Beijing, the laptop's Tokyo + Dar)
Games pair by (city, seed).

Integrity (any failure aborts before a number is computed): every run is f35-keyed, keyed, cap 3600, commit
29b78daf, no --verify, the policy text hash it should have, 50 seeds, one game per seed, and none truncated by an
error (a game ends terminated, or truncated at the cap). Test: 800 pairs (200 per city); validation: 200 pairs
(50 per city).

Headline: C* - B7 on the 800 test maps pooled, one-sided paired t (H0: mean <= 0), alpha 0.05, looked at once.
Secondaries, one Holm family of 5, two-sided paired t: C* - B7 per city on test (4); tools ablation
C* - C*_off on validation pooled (1). Reported with each policy and block: mean, median, best, worst trips;
lights and roundabouts placed per game; mean car wait; rejected actions. BCa 90% interval and the one-sided
Wilcoxon p are given next to the headline; they never decide.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from evolved_rules import evolve as evo
from evolved_rules import stats7

CITIES = ("LosAngeles", "Beijing", "Tokyo", "DarEsSalaam")
SIM = "2026-11-21.f35-keyed"
COMMIT = "29b78daf95dbc62bd0d4d3391ee02af025eee9f3"
HASH = {"Cstar": "ca8dbf764e44edab", "CstarOff": "5d63e883708f4e6b", "B7": "e8b8b4cad3d5b71c"}
VAL, TEST = (9500,), (9600, 9650, 9700, 9750)
ALPHA = 0.05


def load_run(d: Path, label: str, n_seeds: int, check_hash: bool = True) -> dict:
    s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    c = s["config"]
    errs = []
    if c.get("simulator_version") != SIM: errs.append(f"simulator {c.get('simulator_version')}")
    if c.get("randomness") != "keyed": errs.append(f"randomness {c.get('randomness')}")
    if float(c.get("cap_s", 0)) != 3600.0: errs.append(f"cap {c.get('cap_s')}")
    if c.get("commit") != COMMIT: errs.append(f"commit {c.get('commit')}")
    if c.get("dirty"): errs.append("dirty")
    if c.get("verify"): errs.append("verify on")
    if check_hash and evo.text_hash(c["policy_text"].strip()) != HASH[label]:
        errs.append(f"policy hash {evo.text_hash(c['policy_text'].strip())} != {HASH[label]}")
    games = [json.loads(l) for l in (d / "games.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    seeds = [g["scenario_seed"] for g in games]
    if len(games) != n_seeds or len(set(seeds)) != n_seeds or sorted(seeds) != sorted(c["seeds"]):
        errs.append(f"{len(games)} games, {len(set(seeds))} seeds, expected {n_seeds}")
    for g in games:
        if g.get("simulator_version") != SIM: errs.append(f"game {g['scenario_seed']} simulator")
        if g.get("city") != c.get("city"): errs.append(f"game {g['scenario_seed']} city {g.get('city')}")
        if not (g.get("terminated") or g.get("truncated")): errs.append(f"game {g['scenario_seed']} did not end")
        if g.get("error"): errs.append(f"game {g['scenario_seed']} error")
    if errs:
        sys.exit(f"{d}: " + "; ".join(errs[:5]))
    return {(c["city"], g["scenario_seed"]): g for g in games}


def load(root: Path, prefix: str, label: str, starts, n_seeds=50, run_label=None, check_hash=True) -> dict:
    out = {}
    for city in CITIES:
        for s in starts:
            name = f"{prefix}-{city}-{run_label or label}-{s}" if s is not None else f"{prefix}-{run_label or label}-{city}"
            out.update(load_run(root / name, label, n_seeds, check_hash))
    return out


def describe(games: list[dict]) -> dict:
    t = [g["trips"] for g in games]
    ac = [g.get("action_counts", {}) for g in games]
    return {"n": len(t), "mean": statistics.fmean(t), "median": statistics.median(t), "best": max(t), "worst": min(t),
            "lights_per_game": statistics.fmean(a.get("TrafficLight", 0) for a in ac),
            "roundabouts_per_game": statistics.fmean(a.get("Roundabout", 0) for a in ac),
            "mean_car_wait": statistics.fmean(g.get("mean_car_wait", 0.0) for g in games),
            "rejected_actions": sum(g.get("rejected_actions", 0) for g in games)}


def pairs(a: dict, b: dict, keys) -> list[float]:
    return [float(a[k]["trips"]) - float(b[k]["trips"]) for k in keys]


def analyse(cs_val, cs_test, off_val, b7_test, n_test_city, n_val_city) -> dict:
    tkeys = sorted(cs_test)
    vkeys = sorted(cs_val)
    assert set(tkeys) == set(b7_test), "test maps differ between C* and B7"
    assert set(vkeys) == set(off_val), "validation maps differ between C* and C* off"
    assert len(tkeys) == 4 * n_test_city and all(sum(k[0] == c for k in tkeys) == n_test_city for c in CITIES)
    assert len(vkeys) == 4 * n_val_city and all(sum(k[0] == c for k in vkeys) == n_val_city for c in CITIES)
    d = pairs(cs_test, b7_test, tkeys)
    head = stats7.paired_t_one_sided(d)
    head["bca90"] = stats7.bca_interval(d)
    head["wilcoxon_p_one_sided"] = stats7.wilcoxon_one_sided(d)
    head["decision"] = "C* > B7" if head["p"] < ALPHA else "no measurable improvement over B7"
    sec = {}
    for c in CITIES:
        k = [x for x in tkeys if x[0] == c]
        sec[f"test {c}: C* - B7"] = stats7.paired_t_two_sided(pairs(cs_test, b7_test, k))
    sec["validation: C* - C* off"] = stats7.paired_t_two_sided(pairs(cs_val, off_val, vkeys))
    adj = stats7.holm({k: v["p"] for k, v in sec.items()})
    for k in sec:
        sec[k]["p_holm"] = adj[k]
    desc = {"test": {"C*": describe([cs_test[k] for k in tkeys]), "B7": describe([b7_test[k] for k in tkeys])},
            "validation": {"C*": describe([cs_val[k] for k in vkeys]), "C* off": describe([off_val[k] for k in vkeys])}}
    for c in CITIES:
        k = [x for x in tkeys if x[0] == c]
        desc[f"test {c}"] = {"C*": describe([cs_test[x] for x in k]), "B7": describe([b7_test[x] for x in k])}
    return {"headline": head, "secondaries": sec, "describe": desc}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cstar", required=True, type=Path, help="folder holding the c8-* (or trk8-*) runs")
    p.add_argument("--baselines", type=Path, help="folder holding the b8-<city>-B7-<start> runs")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--dry-run", action="store_true", help="tracker data: g090 as C*, g095 as C* off, B7 (9900-9924)")
    a = p.parse_args(argv)
    if a.dry_run:  # exercises loading, pairing and the statistics; the hashes are not C*'s, so not checked
        cs = load(a.cstar, "trk8", "Cstar", [None], 25, run_label="g090", check_hash=False)
        off = load(a.cstar, "trk8", "CstarOff", [None], 25, run_label="g095", check_hash=False)
        b7 = load(a.cstar, "trk8", "B7", [None], 25, run_label="B7")
        res = analyse(cs, cs, off, b7, 25, 25)
    else:
        cs_val = load(a.cstar, "c8", "Cstar", VAL)
        cs_test = load(a.cstar, "c8", "Cstar", TEST)
        off_val = load(a.cstar, "c8", "CstarOff", VAL)
        b7_test = load(a.baselines, "b8", "B7", TEST)
        res = analyse(cs_val, cs_test, off_val, b7_test, 200, 50)
    res["dry_run"] = a.dry_run
    a.out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"headline": res["headline"], "holm": {k: v["p_holm"] for k, v in res["secondaries"].items()}},
                     indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
