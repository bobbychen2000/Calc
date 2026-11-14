import sys, json, numpy as np
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import frame as F
from qa_plot import tci_img, umb_img
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
gj = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson'))
osm = {f['properties']['@id']: f for f in gj['features'] if f['properties']['@type'] == 'way'}
offs = {r['id']: r for r in json.load(open('twy_offset.json'))}
cases = [('osm:way/93184728', 'A1'), ('osm:way/16714128', 'A2'), ('osm:way/93185708', 'T1'), ('osm:way/467403671', 'T6'), ('osm:way/128706564', 'B (mid)'), ('osm:way/469635785', 'H4 east')]
fig, axs = plt.subplots(2, len(cases), figsize=(4 * len(cases), 8.6))
for k, (wid, lab) in enumerate(cases):
    t = next(x for x in A['taxiways'] if x['id'] == wid)
    c = offs[wid]['mid'] if wid in offs else np.mean(t['pts'], axis=0)
    x0, x1, z0, z1 = c[0] - 90, c[0] + 90, c[1] - 90, c[1] + 90
    o = osm[int(wid.split('/')[-1])]['geometry']['coordinates']
    oxz = np.array([F.ll_to_world(la, lo) for lo, la in o])
    for row, (img, ext) in enumerate((tci_img('S2B', x0, z0, x1, z1, res=1.0), umb_img(x0, z0, x1, z1, res=0.7, shift_en=(3.0, 0)))):
        ax = axs[row, k]; ax.imshow(img, extent=ext, cmap='gray', interpolation='nearest')
        for tt in A['taxiways'] + A['taxilanes']:
            p = np.array(tt['pts']); ax.plot(p[:, 0], p[:, 1], '-', color='lime', lw=0.7)
        ax.plot(oxz[:, 0], oxz[:, 1], '--', color='orange', lw=1.2)
        p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '-', color='red', lw=1.3)
        ax.set_xlim(x0, x1); ax.set_ylim(z1, z0); ax.tick_params(labelsize=6)
        off = offs.get(wid, {}).get('off')
        ax.set_title(f"{lab} {wid.split(':')[1]}\n{'S2B TCI' if row == 0 else 'Umbra +3.0 m E'}; QA offset {off} m", fontsize=8)
fig.suptitle('QA C1: taxiway centrelines. red = sha_airport.json, orange dashed = pinned OSM, lime = other taxiways. Contains modified Copernicus Sentinel data 2026; Umbra SAR Open Data (CC BY 4.0); (c) OpenStreetMap contributors', fontsize=9)
plt.tight_layout(); plt.savefig('/home/user/Calc/sha3d/docs/phase1/qa/qa_twy_offsets.jpg', dpi=80)
