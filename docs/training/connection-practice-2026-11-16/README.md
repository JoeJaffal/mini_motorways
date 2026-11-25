> **Publication update:** detailed decisions are now available at `6bd7f71`.
> Read [reconciliation](RECONCILIATION.md) for corrections and remaining gaps.
> This initial prototype report is historical where it describes unavailable
> records, legacy visible-state compliance, the10000token cap, or horizon
> truncation. The prototype must not be used for learning.

# Maskable-PPO restart: preparation without training

16 November 2026. Baseline `938b9f80e67ca5341920a10e9e671164a474fc38`,
simulator `2026-11-10.f34`. Work is isolated in branch `Maskable-PPO` in
`/workspace/mini_motorways-maskable-ppo`. No changes to the existing checkout.
No training/optimizer steps, checkpoints, commits or pushes in this work.

## Source and authorization

User approved a manager choosing primary/optional secondary focus, an executor
making every individual edit, multiple paused edits, explicit one-second waits,
score-only reward, and a connection-first curriculum. User explicitly requests
maximum useful training speed on the Linux PC, and **no training sessions now**.
The handoff was recovered from the earlier chat's saved file-change output;
Windows-local PLAN, detailed hierarchy/network/PPO decisions, and restart
workbooks are not in this remote branch. They have not been fully reconciled.
This document distinguishes implementation proposals from user approvals.

User-supplied Linux evidence: Ryzen 9 3950X / 32 GB / RTX 2080 Ti (11 GB), Ubuntu
24.04, Python 3.12.3. Latest storage output: 87 GiB available after user cleanup.
PyTorch 2.9.1+cu126 GPU calculation/gradients and MaskablePPO import passed;
Gymnasium 1.4.0, SB3/Contrib 2.9.2, NumPy 2.5.4 installed; pip check passed.
.NET 8 installed, Release/Debug builds passed; 99 simulator suites and seven
legacy integration checks passed after creating missing `tmp/`. These are
user-supplied results on the target PC, not this cloud workspace's measurements.

## Code reconciliation and implementation

The legacy `TrafficEnv` advances time after completed edits, permits arbitrarily
long strokes, and offers optional planner/shaping paths elsewhere. It cannot be
the new pipeline unchanged. Those historical runners remain historical.

New opt-in code:

- `PracticeScenario.cs`: empty-land OriginalReference world; one destination and
  matching house, no provided roads. Native demand, vehicles, scoring, failure,
  driveway geometry and connection-cost accounting are reused.
- `ConnectionPractice`: sequential manager-primary, manager-secondary, then
  executor tool/source/adjacent-target decisions. Focus never prunes edits.
  Reuses the legacy 50-channel visible board and 42 globals, with two focus
  planes and seven role/phase/option-progress values. No routes, future spawns,
  RNG internals or demand forecasts enter encoded policy observations.
- Native `wait`: at most 20 native 0.05-second ticks in one IPC exchange, stopping
  for native game-over, rejection or pending weekly choices. Native `erase` is
  exposed without altering its rules. Other protocol behavior is preserved.
- Paused edits, manager choices and handoffs yield zero reward and consume zero
  simulated time. Wait reward is exactly native completed-trip delta.
- Review after eight completed edit requests, one wait, or early handoff.
  Requests include rejected/partially accepted draws, preventing rejections from
  extending an option forever. No rejection penalty or automatic wait is added.
- A 10,000-selection operational cap prevents endless paused decisions in tests
  or evaluation. It invalidates gate evaluation; it is not a game loss/pass.
- `HierarchyPolicy` is an **untrained prototype**, shared feature extractor and
  role-conditioned masked actor/value outputs. Dimensions are engineering
  placeholders, not a claim to preserve the unavailable approved network spec.
- `evaluate_practice.py`: frozen-policy deterministic 100-layout gate, >=90 with
  >=3 trips each; native failures count as failures; operational interruptions
  invalidate the gate; simulator/protocol exceptions propagate. Never learns.

## Provisional Stage 1 distribution (engineering choices)

Duration 180 simulated seconds and >=90/100 layouts scoring >=3 trips are user
approved. The following concrete distribution is newly implemented and remains
provisional pending the older detailed records and review:

- Train destination top-left x=12..21; validation x=30..37. Both y=10..18.
  Destination positions are disjoint across splits, even if seed sets overlap.
- Four native destination layouts, three matching colors, eight initial house
  driveway orientations. House sits 3..6 tiles along the destination's outward
  driveway direction from its exterior tile, plus perpendicular offset -1..1.
- 20 road concrete units, all other inventory zero. Entire 50x30 board visible,
  clear land, no other buildings, city growth, weekly packages or destination
  upgrade events. The curriculum marker uses the existing custom-scenario event
  suppression; it does not change native demand rates or vehicle speed.
- Fixed validation seeds 20000..20099; generator uses seeded .NET System.Random.
  Train practice may use other seeds. This is a practice distribution, not the
  previously discussed full-game city/seed split or reserved final-city test.
- Available Stage 1 primitives: adjacent draw (including legal diagonals and
  native driveway turning), erase one edge, place/remove road, move driveway,
  wait, handoff. Non-road tools have no inventory/applicable terrain here.

A script-only witness in `test_connection_practice.py` verifies native timing.
It is never imported by the environment/policy/evaluator/benchmark, never
supplied as agent actions, and is not a trained-model gate result.

## Readiness gaps — do not launch historical trainers

This is preparatory implementation, not a complete hierarchical PPO trainer.

1. Reconcile the original Windows-local observation/network/PPO/evaluation
   records. Concrete settings here are provisional where those records are absent.
2. Conservative masks admit some native-rejected draw requests. They do not
   prune on strategy/focus. Exact draw legality and tool-availability masks still
   need work before treating this as the final physical mask implementation.
3. Decide and implement manager/executor rollout/credit. A naive fixed discount
   per selection would discount paused manager and endpoint decisions as elapsed
   time. No such default has been silently adopted; no collector/learn CLI exists.
4. Replay export for the new interleaved roles and zero-time edits is not the
   legacy fixed-tick replay schema and still needs its own implementation.
5. No actual Linux-PC speed tuning yet. No claim that GPU beats CPU, more workers
   improve learning, or this prototype is the fastest network.

## Verification and no-training benchmark

From repository root, with the virtual environment active:

```bash
mkdir -p tmp
dotnet build simulation/Headless -c Release
dotnet simulation/Headless/bin/Release/net8.0/TrafficHost.dll --self-test
python training/test_connection_practice.py --dotnet dotnet \
  --dll simulation/Headless/bin/Release/net8.0/TrafficHost.dll -v
```

Run the infrastructure benchmark on the Linux PC only after transferring these
changes. It never calls `learn`, backpropagation, or optimizer updates:

```bash
python training/benchmark_practice.py --workers 1 2 4 8 \
  --output output/benchmarks/practice-infrastructure.json
```

It compares scripted native waits and batched inference of an untrained policy.
Wait throughput includes process startup; inference includes NumPy/device
transfers and warmup is excluded. It does not time PPO updates or measure skill.
Repeat with different `--threads` and expand workers only where evidence helps.
There is no default claim that all 32 logical CPU threads should be used.

Cloud-only smoke results are retained in `cloud-smoke-benchmark.json` and must
not be used to select settings for the Ryzen/RTX machine. No GPU is available in
this execution workspace. `feasibility.json` records the scripted layout check,
not a frozen model passing the curriculum gate.

## Final cloud checks

Release/Debug builds: zero warnings/errors. Existing simulator core:99suitesPASS.
Existing Python adapter:7testsPASS. New practice/interface/policy tests:7PASS,
including100uniquevalidationlayouts scoring10–13trips at180s, exact trip-delta
reward/time-limit behavior, paused option review, operational interruption,
visible-only inputs and batched policy inference with unchanged state/empty
optimizer state. A final reset check confirms varied automatic episode seeds
and reproducibility after reseeding. No optimizer step or training performed.

Known original temporary-directory omission was handled with mkdir -p tmp.
A one-line follow-up restored the new schema label after legacy-base setup;
its focused hierarchy test passed. Tests establish behavior in this checkout,
not target-PC performance or a fully reconciled trainer.
