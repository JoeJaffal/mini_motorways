"""Export numeric level profiles from a locally installed, user-owned game.
Requires UnityPy and TypeTreeGeneratorAPI. Does not copy code, art or assemblies.
"""
import argparse,json,pathlib,hashlib
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
import UnityPy

NAMES=[('losangeles','LosAngeles'),('beijing','Beijing'),('tokyo','Tokyo'),('daressalaam','DarEsSalaam'),('london','London')]
def num(x): return x['m_rawValue']/2**32

def read(root,name,gen):
 env=UnityPy.load(str(root/'StreamingAssets/AssetBundles'/name));env.typetree_generator=gen
 trees={};tilemaps={}
 for o in env.objects:
  if o.type.name=='Tilemap':tilemaps[o.path_id]=o.read_typetree()
  if o.type.name=='Sprite':trees.setdefault('_spriteNames',{})[o.path_id]=o.read().m_Name
  if o.type.name!='MonoBehaviour':continue
  try:
   h=o.parse_monobehaviour_head();s=h.m_Script.deref_parse_as_object()
   if s.m_ClassName=='WeightTile':
    nodes=gen.get_nodes_up(s.m_AssemblyName,(s.m_Namespace+'.' if s.m_Namespace else '')+s.m_ClassName)
    trees.setdefault('_weightTiles',{})[o.path_id]=o.read_typetree(nodes=nodes)
   if s.m_ClassName in ('CityDefinition','CityTilemap','CitySchedulePlanner','SimulationConstantsData'):
    nodes=gen.get_nodes_up(s.m_AssemblyName,(s.m_Namespace+'.' if s.m_Namespace else '')+s.m_ClassName)
    trees[s.m_ClassName]=o.read_typetree(nodes=nodes)
  except Exception:continue
 return trees,tilemaps

def rail_lines(trees,tilemaps,ct):
 railmap=tilemaps.get(ct['railTilemap']['m_PathID'],{});assets=railmap.get('m_TileAssetArray',[]);rail={}
 for pos,tile in railmap.get('m_Tiles',[]):
  props=trees.get('_weightTiles',{}).get(assets[tile['m_TileIndex']]['m_Data']['m_PathID'],{})
  sprite=props.get('sprite',{}).get('m_PathID',0)
  rail[(pos['x'],pos['y'])]=trees.get('_spriteNames',{}).get(sprite)=='blank_s'
 def neighbors(p):
  x,y=p;result=[]
  for dx,dy in [(0,1),(1,0),(0,-1),(-1,0)]:
   if (x+dx,y+dy) in rail:result.append((x+dx,y+dy))
  for dx,dy in [(1,1),(1,-1),(-1,-1),(-1,1)]:
   if (x+dx,y+dy) in rail and (x+dx,y) not in rail and (x,y+dy) not in rail:result.append((x+dx,y+dy))
  return result
 lines=[];remaining=set(rail)
 while remaining:
  ordered=sorted(remaining,key=lambda c:(c[1],c[0]));start=next((p for p in ordered if len(neighbors(p))<=1),ordered[0]);path=[];stack=[start]
  while stack:
   p=stack.pop()
   if p not in remaining:continue
   remaining.remove(p);path.append(p);stack.extend(n for n in neighbors(p) if n in remaining)
  if any(len(neighbors(p))>2 for p in path):raise ValueError('Branched rail network needs explicit handling')
  loop=len(path)>2 and start in neighbors(path[-1]);spawn=next((i for i,p in enumerate(path) if rail[p]),-1)
  lines.append(dict(cells=[[x+25,14-y] for x,y in path],loop=loop,spawn=spawn))
 return lines

def export(root,destination):
 gen=TypeTreeGenerator('2022.3.62f2');gen.load_local_dll_folder(str(root/'Managed'))
 profiles=[];packages=[];hashes={}
 for bundle,kind in NAMES:
  trees,tilemaps=read(root,bundle,gen);ct=trees['CityTilemap'];cd=trees['CityDefinition'];sched=trees['CitySchedulePlanner']
  def cells(ptr):
   return {(v[0]['x'],v[0]['y']) for v in tilemaps.get(ptr['m_PathID'],{}).get('m_Tiles',[]) if v[0].get('z',0)==0}
  water=cells(ct['bridgeableTilemap']);mountain=cells(ct['mountainTilemap']);rail=cells(ct['railTilemap'])
  blocked=cells(ct['unbuildableTilemap'])-water;unzone=cells(ct['unzoneableTilemap'])
  rows=[''.join('~' if (x,y) in water else '^' if (x,y) in mountain else '=' if (x,y) in rail else '#' if (x,y) in blocked else ':' if (x,y) in unzone else '.' for x in range(-25,25)) for y in range(14,-16,-1)]
  osc=sched['demandOscillationData'];groups=len(osc);zones=[]
  for typ in (1,0):
   group=[]
   for color in range(groups):
    coords=set()
    for d in ct['cityTileDefinitions']:
     if d['type']==typ and d['groupIndex'] in (color,-1):coords|=cells(d['tiles'])
    group.append(sorted((14-y)*50+x+25 for x,y in coords if -25<=x<25 and -15<=y<=14 and (x,y) not in water|blocked|unzone|mountain|rail))
   zones.append(group)
  circles=[]
  for color in range(groups):
   coords=set()
   for definition in ct['cityTileDefinitions']:
    if definition['type']!=0 or definition['groupIndex']!=color:continue
    tilemap=tilemaps.get(definition['tiles']['m_PathID'],{});assets=tilemap.get('m_TileAssetArray',[])
    for pos,tile in tilemap.get('m_Tiles',[]):
     asset=assets[tile['m_TileIndex']]['m_Data']['m_PathID']
     if trees.get('_weightTiles',{}).get(asset,{}).get('isCircle',False):coords.add((pos['x'],pos['y']))
   circles.append(sorted((14-y)*50+x+25 for x,y in coords if -25<=x<25 and -15<=y<=14))
  plan=[]
  for ch in sched['scheduleChunks']:
   plan.append(dict(start=ch['startDay'],duration=ch['duration'],ordered=bool(ch['buildingsAreOrdered']),variation=num(ch['spawnVariability']),items=[[b['type'],b['groupIndex'],b['grouping'],1+b['additionalDemandMultiplier'],b['carparkPreference']] for b in ch['plannedBuildings']]))
  schedule=[(ch['startDay'],ch['duration'],b['groupIndex']) for ch in sched['scheduleChunks'] for b in ch['plannedBuildings'] if b['type']==0]
  zoom=cd['cameraZoom'];curve=zoom['velocity']['m_Curve']
  offsets=cd.get('startingOffsets',{}).get('offsets',[])
  profile=dict(name=kind,rows=rows,rail=rail_lines(trees,tilemaps,ct),station=sorted((14-y)*50+x+25 for x,y in cells(ct['stationDemandTilemap']) if -25<=x<25 and -15<=y<=14),house=zones[0],shop=zones[1],circle=circles,plan=plan,schedule=schedule,
   base=[num(d['baseDemand']) for d in osc],burst=[num(d['burstDemand']) for d in osc],ecc=[d['eccentricity'] for d in osc],period=[d['periodInDays'] for d in osc],
   ramp=[cd['spawnRamp']['startDay'],num(cd['spawnRamp']['dailyIncrement'])],zoom=[num(zoom[k]) for k in ['startSize','endSize','delayInDays','durationInDays']],curve=[[k[s] for s in ['time','value','inSlope','outSlope']] for k in curve],
   offsets=[[num(o['fixedPosition']['x'])/2,num(o['fixedPosition']['y'])/2,num(o['variance'])/2] for o in offsets])
  profiles.append(profile);packages.append((kind,cd['upgradeDefinitions']))
  hashes[bundle]=hashlib.sha256((root/'StreamingAssets/AssetBundles'/bundle).read_bytes()).hexdigest()
 def nums(a):return ','.join(repr(v) for v in a)
 def array(a,typ='double'):return 'new '+typ+'[]{'+nums(a)+'}'
 def matrix(a,typ='double'):return 'new '+typ+'[][]{'+','.join(array(r,typ) for r in a)+'}'
 s='// Generated numeric observations from locally installed city bundles. No original code or art.\nnamespace MotorwaysSim {\n'
 s+='public sealed class CityProfile { public string Name; public string[] Terrain; public int[][] HouseZones,ShopZones,CircleZones; public PlanChunk[] Plan; public RailLineProfile[] RailLines; public int[] StationZone; public double[][] ShopSchedule,ZoomCurve,StartOffsets; public double[] BaseDemand,BurstDemand,Zoom,SpawnRamp; public int[] Eccentricity,PeriodDays; }\n'
 s+='public static class CityCatalog { public static readonly ScenarioKind[] Maps={'+','.join('ScenarioKind.'+p['name'] for p in profiles)+'};\n'
 s+='public static CityProfile Get(ScenarioKind scenario) {switch(scenario){'+''.join('case ScenarioKind.'+p['name']+':return Profiles['+str(i)+'];' for i,p in enumerate(profiles))+'default:return Profiles[0];}}\nstatic readonly CityProfile[] Profiles={\n'
 for p in profiles:
  s+='new CityProfile{Name="'+p['name']+'",Terrain=new string[]{'+','.join(json.dumps(r) for r in p['rows'])+'},HouseZones='+matrix(p['house'],'int')+',ShopZones='+matrix(p['shop'],'int')+',StationZone='+array(p['station'],'int')+',RailLines=new RailLineProfile[]{'+','.join('new RailLineProfile{Loop='+str(line['loop']).lower()+',SpawnIndex='+str(line['spawn'])+',Cells=new Cell[]{'+','.join('new Cell('+nums(c)+')' for c in line['cells'])+'}}' for line in p['rail'])+'},CircleZones='+matrix(p['circle'],'int')+',Plan=new PlanChunk[]{'+','.join('new PlanChunk{Start='+repr(ch['start'])+',Duration='+repr(ch['duration'])+',Ordered='+str(ch['ordered']).lower()+',Variation='+repr(ch['variation'])+',Items='+matrix(ch['items'])+'}' for ch in p['plan'])+'},ShopSchedule='+matrix(p['schedule'])+',BaseDemand='+array(p['base'])+',BurstDemand='+array(p['burst'])+',Eccentricity='+array(p['ecc'],'int')+',PeriodDays='+array(p['period'],'int')+',SpawnRamp='+array(p['ramp'])+',Zoom='+array(p['zoom'])+',ZoomCurve='+matrix(p['curve'])+',StartOffsets='+matrix(p['offsets'])+'},\n'
 s+='};}}\n';(destination/'CityCatalog.cs').write_text(s)
 s='// Generated city material quantities and package metadata.\nnamespace MotorwaysSim { public sealed class UpgradeOffer {public int Type,Amount,Roads,FirstWeek,LastWeek,Maximum;public double Weight;}\npublic static class OriginalUpgrades {public static int[] Starting(string city){switch(city){'
 for name,data in packages:
  inv=[0]*6
  for p in data['startingPackages']:
   if p['type']<6:inv[p['type']]+=p['amount'];inv[0]+=p['additionalConcrete']
  s+='case "'+name+'":return '+array(inv,'int')+';'
 s+='default:return new int[]{25,1,0,0,0,0};}}public static UpgradeOffer[] Offers(string city){switch(city){'
 for name,data in packages:
  s+='case "'+name+'":return new UpgradeOffer[]{'
  for o in data['weeklyChoicePackages']:
   p=o['package']
   s+='new UpgradeOffer{Type='+str(p['type'])+',Amount='+str(p['amount'])+',Roads='+str(p['additionalConcrete'])+',FirstWeek='+str(o['startingWeek'])+',LastWeek='+str(o['lastWeek'])+',Maximum='+str(o['maxPackageCount'])+',Weight='+repr(num(o['baseWeight']))+'},'
  s+='};'
 s+='default:return new UpgradeOffer[0];}}}}\n';(destination/'OriginalUpgrades.cs').write_text(s)
 provenance=dict(source='User-owned installed game; numeric data only',assemblySha256=hashlib.sha256((root/'Managed/App.dll').read_bytes()).hexdigest(),bundles=hashes,canvas=dict(width=50,height=30,worldXMin=-25,worldYMax=14),notes='Canvas contains the final playable area for these five profiles; use zoom bounds. Train geometry, station placement and full spawn behavior remain unverified. Rail topology, train origins, station zones and tuning values are exported numerically. Plan chunks retain grouping, ordering, variability and demand multipliers.')
 (destination.parent.parent/'Docs/REFERENCE_DATA.json').write_text(json.dumps(provenance,indent=2))
 print('Exported five profiles; London rail:',[(len(l['cells']),l['loop'],l['spawn']) for l in profiles[-1]['rail']])
 core=read(root,'core',gen)[0]['SimulationConstantsData']
 fields={'Speed':'trainSpeed','Acceleration':'trainAcceleration','Deceleration':'trainDeceleration','MinimumSpeed':'trainMinimumSpeedDuringDeceleration','BufferDistance':'trainStoppingDistanceFromBuffer','SignalDistance':'trainCrossingSignalDistance','WheelDistance':'trainCenterToWheelDistance','CarriageGap':'trainCarriageSeparationDistance'}
 tuning='// Numeric observations from installed SimulationConstantsData. Distances are in tiles.\nnamespace MotorwaysSim {public static class TrainTuning {\n'
 for field,key in fields.items():tuning+='public const double '+field+'='+repr(num(core[key])/2)+';\n'
 for field,key in {'StationWait':'trainStationWaitTime','CrossingWait':'crossingWaitTime','DemandPerHouse':'demandPerHouse'}.items():tuning+='public const double '+field+'='+repr(num(core[key]))+';\n'
 for field,key in {'MinimumDemand':'minDemandFromTrain','MaximumDemand':'maxDemandFromTrain'}.items():tuning+='public const int '+field+'='+str(core[key])+';\n'
 tuning+='}}\n';(destination/'TrainTuning.cs').write_text(tuning)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--game-data',type=pathlib.Path,required=True);ap.add_argument('--destination',type=pathlib.Path,default=pathlib.Path('simulation/Assets/Simulation'));args=ap.parse_args();export(args.game_data,args.destination)
