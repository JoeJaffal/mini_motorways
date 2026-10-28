# Training status — 28 October 2026

**New authorized investigation:** the user has authorized three hours of
autonomous changes/training. Opt-in connectivity inputs, spatial scoring,
informed initialization and no-op masks are being compared. The informed
training run has recorded 110 trips, but its frozen starting prior also improves
behavior; do not interpret the new record as learning alone. See the
[live protocol/results](EXPERIMENT_2026_10_28.md). Existing checkpoints remain
intact. These experimental models differ from the earlier report below.

**Latest code update:** the user authorized a connectivity reward experiment.
Training now defaults to trip delta plus discounted potential shaping; the
four-hour results below and both PDFs describe the earlier trip-only policy.
The user has since launched shaped training: a single-seed run stopped after
1,706.6 seconds/526 games (best 61), and a multi-seed run stopped after
1,721.5 seconds/687 games (best 60). Its last-100 mean was 2.58 versus initial
5.04, with different seed mixes. A separate frozen deterministic evaluation on
five unseen seeds improved from 0/2/0/0/0 to 0/2/4/4/0 (means 0.4 to 2.0).
That is limited evidence of some progress, not strong performance or proof of
shaping's benefit. [Full stopped-run assessment](../docs/training/stopped-run-assessment-2026-10-28.json).
No training is currently running at this assessment. See the
[design, audit and launch command](REWARD_SHAPING.md).

This is the current experiment summary on branch `mohammad`. `main` remains the
playground. The target is 1,000 completed trips on the first city, Los Angeles,
using OriginalReference, structured simulator data and trial-and-error learning.
The target has not been reached. OriginalReference is still an approximation;
these results do not establish performance in the commercial game.

## Current model

CPU MaskablePPO trains one shared policy across independent simulator processes.
The policy has 450,610 trainable parameters: numeric weights adjusted during
learning, not a count of rules, examples or games. Its encoder uses two small
convolution layers, combines the map with global values, and feeds policy/value
heads. It is feed-forward, with no persistent recurrent memory or observation
history. Four workers collect experience for the same policy, not four separate
models. The aggregate rollout is 256 selections, followed by PPO updates.

Historical runs used only completed-trip delta. New training defaults to that
reward plus a bounded connectivity potential difference; breaking connections
reverses their credit. `-RewardMode trips` selects the baseline. There is no
separate survival or construction-cost reward. Materials/failure rules remain
normal. Removing roads after delivery is a policy choice, not a delivery
mechanic. A small held-out improvement has been measured, but its cause and
robustness are unestablished. No explicit connectivity input has yet been added.

All ordinary construction tools are exposed through staged tool/cell selections.
Masks filter locally unavailable choices; the host checks final legality.
One completed gameplay command advances one simulated second. Intermediate
selections advance no simulation time. See the [full contract](README.md) for
the exact action and observation schemas.

## What it can and cannot see

The input is a 50-by-30 map with 50 channels plus 42 global values, rather than
screenshots. It includes terrain, infrastructure, building kinds/colors,
connections, entrances, demand, reservations, overcrowding timers, materials,
upgrade offers, time, score, motorway links and current selection state.

Traffic is aggregated per tile: car count, maximum speed and maximum current
wait. The neural network does not receive individual car colors, destinations
or planned routes. It receives no explicit label saying whether each house is
connected to a matching destination. That relationship must be inferred from
the map. It has no persistent memory between decisions. Future spawning/RNG
data and terrain outside playable bounds are excluded. Numeric input values
are clipped to the documented ranges. London-specific train observations are
not encoded; the current experiment is Los Angeles only.

## Completed four-hour run

Run: `output/training/seed-1000-parallel-02` (local, ignored artifacts).
Source revision: `e6119ebcae4632178d7aaa8aa42076ca5e962062`, clean at launch.
Resumed `seed-1000-parallel-01/latest.zip`, rather than starting from scratch.
Four workers repeatedly played seed 1000 with normal finite materials.

| Measurement | Result |
| --- | --- |
| Learner time | 14,400.7 seconds, normal completion |
| Policy selections | 2,271,492 |
| Completed commands | 1,650,223 |
| Completed games | 4,549 |
| Best score | 73 trips |
| First 100 completed games: mean score | 24.88 |
| Last 100 completed games: mean score | 52.10 |
| First / last 100 games scoring at least 50 | 7 / 75 |
| Hour 1 / 2 / 3 / 4 mean score | 31.97 / 45.92 / 52.64 / 52.64 |
| Parameter update confirmed | Yes |

Means use merged worker monitor records ordered by completion time. Hour bins
use monitor elapsed seconds; setup precedes the learner timer, and games
finishing at shutdown can fall just outside four 3,600-second bins. The first
and last 100 compare this resumed run, not an untrained policy versus final.

Held-out scores on seeds 2000, 2001 and 2002:

| Evaluation | Seed 2000 | Seed 2001 | Seed 2002 |
| --- | --- | --- | --- |
| Starting policy, stochastic | 0 | 2 | 0 |
| Final policy, stochastic | 3 | 0 | 0 |
| Final policy, deterministic | 0 | 2 | 0 |

The policy became more consistent on the practiced seed, then plateaued.
It matched the previous 73-trip record without exceeding it. These three
held-out evaluations show poor transfer; they are too small a sample to
estimate general performance precisely. Another unchanged four-hour run is
not the recommended next experiment. Investigate recurring failure cases and
the observation/action/reward bottlenecks before committing more training time.
That run had no shaping, explicit connectivity input or memory model. Shaping
has since been implemented as a new experiment; inputs/memory are unchanged.

The best exact command replay scored 73 in 461.4 simulated seconds. Replay it:

```powershell
.venv/Scripts/python.exe training/watch_best.py --run output/training/seed-1000-parallel-02 --play
```

Press Play or Space; the speed control cycles 1x, 4x and 16x. Best-game playback
is an exact recorded action sequence, not a guarantee that the final checkpoint
will repeat it. `final.zip` and `summary.json` exist for this completed run.

## Seeds, stopping and recovery

With `-SeedCount 1`, all workers keep playing the same seed for the chosen time
budget. An attempt label such as `9/100` counts the scheduling block; reaching
100 starts another block on that same seed, rather than ending training. A
failed game resets to a new episode; the policy continues learning.

The first time/selection limit stops learning. Setup and final evaluation are
outside the learner timer. Ctrl+C once saves and skips final evaluation. Wait
for the save and PowerShell prompt before closing the terminal.

An earlier parallel run crashed on Ctrl+C because console interruption killed
hosts and cleanup failed before the final save. The fix isolates host process
groups on Windows, saves `final.zip` atomically before waiting for workers,
tolerates failed worker/replay cleanup, and handles invalid closed pipes.
`seed-1000-parallel-01/latest.zip` loaded successfully at 423,892 selections and
was used for recovery; its absent final checkpoint was not reconstructed.
Periodic `latest.zip` can be about two minutes behind a crash. Always use a
fresh run name when resuming. Resume retains learned weights/optimizer state,
but starts new episodes and metrics, not the old live simulator state.

The four-hour run was launched in a new visible PowerShell window, rather than
the user's existing terminal. No continuing training or scheduled restart was
set up after its completion. Commands and recovery examples are in the
[quickstart](QUICKSTART.md).

## Viewer correction and validation

The supplied video exposed a real display mismatch: changing a driveway
detached its road connection immediately while active cars retained committed
lane snapshots and return routes. Those cars appeared to travel over grass.
The viewer now draws pale gray retiring pavement until the committed trips no
longer need it. This display query does not reconnect the road, change inventory
or reopen it to new trips. The Original Windows viewer was rebuilt.

This correction does not establish exact roundabout geometry, complete visual
fidelity or equivalence to the original game. Those broader claims remain
unvalidated; see [fidelity evidence](../simulation/Docs/FIDELITY.md).

Verification at revision `e6119eb`: 40 shared simulator suites, seven environment
tests, four workflow tests, three parallel tests, the shutdown failure test,
five-map protocol checks and repository checks passed. A four-worker inference
shutdown check saved and reloaded unchanged weights without learner updates.
The earlier 73-trip/479.8-second/480-command replay verified in both headless
and native runtimes. A matching before/after viewer capture confirmed visible
pavement under the affected car. This replay predates the four-hour run's
different 73-trip/461.4-second best recording.

## Where the evidence lives

- [Full training guide](README.md): algorithm contract and exact input channels.
- [Quickstart](QUICKSTART.md): run/resume, parallel workers, live metrics and replay.
- [First trial](first-run.md): historical initial experiment, not current results.
- Each local run directory: `config.json`, source snapshots, checkpoints,
  `worker-*.monitor.csv`, `episodes.jsonl`, `progress.csv`, `status.json`,
  `summary.json`, and best replay files. These large/generated artifacts are
  local and ignored by Git; committing documentation does not back them up.

The earlier model PDF is a historical explanation. Its unchanged 16 pages,
searchable text, graph images and underlying measurements are now preserved in
the [tracked evidence archive](../docs/training/README.md). It has not been
rewritten with newer results. Use this report for current behavior and the
[chronological history](EXPERIMENT_HISTORY.md) for decisions, updates and analysis.

An [updated 12-page current-model PDF](../docs/training/current-model-report-2026-10-28.pdf)
now includes the four-hour results, new held-out/throughput charts, model
explanation, recent fixes and limitations. Its builder and full searchable text
are also preserved in the evidence index. No new training accompanied this report.
It predates the connectivity-reward code change; the shaping specification is
the current source for the reward definition, not that historical PDF.
