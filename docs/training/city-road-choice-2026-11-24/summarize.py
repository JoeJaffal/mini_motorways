from pathlib import Path
import json,numpy as np,shutil
root=Path.cwd();rec=root/'docs/training/city-road-choice-2026-11-24'
paths=dict(reference='city-whole-baseline-01',joint='city-whole-whole-eval-01',roads='city-road-choice-roads-eval-01')
rows={};result={}
for name,path in paths.items():
 p=root/'output/training'/path
 rows[name]=list(map(json.loads,(p/'games.jsonl').read_text().splitlines()))
 result[name]=json.loads((p/'summary.json').read_text())['results']
 target=rec/'evaluation'/name;target.mkdir(parents=True,exist_ok=True)
 for fn in ('games.jsonl','summary.json','suite.json'):shutil.copy2(p/fn,target/fn)
pairs={}
for comparison in ('reference','joint'):
 base={(x['seed'],x['action_seed']):x for x in rows[comparison]};pairs[comparison]={}
 for split in ('repeated','heldout'):
  group=[x for x in rows['roads'] if x['split']==split]
  deltas=np.array([np.mean([x['trips']-base[x['seed'],x['action_seed']]['trips'] for x in group if x['seed']==seed]) for seed in sorted({x['seed'] for x in group})])
  rng=np.random.default_rng(142915);draw=rng.integers(len(deltas),size=(12000,len(deltas)))
  pairs[comparison][split]=dict(delta=float(deltas.mean()),interval95=np.quantile(deltas[draw].mean(1),[.025,.975]).tolist(),city_differences=deltas.tolist(),wins=sum(x['trips']>base[x['seed'],x['action_seed']]['trips'] for x in group),losses=sum(x['trips']<base[x['seed'],x['action_seed']]['trips'] for x in group))
report=dict(results=result,paired_roads_minus=pairs,limits='Eight city clusters per split, two action RNGs each, one training RNG. Previously used development cities, not independent confirmation.')
(rec/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
