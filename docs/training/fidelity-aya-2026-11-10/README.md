# Simulator fidelity against the original (branch `fidelity-aya`) — 10 November 2026

Aya's parallel attempt, alongside Mohammad's work on `mohammad`, to make the simulator behave as close
as possible to the original game. The two versions will be compared and the better one kept.

**User decisions (10 November 2026).** Work on a separate branch, pushed to origin. "Better" means both:
rules that match the original's code, and the recorded 835-point Los Angeles game (replay v21) landing
close to 835 at about 1314.6 s. Reading the decompiled original locally and running its components as an
oracle are allowed; decompiled code and assemblies stay outside Git (decision 077).

## Method

- **Original reference.** The installed `App.dll` (SHA256 `76c9d906…c638`, the build in
  `REFERENCE_DATA.json`) decompiled locally with ilspycmd. The real constant values come from the
  installed `core` asset bundle (`SimulationConstantsData`), dumped with [dump_constants.py](source/dump_constants.py):
  the C# field defaults in the decompiled class are **not** what the game uses (for example the
  overcrowd timer defaults 90 / 0.02 / 0.5 are overridden by 50 / 1 / 0.02, which our rules already use).
- **Five read-only audits** compared our `OriginalReference` rules with the original: demand and game
  over, dispatch and parking, vehicle motion, pathfinding, clock and progression. Findings are in the
  [results table](#changes-and-measurements) and the decision log.
- **Real score curve.** The original's HUD score was read every 10 video seconds from the recording
  (SHA256 `c9762eb1…`; video stays local) and mapped to game time with the replay's own
  video/game event pairs ([score_by_video.py](source/score_by_video.py),
  [score_timeline.csv](measurements/score_timeline.csv)).
- **Harness.** [Trace.cs](source/Trace.cs) compiles the simulator source and runs a scenario in about
  40 s, optionally overriding the five demand-wave phases. [bench.sh](source/bench.sh) runs replay v21 on
  16 fixed random phase sets ([bench-phases.txt](measurements/bench-phases.txt)) plus the fitted set,
  15 in parallel.

## Why the demand phases matter

Each colour's demand wave starts at a random offset drawn from the original's RNG. The replay's seed is a
video-hash carrier, not the original seed, so our offsets are arbitrary. On the unchanged simulator,
32 random phase sets give 380–709 trips and game over at 968–1284 s
([phase-sweep.txt](measurements/phase-sweep.txt)). A single replay score is therefore one draw; every
change is judged on the mean over the 16 fixed sets, with the range, plus the fitted set.

**Fitted phases (estimate, not recovered state).** While the city is uncongested the score tracks pin
creation, so the five offsets were fitted to the real score curve up to 1000 s with the original's demand
formula, destination spawn times and the replay's upgrade (circle) times ([fit_phases.py](source/fit_phases.py)).
Result: 0.74, 3.58, 9.68, 5.03, 20.08 days (RMSE 8.7 trips). The fit is weakly identified (later windows
move colours 1–2; colour 4 appears only at 639 s), and a better fit needs a negative delivery lag, which
suggests the replay's reconstructed event times are late by up to ~20 s in places. Treat it as one
plausible set.

**Pin creation itself matches.** With the same phases, our per-destination pin counts equal the original
formula within one pin. The original formula predicts about 860 pins by 1314.6 s, and the original
scored 835, so it delivered nearly everything; our simulator builds a backlog of 30–50 in-flight pins
before failing. The remaining gap is throughput (traffic, carparks), not demand.

## Changes and measurements

Replay v21, 16-phase mean (min–max) and fitted-phase result. Real game: 835 at ~1314.6 s.

| Version | Change | Mean trips (range) | Mean game over | Fitted phases |
| --- | --- | --- | --- | --- |
| `2026-11-08.7` | Baseline (`mohammad` 2af8e1a) | 576.6 (380–709) | 1173 s | 642 at 1235 s |
| `2026-11-10.f1` | First pin after 4 s for every destination | 606.1 (531–667) | 1190 s | 665 at 1247 s |
| `2026-11-10.f2` | Original carparks: continuous trips, no gate / bay-departure check / body-clearance limiter, same-exit merges block | 749.4 (616–804), 4/16 reach the end | 1281 s | 748 at 1279 s |
| `2026-11-10.f3` | Carpark lane speeds from the original's lane-speed rule | 772.5 (713–815), 6/16 reach the end | 1298 s | 777 at 1296 s |
| `2026-11-10.f4` | Original movement: approach-lane junction factor, ring-only roundabout speed, acceleration by current/next chunk, uncontrolled-junction slowdown, stop offset | 769.2 (645–807), 7/16 reach the end | 1295 s | 774 at 1294 s |
| `2026-11-10.f5` | 45 s intersection escape (alone: 769.4); arrival on bay-lane entry; car available on driveway entry; eviction only with a car on its way | 775.2 (605–806), 8/16 reach the end | 1298 s | 800 at 1311 s |
| `2026-11-10.f6` | Pin relocation from full destinations; original failure-timer update (banked arrivals, after movement) | 775.1 (604–806), 8/16 reach the end | 1298 s | 800 at 1310 s |
| `2026-11-10.f7` | U-turns only at dead ends, re-routes keep heading; last-destination dispatch quota; driveway excluded from house choice | 777.8 (726–819), 8/16 reach the end | 1301 s | 799 at 1307 s |
| `2026-11-10.f8` | Original lane-conflict test by directions; retired motorway penalty when re-routing | 796.7 (613–822), 15/16 reach the end | 1306 s | 824, reaches the end (1314.6 s) |
| `2026-11-10.f9` | Roundabout commitment from the previous ring tile only; roundabouts controlled for the blocked boost | 809.3 (800–822), 16/16 reach the end | 1315 s | 820, reaches the end |

Self-test: 85 suites pass at every version listed.

### f2 evidence

Waiting time by reason on f1 (fitted phases): 890 car-seconds held by the shared-exit space test and 357 by the carpark gate, with cars averaging ~4.1 s leaving and ~3.1 s entering a lot. Toggle experiments: removing the gate alone or the bay-departure check alone deadlocks within 250–600 s; the stuck cars were entering and leaving cars at the same entrance blocking each other through our body-clearance limiter, which the original does not have. Removing gate + limiter gave 657.7 mean; adding no bay-departure check 674.9; carrying speed across leg ends 737.4; ordinary entrance stop offset 748.4. A blind spot then appeared (a car could not see cars standing on the entrance lane of its next leg), so trips were made continuous as in the original rather than carrying speed. The original's connection test treats lanes with the same exit as intersecting, which closed the one aisle-merge near-collision ([Overlap.cs](source/Overlap.cs)); after f2 no two cars come within 0.2 tiles in the carpark fixtures.

## Experiments not adopted

- **Original tick length (0.1 s instead of 0.05 s), on f7:** 16-phase mean 777.8 → 762.5 (597–813), 5/16 reach the end; fitted 799 → 789 ([data](measurements/experiment-tick-0.1-on-f7.txt)). The original steps at 0.1 s, but our arbitration, dispatch quotas and tests were built around 0.05 s and the coarser step made results worse and noisier, so the step stays at 0.05 s.

- **Automatic removal of a traffic light whose tile drops below three roads, on f7:** mean 777.8 → 745.4 ([data](measurements/experiment-light-cleanup-on-f7.txt)); the motorway penalty alone was neutral (777.1, [data](measurements/experiment-motorway-penalty-only-on-f7.txt)). The original counts pending roads toward the three and the replay erases and redraws at that light, so our version removed a light the real game kept (no rebuild appears in the video). Not adopted until pending roads are modelled.

## Other checks on f7 and f8

`scripts/verify_five_maps.py` (10 runs) and `scripts/check_training_readiness.py` (60 episodes, exact replays on all five maps) pass on f7 and on f8; their reports are regenerated in `simulation/Reports/`.

