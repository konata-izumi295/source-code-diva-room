. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition -ne 'Desktop'){throw 'Run with Windows PowerShell 5.1'}
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$game=$DivaGameDir
$dest=Join-Path (Split-Path $PSScriptRoot) 'research\loading-assets'
New-Item -ItemType Directory -Force $dest | Out-Null
$cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
try {
 $cpk.Load((Join-Path $game 'diva_main.cpk'))
 foreach($file in $cpk.FileNames) {
  if($file -match '(^|/)aet_db.bin$') {
   $stream=$cpk.Open($file,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
   $db=New-Object MikuMikuLibrary.Databases.AetDatabase
   try {$db.Load($stream,$true);foreach($s in $db.AetSets){if($s.Id -eq 0x521 -or $s.Name -match 'load|wait|pause'){Write-Output "$file";Write-Output ($s | Format-List * | Out-String)}}} finally {$stream.Dispose()}
  }
  if($file -match '(aet|spr)_[^/]*(load|wait)[^/]*\.(bin|farc)$' -or $file -match '^rom_steam(_sp)?/rom/2d/(aet|spr)_(nswgam_cmn|nswgam_cmnbg|gam_cmn)\.(bin|farc)$') {
   Write-Output $file
   $out=Join-Path $dest ($file.Replace('/','_'))
   $stream=$cpk.Open($file,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
   $target=[IO.File]::Create($out)
   try {$stream.CopyTo($target)} finally {$stream.Dispose();$target.Dispose()}
   if($file -match 'aet_.*bin$') {
    $a=New-Object MikuMikuLibrary.Aets.AetSet
    try {$a.Load($out);foreach($scene in $a.Scenes){Write-Output "SCENE $($scene.Name) $($scene.Width)x$($scene.Height) frames $($scene.StartFrame)-$($scene.EndFrame)";foreach($comp in $scene.Compositions){foreach($l in $comp.Layers){if($l.Name -match 'loading|st_sp|ed_sp|now_|pause|resume|retry|return'){Write-Output "LAYER $($l.Name) $($l.StartFrame)-$($l.EndFrame)"}}}}}finally{$a.Dispose()}
   }
  }
 }
}finally{$cpk.Dispose()}
