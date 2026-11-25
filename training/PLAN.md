25 November 2026, 23:49 Beirut: all bounded mini-task studies and reviews complete; no training active. Spatial PPO improved first-delivery practice20→27/32 tight and25→31/32 generous, but native obstacles regressed, tight routes9/16, both pairs6/16, and city128.25/28scoring versus parent141.09/31. Development readiness fails; no overnight run or fresh confirmation. Checkpoints preserved. [Session review](../docs/training/mini-task-repair-2026-11-25/SESSION_REVIEW.md); [final findings](../docs/training/route-spatial-run-2026-11-25/INTERPRETATION.md); [current handoff](../docs/training/route-spatial-ppo-2026-11-25/ACTIVE_WORK.md). Entries below are historical.

25 November 2026 22:25 EET: duration comparison complete; neither arm promoted (final city106.19 short,98.47 long, original126.09). Only spatial road study PID947374 remains training toward262144decisions. No overnight readiness or launch. [Active work](../docs/training/route-spatial-ppo-2026-11-25/ACTIVE_WORK.md); [duration findings](../docs/training/mini-task-horizon-2026-11-25/INTERPRETATION.md). Earlier entries historical.

25 November 2026 21:54 EET: route-head study rejected (city122.50,27/32scoring vs parent141.09,31/32). Broader road-encoder PPO launched PID947374 from retained Wait01,262144boundeddecisions; separate frozen Wait representation, same practice reward. Duration short control continues. No overnight launch. [Active work and monitor](../docs/training/route-spatial-ppo-2026-11-25/ACTIVE_WORK.md). Older entries historical.

25 November 2026 21:06 EET: bounded varied-route PPO study launched, PID927046,65536decisions from Wait01. Freeze learned Wait/shared encoder; actual delivery plus bounded efficiency bonus; no planner. Native city reward unchanged. Duration comparison short control continues. No overnight launch. [Active work and commands](../docs/training/route-outcome-ppo-2026-11-25/ACTIVE_WORK.md). Earlier entries historical.

25 November2026,21:01Beirut: Wait02 completed98k total practice; mini restraint improves but city141.09→120.84, paired CI excludes zero. Not promoted; diagnosing exact city failure. Wait01 retained. Duration long arm final98.47 regressed from midpoint146.69; matched short control continues. Route-outcome lesson is preparation only; no overnight launch. [Evidence and current work](../docs/training/build-wait-continuation-2026-11-25/INTERPRETATION.md). Older entries historical.

25 November2026,20:15Beirut: first32kWait-only PPO repair complete. CorrectfirstWait improves but repeatedstopping stillfails; nativepositive/shortconnectionsretained. City141.09vs129.25parent,31/32scoringboth; gainuncertain, outside-routeunitslower. Unchanged65,536decisioncontinuation PID905893 launched from verifiedfinal, output/training/build-wait-02. Longer-lessoncomparison PID807935 continues. No overnightpromotion. [Current work and monitor](../docs/training/build-wait-continuation-2026-11-25/ACTIVE_WORK.md). Older entries below historical.

25 November2026,19:52Beirut: focused continuation completed; fixed-board32/32familiar,29/32fresh action draws, but city107.47/27scoring fails retention versus preceding129.25/31. Preserved final, selected earlier run01final for bounded build-or-Wait PPO. New run PID896687,32,768decisions, output/training/build-wait-01; only8Wait parameters learn binary action-group reward, road/critic weights and Adam retained. Native city reward unchanged. Longer-lesson comparison PID807935 continues. No overnight launch or promotion. [Current work and criteria](../docs/training/build-wait-ppo-2026-11-25/ACTIVE_WORK.md). Older entries below are historical.

25 November 2026, 18:59 Beirut: first focused connection run complete, success5→24/32 but no clear full-city gain. Another65,536 unchanged practice decisions launched from its verified final weights/Adam, PID877049, output/training/mini-fixed-route-02. Separate lesson-duration comparison continues. No overnight run or promotion. [Current work, evidence and monitor commands](../docs/training/mini-task-repair-2026-11-25/ACTIVE_WORK.md). Older entries below are historical.

25 November2026,18:12Beirut: reset/cold comparison completed and explicitly recovered its known export error; neither candidate promoted. Longer-lesson comparison remains active with a positive131k city development gain (~16percent) but unresolved hard tasks. Focused one-board PPO practice launched18:09,PID859857,65536decisions, retained road/Adam progress, frozen Wait and detached critic input; no overnight run. [Current work, commands and next checks](../docs/training/mini-task-repair-2026-11-25/ACTIVE_WORK.md). Older entries below historical.

25 November2026,17:49Beirut: two original comparisons continue; cold-control nearing completion and longer lessons nearing midpoint. Wait-restored checkpoint review completed: city135.78 versus original126.09 (gain uncertain), tight8/16, bothpairs5/16; short skills retained, readiness screen failed. A further candidate preserves these outputs/Adam while preventing critic-loss updates to road features; migration, gradient-isolation and GPU resume checks passed. It is prepared, not training. Next: review fixed comparison results, recover known reset-study export error after all work ends, then decide bounded road continuation. No overnight run or promotion. [Live handoff](../docs/training/mini-task-repair-2026-11-25/ACTIVE_WORK.md). Older entries below historical.

25 November2026,17:20Beirut: reset-curriculum arm completed and failed city retention; its matched cold control continues. Longer300-second lesson study continues (early city improvement uncertain; task gates unmet). A separately saved Wait-restored checkpoint preserves learned roads/Adam and passed migration checks; frozen mini evaluation running, no new learner or promotion. No overnight run launched. [Current work and recovery instructions](../docs/training/mini-task-repair-2026-11-25/ACTIVE_WORK.md). Older entries below historical.

25 November2026,15:52Beirut: two bounded studies active on Maskable-PPO. Reset curriculum vs cold control PID776266 continues unchanged. Separate60/300-second lesson comparison PID807935 starts from retained original,262144decisions/arm, native reward only; long-window runs first. No overnight session or promotion. [Duration design and monitor](../docs/training/mini-task-horizon-2026-11-25/README.md); [active work/recovery details](../docs/training/mini-task-repair-2026-11-25/ACTIVE_WORK.md). Older entries below historical.

25 November 2026, afternoon: reset-curriculum comparison remains active on Maskable-PPO, PID776266. The131072-decision midpoint has not improved city transfer (100.06 versus retained original126.09). The declared262144decisions/arm and cold control are still running; no promotion or overnight launch. Optional300-second lessons passed exact-native/default-parity and disposable PPO/cache reload checks; production duration comparison is prepared but unlaunched. See [active work](../docs/training/mini-task-repair-2026-11-25/ACTIVE_WORK.md). Older entries below remain historical.

Mini-task reset comparison launched25November2026 after exact replay and PPO smoke checks. Eight city workers retained; four of eight lesson workers use policy-generated initial states, no action targets.262144decisions/arm with fixed empty-board/city reviews. PID776266. Monitor: tail -F /home/mohammadjaffal/mini_motorways/output/training/mini-reset-comparison-01/run.log. Archive: docs/training/mini-task-repair-2026-11-25/. No promotion or overnight continuation yet. Older entries below historical.

Mini-task behavioral audit and repair approved25November2026; flexible timing, target overnight launch by midnight conditional on readiness. Prior expansion comparison complete, no city gain over original and no promotion. Current audit uses frozen original/expansion policies on7task families with native Wait. See docs/training/mini-task-repair-2026-11-25/README.md. Older entries below are historical.

Native-score expansion comparison launched25November2026 on Maskable-PPO. Twelve exact replays show opening failures and rapid post-award stock exhaustion; reward accounting is correct, so native delivery rewards are retained. From the preserved original, compare city-only versus8city+4later-pair+4single workers with within-task advantage normalization;262144added decisions per arm. Four tests/two smoke reload checks passed; no planner/imitation/simulator change. Live status: output/training/expansion-comparison-01/status.json. Monitor: tail -F /home/mohammadjaffal/mini_motorways/output/training/expansion-comparison-01/run.log. Fixed practice/city evaluations run automatically; no promotion/extension. See docs/training/city-transfer-diagnosis-2026-11-25/README.md. Launch status only; consult live status for results. Older entries below are historical.

Overnight comparison completed25November2026 at05:26Beirut. No training remains active. Practice-only and mixed-city continuations each reached524288cumulative decisions. City development means: original126.09, starting practice candidate86.97, lesson-only107.44, mixed-city99.16. Both continuations score in30/32games versus27/32at their start, but all paired score-gain intervals include zero; neither demonstrates an improvement over the original. Mixed training also loses some single-connection practice success. Preserve all saves and retain original as reference; no promotion or new run. See docs/training/overnight-learning-2026-11-25/RESULTS.md. Older launch entries below are historical.

Overnight transfer comparison launched25November2026 after the requested half-hour follow-up. Previous road-cost run improved generous-stock practice but regressed in city development play; original model retained. New bounded run compares lesson-only with8city+8practice workers from the same saved262144policy, reaching524288each; optimizer settings unchanged, road cost confined to practice. Mixed resume smoke passed after fixing missing stock_initial reporting. Live status: output/training/overnight-transfer-comparison-01/status.json; monitor: tail -F /home/mohammadjaffal/mini_motorways/output/training/overnight-transfer-comparison-01/run.log. Automatic fixed-checkpoint evaluation/reporting, no automatic promotion or further extension. See docs/training/overnight-learning-2026-11-25/README.md. This records launch, not completed results; consult live status. Older entries below are historical.

Matched road-cost continuation launched25November2026 on Maskable-PPO. Two original16384-decision checkpoints continue with Adam preserved toward262144decisions/arm; no reward/architecture change. Frozen diagnostics and two resume smoke checks passed. Live status: output/training/road-cost-continuation-01/status.json; monitor: tail -F /home/mohammadjaffal/mini_motorways/output/training/road-cost-continuation-01/run.log. Six fixed development evaluations and archival summary run automatically; no promotion or automatic extension. See docs/training/road-cost-continuation-2026-11-24/README.md. This is launch status, not a result; consult live status for completion. Older entries below are historical.

Research review complete (24 November 2026): keep PPO; latest16k reward trial remains inconclusive, while historical overnight learning and later regressions are both documented. Next recommendation: audit joint-action entropy, effective actor updates and critic calibration, then a stable matched control/.04 continuation with checkpoint curves. Proposed262144decisions/arm; not launched or implemented. No policy/simulator changes. See docs/training/ppo-research-review-2026-11-24/REPORT.md. Older recommendations below are historical.

Road-cost short pilot complete; effectiveness INCONCLUSIVE at16,384decisions/arm. User correctly challenged premature judgment; no convergence shown. Costs0/.01/.04 pass reward/native checks; generous success44/44/45 per64 versus parent46, with no spending decrease or no-build collapse. Preserve checkpoints/Adam for longer matched control/.04 comparison; proposed100k–250k cumulative/arm, duration not selected and no extended run started. See docs/training/road-cost-reward-2026-11-24/RESULTS.md. Older entries below are historical.

Small-city service experiment complete on Maskable-PPO. Easy pairs already64/64; easy pilot stopped with8192-decision checkpoint preserved. Offset trial completed32768 decisions/1024 updates/882episodes; separate-layout both9/32 unchanged, first20→17/32, outside-route units8.34→9.25. Fresh city means121.53→123.53,29/32scoring both, paired95%CI delta[-16.84,20.72]: no reliable gain. No promotion, no long run; all jobs ended. Next proposed test: one longer offset connection with tight versus generous stock, before restoring second arrivals. See docs/training/small-city-service-2026-11-24/RESULTS.md. Older entries below are historical.

Road-choice-only diagnostic complete on Maskable-PPO: 32,768 decisions, 1,024 Adam updates, 64 episodes. Frozen Wait verified; conditional-road changes increased but no reliable score gain. Repeated mean128.81 vs reference126.25; separate122.25 vs125.94. Opening probe26/32 scoring vs27/32. No promotion, no joint continuation, no long run; all jobs completed. Next proposed test: bounded road-head learning-rate comparison with frozen Wait and native rewards. See docs/training/city-road-choice-2026-11-24/RESULTS.md. Older entries below are historical.

Whole-city observation/training diagnostic complete:3 bounded32k trials (98,304 decisions,3,072 optimizer updates,195 episodes). Reference repeated/separate600s means126.25/125.94;gated101.88/115.38;whole129.50/133.75;finite121.50/116.44. No reliable reference gain,no promotion,no long session. Selected replay0→175 does not improve32-RNG opening reliability (27/32 both). All jobs ended;checkpoints preserved. See docs/training/city-whole-policy-2026-11-24/RESULTS.md and compare-play.html. Older entries below are historical.

The [road reserve experiment](../docs/training/road-reserve-learning-2026-11-23/README.md) is complete on Maskable-PPO. One 8,192-decision PPO pilot improves held-out future-connection success from 2/16 to 13/16 and stock at arrival from 1.06 to 3.0 roads. A separately saved feature repair fixes excessive waiting when local progress is absent. Nevertheless, final fresh city means are 54.97 versus calibrated parent 81.88, both 23/32 scoring (paired difference −26.91, 95% interval [−43.50, −11.81]). Reject both new city candidates and retain prior checkpoints. No training/evaluation is active; no overnight run is recommended. Next proposed work is mixed-city conservation versus prompt expansion, with wider stock and route conditions. All older status/launch paragraphs below are historical.

The [five-stage city learning program](../docs/training/five-stage-city-learning-2026-11-23/README.md) completed all eleven bounded PPO runs and independent checks on the user-confirmed `Maskable-PPO` checkout. Best city candidate is inference calibration only: independent mean82.13 versus original63.53, both26/32 scoring. The calibrated PPO demand candidate scores67.44; it passes32/32 urgent-demand cases but does not establish better city retention (and loses one scoring development city). Longer-route completion improves5/16 to16/16 from calibration; quiet stock conservation remains unsolved. Keep the original protected425984 checkpoint as rollback and both candidates separate; no automatic promotion or overnight run. No jobs remain active. Next: a bounded waiting/stock lesson with later native delivery consequences and fresh city retention. All older status/launch paragraphs below are historical and superseded where they conflict with this report; the branch question is resolved.

The [opening regression repair](../docs/training/city-regression-repair-2026-11-23/README.md) completed a 12,288-decision bounded pilot. It preserves the retained opening actor until visible service is established. Three selected regressions now score 14, 4 and 156; the paired 16-city mean is 96.56 versus 90.19 at start, with 15/16 scoring each and an uncertain gain. Final is a repair candidate, not a proven high-score promotion. No training is active. Next: reconcile the supplied `mohammad` instruction with this existing `Maskable-PPO` checkout, then bounded stability and a larger predeclared comparison before another long run. Older launch instructions below are historical and are not the current recommendation.

The [learning audit and guarded long-run preparation](../docs/training/city-learning-readiness-2026-11-23/README.md) enabled the spatial road actor and tested three learning rates. The 0.000001 midpoint retained performance on 24 fresh cities, averaging 111.29 versus 110.46 with 23/24 scoring cities each. A guarded eight-active-hour command is ready for the user. The long run has not started.

The [network service repair and bounded pilot](../docs/training/city-network-service-pilot-2026-11-23/README.md) completed. Three feature defects are corrected in a separately loadable policy. All 69 tests pass. The final improved the small city mean, while controlled route success matched initialization. Keep the final as an experimental candidate. The next hypothesis is a richer trainable destination-to-edge interaction. No training is active.

The [city policy gap audit](../docs/training/city-policy-gap-audit-2026-11-23/README.md) completed the independent city comparison and identified the next proposed gate. Correct visible road components and target-specific progress, then test affordable joins against distractors before returning to longer city training. Demand priority, congestion, weekly choices and additional tools follow with separate native controls.

The [midgame service experiment](../docs/training/city-midgame-service-2026-11-22/README.md) verified waiting for a visibly blocked approach in the controlled case. Generalization to new service opportunities in a growing city and reduction of full-city road waste remain open.

The [opening route repair](../docs/training/city-route-repair-2026-11-22/README.md) cleared its fresh short, long and delayed tests and improved the paired full-city evaluation. Whole-network road waste, longer horizons and other tools remain open.

The [short, long and delayed route pilot](../docs/training/limited-route-ppo-2026-11-22/README.md) improved short-route completion and delayed spending but left longer route assembly unresolved. Progressively remove provided road sections while testing ordinary-city retention.

The [road spending audit](../docs/training/city-road-spending-audit-2026-11-22/README.md) points to a controlled exercise for completing matching service routes and timing expansion. The frozen higher-Wait ablation reduced scoring on fresh cities, so carrying stock alone is insufficient.

The [mixed hard-opening continuation](../docs/training/city-opening-pilot-2026-11-22/README.md) ended with little hard-opening gain and lower ordinary-city scores. The proposed next timing experiment should isolate saving and spending stock while retaining existing road construction behavior.

The [road-only diagnostic](../docs/training/city-road-diagnostic-2026-11-22/README.md) prioritizes retaining stock until a valid opening route is possible and bringing newly spawned destinations onto the network. The proposed next step is a bounded score-only continuation on fresh development and training cities.

The [eight-hour city experiment](../docs/training/city-overnight-results-2026-11-22/README.md) is complete. The 6,234,112-decision checkpoint is the road-only reference, with verified improvement on the reserved Los Angeles seeds. Longer-horizon and other-map transfer, weekly choice and additional tools remain open.

The [eight-hour city launch command](../docs/training/city-overnight-launch-2026-11-22/README.md) is prepared and smoke-tested. After learning, compare regular checkpoint candidates on development seeds and evaluate the selected candidate against the starting reference on the reserved suite.

The [actual CUDA PPO worker comparison](../docs/training/city-ppo-worker-benchmark-2026-11-22/README.md) selected 32 native workers for the overnight setup. It averaged 256.9 decisions/s across the two bounded trials. The overnight duration and score checks remain separate from this short throughput measurement.

The [growing-city replay](../docs/training/city-road-preflight-2026-11-21/README.md) now passes through the road-only adapter. The [starting policy](../docs/training/city-policy-start-2026-11-22/README.md) is selected. The [frozen baseline](../docs/training/city-frozen-baseline-2026-11-22/README.md) is complete on 32 fresh seeds. The [bounded score-only pilot](../docs/training/city-score-pilot-2026-11-22/README.md) completed with both checkpoints retained. Keep the frozen start as reference and use the measured worker setting above.

The [pre-surge timing study](../docs/training/wait-before-surge-2026-11-21/README.md) verified waiting and conditional spending from second 15, including a median five-second adjustment to a later surge. The next open gate is reliable cold-start and longer-horizon timing before larger growing-city experiments.

The [road-end transfer study](../docs/training/road-end-transfer-2026-11-21/README.md) passed for the supplied junction family. The selected policy chooses the feeder in light traffic and closes the bypass in multiple unseen gap positions in heavy traffic. The next proposed test starts before the surge and verifies whether the agent saves its available road unit when information is incomplete. Full bypass construction and larger evolving networks remain distinct milestones.

The [frozen geometry check](../docs/training/junction-transfer-2026-11-21/README.md) confirms relocated-gap transfer is still open. The next proposed pilot uses visible road ends and multiple bypass gap positions, with a combined geometry held out and an original-junction retention check. Waiting before the surge and integrating the traffic and priority skills remain subsequent gates.

On 21 November 2026 the [demand priority and traffic work](../docs/training/traffic-milestones-2026-11-21/README.md) verified three serviceable destinations with two units, two-unit shared-versus-bypass construction and one-unit allocation after a live surge. Test transfer to a relocated bypass gap, the decision to Wait before the surge and joint use of priority and congestion with the preserved partial checkpoints. User direction remains native score, legal individual edits and observation of vehicle movement. Once these behaviors transfer, the next larger scenario is a growing city with several developing service networks.

Earlier (20 November 2026): Use the [bounded reward-only PPO session](../docs/training/reward-only-construction-hour-2026-11-20/README.md) for the previous selection and evidence. Independent stock-only clear-road verification is complete. The next curriculum priority is reliable full-build routing with competing buildings, with separate gates for hard shifted barriers and elapsed-time score. Keep local specialist checkpoints available for comparison.

Earlier (20 November 2026): Preserve the [early spare-stock checkpoint](../docs/training/reward-only-spare-stock-2026-11-20/README.md#outcome-and-the-edit-limit-finding) for stock-limited construction. The next verification is independent clear-land layouts using the stock-only allowance. Use the prior 66/100 checkpoint as the strict edit-cap reference.

Latest (20 November 2026): The [clear-land PPO gate](../docs/training/reward-only-clear-roads-2026-11-20/README.md#completed-pilot) remains unmet at 66/100. The next proposed focus is the two-tile lateral offset, with earlier skills rehearsed.

Latest (20 November 2026): The [reward-only shared-edge PPO track](../docs/training/reward-only-bend-ppo-2026-11-20/README.md) has verified adjacent gaps and unfinished bends. The imitation checkpoint is a separate diagnostic; other construction skills remain unverified on the PPO track.

Latest (20 November 2026): All [five authorized construction exercises](../docs/training/construction-five-stage-2026-11-20/README.md) passed. Autonomous Build-or-Wait and broader layout families are separate work.

Latest (19 November 2026): User authorized the [shared local action scorer](../docs/training/shared-edge-policy-2026-11-19/README.md). The first pilot has started with the existing one-build layout and reward. Compare held-out orientation accuracy and board matching after it finishes.

Latest (19 November 2026): The user chose to improve [one-build repair accuracy](../docs/training/one-gap-single-build-results-2026-11-19/README.md#user-decision-after-the-evaluation) with the current gap placement before diversifying layouts.

Latest (19 November 2026): The user approved [one-build practice with immediate binary reward](../docs/training/one-gap-single-build-2026-11-19/README.md). Implementation and no-training verification are complete. Any pilot still requires separate authorization.

Latest (19 November 2026): [Approved introductory plan](../docs/training/one-gap-direct-2026-11-19/README.md) is implemented. Direct new connections or Wait, native trip reward, and frozen initial/trained/uniform comparison. Next milestone is a separately authorized bounded pilot, then evaluation on the 100 held-out layouts. The earlier hierarchy plan below applies to the historical introductory setup and broader curriculum.

Latest: the bounded Stage1runner/update/checkpoint implementation now exists and passes forward-only preflight checks. See [launch preparation](../docs/training/stage1-launch-preparation/README.md). Actual weight updates and Linux-PC verification remain untested; no training has run or is authorized. Older implementation-next wording below is historical.

# What we are doing

**Goal: teach a fresh model to play against Mohammad.**

## What is agreed

The manager chooses a focus; the executor makes each individual edit itself.
No road planner or automatic connection building. Edits happen while paused,
waiting is an explicit choice, and only scored trips give reward.
We start with a small practice game and expand difficulty when evidence supports it.

## What is now in place

- Linux software setup was verified from your terminal outputs, including GPU access.
- The first practice game exists: one house and matching destination, varied layouts.
- The model's allowed observations, Stage1 physical action masks and separate
  manager/executor heads are implemented and checked.
- Focus changes, cancellation, paused edits, waiting, endings and errors have checks.
- Replay recording and verification, frozen evaluation/review selection, and
  no-learning collection/credit calculations are available.
- The first100scripted layouts meet the timing target. This is feasibility,
  not a learned result. A complete scripted example replays exactly.

## Next

Finish the actual PPO update integration and explicitly resolve its remaining
hierarchy return/trace and entropy/level-weight choices. Then transfer these
changes to the Linux PC and use the no-training benchmark to choose worker,
batching and CPU/GPU settings from that machine's evidence.

**No training sessions are authorized.** No learned model exists yet. Any future
pilot needs your explicit instruction and a bounded budget. Do not start the
historical trainers below older documentation.

The approved first gate remains180simulated seconds; at least90of100held-out
layouts each complete at least3scored trips. Paused edits cost no game time.
Operational interruptions do not count as completed attempts. The scenario's
20road inventory, layout ranges and event suppression remain documented,
provisional engineering choices, not new user-approved game rules.

Current implementation is in the cloud Maskable-PPO checkout, not yet installed
on the Linux PC or pushed. [One-hour implementation report](../docs/training/check-in-2026-11-16/README.md).
[Decisions](../docs/training/DECISIONS.md) preserve approval/review precedence;
[handoff](HANDOFF.md) and [history](EXPERIMENT_HISTORY.md) preserve continuation.
