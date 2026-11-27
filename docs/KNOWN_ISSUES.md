# Known issues and handoff

## Audio: confirmed unresolved

The user confirmed silence on October 24, 2026 after the OGG and current DLL
were installed. `NativeLoading.h` uses the reviewed PlayMusic, StopMusic, and
MusicActive routines for channel 0. `RoomView.cpp` calls them at room entry,
while active, and on exit. The file is `rom/sound/bgm/divaroom.ogg`.
The converted file decodes as stereo 44.1 kHz, approximately 89.69 seconds.
The next investigation should distinguish signature readiness, native path/file
resolution, playback state, and mixer state. Do not mark the issue fixed merely
because callback mocks pass or the file exists. Looping is also unverified in-game.

## Animation and visuals

Wrist helpers now follow the wrist deformation, mirrored palms use separate
frames, and the phone interaction uses independent grip and touch poses.
The latest dance uses periodic curves, wider arm gestures, body weight changes,
and a short knee lift. These remain manual adaptations, not exact reproductions
of the reference animation. Walking turns, bed/chair transitions, finger contact,
and motion polish may still need work. Hair and tie secondary motion does not
have full body/furniture collision. Lighting and the original game shaders are
not fully reproduced.

## Scope still missing

- Other VOCALOIDs and purchased-module selection.
- Communication mode and its mechanics.
- Complete native stage/material integration.

## Validation recorded

Release/x64 DLL build passed. The standalone renderer passed with the final
actor. Hand deformation, loop seams, and phone handoff checks passed. The game
launched; room, bed phone pose, dance, and seated phone pose were observed.
The installed snapshot remains a preview, with the audio failure listed above.
