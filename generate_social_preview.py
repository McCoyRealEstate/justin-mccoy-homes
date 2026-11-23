#!/usr/bin/env python3
"""Create social sharing preview using Pillow, without personal photos."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
p=Path('og-preview.png')
im=Image.new('RGB',(1200,630),'#142638')
d=ImageDraw.Draw(im)
d.rectangle((0,0,18,630),fill='#d5ad66')
d.line((75,460,1120,460),fill='#d5ad66',width=4)
def font(size,bold=True):
    paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for path in paths:
        if Path(path).exists():return ImageFont.truetype(path,size)
    return ImageFont.load_default()
d.text((78,150),'McCoy Real Estate',font=font(69),fill='white')
d.text((80,265),'NEW HOMES IN CENTRAL FLORIDA',font=font(33),fill='#d5ad66')
d.text((80,365),'Justin McCoy  |  Lennar New Home Consultant',font=font(26,False),fill='white')
d.text((80,510),'Jus3D.com',font=font(39),fill='white')
im.save(p,optimize=True)
print('Generated',p,p.stat().st_size)
