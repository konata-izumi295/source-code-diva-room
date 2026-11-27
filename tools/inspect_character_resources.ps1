. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
$lib=[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll'))
$root=Join-Path (Split-Path $PSScriptRoot) 'research\character'
New-Item -ItemType Directory -Force $root | Out-Null
$cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
try {
 $cpk.Load((Join-Path $DivaGameDir 'diva_main.cpk'))
 $names=@($cpk.FileNames)
 $names | Where-Object {$_ -match 'itm_tbl|item_tbl|gm_module|chritm|cos_tbl'} | Set-Content (Join-Path $root 'item-table-names.txt')
 $names | Where-Object {$_ -match '(^|/)(mik|mot|bone|chara|module|cstm)' } | Set-Content (Join-Path $root 'resource-names.txt')
 $names | Where-Object {$_ -match '(^|/)(mik000|mik001|mikbod000|mikhair000|mikhed000|bone_data|mot_db|chara|module)' } | Select-Object -First 65
 $lib.GetTypes() | Where-Object {$_.FullName -match 'Skin|Bone|Motion|AssimpExporter|CpkArchive'} | ForEach-Object FullName | Set-Content (Join-Path $root 'library-types.txt')
} finally {$cpk.Dispose()}

