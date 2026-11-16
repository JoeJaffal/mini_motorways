# What we are doing

**Goal: teach a fresh model to play against Mohammad.**

## Already agreed

- The model chooses a focus, then makes the individual edits itself.
- No road planner, generated route menu or automatic road completion.
- It can make several edits while paused, then choose to wait.
- Only game score gives reward.
- We start with a small practice game, then increase difficulty.

These are design decisions. We have not built or trained this new model yet.

## NOW: Linux setup and implementation preparation

**Approved:** one house and one matching destination, separated by a short clear land gap. Change their positions between games. The model builds its own connection and waits for cars to complete scored trips.

**Approved starting rule:** 3 simulated minutes per game; pass when at least 90 of 100 held-out layouts each produce at least 3 scored trips. Paused edits consume no simulated time. First verify that native trip timing makes this achievable. These are evaluation criteria, not extra rewards.

**Latest:** you report30GBfree and the Linux clone is done. Next we verify the checkout and set up an isolated software environment. I also reconcile existing settings with our hierarchy before implementing it. We do not repeat settled discussions or start training before the new pipeline exists. [New-chat handoff](HANDOFF.md).

## Computer setup alongside planning

Linux inventory is received: Ryzen 9 3950X, nominal 32GiB RAM, RTX 2080 Ti (11GiB). User now reports30GBfree; olderroot99%usage is historical. Verify intended workspace is writable. [Initial GPU storage budget](../docs/training/linux-preflight-2026-11-16/STORAGE_BUDGET.md) recommends25GiBfree under explicit allowances;50GB is comfortable, not a measured minimum. Initial capacity target is provisionally met; verify workspace location/access during setup. No benchmark or training yet.

## AFTER that

1. **Build it.** Implement the agreed practice game and model interface.
2. **Check it.** Make sure the rules, actions, score and replay work correctly.
3. **Try a small training run.** Agree on its budget first; review its results and replays together.
4. **Make practice harder.** Add water, more buildings and traffic, then full cities when ready.
5. **Play against you.** Compare scores under agreed conditions.

I handle the implementation, diagnostics and records. We review meaningful design choices and results together. Difficulty increases depend on evidence, not a promised training time.

This page is the overview to follow. [Detailed historical checklist](../docs/training/pipeline-checklist-2026-11-16/DETAILED_CHECKLIST.md) and [decision history](EXPERIMENT_HISTORY.md) are references, not extra tasks for you.
