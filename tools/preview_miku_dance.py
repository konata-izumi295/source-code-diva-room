import bpy,sys
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-actions.blend'))
if '--live' in sys.argv:
    source=Path(__file__).with_name('animate_miku.py')
    exec(compile(source.read_text().split('clips=[')[0],str(source),'exec'),globals())
rig=bpy.data.objects['DR_Miku'];rig.scale=(1,1,1);rig.animation_data_create()
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=500;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
bpy.ops.object.camera_add(location=(.5,-3.5,1.4));cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=1.85;scene.camera=cam
for i in range(8):
    if '--live' in sys.argv:
        rig.animation_data.action=None;pose('dance',float(i))
    else:
        rig.animation_data.action=bpy.data.actions['DR_dance'];scene.frame_set(1+i*30)
    scene.render.filepath=str(root/f'dance-review-{i}.png');bpy.ops.render.render(write_still=True)
