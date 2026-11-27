import bpy,math
from mathutils import Vector
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.resolution_x=480;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Preview');scene.world.color=(.25,.25,.25)
bpy.ops.object.camera_add(location=(1,-3.2,1.15));cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=48;scene.camera=cam
for loc,power,size in [((2,-3,4),450,4),((-2,-1,2),200,3),((0,2,3),300,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
for name,frame in [('walk',1),('walk',9),('walk',16),('walk',24)]:
    rig.animation_data.action=bpy.data.actions['DR_'+name];scene.frame_set(frame)
    scene.render.filepath=str(root/('walk-review-'+str(frame)+'.png'));bpy.ops.render.render(write_still=True)
