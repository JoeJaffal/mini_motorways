"""Archive matched development curves; never selects/promotes a checkpoint."""
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    root=a.archive
    rows=[];comparisons=[]
    for budget in (65536,131072,262144):
        arms={}
        for arm in ('control','strong'):
            games=[json.loads(x) for x in (root/'evaluation'/f'{arm}-{budget}'/'games.jsonl').read_text().splitlines()]
            arms[arm]={(x['exercise'],x['seed'],x['action_seed']):x for x in games}
            for exercise in ('small-city-offset-single','small-city-offset-stock'):
                group=[x for x in games if x['exercise']==exercise]
                rows.append(dict(arm=arm,budget=budget,exercise=exercise,games=len(group),
                                 **{k:float(np.mean([x[k] for x in group])) for k in
                                    ('score','first_served','paid_units','outside_routes','no_build','remaining_stock')}))
        assert arms['control'].keys()==arms['strong'].keys()
        for exercise in ('small-city-offset-single','small-city-offset-stock'):
            seeds=sorted({k[1] for k in arms['control'] if k[0]==exercise})
            rng=np.random.default_rng(251125)
            indices=rng.integers(0,len(seeds),size=(12000,len(seeds)))
            result=dict(budget=budget,exercise=exercise,clusters=len(seeds),differences={})
            for metric in ('score','first_served','paid_units','outside_routes'):
                diffs=np.array([np.mean([float(arms['strong'][k][metric])-float(arms['control'][k][metric])
                                        for k in arms['control'] if k[0]==exercise and k[1]==seed]) for seed in seeds])
                result['differences'][metric]=dict(mean=float(diffs.mean()),ci95=np.quantile(diffs[indices].mean(1),[.025,.975]).tolist())
            comparisons.append(result)
    (root/'results.json').write_text(json.dumps(dict(curves=rows,paired_comparisons=comparisons),indent=2)+'\n')
    lines=['# Matched road-cost continuation results','',
           'Both learners completed the predeclared budget. These are development evaluations of one training seed per arm, not independent confirmation or proof of convergence. No automatic promotion or further training.', '',
           '| Decisions | Arm | Stock | Success | Native score | Paid roads | Outside observed routes |',
           '|---:|---|---|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f"| {row['budget']} | {row['arm']} | {'tight' if row['exercise'].endswith('single') else 'generous'} | {row['first_served']:.1%} | {row['score']:.3f} | {row['paid_units']:.3f} | {row['outside_routes']:.3f} |")
    lines += ['', 'Final .04 minus control, clustered paired 95% bootstrap intervals:', '']
    for c in comparisons[-2:]:
        lines.append(f"- {c['exercise']}: "+'; '.join(f"{k}: {v['mean']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]" for k,v in c['differences'].items()))
    lines += ['', 'A road outside a route observed within60seconds is not proven permanently useless. Raw games, recipe, checkpoints/hashes, seed cursors, gradient and parameter-update records are archived alongside. Weights and compiled host remain local-only under output/training/road-cost-continuation-01. The disposable smoke runs are excluded.', '',
              'Full-city transfer, independent training-seed replication and untouched confirmation remain pending. The final and intermediate development scores must be reviewed before choosing the next experiment.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
