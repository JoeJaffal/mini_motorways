from pathlib import Path
import json,numpy as np
root=Path.cwd();cohorts={}
for p in (root/'output').rglob('suite.json'):
 try:rows=json.loads(p.read_text())
 except (ValueError,OSError):continue
 if not isinstance(rows,list):continue
 seeds={row[0] for row in rows if isinstance(row,list) and len(row)==2 and isinstance(row[0],int) and 99000000<=row[0]<99500000}
 if seeds:cohorts[str(p.relative_to(root))]=seeds
seen=set().union(*cohorts.values()) if cohorts else set()
reserved={}
for rng_seed,count in [(950245,32),(950246,64)]:
 rng=np.random.default_rng(rng_seed);seeds=set((99000000+rng.choice(500000,count,replace=False)).tolist());reserved[str(rng_seed)]=dict(count=count,overlap_with_available_suites=sorted(seeds&seen))
result=dict(note='Read-only checks of every available output/**/suite.json containing ordinary99M city seeds, including archived copies of the same suite. Absence of overlap does not prove absent records never used a seed.',available_suites=len(cohorts),unique_city_seeds=len(seen),reserved=reserved)
(root/'docs/training/city-strategy-launch-2026-11-24/city-cohort-overlap-all-records.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
