# Growing-city service readiness

The user asked to work until a long run was ready, then launch it and leave it running. This continues the [verified opening repair](../city-route-repair-2026-11-22/README.md), the [one-hour later-city comparison](../city-growth-pilot-results-2026-11-22/README.md) and the [controlled midgame timing lesson](../city-midgame-service-2026-11-22/README.md) on `Maskable-PPO`.

## Native city diagnosis

A frozen audit replayed the repaired policy on 24 fresh Los Angeles seeds. It followed destinations that appeared after the city had scored. Of 101 such destinations, 69 received a delivery. All 32 that remained unserved eventually had a visible matching home, and 24 appeared while stock was empty. For 16 unserved destinations the audit found no affordable path during its observations. Only three had an estimated affordable route of one to three paid units.

The path check combines existing links and individually legal edges from the native mask. That graph can overstate joint buildability and cannot see paid options when stock is empty. Observations were sampled at network changes, spawns and five-second intervals. The audit is a diagnostic. Its path search is excluded from the policy and reward.

## Pilot

The full-city policy preserves the repaired actor’s decisions where its short-range, single-pair opening correction applies. It adds later-city signals from visible matching parcels and the road components that already exist, with a soft preference for reducing a local service gap or retaining stock when there is no promising legal edge. All native legal actions remain available. Unused-road counts come from observed trip assignments, alongside native deliveries and new-destination service. Native deliveries remain the only reward.

The first readiness attempt failed before updates because PyTorch's CUDA scatter reduction rejected a Boolean accumulator. The retry uses a floating accumulator followed by a Boolean conversion. Both used distinct output paths and the original model was preserved.

Both pilots started from the same repaired policy. The broad version encourages nearby progress and joins. The narrower version initially favors Wait only on quiet, already supplied networks with at most eight road units and no pending matched driveway or visible warning. It uses a weaker join preference. Both can learn later-city preferences through Maskable PPO. The broad run added 36,864 decisions in 198.87 seconds across 60 completed games. The narrow run added 24,576 in 158.71 seconds across 35 games.

| Matched suite | Checkpoint | Mean deliveries | Scoring games | New destinations served | Arrivals with zero road units | Median seconds to first delivery | Paid units per game outside observed routes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Broad, 24 seeds | Repaired reference | 86.29 | 20 | 83/103 | 66/103 | 57 | 30.71 |
| Broad, 24 seeds | Broad midpoint | 86.83 | 21 | 78/97 | 21/97 | 36 | 31.50 |
| Broad, 24 seeds | Broad final | 84.21 | 20 | 74/98 | 20/98 | 39.5 | 34.67 |
| Narrow, 24 seeds | Repaired reference | 81.71 | 23 | 75/101 | 52/101 | 39 | 33.75 |
| Narrow, 24 seeds | Narrow midpoint | 92.46 | 23 | 81/114 | 40/114 | 35 | 36.67 |
| Narrow, 24 seeds | Narrow final | 89.63 | 22 | 80/115 | 35/115 | 35 | 35.75 |
| Confirmation, 16 seeds | Repaired reference | 70.50 | 13 | 43/62 | 40/62 | 47 | 33.63 |
| Confirmation, 16 seeds | Broad midpoint | 51.31 | 14 | 33/53 | 12/53 | 27 | 36.25 |
| Confirmation, 16 seeds | Narrow final | 62.13 | 15 | 35/51 | 19/51 | 48 | 33.81 |

The eight-seed smoke found an initial broad mean of 77.63 versus 104.50 for the repaired reference and 10 versus 17 arrivals with empty stock. On the complete broad suite the initial mean was 85.21 versus 86.29, with 13 versus 66 empty-stock arrivals. Narrow initialization averaged 76.58 versus 81.71, with 23 versus 52 empty-stock arrivals. Corresponding aged checkpoints and per-game traces are archived below.

The confirmation reran the selected broad midpoint and narrow final on 16 different cities. The broad midpoint lost 19.19 mean deliveries, with a paired 95% bootstrap interval from −36.88 to −5.13. The narrow final had a mean advantage of 7.92 on its development suite and a mean loss of 8.38 on confirmation. Its paired intervals were −15.54 to +30.50 and −37.19 to +20.81. Across those two sets it scored 1.40 more deliveries per city on average, had 54/166 empty-stock arrivals versus 92/163 and served 115 new destinations versus 118. Spawns and game duration vary with play, so those counts use the observed destinations in each condition. The stock reduction held across both sets. City score, new service and waste did not consistently improve. The narrow final is the continuation start. The repaired reference remains the comparison baseline.

The native host passed 99 self-test suites and the existing Python set passed 14 tests. The transfer preserved the original actor tensors and produced identical probabilities on 13 observed states where the repaired short-range single-pair correction activated. Eight other checked states fell outside that scope. The checkpoint check found 21 Adam state entries in both final candidates. All tested model hashes matched. [Native audit](native-audit.json), [broad smoke](broad-smoke-summary.json), [broad review](broad-summary.json), [narrow review](narrow-summary.json), [confirmation](confirmation-summary.json) and [policy checks](policy-checks.json).

## Long run

The user authorized this launch and requested to report back when ready and leave the run in progress. Started on 23 November 2026 at 03:12:21 Beirut time in `/home/mohammadjaffal/mini_motorways` on `Maskable-PPO`, based on `6bd7f71` plus local work. The detached `city-service-long-01` tmux session restored the narrow final save at 86,016 decisions, 84 PPO epochs and 21 Adam state entries. The first completed rollout confirmed 90,112 total decisions. Training uses 32 native Los Angeles workers, a CUDA learner and score-only reward. The selected duration is eight active training hours, with saves at rollout boundaries about every 15 minutes.

Each run uses a distinct portion of the training range. The broad and narrow pilots started at 97,000,000 and 97,300,000. The long job starts at 98,000,000, below the exclusive training bound of 99,000,000. The smoke, pilot, confirmation and scheduled review suites were checked for seed overlap. The review runs after training and compares the repaired reference, the exact warm start, and roughly two-hour snapshots through the final save on 24 new paired cities in the 99,000,000–99,499,999 review range. The older reserved city benchmark remains untouched. See [launch check](long-launch.txt), [configuration and hashes](long-config.json) and [restored seed cursors](long-start.json).

Follow the console from any terminal:

```bash
tail -n 30 -F /home/mohammadjaffal/mini_motorways/output/training/city-service-long-01.console.log
```

The launch command below is recorded for reproduction. The active run already owns this output. For a future resume after the old process exits, keep the same flags, add `--resume`, and use a fresh console log.

```bash
cd /home/mohammadjaffal/mini_motorways
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u training/run_city_service_training.py \
  --dll output/city-midgame-service-build.hSMk1r/bin/TrafficHost/release/TrafficHost.dll \
  --start output/training/city-service-reserve-readiness-01/checkpoints/city-000086016-db6c8742.zip \
  --output output/training/city-service-long-01 --hours 8 --workers 32 \
  --save-minutes 15 --seed-start 98000000 --review-games 24 \
  --review-seed 870627 --review-interval-minutes 120 --reserve
```

The long run is independent of the terminal and chat. When the user reports completion, inspect local `state.json` and `review.json` in the run directory. Models, simulator binaries and the ongoing training logs stay in local output. The archive contains pilot configurations, states, paired evidence, launch evidence and a hash manifest.
