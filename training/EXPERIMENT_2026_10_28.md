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

## Prepared spatial residual hypothesis

Early pilot logs show about 89% of draws make no network change. An additional
opt-in `spatial-residual` architecture is prepared, to be assessed separately
after the initial input-only comparison. It adds a shared per-tile convolutional
residual to the legacy coordinate logits, retaining the old global tool/critic
branches. It sees only the supplied grid/globals, normalized coordinates,
relative selected-point coordinates, selected parcel kind and same-color relation
to the selected parcel. Those are deterministic transformations of current
inputs, not routed suggestions or demonstrations. Its final residual layer is
zero initialized, so copying the old weights preserves the starting policy.

This tests shared spatial scoring instead of unrelated global coordinate logits.
It is a different architecture, not evidence that two extra channels alone help.
Tests verified identical initial masked probabilities, actual gradient updates
to the residual head during a disposable 32-selection smoke learner, and exact
deterministic predictions after saving/reloading that disposable model. The
smoke update was explicitly authorized within the three-hour experiment and
does not modify any production checkpoint. Further learning results are pending.

## Pilot input-only results

Both two-worker pilots completed exactly 65,536 selections, starting from the
same stopped multi-seed policy with fresh optimizers, random seeds 1000-1099
and the same shaping. Control took 452.4 learner seconds, 129 games, best 34;
52-channel input pilot took 460.7 seconds, 126 games, best 33. Development
sampled scores were control 2/14/1/0/0 versus input pilot 9/0/4/10/0;
deterministic scores were control 0/0/0/0/0 versus input pilot 0/0/2/5/0.
This favors the inputs relative to this control, but the starting deterministic
mean was 2.0, higher than either final mean (0.0/1.4). Do not claim an absolute
generalization improvement. Periodic results and exact source are saved per run.

## Productive-stroke mask hypothesis

Diagnostics found roughly 89% of early pilot draw commands had no physical
network effect. Prepared an optional `productive` draw mask: a read-only core
probe excludes a target only when it proves the complete normal stroke cannot
change roads, connections or a driveway direction. True means "may change",
not "useful", reachable or even guaranteed legal. It never supplies routes.
Wait remains available; every ordinary tool remains exposed. Provably empty
start choices are cached/excluded until topology, inventory or playable bounds
change. The probe is conservative around potentially buildable tiles and rail
restrictions. Original construction rules are untouched; this changes the
agent's action interface and is reported as a separate intervention.

The query has a lightweight headless response and no simulation ticks. It is
tested against actual stroke effects and for read-only behavior. A versioned
host build under `tmp/headless-productivity` avoids replacing the DLL used by
the already-running spatial pilot. Frozen-policy deterministic development
scores with the initial version of the mask were 2/0/6/6/0, mean 2.8, versus
the original unmasked 0/2/4/4/0, mean 2.0. All sampled draw commands in that
five-seed masked evaluation had physical changes. This is a mask-only inference
effect, not learning. The cache improvement and any subsequent learning must
be evaluated separately. No final test seeds have been inspected.

## Further pilot outcomes and informed initialization

The spatial-residual pilot hit its 18-minute time ceiling at 63,490 selections
(rather than 65,536), with best training score 39. Sampled development scores
were 37/0/0/0/0, deterministic scores all zero. It did not provide convincing
generalization. The productive-mask/input pilot completed 65,536 selections in
582.9 seconds; sampled scores 12/4/0/12/0, deterministic 0/0/0/6/0. These are
weak and inconsistent, not evidence that another unchanged run will solve it.

Prepared a distinct `informed-spatial` initialization to address unproductive
exploration. It uses the same current 52-channel observation and normal commands,
but intentionally changes the starting action distribution: suppress the old
independent coordinate logits; favor current driveway outside points for houses
lacking a route or matching an unsupplied destination; favor same-color current
destination driveway outside points at the second selection; prefer shorter
direct endpoint distances, waiting when no such source remains, and choosing
an offered upgrade. A shared learned spatial residual can adjust cell scores.
There is no path computation, routed proposal, stock grant, future data or
demonstration dataset. The goal prior strength starts at 6 and is trainable;
wait/upgrade logit biases are explicitly 8/10. All ordinary tools remain exposed.

This is a hand-designed action prior, not a zero-behavior-change migration or
learning achievement. Its frozen initial checkpoint must be evaluated alongside
trained checkpoints; improvement over the old agent alone would not demonstrate
learning. Tests verify that it initially favors visible source/target driveway
points and that saved/reloaded predictions agree. The earlier zero-residual
architecture and legacy default retain their original starting behavior.

The continuing run uses a fresh directory, four workers, mixed seeds, periodic
development evaluation and a stop-file mechanism for graceful early completion.
The best developmental candidate can be the frozen initial informed policy if
optimization does not improve it. No test seed 3000-3009 has yet been inspected.
