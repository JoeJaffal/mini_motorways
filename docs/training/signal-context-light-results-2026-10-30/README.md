# V4 traffic-light availability result - 30 October 2026

Twenty frozen deterministic games on paired seeds7000-7009 completed naturally.
Checkpoint matches the predeclared v4 validation-best selection; weights did
not change. No simulation/training was launched during this result inspection.

| Condition | Mean trips | Descriptive mean per-game car wait |
| --- | ---: | ---: |
| Light placement enabled |177.5|1.0564s|
| Light placement disabled |159.1|1.5240s|

Enabled improves the mean by18.4 (+11.56%), with three wins, six ties and one
loss. Differences by seed are134/0/0/15/0/0/0/155/-120/0. Thus the effect is
mixed, with a large loss on7008 despite positive average benefit. ON placed22
lights; OFF none. Waiting is descriptive and confounded by different survival/
load. This is a policy availability intervention, not isolated light physics.

This supports keeping light actions available for this selected model on this
set, not universal benefit or proof that the v4 inputs caused improvement over
v3: their earlier availability tests used different seeds. No post-test policy
selection or feature/reward change occurred. The current model was chosen by
development validation before these tests. Future unseen tests require new seeds.

Reports, paired scores, traces and best recordings are preserved byte-for-byte
with source hashes in manifest.json. Replays were not newly executed/verified
for this inspection. Weight files remain local. A bounded user-run continuation
of the same architecture/settings is recommended before further feature expansion;
it has not been launched by the assistant.
