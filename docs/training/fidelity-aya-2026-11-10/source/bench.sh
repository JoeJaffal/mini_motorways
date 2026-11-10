#!/bin/sh
# usage: tmp/bench.sh <tag>   (run from mm-fidelity root) - builds harness from current sim source and benchmarks v21 replay
TAG=$1; cd "/c/Projects/490 - Project/mm-fidelity"
(cd tmp/harness && dotnet build -c Release -nologo -v q 2>&1 | grep -E " error |rror\(s\)" | head -3)
rm -rf tmp/hbin-$TAG && cp -r tmp/harness/bin/Release/net8.0 tmp/hbin-$TAG
R=docs/training/simulator-repairs-2026-11-08/replay-candidate-v21.json
(cat tmp/runs/bench-phases.txt; echo "FIT $(cat tmp/runs/fitted-phases.txt)") | xargs -P 15 -L 1 sh -c 'if [ "$0" = FIT ]; then echo "FIT :: $(tmp/hbin-'$TAG'/Harness.exe '$R' - $1 $2 $3 $4 $5 | head -1)"; else echo "$0 $1 $2 $3 $4 :: $(tmp/hbin-'$TAG'/Harness.exe '$R' - $0 $1 $2 $3 $4 | head -1)"; fi' > tmp/runs/bench-$TAG.txt
py -3 - "$TAG" <<'PY'
import sys,re,statistics as st
tag=sys.argv[1];L=open(f'tmp/runs/bench-{tag}.txt').read().splitlines()
rows=[(l.startswith('FIT'),float(re.search(r't=([\d.]+)',l).group(1)),int(re.search(r'score=(\d+)',l).group(1)),'failed=True' in l) for l in L if 'score=' in l]
s=[r[2] for r in rows if not r[0]];t=[r[1] for r in rows if not r[0]];f=[r for r in rows if r[0]]
print(f"[{tag}] 16 phases: score mean {st.mean(s):.1f} median {st.median(s)} min {min(s)} max {max(s)} | end mean {st.mean(t):.0f} min {min(t):.0f} max {max(t):.0f} | survived {sum(not r[3] for r in rows if not r[0])}/16")
if f: print(f"[{tag}] fitted phases: score {f[0][2]} end {f[0][1]:.0f} failed {f[0][3]}   (real: 835 @ ~1314.6)")
PY
