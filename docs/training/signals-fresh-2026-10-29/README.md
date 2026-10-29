# Fresh-map evaluation - 29 October 2026

The [protocol](protocol.json) was frozen before inference: overnight initial
versus development-selected best, seeds 4000-4009, primary deterministic and
secondary sampled trajectories, 3600 simulated seconds, no training/reselection.
Checkpoint, runtime and inference source hashes are recorded. All 40 games are
complete, at most two evaluation jobs ran concurrently, and all ended naturally
before the cap. Both policies use the same current simulator and inference code.
These are unseen layouts/seeds within Los Angeles, not different cities.

## Results

| Mode | Starting policy mean | Trained policy mean | Difference | Better / tied / worse maps |
| --- | ---: | ---: | ---: | --- |
| Deterministic (primary) | 161.3 | 207.4 | +46.1 / +28.58% | 9 / 0 / 1 |
| Sampled (secondary) | 182.0 | 188.9 | +6.9 / +3.79% | 5 / 2 / 3 |

| Seed | Initial deterministic | Trained deterministic | Initial sampled | Trained sampled |
| --- | ---: | ---: | ---: | ---: |
| 4000 | 145 | 153 | 170 | 170 |
| 4001 | 125 | 155 | 169 | 152 |
| 4002 | 65 | 83 | 288 | 285 |
| 4003 | 147 | 221 | 218 | 217 |
| 4004 | 119 | 327 | 138 | 148 |
| 4005 | 164 | 326 | 221 | 226 |
| 4006 | 72 | 95 | 102 | 172 |
| 4007 | 408 | 265 | 231 | 234 |
| 4008 | 81 | 142 | 75 | 77 |
| 4009 | 287 | 307 | 208 | 208 |

The primary result supports transfer of improved deterministic decisions beyond
the training/development seeds. It does not establish universal reliability or
rule out all overfitting. Secondary sampled improvement is weaker: seed 4006
contributes +70 trips to a total paired gain of +69; the other nine net -1.
There is only one sampled trajectory per seed and one trained model, on ten
fresh maps. No confidence claim or causal traffic-light benefit is asserted.
No policy was retuned, reselected or updated after these results; these seeds
are now exposed test data and should not be treated as fresh again for tuning.

## Selection and verification

Selected model is the overnight `validation-best.zip`, chosen at 77,220 training
decisions using development mean 204.2 **before** this test. Initial baseline is
the same run's `initial.zip`; the current last policy and the maximum-training
replay policy were not tested as selection alternatives. Runtime checkpoints
remain local; their hashes are in the protocol/reports. All four evaluator jobs
checked tensors unchanged and checkpoint file hashes remained fixed.

[Assessment](assessment.json) contains paired differences and full protocol hash.
Per-policy files retain scores, waiting, placements, rejections and terminations.
The four saved best replays were verified by executing their exact ordinary
commands in the headless runtime; [verification](replay-verification.json) records
the results. These checks are replay reconstruction, not four additional policy
tests. Source files and 40-game stdout/stderr traces are archived too.

The [manifest](manifest.json) records byte SHA256s for copied outputs and inference
sources. No weights or generated binaries are archived. Original runtime output
is under `output/experiments/signals-fresh-20261029`. Historical reports and the
overnight checkpoint selection remain unchanged. Driver source is preserved in
`sources/evaluate_fresh_signals.py` and tracked under training/.
