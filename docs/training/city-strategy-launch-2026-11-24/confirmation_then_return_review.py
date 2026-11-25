from pathlib import Path
import subprocess,os,sys
root=Path.cwd()
env=dict(os.environ,OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",PYTHONPATH=str(root/"training"))
with (root/"output/training/city-strategy-extension-confirmation-03.log").open("x") as f:subprocess.run(['/home/mohammadjaffal/mini_motorways/.venv/bin/python', '-u', 'training/evaluate_city_service.py', '--dll', 'output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll', '--checkpoints', 'output/training/city-five-stage-cold-initial-01/candidate.zip', 'output/training/city-strategy-balanced-extension-01/segment-001/midpoint.zip', '--output', 'output/training/city-strategy-extension-confirmation-03', '--games', '64', '--seed', '950243', '--workers', '8'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run([sys.executable,"-u","docs/training/city-strategy-launch-2026-11-24/review_return_advantage.py"],cwd=root,env=env,check=True)
