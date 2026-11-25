"""Recover missing replay-template packaging, preserving the failed review."""
import datetime,json,os,shutil,subprocess,sys
from pathlib import Path
from prepare_city_policy import sha256
from train_city_wait_decision import publish_json
root=Path.cwd();out=root/'output/training/route-outcome-01';archive=root/'docs/training/route-outcome-run-2026-11-25'
state=json.loads((out/'status.json').read_text());assert state['status']=='failed'
(archive/'initial-review-failure-status.json').open('x').write(json.dumps(state,indent=2)+'\n')
shutil.copy2(out/'practice-final.log',archive/'initial-practice-review-failure.log')
shutil.copytree(out/'evaluation/practice-final',archive/'failed-practice-review')
source=out/'runtime/training';template=root/'training/stage1_replay.html'
assert not (source/'stage1_replay.html').exists()
shutil.copy2(template,source/'stage1_replay.html');shutil.copy2(template,archive/'runtime-source/stage1_replay.html')
state.update(status='running',phase='recovery',recovery_pid=os.getpid(),recovery_reason='Missing HTML replay template in frozen packaging. Training and final checkpoint intact; failed partial evaluation preserved. Re-evaluate same frozen development suite in a new directory, then finish city review/native export.')
env=dict(os.environ,PYTHONPATH=str(source))
def publish():
 publish_json(out/'status.json',state);publish_json(archive/'status.json',state)
def run(label,args):
 state['phase']=label;publish()
 command=[sys.executable,'-u',*map(str,args)]
 (archive/(label+'-command.json')).open('x').write(json.dumps(command,indent=2)+'\n')
 print('START',label,flush=True)
 with (out/(label+'.log')).open('x') as log:subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('COMPLETE',label,flush=True)
try:
 publish()
 dll=out/'runtime/host/TrafficHost.dll';final=out/'training/final.zip'
 run('practice-recovery',[source/'audit_mini_behavior.py','--dll',dll,'--output',out/'evaluation/practice-final-recovered','--workers',2,'--checkpoints',final,'--labels','candidate','--small-city-horizon',300])
 shutil.copytree(out/'evaluation/practice-final-recovered',archive/'evaluation/practice-final')
 run('city-final',[source/'evaluate_overnight_city.py','--dll',dll,'--output',out/'evaluation/city-final','--workers',2,'--checkpoint',final])
 shutil.copytree(out/'evaluation/city-final',archive/'evaluation/city-final')
 run('native-export',[source/'prepare_city_route_outcome.py','--parent',final,'--native-template',root/'output/training/mini-fixed-route-01/training/final.zip','--dll',dll,'--output',out/'native-export','--archive',archive/'native-export','--direction','native'])
 assert sha256(Path(state['parent']))==state['parent_sha256'] and sha256(dll)==state['host_sha256']
 state.update(status='complete',phase='complete',finished=datetime.datetime.now().astimezone().isoformat());publish()
 print('RECOVERY COMPLETE. No training was rerun.',flush=True)
except BaseException as error:
 state.update(status='failed',recovery_error=repr(error));publish();raise
