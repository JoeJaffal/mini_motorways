from pathlib import Path
import json,numpy as np
from city_repeated_seeds import CityRepeatedSeedsEnv
from city_road_pilot import CityRoadEnv
root=Path.cwd();rec=root/'docs/training/city-whole-policy-2026-11-24';source=json.loads((rec/'watched-reference-success/trace.json').read_text());dll='output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll'
a=CityRoadEnv(dll,horizon=600,allow_bridges=True);b=CityRepeatedSeedsEnv(dll,stage='city',city_horizon=600,allow_bridges=True,seed_start=184000003,repeat_city_count=8,finite_city_horizon=True)
try:
 x,_=a.reset(options=dict(scenario_seed=184000003));y,_=b.reset();score=0
 for action in source['actions']:
  np.testing.assert_array_equal(a.action_masks(),b.action_masks())
  ra=a.step(action['action']);rb=b.step(action['action']);score+=ra[1]
  assert ra[1]==rb[1]
  for k in ra[0]:np.testing.assert_array_equal(ra[0][k],rb[0][k])
  if not a.done:assert ra[2:4]==rb[2:4]
 assert a.raw==b.raw and score==158 and ra[2:4]==(False,True) and rb[2:4]==(True,False)
 assert rb[4]['finite_horizon_end'] and not rb[4]['native_game_over']
 report=dict(decisions=len(source['actions']),native_score=score,all_observations_masks_rewards_exact=True,only_final_termination_flags_changed=True,native_world_exact=True)
finally:a.close();b.close()
(rec/'finite-horizon-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
