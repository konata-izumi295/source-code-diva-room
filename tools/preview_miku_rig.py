import bpy,math
from mathutils import Vector
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-rig.blend'))
rig=bpy.data.objects['DR_Miku'];rig.scale=(1,1,1)
bpy.context.view_layer.update()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Preview world');scene.world.color=(.25,.25,.25)
bpy.ops.object.camera_add(location=(0,-3.2,1.15));cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=48;scene.camera=cam
for loc,power,size in [((2,-3,4),450,4),((-2,-1,2),200,3),((0,2,3),300,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(root/'miku-rig-preview.png');bpy.ops.render.render(write_still=True)
