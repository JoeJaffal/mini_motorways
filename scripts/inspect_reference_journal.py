"""Read a supported original-game journal envelope without loading or modifying it.

Only gameplay metadata and object-table counts are exported. Device strings are
consumed but omitted. This does not decode the simulation object graph or certify
serializer compatibility. Keep raw journals outside the repository.
"""
import argparse,hashlib,json,struct
from pathlib import Path

class Reader:
 def __init__(self,data):self.data=data;self.offset=0
 def read(self,n):
  if n<0 or self.offset+n>len(self.data):raise ValueError('Truncated journal')
  result=self.data[self.offset:self.offset+n];self.offset+=n;return result
 def integer(self):return struct.unpack('<i',self.read(4))[0]
 def long(self):return struct.unpack('<q',self.read(8))[0]
 def string(self):
  length=0
  for shift in range(0,35,7):
   byte=self.read(1)[0];length|=(byte&127)<<shift
   if byte<128:break
  else:raise ValueError('Invalid string length')
  if length>65536:raise ValueError('Unexpected journal string size')
  return self.read(length).decode('utf-8')

def envelope(reader):
 start=reader.offset;size=reader.long();scope_hash=reader.integer();version=reader.integer();count=reader.integer()
 if size<20 or start+size>len(reader.data) or not 1<=count<=10000:raise ValueError('Unsupported journal envelope')
 table=[]
 for _ in range(count):
  type_id=reader.integer();serializer_hash=reader.integer();objects=reader.integer()
  if objects<0 or objects>1000000:raise ValueError('Invalid object count')
  table.append(dict(typeId=type_id,serializerHash=serializer_hash,objects=objects))
 if reader.offset>start+size:raise ValueError('Object table exceeds envelope')
 return dict(start=start,size=size,scopeHash=scope_hash,rootVersion=version,types=table,payloadOffset=reader.offset)

def inspect(path):
 data=Path(path).read_bytes();r=Reader(data);header=envelope(r)
 if header['rootVersion']!=1 or len(header['types'])!=1 or header['types'][0]['objects']!=1:
  raise ValueError('Unsupported journal header version or shape')
 if (header['types'][0]['typeId'],header['types'][0]['serializerHash'])!=(2131895424,-1272368233):
  raise ValueError('Unsupported journal header schema')
 motive=r.integer();r.string();r.string() # Omit device model and device name.
 r.long() # Omit creation timestamp.
 simulation_hash=r.integer();city=r.string();mode=r.integer();trips=r.integer();time_raw=r.long()
 challenge=r.integer();r.integer();r.integer()
 if r.offset!=header['start']+header['size']:raise ValueError('Header layout differs from supported build')
 if city.lower().replace(' ','') not in {'losangeles','beijing','tokyo','daressalaam','london'} or not 0<=trips<=10000000 or time_raw<0:
  raise ValueError('Unexpected city, score or elapsed time')
 simulation=envelope(r)
 if simulation['scopeHash']!=simulation_hash:raise ValueError('Header and simulation serializer hashes differ')
 if simulation['start']+simulation['size']!=len(data):raise ValueError('Unexpected trailing journal data')
 return dict(format='Mini Motorways factory journal envelope; supported header v1',journalSha256=hashlib.sha256(data).hexdigest(),bytes=len(data),city=city,modeValue=mode,motiveValue=motive,trips=trips,elapsedRaw=time_raw,elapsedSeconds=time_raw/(1<<32),challengeValue=challenge,gameSerializerHash=simulation_hash,header=header,simulation=simulation,simulationObjects=sum(t['objects'] for t in simulation['types']),simulationGraphDecoded=False,exactReplicaValidated=False)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('journal');p.add_argument('--output');a=p.parse_args()
 result=inspect(a.journal);text=json.dumps(result,indent=2)
 if a.output:Path(a.output).write_text(text+'\n',encoding='utf-8')
 else:print(text)
