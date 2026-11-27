import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
import bpy
from mathutils import Vector
path=str((MOD_DIR / '3dmodels/cellphone/mikucell.blend'))
bpy.ops.wm.open_mainfile(filepath=str(__import__('pathlib').Path(__file__).resolve().parents[1]/'research/character/miku-actions.blend'))
with bpy.data.libraries.load(path,link=False) as (src,dst):dst.objects=src.objects
for o in dst.objects:
    if o and o.type=='MESH':bpy.context.collection.objects.link(o)
bpy.context.view_layer.update()
for o in dst.objects:
    if o.type!='MESH':continue
    for i,m in enumerate(o.data.materials):
        faces=[p for p in o.data.polygons if p.material_index==i]
        area=sum(p.area for p in faces)
        if not area:continue
        normal=sum((o.matrix_world.to_3x3()@p.normal*p.area for p in faces),Vector())/area
        center=sum((o.matrix_world@p.center*p.area for p in faces),Vector())/area
        print(o.name,m.name,'center',tuple(center),'normal',tuple(normal))
