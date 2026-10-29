# Traffic-light agent and overnight training

To test whether this policy benefits from light placement, use the
[frozen ON/OFF comparison command](TRAFFIC_LIGHT_TEST.md). It runs evaluation,
not further training. The full comparison has not been run during preparation.

The optional v3 agent adds **traffic lights**, as requested, before motorways.
It keeps ordinary roads/bridges, connection and bypass proposals, upgrades and
waiting. Motorways, roundabouts, demolition and manual driveway editing remain
excluded. This is a planner-assisted agent, not a claim that PPO discovered the
router. OriginalReference rules and material stock are unchanged.

## Start overnight

Paste into PowerShell:

```powershell
cd C:\Users\moham\mini_motorways
powershell -NoProfile -ExecutionPolicy Bypass -File .\training\start_signals.ps1 -Hours 8 -RunName signals-night-01
```

This starts a **fresh v3 model**, four workers and an eight-hour learner window.
Initial/final evaluation adds time; periodic validation counts against that
window. The launcher builds the headless host first and selects a 10-million
decision ceiling so time is normally the limiting budget. Use `-Hours 6` for six
hours. Keep the computer awake and plugged in. No scheduled/background task is
created by preparing this command. A run starts only when you execute it.

If the folder exists, choose `signals-night-02`; existing models are never
overwritten. Older v1/v2 checkpoints have different inputs/actions and cannot
resume directly into v3. They remain intact. New v3 starts retain the engineered
connection prior, but do not claim to continue weights from the earlier runs.

The console prints elapsed/remaining time, per-worker games, scores, car waiting,
traffic lights placed, checkpoints, PPO update count, entropy and KL. Validation
prints its per-map scores and the difference from the starting model. KL and
entropy describe probability updates, not game skill. Games/second also depends
on episode survival and is not equivalent to commands/second.

**Ctrl+C saves and stops.** Checkpoints are also saved every two minutes as
`latest.zip`. `final.zip` is the last policy; `validation-best.zip` is the best
development policy, with its score and baseline flag in `validation-best.json`.
The starting model is eligible and wins ties, so the best checkpoint can remain
untrained when learning does not help. The last evaluation is eligible too.

Watch the best recorded game from another terminal after it records actions:

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\watch_best.py --run output/training/signals-night-01 --play
```

To deliberately continue the **best validation** v3 policy on another night:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\training\start_signals.ps1 -Hours 8 -RunName signals-night-02 -Resume output/training/signals-night-01/validation-best.zip
```

For exact continuation from the last saved optimizer instead, choose `final.zip`;
it can perform worse. Resume inherits reward scale, prior temperature and timing.
Each continuation needs a fresh output folder. Inspect initial/final/validation
scores before claiming learning; a single training best is not sufficient.

## Exact v3 contract

Schema: `visible-route-signals-policy-v3`; **547 actions**, **21,107 parameters**.
The first 515 actions retain v2 meanings (wait, two upgrade slots, 512 route
proposals). Actions 515-546 select up to 32 proposed traffic-light locations.

Candidates must be visible legal ordinary-road cells with at least three
connections, available light stock, no pending removal/building/roundabout or
motorway endpoint. Existing light tiles are excluded. Candidates are ranked by
maximum waiting in the cell/eight visible neighbors, then nearby vehicle count,
then map index. The model can always wait; lights are not compulsory. A placement
executes the ordinary `build TrafficLight` command and consumes normal inventory.
It does not create materials or remove roads. Only accepted placements are counted.

The simulator gives lights a real trade-off: ordinary degree>=3 junctions use
a .5 speed multiplier; light tiles are exempt from that penalty. Red/amber
approaches must stop, and the phase controller chooses approaches using cars
and waiting. Removing the speed penalty is not a guarantee of doubled throughput
or improved trip totals. Net benefit of this agent's placements has not been
isolated by a controlled lights-disabled test. These are code-inspection facts,
not a new throughput measurement; simulator rules remain unchanged.

The v2 route rows (512 x 32) and 42 globals remain. Traffic becomes 5 x 30 x 50:
vehicle count / 10, max wait / 60, road presence, degree / 8, **existing light**.
The light plane uses actual simulator infrastructure code 4. Hidden cells are zero;
all values clipped. It is a cell snapshot, not lane flow or forecast capacity.

Signal observations are 32 x 12, normalized/clipped to [0,1]:

| Index | Value |
| --- | --- |
| 0-2 | x / 50, y / 30, connection degree / 8 |
| 3-4 | Cell vehicle count / 10, maximum waiting / 60 |
| 5-7 | Nearby vehicle count / 20, max nearby waiting / 60, fraction nearby cells with waiting >= 3s |
| 8-10 | Light stock / 10, road stock / 100, current week phase |
| 11 | Valid candidate flag |

Signal positions/features and masks refresh at every decision. The router's
existing 15-second bypass-search cadence is unchanged. No future state is exposed.
Light phases follow the existing simulator; the agent places lights but does not
set their timing or choose which lane receives green. Cars retain their existing
routing rules, and a light can make a junction worse.

The shared signal network is 12 -> 32 -> 1. An initial trainable linear prior
uses `-1 + 2 * cell_wait/60 + 2 * nearby_wait/60`; the residual starts at zero.
The route actor now also receives global/traffic-map context through a zero-start
32-value interaction with candidate embeddings. In v2, the map CNN fed tool logits
and critic but not route-choice logits directly. This new route context is an
architectural change, not a measured proof of improved decisions.

Default v3 `--prior-temperature 2` divides the trainable linear route/signal prior
and fixed upgrade-offer bias by two. Learned residual/context logits are not
divided. At fresh initialization the argmax is unchanged; sampled choices become
more varied. This is an experimental exploration choice, not a proven score gain.
`--prior-temperature 1` reproduces original-strength priors for a fresh comparison;
resume rejects a temperature mismatch rather than silently altering the policy.

Reward is unchanged: actual trip delta plus `0.99 * next_potential - old_potential`,
potential `.25 * min(connected_houses, 8)`, terminal potential zero, numerical scale
`.01` in the launcher. There is **no reward for placing a light or merely building
a road**. Gamma/lambda .99, aggregate rollout 256, batch 64, four epochs, learning
rate .0001 and entropy coefficient .005 remain. Discounting is per macro decision,
whose duration varies; it is not per simulated second. Early connection shaping
saturates after eight houses and does not teach later congestion management itself.

Training uses random seeds 1000-1099. Development checks use 2000-2004. The old
investigation's final maps were not reused for tuning this change.

## What is established

The old v2 audit on one frozen trajectory found only 1/42 changed top choices,
mean KL about 0.0000415, despite changed weights. Sixty states had only one legal
action; average choice-state max probability was .488, so this does not establish
that every state lacks exploration or identify one sole cause of weak learning.

Two controlled 512-decision v3 pilots used identical initial tensors and settings
except prior temperature 1 vs 2. Both started at 79/207/82 and ended at 79/208/80
on three development maps: mean **122.67 -> 122.33**. Both retained their initial
policy as validation best. Signal and route-context parameters updated, and real
lights were placed, but no score improvement was established. A paired frozen
58-choice-state check increased mean entropy 1.849 -> 1.978, with no changed
argmax. This measures more varied probabilities, not learned skill.

Subsequent user overnight result: the run stopped early at about4h18m/8h, cause
unknown. Best development mean improved167.4->204.2; latest was185.4. The best
training recording was494. These are development results, not a fresh-seed test.
See [overnight assessment](../docs/training/signals-overnight-2026-10-29/README.md).

The subsequent frozen fresh-map check used ten unseen LosAngeles seeds4000-4009.
Deterministic mean rose161.3->207.4 (nine wins/one loss); sampled mean182.0->188.9
(five wins/two ties/three losses, aggregate gain mainly one map). This supports
deterministic transfer, with limited evidence for sampled improvement. No weights
or checkpoint selection were changed. See
[full fresh-map result](../docs/training/signals-fresh-2026-10-29/README.md).

The new actions/observations, normal stock/replay, update/save/reload, four-worker
startup/resume and baseline checkpoint protection were checked. A full overnight
experiment has not completed. See [preparation measurements](../docs/training/signals-2026-10-29/README.md)
and [history](EXPERIMENT_HISTORY.md). Existing PDFs remain historical snapshots.
