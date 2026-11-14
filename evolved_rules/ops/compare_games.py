"""Per-seed game comparison for the determinism gates D1/D2 (HANDOFF.md section 4).

Compares two games.jsonl files on the seeds they share (optionally restricted with --seeds A-B) and reports
how many seeds match exactly on trips, seconds and commands. It prints counts and the first mismatches only,
plus the mean trip difference; use it only on seed blocks that are not protected (close-out 5100-5299,
calibration 5300-5399).

  python evolved_rules/ops/compare_games.py A/games.jsonl B/games.jsonl [--seeds 5100-5159]
Exit code 0 if every shared seed matches, 1 otherwise (2 if no seeds are shared).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FIELDS = ("trips", "seconds", "commands")


def load(path: Path) -> dict[int, dict]:
    games = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            games[int(g["scenario_seed"])] = g
    return games


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a", type=Path)
    p.add_argument("b", type=Path)
    p.add_argument("--seeds", default="", help="inclusive range A-B")
    a = p.parse_args()
    ga, gb = load(a.a), load(a.b)
    seeds = sorted(set(ga) & set(gb))
    if a.seeds:
        lo, hi = (int(x) for x in a.seeds.split("-"))
        seeds = [s for s in seeds if lo <= s <= hi]
    if not seeds:
        print("no shared seeds")
        return 2
    bad = [s for s in seeds if any(ga[s][f] != gb[s][f] for f in FIELDS)]
    print(f"shared seeds {len(seeds)} ({seeds[0]}-{seeds[-1]}); identical on {'/'.join(FIELDS)}: "
          f"{len(seeds) - len(bad)}; different: {len(bad)}")
    for s in bad[:5]:
        print(f"  seed {s}: " + ", ".join(f"{f} {ga[s][f]} vs {gb[s][f]}" for f in FIELDS))
    if bad:
        d = [ga[s]["trips"] - gb[s]["trips"] for s in seeds]
        print(f"mean trips difference (A - B) over shared seeds: {sum(d) / len(d):+.1f}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
