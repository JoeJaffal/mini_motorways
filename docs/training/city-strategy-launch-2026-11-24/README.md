# City strategy learning and long-run readiness — 24 November 2026

**Bounded trials complete; no long run justified or launched.** The road-only city mask hid legal bridge
crossings despite available bridge inventory. Optional bridge connections now
pass104 native suites,11Python checks,and1,600 exact legacy transitions.
On the same32 development cities,the unchanged reference rises69.19→124.41;
scoring25→29/32,survival to600s5→21/32. This is an engineering interface gain,
not PPO learning. All prior road-only records remain historical.

The bridge-enabled calibrated reference remains the best supported city starting
behavior. Conservation continuation, low-rate city final and higher-rate city final
do not improve the matched1200s development mean. Higher-rate midpoint was244.44
versus230.97 on32cities, but broader64-city review is231.55 versus262.77; no
promotion. Both bounded rate trials are complete. Recorded native midgame training completed65,536 decisions: final234.91 versus230.97 on32 full-start cities is uncertain, and new-target zero-stock arrivals rise44→104. No promotion. Critic-head-rate final220.53 versus230.97 failed promotion despite better value fit. Longer-rollout final213.03 versus230.97 also failed promotion. All jobs have ended. Reliable full-city strategy improvement remains unresolved. No long run is launched. All checkpoints remain preserved. The normalized bridge-choice prototype
is **unused**:completed rollouts showed the existing actor already uses bridges,
contrary to the interpretation of tiny probabilities on selected initial states.

See [current status](../../../training/CURRENT_STATUS.md),[plan](PLAN.md),
[matched bridge results](BRIDGE_RESULTS.md),[run ledger](RUN_LEDGER.md),[run register](run-register.json),and
[history](../../../training/EXPERIMENT_HISTORY.md). Historical phase records below
retain the evidence and superseding decisions.

## Authorization and preserved starting point

User authorized changes and bounded training to establish meaningful strategic
learning, then a long launch when evidence supports it. No finite pilot can
promise that subsequent scores will increase. Work uses the explicitly approved
`/home/mohammadjaffal/mini_motorways` checkout on `Maskable-PPO`; the separate
Desktop/main checkout is not the working tree. Existing dirty files, checkpoints
and prior failed experiments are preserved; no pull/reset or handoff patch.

The starting policy is `city-five-stage-cold-initial-01/candidate.zip`. Its prior
calibration is engineering work, not a PPO improvement. This experiment's new
policy layers and added critic columns initialize to zero output, preserving
initial action probabilities and values. Subsequent improvements therefore
require actual training or sampling variation, not changed initialization.

## Changes and limits

- Add learned Wait and per-road residuals using visible city context, stock,
  demand, existing connections and visible motion. Only these new layers and
  the critic train. Preserve the inherited opening policy.
- Initial trials use city-only native completed-delivery rewards,512-step rollouts,GAE1/gamma1,
  batch128 and up to four PPO epochs. Later fixed-worker trials allocate50% of
  decisions to cities,25% reservation and25% demand priority. No road-use penalty, planner, teacher actions,
  imitation updates or future information were added.
- A measured limitation of the first residual is input aliasing:532 of541 legal
  roads in the join probe have identical trainable relation inputs. Frozen prior
  scores differ, but this residual cannot learn to distinguish those roads.
- A separate learned spatial branch adds dilated convolutions over the visible
  board, per-edge outputs and pooled critic/Wait features. Receptive-field span
  is63 cells (radius31), not a claim that every corner sees every other corner.
  This branch is not merged into the first candidate and needs its own evidence.
- Add1200-second native horizon support while retaining the600-second observation
  schema. Exact initial observations and30 native transitions match. This tests
  longer consequences; scores across different horizons are not directly compared.
- Checkpoint every rollout, save checkpoints atomically, preserve optimizer state
  on compatible continuation and archive small progress records. Verified a
  detached segmented runner on bounded jobs with paired regression checks; no
  eight-hour session has launched.

The policy still chooses a road or Wait; weekly choices are scripted. These
results do not establish mastery of every tool, commercial-game fidelity or
leaderboard performance. Frozen opening mistakes also remain possible.

## Completed score evidence

All comparisons below use matched native and action RNG seeds and frozen models.
The bootstrap interval measures paired score differences across cities.

| Review | Parent mean | Candidate mean | Scoring cities | Paired gain,95% interval | Interpretation |
|---|---:|---:|---|---|---|
| Development32,midpoint |69.19|69.47|25→25|+0.28 [−12.84,12.63]|Flat |
| Development32,final |69.19|84.34|25→26|+15.16 [1.28,30.34]|+21.9%,selection evidence |
| Independent64,final |82.73|88.14|54→54|+5.41 [−5.50,16.23]|+6.5%,launch gate failed |

The independent candidate served207 new targets versus202, but zero-stock target
arrivals increased105 versus58. This is not evidence of reliable road saving.
Development stockouts also rose65 versus33. Native game results take priority
over attractive training averages; early training averages contain only games
that have already finished and can be biased toward short failures.

## Run ledger

| Run | Outcome |
|---|---|
| summary initial01 | Exact initial actor/value parity; new hidden weights not explicitly seeded; exact saved start is needed for identical initialization. |
| summary pilot01 |65,536 decisions,168 episodes,1,021.2s; midpoint/final saved; finite losses; protected opening exact. |
| wide initial01 | Explicit seed11424; exact actor/value parity on opening and nine lessons. |
| wide pilot01 | Interrupted after24,576 logged decisions; no saved midpoint; unsaved updates lost. |
| longer pilot01 | Interrupted before checkpoint; partial evidence retained. |
| confirmation01 | Interrupted partial printed results; not a complete statistical review. |
| wide pilot02 | Stopped before first checkpoint to relieve RAM/swap pressure; not a learning failure. |
| longer pilot02 |32,768 additional decisions,93 episodes,660.8s; checkpoint each rollout; weight/opening audit passed; score reviews complete:600s development79.44,1200s review86.28 vs parent98.22; reject. |
| confirmation02 | Completed64 paired cities; independent gate failed, as above. |
| wide pilot03 | Completed65,536 decisions/150 episodes in977.8s; midpoint development75.63 vs69.19,paired+6.44 [−8.34,21.69]; final68.625 vs69.1875,paired−0.56 [−15.34,13.72]; no gain. |
| mixed pilot01 | Stopped at saved32,768 midpoint; city73.625,priority7+9/32,reserve0/16; episode cycling undersampled priority. |
| balanced pilot01 | Fixed workers8 city/4 reserve/2 priority/2 swapped; preserve first8,192 checkpoint, then enable validated terminal-tail speedup for remaining24,576. |

Two16-worker trainers plus eight review workers exceeded comfortable physical
memory. Trainers now run serially; one trainer plus eight evaluation workers
fits. Interrupted runs are never silently presented as completed trials.

## Verification and retained evidence

Eighteen city-focused Python tests pass (latest optional learning-signal and
reporting checks included): policy shapes/trainability/zero output,
spatial gradients and empty-board handling, and long-run regression decisions.
Native host unchanged this task; its prior99 suites and364 parity checks are
recorded in the preceding road-reserve report. No claim those were rerun here.
Parameter audits verify only intended layers changed, finite weights, valid masks
and exact protected opening on four seeds. Native skill retention is separately
scheduled; initialization checks alone do not prove retained learned behavior.

`measurements/` preserves small configs, episodes, evaluation rows and logs.
`source/` preserves the dirty Python source snapshot. `local-artifacts.json`
records hashes/locations of local-only ZIP weights and native binaries, which
are not included in this archive. `manifest.json` hashes retained small records;
active snapshots are provisional until the final archive refresh.

## Latest strategy learning

Correct decision allocation raises priority success16/32→26/32 and mean
conditional urgent-road probability51.51%→78.33%. Connections remain16/16 and
delayed connection13/16. Full-city development74.65625 versus69.1875 (+7.9%),
paired+5.47 [−6.16,17.22],25/32 scoring retained; this is not the long-launch gate.
Reservation remains0/16.

The32,768-decision warmup extension completed. Its midpoint reaches30/32
priority checks and82.75 city development mean vs69.1875 (+19.6%,paired interval
[−6.84,34.16]); final28/32 and80.0. Both retain connections but score0/16 on the
original-delay reservation cohort. A separate16-case diagnostic finds genuine
future service on easier starting states; see below. Fixed6s native warmup uses
no hidden timing and excludes warmup deliveries;16 paired checks match manual
waiting. Evaluation defaults to original zero-warmup/full-delay conditions.

The subsequent task-homogeneous minibatch pilot finishes32,768 decisions:
midpoint73.375,final71.53125 vs69.1875 development reference. Final priority27/32,
reservation0/16; no meaningful city gain. Reject as a city candidate. Reservation
return std2.7–2.8 versus advantage std17–20 suggests a noisy learned baseline.
A new bounded32,768-decision pilot uses return-to-go actor advantages only for
reservation, keeping native rewards/critic targets and other tasks unchanged.
Its explicit flag defaults off. All later-delivery outcomes are now separately
logged; total training reward is not a substitute for future-target service.

Frozen extension midpoint is undergoing64-city independent confirmation on
RNG950243. This cohort is separate from development and becomes consumed once
its results are inspected. Evaluation jobs are serialized to bound memory.

The unattended runner passed a512-decision/two-city workflow smoke. That tiny
review is not selection evidence and its checkpoint is not a training parent.
The extension runs one bounded segment through the same frozen-runtime runner;
no eight-hour session has launched. Its logging clears inherited episode history
and prints separate task means. Process tests cover failure,timeout,and orphan
workers that ignore SIGTERM. See [run register](run-register.json) for per-task
episode counts; thousands of short lessons are not thousands of full cities.

## Pending readiness decisions

The longer-game comparison failed to show repeated improvement: parent98.22,
summary112.19, additional continuation86.28 on32 paired1200s cities. Both paired
intervals include zero. Native summary retention preserves join/route16/16 and
delay13/16; priority remains8/16 in each orientation and reservation drops2→0/16.
Spatial final retains connections but priority7/16+9/16 is still16/32 overall;
reservation0/16. Live junction success flags are not meaningful here (even the
controls have no new target); compare their native delivery scores instead.

A ten-city opening audit finds the new-layer gate active for174/1,898 decisions
in zero-score games, starting only140–142s in eight cases and never in two. The
gate detects a visible matching connection and>2 buildings, not actual deliveries.
Thus protected early behavior remains a substantive limitation. Saturated road
probabilities also persist in the wide candidate.

The mixed curriculum exposed a sampling defect:27 one-decision priority episodes
among24,576 decisions,about0.11% priority exposure. Corrected fixed worker tasks
allocate50% city,25% reserve,25% priority decisions. Native32-reset validation
confirms task assignments,unique seeds,observations and masks.

Optional fast-priority-tail skips only Python IPC/encoding after the priority
fixture has exhausted its one road and has no remaining choices. Existing native
`step` executes the same physics until termination.32 paired cases preserve exact
raw final state,reward,flags,info and next reset; tail benchmark3.66x faster.
Terminal motion history differs but is never bootstrapped or used by the next
episode. Ordinary city behavior and the native binary are unchanged.

Finish the decision-balanced strategy continuation and frozen reviews.
Select on development evidence; a later selected candidate must pass fresh
confirmation. Do not weaken the predeclared gate merely because one cohort
improved. A long launch requires repeated measured improvement, stable training
and no material loss of useful service. Its prepared runtime must pass an
integration smoke test before launch.

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
All18 city-focused unittest tests pass after the optional return-advantage and
reporting changes; weights/Adam/counters/nine actor distributions are unchanged
on load. Pytest is absent; no package installation was needed.

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

Return-advantage pilot final:32,768 decisions/8,383 episodes/1,011.53 seconds;
city74.75 vs69.1875,paired+5.5625 [−9.96875,20.71875],new targets90 vs91,
stockouts33 vs33. Priority27/32,original-delay reserve0/16,connections retained.
Reject as a city promotion. Complete records and all checkpoints preserved.

Value-balance midpoint: original-delay reserve1/16 vs0 at its parent,short-delay
9/16 vs7 on matched validation cases;priority29/32,join/route16/16,delay13/16.
This is small early progress, not readiness. First two rollouts use17 optimizer
steps out of512 maximum,still restricted by taskwise KL early stopping.

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

Broader development(64 reused950242 cities) gives original-delay midpoint88.671875
vs82.734375,parent54 scoring→candidate55;paired+5.9375 [−3.28125,15.296875].
New targets served202→222;zero-stock target arrivals58→27;median service delay
26s unchanged. This supports improved resource management on this selection
cohort,not a substantial independently confirmed score gain. Paid units76.53→
78.86,outside-route units33.20→34.23,so do not claim all excess construction is
fixed. Keep final review and the original long-launch gate.

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


### Longer-horizon selection correction

The bridge-enabled 1200s baseline favors the calibrated reference (230.97) over the conservation-trained parent (185.53) on 32 matched development cities; paired difference −45.44, interval [−92.60, 4.19]. The balanced bridge continuation was stopped with its 24,576-decision checkpoint preserved (768 optimizer updates). Its waiting reviewer was canceled. The runner status reports zero completed-segment training seconds because interruption occurred inside the first segment; checkpoint records document 769.64 seconds to the last saved checkpoint, not zero work. Unsaved later rollout progress is not carried forward. Next compare the existing city-only final under the same bridge-enabled 1200s protocol. No long run has started. See `bridge-balanced-stop.json` and `bridge-city-only-longer-launch.json`.


### Continued work: compare city outcomes before choosing training parent

All32-city1200s comparisons below use the same seeds, action RNGs, bridge-enabled interface and native host. They are consumed development data.

| Candidate | Mean deliveries | Scoring cities | Difference from reference (95% paired interval) |
|---|---:|---:|---|
| Calibrated reference |230.97|29/32|Reference|
| Conservation parent |185.53|29/32|−45.44 [−92.60,4.19]|
| Existing city-only final |220.00|29/32|−10.97 [−74.56,49.59]|
| Balanced bridge24,576 |183.69|29/32|−47.28 [−115.19,16.88]|

No trained candidate is promoted. The balanced bridge run is stopped and preserved. A bounded65,536-decision city-only trial (`city-strategy-bridge-reference-city-01`) now starts from the stronger calibrated behavior via its zero-output wide initialization. Actor equality passed1,024 sampled bridge-enabled observations. Optimizer state starts fresh as recorded in that initialization; this does not erase or overwrite any earlier checkpoint. Native reward, action representation and model architecture are unchanged in this trial. CorrectedLR0.0001/vf0.00001;16workers,1200s,seed168M. First16,384decisions complete512/512 optimizer updates and pass parameter-change audit; small policy changes do not yet prove score gains. Midpoint/final matched development reviews are scheduled; no overnight launch.

Eight read-only terminal replays match all evaluation fields exactly. Several failing destinations have connected homes and assigned cars, but this alone cannot identify congestion: detailed zero-score replay99020130 connects too late (no assigned cars through140s, moving cars at144.95s death). No collision-rule change is justified by that observation. See `bridge-reference-ending-diagnostics.json`, `bridge-zero-city-traffic.json`, and diagnostic scripts. These use only existing-link connectivity for audit and supply no actions or routes to the learner.
