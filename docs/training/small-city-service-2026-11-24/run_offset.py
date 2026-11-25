from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys,json,os,shutil,datetime
from run_city_strategy_long import run_child
root=Path.cwd();r=root/'docs/training/small-city-service-2026-11-24';out=root/'output/training/small-city-offset-fit-01';out.mkdir(exist_ok=False)
source=out/'runtime/training';source.mkdir(parents=True)
for p in (root/'training').glob('*.py'):shutil.copy2(p,source/p.name)
shutil.copytree(source,r/'offset-runtime-source')
host=out/'runtime/host';shutil.copytree(root/'output/small-city-offset-build-01/bin/TrafficHost/release',host)
status=dict(status='running',pid=os.getpid(),phase='offset training',started=datetime.datetime.now().astimezone().isoformat())
def publish():
 for p in [out/'status.json',r/'offset-status.json']:p.write_text(json.dumps(status,indent=2)+'\n')
def run(name,args):
 (r/f'{name}-command.json').write_text(json.dumps(list(map(str,args)),indent=2)+'\n')
 wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
 run_child([sys.executable,'-c',wrapper,str(out/f'{name}.log'),sys.executable,'-u',*map(str,args)],cwd=root,timeout=3600)
parent=root/'output/training/city-whole-initial-01/start.zip'
try:
 publish()
 train=[source/'train_city_curriculum.py','--dll',host/'TrafficHost.dll','--parent',parent,'--output',out/'ppo','--record-dir',r/'offset-run','--stage','small-city-offset','--workers','16','--seed-start','190000000','--rollouts','4','--rollout-steps','512','--batch-size','128','--gae-lambda','1','--learning-rate','.0003','--value-coefficient','.00001','--gradient-audit-steps','64','--collapse-forced-wait','--save-every-rollouts','1']
 run('train',train)
 status.update(phase='final evaluation');publish()
 checkpoint=out/'ppo/final.zip'
 with ThreadPoolExecutor(max_workers=2) as pool:
  jobs=[pool.submit(run,'final',[r/'evaluate_offset.py','--checkpoint',checkpoint,'--output',root/'output/training/small-city-offset-final-01']),pool.submit(run,'city-retention',[r/'evaluate_city.py','--checkpoint',checkpoint,'--output',root/'output/training/small-city-offset-city-01','--baseline',root/'output/training/city-whole-baseline-01'])]
  for f in jobs:f.result()
 status.update(status='complete',phase='finished');publish()
except BaseException as ex:
 status.update(status='error',error=repr(ex));publish();raise
