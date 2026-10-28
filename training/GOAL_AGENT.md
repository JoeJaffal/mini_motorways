# Experimental planner-aided connection policy

This is a separate model/action abstraction, not a replacement for the primitive
all-tools MaskablePPO agent. The [investigation protocol](EXPERIMENT_2026_10_28.md)
distinguishes engineered assistance from improvement attributable to learning.

## What it does

The current-state router proposes affordable matching-color house/destination
connections. PPO selects a connection, upgrade, or waiting. The router executes
ordinary straight road strokes; the simulator enforces normal finite resources,
construction, traffic and failure. Each macro decision can span several one-second
commands. Waiting executes up to five, stopping early on growth, upgrades or end.

Motorways, roundabouts, lights, demolition and manual driveway edits are excluded.
Bridges can arise from ordinary water-crossing strokes. The router is not optimal;
approximate route costs do not prove every proposal will be accepted. There are
no stock grants, future spawns, debug construction or teacher trajectories.

## Inputs and architecture

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
Cached route traffic refreshes on topology/resource/bounds changes; candidate
demand/overcrowding refresh every observation. Structured diagnostics are not
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
