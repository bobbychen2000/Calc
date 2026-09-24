#!/usr/bin/env python3
"""Split the SFO terminal complex (SFO Museum geometry) into building parts with heights, and precompute for every
wall edge the height of whatever lies directly outside it, so the renderer can draw each wall only where it is
actually exposed (no coincident walls, no z-fighting).

Parts: boarding areas (piers) A-G, terminal halls (terminal polygon minus its boarding areas), and connectors
(rest of the complex). Heights are approximate except the International Terminal hall (up to 83 ft, published).
Output: data/sfo_buildings.json and data/sfo_buildings.js (same JSON as an ES module). World frame = that of
data/sfo_airport.json (tools/geo_frame.py; no projection is done here).
"""
import json, math, os
import numpy as np, cv2
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
RES = 0.5
xs = [p[0] for p in D['terminalComplex'][0][0]]; zs = [p[1] for p in D['terminalComplex'][0][0]]
X0, Z0 = min(xs) - 20, min(zs) - 20; X1, Z1 = max(xs) + 20, max(zs) + 20
W, H = int((X1 - X0) / RES), int((Z1 - Z0) / RES)
def px(pts): return np.array([[(x - X0) / RES, (z - Z0) / RES] for x, z in pts], np.float64)
def fill(mask, rings, holes=True, val=1):
    cv2.fillPoly(mask, [np.round(px(rings[0]) * 16).astype(np.int32)], val, shift=4)
    if holes:
        for h in rings[1:]: cv2.fillPoly(mask, [np.round(px(h) * 16).astype(np.int32)], 0, shift=4)
    return mask
def m(): return np.zeros((H, W), np.uint8)

CX = m(); fill(CX, D['terminalComplex'][0])
BA = {b['letter'] if b.get('letter') else b['name'][-1]: fill(m(), b['polys'][0]) & CX for b in D['boardingAreas']}
TM = {t['name']: fill(m(), t['polys'][0]) & CX for t in D['terminals']}
HALL_H = {'Harvey Milk Terminal 1': 20.0, 'Terminal 2': 19.0, 'Terminal 3': 21.0, 'International Terminal': 25.3}
PIER_H, CONN_H = 14.6, 12.0
baU = np.zeros_like(CX)
for k, v in BA.items(): baU |= v
parts = []  # (label mask, meta)
for k, v in BA.items(): parts.append((v, {'kind': 'pier', 'name': 'Boarding Area ' + k, 'h': PIER_H}))
tU = np.zeros_like(CX)
for name, v in TM.items():
    hall = v & (1 - ndi.binary_dilation(baU, iterations=2).astype(np.uint8))
    hall = ndi.binary_opening(hall, iterations=3).astype(np.uint8)
    parts.append((hall, {'kind': 'hall', 'name': name, 'h': HALL_H.get(name, 20.0)}))
    tU |= v
conn = CX & (1 - ndi.binary_dilation(baU | tU, iterations=1).astype(np.uint8))
conn = ndi.binary_opening(conn, iterations=2).astype(np.uint8)
parts.append((conn, {'kind': 'connector', 'name': 'Connector', 'h': CONN_H}))
# thin structures (sky bridges / corridors < ~14 m wide) become elevated walkways instead of full-height buildings
def split_thin(mk, r_px=int(7 / RES)):
    se = np.ones((3, 3), bool)
    core = ndi.binary_opening(mk > 0, structure=se, iterations=r_px)
    core = ndi.binary_dilation(core, structure=se, iterations=2) & (mk > 0)
    thin = (mk > 0) & ~core
    thin = ndi.binary_opening(thin, iterations=1)
    return core.astype(np.uint8), thin.astype(np.uint8)
split = []; THIN = np.zeros_like(CX)
for mk, meta in parts:
    core, thin = split_thin(mk)
    split.append((core, meta))
    if thin.sum() * RES * RES > 150: split.append((thin, {'kind': 'walkway', 'name': meta['name'] + ' walkway', 'h': 10.5, 'y0': 6.0})); THIN |= thin
parts = split
# label raster: part index + height raster
LAB = np.full((H, W), -1, np.int32)
for i, (mk, meta) in enumerate(parts):
    LAB[(mk > 0) & (LAB < 0)] = i
HGT = np.zeros((H, W), np.float32)
for i, (mk, meta) in enumerate(parts): HGT[LAB == i] = meta['h'] if meta['kind'] != 'walkway' else 0.0  # walkways do not hide neighbouring walls
# fill tiny gaps inside the complex with the nearest (non-walkway) part so there are no holes between parts
gap = (CX > 0) & (LAB < 0) & (ndi.distance_transform_edt(LAB < 0) < 4 / RES)
if gap.any():
    idx = ndi.distance_transform_edt(LAB < 0, return_distances=False, return_indices=True)
    LAB[gap] = LAB[idx[0][gap], idx[1][gap]]; HGT[gap] = HGT[idx[0][gap], idx[1][gap]]

def world(p): return [round(float(X0 + p[0] * RES), 2), round(float(Z0 + p[1] * RES), 2)]
out = []
for i, (mk, meta) in enumerate(parts):
    lm = (LAB == i).astype(np.uint8)
    cs, hier = cv2.findContours(lm, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None: continue
    hier = hier[0]
    for j, c in enumerate(cs):
        if hier[j][3] != -1 or cv2.contourArea(c) * RES * RES < 250: continue
        rings = [c]; k = hier[j][2]
        while k != -1:
            if cv2.contourArea(cs[k]) * RES * RES > 60: rings.append(cs[k])
            k = hier[k][0]
        R = []; B = []
        for r in rings:
            a = cv2.approxPolyDP(r, 0.9 / RES, True)[:, 0, :].astype(np.float64)
            pts = [world((p[0] + 0.5, p[1] + 0.5)) for p in a]
            # for every edge: what is outside? sample 1.2 m outward at 3 points along the edge
            n = len(pts); base = []
            area = sum(pts[q][0] * pts[(q + 1) % n][1] - pts[(q + 1) % n][0] * pts[q][1] for q in range(n)) / 2
            for q in range(n):
                p0, p1 = np.array(pts[q]), np.array(pts[(q + 1) % n]); L = np.linalg.norm(p1 - p0)
                if L < 1e-6: base.append(0); continue
                d = (p1 - p0) / L; nrm = np.array([-d[1], d[0]])
                # outward normal: for a ring with positive raw area (x,z) the left normal points inward
                if (area > 0) == (len(R) == 0): nrm = -nrm
                hs = []
                for t in (0.25, 0.5, 0.75):
                    s = p0 + (p1 - p0) * t + nrm * 1.2
                    ix, iy = int((s[0] - X0) / RES), int((s[1] - Z0) / RES)
                    if 0 <= ix < W and 0 <= iy < H and LAB[iy, ix] >= 0 and LAB[iy, ix] != i: hs.append(float(HGT[iy, ix]))
                    else: hs.append(0.0)
                base.append(round(min(hs), 2))
            R.append(pts); B.append(base)
        # principal axis (for skylights / roof features)
        P = np.array(R[0]); c0 = P.mean(0); cov = np.cov((P - c0).T); ev, evec = np.linalg.eigh(cov); ax = evec[:, 1]
        ext = (P - c0) @ ax; wid = (P - c0) @ np.array([-ax[1], ax[0]])
        out.append({**meta, 'rings': R, 'base': B, 'axis': [round(float(ax[0]), 4), round(float(ax[1]), 4)], 'center': [round(float(c0[0]), 1), round(float(c0[1]), 1)],
                    'len': round(float(ext.max() - ext.min()), 1), 'wid': round(float(wid.max() - wid.min()), 1), 'area': round(float(cv2.contourArea(c)) * RES * RES)})
print(len(out), 'parts:', [(o['kind'], o['name'], len(o['rings'][0])) for o in out])
# complex outline rings (apron-level base walls 0-5 m)
cxr = []
BASE = (CX & (1 - THIN)).astype(np.uint8); BASE = ndi.binary_opening(BASE, iterations=2).astype(np.uint8)
cs, hier = cv2.findContours(BASE, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
for c in cs:
    if cv2.contourArea(c) * RES * RES < 60: continue
    a = cv2.approxPolyDP(c, 0.9 / RES, True)[:, 0, :].astype(np.float64)
    cxr.append([world((p[0] + 0.5, p[1] + 0.5)) for p in a])
_doc = {'frame': D.get('frameId', 'equirect-v1'), 'complex': cxr, 'parts': out, 'note': 'derived from SFO Museum footprints; heights approximate except ITB hall (83 ft)'}
json.dump(_doc, open(os.path.join(ROOT, 'data', 'sfo_buildings.json'), 'w'), separators=(',', ':'))
open(os.path.join(ROOT, 'data', 'sfo_buildings.js'), 'w').write('// Terminal building parts derived from SFO Museum footprints by tools/build_terminal_parts.py\nexport const BUILDINGS = ' + json.dumps(_doc, separators=(',', ':')) + ';\n')
print('bytes', os.path.getsize(os.path.join(ROOT, 'data', 'sfo_buildings.json')))
# debug image
img = np.zeros((H, W, 3), np.uint8)
cols = [(200, 120, 60), (60, 160, 220), (90, 200, 90), (220, 90, 160), (160, 160, 60), (80, 80, 220), (200, 200, 200), (120, 60, 200), (60, 220, 200), (220, 160, 90), (150, 90, 90), (90, 150, 150)]
for i in range(len(parts)): img[LAB == i] = cols[i % len(cols)]
cv2.imwrite(os.path.join(ROOT, 'out', 'details', 'parts.png'), cv2.resize(img, (W // 3, H // 3)))
