# Results: watched play and whole-city PPO

All three bounded training runs and their reviews are complete. No candidate promoted; no long session launched. Reference and all checkpoints retained.

Training: 98,304 decisions, 3,072 Adam updates, 195 completed episodes across three matched32k trials.

| Model | Repeated-city mean | Separate-validation mean | Scoring games (repeated / separate) |
|---|---:|---:|---|
| Reference | 126.25 | 125.94 | 15/16 / 15/16 |
| Gated control32k | 101.88 | 115.38 | 15/16 / 15/16 |
| Whole-city midpoint16k | 119.00 | 95.00 | 15/16 / 14/16 |
| Whole-city final32k | 129.50 | 133.75 | 15/16 / 14/16 |
| Finite-horizon whole-city32k | 121.50 | 116.44 | 15/16 / 14/16 |

All games have600s horizons and bridge legality. Each column covers eight layouts,two action RNGs each. Validation layouts never enter training,but are used for selection;these are not independent final-confirmation results. Paired intervals resample cities. No reliable reference improvement established.

The whole-city version outperformed gated control on the repeated set (+27.625,95%[4.6875,52.6875]),but gains versus reference are uncertain,and separate-city scoring count falls15→14. Finite-cutoff final repeated delta−4.75,95%[−21.3125,7.625];separate delta−9.5,[−41.5625,28.125]. The cutoff hypothesis did not produce a score fix.

## What watching revealed

The failed reference anchor spends all initial roads by26s on branches/loops before completing service,then ends with0 at151.15s. Whole-city final reaches175 at600s with first delivery32s. The second anchor changes158→172. However32 fresh action RNGs on the first opening give27/32 success for both reference and final. One favorable replay is not a reliable repair. Finite-horizon anchor scores20 and168.

At16 inspected initial states,the whole-city actor changes mean Wait probability by−0.016868,while conditional-road TV averages0.000370. The first differing action on the improved replay can be reproduced by changing only Wait mass in the joint categorical sampler. This supports investigating weak road-choice adaptation;it does not prove a sole global cause or establish that a longer run cannot learn.

## Changes and checks

Optional whole-city correction removes the established-service gate without changing initial weights/actions/values. Repeated-city training is optional;defaults remain unchanged. Optional finite horizon changes learning termination semantics only for that diagnostic. Native rewards remain deliveries;no planner,teacher actions,new reward term or physics change.

Checks:256 exact initial actor/value states;opening gradient0 gated versus2.86916 whole;reset cycle/bypass;three policy/reporting tests;first8 pre-update episodes exactly matched;729-transition finite-horizon parity;post-training allowed-weight/finite/optimizer audits. All three runs completed1024/1024 updates. Figures were visually inspected. Replay selector/timeline logic passed six combinations in a JavaScript VM with stub DOM/canvas,not a browser rendering test. Sampled snapshots are labeled frames,not policy decisions.

## Artifacts and remaining question

[Interactive comparison of both preselected games and all three policies](compare-play.html). [Measured source results](results.json). [Plan and chronological choices](PLAN.md). [Full experiment history](../../../training/EXPERIMENT_HISTORY.md). Weights/native binaries are local-only;see local-artifacts.json and manifest.json.

Current strongest remaining lead: road-choice adaptation is weak at the inspected opening states,while Wait changes can create visually dramatic but unreliable trajectory changes. Next work should measure/target road-choice learning and exploration on repeatable native decisions,then test untouched layouts. These small one-training-seed trials do not establish impossibility or justify promising overnight score gains.
