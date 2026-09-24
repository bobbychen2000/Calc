"""Bridge checks: docked bridge (attach -> door) length and interference with other stands' aircraft and bridges."""
import json, math
import numpy as np
from common import *
from stview import w2st, st2w
from check import plan_mask, RES, S0, T1, Wd, Hd, building_mask
import stand_defs
from export_stands import door_st
S = {s['name']: s for s in stand_defs.STANDS}
data = json.load(open(ROOT + '/data/sfo_stands.json'))
masks = {n: plan_mask(s) for n, s in S.items()}
segs = []
for st in data['stands']:
    s = S[st['name']]
    for b in st['bridges']:
        a = w2st(*b['attach']); d = door_st(s, b['door'])
        segs.append((st['name'], b['gate'], a, d))
issues = []
for name, gate, a, d in segs:
    L = math.hypot(d[0] - a[0], d[1] - a[1])
    if L > 48: issues.append((name, gate, f'long bridge {L:.1f} m'))
    if L < 12: issues.append((name, gate, f'short bridge {L:.1f} m'))
    # interference with other stands' aircraft
    for n2, m in masks.items():
        if n2 == name: continue
        hit = 0
        for u in np.linspace(0.05, 0.95, 40):
            p = (a[0] + (d[0] - a[0]) * u, a[1] + (d[1] - a[1]) * u)
            i, j = int((T1 - p[1]) / RES), int((p[0] - S0) / RES)
            if 0 <= i < Hd and 0 <= j < Wd and m[i, j]: hit += 1
        if hit: issues.append((name, gate, f'crosses aircraft at {n2} ({hit}/40)'))
def inter(p1, p2, p3, p4):
    def cr(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = cr(p3, p4, p1), cr(p3, p4, p2), cr(p1, p2, p3), cr(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)
for i in range(len(segs)):
    for j in range(i + 1, len(segs)):
        if segs[i][0] == segs[j][0]: continue
        if inter(segs[i][2], segs[i][3], segs[j][2], segs[j][3]): issues.append((segs[i][0], segs[j][0], 'bridges cross'))
print(len(segs), 'bridges;', len(issues), 'issues'); [print('  ', x) for x in issues]
