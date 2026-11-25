"""Report a bounded continuation against its restored parent and original."""
import argparse
import json
from pathlib import Path
import numpy as np
from summarize_expansion_comparison import paired


def summarize(root):
    read=lambda kind,label:[json.loads(s) for s in (root/'evaluation'/f'{kind}-{label}'/'games.jsonl').read_text().splitlines()]
    status=json.loads((root/'status.json').read_text());budget=status['added_decisions']
    parent=read('city','initial');original=read('city','retained-original');mini=read('practice','initial')
    curves=[]
    for count in (budget//4,budget//2,budget):
        city=read('city',f'road-learning-{count}');practice=read('practice',f'road-learning-{count}')
        row=dict(added_decisions=count,city_mean=float(np.mean([x['trips'] for x in city])),
            city_scoring=sum(x['trips']>0 for x in city),
            delta_parent=paired(city,parent,('trips','paid_units','outside_routes')),
            delta_original=paired(city,original,('trips','paid_units','outside_routes')),practice={})
        for task in sorted({x['exercise'] for x in practice}):
            group=[x for x in practice if x['exercise']==task];base=[x for x in mini if x['exercise']==task]
            row['practice'][task]=dict(games=len(group),first_served=sum(x['first_served'] for x in group),
                both_served=sum(x['both_served'] for x in group),
                delta_parent=paired(group,base,('score','first_served','both_served','paid','outside_routes')))
        curves.append(row)
    result=dict(policy_class=status.get('policy_class'),critic_features_detached=status.get('critic_features_detached',False),parent_city_mean=float(np.mean([x['trips'] for x in parent])),
        original_city_mean=float(np.mean([x['trips'] for x in original])),curves=curves,
        limits='One continuation seed, consumed development layouts, temporarily frozen Wait. Not a causal comparison against joint training; no automatic promotion, fresh confirmation or overnight launch.')
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Bounded road-learning continuation','',result['limits'],'',
        '| Added decisions | City mean | Scoring /32 | Tight served /16 | Both pairs /16 |',
        '|---:|---:|---:|---:|---:|']
    for row in curves:
        lines.append(f"| {row['added_decisions']} | {row['city_mean']:.2f} | {row['city_scoring']} | {row['practice']['small-city-offset-single']['first_served']} | {row['practice']['small-city-offset-pairs']['both_served']} |")
    lines += ['',f"Starting repaired parent mean: {result['parent_city_mean']:.2f}; retained original: {result['original_city_mean']:.2f}.",'',
        f"Critic feature detachment enabled: {result['critic_features_detached']}.",'',
        'Road/critic learning preserves existing Adam state. Native score remains the only reward. Wait is temporarily frozen to isolate road improvement after the measured joint-policy regression. This does not solve future timing strategy or prove every original action was correct.','']
    for reference in ('parent','original'):
        delta=curves[-1]['delta_'+reference]['trips']
        lines.append(f"Final minus {reference}: {delta['mean']:+.2f}; paired scenario-bootstrap95%interval {delta['ci95']}.")
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True)
    summarize(parser.parse_args().archive)
