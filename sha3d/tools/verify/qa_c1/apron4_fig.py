import sys, json, numpy as np
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/common'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/airport')
import frame as F
from acplan import planform, CLS_REF, CLASS_MAX
from qa_plot import tci_img, fullres_img
from shapely.geometry import Polygon
from shapely.ops import unary_union
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json')); T = json.load(open('/home/user/Calc/sha3d/data/sha_taxigraph.json'))
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
by = {s['name']: s for s in S['stands']}
def place(polys, s):
    f = F.hdg_vec(s['hdg']); r = (-f[1], f[0]); n = s['nose']
    return unary_union([Polygon([(n[0] + u * f[0] + v * r[0], n[1] + u * f[1] + v * r[1]) for u, v in p]) for p in polys])
ov = json.load(open('overlaps_max.json'))
names = [n for n in by if n.startswith('4')]
pts = np.array([by[n]['nose'] for n in names])
pe = np.array([l['pts'][-1] for l in T['links'] if l['kind'] == 'push' and l['ref'] in names])
x0, z0 = pts.min(0) - np.array([60, 60]); x1 = pe[:, 0].max() + 60; z1 = pts.max(0)[1] + 60
fig, axs = plt.subplots(1, 2, figsize=(16, 9))
for ax, (img, ext, lab) in zip(axs, (tci_img('S2B', x0, z0, x1, z1, res=2.0) + ('S2B 2026-10-14 TCI',), fullres_img('umbra_fullres_stands', x0, z0, x1, z1, res=0.6) + ('Umbra 2024-06-02 (+3.4 m E)',))):
    ax.imshow(img, extent=ext, cmap='gray', interpolation='nearest')
    for n in names:
        s = by[n]; _, L, sp, w, sw = CLS_REF[s['cls']]; smax, lmax = CLASS_MAX[s['cls']]
        pr = place(planform(L, sp, w, sw), s); pm = place(planform(lmax, smax, w, sw), s)
        for g, st in ((pr, dict(ec='yellow', lw=0.9)), (pm, dict(ec='orange', lw=0.7, ls='--'))):
            for p in getattr(g, 'geoms', [g]): ax.add_patch(MP(np.array(p.exterior.coords), closed=True, fill=False, **st))
        ax.annotate(f"{n} {s['cls']}", s['nose'], color='cyan', fontsize=8, xytext=(4, -4), textcoords='offset points')
    for a, b, *_ in ov:
        if a in by and b in by and a.startswith(('4', '6')):
            def pmx(s):
                _, L, sp, w, sw = CLS_REF[s['cls']]; smax, lmax = CLASS_MAX[s['cls']]; return place(planform(lmax, smax, w, sw), s)
            inter = pmx(by[a]).intersection(pmx(by[b]))
            for p in getattr(inter, 'geoms', [inter]):
                if p.area > 0: ax.add_patch(MP(np.array(p.exterior.coords), closed=True, fill=True, fc='red', ec='red'))
    for l in T['links']:
        if l['kind'] == 'push' and l['ref'] in names:
            q = np.array(l['pts']); ax.plot(q[:, 0], q[:, 1], '-', color='magenta', lw=1.2)
    for t in A['taxiways']:
        q = np.array(t['pts']); ax.plot(q[:, 0], q[:, 1], '-', color='lime', lw=0.6)
    ax.set_xlim(x0, x1); ax.set_ylim(z1, z0); ax.set_title(lab, fontsize=9); ax.tick_params(labelsize=7)
fig.suptitle('QA C1: west remote apron (Apron Nr. 4). yellow = reference planform of the data class, orange dashed = sfo3d CLASS_MAX planform of the same class, red = overlap at class max,\nmagenta = push link (stop -> junction, 190-194 m onto TWY D), lime = taxiways. Contains modified Copernicus Sentinel data 2026; Umbra SAR Open Data (CC BY 4.0); (c) OpenStreetMap contributors', fontsize=9)
plt.tight_layout(); plt.savefig('/home/user/Calc/sha3d/docs/phase1/qa/qa_apron4_classes_push.jpg', dpi=72)
