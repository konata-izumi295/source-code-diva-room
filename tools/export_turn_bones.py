import bpy
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'research/character/miku-actions.blend'))
bones=list(bpy.data.objects['DR_Miku'].data.bones)
text=['#pragma once','// Generated from the installed Miku bind rig; rerun tools/export_turn_bones.py if the rig changes.','namespace RoomActorBones {']
for label,name in [('Head','j_kao_wj'),('Torso','n_hara_c_wj_ex')]:
 b=next(b for b in bones if b.name==name)
 axis=b.parent.matrix_local.to_quaternion().inverted()@Vector((0,1,0))
 text.append(f'inline constexpr unsigned {label}={bones.index(b)};')
 text.append(f'inline constexpr float {label}Axis[3]={{'+','.join(f'{float(v):.9f}f' for v in axis)+'};')
text.append('}')
(root/'DivaRoom/RoomActorBones.h').write_text('\n'.join(text))
