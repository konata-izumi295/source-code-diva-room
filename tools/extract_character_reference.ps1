. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
$lib=[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll'))
$root=Join-Path (Split-Path $PSScriptRoot) 'research\character'
$cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
try {
 $cpk.Load((Join-Path $DivaGameDir 'diva_main.cpk'))
 foreach($name in @('rom_ps4/rom/objset/mikitm000.farc','rom_ps4/rom/objset/mikitm001.farc','rom/bone_data.bin','rom/rob/mot_CMN.farc','rom_ps4/rom/rob/mot_db.farc')) {
  $stream=$cpk.Open($name,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
  $dest=[IO.File]::Create((Join-Path $root ([IO.Path]::GetFileName($name))))
  try {$stream.CopyTo($dest)}finally{$stream.Dispose();$dest.Dispose()}
 }
}finally{$cpk.Dispose()}
foreach($name in @('mikitm000.farc','mikitm001.farc','mot_CMN.farc','mot_db.farc')) {
 $f=New-Object MikuMikuLibrary.Archives.FarcArchive
 try {
  $f.Load((Join-Path $root $name))
  foreach($entry in $f.FileNames){
   Write-Output "$name : $entry"
   $s=$f.Open($entry,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream);$d=[IO.File]::Create((Join-Path $root $entry))
   try{$s.CopyTo($d)}finally{$s.Dispose();$d.Dispose()}
  }
 }finally{$f.Dispose()}
}
foreach($type in @('MikuMikuLibrary.Objects.Processing.Assimp.AssimpExporter','MikuMikuLibrary.Objects.ObjectSet','MikuMikuLibrary.Objects.Skin','MikuMikuLibrary.Motions.MotionSet','MikuMikuLibrary.Databases.BoneDatabase')){
 $t=$lib.GetType($type);"TYPE $type";$t.GetMethods() | Where-Object {$_.DeclaringType -eq $t} | ForEach-Object ToString
}

