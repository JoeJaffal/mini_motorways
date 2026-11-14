# Traffic-light preparation, audit and pilots - 29 October 2026

This archive records the user-authorized learning audit, addition of traffic
lights before motorways, controlled short pilots and overnight preparation.
The overnight run has **not** been started. The exact current contract and
command are in [SIGNALS.md](../../../training/SIGNALS.md).

## Findings

The [old-policy audit](old-policy-audit.json) follows the v2 initial policy's
deterministic development-seed-2000 trajectory, comparing initial/final
probabilities on identical states without changing weights. It saw 42 states
with multiple legal actions and 60 forced states; one top choice changed.
Mean choice-state KL was 0.00004154; initial max probability averaged .488 and
entropy 1.246 nats. Thus updates barely affected this trajectory, but the
measurements do not prove universal lack of exploration or identify the cause
of the separate seed-2001 regression. No final-test seed was used.

Code inspection found that v2's traffic CNN supplied tool/critic context but did
not directly condition route-choice logits. V3 adds a zero-start global/map
interaction to route embeddings, legal traffic-light candidates and existing
lights on the map. It keeps the simulator and reward unchanged. Reward identity,
terminal potential accounting and normal tool stock were tested; adequate
long-horizon credit assignment has not been established.

## Controlled pilots

Both v3 arms used seed 42, identical initial tensors, two workers, 512 decisions,
gamma/lambda .99, rollout 256, four epochs, batch 64, learning rate .0001,
entropy .005, reward scale .01 and development maps 2000-2002 capped at 1200s.
All evaluated games failed naturally before the cap. Training environments keep
their normal 3600s cap. The sole controlled algorithm setting was the prior
temperature: 1 versus 2. The two runs overlapped in wall time, so their durations
are not a valid speed comparison. The controls are too small for a learning claim.

| Setting | Initial scores | Final scores | Initial / final mean | Selected best |
| --- | --- | --- | --- | --- |
| Temperature 1 | 79 / 207 / 82 | 79 / 208 / 80 | 122.67 / 122.33 | Initial policy |
| Temperature 2 | 79 / 207 / 82 | 79 / 208 / 80 | 122.67 / 122.33 | Initial policy |

No score improvement was established. Both had parameter updates in the route,
map/context and light heads, and training trajectories used real lights. Their
training bests (236 and 222) are not independent evidence of improvement. The
starting model wins validation ties and cannot be replaced by a worse trained
checkpoint merely because it was the first periodic evaluation. The final
evaluation is also eligible if it strictly improves the best mean.

[Assessment](assessment.json) verifies initial tensors match and selected weights
equal the initial weights. It records checkpoint SHA256s and parameter-group
changes. The earlier v2 frozen comparison scored 79/209/82, so adding the initial
light-placement policy itself did not establish better performance either.

A separate [paired temperature audit](temperature-audit.json) uses the two frozen
initial v3 policies on the same seed-2000 trajectory. On 58 choice states, mean
entropy increased 1.849 -> 1.978 and max probability fell .369 -> .300; all top
choices were identical. This is more varied sampling by engineering, not learning.
Default temperature 2 remains an experimental exploration setting; no tuning
followed the pilot results and no score benefit is claimed.

## Checks and limitations

Thirty checks passed across goal (8), signal (3), workflow (5), environment (7),
reward (6) and shutdown (1) suites. The signal integration check earns stock via
normal weekly offers, places a light, verifies exact light/road stock accounting,
legal masking and the existing-light plane, and verifies its ordinary-command
replay in the headless simulator. It also exercises the light head's gradients;
this is not evidence the placement strategy learned to be useful. No debug grants
or teacher data were used. V3 route-context updates and save/reload were checked.

[Four-worker startup](four-worker-smoke.json) and
[resume](resume-smoke.json) finished normally. They were intentionally too short
for a PPO rollout/update and report `parameter_update_confirmed:false`; they are
not performance trials. [Resume configuration](resume-config.json) confirms v3,
temperature 2 and scale .01 were inherited without respecifying those flags.
The [frozen evaluator smoke](evaluator-smoke.json) detected v3 automatically and
kept weights unchanged. Direct v2-to-v3 resume was rejected before output creation.
The PowerShell launcher parsed; its headless build passed without warnings/errors.

The first signal test caught a mistaken light infrastructure code (3 rather than
actual 4); corrected before pilots. A workflow test double initially appended an
extra `.zip`, corrected to match SB3 save behavior. The first reward-suite command
lacked the local dotnet path; rerun with it passed. Current global encoding avoids
constructing an unused 52-channel grid and is checked equivalent to the old values;
no quantified speedup is claimed. Accepted-placement counting was hardened after
pilot source snapshots; all pilot rejected-action counts were zero, so this did
not change their outcomes. Later edits added reporting/interrupt safeguards only.

## Archive integrity

[Manifest](manifest.json) contains SHA256s for 34 byte-identical source/metric
copies, including the two pilot source snapshots. No weights or generated native
binaries are archived. Runtime checkpoints/replays remain local under the run
names in the assessment; the snapshots identify the exact pilot implementation.
Verify from the repository root:

```powershell
.\.venv\Scripts\python.exe -c "import json,hashlib; from pathlib import Path; p=Path('docs/training/signals-2026-10-29'); rows=json.loads((p/'manifest.json').read_text()); assert all(hashlib.sha256((p/r['archived']).read_bytes()).hexdigest()==r['sha256'] for r in rows); print('PASS',len(rows),'archived files')"
```

The old investigation PDF and its immutable archive remain historical. No
overnight performance, robust learning, 1000-trip success or commercial-game
fidelity is established by these preparation checks.
