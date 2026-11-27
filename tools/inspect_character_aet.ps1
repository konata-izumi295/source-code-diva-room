. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$a=New-Object MikuMikuLibrary.Aets.AetSet
$a.Load((Join-Path $PSScriptRoot '..\research\original-assets\diva_main.cpk_rom_steam_sp_rom_2d_aet_nswgam_menu.bin'))
$s=$a.Scenes[0]
foreach($i in @(54,55,59,60,93)) {
 foreach($l in $s.Compositions[$i].Layers) {
  if($i -eq 93 -and $l.Name -ne 'chara_mainmenu_rhythmgame'){continue}
  Write-Output "COMP $i : $($l.Name) time=$($l.StartTime)..$($l.EndTime) parent=$($l.Parent.Name)"
  if($l.Item -is [MikuMikuLibrary.Aets.Video]) { $l.Item | Format-List; $l.Item.Sources | Format-List }
  foreach($p in @('AnchorX','AnchorY','PositionX','PositionY','ScaleX','ScaleY')) { Write-Output "$p : $(($l.Video.$p.Keys | ForEach-Object { "$($_.Frame):$($_.Value)" }) -join ',')" }
 }
}
$a.Dispose()
