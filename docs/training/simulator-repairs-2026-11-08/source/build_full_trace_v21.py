# v21: Mohammad's v20 builder (docs/training/full-replay-review-2026-11-08/source/build_full_trace.py, regenerated
# output identical to replay-candidate-v20.json) plus ONLY the seven corrections listed in EMERGENCY_HANDOFF.md
# "Exact next input corrections", each marked "handoff correction N". Inputs stay in Mohammad's local folder;
# outputs go to tmp/simulator-repairs-2026-11-08 so v20 working files are never overwritten. Run from the repo root
# with numpy available and OpenCV in tmp/video-analysis-deps.
import json,pathlib,sys,numpy as np
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
base=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');root=pathlib.Path('tmp/full-replay-review-2026-11-08');out=pathlib.Path('tmp/simulator-repairs-2026-11-08');out.mkdir(parents=True,exist_ok=True);old=json.loads(pathlib.Path('simulation/Scenarios/recorded-la-draft.json').read_text());opening=json.loads(pathlib.Path('simulation/Scenarios/recorded-la-reviewed-opening60.json').read_text());houses=json.loads((root/'house-onsets-v1.json').read_text());changes=json.loads((root/'road-changes-v7-dynamic.json').read_text());terrain=json.loads((base/'terrain.json').read_text());clock=json.loads((base/'clock-raw.json').read_text());raw=np.cumsum([v['speed'] for v in clock]);anchors=[86,160,232,307,416,537,712,803,877];vals=[raw[t] for t in anchors]
colors={'yellow':0,'red':1,'cyan':2,'navy':3,'green':4}
def gametime(video):
 lo=int(video);fraction=video-lo
 def integer(t):
  if t<20:return max(0.,t-10.)
  for i,end in enumerate(anchors):
   if t<=end:
    if i==0:return max(0.,float(raw[t]+140-vals[0]))
    return i*140+float(raw[t]-vals[i-1])*140/float(vals[i]-vals[i-1])
  return float(1260+raw[min(1007,t)]-vals[-1])
 return integer(lo)+(integer(min(1007,lo+1))-integer(lo))*fraction
# Known birth intervals/initial directions visually reviewed; one motorway-occluded native remains marked uncertain.
for h in houses:
 if (h['x'],h['y'])==(8,8):h['onset']=664
 if (h['x'],h['y'])==(35,12):h['onset']=799
 if h['index']==0:h['onset']=0;h['direction']=6
 if h['index']==1:h['onset']=19.6;h['direction']=6
 if h['index']==2:h['onset']=55.5;h['direction']=4
 if h['index']==44:h['direction']=4
 if h['index']==54:h['onset']=888;h['direction']=2;h['uncertainNative']=True
native={tuple((h['x'],h['y'])):h for h in houses};events=[dict(e) for e in opening['events']];decisions=[]
for h in houses:
 if h['onset']<=60:continue
 events.append(dict(at=round(gametime(h['onset'])/.05)*.05,videoTime=h['onset'],kind='house',id=h['key'],x=h['x'],y=h['y'],color=colors[h['color']],direction=h['direction']))
for e in old['events']:
 if e['kind'] not in ['house','draw','erase','driveway'] and e['videoTime']>60:
  copy=dict(e)
  if copy.get('id')=='shop:navy:14,15':copy['layout']=2
  if copy.get('id')=='shop:green:40,17':copy['layout']=0
  events.append(copy)
shops=[e for e in events if e['kind'] in ['shop','shared']];foot={};access={}
for shop in shops:
 x,y=shop['x'],shop['y'];layout=shop['layout'];kind=shop['kind'];w,h=(4,3) if kind=='shared' else (2,3) if layout<2 else (3,2)
 for yy in range(y,y+h):
  for xx in range(x,x+w):foot[(xx,yy)]=shop['videoTime']
 ent=[((x,y+2),(x-1,y+2)),((x+3,y+2),(x+4,y+2))] if kind=='shared' else [((x,y+2),(x-1,y+2))] if layout==0 else [((x+1,y+2),(x+2,y+2))] if layout==1 else [((x,y),(x,y-1))] if layout==2 else [((x,y+1),(x,y+2))]
 for a,b in ent:access[tuple(sorted((a,b)))]=shop['videoTime']
records=json.loads((root/'diagonal-candidates.json').read_text());confirmed=[8,17,40,46,62,65,81,83,86,87,90,92,94,96,98,101,105,111];gooddiag={tuple(map(tuple,records[i]['edge'])) for i in confirmed}
(out/'diagonal-decisions.json').write_text(json.dumps([dict(v,decision='visually_confirmed' if v['index'] in confirmed else 'false_detection',reason='Manual candidate and later stable crop review; native stubs are processed separately') for v in records],indent=2))
cache={}
def direct_white(a,b,t):
 t=min(1007,int(t));
 if t not in cache:
  im=cv2.imread(str(root/'boards'/f'{t:04}.png'));cache[t]=(im.min(axis=2)>205)&(im.max(axis=2)-im.min(axis=2)<16)
 mask=cache[t];points=[((a[0]+.5+(b[0]-a[0])*f)*20,(a[1]+.5+(b[1]-a[1])*f)*20) for f in np.linspace(.5,.95,12)]
 return float(np.mean([mask[round(y)-1:round(y)+2,round(x)-1:round(x)+2].mean() for x,y in points]))
false_windows={
 tuple(sorted(((31,15),(32,15)))):(700,705),
 tuple(sorted(((25,11),(25,12)))):(608,1007),
 tuple(sorted(((37,9),(38,9)))):(686,1007),
 tuple(sorted(((24,11),(24,12)))):(549,1007),
 tuple(sorted(((25,12),(25,13)))):(248,474),
 tuple(sorted(((21,9),(21,10)))):(267,303),
 tuple(sorted(((20,10),(21,10)))):(267,303),
 tuple(sorted(((14,17),(14,18)))):(282,540),
 tuple(sorted(((15,6),(15,7)))):(284,1007),
 tuple(sorted(((26,12),(26,13)))):(284,475),
 tuple(sorted(((25,15),(25,16)))):(314,360),
 tuple(sorted(((11,13),(12,13)))):(440,736),
 tuple(sorted(((12,12),(12,13)))):(443,736),
 tuple(sorted(((19,14),(19,15)))):(435,1007),
 tuple(sorted(((25,17),(26,17)))):(437,666),
 # handoff correction 1: rounded cyan diagonal side, not a road (actual diagonal 24,11-25,12 stays)
 tuple(sorted(((24,12),(25,12)))):(715,1007),
 # handoff correction 2: empty side beside the cyan 8,11 NE native stub to 9,10 (paid 9,10-10,10 stays)
 tuple(sorted(((9,10),(9,11)))):(731,1007),
 # handoff correction 3: green destination 39,16 spawn circle and lot outline, never a road (boards 841-1007)
 tuple(sorted(((38,16),(38,17)))):(841,1007),
 tuple(sorted(((38,17),(38,18)))):(841,1007),
 # handoff correction 5: false horizontal side beside the real 37,20-40,23 diagonal (841 add, 849 erase, 857 add)
 tuple(sorted(((37,20),(38,20)))):(841,1007),
 # handoff correction 7: blue cursor ring on empty grass, not a road
 tuple(sorted(((43,8),(43,9)))):(859,1007)}
def allowed(edge,t):
 a,b=edge
 if 776<=t<=780 and any(18<=x<=32 and 4<=y<=7 for x,y in edge):return False
 if edge in false_windows and false_windows[edge][0]<=t<=false_windows[edge][1]:return False
 if any(terrain[y][x] in '#^' for x,y in edge):return False
 water=[p for p in edge if terrain[p[1]][p[0]]=='~']
 if water and (a[1]!=b[1] or any(p not in {(22,13),(33,22)} for p in water)):return False
 if (22,13) in water and t<129:return False
 if (33,22) in water and t<384:return False
 if any(p in foot and t>=foot[p] for p in edge):return edge in access
 if t>=748 and any(p in {(19,9),(19,8),(18,9),(19,10),(20,9)} for p in edge):return False
 if a[0]!=b[0] and a[1]!=b[1] and edge not in gooddiag:return False
 return True
active={tuple(sorted(((e['x'],e['y']),(e['toX'],e['toY'])))) for e in opening['events'] if e['kind']=='draw'};directions={p:h['direction'] for p,h in native.items()};pending=[]
# Replay detected road changes after manually reviewed opening. All events still face the strict simulator gate.
# Specific manual corrections: junction diagonal replaced by two cardinal edges;
# later real cyan/green connection and cyan reroute must not inherit earlier false detections.
changes.extend([
 dict(video=301,kind='remove',edge=[20,10,21,9],score=0),
 dict(video=362,kind='add',edge=[25,15,25,16],score=1),
 dict(video=475,kind='add',edge=[25,12,25,13],score=1),
 # handoff correction 6: both temporary verticals drawn 853 are erased by 855 (stock 14->12->14); detector removed only one
 dict(video=855,kind='remove',edge=[40,22,40,23],score=0),
 # handoff correction 4: green 38,19 turns SW->N, first unambiguous at 846 (~1 s uncertainty); meets the green
 # destination's left-entrance stub at the common native endpoint 38,18
 dict(video=846,kind='turn',target=(38,19),direction=6)])
changes.sort(key=lambda c:(c['video'],0 if c['kind']=='remove' else 1))
for change in changes:
 if change['kind']=='turn':
  home=change['target'];events.append(dict(at=round(gametime(change['video'])/.05)*.05,videoTime=change['video'],kind='driveway',target=native[home]['key'],direction=change['direction']));directions[home]=change['direction'];continue
 t=change['video'];a,b=tuple(change['edge'][:2]),tuple(change['edge'][2:]);edge=tuple(sorted((a,b)))
 if t<=60 or not allowed(edge,t):continue
 if edge in access and t>=access[edge]:continue
 hs=[p for p in edge if p in native and t>=native[p]['onset']]
 if hs:
  if change['kind']!='add' or len(hs)!=1:continue
  home=hs[0];other=b if a==home else a;dx,dy=other[0]-home[0],other[1]-home[1];direction=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)].index((dx,dy))
  if direction==directions[home]:continue
  scores=[direct_white(home,other,t+i) for i in range(9)]
  onset=next((i for i in range(8) if scores[i]>=.8 and scores[i+1]>=.65),None)
  if onset is None:decisions.append(dict(video=t,edge=edge,reason='Reject apparent native turn: direct undilated stub not persistently visible',scores=scores));continue
  actual=t+onset
  events.append(dict(at=round(gametime(actual)/.05)*.05,videoTime=actual,kind='driveway',target=native[home]['key'],direction=direction));directions[home]=direction;continue
 if change['kind']=='add':
  if edge in active:continue
  active.add(edge);kind='draw'
 else:
  if edge not in active:continue
  active.remove(edge);kind='erase'
 events.append(dict(at=round(gametime(t)/.05)*.05,videoTime=t,kind=kind,x=a[0],y=a[1],toX=b[0],toY=b[1]))
# Opening infrastructure is already present; suppress any detector add/remove pair only when its semantics is redundant.
events.sort(key=lambda e:(e['at'],e['videoTime'],0 if e['kind'] in ['house','shop','shared','join'] else 1))
old.update(id='video-c9762eb1-full-review-v21',source='Reconstructed full video under strict input validation',uncertainties='Full review candidate v21 = v20 plus the seven handoff input corrections, NOT certified exact original state. Green 38,19 north turn time has ~1 s uncertainty; green 37,20-37,21 branch onset 858 is ~1 s late versus stock and left unchanged. Reviewed55houses, explicit driveway turns, dynamic destination footprints, manually screened diagonals. Timing sampled1s; one native direction hidden by motorway. Further checkpoints/rejections remain to validate.',events=events)
(out/'trace-v21.json').write_text(json.dumps(old,indent=2));(out/'native-turn-rejections-v21.json').write_text(json.dumps(decisions,indent=2));(out/'houses-reviewed-v21.json').write_text(json.dumps(houses,indent=2));print('events',len(events),'houses',len(houses),'screened native candidates',len(decisions))
