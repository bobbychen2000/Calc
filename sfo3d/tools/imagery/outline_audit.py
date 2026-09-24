"""SFO Museum building outlines (data/sfo_airport.json) vs NAIP (task (d)).

For every outline edge segment >= 15 m (terminal complex, terminals, boarding areas, garages/hotel/hangar/ATC),
NAIP is sampled on a segment-aligned strip (0.2 m across, +-14 m along the outward normal, 1 m along the segment,
10 % trimmed at each end); the across-profile of the gradient magnitude, averaged along the segment, gives the
position of the strongest parallel edge -> signed normal offset o (m, + = NAIP edge outside the outline).
Per building a least-squares translation d with n.d = o (weighted by edge strength, 2-sigma trimmed) summarises it;
the remaining scatter says how much is shape (not just position) disagreement.
Caveat (important): NAIP is an orthophoto on a bare-earth DEM ("2018 or newer HxIP DEM" per the NAIP metadata),
not a true orthophoto, so ROOF edges lean away from the image nadir by h * r / H (H = 4470 m AGL per the metadata,
r = distance from nadir, up to ~3 km across the 6 km frame) - several metres for 15-30 m roofs.  Running the same
audit on NAIP 2022 and 2024 (different flight lines) shows how much of the offset is lean.
Writes refs/cache/naip/outline_audit_<year>.json and an overlay image.
usage: python3 tools/imagery/outline_audit.py [--year 2024]
"""
import argparse, json, math, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def features():
    D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    out = [('Terminal complex', 'terminalComplex', D['terminalComplex'])]
    for k in ('terminals', 'boardingAreas'):
        for f in D[k]: out.append((f['name'], k, f['polys']))
    for f in D['structures']:
        if f['kind'] in ('garage', 'building', 'hangar', 'hotel', 'atc'): out.append((f['name'], f['kind'], f['polys']))
    return out


def seg_offset(S, a, b, half=14.0):
    v = b - a; L = np.linalg.norm(v); v = v / L; n = np.array([v[1], -v[0]])   # candidate normal (sign fixed later)
    s = np.arange(0.1 * L, 0.9 * L, 1.0); t = np.arange(-half, half, 0.2)
    SS, TT = np.meshgrid(s, t, indexing='ij')
    X = a[0] + SS * v[0] + TT * n[0]; Z = a[1] + SS * v[1] + TT * n[1]
    G = S(X, Z)
    if (G == 0).mean() > 0.02: return None
    G = cv2.GaussianBlur(G, (0, 0), 1.0)
    gt = np.abs(np.gradient(G, axis=1)) / 0.2                       # across-edge derivative (per m)
    prof = np.median(gt, axis=0)                                    # median along the segment: only edges parallel
    i = int(np.argmax(prof)); pk = float(prof[i])
    if 0 < i < len(t) - 1:
        a_, b_, c_ = prof[i - 1], prof[i], prof[i + 1]; den = a_ - 2 * b_ + c_
        di = 0.5 * (a_ - c_) / den if den < 0 else 0.0
    else: di = 0.0
    snd = np.max(prof[np.abs(t - t[i]) > 3.0]) if (np.abs(t - t[i]) > 3.0).any() else 0.0
    return dict(o=float(t[i] + di * 0.2), strength=pk, ratio=float(pk / max(snd, 1e-6)), n=n, L=float(L))


def ring_area(r):
    x, z = r[:, 0], r[:, 1]; return 0.5 * np.sum(x * np.roll(z, -1) - np.roll(x, -1) * z)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--year', default='2024'); ap.add_argument('--minlen', type=float, default=15.0)
    a = ap.parse_args()
    S = NaipSampler(a.year)
    res = {}
    allrows = []
    for name, cat, polys in features():
        rows = []
        for poly in polys:
            for k, ring in enumerate(poly):
                r = np.array(ring, float)
                # outward normal: rings are CCW in (x, -z) for outers (ringConvention), CW for holes
                sgn = 1.0 if ring_area(r * [1, -1]) > 0 else -1.0
                for i in range(len(r)):
                    p, q = r[i], r[(i + 1) % len(r)]
                    if np.linalg.norm(q - p) < a.minlen: continue
                    o = seg_offset(S, p, q)
                    if o is None: continue
                    v = (q - p) / np.linalg.norm(q - p)
                    out_n = sgn * np.array([-v[1], v[0]]) * np.array([1, 1])
                    # express offset along the outward normal
                    # (x,-z) CCW ring: outward normal in (x,-z) is (vy', -vx') ... convert via a test point
                    mid = (p + q) / 2
                    o_n = o['n']
                    if np.dot(o_n, out_n) < 0: o_n = -o_n; o['o'] = -o['o']
                    rows.append(dict(a=p.tolist(), b=q.tolist(), L=o['L'], off=o['o'], strength=o['strength'], ratio=o['ratio'], n=o_n.tolist(), hole=bool(k > 0)))
        good = [r_ for r_ in rows if r_['ratio'] > 1.3 and r_['strength'] > 4]
        entry = dict(category=cat, n_segments=len(rows), n_good=len(good))
        if len(good) >= 3:
            N = np.array([g['n'] for g in good]); o = np.array([g['off'] for g in good]); w = np.array([g['L'] for g in good])
            keep = np.ones(len(o), bool)
            for _ in range(4):
                sw = np.sqrt(w[keep])
                d, *_ = np.linalg.lstsq(N[keep] * sw[:, None], o[keep] * sw, rcond=None)
                e = o - N @ d
                sig = max(0.5, 1.4826 * np.median(np.abs(e[keep])))
                keep = np.abs(e) < 2.5 * sig
            entry.update(translation=d.tolist(), translation_m=float(np.hypot(*d)), resid_rms=float(np.sqrt(np.mean(e[keep] ** 2))),
                         median_abs_offset=float(np.median(np.abs(o))), p90_abs_offset=float(np.percentile(np.abs(o), 90)),
                         mean_offset_outward=float(np.average(o, weights=w)), n_used=int(keep.sum()),
                         cond=float(np.linalg.cond(N[keep])) if keep.sum() >= 2 else None)
            print(f"{name:38s} segs {len(rows):3d} good {len(good):3d}: translation ({d[0]:+.2f}, {d[1]:+.2f}) m = {np.hypot(*d):.2f}; "
                  f"|normal offset| median {entry['median_abs_offset']:.2f} p90 {entry['p90_abs_offset']:.2f}; mean outward {entry['mean_offset_outward']:+.2f}; "
                  f"resid rms {entry['resid_rms']:.2f}")
        else:
            print(f'{name:38s} segs {len(rows):3d} good {len(good):3d}: too few')
        # robust, interpretable summary in the airport grid (most facades follow it): length-weighted median offset of
        # the edges whose outward normal is
        # within 25 deg of +s (ESE 117.83), -s, +t (NNE 27.83) or -t.  Pure translation d gives off(+s) = d_s and
        # off(-s) = -d_s; a size difference (e.g. roof overhang, edge picked on a parapet/shadow) gives equal signs.
        hs, ht = math.radians(117.83), math.radians(27.83)
        us = np.array([math.sin(hs), -math.cos(hs)]); ut = np.array([math.sin(ht), -math.cos(ht)])
        cls = {}
        for key, u in (('+s', us), ('-s', -us), ('+t', ut), ('-t', -ut)):
            sel = [g for g in good if np.dot(g['n'], u) > math.cos(math.radians(25))]
            if sel:
                o_ = np.array([g['off'] for g in sel]); w_ = np.array([g['L'] for g in sel])
                srt = np.argsort(o_); cw = np.cumsum(w_[srt]) / w_.sum()
                wmed = float(o_[srt][np.searchsorted(cw, 0.5)])                     # length-weighted median
                cls[key] = dict(n=len(sel), median=wmed, plain_median=float(np.median(o_)), wmean=float(np.average(o_, weights=w_)), len_m=float(w_.sum()))
        grid = dict(classes=cls)
        for ax in ('s', 't'):
            if f'+{ax}' in cls and f'-{ax}' in cls:
                grid[f'shift_{ax}'] = (cls[f'+{ax}']['median'] - cls[f'-{ax}']['median']) / 2
                grid[f'grow_{ax}'] = (cls[f'+{ax}']['median'] + cls[f'-{ax}']['median']) / 2
        if 'shift_s' in grid and 'shift_t' in grid:
            d2 = grid['shift_s'] * us + grid['shift_t'] * ut
            grid['shift_xz'] = d2.tolist()
        entry['grid'] = grid
        if grid.get('shift_s') is not None or grid.get('shift_t') is not None:
            f_ = lambda k: 'n/a' if grid.get(k) is None else f"{grid[k]:+.2f}"
            print(f"{'':38s} grid: shift along s (ESE) {f_('shift_s')} m, along t (NNE) {f_('shift_t')} m; "
                  f"growth s {f_('grow_s')}, t {f_('grow_t')}  " + ' '.join(f"{k}:{v['median']:+.1f}({v['n']})" for k, v in cls.items()))
        entry['segments'] = rows
        res[name] = entry
        allrows += [dict(name=name, **g) for g in good]
    o = np.array([g['off'] for g in allrows])
    summ = dict(n=len(o), median_abs=float(np.median(np.abs(o))), p90_abs=float(np.percentile(np.abs(o), 90)),
                within_1m=float((np.abs(o) < 1).mean()), within_2m=float((np.abs(o) < 2).mean()), within_5m=float((np.abs(o) < 5).mean()))
    print('all good segments:', summ)
    json.dump(dict(year=a.year, summary=summ, buildings=res), open(os.path.join(CACHE, f'outline_audit_{a.year}.json'), 'w'), indent=1)
    # overlay (terminal area) for visual QA
    x0, z0, x1, z1, r = -1650.0, -350.0, -400.0, 1000.0, 0.5
    X, Z = np.meshgrid(np.arange(x0, x1, r) + r / 2, np.arange(z0, z1, r) + r / 2)
    img = np.ascontiguousarray(np.transpose(np.stack([S(X, Z, gray=True)] * 3), (1, 2, 0)).clip(0, 255).astype(np.uint8))
    for name, cat, polys in features():
        for poly in polys:
            for ring in poly:
                pts = np.round((np.array(ring) - [x0, z0]) / r).astype(np.int32)
                cv2.polylines(img, [pts], True, (0, 0, 255), 1)
    for g in allrows:
        m = (np.array(g['a']) + np.array(g['b'])) / 2; e = m + np.array(g['n']) * g['off']
        cv2.line(img, tuple(np.round((m - [x0, z0]) / r).astype(int)), tuple(np.round((e - [x0, z0]) / r).astype(int)), (0, 255, 255), 1)
    cv2.imwrite(os.path.join(CACHE, f'outline_audit_{a.year}.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == '__main__':
    main()
