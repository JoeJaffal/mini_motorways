import pathlib,json
root=pathlib.Path(__file__).resolve().parents[1]/'measurements'
refs=json.loads((root/'reference-checkpoints.json').read_text());results={}
def edges(a):return {tuple(sorted((tuple(e[:2]),tuple(e[2:])))) for e in a}
for name in ['old-checkpoints.json','reviewed-checkpoints.json']:
 rows=json.loads((root/name).read_text(encoding='utf-8-sig'));checks=[]
 for ref,got in zip(refs,rows):
  checks.append(dict(video=ref['video'],edges=edges(ref['edges'])==edges(got['edges']),roadNodes=set(map(tuple,ref['roadNodes']))==set(map(tuple,got['roadNodes'])),houseDirections=set(map(tuple,ref['houseDirections']))==set(map(tuple,got['houseDirections'])),stock=ref['roadStock']==got['roadStock']))
 results[name]=checks
print(json.dumps(results,indent=2));assert all(all(v for k,v in row.items() if k!='video') for row in results['reviewed-checkpoints.json'])
