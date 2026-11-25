from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys,json
from run_city_strategy_long import run_child
root=Path.cwd();r=root/'docs/training/small-city-service-2026-11-24'
models={'parent':root/'output/training/city-whole-initial-01/start.zip','final':root/'output/training/small-city-offset-fit-01/ppo/final.zip'}
def run(label):
 args=[sys.executable,'-u',str(r/'evaluate_confirm.py'),'--checkpoint',str(models[label]),'--output',str(root/f'output/training/small-city-confirm-{label}-01')]
 (r/f'confirm-{label}-command.json').write_text(json.dumps(args,indent=2)+'\n')
 wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
 run_child([sys.executable,'-c',wrapper,str(r/f'confirm-{label}.log'),*args],cwd=root,timeout=1800)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,models))
(r/'confirm-complete.json').write_text('{"complete":true}\n')
