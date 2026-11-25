from pathlib import Path
import json,numpy as np,shutil
r=Path('docs/training/small-city-service-2026-11-24');root=Path('output/training');rows={};report={}
for label in ['parent','final']:
 p=root/f'small-city-confirm-{label}-01';rows[label]=list(map(json.loads,(p/'games.jsonl').read_text().splitlines()))
 assert len(rows[label])==32 and len({x['seed'] for x in rows[label]})==32
 report[label]=dict(games=32,mean=float(np.mean([x['trips'] for x in rows[label]])),scoring=sum(x['trips']>0 for x in rows[label]),paid_units=float(np.mean([x['paid_units'] for x in rows[label]])),outside_routes=float(np.mean([x['outside_routes'] for x in rows[label]])),stockout_arrivals=sum(t['arrival_stock']==0 for x in rows[label] for t in x['targets']),new_targets_served=sum(t['served']>0 for x in rows[label] for t in x['targets']))
 dest=r/'confirmation'/label;dest.mkdir(exist_ok=True,parents=True)
 for fn in ['games.jsonl','summary.json','suite.json']:shutil.copy2(p/fn,dest/fn)
a={x['seed']:x for x in rows['parent']};differences=[]
for x in rows['final']:
 assert x['action_seed']==a[x['seed']]['action_seed'];differences.append(dict(seed=x['seed'],parent=a[x['seed']]['trips'],final=x['trips'],delta=x['trips']-a[x['seed']]['trips']))
d=np.array([x['delta'] for x in differences]);rng=np.random.default_rng(241124);draw=rng.integers(len(d),size=(12000,len(d)))
report.update(delta=float(d.mean()),interval95=np.quantile(d[draw].mean(1),[.025,.975]).tolist(),wins=int((d>0).sum()),ties=int((d==0).sum()),losses=int((d<0).sum()),paired=differences,scope='32 previously unused city seeds; one action RNG per city, one training RNG. Frozen candidate selected before these results; no guarantee of generalization to other maps or leaderboard settings.')
(r/'confirmation-results.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='paired'})
