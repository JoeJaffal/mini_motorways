"""Second generalization: paired SUMO evaluation on fixed, road-independent demand."""
from pathlib import Path
from collections import Counter
from itertools import combinations
import argparse, csv, hashlib, heapq, importlib.util, json, math, random, shutil, statistics, subprocess, sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
FIRST=ROOT.parent/'first generalization'
sys.path.append(str(FIRST))
from experiment import read, write, digest, Episode


def xml(path,root):
    ET.indent(root)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def validate_config(c):
    for name in ['cell_size_m','junction_radius_m','speed_mps','connector_speed_mps','lane_width_m','step_length_s','vehicle_length_m','vehicle_min_gap_m','vehicle_tau_s','end_s','departure_window_s']:
        if isinstance(c[name],bool) or not isinstance(c[name],(int,float)) or not math.isfinite(c[name]) or c[name]<=0: raise ValueError('Invalid '+name)
    if isinstance(c['trip_count'],bool) or not isinstance(c['trip_count'],int) or c['trip_count']<1: raise ValueError('Invalid trip count')
    if isinstance(c['departure_window_s'],bool) or not isinstance(c['departure_window_s'],int): raise ValueError('Departure window must be integer seconds')
    if c['end_s']<=c['departure_window_s']: raise ValueError('End must exceed departure window')
    if not c['evaluation_seeds'] or any(isinstance(s,bool) or not isinstance(s,int) or not 0<=s<2**31 for s in c['evaluation_seeds']) or len(set(c['evaluation_seeds']))!=len(c['evaluation_seeds']): raise ValueError('Invalid evaluation seeds')
    if c['construction_seed'] in c['evaluation_seeds']: raise ValueError('Construction and evaluation seeds must differ')
    if not math.isfinite(c['budget_source_cost']) or c['budget_source_cost']<=0: raise ValueError('Invalid construction budget')


class DesignState:
    """Own experiment constraints: legal corridors, road-connected additions, cost cap."""
    def __init__(self,scenario,budget):
        self.scenario=scenario; self.edges={e['id']:e for e in scenario['edges']}
        self.roads={e['id'] for e in scenario['edges'] if e['existing']}
        self.initial=self.roads.copy(); self.actions=[]; self.budget=budget; self.cost=0.; self.nr=0 if not self.unserved() else None
    def nodes(self): return {n for eid in self.roads for n in [self.edges[eid]['u'],self.edges[eid]['v']]}
    def unserved(self):
        ns=self.nodes()
        return [p['id'] for p in self.scenario['places'] if not ns.intersection(p['nodes'])]
    def legal(self):
        ns=self.nodes()
        return sorted(eid for eid,e in self.edges.items() if eid not in self.roads and not e['barrier'] and e['cost']+self.cost<=self.budget+1e-10 and ns.intersection([e['u'],e['v']]))
    def step(self,eid):
        if eid not in self.legal(): raise ValueError(f'Illegal/duplicate/disconnected/over-budget corridor {eid}')
        self.roads.add(eid); self.actions.append(eid); self.cost+=self.edges[eid]['cost']
        if self.nr is None and not self.unserved(): self.nr=len(self.actions)
    def observe(self):
        return {'scenario_sha256':digest(self.scenario),'road_edge_ids':sorted(self.roads),'legal_edge_ids':self.legal(),
                'cost_used':self.cost,'cost_remaining':self.budget-self.cost,'unserved_place_ids':self.unserved(),
                'stop_allowed':True,'action_unit':'one complete source corridor','no_KDD_33_step_limit':True}
    def design(self,label): return {'schema_version':1,'scenario_sha256':digest(self.scenario),'label':label,'actions':list(self.actions)}


def validate_design(s,d,budget):
    if d.get('schema_version')!=1 or d.get('scenario_sha256')!=digest(s): raise ValueError('Design schema/scenario mismatch')
    if not isinstance(d.get('label'),str) or not isinstance(d.get('actions'),list): raise ValueError('Invalid design')
    state=DesignState(s,budget)
    for eid in d['actions']: state.step(eid)
    return state


def generate_workload(s,setup,c,seed):
    origins=sorted(p for p,v in setup['roles'].items() if v['kind']=='house')
    destinations=sorted(p for p,v in setup['roles'].items() if v['kind']=='destination')
    if not origins or not destinations or set(origins)&set(destinations): raise ValueError('Invalid construction roles')
    if set(origins+destinations)!={p['id'] for p in s['places']}: raise ValueError('Roles do not cover scenario')
    rng=random.Random(seed)
    trips=[{'id':f'trip-{i:06d}','origin':rng.choice(origins),'destination':rng.choice(destinations),'depart':rng.randrange(c['departure_window_s'])} for i in range(c['trip_count'])]
    trips.sort(key=lambda t:(t['depart'],t['id']))
    return {'schema_version':1,'generator':'uniform-house-to-destination-v1','scenario_sha256':digest(s),'setup_sha256':digest(setup),'seed':seed,'requests':trips,
            'note':'Independent sampled vehicle requests, not persistent game household cars; synthetic one-way journeys.'}


def binary(name,bin_dir=None):
    suffix='.exe' if sys.platform=='win32' else ''
    candidates=[]
    if bin_dir: candidates.append(Path(bin_dir)/(name+suffix))
    candidates.extend([Path(sys.executable).parent/(name+suffix),ROOT.parent/'.venv/Scripts'/(name+suffix)])
    try:
        import sumo
        candidates.append(Path(sumo.SUMO_HOME)/'bin'/(name+suffix))
    except ImportError: pass
    for p in candidates:
        if p.is_file(): return str(p.resolve())
    p=shutil.which(name)
    if p: return p
    raise FileNotFoundError(f'{name} not found. Install eclipse-sumo==1.28.0 in ../.venv or pass --bin-dir.')


def execute(args,directory,name):
    result=subprocess.run(list(map(str,args)),cwd=directory,capture_output=True,text=True,timeout=180)
    (directory/(name+'.stdout.txt')).write_text(result.stdout,encoding='utf-8')
    (directory/(name+'.stderr.txt')).write_text(result.stderr,encoding='utf-8')
    if result.returncode: raise RuntimeError(f'{name} failed with {result.returncode}: {result.stderr[-1800:]}')
    return result


def check_grid(s,g):
    from grid_projection import project
    if g['scenario_sha256']!=digest(s): raise ValueError('Grid/scenario mismatch')
    audit=project(s,width=g['width'],height=g['height'],margin=g['projection']['margin'],offset=g['projection']['offset'],paths_override=g['corridor_cells'])
    if audit['conflicts']: raise ValueError('Grid has topology conflicts')
    if audit['source_node_cells']!=g['source_node_cells']: raise ValueError('Grid node positions changed')
    for e in s['edges']:
        path=g['corridor_cells'][e['id']]
        if path[0]!=g['source_node_cells'][e['u']] or path[-1]!=g['source_node_cells'][e['v']]: raise ValueError('Corridor endpoints mismatch')
        if any(max(abs(a[0]-b[0]),abs(a[1]-b[1]))!=1 for a,b in zip(path,path[1:])): raise ValueError('Nonadjacent grid path')


def export_network(s,g,state,c,directory,bins):
    nodes=ET.Element('nodes'); edges=ET.Element('edges'); tazs=ET.Element('tazs')
    scale=c['cell_size_m']; roadnodes=state.nodes(); edge_lengths={}
    for nid in sorted(roadnodes):
        x,y=g['source_node_cells'][nid]
        ET.SubElement(nodes,'node',id=nid,x=str(x*scale),y=str(y*scale),type='priority')
    for eid in sorted(state.roads):
        e=state.edges[eid]; cells=g['corridor_cells'][eid]
        length=sum(math.dist(a,b)*scale for a,b in zip(cells,cells[1:]))
        edge_lengths[eid]=length
        for suffix,a,b,path in [('f',e['u'],e['v'],cells),('r',e['v'],e['u'],list(reversed(cells)))]:
            ET.SubElement(edges,'edge',id=f'{eid}_{suffix}',attrib={'from':a,'to':b,'priority':'2','numLanes':'1','speed':str(c['speed_mps']),'width':str(c['lane_width_m']),'length':str(length),'allow':'passenger','shape':' '.join(f'{x*scale},{y*scale}' for x,y in path)})
    endpoints={}
    for p in s['places']:
        pid=p['id']; access=sorted(set(p['nodes'])&roadnodes)
        endpoints[pid]={'access_node_ids':access,'source_edges':[],'sink_edges':[]}
        if not access: continue
        x,y=g['parcel_centroid_markers'][pid]; x*=scale; y*=scale
        # Separate source and sink: no incoming link to source, no outgoing link
        # from sink. Thus these parcel connectors cannot form transit shortcuts.
        ET.SubElement(nodes,'node',id='src_'+pid,x=str(x),y=str(y),type='priority')
        ET.SubElement(nodes,'node',id='dst_'+pid,x=str(x),y=str(y),type='priority')
        taz=ET.SubElement(tazs,'taz',id=pid)
        for nid in access:
            nx,ny=g['source_node_cells'][nid]; length=max(5.,math.dist([x,y],[nx*scale,ny*scale]))
            src=f'access_{pid}_{nid}_out'; dst=f'access_{pid}_{nid}_in'
            for edge_id,a,b in [(src,'src_'+pid,nid),(dst,nid,'dst_'+pid)]:
                ET.SubElement(edges,'edge',id=edge_id,attrib={'from':a,'to':b,'priority':'1','numLanes':'1','speed':str(c['connector_speed_mps']),'length':str(length),'allow':'passenger'})
            ET.SubElement(taz,'tazSource',id=src,weight='1'); ET.SubElement(taz,'tazSink',id=dst,weight='1')
            endpoints[pid]['source_edges'].append(src); endpoints[pid]['sink_edges'].append(dst)
    xml(directory/'network.nod.xml',nodes); xml(directory/'network.edg.xml',edges); xml(directory/'zones.taz.xml',tazs)
    args=[bins['netconvert'],'--node-files','network.nod.xml','--edge-files','network.edg.xml','--output-file','network.net.xml','--no-turnarounds','true','--junctions.join','false','--junctions.corner-detail','5','--default.junctions.radius',str(c['junction_radius_m']),'--no-warnings','false']
    conversion=execute(args,directory,'netconvert')
    network=ET.parse(directory/'network.net.xml').getroot()
    actual={e.attrib['id']:e for e in network.findall('edge') if e.get('function')!='internal'}
    expected={e.attrib['id'] for e in edges}
    if set(actual)!=expected: raise RuntimeError('Netconvert changed the external edge set')
    for edge in edges:
        got=actual[edge.attrib['id']]
        if got.get('from')!=edge.get('from') or got.get('to')!=edge.get('to'): raise RuntimeError('Netconvert changed endpoints')
    write(directory/'endpoint-map.json',endpoints)
    components={}; adjacency={nid:set() for nid in roadnodes}
    for eid in state.roads:
        e=state.edges[eid]; adjacency[e['u']].add(e['v']); adjacency[e['v']].add(e['u'])
    for start in sorted(roadnodes):
        if start in components: continue
        stack=[start]; group=len(set(components.values()))
        while stack:
            node=stack.pop()
            if node in components: continue
            components[node]=group; stack.extend(adjacency[node]-components.keys())
    return {'endpoints':endpoints,'components':components,'export_warnings':conversion.stderr.strip().splitlines(),'added_road_length_m':sum(edge_lengths[e] for e in state.actions),'total_road_length_m':sum(edge_lengths.values()),'command':list(map(str,args))}


def account(manifest,routing_failures,tripinfo_path,end_s):
    reqs={r['id']:r for r in manifest['requests']}
    if len(reqs)!=len(manifest['requests']) or not set(routing_failures)<=set(reqs): raise ValueError('Invalid IDs')
    observed={}
    triproot=ET.parse(tripinfo_path).getroot()
    if triproot.tag!='tripinfos': raise ValueError('Expected SUMO tripinfos document')
    for trip in triproot.findall('tripinfo'):
        tid=trip.get('id')
        if tid not in reqs or tid in routing_failures or tid in observed: raise ValueError('Unexpected trip record '+str(tid))
        observed[tid]=trip.attrib
    if set(reqs)!=set(observed)|set(routing_failures): raise ValueError('Missing routed-trip accounting')
    outcomes=[]
    for r in manifest['requests']:
        row={**r,'status':'unroutable','failure_reason':routing_failures.get(r['id']),'duration_s':None,'departure_delay_s':None,'waiting_s':None,'time_loss_s':None,'arrival_s':None,'requested_to_arrival_s':None}
        if r['id'] in observed:
            t=observed[r['id']]; dep=float(t['depart']); arrival=float(t['arrival'])
            removed=t.get('vaporized','') not in ('','false','0','end')
            if removed: row['status']='removed'
            elif dep<0: row['status']='never_departed'
            elif arrival<0: row['status']='unfinished'
            else: row['status']='completed'
            row['departure_delay_s']=max(0.,(end_s if dep<0 else dep)-r['depart'])
            if dep>=0:
                row['waiting_s']=float(t.get('waitingTime',0)); row['time_loss_s']=float(t.get('timeLoss',0))
            if row['status']=='completed':
                row.update(duration_s=float(t['duration']),arrival_s=arrival,requested_to_arrival_s=arrival-r['depart'])
        outcomes.append(row)
    return outcomes


def summarize(rows):
    counts={s:0 for s in ['completed','unroutable','never_departed','unfinished','removed']}; counts.update(Counter(r['status'] for r in rows))
    complete=[r for r in rows if r['status']=='completed']
    def avg(key,items):
        values=[r[key] for r in items if r[key] is not None]
        return statistics.mean(values) if values else None
    return {'requested':len(rows),'counts':counts,'completion_fraction':len(complete)/len(rows),
            'mean_completed_duration_s':avg('duration_s',complete),
            'mean_completed_requested_to_arrival_s':avg('requested_to_arrival_s',complete),
            'mean_completed_waiting_s':avg('waiting_s',complete),
            'mean_departure_delay_routable_s':avg('departure_delay_s',[r for r in rows if r['status']!='unroutable'])}


def simulate(manifest,network,c,directory,bins,seed):
    # Network files are in the parent design directory. Output lives under seed/.
    endpoints=network['endpoints']; trips=ET.Element('routes'); failures={}
    ET.SubElement(trips,'vType',id='car',vClass='passenger',length=str(c['vehicle_length_m']),minGap=str(c['vehicle_min_gap_m']),maxSpeed=str(c['speed_mps']),sigma='0',tau=str(c['vehicle_tau_s']),speedFactor='1',speedDev='0')
    for r in manifest['requests']:
        if not endpoints[r['origin']]['source_edges'] or not endpoints[r['destination']]['sink_edges']:
            failures[r['id']]='no_road_access_at_origin_or_destination'; continue
        ET.SubElement(trips,'trip',id=r['id'],depart=str(r['depart']),fromTaz=r['origin'],toTaz=r['destination'],type='car',departLane='best',departPos='base',departSpeed='0',arrivalPos='max')
    xml(directory/'requests.trips.xml',trips)
    route_args=[bins['duarouter'],'--net-file','../network.net.xml','--route-files','requests.trips.xml','--taz-files','../zones.taz.xml','--with-taz','true','--output-file','routes.rou.xml','--ignore-errors','true','--routing-algorithm','dijkstra','--seed',str(seed),'--no-step-log','true']
    if trips.findall('trip'):
        execute(route_args,directory,'duarouter')
    else:
        xml(directory/'routes.rou.xml',ET.Element('routes'))
        (directory/'duarouter.stdout.txt').write_text('Skipped: all requests lack endpoint access.\\n',encoding='utf-8')
    routes=ET.parse(directory/'routes.rou.xml').getroot(); routed={}
    reqs={r['id']:r for r in manifest['requests']}
    for vehicle in routes.findall('vehicle'):
        tid=vehicle.get('id')
        if tid not in reqs or tid in routed or tid in failures: raise RuntimeError('Unexpected routed ID')
        r=reqs[tid]; route=vehicle.find('route')
        if route is None: raise RuntimeError('Missing explicit route')
        path=route.get('edges','').split()
        if not path or path[0] not in endpoints[r['origin']]['source_edges'] or path[-1] not in endpoints[r['destination']]['sink_edges']: raise RuntimeError('Router changed requested endpoints')
        if abs(float(vehicle.get('depart'))-r['depart'])>1e-6: raise RuntimeError('Router changed requested departure')
        if any(e.startswith('access_') for e in path[1:-1]): raise RuntimeError('Route uses a parcel as a transit shortcut')
        routed[tid]=path
    for tid in reqs.keys()-routed.keys()-failures.keys():
        r=reqs[tid]
        a={network['components'][n] for n in endpoints[r['origin']]['access_node_ids']}
        b={network['components'][n] for n in endpoints[r['destination']]['access_node_ids']}
        if a & b: raise RuntimeError('SUMO routing lost a source-graph connection: '+tid)
        failures[tid]='disconnected_road_components'
    write(directory/'routing-failures.json',failures)
    sumo_args=[bins['sumo'],'--net-file','../network.net.xml','--route-files','routes.rou.xml','--begin','0','--end',str(c['end_s']),'--step-length',str(c['step_length_s']),'--seed',str(seed),'--tripinfo-output','tripinfo.xml','--tripinfo-output.write-unfinished','true','--tripinfo-output.write-undeparted','true','--time-to-teleport','-1','--max-depart-delay','-1','--collision.action','warn','--no-step-log','true','--duration-log.disable','true','--statistic-output','statistics.xml']
    execute(sumo_args,directory,'sumo')
    rows=account(manifest,failures,directory/'tripinfo.xml',c['end_s'])
    write(directory/'outcomes.json',rows)
    with (directory/'outcomes.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    stats=ET.parse(directory/'statistics.xml').getroot()
    safety=stats.find('safety'); teleports=stats.find('teleports')
    diagnostics={'safety':safety.attrib if safety is not None else {},'teleports':teleports.attrib if teleports is not None else {}}
    for tag in [safety,teleports]:
        if tag is not None and any(float(v)>0 for k,v in tag.attrib.items() if k in ['collisions','total','jam','yield','wrongLane']): raise RuntimeError('Collision/teleport invalidates comparison; inspect statistics.xml')
    return {'summary':summarize(rows),'rows':rows,'diagnostics':diagnostics,'commands':[list(map(str,route_args)),list(map(str,sumo_args))]}


def pair(reference,candidate):
    a={r['id']:r for r in reference}; b={r['id']:r for r in candidate}
    if set(a)!=set(b): raise ValueError('Different request sets')
    for tid in a:
        if any(a[tid][k]!=b[tid][k] for k in ['origin','destination','depart']): raise ValueError('Different paired demand')
    common=[tid for tid in a if a[tid]['status']==b[tid]['status']=='completed']
    sa,sb=summarize(reference),summarize(candidate)
    return {'candidate_minus_reference_completed':sb['counts']['completed']-sa['counts']['completed'],
            'candidate_minus_reference_completion_fraction':sb['completion_fraction']-sa['completion_fraction'],
            'common_completed_count':len(common),
            'mean_paired_duration_difference_s':statistics.mean(b[i]['duration_s']-a[i]['duration_s'] for i in common) if common else None,
            'mean_paired_requested_to_arrival_difference_s':statistics.mean(b[i]['requested_to_arrival_s']-a[i]['requested_to_arrival_s'] for i in common) if common else None,
            'note':'Time differences condition on completion in BOTH designs; always interpret alongside completion counts.'}


def prepare():
    s=read(FIRST/'data/harare.json'); g=read(FIRST/'data/grid-draft.json'); setup=read(FIRST/'data/construction-setup.json')
    reference=read(FIRST/'examples/heuristic-seed0.json'); candidate=read(FIRST/'examples/heuristic-seed1.json')
    reference['label']='Published Brelsford probabilistic reblocking, seed 0; local reference run'
    reference['method_provenance']={'topology_revision':'2232a3da3cfa7bbe3f4e5eb48049baac6e67f662','alpha':8,'wholepath':True,'stop':'universal parcel access','not_exact_KDD_HS_MC_reproduction':True}
    cost=sum({e['id']:e['cost'] for e in s['edges']}[a] for a in reference['actions'])
    c={'schema_version':1,'scenario_sha256':digest(s),'reference_sha256':digest(reference),'construction_setup_sha256':digest(setup),'construction_seed':setup['seed'],
       'budget_rule':'source cost of preselected published heuristic seed 0, full-access stopping rule','budget_source_cost':cost,
       'evaluation_seeds':[1001,1002,1003],'trip_count':120,'departure_window_s':600,'end_s':1200,
       'cell_size_m':10.,'junction_radius_m':5.,'speed_mps':8.33,'connector_speed_mps':3.,'lane_width_m':3.,'step_length_s':0.5,
       'vehicle_length_m':4.5,'vehicle_min_gap_m':2.5,'vehicle_tau_s':1.,
       'scale_status':'synthetic physical scale; not calibrated to Harare traffic or dimensions',
       'endpoint_access':'same parcel, any built boundary-road node; directed source/sink connectors forbid parcel transit'}
    validate_config(c); check_grid(s,g)
    for name,value in [('scenario',s),('grid',g),('construction-setup',setup),('protocol',c),('reference-design',reference)]: write(ROOT/'data'/(name+'.json'),value)
    candidate['label']='Engineering candidate: published heuristic seed 1; NOT GP'
    write(ROOT/'examples/candidate-design.json',candidate)
    write(ROOT/'examples/empty-design.json',{'schema_version':1,'scenario_sha256':digest(s),'label':'Empty added-road fixture; intentional inaccessible endpoints','actions':[]})
    write(ROOT/'examples/initial-state.json',DesignState(s,cost).observe())
    print('Prepared frozen protocol and baseline; no evaluation workload generated yet.')


def run(candidate_path,out,bin_dir=None,reference_path=None,config_path=None):
    s=read(ROOT/'data/scenario.json'); g=read(ROOT/'data/grid.json'); setup=read(ROOT/'data/construction-setup.json')
    c=read(config_path or ROOT/'data/protocol.json'); validate_config(c); check_grid(s,g)
    reference=read(reference_path or ROOT/'data/reference-design.json'); candidate=read(candidate_path)
    if c['scenario_sha256']!=digest(s) or setup['scenario_sha256']!=digest(s): raise ValueError('Protocol/setup scenario mismatch')
    if c['construction_setup_sha256']!=digest(setup) or c['construction_seed']!=setup['seed']: raise ValueError('Frozen construction setup mismatch')
    if c['reference_sha256']!=digest(reference): raise ValueError('Frozen baseline identity mismatch')
    states={name:validate_design(s,d,c['budget_source_cost']) for name,d in [('reference',reference),('candidate',candidate)]}
    out=out.resolve(); out.mkdir(parents=True,exist_ok=False)
    bins={name:binary(name,bin_dir) for name in ['netconvert','duarouter','sumo']}
    versions={k:subprocess.check_output([v,'--version'],text=True).splitlines()[0] for k,v in bins.items()}
    write(out/'protocol.json',c); write(out/'reference-design.json',reference); write(out/'candidate-design.json',candidate)
    write(out/'scenario.json',s); write(out/'construction-setup.json',setup); write(out/'grid.json',g)
    result={'schema_version':1,'status':'running','protocol_sha256':digest(c),'scenario_sha256':digest(s),
            'reference_design_sha256':digest(reference),'candidate_design_sha256':digest(candidate),'versions':versions,
            'research_ready':False,'readiness_note':'Engineering pipeline verified; GP/native-game adapter and junction geometry review pending.',
            'implementation_sha256':{str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),FIRST/'experiment.py',FIRST/'grid_projection.py']},
            'labels':{'reference':reference['label'],'candidate':candidate['label']},'construction':{},'seeds':[]}
    write(out/'comparison.json',result)
    try:
        networks={}
        for name,state in states.items():
            folder=out/name; folder.mkdir()
            networks[name]=export_network(s,g,state,c,folder,bins)
            metric=Episode(s); metric.roads=state.roads; metric.actions=state.actions; metric.nr=state.nr
            result['construction'][name]={'source_cost':state.cost,'budget_cap':c['budget_source_cost'],'added_segments':len(state.actions),
                'added_road_length_m':networks[name]['added_road_length_m'],'export_warnings':networks[name]['export_warnings'],'source_graph_metrics':{k:v for k,v in metric.metrics().items() if k!='budget_complete'}}
        # Designs are frozen above before the held-out requests are sampled.
        for seed in c['evaluation_seeds']:
            manifest=generate_workload(s,setup,c,seed); write(out/f'workload-{seed}.json',manifest)
            sims={}
            for name in ['reference','candidate']:
                folder=out/name/f'seed-{seed}'; folder.mkdir(); write(folder/'workload.json',manifest)
                sims[name]=simulate(manifest,networks[name],c,folder,bins,seed)
            result['seeds'].append({'seed':seed,'workload_sha256':digest(manifest),'reference':sims['reference']['summary'],'candidate':sims['candidate']['summary'],
                'paired':pair(sims['reference']['rows'],sims['candidate']['rows']),
                'diagnostics':{name:sims[name]['diagnostics'] for name in sims}})
        values=[r['paired']['candidate_minus_reference_completed'] for r in result['seeds']]
        result['across_seeds']={'mean_completion_count_difference':statistics.mean(values),'sd_completion_count_difference':statistics.stdev(values) if len(values)>1 else None,'seed_count':len(values)}
        result['status']='complete'; write(out/'comparison.json',result)
        report(result,out/'REPORT.md')
    except Exception as exc:
        result['status']='failed'; result['error']=str(exc); write(out/'comparison.json',result); raise
    snapshot=ROOT/'results'/out.name
    snapshot.mkdir(parents=True,exist_ok=False)
    for filename in ['comparison.json','REPORT.md','protocol.json','reference-design.json','candidate-design.json']:
        shutil.copy2(out/filename,snapshot/filename)
    for seed in c['evaluation_seeds']:
        shutil.copy2(out/f'workload-{seed}.json',snapshot/f'workload-{seed}.json')
        for name in ['reference','candidate']:
            shutil.copy2(out/name/f'seed-{seed}'/'outcomes.json',snapshot/f'{name}-outcomes-{seed}.json')
    print(json.dumps({'status':result['status'],'output':str(out),'paired':[x['paired'] for x in result['seeds']]},indent=2))
    return result


def report(result,path):
    lines=['# Second generalization: paired traffic comparison','',f"Reference: {result['labels']['reference']}",f"Candidate: {result['labels']['candidate']}",'',
       'Synthetic traffic and physical scale. These runs do not reproduce KDD DRL-GNN or establish real-world traffic performance.','',
       '| Seed | Reference completed | Candidate completed | Difference | Common completed trips | Paired duration difference (s) |',
       '|---|---:|---:|---:|---:|---:|']
    for r in result['seeds']:
        lines.append(f"| {r['seed']} | {r['reference']['counts']['completed']} / {r['reference']['requested']} | {r['candidate']['counts']['completed']} / {r['candidate']['requested']} | {r['paired']['candidate_minus_reference_completed']} | {r['paired']['common_completed_count']} | {r['paired']['mean_paired_duration_difference_s']} |")
    warnings=sum(len(v.get('export_warnings',[])) for v in result['construction'].values())
    if warnings: lines += ['',f'Network exporter reported {warnings} junction-geometry warnings; review export_warnings in comparison.json before research use. No collision or teleport was observed in accepted runs.']
    lines+=['','Differences are candidate minus reference. Time differences include only journeys completed by both designs; completion and failure counts must accompany them.','',
            'Full failure counts, delays, construction cost, diagnostics, binary versions and input hashes are recorded in comparison.json. All individual requests are accounted for in each seed directory.',
            'A synthetic heuristic candidate is an engineering fixture, not a GP result.']
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('prepare')
    p=sub.add_parser('run'); p.add_argument('--candidate',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--bin-dir',type=Path); p.add_argument('--config',type=Path)
    p=sub.add_parser('observe'); p.add_argument('--design',type=Path); p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare': prepare()
    elif args.command=='run': run(args.candidate,args.output,args.bin_dir,config_path=args.config)
    else:
        s=read(ROOT/'data/scenario.json'); c=read(ROOT/'data/protocol.json')
        state=validate_design(s,read(args.design),c['budget_source_cost']) if args.design else DesignState(s,c['budget_source_cost'])
        write(args.output,state.observe())
if __name__=='__main__': main()






