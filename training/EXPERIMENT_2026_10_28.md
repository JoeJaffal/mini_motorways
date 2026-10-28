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

## Credit-window comparison

The frozen informed policy scored 0/0/8/33/22 (mean 12.6) in deterministic
development evaluation; its separate initial sampled evaluation also averaged
12.6, with different per-seed scores. The first eight-minute validation averaged
10.0, so improvement from learning is not established.

Testing a joint longer-credit configuration from the exact same informed initial
checkpoint: aggregate rollout 1,024 (256 per worker), GAE lambda 0.99, gamma
still 0.999, all other rules/reward/priors fixed. The earlier control uses rollout
256 and lambda 0.95. These are two interacting credit-window changes, not a
single-factor ablation. A graceful stop-file guard targets roughly 65,536
selections for the already-running control; its logged stopping count may
overshoot by one rollout/poll interval. The new arm has an explicit 65,536
selection ceiling. Both use four workers, temporarily eight simulator processes
total; timings under shared load are not hardware speed benchmarks. The longer
arm is capped at 35 minutes and must fit inside the original three-hour window.

An independent visible-state greedy routing diagnostic (not a model, no optimizer
or demonstrations fed into training) scored 216/85/116 on development seeds
2000-2002 with a 1,200 simulated-second cap; all failed before that cap.
It used ordinary finite resources, upgrades and road strokes, with current
visible-state path planning. All three command recordings verified exactly in
the headless runtime. This is evidence that better construction is possible,
not a learned score or an optimal ceiling. The informed 110-trip training replay
also verified in the native player (532 commands, 531.35 seconds).

## Separate planner-aided goal policy

A new opt-in experiment chooses among current visible house/destination pairs;
a deterministic visible-state pathfinder executes each chosen connection using
ordinary road strokes and finite inventory. It can also wait up to five seconds
or select offered upgrades. Motorways, roundabouts, lights, demolition and manual
driveway edits are excluded from this restricted experiment. The original
all-tools policy and checkpoints remain available unchanged.

Candidate features contain current positions, colors, route costs, supply,
demand and congestion; global features include current inventory, clock and
current network statistics. A hand-designed initial scoring prior prefers
unsupplied destinations and inexpensive connections. Its frozen initial policy
is evaluated separately; any superiority over the primitive agent cannot by
itself be credited to learning. The learned policy shares weights across
candidate rows, with a separate critic. PPO uses gamma/lambda 0.99 per macro
decision and bounded connection-potential shaping. Macro decisions span variable
numbers of ordinary one-second commands; this is a distinct learning problem,
not a clean architecture-only ablation. Development seeds remain 2000-2004;
3000-3009 remain reserved for the final comparison.

Two checks passed: actual finite-stock connection/trip/replay equivalence, and
parameter updates plus exact save/reload predictions. Viewer labels distinguish
planner-aided replays and heuristic diagnostics from the primitive AI.

## Goal-agent numerical-scale comparison

At 44 PPO updates, the first goal run logged value loss about 3,226, explained
variance about 0.00037, and approximate KL about 1.2e-7. This motivates a separate
numerical-scale pilot, not a diagnosis proven by these metrics. The second arm
starts from the exact same frozen initial goal checkpoint, uses the same two
workers, learning rate, entropy, architecture, rollout, seeds and 25-minute cap,
but multiplies learning rewards by 0.01. Actual trip scores, observations,
actions and simulator rules are unchanged. Initial/final evaluation reports
unscaled trips. A paired real-host test checks identical observations/score and
scaled rewards through positive delivery. Scaling can change the value/policy
loss balance and entropy's effective optimization behavior; no learning benefit
is assumed. Shared CPU load means wall-limited arms may collect unequal samples.

## Verification record so far

The 42 shared simulator suites and ten five-map protocol checks passed. Python
checks passed: environment 7, rewards 6, workflow/replay 4, parallel 4,
shutdown 1, optional input/spatial migration 4, productive masks 1, and goal
adapter/update/reload/scaling 3. The first shutdown invocation incorrectly used
an unsupported --dotnet option; rerunning its correct standalone CLI passed.
A documentation patch with a mismatched context was rejected before applying;
the corrected patch succeeded. These command mistakes did not change training.

The rebuilt OriginalReference native player completed the simulator suites and
build successfully. A duplicate build invocation exited while the first project
build was active; the successful first build log is preserved separately.
Generated scenes/settings were restored. Exact native replay checks passed for
126 trips / 592.6 seconds / 593 commands (primitive) and 300 / 890.4 / 891
(planner-aided). The latter map capture visually shows the proper planner-aided
source label and verified final outcome. No gameplay rule was relaxed.

## Choice-only timing pilot

Frozen seed 2000 used 145 macro decisions, of which 109 had only waiting legal.
An opt-in `--skip-forced-wait` mode now folds those forced states into the
preceding decision. Every ordinary one-second command is still executed and
recorded; after each command it checks for a newly available route, upgrade or
termination. It never skips a state where the policy could choose another action.
The saved checkpoint records this timing mode; frozen evaluation restores it.
Legacy goal checkpoints retain the original five-second wait semantics.

A real-host test at a 180-second external cap produced identical exact ordinary
command histories and trip scores with/without collapsing forced waits, while
reducing neural decision count. This verifies the tested frozen behavior, not
all future policies. Potential shaping and PPO discount now operate between
choice points, so reward schema is explicitly `goal-trip-potential-gamma099-choice-v1`.
This is an action-duration/credit-assignment change, not merely a CPU optimization.
The new arm starts from the same initial checkpoint, uses reward scale .01 and
otherwise the same PPO configuration as the scaled arm. Its 25-minute ceiling
fits the original authorization; independent arms temporarily share six hosts.

## Final learning-rate pilot (development-only)

Actual checkpoint comparisons confirm nonzero changes to goal actor prior,
residual and tool-head weights as well as the critic. Thus unchanged deterministic
development scores are not explained by a critic-only optimizer bug. Changes to
actor logits have remained small relative to the informed prior. This motivates
one final higher-rate pilot, not a proven diagnosis: choice-only timing, reward
scale .01 and learning rate .001 instead of .0001, from the identical initial
weights/empty optimizer state. Other PPO settings remain fixed. It has a
25-minute cap. This will be the last tuning arm before final tests. No final-test
result will be used for another update, checkpoint selection or hyperparameter
change during this investigation.

The final goal comparison will use a frozen initial checkpoint with the same
decision timing as the selected trained candidate. Development ties prefer the
first listed candidate; operational selection includes the frozen initial policy.
Best training scores and selected development checkpoints remain separate.

## Final-test sampling and usability checks

Before opening final-test seeds, predeclared a secondary sampled-policy comparison:
one inference trajectory on each of seeds 3000-3009 for the selected trained goal
policy and its timing-matched frozen initial. Each game resets Torch RNG to
43 plus its scenario offset. The primary comparison remains deterministic and
checkpoint selection remains development-only. Neither test triggers retuning.

Fixed the generic evaluator to apply its requested RNG after SB3 loading (which
otherwise restores the model's seed), resetting per scenario. Earlier generic
reports in this session were deterministic, so their action histories are not
affected. Repeating sampled development seed 2000 at a 180-second cap gave
identical metrics and exact command histories; both scored 14. This is a
reproducibility check, not another training or final-test result.

Goal resume now inherits rate, numerical reward scale and decision timing unless
explicitly overridden. A four-worker resume smoke check inherited .01 scale and
choice-only timing, stopped after 1.63 seconds/eight decisions, changed no weights,
and reproduced 161 before/after on development seed 2000. It is excluded from
performance-arm summaries. Direct actor-only parameter checks passed; all four
main goal initial checkpoints have identical policy weights and empty optimizer
states, despite different timing/rate metadata.

Goal evaluation no longer duplicates whole command recordings inside metric rows
or the console RESULT line. The archive removes only duplicated episode_replay
keys from older JSON/JSONL/RESULT rows, records the original source SHA-256 and
transformation, and retains dedicated exact replay files byte-for-byte. A check
preserved every remaining metric and reduced a 1,274,560-byte summary to 12,278
bytes. Raw original local files are preserved. This is evidence compaction, not
score editing.
