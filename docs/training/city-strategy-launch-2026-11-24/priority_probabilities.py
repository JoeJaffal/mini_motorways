from pathlib import Path
import json,numpy as np
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24'
base=[json.loads(x) for x in (out/'city-strategy-skill-review-02/games.jsonl').read_text().splitlines()]
controls={}
for row in base:
 if row['exercise'].startswith('traffic-priority-') and row['model'] in ('upper','lower'):
  controls.setdefault((row['exercise'],row['seed']),{})[row['model']]=row['urgent_deliveries']
correct={k:max(v,key=v.get) for k,v in controls.items()};assert len(correct)==32 and all(len(set(v.values()))==2 for v in controls.values())
sources=[('parent','city-strategy-skill-review-02','0'),('summary','city-strategy-skill-review-02','1'),('wide','city-strategy-wide-skill-review-03','0'),('mixed-midpoint','city-strategy-mixed-midpoint-skill-02','0'),('balanced-first','city-strategy-balanced-first-skill-01','0'),('balanced-fast-midpoint','city-strategy-balanced-fast-midpoint-skill-01','0'),('balanced-fast-final','city-strategy-balanced-fast-final-skill-01','0'),('extension-midpoint','city-strategy-extension-midpoint-skill-01','0'),('extension-final','city-strategy-extension-final-skill-01','0')]
result=[]
for name,path,index in sources:
 p=out/path/'games.jsonl'
 if not p.exists():continue
 rows=[json.loads(x) for x in p.read_text().splitlines()];cases=[]
 for row in rows:
  key=(row['exercise'],row['seed'])
  if row['model']!=index or key not in correct:continue
  probs=row['first_probabilities'];cases.append(dict(exercise=key[0],seed=key[1],urgent=correct[key],wait=probs['wait'],conditional_urgent_probability=probs[correct[key]]/(probs['upper']+probs['lower'])))
 assert len(cases)==32
 result.append(dict(model=name,mean_conditional_urgent_probability=float(np.mean([x['conditional_urgent_probability'] for x in cases])),cases=cases))
(rec/'priority-probabilities.json').write_text(json.dumps(dict(note='Frozen initial-state distributions on reused native validation cohort; control labels used for evaluation only, never training.',results=result),indent=2)+'\n')
print([(r['model'],r['mean_conditional_urgent_probability']) for r in result])
