#!/usr/bin/env python3
"""Score the traffic engine's replay (tools/live/replay_engine.mjs log) against what really happened.

Truth (all derived from the same recording, tools/live/replay_events.py; see its header for the definitions):
  * phase at display time td = T - delay: final / approach / rollout / takeoff / departure / taxi / pushback / still
    (replay_audit.Truth.phase), for aircraft that used SFO in the window;
  * runway and time of every touchdown (deceleration-onset estimate) and liftoff (sustained climb estimate);
  * go-arounds; displayed position vs the merged reports interpolated at td.
SFO's own stand allocation (flysfo.com AODB windows, as the relay's /api/gates served them at T: gates.jsonl.gz from
tools/live/build_stream.py) for every aircraft the engine shows parked at a stand, and for aircraft SFO had on a stand
while the engine showed them parked without one. With --no-plan runs this is an independent check (the engine never saw
the plan); with the plan it checks the plan is applied correctly.
Kinematics, teleports, overlaps, off-pavement and in-building frames come from the harness summary line.
Usage: REPLAY_FROM=... REPLAY_UNTIL=... python3 tools/live/replay_score.py refs/cache/replay_day/engine.jsonl.gz
       [--events refs/cache/replay_day/events.json] [--gates refs/cache/replay_day/gates.jsonl.gz] [--json out.json]
"""
import argparse, bisect, gzip, json, math, os, re, sys
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import NM, RWY, build_reports, is_vehicle, rwy_coords, utc, load_json
from replay_events import in_airport
from replay_audit import Truth

COLS = ['T', 'hex', 'phase', 'mphase', 'rwy', 'gate', 'x', 'y', 'z', 'hdg', 'ground', 'gs', 'flight', 'icao', 'delay', 'gateSrc', 'veh', 'stale', 'pitch', 'gear']
APP_GROUP = {'final': 'final', 'approach': 'approach', 'goaround': 'air-other', 'landing': 'rollout', 'takeoff': 'takeoff', 'lineup': 'still',
             'departure': 'departure', 'taxi': 'taxi', 'pushback': 'pushback', 'holding': 'still', 'gate': 'still', 'parked': 'still',
             'enroute': 'air-other', 'ground-other': 'ground-other', 'new': 'new', 'vehicle': 'vehicle'}
GROUPS = ['final', 'approach', 'rollout', 'takeoff', 'departure', 'taxi', 'pushback', 'still', 'air-other', 'ground-other']


def pct(a, qs=(50, 90, 99)):
    a = np.asarray([v for v in a if v is not None and np.isfinite(v)], float)
    if not len(a): return {'n': 0}
    return {**{f'p{q}': round(float(np.percentile(a, q)), 2) for q in qs}, 'n': int(len(a)), 'max': round(float(a.max()), 2)}


def norm_cs(c):
    m = re.match(r'^([A-Z]{3})0*(\d+[A-Z]?)$', (c or '').strip().upper())
    return m.group(1) + m.group(2) if m else (c or '').strip().upper()


def stand_names():
    S = load_json('data/sfo_stands.json'); out = {}
    for s in S['stands']:
        names = {s['name'], *(s.get('alias') or [])}
        for k in ('sfo', 'sfoName', 'sfoNames', 'alt', 'alts', 'alternates', 'mars', 'names'):
            v = s.get(k)
            if isinstance(v, list): names |= {str(q) for q in v}
            elif isinstance(v, str): names.add(v)
        out[s['name']] = {n.upper() for n in names}
    for r in S.get('remote', []): out[r['name']] = {r['name'].upper()}
    return out


def base(n):
    m = re.match(r'^([A-G]\d+)', n or ''); return m.group(1) if m else n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('log'); ap.add_argument('--events'); ap.add_argument('--gates'); ap.add_argument('--json')
    o = ap.parse_args()
    d = os.path.dirname(os.path.abspath(o.log))
    ev_path = o.events or os.path.join(d, 'events.json'); g_path = o.gates or os.path.join(d, 'gates.jsonl.gz')
    rows, summ, meta = [], None, None
    with gzip.open(o.log, 'rt') as f:
        for l in f:
            j = json.loads(l)
            if isinstance(j, list): rows.append(dict(zip(COLS, j)))
            elif 'meta' in j: meta = j['meta']
            elif 'summary' in j: summ = j['summary']
    tracks, _ = build_reports(); events = json.load(open(ev_path))
    # truth hygiene: an arrival with neither threshold crossing nor touchdown estimate, or a departure with neither
    # liftoff nor take-off roll, is an artefact of the offline extractor (e.g. a spurious 'airborne' flag while taxiing
    # at 16 kt: UAL1469 16:26Z) -> not used as truth
    for a in events['aircraft']:
        a['arrivals'] = [e for e in a['arrivals'] if e.get('td_t') or e.get('t_thr')]
        a['departures'] = [e for e in a['departures'] if e.get('t_lo') or e.get('roll_m')]
    TR = Truth(tracks, events)
    t0, t1 = meta['t0'], meta['t1']
    by_ev = {a['hex']: a for a in events['aircraft']}
    sfo = {a['hex'] for a in events['aircraft'] if (a['arrivals'] or a['departures'] or a['sfo_ground']) and not a.get('vehicle')}
    R = {'log': os.path.basename(o.log), 'plan_used': meta.get('plan'), 'window_utc': [utc(t0), utc(t1)], 'rows': len(rows)}
    # ------------------------------------------------------------------ phase agreement + position error at display time
    conf = Counter(); perr = defaultdict(list); lagm = defaultdict(list); worst = {}
    for r in rows:
        if r['veh'] or r['hex'] not in sfo: continue
        td = r['T'] - r['delay'] / 1000.0
        st = TR.at(r['hex'], td)
        if st is None: continue
        tp, _ = TR.phase(r['hex'], td, st)
        if tp and (in_airport(st['x'], st['z']) or math.hypot(st['x'], st['z']) < 30000):
            conf[(tp, APP_GROUP.get(r['phase'], r['phase']))] += 1
        e = math.hypot(r['x'] - st['x'], r['z'] - st['z'])
        k = ('ground_moving' if np.isfinite(st['gs']) and st['gs'] >= 1.5 else 'ground_still') if st['ground'] else ('air_lt10nm' if math.hypot(st['x'], st['z']) < 10 * NM else 'air_far')
        perr[k].append(e)
        if e > worst.get((r['hex'], k), (0,))[0]: worst[(r['hex'], k)] = (e, r['flight'], utc(r['T']), r['phase'], r['mphase'])
        now = TR.at(r['hex'], r['T'])
        if now is not None: lagm[k].append(math.hypot(r['x'] - now['x'], r['z'] - now['z']))
    tot = sum(conf.values()); ok = sum(n for (p, q), n in conf.items() if p == q)
    R['phase'] = {'rows_scored': tot, 'agreement': round(ok / max(tot, 1), 3),
                  'per_truth_phase': {p: round(conf[(p, p)] / max(1, sum(n for (a, _), n in conf.items() if a == p)), 3) for p in GROUPS if any(a == p for (a, _) in conf)},
                  'confusion_rows': {p: dict(sorted({q: n for (a, q), n in conf.items() if a == p}.items(), key=lambda kv: -kv[1])) for p in GROUPS if any(a == p for (a, _) in conf)}}
    R['position_error_m'] = {k: pct(v) for k, v in perr.items()}
    R['behind_realtime_m'] = {k: pct(v, (50,)) for k, v in lagm.items()}
    R['position_error_worst'] = [(k[1], round(v[0]), *v[1:]) for k, v in sorted(worst.items(), key=lambda kv: -kv[1][0])[:25]]
    R['delay_ms'] = pct([r['delay'] for r in rows], (5, 50, 95))
    # ------------------------------------------------------------------ runway events
    eng = defaultdict(list)
    for e in summ['events']: eng[e['hex']].append(e)
    arr_rows, dep_rows, ga = [], [], []
    for hx, A in by_ev.items():
        if A.get('vehicle'): continue
        for a in A['arrivals']:
            tt = a.get('td_t')
            if tt is None or not (t0 + 60 < tt < t1 - 30) or a.get('c_med', 999) > 150: continue
            cands = [e for e in eng.get(hx, []) if e['kind'] == 'touchdown' and abs(e['t'] / 1000 - tt) < 90]
            e = min(cands, key=lambda q: abs(q['t'] / 1000 - tt)) if cands else None
            arr_rows.append({'flight': A['flight'], 'truth_rwy': a['rwy'], 'truth_td': utc(tt), 'truth_td_a': a.get('td_a'), 'rwy': e and e['rwy'], 'how': e and e.get('how'),
                             'dt_s': round(e['t'] / 1000 - tt, 1) if e else None, 'td_a': e and e.get('a'), 'ok': bool(e and e['rwy'] == a['rwy'])})
        for dd in A['departures']:
            tt = dd.get('t_lo')
            if tt is None or not (t0 + 60 < tt < t1 - 30) or (dd.get('lo_after_flag_s') or 0) < 1 or not dd.get('roll_m') or dd['roll_m'] < 300: continue
            cands = [e for e in eng.get(hx, []) if e['kind'] == 'liftoff' and abs(e['t'] / 1000 - tt) < 90]
            e = min(cands, key=lambda q: abs(q['t'] / 1000 - tt)) if cands else None
            dep_rows.append({'flight': A['flight'], 'truth_rwy': dd['rwy'], 'truth_lo': utc(tt), 'rwy': e and e['rwy'], 'dt_s': round(e['t'] / 1000 - tt, 1) if e else None, 'ok': bool(e and e['rwy'] == dd['rwy'])})
        for g in A['go_arounds']: ga.append({'flight': A['flight'], 'truth': g})
    eng_ga = [e for L in eng.values() for e in L if e['kind'] == 'go-around']
    # displayed touchdown: first grounded row after final, along-runway distance vs the truth estimate
    disp_td = []
    rows_by = defaultdict(list)
    for r in rows: rows_by[r['hex']].append(r)
    for a in arr_rows:
        pass
    for hx, A in by_ev.items():
        for a in A['arrivals']:
            if a.get('td_a') is None or a.get('td_t') is None: continue
            L = [r for r in rows_by.get(hx, []) if abs(r['T'] - r['delay'] / 1000 - a['td_t']) < 60]
            prev = None
            for r in L:   # wheels on: the displayed wheel height reaches the runway (< 0.3 m)
                if prev and prev['y'] - 3.0 >= 0.3 and r['y'] - 3.0 < 0.3 and r['phase'] in ('landing', 'final', 'taxi'):
                    aa, c = rwy_coords(a['rwy'], r['x'], r['z']); disp_td.append({'flight': A['flight'], 'disp_a': round(float(aa)), 'truth_a': a['td_a'], 'err_m': round(float(aa) - a['td_a'])}); break
                prev = r
    R['arrivals'] = {'n': len(arr_rows), 'runway_correct': sum(a['ok'] for a in arr_rows), 'detected': sum(a['rwy'] is not None for a in arr_rows),
                     'touchdown_dt_s': pct([a['dt_s'] for a in arr_rows if a['dt_s'] is not None], (10, 50, 90)), 'rows': arr_rows,
                     'displayed_touchdown_point_err_m': pct([abs(q['err_m']) for q in disp_td], (50, 90)), 'displayed_touchdowns': disp_td}
    R['departures'] = {'n': len(dep_rows), 'runway_correct': sum(a['ok'] for a in dep_rows), 'detected': sum(a['rwy'] is not None for a in dep_rows),
                       'liftoff_dt_s': pct([a['dt_s'] for a in dep_rows if a['dt_s'] is not None], (10, 50, 90)), 'rows': dep_rows}
    R['go_arounds'] = {'truth': ga, 'engine': [{'flight': e['flight'], 't': utc(e['t'] / 1000), 'rwy': e.get('rwy')} for e in eng_ga]}
    R['runway_changes'] = [{'flight': e['flight'], 't': utc(e['t'] / 1000), 'from': e.get('from'), 'to': e.get('rwy')} for L in eng.values() for e in L if e['kind'] == 'runway-change']
    kinds = Counter(e['kind'] for L in eng.values() for e in L); R['engine_events'] = dict(kinds)
    # ------------------------------------------------------------------ stands vs SFO's allocation
    plans = []
    if os.path.exists(g_path):
        with gzip.open(g_path, 'rt') as f:
            for l in f: plans.append(json.loads(l))
    PT = [p['T'] for p in plans]
    names = stand_names()
    visits = {}
    for r in rows:
        if r['veh'] or r['phase'] not in ('gate', 'parked') or not r['flight']: continue
        i = bisect.bisect_right(PT, r['T']) - 1
        if i < 0: continue
        P = plans[i]['gates']; cs = norm_cs(r['flight']); cs = (P['aliases'].get(cs) or {}).get('to') or cs
        s = (P['byCallsign'].get(cs) or {}).get('stand')
        sfo_n = s['name'].upper() if s and s['from'] - 60 <= r['T'] <= s['to'] + 60 else None
        key = (r['hex'], sfo_n or '-', r['gate'] or '-')
        v = visits.setdefault(key, {'flight': r['flight'], 'sfo': sfo_n, 'ours': r['gate'], 'src': r['gateSrc'], 'rows': 0})
        v['rows'] += 1
    verdict = Counter(); vis = []
    for (hx, sn, og), v in visits.items():
        if v['rows'] < 20: continue           # >= 10 s parked
        if not v['sfo']: vd = 'no-sfo-window'
        elif not v['ours']: vd = 'unassigned'
        elif v['sfo'] in names.get(v['ours'], {v['ours']}) or base(v['sfo']) in names.get(v['ours'], set()): vd = 'agree'
        else: vd = 'DISAGREE'
        verdict[vd] += 1; vis.append({**v, 'verdict': vd})
    R['stands_vs_sfo'] = {'visits': dict(verdict), 'agree_rate_of_comparable': round(verdict['agree'] / max(1, verdict['agree'] + verdict['DISAGREE']), 3),
                          'list': sorted(vis, key=lambda q: q['verdict'])}
    # ------------------------------------------------------------------ physical plausibility (harness)
    s = summ
    R['physical'] = {'teleports': s['teleports'], 'gap_reacquisitions': s.get('gapResets'), 'teleports_who': s['teleWho'][:10],
                     'kinematics': s['kin'], 'thresholds': s['thresholds'], 'exceed_frames': s['exceed'], 'frames': s['frames'], 'dt': s['dt'],
                     'overlap_frames': s['overlapFrames'], 'overlap_pairs_s': s['overlapPairs'][:10],
                     'off_pavement_frames': {'aircraft_frames': s['offPave']['frames'], 'gear_off_mask': s['offPave']['maskOnly'], 'gear_off_mask_or_osm': s['offPave']['union'], 'who': s['offPave']['who'][:8]},
                     'in_building_frames': s['inBld'], 'counters': s['counters']}
    out = json.dumps(R, indent=1, default=str)
    if o.json: open(o.json, 'w').write(out)
    short = {k: v for k, v in R.items() if k not in ('stands_vs_sfo',)}
    short['arrivals'] = {k: v for k, v in R['arrivals'].items() if k not in ('rows', 'displayed_touchdowns')}
    short['departures'] = {k: v for k, v in R['departures'].items() if k != 'rows'}
    short['stands_vs_sfo'] = {k: v for k, v in R['stands_vs_sfo'].items() if k != 'list'}
    short['physical'] = {k: v for k, v in R['physical'].items() if k not in ('kinematics',)}
    print(json.dumps(short, indent=1, default=str))


if __name__ == '__main__':
    main()
