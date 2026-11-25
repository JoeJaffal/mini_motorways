# Growing-city frozen baseline

The second overnight milestone measures the [selected city starting checkpoint](../city-policy-start-2026-11-22/README.md) on `Maskable-PPO` before city PPO updates. The 32 Los Angeles scenario seeds and paired action seeds were fixed before evaluation. All conditions started with an empty road network and used the native game, legal single-edge mask, delivery-only reward, automatic weekly road award, and 600-second evaluation horizon.

Each scenario had five runs. Sampled transfer and sampled fresh initialization both used the city policy architecture. Greedy transfer took the most probable individual action. Uniform edges used the same 50% Wait probability as the initialized policy whenever roads were legal, then chose a road uniformly. Uniform legal actions gave Wait and every legal edge the same individual probability. All conditions used the same scenario and action seed for each pair, with one sampled trajectory per condition and scenario.

## Results

| Policy | Games scoring | Mean score | Median score | Best | Median survival | Mean roads spent | Games with an award |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Transfer, sampled | 24/32 | 32.19 | 26.5 | 94 | 259.75 s | 65.03 | 30/32 |
| Transfer, greedy | 0/32 | 0 | 0 | 0 | 144.90 s | 0 | 27/32 |
| Fresh initialization, sampled | 0/32 | 0 | 0 | 0 | 135.20 s | 29.09 | 7/32 |
| Uniform edges with matched Wait | 0/32 | 0 | 0 | 0 | 135.20 s | 29.09 | 7/32 |
| Uniform legal actions | 0/32 | 0 | 0 | 0 | 134.90 s | 32.78 | 8/32 |

All 160 games ended at native game-over. Sampled transfer won 24 paired games and tied eight against each control. The paired score advantage was 32.19 deliveries on average, with a 95% paired bootstrap interval of 22.88–42.09 on this suite. Because the matched-Wait uniform control also scored zero, the transferred road preference explains the observed advantage at the same initial Build/Wait balance. The transferred policy played longer, so its total road spend includes stock received over more weeks.

Greedy transfer made zero road draws across the suite. At initialization the Wait action gets half the probability when a build is legal, with the other half shared by all legal roads. Greedy play chose Wait in this setup while sampling gave the transferred scorer a chance to act. Eight sampled transfer runs scored zero, and six of those ended with available road stock. Sampling demonstrates construction transfer on these native Los Angeles seeds. Reliable cold starts and learned timing remain open.

Keep this fixed test suite out of training and checkpoint selection. The next milestone is a short score-only PPO pilot from the selected checkpoint, using separate training and development seeds. Compare deliveries, zero-score frequency, survival and road spending with the frozen start.

## Reproduce

Run from the Linux training checkout. The evaluator uses eight CPU workers in this record. Use a new output directory.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python /home/mohammadjaffal/mini_motorways/training/evaluate_city_policy.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint /home/mohammadjaffal/mini_motorways/output/training/city-road-start-01/city-start.zip \
  --seed-suite /home/mohammadjaffal/mini_motorways/docs/training/city-frozen-baseline-2026-11-22/seed-suite.json \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-road-frozen-baseline-recheck \
  --workers 8
```

[Seed suite](seed-suite.json) · [Per-game evidence](episodes.jsonl) · [Summary and paired comparisons](summary.json) · [Checksums and source identity](manifest.json). The checkpoint and compiled host are local-only. The evaluator reuses the first milestone's frozen replay with optional action sampling and action seed parameters. The 14 existing construction and observation tests passed, and both random controls were checked against normal and forced-Wait masks.
