"""Report fixed endpoints, paired city uncertainty and finite-budget limits."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();root=a.archive
    city={};lessons={};learner={}
    for label in ('original','parent','unchanged','critic-rate'):
        folder=root/'evaluation'/f'city-{label}'
        city[label]=dict(summary=json.loads((folder/'summary.json').read_text()),
                         games=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines()])
    for label in ('unchanged','critic-rate'):
        for budget in (393216,524288):
            folder=root/'evaluation'/f'lesson-{label}-{budget}'
            lessons[f'{label}-{budget}']=json.loads((folder/'summary.json').read_text())['results']
        records=list(csv.DictReader((root/'measurements'/label/'progress.csv').open()))
        learner[label]=next(row for row in reversed(records) if row.get('train/value_loss'))
    comparisons=[]
    for candidate,baseline in [('unchanged','parent'),('critic-rate','parent'),('critic-rate','unchanged'),('critic-rate','original'),('unchanged','original')]:
        base={(x['seed'],x['action_seed']):x for x in city[baseline]['games']}
        games=city[candidate]['games'];assert {(x['seed'],x['action_seed']) for x in games}==base.keys()
        seeds=sorted({x['seed'] for x in games});rng=np.random.default_rng(251125)
        draws=rng.integers(0,len(seeds),size=(12000,len(seeds)))
        metrics={}
        for key in ('trips','paid_units','outside_routes'):
            delta=np.array([np.mean([x[key]-base[(x['seed'],x['action_seed'])][key] for x in games if x['seed']==seed]) for seed in seeds])
            metrics[key]=dict(mean=float(delta.mean()),ci95=np.quantile(delta[draws].mean(1),[.025,.975]).tolist())
        comparisons.append(dict(candidate=candidate,baseline=baseline,clusters=len(seeds),metrics=metrics))
    report=dict(city={k:v['summary'] for k,v in city.items()},lesson=lessons,city_comparisons=comparisons,final_learner_metrics=learner,
                limitations='One training seed; reused development maps; fixed final checkpoints; no promotion, fresh confirmation or commercial-game leaderboard claim.')
    (root/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Overnight critic-rate comparison —25November2026','',
           'Both arms resumed the same262144-decision cost.04 policy and added262144decisions. The only intended learning change was critic Adam rate: unchanged0.1 versus1.0 relative to the common base rate. Rewards, actor rates, masks and architecture remained fixed. No planner or imitation was added.','',
           '## Native city results','',
           'These are sampled600-second games with bridges enabled on16previously used development cities, two action RNGs each. They measure transfer from practice; the models were not trained on these city episodes.','',
           '| Model | Mean deliveries | Cities scoring /32 | Paid roads | Roads outside observed routes |',
           '|---|---:|---:|---:|---:|']
    for label,value in city.items():
        s=value['summary'];lines.append(f"| {label} | {s['trips']:.2f} | {s['scoring']} | {s['paid_units']:.2f} | {s['outside_routes']:.2f} |")
    lines += ['', 'Paired score differences, clustered by city with both action RNGs retained:', '']
    for c in comparisons:
        v=c['metrics']['trips'];lines.append(f"- {c['candidate']} minus {c['baseline']}: {v['mean']:+.2f},95%bootstrap interval[{v['ci95'][0]:+.2f},{v['ci95'][1]:+.2f}].")
    lines += ['', '## Practice curves','', '| Model/budget | Stock | Success | Native deliveries | Paid roads |', '|---|---|---:|---:|---:|']
    for label,groups in lessons.items():
        for key,s in groups.items():lines.append(f"| {label} | {'tight' if key.endswith('single') else 'generous'} | {s['first_served']:.1%} | {s['score']:.3f} | {s['paid_units']:.3f} |")
    lines += ['', '## Interpretation and remaining work','',
              'Positive mean changes are not automatically reliable gains; assess the paired intervals, scoring reliability and road spending together. A lower practice cost is not a full-city score improvement. Poor critic prediction can be measured without establishing that it is the sole cause of policy failure. These finite budgets do not establish convergence.', '',
              'No winner is automatically promoted. Independent training-seed replication, unseen-city confirmation and broader tools/weekly-choice competence remain untested here. All checkpoints and the original policy remain preserved. No further run is launched by this controller.', '',
              'Raw games, source snapshots, recipe, gradients, parameter updates and checkpoint hashes are archived. Weights and simulator binaries remain local-only under output/training/overnight-critic-comparison-01.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
