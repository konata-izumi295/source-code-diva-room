. (Join-Path $PSScriptRoot 'project_paths.ps1')
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$a=New-Object MikuMikuLibrary.Aets.AetSet
$a.Load((Join-Path $PSScriptRoot '..\research\repaired-assets\aet_nswgam_menu_sp.bin'))
$s=$a.Scenes[0]
foreach($comp in $s.Compositions) {
 foreach($l in $comp.Layers) {
  if($l.Name -match 'divaroom') {
   Write-Output "$($l.Name) time=$($l.StartTime)..$($l.EndTime) offset=$($l.OffsetTime)"
   foreach($p in @('AnchorX','AnchorY','PositionX','PositionY','ScaleX','ScaleY','Opacity')) {
     Write-Output "$p : $(($l.Video.$p.Keys | ForEach-Object { "$($_.Frame):$($_.Value)" }) -join ',')"
   }
  }
 }
}
$a.Dispose()
