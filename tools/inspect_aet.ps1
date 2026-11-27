. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
foreach($path in @('..\research\original-assets\diva_main.cpk_rom_steam_sp_rom_2d_aet_nswgam_menu.bin','..\research\repaired-assets\aet_nswgam_menu.bin')) {
 $a=New-Object MikuMikuLibrary.Aets.AetSet
 $a.Load((Join-Path $PSScriptRoot $path))
 Write-Output $path
 $s=$a.Scenes[0]
 $s | Format-List Name,StartFrame,EndFrame,Width,Height
 for($i=0;$i -lt $s.Compositions.Count;$i++) {
   $comp=$s.Compositions[$i]
   Write-Output "COMP $i ($($comp.Layers.Count))"
   foreach($l in $comp.Layers) { Write-Output "$($l.Name) $($l.StartFrame) $($l.EndFrame) $($l.Item.GetType().Name)" }
 }
 $a.Dispose()
}
[MikuMikuLibrary.Aets.Layer].GetProperties() | Select-Object Name,PropertyType | Format-Table -AutoSize
[MikuMikuLibrary.Aets.Video].GetProperties() | Select-Object Name,PropertyType | Format-Table -AutoSize
