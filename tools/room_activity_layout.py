import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
import bpy,json
from mathutils import Vector
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str((MOD_DIR / '3dmodels/divaroom/model/divaroom.blend')))
scene=bpy.context.scene;scene.frame_set(1);rows=[]
for o in scene.objects:
    if o.type!='MESH':continue
    points=[o.matrix_world@Vector(v) for v in o.bound_box]
    lo=[min(p[i] for p in points) for i in range(3)];hi=[max(p[i] for p in points) for i in range(3)]
    rows.append({'name':o.name,'min':lo,'max':hi})
    if hi[2]>12:o.hide_render=True
(root/'room-bounds.json').write_text(json.dumps(rows,indent=2))
bpy.ops.object.camera_add(location=(0,0,70));cam=bpy.context.object;cam.rotation_euler=(0,0,0);cam.data.type='ORTHO';cam.data.ortho_scale=65;scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.filepath=str(root/'room-layout.png');bpy.ops.render.render(write_still=True)

