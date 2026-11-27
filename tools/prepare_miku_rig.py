"""Rebuild Assimp's mesh UVs from COLLADA, retain the imported native skeleton."""
import bpy,xml.etree.ElementTree as ET,json,math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]/'research/character'
bpy.ops.wm.open_mainfile(filepath=str(root/'miku-original.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
rig.name='DR_Miku'
for o in list(bpy.data.objects):
    if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
r=ET.parse(root/'miku-original.dae').getroot();ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
def find(e,p):return e.find(p,ns)
def all(e,p):return e.findall(p,ns)
def sources(e):
    out={}
    for s in all(e,'c:source'):
        a=find(s,'c:float_array'); stride=int(find(s,'c:technique_common/c:accessor').get('stride','1'))
        if a is not None:
            v=list(map(float,a.text.split()));out[s.get('id')]=[v[i:i+stride] for i in range(0,len(v),stride)]
        else:out[s.get('id')]=find(s,'c:Name_array').text.split()
    return out
images={e.get('id'):find(e,'c:init_from').text for e in all(r,'c:library_images/c:image')}
materials={}
for e in all(r,'c:library_effects/c:effect'):
    tex=find(e,'.//c:diffuse/c:texture');color=find(e,'.//c:diffuse/c:color')
    mat=bpy.data.materials.new('DR_'+e.get('id'));mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.65
    if tex is not None:
        sampler=tex.get('texture');source=find(e,f'.//c:newparam[@sid="{sampler}"]/c:sampler2D/c:source').text
        imageid=find(e,f'.//c:newparam[@sid="{source}"]/c:surface/c:init_from').text
        im=bpy.data.images.load(str(root/images[imageid]),check_existing=True)
        node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=im
        mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
        mat.node_tree.links.new(node.outputs['Alpha'],bs.inputs['Alpha'])
        mat.surface_render_method='DITHERED'
    elif color is not None:bs.inputs['Base Color'].default_value=list(map(float,color.text.split()))
    materials[e.get('id')]=mat
matrefs={m.get('id'):find(m,'c:instance_effect').get('url')[1:] for m in all(r,'c:library_materials/c:material')}
controllers={}
for co in all(r,'c:library_controllers/c:controller'):
    sk=find(co,'c:skin');src=sources(sk);vw=find(sk,'c:vertex_weights');inputs=all(vw,'c:input')
    ji=next(i for i in inputs if i.get('semantic')=='JOINT');wi=next(i for i in inputs if i.get('semantic')=='WEIGHT')
    names=src[ji.get('source')[1:]];weights=src[wi.get('source')[1:]]
    seq=list(map(int,find(vw,'c:v').text.split()));counts=list(map(int,find(vw,'c:vcount').text.split()))
    n=max(int(i.get('offset')) for i in inputs)+1;cursor=0;groups=[]
    for count in counts:
        row=[]
        for _ in range(count):
            row.append((names[seq[cursor+int(ji.get('offset'))]],weights[seq[cursor+int(wi.get('offset'))]][0]));cursor+=n
        groups.append(row)
    controllers[co.get('id')]=(sk.get('source')[1:],groups)
geoms={g.get('id'):g for g in all(r,'c:library_geometries/c:geometry')}
for node in all(r,'.//c:visual_scene//c:node'):
    inst=find(node,'c:instance_controller')
    if inst is None:continue
    geom,groups=controllers[inst.get('url')[1:]];mesh=find(geoms[geom],'c:mesh');src=sources(mesh)
    vertices=find(mesh,'c:vertices');possrc=find(vertices,'c:input').get('source')[1:];positions=src[possrc]
    poly=find(mesh,'c:polylist');inputs=all(poly,'c:input');stride=max(int(i.get('offset')) for i in inputs)+1
    vi=int(next(i for i in inputs if i.get('semantic')=='VERTEX').get('offset'))
    ti=next((i for i in inputs if i.get('semantic')=='TEXCOORD'),None)
    data=list(map(int,find(poly,'c:p').text.split()));counts=list(map(int,find(poly,'c:vcount').text.split()))
    faces=[];uvs=[];cursor=0
    for count in counts:
        faces.append([data[cursor+k*stride+vi] for k in range(count)])
        for k in range(count):uvs.append(src[ti.get('source')[1:]][data[cursor+k*stride+int(ti.get('offset'))]][:2] if ti is not None else (0,0))
        cursor+=count*stride
    me=bpy.data.meshes.new(node.get('name') or geom);me.from_pydata(positions,[],faces);me.update()
    obj=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(obj);obj.matrix_world=rig.matrix_world.copy()
    uv=me.uv_layers.new(name='UVMap')
    for loop,coord in zip(me.loops,uvs):uv.data[loop.index].uv=coord
    for p in me.polygons:p.use_smooth=True
    bind=find(inst,'.//c:instance_material');obj.data.materials.append(materials[matrefs[bind.get('target')[1:]]])
    vgs={}
    for i,row in enumerate(groups):
        for name,weight in row:
            if name not in vgs:vgs[name]=obj.vertex_groups.new(name=name)
            if weight>0:vgs[name].add([i],weight,'REPLACE')
    mod=obj.modifiers.new('Native skeleton','ARMATURE');mod.object=rig
    obj.parent=rig;obj.matrix_parent_inverse=rig.matrix_world.inverted()
# Native skin chunks omit parents outside their own weighted subset. Reconnect
# those existing bones without changing their bind transforms.
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
links={'n_hara_b_wj_ex':'kl_kosi_etc_wj','n_hara_c_wj_ex':'n_hara_b_wj_ex','kl_mune_b_wj':'n_hara_c_wj_ex',
       'kl_te_l_wj':'n_sude_b_l_wj_ex','kl_te_r_wj':'n_sude_b_r_wj_ex'}
for child,parent in links.items():rig.data.edit_bones[child].parent=rig.data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'miku-rig.blend'))
print('Rebuilt',len([o for o in bpy.data.objects if o.type=='MESH']),'meshes with validated COLLADA indices; rig matrix',list(map(list,rig.matrix_world)))
