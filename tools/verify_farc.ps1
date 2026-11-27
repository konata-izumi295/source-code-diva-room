. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference = 'Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$paths = @(
    (Join-Path $DivaModDir ' Prototype\rom\2d\spr_divaroom.farc'),
    (Join-Path $PSScriptRoot '..\research\repaired-assets\spr_divaroom.farc')
)
foreach ($path in $paths) {
    $archive = New-Object MikuMikuLibrary.Archives.FarcArchive
    try {
        $archive.Load($path)
        $entry = $archive.Open('spr_divaroom.bin', [MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
        Write-Output "$path : OK ($($entry.Length) bytes)"
        $sprites = New-Object MikuMikuLibrary.Sprites.SpriteSet
        $sprites.Load($entry, $true)
        Write-Output "SpriteSet: $($sprites.Sprites.Count) sprites; $($sprites.TextureSet.Textures.Count) textures"
        $sprites.Dispose()
        $entry.Dispose()
    } catch {
        Write-Output "$path : FAILED ($($_.Exception.GetBaseException().Message))"
    } finally {
        $archive.Dispose()
    }
}
