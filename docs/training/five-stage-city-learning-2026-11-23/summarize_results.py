from pathlib import Path
import json,numpy as np
base=Path('output/training');out=Path('docs/training/five-stage-city-learning-2026-11-23')
def rows(n):return [json.loads(x) for x in (base/('city-five-stage-'+n)/'games.jsonl').read_text().splitlines()]
def model(rs,i):return {(r['seed'],r['action_seed']):r['trips'] for r in rs if r['model']==i}
def compare(a,b):
 assert a.keys()==b.keys()
 d=np.array([b[k]-a[k] for k in sorted(a)])
 rng=np.random.default_rng(142915)
 return dict(n=len(d),mean_delta=float(d.mean()),paired_bootstrap_95=np.quantile(d[rng.integers(0,len(d),size=(12000,len(d)))].mean(1),[.025,.975]).tolist())
dev=[model(rows('city-references-01'),1),model(rows('cold-city-01'),0),model(rows('cold-city-01'),1)]
ind=[model(rows('independent-city-01'),i) for i in range(3)]
report={}
for name,group in [('development',dev),('independent',ind)]:
 report[name]=dict(models=[dict(mean=float(np.mean(list(m.values()))),scoring=sum(v>0 for v in m.values()),games=len(m)) for m in group],calibrated_vs_original=compare(group[0],group[1]),trained_vs_original=compare(group[0],group[2]),trained_vs_calibrated=compare(group[1],group[2]))
report['overlap_city_seeds']=sorted({k[0] for k in dev[0]} & {k[0] for k in ind[0]})
(out/'final-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
runs=[]
for suffix in ['stability-01','connections-01','waiting-01','connections-02','waiting-02','connections-03','waiting-03','traffic-01','mixed-01','relations-01','relations-mixed-01']:
 p=base/('city-five-stage-'+suffix);c=json.loads((p/'config.json').read_text())
 if suffix=='stability-01':
  s=json.loads((p/'state.json').read_text())['checkpoints'][-1];d=s['decisions']-425984;e=s['completed_games'];t=s['training_seconds'];lr=c['pilot']['learning_rate']
 else:
  s=json.loads((p/'complete.json').read_text())['checkpoints'][-1];d=s['added_decisions'];e=s['episodes'];t=s['seconds'];lr=c['learning_rate']
 runs.append(dict(run=suffix,added_decisions=d,episodes=e,seconds=t,lr=lr,forced_wait_compression=c.get('collapse_forced_wait',False),parent=c.get('parent',c.get('start'))))
(out/'run-register.json').write_text(json.dumps(dict(runs=runs,total_added_decisions=sum(r['added_decisions'] for r in runs)),indent=2)+'\n')
print('RUNS',json.dumps(runs))
