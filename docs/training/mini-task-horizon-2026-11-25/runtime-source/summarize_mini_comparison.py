"""Matched reset-curriculum learning curves; never automatically promote."""
import argparse
import json
from pathlib import Path
import numpy as np
from summarize_expansion_comparison import paired

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();r=a.archive
    def read(path):return [json.loads(line) for line in path.read_text().splitlines()]
    base=read(r/'evaluation/city-initial/games.jsonl')
    baseline=[x for x in read(r/'audit/games.jsonl') if x['model']=='original']
    for x in baseline:x.setdefault('action_seed',x['seed']+103)
    geometry=json.loads((r/'audit/geometry.json').read_text());gates={(x['exercise'],x['seed']):x['opening_gate'] for x in geometry}
    curves=[];contrasts=[]
    for budget in (65536,131072,262144):
        arms={}
        for arm in ('cold-control','reset-curriculum'):
            city=read(r/f'evaluation/city-{arm}-{budget}/games.jsonl');practice=read(r/f'evaluation/practice-{arm}-{budget}/games.jsonl');arms[arm]=city
            row=dict(arm=arm,added_decisions=budget,city_mean=float(np.mean([x['trips'] for x in city])),city_scoring=sum(x['trips']>0 for x in city),city_delta=paired(city,base,('trips','paid_units','outside_routes')),practice={})
            for task in sorted({x['exercise'] for x in practice}):
                group=[x for x in practice if x['exercise']==task];old=[x for x in baseline if x['exercise']==task]
                entry=dict(games=len(group),**{k:float(np.mean([x[k] for x in group])) for k in ('score','success','paid','after_first','outside_routes','later_served')},delta=paired(group,old,('score','success','paid','outside_routes','later_served')))
                hard=[x for x in group if gates.get((task,x['seed'])) is False]
                if hard:entry['outside_opening_gate']=dict(games=len(hard),successes=sum(x['success'] for x in hard))
                row['practice'][task]=entry
            curves.append(row)
        contrasts.append(dict(added_decisions=budget,reset_minus_cold=paired(arms['reset-curriculum'],arms['cold-control'],('trips','paid_units','outside_routes'))))
    result=dict(curves=curves,contrasts=contrasts,limits='Single training seed per recipe; repeated development evaluation; fresh empty-board/city confirmation required. Selected reset bank performance is not transfer evidence.')
    (r/'results.json').write_text(json.dumps(result,indent=2))
    lines=['# Mini-task reset curriculum comparison','',result['limits'],'','| Decisions | Recipe | City score | Scoring /32 | Tight single | Later pair |','|---:|---|---:|---:|---:|---:|']
    for x in curves:
        lines.append(f"| {x['added_decisions']} | {x['arm']} | {x['city_mean']:.2f} | {x['city_scoring']} | {x['practice']['small-city-offset-single']['success']:.1%} | {x['practice']['small-city-offset-pairs']['later_served']:.1%} |")
    lines+=['','Final checkpoint city comparisons versus original:','']
    for x in curves[-2:]:
        d=x['city_delta']['trips'];lines.append(f"- {x['arm']}: {d['mean']:+.2f}; paired95% interval {d['ci95']}.")
    lines+=['','No automatic promotion or overnight extension. Inspect trajectories, hard-layout performance and fresh confirmation before selecting a candidate.']
    (r/'RESULTS.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
