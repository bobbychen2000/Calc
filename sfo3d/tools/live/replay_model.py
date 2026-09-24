#!/usr/bin/env python3
"""Reference implementation (Python, for evaluation only -- NOT wired into js/) of the proposed online traffic state
machine of docs/research/traffic_audit.md section 6, run causally over the recorded 1 Hz merged stream and scored
against the offline ground truth of tools/live/replay_events.py.

What it implements (each rule cites the measurement that motivates it; section numbers refer to the audit):
  * report hygiene: MLAT positions dropped while ADS-B is fresh (3.6); ADS-B 'track' ignored on the surface (3.4);
    vehicles decided once per hex (category C*, type SERV) and never shown as aircraft (3.8).
  * runway posterior for arrivals: Bayesian accumulation of cross-track likelihoods, sigma widening with distance
    (offset visual/RNP procedures), prior from the D-ATIS approach runways (5.2).
  * air/ground from kinematics, not from the transponder flag (the flag is the 100 kt WOW-validation override,
    EASA CS-ACNS AMC1 ACNS.D.ELS.020): touchdown = deceleration onset after the threshold (or the flag, back-dated);
    liftoff = sustained climb evidence (vertical rate >= 192 ft/min twice, or alt_geom +50 ft over its runway value);
    the flag during the take-off roll only means "gs > ~100 kt" (3.5).
  * go-around: final/flare, never touched down, climbing >= 150 ft above the lowest point with >= +500 ft/min.
  * phases: final, flare, rollout, taxi, pushback, still, lineup/takeoff (roll), initial climb/departure, approach.
  * live statistics (6.9): arrivals/departures per runway in the last hour, go-arounds, runway occupancy, taxi times.
Scores: phase agreement with the offline truth (same groups as replay_audit.py), runway correctness and the distance
from the threshold at which the runway became certain, online detection latency of touchdown/liftoff (data time),
false go-arounds, statistics vs the offline event list.
CAVEAT: thresholds were chosen with this (small, overnight) recording in view -> re-validate on daytime data.
Usage: python3 tools/live/replay_model.py [--no-atis]
"""
import argparse, json, math, os, sys
from collections import Counter, defaultdict, deque
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import FT, KT, NM, OUT, RWY, build_reports, ident, is_vehicle, on_runway, rwy_coords, wrap180, utc
from replay_events import in_airport, Arr
from replay_audit import Truth
import replay_wx

VR_CLIMB = 192          # ft/min, 3 quanta of 64
DECEL_TD = 1.0          # kt/s sustained over two report intervals -> wheels on (flare decel measured 0.3-0.8 kt/s)
GA_CLIMB_FT, GA_VR = 150, 500


def num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


class AC:
    def __init__(self, hx):
        self.hx = hx; self.phase = 'new'; self.rwy = None; self.logp = defaultdict(float); self.n_fin = 0
        self.hist = deque(maxlen=12); self.td = None; self.lo = None; self.veh = None; self.minalt = None
        self.geom_ref = deque(maxlen=20); self.flag_air_t = None; self.last_ads_b = -1e9; self.exit_t = None
        self.events = []; self.decided_at = None; self.nose = None; self.climb_n = 0


class Model:
    def __init__(self, app_prior=None):
        self.A = {}; self.app_prior = app_prior or {}
        self.log = []   # (t, hex, phase, rwy)

    # ---------------------------------------------------------------- report hygiene
    def clean(self, a, r):
        if (r.get('type') or '').startswith('mlat') and r['pt'] - a.last_ads_b < 10:
            return None                                   # MLAT position while ADS-B is fresh: drop
        if (r.get('type') or '').startswith('adsb') or (r.get('type') or '').startswith('adsr'):
            a.last_ads_b = r['pt']
        r = dict(r)
        if r['ground']:
            r['track'] = None                             # surface 'track' is unreliable (3.4)
        return r

    def prior(self, name):
        return math.log(self.app_prior.get(name, 0.02))

    # ---------------------------------------------------------------- per report
    def update(self, r):
        hx = r['hex_']; a = self.A.get(hx)
        if a is None: a = self.A[hx] = AC(hx)
        if a.veh is None and ((r.get('category') or '')[:1] == 'C' or r.get('t') in ('SERV',) or r.get('type') == 'adsb_icao_nt'):
            a.veh = True
        if a.veh: a.phase = 'vehicle'; return a
        r = self.clean(a, r)
        if r is None: return a
        a.hist.append(r)
        gs = num(r.get('gs')); alt = num(r.get('alt_baro')); geom = num(r.get('alt_geom'))
        vr = num(r.get('baro_rate')) if num(r.get('baro_rate')) is not None else num(r.get('geom_rate'))
        th = num(r.get('true_heading')); trk = num(r.get('track'))
        x, z, t = r['x'], r['z'], r['pt']
        hdg = trk if trk is not None else th
        if hdg is None and len(a.hist) >= 2:
            p = a.hist[-2]
            if math.hypot(x - p['x'], z - p['z']) > 5: hdg = math.degrees(math.atan2(x - p['x'], -(z - p['z']))) % 360
        prev = a.phase
        if a.phase == 'rollout':
            # wheels are on the runway from the touchdown estimate until the runway exit, whatever the flag says
            if a.rwy:
                aa, c = rwy_coords(a.rwy, x, z)
                if abs(c) > 45: a.phase = 'taxi'; a.exit_t = t; a.events.append((t, 'exit', a.rwy, round(aa)))
            if a.phase != prev: a.events.append((t, prev, a.phase, a.rwy))
            self.log.append((t, hx, a.phase, a.rwy)); return a
        if not r['ground'] or a.phase in ('takeoff', 'final', 'flare', 'go-around'):
            self.air_logic(a, r, t, x, z, gs, alt, geom, vr, hdg)
        else:
            self.ground_logic(a, r, t, x, z, gs, hdg, th)
        if a.phase != prev:
            a.events.append((t, prev, a.phase, a.rwy))
        self.log.append((t, hx, a.phase, a.rwy))
        return a

    def air_logic(self, a, r, t, x, z, gs, alt, geom, vr, hdg):
        gnd = r['ground']
        # ---- take-off roll continues through the 100 kt flag until real climb evidence
        if a.phase == 'takeoff':
            if not gnd and a.flag_air_t is None: a.flag_air_t = t
            if gnd and geom is not None: a.geom_ref.append(geom)
            climb = (vr is not None and vr >= VR_CLIMB)
            a.climb_n = a.climb_n + 1 if climb else 0
            ref = np.median(a.geom_ref) if a.geom_ref else None
            if not gnd and (a.climb_n >= 2 or (vr is not None and vr >= 500) or (ref is not None and geom is not None and geom >= ref + 50)):
                a.lo = t; a.phase = 'climb'; a.events.append((t, 'liftoff', a.rwy, gs)); return
            if gs is not None and len(a.hist) >= 3 and a.hist[-3].get('gs') and gs < a.hist[-3]['gs'] - 6 and gs > 40:
                a.phase = 'rollout'; a.events.append((t, 'rejected', a.rwy, gs))
            return
        if gnd and a.phase in ('final', 'flare'):
            self.touchdown(a, t, 'flag'); return
        # ---- cold start (first seen with the "airborne" flag while still on the runway, e.g. mid take-off roll at
        #      app start: UAL60 07:28Z was at 100 kt on 28L): treat as a take-off roll until climb evidence
        if a.phase == 'new' and not gnd and on_runway(x, z) and hdg is not None:
            for n in on_runway(x, z).split('/'):
                if abs(wrap180(hdg - RWY[n]['hdg_deg'])) < 15 and (vr is None or vr > -300) and (alt is None or alt - RWY[n]['elev_ft'] < 200):
                    a.phase = 'takeoff'; a.rwy = n; a.flag_air_t = t; a.climb_n = 0; return
        # ---- climb / departure
        if a.phase in ('climb', 'departure'):
            if a.phase == 'climb' and (t - (a.lo or t) > 120 or (alt is not None and alt > 3000)): a.phase = 'departure'
            return
        # ---- runway posterior (arrivals)
        best = None
        climbing = vr is not None and vr > 300          # a departure climbing out along the centreline is not on final
        for n, R in RWY.items():
            if climbing or hdg is None or abs(wrap180(hdg - R['hdg_deg'])) > 25: continue
            aa, c = rwy_coords(n, x, z)
            if not (-25000 < aa < 1500): continue
            h = (alt or 0) - R['elev_ft']
            if h > 3000 + max(0, -aa) * 0.09 / FT * FT: continue
            sig = 25 + 0.012 * abs(min(aa, 0))
            a.logp[n] += -0.5 * (c / sig) ** 2 - math.log(sig)
            best = n if best is None or abs(c) < abs(rwy_coords(best, x, z)[1]) else best
        cand = {n: a.logp[n] + self.prior(n) for n in a.logp}
        if best is not None and cand:
            m = max(cand.values()); Z = sum(math.exp(v - m) for v in cand.values())
            post = {n: math.exp(v - m) / Z for n, v in cand.items()}
            top = max(post, key=post.get)
            aa, c = rwy_coords(top, x, z)
            if post[top] >= 0.9 and abs(c) < 150 + 0.1 * abs(aa):
                if a.rwy != top and a.phase in ('final', 'flare'): a.events.append((t, 'runway-change', a.rwy, top))
                if a.phase not in ('final', 'flare') and (a.decided_at is None or t - a.decided_at[0] > 900): a.decided_at = (t, aa, top, post[top])
                a.rwy = top
                if a.phase not in ('final', 'flare', 'go-around'): a.phase = 'final'
        # ---- final -> flare -> touchdown / go-around
        if a.phase in ('final', 'flare') and a.rwy:
            aa, c = rwy_coords(a.rwy, x, z)
            if alt is not None: a.minalt = alt if a.minalt is None else min(a.minalt, alt)
            if a.minalt is not None and alt is not None and alt >= a.minalt + GA_CLIMB_FT and vr is not None and vr >= GA_VR and a.td is None:
                a.phase = 'go-around'; a.events.append((t, 'go-around', a.rwy, alt)); a.logp.clear(); return
            if a.phase == 'final' and aa > -150: a.phase = 'flare'
            if a.phase == 'flare' and aa > 100 and len(a.hist) >= 3:
                g = [num(q.get('gs')) for q in list(a.hist)[-3:]]; ts = [q['pt'] for q in list(a.hist)[-3:]]
                if None not in g and ts[2] > ts[1] > ts[0]:
                    d1 = (g[1] - g[0]) / (ts[1] - ts[0]); d2 = (g[2] - g[1]) / (ts[2] - ts[1])
                    if d1 <= -DECEL_TD and d2 <= -DECEL_TD: self.touchdown(a, ts[0], 'decel')
            if aa > 2500 and a.phase == 'flare' and alt is not None and alt - RWY[a.rwy]['elev_ft'] < 150: self.touchdown(a, t, 'position')
        elif a.phase == 'go-around':
            if alt is not None and (alt > 2500) or (a.events and t - a.events[-1][0] > 180): a.phase = 'approach'; a.minalt = None
        elif not r['ground'] and a.phase in ('new', 'enroute', 'approach', 'unknown', 'taxi', 'still'):
            d = math.hypot(x, z); inbound = vr is not None and vr < -300 and d < 40000 and (alt or 1e9) < 12000
            a.phase = 'approach' if inbound else 'enroute'

    def touchdown(self, a, t, how):
        a.td = t; a.phase = 'rollout'; a.events.append((t, 'touchdown', a.rwy, how))

    def ground_logic(self, a, r, t, x, z, gs, hdg, th):
        if not in_airport(x, z): a.phase = 'ground-other'; return
        rp = on_runway(x, z)
        if a.phase == 'rollout':
            if a.rwy:
                aa, c = rwy_coords(a.rwy, x, z)
                if abs(c) > 45: a.phase = 'taxi'; a.exit_t = t; a.events.append((t, 'exit', a.rwy, round(aa)))
            return
        moving = gs is not None and gs >= 1.5
        # take-off roll: on a runway, aligned, and either >= 50 kt or accelerating >= 1.5 kt/s over ~3 s (take-off
        # acceleration measured 3-5 kt/s; a runway back-taxi at 30-36 kt was seen at 0.1 kt/s: UAL1947 07:31Z)
        acc = None
        if len(a.hist) >= 4 and gs is not None:
            q = a.hist[-4]
            if num(q.get('gs')) is not None and r['pt'] - q['pt'] > 1.5: acc = (gs - q['gs']) / (r['pt'] - q['pt'])
        if rp and gs is not None and (gs >= 50 or (gs >= 20 and acc is not None and acc >= 1.5)) and hdg is not None:
            for n in rp.split('/'):
                if abs(wrap180(hdg - RWY[n]['hdg_deg'])) < 15:
                    if a.phase != 'takeoff': a.rwy = n; a.phase = 'takeoff'; a.flag_air_t = None; a.climb_n = 0; a.geom_ref.clear()
                    return
        if not moving:
            a.phase = 'still'; return
        # push-back: motion against the reported nose
        if th is not None and len(a.hist) >= 2:
            p = a.hist[-2]
            if math.hypot(x - p['x'], z - p['z']) > 2:
                mv = math.degrees(math.atan2(x - p['x'], -(z - p['z']))) % 360
                if abs(wrap180(mv - th)) > 120 and gs <= 8: a.phase = 'pushback'; return
        a.phase = 'taxi'


GROUP = {'final': 'final', 'flare': 'final', 'approach': 'approach', 'rollout': 'rollout', 'takeoff': 'takeoff', 'climb': 'departure', 'departure': 'departure',
         'taxi': 'taxi', 'pushback': 'pushback', 'still': 'still', 'enroute': 'air-other', 'go-around': 'air-other', 'ground-other': 'ground-other', 'new': 'new', 'vehicle': 'vehicle'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--no-atis', action='store_true'); o = ap.parse_args()
    tracks, _ = build_reports()
    events = json.load(open(os.path.join(OUT, 'events.json')))
    TR = Truth(tracks, events)
    prior = {}
    if not o.no_atis:
        M, AT = replay_wx.timeline()
        app = set()
        for k, v in AT.items():
            cfg = replay_wx.runway_config(v['datis']); [app.update(s.replace(' ', '').split(',')) for s in cfg['app']]
        prior = {n: (0.45 if n in app else 0.02) for n in RWY}
    stream = sorted(((r['pt'], hx, r) for hx, L in tracks.items() for r in L), key=lambda q: q[0])
    M_ = Model(prior)
    sfo_related = {a['hex']: bool(a['arrivals'] or a['departures'] or a['sfo_ground']) for a in events['aircraft']}
    conf = Counter(); lat_td = []; lat_lo = []
    for t, hx, r in stream:
        r = dict(r, hex_=hx)
        a = M_.update(r)
        st = TR.at(hx, t)
        if st is None or a.veh or not sfo_related.get(hx): continue
        tp, trw = TR.phase(hx, t, st)
        if tp and (in_airport(st['x'], st['z']) or math.hypot(st['x'], st['z']) < 30000):
            conf[(tp, GROUP.get(a.phase, a.phase))] += 1
    groups = ['final', 'approach', 'rollout', 'takeoff', 'departure', 'taxi', 'pushback', 'still', 'air-other', 'ground-other']
    tot = sum(conf.values()); ok = sum(n for (p, q), n in conf.items() if p == q)
    out = {'reports_scored': tot, 'phase_agreement': round(ok / tot, 3), 'confusion_reports': {p: {q: n for (pp, q), n in conf.items() if pp == p} for p in groups if any(pp == p for (pp, _) in conf)}}
    # event scoring
    ev_rows = []
    by = {a['hex']: a for a in events['aircraft']}
    for hx, A in M_.A.items():
        E = by.get(hx)
        if not E: continue
        for e in A.events:
            if e[1] == 'touchdown':
                tru = min(E['arrivals'], key=lambda q: abs((q.get('td_t') or q['t_flag']) - e[0]), default=None)
                if tru: ev_rows.append(dict(kind='touchdown', flight=E['flight'], how=e[3], rwy=e[2], truth_rwy=tru['rwy'], t=utc(e[0]),
                                            minus_truth_td_s=round(e[0] - tru['td_t'], 1) if tru.get('td_t') else None, minus_flag_s=round(e[0] - tru['t_flag'], 1)))
            if e[1] == 'liftoff':
                tru = min(E['departures'], key=lambda q: abs((q.get('t_lo') or q['t_flag']) - e[0]), default=None)
                if tru: ev_rows.append(dict(kind='liftoff', flight=E['flight'], rwy=e[2], truth_rwy=tru['rwy'], t=utc(e[0]), gs=e[3],
                                            minus_truth_lo_s=round(e[0] - tru['t_lo'], 1) if tru.get('t_lo') else None, minus_flag_s=round(e[0] - tru['t_flag'], 1)))
            if e[1] in ('go-around', 'runway-change', 'rejected'):
                ev_rows.append(dict(kind=e[1], flight=E['flight'], t=utc(e[0]), detail=e[2:]))
        if A.decided_at and E['arrivals']:
            tru = E['arrivals'][-1]
            ev_rows.append(dict(kind='runway-decision', flight=E['flight'], rwy=A.decided_at[2], truth=tru['rwy'], a_m=round(A.decided_at[1]), posterior=round(A.decided_at[3], 3), t=utc(A.decided_at[0])))
    out['events'] = ev_rows
    # live statistics panel (last hour at the end of the recording; plus whole window)
    tend = max(t for t, _, _ in stream)
    stats = defaultdict(Counter)
    for hx, A in M_.A.items():
        for e in A.events:
            if e[1] == 'touchdown': stats['arrivals'][e[2]] += 1; stats['arrivals_last_hour'][e[2]] += int(tend - e[0] <= 3600)
            if e[1] == 'liftoff': stats['departures'][e[2]] += 1; stats['departures_last_hour'][e[2]] += int(tend - e[0] <= 3600)
            if e[1] == 'go-around': stats['go_arounds'][e[2]] += 1
    truth_stats = defaultdict(Counter)
    for a in events['aircraft']:
        for e in a['arrivals']: truth_stats['arrivals'][e['rwy']] += 1
        for e in a['departures']: truth_stats['departures'][e['rwy']] += 1
        for e in a['go_arounds']: truth_stats['go_arounds'][e['rwy']] += 1
    out['stats_model'] = {k: dict(v) for k, v in stats.items()}; out['stats_truth'] = {k: dict(v) for k, v in truth_stats.items()}
    out['atis_prior'] = prior
    json.dump(out, open(os.path.join(OUT, 'model_eval.json'), 'w'), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str)[:12000])


if __name__ == '__main__':
    main()
