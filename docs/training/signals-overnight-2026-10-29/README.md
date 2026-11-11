# Partial overnight assessment - 29 October 2026

Run `signals-night-01` was configured for eight hours/four workers. At inspection
no learner/host was active. Its last unfinished status is15471.3 learner seconds,
125924 decisions,569758 ordinary commands and832 completed games. Final model
and final summary are absent. The cause of stopping is **unknown**; no process
was changed and no new learner or evaluation started for this assessment.

| Development measure | Mean trips | Scores on seeds2000-2004 |
| --- | ---: | --- |
| Starting policy |167.4|79 /207 /82 /132 /337|
| Best saved validation |204.2|125 /291 /154 /122 /329|
| Latest validation |185.4|237 /85 /135 /134 /336|

Best improvement is21.98% on repeatedly checked development maps, with three
improved/two worse. It is evidence of development improvement, not independent
fresh-seed generalization or a causal traffic-light benefit. The selected trained
checkpoint is local `output/training/signals-night-01/validation-best.zip`.

Best completed training replay is494 trips on seed1099,1124.7 simulated seconds.
The [exact action recording](best-game.json) is archived; it is not the same
measure as evaluating the validation-best policy. Checkpoint binaries remain
local and are identified by SHA256 in [assessment.json](assessment.json).
Latest policy is saved separately as latest.zip; it is not the best validation
model. No fresh-seed test or replay verification was newly run for this inspection.

The eight raw metric/recording copies in [manifest.json](manifest.json) retain
source-byte SHA256s. Original files remain in output/training/signals-night-01.
Earlier PDFs and immutable preparation evidence are unchanged.
