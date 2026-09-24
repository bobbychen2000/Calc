#!/usr/bin/env python3
"""Record live ADS-B around SFO from several public aggregators, for provider comparison and replay tests.

Writes one gzip JSON-lines file per provider per hour to refs/cache/rec/ (gitignored: the data is the providers',
see docs/research/realtime_feeds.md for their terms). Each line: {"t": local receive time (s), "p": provider, "d": response}.
Rates respect each provider's documented limit (adsb.fi: 1 request/s; adsb.lol: dynamic, we use 1/s).
adsb.fi lists aircraft under 'aircraft', adsb.lol under 'ac'.
Radius 40 nm around the SFO ARP (37.6188 N, 122.3754 W, FAA 5010) so full approaches are captured.
Usage: python3 tools/live/record.py [hours]
"""
import gzip, json, os, sys, threading, time, urllib.request

LAT, LON, NM = 37.6188, -122.3754, 40
PROVIDERS = {
    'adsbfi': f'https://opendata.adsb.fi/api/v2/lat/{LAT}/lon/{LON}/dist/{NM}',
    'adsblol': f'https://api.adsb.lol/v2/point/{LAT}/{LON}/{NM}',
    # airplanes.live: API needs prior permission (403: 'Please contact us at contact@airplanes.live'), not used
}
PERIOD = {'adsbfi': 1.0, 'adsblol': 1.0}
OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'refs', 'cache', 'rec')
UA = 'sfo-live-3d/0.1 (personal non-commercial visualisation; contact via github.com/bobbychen2000)'

def run(name, url, until):
    f = None; hour = None; backoff = 0
    while time.time() < until:
        t0 = time.time()
        h = time.strftime('%Y%m%d_%H', time.gmtime(t0))
        if h != hour:
            if f: f.close()
            f = gzip.open(os.path.join(OUT, f'{name}_{h}.jsonl.gz'), 'at'); hour = h
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read())
            f.write(json.dumps({'t': round(t0, 3), 'p': name, 'd': d}, separators=(',', ':')) + '\n'); f.flush()
            backoff = 0
        except Exception as e:
            f.write(json.dumps({'t': round(t0, 3), 'p': name, 'err': str(e)[:200]}) + '\n'); f.flush()
            backoff = min(60, backoff * 2 + 2)
        time.sleep(max(0, PERIOD[name] + backoff - (time.time() - t0)))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'recorder.pid'), 'w').write(str(os.getpid()))
    until = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 10) * 3600
    ts = [threading.Thread(target=run, args=(n, u, until), daemon=True) for n, u in PROVIDERS.items()]
    for t in ts: t.start()
    for t in ts: t.join()
