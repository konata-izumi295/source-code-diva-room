. (Join-Path $PSScriptRoot 'project_paths.ps1')
$ErrorActionPreference='Stop'
[Reflection.Assembly]::LoadFrom((Join-Path $MikuMikuModelDir 'MikuMikuLibrary.dll')) | Out-Null
$root=Split-Path $PSScriptRoot
$original=New-Object MikuMikuLibrary.Aets.AetSet
$custom=New-Object MikuMikuLibrary.Aets.AetSet
$original.Load((Join-Path $root 'research\original-assets\diva_main.cpk_rom_steam_sp_rom_2d_aet_nswgam_menu.bin'))
$custom.Load((Join-Path $root 'research\repaired-assets\aet_nswgam_menu.bin'))
$o=$original.Scenes[0]; $c=$custom.Scenes[0]
if($o.Compositions.Count -ne 94 -or $c.Compositions.Count -ne 99) { throw 'Unexpected composition layout' }
$main=$o.Compositions[93]
# The native list now keeps two rows above the focus. Number the transform
# slots in spatial order, including the offscreen entry/exit rows.
$slots=@{'04_b'='00_a';'05_a'='01_a';'06_a'='02_a';'01_a'='03_a';'02_a'='04_a';'03_a'='05_a';'04_a'='06_a';'05_b'='07_a'}
foreach($i in 45..48) {
 foreach($layer in $o.Compositions[$i].Layers) {
  if($layer.Name -match '^p_menu_list(\d\d_[ab])$') {
   $layer.Name='p_menu_list'+$slots[$Matches[1]]
  }
 }
}
# Preserve every original Spanish composition, video and animation curve.
# Rebind the five added compositions to original shared backgrounds.
foreach($comp in @($c.Compositions | Select-Object -Skip 94)) {
 foreach($layer in $comp.Layers) {
  if($layer.Item -is [MikuMikuLibrary.Aets.Video]) {
   $idx=$c.Videos.IndexOf($layer.Item)
   if($idx -lt 103) { $layer.Item=$o.Videos[$idx] }
   if($idx -eq 103) {
    # The supplied selected sprite is 2048x682, not the 910x143 source
    # used by the animation template. Fit its actual bounds uniformly.
    foreach($key in $layer.Video.AnchorX.Keys) { $key.Value *= 2048.0/910.0 }
    foreach($key in $layer.Video.AnchorY.Keys) { $key.Value *= 682.0/143.0 }
    # Enlarge the selected logo 25% around its corrected center.
    $selectedScale=1.25*143.0/682.0
    foreach($key in $layer.Video.ScaleX.Keys) { $key.Value *= $selectedScale; $key.Tangent *= $selectedScale }
    foreach($key in $layer.Video.ScaleY.Keys) { $key.Value *= $selectedScale; $key.Tangent *= $selectedScale }
   }
   if($idx -eq 104) {
    foreach($key in $layer.Video.PositionX.Keys) { $key.Value += 90 }
   }
  } elseif($layer.Item -is [MikuMikuLibrary.Aets.Composition]) {
   $idx=$c.Compositions.IndexOf($layer.Item)
   if($idx -lt 94) { $layer.Item=$o.Compositions[$idx] }
  }
 }
}
$normal=$c.Compositions[93].Layers | Where-Object Name -eq 'nsw_menu_selector_divaroom'
$selected=$c.Compositions[44].Layers | Where-Object Name -eq 'nsw_menu_selector_divaroom_sel'
if(!$normal -or !$selected) { throw 'Missing DivaRoom layers' }
$selected.StartTime=1200
$selected.EndTime=1400
foreach($marker in $selected.Markers) { $marker.Frame += 1200 }
$main.Layers.Insert(18,$normal)
$o.Compositions[44].Layers.Add($selected)
# Keep the root composition last, as in the original serialized scene.
for($i=94;$i -lt 99;$i++) { $o.Compositions.Insert($o.Compositions.Count-1,$c.Compositions[$i]) }
for($i=103;$i -lt $c.Videos.Count;$i++) { $o.Videos.Add($c.Videos[$i]) }
# Read an independent graph so character changes cannot affect Rhythm Game.
$character=New-Object MikuMikuLibrary.Aets.AetSet
$character.Load((Join-Path $root 'research\original-assets\diva_main.cpk_rom_steam_sp_rom_2d_aet_nswgam_menu.bin'))
$cs=$character.Scenes[0]
$cloned=New-Object 'System.Collections.Generic.HashSet[int]'
function Register-CharacterComposition($comp) {
 $idx=$cs.Compositions.IndexOf($comp)
 if(!$cloned.Add($idx)){return}
 foreach($layer in $comp.Layers) {
  if($layer.Item -is [MikuMikuLibrary.Aets.Composition]) { Register-CharacterComposition $layer.Item }
  elseif($layer.Item -is [MikuMikuLibrary.Aets.Video]) {
   $video=$layer.Item
   $source=$video.Sources | Select-Object -First 1
   if($source.Name -eq 'NSWGAM_MENU_CHARA_MAINMENU_01' -or $source.Name -eq 'NSWGAM_MENU_CHARA_MAINMENU_01_DS') {
    $shadow=$source.Name.EndsWith('_DS')
    $width=1412; $height=1114; $id=[uint32]2060726814; $name='SPR_DIVAROOM_CHARA_MAINMENU_07'
    if($shadow){$width=1432; $height=1098; $id=[uint32]1090781876; $name='SPR_DIVAROOM_CHARA_MAINMENU_07_DS'}
    $sx=$width/[double]$video.Width; $sy=$height/[double]$video.Height
    $fit=[Math]::Min(1.0/$sx,1.0/$sy)
    foreach($k in $layer.Video.AnchorX.Keys){$k.Value*=$sx}
    foreach($k in $layer.Video.AnchorY.Keys){$k.Value*=$sy}
    foreach($p in @('ScaleX','ScaleY')){foreach($k in $layer.Video.$p.Keys){$k.Value*=$fit; $k.Tangent*=$fit}}
    $video.Width=$width; $video.Height=$height; $source.Id=$id; $source.Name=$name
    $o.Videos.Add($video)
   } else { $layer.Item=$o.Videos[$cs.Videos.IndexOf($video)] }
  }
 }
 $o.Compositions.Insert($o.Compositions.Count-1,$comp)
}
$chara=$cs.Compositions[93].Layers | Where-Object Name -eq 'chara_mainmenu_rhythmgame'
Register-CharacterComposition $chara.Item
$chara.Name='chara_mainmenu_divaroom'
# Distinct positions, retaining original floating curves and entry/exit timing.
$offsets=@{
 'chara_mainmenu_01_obj_03'=@(-70,-140)
 'chara_mainmenu_01_obj_03_ds'=@(-70,-140)
 'nswgam_menu_cube01_01.pic'=@(30,-210)
 'nswgam_menu_cube01_02.pic'=@(-75,100)
 'chara_mainmenu_01_obj_01_ds'=@(-75,100)
 'chara_mainmenu_01_obj_02_ds'=@(30,-210)
}
foreach($layer in $cs.Compositions[59].Layers) {
 if($offsets.ContainsKey($layer.Name)) {
  $delta=$offsets[$layer.Name]
  foreach($k in $layer.Video.PositionX.Keys){$k.Value+=$delta[0]}
  foreach($k in $layer.Video.PositionY.Keys){$k.Value+=$delta[1]}
 }
}
$main.Layers.Add($chara)
$output=Join-Path $root 'research\repaired-assets\aet_nswgam_menu_sp.bin'
$original.Save($output)
Write-Output $output
$original.Dispose(); $custom.Dispose(); $character.Dispose()
