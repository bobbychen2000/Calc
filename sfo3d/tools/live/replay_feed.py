#!/usr/bin/env python3
"""Turn the ADS-B recording into the payload sequence the app would have received, for tools/live/replay_app.mjs.

Modes (what the browser app does, js/live/app.js + js/live/feed.js + sfo_live_server.py):
  relay5   the app with the local relay: Feed polls /api/adsb every 5 s (app.js intervalMs relay ? 5000 : 7000);
           the relay (sfo_live_server.py Hub._merge) merges the latest adsb.fi and adsb.lol snapshots per hex,
           freshest position wins (now - seen_pos), fields missing from the freshest record are filled from the
           other, positions older than 60 s dropped, seen_pos rewritten relative to the relay's wall clock.
  relay1   same merge, polled every 1 s (what the relay's /api/stream SSE would deliver) -- an upper bound.
  lol7     no relay, adsb.lol polled directly every 7 s, rotating to adsb.fi after an error (feed.js Feed.tick).
           (Browsers cannot actually do this: neither API sends Access-Control-Allow-Origin -- realtime_feeds.md 3.1/3.2.)
Timing assumption (inferred): a recorded response arrives LAT = 0.35 s after its request start (measured round trips
0.26-0.46 s, docs/research/realtime_feeds.md 3.2); the recorder, like the relay, polls each provider every 1 s + back-off.
Output: refs/cache/replay/polls_<mode>.jsonl  one line per poll: {"T": wall s, "p": payload (readsb jv2 shape)}
Usage: python3 tools/live/replay_feed.py relay5 [relay1 lol7]
       python3 tools/live/replay_feed.py routes     # one batched POST to the adsb.lol routeset API for every airline
                                                    # callsign in the recording -> refs/cache/replay/routes.json, stored
                                                    # exactly as js/live/feed.js Routes caches it ({codes, airports, plausible} | null)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_common import OUT, snapshots, request_log

LAT = 0.35
KEEP = ('hex', 'flight', 'r', 't', 'desc', 'ownOp', 'year', 'type', 'lat', 'lon', 'alt_baro', 'alt_geom', 'gs', 'track', 'true_heading', 'mag_heading',
        'track_rate', 'roll', 'baro_rate', 'geom_rate', 'squawk', 'category', 'emergency', 'nav_altitude_mcp', 'nav_qnh', 'seen_pos', 'seen', 'mlat', 'tisb', 'dbFlags')


def stream():
    """time-ordered (arrival, provider, now_s, aircraft list) of both providers, plus error events"""
    ev = []
    for prov in ('adsbfi', 'adsblol'):
        for req, now, acs in snapshots(prov):
            ev.append((req + LAT, prov, now, [{k: a[k] for k in KEEP if k in a} for a in acs]))
        for t, ok, err in request_log(prov):
            if not ok: ev.append((t + LAT, prov, None, err))
    ev.sort(key=lambda e: e[0])
    return ev


def merge(latest, T):
    """sfo_live_server.py Hub._merge at wall time T"""
    best = {}
    for name, (recv, now, lst) in latest.items():
        for a in lst:
            hx = str(a.get('hex', '')).lower()
            if not hx or a.get('lat') is None: continue
            pos_t = now - float(a.get('seen_pos', a.get('seen', 0)) or 0)
            if T - pos_t > 60: continue
            cur = best.get(hx)
            if cur is None or pos_t > cur[0]:
                if cur is not None: a = {**cur[2], **a}
                best[hx] = (pos_t, name, a)
            else:
                best[hx] = (cur[0], cur[1], {**a, **cur[2]})
    out = []
    for hx, (pos_t, name, a) in best.items():
        a = dict(a); a['seen_pos'] = round(max(0.0, T - pos_t), 2); a['_src'] = name; out.append(a)
    return {'ac': out, 'now': int(T * 1000), 'total': len(out), '_source': '+'.join(sorted({v[1] for v in best.values()}))}


def run(mode):
    ev = stream()
    fn = os.path.join(OUT, f'polls_{mode}.jsonl')
    n = 0
    with open(fn, 'w') as f:
        if mode.startswith('relay'):
            period = float(mode[5:])
            latest = {}; T = ev[0][0] + 3.0
            for e in ev:
                while e[0] > T:
                    if latest:
                        f.write(json.dumps({'T': round(T, 3), 'p': merge(latest, T)}, separators=(',', ':')) + '\n'); n += 1
                    T += period
                if e[2] is not None: latest[e[1]] = (e[0], e[2], e[3])
        elif mode == 'lol7':
            # Feed.tick: one request in flight; next request 7 s after success; on error rotate provider and wait
            # min(60, 2*1.6^fails) s (429 -> 60 s). Emulated with the recorded responses closest after each request.
            by = {p: [e for e in ev if e[1] == p] for p in ('adsblol', 'adsbfi')}
            idx = {p: 0 for p in by}; src = 'adsblol'; fails = 0; T = ev[0][0] + 3.0; Tend = ev[-1][0]
            while T < Tend:
                L = by[src]; i = idx[src]
                while i < len(L) and L[i][0] < T: i += 1
                idx[src] = i
                if i >= len(L): break
                e = L[i]
                if e[2] is None:
                    fails += 1; wait = 60.0 if '429' in str(e[3]) else min(60.0, 2 * 1.6 ** min(fails, 8))
                    src = 'adsbfi' if src == 'adsblol' else 'adsblol'; T = e[0] + wait; continue
                fails = 0
                f.write(json.dumps({'T': round(e[0], 3), 'p': {'ac': e[3], 'now': int(e[2] * 1000), '_source': src}}, separators=(',', ':')) + '\n'); n += 1
                T = e[0] + 7.0
        else:
            raise SystemExit('unknown mode ' + mode)
    print(mode, n, 'polls ->', fn)


def routes():
    """Route per callsign. The app's source, POST https://api.adsb.lol/api/0/routeset, answered HTTP 201 with an empty
    body on 24 Sep 2026 08:48Z (and GET /api/0/route/{cs}/{lat}/{lng} HTTP 500), so the live app currently gets NO
    routes (feed.js Routes caches every callsign as null when the JSON parse fails). For the "with routes" replay we read
    the same VRS standing-data record from the static mirror https://vrs-standing-data.adsb.lol/routes/{cs[:2]}/{cs}.json
    (the URL the API's deprecated GET redirects to, adsblol/api api_routes.py); 'plausible' is not in that file and is
    set True (ASSUMED)."""
    import re, urllib.request, urllib.error
    from replay_common import build_reports, ident
    tracks, _ = build_reports()
    cs = sorted({ident(L)['flight'] for L in tracks.values() if ident(L)['flight'] and re.match(r'^[A-Z]{3}\d[0-9A-Z]{0,4}$', ident(L)['flight'])})
    out = {}
    for c in cs:
        try:
            req = urllib.request.Request(f'https://vrs-standing-data.adsb.lol/routes/{c[:2]}/{c}.json', headers={'User-Agent': 'sfo-live-3d/0.1 (traffic audit)'})
            x = json.loads(urllib.request.urlopen(req, timeout=30).read())
            codes = x['_airport_codes_iata'].split('-') if x.get('_airport_codes_iata') and x['_airport_codes_iata'] != 'unknown' else None
            out[c] = {'codes': codes, 'airports': [{'iata': a.get('iata'), 'icao': a.get('icao'), 'name': a.get('name')} for a in x.get('_airports') or []], 'plausible': True} if codes else None
        except urllib.error.HTTPError as e:
            out[c] = None
    json.dump(out, open(os.path.join(OUT, 'routes.json'), 'w'), indent=0)
    print(len(cs), 'callsigns,', sum(1 for v in out.values() if v), 'with a route')


if __name__ == '__main__':
    for m in (sys.argv[1:] or ['relay5']):
        routes() if m == 'routes' else run(m)
