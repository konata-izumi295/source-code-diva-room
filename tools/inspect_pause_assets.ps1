. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition -ne 'Desktop'){throw 'Windows PowerShell 5.1 required'}
$lib=$MikuMikuModelDir
[Reflection.Assembly]::LoadFrom("$lib\MikuMikuLibrary.dll") | Out-Null
$dest=Join-Path (Split-Path $PSScriptRoot) 'research\pause-assets'
New-Item -ItemType Directory -Force $dest | Out-Null
$cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
try {
 $cpk.Load((Join-Path $DivaGameDir 'diva_main.cpk'))
 foreach($file in @('rom_steam_sp/rom/2d/aet_nswgam_game.bin','rom_steam_sp/rom/2d/spr_nswgam_game.farc')) {
  $s=$cpk.Open($file,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
  $o=[IO.File]::Create((Join-Path $dest ([IO.Path]::GetFileName($file))))
  try{$s.CopyTo($o)}finally{$s.Dispose();$o.Dispose()}
 }
}finally{$cpk.Dispose()}
$a=New-Object MikuMikuLibrary.Aets.AetSet;$a.Load((Join-Path $dest 'aet_nswgam_game.bin'))
foreach($scene in $a.Scenes) {
 for($i=0;$i -lt $scene.Compositions.Count;$i++) {
  foreach($layer in $scene.Compositions[$i].Layers) {
   if($layer.Name -match 'pause_win|gam_btn_resume|gam_btn_back') {
    Write-Output "COMPOSITION $i"
    $layer | Format-List Name,StartTime,EndTime,OffsetTime,TimeScale,Markers
    Write-Output "ITEM $($layer.Item.GetType().Name) $($scene.Compositions.IndexOf($layer.Item))"
    if($layer.Item -is [MikuMikuLibrary.Aets.Composition]){foreach($l in $layer.Item.Layers){Write-Output "  $($l.Name) $($l.StartTime)-$($l.EndTime) type=$($l.Item.GetType().Name)";if($l.Item -is [MikuMikuLibrary.Aets.Video]){$l.Item | Format-List *; $l.Item.Sources | Format-List *}}}
   }
  }
 }
}
$a.Dispose()
[MikuMikuLibrary.Textures.Processing.TextureDecoder].GetMethods() | Where-Object Name -match Decode | ForEach-Object ToString
[MikuMikuLibrary.Sprites.Sprite].GetProperties() | Select-Object Name,PropertyType
