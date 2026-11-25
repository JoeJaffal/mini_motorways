from pathlib import Path
import json,os,subprocess,time
root=Path.cwd();record=root/'docs/training/city-strategy-launch-2026-11-24/wide-queue.json'
record.write_text(json.dumps(dict(status='waiting',parent_pid=150630))+'\n')
complete=root/'output/training/city-strategy-longer-pilot-02/complete.json'
try:
 for _ in range(360):
  if complete.exists():break
  os.kill(150630,0);time.sleep(10)
 else:raise TimeoutError('Longer pilot did not complete within queue budget')
 name='city-strategy-wide-pilot-03';output=root/'output/training'/name
 assert not output.exists()
 command=[str(root/'.venv/bin/python'),'-u','training/train_city_curriculum.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--parent','output/training/city-strategy-wide-initial-01/start.zip','--output',str(output),'--stage','city','--rollouts','8','--rollout-steps','512','--batch-size','128','--gae-lambda','1','--seed-start','142000000','--learning-rate','.003','--collapse-forced-wait','--save-every-rollouts','1']
 env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 with (root/'output/training'/(name+'.log')).open('x') as stream:
  proc=subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 record.write_text(json.dumps(dict(status='launched',pid=proc.pid,command=command),indent=2)+'\n')
except BaseException as error:
 record.write_text(json.dumps(dict(status='error',error=repr(error)))+'\n');raise
