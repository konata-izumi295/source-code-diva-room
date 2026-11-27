import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'research/character'
game=(MOD_DIR / '3dmodels')
report={}
for label,path in [('phone',game/'cellphone/mikucell.blend'),('room',game/'divaroom/model/divaroom.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.scene.frame_set(1);rows=[]
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or not o.data.vertices:continue
        points=[o.matrix_world@v.co for v in o.data.vertices]
        rows.append(dict(name=o.name,min=[min(p[i] for p in points) for i in range(3)],max=[max(p[i] for p in points) for i in range(3)],materials=[m.name for m in o.data.materials if m]))
    report[label]=rows
(root/'activity-contacts.json').write_text(json.dumps(report,indent=2))
