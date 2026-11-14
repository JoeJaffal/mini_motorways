# Seed 5009 failure diagnosis - 29 October 2026

User authorized tracing the bad ON/OFF case. No model training, reward change,
simulator modification or checkpoint reselection was performed. This is analysis
of an already exposed diagnostic seed, not a new generalization test.

## First divergence and failure

Frozen policy reruns reproduced **279 ON at824.9s** and **475 OFF at1097.0s**.
The regenerated OFF actions exactly match the previously saved original475-trip
recording. Both policies share the first675 ordinary commands. At675s, with196
trips, ON places a light at **(15,15)**, while OFF draws **(16,7)->(17,6)**.
That is a different command, not a claim that the stroke adds useful road.
ON places its second light at **(24,14),697s**. Subsequent policy trajectories
differ; the aggregate196-trip gap is not an isolated physical-light effect.

ON ultimately fails because green destination28 at(21,8) reaches an overcrowding
timer of50.043s, with7 demand against capacity6. At800s ON and OFF both have263
trips and the green timer33.443s. By820s total trips are still275 in both, but
the green timer is45.143s ON versus3.889s OFF. Thus similar global trip counts
hide very different survival pressure at one destination. The specific microscopic
route/arrival chain causing the difference was not fully isolated.

## Fixed-command counterfactuals

Replayed the ON construction/upgrade schedule. Each omitted light build becomes
an ordinary one-second wait. Road commands remain fixed; no model is called to
adapt them. After the original ON command horizon (~825s), only waits are issued.
All commands were accepted and no resources were granted. Original failure can
truncate its last one-second step, so horizon timestamps differ slightly.

| Light configuration, fixed ON command schedule | Trips at failure | Failure time |
| --- | ---: | ---: |
| Both lights, original ON |279|824.9s|
| First only; omit second |374|964.95s|
| Second only; omit first |277|824.55s|
| Neither |276|824.6s|

The second placement hurts **when the first is present**; the first alone is
beneficial in this fixed construction schedule. Removing both does not recover
the full OFF policy's475, showing that its different command/timing decisions
also matter. Effects interact; the table does not justify banning all lights.
The first-only counterfactual has277 trips at825s, versus original279 at824.9s:
its later374 comes from survival, not an immediate throughput increase. It later
fails at an unserved purple destination54 after the fixed building schedule ends.
A live first-only policy could make new choices and need not score374.

## Concrete observation gap

Just before the second placement, car41 near(24,14) is stopped for8.05s with
obstacle **"Carpark access occupied"**. The nearby blue destination27 is at
(24,12), with entrance(24,13) facing road cell(24,14). The light site's degree
is3; the first light site's degree is6. The existing simulator explicitly blocks
parking access while another car enters/leaves, independently of green phases.

Current light-candidate features encode aggregate waiting/counts/degree, not why
cars are waiting or which downstream destination is threatened. This is an input
gap and a plausible reason for poor placement, not proof of the network's internal
reasoning. Exposing queue causes and destination/approach pressure is a reasonable
next engineering hypothesis. No such feature change or location-specific ban was
implemented; one diagnostic map cannot validate a general fix.

## Evidence and reproduction

[Assessment](assessment.json), [detailed diagnosis](diagnosis.json) and
[measured timelines](timeline.json) preserve results, state summaries and exact
timestamps. All five [replay verifications](replay-verification.json) passed in
the headless simulator. Source copies and selected raw observations/recordings
are covered by [manifest](manifest.json). Exact replays can be opened with
training/watch_best.py --replay FILE --play; the omitted-light replays are fixed
command counterfactuals, not neural-agent runs. Native viewer playback was not
newly inspected for this diagnosis.

Full per-command ON/OFF traces (~11MB combined), decision logs and counterfactual
traces remain local under output/experiments/light-failure-5009-20261029. Their
hashes are in local-artifacts.json; the compact archived timelines and complete
command replays permit reconstruction. Checkpoint weights remain local and their
SHA256 is recorded in protocol.json. No future diagnostic state was fed back to
the policy. Existing earlier archives/PDFs remain unchanged.

An optional chart renderer could not import Matplotlib in the available Python
environments. It was removed; no chart is claimed or supplied. Measurements and
timeline source data are preserved, without installing/changing training packages.
