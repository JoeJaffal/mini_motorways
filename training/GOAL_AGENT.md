# Experimental planner-aided connection policy

The newer **traffic-light v3** option and overnight command are documented in
[SIGNALS.md](SIGNALS.md). The v1/v2 contracts below remain available and preserve
their old checkpoint shapes.

This is a separate model/action abstraction, not a replacement for the primitive
all-tools MaskablePPO agent. The [investigation protocol](EXPERIMENT_2026_10_28.md)
distinguishes engineered assistance from improvement attributable to learning.

## What it does

The current-state router proposes affordable matching-color house/destination
connections. PPO selects a connection, upgrade, or waiting. The router executes
ordinary straight road strokes; the simulator enforces normal finite resources,
construction, traffic and failure. Each macro decision can span several one-second
commands. Waiting executes up to five, stopping early on growth, upgrades or end.

In v1/v2, motorways, roundabouts, lights, demolition and manual driveway edits are excluded.
Bridges can arise from ordinary water-crossing strokes. The router is not optimal;
approximate route costs do not prove every proposal will be accepted. There are
no stock grants, future spawns, debug construction or teacher trajectories.

## Inputs and architecture

### Optional congestion model v2

Use `--congestion-aware` for a fresh `visible-route-congestion-policy-v2` model.
It adds a live 4 x 30 x 50 visible map: vehicle count / 10, maximum vehicle wait
/ 60, road presence, and connection degree / 8. Values are clipped to [0,1];
hidden cells are zero. This is a snapshot, not measured vehicles/second, lane
capacity or predicted travel time. Counts include visible simulator vehicles.

Candidate rows have 32 values: the original 25 plus bypass flag, reference-route
mean vehicle count / 10 and maximum wait / 60, proposed-route fraction of cells
with waiting >= 3 seconds, maximum vehicle count / 10, maximum junction wait / 60,
and junction fraction. Junctions have at least three connections. All live values
refresh every decision. A small convolutional encoder reads the map and supplies
32 context values to tool logits and the critic. Candidate scoring sees the
route summaries. Total parameters: **18,205**. The reward is unchanged.

An optional engineering heuristic searches for bypasses on already connected
matching-color pairs. It uses a conservative existing-road reference path, needs
at least 3 seconds of observed waiting, and adds per-cell routing cost
`0.3 * min(vehicle_count, 10) + min(wait, 60) / 15`. Proposals must add physical
road tiles, fit current road inventory, and reduce summed reference-path load
by at least 20%. This is a proposal heuristic, not a guarantee of reduced traffic.
Search refreshes on network/resource/bounds changes and every 15 simulated seconds;
the full traffic map and candidate summaries refresh every decision. Up to 64
bypasses fill remaining candidate slots after new connections; overflow of the
original connection proposals still raises an error. Construction uses ordinary
commands and simulator resource enforcement, with no demolition or stock grants.

Cars still choose routes using the simulator's travel costs; building a bypass
does not force cars to use it. Reference paths can differ from actual vehicle
journeys. The conservative path check may miss a usable bypass. No existing
road is removed, so this does not yet support full network redesign.

Old goal checkpoints remain v1. Changing the flag while resuming is rejected;
start a fresh v2 model. Saved v2 models automatically restore the new inputs on
resume and evaluation. A three-map frozen comparison was mixed: old live v1
and v2 without bypasses both scored 161/85/115 (mean 120.3); v2 with bypasses
scored 79/209/82 (mean 123.3). Two maps worsened. This is an engineering comparison,
not evidence of learning or a reliable improvement. See
[comparison evidence](../docs/training/congestion-v2-2026-10-28/README.md).

Recommended first trial (four workers, 30 learner minutes, new output name):

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\train_goal.py --output output/training/congestion-v2-01 --minutes 30 --workers 4 --congestion-aware --reward-scale .01
```

Initial/final evaluation adds time. Compare `before.json`, `after.json` and
`validation.jsonl` on the same development maps, rather than interpreting training
best as learning. Ctrl+C saves. For a later continuation use a fresh output name
and `--resume output/training/congestion-v2-01/final.zip`; the schema is inherited.
Use `validation-best.zip` when deliberately selecting the best validation policy;
this differs from a continuation of the final optimizer. Do not use old
investigation final test seeds for tuning this development change.

### Original v1 inputs

Schema `visible-route-goal-policy-v1` supports up to 512 candidate rows, each with
25 values. Overflow raises an error instead of silently truncating.

| Candidate indices | Current-state values |
| --- | --- |
| 0-5 | Home/destination x/y and displacement, normalized by 50/30 |
| 6-13 | Eight color indicators |
| 14-16 | New road tiles / 100, route length / 100, demand / 20 |
| 17-19 | Missing house supply, missing destination supply, existing-road fraction |
| 20-23 | Mean route traffic / 10, maximum waiting / 60, overcrowding / 50, new water tiles / 10 |
| 24 | Valid candidate |

The 42 globals retain primitive indices 0-24: materials, current time, week, trips
and offers. Indices 25-36 contain current week phase, connected-house fraction,
unsupplied-destination fraction, candidates / 512, houses / 100, destinations / 20,
active cars / 200, demand / 100, max overcrowding / 50, mean/max waiting / 60 and
occupied infrastructure cells / 1500. Indices 37-41 are zero. Week phase derives
from current clock modulo the 140-second simulated week. Values are clipped.
Route geometry is cached on topology/resource/bounds changes; traffic, waiting,
demand and overcrowding refresh at every decision, including cache hits. Traffic
is a snapshot count of vehicles in visible integer map cells, averaged across
the proposed route; waiting is the maximum vehicle waiting value along it.
These are not lane-level flow, utilization, queue length or travel-time forecasts.
The 25-value input layout and checkpoint tensor shapes remain compatible, but
inference behavior can change because formerly stale summaries are now live.
Historical investigation scores used the earlier cached measurements; no new
performance benefit has been measured. Structured diagnostics are not
claimed equivalent to pixels visible to a human. Future state is excluded.

A shared 25->32->32 network and trainable linear prior score candidate rows.
Globals score wait/upgrade actions. Mean/max pooled candidate features and globals
feed a 64-unit critic. There are **10,334 parameters** and no recurrent memory.
The informed initial prior favors low cost, demand and missing supply; offers
receive a fixed upgrade bias. These are engineered choices. Compare against the
frozen initial checkpoint to establish whether learning improves performance.

## Learning and reward

Unscaled reward per macro decision is actual trip delta plus
`0.99 * next_potential - previous_potential`, with potential
`0.25 * min(usefully_connected_houses, 8)`. True failure resets potential to zero;
external caps bootstrap live potential. This is macro-decision discounting,
not elapsed-time discounting; action durations therefore matter.

PPO: gamma/lambda .99, aggregate rollout 256, batch 64, four epochs, learning rate
.0001, entropy .005. Workers collect experience for one shared policy. Training
seeds 1000-1099 are randomly sampled; development seeds 2000-2004; final test
3000-3009. Final tests are not used for subsequent selection or optimization.

`--reward-scale .01` changes only numerical learning rewards, including shaping.
Scores/replays always use unscaled actual trips. The scale comparison starts
from the exact same frozen initial checkpoint. Scaling changes optimization
balance and is an experiment, not a simulator change or proven improvement.

## Run explicitly

```powershell
cd C:\Users\moham\mini_motorways
.\tmp\dotnet\dotnet.exe build .\simulation\Headless
.\.venv\Scripts\python.exe .\training\train_goal.py --output output/training/my-goal-experiment-01 --minutes 30 --workers 4 --reward-scale .01
```

This creates a fresh informed goal policy. Add `--resume` with a **goal-policy**
checkpoint to continue weights/optimizer; primitive checkpoints are incompatible.
Resume inherits its learning rate, reward scale and decision timing unless you
explicitly override them. Old goal checkpoints without a scale attribute read
their neighboring config; keep it alongside the checkpoint. New checkpoints save
the scale. `--learning-rate .001` explicitly changes rate;
`--no-skip-forced-wait` explicitly restores five-second-wait timing.
Use a fresh output folder. Initial/final evaluation adds time outside the learner
budget; periodic validation consumes learner time. Output shows elapsed/remaining
time, seed scores, waiting, connections, best replay and validation. Macro
decisions, primitive selections and completed commands are different quantities.

Ctrl+C saves and stops; `--stop-file PATH` supports graceful stopping. No recurring
run is created. Final evaluation can be skipped after interruption.

`--skip-forced-wait` is another explicit experiment. After a chosen macro finishes,
it advances ordinary one-second commands while waiting is the only legal action,
checking for new connections/upgrades/end after every command. This reduces
value-free neural calls but also changes the effective discount/credit horizon:
schema `goal-trip-potential-gamma099-choice-v1`. The checkpoint stores the timing
mode and evaluation restores it. Fresh models default to five-second waits;
resumed models inherit their saved mode. A paired
frozen-policy check verified identical ordinary command histories at a 180-second
cap; the broader experiment still needs measured validation.

```powershell
.\.venv\Scripts\python.exe .\training\watch_best.py --run output/training/my-goal-experiment-01
```

Add `--play` to start paused at the beginning. Native viewer labels planner-aided
replays; recordings contain exact ordinary commands and support cross-runtime
verification. Episodes can span PPO updates and sampled actions. The action record
is the authoritative best-game reconstruction; its end checkpoint is a snapshot.
Weights/binaries stay local; code, small evidence and reports are archived in Git.
