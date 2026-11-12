"""Overview JPEG (~2000 px wide) of the HWD NAIP mosaic, with the FAA NASR runway ends, displaced thresholds and ARP
projected into it (hwd3d/out/phase1/naip_overview[_<year>].jpg, gitignored - for humans).

New for hwd3d (no sfo3d counterpart; sfo3d's naip_world.py preview is a world-grid texture, not forked).
Projection: NASR lat/lon (NAD 83) -> UTM 10N (hwd_frame.ll_to_utm10, Krueger series) -> pixel centre convention of
common.py. Markers: red cross = runway end (NASR APT_RWY_END LAT/LONG_DECIMAL), cyan cross = displaced threshold
(LAT/LONG_DISPLACED_THR_DECIMAL), yellow circle = ARP (APT_BASE). The dashed tile seam (overlap rule of naip_fetch.py)
is drawn in magenta.

usage: python3 -I hwd3d/tools/imagery/naip_overview.py [--year 2024] [--width 2000]
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import F, OUT, load_rgb, georef_path  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--year', default='2024'); ap.add_argument('--width', type=int, default=2000)
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    img, geo, src = load_rgb(a.year)
    H, W = img.shape[:2]; s = a.width / W
    im = Image.fromarray(np.ascontiguousarray(img[..., :3])).resize((a.width, round(H * s)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype('DejaVuSans.ttf', 18)
    except Exception: font = ImageFont.load_default()
    def px(lat, lon):
        E, N = F.ll_to_utm10(lat, lon)
        return ((E - geo['e0']) / geo['g']) * s, ((geo['n1'] - N) / geo['g']) * s    # outer-edge coords * scale
    def cross(x, y, col, r=9):
        d.line([(x - r, y), (x + r, y)], fill=col, width=2); d.line([(x, y - r), (x, y + r)], fill=col, width=2)
    for k, e in F.RWY_ENDS.items():
        x, y = px(e['lat'], e['lon']); cross(x, y, (255, 40, 40))
        d.text((x + 8, y - 26 if k in ('10L', '28R') else y + 6), k, fill=(255, 60, 60), font=font)
        if e['thrLat'] is not None:
            x, y = px(e['thrLat'], e['thrLon']); cross(x, y, (0, 230, 255))
            d.text((x + 8, y + 6), f'{k} thr', fill=(0, 230, 255), font=font)
    x, y = px(F.ARP_LAT, F.ARP_LON); d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 230, 0), width=2)
    d.text((x + 9, y - 9), 'ARP', fill=(255, 230, 0), font=font)
    # tile seam: boundary of the tile-index raster
    G = json.load(open(georef_path(a.year)))
    ti = np.asarray(Image.open(os.path.join(os.path.dirname(georef_path(a.year)), G['tile_index_png'].split(' ')[0])))
    rows = np.arange(0, H, 40)
    for r in rows:
        c = np.nonzero(np.diff(ti[r].astype(int)))[0]
        for cc in c:
            if (r // 40) % 2 == 0: d.line([(cc * s, r * s), (cc * s, (r + 40) * s)], fill=(255, 0, 255), width=1)
    # scale bar 500 m
    L = 500 / geo['g'] * s; x0, y0 = 30, im.size[1] - 40
    d.rectangle([x0 - 6, y0 - 28, x0 + L + 10, y0 + 12], fill=(0, 0, 0))
    d.line([(x0, y0), (x0 + L, y0)], fill=(255, 255, 255), width=4)
    d.text((x0, y0 - 26), '500 m', fill=(255, 255, 255), font=font)
    dates = ', '.join(sorted({t['flight_date'] for t in G['tiles']}))
    lab = f'NAIP {a.year} ({dates}), EPSG:26910 0.6 m; north up. Red: NASR runway ends; cyan: displaced thresholds'
    d.rectangle([0, 0, im.size[0], 26], fill=(0, 0, 0)); d.text((8, 3), lab, fill=(255, 255, 255), font=font)
    name = 'naip_overview.jpg' if a.year == '2024' else f'naip_overview_{a.year}.jpg'
    im.save(os.path.join(OUT, name), quality=90)
    print('wrote', os.path.join(OUT, name), im.size, 'from', src)


if __name__ == '__main__':
    main()
