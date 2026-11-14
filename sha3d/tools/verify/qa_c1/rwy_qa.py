import sys, json, numpy as np
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import frame as F
from qa_img import s2, umbra
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
M = json.load(open('/home/user/Calc/sha3d/data/meas/rwy_ends.json'))
bands = {sc: {b: s2(sc, b) for b in ('B02', 'B03', 'B04', 'B08')} for sc in ('S2B', 'S2C')}
U = umbra()
res = {}
fig, axs = plt.subplots(4, 1, figsize=(13, 15))
k = 0
for rw in A['runways']:
    n0 = np.array(rw['ends'][0]['osm_end_node']['xz']); n1 = np.array(rw['ends'][1]['osm_end_node']['xz'])
    L = np.linalg.norm(n1 - n0); u = (n1 - n0) / L; v = np.array([-u[1], u[0]])
    half = rw['width_m'] / 2
    placed = {e['id']: e for e in rw['ends']}
    for which, s_lo, s_hi in (('N', -320, 260), ('S', L - 260, L + 320)):
        s = np.arange(s_lo, s_hi, 2.0)
        acr = np.arange(-half + 5, half - 5 + 0.1, 2.5)
        S_, A_ = np.meshgrid(s, acr, indexing='ij')
        X = n0[0] + S_ * u[0] + A_ * v[0]; Z = n0[1] + S_ * u[1] + A_ * v[1]
        ax = axs[k]; k += 1
        out = {}
        for sc in ('S2B', 'S2C'):
            b4 = np.nanmedian(bands[sc]['B04'].sample(X, Z), axis=1); b8 = np.nanmedian(bands[sc]['B08'].sample(X, Z), axis=1)
            ndvi = (b8 - b4) / (b8 + b4)
            ax.plot(s, ndvi, label=f'{sc} NDVI'); out[sc] = ndvi
            ax.plot(s, b4 / 3000, '--', lw=0.8, label=f'{sc} B04/3000')
        ua = np.nanmedian(U.sample(X + 3.4, Z), axis=1)   # Umbra shifted ~3.4 m E (A2 value)
        ax.plot(s, ua / 255, 'k', lw=0.7, label='Umbra amp/255 (shift +3.4 E)')
        # placed ends and derived
        ids = rw['id'].split('/')
        e_n, e_s = placed[ids[0]], placed[ids[1]]
        for e in (e_n, e_s):
            se = e['end']['s_m']; sd = e['dthr']['s_m']
            ax.axvline(se, color='r', lw=1.2); ax.axvline(sd, color='g', lw=1)
        bp = rw['blast_pad_m'][0]
        ax.axvline(e_n['end']['s_m'] - bp, color='m', ls=':', lw=1); ax.axvline(e_s['end']['s_m'] + bp, color='m', ls=':', lw=1)
        ax.axvline(0, color='0.5', ls='--'); ax.axvline(L, color='0.5', ls='--')
        ax.set_xlim(s_lo, s_hi); ax.set_ylim(-0.1, 0.8); ax.grid(alpha=0.3)
        ax.set_title(f"{rw['id']} {'north' if which=='N' else 'south'} end: s = m south of OSM north node; red = placed end, green = DTHR, magenta = placed end +/- AIP blast pad {bp} m, grey = OSM end nodes", fontsize=9)
        ax.legend(fontsize=7, ncol=4, loc='upper right')
        # find grass->pavement edge: NDVI crossing midpoint between grass and pavement levels
        for sc in ('S2B', 'S2C'):
            nd = out[sc]
            if which == 'N':
                grass = np.nanmedian(nd[(s < (e_n['end']['s_m'] - bp - 60))]); pave = np.nanmedian(nd[(s > 20) & (s < 200)])
                mid = (grass + pave) / 2; idx = np.where((nd[:-1] > mid) & (nd[1:] <= mid))[0]
                edge = [s[i] + 2 * (nd[i] - mid) / (nd[i] - nd[i + 1]) for i in idx]
            else:
                grass = np.nanmedian(nd[(s > (e_s['end']['s_m'] + bp + 60))]); pave = np.nanmedian(nd[(s < L - 20) & (s > L - 200)])
                mid = (grass + pave) / 2; idx = np.where((nd[:-1] <= mid) & (nd[1:] > mid))[0]
                edge = [s[i] + 2 * (mid - nd[i]) / (nd[i + 1] - nd[i]) for i in idx]
            res[(rw['id'], which, sc)] = dict(grass=round(float(grass), 3), pave=round(float(pave), 3), edges=[round(float(x), 1) for x in edge])
plt.tight_layout(); plt.savefig('/home/user/Calc/sha3d/docs/phase1/qa/qa_rwy_profiles.png', dpi=80)
for k_, v_ in res.items(): print(k_, v_)
for rw in A['runways']:
    for e in rw['ends']:
        print(rw['id'], e['id'], 'end s', e['end']['s_m'], 'dthr s', e['dthr']['s_m'], 'beyond node', e['end']['beyond_osm_node_m'])
