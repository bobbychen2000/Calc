import sys
from common import *
from PIL import Image, ImageDraw, ImageFont
def gridimg(name, x0=0, y0=0, x1=1290, y1=2796, scale=0.5, step=100, out=None):
    U = open(SP + 'uniq.txt').read().split()
    f = [u for u in U if name in u][0]
    im = Image.open(f).convert('RGB').crop((x0, y0, x1, y1))
    im = im.resize((int((x1 - x0) * scale), int((y1 - y0) * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 12)
    for x in range((x0 // step) * step, x1, step):
        if x < x0: continue
        X = (x - x0) * scale; d.line([(X, 0), (X, im.size[1])], fill=(255, 0, 255) if x % 500 == 0 else (0, 255, 255), width=1)
        for y in range((y0 // 200) * 200, y1, 200):
            if y >= y0: d.text((X + 2, (y - y0) * scale + 2), f'{x},{y}', fill=(255, 255, 0), font=fnt)
    for y in range((y0 // step) * step, y1, step):
        if y < y0: continue
        Y = (y - y0) * scale; d.line([(0, Y), (im.size[0], Y)], fill=(255, 0, 255) if y % 500 == 0 else (0, 255, 255), width=1)
    im.save(out or SP + f'grid_{name}.png')
if __name__ == '__main__':
    a = sys.argv[1:]
    gridimg(a[0], *[int(v) for v in a[1:5]], scale=float(a[5]) if len(a) > 5 else 0.5)
