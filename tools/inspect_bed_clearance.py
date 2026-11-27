"""Measure head/mattress clearance from evaluated vertices; no game launch."""
import bpy,json,numpy as np
from pathlib import Path
root=Path.cwd();bpy.ops.wm.open_mainfile(filepath=str(root/'research/character/miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];rig.animation_data.action=bpy.data.actions['DR_lie_phone'];bpy.context.scene.frame_set(1)
vertices=[];triangles=[]
for line in (root/'research/room-export/divaroom.obj').read_text().splitlines():
 f=line.split()
 if not f:continue
 if f[0]=='v':vertices.append(tuple(map(float,f[1:4])))
 if f[0]=='f':
  tri=np.array([vertices[int(x.split('/')[0])-1] for x in f[1:]])
  if tri[:,1].max()<.6 and tri[:,1].max()>.15:triangles.append(tri)
report=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith(('face_MZ','back_MZ','headset_MZ')):continue
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 pts=np.array([[.02-.44*v.co.y,.28+.44*v.co.z,1.05-.44*v.co.x] for v in mesh.vertices])
 surface=np.full(len(pts),-100.)
 for tri in triangles:
  a=np.vstack((tri[:,0],tri[:,2],np.ones(3)))
  if abs(np.linalg.det(a))<1e-10:continue
  w=np.column_stack((pts[:,0],pts[:,2],np.ones(len(pts))))@np.linalg.inv(a).T
  inside=np.min(w,axis=1)>=-1e-6
  surface[inside]=np.maximum(surface[inside],(w@tri[:,1])[inside])
 delta=pts[:,1]-surface
 report.append(dict(mesh=o.name,min_clearance=float(delta.min())))
 ev.to_mesh_clear()
(root/'research/character/bed-head-clearance.json').write_text(json.dumps(report,indent=2))
print('HEAD_CLEARANCE',json.dumps(report))
