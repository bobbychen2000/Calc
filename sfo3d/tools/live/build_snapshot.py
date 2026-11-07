#!/usr/bin/env python3
"""Candidate replacement for data/snapshot.js built from adsb.lol records ONLY (close-out round 3, realtime-17).

Why: data/snapshot.js (the snapshot-mode app's recorded traffic, 23 Sep 2026) mixes adsb.fi and adsb.lol records without a
per-record provider; adsb.fi's terms forbid licensing its data ("You may not license, sell, rent, or lease any part of the
data or the service", docs/research/realtime_feeds.md s.3.2), so the file cannot be offered under the repository's terms
(docs/ATTRIBUTION.md, data/snapshot.js row: LICENCE CONFLICT - owner's decision). The September recordings that would allow
an adsb.lol-only rebuild of THAT snapshot were lost with the container (2026-11-04). This tool builds a NEW snapshot from one
adsb.lol response of the own recording (refs/cache/rec/adsblol_*.jsonl.gz; adsb.lol: "all data ADSB.lol makes public is ODbL",
realtime_feeds.md s.3.1), with the provider on every record and the ODbL attribution, plus the KSFO METARs of that time
from the relay's replay cache (refs/cache/replay/wx/metar_ksfo_*.json: aviationweather.gov, NOAA / NWS, U.S. Government
work). It writes a CANDIDATE (default out/live/snapshot_adsblol.js) and never touches data/snapshot.js: whether to keep the
current file, swap in a candidate, or remove the snapshot from the public repository is the owner's decision.

Usage: python3 tools/live/build_snapshot.py --at 2026-11-04T19:30:00Z [--radius-km 60] [--out out/live/snapshot_adsblol.js]
"""
import argparse, datetime as dt, glob, gzip, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ARP = (37.618806, -122.375417)   # KSFO aerodrome reference point (FAA NASR; js/geo.js)
KEEP = ('hex', 'flight', 't', 'r', 'lat', 'lon', 'alt_baro', 'alt_geom', 'gs', 'track', 'true_heading', 'baro_rate', 'category', 'squawk', 'seen', 'seen_pos')


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def lines(p):
    try:
        with gzip.open(p, 'rt') as fh:
            for l in fh:
                try: yield json.loads(l)
                except ValueError: return   # the hour file being written: stop at its end
    except EOFError:
        return


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--at', required=True); ap.add_argument('--radius-km', type=float, default=60.0)
    ap.add_argument('--out', default=os.path.join(ROOT, 'out', 'live', 'snapshot_adsblol.js')); o = ap.parse_args()
    T = ts(o.at); hour = dt.datetime.utcfromtimestamp(T).strftime('%Y%m%d_%H')
    best = None
    for r in lines(os.path.join(ROOT, 'refs', 'cache', 'rec', f'adsblol_{hour}.jsonl.gz')):
        t = r.get('tr') or r.get('t')
        if r.get('p') != 'adsblol' or not isinstance(r.get('d'), dict) or not r['d'].get('ac'): continue
        if t <= T: best = r
        else: break
    if not best: sys.exit(f'no adsb.lol response at or before {o.at} in refs/cache/rec/adsblol_{hour}.jsonl.gz')
    d = best['d']; now_ms = int(round((d.get('now') if d.get('now', 0) > 1e11 else (d.get('now') or best['t']) * 1000)))
    out = []
    for a in d['ac']:
        lat, lon = a.get('lat'), a.get('lon')
        if lat is None or lon is None: continue
        dk = math.hypot((lat - ARP[0]) * 111.2, (lon - ARP[1]) * 111.2 * math.cos(math.radians(ARP[0])))
        if dk > o.radius_km: continue
        rec = {k: (a[k].strip() if isinstance(a[k], str) and k == 'flight' else a[k]) for k in KEEP if k in a and a[k] is not None}
        rec['_prov'] = 'adsb.lol'; out.append(rec)
    out.sort(key=lambda a: a.get('hex', ''))
    # KSFO METARs observed at or before T (the newest three), from the relay's replay cache
    mets = {}
    for p in glob.glob(os.path.join(ROOT, 'refs', 'cache', 'replay', 'wx', 'metar_ksfo_*.json')):
        for m in json.load(open(p)):
            if m.get('obsTime') and m['obsTime'] <= T and m.get('rawOb'): mets[m['obsTime']] = m['rawOb']
    raw = '\n'.join(mets[k] for k in sorted(mets, reverse=True)[:3])
    when = dt.datetime.utcfromtimestamp(now_ms / 1000)
    snap = {'now': now_ms, 'ac': out, '_source': 'recorded snapshot (adsb.lol only)', '_licence': 'ODbL 1.0',
            '_attribution': 'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL'}
    head = (f'// CANDIDATE (not data/snapshot.js - owner decision, docs/ATTRIBUTION.md): recorded ADS-B snapshot around SFO, '
            f'{when:%d %b %Y %H:%M} UTC, adsb.lol records only\n'
            f'// (tools/live/build_snapshot.py --at {o.at}); every record carries _prov. Contains information from ADSB.lol\n'
            f'// (https://adsb.lol), made available under the ODbL 1.0. METARs: aviationweather.gov (NOAA / NWS, U.S. Government work).\n')
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    with open(o.out, 'w') as fh:
        fh.write(head + 'export const SNAPSHOT = ' + json.dumps(snap, separators=(',', ':')) + ';\n'
                 + 'export const SNAPSHOT_METAR = ' + json.dumps(raw) + ';\n')
    print(f'{o.out}: {len(out)} aircraft within {o.radius_km:g} km at {when:%Y-%m-%d %H:%M:%S}Z (adsb.lol response {best["t"]:.1f}), '
          f'{len(mets) and min(3, len(mets))} METARs, {os.path.getsize(o.out)} B')


if __name__ == '__main__':
    main()
