"""B3: what Copernicus GLO-30 (a DSM) says about airport building heights.

For each airport building in data/sha_airport.json (and the control tower), sample the GLO-30 DEM, the editing mask (EDM)
and the height error mask (HEM) inside the footprint and in a 30-90 m ring around it. Report the median/p90 DSM excess
inside vs the ring. Pixels are 1 arc-second (~26.5 x 30.9 m here), so only large buildings can show up, and the WorldDEM
editing may have flattened the aerodrome.

usage: python3 -I sha3d/tools/standards/dem_building_heights.py sha3d out.json
"""
import json, sys, os, math
import numpy as np
import rasterio
from shapely.geometry import Polygon, Point
from shapely.prepared import prep
root = sys.argv[1]; out = sys.argv[2]
sys.path.insert(0, os.path.join(root, 'tools', 'common'))
import frame  # noqa: E402
D = os.path.join(root, 'refs', 'cache', 'dem', 'glo30_N31_E121')
dem = rasterio.open(os.path.join(D, 'Copernicus_DSM_COG_10_N31_00_E121_00_DEM.tif'))
edm = rasterio.open(os.path.join(D, 'Copernicus_DSM_COG_10_N31_00_E121_00_EDM.tif'))
hem = rasterio.open(os.path.join(D, 'Copernicus_DSM_COG_10_N31_00_E121_00_HEM.tif'))
flm = rasterio.open(os.path.join(D, 'Copernicus_DSM_COG_10_N31_00_E121_00_FLM.tif'))
A = json.load(open(os.path.join(root, 'data', 'sha_airport.json'), encoding='utf-8'))
# read a window covering the extent
lat0, lat1, lon0, lon1 = 31.160, 31.235, 121.300, 121.365
win = rasterio.windows.from_bounds(lon0, lat0, lon1, lat1, dem.transform)
Z = dem.read(1, window=win).astype(float); E = edm.read(1, window=win); H = hem.read(1, window=win).astype(float); FL = flm.read(1, window=win)
T = dem.window_transform(win)
rows, cols = np.indices(Z.shape)
lon = T.c + (cols + 0.5) * T.a; lat = T.f + (rows + 0.5) * T.e
# world coords of every pixel centre
XZ = np.array([frame.ll_to_world(la, lo) for la, lo in zip(lat.ravel(), lon.ravel())]).reshape(Z.shape + (2,))
def stats(mask):
    v = Z[mask]; e = E[mask]; h = H[mask]
    if v.size == 0: return None
    return dict(n=int(v.size), med=float(np.median(v)), p90=float(np.percentile(v, 90)), max=float(v.max()),
                edm=dict(zip(*[x.tolist() for x in np.unique(e, return_counts=True)])), hem_med=float(np.median(h)),
                flm=dict(zip(*[x.tolist() for x in np.unique(FL[mask], return_counts=True)])))
res = []
items = [dict(id=b['id'], role=b.get('role') or b['kind'], name=b.get('name'), ring=b['ring'], area=b['area_m2'],
              h_rule=b['height_m']) for b in A['buildings']]
ct = A['control_tower']
res_t = None
for it in items:
    P = Polygon(it['ring'])
    pin = prep(P); ring = prep(P.buffer(90).difference(P.buffer(30)))
    m_in = np.zeros(Z.shape, bool); m_ring = np.zeros(Z.shape, bool)
    minx, minz, maxx, maxz = P.buffer(90).bounds
    sel = (XZ[..., 0] > minx) & (XZ[..., 0] < maxx) & (XZ[..., 1] > minz) & (XZ[..., 1] < maxz)
    for r, c in zip(*np.nonzero(sel)):
        p = Point(XZ[r, c, 0], XZ[r, c, 1])
        if pin.contains(p): m_in[r, c] = True
        elif ring.contains(p): m_ring[r, c] = True
    si, sr = stats(m_in), stats(m_ring)
    exc = None if not (si and sr) else dict(med=si['med'] - sr['med'], p90=si['p90'] - sr['med'], max=si['max'] - sr['med'])
    res.append(dict(it, ring=None, inside=si, around=sr, excess_m=exc))
    print(f"{it['role'][:18]:18s} {it['area']:9.0f} m2  in n={si['n'] if si else 0:3d} "
          f"med={si['med'] if si else float('nan'):6.2f} p90={si['p90'] if si else float('nan'):6.2f}  ring med={sr['med'] if sr else float('nan'):6.2f}  "
          f"excess med/p90/max = {exc['med'] if exc else float('nan'):5.1f} / {exc['p90'] if exc else float('nan'):5.1f} / {exc['max'] if exc else float('nan'):5.1f}  "
          f"EDM in {si['edm'] if si else None} FLM {si['flm'] if si else None}")
# whole aerodrome: edit mask histogram inside the aerodrome polygon
aer = A['aerodrome']
json.dump(dict(what='GLO-30 DSM samples in/around airport building footprints (B3)', pixel_deg=[T.a, T.e],
               edm_codes='EDM (handbook v5.0 table 6): 1 not edited, 2 infill of external elevation data, 3 interpolated, 4 smoothed, 5 airport editing, 6 raised negative, 10 river', flm_codes='FLM (table 7): 1 edited, 2 not edited/not filled, 3 ASTER, 4 SRTM90, 5 SRTM30, 6 GMTED2010, 7 SRTM30plus, 8 TerraSAR-X radargrammetric, 9 AW3D30', acquisition='TanDEM-X Dec 2010 - Jan 2015 (handbook): T1 was the pre-renovation building then (renovated 2014-2018)', buildings=res),
          open(out, 'w'), indent=1, default=str)

# ---- figure: DSM excess over the airport with building outlines (extent-limited) ----
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import median_filter
figp = sys.argv[3] if len(sys.argv) > 3 else None
if figp:
    ground = median_filter(np.where(E == 1, Z, np.nan), size=25, mode='nearest') if False else None
    # local ground: 10th percentile in a 15-pixel window (robust to buildings)
    from scipy.ndimage import percentile_filter
    g = percentile_filter(Z, 10, size=15)
    exc = Z - g
    fig, ax = plt.subplots(1, 2, figsize=(15, 8.6), gridspec_kw=dict(width_ratios=[1.25, 1]))
    X, Zw = XZ[..., 0], XZ[..., 1]
    m = ax[0].pcolormesh(X, Zw, np.clip(exc, 0, 30), cmap='magma', shading='nearest', vmin=0, vmax=30)
    ax[0].invert_yaxis(); ax[0].set_aspect('equal')
    for b in A['buildings']:
        r = np.array(b['ring'] + [b['ring'][0]]); ax[0].plot(r[:, 0], r[:, 1], color='cyan', lw=0.7)
        if b.get('role') in ('T1', 'T2', 'MU_hangar', 'FBO') or b['id'] == 'osm:way/327473856':
            ax[0].text(r[:, 0].mean(), r[:, 1].mean(), b.get('role') or 'hangar E', color='w', fontsize=8, ha='center')
    ax[0].set_xlim(-1800, 1300); ax[0].set_ylim(1900, -1900)
    ax[0].set_xlabel('x east (m)'); ax[0].set_ylabel('z south (m)')
    ax[0].set_title('GLO-30 DSM minus local 10th-percentile ground (m), airport buildings (OSM) in cyan', fontsize=9)
    plt.colorbar(m, ax=ax[0], shrink=0.7, label='DSM excess (m)')
    ed = ax[1].pcolormesh(X, Zw, E, cmap='tab10', vmin=0.5, vmax=10.5, shading='nearest')
    ax[1].invert_yaxis(); ax[1].set_aspect('equal'); ax[1].set_xlim(-1800, 1300); ax[1].set_ylim(1900, -1900)
    for b in A['buildings']:
        r = np.array(b['ring'] + [b['ring'][0]]); ax[1].plot(r[:, 0], r[:, 1], color='k', lw=0.6)
    cb = plt.colorbar(ed, ax=ax[1], shrink=0.7, ticks=range(1, 11))
    cb.ax.set_yticklabels(['1 not edited', '2 infill', '3 interpolated', '4 smoothed', '5 airport edit', '6 raised neg.', '7 flattened', '8 ocean', '9 lake', '10 river'], fontsize=7)
    ax[1].set_title('GLO-30 editing mask (EDM): hangars sit on airport-edited planes', fontsize=9)
    fig.suptitle('Produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS '
                 'by the European Union and ESA. Acquired Dec 2010 - Jan 2015 (T1 pre-renovation). Footprints (c) OpenStreetMap contributors (ODbL).', fontsize=8)
    fig.tight_layout(); fig.savefig(figp, dpi=100)
