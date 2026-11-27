import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]/'research'/'room-export'
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
if scene.world and scene.world.use_nodes:
    bg=next((n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'),None)
    if bg:bg.inputs['Strength'].default_value=.35
ld=bpy.data.lights.new('Preview fill','AREA');ld.energy=1800;ld.shape='DISK';ld.size=14
light=bpy.data.objects.new('Preview fill',ld);scene.collection.objects.link(light);light.location=(0,1,15)
target=bpy.data.objects['DR_CharacterTarget'];cam=bpy.data.objects['DR_Communication']
bpy.context.view_layer.update();start=cam.matrix_world.translation.copy()
target.location.x+=2;bpy.context.view_layer.update()
delta=cam.matrix_world.translation-start
assert (delta-Vector((2,0,0))).length<1e-4,delta
target.location.x-=2;bpy.context.view_layer.update()
for name in ['DR_Overview','DR_Communication','DR_Activity']:
    scene.camera=bpy.data.objects[name];scene.frame_set(1)
    scene.render.filepath=str(root/(name+'.png'));bpy.ops.render.render(write_still=True)
print('Verified communication rig follows target translation; rendered three camera views. Preview lights not saved.')
