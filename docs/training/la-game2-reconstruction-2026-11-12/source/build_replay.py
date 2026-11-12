import json
MAN=json.load(open('manual.json'))
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
def game(v):
    for end,c in W:
        if v<=end+2:return round(max(0.05,v+c),2)
COLOR={'yellow':0,'magenta':1,'charcoal':2,'blue':3,'green':4}  # plan order: charcoal plays the cyan role, blue the navy role
ev=[]
# lots: (origin, size, colour, layout, spawn video, kind)
LOTS=[((12,15),'yellow',3,0.5,'shop'),((16,17),'magenta',2,68,'shop'),((15,12),'yellow',3,294,'shop'),((11,12),'blue',3,304,'shop'),
      ((27,15),'charcoal',3,334,'shop'),((27,18),'magenta',3,391,'shop'),((28,9),'charcoal',0,492,'shared'),((10,9),'magenta',3,537,'shop'),((38,15),'green',1,807,'shop')]
lid={}
# late plan items (game s): yellow chunk days 7-9, navy slot 0 of days 8-22, cyan slot 0 of days 16-36
LATE={(15,12):160.0,(11,12):230.0,(28,9):407.0}
for (x,y),c,lay,v,kind in LOTS:
    i=f'{kind}:{c}:{x},{y}';lid[(x,y)]=i
    e=dict(at=game(v),videoTime=v,kind=kind,id=i,x=x,y=y,color=COLOR[c],layout=lay)
    if (x,y) in LATE:e['scheduledAt']=LATE[(x,y)]
    ev.append(e)
# round conversions (approximate, mid of the 30 s window where the shape changes)
for (x,y),v in [((12,15),671),((27,18),671),((28,9),840),((11,12),929),((15,12),1055)]:
    ev.append(dict(at=game(v),videoTime=v,kind='circle',target=lid[(x,y)]))
# houses and driveways
hs=json.load(open('houses_dom.json'));hraw={(h['x'],h['y']):h for h in json.load(open('houses_raw.json'))}
for h in hs:
    if (h['x'],h['y']) not in hraw:continue
    import collections
    cs=[d for t,d in h['conn'] if d is not None]
    init=collections.Counter(cs).most_common(1)[0][0] if cs else h['dominant'][0][1];dom=[]
    init=MAN['driveway'].get(f"{h['x']},{h['y']}",init)
    i=f"house:{h['name']}:{h['x']},{h['y']}"
    ev.append(dict(at=game(h['video']),videoTime=h['video'],kind='house',id=i,x=h['x'],y=h['y'],color=COLOR[h['name']],direction=init))
    cur=init
    for k in range(1,len(dom)-2):
        d=dom[k][1]
        if d!=cur and all(dom[j][1]==d for j in range(k,min(len(dom),k+3))) and dom[k][2]>0.5:
            ev.append(dict(at=game(dom[k][0]+0.5),videoTime=dom[k][0]+0.5,kind='driveway',target=i,direction=d));cur=d
for hx,hy,hd,hv in MAN.get('drivewayEvents',[]):
    hid=next(e['id'] for e in ev if e['kind']=='house' and e['x']==hx and e['y']==hy)
    ev.append(dict(at=game(hv),videoTime=hv,kind='driveway',target=hid,direction=hd))
# missing houses detected only by the looser rule (no dominant series)
for (x,y),h in hraw.items():
    if not any(e.get('id')==f"house:{h['name']}:{x},{y}" for e in ev):
        ev.append(dict(at=game(h['video']),videoTime=h['video'],kind='house',id=f"house:{h['name']}:{x},{y}",x=x,y=y,color=COLOR[h['name']],direction=2))
# roads (automatic, minus manual removals) and manual additions [x,y,toX,toY,fromVideo(,toVideo)]
rem={tuple(r[:4]) for r in MAN['remove']}
for a in MAN['add']:
    ev.append(dict(at=game(a[4]),videoTime=a[4],kind='draw',x=a[0],y=a[1],toX=a[2],toY=a[3],manual=True))
    if len(a)>5:ev.append(dict(at=game(a[5]),videoTime=a[5],kind='erase',x=a[0],y=a[1],toX=a[2],toY=a[3],manual=True))
for r in json.load(open('roads_fixed.json')):
    if (r['x'],r['y'],r['toX'],r['toY']) in rem or (r['toX'],r['toY'],r['x'],r['y']) in rem:continue
    ev.append(dict(at=game(r['video']),videoTime=r['video'],kind=r['kind'],x=r['x'],y=r['y'],toX=r['toX'],toY=r['toY']))
# weekly offers (type 0 roads, 1 bridge, 2 motorway, 3 lights, 4 roundabout) and choices
OFF=[([(3,2,20),(4,1,20)],1),([(0,30,0),(3,2,20)],0),([(2,1,10),(1,1,20)],1),([(1,1,20),(0,30,0)],0),
     ([(2,1,10),(1,1,20)],1),([(2,1,10),(0,30,0)],1),([(2,1,10),(1,1,20)],1),([(1,1,20),(2,1,10)],1)]
for k,(offers,ch) in enumerate(OFF):
    t=140*(k+1)
    ev.append(dict(at=t,kind='offer',offers=[dict(type=a,amount=b,roads=c) for a,b,c in offers]))
    ev.append(dict(at=t+0.01,kind='choose',choice=ch))
ev=[e for e in ev if 0<e['at']<1162.0]
order={'offer':0,'choose':1,'shop':2,'shared':2,'join':2,'house':3,'circle':4,'erase':5,'driveway':6,'draw':7}
ev.sort(key=lambda e:(e['at'],order[e['kind']]))
base=json.load(open('../../replay-v21d-final.json'))
rep=dict(schemaVersion=1,id='video-la-game2-draft1',city='LosAngeles',seed=-915001679,referenceScore=601,duration=1162.0,
 source='la-game2-score-601.mp4, automatic reconstruction draft 1',sourceSha256='',startingInventory=[25,1,0,0,0,0],
 paletteRgb=base['paletteRgb'],bounds=[0,0,50,30],uncertainties='draft',events=ev,notes=[])
json.dump(rep,open('replay-g2-draft1.json','w'),indent=1)
import collections;print(len(ev),collections.Counter(e['kind'] for e in ev))
