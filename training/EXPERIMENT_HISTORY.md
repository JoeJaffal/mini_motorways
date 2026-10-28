# Training decisions, changes and analysis

Updated 28 October 2026. This records the available conversation, source history,
PDF and saved run evidence. Dates are reporting dates unless an exact run date
is stated. It is not a verbatim chat transcript. Missing measurements are marked
unknown rather than reconstructed from a later checkpoint.

User decisions are distinguished from engineering choices and hypotheses.
Earlier simulator decisions remain in the
[project decision history](../simulation/Docs/DESIGN_DECISIONS.md). Current
behavior is summarized in [CURRENT_STATUS](CURRENT_STATUS.md); commands live in
the [quickstart](QUICKSTART.md). The evidence index is
[docs/training](../docs/training/README.md).

## T01 - Training objective and initial authorization

**User decision:** learn through trial and error, using structured simulator
data, OriginalReference, all ordinary tools, one city initially, and a provisional
1,000-trip goal. The user asked for a time estimate before approving training.
There was no existing learner. The user explicitly required branch `mohammad`;
`main` must remain the playground.

**Engineering choice:** Los Angeles first; CPU MaskablePPO with a compact
convolutional actor-critic. Masks narrow a large staged action space without
supplying a route planner. Hardware feasibility was established by measurements,
not a guarantee of convergence. The machine is an i7-1185G7, four cores/eight
logical processors, 32 GB RAM and integrated Iris Xe graphics. CPU PyTorch uses
two threads; no GPU training was configured.

**Boundary:** finite materials, ordinary failure/spawning, no stock grants,
demonstrations, debug reference networks, future schedule inputs or artificial
training cities. Trip delta is the implemented reward, not a user-specified
numerical weighting of survival/cost. Original and Custom objectives differ.

**Source:** `db5dba6`, `30ef7ab`; full contract in [README](README.md).

## T02 - Baseline implementation and validation

**Engineering choice:** 50 map channels, 42 globals, 450,610 trainable weights;
two convolution layers, 128 shared features, separate 64-unit actor/critic
heads; 1,513 action IDs. All tools are staged into at most four selections.
Completed commands advance 20 ticks/one simulated second; intermediate
selections have zero time/reward. Invalid commands still consume time.

PPO settings: learning rate 0.0003, gamma 0.999, GAE lambda 0.95, clip 0.2,
entropy coefficient 0.01, value coefficient 0.5, gradient norm cap 0.5,
rollout 256, minibatch 64, four epochs. Gamma applies per selection, so different
command lengths have different discount timing. PPO uses recent on-policy
rollouts, not a persistent experience replay buffer. The critic predicts future
reward; advantage compares outcomes with that estimate. Masks zero unavailable
action probabilities. PPO clipping limits the optimization objective, not every
possible policy change. Weights are learned numeric coefficients, not rules or
memorized games. Exact architecture and input tables are in the original report.

**Verification:** seven adapter tests, checkpoint reload, positive scripted
trip rewards, five-map replay/protocol checks and 37 then-current simulator
suites. No commercial-game parity claim. The external episode cap is 3,600
simulated seconds; ordinary failure is termination and the cap is truncation.
Protocol errors and rejected scenarios abort instead of being scored as games.

## T03 - First measured run and its PDF

**Run:** `first-full-tools`, revision `30ef7ab`, random sampling of seeds
1000-1099; 91 distinct seeds observed. Budget 65,536 selections or 29.5 minutes.
It hit the selection limit in 431.1 seconds, completed 242 games and 35,610
commands, and reached a best of seven trips. Only episodes 9, 17, 19 and 26
earned trips: respectively seed 1020/7, 1051/1, 1083/1 and 1064/1.
All later completed games scored zero. Mean score 0.0413; four reward-bearing
games (1.65%); all 242 games failed normally. Longest survival 210.05 seconds.

**Performance:** 152 selections/s, 82.6 commands/s; sampled Python working set
about 378 MB, not system peak. 256 rollout batches, 1,024 epochs and 4,096 Adam
steps were checked in the checkpoint. The final CSV row precedes the last four
epochs. A 512-selection smoke run took 4.3 seconds.

**Held-out evaluation:** seeds 2000-2002 all scored zero before and after
training, both stochastic and final deterministic evaluation. Failures occurred
at 139.55-140.75 seconds. A separate deterministic final-policy replay placed
25 single road tiles and then waited 116 times, exhausted concrete, made no
productive network and failed at 140.1 seconds. Road tiles do not automatically
connect every neighboring tile; road strokes establish explicit links.

**Analysis:** a working pipeline and changed parameters do not prove useful
learning. Rare rewards support an exploration/coordination concern but do not
isolate tool choice, representation, delayed credit or optimizer settings as the
single cause. Increasing the episode cap would not fix these early failures.
One million selections at that measured rate extrapolates to about 1h50m;
this is not an estimate of time to 1,000 trips.

**User request:** a detailed PDF with graphs and an accessible explanation.
The original report contains throughput, score/rolling-mean, survival,
parameter distribution, optimizer, behavior-map/material and evaluation
graphics. All 16 pages, graphs, explanations, hyperparameters, glossary and
limitations are now archived. Its recommendations were proposals, not work
already performed. See [PDF coverage](../docs/training/README.md) and
[first-run measurements](first-run.md). Source: `7c0c5ce` and archived evidence.

## T04 - Seed practice, best-game recording and live diagnostics

**User decisions:** save the best AI game and view its map in the actual native
viewer; practice one seed repeatedly before switching; print elapsed/remaining
time, per-seed performance and waiting data; implement first and teach the
launch command without starting training automatically.

**Engineering choice:** default blocks of 100 episodes per seed, then advance
through the configured seed range and cycle. Score/optimizer learning continues
across blocks. Later, the user explicitly chose a single seed: `SeedCount 1`
keeps seed 1000 indefinitely within the time/selection budget. `try 9/100`
describes the current block; reaching 100 does not stop the learner. A failed
episode restarts the city, not the model. Repeating seeds was a user hypothesis
for faster learning; no controlled seed-schedule comparison established that.

**Implementation:** best recordings globally/per seed; ranking is highest trips,
then longest survival, then fewest rejected actions. Replays contain ordinary
commands and expected score/time/acceptance, checked by the shared simulator.
Partial games can qualify at stop. The end-of-episode policy checkpoint can
differ from the policy that generated earlier commands, so exact command replay
is the authoritative saved game. The viewer supports play, step, speed,
restart, reload-best, pan/zoom and inspection. Construction is disabled in replay.

**Diagnostics:** periodic elapsed/ETA, selections/s, commands/s, game scores,
seed averages/recent scores/best, survival, waiting and action counts. Waiting
is an observation, not an added reward. A replay showing 0 trips at command 0
is at the beginning; recorded score labels the final result. Four trips really
was the best in `seed-test-01`; a small score is not a replay playback error.

**Rejected-seed clarification:** OriginalReference does not use Custom's
estimated-capacity rejection filter. Invalid original scenarios/protocol errors
abort; they are not silently discarded as poor scores. No documented list of
rejected Original training seeds or rationale was recovered. Custom's separate
filter is provisional and does not prove impossibility.

**Stopping:** learner time or selection budget, whichever first; setup/evaluation
are outside that timer. Ctrl+C should save and skip final evaluation. Reusing a
run directory is forbidden to protect results; resume uses a new name.
Source: `53b4251`, [quickstart](QUICKSTART.md).

## T05 - Early seed-1000 runs

These are separate runs with fresh counters, not one uninterrupted trajectory.
The archived configs record exact commands, starting weights and budgets.

| Run | Learner seconds | Selections | Games | Best | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| smoke-full-tools | 4.3 | 512 | 1 | 0 | Normal completion |
| first-full-tools | 431.1 | 65,536 | 242 | 7 | Selection limit |
| seed-test-01 | 171.5 | 31,216 | 100 | 4 | Interrupted |
| seed-1000-continued | 21.2 | 4,134 | 11 | 0 | Interrupted |
| seed-1000-three-hours | 1,156.0 | 197,120 | 451 | 49 | Interrupted |
| seed-1000-parallel-01 | Unknown final | No final summary | See archived logs | 73 recorded | Shutdown crash |
| seed-1000-parallel-02 | 14,400.7 | 2,271,492 | 4,549 | 73 | Time limit |

The name `three-hours` is a requested budget, not a claim it ran three hours.
The saved `parallel-01` config requested 480 minutes; that records configuration,
not measured duration or proof of who chose it. Its valid periodic checkpoint
was at 423,892 selections; that is not a final total. Earlier stopped runs
skipped final evaluation. Per-run counters must not be added without checking
checkpoint lineage and resetting semantics.

## T06 - Road density, reward and simulation concerns

**User questions:** why so many roads, why remove roads after trips, whether
roundabouts are accurate, and whether odd movement is a rendering/simulator
problem rather than weak model play.

**Analysis:** trip-only reward has no direct demolition or construction penalty.
Unproductive building/removal can persist under exploration or a poor policy.
That does not establish that reward shaping is the correct fix or authorize
changing game stock limits. Road/material correctness and policy quality are
separate questions. No reward change or reduced tool set has been implemented.

**Relevant earlier simulator work:** `34add43` attaches designated driveway
ends and enables house exit editing; `e69e619` allows roundabout conversion
while committed traffic clears; `0c59421` fixes over-retained crossing
reservations and aligns road/roundabout proportions. The lane radius is about
0.737 tiles; connectors remain approximate. See the
[traffic/scale investigation](../simulation/Reports/traffic-and-scale-investigation.md)
for the controlled seed-40-43 before/after table (45/54/57/55 to 70/56/65/78
trips) and the reduction in snapshot waits over 20 seconds from 72 to zero.
Those diagnostic runs used replenished stock/extended failure and are not
normal-play model scores. Rejected future-junction-lookahead experiments did
not resolve the waits and were discarded. Exact roundabout fidelity remains
unproven; no blanket claim that the game is correct is justified.

## T07 - Parallel games and throughput

**User decision:** try parallel games and supply instructions after implementation.
The user clarified that learning/experience collection speed was the concern,
not merely rendering speed.

**Engineering choice:** 1/2/4 independent .NET hosts with a thread-pool vector
wrapper in Python, shared-memory observation buffers and centrally batched
neural-network calls. This avoids an extra Python-process hop for roughly
300 KB observations. JSON processing still shares Python's GIL, so more workers
do not imply linear scaling. Four workers each collect 64 selections per
aggregate 256-selection rollout; PPO minibatch/epochs remain 64/four. Shorter
worker fragments may affect delayed credit. No gameplay speed cap of 0.8
games/s was deliberately configured; throughput depends on processing and
episode length. Longer-surviving games can reduce games/s while improving play.

**Measured benchmark:** two 12-second trials per worker count, order 1/2/4/4/2/1,
after warm-up, under load from another active training session. Means:

| Workers | Selections/s | Commands/s |
| --- | ---: | ---: |
| 1 | 106.5 | 60.3 |
| 2 | 123.4 | 70.3 |
| 4 | 125.4 | 74.9 |

About 17%/24% more commands with two/four workers than one in this short test.
This was not an idle-system ceiling, a convergence experiment or proof of
faster learning. Disposable benchmark clones performed real short optimizer
updates, without replacing production weights. Raw trials are archived.
Source: `6103fbb`, [benchmark protocol](QUICKSTART.md).

## T08 - Video-confirmed missing pavement

**Finding:** a driveway edit unlinks its old connection immediately, while
active vehicles keep lane snapshots/return routes. The viewer only drew live
connections, so cars appeared to drive across grass. This is a concrete
rendering mismatch independent of model competence.

**Diagnostic:** the 73-trip/479.8-second replay had 3,777 moving car-tick samples
using a missing connection, with 2,168 samples more than 0.205 tiles from the
then-drawn surface. These count car-ticks, not distinct vehicles or elapsed
seconds. A small off-surface sample without a missing connection also occurred;
the fix is not evidence that all curve/rendering approximations are solved.
The scratch diagnostic is local; counts are historical observations, not a
maintained test or a complete video ground-truth annotation.

**Engineering change:** a read-only query enumerates detached adjacent links
still required by committed trips. The viewer draws pale gray pavement until
those trips clear. It does not restore routing or change stock, reward, RNG or
weights. Network non-mutation/clearing tests and visible before/after captures
were checked. Original Windows player rebuilt. Old 73-trip replay still passes
headless/native verification with exactly 480 commands and 479.8 seconds.
Source: `e6119eb`; 40 simulator suites and training/protocol tests passed.

## T09 - Parallel Ctrl+C crash and recovery

**Observed error:** interruption killed worker hosts; shutdown waited on a failed
future before saving the final policy, then closing invalid pipes raised OSError
22. A later attempt reused `seed-1000-parallel-01` and raised FileExistsError.
The best replay survived; `final.zip` did not exist.

**Fix:** Windows hosts get separate process groups. Interrupt handling ignores
repeated Ctrl+C during saving, atomically saves `final.zip` first, then drains
workers and attempts replay cleanup with warnings on failure. Pending results
are collected per worker; closed-pipe errors do not block remaining cleanup.
An existing output directory now produces an actionable argument error.

**Recovery:** load-verified `parallel-01/latest.zip` at 423,892 selections. A
periodic save may miss roughly two minutes before a crash; recovery was not
lossless. Tests included dead-worker/replay-save failures and a four-worker
inference-only interrupt/save/reload with identical weights. No long training
was started to test shutdown. Source: `e6119eb`.

## T10 - Authorized four-hour run and conclusions

**User decision:** when implementation is done, launch four workers for four
hours in the open terminal. The run resumed `parallel-01/latest.zip` on seed
1000 with a fresh `parallel-02` name. Launch used a new visible PowerShell
window because the available Windows UI tool prohibited terminal automation;
the requested existing terminal was not reused. All four workers were verified.

**Measured result:** 4,549 games, 2,271,492 selections, 1,650,223 commands,
157.7 selections/s and 114.6 commands/s; normal four-hour time-limit stop,
saved final checkpoint/evaluation. The current run's best is 73 trips in
461.4 simulated seconds, different from the earlier 73-trip replay.

**Analysis:** first/last 100 mean scores 24.88/52.10; 7/75 games scored at least
50. Hourly means 31.97, 45.92, 52.64, 52.64 show improvement then a plateau.
Best score did not exceed the previous record. Held-out initial sampled scores
were 0/2/0, final sampled 3/0/0 and final deterministic 0/2/0 on seeds
2000/2001/2002. Three seeds are limited evidence, but do not support useful
transfer. The user asked whether it learned nothing: the supported answer is
better consistency on the practiced seed, no new record and poor transfer.
More unchanged training is not presently recommended. See
[current results and aggregation caveats](CURRENT_STATUS.md).

## T11 - Input limits and proposed next investigation

**Code-verified limits:** per-cell traffic aggregates omit individual vehicle
color, destination and route. No explicit house-to-matching-destination
reachability labels, recurrent state or history are fed into the policy.
Values clip at schema limits; aggregated entities lose detail. Future spawns,
RNG and out-of-bounds cells are withheld. London rail features are absent.

**Hypotheses, not changes/results:** missing connectivity features, a more
spatial action head, entropy/initialization changes, seed curriculum, delayed
credit and reward sparsity could contribute to the plateau. Instrument failure
cases before changing several factors at once. No new planner, shaping,
demonstration system or recurrent architecture has been adopted. The PDF's
proposed experiments are likewise not completed work.

## T12 - Documentation scope corrected

**User decision:** every update, decision, analysis and performance finding,
including the PDF, must be documented, not merely current commands/status.

**Implementation:** this chronological record; unchanged original PDF plus
searchable full text/figure images; small run evidence archived with hashes;
first-report rebuild source; cross-links to the older simulator decision
history; and a continuing documentation requirement in contributor/agent
instructions. The first PDF remains historically dated rather than silently
rewritten with newer results. No new training is part of this documentation work.

**Known evidence limits:** available chat and artifacts are the sources. There
is no complete machine-verifiable transcript of every past interaction,
unsaved exploratory command or lost pre-crash state. Unmeasured comparisons
and missing summaries stay unknown. Future records must preserve the concrete
decision, rationale, evidence, limits and superseding change as work happens.

## T13 - Publish the training branch to GitHub

The user could not find the branch on GitHub. Inspection confirmed `mohammad`
existed only locally and had no upstream tracking branch. Published it with
`git push -u origin mohammad` to `JoeJaffal/mini_motorways`; Git confirmed the
new remote branch and tracking configuration. `main` was not pushed or merged.
This publishes committed code, documentation and archived evidence, not ignored
local checkpoints or generated player builds. No pull request was created.

## T14 - Deliver an updated current-model PDF

The user requested the current PDF. Created a separate dated 12-page report
rather than replacing the historical first-model report. It explains the current
inputs/missing information, architecture, staged actions, MaskablePPO/reward,
parallel configuration, four-hour learning curve, held-out performance,
historical baseline, throughput benchmark, fixes, decisions and unresolved
hypotheses. New held-out and benchmark charts use archived measurements only.
No model was run, evaluated or trained to create the report. All 12 pages were
rendered and visually checked for layout; page count/text extraction and archived
copy integrity were checked. The source builder, figures, full searchable text
and dated PDF are tracked with the evidence index. The earlier 16-page report
remains unchanged. This delivery adds reporting, not a model change or improved
performance claim.

## T15 - Authorize and implement connection reward shaping

**User decision:** explicitly approved adding a carefully designed reward for
useful connections. This supersedes trip-only as the training CLI/helper
default; trip-only remains selectable. It does not authorize another long run.
No new policy input, planner, demonstration, stock change or memory was added.

**Engineering choice:** potential is 0.25 times houses with current same-color
outbound and return routes, capped at eight houses/two potential units. Each
selection receives gamma*next_potential - current_potential, including zero-time
intermediate selections; gamma 0.999 matches PPO. Failure has zero terminal
potential, while external caps bootstrap live potential. These settings are
initial engineering choices, not optimized learning hyperparameters. The form
follows Ng/Harada/Russell's original paper (linked in the specification), and
prevents positive discounted reconnect loops. It does not guarantee faster
learning for our partially observed approximate PPO.

**Implementation:** cached read-only diagnostic through actual dispatch routing,
optional headless output, versioned reward metadata/source snapshots, baseline
flag, separate trip/shaping totals and live console/status diagnostics. Best
games/evaluation still use actual trips. Monitor CSV `r` now means shaped return
in connectivity mode; `trips` remains game score. Old inputs remain compatible
with checkpoints, but the critic/optimizer must adapt to changed returns.

**Evidence:** 41 core suites and six reward tests pass, along with the existing
environment/workflow/parallel/shutdown checks. A fixed 462-command recording
produced identical observations/outcomes in baseline and shaped hosts: 73 trips
at 461.35 seconds. First positive shaping was +0.24975 at second 23, before any
trip. Peak connected count 12 was capped at two potential units. Discounted
shaping summed to about zero after failure. Undiscounted shaping totaled
-0.70775, yielding 72.29225 training reward versus 73 trips. This scripted
audit omits historical intermediate actor selections, which are tested
separately. No policy calls or optimizer updates were used. See the
[exact rule and limitations](REWARD_SHAPING.md) and
[archived audit](../docs/training/connectivity-reward-audit-2026-10-28.json).

**Next:** explicitly launched short trials, compared with matched trip-only
baselines using actual trips, held-out scores and throughput. Faster learning
remains unmeasured. The dated 12-page PDF predates this update and stays a
historical snapshot; current guides identify the new specification.

## T16 - Read-only check of the active multi-seed shaped run

The user asked whether the running model was learning. Inspected processes,
status, episode logs and optimizer CSV without stopping/changing training or
starting another evaluation. `multi-seed-shaped-01` was running four hosts with
connectivity shaping, one episode per seed, seeds 1000-1099, a user-launched
60-minute budget and the old `parallel-02/final.zip` warm start.

At the first-556-game snapshot, all 100 training seeds had been encountered.
First/last 100 mean scores were 5.04/4.16; overall mean 3.656, best 60. The latest
100 games used 17,057 draw commands, overwhelmingly more than other tools.
Optimizer update counters advanced from 45,677 to 50,029. The pipeline is active,
but these logs do not establish useful improvement. For 43 seeds appearing in
both cycles, seed-weighted means were 4.535/3.337; incomplete second-cycle worker
coverage and stochastic trajectories prevent treating this as a controlled
regression estimate. Final held-out results were not yet available.

The lower score distribution versus seed 1000 exposes poor transfer; it is not
alone evidence that multi-seed practice or shaping caused deterioration. Tool/
endpoint coordination is a hypothesis for investigation, not a diagnosed bug.
Recorded an [immutable interim snapshot](../docs/training/live-check-multi-seed-shaped-01-2026-10-28.json).
No code, hyperparameters, running process or checkpoint was changed. This is
an interim observation, not a completed run report or promise of convergence.

## T17 - Stopped multi-seed run and frozen-policy assessment

The user stopped training and asked what to do next. Confirmed no active learner
and a valid final checkpoint file. Final summary reports interruption after
1,721.5 seconds, 344,244 selections, 117,097 commands and 687 completed games,
best 60 trips. Last-100 mean was 2.58 versus first-100 5.04; these windows have
different seed mixes, so this alone is not a controlled policy comparison.
The final 100 games used 16,239 draw commands, still overwhelmingly dominant.

Performed a new read-only frozen-policy evaluation of this run's initial.zip
and final.zip on identical held-out seeds 2000-2004. Both used deterministic
masked actions, a 3,600-second cap, ordinary gameplay and trip-only evaluation.
Initial scores were 0/2/0/0/0 (mean 0.4); final scores 0/2/4/4/0 (mean 2.0).
All ten games ended in normal failure, not truncation. Parameters were compared
before/after inference and remained unchanged. This is limited evidence of
some unseen-seed improvement, not proof of robust generalization, useful high
scoring or an isolated benefit from shaping. There is only one training run
and five test seeds. Ctrl+C skipped the learner's normal final evaluation;
this separate assessment supplies the explicitly identified later measurement.

Saved [full outcomes, config and provenance](../docs/training/stopped-run-assessment-2026-10-28.json).
No optimizer updates, rule changes or new training were performed.

**Recommendation, not an approved/implemented change:** expose explicit
connectivity indicators for houses lacking same-color round trips and
destinations without connected supply; add endpoint diagnostics to understand
unproductive road strokes. Keep all ordinary tools/rules and preserve the
current checkpoint as a baseline. A new input schema needs an explicit
checkpoint adaptation strategy and a controlled short comparison; do not
silently load incompatible inputs or change several learning factors at once.
Another unchanged long run is not recommended from this evidence.

## T18 - Authorized three-hour autonomous improvement experiment

The user explicitly authorized improvements and training while away for three
hours. Implemented an opt-in 52-channel schema with unconnected-house and
unsupplied-destination indicators, retaining the 50-channel default and all
ordinary tools/rules. Explicit migration zero-fills the extra input weights and
preserves initial action probabilities, with a fresh optimizer. A matched
legacy-input/fresh-optimizer control is required. Added immediate network-change,
draw-no-op and endpoint-diversity counts. Periodic deterministic development
evaluation preserves Torch RNG and logs actual trips, with a validation-best
checkpoint. No final-test seed is used to choose a candidate.

See the [predeclared protocol and evolving results](EXPERIMENT_2026_10_28.md).
The additional inputs are an engineering hypothesis, not an established fix.

## T19 - Separate planner-aided goal-policy experiments

Within the same three-hour authorization, primitive pilots failed to establish
strong transfer. Current-state route planning was tested separately as a
heuristic diagnostic: 216/85/116 trips on development seeds 2000-2002, ordinary
finite materials, exact replays. These were not learned scores or demonstrations
fed to PPO. This motivated an opt-in restricted goal agent with shared candidate
scoring (10,334 parameters): choose a visible matching-color connection, wait or
upgrade; a router executes ordinary strokes. It excludes demolition, motorways,
lights, roundabouts and manual driveway edits. Original all-tools training remains.

Its engineered initial prior averaged 162.6 trips on development seeds 2000-2004
before training. Four bounded pilots compare original numerical scale, scale .01,
choice-only timing that collapses forced waits, and higher learning rate .001.
All four initial policy weights/empty optimizers match exactly. The timing pilot
was motivated by 109/145 forced-only calls on a frozen game; paired command
histories matched with/without collapsing at a 180-second cap. Discount/credit
semantics differ and are versioned. No improvement is assumed. Initial completed
arms retain identical greedy development scores despite actor/critic updates.

The [protocol](EXPERIMENT_2026_10_28.md) records settings, reasons, intermediate
results, checks, command corrections and final-test rules. [Goal guide](GOAL_AGENT.md)
explains restrictions, input features, reward, resume inheritance and commands.
Final test seeds remain untouched until checkpoint selection is frozen. Training
best scores are not checkpoint-selection scores and engineered assistance is not
attributed to learning. The final record will report the independent tests.

## T20 - Final independent assessment and report

The authorized study completed ten bounded training arms, preserving original
checkpoints and `main`. Primitive all-tools best was 126; the separate restricted
planner-aided variant recorded 356 (seed 1075, 971.65 seconds/972 commands), verified
exactly in headless and native runtimes. The higher-rate final model's development
mean fell to 128.0 despite that record. Goal development selection retained the
frozen initial policy on a tie; the first arm's early validation checkpoint was
the trained comparison. Selection/hash record preceded all final tests.

On ten fresh deterministic seeds, old primitive mean was 0.6, informed primitive
initial 23.4, trained primitive 20.7, goal initial 119.1, trained goal 125.7.
The last gain came from one map improving 56 to 122; nine tied. Secondary sampled
inference averaged 130.4 for both goal policies, with identical per-map scores.
No final-test result was used for retuning or reselection. Parameter updates are
verified, but robust learning, a shaping benefit and the 1,000-trip target are not
established. Engineered priors/router account for most improved starting play.

The [latest report](../docs/training/model-investigation-2026-10-28.pdf) preserves
the graphs, findings and limitations. [Evidence and integrity instructions](../docs/training/investigation-2026-10-28/README.md)
cover 312 source/metric/log/replay files plus report assets and hashes. Exact
replays remain byte-identical; duplicated command histories are removed only from
metric rows, with source hashes/transformations recorded. Unity device/licensing
identifiers are redacted from published logs; originals remain local. Code,
commands, current status and report are on `mohammad`. Weights/binaries remain
local. Historical PDFs stay historical. All learning/evaluation is stopped.

## T21 - Live candidate traffic correction (28 October 2026)

User requested more accurate traffic observations after inspecting the 356-trip
replay. Code inspection found candidate mean vehicle occupancy and maximum wait
were computed only when topology/inventory/bounds invalidated the path cache;
demand/overcrowding were already refreshed on cache hits. This could hide traffic
changes on unchanged roads. `GoalEnv._refresh` now updates all four dynamic values
on cache hits while retaining cached route geometry. Initial route construction
already reads current vehicles. No reward, simulator rule, router cost, action
space or input tensor shape changed. Existing weights load with the same layout,
but live inputs can change their actions; prior benchmark scores are historical.

Traffic remains a current visible-cell vehicle count averaged along a candidate
route, plus maximum vehicle waiting on that route; it is not lane-level flow or
travel-time prediction, and does not expose a full per-road map to this policy.
No performance improvement or learning benefit is claimed. A regression injects
two waiting vehicles, then removes them with topology/inventory unchanged,
checking occupancy, waiting, demand, overcrowding and unchanged cached geometry.
All five goal-agent tests passed (14.622 seconds), including replay, observation
contract, reward scaling, forced-wait equivalence and short parameter-update/save
checks. These bounded unit checks are not a new training experiment. Initial test
invocation failed because dotnet is not on PATH; rerun passed using the existing
`tmp/dotnet/dotnet.exe`. No long training or held-out performance evaluation ran.
Current status/input documentation updated; existing PDFs and evidence untouched.

## T22 - Optional congestion inputs and connected-route bypasses

User authorized implementing congestion information, alternatives for existing
connections, frozen comparisons and a training-ready command. Engineering change:
opt-in `--congestion-aware`, schema `visible-route-congestion-policy-v2`, 18,205
parameters. A live 4x30x50 visible traffic/wait/road/junction map and seven extra
candidate summaries expose current load. A CNN supplies tool/critic context;
route summaries feed candidate logits. A bounded current-state router may add
physical bypasses for already connected pairs; it needs observed waiting >=3s,
affordability and >=20% lower summed snapshot load than a conservative reference
route. Up to 64 bypass proposals occupy remaining slots after original goals.
Search refreshes every 15 simulated seconds or network/resource/bounds change;
dynamic observations refresh every decision. Ordinary road/bridge commands enforce
normal materials. Reward and simulator unchanged; no demolition, motorways or
forced vehicle rerouting. Vehicle routing uses simulator travel costs, so snapshot
load reduction does not guarantee vehicles use the bypass or traffic improves.

Old v1 weights remain usable only with v1 inputs. Resume explicitly rejects a
schema switch; saved v2 inputs are inferred by trainer and frozen evaluator.
The v1 live-input correction from T21 remains included. Fresh-model command,
controls, tensor semantics, assumptions and limits are in GOAL_AGENT/QUICKSTART;
current status and evidence index updated. Historical PDFs unchanged.

Measured frozen initial-policy development comparison, seeds 2000/2001/2002,
1200-second caps: v1 live 161/85/115; v2 without bypasses 161/85/115; v2 with
bypasses 79/209/82. Means 120.33/120.33/123.33; two maps worsened, one improved.
V2 selected 5/3/6 bypasses. Parameter hashes unchanged; v2 ablation weights match.
No reliable gain, learning benefit, or 1000-trip success claimed. No tuning or
checkpoint selection followed these results, and prior final-test maps untouched.

Eight goal checks pass (14.862s), including old behavior contracts, synthetic
fixed-network live traffic, v2 actor/CNN updates/save/reload and a finite-stock
bypass verified by exact replay. First new-grid fixture lacked vehicle `speed`;
fixed fixture and reran all eight. Four-worker startup (36 aggregate decisions,
159 commands, 2.136 learner seconds) saved normally; expected no PPO update before
full rollout. New-schema frozen evaluator smoke passed, weights unchanged.
These bounded checks do not start the proposed 30-minute training experiment.
Small measurements and protocol are archived in
[congestion v2 evidence](../docs/training/congestion-v2-2026-10-28/README.md).
Weights/replay runtime artifacts stay local, no long run active.

## T23 - User-started v2 run: live speed check

User started `congestion-v2-01` with four workers, 30 minutes, reward scale .01,
then asked why it is slower. Read-only snapshot at 326.7 learner wall seconds:
2564 macro decisions (7.8/s), 11833 ordinary commands (36.2/s), 14 completed
episodes (~0.043 games/s), best recorded training score 397. Four C# hosts were
active. `before.json` existed, so this snapshot was training rather than initial
evaluation; progress CSV showed 32 PPO updates at 2304 decisions. This establishes
execution and updates, not generalization or learning benefit. Metrics are live,
not a completed-run comparison, and differ from primitive selection rates.

Implementation explains extra work: v2 constructs live traffic grids, runs a CNN
and searches connected pairs for bypasses on cache invalidation/every 15 simulated
seconds. Python-heavy routing/encoding shares one interpreter's GIL across worker
threads, while C# hosts run concurrently; a slow worker also delays the vector
batch. These are identified overhead mechanisms, not measured profiler shares.
Longer-lived games also reduce games/second without necessarily reducing command
throughput. No artificial 0.8-games/s cap is set. No running code, checkpoint or
process was changed or stopped during this inspection. Profile/cache routing
and consider process-based Python workers before promising a speedup.

## T24 - Two completed user-started congestion runs

User asked to assess two sessions (called seconds in chat; saved budgets and
elapsed times establish 30 minutes each). Read-only local summaries show:
`congestion-v2-01`: 1802.73 learner seconds, 9448 decisions, 43217 commands,
58 episodes; `congestion-v2-02`: 1814.58 seconds, 10652 decisions, 48595 commands,
68 episodes. Both finished normally, parameter updates confirmed. Both configs
have `resume:null`: these are fresh starts, not cumulative continuation.

Both recorded 432 trips on seed 1099, duration 1048.1 seconds, completed rather
than partial. This exceeds the historical 356 recording but is a training-map
best, not generalization evidence. Initial deterministic development scores
were 79/209/82/132/333, mean 167.0, for both. Final scores were 79/86/82/132/333
(142.4) and 79/85/82/132/333 (142.2). Best periodic validation mean was 167.4
for both, scores 79/209/82/134/333: a two-trip change on one development map.
Thus longer training and updated parameters did not establish reliable improved
play; the final checkpoints regressed on one map. Do not present the 432 best as
proof of learning or recommend extending final weights on that basis.

No further training or evaluation was launched for this assessment. Compact
source summaries, configured arguments, validation scores and best replay SHA256
are preserved in `docs/training/congestion-v2-2026-10-28/two-user-runs.json`.
Weights and exact best recordings remain local in their run folders.

## T25 - Traffic lights first, learning audit and overnight preparation (29 October)

User authorized the audit/controlled comparison/checkpoint-selection steps and
asked for traffic lights before motorways, with an overnight command to run
personally. Engineering work remains on `mohammad`; the overnight run was not
launched. Two small 512-decision pilots and bounded startup/update checks were
run to make the implementation reviewable and verify readiness.

Read-only old v2 audit, same states from initial deterministic seed-2000 policy:
42 choice states, 60 forced states, one changed argmax after training, mean KL
0.00004154. Initial max choice probability .488 and entropy 1.246 nats mean this
does not establish that all states lack exploration. It demonstrates small
probability/decision changes on one trajectory, not a unique cause of poor
learning or the seed-2001 regression. Actor updates are not confused with scores.

Implemented opt-in `--traffic-lights`, schema `visible-route-signals-policy-v3`:
547 actions/21107 parameters, up to 32 legal visible ordinary-road junction
proposals (degree >=3, normal light stock, no forbidden endpoints/removals),
12 current-state features per proposal, five traffic-map planes including actual
lights. Proposals refresh each decision, ranked by nearby waiting/vehicle count.
Placement is ordinary `build TrafficLight`; no stock grants or timing control.
Motorways/roundabouts/demolition/manual driveways stay excluded. A shared light
head and zero-start map/global-to-route interaction are learnable. Inspection
showed v2 CNN context fed tool logits/critic but not route logits directly.

Reward remains actual trip delta plus gamma .99 bounded connection potential;
launcher numerical scale .01, lambda .99, learning rate .0001/rollout256/batch64/
four epochs/entropy .005 unchanged. Potential saturates at eight houses and
discounting remains per variable-duration macro decision. No placement bonus is
introduced. Adequate delayed credit assignment remains an open question.
Default v3 prior temperature 2 halves linear prior and upgrade bias contributions
while residual/context contributions stay unscaled; this is an exploration
hypothesis, not an established score improvement. Older inputs/policies remain
available with default temperature 1. Incompatible direct resume is rejected;
v3 resume restores its schema, timing, scale and temperature.

Two fixed-512-decision pilots, two workers, same seed and verified identical
initial tensors, only temperature 1 vs 2 differs. Initial deterministic dev
scores (2000-2002, cap1200) 79/207/82, mean122.667, final 79/208/80, mean122.333,
for both. All six initial/final games per arm failed before the cap. Both update
the route, CNN and light parameters and use normal lights; neither shows improved
score. Training bests236/222 are not generalization evidence. Their wall windows
overlap; 85.52/72.29 learner seconds do not establish a speed difference.
No parameter retuning followed these pilot results. A paired frozen initial-v3
audit on 58 identical choice states increases entropy1.849->1.978 and reduces
max probability .369->.300, with zero changed argmax. This validates more varied
probabilities, not learning. Original v2 dev79/209/82 also means initial traffic
lights alone did not establish better play.

Best validation now starts with the untrained/resumed starting model and keeps
ties; periodic/final policies replace it only on a strict higher development
mean. Both pilots correctly kept initial weights. Selection score/baseline flag
is in `validation-best.json`. Checkpoint selection protection has a regression
test. Console adds placement counts, PPO entropy/KL/updates and validation delta
from baseline. Ctrl+C during initial/final evaluation now also saves current
weights; existing learning-phase shutdown/save path retained. Removed redundant
full-grid construction when only globals are needed, with equivalent values
tested; no measured speedup claimed.

Thirty checks pass: goal8, signals3, workflow5, environment7, rewards6, shutdown1.
Normal weekly stock, legal placement/stock decrement, no road stock decrement,
existing-light plane and exact command replay verified. Signal-head gradients,
route-context/CNN updates, save/reload, four-worker startup and schema-inheriting
resume tested. Tiny startup/resume intentionally stop before a PPO update; not
learning evidence. Generic frozen evaluator detects v3 and preserves weights.
Headless build passes, PS launcher parses. Initial test failures: guessed light
code3 corrected to actual4 before pilots; fake save double-extension corrected;
reward command lacked local dotnet path, rerun passed. Placement counts hardened
to accepted commands after pilot snapshots; pilots had no rejects, so no outcome
change. Later edits add metadata and interrupt/reporting safeguards.

`start_signals.ps1` prepares a manual eight-hour/four-worker fresh v3 run with
30-minute development validation, two-minute checkpoints and a 10M decision
ceiling. Initial/final evaluation adds wall time, periodic validation counts in
the learner window. User may change hours. No recurring automation was created.
Exact command, resume/replay instructions, input meanings and limitations are in
[SIGNALS.md](SIGNALS.md); status/quickstart/index updated. Historical PDFs and
weights untouched. [Evidence archive](../docs/training/signals-2026-10-29/README.md)
preserves audits, paired tensor/parameter assessment, pilot sources/logs/scores,
startup/resume/evaluator measurements and 34 source-copy SHA256s. Weights and
native binaries remain local. The overnight run remains an experiment and is not
claimed to fix learning, reach1000 or use the excluded tools.
