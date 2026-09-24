"""LEGACY: checks the Google-screenshot survey (stand_defs.py), superseded by tools/stands/check_stands.py (24 Sep 2026).
Physical plausibility checks for the stand layout: aircraft vs buildings and aircraft vs aircraft clearances."""
import math, sys, importlib
import numpy as np, cv2
from scipy import ndimage as ndi
from common import *
from stview import w2st
from stands import planform_st, CLS, CLEAR
RES = 0.5
S0, T0, S1, T1 = -1700, -1500, -150, -150
Wd, Hd = int((S1 - S0) / RES), int((T1 - T0) / RES)
def px(pts): return np.array([[(s - S0) / RES, (T1 - t) / RES] for s, t in pts])
def fill(mask, poly, val=1):
    cv2.fillPoly(mask, [np.round(px(poly) * 8).astype(np.int32)], val, shift=3)
def building_mask():
    m = np.zeros((Hd, Wd), np.uint8)
    for poly in D['terminalComplex']:
        fill(m, [w2st(*q) for q in poly[0]])
        for h in poly[1:]: fill(m, [w2st(*q) for q in h], 0)
    for b in D['boardingAreas']:
        fill(m, [w2st(*q) for q in b['polys'][0][0]])
    for s in D['structures']:
        if s['kind'] in ('rail',): continue
        for poly in s['polys']: fill(m, [w2st(*q) for q in poly[0]])
    return m
def plan_mask(st):
    m = np.zeros((Hd, Wd), np.uint8)
    for poly in planform_st(st['nose'], st['hdg'], st['cls']): fill(m, poly)
    return m
def run(stands, verbose=True):
    B = building_mask()
    DTB = ndi.distance_transform_edt(B == 0) * RES
    masks = [plan_mask(s) for s in stands]
    dts = {}
    issues = []
    for i, s in enumerate(stands):
        m = masks[i] > 0
        if not m.any(): issues.append((s['name'], 'outside grid')); continue
        db = float(DTB[m].min())
        s['clr_bldg'] = round(db, 1)
        if db < 3.0: issues.append((s['name'], f'building clearance {db:.1f} m'))
    for i, a in enumerate(stands):
        for j in range(i + 1, len(stands)):
            b = stands[j]
            if math.hypot(a['nose'][0] - b['nose'][0], a['nose'][1] - b['nose'][1]) > 170: continue
            if j not in dts: dts[j] = ndi.distance_transform_edt(masks[j] == 0) * RES
            d = float(dts[j][masks[i] > 0].min())
            need = max(CLEAR[a['cls']], CLEAR[b['cls']])
            if d < 3.0: issues.append((a['name'] + '|' + b['name'], f'PHYSICAL: aircraft clearance {d:.1f} m'))
            elif d < need and verbose: print(f'   note: {a["name"]}|{b["name"]} wingtip clearance {d:.1f} m (ICAO stand design value {need} m)')
    if verbose:
        for s in stands: print(f"{s['name']:>5} cls {s['cls']:2s} bldg {s.get('clr_bldg')}")
        print('ISSUES:', len(issues)); [print('  ', x) for x in issues]
    return issues
if __name__ == '__main__':
    import stand_defs; importlib.reload(stand_defs)
    run(stand_defs.STANDS)
