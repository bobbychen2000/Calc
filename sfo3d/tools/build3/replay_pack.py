#!/usr/bin/env python3
"""Pack a recent window of real SFO traffic for the phone artifact's in-page replay (owner request, 8 Nov 2026: "an
artifact with the backend being your host's running server").

Why a replay and not a live link: the claude.ai artifact CSP blocks every fetch outside the artifact (measured in close-out
round 3, integration-4), so a published page cannot reach the relay. Instead this packs what the relay itself recorded
(sfo_live_server.py --record refs/cache/rec) and the page replays it at real speed through the app's own relay code path
(tools/build3/replay_shim.js fakes /api/ping, /api/stream, /api/adsb, /api/metar and /api/routeset).

Steps:
  1. tools/live/build_stream.py: the recordings -> the exact SSE event sequence the relay would have sent (same Hub merge).
  2. Keep only the aircraft fields js/live/feed.js normalizeAircraft() reads (smaller file, same app behaviour).
  3. METARs (aviationweather.gov, US Government work) and routes (adsb.lol routeset, ODbL; VRS standing data, CC0) for the
     window's callsigns, asked from the running relay at pack time.
  4. Write <out>/replay.json.gz: {from, until, events: [{T, p}], metar: [...], routes: [...], attribution}.
     No SFO gate plan: flysfo.com data has no licence to embed (docs/research/gate_truth.md, 'Snapshot / artifact mode').

Usage: python3 tools/build3/replay_pack.py --minutes 35 [--end-ago 1] [--relay http://localhost:8000] --out DIR
"""
import argparse, gzip, json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
# fields of a readsb jv2 aircraft record that js/live/feed.js normalizeAircraft() reads (keep in step with it)
KEEP = ('hex', 'flight', 'r', 't', 'desc', 'ownOp', 'year', 'type', 'lat', 'lon', 'lastPosition', 'alt_baro', 'ground',
        'alt_geom', 'gs', 'track', 'true_heading', 'mag_heading', 'track_rate', 'roll', 'baro_rate', 'geom_rate', 'squawk',
        'category', 'emergency', 'nav_altitude_mcp', 'nav_qnh', '_pt', 'seen_pos', 'seen', '_veh', '_src', '_prov', 'mlat',
        '_dbalt', '_faa')


def iso(t): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--minutes', type=float, default=35.0)
    ap.add_argument('--end-ago', type=float, default=1.0, help='minutes before now where the window ends')
    ap.add_argument('--relay', default='http://localhost:8000')
    ap.add_argument('--rec', default=os.path.join(ROOT, 'refs/cache/rec'))
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t1 = time.time() - a.end_ago * 60; t0 = t1 - a.minutes * 60
    raw = os.path.join(a.out, 'stream_raw.jsonl.gz')
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools/live/build_stream.py'), '--from', iso(t0), '--until', iso(t1),
                    '--rec', a.rec, '--gates-every', '0', '--out', raw], check=True)
    ev = []
    for line in gzip.open(raw, 'rt'):
        e = json.loads(line); p = e['p']
        p['ac'] = [{k: x[k] for k in KEEP if k in x} for x in p.get('ac', [])]
        ev.append({'T': round(e['T'], 3), 'p': {k: p[k] for k in ('now', 'dataNow', 'seq', '_source', 'ac') if k in p}})
    if not ev: sys.exit('no events in the window')
    metar = json.load(urllib.request.urlopen(a.relay + '/api/metar?ids=KSFO&format=json', timeout=20))
    metar = [m for m in metar if (m.get('obsTime') or 0) <= ev[-1]['T']] or metar
    last = {}
    for e in ev:
        for x in e['p']['ac']:
            cs = (x.get('flight') or '').strip()
            if cs and x.get('lat') is not None: last[cs] = {'callsign': cs, 'lat': x['lat'], 'lng': x['lon']}
    routes = []; planes = list(last.values())
    for i in range(0, len(planes), 100):
        req = urllib.request.Request(a.relay + '/api/routeset', data=json.dumps({'planes': planes[i:i + 100]}).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
        try:
            txt = urllib.request.urlopen(req, timeout=30).read().decode().strip()
            if txt: routes += [r for r in json.loads(txt) if isinstance(r, dict) and r.get('callsign')]
        except Exception as e:  # routes are optional, as in the app
            print('routes:', e, file=sys.stderr)
    ping = json.load(urllib.request.urlopen(a.relay + '/api/ping', timeout=20))
    pack = {'from': ev[0]['T'], 'until': ev[-1]['T'], 'events': ev, 'metar': metar, 'routes': routes,
            'attribution': ping.get('attribution'), 'packed': time.time()}
    out = os.path.join(a.out, 'replay.json.gz')
    with gzip.open(out, 'wt', compresslevel=9) as f: json.dump(pack, f, separators=(',', ':'))
    os.remove(raw)
    print(f'{out}: {len(ev)} events {iso(ev[0]["T"])} - {iso(ev[-1]["T"])}, {len(metar)} METARs, {len(routes)} routes, '
          f'{os.path.getsize(out) / 1e6:.2f} MB')


if __name__ == '__main__':
    main()
