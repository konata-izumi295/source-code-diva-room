. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$root=Split-Path $PSScriptRoot
$a=New-Object MikuMikuLibrary.Aets.AetSet
$a.Load((Join-Path $root 'research\repaired-assets\aet_nswgam_menu_sp.bin'))
$s=$a.Scenes[0]; $main=$s.Compositions[$s.Compositions.Count-1]
$original=$main.Layers | Where-Object Name -eq 'chara_mainmenu_rhythmgame'
$custom=$main.Layers | Where-Object Name -eq 'chara_mainmenu_divaroom'
if(!$original -or !$custom -or $original.Item -eq $custom.Item){throw 'Character graphs not independent'}
foreach($name in @('rhythmgame','divaroom','customize','playlist','gallery','eshop','option')) {
 if(!($main.Layers | Where-Object Name -eq "nsw_menu_selector_$name")){throw "Missing selector $name"}
}
$ids=@($s.Videos | ForEach-Object {$_.Sources} | ForEach-Object {$_.Id})
foreach($id in @([uint32]2060726814,[uint32]1090781876,[uint32]52422,[uint32]52423)) {
 if($id -notin $ids){throw "Missing sprite $id"}
}
$archive=New-Object MikuMikuLibrary.Archives.FarcArchive
$archive.Load((Join-Path $root 'research\repaired-assets\spr_divaroom.farc'))
$stream=$archive.Open('spr_divaroom.bin',[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
$sprites=New-Object MikuMikuLibrary.Sprites.SpriteSet
$sprites.Load($stream,$true)
$sprites.Sprites | Format-List Name,Width,Height
Write-Output "OK: seven selectors, independent character graph, original and custom sprite references, serialized AET reload."
$sprites.Dispose();$stream.Dispose();$archive.Dispose();$a.Dispose()
