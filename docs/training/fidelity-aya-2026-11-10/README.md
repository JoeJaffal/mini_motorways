# Simulator fidelity against the original (branch `fidelity-aya`) — 10 November 2026

Aya's parallel attempt, alongside Mohammad's work on `mohammad`, to make the simulator behave as close
as possible to the original game. The two versions will be compared and the better one kept.

**User decisions (10 November 2026).** Work on a separate branch, pushed to origin. "Better" means both:
rules that match the original's code, and the recorded 835-point Los Angeles game (replay v21) landing
close to 835 at about 1314.6 s. Reading the decompiled original locally and running its components as an
oracle are allowed; decompiled code and assemblies stay outside Git (decision 077).

## Current state (12 November 2026, simulator `2026-11-10.f27`)

- **Benchmark:** replay v21d (event times read from the game's clock dial) on 60 demand-phase sets refitted to the dial-timed real score curve.
- **Scores:**
  - f24: 805.5, 22/60 runs reach the end.
  - f25, after the original's junction exit-space formula: 783.4.
  - f26: 773.5; the median run is unchanged, and one run collapses.
  - f27 (review fixes, decision 116): 771.9.
  - The original scored 835 and ended at about 1314.6 s.
- **Where it differs:** up to about 1000 s our runs follow the real curve within 5–13 trips. The gap opens in the late game, when our congestion ends the game earlier.
- **Rules ported overnight from the decompiled code:**
  - crossing diagonals (f23);
  - gridlock cycles, roundabout activation and level crossings (f24);
  - re-plan, exit space and registration stamps (f25);
  - traffic-light details and the weekly offer draw (f26).
- **Kept although it lowers the replay:** the exit-space formula (decision 112, -16.6). It is the original's code; see "f25" below.

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
| `2026-11-10.f10` | Original motorway end tiles (ordinary start lane to the slot, straight motorway lane between slots, full end-tile lane) | 792.8 (741–809), 12/16 reach the end | 1309 s | 816, reaches the end |
| `2026-11-10.f11` | Signal pair order, post-amber hold and pair-loss switch; roundabout exit-lane factor | 784.5 (747–808), 8/16 reach the end | 1304 s | 784, fails at 1301 s |
| `2026-11-10.f12` | Merge of `fidelity-aya-growth` (original free-play placement; replays unaffected) | 784.5 (747–808), 8/16 reach the end | 1304 s | 784, fails at 1301 s |
| `2026-11-10.f13` | Motorway slots count as roads on end tiles; exit-lane cars not circulating | 762.9 (584–803), 5/16 reach the end | 1289 s | 795, fails at 1308 s |
| `2026-11-10.f14` | Roundabout placement as the original (exits kept and paid, no automatic links, ring links cost 1) | 791.4 (763–804), 14/16 reach the end | 1313 s | 807, reaches the end |
| `2026-11-10.f15` | Stored return paths re-routed when a link they use is erased; ring exits erasable | 788.3 (735–805), 13/16 reach the end | 1311 s | 808, reaches the end |
| `2026-11-10.f16` | Diagonal steps through the original's tile-corner lanes | 791.1 (740–809), 13/16 reach the end | 1312 s | 791, fails at 1310 s |
| `2026-11-10.f17` | Bridge stock by crossing (parallel bridges pay separately, joins refund, erased bridges refund) | 791.1 (740–809), unchanged: the replay has no parallel bridges | 1312 s | 791, fails at 1310 s |
| `2026-11-10.f18` | Strokes keep stepping past an unaffordable link; strokes into a house turn its driveway | 791.1, unchanged (no such strokes in the replay) | 1312 s | 791, fails at 1310 s |
| `2026-11-10.f19` | Lights only on tiles with three or more roads, not on rail | 791.1, unchanged (both replay lights qualify) | 1312 s | 791, fails at 1310 s |
| `2026-11-10.f20` | Full-lot drive-through crosses the nearest bay behind its parked car | 791.1, unchanged (no lot fills in the replay) | 1312 s | 791, fails at 1310 s |
| `2026-11-10.f21` | No junctions on bridge tiles; no links from bare water | v21b on the 20 plausible phase sets unchanged (791.5): the replay's bridges have no junctions | | |
| `2026-11-10.f22` | Motorway ramps take a free side by the original's pair score and block it | v21r: 784.0 (626–805), 13/16 reach the end (f21: 791.1 (740–809), 13/16). Plausible phases, v21c: **801.4** (755–831), 6/20 reach the end (f21: 791.5) | 1306 s | 802, reaches the end (f21: 791, fails at 1310 s) |

Self-test: 85 suites pass at every version listed (92 from f12 with 7 placement suites, 93 from f16 with the tile-corner check, 94 from f18 with the house-driveway stroke check).

### f2 evidence

Waiting time by reason on f1 (fitted phases): 890 car-seconds held by the shared-exit space test and 357 by the carpark gate, with cars averaging ~4.1 s leaving and ~3.1 s entering a lot. Toggle experiments: removing the gate alone or the bay-departure check alone deadlocks within 250–600 s; the stuck cars were entering and leaving cars at the same entrance blocking each other through our body-clearance limiter, which the original does not have. Removing gate + limiter gave 657.7 mean; adding no bay-departure check 674.9; carrying speed across leg ends 737.4; ordinary entrance stop offset 748.4. A blind spot then appeared (a car could not see cars standing on the entrance lane of its next leg), so trips were made continuous as in the original rather than carrying speed. The original's connection test treats lanes with the same exit as intersecting, which closed the one aisle-merge near-collision ([Overlap.cs](source/Overlap.cs)); after f2 no two cars come within 0.2 tiles in the carpark fixtures.

## Remaining replay gap: the replay gives our simulator less demand than the original had

- **After the last event.** With the replay extended to 1500 s and no further player actions, f9 fails between 1337 s and 1490 s, or survives (4/17 runs) ([data](measurements/extended-to-1500s-f9.txt)); the original failed at about 1314 s while the player was still building.
- **Pins on screen at ~1260 s** (video 900 s, upgrade screen, score 809), read by eye: red 10,8 full (6 pins); red 16,16, red 11,18 and red 30,18 overcrowding (timers, 7+ each); yellow 16,16 (upgraded) about 7; navy 12,14 3; others 0–2. The simulator at 1260 s with the fitted phases: red 3, 4, 6, 5 (none overcrowding), yellow 16,16 3, navy 8. Visible real pins plus score imply roughly 865 pins created by 1260 s, against about 790 from the original's demand formula with the replay's spawn and upgrade times, which our simulator reproduces within a few pins.
- **Interpretation.** The real game had roughly 10% more demand, concentrated on red. Candidates are hidden state the replay cannot carry: extra demand while scheduled destinations were delayed (two red destinations appear after their plan windows close), and errors in the reconstructed event times between week anchors. This is not adjusted by tuning; it explains why the replay score sits about 2% below 835 while our runs outlast the real game.

### Replay v21a: the two provably late red destinations

The LA plan (`City.cs` schedule: item time = slot midpoint × (1 − variation) + sorted uniform draw × variation) bounds when each destination can be scheduled. Two red destinations in the recording appear after the latest possible time: the shared lot at 17,17 (chunk days 8–22, item max 405 s, appears 474 s) and the shared lot at 12,19 (chunk days 30–42, item max 810 s, appears 919 s). While a scheduled destination waits, the original retries placement every 20 s and adds extra demand to its colour. [replay-candidate-v21a.json](replay-candidate-v21a.json) adds an optional `scheduledAt` to those two events at the latest possible time (a lower bound on the delay); the replay session then keeps a delayed plan entry for each until it appears, so the simulator's existing failed-spawn demand rule applies. A third case (yellow 26,18 or red 30,18 in chunk days 16–36, ≥ ~100 s late) is left out because it is ambiguous which of the two was late; the missing blue destination of chunk days 40–76 is left out because its slot is unknown.

On f15: v21 mean 788.3 (735–805), fitted 808 at the end; v21a mean 774.2 (630–815), median 796.5, 9/16 reach the end, fitted 815 at the end ([data](measurements/bench-f15-replay-v21a.txt)). Extra red demand moves the fitted run toward 835 and makes red the stressed colour, as in the video, but the lower-bound delays close only part of the gap. `REPLAY=<file> source/bench.sh <tag>` runs the benchmark on another replay.

### Replay v21b: circle conversion settles the third late destination (11 November 2026)

**The plan's upgrades explain it.** The LA plan items carry a grouping; grouping 3 is a circle (an upgrade of an existing destination, `BuildingSpawningProcess.LevelUpDestinationBasedOnAge`). A circle that finds no eligible destination of its colour (non-upgraded, carpark on a circle-zone tile) retries every 20 s (`FailedDestinationRetryDelay`); at the attempt after its sixth failure it becomes an ordinary destination of that colour and is placed at the next retry, so it appears at least 140 s after it was scheduled. While it waits its colour gets the failed-spawn extra demand. The recording shows no upgrade before 1030 s, although the plan schedules a yellow circle in chunk days 16–36 and a red circle in chunk days 30–42. Both failed and became ordinary destinations:

- **Yellow 26,18 (appears 652 s)** is the converted yellow circle. In chunk days 16–36 (yellow circle, cyan, red; variation 0.15) cyan at 383 s must take slot 0, so the circle is slot 1 (490–550 s) and, from the 140 s minimum, was scheduled by 512 s. Red 30,18 at 662 s is slot 2 (603–663 s) and on time, which resolves the earlier yellow-or-red ambiguity.
- **Red 12,19 (appears 919 s)** is the converted red circle. In chunk days 30–42, green at 639 s is slot 0, so the circle is slot 1 (690–810 s) and was scheduled by 779 s (v21a used the plan bound 810 s).
- **Red 17,17** stays at 405 s (red item of chunk days 8–22, slot 2).

[replay-candidate-v21b.json](replay-candidate-v21b.json) sets these three `scheduledAt` values, each the latest possible time, so the delays are lower bounds. No simulator change is needed: the replay session already applies the failed-spawn demand rule to `scheduledAt` events.

**The real score curve supports it.** Refitting the five demand phases to the real score curve up to 1000 s with this extra demand ([fit_phases.py](source/fit_phases.py), `DELAYED=...`) lowers the error from 8.7 to 3.9 trips. The fit also no longer needs a zero delivery lag: it finds a lag of 6.5–9 s ([fits](measurements/phase-fits-v21b.txt)). Twenty independent fits agree on yellow (1.7–2.4 days), red (3.7–5.5), navy (5.6–7.6) and green (5.5–7.2); cyan has three families (about 1.2, 3–4 and 10.6–11.5). The 20 fitted sets ([plausible-phases-v21b.txt](measurements/plausible-phases-v21b.txt)) replace random phases for judging the replay, because many random sets contradict the real score curve (on f20, v21b on the 16 random sets ranges 361–841, [data](measurements/bench-f20-replay-v21a-v21b-random.txt)). [bench_plausible.sh](source/bench_plausible.sh) runs a replay on them.

| On f20, 20 plausible phase sets | Mean | Median | Range | Reach the end | Mean end |
|---|---|---|---|---|---|
| Replay v21b | 791.5 | 793.5 | 744–824 | 4/20 | 1297 s |
| Replay v21 | 784.8 | 786 | 743–801 | 11/20 | 1309 s |
| Original (recording) | 835 | | | ends at ~1314.6 s | |

Data: [v21b](measurements/bench-f20-replay-v21b-plausible.txt), [v21](measurements/bench-f20-replay-v21-plausible.txt).

**What remains is throughput, not demand.** With the best fit (1.737 4.767 4.153 5.908 6.680), our pins per destination match the original formula within one pin (850 against 854 by 1284 s). Our score still trails the real curve by 5–15 trips from 450 s, and the run fails at 1284 s with 778. Pins wait only 1–3 s for a car until 1000 s; the difference is the time from dispatch to delivery (12.5 s in 200–500 s, 17.7 s in 500–800 s, 22.7 s in 800–1000 s by Little's law). The real game's fitted lag in the same windows (0, 4 and 12 s) is shorter than any physical trip, so part of this offset is timing error in the reconstructed replay. Car speeds, the ×3 movement factor, lookahead speed averaging, dispatch quotas, the 4 s first pin, and scoring on bay entry all match the original. The last part of the gap is congestion at the red lots near the end, where the video also shows red overcrowding.

### Replay v21c and v21r: two same-second reorderings (f22)

From f22, a motorway ramp's side of its end tile takes no road, as in the original (`Tile.CanSetNodeState`), and each ramp's direction is chosen once, when the motorway is placed (`AddMotorwayAction` pair score). Replay v21 then fails at event 246. In two places the player's stroke into a new motorway end is recorded in the same video second as the motorway, and after it: the m2 edit and stroke 24,15→25,15 at 966.2 s (video 667 s), and motorway m4 and stroke 20,18→21,18 at 1306 s (video 1000 s). In both, the ramp would take exactly the side the stroke uses if the motorway came first, so the recorded layout is only possible with the stroke first. [replay-candidate-v21c.json](replay-candidate-v21c.json) is v21b with those two pairs swapped; it is now the benchmark replay. [replay-candidate-v21r.json](replay-candidate-v21r.json) is plain v21 with the same two swaps and no late-destination annotations. Use it to compare this branch with `mohammad` on the same input. The swaps change nothing on f21 (v21c and v21b give the same 791.5).

Data: [v21c on f22 and f21](measurements/bench-f22-replay-v21c-plausible.txt), [v21r on f22 and f21](measurements/bench-f21-f22-replay-v21r-random.txt).

### Car speed measured in the recording (11 November 2026)

At video 116–121 s the HUD shows normal speed (play highlighted, fast-forward dimmed). The clock dial changes between its day and night faces every 5.0 video seconds (2 frames per second, 10 frames per face), and half a day is 10 game seconds, so the game runs **2 game seconds per video second**. That is also the slope of the replay's video/game time pairs there (162 s ↔ video 100, 248 s ↔ video 143). One tile is 100 pixels at 1920×1200 at that zoom: the yellow lots at 16,7 and 15,11 are 400 px apart vertically and 100 px horizontally. A red car on the top straight moves 57 px per 0.2 video seconds, which is **1.43 tiles per game second** (our free straight speed: 1.5). Braking into a right-angle turn it slows to about **1.1** (ours: 1.0 after the 2/3 turn factor). Real car speeds agree with the simulator. So the roughly 11 s longer dispatch-to-delivery time in our replays (see "What remains is throughput") does not come from car speed. With the same roads it most likely comes from the replay's reconstructed event times, consistent with the real game's impossible zero lag in 200–500 s.

### Crossing diagonals (f23, 11 November 2026)

In the original, two diagonals may cross at a tile corner on land. The corner becomes a junction with four nodes, where cars cross and can also turn onto the other diagonal. It is refused only when the new link starts or ends on water (`TileEditor`). Ours refused every crossing. f23 accepts it and routes through the corner, both straight and turning. Corner lanes now arbitrate as their own chunk, as the original's corner chunks do, so a light or the junction slowdown of the tile they leave no longer applies to them (decision 106).

The replay never builds a crossing: none of its builds is refused on f22. The corner-chunk change still moves it slightly. On the 60 plausible phase sets, v21c scores 796.3 (669–829) with 18/60 reaching the end, against f22's 794.4 with 15/60 (paired +2.0 ± 2.0; [data](measurements/bench-f23-replay-v21c-p60.txt)).

### Gridlocks, roundabout activation and level crossings (f24, night of 11–12 November 2026)

f24 ports three more rules from the original's code (decisions 107–109):
- **Gridlocks:** blocking cycles are searched only from stuck vehicles (refused at their next junction, or overlapping their leader), and all-leader cycles push.
- **Roundabout activation:** a new roundabout stays planned until the lanes it replaces are clear. Meanwhile cars about to commit to those lanes wait, and new routes avoid the circle.
- **Level crossings:** cars slow towards, accelerate gently on, and do not enter a congested train crossing. A diagonal road between two diagonal rail tiles is a crossing too.

| Replay v21c, 60 plausible phase sets | Mean | Range | Reach the end |
|---|---|---|---|
| f23 | 796.3 | 669–829 | 18/60 |
| f23 + gridlock rule | 801.8 | 732–839 | 17/60 |
| f24 (+ roundabout activation, crossings) | 796.0 | 737–836 | 16/60 |
| Original (recording) | 835 | | ends at about 1314.6 s |

The gridlock rule adds 5.5 ± 3.5; roundabout activation costs 5.8 ± 2.6, all of it after the replay's roundabout at 1051 s. The crossing rules cannot affect this replay, which never builds over the rail line. [Data](measurements/bench-f24-replay-v21c-p60.txt).

### Replay v21d: event times from the game's own clock (12 November 2026)

The clock dial in the top-right corner shows the game time in every frame. The hand turns once per 10 game seconds, the face is light from 6 am to 6 pm, and midnight is 12 o'clock on the dark face (decompiled `ClockView`). Reading it at 4 frames per second, anchored at each week's end (Monday 00:00 = 140k s), gives the game time for 2,245 frames of the recording. Every week's start and end agree exactly ([time series](measurements/dial-game-time.csv); tools in [source](source/read_dial.py)).

Against the dial, replay v21c is within about 1 s for most of the game ([comparison](measurements/replay-v21c-vs-dial.txt)). Through weeks 4 and 5 (video 241 to 365 s) it converted video time slightly too slowly: its events there are 2 to 5 s early, and the player's paused building happened at 678.8 s, not 677 s. The recording runs at exactly 2 game seconds per video second whenever the game runs, and fast-forward is never used. [replay-candidate-v21d.json](replay-candidate-v21d.json) takes every event's time from the dial. The real score curve is re-timed the same way ([score_timeline_dial.csv](measurements/score_timeline_dial.csv)). Refitting the 60 demand-phase sets to it improves every fit (error 3.58 to 3.7 trips, was 3.86 to 3.9; [fits](measurements/phase-fits-v21d-60.txt)). v21d on the refitted sets ([plausible-phases-v21d-60.txt](measurements/plausible-phases-v21d-60.txt)) is the benchmark from here on.

| Simulator f24, 60 phase sets | Mean | Median | Range | Reach the end | Mean end |
|---|---|---|---|---|---|
| v21c, v21b sets | 796.0 | 792 | 737 to 836 | 16/60 | 1297 s |
| v21d, v21b sets | 805.1 | 808 | 747 to 835 | 22/60 | 1302 s |
| **v21d, refitted sets (benchmark)** | **805.5** | **811.5** | **759 to 833** | **22/60** | **1302 s** |
| Original (recording) | 835 | | | | ~1314.6 s |

[Data](measurements/bench-f24-replay-v21d.txt). Where the rest goes: with the best refitted set, our score trails the real curve by about 6 trips at 260 s, by 10 to 13 from 500 to 1100 s, and by 23 to 37 after 1188 s. Our cars wait at junctions for only about 3% of their outbound time. The fitted demand lag (about 6 s from a pin to its delivery) is shorter than our trips, so the real game most likely created pins earlier or more often than the replay can tell us (see "Remaining replay gap").

### f25: re-plan on, original exit space, registration stamps (12 November 2026)

| Replay v21d, 60 refitted phase sets | Mean | Range | Reach the end | Paired vs f24 |
|---|---|---|---|---|
| f24 | 805.5 | 759 to 833 | 22/60 | |
| f24 + original re-plan | 803.7 | 745 to 833 | 23/60 | -1.9 +/- 3.2 |
| f24 + original exit-space formula | 789.0 | 693 to 828 | 14/60 | -16.6 +/- 3.2 |
| **f25** (both + registration stamps) | **783.4** | **684 to 832** | **8/60** | **-22.1 +/- 4.0** |

([Data](measurements/bench-f25-replay-v21d.txt).) The re-plan rule no longer costs anything on the re-timed replay, so it is on (decision 111). The exit-space test now follows `DoesVehicleHaveSpace` exactly (decision 112): a car may enter beside a same-exit car only if more than two vehicle lengths are free beyond the junction. Ours had credited the leader's progress through the junction. This rule only acts when traffic queues beyond a junction: f25 is within one trip of f24 up to 1000 s and five trips behind by 1200 s. It moves the replay away from the real game's 835, but it is the original's code. With it, the late-game congestion that ends the game comes earlier.

### f26: traffic-light details and weekly offers (12 November 2026)

The traffic lights and the weekly upgrade offers were checked against the decompiled code (decisions 114 and 115). For the lights, three details were ported: the candidate order, the mothballed-lane weight, and keeping the pair while cars are inbound. The offers now use the original's draw, whose second pick reads stale weights. Replay v21d: 773.5 (f25 783.4). The median run is unchanged, but one run tips into overcrowding at 1080 s ([data](measurements/bench-f26-replay-v21d.txt)).

## Experiments not adopted

- **Original re-plan on road changes, on f22 (11 November 2026).** On the 60 plausible phase sets ([phases](measurements/plausible-phases-v21b-60.txt)) replay v21c scores 786.2 (700–833), 8/60 reach the end, against f22's 794.4 (669–833), 15/60. Paired difference −8.1 ± 4.8 trips; 22/60 runs improve ([data](measurements/experiment-repath-on-f22-p60.txt)). On the 20-set benchmark it was −11.6. It runs at f22's speed once return paths are re-found lazily; refreshing every stored return path at every change doubled run time. It is the original's rule, but it moves the replay away from the real game, so it stays off.
  **Which part, and where (f23).** Split into parts on the 60 sets, each against f23 (796.3), and scored at fixed times as well as at the end ([data](measurements/experiment-repath-parts-on-f23-p60.txt)):

  | Against f23 | Trips by 900 s | 1000 s | 1100 s | 1200 s | Final score | Mean end |
  |---|---|---|---|---|---|---|
  | Full rule (current lane + 2 kept) | −0.1 ± 0.3 | −0.7 ± 0.4 | −0.2 ± 0.7 | −1.6 ± 0.9 | −11.2 ± 4.4 (41/60 worse) | 1290 s (f23 1297 s) |
  | Re-plan keeping the current lane only | +0.1 ± 0.3 | +0.2 ± 0.4 | +0.8 ± 0.7 | −0.4 ± 0.8 | −0.4 ± 4.0 | 1299 s |

  The whole loss comes from the two extra committed lanes, and it is not slower traffic: by 1200 s the full rule has delivered about 1.5 trips fewer. The final score falls because the game ends about 7 s earlier, when a crowded lot overflows slightly sooner. At the end the score moves about 1.6 trips per game second, so small differences there decide the result. The port matches the original. In the original, `path[0]` is the next lane and the car re-plans from `path[1]`, the current lane plus two; our extension to the end of a tile only keeps corner and motorway lanes, which lead one way anyway. So the effect looks real but small, and it is sensitive to the replay's timing near the end. It stays off.

- **Original tick length again, on f27 (12 November 2026).** The original steps at exactly 0.1 s (`Simulation.DefaultTimestep`). Some rules act once per step, such as dispatch quotas and junction decisions, so at 0.05 s ours dispatches up to twice as often per second. On replay v21d with the refitted sets, f27 at 0.1 s scores 766.6 (669 to 823) against 771.9 at 0.05 s: paired -5.3 +/- 7.2, no measurable difference ([data](measurements/experiment-tick-0.1-on-f27.txt)). The step stays at 0.05 s because the headless host's `step` command counts ticks: a change would silently double the game time of every agent step in existing training code. A switch would need the host and the training code changed together.
- **Original tick length (0.1 s instead of 0.05 s), on f7:** 16-phase mean 777.8 → 762.5 (597–813), 5/16 reach the end; fitted 799 → 789 ([data](measurements/experiment-tick-0.1-on-f7.txt)). The original steps at 0.1 s, but our arbitration, dispatch quotas and tests were built around 0.05 s and the coarser step made results worse and noisier, so the step stays at 0.05 s.

- **Automatic removal of a traffic light whose tile drops below three roads, on f7:** mean 777.8 → 745.4 ([data](measurements/experiment-light-cleanup-on-f7.txt)); the motorway penalty alone was neutral (777.1, [data](measurements/experiment-motorway-penalty-only-on-f7.txt)). The original counts pending roads toward the three and the replay erases and redraws at that light, so our version removed a light the real game kept (no rebuild appears in the video). Not adopted until pending roads are modelled.

- **Light removal at release of an erased link, on f20 (11 November 2026).** The exact original rule: `ReleaseMothballedLanesProcess` checks the light on both tiles of a connection when it is released (erased and no longer used by any car, return paths included). `TileSupportsTrafficLight` counts live roads, and live includes erased links still in use, so a light goes only when its tile has fewer than three roads at release; the light is returned to stock. Our retirement already has the same lifecycle, so the port is two lines. Replay v21 mean 791.1 → 788.2 (fitted 791 failing → 800 reaching the end); v21b on the plausible phases 791.5 → 784.8 ([data](measurements/experiment-light-release-on-f20.txt)). In every run it removes light 20,13 at about 979 s: the player erased its south link at 970.15 s (the west one at 832.95 s) and redrew both at 984.05 s, and our cars had left the south link 9 s after the erase. The recording contradicts that: at game time about 1294 s the toolbar shows 2 lights in stock, which is exactly the 4 received (280 s and 1120 s offers) minus the 2 placed, and the frame shows the light at 20,13 with all four roads. So the real game kept the light, unless it was removed and placed again, which would need a light placement that the reviewed replay does not contain. Under the original's rules that means the south link was still in use when it was redrawn 14 s later, even though 20,14 had a 27-tile detour. Not adopted, because it makes the replay contradict the video; the mismatch points to a difference in how long cars keep an erased link (open item 3, re-routing).

## Other checks on f7 and f8

`scripts/verify_five_maps.py` (10 runs) and `scripts/check_training_readiness.py` (60 episodes, exact replays on all five maps) pass on f7 and on f8; their reports are regenerated in `simulation/Reports/`.


## Continued on `fidelity-aya-growth` (merged as f12)

Original free-play city growth (building placement by the original's weight layers and building influence, house driveways, playable edges, spawn schedule, supply anchor; branch simulator `2026-11-11.g1`, merged into `fidelity-aya` as `2026-11-10.f12`) is recorded in [fidelity-aya-growth-2026-11-11](../fidelity-aya-growth-2026-11-11/README.md). Replays force building spawns, so replay v21 results are not affected by it.

## Open items (state at f26)

Known differences from the original that are not yet modelled, roughly by expected effect:

1. **Replay demand input.** The real game had roughly 10% more demand by ~1260 s than replay v21 gives us (see above). v21b covers the three provably late destinations, using lower-bound delays. Circles that failed for a while and then succeeded (navy at 1030 s, yellow at 1106 s) and any pending cyan entry of plan days 40–76 cannot be timed from the video and are not represented.
2. **Crossing diagonals.** Modelled from f23 (see above). Not modelled: a crossing next to a roundabout, and a turn at a corner when the two tiles are also linked directly (the direct link is used).
3. **Re-routing details.** The original's re-plan (current lane and the next two kept) is on from f25 (decision 111). The comparison below, made on replay v21c, is kept for the record.
4. **Roundabout activation.** Modelled from f24 (decision 108). Earlier note: the original keeps a new roundabout planned until conflicting lanes clear and holds affected cars (hot-swapping lanes); ours switched at once. Sized on the replay (best-fit phases): after the roundabout at 19,9 is built at 1051 s, 16 cars still have old footprint lanes ahead and the last clears at 1058 s, so the difference is a one-time window of about 7 s at one junction. Deferred: the port (`ReleaseMothballedLanesProcess` hot-swap rules, `IsAboutToHotswap` stops) is large for that effect.
5. **Traffic-light removal.** The original removes a light, and returns it to stock, when an erased link is released and leaves the tile with fewer than three roads. Erased links still in use count as roads. Ported and measured but not adopted: in the replay it removes a light that the real game kept (see experiments).
6. **Smaller items.** All-leader pushing cycles are modelled from f24 (decision 107); the drag-time preference for a new motorway's anchor ramp, which depends on the mouse drag (edits are modelled); drawing by greedy eight-direction stepping instead of a raster line. Junctions on water (f21) and motorway ramp sides (f22) are now modelled.
