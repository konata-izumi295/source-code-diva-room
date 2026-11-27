import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'research/character/miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];rig.animation_data.action=bpy.data.actions['DR_sit_phone'];bpy.context.scene.frame_set(31)
bpy.context.view_layer.update()
for side in ('l','r'):
    names=[f'{p}_{side}_wj' for p in ('j_ude','kl_te','n_ste','nl_hito','nl_hito_b','nl_hito_c','nl_naka','nl_naka_b','nl_naka_c','nl_oya','nl_oya_b','nl_oya_c')]
    for name in names:
        if name in rig.pose.bones:
            b=rig.pose.bones[name];print(name,'head',tuple(b.head),'rotation',tuple(b.rotation_quaternion),'parent',b.parent.name if b.parent else '')
for o in bpy.data.objects:
    if o.type!='MESH':continue
    sums={}
    for v in o.data.vertices:
        for g in v.groups:
            name=o.vertex_groups[g.group].name
            if 'ste_' in name or 'sude' in name or 'kl_te_' in name:sums[name]=sums.get(name,0)+g.weight
    if sums:print('WEIGHTS',o.name,sums)
