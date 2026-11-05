"""Rooftop mechanical units on the Boarding Area A / G roofs, measured on NAIP 2024 (public domain, USDA FPAC-BC GEO) for the
3-D ITB asset (review round 2, 2026-11-05: "rooftop HVAC units on the parapet line and the bump-out roofs", photo a2).
NAIP is a MEASUREMENT only (extents of dark objects / short shadows on the light membrane), never a texture; the output is
numbers (tools/blender/itb_roofobs.json, committed like tools/blender/dom_roofobs.json, whose method this follows).

    python3 tools/blender/itb_roofobs.py     # -> tools/blender/itb_roofobs.json (+ QA overlays out/buildings3d/itb_roofobs_*.png, local)

Per roof deck (tools/blender/itb_geom: the BA-G main body less its bump-outs, the 10 BA-G bump-out roofs, the BA-A body):
  1. the deck less 1.5 m from its edge (0.8 m on the small bump-out roofs), less the roof pods (+3 m), moved to its imaged
     position: BA-G by the east-only k(x) model of the ITB research (draw_data.k_x_model x height, as build_itb.naip_colours),
     BA-A by the frame model (draw_data.lean_frame)
  2. object pixels: luminance >= UNIT_DROP below the local membrane (9-m median) - a dark unit or the short 2024 shadow (sun az
     186.6, el 72.5: 0.315 m per m of height towards az 6.6) of a light one; open 0.5 m, close 1.0 m
  3. components UNIT_A m2, minimum-rectangle short side >= UNIT_W, fill >= UNIT_FILL, aspect <= UNIT_ASPECT -> the minimum
     rectangle, moved back by the relief of (deck + unit height) and clipped to the deck
  4. height by plan size (not measurable at 0.5 m/px): < 6 m2 1.2 m, < 20 m2 1.8 m, else 2.4 m [inf]
Tags: unit extents [obs, NAIP 2024 2024-05-20, +-0.7 m; a light unit's box includes its ~0.4-0.8 m shadow]; heights, type and
colour [inf]. Photo a2 (BA-G NNE face) shows units on the bump-out roofs and a row of small units behind the NNE parapet.
"""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import itb_geom as G  # noqa: E402
import draw_lib as DL  # noqa: E402
import draw_data as DD  # noqa: E402

OUT_JSON = os.path.join(HERE, 'itb_roofobs.json')
OUT_QA = os.path.join(G.ROOT, 'out', 'buildings3d')
RES = 0.25                     # analysis grid, m (NAIP 0.5 m resampled bilinearly)
UNIT_DROP = 26.0               # as dom_roofobs.py [inf]
UNIT_A = (2.0, 150.0); UNIT_W = 1.0; UNIT_FILL = 0.6; UNIT_ASPECT = 5.0   # [inf; small units allowed: a2 shows ~1-2 m units]
UNIT_H = ((6.0, 1.2), (20.0, 1.8), (1e9, 2.4))


def shift(key, x, z, h):
    if key == 'G':
        return np.array([DD.k_x_model(x) * h, 0.0])
    return np.asarray(DD.lean_frame((x, z), h), float)


def decks():
    out = []
    h = float(G.PIERS['G']['h_main_roof']) - G.PARAPET
    bo = G.bumpouts('G')
    body = G.largest(G.PIER_G.difference(unary_union([b[3] for b in bo]).buffer(0.01)))
    pods = unary_union([g for _, g in G.pod_polys('G')] + [Polygon(G.POD['G3-box']['ring_true_xz'])]).buffer(3.0)
    out.append(('G', 'ba_g_body', body.buffer(-1.5).difference(pods), h))
    for i, b in enumerate(bo):
        out.append(('G', 'ba_g_bump%d' % i, b[3].buffer(-0.8), G.BUMP_H_G))
    h = float(G.PIERS['A']['h_main_roof']) - G.PARAPET
    pods = unary_union([g for _, g in G.pod_polys('A')]).buffer(3.0)
    out.append(('A', 'ba_a_body', G.largest(G.PIER_A).buffer(-1.5).difference(pods), h))
    return out


def sample(x0, z0, nx, nz):
    A, T = DL._naip(); R = T['res']
    xs = x0 + (np.arange(nx) + 0.5) * RES; zs = z0 + (np.arange(nz) + 0.5) * RES
    X, Z = np.meshgrid(xs, zs)
    c = (X - T['x0']) / R - 0.5; r = (Z - T['z0']) / R - 0.5
    c0 = np.floor(c).astype(int); r0 = np.floor(r).astype(int); fc = c - c0; fr = r - r0
    out = 0
    for dr, wr in ((0, 1 - fr), (1, fr)):
        for dc, wc in ((0, 1 - fc), (1, fc)):
            out = out + A[r0 + dr, c0 + dc].astype(float) * (wr * wc)[..., None]
    return out[..., ::-1], X, Z


def detect(key, name, deck, h):
    if deck.is_empty: return [], None
    cx, cz = deck.centroid.coords[0]
    s = shift(key, cx, cz, h)
    img_deck = affinity.translate(deck, s[0], s[1])
    x0, z0, x1, z1 = img_deck.bounds
    nx, nz = int((x1 - x0) / RES) + 2, int((z1 - z0) / RES) + 2
    rgb, X, Z = sample(x0, z0, nx, nz)
    L = rgb.mean(-1)
    import shapely
    inside = shapely.contains_xy(img_deck, X, Z)
    if inside.sum() < 50: return [], None
    Lm = np.where(inside, L, np.nan)
    bg = ndi.generic_filter(np.nan_to_num(Lm, nan=np.nanmedian(Lm)), np.median, size=int(9 / RES) | 1, mode='nearest') \
        if inside.sum() < 40000 else ndi.median_filter(np.nan_to_num(Lm, nan=np.nanmedian(Lm)), size=int(9 / RES) | 1)
    obj = inside & (bg - L >= UNIT_DROP)
    obj = ndi.binary_opening(obj, iterations=1)
    obj = ndi.binary_closing(obj, iterations=2) & inside
    lab, n = ndi.label(obj)
    units = []
    for k in range(1, n + 1):
        m = lab == k
        a = m.sum() * RES * RES
        if not (UNIT_A[0] <= a <= UNIT_A[1]): continue
        pts = np.c_[X[m], Z[m]]
        poly = shapely.MultiPoint(pts).convex_hull.buffer(RES / 2, join_style=2)
        mrr = poly.minimum_rotated_rectangle
        C = np.asarray(mrr.exterior.coords)
        e = sorted(np.linalg.norm(C[i + 1] - C[i]) for i in range(4))
        if e[0] < UNIT_W or e[-1] / max(e[0], 1e-6) > UNIT_ASPECT: continue
        if a / mrr.area < UNIT_FILL: continue
        hu = next(hh for amax, hh in UNIT_H if mrr.area < amax)
        s2 = shift(key, *mrr.centroid.coords[0], h + hu)
        true = affinity.translate(mrr, -s2[0], -s2[1]).intersection(deck.buffer(0.3))
        if true.is_empty or true.area < UNIT_A[0]: continue
        true = true.minimum_rotated_rectangle
        units.append(dict(ring=[[round(float(x), 2), round(float(z), 2)] for x, z in np.asarray(true.exterior.coords)[:-1]],
                          area=round(float(true.area), 1), h=hu, contrast=round(float(np.mean(bg[m] - L[m])), 1)))
    return units, (rgb, img_deck, X, Z, units, s)


def main():
    res = dict(generated_by='tools/blender/itb_roofobs.py', image='NAIP 2024 (2024-05-20, 0.5 m, public domain), reference measurement only',
               params=dict(res=RES, unit_drop=UNIT_DROP, unit_area=UNIT_A, unit_w=UNIT_W, fill=UNIT_FILL, aspect=UNIT_ASPECT, heights=UNIT_H),
               tags=dict(extents='obs NAIP 2024 (+-0.7 m)', heights='inf (by plan size)', type_colour='inf'), decks={})
    qa = []
    for key, name, deck, h in decks():
        units, dbg = detect(key, name, deck, h)
        res['decks'][name] = dict(pier=key, deck_h=round(h, 2), n=len(units), units=units)
        print('%-12s deck %.1f m  units %d  area %.0f m2' % (name, h, len(units), sum(u['area'] for u in units)))
        if dbg is not None and name in ('ba_g_body', 'ba_a_body'):
            qa.append((name, dbg))
    json.dump(res, open(OUT_JSON, 'w'), indent=1)
    try:
        from PIL import Image, ImageDraw
        os.makedirs(OUT_QA, exist_ok=True)
        for name, (rgb, img_deck, X, Z, units, s) in qa:
            im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
            x0, z0 = X[0, 0] - RES / 2, Z[0, 0] - RES / 2
            px = lambda x, z: ((x - x0) / RES, (z - z0) / RES)  # noqa: E731
            d.line([px(x, z) for x, z in np.asarray(img_deck.exterior.coords)] if img_deck.geom_type == 'Polygon' else [], fill=(0, 160, 255))
            for u in units:
                R = np.asarray(u['ring'])
                s2 = shift(name[3].upper(), R[:, 0].mean(), R[:, 1].mean(), res['decks'][name]['deck_h'] + u['h'])
                d.polygon([px(x + s2[0], z + s2[1]) for x, z in R], outline=(255, 0, 0))
            im.save(os.path.join(OUT_QA, 'itb_roofobs_%s.png' % name))
    except Exception as e:  # noqa: BLE001
        print('QA overlay failed:', e)


if __name__ == '__main__':
    main()
