#!/usr/bin/env python3
"""SFO Live 3D — local relay (Python 3 standard library only).

Serves the app from this directory and relays live data, so the browser never talks to third-party APIs directly
(no CORS problems, one shared poll for all open tabs, provider rate limits respected no matter how many tabs).

  python3 sfo_live_server.py [--port 8000] [--radius 40]      then open http://localhost:8000/live.html
  python3 sfo_live_server.py --replay refs/cache/rec [--speed 1] [--skip 600]
        replays traffic recorded by tools/live/record.py through the same merge, re-timed to "now" (for tests)

Endpoints
  /api/ping                 {"sfolive": 1, ...}   (js/live/entry.js detects the relay with this)
  /api/adsb                 latest merged aircraft list, readsb "jv2" shape: {"ac": [...], "now": ms, "_source": ...}
  /api/stream               Server-Sent Events: one "adsb" event per merged update (~1 s), same JSON as /api/adsb
  /api/routeset             POST passthrough to the adsb.lol routeset API (origin/destination by callsign)
  /api/metar?ids=KSFO       raw METAR from aviationweather.gov (cached 60 s)
  /api/status               provider health (last success, latency, errors)

Providers (polled only while a client has asked for data in the last 60 s):
  adsb.fi  https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{nm}   list key 'aircraft'   limit 1 request/s
  adsb.lol https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}                  list key 'ac'
  Terms, attribution and the measured latency of each are documented in docs/research/realtime_feeds.md.
Merge policy: per ICAO hex keep the record with the freshest position (provider 'now' minus 'seen_pos'); fields the
freshest record lacks (registration, type, true heading, ...) are filled from the other provider's record for that hex.
"""
import argparse, gzip, json, os, queue, threading, time, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ARP = (37.6188056, -122.3754167)          # FAA airport reference point (js/geo.js ARP)
UA = 'sfo-live-3d-relay/0.2 (personal, non-commercial visualisation)'
PROVIDERS = [
    {'name': 'adsb.fi', 'home': 'https://adsb.fi', 'period': 1.0, 'key': 'aircraft',
     'url': 'https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{nm}'},
    {'name': 'adsb.lol', 'home': 'https://adsb.lol', 'period': 1.0, 'key': 'ac',
     'url': 'https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}'},
]
IDLE_AFTER = 60.0     # stop polling providers when no client has asked for data for this long (s)
MAX_POS_AGE = 60.0    # drop positions older than this (s)


def http_get(url, timeout=10, data=None, headers=None):
    h = {'User-Agent': UA, 'Accept-Encoding': 'gzip'}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            body = gzip.decompress(body)
        return r.status, body


class Hub:
    """Polls providers, merges per hex, fans updates out to SSE subscribers."""

    def __init__(self, lat, lon, nm, replay=None):
        self.lat, self.lon, self.nm = lat, lon, nm
        self.lock = threading.Lock()
        self.latest = {}          # provider -> (recv_time, provider_now_s, [aircraft])
        self.status = {p['name']: {'ok': None, 'last_ok': None, 'latency_ms': None, 'errors': 0, 'last_error': None} for p in PROVIDERS}
        self.merged = {'ac': [], 'now': int(time.time() * 1000), '_source': None, 'msg': 'waiting for first poll'}
        self.merged_bytes = json.dumps(self.merged).encode()
        self.last_client = 0.0
        self.subs = set()
        self.wake = threading.Event()
        if replay:
            threading.Thread(target=self._replay, args=replay, daemon=True).start()
        else:
            for p in PROVIDERS:
                threading.Thread(target=self._poll, args=(p,), daemon=True).start()

    def _replay(self, root, speed, skip):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'live'))
        import recio
        recs = sorted((r for r in recio.records(root=root) if 'd' in r), key=lambda r: r['t'])
        if not recs:
            print('replay: no records in', root); return
        t_rec0 = recs[0]['t'] + skip
        recs = [r for r in recs if r['t'] >= t_rec0]
        print(f'replay: {len(recs)} provider responses, {(recs[-1]["t"] - t_rec0) / 60:.1f} min from', time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(t_rec0)))
        wall0 = time.time()
        for r in recs:
            due = wall0 + (r['t'] - t_rec0) / speed
            time.sleep(max(0.0, due - time.time()))
            d = r['d']; shift = time.time() - r['t']      # re-time the recording to the present
            lst = d.get('ac') or d.get('aircraft') or []
            now = d.get('now') or r['t']; now = now / 1000.0 if now > 1e12 else float(now)
            with self.lock:
                self.latest[r['p']] = (r['t'] + shift, now + shift, lst)
            self.status.setdefault(r['p'], {})['ok'] = True
            self._merge()
        print('replay: finished')

    def touch(self):
        self.last_client = time.time()
        self.wake.set()

    def _poll(self, p):
        url = p['url'].format(lat=f'{self.lat:.4f}', lon=f'{self.lon:.4f}', nm=self.nm)
        backoff = 0.0
        while True:
            if time.time() - self.last_client > IDLE_AFTER:
                self.wake.wait(5); self.wake.clear(); continue
            t0 = time.time()
            st = self.status[p['name']]
            try:
                code, body = http_get(url)
                j = json.loads(body)
                lst = j.get(p['key']) or j.get('ac') or j.get('aircraft') or []
                now = j.get('now') or j.get('ctime') or t0
                now = now / 1000.0 if now > 1e12 else float(now)
                with self.lock:
                    self.latest[p['name']] = (t0, now, lst)
                st.update(ok=True, last_ok=t0, latency_ms=round((time.time() - t0) * 1000), last_error=None)
                backoff = 0.0
                self._merge()
            except Exception as e:  # network errors, HTTP 429/5xx, bad JSON
                st.update(ok=False, errors=st['errors'] + 1, last_error=str(e)[:200])
                backoff = min(60.0, backoff * 2 + 2.0)
            time.sleep(max(0.0, p['period'] + backoff - (time.time() - t0)))

    def _merge(self):
        wall = time.time()
        best = {}
        with self.lock:
            snaps = list(self.latest.items())
        for name, (recv, now, lst) in snaps:
            for a in lst:
                hx = str(a.get('hex', '')).lower()
                if not hx or a.get('lat') is None:
                    continue
                pos_t = now - float(a.get('seen_pos', a.get('seen', 0)) or 0)
                if wall - pos_t > MAX_POS_AGE:
                    continue
                cur = best.get(hx)
                if cur is None or pos_t > cur[0]:
                    if cur is not None:   # keep fields only the older record has
                        a = {**cur[2], **a}
                    best[hx] = (pos_t, name, a)
                else:
                    best[hx] = (cur[0], cur[1], {**a, **cur[2]})
        now_ms = int(wall * 1000)
        out = []
        for hx, (pos_t, name, a) in best.items():
            a = dict(a)
            a['seen_pos'] = round(max(0.0, wall - pos_t), 2)
            a['_src'] = name
            out.append(a)
        used = sorted({v[1] for v in best.values()})
        merged = {'ac': out, 'now': now_ms, 'total': len(out), '_source': '+'.join(used) or None, 'msg': 'No error'}
        data = json.dumps(merged, separators=(',', ':')).encode()
        with self.lock:
            self.merged, self.merged_bytes = merged, data
            subs = list(self.subs)
        for q in subs:
            try:
                q.put_nowait(data)
            except queue.Full:
                pass


class Cache:
    def __init__(self, ttl):
        self.ttl, self.v, self.t = ttl, {}, {}

    def get(self, k, fn):
        if k in self.v and time.time() - self.t[k] < self.ttl:
            return self.v[k]
        v = fn(); self.v[k], self.t[k] = v, time.time(); return v


METAR = Cache(60)


def make_handler(hub, root):
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=root, **k)

        def log_message(self, fmt, *args):
            if not self.path.startswith('/api/'):
                return
            super().log_message(fmt, *args)

        def _json(self, obj_or_bytes, code=200):
            b = obj_or_bytes if isinstance(obj_or_bytes, bytes) else json.dumps(obj_or_bytes).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers(); self.wfile.write(b)

        def end_headers(self):
            if not self.path.startswith('/api/'):
                self.send_header('Cache-Control', 'no-cache')
            super().end_headers()

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == '/api/ping':
                return self._json({'sfolive': 1, 'providers': [p['name'] for p in PROVIDERS], 'stream': True})
            if u.path == '/api/adsb':
                hub.touch()
                with hub.lock:
                    b = hub.merged_bytes
                return self._json(b)
            if u.path == '/api/status':
                return self._json({'providers': hub.status, 'clients': len(hub.subs), 'polling': time.time() - hub.last_client < IDLE_AFTER})
            if u.path == '/api/stream':
                return self._stream()
            if u.path == '/api/metar':
                ids = urllib.parse.parse_qs(u.query).get('ids', ['KSFO'])[0][:8]
                try:
                    txt = METAR.get(ids, lambda: http_get(f'https://aviationweather.gov/api/data/metar?ids={urllib.parse.quote(ids)}&format=raw&hours=2')[1].decode())
                except Exception as e:
                    return self._json({'error': str(e)[:200]}, 502)
                b = txt.encode(); self.send_response(200)
                self.send_header('Content-Type', 'text/plain'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b); return
            return super().do_GET()

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == '/api/routeset':
                n = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(min(n, 200000))
                try:
                    code, b = http_get('https://api.adsb.lol/api/0/routeset', data=body, headers={'Content-Type': 'application/json'})
                    return self._json(b, code)
                except Exception as e:
                    return self._json({'error': str(e)[:200]}, 502)
            self.send_error(404)

        def _stream(self):
            hub.touch()
            q = queue.Queue(maxsize=4)
            with hub.lock:
                hub.subs.add(q); first = hub.merged_bytes
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Accel-Buffering', 'no')
            self.end_headers()
            try:
                self.wfile.write(b'event: adsb\ndata: ' + first + b'\n\n'); self.wfile.flush()
                while True:
                    try:
                        data = q.get(timeout=15)
                        hub.touch()
                        self.wfile.write(b'event: adsb\ndata: ' + data + b'\n\n')
                    except queue.Empty:
                        self.wfile.write(b': keepalive\n\n')
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with hub.lock:
                    hub.subs.discard(q)

    return H


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--host', default='127.0.0.1', help='use 0.0.0.0 to open it from a phone on the same Wi-Fi')
    ap.add_argument('--radius', type=int, default=40, help='nm around the SFO ARP')
    ap.add_argument('--replay', help='directory of recordings (tools/live/record.py) to replay instead of polling')
    ap.add_argument('--speed', type=float, default=1.0, help='replay speed factor')
    ap.add_argument('--skip', type=float, default=0.0, help='seconds of the recording to skip')
    a = ap.parse_args()
    root = os.path.dirname(os.path.abspath(__file__))
    hub = Hub(ARP[0], ARP[1], a.radius, replay=(a.replay, a.speed, a.skip) if a.replay else None)
    if a.replay:
        hub.last_client = float('inf')
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(hub, root))
    srv.daemon_threads = True
    print(f'SFO Live 3D relay: http://{"localhost" if a.host in ("127.0.0.1", "0.0.0.0") else a.host}:{a.port}/live.html')
    print('ADS-B: ' + ', '.join(p['name'] for p in PROVIDERS) + ' (see About in the app for attribution and terms)')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
