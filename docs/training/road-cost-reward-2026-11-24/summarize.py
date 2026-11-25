from pathlib import Path
import json,numpy as np,shutil
r=Path('docs/training/road-cost-reward-2026-11-24');root=Path('output/training');rows={};summary={}
for arm in ['parent','control','mild','strong']:
 p=root/f'road-cost-reward-eval-{arm}-01';rows[arm]=list(map(json.loads,(p/'games.jsonl').read_text().splitlines()));summary[arm]=json.loads((p/'summary.json').read_text())['results']
 dest=r/'evaluation'/arm;dest.mkdir(parents=True,exist_ok=True)
 for name in ['games.jsonl','suite.json','summary.json']:shutil.copy2(p/name,dest/name)
paired={}
for arm in ['control','mild','strong']:
 paired[arm]={}
 for ref in ['parent','control']:
  if arm==ref:continue
  lookup={(x['exercise'],x['seed'],x['action_seed']):x for x in rows[ref]};stats={}
  for condition in ['small-city-offset-single','small-city-offset-stock']:
   group=[x for x in rows[arm] if x['exercise']==condition];metrics={}
   for metric in ['first_served','score','paid_units','outside_routes','no_build']:
    ds=np.array([np.mean([float(x[metric])-float(lookup[(condition,x['seed'],x['action_seed'])][metric]) for x in group if x['seed']==seed]) for seed in sorted({x['seed'] for x in group})]);rng=np.random.default_rng(241127);draw=rng.integers(len(ds),size=(12000,len(ds)))
    metrics[metric]=dict(delta=float(ds.mean()),interval95=np.quantile(ds[draw].mean(1),[.025,.975]).tolist())
   stats[condition]=metrics
  paired[arm][ref]=stats
k='validation/small-city-offset-stock';gates={}
for arm in ['mild','strong']:
 gates[arm]=dict(success_retained=all(summary[arm][f'validation/{cond}']['first_served']>=max(summary[ref][f'validation/{cond}']['first_served'] for ref in ['parent','control']) for cond in ['small-city-offset-single','small-city-offset-stock']),outside_routes_10pct_lower=summary[arm][k]['outside_routes']<=.9*summary['control'][k]['outside_routes'],outside_routes_interval_below_zero=paired[arm]['control']['small-city-offset-stock']['outside_routes']['interval95'][1]<0,native_score_retained=summary[arm][k]['score']>=summary['control'][k]['score'])
diagnostics={}
for arm in ['parent','control','mild','strong']:
 diagnostics[arm]={}
 for condition in ['small-city-offset-single','small-city-offset-stock']:
  group=[x for x in rows[arm] if x['exercise']==condition];failed=[x for x in group if not x['first_served']];successful=[x for x in group if x['first_served']]
  lookups={a:{(x['seed'],x['action_seed']):x for x in rows[a] if x['exercise']==condition} for a in ['parent','control',arm]}
  common=[x for x in group if all(lookup[(x['seed'],x['action_seed'])]['first_served'] for lookup in lookups.values())]
  diagnostics[arm][condition]=dict(failed_games=len(failed),mean_failed_stock_left=float(np.mean([x['remaining_stock'] for x in failed])) if failed else None,mean_success_paid_units=float(np.mean([x['paid_units'] for x in successful])) if successful else None,mean_success_outside_routes=float(np.mean([x['outside_routes'] for x in successful])) if successful else None,common_success_games=len(common),common_success_outside_routes={a:float(np.mean([lookup[(x['seed'],x['action_seed'])]['outside_routes'] for x in common])) if common else None for a,lookup in lookups.items()})

report=dict(results=summary,diagnostics=diagnostics,paired=paired,gates=gates,passing=[a for a,g in gates.items() if all(g.values())],limits='One training RNG per arm;32 layouts with two sampling streams, shared geometry across stock conditions. This suite selects a candidate; not independent confirmation.')
(r/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
