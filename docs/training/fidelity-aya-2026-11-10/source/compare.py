import csv,sys,bisect
real=[(float(r['game_s']),int(r['score'])) for r in csv.DictReader(open('tmp/video/score_timeline.csv'))]
sim=[r for r in csv.DictReader(l for l in open(sys.argv[1]) if not l.startswith('#'))]
st=[float(r['t']) for r in sim]
print(f"{'game_s':>7} {'real':>5} {'sim':>5} {'diff':>5}  demand reserved cars moving wait5 houses dests maxOver")
for g,s in real[::3]:
    i=min(bisect.bisect_left(st,g),len(sim)-1);r=sim[i]
    if abs(st[i]-g)>15: print(f"{g:7.0f} {s:5d}   (sim ended)");continue
    print(f"{g:7.0f} {s:5d} {r['score']:>5} {int(r['score'])-s:5d}  {r['demand']:>6} {r['reserved']:>8} {r['cars']:>4} {r['moving']:>6} {r['waiting5']:>5} {r['houses']:>6} {r['dests']:>5} {r['maxOver']:>7}")
