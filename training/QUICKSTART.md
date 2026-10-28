# Repeated-seed training and watching the best game

Changes live on `mohammad`. No training was started while implementing them.
The objective, trip-only reward, all tools, normal material limits and failure
rules are unchanged.

## Start training

Open PowerShell:

```powershell
cd C:\Users\moham\mini_motorways
powershell -NoProfile -ExecutionPolicy Bypass -File .\training\start_training.ps1 -Minutes 30 -EpisodesPerSeed 100 -RunName seed-test-01
```

The execution-policy flag applies only to that PowerShell process. The helper
builds the headless host, then starts a fresh model. Dependencies are installed
on this PC. Use a new `-RunName` next time: existing directories are never
overwritten. You may also use the direct Python CLI in [the full guide](README.md).

The default schedule is **100 games on seed 1000, 100 on 1001, then 100 on 1002**,
through 1099, then back to 1000. Weights and optimizer state continue across seed
changes. Change `-EpisodesPerSeed 100` to 50 or 200 for shorter/longer blocks;
`-StartSeed 1000 -SeedCount 5` cycles through only seeds 1000-1004.

Repeating a layout may help practice but can also overfit. Held-out evaluation
still uses seeds 2000-2002; the CLI rejects overlapping training seeds.

The learner stops at its time or decision budget. Initial/final evaluation is
outside learner time. Press **Ctrl+C once** to save and stop learning; final
evaluation is skipped after Ctrl+C. The current partial game is also eligible
for best replay when training ends, provided at least one command completed.

To continue an existing checkpoint instead of creating fresh weights, add:

```powershell
-Resume output/training/first-full-tools/final.zip
```

Resume starts the seed schedule at its beginning and creates a new run directory.
It restores model/optimizer weights, not old simulator state, schedule counters
or previous best rankings. The earlier run's best files remain in its directory.

## Read the live output

Example only; these numbers are not new training results:

```text
SEED 1000 | block attempt 1/100 | cycle 1 | model weights continue
GAME 12 | seed 1000 try 12/100 | score 3 | seed mean 0.75 recent20 0.75 best 7 | survival 155.0s | car wait mean/max 0.10/2.00s | wait actions 20/155 | rejected 2
PROGRESS | elapsed 00:02:10 | ETA ~00:27:50 | 20,000/10,000,000 selections | 80.0 commands/s | seed 1000 try 13/100 | current score 0 at 35.0s | best 7
NEW BEST | seed 1000 | score 8 | survived 160.0s | replay: .../best-game.json
```

| Printed measurement | Meaning |
| --- | --- |
| try 12/100 | Twelfth game in the current seed block |
| seed mean / recent20 / best | Mean finished-game score on that seed, mean over its last up to 20 games, and its best finished score |
| survival | Simulated game time before failure or cap |
| car wait mean/max | Pooled mean and maximum vehicle `waiting` samples after commands, in simulated seconds; includes home/parked cars, not full-trip delay or a continuous-tick peak |
| wait actions | Deliberate no-op commands, separate from traffic delays; invalid selections also consume a wait |
| rejected | Invalid selections plus rejected gameplay commands; partially successful strokes can be accepted |
| ETA | Approximate learner time remaining until the earlier budget limit, excluding evaluation |
| commands/s | Completed game commands per wall second; a command can take multiple model selections |

Progress prints every five seconds and each completed game/new best. Read the
same data in `status.json`, detailed episodes in `episodes.jsonl`, optimizer
statistics in `progress.csv` and final per-seed statistics in `seed-summary.json`.

## See the best game in the actual playground

The rebuilt **Traffic Lab Original** Unity player supports recordings. This is
our playground, not an import into the commercial Mini Motorways game. On another
PC rebuild **Traffic Lab > Build Original Windows app** in Unity first.

Once a game has been saved, open another PowerShell in the repository root:

```powershell
.venv/Scripts/python.exe training/watch_best.py --run output/training/seed-test-01
```

That shows the final map. To watch construction and traffic from the beginning:

```powershell
.venv/Scripts/python.exe training/watch_best.py --run output/training/seed-test-01 --play
```

The replay opens paused. **Play / Space** starts it; speed cycles 1x/4x/16x;
**Step** advances a simulation tick. **Restart this replay** rereads the current
recording. **Show final map / reload best** rereads the same path, including a
new best saved while training continues. Inspection, overlays, zoom and pan work;
manual construction is disabled. Training and replay run in separate processes.
Pale gray pavement marks detached connections still needed by committed trips.
It clears when those trips finish; it does not reopen those connections to new cars.

Each run saves:

- `best-game.json`: exact actions for its best observed training game.
- `seeds/seed-N/best-game.json`: the best for each practiced seed.
- `best-policy.zip`: the policy present when the best game finished.

Ranking is highest trips, then longer survival, then fewer rejections. An
unfinished game is marked partial when saved at training shutdown. Held-out
evaluation does not overwrite the training best. An episode can span optimizer
updates: **the command file is the exact replay**, while the end-of-game policy
checkpoint is not guaranteed to regenerate that same game.

Both .NET and Unity validate acceptance, score and time after every command and
stop on divergence. This reproduces normal gameplay; it never grants stock or
uses debug roads. Simulator changes may invalidate older recordings.

The earlier seven-trip exploratory game was not recorded, so it cannot honestly
be reconstructed now. For a preview without training, an **inference-only,
zero-trip demonstration** from the existing final checkpoint is available:

```powershell
.venv/Scripts/python.exe training/watch_best.py --replay output/replays/existing-checkpoint-demo.json --play
```

## Validate without training

```powershell
./tmp/dotnet/dotnet.exe build simulation/Headless
.venv/Scripts/python.exe training/test_environment.py --dotnet ./tmp/dotnet/dotnet.exe -v
.venv/Scripts/python.exe training/test_workflow.py --dotnet ./tmp/dotnet/dotnet.exe -v
./tmp/dotnet/dotnet.exe simulation/Headless/bin/Debug/net8.0/TrafficHost.dll --verify-replay output/replays/existing-checkpoint-demo.json
```

These run scripted fixtures, test doubles or existing-checkpoint inference; they
do not call the learner or update model weights.

## Run several games in parallel

Add `-Workers 2` or `-Workers 4` to the PowerShell helper. The default remains one
worker for compatibility. Workers are separate simulator processes collecting
experience for **one shared model**, whose neural-network calls are batched.
They sample different actions even when they all play seed 1000.

To switch the active three-hour run, press Ctrl+C once and wait for `final.zip`
to finish saving. Then continue its weights with four games on seed 1000:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\training\start_training.ps1 -Minutes 180 -StartSeed 1000 -SeedCount 1 -Workers 4 -RunName seed-1000-parallel-01 -Resume output/training/seed-1000-three-hours/final.zip
```

Use the actual stopped run's directory if it differs. Use a new `-RunName` for
each launch. This starts a new training session; do not leave the old session
running if you want all CPU capacity available to the parallel session.

On Ctrl+C, wait for `CHECKPOINT SAVED` and then the PowerShell prompt. The model
is saved before worker cleanup, so a failed simulator cannot block that save.
If an older run crashed before creating `final.zip`, resume its `latest.zip`
instead. That periodic checkpoint can be up to about two minutes behind the
crash. The best replay remains available independently.

For recovery from `seed-1000-parallel-01`, use a fresh output directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\training\start_training.ps1 -Minutes 180 -StartSeed 1000 -SeedCount 1 -Workers 4 -RunName seed-1000-parallel-02 -Resume output/training/seed-1000-parallel-01/latest.zip
```

The console labels completed games by `worker 0`, `worker 1`, etc. Commands/s
and selections/s count **all workers combined**. Per-seed means combine their
finished games. Each worker has its own attempt counter and, with multiple
training seeds, advances its seed blocks independently. With `-SeedCount 1`
all workers remain on seed 1000 for the full time budget.

Best-game selection compares every worker, including partial games when stopped.
The same `watch_best.py --run ...` command opens the global best; the replay JSON
also records its worker ID. Monitor logs are now `worker-00.monitor.csv`,
`worker-01.monitor.csv`, etc. `status.json` includes every worker's latest status.

The aggregate PPO rollout is held at 256 selections: 256 per worker with one
worker, 128 with two and 64 with four. Batch size and learning rate stay the same.
Shorter individual fragments can affect learning with delayed rewards; faster
throughput is not a guarantee of faster score improvement. Reward, observations,
allowed tools, game timing and simulator rules are unchanged.

### Measured short benchmark

Six isolated 12-second learner trials used worker counts 1, 2, 4, 4, 2, 1, after
one warm-up rollout each. All started from the same immutable old checkpoint;
they did not overwrite the active run or its files. The user's existing training
session was still running, so these are **under-load comparisons**, not clean
hardware maximums. Two PyTorch threads were used in all trials.

| Concurrent games | Mean selections/s | Mean completed commands/s |
| --- | --- | --- |
| 1 | 106.5 | 60.3 |
| 2 | 123.4 | 70.3 |
| 4 | 125.4 | 74.9 |

Four workers yielded about 24% more completed commands/s than one here. Two
yielded about 17%. These trials are too short to compare learned playing skill
or stable completed-games/s, especially with partially finished games at stop.
Raw results are local at `output/benchmarks/parallel-first/results.json`.

To repeat an isolated speed benchmark yourself:

```powershell
.venv/Scripts/python.exe training/benchmark_parallel.py --dotnet ./tmp/dotnet/dotnet.exe --seconds 15
```

Unlike the scripted validation tests, this benchmark **does perform short learner
updates** on disposable clones, in separate benchmark directories. It does not
resume or replace your production run. Prefer stopping other training first for
cleaner speed measurements.
