. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
$libdir=$MikuMikuModelDir
$lib=[Reflection.Assembly]::LoadFrom("$libdir\MikuMikuLibrary.dll")
[Reflection.Assembly]::LoadFrom("$libdir\AssimpNet.dll") | Out-Null
[Assimp.Unmanaged.AssimpLibrary]::Instance.LoadLibrary("$libdir\runtimes\win-x64\native\assimp.dll") | Out-Null
$root=Join-Path (Split-Path $PSScriptRoot) 'research\character'
$bone=New-Object MikuMikuLibrary.Databases.BoneDatabase;$bone.Load((Join-Path $root 'bone_data.bin'))
$obj=New-Object MikuMikuLibrary.Objects.ObjectSet;$obj.Load((Join-Path $root 'mikitm001_obj.bin'))
$obj.TryFixParentBoneInfos($bone)
$obj.Objects | ForEach-Object {"$($_.Name) meshes=$($_.Meshes.Count) bones=$($_.Skin.Bones.Count)"}
$bone.Skeletons | ForEach-Object {"Skeleton $($_.Name) bones=$($_.Bones.Count)"}
$obj.Objects | ForEach-Object {$_.Skin.Bones | Select-Object -First 12 | Format-List *}
$motdb=New-Object MikuMikuLibrary.Databases.MotionDatabase;$motdb.Load((Join-Path $root 'mot_db.bin'))
$motdb.MotionSets | Where-Object {$_.Name -eq 'CMN'} | ForEach-Object {$_.Motions | Select-Object Id,Name} | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $root 'common-motion-names.json')
"TEXTURES $($obj.TextureSet.Textures.Count)"
[MikuMikuLibrary.Objects.Processing.Assimp.AssimpExporter]::ExportToFile($obj,(Join-Path $root 'miku-body.dae'))

