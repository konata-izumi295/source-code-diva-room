"""Author room-specific actions on the recovered Miku rig, leaving originals intact."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
root=Path(__file__).resolve().parents[1]/'research/character'
only=sys.argv[sys.argv.index('--only')+1].split(',') if '--only' in sys.argv else None
bpy.ops.wm.open_mainfile(filepath=str(root/('miku-actions.blend' if only else 'miku-rig.blend')))
rig=bpy.data.objects['DR_Miku'];rig.scale=(1,1,1)
bpy.context.view_layer.update()
bones=rig.pose.bones
for b in bones:b.rotation_mode='QUATERNION'

def rotate(name,axis,degrees):
    b=bones[name];q=b.bone.matrix_local.to_quaternion()
    b.rotation_quaternion=q.inverted()@Quaternion(Vector(axis),math.radians(degrees))@q

def move(name,offset):
    # Imported pelvis local Z points sideways; all authored offsets are Y-up room space.
    b=bones[name];b.location=b.bone.matrix_local.to_quaternion().inverted()@Vector(offset)

def aim(name,child,target):
    bpy.context.view_layer.update();b=bones[name]
    direction=bones[child].head-b.head
    if direction.length<1e-5:return
    q=direction.rotation_difference(Vector(target)-b.head)
    matrix=b.matrix.copy();rotation=q.to_matrix().to_4x4()@matrix
    rotation.translation=matrix.translation;b.matrix=rotation
    bpy.context.view_layer.update()

def hand(side,target,relaxed=False):
    shoulder=f'j_kata_{side}_wj_cu';elbow=f'j_ude_{side}_wj';wrist=f'kl_te_{side}_wj'
    bpy.context.view_layer.update();s=bones[shoulder].head.copy();e=bones[elbow].head.copy();w=bones[wrist].head.copy()
    a=(e-s).length;b=(w-e).length;target=Vector(target);d=target-s
    distance=min(d.length,a+b-.012);direction=d.normalized();target=s+direction*distance
    low=Vector(((.12 if side=='l' else -.12),0,-1))
    high=Vector(((.32 if side=='l' else -.32),-1,-.15))
    blend=0 if relaxed else ease((target.y-.82)/.32)
    pole=low.lerp(high,blend)
    pole=(pole-direction*pole.dot(direction)).normalized()
    along=(a*a-b*b+distance*distance)/(2*distance)
    elbow_target=s+direction*along+pole*math.sqrt(max(0,a*a-along*along))
    aim(shoulder,elbow,elbow_target);aim(elbow,wrist,target)

def reset():
    for b in bones:b.location=(0,0,0);b.rotation_quaternion=(1,0,0,0);b.scale=(1,1,1)

def ease(x):
    x=max(0,min(1,x));return x*x*(3-2*x)

def palm(side,long,normal,weight=1):
    # Orient the actual palm, not the arbitrary tail of the imported wrist bone.
    wrist=bones[f'kl_te_{side}_wj'];rest=wrist.bone
    z=(bones[f'nl_naka_{side}_wj'].bone.head_local-rest.head_local).normalized()
    x=(bones[f'nl_hito_{side}_wj'].bone.head_local-bones[f'nl_ko_{side}_wj'].bone.head_local).normalized()
    y=z.cross(x).normalized();x=y.cross(z).normalized()
    source=Matrix((x,y,z)).transposed()
    # The two bind frames have opposite palm normals. Giving both wrists the
    # same frame used to pronate the right hand by an extra half turn.
    z=Vector(long).normalized();y=Vector(normal)*(1 if side=='l' else -1)
    y=(y-z*y.dot(z)).normalized();x=y.cross(z).normalized()
    target=Matrix((x,y,z)).transposed()
    matrix=(target@source.inverted()).to_4x4()@rest.matrix_local
    matrix=wrist.matrix.to_quaternion().slerp(matrix.to_quaternion(),weight).to_matrix().to_4x4()
    matrix.translation=wrist.head.copy();wrist.matrix=matrix
    bpy.context.view_layer.update()

def wrist_helpers():
    # These weighted sibling bones are driven by the native rig, not by wrist
    # parenting. Leaving them in the forearm pose tears the base of the palm.
    bpy.context.view_layer.update()
    for side in ('l','r'):
        wrist=bones[f'kl_te_{side}_wj'];helper=bones[f'n_ste_{side}_wj_ex']
        helper.matrix=wrist.matrix@wrist.bone.matrix_local.inverted()@helper.bone.matrix_local
    bpy.context.view_layer.update()

def fingers(side,t,grip=0,touch=0):
    # Separate knuckle, middle and tip flexion; keep relaxed fingers together.
    for i,finger in enumerate(('hito','naka','kusu','ko')):
        rest=(10+i*2,16+i*2,7+i)
        hold=(45+i*2,58+i*2,26+i)
        for j,joint in enumerate(('','_b','_c')):
            a=rest[j]+(hold[j]-rest[j])*grip
            if finger=='hito':a=a*(1-touch)+(5,9,4)[j]*touch
            a+=1.2*math.sin(2*math.pi*t/4-i*.25)*(1-grip)
            curl_finger(side,finger,joint,a)
    # Thumb opposition is not the same hinge as the other four fingers.
    wrist=bones[f'kl_te_{side}_wj'].bone
    z=(bones[f'nl_naka_{side}_wj'].bone.head_local-wrist.head_local).normalized()
    x=(bones[f'nl_hito_{side}_wj'].bone.head_local-bones[f'nl_ko_{side}_wj'].bone.head_local).normalized()
    n=z.cross(x).normalized()*(1 if side=='l' else -1)
    thumb=bones[f'nl_oya_l_wj' if side=='l' else 'nl_oya_r_wj'].bone
    direction=(bones[f'nl_oya_b_{side}_wj'].bone.head_local-thumb.head_local).normalized()
    axis=direction.cross(n).normalized()
    for j,joint in enumerate(('','_b','_c')):
        rotate(f'nl_oya{joint}_{side}_wj',axis,(8,10,7)[j]+grip*(12,15,12)[j])

def reading_hands(kind,t,draw=1):
    # Keep the wrist closer to the forearm line; the other hand approaches the
    # visible screen from the side instead of occupying the holder's palm.
    long=Vector((0,.60,.80));normal=Vector((0,.80,-.60))
    palm('l',long,normal,draw)
    bpy.context.view_layer.update()
    w=bones['kl_te_l_wj'].head.copy()
    target=w+Vector((-.115,.015,-.015))
    current=bones['kl_te_r_wj'].head.copy()
    hand('r',current.lerp(target,draw))
    palm('r',(.82,.35,.45),(0,.80,-.60),draw)
    fingers('l',t,grip=.8*draw)
    fingers('r',t,grip=.15*draw,touch=draw)
    if draw>.001:
        # Align the index pad with the screen, not with its back. The tap lifts
        # a few millimetres before returning, while the holding hand stays calm.
        tap=w+long*.070+normal*(.024+.004*(.5-.5*math.cos(math.pi*t)))
        for _ in range(2):
            bpy.context.view_layer.update()
            b=bones['nl_hito_b_r_wj'].head;c=bones['nl_hito_c_r_wj'].head
            tip=c+(c-b).normalized()*.012
            hand('r',bones['kl_te_r_wj'].head+(tap-tip)*draw)
            palm('r',(.82,.35,.45),(0,.80,-.60),draw)
        fingers('r',t,grip=.15*draw,touch=draw)

def reach_amount(t):
    return ease(t/1.5)*(1-ease((t-2.2)/1.5))

def curl_finger(side,finger,joint,degrees):
    name=f'nl_{finger}{joint}_{side}_wj'
    if name not in bones:return
    wrist=bones[f'kl_te_{side}_wj'].bone
    long=(bones[f'nl_naka_{side}_wj'].bone.head_local-wrist.head_local).normalized()
    width=(bones[f'nl_hito_{side}_wj'].bone.head_local-bones[f'nl_ko_{side}_wj'].bone.head_local).normalized()
    normal=long.cross(width).normalized()*(1 if side=='l' else -1)
    # Flex into the palm, rather than rotating all phalanges about world Y.
    axis=long.cross(normal).normalized()
    rotate(name,axis,degrees)

def leg(side,phase,stationary=False,target_override=None):
    # Heel-to-toe stance, followed by a low swing. Keep the sole level using IK.
    phase%=1
    if phase<.6:
        z=.18-.36*phase/.6;lift=0
    else:
        u=(phase-.6)/.4
        # Match backward stance velocity on both ends of the airborne arc.
        # A cosine swing stopped the foot abruptly at toe-off and heel strike.
        z=(2*u**3-3*u**2+1)*(-.18)+(u**3-2*u**2+u)*(-.24)+(-2*u**3+3*u**2)*.18+(u**3-u**2)*(-.24)
        lift=.065*math.sin(math.pi*u)**2
    if stationary:z=0;lift*=.65
    hip=f'j_momo_{side}_wj';knee=f'j_sune_{side}_wj';ankle=f'kl_asi_{side}_wj_co'
    bpy.context.view_layer.update();h=bones[hip].head.copy()
    target=Vector((.065 if side=='l' else -.065,.102+lift,-.046+z))
    if target_override is not None:target=Vector(target_override)
    a=.39;b=.413;d=target-h;length=min(d.length,a+b-.001);direction=d.normalized()
    pole=Vector((0,0,1));pole=(pole-direction*pole.dot(direction)).normalized()
    along=(a*a-b*b+length*length)/(2*length)
    bend=h+direction*along+pole*math.sqrt(max(0,a*a-along*along))
    aim(hip,knee,bend);aim(knee,ankle,target)
    foot=bones[ankle];matrix=foot.bone.matrix_local.copy();matrix.translation=foot.head.copy();foot.matrix=matrix
    bpy.context.view_layer.update()

def spring_wave(t,frequency,natural,damping):
    # Steady periodic response of a damped spring, baked without loop startup jumps.
    w=2*math.pi*frequency;wn=2*math.pi*natural
    gain=wn*wn/math.sqrt((wn*wn-w*w)**2+(2*damping*wn*w)**2)
    lag=math.atan2(2*damping*wn*w,wn*wn-w*w)
    return gain*math.sin(w*t-lag)

def pose(kind,t):
    if kind in ('bed_exit','bed_entry'):
        entering=kind=='bed_entry'
        # Independent entry beats: sit, settle weight, lower sideways, roll, draw.
        phase=(5-1.6*t/1.2 if t<1.2 else 3.4 if t<1.65 else
               3.4-(t-1.65)/.25 if t<1.9 else
               2.4-1.4*(t-1.9)/1.35 if t<3.25 else
               max(0,1-(t-3.25)/1.10)) if entering else t
        pose('lie_phone',0)
        sit=ease((phase-1)/1.4);stand=ease((phase-3.4)/1.6)
        for name in ('n_hara_c_wj_ex','j_kao_wj'):bones[name].location*=1-sit
        leg_sit=ease((phase-.35)/1.25) if entering else sit
        for side in ('l','r'):
            rotate(f'j_momo_{side}_wj',(1,0,0),-85*leg_sit*(1-stand))
            rotate(f'j_sune_{side}_wj',(1,0,0),85*leg_sit*(1-stand))
        if phase>2:
            for side in ('l','r'):
                names=[f'j_momo_{side}_wj',f'j_sune_{side}_wj',f'kl_asi_{side}_wj_co']
                before={n:bones[n].rotation_quaternion.copy() for n in names}
                # Keep both soles planted in the aisle while the pelvis shifts
                # back onto the mattress; match the runtime standing clearance.
                leg(side,0,True,((.065 if side=='l' else -.065),(.20988-.165*stand)/.44,(.28-.30*stand)/.44))
                blend=ease((phase-2)/.4)
                for n in names:bones[n].rotation_quaternion=before[n].slerp(bones[n].rotation_quaternion,blend)
        # Lean over the planted feet before the pelvis rises, then unfold.
        # Entry uses a softer braking lean while lowering onto the edge.
        lean=(18*math.sin(math.pi*stand) if entering else
              23*ease((phase-2.75)/.65)*(1-ease((phase-3.8)/1.2)))
        rotate('n_hara_b_wj_ex',(1,0,0),lean)
        rotate('n_hara_c_wj_ex',(1,0,0),8*(1-sit))
        rotate('j_kao_wj',(1,0,0),22*(1-sit)+6*sit+lean*.35)
        # Look toward the supporting side ahead of the torso, then settle.
        anticipate=(ease((t-.95)/.45)*(1-ease((t-2.2)/.8)) if entering else
                    ease((phase-.85)/.55)*(1-ease((phase-2.3)/.7)))
        for name,angle in [('j_kao_wj',-10),('n_hara_c_wj_ex',-4)]:
            b=bones[name];q=b.bone.matrix_local.to_quaternion()
            b.rotation_quaternion=(q.inverted()@Quaternion((0,1,0),math.radians(angle*anticipate))@q)@b.rotation_quaternion
        for side,sign in [('l',1),('r',-1)]:
            # The supporting arm releases after weight has shifted to the feet.
            brace=Vector((sign*.20,.74,.025 if side=='l' else .06))
            relaxed=Vector((sign*.18,.87,.025))
            target=brace.lerp(relaxed,ease((stand-.35)/.65))
            reading=Vector((.10,1.20,.29) if side=='l' else (.045,1.185,.245))
            pocket=Vector((sign*.18,.87,.04))
            if entering:
                if t<1.65:
                    target=relaxed.lerp(brace,ease((t-.2)/1.2))
                elif t<4:
                    # One forearm leads the lowering, the second arm follows.
                    target=brace+Vector((0,.035*math.sin(math.pi*ease((t-1.65)/2.35)),0))
                else:
                    reach=ease((t-4)/.35)
                    draw=ease((t-4.35)/1.65)
                    target=brace.lerp(pocket,reach).lerp(reading,draw)
                    target.z+=.045*math.sin(math.pi*draw)
            elif phase<1.2:
                stow=ease(phase/.75)
                target=reading.lerp(pocket,stow)
                target.z+=.045*math.sin(math.pi*stow)
                target=target.lerp(brace,ease((phase-.75)/.45))
            if entering and side=='l':
                # Keep the supporting wrist at a mattress-space anchor while
                # the pelvis and torso lower around it; do not carry it rigidly.
                lying=(Matrix.Rotation(math.pi/2,3,'Y')@Matrix.Rotation(-math.pi/2,3,'X')).to_quaternion()
                lateral=(Matrix.Rotation(math.pi,3,'Y')@Matrix.Rotation(-math.pi/2,3,'Z')).to_quaternion()
                seated=Matrix.Rotation(math.pi,3,'Y').to_quaternion()
                q=lying.slerp(lateral,ease(phase)).slerp(seated,sit)
                rotation=q.to_matrix()
                center=Vector((-.37,.25+.03*(1-sit)+.165*stand,1.05-.23*sit-.30*stand))
                origin=center-rotation@Vector((0,.39,0))
                anchor=rotation.transposed()@(Vector((-.55,.265,.86))-origin)/.44
                support=ease((t-1.2)/.45)*(1-ease((t-3.05)/.75))
                target=target.lerp(anchor,support)
            hand(side,target,relaxed=stand>.9)
            forearm=(bones[f'kl_te_{side}_wj'].head-bones[f'j_ude_{side}_wj'].head).normalized()
            relaxed_weight=ease((stand-.35)/.65)
            palm(side,Vector((0,0,1)).lerp(forearm,relaxed_weight),Vector((0,1,0)).lerp(Vector((0,0,1)),relaxed_weight),1)
            phone_blend=ease((t-4.35)/1.65) if entering else 1-ease(t/.75)
            palm(side,(0,.60,.80) if side=='l' else (.82,.35,.45),(0,.80,-.60),phone_blend)
        reading_hands(kind,t,phone_blend)
        wrist_helpers()
        bpy.context.view_layer.update()
        for side in ('l','r'):
            for src,dst in [(f'j_kata_{side}_wj_cu',f'n_skata_{side}_wj_cd_ex'),(f'j_momo_{side}_wj',f'n_momo_a_{side}_wj_cd_ex')]:
                b=bones[src];h=bones[dst];h.matrix=b.matrix@b.bone.matrix_local.inverted()@h.bone.matrix_local
        bpy.context.view_layer.update();return
    reset();wave=math.sin(2*math.pi*t)
    rotate('j_kata_l_wj_cu',(0,0,1),-52)
    rotate('j_kata_r_wj_cu',(0,0,1),52)
    rotate('n_hara_c_wj_ex',(1,0,0),.8*math.sin(t*math.pi))
    rotate('j_kao_wj',(0,1,0),4*math.sin(t*math.pi/2))
    if kind in ('walk','turn'):
        move('kl_kosi_etc_wj',(.008*wave,-.035+.008*math.cos(4*math.pi*t),0))
        rotate('kl_kosi_etc_wj',(0,0,1),1.5*wave)
        # Pelvis leads; upper torso follows with a small delay. Head counters
        # the torso instead of bobbing and turning as one rigid block.
        pelvis=bones['kl_kosi_etc_wj'];q=pelvis.bone.matrix_local.to_quaternion()
        pelvis.rotation_quaternion=(q.inverted()@Quaternion((0,1,0),math.radians(2*wave))@q)@pelvis.rotation_quaternion
        follow=math.sin(2*math.pi*t-.22)
        rotate('n_hara_c_wj_ex',(0,1,0),-3.5*follow)
        rotate('j_kao_wj',(0,1,0),1.5*follow)
        head=bones['j_kao_wj'];q=head.bone.matrix_local.to_quaternion()
        head.rotation_quaternion=(q.inverted()@Quaternion((0,0,1),math.radians(-.9*wave))@q)@head.rotation_quaternion
        leg('l',t,kind=='turn');leg('r',t+.5,kind=='turn')
        for side,sign in [('l',1),('r',-1)]:
            # Bent elbows and delayed hand swing, opposite the supporting leg.
            swing=-math.cos(2*math.pi*t-.25)*sign
            amplitude=1 if kind=='walk' else .45
            hand(side,(sign*(.18+.006*math.sin(2*math.pi*t-.4)),
                       .85+.018*amplitude*(.5+.5*swing),
                       .025+.09*amplitude*swing),relaxed=True)
    elif kind in ('phone','lie_phone','place_phone','pick_phone','sit_phone','sit_down','stand_up','seated_draw'):
        rotate('j_kao_wj',(1,0,0),16)
        hand('l',(.11,1.12,.25));hand('r',(.055,1.105,.205+.006*wave))
        if kind in ('sit_phone','sit_down','stand_up','seated_draw'):
            seated=ease((t-.8)/1.6) if kind=='sit_down' else 1-ease((t-.55)/1.65) if kind=='stand_up' else 1
            bones['kl_kosi_etc_wj'].location.y=-.50*seated
            for side in ('l','r'):
                leg(side,0,True,((.065 if side=='l' else -.065),.102,-.046+.25*seated))
            rotate('n_hara_b_wj_ex',(1,0,0),16*math.sin(math.pi*seated))
            draw=ease(t/1.65) if kind=='seated_draw' else 1 if kind=='sit_phone' else 0
            hip=.89-.50*seated
            hand('l',Vector((.18,hip,.04)).lerp(Vector((.11,.62,.25)),draw),relaxed=draw<.1)
            hand('r',Vector((-.18,hip,.04)).lerp(Vector((.055,.605,.205+.006*wave)),draw),relaxed=draw<.1)
        if kind=='lie_phone':
            # Raised head end: flex upper torso/neck instead of sinking the skull into it.
            rotate('n_hara_c_wj_ex',(1,0,0),8)
            rotate('j_kao_wj',(1,0,0),22)
            bpy.context.view_layer.update()
            for name in ('n_hara_c_wj_ex','j_kao_wj'):
                b=bones[name];m=b.matrix.copy();m.translation.z+=.04;b.matrix=m
                bpy.context.view_layer.update()
            hand('l',(.10,1.20,.29));hand('r',(.045,1.185,.245+.006*wave))
            rotate('j_momo_l_wj',(1,0,0),0);rotate('j_sune_l_wj',(1,0,0),3)
            rotate('j_momo_r_wj',(1,0,0),0);rotate('j_sune_r_wj',(1,0,0),5)
        if kind in ('place_phone','pick_phone'):
            progress=reach_amount(t)
            move('kl_kosi_etc_wj',(0,-.27*progress,.14*progress))
            rotate('n_hara_b_wj_ex',(1,0,0),25*progress)
            rotate('n_hara_c_wj_ex',(1,0,0),18*progress)
            rotate('kl_mune_b_wj',(1,0,0),12*progress)
            for side in ('l','r'):leg(side,.3,True)
            held=(kind=='place_phone' and t<1.8) or (kind=='pick_phone' and t>=1.8)
            rest=Vector((.11,1.12,.25)) if held else Vector((.18,.87,.025))
            hand('l',rest.lerp(Vector((0,.65163636,.395)),progress))
            # The free hand balances beside the thigh instead of reaching through the phone.
            hand('r',Vector((-.18,.87,.025)).lerp(Vector((-.21,.67,.15)),progress))
        if kind in ('place_phone','pick_phone'):
            reach=reach_amount(t)
            forearm=(bones['kl_te_l_wj'].head-bones['j_ude_l_wj'].head).normalized()
            start_long=Vector((0,.60,.80)) if held else forearm
            start_normal=Vector((0,.80,-.60)) if held else Vector((0,0,1))
            palm('l',start_long.lerp(Vector((0,0,1)),reach),start_normal.lerp(Vector((0,1,0)),reach))
    elif kind=='dance':
        # Manually matched to the visible 4:00--4:07 phrase: open, diagonal
        # reach, low gather, wide V, left sweep, then alternating chest gestures.
        # All channels share periodic cubic tangents, not stop/start key poses.
        phase=t%8;i=int(phase);u=phase-i
        def curve(values):
            p0=Vector(values[(i-1)%8]);p1=Vector(values[i]);p2=Vector(values[(i+1)%8]);p3=Vector(values[(i+2)%8])
            return (2*p1+(-p0+p2)*u+(2*p0-5*p1+4*p2-p3)*u*u+(-p0+3*p1-3*p2+p3)*u*u*u)*.5
        hips=[(.025,-.055,0),(.055,-.035,.006),(.055,-.055,0),(-.015,-.135,.025),
              (0,-.025,0),(-.055,-.075,.018),(-.03,-.045,0),(.045,-.045,.006)]
        move('kl_kosi_etc_wj',curve(hips))
        turn=curve([(4,0,0),(-6,0,0),(-10,0,0),(5,0,0),(0,0,0),(-22,0,0),(-8,0,0),(17,0,0)]).x
        rotate('kl_kosi_etc_wj',(0,0,1),-curve(hips).x*45)
        rotate('n_hara_c_wj_ex',(0,1,0),turn)
        rotate('j_kao_wj',(0,0,1),3*math.sin(math.pi*t/2-.25))
        keys=[((.35,1.04,.14),(.08,1.24,.26)),
              ((.34,1.30,.21),(-.34,1.16,.23)),
              ((.48,1.28,.06),(-.34,1.60,.04)),
              ((.015,.85,.28),(.08,.98,.30)),
              ((.37,1.57,.06),(-.37,1.57,.06)),
              ((-.23,1.20,.27),(-.41,1.06,.25)),
              ((-.10,1.35,.26),(-.17,.99,.27)),
              ((.30,1.32,.23),(.10,1.09,.30))]
        for side,j in [('l',0),('r',1)]:
            hand(side,curve([key[j] for key in keys]))
            forearm=(bones[f'kl_te_{side}_wj'].head-bones[f'j_ude_{side}_wj'].head).normalized()
            palm(side,forearm+Vector((0,.10*math.sin(math.pi*t/2-.35),.08)),(0,0,1),.7)
            # Brief bent-knee lift on the diagonal reach. The support foot
            # stays planted, and the lifted foot returns to the same contact.
            swing=math.sin(math.pi*(phase-1.45)/1.15)**2 if side=='r' and 1.45<phase<2.60 else 0
            leg(side,0,True,((.065 if side=='l' else -.065),.102+.11*swing,-.046-.055*swing))
    bpy.context.view_layer.update()
    # These deformation helpers are normally driven by the game's rig solver.
    # Their sibling hierarchy alone does not follow the animated upper limb.
    for side in ('l','r'):
        for source,destination in [(f'j_kata_{side}_wj_cu',f'n_skata_{side}_wj_cd_ex'),(f'j_momo_{side}_wj',f'n_momo_a_{side}_wj_cd_ex')]:
            b=bones[source];helper=bones[destination]
            helper.matrix=b.matrix@b.bone.matrix_local.inverted()@helper.bone.matrix_local
        bpy.context.view_layer.update()
    if kind!='lie_phone':
        for side in ('l','r'):
            b=bones[f'j_tail_{side}_000_wj'];position=b.matrix.translation.copy()
            matrix=b.bone.matrix_local.copy();matrix.translation=position;b.matrix=matrix
            if kind in ('walk','turn','dance'):
                for index in (1,4,8,12):
                    name=f'j_tail_{side}_{index:03d}_wj'
                    if name in bones:
                        rotate(name,(1,0,0),2.8*spring_wave(t-index*.012,2,3,.8))
                        b=bones[name];q=b.bone.matrix_local.to_quaternion()
                        b.rotation_quaternion=q.inverted()@Quaternion((0,0,1),math.radians(2.2*spring_wave(t-index*.025,1,2,.75)))@q@b.rotation_quaternion
    rotate('j_necktie_000_wj',(1,0,0),20)
    for index in range(1,5):
        name=f'j_necktie_{index:03d}_wj'
        if name in bones:rotate(name,(1,0,0),1.2*spring_wave(t-index*.035,1,2,.9))
    for side,sign in [('l',1),('r',-1)]:
        grip=0
        if side=='l' and kind in ('place_phone','pick_phone'):
            grip=.8*((1-ease((t-1.5)/.3)) if kind=='place_phone' else ease((t-1.8)/.3))
        fingers(side,t*4 if kind in ('walk','turn') else t,grip)
        if kind in ('idle','walk'):
            rotate(f'kl_te_{side}_wj',(0,1,0),sign*(3+3*math.sin(2*math.pi*t-.5)))
    if kind in ('phone','lie_phone','sit_phone','seated_draw'):
        reading_hands(kind,t,ease(t/1.65) if kind=='seated_draw' else 1)
    wrist_helpers()
    bpy.context.view_layer.update()

clips=[('idle',4),('walk',1),('phone',4),('lie_phone',4),('dance',8),('place_phone',4),('pick_phone',4),('sit_phone',4),('bed_entry',6),('turn',1),('bed_exit',5),('sit_down',3),('stand_up',3),('seated_draw',2)]
for name,seconds in clips:
    if only and name not in only:continue
    if 'DR_'+name in bpy.data.actions:bpy.data.actions.remove(bpy.data.actions['DR_'+name])
    rig.animation_data_create();rig.animation_data.action=bpy.data.actions.new('DR_'+name)
    for frame in range(seconds*30+1):
        pose(name,frame/30)
        for b in bones:
            b.keyframe_insert('rotation_quaternion',frame=frame+1,group=b.name)
            b.keyframe_insert('location',frame=frame+1,group=b.name)
    rig.animation_data.action.use_fake_user=True
    print('Baked',name,flush=True)
rig.animation_data.action=bpy.data.actions['DR_idle']
bpy.context.scene.render.fps=30;bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'miku-actions.blend'))
(root/'actions.json').write_text(json.dumps(dict(clips=clips,character_scale=.60,notes='Original bind skeleton; room-specific authored motions. Phone contact and transitions require runtime placement.'),indent=2))
print('Authored',len(clips),'actions')
