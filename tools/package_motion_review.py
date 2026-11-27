"""Package renderer-produced review frames without modifying any game assets."""
from pathlib import Path
from PIL import Image,ImageDraw
import csv,collections
root=Path(__file__).resolve().parents[1]/'build/room-view'
groups=collections.defaultdict(list)
for row in csv.DictReader((root/'review-frames.csv').open()):groups[int(row['clip'])].append(row)
for clip,rows in groups.items():
    frames=[]
    for row in rows:
        with Image.open(root/row['path']) as image:frame=image.resize((640,360))
        label='Bed to table' if clip==101 else f'Clip {clip}'
        ImageDraw.Draw(frame).text((8,8),f"{label} / {float(row['time']):.2f}s",fill='white',stroke_width=1,stroke_fill='black')
        frames.append(frame)
    frames[0].save(root/f'review-motion-{clip}.webp',save_all=True,append_images=frames[1:],duration=125,loop=0,quality=80)
    sheet=Image.new('RGB',(1600,180))
    for i in range(5):sheet.paste(frames[round(i*(len(frames)-1)/4)].resize((320,180)),(i*320,0))
    sheet.save(root/f'review-motion-{clip}.png')
print('Packaged clips:',sorted(groups))
