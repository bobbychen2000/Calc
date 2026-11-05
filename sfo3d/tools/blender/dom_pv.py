"""Roof PV fields of the domestic terminals, measured on NAIP 2024 (public domain, USDA FPAC-BC GEO) for the 3-D asset
(tools/blender/build_domestic.py). NAIP is used here as a MEASUREMENT (extents of the dark PV racks on the light roof
membrane), never as a texture; the output is numbers only (tools/blender/dom_pv.json, committed like
tools/buildings/dom_bab_roof.json).

    python3 tools/blender/dom_pv.py            # -> tools/blender/dom_pv.json (+ QA overlays out/buildings3d/dom_pv_*.png, local)

Method (per roof level, all heights / leans from the sheets' inputs, tools/buildings/draw_data.py):
  1. imaged roof = the true roof polygon (tools/blender/dom_geom.py) shifted by the level's NAIP 2024 relief: lean (m/m,
     east; draw_data.dom_lean, the per-pier two-epoch value) x the roof height; eroded 1.5 m (parapet shadows, fascia)
  2. PV pixel: luminance below PV_LUM x the roof's median luminance and not green / brown (planted roof wells, B > G - 6)
  3. morphological open 1.0 m (thin shadows, joints), close 1.5 m (cells / rows of one rack block), components >= 20 m2
  4. each component -> its minimum rotated rectangle when it fills >= 70 % of it, else the outline simplified at 0.6 m
  5. moved back by the relief (lean x height) to the lean-free roof, clipped to the true roof deck less 0.8 m
Tags: extents [obs, NAIP 2024 2024-05-20, +-1 m]; positions lean-corrected [inf where the roof height is inf / unk: T1 hall,
T3]; rack height / tilt [inf]. PV existence: BA-B [pub bab.pv 1.0 MW], T1 Center [obs t1c.roof_pv], BA-E [obs photo a1],
T3 [obs NAIP, this script; not in the spec].
"""
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dom_geom as G  # noqa: E402
import draw_lib as DL  # noqa: E402
import draw_data as D  # noqa: E402

PV_LUM = 0.80          # PV pixel: luminance < 0.80 x the roof median [inf, tuned on the B / T1 / T3 / E crops]
OPEN_M, CLOSE_M = 1.0, 1.5
A_MIN = 20.0
OUT_JSON = os.path.join(HERE, 'dom_pv.json')
OUT_QA = os.path.join(G.ROOT, 'out', 'buildings3d')


def regions():
    """(name, true roof polygon (world x, z), roof height h, east lean m/m, tag of the position)."""
    lB, lE, lF = (float(D.dom_lean(k)[0][0]) for k in 'BEF')
    out = []
    for nm, poly, h, k, tag in G.pv_regions(lB, lE, lF):
        out.append((nm, poly, h, k, tag))
    return out


def detect(name, poly, h, k):
    import cv2
    shift = np.array([k * h, 0.0])
    img_poly = affinity.translate(poly, shift[0], shift[1]).buffer(-1.5, join_style=2)
    if img_poly.is_empty: return [], None
    x0, z0, x1, z1 = img_poly.bounds
    x0, z0, x1, z1 = math.floor(x0) - 2, math.floor(z0) - 2, math.ceil(x1) + 2, math.ceil(z1) + 2
    rgb, (X0, Z0, X1, Z1) = DL.naip_rgb(x0, z0, x1, z1, res=0.5, bounds=True)
    H_, W_ = rgb.shape[:2]
    R = (X1 - X0) / W_
    mask = np.zeros((H_, W_), np.uint8)
    for p in G.polys_of(img_poly):
        ext = np.array([[(x - X0) / R, (z - Z0) / R] for x, z in p.exterior.coords], np.int32)
        cv2.fillPoly(mask, [ext], 1)
        for r in p.interiors:
            cv2.fillPoly(mask, [np.array([[(x - X0) / R, (z - Z0) / R] for x, z in r.coords], np.int32)], 0)
    f = rgb.astype(float)
    lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    med = float(np.median(lum[mask > 0]))
    pv = (lum < PV_LUM * med) & (f[..., 2] > f[..., 1] - 6) & (mask > 0)
    ko = max(1, int(round(OPEN_M / R))); kc = max(1, int(round(CLOSE_M / R)))
    m = cv2.morphologyEx(pv.astype(np.uint8), cv2.MORPH_OPEN, np.ones((ko, ko), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((kc, kc), np.uint8)) & mask
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    deck = poly.buffer(-0.8, join_style=2)
    out = []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] * R * R < A_MIN: continue
        cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(float)
        if len(c) < 3: continue
        pts = [(X0 + (u + 0.5) * R, Z0 + (v + 0.5) * R) for u, v in c]
        g = Polygon(pts).buffer(0.25 * R / 0.5, join_style=2).buffer(0)
        if g.is_empty: continue
        rr = g.minimum_rotated_rectangle
        g = rr if g.area / max(rr.area, 1e-6) >= 0.70 else g.simplify(0.6, preserve_topology=True)
        g = affinity.translate(g, -shift[0], -shift[1]).intersection(deck)
        for q in G.polys_of(g):
            if q.area < A_MIN * 0.6: continue
            q = q.simplify(0.15)
            out.append(dict(ring=[[round(x, 2), round(z, 2)] for x, z in list(q.exterior.coords)[:-1]], area=round(q.area, 1)))
    qa = (rgb, m, (X0, Z0, R), shift)
    return out, qa


def main():
    res = dict(generated_by='tools/blender/dom_pv.py', image='NAIP 2024 world raster 0.5 m (refs/cache/naip/naip_2024_world_0.5m.png), '
               'public domain; used as a measurement only', params=dict(pv_lum=PV_LUM, open_m=OPEN_M, close_m=CLOSE_M, a_min_m2=A_MIN),
               frame='ltp-nad83-2011 world (x east, z south), lean-free (relief removed with the listed lean x height)', regions={})
    os.makedirs(OUT_QA, exist_ok=True)
    from PIL import Image, ImageDraw
    for name, poly, h, k, tag in regions():
        blocks, qa = detect(name, poly, h, k)
        res['regions'][name] = dict(h=round(h, 2), lean_east=round(k, 3), shift_m=round(k * h, 2), tag=tag, n=len(blocks),
                                    area_m2=round(sum(b['area'] for b in blocks), 0), blocks=blocks)
        print(f'{name:10s} h {h:5.2f} lean {k:.3f}: {len(blocks)} blocks, {sum(b["area"] for b in blocks):.0f} m2')
        if qa is None: continue
        rgb, m, (X0, Z0, R), shift = qa
        im = Image.fromarray(rgb).convert('RGB')
        ov = np.array(im); ov[m > 0] = (0.5 * ov[m > 0] + np.array([0, 0, 127])).astype(np.uint8)
        im = Image.fromarray(ov); dr = ImageDraw.Draw(im)
        for b in blocks:
            dr.polygon([((x + shift[0] - X0) / R, (z + shift[1] - Z0) / R) for x, z in b['ring']], outline=(255, 0, 0))
        im.save(os.path.join(OUT_QA, f'dom_pv_{name}.png'))
    json.dump(res, open(OUT_JSON, 'w'), indent=1)
    print('->', OUT_JSON)


if __name__ == '__main__':
    main()
