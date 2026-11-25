from pathlib import Path
import subprocess,os,json
root=Path.cwd();python=str(root/'.venv/bin/python');dll='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll'
common=['--dll',dll,'--stage','city','--rollout-steps','512','--batch-size','128','--gae-lambda','1','--learning-rate','.003','--collapse-forced-wait','--save-every-rollouts','1']
jobs=[('city-strategy-wide-pilot-02',[python,'-u','training/train_city_curriculum.py',*common,'--parent','output/training/city-strategy-wide-initial-01/start.zip','--output','output/training/city-strategy-wide-pilot-02','--rollouts','8','--seed-start','142000000']),
('city-strategy-longer-pilot-02',[python,'-u','training/train_city_curriculum.py',*common,'--parent','output/training/city-strategy-pilot-01/final.zip','--output','output/training/city-strategy-longer-pilot-02','--rollouts','4','--horizon','1200','--seed-start','143000000']),
('city-strategy-confirmation-02',[python,'-u','training/evaluate_city_service.py','--dll',dll,'--checkpoints','output/training/city-five-stage-cold-initial-01/candidate.zip','output/training/city-strategy-pilot-01/final.zip','--output','output/training/city-strategy-confirmation-02','--games','64','--seed','950242','--workers','8'])]
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');records=[]
for name,command in jobs:
 assert not (root/'output/training'/name).exists()
 log=root/'output/training'/(name+'.log')
 with log.open('x') as stream:p=subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 records.append(dict(name=name,pid=p.pid,command=command,log=str(log)))
Path('docs/training/city-strategy-launch-2026-11-24/restart-launches.json').write_text(json.dumps(records,indent=2)+'\n')
print(records)
