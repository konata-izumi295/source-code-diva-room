"""Conservative horizontal envelope of the evaluated actor below the bed top."""
import bpy,json
import numpy as np
from pathlib import Path

root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'research/character/miku-actions.blend'))
rig=bpy.data.objects['DR_Miku']
scene=bpy.context.scene
points=[]
for action,frames in [('DR_walk',range(1,32)),('DR_idle',range(1,122,15))]:
    rig.animation_data.action=bpy.data.actions[action]
    for frame in frames:
        scene.frame_set(frame)
        deps=bpy.context.evaluated_depsgraph_get()
        for obj in scene.objects:
            if obj.type!='MESH':continue
            evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
            vertices=np.empty(len(mesh.vertices)*3,dtype=np.float32)
            mesh.vertices.foreach_get('co',vertices)
            vertices=vertices.reshape(-1,3)*.44
            low=vertices[vertices[:,1]+.025<.31][:,[0,2]]
            if len(low):points.extend(map(tuple,low.tolist()))
            evaluated.to_mesh_clear()

# Exact convex hull of all sampled low vertices, including hair and clothing.
points=sorted(set(points))
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
lower=[];upper=[]
for p in points:
    while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
    lower.append(p)
for p in reversed(points):
    while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
    upper.append(p)
hull=lower[:-1]+upper[:-1]
report={'scale':.44,'bed_top_including_margin':.31,'hull_xz':hull,
        'note':'Envelope of all sampled walking/idle poses, not a single gait frame.'}
(root/'research/character/walk-envelope.json').write_text(json.dumps(report,indent=2))
print('WALK_ENVELOPE',len(points),'unique points;',len(hull),'hull points')
