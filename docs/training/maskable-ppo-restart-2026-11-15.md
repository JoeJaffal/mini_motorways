# Maskable PPO restart: decisions before training

Date: 15 November 2026. Planning only; no training authorized or started.

## Scope and evidence

**User decision:** restart training from scratch on a user-reported new branch called "maskable PPO"; first produce a list of matters to settle. The precise Git branch/ref and its location are not verified. This supersedes the older mohammad-only training preference for the intended new experiment, once its branch is located.

**Observed checkout:** `codex/driveway-physics`, HEAD `543d84e`, with pre-existing tracked changes and many untracked files. Local branch inventory contains codex/driveway-physics, main and mohammad; no matching new branch was listed. Another worktree owns mohammad. No branch was switched, created or fetched. This planning record is saved in the present checkout and will need carrying into the intended branch.

**Read-only source findings:** `training/train.py` already imports/constructs MaskablePPO. Its defaults include connectivity shaping, legacy observations and repeated seed blocks. `training/environment.py` exposes staged tool/cell actions and distinguishes selections from simulated-time advancement. These are historical implementation choices, not decisions adopted for the restart.

**Historical checks, not rerun:** latest inspected 11 November status reports simulator source 2026-11-11.3, unresolved fidelity/state issues and a reward fixture failure (actual 9 versus historical 12). See [current status](../../training/CURRENT_STATUS.md) and [demand-state report](demand-state-recovery-2026-11-11/README.md). These limit confidence in a frozen simulator baseline; they do not establish that every new experiment must wait for full commercial-game parity.

## Open decisions and proposed acceptance checklist

All proposals below are engineering recommendations, not adopted settings or measured new results.

1. **Define success.** Is the goal good simulator scores, learning road construction without a planner, unseen-map generalization, or eventual commercial-game transfer? Confirm whether the historical 1,000-trip Los Angeles target still applies. Set a first milestone smaller than the final research goal.
2. **Define "from scratch."** Fresh random policy and optimizer, with no old checkpoint or imitation initialization? Decide separately which tested simulator, environment and logging code to reuse. Preserve old experiments as historical evidence.
3. **Locate the experiment branch and freeze the simulator.** Confirm the exact branch/worktree and choose a source revision plus matching headless build and rules/city. Resolve or explicitly document the known reward check and relevant fidelity defects; do not mix simulator revisions within a comparison.
4. **Choose what one action means.** Individual tool/cell selections, a complete road segment, or selection among planner-generated routes? Decide allowed tools and staged-action state. This determines which parts of the problem are learned versus supplied by engineering.
5. **Specify masks.** Define legality for each action stage, inventory and upgrades; define waiting when nothing can be built. Proposal: mask illegal actions, while treating productive-only filters and route pruning as separate restrictions to disclose and evaluate. Check mask/host agreement, rejected commands and that every reachable state has a valid action.
6. **Specify observations.** List road/building geometry, colours, entrances, stocks, demand/queues, traffic, time and current selection state. Choose grid/other encoding and whether memory is needed. Separate player-visible information from simulator-only information; no future spawn leakage. Ensure selected actions and masks refer to the same state.
7. **Specify reward.** Completed trips alone or explicitly defined shaping? Write down scales, any costs/penalties and terminal behavior. Check that bonuses cannot be farmed through repeated edits or selections. Keep actual trips separate from training reward in reports.
8. **Define time and episode boundaries.** How much simulated time follows each action? Can the agent build while paused? Set game-over and external-cap handling, reset behavior and maximum selections. Choose discount/credit settings in light of decision frequency and delayed deliveries.
9. **Freeze training and evaluation splits.** Decide repeated versus varied training maps, any curriculum and its promotion gates. Reserve validation seeds for checkpoint selection and a separate untouched final test set. Distinguish map seeds from independent learner initialization seeds.
10. **Set the first model/configuration.** After actions/inputs are settled, record architecture, learning rate, rollout size, minibatch size, epochs, discount, GAE, clipping, entropy, normalization, dependency versions and device. Change one main factor per interpretable comparison; no inherited numeric defaults are adopted here.
11. **Define convincing evidence.** Compare with the fresh untrained policy, a legal-random policy and a fixed existing heuristic/planner baseline under the same simulator/tool/time contract. Report trips across seeds (mean/median/spread), survival/cap status, failure reasons and sampled versus deterministic policy behavior. Save typical and poor replays as well as the best. Decide advancement/stop criteria before examining results.
12. **Set compute, preflight and run limits.** Choose machine, workers, interaction and wall-time budgets, checkpoint cadence and bounded pilot scope. Measure simulator/observation/mask/inference/update costs on the chosen workload before estimating a longer run. Preflight reset/step/mask/reward/termination checks, then an explicitly scoped short learning pilot with finite losses, valid actions and verified save/reload/evaluation. A long run needs separate authorization.

## Proposed order

Settle goal, restart scope, simulator revision, actions, masks, observations, reward and time first (1-8). Then freeze splits, configuration, evaluation and compute plan (9-12). Only after these are concrete should implementation and a bounded pilot be proposed. No training command is supplied yet because the experiment contract and branch are unresolved.

## Record and limits

Checks performed: read repository instructions, training README/status/history and evidence archive procedure; inspect local branches/worktrees/HEAD and relevant trainer/environment source. No tests, benchmark, simulation episodes, dependency installs, source gameplay edits, weights, generated binaries, private research copies, commits or pushes. No new performance measurement or graph was produced. Future reports should use new archive destinations under docs/training and preserve historical archives; weights and generated players remain local-only.
