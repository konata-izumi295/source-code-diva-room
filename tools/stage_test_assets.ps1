param([string]$ModPath = $env:DIVA_MOD_DIR)
$ErrorActionPreference = 'Stop'
if (!$ModPath) { throw 'Pass -ModPath with the full path to the packaged or installed Diva Room folder.' }
if (!(Test-Path -LiteralPath (Join-Path $ModPath 'room\miku.actor'))) { throw 'The mod runtime assets were not found.' }
$target = Join-Path (Split-Path $PSScriptRoot) 'build\room-view'
New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ModPath 'room') -Destination $target -Recurse -Force
Write-Output "Test assets copied to $target. The game installation was not modified."
