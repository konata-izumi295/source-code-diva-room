"""Text A3DA export following ReDIVA KKdLib/a3da.cpp and a3da.hpp.
No runtime address assumptions. Registration/loading is a separate integration step.
"""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'research'/'room-export'
m=json.loads((ROOT/'manifest.json').read_text())
def native(v):return [v[0]*.1,v[2]*.1,-v[1]*.1]
def static(d,k,v):d[k+'.type']='1';d[k+'.value']=format(v,'.9g')
def curve(d,k,values):
    d[k+'.type']='2';d[k+'.max']='360';d[k+'.key.length']=str(len(values))
    d[k+'.ep_type_post']='2';d[k+'.ep_type_pre']='2'
    for i,v in enumerate(values):
        d[f'{k}.key.{i}.type']='1';d[f'{k}.key.{i}.data']=f'({i},{v:.9g})'
def transform(d,k,pos=(0,0,0)):
    for axis,v in zip('xyz',pos):static(d,k+'.trans.'+axis,v)
    for axis in 'xyz':static(d,k+'.rot.'+axis,0);static(d,k+'.scale.'+axis,1)
    static(d,k+'.visibility',1)
def write(name,d):
    d.update({'_.converter.version':'DivaRoom exporter 1','_.file_name':name,
              '_.property.version':'1','play_control.begin':'0','play_control.fps':'30','play_control.size':'360'})
    data='#A3DA__________\n'+'\n'.join(k+'='+d[k] for k in sorted(d))+'\n'
    assert len(data.splitlines()[0]+'\n')==16
    (ROOT/name).write_bytes(data.encode('utf8'))
for name,cam in m['cameras'].items():
    d={'camera_root.length':'1','camera_root.0.view_point.aspect':str(16/9),
       'camera_root.0.view_point.fov_is_horizontal':'1'}
    transform(d,'camera_root.0');transform(d,'camera_root.0.interest',native(cam['interest']))
    transform(d,'camera_root.0.view_point',native(cam['position']))
    static(d,'camera_root.0.view_point.fov',cam['horizontal_fov_radians'])
    static(d,'camera_root.0.view_point.roll',0)
    write(name.lower()+'.a3da',d)
d={'object.length':str(len(m['geometry_after'])),'object_list.length':str(len(m['geometry_after']))}
for i,name in enumerate(sorted(m['geometry_after'])):
    obj='DR_ROOM_'+name;k=f'object.{i}';d[k+'.name']=obj;d[k+'.uid_name']=obj;d[f'object_list.{i}']=obj
    transform(d,k)
    if obj in m['floating_offsets']:
        vals=m['floating_offsets'][obj]
        assert max(abs(a-b) for a,b in zip(vals[0],vals[-1]))<1e-5
        for axis,index in zip('xyz',range(3)):
            if any(abs(v[index])>1e-8 for v in vals):
                d.pop(k+'.trans.'+axis+'.value',None);curve(d,k+'.trans.'+axis,[v[index] for v in vals])
    if name=='292':
        p=k+'.tex_transform.0';d[k+'.tex_transform.length']='1';d[p+'.name']=m['material_textures'][name][0]
        d[p+'.offsetV']='true';curve(d,p+'.offsetV',[i/60 for i in range(361)])
write('dr_room_idle.a3da',d)
print('Exported 3 camera presets and 47-object scene, including 6 floating loops and stripe UV scroll.')
