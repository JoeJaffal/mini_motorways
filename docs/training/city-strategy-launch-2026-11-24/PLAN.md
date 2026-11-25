# Evidence-gated city strategy continuation — 24 November 2026

User authorizes autonomous changes, bounded pilots and a long training launch
only once evidence supports substantial score improvement and real strategic
learning. No finite experiment guarantees future improvement. Work remains in
the explicitly confirmed Maskable-PPO checkout; preserve existing work/weights.
No planner, teacher actions or imitation; native deliveries remain the reward.

Diagnosis: reservation-only learning transferred poorly. The first new feature
also confused missing short progress with a blocked approach; that error was
repaired but city scores still fell. The existing critic lacks explicit visible
service context, and GAE .95/128-step rollouts emphasize short consequences.
These are candidate limitations, not established sole causes of every failure.

New experiment: start exactly from the best calibrated city parent, add zero
initialized neural residuals for Wait and road choice using existing visible
service/supply/demand/congestion evidence and visible global context. Preserve
opening and inherited rankings at initialization. Give the critic the same
visible aggregate context; pad its copied first-layer weights with zeros to
preserve initial values. Only new residuals and critic learn. Fresh Adam state
is required for the changed parameter set. No road/path solver supplies actions.

First budget: 65,536 city-only decisions, 16 workers, 512 steps per rollout,
128 batch size, four epochs, gamma1/GAE1, base LR .003 (road group .3x, critic
.1x). Train seeds140M. Save midpoint/final. Native city horizon600s. No practice
fixtures determine this pilot's reward. Development review32 cities RNG950241;
practice regression probes seed141M. Reference scores are paired with exact
saved policies. Full source, configurations, checks and failures are archived.

Launch gate: repeated improvements after additional PPO updates, not just a
changed initialization; substantially higher mean (target >=20%) on independent
city cohorts with a positive paired interval and no lost scoring-city count;
finite/stable training; preservation of useful service on controls; longer
horizon check before calling it general long-run readiness. Any changed gate or
budget must be recorded with reason. Independent confirmation uses RNG950242,
then RNG950243 only if a further revision makes the former development data.

If gates pass, launch a detached eight-active-hour continuation with periodic
checkpoints, readable episode scores, durable best/reference records and
regression protection. Leave it running and return the monitoring command;
do not wait for it to finish. If gates fail, do not present certainty or launch
an unsupported long run just to satisfy the requested outcome.

## First result and representation expansion

Pilot01 completes65,536 decisions/168 episodes in1,021.2 seconds. Midpoint32-city
mean69.46875 versus69.1875, same25/32 scoring; paired difference0.28125 with
95% interval[−12.84,12.63]. No substantial gain. Final review remains pending.

Measured representation limit: in the join probe541 legal roads collapse into
only three distinct trainable relation vectors;532 share one vector. The global
context is identical for every edge. Frozen inherited scores can distinguish
these roads, but the new relation residual cannot change their relative ranks.
This limits what additional training of that residual can learn.

Add a separate wide spatial branch: input is the visible board, a1x1 projection
and five learned3x3 convolutions with dilations1/2/4/8/16 (63-cell receptive-field
span), per-edge outputs and pooled visual input to Wait/critic. This is learned
representation, not route search. No reference actions or future data. All new
outputs and new critic columns start zero, so initial probabilities/values match
on all nine lessons and opening. Explicit initialization/training seed11424;
exact prior summary-branch weights copied from initial01. New parameters require
fresh optimizer state. Old classes/checkpoints preserved.

Bounded wide-pilot01 budget65,536 city-only decisions, seed range142M, same
512/128/4,gamma1/GAE1 settings and base LR.003; spatial encoder LR.0003, road
head LR.0009, Wait.003, critic.0003. Development suite stays RNG950241 and is
selection data. No independent confirmation set has been consumed yet.

## First full pilot gain; independent confirmation and longer-city continuation

Final summary-residual01 development mean84.34375 versus69.1875 (+21.9%),
26/32 scoring versus25/32, no lost scoring seeds. Paired difference15.15625,
95% interval[1.28,30.34]. New targets served98 versus91; arrivals with zero stock
increase65 versus33. This is learned change from identical initialization,
but selection data and increased stockouts prevent an immediate long launch.

Freeze final01 for a64-city independent600s confirmation (RNG950242). This sample
size is selected before seeing its results. Continue its optimizer for32,768
additional city decisions at1200s on143M seeds, same LR/512/128/GAE1 settings,
to test improvement through more learning and longer consequences. No updates
will use the independent cohort's results. Wide pilot01 remains a separate
representation trial; do not merge its unverified weights into this candidate.

## Longer-game and skill retention review (declared before results)

Compare calibrated parent, summary final01 and longer final02 on32 paired1200s
cities RNG950244. This is a longer-horizon diagnostic, not the independent600s
confirmation (950242). Evaluate longer final02 on the existing32 development
cities950241. Check parent/summary/longer on all nine native lessons,16 seeds
starting141M with evaluation controls. Wider candidate selection remains on
950241; if it becomes preferred, use untouched confirmation950243. Run at most
one16-worker trainer and one8-worker review at a time to fit physical RAM.

## Targeted strategy continuation after city-only skill review

City-only spatial final03 retains join/route16/16 and delayed connection13/16,
but priority is7/16 plus9/16 swapped (unchanged16/32 total); reservation0/16.
Thus larger representation alone has not taught those strategies. Test a bounded
65,536-decision continuation from spatial final03 on `strategy-mixed`: four city,
four reservation, one each priority/swapped priority/join/route/delay/quiet per
14-episode worker cycle. This is episode weighting, not equal decision weighting;
full cities are much longer. Native delivery reward only; no reference actions.
Use144M training seeds,512-step rollouts,batch128,gamma1/GAE1,base LR.001
(smaller than.003 to limit damaging the retained skills), save every rollout.
Compatible optimizer state continues; no new network or calibration.

Review midpoint/final against spatial final03 on development950241 and native
16-case skill cohort141M. Only a selected candidate gets fresh confirmation950243.
This is a targeted curriculum hypothesis, not an asserted fix or a long launch.
Inherited road saturation and early-phase gating remain explicit limitations.

## Correct the strategy sample allocation at the saved midpoint

After24,576 mixed decisions, only27 completed priority/swapped episodes supplied
one decision each because forced-Wait compression removes their remaining wait.
Episode cycling therefore supplies about0.11% priority samples, despite naming
two priority lessons. This is insufficient exposure for the intended curriculum.
At the32,768 saved midpoint, stop the current bounded trainer, preserve it and
continue the remaining32,768 budget as `strategy-balanced`: fixed16 workers,
eight city/four reserve/two priority/two swapped. Equal per-worker rollout lengths
allocate50%/25%/12.5%/12.5% decisions, independent of episode length. Seed145M,
LR.001 and compatible optimizer state retained. This is an adaptive engineering
correction, not a separate claim of a clean one-variable randomized comparison.
No long run. Review saved mixed midpoint and balanced final on development950241
and the same native skill cohort; fresh confirmation950243 remains unused.

## Conditional bounded extension, not a relaxed long-launch gate

The balanced16k checkpoint retains city mean70.31 vs69.19 and raises the native
conditional urgent-choice probability51.5%→56.7%,priority18/32,reserve1/16.
If balanced32k final retains>=95% parent development mean with no lost scoring
cities and improves urgent-choice probability to>=60% or priority to>=20/32,
one additional32,768 balanced decisions (148M seeds,LR.001,fast tail) is justified
to test continued learning/transfer. Keep the original long-launch gate unchanged:
substantial independently confirmed city-score improvement and retained service.
Do not launch eight hours merely because a narrow practice metric improved.

Balanced32k final meets the bounded-extension condition: development74.65625
versus69.1875 (+7.9%),25/32 scoring retained; urgent-choice probability78.33%,
priority26/32. Reservation remains0/16. Extend32,768 decisions at148M as declared,
with one targeted curriculum adjustment: reserve episodes start after a fixed
six-second native warmup (future pair normally appears8–16s after original start,
so remaining wait is2–10s). Warmup reads no future time, gives no teacher actions
or training reward, and leaves road stock intact. Original zero-warmup validation
is unchanged. This tests easier positive-reward discovery and transfer; it is
not a claim that the full-delay exercise is solved.

Use one bounded segment of the detached runtime-snapshot runner (hours .0001,
segment-rollouts4,16 workers) for this extension. The tiny time target ends after
that32768-decision segment; its two-city review is workflow evidence only. This
also exercises balanced/fast-tail/reporting options end-to-end. The eight-hour
launch remains conditional on the original substantive gates. The earlier512-
decision/two-city runner smoke completed successfully; its checkpoint is excluded
from candidate selection and not used as the extension parent.

If an extension checkpoint passes development selection and original-delay skill
retention, use the reserved64-city600s confirmation RNG950243 and a separately
predeclared32-city1200s cohort RNG950245 against the calibrated parent. The latter
must retain>=95% mean and scoring-city count; the main independent cohort must
meet the original>=20% gain/positive paired interval gate. These suites remain
unrun until candidate selection; do not tune on their outcomes and call them
fresh again. The earlier1200s cohort950244 has already been examined.

## Task-homogeneous PPO minibatch test

Extension final80.0 versus69.1875,paired10.8125 [−5.34375,27.625],priority28/32,
reservation0/16. Prefer its midpoint82.75/priority30/32 as the next experimental
parent; preserve both. Easier starts create positive training returns but have
not transferred reservation. Hypothesis: global minibatch advantage normalization
mixes large city-return variation with much smaller reservation-return variation.
This is not yet an isolated/proven cause; log actual per-task rollout advantage
mean/std and return std before each optimizer update.

Opt-in CityTaskRolloutBuffer shuffles examples within fixed worker tasks, then
shuffles the task-homogeneous minibatches. PPO's existing per-minibatch advantage
normalization now operates within city/reserve/priority separately. All samples,
old likelihoods,values,returns and action masks stay aligned and appear once per
full sampling epoch. Native rewards,critic targets,PPO loss,learning rate,policy
architecture and inherited optimizer state are unchanged. This does change the
relative learning emphasis between tasks; report it as a sampler experiment.

Budget32,768 decisions,150M seeds,LR.001,balanced16 workers,512/128/four maximum
epochs,6s reserve warmup and validated fast tail. Save every rollout; review16k
and32k on development950241 and original native141M lessons. Sixteen Python tests
pass; exact loaded weights/Adam/counters and nine native actor probes verified.
Use one bounded runtime-snapshot segment, not eight hours. Independent950243 and
longer950245 remain unused; original long-launch thresholds remain unchanged.

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

Frozen extension midpoint independently tested on reserved64-city RNG950243,600s,against calibrated parent. Cohort is consumed once outcomes are seen; not reusable as fresh confirmation. Return-advantage reviews queued behind this to cap concurrent evaluation workers at8. No candidate selection based on these independent outcomes before launch.

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


## Bridge-enabled parent selection and next bounded city trial

Supersede automatic balanced continuation: calibrated bridge1200 development mean230.97 exceeds conservation parent185.53 and city-only final220.0. Preserved balanced24,576 checkpoint is evaluated before final parent selection. If it does not beat calibrated reference, use the existing zero-output wide initialization (SHA9d9c9c95...) whose calibrated actor parity passes1,024 bridge-enabled observations across8 consumed development trajectories. These checks only sample initial~100 native seconds; zero initialized residual heads preserve inherited logits by construction. Existing weights are retained. Fresh optimizer state in this older initialization is explicitly recorded, not presented as resuming conservation optimizer progress.

Next bounded test, if needed: pure native-city delivery PPO, bridge-enabled1200s,16workers,512steps,4epochs,batch128,gamma1/GAE1,LR.0001,vf1e-5,seed168M. Budget65,536 decisions with per-rollout saves and32,768 midpoint. No practice rehearsal, road penalty, new bridge-choice head, planner or teacher actions. Review midpoint/final on the same32 development cities against bridge-enabled calibrated reference and report change from own start. Use matched600s retention and native exercises for a selected improvement. Only a frozen substantial development improvement proceeds to unused64-city1200s confirmation950247; original20% gain/positive interval/no lost scoring-count requirements remain unchanged. A bounded test is not the authorized long launch.


### Bridge reference midpoint and conditional learning-rate check

Measured32,768-decision midpoint: mean231.0 vs calibrated230.96875,29/32 scoring each; paired delta0.03125,95% interval[−61.8140625,62.90703125]. New targets served170 vs175,stockout arrivals54 vs44. No learned score gain established. Complete predeclared65,536 trial; no promotion from unchanged development mean.

If final fails substantial-gain development gate, test a separate32,768-decision city-only trial from the same zero-output wide initialization, same168M training seeds/1200s/bridge profile/16workers/512steps/batch128/4epochs/GAE1/vf1e-5, but baseLR.001 versus.0001. Save16k midpoint and32k final. This compares learning rate at the same initialization and decision budget (low-rate32k midpoint), unlike older higher-rate trials starting a conservation-trained policy on the dry-road interface. Preserve KL.03 and gradient clipping. Rationale: current per-rollout approximateKL~4e-6–3e-5 and small actor changes, weak critic explained variance; these suggest a rate test, not proof that larger steps will help. Evaluate both saved high-rate policies on the same32 consumed development cities; only a frozen substantial improvement proceeds to unused confirmation. No automatic long run or gate relaxation.


### Real-city recorded starts — preparation, not demonstrated improvement

Engineering hypothesis: give PPO more decisions in actual expanding cities, rather than further optimizing synthetic reservation exercises or merely raising the global learning rate. New optional CityRecordedStartEnv reconstructs a native city by replaying a frozen existing policy prefix only during reset. These actions are not labels, PPO samples, reward, a route planner, or actions imposed after reset. The policy controls every subsequent legal connection/Wait decision and receives subsequent native deliveries only. Three workers in four use recorded starts; one retains ordinary cold starts. Default training/evaluation remains unchanged without --city-starts. The runner freezes and hashes the manifest alongside source and host.

Six native checks pass: exact world/visible motion-history replay, exclusion of prefix score/actions, subsequent reward/trips identity, explicit evaluation-reset bypass,32 exact cold transitions, rejection of corrupt replay and wrong host. The smoke prefix uses a consumed development seed for testing only and must never be used as training data. Separate dataset generation now uses128 seeds170000000..170000127, fixed280s prefixes of the calibrated reference; retain only native-live states with completed service, selected using prefix-visible outcomes only. Exclude failed/nonserving prefixes with recorded reasons. Future state/action information never selects learner actions. No policy update or long launch is part of dataset preparation.


### Broader rate result and predeclared recorded-start pilot

Frozen higher-rate midpoint fails broader64-city bridge1200 retention: calibrated262.765625 vs candidate231.546875,61/64 scoring each; delta−31.21875,95% interval[−83.00078125,19.579296875]. This supersedes the favorable32-city midpoint mean as a promotion argument. No fresh confirmation consumed. No previously tried PPO candidate is promoted.

Proceed with one bounded recorded-start mixture after dataset/native replay/integration checks:128 requested training seeds170M, prefixes at280s generated by calibrated reference, retain live serving starts without looking ahead. Require at least64 retained starts. Start the same actor-equivalent wide initialization, LR.0001,vf1e-5,16workers (12 recorded/4 cold),cold seeds172M,512 rollout steps,batch128,4epochs,GAE1,1200s,bridges. Budget65,536 decisions; checkpoint each rollout,32k midpoint/final matched32-city full-start evaluation. Report cold/warm training scores separately; warm rewards exclude prefix deliveries. Hypothesis is more native midgame practice and shorter reward delays; not a claim of causality or improvement. Existing cold-only low-rate result remains comparison context, but changed seed/data distribution prevents calling this a perfectly controlled one-variable study. If selected candidate passes substantial development gain, verify600s/skills and broader retention, then unused64-city confirmation950247. Original20% positive-interval/no fewer scoring-cities gate remains. This is not an overnight run.

Implementation checks so far:6 native replay checks and5 existing runner/reporting/gradient tests pass; Python compilation passes. Default environment/evaluation unaffected without --city-starts. Native simulator and reward rules unchanged.


### 2026-11-24 — recorded midpoint and isolated critic-rate test preparation

Measured recorded-start midpoint32,768 full-start evaluation:211.3125 versus calibrated230.96875,29/32 scoring each; paired delta−19.65625,95% interval[−110.003125,67.96875]. No demonstrated transfer gain. Let the predeclared65,536-decision budget and final review complete before selecting another trainer. Evidence: recorded-midpoint-longer-comparison.json.

Engineering hypothesis: low-rate value fitting remains weak (explained variance near zero), while the higher global-rate pilot reached0.2123 but regressed city scores. Isolate the dedicated value-head rate without increasing actor or shared-encoder rates. Added optional --critic-lr-scale to trainer/runner; defaultNone preserves existing behavior. Dedicated-group validation rejects shared/missing groups and nonfinite/nonpositive scales. Two unit tests pass; real checkpoint save/load check preserves every weight, Adam moment and2048 optimizer steps, with source checkpoint SHA unchanged. Evidence: critic-scale-checkpoint-check.json and training/test_city_optimizer_settings.py. No causal conclusion yet; changing only the head may not resolve shared representation or long-term credit assignment.

Conditional bounded next trial, only if recorded final fails strong development gain: start unchanged actor-equivalent wide initialization, cold-city seeds168000000,16workers,4rollouts×512=32,768 decisions,1200s native horizon,bridges,baseLR.0001,vf1e-5,GAE1,batch128,4epochs. Set dedicated value-head lr_scale1.0 instead of0.1; all actor/shared scales unchanged. Validated exact-parity evidence cache is enabled. Evaluate16,384 midpoint and32,768 final on the same32 development cities950241 against calibrated baseline; compare final to previous low-rate equal-budget midpoint. No recorded-start mixture in this controlled test. Preserve all checkpoints. Strong-gain, retention, and unused independent-confirmation gates remain unchanged before any long launch. No promise of improvement.


### 2026-11-24 — critic result and longer credit-window test

Critic-head-only rate final32,768:220.53125 versus calibrated230.96875,29/32 scoring each; paired−10.4375,95% interval[−75.81328125,52.12578125]. Equal-budget low-rate control231.0, paired−10.46875 [−77.4703125,57.659375]. New targets served166 versus reference175,stockouts48 versus44. Faster value fitting did not establish better city strategy; no promotion and no long launch. All trial/reviewer processes exited. Checkpoints retained.

Next engineering hypothesis: longer rollout windows reduce reliance on weak bootstrap values for delayed road payoffs. Prior cold run has90 completed games,median713.5 decisions;60 exceed512,6 exceed1024. These lengths motivate testing but do not prove causal failure. At gamma1/GAE1, completed trajectories have direct sampled return targets; unfinished tails use a learned bootstrap. Optional --rollout-steps now flows through frozen runner/config to existing trainer, default512 unchanged. Three runner tests and Python compilation pass.

Predeclared bounded comparison: same original wide initialization,16 cold-city workers,seeds168M,baseLR.0001,vf1e-5,original critic scale0.1,bridge1200 profile. Change rollout length512→1024,with2rollouts=32,768 total decisions and same1024 maximum Adam steps. Compare midpoint16,384 and final32,768 against calibrated baseline and final against previous low-rate32,768. The policy-update timing necessarily changes with rollout length. Do not carry the unsuccessful critic-rate checkpoint into this test. No planner/imitation/reward/physics change. Expected buffer arrays8.33GiB,conservative doubled flatten storage16.67GiB; no concurrent evaluation during training. Reject2048-per-worker variant for RAM risk. Review both frozen checkpoints sequentially after trainer exits. Existing strong gain,retention,independent confirmation gates remain; this is not an overnight run.


### 2026-11-24 — continuation outcome: long launch remains unjustified

Longer-rollout final32,768 review:213.03125 versus calibrated230.96875,29/32 scoring each;paired delta−17.9375,95% interval[−78.75,39.7203125]. Against equal-budget low-rate32,768 control231.0:delta−17.96875 [−79.28203125,39.25078125]. New targets served177 versus reference175,zero-stock arrivals43 versus44; these do not establish score improvement. Midpoint239.15625 did not persist. Reject global promotion despite the runner's favorable two-city local guard. Both midpoint/final audits preserve protected opening probes and change permitted tensors only. All trainers/reviewers completed; no further training queued and no long session launched.

Measured conclusion: recorded midgame exposure, faster dedicated critic learning, and longer rollout credit windows each exercised their intended mechanism but did not establish substantial full-city score gains. Current implementation performs PPO updates with finite losses, legal masks and gradients; that is not proof of effective strategy learning. Retain calibrated reference and all trial checkpoints separately. Fresh confirmation950247 and reserved950245 remain unconsumed. The user's desired reliable large score increase remains unresolved; no claim that another long run will work.

Next investigation should focus on decision-level policy failures and whether return targets/representation distinguish successful expansion from unproductive building, with a falsifiable intervention and native-score validation. This is an open research direction, not an implemented fix or a claim that more time alone suffices. Existing optional experimental knobs retain their defaults; no unsuccessful candidate is made the default model.


### 2026-11-24 — strategy bottleneck explanation and proposed diagnostic

User asks what prevents strategy learning and what to do next. Source-verified limitation: current CityWideStrategyPolicy freezes inherited features/actor and learns additive road/Wait corrections plus critic/spatial branch. Both actor correction paths are multiplied by established, which requires more than two building entrances and at least one graph-connected matching home/destination pair. Therefore these runs cannot change decisions before that gate, including early layout/resource choices. This intentionally protected earlier skills; it is a proven learning restriction, not proven sole cause of the full-city plateau. Do not describe the entire actor as frozen: permitted road/Wait probabilities do change.

Measured additional limitations: weak return prediction;512-step windows yield about32% native-terminal return coverage in the prior cold run;1024 increases coverage but failed score improvement. Diagnostic states average358 legal roads and inherited road preferences are often sharp; this suggests limited exploration, not proof that exploration alone blocks learning. Recent32k trials contain only42–45 completed cities,so decision counts are not independent strategy examples; unsuccessful short runs do not prove a longer run cannot learn. Missing deletion,motorways,signals,roundabouts and learned weekly choices limit eventual capability but are not established causes of this plateau.

Proposed next experiment, not implemented or launched by this explanation: retain reference checkpoint; test a zero-initialized trainable correction active throughout the city (including opening), against current gated correction. First test ability to improve native delivery score on a small repeated set of4–8 real training cities,with different action RNG and untouched evaluation cities. No planner,teacher actions or shaped construction reward. Fixed training cities are a fitting diagnostic,not evidence of generalization. If even this cannot improve,investigate return targets/representation and exploration before more diverse training. If it fits but fails held-out cities,focus on diversity/generalization. Evaluate opening skills as a regression check instead of making all early decisions permanently untrainable. Require repeatability across training RNG seeds and fresh full-city validation before long launch. No certainty claimed and no new training started.
