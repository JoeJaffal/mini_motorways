# V4 fresh-map result - 30 October 2026

User completed the frozen comparison on ten new Los Angeles seeds6000-6009.
The initial policy is this trial's v3-weight warm start, not a model trained from
scratch. The selected policy is its development-best checkpoint after one hour.
Protocol/seeds/checkpoint hashes were recorded before the test. No training,
retuning or new policy selection occurred during evaluation or this inspection.

| Mode | Trial starting mean | Selected mean | Change | Better / tied / worse |
| --- | ---: | ---: | ---: | --- |
| Deterministic |175.9|194.0|+18.1 / +10.29%|2 /5 /3|
| Sampled |168.7|169.0|+0.3 / +0.18%|1 /9 /0|

The deterministic gain comes from seeds6003 (+132) and6004 (+72); the other
eight net-23. Sampled scores tie on nine maps and gain3 on6005. Thus the point
average improved, but broad/reliable improvement is not established. This does
not isolate feature benefit versus equally long additional v3 training, nor
prove improved light-placement judgment. Light counts are24->28 deterministic
and24->24 sampled. More placements alone are not evidence of better placement.

All40 games ended naturally before3600 simulated seconds. Parameter tensors
were unchanged, report checkpoint hashes match the predeclared protocol, and
the protocol digest matches assessment.json. Runtime checkpoints remain local.
Complete reports, paired scores, stdout/stderr and best recordings are archived
with byte hashes in manifest.json. Replays were not newly executed/verified for
this inspection, and no further jobs were launched. These seeds are now exposed
test data, not fresh tuning targets. One trained run/ten maps/one sampled path
per seed are important limits. Earlier reports/archives remain historical.
