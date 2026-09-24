"""Export the surveyed stand layout (stand_defs.py) to data/sfo_stands.json/.js in world coordinates (x east, z south).
Each stand lists the jet bridges that serve it: one per hold-room gate (name + aliases) on the aircraft's left side,
two for wide-body stands (L1 + L2)."""
import json, math, os
import numpy as np
from common import *
from stview import st2w, w2st, HDGV
import stand_defs
from stands import CLS, planform_st, hdg_to_st
GATE = {g['name']: g for g in D['gates'] if not g.get('dup')}
OUTLINE = [[w2st(*q) for q in r] for r in rings_all('complex') + rings_all('ba')]
import cv2 as _cv2
_BR = 0.5; _S0, _T1 = -1700.0, -150.0; _BM = np.zeros((int(1350 / _BR), int(1550 / _BR)), np.uint8)
for poly in [p_ for p_ in D['terminalComplex']] + [b['polys'][0] for b in D['boardingAreas']]:
    for i, ring in enumerate(poly):
        pts = np.array([[(w2st(*q)[0] - _S0) / _BR, (_T1 - w2st(*q)[1]) / _BR] for q in ring])
        _cv2.fillPoly(_BM, [np.round(pts * 4).astype(np.int32)], 1 if i == 0 else 0, shift=2)
def crosses(a, b):
    # does the straight bridge line from a to b pass through the building (beyond its first 3 m)?
    L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(2, int(L / 0.5))
    for k in range(n + 1):
        u = k / n; d = u * L
        if d < 3.0: continue
        x = a[0] + (b[0] - a[0]) * u; y = a[1] + (b[1] - a[1]) * u
        i, j = int((_T1 - y) / _BR), int((x - _S0) / _BR)
        if 0 <= i < _BM.shape[0] and 0 <= j < _BM.shape[1] and _BM[i, j]: return True
    return False
WIDE = {'D', 'E', 'EL', 'F'}
def door_st(st, which):
    """approximate door position (s,t) for the stand's class: L1 / L2, on the aircraft's left side"""
    L, B, F = CLS[st['cls']][:3]
    f = hdg_to_st(st['hdg']); left = (-f[1], f[0])
    back = {1: (5.2 if st['cls'] in ('B', 'C', 'CL') else 10.0), 2: 0.33 * L}[which]
    return (st['nose'][0] - f[0] * back + left[0] * (F / 2), st['nose'][1] - f[1] * back + left[1] * (F / 2))
def side_of(st, p):
    """+1 if point p (s,t) is on the stand's left side"""
    f = hdg_to_st(st['hdg']); left = (-f[1], f[0])
    return (p[0] - st['nose'][0]) * left[0] + (p[1] - st['nose'][1]) * left[1]
out = []
for st in stand_defs.STANDS:
    names = [st['name']] + list(st.get('alias', []))
    heads = []
    for n in names:
        g = GATE.get(n)
        if not g or g['level'] != 2: continue
        e = w2st(*g['edge'])
        heads.append((n, e, g))
    bridges = []
    d1 = door_st(st, 1)
    def facade_point(door, near_edge, maxd=60.0):
        # the bridge's fixed end: the point of the building outline nearest to the door (e.g. the tip of a fixed
        # walkway finger), searched within maxd of the hold room's edge point
        best, bd = None, 1e9
        for ring in OUTLINE:
            n = len(ring)
            for i in range(n):
                a = np.array(ring[i]); b = np.array(ring[(i + 1) % n]); ab = b - a; L2 = ab @ ab
                if L2 < 1e-6: continue
                u = np.clip((np.array(door) - a) @ ab / L2, 0, 1); p = a + ab * u
                if np.hypot(*(p - np.array(near_edge))) > maxd: continue
                d = np.hypot(*(p - np.array(door)))
                if d < bd: bd, best = d, p
        return best
    # primary: hold room of the stand name (fall back to the nearest alias); reach check
    heads.sort(key=lambda h: math.hypot(h[1][0] - d1[0], h[1][1] - d1[1]))
    if heads:
        n, e, g = heads[0]
        a1 = tuple(e) if not crosses(e, d1) else (tuple(facade_point(d1, e)) if facade_point(d1, e) is not None else tuple(e))
        bridges.append({'gate': n, 'attach': [round(v, 2) for v in st2w(*a1)], 'door': 1})
        if st['cls'] in WIDE:
            d2 = door_st(st, 2)
            # L2 bridge from a second hold room if one is close, else from the same one
            n2, e2, g2 = heads[1] if len(heads) > 1 and math.hypot(heads[1][1][0] - d2[0], heads[1][1][1] - d2[1]) < 55 else heads[0]
            a2 = tuple(e2) if not crosses(e2, d2) else (tuple(facade_point(d2, e2)) if facade_point(d2, e2) is not None else tuple(e2))
            if math.hypot(a2[0] - a1[0], a2[1] - a1[1]) < 6: # same spot: second bridge 8 m further along the facade, aft
                f = hdg_to_st(st['hdg']); a2 = (a2[0] - f[0] * 8, a2[1] - f[1] * 8)
            bridges.append({'gate': n2, 'attach': [round(v, 2) for v in st2w(*a2)], 'door': 2})
    nose_w = st2w(*st['nose'])
    out.append({'name': st['name'], 'alias': st.get('alias', []), 'letter': st['name'][0], 'nose': [round(nose_w[0], 2), round(nose_w[1], 2)],
                'hdg': round(st['hdg'] % 360, 2), 'cls': st['cls'], 'src': st['src'], 'bridges': bridges})
# remote stands (level-0 records without a letter suffix)
remote = [g for g in D['gates'] if g['level'] == 0 and not g['variant'] and not g.get('dup')]
boxes = []
try:
    for x, z, sz, ang in json.load(open(SP + 'redboxes.json')):
        if 3.5 <= sz <= 7.5: boxes.append([x, z, sz])
except FileNotFoundError: pass
res = {'redBoxes': boxes, 'note': 'Stand layout surveyed from georeferenced satellite screenshots (Google Maps, reference only) against the SFO Museum '
               'building outlines. src=obs: an aircraft was parked there in the imagery; src=inf: stand inferred from jet-bridge '
               'positions / stand pitch (empty in the imagery). Gate names follow the SFO Museum hold-room points; names at pier '
               'tips are the nearest hold room.', 'stands': out,
       'remote': [{'name': g['name'], 'x': g['x'], 'z': g['z']} for g in remote]}
json.dump(res, open(os.path.join(ROOT, 'data', 'sfo_stands.json'), 'w'), separators=(',', ':'))
open(os.path.join(ROOT, 'data', 'sfo_stands.js'), 'w').write('// generated by tools/sat/export_stands.py\nexport const STANDS = ' + json.dumps(res, separators=(',', ':')) + ';\n')
print(len(out), 'stands,', sum(len(s['bridges']) for s in out), 'bridges,', len(remote), 'remote')
from collections import Counter
print(Counter(s['cls'] for s in out), Counter(s['src'] for s in out))
nob = [s['name'] for s in out if not s['bridges']]
print('no bridge:', nob)
