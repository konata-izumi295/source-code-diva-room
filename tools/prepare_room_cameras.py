"""Prepare editable camera rigs and a static mesh interchange; preserve source meshes."""
import bpy, json, hashlib, struct, math, shutil
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research'/'room-export'
OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
scene.frame_set(1)
def fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
    for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
    for uv in o.data.uv_layers:
        for v in uv.data:h.update(struct.pack('<2f',*v.uv))
    return h.hexdigest()
meshes=sorted([o for o in scene.objects if o.type=='MESH'],key=lambda o:o.name)
before={o.name:fingerprint(o) for o in meshes}
collection=bpy.data.collections.get('DIVA ROOM Cameras') or bpy.data.collections.new('DIVA ROOM Cameras')
if collection.name not in scene.collection.children:scene.collection.children.link(collection)
def empty(name,loc):
    o=bpy.data.objects.get(name)
    if o is None:
        o=bpy.data.objects.new(name,None);collection.objects.link(o)
    o.location=loc;o.empty_display_size=.5
    return o
target=empty('DR_CharacterTarget',(0,7,5.5))
target['purpose']='Preview target only. Runtime must bind to the selected character chest/head.'
presets=[('Overview',(0,-12,9),(-1,15,6),24),
         ('Communication',(0,-3,5.8),(0,7,5.5),38),
         ('Activity',(-7,-8,10),(0,12,4.5),26)]
manifest={'units':'native = Blender world * 0.1; axes X,Z,-Y',
          'runtime_follow_implemented':False,'cameras':{},'geometry_before':before}
for name,loc,look,lens in presets:
    name='DR_'+name
    cam=bpy.data.objects.get(name)
    if cam is None:
        cam=bpy.data.objects.new(name,bpy.data.cameras.new(name));collection.objects.link(cam)
    cam.location=loc;cam.rotation_euler=(Vector(look)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens;cam.data.sensor_width=36;cam.data.clip_start=.1;cam.data.clip_end=200
    cam['purpose']='Editable framing preset; activity locations must match final character blocking.'
    if name=='DR_Communication':
        bpy.context.view_layer.update()
        world=cam.matrix_world.copy();cam.parent=target;cam.matrix_world=world
        con=cam.constraints.get('DR_LookAt') or cam.constraints.new('TRACK_TO')
        con.name='DR_LookAt';con.target=target;con.track_axis='TRACK_NEGATIVE_Z';con.up_axis='UP_Y'
    manifest['cameras'][name]={'position':list(loc),'interest':list(look),'lens_mm':lens,
                            'horizontal_fov_radians':2*math.atan(36/(2*lens))}
scene.camera=bpy.data.objects['DR_Overview']
bpy.context.view_layer.update()
assert (bpy.data.objects['DR_Communication'].matrix_world.translation-Vector((0,-3,5.8))).length<1e-4
scene.render.resolution_x=1920;scene.render.resolution_y=1080
scene.render.resolution_percentage=100
# Save an editable copy with absolute image links, independent of staging folder.
for im in bpy.data.images:
    if im.filepath: im.filepath=bpy.path.abspath(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'divaroom_cameras.blend'),relative_remap=False)
assert before=={o.name:fingerprint(o) for o in meshes}
# OBJ is intermediate only. Native serialization is performed by MikuMikuLibrary.
# Export evaluated world-space geometry at frame 1, retaining all object names.
def native(v):return (v[0]*.1,v[2]*.1,-v[1]*.1)
materials={}
for o in meshes:
    for slot in o.material_slots:
        if slot.material:materials[slot.material.name]=slot.material
mat_names={name:'DIVAROOM_ROOM_TEX_%03d'%i for i,name in enumerate(materials)}
screen_materials=set()
mtl=[]
for name,mat in materials.items():
    tag=mat_names[name]
    mtl.extend([f'newmtl {tag}','Kd 1 1 1','Ka 0.1 0.1 0.1','Ks 0.1 0.1 0.1','Ns 16'])
    images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if mat.use_nodes else []
    if images:
        sequences=[im for im in images if im.source=='SEQUENCE']
        if sequences:images=sequences;screen_materials.add(name)
        im=images[0];dest=OUT/(tag+'.png')
        if im.source=='SEQUENCE':
            # First frame preview; the GIF sequence still requires native material animation.
            shutil.copyfile(bpy.path.abspath(im.filepath),dest)
        else:
            _=im.pixels[0]
            copy=im.copy();copy.filepath_raw=str(dest);copy.file_format='PNG';copy.save()
            bpy.data.images.remove(copy)
        mtl.append('map_Kd '+dest.name)
    mtl.append('')
(OUT/'divaroom.mtl').write_text('\n'.join(mtl),encoding='utf8')
lines=['mtllib divaroom.mtl'];base=1;uvbase=1
for o in meshes:
    mesh=o.data;mesh.calc_loop_triangles();lines.append('o DR_ROOM_'+o.name)
    for v in mesh.vertices:lines.append('v '+' '.join('%.9g'%x for x in native(o.matrix_world@v.co)))
    uv=mesh.uv_layers.active
    screen_loops={i for p in mesh.polygons if o.material_slots[p.material_index].material.name in screen_materials for i in p.loop_indices}
    for loop in mesh.loops:
        p=uv.data[loop.index].uv if uv else (0,0)
        if loop.index in screen_loops:p=(1-p[0],p[1]/.7184866070747375)
        lines.append('vt %.9g %.9g'%(p[0],p[1]))
    current=None
    for tri in mesh.loop_triangles:
        mat=o.material_slots[tri.material_index].material
        if mat.name!=current:lines.append('usemtl '+mat_names[mat.name]);current=mat.name
        lines.append('f '+' '.join(f'{base+mesh.loops[i].vertex_index}/{uvbase+i}' for i in tri.loops))
    base+=len(mesh.vertices);uvbase+=len(mesh.loops)
(OUT/'divaroom.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
manifest['floating_offsets']={}
manifest['material_textures']={o.name:[mat_names[s.material.name] for s in o.material_slots if s.material] for o in meshes}
for name in ['303','315','331','354','360','368']:
    o=bpy.data.objects[name];scene.frame_set(1);basepos=o.matrix_world.translation.copy();values=[]
    for frame in range(1,362):
        scene.frame_set(frame);values.append(list(native(o.matrix_world.translation-basepos)))
    manifest['floating_offsets']['DR_ROOM_'+name]=values
scene.frame_set(1)
manifest['geometry_after']={o.name:fingerprint(o) for o in meshes}
assert manifest['geometry_before']==manifest['geometry_after']
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('DIVA ROOM: camera rigs saved; 47 mesh geometry/UV fingerprints unchanged; interchange exported.')
