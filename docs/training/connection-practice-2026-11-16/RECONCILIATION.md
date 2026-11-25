# Published decisions reconciled — 16 November 2026

Retrieved and fast-forwarded `Maskable-PPO` to publication commit `6bd7f71`
(`4c0700d` adds the records). Preserved local uncommitted source and preparation
records; archived the earlier cloud handoff as `CLOUD_HANDOFF_BEFORE_SYNC.md`.
No training or optimizer step is authorized or performed. Prior claims that the
specification is inaccessible are superseded by this reconciliation.

## Authority and precedence

Start with [DECISIONS](../DECISIONS.md), then the adopted hierarchy and latest
curriculum approval. Preserve exact historical v1 settings where compatible.
The no-hierarchy/no-curriculum flat-policy sections and old hardware/device pins
are historical. Reviewed workbook rows are review evidence, not implementation.
Detailed numerical encoder/network settings are an existing baseline needing
specific hierarchy adaptations; they are not newly blank decisions. Gamma=1
remains the score-only undiscounted objective; lambda=.95 was explicitly reopened
and must not be silently restored as a settled hierarchy setting.

## Implementation audit

| Topic | Published baseline / later approval | Prototype and required action |
| --- | --- | --- |
| Reward | Raw trip delta only; gamma=1 | Trip-only environment passes timing tests. Carry gamma=1 to collector/returns. Manager aggregates the same score stream, never a second environment payout. |
| Observation | 81x30x50 grid, 54 globals, 1500x6 visible motorway table; four distinct-time traffic frames | Legacy 50/42 prototype is **not compliant**: it exposes raw overcrowding timer, vehicle speed/wait, reservations and score as an input. Replace it; do not train using the current encoder. Hidden-state perturbation test must cover all these fields, not just RNG/future spawns. |
| Shared representation | CNN32/64/64, pool4x7, projection256, global64, motorway pooled64, fuse256 | Draft tiny CNN is a smoke-test placeholder. Preserve the established widths and add focus/role inputs explicitly; recompute parameter and buffer budgets. |
| Hierarchy heads | Shared encoder; distinct manager/executor actor/value heads; dedicated weekly offer head | Current role-conditioned single actor/value is not the adopted separate-head design. Replace and test each role, including primary/secondary conditioning. |
| Actions | Discrete1501 context-dependent tokens; adjacent direction stages, CANCEL; native tools minus traffic lights/tunnels | Prototype1508 tokens and standalone-road/driveway controls differ. Reconcile to published token/control definitions plus hierarchy focus/handoff/weekly contexts; do not call the draft a finished policy interface. |
| Masks | Pure exact validators, no mutation/RNG change, no strategic pruning; masked-valid rejection fatal | Current conservative masks intentionally admit rejections. Finish native validation before collector rollout; preserve legal harmless no-ops, prefix existence and all eight legal directions. |
| Cadence | Eight completed edits or one wait, early handoff **between** completed actions; cancellation clears operands | Draft allows handoff in operand phases. Separate CANCEL from HANDOFF; preserve cadence and keep focus boundaries distinct from game endings. |
| Paused guard | 4096 tokens without positive game-time advance, observable, resets on time advance | Correct initial draft10000 total-episode cap to the published pause guard; no forced waits/reward penalties. |
| Horizon | Finite game task horizon terminates; external pause/operational interruptions truncate and bootstrap | Correct draft180-second time limit from truncation to termination; native failure remains terminal. No bootstrap at task horizon. |
| PPO | lr3e-4, clip.2, epochs4, batch128, KL.02, entropy.01, vf.5, grad.5, Adam eps1e-5; lambda reopened | Keep numerical baselines explicitly versioned. Select level-specific trace units/lambda deliberately; do not nest independent learn calls. |
| Hardware | New Ryzen/RTX target and measured compatible CUDA stack supersede old CPU-only development pins | Keep installed torch2.9.1+cu126 and verified Python3.12.3. Compare CPU/GPU/workers after correct implementation on target; old2-worker choice came from a smaller laptop. |
| Stage 1 | User-approved180s, >=90/100 each>=3trips | Scripted feasibility100/100 yields10–13trips; frozen policy has not passed. Current generator/inventory are explicitly provisional curriculum engineering choices, not physics changes. |
| Full-game split | LA/Beijing/Tokyo/DarEsSalaam; London reserved, exact manifest retained | Stage 1 distribution is additional, not replacement. Do not use London/final seeds for tuning or label Stage 1 scores full-game ability. |
| Replay | Versioned exact zero-time/adjacent edit/wait/weekly replay, plus focus annotations | Still required; current legacy replay assumptions are incompatible. Preserve stalls/errors and best/worst/nearest-mean from complete frozen cohorts. |

## Manager/executor collection contract, before implementation

Use one frozen behavior-policy version for each complete collection phase. Store
observations, syntactic/native masks, selected action, behavior log probability,
role-conditioned value, score delta, exact elapsed simulation ticks and boundary
kind for every executor decision. Preserve tool/operand tokens as decisions.

A manager focus is sequential primary and optional secondary. Store both masks
and conditional log probabilities (secondary conditioned on primary), their
selection contexts, and interval boundaries; never pretend two independently
sampled coordinates form one unconditional categorical action. Aggregate actual
executor trip deltas into that focus interval, preserving exact duration and
intervening transitions. Manager rewards are training bookkeeping over the same
stream, not a second score in environment metrics. Handoff/review is not done.

Gamma=1 preserves the undiscounted finite objective and zero-time edits do not
introduce reward discount. Explicitly select and record trace decay units and
lambda separately per level; the published .95/.99/1 discussion is not a command
to run a tuning grid. Duration-aware manager accounting must handle zero-duration
options. Native failure and finite horizon cut bootstrap; operational pause stall
bootstraps the still-live state, including manager focus/selection context.
Rollout-buffer cuts also bootstrap; they do not masquerade as game completion.

Tests must exercise synthetic delayed rewards, zero-time focus switches, variable
option durations, cuts mid-option, both endings and conditional manager
probabilities without launching learning. No collector/learn entry point should
be offered until exact mask, leakage, replay and credit checks pass.

## Next implementation order

1. Apply settled pause-guard/horizon semantics with focused non-training tests.
2. Replace legacy observations, reconcile1501token action contexts, and implement
   exact native legality; then restore shared encoder dimensions/separate heads.
3. Implement the explicit collector/return contract and replay provenance.
4. Re-run correctness tests and target-PC no-training speed measurements. Only a
   later explicit user instruction may authorize any training session.

Historical tests and smoke timings validate only the draft features they cover.
They do not establish conformance to the newly available full specification.

## Follow-up verification

Release build:0warnings/0errors. Six focused checks PASS: operational cap is not
a gate pass; positive-time-only reset of pause guard (including manager/handoff
cycles); final fractional-second wait stops at180; task horizon is terminal with
native trip-delta reward; batched untrained policy inference leaves parameters
and optimizer state unchanged; paused hierarchy/focus does not prune edits.
The unchanged100-layout generator/physics feasibility result remains historical
evidence; it was not rerun for this counter/ending update. No training ran.
