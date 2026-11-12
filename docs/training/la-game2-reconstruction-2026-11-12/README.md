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

## Open

1. Map each lot to its slot in the LA plan and add `scheduledAt` for late items. The analytic pin model under-predicts the middle of the game (37 against 51 at 304 s), which points to pending planned destinations adding demand.
2. Fit demand phases to this game's curve once (1) is in.
3. Check the road events against the stock series and the 1x frames, and remove the unlimited-stock crutch.
