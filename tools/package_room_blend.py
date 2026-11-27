"""Make a portable copy in the mod; never edit the user's working project."""
import bpy, shutil
from pathlib import Path
root=Path(bpy.data.filepath).parent.parent
out=Path(__file__).resolve().parents[1]/'build'/'room-view'/'blender'
(out/'model').mkdir(parents=True,exist_ok=True)
shutil.copytree(root/'textures',out/'textures',dirs_exist_ok=True)
for image in bpy.data.images:
    if not image.filepath:continue
    source=Path(bpy.path.abspath(image.filepath))
    try:relative=source.relative_to(root)
    except ValueError:
        if image.packed_file:continue
        raise RuntimeError(f'External unpacked image requires packaging: {source}')
    image.filepath='//../'+relative.as_posix()
    if not image.packed_file:assert (out/relative).exists(),image.filepath
bpy.ops.wm.save_as_mainfile(filepath=str(out/'model'/'divaroom.blend'),relative_remap=False)
print('Portable Blender project and textures packaged; original untouched.')
