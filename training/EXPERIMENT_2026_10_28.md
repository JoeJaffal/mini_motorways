# Authorized three-hour investigation

The user authorized autonomous improvements and training for the next three
hours, starting 28 October 2026 at 10:40 UTC (Asia/Beirut local time applies).
Existing checkpoints and historical reports must remain intact. This is a
bounded experiment, not authorization for recurring training afterward.

## Predeclared protocol

1. Add explicit current connectivity inputs without a planner or rule changes.
   Channel 50 marks houses without a usable same-color round trip. Channel 51
   marks destination footprints without any connected same-color supply.
   Missing-supply features are binary, not estimates of sufficient throughput.
2. Keep all tools, masks, trip-plus-potential reward and gameplay timing fixed.
   Add counts of draw commands changing the actual network, no-op draw commands
   and distinct ordered endpoint pairs, measured immediately after the command.
3. Introduce input schema `full-tools-staged-grid-connectivity-v2`, with 52 map
   channels and 42 globals. Legacy mode remains 50 channels by default. The new
   model has 450,898 parameters (288 additional first-convolution weights).
4. Warm-start from `multi-seed-shaped-01/final.zip`. Zero-fill added channel
   weights, copying all other weights. Check initial masked probabilities match
   the old model. Reset optimizer explicitly; compare against a control with
   the same old inputs, starting weights and fresh optimizer.
5. Pilot both arms at equal selection budgets, with two workers each (four
   total). Training seeds 1000-1099, random schedule, one episode per block.
   These are paired engineering pilots, not replicated statistical evidence.
6. Development evaluation seeds 2000-2004, deterministic; sampled final
   evaluations are also logged. Periodic validation uses no optimizer updates
   and restores the training Torch RNG state. Its time is included in learner
   wall budget, unlike initial/final evaluation. Save validation-best policy
   separately; best-game ranking remains actual training trips.
7. Choose the next candidate using development scores plus no-op/connection
   diagnostics. Reserve seeds 3000-3009 for a final report only, after selection.
   Do not select hyperparameters using those test results. Preserve baseline
   checkpoints for the same final comparison.
8. Stop within the three-hour wall window, including preparation/evaluation.
   Never promise improved convergence or the 1,000-trip target. If the small
   input change fails, investigate action coordination and report that result.

## Implementation checks

The added channels are derived from existing current-state dispatch routing,
including required return paths and ordinary retired-link exclusion. All matching
destinations are examined to mark supply, not just the first matching shop.
The actor gets no suggested endpoints or paths, future schedule or RNG data.
Tests check missing-supply features, visibility/future filtering, a real connected
replay, identical initial action probabilities after migration, zero new weights,
fresh optimizer state and rejection of implicit incompatible migration.

Commands and results will be appended after the pilots; source snapshots/configs
are retained per run. `--observation-mode connectivity --adapt-inputs` explicitly
opts into migration; `--reset-optimizer` supports the legacy-input control.
Existing PowerShell commands/old checkpoints remain legacy-input compatible.
