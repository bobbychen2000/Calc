#!/usr/bin/env python3
"""How far behind real time must the display run, and how large is the error? (traffic_audit.md section 5.7)

For every aircraft and every wall-clock second T of the recording, estimate the position the display would show for
td = T - D using ONLY the reports that had reached the app by T, and compare it with the truth at td (the recorded
reports interpolated at td, bracketed by reports <= 2.5 s apart). Also report the distance to the truth at T itself
(how far the picture lags reality) -- that is what "real time" costs.

Availability of a report (INFERRED from the recording): the first provider request whose snapshot contained it,
+ 0.35 s round trip (docs/research/realtime_feeds.md 3.2), + nothing for the relay -> browser hop.
Feeds:  stream = every merged report as soon as it is available (relay /api/stream, ~1 Hz)
        poll5  = only what the relay held at the app's last 5 s poll (app.js today: Feed intervalMs 5000)
Estimator (a simplified version of the proposed client, traffic_audit.md 6.6):
        td inside the available reports -> linear interpolation between the bracketing reports (Hermite adds < 1 m)
        td after the newest report      -> dead reckoning from it: groundspeed along the track (airborne) or along
                                           the position chord of the last reports (ground; ADS-B 'track' is not
                                           trusted on the surface, section 3.4), constant turn rate from the last
                                           two directions (|w| <= 3 deg/s air, 12 deg/s ground), horizon capped 15 s
States: air_app = airborne within 10 NM of the ARP below 5000 ft; gnd_mov = ground, gs >= 3 kt, at SFO.
Usage: python3 tools/live/replay_latency.py [--delays 0,1,1.5,2,3,5,7.5]
"""
import argparse, json, math, os, sys
from collections import defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import KT, NM, OUT, snapshots, build_reports, is_vehicle, ll2w
from replay_events import in_airport

LAT = 0.35


def availability():
    """{(hex, round(pt,1)): earliest arrival} over both providers"""
    av = {}
    for prov in ('adsbfi', 'adsblol'):
        for req, now, acs in snapshots(prov):
            for a in acs:
                if a.get('seen_pos') is None: continue
                k = (str(a['hex']).lower(), round(now - a['seen_pos'], 1))
                t = req + LAT
                if k not in av or t < av[k]: av[k] = t
    return av


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--delays', default='0,0.5,1,1.5,2,3,5,7.5'); o = ap.parse_args()
    delays = [float(d) for d in o.delays.split(',')]
    tracks, _ = build_reports(); av = availability()
    res = defaultdict(list)
    for hx, L in tracks.items():
        if sum(is_vehicle(r) for r in L) > len(L) / 2 or len(L) < 20: continue
        t = np.array([r['pt'] for r in L]); x = np.array([r['x'] for r in L]); z = np.array([r['z'] for r in L])
        g = np.array([r['ground'] for r in L]); gs = np.array([r['gs'] if isinstance(r.get('gs'), (int, float)) else np.nan for r in L])
        trk = np.array([r['track'] if isinstance(r.get('track'), (int, float)) else np.nan for r in L])
        alt = np.array([r['alt_baro'] if isinstance(r.get('alt_baro'), (int, float)) else np.nan for r in L])
        a = np.array([av.get((hx, round(r['pt'], 1)), r['req'] + LAT) for r in L])
        a = np.maximum(a, t)   # cannot arrive before it happened
        order = np.argsort(a); a_sorted = a[order]
        # poll5: the relay holds ONE merged record per hex; each 5 s poll delivers the newest report available then
        pollidx = {}
        run_max = np.maximum.accumulate(order)              # newest (max index) among the first n arrivals
        for P in np.arange(math.floor(t[0] / 5.0) * 5.0, t[-1] + 5, 5.0):
            n = int(np.searchsorted(a_sorted, P, side='right'))
            if n: pollidx[P] = int(run_max[n - 1])
        for T in np.arange(math.ceil(t[0]) + 10, t[-1], 1.0):
            i = int(np.searchsorted(t, T))
            if i == 0 or i >= len(t): continue
            st = 'air_app' if not g[i] and np.hypot(x[i], z[i]) < 10 * NM and np.isfinite(alt[i]) and alt[i] < 5000 else \
                 ('gnd_mov' if g[i] and np.isfinite(gs[i]) and gs[i] >= 3 and in_airport(x[i], z[i]) else None)
            if st is None: continue
            for feed in ('stream', 'poll5'):
                if feed == 'stream':
                    navail = int(np.searchsorted(a_sorted, T, side='right'))
                    if navail < 3: continue
                    idx = np.sort(order[:navail])          # available reports, in time order
                else:
                    Ps = [P for P in pollidx if P <= T]
                    if len(Ps) < 3: continue
                    idx = np.array(sorted({pollidx[P] for P in Ps}))
                for D in delays:
                    td = T - D
                    j = int(np.searchsorted(t, td))    # truth at td
                    if j == 0 or j >= len(t) or t[j] - t[j - 1] > 2.5: continue
                    u = (td - t[j - 1]) / (t[j] - t[j - 1]); tx = x[j - 1] + u * (x[j] - x[j - 1]); tz = z[j - 1] + u * (z[j] - z[j - 1])
                    k = int(np.searchsorted(t[idx], td))
                    if 0 < k < len(idx):
                        p, q = idx[k - 1], idx[k]; uu = (td - t[p]) / max(1e-6, t[q] - t[p])
                        ex, ez = x[p] + uu * (x[q] - x[p]), z[p] + uu * (z[q] - z[p]); mode = 'interp'
                    elif k >= len(idx):
                        p = idx[-1]; h = min(15.0, td - t[p])
                        # direction: track airborne; chord of the last reports >= 5 m apart on the ground
                        th = None
                        if not g[p] and np.isfinite(trk[p]): th = math.radians(trk[p])
                        else:
                            for qq in idx[::-1][1:8]:
                                if math.hypot(x[p] - x[qq], z[p] - z[qq]) >= 5: th = math.atan2(x[p] - x[qq], -(z[p] - z[qq])); break
                        v = (gs[p] if np.isfinite(gs[p]) else 0) * KT
                        w = 0.0
                        if len(idx) >= 2:
                            p2 = idx[-2]
                            if not g[p] and np.isfinite(trk[p]) and np.isfinite(trk[p2]) and t[p] > t[p2]:
                                w = ((trk[p] - trk[p2] + 180) % 360 - 180) / (t[p] - t[p2])
                        w = math.radians(max(-3, min(3, w))) if not g[p] else 0.0
                        if th is None: ex, ez = x[p], z[p]
                        elif abs(w) > 1e-4:
                            th1 = th + w * h; ex = x[p] + v / w * (math.cos(th) - math.cos(th1)); ez = z[p] - v / w * (math.sin(th1) - math.sin(th))
                        else:
                            ex = x[p] + math.sin(th) * v * h; ez = z[p] - math.cos(th) * v * h
                        mode = 'dr'
                    else:
                        continue
                    jr = int(np.searchsorted(t, T))
                    lag = None
                    if 0 < jr < len(t) and t[jr] - t[jr - 1] <= 2.5:
                        ur = (T - t[jr - 1]) / (t[jr] - t[jr - 1]); lag = math.hypot(ex - (x[jr - 1] + ur * (x[jr] - x[jr - 1])), ez - (z[jr - 1] + ur * (z[jr] - z[jr - 1])))
                    res[(st, feed, D)].append((math.hypot(ex - tx, ez - tz), lag if lag is not None else np.nan, mode == 'dr'))
    out = {}
    print('state    feed   delay  n     err p50/p90/p99 (m)       lag-behind-reality p50/p90 (m)   extrapolated')
    for k in sorted(res):
        v = np.array(res[k]); e = v[:, 0]; l = v[:, 1][np.isfinite(v[:, 1])]
        row = dict(n=len(v), err_p50=round(float(np.percentile(e, 50)), 1), err_p90=round(float(np.percentile(e, 90)), 1), err_p99=round(float(np.percentile(e, 99)), 1),
                   lag_p50=round(float(np.percentile(l, 50)), 1) if len(l) else None, lag_p90=round(float(np.percentile(l, 90)), 1) if len(l) else None, dr_frac=round(float(v[:, 2].mean()), 3))
        out['%s|%s|%g' % k] = row
        print(f"{k[0]:8s} {k[1]:6s} {k[2]:4.1f}  {row['n']:5d}  {row['err_p50']:6.1f} {row['err_p90']:7.1f} {row['err_p99']:7.1f}        {row['lag_p50']!s:>7} {row['lag_p90']!s:>7}          {row['dr_frac']:.2f}")
    json.dump(out, open(os.path.join(OUT, 'latency.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
