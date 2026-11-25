from pathlib import Path
import subprocess,sys,time,json,os
root=Path.cwd();rec=root/'docs/training/city-strategy-launch-2026-11-24';done=root/'output/training/city-strategy-balanced-fast-01/complete.json'
for _ in range(360):
 if done.exists():break
 time.sleep(5)
else:raise TimeoutError('Awaited bounded training did not complete')
cmd=[sys.executable,'-u','training/run_city_strategy_long.py','--start','output/training/city-strategy-balanced-fast-01/final.zip','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--output','output/training/city-strategy-runner-smoke-01','--record-dir',str(rec/'runner-smoke-01'),'--hours','.0001','--workers','1','--segment-rollouts','1','--review-every','1','--review-games','2','--horizon','600','--learning-rate','.001']
with (root/'output/training/city-strategy-runner-smoke-01.log').open('x') as f:
 result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
status=json.loads((root/'output/training/city-strategy-runner-smoke-01/status.json').read_text());assert result.returncode==0 and status['status'] in ('complete','regression_stop')
assert status['segments']==1 and status['last_review']
(rec/'runner-smoke-result.json').write_text(json.dumps(dict(status=status,command=cmd,note='Workflow smoke only:512 training decisions and two paired review cities; not score-selection or readiness evidence.'),indent=2)+'\n')
