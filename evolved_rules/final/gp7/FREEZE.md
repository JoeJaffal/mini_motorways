# gp-7 / cma-7 challenger freeze (plan 2.2), 2026-11-19 00:12 (commit 4982e73), before any validation game (first one started 00:13)

Both runs ended with status **budget** ("stop time 2026-11-19T01:22 reached"): cma-7 at 00:06:43 after 74
generations (0-73), gp-7 at 00:07:43 after 54 (0-53). Each stopped early because no further generation could finish
before T_stop.

**Frozen commit: `6b80889` (tag `cma7-launch`, gp7-v1)**, worktree `../mm-gp7-final` (detached, clean), host DLL of
the main clone (simulator 2026-11-10.f34, `simulation/` unchanged since b96d98d). The plan does not name the commit.
Why this one:
- x0\* and cma-7 were played by this code.
- gp-7's final text has no slot trailer, because no tree was ever inserted, so it is a pure v1 text.
- The fork gate showed v2 = v1 on empty slots (byte-identical draws, texts and games). gp-7's post-fork
  generations reproduce cma-7's to the digit.

Pipeline check: x0\* played through `evaluate` in this worktree on training seed 138 gives 1157 trips, the same as
its recorded gen-0 trend-monitor game. Cap 3600 s, the same as L's pre-play and the runs.

| Challenger | File | Canonical text hash | Origin |
|---|---|---|---|
| x0\* | `challengers/x0star.txt` | `7bf3469481eb3fb9` | screen (pre-registration) |
| cma-7 final | `challengers/cma7_final.txt` | `8b38684b600cb458` | in-bounds mean after gen 73 |
| gp-7 final | `challengers/gp7_final.txt` | `e8b8b4cad3d5b71c` | in-bounds mean after gen 53 |

gp-7 final's hash equals cma-7's gen-53 `final_mean_hash`, so gp-7 final is literally cma-7's mean at gen 53.

The rule is `stats7.decide_headline`, unchanged since 4453544. The pick is `ops/pick7.py`: validation 1550-1749 for
the three challengers vs L's pre-played games. The test (C\* on 6100-6999, up to 900, never below 400) is one look.
The queue is `output/evolved_rules/ops/valtest.sh` under the watchdog, and no chunk starts after 07:38.
