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
