# Maskable PPO — our training checklist

Updated: 16 November 2026. This is the main place to check progress.

**Goal:** learn to play well enough to compete with Mohammad, then assess further progress.

**We are here: planning Stage 1.** The hierarchy and first-stage concept are approved. The new training pipeline has not been implemented or run.

Work branch: `Maskable-PPO`. Working folder: `C:/Users/moham/mini_motorways-maskable-ppo`. Baseline simulator: `938b9f8`, version `2026-11-10.f34`. The separate older checkout contains unfinished work and earlier decision documents; those are not automatically part of this branch.

Checked boxes mean the stated task is complete. Approval of a design does not mean its implementation is complete. Future tasks below are a work order, not claims of approved numerical settings or permission for long training runs.

## 1. Agree on the design — IN PROGRESS

- [x] Fresh model; aim to compete with a human.
- [x] Model chooses every neighboring road/bridge connection; no generated construction routes or route menu.
- [x] Paused edits with a new observation after each; explicit one-second wait, interrupted by native events.
- [x] Mask physically impossible actions; do not hide legal choices because they appear unhelpful.
- [x] Use game score as the only reward.
- [x] Adopt manager focus + executor actions. Initial review after eight completed edits or one wait; executor may hand control back earlier. Cadence is adjustable against evidence.
- [x] Adopt staged practice: basic connections → construction challenges → shared networks → growing cities → full games.
- [x] Approve Stage 1 concept: one matching house/destination, short clear land gap, varied layouts, actual scored trips, separate validation layouts.
- [x] Require best/worst/representative-average replay review.
- [ ] Bring earlier decision records and review marks onto this branch without overwriting history; identify superseded choices.
- [ ] Finalize Stage 1: layout generation, inventory, spawn/event setup, game-time horizon and validation cohort.
- [ ] Set the Stage 1 passing rule, operational limits and practice retention rules.
- [ ] Finish exact observations/actions, network and manager/executor PPO/credit settings; reconcile remaining reviewed/unreviewed workbook items.

**Next task:** define a concrete Stage 1 scenario and how we judge it. We have not chosen its episode length or passing threshold.

## 2. Build the training pipeline — NOT STARTED

- [ ] Implement Stage 1 scenario generation and fixed train/validation splits.
- [ ] Implement the agreed tools, operand selection and physical legality masks against the frozen simulator.
- [ ] Implement the manager/executor model and explicit handling of focus changes and weekly offers.
- [ ] Implement score-only reward accounting, correct episode endings/timeouts and two-level training credit.
- [ ] Save reproducible configurations, seeds, checkpoints, diagnostics and complete replays with focus overlays.

**Ready to leave this phase when:** a fresh policy can interact through the complete interface and a saved run can be replayed. This does not require that it plays well yet.

## 3. Verify correctness and measure speed — NOT STARTED

- [ ] Check that the model supplies every road connection and focus never generates construction.
- [ ] Check that legal edits remain available outside the focus and masks match native rules.
- [ ] Check that total emitted reward equals score change, including weekly/terminal transitions.
- [ ] Check paused edits, waits, manager handoffs and zero-time loops; distinguish operational truncation from losing the game.
- [ ] Check hierarchy rollout/value bookkeeping and reproducible replay.
- [ ] Inspect the Linux Alienware's actual GPU/VRAM and software; confirm CPU/device setup.
- [ ] Measure simulator + learner throughput before estimating runtime or selecting worker counts.

**Ready to leave this phase when:** correctness checks pass, unresolved failures are documented, and a bounded pilot has a concrete configuration and runtime estimate.

## 4. Run and review a bounded Stage 1 pilot — NOT STARTED

- [ ] Agree on the pilot budget and run configuration before starting training.
- [ ] Train from fresh weights; evaluate frozen checkpoints on the reserved validation layouts.
- [ ] Review best, worst and nearest-average runs from the same evaluation cohort.
- [ ] Inspect score, repeated service, stalls, focus switching and time advancement.
- [ ] Diagnose failures; change the design if evidence warrants it and record why.

**Ready to leave this phase when:** Stage 1 meets the agreed passing rule across validation evaluations and replay review. A single successful seed is insufficient. There is no result or training-duration prediction yet.

## 5. Expand practice gradually — NOT STARTED

- [ ] Specify and validate construction challenges, including water and resource pressure.
- [ ] Add multiple houses/destinations and shared infrastructure.
- [ ] Add growing cities and event/resource decisions.
- [ ] Retest earlier skills and revise the practice mixture if forgetting appears.
- [ ] Advance to full-game training only when the preceding agreed gates pass.

Each stage needs its own documented setup, validation rule and budget. These stage names are approved directions, not completed specifications.

## 6. Compare full-game play with a human — NOT STARTED

- [ ] Finalize city/seed splits and matched human/model play conditions.
- [ ] Select checkpoints using validation, keeping the final city separate from tuning.
- [ ] Run human and model evaluations; report score distributions and replay failures.
- [ ] Use the reserved final city for the final assessment; document if later tuning consumes that holdout.

**Outcome sought:** measured competitive play, with limitations and failed cases visible. No success guarantee or fixed time-to-human-performance is claimed.

## Where the detail lives

- [Hierarchy decision, rationale and original proposal](../hierarchy-proposal-2026-11-16/README.md)
- [Curriculum and Stage 1 decisions](../curriculum-design-2026-11-16/README.md)
- [Chronological history](../../../training/EXPERIMENT_HISTORY.md)
- [Current technical status](../../../training/CURRENT_STATUS.md)
- [Simulator/user design decisions](../../../simulation/Docs/DESIGN_DECISIONS.md)

Keep this checklist current after material changes. Store reasons and evidence in the linked records. New findings can change the plan; retain what changed and why. Roundabout fidelity follow-up belongs to the other person and is outside our current task. No commit or push of this checklist has been requested yet.
