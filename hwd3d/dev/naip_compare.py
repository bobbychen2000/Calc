#!/usr/bin/env python3
"""NAIP 2024 vs model comparison crops for the HWD world (P2, Phase 2 dev tool; not part of the app).

For each named region it resamples the committed NAIP 2024 mosaic (refs/cache/naip/naip_2024_hwd_rgb.jpg, USDA, public
domain) onto a world-frame grid (exact per-pixel mapping world -> NAD83 lat/lon -> UTM 10N -> pixel through
tools/imagery/common.py NaipSampler, i.e. the frame code of tools/common/hwd_frame.py) and writes
out/phase2/cmp_<name>.png: NAIP alone (top) and NAIP with the outlines of our paint geometry (bottom; red = white paint,
cyan = yellow paint) from out/phase2/paint_tris.json (node dev/paint_dump.mjs) and of the building footprints we extrude
(magenta, js/world/site.js buildings via out/phase2/site_dump.json if present).

usage (from hwd3d/):  node dev/paint_dump.mjs && python3 dev/naip_compare.py [name ...]
A region is a centre (world x, z), a size (m), a resolution (m/px) and an orientation: 'north' (north up) or 'rwy'
(the 10 -> 28 runway axis to the right, js/world/grid.js GRID.s).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'imagery'))
from common import NaipSampler  # noqa: E402

OUT = os.path.join(ROOT, 'out', 'phase2')
# js/world/grid.js GRID: runway axis 10L -> 28R, 119.857 deg true (geo.js rwyAxis('10L'))
H = math.radians(119.857)
GS = (math.sin(H), -math.cos(H))          # world (x, z) unit along 10 -> 28
GT = (-GS[1], GS[0])                      # right of it (x, z)

REGIONS = {
    # name: (cx, cz, width_m, height_m, res_m, orientation)
    'rwy10R_end': None, 'rwy28L_end': None, 'rwy10L_end': None, 'rwy28R_end': None,
    'green_ramp': (-55, -345, 260, 170, 0.25, 'north'),
    'west_hangars': (-250, -600, 420, 300, 0.4, 'north'),
    'tower': (40, -410, 160, 110, 0.15, 'north'),
    'wsock': (-27, -59.4, 70, 60, 0.1, 'north'),
    'fire': (300, 586, 90, 60, 0.15, 'north'),
}


def runway_regions():
    """runway-end regions along the runway axis, from geo.js-equivalent NASR ends in the site dump"""
    S = json.load(open(os.path.join(OUT, 'site_dump.json')))
    out = {}
    for e, (x, z) in S['ends'].items():
        if e.endswith('_thr'): continue
        th = S['ends'][e + '_thr']
        # from 60 m before the end to 420 m past the threshold, centred on the runway axis
        sgn = 1 if e.startswith('10') else -1
        a0 = -70; a1 = math.hypot(th[0] - x, th[1] - z) + 430
        c = (x + GS[0] * sgn * (a0 + a1) / 2, z + GS[1] * sgn * (a0 + a1) / 2)
        out['rwy%s_end' % e] = (c[0], c[1], a1 - a0, 70, 0.15, 'rwy' if sgn > 0 else 'rwy_rev')
    return out


def frame(orient):
    if orient == 'north': return (1.0, 0.0), (0.0, 1.0)          # image right = east, image down = south
    if orient == 'rwy': return GS, GT                              # right = toward 28, down = right of 10 -> 28
    if orient == 'rwy_rev': return (-GS[0], -GS[1]), (-GT[0], -GT[1])
    raise ValueError(orient)


def render(name, reg, naip, tris, rings):
    cx, cz, w, h, res, orient = reg
    u, d = frame(orient)
    W, Hh = int(round(w / res)), int(round(h / res))
    jj, ii = np.mgrid[0:Hh, 0:W].astype(np.float64)
    X = cx + (ii + 0.5 - W / 2) * res * u[0] + (jj + 0.5 - Hh / 2) * res * d[0]
    Z = cz + (ii + 0.5 - W / 2) * res * u[1] + (jj + 0.5 - Hh / 2) * res * d[1]
    rgb = np.stack([naip.sample_world(X, Z, band=b) for b in range(3)], -1).clip(0, 255).astype(np.uint8)
    base = Image.fromarray(rgb)

    def P(x, z):
        dx, dz = x - cx, z - cz
        return ((dx * u[0] + dz * u[1]) / res + W / 2, (dx * d[0] + dz * d[1]) / res + Hh / 2)
    masks = {}
    for col in 'WY':
        m = Image.new('L', (W, Hh), 0); dr = ImageDraw.Draw(m)
        for t in tris:
            if t[6] != col: continue
            pts = [P(t[0], t[1]), P(t[2], t[3]), P(t[4], t[5])]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if max(xs) < 0 or min(xs) > W or max(ys) < 0 or min(ys) > Hh: continue
            dr.polygon(pts, fill=255)
        masks[col] = m
    over = base.copy(); od = np.asarray(over).copy()
    for col, c in (('W', (255, 30, 30)), ('Y', (0, 230, 255))):
        m = masks[col]; er = m.filter(ImageFilter.MinFilter(3)); edge = (np.asarray(m) > 0) & ~(np.asarray(er) > 0)
        od[edge] = c
    over = Image.fromarray(od); dr = ImageDraw.Draw(over)
    for r in rings:
        q = [P(p[0], p[1]) for p in r]
        dr.line(q + [q[0]], fill=(255, 0, 255), width=1)
    out = Image.new('RGB', (W, Hh * 2 + 18), (0, 0, 0))
    out.paste(base, (0, 0)); out.paste(over, (0, Hh + 18))
    dd = ImageDraw.Draw(out)
    dd.text((4, Hh + 3), f'{name}: NAIP 2024 (top) / + model paint (red white, cyan yellow) and footprints (magenta); '
            f'{res} m/px, {orient}', fill=(255, 255, 0))
    fn = os.path.join(OUT, f'cmp_{name}.png'); out.save(fn)
    return fn


def main():
    D = json.load(open(os.path.join(OUT, 'paint_tris.json')))
    S = json.load(open(os.path.join(OUT, 'site_dump.json')))
    regs = dict(REGIONS); regs.update(runway_regions())
    names = sys.argv[1:] or [k for k in regs]
    naip = NaipSampler('2024', prefer='jpg')
    for n in names:
        print(render(n, regs[n], naip, D['tris'], S['rings']))


if __name__ == '__main__':
    main()
