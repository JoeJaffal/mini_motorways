"""Describe matched city/expansion learning curves without automatic promotion."""
import argparse
import json
from pathlib import Path
import numpy as np


def paired(candidate,baseline,metrics):
    original={(x['seed'],x['action_seed']):x for x in baseline}
    assert {(x['seed'],x['action_seed']) for x in candidate}==original.keys()
    seeds=sorted({x['seed'] for x in candidate});draw=np.random.default_rng(251125).integers(len(seeds),size=(12000,len(seeds)))
    result={}
    for metric in metrics:
        delta=np.array([np.mean([float(x[metric])-float(original[(x['seed'],x['action_seed'])][metric]) for x in candidate if x['seed']==seed]) for seed in seeds])
        result[metric]=dict(mean=float(delta.mean()),ci95=np.quantile(delta[draw].mean(1),[.025,.975]).tolist())
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();r=a.archive
    def read(kind,label):return [json.loads(x) for x in (r/'evaluation'/f'{kind}-{label}'/'games.jsonl').read_text().splitlines()]
    initial_city=read('city','initial');initial_practice=read('practice','initial');curves=[];contrasts=[]
    for budget in (65536,131072,262144):
        arms={}
        for arm in ('city-only','expansion'):
            city=read('city',f'{arm}-{budget}');practice=read('practice',f'{arm}-{budget}');arms[arm]=city
            item=dict(arm=arm,added_decisions=budget,city_mean=float(np.mean([x['trips'] for x in city])),
                      city_scoring=sum(x['trips']>0 for x in city),city_games=len(city),
                      city_delta_vs_initial=paired(city,initial_city,('trips','paid_units','outside_routes')),practice={})
            for task in sorted({x['exercise'] for x in practice}):
                group=[x for x in practice if x['exercise']==task];base=[x for x in initial_practice if x['exercise']==task]
                item['practice'][task]=dict(games=len(group),**{key:float(np.mean([x[key] for x in group])) for key in ('score','first_served','later_exists','later_served','both_served','paid_units')},
                                           delta_vs_initial=paired(group,base,('score','first_served','later_served','both_served','paid_units')))
            curves.append(item)
        contrasts.append(dict(added_decisions=budget,expansion_minus_city_only=paired(arms['expansion'],arms['city-only'],('trips','paid_units','outside_routes'))))
    result=dict(initial_city_mean=float(np.mean([x['trips'] for x in initial_city])),curves=curves,city_contrasts=contrasts,
                limits='One training seed per arm; city development suite reused; practice suite becomes development after repeated checkpoints. No independent confirmation, promotion or convergence claim.')
    (r/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Native-score expansion curriculum comparison','',
           'Both branches start from the exact retained original policy. City-only control and expansion curriculum each receive262144additional decisions. The curriculum uses eight city, four later-pair and four single-connection workers, with task-homogeneous minibatches for within-task advantage normalization. This compares a curriculum recipe, not task mix in isolation. Native deliveries are the only reward throughout. No planner, imitation, new road penalty or simulator change.','',
           '| Added decisions | Arm | City mean score | City games scoring /32 | Single success | First pair served | Both pairs served |',
           '|---:|---|---:|---:|---:|---:|---:|']
    for row in curves:
        single=row['practice']['small-city-offset-single'];pairs=row['practice']['small-city-offset-pairs']
        lines.append(f"| {row['added_decisions']} | {row['arm']} | {row['city_mean']:.2f} | {row['city_scoring']} | {single['first_served']:.1%} | {pairs['first_served']:.1%} | {pairs['both_served']:.1%} |")
    lines+=['',f"Original city mean: {result['initial_city_mean']:.2f}. Fixed final-checkpoint comparisons:",'']
    for row in curves[-2:]:
        v=row['city_delta_vs_initial']['trips'];lines.append(f"- {row['arm']} minus original: {v['mean']:+.2f}; paired95%interval[{v['ci95'][0]:+.2f},{v['ci95'][1]:+.2f}].")
    v=contrasts[-1]['expansion_minus_city_only']['trips'];lines.append(f"- Expansion minus city-only: {v['mean']:+.2f}; paired95%interval[{v['ci95'][0]:+.2f},{v['ci95'][1]:+.2f}].")
    lines+=['','Intervals resample scenario seeds with both action RNGs together. Practice success does not establish city improvement. Compare the entire curve and uncertainty; do not treat an early uncertain point as failure or a single high score as proof. Native city returns and finite lesson returns differ in scale; per-task advantage records preserve the diagnostic evidence.', '',
            'The prior reward audit found correct native delivery accounting. Repeated deliveries remain legitimate game points. All checkpoints are preserved; no automatic promotion or additional run follows. Any claimed gain needs independent training-seed replication and fresh city confirmation. See DIAGNOSIS.md and PLAN.md for rationale, preflight evidence, sources and limits.']
    (r/'RESULTS.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
