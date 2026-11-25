import json,numpy as np
from pathlib import Path
from city_curriculum import CityCurriculumEnv
from city_road_pilot import CityRoadEnv
D='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll'
a,b,c=CityRoadEnv(D),CityCurriculumEnv(D,city_horizon=600),CityCurriculumEnv(D,city_horizon=1200)
try:
 states=[e.reset(options=dict(exercise='city',scenario_seed=2004))[0] for e in [a,b,c]]
 for key in states[0]:
  np.testing.assert_array_equal(states[0][key],states[1][key]);np.testing.assert_array_equal(states[0][key],states[2][key])
 assert b.horizon==600 and c.horizon==1200
 for _ in range(30):
  a.step(0);b.step(0);c.step(0);assert a.raw==b.raw==c.raw
 Path('docs/training/city-strategy-launch-2026-11-24/horizon-check.json').write_text(json.dumps(dict(ordinary_initial_observation_exact=True,native_transitions_exact=30,short_horizon=b.horizon,long_horizon=c.horizon,observation_horizon=c.observation_horizon),indent=2)+'\n')
finally:
 for e in [a,b,c]:e.close()
