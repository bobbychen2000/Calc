#!/usr/bin/env python3
"""Characterise the recorded ADS-B around SFO for the traffic audit (docs/research/traffic_audit.md section 3):
stationary jitter, update gaps (merged, per provider and as the app polls), heading availability on the ground,
quantisation, baro vs geometric altitude and QNH, air/ground flag vs events, source types (ADS-B/ADS-R/MLAT/TIS-B),
duplicate/ghost targets, teleports and airport vehicles.

Inputs: refs/cache/rec (recordings), refs/cache/replay/events.json (tools/live/replay_events.py), METARs cached by
tools/live/replay_wx.py. Output: stdout report + refs/cache/replay/datachar.json.
All statistics are OBSERVED from the recording unless a line says "inferred".
Usage: python3 tools/live/replay_datachar.py
"""
import json, math, os, sys
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import FT, KT, NM, OUT, ROOT, RWY, build_reports, ident, is_vehicle, snapshots, request_log, wrap180, utc, on_runway, rwy_coords, ll2w, load_json
from replay_events import in_airport, find_stops, Arr
import replay_wx

P = lambda a, q: float(np.percentile(a, q)) if len(a) else float('nan')


def pct(a, qs=(50, 90, 95, 99)):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    return {f'p{q}': round(P(a, q), 2) for q in qs} | {'n': int(len(a)), 'max': round(float(a.max()), 2) if len(a) else None}


def main():
    tracks, meta = build_reports()
    E = json.load(open(os.path.join(OUT, 'events.json')))
    ev = {a['hex']: a for a in E['aircraft']}
    R = {}
    # ------------------------------------------------------------------ provider requests / errors / latency
    rq = {}
    for prov in ('adsbfi', 'adsblol'):
        log = request_log(prov)
        errs = Counter((e or '')[:40] for t, ok, e in log if not ok)
        ts = np.array([t for t, ok, e in log if ok])
        rq[prov] = dict(requests=len(log), ok=int(sum(ok for _, ok, _ in log)), errors=dict(errs.most_common(5)), ok_interval=pct(np.diff(ts)))
        # age of each fresh position at request time, and server 'now' steps
        ages = []; nows = []
        for req, now, acs in snapshots(prov):
            nows.append(now)
            for a in acs:
                if a.get('seen_pos') is not None and a.get('alt_baro') != 'ground' and a.get('dst') is not None and a['dst'] < 10:
                    ages.append(req - (now - a['seen_pos']))
        dn = np.diff(np.unique(np.array(nows)))
        rq[prov]['now_step'] = pct(dn); rq[prov]['age_at_request_air10nm'] = pct(ages)
    R['requests'] = rq
    # ------------------------------------------------------------------ source types, categories, vehicles, ghosts
    types = Counter(); gtypes = Counter(); mlat_fields = Counter(); tisb = 0; nrep = 0
    veh = []; nonicao = []
    cs_hex = defaultdict(set)
    for hx, L in tracks.items():
        I = ident(L)
        for r in L:
            nrep += 1; types[r.get('type')] += 1
            if r['ground'] and in_airport(r['x'], r['z']): gtypes[r.get('type')] += 1
            for f in (r.get('mlat') or []): mlat_fields[f] += 1
            if r.get('tisb'): tisb += 1
            if r.get('flight'): cs_hex[r['flight'].strip()].add(hx)
        if hx.startswith('~'):
            nonicao.append(dict(hex=hx, n=len(L), type=I['src'], ground=sum(r['ground'] for r in L), near=sum(in_airport(r['x'], r['z']) for r in L)))
        vflag = [is_vehicle(r) for r in L]
        if sum(vflag) > len(L) / 2:
            nocat = sum(1 for r in L if not (r.get('category') or '').startswith('C') and r.get('t') not in ('SERV',))
            gs = np.array([r['gs'] for r in L if isinstance(r.get('gs'), (int, float))])
            onrwy = sum(1 for r in L if on_runway(r['x'], r['z']))
            veh.append(dict(hex=hx, flight=I['flight'], reg=I['reg'], op=I['op'], cat=I['cat'], t=I['icao'], src=I['src'], n=len(L),
                            reports_without_C_category=nocat, gs_max=float(gs.max()) if len(gs) else None, reports_on_runway=onrwy))
    dup_cs = {c: sorted(h) for c, h in cs_hex.items() if len(h) > 1}
    R['source_types_all'] = dict(types.most_common()); R['source_types_sfo_ground'] = dict(gtypes.most_common())
    R['mlat_derived_fields'] = dict(mlat_fields.most_common()); R['tisb_reports'] = tisb; R['reports'] = nrep
    R['vehicles'] = veh; R['non_icao'] = nonicao; R['callsign_on_several_hexes'] = dup_cs
    # ------------------------------------------------------------------ cross-provider timing of identical reports
    same_pos_dt = []
    for hx, L in tracks.items():
        seen = {}
        for r in L:
            k = (r['lat'], r['lon'])
            if k in seen and seen[k]['prov'] != r['prov'] and not r['ground'] and r.get('gs') and r['gs'] > 50:
                same_pos_dt.append(r['pt'] - seen[k]['pt'])
            seen.setdefault(k, r)
    R['identical_airborne_position_time_diff_between_providers_s'] = pct(np.abs(same_pos_dt))
    # ------------------------------------------------------------------ per-state update intervals (merged) + teleports
    gaps = defaultdict(list); tele = []
    for hx, L in tracks.items():
        if sum(is_vehicle(r) for r in L) > len(L) / 2: continue
        A = Arr(L)
        for i in range(1, len(L)):
            dt = A.t[i] - A.t[i - 1]
            if dt <= 0: continue
            x, z = A.x[i], A.z[i]
            if A.g[i] and in_airport(x, z):
                st = 'ground_moving' if (np.isfinite(A.gs[i]) and A.gs[i] >= 1) else 'ground_still'
            elif not A.g[i] and math.hypot(x, z) < 10 * NM and np.isfinite(A.alt[i]) and A.alt[i] < 5000:
                st = 'air_below5000_10nm'
            else:
                st = 'other'
            gaps[st].append(dt)
            d = math.hypot(A.x[i] - A.x[i - 1], A.z[i] - A.z[i - 1])
            vmax = max(A.gs[i] if np.isfinite(A.gs[i]) else 0, A.gs[i - 1] if np.isfinite(A.gs[i - 1]) else 0) * KT
            if d > 30 and d > 1.5 * vmax * dt + 30:
                tele.append(dict(hex=hx, flight=ident(L)['flight'], t=A.t[i], dt=round(dt, 2), jump_m=round(d, 0), gs_kt=float(A.gs[i]) if np.isfinite(A.gs[i]) else None,
                                 ground=bool(A.g[i]), provs=(L[i - 1]['prov'], L[i]['prov'])))
    R['merged_update_interval_s'] = {k: pct(v) | {'gt10s': int(np.sum(np.array(v) > 10)), 'gt30s': int(np.sum(np.array(v) > 30))} for k, v in gaps.items()}
    R['teleports'] = tele
    # ------------------------------------------------------------------ what the app sees: one provider polled every 5 or 7 s
    app = {}
    for prov in ('adsblol', 'adsbfi'):
        for period in (5.0, 7.0):
            last = {}; last_req = 0; iv = defaultdict(list); fresh = []; n = 0
            for req, now, acs in snapshots(prov):
                if req - last_req < period: continue
                last_req = req; n += 1
                for a in acs:
                    if a.get('seen_pos') is None: continue
                    hx = a['hex']; pt = now - a['seen_pos']
                    near = a.get('dst') is not None and a['dst'] < 5
                    if not near: continue
                    k = 'ground' if a.get('alt_baro') == 'ground' else 'air'
                    if hx in last and pt > last[hx] + 0.05:
                        iv[k].append(pt - last[hx]); fresh.append(1)
                    elif hx in last:
                        fresh.append(0)
                    last[hx] = max(pt, last.get(hx, 0))
            app[f'{prov}_{int(period)}s'] = {k: pct(v) for k, v in iv.items()} | {'polls': n, 'fraction_polls_with_new_position': round(float(np.mean(fresh)), 3) if fresh else None}
    R['app_poll_intervals_within_5nm'] = app
    # ------------------------------------------------------------------ ground: jitter, heading, quantisation
    jit = []; jit_rows = []
    hd_counts = Counter(); th_grid = []; th_vs_motion = []
    for hx, L in tracks.items():
        if sum(is_vehicle(r) for r in L) > len(L) / 2: continue
        A = Arr(L)
        gi = np.where(A.g & np.array([in_airport(x, z) for x, z in zip(A.x, A.z)]))[0]
        for st in find_stops(A, gi, min_dur=60):
            st = np.array(st); mx, mz = np.median(A.x[st]), np.median(A.z[st]); d = np.hypot(A.x[st] - mx, A.z[st] - mz)
            nac = Counter(L[i].get('nac_p') for i in st).most_common(1)[0][0]
            jit.append((P(d, 50), P(d, 95), float(d.max()), nac)); jit_rows.append(dict(hex=hx, flight=ident(L)['flight'], dur=round(A.t[st[-1]] - A.t[st[0]]), p50=round(P(d, 50), 1), p95=round(P(d, 95), 1), max=round(float(d.max()), 1), nac_p=nac,
                                                                                              gs_all_zero=bool(np.all(A.gs[st][np.isfinite(A.gs[st])] < 0.2))))
        for i in gi:
            moving = np.isfinite(A.gs[i]) and A.gs[i] >= 1
            k = ('moving' if moving else 'still', 'true_heading' if np.isfinite(A.th[i]) else ('track' if np.isfinite(A.trk[i]) else 'none'))
            hd_counts[k] += 1
            if np.isfinite(A.th[i]): th_grid.append(A.th[i])
        # true heading vs direction of motion while taxiing forward (chord over >= 10 m within 6 s)
        for a_, b_ in zip(gi[:-1], gi[1:]):
            if not (np.isfinite(A.th[b_]) and np.isfinite(A.gs[b_]) and A.gs[b_] >= 8): continue
            d = math.hypot(A.x[b_] - A.x[a_], A.z[b_] - A.z[a_])
            if d < 10 or A.t[b_] - A.t[a_] > 6: continue
            mv = math.degrees(math.atan2(A.x[b_] - A.x[a_], -(A.z[b_] - A.z[a_]))) % 360
            th_vs_motion.append(float(wrap180(A.th[b_] - mv)))
    jit = np.array(jit) if jit else np.zeros((0, 4))
    R['stationary_jitter_m'] = dict(stops=len(jit), p50_of_stop_p50=round(P(jit[:, 0], 50), 1), p50_of_stop_p95=round(P(jit[:, 1], 50), 1), p90_of_stop_p95=round(P(jit[:, 1], 90), 1),
                                   max_of_max=round(float(jit[:, 2].max()), 1) if len(jit) else None,
                                   by_nac_p={str(int(k)): round(P(jit[jit[:, 3] == k, 1], 50), 1) for k in np.unique(jit[:, 3]) if np.isfinite(k)}, rows=sorted(jit_rows, key=lambda r: -r['p95'])[:12])
    tot = Counter(); [tot.update({k[0]: v}) for k, v in hd_counts.items()]
    R['ground_heading_availability'] = {f'{a}/{b}': round(v / tot[a], 3) for (a, b), v in sorted(hd_counts.items())} | {'n_moving': tot['moving'], 'n_still': tot['still']}
    g = np.array(th_grid); q = 360 / 128
    R['true_heading_on_2.8125_grid'] = round(float(np.mean(np.abs(g / q - np.round(g / q)) < 0.01)), 3) if len(g) else None
    R['true_heading_minus_motion_deg_taxi_ge8kt'] = pct(np.abs(th_vs_motion))
    # quantisation of air fields
    alt = []; geo = []; br = []; gsd = []; trk = []
    for L in tracks.values():
        for r in L:
            if isinstance(r.get('alt_baro'), (int, float)): alt.append(r['alt_baro'])
            if isinstance(r.get('alt_geom'), (int, float)): geo.append(r['alt_geom'])
            if isinstance(r.get('baro_rate'), (int, float)): br.append(r['baro_rate'])
            if isinstance(r.get('gs'), (int, float)): gsd.append(r['gs'])
    alt, geo, br = np.array(alt), np.array(geo), np.array(br)
    R['quantisation'] = dict(alt_baro_mult25=round(float(np.mean(alt % 25 == 0)), 4), alt_baro_mult100=round(float(np.mean(alt % 100 == 0)), 4),
                             alt_geom_mult25=round(float(np.mean(geo % 25 == 0)), 4), baro_rate_mult64=round(float(np.mean(br % 64 == 0)), 4),
                             alt_baro_n=len(alt))
    # ------------------------------------------------------------------ baro vs geometric and QNH
    M, AT = replay_wx.timeline()
    metar_q = sorted((t, m['altim']) for t, m in M.items())
    def qnh_at(t):
        prev = [q for tt, q in metar_q if tt <= t]; return prev[-1] if prev else (metar_q[0][1] if metar_q else 1013.25)
    bands = defaultdict(list); navq = []
    for L in tracks.values():
        for r in L:
            if r['ground'] or not isinstance(r.get('alt_baro'), (int, float)): continue
            if math.hypot(r['x'], r['z']) > 25 * NM: continue
            Q = qnh_at(r['pt'])
            hq = r['alt_baro'] + 145366.45 * (1 - (1013.25 / Q) ** 0.190284)      # pressure altitude -> QNH altitude (ISA)
            if isinstance(r.get('nav_qnh'), (int, float)) and r['alt_baro'] < 10000: navq.append(r['nav_qnh'] - Q)
            if isinstance(r.get('alt_geom'), (int, float)):
                b = min(int(hq // 1000), 9) if hq >= 0 else -1
                bands[b].append(r['alt_geom'] + 32.29 / FT - hq)     # geometric MSL (EGM96) minus QNH altitude
    R['geom_msl_minus_qnh_alt_ft_by_1000ft_band'] = {str(k): pct(v, (10, 50, 90)) for k, v in sorted(bands.items())}
    R['nav_qnh_minus_metar_hpa'] = pct(navq, (5, 50, 95))
    R['metar_altimeter'] = metar_q
    # ------------------------------------------------------------------ air/ground flag vs events (from events.json)
    arr = [e for a in E['aircraft'] for e in a['arrivals']]; dep = [e for a in E['aircraft'] for e in a['departures']]
    R['flag_arrivals'] = dict(n=len(arr), gs_first_ground=pct([e['gs_flag'] for e in arr]), gs_last_air=pct([e['gs_last_air'] for e in arr]),
                              lag_after_td_s=pct([e['flag_lag_s'] for e in arr if e.get('flag_lag_s') is not None]), lag_after_td_m=pct([e['flag_lag_m'] for e in arr if e.get('flag_lag_m') is not None]),
                              a_flag_m=pct([e['a_flag'] for e in arr]), alt_baro_last_air=Counter(int(e['alt_last_air']) for e in arr if e.get('alt_last_air') is not None).most_common())
    R['flag_departures'] = dict(n=len(dep), gs_first_air=pct([e['gs_flag'] for e in dep]), gs_last_ground=pct([e['gs_last_gnd'] for e in dep]),
                                lo_after_flag_s=pct([e['lo_after_flag_s'] for e in dep if e.get('lo_after_flag_s') is not None]),
                                lo_after_flag_m=pct([e['lo_after_flag_m'] for e in dep if e.get('lo_after_flag_m') is not None]),
                                alt_baro_at_flag=Counter(int(e['alt_flag_baro']) for e in dep if e.get('alt_flag_baro') is not None).most_common())
    # ------------------------------------------------------------------ glide path: alt_geom (MSL) vs the published ILS/RNAV path
    # FAA d-TPP cycle 2609 (aeronav.faa.gov/d-tpp/2609/): ILS OR LOC RWY 28L GS 2.85 deg TCH 53 ft (Amdt 27C);
    # ILS OR LOC RWY 28R GS 3.00 deg TCH 55 ft (Amdt 15B); ILS OR LOC RWY 19L GS 3.00 deg TCH 55 ft (Amdt 23A);
    # RNAV (GPS) RWY 10L GP 3.00 deg TCH 55 ft. Threshold elevations js/geo.js RWY_ENDS (FAA/AirNav).
    GS = {'28L': (2.85, 53), '28R': (3.00, 55), '19L': (3.00, 55), '10L': (3.00, 55)}
    gp = []
    for a in E['aircraft']:
        for e in a['arrivals']:
            if e['rwy'] not in GS: continue
            ang, tch = GS[e['rwy']]; L = tracks[a['hex']]
            res = []
            for r in L:
                if r['ground'] or not isinstance(r.get('alt_geom'), (int, float)) or r['pt'] > e['t_flag'] or r['pt'] < e['t_flag'] - 400: continue
                aa, c = rwy_coords(e['rwy'], r['x'], r['z'])
                if -9000 < aa < -300:
                    exp = RWY[e['rwy']]['elev_ft'] + tch + (-aa) / FT * math.tan(math.radians(ang))
                    res.append(r['alt_geom'] + 32.29 / FT - exp)
            if res: gp.append(dict(flight=a['flight'], rwy=e['rwy'], n=len(res), resid_ft_p50=round(float(np.median(res)), 1), p10=round(P(res, 10), 1), p90=round(P(res, 90), 1)))
    R['glidepath_geom_minus_published_ft'] = gp
    # ------------------------------------------------------------------ surface 'track' vs true_heading, per provider (section 4.3)
    st = defaultdict(list); st_int = Counter(); st_mlat = Counter()
    for prov in ('adsbfi', 'adsblol'):
        for req, now, acs in snapshots(prov):
            for a in acs:
                if a.get('alt_baro') != 'ground' or a.get('track') is None or (a.get('category') or '')[:1] == 'C': continue
                x, z = ll2w(a['lat'], a['lon'])
                if not in_airport(float(x), float(z)): continue
                st_int[(prov, float(a['track']).is_integer())] += 1
                if 'track' in (a.get('mlat') or []): st_mlat[prov] += 1
                if a.get('true_heading') is not None and (a.get('gs') or 0) > 5:
                    st[prov].append(abs((a['track'] - a['true_heading'] + 180) % 360 - 180))
    R['surface_track_vs_true_heading'] = {p: dict(pairs=len(v), frac_gt90=round(float(np.mean(np.array(v) > 90)), 3), p50=round(P(v, 50), 1),
                                              track_reports=st_int[(p, True)] + st_int[(p, False)], whole_degree=st_int[(p, True)], mlat_lists_track=st_mlat[p]) for p, v in st.items()}
    # ------------------------------------------------------------------ taxi networks vs real taxi tracks (section 6.8)
    try:
        from scipy.spatial import cKDTree
        def kd(polys):
            pts = []
            for pl in polys:
                q = np.array(pl, float)
                for a_, b_ in zip(q[:-1], q[1:]):
                    n = max(1, int(np.hypot(*(b_ - a_)) / 1.0))
                    for u in np.linspace(0, 1, n + 1): pts.append(a_ + (b_ - a_) * u)
            return cKDTree(np.array(pts))
        nets = {'sfo_details_centerlines': load_json('data/sfo_details.json')['centerlines']}
        xp = os.path.join(ROOT, 'refs', 'cache', 'xplane', 'ksfo_apt_parsed.json')
        if os.path.exists(xp):
            X = json.load(open(xp)); N_ = X['taxi_nodes']
            nets['xplane_gateway_1201_1202'] = [[[float(v) for v in ll2w(N_[e['a']]['lat'], N_[e['a']]['lon'])], [float(v) for v in ll2w(N_[e['b']]['lat'], N_[e['b']]['lon'])]] for e in X['taxi_edges']]
        op = os.path.join(ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')
        if os.path.exists(op):
            O = json.load(open(op)); nets['osm_taxiway_taxilane'] = [[[float(v) for v in ll2w(la, lo)] for la, lo in w['pts']] for w in O['taxiways']]
        pts = []
        for hx, L in tracks.items():
            if sum(is_vehicle(r) for r in L) > len(L) / 2: continue
            for r in L:
                if r['ground'] and in_airport(r['x'], r['z']) and isinstance(r.get('gs'), (int, float)) and r['gs'] >= 3 and not on_runway(r['x'], r['z']):
                    pts.append((r['x'], r['z']))
        pts = np.array(pts)
        R['taxi_network_fit_m'] = {k: (lambda d: dict(n=len(d), p50=round(P(d, 50), 1), p90=round(P(d, 90), 1), p95=round(P(d, 95), 1), frac_gt10=round(float(np.mean(d > 10)), 3)))(kd(v).query(pts)[0]) for k, v in nets.items()}
    except Exception as e:
        R['taxi_network_fit_m'] = str(e)
    R['source_types_all_pct'] = {k: round(100 * v / sum(types.values()), 1) for k, v in types.items()}
    json.dump(R, open(os.path.join(OUT, 'datachar.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str)[:20000])


if __name__ == '__main__':
    main()
