# Development and asset workflow

## Native integration

`NativeMenu.h` adds the seventh option without replacing the original six.
`MenuDescription.h` retains the existing regional strings. `NativeScene.h`
adds the room state and uses the native menu's confirmation/exit flow.
`NativeLoading.h` connects the original WAIT_SCREEN loading UI and audio hooks.
`NativeRender.h` schedules the custom D3D11 pass before native sprites/dialogs.
`RoomView.cpp` handles room lifetime, pause, resources, and rendering.
`RoomActor.h` handles activity timing, paths, pose blending, phone placement,
camera targets, and secondary motion. `tools/animate_miku.py` authors bone motion.

The room is a custom renderer inside the game's scene flow. It is not a complete
native OBJ/AUTH_3D stage. Never treat the experimental native-stage installer as
the current room installation path; its validation guard is deliberately retained.

Native patch-site headers contain bytes reviewed against the executable with SHA-256:
`6f4df714c28515c93b3023e7d6dafa9095dd8835f762d54db1726fb8bc04504d`.
Keep signature checks intact. Do not guess replacement addresses for other versions.

## Tool paths and dependencies

Python/Blender tools use `tools/project_paths.py`; PowerShell asset tools use
`tools/project_paths.ps1`. Optional overrides are `DIVA_GAME_DIR`, `DIVA_MOD_DIR`,
`DIVA_ROOM_SOURCE_DIR`, and `MIKUMIKUMODEL_DIR`. Set these to your own paths.
The C++ build needs none of these overrides.

Animation tools were run with Blender 5.2.2. General Python tools use Python 3
with `numpy` and `Pillow`; Blender supplies its own `bpy`, `mathutils`, and NumPy.
Asset extraction tools use a separately installed MikuMikuLibrary/MikuMikuModel.
Run its .NET Framework scripts in Windows PowerShell 5.1 (`powershell.exe`).
The Java `Inspect*.java` files are Ghidra scripts, not DLL dependencies.

Historical inspection/extraction scripts may require intermediate files from
your own game extraction or the original menu artwork archive. They are retained
as development source, not presented as a one-click asset rebuild pipeline.

## Character workflow

Set `DIVA_MOD_DIR` to the complete mod folder so the exporter can find the phone.
From the source root, with Blender available on PATH:

```powershell
blender -b --python tools/animate_miku.py -- --only dance
blender -b --python tools/verify_miku_hands.py
blender -b --python tools/verify_miku_gait.py
blender -b --python tools/verify_bed_support.py
blender -b --python tools/export_miku_actor.py
```

The editable output is `research/character/miku-actions.blend`.
The runtime output is `build/room-view/room/miku.actor`.
Omit `--only dance` to regenerate all clips from `miku-rig.blend`.
Blender can return exit code zero after a Python error: inspect output for a
traceback and require each validation script's PASS result.

## Room and tests

The packaged room inputs can be rebuilt with `python tools/build_room_view.py`
after setting `DIVA_MOD_DIR`. The GIF comes from the mod's editable room textures.
The editable room project is in the mod, `3dmodels/divaroom/model/divaroom.blend`.

Copy runtime assets for the standalone renderer, then compile and run:

```powershell
.\tools\stage_test_assets.ps1 -ModPath 'C:\path\to\Diva Room'
MSBuild tools/test_room_renderer.vcxproj /p:Configuration=Release /p:Platform=x64
Push-Location build/room-view
.\TestRoomRenderer.exe
Pop-Location
MSBuild tools/test_native_scene.vcxproj /p:Configuration=Release /p:Platform=x64
```

Renderer tests cover graphics-state restoration, room lifetime, pause/resume,
reentry, motion continuity, and the music callback lifecycle. Mocked audio tests
do not prove native playback. Native function calls, physical controller behavior,
and artistic quality still need in-game checks.

## Reference and credits

Mod project: konata. Animation reference:
https://www.youtube.com/watch?v=LKQt4gv4gKI
Room reference supplied for remodeling:
https://sketchfab.com/3d-models/prj-diva-house-2ea654d820bd4928a509fad78b660bab
External tools and format references:
https://github.com/blueskythlikesclouds/MikuMikuLibrary
https://github.com/blueskythlikesclouds/DivaModLoader
https://github.com/korenkonder/ReDIVA

No new source-code license is assigned by this snapshot. Game-derived assets
and external tools retain their existing ownership and terms.
