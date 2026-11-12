# Simulator fidelity against the original (branch `fidelity-aya`) — 10 November 2026

Aya's parallel attempt, alongside Mohammad's work on `mohammad`, to make the simulator behave as close
as possible to the original game. The two versions will be compared and the better one kept.

**User decisions (10 November 2026).** Work on a separate branch, pushed to origin. "Better" means both:
rules that match the original's code, and the recorded 835-point Los Angeles game (replay v21) landing
close to 835 at about 1314.6 s. Reading the decompiled original locally and running its components as an
oracle are allowed; decompiled code and assemblies stay outside Git (decision 077).

## Current state (12 November 2026, simulator `2026-11-10.f33`)

- **Benchmark:** replay v21d (event times read from the game's clock dial) on 60 demand-phase sets refitted to the real score curve, re-read at exact frame times (decision 118).
- **Scores:**
  - f24: 805.5, 22/60 runs reach the end.
  - f25, after the original's junction exit-space formula: 783.4.
  - f26: 773.5; the median run is unchanged, and one run collapses.
  - f27 (review fixes, decision 116): 771.9.
  - f28 (carpark connection nodes, decision 117): 780.1, 12/60 reach the end; 778.3 on the corrected-curve phase sets (decision 118).
  - f29 (lane-length route costs, decision 119): **792.5**, 17/60 reach the end.
  - f30 (in-lot leg when choosing an exit, decision 120): 792.3.
  - f31 (motorway costs, decision 121): **795.4** (median 804), 18/60 reach the end.
  - f32 (seven rules from an audit of the decompiled movement, junction and parking code, decisions 122 to 129): **754.1** (median 760), 0/60 reach the end. Fixed-time scores are as close to the real curve as before: 365.4 at 900 s (real 364), 449.2 at 1000 s (454), 553.5 at 1100 s (551), 666.1 at 1200 s (663). The loss is in when the game ends, see "f32" below.
  - f33 (two audit details, decision 130): identical to f32 on the replay.
  - The original scored 835 and ended at about 1314.6 s.
- **Where it differs:** up to about 360 s our score is within 3 trips of the real curve, and from 430 to 1000 s 5 to 17 trips behind. The gap opens in the late game, when the far red lot overflows earlier than in the original.
- **Rules ported overnight from the decompiled code:**
  - crossing diagonals (f23);
  - gridlock cycles, roundabout activation and level crossings (f24);
  - re-plan, exit space and registration stamps (f25);
  - traffic-light details and the weekly offer draw (f26).
- **Kept although it lowers the replay:** the exit-space formula (decision 112, -16.6), cars braking towards their target (decision 123, -28.1) and the original's lookahead order (decision 126, -13.6). All are the original's code; see "f25" and "f32" below.

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

### Free-play soak test on all five maps: f22 against f27 (12 November 2026)

Tonight's ported rules lower the replay score, so they were also checked away from it. On each map, with two seeds, the reference road builder ran for 1500 game seconds. It rebuilt every 10 s with stock topped up and the failure timer extended. f27 delivered 10,561 trips against f22's 9,486 (+11%). The longest car wait fell from 352 s to 45 s; f22 had a lasting gridlock on Beijing seed 41. In 8 of 10 runs f27 had no car stuck for more than 30 s ([data](measurements/soak-f22-f24-f27.txt)). The same test on f24 gives 10,362 trips, so the f25 to f27 changes, including the exit-space formula, also add about 2% in free play. So the original's gridlock-breaking and junction rules make the network flow better in free play, while the replay's late game ends earlier. The replay difference therefore comes from how its particular late-game layout loads the network, not from extra gridlock.

### The real score curve re-read (12 November 2026)

The original real score curve (10 November) was read from frames that turn out to be about 5 video seconds late. Re-read at exact frame times, the HUD shows for example 53 at video 180 s (old curve 55), 277 at 450 s (285) and 691 at 850 s (705) ([new curve on the dial clock](measurements/score_timeline_dial.csv)). Refitted to it, the 60 demand-phase sets fit much better: error 2.27 to 2.3 trips instead of 3.58. The fitted delivery lag becomes a physical 11 to 12 s ([fits](measurements/phase-fits-v21e-60.txt)). The benchmark is now v21d on these sets ([plausible-phases-v21e-60.txt](measurements/plausible-phases-v21e-60.txt)).

f28 on them: 778.3 (705 to 827), 6/60 reach the end ([data](measurements/bench-f28-replay-v21d-p21e.txt)). With the best set, our curve is within 3 trips of the real one up to about 360 s and 5 to 17 trips behind from 430 to 1000 s. The real first delivery (car leaving at about video 18 s, parked by video 24 s) agrees with ours (game 15.5 s). Much of the mid-game "deficit" reported earlier came from the shifted real curve.

### f29: route costs use lane lengths (12 November 2026)

The original charges a lane its length over its speed limit. Ours charged each step a whole tile, so a right turn (lane 0.64 tiles) cost as much as a left turn (0.95) and more than the original's. With lane lengths in the costs, replay v21d on the current phase sets scores 792.5 against 778.3 (paired +14.2 +/- 4.0, 42/60 better; [data](measurements/bench-f29-replay-v21d-p21e.txt); decision 119).

### f32: audit of the decompiled movement, junction and parking code (12 November 2026)

Three independent read-only audits compared the decompiled original with our code: movement, junction entry, parking and dispatch. Each difference was checked on both sides before it was ported. Demand, dispatch, the parking timer, the failure timer and the junction check order were confirmed as already faithful. Ported (decisions 122 to 129):

- **Target braking (123).** In the original, a car brakes towards the end of its path as if a stopped car stood there: the lot's entrance lane, then the middle of its bay, or its driveway. Ours had no such obstacle, so cars arrived at lane speed.
- **Exit space (122).** The exit-space test measures the target case from the car's current lane.
- **Lookahead order (126).** The next lane is always tested. Later lanes are tested only until a leader, the target or a refusal is found, and a refusal behind a leader does not brake. The junction slowdowns combine with a blocked junction, and the signal doubling applies with either sign.
- **Level crossings (124).** The crossing checks are skipped while the car's own crossing is closed; the condition was inverted.
- **One-way bay lanes (125).** A car leaving by the other entrance laps the aisle with a U-turn instead of reversing across its bay.
- **Eviction (127).** A full lot sends home one car per step, and a car still rolling into its bay counts.
- **Inbound order (128).** Ineligible inbound cars keep their registration order, so an uncommitted car also yields to an earlier uncommitted one.
- **Re-plans (129).** A re-plan keeps shoving and pushing.

**Measured:**

| step | replay mean | paired vs previous | data |
|---|---|---|---|
| f31 | 795.4 | | [f31](measurements/bench-f31-replay-v21d-p21e.txt) |
| + 122 | 789.2 | -6.2 +/- 4.1 | [f32a](measurements/bench-f32a-replay-v21d-p21e.txt) |
| + 123 | 761.0 | -28.1 +/- 5.4 | [f32b](measurements/bench-f32b-replay-v21d-p21e.txt) |
| + 124, 125 | 765.0 | +4.0 +/- 5.0 | [f32c](measurements/bench-f32c-replay-v21d-p21e.txt) |
| + 126 | 751.4 | -13.6 +/- 7.0 | [f32d](measurements/bench-f32d-replay-v21d-p21e.txt) |
| + 127 | 758.3 | +6.9 +/- 6.3 | [f32e](measurements/bench-f32e-replay-v21d-p21e.txt) |
| + 128 | 758.1 | -0.3 +/- 6.3 | [f32f](measurements/bench-f32f-replay-v21d-p21e.txt) |
| + 129 (f32) | 754.1 | -4.0 +/- 4.6 | [f32](measurements/bench-f32-replay-v21d-p21e.txt) |

**Where the loss comes from.** Up to 1200 s the score barely moves: f32 is within 5 trips of the real curve at 900, 1000, 1100 and 1200 s, as f31 was, and closer at 1100 and 1200 s. The loss comes from an earlier game over. Our runs end on average at 1273 s instead of 1314.6 s: slower lot intake lets the red lots overflow sooner. They are the same lots that were overcrowding in the real game at 1260 s (red 30,18 fails in both). In two phase sets with high red demand, the late red lot at 11,18 fails before 1100 s because the few red houses cannot supply four red lots; no cars are stuck. The demand-phase sets were selected under earlier versions, so the end-of-game score partly measures the replay's demand input as well as the rules (see "Why the demand phases matter").

**Free play.** The five-map soak (two seeds each, 1500 s, no game over) has no gridlock in f32: at most 4 cars waiting over 30 s, longest wait 45 s. Throughput is not lower: 10,260 trips in the ten runs, against 10,163 for f32a and 10,070 for f29. So target braking slows lot intake mainly where lots are short of cars, as on the replay's late red lots ([data](measurements/soak-f29-f32.txt)). The London jam seen on f29 does not recur. On f31 it is gone with either exit-space formula; with the earlier formula Tokyo carries more traffic late in the game ([data](measurements/soak-LT-f31-vs-old-exit-space.txt)).



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

## Open items (state at f33)

Differences from the original that remain, roughly by expected effect:

1. **Replay demand input.** The real game created more demand by the late game than the replay can give us. Circles that failed for a while and then succeeded (navy at 1031 s, yellow at 1106 s) and destinations whose first placement failed briefly cannot be timed from the video. Through about 1000 s our score and waiting pins are close to the real ones (score 272 against 277 at 760 s; pins 12 against about 15).
2. **Carpark lane geometry.** Conflicts now follow the original connections (f28). The bay lanes run from the bay's side to its middle rather than straight across, which gives the same distances.
3. **Simulation step.** The original steps at 0.1 s and ours at 0.05 s. Measured without a replay difference; kept because the host's `step` command counts ticks (see experiments).
4. **Traffic-light removal.** The original removes a light when an erased link is released and leaves fewer than three roads. Ported and measured but not adopted, because the replay then removes a light that the real game kept (see experiments).
5. **Smaller items.**
   - Crossing diagonals next to a roundabout.
   - A corner turn where the two tiles are also linked directly (the direct link is used).
   - The hot-swap obstacle in the traffic-light blocked-car tests.
   - The traversing-collision part of inbound eligibility when ordering light candidates.
   - The drag-time preference for a new motorway's anchor ramp.
   - Strokes drawn by greedy eight-direction stepping.

Small differences found by the f32 audits and not yet ported (each judged low effect):
- Lanes leaving a driveway have no leader in the original.
- A car in a roundabout hot-swap counts as stopped for the cross-in-front relaxation.
- A re-plan re-stamps every later registration.
- The small-intersection lane count includes mothballed lanes.
- Dispatch does not require a return route.
- Bays are assigned after all movement in the step.
- The car leaving a house is the first to have arrived there.

Modelled since f22: crossing diagonals (f23); gridlock cycles from stuck vehicles with pushing, roundabout activation, and car rules at train crossings (f24); the original re-plan, junction exit space and registration stamps (f25); traffic-light details and the weekly offer draw (f26); fixes from an independent review (f27).
