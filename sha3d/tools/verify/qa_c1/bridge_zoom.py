import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_plot import fullres_img
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json')); A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
by = {s['name']: s for s in S['stands']}
SAR = json.load(open('/home/user/Calc/sha3d/data/meas/stand_sar.json'))
names = sys.argv[2].split(',')
out = sys.argv[1]
n = len(names); fig, axs = plt.subplots(2, n, figsize=(3.6 * n, 7.6))
for k, nm in enumerate(names):
    s = by[nm]; c = np.array(s['nose'])
    g = np.array(s["bridges"][0]["rotunda"]) if s["bridges"] else c + 20 * np.array([np.sin(np.radians(s["hdg"])), -np.cos(np.radians(s["hdg"]))])
    m = (c + g) / 2
    x0, x1, z0, z1 = m[0] - 45, m[0] + 45, m[1] - 45, m[1] + 45
    img, ext = fullres_img('umbra_fullres_stands', x0, z0, x1, z1, res=0.2, shift_en=(3.4, 0))
    for row in (0, 1):
        ax = axs[row, k]; ax.imshow(img ** 0.6, extent=ext, cmap='gray', interpolation='nearest')
        if row == 1:
            ax.plot(*c, 'o', color='red', ms=4)
            f = np.array([np.sin(np.radians(s['hdg'])), -np.cos(np.radians(s['hdg']))])
            ax.plot([c[0], c[0] - 45 * f[0]], [c[1], c[1] - 45 * f[1]], '-', color='deepskyblue', lw=0.7)
            for b in s['bridges']:
                ax.plot([b['rotunda'][0], b['cab'][0]], [b['rotunda'][1], b['cab'][1]], '-', color='lime', lw=1)
                ax.plot(*b['rotunda'], 's', color='magenta', ms=4)
            for bb in A['buildings']:
                if bb.get('ring'): ax.add_patch(MP(bb['ring'], closed=True, fill=False, ec='orange', lw=0.6))
        ax.set_xlim(x0, x1); ax.set_ylim(z1, z0); ax.tick_params(labelsize=5)
        sc = SAR['stands'].get(nm, {}) if isinstance(SAR.get('stands'), dict) else {}
        ax.set_title(f"{nm} {s['bridge_status']} hdg {s['hdg']:.0f}" + (f"\nscore {sc.get('bridge_score', '')}" if row == 0 else ''), fontsize=8)
fig.suptitle('QA: Umbra SAR 2024-06-02 full res, north up (+3.4 m E), 90 x 90 m. Bottom: red = OSM stop, blue = stand axis, magenta = OSM gate (rotunda), lime = bridge record, orange = OSM building. Umbra Open Data (CC BY 4.0); OSM (ODbL)', fontsize=8)
plt.tight_layout(); plt.savefig(out, dpi=85)
