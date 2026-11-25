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


8 November2026 — User authorizes answering REQUEST_SPACE_CHECK_RULE. [Read-only original-rule audit](../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SPACE_CHECK_RULE_ANSWER.md): conditional shared-exit gap chain(5states,>2vehicle lengths), inbound eligible-prefix arbitration, first-two-lane commitment, route-time registration and explicit blocking-cycle shoving verified. Installed green bypass on/straight-entry option off;45swait feature runtime state unverified.191e9adpartial filter is not an exact reproduction. No engine changes, original execution, learning or score claim; private source stays local.


## 8 November 2026 — Original junction arbitration replicated, no learning

User decision: replicate the original's space-checking logic, including its conditions, using Mohammad's read-only extract findings ([answer](../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SPACE_CHECK_RULE_ANSWER.md)). Implemented independently for OriginalReference (`c1d23d0`, simulator `2026-11-08.3`). Registration, shared-exit and v21-gridlock checks fail on the previous engine and pass now; 81 core/7 environment/6 reward/10 map PASS. v20 and v21 replays: no deadlocked second; 490 and 488 trips, ended by a newly exposed carpark gate lock at shared lot 20 (gate owned by a car queued behind the requester). Partial diagnostics, not a comparison with 835. Gate lock not fixed; awaiting the user.


## 8 November 2026 — Carpark gate measured at one point, no learning

User decision: keep the approach gate but measure every car at the same point and expose gate waits to cycle recovery, then inform Mohammad. `7ef4071`, simulator `2026-11-08.4`: cars passing through a shared lot are gated at the start of the outside approach lane, like arriving cars. The v20 lock reconstruction fails on .3 and passes; two earlier variants were discarded (ParkingFlow overlap; departing-owner trap). 82 core/7 environment/6 reward/10 map PASS. Replays: v20 620 trips/1206.4 s, no deadlock; v21 537/1147.15 s, ended by a signal that stops switching (one stuck green car within 0.5 tiles), question sent to Mohammad. Partial diagnostics, not a comparison with 835.


8 November2026 — User requests original traffic-light/carpark follow-up. Read-only private-rule/config audit: nearby0.5tiles/min3/overtime1sconfirmed, but blocked-candidate early termination and commitment-age phase weights differ materially from simulator. Installed age multipliers carpark10/mothball4, same-chunk active-pair total penalty0.1; no max-green cap. Amber retains prior ActivePair in shown chunk permission logic; American non-crossing red-turn exception on. Carpark entrance/exit/internal paths use road chunks; no separate one-owner gate found in inspected classes; bay allocation separate. Full response/provenance in ORIGINAL_SIGNALS_CARPARKS_ANSWER.md. Reported408vs513GPresult not rerun, no causal attribution/engine edit/learning/deployment.

[Source-backed response](../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SIGNALS_CARPARKS_ANSWER.md).


## 8 November 2026 — Original traffic lights replicated; deterministic lights comparison, no learning

From Mohammad's answer (`e58b1fd`), implemented in `470784a` (simulator `2026-11-08.5`): original phase timing, nearby guard with same-chunk early termination, commitment-age weights, amber permission and American red-light rules. Stuck-light, right-on-red and amber checks fail on .4 and pass. Deterministic Evolved Rules lights on/off comparison on LA 3100-3109 (20 games plus a 2-game harness check reproducing .4 exactly): lights 510.5 vs 513.2 without (was 408.4 vs 513.2); stuck-phase time ≤4.7 s per game (was up to 237 s). Map 3101 still -197 for another cause. Evaluation only, no learning or selection.


## 8 November 2026 — Carpark chunk arbitration; gate kept, no learning

`59e8830`, simulator `2026-11-08.6`: carpark lanes arbitrated as the original's chunks and registered as inbound lanes (Mohammad's B1–B4). The registration check fails on .5 and passes; 84 core/7 environment/6 reward/10 map PASS. Gate-removal experiment: the eight-car queue deadlocks at the entrance (entering vs drive-through body clearance), so the engineered gate stays. Replays v20 629, v21 642, no deadlock; lights comparison 529.7 vs 535.5 without (20 games). User asked for the Evolved Rules session to start gp-5 on this simulator.


## 9 November 2026 — Map 3101 gate lock fixed; lights now help, no learning

Investigation of LA 3101 (lights −189 on .6): a car held at the red light outside shop 9 owned the engineered carpark gate, locking the lot for the green-side queue. `ad8e2ca` (simulator `2026-11-08.7`): red-blocked cars may not take or keep the gate. The new check fails on .6 and passes; 85 core/7 environment/6 reward/10 map PASS. Deterministic lights comparison (20 games): 580.3 vs 535.5 without (6 better, 4 worse; 3101 752 vs 684). `main` redone as simulator-only (`d4c8099`, full merge kept as `main-full-merge`) and pushed to Aya's fork; updated to .7 the same way.


## 16 November 2026 — Focus hierarchy proposed; not approved

User requested a supported hierarchy plan and reasons, and assigned roundabout follow-up to another person. Engineering proposal: manager selects a persistent primary tile and optional secondary tile; executor retains global observation and every physically legal primitive action. No generated routes, goal bonuses or strategic masks. Provisional review after 8 completed edits or one wait, with early handoff and native-event interruption; cadence unmeasured. Shared encoder/separate heads and custom duration-aware PPO credit are proposals, not implemented defaults. Score-only delayed learning and ignored-focus/manager-cycle risks remain explicit; curriculum is deferred.

Full rationale, alternatives, literature, checks to perform and limits: [proposal](../docs/training/hierarchy-proposal-2026-11-16/README.md). No model, run, game episode, measured performance result or user approval. Literature inspected: Option-Critic, HIRO and official SB3-Contrib documentation; none establish this hierarchy as best for this game.

Branch correction: per explicit user instruction, fetched existing remote Maskable-PPO at 938b9f8/f34 and created its local tracking branch in C:/Users/moham/mini_motorways-maskable-ppo. Dirty codex/driveway-physics checkout preserved separately. This supersedes the older mohammad preference for this restart. Current proposal documentation lives only on Maskable-PPO; prior planning records still require migration from the older checkout. No commit/push this turn. Checks: branch/base identity and documentation links inspected; no trainer tests appropriate to proposal-only edits.


## 16 November 2026 — User adopts focus hierarchy; agent accountable for revision

After explicitly confirming no planner-generated construction routes or route menu, user instructs us to follow the agent's hierarchy recommendation and be able to justify, fix and change it. Adopt manager primary/optional-secondary focus plus unrestricted primitive executor, with provisional eight-edit/one-wait reviews. See [decision and preserved proposal](../docs/training/hierarchy-proposal-2026-11-16/README.md). Engineering accountability includes held-out/replay evidence, focus-response and stall diagnostics, recorded revisions and honest uncertainty; initial adoption is not measured success. No changes to score-only/physical masks/no-generated-routes constraints authorized. Architecture/credit details and curriculum remain unresolved. Checks: documentation and status consistency inspected. No code, training, measurement, commit or push.


## 16 November 2026 — Curriculum discussion resumed; broad direction accepted

User agrees to staged practice progressing from basic connections through construction challenges/shared networks/growing cities to full games. This resumes the deferred curriculum topic; brief assent does not settle numerical gates or scenario details. [Record and first-stage proposal](../docs/training/curriculum-design-2026-11-16/README.md). Proposed first stage: one matching house/destination, varied short clear land layouts, explicit waits and actual scored service, held-out validation layouts. Score-only reward, native physical legality and no generated routes preserved. Scenario distribution simplifications must be disclosed. No measured result, implementation or training; checks limited to documentation links/status.


## 16 November 2026 — Stage 1 concept approved; main checklist created

User approves the preceding Stage 1 decisions and requests a clear pipeline/checklist. [Main checklist](PLAN.md) now separates approved design, unresolved decisions, implementation, correctness/speed checks, bounded pilot, curriculum expansion and human evaluation. Stage 1 concept adopted; no unmentioned numerical thresholds, horizon or budget inferred. [Curriculum approval](../docs/training/curriculum-design-2026-11-16/README.md) preserves earlier discussion. Current position: define concrete Stage 1 scenario and passing rule, then resolve remaining implementation contracts. Earlier local planning/workbook migration remains explicit unfinished work. Checks: local links resolved, branch Maskable-PPO confirmed, statuses checked for approval versus implementation distinction. Documentation only; no model, training, measurement, simulator change, commit or push.


## 16 November 2026 — Progress overview simplified after user feedback

User reports the detailed checklist is unclear and overwhelming. Replaced training/PLAN.md with a short overview: agreed design, current first-practice-game decision, and later build/check/pilot/expand/compare steps. Preserved the previous checklist at docs/training/pipeline-checklist-2026-11-16/DETAILED_CHECKLIST.md, adjusting relative links for its archive location. No design choices, approval states or execution gates changed. No implementation/training/commit/push. Documentation links checked.


## 16 November 2026 — Correction: do not reopen previously discussed decisions wholesale

User challenges the statement that model information, architecture, optimization and evaluation still need to be decided. Checked the earlier current_decisions.json in the separate original checkout: observation contents D22 and replay requirement D34 are recorded settled; observation encoding D24, architecture D36, PPO D37 and credit D28 already have concrete prior settings and review evidence, with dependent design states reopened when hierarchy was previously unspecified. Pilot D42 has an existing concrete proposal but is explicitly Not reviewed in that record. Thus prior settings are not missing and should not be presented as a blank-slate approval queue. New manager/executor and curriculum adoption requires targeted reconciliation, not repeating every topic. Stage 1 horizon and promotion threshold were explicitly unspecified in the recent approval; earlier full-game horizon/evaluation are not automatically transferable. Approval, review and implementation remain distinct. Updated overview accordingly. No new setting, implementation, training, commit or push; future record migration/reconciliation remains an agent task.


## 16 November 2026 — Stage 1 horizon and passing rule approved

User explicitly approves the agent proposal: 180 simulated seconds per practice episode, excluding paused edit time; at least 90 of 100 held-out practice layouts must each produce at least 3 scored trips. Reason: repeated service rather than connectivity alone and varied-layout reliability rather than one memorized arrangement. Initial engineering targets, not measured optimal values. Timing feasibility must be verified against native trip generation before applying this gate; failure requires documented revision, not a hidden physics/reward change. Cohort uses a frozen checkpoint; operationally truncated episodes cannot count as successful complete episodes. [Full record](../docs/training/curriculum-design-2026-11-16/README.md). Updated overview/status. No scenario implementation, game episode, feasibility measurement, training, commit or push. Existing design reconciliation remains next.


## 16 November 2026 — Linux inventory commands supplied

User requests the commands to run on the training computer. Archived read-only shell inventory and scope at docs/training/linux-preflight-2026-11-16/. Requests OS/CPU/RAM/disk/GPU/tool versions and current Python package versions/CUDA availability, without installation or training. No results received and no throughput benchmark possible until the new workload exists. No new hardware conclusion, implementation, commit or push.


## 16 November 2026 — Linux hardware evidence received; root disk nearly full

User-supplied inventory confirms Ubuntu24.04.4/kernel6.8.0-149, Ryzen9 3950X/16cores/32threads, nominal32GiB RAM, RTX2080Ti/11264MiB (supersedes GPU unknown/earlier uncertain2080Super). Root and home share /dev/nvme0n1p4:476G size,443G used,8.1G available,99% utilization. This does not inventory other drives or verify the prior3TB total. Python3.12.3/Git2.43.0 present; dotnet not on PATH; active interpreter has NumPy1.26.4 but no torch/gymnasium/SB3/contrib. [Sanitized measurement source and limits](../docs/training/linux-inventory-2026-11-16/README.md). Next: read-only lsblk/df to find storage before installation. No performance benchmark, training, dependency installation, deletion, commit or push. Checks: parsed reported values against attachment; SHA-256 retained, raw hostname/process details left local-only.


## 16 November 2026 — Disk layout clarified; read-only mount proposed

User-pasted lsblk/df accounts for roughly 3TB nominal across NVMe and SATA-named disks; root/home remain 99% full. 1.8T /dev/sda2 NTFS and 469.8G NVMe NTFS are unmounted; their free space is unknown. Archived small numeric source at docs/training/linux-preflight-2026-11-16/storage.json. Proposed read-only udisksctl mount of sda2 then df, checked against official Ubuntu Noble manual. No mount result yet; no installation, deletion, partitioning, training or new performance finding.


## 16 November 2026 — User home small; storage setup needs IT assistance

User reports mounting sda2 prompts for IT credentials, then home du totals389M (snap311M, Desktop51M, cache27M). Existing df root443Gused cannot be explained by user home; other usage ownership/source unknown. Archived numeric summary and limits in docs/training/linux-preflight-2026-11-16/home-storage-followup.json. Engineering recommendation: ask IT for writable project storage or adequate Linux free space rather than delete small user folders. No IT message sent, password requested, mount success, installation, deletion or training. Remote setup is pending storage; local implementation preparation remains possible.


## 16 November 2026 — Initial storage allowance explained

In response to user capacity question, clarified only Linux root/home is measured nearly full (8.1Gfree/476G,99%used); second disk free space unknown. Recommend asking IT for50GB writable initial workspace as an engineering allowance for environment/project/builds/bounded artifacts, not measured minimum or unlimited-run capacity. Need actual footprint and retention measurements later. No new measurement, installation or training.


## 16 November 2026 — Disks screenshots distinguish unallocated from file free space

User supplies3Disks screenshots: DATA /dev/sda2 is2TB NTFS Not Mounted; selected1.1MB trailing region is Unallocated Space. This does not measure filesystem free space. DATA usage remains unknown; root99%usage finding unchanged. Recorded own observations in docs/training/linux-preflight-2026-11-16/disks-ui-observations.json, without publishing screenshots/device identifiers beyond needed paths. Prior mounting requires IT credentials; advise IT-authorized access then graphical file Properties. No storage change, installation, training, commit or push.


## 16 November 2026 — Additional unprivileged disk diagnostic proposed

User has no external drive and requests another terminal command. Proposed read-only `du -xhd1 / 2>/dev/null | sort -h`, with explicit incomplete-count limitation for inaccessible folders. No claim it unlocks unmounted NTFS, guarantees recoverable space or authorizes deleting data. No output received, install, storage modification or training.


## 16 November 2026 — Unprivileged root accounting incomplete; no cleanup target found

User's du output totals36G versus earlier df443Gused; /usr19G,/var13G,/opt2.8G,/home398M. This is not evidence of hundreds of GB free: command suppresses errors and may omit inaccessible directories. Exact cause unresolved; no deletion or recovered capacity. Archived own numeric source at docs/training/linux-preflight-2026-11-16/root-usage-followup.json. Recommend IT-level accounting/access assistance; local preparation can continue, remote sizeable installation remains pending storage. No new benchmark or training.


## 16 November 2026 — Exact storage request: measurable source separated from allocation

User asks exact required storage. Inspected baseline requirements and hierarchy record: full Linux environment/torch device build and retention footprint are not pinned/measured. Calculated1354tracked files at938b9f8 total38,368,424bytes (36.59MiB), excluding git/dependencies/builds/checkpoints/logs/replays; this is not clone/install disk usage. Recorded docs/training/linux-preflight-2026-11-16/storage-requirement-status.json. Official PyTorch selector and pip install stages checked; neither supplies this project's disk total.50GB remains proposed allocation, not measured minimum;8.1GB sufficiency unestablished. Exact peak installation and bounded run storage need resolved dependency closure and retention measurement. No large download, install, training, commit or push.


## 16 November 2026 — Full Windows workspace size reconciled with screenshot

User supplies folder Properties7.28GBlogical/7.37GBallocated. Direct scan matches screenshot logical7,819,448,923bytes exactly,0errors. Breakdown: tmp5.001GiB,output1.039GiB,.venv.658GiB,simulation.394GiB,docs.144GiB; own aggregate source archived at docs/training/linux-preflight-2026-11-16/local-workspace-size.json. Earlier36.59MiB was tracked source only and not a useful standalone full-space estimate. Large scratch/output is accumulated existing work, not a requirement to copy it all to new Linux training. Linux GPU environment peak/retained-artifact footprint still unmeasured; Windows CPU venv size not transferable. No cleanup, upload, install, training, commit or push.


## 16 November 2026 — Initial storage budget calculated from Linux archives

User requests an actual calculation. Inspected official CPU/cu126 PyTorch2.14.1 distributions, existing four requirement pins and LinuxCPython3.12wheel metadata. Own metadata/ZIP-range script resolves applicable dependency scenarios without full wheel downloads: CPU16packages0.209GiBcompressed/0.760GiBpayload;GPU34packages3.421GiBcompressed/6.159GiBpayload. Sum/count/positive-size checks pass; metadata resolver checks version constraints, not a pip/runtime install. SDK8.0.427 archive217,060,685bytes/gzip tar-size597,166,080bytes inspected via range. Microsoft now marks .NET8 out of support; note for later dependency reconciliation, no source upgrade adopted. Current source remainsf34.

[Full calculation and limits](../docs/training/linux-preflight-2026-11-16/STORAGE_BUDGET.md), script, per-package public source URLs/hash/size data, version snapshots and storage-budget.json archived. Engineering allowances1GiBSDK/builds+0.1GiBfreshsource/git+5GiBrunartifacts+5GiBsystemreserve produce20.680GiBplanned peak/capacity budget; recommend25GiBavailableinitially.50GBpriorrequest remains comfortable, not required minimum. Run-artifact allowance is not a silent deletion policy. No guarantee candidateGPUbinary compatibility, exactinstalledfootprint or unlimited retention; must verify later. Windows7.37GBfolder mostly accumulatedscratch/output is not copied wholesale. No target mutation, package installation, simulation, training, commit or push.


## 16 November 2026 — Alternative laptop inventory requested

User reports another laptop with20cores and asks for Bash commands to assess it. Archived simple read-only OS/CPU/RAM/free-space/disk/GPU/tool checks at docs/training/alternative-laptop-2026-11-16/. No hardware conclusions or comparison until output arrives; physical cores versus threads unresolved. No install, training, storage modification, commit or push.


## 16 November 2026 — Alternative Windows laptop partial inventory received

Three user screenshots show RTX5060prefix/fullname truncated with8151MiBtotal VRAM; Python command not found/storealias, Git not recognized, .NEThost available but noSDKsfound. CPU20cores unverified, RAM/storageunknown. Recorded small own observation source in docs/training/alternative-laptop-2026-11-16/windows-observations.json; original screenshots local-only, processlist not copied. Request graphical CPU/RAM/disk views rather than more complex terminal commands. No installation, device-selection adoption, benchmark, training or commit/push.


## 16 November 2026 — User reports30GBfree; initial storage target met provisionally

User says storage issue resolved and30GBisfree. This supersedes treating older8.1Gfree as the current availability; no new df/path evidence supplied.30GBmeets rounded initialrequest/25GiBbudget if accessible to currentLinuxaccount. Filesystem/path and writeaccess still need verification as part of setup, not assumed from report. Record at docs/training/linux-preflight-2026-11-16/storage-update.json. No deletion by agent, installation, GPUvalidation, training, commit or push.


## 16 November 2026 — Linux setup begins with branch clone command

User asks next step after reporting30GBfree. Verified remoteMaskable-PPO still938b9f8f34. Supply single-branch clone into userhome/mini_motorways, with instruction to return output and not overwrite existing paths. No credentials requested. Local restart planning documents are not yet pushed/newtrainer notimplemented; clone obtains baseline only. No clone result, dependency install, training, commit or push performed by agent.


## 16 November 2026 — New-chat handoff saved after reported successful clone

User says clone is done and wants to continue in a new chat. Added training/HANDOFF.md with exact stopping point, approved hierarchy/curriculum and Stage1gate, branch/worktree constraints, local-only documentation status, Linux inventory/storage allowance, pending setup, and older decision-source paths. No clone output received; successful clone and30GBfree are user-reported, not agent verification. No new dependencies, trainer, training, commit/push. Current status points to handoff. Checked local handoff links and branch. Consulted OpenAI docs skill/product glossary; do not promise full automatic chat recall, use explicit handoff file instead.


## 16 November 2026 — Detailed decision publication authorized

User explicitly asks to push detailed decisions for the other computer. Selected50restart-specific ledger/spec/config/JSON/workbook/review-mapping/hardware/time-planning files migrated byte-identically from separate original checkout, total501151bytes. New docs/training/DECISIONS.md indexes full rationale and marks original flat/no-curriculum/old-device assumptions superseded by latest approvals. Existing hierarchy/curriculum,Stage1gate,inventory/storage calculation,shortplan and handoff included. Original snapshots and workbook review cells unchanged; new approval records remain separate. No model weights, game footage/private research, generated binaries, virtual environment or unrelated simulation changes included. Publication only, no newtrainer or training authorization. Checks: migration SHA256matches, staged file scope/credential scan, JSON/XLSX validity and current-entry-point links. Linux needs a manual fast-forward pull after push.


### Publication outcome

Detailed decisions committed as4c0700d508636c8e3930bbc26beb71b1ee5dcb38 (84files) and successfully pushed toorigin/Maskable-PPO. Verified remote head equals local commit; worktree clean immediately after publication. GitHub entry point: https://github.com/JoeJaffal/mini_motorways/blob/Maskable-PPO/docs/training/DECISIONS.md . Linux clone must pull to receive it. No source simulator/trainer change or training run.


## 17 November 2026 — Cloud continuity guide and stale branch guidance corrected

User reports new cloud chat seems to lack accumulated context. Verified remoteMaskable-PPO still6bd7f71 before changes. Found concrete instruction conflict: rootAGENTS.md still said training stays onmohammad, while explicit user instruction/handoff selectedMaskable-PPO. Corrected root guidance toread portablecloudstart/currentdecisions/handoff and useMaskable-PPO as source branch. Added training/CLOUD_START_HERE.md with approved rules, hierarchy/curriculum/gate, detailed-source precedence, device distinction and known stopping point. No automatic chat-history inheritance claim; no access to new cloud chat or verification of its code/state. Existing local16Novstate is not assumed to override newcloudprogress. Documentation publication follows prior request to make detailed decisions available to the other environment. No simulator/trainer edit or training. Checks: primary guide links, branch instruction consistency, no altered userconstraints; existingwork preserved.


## 16 November 2026 — Maskable-PPO setup verified; preparation only

**User decisions:** Work only on Maskable-PPO; prioritize training efficiency on Ryzen 9 3950X/32GB/RTX2080Ti; prepare implementation but do not launch any training sessions. Prior approved hierarchy/curriculum and score-only/no-planner/paused edits preserved.

**User-supplied evidence:** Storage 87GiB available after user cleanup; Python3.12.3 venv, torch2.9.1+cu126 GPU forward/backward passed, SB3/Contrib2.9.2/Gymnasium1.4.0/NumPy2.5.4, pipcheck passed. .NET8 Release/Debug builds and99core/7legacyintegration passed after creating tmp/. These measurements belong to the Linux PC, not the cloud machine.

**Engineering work:** Isolated cloud worktree /workspace/mini_motorways-maskable-ppo on Maskable-PPO from938b9f8; baseline checkout untouched. Added opt-in native practice reset, native one-second wait/erase protocol, paused adjacent construction and focus scheduling, untrained policy prototype, frozen gate evaluator, and bounded infrastructure/inference benchmark with no optimization calls. Reused current visible board encoding. Native rules/ordinary scenarios unchanged.

**Measured cloud checks:**99simulator suites passed. Scripted connection feasibility100/100uniquevalidationlayouts scored10–13trips each by180s. This is a test witness, not policy input, training or a learned gate result. First fixture version with180individualwaitobservations perlayout was interrupted to reduce redundant IPC; replaced with native bulk ticks for timing feasibility, retaining dedicated interface wait checks. Initial inference smoke hit an unsupported policy device constructor argument; corrected to .to(device), smoke now passes. Small JSON evidence/report is under docs/training/connection-practice-2026-11-16/.

**Limits:** Windows-local detailed planning files absent from remote; new distribution/inventory/CNN dimensions remain provisional engineering choices. Exact masks, hierarchical PPO credit/collector and zero-time replay format remain unfinished; no production trainer or training readiness claimed. Target-PC worker/device/batch settings unmeasured. No training, optimizer updates, checkpoint creation, commit/push or target-PC changes. See training/HANDOFF.md.


### Verification completion for the preparation above

Cloud Release/Debug build clean;99core/7legacy/7newchecksPASS. New suite includes100scriptedvalidationlayouts with10–13trips each by180s, batching without weight updates, paused review, score-only reward and time-limit completion. Final focused reset check verifies variation of automatically selected seeds plus reproducibility after reseeding; schema label follow-up check passes. Cloud-only benchmark smoke succeeded without learning; its timings are not Ryzen/RTX tuning evidence. Source transfer patch packaged separately; no commit/push.


## 16 November 2026 — Pushed detailed decisions retrieved and reconciled

User reports decisions pushed. Fetched Maskable-PPO, verified4c0700d publication plus6bd7f71verification, fast-forwarded this isolated checkout while preserving all uncommitted prototype changes. Shared documentation additions were backed up under local scratch then retained alongside publication; earlier cloud handoff archived. No original dirty Windows checkout touched; no commit/push. Read DECISIONS, adopted hierarchy/curriculum, exact historical spec/config, review mapping and pipeline checklist. Availability blocker resolved.

Audit identifies draft legacy observations expose internal timers/speed/wait/reservations/score, whereas exact81/54/motorway-table specification forbids them; draft single role-conditioned heads differ from adopted distinct heads;1508token syntax and conservative masks need reconciliation. These were smoke-test placeholders, not training-ready implementations. Preserve exact encoder widths and numerical PPO baselines where compatible, gamma1; lambda explicitly reopened with hierarchy, not silently reset to.95. Review/approval/engineering selection remain distinct. Full mapping and collector contract are in docs/training/connection-practice-2026-11-16/RECONCILIATION.md.

Engineering corrections implemented without training:4096tokens since last positive simulated-time advance replaces10000total-episode cap; visible pause counter; finite180s task horizon terminates rather than bootstrapping as truncation; operational stalls truncate; native wait stops at supplied task horizon including partial final second. Context dimension8 and draft schema v2, feature input adjusted. Focused correctness checks recorded in the report after completion. Legacy input/action/head replacement, exact native masks, hierarchy collector/credit and replay still pending. No training session, optimizer update or target-PC benchmark.

Follow-up result: Release build0warnings/0errors and six focused checks PASS (guard reset/cycles, fractional horizon, reward/ending, no-update inference, paused focus). No training. Prior100-layout feasibility retained; unchanged scenario physics/generator did not require another timing sweep.


## 16 November 2026 — One-hour implementation, no training

**User scope:** work exactly one hour; finish useful implementation/checks; give a plain-language final check-in. Start17:11:03UTC/deadline18:11:03UTC, recorded under docs/training/check-in-2026-11-16/SESSION.json. No training remains authorized. This entry records implementation progress, not the eventual end timestamp.

**Implemented:** published visible81/54/motorway encoder with four distinct-time traffic frames; two focus planes/role context; source viewer-visible flags; no legacy internal answers. Context-dependent1501tokens, separate cancel/handoff; native clear-land exact acceptance predicates and prefix masks; no strategic pruning, preserves no-ops/partial-effect native acceptance. Distinct manager/executor heads/shared established encoder widths. Native protocol/reset handshake, fatal schema/IPC/masked-valid rejection handling. Cached masks by actual legality state.

Frozen inference collector stores masks/probabilities/values/roles/ticks and checks unchanged weights; conditional primary/secondary focus records preserve partial rollouts, aggregate the same score stream without extra reward. Explicit gamma1GAE helper leaves lambda/trace units required; PPO loss-term helper clips a joint manager likelihood ratio once and requires supplied entropy rather than assuming independent conditional heads. No updater/backward/optimizer step. Replay persists all tokens/focus/clock/score plus input/source/build hashes and checks exact reproduction. Frozen evaluation preserves all attempts, errors and best/worst/nearest-average examples. Coupled batched-policy/parallel-simulator benchmark added; no-learning smoke checks only.

**Engineering interpretation:** the published3-trip gate does not add survival-to180s. A native game-over is a naturally completed episode with its actual score;>=3can meet the score floor. Removed the prototype's extra survival requirement. Operational stalls remain incomplete and invalidate promotion. Scenario20roadstock/generator/event setup remain provisional, not new user approvals. Workbook/review archives unchanged.

**Evidence:**99native core suites and1116differential acceptance casesPASS, including100live-traffic cases and16cardinal/diagonal/repeated connections.55combined selected Python testsPASS; seven additional distinct checks (five analytic PPO loss, one reset drift, one evaluation wall budget)PASS,62distinct total.100scriptedvalidation layouts10–13trips by180s; labelled full fixture552tokens/11trips/180s exact replay. No learned gate pass. Save/reload test uses temporary untrained weights and cleans them. Smoke timings are cloud CPU under concurrent verification load, not target-PC tuning evidence. Report/small JSON sources/logs retained under docs/training/check-in-2026-11-16/.

**Limits/next:** actual hierarchical PPO updater, deliberate remaining trace/entropy/level-weight choices, full-game tool/weekly support and graphical replay viewer still pending. No training, optimizer updates, target-PC run, commit/push or unrelated checkout modifications. No historic learning tests were invoked; tests were explicitly selected after scanning for learning calls.

Additional completion detail: fresh reset/rules/clear-land distribution handshake now rejects source drift before collection. Standard clipped PPO loss terms are checked analytically (five cases) with no updater; manager ratio is clipped jointly, entropy supplied explicitly, no level weighting default. No training.

Final audit addition: evaluation wall budget is now explicit/finite, expires as an external incomplete result with partial evidence retained; one new distinct timeout test passes (62distinct Python checks total). Clean-base patch apply/fresh Release build/9privacy checks pass.

One-hour checkpoint: requested work window17:11:03–18:11:03UTC; check-in timestamp returned18:11:13UTC (10seconds after deadline). Implementation/checks stopped for this check-in; final metadata/patch recording only. No training or optimizer updates.


## 16 November 2026 — Training preparation resumed

User requests getting everything ready, without overriding the earlier prohibition on starting training. Added hierarchy_updater.py with explicit authorization boundary, role-specific masked PPO loss evaluation, conditional manager entropy callback, explicit level weights, KL stopping and finite-gradient checks. No update/backward/optimizer call executed. Authorization-boundary test passed; this is preliminary implementation, NOT end-to-end training readiness. Return preparation, explicit trace/entropy/weight choices, complete checkpoint/run orchestration and Linux checks remain outstanding. Do not launch this partial updater as a completed runner.


## 16 November 2026 — Stage1 batch/update/checkpoint/launch integration prepared

User says go ahead with preparation; no training permission inferred. Implemented explicit lambda1/gamma1 return preparation, equal aggregate role weights, role-wide normalization, conditional manager entropy IS estimator, joint clipping, gradient accumulation with one Adam step per epoch, safe boundary collection and strict token cap, bounded default-dry runner, atomic policy/optimizer/RNG/config checkpoints. These integration settings are provisional engineering choices, not newly user-reviewed numerical decisions. No backward/optimizer call executed.

Dry real-host collections6and129tokens passed both role losses with unchanged fingerprints/0optimizersteps. Hard1token cut returns BUDGET_EXHAUSTED, not a learning result. Three forward-only integration/checkpoint tests and authorization-default test passed. Code exists for updates but that path and trained optimizer recovery are untested under current no-training constraint. Cloud CPU only; no Linux transfer/timing or production readiness claim. Detailed rationale/limits and small status/config evidence: docs/training/stage1-launch-preparation/README.md.

## 19 November 2026 — Linux connection-economy pilot verified

Read-only inspection identified the patched Linux checkout at `~/mini_motorways` on `Maskable-PPO` at `6bd7f71` with uncommitted implementation. The separate Desktop checkout is on clean `main`. No training process was found. The saved run and episode log confirm 341 completed games, six successes and a best score of 13. Mean road use fell from 20.00 units in the first 100 games to 0.22 in the last 41, and all final 141 scored zero. Construction avoidance is the leading interpretation, with causality and held-out performance unresolved. [Run record, configuration and measurements](../docs/training/linux-compact-reward-results-2026-11-19/README.md).

User supplied the pending introductory action simplification and asked for a summary first. Implementation and execution remain unapproved. No patch, branch change, pull, reset or training was performed.

### 19 November 2026 — Review of the proposed introductory action space

Read-only review of the compact mask, reward ledger, frozen comparison and verified run. Engineering recommendation: use an opt-in compact stage with one action per distinct new native-legal connection plus Wait. Keep existing arena, inventory, no-delete rules and native timing. Check whether both draw orientations have identical effects before merging their action IDs. Avoid filtering actions by whether they repair the gap. Start with native trip reward and defer both road cost and potential shaping so the first trial has an interpretable baseline. Changing the interface and reward together tests the package and cannot establish which change helped. Recommend a fresh checkpoint and a frozen paired initial-versus-trained comparison on the existing 100 held-out layouts. Add a uniform legal-action reference to measure chance repair and log repair rate, first connection time, and native trips. Validate masks and scripted repair before requesting separate pilot approval. These are review suggestions only. No source changes, evaluation, or training.

### 19 November 2026 — Direct one-gap practice implemented

The user approved the three review suggestions for implementation. Added opt-in `one-gap-direct` with native distinct-new-link masking, one build or Wait per decision, a single PPO actor/value stream, and trip-only reward. The frozen comparison adds a uniform legal-action reference and records connection timing, road use and native score on the same validation layouts. The existing promotion rule remains 90 of 100 layouts with at least three trips. [Implementation, checks and commands](../docs/training/one-gap-direct-2026-11-19/README.md). Implementation approval did not authorize a pilot.

### 19 November 2026 — User completed the first direct score-only pilot

The pasted transcript and local logs agree. `direct-score-pilot-01` reached the 30-minute wall budget with 250,028 decisions, 724 optimizer steps and 1,440 completed games. There were 108 successes (7.5%), best 13 and 1,213 total native trips. Every completed game spent 20 road units with no repeated draws. The first and last 100 games had 8 and 14 successes, a preliminary within-run pattern across different seeds and changing weights. Held-out performance and improvement over chance are unknown. [Run record and evidence](../docs/training/linux-direct-score-pilot-2026-11-19/README.md).

### 19 November 2026 — Direct score-only held-out comparison

Frozen initial/latest/uniform evaluation completed all 300 games naturally on the same 100 layouts. Successes 5/100 initial, 10/100 trained and 4/100 uniform. Mean native trips 0.60, 1.17 and 0.45. Trained versus initial: five wins, zero losses, 95 ties, +0.57 trips per layout (paired bootstrap 95% interval +0.12 to +1.12). Suggests modest improvement in this run. The 90/100 gate remains unmet, and all policies averaged 20 roads spent. No checkpoint updates or further training. [Results and per-game evidence](../docs/training/linux-direct-score-pilot-2026-11-19/README.md#frozen-held-out-comparison).

### 19 November 2026 — Diagnosed direct score-only credit and first-action behavior

Read-only probes of the verified pilot and frozen checkpoints. Wait accounted for 88.4% of completed-game decisions. At reset there were 457–460 legal builds plus Wait. Mean held-out exact repair probability rose from 0.218% initial to 0.490% trained, but the trained policy ranked it first on eight layouts. A board-matching control using all 9,900 mismatched observations with the correct target masks produced essentially the same repair probability and first-place rate. This failed to demonstrate board-specific gap selection at reset. Ninety of 181 logged rollout versions had zero approximate KL across all recorded epochs. Delay, action dilution and positional bias are plausible constraints, with no optimizer defect established. Proposed one-build immediate-connectivity diagnostic and conditional shared per-edge scorer. No code change or training. [Methods and saved data](../docs/training/linux-direct-score-pilot-2026-11-19/README.md#why-the-pilot-is-struggling).

### 19 November 2026 — One-build diagnostic approved and implemented

User approved one road unit and one build, with immediate reward 1 when the house and destination become connected, otherwise 0. The opt-in stage preserves the previous layouts and legal distractors and ends immediately after the build. Batches can pool independent completed episodes under one behavior version. Fifteen tests passed, including a successful scripted repair on all 100 held-out layouts, a zero-reward legal distractor, exact replay, and binary comparison. A 63-episode dry run and terminal positive-credit probe passed with unchanged weights. No new pilot. [Commands, decisions and verification](../docs/training/one-gap-single-build-2026-11-19/README.md).

### 19 November 2026 — Started the first authorized one-build pilot

User authorized starting training. Launched a fresh `single-build-pilot-01` on CUDA with 16 workers, capped at 131,072 attempts or 30 minutes. First rollout had 2/2,048 successful builds and completed four optimizer steps. Both checkpoints exist. The run was active at launch verification. [Launch and configuration](../docs/training/one-gap-single-build-2026-11-19/README.md#first-training-pilot-launched).

### 19 November 2026 — Checked one-build rollout throughput

Read-only check of the first ten active CUDA rollouts. Collection took 355.28 seconds for 20,480 build attempts versus 26.15 seconds for updates, about 93% of the two logged phases. Serial host reset, repeated same-version fingerprints and unused terminal observation work are candidates for a controlled throughput benchmark. Their individual impact is unmeasured. No live-run changes or benchmark. [Measurements and proposed checks](../docs/training/one-gap-single-build-2026-11-19/README.md#collection-throughput-check).

### 19 November 2026 — Optimized single-build collection for future runs

User approved throughput changes conditional on leaving the running pilot uninterrupted. Archived its exact source, then added parallel independent resets, rollout-boundary fingerprints and a terminal collection path that skips unused observation and GPU work. Eight tests passed. Four matched low-priority CPU dry trials with four workers and 256 attempts lowered median collection from 6.69 to 3.63 seconds (1.84×), with matching episode results and forward losses. No new training or CUDA benchmark. Existing service retained the same PID and continued producing rollouts. [Details and measurements](../docs/training/one-gap-single-build-2026-11-19/README.md#collection-speed-changes).

### 19 November 2026 — Checked whether the active one-build pilot can switch collectors

Verified the active run's atomic checkpoint at 43,008 attempts and 84 optimizer steps, with 24 Adam state entries, Python/NumPy/PyTorch CPU and CUDA RNG state, and per-worker seed counters. Current strict resume rejects changes in four recorded files (environment, collector, runner and rollout types). The native binary and policy definition are the same. A verified, narrow compatibility migration is required for cross-version resume. Resume would retain saved learning and restart at a fresh one-build episode on each worker. Attempts collected after the chosen checkpoint are absent from it. No migration, pause or restart performed during this check.

### 19 November 2026 — Resumed the active pilot with the faster collector

User authorized switching. Verified a narrow source identity migration for single-build rollout mechanics. Real-checkpoint preflight matched weights, Adam and RNG state and rejected settings and binary changes. Stopped old process at version 25, 51,200 attempts and 100 optimizer steps. Terminal counters matched the checkpoint and the new run started at the next seed. The resumed segment uses the remaining original budget and preserved the prior run directory. First optimized rollout completed four more optimizer steps, reached 53,248 cumulative attempts and collected 2,048 attempts in 20.28 seconds versus 35.11 seconds in the last original collection. Comparison is descriptive across two consecutive rollouts. Continuation active. [Handoff and measurements](../docs/training/one-gap-single-build-2026-11-19/README.md#pilot-switched-to-the-faster-collector).

### 19 November 2026 — Completed and evaluated the one-build pilot

Pilot stopped at the original wall budget. Latest saved state covers 122,880 decisions and 240 optimizer steps. The final full training rollout had 994/2,048 correct builds. Frozen held-out repairs were 46/100 sampled and 50/100 highest-probability, with 0/100 in both baselines. Swapping board observations while retaining each target's valid-action mask left exact-gap probability and first-place rate essentially unchanged. Learning is measurable, yet the probe shows no evidence of board-specific repair selection beyond the mask on this cohort. Median collection dropped from 35.13 to 18.95 seconds after handoff. Proposed keeping the binary objective and testing more varied placements against new diagnostic layouts and the same board-swap control. No promotion and no further training. [Results and measurements](../docs/training/one-gap-single-build-results-2026-11-19/README.md).

### 19 November 2026 — User chose to improve accuracy before changing layouts

After the first one-build pilot, the user chose to keep the gap placement as it is for now and improve accuracy before adding more placement variation. Continue with the existing one-build task and binary reward. The current reference is 46/100 sampled repairs and 50/100 highest-probability repairs. The earlier board-swap result still limits claims about reading the layout. No new accuracy threshold was specified and no new training was requested in this decision. [Pilot and evaluation data](../docs/training/one-gap-single-build-results-2026-11-19/README.md).

### 19 November 2026 — Started the accuracy continuation on the same one-build layouts

User authorized training and requested the live-log command. Resumed the saved checkpoint at 122,880 attempts and 240 optimizer steps into the new `single-build-pilot-02` directory. Same task and CUDA16 settings. New segment bounded by 131,072 additional attempts or 30 minutes. First rollout had 978/2,048 correct and saved 244 cumulative optimizer steps. Run was active at verification. [Launch and monitor location](../docs/training/one-gap-single-build-results-2026-11-19/README.md#second-pilot-started).

### 19 November 2026 — Same-layout continuation exposed an orientation plateau

The second one-build pilot completed its 131,072-attempt cap and saved at 253,952 cumulative attempts and 496 optimizer steps. Last five rollouts scored 49.7%. The frozen held-out checkpoint improved from 46/100 to 50/100 sampled (four paired gains) and remained 50/100 highest-probability with all 100 outcomes unchanged. Exact-action probe: solved every vertical gap and no horizontal gap. All 9,900 observation swaps left the selected action unchanged with the target mask held fixed. Proposed sharing an orientation-normalized local scorer across candidate edges while retaining user-approved layouts and reward. No further training. [Result and diagnosis](../docs/training/one-gap-single-build-continuation-2026-11-19/README.md).

### 19 November 2026 — Shared-edge policy implemented and training started

User authorized the new scorer and its pilot while retaining gap placements and binary reward. The opt-in actor uses orientation-aligned endpoint neighborhoods and shares one scorer across edges. Ten tests and a 128-attempt forward-only CUDA check passed, including translation and quarter-turn equivariance. Started fresh CUDA16 training with the same 131,072-attempt or 30-minute cap. First rollout had 2/2,048 correct from initial weights and completed four optimizer steps. Previous run and exact source snapshot preserved. [Implementation, verification and monitor path](../docs/training/shared-edge-policy-2026-11-19/README.md).

### 19 November 2026 — Checked the shared-edge cold start

First four CUDA rollouts scored 2, 5, 8 and 3 correct per 2,048 attempts, matching the first four of the previous fresh pilot at the same seed. Near-uniform exploration is consistent with this scale given roughly 460 legal builds. No evidence of learning at this early point. The new architecture did not inherit the old checkpoint's weights. Pilot left running. [Early training check](../docs/training/shared-edge-policy-2026-11-19/README.md#early-training-check).

### 19 November 2026 — Shared-edge pilot learned both orientations; short continuation started

Completed 131,072 attempts and 256 optimizer steps. Final rollout 1,480/2,048 correct. Frozen held-out evaluation: 84/100 sampled (44/50 horizontal, 40/50 vertical) and 100/100 highest-probability. Exact-gap top rank fell from 100% matched to 35.4% with shuffled observations and the same legal mask. This supports board-dependent choice on the current layout family. User delegated follow-up training if needed. Resumed to strengthen sampled accuracy with 32,768 additional attempts or ten minutes, same task. First resumed rollout 1,622/2,048, four more optimizer steps, service active. [Results, data and monitor path](../docs/training/shared-edge-results-2026-11-19/README.md).

### 20 November 2026 — Verified the shared-edge continuation result

The resumed segment completed its 32,768-attempt cap and reached 163,840 cumulative attempts and 320 optimizer steps. Final training rollout was 2,044/2,048 correct. On the fixed held-out set, sampled accuracy improved from 84/100 to 100/100 with 16 gains and no regressions. Highest-probability accuracy remained 100/100. Each mode got all 50 horizontal and 50 vertical repairs. This is the same one-build layout family and one training seed. No delivery evaluation or additional training. [Results and small evidence](../docs/training/shared-edge-results-2026-11-19/README.md#continuation-results).

### 20 November 2026 — Frozen shared-edge checkpoint generalized to diagonal gaps

User authorized a diagnostic evaluation. On 100 native test-only diagonal layouts with 50 of each slope, the final shared-edge checkpoint placed the exact missing diagonal on all 100 using sampled actions and all 100 using highest-probability actions. Scripted feasibility was 100/100; uniform legal action scored 0/100. Mean exact-gap probability 99.86%. Original training and simulation source identities preserved; isolated fixture changes reset geometry only. Applies to straight diagonal one-gap roads, not other geometry or deliveries. No training. [Fixture, methods and per-layout evidence](../docs/training/shared-edge-diagonal-evaluation-2026-11-20/README.md).

### 20 November 2026 — Frozen one-build repairs delivered traffic

User authorized automatic native delivery evaluation after a single frozen build. Shared-edge continuation checkpoint placed the exact gap on 200/200 horizontal, vertical and diagonal layouts in each of sampled and highest-probability modes. After running to 180 simulated seconds with no further policy actions, every repaired layout delivered 10–13 trips (mean 11.535); all 200 matched no-build controls failed with zero. This verifies the build plus automatic advance protocol. Autonomous wait and multiple builds are untested. No training or simulator implementation changes. [Protocol and per-layout measurements](../docs/training/shared-edge-delivery-evaluation-2026-11-20/README.md).

### 20 November 2026 — Frozen one-build checkpoint repaired two separated gaps

User approved evaluating two opportunities with two road units on 200 isolated straight or diagonal layouts. Both sampled and highest-probability frozen arms chose the two exact gaps on every board, starting disconnected and connecting only after the second build. Each repaired layout delivered 10–13 trips under automatic native advance (mean 11.26), matching scripted feasibility. Uniform repairs and deliveries were zero across 200. Local repair can repeat with updated observations; adjacent gaps, mixed directions and waiting remain untested. No training or production change. [Fixture, protocol and per-board data](../docs/training/shared-edge-two-gap-evaluation-2026-11-20/README.md).

### 20 November 2026 — Reviewed proposed construction curriculum

User proposed adjacent gaps, house driveway rotation, building a full road, and full roads with obstacles. Engineering recommendation for review: test adjacent gaps first, with the center road tile absent and exactly two builds. Then test short unfinished bends and short clear-land spans with several empty tiles. Isolate driveway rotation as a separate control exercise using an otherwise nearly complete road before combining it with construction. Follow with full routes on clear land, then one-obstacle detours. Use minimum scripted builds to verify fixtures and native deliveries for layouts that admit multiple valid routes. Maintain separate construction and waiting checks. Ordering is a proposal, with no implementation, evaluation, or training authorized by this discussion. [Current two-gap evidence](../docs/training/shared-edge-two-gap-evaluation-2026-11-20/README.md).

### 20 November 2026 — Completed five construction exercises with one checkpoint

User authorized all five exercises and asked to continue through verification and document every run. Implemented opt-in native exercise fixtures with unchanged traffic mechanics, explicit driveway rotation/Finish, and blocked-aware legality. Scripted smoke passed 150/150 and full feasibility 500/500. Original frozen policy scores: adjacent 100, bend 51, driveway 25 originally served with no rotation action, clear 33, obstacle 0, all per 100. Trained one shared spatial scorer with masked behavior cloning on 512 layouts per stage and 7,171 legal demonstrations, 36 epochs, CUDA. Exact choice and delivery matched the scripted reference on all 500 held-out boards in each of sampled and highest-probability evaluations. Three-delivery gate passed 100/100 per stage. All 75 wrong driveways corrected and all 25 correct driveways left alone. No PPO updates in this curriculum run. Automatic advance, predefined fixture families, single training seed. Checkpoints and builds local; no run active. [Every run, sources and results](../docs/training/construction-five-stage-2026-11-20/README.md).

### 20 November 2026 — Frozen construction policy tested on incompatible pairs

User requested two homes, blue home/red destination and two destinations. Evaluated each plus a blue/blue control on 100 native fixtures in sampled, highest-probability and extra Finish-offered modes. All built in every case. Default highest-probability physical links: 100 matching, 100 mismatched, zero two-home and 23 two-destination. Only matching scenes delivered. The original mixed-pair encoder produced identical tensors and masks when only color differed. Exposing the driveway-trained Finish action did not yield any no-build outcomes. Same-type fixtures used a documented absent-role observation adapter. No weights changed or training. [Protocol, isolated patch and measurements](../docs/training/construction-pair-compatibility-2026-11-20/README.md).

### 20 November 2026 — User reiterated independent route discovery as a priority

The user expressed concern that imitating scripted routes could make the model favor the teacher's solutions, and connected that concern to the existing constraint against a construction route planner. The five-stage checkpoint exactly reproduced the reference sequences on its evaluation set. That shows demonstrated proficiency and leaves independent route discovery, alternative routing and recovery unverified. Engineering recommendation for the next approved learning run: use a reward-trained policy as the starting point, keep physical-only masks and scripted routes in feasibility checks, and evaluate useful deliveries and road usage across layouts with multiple valid solutions. The imitation checkpoint remains a separate diagnostic. No algorithm switch or training was authorized by this discussion.

### 20 November 2026 — Proposed reward-only PPO restart point

Engineering recommendation pending user approval: start from the reward-trained shared-edge checkpoint and target unfinished bends first. It already passed adjacent gaps at 100/100 and achieved 51/100 on bends. Retain two or three paused legal builds depending on the fixture and binary terminal connectivity reward, then evaluate native deliveries with automatic advance. Include layouts verified to admit multiple solutions and treat all successful routes equally. Scripted paths remain feasibility checks, outside policy observations, rollouts and updates. Compare against the same checkpoint before the pilot and rerun previous repairs to catch regressions. Keep visible color and Finish on mixed or incompatible pairs as a separate skill. No implementation or training ran during this proposal.

### 20 November 2026 — Started reward-only PPO on unfinished bends

User approved going ahead and requested a live command. Added a bounded Maskable-PPO runner for the existing native bend fixtures. Warm-started weights from the reward-trained shared-edge checkpoint and started a fresh Adam optimizer. No imitation checkpoint or reference action in the rollout path. Compact adapter matched the original observation planes and masked logits in CUDA preflight. CUDA16, 131,072 decisions or 30 minutes, terminal connectivity reward. First rollout reached 141/813 training connections. [Protocol and live log](../docs/training/reward-only-bend-ppo-2026-11-20/README.md).

### 20 November 2026 — Reward-only PPO bend pilot passed with alternative working roads

Reached 131,072 saved decisions in 176.36 seconds, 64 rollouts and 256 PPO epochs. Offline verified 75/100 training and 75/100 validation bends with two distinct working routes, independent from PPO. Held-out bend passes improved sampled 22/100→100/100 and highest-probability 51/100→100/100. Adjacent regressions none: sampled 97/100→100/100 and highest-probability 100/100→100/100. Every final board survived 180 seconds and bends averaged 11.18 native deliveries. Model used different edge sets from the scripted reference on 52 sampled and 36 highest-probability bends. No teacher actions in PPO. Same fixture family, one seed, native automatic advance. No additional training. [Saved run and per-board evidence](../docs/training/reward-only-bend-ppo-2026-11-20/README.md#completed-run-and-held-out-results).

### 20 November 2026 — Proposed frozen empty-road assessment after the bend PPO pass

Engineering recommendation pending approval: evaluate the new reward-trained bend checkpoint on the existing short clear-land layouts, starting with no supplied road tiles. Keep the legal single-edge control, native inventory and automatic traffic advance so the new challenge is initiating and extending a route. Compare against the earlier 33/100 highest-probability reference, break down by distance and offset, and count valid delivery routes regardless of their edge sequence. If below the 90/100 three-delivery benchmark, start reward-only PPO on the short empty-road skill and recheck adjacent and bend performance afterward. Driveway rotation and compatibility/abstention introduce separate action or input requirements. No evaluation, implementation or training in this proposal.

### 20 November 2026 — Started the reward-only clear-road pilot

User approved the next move. The frozen bend checkpoint scored 0/100 highest-probability and 3/100 sampled on clear roads, while remaining 100/100 on adjacent gaps and bends. Opt-in residual scorer adds visible driveway-relative geometry to the PPO parent and starts with zero output. Preflight matched initial masked logits. CUDA16 pilot, 131,072 build decisions or 30 minutes, clear plus two earlier skill rehearsals, one terminal connectivity reward and no teacher data. [Baseline, settings and monitor](../docs/training/reward-only-clear-roads-2026-11-20/README.md).

### 20 November 2026 — Clear-road PPO improved to 66/100 and exposed the two-tile offset gap

Saved 131,072 decisions and 256 PPO epochs in 192.98 seconds. Both modes reached 66/100 on clear land, from 3 sampled and zero highest-probability. All 66 aligned or one-tile-offset layouts passed; all 34 two-tile-offset layouts failed. The policy still passed every bend and adjacent gap. Clear-land gate unmet. No teacher data. Proposed targeting two-tile offsets in the next authorized pilot with rehearsal. No further training or obstacle promotion. [Final metrics and records](../docs/training/reward-only-clear-roads-2026-11-20/README.md#completed-pilot).

### 20 November 2026 — Targeted offset PPO launched

User approved the two-tile offset experiment. Offline reference probabilities exposed an overconfident starting policy. Isolated distance-2 feasibility and original-host parity passed. Resumed saved weights and optimizer, broadened the rollout distribution with temperature and balanced six workers per sign with four rehearsal workers. Advances length after both directions reach the scripted-free rollout criterion. No teacher data. Initial launch failed on a missing import before training; corrected and relaunched to a fresh directory at the 131,072-decision/30-minute cap. First current rollout left 7/384, right 5/384. [Preflight, launch and live log](../docs/training/reward-only-offset-ppo-2026-11-20/README.md).

### 20 November 2026 — Offset warm-up passed but standard routes regressed

Distance-2 warm-up met its advancement rule, but 16 distance-3 rollouts yielded one success in 6,696 targeted episodes. Offline probability probe put the median combined chance of verified two-paid-edge sequences at 9.76e-10 at training temperature; it excluded other action sequences. Stopped early at saved boundary: 67,584 new decisions, 16 fresh attempts discarded. Service cleanup did not alter saved state. Frozen shortest variant 100/100; standard clear fell 66/100→33/100 in both modes, losing all one-tile offsets and solving none of the targeted standard two-tile offsets. Adjacent and bends retained 100/100. Do not promote this checkpoint. No additional training. [Evidence, runs and hypothesis](../docs/training/reward-only-offset-ppo-2026-11-20/README.md#final-result-and-early-stop).

### 20 November 2026 — Started spare-stock PPO from the 66/100 parent

User approved two extra road units for exploration in shortest two-build offset training while retaining original evaluation stock. Separate host verified normal fixture parity and six scripted feasibility cases across surplus levels and both signs. Exact warm weights and Adam restored. Targeted-only temperature, increased easy clear rehearsal and unchanged binary reward, no planner or example actions. First rollout 1/100 left and 0/100 right. Run capped at 131,072 decisions/30 minutes, with small-signal stopping rule. [Settings and monitor](../docs/training/reward-only-spare-stock-2026-11-20/README.md).

### 20 November 2026 — Spare-stock PPO exposed the free-driveway edit cap

Both surplus phases passed. At two paid units the learned route in six paired probes used two free parcel attachments and two paid links, while the harness allowed only three edits. The early zero-spare checkpoint at 186,368 decisions passed 100/100 highest-probability and 98/100 sampled with identical native stock and one more edit allowed; two-offset passes 34/34 and 33/34. Both earlier skills stayed 100/100. Under the old cap the same checkpoint scored 33 and 34. The previous 66/100 parent did not improve by merely allowing the extra edit. After 16 strict zero-spare rollouts without a target success, the late checkpoint lost the hard-road gain; stopped at 212,992 saved decisions (81,920 new) with prior checkpoints intact. A first threaded diagnostic raced over distribution state, corrected by serializing inference and rerunning. The stock-only gate passes on the reused suite, with independent new-board verification pending. No further training. [Full paired evaluation and trace data](../docs/training/reward-only-spare-stock-2026-11-20/README.md#outcome-and-the-edit-limit-finding).

Independent follow-up of the selected checkpoint used fresh seeds 36200–36299: original paid stock plus two free attachment slots, 100/100 highest-probability, 100/100 sampled, zero stock violations. [Saved measurements](../docs/training/reward-only-spare-stock-2026-11-20/README.md#independent-verification).

### 20 November 2026 — Bounded work session and frozen obstacle transfer

The user delegated up to one hour. On the active Linux training checkout, created local `mohammad` at the preserved `6bd7f71` starting point to follow current branch instructions. The existing stock-only PPO checkpoint solved the standard two-block layouts 100/100 greedy in each of two independent cohorts, and 94/100 then 89/100 sampled. Each success delivered at least three trips at original native stock. The same road scorer failed all empty wider/offset three-block variants in both modes. [Cohorts, settings and measurement files](../docs/training/reward-only-construction-hour-2026-11-20/README.md#frozen-obstacle-transfer).

### 20 November 2026 — Reward-only driveway and isolated pair PPO

Extended the reward-trained road actor with an opt-in driveway/Finish head. Verified road probability parity and froze its weights. At 65,536 decisions, driveway correctness was 100/100 in each frozen mode, including 75 repairs and 25 correct no-edits, with native delivery. The first CPU/CUDA parity check failed before learning and was corrected. A later longer-board probe exposed an off-map neighborhood index, corrected before repeating it. Pair pilot 01 collapsed to Finish, scoring zero on matching pairs after 98,304 decisions. Pilot 02 reintroduced matching service but failed two destinations at 131,072. Pilot 03 used a training-only commitment warm-up; the frozen 163,840-decision checkpoint passed all five pair classes 100/100 in each mode on fresh boards, with repeated Finish choices legal. The pinned intermediate had 98/100 sampled matches and was the terrain parent. The three changes were bundled and their causal contributions are unknown. [Every run, learning graph and per-layout data](../docs/training/reward-only-construction-hour-2026-11-20/README.md).

### 20 November 2026 — Target selection and actual elapsed-time score

Native color swaps on identical competing-home layouts showed empty-road transfer at 0/100 greedy and 1/100 sampled per swap for the isolated-pair policy. Supplying the matching anchor as an evaluation control left the same result. A reward-only learned target weighting on one-gap branches reached 100/100 on each independent color-swap set in both modes and transferred to two missing links at 100/100 greedy and at least 97/100 sampled. Three missing links and full builds remained harder. The terrain residual learned wide detours with 100/100 greedy and 97/100 sampled at original paid stock after 262,144 decisions, but shifted starts reached 46/100 and 54/100 and the earlier obstacle suite regressed. The score-only Build-or-Wait pilot learned 100/100 sampled with one gap and 90/100 with two. Individual-action greedy waited throughout 55 two-gap failures, and grouping build mass reduced this to 33. Native trip scores were the only rewards in that pilot. [Protocol, limits, run histories and exact native outcomes](../docs/training/reward-only-construction-hour-2026-11-20/README.md).

### 20 November 2026 — Three-gap and elapsed-time gates passed

Resumed the branch scorer to train on three gaps with earlier branch rehearsal. Independent mirrored layouts scored 100/100 greedy and 99/100 or 98/100 sampled. The full-build continuation improved fresh sampled work to 91/100 and 84/100, while greedy exhausted the road budget on all empty-board layouts. The second score-only run added a learned correction from observed loose road ends and matched the first pilot at initialization. After 65,536 further decisions it achieved 100/100 in each of the zero-, one-, and two-gap cases, in greedy and sampled modes on both cohorts. The time and available decision limits remain experimental conditions. [Results and controls](../docs/training/reward-only-construction-hour-2026-11-20/README.md).

### 20 November 2026 — Exact-stock shifted detours and frozen full-build diagnosis

Moving the terrain actor directly to original stock improved shifted layouts to 62/100 greedy and 59/100 sampled on a fresh test. On that cohort, greedy solved 42/50 one-tile offsets and 20/50 two-tile offsets. A same-weight guard restores the base policy on the two-block standard fixtures, with bit-for-bit action distribution checks. Hard-offset rehearsal then brought shifted performance to 93/100 greedy and 85/100 sampled on each independent cohort. Wider-barrier sampled performance fell to 82/100 and 83/100, so its previous checkpoint remains the reference. For empty competing-home boards, using only the highest-weight target component failed in both modes. Sampling the first one, two or three moves before switching to greedy raised performance progressively, with 63/100 for both color swaps after three sampled moves. Final totals are 12 bounded PPO runs and 1,441,792 new saved decisions. All training ended. [Checkpoint selection, native fixture evidence and control traces](../docs/training/reward-only-construction-hour-2026-11-20/README.md).

### 20 November 2026 — Diagnosed and started the competing-home stub curriculum

User authorized up to an hour for the proposed replay, stub curriculum and verification. Replayed 400 frozen native traces from the two mirrored fresh suites. All 200 greedy failures crossed an optimistic remaining-stock bound on a paid edit that made no progress toward a connection, on edits three through six. All 175 sampled successes retained enough stock by the same test. The bound remains offline. Verified 32 native witnesses for short stubs at both ends or the shop alone. Started two bounded PPO runs from the preserved sampled full-board checkpoint, one with existing architecture and Adam, and one with a zero-initialized position-and-inventory scorer. Both use native legality and the same terminal connection reward. Three-gap gates and the follow-on scored Wait pilot remain conditional on held-out results. [Exact replay, fixture patch and launch details](../docs/training/competing-homes-2026-11-20/README.md).

### 20 November 2026 — Empty-road selection passed and native score-only timing started

The stub continuation's rollout-64 checkpoint used original road stock and served fresh empty boards at 100/100 greedy on both sides and 93/100 and 98/100 sampled. Three-gap checks remained at 100/100 greedy and at least 95/100 sampled. The original greedy suite now had no stock deficits. A frozen uneven-distance test reached 96/100 and 100/100 greedy, and 91/100 and 93/100 sampled. The static frame-only alternative lagged on development. Started a third construction arm with observed current component context, plus two native score-only timed arms after the route gate passed. Each timed choice is one legal road edge or ten seconds of Wait, with 18 decisions and the original paid stock. Early direct Wait transfer over-waited, so the second arm began at 20% Wait whenever draws remained. [Outcomes, native controls and in-progress settings](../docs/training/competing-homes-2026-11-20/README.md).

### 20 November 2026 — Full roads and native delivery timing verified

The current-road-context checkpoint passed 100/100 greedy and 99–100/100 sampled on both mirrored and unequal-distance boards, retaining the three-gap repair gate. The empty-board-only control also scored 100/100 greedy and 99/100 sampled on both fresh mirrored assignments. It met the observed development gate earlier than the stub schedule from the same checkpoint and Adam. Its comparison establishes that stubs were optional for this continuation. The selected timed network scored 100/100 greedy and 99–100/100 sampled on two mirrored cohorts, and 100/100 greedy and 98–100/100 sampled on unequal distances. A joint score-only continuation improved over the first timing model and retained high test accuracy. Frozen floor controls found that explicit driveway attachments spend two choices the native simulator can perform automatically during paid construction. The attachment-logit pilot favored explicit attachments and did not close the score gap. A five-second Wait control with 29 choices retained the pass rates. Nine bounded PPO runs ended after 1,146,880 new decisions. [All runs, timed score, evidence, and checkpoint identities](../docs/training/competing-homes-2026-11-20/README.md).

The selected frozen timed checkpoint then passed 2,000/2,000 greedy and 1,983/2,000 sampled in a larger unopened suite of mirrored and uneven scenarios, using the original stock and 18 choices. Greedy chose Wait in 2,408/2,408 post-connection states with other legal actions on the separate unequal-distance replay check. An extra-two-choice same-board control brought greedy scores to 8.73–8.75 mean deliveries, with 7.46 at 18 choices and 8.75 for the 18-choice native witness. This supports a choice-efficiency explanation for most of the remaining score difference in these fixtures. No learned state changed in these controls. [Large-suite data and replay controls](../docs/training/competing-homes-2026-11-20/README.md#larger-frozen-validation).

### 21 November 2026 — Demand priority and traffic curriculum

The user authorized work on the priority and congestion milestones and extended the work window to two hours. The live checkout is `/home/mohammadjaffal/mini_motorways` on `mohammad`, base `6bd7f71` with pre-existing local changes. The training path uses per-edge native legality and Wait with native trip increments as the only reward. Prior isolated checkpoints remain available.

The first two-pair fixture delivered zero under both road controls because the shop access faced the wrong way. After the isolated native fix, both roads delivered. A 32,768-decision shared-edge PPO reached 163/200 greedy and 160/200 sampled higher-demand choices. Supplying visible existing components raised that to 200/200 and 191/200 after a separate 32,768 decisions. A third policy with a learned interaction between visible demand and existing reachable road reached 200/200 greedy and 196/200 sampled after 24,576 decisions. Mean frozen score was 13.70 greedy and 13.49 sampled across 200 boards. Evaluation reused the same board across demand swaps, with seeds disjoint from training. The three runs used fresh weights and no teacher data. The supplied roads and a single paid gap per pair bound the demonstrated skill.

The first shared-road calibration showed queues in heavy traffic but a near tie between routes in light traffic. After holding the second demand source fixed and shortening the bypass in the two-unit competition, matched native controls showed shared route plus feeder at 14.73 vs 13.16 in light traffic, and bypass at 36.43 vs 29.86 in heavy traffic. The heavy bypass reduced average sampled stopped cars from 6.61 to 0.96. A separate one-unit network already in service gained 3.05 heavy trips from the bypass and reduced stopped cars from 4.45 to 0.46. Light traffic gained 3.49 trips from the feeder. Offline native passage checks confirmed second-destination cars physically used the opened bypass. These controls are outside policy observations and training. [Fixture history, experiment runs, and measurements](../docs/training/traffic-milestones-2026-11-21/README.md).

### 21 November 2026 — Two-unit congestion choice and live relief passed in scoped fixtures

After 36,864 reward-only PPO decisions, the two-unit policy picked shared plus feeder on 94/100 light layouts greedily and 89/100 sampled. The heavy two-link bypass was completed on 100/100 greedy and 98/100 sampled. Greedy heavy score and stopped-car means matched the bypass control at 36.43 and 0.96. A separate live policy, also trained for 36,864 decisions, opened a bypass on 100/100 heavy and chose a feeder on 100/100 light layouts greedily. Sampled results were 94/100 and 91/100. Greedy heavy score was 32.04 versus 29.03 for expanding the feeder, and stopped cars averaged 0.48 versus 4.45. A 40-pair input switch raised mean bypass probability from 10.35% to 61.03% when only visible vehicle-motion inputs changed, with a separate increase to 43.25% from visible demand inputs. The live policy did poorly on mirrored approach geometry or a relocated gap, motivating a continuation that withholds their combination. Three-pair and earlier-in-time waiting experiments were added within the same user-authorized window. [Exact traces and learning runs](../docs/training/traffic-milestones-2026-11-21/README.md).

### 21 November 2026 — Three-destination priority passed and interrupted runs were archived

The 36,864-decision three-destination checkpoint served both higher-demand shops on 200/200 greedy and 192/200 sampled boards with two units of native stock. A reflection control restored heavy score on the mirrored original gap from 29.29 to 32.04, while the relocated gap still failed to transfer. The road-end pilot initialized a learned interaction based on visible degree-one endpoints and saved no updated checkpoint. The two pre-surge timing runs saved 23,040 and 10,752 added decisions. The varied-junction and integrated rehearsals saved 15,360 and 4,608 added decisions. These four final checkpoints lack frozen tests, and a frozen intermediate of the five-second timing arm still favored the shared feeder under heavy demand. The matching-component variant ended at its wall limit with 43,008 saved decisions. Across 12 runs including initialization-only, the session saved 297,472 added decisions. The follow-up process check after interruption found no active training. [Run ledger, archives, and limits](../docs/training/traffic-milestones-2026-11-21/README.md#run-ledger-and-local-state).

### 21 November 2026 — Frozen continuation retained score and failed bypass transfer

The user approved frozen testing before another training run. The saved geometry continuation at 52,224 total decisions and its 36,864-decision parent faced the original, moved and combined mirrored-and-moved gap, each under light and heavy traffic at 100 fresh paired seeds. The continuation kept original heavy greedy trips at 31.83 versus 31.85 but reduced bypass use from 99/100 to 86/100. On the moved heavy gap, 27.39 rose to 29.73 deliveries and early endings fell from 19 to two as the actor started choosing the feeder. It used the bypass only 7/100 times and averaged 3.86 stopped cars versus 0.41 for the native bypass. On the held-out combined geometry the continuation chose the feeder 100/100 greedily and averaged 29.26 trips versus 31.73 for the bypass. Light feeder choice remained 298/300 greedily. Across 4,200 replays, seeds, stock, scores and policy fingerprints checked out. No training ran. The original junction checkpoint remains the reference there. The initialized road-end scorer is a proposed follow-on for multiple gap positions. [Matched replays and run commands](../docs/training/junction-transfer-2026-11-21/README.md).

### 21 November 2026 — Started road-end learning across multiple gap positions

The user approved work on bypass recognition after the transfer replay. The previous endpoint initialization had no completed update. Started it in a new run directory and added a separate shared scorer using visible road-end counts, current shop components and traffic without actor position inputs. Isolated native fixture variations moved the gap to three additional positions along the same bypass. In 24 paired boards per training variant, the new heavy bypass controls gained 2.46–2.96 deliveries and reduced mean stopped cars from 4.16–4.21 to 0.42–0.48. Light controls still favored the feeder. Verified actor reflection parity on three native observations. Bounded reward-only PPO began with separate training seeds, a reserve middle gap, and original-junction retention checks planned. [Fixture patch, launch details and evidence](../docs/training/road-end-transfer-2026-11-21/README.md).

### 21 November 2026 — Bypass location transfer verified on the live junction family

The endpoint residual saved 39,936 decisions at the wall budget. It opened all 300 heavy changed bypasses greedily and used the feeder on 173/300 corresponding light boards. The coordinate-independent base saved 40,960 and improved the light choice to 300/300 on those changed layouts with 265/300 heavy bypasses. Native controls with stronger traffic showed a larger score advantage for bypassing. A mixed-pressure continuation from the base's 30,720-decision checkpoint added 24,576 PPO decisions with the same native trip reward, then tested at standard pressure. It opened 297/300 changed heavy bypasses greedily and 283/300 sampled, and used the feeder on 400/400 light boards greedily and 392/400 sampled. Independent additional geometry combinations gave 123/128 heavy and 128/128 light correct greedily. Select the mixed-pressure checkpoint for this fixture family. All 105,472 added decisions are saved, no training is active, and the next timing question remains open. [Run ledger, frozen data and reproduction](../docs/training/road-end-transfer-2026-11-21/README.md#selected-checkpoint).

### 21 November 2026 — Started one-hour pre-surge timing study

User authorized an hour of further curriculum work. The selected road-end actor had about 0.7% initial Wait probability at second 15 and a strong cue-conditioned action difference by second 35. Started matched joint and Wait-only PPO arms with a one-time +4.6 Wait logit exploration offset and a voluntary 20-second Wait. The first Wait-only launch stopped before learning because SB3 deserialized the topology head class by value. Corrected the saved class check and relaunched in a new output directory. Calibrated stronger native pressure at the second destination and started an extra arm with the road scorer fixed. The reward remains native deliveries. Held-out evaluation includes the biased initialization, immediate fixed controls, delayed controls, and reserved gap geometry. [Entry conditions and controls](../docs/training/wait-before-surge-2026-11-21/README.md).

The timing study added a separate clock-dependent exploration arm with fresh Adam and a frozen road scorer. The trainable initial Wait adjustment fades between seconds 15 and 35, allowing initial exploration before the cue and preserving the parent's post-cue preferences. Mid-run frozen probes raised Wait probability around second 15 from 0.40 to 0.67 but found very little Wait at second zero. Started an earlier-start continuation with warmup sampled across seconds 0–15, ten-second Wait, and ordinary and later surge fixtures. Frozen versions before and after the timing updates are retained for comparison. [Timing hypotheses and run design](../docs/training/wait-before-surge-2026-11-21/README.md).

The clock-dependent Wait run saved 29,184 added decisions. The frozen policy waited first on 316/320 contrast validation boards greedily versus 134/320 for its exploration initialization. It used the correct road at second 35 on 311/320 and averaged 38.14 trips, above 36.59 for the best immediate controls. Standard-traffic transfer gained 0.64 greedy trips over the corresponding best immediate reference. The same policy did not beat the immediate reference when the pulse moved to seconds 24–28. On those boards it delayed in every greedy game, but selected the heavy bypass at second 35 only 33/50 times. Began route-head rehearsal at seconds 34–39 with the Wait head frozen to address the later-cue failure. [Frozen evidence and contrasting runs](../docs/training/wait-before-surge-2026-11-21/README.md#learned-to-hold-the-road-unit-before-the-normal-surge).

### 21 November 2026 — Learned cue-dependent delay at five-second cadence

The fine-cadence continuation added 20,480 decisions. It began with Wait on 512/512 greedy held-out episodes from second 15. It chose the bypass on 128/128 normally timed and 116/128 later-pulse heavy cases. In paired traffic tests, shifting the event from seconds 16–20 to 24–28 shifted the median heavy commitment from second 35 to second 40 in both geometries. Seventy-seven of 128 heavy pairs committed later and all 128 corresponding light pairs retained their timing. Mean greedy score beat the best fixed immediate control by 1.39 trips on normal contrast and 0.58 on later contrast. Sampled later-pulse score remained approximately level with the immediate benchmark. The earlier-start continuation added 24,576 decisions but committed immediately from second zero in greedy evaluation. The route-only late-cue continuation gained slightly on the later pulse and reduced score on ordinary timing, so it was not selected. Seven bounded learning runs saved 180,224 added decisions during the delegated hour. Keep the coarse clock model for standard second-15 timing and the five-second model for variable pulse timing. [Paired scores, learning graph and replays](../docs/training/wait-before-surge-2026-11-21/README.md#five-second-decisions-adapt-to-a-later-pulse).

The final frozen substitution check paired two heavy pulse schedules at the same clock and geometry. Before the pulse, inputs and masks matched on all 32 boards. At second 36, swapping only ordinary-surge vehicle channels into late-surge states lowered mean Wait probability from 46.0% to 28.9%. Swapping only pins and warnings lowered it to 44.8%. This adds cue sensitivity evidence alongside the native timing replays. Selected coarse and fine checkpoint subsets reproduced 64 and 128 frozen episodes exactly. [Feature and replay records](../docs/training/wait-before-surge-2026-11-21/README.md#reproduction-and-next-open-decision).

### 21 November 2026 — Prepared a runnable growing-city preflight

The user requested something runnable for the first growing-city milestone. Added a native ordinary-road mask and single-edge command, a Gymnasium adapter on the published visible encoder, and a launcher that builds the current source in a fresh ignored output directory. The road-only adapter selects the offered weekly package with the greatest native concrete award. On Los Angeles seed 2004 the fixture started with zero roads and spent four units on four paused links. It scored first at second 13, received 20 road units at second 140, grew from two to 11 buildings and ended naturally at 212.1 seconds. Reward matched 14 native trips. A separate probe completed 157 legal draws on six seeds with unchanged observations around mask queries. Existing 14 construction and observation tests passed. This verifies the game loop before selecting a starting checkpoint and freezing a city baseline. No training ran. [Runnable preflight and evidence](../docs/training/city-road-preflight-2026-11-21/README.md).

### 22 November 2026 — Growing-city throughput benchmark

The user asked whether the overnight run would use the PC effectively. Measured the actual native city adapter and SB3 subprocess observation and mask paths on the Ryzen 9 3950X and checked CUDA on the RTX 2080 Ti. Collection rose from 319 decisions/s at four workers to 1,054 at 32. In matched short repeats, 32 workers reached 1,070 and 1,084, 40 reached 1,081 with less RAM available, and 48 reached 1,050. A separate 40-second 32-worker run processed 48,192 decisions. Choose 32 as the first collector candidate, then compare actual policy and update throughput at 16, 24 and 32 with peak RAM, VRAM and temperatures before the overnight run. The benchmark was collection-only. [Measurements and reproduction](../docs/training/city-throughput-2026-11-22/README.md).

### 22 November 2026 — Growing-city starting checkpoint (milestone 1)

The user authorized completion of the first overnight milestone. On `mohammad` at `6bd7f71` plus local adapter changes, prepared one city Maskable PPO policy, copied the timed triad endpoint and edge scoring tensors, and initialized the city context, Wait head and critic with a fresh optimizer. Chose the transfer checkpoint after the sampled frozen games scored 22 and 15 on seeds 2004 and 16005 versus zero on both matched fresh-initialization runs. Both transferred runs reached the road-stock award and native game-over. Greedy seed 2004 waited throughout and scored zero. In a connected handover the frozen actor scored 18 and reached the weekly award. Reused scorer logits matched on 256 interior edges within 0.00000191; the checks also verified native masks, PPO gradients without optimizer steps, and prediction parity after reload. The 14 existing tests passed. Save `output/training/city-road-start-01/city-start.zip` as the starting point for independent frozen baselines. No city training or weight updates ran. [Reproduction and evidence](../docs/training/city-policy-start-2026-11-22/README.md).

### 22 November 2026 — PPO branch correction

The user directed that training work continue on `Maskable-PPO`. Switched the existing Linux training checkout from `mohammad` to `Maskable-PPO`. Both local refs pointed at `6bd7f71`. Verified that tracked edits, index contents and untracked paths matched across the switch. The [starting checkpoint](../docs/training/city-policy-start-2026-11-22/README.md) and its parent still match their recorded hashes. The archived report retains the branch used for the frozen checks. No training ran.

### 22 November 2026 — Frozen growing-city baseline (milestone 2)

On `Maskable-PPO` at `6bd7f71` plus the local city implementation, completed 160 frozen city games across five matched conditions and 32 fresh Los Angeles seeds. Sampled transfer scored on 24/32, averaged 32.19 deliveries, peaked at 94, and survived a median 259.75 seconds. Greedy transfer drew no roads. The fresh architecture and both uniform controls also averaged zero. Sampled transfer reached a weekly award on 30/32 games and ended out of stock on 24/32. Six of its eight zero-score games ended with stock still available. The matched-Wait control separates the benefit of the transferred road scorer from the initial Build/Wait balance. All games reached native game-over. The evaluator used eight CPU workers and the existing saved checkpoint, whose hash was unchanged. Both random controls and 14 construction/observation tests passed. Keep the suite separate from training and checkpoint selection. The next milestone is the short score-only PPO pilot. [Evidence, seeds and command](../docs/training/city-frozen-baseline-2026-11-22/README.md).

### 22 November 2026 — First growing-city score-only PPO pilot (milestone 3)

The user directed proceeding to the pilot on `Maskable-PPO`. The bounded CUDA run used the existing construction-transfer checkpoint, 16 native workers, 128 decisions per worker, and delivery-only reward. It completed 24,576 decisions and 76 games in 112.64 seconds, saving at 12,288 and 24,576. The learner reached 218.18 end-to-end decisions/s and PyTorch reserved up to 846 MiB CUDA memory. In 144 frozen development games the sampled mean was 35.46 before training, 38.58 halfway and 34.83 at the end. All three scored on 21/24 development seeds. The halfway paired mean gain was 3.13 with bootstrap interval −7.17 to +13.25. Greedy averaged zero at all three checkpoints. Preserve the frozen start as reference and both pilot saves, with the midpoint the better pilot candidate on this suite. All reserved test seeds were held back, all existing 14 tests passed, and the starting ZIP hash remained unchanged. An overnight worker setting still needs an actual PPO sweep. [Full results, seed boundaries, performance and commands](../docs/training/city-score-pilot-2026-11-22/README.md).

### 22 November 2026 — End-to-end city PPO worker benchmark

The user approved the actual learner throughput comparison. On `Maskable-PPO` ran six isolated 12,288-decision CUDA trials in order 16, 24, 32, 32, 24, 16. Every trial reloaded the selected frozen transfer checkpoint and kept the pilot's batch and optimizer settings. Mean rates were 220.2, 238.1 and 256.9 decisions/s for 16, 24 and 32 workers. Mean collection time dropped from 29.8 to 21.6 seconds, while PPO update time stayed near 26 seconds per trial. Select 32 workers for the initial overnight configuration. At that setting the two short trials kept at least 12.9 GiB RAM available and reached a sampled GPU peak of 72 °C. Total 73,728 benchmark decisions used the training-only seed range and temporary weights. The parent hash was unchanged, the 14 existing tests passed, and the overnight run has yet to start. [Trial logs, resource samples and reproduction](../docs/training/city-ppo-worker-benchmark-2026-11-22/README.md).

### 22 November 2026 — Eight-hour launch and resume verification

The user requested an eight-hour command to run locally. Prepared a 32-worker score-only city PPO launcher using the existing construction-transfer checkpoint. Engineering choices were a roughly 15-minute checkpoint cadence, hourly development candidate sampling, and highest sampled mean deliveries among candidates that score in at least as many development games as the start. On `Maskable-PPO`, a four-worker smoke restored optimizer state, epoch counts and seed cursors after SIGTERM and terminal-style Ctrl+C, ending at 8,192 decisions. A separate 32-worker smoke reached 4,096 and verified saving. Disposable seeds checked the development-to-reserved review, and a test rejected a changed actual reserve checksum. The original start hash matched, the real development and reserved suites were untouched, and 14 existing tests passed. The eight-hour run has yet to start. [Command, resume and archived checks](../docs/training/city-overnight-launch-2026-11-22/README.md).

### 22 November 2026 — Completed eight-hour growing-city PPO run

The user launched the 32-worker road-only Los Angeles run on `Maskable-PPO`. It completed 7,008,256 decisions and 16,197 episodes, averaging 243.3 decisions/s. The development review selected the 6,234,112-decision checkpoint, whose sampled mean was 101.75 versus 35.46 for the start and 88.92 for the final save. On 32 reserved cities sampled deliveries rose from 32.19 to 95.44, with 26 wins, three ties and three losses. Greedy improved from zero to 21.50. Four selected sampled games scored zero and nine hit the 600-second cutoff. Keep the development-selected checkpoint as the road-only reference and retain the start as comparison. All checkpoint and evaluation-seed hashes matched. [Results and archived evidence](../docs/training/city-overnight-results-2026-11-22/README.md).

### 22 November 2026 — Frozen overnight city diagnostics

On `Maskable-PPO` evaluated the selected overnight 6,234,112-decision checkpoint without updates. The 32 opening replays scored on 12, including 7/8 for one previously zero-score city. Nineteen of the 20 zero-score replays exhausted starting stock by second 14. Four independent native route witnesses delivered using 5–7 road units. On 24 fresh longer games, five passed 600 seconds and continued delivering until failure at an unsupplied destination. Six shorter/longer prefixes matched and the original four zero-score games reproduced. The changed adapter exposes diagnostic connectivity and an independent evaluation horizon with the existing behavior as defaults. The native preflight and 14 existing tests passed. The next proposed experiment targets opening stock timing and destination coverage. [Traces, witnesses and commands](../docs/training/city-road-diagnostic-2026-11-22/README.md).

### 22 November 2026 — Bounded score-only hard-opening continuation

The user authorized the next road-only continuation. On `Maskable-PPO`, restored the seven-hour overnight checkpoint and Adam state, mixed 16 closed-opening and 16 ordinary workers, allowed 1,200 simulated seconds with the original observation clock, and used learning rate 0.00005. The bounded job finished 65,536 added decisions and 201 episodes in 288.02 seconds. On 96 paired frozen games, hard-opening success was 2/16, 3/16 and 2/16 for the parent, midpoint and end. Early exhaustion in the hard cohort was 16/16, 15/16 and 16/16. Ordinary means were 133.63, 91.63 and 86.38. Neither candidate replaced the overnight reference. All 14 existing tests passed, model hashes matched, and the real reserved suite remained unused. [Run and evaluation evidence](../docs/training/city-opening-pilot-2026-11-22/README.md).

### 22 November 2026 — Overnight game examples

The user asked for a best, average and worst example. Used the selected overnight checkpoint's 32 sampled reserved games and replayed the highest score, the closest score to the 95.44 mean, and the earliest game-over among zero scores. The three were 175, 85 and zero deliveries. The replay matched the archived end times, scores and decisions. Generated local offline HTML viewers and archived action sequences, hashes and the regeneration command. Browser controls passed on the three pages. No training ran. [Replay details](../docs/training/city-overnight-replays-2026-11-22/README.md).

### 22 November 2026 — Overbuilding and first route audit

The user identified excess construction in the three replays. Exact action playback found that 24/109, 32/95 and 25/25 paid road units were outside observed assigned vehicle routes in the best, near-average and worst games. The worst paid all 25 units by second 44 without a matching service route. A previous offline witness on the same seed used seven units and delivered by second 17. In a frozen comparison on 16 fresh cities, quadrupled Wait odds reduced early stockouts from nine to zero but cut mean deliveries from 50.19 to 26.31. Both settings scored on two of eight hard openings. Keep the selected weights and focus the next isolated exercise on route completion with distractors and delayed opportunities. No training ran. [Audit, evidence and reproduction](../docs/training/city-road-spending-audit-2026-11-22/README.md).

### 22 November 2026 — Limited-stock route completion and delayed gates

The user authorized the focused route exercise. Implemented matching-pair arenas with two genuine road stubs, two to five paid route edges and zero or one spare unit. The delayed arena opens a physical gate at second 6, 9 or 12. A first launch failed before any update when NumPy integer coordinates reached the JSON bridge. The corrected `limited-route-ppo-02` run on `Maskable-PPO` completed 81,920 decisions in 294.12 seconds, saving before and after delayed layouts joined. The parent, first and final checkpoints scored 6/32, 9/32 and 12/32 on short routes. Long-route success reached 1/32. All delayed groups scored zero, but the final retained stock at opening in 26/32 versus zero for the parent. Fresh city means were 72.13, 66.56 and 39.69. Retain the overnight city reference and both practice saves. Verified 36 scoring fixtures, 12 gate transitions, 99 native self-test suites, 14 Python tests, and unchanged checkpoint hashes. The original reserved suite remained unused. [Measurements and reproduction](../docs/training/limited-route-ppo-2026-11-22/README.md).

### 22 November 2026 — Verified limited-stock opening repair

The user requested work through a fix. On `Maskable-PPO`, added one-, two- and three-gap curriculum variants and a frozen-base PPO opening correction. Two bounded approaches were redirected after preserving two checkpoints each. The successful progress-conditioned run completed 61,440 decisions. It used existing-road reachability, geometric separation and legal-action evidence to address the first matching route. Potential shaping was a fixed return offset at each practice start. An initialization comparison established that much of the performance gain came from the observable geometry and initial action preferences. The PPO candidate completed 20/24 delayed routes in development. Failure replays motivated a stronger soft alignment preference and extra Wait weight in the absence of a progressing legal edge. Fresh confirmation scored 32/32 on short, long, full delayed and delayed two-gap layouts. On 32 separate native Los Angeles cities the calibrated mean was 99.97 versus 81.63 for the overnight parent, with paired mean gain 18.34 and interval 5.81–32.13. Paid road units outside observed assigned routes remained about 37 per full city. The selected artifact matches the evaluated weights and keeps the 61,440 counter. The original benchmark seeds remained held back. Native tests, Python tests, fixture witnesses and multi-parcel probability parity passed. [Repair, evidence and reproduction](../docs/training/city-route-repair-2026-11-22/README.md).

### 22 November 2026 — One-hour whole-city pilot launch preparation

The user requested the command for the proposed one-hour pilot. Prepared a resumable 32-worker native-score launcher from the selected route repair. A zero-initialized learned correction applies outside the verified opening states, and the earlier city critic supplies the initial value weights. Initial probabilities and all frozen actor tensors matched the repaired source. Two-worker smoke runs verified policy updates, saves, Adam and seed-cursor restoration, and complete paired city reviews on disposable seeds. The pilot review uses 24 fresh cities and measures score, zero-score frequency and paid units outside observed trip routes. The one-hour run has yet to start. [Command and checks](../docs/training/city-growth-pilot-launch-2026-11-22/README.md).

### 22 November 2026 — One-hour growing-city PPO pilot outcome

The user's run on `Maskable-PPO` added 798,720 decisions and 1,707 episodes in 3,617 seconds. On 24 fresh paired cities, repaired-start, halfway and final means were 84.04, 76.46 and 73.88 deliveries. Scoring games were 20, 21 and 22. Paid units outside observed trip routes averaged 35.58, 33.25 and 38.67, with corresponding shares of 43.2%, 43.3% and 49.3%. The paired score and road-unit intervals included zero. Both saved checkpoint hashes matched, and frozen actor tensors exactly matched the repaired source. Retain the repaired checkpoint and both local pilot saves. [Paired evidence and limits](../docs/training/city-growth-pilot-results-2026-11-22/README.md).

### 22 November 2026 — Serving a new destination midgame

The user approved a controlled service exercise. Added an established working network, a second matching pair, one or two missing paid edges, and a native delayed approach. The first build failed a double-to-int counter conversion and made no updates. The corrected `Maskable-PPO` run passed 16 native scoring witnesses and added 65,536 decisions. An eight-city frozen timing control moved delayed success from 0/8 to 8/8 by waiting until the visible blocker cleared. A 16,384-decision follow-up optimized a soft visible-blocker Wait correction. On 24 immediate and 24 delayed review seeds, the repaired baseline and both basic saves served all immediate targets and 1/24, 1/24 and 0/24 delayed targets. The timing initialization and trained checkpoint served all 24 delayed cases with unchanged existing-route deliveries. PPO barely changed the seeded Wait behavior. Full-city metrics for both timing checkpoints matched the parent exactly across 20 fresh games. The ordinary final save scored higher in mean but on fewer full cities and missed the delayed service gate. Preserve all saves and retain the repaired full-city reference. [Fixture, run and matched evaluation evidence](../docs/training/city-midgame-service-2026-11-22/README.md).

### 23 November 2026 — Growing-city new-destination readiness and detached launch

The user authorized qualification and launch of a long run on `Maskable-PPO`, with follow-up after they report completion. On `6bd7f71` plus local work, a frozen 24-city native audit found 69/101 new destinations served. Twenty-four of the 32 unserved arrivals had no road stock, and only three unserved targets had a seen affordable path estimated at one to three road units. The estimate uses visible matching homes, existing links and the native legal mask. It can miss future affordable opportunities and does not prove that a set of individually legal roads can be built together.

Tested a soft later-city feature head with Maskable PPO and delivery-only reward. The first broad attempt failed a CUDA Boolean reduction before updates. Corrected the accumulator and started a new output directory. The broad and narrower stock-reserve pilots added 36,864 and 24,576 decisions. The broad midpoint conserved stock but lost 19.19 mean deliveries on the 16-city independent comparison. The narrower final scored +7.92 and −8.38 versus the repaired reference on its 24-city development and 16-city confirmation suites. Across those suites it had 54 versus 92 empty-stock arrivals and served 115 versus 118 new destinations. This supports testing stock timing over a longer run. Consistent scoring, service and efficiency gains remain open. Verified 99 native suites, 14 Python tests, exact actor parity in 13 protected opening states, distinct evaluation seeds and checkpoint identities.

Launched `city-service-long-01` at 03:12:21 Beirut time for eight active training hours, with 32 workers and saves about every 15 minutes. The narrow final restored at 86,016 decisions with 21 Adam state entries. Verified the first PPO update at 90,112 decisions and left the detached session running. The repaired baseline and exact warm start are both included in the post-training comparison. [Diagnosis, paired data and launch record](../docs/training/city-service-readiness-2026-11-23/README.md).

### 23 November 2026 — Completed eight-hour growing-city service PPO

The user requested an assessment after the authorized detached run. `city-service-long-01` on `Maskable-PPO` added 5,230,592 decisions across 10,884 training episodes in 28,809.83 active seconds. Its 32 saves and frozen model hashes verified. The automatic review covered 144 sampled games across 24 matched Los Angeles seeds. Repaired, warm-start, two-hour, four-hour, six-hour and final means were 89.17, 98.54, 89.50, 101.00, 84.46 and 77.13 deliveries. The four-hour checkpoint scored in 24/24 and averaged 2.46 additional deliveries versus the warm start, with paired interval −23.75 to +29.13. It served 88 versus 89 new destinations and matched the warm start’s road units outside observed routes. The final brought empty-stock arrivals down to 13/96 versus 31/108 at warm start while new destinations served fell from 89 to 74. Its builds per simulated minute rose from 13.58 to 14.06. Timing and placement effects remain unverified. Preserve the four-hour candidate and both references. An independent comparison is still open. No follow-up training ran. [Full review and archived measurements](../docs/training/city-service-long-results-2026-11-23/README.md).

### 23 November 2026 — Follow-up on the late full-city service decline

The user asked why the eight-hour policy regressed. From its archived 24 matched games per checkpoint, 429 of the 514 fewer deliveries versus the warm start went to destinations arriving after initial score. Median game length fell from 476.58 to 454.25 seconds and the final saw 12 fewer destinations. Unserved destinations that arrived with positive stock rose from 8/77 to 17/83. For positive-stock arrivals with at least 90 seconds of follow-up, unserved counts were 7/71 at warm start, 9/81 at four hours and 14/74 at the end. Positive stock is not an affordability witness. The paired review did not record route feasibility or action sequences, so action timing versus placement remains open. No new games or updates ran. [Analysis and counts](../docs/training/city-service-long-results-2026-11-23/SERVICE_FAILURE_ANALYSIS.md).

### 23 November 2026 — Frozen checks of retained construction and a real missed join

The user asked what the policy can verifiably do and which specific decision fails. On `Maskable-PPO`, the repaired reference, warm start, four-hour and eight-hour saves each scored in the same 63/64 fresh single-pair short, long and delayed opening fixtures. All four served 24/24 immediately open second destinations. Delayed second-destination success was 1/24, 22/24, 24/24 and 23/24 on the existing controlled suite. These are frozen native deliveries and include the engineered observation and action preferences.

Replayed the 14 eligible final-checkpoint misses from the full-city suite. On seed `99387707` at second 277, the model spent one of four road units on a different edge. Replaying the exact prefix and substituting one legal edge of the same cost delivered to the originally unserved target at second 295. Three tested edges succeeded on that board. Each of the four snapshots assigned less than 0.1% total probability to those choices on the same state, establishing that the underlying decision blind spot predates the long run. This is a direct missed one-edge join in a full city. The probe did not establish the mechanism for the other cases or isolate the cause of the late aggregate regression. [Frozen evaluation and native witness](../docs/training/city-service-capability-2026-11-23/README.md).

### 23 November 2026 — City policy gap audit and independent check

The user asked for checks and a complete list of remaining fixes and skills. On `Maskable-PPO` verified that the final feature recognized the three legal matching joins on the previously replayed city board but collectively scored them at 0.068% probability. A visible sixteen-link chain proved the ten-hop reach cutoff, and constructed boards proved same-color target interference and an established flag across a bare shared driveway approach. A full-graph comparison made no change at the witnessed real-city decision. Bounded native branches found three-paid-unit routes serving two of 14 selected misses, including a route to the previously witnessed target 86 seconds before the one-edge opportunity.

In the frozen two-color demand fixture the final served the urgent shop in 5/12 and changed the first road in only one of six paired demand reversals. On six paired light and heavy junctions each city actor always chose the bypass. Native controls favored the feeder in light traffic and the bypass in heavy traffic. An additional 24 independent city pairs yielded mean scores 61.88, 73.75, 75.29 and 64.71 for repaired, warm start, four hours and eight hours. The four-hour paired gain against warm start was 1.54 with interval −22.25 to +25.58. No checkpoint was promoted. The native checks passed 99 suites and 1,116 differential actions. The full Python check passed 64/66 with two legacy fixture errors caused by advancing the native world outside the training reward ledger. The current city actor remains road or Wait with scripted weekly picks. The proposed next gate is service-feature correctness plus city-like affordable route choices. No training ran. [Archive and ordered work](../docs/training/city-policy-gap-audit-2026-11-23/README.md).

### 23 November 2026 — Destination-specific service repair and bounded PPO pilot

The user approved the network fixes and pilot and requested review during execution. Added a separately loadable policy using complete reciprocal road components, real driveway attachments and destination-specific progress and urgency. Added three native practice variants with distractor roads, detours and delayed approaches. Verified 96 scoring witnesses, 99 native suites, 1,116 legality actions and 69 Python tests. The narrow warm start seeded a 32,768-decision, 510-episode pilot with 16 workers. The changed trainable parameter set starts fresh Adam state. The archive records both the geometry-only transfer and soft initialization so PPO gains can be measured separately. Five-way frozen reviews and final opening parity checks are recorded with the pilot results. [Pilot record](../docs/training/city-network-service-pilot-2026-11-23/README.md).

The completed five-way review found identical one-edge (12/16) and delayed (8/16) success, with longer routes 1/16 for parent/features-only and 2/16 for initialization and both PPO saves. The final retained exact opening probabilities on 275 states. On 16 paired cities the final averaged 81.81 versus 59.25 parent and 68.13 initialization, with wide uncertainty. All scored in 13/16 cities. The candidate remains experimental. [Measurements](../docs/training/city-network-service-pilot-2026-11-23/README.md).

### 23 November 2026 — Audit of spatial learning before long-run preparation

The user authorized bounded experiments and required a command only once ready. Audited the prior network pilot and found the learned spatial road actor frozen, with only service scalars and the critic trainable. Prepared a separate CityLearningPolicy with identical copied weights and newly enabled spatial growth modules. Verified log-probability parity and finite gradients, and kept a separate optimizer because trainable parameters changed. The first three-minute city pilot at learning rate 0.00005 fell from 85.13 to 55.13 on 16 paired cities. The second at 0.000005 averaged 77.56 halfway and 78.06 final, with scoring cities 15 and 13 versus 15 at start. All original weights remain available. A third bounded learning-rate probe is underway. No long session launched. [Readiness audit](../docs/training/city-learning-readiness-2026-11-23/README.md).

The third pilot at 0.000001 yielded 83.50 midpoint and 70.19 final versus 85.13 at start on development. Its midpoint passed fresh retention on 24 cities with 111.29 versus 110.46 and 23/24 scoring cities each, paired gain interval −5.63 to +8.79. Prepared the user-run guarded launcher for up to eight active hours, evaluating every half hour and stopping if neither save retains the segment-start scoring count and at least 95% of its mean deliveries. The threshold is an engineering choice. The long job has not launched. [Command and evidence](../docs/training/city-learning-readiness-2026-11-23/README.md).

### 23 November 2026 — Early live score reporting during guarded training

The user asked why the first completed games scored low. The active first segment restored 133,120 decisions and 22 optimizer entries. The first four completed episodes scored zero and ended at about 141–153 simulated seconds. Subsequent initial completions included scores 14, 38 and 41 at longer durations. At the snapshot, 87 completed episodes averaged 81.21 deliveries. The console mean uses the learner's recent completed episode buffer. Parallel cities that survive longer report later, so the first completions disproportionately include early failures. This explains the early reporting bias and leaves opening failures as genuine policy errors. The fresh paired segment review remains the performance comparison.

### 23 November 2026 — Guarded continuation stopped after two segments

The user asked whether training finished. The launcher stopped automatically after about one active hour and 1,117 episodes. Segment two failed scoring-city retention, with 21/24 at midpoint and 20/24 final versus 22/24 for its reference. Means were 86.08 and 82.88 versus 86.21. It retained the first segment final at 413,696 decisions. No trainer is active. [Status evidence](../docs/training/city-learning-long-status-2026-11-23/README.md).

### 23 November 2026 — Opening regression replay and protected PPO pilot

The user authorized investigating the stopped guarded run and making bounded repairs toward higher scores. Replayed all three newly scoreless cities from segment two with identical scenario and action seeds. All first action divergences preceded the first delivery. This identifies an opening-retention gap but does not isolate every cause of later score changes. Added a separately loadable CityEstablishedFeatures policy carrying a frozen copy of the retained 413,696-decision feature extractor. It uses that reference until the visible reciprocal, matching-color, attached-road graph indicates service in a city with more than two parcels; subsequent spatial growth weights remain PPO-trainable. No new planner, reward or simulator change was introduced. This engineering choice also freezes the reference's unsuccessful openings, an explicit limit.

Prepared an exact-weight transfer with the same 22 optimizer state entries and ran city-established-pilot-01 for 12,288 added decisions, 19 completed episodes and 101.71 active seconds at learning rate 0.000001. Three targeted final-checkpoint replays scored 14, 4 and 156 versus retained 14, 4 and 158. Opening probabilities matched exactly in 175 checked states and reference tensors stayed identical while spatial road weights changed. Four focused tests passed, including mixed-batch retention and gradient flow. A paired 16-city review is pending. This work occurred in the existing /home/mohammadjaffal/mini_motorways Maskable-PPO checkout; the supplied Desktop instruction naming mohammad differs from that checkout's AGENTS.md. No branch was switched and Desktop main was untouched. No long run launched. [Evidence and limitations](../docs/training/city-regression-repair-2026-11-23/README.md).

The completed paired 16-city review yielded means 99.00 older repaired baseline, 90.19 exact start, 92.81 midpoint and 96.56 final, with 15/16 scoring in all conditions. Final served 59 new targets versus 53 at start and averaged 36.69 road units outside observed routes versus 40.06. Final-start paired gain was 6.375 with bootstrap interval -7.81 to +27.69, driven substantially by one +147 game and offset by a -45 game. The suite has no scenario overlap with the failed segment, but reused its generator seed and is development evidence. Exact Adam transfer and protected/spatial weight checks passed for both saves. Retain the final as a repair candidate, without claiming general improvement or long-run readiness. The next gate is bounded stability and a larger predeclared paired review after resolving the checkout/branch discrepancy. All jobs finished; no long run launched.

### 23 November 2026 — Five-stage city improvement authorized

The user approved all five stages (stability, useful connections, waiting,
demand/congestion and mixed full-city PPO), and explicitly chose the existing
Maskable-PPO checkout after the supplied mohammad instruction conflict was
identified. No training was active at inspection. Started a bounded three-minute
stability continuation and prepared native curriculum integration. The previous
traffic fixtures existed only in archived/local host copies; their provenance
and opt-in integration will be archived. All outcomes remain pending. See
[predeclared plan](../docs/training/five-stage-city-learning-2026-11-23/PLAN.md).

Five-stage intermediate measurements: the stability continuation added 22,528 decisions and 41 completed episodes. On 32 paired cities the exact start/midpoint/final means were 81.59/80.28/75.22, with 27 scoring cities each; the midpoint passes retention and final fails. The older repaired reference averaged 74.91 and scored in 28/32. The 32,768-decision connection pilot completed 508 episodes but matched the original 6/8 one-edge and 2/8 longer-route success. Native controls pass all 12 tested useful routes. Waiting-01 completed 32,768 decisions and 512 episodes. All 99 native suites, 1,116 legality actions and 364 old/new city transition comparisons passed. The first temperature unit test selected indistinguishable empty-road cells and could not demonstrate a change; selecting distinct road geometries corrected the test, and all five focused tests pass.

Exploration diagnosis: the retained city actor assigned a useful light-traffic feeder roughly 5e-14 probability and selected the bypass on all eight light boards. Added a checkpoint-specific generic road-temperature experiment that preserves legal masking, Wait/build mass and opening behavior while softening only the frozen established-road prior; learned corrections remain unscaled. A temperature-20 probe puts the feeder at about 7% of conditional build choices on the diagnostic board. This is an engineered initialization, not a learned result. The old coordinator was stopped after starting waiting-01; that trainer completed unchanged. Revised bounded experiments increase connection/wait learning rate and give traffic a separately measured exploratory starting checkpoint and a 65,536-decision budget. See the evolving [plan and adaptive decisions](../docs/training/five-stage-city-learning-2026-11-23/PLAN.md).

Further five-stage checks: connections-02 (32,768 decisions, 508 episodes,
learning rate 3e-4) improves one-edge held-out success to 7/8 but leaves longer
routes at 2/8. The first waiting run is unchanged at 3/8 delayed successes and
still spends both spare units on the quiet controls. Added optional forced-Wait
compression with exact native state/reward parity on all eight lessons; only
steps with no legal build are combined. Finite practice windows terminate in
this mode, while ordinary-city time limits retain truncation. This deliberately
changes credit assignment and makes raw decision counts incomparable across
modes. The already-started waiting-02 pilot completes unchanged. Revised the
remaining bounded budgets to 4,096 connection, 4,096 waiting, 8,192 traffic and
8,192 mixed meaningful decisions. Archived controls distinguish verified
mechanics from the hypothesis that this improves learning efficiency.

The first five-stage sequence completed nine bounded training runs. Traffic-01
processed 2,014 episodes in 8,192 meaningful decisions; mixed-01 added 8,192
and 119 episodes. On 32 matched cities their mean scores were 18.56 and 16.22,
versus original85.03 and pre-exploration73.63; all four scored in31/32.
Reject the broad-exploration versions. Fresh practice also exposes lost
construction ability. The original protected checkpoint remains selected.

A follow-up visible-feature probe found no service signal for a feeder that
adds homes to an already-served destination. Added separately loadable visible
supply/cycle/traffic/demand relation features with zero initial weights, keeping
service priors unscaled. The older actor/reference remain frozen for this
narrow diagnostic; ten relation coefficients and the critic learn from native
scores, with separately scaled learning rates and fresh optimizer state because
the trainable set changes. Temperature-one and opening parity, native supply
features, and the optimizer rate ratio passed checks. The eight-feature
prototype is preserved untrained; the ten-feature candidate is under bounded
traffic and mixed-city testing. All earlier candidates and checkpoints remain
available. See the [adaptive record](../docs/training/five-stage-city-learning-2026-11-23/PLAN.md).


### Five-stage completion, calibration attribution and independent retention — 2026-11-23

Engineering choices: after relations-01 (4,096 decisions,1,770 episodes) and
relations-mixed-01 (4,096,57), warm sampling still scored poorly. Saved identical
factor20 conditional-road calibrations of the zero-weight initialization and
trained candidate. Wait/build mass, opening distribution and road argmax remain
unchanged; this is inference calibration, not another PPO run. A retained-prior
variant with scaled learned weights and reset Adam state was also evaluated and
not preferred. No planner or imitation was added. All eleven bounded runs total
169,984 added decisions across branches; forced-Wait and ordinary counts have
different meanings. All parent paths, run configs, checkpoints and failed trials
are preserved. The original protected reference hash remains unchanged.

Measured development city means (32 paired cases): original85.03,
calibration-only97.56, calibrated-trained93.53; scoring31/31/30. Final independent
32-city means:63.53/82.13/67.44, all26 scoring. Scenario sets have no shared city
seeds. Calibration-minus-original independent paired mean18.59, bootstrap95%
[3.13,35.06]; trained-minus-original3.91,[-15.94,23.59]. The original remains
conservative rollback; calibration-only is the best measured experimental city
candidate. Do not promote trained demand learning as proven city improvement.
Its lost development scoring city still fails the strict retention gate.

On sixteen fresh practice cases, original/calibrated-init/calibrated-trained
longer-route success is5/16,16/16,16/16; delayed service10/16,15/16,15/16.
Urgent target service across both variants is16/32,17/32,32/32. Thus construction
gains precede PPO, while demand gains exceed identical calibration alone.
Light-traffic scores11.75/11.75/13.375 improve partially (feeder control14.875),
heavy scores all31.0. Quiet boards still spend both spare road units; Wait
controls preserve them with comparable native score. The short horizon does not
make conservation valuable. Proposed next work: later service consequences for
stock spending, then fresh city retention. This is an open gate, not a new reward
penalty or authorized long-run launch.

Checks: final seven focused Python tests pass;99 native suites and1,116 legality
actions pass;364 ordinary host transitions match; forced-Wait and parameter
change audits pass. Independent evaluation completes without new training.
All jobs have ended; Desktop/main remains clean. Detailed run-by-run results,
measurements, source snapshots and local-only weight/binary hashes are archived
in [five-stage report](../docs/training/five-stage-city-learning-2026-11-23/README.md).

### Road-stock reservation experiment opened — 2026-11-23

User requested learning to save roads for later connections and full-city checks.
On Maskable-PPO, no training was active. Existing work remains intact. Planned
native future-demand practice and a zero-initialized Wait-only learner from the
best calibrated city candidate; keep road ranking/opening frozen to isolate
conservation. Native deliveries remain the only reward. Bounded budgets,
held-out seeds and retention gates: [plan](../docs/training/road-reserve-learning-2026-11-23/PLAN.md).

Road-reserve preflight: new host passes99 suites and ordinary-state parity;
zero-initialization probabilities match the calibrated parent exactly on the
opening and all nine lessons. Eight focused Python tests pass. Native saving
controls serve8/8 later targets, wasting controls0/8, parent2/8. No change to
native reward. Started the predeclared8,192-decision Wait-only PPO pilot with
fresh Adam state (new parameter set), actor.03/critic.0003, exact inherited road
rankings. The parent and initial checkpoint remain preserved.

### Road-reserve pilot selected for independent tests — 2026-11-24

Completed8,192 decisions/454 episodes in223.7 seconds. Development later-service
success2/8→3/8 midpoint→6/8 final, arrival stock1.125→2.5→3.125. Final longer
routes8/8 retained, delayed6/8→8/8, quiet spare stock0→0.875. Saved all checkpoints.
Audit verifies only six Wait coefficients plus critic changed; conditional road
ranking and protected opening remain identical. Final selected before inspecting
independent city outcomes. Fresh16-case/nine-lesson practice and paired32-city
checks are running; no further training is active. Results pending.

Road-reserve transfer diagnosis: two city replays reveal that the new unavailable
progress input wrongly generalizes blocked-gate waiting to ordinary incomplete
networks (>99% Wait with211/274 legal builds and no visible approach blocker).
Preserve candidate01. Added a separately loadable feature correction restricting
those two inputs to visible blocked approaches; identical PPO weights, no new
training. Nine initial lesson distributions and opening remain unchanged.
The first city suite is now diagnostic; fresh32-city RNG940128 confirmation and
repaired16-case practice checks are running. See the archived diagnosis and plan.

Fresh16-case practice results: repaired later-target success13/16 versus parent
2/16; stock at appearance3.0 versus1.0625. Saving control16/16, wasting0/16,
permanent Wait0/16. Longer-route16/16 retained; delayed15/16→16/16; quiet stock
0→0.875. Priority service remains17/32 across both variants; light/heavy traffic
means12.0625/32.25→11.8125/31.5625, a small measured regression. Repair preserves
all construction and reservation lesson outcomes of the unrepaired PPO while
removing the diagnosed unavailable-progress Wait error. Nine final tests pass;
native counterfactual replay restores parent Wait probability .74367 from
unrepaired .999932 at a city state with20 stock and274 legal builds. Full-city
confirmation remains pending; no automatic promotion.

First full-city comparison completed32 matched games: calibrated parent98.03125,
unrepaired PPO37.4375; both30/32 scoring. Paired mean change−60.59375 with95%
bootstrap interval[−81.25,−40.16]. Older protected reference105.375. Reject the
unrepaired checkpoint despite zero target-arrival stockouts: it served62 new
targets versus115 and spent26.53 versus83.28 units; shorter survival also changes
target exposure. The repaired fresh-city confirmation remains pending.
Extended forced-Wait parity to exact-stock controls:64→20 and62→15 wrapper steps
with identical native state/reward; reset isolation passes. No additional PPO.


### Road-reserve completion and rejection — 2026-11-24

Final separately fixed 32-city RNG940128 confirmation: calibrated parent81.875,
repaired PPO54.96875, both23/32 scoring. Paired mean difference−26.90625 with
95% bootstrap interval[−43.5,−11.8125]. No shared city seeds between first and
confirmation suites. Reject both new candidates for city continuation. Preserve
all checkpoints; keep previous calibrated and protected references. Lesson
success13/16 versus2/16 demonstrates learned conservation, not general city
improvement. Nine final tests,99 native suites,364 ordinary-state parity checks,
reset isolation, forced-Wait exact-stock parity and parameter/distribution audits
pass. Main checkout remains untouched. No jobs remain active; no overnight run.

Measured limitation: the trained Wait correction also raises Wait on an available
route probe from14.54% to42.55%. Its causal contribution to score loss is not
isolated. Proposed next work is mixed-city conservation versus prompt expansion
with wider stock/route states and real delivery deadlines, not more of this
narrow lesson alone. Full small measurements, source snapshots, failed candidate
and repaired candidate hashes, and all decisions are preserved in the
[final report](../docs/training/road-reserve-learning-2026-11-23/README.md).

### City strategy and conditional long-launch authorization — 2026-11-24

User authorizes autonomous bounded work and a long launch when repeated evidence
supports substantial city-score gains and genuine policy learning; no guarantee
is possible. No jobs active at inspection. Starting from the calibrated parent,
prepare zero-init neural Wait/road residuals plus explicit visible critic context,
city-only delivery rewards and longer credit assignment. Preserve opening and
all prior candidates. Predeclared budgets, seeds and launch gates are in
[city strategy plan](../docs/training/city-strategy-launch-2026-11-24/PLAN.md).

City strategy preflight: exact action probabilities and initial values match the
calibrated parent on all nine native lessons; opening probabilities also match.
Ten focused Python tests pass. New residuals and critic are the only trainable
parameters. Native city-only pilot started at65,536 decisions,512-step rollouts,
GAE1/gamma1,16 workers,batch128. Parent's hidden residual initialization was not
explicitly seeded; its exact local start checkpoint/hash is required for an
identical initialization. Native scenario/action evaluation seeds are fixed.
Added optional horizon plumbing, with exact initial observations and30 native
transitions verified across ordinary600s and1200s wrappers; the visible input
horizon remains600s. Current running pilot retains600s behavior unchanged.

City strategy pilot01 completes65,536 decisions/168 episodes. Midpoint matches
parent mean69.47 versus69.19 on32 development cities (25/32 scoring each), not
readiness. Native input audit finds532/541 roads share the same trainable relation
vector in one probe, limiting within-group learning despite different frozen
prior scores. Prepared a separately loadable wide spatial CNN residual with
exact zero-init actor/value parity, explicit seed11424, no planner/teacher.
A second65,536-decision city pilot on142M seeds tests that representation.
Final01 review continues; all first-run artifacts remain intact.

City strategy final01 passes the development strong-gain gate:84.34 versus69.19,
26/32 scoring versus25/32; paired gain15.16 [1.28,30.34]. New-target service98
versus91, but stockouts65 versus33. Midpoint was flat, so final gain follows
additional native-score PPO rather than initialization. It is still selection
evidence. Frozen64-city independent confirmation RNG950242 and a32,768-decision
1200s continuation on143M seeds are authorized readiness work, not the long
launch. Wide spatial pilot remains separately measured.

City strategy interruption recovery: all active jobs stopped during the chat
interruption. Completed summary pilot01 and its reports are preserved. Wide
pilot01 had logged24,576 decisions/50 episodes but had not reached its32,768
midpoint save; those unsaved updates cannot be recovered. Longer-pilot01 had no
saved checkpoint; confirmation01 had partial printed results only. Preserve all
partial files. Restart in separate02 directories from exact saved starts, same
native seed ranges and confirmation suite, saving every8,192-decision rollout.
Jobs now use detached sessions. No long session has been launched.

Resource correction after restart: two16-worker trainers plus eight paired
review workers reached29GiB RAM and nearly all2GiB swap. Stop only the detached
wide-pilot02 process group with SIGINT before its first completed rollout save;
no newly trained checkpoint exists to recover. Keep its partial logs. Continue
the longer-game pilot and independent review; serialize subsequent trainers.
This is an engineering resource stop, not a measured learning failure.

Predeclared longer-game diagnostic:32 paired1200s cities RNG950244 for calibrated
parent, summary final01 and longer final02; native retention16 cases per lesson
at141M. Keep development950241 separate from independent confirmation950242.
The review plan records these cohorts before their outcomes are available.

Independent confirmation02 completes64 frozen paired cities: summary final01
88.140625 versus82.734375 (+6.53%),54/64 scoring each; paired delta5.40625,
95% bootstrap interval[-5.5,16.23477]. New targets served207 versus202; stockouts
105 versus58. This fails the predeclared strong-gain launch gate despite the
+21.9% development gain. No long launch. Continue the already-budgeted longer
and wide representation trials; do not reuse950242 as fresh confirmation for
an adaptively chosen later candidate.

Longer continuation02 development600s mean79.4375 versus69.1875 parent,25/32
scoring each; paired delta10.25 [−2.40625,23.125]. Below summary final01's84.34;
no repeated improvement established. Longer1200s diagnostic remains active.
Native exploration probes show near-deterministic inherited conditional roads:
quiet top probability0.9999973 (539 legal), reserve0.9998524 (579 legal), live
junctions>0.99965 (six legal). Join is exactly1 at float precision. Priority
probes remain two-way. These are initial lesson probes, not all city states;
saturation is a plausible exploration barrier, not yet an isolated causal claim.
Exact metrics saved in parent-exploration.json. No sampling change made yet.

Wide-pilot03 first8,192-decision checkpoint audit passes frozen inherited weights,
finite parameters, valid masks and four exact opening cases. Conditional road TV
on route probe is0.01215 and priority probes0.06548/0.05952, versus nearly no
route change from the summary residual. Spatial policy can therefore change
previously aliased rankings. This verifies learning capacity/parameter effect,
not beneficial strategy; matched score and native skill reviews remain required.

Opening failure diagnostic replays all ten zero-score independent reference cities
with the exact initial policy and action RNG; scores and build counts match.
The established gate means a visible matching connection with>2 buildings,
not a completed delivery (an earlier chat explanation was corrected promptly).
In eight failures activation starts only at140–142s; in two it never activates.
Thus these residuals cannot repair most early decisions in those trajectories.
This is a scope limitation, not evidence that the simulator or PPO optimizer is
broken. The independent suite is now also diagnostic data, not a fresh future
selection test. Exact per-city counts retained in opening-failures.json.

Paired longer1200s review02 completes32 cities: calibrated parent98.21875,
summary final01 112.1875, longer continuation02 86.28125; all24/32 scoring.
Summary gain13.96875 interval[-20.65859,60.37578]; continuation delta−11.9375
[-45.84375,17.53125] versus parent. New targets served97/101/83; stockouts40/69/59.
The additional1200s PPO continuation does not establish improvement and is not
selected for a long run. Preserve it as negative evidence. Wide pilot and native
retention checks continue; no further summary-only training is justified now.

Spatial city-only pilot03 completes65,536 decisions/150 episodes; native retention
join/route16/16,delay13/16,priority7/16 and swapped9/16 (16/32 combined, unchanged),
reservation0/16. No broad strategy mastery established. Introduce an opt-in
strategy-mixed native curriculum (four city/four reservation/six other lessons
per14 episodes) for one65,536-decision continuation,LR.001,seed144M. Rationale:
provide repeated native reward consequences for strategy choices that city-only
training has not learned, while retaining full-city experience. No teacher or
planner, no shaped road penalty; preserve all earlier checkpoints and defaults.

Completed skill retention02 (16 cases per nine lessons): summary and longer
retain join/route16/16 and delay13/16, priority8/16 in each orientation; reserve
falls2/16 parent→0/16 both. Quiet still spends2 roads despite Wait control doing
better. Junction success flags are not useful (no new targets even for controls);
use native scores: low12.375 unchanged, high31.25→31.5. Spatial final03 has
priority7/16+9/16, also16/32 total; reserve0/16. Larger road probability changes
therefore did not yet translate into these strategies. Mixed training means
combine short lessons and cities and must not be compared with city-only means.
Wide midpoint development75.625 vs69.1875,paired6.4375 [−8.34375,21.68828]; no
strong-gain pass. Source snapshot before mixed-stage addition preserved separately.

Spatial final03 development completes:68.625 versus69.1875 parent (−0.81%),
25/32 scoring each, no strong gain. Midpoint75.625 was higher. The broader
representation changes road choices but city-only updates did not yield reliable
score improvement. This final remains an experimental continuation source for
the already-started mixed curriculum, not a promoted best model or long-run start.

Curriculum sampling diagnosis: at24,576 mixed decisions,13 priority and14 swapped
completed episodes each contribute one decision,~0.11% of samples. Whole cities
contribute hundreds of decisions per episode. Episode-cycle weights therefore
failed to provide the intended strategy exposure after forced-Wait compression.
Adapt at saved32,768 midpoint: preserve/stop mixed trainer; allocate fixed workers
8 city/4 reserve/2 priority/2 swapped for remaining32,768 decisions,seed145M,
LR.001. Compatible PPO optimizer/weights continue; no reference actions/rewards.
This changes the sampling schedule only for the opt-in strategy-balanced stage.

Mixed midpoint32,768 decisions: development73.625 vs69.1875 parent,paired4.4375
[-10.71953,20.43828], vs spatial final+5[-12.12578,22.125]. Native priority remains
7/16+9/16 and reserve0/16. The episode-cycle sample imbalance did not resolve
strategy failures. Completed reviews preserved; old review scheduler stopped
while waiting for a midpoint that the revised continuation will replace.

Performance correction for balanced priority workers: after their only road is
spent and the mask has no road action, these fixed fixtures cannot gain stock,
spawn buildings or remove roads. Optional fast-priority-tail advances the exact
same native ticks in one existing `step` call until termination/horizon. Native
host/reward/physics are unchanged.32 paired cases (two orientations,16 seeds,
0–3 preliminary Waits, both legal choices) have exact final raw simulator state,
reward/flags/info/counters and next-reset observations. Benchmark tail time27.17s
versus7.42s (~3.66x). Terminal motion/history differs, intentionally: all such
finite lessons are terminated=True and never bootstrap that observation. No
nonterminal learning-visible observation is skipped. Flag defaults off and is
restricted to priority fixtures with zero stock/no legal road; runtime checks
reject changed end-state contracts. At first saved8,192 balanced decisions,
continue remaining24,576 from that checkpoint with this option and146M seeds.

Balanced first rollout saved8,192 decisions/2,087 episodes with finite PPO loss.
Transition SIGINT reached shutdown but the vector worker close hung for>60s;
launcher refused to overlap trainers and exited with a diagnostic error. Verified
saved checkpoint hash, then SIGTERM only owned process group173520 and confirmed
parent exit before launching balanced-fast01. Saved weights/optimizer preserved;
unsaved work after the rollout is not claimed. This is process cleanup, not a
learning failure. New bounded continuation24,576 decisions uses146M seeds.

Future mixed-run logs now also print separate recent per-task native score means
(up to100 completed episodes per task), so thousands of short practice games do
not hide the city mean in one aggregate. This is logging only; the already-running
fast continuation retains its loaded earlier logger. Score evidence still comes
from frozen reviews, not training means. The prepared long runner can explicitly
select city or strategy-balanced and opt into the validated priority-tail speedup;
no long runner has been executed or declared ready.

Prepared unattended runner now starts each training/review child in its own
process group, bounds each child job to one hour, and cleans up that owned group
on failure/interrupt/timeout (including SIGTERM-ignoring orphan workers). Root
SIGTERM records an interrupted status. Fourteen focused tests passed before the
final orphan escalation; three process/regression tests then pass with explicit
SIGTERM-ignoring orphan,timeout,and normal completion cases. This addresses the
observed vector-close hang; it never targets unrelated training processes.
Native full-run integration remains required before any long launch.

Balanced16,384-decision checkpoint (fast midpoint after first ordinary balanced
rollout): development70.3125 vs69.1875 parent, retention passes but no strong
gain. Native priority10/16+8/16 (18/32), reserve1/16; join/route16/16,delay13/16.
Evaluation-only control labels identify the urgent road and measure frozen
conditional probabilities: parent51.51%,wide51.94%,mixed51.77%,first balanced
53.01%,balanced16k56.73%. These reused diagnostic states show directional
strategy learning beyond sampled-score noise, not yet city-score transfer.
Controls/labels are never supplied to training. Exact per-case probabilities
retained in priority-probabilities.json. Continue the predeclared remaining budget.

Runner smoke exposed stale reporting history: loaded SB3 ep_info_buffer can carry
short practice scores into the next city run's early recent mean. Clear only
loaded episode/success reporting buffers after load; retain model weights,Adam,
num_timesteps and update count. Frozen evaluation scores are unaffected. Earlier
training-log means may contain inherited episode history until100 new episodes;
they were never used as readiness evidence. Also publish completed segment/status
and review phase before starting paired reviews, rather than leaving the status
file at the previous checkpoint throughout review. These are reporting fixes.

Balanced32k final: city development74.65625 vs69.1875,25/32 scoring each,paired
+5.46875 [−6.15625,17.21953]; no strong city gain yet. Priority improves26/32,
conditional urgent-choice probability78.33%,from16/32 and51.51% reference.
Reservation remains0/16; join/route16/16,delay13/16 preserved. This satisfies the
predeclared bounded-extension condition, not the long-launch gate.

Next32,768 balanced decisions on148M,LR.001,retain weights/Adam. Reservation uses
fixed6s native warmup before the rated episode to shorten the initial delay and
increase positive-reward opportunities; no hidden spawn time or teacher action
is consumed and warmup deliveries are excluded.16 paired train/validation resets
match manually waited native states,actor inputs,masks and next-step rewards;
start reward/time reset to0 and the future pair is not yet visible. Full original
zero-warmup validation remains unchanged. Use one bounded runtime-snapshot segment
for this extension, not an eight-hour launch. Prior512-decision/two-city smoke
passed; its checkpoint and tiny review are not score-selection evidence.

Extension midpoint16k: development82.75 vs69.1875 (+19.60%),26/32 scoring vs25,
paired+13.5625 [−6.84375,34.15703]. It narrowly misses20% and the interval crosses
zero; do not lower the launch gate. Priority30/32,conditional urgent probability
87.04%; connection skills retained. Original-delay reservation remains0/16,
despite higher training rewards in the easier starting states. Priority learning
is established on these diagnostics; reservation transfer is not. Finish the
remaining predeclared extension budget and review final before any selection.

Evaluation efficiency fix: skip neural inference only for a singleton legal mask,
while still sampling its exact one-hot distribution to consume the same action
RNG draw and stepping/encoding every native observation. No training behavior or
mask restriction changes. Six paired complete reviews (priority,swap,reserve,
route,and two cities) have exactly identical result dictionaries; frozen weight
hash unchanged. Example timings: priority8.64→1.25s,city36.44→23.66s. This is a
stateless forced-action shortcut, not a planner. New evaluation configs record
forced_action_inference_skipped=True; retained earlier reviews remain valid by
parity. Active training's frozen runtime is unaffected by this source update.

Extension final completed32,768 decisions/8,433 episodes in1,091.0s (mostly short
practice episodes). Development80.0 vs69.1875,paired+10.8125 [−5.34375,27.625],
27/32 scoring vs25; priority28/32,conditional urgent probability87.02%,reserve0/16.
No long readiness. Midpoint82.75/priority30/32 is the next experimental parent;
final and all earlier checkpoints remain intact. Bounded runner's two-city guard
is workflow-only and does not promote a project-wide winner.

Next controlled implementation test groups PPO minibatches by fixed task, so
standard advantage normalization does not mix city and small-lesson scales.
This is a hypothesis about relative learning emphasis, not a proven root cause.
Native rewards/critic targets/architecture/Adam progress remain unchanged.
Per-task pre-update advantage/return statistics are now recorded. Tests verify
all16 synthetic buffer rows occur once per epoch, task purity, and exact alignment
of observations,actions,masks,values,likelihoods,advantages and returns across
multiple epochs;16 focused tests pass. Exact weights/optimizer/counters and nine
native distributions match when loading the new sampler. Budget32,768 decisions,
seed150M,LR.001,otherwise same balanced/warmup protocol; midpoint/final reviewed
on existing selection cohorts before any independent test or long launch.

### 2026-11-24 — task batching rejected; reservation baseline experiment

Measured task-batch final: city71.53125 vs69.1875 on32 development seeds,
paired+2.34375 [−11.56328,16.31328],25 scoring each. Priority27/32,
original-delay reserve0/16, join/route16/16,delay13/16. No long launch.
The first two reservation rollouts had return std2.82/2.74 but advantage
std20.47/17.08. This diagnoses increased scalar variance from the learned
baseline, not proof of a sole causal root cause. Task batching alone failed.

Engineering hypothesis: use zero state-value baseline for reservation actor
advantages only (return-to-go with GAE1), while preserving native reward,
critic targets, masks, PPO clipping, optimizer and all other task advantages.
Incomplete rollout tails retain normal value bootstrap. Task-local minibatch
centering/scaling remains active. This is PPO, with no teacher or planner.
New flag defaults off. Tests check exact targets/other-task advantages across
terminal boundaries and bootstrapped tails. Eight focused unittest tests pass;
pytest is unavailable (recorded, no dependency installed).

Next bounded budget32,768 decisions,seed152M,LR.001,balanced16workers,warmup6,
parent extension midpoint. Same midpoint/final development and original-delay
skill reviews; no long readiness assumed. Add native new_deliveries,
future_stock,future_targets,urgent_deliveries to episode records (null for cities).
Higher total lesson score is not by itself proof of servicing future targets.
Expose explicit evaluation split/warmup parameters; defaults remain validation/0.

### Reservation transfer diagnostic (24 November)

Frozen extension midpoint,16 matched scenario/action seeds152010000+: train
positions with6s warmup9/16 future-target successes; train positions original
start5/16; validation positions with6s warmup7/16; validation original start3/16.
Reference evaluator route succeeds16/16 in each cell. Initial Wait probability
averages81.51%,70.58%,74.62%,61.15%,respectively. These small diagnostic cohorts
suggest both waiting duration and position transfer matter; they do not isolate
all causal factors or replace independent city testing. The earlier0/16 reserve
result uses a different reused validation cohort141M and remains valid.
Warmup's higher training reward does include genuine future deliveries, but
neither original nor warmup task is mastered. Exact per-game records retained.
All17 city-focused unittest tests pass after the optional return-advantage and
reporting changes; weights/Adam/counters/nine actor distributions are unchanged
on load. Pytest is absent; no package installation was needed.

Independent check: freeze extension midpoint before reviewing64 new600s cities,
RNG950243, against calibrated parent. Serialize confirmation ahead of new pilot
reviews; waiting review controller216557 was stopped before any child launched
and replaced by controller218688. Trainer216556 continues unchanged. This is
not a long-session launch. New reporting test verifies native future outcomes
are preserved and city outcomes are null rather than mislabelled;18 tests pass.

### 2026-11-24 — practice-only delay option (engineering choice, not promotion)

Reservation warmup shifts initial time and traffic, while original-state waiting
is still weak. Prepare an optional1..16s future-pair delay for reservation practice
only, default null preserving original random8..16s. Unlike six-second warmup,
this retains the original starting state and movement history. Always consume the
original RNG delay draw to preserve subsequent layout RNG. Actor receives no
future-event timing. Native delivery rewards and every ordinary city rule remain
unchanged. New resetReserveDelay command rejects use outside the named practice
fixture; old hosts reject it rather than silently ignoring the option. Explicit
delay and warmup cannot be combined. Old native files/binaries remain intact;
pre-change native source is archived. New isolated build has zero warnings/errors
and passes99 simulation suites; native/state parity check is running. No training
has yet used this option. Existing trainer uses frozen original sources/host.

This is a proposed easier curriculum, not evidence that reservation transfers
or that scores will increase. Validate original8..16s and full cities separately.

Short-delay validation complete: isolated native build99 suites;18 Python tests;
1,600 exact default native transitions across nine lessons plus city (160 city,
1,440 practice), including rewards,flags,info,raw observations,actor observations
and masks. Sixteen train/validation short-delay cases preserve exact reset and
first-second state, then reveal the future pair at2s. Reset isolation checks
preserve ordinary states after a short-delay fixture. Old host explicitly rejects
the new reset command. Host sha256bc4f243fddabdeeefbb16e178ab06a25149378f36aa2a1492ffcc39b70d9aed8.
No training yet uses the option; default8..16s evaluation remains unchanged.

Independent confirmation03 rejects extension midpoint:64 paired600s cities,
RNG950243,parent88.5625 vs86.96875,candidate−1.8%; both54/64 scoring. Paired
score−1.59375 [−10.0,6.890625],new targets served212→213,stockouts61→75.
The19.6% reused-development gain did not generalize. Cohort950243 is consumed;
no long launch and no selection based on a falsely claimed independent gain.
Further revisions need a new independent cohort (reserve950246);1200s cohort
950245 remains unused. Continue only bounded experiments, preserving all models.

Return-advantage midpoint: development77.84375 vs69.1875,paired+8.65625
[−5.68828,23.53125]. The reservation actor signal now has the expected std2.39,
then2.31, exactly matching returns; this implementation check is not improved
strategy. The original-delay skill review still shows failures. Keep final review.

Next bounded curriculum test (after current trainer exits):32,768 decisions,
seed156M,LR.001,balanced16 workers,task minibatches and reserve return advantages,
parent fixed at extension midpoint (not selected using new confirmation results).
Use optional2s reserve delay with warmup0 and the new isolated host. City rules
and native reward unchanged. Evaluate original-delay skills/cities on the old
host to keep evaluation identical to reference; cross-host default parity has
passed. Also measure paired parent/candidate short-delay reservation separately.
This is a new curriculum test, not a long launch. Advance to original-delay
practice only after strong short-delay performance with retained city service;
substantial independent city gain remains required for long readiness.

### 2026-11-24 13:36 — gradient clipping imbalance; controlled continuation

Frozen on-policy reservation diagnostic(16 trajectories,32 sampled transitions):
actor+entropy gradient norm0.84593 with return advantages; weighted critic norm
21,368.92 at vf_coef0.5. Shared max_norm0.5 clips both by2.33985e-5. Conventional
value-subtracted advantages give actor norm0.40056 with the same dominating
critic. This establishes a scale imbalance in this measured batch; Adam's
adaptive moments mean it is not proof of an exact43,000x learning-speed loss
or the sole cause of city failure. Future clipping is logged directly.
At vf_coef.001 the critic norm would still be42.74. Choose1e-5 for the bounded
continuation: its weighted critic norm for this same unscaled gradient would
be0.42738, comparable to actor0.84593. Native rewards/returns and value targets
stay in native delivery units; only the loss coefficient changes. No planner,
teacher actions, optimizer reset or policy initialization change.

Stop short-delay01 after saved16,384 midpoint,sha256
fea5d80883b619804db542098ac514be31af0f6fdcad2c1ed4b819d3efaf5132.
SIGTERM owned runner228648 triggers tested owned-child cleanup. Any subsequent
unsaved transitions are not carried forward; all saved files remain. Review
midpoint on original skills/cities and short-delay probes; no final exists.
Next continuation budget32,768,158M,otherwise identical2s balanced protocol,
vf_coef1e-5. New optional read-only gradient audit records first32 optimizer
updates by task and parameter group,before/after clipping. Hook unit test proves
bit-exact parameter updates versus an uninstrumented optimizer and bounded log
count;19 city tests pass. Load check preserves parameters,Adam state,counters,
and nine native actor distributions exactly when changing vf_coef.

Further measured optimizer audit: extension midpoint had4,608 Adam steps;
return-advantage final4,689 (+81) across four rollouts, with epoch counter820→824.
Configured maximum is4rollouts*4epochs*8192/128=1,024 optimizer steps. Short-delay
midpoint adds100 Adam steps over two rollouts (maximum512),epoch counter820→823.
Thus configured four PPO epochs are maxima, not completed epochs: target_kl.03
stopped optimization early. This safeguard is not itself a defect; task-homogeneous
minibatches may contribute to task-specific stopping. Actual gradient/task logs
in the new pilot will inform the next decision, not an automatic removal of KL
protection. No claim all1,024 updates happened in earlier pilots.

Short-delay midpoint review: city75.5625 vs69.1875,paired+6.375
[−7.28203,19.8125];original-delay reserve0/16. On separate2s validation cohort,
parent7/16 and midpoint7/16; reference route16/16,Wait/waste0/16. No demonstrated
short-task learning. Original-delay and city failure remain. Owned review
controller228649 stopped only after midpoint reviews finished and it was waiting
for the intentionally absent final. All midpoint results retained.

Live loss-balance audit after two rollouts captures17 actual optimizer updates:
3 reservation,6 priority,8 city (first32 audit cap not yet reached). The first
reserve update has group norms Wait0.1989,roads0.4719,spatial0.3412,critic0.4533,
and retains65.42% after global clipping. The earlier frozen baseline retained
0.00234%; these are different batches, not a paired speed claim. Critic domination
is reduced, but actor/priority gradients and KL stopping now limit update coverage.
Midpoint development78.0 vs69.1875,25/32 scoring,paired+8.8125
[−6.21875,23.53203]. Initial original-delay reserve Wait probe rises to0.64647
from approximately0.607 at the continuation parent. This is a learned distribution
change, not yet successful reservation or independent city improvement.

Return-advantage pilot final:32,768 decisions/8,383 episodes/1,011.53 seconds;
city74.75 vs69.1875,paired+5.5625 [−9.96875,20.71875],new targets90 vs91,
stockouts33 vs33. Priority27/32,original-delay reserve0/16,connections retained.
Reject as a city promotion. Complete records and all checkpoints preserved.

Value-balance midpoint: original-delay reserve1/16 vs0 at its parent,short-delay
9/16 vs7 on matched validation cases;priority29/32,join/route16/16,delay13/16.
This is small early progress, not readiness. First two rollouts use17 optimizer
steps out of512 maximum,still restricted by taskwise KL early stopping.

Frozen reservation signal diagnostic on16 training-layout seeds157100000+:
original4/16 successes,6s warmup6/16,2s arrival10/16. Full-cohort normalized
score-function estimates for additive Wait bias are+.02777,+.03487,−.00191,
respectively. Positive means an expected local increase in Wait on this sample;
these estimates are not exact minibatch PPO updates and are noisy. Some useful
prebuilding succeeds without stock remaining, so short-delay success is not
proof of learning to reserve stock. No teacher controls influenced these samples.
Future original-delay and city performance remain decisive.

Next conditional bounded continuation: use the retained value-balance candidate
(midpoint or final selected on development/skills, never fresh confirmation),
return to the original random8..16s reserve delay with zero warmup,lower base LR
from.001 to.0001,keep vf_coef1e-5,task-homogeneous batches and return advantages.
Budget65,536 decisions(eight512x16 rollouts),seed160M,first64 gradient updates
logged; checkpoint every rollout,review32k/64k on existing selection cohorts.
Reason: original-delay diagnostic has a stronger positive Wait signal than2s,
and smaller steps may permit more task coverage before target_kl.03 stops updates.
Do not remove that safeguard. This tests a combined curriculum/rate schedule;
it cannot attribute outcomes to either alone. Retain useful native connections
and at least95% city mean before continuing from a checkpoint. Original native
host is used again because the optionalshort-delay command is no longer needed.
Long launch still requires substantial fresh-city gain plus longer-horizon review.

Value-balance final:32,768 decisions/8,586 episodes. Development71.59375 versus
69.1875,26/32 scoring vs25,paired+2.40625 [−11.18828,15.375]. Join/route16/16,
delay13/16,priority31/32,original-delay reserve1/16. Final chosen only as the next
experimental continuation parent: stronger priority than midpoint29/32,same
reservation success,retained city threshold. It is not a city promotion or proof
of reliable score gain. All checkpoints remain available,including midpoint78.0.

Original-delay lower-rate pilot launched:runner248080,review controller248081,
65,536 decisions,seed160M,LR.0001,vf_coef1e-5,old native host,zero warmup,default
8..16s arrival. Native reward,weights,Adam progress,task allocation and clipping
safeguard preserved. Reviews include a paired comparison against its actual
starting value-balance final,as well as the original city reference. No long run.
Available ordinary-city suites contain593 unique seeds across54 files. Reserved
950245(32 longer cities) and950246(64 confirmation cities) have no overlap with
those available suites. Missing historical evidence cannot be ruled out.

Original-delay first8,192 checkpoint: optimizer827→831 epochs and4,741→4,997
Adam steps,exactly all256 configured updates. First64 logged batches include
32city/16reserve/16priority,one complete epoch's fixed allocation. Native original
reserve improves1/16→3/16 on the reused validation cohort; mean stock at arrival
1.375 versus value-final0.6875. This is early selection evidence,not a city gain.
An extra first-checkpoint reserve-only check was added to verify the mechanism;
it is not an independent cohort or a launch decision.

Opening diagnostic replays all10 already-seen zero-score confirmation02 games
with exact prior scores/road counts. Before the new actor gate activates,there
are405 states with legal road choices,321 chosen roads,and129 states with>99.9%
conditional probability on one road. Every case builds from time0. This rules
out simple initial hesitation in those cases; inefficient road selection and
stock depletion remain plausible. The gate still protects those early actions,
so current growth training cannot directly repair them. This is a separate
remaining limitation,not proof every zero-score map shares one cause.

Reporting change prepared for subsequent runs: record loaded and added Adam
step counts,actual/max updates each rollout,in checkpoint metadata and progress
CSV. This makes early stopping visible instead of presenting configured epochs
as completed work. No optimizer operation changes; active frozen runtime remains
unchanged. Syntax checked. Mask source audit confirms PracticeNewConnections
uses visible/native legality and does not read ConstructionReference; priority
fixtures have constrained visible dry-land corridors,not an oracle action mask.

Original-delay midpoint frozen review:67.28125 vs69.1875 on32 development cities,
paired−1.90625 [−18.21875,13.71875];vs actual start71.59375,delta−4.3125
[−18.34375,9.62578]. No long readiness. Original-delay reserve4/16 (start1/16),
stock at arrival2.0 (start0.6875);short-delay12/16 vs prior7/16. Priority31/32,
connections retained. This is improved conservation practice without proven
full-city benefit. Complete the bounded budget,checking tradeoffs rather than
promoting practice success alone.

Broaden development assessment to the already-consumed64-city RNG950242 cohort,
for midpoint/final. It is explicitly no longer an independent confirmation set.
Reuse its frozen parent model0 results from confirmation02 under identical native
host/horizon/action RNG; fresh950246 remains untouched. Waiting controller248081
was superseded only after midpoint standard reviews completed; controller258368
serializes broader midpoint,standard final,and broader final reviews (8 workers).

Checked whether600s score loss merely hides later conservation benefits: parent
5/32 horizon survivors,original-delay midpoint2/32,value-balance final6/32;
mean lifetimes373.25,371.41,377.52s. This cohort does not support excusing the
midpoint loss as a horizon artifact. Do not weaken or change the launch gate.
A longer-horizon review remains required if a candidate earns confirmation.

Broader development(64 reused950242 cities) gives original-delay midpoint88.671875
vs82.734375,parent54 scoring→candidate55;paired+5.9375 [−3.28125,15.296875].
New targets served202→222;zero-stock target arrivals58→27;median service delay
26s unchanged. This supports improved resource management on this selection
cohort,not a substantial independently confirmed score gain. Paid units76.53→
78.86,outside-route units33.20→34.23,so do not claim all excess construction is
fixed. Keep final review and the original long-launch gate.

Conditional next step if final mixed-task results still miss the score gate:
use a retained conservation candidate for65,536 city-only PPO decisions,seed162M,
same corrected vf_coef1e-5,LR.0001,512/128/GAE1 and target_kl.03. No new practice
shaping,teacher or planner. Earlier city-only trials did not have the measured
loss-balance/update-coverage fixes,so this directly tests full-game learning
under the corrected optimizer. Compare32k/64k on32+64 consumed development
cities and native skill retention. Original-delay midpoint/final selection uses
pooled matched development score across these disjoint cohorts (96 cases),with
>=95% parent mean,no lost aggregate scoring count and retained useful native
connections. Prefer the stronger retained pooled candidate; document selection
before city-only training. Fresh950246 and longer950245 remain untouched.
This is a conditional plan,not a launched job or a relaxation of the long gate.

Original-delay final standard development result:90.5625 vs69.1875 (+30.89%),
paired+21.375 [6.78125,37.5],26/32 scoring vs25. New targets served113 vs91;
zero-stock arrivals9 vs33;paid units76.875 vs74.84375,outside-route units37.90625
vs34.09375. No claim all excess construction is solved. Native checks:join/route
16/16,delay14/16,priority32/32,reserve9/16,stock at arrival2.5625. This is substantial
selection-cohort improvement after additional PPO updates; not confirmation yet.

Freeze original-delay final e72ec5ada055dd474f65ec0d032e6333128e241f8154ea2f3fc382c73dbf34e2
for64 fresh600s cities RNG950246 before those outcomes are seen. Selected using
final32-city result and retained/improved native skills; broader consumed final
review continues separately. Independent evaluator266867 runs8 workers alongside
8 broader-review workers; no trainers remain active. All policies stay frozen.
Conditional city-only training plan is not launched while this candidate is being
confirmed. Long launch still requires >=20% independent mean gain,positive paired
interval,no lost scoring-city count,and the reserved1200s retention check.

Broader final development review completed:64 consumed cities mean83.3125 vs82.734375,
paired+0.57812595%[-10.9535,12.171875],54/64 scoring each. Stockouts58→14,
new targets served202→218. Pooled96 disjoint consumed cases:85.72917 vs78.21875,
paired+7.51042[-1.79193,17.13542],80 scoring vs79. Retention passes; substantial
score-gain gate does not pass on pooled development. The32-city gain alone
was optimistic. Fresh950246 confirmation remains running; no trainer active.

Fresh confirmation04 completed:64 unseen cities RNG950246,reference85.953125,
original-delay final86.1875,53/64 scoring each;paired+0.23437595%[-12.65625,12.96875].
Stockouts53→26,served210→217. Reject substantial-score claim and long launch.
This cohort is now consumed. Reserved1200s RNG950245 remains unused.
Proceed with predeclared city-only65,536-decision test under corrected optimizer.
Select original-delay final by stronger pooled96 development mean85.7292 vs
midpoint81.5417,retention and native skills. Preserve all weights/Adam exactly;
city-only-final-load-check.json passes nine native actor probes. No reward,
planner,opening gate or architecture change. Seed162M,LR.0001,vf_coef1e-5,
16workers,512steps,batch128,GAE1,standard minibatches;midpoint/final matched32+64
consumed development and native retention reviews. This is a bounded pilot,
not the conditionally authorized long session.

Diagnostic follow-up to consumed confirmation04:reference16/64 cities survived600s,
candidate14/64;mean lifetime413.64→415.82s. Deaths with positive stock11→23,
zero-stock deaths37→27. Four selected regressions with positive stock were replayed
exactly;three had unserved new targets with affordable single-edge graph estimates
at arrival (costs6–10,stock12–31). One served all recorded new targets but died
at score83. This supports unresolved spending/connection/service problems,not a
claim all failures are hoarding. The audit's shortest-cost graph is diagnostic
only,never teacher actions or learner input;individual legal edges do not prove
joint route feasibility. Sources:confirmation04-failure-shifts.json and
reserve-loss-affordability.json. City-only first two rollouts each performed
256/256 planned Adam updates;training means are not frozen score evidence.

City-only update diagnostics: first six rollouts each complete256/256 updates.
Explained variance is0.50–0.67 (not a failed critic); measured KL0.00036–0.00163,
well below the0.03 early-stop threshold. First audited city minibatch group norms
before clipping:Wait0.095,road1.813,encoder0.974,critic0.959; afterglobalclip0.021,
0.399,0.214,0.211. Critic domination is no longer present in this sample. Do not
change reward/critic based merely on score noise. Midpoint32-city mean80.75vs69.1875,
paired+11.5625[0.90625,21.40625],26/32vs25,still below own starting90.5625.
Broader consumed64 and final reviews remain pending. No long launch authorized
by these interim results.

Engineering next comparison:bounded32,768-decision city-only LR.0003 versus
completed LR.0001 midpoint at the same32,768 budget. Same original-delay final
parent and162M training seed schedule;only base learning rate differs (auditing
limit may differ but hooks are verified read-only). Reason:all updates complete,
critic explained variance0.50–0.67,but city KL0.00036–0.00163 is far below.03.
Hypothesis:previous.001 was too aggressive,whereas.0001 may adapt too slowly in
full cities. Test the intermediate rate without changing rewards,architecture,
stock logic,practice mix or early-stop safeguard. Compare final on the same96
consumed development cities plus native retention;do not use a new independent
cohort unless materially stronger. Original low-rate final review continues.
This is a bounded hyperparameter comparison,not a long session or proven fix.

Post-gate exploration diagnostic on four selected confirmation04 regressions:
conditional top-road probability>.999 in24/214,122/265,114/459,90/501 legal-road
states. Mean conditional entropy1.189,.639,.785,.751 nats;meanWait.803,.858,.869,
.816;actual road choices33,33,54,98. Strong prior concentration exists but is not
uniform;these measurements do not prove exploration temperature is the dominant
failure or justify changing calibrated sampling. No exploration modification made.
Exact replay scores matched12,22,76,83. Source:growth-exploration-failures.json.
City-only final32-city mean84.90625 vs69.1875 (+22.72%,paired+15.71875[2.21875,29.5]),
still below own starting90.5625. Broader final96 pooled decision pending.

Completed city-only final:65,536 decisions,134 completed cities,897.02569s,
2,048/2,048 Adam updates. Pooled96 consumed cities89.76042 vs78.21875,
paired+11.54167[3.47891,19.62526],79/96 scoring each;served329vs293,stockouts72vs91.
Against own original-delay start85.72917,the increase+4.03125[-5.29193,13.17734]
is uncertain and scoring count falls80→79. Native join/route16/16,delay13/16,
priority31/32,reserve4/16 (start9/16). Do not promote as an unequivocal improvement:
city mean improves over calibrated reference,while conservation retention weakens.
Intermediate-rate pilot completed32,768 decisions64 cities,all1,024 updates;
frozen development/native reviews remain pending.

Additional native skill validation at170100000..170100063,original delay and no
warmup:calibrated reference reservation7/64 vs frozen original-delay final32/64;
priority32/64→64/64,swapped35/64→64/64 (combined67/128→128/128). Available prior
curriculum evaluation configs had no seed overlap. This supports generalized
learning on these fixture families;does not establish full-city score gain,
all-tool strategy or leaderboard performance. Candidate frozen before these
outcomes. Sources:additional-skills-launch.json,additional-skill-cohort-check.json,
output/training/city-strategy-additional-skills-01 (small files archived).

Structural opening experiment:the protected existing actor intentionally freezes
bad openings too (see city_established_policy.py and 23Nov regression repair).
The earlier10-zero-city replay confirms only174/1,898 decisions had the growth
gate active;8 first activated at140–142s and2 never activated. Further growth-only
updates therefore cannot directly fix those early choices. Add a separate learned
opening residual inside the same policy,active only before the existing visible
matching-network gate. Freeze the entire inherited feature/actor stack;train
new opening spatial encoder/road/Wait heads plus critic. Zero output heads ensure
exact initial behavior;copy the learned spatial encoder for initialization.
No planner,teacher,reward shaping,native change or hidden information added.
Existing state-conditioned established behavior must remain exact after arbitrary
opening-parameter changes. Changed opening decisions may still change later
city states,so full-city and skill retention checks remain necessary.
New actor parameters need fresh optimizer moments;retain the four critic Adam
states and all original weights/counters. Preserve original checkpoint as rollback.
Plan bounded65,536 native-city decisions,seed164M,LR.0001,vf_coef1e-5,16workers,
512steps/batch128/GAE1,midpoint/final96 consumed city reviews plus native tests.
Do not launch until zero-initialization,gradient isolation,load/save and native
same-state invariants pass. Long-session gate remains unchanged.
Preparation attempt01 failed in diagnostic NumPy sampling because float32 sum
was used to normalize float64 probabilities. No model was saved. Preserve empty
attempt01 directory and script;attempt02 normalizes in float64 consistently.
This was a preparation harness error,not a PPO/native transition failure.

Opening preparation attempt02 passes120 native opening-state actor/value exact
comparisons,9 native fixture initial actors,9 established actors after arbitrary
opening parameter changes,and4 critic Adam states through save/load. Seven focused
unit tests pass. Initial checkpoint74b3a046394147eb8a8cbe730cb2c0352eee14c49dd9b6b4e64357595f7749ab.
Bounded opening65,536-decision pilot launched PID294537,reviews294538.
Intermediate-rate city trial failed to improve:96-city84.30208 vs78.21875,
paired+6.08333[-2.88542,14.92734],80/96scoring vs79;reservation4/16,priority31/32.
Reject higher-rate promotion;do not launch long training from either city-only trial.

Opening first-rollout audit passes at8,192 decisions:only opening_strategy_ and
critic parameters changed;all old actor/feature weights exact;all9 established
fixture initial distributions exact. Six opening probes show total variation
0.050–0.145 and increased Wait probabilities. This proves trainable opening
behavior changes,not that those changes improve scores. Source:opening-first-rollout-audit.json.

Opening evaluation plan:use the same32+64 consumed development cities for midpoint
and final selection,plus fixed native retention tests and feature isolation audits.
If a candidate shows substantial development improvement,freeze it before a new
64-city confirmation RNG950247 (checked against available suites for overlap).
Compare calibrated reference,original-delay conserved parent,and selected opening
candidate together to distinguish inherited gains from opening training. Keep
reserved32-city1200s RNG950245 for the longer-horizon gate. No new confirmation
cohort is evaluated merely to search for a favorable result. Long launch requires
the original independent substantial-gain and retention gates;no guarantee of
future improvement is possible. Opening-only continuation leaves learned growth
behavior fixed for the same state,while changed early roads can change later play.

Opening midpoint96-city development:81.52083vs calibrated78.21875,
paired+3.30208[-6.60443,13.04167],80/96scoringvs79. Own conserved parent85.72917
was higher. Stockouts37vs calibrated91;new targets served310vs293. No substantial
score improvement. All144 complete native fixture evaluation rows are exactly
identical to conserved parent (same layout/action seeds),confirming retained
established behavior through full trajectories,not only initial distributions.
Opening training completed65,536 decisions and135 native cities;final evaluation
pending. Do not infer overnight readiness from successful isolation or lower
stockouts. Sources:opening-midpoint-pooled-development.json and
opening-midpoint-native-exact-replay.json.

Material finding,24Nov~15:45–15:55 Beirut:all10 already-seen zero-score seeds in
confirmation02 have no affordable ordinary-road path to the initial destination
throughout a Wait-only control before native game over (139.7–154.2s). This is a
diagnostic legal-edge graph,not a teacher/planner. At least seed99005063 is
physically solvable with its starting bridge:manual fixed native control uses
7road units and1bridge,then delivers3 trips by60s. Current CityRoadEnd explicitly
rejects every water endpoint,including existing bridge tiles;the actor cannot
issue the necessary crossing despite visible starting inventory[25,1,0,0,0,0].
Thus the earlier interpretation of all zero games as a learnable opening fault
was too broad. This action-coverage limitation must be fixed before more road-only
training. Other missing tools/weekly policy choices remain separate limitations.

Engineering change:optional cityConnectionMask/cityConnection native commands add
legal neighboring bridge edges using native stock,span degree,water direction,
parcel and diagonal-crossing rules. Same undirected edge action space;native
stroke orientation is resolved only for the requested edge. No route search or
strategic mask filtering. Legacy cityRoadMask/cityRoad behavior unchanged.
Python --allow-bridges is explicit and defaults off;observation dimensions unchanged,
existing visible global inventory includes bridge stock. Records identify action
profile and summarize native bridge tiles/stock. Comparison/pooling tools now
reject mismatched profiles. Tests:104 native suites pass (99 prior+5new),including
144 sampled requested-edge transitions against ordinary native DrawRoad controls.
Old/new default-protocol parity and Python bridge-mode checks still pending.
Native build isolated in output/city-bridge-connection-build-01;prior DLLs retained.
Opening final96-city result84.28125vs78.21875,paired+6.0625[-4.02135,16.55260],
81/96scoringvs79. Own conserved parent85.72917 was higher. No long launch.
Sources:opening-wait-opportunities.json,zero-opening-native-snapshot.json,
bridge-capability-control.json,bridge-native-tests.txt. Controls are never trainer inputs.

Bridge mode validation complete:104 native suites,11 focused Python tests,
1,600 exact default legacy transitions across16seeds,legacy mask subset preserved,
new Python mode executes the fixed native bridge control (3deliveries,18roads,
0bridges remaining),old host rejects unsupported mode explicitly. Final host hash
406856cd35d2f33d2a5a06661b6440762fb790db8ff69a05c34aafb881adbec6.
Protocol check attempt01 incorrectly requested a final driveway edge already
attached automatically by native road construction. Corrected test skips only
an edge whose native connection bit is already set;attempt02 passes. No mask
relaxation or simulator change was needed for this test correction.
Frozen32-city bridge-mode evaluation PID311635:calibrated reference,conservation
candidate,and opening final. All three share newhost/bridgeprofile and same
consumed development seeds/actionRNG. Added bridge access is engineering,not
PPO learning;within-profile comparisons isolate checkpoint differences. No trainer
or long run active. Prior road-only records remain historical and untouched.

Completed frozen bridge-mode32-city results revise the initial-probability
hypothesis. Calibrated reference124.40625,29/32scoring,mean1.71875bridge tiles;
conserved candidate121.9375,29/32,2.0bridge tiles;opening final117.125,29/32,
1.75bridge tiles. Existing policies DO use bridges later in actual play.
Initial water probabilities1e-9..1e-8 on selected states do not establish a
whole-trajectory exploration failure. The new normalized bridge-choice policy
and its3passing distribution tests remain an UNUSED prototype:do not initialize
or train it based on that disproven generalization. No checkpoint uses it.

The unchanged calibrated checkpoint rises69.1875→124.40625 (+79.81%) on the same
32cities by fixing action coverage. That is engineering improvement,NOT PPO.
Conserved and opening PPO variants do not beat the bridge-enabled calibrated
reference on this set. Future PPO comparisons must use the stronger bridge-mode
baseline,not claim learned gains against the handicapped dry-road interface.
No long launch yet. Review longer-horizon bridge baseline and corrected-optimizer
bounded continuation before any long launch;keep reward/native simulation fixed.
Sources:bridge-interface-paired-development.json and bridge-initial-development-01.

Bridge-mode continuation plan (supersedes unused opening-phase600s confirmation
plan):21/32 reference cities now survive the600s cutoff versus5/32 before the
interface fix. Use matched1200s baseline/candidate reviews to expose later stock,
service and congestion outcomes. Never compare raw600s and1200s scores as gains.
Baseline:calibrated reference and conserved original-delay final,32 consumed
seed950241 cities,bridge enabled,newhost. Bounded PPO starts the conserved model
(retains learned reservation/priority;bridge600s mean121.94vs reference124.41,
29/32scoring each),not the unused bridge-choice prototype or unpromoted opening
correction. Same CityWideStrategyPolicy,existing opening reference frozen.
65,536 decisions,seed166M,16workers,balanced8city/4reserve/2priority/2swap,
original reservation delay,no warmup,task minibatches,reserve return advantages,
LR.0001,vf_coef1e-5,GAE1,512steps/batch128,city horizon1200,allow_bridges true.
Evaluate midpoint/final on matched32-city600s retention and32-city1200s development,
plus native skill retention. If selected candidate improves substantially,freeze
before fresh64-city1200s confirmation RNG950247 (still unused). Require>=20%
mean gain over bridge-enabled calibrated reference,positive paired interval,
no fewer scoring cities,and useful skill/600s retention. Learned change relative
to its own conserved starting checkpoint must also be reported;interface gains
alone do not establish PPO improvement. Original reserved950245 remains unused.
No long session is launched by these bounded jobs.


### Bridge continuation selection correction — 2026-11-24

Measured matched32-city1200s bridge baseline: calibrated reference230.96875 versus conservation parent185.53125; paired delta−45.4375,95% interval[−92.5953125,4.18828125]. Fewer stockouts did not prove better city performance. Engineering decision: stop balanced continuation at preserved24,576-decision checkpoint (768 Adam updates), cancel waiting midpoint reviewer, retain all artifacts. Any subsequent unsaved rollout tail is not preserved. Next evaluate existing city-only final with the same bridge interface and1200s cohort before selecting further training. This is development selection, not independent confirmation. No long run launched. Stop evidence: docs/training/city-strategy-launch-2026-11-24/bridge-balanced-stop.json.

Evaluate the preserved bridge-balanced24,576 checkpoint as well as city-only final on the same32 consumed1200s bridge cities. This checks whether the short bridge continuation recovered its weaker starting behavior, before discarding or resuming it. Eight evaluators alongside the city-only16-worker evaluation; no training concurrently. Both candidate selections remain development analyses.

Matched city-only final bridge1200 development result: mean220.0 versus calibrated230.96875,29/32 scoring each,paired difference−10.96875 with95% interval[−74.56328125,49.59453125]. New targets served178 versus175; mean construction outside observed assigned routes47.46875 versus37.8125 (difference9.65625,interval[3.40625,16.1875]). This is not a score improvement; do not promote city-only final. Await preserved bridge24k result before selecting training parent. Evidence: bridge-city-only-longer-comparison.json in the strategy archive.

Longer-city survival diagnostic (same development cohort): calibrated/conserved/city-only models survive1200s in1/32,0/32,0/32 games; mean native lifetimes655.87/607.09/661.47s. Final road inventories average0.91/7.50/0.84. These descriptive figures support a timing tradeoff, not a causal claim that conserving roads itself kills cities. Remaining zero-score seeds are identical across all three:99020130,99047255,99202636. Evidence: bridge-longer-survival-development.json.

Bridge reference parity check passed1,024 sampled observations across8 development city trajectories (~98–104s each), calibrated reference versus existing zero-output wide initialization. Exact masked probabilities; no training or checkpoint changes. Source/checksums/result: check_bridge_reference_parity.py and bridge-reference-wide-parity.json. This supports starting a corrected-optimizer city trial from the stronger reference if saved balanced24k is not better; does not prove learned improvement.

Preserved bridge-balanced24,576 evaluation completes: mean183.6875 vs calibrated230.96875,29/32 scoring each; paired delta−47.28125,95% interval[−115.18828125,16.8765625]. Arrivals with zero roads8 vs44; fewer stockouts again did not prove higher city score. No promotion. Start bounded bridge-reference-city-01 from actor-equivalent wide initialization, per declared plan:65,536 city-only decisions,16workers,1200s,bridges,seed168M,LR.0001,vf1e-5,GAE1. Preserve all other models; no new architectural/reward change. This restarts optimization from stronger inherited behavior and fresh saved optimizer state. Review32k/final against calibrated bridge baseline; no long session launched.

First bridge-reference-city rollout saves8,192 decisions and completes256/256 intended Adam updates. First64 audited updates show finite actor/critic gradients; zero spatial encoder gradient on the first update is expected from zero-initialized output heads and becomes nonzero on the second update. Initial KL4.61e-6 is small; early optimization movement is not evidence of performance gain. Ten early completed training games average39.1, with longer unfinished games excluded; do not compare that completion-biased mean to frozen full-cohort230.97. Source: bridge-reference-first-gradient-summary.json and archived progress/checkpoints.

Eight representative calibrated-reference terminal replays exactly reproduce all recorded evaluation fields. Six failing destination graphs have at least one matching connected home and assigned cars; two have neither. Selection is score-order indices0,4,8,12,16,20,24,31, not a prevalence estimate. Terminal connectivity alone cannot distinguish late completion from congestion. Follow-up of zero-score seed99020130 finds no cars assigned to the initial destination through140s; at native death144.95s four outbound cars have positive speeds on12–15-point routes. This supports an opening completed too late, not a demonstrated traffic deadlock or simulator bug. Do not modify collision rules based on that terminal snapshot. Evidence: bridge-reference-ending-diagnostics.json, bridge-zero-city-traffic.json and their diagnostic scripts. No routes/actions were supplied to learner.

Read-only midpoint Adam-scale diagnostic: actual optimizer epsilon is1e-8, not SB3 Adam default1e-5 (custom RelativeRateAdam). Spatial encoder median bias-corrected second-moment root is523×epsilon and only3.67% of its parameters fall below epsilon. Reject the speculative explanation that Adam epsilon broadly suppresses spatial learning; no epsilon change. Critic explained variance remains near0.002–0.019 in early rollouts, a measured limitation but not sufficient by itself to identify its cause. Evidence: bridge-reference-midpoint-optimizer-scale.json and archived progress.csv.


### Bridge reference midpoint and conditional learning-rate check

Measured32,768-decision midpoint: mean231.0 vs calibrated230.96875,29/32 scoring each; paired delta0.03125,95% interval[−61.8140625,62.90703125]. New targets served170 vs175,stockout arrivals54 vs44. No learned score gain established. Complete predeclared65,536 trial; no promotion from unchanged development mean.

If final fails substantial-gain development gate, test a separate32,768-decision city-only trial from the same zero-output wide initialization, same168M training seeds/1200s/bridge profile/16workers/512steps/batch128/4epochs/GAE1/vf1e-5, but baseLR.001 versus.0001. Save16k midpoint and32k final. This compares learning rate at the same initialization and decision budget (low-rate32k midpoint), unlike older higher-rate trials starting a conservation-trained policy on the dry-road interface. Preserve KL.03 and gradient clipping. Rationale: current per-rollout approximateKL~4e-6–3e-5 and small actor changes, weak critic explained variance; these suggest a rate test, not proof that larger steps will help. Evaluate both saved high-rate policies on the same32 consumed development cities; only a frozen substantial improvement proceeds to unused confirmation. No automatic long run or gate relaxation.

Conditional bridge-reference-rate-01 launched after low-rate final failed the predeclared development gain gate.32,768 city-only decisions,LR.001,otherwise same starting policy/168M seeds/1200s bridge environment and optimizer coefficient. Bounded comparison only; launch record and matched reviews in strategy archive.

Low-rate bridge-reference-city-01 completes65,536 decisions/90 city episodes in1293.79 training seconds with2048/2048 Adam updates. Final SHA f30db996223d11a932a597284bc74b33e2b696e9ddf739e2a9bc2314c948fb66. Matched32-city1200s final mean196.5 vs230.96875,29/32 scoring each; delta−34.46875,95% interval[−100.93984375,25.625]. No promotion; midpoint231.0 also did not establish a gain. Runner separately records regression_stop on its two-city guard; this does not erase final or replace the larger comparison. Starting-value prediction mean rises29.56→101.72 across32 initial states; critic is learning but not well calibrated to these full-game outcomes. Conditional higher-rate32,768 trial started as declared; no overnight launch.

Read-only loss-component audit of low-rate final:2,048 decisions on169M diagnostic training seeds,16 minibatches,zero optimizer updates and exact unchanged weights. Mean policy versus weighted-entropy gradient norms:Wait0.624 vs0.0618;road heads0.654 vs0.00311. This sample does not support exploration regularization dominating actor learning. Shared spatial encoder value-gradient norm0.0822 exceeds policy0.0128, while critic-only norm0.0863; distinguish shared representation gradients from the previously fixed global critic-gradient problem. No entropy/epsilon change is justified from these results. Higher-rate trial first rollout matches all ten completed initial low-rate game scores before updates, then completes256/256 updates with approximateKL0.00143. Evidence: bridge-loss-components.json and rate progress.csv.

Extended read-only diagnostic exactly reproduces previous loss-component norms and adds conditional road-probability checks on2,013 states with>=2 legal roads. Low-rate final versus calibrated initialization: mean conditional-road total variation0.02360 (median0.01174), mean Wait probability change−0.01020. Reference conditional top-road probability mean0.7068,median0.8627;31.50% exceed0.99. Thus inherited sharp priors are a limitation in some states but road choice is not generally frozen, nor do the observed updates change only Wait. Mean actor/value gradient cosine on shared spatial encoder0.000741, not evidence of broad opposing gradients. No architecture or entropy change based solely on these hypotheses. Zero optimizer updates and all weights exactly preserved. Evidence: bridge-loss-components-v2.json and audit_bridge_loss_components_v2.py.

Higher-rate midpoint16,384 evaluation: mean244.4375 vs230.96875,29/32 scoring each,paired delta13.46875 with95% interval[−52.68828125,75.15703125]. This5.83% development increase is uncertain and below the substantial-gain gate. Weight audit preserves opening probes and changes only allowed tensors. Full32,768 high-rate budget completes1024/1024 optimizer steps; final review pending. Do not infer readiness from the favorable midpoint mean.

Before spending further training budget, freeze higher-rate16,384 midpoint for64-city paired bridge1200 evaluation against calibrated reference, RNG950242 (previously consumed broader development cohort, not fresh confirmation),16workers. Reason: +5.83% result on32 reused selection cities is too uncertain to justify continuing merely from its favorable mean. Final32k review continues separately. Unused950247/950245 cohorts remain untouched; no further trainer or long session launched. Evidence: bridge-rate-midpoint-broader-launch.json.

Higher-rate32,768 final review completes: mean181.90625 versus230.96875,29/32 scoring each,paired delta−49.0625,95% interval[−116.62890625,10.28203125]. The rate increase did not establish improvement; no final promotion. Midpoint244.4375 remains only a weak development candidate under broader64-city review. Both bounded trainers have exited; no new training is authorized by these statistics alone. Existing user long-launch authorization remains conditional on evidence, not revoked.


### Real-city recorded starts — preparation, not demonstrated improvement

Engineering hypothesis: give PPO more decisions in actual expanding cities, rather than further optimizing synthetic reservation exercises or merely raising the global learning rate. New optional CityRecordedStartEnv reconstructs a native city by replaying a frozen existing policy prefix only during reset. These actions are not labels, PPO samples, reward, a route planner, or actions imposed after reset. The policy controls every subsequent legal connection/Wait decision and receives subsequent native deliveries only. Three workers in four use recorded starts; one retains ordinary cold starts. Default training/evaluation remains unchanged without --city-starts. The runner freezes and hashes the manifest alongside source and host.

Six native checks pass: exact world/visible motion-history replay, exclusion of prefix score/actions, subsequent reward/trips identity, explicit evaluation-reset bypass,32 exact cold transitions, rejection of corrupt replay and wrong host. The smoke prefix uses a consumed development seed for testing only and must never be used as training data. Separate dataset generation now uses128 seeds170000000..170000127, fixed280s prefixes of the calibrated reference; retain only native-live states with completed service, selected using prefix-visible outcomes only. Exclude failed/nonserving prefixes with recorded reasons. Future state/action information never selects learner actions. No policy update or long launch is part of dataset preparation.


### Broader rate result and predeclared recorded-start pilot

Frozen higher-rate midpoint fails broader64-city bridge1200 retention: calibrated262.765625 vs candidate231.546875,61/64 scoring each; delta−31.21875,95% interval[−83.00078125,19.579296875]. This supersedes the favorable32-city midpoint mean as a promotion argument. No fresh confirmation consumed. No previously tried PPO candidate is promoted.

Proceed with one bounded recorded-start mixture after dataset/native replay/integration checks:128 requested training seeds170M, prefixes at280s generated by calibrated reference, retain live serving starts without looking ahead. Require at least64 retained starts. Start the same actor-equivalent wide initialization, LR.0001,vf1e-5,16workers (12 recorded/4 cold),cold seeds172M,512 rollout steps,batch128,4epochs,GAE1,1200s,bridges. Budget65,536 decisions; checkpoint each rollout,32k midpoint/final matched32-city full-start evaluation. Report cold/warm training scores separately; warm rewards exclude prefix deliveries. Hypothesis is more native midgame practice and shorter reward delays; not a claim of causality or improvement. Existing cold-only low-rate result remains comparison context, but changed seed/data distribution prevents calling this a perfectly controlled one-variable study. If selected candidate passes substantial development gain, verify600s/skills and broader retention, then unused64-city confirmation950247. Original20% positive-interval/no fewer scoring-cities gate remains. This is not an overnight run.

Implementation checks so far:6 native replay checks and5 existing runner/reporting/gradient tests pass; Python compilation passes. Default environment/evaluation unaffected without --city-starts. Native simulator and reward rules unchanged.

Recorded-start generation completes109/128 retained cities,all at280s;mean prior score39.37,mean stock28.53(range20–38),mean prefix328.43 decisions. Manifest SHA bd8a5b8a0c4f8706ca51dae240e9191ae6cfa80d4ed2f5514630537d5177c393. Integration smoke completes256 decisions and16/16 Adam updates; its checkpoint is retained only as a smoke artifact, never selected for training/evaluation promotion. A separate full Wait-only Monitor control reports56 subsequent deliveries,excluding40 prior deliveries,191 decisions,correct warm episode fields. First smoke had no completed games and printed nan as an empty-statistic placeholder; logging now says pending until a game completes. No nonfinite model result was observed. Start bounded recorded-city-01 from unchanged wide initialization after these checks,per declared65,536-decision plan. All rollout/optimizer progress and separate warm/cold episode metrics are recorded. No overnight launch.

Pooled96 consumed bridge1200 development cities confirm no promotion for higher-rate midpoint SHA92adb88c255578d338eb5a2e3db23c2bb914c20bbd4e58b3d1e9ca05fe55576c: calibrated252.16667 vs candidate235.84375,90/96 scoring each; delta−16.32292,paired95% interval[−57.86484,23.39635]. Nonoverlapping cities, matched action RNG/host/horizon/profile and candidate hashes checked. No independent cohort consumed. Evidence: bridge-rate-midpoint-pooled-development.json plus source rows.

Performance-only optimization: CityWideStrategyFeatures now reuses pure visible service/relation evidence within a single forward call. Cache is cleared in finally, never spans decisions/updates, and is bypassed for inputs requiring gradients. No new weights, actions, labels or rewards. Eight native midgame states using a trained nonzero-residual checkpoint pass exact features/probabilities/values/gradients and one Adam-update parity; original saved checkpoint unchanged. GPU batch8 timing suggests1.232× throughput for the tested forward workload, not an end-to-end guarantee (active trainer also used GPU). Enable caching by default for future loads; the active recorded-city trainer uses its frozen pre-cache source. Evaluation remains numerically unchanged in checks. Evidence: evidence-cache-check.json and check_evidence_cache.py; previous source preserved in recorded-start-before/.

Evidence-cache CPU validation also passes exact features/probabilities/values/gradients/one Adam step on8 native midgame states, with cache cleared and checkpoint unchanged; tested CPU batch8 speedup1.346×. Service-feature body calls fall7→2 in a forward. Two wide/opening policy unit tests pass with caching enabled by default. These are scoped performance checks, not score gains; timings occurred alongside active work and do not establish whole-training throughput. The active recorded-city runtime remains its frozen pre-cache source. CPU validation source/result and unit log are archived.

Recorded-city first saved rollout8,192 decisions completes256/256 updates; first64 gradient checks show no global clipping suppression (mean pre/post norms identical), actor gradients present. Subsequent16,384 save has512 updates and27 completed episodes (4 cold,23 recorded starts). This is training activity, not a measured full-city improvement.

Additional action-coverage review (source inspection, not exhaustive simulation): the dry crossing-diagonal check in CanDrawCityRoad matches native Connect’s SplitsCorner condition; it does not blanket-ban native legal dry corner junctions. Rail endpoints remain excluded, but the captured current LosAngeles native map has zero rail lines, so this does not explain these runs. Roundabout/motorway/deletion/learned weekly choices remain outside this experiment’s action profile. No further native mask change was made from these checks.


### 2026-11-24 — recorded midpoint and isolated critic-rate test preparation

Measured recorded-start midpoint32,768 full-start evaluation:211.3125 versus calibrated230.96875,29/32 scoring each; paired delta−19.65625,95% interval[−110.003125,67.96875]. No demonstrated transfer gain. Let the predeclared65,536-decision budget and final review complete before selecting another trainer. Evidence: recorded-midpoint-longer-comparison.json.

Engineering hypothesis: low-rate value fitting remains weak (explained variance near zero), while the higher global-rate pilot reached0.2123 but regressed city scores. Isolate the dedicated value-head rate without increasing actor or shared-encoder rates. Added optional --critic-lr-scale to trainer/runner; defaultNone preserves existing behavior. Dedicated-group validation rejects shared/missing groups and nonfinite/nonpositive scales. Two unit tests pass; real checkpoint save/load check preserves every weight, Adam moment and2048 optimizer steps, with source checkpoint SHA unchanged. Evidence: critic-scale-checkpoint-check.json and training/test_city_optimizer_settings.py. No causal conclusion yet; changing only the head may not resolve shared representation or long-term credit assignment.

Conditional bounded next trial, only if recorded final fails strong development gain: start unchanged actor-equivalent wide initialization, cold-city seeds168000000,16workers,4rollouts×512=32,768 decisions,1200s native horizon,bridges,baseLR.0001,vf1e-5,GAE1,batch128,4epochs. Set dedicated value-head lr_scale1.0 instead of0.1; all actor/shared scales unchanged. Validated exact-parity evidence cache is enabled. Evaluate16,384 midpoint and32,768 final on the same32 development cities950241 against calibrated baseline; compare final to previous low-rate equal-budget midpoint. No recorded-start mixture in this controlled test. Preserve all checkpoints. Strong-gain, retention, and unused independent-confirmation gates remain unchanged before any long launch. No promise of improvement.

Recorded-start final65,536 review:234.90625 versus230.96875,29/32 scoring each;paired delta3.9375,95% interval[−79.75078125,84.6875]. New-target zero-stock arrivals104 versus44,paired delta1.875 percity,95% interval[1.0,2.78125]. Reject promotion: uncertain1.70% mean difference and worsened conservation. Root2-city guard marked regression_stop; full32-city comparison governs scientific conclusion. All prior processes exited. Proceed with predeclared bounded critic-head-rate test; no long launch.

Critic-rate first8,192-decision rollout completes256/256 updates. All10 pre-update completed city episodes exactly match the prior low-rate control (excluding wall time), supporting unchanged starting behavior and exact-parity cache activation. First64 gradient checks retain actor gradients and show no global clipping suppression. Evidence: critic-rate-first-rollout-check.json. No score inference from completion-biased first10 training games.

Published BRIDGE_RESULTS.md to consolidate eight matched32-city bridge/horizon comparisons without hiding failed candidates. Added value-fit-comparison.json with rollout explained variance/value loss/KL/actual updates for the cold low-rate, global high-rate, recorded-start, and active critic-rate trials. This is diagnostic learning evidence only; no optimizer metric substitutes for native score improvement. First two critic-rate variance measurements0.0061,0.0252 versus low-rate0.0061,0.0193; not yet a meaningful value-fit conclusion.

Critic-head-rate trial completes32,768 decisions,45 cold-city episodes,1024/1024 optimizer updates in545.88 active seconds. Final SHA4e51f8c6368802d8bc7c3b7cb36909ccc1910a4f0bba369fae53697b4a336140. Explained variance across four rollouts0.00610,0.02520,0.06574,0.09193 versus equal-budget low-rate0.00610,0.01926,0.01638,0.00164. This supports faster value fitting but not causal score improvement: midpoint16,384 mean205.625 versus230.96875,29/32 scoring each,paired delta−25.34375,95% interval[−102.12890625,43.12578125]. No promotion. Final full-city review pending.


### 2026-11-24 — critic result and longer credit-window test

Critic-head-only rate final32,768:220.53125 versus calibrated230.96875,29/32 scoring each; paired−10.4375,95% interval[−75.81328125,52.12578125]. Equal-budget low-rate control231.0, paired−10.46875 [−77.4703125,57.659375]. New targets served166 versus reference175,stockouts48 versus44. Faster value fitting did not establish better city strategy; no promotion and no long launch. All trial/reviewer processes exited. Checkpoints retained.

Next engineering hypothesis: longer rollout windows reduce reliance on weak bootstrap values for delayed road payoffs. Prior cold run has90 completed games,median713.5 decisions;60 exceed512,6 exceed1024. These lengths motivate testing but do not prove causal failure. At gamma1/GAE1, completed trajectories have direct sampled return targets; unfinished tails use a learned bootstrap. Optional --rollout-steps now flows through frozen runner/config to existing trainer, default512 unchanged. Three runner tests and Python compilation pass.

Predeclared bounded comparison: same original wide initialization,16 cold-city workers,seeds168M,baseLR.0001,vf1e-5,original critic scale0.1,bridge1200 profile. Change rollout length512→1024,with2rollouts=32,768 total decisions and same1024 maximum Adam steps. Compare midpoint16,384 and final32,768 against calibrated baseline and final against previous low-rate32,768. The policy-update timing necessarily changes with rollout length. Do not carry the unsuccessful critic-rate checkpoint into this test. No planner/imitation/reward/physics change. Expected buffer arrays8.33GiB,conservative doubled flatten storage16.67GiB; no concurrent evaluation during training. Reject2048-per-worker variant for RAM risk. Review both frozen checkpoints sequentially after trainer exits. Existing strong gain,retention,independent confirmation gates remain; this is not an overnight run.

Retrospective return-coverage diagnostic checks episode boundaries against worker seeds and cumulative lengths. On the same65,536 recorded low-rate decisions,20,988 (32.025%) have a native terminal within their512-step rollout window; regrouping those fixed trajectories into1024-step windows gives36,280 (55.359%). Time-limit truncations still count as bootstrapped. This is a counterfactual window regrouping, not a claim that new on-policy trajectories or scores will match. Evidence: analyze_rollout_bootstrap.py and rollout-bootstrap-coverage.json.

Longer-rollout first16,384 decisions complete512/512 updates and save midpoint. Frozen config verifies1024 steps,32,768 budget,original optimizer scales[1,.3,.1,.1]. First64 gradient checks show actor gradients and no global suppression. Memory remained within host capacity and dropped after optimizer pass. No evaluations overlap training. Evidence: long-rollout-first-check.json.

Longer-rollout trial completes32,768 decisions,42 cold-city episodes,1024/1024 optimizer updates in545.83 active seconds. Final SHA3a8352496aaf11c0c263c6846e3021fea42aaea667b3ef3e2e82f68a8b40c98c. Actual native-terminal target coverage17,299/32,768 (52.792%); hypothetical512 regrouping of the same trajectories10,437 (31.851%). Changed coverage occurred as intended; no score conclusion before frozen review. All weights and host hashes remain intact. Evidence: long-rollout-bootstrap-coverage.json and saved complete.json.

Longer-rollout midpoint16,384 full-start review:239.15625 versus230.96875,29/32 scoring each;paired delta8.1875,95% interval[−27.84453125,42.93828125]. New targets served184 versus175,stockouts49 versus44. A modest3.545% development increase,not substantial/confirmed gain. No promotion. Two-city runner guard favored final276.5 versus146.5 (one scoring city each); root best_checkpoint is local guard bookkeeping,not global promotion or launch evidence. Final32-city review now active.

Longer-rollout midpoint paired outcomes:15 cities improve,11 worsen,6 tie versus calibrated reference. Per-city deltas archived in long-rollout-midpoint-paired-games.json. The positive mean remains uncertain and is not a broadly established strategy improvement. All training has finished; only final evaluation remains and no further trainer is queued.


### 2026-11-24 — continuation outcome: long launch remains unjustified

Longer-rollout final32,768 review:213.03125 versus calibrated230.96875,29/32 scoring each;paired delta−17.9375,95% interval[−78.75,39.7203125]. Against equal-budget low-rate32,768 control231.0:delta−17.96875 [−79.28203125,39.25078125]. New targets served177 versus reference175,zero-stock arrivals43 versus44; these do not establish score improvement. Midpoint239.15625 did not persist. Reject global promotion despite the runner's favorable two-city local guard. Both midpoint/final audits preserve protected opening probes and change permitted tensors only. All trainers/reviewers completed; no further training queued and no long session launched.

Measured conclusion: recorded midgame exposure, faster dedicated critic learning, and longer rollout credit windows each exercised their intended mechanism but did not establish substantial full-city score gains. Current implementation performs PPO updates with finite losses, legal masks and gradients; that is not proof of effective strategy learning. Retain calibrated reference and all trial checkpoints separately. Fresh confirmation950247 and reserved950245 remain unconsumed. The user's desired reliable large score increase remains unresolved; no claim that another long run will work.

Next investigation should focus on decision-level policy failures and whether return targets/representation distinguish successful expansion from unproductive building, with a falsifiable intervention and native-score validation. This is an open research direction, not an implemented fix or a claim that more time alone suffices. Existing optional experimental knobs retain their defaults; no unsuccessful candidate is made the default model.


### 2026-11-24 — strategy bottleneck explanation and proposed diagnostic

User asks what prevents strategy learning and what to do next. Source-verified limitation: current CityWideStrategyPolicy freezes inherited features/actor and learns additive road/Wait corrections plus critic/spatial branch. Both actor correction paths are multiplied by established, which requires more than two building entrances and at least one graph-connected matching home/destination pair. Therefore these runs cannot change decisions before that gate, including early layout/resource choices. This intentionally protected earlier skills; it is a proven learning restriction, not proven sole cause of the full-city plateau. Do not describe the entire actor as frozen: permitted road/Wait probabilities do change.

Measured additional limitations: weak return prediction;512-step windows yield about32% native-terminal return coverage in the prior cold run;1024 increases coverage but failed score improvement. Diagnostic states average358 legal roads and inherited road preferences are often sharp; this suggests limited exploration, not proof that exploration alone blocks learning. Recent32k trials contain only42–45 completed cities,so decision counts are not independent strategy examples; unsuccessful short runs do not prove a longer run cannot learn. Missing deletion,motorways,signals,roundabouts and learned weekly choices limit eventual capability but are not established causes of this plateau.

Proposed next experiment, not implemented or launched by this explanation: retain reference checkpoint; test a zero-initialized trainable correction active throughout the city (including opening), against current gated correction. First test ability to improve native delivery score on a small repeated set of4–8 real training cities,with different action RNG and untouched evaluation cities. No planner,teacher actions or shaped construction reward. Fixed training cities are a fitting diagnostic,not evidence of generalization. If even this cannot improve,investigate return targets/representation and exploration before more diverse training. If it fits but fails held-out cities,focus on diversity/generalization. Evaluate opening skills as a regression check instead of making all early decisions permanently untrainable. Require repeatability across training RNG seeds and fresh full-city validation before long launch. No certainty claimed and no new training started.


### 2026-11-24 — user-authorized whole-city fitting diagnostic

User authorized watching play,teaching through PPO,monitoring training,and reporting findings. Preserve Maskable-PPO reference/checkpoints and Desktop/main. No planner,teacher labels,new reward or physics change.

Predeclared comparison: gated versus whole-city correction,both initialized from identical zero-residual wide checkpoint. Original ratesLR.0001,value coefficient1e-5,16workers,512steps,4rollouts=32,768 decisions each,4epochs,batch128,GAE1/gamma1,600s native horizon,bridge actions. Eight repeated training seeds184000000..184000007;each worker cycles all eight on episode resets. This is a fitting diagnostic,not generalization evidence. Two sampled action RNG replicates per city for frozen review; eight separate185000000..185000007 cities evaluate transfer. Baseline suite fixed before results. Never mix held-out seeds into training.

Current experiment removes only the correction gate; inherited actor remains the starting prior. Zero outputs preserve initial behavior. The shared correction can adapt road/Wait choices throughout the game; no phase-specific teacher policy. Compare equal-budget arms rather than attributing any improvement to gate removal without a control. No long run authorized by fitting performance alone.

Watch recorded trajectories and produce replay artifacts before/after. Assess native score,first delivery,stock at new-target arrival,service to new targets,and visible unproductive construction. Keep negative findings. Report finite-horizon and eight-city limitations; two action replicates do not create16 independent cities.

Whole-city preparation passes256 exact actor/value state comparisons and exact initial weights. On a pre-established state,actor correction gradient L1 is0 for gated control and2.86916 for whole-city version; save/load and repeated8-city reset cycle/explicit reset bypass pass. Three existing wide/opening/reporting tests pass. Both bounded32k arms launched under controller396475 with frozen source/host. Recorded seed99020130 was visually inspected:all25 starting roads spent by60s on disconnected branches/loops; no score at120s,cars moving only near144.95s death. This is an observed example,not the only failure mode. Figure source cross-links prior bridge-zero-city-traffic.json. System Python renders figures because project venv lacks matplotlib; no package/environment change.

Fresh frozen reference watch on preselected training seed184000000/action193251 exactly reproduces baseline trace. Visually: by62s starting25roads are exhausted in branches and a loop while the red destination remains disconnected; by124s score remains0; by151.2s gameover,cars moving after late connection,score0. This reproduces the earlier failure pattern on a different native layout. Fixed-seed replay retained as HTML,raw frames,actions and rendered panels. Baseline600s averages126.25 on8 repeated cities×2 action RNGs and125.9375 on8 untouched cities×2 RNGs;15/16 scoring each. These are600s numbers and must not be compared to previous1200s means. A second anchor seed184000003/action193254 is selected now,before candidate results,for a successful-game comparison.

Second preselected reference replay184000003/action193254 reaches158 at600s,first delivery13s,first zero road stock240s. It uses115 paid units;51 lie outside routes observed assigned during this replay (not proof those units can never be useful). Visual review shows a successful initial connection followed by substantial loops/branches as new destinations arrive. Contrasting failed anchor184000000 first exhausts roads at26s,well before any delivery,ends0 at151.15s. Both anchors are fixed before trained candidate results. HTML playback,actions,raw frame data,render source and figures retained.


Engineering finding during observation:65 completed control episodes include35 reaching the600s time limit. Existing CityRoadEnv correctly marks these as truncations for a continuing-game objective; installed MaskablePPO adds gamma*V(terminal_observation) to the last training reward. Thus the repeated-city test is not a pure finite600s-return fitting test,even though native reward/Monitor scores remain unmodified. Both active arms use identical semantics,so their gate comparison remains valid; failure to improve cannot by itself establish inability to fit exact600s returns.

Prepare optional --finite-city-horizon restricted to repeated-city diagnostics. It converts only a surviving600s cutoff to a terminal learning boundary,with explicit native_game_over/finite_horizon_end metadata. Native simulation,rewards,observations and actions stay unchanged. This intentionally changes the diagnostic objective to deliveries within600s; it is not automatically a production policy or a fix proven to improve lifelong score. Active frozen runtimes remain unchanged. Conditional third bounded32k trial from same whole-city initialization if gate-only comparison does not clearly improve repeated-city score: same settings,seeds,budget; change only finite cutoff semantics. Evaluate same paired suites and preselected replay anchors. Do not infer transfer from fitting alone.

Control completes32,768 decisions and1024/1024 updates,65 completed games. Whole-city first8,192 rollout completes256/256 updates; its8 completed pre-update episodes exactly match control apart from wall time. Gradient checks remain finite with actor gradients present. Finite-horizon optional check replays729 native actions to600s:all masks,observations,rewards and entire final native world exactly equal;only final training termination flags change,score158. No active runtime modified. Conditional finite trial trigger fixed before candidate results:whole-city repeated-score improvement less than10% versus baseline or paired city-bootstrap lower interval<=0. This is a fitting diagnostic trigger,not a relaxed long-launch gate.

Whole-city midpoint16,384 replay on the preselected failed anchor184000000/action193251 scores123 versus reference0;first delivery34s,native death532.1s versus151.15s. Visual inspection confirms earlier usable service connection,though inventory still depletes and later isolated destinations remain. One stochastic trajectory is not general strategy evidence. Because this checkpoint changed the anchor meaningfully,add a full32-game midpoint validation on the already declared repeated/separate suites;selection driven by the anchor is explicit. These separate cities remain excluded from training but are validation/selection data,not fresh confirmation. No overnight implication.

Both bounded arms complete32,768 decisions and1024 optimizer steps. Post-training structural audit:82 allowed tensors changed per arm,inherited prior weights unchanged and finite. Gated control is exactly unchanged on16 initial-state action distributions;whole-city correction changes mean initial distribution TV0.016868. Most measured initial-state change is Wait probability (mean−0.016868);conditional-road TV averages0.000370. Thus do not describe the successful anchor as proof of newly learned route planning. Full midpoint validation:repeated mean119.0 versus126.25,delta−7.25,city-cluster95% interval[−33.8125,18.5625];separate mean95.0 versus125.9375,delta−30.9375 [−69.315625,5.4375],14/16 scoring versus15. The single positive replay does not generalize across this suite. Final validation pending. Added32 fresh action-RNG opening trials on anchor184000000 at180s for reference/midpoint/final;this tests one-layout reliability only,not fresh-city transfer.

Matched final results: gated repeated101.875 vs126.25 (delta−24.375,95%[−47.5015625,−1.684375]),separate115.375 vs125.9375 (delta−10.5625,[−35.0625,20.8765625]);whole repeated129.5 (delta3.25,[−26.1875,26.0]),separate133.75 (delta7.8125,[−26.5015625,44.0640625]). Whole scoring15/16 repeated,14/16 separate versus baseline15/16 each;stockouts32/31 versus24/20. No promotion. Final preselected replays0→175 (first delivery32s) and158→172 (first delivery13s). But fresh32 action-RNG opening trials on the first anchor give27/32 reference,28/32 midpoint,27/32 final;mean180s scores13.25,13.40625,13.3125. The favorable selected trajectory does not establish improved reliability. Both trainers/reviewers and opening probe finished. Conditional finite-horizon trial triggers because repeated gain is below10% and interval crosses0. Launch only the declared32k diagnostic; no long session.

Whole-minus-gated comparison:repeated paired+27.625,95%[4.6875,52.6875];separate+18.375,[−17.7515625,54.2515625]. This supports removing the restriction relative to restricted training in this run,but does not establish improvement over reference or repeatability across training RNG seeds. First-divergence audit on anchor:decision7,time4s,reference/action3082 versus candidate3252;Wait probability0.36004→0.32022,conditional-road TV0.001812. Counterfactual probabilities with only Wait changed reproduce candidate action3252;only road preferences changed reproduce reference3082. Therefore the dramatic selected replay is not proof of learned superior routing. Evidence/limits stored in first-divergence.json. Comparison HTML control logic tested via Node REPL VM with stub DOM/canvas (no browser rendering claim);four final displayed scores match recorded replays.


### 2026-11-24 — whole-city observation/training result

All three32,768-decision trials complete,98,304 total decisions,3,072 actual Adam updates,195 completed episodes. Finite final SHAe3750c9cad7e51d6bc2b395d5444fa92c61206c0030895071b16e09159b30f6a. Finite repeated mean121.5 versus126.25,delta−4.75,95%[−21.3125,7.625];separate mean116.4375 versus125.9375,delta−9.5,[−41.5625,28.125]. Scoring15/16 repeated,14/16 separate;stockouts32/35 versus24/20. Finite native replay anchors score20(first delivery34s,death223.65s) and168(first delivery13s,survives600s). Optional finite objective did not establish improvement. Post-training audit:82 permitted tensors changed,opening meanTV0.015835,1024 optimizer steps,protected prior unchanged. No global promotion/no long launch.

Complete findings,run/checkpoint records,paired evaluations and scope are in docs/training/city-whole-policy-2026-11-24/RESULTS.md and results.json. Interactive comparison includes reference,whole-city final and finite final on both preselected anchors. Seven newly recorded replays were preserved (including midpoint). Display labels corrected to Frame because waits are sampled between build frames;complete action traces remain available. Six selector/timeline combinations checked via JavaScript VM;native figures visually inspected. No browser rendering claim.

Conclusion: opening correction restriction was removed and its learning path verified. Whole correction beats gated control on repeated cities in this one training run,but not reliably the reference. The selected0→175 replay does not show a reliable opening repair:27/32 opening success before and after across new action RNGs. Most inspected initial-state change is Wait rather than conditional-road preferences. Investigate road-choice plasticity/exploration next;this is a lead,not proven sole cause. Limited32k budgets/eight layouts/one training RNG cannot establish that longer training would never work. All jobs stopped normally;no further training queued. Preserve baseline and all candidates.

Final verification:three wide/opening/reporting tests pass after all optional changes;no experiment trainer/evaluator/native-host processes remain;reference SHA unchanged. Finite trial first8 pre-update episodes match whole-city control on every native episode field,excluding wall time and deliberately changed termination metadata. Final replay controls pass six city/policy combinations;sampled snapshots labeled Frame. All final measurements,render source,figures,replays and local-only artifact hashes archived.


## 2026-11-24 — Road-choice-only diagnostic authorized

User approved the proposed road-choice-only PPO test. Same whole-city zero-residual initialization, eight repeated cities and 32,768-decision budget as the prior joint run; freeze Wait corrections, preserve road/spatial/critic learning and native rewards. No planner or imitation. New three-group optimizer avoids counting a frozen Wait parameter as an Adam update. A zero visual Wait final layer is required because its shared encoder still learns. Preparation checks and paired evaluation are required before drawing conclusions. Existing files and checkpoints preserved. Plan: `docs/training/city-road-choice-2026-11-24/PLAN.md`. No long run launched.

Preparation harness correction: the disposable gradient check called masked_probs after obtaining SB3's mutable distribution, replacing it with a no-grad distribution. Reordered the probe to obtain the differentiable distribution last. This was a check bug, before training; the saved zero-step initialization is unchanged. Revalidate it rather than overwrite it.

Launch correction: resolving the virtualenv Python symlink selected /usr/bin/python3.12, which lacks torch. The first launch failed before any training or environment creation. Its output remains in city-road-choice-fit-01. Relaunch uses the absolute virtualenv path without resolving symlinks, in city-road-choice-fit-02. No model progress was lost.


## 2026-11-24 — Road-choice-only diagnostic completed

Measured: 32,768 decisions, 1,024 actual Adam updates, 64 episodes (36 time limits/28 native ends), 450.47 training seconds. First eight pre-update games match prior joint run. Frozen Wait tensors and inherited prior preserved; maximum shared-state Wait probability error7.75e-7 over94 states. Conditional-road TV0.002140 versus joint0.000702; this is probability movement, not proof of better choices. Repeated mean128.8125 versus reference126.25 (paired95%CI delta[-11.0641,18.3125]); separate122.25 versus125.9375 ([-51.5031,46.4375]). Scoring14/16 repeated and16/16 separate, versus15/16 each. Single-layout32-RNG opening scores26/32 versus27/32 reference. Watched anchors score0 and147 versus0 and158 reference; the latter dies with18roads and an unserved later destination, whose arrival stock was zero. These remain development results with one training RNG.

Engineering decision: reject promotion and joint/long continuation; preserve all checkpoints. Hypothesis for next work: test larger road-head updates under unchanged Wait, spatial/critic settings, native rewards and PPO KL guard; this is not yet implemented or launched. Reports, graphs, replays, source snapshots and small evidence in `docs/training/city-road-choice-2026-11-24/RESULTS.md`; no weights/binaries in archive. Earlier preparation and launch failures are recorded above and occurred before training. All experiment jobs completed.

## 2026-11-24 — Small-city useful-construction experiment authorized

User highlighted messy overbuilding and approved small, varied cities with tight stock and a later second pair. New native fixtures have no prepared roads, hints or reference edits; unlike earlier reserve lessons they require the first connection from scratch. Native completed deliveries remain the sole reward. Engineering choices and fixed evaluation gates are recorded in `docs/training/small-city-service-2026-11-24/PLAN.md`. Planned bounded32,768-decision joint road/Wait PPO trial from preserved whole-city initialization; no planner, imitation, inherited-prior unfreezing or long session. Checks and measurements pending.

Small-city baseline ceiling finding: original parent serves first and later pair64/64 across train/validation positions and two RNGs; single-pair64/64. This invalidates the planned +10pp improvement gate for this easy fixture. Stopped easy training after preserving8192-decision/256-update checkpoint; no claim that incomplete next rollout is saved. Parent baseline measured concurrently with initial training. Next screen offset geometry before another training launch. No larger-city strategy gain inferred.

Offset fixture baseline establishes a learning gap: validation first-pair20/32 and both-pair9/32, compared to32/32 both on easy geometry; mean14.125 paid units,8.34375 outside observed routes. Train-position both8/32. Native controls128/128 and104 regression suites pass; ordinary160transitions exact. Launched declared32,768-decision offset PPO trial, LR.0003, from original whole-city init. All earlier checkpoints remain preserved; no long run.


## 2026-11-24 — Small-city experiment completed; overbuilding not fixed

Measured: easy baseline serves both pairs64/64 and singles64/64, prompting intentional stop of the first pilot after preserving8192decisions/256updates/212episodes at118.16s. Its incomplete second rollout is not claimed as saved progress;302episodes total remain in its log. SIGINT did not end the detached trainer; the owned process group was terminated, with launcher error preserved as the intentional-stop record.

Offset pilot completed32768decisions,1024actualupdates,882episodes,534.98s from the original whole-city initialization. Separate-layout first service20/32→17/32, both9/32→9/32, score2.8125→2.46875 and outside-observed-route units8.34375→9.25. All practice gates fail. Native-score PPO changed only allowed road/Wait/spatial/critic tensors; shared-state conditional-road TV≈0.001986. No planner, imitation, extra reward or inherited-prior update. Existing parent and all saves retained.

Development-city means126.09375→143.0625 (both30/32scoring) motivated a frozen, predeclared fresh confirmation on cities196000000–196000031/actionRNG244001–244032. Fresh means121.53125→123.53125, both29/32scoring; paired delta+2,95%CI[-16.84375,20.71875],14wins/3ties/15losses. The development gain is not reliably confirmed. Fresh zero-stock target arrivals25→38. This does not establish cleaner networks, road conservation or high-score readiness.

Checks: two native builds each104existing suites; easy/offset each128fixture controls and160ordinary-city parity transitions;560easy-fixture transitions preserved across new hosts;8compression controls;2focused final Python tests;4replays exactly match evaluation. Native design rationale in simulation/Docs/DESIGN_DECISIONS.md. Full results, graphs, traces, source snapshots, small measurements and local-only artifact hashes: docs/training/small-city-service-2026-11-24/RESULTS.md. No weights/binaries copied into docs.

Decision: reject promotion and long continuation. Next hypothesis, not implemented/launched: isolate a single longer offset connection with tight versus generous stock before restoring the second arrival, to distinguish geometry from resource/context effects. One training RNG and finite two-pair tasks limit conclusions; cosmetic surplus roads after final service may have no native score cost. All jobs ended.

## 2026-11-24 — User-authorized reward experiment

User suggested changing reward to discourage messy construction and approved “Try”. For this bounded test only, road-spending penalties are now explicitly authorized; previous native-only restrictions remain historical. Plan: single longer offset pair, tight/generous stock, matched cost0/.01/.04 PPO arms,16,384decisions each. Native delivery score remains separate from shaped reward. Analytic maximum18units bounds successful return≥.28 under strongest cost, versus failure≤0, avoiding a reward incentive for permanent Wait. No planner, imitation, terminal bonus or native city reward change. Original parent and all old checkpoints retained. See `docs/training/road-cost-reward-2026-11-24/PLAN.md`.

User correction: “I think youre judging too fast, training needs so much time.” Agreed:16,384decisions per arm is an initial pilot, not adequate evidence of convergence or grounds to reject the reward approach. Short-pilot promotion gates were not met, but effectiveness remains inconclusive. Preserve checkpoints/Adam for a longer matched control/.04 comparison; judge learning curves at equal budgets. Proposed100k or250k cumulative decisions per arm; no extended training has started and no duration was selected. This supersedes any impression that the short negative result disproves road penalties.


## 2026-11-24 — Road-cost pilot recorded as inconclusive

Three arms each16,384decisions/512Adam updates/434episodes (49,152total decisions,1,536updates,1,302episodes). Training seconds247.53/246.49/246.54. Cost0/.01/.04 generous successes44/44/45 of64 versus parent46; tight33/33/33 versus parent32. Paid units identical7.046875tight/10.359375generous. Strong versus control outside-route difference−.15625,paired95%CI[-.671875,.28125]; native score+.046875[-.09375,.1875]. No zero-build episodes. Strong/common-success outside units1.35 equal control on40cases. No short-pilot promotion gate passes, but user timing correction supersedes treating this as rejection of the reward hypothesis. No convergence/plateau demonstrated.

Reward validation:104native suites,192controls,304cross-cost native transitions,308old-fixture transitions,220identical pre-update native episode records across all arms, all penalized/native ledgers,2focused Python tests,8exact replay/evaluation matches. Penalties changed allowed weights but mean opening-distribution TV versus control only.00003374/.00013039. Checkpoints and Adam preserved; all jobs ended. Next proposed longer control/.04comparison with learning curves; no duration chosen or extended training started. Full evidence and graph: docs/training/road-cost-reward-2026-11-24/RESULTS.md.


## 24 November 2026 — PPO research and reassessment

User requested primary-source game-RL research after challenging early conclusions. Reviewed PPO, OpenAI Five, implementation studies, masking, generalization, statistical evaluation and shaping alongside current code and archived results. See [full review](../docs/training/ppo-research-review-2026-11-24/REPORT.md). Confirmed genuine earlier overnight learning (reserved32.19→95.44), later long-run regression, and inconclusive16k reward trials. Identified joint-action entropy pressure toward the road branch algebraically; causal importance is unmeasured. Frozen prior, relative update rates and tiny value weight remain audit targets, not proven root causes. Proposed matched continuation to262144decisions/arm with preserved Adam, curves, separate ablations and later city transfer; no execution or policy change. BranchMaskable-PPO, HEAD6bd7f71 plus preserved local work; SB3/contrib2.9.2, Gymnasium1.4.0. No matching training/host process found. Source hashes and report archived.


## 25 November 2026 — authorized research follow-through and continuation preparation

User approved working on the research recommendations. Frozen16-game diagnostics per arm find poor critic calibration (EVabout−10), but entropy road-gradient norm only0.57–0.61%of reward-gradient norm; no causal dominance established. Post-service sampled build probability~0.099%with builds legal. Keep recipe unchanged for matched continuation, instrument actual updates, preserve old checkpoints/Adam. [Plan, scope and evidence](../docs/training/road-cost-continuation-2026-11-24/PLAN.md). New continuation/controller/diagnostic/report scripts; disposable resume checks precede launch. No planner/imitation/simulator or reward changes.


## 25 November 2026 — matched comparison launched

Two disposable smoke continuations passed:512→768→1024Adamsteps, both8192decisions; reload and finite moments verified, all four trainable parameter groups changed. They are excluded from the experiment. Launched control/.04original saves toward262144cumulative decisions/arm; PID493685. New seed stream208000000, explicit RNG241124, original recipe unchanged. [Launch, scope and live status](../docs/training/road-cost-continuation-2026-11-24/README.md). Logs/checkpoints local; measurements and six evaluations automatically archived. No claim of improvement yet; no automatic promotion or extension.

First production continuation rollout verified: control cumulative24576decisions,225completed episodes,768Adamsteps,132.12seconds. Checkpoint hash verified and all four trainable groups changed; original prior equality/finite checks passed in trainer. Last100training episodes native mean1.99,success56%,paid8.36; early training metrics are not an evaluation or improvement claim. Both-arm comparison remains running.


## 25 November 2026 — overnight follow-up authorized

User requested a check after half an hour and further justified training while asleep, with research as needed. Keep follow-up in this active chat rather than creating a recurring automation for a specific running job. First check target about02:29Asia/Beirut (00:29UTC),30minutes after01:59local inspection. Existing comparison was on strong arm at212992/262144; no interruption. Authorization permits bounded further experiments, not a guaranteed score increase. Preserve all checkpoints, evaluate actual native performance, document research/changes and report morning outcomes honestly.


## 25 November 2026 — matched road-cost continuation completed

Both arms reached262144cumulative decisions; six128-game development evaluations completed. [Archived results](../docs/training/road-cost-continuation-2026-11-24/RESULTS.md). One training seed, no automatic promotion or city-transfer claim. Review curves and paired intervals before choosing further training.


## 25 November 2026 — completed comparison reviewed during overnight follow-up

Longer .04practice training improves generous-stock development success55/64versus46/64control and native score2.875versus2.484; paired score interval[+.031,+.766]. Outside-observed-route construction falls, while total spending rises slightly: better connection placement, not proven conservation. Tight-stock change remains uncertain. Strong/initial native city prechecks and frozen critic diagnostic started read-only. [Record and provisional next-stage rationale](../docs/training/overnight-learning-2026-11-25/FOLLOWUP.md). No new training launched yet; requested02:29follow-up remains pending.


## 25 November 2026 — practice-to-city regression changes overnight plan

Native development prechecks: original126.09/30scoring of32; stronger practice candidate86.97/27of32. Preserve original and do not promote. Prepared critic-rate ablation is deferred without execution. Next bounded comparison: same strong262144parent, lesson-only versus8city+4tight+4generous workers, unchanged optimizer/architecture; practice cost.04only, native city reward. [Decision, evidence and limitations](../docs/training/overnight-learning-2026-11-25/FOLLOWUP.md). Transition-parity checks started; no next-stage training launched yet.

Mixed-city wrapper passed497exact shared transitions across six games against existing native/cost environments; finite reward ledgers and episode endings match. Prepared reporting self-check passed. Original-to-practice-final city delta−39.125,paired95%interval[-63.94,-11.50]on consumed development layouts. New source remains unlaunched until the requested follow-up and smoke.


## 25 November 2026 — requested half-hour follow-up performed02:29:30Beirut

Previous comparison complete, no remaining learner/host processes. All561paired mixed-wrapper transitions across six games match existing environments (observations,masks,rewards,termination); summary identity checks pass. Started disposable8192-decision mixed-worker resume smoke on213Mfromstrong262144checkpoint. After a successful smoke, launch the predeclared lesson-only/mixed-city comparison. No additional user click required. [Record](../docs/training/overnight-learning-2026-11-25/half-hour-check.json).

Count correction: the02:29entry manually said561transitions; the machine record and earlier computed entry correctly contain497paired transitions. The parity result is unchanged.

Mixed smoke01caught missing stock_initial in native city Monitor reporting; worker failure stalled collection before any saved PPO update. Original model untouched. Stopped only owned smoke process tree and retained partial logs. Added consistent native reset-stock field and controller no-progress watchdog. Smoke02started from the original parent on a fresh213100000seed stream; not an experiment arm.


## 25 November 2026 — overnight transfer comparison launched

Corrected mixed smoke02passed8192decisions,133episodes,181.72seconds; optimizer8192→8448restored on reload, finite weights, all task reward ledgers correct, original parent unchanged. Native city reward remains score-only. Smoke checkpoints excluded. Launched matched lesson-only/mixed-city branches from original strong262144save toward524288each, PID551324. Fresh210Mtraining stream, RNG251125. Controller snapshots code/host, saves every rollout, evaluates fixed practice checkpoints and final city performance, archives results and stops. Verified precheck results are reused. Expected roughly3hours including evaluation, not a score guarantee. [Commands, decisions, checks and live status](../docs/training/overnight-learning-2026-11-25/README.md).


## 25 November 2026 — overnight task-mix comparison completed

Both branches completed262144additional decisions, reaching524288cumulative from the same saved policy. The planned intervention was adding native city workers; critic and actor settings were unchanged. Four practice and four32-game city development evaluations completed. [Results](../docs/training/overnight-learning-2026-11-25/RESULTS.md). No automatic promotion or further run; independent replication/confirmation remain open.


## 25 November 2026 — morning results verified and assessed

On user status request, verified complete status05:26:22Beirut, both524288-decision endpoints, archive manifest (276files) and protected parent/original hashes. No matching learner/native-host processes remain. City means126.09original,86.97parent,107.44lesson-only,99.16mixed; both new candidates30/32scoring. Paired gains versus parent remain uncertain, and neither shows superiority to original. Mixed final practice generous success71.9%versus85.9%at parent; lesson-only84.4%. More practice learned useful task behavior earlier, but integrated city improvement remains unproven. No promotion or new launch. Current status/indexes updated; historical report preserved.


## 25 November 2026 — authorized matched replay/reward diagnosis and next experiment

User said“Go ahead do sll”after agreeing to research-grounded diagnosis then targeted training. Twelve exact native replay matches show opening failures plus rapid post-award stock exhaustion/later-service losses. Reward equals native trip increments; no duplicate-delivery reward bug found. Preserve native deliveries, not a first-connection-only reward. Retain original stronger city model as common start. Added expansion-balanced worker assignment using existing native single/two-arrival fixtures. First8192-decision smoke passed but exposed large cross-task advantage offsets; enable existing task-homogeneous minibatches for the curriculum arm, explicitly a recipe comparison versus city-only. Second smoke and buffer tests in progress; no long launch yet. [Diagnosis, primary-source rationale, images and plan](../docs/training/city-transfer-diagnosis-2026-11-25/README.md).

Expansion preflight complete: four task-buffer/reporting tests pass; two8192-decision smokes pass256Adamupdates and reload checks; frozen inherited prior unchanged. Task-normalized smoke exercises all three task groups, with32city/16single/16two-arrival updates in its first audited epoch. Synthetic identical-input report checks pass. Native baseline practice on216M:single32/64,first pair39/64,both pairs20/64; these are now development records. Ready for the authorized bounded city-only versus curriculum recipe comparison.


## 25 November 2026 — authorized expansion comparison launched

Launched PID708157 from the exact retained original, not either smoke or weaker recent candidate. Both arms add262144decisions; city-only is the control, curriculum adds single/timed-pair exercises with within-task advantage normalization. Common native score rewards, parent sampling seed11424, training215M. Save every rollout; fixed65k/131k/262kpractice and city reviews, one evaluation queue, source/host snapshots and no-progress watchdog. No automatic promotion/extension. [Launch command and evidence](../docs/training/city-transfer-diagnosis-2026-11-25/launch.json). Expected roughly2.5–3hours, not a guaranteed score increase.


### 2026-11-25 — Deadline readiness interim assessment

User asked for a candid assessment as the deadline approaches. Read-only check: expansion comparison controller PID 708157 remains active, expansion branch at 212,992/262,144 added decisions; city-only branch completed. Completed development city evaluations (name, mean trips, scoring games out of 32): [('city-city-only-131072', 116.5625, 29), ('city-city-only-262144', 88.5625, 27), ('city-city-only-65536', 137.03125, 30), ('city-expansion-131072', 126.46875, 31), ('city-expansion-65536', 116.03125, 28), ('city-initial', 126.09375, 30)]. These reused development games do not establish fresh-city generalization or a statistically reliable gain. Engineering assessment: useful learned connection/service behavior exists, but opening failures and premature inventory spending remain documented; leaderboard readiness is unproven. Recommendation: complete the existing bounded comparison, preserve the strongest verified checkpoint, confirm the selected candidate on untouched cities, and prioritize reliable delivery over further broad redesign near deadline. No new training launched or existing run interrupted. Evidence: docs/training/city-transfer-diagnosis-2026-11-25/evaluation and DIAGNOSIS.md. Final expansion evaluation still pending.


### 2026-11-25 — Midnight training deadline and remaining failures

User decision: training should start by midnight today (Asia/Beirut). Current bounded comparison remains active; latest observed expansion progress 229,376/262,144 decisions, final evaluation pending. Diagnosis remains unreliable opening completion, rapid road depletion after awards and inadequate later-demand service; prior newer policies regress relative to retained original despite practice gains. These are observed behavior and transfer failures, not proof of a specific optimizer defect. Reward accounting passed 12 matched replays; congestion-aware strategy and leaderboard readiness remain unproven. Recommended pre-midnight priority is finish the current comparison and confirm candidate city performance before selecting the overnight checkpoint/configuration. No new run or automatic midnight schedule was created by this status response. See docs/training/city-transfer-diagnosis-2026-11-25/DIAGNOSIS.md and evaluation/.


## 25 November 2026 — expansion curriculum comparison completed

Both native-score branches added262144decisions from the preserved original policy. Fixed65k/131k/262kpractice and city evaluations completed. [Archived results](../docs/training/city-transfer-diagnosis-2026-11-25/RESULTS.md). No automatic promotion or further training; inspect uncertainty and transfer before deciding the next step.


## 25 November 2026 — approved mini-task audit and repair

User approved flexible-duration audit, task repair, bounded comparison, fresh-city confirmation and conditional pre-midnight long-run launch. Completed prior comparison did not beat original; no promotion. Began current-policy behavioral audit of seven mini-task families,16fresh seeds/model, original versus final expansion; no reference actions or policy changes. Historical five-stage automatic-Finish/imitation results are scoped separately. See ../docs/training/mini-task-repair-2026-11-25/README.md.


### Mini-task audit findings and reset-state curriculum decision
224frozen games: short gap/bend/clear16/16each, tight offset8/16each, later pair3/16each. Tight successes7/7within existing6cell opening gate,1/9outside. Preserve this gate; do not add route heuristics. Implement opt-in self-generated initial-state curriculum, not imitation: exact own successful prefixes only during reset, subsequent rewards only, half lessons still empty. Bank collection and tests underway; no PPO run yet. Sources and limits: docs/training/mini-task-repair-2026-11-25/README.md.


### 25November2026 — mini-task reset comparison launched
80own-policy reset states pass4488exact continuation transitions, reward exclusion and forced-Wait checks. Selected-bank baseline21/36long completion and94/124later service; these are training-bank checks, not generalization.8192-decision smoke passed finite/reload/prior-retention checks;273episodes/256updates/195.38seconds, excluded from production. Launched matched reset/cold comparison,262144decisions each, from retained original, PID776266. Four lesson workers change reset distribution; native reward, model and optimizer unchanged. Fixed checkpoint city/empty-board reviews; no automatic promotion or overnight continuation. Archive: docs/training/mini-task-repair-2026-11-25/.


### Additional frozen city/traffic audit during mini-task comparison
16long-city diagnostic games (8seeds238000000–007,2actiondraws,1800smax): mean234,median233,best967,3zeros,9survive600s,all16nativegameover before1800. Not comparable to600scaps. Traffic urgency swaps leavefirstchoiceunchanged on8pairedlayouts; urgentservice3/8and5/8. Both low/high junctions alwayschoosebypass; native controls show feederbetterlowload, bypassbetterhighload. Fixed misleading junction success metric (already-served destinations made new_deliveries alwayszero); future reports null+pairedscore guidance, historicalraw preserved. New checks and sources in docs/training/mini-task-repair-2026-11-25/. No policy/reward change or interruption to frozen-runtime comparison.


### Action-interface scope and traffic reporting validation
Current CityRoadEnv exposes connections/Wait, with bridges enabled in city runs; weekly package still selected by max-road rule, not learner. No direct demolition/rotation/motorway/roundabout/light actions in this actor.15/16long diagnostic games use bridge tiles, not proof of bridge strategy.9native control checks validate null congestion-success counts and unchanged priority metric; production runtime unchanged. Scope recorded in mini-task-repair archive.


### Long-game fallback comparison and failure classification
Matched16long games: prior65kcity-only candidate mean231.625 versus original234; no demonstrated gain, original retained. Three original replays exact: worst never connects, typical ends with unserved later destination/zero stock, best967servedall14destinations but dies under demand pressure with7roads left. Connectivity alone insufficient; longtrip/queue/capacity causes not isolated. Evidence: mini-task-repair archive long-city-comparison.json, long-replays/, long-replay-findings.json. Current bounded reset comparison continues unchanged.


### Optional frozen-computation cache prepared, default off
Removed duplicate computation only when explicit runtime flag enabled. CPU exact output/gradient and post-update parity passed on11observations, cache scoped per-call, protected checkpoint unchanged. CPU batch1/16 benchmarks improve, but GPU/end-to-end benefit unverified; do not apply to current frozen comparison. Full source/test/timings in mini-task-repair archive.


### First65kevaluation packaging failure, training preserved
Missing replay HTML in frozen Python-only snapshot caused behavioral evaluation failure. Added missing resource; failed outputs/log preserved, samecheckpoint/seeds evaluation rerun. Training uninterrupted; no reset or lost updates. Launcher fixed forfuturejobs. Running controller retains failed Future and requires explicit recovered finalization after all arms/evaluations; do not launchduplicate training. Details: mini-task-repair/evaluation-recovery.json. Prefix-only65kcheck24/36single vs21/36,93/124later vs94/124; no transferclaim.


### Mini-task horizon diagnosis and optional300-second lesson repair
64frozen continuation games verify first60-second accounting exactly. Original first-onlytwo-pair cases5/5eventuallyfail (mean3.4at60,10.8final); both-served3/3survive300(mean5.67at60,37.33final). Thus60scutoff weakens future-service reward separation and hides nativefailures. Added default-preserving optionalsmall_city_horizon (60..600) to small-city environment/trainer/evaluator; preparing300s withnative reward only, no roadmap/teacher/penalty. Exactreset/defaultparity tests underway, no300sPPO yet. Existingcomparisonunmodified. Fullmeasurements in mini-task-repair/horizon-diagnostic/.


### Longer-window validation and reset-comparison midpoint

All 80 recorded starts passed 13,801 exact native transitions at the 300-second deadline, including reward-prefix exclusion and forced-Wait parity. The default 60-second implementation matched 120 transitions across 15 task families. A disposable 2,048-decision PPO smoke using the optional frozen-computation cache completed 64 Adam updates and 52 lesson episodes; checkpoint reload, finite tensors, unchanged inherited prior and native reward accounting passed. Runtime 97.24 seconds under concurrent production training is not a matched speed comparison. No city episode finished in this short smoke. Smoke weights remain local and are excluded from production.

The 14-game evaluator check exercised both legacy 60-second geometry tasks and 300-second small-city tasks. Added explicit first/both-destination service, native game-over and elapsed-time reporting so a first-only pair is not counted as solving the whole task. First-delivery timing fields are prepared for future reports. The production reset comparison remains frozen at 60 seconds.

Prepared (not launched) a duration comparison runner and summarizer: same recorded-start curriculum and parent/Adam on both sides, only 60 versus 300-second small-city training duration differs; both evaluated at 300 seconds and on the same 600-second cities. The optional cache is used in both arms. Parent choice and budget must be recorded before launch after review of the current comparison. This preparation does not establish readiness or authorize automatic promotion.

Midpoint reset evaluation: city mean 100.0625 with 28/32 scoring, compared with original 126.09375 and 30/32. Tight single 7/16; later pair 2/16; generous single 10/16; adjacent/bend/clear 16/16, obstacle 15/16. No transfer improvement yet. Continue the declared budget/control comparison, retaining all checkpoints.

Evidence: [archive](../docs/training/mini-task-repair-2026-11-25/README.md).


### Longer native lessons comparison launched
Frozen128-game value-calibration diagnostic confirms poor short-lesson critic calibration and stronger native reward separation at300seconds for the original policy. This supports a separate bounded60/300-second comparison from retained original,262144decisions/arm, same native reward/reset curriculum/optimizer. Current reset study continues unchanged. Both arms use validated frozen-growth cache. Parent fixed before inspecting later reset results; no checkpoint promotion or overnight launch. [Design and monitor](../docs/training/mini-task-horizon-2026-11-25/README.md). ControllerPID807935.


### Duration-study evaluation memory bound
Concurrenttraining+baseline evaluation left3.4GiB availableRAM. Future duration-study evaluator processes limitedto2CPUworkers, same game data/inference; initial source andhashes preserved. Existingtrainingandresetstudyuntouched. Evidence:mini-task-horizon/evaluation-resource-limit.json.


## Optional small-city terminal-tail acceleration
Prepared default-off --fast-small-city-tail for future runs. Only after stock is exhausted, no legal connection remains, and all fixture spawn opportunities have passed (single fixtures have none; pair fixture sole attempt is bysecond30), run the same native ticks in one host call. Keep ordinary per-second checking before that point, so later parcels can restore legal choices. No policy action is skipped and no planner is used. Guard unchanged stock/building IDs and native reward accounting. Terminal motion history differs, but these finite lessons terminate without bootstrap; next reset must match.

88paired games across five small-city families,60/300deadlines and48recorded-prefix cases passed4,267exact decision transitions: native state/reward/flags/info/masks identical, all nonterminal and next-reset observations identical. Measured environment-step speedup1.63x under concurrent training, excluding inference/optimizer; not an end-to-end training claim. Default behavior also matches240native transitions across15families and both horizons. Invalid flag combination rejected before creating a host. Neither active study uses this optimization; no learner interrupted or restarted. Source preserved under tail-prototype-source.

Evidence: [native parity](../docs/training/mini-task-repair-2026-11-25/small-tail-check/summary.json).


### Terminal-tail PPO integration check
The first disposable harness exited before learning because the original checkpoint has no episode-statistics deque yet; an unconditional `.clear()` raised AttributeError. Both native environments closed in finally; no training/checkpoint was produced. Preserved its log/output. Corrected the harness to use the same None guard already present in the production trainer, then reran into mini-fast-tail-smoke-02.128decisions,4Adamupdates,11completedlessons,11.01seconds; native reward ledger, no terminal bootstrap, frozen inherited prior, finite tensors and save/reload passed. Actual trainer worker factory used for recorded single/two-arrival tasks with cache and fast-small-city-tail enabled. Disposable checkpoint excluded from production. This validates integration, not throughput or learned performance. Script/config/episode rows/verification archived in mini-task-repair. Active studies still use their original no-fast-tail training runtimes.


## Connection-count reporting clarification
The existing before_first/after_first/outside_routes fields count paid road units, not all construction edits. Zero-cost connections between existing road tiles can still change a network. Therefore zero post-delivery spending alone does not prove zero post-delivery building. Selected original/expansion replays(14games,one layout per family/model) show no post-delivery edits; this is not a population claim. Added separate total/pre/post-first-delivery connection counts, zero-cost counts and connections outside observed assigned trip routes to the current auditor. Existing frozen production evaluators remain unchanged. Additional original60-second baseline audit is running with2CPUworkers; compare all common fields against prior measurements before using the added counts. No reward or policy change.

Evidence:mini-task-repair/selected-free-connection-audit.json and updated auditor.


### Evaluation memory scheduling
Both live studies now limit future frozen evaluations to2CPUworkers to keep parallel review memory bounded. At reset-final review, availableRAM5.4GiB and fullswap motivated applying the scheduling-only limit to the original study too. Already running evaluations retain their loaded worker count. Initial evaluator source and exact diffs/hashes preserved; trainingsource/checkpoints/seeds/rewardunchanged.


## Reset-curriculum arm completed: readiness failed
Completed262144added decisions/8192Adamupdates. City mean89.25vs126.09375original,24/32scoringvs30/32. Full curve113.78→100.06→89.25. Tight single8/16unchanged, laterpair2/16vs3/16original; shortadjacent/bend/clear16/16,obstacle14/16retained. Final paired score interval is recorded in reset-arm-complete.json. This candidate fails the predeclared screen and is not promoted. Coldcontrol continues its full budget; pending result needed to assess the reset intervention relative to matched training. Separate duration study continues from original, not this regressed checkpoint. Bank-final check running to distinguish selected-start learning from transfer.


## Completed reset-arm behavior and selected-bank review
Final selected-bank successes23/36single versus original21/36,96/124later-pair versus94/124. These small changes on selected training states do not establish transfer; empty-board tight single remains8/16 and later service2/16. Final city regression−36.84375,paired95percent interval[−61.65625,−15.15625],on consumed development data. No promotion.

Six of32matched city games newly score zero; every one spends45road units and makes49–51construction edits. This is not construction avoidance on those failures. Selected paired replay uses the largest original score among newly-zero games: seed184000001/action193352. Both native replays reproduce all final counters exactly. Original scores169at600seconds; candidate0at147.35seconds. Original first delivery31seconds/firststockout87; candidate firststockout14and no delivery. Candidate eventually has native assigned routes to the initial destination; first recorded visible red cars are at145seconds, close to failure. Therefore this illustrative failure is late effective service after poor spending, not proof it never physically connects. Screenshot shows extra early branches around the initial destination. Selected case is not the average; complete32-game counts retained. [Comparison figure](reset-regression-replay/comparison.png), exactHTML/traces/finalstates andbehavior-summary.json archived.

Expanded112-game original60-second audit matches every preexisting field exactly. It now confirms zero post-delivery construction edits across all64adjacent/bend/clear/obstacle cases. Singles have2post-delivery edits total across16tight games; generous singles3. Two-pair games have67post-delivery edits,12zero-cost; some later building is necessary, so these counts alone do not identify waste. Source/counts under connection-counts-original-60.


### Reset policy distribution drift probe
On identical states from the selected paired city replay, the reset-final model is substantially more eager to build: on original opening states through31seconds, mean Wait probability0.609→0.351, while mean conditional-road total variation is0.0626. On the candidate opening states, Wait0.637→0.388 and roadTV0.0829. This is one selected city, not a generalization estimate or a causal ablation. It motivates a separate frozen32-city probability-component diagnostic: original Wait + new conditional roads, and new Wait + original conditional roads. This swaps only inference distributions for diagnosis; no labels, training, planner, checkpoint promotion or new long run. Script/config/data under reset-components/. TwoCPUworkers bound memory.


## First65k development review
Long-window65,536: city137.53125versus126.09375original,31/32scoringversus30/32; pairedmean+11.4375,95percentinterval[−7.1570,31.4703]. Tight single8/16unchanged; generous10/16; firstpair10/16andboth4/16versusoriginalfirst8/16/both3/16on the same300-second protocol. Shortskillsretained. This is preliminary positive movement but the interval includeszero, task screening targets are unmet, and the matched60-second duration control has not run yet. Continue full declared budget; no promotion/overnight launch or attribution to duration alone. Earlier experiments also had transient early city gains, so inspect the full curve. Full records long-65536-review.json.


## Wait/road component intervention completed (25 November, 17:18 Beirut)
Frozen32-city component swaps: original Wait + reset-final conditional roads yields135.78125,30/32scoring; original126.09375,30/32; reset-final89.25,24/32. Against original, pairedmean+9.6875,95percentinterval[-17.4695,36.3133]; against jointresetfinal,+46.53125,[9.1555,82.1875]. Reverse combination(newWait/originalroads)106.28125,29/32. This supports Wait drift contributing to the observed regression; it does not establish improvement over original or prove road preferences are optimal. All64games and pairedresults in reset-components/. Development seeds reused; hybrids were diagnostic only.

Engineering next step: prepare a separately named checkpoint restoring original zero-output Wait modules while retaining all trained non-Wait weights, critic and named Adam state. Frozen Wait output remains independent of trainable shared encoder because both final Wait layers are zero. Explicit migration and shared-state probability/save-reload checks required before evaluation. No new learner or promotion. Existing two comparisons continue unchanged.


## Wait restoration checkpoint verified (17:20 Beirut)
Created local-only `output/training/mini-reset-wait-repair-01/start.zip`, SHA edb2a26da557f6d3d41a51ca64d62d0bdde8423572e84e78039a80cc43083aa5. Source is completed reset-final; both original zero-output Wait modules restored and frozen. All non-Wait weights retained exactly, including critic. Named Adam migration retains22 parameter states at8192steps, omits8 frozen Wait states, and preserves688128 lifetime decisions and876 SB3 epoch-update counter. These counters have different meanings;8192 is actual optimizer steps for this continuation. Reload exact, input hashes unchanged,384 shared city states match the diagnostic component distribution within5.35e-7. No training performed by migration and no promotion.112-game mini evaluation at300seconds now running with2CPUworkers. Source and checks in wait-repair/; subsequent road-only training would require verifying frozen Wait under an optimizer step.


## Wait restoration mini-task review
Completed112frozen games. Same300-second protocol as duration-study original: tight single8/16 unchanged, generous8/16 unchanged, both pairs5/16 versus3/16 original. Short adjacent/bend/clear16/16 andobstacle14/16 retained. Still below declared tight14/16 andboth8/16 screens; no promotion. Component city result recovers degradation but remains uncertain versus original. Separately, a disposable Adam update changed road/encoder/critic tensors while Wait remainedwithin3.58e-7 on12shared states; saved checkpoint/8192Adamsteps unchanged. This validates mechanics, not effectiveness. [Detailed review](../docs/training/mini-task-repair-2026-11-25/wait-repair/RESULTS.md). Both planned comparisons continue.


## Visual verification of Wait-restored mini behavior
Four exact replays completed: original/restored on the lowest-seed newly both-served pair (231000003) and lowest-seed tight failure (231000000). Every existing archived metric matches. Paired frame sheets visually inspected. In the improved pair, original spends its12 units on one served route plus disconnected fragments; restored serves both colors and survives300seconds (36deliveries vs11before original native failure near170seconds), still with an unnecessary remote fragment. The tight case remains disconnected with stock exhausted for both, failing near148seconds. These selected cases demonstrate real service improvement and a remaining route-assembly failure, not population optimality or a solved city strategy. Preserve plots, HTML, rawframes andsources in wait-repair/selected-replays/. Auditor now accepts explicit replay seeds; default evaluation behavior remains unchanged, active snapshots untouched.


### Finite-lesson observability research cross-check
Read the primary Pardo etal.2018 time-limit result while reviewing current context/bootstrapping. The lesson encoder keeps a600second time scale while finite training lessons end at60/300; no explicit task/deadline input. Across-run identical-state/different-return evidence does not prove within-run state aliasing, and fixture geometry may identify context. Documented an open critic-context hypothesis, with no change to either active study or terminal semantics. [Source, limits and proposed checks](../docs/training/mini-task-repair-2026-11-25/horizon-observability-note.md).


## Completed reset-arm training behavior
Aggregated completed training episodes by quarter and cold versus recorded reset, using native per-destination delivery counters. Cold tight-single success stays about56percent to55percent; recorded tight starts59percent to59percent. Cold later-pair service24percent to23percent; recorded later-pair service76percent to74percent. Fixed-bank repetitions do not show clear monotonic learning over this budget. These are training distributions (different cold seeds over time), not paired evaluation or proof that more time can never help. Mean task return mixes cold and selected easier starts, so it should not be read as empty-board accuracy. Source/hashes and allquartercounts in reset-training-behavior.json; analysis source summarize_training_behavior.py.

Wait-restored GPU resume smoke also completed128decisions/4Adamupdates/12episodes in12.90seconds through actual two-worker factory with300-second recorded tasks, cache and fast-tail. Native reward/no-bootstrap, frozen prior andWait, finite tensors and save/reload8192→8196Adamsteps passed. Disposable checkpoint excluded; original remains unchanged. No additional production learner launched.


## Prepared bounded road continuation; not launched
Prepared `run_mini_road_continuation.py` and its report script. It requires an explicitly verified CityRoadChoicePolicy parent with both zero-output Wait modules frozen. Same native8city+4pair+4single reset mixture,300-second lessons, original road/spatial/critic rates, retained Adam, optional validated cache/fast-tail. A declared262144-decision budget would have65k/131k/final mini/city reviews against its starting parent and retained original. New cold training range241M reserved. This would test whether road learning continues once Wait drift is prevented; it is not a matched causal comparison with the ongoing original-parent duration study and is not a permanent timing policy. No third production learner or overnight run launched. Actual checkpoint city evaluation and frozen finite-lesson gradient diagnostic are running before a launch decision; existing two comparisons continue. Source compilation passed, CUDA resume smoke passed as separately recorded.


## Restored checkpoint city repeat and critic follow-up
Actual saved Wait-restored checkpoint completed32cities: mean135.78125,30/32scoring. Every common native game field exactly matches the earlier original-Wait/new-roads probability intervention. This verifies the saved artifact reproduces the diagnostic behavior; the gain over original remains uncertain and mini gates remain unmet. City-repeat checks and rows in wait-repair/. An initial comparison helper expected wrapper-specific metadata in both schemas; corrected to compare the explicit intersection of native fields. No rerun or model change.

Frozen16-game native300-second lesson gradient probe completed256 sampled choice states, no optimizer step. Critic mean−13.91 versus finite return11.23, MSE865.70, explained variance−0.638 on this reused small cohort. In the shared spatial encoder, mean value-loss gradient norm0.495 versus policy0.257 on pairs;0.336 versus0.229 on singles. These magnitudes motivate checking gradient directions; they do not alone prove interference. Native finite MonteCarlo targets and within-task normalization approximate the first policy-gradient update, not actual mixed-rollout bootstrapped/epoch gradients. A same-trajectory direction probe adds policy/value cosine and current-baseline/zero-baseline comparisons, with no training. No new production learner launched while this concern is reviewed.


## Shared-encoder gradient interference hypothesis and prepared intervention
Direction probe reproduces all16episodes and256sampled states exactly. Value gradients oppose actor gradients in5/7nondegenerate shared-encoder batches; two pair batches have a−0.94projection relative to the actor component. One nearzero actor batch excluded from directional interpretation. This is not actual PPO epoch/Adam causal attribution. Full norms/directions in wait-repair/gradient-review.json.

Prepared a separately loadable CityRoadChoiceDetachedCriticPolicy. It detaches critic input features, keeping value-head training while preventing value-loss updates to road features. Existing weights/outputs/Adam can remain exact; this is not a fully separate critic encoder or a complete calibration fix. Research basis and limitations in critic-detach/PLAN.md. Migration/gradient/PPO checks precede any production use. Two active studies unchanged; no new production learner yet.


## Critic detachment preflight passed
Separate parent `output/training/mini-road-detached-initial-01/start.zip`, SHA7582e285e3f6b2b44487cf3fe86156169aa80d79272dccbe21dc408fed0bf324. All22Adam states remain at8192steps; weights and lifetime counters preserved.384shared-state component checks and exact original/repaired value comparisons passed. Additional12shared states have bit-exact action and value outputs versus the Wait-restored parent. Value-only backward/update reaches only value_net and leaves all12action distributions exact; actor backward still reaches road/spatial parameters and excludes critic/Wait. GPU factory resume128decisions/4updates/12episodes passed native return/no-bootstrap/frozenprior+Wait/finite/reload checks; saved parent unchanged. Disposable smoke excluded. No new production run yet. Added explicit policy class/critic-detachment metadata for future trainer/runner records; active runtimes unchanged.


Scope clarification: this gradient probe evaluates the Wait-restored candidate on300-second lessons, whereas its critic was last trained jointly with different Wait behavior and60-second lessons. Changed policy/state distribution and return objective can themselves explain stale value estimates. Opposing sampled gradients are not inherently an implementation bug, and the probe does not establish that critic interference caused the original reset-arm regression. Detachment is a bounded protection hypothesis while adapting road/value learning, with fresh performance checks still required.


### Fresh confirmation protocol prepared
Reserved236Mmini/237Mcity seeds remain unused. Specified32mini layouts per family,32new600second cities×2actiondraws, and8different1800second cities×2draws, with checkpoint frozen before review. Gates unchanged; no automatic launch. Added explicit --workers to generic city suite evaluator (default8 preserved) so future confirmation can use2CPUworkers without memory pressure. Scheduling only; existing runs unaffected. See mini-task-repair/CONFIRMATION_PLAN.md.


### Mini-task reset comparison completed with explicit export-error recovery
Both arms completed262144added decisions. All saved checkpoint hashes and12evaluation measurements verified. The first replay-template error is retained separately; its successful identical rerun is used in the summary. No training restart or promotion. [Results](../docs/training/mini-task-repair-2026-11-25/RESULTS.md).


## Reset comparison complete; longer-lesson midpoint and focused practice launch
Both reset/cold arms completed262144added decisions. All12evaluations and checkpoint hashes passed explicit recovery checks; retained export-error record is historical, not a new training failure. Cold final city115.25,29/32scoring, delta−10.84CI[-36.22,14.84]; reset final89.25,24/32, delta−36.84CI[-61.66,-15.16]. Both tight8/16; latercold3/16,reset2/16. Neither promoted.

Longer300-second lesson midpoint131072: city146.6875 versus original126.09375,31/32scoring; pairedgain20.59375CI[2.4375,40.375], about16.3percent. Tight9/16,generous11/16,firstpair11/16,both3/16; shortskillsretained. Encouraging consumed-development evidence; fullbudget and matchedshortcontrol still pending, taskgatesunmet, freshconfirmationunused.

Engineering decision: defer the prepared broad protected-road continuation and first practice one difficult empty training board. Select232000001 as lowest previously successful beyond-six-cell bank-collection seed (distance7,stock8); no prefix or teacher action. Detached-critic/Wait-restored parent succeeds5/32sampled games initially. Actual-factory2workerGPU smoke128decisions/4updates/10episodes passed. Launched bounded65536decision run18:09Beirut, controllerPID859857, output/training/mini-fixed-route-01. Same native300second reward/termination,16workers×512steps×8rollouts; Wait frozen, critic input detached, road/criticAdam8192retained; cache/fasttail validated. Fixed16k/32k/64kreviews then broadmini/cityretention, no automatic promotion. This tests one-layout learning, not generalization. Fullplan/source/revision/commands in docs/training/mini-fixed-route-2026-11-25/. Existing duration comparison continues unchanged. No overnight session.


## Focused route quarter review and exact visual check
At16384added decisions, fixed-layout successes12/32 versus5/32 initially;9actiondraws gained success and2lost it. Mean native score6.75 versus2.8125. Early learning movement on one training layout, not generalization or convergence. Full65536budget continues.

Selected the lowest-RNG newly successful draw622005 for exact paired replay. Expanded only forced Wait periods for visualization; every compact native boundary and final evaluation counter matches. Starting candidate0deliveries/nativefailure near148seconds; quartercandidate18deliveries by300, firstdelivery15seconds. Both make10construction edits and no edits afterfirstdelivery. The quarter policy completes a functioning route but also places a remote stray fragment. Thus route completion improves while conservation is not yet demonstrated. Frame sheet visually inspected, including all road coordinates. Source, HTML, rawframes, selection andchecks in mini-fixed-route/quarter-replay/; plot source plot_quarter.py.


## Focused connection midpoint, 25 November 18:30 Beirut
Measured: at32768added decisions the fixed board succeeds15/32 (initial5,quarter12); gained11 and lost1 draws against initial. Checkpoint SHA8601e00f53432f0b951e46cc6c8e7cca6d629cd30844a9eec2ea68b75adaa658. Positive movement, still below29/32mastery; declared65536budget continues unchanged. Same training layout/action draws, not geometry generalization. Evidence docs/training/mini-fixed-route-2026-11-25/evaluation/fixed-32768 and midpoint-review.json.


## Longer-lesson midpoint visual audit, 25 November 18:31 Beirut
Measured exact paired city replay selected nearest median gain among positive paired changes, tie lowest seed/action RNG; seed184000000. Original0deliveries/151.15seconds, midpoint28/270.4. All final native counters and checkpoint hashes match frozen evaluation. Figure inspected: midpoint completes the opening red route but builds disconnected fragments and excess roads, exhausts stock and eventually fails. Native future buildings differ between trajectories; not identical late-state control. This is evidence of useful opening connection behavior in this selected game, not reliable conservation/strategy. See docs/training/mini-task-horizon-2026-11-25/midpoint-city-replay/ (selection, exact checks, frames, HTML, figure, behavior summary); sources replay_midpoint.py/plot_midpoint.py. Full budget and short control continue; no promotion.


### Scope of the fixed-board test
Engineering interpretation: a successful native-score route can include a harmless extra road when stock allows it. This lesson therefore tests reliable connection completion, not minimal construction or reserving stock for a future arrival. The Wait correction heads remain frozen; relative road preferences still affect action probabilities, but this stage is not new joint Wait/road strategy training. After reliable fixed-board success, test new action draws and varied empty-board connections before judging later-arrival conservation and city transfer. No new road penalty or hidden reference route is added.

Scope clarification for focused route run: Wait correction logits are frozen, but actual Wait probability can change through normalization as road logits learn. Do not describe overall Wait behavior as mathematically fixed.


## Full fixed-board budget, 25 November 18:46 Beirut
Measured final fixed review:24/32 successes, mean13.5, after65536added decisions and5529completed training episodes. Initial5/32,quarter12/32,midpoint15/32. Final checkpoint SHA c86c0db95e28951c3e9ed36d5a29eb94d7faa4cbddbfddaed18700dc70121eb3. Still below practical29/32 mastery, but substantial improvement across the declared budget. Broader112mini/32city retention reviews remain running. No promotion or overnight launch. Further same-task continuation is under consideration, not yet started.


### Final fixed-board visual review
Exact replay of the lowest-action-RNG success and failure under the final checkpoint: success18deliveries (first15s), failure0/nativeend147.9s; each10construction edits, stock0, no post-first-delivery edits. All compact native boundaries and final metrics match; visualization expands only forced Wait ticks. Figure visually inspected: successful draw completes a direct functioning route but includes a remote stray fragment; failed draw builds two disconnected sides and an unnecessary branch, exhausting inventory before bridging the gap. This selected failure is a construction-choice issue, not demonstrated congestion. Different sampled actions on the same training board; no population frequency claim beyond the32-game review. Source/frames/HTML/checks/figure: final-replay/, replay_final.py, plot_final.py.


### Broader mini review after fixed practice, 25 November 18:52 Beirut
Measured112developmentgames: adjacent/bend/clear16/16each, obstacle14/16 (short skills retained); tight singles8/16 unchanged versus forward-equivalent parent; generous singles12/16 versus8/16; firstpair12/16, bothpairs3/16 versus5/16 parent. This does not establish general tight-stock improvement or later-connection mastery. Finalcity review still running. Fixedboard24/32 is a learning diagnostic, not transferable strategy certification.


### Audit coverage limitation: legacy negative pair fixtures
Source inspection at18:56Beirut: historical training/pair_ppo.py requests curriculum-pair-match/mismatch/homes/destinations/blue-red. The current simulation/Assets/Simulation/ConstructionCurriculum.cs allow-list does not include pair-*; current Headless/Program.cs dispatches curriculum-* through that method. No native reset probe or compatibility repair performed here. Therefore the current112-game city-interface mini audit does NOT certify negative-pair/no-needed-connection behavior using those historical fixtures. Its scope remains the seven documented families. Legacy pair scripts/results are preserved, not treated as current-host proof. Current quiet/traffic fixtures are different tests. Investigate compatibility before attempting or claiming those negative-pair checks.


## Repeated hard-connection diagnostic completed
Declared budget and all fixed/practice/city reviews complete. See docs/training/mini-fixed-route-2026-11-25/RESULTS.md. No automatic promotion or overnight launch.


## Focused route result and unchanged continuation, 25 November 18:59 Beirut
First focused run completed: fixed5→12→15→24/32,5529trainingepisodes; shortskills retained, general tight8/16unchanged, bothpairs3/16vsparent5, generous12/16vs8. City129.25,31/32scoring; delta−6.53125 CI[-27.34375,15.21875] versus forward-equivalent parent, +3.15625 CI[-21.0625,27.0633] versus retainedoriginal. No clear city gain, no promotion. Exact selected final replays and learning curve inspected; source/small evidence in mini-fixed-route archive.
Engineering decision: another65536unchanged fixed-board decisions because the full learning curve remains positive, then new action draws if29/32mastery and varied layouts. Parentfinal SHA c86c0db95e28951c3e9ed36d5a29eb94d7faa4cbddbfddaed18700dc70121eb3 preserves753664lifetime decisions/all22Adam states10240. Source unchanged, prior native/PPO validation and new load-integrity passed. New episode/RNG process, not bit-exact uninterrupted trajectory. Launched controller877049, output/training/mini-fixed-route-02. Plan/source/commands/revision archived in docs/training/mini-fixed-route-continuation-2026-11-25/. Duration comparison unchanged; no overnight run.


## Current-policy negative-pair audit prepared and validated
Code inspection found historicalpairfixtures separate fromproduction. Created isolated output/pair-city-audit-build-01 fromcurrentnative source, adapted archived20Nov fixtureloader/dispatch only; production source/binaries and active learners unchanged. Fourmatching/mismatched/same-type cases, nativeconnection/Wait, no autoFinish/planner/references. Initialadapterwronglyusedregularcitymask (native rejected); changed toexistingpractice mask/draw/Wait methods. Second check forgot redundantbuildingColorsplane incolor-only comparison; fixedexpectedcolor-plane normalization, retainingallotherrawfield equality. Bothfailures archived; no policyresults fromthem. Final180native transitions across9ordinarycity/mini families exact againstproduction;16fixturechecks pass, match/mismatch geometry/masksidentical/currentinputscolordistinct.
Frozen original andfocusedrun01final evaluation128games (4cases×16layouts×2models), seed243M,60seconds,2CPUworkers, source/runtimefrozen. Smoke244M; reserved236M/237M untouched. Scorezeroexpectedfornegativecases; reportbuildingbehavior, notscoreaccuracy. No training/overnightlaunch. Archive docs/training/city-negative-pair-audit-2026-11-25/.


## Completed frozen audit and mechanism, 25 November 19:10 Beirut
All128games completed with checkpoint hashes unchanged. Both retainedoriginal andfocusedrun01final solved16/16matching controls and built/spent all stock in48/48negative scenes (16wrongcolor,16twohomes,16twodestinations), scoringzero as expected. Average3.125paidunits ineachfamily; negative scenes5.125construction edits includingzero-cost additions. Current observations distinguish matching fromwrongcolor; this is not the old missing-color-input defect. Current tests use nativeWait, notautomaticFinish.

Probe of64initial states permodel: negative Waitprobability about4.86–6.26percent. Original andfocusedfinal Waitprobabilities match within float tolerance; roadchoices changed but the build-versus-Wait decision did not. Source confirms CityActionDistribution already subtracts legal-road logsumexp, separating conditionalroadchoice fromWait; ProgressDistribution adds only the inherited frozen progresscoupling. Adding10toallroadlogits inread-only probes cancels, as intended. The focusedtraining deliberately frozeWait corrections, so it cannot repair thisdecision. Nativezero reward in isolatednegative cases also does not preferWait overunnecessarybuilding. These are distinct learning limitations, not proof of a policy-gradient implementation bug.

Correction to an earlier note: the statement that road-logit changes could materially changeWaitprobability throughordinarysoftmax normalization was wrong for thiscustom distribution. The already implemented conditionalnormalizer prevents that. See wait-probe.json/probe_wait.py and training/city_road_policy.py. Earlier notes remain historical and are superseded.

Next engineering proposal within the approved repair: a boundedPPO build-or-Wait mini-task that trainsWait corrections whilepreservingconditionalroadweights. Use matching/negative nativefixtures, no teacher routes orsupervised actionloss. Explicitbinarytaskreward andone-decisionepisodes provide a learnable signal forabstaining; retain nativecityscore evaluation separately. This is preparednextwork, not yetimplemented orlaunched. Continue existingdeclaredroad/durationbudgets. Noovernightpromotion.


## Preflight completed — 25 November 19:40 Beirut
New fixture build02 uses the native map's five-color palette and safe50×30board placement. Version1 mistakenly assumed all8observation color channels were nativepalette entries; its failingseed andsource/build are retained. No training usedv1. Build02 passed180exactordinarynative transitions across9families,1024train/validationpairresets,64binarynativeactions.56Wait-only native continuations validate fixture meaning: incompleteconnections stayunserved,quietnetworksservewithoutconstruction; no reference actions queried.

Migration fromfocusedrun01final preserves everyweight and22Adamstates10240, with16shared-state actor outputs bitexact. Only8existingWaitparameters become trainable; originalcriticweights/Adam remainfrozen andvaluepredictions arezero only forone-stepbandit training. Actual2workerGPU PPO smoke128decisions/4Adamsteps passedbinaryreturns/no bootstrap, finite/reload, roadlogits exact andallotherweights/Adam unchanged. Conditionalroadprobabilities differ by atmost5.96e-8; Waitprobability changes byup to.0259.24changedstate-dict keys arealiasesof8Waitparameters, not24independentparameters. Smoke weights excluded. A finite-weight assertion was added after the smoke; thisguard does not change the computation. Evaluator smoke passedone-decision andnative60-second modes on7fixtures each.

Preparedcontroller freezesruntime, verifiesmigration, reviews8k/16k/32k, thennative112/practice112/city32. Initialnative112review providesbefore/afterbehavior. Ordinarypractice/city reviews explicitly use the originalproduction host (a3a225...), while newdecisionfixtures useisolatedbuild02. No productionWait run yet; waitforfocusedrun02final/reviews beforeparentselection. Current native cityconfirmation236M/237M andWaitconfirmation247M untouched. Existing durationcomparisonunchanged.


## Focused continuation final fixed review, 25 November19:42Beirut
Measured32/32fixed successes at65536addeddecisions inrun02 (131072totalfocused), mean18.0. Run02curve24→28→29→32/32; run01began5/32. Finalcheckpoint SHA bc23555cf04845f7c8d648c97e5d7260d7b95563280e6114aa22fb2b3a6edabd. All5534trainingepisodes finished; broader112mini/32cityretentionunderway. Target29/32reached, sofreeze finalcheckpoint andlaunch32newactiondraws623000–623031 ontheSAME traininglayout. Theseactiondraws nowconsumed; no geometry/generalizationclaim. No promotion/overnightlaunch.

Focusedrun02 freshactionreview:29/32 onnew623000–623031, sameboard/frozenfinalSHA bc23555...; oldreview32/32. Practicalone-boardmastery targetmet; do notclaimgeneralrouteorcitymastery. Fullmini/cityretentioncontinues.


## Native export preparation — 25 November 19:50 Beirut
Engineering: implemented export_city_wait_learning.py and CityNativeAfterWaitPolicy. Export restores the native template PPO configuration (gamma1, value coefficient1e-5), retained city critic forward pass and joint Wait/road/critic learning with detached critic features. It preserves every actor/critic weight, all30 named Adam states, counters and exact16-state action probabilities. This was checked on disposable smoke weights only, not a candidate promotion. First native-resume smoke failed before learning because its copied assertion assumed the first optimizer group was roads (10240steps); in the joint policy it is Wait (4steps). Corrected to check each named state's advance; failed source/output retained. Native learning smoke still pending. Sources/results in docs/training/build-wait-ppo-2026-11-25/native-export-smoke.

Focused continuation final checkpoint verified:819200lifetime decisions,22Adam states at12288, finite weights. Learning curve source and figure archived/viewed; training success rises roughly76% to94%, familiar review24/32 to32/32, fresh action draws29/32 on the same board. No geometry transfer claim. Broad review retains16/16 adjacent/bend/clear,14/16obstacles; tight8/16,generous11/16,both-pairs4/16. City retention still pending.


## Before-launch review criteria — 25 November 19:50 Beirut
The first bounded32,768decision run is a repair experiment, not permission to launch overnight. Review all planned8k/16k/32k checkpoints. An encouraging one-step result requires at least90% mean appropriate-group probability in each of the seven cases; this alone cannot pass. Full native60second play should avoid construction in at least14/16 of each negative/quiet family, while all-target service on matching/join/route cases loses no more than2/16 against the same parent. Broad short skills should lose at most one success per16-game family; city retention should have at most one extra zero-score game and no clear paired regression. Treat these small development checks as selection gates, not statistical proof of mastery. A successful stopping repair still must satisfy the broader geometry, second-connection and fresh-city confirmation protocol before overnight promotion. If the run is still improving, consider a documented fixed-budget continuation; do not declare failure solely from an early checkpoint.

Native export smoke completed:128decisions through the actual curriculum worker factory,12episodes, native reward ledger/no terminal bootstrap, all30 named Adam states advance4steps, frozen inherited weights unchanged, finite save/reload. This validates plumbing on disposable weights, not native learning quality. Initial assertion error/source retained.


## Repeated hard-connection diagnostic completed
Declared budget and all fixed/practice/city reviews complete. See docs/training/mini-fixed-route-continuation-2026-11-25/RESULTS.md. No automatic promotion or overnight launch.


## Fixed continuation decision and Wait study launch — 25 November19:52Beirut
# Focused continuation: mastery on one board, failed city retention

The second65,536-decision run completed its full budget unchanged (131,072focused decisions across both runs). Familiar32-action review improved24→28→29→32successes. A frozen final checkpoint passed29/32new action draws on the same training board; these draws are now consumed. Training success rose roughly76% to94%. The checked learning curve and its source are retained here.

This is evidence of fixed-layout learning, not broad strategy. Varied tight-stock cases remained8/16, generous11/16, both connections4/16; short tasks retained16/16adjacent/bend/clear and14/16obstacle.

City development mean fell from129.25 to107.47, scoring27/32 instead of31/32. Paired scenario-cluster mean change−21.78,95%bootstrap interval[−50.22,8.88]. The mean decrease is uncertain, but four extra zero-score games fail the retention screen. Do not promote this checkpoint. Original baseline126.09also remains above its mean; this is a consumed development suite, not independent confirmation.

Engineering decision: preserve both completed runs and continue the build-or-Wait repair from run01final, SHA c86c0db95e28951c3e9ed36d5a29eb94d7faa4cbddbfddaed18700dc70121eb3. Run02final remains local at output/training/mini-fixed-route-02/training/final.zip, SHA bc23555cf04845f7c8d648c97e5d7260d7b95563280e6114aa22fb2b3a6edabd;819200lifetime decisions,22Adam states12288, finite weights verified. No files/checkpoints replaced. No overnight promotion.

See transfer-review.json, fresh-actions/, learning-curve.png/json and final-checkpoint-integrity.json. The controller's RESULTS.md is the historical raw study report; this interpretation adds the parent choice and fresh-action result.

25 November2026,19:52Beirut: focused continuation completed; fixed-board32/32familiar,29/32fresh action draws, but city107.47/27scoring fails retention versus preceding129.25/31. Preserved final, selected earlier run01final for bounded build-or-Wait PPO. New run PID896687,32,768decisions, output/training/build-wait-01; only8Wait parameters learn binary action-group reward, road/critic weights and Adam retained. Native city reward unchanged. Longer-lesson comparison PID807935 continues. No overnight launch or promotion. [Current work and criteria](../docs/training/build-wait-ppo-2026-11-25/ACTIVE_WORK.md). Older entries below are historical.

Monitor: `tail -F /home/mohammadjaffal/mini_motorways/output/training/build-wait-01/run.log`. Exact launch/revision/parent choice in docs/training/build-wait-ppo-2026-11-25/launch.json. All preflight checks passed; source/native frozen bycontroller. No planner/BC; mini-task reward explicitly changed, city reward unchanged.


## Focused continuation city replay — 25November19:54Beirut
# Selected city regression replay

Selection was fixed before replay: lowest scenario/action RNG among games that scored with focusedrun01 but scored zero after run02. Seed184000001. Both frozen replays exactly reproduce the evaluation counters; models/native host hashes are checked in selection.json.

Parent scored36 and lasted316.85seconds. Continuation scored0 and ended147.35seconds. At30seconds parent retained6road units, continuation0. Both produce extra branches; continuation spends its opening stock without delivering to the initial red destination and still has no delivery at native failure. This is a selected failure illustration, not the average game or proof that all extra training harms learning. Later generated layouts can diverge as construction changes; the common starting seed is not an identical late-board counterfactual.

The replay supports rejecting the continuation as the starting point for the Wait repair. It also shows the unresolved placement/driveway-completion problem: learning when to Wait alone cannot guarantee useful routes. Trace JSON/HTML and plotted comparison are retained, and the image was inspected.


## Wait repair first frozen review — 25November19:55Beirut
After8192decisions, appropriate-group probabilities: destinations.193(vs.056),homes.243(vs.074),mismatch.234(vs.071),quiet.794(vs.790),match.910(vs.975),join.735(vs.715),route.708(vs.687). Early discrimination is incomplete; positive matching loses confidence. Full32kbudget continues unchanged.139WaitAdam updates afterKL safeguard; everyotherweight/22oldAdam states exact. Initial native112review confirms0/16no-build in each negative/quiet family, all-targetservice16/16matching/join/route/quiet. Firstdecision correctness alone would miss repeatedbuilding. Measurement paths evaluation/decision-initial,decision-8192,native-initial underbuild-wait-ppo archive. No promotion.


## Build-or-Wait32k frozen/native findings — 25November20:02Beirut
Declared32,768decisions complete; fullcity/broadmini retention pending. Frozen appropriate-action probabilities: destinations.5976,homes.6707,mismatch.6496,quiet.9199,match.8947,join.9536,route.9466. Curve/measurement sources archived and plot inspected. Road/critic weights and22oldAdamstates remainedexact everyrollout.

Native112review: all-targetservice16/16 inmatch/join/route/quiet retained. However no-build0/16 ineachnegativefamily andquiet, so repeatedstoppingfails. Negativegames stillspendstock; quietmeanedits1.8125vs2initial. MorefrequentcorrectfirstWait doesnotensuresequence-level restraint. This is nottaskmastery. Do notchangerward/architecturebasedsolelyon32k; curveimproving, considerboundedunchangedcontinuationaftercityretention. No overnightpromotion.

Preparedcontinuationplumbing (runningrun01runtimeunchanged): controller--seed-start canadvancepastpriortrainingseeds; migrationchecks retainednativecritic throughbaseforward evenwhenparenthaszerobanditbaseline. Disposablebandit-parentmigration retainsall30Adamstates/weights, exact16sharedactors; actual128decisionPPOresume advancesWaitAdam4→8, old22states10240unchanged, frozenweights/binaryreturns/reloadpassed. Smokeweightsnotcandidate. See bandit-resume-smoke/. Nativeexport previouslypassed separately.


## Wait repair broad retention/replay check — 25November20:08Beirut
Broader112mini review retained16/16adjacent/bend/clear and14/16obstacle. Tight8/16unchanged; generous11/16vs12parent; bothpairs4/16vs3parent (firstpair11vs12). No general hard-route mastery. City32reviewstillrunning. Exact lowest-seed native replays completed for7families before/after; final counters/checkpoints match all14evaluations. Inspected comparisonplot confirms matching/partialrouteswork but mismatchstillgetsconnectedandquietstatesstillreceiveextraedges. Prebuiltfixtureconnections areincluded infigures; stepsidentifynewconstruction. Sources/HTML/frames archived.

Open question for later review, not a measured failure: quiet lesson uses an established multi-building network; ensure learned stopping also transfers to simpler completed routes and busy cities. Do not infer universal stopping from one fixture family. No addedfixture/rewardchange or automaticcontinuation yet.


## Build-or-Wait bounded study completed
All declared checkpoints and native/practice/city reviews completed. See docs/training/build-wait-ppo-2026-11-25/RESULTS.md. No automatic promotion or overnight launch.


## Wait repair completed and continued — 25November20:15Beirut
# First Wait lesson: interpretation after all reviews

The full32,768-decision budget and every declared review completed. First-action discrimination improved strongly, but repeated stopping failed:0/16games without building in each incompatible family and quiet. Native matching/join/route/quiet service retained16/16perfamily. Broad short skills retained; tight8/16, generous11/16, bothpairs4/16. These do not pass overnight-readiness gates.

City mean141.09375 versus129.25parent,31/32scoringboth. Paired scenario-cluster scorechange+11.84375,95%bootstrap interval[-10.59375,34.25]; the gain is uncertain. Outside-route roadunits fell6.8125,interval[-11.875,-1.53125]. Versus original126.09375,mean+15.0,interval[-11.65625,41.15703]. These are consumed development scenarios, not fresh confirmation. Fewer outside-route units is a descriptive efficiency signal, not proof every unused road was unnecessary or strategic planning is mastered.

Decision: continue the same improving lesson for65,536additional decisions from final SHA907e1a083b58780bd140d4e258285878ed3534a4c0be6cf9b75070eae7f04826. Nativecityretention andpositiveconnection checks passed sufficiently for a bounded continuation; stopping remains unmastered. Rewards,taskproportions,optimizer and frozenroad/criticweights stay unchanged. Newtrainingseedrange245032768–245098303. No overnight promotion. See../build-wait-continuation-2026-11-25/PLAN.md and launch.json.

Evidence: transfer-review.json,mini-retention-review.json,evaluation/,bothreplaysets,decisioncurve and nativecomparisonfigures. Sources for additional analysis/replays remain alongside runtime-source. All model/native binaries remain local-only output artifacts.

25 November2026,20:15Beirut: first32kWait-only PPO repair complete. CorrectfirstWait improves but repeatedstopping stillfails; nativepositive/shortconnectionsretained. City141.09vs129.25parent,31/32scoringboth; gainuncertain, outside-routeunitslower. Unchanged65,536decisioncontinuation PID905893 launched from verifiedfinal, output/training/build-wait-02. Longer-lessoncomparison PID807935 continues. No overnightpromotion. [Current work and monitor](../docs/training/build-wait-continuation-2026-11-25/ACTIVE_WORK.md). Older entries below historical.



## Wait repair native city replay — 25November20:18Beirut
# City replay near the median paired score change

Chosen before replay from all32development pairs: closest score change to the median (2points), ties lowest scenario/action RNG. Selected seed184000003,action RNG193354; actual scorechange3points. This is one illustration, not the best game or a substitute for the complete distribution.

Before Wait practice:170deliveries at600seconds,112paid roadunits,123build actions,26units outside final working routes,13stock remaining. After32kWait practice:173deliveries,84paid units,95build actions,16outside-route units,31stock remaining. Both native replay final counters and checkpoint/host hashes match their evaluation exactly.

The inspected frame comparison shows a simpler early connection and more retained stock after Wait practice, with continued excess branches later. Atabout30seconds the parent has added a loop/second-home connection whereas the Wait candidate keeps its opening route. This does not imply that second-home connections are always unnecessary. The two trajectories generate different later building layouts (24vs25buildings by600seconds), so later geometry is not controlled-identical. Stock difference is not simply the road-cost difference because native arrivals/awards can diverge. The complete paired city suite reports uncertainty separately.

Files: selection.json, parent/ and wait/ trace/HTML/steps/verification, comparison.png; source replay_city_change.py and plot_city_change.py in the parent archive. No learning occurred during replay.


## Wait continuation quarter and reset-bank audit — 25November20:22Beirut
At16,384additional decisions(49,152totalWait), frozen appropriate-action probabilities destinations.8676,homes.8989,mismatch.8885,quiet.9836,match.9165,join.9868,route.9848. Full65,536continuationbudgetcontinues. Thirdrolloutcollection94.64%correct istrainingbehavior, notfrozenassessment. Initial112decisionand112nativegames reproduce priorfinalbitexact aftermigration; these are duplicatechecks, notnewindependent evidence.

Read-onlyaudit of prepare_mini_starts.py confirms two-arrival bank entries require BOTH destinations served in the complete original sampled game, first delivery beforesecondspawn, andremainingstock.62pairprefixes have5–10stock at13–15seconds; native secondarrival18–30seconds. Thus bankstates aredemonstrably solvable underatleasttheoriginalsampledcontinuation; no claimthatall actionsremainrecoverable. No planner/actiontargets areprovided duringtraining.

NativeSmallCityPractice canfailtoadd thesecondpairifroadconstructionobstructsplacement; auditcounts missingpairasfailure. Measured missinglaterpair: long-lessonmidpoint1/16,C1parent2/16,Wait32k1/16. This is a limitation ofisolatedlessonreward/placement, notproof ofintentionalspawnblockingor the maincauseofpoorresults. Nofixture/rewardchange made; runningstudiesunchanged. Shoulda laterminirewardrepairbeconsidered, separateactualnew-targetservicefromalreadyservedtraffic andvalidateall-targetcompletion; do notclaimnativepartialscoreprovesbothconnections. This is anopen design consideration, notimplemented.


## Wait continuation midpoint — 25November20:24Beirut
At32,768additional decisions(65,536totalWait), allsevenfamilies exceed90%meanappropriatefirst-actionprobability: destinations.94916,homes.96203,mismatch.95707,match.95247,quiet.99522,join.99654,route.99598. This passes the one-decision developmenttarget only; repeatednative stopping andcityretention areunmeasuredatthischeckpoint. Full65,536addedbudgetcontinues. Frozenreviewcurve/measurementhashes archivedasdecision-curve-midpoint.png/json andfigureviewed. Do notinferwholeepisodebehaviorfromtheseprobabilities.


## Duration long arm budget completed — 25November20:26Beirut


20:26: durationlong-windowcompleted262144addeddecisions/8887episodes; controller807935nowshort-control, final-longpractice/cityreviewsqueued. Do notmistakecontrolfreshstartforlostlongprogress; bothuseoriginalsharedparentbydesign. Wait02~40960added, full65536continues. No promotion.


## Prepared road-head lesson safeguard — 25November20:32Beirut
Engineering preparation only, no production road lesson launched. AddedCityRoadHeadsAfterWaitPolicy and export_city_wait_learning.py --mode road-heads. Train conditionalroadheads andnativevaluehead(10parameter tensors); freezeWaitheads AND sharedvisualencoder, because a learnednonzeroWaitheaddependsonitsencoder. Retainall4optimizer groups/30namedAdamstates. This restriction is anoptionalcurriculum tool, not a permanentjoint-policydesign or a newplanner. No reward/fixturechange.

Disposablemigration preservesallweights/Adam/nativevalues and16stateactorsbitexact. ActualnativePPO128decisions/12episodes advances10road/criticstates4steps while20Wait/encoderstatesremainunchanged; nativeledger,finite/reload/frozenpriorchecks pass.16sharedstateprobes showWaitprobmaxdifference2.235e-7 andconditionalroadprobchangeup to.00664. Differentroadchoices canstill produce differentfuturestates; invariance appliesonlytothesamestate/mask. Smokeweightsexcluded. Evidence/source:docs/training/build-wait-continuation-2026-11-25/road-heads-preflight/.

Foundarecordingassumption:train_city_curriculum.optimizer_steps alwaysreadfirstgroup'sfirstparameter, whichisfrozenWaitunderthisnewmode. Fixedittochoosefirsttrainableparameter. Read-onlycounterchecks preserveexistingC1(10240),Wait(907),durationlongfinal(8192),andreportnewroadsmoke10240→10244correctly. No learningcomputationchanged; currentproductionstudiesusefrozenoldsourceandareunaffected. Originaltrainerusedforsmoke retainedastrainer-before-counter-fix; allnamedAdamadvancesweredirectlyverifiedindependentlyoftheoldfirst-groupcounter.


## Build-or-Wait bounded study completed
All declared checkpoints and native/practice/city reviews completed. See docs/training/build-wait-continuation-2026-11-25/RESULTS.md. No automatic promotion or overnight launch.


## Completed Wait continuation and regression diagnosis — 25 November 21:01 Beirut

25 November 2026, 21:01 Beirut. Run02 completed 65,536 additional decisions (98,304 total Wait practice). Each family now exceeds98% appropriate first-action probability. Quiet scenes avoid construction in14/16 native games, but negative scenes only4/16 destinations,8/16 homes,5/16 mismatches; first-action accuracy is insufficient to claim persistent stopping. Positive service remains16/16 in each matching/join/route/quiet family. Tight routes10/16, both-pair service4/16 remain below readiness.

City mean fell from141.09375 to120.84375 over32 paired development plays; mean change−20.25, scenario-cluster95% bootstrap interval[-38.125,-2.1234375]. Scoring games fell31→30. This is a measured regression on this consumed development set. The checkpoint is preserved but not promoted; no further Wait extension or overnight launch. Earlier32k checkpoint remains a candidate, not a confirmed improvement over original.

Hypothesis check: on124 identical selected bank states (62 prefixes/37 scenarios, before first delivery and at first delivery), both models already assign >99.98% mean Wait probability. The98k model waits even more. Conditional road distributions remain equal within floating-point tolerance. This does NOT support the suspected failure to wait on these functional two-building openings. It does not cover all city states. Sources: opening-wait-probe/summary.json and states.jsonl. Next diagnosis traces the largest paired city loss (166→0, seed184000004/action193255) with both policies scored on each identical encountered state. This deliberately selected failure is diagnostic, not a representative sample.

The separate duration study's long300-second arm finished262,144 decisions: city98.47 versus146.69 at midpoint and126.09 original. Final-minus-midpoint−48.22, interval[-72.72,-22.59]. Do not attribute this to lesson length before its matched60-second control completes. That control continues. No confirmation seeds consumed, no long-run readiness claim.

Evidence: docs/training/build-wait-continuation-2026-11-25/INTERPRETATION.md; transfer-review.json; docs/training/mini-task-horizon-2026-11-25/long-262144-review.json.


## Varied route repair decision — 2026-11-25T21:05:26.341281+02:00

Engineering decision under approved flexible mini-task repair: start one bounded65,536-decision PPO road-head lesson from Wait01(32k)final, not regressed Wait02. Native C1critic remains the retained template.12tight/4generous workers on varied248M seeds;64frozen development games249M(initial,16k,32k,65k), final112native mini and32city reviews. No road planner/imitation/teacher action, no native city reward change. Shared encoder and Wait weights/Adam frozen; temporary task critic, native critic explicitly restored at export. Success-only reward1+.20*remaining-stock fraction+.05/(1+ALL road actions), failure0. This targets demonstrated fragile routing rather than claiming more Wait will fix it. No overnight promotion or automatic extension.

Measured evidence: selected largest Wait02 city loss replays exactly166→0. Newmodel stockout at5seconds, no deliveries before nativefailure154.25s; parentfirstdelivery18s, stockout120s, eventually166at600s. Both policies evaluated on the same states; stronger Waitlesson lowers Waitprobability before connections, increases it on working-network states. Conditional road weights unchanged; changed action-group probabilities alter sampled construction sequence. This one selected failure supports fragile routing, not proof of the cause of every loss. Previouslyselected124functionalopeningstates alreadywaitreliably, contradicting the suspected missing functional-opening Waitskill. Exactreplays/figure underbuild-wait-continuation.../city-regression-replay; figure inspected. Templatepath exporterror repaired using existing exact trace, originalerror retained. Some redundant pre-step time/stock fields were null due to fieldname mismatch; post-step fields and trace hold correct values, not used as missing observations.

Preflight:36games/1162native transitionparity; actor migration exact26Adam/16actorstates; disposable128decision PPO7episodes/4updates passed rewardledger, frozenWait/encoder/Adam, finite reload. Native roundtrip restored4nativecriticAdam andweights exactly; actor unchanged. Dedicated subprocess trainer128decisions/9episodes and4game evaluator passed. Failed smoke checks were test-harness issues: comparing CUDA vsCPU optimizer tensors, then duplicate state_dict aliases mistakenly treated as frozen names. Preserved failedsources/logs; corrected smoke normalizes device, trainer checks unique namedparameters. No production run used failed checks. Smoke artifacts excluded from candidates. Source and small evidence retained in docs/training/route-outcome-ppo-2026-11-25/.


## Road-repair representation scope — 2026-11-25T21:13:53.932850+02:00

Code inspection and limitation, not a new intervention: road heads learn while shared encoder/Wait stay frozen. Existing representation may limit adaptation; separate road representation is a possible future hypothesis only. No teacher route/hidden future state added; traffic/tool strategy not established by first-delivery success. Details: docs/training/route-outcome-ppo-2026-11-25/SCOPE.md.


## Duration comparison matched checkpoints — 2026-11-25T21:27:38.353967+02:00

Both arms now reviewed through131072 added decisions. Long/short city means at65536:137.53/110.19; at131072:146.69/116.75. Paired scenario-cluster comparisons archived in docs/training/mini-task-horizon-2026-11-25/matched-through-midpoint.json. Long final already regressed to98.47; short final still pending. One training seed per arm and consumed development scenarios: do not infer stable long-run advantage or readiness from these midpoint contrasts.


## Completed road-head learning, evaluation recovery and optional representation preparation — 2026-11-25T21:39:46.575180+02:00

Route01 completed65,536decisions/3997episodes in1494.58s; finalSHA52de08460ce18e905cbb26acbef38f12053c369f7a47fa5d085b5d6b77e3dfa9, lifetime851968. FrozenWait/encoder/Adam andfinite reload checks pass. Fixed route curve tight20→22→21→21/32, generous25→24→25→25/32; no meaningful practice gain or road-spending improvement demonstrated. Native reviews pending. Packaging omitted stage1_replay.html from frozen runtime: mini evaluation failed during HTML export, not learning. Failedstatus/logs/partialresults preserved; added missing template and rerunning same frozen review in a separate directory before city/native export. Future controller packages template. No training/checkpoint overwritten or rerun.

Optional separate Wait/road representation prepared; restriction is hypothesis, not established cause. Details and exact migration evidence: docs/training/route-spatial-ppo-2026-11-25/PLAN.md. No production spatial study yet. Controller now accepts explicit fresh training seed start for possible continuations; current frozen run unaffected.


## Separate representation preflight passed — 2026-11-25T21:42:08.568869+02:00

Optional learned road encoder with separate frozen Wait representation passes128decision actual PPO,22trainable Adam advances,64shared-state Wait invariance(max2.03e-7), changedroadencoder/conditionalroads, no critic actor-gradient path, native export and exact lesson resume. Source/checks under docs/training/route-spatial-ppo-2026-11-25/. This establishes implementation behavior only, not learning efficacy. Await current road-head native/city review before any production decision.


## Road-head study rejected; broader road representation selected — 2026-11-25T21:52:29.293059+02:00

The65,536-decision road-head lesson did not meet readiness. Tight first-delivery practice changed20→21/32, generous stayed25/32; construction usage did not clearly improve. Native short tasks were retained (allfour families16/16), generous long routes improved11→14/16 and both-pair service4→5/16, but tight native routes fell8→7/16. These mixed outcomes do not establish robust road economy.

Native city mean fell141.09→122.50, and scoring games31→27/32. Paired mean difference−18.59375 has exploratory95% scenario-cluster interval[-46.40703,5.84375]; this is not a statistically clear mean decline, but four additional zero games violate the declared retention screen. Preserve the final, do not promote it or continue from it. No fresh confirmation or overnight launch.

The next bounded experiment returns to the stronger Wait01parent, preserving that checkpoint's actor/Adam. It permits road-encoder learning while keeping an independent frozen Wait representation, with the same first-delivery/economy reward.262,144decisions, varied new training seeds248100000+, the same consumed249M practice development cohort, plus native mini/city reviews. This gives the new trainable representation a larger budget; comparison against the previous65k study will not isolate architecture from extra training. No guarantee of score improvement and no claim the frozen encoder is proven causal. Exact migration/resume/PPO/native-export checks passed before selection. Native critic remains retained in C1template; temporary task critic starts afresh as in the previous study. This returns to an earlier retained actor, not a randomly initialized model.

The initial native mini review failed only because the replay HTML template was missing from frozen packaging. Failed status/logs/partial outputs are archived; recovery added the missing asset, reran evaluation in a new directory and completed native city review/export. Training was not rerun. All checkpoints, original sources and failed outputs are preserved. Report/figure and small sources are archived here; weights/binaries remain local-only under output/.

Evidence: docs/training/route-outcome-run-2026-11-25/; separate encoder preflight: docs/training/route-spatial-ppo-2026-11-25/.


## Road-head exact replay review — 2026-11-25T21:53:56.968003+02:00

Six paired practice traces match their frozen review counters. Gained success stillbranches, lostsuccessbuildsdisconnected, retainedsuccessusesdifferent validgeometrywithsame6edits/stock. Notuniformcleanerconstruction. Conditionalroadtop-probability averages.48–.72 inselectedbuilddecisions, notanextremenear-deterministicwrong-roadfinding. Fullselectioncriteria,trace,probabilityrecords,plotcodeandinspectedfigure archived under docs/training/route-outcome-run-2026-11-25/outcome-replays/ andprep sources. Completed evidence manifest records archivehashes; checkpoints remainlocalonly.


## Practice coverage limitation — 2026-11-25T22:22:59.612859+02:00

Code inspection: single-pair fixture uses3color IDs andone matchingpair, while nativecityprofile supports5. Layout/offset/placementvariation doesnotestablishcolorselectionwithdistractors. Existinggenericcolorfeatures arenotproof oflearnedgeneralization. Notaprovenregressioncause; activefrozenstudyunchanged. Follow-upcoverage andlongcityconfirmation remainneeded. See docs/training/route-spatial-ppo-2026-11-25/COVERAGE.md; no private mapparameterscopied.


## 25 November 2026 — mini-task duration comparison completed

Both native-score branches completed the declared equal continuation budget from the selected saved policy; only small-city lesson duration differs. Fixed quarter/half/final practice and city evaluations completed. [Archived results](../docs/training/mini-task-horizon-2026-11-25/RESULTS.md). No automatic promotion or further training; inspect uncertainty and transfer before deciding the next step.


## Full duration comparison rejected for promotion — 2026-11-25T22:24:45.888869+02:00

Both arms completed262,144 added decisions from the same retained original. The shorter60-second practice arm finished at city mean106.19, scoring27/32; the longer300-second arm finished at98.47, scoring30/32. The original mean was126.09, scoring30/32. Both final mean-change intervals include zero, but neither meets the declared mean-score/skill readiness screen, and the short control also adds three zero games. No candidate is promoted or extended.

Longer lessons had a clear early advantage over the shorter control on these development games: +27.34 at65k and +29.94 at131k, with positive paired scenario-cluster intervals. That advantage did not survive the completed budget. The final long-minus-short difference is−7.72, interval[−30.66,15.41], which does not establish either duration as better at the endpoint. The long arm's own midpoint-to-final decline is−48.22, interval[−72.72,−22.59]. Do not convert the earlier midpoint gain into a claim that a longer run is now justified.

Final native mini results remain weak: tight routes7/16 short versus8/16 long, both-arrival service4/16 short versus2/16 long. More practice time inside an episode did not by itself establish reliable route/resource behavior. This does not prove that training longer can never work, or identify a single causal defect. One training seed per arm and repeated development review limit the inference; the bootstrap reflects scenario variation, not training-seed uncertainty.

A final long-arm replay was selected nearest the median paired score change across all32games, rather than selecting an improved case. Both policies first delivered at13seconds. The final model exhausted starting roads at29seconds versus135seconds for the original, made82 construction actions versus74, and ended with37 deliveries versus43. The inspected frames show excess branches after the opening. Later generated layouts diverge, so this is an illustration of behavior under matched seeds, not an identical-state counterfactual. It complements the earlier positive midpoint example; neither example replaces the full distribution.

All source, settings, quarter/half/final reviews, raw small measurements, replay traces and inspected figures are archived here. Both final models and all intermediate checkpoints remain local under `output/training/mini-horizon-comparison-01/`. Short final SHA:9064df1bf7805424fc730eb2c2add85140e63b463d6c8b503995065b0ae26d00. Long final SHA:3e7f76395fdf61a62c9cfbe48018f44ac4a61dc29d068f803b777120c358c413. No fresh confirmation cohort was consumed.

The separate road-encoder repair continues from its previously selected Wait01parent. This completed comparison does not change that running study or authorize an overnight launch.

See docs/training/mini-task-horizon-2026-11-25/INTERPRETATION.md,results.json,complete-learning-curves.png andfinal-city-replay/.


## Timely frozen spatial checkpoint review — 2026-11-25T22:27:07.212758+02:00

Read-only evaluation of the65,536-decision spatial checkpoint launched on the same64 consumed249M development games while its full262k budget continues. Output docs/training/route-spatial-run-2026-11-25/live-outcome-65536. TwoCPUworkers, nolearnerchange. The frozencontroller will repeat this plannedcheckpointreview aftertraining; that duplicate is not independent evidence and should match. Purpose: observe learning during the larger budget, not early promotion/stopping or new confirmation.


## Spatial study quarter review — 2026-11-25T22:32:00.664700+02:00

At65,536addeddecisions, frozenpractice successes20→23/32tight and25→26/32generous. Successeswithstockremaining remain6/32tight and21/32generous. Meanpaidunits tight7.34375 unchanged, generous10.09375→10.125. Smallcompletiongain onthisconsumeddevelopmentcohort, no demonstratedroadeconomygain, nativecityretentionunmeasured. Full262kbudgetcontinues. Rawdata/live-quarter-review.json under docs/training/route-spatial-run-2026-11-25/. Futurecontrollerrepeatofsamecheckpointisnotindependentconfirmation.


## Spatial study midpoint review — 2026-11-25T22:49:01.596861+02:00

At131072addeddecisions, tight21/32(initial20,quarter23), generous29/32(initial25,quarter26). Meanpaid tight7.34375 unchanged, generous9.90625versus10.09375initial. Clearestgainiscompletionwithsparestock, notyetreliableeconomicaltightconstruction. Full262kbudgetcontinues; cityretentionnotyetreviewed. Pairedoutcomeandremainingstockcounts in docs/training/route-spatial-run-2026-11-25/live-midpoint-review.json; sameconsumeddevcohort, notfreshconfirmation.


## Session evidence synthesis prepared — 2026-11-25T22:56:24.324651+02:00

Added docs/training/mini-task-repair-2026-11-25/SESSION_REVIEW.md consolidating completed studies, parents, measured transfer, decisions and limits. Spatial final remains explicitly pending. Prepared a post-completion economy review that separates successful stock retention from lower construction caused by failure, and verifies exact duplicate checkpoint evaluations without counting them as independent evidence. No active learner settings changed.


## Spatial route learning budget completed — 2026-11-25T23:32:08.401557+02:00

Completed 262,144 added decisions and15,945 episodes in5842.92 seconds. Final checkpoint SHA f8333fd9ff4ae46325bd675edbfc141288901740d28e654a94191c793fc97256. All32 per-rollout frozen-weight/Adam and finite checks passed. Frozen quarter/half/final practice reviews, native mini/city transfer and export now run serially; no further learning or promotion. Completion of learning is not evidence of readiness.


## Spatial final practice and native skill reviews — 2026-11-25T23:39:24.385778+02:00

Full-budget first-delivery cohort: tight27/32 versus20 initially; generous31/32 versus25. Successes with remaining stock6/32 unchanged tight,23/32 versus21 generous. Mean paid tight7.34375 unchanged, generous9.9375 versus10.09375. Clear completion gains on this consumed practice cohort, no reliable tight-stock economy improvement. Quarter/midpoint official game rows exactly reproduce the live reviews and are not independent evidence.

Native112-game review on the separate consumed mini cohort: adjacent/bend/clear16/16 each, obstacle12/16 versus parent14; tight9/16 versus8, generous14/16 versus11, first pair14/16 versus11, both pairs6/16 versus4. Obstacle retention, tight-route and both-pair readiness thresholds fail. City review pending. Do not open reserved confirmation or promote based on the practice gain.


## Spatial outcome replay review — 2026-11-25T23:43:37.072778+02:00

Four initial/final paired traces exactly reproduce the selected gained and retained success counters. On the gained tight example, disconnected parent roads become a continuous final route with the same9 edits and zero stock. The retained generous example becomes visibly straighter with the same6 edits and6 stock left. No formerly successful cases are lost on this64-game practice cohort, so no lost-success replay exists. These are favorable geometry examples, not evidence of population-wide road savings.

Added a separate post-result diagnostic: the lowest-key remaining final failure (seed 249000002, action RNG 641002). Both parent and candidate expend all stock and make11 edits without service; the final leaves a gap near the home after extending in the opposite direction. This illustrates unresolved resource allocation despite improvement elsewhere. Both traces verify exactly. Sources, selection rules, frames and inspected figures are under route-spatial-run-2026-11-25/outcome-replays andremaining-failure-replay. A clipped first figure render is retained; corrected figure inspected. No training changes or reference route targets.


## Spatial study completed: no overnight promotion — 2026-11-25T23:49:11.504161+02:00

All learning, native reviews/export, final integrity checks and selected practice/city replays completed. Final city128.25,28/32scoring versus Wait01parent141.09375,31/32. Paired change−12.84375 CI[−40.96875,10.40625]; versus original+2.15625 CI[−24.87578,30.3125]. Mean-change uncertainty does not erase the practical zero-game/skill retention failures. Four development gates fail (obstacle retention, tight routes, both pairs, city zeros); original mean threshold alone passes. No fresh confirmation or overnight launch. Final route checkpoint preserved as useful practice learning, not promoted city strategy.

Representative city replay nearest median paired change: parent176→final171, firstdelivery31→30s, firststockout65→130s, builds98→112, finalstock43→19. Exact counters reproduce; bothreach600s. Inspected frames retain extra construction and laterlayouts diverge. Not a uniform timing regression nor a clean economy gain. All artifacts and interpretation in docs/training/route-spatial-run-2026-11-25; whole-session synthesis in mini-task-repair-2026-11-25/SESSION_REVIEW.md.

Recommended follow-up is a bounded retention-aware combination of affordable routes, obstacles and later arrivals, after reward/critic compatibility checks. Earlier mixed curricula failed, so this remains a proposal, not a verified remedy. All authorized bounded studies now reviewed; no learner remains active.


## Publication preparation — 2026-11-26T00:36:00.286109+02:00

User requested push of the current project. Local Maskable-PPO starts at6bd7f71 with accumulated source and archived experiment work. Remote is84d209b (older cloud-continuation documentation); fetched metadata without pulling or resetting files. Preserve both histories and reconcile documentation before a normal non-force push. Pending source/archive scan found no model-weight/generated-binary extensions or credential-pattern hits; ignored checkpoints, runtimes and private reference directories remain local. Training Python source syntax and tracked diff whitespace checks pass. No training launched. Publication outcome will be verified against the remote ref.


## Publication reconciliation — 2026-11-26T00:37:10.962442+02:00

Committed local work as74820ad, preserving all existing source and archived evidence. In an isolated temporary worktree, merged remote84d209b without force or reset. Four documentation overlaps resolved by retaining both histories and adding current precedence to the cloud entry point; no simulator/trainer source changed during reconciliation. Training syntax checks and the task-reporting unit test pass. Credential-pattern scan found no hits among pending files; weights/binaries/private reference directories remain excluded. Git author identity was absent locally, so commit commands used the existing branch publication author identity without changing global configuration. Push and remote-head verification follow.
