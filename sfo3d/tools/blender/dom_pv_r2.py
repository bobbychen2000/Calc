"""Review round 2 (domestic finding 2): the PV arrays on the Boarding Area E raised roof plate that tools/blender/dom_pv.py
missed, measured on NAIP 2024 (public domain, USDA FPAC-BC GEO) as numbers only (never a texture).

    python3 tools/blender/dom_pv_r2.py        # -> tools/blender/dom_pv_r2.json (+ QA overlay out/buildings3d/dom_pv_r2_E_centre.png, local)

Why dom_pv.py missed them: the row of ~5 x 11-m arrays along the WNW half of the plate lies 1-2 m apart and 2-4 m from the
plate's tapered WNW edge; dom_pv.py's 2-m closing merged them with the edge shadow into one 1,085-m2 component that failed
its fill test (0.25), and its 3.5-m minimum width dropped the narrower arrays. Photo a1 (reference only) shows the plate
covered by PV in both halves near the tip (review r2).

Method (the imaged plate = the true plate of tools/blender/dom_geom.py shifted east by the BA-E relief, lean 0.443 m/m x
12.85 m = 5.69 m, as dom_pv.json):
  1. the imaged plate eroded ERODE_M (the tapered edge, its shadow and the gutter)
  2. PV pixel: luminance >= DROP below the local membrane brightness (9-m max filter), not teal (B - R < 25); open 1 px
     (0.5 m), NO closing (the 1-2-m aisles between arrays separate the components)
  3. components >= A_MIN m2 -> minimum rotated rectangle; kept when its short side >= W_MIN, fill >= FILL_MIN, aspect
     <= ASPECT_MAX, >= INSIDE_MIN of it inside the eroded imaged plate and the mean drop below the membrane >= DROP_MEAN
     (dark modules; the light grey-green patches between the arrays - skylights or light equipment, not resolved - are NOT
     taken as PV)
  4. dropped where >= 30 % of the rectangle overlaps a table of dom_roofobs.json (already modelled)
  5. moved back by the relief to the lean-free roof; the 3-D build clips them to the free deck (dom_geom.pv_racks)
Tags: array extents [obs, NAIP 2024 2024-05-20, +-0.5 m]; module layout inside an array [inf] (PV tiles); rack height [inf].
"""
import json
import os
import sys

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dom_geom as G  # noqa: E402
import draw_lib as DL  # noqa: E402

OUT_JSON = os.path.join(HERE, 'dom_pv_r2.json')
OUT_QA = os.path.join(G.ROOT, 'out', 'buildings3d')
ERODE_M = 4.0          # [inf, tuned on the overlay: the tapered WNW edge + its shadow reach ~3.5 m into the imaged plate]
DROP = 18.0            # PV pixel: >= 18 below the membrane [inf]
DROP_MEAN = 40.0       # PV array: mean drop >= 40 (the dark arrays 49-69, the light patches 20-37) [inf, measured on the overlay]
W_MIN, FILL_MIN, ASPECT_MAX, A_MIN = 3.0, 0.55, 6.0, 6.0
INSIDE_MIN = 0.8       # >= 80 % of the rectangle inside the eroded imaged plate (rejects dark bridge / edge structures) [inf]
LEAN_E = 0.443         # dom_pv.json regions.E_centre.lean_east (the BA-E two-epoch lean, draw_data.dom_lean('E'))


def detect():
    import cv2
    W, feats, info = G.build_world(1)
    sEc = next(s for s in W.S if s.key == 'BA_E_centre')
    sh = LEAN_E * G.H['E']
    plate = G.wld(sEc.roof).buffer(0)
    img = affinity.translate(plate, sh, 0).buffer(-ERODE_M, join_style=2)
    x0, z0, x1, z1 = img.bounds
    rgb, (X0, Z0, X1, Z1) = DL.naip_rgb(x0 - 3, z0 - 3, x1 + 3, z1 + 3, res=0.5, bounds=True)
    R = (X1 - X0) / rgb.shape[1]
    f = rgb.astype(float)
    lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    kb = max(3, int(round(9.0 / R)) | 1)
    bg = cv2.blur(cv2.dilate(lum.astype(np.float32), np.ones((kb, kb), np.uint8)), (kb, kb))
    mask = np.zeros(lum.shape, np.uint8)
    for p in G.polys_of(img):
        cv2.fillPoly(mask, [np.array([[(x - X0) / R, (z - Z0) / R] for x, z in p.exterior.coords], np.int32)], 1)
    pv = (lum < bg - DROP) & (f[..., 2] - f[..., 0] < 25) & (mask > 0)
    m = cv2.morphologyEx(pv.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)) & mask
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    RO = json.load(open(os.path.join(HERE, 'dom_roofobs.json')))
    have = unary_union([Polygon(t['ring']).buffer(0) for t in RO['pv_tables'].get('E_centre', {}).get('tables', [])])
    have_img = affinity.translate(have, sh, 0) if not have.is_empty else have
    out, rej = [], []
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA] * R * R
        if a < A_MIN: continue
        ys, xs = np.nonzero(lab == i)
        pts = np.c_[X0 + (xs + 0.5) * R, Z0 + (ys + 0.5) * R].astype(np.float32)
        rr = cv2.minAreaRect(pts)
        box = cv2.boxPoints(((rr[0][0], rr[0][1]), (rr[1][0] + R, rr[1][1] + R), rr[2]))
        q = Polygon(box).buffer(0)
        w, h = sorted((rr[1][0] + R, rr[1][1] + R))
        fill = a / max(w * h, 1e-6)
        drop = float((bg - lum)[lab == i].mean())
        rec = dict(img_area=round(a, 1), w=round(w, 2), l=round(h, 2), fill=round(fill, 2), drop=round(drop, 1))
        why = None
        if w < W_MIN: why = 'narrow'
        elif fill < FILL_MIN: why = 'fill'
        elif h / w > ASPECT_MAX: why = 'aspect'
        elif drop < DROP_MEAN: why = 'light (not PV)'
        elif q.intersection(img).area < INSIDE_MIN * q.area: why = 'outside the plate'
        elif not have_img.is_empty and q.intersection(have_img).area > 0.3 * q.area: why = 'already a dom_roofobs table'
        qq = affinity.translate(q, -sh, 0)
        rec['ring'] = [[round(x, 2), round(z, 2)] for x, z in list(qq.exterior.coords)[:-1]]
        rec['area'] = round(qq.area, 1)
        if why: rec['rejected'] = why; rej.append(rec)
        else: out.append(rec)
    # QA overlay (local)
    from PIL import Image, ImageDraw
    sc = 4
    im = Image.fromarray(rgb).convert('RGB').resize((rgb.shape[1] * sc, rgb.shape[0] * sc), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    P = lambda x, z: ((x - X0) / R * sc, (z - Z0) / R * sc)  # noqa: E731
    dr.line([P(*c) for c in img.exterior.coords], fill=(0, 160, 255), width=1)
    for r_ in rej: dr.polygon([P(x + sh, z) for x, z in r_['ring']], outline=(255, 255, 0))
    for r_ in out: dr.polygon([P(x + sh, z) for x, z in r_['ring']], outline=(255, 0, 0))
    os.makedirs(OUT_QA, exist_ok=True)
    im.save(os.path.join(OUT_QA, 'dom_pv_r2_E_centre.png'))
    return dict(shift_m=round(sh, 2), lean_east=LEAN_E, n=len(out), area_m2=round(sum(t['area'] for t in out), 1), tables=out,
                rejected=rej)


def main():
    res = dict(generated_by='tools/blender/dom_pv_r2.py', image='NAIP 2024 world raster 0.5 m (refs/cache/naip/naip_2024_world_0.5m.png), '
               'public domain; used as a measurement only', frame='ltp-nad83-2011 world (x east, z south), lean-free',
               params=dict(inside_min=INSIDE_MIN, erode_m=ERODE_M, drop=DROP, drop_mean=DROP_MEAN, w_min=W_MIN, fill_min=FILL_MIN, aspect_max=ASPECT_MAX, a_min=A_MIN),
               tags='array extents obs (NAIP 2024, +-0.5 m); module layout / rack height inf',
               regions={'E_centre': detect()})
    json.dump(res, open(OUT_JSON, 'w'), indent=1)
    r = res['regions']['E_centre']
    print(f'E_centre: {r["n"]} arrays {r["area_m2"]} m2 added ({len(r["rejected"])} components rejected) ->', OUT_JSON)


if __name__ == '__main__':
    main()
