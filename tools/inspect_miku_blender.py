import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root/'miku-original.fbx'))
report=[]
for obj in bpy.data.objects:
    row={'name':obj.name,'type':obj.type,'location':list(obj.location),'scale':list(obj.scale),'dimensions':list(obj.dimensions)}
    if obj.type=='ARMATURE':
        row['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in obj.data.bones]
    if obj.type=='MESH':row['vertices']=len(obj.data.vertices)
    report.append(row)
(root/'blender-rig.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(root/'miku-original.blend'))
print('Imported',len(report),'objects;',sum(len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE'),'bones')
