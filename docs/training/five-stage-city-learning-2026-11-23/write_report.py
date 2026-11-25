from pathlib import Path
import json
out=Path('docs/training/five-stage-city-learning-2026-11-23');base=Path('output/training')
r=json.loads((out/'final-comparison.json').read_text());reg=json.loads((out/'run-register.json').read_text())
p=json.loads((base/'city-five-stage-independent-practice-01/summary.json').read_text())
text='''# Five-stage city learning — 23 November 2026

All five experiment stages and eleven bounded PPO runs are complete. **The
capability gates are not all passed. No overnight training was launched.**
Work stayed in the user-confirmed `/home/mohammadjaffal/mini_motorways` checkout
on `Maskable-PPO`. Existing checkpoints and uncommitted work were preserved.

The original protected checkpoint remains the conservative reference. Keep the
calibrated initialization and PPO-trained candidate as separately measured
experimental variants. Do not substitute either into old long-run commands.

## City retention

Sampled native Los Angeles games, maximum 600 simulation seconds. Original,
calibrated zero-initialization and identically calibrated trained candidate use
the same scenario/action seeds within each suite. Development was used to make
choices; independent results were not used for further updates.

| Suite | Original mean / scoring games | Calibration only | Calibration + PPO |
|---|---:|---:|---:|
'''
for suite in ['development','independent']:
 a=r[suite]['models'];text+='| '+suite+' | '+' | '.join(f"{m['mean']:.2f} / {m['scoring']}/{m['games']}" for m in a)+' |\n'
text+='\nPaired mean-score changes and 95% bootstrap intervals:\n\n'
for suite in ['development','independent']:
 for key in ['calibrated_vs_original','trained_vs_original','trained_vs_calibrated']:
  v=r[suite][key];lo,hi=v['paired_bootstrap_95'];text+=f"- {suite}, {key.replace('_',' ')}: {v['mean_delta']:+.2f} [{lo:+.2f}, {hi:+.2f}].\n"
text+=f"\nCross-suite shared city seeds: {r['overlap_city_seeds']}. See [paired data](final-comparison.json).\n"
text+='''
The trained candidate lost one scoring development city (30/32 versus31/32).
That fails the strict retention gate even though its development mean exceeds
the original. Do not erase this failure by pooling suites. City means are noisy;
controlled practice gains are not evidence that all city regressions are fixed.

## Independent practice

Sixteen fresh cases per lesson; demand combines both location/color variants.
Native evaluator controls confirm feasible choices without supplying training
actions. Numbers below are measured outcomes, not guarantees on unseen cities.

| Measure | Original | Calibration only | Calibration + PPO |
|---|---:|---:|---:|
'''
for lesson,label in [('midgame-network-join','One-edge target served /16'),('midgame-network-route','Longer-route target served /16'),('midgame-network-delay','Delayed target served /16')]:
 text+='| '+label+' | '+' | '.join(str(p[lesson][str(i)]['successes']) for i in range(3))+' |\n'
text+='| Urgent target served /32 | '+' | '.join(str(sum(p[l][str(i)]['successes'] for l in ['traffic-priority-established','traffic-priority-established-swap'])) for i in range(3))+' |\n'
for lesson,label,key in [('midgame-network-quiet','Quiet-board road units left','mean_stock'),('traffic-junction-low-live','Light-traffic mean score','mean_score'),('traffic-junction-high-live','Heavy-traffic mean score','mean_score')]:
 text+='| '+label+' | '+' | '.join(f"{p[lesson][str(i)][key]:.2f}" for i in range(3))+' |\n'
text+='''
Construction gains already exist before new PPO: attribute those to calibration.
PPO adds a clear demand-priority gain against that same calibrated initialization.
Light traffic improves but still falls below the fixed feeder control (14.875);
heavy traffic remains similar. Quiet Wait keeps two roads and averages6.4375,
while the trained candidate spends them and also averages6.4375. That exercise
does not reward conservation over its short horizon. Waiting is not solved.

## Every bounded training run

All names below have the prefix `city-five-stage-` under `output/training/`.
Budgets count added decisions. Forced-Wait compression changes the meaning of a
decision; these counts are not comparable measures of simulated time.

| Run | Decisions | Completed episodes | Seconds | Actor LR | Forced Wait compressed |
|---|---:|---:|---:|---:|---|
'''
for x in reg['runs']:text+=f"| {x['run']} | {x['added_decisions']:,} | {x['episodes']:,} | {x['seconds']:.1f} | {x['lr']:g} | {x['forced_wait_compression']} |\n"
text+=f"\nTotal added decisions across all branches: {reg['total_added_decisions']:,}. Relation runs use critic LR equal to 1% of actor LR. Parent paths/hashes are in [run register](run-register.json) and archived configs.\n"
text+='''
- Stability-01: start/mid/final city means81.59/80.28/75.22 with27/32
  scoring each. Midpoint passes the predeclared retention check; final fails.
- Connections-01: one-edge6/8 and longer2/8, unchanged. Waiting-01:
  delayed3/8 unchanged and quiet spends both units.
- Connections-02: one-edge7/8, longer2/8. Waiting-02: delayed5/8.
- Connections-03: one-edge8/8 but longer falls to1/8. Waiting-03:
  delayed5/8 and quiet builds1.375 on average; no robust conservation result.
- Traffic-01 and mixed-01: broad exploration means18.56 and16.22 on the
  development city suite, versus85.03 original. Rejected. Their fresh practice
  also regressed. Previous checkpoints remain intact.
- Relations-01: narrower native-score learning improves development demand
  from8/16 at zero initialization to12/16 in warm sampling. Mixed continuation
  completes with only relation coefficients and critic changing; old actor
  and opening reference remain frozen.
- Warm relation city means29.34 at initialization,30.03 after traffic and33.00
  after mixed: insufficient. Subsequent *inference* calibration restores route
  selection; compare zero-init and learned versions separately in tables above.
- Retaining the old generic prior while scaling learned corrections is another
  calibration-only variant: development89.50,30/32 scoring, not preferred.

## Five-stage verdict and next work

1. **Stability:** tested, but final checkpoints still regress. Keep retention
   checks and original rollback; more training is not automatically improvement.
2. **Useful connections:** substantial controlled improvement, largely from
   inference calibration. Both calibrated variants pass all16 longer routes.
3. **Waiting:** delayed service improves to15/16; quiet-stock conservation fails.
   Next proposed lesson must make saved stock matter to later native deliveries.
4. **Demand/congestion:** PPO learns the tested demand preference (32/32 fresh).
   Light-traffic adaptation is partial; arbitrary congestion management remains.
5. **Mixed city:** bounded training and independent evaluation completed, but
   robust city-score retention/high-score readiness is not established.

The next work should address the future consequence of unnecessary construction,
then test transfer on city seeds held out from this report. Keep generic service
and demand candidates separate until city retention passes. No new reward
penalty, planner, long training or automatic promotion is authorized by this
report itself.

## Records and local checkpoints

- [Detailed changes, attribution, limitations and checks](REPORT_NOTES.md)
- [Original plan and chronological adaptive decisions](PLAN.md)
- [All small run/evaluation evidence](measurements/output/training/)
- [Checkpoint/binary hashes and local paths](local-artifacts.json)
- [Source context](source-context.json) and [archive checksums](manifest.json)
- [Final seven Python checks](python-final-checks.txt), [99 native suites](native-checks.txt),
  [1,116 legality checks](legality-checks.txt), [364-transition parity](host-parity.json)

Reference (local only):
`output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip`.
Calibration-only candidate: `output/training/city-five-stage-cold-initial-01/candidate.zip`.
Learned demand candidate: `output/training/city-five-stage-cold-final-01/candidate.zip`.
These files are preserved; weights/binaries are deliberately excluded from the
archive. Tests are bounded native simulation, not commercial-game leaderboard
proof. This report supersedes the active-work paragraphs; older reports remain
historical.
'''
(out/'README.md').write_text(text)
