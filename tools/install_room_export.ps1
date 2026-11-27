. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$stage=Join-Path $root 'research\room-export'
$destination=$DivaModDir
$blend=(Join-Path $DivaRoomSourceDir 'model\divaroom.blend')
$source=Get-Item -LiteralPath $blend
if($source.Length -ne 879610 -or $source.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss') -ne '2026-10-15 15:02:10') {
 throw 'The editable Blender source changed; re-read it before installation.'
}
$report=Get-Content (Join-Path $stage 'native-validation.json') -Raw | ConvertFrom-Json
if($report.objects -ne 47 -or $report.textures -ne 48){throw 'Native validation missing'}
if(-not $report.gameRenderVerified -or -not $report.auth3dRegistered){
 throw 'Room integration is not verified in-game. Keep exports in assets\pending-room, outside the active mod.'
}
$backup=Join-Path $root ('backups\room-before-cameras-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath $blend -Destination (Join-Path $backup 'divaroom.blend')
$package=Join-Path $stage 'package'
$installed=@()
foreach($file in Get-ChildItem -LiteralPath $package -Recurse -File) {
 $relative=$file.FullName.Substring($package.Length+1)
 $target=Join-Path $destination $relative
 if(Test-Path -LiteralPath $target) {
  $old=Join-Path $backup $relative
  New-Item -ItemType Directory -Force (Split-Path $old) | Out-Null
  Copy-Item -LiteralPath $target -Destination $old
 }
 New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
 Copy-Item -LiteralPath $file.FullName -Destination $target -Force
 $expected=(Get-FileHash -LiteralPath $file.FullName).Hash
 if((Get-FileHash -LiteralPath $target).Hash -ne $expected){throw "Copy mismatch: $target"}
 $installed+=@{path=$target;sha256=$expected}
}
Copy-Item -LiteralPath (Join-Path $stage 'divaroom_cameras.blend') -Destination $blend -Force
if((Get-FileHash -LiteralPath $blend).Hash -ne (Get-FileHash -LiteralPath (Join-Path $stage 'divaroom_cameras.blend')).Hash){throw 'Blender copy mismatch'}
@{backup=$backup;blend=$blend;files=$installed;runtimeSceneVerified=$false} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $stage 'installation.json')
Write-Output "Installed $($installed.Count) files. Blender saved with camera rigs. Backup: $backup"
