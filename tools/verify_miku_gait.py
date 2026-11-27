import bpy,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-actions.blend'))
rig=bpy.data.objects['DR_Miku'];rig.animation_data.action=bpy.data.actions['DR_walk']
scene=bpy.context.scene;scene.frame_set(1)
first={b.name:b.matrix.copy() for b in rig.pose.bones};max_error=0;min_ankle=100;stance=[]
for frame in range(31):
    scene.frame_set(frame+1)
    for side,shift in [('l',0),('r',.5)]:
        phase=(frame/30+shift)%1;b=rig.pose.bones[f'kl_asi_{side}_wj_co'];p=b.head
        assert all(math.isfinite(v) for v in p)
        min_ankle=min(min_ankle,p.y)
        if phase<.6:
            expected_z=-.046+.18-.36*phase/.6
            max_error=max(max_error,abs(p.y-.102),abs(p.z-expected_z))
            stance.append([frame,side,float(p.y),float(p.z)])
loop=max(abs(b.matrix[i][j]-first[b.name][i][j]) for b in rig.pose.bones for i in range(4) for j in range(4))
report=dict(max_stance_error=max_error,min_ankle_height=min_ankle,loop_matrix_error=loop,stance=stance)
(root/'gait-validation.json').write_text(json.dumps(report,indent=2))
assert max_error<.004,report
assert min_ankle>.098,report
assert loop<.001,report
for frame in (1,16):
    scene.frame_set(frame)
    hand_delta=rig.pose.bones['kl_te_l_wj'].head.z-rig.pose.bones['kl_te_r_wj'].head.z
    foot_delta=rig.pose.bones['kl_asi_l_wj_co'].head.z-rig.pose.bones['kl_asi_r_wj_co'].head.z
    assert hand_delta*foot_delta<0,('Arms must oppose legs',frame,hand_delta,foot_delta)
print('PASS gait contacts and loop',max_error,min_ankle,loop)
contacts={}
for clip in ('place_phone','pick_phone','sit_down','sit_phone','stand_up','seated_draw'):
    rig.animation_data.action=bpy.data.actions['DR_'+clip]
    duration=dict(json.loads((root/'actions.json').read_text())['clips'])[clip]
    error=0
    for frame in range(duration*30+1):
        scene.frame_set(frame+1)
        for side in ('l','r'):
            ankle=rig.pose.bones[f'kl_asi_{side}_wj_co'].head
            error=max(error,abs(ankle.y-.102))
    contacts[clip]=error
    assert error<.004,(clip,'feet leave the floor',error)
(root/'support-validation.json').write_text(json.dumps(contacts,indent=2))
print('PASS support during chair and phone interactions',contacts)
