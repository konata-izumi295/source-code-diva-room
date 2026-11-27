"""Export original meshes and authored skin palettes for the room renderer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
import bpy,struct,math,json
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
root=Path(__file__).resolve().parents[1]/'research/character'
out=Path(__file__).resolve().parents[1]/'build/room-view/room/miku.actor'
out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];bones=list(rig.data.bones);ids={b.name:i for i,b in enumerate(bones)}
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
phonepath=(MOD_DIR / '3dmodels/cellphone/mikucell.blend')
with bpy.data.libraries.load(str(phonepath),link=False) as (src,dst):dst.objects=src.objects
phones=[o for o in dst.objects if o and o.type=='MESH']
for o in phones:bpy.context.collection.objects.link(o)
bpy.context.view_layer.update()

def pixels(mat):
    image=None
    if mat and mat.use_nodes:
        bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if bs and bs.inputs['Base Color'].is_linked:
            n=bs.inputs['Base Color'].links[0].from_node
            if n.type=='TEX_IMAGE':image=n.image
        if image is None:
            image=next((n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None)
    if image:
        if not image.has_data:
            candidate=phonepath.parent/'textures'/Path(bpy.path.abspath(image.filepath)).name
            if candidate.exists():image.filepath=str(candidate);image.reload()
        w,h=image.size
        if w and h:
            data=np.empty(w*h*4,dtype=np.float32);image.pixels.foreach_get(data);data=data.reshape(h,w,4)[::-1].copy()
            rgb=np.clip(data[:,:,:3],0,1)
            data[:,:,:3]=np.where(rgb<=.0031308,rgb*12.92,1.055*np.power(rgb,1/2.4)-.055)
            return w,h,(np.clip(data,0,1)*255+.5).astype(np.uint8).tobytes()
    color=list(mat.diffuse_color) if mat else [1,1,1,1]
    return 1,1,bytes(round(max(0,min(1,c))*255) for c in color)

groups=[]
for obj in meshes+phones:
    me=obj.data;me.calc_loop_triangles();phone=obj in phones
    # Actual vertices (not the stale imported bounding box): screen is +Z,
    # top is +Y. Normalize to the attachment's +Y screen / +Z top frame.
    phone_axes=Matrix(((-1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
    transform=phone_axes@Matrix.Scale(.05,4)@obj.matrix_world if phone else Matrix.Identity(4)
    for material_index,mat in enumerate(me.materials):
        verts=bytearray()
        for tri in me.loop_triangles:
            if tri.material_index!=material_index:continue
            for index in tri.loops:
                loop=me.loops[index];v=me.vertices[loop.vertex_index]
                p=transform@v.co;n=transform.to_3x3()@v.normal;n.normalize()
                uv=me.uv_layers.active.data[index].uv if me.uv_layers.active else (0,0)
                weights=[(len(bones),1)] if phone else sorted([(ids[obj.vertex_groups[g.group].name],g.weight) for g in v.groups if obj.vertex_groups[g.group].name in ids and g.weight>0],key=lambda x:-x[1])[:4]
                if not weights:raise ValueError('Unweighted vertex '+obj.name)
                total=sum(w for _,w in weights);weights=[(i,w/total) for i,w in weights]
                weights+=( [(0,0)]*(4-len(weights)) )
                verts+=struct.pack('<8f4I4f',*p,*n,uv[0],1-uv[1],*[i for i,w in weights],*[w for i,w in weights])
        if verts:groups.append((verts,*pixels(mat)))

clips=json.loads((root/'actions.json').read_text())['clips']
contacts=[]
staging=out.with_suffix('.actor.tmp')
with staging.open('wb') as f:
    f.write(b'DRMIKU3\0');f.write(struct.pack('<3I',len(bones)+1,len(groups),len(clips)))
    for b in bones:
        kind=2 if b.name in [f'j_necktie_{i:03d}_wj' for i in range(1,5)] else 1 if b.name in [f'j_tail_{side}_{i:03d}_wj' for side in ('l','r') for i in (1,4,8,12)] else 0
        f.write(struct.pack('<iI',ids[b.parent.name] if b.parent else -1,kind))
        inverse=b.matrix_local.inverted();f.write(struct.pack('<16f',*[inverse[col][row] for row in range(4) for col in range(4)]))
    f.write(struct.pack('<iI16f',-1,0,*[float(i==j) for i in range(4) for j in range(4)]))
    for vertices,w,h,rgba in groups:
        f.write(struct.pack('<3I',len(vertices)//64,w,h));f.write(vertices);f.write(rgba)
    for name,seconds in clips:
        rig.animation_data.action=bpy.data.actions['DR_'+name]
        f.write(name.encode().ljust(32,b'\0'));f.write(struct.pack('<If',seconds*30+1,seconds))
        for frame in range(seconds*30+1):
            bpy.context.scene.frame_set(frame+1);bpy.context.view_layer.update()
            matrices=[(rig.pose.bones[b.parent.name].matrix.inverted()@rig.pose.bones[b.name].matrix) if b.parent else rig.pose.bones[b.name].matrix.copy() for b in bones]
            wrist=rig.pose.bones['kl_te_l_wj'].head
            long=(rig.pose.bones['nl_naka_l_wj'].head-wrist).normalized()
            width=(rig.pose.bones['nl_hito_l_wj'].head-rig.pose.bones['nl_ko_l_wj'].head).normalized()
            normal=long.cross(width).normalized();width=normal.cross(long).normalized()
            # Canonical geometry: screen +Y, top +Z; retain the established grip position.
            # One palm attachment for every action; no independent phone trajectory.
            phone=Matrix((width,normal,long)).transposed().to_4x4()
            phone.translation=wrist+long*.055+normal*.012
            if name in ('place_phone','pick_phone') and frame==54:
                error=(phone.translation-Vector((0,.66363636,.45))).length
                contacts.append(dict(clip=name,error=error,position=list(phone.translation)))
                if error>.005:raise ValueError(f'Phone does not reach table at handoff: {name} {error}')
            matrices.append(phone)
            for m in matrices:
                values=[m[col][row] for row in range(4) for col in range(4)]
                if not all(math.isfinite(x) for x in values):raise ValueError('Non-finite pose')
                f.write(struct.pack('<16f',*values))
staging.replace(out)
print('Exported',out,'bones',len(bones)+1,'groups',len(groups),'bytes',out.stat().st_size)
(root/'phone-contact-validation.json').write_text(json.dumps(contacts,indent=2))
