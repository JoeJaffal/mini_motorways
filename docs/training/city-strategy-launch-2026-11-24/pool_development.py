"""Pool disjoint consumed city cohorts; never label this fresh confirmation."""
from pathlib import Path
import argparse,json
from evaluate_city_service import summarize
p=argparse.ArgumentParser();p.add_argument('--references',nargs='+',type=Path,required=True);p.add_argument('--candidates',nargs='+',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
assert len(args.references)==len(args.candidates)
rows=[];identities={0:set(),1:set()};hosts=set();horizons=set();profiles=set();seen=set()
for reference,candidate in zip(args.references,args.candidates):
 pairs=[]
 for model,folder in enumerate((reference,candidate)):
  summary=json.loads((folder/'summary.json').read_text());name=summary['models'][0]
  identities[model].add(summary['sha256'][name]);hosts.add(summary['host_sha256']);horizons.add(summary.get('horizon',600));profiles.add(summary.get('allow_bridges',False))
  games=[json.loads(line) for line in (folder/'games.jsonl').read_text().splitlines()];games=[r for r in games if r['model']==0]
  keys={(r['seed'],r['action_seed']) for r in games};assert len(keys)==len(games)
  pairs.append(keys);rows.extend(dict(r,model=model) for r in games)
 assert pairs[0]==pairs[1]
 seeds={seed for seed,_ in pairs[0]};assert not seen&seeds;seen|=seeds
assert all(len(x)==1 for x in identities.values()) and len(hosts)==len(horizons)==len(profiles)==1
stats=summarize(rows,2);a,b=stats[0],stats[1]
result=dict(note='Pooled disjoint consumed development cases; selection evidence only, not fresh confirmation.',reference_directories=list(map(str,args.references)),candidate_directories=list(map(str,args.candidates)),sha256={k:next(iter(v)) for k,v in identities.items()},host_sha256=next(iter(hosts)),horizon=next(iter(horizons)),allow_bridges=next(iter(profiles)),results=stats,relative_mean=b['mean_score']/a['mean_score'],retention_pass=b['mean_score']>=.95*a['mean_score'] and b['scoring_games']>=a['scoring_games'],strong_gain_pass=b['mean_score']>=1.2*a['mean_score'] and b['scoring_games']>=a['scoring_games'] and b['paired_score_delta_and_interval'][1][0]>0)
args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(reference=a['mean_score'],candidate=b['mean_score'],paired=b['paired_score_delta_and_interval'],retained=result['retention_pass']),indent=2))
