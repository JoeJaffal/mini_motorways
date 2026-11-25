# Five-stage city learning — 23 November 2026

User decision: implement and run all five proposed stages. The user explicitly
resolved the checkout discrepancy in favor of continuing
`/home/mohammadjaffal/mini_motorways` on `Maskable-PPO`. Preserve earlier changes
and checkpoints. No road planner, target-action imitation or shaped road reward.

Engineering plan, recorded before the curriculum results:

1. Continue the protected city candidate for ~3 active minutes at 1e-6; evaluate
   midpoint/final/start and repaired baseline on 32 paired cities, seed 731824.
   Retention gate: no fewer scoring cities and >=95% start mean. Passing this
   short test does not establish stability over hours.
2. Train useful connections with native one-edge and 2–4-edge service exercises,
   retaining full legal distractor choices. Initial budget 32,768 decisions.
3. Train delayed service with scarce stock plus supplied-network controls and
   immediate-service retention. Initial budget 32,768 decisions.
4. Train demand reversals and light/heavy live junction choices, using the same
   full-city observation/action model. Initial budget 32,768 decisions.
5. Mix full cities with all practice lessons in a bounded continuation. Compare
   the final, pre-mixture candidate and initial reference on predeclared city
   evaluation seed 826341 and 32 cities; repeat all controlled exercises.

Stages 2–5 branch from the original protected candidate independently of the
stability probe. Sequential saves are experimental candidates, not promotions.
Use disjoint training seed starts 110M/111M/112M/113M and validation 118.2M.
Stage-specific pre/post exercises determine whether each lesson improved.
A final development comparison uses 118.3M practice seeds; do not describe it
as proof of generalization to commercial gameplay or arbitrary traffic geometry.

Validation: native feasible-route controls, Wait controls, urgent-demand
reversal, light/heavy alternative controls, exact delivery reward accounting,
legal actions, finite PPO updates, frozen-reference preservation, and ordinary
city host parity. Named native reference edits are used only by evaluations.

Reward limitation: paused, harmless extra construction may be score-equivalent
to Wait when no future stock is needed. The quiet exercise is a retention probe;
delayed service creates an actual consequence for premature road spending.
High scores, congestion mastery, and successful completion of every learning
gate must be reported separately from completing these experiments.

## Adaptive changes after the first results

The stability midpoint passes the retention threshold (80.28 vs 81.59 mean,
27/32 scoring each); final fails mean retention (75.22). The original candidate
remains the reference. The first 32,768-decision connection pilot at 1e-5 matches
the before-test exactly: 6/8 one-edge and 2/8 longer-route successes. Its spatial
weights do change, so this is insufficient behavioral improvement, not a frozen
optimizer.

The junction baseline assigns the feeder about 5e-14 at one light board and
chooses the bypass on all eight light boards. A generic road-temperature probe
preserves Wait/build mass, opening probabilities and masks, while temperature
20 raises that feeder to about 7% of conditional build choices. This only creates
exploration; it is not a learned gain. A separately loadable feature class softens
the frozen reference road logits and leaves learned corrections unscaled.

Stop the original coordinator before its traffic/mixed jobs; its already-started
waiting pilot completes unchanged. Additional bounded candidates: connections-02
32,768 decisions at 3e-4 from connections-01; waiting-02 16,384 at 3e-4 from that;
traffic-01 65,536 at 3e-4 from an explicitly saved temperature-20 initialization;
mixed-01 32,768 at 1e-5. Training starts 114M and 115M keep the repeated lessons
separate. These changes are engineering experiments, with every earlier save
preserved and no automatic promotion. The larger traffic budget is necessary to
sample previously suppressed legal alternatives. The temperature's frozen
initial baseline must be compared separately from its PPO-trained result.

## Meaningful-decision rollout refinement

The stronger connection continuation improved one-edge success from 6/8 to 7/8,
with longer routes still 2/8. Waiting-01 matched its pretest. Inspection found
that after stock exhaustion the learner still records many forced Wait actions.
A new optional wrapper combines only transitions where Wait is the sole legal
action, preserves all native rewards (gamma=1), updates visible frame history,
and stops when any build becomes legal. All eight lesson controls matched exact
final native states and rewards; 60–120 forced turns often collapse into the
last construction decision. This changes GAE credit assignment and episode
throughput. Decision counts across modes are not equivalent amounts of play.

In this mode controlled lessons terminate at their specified finite measurement
window, avoiding bootstrap from an unmeasured continuation; ordinary city time
limits retain their existing truncation handling. Earlier pilots used time-limit
bootstrap, which may have weakened learning; no causal ablation establishes its
individual contribution. The already-started waiting-02 run finishes unchanged.
The revised coordinator was stopped before traffic or mixed training began.

Revised remaining budgets: connections-03 4,096 meaningful decisions (seed116M),
waiting-03 4,096 (117M), traffic-01 8,192 (112M) and mixed-01 8,192 (113M).
The first three use 3e-4; the mixed continuation uses 1e-5. These replace the
unexecuted larger raw-decision budgets above. Record actual completed games and
simulated time alongside decision totals. Traffic still uses a separately saved
temperature-20 initialization, and frozen posttests use ordinary one-second
Wait steps so comparisons remain on the original evaluation contract.

## Rejection of broad exploration and narrower representation repair

The first complete sequence failed transfer. On the predeclared 32-city suite,
original / pre-exploration / traffic / mixed means are 85.03 / 73.63 / 18.56 /
16.22, with 31/32 scoring each. The first mixed checkpoint also loses service
success on fresh practice boards. Reject both broad-exploration candidates.
Their artifacts remain intact. Neither a larger training mean nor merely
exploring more roads is a promotion criterion.

A direct feature probe shows zero service progress/join/urgency at both the
feeder and bypass on the native junction cases. The existing features focus on
unserved destinations and omit additional homes feeding an already-served shop.
The spatial actor could in principle learn this implicitly; the probe does not
prove this omission is the sole cause of its failure.

A narrower candidate branches from the original protected reference. It keeps
existing service corrections unscaled when softening the frozen generic road
prior. Ten new zero-initialized coefficients combine visible existing-component
home supply, candidate cycle edges, position-derived traffic counts/stopping,
displayed demand, and the existing service progress/urgency. No routes, reference
edits, future events or teacher targets enter the learner. All native legal
choices remain available. This is engineered representation, not a claim that
PPO discovered those input relationships.

The original generic actor and reference are frozen for this diagnostic; only
the new relation coefficients and critic learn. The trainable parameter set
changes, so this branch starts fresh Adam state while retaining policy weights
and counters. RelativeRateAdam gives the critic 1% of the actor's scheduled rate;
a direct numerical test verifies the ratio and scheduled-rate restoration.
The eight-feature prototype is preserved but not trained; the ten-feature
version additionally includes displayed demand on connected destinations.

Bounded extra budgets: relations-01 4,096 meaningful traffic decisions at actor
rate .03 / critic .0003 (seed119M), then relations-mixed-01 4,096 mixed decisions
at .003 / .00003 (120M). Compare zero-weight initialization separately from PPO.
Use the same 32-city development suite for comparability and fresh practice
seeds118.4M for final checks. This is a follow-up repair within stages four and
five, not a long-run promotion. The original reference remains selected.

## Final calibration and independent checks

After both relation PPO runs, saved two identical conditional-road calibrations:
zero-weight initialization and learned final. Road scale20 sharpens conditional
sampling while preserving Wait/build mass, legal mask, argmax and protected
opening. No PPO updates occur during calibration. The checkpoints retain warm
optimizer moments; long-run continuation needs its own bounded rate check.
A second retained-prior/rescaled-coefficient calibration was also evaluated,
with explicitly reset optimizer state, and was not preferred.

Development city means97.56 (calibrated zero-init) and93.53 (calibrated learned)
exceed original85.03, but scoring counts31/32 and30/32 versus31/32 mean the
learned candidate fails strict retention. Construction gains already occur at
zero-init. Demand gains appear only after PPO. These distinctions motivated a
final independent three-way32-city suite (RNG932617), and16 new cases per lesson
(seed118500000 onward), with native controls. No further updates use those
results. Final measurements, failed gates and next proposals are in README.md.
All eleven bounded runs are complete. No overnight session is launched.
