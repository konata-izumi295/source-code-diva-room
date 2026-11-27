"""Adapt original pause sprites to the room's two actions, with localized labels."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import struct
root=Path(__file__).resolve().parents[1]
out=root/'build/room-view/room'
out.mkdir(parents=True,exist_ok=True)
labels={'sp':'Volver al menú','en':'Return to main menu','fr':'Retour au menu principal','ge':'Zum Hauptmenü','it':'Torna al menu principale','jp':'メインメニューへ戻る','kr':'메인 메뉴로 돌아가기','cn':'返回主菜单','tw':'返回主選單'}
fonts={'jp':'YuGothB.ttc','kr':'malgunbd.ttf','cn':'msyhbd.ttc','tw':'msjhbd.ttc'}
for region,label in labels.items():
    src=root/'research/pause-assets'/region
    def asset(name):return Image.open(src/(name+'.png')).convert('RGBA')
    font=ImageFont.truetype('C:/Windows/Fonts/'+fonts.get(region,'arialbd.ttf'),52)
    for selection in range(2):
        im=Image.new('RGBA',(1920,1080),(0,0,0,150))
        # The frame, backgrounds, and Resume lettering are extracted game assets.
        im.alpha_composite(asset('WIN_TOP_01'),(229,300))
        im.alpha_composite(asset('WIN_MIDDLE_01').resize((1462,408)),(229,336))
        im.alpha_composite(asset('WIN_BOTTOM_01'),(229,744))
        for row,y in enumerate((415,565)):
            selected=row==selection
            button=asset('TOPMENU_BTN_ON' if selected else 'TOPMENU_BTN_OFF')
            im.alpha_composite(button,((1920-button.width)//2,y))
            if row==0:
                text=asset('TOPMENU_TXT_01_ON' if selected else 'TOPMENU_TXT_01')
                im.alpha_composite(text,((1920-text.width)//2,y+(104-text.height)//2))
            else:
                draw=ImageDraw.Draw(im)
                draw.text((960,y+50),label,anchor='mm',font=font,fill='white' if selected else (140,140,145,255),stroke_width=2 if selected else 0,stroke_fill=(0,135,140,255))
        im.save(out/f'pause-{region}-{selection}.png')
        if region=='sp':im.save(root/f'build/room-view/pause-preview-{selection}.png')
print('Original pause sprites prepared for 9 regions; room-specific Return label localized.')
