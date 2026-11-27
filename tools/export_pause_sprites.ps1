. (Join-Path $PSScriptRoot 'project_paths.ps1')
param([string]$Region='sp')
$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition -ne 'Desktop'){throw 'Windows PowerShell 5.1 required'}
$lib=$MikuMikuModelDir
[Reflection.Assembly]::LoadFrom("$lib\MikuMikuLibrary.dll") | Out-Null
Add-Type -AssemblyName System.Drawing
$dest=Join-Path (Split-Path $PSScriptRoot) 'research\pause-assets'
$dest=Join-Path $dest $Region
New-Item -ItemType Directory -Force $dest | Out-Null
$cpk=New-Object MikuMikuLibrary.Archives.CriMw.CpkArchive
$f=New-Object MikuMikuLibrary.Archives.FarcArchive
try {
 $cpk.Load((Join-Path $DivaGameDir 'diva_main.cpk'))
 $prefix=if($Region -eq 'jp'){'rom_steam'}else{"rom_steam_$Region"}
 $archive=$cpk.Open("$prefix/rom/2d/spr_nswgam_game.farc",[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
 $f.Load($archive,$true)
 $stream=$f.Open('spr_nswgam_game.bin',[MikuMikuLibrary.Archives.EntryStreamMode]::MemoryStream)
 $set=New-Object MikuMikuLibrary.Sprites.SpriteSet;$set.Load($stream,$true)
 $atlas=@{}
 foreach($sprite in $set.Sprites) {
  if($sprite.Name -notmatch 'TOPMENU_(BTN|TXT_01|TXT_05)|WIN_(TOP|MIDDLE|BOTTOM)_01|PAUSE'){continue}
  if(!$atlas.ContainsKey($sprite.TextureIndex)){$atlas[$sprite.TextureIndex]=[MikuMikuLibrary.Textures.Processing.TextureDecoder]::DecodeToBitmap($set.TextureSet.Textures[$sprite.TextureIndex]);$atlas[$sprite.TextureIndex].RotateFlip([Drawing.RotateFlipType]::RotateNoneFlipY)}
  $rect=New-Object Drawing.Rectangle ([int]$sprite.X),([int]$sprite.Y),([int]$sprite.Width),([int]$sprite.Height)
  $crop=$atlas[$sprite.TextureIndex].Clone($rect,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
  try{$crop.Save((Join-Path $dest ($sprite.Name+'.png')),[Drawing.Imaging.ImageFormat]::Png)}finally{$crop.Dispose()}
  Write-Output "$($sprite.Name) $($sprite.Width)x$($sprite.Height)"
 }
 foreach($bitmap in $atlas.Values){$bitmap.Dispose()}
}finally{$f.Dispose();$cpk.Dispose()}
