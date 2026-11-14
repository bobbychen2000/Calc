"""Parked aircraft on the ZSSS stands in a Sentinel-2 L2A time stack (task A2): per stand and date, is an aircraft
parked on the lead-in, and which size template fits it. Copernicus Sentinel data 2023-2026 (free and open).

usage: python3 -I sha3d/tools/airport/stand_s2.py SHA3D_DIR OUT_JSON [OUT_PNG]

Method (all numbers are measured here; the templates are inferred sketches, tools/airport/acplan.py):
  1. Stack: refs/cache/s2_stack/<item>/{B02,B03,B04,SCL}.tif (tools/airport/s2_stack.py; 67 dates 2023-01..2026-10,
     tile cloud < 20 %). Brightness = mean of B02/B03/B04 DN / 10000. Cloud / shadow / snow pixels (SCL 3, 8, 9, 10, 11)
     and scenes with > 2 % such pixels inside the stand window are dropped.
  2. Registration: each date is aligned to S2B 2026-10-14 by FFT cross-correlation of gradient images (sub-pixel,
     whole 2.3 x 3.4 km window); that scene's offset to OSM is the phase-0 value OSM - S2 = (-3.09, -1.00) m
     (docs/phase0/geo.md s.4), applied to all.
  3. Per stand, a stand-aligned patch (2 m grid, u = metres ahead of the OSM stop node, v = to the right) is sampled for
     every date; background = per-pixel 15th percentile over the valid dates (the apron without aircraft; aircraft are
     brighter than the concrete); excess = brightness - background.
  4. Template fit: the planform templates (B, C38, C44, D, E, EL, F; nose tip at u = du), rasterised at 2 m and blurred
     (Gaussian sigma 4.5 m ~ the 10 m S2 pixel + resampling), are fitted to the excess (amplitude a >= 0, least squares)
     inside the stand's own domain, for du in [-12, +10] m and dv in [-5, +5] m. A date counts as an aircraft call
     when the best template explains R2 >= 0.75 of the (zero-mean) excess energy and a >= 0.035 (reflectance); the
     size call is the best template. Calls whose best du or dv sits on the search bound are discarded (counted).
     Domain (QA C1 M4 fix, 2026-11-14): a FIXED half-width |v| <= 36 m and u in [-85, +10], with neighbour masking:
     pixels nearer to a lateral neighbour's axis than to this stand's axis (beyond the mid-line, per side) are left
     out. Before, the domain was |v| <= half the spacing to the nearest neighbour on either side, which built the
     spacing into the wide / narrow result.
Outputs per stand: dates valid / occupied, size calls per date, the largest size called on >= 2 dates, median nose
offset du per size family, occupancy fraction (10:30-10:50 local overpasses).
"""
import json
import math
import os
import sys

import numpy as np
import rasterio
from pyproj import Transformer
from scipy.ndimage import gaussian_filter, map_coordinates, zoom

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
from acplan import TEMPLATES, TEMPLATE_CLASS, planform  # noqa: E402
from stand_geom import OsmStands, to_local, hdiff  # noqa: E402

REF_ID = 'S2B_51RUQ_20261014_0_L2A'
REF_OFF = (-3.09, -1.00)      # OSM - S2 (m east, north) for REF_ID, phase 0 geo.md s.4
RES = 2.0
U = np.arange(10, -85, -RES)        # metres ahead of the stop (rows)
V = np.arange(-36, 36.01, RES)      # metres right (cols)
DU = np.arange(-12, 10.1, 1.0); DV = np.arange(-5, 5.1, 1.0)     # QA C1 M4: widened from -8..+6 / +-3 m
V_DOMAIN = 36.0                                                   # fixed half-width of the fit domain (m)
SIGMA = 4.5
R2_MIN = 0.75; A_MIN = 0.035


def load_stack(root):
    st = json.load(open(os.path.join(root, 'refs/cache/s2_stack/stack.json')))
    out = []
    for it in st['items']:
        d = os.path.join(root, 'refs/cache/s2_stack', it['id'])
        try:
            b = [rasterio.open(os.path.join(d, n + '.tif')) for n in ('B02', 'B03', 'B04')]
            scl = rasterio.open(os.path.join(d, 'SCL.tif')).read(1)
        except Exception:  # noqa: BLE001
            continue
        img = np.mean([x.read(1).astype(float) for x in b], axis=0) / 10000.0
        sclu = np.kron(scl, np.ones((2, 2), dtype=scl.dtype))[:img.shape[0], :img.shape[1]]
        bad = np.isin(sclu, [3, 8, 9, 10, 11]) | (img <= 0)
        out.append(dict(id=it['id'], dt=it['datetime'], img=img, bad=bad, T=b[0].transform, crs=b[0].crs))
    return out


def xcorr_shift(a, b):
    """shift (drow, dcol) to apply to b to match a (sub-pixel, FFT cross-correlation of gradient magnitudes)"""
    def g(x):
        gy, gx = np.gradient(gaussian_filter(x, 1.0)); m = np.hypot(gx, gy); return (m - m.mean()) / (m.std() + 1e-9)
    A, B = g(a), g(b)
    C = np.real(np.fft.ifft2(np.fft.fft2(A) * np.conj(np.fft.fft2(B))))
    i, j = np.unravel_index(np.argmax(C), C.shape)
    def sub(c, k, n):
        y0, y1, y2 = c[(k - 1) % n], c[k], c[(k + 1) % n]
        den = y0 - 2 * y1 + y2
        return k + (0.5 * (y0 - y2) / den if den != 0 else 0.0)
    di = sub(C[:, j], i, C.shape[0]); dj = sub(C[i, :], j, C.shape[1])
    if di > C.shape[0] / 2: di -= C.shape[0]
    if dj > C.shape[1] / 2: dj -= C.shape[1]
    return di, dj


def templates():
    """rasterised, blurred templates on a padded (u, v) grid, nose tip at the grid origin u = 0"""
    from matplotlib.path import Path
    uu = np.arange(20, -110, -RES); vv = np.arange(-60, 60.01, RES)
    UU, VV = np.meshgrid(uu, vv, indexing='ij'); pts = np.c_[UU.ravel(), VV.ravel()]
    out = {}
    for name, L, span, w, sw in TEMPLATES:
        m = np.zeros(UU.size, bool)
        # supersample the edges a little: rasterise on a 4x finer grid then average
        for du in (-0.75, -0.25, 0.25, 0.75):
            for dv in (-0.75, -0.25, 0.25, 0.75):
                q = pts + [du, dv]
                for poly in planform(L, span, w, sw):
                    m |= Path(poly).contains_points(q)
        t = gaussian_filter(m.reshape(UU.shape).astype(float), SIGMA / RES)
        out[name] = t
    return out, uu, vv


def main(root, out_json, out_png=None):
    O = OsmStands(root)
    stands = O.stands()
    for i, s in enumerate(O.unref_dead_ends()):
        s['name'] = 'osm-way-%d' % s['way']; stands.append(s)
    scenes = load_stack(root)
    ref = [s for s in scenes if s['id'] == REF_ID][0]
    # window of the stand areas only for the cloud test
    for s in scenes:
        s['cloud_frac'] = float(s['bad'].mean())
    good = [s for s in scenes if s['cloud_frac'] <= 0.02]
    for s in good:
        if s is ref:
            s['shift_px'] = (0.0, 0.0)
        else:
            a = np.where(ref['bad'], np.nanmedian(ref['img']), ref['img']); b = np.where(s['bad'], np.nanmedian(s['img']), s['img'])
            s['shift_px'] = xcorr_shift(a, b)
    tr = Transformer.from_crs('EPSG:4326', ref['crs'], always_xy=True)
    TPL, tu, tv = templates()
    # lateral neighbours (for the neighbour mask) and the half-spacing (reported only)
    for s in stands:
        sp = 72.0; nb = []
        for t in stands:
            if t is s or abs(hdiff(s['hdg'], t['hdg'])) > 25:
                continue
            u, v = to_local(t['stop'], s['stop'], s['hdg'])
            if abs(u) < 30 and 12 < abs(v) < 110:
                sp = min(sp, abs(v)); nb.append(v)
        s['half_sp'] = min(36.0, sp / 2)
        s['nb_v'] = nb
    res = {}
    f_sh = lambda p: p  # noqa: E731
    for s in stands:
        f = F.hdg_vec(s['hdg']); r = (-f[1], f[0])
        UU, VV = np.meshgrid(U, V, indexing='ij')
        X = s['stop'][0] + UU * f[0] + VV * r[0]; Z = s['stop'][1] + UU * f[1] + VV * r[1]
        lat, lon = np.vectorize(F.world_to_ll)(X, Z)
        E0, N0 = tr.transform(lon, lat)
        E0 = E0 - REF_OFF[0]; N0 = N0 - REF_OFF[1]     # OSM registration -> REF scene registration
        stack, bads, ids = [], [], []
        for sc in good:
            T = sc['T']; di, dj = sc['shift_px']
            col = (E0 - T.c) / T.a - 0.5 - dj; row = (N0 - T.f) / T.e - 0.5 - di
            v = map_coordinates(sc['img'], [row, col], order=1, mode='nearest')
            bd = map_coordinates(sc['bad'].astype(float), [row, col], order=1, mode='nearest') > 0.01
            stack.append(v); bads.append(bd.any()); ids.append(sc['id'])
        stack = np.array(stack); ok = ~np.array(bads)
        if ok.sum() < 8:
            res[s['name']] = {'n_valid': int(ok.sum())}; continue
        bg = np.percentile(stack[ok], 15, axis=0)
        dom = (np.abs(VV) <= V_DOMAIN) & (UU <= 10) & (UU >= -85)
        for vt in s['nb_v']:                       # neighbour masking: beyond the mid-line towards each neighbour
            dom &= ~(np.abs(VV - vt) < np.abs(VV))
        # shifted, domain-masked templates for this stand: matrix (n_models, n_pix)
        models, Tm = [], []
        for name, t in TPL.items():
            for du in DU:
                for dv in DV:
                    ri = (tu[0] - (UU - du)) / RES; ci = ((VV - dv) - tv[0]) / RES
                    tt = map_coordinates(t, [ri, ci], order=1, mode='constant', cval=0.0)
                    tt = np.where(dom, tt, 0.0)
                    models.append((name, du, dv)); Tm.append(tt.ravel())
        Tm = np.array(Tm); dm = dom.ravel(); nd = float(dm.sum())
        # zero-mean over the domain (a constant offset b is fitted together with the amplitude a)
        Tc = np.where(dm[None, :], Tm - (Tm[:, dm].sum(1) / nd)[:, None], 0.0); tt2 = (Tc * Tc).sum(1)
        calls = []; n_bound = 0
        for k in np.where(ok)[0]:
            ex = (stack[k] - bg).ravel()
            ex = np.where(dm, ex - ex[dm].mean(), 0.0)
            Ee = float((ex * ex).sum())
            dot = Tc @ ex
            a_ = dot / np.maximum(tt2, 1e-12)
            r2 = np.where(a_ > 0, dot * dot / np.maximum(tt2 * Ee, 1e-12), 0.0)
            j = int(np.argmax(r2))
            best = (float(r2[j]), float(a_[j])) + models[j]
            if best[0] >= R2_MIN and best[1] >= A_MIN and (best[3] in (DU[0], DU[-1]) or best[4] in (DV[0], DV[-1])):
                n_bound += 1                       # best fit on the search bound: discarded (QA C1 M4)
            elif best[0] >= R2_MIN and best[1] >= A_MIN:
                calls.append({'scene': ids[k][:24], 'tpl': best[2], 'cls': TEMPLATE_CLASS[best[2]], 'r2': round(best[0], 3),
                              'a': round(best[1], 4), 'du': float(best[3]), 'dv': float(best[4])})
        n_ok = int(ok.sum())
        from collections import Counter
        cc = Counter(c['cls'] for c in calls)
        order = ['B', 'C', 'D', 'E', 'EL', 'F']
        max2 = None
        for c in order[::-1]:
            if sum(cc[x] for x in order[order.index(c):]) >= 2:
                max2 = c; break
        wide_n = sum(cc[x] for x in ('D', 'E', 'EL', 'F'))
        fam = {}
        for famname, members in (('narrow', ('B', 'C')), ('wide', ('D', 'E', 'EL', 'F'))):
            d_ = [c['du'] for c in calls if c['cls'] in members]
            fam[famname] = {'n': len(d_), 'du_median': (float(np.median(d_)) if d_ else None)}
        res[s['name']] = {'n_valid': n_ok, 'n_occupied': len(calls), 'occupancy': round(len(calls) / n_ok, 3),
                          'calls_by_class': dict(cc), 'wide_calls': wide_n, 'max_class_2plus': max2,
                          'nose_du': fam, 'calls': calls, 'calls_discarded_on_bound': n_bound,
                          'half_spacing_m': s['half_sp'], 'domain_px': int(dom.sum())}
        print(s['name'], n_ok, len(calls), dict(cc), max2, flush=True)
    meta = {'what': 'parked aircraft per stand in a Sentinel-2 L2A time stack (tools/airport/stand_s2.py)',
            'attribution': ('Contains modified Copernicus Sentinel data 2023-2026; (c) OpenStreetMap contributors '
                            '(ODbL 1.0)'),
            'licence': ('Sentinel-2: Copernicus Sentinel data legal notice (free reproduction / distribution with the notice); '
                        'measurements on OSM stands: ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)'),
            'scenes_total': len(scenes), 'scenes_used': len(good),
            'scenes': [{'id': s['id'], 'datetime': s['dt'], 'cloud_frac_window': round(s['cloud_frac'], 4),
                        'used': s in good, 'shift_px_row_col': [round(v, 2) for v in s.get('shift_px', (0, 0))] if s in good else None}
                       for s in scenes],
            'ref_scene': REF_ID, 'ref_offset_osm_minus_s2_m': REF_OFF,
            'params': {'res_m': RES, 'sigma_m': SIGMA, 'r2_min': R2_MIN, 'a_min': A_MIN, 'bg_percentile': 15,
                       'du_range': [float(DU[0]), float(DU[-1])], 'dv_range': [float(DV[0]), float(DV[-1])],
                       'domain': 'fixed |v| <= %g m, u in [-85, +10], lateral neighbours masked beyond the mid-line; '
                                 'calls on the du / dv search bound discarded' % V_DOMAIN},
            'calls_discarded_on_bound': int(sum(r.get('calls_discarded_on_bound', 0) for r in res.values())),
            'stands': res}
    json.dump(meta, open(out_json, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
