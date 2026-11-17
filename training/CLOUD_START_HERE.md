# Start here in the cloud chat

17 November 2026. This is a portable context guide, not a runnable training configuration or a substitute for reading the detailed decisions.

## Why this file exists

The user moved from a long local design chat to a cloud chat and feels the context was lost. Repository documents carry the decisions; do not assume the cloud chat has the full conversation. The root AGENTS.md previously still named the old `mohammad` branch; corrected for this restart. No complete transcript or private attachments are published here.

## First actions

1. Inspect the actual checkout, branch, working changes and any progress already made in this cloud chat. Preserve it. Base restart work on the latest `origin/Maskable-PPO`, not `main` or the legacy training branch. Refresh safely if this environment was created before the documentation publication; do not reset or overwrite existing work to do so.
2. Read [current decisions](../docs/training/DECISIONS.md), [handoff](HANDOFF.md), [short overview](PLAN.md), [hierarchy adoption and rationale](../docs/training/hierarchy-proposal-2026-11-16/README.md), and [curriculum approvals](../docs/training/curriculum-design-2026-11-16/README.md).
3. Explain the approved design and the next concrete action briefly to the user. Identify specific inconsistencies or missing evidence, not a new blanket approval queue. Read linked exact specifications/JSON when implementing a particular interface or parameter.

## The user's intended project

Train fresh weights with Maskable PPO to compete with Mohammad at the game, then assess further progress. Existing legacy imitation/training code and weights are not the new approved pipeline. The simulator source baseline is `938b9f80e67ca5341920a10e9e671164a474fc38`, version `2026-11-10.f34`. No physics change is implied by implementing a new controller.

### Strict construction and reward rules

- No engineering-generated construction routes, candidate-route menu, planner-selected road paths or automatic route completion.
- Model chooses every neighboring road/bridge connection, including legal diagonals. Ordinary vehicle routing and native motorway geometry remain simulator mechanisms.
- Edits happen paused, with a fresh observation after each. Multiple edits are allowed; waiting advances one simulated second, stopping early for native weekly/game-over events.
- Masks enforce physical game legality only. Do not remove legal choices because they look unproductive or because they are outside the manager focus.
- Game score is the only reward. No connection, goal-completion, wait, survival or congestion bonuses/penalties. Human-visible structured observations exclude hidden future/RNG answers.

### Adopted hierarchy

Manager chooses a primary board location and optional secondary location. Executor gets those plus the full board and selects actual primitive tools/operands/edits/waits. Manager does not choose a generated route. Executor may edit anywhere physically legal. Provisional focus review after eight completed edits or one wait; early handoff allowed, same focus may be reselected, native events interrupt. Tool/operand selection is not a third strategic agent. Agent owns evidence-based justification, diagnosis and revision of this recommendation. Exact PPO rollout/return accounting must be designed for the hierarchy, not assumed to work by nesting two stock `.learn()` calls.

### Adopted curriculum and first gate

Progression: basic connections → construction challenges → shared networks → growing cities → full games. First stage: one matching house/destination with short clear land gap, varied placement/orientation. Model builds and waits for actual scored trips. Approved first gate:180simulated seconds per episode; at least90of100held-out layouts each complete at least3scored trips, using a frozen checkpoint. First verify native trip timing can support the gate. No extra passing reward or generated route. Exact inventory/event/layout generation details still need reconciliation/specification.

### Previous decisions are not blank

Observation contents/encoding, architecture, PPO settings, delayed credit, evaluation and replay review were already discussed or reviewed. The earlier [full v1 specification](../docs/training/maskable-ppo-spec-v1-2026-11-16/SPECIFICATION.md) and [dated decision JSON](../docs/training/hierarchy-design-2026-11-16/current_decisions.json) preserve exact choices/reasons. They contain superseded no-hierarchy/no-curriculum and device assumptions. Keep compatible prior choices; identify and justify only necessary changes for the adopted manager/executor and curriculum. Do not mistake the old flat900702parameter count/config for a complete current hierarchy. Review, approval, implementation and measured success are different states.

## Last confirmed real-computer setup

As of the local handoff: user reported30GBfree on the Linux training PC and successful clone to `~/mini_motorways`; no new dependency installation, new hierarchical trainer implementation or training result was confirmed in that chat. Inspect newer cloud/user work rather than overwriting it with this older state.

Training PC evidence: Ubuntu24.04.4, Ryzen9 3950X/16physical cores/32threads, nominal32GiBRAM, RTX2080Ti11264MiB. Python3.12.3/Git2.43.0 available; active interpreter originally lacked torch/Gymnasium/SB3/Contrib, and dotnet was not on PATH. User runs commands there manually; a cloud shell is a different computer. Do not claim a cloud install or benchmark has configured/measured the Alienware.

The [storage calculation](../docs/training/linux-preflight-2026-11-16/STORAGE_BUDGET.md) recommends25GiB(~27GB), rounded request30GB, from candidate GPU archive payload/download sizes plus explicit run/system allowances.50GBwas comfortable, not minimum. Sizing snapshots are not approved installation locks or GPU validation. Check compatibility and peak placement before using the space. Windows `.venv`, scratch and outputs are not transferred wholesale.

Alternative Windows laptop was only partially inventoried, not selected as replacement. Roundabout fidelity follow-up belongs to another person; no roundabout patch in this task.

## Communication and records

Use short, plain explanations. One clear next step beats many repeated decisions. Agent handles engineering/reconciliation and documents changes; bring user actual material choices, not questions already answered. Maintain experiment history, current status and design decisions. No weights/binaries/private game footage/secrets committed. No long training run merely because code/setup is ready.

If context is missing, read the detailed records and state precisely what is missing. Do not invent rationale or claim measured performance. The research supports possible hierarchical structure, not proof this design learns human-level play.
