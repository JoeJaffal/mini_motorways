# gp-8 / cma-8 freeze (plan §5), 2026-11-25, before any validation or test game of C\*

cma-8 ended with status **budget** at 20:37:15 ("stop time 2026-11-25T21:00:00+02:00 reached") after 100
generations (0-99), ledger 29,992 games. It stopped before 21:00 because a 101st generation could not finish in
time. About 4 h of run time was lost to the M4 reboot on 2026-11-23 (plan §6).

**C\* = cma-8's final in-bounds mean** (after the tell of gen 99), by rule. There is one challenger, so validation
does not pick anything.

**Frozen commit: `29b78daf` (tag `cma8-launch`, gp8-v1)**, worktree `../mm-cma8` (clean), its own simulator build
(`2026-11-21.f35-keyed`; every call passes `--randomness keyed`). cma-8, the tracker
and both baseline halves were played by this commit (the laptop half's `config.commit` is 29b78daf; the M1 half's
is checked when its branch is fetched).

| Policy | File | Canonical text hash | Origin |
|---|---|---|---|
| C\* | `challengers/cstar.txt` | `ca8dbf764e44edab` | `final_mean.txt` after gen 99; equals gen 99's `final_mean_hash` |
| C\* tools off | `challengers/cstar_tools_off.txt` | `5d63e883708f4e6b` | C\*'s x decoded with lights and roundabouts off |

Checks:
- `final_mean.txt` hash = gen 99 `final_mean_hash`; decoding `final_mean.json` x under the run's space gives the
  same text; x is in bounds.
- Tools off is the same construction as gate G1: the same x under a space with `lights=False, roundabouts=False`
  (flags line `lights=0 roundabouts=0`, no place tree). Applied to x0 it gives gp7_final.txt (B7) exactly. The
  upgrade tree (including the light and roundabout offer weights) is unchanged; only placement is removed.
- Pipeline: the mean after 95 generations (`d86c9a60e64c6055`, tracker `g095.txt`) played through `evaluate` from
  this worktree on its gen-95 trend-monitor map (LA 675, keyed, cap 3600) gives 1243 trips, the same as the
  training record.

Run records copied to `runs/cma-8/`: config.json, final_mean.json, generations.jsonl, status.json.

Plays (plan §5), all `evaluate` from `../mm-cma8`, keyed, cap 3600, no `--verify` (as the baselines), 50-seed runs
named `c8-<city>-<label>-<start>`:
- C\* on validation 9500-9549 and test 9600-9799, all four cities (1,000 games).
- C\* tools off on validation 9500-9549, all four cities (200 games).
The test numbers are looked at once, after the analysis script is committed and both baseline halves are fetched
and checked.
