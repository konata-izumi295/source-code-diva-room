"""Read evaluated Blender animation without changing or saving the source file."""
import bpy, json
from pathlib import Path
scene=bpy.context.scene
out=Path(__file__).resolve().parents[1]/'research/room-export/animation.json'
names=['303','315','331','354','360','368','292','324','459','257','138','343']
scene.frame_set(1)
origins={n:bpy.data.objects[n].matrix_world.translation.copy() for n in names}
samples={n:[] for n in names}
for frame in range(1,362):
    scene.frame_set(frame)
    for name in names:
        obj=bpy.data.objects[name]
        delta=obj.matrix_world.translation-origins[name]
        uv=(0,0);strength=0
        nodes=obj.active_material.node_tree.nodes
        if name=='292':
            uv=nodes['DIVA ROOM | Stripes downward'].inputs[1].default_value[:2]
            strength=2.2
        elif name in ['324','459','257','138','343']:
            strength=nodes['DIVA ROOM | Soft LED breathing'].outputs[0].default_value
        # D3D image coordinates flip Blender's vertical UV coordinate.
        samples[name].append([delta.x*.1,delta.z*.1,-delta.y*.1,uv[0],-uv[1],strength])
for name in names:
    a,b=samples[name][0],samples[name][-1]
    assert max(abs(a[i]-b[i]) for i in [0,1,2,5])<1e-4,name
assert all(max(s[1] for s in samples[n])-min(s[1] for s in samples[n])>.001 for n in names[:6])
out.write_text(json.dumps({'source':bpy.data.filepath,'fps':30,'period':360,'samples':samples},indent=2))
print('Sampled original Blender transforms, LED strengths and stripe UVs: 361 loop samples')
