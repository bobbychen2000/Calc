#!/usr/bin/env python3
"""Collect the traffic-audit outputs (refs/cache/replay/*.json) into markdown tables: refs/cache/replay/summary.md.
The numbers quoted in docs/research/traffic_audit.md come from this file (re-run tools/live/replay_all.sh first).
Taxi routes are named with OpenStreetMap aeroway=taxiway/taxilane refs (refs/cache/osm/ksfo_osm_parsed.json, ODbL,
(c) OpenStreetMap contributors) because they cover the ramp taxilanes that the SFO Museum polygons lack (section 6.5).
Usage: python3 tools/live/replay_report.py
"""
import json, math, os, sys
from collections import Counter
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import OUT, ROOT, RWY, build_reports, ll2w, utc, on_runway, is_vehicle
from replay_events import in_airport

J = lambda n: json.load(open(os.path.join(OUT, n))) if os.path.exists(os.path.join(OUT, n)) else None
f0 = lambda v, d=0: '–' if v is None or (isinstance(v, float) and not math.isfinite(v)) else (f'{v:.{d}f}' if isinstance(v, (int, float)) else str(v))


def osm_router():
    p = os.path.join(ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')
    if not os.path.exists(p): return None
    from scipy.spatial import cKDTree
    O = json.load(open(p)); pts = []; refs = []
    for w in O['taxiways']:
        P = np.array([ll2w(la, lo) for la, lo in w['pts']], float)
        for a, b in zip(P[:-1], P[1:]):
            n = max(1, int(np.hypot(*(b - a)) / 2.0))
            for u in np.linspace(0, 1, n + 1): pts.append(a + (b - a) * u); refs.append(w.get('ref') or w['tags'].get('ref') or ('taxilane' if w['tags'].get('aeroway') == 'taxilane' else 'unnamed'))
    kd = cKDTree(np.array(pts))
    def route(L):
        out = []
        for r in L:
            if not r['ground'] or not isinstance(r.get('gs'), (int, float)) or r['gs'] < 3: continue
            rp = on_runway(r['x'], r['z'])
            if rp: name = 'RWY ' + rp
            else:
                d, i = kd.query([r['x'], r['z']]); name = refs[i] if d < 12 else 'ramp'
            out.append(name)
        comp = []
        for n in out:
            if comp and comp[-1][0] == n: comp[-1][1] += 1
            else: comp.append([n, 1])
        comp = [c for c in comp if c[1] >= 3]           # drop 1-2 report blips at junctions
        res = []
        for n, k in comp:
            if not res or res[-1] != n: res.append(n)
        return ' > '.join(res)
    return route


def main():
    E = J('events.json'); D = J('datachar.json'); M = J('model_eval.json'); LAT = J('latency.json'); G = J('gatecheck_every120.json')
    tracks, meta = build_reports()
    route = osm_router()
    md = []
    P = meta['providers']; t0 = min(p['t0'] for p in P.values()); t1 = max(p['t1'] for p in P.values())
    md.append(f'Recording: {utc(t0)}–{utc(t1)} UTC 24 Sep 2026 ({(t1 - t0) / 60:.0f} min); adsb.fi {P["adsbfi"]["snapshots"]} snapshots, adsb.lol {P["adsblol"]["snapshots"]} snapshots.\n')
    # ---- arrivals
    md.append('### Arrivals\n')
    md.append('| thr (UTC) | flight | type | rwy | median \\|c\\| m (next rwy) | gs thr kt | height at thr ft MSL (geom) | est. touchdown m past thr / gs kt | decel before→after kt/s | "ground" flag: +s / +m / gs kt | exit | exit a m / gs kt | ROT s | taxi-in route (OSM refs) | stopped at |')
    md.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for a in E['aircraft']:
        for e in a['arrivals']:
            L = [r for r in tracks[a['hex']] if r['pt'] >= (e.get('t_exit') or e['t_flag'])]
            end = next((s for s in a['stops'] if s['t0'] >= (e.get('t_exit') or e['t_flag']) and s['dur'] >= 60 and not s['runway']), None)
            if end: L = [r for r in L if r['pt'] <= end['t0']]
            rt = route(L) if route else ''
            stand = end['stands'][0] if end else None
            md.append(f"| {utc(e.get('t_thr') or e['t_flag'])} | {a['flight'] or a['reg']} | {a['icao']} | {e['rwy']} | {f0(e['c_med'],1)} ({e['runner_up'][0][1]} {f0(e['runner_up'][0][0])}) | {f0(e.get('gs_thr'))} | {f0(e.get('alt_thr_geom_msl'))} | {f0(e.get('td_a'))} / {f0(e.get('td_gs'))} | {e.get('td_decel_before')}→{e.get('td_decel_after')} | +{f0(e.get('flag_lag_s'),1)} / +{f0(e.get('flag_lag_m'))} / {f0(e['gs_flag'])} | {'/'.join(e.get('exit_twy') or []) or '–'} | {f0(e.get('a_exit'))} / {f0(e.get('gs_exit'))} | {f0(e.get('rot_s'))} | {rt} | {('%s (%.0f m, %s)' % (stand['stand'], abs(stand['lat']) + abs(stand['along']), 'still' if end['last'] else '%.0f s' % end['dur'])) if stand else '–'} |")
    # ---- departures
    md.append('\n### Departures\n')
    md.append('| "air" flag (UTC) | flight | type | rwy | median \\|c\\| m | lined up from | roll start m from rwy end (rolling?) | flag: m / gs kt / alt_baro ft | est. liftoff: m / gs kt | flag→liftoff s / m | roll s / m | taxi-out route (OSM refs) |')
    md.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for a in E['aircraft']:
        for e in a['departures']:
            pb = [p for p in a['pushbacks'] if p['t0'] < e['t_flag']]
            ts = pb[-1]['t0'] if pb else e['t_flag'] - 1200
            L = [r for r in tracks[a['hex']] if ts <= r['pt'] <= (e.get('t_lineup') or e['t_flag'])]
            rt = route(L) if route else ''
            md.append(f"| {utc(e['t_flag'])} | {a['flight'] or a['reg']} | {a['icao']} | {e['rwy']} | {f0(e['c_med'],1)} | {'/'.join(e.get('lineup_twy') or []) or '–'} | {f0(e.get('a_roll'))} ({'yes' if e.get('rolling_takeoff') else 'no'}) | {f0(e['a_flag'])} / {f0(e['gs_flag'])} / {f0(e.get('alt_flag_baro'))} | {f0(e.get('a_lo'))} / {f0(e.get('gs_lo'))} | {f0(e.get('lo_after_flag_s'),1)} / {f0(e.get('lo_after_flag_m'))} | {f0(e.get('roll_s'))} / {f0(e.get('roll_m'))} | {rt} |")
    ga = [(a, g) for a in E['aircraft'] for g in a['go_arounds']]
    md.append(f'\nGo-arounds / missed approaches detected: {len(ga)}' + ''.join(f"\n- {utc(g['t_low'])} {a['flight']} {g}" for a, g in ga))
    # ---- parking
    md.append('\n### Where aircraft stopped (stops >= 120 s off the runways; nearest stand by the app\'s antenna model)\n')
    gt = {}
    for r in (G or {}).get('rows', []):
        gt.setdefault(r['hex'], []).append(r)
    md.append('| flight | reg | type | from (UTC) | dur s | jitter p95 m | reported hdg | nearest stand (lat/along m, hdg diff) | SFO AODB stand (flysfo) | verdict (gatecheck) |')
    md.append('|---|---|---|---|---|---|---|---|---|---|')
    for a in E['aircraft']:
        if a['vehicle']: continue
        for s in a['stops']:
            if s['dur'] < 120 or s['runway']: continue
            c = s['stands'][0]
            q = next((r for r in gt.get(a['hex'], []) if s['t0'] - 60 <= r['T'] <= s['t1'] + 60), None)
            md.append(f"| {a['flight'] or '–'} | {a['reg']} | {a['icao']} | {utc(s['t0'])} | {s['dur']:.0f} | {s['jit_p95']} | {f0(s['hdg'])} | {c['stand']} ({c['lat']}/{c['along']}, {f0(c['dhdg'])}) | {(q.get('published_stand') or '–') if q else '–'} | {q['verdict'] if q else '–'} |")
    pbs = [(a, p) for a in E['aircraft'] for p in a['pushbacks']]
    md.append(f'\nPush-backs detected: {len(pbs)}\n')
    md.append('| t (UTC) | flight | reported hdg | motion dir | gs kt | from (nearest stand, score) |')
    md.append('|---|---|---|---|---|---|')
    for a, p in pbs: md.append(f"| {utc(p['t0'])} | {a['flight'] or a['reg']} | {p['hdg']:.1f} | {p['move_dir']:.0f} | {p['gs']} | {p['stands'][0]['stand']} ({p['stands'][0]['score']}) |")
    # ---- app replay
    md.append('\n### App logic replayed (node, js/live/traffic.js + ground.js unmodified)\n')
    md.append('| variant | polls | delay s | pos err p50/p99 m: air<10NM, gnd moving, gnd still | lag behind real time p50 m: air<10NM / gnd moving | on-runway rows shown >1 m high | gear up on runway | phase agreement | wrong-runway rows | jumps (SFO) | heading >60° flips/0.5 s (SFO) | vehicles shown as aircraft | off-pavement s (tracks) | overlap s |')
    md.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for v in ('relay5_noroutes', 'relay5', 'relay5_paved', 'relay1', 'lol7'):
        A = J(f'audit_app_{v}.json') or J(f'audit_{v}.json')
        if not A: continue
        pe = A['position_error_m']; lg = A['lag_behind_real_time_m']; og = A['on_runway_truth_displayed_height_m']
        g = lambda k, q: pe.get(k, {}).get(q)
        md.append(f"| {v} | {os.path.basename(A['meta']['polls'])} | {A['meta']['delay'] / 1000:g} | {f0(g('air_lt10nm','p50'),1)}/{f0(g('air_lt10nm','p99'))}, {f0(g('ground_moving','p50'),1)}/{f0(g('ground_moving','p99'))}, {f0(g('ground_still','p50'),1)}/{f0(g('ground_still','p99'))} | {f0(lg.get('air_lt10nm',{}).get('p50'))} / {f0(lg.get('ground_moving',{}).get('p50'))} | {og.get('frac_gt_1m')} | {og.get('frac_gear_retracted')} | {A['phase_agreement']} | {A['runway']['wrong_rows']} | {A['jumps'].get('n_sfo', A['jumps']['n'])} | {A['heading_jumps_gt60deg_in_0p5s'].get('n_sfo', A['heading_jumps_gt60deg_in_0p5s']['n'])} | {len(A['vehicle_tracks_in_app'])} | {A['off_pavement_seconds']['total']} ({A['off_pavement_seconds']['tracks']}) | {A['overlap_seconds']['total']} |")
    A = J('audit_app_relay5_noroutes.json') or J('audit_relay5_noroutes.json')
    if A:
        md.append('\nPhase confusion (relay5, seconds of display time; rows = truth, columns = app):\n')
        cols = ['final', 'approach', 'rollout', 'takeoff', 'departure', 'taxi', 'pushback', 'still', 'air-other', 'ground-other']
        md.append('| truth \\ app | ' + ' | '.join(cols) + ' |'); md.append('|---' * (len(cols) + 1) + '|')
        for tp, row in A['phase_confusion_seconds'].items():
            md.append(f'| {tp} | ' + ' | '.join(str(row.get(c, '')) for c in cols) + ' |')
        md.append('\nEvent timing (relay5): app phase switch at display time minus truth event time\n')
        md.append('| kind | flight | truth | app − truth s | app takeoff-phase start − truth roll start s |'); md.append('|---|---|---|---|---|')
        for r in A['event_timing']:
            md.append(f"| {r['kind']} | {r['flight']} | {r.get('truth_td') or r.get('truth_lo')} | {r.get('app_minus_truth_s')} | {r.get('app_takeoff_start_minus_truth_roll_s', '')} |")
    # ---- latency
    if LAT:
        md.append('\n### Display delay vs error (replay_latency.py)\n')
        md.append('| state | feed | delay s | n | error p50/p90/p99 m | behind reality p50/p90 m | share extrapolated |'); md.append('|---|---|---|---|---|---|---|')
        for k, r in LAT.items():
            st, feed, dl = k.split('|')
            md.append(f"| {st} | {feed} | {dl} | {r['n']} | {r['err_p50']}/{r['err_p90']}/{r['err_p99']} | {r['lag_p50']}/{r['lag_p90']} | {r['dr_frac']} |")
    # ---- model
    if M:
        md.append('\n### Reference model (replay_model.py)\n')
        md.append(f"Phase agreement {M['phase_agreement']} over {M['reports_scored']} reports of SFO traffic. Stats: model {M['stats_model']} vs truth {M['stats_truth']}.\n")
        md.append('| kind | flight | rwy (truth) | t | detail |'); md.append('|---|---|---|---|---|')
        for e in M['events']:
            det = {k: v for k, v in e.items() if k not in ('kind', 'flight', 'rwy', 'truth_rwy', 'truth', 't')}
            md.append(f"| {e['kind']} | {e['flight']} | {e.get('rwy', '')} ({e.get('truth_rwy') or e.get('truth') or ''}) | {e['t']} | {det} |")
    open(os.path.join(OUT, 'summary.md'), 'w').write('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
