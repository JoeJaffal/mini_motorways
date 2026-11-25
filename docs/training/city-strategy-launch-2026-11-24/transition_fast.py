from pathlib import Path
import json,os,signal,subprocess,time,hashlib
root=Path.cwd();rec=root/'docs/training/city-strategy-launch-2026-11-24';parent=root/'output/training/city-strategy-balanced-pilot-01/checkpoint-000008192.zip';records=parent.parent/'checkpoints.json'
assert json.loads((rec/'priority-tail-check.json').read_text())['exact_native_final_reward_flags_info_and_next_reset']
assert (root/'output/training/city-strategy-mixed-midpoint-skill-02/summary.json').exists()
os.killpg(173965,signal.SIGTERM) # Its completed mixed review is preserved; now waiting for the old midpoint.
for _ in range(360):
 if parent.exists() and records.exists():
  saves=json.loads(records.read_text());match=[r for r in saves if Path(r['path']).name==parent.name]
  if match:
   assert hashlib.sha256(parent.read_bytes()).hexdigest()==match[0]['sha256'];break
 time.sleep(5)
else:raise TimeoutError('Verified rollout checkpoint unavailable')
os.kill(173520,signal.SIGINT)
for _ in range(60):
 stat=Path('/proc/173520/stat')
 if not stat.exists() or stat.read_text().split()[2]=='Z':break
 time.sleep(1)
else:raise RuntimeError('Old trainer has not stopped')
name='city-strategy-balanced-fast-01';cmd=[str(root/'.venv/bin/python'),'-u','training/train_city_curriculum.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--parent',str(parent),'--output',str(root/'output/training'/name),'--stage','strategy-balanced','--rollouts','3','--rollout-steps','512','--batch-size','128','--gae-lambda','1','--seed-start','146000000','--learning-rate','.001','--collapse-forced-wait','--fast-priority-tail','--save-every-rollouts','1']
with (root/'output/training'/(name+'.log')).open('x') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
(rec/'balanced-fast-launch.json').write_text(json.dumps(dict(pid=p.pid,command=cmd,parent_sha256=match[0]['sha256'],reason='Use parity-checked native terminal-tail acceleration; retain completed rollout and optimizer.'),indent=2)+'\n');print(p.pid,flush=True)
