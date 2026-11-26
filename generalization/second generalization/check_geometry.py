from pipeline import *
s=read(ROOT/'data/scenario.json'); g=read(ROOT/'data/grid.json'); c=read(ROOT/'data/protocol.json'); d=read(ROOT/'data/reference-design.json')
bins={n:binary(n) for n in ['netconvert']}; result=[]
for scale,radius in [(15.,8.),(20.,10.),(30.,10.)]:
    cfg=dict(c,cell_size_m=scale,junction_radius_m=radius)
    folder=ROOT/'runs'/f'geometry-{scale:g}-{radius:g}'; folder.mkdir()
    net=export_network(s,g,validate_design(s,d,c['budget_source_cost']),cfg,folder,bins)
    result.append({'cell_size_m':scale,'junction_radius_m':radius,'warnings':net['export_warnings']})
write(ROOT/'results/geometry-checks.json',result)
print(json.dumps(result,indent=2))
