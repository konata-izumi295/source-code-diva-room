. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition -ne 'Desktop'){throw 'Use powershell.exe (Windows PowerShell 5.1). This MML build needs .NET Framework for complete compressed archive reads.'}
$lib=$MikuMikuModelDir
[Reflection.Assembly]::LoadFrom("$lib\MikuMikuLibrary.dll") | Out-Null
[Reflection.Assembly]::LoadFrom("$lib\AssimpNet.dll") | Out-Null
[Assimp.Unmanaged.AssimpLibrary]::Instance.LoadLibrary("$lib\runtimes\win-x64\native\assimp.dll") | Out-Null
$root=Join-Path (Split-Path $PSScriptRoot) 'research\room-export'
$o=[MikuMikuLibrary.Objects.Processing.Assimp.AssimpImporter]::ImportFromFile((Join-Path $root 'divaroom.obj'))
Write-Output "Imported $($o.Objects.Count) objects / $($o.TextureSet.Textures.Count) textures"
if($o.Objects.Count -ne 47 -or $o.TextureSet.Textures.Count -eq 0) {throw 'Incomplete imported room'}
for($i=0;$i -lt $o.Objects.Count;$i++) {$o.Objects[$i].Id=$i}
$o.Format=[MikuMikuLibrary.IO.BinaryFormat]::FT
$o.Endianness=[MikuMikuLibrary.IO.Endianness]::Little
$o.TextureSet.Format=[MikuMikuLibrary.IO.BinaryFormat]::FT
$o.TextureSet.Endianness=[MikuMikuLibrary.IO.Endianness]::Little
$o.Save((Join-Path $root 'divaroom_obj.bin'))
$o.TextureSet.Save((Join-Path $root 'divaroom_tex.bin'))
$check=New-Object MikuMikuLibrary.Objects.ObjectSet
$check.Load((Join-Path $root 'divaroom_obj.bin'))
Write-Output "Reloaded $($check.Objects.Count) objects / Format $($check.Format)"
$game=$DivaGameDir
$used=[Collections.Generic.HashSet[uint32]]::new()
$texUsed=[Collections.Generic.HashSet[uint32]]::new()
$dbPaths=@((Join-Path (Split-Path $root) 'native-export\obj_db.bin'))+@(Get-ChildItem "$game\mods" -Recurse -Filter '*obj_db.bin' | Where-Object FullName -notlike '*\Diva Room\*' | ForEach-Object FullName)
foreach($path in $dbPaths) {
 $db=New-Object MikuMikuLibrary.Databases.ObjectDatabase;$db.Load($path)
 foreach($set in $db.ObjectSets) {$null=$used.Add($set.Id)}
}
$texPaths=@((Join-Path (Split-Path $root) 'native-export\tex_db.bin'))+@(Get-ChildItem "$game\mods" -Recurse -Filter '*tex_db.bin' | Where-Object FullName -notlike '*\Diva Room\*' | ForEach-Object FullName)
foreach($path in $texPaths) {
 $db=New-Object MikuMikuLibrary.Databases.TextureDatabase;$db.Load($path)
 foreach($t in $db.Textures) {$null=$texUsed.Add($t.Id)}
}
$setId=62000
while($used.Contains($setId)) {$setId++;if($setId -gt 65534){throw 'No free reserved object-set ID'}}
$odb=New-Object MikuMikuLibrary.Databases.ObjectDatabase
$info=New-Object MikuMikuLibrary.Databases.ObjectSetInfo
$info.Name='DIVAROOM_ROOM';$info.Id=$setId;$info.FileName='divaroom_obj.bin';$info.TextureFileName='divaroom_tex.bin';$info.ArchiveFileName='divaroom_room.farc'
foreach($obj in $o.Objects) {
 $oi=New-Object MikuMikuLibrary.Databases.ObjectInfo;$oi.Name=$obj.Name;$oi.Id=$obj.Id;$info.Objects.Add($oi)
}
$odb.ObjectSets.Add($info)
$tdb=New-Object MikuMikuLibrary.Databases.TextureDatabase
foreach($tex in $o.TextureSet.Textures) {
 if($texUsed.Contains($tex.Id)) {throw "Texture ID collision: $($tex.Name)"}
 $ti=New-Object MikuMikuLibrary.Databases.TextureInfo;$ti.Name=$tex.Name;$ti.Id=$tex.Id;$tdb.Textures.Add($ti)
}
$package=Join-Path $root 'package'
$objdir=Join-Path $package 'rom\objset';$authdir=Join-Path $package 'rom\auth_3d'
New-Item -ItemType Directory -Force $objdir,$authdir | Out-Null
$odb.Save((Join-Path $objdir 'mod_obj_db.bin'));$tdb.Save((Join-Path $objdir 'mod_tex_db.bin'))
function Pack($path,$files) {
 $f=New-Object MikuMikuLibrary.Archives.FarcArchive
 try {
  $f.IsCompressed=$true;$f.Alignment=16
  foreach($file in $files) {$f.Add([IO.Path]::GetFileName($file),$file,[MikuMikuLibrary.Archives.ConflictPolicy]::RaiseError)}
  $f.Save($path)
 } finally {$f.Dispose()}
}
Pack (Join-Path $objdir 'divaroom_room.farc') @((Join-Path $root 'divaroom_obj.bin'),(Join-Path $root 'divaroom_tex.bin'))
Pack (Join-Path $authdir 'DIVAROOM_ROOM.farc') @(Get-ChildItem $root -Filter '*.a3da' | ForEach-Object FullName)
$report=@{objectSetId=$setId;objects=$o.Objects.Count;textures=$o.TextureSet.Textures.Count;objectDatabasesChecked=$dbPaths.Count;textureDatabasesChecked=$texPaths.Count;gameRenderVerified=$false;auth3dRegistered=$false}
$dbCheck=New-Object MikuMikuLibrary.Databases.ObjectDatabase;$dbCheck.Load((Join-Path $objdir 'mod_obj_db.bin'))
if($dbCheck.ObjectSets[0].Objects.Count -ne 47 -or $dbCheck.ObjectSets[0].Id -ne $setId){throw 'Database round trip mismatch'}
$f=New-Object MikuMikuLibrary.Archives.FarcArchive;$f.Load((Join-Path $objdir 'divaroom_room.farc'))
try {
 $stream=$f.Open('divaroom_obj.bin',[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
 $round=New-Object MikuMikuLibrary.Objects.ObjectSet;$round.Load($stream,$true)
 if($round.Objects.Count -ne 47){throw 'Archive round trip mismatch'}
 $stream=$f.Open('divaroom_tex.bin',[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
 $roundtex=New-Object MikuMikuLibrary.Textures.TextureSet;$roundtex.Load($stream,$true)
 if($roundtex.Textures.Count -ne 48){throw 'Texture round trip mismatch'}
} finally {$f.Dispose()}
$report | ConvertTo-Json | Set-Content (Join-Path $root 'native-validation.json')
Write-Output ($report | ConvertTo-Json -Compress)
