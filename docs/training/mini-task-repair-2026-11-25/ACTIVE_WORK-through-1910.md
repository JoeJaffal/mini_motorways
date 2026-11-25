# Latest status — 25 November 2026, 18:59 Beirut

Focused run01 is COMPLETE, all fixed/broad-mini/city reviews done. Fixed success5→12→15→24/32; broad short skills retained, tight8/16 unchanged, generous12/16 vs8, bothpairs3/16 vs5. City129.25,31/32: no clear change against parent135.78 or original126.09. Learning curve and exact selected success/failure replays inspected. Archive ../mini-fixed-route-2026-11-25/ includes results, transfer-review, final-checkpoint-integrity, learning-curve and final-replay. No promotion.

**New live focused continuation02**, controller877049, output/training/mini-fixed-route-02. Another65536decisions on the SAME board with unchanged native reward/settings; total focused131072. Started18:58:36, preserving finalrun01 weights,753664lifetime decisions and22Adam states10240. Source unchanged; new episode/RNG process, not bit-exact trajectory continuation. Strong fullcurve improvement supports more practice before changing reward. Reviews16k/32k/64k then112mini/32city; target29/32fixed, then fresh actiondraws623000–623031 (unused) before varied layouts. Archive ../mini-fixed-route-continuation-2026-11-25/README.md. Monitor tail -F /home/mohammadjaffal/mini_motorways/output/training/mini-fixed-route-02/run.log. No automatic extension/promotion/overnight.

**Other live study unchanged:** duration comparison807935, long-window last published180224/262144, followed by matchedshortcontrol262k. Midpointcity146.69 positive development gain; final/control pending. Exact selected positive city replay shows opening service improvement but excess roads/finalfailure, in ../mini-task-horizon-2026-11-25/midpoint-city-replay/. Do not call this conservation or generalized strategy. Both studies still need completion/review; continue work, do not stop simply because jobs are backgrounded.

Wait correction logits are frozen in focused candidate; actual Wait probability can still change through road-logit normalization. Native300-second score on one fixed board does not inherently punish harmless extra roads. Broadertight/pair and freshcity gates remain unmet. Reserved236M/237M confirmation unused. Original reference retained; no overnight run. Legacy negative-pair fixture names in historical pair_ppo.py are absent from currentnative curriculum allow-list (source inspection only); current112mini audit does not certify those cases. No compatibility change made.

Earlier detailed notes below are historical where superseded by this section.

# Active work — 25 November 2026, 18:12 Beirut

User approved flexible-duration mini-task repair toward a justified overnight launch. Continue reviewing learning/behavior and fixing issues; do not declare readiness from a high sampled score. No planner/new imitation. Preserve all dirty files/checkpoints. Authoritative checkout `/home/mohammadjaffal/mini_motorways`, branch `Maskable-PPO`; Desktop/main untouched. No subagents authorized.

## Live work: two learners

**Duration comparison**, controller807935, `output/training/mini-horizon-comparison-01`. Original retained parent,300-second lessons first then matched60-second control,262144added decisions per arm. Source/runtime frozen. At131072midpoint: city146.6875 versus126.09375 original,31/32scoring; pairedgain+20.59375 CI[2.4375,40.375]. Tight9/16,generous11/16,firstpair11/16,both3/16. Shortskills retained. Positive development movement, but task gates unmet; final/control/fresh confirmation pending. Archive `../mini-task-horizon-2026-11-25/`.

**Focused repeated hard connection**, controller859857, `output/training/mini-fixed-route-01`, launched18:09.65536added decisions,16workers×512steps×8rollouts. One empty native training fixture232000001 (distance7,stock8), selected as lowest previously successful bank-collection seed outside6-cell specialist range. No road prefix or teacher action. Initial32action draws:5successes,mean2.8125. Same300-second native score/termination. Wait frozen; critic input detached; learned road/critic weights andAdam8192preserved. Cache andfasttail enabled after exact/native/PPO checks. Fixed16k/32k/64kreviews; final112mini and32cityretention. Archive `../mini-fixed-route-2026-11-25/`. Practical fixed-layout target29/32; then new action draws before broader layouts. One-layout success is not city/generalization evidence. Do not auto-promote or start overnight from it.

Monitor with `tail -F /home/mohammadjaffal/mini_motorways/output/training/mini-fixed-route-01/run.log` and the analogous duration log. Initial progress prints after a complete rollout. Keep at most two production learners and two CPUworkers per evaluator.

## Completed comparison — recovery DONE

Reset/cold comparison776266 is **complete-recovered**. Both arms262144decisions, all12evaluations andcheckpoint hashes verified. The known first65k replay-template failure was recovered without training restart; original error preserved in controller-final-error.json. `recover_comparison.py` has already run successfully: DO NOT run again. Final cold city115.25,29/32 (delta−10.84CI[-36.22,14.84]); reset89.25,24/32 (delta−36.84CI[-61.66,-15.16]). Both tight8/16; laterpairs cold3/16/reset2/16. Neither promoted. RESULTS.md/results.json contain full curves.

## Prepared candidates and evidence

Wait-restored parent `output/training/mini-reset-wait-repair-01/start.zip`, SHA edb2a26da557f6d3d41a51ca64d62d0bdde8423572e84e78039a80cc43083aa5. All non-Wait weights and22namedAdamstates retained at8192steps; original zero-output Wait modules restored/frozen. Actual32-city run135.78125,30scoring exactly matches the probability-component diagnostic. Gain over original uncertain.300-second mini: tight8/16,generous8/16,bothpairs5/16 vsoriginal3; shortskillsretained. Four selected replays exact; plots visually inspected. One gained pair has two functioning colored routes but still a stray fragment; tightcase remains disconnected atstock0. Evidence `wait-repair/`.

Focused-run parent `output/training/mini-road-detached-initial-01/start.zip`, SHA7582e285e3f6b2b44487cf3fe86156169aa80d79272dccbe21dc408fed0bf324. `CityRoadChoiceDetachedCriticPolicy` changes only critic gradient flow, not forward outputs or Adam state. Value head still learns; this is NOT a separately learned critic encoder.12shared-state outputs bitexact;384component checks passed. Value-only update touches onlyvalue_net, actor gradients still reachroads/spatial, nativeGPUresume128decisions/4updates passed. Original candidate retained; smoke checkpoints excluded.

Motivation:16-game/256choice-state frozen300-second probe found opposing actor/value encoder gradients in5/7nondegenerate batches. Two pair batches project−0.94relative to actor. This is not actual PPO/Adam causal proof. The critic was trained with different Wait behavior and60-second lessons, so stale values can reflect changed policy/return targets. Primaryresearch andlimits in critic-detach/PLAN.md.

Broader `run_mini_road_continuation.py` is prepared but **not launched**; defer pending focused learning results.241Mtraining range remains unused. New repeated-fixture module and optional trainerflag preserve existing defaults. Both active runtimes are frozen snapshots.

## Readiness / next actions

Follow focused checkpoints and broader retention; inspect solved/failed play and actual optimizer changes. Follow full duration curve and its shortcontrol, without stopping early for one low score. If fixed task masters29/32, verify new action draws and expand training layouts; do not mistake memorizing a board for strategy. Further bounded continuation only with documented reason and existing progress preserved.

Development gates remain tight14/16,bothpairs8/16, shortskillsretained, citymean at leastoriginal and no morethan1extra zero. Freeze candidate before freshconfirmation. `CONFIRMATION_PLAN.md` specifies32mini layouts/family236000000–031 (targets28/32tight,16/32both),32cities237000000–031×2RNGs600seconds (target20percentmean gain withpositivepairedCI,atmost2extra zeros),8othercities237001000–007×2RNGs1800seconds for longer-play check. NONE run. No overnight session or promotion yet.

Consumed: dev231Mmini,184M/185Mcities; bank232M(includingfixedtrainingseed), cold233M; smoke235M; longdiagnostic238M; traffic239M; durationtraining240M. Original reference start.zip SHA7eb605e4e465b9143e095e367abe0a01285b8ace05843aaac80bd48b5f049027.

Current action interface remains connection/Wait, native legal bridges. Weeklychoice is environment max-roads rule, not learned; no directdemolition/rotation/motorway/roundabout/lightactions. Do notclaim full tool strategy. Weights/binaries local-only. Durable history/records in training/EXPERIMENT_HISTORY.md and these archives. Prior active notes preserved in ACTIVE_WORK-through-1718.md and ACTIVE_WORK-through-1809.md.


## Focused connection midpoint, 25 November 18:30 Beirut
Measured: at32768added decisions the fixed board succeeds15/32 (initial5,quarter12); gained11 and lost1 draws against initial. Checkpoint SHA8601e00f53432f0b951e46cc6c8e7cca6d629cd30844a9eec2ea68b75adaa658. Positive movement, still below29/32mastery; declared65536budget continues unchanged. Same training layout/action draws, not geometry generalization. Evidence docs/training/mini-fixed-route-2026-11-25/evaluation/fixed-32768 and midpoint-review.json.
Quarter selected newlysuccessful replay622005 is exact: functionalroute butstrayfragment. Source/frames/plot in focusedarchive quarter-replay. Duration midpoint pairedcityreplay under way; no learnerchange.
