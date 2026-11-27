"""Package real mesh triangles/textures for the mod's D3D11 room viewer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
from pathlib import Path
from PIL import Image, ImageSequence
import struct, math, json
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'research'/'room-export'
OUT=ROOT/'build'/'room-view'
OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((SRC/'manifest.json').read_text())
animation=json.loads((SRC/'animation.json').read_text())
positions=[];uvs=[];groups={};material=None;obj=None
for line in (SRC/'divaroom.obj').read_text().splitlines():
    fields=line.split()
    if not fields:continue
    if fields[0]=='v':positions.append(tuple(map(float,fields[1:])))
    elif fields[0]=='vt':uvs.append(tuple(map(float,fields[1:])))
    elif fields[0]=='o':obj=fields[1].removeprefix('DR_ROOM_')
    elif fields[0]=='usemtl':material=fields[1];groups.setdefault((obj,material),[])
    elif fields[0]=='f':
        assert len(fields)==4
        indices=[tuple(int(x)-1 for x in f.split('/')) for f in fields[1:]]
        p=[positions[i[0]] for i in indices]
        a=[p[1][i]-p[0][i] for i in range(3)];b=[p[2][i]-p[0][i] for i in range(3)]
        n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        length=math.sqrt(sum(x*x for x in n))
        n=[x/length for x in n] if length>1e-12 else [0,1,0]
        for vi,ti in indices:groups[(obj,material)].append((*positions[vi],*n,uvs[ti][0],1-uvs[ti][1]))
leds={m for name in ['324','459','257','138','343','292'] for m in manifest['material_textures'][name]}
camera=manifest['cameras']['DR_Overview']
def native(v):return (v[0]*.1,v[2]*.1,-v[1]*.1)
data=bytearray(b'DRROOM2\0')
data+=struct.pack('<I7f',len(groups),*native(camera['position']),*native(camera['interest']),camera['horizontal_fov_radians'])
vertices=0
tv=manifest['material_textures']['131'][-1]
gif=Image.open(MOD_DIR/'3dmodels/divaroom/textures/screen.gif')
movie=[(f.info.get('duration',100),f.convert('RGBA').copy()) for f in ImageSequence.Iterator(gif)]
for (obj,name),vs in groups.items():
    im=Image.open(SRC/(name+'.png')).convert('RGBA')
    assert im.width<=4096 and im.height<=4096 and len(vs)%3==0
    flags=2 if obj=='292' else (1 if name in leds else (4 if name==tv else 0))
    samples=animation['samples'].get(obj,[[0]*6])
    frames=movie if name==tv else [(12000,im)]
    data+=struct.pack('<6I',len(vs),frames[0][1].width,frames[0][1].height,flags,len(samples),len(frames))
    data+=b''.join(struct.pack('<8f',*v) for v in vs)
    data+=b''.join(struct.pack('<6f',*s) for s in samples)
    for duration,frame in frames:data+=struct.pack('<I',duration)+frame.tobytes()
    vertices+=len(vs)
(OUT/'room.mesh').write_bytes(data)
report={'groups':len(groups),'triangles':vertices//3,'bytes':len(data),'camera':camera,'animated_objects':list(animation['samples']),'tv_frames':len(movie),'tv_duration_ms':sum(d for d,f in movie),'source':animation['source']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
