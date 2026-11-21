#!/bin/bash
# gp-8 stream E step 2 (descriptive): gp-7 final, L and hand on 100 seeds per city, f35 stream (= f34).
# Beijing 8000-8099, Tokyo 8100-8199, Dar es Salaam 8200-8299. London excluded (smoke failure).
# Restartable via battery7. <= 3 workers at nice 19 while StrokeQ holds the M4.
set -u
G8=/Users/mounir/Desktop/mini_motorways/mm-gp8
cd $G8
export PATH=~/.dotnet:$PATH DOTNET_ROOT=~/.dotnet PYTHONHASHSEED=0 EVOLVED_RULES_HOST_DLL=$G8/simulation/Headless/bin/Release/net8.0/TrafficHost.dll
PY=/Users/mounir/Desktop/mini_motorways/mini_motorways/.venv/bin/python
W=${W:-3}
CH=$G8/evolved_rules/final/gp7/challengers
for cs in Beijing:8000-8099 Tokyo:8100-8199 DarEsSalaam:8200-8299; do
  c=${cs%%:*}; s=${cs#*:}
  for p in "gp7:tree:$CH/gp7_final.txt" "L:tree:$G8/evolved_rules/seeds/gp7/cma1_3tree.txt" "hand:hand"; do
    n=${p%%:*}; f=${p#*:}
    nice -n 19 $PY $G8/evolved_rules/ops/battery7.py --policy "$f" --seeds $s --chunk 100 --workers $W \
      --main $G8 --prefix "e2-$c-$n" --city $c --randomness stream || exit 1
  done
done
touch $G8/output/evolved_rules/ops/cities_check.done
