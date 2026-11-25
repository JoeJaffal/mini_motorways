# Frozen bypass transfer check

The user approved replaying the interrupted geometry continuation before spending more time on training. The active Linux checkout is `/home/mohammadjaffal/mini_motorways` on `mohammad`. Both checkpoints came from the [demand priority and congestion session](../traffic-milestones-2026-11-21/README.md). The original policy saved 36,864 decisions. The geometry continuation added 15,360 decisions and saw the original junction, a mirror and a moved gap individually. The combination of a mirror and a moved gap was held out of training.

## Method

Both checkpoints and all three native controls played the same 100 seeds, 84300–84399, per combination of layout and traffic level. The layouts were the original junction, the relocated gap and the relocated gap with a mirrored board. The actor used its usual visible observation and legal masks, with no geometry transform. Decision-making began at native second 36 and ended at second 120 or at native game-over. The episode starts with one paid road unit. Scores count deliveries after the warm-up. The evaluator advanced in five-second Wait intervals, the same evaluation cadence used in the original report. Stopped cars count visible moving-stage vehicles below 0.22 speed units at each Wait sample and are averaged within each game. Native early endings are included in the averages.

The comparison used the shipped fixture's immediate feeder and bypass controls and an all-Wait control. Edits were matched by native action ID for the same seed and layout. The action counts explain how the models obtained their scores and all scored play is included regardless of the chosen legal edit. The paired replay checked native stock and trip accounting and verified that each policy fingerprint was unchanged. Only frozen evaluation ran.

## Result

The continuation kept the delivery score on the original junction and improved the shifted layouts. The action traces show that on shifted heavy boards the improvement mostly came from extending the existing feeder. The actor rarely found the new bypass edge. The original live policy remains the reference for its original junction.

| Heavy-traffic layout | Original bypass, greedy / sampled | Continuation bypass, greedy / sampled | Greedy trips, original / continuation / native bypass | Greedy stopped cars, original / continuation / native bypass |
| --- | ---: | ---: | ---: | ---: |
| Original | 99 / 98 | 86 / 86 | 31.85 / 31.83 / 31.88 | 0.45 / 0.74 / 0.41 |
| Gap moved | 0 / 16 | 7 / 15 | 27.39 / 29.73 / 31.88 | 2.43 / 3.86 / 0.41 |
| Mirrored and gap moved | 2 / 37 | 0 / 13 | 29.01 / 29.26 / 31.73 | 3.96 / 4.14 / 0.42 |

Each action count is out of 100. On the moved heavy gap, the original greedy policy left the stock unused in 53 games and had 19 native early endings. The continuation chose the feeder in 93 games, opened the bypass in seven and had two early endings. Its 2.34 extra deliveries came with 1.43 more stopped cars per game. The fixed feeder averaged 29.31 trips and 4.20 stopped cars. On the mirrored and moved heavy gap, the continuation reproduced the native feeder on all 100 greedy games, averaging 29.26 trips and 4.14 stopped cars. Opening the bypass would have averaged 31.73 trips and 0.42 stopped cars, with five early endings compared with three for the feeder. The continuation sampled the bypass in only 13 of those games and earned 29.68 trips on average.

Light-traffic behavior remained reliable. The continuation chose the feeder on 298/300 greedy and 283/300 sampled games across all three layouts. The greedy delivery means were 15.28 on the original and moved layouts and 15.27 on the mirrored moved layout.

All 4,200 replays passed native stock, summed shop-score and seed-pairing checks. The two checkpoint SHA-256 hashes and stored update fingerprints matched the frozen results. The measurements cover one junction family. Waiting before the surge, more varied road networks and full-city play remain open.

## Next experiment

The evidence favors testing the initialized road-end scorer on several missing-link positions. Its feature counts visible degree-one endpoints using existing built links. The policy still chooses among all native legal edits and Wait, using native deliveries as its reward. Keep a combined geometry held out and check for retention on the original board. This would test the hypothesis that explicit road-end structure helps the policy recognize a useful bypass away from its original coordinates. The scorer has initialization evidence only.

## Reproduction

From the Linux training checkout, use the following command for the continuation and choose a fresh output file. The parent uses the same command with checkpoint `output/training/traffic-live-ppo-01/latest.zip`. To reproduce native controls, use `controls` in place of `evaluate` and omit the checkpoint option.

```bash
.venv/bin/python training/traffic_ppo.py evaluate --exercise junction \
  --stages traffic-junction-low-live traffic-junction-high-live \
           traffic-junction-low-live-shift traffic-junction-high-live-shift \
           traffic-junction-low-live-mirror-shift traffic-junction-high-live-mirror-shift \
  --dll output/training/traffic-varied-junction-host-01/build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint output/training/traffic-live-varied-ppo-01/latest.zip \
  --horizon 120 --warm-seconds 36 --wait-ticks 100 --offset 6300 --count 100 --workers 6 \
  --output output/training/junction-transfer-replay-new.json
```

The compiled host and weights are local. The parent report preserves the [source patch for the mirrored and shifted geometry](../traffic-milestones-2026-11-21/varied-junction.patch). This archive retains the [parent replays](original.json), [continuation replays](continuation.json), [native controls](controls.json), [per-condition summary](summary.json) and [evidence hashes](manifest.json).
