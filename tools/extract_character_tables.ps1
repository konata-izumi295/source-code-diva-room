. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$root=Join-Path (Split-Path $PSScriptRoot) 'research\character'
$c=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
try {
 $c.Load((Join-Path $DivaGameDir 'diva_main.cpk'))
 foreach($name in @('rom_ps4_patch/rom/chritm_prop.farc','rom_ps4/rom/gm_module_tbl.farc')) {
  $s=$c.Open($name,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
  $f=New-Object MikuMikuLibrary.Archives.FarcArchive
  try {
   $f.Load($s,$true)
   foreach($entry in $f.FileNames){
    $es=$f.Open($entry,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream);$d=[IO.File]::Create((Join-Path $root $entry))
    try{$es.CopyTo($d)}finally{$es.Dispose();$d.Dispose()};Write-Output $entry
   }
  }finally{$f.Dispose();$s.Dispose()}
 }
}finally{$c.Dispose()}
