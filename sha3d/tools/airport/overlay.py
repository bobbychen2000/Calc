"""Overlay plates of data/sha_airport.json on Sentinel-2 true colour and on the Umbra SAR GEC overview.

usage: python3 -I sha3d/tools/airport/overlay.py SHA3D_DIR OUT_S2_JPG OUT_UMBRA_JPG

Each plate: the whole detailed extent (left) and four zooms (both runway north ends, both south ends, Terminal 1,
Terminal 2). Images are resampled north-up into the world frame (tools/common/frame.py) through PROJ (topocentric
inverse; drawing only) and shown in their own georeferencing (no shift applied: OSM minus S2 is about (-2.4, -0.6) m,
Umbra minus OSM about (+3.1, 0) m from the runway bands - see docs/phase1/airport.md). Imagery outside the detailed
extent polygon is not shown (QA C1 M8: the plates show no imagery beyond the extent).
"""
import json
import os
import sys

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from scipy.ndimage import map_coordinates

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402

ROOT = os.environ.get('SHA3D_ROOT') or sys.argv[1]
D = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
INV = Transformer.from_pipeline(
    f'+proj=pipeline +step +inv +proj=topocentric +ellps=WGS84 +lat_0={F.ORIGIN_LAT} +lon_0={F.ORIGIN_LON} +h_0=0 '
    f'+step +inv +proj=cart +ellps=WGS84')


def world_grid_ll(x0, z0, x1, z1, res):
    xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
    X, Z = np.meshgrid(xs, zs)
    lon, lat, _ = INV.transform(X, -Z, np.zeros_like(X))
    return lon, lat


from matplotlib.path import Path as _Path  # noqa: E402
_EXT = _Path(D['extent']['ring'])


def outside_extent(x0, z0, x1, z1, res):
    xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
    X, Z = np.meshgrid(xs, zs)
    return ~_EXT.contains_points(np.c_[X.ravel(), Z.ravel()]).reshape(X.shape)


def s2_image(x0, z0, x1, z1, res):
    ds = rasterio.open(os.path.join(ROOT, 'refs/cache/s2/S2B_51RUQ_20261014_0_L2A/TCI.tif'))
    a = ds.read().astype(float); T = ds.transform
    tr = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True)
    lon, lat = world_grid_ll(x0, z0, x1, z1, res)
    E, N = tr.transform(lon, lat)
    col = (E - T.c) / T.a - 0.5; row = (N - T.f) / T.e - 0.5
    rgb = np.stack([map_coordinates(a[k], [row, col], order=1, mode='nearest') for k in range(3)], -1)
    rgb = np.clip(255 * (np.clip(rgb, 0, 255) / 255) ** 0.9 * 1.1, 0, 255)   # mild stretch of the TCI
    rgb[outside_extent(x0, z0, x1, z1, res)] = 40
    return Image.fromarray(rgb.astype(np.uint8))


def umbra_image(x0, z0, x1, z1, res):
    ds = rasterio.open(os.path.join(ROOT, 'refs/cache/imagery/umbra_opendata/umbra_gec_ovr4.tif'))
    a = ds.read(1).astype(float); inv = ~ds.transform
    lon, lat = world_grid_ll(x0, z0, x1, z1, res)
    col, row = inv * (lon, lat)
    v = map_coordinates(a, [np.asarray(row) - 0.5, np.asarray(col) - 0.5], order=1, mode='constant', cval=0)
    v = np.clip(v / 40.0, 0, 1) ** 0.6 * 255
    v[outside_extent(x0, z0, x1, z1, res)] = 40
    return Image.fromarray(v.astype(np.uint8)).convert('RGB')


def draw_data(img, x0, z0, res, scale_txt=True, detail=1):
    d = ImageDraw.Draw(img, 'RGBA')

    def P(p):
        return ((p[0] - x0) / res, (p[1] - z0) / res)

    def poly(r, **kw):
        if len(r) >= 2:
            d.polygon([P(p) for p in r], **kw)

    def line(pts, **kw):
        if len(pts) >= 2:
            d.line([P(p) for p in pts], **kw)
    lw = max(1, int(round(2.5 / res))) if detail else 1
    # extent + aerodrome
    ext = D['extent']['ring']
    line(ext + [ext[0]], fill=(255, 255, 255, 200), width=2)
    for r in D['aerodrome']['rings']:
        line(r + [r[0]], fill=(255, 255, 255, 255), width=1)
    # context water + rail + major roads
    for wl in D['context']['water_lines']:
        if wl['waterway'] in ('river', 'canal'):
            for ln in wl['lines']:
                line(ln, fill=(60, 170, 255, 220), width=1)
    for wa in D['context']['water_areas']:
        poly(wa['ring'], outline=(60, 170, 255, 255))
    for rl in D['context']['rail']:
        if rl['railway'] in ('rail', 'subway') and not rl.get('tunnel'):
            for ln in rl['lines']:
                line(ln, fill=(200, 120, 255, 150), width=1)
    for rd in D['context']['roads']:
        if rd['class'] in ('motorway', 'trunk') and not rd.get('tunnel'):
            for ln in rd['lines']:
                line(ln, fill=(255, 255, 255, 90), width=1)
    for b in D['context']['buildings']:
        poly(b['ring'], outline=(200, 200, 200, 110))
    # aprons, surfaces
    for a in D['aprons']:
        poly(a['ring'], outline=(80, 160, 255, 255))
    for s in D['surfaces']['taxiway']:
        poly(s['ring'], outline=(255, 230, 0, 120))
    for r in D['runways']:
        poly(r['shoulders']['ring'], outline=(255, 140, 0, 200))
        for bp in r['blast_pads']:
            poly(bp['ring'], outline=(255, 140, 0, 255), fill=(255, 140, 0, 50))
        poly(r['outline']['ring'], outline=(255, 40, 40, 255))
        line(r['centreline']['pts'], fill=(255, 40, 40, 160), width=1)
        for e in r['ends']:
            # ALS, PAPI, DTHR bar, end, OSM node
            line(e['approach_lights']['line'], fill=(255, 200, 80, 200), width=1)
            px, pz = P(e['papi']['xz']); k = max(2, 3 / res)
            d.rectangle([px - k, pz - k, px + k, pz + k], outline=(255, 120, 255, 255))
            u = r['axis_unit_xz']; n = (-u[1], u[0]); h = r['aip_facts']['width_m'] / 2
            for key, col in (('dthr', (255, 0, 255, 255)), ('end', (0, 255, 255, 255))):
                c = e[key]['xz']
                line([[c[0] - n[0] * h, c[1] - n[1] * h], [c[0] + n[0] * h, c[1] + n[1] * h]], fill=col, width=lw)
            ox, oz = P(e['osm_end_node']['xz']); k = max(2, 2.5 / res)
            d.ellipse([ox - k, oz - k, ox + k, oz + k], outline=(0, 255, 0, 255), width=1)
    # taxiways: original OSM (where moved) grey, final yellow
    pinned_orig = ORIG
    for t in D['taxiways'] + D['taxilanes']:
        parts = [t['pts']] if t['pts'] else t['parts']
        moved = t['refit'] and t['refit']['own_run_refit']
        if moved and t['id'] in pinned_orig:
            for ln in pinned_orig[t['id']]:
                line(ln, fill=(180, 180, 180, 220), width=1)
        col = (255, 230, 0, 255) if t['kind'] == 'taxiway' else (255, 245, 170, 200)
        if moved:
            col = (0, 255, 120, 255)
        for p in parts:
            line(p, fill=col, width=lw if (detail and moved) else 1)
    for h in D['holds']:
        px, pz = P([h['x'], h['z']]); k = max(2, 3 / res)
        d.ellipse([px - k, pz - k, px + k, pz + k], fill=(255, 0, 255, 255))
    for b in D['buildings']:
        poly(b['ring'], outline=(0, 255, 255, 255))
        for r2 in (b['more_rings'] or []):
            poly(r2, outline=(0, 255, 255, 255))
    ct = D['control_tower']; px, pz = P([ct['x'], ct['z']]); k = max(4, 6 / res)
    d.polygon([(px, pz - k), (px + k * .9, pz + k * .6), (px - k * .9, pz + k * .6)], outline=(255, 0, 0, 255),
              fill=(255, 0, 0, 160))
    for nv in D['navaids']:
        px, pz = P([nv['x'], nv['z']]); k = max(3, 4 / res)
        d.polygon([(px, pz + k), (px + k, pz - k), (px - k, pz - k)], outline=(255, 255, 255, 255))
    return d


def orig_taxiways():
    fc = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
    out = {}
    for f in fc['features']:
        if f['properties']['tags'].get('aeroway') == 'taxiway' and f['geometry']['type'] == 'LineString':
            out['osm:way/%d' % f['properties']['@id']] = [[F.ll_to_world(la, lo) for lo, la in f['geometry']['coordinates']]]
    return out


ORIG = orig_taxiways()


def label(img, txt, xy=(6, 6), size=16):
    d = ImageDraw.Draw(img, 'RGBA')
    f = ImageFont.truetype(FONTB, size)
    bb = d.textbbox(xy, txt, font=f)
    d.rectangle([bb[0] - 4, bb[1] - 3, bb[2] + 4, bb[3] + 3], fill=(0, 0, 0, 170))
    d.text(xy, txt, font=f, fill=(255, 255, 255))


def scalebar(img, res, metres, xy):
    d = ImageDraw.Draw(img, 'RGBA'); f = ImageFont.truetype(FONT, 13)
    L = metres / res
    x, y = xy
    d.rectangle([x - 4, y - 18, x + L + 4, y + 8], fill=(0, 0, 0, 160))
    d.line([x, y, x + L, y], fill=(255, 255, 255), width=3)
    d.text((x, y - 17), f'{metres:g} m', font=f, fill=(255, 255, 255))


def plate(make_img, out, title, credit):
    xs = [p[0] for p in D['extent']['ring']]; zs = [p[1] for p in D['extent']['ring']]
    x0, x1, z0, z1 = min(xs) - 60, max(xs) + 60, min(zs) - 60, max(zs) + 60
    res0 = (z1 - z0) / 1500
    ov = make_img(x0, z0, x1, z1, res0)
    draw_data(ov, x0, z0, res0, detail=0)
    label(ov, 'Detailed extent (hull + 1 km, %.1f km2), north up' % D['extent']['area_km2'], size=18)
    scalebar(ov, res0, 1000, (20, ov.height - 20))
    zooms = [('Runway north ends (18L right, 18R left)', (-262, -1660), 900, 720),
             ('Runway south ends (36R right, 36L left)', (-105, 1640), 900, 720),
             ('Terminal 1 and the control tower (east)', (560, 200), 1000, 800),
             ('Terminal 2 (west)', (-1130, 170), 1000, 800)]
    tiles = []
    for name, (cx, cz), wdt, hgt in zooms:
        res = wdt / 900
        zx0, zz0 = cx - wdt / 2, cz - hgt / 2
        im = make_img(zx0, zz0, zx0 + wdt, zz0 + hgt, res)
        draw_data(im, zx0, zz0, res)
        label(im, name, size=16)
        scalebar(im, res, 200, (20, im.height - 18))
        tiles.append(im)
        # frame on the overview
        dd = ImageDraw.Draw(ov)
        dd.rectangle([(zx0 - x0) / res0, (zz0 - z0) / res0, (zx0 + wdt - x0) / res0, (zz0 + hgt - z0) / res0],
                     outline=(255, 255, 0), width=2)
    tw, th = tiles[0].size
    W = ov.width + 2 * tw + 30; H = max(ov.height, 2 * th + 10) + 140
    canvas = Image.new('RGB', (W, H), (20, 20, 20))
    canvas.paste(ov, (10, 10))
    for k, im in enumerate(tiles):
        canvas.paste(im, (ov.width + 20 + (k % 2) * (tw + 0), 10 + (k // 2) * (th + 10)))
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(FONT, 15); fb = ImageFont.truetype(FONTB, 20)
    y = max(ov.height, 2 * th + 10) + 18
    d.text((12, y), title, font=fb, fill=(255, 255, 255))
    legend = ('red = runway outline (AIP length / width on the OSM axis, ends measured on imagery)   orange = shoulders and '
              'blast pads   cyan bar = placed runway end   magenta bar = displaced threshold   green circle = OSM runway '
              'end node\nlight orange = approach lights (from DTHR)   pink square = PAPI (lateral offset is a placeholder)   '
              'yellow = OSM taxiways (faint = 23 m surface)   pale = taxilanes   bright green = taxiway re-fitted to '
              'Sentinel-2 (grey = the OSM line before)\nmagenta dot = holding position   blue = aprons, canals   violet = '
              'rail   cyan = airport buildings   grey = other buildings   red triangle = control tower   white triangle = '
              'glide-path antenna (inferred from AIP obstacle positions)   white = aerodrome boundary, extent')
    d.multiline_text((12, y + 30), legend, font=f, fill=(230, 230, 230), spacing=4)
    d.multiline_text((12, y + 98), credit, font=f, fill=(255, 255, 160), spacing=4)
    canvas.save(out, quality=88)
    print(out, canvas.size)


if __name__ == '__main__':
    OUT_S2, OUT_UM = sys.argv[2:4]
    plate(s2_image, OUT_S2, 'SHA Live 3D - airport data (sha_airport.json) over Sentinel-2 L2A true colour, S2B 2026-10-14 (10 m)',
          'Contains modified Copernicus Sentinel data 2026.   Map data (c) OpenStreetMap contributors (ODbL 1.0).   '
          'AIP values: AIP (mirror), short facts, not ODbL.   Image shown in its own georeferencing (OSM - S2 = -2.4 m E, '
          '-0.6 m N); no imagery outside the extent.')
    plate(umbra_image, OUT_UM, 'SHA Live 3D - airport data over Umbra SAR (X-band VV, GEC, 2024-06-02, 1.4 m overview of 0.35 m)',
          'Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0 (creativecommons.org/licenses/by/4.0), modified.   Map data '
          '(c) OpenStreetMap contributors (ODbL 1.0).\nRadar: buildings lean west (towards the sensor); flat ground '
          'appears ~3.1 m east of OSM (runway bands); no imagery outside the extent.')
