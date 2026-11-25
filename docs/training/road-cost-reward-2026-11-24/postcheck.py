from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time,sys,json
from run_city_strategy_long import run_child
root=Path.cwd();r=root/'docs/training/road-cost-reward-2026-11-24';out=root/'output/training/road-cost-reward-fit-01';start=time.monotonic()
def run(name,args):
 wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
 run_child([sys.executable,'-c',wrapper,str(r/f'{name}.log'),sys.executable,'-u',*map(str,args)],cwd=root,timeout=1200)
run('watch-parent',[r/'watch.py','--arm','parent','--checkpoint',root/'output/training/city-whole-initial-01/start.zip'])
for arm in ['control','mild','strong']:
 while not (out/arm/'complete.json').exists():
  if time.monotonic()-start>2700:raise TimeoutError('Training completion not observed')
  if json.loads((out/'status.json').read_text()).get('status')=='error':raise RuntimeError('Training failed')
  time.sleep(5)
 run('watch-'+arm,[r/'watch.py','--arm',arm,'--checkpoint',out/arm/'final.zip'])
run('audit',[r/'audit.py'])
(r/'postcheck-complete.json').write_text('{"complete":true}\n')
