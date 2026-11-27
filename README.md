# DIVA ROOM — Source snapshot

Community preview by konata for Hatsune Miku: Project DIVA Mega Mix+.
This source snapshot matches the mod package dated October 24, 2026.
Documentation and code comments are in English. Existing in-game localization
strings are intentionally retained.

## Build the DLL

Requirements: Windows x64, Visual Studio 2026 C++ tools (`v145`), and Windows SDK.
Open `DivaRoom.slnx`, select **Release / x64**, and build. Alternatively:

```powershell
.\build.ps1
```

The result is `build/DivaRoom.dll`. The C++ build does not require Blender,
Python, MikuMikuLibrary, or the game executable. Close the game before replacing
the installed DLL. Keep it paired with the current `DRMIKU3` actor asset.
The other project configurations are inherited development configurations;
Release / x64 is the validated target.

## Project layout

- `DivaRoom/`: DLL, native menu/scene/loading/render adapters, input and room renderer.
- `tools/`: asset exporters, animation authoring, validation, and historical research scripts.
- `research/character/`: editable rig and current authored actions.
- `research/room-export/`: room geometry, material textures, and animation samples.
- `docs/`: architecture, asset workflow, and known limitations.

The matching mod package provides the full runtime assets and the editable room,
phone, and character Blender projects under `3dmodels`.

## Current status

The seventh menu entry, room, following camera, native loading/scene flow,
keyboard/controller input, pause, and Miku activity routine are implemented.
The latest snapshot includes revised wrist skinning, phone grip, and dance curves.
The OST playback integration is **not working in the latest user check**;
the room remains silent despite the included OGG and native playback adapter.
Animation quality, lighting, and secondary-motion collisions remain unfinished.
Other VOCALOIDs, purchased outfit selection, and communication mode are not implemented.

See `docs/DEVELOPMENT.md` for reproduction steps and `docs/KNOWN_ISSUES.md`
for the handoff. No game executable, full game archives, IDE caches, crash dumps,
private paths, or old backup DLLs are included in this source snapshot.
