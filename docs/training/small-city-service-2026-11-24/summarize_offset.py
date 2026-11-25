from pathlib import Path
import json,numpy as np,shutil
r=Path('docs/training/small-city-service-2026-11-24');root=Path('output/training');allrows={};practice={}
for label,name in [('parent','small-city-offset-baseline-01'),('final','small-city-offset-final-01')]:
 p=root/name;allrows[label]=list(map(json.loads,(p/'games.jsonl').read_text().splitlines()));practice[label]=json.loads((p/'summary.json').read_text())['results']
 dest=r/'evaluation'/label;dest.mkdir(parents=True,exist_ok=True)
 for fn in ['games.jsonl','summary.json','suite.json']:shutil.copy2(p/fn,dest/fn)
parent={(x['split'],x['exercise'],x['seed'],x['action_seed']):x for x in allrows['parent']};paired={}
for split in ['train','validation']:
 for exercise in ['small-city-single','small-city-offset-pairs']:
  group=[x for x in allrows['final'] if x['split']==split and x['exercise']==exercise];metrics={}
  for metric in ['score','first_served','both_served','outside_routes']:
   deltas=np.array([np.mean([float(x[metric])-float(parent[(x['split'],x['exercise'],x['seed'],x['action_seed'])][metric]) for x in group if x['seed']==seed]) for seed in sorted({x['seed'] for x in group})]);rng=np.random.default_rng(23911);draw=rng.integers(len(deltas),size=(12000,len(deltas)));metrics[metric]=dict(delta=float(deltas.mean()),interval95=np.quantile(deltas[draw].mean(1),[.025,.975]).tolist())
  paired[split+'/'+exercise]=metrics
city=json.loads((root/'small-city-offset-city-01/summary.json').read_text())['results'];baseline=json.loads((root/'city-whole-baseline-01/summary.json').read_text())['results'];k='validation/small-city-offset-pairs';p=practice['parent'][k];f=practice['final'][k]
gates=dict(practice_both_improves_10pp=f['both_served']-p['both_served']>=.1,practice_first_retained=f['first_served']>=p['first_served'],practice_outside_routes_not_worse=f['outside_routes']<=p['outside_routes'],city_mean_retained=sum(x['mean'] for x in city.values())>=.95*sum(x['mean'] for x in baseline.values()),city_scoring_retained=sum(x['scoring'] for x in city.values())>=sum(x['scoring'] for x in baseline.values()))
result=dict(practice=practice,paired=paired,city=city,city_parent=baseline,gates=gates,all_gates_pass=all(gates.values()),limits='One training RNG; paired bootstrap clusters both action RNGs by scenario. Practice validation translations excluded from training. City suite is previously used development data.')
(r/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
