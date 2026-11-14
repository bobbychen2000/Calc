import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_plot import tci_img, umb_img
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
fig, axs = plt.subplots(2, 4, figsize=(20, 11))
col = 0
for rw in A['runways']:
    for e in rw['ends']:
        c = np.array(e['end']['xz']); x0, x1 = c[0] - 160, c[0] + 160
        if e['id'] in ('18L', '18R'): z0, z1 = c[1] - 230, c[1] + 170
        else: z0, z1 = c[1] - 170, c[1] + 230
        for row, (img, ext) in enumerate((tci_img('S2B', x0, z0, x1, z1), umb_img(x0, z0, x1, z1))):
            ax = axs[row, col]
            ax.imshow(img, extent=ext, cmap='gray', interpolation='nearest')
            for key, colr in (('outline', 'yellow'), ('shoulders', 'orange')):
                ax.add_patch(MP(rw[key]['ring'], closed=True, fill=False, ec=colr, lw=0.8))
            for bp in rw['blast_pads']:
                ax.add_patch(MP(bp['ring'], closed=True, fill=False, ec='magenta', lw=1.0))
            cl = np.array(rw['centreline']['pts']); ax.plot(cl[:, 0], cl[:, 1], 'c-', lw=0.6)
            ax.plot(*e['osm_end_node']['xz'], 'wo', ms=5, mfc='none')
            ax.plot(*e['end']['xz'], 'r+', ms=12, mew=2)
            ax.plot(*e['dthr']['xz'], 'g+', ms=12, mew=2)
            al = np.array(e['approach_lights']['line']); ax.plot(al[:, 0], al[:, 1], 'y:', lw=1)
            for t in A['taxiways']:
                p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '-', color='lime', lw=0.6)
            ax.set_xlim(x0, x1); ax.set_ylim(z1, z0)
            ax.set_title(f"{e['id']} end - {'S2B 2026-10-14 TCI' if row == 0 else 'Umbra 2024-06-02 (+3.4 m E)'}", fontsize=9)
            ax.tick_params(labelsize=6)
        col += 1
fig.suptitle('QA C1: runway ends. red + placed end, green + DTHR, white o OSM end node, yellow = runway outline, orange = shoulders, magenta = blast pad (AIP size), lime = taxiway centrelines. Axes: world x east / z south (m).\nContains modified Copernicus Sentinel data 2026; Umbra SAR Open Data (CC BY 4.0); (c) OpenStreetMap contributors (ODbL)', fontsize=9)
plt.tight_layout(); plt.savefig('/home/user/Calc/sha3d/docs/phase1/qa/qa_rwy_ends.jpg', dpi=75)
