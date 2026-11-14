"""gp-7 game-level identity gates (plan 2026-11-14 section 4, Block B; section 3.3 gate (4)).

  (1) moves=v6: L played by THIS code (no trailers) reproduces L's gp6-final close-out games;
  (3) planner "off": L plus `flags: clean=0 lights=0 roundabouts=0` and a planner trailer at the separated cost
      vector with M_eff = 0 reproduces the same games;
  (4) linear.py: L converted to live coordinates (planner off, templates, slots and new terms at 0) and written
      back as text reproduces the same games (only once linear.py exists; skipped otherwise).
Every gate compares trips, seconds and commands per seed with evolved_rules/closeout/gp6/c6-cma1-3tree/games.jsonl
on close-out seeds (already played; not a decision block). Run from the main clone:

  python -m evolved_rules.ops.identity7 [--seeds 5100-5119] [--workers 4] [--gates 1,3,4]
Writes output/evolved_rules/gp7/identity/report.json and prints one line per gate. Exit 0 iff all run gates pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "evolved_rules" / "closeout" / "gp6" / "c6-cma1-3tree" / "games.jsonl"
L_PATH = ROOT / "evolved_rules" / "seeds" / "gp7" / "cma1_3tree.txt"
OUT = ROOT / "output" / "evolved_rules" / "gp7" / "identity"
FIELDS = ("trips", "seconds", "commands")
OFF_TRAILERS = ("flags: clean=0 lights=0 roundabouts=0\n"
                "planner: cost=1.0,0.15,0.05,0.5,0.0,0.0,3.0,0.0,0.0,0.0; target=0.0,0.0,0.0,0.0,0.0,0.0,0.0; "
                "theta=600.0")


SPACE = ""  # --space: a frozen space.json for gate (4); default unit scales


def gate_texts(L: str, gates: list[int]) -> dict[str, str]:
    out = {}
    if 1 in gates:
        out["(1) v6"] = L
    if 3 in gates:
        out["(3) planner off"] = f"{L}\n{OFF_TRAILERS}"
    if 4 in gates:
        try:
            from evolved_rules import linear
        except ImportError:
            print("(4) skipped: linear.py not present yet")
        else:
            sp = linear.Space.load(Path(SPACE)) if SPACE else linear.Space(l_text=L)
            out["(4) linear round trip" + (" (frozen space)" if SPACE else "")] = linear.text_from_x(
                linear.x_from_l(sp), sp)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seeds", default="5100-5119")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--gates", default="1,3,4")
    p.add_argument("--space", default="", help="frozen space.json for gate (4)")
    a = p.parse_args()
    global SPACE
    SPACE = a.space
    from evolved_rules.engine import CODE_VERSION, Engine
    lo, hi = (int(x) for x in a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    ref = {}
    for line in CLOSEOUT.read_text().splitlines():
        g = json.loads(line)
        ref[int(g["scenario_seed"])] = g
    missing = [s for s in seeds if s not in ref]
    if missing:
        raise SystemExit(f"seeds without close-out games: {missing[:5]}...")
    L = L_PATH.read_text().strip()
    texts = gate_texts(L, [int(x) for x in a.gates.split(",")])
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"code_version": CODE_VERSION, "seeds": a.seeds, "gates": {}}
    ok_all = True
    with Engine(workers=a.workers, cache_path=OUT / "cache.jsonl") as eng:
        for name, text in texts.items():
            games = eng.play([(text, s) for s in seeds])
            bad = [s for s, g in zip(seeds, games) if any(g[f] != ref[s][f] for f in FIELDS)]
            rejected = sum(g["rejected_actions"] for g in games)
            ok = not bad
            ok_all &= ok
            report["gates"][name] = {"pass": ok, "seeds": len(seeds), "different": bad, "rejected_actions": rejected}
            print(f"{name}: {'PASS' if ok else 'FAIL'} ({len(seeds) - len(bad)}/{len(seeds)} identical on "
                  f"{'/'.join(FIELDS)}; rejected draws {rejected})" + (f"; first different {bad[:5]}" if bad else ""),
                  flush=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
