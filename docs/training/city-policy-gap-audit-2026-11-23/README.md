# City policy gaps and next training targets

On 23 November 2026 the user asked for a broad diagnosis of the policy on `Maskable-PPO`. This assessment uses `6bd7f71` plus the existing local implementation. The checks replayed frozen checkpoints, used native scoring and preserved the eight-hour run. The repaired checkpoint, narrow warm start, four-hour save and eight-hour save appear in that order in the measurement files. The original reserved benchmark remains available. [Previous capability tests](../city-service-capability-2026-11-23/README.md).

## Confirmed implementation problems

- **Some existing links disappear from the service features on longer roads.** The service feature expands matching-home and shop reach only ten times. On a visible chain of 16 existing edges the code reached 11 of 17 cells, including the starting cell. A complete traversal reached all 17. Compute full components of the currently visible, built road network. This can remain a description of existing roads.
- **Competing destinations of the same color can hide one another.** The features pool approaches by color and score road progress against the minimum gap for that color. On a constructed board the same edge gave zero progress toward a farther destination with a nearer same-color destination present and full progress when only the nearer destination's color changed. Keep destination-specific progress and demand available before combining action scores.
- **A bare approach can count as a working connection.** The road-component feature seeds reach at neighboring approach tiles. A matching home and shop pointed at the same empty tile on a constructed board, causing the model feature to signal an established network without any links. Test entrance attachment and connected service on the built road graph. The test confirms an observation-derived feature defect. The size of its effect on real city scores is open.

These changes alone would leave the previous real-city miss unsolved. At second 277 of seed `99387707`, the current feature already flagged all three verified one-road joins as progress. The complete-graph diagnostic produced the same flags and probabilities there. Of 343 legal roads, the best good join ranked second, yet all three good choices had 0.068% probability combined while a different road had 42.76% and Wait had 57.18%. The road ranking must learn to give a viable connection enough weight to beat competing builds. The audited stock threshold correctly covers zero through eight units. [Feature checks](features.json), [probe source](probe_service_features.py) and [verified one-road replay](../city-service-capability-2026-11-23/README.md).

## Route completion in normal cities

The native branch checks replayed the 14 final-checkpoint misses where some road stock was present at arrival and at least 90 seconds were observed afterward. They tested a bounded short-route candidate on snapshots of the existing road network and built the proposed links only in an alternate replay. Two distinct missed destinations were served on this branch test.

| Los Angeles seed | Target | Branch time | Stock | Native route cost | First delivery after the edits |
| --- | ---: | ---: | ---: | ---: | ---: |
| 99140298 | 14 | 373 s | 17 | 3 paid units in 3 edits | 403 s |
| 99387707 | 7 | 191 s | 20 | 3 paid units in 4 edits | 218 s |

Target 7 is the same one that eventually became one road away at second 277. The agent missed its earlier affordable expansion and also missed the later simple join. The probe tested up to five route candidates per target, capped at three paid units and four edits. The other missed destinations could need longer or more complex routes, a later legal window or a different traffic response. Replaying a successful branch supplies feasibility evidence and changes neither the policy nor its reward. [Native branch measurements](multiedge.json) and [probe source](check_multiedge.py).

## Competing demand and congestion

The same frozen city actors played two demand assignments on six paired layouts and two traffic regimes on six paired junction layouts. The existing native traffic fixture host supplied the legal edits and the original visible observation schema supplied the input. The probe warmed the live junction for 36 seconds, then used one-second Wait, like the city action interface. These small samples test decisions in supplied layouts.

- **Urgency under a fixed budget is weak.** The repaired, warm and four-hour policies each served the highest-demand destination in 6/12 demand cases. The final served it in 5/12. When the high-demand side changed on the same geometry, the first road changed on zero of six pairs for the repaired, warm and four-hour policies and one of six for the final.
- **Choosing a bypass when traffic warrants it is still a gap for the unified policy.** All four chose a separate exit first on all six light and all six heavy layouts. The native feeder averaged 16.50 deliveries in light traffic compared with 13.17 for the separate exit. In heavy traffic the separate exit averaged 32.33 deliveries with 0.45 stopped cars, versus 30.50 deliveries and 4.26 stopped cars for the feeder. The same route choice across these regimes fails the adaptive test. Earlier specialist policies established this behavior in related fixtures, which depend on their own checkpoints. [Traffic replays](traffic.json), [probe source](probe_city_traffic.py) and [specialist results](../traffic-milestones-2026-11-21/README.md).

## Independent city check

The candidate was evaluated on 24 new paired Los Angeles seeds outside the readiness and original long-run review suites. All reviews used exact model and host hashes, and the 600-second cap still applies. Of 96 games, 78 ended normally and 18 reached the cap.

| Checkpoint | Mean deliveries | Cities that scored | New destinations served | Arrivals with empty stock | Paid units per game outside observed routes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Repaired reference | 61.88 | 18/24 | 52/80 | 40/80 | 34.83 |
| Narrow warm start | 73.75 | 19/24 | 64/84 | 25/84 | 34.04 |
| Four-hour candidate | 75.29 | 19/24 | 73/94 | 24/94 | 32.63 |
| Eight-hour final | 64.71 | 18/24 | 60/81 | 13/81 | 33.25 |

Four hours gained 1.54 mean deliveries against the warm start (95% paired interval −22.25 to +25.58), with 12 wins, three ties and nine losses. Eight hours lost 9.04 against the warm start (−32.38 to +14.96), with nine wins, four ties and 11 losses, while decreasing empty-stock arrivals. The four-hour checkpoint remains useful for comparison. This suite leaves improvement over the warm start uncertain. All four still have fully scoreless cities. The amount outside assigned routes is a proxy over the measured interval. It includes future-use roads and cannot prove that every unused edge was a bad choice. [Summary](city-summary.json), [paired intervals](city-vs-warm-start.json), [seed pairs](city-suite.json) and [game rows](city-games.jsonl).

## Recommended order of work

| Order | Change or skill | Acceptance evidence |
| --- | --- | --- |
| 1 | Represent real attachments and full built-road components. Preserve per-destination progress, color and visible urgency. | Long-component, shared bare approach and same-color target regression checks. Compare actor probabilities on identical opening states. |
| 2 | Rank a feasible matching join ahead of irrelevant nearby construction. Finish two-to-four-edge routes when they are affordable. Choose Wait when a useful route is genuinely blocked or unaffordable. | Add paired city-like cases with ordinary distractor roads, colors, rotated driveways, barriers and route lengths that require an initial detour. Measure native service and use matched blocked versus open controls. Keep single-edge PPO actions and native delivery reward. |
| 3 | Decide which destination to serve first, when to preserve limited stock, and when to improve throughput. | Swap demand on identical geometry and change traffic load on an identical junction. Test one network that needs both prioritization and a bypass. Add constrained stock with competing services and several future arrivals. |
| 4 | Make city performance robust and measured across openings, horizons and maps. | Recheck repaired short starts, hard distant starts, sampled and greedy runs, held-back cities, games beyond ten minutes, and other maps. Measure native score and survival along with target coverage, unused paid roads and queue outcomes. Use independent validation before promotion. |
| 5 | Give one policy the tools and weekly pick decisions before training them jointly. | The current city actor can place a road edge or Wait. The environment picks the weekly offer with the most road units, and the normal city actor cannot erase or use bridges, tunnels, motorways, traffic lights or roundabouts. Add verified native legal action/observation paths for equipment and weekly offers. Isolate a real choice for each tool, then check transfer to a mixed full game. |

The native host passed 99 simulation suites and 1,116 Stage 1 differential legality actions. The broader Python suite ran 66 tests with 64 passes and two errors in the older staged connection practice. Both tests advance native time through a low-level call that bypasses the reward ledger, then fail the ordinary ledger parity check. The replays measured raw scores of 11 and 12 while the ledger remained zero before the final Wait. Update those test setups so the timed advancement is accounted for before using their results as a gate. The current road-only city adapter uses a separate score path and the sampled game evaluation ran to native termination or the configured time cap. [Checks and failure reproduction values](checks.json).

## Reproduction

The three probe scripts in this archive use `PYTHONPATH=training`. Run from the repository root and write to new output paths. `probe_service_features.py` takes the [previous capability archive](../city-service-capability-2026-11-23/README.md) as `--evidence`. `check_multiedge.py` takes its action record as `--witness` and the earlier completed run's game rows as `--games`. Both use the existing city host. `probe_city_traffic.py --count 6` uses the archived `traffic-live-junction-host-01` DLL and the four checkpoints in [traffic.json](traffic.json). The independent comparison used `training/evaluate_city_service.py --games 24 --seed 731709 --workers 8` with the four checkpoints in [city-summary.json](city-summary.json). Only the measurement scripts and reports were written. Checkpoints and simulator builds remain local. [Integrity manifest](manifest.json).
