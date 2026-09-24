#!/usr/bin/env python3
"""Score the app's displayed traffic (tools/live/replay_app.mjs log) against the recorded truth (1 Hz merged reports
and the events of tools/live/replay_events.py). Section 4 of docs/research/traffic_audit.md.

Truth at display time: the app shows, at wall time T, the state for T - delay (traffic.js DELAY/app.js delay). Every
logged row (T, hex, ...) is compared with the merged reports interpolated at td = T - delay (linear between the
bracketing reports; no truth if they are > 12 s apart airborne / > 30 s moving on the ground).
Metrics (OBSERVED from the replay unless marked):
  position   horizontal |displayed - truth(td)| by state; lag = |displayed - truth(T)| (what "real time" costs)
  jumps      displayed speed between consecutive rows > 1.5 x truth speed + 5 m/s (teleports, snap slides)
  heading    |displayed - truth| on the ground (truth = true_heading, else track, else motion chord)
  vertical   displayed height above GROUND_Y while the aircraft is really on the runway (touchdown->exit,
             take-off roll before liftoff) and gear state; airborne height error below 1500 ft (truth = alt_geom
             converted to MSL with the EGM96 undulation, referenced to the aircraft's own on-runway alt_geom)
  phase      confusion (seconds) between the app phase and the truth phase at td
  runway     app runway during final/landing/takeoff vs the event runway
  stands     app gate while the truth is stopped >= 120 s, vs SFO's own allocation (tools/live/gatecheck.py output,
             refs/cache/replay/gatecheck_every120.json, if present) and vs the nearest stand
  surface    gear points off pavement / airframe in a building / planform overlaps (from the harness), and the same
             pavement test applied to the RAW reports (to separate data from logic)
Usage: python3 tools/live/replay_audit.py refs/cache/replay/app_relay5.jsonl.gz [--delay 7.5] [--json out.json]
"""
import argparse, gzip, json, math, os, sys
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import FT, KT, NM, OUT, RWY, GROUND_Y, build_reports, ident, is_vehicle, wrap180, utc, on_runway, rwy_coords
from replay_events import Arr, in_airport

COLS = ['T', 'hex', 'phase', 'rwy', 'gate', 'x', 'y', 'z', 'hdg', 'pitch', 'roll', 'gear', 'flaps', 'spoilers', 'ground', 'gs', 'extrap', 'stale', 'finA', 'dir', 'label', 'cat',
        'offPave', 'inBld', 'overlaps', 'physOff', 'flight', 'icao', 'model']
GEOID_M = 32.29


def pct(a, qs=(50, 90, 99)):
    a = np.asarray([v for v in a if v is not None and np.isfinite(v)], float)
    if not len(a): return {'n': 0}
    return {f'p{q}': round(float(np.percentile(a, q)), 2) for q in qs} | {'n': int(len(a)), 'max': round(float(a.max()), 2)}


def load_masks():
    p = os.path.join(OUT, 'masks_1m.pgm')
    if not os.path.exists(p): return None
    b = open(p, 'rb').read(); parts = b.split(b'\n', 4); W, H = map(int, parts[2].split())
    return np.frombuffer(parts[4], np.uint8).reshape(H, W)


class Truth:
    def __init__(self, tracks, events):
        self.tr = tracks; self.ev = {a['hex']: a for a in events['aircraft']}; self.A = {}
    def arr(self, hx):
        if hx not in self.A:
            L = self.tr.get(hx); self.A[hx] = Arr(L) if L else None
        return self.A[hx]
    def at(self, hx, t):
        A = self.arr(hx)
        if A is None: return None
        i = int(np.searchsorted(A.t, t))
        if i == 0 or i >= len(A.t): return None
        a, b = i - 1, i; dt = A.t[b] - A.t[a]
        g = bool(A.g[a] and A.g[b])
        mov = np.isfinite(A.gs[a]) and A.gs[a] >= 1
        lim = 30 if g and mov else (12 if not g else 120)
        if dt > lim: return None
        u = (t - A.t[a]) / dt if dt > 0 else 0
        x = A.x[a] + u * (A.x[b] - A.x[a]); z = A.z[a] + u * (A.z[b] - A.z[a])
        h = A.th[a] if np.isfinite(A.th[a]) else A.trk[a]
        geom = A.geom[a] + u * (A.geom[b] - A.geom[a]) if np.isfinite(A.geom[a]) and np.isfinite(A.geom[b]) else np.nan
        gs = A.gs[a] if np.isfinite(A.gs[a]) else np.nan
        return dict(x=x, z=z, ground=g, gs=gs, hdg=h, geom=geom, alt=A.alt[a])
    def phase(self, hx, t, st):
        """truth phase group at time t"""
        E = self.ev.get(hx)
        if E is None or st is None: return None, None
        for e in E['arrivals']:
            td = e.get('td_t') or e['t_flag']
            if td - 900 <= t < td:
                if st['ground']: return 'rollout', e['rwy']
                a, c = rwy_coords(e['rwy'], st['x'], st['z'])
                if -30000 < a < 1500 and abs(c) < 150 + 0.1 * abs(a): return 'final', e['rwy']
                return 'approach', e['rwy']
            if td <= t < (e.get('t_exit') or td + 60): return 'rollout', e['rwy']
        for e in E['departures']:
            t0 = e.get('t_roll') or e['t_flag'] - 30; t1 = e.get('t_lo') or e['t_flag'] + 20
            if t0 <= t < t1: return 'takeoff', e['rwy']
            if t1 <= t < t1 + 300 and not st['ground']: return 'departure', e['rwy']
        if st['ground'] and in_airport(st['x'], st['z']):
            for p in E['pushbacks']:
                if p['t0'] <= t < p['t0'] + 120 and np.isfinite(st['gs']) and st['gs'] >= 0.5: return 'pushback', None
            if np.isfinite(st['gs']) and st['gs'] >= 1.5: return 'taxi', None
            return 'still', None
        if not st['ground']: return 'air-other', None
        return 'ground-other', None


APP_GROUP = {'final': 'final', 'approach': 'approach', 'landing': 'rollout', 'takeoff': 'takeoff', 'departure': 'departure', 'taxi': 'taxi', 'pushback': 'pushback',
             'holding': 'still', 'gate': 'still', 'parked': 'still', 'enroute': 'air-other', 'ground-other': 'ground-other', 'new': 'new', 'stopped': 'still'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log'); ap.add_argument('--delay', type=float, default=None); ap.add_argument('--json')
    o = ap.parse_args()
    rows = []; phase_ev = []; tail = None; meta = None
    with gzip.open(o.log, 'rt') as f:
        for l in f:
            j = json.loads(l)
            if isinstance(j, list): rows.append(dict(zip(COLS, j)))
            elif 'meta' in j: meta = j['meta']
            elif j.get('ev') == 'phase': phase_ev.append(j)
            else: tail = j
    delay = o.delay if o.delay is not None else meta['delay'] / 1000
    tracks, _ = build_reports()
    events = json.load(open(os.path.join(OUT, 'events.json')))
    TR = Truth(tracks, events)
    masks = load_masks()
    veh = {hx for hx, L in tracks.items() if sum(is_vehicle(r) for r in L) > len(L) / 2}
    R = {'log': os.path.basename(o.log), 'meta': meta, 'rows': len(rows)}
    by = defaultdict(list)
    for r in rows: by[r['hex']].append(r)
    R['vehicle_tracks_in_app'] = sorted(h for h in by if h in veh)
    # ------------------------------------------------------------------ position / lag / heading / vertical / phase
    perr = defaultdict(list); lag = defaultdict(list); herr = []; hflip = []; conf = Counter(); runway_bad = []; runway_ok = 0
    vert_gnd = []; gear_up_gnd = []; vair = []; jumps = []; slides = []
    phase_windows = defaultdict(Counter)
    for hx, L in by.items():
        if hx in veh: continue
        prev = None
        for r in L:
            td = r['T'] - delay
            st = TR.at(hx, td)
            if st is not None:
                e = math.hypot(r['x'] - st['x'], r['z'] - st['z'])
                if st['ground']:
                    k = 'ground_moving' if np.isfinite(st['gs']) and st['gs'] >= 1.5 else 'ground_still'
                    if r['gate']: k += '_at_gate'
                else:
                    k = 'air_lt10nm' if math.hypot(st['x'], st['z']) < 10 * NM else 'air_far'
                perr[k].append(e); perr[k + ('_extrap' if r['extrap'] and r['extrap'] > 0.05 else '_interp')].append(e)
                now = TR.at(hx, r['T'])
                if now is not None: lag[k].append(math.hypot(r['x'] - now['x'], r['z'] - now['z']))
                if st['ground'] and in_airport(st['x'], st['z']) and np.isfinite(st['hdg']):
                    dh = abs(float(wrap180(r['hdg'] - st['hdg']))); herr.append(dh)
                tp, trw = TR.phase(hx, td, st)
                ag = APP_GROUP.get(r['phase'], r['phase'])
                if tp and (in_airport(st['x'], st['z']) or math.hypot(st['x'], st['z']) < 30000):
                    conf[(tp, ag)] += 1
                    if tp in ('final', 'rollout', 'takeoff') and ag == tp and r['rwy']:
                        if r['rwy'] != trw: runway_bad.append((utc(td), hx, r['flight'], tp, trw, r['rwy']))
                        else: runway_ok += 1
                    if tp in ('rollout', 'takeoff', 'final', 'departure'):
                        phase_windows[(hx, tp)][ag] += 1
                # vertical: really on the runway?
                E = TR.ev.get(hx) or {}
                on_rwy_truth = any((e.get('td_t') or e['t_flag']) <= td < (e.get('t_exit') or e['t_flag'] + 30) for e in E.get('arrivals', [])) or \
                               any((e.get('t_flag')) <= td < (e.get('t_lo') or e['t_flag'] + 15) for e in E.get('departures', []))
                if on_rwy_truth:
                    vert_gnd.append(r['y'] - GROUND_Y); gear_up_gnd.append(r['gear'] < 0.5)
                elif not st['ground'] and np.isfinite(st['geom']):
                    msl = st['geom'] * FT + GEOID_M
                    agl_truth = msl - (GROUND_Y + 5.0)      # antenna ~5 m above the wheels (INFERRED typical)
                    if agl_truth < 1500 * FT: vair.append((agl_truth, r['y'] - GROUND_Y))
            if prev is not None:
                dt = r['T'] - prev['T']
                if 0 < dt <= 1.0:
                    d = math.hypot(r['x'] - prev['x'], r['z'] - prev['z']); v = d / dt
                    tv = st['gs'] * KT if st is not None and np.isfinite(st['gs']) else (r['gs'] or 0)
                    if v > 1.5 * tv + 5 and d > 3:
                        jumps.append(dict(t=utc(td), hex=hx, flight=r['flight'], phase=r['phase'], d=round(d, 1), v=round(v, 1), truth_gs=round(tv, 1), ground=r['ground']))
                    if st is not None and st['ground'] and np.isfinite(st['gs']) and st['gs'] < 0.5 and d / dt > 1.0:
                        slides.append(dict(t=utc(td), hex=hx, flight=r['flight'], phase=r['phase'], gate=r['gate'], v=round(v, 2)))
                    if r['ground'] and prev['ground'] and abs(float(wrap180(r['hdg'] - prev['hdg']))) > 60 and (st is None or not np.isfinite(st['gs']) or st['gs'] < 25):
                        hflip.append(dict(t=utc(td), hex=hx, flight=r['flight'], phase=r['phase'], dh=round(float(wrap180(r['hdg'] - prev['hdg'])), 0), gate=r['gate']))
            prev = r
    R['position_error_m'] = {k: pct(v) for k, v in sorted(perr.items())}
    R['lag_behind_real_time_m'] = {k: pct(v) for k, v in sorted(lag.items())}
    R['ground_heading_error_deg'] = pct(herr)
    sfo_hex = {a['hex'] for a in events['aircraft'] if a['sfo_ground']}
    R['heading_jumps_gt60deg_in_0p5s'] = dict(n=len(hflip), n_sfo=sum(1 for r in hflip if r['hex'] in sfo_hex and r['phase'] != 'ground-other'),
                                             by_track=Counter((r['flight'] or r['hex'], r['phase']) for r in hflip if r['phase'] != 'ground-other').most_common(12), rows=hflip[:30])
    R['jumps'] = dict(n=len(jumps), n_sfo=sum(1 for r in jumps if r['hex'] in sfo_hex and r['phase'] != 'ground-other'),
                      by_track=Counter((r['flight'] or r['hex'], r['phase']) for r in jumps if r['phase'] != 'ground-other').most_common(12), rows=jumps[:40])
    sl = Counter((s['hex'], s['flight'], s['phase'], s['gate']) for s in slides)
    R['moving_while_truth_still'] = dict(rows=len(slides), by_track=[dict(hex=k[0], flight=k[1], phase=k[2], gate=k[3], seconds=v * (meta['log'] if meta else 0.5)) for k, v in sl.most_common(20)])
    R['on_runway_truth_displayed_height_m'] = pct(vert_gnd, (10, 50, 90, 99)) | {'frac_gt_1m': round(float(np.mean(np.array(vert_gnd) > 1)), 3) if vert_gnd else None,
                                                                              'frac_gear_retracted': round(float(np.mean(gear_up_gnd)), 3) if gear_up_gnd else None}
    va = np.array(vair) if vair else np.zeros((0, 2))
    R['airborne_below_1500ft_height_error_m'] = {b: pct(va[(va[:, 0] >= lo) & (va[:, 0] < hi), 1] - va[(va[:, 0] >= lo) & (va[:, 0] < hi), 0]) for b, lo, hi in
                                                (('0-15m', -99, 15), ('15-60m', 15, 60), ('60-150m', 60, 150), ('150-460m', 150, 460))}
    groups = ['final', 'approach', 'rollout', 'takeoff', 'departure', 'taxi', 'pushback', 'still', 'air-other', 'ground-other']
    step = meta['log'] if meta else 0.5
    R['phase_confusion_seconds'] = {tp: {ag: round(n * step) for (t2, ag), n in conf.items() if t2 == tp} for tp in groups if any(t2 == tp for (t2, _) in conf)}
    tot = sum(conf.values()); ok = sum(n for (tp, ag), n in conf.items() if tp == ag)
    R['phase_agreement'] = round(ok / tot, 3) if tot else None
    R['phase_windows'] = {f'{k[0]}:{k[1]}': {a: round(n * step, 1) for a, n in v.items()} for k, v in sorted(phase_windows.items())}
    R['runway'] = dict(ok_rows=runway_ok, wrong_rows=len(runway_bad), wrong=runway_bad[:20])
    # ------------------------------------------------------------------ stands
    gt = {}
    gp = os.path.join(OUT, 'gatecheck_every120.json')
    if os.path.exists(gp):
        for r in json.load(open(gp))['rows']:
            if r.get('published_stand') or r.get('verdict', '').startswith('occupancy'):
                gt.setdefault(r['hex'], []).append(r)
    stand_rows = []
    for a in events['aircraft']:
        if a['vehicle']: continue
        for s in a['stops']:
            if s['dur'] < 120 or s['runway']: continue
            L = [r for r in by.get(a['hex'], []) if s['t0'] + 30 <= r['T'] - delay <= s['t1']]
            if not L: continue
            g = Counter(r['gate'] for r in L).most_common()
            sfo = None
            for q in gt.get(a['hex'], []):
                if s['t0'] - 60 <= q['T'] <= s['t1'] + 60:
                    sfo = q.get('published_stand') or q.get('published'); break
            stand_rows.append(dict(hex=a['hex'], flight=a['flight'] or a['reg'], type=a['icao'], t0=utc(s['t0']), dur=s['dur'], app_gate=g[0][0], app_gate_frac=round(g[0][1] / len(L), 2),
                                   app_phase=Counter(r['phase'] for r in L).most_common(1)[0][0], nearest=s['stands'][0]['stand'], nearest_lat=s['stands'][0]['lat'], nearest_along=s['stands'][0]['along'],
                                   sfo=sfo if isinstance(sfo, str) else (str(sfo)[:60] if sfo else None), jit_p95=s['jit_p95'], hdg_reported=s['hdg'] is not None,
                                   hdg_app=round(float(np.median([r['hdg'] % 360 for r in L])), 1), hdg_truth=s['hdg']))
    R['stands'] = stand_rows
    # gate occupancy events
    if tail:
        ge = tail.get('gateEvents', [])
        R['gate_events'] = dict(n=len(ge), occupy=sum(1 for e in ge if e[2]), release=sum(1 for e in ge if not e[2]), per_gate=Counter(e[1] for e in ge).most_common(10))
        R['removed_tracks'] = tail.get('removed', [])[:40]
    # ------------------------------------------------------------------ surface plausibility
    off = defaultdict(float); bld = defaultdict(float); ovl = defaultdict(float); ovl_pairs = Counter()
    phys = []
    for r in rows:
        if r['hex'] in veh or not in_airport(r['x'], r['z']): continue
        if r['ground'] and r['physOff']: phys.append(r['physOff'])
        if r['offPave']: off[(r['hex'], r['flight'], r['phase'], r['gate'])] += step
        if r['inBld']: bld[(r['hex'], r['flight'], r['phase'], r['gate'])] += step
        for o2 in r['overlaps'] or []:
            ovl[(r['hex'], r['flight'], r['phase'])] += step; ovl_pairs[tuple(sorted((r['hex'], o2)))] += step / 2
    R['off_pavement_seconds'] = dict(total=round(sum(off.values())), tracks=len({k[0] for k in off}), top=[dict(hex=k[0], flight=k[1], phase=k[2], gate=k[3], s=round(v)) for k, v in sorted(off.items(), key=lambda kv: -kv[1])[:15]])
    R['in_building_seconds'] = dict(total=round(sum(bld.values())), top=[dict(hex=k[0], flight=k[1], phase=k[2], gate=k[3], s=round(v)) for k, v in sorted(bld.items(), key=lambda kv: -kv[1])[:10]])
    R['ground_physics_displacement_m'] = pct(phys)
    R['overlap_seconds'] = dict(pairs=len(ovl_pairs), total=round(sum(ovl_pairs.values())), top=[dict(pair=k, s=round(v)) for k, v in ovl_pairs.most_common(15)])
    if masks is not None:
        # raw reports (antenna point) off pavement, ground reports inside the airport, by speed
        rawoff = Counter(); rawn = Counter()
        for hx, L in tracks.items():
            if hx in veh: continue
            for r in L:
                if not r['ground'] or not in_airport(r['x'], r['z']): continue
                i, j = int(r['x'] + 2700), int(r['z'] + 2350)
                if 0 <= i < masks.shape[1] and 0 <= j < masks.shape[0]:
                    k = 'moving' if (r.get('gs') or 0) >= 1.5 else 'still'
                    rawn[k] += 1; rawoff[k] += int(not (masks[j, i] & 1))
        R['raw_reports_off_pavement'] = {k: dict(n=rawn[k], off=rawoff[k], frac=round(rawoff[k] / rawn[k], 4)) for k in rawn}
    # ------------------------------------------------------------------ event timing: when the app's phase switched vs truth
    tim = []
    first = defaultdict(dict)
    for e in phase_ev:
        first[e['hex']].setdefault(e['phase'], []).append(e['t'])
    for a in events['aircraft']:
        for e in a['arrivals']:
            ts = [t for t in first.get(a['hex'], {}).get('landing', []) if abs(t - delay - (e.get('td_t') or e['t_flag'])) < 120]
            tim.append(dict(kind='arr', flight=a['flight'], truth_td=utc(e['td_t']) if e.get('td_t') else None, app_landing_display=utc(ts[0] - delay) if ts else None,
                            app_minus_truth_s=round(ts[0] - delay - e['td_t'], 1) if ts and e.get('td_t') else None, app_landing_wall=utc(ts[0]) if ts else None))
        for e in a['departures']:
            ts = [t for t in first.get(a['hex'], {}).get('departure', []) if abs(t - delay - e['t_flag']) < 120]
            tt = [t for t in first.get(a['hex'], {}).get('takeoff', []) if abs(t - delay - (e.get('t_roll') or e['t_flag'])) < 180]
            tim.append(dict(kind='dep', flight=a['flight'], truth_lo=utc(e['t_lo']) if e.get('t_lo') else None, app_departure_display=utc(ts[0] - delay) if ts else None,
                            app_minus_truth_s=round(ts[0] - delay - e['t_lo'], 1) if ts and e.get('t_lo') else None,
                            app_takeoff_start_minus_truth_roll_s=round(tt[0] - delay - e['t_roll'], 1) if tt and e.get('t_roll') else None))
    R['event_timing'] = tim
    js = json.dumps(R, indent=1, default=str)
    if o.json: open(o.json, 'w').write(js)
    print(js[:60000])


if __name__ == '__main__':
    main()
