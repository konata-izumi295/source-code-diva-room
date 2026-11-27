"""Inspect the actual hand chains and deformation, without saving the project."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-actions.blend'))
if '--live' in sys.argv:
    source=Path(__file__).with_name('animate_miku.py')
    exec(compile(source.read_text().split("clips=[")[0],str(source),'exec'),globals())
rig=bpy.data.objects['DR_Miku'];rig.scale=(1,1,1)
report={}
for b in rig.data.bones:
    if any(s in b.name for s in ('te_l','hito','naka','kusu','ko_l','oya','sude','ude_l')):
        report[b.name]=dict(parent=b.parent.name if b.parent else None,head=list(b.head_local),tail=list(b.tail_local),children=[c.name for c in b.children])
(root/'hand-rig-inspection.json').write_text(json.dumps(report,indent=2))
for name,data in report.items():print(name,data)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1000;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
phonepath=(MOD_DIR / '3dmodels/cellphone/mikucell.blend')
with bpy.data.libraries.load(str(phonepath),link=False) as (src,dst):dst.objects=src.objects
phones=[o for o in dst.objects if o and o.type=='MESH']
originals={o.name:o.matrix_world.copy() for o in phones}
for o in phones:bpy.context.collection.objects.link(o)
phone_axes=Matrix(((-1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.40
for kind in ('sit_phone','phone','idle'):
    if '--live' in sys.argv:
        rig.animation_data_create();rig.animation_data.action=None;pose(kind,1)
    else:
        rig.animation_data.action=bpy.data.actions['DR_'+kind];scene.frame_set(31)
    bpy.context.view_layer.update()
    wrist=rig.pose.bones['kl_te_l_wj'].head
    long=(rig.pose.bones['nl_naka_l_wj'].head-wrist).normalized()
    width=(rig.pose.bones['nl_hito_l_wj'].head-rig.pose.bones['nl_ko_l_wj'].head).normalized()
    normal=long.cross(width).normalized();width=normal.cross(long).normalized()
    attachment=Matrix((width,normal,long)).transposed().to_4x4();attachment.translation=wrist+long*.055+normal*.012
    for o in phones:o.matrix_world=rig.matrix_world@attachment@phone_axes@Matrix.Scale(.05,4)@originals[o.name];o.hide_render=kind=='idle'
    target=rig.matrix_world@rig.pose.bones['kl_te_l_wj'].head
    # Native coordinates are Y-up before the armature object's world transform.
    direction=rig.matrix_world.to_3x3()@Vector((-.9,.45,.65))
    cam.location=target+direction
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    label=sys.argv[sys.argv.index('--label')+1] if '--label' in sys.argv else 'before'
    scene.render.filepath=str(root/f'hands-{label}-{kind}.png');bpy.ops.render.render(write_still=True)
