"""Graceful external guard for an already-running experiment with --stop-file."""
import argparse
import csv
from pathlib import Path
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--run',type=Path,required=True);p.add_argument('--stop-file',type=Path,required=True)
p.add_argument('--steps',type=int,required=True);p.add_argument('--max-minutes',type=float,required=True)
a=p.parse_args();started=time.monotonic()
while not (a.run/'summary.json').exists():
    steps=0
    try:
        with (a.run/'progress.csv').open() as f:
            for row in csv.DictReader(f):
                value=row.get('time/total_timesteps')
                if value:steps=max(steps,int(float(value)))
    except (FileNotFoundError,ValueError):pass
    if steps>=a.steps or time.monotonic()-started>=a.max_minutes*60:
        a.stop_file.parent.mkdir(parents=True,exist_ok=True)
        a.stop_file.write_text(f'Graceful experiment guard: observed {steps} selections; target {a.steps}\n')
        print(f'Stop requested at observed {steps} selections',flush=True);break
    time.sleep(2)
