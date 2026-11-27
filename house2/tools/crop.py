"""Crop (and optionally scale) a region of a cached image, with pixel-coordinate ticks of the ORIGINAL image.

    python3 -I tools/crop.py photos/p30_b7b282.jpg x0 y0 x1 y1 out.jpg [scale] [grid]
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def crop(name, x0, y0, x1, y1, out, scale=1.0, grid=100):
    im = Image.open(os.path.join(HERE, 'refs', 'cache', name)).convert('RGB').crop((x0, y0, x1, y1))
    if scale != 1.0:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    if grid:
        gx = (x0 // grid + 1) * grid
        while gx < x1:
            px = (gx - x0) * scale
            d.line([(px, 0), (px, 14)], fill=(255, 255, 0), width=2)
            d.line([(px, im.height - 14), (px, im.height)], fill=(255, 255, 0), width=2)
            d.text((px + 3, 1), str(gx), fill=(255, 255, 0))
            gx += grid
        gy = (y0 // grid + 1) * grid
        while gy < y1:
            py = (gy - y0) * scale
            d.line([(0, py), (14, py)], fill=(255, 255, 0), width=2)
            d.line([(im.width - 14, py), (im.width, py)], fill=(255, 255, 0), width=2)
            d.text((16, py - 5), str(gy), fill=(255, 255, 0))
            gy += grid
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    im.save(out, quality=90)
    return im.size


if __name__ == '__main__':
    a = sys.argv
    print(crop(a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]), a[6], float(a[7]) if len(a) > 7 else 1.0,
               int(a[8]) if len(a) > 8 else 100))
