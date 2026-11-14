"""B3: building heights from SAR layover in the Umbra GEC (2024-06-02, UMBRA-05, X band, CC BY 4.0).

Geometry (metadata): incidence 38.08 deg, sensor azimuth 275.50 deg (seen from the scene), i.e. the sensor looks east
from the west. In the ground-projected GEC a point at height h above the ground is displaced towards the sensor by
L = h * cot(38.08 deg) = 1.2763 h (exact cotangent; Fix round 1 corrected the old docstring value 1.2748), along azimuth 275.5 deg. So the roof edge above a west-facing wall appears L metres
west of the wall foot (the wall foot itself shows the wall-ground double bounce), and h = L / 1.2763.

Method: for each target wall (a straight OSM footprint edge facing the sensor), sample the 4x overview (1.4 m) along
range lines (direction 95.5 deg, i.e. away from the sensor) at 2 m spacing along the wall, align every line on the
OSM wall foot (shifted by the measured Umbra-OSM ground offset +6.1 E / -0.9 N), take the median profile, and find
 - the onset of the building's layover: the first point (coming from the west) where the smoothed median profile
   rises above the ground level west of it by half of the step to the layover plateau,
 - the double-bounce peak near the wall foot (checks the alignment).
h = (wall foot - onset) / K, K = 1/tan(38.0798 deg) = 1.2763. The uncertainty combines the edge-fit spread across lines (bootstrap), the 1.4 m
pixel and +-2 m for the footprint / offset.

usage: python3 -I sha3d/tools/standards/umbra_layover.py sha3d OUT.json OUT.png [id#wall,id#wall,...  (panels to plot)]
"""
import json, sys, os, math
import numpy as np
import rasterio
from PIL import Image, ImageDraw
root, outj, outp = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.join(root, 'tools', 'common'))
import frame  # noqa: E402
INC = 38.0798; AZ = 275.4967
K = 1.0 / math.tan(math.radians(INC))           # layover metres per metre of height
UMB = np.array([6.1, 0.9])                     # Umbra - OSM in world (x east, z south)
rv = np.array([math.sin(math.radians(AZ + 180)), -math.cos(math.radians(AZ + 180))])   # range direction (away from sensor)
src = rasterio.open(os.path.join(root, 'refs/cache/imagery/umbra_opendata/umbra_gec_ovr4.tif'))
img = src.read(1).astype(np.float32); inv = ~src.transform
la0, lo0 = frame.world_to_ll(0, 0); la1, lo1 = frame.world_to_ll(1000, 0); la2, lo2 = frame.world_to_ll(0, 1000)
def sample(P):  # P: (..., 2) world xz -> bilinear-free nearest sample
    lat = la0 + P[..., 0] / 1000 * (la1 - la0) + P[..., 1] / 1000 * (la2 - la0)
    lon = lo0 + P[..., 0] / 1000 * (lo1 - lo0) + P[..., 1] / 1000 * (lo2 - lo0)
    c, r = inv * (lon, lat)
    c = np.clip(np.round(c).astype(int), 0, img.shape[1] - 1); r = np.clip(np.round(r).astype(int), 0, img.shape[0] - 1)
    return img[r, c]
A = json.load(open(os.path.join(root, 'data/sha_airport.json'), encoding='utf-8'))
byid = {b['id']: b for b in A['buildings']}
# targets: building id, wall = (start vertex, end vertex) given as world points on the west side; trim m at the ends
def west_walls(b, minlen=30.0):
    ring = np.array(b['ring']); xs = ring[:, 0]
    # longest edge whose outward normal faces the sensor (west): pick edges with normal.x < -0.9
    walls = []
    n = len(ring)
    for i in range(n):
        p, q = ring[i], ring[(i + 1) % n]; d = q - p; L = np.hypot(*d)
        if L < 20: continue
        nrm = np.array([d[1], -d[0]]) / L
        # outward: test a point slightly along the normal
        from shapely.geometry import Polygon, Point
        poly = Polygon(ring)
        mid = (p + q) / 2
        if poly.contains(Point(*(mid + nrm * 1.0))): nrm = -nrm
        if nrm @ (-rv) > 0.95 and L >= minlen: walls.append((p, q, L, nrm))
    return walls
targets = [
    ('China Eastern hangar (way 327613444)', 'osm:way/327613444'),
    ('big hangar E (way 327473856)', 'osm:way/327473856'),
    ('hangar E small (way 327473860)', 'osm:way/327473860'),
    ('SW hangar (way 328013621)', 'osm:way/328013621'),
    ('FBO terminal (way 469610770)', 'osm:way/469610770'),
    ('T1 (way 93184730)', 'osm:way/93184730'),
    ('T2 (relation 21913345)', 'osm:relation/21913345'),
    ('MU office (relation 21913196)', 'osm:relation/21913196'),
    ('building next to MU hangar (way 861029093)', 'osm:way/861029093'),
    ('MU hangar annex S (way 1257868692)', 'osm:way/1257868692'),
    ('T1 south block (way 1443259951)', 'osm:way/1443259951'),
    ('hotel by T2 (way 1576050065)', 'osm:way/1576050065'),
]
res = []; plots = []
s = np.arange(-110, 60.01, 0.7)   # metres along range from the (shifted) wall foot; negative = towards the sensor
def measure(sm):
    """wall foot = steepest drop in [-15, +15] m (end of the facade layover); onset = steepest rise in
    [foot-90, foot-3] m whose plateau (onset..foot) stays above half the step. Returns foot, onset, contrast."""
    gr = np.gradient(sm, s)
    w = (s > -15) & (s < 15); i_f = np.where(w)[0][np.argmin(gr[w])]; foot = s[i_f]
    w2 = (s > foot - 90) & (s < foot - 3)
    if not w2.any(): return foot, None, None
    cand = np.where(w2)[0][np.argsort(gr[w2])[::-1][:6]]
    best = None
    for i_o in cand:
        on = s[i_o]
        pl = np.median(sm[(s > on + 1) & (s < foot - 1)]) if foot - on > 3 else None
        g = np.median(sm[(s > on - 25) & (s < on - 2)])
        if pl is None or not np.isfinite(g): continue
        frac_above = np.mean(sm[(s > on + 1) & (s < foot - 1)] > g + 0.5 * (pl - g))
        score = (pl - g) / max(g, 1e-3) * frac_above
        if frac_above > 0.7 and (best is None or score > best[2]): best = (on, pl / g, score)
    if best is None: return foot, None, None
    return foot, best[0], best[1]
for name, bid in targets:
    b = byid[bid]
    for wi, (p, q, L, nrm) in enumerate(west_walls(b)):
        t = np.linspace(0.1, 0.9, max(5, int(L * 0.8 / 2)))
        foot = p[None, :] + (q - p)[None, :] * t[:, None] + UMB[None, :]
        P = foot[:, None, :] + s[None, :, None] * rv[None, None, :]
        prof = np.sqrt(np.maximum(sample(P), 0))
        sm = np.convolve(np.median(prof, axis=0), np.ones(5) / 5, mode='same')
        f, on, con = measure(sm)
        rng = np.random.default_rng(1); boots = []
        for _ in range(200):
            k = rng.integers(0, prof.shape[0], prof.shape[0])
            f2, o2, _ = measure(np.convolve(np.median(prof[k], axis=0), np.ones(5) / 5, mode='same'))
            if o2 is not None: boots.append(f2 - o2)
        h = None if on is None else (f - on) / K
        sd = float(np.std(boots)) / K if len(boots) > 20 else None
        unc = None if sd is None else math.sqrt(sd ** 2 + 2 * (1.4 / K) ** 2)
        mid = ((p + q) / 2).round(1).tolist()
        r = dict(name=name, id=bid, wall=wi, wall_mid_xz=mid, wall_len_m=round(float(L), 1), lines=int(prof.shape[0]),
                 foot_m=round(float(f), 1), onset_m=None if on is None else round(float(on), 1),
                 contrast=None if con is None else round(float(con), 2), boot_ok=len(boots),
                 height_m=None if h is None else round(float(h), 1), height_unc_m=None if unc is None else round(unc, 1),
                 rule_height_m=b['height_m'])
        res.append(r); plots.append((f"{name} w{wi} @({mid[0]:.0f},{mid[1]:.0f})", sm, on, f, h, unc, con, f'{bid}#{wi}'))
        print(r)
json.dump(dict(what='Building heights from Umbra GEC layover (B3)', incidence_deg=INC, sensor_azimuth_deg=AZ,
               layover_m_per_m=K, umbra_minus_osm=UMB.tolist(), results=res,
               attribution=('Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), '
                            'modified; (c) OpenStreetMap contributors (ODbL 1.0)'),
               licence='Umbra: CC BY 4.0; OSM footprints: ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)',
               registration_note=('umbra_minus_osm is the former A1 taxiway fit (+6.1 E / -0.9 N), not the single Phase-1 '
                                  'value +3.07 E / 0 N of tools/common/umbra_reg.py; see docs/phase1/qa_data.md, '
                                  'Fix round 2 (N4): left for task B3 to re-run')),
          open(outj, 'w'), indent=1)
# plot
sel = sys.argv[4].split(',') if len(sys.argv) > 4 else None
if sel: plots = [p for k in sel for p in plots if p[7] == k]
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
n = len(plots); fig, axs = plt.subplots(math.ceil(n / 4), 4, figsize=(19, 3.0 * math.ceil(n / 4)), squeeze=False)
for ax, (name, sm, on, db, h, unc, con, key) in zip(axs.ravel(), plots):
    ax.plot(s, sm, 'k-', lw=1)
    ax.axvline(0, color='0.6', lw=1, ls='--', label='OSM wall (+Umbra offset)')
    ax.axvline(db, color='tab:red', lw=1, label=f'SAR wall foot {db:.1f} m')
    if on is not None:
        ax.axvline(on, color='tab:blue', lw=1.2, label=f'layover onset {on:.1f} m')
        ax.axvspan(on, db, color='tab:blue', alpha=0.08)
    ax.set_title(f'{name}\n' + (f'h = {h:.1f} +- {unc:.1f} m, contrast {con:.1f}' if (h and unc) else (f'h = {h:.1f} m (unstable)' if h else 'no onset')), fontsize=9)
    ax.set_xlabel('m along range (negative = towards sensor, west)', fontsize=8); ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc='upper right')
for ax in axs.ravel()[n:]: ax.axis('off')
fig.suptitle('Layover heights: h = (SAR wall foot - layover onset) / cot(38.08 deg) = d / 1.275. Median range profiles across each sensor-facing wall (>= 30 m).\n'
             'Umbra Open Data 2024-06-02 GEC (CC BY 4.0) 4x overview; footprints OSM (ODbL).', fontsize=9)
fig.tight_layout(); fig.savefig(outp, dpi=110)
