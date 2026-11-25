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

ACTIVE MINI-TASK WORK: read docs/training/mini-task-repair-2026-11-25/ACTIVE_WORK.md before acting. Controller776266 already running; do not duplicate. Known recovered first-evaluation packaging failure requires explicit finalization after BOTH arms complete. Optional300slessons/cache prepared, not enabled in current frozen experiment. Midnight launch remains conditional on readiness.

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

The [city policy audit](../docs/training/city-policy-gap-audit-2026-11-23/README.md) contains independent results, frozen skill probes, two verified full-city branch routes and the proposed next gate. Keep the warm-start, four-hour save and repaired baseline for comparisons. The launch and result reports retain local run and checkpoint identities.

The [midgame service report](../docs/training/city-midgame-service-2026-11-22/README.md) records both bounded runs, the selected timing checkpoint, native witnesses and 340 paired review games. The opening repair remains the full-city reference.

The [one-hour pilot results](../docs/training/city-growth-pilot-results-2026-11-22/README.md) archive all 72 paired games, the two local checkpoint identities and the road-use comparison. Use the earlier repaired checkpoint as the current city reference.

The [growing-city pilot launcher](../docs/training/city-growth-pilot-launch-2026-11-22/README.md) records the user command, paired review and save/resume verification. The current repaired policy is its starting reference.

The [route repair record](../docs/training/city-route-repair-2026-11-22/README.md) identifies the evaluated calibration and selected local checkpoint with retained decision counters. It preserves the overnight reference, both redirected attempts and all final run saves. Use the fresh confirmation evidence for this result.

The [limited-stock route pilot](../docs/training/limited-route-ppo-2026-11-22/README.md) records 36 native scoring witnesses, the interrupted launch and its correction, the completed checkpoints and 336 paired evaluation games. Keep both practice saves as evidence and retain the overnight checkpoint for full cities.

The [hard-opening continuation report](../docs/training/city-opening-pilot-2026-11-22/README.md) archives the two unpromoted checkpoints and the 96 paired development games. It records early road-stock use, ordinary performance and late-game results. Use the seven-hour overnight checkpoint as the next starting reference.

The [road-only diagnostic archive](../docs/training/city-road-diagnostic-2026-11-22/README.md) gives the fixed policy, 62 frozen traces, four scoring feasibility routes and reproduction commands. Early stock use and late destination coverage are the next experiment targets.

The [completed overnight result](../docs/training/city-overnight-results-2026-11-22/README.md) identifies the selected 6,234,112-decision checkpoint and archives development and reserved results. Keep it and the frozen start for comparisons.

The [overnight launch handoff](../docs/training/city-overnight-launch-2026-11-22/README.md) has the user-run command, resume workflow and smoke evidence. It uses the original city transfer checkpoint and 32 native workers. Real development selection and the reserved comparison follow the overnight run.

The [city PPO worker comparison](../docs/training/city-ppo-worker-benchmark-2026-11-22/README.md) selects 32 native workers with the same CUDA learner, 128 rollout steps per worker and batch size 64. Benchmark weights were temporary. The report gives the reproduction command and measured resource headroom.

The [city PPO pilot](../docs/training/city-score-pilot-2026-11-22/README.md) archives the training and comparison commands, seed separation, measurements and local checkpoint hashes. Keep the starting transfer as the reference and retain both pilot checkpoints. The worker setting was chosen in the benchmark above.

The [city baseline archive](../docs/training/city-frozen-baseline-2026-11-22/README.md) contains the fixed 32-seed test suite, five frozen conditions, and the reproduction command. Keep those seeds out of pilot training and checkpoint selection. This archive predates the completed pilot.

Continue training work in `/home/mohammadjaffal/mini_motorways` on `Maskable-PPO`. Earlier entries describe the branch used at the time of each run.

The [city starting policy report](../docs/training/city-policy-start-2026-11-22/README.md) gives the selected local checkpoint, archived frozen evidence and the reproduction command. It supplied the checkpoint for the completed baseline.

Run the [growing-city preflight](../docs/training/city-road-preflight-2026-11-21/README.md) with `bash training/verify_city_road_pilot.sh` from the training checkout. The command runs the complete verification game. Earlier checkpoint results remain indexed below.

The latest [timing report](../docs/training/wait-before-surge-2026-11-21/README.md) records both selected checkpoints, frozen timing and stock checks, native setup patches and a replay command. The original road-end checkpoint remains available for the earlier bypass milestone.

The [road-end transfer report](../docs/training/road-end-transfer-2026-11-21/README.md) contains the selected mixed-pressure checkpoint, native fixture patches, stopped-car measurements and held-out replay command. No training is active. The earlier isolated and construction checkpoints remain available.

The latest [frozen bypass transfer report](../docs/training/junction-transfer-2026-11-21/README.md) has same-board controls, both saved checkpoint identities and an exact replay command. The original checkpoint remains selected for the original junction. The initialized road-end scorer is ready for a separately authorized training comparison. No training is active.

On 21 November 2026 the training checkout is `/home/mohammadjaffal/mini_motorways` on `mohammad`. The [demand priority and congestion report](../docs/training/traffic-milestones-2026-11-21/README.md) has the selected checkpoints, native fixture patch chain, interrupted run ledger and frozen replay command. No training is active. The earlier construction and timed Build-or-Wait checkpoints are indexed below.

Current (20 November 2026): The active Linux checkout is `/home/mohammadjaffal/mini_motorways` on `mohammad`. See the [competing-home routing and timed policy report](../docs/training/competing-homes-2026-11-20/README.md) for the newest selected checkpoints, exact native hosts, scored outcomes, and replay commands. The [earlier construction report](../docs/training/reward-only-construction-hour-2026-11-20/README.md) retains the obstacle, driveway, isolated-pair and other training specialists. Prior `Maskable-PPO` entries below are historical.

Latest (20 November 2026): Read the completed [five-stage construction curriculum report](../docs/training/construction-five-stage-2026-11-20/README.md) for the opt-in host, final local checkpoint, and every run. Historical PPO checkpoints remain preserved.

Latest (19 November 2026): Read the [one-build diagnostic and verification](../docs/training/one-gap-single-build-2026-11-19/README.md) before planning a new pilot. The stage is implemented locally and has no trained checkpoint.

Latest (19 November 2026): The Linux training checkout is `~/mini_motorways` on `Maskable-PPO`. Read the [direct one-gap implementation](../docs/training/one-gap-direct-2026-11-19/README.md) and [latest completed training run](../docs/training/linux-compact-reward-results-2026-11-19/README.md). No direct pilot has run. Older cloud-only setup and updater status below are historical.

Latest: [Stage1 launch preparation](../docs/training/stage1-launch-preparation/README.md). Batch/update/checkpoint and bounded default-dry runner now implemented. Real-host forward checks pass with0updates; actual update path and target Linux validation remain untested. No training authorized/run. Earlier no-updater statements below are historical.

# Latest continuation after one-hour implementation — 16 November 2026

Read [implementation report](../docs/training/check-in-2026-11-16/README.md) first. Worktree:
/workspace/mini_motorways-maskable-ppo, Maskable-PPO, documentation base6bd7f71.
No new commit/push; original Windows checkout and Linux PC unchanged. User
explicitly prohibited training and requested one hour of implementation/checks.
SESSION.json records the work window and final timing. No training ran.

## Now implemented

Published81/54/motorway visible schema with observed traffic history; additional
focus/context. Stage1uses1501context-dependent tokens, CANCEL separate from
HANDOFF, and exact pure clear-land native masks. Shared reconciled encoder with
distinct manager/executor actor/value heads, no pretrained/planner initialization.
Source/protocol/reset handshake and failure handling fail closed. Masks cache by
reset/network/stock/offer state. No hidden routes, raw speed/wait/reservations,
score or future data enter model inputs.

Frozen inference collection, version-controlled partial focus bookkeeping,
explicit gamma1GAE helper, separate PPO loss-term helper, replay recording and
strict verification, and evaluation with all-attempt logs plus best/worst/actual
nearest-average exemplars are available. No optimizer/update loop is connected.
Do not treat an inference collection or scripted replay as learning.

## Verified

99native core suites;1116differential Stage1action checks (includes live traffic,
refunds, all directions and harmless repetitions);62distinct selected Python
checks.100scripted validation layouts score10–13trips by180s. A labelled
552-token scripted fixture scores11trips and replays exactly. Native builds clean.
Cloud CPU speed measurements are smoke tests, not Ryzen/RTX configuration advice.
No trained weights saved; temporary untrained save/load fixture is removed.

## Next work

1. Complete explicit hierarchical PPO updater integration using stored conditional
   probabilities and role contexts. Trace lambda/units remain open; manager joint
   entropy estimator and level-loss weighting must be explicit. Do not silently
   default to the old.95or nest independent learn calls.
2. Stage1legality is intentionally scope-guarded; full-game water/circle/motorway/
   weekly contexts and graphical focus replay support are not finished.
3. Transfer source changes, repeat checks on Linux and run bounded non-training
   batched/parallel benchmark there. Code is not available via pull until published.
4. Respect no-training instruction. A future pilot requires separate explicit
   user authorization; current tools do not supply a training launch command.

The approved gate counts a naturally completed episode with>=3trips, including
native game-over; the draft's extra survival requirement was removed. External
stall/operational interruption is not a completed gate success. Details/reason
are in the report. Earlier handoffs below are history, not current blockers.

---

# Latest implementation continuation — 16 November 2026

Published decision records fetched at `6bd7f71` and integrated into the cloud
Maskable-PPO worktree, preserving uncommitted implementation changes. The
Windows-local decision-record availability blocker is resolved. Read
[reconciliation](../docs/training/connection-practice-2026-11-16/RECONCILIATION.md)
before code or claims of readiness. The earlier setup handoff below is a dated
snapshot: Linux setup has since passed GPU/import/build tests, 99 core and seven
legacy integration checks; user reported 87 GiB available after cleanup.

The draft practice environment is **not ready for learning**: its legacy input
schema, masks, token syntax and shared heads need replacement/reconciliation.
Gamma=1 is carried forward; lambda remains explicitly reopened. Initial total
episode decision guard corrected to a 4096-token guard since positive time
advance; finite task horizon terminates, operational stalls truncate. Native wait
also stops at task horizon. No training/optimizer updates have run.

Next: replace legacy observations, reconcile exact action contexts/native masks,
restore established encoder widths and distinct heads, implement the documented
collection/credit and new replay contract, then target-PC speed checks. User's
no-training instruction remains active. Changes remain cloud-local and unpushed.

---

# Continue here — Maskable PPO restart

Updated 16 November 2026. Read this before resuming. This is a handoff from a long design/setup chat, not evidence of implemented training.

## Exact stopping point

The user reports the Linux machine now has **30 GB free** and has just completed cloning:

```bash
git clone --branch Maskable-PPO --single-branch https://github.com/JoeJaffal/mini_motorways.git "$HOME/mini_motorways"
```

User said "done"; no clone output/revision or new df output supplied. No package installation, new model implementation or training has been completed in this chat. The next practical step is verify the Linux checkout/workspace and prepare an isolated Python environment, then install a deliberately chosen compatible stack and simulator build tooling. Do not mistake software setup for permission to launch long training. Before coding, reconcile old settings with the approved hierarchy; do not repeat settled design discussions.

The user will manually run Linux commands; no remote connection is configured or wanted. Give short, understandable commands in small useful batches and interpret results. They prefer simple explanations and a clear next step, not sprawling checklists or repeated approval of settled topics.

## Where work actually lives

- **Use this checkout:** `C:/Users/moham/mini_motorways-maskable-ppo`, branch **`Maskable-PPO`**. This explicitly supersedes AGENTS.md's old `mohammad` branch preference for this restart.
- Branch baseline/last checked remote: `938b9f80e67ca5341920a10e9e671164a474fc38`, simulator `2026-11-10.f34`. The clone initially received that baseline. Pull the documentation publication to obtain these decisions; simulator source baseline is unchanged.
- Original checkout `C:/Users/moham/mini_motorways` remains dirty on `codex/driveway-physics`. Do not switch, clean or stage its unrelated modifications. Older decision spreadsheets, ledger and dated decision JSON have now been copied byte-for-byte into this branch. See docs/training/DECISIONS.md for current precedence and migration provenance; original dirty checkout remains untouched.
- User now explicitly authorizes committing/pushing the detailed decision records on Maskable-PPO so the Linux clone can read them. This publication includes the new planning records and selected older archives. Update Linux with `git pull --ff-only origin Maskable-PPO` from `~/mini_motorways`; verify the pull result rather than assuming automatic sync.
- Root AGENTS.md documentation requirements apply: chronological `training/EXPERIMENT_HISTORY.md`, simulator/user decisions in `simulation/Docs/DESIGN_DECISIONS.md`, current status/index, durable small sources, no weights/binaries/private game material/secrets committed.

## Approved direction — preserve it

1. Fresh model aiming to compete with Mohammad, then see how far it can improve.
2. **No external road planner, generated routes, candidate-route menu or automatic completion.** Manager only selects focus; executor chooses every neighboring road/bridge connection, including legal diagonals. Ordinary native vehicle routing is still allowed.
3. Multiple sequential paused edits, each followed by observation. Explicit one-simulated-second wait, ending early at native weekly/game-over events. Physical game legality only in action masks, not strategic pruning.
4. Visible structured game state; game score only as reward. No connection/completion/congestion bonus or wait/edit reward manipulation.
5. **Adopted hierarchy:** manager selects primary tile and optional secondary tile; executor gets that focus plus full board and retains all physically legal edits, including outside the focus. Provisional review after eight completed edits or one wait; early executor handoff and native event interruption. Agent is responsible for backing this up and revising it against evidence. Detailed encodings/network dimensions/manager-executor PPO credit still need reconciliation, not a blank-slate redesign.
6. **Adopted curriculum:** basic connections → construction challenges → shared networks → growing cities → full games. Stage 1: one house and matching destination, short clear land gap, varied positions/orientations, model constructs and waits for real scored service. No generated construction path provided.
7. **Approved Stage 1 gate:** 180 simulated seconds per episode; at least 90 of 100 held-out practice layouts each complete at least 3 scored trips, evaluated with a frozen checkpoint. Paused building consumes no game time. Check native trip timing feasibility before using this initial gate. Exact inventory/event/scenario generator settings still need specification/reconciliation. Threshold is evaluation, not extra reward. Do not count operationally truncated episodes as completed passes.
8. Train/validation cities with distinct seeds and a reserved final city; retain best/worst/nearest-average replays for user evaluation. Prior exact full-game split/config proposals exist; do not pretend the topics have never been discussed. New practice distribution must be explicitly documented.
9. Roundabout comparison/fix belongs to another person; move on. Published report commit `c37ce9a6eee1a5621bc40c1b546281a9ebc9f482` on `codex/driveway-physics`, path `docs/training/roundabout-video-2026-11-16/REPORT.md`. No roundabout engine patch was applied by this work.

## Linux training machine — distinguish evidence from assumptions

User-supplied terminal output: Ubuntu24.04.4LTS, kernel6.8.0-149, Ryzen9 3950X (16physical cores/32threads), nominal32GiBRAM (31GiBreported), RTX2080Ti11264MiBVRAM, driver595.84. Python3.12.3, Git2.43.0; dotnet not found. Active Python had NumPy1.26.4, no torch/Gymnasium/SB3/Contrib. No benchmark or GPU-PyTorch validation.

Storage originally root/home476GiB,443GiBused,8.1GiBavailable,99%. Separate1.8TiBNTFS DATA `/dev/sda2` was unmounted; NVMe also has an unmounted469.8GiBNTFS partition. Mount command `udisksctl mount -b /dev/sda2 -o ro` required IT credentials; do not bypass/access other credentials or format/repartition. Unprivileged du only counted36GiB; exact discrepancy unresolved. User then reported30GBfree; accept as latest report, verify actual workspace during setup. No cleanup performed by agent.

Storage calculation now exists: [budget](../docs/training/linux-preflight-2026-11-16/STORAGE_BUDGET.md). Metadata/ZIP-directory measurements for candidate LinuxCPython3.12 stack: CPU16packages .760GiBunpacked/.209GiBdownloads; CUDA12.6 profile34packages6.159GiBunpacked/3.421GiBdownloads. Torch2.14.1 + current four requirements pins. With1GiBSDK/builds,.1GiBcode/git,5GiBinitial artifacts and5GiBsystem reserve, planned total20.680GiB; target25GiB(~27GB), rounded request30GB.50GBwas comfortable allowance, not a measured minimum. These are sizing scenarios, **not adopted/runtime-tested install locks**. Check RTX2080Ti binary support; do not install whatever CUDA nvidia-smi labels. Full dependency resolution/installed peak and artifact retention remain to verify. No Unity Editor or full CUDA toolkit included in budget.

Current headless project `simulation/Headless/TrafficHost.csproj` targets net8.0. Prior SDK8.0.427 used in source/analysis; official current .NET8page now says end-of-support. Reconcile support/version deliberately; no automatic simulator upgrade adopted. Build/run tooling may be user-local; do not presume admin access is necessary for training.

Alternative Windows laptop screenshots: RTX5060prefix, full suffix truncated,8151MiBVRAM, Python command missing/storealias, Git unrecognized, .NET host responds but noSDKfound. CPU20cores only user-reported; RAM/storage unknown. Not selected instead of Linux. Keep inventories separate.

## Read next, in this order

Start with [current decisions and detailed archive index](../docs/training/DECISIONS.md). This is the authoritative entry point for distinguishing later approvals from historical snapshots.

- [Short overview](PLAN.md)
- [Latest technical status](CURRENT_STATUS.md) — top entries supersede historical material below.
- [Hierarchy adoption and preserved proposal](../docs/training/hierarchy-proposal-2026-11-16/README.md)
- [Stage 1 approvals and earlier discussion](../docs/training/curriculum-design-2026-11-16/README.md)
- [Linux evidence/setup and storage data](../docs/training/linux-preflight-2026-11-16/README.md)
- [Chronological history](EXPERIMENT_HISTORY.md)

Migrated historical sources in this checkout (original copies also remain in the original checkout): `docs/training/hierarchy-design-2026-11-16/current_decisions.json`, `docs/training/maskable-ppo-spec-v1-2026-11-16/SPECIFICATION.md`, `docs/training/maskable-ppo-restart-decisions-2026-11-15.md`. They contain earlier flat-policy/default assumptions and stale no-hierarchy/no-curriculum/Intel-Windows descriptions. New explicit approvals above supersede those. Existing reviewed observations/network/PPO/evaluation topics should be kept where compatible, changed only with concrete reasons. Original workbook unreviewed Excel rows were20,28,47–49,51–58; review is not implementation, and later hierarchy/curriculum approvals update their own topics.

## Immediate next action

Continue Linux setup after the reported successful clone. Confirm the checkout path/branch and available writable space with simple commands if needed, then create/check an isolated environment. Do not issue a training command: the new hierarchy trainer is not implemented. Plan a complete compatible dependency installation before consuming the newly available30GB; avoid copying7.37GBWindows scratch/output/venv wholesale. Maintain this handoff/status/history with material progress. No need to ask user to explain the project again.
