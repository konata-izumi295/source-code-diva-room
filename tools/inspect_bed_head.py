import bpy,json
from pathlib import Path
root=Path.cwd()
bpy.ops.wm.open_mainfile(filepath=str(root/'research/character/miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];rig.animation_data.action=bpy.data.actions['DR_lie_phone'];bpy.context.scene.frame_set(1)
report=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 pts=[v.co for v in mesh.vertices if v.co.y>1.28]
 if pts:report.append(dict(name=o.name,count=len(pts),minz=min(v.z for v in pts),maxy=max(v.y for v in pts)))
 ev.to_mesh_clear()
print('HEAD_GEOMETRY',json.dumps(report))
