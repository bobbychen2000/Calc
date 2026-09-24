import sys
from PIL import Image, ImageDraw
from common import *
U = open(SP + 'uniq.txt').read().split()
def zg(n, cx, cy, half=60, z=4, step=10, out=None):
    im = Image.open([u for u in U if n in u][0]).convert('RGB')
    x0, y0 = cx - half, cy - half
    c = im.crop((x0, y0, x0 + 2 * half, y0 + 2 * half)).resize((2 * half * z, 2 * half * z), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    for x in range((x0 // step) * step, x0 + 2 * half + 1, step):
        if x < x0: continue
        X = (x - x0) * z; d.line([(X, 0), (X, 2 * half * z)], fill=(255, 0, 255) if x % 50 == 0 else (0, 220, 255), width=1)
        if x % 50 == 0: d.text((X + 2, 2), str(x), fill=(255, 255, 0))
    for y in range((y0 // step) * step, y0 + 2 * half + 1, step):
        if y < y0: continue
        Y = (y - y0) * z; d.line([(0, Y), (2 * half * z, Y)], fill=(255, 0, 255) if y % 50 == 0 else (0, 220, 255), width=1)
        if y % 50 == 0: d.text((2, Y + 2), str(y), fill=(255, 255, 0))
    return c
if __name__ == '__main__':
    n = sys.argv[1]; pts = [tuple(int(v) for v in p.split(',')) for p in sys.argv[2:]]
    tiles = [zg(n, x, y) for x, y in pts]
    W = sum(t.size[0] for t in tiles[:4]); rows = (len(tiles) + 3) // 4
    sheet = Image.new('RGB', (min(4, len(tiles)) * tiles[0].size[0], rows * tiles[0].size[1]))
    for i, t in enumerate(tiles): sheet.paste(t, ((i % 4) * t.size[0], (i // 4) * t.size[1]))
    sheet.save(SP + f'zg_{n}.png')
