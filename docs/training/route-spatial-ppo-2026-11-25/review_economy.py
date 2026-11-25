"""Describe resource use without treating failure or inaction as economy."""
import json
from pathlib import Path
from statistics import mean
r=Path('docs/training/route-spatial-run-2026-11-25')
status=json.loads((r/'status.json').read_text())
assert status['status']=='complete'
def rows(p): return [json.loads(x) for x in p.read_text().splitlines()]
def key(g): return (g['exercise'],g['seed'],g['action_seed'])
base=rows(r/'evaluation/outcome-initial/games.jsonl')
before={key(g):g for g in base}
curve=[]
for label in ('initial',str(status['budget']//4),str(status['budget']//2),str(status['budget'])):
    games=rows(r/f'evaluation/outcome-{label}/games.jsonl')
    cases={}
    for case in sorted({g['exercise'] for g in games}):
        group=[g for g in games if g['exercise']==case]
        successful=[g for g in group if g['task_success']]
        retained=[g for g in successful if before[key(g)]['task_success']]
        cases[case]=dict(games=len(group),successes=len(successful),
            successes_with_remaining_stock=sum(g['road_stock']>0 for g in successful),
            failures_with_remaining_stock=sum(not g['task_success'] and g['road_stock']>0 for g in group),
            all_mean_paid_units=mean(g['paid_units'] for g in group),
            all_mean_builds=mean(g['road_actions'] for g in group),
            retained_successes=len(retained),
            retained_success_mean_paid_change=mean(g['paid_units']-before[key(g)]['paid_units'] for g in retained) if retained else None,
            retained_success_mean_build_change=mean(g['road_actions']-before[key(g)]['road_actions'] for g in retained) if retained else None)
    curve.append(dict(added_decisions=0 if label=='initial' else int(label),cases=cases))
repeats={}
for steps in (status['budget']//4,status['budget']//2):
    live=r/f'live-outcome-{steps}/games.jsonl'
    if live.exists():
        same=rows(live)==rows(r/f'evaluation/outcome-{steps}/games.jsonl')
        assert same, f'Live/final repeat mismatch at {steps}'
        repeats[str(steps)]=dict(exact_game_rows=True,independent_evidence=False)
report=dict(curve=curve,planned_review_repeats=repeats,limits='Consumed development games. Lower construction after failure is not successful economy. Common-success changes are conditional on both models succeeding and do not measure population-wide causal efficiency. No optimal route length is estimated or supplied.')
(r/'economy-review.json').open('x').write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
