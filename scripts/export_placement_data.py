"""Export numeric building-placement data from a locally installed, user-owned game.

Writes simulation/Assets/Simulation/OriginalPlacementData.cs: per city and colour the house ("Supply") and
destination ("Demand") spawn-weight layers, the spawn-density map, the unbuildable mask, the station weight layer
and the minimum/maximum suburb-count curves. Numbers only; no code, art or assemblies are copied.
Requires UnityPy and TypeTreeGeneratorAPI (same environment as export_reference_profiles.py).

Canvas mapping (as export_reference_profiles.py): canvas x = tile.x + 25, canvas y = 14 - tile.y, 50 x 30.
Weight rows use one character per tile: '.' = tile not in the layer, digit k = weight k/4.
Density rows: '0' high (also where no density tile is painted), '1' medium, '2' low.
"""
import argparse,pathlib
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
import UnityPy

NAMES=[('losangeles','LosAngeles'),('beijing','Beijing'),('tokyo','Tokyo'),('daressalaam','DarEsSalaam'),('london','London')]
WIDTH,HEIGHT=50,30
DEMAND,SUPPLY=0,1

def read(root,name,gen):
 env=UnityPy.load(str(root/'StreamingAssets/AssetBundles'/name));env.typetree_generator=gen
 trees={};tilemaps={};tiles={}
 for o in env.objects:
  if o.type.name=='Tilemap':tilemaps[o.path_id]=o.read_typetree()
  if o.type.name!='MonoBehaviour':continue
  try:
   h=o.parse_monobehaviour_head();s=h.m_Script.deref_parse_as_object()
   if s.m_ClassName not in ('WeightTile','DensityTile','CityTilemap','CitySchedulePlanner'):continue
   nodes=gen.get_nodes_up(s.m_AssemblyName,(s.m_Namespace+'.' if s.m_Namespace else '')+s.m_ClassName)
   tree=o.read_typetree(nodes=nodes)
   if s.m_ClassName in ('WeightTile','DensityTile'):tiles[o.path_id]=(s.m_ClassName,tree)
   else:trees[s.m_ClassName]=tree
  except Exception:continue
 return trees,tilemaps,tiles

def layer(tilemaps,tiles,ptr):
 """Tile position (z = 0 only, as the original looks tiles up with z = 0) -> (class name, properties)."""
 tm=tilemaps.get(ptr['m_PathID'],{}) if ptr else {};assets=tm.get('m_TileAssetArray',[]);out={}
 for pos,tile in tm.get('m_Tiles',[]):
  if pos.get('z',0)!=0:continue
  out[(pos['x'],pos['y'])]=tiles.get(assets[tile['m_TileIndex']]['m_Data']['m_PathID'],('Tile',{}))
 return out

def canvas(values,default):
 rows=[[default]*WIDTH for _ in range(HEIGHT)]
 for (x,y),c in values.items():
  cx,cy=x+25,14-y
  if 0<=cx<WIDTH and 0<=cy<HEIGHT:rows[cy][cx]=c
 return [''.join(r) for r in rows]

def weight_char(entry):
 kind,props=entry
 # BuildingSpawningTileWeights: a WeightTile contributes its tileWeight, any other tile weight 1.
 w=props.get('tileWeight',1.0) if kind=='WeightTile' else 1.0
 k=round(w*4)
 if abs(k-w*4)>1e-6 or not 0<=k<=9:raise ValueError(f'weight {w} is not a quarter step in 0..2.25; extend the encoding')
 return str(k)

def curve(c):
 keys=c['m_Curve']
 if any(k.get('weightedMode',0)!=0 for k in keys):raise ValueError('weighted suburb-curve tangents need explicit handling')
 return [[k['time'],k['value'],k['inSlope'],k['outSlope']] for k in keys]

def export(root,destination):
 gen=TypeTreeGenerator('2022.3.62f2');gen.load_local_dll_folder(str(root/'Managed'))
 profiles=[]
 for bundle,kind in NAMES:
  trees,tilemaps,tiles=read(root,bundle,gen);ct=trees['CityTilemap'];planner=trees['CitySchedulePlanner']
  groups=len(planner['demandOscillationData'])
  # CitySpawningLayerData keys layers by (type, groupIndex); a later definition with the same key replaces an earlier one.
  definitions={}
  for d in ct['cityTileDefinitions']:definitions[(d['type'],d['groupIndex'])]=d
  for (t,g),d in definitions.items():
   if g==-1 and layer(tilemaps,tiles,d['tiles']):print(f'note: {kind} has a non-empty all-colour layer (type {t}); placement by colour never reads it')
  def weights(t,g):
   d=definitions.get((t,g))
   return canvas({p:weight_char(e) for p,e in layer(tilemaps,tiles,d['tiles']).items()},'.') if d else ['.'*WIDTH]*HEIGHT
  density=canvas({p:str(e[1].get('group',0)) for p,e in layer(tilemaps,tiles,ct.get('spawnDensityTilemap')).items() if e[0]=='DensityTile'},'0')
  unbuildable=canvas({p:'#' for p in layer(tilemaps,tiles,ct.get('unbuildableTilemap'))},'.')
  station=canvas({p:weight_char(e) for p,e in layer(tilemaps,tiles,ct.get('stationDemandTilemap')).items()},'.')
  sched=planner['scheduleGroups']
  profiles.append(dict(name=kind,house=[weights(SUPPLY,g) for g in range(groups)],destination=[weights(DEMAND,g) for g in range(groups)],
   density=density,unbuildable=unbuildable,station=station,
   minimum=[curve(sched[g]['minimumNumSuburbs']) for g in range(groups)],maximum=[curve(sched[g]['maximumNumSuburbs']) for g in range(groups)]))
  print(kind,'groups',groups,'house tiles',[sum(WIDTH-r.count('.') for r in l) for l in profiles[-1]['house']],
   'destination tiles',[sum(WIDTH-r.count('.') for r in l) for l in profiles[-1]['destination']],
   'density medium/low',sum(r.count('1') for r in density),sum(r.count('2') for r in density))
 def strings(rows):return 'new string[]{'+','.join('"'+r+'"' for r in rows)+'}'
 def layers(ls):return 'new string[][]{'+','.join(strings(l) for l in ls)+'}'
 def keys(k):return 'new double[][]{'+','.join('new double[]{'+','.join(repr(float(v)) for v in key)+'}' for key in k)+'}'
 def curves(cs):return 'new double[][][]{'+','.join(keys(c) for c in cs)+'}'
 s='// Generated by scripts/export_placement_data.py: numeric spawn-placement observations from locally installed city bundles.\n'
 s+='// No original code or art. Weight rows: \'.\' = not in the layer, digit k = weight k/4. Density: 0 high, 1 medium, 2 low.\n'
 s+='namespace MotorwaysSim {\n'
 s+='public sealed class CityPlacementProfile { public string Name; public string[][] HouseWeights,DestinationWeights; public string[] StationWeights,Density,Unbuildable; public double[][][] MinimumSuburbs,MaximumSuburbs; }\n'
 s+='public static class OriginalPlacementData {\n'
 s+='public static CityPlacementProfile Get(ScenarioKind scenario) {switch(scenario){'+''.join('case ScenarioKind.'+p['name']+':return Profiles['+str(i)+'];' for i,p in enumerate(profiles))+'default:return null;}}\n'
 s+='static readonly CityPlacementProfile[] Profiles={\n'
 for p in profiles:
  s+='new CityPlacementProfile{Name="'+p['name']+'",\nHouseWeights='+layers(p['house'])+',\nDestinationWeights='+layers(p['destination'])+',\nStationWeights='+strings(p['station'])+',\nDensity='+strings(p['density'])+',\nUnbuildable='+strings(p['unbuildable'])+',\nMinimumSuburbs='+curves(p['minimum'])+',\nMaximumSuburbs='+curves(p['maximum'])+'},\n'
 s+='};}}\n'
 (destination/'OriginalPlacementData.cs').write_text(s,newline='\n')
 print('Wrote',destination/'OriginalPlacementData.cs')

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--game-data',type=pathlib.Path,required=True)
 ap.add_argument('--destination',type=pathlib.Path,default=pathlib.Path('simulation/Assets/Simulation'))
 args=ap.parse_args();export(args.game_data,args.destination)
