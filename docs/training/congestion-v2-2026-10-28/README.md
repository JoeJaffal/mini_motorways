# Congestion v2 development check - 28 October 2026

This follows the user's request to prepare congestion-aware learning. It does
not supersede or modify the completed investigation PDF or its final tests.
See [exact inputs, algorithm, restrictions and commands](../../../training/GOAL_AGENT.md).

## Frozen engineering comparison

`training/compare_congestion.py` ran deterministic, informed **initial** policies
on development seeds 2000-2002, with a 1,200-second simulated cap and ordinary
finite stock. All nine games ended by game failure rather than the cap. No policy
was optimized. Parameter tensors were checked unchanged after each arm; v2 arms
have identical initial-weight hashes. v1 has a different input architecture,
although its engineered initial candidate prior is the same. This is a small
development comparison, not an independent final test or evidence of learning.

| Arm | Seed 2000 | Seed 2001 | Seed 2002 | Mean |
| --- | ---: | ---: | ---: | ---: |
| v1 with live traffic fix | 161 | 85 | 115 | 120.33 |
| v2 traffic inputs, bypasses disabled | 161 | 85 | 115 | 120.33 |
| v2 traffic inputs and bypasses enabled | 79 | 209 | 82 | 123.33 |

The bypass-enabled arm selected 5/3/6 bypasses. One map improved and two worsened;
the +3.0 mean difference establishes no reliable improvement. No tuning or
selection followed this comparison. The new actions can spend materials poorly;
the future training experiment must demonstrate benefit relative to its own
initial policy. More observation accuracy does not itself imply learned skill.
Read [complete scores, waiting and frozen hashes](results.json).

## Verification and local artifacts

Eight goal-agent unit/integration checks passed in 14.862 seconds. Coverage:
live cache-hit occupancy/wait refresh; full-grid values and contract; physical
bypass availability with synthetic congestion and ordinary-command replay;
v2 actor and CNN parameter updates plus save/reload; old policy save/reload;
finite-resource gameplay/replay; reward scaling; forced-wait equivalence.
Synthetic congestion is injected only for the proposal test, not performance
measurement. A missing `speed` key in the new synthetic grid fixture initially
failed; corrected fixture and full suite passed. The initial v1 invocation also
required the local dotnet executable rather than PATH (recorded in history T21).

The [four-worker startup smoke](startup-smoke.json) finished normally in 2.136
learner seconds, 36 aggregate decisions/159 commands. It was deliberately too
short for a PPO rollout/update; `parameter_update_confirmed:false` is expected.
This is a startup check, not a learning experiment. Its development evaluation
before/after both scored 79. The [frozen evaluator smoke](evaluator-smoke.json)
loaded the new schema automatically and verified unchanged weights at a short
120-second cap (7 trips); this is not comparable with full-game scores.

Runtime artifacts and three comparison best replays remain local under
`output/experiments/congestion-v2-20261028`; the small startup checkpoint is under
`output/training/congestion-v2-smoke-20261028`. They are not Git-backed weights.
No long run is active. A fresh 30-minute trial is the next measurement, not a
claim that the new model is better. The 18,205-parameter v2 model cannot resume
older v1 tensors; resuming a v2 checkpoint automatically restores its inputs.
