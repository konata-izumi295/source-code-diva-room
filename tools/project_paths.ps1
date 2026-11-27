# Override these locations before running optional asset/research tools.
$DivaGameDir = if ($env:DIVA_GAME_DIR) { $env:DIVA_GAME_DIR } else { 'C:\Program Files (x86)\Steam\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus' }
$DivaModDir = if ($env:DIVA_MOD_DIR) { $env:DIVA_MOD_DIR } else { Join-Path $DivaGameDir 'mods\Diva Room' }
$MikuMikuModelDir = if ($env:MIKUMIKUMODEL_DIR) { $env:MIKUMIKUMODEL_DIR } else { Join-Path $env:USERPROFILE 'Downloads\MikuMikuModel' }
$DivaRoomSourceDir = if ($env:DIVA_ROOM_SOURCE_DIR) { $env:DIVA_ROOM_SOURCE_DIR } else { Join-Path $DivaModDir '3dmodels\divaroom' }
