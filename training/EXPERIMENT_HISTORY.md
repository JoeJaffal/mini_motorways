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







## T26 - Partial overnight results (29 October 2026)







User requested the result of `signals-night-01`. Read-only inspection found no



Python trainer or dotnet host running. Saved status is unfinished at 15471.3



learner seconds (4h17m51s) of configured 480 minutes, 125924 macro decisions,



569758 commands and 832 completed games. Neither final.zip nor summary.json



exists. Thus the run stopped before its planned end; cause is unknown from these



files. Do not infer sleep, reboot, crash or user interruption without evidence.



Existing latest/validation-best/best-policy/initial checkpoints remain local.







Initial deterministic development scores2000-2004 were79/207/82/132/337,



mean167.4. Best periodic mean204.2 (+21.98%), at77220 decisions, scores



125/291/154/122/329. Three maps improved and two worsened versus initial. Latest



validation mean185.4, scores237/85/135/134/336, below the best but above initial.



Validation-best metadata has baseline:false, so a trained policy beat its own



starting policy on this development set. This is stronger development learning



evidence than the earlier flat short runs, not a fresh-seed generalization test;



repeated development selection can overfit and results fluctuate.







Best completed training recording:494 trips, seed1099,1124.7 simulated seconds,



partial:false and terminated:true. It is distinct from a deterministic evaluation



of the selected validation-best policy. Do not credit all score changes solely



to traffic lights or confuse the training maximum with validation averages.



No new training, evaluation or process changes were performed during assessment.



Raw metrics, complete best replay, checkpoint hashes (no weights) and source-copy



integrity records are preserved in



[overnight evidence](../docs/training/signals-overnight-2026-10-29/README.md).







## T27 - Predeclared fresh-map comparison (29 October 2026)







User authorized fresh-map evaluation. Before launching inference, froze hashes



of `signals-night-01/initial.zip` and the development-selected



`validation-best.zip` (mean204.2 at77220 decisions); latest and best-training



policies are not eligible for fresh-test reselection. Reserved seeds4000-4009



have no matches in recorded prior training/test evidence. Training was1000-1099,



development2000-2004 and earlier investigation tests3000-3009.







Protocol: same ten LosAngeles/OriginalReference scenarios for both checkpoints,



3600s cap, primary deterministic play, secondary sampled play with one trajectory



per seed and common RNG43+scenario offset. Forty games, at most two evaluation



jobs concurrently; no optimization, tuning or checkpoint reselection based on



these outcomes. Evaluator checks parameter tensors unchanged; driver verifies



checkpoint/host hashes and paired map IDs. Protocol, checkpoint/runtime/source



hashes were saved before spawning jobs and copied to



`docs/training/signals-fresh-2026-10-29/protocol.json`. Limited ten-map/one-run



evidence cannot establish universal performance. Results pending at this entry;



completion/limits will be appended without changing the frozen protocol.







T27 completion: all 40 predeclared inference games finished naturally before



3600s. Deterministic primary means 161.3 initial -> 207.4 selected (+46.1,



+28.58%), with 9/10 maps better and one worse. Secondary sampled means 182.0 ->



188.9 (+6.9,+3.79%), with five better/two tied/three worse. Seed4006 adds70 to



the sampled paired total69, so the secondary gain is almost entirely one map;



do not imply robust sampled improvement. Primary paired differences are



8/30/18/74/208/162/23/-143/61/20. This is evidence of deterministic improvement



on unseen LosAngeles seeds, beyond repeated development maps, not universal



generalization, a unique traffic-light effect, or proof that no memorization



occurred. Only ten maps and one trained model; one sampled path per seed.







All evaluator parameter tensors and checkpoint file hashes remained unchanged.



No optimization, source retuning or policy reselection occurred. The same



development-selected validation-best checkpoint remains the evaluated candidate;



latest and maximum-training policy were not searched on fresh maps. Four saved



best recordings passed headless exact-command replay verification. Those are



reconstruction checks, not additional policy-test trajectories. Protocol/results,



all per-seed metrics, traces, recordings and inference sources are archived in



[fresh-map evidence](../docs/training/signals-fresh-2026-10-29/README.md), with



byte hashes. The protocol copied before execution remains unchanged. The exposed



4000-4009 partition should not be reused as a fresh tuning test. No new training



was started, and the stopped overnight process was not restarted.







## T28 - Traffic-light usage audit of existing fresh-test metrics







User asked whether it learned to use lights. Read-only aggregation of the T27



results: deterministic initial placed12 lights across4/10 games; selected placed24



across8/10. Sampled initial placed22 across9/10; selected placed20 across8/10.



Training changed placement behavior, but the starting policy already included



engineered junction proposals and a light prior. It did not discover placement



from scratch. More placements are not inherently better and counts confound



survival, road design and acquired stock. The fresh-score improvement cannot be



attributed specifically to lights without a controlled enable/disable comparison.



No new inference/training, policy update or checkpoint selection was performed;



these counts derive entirely from the already archived per-game metrics.







## T29 - Simulator traffic-light mechanics inspection







User asked whether lights actually improve traffic in this game. Code inspection:



RoadNetwork.LaneSpeed applies IntersectionMultiplier=.5 at degree>=3 ordinary



junctions but exempts traffic-light tiles. This removes that junction speed-limit



penalty; it does not establish doubled throughput or double total journey speed.



TrafficControl.SignalAllows/MayEnter block red/amber approaches. UpdateSignals



uses green/overtime/amber phases and BestSignalPair considers approaching cars



and waiting. Therefore lights have actual effects, with a speed-versus-stopping



trade-off; a placement can hurt rather than help. No controlled throughput or



AI-policy light-disable comparison was run for this question, so no net benefit



of the trained model's placements is claimed. Simulator rules/code unchanged.







## T30 - Manual traffic-light comparison command prepared







User requested instructions for the next test. Added frozen evaluator



`--disable-traffic-lights` and a SignalEnv action-mask-only switch. Signal proposal



observations remain intact at identical states, as do non-light masks; no physical



simulator rules are changed. A three-test signal suite passes, including that



mask/observation invariant at a normal-stock state and existing placement/replay



checks. Added `compare_traffic_lights.py`: same overnight validation-best policy,



default new seeds5000-5009, deterministic ON/OFF, twenty games, two concurrent



evaluation jobs, pre-inference protocol/hash record, unchanged weight checks and



zero-placement assertion in the OFF condition. Comparison includes trips, paired



wins/ties/losses and descriptive wait averages. Different survival/load confounds



waiting; routes/upgrades/stock can evolve differently. This tests tool availability



for this frozen policy, not an optimized no-light policy or isolated throughput.







Only startup smoke was executed: development seed2000, cap30 simulated seconds,



one trip each condition. It is not performance evidence and does not expose the



new full-test seeds. The full test remains for the user to launch; no training



was started. Exact command and interpretation are in TRAFFIC_LIGHT_TEST.md.



Existing frozen fresh-map archive remains immutable; default normal evaluation



behavior is unchanged. The new switch is explicitly opt-in.







## T31 - User-completed traffic-light availability test







User supplied the completed lights-test-01 output; local reports confirm twenty



natural-ending deterministic games on paired seeds5000-5009. Checkpoint SHA256



matches the same preselected overnight candidate from the fresh-map test. No



weights changed, OFF placed zero lights, ON placed14 total. Mean trips ON190.9



vs OFF209.9 (-19.0, -9.05% relative to OFF). ON better on2 maps, tied5, worse3.



Crucially seed5009 is279 ON versus475 OFF (-196); the other nine total+6 for ON.



Thus the mean disadvantage is dominated by one severe failure, not a consistent



every-map light penalty. Descriptive mean waiting is .69014 ON/.68990 OFF,



essentially unchanged and confounded by episode length/load.







This policy has not established reliably beneficial light placement. It does



not imply lights are always harmful or identify the physical cause of seed5009:



masking placement can also change later road/upgrade decisions. The next useful



diagnostic is comparing the existing ON/OFF seed5009 trajectories/placements,



not blind additional training or changing simulator physics from this result.



No new training, inference, checkpoint reselection or runtime changes were made



for this inspection. Raw protocol/reports/traces/best recordings and source-copy



SHA256s are preserved in



[light availability evidence](../docs/training/light-availability-2026-10-29/README.md).



These exposed test seeds should not be treated as unseen for later tuning.







## T32 - Seed5009 divergence and fixed-command diagnosis







User authorized investigating the failure. New diagnostic scripts reconstruct



the frozen ON/OFF trajectories, record every ordinary command/state, and replay



ON commands with each/both light builds replaced by equal-time waits. Policy



tensors stay unchanged; checkpoint hash matches T31. Scores reproduce279 ON



(824.9s) and475 OFF(1097s); regenerated OFF commands exactly match the original



saved recording. The first675 commands agree. At675s/196trips, ON places a light



at(15,15) while OFF draws(16,7)->(17,6). ON's second light is(24,14) at697s.



No claim is made that the first differing OFF stroke actually adds road.







Holding the ON road/upgrade schedule fixed: both279; first-only374/964.95s;



second-only277/824.55s; neither276/824.6s. No rejected commands/grants. After the



original825-command horizon the counterfactual only waits, rather than using



the policy to adapt. First-only has277 at825s vs original279 at824.9s, then



survives longer; final374 is not immediate throughput or predicted live-policy



performance. Later failure is unserved purple destination54. Thus the second



light hurts in the first-light configuration, but the first can help when the



second is absent. Removing both does not reproduce the full OFF policy's475:



construction/timing feedback is also material. Do not attribute the whole196



gap to isolated traffic-light physics or infer that all lights should be banned.







Original ON fails at green destination28,(21,8): demand7/capacity6, timer50.043s.



At800s both policies have263 trips and timer33.443; at820s both have275 trips



but ON timer45.143 versus OFF3.889. Per-destination survival pressure can differ



despite nearly identical global throughput. The exact microscopic traffic chain



was not fully isolated. Just before the second placement, nearby car41 waits



8.05s for "Carpark access occupied" at blue destination27's entrance road.



Current light features do not encode obstacle cause; this is a concrete input



gap and plausible decision weakness, not a proven account of model reasoning.



Queue-cause and approach/destination pressure are future feature hypotheses;



none was implemented or trained, and no seed-specific placement rule was added.







Five saved replays pass headless exact verification. No simulator, reward,



production policy or selected checkpoint changed. Full local traces/decisions



remain in output; compact timelines, diagnoses, five recordings, relevant



snapshots, source scripts and hashes are in



[diagnosis evidence](../docs/training/light-failure-5009-2026-10-29/README.md).



Optional chart imports failed due missing Matplotlib in both Python environments;



the dependency-free report preserves data without installing training packages.



No chart or new generalization result is claimed. Historical archives unchanged.







## T33 - Queue-cause v4 inputs, preserving weights; user runs long experiments







User authorized implementing the diagnosis and explicitly requested conserving



assistant credits: do not run long shell jobs and wait; provide commands for



the user to run and report completion. Honored: only brief correctness/wiring



checks ran; no full policy evaluation or training experiment was launched.







Opt-in --signal-context introduces v4,32x24 light rows/547 actions/21503 parameters.



Original12 fields are unchanged. Added stopped-car fractions and maximum waits



for parking vs crossing/priority causes, signal/queue causes, related outbound



destination pressure/unreserved demand, global destination pressure, shop-access



adjacency and nearby existing lights. Features use visible current state only;



they are not direction-specific flow forecasts or hidden future outcomes. No



parking ban, hand reward, seed-specific rule, candidate ordering or simulator



change. Their learning benefit remains untested.







Explicit --warm-start transfers the v3 validation-best weights into v4, copying



all existing parameters and zero-extending only two light-input matrices.



Optimizer resets; provided checkpoint's scale/rate/prior/timing inherit. Direct



cross-schema resume is rejected; matching v4 resumes and frozen evaluation infer



the schema from signal width. Common weights are retained rather than restarting



the learned policy. V3 behavior/shapes remain supported.







New short test passes: synthetic observation-only queue/pressure values, unchanged



first12 fields, transferred action probabilities match within1e-6, new columns



zero, optimizer empty, gradients reach new input columns, save/reload detects v4.



Synthetic observation stock is not sent as construction commands or training data.



Three existing signal checks also pass, covering actual normal stock/replay and



masking invariants. Tiny CLI wiring smoke:0.255 learner seconds/3 decisions,



weights unchanged, no PPO update; source SHA/optimizer-reset config saved.



No performance gain claimed. [Command/contract](SIGNAL_CONTEXT.md) gives a manual



60-minute/four-worker trial with15-minute validation; user will notify when done.



Prior exposed test seeds remain excluded from training/development; new final



evaluation must use a new partition. Historic reports/checkpoints untouched.







## T34 - User-completed one-hour v4 trial; next test prepared







User asked what to do next. Local files show signals-context-01 completed normally



in 3600.48 learner seconds: 25,876 decisions, 117,662 commands, 167 episodes,



confirmed weight updates, no active trainer. Warm-start initial validation was



204.2 (125/291/154/122/329), matching the prior selected model's score. Final



and best validation are 228.0 (235/259/155/122/369), up 23.8 / 11.66%.



Three maps improve, one worsens, one ties. Seed2000 contributes110 of the119



paired total gain; the remaining four net+9. Intermediate means164.2/185.6/185.0



were below baseline, so final validation selection correctly retained baseline



until the strict final improvement. Best completed training recording426 on1066



is not a new all-time record or generalization evidence.







Next step is a frozen comparison of this run's warm-start initial policy against



its development-selected best on new seeds6000-6009, deterministic and sampled,



forty games. Added --run/--seed-start/--count to the existing tested fresh-map



driver; defaults preserve the old invocation. CLI help/parameter exposure checked,



no evaluation or additional training started. Per user's credit-conservation



request, the user will execute/wait and report completion. These development



gains do not establish benefit of the added inputs versus equal-budget further



v3 training; that causal comparison remains open.







Raw config, summary, periodic/final selection, final status and PPO metrics are



archived in docs/training/signal-context-run-2026-10-29 with source-byte hashes.



Runtime checkpoint/replay binaries remain local. The new held-out test has not



yet exposed its maps. Existing historical archives are unchanged.







T34 follow-up: user reported "done", but inspection found no assessment.json;



only initial-deterministic.json was complete and the evaluation driver/children



were still active. No error text was present. Requested waiting for the final



ASSESSMENT and returned shell prompt before analysis. Per credit preference,



the assistant did not poll/wait, launch another job or draw partial conclusions.







## T35 - User-completed v4 fresh-map evaluation (30 October 2026)







User reported completion; assessment is now present. Forty frozen inference



games on predeclared seeds6000-6009 all ended naturally. Deterministic mean



175.9 warm-start initial ->194.0 selected (+18.1,+10.29%), two wins/five ties/



three losses. Gains+132 on6003 and+72 on6004 dominate; the other eight net-23.



Sampled mean168.7->169.0 (+.3,+.18%), one win/nine ties/no losses; only6005



changes,+3. This is an improved point mean with inconsistent transfer, not broad



reliable improvement or proven light-placement/feature benefit. Further v3



training with the same budget was not controlled, so feature causality remains



open. Light placements24->28 deterministic,24->24 sampled; counts are not skill.







Checked protocol digest, declared map partition,40 terminal/nontruncated rows,



unchanged tensors and report checkpoint hashes. No new evaluation, training,



replay execution, source tuning or checkpoint reselection was performed. Per



user preference, read completed results only, without waiting/polling. Raw



protocol/reports/traces/best recordings and source-byte hashes are archived in



[v4 fresh evidence](../docs/training/signal-context-fresh-2026-10-30/README.md).



Weights remain local and prior archives unchanged. No next long run authorized.







## T36 - User-run v4 light-availability comparison prepared (30 October)







User authorized preparing the next test. Existing comparison CLI already supports



an explicit v4 checkpoint and custom seeds; no runtime code change was needed.



Selected signals-context-01/validation-best.zip using existing development228.0



selection. Recorded its current SHA256 and reserved new paired seeds7000-7009,



twenty deterministic ON/OFF games, unchanged policy, no optimization. Plan is



docs/training/signal-context-light-test-plan-2026-10-30.json. CLI help and file



existence checked; no simulation or training launched. Per explicit user credit



preference, user will run/wait and notify after final comparison/shell prompt.



Updated TRAFFIC_LIGHT_TEST.md with exact explicit-checkpoint command. This tests



availability for this policy; no universal traffic-light benefit is implied.







## T37 - Completed v4 light test; bounded continuation recommended







User requested next step. Completed lights-context-test-01 matches the planned



v4 checkpoint hash and seeds7000-7009. Twenty deterministic games end naturally;



all tensors unchanged. ON mean177.5 versus OFF159.1 (+18.4,+11.56%), three wins/



six ties/one loss. Paired differences134/0/0/15/0/0/0/155/-120/0;7008 remains a



large adverse case. ON placed22 lights, OFF0. Descriptive waits1.0564/1.5240s



cannot cleanly isolate flow because lifetime/load differ. Availability helps



this frozen policy on average here, not universally. Comparing to v3's earlier



negative availability mean does not prove a v4 feature effect: seeds differ.







No further inference, replay execution, training or checkpoint reselection ran.



Raw evidence/source hashes are in



[v4 light results](../docs/training/signal-context-light-results-2026-10-30/README.md).



Recommendation: retain existing light-enabled policy and run a bounded two-hour



continuation of validation-best with identical architecture/reward/settings,



preserving best validation selection. User executes/waits per credit preference;



no new job has been started. More tools/feature expansion not implemented.







## Branch playground comparison — 29 October 2026







Read-only source comparison requested by the user: local `main` f02fe0e versus



`mohammad` f632008, using `git diff main mohammad` (branch tips, not merge base).



Finding: normal interactive Unity gameplay rules/core existing files are unchanged.



The viewer on mohammad adds AI replay launch/playback with an inspection-only



replay UI, and displays retiring pavement for committed car routes after links



are detached. Added simulation helpers provide read-only draw-change/useful-



connectivity diagnostics and replay validation; headless/training support also



 differs. Legacy C++ playground files have no differences. This is source



inspection, not a new runtime or built-executable comparison; local ignored builds



may reflect another revision. No training or gameplay changes were made for this



analysis. The pre-existing untracked training/diagnose_light_failure.py was left



untouched.







## T38 - Two-hour continuation regressed; starting checkpoint protected







Measured user-run signals-context-02 completed normally after 7200.58 learner seconds,



56,352 policy decisions, 255,084 commands and 370 episodes. Parameter updates confirmed.



Best training game: 480 trips; this is not a validation score or proof of improvement.







Development seeds2000–2004: starting scores235/259/155/122/369 (mean228.0),



final83/259/139/122/329 (mean186.4, -18.25%). Three maps worse, two tied.



Every periodic validation was below228.0. Best-selection retained the starting



checkpoint (baseline:true, steps0); it did not select the regressed final policy.



This means no demonstrated development improvement in this continuation, not



that parameters never changed or that all previous learning was absent.







Engineering recommendation: pause additional long training, keep the protected



228.0 checkpoint and diagnose the regression on development trajectories before



changing settings. No unseen-map test is needed to confirm selection of the same



starting checkpoint. Possible policy instability/credit assignment limitations are



hypotheses, not established causes; no new hyperparameter choice is justified yet.







Inspection only: no training, evaluation, replay execution or simulator changes.



Raw small run files and checkpoint hashes are archived here. Weights and full



training episode/replay data remain local under output/training/signals-context-02.



No new PDF/graph was generated. Earlier PDFs remain historical.







Evidence: [continuation archive](../docs/training/signal-context-continuation-2026-10-30/README.md).





## T39 - Frozen policy regression diagnostic prepared (31 October 2026)



User authorized preparing the proposed comparison, preserving the preference to

run and wait themselves. Added training/diagnose_policy_regression.py. No training

or full diagnostic was launched. The two-second-per-policy wiring check completed:

both zero trips, capped rather than natural ends, weights unchanged. This is only

an integration check, not performance evidence.



Engineering choice: development seed2000, the largest observed regression (235 to83)

in signals-context-02. Compare validation-best.zip with final.zip, deterministic,

cap3600 simulation seconds. Save ordinary-command traffic/queue/shop-pressure

traces, replay files and macro decisions. Both policies are scored on each visited

state with the same action mask; top five choices include route geometry or light

cell and candidate features. Records available route/light counts and first policy

disagreement. Check in-memory tensors and checkpoint file hashes remain unchanged.

Runs sequentially to avoid a long concurrent job; no optimizer call.



Limits: an exposed development failure case, not generalization evidence. First

disagreement is descriptive, not causal proof. Planner option limitations require

follow-up inspection; an unavailable option does not establish impossibility. No

new reward, tool, simulator rule or training setting chosen. Full execution time

has not been measured. Full traces and weights stay local; archive compact findings

when user reports completion. Smoke metadata is preserved here.



Run from PowerShell:



```powershell

cd C:\Users\moham\mini_motorways

.\.venv\Scripts\python.exe .\training\diagnose_policy_regression.py --output output/experiments/regression-2000-01

```



Wait for DIAGNOSIS COMPLETE and the returned PowerShell prompt, then report done.



Evidence: [preparation and smoke](../docs/training/regression-diagnostic-preparation-2026-10-31/README.md).



## T40 - Seed2000 regression reproduced; upgrade choice is first divergence



Measured: user-run frozen seed2000 comparison reproduced protected235 trips at

792.35s versus final83 at469.7s. Both natural failures, unchanged weights. Protected

174 macro decisions, final102; each trajectory has8 states where the two policies'

argmax choices differ under identical observations and masks.



First ordinary command difference is index140 at140s,9 trips, identical state:

protected chooses upgrade index1 (type3 amount2 plus20 roads), final index0

(type4 amount1 plus20 roads). Inventory confirms protected gained2 traffic lights;

final gained inventory slot4 instead. Protected choice probabilities .516/.484;

final reverses preference .476/.524. Small preference changes can switch argmax.

Protected later builds lights at(12,12),235s and(20,8),466s. Final builds none.



Final policy fails at destination0,(16,8), demand10/capacity6, overcrowding50.025s;

several vehicles have crossing/approaching-priority waits around80-104s. Protected

survives longer but also eventually fails (destination14,(21,8),overcrowding50.025s).

On final trajectory at405/410/415s, route choices exist: protected would choose a

route while final chooses wait. Thus this case does not demonstrate complete

absence of planner options; their effectiveness is untested.



Inference: upgrade/tool availability and later route-versus-wait choices are

specific candidates for the regression, not a measured causal attribution. First

choice is near a probability tie, not proof of training instability or internal

reasoning. Recommend one isolated counterfactual: frozen final policy, force only

first differing upgrade to protected choice at140s, then resume normal decisions.

Do not globally ban upgrades or change rewards from this single exposed map.

No full counterfactual, new evaluation, replay verification or training executed

by assistant. Raw command traces remain local; archived policy decisions, replays,

protocol, outcome and first command difference preserve the compact evidence.

This is development diagnosis, not unseen-map improvement evidence.



[Evidence](../docs/training/regression-2000-2026-10-31/README.md).



## T41 - Single-upgrade causal test prepared; user runs full comparison



User authorized preparation and explicitly reserved long execution/waiting for

themselves. Added training/test_first_upgrade.py; no full test or training launched.

Two-second-per-condition wiring smoke passed with unchanged weights; no intervention

occurred in this short check, so the intervention branch remains untested at runtime.



Predeclared protocol: exposed development seed2000, final checkpoint frozen to

original diagnosis SHA256, original3600s cap, deterministic final-policy baseline

versus exactly one override. At140s replace action1 (upgrade choice0) with action2

(upgrade choice1), then use final policy normally on resulting states. Validate

exact intervention state, legal replacement and expected original choice. Compare

all baseline ordinary commands and pre-intervention prefix against diagnosed trace;

require baseline83 trips/469.7s and actual intervention. Record outcomes, full command

traffic traces, decisions and replays. Verify parameter tensors/file hash unchanged.

No optimizer calls, simulator changes, reward changes, grants or forced later actions.



This measures total effect of the one upgrade under this policy, including later

inventory/policy feedback. It does not isolate traffic-light physics, prove which

later decision matters, or establish generalization. Even recovery would not justify

a global hard-coded upgrade rule. If baseline/state guard fails, inspect before

interpreting any outcome. Runtime of full test not measured; two games sequential.

Weights/traces remain local; small protocol/smoke evidence retained here.



```powershell

cd C:\Users\moham\mini_motorways

.\.venv\Scripts\python.exe .\training\test_first_upgrade.py --output output/experiments/first-upgrade-2000-01

```



Wait for UPGRADE TEST COMPLETE and returned PowerShell prompt, then report done.



[Evidence](../docs/training/first-upgrade-test-preparation-2026-10-31/README.md).



## T42 - One upgrade override recovers seed2000 score (31 October 2026)



User completed the prepared test. Baseline reproduces83 trips/469.7s, zero lights.

Changing only the final policy's first upgrade at140s to choice1 produces266 trips/

838.3s, two lights, +183 trips. Both terminate naturally; intervention applied,

checkpoint files and policy tensors unchanged. Script guards require original

baseline command sequence, identical intervention state and legal replacement.

No training or assistant-run simulation occurred during result inspection.



Changed policy independently builds at(12,12), command ending236s, and(13,13),

ending348s. Baseline fails destination0 at(16,8). Changed game fails destination20

at(9,9), demand14/capacity9, overcrowding50.02235. Original protected policy scored

235, so final policy with one overridden choice exceeds that single-map score by31.

It is an intervened policy result, not a new unassisted checkpoint selection.



Causal interpretation: under this frozen policy and exposed seed, the upgrade

intervention changes total outcome substantially. Later light, road, offer and

spawn feedback is included; this does not isolate light physics or assign all183

trips solely to lights. It does not prove generally better upgrade preferences,

robust learning, or universal need for lights. No global upgrade ban/rule adopted.



Engineering recommendation: investigate upgrade representation/action utility,

especially packages for tools this restricted agent cannot deploy, and test a

single explicit upgrade-handling change against the protected checkpoint on a

predeclared development set before another long training run. Exact change and

budget remain undecided; retain228-development protected checkpoint. No long job

launched. Full command traces remain local in output/experiments/first-upgrade-2000-01;

small raw outcome/protocol, macro decisions and replays archived here. Replays

have not additionally been verified in native/headless playback in this inspection.



[Evidence](../docs/training/first-upgrade-results-2026-10-31/README.md).



## T43 - Optional supported-package rule comparison prepared



User asked next step under standing authorization to prepare changes, reserving

long jobs for themselves. Source inspection: GoalEnv masks both offers legal;

SignalEnv adds light placement, but neither implements roundabout/motorway/tunnel

actions. Existing global observation already includes offer type/amount/roads

and inventory; this is not a missing-offer-observation bug. MaterialInventory.cs

increments package counts, which can affect later offers. No simulator bug claimed.



Prepared compare_upgrade_support.py, optional frozen evaluation only. Predeclared

final signals-context-02 policy, deterministic paired exposed development2000-2004,

3600s cap, baseline versus supported-package filter,10 games sequentially. For an

unsupported-extra offer (types2/4/5), mask only its upgrade action if another legal

offer has positive supported extra (roads0/bridge1/lights3) and no fewer bonus road

tiles. Keep observations and all non-upgrade actions intact. Supported extras are

not guaranteed useful on the current map; this is a heuristic, not mathematical

dominance. No masks changed in actual training or ordinary evaluation defaults.



Baseline must reproduce recorded final evaluation on every seed (score/time).

Checkpoint hash and in-memory parameters must remain unchanged. Record each offer,

masked/original/executed action, per-map score/survival/light count, paired outcome

and best replay per condition. This measures total selection-rule effect under

frozen final policy; it does not demonstrate learned improvement or generalization.

No protected checkpoint replaced. No long training/full test launched by assistant.



Checks: six synthetic rule cases passed (supported/unsupported combinations,

road budget and zero quantity; masks/input preserved). Two-second-per-condition

wiring smoke passed, unchanged weights; no upgrade occurs in smoke. After smoke,

added full-run baseline score/time guard; checked syntax/help, not full runtime.



If development outcomes justify continuing, compare to protected policy and test

on predeclared unused maps before adoption/long training. Do not hard-code seed2000

or always pick lights from its one-map result.



```powershell

cd C:\Users\moham\mini_motorways

.\.venv\Scripts\python.exe .\training\compare_upgrade_support.py --output output/experiments/upgrade-support-01

```



Wait for UPGRADE COMPARISON COMPLETE and returned shell prompt, then report done.

Full runtime unmeasured. Weights/local full outputs remain ignored; small smoke

metadata is preserved here. No new PDF/graph created; historical reports unchanged.



[Evidence](../docs/training/upgrade-support-test-preparation-2026-10-31/README.md).



## T44 - Supported upgrade filter improves development set; fresh test prepared



User completed ten frozen final-policy games (signals-context-02/final.zip).

Baseline186.4 versus filter228.8 trips (+42.4,+22.75%);4 wins,1 tie,0 losses.

Pairs2000:83->245;2001:259->288;2002:139->146;2003:122->122;2004:329->343.

Seed2000 contributes162 of212 total gained trips; other four net+50. Policy weights

unchanged, all ten games natural failures, baseline score/time guard passed.

Filtered games changed2/1/2/0/2 decisions and placed4/2/4/0/4 lights. This is a

selection-rule effect, not new learning or proof of generalization. Its228.8 mean

is numerically near protected228.0; not grounds for replacing protected checkpoint.



This rule can change multiple upgrades, explaining245 versus the earlier266 from

only one override on2000. It is not mathematically dominant: supported extras can

be unnecessary, and package counts affect future offers. No training default changed.

Full raw result files (small JSONs, offer events and two best replays) archived here;

weights remain local. No additional replay playback verification, training or full

evaluation performed by assistant. No new PDF/graph created.



Next predeclared test: same frozen final checkpoint, same filter, deterministic

paired seeds8000-8009,3600s cap,20 games. These seeds have not been used in the

recorded experiments. Compare baseline/filter mean and per-map wins/ties/losses;

report concentration, caps and mutation checks; no tuning/reselection from test.

Retain protected checkpoint and keep training paused until reviewed. Added CLI

seed-start/count options to existing evaluator; default development behavior

unchanged, recorded-baseline guard applies only to2000-2004. Short CLI help passed;

no fresh-map games launched. User executes and waits per credit preference.



```powershell

cd C:\Users\moham\mini_motorways

.\.venv\Scripts\python.exe .\training\compare_upgrade_support.py --seed-start 8000 --count 10 --output output/experiments/upgrade-support-fresh-01

```



Wait for UPGRADE COMPARISON COMPLETE and returned shell prompt, then report done.



[Evidence and plan](../docs/training/upgrade-support-results-2026-10-31/README.md).



## T45 - User chooses four-hour training; supported-package option integrated



User chose a long training run instead of further evaluation before sleep, reserved

execution/waiting for themselves, and explicitly corrected8h to4h. Fresh8000-8009

test remains unexecuted/unread in this preparation; no unseen benefit is claimed.



Engineering: opt-in --supported-upgrades on train_goal.py; old defaults false.

Moved identical filter into upgrade_rules.py, used by SignalEnv action_masks and

comparison CLI. Signal-only option; saved model attribute inherited on resume and

model_environment evaluation, including periodic/final validation. Config and info

record flag; run source snapshot includes helper. Explicit --no-supported-upgrades

available on resume. Comparison CLI explicitly disables inherited environment rule

so its baseline remains genuine. Observation shapes/reward/PPO settings unchanged.



Command resumes protected signals-context-02/validation-best.zip (228 development

without filter), preserving weights/optimizer and enabling filter. The new run's

initial baseline is remeasured with filter; starting checkpoint is eligible and

strict-gain validation retains it if learning regresses. Original checkpoint stays

in its source directory. Uses4workers,240 learner minutes,10M step ceiling,

validation every30 learner minutes, seeds1000-1099 and development2000-2004.

Initial/final evaluations add time outside learner budget; not an exact4h alarm.

No rate/entropy/reward changes or long job launched by assistant. Periodic saving

and Ctrl+C handling already exist. Source/checkpoint artifacts remain local.



Checks: synthetic SignalEnv mask integration(default/opt-in), preservation of

non-upgrade masks, road-budget rule, saved model metadata roundtrip and evaluation

inheritance/explicit override; unchanged parameter tensors. No optimizer updates or

games. First synthetic fixture omitted action_space and was corrected; check then

passed. CLI help and repository check passed. Full multiworker training path not

executed in preparation; no promised learning-speed or performance improvement.



```powershell

cd C:\Users\moham\mini_motorways

.\.venv\Scripts\python.exe .\training\train_goal.py --output output/training/upgrades-night-01 --resume output/training/signals-context-02/validation-best.zip --supported-upgrades --minutes 240 --steps 10000000 --workers 4 --validation-minutes 30

```



Keep PC powered and awake. Screen may turn off; system sleep suspends training.

Ctrl+C requests saving. After completion return for summary/validation review;

compare selected checkpoint, not just best training score. Do not infer fresh-map

improvement from validation. Full fresh test remains pending and8000-8009 should

stay untouched until checkpoint selection/protocol is frozen.



[Preparation/checks](../docs/training/supported-upgrade-training-2026-10-31/README.md).



## T46 - ML engineering and games book research (2 November 2026)



User requested two books conveying ML-engineer thinking plus one on ML in games.

Editorial choices: Huyen for systems judgment, Ng for experimental diagnosis,

Yannakakis/Togelius second edition for games. Author/publisher contents checked;

fit-based recommendation, not measured ranking or performance evidence. No run,

code, simulator or training-status changes; commands remain T45. Sources,

alternatives, rationale and limits: [research record](../docs/training/ml-book-research-2026-11-02/README.md).



## T47 - Book recommendation knowledge graph (2 November 2026)



User requested graph presentation of T46. Added labeled relationships between

books, engineering skills and suggested game-project applications to the

[research record](../docs/training/ml-book-research-2026-11-02/README.md).

Editorial synthesis only; no new performance claims, training or code changes.



## T48 - Reading pass: complete Ng text, selected games sections, Huyen summaries (2 November 2026)



User asked to read the three books. Ng chapters1–58 text read; two figure/table

pages visually checked. Games author PDF selected sections read, including full

chapters4–5 and RL/puzzle/strategy passages. Huyen official summaries of all11

chapters read; full publisher text inaccessible. **Request remains partial**:

full Huyen and remaining games-book sections unread. Saved exact PDF ranges,

source URLs/hashes, short takeaways, interpretation/technical cautions and access

limits. No training/evaluation or simulator/code changes. Proposed diagnostics

are hypotheses/engineering suggestions, not measured results or user decisions.

Local-only official book downloads and inspection derivatives stay in ignored tmp;

original notes/source metadata are durable. Training status/commands remain T45.

[Reading notes](../docs/training/ml-book-research-2026-11-02/READING_NOTES.md).



## T49 - Proposed teaching approach after book reading (2 November 2026)



User requested the best approach, not a training run. Engineering proposal:

retain strategic planner-assisted actions; audit observations, proposals and

reward; validate a teacher and collect demonstrations/corrections; test bounded

PPO refinement with mixed curricula; add lookahead only if measured costs allow.

Separate teacher/planner assistance from learning, and development diagnosis from

fresh-map generalization. No claim any new method is proven best. Evidence checked:

228.0->186.4 continuation, frozen upgrade rule186.4->228.8 (mostly seed2000),

single-upgrade83->266 and older investigation limits. Four-hour run outcome was

not inspected. Book coverage remains partial as T48. No new code, simulator

choices, weights, training/evaluation games or performance results. User has not

adopted this proposal; existing training commands unchanged. Full rationale,

sequence/gates, sources and unknowns:

[approach](../docs/training/ml-book-research-2026-11-02/MINI_MOTORWAYS_APPROACH.md).



## T50 - Published GitHub learning roadmap (2 November 2026)



User requested a forward plan as closable GitHub issues, authorizing publication.

Created tracker JoeJaffal/mini_motorways#1 plus12 child issues#2–#13. Each has

explicit scope, evidence-based closure criteria, dependencies and documentation

requirements. Sequence: review four-hour outcome; freeze evaluation/budgets;

audit/fix bottlenecks; validate teacher; dataset; imitation; learner-state

corrections; PPO comparison; conditional curriculum; optional lookahead; frozen

final evaluation. A closed negative result does not pass a downstream gate.

No claims imitation/curriculum/planning are already proven best.8000–8009 remain

reserved; no run output or reserved maps inspected. No training/evaluation,

model or simulator changes. Commands and long-run authorization unchanged.

GitHub CLI authentication/empty issue inventory checked;13 open issues fetched

and complete bodies/titles/URLs verified against archived source. Working branch

mohammad; no commit/push performed. Current status and docs index updated.

[Plan, issue bodies and publication checks](../docs/training/learning-roadmap-2026-11-02/README.md).



## T51 - Paused issue work and provisional project ratings (2 November 2026)



User started GitHub#1/#2, then explicitly stopped execution; issues remain open.

Before stop, read-only inspection found completed upgrades-night-01 (824episodes,

125452steps), development initial236.4, selected239.0 at99628steps, final213.4;

no new training/evaluation or issue closing occurred. Hash/archive/baseline review

is incomplete. User then requested expectations and a candid assessment, not

resumption. Provisional editorial ratings: engineering7/10, experiments6/10,

model3/10, learned-skill evidence3/10, teaching4/10, progress toward robust

player4/10, roadmap7/10. These are not measured benchmarks. Selected gain+2.6

(+1.10%) across5 exposed maps has2 improvements/1tie/2declines; final regresses.

No generalized skill or human/expert comparison established. Suggested refinements

include diagnostic branching, small imitation feasibility gate and simulator

transfer checks; not applied to GitHub. Pause remains in force. Assessment records

sources, preliminary findings, rating rationale, unknowns and limitations:

[project assessment](../docs/training/ml-book-research-2026-11-02/PROJECT_ASSESSMENT.md).



## T52 - Model-specific audit and roadmap v2 published (2 November 2026)



User requested a complete model-tailored roadmap rework and explicitly permits

starting from scratch with a different algorithm. This authorizes audit/replanning

and GitHub edits, not training execution. Earlier paused issue work is not silently

completed. Reviewed goal/signal/environment/trainer/reward/router/callback/vector

source and saved checkpoint/settings; synthetic forward passes only. Confirmed

critic ignores detailed signal rows (value delta0), local signal logits ignore

changed global/traffic (delta0), while changed signal context changes signal logits

0.0149809. Parameter tensors unchanged; no simulator or optimizer steps. No score

harm inferred from these probes. Variable macro duration vs per-decision discount,

limited topology/pressure inputs, restricted proposals/tools, trainable priors,

action-family mass and narrow validation require explicit checks. Checkpoint has

64 rollout steps/worker,4workers,gamma/lambda.99,4epochs,batch64,target_klNone;

these settings alone do not explain regressions. Development236.4/239.0/213.4

initial/selected/final verified from existing records, not newly evaluated.



Published tracker#1 revision and19 open child issues#2–#20. Reused12 existing

child IDs with explicit superseding scopes and added7 milestones; all remote

full bodies/titles/states verified against local archives. v1 source and pre-edit

snapshot preserved; old publisher retired. v2 sequence: baseline/protocol/fidelity;

causal case corpus; return semantics; actor/critic representation; proposal/execution;

tiny-task learnability; cheap teacher/search feasibility; common-contract algorithm

tournament; optional imitation/curriculum; stability/profiling; full tools/redesign;

ablations; transfer; frozen release; regression/plateau process. Teacher failure

no longer blocks model-free alternatives. Corrected PPO, replay-based candidate

value learner, justified masked memory and feasible planning/teaching can compete;

scratch/warm choice is measured. No method declared optimal. Numeric quality/budget

defaults are proposed for protocol ratification before outcomes, not user decisions

or guaranteed results. Full-tool/real-game milestones remain explicit if deferred.



Archived small source/run evidence with hashes and local-only checkpoint identities;

no weights/binaries/private game research copied. Current status/index updated.

No training/evaluation, issue closing, production model/simulator changes, commit

or push. Verification: archive hashes/checkpoints, synthetic dependencies and

GitHub full-body matches; no perfection/1000-trip promise. Work onmohammad.

[Audit](../docs/training/model-audit-2026-11-02/README.md),

[v2 roadmap](../docs/training/learning-roadmap-v2-2026-11-02/README.md).



## Live random-map viewing preparation - 2 November 2026



Added frozen one-game local browser viewer; native viewer supports replay only.

Two-second smoke passed (no training/full game); simplified rendering has not

been visually inspected. Play/Pause and saved completed replay; user runs full

game. [Contract/command/limits](../docs/training/live-random-view-2026-11-02/README.md).


## T53 - Baseline review completed; GitHub issue2 closed (2 November 2026)

User authorized starting roadmap execution. Completed first issue through read-only
source/config/log/checkpoint inspection; no environments, games or optimizer steps.
Runupgrades-night-01 completed824episodes/125452selections/564102commands and time
budget; no independent console termination log. Seven validation means checked;
selected239.0 at99628steps is maximum eligible, initial236.4, final213.4. All45
existing eval rows naturally terminated/zero rejections, all10 replay headers
consistent but not simulator-replayed.824episode and worker-monitor rows agree;
best training496 remains a recording, not expected selected-policy skill.

Engineering baseline decision: selectedvalidation-best is provisional development
incumbent (239.0); initial is same-filter rollback/control236.4. Original protected
unfiltered228.0 retained; protected/initial policy tensors AND optimizer identical.
Thus filter effect on this starting model+8.4 is engineering; selected learning
comparison+2.6/+1.10%,2wins/1tie/2losses is development only. Older186.4->228.8 used
a different final model. No fresh generalization/release promotion. Exact checkpoint
paths/hashes/environment/inference contract and unexecuted command in registry.
Ten source snapshots match recorded4d8577c after newline normalization. Four weight
identities hashed; no weights/binaries/private research archived.36small sources/
derived files archived and independently hash-verified. Missing reproduction,
selected original replays, binary identity and wider/multi-seed evidence explicit.

Published completed checkboxes and self-contained result/hashes toGitHub#2, closed
COMPLETED; tracker#1 remainsOPEN and first checkbox checked. Others remainopen.
Current status/docs index updated. Next#3 protocol/seed/budget contract; no new
long-run authorization or execution. All changes onmohammad; no commit/push.
[Assessment/registry/evidence](../docs/training/baseline-review-2026-11-02/README.md).


## T54 - Evaluation contract and seed/budget registry completed (2 November 2026)

User assented to proceeding after the baseline explanation. Continued foundation
planning only; no training/model/map/game outcomes loaded or generated. Engineering
contract defines LosAngeles OriginalReference real-trip score at3600game seconds,
restricted/full-tool/transfer claims separate. New allocations: training10000–19999,
development20000–20029(30), teacher validation21000–21019(20), final quarantine
30000–30099(100); legacy8000–8009 retains its prior reserved purpose. Historical
exposure inventory based on durable records, novelty still subject to metadata
conflict check before first use. No reserved outcomes inspected.

Pre-outcome acceptance choices:>=5% and>=5trip mean gain;positive95% hierarchical
paired mean-difference interval;no median decline;<=10% lower20%-tail loss;
early failure<300s increase<=5pp;zero invalid/rejected/crash/nonfinite outcomes;
p95CPU encoding/scoring250ms,totaldecision1s,combinedmemory12GiB. Unmeasured
resource gates/missing precision mean inconclusive. Three independent finalist
seeds101/202/303; screening101/202. Fixed historical incumbent is not replicated
training evidence. Separate action/map/learner/bootstrap RNG rules. Counts are
budget/precision choices, not power guarantees or predicted attainable scores.
No retroactive relaxation or final-test reselection. Screen ceiling30learnermin
or20000decisions and60min inclusive perarm/seed; fixed initial/final30map checks
and at most one first10-map midcheck. Longer runs still need measured proposal
and separate authorization. At historical8.7decisions/s,20k~38min;not a forecast.
Hardware read-only: i7-1185G7,4cores/8logical,31.7GiB RAM; latency not benchmarked.

Found current trainer hard-codes old map pools,1–5validation maps and RNG42/43.
Issue#8 updated with explicit configurable split/RNG/cadence readiness before
comparative updates;#13 updated with quality/statistics/resource report readiness.
Protocol planning completion does not claim those changes implemented. Checker
verified disjoint partitions/counts/RNG/cap and printed unexecuted development
commands only. Primary uncertainty motivation checked in Agarwal etal arxiv
2108.13264; actual criteria here are engineering choices. No production source
change; historical roadmap publisher guarded against replay over completed issues.

GitHub#3 checkboxes/results published and closedCOMPLETED;#1 checklist updated,
#8/#13 remainOPEN,next#14 fidelity. Baseline/checkpoints unchanged. Exact bodies,
protocol/registry/ledger/report and integrity metadata archived. Current status,
indexes and progress updated. Work onmohammad,no commit/push or jobs.
[Contract](../docs/training/evaluation-contract-2026-11-02/README.md).


## T55 - Scoped fidelity audit completed; issue14 closed (3 November 2026)

User authorized proceeding to the next foundation issue. Fresh headless build
passed(0warnings/errors,7.87reportedsec).42mixedC#simulation suites,21selected
existingPythonchecks(7adapter/6reward/6goal/1workers/1signal),5additionalv4contract
groups all passed. Tests use legacy/lab fixtures, not new development/test sets.
Existing learner/update tests excluded. No optimizer steps, full policy benchmark,
reserved8000–8009 or new allocated maps opened. Some correctness fixtures use
frozen/untrained prediction; not learning. Core lab/debug setup remains isolated
from allowed training actions and is not performance evidence.

Currentv4 train/eval settings/encodedobs/masks match; future/RNG/planned-demand
field injection unchangedencodedobs/masks; supported-upgrade mask alters only
intended offers; wait cap/time-limit and reward-scale/game equality pass. Normal
scripted upgrade/light consumes1light/noextra roads with0rejectedcommands;
142command/142s exact replay PASS,9trips correctnessfixture(not model skill).
Independenthost/autoreset/terminalobs flags and existing shapingterminal/cap
contracts pass. All4baselineweight-file hashes unchanged. Source snapshots match
4d8577c normalized; hosthash81cff0fcd7a775245c3ad77ae1382490c2ab1d3155ec0ac93fe94d1dc6babe49.

Scope verdict:PASS bounded internal consistency of restrictedsimulator/adapter;
not exactcommercialparity or comparative-training readiness. Discrepancies F1:
runtimeexactReplicaValidatedfalse/acceptedparking and other approximations(#19);
F2:hardcodednew-protocolsplits/RNG(#8);F3:macrotime-returnchoice(#5);
F4:information/proposals/tools(#6/#7/#17);F5:unexhaustive long/adversarial coverage
needs failure-driven fixtures(#4/#7). No new critical mismatch found in tested
scope; no claim allremainingdifferences resolved. No user/simulator rule change;
existing DESIGN_DECISIONS041 remains historical acceptedapproximation.

Archived48report/log/source/replay/script/provenancefiles withhashes; binary/weights
local-only, no privategame research newly accessed/copied. Initial rg path/glob
lookups corrected; actual test groups passed first execution. GitHub#14checkboxes
and self-contained findings published, closedCOMPLETED;tracker#1checkedscopedgate,
remainsOPEN,next#4failurecorpus. Status/index/progress updated. Workmohammad,
no commit/push, no new longrun authorized. No further broadened tests after passes.
[Report/evidence](../docs/training/fidelity-audit-2026-11-03/README.md).


## T56 - Current decision corpus and isolated connection effect; issue4 completed (3 November 2026)

User authorized proceeding. Collected10 frozen deterministic trajectories on
already exposed2000–2004 (current incumbent+same-contract rollback), no optimizer
updates/newmap allocations/reserved access. Reproduced all prior scores exactly:
266/317/147/122/343 vs235/288/155/122/382 (239.0 vs236.4). Both policies cross-scored
at every visited identical observation/mask.1763 macro decisions log legal IDs,
all legal probabilities/raw logits, values, action families, durations/rewards,
resources/pressure;68 predefined event/final states retain full lossless sparse
policy observations/candidate identities plus segregated diagnostics. Full inputs
are sampled, not stored at every frame. Successful/tie controls included. No
policy tensors/checkpoint files changed; all control games natural failure,0rejects.

First shared differences:2000light/wait395s;2001route/route210s;2002route/route281s;
2003wait/route511s;2004provider/path alternatives to same destination22 at308s.
Measured additional isolated intervention: force exactly incumbentaction6->5 at
that identical observation/mask, then unchanged incumbent adapts normally.
343->366 (+23) at978.4s,0rejects, below full rollback382. Both options existed,
25roads in stock,one newtile feature each. Total macro-choice effect includes
path/provider, stroke duration and downstream traffic/growth/adaptive choices;
not all39-pointgap explained, not an isolated physical-road effect or universal
better-house rule. Single exposed map chosen adaptively for diagnosis; no promotion.

56 pressuredstates(timer>=30s),25onlywaitlegal despite roads in stock in5/10
trajectories across4/5maps;9other pressured discretionarywaits not labeled errors.
These are sample-state counts,not populationfrequencies, and useful full-tool
recovery remainsunproven. No strict trips/discounted-return reversal inpaired
outcomes. Intervention tripreturn94.398063->95.416689 also improves; discounted
potential cancels atnaturaldeath inall11trajectories. No uncanceledbonusloop or
rewardmisranking demonstrated here; macrotime/credit remainsopen. No rejection
executionbug inthissample; accepted redraw/no-op costs not exhaustively attributed.

Rankednextchecks: strategicranking/context (currentcausalevidence), recovery
proposals(observedceiling,unmeasuredrepairbenefit), actor/criticinfo(structural
unmeasuredscoreeffect), macrocredit/stability(open), historicalunsupportedupgrade/
lightinteractioncases(partlymitigated,olderpolicies). Old83->266 upgrade and
279->374 fixed-schedule light cases preserved separatelywithsourcehashes,not
remeasured/currentpolicy effects. Rollback not a qualified universalteacher.

Controlcollection377.93wallsec plus51.65interventionsec includes tracing,not
throughputbenchmark. Newreplays preserved butnotindependentlyreplayed. Checks
passed same-state/candidate,probabilitysum,command/duration/reward bookkeeping,
exactscoreguards,singleoverride andunchangedweights.45corpus/report/script/metadata
files~9.3MiB archived withhashes;weights/generatedbinaries/privategame research
excluded. No production code/ruleschanged or longtraining; no furthergames after
planned10controls+1intervention. Initialhistoricalcase resultlabel lookup corrected
beforearchive (changed-upgrade key); no missing scoreinvented.

GitHub#4checked/closedCOMPLETED;#5/#6/#7 updatedwithself-contained findings;
tracker#1checked scopedgate,remainsOPEN. Next#5return/creditcontract,then#6/#7
context/proposals. Baselineunchanged. Status/index/progressupdated. Workmohammad,
no commit/push. [Corpus/ranking/limits](../docs/training/failure-corpus-2026-11-03/README.md).



## T57 — Return/time/credit audit, 3 November 2026



User authorized next roadmap step (#5). Engineering decision: retain versioned

legacy per-macro gamma=.99/lambda=.99 surrogate, .01 training scale, terminal

potential zero only at true failure, external-cap live potential and critic

bootstrap. Capped actual-trip evaluation is a different objective. No simulator

design decision or production-code change. Revision4d8577cf on mohammad.



Measured:7 transition+5 isolated event/fractional checks,12 installed SB3 buffer

fixtures and2 installed MaskablePPO toy timeout collections pass; four synthetic

transitions,0 optimizer updates, no real checkpoint loads or simulator games.

True termination has no bootstrap; timeout adds gamma*terminal value. Rollout

32/64/128 and lambda .99/1 with zero/oracle values demonstrate bootstrap can

carry credit beyond rollout, not a real-critic quality or improvement measurement.

Same physical trip history produces9.320653 vs9.9 legacy return under different

grouping; correct illustrative event weighting removes this synthetic difference.

Eleven archived #4 traces rescored, durations .45–18s; no strict paired trip-score

ordering reversal under legacy or illustrative time discount. Five exposed pairs

and approximate command-end trip timing cannot establish general alignment.



Current routes continue through growth/offers; wait interrupts, terminal/cap ends

routes. Preserve baseline behavior; event-aware execution goes to#7 with versioned

timing. No evidence here justifies learned reward improvement. Reopen for

controlled score/return conflicts, timing restrictions or cap exploitation. New

finite-horizon/time-aware objectives require aligned event rewards, continuation,

potential, GAE, targets, cap semantics and explicit critic/optimizer migration;

no scalar-gamma-only patch. #8 readiness must enforce contract. All4 protected

weight hashes unchanged. Full checks, source/input hashes, results and decision:

[return audit](../docs/training/return-audit-2026-11-03/README.md).



GitHub#5 closed as justified no-change;#7/#8 and tracker#1 updated, remaining

gates open. Next#6 context. Status/index/progress updated. No commit/push or long

training authorized. Hypothesis that better context/proposals improve play remains

to be measured. Archived weights/binaries excluded; local reports not yet pushed.



## T58 — Contextual representation implementation and bounded audit, 3 November 2026



User said go ahead following#5. Engineering choice: implement opt-in

contextual-candidate-actor-critic-v1 with unchanged v4 observations/actions/return

schema; preserve legacy GoalPolicy and all trainer defaults. Shared route/signal

masked mean/max pools plus global/traffic context feed nonlinear per-row scorers,

tool head and critic. No hand-initialized priors/upgrade offsets in this candidate;

initial behavior differs and requires learning. New module only, no simulator

design or legacy source changes. Workmohammad,base4d8577cf,dirty documentation.



Measured:3 focused groups pass: detailed signal-to-critic and global/traffic/

competing-demand pairwise-score gradients, full value perturbation, permutation,

padding/empty/negative maxima, duplication sensitivity, legal-mask probabilities,

unused optimizer, temporary checkpoint save/reload.68 archived #4 snapshots

cross-scored with incumbent/scratch/partial-warm initializations; results explicitly

not learned-performance comparisons. Boundary counts0/179 valid route demand and

0/269 signal pressure at clip ceiling, not all-column or raw exceedance proof.

Four checkpoint hashes unchanged. No host/game transitions, optimizer updates,

new/reserved seed access or learning. Added shape/action/source guards afterward;

unchanged forward computation, full tests rerun pass. Scratch/warm toy models are

not saved as promoted artifacts; temporary serialization files removed normally.



Audit distinguishes heuristic prior/residual/context effects, strong offer10

offset at temperature2, softmax candidate multiplicity and non-invariant unequal

duplication. No unsupported family correction/pruning added. Directed edge bits,

complete path overlap and per-provider/building capacity/reservation/in-flight

distinctions remain absent. Degree-only grid is provably lossy; complete-state

alias and C5 internal cause not established. Draft observable-network/graph

specification only; no graph/history implementation or benefit claimed. Partial

warm helper copies route first affine weights only, changes activation, resets

critic/heads/optimizer; not behavior preserving or proven helpful.



Decision: keep as comparison candidate, do not promote. #6 remains OPEN because

trained scratch/warm acceptance, topology-task evidence and trainer architecture/

resume metadata readiness are pending#8/#7. #7 is next actionable proposal audit;

#8 must resolve protocols/integration before bounded learning comparison, then

close#6 only with keep/reject measured evidence. No long training authorized.

GitHub#6 first4 audit checkboxes checked, final learning checkbox remains open;

#7/#8/tracker handoffs and status/index/progress updated. No commit/push. Full

[specification, results and code archive](../docs/training/representation-audit-2026-11-03/README.md).



## T59 — Independent authorization and proposal/execution audit, 3 November 2026



User's final instruction authorizes independent useful work without repeated

confirmation and requests summary. Engineering scope: proposal audit, trainer

readiness and bounded diagnostic learning, preserving incumbent. Base4d8577cf,

mohammad; no simulator design/rule changes.68 prior snapshots:179 route proposals,

7 exact route+destination duplicates,2055 edges/1462 already connected,1388 planned

strokes/904 entirely connected. Experimental missing-edge draft emits484 strokes;

these are correlated planned candidates, not executed savings or useful-action

recall. No route512/signal32 full rows in these snapshots; wait always legal.

Introduced pure draft/identity helpers and tests, not enabled in environment.



Four exposed2004 prefix replays to308s passed exact trip/time guards. Route5

legacy2 commands vsdraft1, same final topology/infrastructure, roadstock25→24,

end310vs309s; route6 remains1. All completed branches0 rejects. Initial replay

adapter sent recordedwait as a host command and failed; fixed wait->advanceNone,

then all4 branches rerun successfully. Five resets including failed attempt;

no partial failed result passed as success. No whole-game scores/newmap access.

No proof of general bridge/stock/stale-plan feasibility or traffic benefit.

Decision: keep legacy execution;#7 stays open. Source/results and limits:

[overnight archive](../docs/training/overnight-preparation-2026-11-03/README.md).



## T60 — Registered fresh-only trainer readiness, 3 November 2026



New train_contextual.py leaves historical train_goal untouched. Explicit old/new

architecture identity, fresh-only outputs/no implicit resume, compatible partial

warm helper/fresh critic-head-optimizer; configurable training10000–19999 subset

and exact30 development20000–20029, rejects quarantined/unknown configs. Distinct

learner/action/worker RNG roles; worker seeds explicitly reapplied; fixed initial/

final evaluation,optional one10-map midcheck, RNG state preserved across eval.

Return/cap/scale timing held to#5. Stop/time/step limits,checkpoint/source metadata,

collection sequence/exposure logging. Between-operation budget checks can exceed

cutoff by host/checkpoint/shutdown overhead; partial rollouts may be discarded.

No full-host run of new runner; no stats/resource/release sign-off. Three runner

tests and dry-run pass; no new registered maps generated or exposed. Test exposure

writer mocked; production ledger remains free of fake development outcomes.



## T61 — Predeclared mixed synthetic PPO comparison, 3 November 2026



Under broad user authorization, pilot-plan.json fixed7 arms before updates:

contextual scratch/warm and legacy scratch at101/202 plus constant-cue control101,

4096 interactions each,nsteps128,batch64,epochs4,lr.0003,gamma/lambda.99,180s/arm,

900s total.28672 synthetic steps,896 SB3 epoch counters,166.38s wall incl eval/save.

Not game reward/trip optimization: hand-declared feature/credit rules only.

Train magnitudes.1/.9,withheld.3/.7;128 independently seeded evaluation cases/task.

Required each fit>=.8/withheld>=.75, no averaging away failures.



Both contextual scratch/warm seeds learn5/6 rules at100% withheld;upgrade stock

46.09% fails (fit44.53%). Both legacy scratch learn4/6;upgrade53.91% andusefulwait

48.44% withheld fail. Legacy uses defaulttemperature1, not incumbent2: architecture

and initialization bundled, no isolated causal attribution or game superiority.

Warm no final task-accuracy benefit; choose scratch for experimental continuation.

Every mixed arm fails mandatory gate. Fixed declared-rule heuristic100%; cue

shuffle43.75–53.13% and corrected erased-input44.53–53.91% contextual controls.

Original constant-trained evaluation on normal inputs was distribution shift,

not a valid chance claim; retained rawresults and added corrected erased-input

analysis. Test verifies constant inputs alias balanced labels. Gradient/parameters,

masks/finite values and save/reload pass. No retuning/extension or promotion.



## T62 — Failure probes, final checks and gate decision, 3 November 2026



After mixed failures, separately predeclared supervised representability probe:

copy contextual101 checkpoint,200 Adam steps,lr.001,30s max;8.70s actual,100% final

fit/withheld,finite gradients. Originalcheckpointunchanged. Stock-input gradient

already nonzero: mixed policy101 upgrade probability.4626→.3567 asstock.1→.9;

signal moves correctly but stays below decision threshold. Direct fit does not

repair PPO or qualify a real-game teacher.



Separate isolated-task PPO plan then fixed same4096step hyperparameters/seeds101/

202,90s/seed. Both fit100%,withheld10146.09% fail vs202100% pass (14.31/13.88s).

Mixed verdict remainsfailed; cannot conclude absent representation or inherent

PPO failure. Sparse two-magnitude training underdetermines interpolated behavior;

next hypothesis is varied-cue data coverage/sample allocation and balanced-task

optimization, with a new versioned experiment, not rewritten historical verdict.

Total9 PPO runs36864 synthetic interactions,1152 SB3 epoch counters (not minibatch

optimizer-step count),plus200 supervised Adam steps. No real game policy learning.

All experiments ended; no backgroundjob. Full-game/tournament remains gated.



Final12 focused/regression checks andgitdiffcheck pass. All4 protected checkpoint

SHA256s reverified. New weights/temporarygeneratedfiles remain ignored/local-only,

small measurements/plans/source/logs archived withhashes. No newdevelopment,

teacher,final or8000reserved scenario access; onlyexposed2004prefixes inT59.

No simulator designchanges; no commit/push. #6 closes comparison withkeep

experimental scratch/no promotion; this supersedes T58's pendingcomparison only,

not #8's mandatory failed gate. #7/#8 remainOPEN;tracker updated; next repair

diagnostic distribution/mixedlearning andfinish proposal safety/commoncontrols.

Status/index/progress/GitHubupdated. See datedarchive for exact results/limits.



## T63 — User chooses planner-free direct construction, 3 November 2026



Explicit user preference: "have this in our plan ... i dont like the planner

idea" after discussing direct tool/cell control. User decision045 records it;

do not infer a measured advantage or new long-run authorization. Engineering

revisionv3 makes direct model-selected construction/removal/reconnection/upgrades/

wait the target. Deterministic ordinary execution/legality allowed; no route

generator, goal selector or strategic pruning supplies the deployed solution.

Hybrid remains frozen comparison baseline, not primary development path.



Revised #7 to audit/reuse primitive all-tools adapter and define direct input/

action/cursor/mask/timing contracts; #8 to actual small direct-construction learning

and withheld variations; #10 to common direct-control algorithm comparison;

#15 to staged learned construction/traffic/repair. #9/#12 now optional offline

teaching and no longer block#10/#11/#15 when deferred. All remaining open issue

scopes/tracker reflect direction; previous bodies archived before mutation.

Closed audits retained historical scope. New direct observations/architectures,

staged selection discount/shaping/GAE and full tools must be revalidated; old

macro/candidate experiments are not direct-control passes. Overnight mixed

diagnostic gate remains failed; next step supersedes T62's hybrid repair order.



No training/inference/scenario generation, model migration or production code

change. Workmohammad; no commit/push. GitHub open states/title/direction checks

passed for all14 edited issues. Current status/index/liveprogress updated. V2

reports/publication snapshots preserved. [v3 plan and before/after archive](../docs/training/learning-roadmap-v3-2026-11-03/README.md).


## T64 — Workstation hardware recommendation, 3 November 2026

User reports XeonW-1370P/QuadroRTX4000 PC and asks whether to use it. Verified
manufacturer specs:8cores/16threads and originalQuadro8GB; laptop recorded
anchor i7-1185G7/4cores8threads. Recommend workstation for sustained experiments,
laptop for development, contingent on setup/benchmark; no measured speedup.
CPU worker scaling and GPU learning benefit are hypotheses; C# simulator remains
CPU and current trainers forceCPU. PC RAM/runtime/software unknown. Future#16
needs device/worker parity and whole-run timing;8workers would require amendment
to current4worker cap. Not a user migration decision or authorization to skip
failed#8 gate. No installations/code/config/model/run changes or remote inspection.
[Sources, evidence and limits](../docs/training/hardware-assessment-2026-11-03/README.md).


## T65 — Second-PC project visibility and transfer gap, 3 November 2026

User installed Codex on workstation but cannot see project. Official OpenAI
projects documentation confirms conversation sync does not transfer local folders:
https://learn.chatgpt.com/docs/projects#use-local-projects-for-folders-and-codebases
Checked local status: mohammad tracksorigin/mohammad, but current code/docs and
new dated archives remain uncommitted/untracked. Origin is JoeJaffal/mini_motorways.
Cloning branchmohammad gets pushed history only; it will miss these local changes
and ignored checkpoint weights. Need transfer/publish reviewed source/evidence,
separately transfer required local-only checkpoints, recreate dependencies on PC,
and attach resulting folder as local project. No remote state inspected, transfer,
commit/push, environment installation or training performed. Guidance used the
OpenAI Docs skill; distinguish app installation/conversation from filesystem access.


## T66 — Laptop control of workstation Codex, 3 November 2026

User asks whether laptop can command workstation Codex. Official remote-connections
page fetched: https://learn.chatgpt.com/docs/remote-connections. Supported desktop
apps can pair via Settings>Connections>ControlthisMacorPC on host and Controlother
devices on client where available; rollout/account/workspace/admin availability
varies. Host must remain awake,online,app running; execution/files are on host.
SSH remote projects are a separate documented alternative, not configured here.
Chat handoff can transfer Git state to a matching saved destination project, but
ignored weights/dependencies are not assumed transferred. This refines T65's
manual-transfer advice: native handoff is another supported path once connected.
No settings/access/credentials changed, pairing performed, remote state inspected
or transfer/training started. User-facing guidance cites official OpenAI docs.



## T67 — Direct-control interface audit and prototype, 4 November 2026



User requests continuing issue work after v3 planner rejection. Scope#7,

not a long run. Engineering reuse: primitive TrafficEnv already directly decodes

ordinary tools/cells and directional road bits; historical hybrid and primitive

source remain unchanged. New direct_agent/direct_policy/direct_legality opt-in

modules, fresh schemas and checkpoints only. Workmohammad,base4d8577cf; no simulator

rule/code change. User decision045 remains direction; choices below engineering.



Direct-tools-staged-raster-v1 initially exposes tool/cell selections and normal

host RasterLine command, not route search. New62-channel visible-load grid and

6-stock vector extend old52-channel directional/cursor input with bounded demand,

reserved/capacity/overcrowding, visible assignments/queue causes/home workloads.

Hidden future/random data excluded; visibility test passes. Original columns

still clip; rail/train actor fields and exact vehicle/parking tables missing.

New shared learned actor/critic consumes all input groups; cursor-coordinate

context and distant-cell ranking test added (architecturev2-cursor). No heuristic

score offsets, route candidates, productive mask or unsupported-upgrade pruning.



Reward explicitly new per-SELECTION gamma.99/lambda.99-compatible surrogate:

.01*(trips+.99PhiNext-PhiCurrent),Phi=.25minconnected8; zero-time cursor steps

included in discount/shaping. True failure zeroPhi/nobootstrap; external caplivePhi/

valuebootstrap. Real capped trips remain evaluation, not equal objective. Future

runner must enforce learner settings; arbitrary external SB3 settings not enforced.

One command advances20ticks, fractional failure possible; intermediate selections

0ticks. Wait cancels cursor/time advances; terminalnextmasks empty before reset.



Initial random mask exerciser3exposedmaps1000/2000/2004,60commands each:394selections,

180commands,6 rejected draws,0trips (not a learned score benchmark). Exact old

replays give3no-road-stock,2invalid-driveway-neighbor,1invalid-parcel-link reasons;

all atstock0 but stocknotsolecause. Preserved initial source/results/snapshots.

Fixed via visible complete-stroke feasibility over model-selected raster, with

stock/bridges/terrain/access/diagonal/rail tests; no alternative route search or

strategic ranking. Versionactionv2-complete-stroke. All6failedcommands excluded

in exact oldstates. V2 and final shorttrials each388selections/180commands,

0rejections/0trips; masks change sampled trajectories so not a paired score gain.



Precheck conservative: roundabout footprints and partial strokes excluded; no

reliance on within-command bridge-span-merger refunds. All13tool decoder paths

exist but full-tool legality/capability NOT signed off. #17 owns remaining advanced

stock/bridge/refund/rail/roundabout/motorway/driveway/removal coverage. Simulator

normal draw auto-orients starting-house driveway from selected initial direction;

explicitly disclosed ordinary executor effect, not hidden planning. No inference

router imports/probes in new modules; source audit and no-host-probe test pass.



Thirteen focused groups pass (last5.515s): geometry/cursor/time/stock, information

boundary/directed topology, invalid/cap, potential cancellation, mask/no probe,

actor/critic/cursor gradients and distant ranking, masked distribution/evaluate

log-prob equality/save-reload, synthetic bridge/rail/pending cases, naturalfailure/

fallback, all13decoders withfakeprotocol, real140supgrade boundary normalstock,

bounds-stamp cache and realremoval/refund/stalecursor. Expanded decoder fake

initially omitted connectivity fields, corrected testdouble, not production.

Initial6pass,expanded test error then final13pass; no hidden failed verdict.



Final current-source exact replay matches388 input/mask/reward hashes;3 C# command

replay verifications pass. Bounds cache hardened after final sampled trial;

new test and exact-source replay prove parity on recorded histories. Before/after

observations,cursors,masks,stable coordinate/tool identities,schema IDs retained

losslessly sparse. Hash is inputcontext, not full hidden-world identity/clone.

Historical intermediate sources restored/verified against measured SHA256s and

archived alongside current source. No learned-policy gameplay or optimizer updates;

fresh model forward/gradient/save tests only, temporary weights removed normally.



Decision: keep bounded direct interface for#8; close#7's prototype/contract/probe

scope, do not pass#8 or#17. Next direct-compatible runner and actual small learned

construction fixtures with held-out variants and fixed budgets. Old hybrid

train_contextual incompatible; historical synthetic stock failures stayfailed,

not a direct-control verdict. All4protectedweights unchanged. No newprotocol,

teacher/final/reservedmaps, longtraining,remotePCuse,commit/push. Existing exposed

prefixes/replays/tests only; repeated fixtures not independentperformance samples.

Status/index/currentprogress/GitHub#7/#8/#17/tracker updated; all details in

[direct audit](../docs/training/direct-control-audit-2026-11-04/README.md).



## T68 — Run-notice instruction and direct cancel correction, 4 November 2026



User requests next step and advance notice before longer training. Decision046/

AGENTS record that requirement; this is not permission for a longer run. Proceed

#8 with disclosed short fixed pilot only. During integration found T67 explicit

cancel gap: inherited mask excluded wait while cursor choices existed; calling

wait advanced time via invalid-action path and counted rejection. Prior upgrade

test checked reset but omitted zero-rejection assertion. Corrected DirectEnv to

admit wait in all live phases; underlying actionv3-explicit-cancel. Added assertion

and two-phase cancel regression; historical v2 samples remain historical. No

simulator or legacy adapter changed. Generic direct feature dimensions now support

separate lesson subclass; numerical regression exactly preserves62-channel old

initial weights/forward result. Production direct trip/potential reward unchanged.



## T69 — First real-command classroom learning pilot, 4 November 2026



New construction_lessons has actual normal-stock host tile/edge objectives,

2/3explicit sites and Road/draw/wait subset. Goal/site marker channels and observed

remaining6selection horizon,64grid/44global/6resources, separate lesson schemas.

Actor selects tool/cells; success verified from physical infrastructure or both

connection bits, no router. Desired endpoints are classroom instructions, NOT

independent city goal selection, obstacle routing or full-game skill. Binary

physical-success lesson reward, true finite-horizon termination/no continuing

bootstrap; game trip/potential reward logged separately. No production roadbonus.



Predeclared plan before updates: tile/edge×seeds101/202,512steps or30s perrun,

120s totallearning/180s session; nsteps64,batch32,epochs4,lr.0003,gamma/lambda.99,

ent.005. User told budget before start. Fresh models/output, explicit init/action/

worker seeds, eval RNG restoration, fixed initial32/final64fit+64withheld+64erased,

no checkpoint selection/retune/extension. Map1000 even anchors train,2000 odd

withheld, both exposed. No new registered/teacher/reserved/final map access.



Completed4×512=2048selections,128 SB3 epoch counters (not minibatch steps),519

recorded training episode aggregates.35.5031s learning,70.3095s inclusive pilot.

Fit/withheld/erased respectively: tile101 .859375/.75/.53125 FAIL;

tile202 .953125/.921875/.5625 PASS;edge101 .359375/.578125/.375 FAIL;

edge202 .78125/.71875/.3125 FAIL. Initial fit0/0/0/.53125 in same order.

Criteria eachseed fit>=.9/withheld>=.8 plus0rejects/finitechangedparams/reload;

bothseedsrequired. Tile1/2 andedge0/2 means no accepted lesson/#8 gate pass.

All4 checkpoints reload identically on first8withheld cases,0host rejects,

positive parameterL2changes; no old checkpoint promoted/overwritten.



Posthoc frozen instruction shuffle (not selection/newgate): tile101/202 .546875/

.546875,edge101/202 .328125/.28125 withheld. Goal scoring/physics unchanged, only

instruction reassigned, supports goal sensitivity with finite-sample limits.

Saved/reproduced first already-reported withheld success per frozenmodel,4real

command traces; descriptive selection, not unbiased extra performance evidence.

Training summaries not full action/observation trajectories; exact finalmodels,

case seeds,source and evaluation arrays retained. Scripted goal-control physically

succeeds12 test episodes across tasks/partitions/seeds, not actor inputs/teacher.



14direct+4lesson tests pass. Tests cover true horizon/incorrect build, visibility,

erasure/action mask independence, normalcommand stock,maskedlogprob,canonical

feature equivalence,legalcancel. Source/script/plan/results archived; weights

ignored/localonly. All4protectedcheckpointhashes unchanged. No simulator edits,

full-game training,remotePCuse,commit/push or jobleft running. History#7closed

bounded interface remains;#8OPENpartial/failed, not automatically repaired bytime.



Prepared separate proposed4096step/120sperrun×4 (480s learning/600s inclusive)

fresh pilot at unchanged thresholds/settings; NOT STARTED. Generalized runner

help/parse checked only after freezing exact short-run script. It preserves fresh

outputs and marks incomplete budgets inconclusive; no retroactive short-result

changes. Discuss longer run with user before starting per decision046; more

training is a hypothesis, not established remedy. Even a future pass leaves

obstacles/color/service/stock/queues/redesign/unrestricted lessons unproved.

Currentstatus/index/v3progress/GitHubupdated; [evidence/proposal](../docs/training/direct-learnability-2026-11-04/README.md).


## T70 — Approved pilot, user-controlled execution, 4 November 2026

User says sure to longer pilot but requires exact terminal commands and will run
training and return results. Standing instruction now covers ALL training incl
short diagnostics; decision047/AGENTS supersede autonomous short-run practice.
Prepared new approved-manual-only plan4096steps or120s/taskseed,tile/edge101/202,
480slearning/600swall, unchanged hyperparameters/criteria/cases, fresh user-run
output. Existing proposed and short-study files stay historical/unchanged.
Checked plan values, runner syntax, local Python/.NET/host paths and fresh output
absence using no-training checks. No subprocess training, no outcomes, no model
changes. Source/current plan only on laptop, not yet pushed/transferred to PC.
Command and follow-up results path in
[manual pilot](../docs/training/direct-manual-pilot-2026-11-04/README.md).
Status/index/GitHub issue8 updated to awaiting USER execution, not running or
completed. No run authorization implied for future automatic executions.



## T71 — User-run longer classroom pilot passes starter tasks, 4 November 2026



User says done. Read actual manual results locally; no new training launched.

PlanSHA matches approvedplan. Four runs tile/edge101/202 each4096 selections and

256SB3 epoch counters,stopreasonNone,completeassessments. Total16384 selections,

1024epoch counters,246.1585s learning/275.8153s inclusive (within480/600s caps);

individuallearning66.2685/67.5856/57.8098/54.4946s (<120s). Initial fit0/0/0/.53125;

finalfit1.0 andwithheld1.0 all4,64cases each. Erasedtile101 .65625,tile202 .296875,

edge101/202 .34375; variable controls, no exact chance claim.5836 training episode

aggregates; no full mid-update trajectories. Recomputed criteria>=.9fit/.8heldout,

bothseeds,0rejections,finitechangedparameters,reload: BOTH starter lessons PASS.



Read-only review loaded initial/finalmodels: initial0steps/updates/unusedoptimizer;

final4096steps/256epochs,LessonPolicy and allschemaIDs,gamma/lambda.99 correct.

MeasuredL2parameterdeltas reproduce; finiteweights; checkpoint hashes stable.

Re-ran64fit+64withheld cases permodel: all512 episode records exactly reproduce

including command/selection counts and0rejects. Review0trainingupdates; all4

historical protectedhybridhashes unchanged. No promotion or combinedskillclaim.

Executed training source wasn't snapshotted at launch; current source reproduces

results and isarchived, exact historicalsource provenance remains limited.



Posthoc inference-only larger-action probe: same exposed2000 goalcases, sites

widened2/3->84eligibleemptylandcells with visible siteplaneupdated; toolsubset,

goals/horizon unchanged. All4models64/64 successes,0rejects,hashesunchanged.

This extends development evidence, not a new independentgate/final assessment.

Goal markers still provided; edgeadjacent; no obstacle/multistroke/unprompted

goal selection/fulltools learned. Four different policies, no singleagentcombined.

Original short512step failures retained; longer exposure helps these particular

tasks, not universalproof longertraining solves all issues.



Decision: accept restricted markedtile andsingleedge controls;#8remainsOPEN for

broaderobstacle/color/service/stock/queue/wait/networkrevision/combined/unrestricted

lessons. Next prepare those fixtures/contracts and testfrozenmodelswhereuseful;

user launches ALL futuretraining through terminalcommands. No new training,

jobs or schedule from review. Only exposed1000/2000, no newregistered/teacher/

reserved/finalmaps. Smallrawresults/plan/sourcecopiedwithhashes; localweights

keptignored. Currentstatus/index/v3progress/GitHubupdated; no commit/push.

[Review/evidence](../docs/training/direct-manual-review-2026-11-04/README.md).



## T72 — Multi-stroke/obstacle lessons, frozen probes and manual plan, 4 November 2026



User saysgoahead after starterpasses; standing decision047 means preparation/

no-update verification only, give terminalcommand for user training. New

network_lessons adds line/extend/detour using actual normalstock maps1000/2000.

No private future data,stock grants,simulator edits or route suggestions.

Allvisiblecell region,Draw/wait subset; actorsees2goalmarkers/world/cursor/horizon.

Actualbidirectional built-edge traversal is success metric, not actor route.

Reward1physicalconnection else0;18selection truefinitehorizon/no continuing

bootstrap; wrongpartialbuild no longer ends lesson, allows multi-command plans.

Separate networkv2obs/action/reward semantics,same64/44/6 tensors/NNarchitecture.



Fixed fixture perimeter/elbow templates qualify feasible goals and script tests,

never actor waypoints/demos. Extend begins with1normaldraw leg, stock/time/setup

loggedseparately; full detour startswithoutit. First outside-corner qualification

found0trainobstacles because buildings touch playable edge; corrected to free

perimeter targets and two axis-aligned witness elbows, without changingmap.

Initial detour catalog reusedsome goalpairs with different unprovided elbows;

deduped unscaffoldedgoalpairs before trainingplan. Extend differinginitiallegs

remain distinct initialstates. Initialsource/results retained.



Frozenedge101/202 probes32cases/task/partition: line100/100%fit andheld, catalog

238/109 (length2/3fit,4/5held). Extend0/0%fit,31.25/31.25%held,13/50initialstates.

Initial detour0/0fit,3.125/0held with13/50catalog; canonical dedup13/46goalpairs

gives0/0fit,3.125/3.125held. No retroactive overwriting: canonical separate.

Initial28.71s andcanonical13.16s inference probes,0optimizerupdates. Onlyexposed

1000/2000, fixed small repeatedcatalogs, not independent32layouts or freshmaps.



Added explicit actor-only transfer helper: shared actor/encoder copied onmatching

shape/policy; targetvaluehead untouchedfresh,optimizer unused,counters0. No old

critic/optimizer resume across6->18selection changedMDP. Identical-input actor

logits match frozen source; benefitunproved, scratchcontrolrequired. Recordwarm

prior4096source selections/256epochs separately. New user-run trainer captures

exactsource/build/plan/versions/dirtyrevision atlaunch,goal/case catalogs,perstep

action/maskhashes andepisodecosts; initialization/action/worker RNGroles explicit.

Eval preserves Python/NumPy/TorchRNG; fixed initial/final cases, no midselection.

Interrupt/error checkpoints+partial evidence saved; incompletebudgets inconclusive.



5fixture tests pass (18scriptedordinary physical episodes plusmetric/cursor/

horizon/blocking/no waypoint checks);2transfer/runner tests pass. Observed2.991s/

1.964s; no-updatepreflight confirmsbudgets/runtimes/frozen sourceSHA/freshoutputs.

Metadata-only priorcost/runtime additions afterward do not change tested logic.

No modellearn/optimizerstep called. All4protectedweights and2edge actors unchanged.

No remotePCuse,commit/push or newregistered/teacher/reserved/finalscenarios.



Plan nowready for USER launch: extendonly,scratch/actor-warm×101/202,4096steps or

120slearning/run,480slearning/600swall. Thresholds90%fit/80%held and90%line retention

in bothseeds,0rejects,finitechangedparams/reload. Full emptydetour diagnostic

separate, no falsemastery; no automaticextension/promotion. Output/results still

ABSENT, NOT STARTED. Morefulltools/citygoalselection/service/stock/queue skills

remain#8/#17. Status/index/v3progress/GitHub#8/#15/trackerupdated. Exactcommand,

sources,plans/probes/limits: [network preparation](../docs/training/network-lesson-preparation-2026-11-04/README.md).





## T73 — User-run extension gate fails; verified failure analysis, 6 November 2026



User reports run completed, requires notice before changing anything, and

subsequently authorizes recording/diagnosis within current roadmap #8/#15.

New user preference recorded as decision048. No training launched by assistant.

Four runs completed4096 selections each,16384 new total,197.9466s learning,

291.2508s inclusive, no cutoffs/errors. Warm prior4096 selections/seed separate.

Scratch101/202 fit0/0%,held0/0%,line0/0%,detour0/0%; warm fit81.25/98.4375%,

held48.4375/51.5625%,line100/100%,full-detour9.375/34.375%,erased0/0%.

Neither arm meets unchanged both-seed90%fit/80%held/90%line requirements.



Inference-only review independently reproduces512 fit/held records and collects

256 held traces. Fresh initial optimizer/counters, final4096/256, finite changed

parameters, reload equality and no rejected commands verified. Source snapshots,

current source, launch plan/host, both warm sources and4 protected hybrid hashes

match. First review assertion compared tuple/list representations; canonical JSON

comparison fixed only the review harness, then all records match. No learning.



Training episodes include44/249 and44/246 scratch successes, so zero final greedy

success does not mean no training reward. Scratch101 chooses no cell61/64 held;

example Draw/cancel repeats. Scratch202 repeats same3selectionstroke60/64;

warm101 does so21/33 failures,warm2020/31. Observed symptoms, not proven causal

mechanism; warm fit-to-held gap and tiny13fit/50held catalogs limit transfer.

64held samples contain35 unique cases on exposed1000/2000, not independent maps.

No new registered/reserved/final maps, simulator edits, promotion, commit or push.



Engineering outcome: retain failed verdict; #8/#15 OPEN, archive small raw/source/

trace/training evidence and local-only checkpoint identities. Proposed only:

fixed-budget frozen probability/sampling and unique-case geometry diagnosis,

then explain lesson proposal before editing. No lesson/reward/algorithm/budget

change, new training command or next run. Sources and limits:

[review](../docs/training/network-extension-review-2026-11-06/README.md).





## T74 — Frozen action probability and unique-fixture diagnosis, 6 November 2026



User authorizes proposed diagnosis after notice. Predeclared180s cap, four frozen

models ×13fit/50held unique states ×deterministic/one seeded sampled attempt;

504episodes completed52.2387s, zero host rejections/optimizer updates, all final

checkpoint hashes match T73 and unchanged. No training, game/lesson/NN edits.

Fit deterministic/sample counts: scratch1010/3 of13,2020/2; warm10110/11,

20212/12. Held: scratch1010/8 of50,2020/2; warm10126/45,20226/32.

Original64-sample deterministic gates remainfailed; these posthoc unique-case

measurements cannot replace acceptance or claim reliable sampled transfer.



Warm deterministic failures include121/68 topology-unchanged endpoint draws,

zero cancellations; failed first endpoint top probability averages.318/.284.

Sampling finds useful alternatives but large seed variation remains. Scratch101

all50held episodes no topology change,447cancels; scratch202248redundantdraws.

Topology hash covers connections/infrastructure only, not full world. Both warm

models first select a goal in all50cases, which can be valid, not itself anerror.

Fit13catalog lengths1–3, held50 includes6vertical length4cases; both warm1/6 on

length4. Otherlengths alsofail; map/orientation/location/length confounded.

No proven root cause, no inferenceplanner, no reserved/final scenarios.



Engineering proposal only: stratified feasible fixtures with varied positions,

both orientations and fit lengths1–3; disjoint interpolation and separate length4

extrapolation, no silent reuse of held as fresh. Validate coverage/feasibility

before bounded warm comparison with deterministic+sampled metrics, redundant

stroke counts, oldskill retention and priorcost. Explain before lesson edits.

No new budget/run/command or architecture/reward/algorithm change. #8/#15 OPEN.

Archived raw trajectories/probabilities, catalogs, analyses, source, hashes and

issue snapshots: [diagnosis](../docs/training/network-action-diagnosis-2026-11-06/README.md).





## T75 — Varied fixture coverage and bounded user pilot preparation, 6 November 2026



User authorizes next varied lesson preparation. Advance notice given for new

fixtures, then broadened map scope after first physical coverage check. Added

opt-in varied_network_lessons and train_varied_extension, preserving original

lessons/trainer/NN/reward/masks/simulator. First fixed-map1000 pool62selected36

physically valid but thin/missingstrata; archived unchanged as failed coverage.

Broadened to legacy exposed training1000–1005, not newregistered/finalmaps.

Pool1516; selected48fit1000–1002,48same-length layouttransfer1003–1004,

16length4transfer1005;8per horizontal/vertical lengthstratum. Allfit1–3lengths,

bothaxes; split bymap and disjoint unorderedgoalgroup. Differentmap/length

remainconfounded; no claim pure interpolation or freshmapgeneralization.



All112selected physical witness completions pass normalstock,1prefix+1actor

command,0rejects,success/termination/observations/no witnessinfo.4.322s. Fixed

witness only classroom qualification, never actor route. Balanced strata resets,

v2fixture/obs schemas, ordinary18selection binaryconnectivity MDP unchanged.

4dedicatedtests pass8.069s incl RNG/weights/unusedoptimizer preserved on16

inferenceepisodes, repeatedseed/strata/partition checks, budgetextension guard.

No-learning --checkpasses source/fixture/host/checkpoint hashes/freshoutputs.

All4protected hybridweights unchanged. Source/plan/evidence archivedwithhashes.



Prepared USER-only warm101/202pilot from reviewed matchingstarteredge actors,

freshvalue/optimizer/counters,4096newstepsor120s each,240slearning/360sinclusive,

noextension/retry. Prior4096edgelearningsteps each separate. Warm-only feasibility,

not matched causal ablation. Initialallunique deterministic; finaldeterministic+

seededsample,goal-erasedtransfer,line/full-detour/reload with redundantdrawcounts.

Bothseeds need90%fit/80%layouttransfer/90%line deterministic plus checks;

length4/sample diagnostic separate. Outputs/results absent, NO TRAINING STARTED.

#8/#15stayOPEN; no sourcecommit/push or promotion. [Plan and command](../docs/training/varied-extension-preparation-2026-11-06/README.md).





## T76 — Varied lesson USER-run failed gate, sampled improvement verified, 6 November 2026



User reportsdone, authorizescontinuation; advance notice before review/recording.

Two4096selection/256epoch runs finish140.39599slearning/230.19663sinclusive,

8192newselectionstotal, noerror/cutoff. Prior4096edgelearning each separate.

Deterministicfit10/48,5/48; layout10/48,3/48; length4 1/16,2/16; lines32/32both;

full unscaffolded detour0/16both. Erasedgreedy0/48,1/48. Sampledfit45/48both,

layout42/48,41/48; length4 16/16,14/16. Both fail unchanged bothseed90%fit/80%

layout/90%line deterministicgate. No promotion or retrospective sampledpass.



Independent frozenreview exactly reproduces448finalfixture episodes across

partitions/modes/seeds, checks initialunusedoptimizer/0counters,final4096/256,

finitechangedparams/deltas/schema/reload/0rejects. Runtime/current source,plan,

fixture,host,warm-source hashesmatch;4protectedhybridweightsunchanged. Review

180scap, completed;0updates. Added posthocinitialsampledbaseline under90scap,

224episodes,samefixtureorder/samplingstreams:fit32/48,33/48;layout24/48,21/48;

length4 7/16,8/16. Stronger finalsampledperformance not alreadypresent atinit,

but one RNGstream/case and no matchedcurriculumcontrol limitclaims.



Trainingepisodes308/388,295/387successes; deterministiclayoutredundanttopology-

unchangeddraws210/263vs sampled41/49. Topologyhash is not fullworld equality.

Deterministicfit/layout declinefrominit despite sampled gains; simulatorreject

not the cause. Sparsecredit/architecture/selection rootcause unresolved. Maps

1000–1005alreadyexposed development; no newregistered/reserved/finalscenarios.



Engineering outcome:retain failedgate, #8/#15OPEN; proposedonly boundedfrozen

multi-streamsampled reliability/cost/erasedcontrols before prospectively choosing

stochasticexecution or learnedactionrepresentation repair. No trainingplan,

code/lesson/model/algorithm/gatechange or sourcepush. Raw smallrun/source/trace/

baseline/hashes archived; weightslocalonly. [Review](../docs/training/varied-extension-review-2026-11-06/README.md).





## T77 — Multi-stream frozen reliability; best checkpoint/replay requirement, 6 November 2026



User authorizes diagnosis, asks NEXT run savebest towatch. Advancechange notice

before probe/recordingcode.1024frozen episodes89.4439s under180s;0updates/rejects.

48layoutstates×5streams×2goalconditions×2models=960 plus64sampledlinecases.

Normalgoals190/240(79.17%) and211/240(87.92%), streamwins37/40/39/40/34 and

43/45/42/40/41 outof48;17/24cases succeedall5. Erased31/240,41/240;noall5cases.

Sampledlines32/32both. Goalcommandsmean3.3208/3.0083, selections9.9167/8.9667;

erasedcommands5.5833/5.4833,selections16.7333/16.4. Redundantdraws299/269normal.

Correlated repeatedfixtures, notnewmaps; nofinal/reservedaccess orgatepass.

Originalcheckpoint hashes unchanged. No architecture/lesson/reward/mask edit.



Newbest saver +optin recorded runner: declaredfixed48FITcase sampled screens,

step0/every1024atrolloutboundary/finalifbudget;highest success then fewercommands,

tiesearlier; checkpoint/replay pair+hash/version files, final remainsseparate.

RNGpreserved, screeningusesexistingbudget. Bestnotpass; heldscreenrejected.

2no-learningtests pass.019s, ephemeralplan --checkpasses/freshoutputabsent.

No persistentnewtrainingplan,commandissued orsessionstarted. Nextalgorithm/

representation/executionremedy undecided, #8/#15OPEN. Userrequirement049/AGENTS.



Currentseed101 frozenpreview fit-screen48cases saveslocalcheckpoint+exactdemo,

not crossmodelwinner. Native replayPASSseed1000,2commands/2seconds/0trips,

1suppliedprefix+1actorcompletion; goals inmetadata,notnativeoverlay. Viewerexists,

watchcommandprovided, noGUIlaunched. Smallreplay/source/metrics archived, weights

localonly. No sourcecommit/push/promotion. [Evidence](../docs/training/sampled-reliability-2026-11-06/README.md).





## T78 — Relative-position hypothesis and paired manual pilot preparation, 6 November 2026



User sayscontinue; advance notice before explicit learned relativeposition inputs

and controlledcomparison. Hypothesisonly: local5x5cellfeatures/globalpooled16summary

make goal/cursor relations hard tolearn. Not representability impossibility or

provenrootcause. Added relational_lesson_policy/relation_training/newstandalone

train_relation_comparison. Allgoals/cursors alreadyvisible, no teacherwaypoint,

route/distanceprior/actionmask/reward/simulatorchange. Extra6global descriptors,

12cellrelative/presence features;576extraparameters(18735→19311), architecturev1.

Newweightcolumns0, sourceactorcopyexact, freshvaluehead matched baseline seed;

unusedoptimizers/counters0. Priorreviewededge source4096steps/seed, reusedbyarms.



2focusedtests pass1.929s (actoridentity, backwardonlynewcolumngradients, erased

absence, serialization);2saver tests pass.044s;3planmutationguardsrejectchanges.

No optimizerstep/learn called. Pairedinitialactor+critic logits/values agree

bothseeds acrossordinarycommands; realcandidatefit48screen checkpointsave/load,

nativereplayPASSseed1000/2commands/2seconds/0trips. This is INITIAL model behavior,

not newlylearnedskill. lesson_recording addsoptional deterministicmode/accurate

replaymode label; defaultsampledbehaviorpreserved. Historicalarchivesunchanged.

4protectedbaselineweightsunchanged, fixturesidentical, freshoutput/resultsabsent.



PreparedUSER-only baseline/relation×101/202,4096selectionsor120sinsidelearncall

includingbest-screens,480scumulative/600sinclusive; noextension/retry. Existing

48fit/48layout/16length4 fixtures onexposedmaps, originalgate90%fit/80%layout/

90%line BOTHseeds perarmunchanged. Bestfit-only deterministic48case screens

step0/every1024/finalifbudget;success thenfewestcommands/tiesearlier;savebestzip+

exactreplay/versionedpairs, finalstillprimarygate. Sampled/length4diagnostic only.

Incompletebudgetsinconclusive;2seeds/extra576params notdefinitivecausalproof.

Pinnedsource/fixture/host/warm preflightpasses withoutenvironment/learner.



No trainingstarted, algorithmwinner/promotion/newfinalmaps/commit/push. #8/#15

OPEN. Nextuserterminalcommand and boundedpurpose/limits in [preparation](../docs/training/relation-comparison-preparation-2026-11-06/README.md).





## T79 — USER comparison times out; best checkpoints/replays verified, 6 November 2026



User reportsdone; advance notice for record/review only. Rawstatusinconclusive,

TimeoutError('Recording screen deadline'). Baseline101/202complete4096steps each,

82.4475/91.7437sinsidelearncalls; relation101reaches2048steps/128epochcounter,

then2048fitrecordingscreenhits120.0398scap; relation202notstarted.294.231slearning-

callaccounting/400.2844sinclusive,10240newselectionsrecorded. No extension/retry.

Screen/optimizer/host timing notisolated, so slowdown causeunproven. Insufficient

runtime forplannedcandidate workload, not evidence a completedcandidatefailed.



Completedbaselinefinalfit10/48,5/48; layout10/48,3/48, sample42/48,41/48;

line32/32both; unchangedfailedgates. Baselinefinalpolicyparams bit-identicalto

previousvariedfinals. Source/plan/fixture/host/warm hashesverified,4protected

hybridweightsunchanged. Bestcheckpoints/replayhashesverified/finite:baseline101

step2048(128epochs)fit19/48; baseline202step1024(64epochs)fit11/48;relation101

step1024(64epochs)fit19/48. All3exactnative replaysPASS2commands/2seconds,

0trips,seeds1000/1000/1001. Bestnotpassedgate or fullgame; suppliedprefix.

Partialerrorcheckpointfinite/actual2048steps retainedlocalonly; nofinal.zip for

candidate, nofutureseed. Best saving requirementfulfilled despite earlystop.



Bounded180s frozenreview completes528bestfit/layout/lineepisodes; finalpartial

probehitsreviewcap, no budgetextension. Bestfit/commandmeansmatchsavedselection.

Bestlayoutdet/sample counts6/34,15/34,17/29 of48 for baseline101/202/relation101.

Unequal snapshotsteps/candidatebudget, posthocdescriptiveonly. Reviewharness

savedpercaserows onlyatend; timeoutlostthose rows. Consoleaggregates archived,

partialcheckpointperformanceunknown. Rawrun/evidence/checkpoints unaffected.



Engineering outcome:comparisonINCONCLUSIVE,#8/#15OPEN,noalgorithmwinner or

promotion. NextPROPOSED profilefrozenfeature/batchcost andscreeningtime plus

incrementalreviewevidence before anybudget/codechange. No newtrainingcommand,

model/lesson/algorithmedit,finalmaps,sourcecommit/push. Fullraw/source/selection/

replay/hash/limitrecords: [review](../docs/training/relation-comparison-review-2026-11-06/README.md).





## T80 — Runtime profile/repair, durable assessment, prospective manual plan, 6 November 2026



User saysmeh/continue andshows2command/2second/0trip replay withisolatedroad.

Recorddissatisfaction/limitedclassroomscope, not a newuseralgorithmdecision.

Advance notice before no-learningprofile, equivalentalgebra, durablejournals,

lighterrecording andnewtimeheadroom. Frozenprofile90scapfinishes41.37s; initial

weights/optimizer/counters unchanged. Batch32ff+backward .24792/.25008s old

baseline/relation;12case screens6.3659/8.1410s,183selections/3wins each. No exact

attribution ofprevious timeout; variability/measurementlimited. Pythonconv2d

.832/1.253scandidatebatchprofile dominates, relationinputprepnotsolecause.



Newoptin factorizedcontextcellhead preservesallweights/parametercounts, projects

sharedcontextonce, same learnedalgebra/no routes/prior/reward/maskchange.

60sfrozencheckfinishes33.68s;36realobservations/arm,all72argmaxmatch,

maxmaskedlogiterror9.5367e-7;float64output/allparamgradienttestpass.460s.

Batch32ff+backward baseline.23175→.18505s,relation.22711→.20251s(1.25/1.12×),

notendtoendguarantee;somebatch1regressions/noisyCPU. Backwardtiming/testsonly,

NO optimizerstep/learn. Computationschemav1 tagsfloatingreorderlimits; oldfiles

andhistoricalarchivesunchanged,4protectedhybridweightsandprofiledsourcehashesmatch.



Newfrozen_evaluation/reviewCLI journalcompletedcases immediately+atomicsummary,

restoreRNG,preserveactivecase/errors/caps;3faulttests pass.447s inclcleanupfailure,

realcandidate2casejournals work. Newfactorized_training and train_runtime_comparison

optinmatchedarms,12balancedFITscreens at0/every2048/final,screen_case_count/mode,

percase screenjournals, rollout/betweenupdategap/screentiming.2recordingtests

pass.679s;save/load/12casejournal/nativeexactreplay/realassessment smoke passes.

Reviewrowsarenolongeronlysavedatend. Betweenrollouttimeincludesframework,notpure

optimizer. Bestselectionsubsetprospective, not comparabletoold48best rates or

substitution forfullfinalacceptance. Userbest/replayrequirementretained.



PreparednewUSER-only4runs baseline/relation×101/202, same4096selections/run,

240slearncall/960stotal/1800sinclusive. MoreTIMEheadroomonly, no extraexperience

oroldpartialresume. Old10mincomparisonstaysinconclusive. Newcapannouncedbefore

preparation;fullfinal90%fit/80%layout/90%line bothseeds unchanged,sampled/length4

diagnostic. Pinnedsource/fixture/host/sourcecheckpoint/freshpathpreflightpasses,

no learnercreatedby--check; budgetmutationguards.6focusedtests,0trainingstarted.

No sourcecommit/push/promotion/newfinalmaps; #8/#15OPEN. [Profile](../docs/training/runtime-profile-2026-11-06/README.md), [manualplan](../docs/training/runtime-repair-preparation-2026-11-06/README.md).





## T81 — User reportsdone; new local run evidence absent, 6 November 2026



Afteruserdone, read-only search finds no output/training/runtime-repair-comparison-

user-v1 and no expectedresultsdirectory/file. Latest otherresults are priorstudies;

Win32_Process query returns no python.exe atinspection. Exact newrunner --check

passes pinnedsource/fixture/host/warm/budgets/freshpaths, NO learner/training.

Causeunknown:cannotinfer failedtraining, nonexecution or elsewhereexecution.

Need terminaloutput/actualmachine/project before review. Usernotifiedbefore

recording this missingevidence. No code/plan/budget/checkpointchange, no training

or outcome/promotion. #8/#15remainOPEN with lastcomparisoninconclusive.

[Durable evidence](../docs/training/runtime-run-return-check-2026-11-06/README.md).





## T82 — PermissionError evidence arrives; summary writer repaired, 6 November 2026



UserprovidesPermissionError(13,'Access is denied'). Read-onlyinspection nowfinds

v1run/resultsabsentatT81. Rawstatusinconclusive0learningseconds/7.0942swall,

no completedruns;0steps/0epochs/unusedoptimizers ininitial/errorcheckpoint,

parametersbit-identical. Initial48fitcases14successes,49journal lines;completed

summaryand .summary.saving.json identical. Stronginference summarycommit path,

notproven exactlockholder/OSoperation withoutfulltraceback. NoACL/adminchanges.



Advance notice before narrowcodefix: uniqueclosedtemporary, boundedreplace-only

PermissionError retries7attempts/1.26sdelays; permanentdenial preservesoldsummary

andnewtempwithdetailedpaths. Remove duplicate finalsave in frozen_evaluation.

2writerfaulttests pass.020s;3journalfaulttests pass.032s. SAME48initialcases

completewith14successes under30s frozeninferencecap, no learning/weightchange.

Originalfailedattempt/source/evidence preserved;4protectedhashesverified.



Freshv2outputallowlist/plan/sourcepins, no destructiveoverwrite/deletion. Same

4096selections×4,240slearncall each/960stotal/1800sinclusive, best/replay/12case

screens/fullfinalgates unchanged. --checkpasses withoutlearner/env; v2outputs

absent. User launchesretry, NO assistanttraining. #8/#15OPEN; infrastructure

failure notmodelgatefailure. No newalgorithm/game/reward/fixturechange or

promotion/commit/push/finalmaps. [Evidence/fix/command](../docs/training/runtime-permission-repair-2026-11-06/README.md).





## T83 — User thinks v2 done; local evidence still absent, 6 November 2026



Userreportsithinkdone. Expectedv2output/resultsdirectoriesabsent, noPythonprocess

atinspection; latestlocalrun remainsfailedv1. Exactv2 --checkPASS withoutlearner/

environment/training. Actualterminalcommand/output/machineunknown, no newoutcome

inferred. Notifiedbefore recording; needlastterminaloutput before dependentreview.

No source/plan/budget/checkpointchange or traininglaunched. #8/#15remainOPEN.

[Evidence](../docs/training/runtime-v2-return-check-2026-11-06/README.md).





## T84 — USER runtime comparison completes; no robust learner improvement, 6 November 2026



Userreportedrestart,manual --checkPASS then actualrun/done. Expectedv2artifacts

nowexist, supersedingT83missingstate. Advance notice for review/recording only.

Four4096selection/256epoch runs,16384newselectionstotal/1024epochcountertotal,

202.1744sinsidelearncalls/386.1797sinclusive, noerrors/caps, budgetsmet. Runtime

fixesoperationalonthisrun; reboot/load/recording/factorization/timeheadroom

confounded, no isolatedspeedupclaim. Ledger16.20sscreens/109.51scollection/

76.27sbetweenrollouts(update+framework,notpureoptimizer), restsmalloverhead.



Baseline101/202fitdet10/48,5/48;layoutdet10/48,3/48;sampledlayout42/48,41/48.

Relation101/202fitdet13/48,7/48;layoutdet7/48,9/48;sampledlayout38/48,39/48.

Longerlegdet1/16,2/16,0/16,4/16;sample16/16,14/16,13/16,12/16(roworder).

Lines32/32all; fullunscaffoldeddetour0/16all;erasedlayout0/48,1/48,2/48,0/48.

Trainingwins308/388,295/387,238/341,280/365. BOTHarmssfail unchanged90%fit/

80%layout/90%line deterministicbothseedgates. No consistentheldadvantage,

not proofunlearnableorstatisticalarchitectureverdict; no promotion.



Frozen180scap review reproducesALL896finalfixtureepisoderecords EXACTLY with

incrementaldurablejournals,0optimizerupdates. Source/plan/fixture/host/source

hashesmatch,4protectedhybridsunchanged. Freshinitial0steps/epochs/unusedoptimizer,

final4096/256finitechangedparams/deltas/reloads verified.4bestcheckpoint/replay

hashes/steps/finiteweights/nativeexact2commandreplays PASS. Baselinebest2048

bothseeds (3/12,2/12fit),relationbest0both(3/12,2/12). Relationbest pretraining

FORTHISlesson, carriesoldedgepractice; do not showasimprovednewskill. Finalweights

separate.12casebestmetricnotold48metricorgate. Allsmallraw/source/traces/timings/

launchjournals/reproductionrows archived, weightslocalonly. Line/erased/detour

areoriginalmeasuredrunresults, notseparatelyrerunbyreview.



NextPROPOSED optionalfit-only supervisedconstruction probe toseparatepolicy

representabilityfromPPOcredit/actionselection, no deployedplanner; #9/#12branch

onlyifexplained/authorized, notimplementedortrainingstarted. #8/#15OPEN, no new

trainingcommand/algorithm/reward/fixture/gatechange or codecommit/push/finalmaps.

[Review and limits](../docs/training/runtime-comparison-review-2026-11-06/README.md).





## T85 — User-approved correct-example diagnostic preparation, 6 November 2026



Userasksnowwhat; proposedlearncorrecttrainingexamples thenindependentmodel-only

heldlayouts; usergoahead. Decision050 permits narrowoffline-teachingtest, not

deployedplanner orautomatictraining. Advance notice beforecode/data/loss and

300updates×4,120s/run/900sinclusive budget. New fit-only generator/loader,

set-valuedmaskedNLL andmanualsupervisedrunner, preservingarchitecture/obs/

legalmasks/game rewards/simulator/currentfailedPPOverdicts.



48fitfixtures1000–1002×4teacherstates=192; phase48/48/96. Bothorientations of

fixedcompletion physicallyverified96episodes/192commands includingprefixes;

2.5815s under60scap. No model/optimizerlearning incollection. Fitlabels only;

caseIDs matchfit/disjointheld; witness neverobs, masksordinary. Two validfirst

endpoints representedas aSET, not contradictorysinglelabels. No online search/

learnercorrections, no teacheratplay, no newregisteredteacher/final/reservedmaps.

Existingfixturequalificationcost historicalT75, notfreeexpertclaim. Compressed

NPZ106388bytes localignored, manifest/inputhashes/source/fixtures trackedarchive.



Preparedbaseline/relation×101/202 fromreviewedmatchingedgeactors, freshAdam,

300updatesbatch32(50passes/9600examplepresentations/run),.0003lr,gradclip.5,

120s/run/480scumulativelearningcallsinclfitbest/900sinclusive, noextensions.

No PPOlearn/criticloss; fixedvalueheadweights butsharedfeatureschange,value

predictionsuncalibrated; PPO-readyFalse. Actualsupervisedupdates/examplesseen

separate fromnum_timesteps0/_n_updates0; optimizersteps occuronlyUSERcommand.

Bestcheckpoint/replay counterunit=supervised_update, evaluatedFIT12 at0/100/

200/300,tiesearlier;finalweights separate. Fullfinalphysical90%fit/80%layout/

90%line BOTHseeds unchanged, labelaccuracy notgate; assistedlearningnotunassisted

PPO/fullgame/tournamentproof. Optional#9/#12diagnostic selected, broaderworkopen.



3imitationtests pass.124s +2saver regressions.039s; realactorgradientsfinite,

valueheadgradsNone,parametersandunusedoptimizersunchanged. BCtaggedinitialmodel

save/reload/customcounter/nativeexact2commandreplay PASS;12FITscreenepisodes,

zerooptimizersteps.3planmutationguards/preflightpass withpinneddata/source/

host/warmhashes/freshoutputs;4protectedhybridhashesunchanged. NO trainingstarted,

no sourcecommit/push/promotion. #8/#15/#9/#12OPEN. [Manualplan/evidence](../docs/training/construction-imitation-preparation-2026-11-06/README.md).





## T86 — Public high-score/video teaching research, 7 November 2026



User permitsYouTube/world-recordvideos as correctbuildingaction references and

saysgoahead. Advance notice forresearch/records, existingverifiedsimdatasetkept

unchanged. Decision051 records optionalpublicsource direction, no permission

for automaticlearning or uncertifiedvideo labels. Search findscreatorindexed

Zürich113529(2021-08-03),Retroflux2023guide,AliensrockBeijing2021flowseparation,

LA71074discussion(unrecordedstartpercreator),Stantin2020tutorial. Read official

Creativeannouncement/FAQ for mode/version/multiplestrategy context. Claims are

historicalself-reports, not currentcertifiedworldrecords. No videoswatched or

frames/transcripts accessed:directYouTubeopensfail/timeout, indexeddescriptions

only. No inventedtimestamp/actionlabels or leaderboardverification.



Measuredresearchoutcome:5candidatevideos/2officialwrittenreferences catalogued,

0videoactionlabelsadded,0modelupdates/newmaps. Proposed futureannotation needs

continuousbefore/action/after,mode/version/resources/camera-grid reconstruction,

ordinaryrulelocalreplay/quality checks, whole-session/map split and separate

assistance/cost/datasetversion. Sourcehypotheses(separateflows,junctionchoice,

networkrepair) are not universalcodedrules or teacher-at-play. Commercialgame

fidelitystillunverified; no simulator/reward/architecture/trainingplanchange.



Current192fit-state imitationpilot remainsREADY, unchanged, no outputs/results

atinspection. Userlaunchesalltraining; no assistantstep/learn orlongrun. #8/#15/

#9/#12OPEN; no sourcepush/promotion/privategamecapture or videobulkdownload.

[Research/coverage/sources](../docs/training/video-teaching-research-2026-11-07/README.md).





## T87 — Correct-example teaching completes; first-click distinction fails, 7 November 2026



User reportsdone; advance notice for frozen verification/phase analysis/recording.

Four300-update Adam runs,9600examplepresentations each,1200updates/38400presentations

in total.57.324slearning-call/176.026sinclusive, allcomplete/noerrors. ActualBC

updates positive, RL/PPOcounters0 intentionally; valueheadfixed/nottrained,

sharedfeatures change; PPO-readyFalse. Batchorder hashes match acrossarms/seed.



Botharchitectures seed101fitdet10/48,sampled47/48; seed20212/48,47/48. Layout

6/48detall, sample35/48seed101,39/48seed202. Longerlegdet0/16all;sample16/16,

15/16,16/16,14/16 inbaseline101/202,relation101/202order. Line32/32all; full

unscaffoldeddetour0/16all; erasedlayout2/48seed101,3/48seed202. Both fail

unchanged90%fit/80%layout/90%line bothseedphysicalgate, no relativefeaturewin.

TeacherNLL1.767/1.895→~.282, top1validlabels53.65/43.23→59.90/63.02%.



Frozen180sreview exactlyreproduces896finalfixture episode records, teacherNLL/

accuracy and verifies300Adamsteps/counters/finiteness/valuehead/reload/source/

dataset/fixture/plan/host/warm/protectedhashes. No reviewoptimizersteps. Best

updates0(seed101both),200(seed202both), screens3/12,2/12; all4nativeexact

2command/2secondreplays PASS. No new cityplayingclaim.192uniqueeffectiveinputs,

no conflictingduplicate labels. Additional30s-capped teacherstatechoice audit:

tool48/48bothseeds;first10/48,12/48;endpointroadend→goal9/48,13/48;reverse

48/48all. EVERYwrongteacherstateaction is markedgoal already onthe supplied

prefix,38/36firstclick and39/35endpointerrors. This is not a claim allpossible

plans startingthere areillegal or a proof architecturecannotlearn. Validlabels,

warmbias/optimization/conditioning/softsetmass-to-top1 alignment remainopen.



NextPROPOSED only consistentdirection examples (unconnectedgoal→roadend), keeping

alllegalinferencechoices/modeldecisions; not provenfix or newauthorizedrun.

No data/model/reward/architecture/gateedit, newtrainingcommand or promotion.

#8/#15/#9/#12OPEN. Staticlabels onlysuccessfulfitstates, no teacheronheld/eval,

no YouTubeactions/newfinalmaps/commit/push. Raw/source/update/screen/reproduction/

audit/replay records archived; weights/NPZlocalonly. [Review](../docs/training/construction-imitation-review-2026-11-07/README.md).





## T88 — Consistent-order teacher preparation, 7 November 2026



Userauthorizes proposedgoal-first thenroad-end diagnostic; advance noticebefore

newdata/runner and15minceiling. Decision052. Derived144FITstates fromold192,

retainedsource0/1/3perfixture, firstcelltarget narrowed to unconnectedgoal.

No runtime teacher/selector/strategicmask. Originalobservations/resources/masks

identical; all48sequences physicallyreplayed,96normalcommands, reward1/actual

connection/no rejects. Source labels werevalid; simplifying order is hypothesis,

not a proven objectivebug or modelcapacityverdict. Generator60scap,no learning.



Newcanonicaldataset/loader+separatemanualrunner, existingarchitectures/actorloss/

sourceactors/freshoptimizers/valueheads unchanged.300supervisedupdates×24examples,

50passes/7200presentations/run,4runs total28800. Comparedtoold32/192/9600,

coverage/phaseweighting/batchsize changed; no pureloss-only or equalexamplecount

claim. Same two architectures/seeds,12fitbest0/100/200/300 plusfullphysical

90%fit/80%layout/90%line bothseedgates.120s/run/480stotal/900sinclusive, no

extensions/autoRL. PPOcounters0/BCupdateunits/PPO-readyFalse preserved.



Direction/lineage/mask invariance test passes.177s, realactorgradientsfinite,

valueheadno gradients,parametersunchanged/optimizerunused; initialcanonicalmodel

save/load/nativeexactreplayPASS(2commands/2seconds),12FITscreenepisodes.3plan

mutationguards/preflightpass withsource/data/host/warm pins andfreshoutputs.

4protectedhybridweights unchanged. NPZ ignoredlocalonly; smalllineagemanifest/

fixtures/source/checks archived. NO TRAINING STARTED or codecommit/push/promotion/

newfinalmaps. #8/#9/#12/#15OPEN. [Manualplan/evidence](../docs/training/canonical-imitation-preparation-2026-11-07/README.md).





## T89 — Canonical teaching completes; first-click distinction remains weak, 7 November 2026



Userfirstranoldteachercommand, overwriteguardcorrectlyrefused; screenshot/

clarificationredirectedtofreshcanonicalcommand, oldstudiespreserved. Userthen

reportsdone; assistantreviewresumed afterchatlimitwithoutrestarting/extending

frozenchecks. Four300supervisedupdates×batch24,7200examples each/28800total,

50.719slearning-call/174.317sinclusive, allcomplete/nocaps/errors. PPO/RLcounters

0 intentionally; Adam300, unchangedvaluehead/sharedfeatureschange, PPO-readyFalse.



Allfourfitdet5/48/layoutdet7/48,line32/32;sampledfit48/48,layout36/48(seed101)

or39/48(seed202);longerdet0/16,sample16/16all;unscaffoldeddetour0/16all.

Botharmsfail unchanged90/80/90BOTHseedphysicalgate. Labelaccuracy101/144=70.14%

all, NLL1.967/2.033→.236–.245; previous192-state labelaccuracy notcomparable.

No measuredarchitecturegain or canonicalorderfix. No newlearnedskillpromotion.



Frozen180sreview exactlyreproduces896finalfixture episode records plus teacher

metrics; source/plan/dataset/fixture/host/source/protectedhashes,counters/Adam/

valuehead/reload/finiteness verified,0reviewoptimizersteps.144uniqueinputs/no

conflictingduplicates. Choiceaudit30scap:tool48/48,first5/48,end48/48all; every

43firstclickerrors selectsmarkedgoalalreadyonprefix. Conditionalendpoint/mask

success doesnotprove independentunderstanding. Allbestupdates0/pre-existingedge

skills,4nativeexact2commandreplaysPASS, final300weightsseparate.



Additional30sFIT gradientaudit(autograd.grad,NO step/parameterchange) tests shared

cellheadfirst/endloss gradients:cosines+.774,+.650,+.737,+.606. Noaggregate

oppositionatfinalweights; rejectsimpleopposing-gradientexplanation here, not

alloptimization/conditioning/representation hypotheses. Firstnorms.045–.053,

end.167–.176, not proofcause. NextPROPOSED first-click-onlylearnabilitydiagnostic

withtrace/retention/fullphysicalchecks, notnewmodel/code/run/approvedbudget.

#8/#9/#12/#15OPEN; no inferenceplanner/strategicmask, sourcecommit/push/promotion/

newfinalmaps. Raw/source/journals/audits/replays/limitations archived, weights/

NPZlocalonly. [Review](../docs/training/canonical-imitation-review-2026-11-07/README.md).





## T90 — Objective viability assessment, 7 November 2026



User requests extremeobjectivity about projecthope. Informedbefore recording.

Assessment: plausible researchproject, presentmodel/trainingrecipe unvalidated

and notclose to demonstratedfullgamecompetence; no credibleprobability/timeline

fromavailableevidence. Currentfirstclick5/48onFITlabels,layout7/48/full-detour0/16,

failedgates vspositive restrictedstarter/sampled/loss/update evidence. Stochastic

execution canbevalid; a greedycriterionfailurealone isnot proofprojectimpossible.

Reproduciblepipeline value mustnotbeconfusedwith improvedplayingability.



Processcriticism: shouldhaveisolated first-click overfit earlier; too many

feature/curriculumchanges relative to capabilityprogress. Proposedgo/no-go:

timeboxedtinyFITbatch correctness/overfit audit, then48FIT/transfer; diagnose/

pivot pipeline ifbasicfit can'tbecleared, notautomaticscale/videoingestion.

All recommendations/proposals, no architecturedecision, learningbudget, model/

code/reward/fixture/gatechange, training, sourcepush orpromotion. Userlaunches

alllearning. [Evidence/assessment](../docs/training/project-assessment-2026-11-07/README.md).





## T91 — Focused first-click diagnostic prepared, 7 November 2026



User accepts T90 next step and requires critical self-review throughout this

chat (decision053, AGENTS). Informed before code/document changes. Engineering

choice: one-case then independently reset four-case conditional FIT overfit,

baseline architecture, seed101, current canonical baseline101 final actor versus

scratch, fresh optimizers. Post-hoc cases0/1/2/4 from known wrong FIT choices;

no representative sample, held map, video labels or runtime planner.



Fixed500 updates/45seconds per stage,180seconds summed stages/300seconds run-loop

budget; check every25 plus final; fit requires all greedy correct and target

probability>=.99, reload agreement. Four-case stage only if that initialization

fits one case. Stage clocks include recordings; cooperative checks cannot

hard-kill blocking operations. No automatic extension. Up to2000 Adam updates /

5000 presentations across all stages, not PPO. Warm prior300BC/7200presentations

plus4096older edge PPO selections explicitly retained. Fresh value head/fixed

head parameters, changed shared features possible, PPO-readyFalse.



Measured preparation checks:4 tests PASS, including visible/legal labels,

actor preservation/fresh Adam, finite backward gradients with unchanged weights,

zero-update best checkpoint reload/hash and exact native replay verification.

Pinned source/data/actor/host/fresh paths preflight PASS. No optimizer step or

learning executed. Native demo may fail despite conditional fit; best criterion

explicitly conditional FIT, saves checkpoint/replay/step/hash with no game-gate

claim. Final evaluated weights also considered for best (avoids unscreened final

improvement at clock boundary). Initial/final/error files preserved by runner.



Self-criticism: basic memorization should have been isolated sooner; this probe

cannot establish generalization, full-policy behavior, correct-game fidelity,

or project success probability. Failures require mechanism debugging, not an

unsupported declaration that the architecture/project is impossible. Positive

prior gradient cosines do not support our earlier opposing-gradient hypothesis.

No broad training/scaling, promotion, source push or gate closure. Local-only

weights/data/host are hash-pinned, not backed up by source archive. User command,

prospective interpretation and checks: [preparation](../docs/training/first-click-overfit-preparation-2026-11-07/README.md).



T91 coordination: GitHub #8 updated and remains OPEN; exact issue body archived.

Other roadmap issues unchanged/open; no source commit/push. Exposure ledger

records FIT-only preparation/no optimizer updates.





## T92 — Autonomous execution authorization and first-click launch, 7 November 2026



User explicitly supersedes manual-only execution until further notice; decision054

and AGENTS updated after notice. First experiment retains T91 fixed one/four FIT

cases, warm/scratch, seed101, 500updates/45s perstage,180s summed/300s run-loop

budget. No automatic extension. New launch plan preserves original preparation;

runner metadata now honestly identifies assistant execution. No outcome inferred

before completion. Source branch mohammad, dirty working tree; binary artifacts

local-only. Results and review to follow in autonomous-first-click archive.



T92 results: completed13.85s total/12.03s stage clocks. Warm1 fits25updates

(.9922), warm4 fits50updates (min.99096), scratch1 correctgreedy but.98338

after500updates: fails fixed.99criterion; scratch4 skipped, no extension.

Frozen review: warm4 first22/48,end27/48,tool48/48; physicalFIT15/48,

layout9/48,longer3/16, versus sourceFIT5/48/layout7/48. Endpoint retention

regressed from48/48. Warm1 first22/48,end48/48; no complete-policy gate pass.

All3best hashes/native replays verified. Results archived under autonomous-first-click.



## T93 — All-case first-click fit and joint retention diagnostic, 7 November 2026



After notice, new paired101/202 baseline experiment on existing144FITstates.

Stagefirst:48firstclick states fullbatch; stagejoint:16random distinct examples

perphase each update, gatedonall48first>=.99/allcorrect. Joint initializes

from own firststage FINAL actor with freshAdam/valuehead/counters; fullsource

lineage retained. Eachstage1000updates/120s,4stagesmax4000updates/192000

presentations,900srunloop cooperativecap including finalization/screens.

Existing architecture/legal masks unchanged, no PPO. First best usesconditional

FITmetric/replay; jointbest usesfixed12FITphysicalscreen/replay, tiesearlier.

All-phase FIT and existingphysicalgates reviewed separately, no heldselection.

Passing conditionalfit doesnot establishphysicaltransfer. Planned staging is

engineeringchoice, not provenremedy; only48cases/2legacy-trainedseeds.



T93 completed114.106s runloop: bothfirst200updates/~10.6s andjoint800updates/

45.0/44.3s fitall144teacherstates withminprob>=.99. 2000newupdates/96000

presentations total. Frozenreview49.69s, all4Adam/counters/metrics/hash/native

best pairs verified: finalbothFIT48/48, layout36/48,37/48 (75%,77.08%),

longer15/16both, line32/32both; fullunscaffoldeddetour0/16,4/16.

BestFITselected300both, layout34/48both; notallowedselectfinalonheldscore.

Erasedgoals0/48both. Original80%layoutgateFAILS; fitlearnability nowpositive,

no broaderissueclosure/promotion. This changes our viewofarchitecturefit,

notproofcurriculumcausedgain: updates/batches/order/source differ fromT89.



## T94 — Matched-budget joint-practice control, 7 November 2026



After notice, compareT93staged200first+800joint against200joint+800joint,

samecanonicalfinalsource, seeds101/202, lr.0003,48batch, freshoptimizer/value

head/seedreset at200, samejointstageRNG. Eachstage120s,900srunloopcap;

fixed1000totalupdates/48000presentations perseed, no earlyfitstop, no extension.

Physical12FITbest screens initial/every100/final andnativepairs; heldonlyreview.

This post-hoc control isnot prospectivelyrandomized evidence and screening

frequency/metrics differs duringprelude; learningexamples and reset matched.

Question: isfirst-onlypriming necessary, or doesadditionaljointpractice suffice?

No architecture/legality/reward/simulator change or newmap access.





## T95 — Broader FIT-only coverage prepared, 7 November 2026



After notice, expand eachof6axis/lengthstrata8to24 ordinaryconstructions,

144cases/432canonicalteacherstates. Sameexposed1000/1001/1002 trainingmaps;

old48exactlyretained; layout1003/1004 andlonger1005 copiedunchanged, no

developmentteacherstate. Deterministicexistingroundrobin/SHAorder, nofailure-

cherrypick. Qualificationandall144physicalcompletions/288normalcommands

verifiedin6.220s,432uniqueinputs/no conflictinglabels;0updates.

Plan: bothT93declaredfinalFIT-fittedsources, freshAdam/valuehead/counters,

16perphasebatch48, upto1500updates/180seconds perseed,900srunloop.

Best36predeclaredFITcases (6perstratum, old/new) at0/every250/final, paired

checkpoint/native replay/hash. Screens now36not12; metricnotdirectlyequal.

Up to3000updates/144000presentations, noextension. Goal: coverage/retention

notfullrouting; ordinarymasks/NN/productionreward/simulatorunchanged.

SourcesselectedasfixedFIT-fittedendpoints, notbydevelopmentranking.



T94 completed123.289s; 2000updates/96000presentations total.

ControlfinalFIT28/48,48/48;layout21/48,35/48;longer8/16,15/16.

All4source/data/Adam/teacher/hash/native pairs checked; frozenreview

60.158s/0updates. Stagingworkedboth vscontrol1/2; supportive

limitedevidence, notnecessary/universallysuperior ormechanismproof.



T95 processself-review: launchedpilot while lastread-only unit check still

running ratherthanwaitingforcompletion. Testpassed10.618s; do nottreattimings

ascontrolledperformancecomparisons. No testoptimizerstep. Pairedpilotthen

fitall432teacherstates in500updates each; physicaloutcomeawaited.



T95 finalreviewcompleted60.987s/0updates,1440episodes. BothFINALFIT144/144,

oldFIT48/48,layout47/48,longer16/16,line32/32; sampled144/47/16 successes

of144/48/16. Erased0/48both; legacyfull-detour6/16,9/16. BothFIT-selected

best250 achieve144/144FIT, layout46/48,47/48,longer16/16. Originalscaffolded

90/80/90bothseedsubgatePASS, notfullissue8/fullgame. Best/FINAL separately

preserved; no development-selected promotion. Protected4hybridmodelsunchanged.



## T96 — Empty-start full-route readiness audit, 7 November 2026



After notice, opt-in zero-scaffold class and explicitschema; ordinaryDraw/wait/

stock/18selectionhorizon/physicalconnectivity. ExistingextendedFITgoalpairs

canonicalized/deduplicated before futureteaching; reversedgoal/elbowvariants

wouldcollapse once roadscaffoldremoved.48FITwitnesssequences/96commands

verified,288uniqueinputhashes/no contradictorylabels. No dataset ortraining

created.8.208s auditunder180scap. FrozenFIT-selectedexpandedbest250 models

freepolicy34/48,35/48 (~71/73%), zero setup/forcedactions. FIT-onlydiagnostic,

notheld oroptimalityclaim, differentcatalogfromold16legacydetour.

Two freepolicyexamples capturedseparately/nativeverified/checkpoint-hashlinked.

Full-routegateNOTpassed; nextdraftteaching+priorrehearsal hasno runner/corpus

yet andisNOTEXECUTABLE. No PPO/fullgame/newfinalmaps/promotion/sourcepush.

Decision055 and full-route-readiness archive.


T92–T96 wrap-up: GitHub1/8/9/12/15updated/allOPEN, exactbodies archived.
Currentstatus/index/roadmap refreshed; protected4hashesunchanged. Separate
BESTlinecheck32/32both passes. Episodecountcorrected1440expandedreview
(old48subset derived, not96extra). Windowslocalehistoryappend punctuation
repairedtoUTF8, fivebytes/before-afterhashes recorded; no findingchanged.
No sourcecommit/push or productionpromotion. No full-route training started.


## T97 — Empty-start teaching/rehearsal ready for manual launch, 7 November 2026

Usercanrunagain; acceptedmanualworkflow restored after change notice, decision056/
AGENTS supersedes temporaryovernightassistant-execution permission. No learning
launched. New opt-in runner/dataset/evaluator, originalsimulator/masks/NN unchanged.
48fullFITroutes physically reverified96commands/0setup/rejects;288newteacherstates
+432byte-identicalextensionrehearsal=720uniqueinputs/no conflicts. FITmaps1000–1002
only;58canonicaldevelopmentwitnesses physicallyverified without retainingteaching
states. No new/finalmaps. Masks enforce ordinarylegality only, no runtimeteacher.

FourtestsPASS3.908s: priorarrayretention/FITonly, balanced96batch, immutable
budget/gateguards, actualactorcopy/freshunusedAdam/finitebackward/unchangedparams/
valueheadnograd/zero-updatebestserialization/nativeexactreplay. Preflighthash/
freshpathPASS. No optimizersteps; no trainedoutcome inferred. Labelschooseone
validcorner/order; physicalfreeplaygate remains independentoflabelaccuracy.

Paired101/202continued FIT-selectedbest250actors, freshAdam/valuehead/counters,
1000updatesor180s each/360summed/900runloop, batch96 (8six-selectionroutes+16prior
statesperphase), lr.0003/clip.5. Up to2000updates/192000presentations. Earlyfitstop
all720greedycorrect/eachtarget>=.99 at250updatescreenpoints; physicalgate separately.
No extensions; cooperativecaps/blocking/startuplimits explicit. BestFIT12fullcases
at0/250/500/750/1000/finalnewstep, highestsuccess/fewercommands/tiesearlier,
checkpoint+native replay/update/hash, initial/final/error separate.

BOTHbest+finalmustreach fullFIT90%,full-layout80%,priorFIT90%,prior-layout80%,
line90%,0rejects,BOTHseeds. Longerlegsdiagnostic; preservesoldretentiongate and
isstricterthanfinalonly. Existingdevelopmentalreadyexposed, notfinalgeneralization.
Valueheadfixed/sharedfeatureschange/PPO-readyFalse; no PPOlearning/game reward
change. Testsandno-updatequalificationonly; output/resultsabsent, weightsuntouched.
Source/plan/smallmeasurements archived, binarydataset/weights/host localonly.
[Preparation/command](../docs/training/full-route-preparation-2026-11-07/README.md).
No sourcecommit/push,promotion, broadissueclosure or trainingauthorizedbysetupalone.

T97coordination: GitHub1/8/12/15updated/allOPEN; exactbodies archived.
Source/artifact/snapshot hashes reverified, output/resultsabsent, nolearning.
Currentstatus/index/roadmap/AGENTS reflect manualexecutionagain.


## T98 — USER full-route teaching verified: transfer gate FAILED, 7 November 2026

User reportsdone. Beforechanges informed review/documentation/no newlearning.
Both1000supervisedupdates/96000examples complete,249.357sstageclocks/
311.693srunloop,within180/360/900limits,no caps/extensions/errors.2000updates/
192000presentations total,0PPOupdates. FinalfullFIT47/48,48/48; layout25/44,
30/44 (56.82%,68.18%), longer9/14,12/14. PriorFIT144/144both,priorlayout
48/48,47/48,line32/32both;0rejects. BOTHseed/BEST/FINALgateFAILSfull-layout80%.

BestFIT12screen-selected750both,12/12/mean2commands, pairedhash/nativeexactPASS.
BestfullFIT48/48,47/48;layout25/44,26/44;longer10/14,13/14;prior144/144/
47/48/line32/32both. BestnotallFIT/developmentwinner; finalweights separate.
No retrospectiveheldselection/promotion, oldextensionpassretained.

ReviewfirstattemptfailscoordinatePython-tuplevsJSON-list equality,notactor
behavior: actual32linecases exactlymatchafterJSONnormalization. Failedattempt
preserved (reviewsource reconstructedfromsinglelinefix,notlaunchsnapshot).
Freshv2verifiedALL1320originalepisoderecords EXACTLYin59.607s/180scap,0updates;
teacherinitial/final/counters/Adam1000/freshinitialunusedoptimizer/actorcopy/
finiteparams/fixedvaluehead/reload/source-data-host/checkpoint/protected4hashes
checked. Sharedfeatureschanged/PPO-readyFalse; canonicalteacher717/720both,
not physicaltransfer evidence. No reviewoptimizersteps.

Frozeninitial comparison (separate60scap/184cases) FIT34/48,35/48,layout25/44,
32/44. ThusnewtrainingimprovesFIT, notdevelopment:seed101unchanged,seed202
regressed32to30. Thisnegativefindingmustnotbehiddenbytrainingaccuracygains.
Hypothesescoverage/representation/canonicalteachingbiasunresolved. Actualtwo-leg
geometry recomputedforanalysis; inheritedscaffoldgeometrycanbestaleaftergoal
normalization (notpolicyinput, notusedbyuniformteacherbatch/forced-caseeval).
Correctbeforefuturestratifiedonlinesampling.48of124availableFITgoalpairsused.

NextPROPOSED failure-trace/actualgeometrydiagnosis before choosing broaderFIT
coverageorrepresentationchange; no newtrainingcommand/job, algorithm/gate/
reward/simulatorchange, finalmapaccess, promotion, sourcecommit/push. Binary
weights/data/host localonly; raw/source/metrics/journals/replays archived.
[Verified review](../docs/training/full-route-review-v2-2026-11-07/README.md).

T98coordination: GitHub1/8/12/15updated/allOPEN, exactbodiesarchived.
Currentstatus/index/roadmap refreshed; no sourcecommit/push/promotion/newlearning.
Failedreview andsuccessfulv2review preserved separately with smallfilemanifests.


## T99 — Frozen full-route failure diagnosis and targeted proposal, 7 November 2026

User approves inspection after T98transferfailure; advance notices state frozen
traces180scap, one-actiondiagnosticinterventions90scap, unusedFITprobe90scap.
No training/optimizersteps, NN/mask/reward/simulatorchange or newlearningcommand.
Four INITIAL/FINAL×101/202actors traced48FIT+44development each:368freeepisodes,
29.762s, everycase outcome matchespreviousfixedresults; top-probs/phase/cell/
actualtopology/strokehistory archived. Actorinputs/masks unchanged byoffline
both-elbowtemplateclassifier; sourcehashes matchT98andunchangedafterexecution.

FINALdevelopmentfailures19+14=33case-modelpairs (not33distinctlayouts): allfirst
strokesstartatgoal/outsidefeasibleaxis-elbowlegs, allrepeatsame directedstrokes,
83/64unchangedtopologydraws,82/64repeatedstrokes,0waits/zero-lengthdraws/rejects.
Mean initialtemplateendpointmass onfailures.925%/1.485%. Counterevidence:
26/55successfulpairsusetemplatefirstleg,29succeedindirectly; templatefamily
isnotexhaustiveproductiveactions, cannotcallalloff-templatechoiceswrong.

Posthocselectedfailureinterventions99episodes/10.098s: control0/33success,
replacefirstendpointonceandfreeactor31/33(18/19,13/14), replacefirstunchanged-
drawendpointonceandfreeactor21/33(11/19,10/14). Exactly1changedlegalactionper
assistedcase,0rejects/weightsupdates. Assisted/diagnosticonly, NOT model-earned
performance, no developmentstates/labels addedtoteaching. Localizesfirst-leg
choiceandrecoverybehavior; doesnotidentifyrepresentation/coverage mechanism.
31/33failedpairs alreadyhavegoaloffset representedinFIT; simplemissingoffset
explanation unsupportedasmaincause, obstacle/contextcoverage stillopen.

UnusedFITworldprobe:canonical124goalpairs fromexisting144extensionFITcases,
old48exactlymatched, other76on1000/1001/1002 qualified76normaltwo-legwitnesses/
152commands,0setup/rejects. FrozenFINAL62/76,68/76success; all14+8failures
(15distinctcases) showunchangeddraws andoff-templatefirstlegs.10.021s,0updates,
no teacherbinarycorpusgenerated. Notfreshheld-outgeneralization; legacytraining
worldsalreadyexposed. Sixfreefailure/successnative replays exactPASS.

NextPROPOSAL:matched-budget broadercleanFIT vsbroaderclean+verifiedoff-trajectory
recovery, priorrehearsal/sameinit/optimizer/batches andbothseeds. Collectsource-
specificFITonlytrajectories; verifyordinaryremainingstock/connectivity, avoid
teachingalreadyconnected/no-progresslegs, hashduplicate/contradictorylabels.
No development/interventiondataforteaching. Report clean/correctionexposure
tradeoff; keepphysical90/80/prior90/80/line90/BESTFINALbothseedgates. Draftonly,
no dataset/runner/budget/command issued. No architecture/rewardrestart or
strategicno-opmask justifiedbydiagnosisalone. CurrentgateFAILS/oldskillsretained.
[Traces/evidence/proposal](../docs/training/full-route-diagnosis-2026-11-07/README.md).

T99coordination:GitHub1/8/12/15updated/allOPEN; exactbodies archived.
Final4currentactorhashes reverified unchanged, native6replaysPASS.
Source/measurement/report/draft smallfilemanifestverified; no training/sourcepush.


## T99 — User-requested complete technical audit, 7 November 2026

User explicitly requests independent investigation, no source/architecture changes or learning, and approval before implementation. Audited local mohammad HEAD a652042 plus pre-existing dirty/untracked work; all63reachablecommits inventoried. Intended documentation-only changes announced. No install/build/train/optimizer/test-suite/commit/push/externalmessages.

VERIFIED fresh trusted-local checkpoint inspection: latest FactorizedLessonPolicy18735parameters,12changedtensors, Adam1000,96000examplepresentations each,0PPOsteps/updates, valueheadunchanged,ppo_readyFalse. Latest runner supervisedNLL, whereas earlier runners invoke actual installed MaskablePPO with full collection/advantage/clippedloss/critic/entropy mechanisms. Historical candidate512/signal32 router persists separately; latest direct classroom is plannerfree but goalconditioned/Draw-waitrestricted.

Frozen no-learning45secondbudget completes88developmentepisodes in6.295s:10125/44,20230/44,0rejects. Native best101replayPASS seed1002/score0/2seconds/2commands; not fullgameproof. Archived FIT47/48,48/48; initialdevelopment25/44,32/44; thus no demonstrated generalizationgain, bothgatesfailed. Current source untracked; HEADaloneinsufficient. Historical hybrid239.0vs236.4selecteddevelopment remains weak/nonindependent evidence. SUMO mapping/learningtransfer UNKNOWN; officialSUMOdocumentation consulted only.

Full12sectionreport, evidenceledger, equivalentreadonlyscript, exactselectedstdout, git/history/artifactindexes preserved at ../docs/training/complete-technical-audit-2026-11-07/REPORT.md. Options/roadmap/protocol are PROPOSALS, no researchdecision implemented. No PDFs/plots generated; historical reports unchanged, curve/artifact sources indexed. Binaryweights/data/host remainlocalonly. Audit limitations explicit: no fullsuite, cleanmachinebuild, fullhistoricalrescore or finalholdout. Await userreview/approval.


## T100 — Professional audit PDF delivered, 7 November 2026

USER asks audit as professional clear PDF. Intended documentation-only conversion announced; PDF skill used with bundled runtime, no packages installed. Existing T99 findings preserved, 12sections, linked contents/bookmarks, vector architecture/training diagrams, readable repeated-header tables and page numbering. 30pages generated; allpages rendered/visuallyreviewed, dense options/evidence enlarged; escapedHTML/linebreaks corrected before final render. pypdf verifies30pages/12bookmarks/keyfindings, archive/outputbytesidentical. PDF_QA/source/hashes/buildscript retained in ../docs/training/complete-technical-audit-2026-11-07/. Historical report text unchanged. No new experiments/inference/training/sourcearchitecturechange/commit/push. Await researcher approval as before.


## T100 — Matched clean/recovery comparison ready, 7 November 2026

User approves T99proposal conditionalonexistingplan. Advancechangenotice given;
within#8directconstruction/#12offlinecorrections/#15retention, decision057.
No assistantlearning. Broaden124FITgoalpairs (old48retained),744cleanstates+
432unchangedprior; actualcanonicalgeometrymetadata corrected,newbenchmarkold
44layout/14longer unchanged. Original288clean/432priorbyteidenticalverified.

Source-specific frozenFIT-selectedbest750rollouts124perseed (notT99FINALactors),
110/124,115/124source successes. All14/9source failures replayedfrom exact
firstcommittedstroke prefixhash; offlineexpert skipsalreadyconnectedlegs and
verifiesnormalresourcelegalconnectivityprogress/fullcompletion.14recoveries/
78statesseed101,9/48seed202,0reject/contradictoryduplicates;1254/1224unique
inputs includingclean/prior.124cleanqualifiednormalepisodes248commands;42repair
commands across23prefixreplayepisodes, no development/interventionteacherstates.
Collection23.807s under240s preparationcap,0optimizerupdates. BinaryNPzlocalonly.

Newpaired clean/recovery×101/202 USER-run plan: samebest750actors/freshAdam/
valuehead/counters, NLL/lr.0003/clip.5,96batch. Clean48canonical+48prior vs
recovery24canonical+24correction+48prior; pairedsame24clean and48prior samples,
phasebalanced, distinctRNGstreams.1000fixedupdates/180s EACH,720ssummed/
1800srunloop, max4000updates/384000presentations, noextensions/earlyfitstop.
Smallcorrectioncorpusheavilyreused, riskoverfit; matchedtotalbutcleanexposure
halvedincorrectionarm. Report actualexposure/cost, notpurefree-extra-data claim.

FIT12screen6old+6expanded at0/250/500/750/1000/finalnewstep; nativebest/replay/
step/hash,initial/final/error. Samecriterionhighestsuccess/fewercommands/tieearly,
no developmentselection. BOTHbest/FINAL andBOTHseeds mustpass124FIT90%,old48
FIT90%,full-layout80%,prior144FIT90%/48layout80%,line90%,0rejects. Longer14
score diagnostic. Perarmgatepassnotstatisticalsuperiorityproof, no overallwinner
criterion inventedfrom2seeds. Cappedruninconclusive, no unequal-exposurewinner.

Fiveunit/integrationchecksPASS4.763s: byteidentity/FITonly, matchingbatchallocation/
no clean-armcorrectionrows, guards, actualone-legskiprepair, matchedstate/fresh
unusedAdam/finitebackward/unchangedparams/0updatebestserialization/nativeexact
replay. Bothseed matchedpolicystarts/counters/optimizers checked; pinnedsource/
artifact/freshoutputpreflightPASS. No optimizerstep/learning/modelchange beyond
newopt-in tooling/data. Originalarchitecture/simulator/masks/reward maintained;
criticheadfixed/sharedfeatureswillchange/PPO-readyFalse,no PPOlearning.

Source/plan/collection/checks smallarchive; weights/data/hostlocalonly. Outputs/
resultsabsent, no sourcecommit/push/promotion/finalmaps/broadissueclosure. Existing
T98fullroutegatefailed/oldskillsretained; hypothesiscorrectionbenefit unproven.
[Manualcommand/evidence](../docs/training/recovery-comparison-preparation-2026-11-07/README.md).

T100coordination:GitHub1/8/12/15updated/allOPEN; exactbodiesarchived.
Source/artifact/snapshot hashes verified, output/resultsabsent, nolearning.
Currentstatus/index/roadmap ready; no sourcecommit/push or promotion.


## T101 — Existing-output guard after completed USER comparison, 7 November 2026

User pastesFreshoutput/resultsrequired traceback. Beforechanges informedread-only
inspection/preserveartifacts/no learning. Bothpaths contain completed4runT100
results, statuscompleted/errorNone, each1000updates,4000total/384000presentations;
539.754sstageclocks/712.925soverall(11m53), allwithin180/720/1800caps. A later
launchguardblocks beforelearner/outputmutation. Exactreason command reissued
unknown; do notinventfailure/retrycause or deletefinishedoutputs. No rerun needed.
Frozenverification andsmallarchive inprogress; no newtraining/sourceNNchange.

T101verificationcomplete:3248originalepisode records EXACTLYreproduced in181.896s
under240sread-onlycap,0optimizersteps.4bestZIP/replayhash/nativepairs verified;
source/data/host/teacherinitialfinal/Adam1000/counters/freshinitialunusedoptimizer/
pairedactor-valueheadstarts/finiteness/fixedvaluehead/protected4hashes checked.
All4000samplebatchhashes independentlyreproduced, exposurecountsactualmatched.

FINALclean101/202:fullFIT109/124,114/124;oldFIT44/48,46/48;layout31/44both;
longer11/14,10/14;prior144/144and48/48,line32/32both. FINALrecovery101/202:
fullFIT106/124,108/124;oldFIT42/48,41/48;layout32/44,33/44;longer13/14,12/14;
prior144/144both/layout44/48,47/48,line32/32both.0rejects. BotharmgatesFAIL
allfull-layout<80%; clean101also124FIT<90%, recoveryboth124/old48FIT<90%.
BEST1000/250byseedbotharms; cleanbestfullFIT109/113of124,layout31/30of44;
recoverybest106/104of124,layout32/31of44,oldFIT42/43of48,best20289.58%not90%.
No heldselection/finalreplacement/promotion. SourceFIT124110/115vsfinal109/114
and106/108, sourceold48FIT48/47vs44/46and42/41: clean-routeforgettingreal.

Interpretation: recoverygains1/2developmentcases vscleanFINAL, atcost3/6FITcases
and2/5old48cases; recovery101prior-layout loses4vsclean101. Small2seedtradeoff,
notclearwinner/statisticalsuperiority orfix. Canonicalcorneraccuracyclean84/83
of124vsrecovery76/79; recoveryendpointlabels25/26,16/16vs10/26,7/16 inclean.
Labelmatchdoesnotdefineallvalidroads. NextPROPOSED broaderFITfirst-bendaudit
accountingforalternatives beforedataweight/representationchange. No newtraining
command/job, thresholdchange, sourcecommit/push/finalmaps orproductionpromotion.
[Verifiedresults/guardincident](../docs/training/recovery-comparison-review-2026-11-07/README.md).

T101coordination:GitHub1/8/12/15updated/allOPEN; exactbodiesarchived.
Source/currentstatus/index/roadmap refreshed, finishedoutputs/weightsunchanged.
Guardleftintact; no deletion/newtraining/sourcecommit/push/promotion.


## T102 — First-bend audit corrects earlier diagnosis, 7 November 2026

Userasksfollowplan; notifiedfrozenfirst-bendvalidity/coverageaudit,no learning.
124FITconditional Draw→firstgoalobservations/masks byteidenticaltoteacherdata.
8FINAL/BESTclean/recoveryactors×124=992queries;279uniquephysicalendpoint
qualifications,211connect,9.968s/180scap. FINALcanonical/physicallycompletable:
clean10184/116of124,clean20283/118,recovery10176/111,recovery20279/111.
32/35/35/32noncanonicalchoices verifiedvalid. Conditionalassistedqualification
NOT freepolicyperformance; checksdo notexhaust allpossibleroutes.

Continuationaudit248currentcleanFIT+33earlierfaileddevelopmentfreeepisodes,
27.192s/180scap, exactearlieroutcomes; prefixreplayed/hashcheckedseparately.
8/15clean101and4/10clean202FITfailures alreadyhad completablefirstroad; all12
restartfromalreadyconnectedfirstgoal. EarlierT98development6/19+6/14=12/33
alsohave validfirstroad andsamewrongnextgoal. ThusT99'outsideaxis-template'
wastruebutcallingallfirstroadsunhelpfulwasoverbroad; explicitlysuperseded,
notrewritinghistory. Oraclecanonicalcorner31/33rescue canrestorefamiliarprefix.

Demonstratedlabel limitation: singlecanonicaltargetpenalizesverifiedalternatives
andmatchingcontinuations areomitted; notproofuniquegeneralizationmechanism.
Nextengineeringchoicebranch-consistentacceptedlabels+matchingFITsuffixes,
reusecompletedmatchedcleancontrols ratherthanrepeatwork. No corner-onlylearning
orarchitecturechangejustifiedbycanonicalaccuracyalone. Allhashesunchanged,
no training/optimizersteps, no developmentteacherdata/finalmaps/promotion.
[Audit/raw/interpretationcorrection](../docs/training/first-bend-audit-2026-11-07/README.md).


## T103 — Branch-consistent teaching prepared; historical controls reused, 7 November 2026

After advance notice andT102evidence, withinapproved#8/#12/#15plan, engineering
choice058. SameT98FIT-selectedbest750sources/124FITcases asT100cleancontrols;
sourceproposedendpoint conditionaloncanonicalfirstgoal physicallyverified normal
commands beforeacceptance. Seed10140validalternatives/120suffixstates/1296unique
rows; seed20245/135/1311.85two-commandbranches verified,0setup/rejects/conflicting
actionsets,0developmentteacherstates. Original1176input/maskrows/firstcanonical
labels/priorlabels unchanged. Onlyacceptedfirstendpointsets andmatchingnew
continuationstates differ.14.424s/180spreparationcap,0optimizerupdates. Exact
generatorversionpreserved before runtimeaccepted-massmetriccleanup; no generator
logicchange. Acceptedsets limited, not exhaustiveproductiveactions.

ReuseCOMPLETEDT100cleancontrols, same750actors/freshAdam/valuehead/counters,
all2000controlbatchhashes/actualinitialpolicy-valueheadstates bothseeds/package
versionsmatch, hashespinned. Do notrerun oldcommand. Newbranches only2runs,
1000fixedupdates/180s each/360summed/900runloop,noextensions/earlyfitstop,
max2000updates/192000presentations. Batch96=24canonicalinput(acceptedsets)+
24branchsuffix+48prior vscontrol48canonical+48prior; shared24canonicalindices/
48prior eachupdate. Bothtargetsets/stateallocationchange, notpureloss-only or
samecleanexposure, posthoc/exposed-development comparison notnewfinaltest.
SameexistingNLLformula -log acceptedmass, lr.0003/clip.5; no NN/reward/mask/
simulatorchange or runtimeassistance. Sharedfeatureswilltrain,headfixed,PPOreadyFalse.

Best12FIT6old+6expanded at0/250/500/750/1000/finalnewstep; pairedbest/native
replay/step/hash/versions plusinitial/final/error. BOTHsnapshots/bothseedsneed
124FIT90/old48FIT90/full-layout80/priorFIT90/layout80/line90/0rejects, longer
diagnostic. Fixedsamegates/control; no sourcechosenonheldscores or promotion.
FivechecksPASS4.825s: baseidentity/FITonly,2000controlhashes/pairedsamples,
actualsuffixstate/physicalreplay,matchedinitials/acceptedalternativeNLLfinite
backward/unchangedparams/freshunusedAdam/0updatebestnativepair,guards. Version-
guardedpreflightPASS. Newoutput/resultsabsent, no learning or nextoutcomeclaim.

Smallsource/plan/qualifications/checks archived; binarydatasets/weights/host
localonly, no sourcecommit/push/finalmaps/broadissueclosure. T101gatefailed;
benefitofbranchconsistency remainsunproven. Userlaunchesalllearning.
[Readycommand/evidence](../docs/training/branch-teaching-preparation-2026-11-07/README.md).

T102/T103coordination:GitHub1/8/12/15updated/allOPEN, exactbodies archived;
earlier templateinterpretationcorrectedpublicly, rawhistoricaldataunchanged.
Currentstatus/index/roadmap ready; source/control/actor/data/hosthashesverified,
newoutput/resultsabsent. No training/sourcecommit/push/promotion/finalmaps.


## T104 — USER branch teaching verified: FIT improves, development gate FAILS, 7 November 2026

Userreportsdone; review/recordchange announced, no newlearning. Both1000updates/
96000examples,2000updates/192000presentations total;105.708/117.143sstage,
222.851summed/319.499soverall(~5m20),within180/360/900,no caps/extensions/errors.
FINALbranchfullFIT119/124,120/124;oldFIT46/48,47/48;layout34/44,31/44
(77.27%,70.45%);longer14/14,13/14;priorFIT144/144/layout48/48/line32/32both.
HistoricmatchedcleanFINAL109/124,114/124FIT/layout31/44both. Trainingimproves
10/6cases, development+3/0, notrobusttransfer. Paired101win4/loss1,202win5/loss5.

FIT-selectedBEST250/750,12/12/2commands each; fullFIT119/124,122/124;oldFIT48/48
both;layout30/44,32/44;longer12/14,13/14;prior144/48/32perfectboth. No retrospective
heldselection/finalreplacement. All4snapshots FAIL80%layout; >=36/44needed,
35/44not80%. Otherphysical/retentionthresholdspass,0rejects. No promotion/closure.
Source750FIT110/115vs119/120 gain, butsourceold48FIT48/47vs46/47: noforgetting
atallwouldbeoverclaim. Acceptedtargetmetrics notcomparabletosingletonNLLaccuracy.

Frozenreview exactlyreproduces1624originalepisoderecords in87.807s/180scap,
0optimizersteps. All2000newbatchhashes/exposurecountsreproduce. Initial/final
teacher, sourcecopy, exacthistoricalcleaninitialpolicy/valuehead, freshunusedAdam,
finalAdam1000/counters1000/96000/0RL, finite/fixedvaluehead, source/data/host/control
packages/nativebothbestpairs/protected4hashes checked. Sourcecontrolnotrerun,
posthoc historicalmatched2seedstudy, notindependentfinalgeneralization.

Branchpackageacceptedendpoints+matchingcontinuations+allocation isusefulforFIT,
transfermixed; notisolatedlabel-onlyorstatisticalsuperiorityproof. NextPROPOSED
remainingfailure/gained-lostcaseaudit withactualfirstroadvalidity/nextgoal checks,
notcanonicalmismatchheuristicorautomaticmoretraining. No newdataset/command/job,
sourcecommit/push/productionpromotion orfinalmaps. Userlaunchesalllearning.
[Verifiedreview](../docs/training/branch-teaching-review-2026-11-07/README.md).

T104coordination:GitHub1/8/12/15updated/allOPEN, exactbodies archived.
Currentstatus/index/roadmap refreshed; finalZIPhashes unchanged, smallarchive
verified. No newtraining/sourcecommit/push/promotion/finalmaps.


## T105 — Remaining failure audit, finalized 8 November 2026 (began7November)

Userrequestscontinue; frozenchange/budgetnoticesgiven. Initialaudit NumPybool
road-presenceflag notJSONserializable, beforefirsttracecouldbesaved. Failed
source/incident/partialwritertext preserved; original.tmpdebrislocalonly. Fix
explicitPythonbool, freshv2/same180scap, no model/trainingchange. v2all8clean/
branchFINAL/BEST×44development=352freeepisodes in42.847s, exactT101/T104outcomes;
goalprobabilities/component/roadpresence/strokechanges recorded,4nativefailure
replaysPASS, input8checkpointshashes matchstudiesandunchanged.

FINALclean101/202fail13/13;firstroadverifieddirectfinish3/5;branchfail10/13,
verifieddirectfinish0/1. Allsuchfailuresrestartoriginalconnectedgoal. Category
8to1notclaim7identicalcasesfixed: paired8oldcases yield6branchwins,2remaining
failureswithdifferentfirstroads. All23branchfailureshaveunchangeddraws40/53.

Broader90scapofflineprobes1.734s:remaininggoal→ANYroadcomponentcell within
conservativelegality verifies1/23one-strokefinishes, sameasendpointprobe. All23
firststrokesstartatgoal/containonegoalcomponent; all23normalcanonicalrepairs
succeedwithTWOadditionalcommandswithinresources/horizon,0rejects. Notproof
allotherone-strokestrategiesimpossible; assistedoraclefeasibility NOT modelscore
ortrainingcorpus. No developmentstatescollectedforlearning,0optimizerupdates.
Hypothesisgoal-relativeinputcouldhelpfirststrokegeometry; mechanismunproven.
[Audit/caveats](../docs/training/remaining-route-audit-v2-2026-11-07/README.md).

## T106 — Existing relative-input candidate ready for USER test, 8 November 2026

Afteradvancechange notice, engineeringchoice059 withinplan#8/#12/#15. Existing
FactorizedRelationalPolicy adds6observedgoaldescriptors/12relativegoal-cursor
planes,576params(18735→19311). No corner/witness/nextgoal/routerfeature ormask/
NNtask/reward/simulatorchange. EarlierrelativecandidateT78–T84didnotreliablyhelp
extension; preservednegativefinding, differentfull-route/consistent-labeltask
motivatescontrolledablation, notnovelty/successclaim oralgorithmrestart.

SAME T103data/sources750/loss/batch96/samplestreams/versions/FITscreens/gates,
historicalbranchcontrolsreused, no duplicatetraining. TwoNEWrelative101/202USER
runs,1000updates/180s each/360summed/900runloop, max2000updates/192000examples,
noextensions/earlyfitstop. SAMEFIT12success/commands/tieearlybestpair+initial/
final/error. BothBESTFINAL/bothseeds full124FIT90/old48FIT90/layout80/prior90/80/
line90/0rejects, longerdiagnostic. Newcomputeheadroomunbenchmarked; capinconclusive.

ThreefocusedchecksPASS11.350s: all2000baselinebatchhashesreproduce; all2607
corpusinitialactions/probabilities/valuepredictions EXACTmatcharchivedT103
initialactors, maxprob/valueerror0bothseeds; newcolumns havefinite nonzero
backwardgradients/unchangedweights/freshunusedAdam,0updatebestcustomserialization/
nativeexactpair; immutablebudget/physicalguards. Source/artifact/control/package/
freshpathpreflightPASS. Paramcapacity+inductivebiasbothchange, notinformation-
onlycausalclaim; posthoc2continuingseedsexposeddevelopment/notfinalgeneralization.

No learning/modelupdates, currentoutput/resultsabsent, no datasetregeneration/
developmentteacherstates/newfinalmaps/sourcecommit/push/promotion/closure.
Onlynewopt-inbuilder/runner/tests/docs; candidatebenefitunproven/currentgatefailed.
Sessionfolderkeeps7Novemberlabel, workfinalized8November. Userlauncheslearning.
[Checkedcommand/evidence](../docs/training/relative-branch-preparation-2026-11-07/README.md).

T105/T106coordination:GitHub1/8/12/15updated/allOPEN, exactbodiesarchived.
Currentstatus/index/roadmap refreshed; source/control/actor/data/hostpinsverified,
newoutput/resultsabsent. Smallarchivesverified, no newlearning/sourcecommit/
push/modelpromotion/finalmaps. Sessionworkfinalized8November.


## T107 — USER relative-input ablation verified: no measured gain, 8 November 2026

Userreportsdone; reviewchange notice/no newtraining.2×1000supervisedupdates/
96000presentations complete,2000/192000total;116.770/134.765sstage,251.535summed/
356.035soverall(~5m56),within180/360/900,noerror/cap/extension. Savedphysical
scores EXACTLYmatchbaseline:T103branch FINALFIT119/120of124,oldFIT46/47of48,
layout34/31of44,longer14/13of14,prior144/48/32perfect; BEST250/750FIT119/122,
old48/48,layout30/32of44,longer12/13of14,priorperfect. Bothsnapshots/seedsFAIL
80%layout,>=36/44needed. No promotion/gateclosure/heldselection/finalreplacement.

Initialsuspicionidenticalscoresmightbeuntreated/oldrunner explicitlychecked:
actualFactorizedRelationalPolicy19311params(+576),expandedinitial0/finalcontext
norm.211528/.305321andcellrelative.253929/.508542, Adam1000; only1/1000lossrows
perseedexactlyequalsbaseline(initialrow). Treatmenttrained,notano-op. All2000
batchhashes reproduciblymatchbaseline. FreshunusedAdam/sourceactorcopy/expanded
zero columns/valueheadmatch, finalfinite/fixedvaluehead/counters1000/96000/0RL,
acceptedteacherinitial-final/source/data/host/control/packages/protected4hashes
andnativebestbothpairs verified. 1624originalepisoderecords EXACTLYreproduced
in93.211s/180scap; separatecomparisonall1624outcome/costrecords identicalbaseline.

Additional90scap frozen effectcheck:88freeFINALdevelopmentepisodes +2607FIT
statequeries. Probabilitiesdiffermax.022385/.019316; greedychoices0/1296and1/1311
changed; freeactiontraces44/44and43/44identicalbaseline=87/88, changedcaseoutcome
same. Learnedweight/probchange NOT scoregain. Notwholepolicyidentityorclaim
aboutunexamined/stochasticstates; case-levelrecordsexcludecompletegeometry.

Engineeringconclusion: don'tpromoterelativevariant/extendthisexacttestwithout
newevidence; keep simplerbranchreference, notproduction. Earlierextension
negativefindingpersists. No measuredadvantageunderthisdata/budget/init, not
proofallrelativefeatureideas/learnersfail. Runtime5m56vs5m20observational/load
confounded,nocausalspeedclaim. NextPROPOSED reviewdistinctspatialreasoning/
learninghypotheses+smallesttestbeforemodelchange, no nextcommand/job/dataset/
runner, sourcecommit/push/promotion/finalmaps. AlllearningUSERlaunched.
[Verifiednegativefinding](../docs/training/relative-branch-review-2026-11-08/README.md).

T107coordination:GitHub1/8/12/15updated/allOPEN, exactbodiesarchived.
Currentstatus/index/roadmap reflectnegativefinding; finishedweightsunchanged,
smallreport/source/measurementarchiveverified. No newtraining/sourcecommit/push.

## 8 November 2026 — Gameplay fidelity checks, no learning

User reports original high-800 vs simulator 200 scores; checks-only request. [Evidence and limitations](../docs/training/gameplay-fidelity-check-2026-11-08/README.md): 42 internal suites PASS, installed original assembly hash matches prior provenance; four exposed privileged 400-second diagnostics reproduce 70/56/65/78 trips, 391–487 vehicle-seconds of labeled parking-access blockage. Confirmed supply scheduling/parking concurrency differences; causal score gap unquantified. No production changes/training; private extracts stay local. Simulator decision notice recorded as DESIGN_DECISIONS 060. Training results/gates unchanged.

8 November gameplay fidelity follow-up: [road-stock fixtures](../docs/training/gameplay-fidelity-check-2026-11-08/ROAD_STOCK.md), no learning. Straight chain costs6 here versus5 derived from installed base pricing; ordinary road lost when converted to roundabout then removed. Redraw/unused road refunds pass; reward/retirement contributors qualified. Production unchanged.

8 November roundabout fidelity follow-up: [checks-only findings](../docs/training/gameplay-fidelity-check-2026-11-08/ROUNDABOUTS.md), no learning. Original inbound-registration/shoving/topology comparator differs from replica journey-time/current-lane comparator. Static corner fixture creates automatic shortcut; original legality unverified. No code/gameplay changes.

## 8 November 2026 — First gameplay fidelity repair, no training

User authorizes fixes and future original-game video comparison. [Roundabout concrete fix](../docs/training/roundabout-concrete-fix-2026-11-08/README.md): pending replaced-road credit, refunded after old lane paths clear; two new regressions,44 suites PASS. No Unity player update, learning, model performance or full-fidelity claim. Decision061 records comparison limitations. Historical checkpoint/replay results remain tied to their prior simulator version.

## 8 November 2026 — Gameplay repairs installed, then video-comparison freeze

[Repairs](../docs/training/gameplay-fidelity-repairs-2026-11-08/README.md):54 core/7 environment/6 reward/10 map-version checks,5 installed Original city smokes; exact parity NOT established. New4-trip/209.9s ordinary fixture replaces stale-rule fixture only in current reward tests; old73-point record unchanged. Intermediate parking overlap/stall failures preserved and fixed in tested cases. No learning/checkpoint promotion; old model scores remain historical.

User then requests exact uploaded-video replay and no further changes. [Recording evidence](../docs/training/recorded-game-comparison-2026-11-08/README.md): final visible HUD835, correcting paused826; original seed/event state unavailable in scoped search, exact spawn parity/importer absent. No matched simulation score or delta. Gameplay changes frozen; asynchronous reconstruction question unanswered. DESIGN_DECISIONS062/063; private video/frames/profile/journal material stays local, numeric findings/fingerprints archived.

## 8 November 2026 — Custom seed/replay feature; no learning

User authorizes custom seeding and video reconstruction after freeze. [Feature and chronological diagnostics](../docs/training/custom-video-scenario-2026-11-08/README.md), design064.58 core suites pass; numeric-seed and custom scheduled-event playback implemented, Unity build and trace validation pending. Source original835; discarded v4 partial8-trip replay had missed shadowed roads, so it is NOT a matched score. v5 rejected road stock from false riverbank/UI detections. Hidden RNG/demand phase unrecovered; no score-fitting, training or promotion.

Custom-scenario continuation: corrected false-gray-road hypothesis (building shadows), cyan entrance and Unity offer DTO.58 core PASS; headless repeated24/297.45s/84of780 identical, matching Unity player; tiny example4/80/5 agrees. Ordinary seed12345 startup PASS; corrected app installed, previous app backed up locally. Original final835 vs draft24 is preliminary, NOT exact same seed/timing validation; future696 events remain unapplied. Red dynamic queue has>139s carpark waits; static isolated same-network control22trips/400s passes, mechanism open. No gameplay-rule fix for this finding, score-fitting or learning. [Archive](../docs/training/custom-video-scenario-2026-11-08/README.md).

## 8 November 2026 — Recorded playground carpark performance repair; no learning

User authorizes tweaks after watching draft. [Chronological causes/checks/intermediate failures](../docs/training/video-performance-repair-2026-11-08/README.md), design065. Same297.45s event input24trips/failure→30/no failure; red2→9 deliveries,330s37/no failure. Reservation bypass from omitted boundary lane fixed; local bay sweep reservation prevents queue cycle while preserving already-ahead priority. v1/v2 fail existing tests and rejected; v3 passes67core/7environment/6reward/10map-version. Whole original parity still unvalidated; v8 separate trace rejects false diagonal at466.65s,64partial NOT final score. No training, checkpoint change or promotion. Player build pending.

Video performance repair deployment: Unity build/core checks PASS; staged playback37/330/99 matches headless, normal Original LA20s smoke PASS. Updated installed playground with previous app local backup; reopened bounded prefix330 paused for user. Source/build hashes and numeric evidence archived. No model changes, learning, promotion, source commit/push, or full835 parity claim.

## 8 November 2026 — Identical behavior requirement / movement audit, no learning

User rejects improved-only comparisons. [Event audit](../docs/training/event-parity-2026-11-08/README.md), decision066. First3originalHUDevents sampled0.1s, original first estimated17.418vs old25.15. Missing factor3 and ordinary-weighted/motorway-minimum lookahead confirmed in private installed-rule audit; numeric findings/hashes only archived. Corrected first17.45, second32.05vs29.826, third41.15vs47.408: explicitly NOT IDENTICAL.69 core/7environment/10map-versionPASS,330s50trips/no failure. Reward historicalv2outcome changes; separately record v3(12)andv4(13),252.95s within300s bound, v4reward check pending. Final player build pending. No training/policy performance or parity acceptance.

Event-parity continuation: final69core/7environment/6reward-v4/10map-version PASS; Unity50/330/99 and ordinary LA20s PASS, corrected player installed/backed up, prefix reopened paused. Machine original-event gate exits1NOT_MATCHED,2and3timings still differ; do not conflate checks with original identity. v4measured13trips/252.95s/253actions within300s cap; v3(12)andv2(4) historical. No learning, fitting score, checkpoint selection/promotion or push.

## 8 November 2026 — Replay input review, no learning or engine changes

[Reviewed opening](../docs/training/replay-input-validation-2026-11-08/README.md), decision067. First60video seconds(~90game), synthetic native-stub draws create premature/orphan cells; corrected data16events, red bornwest→usernorth.7manual topology/direction/stock checkpoints:2old→7reviewed. Existing69-rule Unity loader6/90/16PASS, incidental output not parity. Opened reviewed clip paused. Full input trace/clock/hidden state remain unvalidated; viewer does not yet replay wall-clock pause/2x pattern. No tuning, learning/weights/promotion/binary replacement/commit/push.

## 8 November 2026 — Independent full video input review (in progress; no learning)

User accepts opening and authorizes continuing independently. [Measured findings and v10–v13 failures](../docs/training/full-replay-review-2026-11-08/README.md), design068. Added4missed yellow houses(total55), corrected navy top/latergreen left entrances, dynamic future-parcel filtering, screened117diagonal candidates. Per-second camera max0.164tiles/median0.0039, not multi-tile error. v11stock90/170/240matches, later specificfalseedgesidentified; v13reaches286trips/832.95s alive then rejects material, not full score/parity. No core change/grants/learning/build/promotion/sourcepush.


## 8 November 2026 — Shared transit and replay continuation, no learning

[Full review continuation](../docs/training/full-replay-review-2026-11-08/README.md), design069. Initial shared-lot physical through-routing71core/7environment/6reward/10mapPASS. v14old295failure→335alive then rejected material; v15 removes one visually false rounded-curve leg, then blocked spawn from erased orphan motorway endpoint. Targeted cleanup72PASS; v15 reaches371/game-over957.05s with shared gate approach deadlock, boundary fix under test. Partial outputs not original835comparison. Five actual source513roads retained after HUD verification rejects false-road hypothesis. No grants/learning/build/promotion/push; installed69rules unchanged.


## 8 November 2026 — Emergency stop and branch checkpoint

User requests immediate stop/save. [Saved exact plan/state](../docs/training/full-replay-review-2026-11-08/EMERGENCY_HANDOFF.md). Installed74verified; source77ahead with final dedup edit untested. No matching running diagnostics at stop; no learning. Latest v20/75partial586/game-over1185.95s/340of406not valid835comparison. Preserve all work and pending7input corrections; do not resume automatically.


8 November2026 — User requests missing-file review/handoff work. [Response](../docs/training/full-replay-review-2026-11-08/LOCAL_TRANSFER_RESPONSE.md). Fetched Aya1779c0b; packaged2368local payloads/video into verified924MiBZIP, kept out ofGit. No external upload, simulator changes, fixture update or learning. General native-rule intent distinguished from unproven implementation correctness; prior results remain historical/version-specific.


## 8 November 2026 — Simulator repairs after resume (Aya's session), no learning

User authorized continuing after Mohammad's [response](../docs/training/full-replay-review-2026-11-08/LOCAL_TRANSFER_RESPONSE.md) and local-file transfer (2368 files verified against its manifest). [Full report](../docs/training/simulator-repairs-2026-11-08/README.md). Measured: reward-v4 drift is the rule-77 native join at spawn (current 23 trips/no game-over vs 13/game-over; variants and lockstep replay show one free join at 10,8); fixture v5 recorded with the v4 recipe (30 trips/305.15 s), v4 kept. Engineering fixes, each with a test that failed first: current wait cleared on arrival; blocked approach priority removed when the conflicting occupant is stationary (v20 deadlock from t=1163 at junction 19,7/ring 19,8). Additive protocol field `simulatorVersion` = `2026-11-08.2`. Builder regenerates v20 exactly; v21 adds the seven handoff corrections, topology check 400/400, strict run 570 trips/1166.05 s game-over from a physical gridlock at 20,11-20,12 (partial diagnostic, not a comparison with 835). Open: gridlock rule (user decision), Unity rebuild, wall-clock playback. No training, model evaluation, deployment or push.
