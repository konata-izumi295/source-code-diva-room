. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[void][Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll'))
$game=$DivaGameDir
$rows=@()
foreach($file in Get-ChildItem -LiteralPath $game -Filter '*.cpk') {
 $cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
 try {$cpk.Load($file.FullName);$rows+=@($cpk.FileNames|Where-Object {$_ -match 'shader|toon|npr|light_param'}|ForEach-Object {$file.Name+':'+$_})}finally{$cpk.Dispose()}
}
$rows|Set-Content (Join-Path (Split-Path $PSScriptRoot) 'research\character\shader-resources.txt')
$rows|Select-Object -First 35
