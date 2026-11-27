"""Check the exported phone's real vertices, not Blender's imported bound_box."""
from pathlib import Path
import struct
import numpy as np
p=Path(__file__).resolve().parents[1]/'build/room-view/room/miku.actor'
points=[]
with p.open('rb') as f:
    assert f.read(8)==b'DRMIKU3\0'
    bones,groups,clips=struct.unpack('<3I',f.read(12))
    f.seek(bones*72,1)
    for _ in range(groups):
        count,w,h=struct.unpack('<3I',f.read(12))
        raw=f.read(count*64)
        ids=np.frombuffer(raw,dtype='<u4').reshape(count,16)[:,8]
        vertices=np.frombuffer(raw,dtype='<f4').reshape(count,16)[:,:3]
        points.extend(vertices[ids==bones-1])
        f.seek(w*h*4,1)
span=np.ptp(np.asarray(points),axis=0)
assert span[1]<span[0]*.2 and span[2]>span[0]*1.5,span
print('PASS actual phone geometry: width / thickness / height:',span)
