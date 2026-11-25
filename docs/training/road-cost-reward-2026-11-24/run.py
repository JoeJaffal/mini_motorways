from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys,json,os,shutil,datetime
from run_city_strategy_long import run_child
root=Path.cwd();r=root/'docs/training/road-cost-reward-2026-11-24';out=root/'output/training/road-cost-reward-fit-01';out.mkdir(exist_ok=False)
source=out/'runtime/training';source.mkdir(parents=True)
for p in (root/'training').glob('*.py'):shutil.copy2(p,source/p.name)
shutil.copytree(source,r/'runtime-source');host=out/'runtime/host';shutil.copytree(root/'output/road-cost-reward-build-02/bin/TrafficHost/release',host)
parent=root/'output/training/city-whole-initial-01/start.zip'
state=dict(status='running',pid=os.getpid(),phase='preparing',started=datetime.datetime.now().astimezone().isoformat())
def publish():
 for p in [out/'status.json',r/'status.json']:p.write_text(json.dumps(state,indent=2)+'\n')
def run(name,args):
 (r/f'{name}-command.json').write_text(json.dumps(list(map(str,args)),indent=2)+'\n')
 wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
 run_child([sys.executable,'-c',wrapper,str(out/f'{name}.log'),sys.executable,'-u',*map(str,args)],cwd=root,timeout=3600)
def evaluate(name,checkpoint):run('eval-'+name,[r/'evaluate.py','--checkpoint',checkpoint,'--output',root/f'output/training/road-cost-reward-eval-{name}-01'])
try:
 with ThreadPoolExecutor(max_workers=1) as pool:
  baseline=pool.submit(evaluate,'parent',parent)
  for arm,cost in [('control',0),('mild',.01),('strong',.04)]:
   state.update(phase='training',arm=arm,cost=cost);publish()
   run(arm,[source/'train_road_cost_trial.py','--dll',host/'TrafficHost.dll','--parent',parent,'--output',out/arm,'--road-cost',cost])
  baseline.result()
 state.update(phase='evaluation',arm='all');publish()
 with ThreadPoolExecutor(max_workers=2) as pool:
  jobs=[pool.submit(evaluate,arm,out/arm/'final.zip') for arm in ['control','mild','strong']]
  for f in jobs:f.result()
 state.update(status='complete',phase='finished');publish()
except BaseException as ex:state.update(status='error',error=repr(ex));publish();raise
