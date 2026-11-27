import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'research/character/miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];rig.animation_data.action=bpy.data.actions['DR_phone']
bpy.context.scene.frame_set(1)
result={}
for b in rig.pose.bones:
    if any(s in b.name for s in ('te_l','hito_l','naka_l','oya_l','necktie')):
        result[b.name]={'head':list(b.head),'tail':list(b.tail),'rest':list(b.bone.head_local)}
(root/'research/character/hand-inspection.json').write_text(json.dumps(result,indent=2))
rig.animation_data.action=bpy.data.actions['DR_place_phone'];bpy.context.scene.frame_set(55)
for name in ('j_kata_l_wj_cu','j_ude_l_wj','kl_te_l_wj','nl_naka_l_wj','nl_hito_l_wj','nl_ko_l_wj'):
    print('CONTACT',name,list(rig.pose.bones[name].head))
path=(MOD_DIR / '3dmodels/cellphone/mikucell.blend')
with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=src.objects
from mathutils import Vector
points=[o.matrix_world@Vector(p)*.05 for o in dst.objects if o and o.type=='MESH' for p in o.bound_box]
print('PHONE BOUNDS',[(min(p[i] for p in points),max(p[i] for p in points)) for i in range(3)])
