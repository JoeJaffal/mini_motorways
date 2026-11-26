"""Draft 50x30 geometric projection. Fails closed on topology conflicts."""
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import argparse, math
from experiment import read, write, digest
ROOT = Path(__file__).resolve().parent

def raster(a,b):
    x,y=a; xx,yy=b
    dx,dy=abs(xx-x),-abs(yy-y)
    sx,sy=1 if x<xx else -1,1 if y<yy else -1
    err=dx+dy; cells=[]
    while True:
        cells.append([x,y])
        if [x,y]==[xx,yy]: return cells
        twice=2*err
        if twice>=dy: err+=dy; x+=sx
        if twice<=dx: err+=dx; y+=sy

def project(scenario, width=50, height=30, margin=2, offset=(0,0), paths_override=None):
    if width<2*margin+2 or height<2*margin+2: raise ValueError('Grid too small')
    xs=[n['xy'][0] for n in scenario['nodes']]; ys=[n['xy'][1] for n in scenario['nodes']]
    scale=min((width-1-2*margin)/(max(xs)-min(xs)),(height-1-2*margin)/(max(ys)-min(ys)))
    ox=(width-1-(max(xs)-min(xs))*scale)/2+offset[0]
    oy=(height-1-(max(ys)-min(ys))*scale)/2+offset[1]
    def xy(p): return [round(ox+(p[0]-min(xs))*scale),round(oy+(p[1]-min(ys))*scale)]
    positions={n['id']:xy(n['xy']) for n in scenario['nodes']}
    roads={e['id']:raster(positions[e['u']],positions[e['v']]) for e in scenario['edges']}
    if paths_override: roads.update(paths_override)
    edge_lookup={e['id']:e for e in scenario['edges']}
    owners=defaultdict(list)
    for n,p in positions.items(): owners[tuple(p)].append(n)
    conflicts=[{'type':'merged_source_nodes','cell':list(p),'nodes':ns} for p,ns in owners.items() if len(ns)>1]
    occupied=defaultdict(list)
    diagonals=defaultdict(list)
    for eid,cells in roads.items():
        for cell in cells: occupied[tuple(cell)].append(eid)
        for a,b in zip(cells,cells[1:]):
            if a[0]!=b[0] and a[1]!=b[1]: diagonals[(min(a[0],b[0]),min(a[1],b[1]))].append((eid,(b[0]-a[0])*(b[1]-a[1])))
    for cell,eids in occupied.items():
        for a,b in combinations(eids,2):
            ea,eb=edge_lookup[a],edge_lookup[b]
            shared={ea['u'],ea['v']}&{eb['u'],eb['v']}
            if not any(tuple(positions[n])==cell for n in shared):
                conflicts.append({'type':'unintended_corridor_overlap','cell':list(cell),'edges':[a,b]})
    for cell, entries in diagonals.items():
        for (a,sa),(b,sb) in combinations(entries,2):
            if a!=b and sa!=sb: conflicts.append({'type':'diagonal_crossing','square':list(cell),'edges':[a,b]})
    source_xy={n['id']:n['xy'] for n in scenario['nodes']}
    for nid,pos in positions.items():
        incident=[e for e in scenario['edges'] if nid in (e['u'],e['v'])]
        if len(incident)<3: continue
        def source_angle(e):
            other=e['v'] if e['u']==nid else e['u']
            return math.atan2(source_xy[other][1]-source_xy[nid][1],source_xy[other][0]-source_xy[nid][0])
        def grid_angle(e):
            cells=roads[e['id']]
            p=cells[1] if e['u']==nid else cells[-2]
            return math.atan2(p[1]-pos[1],p[0]-pos[0])
        if any(len(roads[e['id']])<2 for e in incident): continue
        a=[e['id'] for e in sorted(incident,key=source_angle)]
        b=[e['id'] for e in sorted(incident,key=grid_angle)]
        if not any(a==b[k:]+b[:k] for k in range(len(b))): conflicts.append({'type':'changed_junction_order','cell':pos,'node':nid})
    for eid,cells in roads.items():
        if len(set(map(tuple,cells)))!=len(cells): conflicts.append({'type':'self_overlap','cell':cells[0],'edges':[eid]})
        if any(not (0<=p[0]<width and 0<=p[1]<height) for p in cells): conflicts.append({'type':'outside_grid','cell':cells[0],'edges':[eid]})
    return {'schema_version':1,'scenario_sha256':digest(scenario),'width':width,'height':height,
            'projection':{'margin':margin,'offset':list(offset),'scale':scale},
            'status':'blocked_topology_conflicts' if conflicts else 'geometry_only_pending_building_access',
            'runnable_in_game':False,'source_node_cells':positions,'corridor_cells':roads,
            'parcel_centroid_markers':{p['id']:xy(p['centroid']) for p in scenario['places']},
            'conflicts':conflicts,'notes':['Centroid markers are not spawned buildings.','No mbrl channel layout is assumed.','Use source edge IDs for scoring; never charge raster tile counts.','Building footprints and driveways must preserve parcel access and be validated before use.']}

def svg(grid,scenario,path):
    lines=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 52 34">','<rect x="-1" y="-1" width="52" height="34" fill="white"/>']
    for e in scenario['edges']:
        pts=' '.join(f'{x},{y}' for x,y in grid['corridor_cells'][e['id']])
        color='#24364b' if e['existing'] else '#aaa'
        lines.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="0.15"/>')
    for p in grid['parcel_centroid_markers'].values(): lines.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="0.18" fill="#197a55"/>')
    for c in grid['conflicts']:
        p=c.get('cell',c.get('square'))
        lines.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="0.35" fill="none" stroke="#c00" stroke-width="0.1"/>')
    lines.append('<text x="0" y="32" font-size="0.8">Draft only: red marks indicate topology conflicts; dots are parcel markers.</text></svg>')
    Path(path).write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':
    s=read(ROOT/'data/harare.json')
    candidates=(project(s,margin=m,offset=(x,y)) for m in [1,1.25,1.5,1.75,2,2.25] for x in [-0.5,-0.25,0,0.25,0.5] for y in [-0.5,-0.25,0,0.25,0.5])
    g=min(candidates,key=lambda item:len(item['conflicts']))
    # Try one short waypoint detour for each conflicting corridor; accept only
    # layouts passing the same overlap/crossing/junction-order audit.
    p=g['projection']
    for conflict in list(g['conflicts']):
        for eid in conflict.get('edges',[]):
            start,end=g['corridor_cells'][eid][0],g['corridor_cells'][eid][-1]
            center=conflict.get('cell',conflict.get('square'))
            if center is None: continue
            for dx in range(-2,3):
                for dy in range(-2,3):
                    waypoint=[center[0]+dx,center[1]+dy]
                    path=raster(start,waypoint)[:-1]+raster(waypoint,end)
                    candidate=project(s,margin=p['margin'],offset=p['offset'],paths_override={**g['corridor_cells'],eid:path})
                    if len(candidate['conflicts'])<len(g['conflicts']): g=candidate
    write(ROOT/'data/grid-draft.json',g); svg(g,s,ROOT/'results/grid-draft.svg')
    print(g['status'],len(g['conflicts']),'conflicts')


