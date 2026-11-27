"""Check wrist skinning, contact, bend and clip seams on the exported source rig."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];scene=bpy.context.scene
report={};failures=[]
for clip,seconds in json.loads((root/'actions.json').read_text())['clips']:
    rig.animation_data.action=bpy.data.actions['DR_'+clip]
    max_helper=0;max_bend=0;max_tap=0
    for f in range(seconds*30+1):
        scene.frame_set(f+1);bones=rig.pose.bones
        for side in ('l','r'):
            wrist=bones[f'kl_te_{side}_wj'];helper=bones[f'n_ste_{side}_wj_ex']
            expected=wrist.matrix@wrist.bone.matrix_local.inverted()@helper.bone.matrix_local
            max_helper=max(max_helper,max(abs(expected[i][j]-helper.matrix[i][j]) for i in range(4) for j in range(4)))
            direction=bones[f'nl_naka_{side}_wj'].head-wrist.head
            forearm=wrist.head-bones[f'j_ude_{side}_wj'].head
            bend=math.degrees(direction.angle(forearm));assert math.isfinite(bend)
            max_bend=max(max_bend,bend)
        if clip in ('phone','lie_phone','sit_phone'):
            w=bones['kl_te_l_wj'].head
            long=(bones['nl_naka_l_wj'].head-w).normalized()
            width=(bones['nl_hito_l_wj'].head-bones['nl_ko_l_wj'].head).normalized()
            normal=long.cross(width).normalized()
            target=w+long*.070+normal*(.024+.004*(.5-.5*math.cos(math.pi*f/30)))
            b=bones['nl_hito_b_r_wj'].head;c=bones['nl_hito_c_r_wj'].head
            tip=c+(c-b).normalized()*.012
            max_tap=max(max_tap,(tip-target).length)
    if max_helper>=.0001:failures.append((clip,'weighted wrist helper diverged',max_helper))
    if clip in ('phone','lie_phone','sit_phone'):
        if max_tap>=.012:failures.append((clip,'index misses screen',max_tap))
        if max_bend>=65:failures.append((clip,'wrist over-flexed',max_bend))
    report[clip]=dict(helper_error=max_helper,max_wrist_bend_degrees=max_bend,index_contact_error=max_tap)
    if clip in ('idle','walk','turn','dance','phone','lie_phone','sit_phone'):
        scene.frame_set(1);start={b.name:b.matrix.copy() for b in rig.pose.bones}
        scene.frame_set(seconds*30+1)
        seam=max(abs(b.matrix[i][j]-start[b.name][i][j]) for b in rig.pose.bones for i in range(4) for j in range(4))
        report[clip]['loop_error']=seam
        if seam>=.001:failures.append((clip,'loop seam',seam))
(root/'hand-validation.json').write_text(json.dumps(report,indent=2))
print('HAND REPORT',json.dumps(report))
assert not failures,failures
print('PASS HANDS')
