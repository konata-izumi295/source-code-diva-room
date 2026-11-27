param([string]$MSBuildPath)
$ErrorActionPreference = 'Stop'
if (!$MSBuildPath) {
    $command = Get-Command MSBuild.exe -ErrorAction SilentlyContinue
    if ($command) { $MSBuildPath = $command.Source }
    else {
        $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
        if (!(Test-Path -LiteralPath $vswhere)) { throw 'MSBuild was not found. Use a Visual Studio Developer PowerShell or pass -MSBuildPath.' }
        $MSBuildPath = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1
    }
}
if (!$MSBuildPath) { throw 'Install Visual Studio C++ build tools with the v145 toolset and Windows SDK.' }
& $MSBuildPath (Join-Path $PSScriptRoot 'DivaRoom\DivaRoom.vcxproj') /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo
if ($LASTEXITCODE -ne 0) { throw "Build failed with exit code $LASTEXITCODE." }
Write-Output (Join-Path $PSScriptRoot 'build\DivaRoom.dll')
