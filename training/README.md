# Local reinforcement learning experiment

This training project lives on branch `mohammad`. Branch `main` remains the
playground. Nothing in the simulator's rules, material stocks, spawning, failure
conditions or diagnostic helpers is changed by training.

The objective is 1,000 completed trips on Los Angeles in OriginalReference.
This is a research target, not a claimed result or a verified simulator capacity.
Transfer to the commercial game is untested.

## Install and check

Use Python 3.12 and the .NET 8 SDK. From the repository root in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python.exe -m pip install -r training/requirements.txt
dotnet build simulation/Headless
.venv/Scripts/python.exe training/test_environment.py --dotnet dotnet -v
```

On this PC, a local SDK is available at `tmp/dotnet/dotnet.exe`; substitute that
path wherever `dotnet` is passed if the SDK is not on PATH. The environment and
SDK are ignored local dependencies, not committed files.

## Run

```powershell
.venv/Scripts/python.exe training/train.py --dotnet ./tmp/dotnet/dotnet.exe --minutes 30 --steps 65536
```

The first limit reached stops training. `--minutes` measures the learner, including
its simulator interaction and optimization; setup and evaluation are separate.
The timer is checked at policy decisions, so an in-progress simulator request
(30-second timeout), optimizer update or checkpoint write can slightly overrun it.
Defaults use two PyTorch CPU threads and one persistent headless host process.

Each run has a new directory under `output/training/`, containing configuration,
exact training source snapshots, initial/latest/final checkpoints, per-episode
metrics, optimization CSV, progress status and a final evaluation summary.
Evaluation reloads the final checkpoint. Interrupted learning saves the current
model and then evaluates it. Crashes/timeouts raise integration errors rather
than being scored as game failures.

To continue an explicitly chosen checkpoint in a new run directory:

```powershell
.venv/Scripts/python.exe training/train.py --dotnet ./tmp/dotnet/dotnet.exe --resume output/training/RUN/final.zip --minutes 30
```

Resuming retains policy/optimizer weights, but starts new simulator episodes,
new run metrics and a fresh timestep counter. It is not an exact continuation
of the old simulator/RNG/rollout state.

## Experiment contract

- Algorithm: CPU MaskablePPO, compact convolutional encoder for structured grids.
  This uses the [SB3-Contrib action masking API](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html).
- Training seeds: 1000–1099; held-out evaluation seeds: 2000–2002 by default.
  Reset explicitly uses LosAngeles, OriginalReference and normal finite materials.
- Reward: change in total completed trips across the entire gameplay command and
  subsequent time step. No survival bonus, construction penalty or reward shaping.
- Episodes: normal game failure terminates; an external 3,600 simulated second
  safety cap truncates. A 1,000-trip score is not an artificial stopping condition.
  Rejected scenarios and protocol errors abort instead of entering the learner.
- Time: one gameplay command, then 20 ticks (one simulated second). Invalid or
  rejected commands consume that interval too. Reset initializes the score baseline.
- Tool selection: choose a tool, then its cells. Wait and upgrade choices finish
  immediately. Builds/removals select one cell; road strokes, driveway changes and
  motorways select two; motorway editing selects an existing endpoint plus two
  replacement endpoints. At most four policy decisions complete a command.
  Intermediate selections have zero reward/time and cannot loop. A dead-end
  selection completes a wait. The 1,513-way discrete action vocabulary uses
  1,500 cell IDs and 13 tool/upgrade IDs, with a phase-dependent mask.
- All ordinary tools are available when their resources/targets are available:
  draw/connect road strokes, single roads, bridges, traffic lights, roundabouts,
  demolition, house driveways, motorway creation/edit/removal, upgrades and waiting.
  No path planner, suggested routes, debug reference roads, stock grants or lab
  reset commands are policy actions. Masks check local feasibility; the host
  decides final legality, including partial strokes and crossing conflicts.

## Observation allowlist

The policy receives a `50 x 30` grid with 50 channels and 42 global values.
All grid channels are zero outside the currently playable bounds. No building or
vehicle list is truncated: visible entries are rasterized or aggregated by cell.

Grid channels, in order:

| Indices | Current-state data |
| --- | --- |
| 0 | Playable-cell visibility |
| 1–3 | Terrain categories |
| 4–8 | Infrastructure categories |
| 9–11 | Building-kind categories |
| 12–19 | Building-color categories |
| 20–27 | Eight road-connection bits |
| 28 | Pending demolition |
| 29–31 | Demand / 20, reservations / 20, overcrowding timer / 50 |
| 32–39 | Eight driveway/entrance directions |
| 40–42 | Vehicle count / 10, maximum speed / 2, maximum current waiting / 60 |
| 43–47 | Motorway endpoint, pending retirement, other endpoint x / 50 and y / 30, number / 20 |
| 48–49 | Selected first cell and selected motorway's existing endpoint |

Globals contain six inventory counts (roads / 100, other materials / 10), elapsed
time / cap, week / 100, trips / 1000, two upgrade offers (six type indicators,
amount / 100, roads / 100), four selection phases and thirteen selected tools.
Numeric values saturate to [0, 1]; finite values are checked. Unknown color IDs,
more than two offers or changed grid sizes raise an error instead of dropping data.

These include current internal diagnostics such as reservations and overcrowding
timers; they are a documented structured-state interface, not a pixel-equivalent
reconstruction of player information. Future `scheduledSpawns`, `upgradeAt`,
`plannedDemandMultiplier`, RNG state/diagnostics and offer generation weights are
excluded from policy inputs. The current encoder is designed for Los Angeles;
London train/rail-specific features would require an encoder revision before
meaningful training there.

## Interpret results

`summary.json` separates training scores, stochastic held-out evaluation and
deterministic held-out evaluation, including failures versus external caps. It
also records actual policy-weight changes, elapsed time, policy decisions/second
and completed commands/second. Evaluation uses the same masks as training.

A short sparse-reward run may score zero: generating roads that complete a trip
is a difficult exploration problem when all coordinates and tools are learned
from scratch. Checkpoint creation and optimizer updates demonstrate a working
pipeline; they do not demonstrate a learned road-building strategy. Use held-out
scores, not just training reward or a single seed, to decide on longer runs.
