# One-hour Maskable-PPO implementation check-in

Work window requested by user:16November2026,17:11:03–18:11:03UTC
(19:11:03–20:11:03Beirut). The final end time and check results are recorded in
SESSION.json. Branch Maskable-PPO, published documentation base6bd7f71,
accepted simulator source938b9f8 /2026-11-10.f34. No training authorized.

## Plain-language progress

- Replaced what the model sees, so it receives the agreed game view rather than
  internal simulator answers. Traffic movement comes from successive visible
  positions, not hidden speed or waiting counters.
- Separated the manager's decisions from the executor's decisions while keeping
  one shared understanding of the board. The manager chooses focus; the executor
  still supplies every individual connection and may work outside that focus.
- Replaced the draft action format with the agreed context-dependent tokens.
  Cancellation keeps the current focus; returning to the manager is a separate
  choice. Legal but unhelpful edits remain available.
- Matched Stage1 action availability to the native simulator and checked moving
  traffic, deletion/refunds, repeated edits and all eight directions. Unsupported
  later-stage terrain/tools are rejected explicitly, not guessed.
- Added replay recording and verification for every choice and focus change.
  One complete scripted180-second example scores11trips and replays exactly.
  This is a test fixture, not a learned-model result.
- Added frozen collection and credit bookkeeping, including partial selections
  and interrupted games. This records information for a future PPO updater; it
  does not update weights or establish that the model can learn the task.
- Added evaluation records and best/worst/nearest-average replay selection.
  Stalls/errors remain visible; interrupted cohorts cannot pass.
- Extended the speed test to batched inference plus parallel simulators. Cloud
  runs only check that the tool works; actual Ryzen/RTX tuning remains to do.

## What is still unfinished

No PPO optimizer/update loop has been connected or run. The clipped PPO loss terms have analytical checks, including clipping the manager's joint conditional probability ratio once; no weights are updated. The reopened per-level
trace decay/decision-unit choice remains explicit rather than being silently
reset to the old.95. The GAE helper requires both settings as arguments; tests
exercise alternatives without selecting a training default. Full-game weekly
choices, water/bridge/roundabout/motorway legality and a graphical focus replay
viewer remain later work. Stage1 does not have those unavailable resources.

Changes remain in the isolated cloud checkout. They are uncommitted/unpushed and
have not modified the Linux PC or the original Windows worktree. No learned
weights are produced. Save/reload checks use temporary untrained parameters and
remove them after verification. No old training scripts were launched.

## Technical implementation and reasons

### Visible inputs

`visible_observation.py` implements the published81x30x50 grid,54globals and
1500x6motorway records. Two focus planes and8role/phase/option values are explicit
hierarchy additions. All spatial inputs are gated before aggregation. Signed
heading/velocity/displacement use bounded[-1,1]features; other categorical and
bounded counts retain their specified encodings. Unknown visible enum values,
nonfinite values, mismatched shapes and capacity overflow fail visibly.

History uses four distinct-time frames. Paused edits neither duplicate frames
nor invent motion; ID matching is only for observed displacement, never an ID
feature. The history-valid flag denotes availability of an earlier distinct-time
observation for motion estimation. Untracked cars have no invented velocity or
stopped estimate; means use tracked cars. Hidden routes/reservations/raw speed,
wait/acceleration/future demand/RNG/score/continuous overcrowding timers do not
enter model inputs. The host exports only the viewer's visible-car and warning
presence bits. Source viewer renders retiring motorway pairs; visible pairs are
retained, while a hidden opposite endpoint is not exposed.

### Action semantics and masks

`ConnectionPractice` now uses1501context-dependent tokens. Root controls preserve
the published ten-control ordering, with root10for early handoff. Coordinate
stages use0..1499and CANCEL1500; directions use0..7. The same1500token means NONE
for optional secondary focus. Stage1 resources make only wait, adjacent drawing,
erase, native tile removal and handoff available. There are no extra standalone
road/driveway root aliases. Native DrawRoad can perform ordinary driveway turning.

`PracticeLegality.cs` contains explicit read-only acceptance predicates for the
clear-land Stage1 distribution. Prefixes require a legal completion. No distance,
color matching, connectivity, useful-action filter or focus bounds are used.
Native accepted no-ops remain valid. Native partial-effect DrawRoad acceptance
is preserved: legal creation of an isolated tile need not establish a useful
link. The scope guard rejects applying these validators to water, rail, circles,
motorways, signals or non-road stocks. They are not claimed as full-game masks.
Queries do not change gameplay state or RNG; ordinary derived memoization caches
may populate. Tests compare acceptance against fresh native worlds, not the
predicate's own implementation, and check observable purity.

Mask caches are keyed by reset generation, network version, stocks, offers and
ending flags, with operand-specific direction caches. Native removal/retirement
updates its version; cache reuse across unchanged paused state avoids repeated
IPC without using a strategic shortcut. Native rejection of a masked-valid
request is fatal and requires reset, never a reward penalty/forced wait.

### Model and collection

The shared encoder restores the published32/64/64CNN,4x7pool,256grid projection,
64global features and masked mean/max motorway pooling. Focus adds two planes;
8context values join the shared fusion. Distinct manager/executor actor and
value MLPs use256→128heads with prescribed orthogonal initialization gains.
Total parameters:1,162,876. This is a reconciled engineering baseline, not a
measured optimum. There is no pretrained or planner initialization.

`hierarchy_rollout.py` collects bounded inference data under a fixed policy
fingerprint/version, storing masks, log probabilities, values, roles, focus,
score and exact ticks. It verifies reward telescoping and unchanged parameters.
Primary and conditional secondary selections are retained separately; their
joint behavior log probability is summed. Manager intervals aggregate the same
executor score stream, without adding a second environmental reward. Partial
selections/options survive buffer boundaries, and policy-version changes inside
a focus are rejected. Operational interruptions bootstrap the still-live role
context; real task endings do not. No loss/backward/optimizer step runs in the collector.

Gamma remains1. The generic GAE helper requires explicit lambda and trace units
(policy tokens, simulation ticks or simulation seconds), and distinguishes true
termination from trace cuts. Synthetic tests verify delayed reward, zero-duration
options, partial collections and interruption bootstrap. This is not yet a
complete two-level PPO objective/updater or evidence that any lambda is best.

The separate `hierarchy_objective.py` helper checks standard clipped surrogate,
unclipped value MSE, entropy and KL terms. It does not choose level weighting or
a joint manager entropy approximation; an explicit checked entropy estimate is
required. Analytic tests confirm positive/negative advantage clipping and joint
manager ratio handling, without constructing or updating a policy.

### Endings and evaluation

4096tokens without positive simulated-time advance is an operational truncation;
manager selection, cancellation and handoff tokens count too. Only actual game
time advance resets it. The finite180-second task horizon terminates, including
a fractional final wait. Native game-over is a valid natural ending, not an IPC
failure. The exact approved gate is a per-episode3-trip floor on at least90of100
fixed validation layouts. We removed the draft's extra survival-to180scondition:
a naturally ended game with>=3trips qualifies, while an operational interruption
does not. This follows the approved score criterion, rather than adding a new
survival objective. The ending reason remains visible for review.

Evaluation preserves every replay in a new directory, freezes weight identity,
never retries failed cases, and saves partial evidence on errors. Best/worst and
nearest-to-arithmetic-mean games come from that same cohort with stable seed tie
breaks. If interrupted, selections are provisional and use all-attempt scores.
Passing this numerical gate alone does not automatically promote a curriculum
stage or substitute for the user's replay review.

### Replay and benchmark limits

Replay stores policy tokens, readable action meanings, focus, score, clock,
endings and visible-input hashes, plus source/build/protocol identity. Verification
checks every transition. It is headless verification, not a Unity/video viewer.
Build/source mismatch fails rather than silently accepting a replay on another
engine; cross-machine rebuilds are not promised bit-identical.

The benchmark offers scripted environment-only timing, batched fixed-observation
inference, and optional coupled batched-policy/parallel-host timing. It warms up,
records transferred-input cost, excludes simulator startup for coupled cases,
uses identical initial weights across devices, verifies unchanged weights and
refuses overwriting an existing measurement file. These are inference tests,
not training or skill measurements. Cloud smoke runs overlapped verification
workloads and cannot rank configurations for the target PC.

## Evidence

- `stage1-feasibility.json`:100scripted validation layouts; all meet the native
  timing target,10–13trips by180s. This is not a model gate pass.
- `scripted-replay.json`: one full labelled scripted example;552tokens,11trips,
  180s, exact replay verified for the source/build recorded in its identity.
- `python-verification.txt`: explicitly selected Python checks; old tests that
  call learning were excluded. Final counts/status recorded in SESSION.json.
- `cloud-infrastructure-smoke.json`, `cloud-coupled-smoke.json`: CPU cloud-only
  inference/IPC smoke evidence, not Ryzen/RTX tuning evidence.
- Native core99suitesPASS; Stage1 differential legality1116actionsPASS,
  including100live-traffic cases and all eight directions/repeated connections.
  Release and Debug builds succeeded with0warnings/0errors.

Calculated observation payload is534,248bytes per token, before masks/Python/
rollout bookkeeping. A2048-token float32 observation buffer alone is about1.02GiB;
this is a calculation, not measured training peak. No learner buffer or optimizer
state was allocated for a training run. Benchmark resident usage is inference
only; Linux GPU/worker/batch selection remains unmeasured.

## Linux verification after source transfer

The source patch is based on the published Maskable-PPO6bd7f71revision. It has
been checked against a clean checkout. Preserve any local notes; apply-check
must succeed before applying. This does not publish the implementation or move
it automatically onto the target PC.

With the project virtual environment active:

```bash
bash training/verify_practice.sh
python training/benchmark_practice.py --workers 1 2 4 8 --coupled-rounds 100 \
  --output output/benchmarks/practice-inference-01.json
```

Both commands perform no learning. The verification runner explicitly lists
allowed checks rather than discovering older tests that perform training. The
benchmark compares CPU/GPU where available; choose new filenames to preserve
prior measurements. Read output before selecting a configuration. The actual
PPO update step and training runtime remain unmeasured/unconnected.

Evaluation requires an explicit positive finite wall-time budget. Expiry preserves
partial evidence and invalidates the cohort; it never creates a scored loss.
Budget checks occur between operations; an outstanding native IPC operation still
has its own30-second transport timeout. Seven evaluation/report tests pass,
including deterministic budget-expiry injection.

Initial test iterations caught a duplicate-key bug in a synthetic car fixture
and an overly strict head-routing comparison across different batch sizes
(float32roundoff around1.7e-10). The fixture was corrected and the routing
reference now uses the same batch shape; no tolerance was used to hide a policy
difference. Final checks pass. A root-level inspection command initially lacked
PYTHONPATH; it was rerun correctly. These were test/tooling issues, not learned
model outcomes.

Transfer validation: patch applied on a clean6bd7f71worktree; fresh Release build
passed with0warnings/errors and all9visible-observation checks passed there.
Archive review/specification JSON/workbook snapshots remain untouched.
