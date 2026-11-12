"""Native-resolution crop of the HWD NAIP mosaic for visual inspection (hwd3d/out/phase1/crop_<year>_<name>.png).

New for hwd3d. Pixels are copied 1:1 from the mosaic (local GeoTIFF if present, else the committed JPEG) and
enlarged by an integer factor with nearest-neighbour, so every 0.6 m NAIP pixel stays a visible square; north up.
A 10 m scale bar and the crop's UTM 10N centre are drawn; optional --mark lat,lon[;lat,lon...] draws red crosses.

usage: python3 -I hwd3d/tools/imagery/naip_crop.py --name west_hangars --utm 577020,4169020 --size 200 --up 3
       python3 -I hwd3d/tools/imagery/naip_crop.py --name x --ll 37.6625,-122.1295 --size 120 --up 4 --year 2022
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import F, OUT, load_rgb  # noqa: E402

_cache = {}


def crop(year, E, N, size_m, up, name, marks=(), label=''):
    from PIL import Image, ImageDraw
    if year not in _cache: _cache[year] = load_rgb(year)
    img, geo, src = _cache[year]
    g = geo['g']; h = int(round(size_m / g / 2))
    c = int(np.floor((E - geo['e0']) / g)); r = int(np.floor((geo['n1'] - N) / g))
    c0, r0 = max(0, c - h), max(0, r - h)
    a = np.ascontiguousarray(img[r0:r0 + 2 * h, c0:c0 + 2 * h, :3])
    im = Image.fromarray(a).resize((a.shape[1] * up, a.shape[0] * up), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for la, lo in marks:
        e, n = F.ll_to_utm10(la, lo); x = ((e - geo['e0']) / g - c0) * up; y = ((geo['n1'] - n) / g - r0) * up
        d.line([(x - 10, y), (x + 10, y)], fill=(255, 0, 0), width=2); d.line([(x, y - 10), (x, y + 10)], fill=(255, 0, 0), width=2)
    L = 10 / g * up
    d.rectangle([4, im.size[1] - 26, 18 + L + 40, im.size[1] - 2], fill=(0, 0, 0))
    d.line([(10, im.size[1] - 10), (10 + L, im.size[1] - 10)], fill=(255, 255, 255), width=3)
    d.text((16 + L, im.size[1] - 20), '10 m', fill=(255, 255, 255))
    e_c = geo['e0'] + (c0 + h) * g; n_c = geo['n1'] - (r0 + h) * g
    d.rectangle([0, 0, im.size[0], 14], fill=(0, 0, 0))
    d.text((4, 1), f'NAIP {year} {name} {label} centre E {e_c:.1f} N {n_c:.1f} (UTM 10N), 0.6 m px x{up}, north up',
           fill=(255, 255, 0))
    p = os.path.join(OUT, f'crop_{year}_{name}.png'); im.save(p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', default='2024'); ap.add_argument('--name', required=True)
    ap.add_argument('--utm'); ap.add_argument('--ll'); ap.add_argument('--size', type=float, default=150)
    ap.add_argument('--up', type=int, default=3); ap.add_argument('--mark', default='')
    a = ap.parse_args()
    if a.utm: E, N = map(float, a.utm.split(','))
    else: E, N = F.ll_to_utm10(*map(float, a.ll.split(',')))
    marks = [tuple(map(float, m.split(','))) for m in a.mark.split(';') if m]
    print(crop(a.year, E, N, a.size, a.up, a.name, marks))


if __name__ == '__main__':
    main()
