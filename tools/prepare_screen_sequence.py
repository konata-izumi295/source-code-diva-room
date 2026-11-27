import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
from pathlib import Path
from PIL import Image
import json
root=Path(__file__).resolve().parents[1]/'research'/'blender_animated'
folder=root/'textures'/'screen_frames'
folder.mkdir(parents=True,exist_ok=True)
source=(ROOM_SOURCE_DIR / 'textures/screen.gif')
im=Image.open(source)
durations=[];frame=1
for index in range(im.n_frames):
    im.seek(index)
    duration=im.info.get('duration',100)
    durations.append(duration)
    rgba=im.convert('RGBA')
    for _ in range(round(duration*30/1000)):
        rgba.save(folder/f'screen_{frame:04d}.png')
        frame+=1
(root/'screen_timing.json').write_text(json.dumps({'fps':30,'frames':frame-1,'source_durations_ms':durations},indent=2))
print(f'{frame-1} frames, original GIF timing preserved: {sum(durations)/1000}s')
