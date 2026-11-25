from pathlib import Path
import argparse,json,numpy as np
p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
def read(p):
 s=json.loads((p/'summary.json').read_text());rows=[json.loads(x) for x in (p/'games.jsonl').read_text().splitlines()];return s,{(r['seed'],r['action_seed']):r for r in rows if r['model']==0}
a,x=read(args.parent);b,y=read(args.candidate)
assert x.keys()==y.keys() and a['host_sha256']==b['host_sha256'] and a.get('horizon',600)==b.get('horizon',600)
assert a.get('allow_bridges',False)==b.get('allow_bridges',False), 'Action profiles differ'
keys=sorted(x);rng=np.random.default_rng(142915);draw=rng.integers(len(keys),size=(12000,len(keys)))
measures={'score':lambda r:r['trips'],'new_targets_served':lambda r:sum(t['served']>0 for t in r['targets']),'stockouts':lambda r:sum(t['arrival_stock']==0 for t in r['targets']),'paid_units':lambda r:r['paid_units'],'outside_observed_routes':lambda r:r['outside_routes']}
paired={}
for label,fn in measures.items():
 d=np.array([fn(y[k])-fn(x[k]) for k in keys]);paired[label]=dict(mean_delta=float(d.mean()),interval95=np.quantile(d[draw].mean(1),[.025,.975]).tolist())
parent,candidate=a['results']['0'],b['results']['0']
r=dict(parent_run=str(args.parent),candidate_run=str(args.candidate),parent=parent,candidate=candidate,paired=paired,relative_mean=candidate['mean_score']/parent['mean_score'] if parent['mean_score'] else None,lost_scoring_seeds=[k[0] for k in keys if x[k]['trips']>0 and y[k]['trips']==0],gained_scoring_seeds=[k[0] for k in keys if y[k]['trips']>0 and x[k]['trips']==0])
r['retention_pass']=candidate['scoring_games']>=parent['scoring_games'] and candidate['mean_score']>=.95*parent['mean_score']
r['strong_gain_pass']=r['retention_pass'] and r['relative_mean']>=1.2 and paired['score']['interval95'][0]>0
args.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
