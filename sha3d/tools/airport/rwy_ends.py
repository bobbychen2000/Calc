"""Measure where the runway ends and the surface changes lie along the OSM runway centrelines, on Sentinel-2 (two
scenes, bands B02 B03 B04 B08, 10 m) and on the Umbra SAR GEC overview (1.4 m), and fit the AIP (mirror) runway
lengths to them.

usage: python3 -I sha3d/tools/airport/rwy_ends.py SHA3D_DIR OUT_JSON OUT_PNG

Along-track coordinate s: metres from the OSM north end node, positive southward along the OSM centreline (world
frame, tools/common/frame.py). Profiles: median across the runway (S2: 9 samples over +-10 m; Umbra: 31 samples over
+-15 m), every 1 m (S2 sampled bilinear, in the S2 registration: positions moved by the geo.md OSM-S2 offset of each
scene). Each edge is fitted with a blurred step v = A + B * Phi((s - s0) / sigma) in a window around its expected
place (scipy curve_fit); the per-band / per-scene scatter gives the uncertainty.

What the edges are (AIP mirror AD 2.12 remarks and column 4, read as short facts):
  18L/36R: surface CONC 0-100 m, ASPH 100-3300 m, CONC 3300-3400 m; blast pads 60 x 60 m at both ends.
    -> S2 brightness steps at the runway end (dark blast pad / bright concrete) and 100 m inside it (concrete /
       asphalt); the SAR shows the concrete / asphalt change too (concrete is smoother: darker at X band).
  18R/36L: CONC full length; blast pads 120 x 75 m at both ends.
    -> the step at the runway end (blast pad / runway) and the blast-pad outer edge 120 m beyond it (grass).
The fitted ends are 'obs' (measured on imagery); the AIP length placed on them is 'inf' (rule in the output).
"""
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import curve_fit
from scipy.special import erf
from scipy.ndimage import median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
import imgsample as IS  # noqa: E402

ROOT = sys.argv[1]
OUT_JSON, OUT_PNG = sys.argv[2], sys.argv[3]
AIP_LEN = {'18L/36R': 3400.0, '18R/36L': 3300.0}

# edges: (name, which runway end it measures, offset of the edge from that end along s (south +), window half
# width, images to use, polarity hint) ; s positions relative to the OSM ends are found by the fit
EDGES = {
    '18L/36R': [
        ('N end: blast pad -> CONC', 'N', 0.0, 'S2'),
        ('N: CONC -> ASPH (+100 m)', 'N', 100.0, 'S2+SAR'),
        ('S: ASPH -> CONC (-100 m)', 'S', -100.0, 'S2+SAR'),
        ('S end: CONC -> blast pad', 'S', 0.0, 'S2+SAR'),
    ],
    '18R/36L': [
        ('N blast pad outer edge (-120 m)', 'N', -120.0, 'S2+SAR'),
        ('N end: blast pad -> runway', 'N', 0.0, 'S2'),
        ('S end: runway -> blast pad', 'S', 0.0, 'SAR'),
        ('S blast pad outer edge (+120 m)', 'S', 120.0, 'S2+SAR'),
    ],
}
WIN = 30.0


def step(s, A, B, s0, sig):
    return A + B * 0.5 * (1 + erf((s - s0) / (math.sqrt(2) * abs(sig) + 1e-6)))


def fit_edge(s, v, centre, half=WIN, sig0=4.0):
    m = (s >= centre - half) & (s <= centre + half) & np.isfinite(v)
    ss, vv = s[m], v[m]
    if len(ss) < 10:
        return None
    g = np.gradient(np.convolve(vv, np.ones(5) / 5, mode='same'))
    k = int(np.argmax(np.abs(g[3:-3]))) + 3
    lo, hi = np.median(vv[:8]), np.median(vv[-8:])
    try:
        p, cov = curve_fit(step, ss, vv, p0=[lo, hi - lo, ss[k], sig0], maxfev=4000)
    except (RuntimeError, ValueError):
        return None
    s0, err = float(p[2]), float(np.sqrt(abs(cov[2, 2])))
    contrast = abs(p[1]) / (np.std(vv - step(ss, *p)) + 1e-9)
    if not (centre - half + 3 < s0 < centre + half - 3) or err > 5 or contrast < 3:
        return None
    return dict(s0=round(s0, 2), se=round(err, 2), sigma=round(abs(float(p[3])), 2), step=round(float(p[1]), 1),
                contrast=round(float(contrast), 1))


def main():
    fc = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
    rws = {f['properties']['tags']['ref']: f for f in fc['features'] if f['properties']['tags'].get('aeroway') == 'runway'}
    s2s = [IS.S2(os.path.join(ROOT, 'refs/cache/s2', n)) for n in IS.S2_OFFSETS]
    um = IS.Umbra(os.path.join(ROOT, 'refs/cache/imagery/umbra_opendata/umbra_gec_ovr4.tif'))
    out = {'method': __doc__.split('\n\n')[1].replace('\n', ' '), 'runways': {}}
    prof_store = {}
    for ref in ('18L/36R', '18R/36L'):
        f = rws[ref]
        c = f['geometry']['coordinates']
        (lo0, la0), (lo1, la1) = c[0], c[-1]
        if la0 < la1:
            (lo0, la0), (lo1, la1) = (lo1, la1), (lo0, la0)
        a = np.array(F.ll_to_world(la0, lo0)); b = np.array(F.ll_to_world(la1, lo1))
        L = float(np.linalg.norm(b - a)); u = (b - a) / L; nrm = np.array([-u[1], u[0]])
        s = np.arange(-300.0, L + 300.0, 1.0)

        def lls(ts):
            P = a[None, None, :] + s[:, None, None] * u + ts[None, :, None] * nrm
            return np.array([[F.world_to_ll(*p) for p in row] for row in P])
        ll9 = lls(np.linspace(-10, 10, 9)); ll31 = lls(np.linspace(-15, 15, 31))
        profs = {}
        for img in s2s:
            E, N = img.en(ll9[..., 1], ll9[..., 0])
            for band in ('B02', 'B03', 'B04', 'B08'):
                profs[f'{img.name[:3]}_{band}'] = np.median(img.sample_en(band, E, N), axis=1)
        uraw = um.sample(ll31[..., 1], ll31[..., 0])
        profs['UMBRA'] = median_filter(np.nanmedian(uraw, axis=1), size=9, mode='nearest')
        ull = lls(np.linspace(-24, 24, 49))
        upk = np.nanpercentile(um.sample(ull[..., 1], ull[..., 0]), 90, axis=1)   # light rows span the width
        prof_peaks = upk
        prof_store[ref] = (s, L, profs, prof_peaks)
        # expected positions: N end at s~0, S end at s~L
        res = []
        for name, end, off, use in EDGES[ref]:
            centre = (0.0 if end == 'N' else L) + off
            fits = {}
            for k, v in profs.items():
                if k == 'UMBRA' and 'SAR' not in use:
                    continue
                if k != 'UMBRA' and 'S2' not in use:
                    continue
                r = fit_edge(s, v, centre, sig0=1.5 if k == 'UMBRA' else 5.0)
                if r:
                    fits[k] = r
            s2v = [r['s0'] for k, r in fits.items() if k != 'UMBRA']
            per_scene = {}
            for sc in ('S2B', 'S2C'):
                vv = [r['s0'] for k, r in fits.items() if k.startswith(sc)]
                if vv:
                    per_scene[sc] = round(float(np.median(vv)), 2)
            est = []
            if per_scene:
                est.append(float(np.mean(list(per_scene.values()))))
            if 'UMBRA' in fits:
                est.append(fits['UMBRA']['s0'])
            if not est:
                res.append(dict(edge=name, end=end, offset_from_end_m=off, fits=fits, s=None))
                continue
            sv = float(np.mean(est))
            spread = float(np.std(s2v)) if len(s2v) > 1 else None
            res.append(dict(edge=name, end=end, offset_from_end_m=off, s=round(sv, 2),
                            s2_per_scene=per_scene, s2_band_sd=round(spread, 2) if spread is not None else None,
                            umbra=fits.get('UMBRA', {}).get('s0'), implied_end_s=round(sv - off, 2), fits=fits))
        endN = [r['implied_end_s'] for r in res if r.get('s') is not None and r['end'] == 'N']
        endS = [r['implied_end_s'] for r in res if r.get('s') is not None and r['end'] == 'S']
        sN, sS = float(np.mean(endN)), float(np.mean(endS))
        meas_len = sS - sN
        mid = 0.5 * (sN + sS)
        Laip = AIP_LEN[ref]
        out['runways'][ref] = dict(
            osm_length_m=round(L, 2), osm_north_node=[la0, lo0], osm_south_node=[la1, lo1],
            edges=res,
            north_end_s_m=round(sN, 2), north_end_spread_m=round(float(np.ptp(endN)), 2) if len(endN) > 1 else None,
            south_end_s_m=round(sS, 2), south_end_spread_m=round(float(np.ptp(endS)), 2) if len(endS) > 1 else None,
            measured_length_m=round(meas_len, 2), aip_length_m=Laip, measured_minus_aip_m=round(meas_len - Laip, 2),
            centred_alternative=dict(rule='AIP length centred on the midpoint of the two measured ends',
                                     north_end_s_m=round(mid - Laip / 2, 2), south_end_s_m=round(mid + Laip / 2, 2)))
    # placement (inf): AIP "north ends aligned" + AIP lengths. Both north ends go to the mean of the two measured north
    # ends (on the mean runway axis); each south end = north end + AIP length; residual = placed - measured south end.
    R = out['runways']
    ae0 = np.array(F.ll_to_world(*R['18L/36R']['osm_north_node'])); aw0 = np.array(F.ll_to_world(*R['18R/36L']['osm_north_node']))
    be0 = np.array(F.ll_to_world(*R['18L/36R']['osm_south_node'])); bw0 = np.array(F.ll_to_world(*R['18R/36L']['osm_south_node']))
    ue0 = (be0 - ae0) / np.linalg.norm(be0 - ae0); uw0 = (bw0 - aw0) / np.linalg.norm(bw0 - aw0)
    um0 = (ue0 + uw0) / np.linalg.norm(ue0 + uw0)
    dw = float((aw0 - ae0) @ um0)                       # west OSM north node along the mean axis, rel. east node
    n_common = 0.5 * (R['18L/36R']['north_end_s_m'] + dw + R['18R/36L']['north_end_s_m'])
    for ref, off in (('18L/36R', 0.0), ('18R/36L', dw)):
        r = R[ref]
        pn = n_common - off
        r['placed_rule'] = ('north end: mean of the two measured north ends on the mean runway axis (AIP: "their north '
                            'ends aligned"); south end = north end + AIP length [inf]')
        r['placed_north_end_s_m'] = round(pn, 2)
        r['placed_south_end_s_m'] = round(pn + AIP_LEN[ref], 2)
        r['placed_minus_osm_north_m'] = round(-pn, 2)
        r['placed_minus_osm_south_m'] = round(pn + AIP_LEN[ref] - r['osm_length_m'], 2)
        r['placed_minus_measured_north_m'] = round(pn - r['north_end_s_m'], 2)
        r['placed_minus_measured_south_m'] = round(pn + AIP_LEN[ref] - r['south_end_s_m'], 2)

    def placed_point(ref, key):
        r = R[ref]
        a = np.array(F.ll_to_world(*r['osm_north_node'])); b = np.array(F.ll_to_world(*r['osm_south_node']))
        u = (b - a) / np.linalg.norm(b - a)
        return a + r[key] * u, u
    pe, ue = placed_point('18L/36R', 'placed_north_end_s_m')
    pw, uw = placed_point('18R/36L', 'placed_north_end_s_m')
    oe, _ = placed_point('18L/36R', 'north_end_s_m')
    ow, _ = placed_point('18R/36L', 'north_end_s_m')
    ae = np.array(F.ll_to_world(*R['18L/36R']['osm_north_node'])); aw = np.array(F.ll_to_world(*R['18R/36L']['osm_north_node']))
    um_ = (ue + uw) / np.linalg.norm(ue + uw)
    out['north_end_alignment'] = {
        'note': 'along-track difference (west minus east, + = west end further south) of the north ends, on the mean axis',
        'osm_nodes_m': round(float((aw - ae) @ um_), 2),
        'measured_m': round(float((ow - oe) @ um_), 2),
        'placed_m': round(float((pw - pe) @ um_), 2),
        'centreline_separation_m': round(float(abs((aw - ae) @ np.array([-um_[1], um_[0]]))), 2),
        'aip': 'AIP (mirror) AD 2.12 remarks: "The distance between RCL18R/36L and RCL18L/36R is 365m, and their north ends aligned."'}
    json.dump(out, open(OUT_JSON, 'w'), indent=1)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ('edges',)} for k, v in out['runways'].items()}, indent=1))
    print(json.dumps(out['north_end_alignment'], indent=1))
    plot(prof_store, out)


def plot(prof_store, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(4, 2, figsize=(16, 13))
    for k, ref in enumerate(('18L/36R', '18R/36L')):
        s, L, profs, pk = prof_store[ref]
        r = out['runways'][ref]
        for q, (lo, hi, endkey) in enumerate(((-200, 250, 'N'), (L - 250, L + 200, 'S'))):
            m = (s >= lo) & (s <= hi)
            ax = axs[k * 2 + q, 0]
            for key, col in (('B04', 'tab:red'), ('B08', 'k'), ('B02', 'tab:blue')):
                ax.plot(s[m], profs['S2B_' + key][m], color=col, lw=1.1, label=f'S2B 2026-10-14 {key}')
                ax.plot(s[m], profs['S2C_' + key][m], color=col, lw=0.8, ls='--', alpha=0.6, label=f'S2C 2026-02-21 {key}')
            ax2 = axs[k * 2 + q, 1]
            ax2.plot(s[m], profs['UMBRA'][m], color='0.2', lw=0.9, label='Umbra GEC 2024-06-02 (1.4 m overview), median 9 m')
            ax2.plot(s[m], pk[m], color='tab:purple', lw=0.6, alpha=0.7, label='Umbra p90 across +-24 m (light rows)')

            for a_ in (ax, ax2):
                a_.axvline(0 if q == 0 else L, color='tab:green', lw=1.5, label='OSM end node')
                pe = r['placed_north_end_s_m'] if q == 0 else r['placed_south_end_s_m']
                a_.axvline(pe, color='magenta', lw=1.5, ls='-', label=f'placed AIP end ({pe - (0 if q == 0 else L):+.1f} m)')
                for e in r['edges']:
                    if e.get('s') is not None and e['end'] == endkey:
                        a_.axvline(e['s'], color='orange', lw=0.9, ls=':')
                        a_.text(e['s'], a_.get_ylim()[1] if a_ is ax2 else 0.97, '', fontsize=6)
                a_.grid(alpha=0.3)
                a_.set_xlabel(f's (m) south of the OSM {ref.split("/")[0]} end node')
            ends = ', '.join(f"{e['edge']}: {e['s']:.1f}" for e in r['edges'] if e.get('s') is not None and e['end'] == endkey)
            ax.set_title(f'{ref} {"north" if q == 0 else "south"} end, Sentinel-2 (median across +-10 m)\nedges (orange): {ends}', fontsize=9)
            ax2.set_title(f'{ref} {"north" if q == 0 else "south"} end, Umbra SAR amplitude (median across +-15 m)', fontsize=9)
            if k == 0 and q == 0:
                ax.legend(fontsize=6, ncol=2); ax2.legend(fontsize=6)
    fig.suptitle('Runway ends along the OSM centrelines: Sentinel-2 L2A (Contains modified Copernicus Sentinel data 2026) '
                 'and Umbra SAR Open Data (CC BY 4.0, Umbra Lab Inc)', fontsize=10)
    plt.tight_layout(rect=(0, 0, 1, 0.97))
    plt.savefig(OUT_PNG, dpi=80)


if __name__ == '__main__':
    main()
