#!/usr/bin/env python3
"""Ground truth for the traffic audit: every arrival, departure, go-around, rollout exit, taxi route, stop, push-back
and parking position in the ~1 Hz ADS-B recording (tools/live/record.py -> refs/cache/rec/).

Input: merged, de-duplicated reports of both providers (replay_common.build_reports: position time = now - seen_pos).
Output: refs/cache/replay/events.json (gitignored, derived from the providers' data) and a text summary on stdout.

Definitions (all distances in the app's world frame, js/geo.js; runway ends js/geo.js RWY_ENDS = FAA/AirNav):
  along-track a  = distance past the LANDING threshold (displaced thresholds 28L/28R 300 ft, 1L 640 ft, 1R 560 ft)
  cross-track c  = signed distance from the runway centreline (+ = right of the direction of travel)
  runway         = the runway end whose true heading is within 20 deg of the track and whose centreline has the
                   smallest median |c| over the last 4 NM of final (arrivals) / the take-off roll (departures);
                   the runner-up (usually the parallel, 228.6 m away) is reported as a margin.
  threshold      = time the along-track distance crosses 0 (linear interpolation between reports)
  flag           = first report with alt_baro == "ground" (arrivals) / first airborne report (departures)
  touchdown (est)= breakpoint of a continuous two-segment linear fit of groundspeed vs time between the threshold
                   and the flag (+5 s): the onset of the strong deceleration (spoilers/brakes/reversers). OBSERVED
                   data, INFERRED event: a late bound by ~0-2 s (spoilers deploy at main-gear touchdown).
  liftoff (est)  = first of 3 consecutive airborne reports with vertical rate >= 192 ft/min (rates are 64 ft/min
                   quantised) -- INFERRED; cross-checked with alt_geom leaving its runway value.
  roll start     = last report with gs <= 5 kt on the runway before the take-off (or entering the runway, if the
                   take-off was rolling).
  exit           = first report after touchdown with |c| > 45 m (runway half-width 30.5 m); exit taxiway = SFO
                   Museum taxiway polygon(s) (data/sfo_airport.json) containing the first off-runway reports.
  go-around      = aligned with a runway (|dhdg| < 20 deg, |c| < 300 m, -9 km < a < 3.7 km) below 1000 ft above the
                   runway, descending before, then climbing >= 400 ft without any ground report in between.
  stop           = consecutive ground reports with gs < 1 kt spanning >= 20 s (gaps < 90 s).
  push-back      = ground motion (1-8 kt) whose direction (position chord >= 4 m) is > 120 deg from the reported
                   true_heading, or which leaves a stand against the stand's nose direction.
Usage: python3 tools/live/replay_events.py [--json out.json] [--quiet]
"""
import argparse, json, math, os, sys
from collections import Counter
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import (FT, KT, NM, RWY, PAIRS, build_reports, ident, is_vehicle, ll2w, on_runway, rwy_coords, wrap180,
                           load_stands, taxiway_polys, poly_names_at, app_types, load_json, OUT, utc)

GEOID_FT = 32.29 / FT                    # MSL = HAE + 105.9 ft at the ARP (EGM96)
AIRPORT_BOX = (-2700, 1950, -2350, 1800)  # traffic.js inAirport


def in_airport(x, z):
    return AIRPORT_BOX[0] < x < AIRPORT_BOX[1] and AIRPORT_BOX[2] < z < AIRPORT_BOX[3]


def num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else np.nan


class Arr:
    """column arrays of one aircraft's reports"""
    def __init__(self, L):
        self.L = L
        self.t = np.array([r['pt'] for r in L]); self.x = np.array([r['x'] for r in L]); self.z = np.array([r['z'] for r in L])
        self.g = np.array([r['ground'] for r in L])
        self.gs = np.array([num(r.get('gs')) for r in L]); self.trk = np.array([num(r.get('track')) for r in L])
        self.th = np.array([num(r.get('true_heading')) for r in L])
        self.alt = np.array([num(r.get('alt_baro')) for r in L]); self.geom = np.array([num(r.get('alt_geom')) for r in L])
        br = np.array([num(r.get('baro_rate')) for r in L]); gr = np.array([num(r.get('geom_rate')) for r in L])
        self.vr = np.where(np.isfinite(br), br, gr)
        self.hdg = np.where(np.isfinite(self.trk), self.trk, self.th)   # direction of travel when known


def rwy_fit(A, idx, names=None, amin=-7400, amax=1500):
    """median |c| of reports idx against every runway end (heading within 20 deg); sorted [(med|c|, name, n)]"""
    out = []
    for n in names or RWY:
        R = RWY[n]
        a, c = rwy_coords(n, A.x[idx], A.z[idx])
        dh = np.abs(wrap180(A.hdg[idx] - R['hdg_deg']))
        m = (dh < 20) & (a > amin) & (a < amax) & (np.abs(c) < 600)
        if m.sum() >= 3:
            out.append((float(np.median(np.abs(c[m]))), n, int(m.sum()), float(np.max(np.abs(c[m])))))
    return sorted(out)


def interp_cross(t, v, level=0.0):
    """time at which v crosses `level` going upward (first crossing)"""
    for i in range(1, len(v)):
        if np.isfinite(v[i - 1]) and np.isfinite(v[i]) and v[i - 1] < level <= v[i]:
            u = (level - v[i - 1]) / (v[i] - v[i - 1]); return t[i - 1] + u * (t[i] - t[i - 1]), i
    return None, None


def hinge_fit(t, y):
    """continuous two-segment linear fit; returns (tb, slope1, slope2, rms) minimising SSE over breakpoints."""
    best = None
    for k in range(2, len(t) - 2):
        tb = t[k]
        X = np.column_stack([np.ones_like(t), t - tb, np.maximum(0, t - tb)])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = y - X @ coef; sse = float(r @ r)
        if coef[2] < -0.3 and (best is None or sse < best[0]):
            best = (sse, float(tb), float(coef[1]), float(coef[1] + coef[2]))
    if best is None:
        return None
    return dict(t=best[1], s1=best[2], s2=best[3], rms=math.sqrt(best[0] / len(t)))


class Ctx:
    def __init__(self):
        self.stands = load_stands()
        self.twy = taxiway_polys()
        D = load_json('data/sfo_details.json')
        self.holds = D['holds']

    def twy_names(self, x, z):
        return [n for n in poly_names_at(self.twy, x, z)]

    def nearest_hold(self, x, z):
        best = None
        for h in self.holds:
            d = math.hypot(x - h['p'][0], z - h['p'][1])
            if best is None or d < best[0]:
                best = (d, h['twy'], h['rwy'], h['text'])
        return best

    def stand_candidates(self, x, z, L=None, hdg=None, k=3):
        """stands ranked by the app's antenna model (traffic.js gateScore: report vs nose - ANT*L along the stand
        heading; |lat| + 0.35 |along|) and plain distance to the nose point"""
        out = []
        for s in self.stands:
            if s['remote']:
                d = math.hypot(x - s['x'], z - s['z']); out.append((d + 4, s['name'], d, 0.0, d, None)); continue
            Lm = L or (63 if s['maxSpan'] > 40 else 38)
            ex, ez = s['x'] - s['dx'] * 0.2 * Lm, s['z'] - s['dz'] * 0.2 * Lm
            rx, rz = x - ex, z - ez
            along = -(rx * s['dx'] + rz * s['dz']); lat = -rx * s['dz'] + rz * s['dx']
            dh = None if hdg is None else float(abs(wrap180(hdg - math.degrees(s['hdg']))))
            out.append((abs(lat) + 0.35 * abs(along), s['name'], lat, along, math.hypot(x - s['x'], z - s['z']), dh))
        out.sort()
        return [dict(stand=o[1], score=round(o[0], 1), lat=round(o[2], 1), along=round(o[3], 1), dnose=round(o[4], 1), dhdg=None if o[5] is None else round(o[5], 1)) for o in out[:k]]


def find_stops(A, idx, min_dur=20.0, max_gap=90.0):
    """stops among ground report indices idx"""
    stops = []; cur = []
    for i in idx:
        still = np.isfinite(A.gs[i]) and A.gs[i] < 1.0
        if still and (not cur or A.t[i] - A.t[cur[-1]] < max_gap):
            cur.append(i)
        else:
            if cur and A.t[cur[-1]] - A.t[cur[0]] >= min_dur: stops.append(cur)
            cur = [i] if still else []
    if cur and A.t[cur[-1]] - A.t[cur[0]] >= min_dur: stops.append(cur)
    return stops


def analyse(hx, L, ctx, types):
    A = Arr(L); I = ident(L)
    veh = sum(is_vehicle(r) for r in L) > len(L) / 2
    T = types.get(I['icao'] or '') if I['icao'] else None
    res = dict(hex=hx, **I, vehicle=veh, n=len(L), t0=A.t[0], t1=A.t[-1], app_type=T and T['t'], L=T and T['L'],
               arrivals=[], departures=[], go_arounds=[], stops=[], pushbacks=[], ground_segments=[])
    near = np.array([in_airport(x, z) for x, z in zip(A.x, A.z)])
    res['sfo_ground'] = bool((A.g & near).any())
    # ---------------------------------------------------------------- arrivals
    for i in range(1, len(L)):
        if not (A.g[i] and not A.g[i - 1] and near[i]):
            continue
        j0 = i - 1
        while j0 > 0 and not A.g[j0 - 1] and A.t[i] - A.t[j0 - 1] < 400: j0 -= 1
        air = np.arange(j0, i)
        fit = rwy_fit(A, air)
        if not fit:
            res.setdefault('unmatched', []).append(dict(kind='air->ground without aligned final', t=A.t[i])); continue
        med, rw, nfit, cmax = fit[0]
        R = RWY[rw]
        a_all, c_all = rwy_coords(rw, A.x, A.z)
        t_thr, k_thr = interp_cross(A.t[j0:i + 60], a_all[j0:i + 60], 0.0)
        ev = dict(rwy=rw, pair=R['pair'], c_med=round(med, 1), c_max=round(cmax, 1), n_fit=nfit, runner_up=[(round(f[0], 1), f[1]) for f in fit[1:2]],
                  t_flag=A.t[i], a_flag=round(float(a_all[i]), 0), gs_flag=A.gs[i], gs_last_air=A.gs[i - 1], a_last_air=round(float(a_all[i - 1]), 0),
                  alt_last_air=A.alt[i - 1], dt_air_gnd=round(A.t[i] - A.t[i - 1], 2))
        if t_thr is not None:
            k = j0 + k_thr
            u = (t_thr - A.t[k - 1]) / max(1e-6, A.t[k] - A.t[k - 1])
            ev.update(t_thr=t_thr, gs_thr=float(A.gs[k - 1] + u * (A.gs[k] - A.gs[k - 1])),
                      alt_thr_baro=float(A.alt[k - 1] + u * (A.alt[k] - A.alt[k - 1])) if np.isfinite(A.alt[k]) and np.isfinite(A.alt[k - 1]) else None,
                      alt_thr_geom_msl=float(A.geom[k - 1] + u * (A.geom[k] - A.geom[k - 1]) + GEOID_FT) if np.isfinite(A.geom[k]) and np.isfinite(A.geom[k - 1]) else None)
            # cross-track at the threshold and over the last 1 NM
            m = (a_all[j0:i] > -1852) & (a_all[j0:i] < 0)
            ev['c_last_nm'] = round(float(np.median(c_all[j0:i][m])), 1) if m.any() else None
            # touchdown estimate: deceleration onset between the threshold and flag + 5 s
            w = np.where((A.t >= t_thr - 2) & (A.t <= A.t[i] + 5) & np.isfinite(A.gs))[0]
            if len(w) >= 6:
                h = hinge_fit(A.t[w], A.gs[w])
                if h:
                    ev['td_t'] = h['t']; ev['td_decel_before'] = round(h['s1'], 2); ev['td_decel_after'] = round(h['s2'], 2)
                    ev['td_a'] = round(float(np.interp(h['t'], A.t[w], a_all[w])), 0); ev['td_gs'] = round(float(np.interp(h['t'], A.t[w], A.gs[w])), 1)
                    ev['flag_lag_s'] = round(A.t[i] - h['t'], 1); ev['flag_lag_m'] = round(float(a_all[i] - ev['td_a']), 0)
            # airborne reports past the threshold: altitude read-outs while (probably) on the runway
            m2 = (np.arange(len(L)) >= j0) & (np.arange(len(L)) < i) & (a_all > 0)
            ev['alt_baro_past_thr'] = sorted(Counter(A.alt[m2][np.isfinite(A.alt[m2])].astype(int).tolist()).items())
        # rollout and exit
        k = i
        while k < len(L) and A.g[k] and abs(c_all[k]) <= 45 and A.t[k] - A.t[i] < 400: k += 1
        if k < len(L) and A.g[k] and abs(c_all[k]) > 45:
            names = []
            for q in range(k, min(len(L), k + 12)):
                if abs(c_all[q]) > 150: break
                for n in ctx.twy_names(A.x[q], A.z[q]):
                    if n not in names: names.append(n)
            k20 = k
            while k20 > i and abs(c_all[k20]) > 20: k20 -= 1
            ev.update(t_exit=A.t[k], a_exit=round(float(a_all[k]), 0), exit_side='right' if c_all[k] > 0 else 'left', exit_twy=names,
                      gs_exit=float(A.gs[k20]) if np.isfinite(A.gs[k20]) else None,
                      rot_s=round(A.t[k] - ev['t_thr'], 1) if ev.get('t_thr') else None)
            # speed along the rollout (kt) at 500 m steps past the threshold
            ev['rollout_gs'] = {int(d): round(float(np.interp(d, a_all[i - 5:k], A.gs[i - 5:k])), 1) for d in range(500, 3001, 500)
                                if a_all[i - 5] <= d <= a_all[k - 1] and np.all(np.diff(a_all[i - 5:k]) > -5)}
        res['arrivals'].append(ev)
    # ---------------------------------------------------------------- departures
    for i in range(1, len(L)):
        if not (A.g[i - 1] and not A.g[i] and near[i - 1]):
            continue
        k0 = i - 1
        while k0 > 0 and A.g[k0 - 1] and A.t[i] - A.t[k0 - 1] < 300: k0 -= 1
        k1 = i
        while k1 < len(L) - 1 and not A.g[k1 + 1] and A.t[k1 + 1] - A.t[i] < 90: k1 += 1
        roll = np.arange(k0, k1 + 1)
        fit = rwy_fit(A, roll, amin=-400, amax=4000)
        if not fit:
            res.setdefault('unmatched', []).append(dict(kind='ground->air without aligned runway', t=A.t[i])); continue
        med, rw, nfit, cmax = fit[0]; R = RWY[rw]
        a_all, c_all = rwy_coords(rw, A.x, A.z)
        a_phys = a_all + R['disp']               # distance from the physical runway end (start of the pavement)
        # roll start: last still report on the runway, else runway entry
        onr = [q for q in range(k0, i) if abs(c_all[q]) < 36 and -60 < a_phys[q] < R['len']]
        start = None; lineup = onr[0] if onr else None; rolling = False
        for q in range(i - 1, k0 - 1, -1):
            if abs(c_all[q]) < 36 and np.isfinite(A.gs[q]) and A.gs[q] <= 5:
                start = q; break
        if start is None and onr:
            start = onr[0]; rolling = True
        # liftoff: 3 consecutive vertical rates >= 192 fpm
        lo = None
        for q in range(i, k1 - 1):
            if all(np.isfinite(A.vr[q + e]) and A.vr[q + e] >= 192 for e in range(3)):
                lo = q; break
        ev = dict(rwy=rw, pair=R['pair'], c_med=round(med, 1), c_max=round(cmax, 1), runner_up=[(round(f[0], 1), f[1]) for f in fit[1:2]],
                  t_flag=A.t[i], gs_flag=A.gs[i], gs_last_gnd=A.gs[i - 1], a_flag=round(float(a_phys[i]), 0), dt_gnd_air=round(A.t[i] - A.t[i - 1], 2),
                  alt_flag_baro=A.alt[i])
        if start is not None:
            ev.update(t_roll=A.t[start], a_roll=round(float(a_phys[start]), 0), rolling_takeoff=rolling,
                      t_lineup=A.t[lineup] if lineup is not None else None, a_lineup=round(float(a_phys[lineup]), 0) if lineup is not None else None,
                      lineup_twy=ctx.twy_names(A.x[lineup - 1], A.z[lineup - 1]) if lineup else [])
        if lo is not None:
            ev.update(t_lo=A.t[lo], gs_lo=A.gs[lo], a_lo=round(float(a_phys[lo]), 0), lo_after_flag_s=round(A.t[lo] - A.t[i], 1),
                      lo_after_flag_m=round(float(a_phys[lo] - a_phys[i]), 0))
            if start is not None:
                ev['roll_s'] = round(A.t[lo] - A.t[start], 1); ev['roll_m'] = round(float(a_phys[lo] - a_phys[start]), 0)
        # alt_baro read-outs between the flag and liftoff (aircraft still on the runway)
        if lo is not None:
            ev['alt_baro_flag_to_lo'] = sorted(Counter(A.alt[i:lo][np.isfinite(A.alt[i:lo])].astype(int).tolist()).items())
            ev['geom_flag_to_lo'] = sorted(Counter(A.geom[i:lo][np.isfinite(A.geom[i:lo])].astype(int).tolist()).items())
        res['departures'].append(ev)
    # ---------------------------------------------------------------- go-arounds / low approaches
    i = 0
    while i < len(L):
        if A.g[i] or not np.isfinite(A.alt[i]):
            i += 1; continue
        hit = None
        for n in RWY:
            R = RWY[n]
            a, c = rwy_coords(n, A.x[i], A.z[i])
            if abs(wrap180(A.hdg[i] - R['hdg_deg'])) < 20 and abs(c) < 300 and -9000 < a < R['len'] and A.alt[i] - R['elev_ft'] < 1000:
                hit = n; break
        if hit:
            # descending before?
            pre = np.where((A.t > A.t[i] - 90) & (A.t < A.t[i]) & np.isfinite(A.alt))[0]
            if len(pre) and np.nanmax(A.alt[pre]) - A.alt[i] > 150:
                post = np.where((A.t > A.t[i]) & (A.t < A.t[i] + 150))[0]
                if len(post) and not A.g[post].any():
                    lowest = i + int(np.nanargmin(A.alt[i:post[-1] + 1])) if np.isfinite(A.alt[i:post[-1] + 1]).any() else i
                    after = A.alt[lowest:post[-1] + 1]
                    if lowest < post[-1] and np.isfinite(after).any() and np.nanmax(after) - A.alt[lowest] >= 400:
                        a, c = rwy_coords(hit, A.x[lowest], A.z[lowest])
                        res['go_arounds'].append(dict(rwy=hit, t_low=A.t[lowest], alt_low=A.alt[lowest], a_low=round(float(a), 0), c_low=round(float(c), 0),
                                                      gs_low=A.gs[lowest]))
                        i = post[-1] + 1; continue
        i += 1
    # ---------------------------------------------------------------- ground: segments, stops, push-backs, taxi routes
    gi = np.where(A.g & near)[0]
    segs = []; cur = []
    for q in gi:
        if cur and (q != cur[-1] + 1 or A.t[q] - A.t[cur[-1]] > 300):
            segs.append(cur); cur = []
        cur.append(q)
    if cur: segs.append(cur)
    for sg in segs:
        sg = np.array(sg)
        route = []; dist = 0.0
        for a_, b_ in zip(sg[:-1], sg[1:]):
            dist += math.hypot(A.x[b_] - A.x[a_], A.z[b_] - A.z[a_])
        for q in sg[::2]:
            if not (np.isfinite(A.gs[q]) and A.gs[q] >= 1.0): continue
            rp = on_runway(A.x[q], A.z[q])
            names = ['RWY ' + rp] if rp else ctx.twy_names(A.x[q], A.z[q])
            key = '+'.join(sorted(names)) if names else 'apron/other'
            if not route or route[-1] != key: route.append(key)
        mv = sg[np.isfinite(A.gs[sg]) & (A.gs[sg] >= 1.0)]
        segs_info = dict(t0=A.t[sg[0]], t1=A.t[sg[-1]], n=len(sg), dist_m=round(dist, 0), route=route,
                         gs_max=float(np.nanmax(A.gs[sg])) if np.isfinite(A.gs[sg]).any() else None,
                         gs_med_moving=float(np.median(A.gs[mv])) if len(mv) else None,
                         heading_frac=round(float(np.mean(np.isfinite(A.th[sg]) | np.isfinite(A.trk[sg]))), 2))
        res['ground_segments'].append(segs_info)
        for st in find_stops(A, sg):
            st = np.array(st)
            mx, mz = float(np.median(A.x[st])), float(np.median(A.z[st]))
            d = np.hypot(A.x[st] - mx, A.z[st] - mz)
            ths = A.th[st][np.isfinite(A.th[st])]
            hd = float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(ths))))) % 360) if len(ths) else None
            rp = on_runway(mx, mz)
            names = ctx.twy_names(mx, mz)
            hold = ctx.nearest_hold(mx, mz)
            cand = ctx.stand_candidates(mx, mz, L=T and T['L'], hdg=hd)
            res['stops'].append(dict(t0=A.t[st[0]], t1=A.t[st[-1]], dur=round(A.t[st[-1]] - A.t[st[0]], 0), x=round(mx, 1), z=round(mz, 1),
                                     n=len(st), jit_p50=round(float(np.median(d)), 1), jit_p95=round(float(np.percentile(d, 95)), 1), jit_max=round(float(d.max()), 1),
                                     hdg=None if hd is None else round(hd, 1), hdg_n=len(ths), hdg_spread=round(float(np.ptp(wrap180(ths - hd))), 1) if len(ths) else None,
                                     runway=rp, twy=names, hold=(round(hold[0], 0),) + hold[1:] if hold else None, stands=cand,
                                     first=bool(st[0] == sg[0]), last=bool(st[-1] == sg[-1])))
        # push-backs: motion against the reported nose heading
        q = 0
        while q < len(sg):
            a_ = sg[q]
            if np.isfinite(A.gs[a_]) and 0.5 <= A.gs[a_] <= 8 and np.isfinite(A.th[a_]):
                # chord direction to the first report >= 4 m away
                b_ = next((r for r in sg[q + 1:q + 15] if math.hypot(A.x[r] - A.x[a_], A.z[r] - A.z[a_]) >= 4), None)
                if b_ is not None:
                    mvh = math.degrees(math.atan2(A.x[b_] - A.x[a_], -(A.z[b_] - A.z[a_]))) % 360
                    if abs(wrap180(mvh - A.th[a_])) > 120:
                        # extend while moving backwards
                        e = q
                        while e + 1 < len(sg) and np.isfinite(A.gs[sg[e + 1]]) and A.gs[sg[e + 1]] <= 8 and not (np.isfinite(A.th[sg[e + 1]]) and False):
                            nx = sg[e + 1]
                            if np.isfinite(A.gs[nx]) and A.gs[nx] < 0.5 and A.t[nx] - A.t[sg[e]] > 20: break
                            e += 1
                            if A.t[sg[e]] - A.t[a_] > 400: break
                        cand = ctx.stand_candidates(A.x[a_], A.z[a_], L=T and T['L'], hdg=float(A.th[a_]))
                        res['pushbacks'].append(dict(t0=A.t[a_], hdg=float(A.th[a_]), move_dir=round(mvh, 1), gs=float(A.gs[a_]), stands=cand[:2]))
                        # skip to the end of this reverse motion
                        while q < len(sg) and not (np.isfinite(A.gs[sg[q]]) and A.gs[sg[q]] < 0.5) and A.t[sg[q]] - A.t[a_] < 400: q += 1
                        continue
            q += 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=os.path.join(OUT, 'events.json'))
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()
    tracks, meta = build_reports()
    ctx = Ctx()
    types = app_types([ident(L)['icao'] for L in tracks.values()])
    out = []
    for hx, L in sorted(tracks.items()):
        r = analyse(hx, L, ctx, types)
        out.append(r)
    json.dump(dict(meta=meta, aircraft=out), open(args.json, 'w'), default=lambda o: None if isinstance(o, float) and not math.isfinite(o) else (float(o) if isinstance(o, (np.floating,)) else (int(o) if isinstance(o, np.integer) else str(o))), indent=0)
    if args.quiet:
        return
    t0 = min(p['t0'] for p in meta['providers'].values()); t1 = max(p['t1'] for p in meta['providers'].values())
    print(f'recording {utc(t0)} - {utc(t1)} UTC ({(t1 - t0) / 60:.0f} min); {len(out)} hexes')
    f = lambda v, d=0: '-' if v is None or (isinstance(v, float) and not math.isfinite(v)) else (f'{v:.{d}f}' if isinstance(v, (int, float)) else str(v))
    print('\nARRIVALS')
    for r in out:
        for e in r['arrivals']:
            print(f"  {utc(e.get('t_thr') or e['t_flag'])} {r['flight'] or r['reg']:8s} {r['icao'] or '?':5s} {e['rwy']:4s} c_med {f(e['c_med'],1)} (next {e['runner_up']})"
                  f" thr gs {f(e.get('gs_thr'))} alt {f(e.get('alt_thr_baro'))}/{f(e.get('alt_thr_geom_msl'))}msl | TD~{f(e.get('td_a'))} m gs {f(e.get('td_gs'))}"
                  f" decel {e.get('td_decel_before')}->{e.get('td_decel_after')} kt/s | flag +{f(e.get('flag_lag_s'),1)} s +{f(e.get('flag_lag_m'))} m gs {f(e['gs_flag'])}"
                  f" (last air {f(e['gs_last_air'])} kt, {f(e['alt_last_air'])} ft) | exit {e.get('exit_twy')} a {f(e.get('a_exit'))} gs {f(e.get('gs_exit'))} ROT {f(e.get('rot_s'))} s")
    print('\nDEPARTURES')
    for r in out:
        for e in r['departures']:
            print(f"  {utc(e['t_flag'])} {r['flight'] or r['reg']:8s} {r['icao'] or '?':5s} {e['rwy']:4s} c_med {f(e['c_med'],1)} | lineup {e.get('lineup_twy')} a {f(e.get('a_lineup'))}"
                  f" roll a {f(e.get('a_roll'))} rolling {e.get('rolling_takeoff')} | flag a {f(e['a_flag'])} gs {f(e['gs_flag'])} (last gnd {f(e['gs_last_gnd'])}) alt {e['alt_flag_baro']}"
                  f" | LO~ a {f(e.get('a_lo'))} gs {f(e.get('gs_lo'))} +{f(e.get('lo_after_flag_s'),1)} s +{f(e.get('lo_after_flag_m'))} m | roll {f(e.get('roll_s'))} s {f(e.get('roll_m'))} m")
    print('\nGO-AROUNDS')
    for r in out:
        for e in r['go_arounds']:
            print(f"  {utc(e['t_low'])} {r['flight'] or r['reg']} {e}")
    print('\nSTOPS (aircraft, >= 20 s)')
    for r in out:
        if r['vehicle']: continue
        for s in r['stops']:
            c = s['stands'][0]
            print(f"  {utc(s['t0'])}-{utc(s['t1'])} {r['flight'] or r['reg']:8s} {r['icao'] or '?':5s} {s['dur']:5.0f}s jit {s['jit_p95']:5.1f} m hdg {f(s['hdg'])}({s['hdg_n']})"
                  f" rwy {s['runway'] or '-'} twy {'+'.join(s['twy']) or '-'} hold {s['hold']} | stand {c['stand']} lat {c['lat']} along {c['along']} dnose {c['dnose']} dhdg {c['dhdg']}")
    print('\nPUSH-BACKS')
    for r in out:
        for p in r['pushbacks']:
            print(f"  {utc(p['t0'])} {r['flight'] or r['reg']:8s} hdg {p['hdg']:.1f} moving {p['move_dir']:.0f} gs {p['gs']} from {p['stands'][0]}")


if __name__ == '__main__':
    main()
