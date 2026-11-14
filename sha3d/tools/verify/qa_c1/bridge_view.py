import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_plot import fullres_img
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json')); A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
by = {s['name']: s for s in S['stands']}
COL = {'present': 'lime', 'present_retracted': 'cyan', 'unclear': 'yellow', 'absent': 'red', 'shared': 'orange', 'none': '0.6'}
def view(names, out, title, pad=45, res=0.3, ncols=None):
    pts = np.array([by[n]['nose'] for n in names] + [b['rotunda'] for n in names for b in by[n]['bridges']])
    x0, z0 = pts.min(0) - pad; x1, z1 = pts.max(0) + pad
    img, ext = fullres_img('umbra_fullres_stands', x0, z0, x1, z1, res=res, shift_en=(3.4, 0))
    w = (x1 - x0) / 25; h = (z1 - z0) / 25
    fig, ax = plt.subplots(figsize=(min(w, 22), min(h, 22) + 0.6))
    ax.imshow(img ** 0.7, extent=ext, cmap='gray', interpolation='nearest')
    for b in A['buildings']:
        if b.get('ring'): ax.add_patch(MP(b['ring'], closed=True, fill=False, ec='deepskyblue', lw=0.6, alpha=0.6))
    for n in names:
        s = by[n]; c = COL.get(s['bridge_status'], 'w')
        ax.plot(*s['nose'], 'o', color=c, ms=4)
        ax.annotate(f"{n} {s['bridge_status']}", s['nose'], color=c, fontsize=7, xytext=(3, 3), textcoords='offset points')
        for b in s['bridges']:
            ax.plot([b['rotunda'][0], b['cab'][0]], [b['rotunda'][1], b['cab'][1]], '-', color=c, lw=1.0, alpha=0.8)
            ax.plot(*b['rotunda'], 's', color='magenta', ms=3)
    ax.set_xlim(x0, x1); ax.set_ylim(z1, z0)
    ax.set_title(title + '\nUmbra SAR 2024-06-02 full res (+3.4 m E), north up, world x/z m; line = bridge record rotunda->cab; colour = bridge_status (lime present, cyan retracted, yellow unclear, red absent, orange shared). Umbra Open Data CC BY 4.0; OSM ODbL', fontsize=8)
    ax.tick_params(labelsize=6); plt.tight_layout(); plt.savefig(out, dpi=90); plt.close()
groups = {
 'qa_br_t2_middle': [n for n in by if n[:2] == '23' or n in ('240', '240A')],
 'qa_br_t2_north': [n for n in by if n in [str(i) for i in range(220, 232)]],
 'qa_br_t1': [n for n in by if n.startswith('1')],
 'qa_br_t2_south': [n for n in by if n in [str(i) for i in range(256, 276)] + ['258', '259A']],
}
import sys
for k, v in groups.items():
    view(sorted(v), f'{k}.jpg', k)
    print(k, len(v))
