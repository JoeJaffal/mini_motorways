# Whole-city PPO learning: observed play and matched trials

All three bounded trials and reviews are complete. No reliable score gain over reference,no promotion,and no long session. See [complete results](RESULTS.md) and [interactive replay comparison](compare-play.html). Working checkout `/home/mohammadjaffal/mini_motorways`,branch `Maskable-PPO`. Existing changes and checkpoints retained.

The current strategy corrections cannot change decisions before an established matching connection. New whole-city corrections start at zero and preserve identical initial policy/value behavior,but can learn throughout the opening and later expansion. The inherited prior stays intact. No road planner,demonstration actions,new reward or simulator physics changes.

## Observed reference play

- [First anchor replay](watched-reference/replay.html),seed184000000/action193251:score0,native death151.15s,roads first exhausted26s. Branches and a loop consume inventory before the destination connects;late moving cars do not produce a delivery before death.
- [Second anchor replay](watched-reference-success/replay.html),seed184000003/action193254:first delivery13s,score158 at600s. Initial service succeeds,but later network includes many loops/branches.51 of115 paid units are outside routes observed assigned during the replay;this is not proof that every such unit is permanently useless.
- Both anchors were selected before trained candidate results. Frames/actions/figures and plotting source are retained here.

## Matched experiment

Eight repeated native training cities184000000..184000007; eight separate cities185000000..185000007. Two fixed action RNG replicates per city,600s limit. Baseline mean126.25 repeated and125.9375 separate,15/16 scoring each. Paired uncertainty resamples cities,not individual action replicates. Compare only identical horizons.

Gated and whole-city arms each receive32,768 decisions,16workers,512steps,4rollouts,LR.0001,vf1e-5,original critic scale. Training runs serialize; frozen final evaluations can run together afterward. These are fitting diagnostics,not evidence of broad city mastery or an overnight launch gate.

Initial verification:256 exact actor/value comparisons;identical weights;opening actor gradient0 gated versus2.86916 whole;reset-cycle/bypass checks;three policy/reporting tests. Both arms' first8 completed episodes match exactly before updates. All checks preserve the reference checkpoint.

Existing continuing-game semantics bootstrap surviving600s cutoffs. An optional finite-horizon diagnostic was added separately and parity-checked over729 native transitions;it changes only final learning termination flags,not native score/physics. Active trial snapshots retain their original continuing semantics. Conditional follow-up and limits are recorded in [plan](PLAN.md).

Completed run log:
```bash
tail -n 30 /home/mohammadjaffal/mini_motorways/output/training/city-whole-finite-01/finite.log
```

See [chronological history](../../../training/EXPERIMENT_HISTORY.md),[plan](PLAN.md),[initial checks](initial-checks.json),[matched first rollout](first-rollout-matched-check.json),and[local artifact hashes](local-artifacts.json). Weights/native binaries remain local-only. `archive.py` preserves measurements and source alongside a manifest.

## Completed matched results

| Model | Repeated-city mean | Separate-city mean |
|---|---:|---:|
| Reference |126.25|125.94|
| Gated control32k |101.88|115.38|
| Whole-city midpoint16k |119.00|95.00|
| Whole-city final32k |129.50|133.75|

Whole versus gated on repeated cities:paired+27.625,city-cluster95%[4.6875,52.6875];on separate cities+18.375,[−17.75156,54.25156]. This favors removing the restriction within this training run,but whole versus reference gains remain uncertain. Whole final loses one scoring separate-city case and has more stockout arrivals. No promotion.

[Compare the two preselected games interactively](compare-play.html). Final replay scores0→175 and158→172. On32 fresh action RNGs for the first layout at180s,opening success is27/32 reference,28/32 midpoint,27/32 final. Selected replay improvement is not reliable opening improvement.

At the first divergent decision (decision7,time4s),reference/new Wait probabilities are0.3600/0.3202;conditional-road TV0.001812. Holding road preferences fixed while changing Wait reproduces the new sampled road;changing road preferences alone retains the old road. This read-only probability counterfactual explains the first divergence only,not all later outcomes. Evidence:[first-divergence.json](first-divergence.json). No counterfactual action is used as a training label.

The comparison HTML's four city/policy selections and end-of-timeline controls execute correctly in a JavaScript VM with stub DOM/canvas. This is a logic check,not a browser rendering claim. Native frame figures were visually inspected.

Finite-horizon follow-up:32k decisions from unchanged whole-city initialization,same settings/seeds,only cutoff training semantics differ. This fitting objective optimizes600s deliveries explicitly and is not a production lifelong-score objective. The completed finite model is not promoted;repeated/separate means121.50/116.44.
