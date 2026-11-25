from pathlib import Path
import json,numpy as np
base=Path('output/training');out=Path('docs/training/road-reserve-learning-2026-11-23')
def read(run,file='summary.json'):return json.loads((base/('city-road-reserve-'+run)/file).read_text())
first=json.loads((out/'city-comparison.json').read_text());conf=read('city-confirmation-01')
a,b=conf['results']['0'],conf['results']['1']
assert conf['host_sha256']==read('city-candidate-01')['host_sha256']
retained=b['scoring_games']>=a['scoring_games'] and b['mean_score']>=.95*a['mean_score']
suite1=read('city-candidate-01','suite.json');suite2=read('city-confirmation-01','suite.json')
overlap=sorted({r[0] for r in suite1}&{r[0] for r in suite2})
parent=read('independent-practice-01');repair=read('repaired-practice-01')
summary=dict(first_city_comparison=first,confirmation=conf,retention_gate=retained,city_suite_overlap=overlap,practice_parent_and_uncorrected=parent,practice_repaired=repair)
(out/'final-results.json').write_text(json.dumps(summary,indent=2)+'\n')
print('CITY',a['mean_score'],b['mean_score'],a['scoring_games'],b['scoring_games'],'GATE',retained,'CI',b['paired_score_delta_and_interval'])
for lesson in repair:
 print(lesson,[(x['successes'],x['mean_score'],x.get('mean_stock_at_arrival'),x['mean_stock']) for x in [parent[lesson]['0'],parent[lesson]['1'],repair[lesson]['0']]])
old=(out/'README.md').read_text()
old=old.replace('Status: bounded experiments in progress. No promotion or overnight run.','Status: completed. One bounded PPO run, a diagnosed transfer failure, a separate feature repair and two city suites. No overnight run.')
old=old.replace('Results, run measurements and local-only checkpoint hashes will be archived here\nwhen final comparisons complete. Prior reports remain historical.','Results, run measurements, source snapshots and local-only checkpoint hashes are archived below. Prior reports remain historical.')
old=old.replace('-99','- 99').replace('-Eight','- Eight').replace('-Zero','- Zero').replace('-Native','- Native').replace('-Mean','- Mean').replace('-Reset','- Reset').replace('-Compressed','- Compressed')
old+='''

## Bounded run and repair

`city-road-reserve-pilot-01` added8,192 PPO decisions,454 episodes in223.7 seconds
with16 workers. Parent: calibration-only city candidate; initial and all saves
remain intact. Midpoint at4,096 decisions had273 episodes. Native rewards stayed
finite and the episode ledger matched deliveries. Only six Wait weights and the
critic changed. No road ranking or opening weights changed.

Development later-target success parent/mid/final:2/8,3/8,6/8. Arrival stock:
1.125,2.5,3.125. Longer routes stayed8/8; delayed connections improved6/8→8/8.
Quiet stock at episode end improved0→0.875. Final was frozen before city review.

City review exposed this experiment's feature defect: missing local progress
was treated as blocked. Two native replays showed169/145 such decisions and
>99% Wait with211/274 legal builds and no visible approach blocker. This is
archived in `wait-context-diagnosis.json`. The first city's results are now
diagnostic evidence, not the final independent confirmation.

`CityVisibleReserveFeatures` restricts the last two inputs to visible blocked
shop approaches. Its separately saved checkpoint has exactly the same learned
weights; no extra PPO or probability calibration occurred. Initial nine-lesson
probabilities and road rankings remain unchanged. Native replay checks show
fallback to the parent's probabilities when there is no visible blocker.
The old class and rejected checkpoint remain reproducible. This repair is an
engineering contribution; conservation weights came from native-score PPO.
Copied optimizer moments are not proof of safe long-run continuation after the
input semantics change. No such continuation was launched.

## Full-city measurements

All games are sampled native Los Angeles, maximum600 simulation seconds,
road-or-Wait with inherited scripted weekly picks. Paired scenario/action seeds
within each suite;32 games per policy. These are not leaderboard scores.

| Suite / policy | Mean score | Scoring games | New targets served | Arrivals with zero stock | Mean paid road units |
|---|---:|---:|---:|---:|---:|
'''
for label,m in [('First / original',first['models']['original']),('First / calibrated parent',first['models']['calibrated_parent']),('First / unrepaired PPO',first['models']['reserve_ppo']),('Confirmation / calibrated parent',a),('Confirmation / repaired PPO',b)]:
 old+=f"| {label} | {m['mean_score']:.2f} | {m['scoring_games']}/32 | {m['new_targets_served']} | {m['new_target_stockouts']} | {m['mean_paid_units']:.2f} |\n"
delta,ci=b['paired_score_delta_and_interval']
old+=f"\nConfirmation paired mean change: **{delta:+.2f}**,95% bootstrap interval [{ci[0]:+.2f},{ci[1]:+.2f}] (12,000 resamples). Retention gate: **{'PASS' if retained else 'FAIL'}** (at least95% of parent mean and no fewer scoring cities). Shared city seeds between the two suites: {overlap}.\n"
old+='''
The second suite RNG940128 was fixed after the feature correction and was not
used for further changes. The first suite RNG940127 diagnosed the defect.
Comparing means across suites does not isolate the repair; use each paired
parent comparison. Outside-observed-route counts are diagnostic, not proof that
every such road is waste. Source JSONL and hashes are archived.

## Fresh practice checks

Sixteen cases per lesson, seeds132000000 onward. Construction success means a
new target receives a native delivery; demand success means urgent target
service. Quiet success is not conservation. Junction success counts are not
meaningful; compare scores. Native controls supply no actions to PPO.

| Measure | Parent | Unrepaired PPO | Repaired PPO |
|---|---:|---:|---:|
'''
for ex,label in [('midgame-network-join','One-edge success /16'),('midgame-network-route','Longer-route success /16'),('midgame-network-delay','Delayed success /16'),('midgame-network-reserve','Future-target success /16')]:
 values=[parent[ex]['0'],parent[ex]['1'],repair[ex]['0']];old+='| '+label+' | '+' | '.join(str(v['successes']) for v in values)+' |\n'
for ex,label,key in [('midgame-network-reserve','Stock at future target arrival','mean_stock_at_arrival'),('midgame-network-quiet','Quiet stock left','mean_stock'),('traffic-junction-low-live','Light-traffic mean score','mean_score'),('traffic-junction-high-live','Heavy-traffic mean score','mean_score')]:
 values=[parent[ex]['0'],parent[ex]['1'],repair[ex]['0']];old+='| '+label+' | '+' | '.join(f"{v[key]:.2f}" for v in values)+' |\n'
lessons=['traffic-priority-established','traffic-priority-established-swap']
old+='| Urgent service /32 | '+str(sum(parent[l]['0']['successes'] for l in lessons))+' | '+str(sum(parent[l]['1']['successes'] for l in lessons))+' | '+str(sum(repair[l]['0']['successes'] for l in lessons))+' |\n'
old+='''
The reserve controls compare saving then connecting, wasting then attempting the
same route, and permanent Wait. Some useful prebuilding is possible from visible
stubs and is legitimate; success does not imply all successful games waited until
spawn. The policy still lacks proof of arbitrary-city traffic management or
optimal inventory planning. High-stock contexts extend beyond the narrow
curriculum's2–5-road budget; transfer tests matter more than parameter signs.

## Checks, artifacts and decision

Nine final focused Python tests pass. All99 native suites,364 ordinary-city
transition comparisons, reset isolation, forced-Wait native parity, exact
zero-initialization/opening and conditional-road checks pass. A native replay
verifies the context repair falls back to the parent's probabilities in the
misclassified state. No old checkpoint was overwritten and main stays untouched.

- [Run and evaluation measurements](measurements/output/training/)
- [Detailed results](final-results.json), [first paired comparison](city-comparison.json)
- [Native repair check](context-repair-native-check.json), [parameter audit](repaired-audit.json)
- [Final Python checks](python-final-checks.txt), [native checks](native-checks.txt)
- [Local-only checkpoint and host hashes](local-only-artifacts.json)
- [Source snapshot](source/), [archive checksums](manifest.json)

New checkpoint: `output/training/city-road-reserve-repaired-01/candidate.zip`.
Original failed transfer: `output/training/city-road-reserve-pilot-01/final.zip`.
Reference: `output/training/city-five-stage-cold-initial-01/candidate.zip`.
Weights/binaries stay local; the archive includes only code and small evidence.
'''
old+=('\nThe repaired checkpoint passes the specified retention gate. Treat it as a bounded experimental continuation candidate; further longer-horizon/multi-map validation and a small resume check are still required before an overnight run.\n' if retained else '\nThe repaired checkpoint fails retention. Keep the calibrated parent selected. Conservation practice gains do not justify replacing it or launching a long run; next work must distinguish useful network expansion from unproductive spending in mixed city states.\n')
(out/'README.md').write_text(old)
