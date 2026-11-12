# Second recorded LA game (score 601): reconstruction, 12 November 2026

## Current result (draft 4)

[replay-g2-draft4c-unlimited.json](replay-g2-draft4c-unlimited.json), 60 demand-phase sets fitted to this game's score curve:

| simulator | mean score | median | mean end (game s) | runs reaching 1162 s | score at 900 s | at 1000 s | at 1100 s |
|---|---|---|---|---|---|---|---|
| f24 | 558.0 | 579 | 1093 | 14 | 366 | 454 | 556 |
| f31 | **608.3** | 621.5 | **1149** | **42** | 367 | 454 | 557 |
| f33, earlier exit-space formula | 606.2 | 615 | 1144 | 29 | 367 | 455 | 559 |
| f34 | 591.5 | 589 | 1135 | 16 | 366 | 453 | 553 |
| real game | 601 | | about 1162 | | 373 | 459 | about 549 |

All builds are within about 2% of the real score at every checkpoint. f31 matches best: its mean score is within 7 of the real game's, and 42 of its 60 runs reach the real end time. The order f31 ahead of f34, with the earlier exit-space formula close to f31, matches the first recording.

**Which step from f31 to f34 costs the points** (draft 4, the same 60 phase sets, paired against the previous step):

| step | mean score | runs reaching 1162 s | paired change |
|---|---|---|---|
| f31 | 608.3 | 42 | |
| + 122, exit-space target case (f32a) | 617.0 | 50 | +8.7 +/- 4.7 |
| + 123, target braking (f32b) | 585.0 | 22 | **-32.0 +/- 6.1** |
| + 124 and 125, crossing skip and one-way bays (f32c) | 585.2 | 15 | +0.2 +/- 5.6 |
| + 126, lookahead order (f32d) | 583.5 | 13 | -1.7 +/- 4.9 |
| + 127, eviction (f32e) | 578.0 | 10 | -5.5 +/- 4.7 |
| + 128, inbound order (f32f) | 592.9 | 16 | +14.9 +/- 5.0 |
| + 129, re-plan keeps shove (f32g); f33; f34 | 592.9, 592.9, 591.5 | 16 | 0, 0, -1.4 |

The loss comes almost entirely from target braking (decision 123), as on the first recording (-28.1 there). Short trips are not slower with it: (24,19) or (25,19) to the lot at 27,18 takes 7 to 9 s in f34, against 7 s for a car tracked in the video. The cost therefore sits in busy lots late in the game, where arriving cars creep towards their bay. Re-reading the original confirms how the target is chosen: the outbound path ends at the lot's entrance lane, with the target at that lane's length (`DispatchVehiclesProcess`, `VehiclePathfindingProcess`); the bay middle is set once the lot assigns a bay. The open question is how a creeping car affects the cars behind it inside a busy lot.

**Direct check of target braking.**
- **The acceleration function.** The game's native acceleration function (`CalculateAcceleration` in the installed 32-bit `dpcPlatform.dll`) was called from a 32-bit Python ([native_idm.py](source/native_idm.py); the DLL and the Python stay local). On 30 car-approaching-target cases with the game's constants (maximum acceleration 0.54, maximum deceleration 12, exponents 4 and 6, in world units), its values agree exactly with the decompiled reference formula that our movement code ports. The formula and constants are therefore confirmed.
- **The real car.** The first car to arrive at the yellow lot in the video (video 15.5 to 21.1 s) was tracked at 30 fps at 89 px per tile. It keeps about 1.16 tiles/s down to roughly 0.75 tile from where it comes to rest, drops to about 0.25 at 0.5 tile, then creeps the last 0.5 tile for about 2 s. Its last tile takes 2.5 s.
- **The simulator on the same lot** (first arrival, game 55 to 62 s):
  - f34 brakes from about 1 tile out (0.94 at 0.78, 0.72 at 0.45) and creeps for about 2 s; its last tile takes 3.1 s;
  - f31 keeps 1.1 tiles/s to the bay and stops at once; its last tile takes 1.0 s.
- **Reading.** The original does brake towards the target, as decision 123 ports. f34 brakes a little earlier and softer than the real car, which costs about 0.6 s per arrival. Over a game, f34 adds about 0.7 s inside lots and 0.5 to 1 s per trip, about 3% (10 phase sets, game 600 to 1100 s), and that is the source of its 17-point paired gap to f31.
- **Weighing the evidence.** Against the real totals (601 points, game over at 1162 s), f31 (608) and f34 (592) are both within about 1.5%, and the replay's remaining uncertainty (20% extra road tiles, fitted demand) is of that size. The arrival profile supports keeping target braking. The small residual difference, where the real car brakes later and harder, is open: candidates are the bay geometry, which places the target, and the 0.05 s step.
- **Separate finding.** The replay's first delivery is about 40 s late (simulator 60.6 s, video about 20 s). The earliest road links are confirmed only after the first unusable frames and a 6 s hold, so this is a replay timing limit, not a simulator rule.

On 12 November, at the user's request, f31 (fidelity-aya 4f3bb7c) was merged into upstream main as b018019.

**Correction to draft 3 (below).** Draft 3's conclusion, that every build ends 80 to 125 s too early because lots overflow too soon, was mostly an artefact of the reconstruction. The erase pass ([post_erase.py](source/post_erase.py)) also removed links added on purpose (manual and connectivity repairs) whenever their exact pixels looked like land. One such link was 32,11 to 31,12, which joins the shared lot's east access to the row-12 road. Without it, magenta cars from the far-east houses drove through the shared lot and crossed the river twice to reach 27,18: 35 tiles instead of 28. Real tracked trips were much shorter. For example, (24,19) to (27,18) took 7 s in the video against 13.5 s in the simulator, through a wrong driveway, now also fixed. Draft 4 keeps deliberate links out of the erase pass and builds route-length checks into the harness (`ROUTEALL`, `ROUTEPAIR`, `TRIPS`, `DUMPEVERY`, `REGION` in `tmp/harness/Trace.cs`). Its network still has about 25 to 35 more road tiles than the stock series implies (about 20%), so the replay still runs with unlimited stock.


Source: `la-game2-score-601.mp4` (1596x928, 30 fps, 1197.7 s; stays local in `tmp/video/`). Recorded by the user. Final score 601, game over at about game second 1162.

## What was extracted

- **Game time** from the HUD clock dial: the game ran at 1x in every week; each weekly screen appeared at game time 140k, up to 4.6 s late. The dial centre was refitted for this video (residual 0.24 s). Script: [week_dial.py](source/week_dial.py).
- **Score curve** every 10 video seconds ([score_timeline_g2.csv](measurements/score_timeline_g2.csv)). Up to game second 800 it is close to the first game: 284 against 289 at about 780 s.
- **Road stock** every 5 video seconds ([stock_g2.csv](measurements/stock_g2.csv)).
- **Weekly offers and choices** (week 1 to 8): roundabout, 30 roads, bridge, bridge, bridge, 30 roads, bridge, motorway. The choices were inferred from the counts that changed after each screen.
- **Camera**: every video second was registered to the simulator's LA terrain. An FFT correlation of water masks gives a scale about 0.79 of the zoom curve (`ZoomCurve`) and the offset. Each frame was warped to a 50x30 map board at 32 px per tile. 92 frames that register badly (overlays, upgrade screens) are excluded ([bad_frames.json](measurements/bad_frames.json)).
- **Buildings**: 39 houses, all of them checked against the late frames ([houses_raw.json](measurements/houses_raw.json)). There are 9 destination lots, including a 4x3 shared lot. Their entrances were read from zoomed strips. Five round conversions were timed to within about 8 s.
- **Roads**: link-by-link detection on the boards:
  - a white or road-outline test, with the score taken as the weakest of five pieces along the link;
  - erasure only on evidence of land;
  - a dead-end repair;
  - a connectivity repair from weak evidence;
  - manual additions where lot shadows hide roads ([manual.json](measurements/manual.json)).
  The result is in [roads_fixed.json](measurements/roads_fixed.json).

## Draft replay and first comparison

[replay-g2-draft1.json](replay-g2-draft1.json) uses the real starting stock. The variant [replay-g2-draft1c-unlimited.json](replay-g2-draft1c-unlimited.json) has 500 roads and 20 bridges at the start and lets rejected road events pass. It is a draft, **not a validated replay**:
- Road detection still over- and under-counts in places, so the real stock rejects some events.
- The demand phases are the 60 sets fitted to the first game.
- Planned destinations that appeared late, which add demand to their colour, are not modelled yet.

On the unlimited draft, with the first game's 60 phase sets:

| simulator | mean score | median | mean end (game s) | score at 900 s | score at 1000 s |
|---|---|---|---|---|---|
| f24 | 313.1 | 307 | 873 | 335 (9/60 runs reach it) | - |
| f31 | 435.3 | 455 | 1022 | 333 (49/60) | 416 (48/60) |
| f34 | 397.1 | 421 | 980 | 331 (42/60) | 414 (32/60) |
| real game | 601 | | about 1162 | 373 | 459 |

f31 and f34 deliver at the same rate up to 1000 s, about 10% below the real game. As on the first game, they differ in when the game ends: f34 ends earlier. The failing lot is the magenta lot at 27,18, as in the real game.

## Draft 3: plan delays, fitted demand, strict roads (same day, later)

- **Colours from the city plan.** The LA plan's items fix the colour indices: this game's charcoal plays the cyan role (index 2) and its blue the navy role (index 3). The late chunk's three round conversions (yellow, cyan, navy) match this game's conversions at game 821, 906 and 1030 s only this way, and the shared lot is the cyan item that may become a double lot.
- **Late planned destinations.** Three lots appear after their plan slot. The replay marks them with `scheduledAt`, so the simulator's delayed-demand rule adds demand to their colour while they wait:
  - yellow 15,12: chunk days 7 to 9, scheduled at about 160 s, appears at 288 s;
  - blue 11,12: slot 0 of days 8 to 22, scheduled by 265 s (230 used), appears at 298 s;
  - charcoal shared 28,9: slot 0 of days 16 to 36, scheduled between 377 and 437 s (407 used), appears at 484 s.
- **Demand phases fitted to this game.** The analytic pin model with delayed demand fits the real curve to 1000 s with an rmse of 2.5 trips and a delivery lag of 15 s. The 60 best of 90 random starts are in [plausible-phases-g2b-60.txt](measurements/plausible-phases-g2b-60.txt).
- **Driveways reviewed.** All 39 houses were checked on crops; 8 driveways were corrected and 2 timed rotations added ([manual.json](measurements/manual.json)).
- **Roads from strict detection plus repairs.** The base is the strict link test with weakest-segment scores, crossing diagonals resolved, and staircases next to strong diagonals dropped. On top of it:
  - a dead-end repair;
  - a connectivity repair (every house must reach a lot of its colour, using links with weak video evidence);
  - four links hidden under lot shadows, added by hand;
  - an erase pass for any link that turns to land colour for 15 visible seconds.
  The network ends with about 155 land road tiles against the 134 the stock series implies, roughly 15% too many. A false burst of 18 links after the week 4 screen (frames 425 to 431) is excluded.
- At 900 s every house reaches a lot of its colour.

**Result**, [replay-g2-draft3c-unlimited.json](replay-g2-draft3c-unlimited.json) on the 60 fitted phase sets:

| simulator | mean score | median | mean end (game s) | runs reaching 1162 s | score at 900 s | at 1000 s | at 1100 s |
|---|---|---|---|---|---|---|---|
| f24 | 479.2 | 513 | 1037 | 0 | 362 | 445 | 541 |
| f31 | 509.1 | 514 | 1075 | 0 | 361 | 443 | 543 |
| f33, earlier exit-space formula | 519.9 | 530 | 1082 | 2 | 362 | 445 | 544 |
| f34 | 478.1 | 487.5 | 1050 | 0 | 358 | 441 | 538 |
| real game | 601 | | 1162 | | 373 | 459 | about 549 |

All four deliver within 2 to 4% of the real game up to 1100 s. They differ mainly in when the game ends, and every one ends 80 to 125 s too early on the same lot as the real game (magenta 27,18). The order matches the first recording: the earlier exit-space formula, then f31, then f34. Both recordings therefore point to the same gap: lots overflow earlier than in the original while deliveries keep pace. That suggests looking at the late game (failure timing, late demand, service of the failing lot) rather than general traffic flow.

## Late game: where the early game over comes from (f34, best phase set)

**Real pins waiting per lot**, read from the boards every 20 video seconds. The magenta lot at 27,18 shows 1 to 4 pins between game 957 and 1015 s, 8 at 1075 s, and starts its timer at about 1095 s, failing at about 1162 s. The other magenta lots and both yellow lots start their timers only in the last 60 s.

**Simulator.** The magenta lot at 27,18 holds 8 to 10 pins from 940 s, starts its timer at about 997 s and fails at about 1050 s. The other magenta lots also fill up early: 10,9 holds 8 pins with its timer running at 1020 s, where the video shows 1 to 4. The yellow lots stay close to the video.

**Totals agree, delivery lags.** At about game 980 s, the simulator has created about 482 pins (delivered 441 plus waiting 41), and the real game about 483 (delivered about 459 plus about 24 waiting on lots). Demand totals therefore match. The simulator delivers about 4% less, and the backlog sits mostly on magenta: 18 pins waiting against about 5 in the video.

**Magenta cars.** At 940 to 1000 s the simulator has 20 to 22 of its 24 magenta cars on the move and none idle at home. The video shows 13 to 16 magenta cars on roads and lots, with several magenta houses holding a car at home. The simulator's magenta trips take 42 s out and 42 s back on average (850 to 1050 s, [g2-trips.txt](measurements/g2-trips.txt)).

**Where simulator cars wait** (whole game, wait-location log):
- braking towards the target at lot entrances ("Destination ahead", the target-braking rule of decision 123);
- exit-space queues at the river bridge at 22,14 and the junctions east of it, 23 to 25 by 13 to 17.

**Bridge area.** Cars in tiles 20 to 25 by 12 to 17, around the main bridge and the junctions east of it:
- in the video, counted by eye at video 900 to 1040 s: about 10 to 20, with real queues there too (a line of yellow cars at 980 s);
- in the simulator at game 880 to 1040 s: 10 to 19, of which 2 to 11 are stopped.

Congestion there is comparable, so it does not explain the gap. The player also built a curved second bridge just south of row 14 at about video 1000 s.

**Limit.** The total score curve does not separate colours, so the per-colour timing of demand is not identified by the phase fit. Most good fits give magenta a burst in this period. In one basin of nearly equal fit, the magenta phase is about 10 and the blue lot fails first instead ([18 representative sets](measurements/phases-g2-div.txt)). With f34, the first lot to fail is magenta in 15 of the 18 sets and blue in the other 3. So the magenta under-service is likely, but partly a consequence of the fitted demand timing.

## Open (after draft 3)

1. The road network has about 15% more tiles than the real one, and the replay still runs with unlimited stock.
2. Items scheduled near the end (chunk days 40 to 76) that never appeared may have added demand in the last 100 s; this is not modelled.
3. The motorway built at about video 1175 s, right before game over, is not in the replay.

## Open (draft 1)

1. Map each lot to its slot in the LA plan and add `scheduledAt` for late items. The analytic pin model under-predicts the middle of the game (37 against 51 at 304 s), which points to pending planned destinations adding demand.
2. Fit demand phases to this game's curve once (1) is in.
3. Check the road events against the stock series and the 1x frames, and remove the unlimited-stock crutch.
