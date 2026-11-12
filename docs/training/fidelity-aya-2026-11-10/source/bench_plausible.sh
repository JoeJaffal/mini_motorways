#!/bin/sh
# usage: REPLAY=<file> PHASES=<file> tmp/bench3.sh <tag> [hbin-dir]   - benchmark a replay on a list of phase sets (no rebuild if hbin given)
TAG=$1; cd "/c/Projects/490 - Project/mm-fidelity"
R=${REPLAY:-docs/training/fidelity-aya-2026-11-10/replay-candidate-v21d.json}; P=${PHASES:-docs/training/fidelity-aya-2026-11-10/measurements/plausible-phases-v21e-60.txt}
if [ -n "$2" ]; then H=$2; else (cd tmp/harness && dotnet build -c Release -nologo -v q 2>&1 | grep -E " error |rror\(s\)" | head -3); rm -rf tmp/hbin-$TAG && cp -r tmp/harness/bin/Release/net8.0 tmp/hbin-$TAG; H=tmp/hbin-$TAG; fi
cat $P | xargs -P 15 -L 1 sh -c 'echo "$0 $1 $2 $3 $4 :: $('$H'/Harness.exe '$R' - $0 $1 $2 $3 $4 | head -1)"' > tmp/runs/bench3-$TAG.txt
py -3 - "$TAG" <<'PY'
import sys,re,statistics as st
tag=sys.argv[1];L=open(f'tmp/runs/bench3-{tag}.txt').read().splitlines()
rows=[(float(re.search(r't=([\d.]+)',l).group(1)),int(re.search(r'score=(\d+)',l).group(1)),'failed=True' in l) for l in L if 'score=' in l]
s=[r[1] for r in rows];t=[r[0] for r in rows]
print(f"[{tag}] {len(s)} plausible phases: score mean {st.mean(s):.1f} median {st.median(s)} min {min(s)} max {max(s)} | end mean {st.mean(t):.0f} min {min(t):.0f} | reach end {sum(not r[2] for r in rows)}/{len(s)}   (real 835 @ 1314.6)")
PY
