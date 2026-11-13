"""Downscale an image and cut it into tiles for visual reading. usage: python3 -I img_tiles.py IN OUTDIR NAME [cols rows]"""
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = 60_000_000
src, outdir, name = sys.argv[1:4]
cols, rows = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (2, 2)
im = Image.open(src).convert("RGB")
w, h = im.size
im.resize((1600, int(1600 * h / w))).save(f"{outdir}/{name}_small.jpg", quality=85)
for r in range(rows):
    for c in range(cols):
        box = (c * w // cols, r * h // rows, (c + 1) * w // cols, (r + 1) * h // rows)
        t = im.crop(box)
        t.thumbnail((1800, 1800))
        t.save(f"{outdir}/{name}_r{r}c{c}.jpg", quality=85)
print("ok", w, h)
