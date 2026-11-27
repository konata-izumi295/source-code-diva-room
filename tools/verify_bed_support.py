"""Check planted ankles during the supported portions of bed entry and exit."""
import bpy,json
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'research/character/miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];scene=bpy.context.scene
def ease(x):
    x=max(0,min(1,x));return x*x*(3-2*x)
report={}
for clip,frames in [('bed_entry',range(58)),('bed_exit',range(72,151))]:
    rig.animation_data.action=bpy.data.actions['DR_'+clip]
    maximum=0
    for f in frames:
        scene.frame_set(f+1);t=f/30
        phase=(5-1.6*t/1.2 if t<1.2 else 3.4 if t<1.65 else 3.4-(t-1.65)/.25) if clip=='bed_entry' else t
        stand=ease((phase-3.4)/1.6)
        origin=Vector((-.37,.25+.165*stand-.39,.82-.30*stand))
        for side,sign in [('l',1),('r',-1)]:
            local=rig.pose.bones[f'kl_asi_{side}_wj_co'].head
            world=origin+Vector((-.44*local.x,.44*local.y,-.44*local.z))
            expected=Vector((-.37-sign*.065*.44,.06988,.54))
            maximum=max(maximum,(world-expected).length)
    report[clip]={'max_planted_ankle_error':maximum,'sampled_frames':len(frames)}
    assert maximum<.002,(clip,maximum)
(root/'research/character/bed-support-validation.json').write_text(json.dumps(report,indent=2))
print('PASS BED SUPPORT',json.dumps(report))
