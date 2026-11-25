from pathlib import Path
import json,numpy as np
base=Path('output/training');out=Path('docs/training/road-reserve-learning-2026-11-23')
def get(name):
 p=base/name;return json.loads((p/'summary.json').read_text()),[json.loads(s) for s in (p/'games.jsonl').read_text().splitlines()]
ref,rr=get('city-road-reserve-city-references-01');candidate,cc=get('city-road-reserve-city-candidate-01')
assert ref['host_sha256']==candidate['host_sha256']
sets=[{(r['seed'],r['action_seed']):r for r in rows if r['model']==idx} for rows,idx in [(rr,0),(rr,1),(cc,0)]]
assert sets[0].keys()==sets[1].keys()==sets[2].keys()
models=[ref['results']['0'],ref['results']['1'],candidate['results']['0']]
def compare(a,b):
 keys=sorted(a);rng=np.random.default_rng(142915)
 result={}
 for metric in ['trips','paid_units','outside_routes']:
  d=np.array([b[k][metric]-a[k][metric] for k in keys]);ci=np.quantile(d[rng.integers(0,len(d),size=(12000,len(d)))].mean(1),[.025,.975])
  result[metric]=dict(mean_delta=float(d.mean()),paired_bootstrap_95=ci.tolist())
 result['lost_scoring_seeds']=[k[0] for k in keys if a[k]['trips']>0 and b[k]['trips']==0]
 result['gained_scoring_seeds']=[k[0] for k in keys if a[k]['trips']==0 and b[k]['trips']>0]
 return result
result=dict(models=dict(zip(['original','calibrated_parent','reserve_ppo'],models)),versus_parent=compare(sets[1],sets[2]),versus_original=compare(sets[0],sets[2]),retention_gate=models[2]['scoring_games']>=models[1]['scoring_games'] and models[2]['mean_score']>=.95*models[1]['mean_score'])
# Check final suite against earlier development/independent city suites as well.
prior=set()
for name in ['city-five-stage-city-references-01','city-five-stage-independent-city-01']:
 for line in (base/name/'games.jsonl').read_text().splitlines():prior.add(json.loads(line)['seed'])
result['overlap_previous_city_seeds']=sorted({k[0] for k in sets[0]} & prior)
(out/'city-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
