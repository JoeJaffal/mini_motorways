# Resume review: request for approval before continuing — 8 November 2026

Written by Aya's session for Mohammad, after reading [EMERGENCY_HANDOFF.md](EMERGENCY_HANDOFF.md).
Nothing in the engine, scenarios, fixtures or tests has been changed. This commit adds only this
note, the check outputs it cites and short status pointers. We would like your approval (or
corrections) on the questions at the end before any engine or replay work starts.

## Where the work was checked

- Branch `mohammad`, tip `f7ce005` (unchanged after `git fetch upstream` on 8 November).
- A different machine from yours: no `tmp/`, no source video, no installed player or backups
  (`simulation/Builds/` does not exist). System .NET SDK 8.0.427 replaces `tmp/dotnet`.
  Unity 6000.6.0f1 is installed. Python checks ran with Python 3.12.5.
- The handoff calls the 77-suite source "uncommitted", but `f7ce005` committed it. Every engine
  file under `simulation/Assets/Simulation/` matches the copy archived in `source/` (only line
  endings differ), including the final `NativeDriveways.cs` deduplication edit.

## Measured results on the committed 77-suite source

| Check (handoff step) | Command | Result | Output |
| --- | --- | --- | --- |
| Core suites (2) | `dotnet run --project simulation/Headless/TrafficHost.csproj -- --self-test` | **PASS, 77 suites** | [core-77-dedup.txt](measurements/core-77-dedup.txt) |
| Five-map protocol (7) | `python scripts/verify_five_maps.py` (Debug host) | **PASS, 10 runs** | [maps-77-dedup.txt](measurements/maps-77-dedup.txt) |
| Environment (7) | `python test_environment.py` in `training/` | 6/7; the failure is local only | [environment-77-dedup.txt](measurements/environment-77-dedup.txt) |
| Reward v4 (7) | `python test_rewards.py` in `training/` | **5/6, real regression** | [rewards-77-dedup.txt](measurements/rewards-77-dedup.txt) |

So the deduplication edit does not break the core suites. The five-map script also rewrites the
tracked `simulation/Reports/five-map-protocol-checks.json`. Its 20-second Original runs now give
1 trip on Los Angeles, Beijing, Tokyo and Dar es Salaam, where the committed report has 0. That
report was last written on 25 October (`742ec9e`), before many engine changes, so the difference is
not attributed to 75–77. The new output is kept as
[five-map-report-77-dedup.json](measurements/five-map-report-77-dedup.json), and the tracked report
is left unchanged.

The two non-passing checks:

- **Environment:** `test_normal_roads_and_positive_reward` creates its temporary directory inside
  `tmp/`, which does not exist on this machine. This is an environment issue, not an engine result.
  It needs re-running once an empty, git-ignored `tmp/` exists.
- **Reward v4: ordinary gameplay changed between the 74-suite and 77-suite source.**
  `reward-fixture-v4.json` (ordinary Los Angeles game, 253 actions) passed on 74
  ([rewards-74.txt](measurements/rewards-74.txt)). On the current source the same commands give
  **23 trips with no game-over at 253 s**, against the fixture's **13 trips and game-over at
  252.95 s**. The first difference is at action 66 (t = 67 s): the fixture has 3 trips and the
  simulator has 2. Details: [reward-fixture-v4-replay-77-dedup.json](measurements/reward-fixture-v4-replay-77-dedup.json).
  The cause has not been isolated yet. The candidates are the native-motorway attachment (75), the
  native common-endpoint join (77) and the deduplication edit. `f7ce005` contains 59→77 in one commit,
  so the source cannot be bisected through Git; it has to be traced in code and by replaying.
  The handoff records step 7 as passing only for 74, so this appears to be a new finding.
  Any old Evolved Rules or PPO result is invalid under this source unless the change is reverted.

## What is finished, unfinished and blocked

**Finished and verified here:** the 77-suite core above. The six engine repairs listed in the
handoff exist in source with their regression suites.

**Not finished:** the reward-v4 regression above, the roundabout 19,9 queue investigation (step 5),
updating the reports (step 8) and the Unity build (step 7).

**Possible with what is in Git:**

- All engine checks and fixes, and the roundabout queue reproduction from the numeric
  [replay-candidate-v20.json](measurements/replay-candidate-v20.json) under `--run-scenario`.
- The direct topology-only check, built from the archived `source/DirectTopology.cs` with a
  temporary csproj.
- Step 3 only partly: corrections 1, 2, 5, 6 and 7 have exact edges and source times in the
  handoff, and the video-to-game clock (`custom-video-scenario-2026-11-08/measurements/clock-raw.json`)
  is in Git. They could be applied by hand to a copy of v20 as a new v21, the same way v20 was
  made, with v20 kept unchanged.
- A Unity Original build into a new staging root. Without your installed player there is nothing
  here to back up or replace.

**Blocked without your local files:**

- Step 3, correction 3: the exact interval needs source video 840–845/850.
  Correction 4: the turn time is uncertain by about 1 s and needs the video crops.
- Step 4: `build_full_trace.py` cannot run. It needs
  `tmp/full-replay-review-2026-11-08/road-changes-v7-dynamic.json`,
  `tmp/recorded-game-comparison-2026-11-08/terrain.json` and the frame boards, and
  `tmp/video-analysis-deps` (OpenCV). So v20 or v21 cannot be regenerated from the builder or
  compared with it.
- Step 6: wall-clock playback validation needs the source video.

## Proposed order once approved

1. Isolate which 75–77 change alters the v4 ordinary game, and show the exact mechanism.
   No fix, and no new fixture, until you have confirmed whether that behaviour is intended in
   ordinary play.
2. Check a reported observation bug: in `TrafficControl.cs` a car's `Waiting` seems to update only
   for cars with a movement proposal, so parked or home cars keep stale values (also check
   `TotalWaiting` and `MeanWaiting`). Reproduce it, then write a failing test, then fix it.
3. Add a simulator version string to the headless reset response, without removing any existing
   field, so result caches can key on it.
4. Reproduce the 20–38 s roundabout 19,9 queues on v20 and trace the exact stopped-car interactions
   before any change. The future-junction/yield-cycle idea stays a hypothesis until proven.
5. If approved, write a manual v21 with corrections 1, 2, 5, 6 and 7, labelled "manual, not
   regenerated from the builder". Run the topology-only check, then a strict `--run-scenario`
   (120 s wall cap, stopping at the first rejection).
6. Run the full check set again, then the Unity staging build, then update the handoff, design
   decision 069, the status files, the experiment history and the manifest.

The handoff's rules still apply throughout: no tuning toward 835, no relaxed tests, historical
fixtures not overwritten, no stock grants or ignored rejections, no training and no deployment
over an installed player.

## Questions for you

1. **Local files.** Can you share `tmp/full-replay-review-2026-11-08/` (including `trace-v20.json`,
   `road-changes-v7-dynamic.json`, `green-turn841.png`, `green-turn849.png`,
   `green-late-roads.png`, `far-right-false859.png`), `tmp/recorded-game-comparison-2026-11-08/`
   (`terrain.json` and the boards), `tmp/video-analysis-deps`, and the source video? They would stay
   local and out of Git. Optionally, also the installed 74-suite player.
2. **Native rules in ordinary play.** Are the 75 (motorway onto a native driveway end) and 77 (two
   native stubs meeting at a blank cell) joins meant to apply in every ordinary game, or only where
   the recording needs them? This decides whether the reward-v4 change is a bug or intended
   (intended would mean a new v5 fixture, with v4 kept as history).
3. **Partial v21.** Is a hand-edited v21 with only corrections 1, 2, 5, 6 and 7 acceptable while
   3 and 4 wait for your files, or would you rather wait and regenerate everything from the builder?
4. **Headless protocol.** Is adding a version field to the reset response (an addition only) fine
   for the PPO side?
5. **Anything else** we should know that the handoff does not record?
