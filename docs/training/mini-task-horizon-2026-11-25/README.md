# Longer native lessons: bounded comparison

Engineering decision,25 November2026: a frozen128-game critic probe confirms poor calibration on60-second small-city lessons. Original pair return standard deviation2.03 versus value standard deviation6.95; at300seconds return variation13.86 and return/advantage correlation0.895 versus0.168 at60. The131kreset model has much worse finite-lesson value calibration. These are descriptive diagnostics, not proof that a baseline causes wrong expected policy gradients. [Source and measurements](../mini-task-repair-2026-11-25/value-calibration/summary.json).

Separate frozen continuation games show that first-only service eventually fails while both-served games survive300seconds. Native reward is correct; the earlier short deadline omits important consequences. No road penalty, planner, imitation labels or simulation change is introduced.

## Predeclared design
Use the preserved original checkpoint, not a development-selected regressed continuation. Both arms receive262144added decisions,16workers,8city+4two-arrival+4single lessons; four lessons use the same own-policy reset bank. Same parent/Adam,seed11424,cold training scenarios240000000onward, native score,task minibatches,optimizer/KL settings. Only small-city training deadline differs:300seconds(long-window),60seconds(short-control). Long-window runs first, then short-control. Per-forward frozen-computation cache enabled in both after CPU/GPU parity and disposable PPO validation. This is a new study, not an edit or restart of the active reset comparison. Shared hardware may affect elapsed speed; no throughput comparison will be claimed.

Both arms evaluated at65536/131072/262144added decisions on identical300-second small-city and600-second city development suites. Legacy four geometry tasks retain60seconds. Evaluate the parent on that same protocol before comparing returns. Retained original city baseline is also archived; no gain against a weaker baseline will be claimed. Preserve every rollout checkpoint. No early stopping for a low score; stop only for technical invalidity, nonfinite updates or stalled owned processes.

Development screening: retain short geometry (no more than one additional failure), at least14/16tight single destinations served,8/16both pairs served, city mean at least retained original and at most one extra zero game. These are engineering screens, not statistical proof. If a candidate meets them, freeze it before using reserved fresh mini236M andcity237M cohorts, compare matched parent/candidate behavior and city uncertainty, inspect ordinary/poor replays. Overnight readiness needs a substantial city improvement (target at least20percent mean with positive paired95percent interval), useful skill retention and no material increase in zero-score cities. No automatic promotion, launch or guarantee. If screening fails, inspect full curves before deciding whether a longer bounded continuation is justified.

The prepared source in runtime-source/ is the actual study snapshot. Weights and native binaries remain local under output/training/mini-horizon-comparison-01. Original reset comparison continues its full declared budget unchanged and retains its known replay-export finalization recovery.

Monitor: `tail -F /home/mohammadjaffal/mini_motorways/output/training/mini-horizon-comparison-01/run.log`.


## Evaluation resource bound
After observing3.4GiB available RAM with concurrent learners and baseline review, limited future duration-study evaluations to2CPU workers. Evaluator scheduling only; same games/order/seeds/checkpoint/actions and CPU inference. Already running baseline retains loaded original worker count. Initial evaluator source preserved under initial-evaluator-source; exact before/after hashes in evaluation-resource-limit.json. Training runtime and original reset comparison are unchanged.


## First65k development review
Long-window65,536: city137.53125versus126.09375original,31/32scoringversus30/32; pairedmean+11.4375,95percentinterval[−7.1570,31.4703]. Tight single8/16unchanged; generous10/16; firstpair10/16andboth4/16versusoriginalfirst8/16/both3/16on the same300-second protocol. Shortskillsretained. This is preliminary positive movement but the interval includeszero, task screening targets are unmet, and the matched60-second duration control has not run yet. Continue full declared budget; no promotion/overnight launch or attribution to duration alone. Earlier experiments also had transient early city gains, so inspect the full curve. Full records long-65536-review.json.


## 131k development review
City146.6875,31/32scoring; versus126.09375original,delta+20.59375,paired95percentinterval[2.4375,40.375]. Tight9/16,generous11/16,firstpair11/16,both3/16; shortskillsretained. Positive development movement, but taskgatesunmet and final/control/freshconfirmation pending. Continue declaredbudget. See long-131072-review.json.


## Longer-lesson midpoint visual audit, 25 November 18:31 Beirut
Measured exact paired city replay selected nearest median gain among positive paired changes, tie lowest seed/action RNG; seed184000000. Original0deliveries/151.15seconds, midpoint28/270.4. All final native counters and checkpoint hashes match frozen evaluation. Figure inspected: midpoint completes the opening red route but builds disconnected fragments and excess roads, exhausts stock and eventually fails. Native future buildings differ between trajectories; not identical late-state control. This is evidence of useful opening connection behavior in this selected game, not reliable conservation/strategy. See docs/training/mini-task-horizon-2026-11-25/midpoint-city-replay/ (selection, exact checks, frames, HTML, figure, behavior summary); sources replay_midpoint.py/plot_midpoint.py. Full budget and short control continue; no promotion.
