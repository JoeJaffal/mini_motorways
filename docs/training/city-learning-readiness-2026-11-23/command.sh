#!/usr/bin/env bash
set -euo pipefail
cd /home/mohammadjaffal/mini_motorways
exec env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1   .venv/bin/python -u training/run_city_learning_guarded.py   --start output/training/city-learning-pilot-03/checkpoints/city-000133120-20d5460d.zip   --dll output/city-network-service-build.NdaqGi/bin/TrafficHost/release/TrafficHost.dll   --output output/training/city-learning-long-01 "$@"
