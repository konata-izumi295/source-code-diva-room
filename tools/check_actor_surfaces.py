import struct,collections
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'build/room-view/room/miku.actor'
seen={};duplicates=collections.Counter()
with p.open('rb') as f:
    f.read(8);bones,groups,clips=struct.unpack('<3I',f.read(12))
    for group in range(groups):
        n,w,h=struct.unpack('<3I',f.read(12));data=f.read(n*64)
        for start in range(0,n,3):
            triangle=tuple(sorted(tuple(round(v,5) for v in struct.unpack_from('<3f',data,(start+j)*64)) for j in range(3)))
            if triangle in seen:duplicates[(seen[triangle],group)]+=1
            else:seen[triangle]=group
        f.seek(w*h*4,1)
print('Overlapping triangle groups:',duplicates)
