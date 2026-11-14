"""Re-fit OSM taxiway centrelines to the Sentinel-2 pavement where it can be measured (pinned OSM extract).

usage: python3 -I sha3d/tools/airport/twy_refit.py SHA3D_DIR OUT_JSON OUT_PNG

Method (as docs/phase0/geo.md s.4, run on the pinned extract and on both scenes):
* every aeroway=taxiway way is split into straight runs (vertices within 1 m of the chord, run >= 100 m);
* per run and scene, cross profiles of B04 and B08 every 2.5 m along the run, 0.25 m apart, +-(width/2 + 24 m),
  sampled in the S2 registration (OSM position minus the scene's common OSM-S2 offset, geo.md), so what is measured
  is the run's offset relative to the common registration - the OSM frame (OD0) stays as it is;
* median profile, mirror-symmetry centre c (SSD of m(c+t) vs m(c-t), parabolic refinement), bootstrap SD over
  stations (30 draws); a band is usable when the profile is symmetric (q < 0.08), the centre is not at the search
  limit, SD < 2 m and pavement contrast > 150 DN; bands must agree within 3 m;
* pavement width: full width at half depth of the median NDVI profile (grass high, pavement low), reported only
  when both sides cross the half level (blurred by the 10 m pixels: an estimate, +-3 m);
* a scene's centre is used only when its NDVI profile reaches vegetation on both sides (pavement bounded by grass:
  next to an apron or a wide paved junction the symmetry centre is pulled into the paved expanse - seen at D);
* Umbra (1.4 m overview): the same symmetry centre on the amplitude profile, usable when q < 0.10, SD < 1.5 m and the
  grass on EACH side is > 2x brighter than the pavement; its own global offset (Umbra minus OSM, Huber least squares
  over the usable runs) is removed;
* a run is MEASURED when at least 2 of the 3 sources (S2B, S2C, Umbra) agree within 2.0 m; c = their mean;
* a run is RE-FITTED when measured and |c| >= 3.5 m (about 3x the median source spread): its vertices move by c
  along the run normal. A vertex shared by
  several re-fitted runs takes the mean move; vertices on a runway centreline are never moved. Connectivity is kept
  because every way that shares a vertex (same coordinates) gets the same move (applied by build_airport.py).
Output: per run the scene centres, widths, flags, and the vertex moves (keyed by the vertex lon/lat rounded to 1e-7).
"""
import json
import math
from collections import Counter
import os
import sys

import numpy as np
from scipy.ndimage import median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
import imgsample as IS  # noqa: E402

MIN_RUN = 100.0
TOL = 1.0
AGREE = 2.0
REFIT = 3.5
W_DEFAULT = 23.0


def vkey(lon, lat):
    return f'{lon:.7f},{lat:.7f}'


def straight_runs(P, tol=TOL, min_len=MIN_RUN):
    runs, i = [], 0
    while i < len(P) - 1:
        j = i + 1
        while j + 1 < len(P):
            p0, p1 = P[i], P[j + 1]
            L = np.linalg.norm(p1 - p0)
            u = (p1 - p0) / L
            nn = np.array([-u[1], u[0]])
            dev = max(abs((P[k] - p0) @ nn) for k in range(i, j + 2))
            if dev > tol:
                break
            j += 1
        L = float(np.linalg.norm(P[j] - P[i]))
        if L >= min_len:
            runs.append((i, j, L))
        i = j
    return runs


def sym_centre(mp, tt, cmax):
    dt = tt[1] - tt[0]
    taus = np.arange(1.0, tt[-1] - cmax, dt)
    cs = np.arange(-cmax, cmax + 1e-9, 0.25)
    ssd = np.array([np.mean((np.interp(c + taus, tt, mp) - np.interp(c - taus, tt, mp)) ** 2) for c in cs])
    k = int(np.argmin(ssd))
    c = cs[k]
    if 0 < k < len(cs) - 1:
        y0, y1, y2 = ssd[k - 1], ssd[k], ssd[k + 1]
        den = y0 - 2 * y1 + y2
        if den > 0:
            c = cs[k] + 0.5 * (y0 - y2) / den * 0.25
    return float(c), float(ssd[k] / max(np.var(mp), 1e-9)), (k == 0 or k == len(cs) - 1)


def fwhm(tt, prof):
    """width where the profile is below half-way between its centre level and its outer level (pavement = low)."""
    inner = np.median(prof[np.abs(tt) < 4]); outer = np.median(prof[np.abs(tt) > tt[-1] - 6])
    if outer - inner < 0.08:
        return None
    half = 0.5 * (inner + outer)
    below = prof < half
    c = len(tt) // 2
    if not below[c]:
        return None
    l = c
    while l > 0 and below[l]:
        l -= 1
    r = c
    while r < len(tt) - 1 and below[r]:
        r += 1
    if l == 0 or r == len(tt) - 1:
        return None

    def cross(i0, i1):
        y0, y1 = prof[i0] - half, prof[i1] - half
        return tt[i0] + (tt[i1] - tt[i0]) * (y0 / (y0 - y1)) if y0 != y1 else tt[i0]
    return float(cross(r - 1, r) - cross(l, l + 1))


def main(root, out_json, out_png):
    fc = json.load(open(os.path.join(root, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
    scenes = [IS.S2(os.path.join(root, 'refs/cache/s2', n)) for n in IS.S2_OFFSETS]
    um = IS.Umbra(os.path.join(root, 'refs/cache/imagery/umbra_opendata/umbra_gec_ovr4.tif'))
    rng = np.random.default_rng(7)
    runway_keys = set()
    for f in fc['features']:
        if f['properties']['tags'].get('aeroway') == 'runway' and f['geometry']['type'] == 'LineString':
            runway_keys.update(vkey(*c) for c in f['geometry']['coordinates'])
    runs_out = []
    for f in fc['features']:
        t = f['properties']['tags']
        if t.get('aeroway') != 'taxiway' or f['properties']['@type'] != 'way' or f['geometry']['type'] != 'LineString':
            continue
        coords = f['geometry']['coordinates']
        lon = np.array([c[0] for c in coords]); lat = np.array([c[1] for c in coords])
        E0, N0 = scenes[0].tr.transform(lon, lat)          # OSM registration, UTM 51N
        P = np.c_[E0, N0]
        for (i, j, L) in straight_runs(P):
            p0 = P[i]; u = (P[j] - p0) / L
            n = np.array([-u[1], u[0]])
            if n[0] < 0 or (abs(n[0]) < 1e-9 and n[1] < 0):
                n = -n
            cmax = 14.0
            H = W_DEFAULT / 2 + 24.0 + cmax
            tt = np.arange(-H, H + 1e-9, 0.25)
            st = np.arange(12.0, L - 12.0, 2.5)
            per = {}
            for sc in scenes:
                q0 = p0 - np.array(sc.off)                  # into the S2 registration
                pts_E = (q0[0] + st[:, None] * u[0] + tt[None, :] * n[0])
                pts_N = (q0[1] + st[:, None] * u[1] + tt[None, :] * n[1])
                bands = {}
                for band in ('B04', 'B08'):
                    prof = sc.sample_en(band, pts_E, pts_N)
                    mp = np.median(prof, axis=0)
                    c, q, edge = sym_centre(mp, tt, cmax)
                    boots = [sym_centre(np.median(prof[rng.integers(0, len(st), len(st))], axis=0), tt, cmax)[0]
                             for _ in range(30)]
                    contrast = float(mp[np.abs(tt) < 5].mean() - mp[np.abs(tt) > H - cmax - 4].mean())
                    ok = (not edge) and q < 0.08 and np.std(boots) < 2.0 and abs(contrast) > 150
                    bands[band] = dict(c=round(c, 2), q=round(q, 3), sd=round(float(np.std(boots)), 2),
                                       contrast=round(contrast), ok=bool(ok))
                nd = np.median(sc.ndvi_en(pts_E, pts_N), axis=0)
                oks = [b for b in bands.values() if b['ok']]
                cval = None
                if oks and not (len(oks) == 2 and abs(oks[0]['c'] - oks[1]['c']) > 3.0):
                    cval = round(float(np.mean([b['c'] for b in oks])), 2)
                w = fwhm(tt, nd)
                per[sc.name[:3]] = dict(c=cval, bands=bands, width_ndvi_fwhm=round(w, 1) if w else None)
            # Umbra SAR (1.4 m overview): amplitude profile, same geometry, in the OSM registration (its own global
            # offset is removed after all runs are measured)
            lonp, latp = scenes[0].inv.transform(p0[0] + st[:, None] * u[0] + tt[None, :] * n[0],
                                                 p0[1] + st[:, None] * u[1] + tt[None, :] * n[1])
            ua = um.sample(lonp, latp)
            ump = median_filter(np.nanmedian(ua, axis=0), size=5, mode='nearest')
            if np.isfinite(ump).all():
                cu, qu, eu = sym_centre(ump, tt, cmax)
                bu = [sym_centre(median_filter(np.nanmedian(ua[rng.integers(0, len(st), len(st))], axis=0), size=5,
                                               mode='nearest'), tt, cmax)[0] for _ in range(30)]
                inner = max(np.median(ump[np.abs(tt) < 5]), 1e-6)
                ctr = float(min(np.median(ump[tt < -(H - cmax - 4)]), np.median(ump[tt > H - cmax - 4])) / inner)
                per['UMB_raw'] = dict(c=round(cu, 2), q=round(qu, 3), sd=round(float(np.std(bu)), 2),
                                      grass_over_pavement=round(ctr, 2),
                                      ok=bool((not eu) and qu < 0.10 and np.std(bu) < 1.5 and ctr > 2.0))
            widths = [v['width_ndvi_fwhm'] for k_, v in per.items() if k_ != 'UMB_raw' and v['width_ndvi_fwhm']]
            runs_out.append(dict(way=f['properties']['@id'], version=f['properties']['@version'], ref=t.get('ref'),
                                 v0=i, v1=j, length_m=round(L, 1),
                                 bearing_deg=round(math.degrees(math.atan2(u[0], u[1])) % 360, 1),
                                 normal_EN=[round(float(n[0]), 4), round(float(n[1]), 4)],
                                 scenes=per,
                                 width_s2_m=round(float(np.mean(widths)), 1) if len(widths) == 2 else None,
                                 keys=[vkey(lon[k], lat[k]) for k in range(i, j + 1)]))
    # Umbra global offset (Umbra minus OSM, E/N) by Huber least squares over the usable runs, then residuals
    U = [r for r in runs_out if r['scenes'].get('UMB_raw', {}).get('ok')]
    A = np.array([r['normal_EN'] for r in U]); y = np.array([r['scenes']['UMB_raw']['c'] for r in U])
    wts = np.ones(len(U))
    for _ in range(30):
        g, *_ = np.linalg.lstsq(A * wts[:, None], y * wts, rcond=None)
        res = y - A @ g
        k = 1.5 * (np.median(abs(res)) * 1.4826 + 1e-6)
        wts = np.where(abs(res) <= k, 1.0, np.sqrt(k / abs(res)))
    umbra_global = dict(dE=round(float(g[0]), 2), dN=round(float(g[1]), 2), n_runs=len(U),
                        rms_resid=round(float(np.sqrt(np.mean(res ** 2))), 2))
    for r in runs_out:
        ur = r['scenes'].get('UMB_raw')
        # a scene counts only if its NDVI profile reaches vegetation on BOTH sides (width_ndvi_fwhm defined): next to
        # an apron or a paved junction the symmetry centre is pulled into the paved expanse (seen at taxiway D)
        cands = {k_: v['c'] for k_, v in r['scenes'].items() if k_ in ('S2B', 'S2C') and v['c'] is not None
                 and v['width_ndvi_fwhm'] is not None}
        r['s2_bounded_by_grass'] = {k_: r['scenes'][k_]['width_ndvi_fwhm'] is not None for k_ in ('S2B', 'S2C')}
        if ur and ur['ok']:
            r['scenes']['UMB'] = round(ur['c'] - (g[0] * r['normal_EN'][0] + g[1] * r['normal_EN'][1]), 2)
            cands['UMB'] = r['scenes']['UMB']
        best = []
        names = list(cands)
        for m_ in range(len(names), 1, -1):          # largest agreeing subset (max - min <= AGREE), >= 2 sources
            from itertools import combinations
            for sub in combinations(names, m_):
                v = [cands[x] for x in sub]
                if max(v) - min(v) <= AGREE and (not best or len(sub) > len(best) or
                                                 (len(sub) == len(best) and np.ptp(v) < np.ptp([cands[x] for x in best]))):
                    best = list(sub)
            if best:
                break
        r['sources_used'] = best
        r['measured'] = len(best) >= 2
        r['offset_m'] = round(float(np.mean([cands[x] for x in best])), 2) if r['measured'] else None
        r['source_spread_m'] = round(float(np.ptp([cands[x] for x in best])), 2) if r['measured'] else None
        r['refit'] = bool(r['measured'] and abs(r['offset_m']) >= REFIT)
    # vertex moves
    moves = {}
    for r in runs_out:
        if not r['refit']:
            continue
        for k in r['keys']:
            if k in runway_keys:
                continue
            moves.setdefault(k, []).append((r['offset_m'] * r['normal_EN'][0], r['offset_m'] * r['normal_EN'][1], r['way']))
    vmoves = {}
    for k, lst in moves.items():
        dE = float(np.mean([a[0] for a in lst])); dN = float(np.mean([a[1] for a in lst]))
        lon, lat = map(float, k.split(','))
        E, N = scenes[0].tr.transform(lon, lat)
        lon2, lat2 = scenes[0].inv.transform(E + dE, N + dN)
        vmoves[k] = dict(to=[round(lon2, 7), round(lat2, 7)], dE=round(dE, 2), dN=round(dN, 2),
                         from_runs=sorted(set(a[2] for a in lst)))
    meas = [r for r in runs_out if r['measured']]
    off = np.array([r['offset_m'] for r in meas]) if meas else np.array([0.0])
    summary = dict(runs=len(runs_out), measured=len(meas), refit=sum(r['refit'] for r in runs_out),
                   vertices_moved=len(vmoves),
                   abs_offset_median_m=round(float(np.median(abs(off))), 2),
                   abs_offset_p90_m=round(float(np.percentile(abs(off), 90)), 2),
                   abs_offset_max_m=round(float(abs(off).max()), 2),
                   source_spread_median_m=round(float(np.median([r['source_spread_m'] for r in meas])), 2) if meas else None,
                   measured_by=dict(Counter('+'.join(r['sources_used']) for r in meas)),
                   umbra_global_offset_umbra_minus_osm=umbra_global,
                   width_s2_median_m=round(float(np.median([r['width_s2_m'] for r in runs_out if r['width_s2_m']])), 1),
                   thresholds=dict(min_run_m=MIN_RUN, agree_m=AGREE, refit_m=REFIT),
                   scene_offsets_osm_minus_s2=IS.S2_OFFSETS)
    out = dict(method=__doc__.split('\n\n')[1], summary=summary, runs=[{k: v for k, v in r.items() if k != 'keys'}
                                                                       for r in runs_out], vertex_moves=vmoves)
    json.dump(out, open(out_json, 'w'), indent=1)
    print(json.dumps(summary, indent=1))
    for r in sorted(meas, key=lambda r: -abs(r['offset_m']))[:25]:
        print(r['way'], r['ref'], r['length_m'], r['offset_m'], r['sources_used'], r['source_spread_m'], r['width_s2_m'], 'REFIT' if r['refit'] else '')
    plot(runs_out, out_png)


def plot(runs, out_png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    meas = [r for r in runs if r['measured']]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    def cv(r, k):
        v = r['scenes'].get(k)
        v = v['c'] if isinstance(v, dict) else v
        return np.nan if v is None else v
    a = np.array([[cv(r, 'S2B'), cv(r, 'S2C') if not np.isnan(cv(r, 'S2C')) else cv(r, 'UMB')] for r in meas])
    col = ['tab:red' if r['refit'] else 'tab:blue' for r in meas]
    ax[0].scatter(a[:, 0], a[:, 1], c=col, s=14)
    lim = max(4, np.nanmax(np.abs(a)) + 1)
    ax[0].plot([-lim, lim], [-lim, lim], 'k:', lw=0.8)
    for v in (-REFIT, REFIT):
        ax[0].axvline(v, color='0.7', lw=0.6); ax[0].axhline(v, color='0.7', lw=0.6)
    for r in meas:
        if r['refit']:
            ax[0].annotate(f"{r['ref'] or 'way ' + str(r['way'])}", (cv(r, 'S2B'), cv(r, 'S2C') if not np.isnan(cv(r, 'S2C')) else cv(r, 'UMB')),
                           fontsize=6, xytext=(3, 3), textcoords='offset points')
    ax[0].set_xlabel('S2B 2026-10-14: imaged pavement centre - OSM (m, along run normal)')
    ax[0].set_ylabel('S2C 2026-02-21 (or Umbra 2024-06-02 where S2C failed): same (m)')
    ax[0].set_title(f'{len(meas)} measured taxiway runs (>= {MIN_RUN:.0f} m), red = re-fitted (|c| >= {REFIT} m)', fontsize=9)
    ax[0].grid(alpha=0.3)
    w = [r['width_s2_m'] for r in runs if r['width_s2_m']]
    ax[1].hist(w, bins=np.arange(10, 70, 2), color='0.4')
    ax[1].set_xlabel('S2 pavement width, NDVI full width at half depth (m)')
    ax[1].set_title('taxiway pavement width on Sentinel-2 (both scenes, mean); blurred by 10 m pixels', fontsize=9)
    fig.suptitle('OSM taxiway centrelines vs Sentinel-2 L2A (Contains modified Copernicus Sentinel data 2026; '
                 'OSM (c) OpenStreetMap contributors)', fontsize=9)
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    plt.savefig(out_png, dpi=90)


if __name__ == '__main__':
    main(*sys.argv[1:4])
