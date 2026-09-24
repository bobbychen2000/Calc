"""ADS-B evidence of parked aircraft, tied to SFO's own stand allocation (independent of our stand set).

Inputs (gitignored caches): the ADS-B recording refs/cache/rec/adsblol_*.jsonl.gz ONLY (tools/live/record.py) and
every cached flysfo flight-status snapshot refs/cache/gate_truth/flysfo_api_flight-status_*.json.gz (SFO's AODB stand
windows `stands[]`, see docs/research/gate_truth.md). Readers are reused from tools/live/gatecheck.py (read-only
import); positions are converted with geo_frame.wgs84_to_world (ADS-B is WGS 84), NOT gatecheck's legacy formula.

Licence (review round 2): data/sfo_stands.json is published under ODbL 1.0. adsb.lol's data is ODbL ("The license
for the API as well as all data ADSB.lol makes public is ODbL", docs/research/realtime_feeds.md §3.1); adsb.fi's terms
say "You may not license, sell, rent, or lease any part of the data" (realtime_feeds.md §3.2), so nothing derived from
adsb.fi may go into the ODbL stand file. The recording's adsb.fi files are therefore NOT read here; every stay records
its provider ('prov': 'adsblol').

Method:
  * stays: per aircraft (hex), maximal runs of on-ground reports with gs < 1 kt (or no gs) that stay within 8 m of the
    run's running median, lasting >= 180 s. Position = median of the reports with NACp >= 8 (all if none); heading =
    median true_heading when reported. Spread = 90th percentile distance of those reports from the median.
  * identity: ADS-B callsign seen during the stay, in the 4 h before it or the 45 min after it (the departure
    callsign often appears before push-back); registration / type from the feed ('r', 't').
  * SFO stand: the flysfo flight(s) of that callsign (gatecheck.flights_for: exact callsign, or regional operator by
    flight number) whose stand window, widened by 15 min before and 45 min after (windows are planned times; delays),
    overlaps the stay by >= min(60 s, 30 % of the stay); ties -> most overlap. The consumer (build_stands.py) rejects
    matches far from the stand's lead-in (AODB plan changed / tows) and reports them.
Output: refs/cache/stands/adsb_parked.json (list of stays; those without a stand keep stand=None and still serve as
parked-position evidence for remote/cargo areas).
Usage: python3 tools/stands/adsb_parked.py
"""
import bisect, json, math, os, sys
import numpy as np
from common import GF, WORK, ROOT

sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
import gatecheck as G  # noqa: E402

G.ll_to_world = lambda lat, lon: GF.wgs84_to_world(lat, lon)   # WGS 84 ADS-B -> current world frame
OUT = os.path.join(WORK, 'adsb_parked.json')
PROVIDERS = ('adsblol',)          # ODbL only - see the licence note above


class LolTracks:
    """gatecheck.Tracks restricted to the ODbL provider(s): per aircraft, reports deduplicated by position time"""
    def __init__(self):
        self.h = {}; self.times = []
        for prov in PROVIDERS:
            for r in G.read_records(prov):
                self.times.append(r['t'])
                d = r['d']; ac = d.get('aircraft') if 'aircraft' in d else d.get('ac')
                for a in ac or []:
                    if 'lat' not in a or (a.get('seen_pos') or 0) > 30: continue
                    x, z = G.ll_to_world(a['lat'], a['lon'])
                    if math.hypot(x, z) > 6000: continue
                    tpos = round(r['t'] - (a.get('seen_pos') or 0), 1)
                    self.h.setdefault(a['hex'], {}).setdefault(tpos, dict(a, tpos=tpos, prov=prov, x=x, z=z))
        self.t = {k: sorted(v) for k, v in self.h.items()}; self.times.sort()


def stays_of(h, times):
    out = []; cur = []
    def flush():
        if len(cur) >= 3 and cur[-1]['tpos'] - cur[0]['tpos'] >= 180: out.append(list(cur))
    for t in times:
        a = h[t]
        ok = a.get('alt_baro') == 'ground' and (a.get('gs') is None or a['gs'] < 1.0)
        if ok and cur:
            xs = np.median([p['x'] for p in cur[-40:]]); zs = np.median([p['z'] for p in cur[-40:]])
            if math.hypot(a['x'] - xs, a['z'] - zs) > 8 or a['tpos'] - cur[-1]['tpos'] > 900:
                flush(); cur = []
        if ok: cur.append(a)
        else:
            flush(); cur = []
    flush()
    return out


def main():
    tr = LolTracks()
    info, lu, recs = G.load_flysfo_all()
    print('flysfo:', info, '| aircraft tracks:', len(tr.t), '| recording', len(tr.times), 'polls')
    res = []
    for hx, ts in tr.t.items():
        h = tr.h[hx]
        for st in stays_of(h, ts):
            good = [p for p in st if (p.get('nac_p') or 0) >= 8] or st
            X = np.array([[p['x'], p['z']] for p in good]); m = np.median(X, axis=0)
            d = np.hypot(*(X - m).T); spread = float(np.percentile(d, 90))
            hs = [p['true_heading'] for p in st if p.get('true_heading') is not None]
            hdg = None
            if hs:
                a = np.radians(hs); hdg = float(np.degrees(np.arctan2(np.median(np.sin(a)), np.median(np.cos(a)))) % 360)
            t0, t1 = st[0]['tpos'], st[-1]['tpos']
            # callsign: during, before (4 h), after (45 min)
            cs = None
            i0 = bisect.bisect_left(ts, t0 - 4 * 3600); i1 = bisect.bisect_right(ts, t1 + 2700)
            cands = []
            for t in ts[i0:i1]:
                f = (h[t].get('flight') or '').strip()
                if f and not f.startswith('.'): cands.append((abs(t - (t0 + t1) / 2) if t0 <= t <= t1 else (t0 - t if t < t0 else t - t1), f))
            css = sorted(set(f for _, f in cands))
            reg = next((h[t].get('r') for t in ts if h[t].get('r')), None)
            typ = next((h[t].get('t') for t in ts if h[t].get('t')), None)
            best = None
            for f in css:
                fl, how = G.flights_for(recs, f)
                for r in fl:
                    for s in r.get('stands') or []:
                        a_, b_ = G.iso(s['start_time']), G.iso(s['end_time'])
                        if a_ is None or b_ is None: continue
                        # windows are planned times; real block times drift (delays): extend by 15 min before / 45 min after
                        ov = min(b_ + 2700, t1) - max(a_ - 900, t0)
                        if ov <= 0: continue
                        if ov >= min(60.0, 0.3 * (t1 - t0)):
                            k = (ov, s['stand']['stand_name'])
                            if best is None or k > best[0]:
                                best = (k, {'stand': s['stand']['stand_name'], 'flight': r['flight_id'], 'callsign': f, 'match': how,
                                            'win': [s['start_time'], s['end_time']], 'overlap_s': round(ov),
                                            'sfo_type': (r.get('aircraft_transport_type') or {}).get('icao_code'), 'gate': (r.get('gate') or {}).get('gate_number')})
            lat, lon = GF.world_to_wgs84(float(m[0]), float(m[1]))
            rec = {'hex': hx, 'reg': reg, 'type': typ, 'callsigns': css, 't0': t0, 't1': t1, 'dur_s': round(t1 - t0),
                   'x': round(float(m[0]), 2), 'z': round(float(m[1]), 2), 'lat': round(lat, 7), 'lon': round(lon, 7),
                   'n': len(st), 'n_good': len(good), 'spread90': round(spread, 1), 'hdg': None if hdg is None else round(hdg, 1),
                   'prov': sorted(set(p['prov'] for p in st)), 'n_hdg': len(hs), 'nacp': sorted(set(p.get('nac_p') for p in st if p.get('nac_p') is not None))}
            if best: rec.update(best[1])
            res.append(rec)
    res.sort(key=lambda r: (r.get('stand') or 'zz', r['t0']))
    json.dump({'providers': list(PROVIDERS), 'licence': 'derived from adsb.lol (ODbL 1.0)', 'flysfo': info, 'n_polls': len(tr.times), 'rec_span': [tr.times[0], tr.times[-1]], 'stays': res}, open(OUT, 'w'), indent=0)
    n = sum(1 for r in res if r.get('stand'))
    print(len(res), 'stays,', n, 'with an SFO stand window ->', OUT)


if __name__ == '__main__':
    main()
