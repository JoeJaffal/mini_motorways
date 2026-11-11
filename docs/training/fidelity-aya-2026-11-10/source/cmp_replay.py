import csv,json,bisect,statistics as st,collections,sys
rows=list(csv.DictReader(open(sys.argv[2] if len(sys.argv)>2 else 'week_time.csv')))
V=[float(r['video']) for r in rows];G=[float(r['game']) for r in rows]
def g_at(v):
    i=bisect.bisect_left(V,v)
    if 0<i<len(V) and V[i]-V[i-1]<=1.5:  # interpolate inside readable runs and short gaps
        f=(v-V[i-1])/(V[i]-V[i-1]);return G[i-1]+f*(G[i]-G[i-1]),0
    j=min([k for k in (i-1,i) if 0<=k<len(V)],key=lambda k:abs(V[k]-v));return G[j],abs(V[j]-v)
d=json.load(open(sys.argv[1] if len(sys.argv)>1 else '../../docs/training/fidelity-aya-2026-11-10/replay-candidate-v21c.json'))
res=[(e['videoTime'],e['at'],e['at']-g_at(e['videoTime'])[0]) for e in d['events'] if g_at(e['videoTime'])[1]<=0.5]
off=0;print('n',len(res),'median diff',round(st.median(r[2] for r in res),2))
seg=collections.OrderedDict()
for v,at,o in res:seg.setdefault(int(v//50)*50,[]).append(o-off)
for b,l in seg.items():print(f"video {b:4d}-{b+50:4d}: n={len(l):3d} mean {st.mean(l):+6.2f} min {min(l):+6.2f} max {max(l):+6.2f}")
