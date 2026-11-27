. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$root=Join-Path (Split-Path $PSScriptRoot) 'research\native-export'
$cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
try {
 $cpk.Load((Join-Path $DivaGameDir 'diva_main.cpk'))
 foreach($path in @('rom_steam/rom/objset/obj_db.bin','rom_steam/rom/objset/tex_db.bin','rom_ps4/rom/objset/mikitm000.farc')) {
  $s=$cpk.Open($path,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
  $out=[IO.File]::Create((Join-Path $root ([IO.Path]::GetFileName($path))))
  try {$s.CopyTo($out)} finally {$out.Dispose();$s.Dispose()}
 }
} finally {$cpk.Dispose()}
$db=New-Object MikuMikuLibrary.Databases.ObjectDatabase
$db.Load((Join-Path $root 'obj_db.bin'))
$db.ObjectSets | Select-Object -First 4 | Format-List
$f=New-Object MikuMikuLibrary.Archives.FarcArchive
$f.Load((Join-Path $root 'mikitm000.farc'))
try {
 $f.FileNames
 $s=$f.Open('mikitm000_obj.bin',[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
 $o=New-Object MikuMikuLibrary.Objects.ObjectSet
 $o.Load($s,$true)
 $o | Select-Object Format,Endianness
 $o.Objects | Select-Object -First 2 Name,Id,BoundingSphere
} finally {$f.Dispose()}
