"""Add reversible material/object animation, keeping mesh and UV data intact."""
import bpy, math, json, hashlib, struct
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]/'research'/'blender_animated'
OUT=ROOT/'model'/'divaroom.blend'
OUT.parent.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
FLOATS=['303','315','331','354','360','368']
LEDS=['324','459','257','138','343']
PERIOD=360
def fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
    for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
    for uv in o.data.uv_layers:
        for v in uv.data:h.update(struct.pack('<2f',*v.uv))
    return h.hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
def curves(idblock):
    ad=idblock.animation_data
    if not ad or not ad.action:return []
    return [fc for layer in ad.action.layers for strip in layer.strips
            for bag in strip.channelbags for fc in bag.fcurves]
def cycle(idblock):
    for fc in curves(idblock):
        for k in fc.keyframe_points:k.interpolation='LINEAR'
        fc.modifiers.new('CYCLES')
def node(tree,kind,label):
    n=tree.nodes.new(kind);n.label=label;n.name='DIVA ROOM | '+label
    return n
def mathnode(tree,op,a=None,b=None,label='Math'):
    n=node(tree,'ShaderNodeMath',label);n.operation=op
    for index,value in enumerate((a,b)):
        if value is not None:
            if isinstance(value,(int,float)):n.inputs[index].default_value=value
            else:tree.links.new(value,n.inputs[index])
    return n.outputs[0]
def material(obj):
    m=obj.active_material.copy();m.name=obj.active_material.name+' | Animated'
    obj.active_material=m
    tree=m.node_tree
    bsdf=next(n for n in tree.nodes if n.type=='BSDF_PRINCIPLED')
    tex=next(n for n in tree.nodes if n.type=='TEX_IMAGE')
    return tree,bsdf,tex
scene.frame_start=1;scene.frame_end=PERIOD;scene.render.fps=30
for index,name in enumerate(FLOATS):
    obj=bpy.data.objects[name];base=obj.location.copy()
    amp=0.10 if name=='368' else 0.12+0.025*(index%3)
    phase=index*math.tau/len(FLOATS)
    turns=2 if name=='368' else 3
    for frame in range(1,PERIOD+2):
        t=(frame-1)/PERIOD
        obj.location.z=base.z+amp*(math.sin(math.tau*turns*t+phase)-math.sin(phase))
        obj.keyframe_insert('location',index=2,frame=frame,group='DIVA ROOM · Float')
    cycle(obj)
    obj['divaroom_animation']='Vertical floating; original geometry and frame-1 placement preserved'
tree,bsdf,tex=material(bpy.data.objects['292'])
uv=node(tree,'ShaderNodeTexCoord','Original UV')
offset=node(tree,'ShaderNodeVectorMath','Stripes downward');offset.operation='ADD'
tree.links.new(uv.outputs['UV'],offset.inputs[0]);tree.links.new(offset.outputs[0],tex.inputs['Vector'])
tex.extension='REPEAT'
for frame,value in ((1,0),(PERIOD+1,6)):
    offset.inputs[1].default_value=(0,value,0)
    offset.inputs[1].keyframe_insert('default_value',frame=frame)
cycle(tree)
tree.links.new(tex.outputs['Color'],bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value=2.2
for index,name in enumerate(LEDS):
    tree,bsdf,tex=material(bpy.data.objects[name])
    rgb=node(tree,'ShaderNodeSeparateColor','LED color mask');rgb.mode='RGB'
    tree.links.new(tex.outputs['Color'],rgb.inputs[0])
    chroma=mathnode(tree,'SUBTRACT',rgb.outputs[1],rgb.outputs[0],label='Green/cyan traces only')
    mask=mathnode(tree,'MULTIPLY',chroma,6,label='LED mask');mask.node.use_clamp=True
    pulse=node(tree,'ShaderNodeValue','Soft LED breathing')
    for frame in range(1,PERIOD+2,3):
        pulse.outputs[0].default_value=3.4+0.45*math.sin(math.tau*2*(frame-1)/PERIOD+index*.7)
        pulse.outputs[0].keyframe_insert('default_value',frame=frame)
    strength=mathnode(tree,'MULTIPLY',mask,pulse.outputs[0],label='Masked emission strength')
    tree.links.new(tex.outputs['Color'],bsdf.inputs['Emission Color'])
    tree.links.new(strength,bsdf.inputs['Emission Strength']);cycle(tree)
    bsdf.inputs['Roughness'].default_value=0.38
tv=bpy.data.objects['131'];original_tv_material=tv.active_material
tree,bsdf,tex=material(tv)
animated_tv_material=tv.active_material
tv.data.materials[0]=original_tv_material;tv.data.materials.append(animated_tv_material)
# The imported packed atlas has a different orientation from the loose PNG.
# Only the four front triangles span the complete screen rectangle.
screen_faces=[]
uvdata=tv.data.uv_layers.active.data
for poly in tv.data.polygons:
    coords=[uvdata[i].uv for i in poly.loop_indices]
    us=[c.x for c in coords];vs=[c.y for c in coords]
    if max(us)-min(us)>.99 and max(vs)-min(vs)>.70 and min(vs)<.01 and max(vs)<.72:
        poly.material_index=1;screen_faces.append(poly.index)
assert len(screen_faces)==4,screen_faces
uv=node(tree,'ShaderNodeTexCoord','TV original UV')
sep=node(tree,'ShaderNodeSeparateXYZ','TV coordinates');tree.links.new(uv.outputs['UV'],sep.inputs[0])
u,v=sep.outputs['X'],sep.outputs['Y']
xmin,xmax,ymin,ymax=0,1,0,0.7184866070747375
mask=mathnode(tree,'MULTIPLY',mathnode(tree,'GREATER_THAN',u,xmin),mathnode(tree,'LESS_THAN',u,xmax))
mask=mathnode(tree,'MULTIPLY',mask,mathnode(tree,'GREATER_THAN',v,ymin))
mask=mathnode(tree,'MULTIPLY',mask,mathnode(tree,'LESS_THAN',v,ymax),label='Screen only; preserve bezel')
mapped=node(tree,'ShaderNodeCombineXYZ','Screen UV')
tree.links.new(mathnode(tree,'SUBTRACT',1,u),mapped.inputs['X'])
tree.links.new(mathnode(tree,'DIVIDE',mathnode(tree,'SUBTRACT',v,ymin),ymax-ymin),mapped.inputs['Y'])
img=bpy.data.images.load(str(ROOT/'textures'/'screen_frames'/'screen_0001.png'),check_existing=False)
img.source='SEQUENCE'
movie=node(tree,'ShaderNodeTexImage','screen.gif · original 12-second timing');movie.image=img;movie.extension='EXTEND'
movie.image_user.frame_duration=PERIOD;movie.image_user.frame_start=1
movie.image_user.use_cyclic=True;movie.image_user.use_auto_refresh=True
tree.links.new(mapped.outputs[0],movie.inputs['Vector'])
mix=node(tree,'ShaderNodeMixRGB','Animated display inside original frame')
tree.links.new(mask,mix.inputs[0]);tree.links.new(tex.outputs['Color'],mix.inputs[1]);tree.links.new(movie.outputs['Color'],mix.inputs[2])
tree.links.new(movie.outputs['Color'],bsdf.inputs['Base Color'])
tree.links.new(movie.outputs['Color'],bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value=1.2
cycle(tree)
# A scene compositor glow affects only bright emissive details.
comp=scene.compositing_node_group
if comp is None:
    comp=bpy.data.node_groups.new('DIVA ROOM · LED glow','CompositorNodeTree')
    comp.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    layers=comp.nodes.new('CompositorNodeRLayers')
    output=comp.nodes.new('NodeGroupOutput')
    comp.links.new(layers.outputs['Image'],output.inputs['Image'])
    scene.compositing_node_group=comp
outputs=[n for n in comp.nodes if n.type=='GROUP_OUTPUT']
if outputs and outputs[0].inputs[0].is_linked:
    output=outputs[0];incoming=output.inputs[0].links[0].from_socket
    glare=comp.nodes.new('CompositorNodeGlare')
    glare.inputs['Type'].default_value='Fog Glow';glare.inputs['Quality'].default_value='High'
    glare.inputs['Strength'].default_value=.35
    if 'Threshold' in glare.inputs:glare.inputs['Threshold'].default_value=1.2
    comp.links.new(incoming,glare.inputs['Image']);comp.links.new(glare.outputs['Image'],output.inputs[0])
scene.frame_set(1)
after={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
assert before==after,'Mesh or UV data changed'
# Every float repeats exactly at the first frame after the playback range.
loop={}
for name in FLOATS:
    obj=bpy.data.objects[name]
    scene.frame_set(1);a=obj.matrix_world.translation.copy()
    scene.frame_set(PERIOD+1);b=obj.matrix_world.translation.copy()
    assert (a-b).length<1e-5,(name,a,b)
    loop[name]={'seam_error':(a-b).length}
scene.frame_set(1)
img.filepath='//../textures/screen_frames/screen_0001.png'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),relative_remap=False)
(ROOT/'validation.json').write_text(json.dumps({'geometry_unchanged':before==after,'mesh_hashes':after,'floating_loops':loop,'frames':PERIOD,'fps':30,'screen_duration_seconds':12},indent=2))
# Preview camera and lighting are temporary and are not saved in the project.
camdata=bpy.data.cameras.new('Preview only');cam=bpy.data.objects.new('Preview only',camdata);scene.collection.objects.link(cam)
cam.location=(0,-12,9);target=Vector((-1,15,6));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=24
scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100
if scene.world and scene.world.use_nodes:
    bg=next((n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'),None)
    if bg:bg.inputs['Strength'].default_value=.35
lightdata=bpy.data.lights.new('Preview fill','AREA');lightdata.energy=1800;lightdata.shape='DISK';lightdata.size=14
light=bpy.data.objects.new('Preview fill',lightdata);scene.collection.objects.link(light);light.location=(0,1,15)
scene.render.filepath=str(ROOT/'preview_001.png');bpy.ops.render.render(write_still=True)
scene.frame_set(91);scene.render.filepath=str(ROOT/'preview_091.png');bpy.ops.render.render(write_still=True)
print('VALIDATED',OUT)
