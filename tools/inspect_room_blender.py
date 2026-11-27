import bpy,json
from mathutils import Vector
out={}
for o in bpy.data.objects:
    if o.type=='MESH':
        pts=[o.matrix_world@Vector(v) for v in o.bound_box]
        out[o.name]={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
print('BOUNDS',json.dumps(out))
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            s=a.spaces.active
            print('VIEW',screen.name,'matrix',list(map(list,s.region_3d.view_matrix)),'perspective',s.region_3d.view_perspective,'lens',s.lens)
o=bpy.data.objects['292'];uv=o.data.uv_layers.active
print('STRIPE_COORDS',[(list(o.matrix_world@o.data.vertices[l.vertex_index].co),list(uv.data[l.index].uv)) for l in o.data.loops])
