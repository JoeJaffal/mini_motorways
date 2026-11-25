# Spatial road PPO: useful practice learning, failed city readiness

Completed 25 November 2026 at 23:45 Beirut. Decision: preserve the final as an experimental route checkpoint; do not promote it or launch an overnight continuation. The development screen fails short-skill retention, tight routes, both-pair service and city zero-game retention. Reserved confirmation seeds remain untouched.

## What was tested

A bounded 262,144-decision PPO continuation from the retained Wait01 actor/Adam, with 12 tight-stock and four generous-stock workers. No teacher actions, imitation updates or road planner were added. An independent frozen copy supplies Wait's visual features; the road encoder and road heads may learn. A fresh temporary critic predicts the practice return. Actual first delivery earns 1 plus a bounded remaining-stock/edit bonus; failure earns zero. Native city rewards and simulator rules remain unchanged.

Learning completed 15,945 episodes in 5,842.92 seconds. Final local-only checkpoint: `output/training/route-spatial-01/training/final.zip`, SHA `f8333fd9ff4ae46325bd675edbfc141288901740d28e654a94191c793fc97256`, lifetime 1,048,576 decisions. All 32 rollout preservation checks passed. Final reload, finite parameters/Adam and unchanged frozen weights/Adam also pass. The native export restores the retained native critic and preserves the actor; its default mode trains road heads only, so it is not an automatically approved full-strategy training configuration.

## Learning improved route completion

On the same consumed 64-game practice cohort, tight success rose 20→23→21→27/32 and generous success 25→26→29→31/32. At the endpoint, seven tight cases and six generous cases were gained, with no originally successful cases lost. This is useful PPO learning on these scenarios. It is not a fresh generalization claim.

Road economy did not improve comparably. Tight mean purchased units stayed 7.34375 and mean edits stayed 8.34375; successful games with stock left stayed 6/32. Generous mean purchased units changed 10.09375→9.9375, and successes with stock left 21→23/32. Among games successful for both models, mean paid-unit change was zero tight and −0.04 generous. These conditional comparisons are descriptive, not an optimal-route estimate.

The exact paired practice replays show a formerly disconnected route becoming continuous and another route becoming straighter without fewer edits. A separate lowest-key remaining failure still exhausts stock and leaves a gap near the home after extending away from the needed connection. This preserves both favorable and unfavorable evidence. The selected examples cannot establish the frequency of a particular geometric error across all games. Forced-Wait compression may observe delivery at a later endpoint; endpoint time is not necessarily first-delivery time.

## Native behavior did not meet the launch screen

The separate consumed native mini cohort uses 16 games per family and ordinary continued play, rather than ending at first delivery. Adjacent, bend and clear remain 16/16. Obstacles fall 14→12/16; tight routes rise 8→9/16; generous routes 11→14/16; first-pair service 11→14/16 and both-pair service 4→6/16. These are mixed improvements, below the declared 14/16 tight and 8/16 both-pair thresholds, with excess obstacle regression.

The city cohort contains 16 scenarios with two action draws each. Native city mean is **128.25**, scoring in **28/32** plays, versus parent **141.09**, scoring in **31/32**. Paired mean change −12.84 has scenario-cluster 95% interval [−40.97, 10.41]; do not call the mean decline conclusive. Three additional zero games versus the parent are a practical retention failure. Versus the original reference, mean change is +2.16 [−24.88, 30.31], with two additional zero games. This is not evidence of a reliable score gain. Paid units fall by six versus the parent, but outside-route units change only −0.125 with an interval crossing zero. Lower building totals, especially with more failed games, are not proof of better city resource use.

## Limits and next decision

One training seed, repeated development cohorts, and a larger budget plus different training scenarios than the preceding road-head-only study prevent attributing the gain solely to the representation change. The isolated single-pair fixtures cover three colors and no competing incompatible pair; native cities support more colors and multiple demands. Passing the fixture would still not establish general traffic or long-horizon strategy.

The next development priority is **retaining learned route completion while practicing affordable construction, obstacles and later arrivals together**. A future comparison should explicitly include retention practice, hold reward/optimizer/budget fixed between its arms, and inspect native city behavior at multiple checkpoints. Earlier mixed native-score curricula also failed, so merely adding city workers is not an established remedy. Reward compatibility, critic calibration after representation changes and task coverage need preflight checks before another combined study. This is a proposal, not an implemented fix or a prediction that more time will succeed.

No current candidate qualifies for the reserved fresh confirmation protocol. No overnight run is active. Preserve the original, Wait01 parent and this route checkpoint as separate named artifacts; do not replace the city reference with a practice winner.

## Evidence

- `review.json` / `RESULTS.md`: curve, paired city intervals and explicit development gates.
- `economy-review.json`: all-game and common-success resource use; exact live/official repeat checks.
- `final-integrity.json`: frozen state, changed trainable tensors, counters and reload checks.
- `learning-and-transfer.png` / `figure-source.json`: inspected figure and measurement hash.
- `outcome-replays/` and `remaining-failure-replay/`: exact selected traces, selection rules and inspected frames.
- `evaluation/`, `measurements/`, `runtime-source/`: small records and frozen source.
- `../route-spatial-ppo-2026-11-25/`: preflight, design, coverage and post-review sources.

Weights and native binaries remain local-only under output/. This archive is evidence, not a self-contained copy of the model/runtime.

## Representative native city replay

The paired play nearest the median score change across all 32 plays was replayed exactly (scenario184000000, action RNG193251). Parent176 versus final171 deliveries; both reach the600-second cap. First delivery31 versus30seconds; first stockout65 versus130seconds. The final nevertheless makes112 construction actions versus98 and ends with19roads versus43. Inspected frames show both serving an opening with extra branches, then different evolving layouts and later networks. The final is not uniformly worse at every timing measure, nor uniformly more economical. Native spawning layouts diverge with road choices, so the later frames are not identical-state counterfactuals. This example illustrates the distribution; it does not establish a general causal mechanism.

`final-city-replay/` retains the selection rule, exact traces, counter checks, behavior summary and inspected comparison.
