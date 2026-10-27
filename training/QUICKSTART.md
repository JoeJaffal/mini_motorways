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
