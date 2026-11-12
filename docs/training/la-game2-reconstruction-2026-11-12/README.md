# Second recorded LA game (score 601): draft reconstruction, 12 November 2026

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

## Open (after draft 3)

1. The road network has about 15% more tiles than the real one, and the replay still runs with unlimited stock.
2. Items scheduled near the end (chunk days 40 to 76) that never appeared may have added demand in the last 100 s; this is not modelled.
3. The motorway built at about video 1175 s, right before game over, is not in the replay.

## Open (draft 1)

1. Map each lot to its slot in the LA plan and add `scheduledAt` for late items. The analytic pin model under-predicts the middle of the game (37 against 51 at 304 s), which points to pending planned destinations adding demand.
2. Fit demand phases to this game's curve once (1) is in.
3. Check the road events against the stock series and the 1x frames, and remove the unlimited-stock crutch.
