"""Check walking clearance against the actual exported bed and actor envelope."""
import csv,json,math,sys
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
motion=Path(sys.argv[1]) if len(sys.argv)>1 else root/'build/room-view/motion-validation.csv'
envelope=np.array(json.loads((root/'research/character/walk-envelope.json').read_text())['hull_xz'])
vertices=[];name=''
for line in (root/'research/room-export/divaroom.obj').read_text().splitlines():
    if line.startswith('o '):name=line[2:]
    elif line.startswith('v ') and name in ('DR_ROOM_162','DR_ROOM_171','DR_ROOM_179'):
        vertices.append(list(map(float,line.split()[1:])))
v=np.array(vertices)[:,[0,2]];lo=v.min(0);hi=v.max(0)
bed=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])

def clearance(poly):
    edges=np.roll(poly,-1,axis=0)-poly
    axes=np.vstack((np.eye(2),np.column_stack((-edges[:,1],edges[:,0]))))
    axes/=np.linalg.norm(axes,axis=1)[:,None]
    a=poly@axes.T;b=bed@axes.T
    separated=np.any((a.max(0)<b.min(0))|(b.max(0)<a.min(0)))
    if not separated:return -min((a.max(0)-b.min(0)).min(),(b.max(0)-a.min(0)).min())
    def distance(points,polygon):
        end=np.roll(polygon,-1,axis=0);delta=end-polygon
        offset=points[:,None,:]-polygon[None,:,:]
        t=np.clip(np.sum(offset*delta,axis=2)/np.sum(delta*delta,axis=1),0,1)
        return np.linalg.norm(offset-t[:,:,None]*delta,axis=2).min()
    return min(distance(poly,bed),distance(bed,poly))

worst=(float('inf'),None);collisions=[];count=0
for row in csv.DictReader(motion.open()):
    if int(row['clip'])!=1:continue
    yaw=float(row['yaw']);c=math.cos(yaw);s=math.sin(yaw)
    poly=envelope@np.array([[c,-s],[s,c]])+np.array([float(row['x']),float(row['z'])])
    gap=float(clearance(poly));count+=1
    if gap<worst[0]:worst=(gap,float(row['time']))
    if gap<.005:collisions.append({'time':float(row['time']),'clearance':gap})
assert count>0,'No walking samples were checked'
report={'samples':count,'bed_min_xz':lo.tolist(),'bed_max_xz':hi.tolist(),
        'minimum_clearance':worst[0],'worst_time':worst[1],
        'clearance_margin':.005,'samples_below_margin':len(collisions),'examples':collisions[:12],
        'scope':'Conservative envelope of all walking/idle low vertices versus bed AABB; excludes intentional bed-entry/exit clips.'}
(root/'build/room-view/bed-approach-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
sys.exit(1 if collisions else 0)
