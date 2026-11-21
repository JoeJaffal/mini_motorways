#!/bin/bash
# gp-8 A1 measurement (draft plan, pre-set): gp-7 final, cma-7 final and L on LA 8400-8499, stream (= f34) and keyed.
# Restartable via battery7 (completed chunks are skipped). <= 3 workers at nice 19 while StrokeQ holds the M4.
set -u
G8=/Users/mounir/Desktop/mini_motorways/mm-gp8
cd $G8
export PATH=~/.dotnet:$PATH DOTNET_ROOT=~/.dotnet PYTHONHASHSEED=0 EVOLVED_RULES_HOST_DLL=$G8/simulation/Headless/bin/Release/net8.0/TrafficHost.dll
PY=/Users/mounir/Desktop/mini_motorways/mini_motorways/.venv/bin/python
W=${W:-3}
CH=$G8/evolved_rules/final/gp7/challengers
for mode in keyed stream; do
  for p in "gp7:$CH/gp7_final.txt" "cma7:$CH/cma7_final.txt" "L:$G8/evolved_rules/seeds/gp7/cma1_3tree.txt"; do
    n=${p%%:*}; f=${p#*:}
    nice -n 19 $PY $G8/evolved_rules/ops/battery7.py --policy "tree:$f" --seeds 8400-8499 --chunk 100 --workers $W \
      --main $G8 --prefix "a1-$mode-$n" --randomness $mode || exit 1
  done
done
touch $G8/output/evolved_rules/ops/measure_keyed.done
