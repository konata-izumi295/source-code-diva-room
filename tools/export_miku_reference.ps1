. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
$dir=$MikuMikuModelDir
[Reflection.Assembly]::LoadFrom("$dir\MikuMikuLibrary.dll")|Out-Null
[Reflection.Assembly]::LoadFrom("$dir\AssimpNet.dll")|Out-Null
[Assimp.Unmanaged.AssimpLibrary]::Instance.LoadLibrary("$dir\runtimes\win-x64\native\assimp.dll")|Out-Null
$root=Join-Path (Split-Path $PSScriptRoot) 'research\character'
$cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
$bone=New-Object MikuMikuLibrary.Databases.BoneDatabase;$bone.Load((Join-Path $root 'bone_data.bin'))
$combined=New-Object MikuMikuLibrary.Objects.ObjectSet
$combined.TextureSet=New-Object MikuMikuLibrary.Textures.TextureSet
try {
 $cpk.Load((Join-Path $DivaGameDir 'diva_main.cpk'))
 foreach($id in @('000','001','301','500')) {
  $s=$cpk.Open("rom_ps4/rom/objset/mikitm$id.farc",[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
  $f=New-Object MikuMikuLibrary.Archives.FarcArchive
  try {
   $f.Load($s,$true)
   foreach($name in $f.FileNames){
    $es=$f.Open($name,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream);$d=[IO.File]::Create((Join-Path $root $name))
    try{$es.CopyTo($d)}finally{$es.Dispose();$d.Dispose()}
   }
  }finally{$f.Dispose();$s.Dispose()}
  $part=New-Object MikuMikuLibrary.Objects.ObjectSet;$part.Load((Join-Path $root "mikitm${id}_obj.bin"))
  $part.TryFixParentBoneInfos($bone)
  foreach($obj in $part.Objects){
   if($id -ne '000' -or $obj.Name -eq 'mikitm000_atam_head_00__divskn'){$combined.Objects.Add($obj);Write-Output $obj.Name}
  }
  foreach($tex in $part.TextureSet.Textures){$combined.TextureSet.Textures.Add($tex)}
  foreach($texid in $part.TextureIds){$combined.TextureIds.Add($texid)}
 }
}finally{$cpk.Dispose()}
[MikuMikuLibrary.Objects.Processing.Assimp.AssimpExporter]::ExportToFile($combined,(Join-Path $root 'miku-original.fbx'))
[MikuMikuLibrary.Objects.Processing.Assimp.AssimpExporter]::ExportToFile($combined,(Join-Path $root 'miku-original.dae'))
Write-Output 'Original module assembled from native cos.0 = 500, 1, 301 plus base face 00.'
