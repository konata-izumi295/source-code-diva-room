. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$game=$DivaGameDir
$dest=Join-Path $PSScriptRoot '..\research\original-assets'
New-Item -ItemType Directory -Force $dest | Out-Null
foreach($name in @('diva_main.cpk','diva_main_region.cpk')) {
    $cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
    try {
        $cpk.Load((Join-Path $game $name))
        foreach($file in $cpk.FileNames) {
            if($file -match 'aet_nswgam_menu|spr_nswgam_menu') {
                Write-Output "$name : $file"
                $out=Join-Path $dest ($name+'_'+$file.Replace('/','_').Replace('\','_'))
                $entry=$cpk.Open($file,[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
                $output=[IO.File]::Create($out)
                try { $entry.CopyTo($output) } finally { $output.Dispose(); $entry.Dispose() }
            }
        }
    } finally { $cpk.Dispose() }
}
