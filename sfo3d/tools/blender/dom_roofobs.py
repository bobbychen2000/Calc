"""Roof detail of the domestic terminals measured on NAIP 2024 (public domain, USDA FPAC-BC GEO) for the 3-D asset
(review round 1, tools/blender/build_domestic.py): (1) the PV rack TABLES inside every PV block of tools/blender/dom_pv.json
(the rack rows with their aisles, instead of one plate per block) and (2) the rooftop mechanical units (AHUs, condensers,
screened equipment) on every roof deck. NAIP is used as a MEASUREMENT only (extents of dark objects on the light roof
membrane), never as a texture; the output is numbers (tools/blender/dom_roofobs.json, committed like dom_pv.json).

    python3 tools/blender/dom_roofobs.py        # -> tools/blender/dom_roofobs.json (+ QA overlays out/buildings3d/dom_roof_*.png, local)

PV tables (per block; positions in the imaged frame = the lean-free block shifted by the region's relief, dom_pv.json shift_m):
  1. PV pixels as in dom_pv.py (luminance >= PV_DROP below the local membrane brightness, not green, not teal), no density
     filter, inside the imaged block (+0.5 m)
  2. the table axis: gradient-orientation histogram (mod 90 deg, magnitude-weighted, 1-deg bins, smoothed 5 deg) of the
     luminance inside the block -> the dominant rack-edge direction
  3. per 0.25-m strip across the axis (v) and along it (u): aisles = runs >= AISLE_MIN wide whose PV share < AISLE_MAX or
     whose mean luminance lies more than AISLE_REL of the way from the PV level to the membrane level (the 0.5-1-m aisles
     between tables are only partly resolved); rows = the v-bands between aisles, tables = the u-runs of each row band
  4. each table cell with a PV share >= CELL_MIN -> the rectangle of its PV pixels' extent (2-98 %, +- half a pixel) in the
     (u, v) frame (>= 3 m2), moved back by the relief to the lean-free roof (clipped to the free deck by the 3-D build)
  Tags: table extents and the aisle pattern [obs, NAIP 2024 +-0.5 m]; module rows inside a table (the 1-2-m module pitch is
  at the 0.5-m pixel limit): the PV colour / normal tiles [inf].
Rooftop units (per roof deck of the 3-D solids, tools/blender/dom_geom.build_world(0)):
  1. the deck less 2.0 m from its edge (parapet shadow, lean residuals), less its holes (+1.0 m: wells, skylights, drums,
     lantern, monitor, penthouse) and the PV blocks (+1.2 m), moved to its imaged position (lean x deck height)
  2. object pixels: luminance >= UNIT_DROP below the local membrane brightness (9-m max filter) - a dark unit or the short
     2024 shadow (sun az 186.6, el 72.5: 0.315 m per m of height towards az 6.6) of a light one; open 0.5 m, close 1.0 m
  3. components 4-150 m2, minimum-rectangle short side >= 1.5 m, fill >= 0.65, aspect <= 4 -> the minimum rectangle
  4. shadow test: the mean luminance of a 0.9-m strip on the box's shadow side (az 6.6) must be >= UNIT_SHADOW below the
     strip on its sun side - the object stands >~ 1 m above the deck (rejects undetected PV fields, stains, ponding)
  5. height by plan size (not measurable from the 0.6-m shadow at 0.5 m/px): < 12 m2 1.5 m, < 50 m2 2.2 m, else 3.0 m [inf];
     moved back by lean x (deck + unit height) (the imaged top) and clipped to the deck
  Tags: unit extents [obs, NAIP 2024 2024-05-20, +-0.7 m; a light unit's box includes its ~0.5-1 m shadow]; heights [inf];
  type / colour [inf].
"""
import json
import math
import os
import sys

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dom_geom as G  # noqa: E402
import draw_lib as DL  # noqa: E402
import draw_data as D  # noqa: E402

OUT_JSON = os.path.join(HERE, 'dom_roofobs.json')
OUT_QA = os.path.join(G.ROOT, 'out', 'buildings3d')
PV_DROP, BG_M, TEAL = 14.0, 9.0, 25.0         # as dom_pv.py
AISLE_MAX, AISLE_MIN, CELL_MIN, AISLE_REL = 0.30, 0.5, 0.45, 0.45   # [inf, tuned on the T1 / B / T3 crops: aisles 0.5-2.5 m]
UNIT_DROP = 26.0                               # unit / shadow pixel: >= 26 below the membrane [inf, tuned on the T1 / T2 / C3C crops]
UNIT_A = (4.0, 150.0); UNIT_W = 1.5; UNIT_FILL = 0.65; UNIT_ASPECT = 4.0; UNIT_EDGE = 2.0   # [inf, tuned on the overlays: rejects
# roof-step shadows, parapet / facade slivers and undetected PV fields (> 150 m2)]
UNIT_H = ((12.0, 1.5), (50.0, 2.2), (1e9, 3.0))   # plan area m2 -> height m [inf: typical packaged rooftop units / AHUs]
LEAN_OF = {'BA_B': 'B', 'BA_C': 'C', 'BA_D': 'D', 'BA_E': 'E', 'BA_F': 'F', 'T1': 'BC', 'T2': 'CD', 'T3W': 'EF', 'T3E': 'EF'}


def lean_of(bld, x):
    if bld in LEAN_OF:
        return float(np.mean([float(D.dom_lean(c)[0][0]) for c in LEAN_OF[bld]]))
    return G.lean_x(x)


def crop(poly, pad=3.0):
    x0, z0, x1, z1 = poly.bounds
    rgb, (X0, Z0, X1, Z1) = DL.naip_rgb(x0 - pad, z0 - pad, x1 + pad, z1 + pad, res=0.5, bounds=True)
    return rgb, X0, Z0, (X1 - X0) / rgb.shape[1]


def raster(poly, X0, Z0, R, shape):
    import cv2
    m = np.zeros(shape, np.uint8)
    for p in G.polys_of(poly):
        cv2.fillPoly(m, [np.array([[(x - X0) / R, (z - Z0) / R] for x, z in p.exterior.coords], np.int32)], 1)
        for r in p.interiors:
            cv2.fillPoly(m, [np.array([[(x - X0) / R, (z - Z0) / R] for x, z in r.coords], np.int32)], 0)
    return m


def lum_bg(rgb, R):
    import cv2
    f = rgb.astype(float)
    lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    kb = max(3, int(round(BG_M / R)) | 1)
    bg = cv2.blur(cv2.dilate(lum.astype(np.float32), np.ones((kb, kb), np.uint8)), (kb, kb))
    return f, lum, bg


def runs(mask):
    """[(i0, i1)] runs of True."""
    out, i = [], 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]: j += 1
            out.append((i, j)); i = j
        else: i += 1
    return out


def axis_angle(lum, m):
    import cv2
    gx = cv2.Sobel(lum.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gz = cv2.Sobel(lum.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    w = np.hypot(gx, gz) * (m > 0)
    a = np.degrees(np.arctan2(gz, gx)) % 90.0
    hist, _ = np.histogram(a[w > 0], bins=90, range=(0, 90), weights=w[w > 0])
    k = np.exp(-0.5 * (np.arange(-7, 8) / 2.5) ** 2)
    hs = np.convolve(np.r_[hist[-7:], hist, hist[:7]], k, 'same')[7:-7]
    return float(np.argmax(hs) + 0.5)


ST = 0.25          # strip width of the aisle profiles, m
TAB_INSIDE = 0.85  # a table rectangle must lie >= 85 % inside the NAIP block, else its cell is split (fans of radial rows on T1 /
                   # T3: a local axis per sub-cell) [inf]


def _bands(x, sel_pv, L, BGv):
    """row / table intervals along x: aisles = strips whose mean luminance rises AISLE_REL of the way from the PV level to
    the membrane level (or whose PV share < AISLE_MAX), at least AISLE_MIN wide."""
    lo = x.min(); n = int(math.ceil((x.max() - lo) / ST)) + 1
    k = ((x - lo) / ST).astype(int)
    tot = np.bincount(k, minlength=n).astype(float)
    pvc = np.bincount(k, weights=sel_pv.astype(float), minlength=n)
    ls = np.bincount(k, weights=L, minlength=n); bs = np.bincount(k, weights=BGv, minlength=n)
    ok = tot > 0
    share = np.where(ok, pvc / np.maximum(tot, 1), 0.0)
    ml = np.where(ok, ls / np.maximum(tot, 1), 0.0); mb = np.where(ok, bs / np.maximum(tot, 1), 0.0)
    pv_lvl = np.median(L[sel_pv]) if sel_pv.sum() > 10 else np.median(L)
    rel = np.where(ok, (ml - pv_lvl) / np.maximum(mb - pv_lvl, 5.0), 1.0)
    gap = (share < AISLE_MAX) | (rel > AISLE_REL) | ~ok
    rows, prev = [], 0
    for i0, i1 in runs(gap):
        if (i1 - i0) * ST >= AISLE_MIN or i0 == 0 or i1 == n:
            if i0 > prev: rows.append((prev, i0))
            prev = i1
    if prev < n: rows.append((prev, n))
    return [(lo + i0 * ST, lo + i1 * ST) for i0, i1 in rows if (i1 - i0) * ST >= 1.0]


def _tables(reg_img, blob, lum, bg, pv, X0, Z0, R, depth=0):
    """table rectangles (imaged frame) inside reg_img (a part of the imaged block): local axis, row bands, table runs; a
    rectangle that spills out of the block is split (two halves along its long side) and re-analysed, up to 3 levels."""
    m = raster(reg_img, X0, Z0, R, lum.shape)
    rr, cc = np.nonzero(m)
    if len(rr) < 12: return []
    th = axis_angle(lum, m)
    a = np.array([math.cos(math.radians(th)), math.sin(math.radians(th))]); bv = np.array([-a[1], a[0]])
    P = np.stack([X0 + (cc + 0.5) * R, Z0 + (rr + 0.5) * R], 1)
    U, V = P @ a, P @ bv; isPV = pv[rr, cc]; Lm = lum[rr, cc]; BGm = bg[rr, cc]
    out = []
    for v0, v1 in _bands(V, isPV, Lm, BGm):
        sel = (V >= v0) & (V < v1)
        if sel.sum() < 8: continue
        for u0, u1 in _bands(U[sel], isPV[sel], Lm[sel], BGm[sel]):
            cs = sel & (U >= u0) & (U < u1)
            if cs.sum() < 8 or isPV[cs].mean() < CELL_MIN: continue
            pu, pvv = U[cs & isPV], V[cs & isPV]
            if len(pu) < 6: continue
            a0, a1 = np.percentile(pu, [2, 98]); b0, b1 = np.percentile(pvv, [2, 98])
            a0, a1, b0, b1 = max(u0, a0 - R / 2), min(u1, a1 + R / 2), max(v0, b0 - R / 2), min(v1, b1 + R / 2)
            if (a1 - a0) < 1.0 or (b1 - b0) < 1.0: continue
            q = Polygon([tuple(a * u + bv * v) for u, v in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))])
            if q.area < 3.0: continue
            inside = q.intersection(blob).area / q.area
            if inside >= TAB_INSIDE:
                out.append((q, th)); continue
            part = q.intersection(blob)
            if depth < 3 and part.area > 30.0:
                # split along the long side of the cell and re-analyse each half with its own axis
                Lu, Lv = a1 - a0, b1 - b0
                if Lu >= Lv: halves = [((a0, b0), (0.5 * (a0 + a1), b1)), ((0.5 * (a0 + a1), b0), (a1, b1))]
                else: halves = [((a0, b0), (a1, 0.5 * (b0 + b1))), ((a0, 0.5 * (b0 + b1)), (a1, b1))]
                for (p0, q0), (p1, q1) in halves:
                    h = Polygon([tuple(a * u + bv * v) for u, v in ((p0, q0), (p1, q0), (p1, q1), (p0, q1))]).intersection(blob)
                    if h.area > 3.0: out += _tables(h, blob, lum, bg, pv, X0, Z0, R, depth + 1)
            else:
                for g in G.polys_of(part, 3.0): out.append((g.simplify(0.25), th))
    return out


def pv_tables():
    PV = json.load(open(os.path.join(HERE, 'dom_pv.json')))
    out = {}
    for reg, R_ in PV['regions'].items():
        sh = R_['shift_m']; tabs = []
        for bi, b in enumerate(R_['blocks']):
            blk = Polygon(b['ring']).buffer(0)
            img = affinity.translate(blk, sh, 0.0)
            rgb, X0, Z0, R = crop(img)
            f, lum, bg = lum_bg(rgb, R)
            blob = img.buffer(0.5, join_style=2)
            inb = raster(blob, X0, Z0, R, lum.shape)
            pv = (lum < bg - PV_DROP) & (f[..., 2] > f[..., 1] - 6) & (f[..., 2] - f[..., 0] < TEAL) & (inb > 0)
            for q, th in _tables(blob, blob, lum, bg, pv, X0, Z0, R):
                qq = affinity.translate(q, -sh, 0.0)
                tabs.append(dict(block=bi, ring=[[round(x, 2), round(z, 2)] for x, z in list(qq.exterior.coords)[:-1]],
                                 area=round(qq.area, 1), axis_deg=round(th, 1)))
        out[reg] = dict(shift_m=sh, n=len(tabs), area_m2=round(sum(t['area'] for t in tabs), 0),
                        block_area_m2=R_['area_m2'], tables=tabs)
        print(f'PV {reg:9s}: {len(R_["blocks"])} blocks {R_["area_m2"]:.0f} m2 -> {len(tabs)} tables {out[reg]["area_m2"]:.0f} m2')
    return out


SHADOW_V = np.array([math.sin(math.radians(6.6)), -math.cos(math.radians(6.6))])   # 2024 shadow direction (x, z): az 6.6 deg
UNIT_SHADOW = 12.0   # a unit must be >= 12 darker on its shadow side (1-m strips N vs S of the box): it stands >~ 1 m above the
                     # deck; PV tables (0.75 m) give a median 2-6 (p90 ~30 at table rows) [inf, measured on 120 PV tables]


def shadow_contrast(poly):
    """mean NAIP luminance of a 0.9-m strip on the sun side (south) minus the shadow side (NNE) of an imaged box."""
    from shapely import contains_xy
    n = affinity.translate(poly, SHADOW_V[0] * 0.9, SHADOW_V[1] * 0.9).difference(poly.buffer(0.15))
    sS = affinity.translate(poly, -SHADOW_V[0] * 0.9, -SHADOW_V[1] * 0.9).difference(poly.buffer(0.15))

    def ml(g):
        x0, z0, x1, z1 = g.bounds
        X, Z = np.meshgrid(np.arange(x0, x1, 0.25), np.arange(z0, z1, 0.25))
        m = contains_xy(g, X, Z)
        return float(DL.sample_lum(X[m], Z[m]).mean()) if m.sum() >= 3 else float('nan')
    return ml(sS) - ml(n)


def units():
    import cv2
    W, feats, info = G.build_world(0)
    PVb = json.load(open(os.path.join(HERE, 'dom_pv.json')))
    pvw = unary_union([Polygon(b['ring']).buffer(0) for r in PVb['regions'].values() for b in r['blocks']])
    out = {}
    skip = ('drum', 'lantern', 'monitor', 'penthouse', 'walk', 'vest')
    for s in W.S:
        if not s.top or (isinstance(s.style, str) and s.style in skip): continue
        deck = s.roof.buffer(-UNIT_EDGE, join_style=2)
        if s.holes: deck = deck.difference(unary_union(s.holes).buffer(1.0, join_style=2))
        dw = G.wld(deck).buffer(0).difference(pvw.buffer(1.2, join_style=2))
        dw = G._clean(dw, 20.0)
        if dw.is_empty: continue
        k = lean_of(s.bld, dw.centroid.x)
        img = affinity.translate(dw, k * s.h, 0.0)
        rgb, X0, Z0, R = crop(img)
        f, lum, bg = lum_bg(rgb, R)
        m = raster(img, X0, Z0, R, lum.shape)
        ob = ((lum < bg - UNIT_DROP) & (m > 0)).astype(np.uint8)
        ob = cv2.morphologyEx(ob, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        ob = cv2.morphologyEx(ob, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) & m
        n, lab, stt, _ = cv2.connectedComponentsWithStats(ob, connectivity=8)
        us = []
        for i in range(1, n):
            A = stt[i, cv2.CC_STAT_AREA] * R * R
            if A < UNIT_A[0] or A > UNIT_A[1]: continue
            cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(float)
            if len(c) < 3: continue
            g = Polygon([(X0 + (u + 0.5) * R, Z0 + (v + 0.5) * R) for u, v in c]).buffer(0.5 * R, join_style=2)
            rr = g.minimum_rotated_rectangle
            e = list(rr.exterior.coords)
            L1, L2 = math.dist(e[0], e[1]), math.dist(e[1], e[2])
            wmin, wmax = min(L1, L2), max(L1, L2)
            if wmin < UNIT_W or g.area / max(rr.area, 1e-6) < UNIT_FILL or wmax / wmin > UNIT_ASPECT: continue
            sc_ = shadow_contrast(rr)
            if not (sc_ >= UNIT_SHADOW): continue
            hu = next(h for a_, h in UNIT_H if rr.area < a_)
            q = affinity.translate(rr, -k * (s.h + hu), 0.0).intersection(dw)
            for qq in G.polys_of(q, 2.0):
                qq = qq.minimum_rotated_rectangle if qq.area / max(qq.minimum_rotated_rectangle.area, 1e-6) > 0.85 else qq
                us.append(dict(ring=[[round(x, 2), round(z, 2)] for x, z in list(qq.exterior.coords)[:-1]], area=round(qq.area, 1),
                               h=hu, img_area=round(A, 1), shadow_contrast=round(float(sc_), 1)))
        out[s.key] = dict(bld=s.bld, deck_h=round(s.deck, 2), lean_east=round(k, 3), n=len(us), area_m2=round(sum(u['area'] for u in us), 0), units=us)
        print(f'units {s.key:16s} deck {s.deck:5.2f} lean {k:.3f}: {len(us)} units, {out[s.key]["area_m2"]:.0f} m2')
        # QA overlay (local): the imaged deck, object pixels and the boxes at their imaged position
        from PIL import Image, ImageDraw
        sc = 2
        im = Image.fromarray(rgb).convert('RGB')
        ov = np.array(im); ov[ob > 0] = (0.5 * ov[ob > 0] + np.array([127, 0, 0])).astype(np.uint8)
        im = Image.fromarray(ov).resize((ov.shape[1] * sc, ov.shape[0] * sc), Image.NEAREST); dr = ImageDraw.Draw(im)
        P = lambda x, z: ((x - X0) / R * sc, (z - Z0) / R * sc)  # noqa: E731
        for p in G.polys_of(img):
            dr.line([P(*c) for c in p.exterior.coords], fill=(0, 160, 255), width=1)
        for u in us:
            dr.polygon([P(x + k * (s.h + u['h']), z) for x, z in u['ring']], outline=(255, 255, 0))
        im.save(os.path.join(OUT_QA, f'dom_roof_{s.key}.png'))
    return out


def main():
    res = dict(generated_by='tools/blender/dom_roofobs.py', image='NAIP 2024 world raster 0.5 m (refs/cache/naip/naip_2024_world_0.5m.png), '
               'public domain; used as a measurement only', frame='ltp-nad83-2011 world (x east, z south), lean-free',
               params=dict(pv_drop=PV_DROP, aisle_max=AISLE_MAX, aisle_min_m=AISLE_MIN, cell_min=CELL_MIN, unit_drop=UNIT_DROP,
                           unit_area_m2=UNIT_A, unit_min_w=UNIT_W, unit_fill=UNIT_FILL, unit_aspect=UNIT_ASPECT, unit_h=UNIT_H),
               tags=dict(pv_tables='obs extents (NAIP 2024, +-0.5 m); module rows inside a table inf (textures)',
                         units='obs extents (NAIP 2024, +-0.7 m, light units incl. their short shadow); heights inf by plan size; type inf'))
    os.makedirs(OUT_QA, exist_ok=True)
    res['pv_tables'] = pv_tables()
    res['units'] = units()
    json.dump(res, open(OUT_JSON, 'w'), indent=1)
    print('->', OUT_JSON)


if __name__ == '__main__':
    main()
