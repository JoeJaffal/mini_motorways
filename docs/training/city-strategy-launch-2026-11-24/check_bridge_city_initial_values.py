from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
torch.set_num_threads(1)
paths=['output/training/city-strategy-wide-initial-01/start.zip','output/training/city-strategy-bridge-reference-city-01/segment-001/final.zip'];models=[MaskablePPO.load(p,device='cpu') for p in paths]
e=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=1200,observation_horizon=600,allow_bridges=True);rows=[]
try:
 for seed,_ in json.loads(Path('output/training/city-strategy-bridge-longer-baseline-01/suite.json').read_text()):
  obs,_=e.reset(options=dict(scenario_seed=seed));vals=[]
  for m in models:
   t,_=m.policy.obs_to_tensor(obs)
   with torch.no_grad():vals.append(float(m.policy.predict_values(t).item()))
  rows.append(dict(seed=seed,values=vals))
finally:e.close()
p=Path('docs/training/city-strategy-launch-2026-11-24/bridge-city-initial-value-audit.json');assert not p.exists();p.write_text(json.dumps(dict(checkpoints=paths,rows=rows,means=np.mean([r['values'] for r in rows],axis=0).tolist(),limit='Initial states only; mean predictions versus cohort score are a calibration diagnostic, not a proof of causal training failure.'),indent=2)+'\n');print(p.read_text())
