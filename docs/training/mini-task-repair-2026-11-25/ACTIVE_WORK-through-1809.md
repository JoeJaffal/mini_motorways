# Active work — 25 November 2026, 17:49 Beirut

User approved the mini-task audit/repair plan and flexible timing. Continue through bounded comparisons, behavior review, necessary repairs and a readiness decision. Launch overnight only if evidence supports readiness; a deadline is not evidence. No planner or new imitation. Preserve all files/checkpoints and uncommitted work. Authoritative checkout `/home/mohammadjaffal/mini_motorways`, branch `Maskable-PPO`; Desktop/main untouched. No subagents authorized.

## Running studies

1. `output/training/mini-reset-comparison-01`, controller PID776266. Reset-curriculum arm completed262144 added decisions. Cold control continues the same budget (about147k at17:18). Final reset city score89.25 vs original126.09; six additional zero-score games. Tight connection8/16, later pair2/16. No promotion. Full evidence in this archive.
2. `output/training/mini-horizon-comparison-01`, controller PID807935.300-second lessons first, then matched60-second control;262144 decisions each from original. Around90k at17:18. First65k city137.53 vs126.09, but paired uncertainty includes zero. Tight8/16, both pairs4/16. Full curve/control pending. Archive `../mini-task-horizon-2026-11-25/`.

Both studies use native score. Both future evaluation pools are limited to2CPUworkers; training source unchanged. Only duration study uses validated per-forward frozen-computation cache. Neither uses optional fast-small-city-tail. Avoid a third concurrent learner (RAM/swap pressure).

Monitor either run with `tail -F /home/mohammadjaffal/mini_motorways/output/training/NAME/run.log`.

## Reset-study finalization recovery REQUIRED

First65k practice evaluation failed due to an omitted replay HTML template. Template was restored and identical evaluation rerun successfully; original failure preserved. The live controller still holds that failed Future and will report error AFTER BOTH arms and queued evaluations finish. Do not restart training. Once status is error/phase evaluation/arm both, run `recover_comparison.py` from this archive; it verifies all12 evaluations and both completed arms before summarizing and recording recovered-complete status. Read script first. See evaluation-recovery.json.

## Current repair check

Component intervention64city games: original Wait + reset-final roads averages135.78 (30/32scoring), versus original126.09 and joint reset89.25. It recovers degradation but improvement over original is uncertain. Reverse(newWait/originalroads)106.28. See reset-components/. Six new zero games all spend45roads; selected exact replay confirms late service after early branching, not avoidance. Figure/replays in reset-regression-replay/.

Prepared explicit Wait-restored checkpoint `output/training/mini-reset-wait-repair-01/start.zip`, SHA edb2a26da557f6d3d41a51ca64d62d0bdde8423572e84e78039a80cc43083aa5. Source reset-final; restore original zero-output Wait modules and freeze them using CityRoadChoicePolicy. All other weights exact. Named Adam migration preserves22parameter states at8192steps and counters; omits8frozen Wait parameter states.384shared states reproduce component swap within5.35e-7. Original inputs intact. This is engineering restoration, not a PPO gain. No training/promotion of repaired checkpoint yet.

112-game300-second mini assessment COMPLETE: tight8/16 unchanged, generous8/16 unchanged, bothpairs5/16 versus3/16. Shortskills retained. Screen failed; no promotion. Disposable optimizer invariance check passed (12states, Wait error3.58e-7, road/encoder changes, saved Adam8192 untouched). Sessions71476/55669 complete. Source/report in wait-repair/; root script training/prepare_city_wait_repair.py.

## Readiness and open work

Development gates: short skills retained (at most1additionalfailure), tight at least14/16, both pairs at least8/16, city mean at least original, no more than1extra zero. After passing, freeze candidate before fresh236Mmini/237Mcity tests. Target substantial city gain (~20percent with positive paired interval), inspect typical and poor play; no guaranteed gains. Neither current candidate qualifies.

Reserved fresh seeds236M/237M remain unused. Consumed: dev231Mmini and184M/185Mcities; bank232M; cold training233M; smoke235M; long diagnostic238M; traffic239M; durationtraining240M.

Exact-native reset-bank and300-second checks passed. Value probes show short lesson deadline hides later failure and critic remains poorly calibrated; this is diagnostic, not proof baseline biases expected gradient. Optional fast-small-city-tail passed88paired games/4267transitions plus PPO smoke; not enabled in active training. Original repeated city baseline exact across study runtimes.

Current interface is connection/Wait, native legal bridges. Weekly choice is still environment max-roads rule, not learned; no direct demolition/rotation/motorway/roundabout/light actions. Do not claim full tool strategy. Original retained reference start.zip SHA7eb605e4e465b9143e095e367abe0a01285b8ace05843aaac80bd48b5f049027.

Earlier chronological active notes preserved in ACTIVE_WORK-through-1718.md; detailed findings in README.md and training/EXPERIMENT_HISTORY.md. No overnight run launched.

17:34 update: Wait-restored actual32-city evaluation running session78552 (wait-repair/city.log), native finite-lesson gradient decomposition running session7100 (wait-repair/gradient-diagnostic.log). CUDA2workerresume128decisions/4updates passed, originalAdam8192 retained in parent. Prepared run_mini_road_continuation.py +summarizer, NOT launched;241M coldtraining reserved. Decide after results/capacity, do not claim a matched causal comparison with duration study. Training-quarter analysis shows reset starts and cold lessons largely flat; reset-training-behavior.json. Selected four mini replays exact; two PNGs visually inspected.

17:49 update supersedes pending diagnostics above: Wait-restored actual32-city evaluation COMPLETE, all common native fields exactly match component diagnostic (135.78125,30/32). Direction probe COMPLETE:16games/256states,5/7nondegenerate encoder batches show opposing actor/value gradients; two pair batches have−0.94projection. This is diagnostic, not causal proof. All sessions78552/7100/97443/27857/85527/4442 completed.

New prepared parent output/training/mini-road-detached-initial-01/start.zip SHA7582e285e3f6b2b44487cf3fe86156169aa80d79272dccbe21dc408fed0bf324. CityRoadChoiceDetachedCriticPolicy retains action/value outputs and all22Adamstates at8192steps, but critic feature inputs detach. Value head still trains; this is NOT an independent critic encoder. Source, primary-research caveats, migration/gradient/PPO checks under critic-detach/. Checks passed; disposable smoke excluded. Prepared controller run_mini_road_continuation.py uses262144decisions if --rollouts32, native300lessons, same8/4/4resetmix, cache+fasttail, training241M,2CPUevaluators. No production launch yet: wait for cold-control completion/capacity and duration midpoint review. Both existing production runtimes unchanged. No overnight readiness; fresh236M/237M untouched.
