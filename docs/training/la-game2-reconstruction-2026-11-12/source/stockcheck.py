import json, csv, sys
rep=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'replay-g2-draft1.json'))
real={int(r['video_s']):int(r['roads']) for r in csv.DictReader(open('stock_g2.csv'))}
houses=set();lots=set()
links=set();stock=25;rows=[]
def cells():
    c=set()
    for a,b in links:c.add(a);c.add(b)
    return c-houses-lots
REW={0:0}
ev=sorted(rep['events'],key=lambda e:e.get('videoTime',e['at']))
OFFROADS=[20,30,20,20,20,30,20,10]
evi=0;rewards=0
for v in range(0,1190,5):
    while evi<len(ev) and ev[evi].get('videoTime',ev[evi]['at'])<=v:
        e=ev[evi];evi+=1
        if e['kind']=='house':houses.add((e['x'],e['y']))
        if e['kind'] in('shop','shared'):
            w,h=(4,3) if e['kind']=='shared' else ((2,3) if e['layout']<2 else (3,2))
            for dx in range(w):
                for dy in range(h):lots.add((e['x']+dx,e['y']+dy))
        if e['kind']=='draw':links.add(((e['x'],e['y']),(e['toX'],e['toY'])))
        if e['kind']=='erase':links.discard(((e['x'],e['y']),(e['toX'],e['toY'])))
    weeks=sum(1 for s in [139.25,285.5,425.75,570,713,863.25,1003.25,1145.5] if s<v)
    acq=25+sum(OFFROADS[:weeks]);used=len(cells())
    rows.append((v,acq-used,real.get(v)))
for v,s,r in rows:
    if r is not None and abs(s-r)>=3:print(v,'model',s,'real',r)
