#!/usr/bin/env python3
"""SFO Live 3D — local relay (Python 3 standard library only).

Serves the app from this directory and relays live data, so the browser never talks to third-party APIs directly
(no CORS problems, one shared poll for all open tabs/phones, provider rate limits respected however many clients).

  python3 sfo_live_server.py [--port 8000] [--host 0.0.0.0]      then open http://localhost:8000/live.html
  python3 sfo_live_server.py --replay refs/cache/rec [--speed 1] [--skip 600 | --from 2026-09-24T14:00Z] [--loop]
        replays traffic recorded by tools/live/record.py through the same merge, re-timed to "now" (for tests)
  python3 sfo_live_server.py --no-sfo-gates       never contact flysfo.com (see /api/gates below)
  python3 sfo_live_server.py --record refs/cache/rec   also write every provider response in record.py's format

Endpoints
  /api/ping          {"sfolive": 1, "v", "stream", "features", "attribution"}   (js/live/entry.js detects the relay)
  /api/adsb          latest merged aircraft list, readsb "jv2" shape {"ac": [...], "now": ms, "seq", ...}
  /api/stream        Server-Sent Events. Default: one "adsb" event (full list, same JSON as /api/adsb) per merged update.
                     ?delta=1: a full "adsb" event first, then "delta" events {now, seq, ac: [changed], gone: [keys]};
                     a full event is re-sent whenever a client missed an update (seq gap) and every 30 s.
  /api/gates         SFO's own gate/stand plan from flysfo.com, parsed: {flights, byCallsign, aliases, byStand, ...}
                     ?cs=SKW5339,RPA3456 adds regional callsigns to map (besides those currently on ADS-B)
  /api/routeset      POST {"planes": [{"callsign", "lat", "lng"}]} -> adsb.lol routeset format (origin/destination)
  /api/metar?ids=KSFO[&format=json]   aviationweather.gov METAR (raw text by default; cached 60 s)
  /api/status        provider health, latency, 429s, merge/hygiene counters, gates/routes state

Data sources, terms and measured behaviour: docs/research/realtime_feeds.md (ADS-B), gate_truth.md (flysfo),
realtime_impl.md (this relay's design and test results).
  adsb.lol  GET https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}  primary: every 1.0-1.5 s (random), one request in
            flight; on HTTP 429 wait >= 2 s then back off exponentially to 30 s (feeds §5.1), plus an adaptive floor
            (x1.5 per 429, x0.9 per success) so it settles at the rate adsb.lol currently grants this IP instead of
            cycling through refusals (Poller._schedule; realtime_impl.md §2). Data licence ODbL 1.0.
  adsb.fi   GET https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{nm}  every 2.0 s, ~0.3 s after an even
            second (its snapshot changes only on even seconds, feeds §4.2); documented limit 1 request/s;
            personal non-commercial use, cite and link adsb.fi.
Merge (feeds §5.2, traffic_audit §6.2): per aircraft key (ICAO hex lower-cased; non-ICAO '~' ids keep the '~'),
the freshest position (provider 'now' - 'seen_pos') wins; fields of the same report missing from the winner are filled
from the other provider's copy of that report; identity fields (callsign, squawk, category, registration, type ...)
come from the freshest record that has them, desc/ownOp/year preferably from adsb.fi (adsb.lol omits them).
Hygiene: MLAT/TIS-B positions are ignored while an ADS-B/ADS-R position < 10 s old exists, and rejected if they imply
more than 1.5 x gs x dt + 50 m of motion; on the ground the surface 'track' and every field listed in 'mlat' are
dropped (their origin is MLAT or unverified, traffic_audit §4.3); ground vehicles (emitter category C1-C7, type
SERV/GRND) are flagged '_veh' stickily. Each merged aircraft carries provenance: '_src' (provider of the position),
'_prov' (providers that list it) and '_pt' (absolute position time, epoch s).
"""
import argparse, base64, datetime as dt, glob, gzip, heapq, http.client, json, math, os, random, re, signal, ssl, sys
import threading, time, urllib.parse, urllib.request
from collections import deque
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

VERSION = '0.3'
ROOT = os.path.dirname(os.path.abspath(__file__))
ARP = (37.6188056, -122.3754167)   # FAA airport reference point (AirNav KSFO; js/geo.js ARP)
CONTACT = 'https://github.com/bobbychen2000/Calc'          # the owner's repository (git remote origin)
UA = f'sfo-live-3d-relay/{VERSION} (+{CONTACT}; personal non-commercial visualisation)'
CACHE_DIR = os.path.join(ROOT, 'refs', 'cache')           # gitignored: third-party data stays local

PROVIDERS = {
    # adsb.lol is primary (freshest: 'now' generated during the request, feeds §1, §4.2)
    'adsblol': dict(id='adsblol', name='adsb.lol', short='lol', home='https://adsb.lol', host='api.adsb.lol',
                    path='/v2/point/{lat:.4f}/{lon:.4f}/{nm:d}', schedule='jitter', period=(1.0, 1.5),
                    backoff_first=2.0, backoff_max=30.0),
    'adsbfi': dict(id='adsbfi', name='adsb.fi', short='fi', home='https://adsb.fi', host='opendata.adsb.fi',
                   path='/api/v3/lat/{lat:.4f}/lon/{lon:.4f}/dist/{nm:d}', schedule='even', period=2.0, phase=0.3,
                   backoff_first=4.0, backoff_max=60.0),
}
IDLE_AFTER = 60.0     # stop polling providers when no client has asked for data for this long (s)
MAX_POS_AGE = 60.0    # older positions move to 'lastPosition', as readsb does (README-json.md 'lastPosition')
SNAP_TTL = 45.0       # ignore a provider's last snapshot once it is this old (provider failing / backing off)
SAME_REPORT_S = 0.2   # two providers' positions within this time are the same report (traffic_audit §6.2.5)
MLAT_HOLD_S = 10.0    # ignore MLAT/TIS-B positions while an ADS-B/ADS-R one is younger than this (§6.2.2)
FULL_EVERY = 30.0     # delta streams get a full list at least this often (s)

ATTRIBUTION = {
    'adsb': 'Aircraft data: ADSB.lol (https://adsb.lol) — contains information from ADSB.lol, which is made available '
            'here under the Open Database License (ODbL, https://opendatacommons.org/licenses/odbl/1-0/) — and adsb.fi '
            '(https://adsb.fi) open data (personal, non-commercial use).',
    'routes': 'Routes: Virtual Radar Server standing data (https://github.com/vradarserver/standing-data, CC0 1.0), via '
              'ADSB.lol (api.adsb.lol routeset / vrs-standing-data.adsb.lol mirror).',
    'gates': 'Gates and stands: San Francisco International Airport flight status (https://www.flysfo.com/flight-info/'
             'flight-status). Unofficial use of SFO\'s public flight-status data; no terms of use are published.',
    'metar': 'Weather: NOAA/NWS Aviation Weather Center (https://aviationweather.gov).',
}

SRC_RANK = {'adsb_icao': 0, 'adsb_icao_nt': 1, 'adsr_icao': 2, 'tisb_icao': 3, 'adsc': 4, 'mlat': 5, 'other': 6,
            'mode_s': 7, 'adsb_other': 8, 'adsr_other': 9, 'tisb_other': 10, 'tisb_trackfile': 11}   # readsb order
IDENT = ('flight', 'squawk', 'emergency', 'category', 'r', 't', 'desc', 'ownOp', 'year', 'dbFlags', 'alert', 'spi')
PREFER_FI = ('desc', 'ownOp', 'year')                     # adsb.lol omits them (feeds §3.1, verified §54)
DB_FIELDS = ('r', 't', 'desc', 'ownOp', 'year', 'dbFlags')
META = ('seen', 'messages', 'rssi')
DROP_ALWAYS = ('dst', 'dir')                              # adsb.fi-only distance/bearing from the query point
VOLATILE = ('seen', 'seen_pos', 'messages', 'rssi')       # ignored when deciding whether a record changed
VEH_CAT = re.compile(r'^C[1-7]$')                          # DO-260B emitter category set C: surface vehicles/obstacles


def adsb_like(src_type):
    """ADS-B / ADS-R positions (GNSS-derived, broadcast by the aircraft) versus MLAT / TIS-B / Mode S / other."""
    return bool(src_type) and (src_type.startswith('adsb') or src_type.startswith('adsr'))


def hav_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(a)))


# ------------------------------------------------------------------------------------------------ HTTP client
_SSL = ssl.create_default_context()


class Http:
    """Keep-alive HTTPS client for one host. Honours HTTPS_PROXY / NO_PROXY like urllib (CONNECT tunnel)."""

    def __init__(self, host, timeout=10.0):
        self.host, self.timeout, self.conn, self.lock = host, timeout, None, threading.Lock()

    def _connect(self):
        proxy = urllib.request.getproxies().get('https')
        if proxy and not urllib.request.proxy_bypass(self.host):
            # CONNECT tunnel through the proxy; TLS (and certificate checks) end-to-end with self.host
            u = urllib.parse.urlsplit(proxy if '://' in proxy else 'http://' + proxy)
            c = http.client.HTTPSConnection(u.hostname, u.port or 8080, timeout=self.timeout, context=_SSL)
            hdr = {}
            if u.username:
                hdr['Proxy-Authorization'] = 'Basic ' + base64.b64encode(
                    f'{urllib.parse.unquote(u.username)}:{urllib.parse.unquote(u.password or "")}'.encode()).decode()
            c.set_tunnel(self.host, 443, headers=hdr)
            return c
        return http.client.HTTPSConnection(self.host, 443, timeout=self.timeout, context=_SSL)

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None

    def request(self, method, path, body=None, headers=None):
        """-> (status, {lower-case header: value}, body bytes, decompressed)."""
        h = {'User-Agent': UA, 'Accept-Encoding': 'gzip', 'Accept': 'application/json', 'Connection': 'keep-alive'}
        h.update(headers or {})
        with self.lock:
            for attempt in (0, 1):
                reused = self.conn is not None
                if self.conn is None:
                    self.conn = self._connect()
                try:
                    self.conn.request(method, path, body=body, headers=h)
                    r = self.conn.getresponse()
                    data = r.read()
                    hd = {k.lower(): v for k, v in r.getheaders()}
                    if r.will_close:
                        self.close()
                    if hd.get('content-encoding') == 'gzip':
                        data = gzip.decompress(data)
                    return r.status, hd, data
                except (http.client.RemoteDisconnected, http.client.CannotSendRequest, ConnectionResetError,
                        BrokenPipeError) as e:
                    self.close()
                    if attempt or not reused:      # retry once only when a kept-alive connection had gone stale
                        raise
                except Exception:
                    self.close()
                    raise


def http_get(url, timeout=15.0, data=None, headers=None, method=None):
    """One-off request (urllib). -> (status, headers, body); HTTP errors are returned, not raised."""
    h = {'User-Agent': UA, 'Accept-Encoding': 'gzip'}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, hd, body = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        status, hd, body = e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b''
    hd['_wire_bytes'] = len(body)
    if hd.get('content-encoding') == 'gzip' and body:
        body = gzip.decompress(body)
    return status, hd, body


# ------------------------------------------------------------------------------------------------ provider polling
class Poller(threading.Thread):
    """Polls one provider on its own schedule, one request in flight. Shared with tools/live/record.py.

    on_result(prov, t_start, t_recv, status, headers, json_or_None, error_or_None) is called for every request.
    active() -> bool: poll only while true (the relay stops when no client is connected; the recorder never stops).
    """

    def __init__(self, prov, on_result, lat=ARP[0], lon=ARP[1], nm=40, active=lambda: True, wake=None):
        super().__init__(daemon=True, name='poll-' + prov['id'])
        self.p, self.on_result, self.active = prov, on_result, active
        self.url_path = prov['path'].format(lat=lat, lon=lon, nm=int(nm))
        self.http = Http(prov['host'])
        self.wake = wake or threading.Event()
        self.stop_ev = threading.Event()
        self.phase = prov.get('phase', 0.0)
        self.fails = 0
        self.t_first = None
        self.floor = 0.0      # adaptive minimum interval after HTTP 429s (AIMD: x1.5 per 429, x0.9 per success)
        self.next_due = 0.0
        self.lags = deque(maxlen=30)
        self.st = dict(requests=0, ok=0, http429=0, errors=0, dup=0, last_ok=None, last_error=None, last_code=None,
                       backoff_s=0.0, floor_s=0.0, recent=deque(maxlen=1000), latency_ms=deque(maxlen=200), lag_s=deque(maxlen=200), last_now=None)

    @property
    def url(self):
        return f'https://{self.p["host"]}{self.url_path}'

    def _slot_after(self, t):
        """adsb.fi: first 'even second + phase' instant at or after t (local clock)."""
        base = math.floor(t / 2.0) * 2.0 + self.phase
        while base < t:
            base += 2.0
        return base

    def _schedule(self, t0, t1, ok, retry_after=None, status=None):
        """Next request time. Success: the provider's cadence, but never faster than the adaptive floor. Failure:
        exponential back-off (backoff_first x 2^n up to backoff_max, or Retry-After if longer).

        The floor exists because adsb.lol's limits are "dynamic based on the environment load" (its README) and this
        egress IP is shared: on 24 Sep 15:13-15:16Z, after each back-off (2, 4, 8, 16 s) the first request at the normal
        1.0-1.5 s cadence was refused again, i.e. 3 of 4 requests were 429s (refs/cache/rec/adsblol_20260924_15). So
        each 429 raises the floor x1.5 (at least backoff_first) and each success lowers it x0.9 until it is below the
        normal period again: the poller settles at the rate the provider currently grants, instead of cycling through
        refusals (which, for adsb.fi, count toward its temporary IP restriction, realtime_feeds §3.2)."""
        p = self.p
        if ok:
            self.fails = 0
            self.st['backoff_s'] = 0.0
            if self.floor:
                self.floor *= 0.9
                if self.floor < (p['period'][1] if p['schedule'] == 'jitter' else p['period']):
                    self.floor = 0.0
            if p['schedule'] == 'even':
                self.next_due = self._slot_after(max(t0 + 1.0, t0 + self.floor - 1.0))   # next even second + phase
            else:
                self.next_due = max(t0 + max(random.uniform(*p['period']), self.floor), t1 + 0.05)
            self.st['floor_s'] = round(self.floor, 2)
            return
        self.fails += 1
        if status == 429:
            self.floor = min(p['backoff_max'], max(p['backoff_first'], self.floor * 1.5))
        wait = max(min(p['backoff_max'], p['backoff_first'] * 2 ** (self.fails - 1)), self.floor)
        if retry_after:
            wait = max(wait, min(retry_after, 300.0))
        self.st['backoff_s'] = wait
        self.st['floor_s'] = round(self.floor, 2)
        self.next_due = self._slot_after(t1 + wait) if p['schedule'] == 'even' else t1 + wait

    def _adapt_phase(self, t0, now_s):
        """adsb.fi snapshots are stamped on even seconds. If, requested at even + phase, we keep getting the previous
        snapshot (t0 - now >= phase + 1.5 s), its snapshot was not yet written: move the phase 0.1 s later."""
        if self.p['schedule'] != 'even':
            return
        self.lags.append(t0 - now_s)
        if len(self.lags) == self.lags.maxlen:
            late = sum(1 for x in self.lags if x >= self.phase + 1.5) / len(self.lags)
            if late > 0.3 and self.phase < 1.2:
                self.phase = round(self.phase + 0.1, 2)
                self.lags.clear()

    def run(self):
        while not self.stop_ev.is_set():
            if not self.active():
                self.wake.wait(5.0)
                self.wake.clear()
                continue
            now = time.time()
            if self.next_due == 0.0 and self.p['schedule'] == 'even':
                self.next_due = self._slot_after(now)
            if self.next_due > now:
                if self.stop_ev.wait(min(self.next_due - now, 5.0)):
                    break
                continue
            t0 = time.time()
            self.t_first = self.t_first or t0
            status, hd, js, err = None, {}, None, None
            try:
                status, hd, body = self.http.request('GET', self.url_path)
                if status == 200:
                    js = json.loads(body)
                    if not isinstance(js, dict) or not isinstance(js.get('ac', js.get('aircraft')), list):
                        err, js = 'unexpected JSON shape', None
                else:
                    err = f'HTTP {status}'
            except Exception as e:  # network error, timeout, bad JSON
                err = (type(e).__name__ + ': ' + str(e))[:200]
            t1 = time.time()
            st = self.st
            st['requests'] += 1
            st['last_code'] = status
            st['recent'].append((t1, status))
            st['latency_ms'].append(round((t1 - t0) * 1000))
            ok = js is not None
            ra = None
            if ok:
                st['ok'] += 1
                st['last_ok'] = t1
                now_s = js.get('now') or js.get('ctime')
                if now_s:
                    now_s = now_s / 1000.0 if now_s > 1e11 else float(now_s)
                    st['lag_s'].append(round(t0 - now_s, 3))
                    if st['last_now'] == now_s:
                        st['dup'] += 1
                    st['last_now'] = now_s
                    self._adapt_phase(t0, now_s)
            else:
                if status == 429:
                    st['http429'] += 1
                else:
                    st['errors'] += 1
                st['last_error'] = f'{time.strftime("%H:%M:%S", time.gmtime(t1))}Z {err}'
                try:
                    ra = float(hd.get('retry-after')) if hd.get('retry-after') else None
                except ValueError:
                    ra = None
            self._schedule(t0, t1, ok, ra, status)
            try:
                self.on_result(self.p, t0, t1, status, hd, js, err)
            except Exception as e:  # never let a consumer bug stop polling
                print('on_result error:', repr(e), file=sys.stderr)

    def _recent(self, window):
        t = time.time()
        rr = [(tt, c) for (tt, c) in self.st['recent'] if t - tt <= window]
        r = [c for _, c in rr]
        ok = sum(1 for c in r if c == 200)
        span = min(window, max(1.0, t - self.t_first)) if self.t_first else window
        return {'window_s': round(span), 'requests': len(r), 'ok': ok, 'http429': sum(1 for c in r if c == 429),
                'ok_per_min': round(ok * 60.0 / span, 1) if r else 0.0}

    def status(self):
        st = self.st
        lat, lag = sorted(st['latency_ms']), sorted(st['lag_s'])
        q = lambda a, f: a[min(len(a) - 1, int(f * len(a)))] if a else None
        return {'name': self.p['name'], 'url': self.url, 'requests': st['requests'], 'ok': st['ok'],
                'http429': st['http429'], 'errors': st['errors'], 'duplicates': st['dup'],
                'last_ok_age_s': round(time.time() - st['last_ok'], 1) if st['last_ok'] else None,
                'last_code': st['last_code'], 'last_error': st['last_error'], 'backoff_s': st['backoff_s'],
                'latency_ms_p50': q(lat, 0.5), 'latency_ms_p90': q(lat, 0.9),
                'request_minus_now_s_p50': q(lag, 0.5), 'request_minus_now_s_p90': q(lag, 0.9),
                'phase_s': self.phase if self.p['schedule'] == 'even' else None, 'floor_s': st['floor_s'],
                'last_10min': self._recent(600),
                'next_in_s': round(max(0.0, self.next_due - time.time()), 2) if self.next_due else None}


# ------------------------------------------------------------------------------------------------ recording
class RecordWriter:
    """tools/live/record.py format: one gzip JSON-lines file per provider per UTC hour in `out_dir`, each line
    {"t": request start (s), "tr": response received (s), "p": provider id, "code": HTTP status, "d": response}
    or {..., "err": message, "ra": Retry-After} for failures. Files are appended (a new gzip member per open);
    tools/live/recio.py reads them, including the hour still being written."""

    def __init__(self, out_dir):
        self.dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.files, self.lock = {}, threading.Lock()

    def write(self, pid, t0, t1, status, hd, js, err):
        rec = {'t': round(t0, 3), 'tr': round(t1, 3), 'p': pid, 'code': status}
        if js is not None:
            rec['d'] = js
        else:
            rec['err'] = err
            if hd.get('retry-after'):
                rec['ra'] = hd.get('retry-after')
        line = json.dumps(rec, separators=(',', ':')) + '\n'
        hour = time.strftime('%Y%m%d_%H', time.gmtime(t0))
        with self.lock:
            f = self.files.get(pid)
            if f is None or f[0] != hour:
                if f:
                    f[1].close()
                f = (hour, gzip.open(os.path.join(self.dir, f'{pid}_{hour}.jsonl.gz'), 'at'))
                self.files[pid] = f
            f[1].write(line)
            f[1].flush()

    def close(self):
        with self.lock:
            for _, f in self.files.values():
                try:
                    f.close()
                except Exception:
                    pass
            self.files = {}


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True


# ------------------------------------------------------------------------------------------------ merge hub
class Clock:
    """Maps data time (a recording's clock in replay) to wall time; identity when live."""

    def __init__(self, wall0=None, src0=None, speed=1.0):
        self.wall0, self.src0, self.speed = wall0, src0, speed

    def to_wall(self, t):
        return t if self.src0 is None or t is None else self.wall0 + (t - self.src0) / self.speed

    def to_src(self, w):
        return w if self.src0 is None or w is None else self.src0 + (w - self.wall0) * self.speed


class Hub:
    """Latest snapshot per provider -> per-aircraft merge + hygiene -> JSON payloads and SSE fan-out."""

    def __init__(self, mode='live'):
        self.mode = mode
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.snaps = {}          # provider id -> dict(t0, recv, now, scale, list, name)
        self.hist = {}           # key -> per-aircraft memory (last accepted position, last ADS-B time, vehicle flag)
        self.vehicles = set()    # sticky vehicle keys
        self.seq = 0
        self.full = self.delta = b''
        self.full_t = 0.0
        self.prev_sig = {}
        self.latest = {'ac': [], 'now': int(time.time() * 1000), 'seq': 0, 'total': 0, '_source': None,
                       'msg': 'waiting for the first provider response'}
        self.full = json.dumps(self.latest, separators=(',', ':')).encode()
        self.last_client = 0.0
        self.clients = 0
        self.wakes = []          # one Event per poller, set when a client shows up
        self.replay_pos = None
        self.counters = dict(merges=0, mlat_held=0, mlat_jump=0, ground_track_dropped=0, ground_mlat_fields_dropped=0,
                             same_report_fills=0, pos_to_lastPosition=0, db_type_disagree=0)
        self.fresher = {}        # provider short -> count of merged aircraft whose position it supplied (last merge)
        self.ext = []            # extra consumers of provider results (e.g. RecordWriter)
        self.pollers = {}

    # -- activity
    def touch(self):
        idle = not self.active()
        self.last_client = time.time()
        if idle:
            for w in self.wakes:
                w.set()

    def active(self):
        return time.time() - self.last_client < IDLE_AFTER

    # -- ingest
    def on_result(self, prov, t0, t1, status, hd, js, err):
        for f in self.ext:
            f(prov['id'], t0, t1, status, hd, js, err)
        if js is None:
            return
        self.ingest(prov, t0, t1, js)

    def ingest(self, prov, t0, t1, js, clock=None, scale=1.0):
        now = js.get('now') or js.get('ctime')
        now = (now / 1000.0 if now > 1e11 else float(now)) if now else t0
        if clock is not None:
            now = clock.to_wall(now)
        lst = js.get('ac') if 'ac' in js else js.get('aircraft')
        with self.lock:
            self.snaps[prov['id']] = dict(t0=t0, recv=t1, now=now, scale=scale, list=lst or [], name=prov['name'],
                                          short=prov['short'])
            self._merge()

    def reset(self):
        with self.lock:
            self.snaps.clear()
            self.hist.clear()
            self.prev_sig.clear()

    # -- merge
    def _merge(self):
        wall = time.time()
        C = self.counters
        C['merges'] += 1
        per = {}                                   # key -> [(prov short, snap, record, pos_t, seen_t)]
        for pid, s in self.snaps.items():
            if wall - s['recv'] > SNAP_TTL:
                continue
            k_now, sc = s['now'], s['scale']
            for a in s['list']:
                hx = str(a.get('hex') or '').lower().strip()
                if not hx:
                    continue
                if a.get('lat') is not None and a.get('lon') is not None:
                    pt = k_now - float(a.get('seen_pos') or 0) * sc
                elif isinstance(a.get('lastPosition'), dict) and a['lastPosition'].get('lat') is not None:
                    pt = k_now - float(a['lastPosition'].get('seen_pos') or 0) * sc
                else:
                    continue                       # no position at all (Mode S only): nothing to draw
                st = k_now - float(a.get('seen') or 0) * sc
                per.setdefault(hx, []).append((s['short'], s, a, pt, st))
        # '~' (non-ICAO) ids from different providers merge only if their positions agree (same target)
        for hx in [k for k in per if k.startswith('~') and len(per[k]) > 1]:
            recs = per[hx]
            p0, p1 = _pos(recs[0][2]), _pos(recs[1][2])
            if p0 and p1 and hav_m(p0[0], p0[1], p1[0], p1[1]) > 2000:
                per[hx] = [recs[0]]
                per[hx + '@' + recs[1][0]] = [recs[1]]
        out, sigs, fresher = [], {}, {}
        for key, recs in per.items():
            rec = self._merge_one(key, recs, wall)
            if rec is None:
                continue
            fresher[rec['_src']] = fresher.get(rec['_src'], 0) + 1
            sig = json.dumps({k: (v if k != 'lastPosition' else (v.get('lat'), v.get('lon'))) for k, v in rec.items()
                              if k not in VOLATILE}, separators=(',', ':'))
            sigs[key] = sig
            out.append((key, rec))
        # forget aircraft not seen for 10 min
        for k in [k for k, h in self.hist.items() if wall - h.get('seen', 0) > 600]:
            del self.hist[k]
        self.fresher = fresher
        changed = [r for k, r in out if self.prev_sig.get(k) != sigs[k]]
        gone = [k for k in self.prev_sig if k not in sigs]
        publish = bool(changed or gone) or self.seq == 0
        if publish:                  # a duplicate snapshot (nothing new) is not pushed to streams
            self.seq += 1
        used = sorted({s['name'] for s in self.snaps.values() if wall - s['recv'] <= SNAP_TTL})
        head = {'now': int(wall * 1000), 'seq': self.seq, 'total': len(out), '_source': '+'.join(used) or None, 'msg': 'No error'}
        full = dict(head, ac=[r for _, r in out])
        self.latest = full
        self.full = json.dumps(full, separators=(',', ':')).encode()
        if publish:
            self.prev_sig = sigs
            self.delta = json.dumps(dict(head, ac=changed, gone=gone), separators=(',', ':')).encode()
            self.cond.notify_all()
        else:
            self.counters['unchanged'] = self.counters.get('unchanged', 0) + 1

    def _merge_one(self, key, recs, wall):
        C = self.counters
        h = self.hist.setdefault(key, {})
        h['seen'] = wall
        # 1. position candidates, with MLAT/TIS-B hygiene
        cands = []
        adsb_pts = [c[3] for c in recs if adsb_like(c[2].get('type')) and _pos(c[2])]
        last_adsb = max(adsb_pts + ([h['adsb_pt']] if h.get('adsb_pt') is not None else []), default=None)
        for (short, s, a, pt, st) in recs:
            src = a.get('type')
            if not adsb_like(src):
                if last_adsb is not None and pt - last_adsb < MLAT_HOLD_S:
                    C['mlat_held'] += 1
                    continue
                last = h.get('last')
                p = _pos(a)
                if last and p and pt > last[0]:
                    gs = max(float(a.get('gs') or 0), float(last[3] or 0)) or 250.0
                    if hav_m(p[0], p[1], last[1], last[2]) > 1.5 * gs * 0.514444 * (pt - last[0]) + 50:
                        C['mlat_jump'] += 1
                        continue
            cands.append((short, s, a, pt, st))
        if cands:
            cands.sort(key=lambda c: (-c[3], SRC_RANK.get(c[2].get('type'), 20)))
            best = cands[0]
            # same report from both providers (|dt| <= 0.05 s): prefer the better source type, then adsb.lol
            ties = [c for c in cands if best[3] - c[3] <= 0.05]
            if len(ties) > 1:
                ties.sort(key=lambda c: (SRC_RANK.get(c[2].get('type'), 20), c[0] != 'lol'))
                best = ties[0]
            short, s, a, pt, st = best
            p = _pos(a)
            if p and (not h.get('last') or pt >= h['last'][0]):
                h['last'] = (pt, p[0], p[1], a.get('gs'), short, a)
                if adsb_like(a.get('type')):
                    h['adsb_pt'] = pt
        elif h.get('last') and wall - h['last'][0] <= MAX_POS_AGE:
            pt, _, _, _, short, a = h['last']         # every current position was rejected: keep the last good one
            s = None
        else:
            return None
        out = dict(a)
        for k in DROP_ALWAYS:
            out.pop(k, None)
        out['hex'] = key          # '~xxxxxx@fi' only when two providers' '~' ids disagree in position
        others = [c for c in recs if c[2] is not a]
        # 2. same report in the other provider: fill fields the winner lacks (e.g. true_heading, nav_qnh)
        for (o_short, o_s, o, o_pt, o_st) in others:
            if abs(o_pt - pt) <= SAME_REPORT_S:
                filled = False
                for k, v in o.items():
                    if k not in out and k not in IDENT and k not in DROP_ALWAYS and k not in META:
                        out[k] = v
                        filled = True
                C['same_report_fills'] += filled
        # 3. identity from the freshest record that has it (desc/ownOp/year: adsb.fi first)
        allr = recs if any(c[2] is a for c in recs) else recs + [('last', None, a, pt, pt)]
        for k in IDENT:
            have = [c for c in allr if c[2].get(k) not in (None, '')]
            if not have:
                out.pop(k, None)
                continue
            if k in PREFER_FI and any(c[0] == 'fi' for c in have):
                have = [c for c in have if c[0] == 'fi']
            if k in DB_FIELDS:
                # one database per aircraft, not per report: the providers' databases can disagree (ACA738 C-FDUW was
                # BCS3 at adsb.fi, BCS1 at adsb.lol on 24 Sep) and the position winner alternates, so the type would
                # flicker. adsb.fi's value when it has one (it also carries desc/ownOp/year), else the position winner.
                pick = next((c for c in have if c[0] == 'fi'), None) or next((c for c in have if c[2] is a), None) or max(have, key=lambda c: c[4])
            else:
                pick = max(have, key=lambda c: c[4])
            out[k] = pick[2][k]
            if k == 't':
                # the other provider's database type when it differs: the app keeps the one that agrees with the
                # transponder's own emitter category (js/live/traffic.js resolveType; review round 1: AAL1023 N959XV was
                # 'PA27 Piper Aztec' at adsb.fi but A21N at adsb.lol, emitter category A3)
                alt = next((c for c in have if c[0] != pick[0] and c[2].get('t') and c[2].get('t') != out['t']), None)
                if alt:
                    out['_dbalt'] = {'t': alt[2]['t'], 'desc': alt[2].get('desc'), 'p': alt[0]}
                    C['db_type_disagree'] += 1
                else:
                    out.pop('_dbalt', None)
        seen_t = max(c[4] for c in recs)
        # 4. surface hygiene
        dropped = []
        if out.get('alt_baro') == 'ground':
            for f in list(out.get('mlat') or []):
                if f in out and f not in ('lat', 'lon', 'alt_baro'):
                    out.pop(f)
                    dropped.append(f)
                    C['ground_mlat_fields_dropped'] += 1
            if 'track' in out:
                out.pop('track')
                dropped.append('track')
                C['ground_track_dropped'] += 1
            out.pop('track_rate', None)
        if dropped:
            out['_drop'] = sorted(set(dropped))
        # 5. vehicles (sticky: two of thirteen SFO vehicles sent reports without a category, traffic_audit F8)
        if VEH_CAT.match(str(out.get('category') or '')) or out.get('t') in ('SERV', 'GRND'):
            self.vehicles.add(key)
        if key in self.vehicles:
            out['_veh'] = 1
        # 6. ages relative to the relay clock; old positions become lastPosition (readsb semantics)
        age = wall - pt
        if age > MAX_POS_AGE and 'lat' in out:
            out['lastPosition'] = {'lat': out.pop('lat'), 'lon': out.pop('lon'), 'seen_pos': round(age, 1),
                                   'nic': out.get('nic'), 'rc': out.get('rc')}
            C['pos_to_lastPosition'] += 1
        elif 'lat' in out:
            out['seen_pos'] = round(max(0.0, age), 2)
        elif isinstance(out.get('lastPosition'), dict):
            out['lastPosition'] = dict(out['lastPosition'], seen_pos=round(max(0.0, age), 1))
        out['seen'] = round(max(0.0, wall - seen_t), 1)
        out['_src'] = short
        out['_prov'] = '+'.join(sorted({c[0] for c in recs}))
        out['_pt'] = round(pt, 3)
        return out

    # -- read side
    def current_callsigns(self):
        with self.lock:
            return {(a.get('flight') or '').strip().upper(): a for a in self.latest.get('ac', []) if a.get('flight')}

    def status(self):
        with self.lock:
            snaps = {s['name']: {'age_s': round(time.time() - s['recv'], 1), 'aircraft': len(s['list'])}
                     for s in self.snaps.values()}
            return {'mode': self.mode, 'seq': self.seq, 'aircraft': self.latest.get('total', 0), 'snapshots': snaps,
                    'position_from': self.fresher, 'vehicles': len(self.vehicles), 'counters': dict(self.counters),
                    'clients': self.clients, 'polling': self.active()}


def _pos(a):
    if a.get('lat') is not None and a.get('lon') is not None:
        return float(a['lat']), float(a['lon'])
    lp = a.get('lastPosition')
    if isinstance(lp, dict) and lp.get('lat') is not None:
        return float(lp['lat']), float(lp['lon'])
    return None


# ------------------------------------------------------------------------------------------------ routes
class Routes:
    """Origin/destination by callsign (Virtual Radar Server standing data, CC0 1.0).

    Order: the adsb.lol routeset API (POST https://api.adsb.lol/api/0/routeset); when it fails (non-2xx, or the
    HTTP 201 empty body observed since 24 Sep 08:48Z, traffic_audit F5) or is in cool-down after 3 consecutive
    failures (30 min), the bulk files of adsb.lol's static mirror of the same data, https://vrs-standing-data.adsb.lol/
    routes.csv.gz + airports.csv.gz (the files adsb.lol's own API loads, adsblol/api provider.py; mirror README: "All
    data from https://github.com/vradarserver/standing-data/", LICENSE = CC0 1.0, identical to upstream). They are
    downloaded once (5.5 MB), refreshed with a conditional GET at most daily, and kept in refs/cache/routes/.
    Only definite answers are cached (per callsign per UTC day); a failed lookup is never cached as "no route".
    'plausible' is recomputed here for the reported position (the deployed API's check returns a tuple, which is
    always true: adsblol/api plausible.py / api_routes.py at 3c969c8).
    """
    API = 'https://api.adsb.lol/api/0/routeset'
    MIRROR = 'https://vrs-standing-data.adsb.lol/'

    def __init__(self, mode='auto', cache_dir=os.path.join(CACHE_DIR, 'routes')):
        self.mode, self.dir = mode, cache_dir
        self.cache, self.day = {}, None
        self.api_fail, self.api_cool_until = 0, 0.0
        self.routes_blob = self.airports = None
        self.mirror_checked = 0.0
        self.lock = threading.Lock()
        self.stats = dict(api_ok=0, api_fail=0, mirror_lookups=0, mirror_downloads=0, unknown=0, last_error=None,
                          source=None)

    # -- mirror (bulk)
    def _mirror_file(self, name):
        os.makedirs(self.dir, exist_ok=True)
        path = os.path.join(self.dir, 'vrs_' + name)
        meta_p = path + '.meta.json'
        meta = {}
        if os.path.exists(meta_p):
            try:
                meta = json.load(open(meta_p))
            except ValueError:
                meta = {}
        fresh = os.path.exists(path) and time.time() - meta.get('checked', 0) < 86400
        if not fresh:
            hdr = {}
            if os.path.exists(path) and meta.get('etag'):
                hdr['If-None-Match'] = meta['etag']
            if os.path.exists(path) and meta.get('last_modified'):
                hdr['If-Modified-Since'] = meta['last_modified']
            try:
                code, hd, body = http_get(self.MIRROR + name, timeout=60, headers=dict(hdr, **{'Accept-Encoding': 'identity'}))
                if code == 200 and body:
                    tmp = path + '.tmp'
                    open(tmp, 'wb').write(body)
                    os.replace(tmp, path)
                    self.stats['mirror_downloads'] += 1
                    meta = {'etag': hd.get('etag'), 'last_modified': hd.get('last-modified')}
                elif code != 304:
                    raise IOError(f'HTTP {code}')
                meta['checked'] = time.time()
                json.dump(meta, open(meta_p, 'w'))
            except Exception as e:
                self.stats['last_error'] = f'mirror {name}: {e}'[:200]
                if not os.path.exists(path):
                    raise
        return path

    def _load_mirror(self):
        if self.routes_blob is not None and time.time() - self.mirror_checked < 86400:
            return True
        try:
            rp, ap = self._mirror_file('routes.csv.gz'), self._mirror_file('airports.csv.gz')
            self.routes_blob = b'\n' + gzip.decompress(open(rp, 'rb').read()).replace(b'\r\n', b'\n')
            airports = {}
            import csv, io
            for row in csv.reader(io.StringIO(gzip.decompress(open(ap, 'rb').read()).decode('utf-8-sig'))):
                if len(row) >= 9 and row[0] != 'Code':
                    try:
                        airports[row[0]] = {'name': row[1], 'icao': row[2] or row[0], 'iata': row[3], 'location': row[4],
                                            'countryiso2': row[5], 'lat': float(row[6]), 'lon': float(row[7]),
                                            'alt_feet': float(row[8] or 0)}
                    except ValueError:
                        pass
            self.airports = airports
            self.mirror_checked = time.time()
            return True
        except Exception as e:
            self.stats['last_error'] = f'mirror: {e}'[:200]
            return False

    def _mirror_route(self, cs):
        """Row 'Callsign,Code,Number,AirlineCode,AirportCodes' -> adsb.lol routeset entry (provider.py _route)."""
        i = self.routes_blob.find(b'\n' + cs.encode() + b',')
        if i < 0:
            return {'callsign': cs, 'number': 'unknown', 'airline_code': 'unknown', 'airport_codes': 'unknown',
                    '_airport_codes_iata': 'unknown', '_airports': []}
        j = self.routes_blob.find(b'\n', i + 1)
        _, code, num, airline, codes = self.routes_blob[i + 1:j if j > 0 else None].decode().split(',')[:5]
        aps = [self.airports.get(c) for c in codes.split('-')]
        iata = '-'.join((ap['iata'] if ap and ap.get('iata') else c) for c, ap in zip(codes.split('-'), aps))
        return {'callsign': cs, 'number': num, 'airline_code': airline, 'airport_codes': codes,
                '_airport_codes_iata': iata, '_airports': [dict(ap, alt_meters=round(ap['alt_feet'] * 0.3048, 2)) for ap in aps if ap]}

    # -- API
    def _api(self, planes):
        body = json.dumps({'planes': planes}).encode()
        code, hd, b = http_get(self.API, data=body, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=15)
        if code not in (200, 201) or not b.strip():
            raise IOError(f'HTTP {code}, {len(b)} bytes')
        arr = json.loads(b)
        if not isinstance(arr, list):
            raise IOError('unexpected JSON')
        got = {x.get('callsign'): x for x in arr if isinstance(x, dict)}
        # the API lists only callsigns it knows; the rest are definite "unknown" answers
        return {p['callsign']: got.get(p['callsign']) or {'callsign': p['callsign'], '_airport_codes_iata': 'unknown',
                                                           'airport_codes': 'unknown', '_airports': []} for p in planes}

    def lookup(self, planes):
        """planes: [{callsign, lat, lng}] -> (list of routeset entries, source) ; raises if no source works."""
        day = time.strftime('%Y%m%d', time.gmtime())
        with self.lock:
            if day != self.day:
                self.cache, self.day = {}, day
            todo = [p for p in planes if p.get('callsign') and p['callsign'] not in self.cache][:100]
        src = 'cache'
        if todo:
            res = None
            if self.mode in ('auto', 'api') and time.time() >= self.api_cool_until:
                try:
                    res = self._api(todo)
                    self.api_fail = 0
                    self.stats['api_ok'] += 1
                    src = 'adsb.lol routeset API'
                except Exception as e:
                    self.api_fail += 1
                    self.stats['api_fail'] += 1
                    self.stats['last_error'] = f'api: {e}'[:200]
                    if self.api_fail >= 3:
                        self.api_cool_until = time.time() + 1800
            if res is None and self.mode in ('auto', 'mirror'):
                with self.lock:
                    ok = self._load_mirror()
                if ok:
                    res = {p['callsign']: self._mirror_route(p['callsign']) for p in todo}
                    self.stats['mirror_lookups'] += len(todo)
                    src = 'VRS standing data (vrs-standing-data.adsb.lol mirror)'
            if res is None:
                raise IOError(self.stats['last_error'] or 'no route source available')
            with self.lock:
                for cs, r in res.items():
                    r = dict(r, _src=src)
                    r.pop('plausible', None)
                    self.cache[cs] = r
                    self.stats['unknown'] += r.get('_airport_codes_iata') == 'unknown'
            self.stats['source'] = src
        out = []
        for p in planes:
            r = self.cache.get(p.get('callsign'))
            if r is None:
                continue
            r = dict(r)
            if r.get('_airports') and p.get('lat') is not None and p.get('lng') is not None:
                r['plausible'], r['_leg'] = plausible(float(p['lat']), float(p['lng']), r['_airports'])
            else:
                r['plausible'] = False
            codes = (r.get('airport_codes') or '').split('-')
            if 'KSFO' in codes:
                r['_sfo'] = 'origin' if codes[0] == 'KSFO' else 'destination' if codes[-1] == 'KSFO' else 'stop'
            out.append(r)
        return out, src

    def cached(self, cs):
        return self.cache.get(cs)

    def status(self):
        return dict(self.stats, mode=self.mode, cached=len(self.cache), mirror_loaded=self.routes_blob is not None,
                    api_cooldown_s=round(max(0, self.api_cool_until - time.time())))


def plausible(lat, lon, airports):
    """Is the position within max(50 NM, 20 % of the leg) of any leg's great circle (adsb.lol's thresholds,
    plausible.py), done with a proper cross-track/along-track test? -> (bool, index of the nearest leg or None)."""
    R = 6371008.8
    best = (False, None, 1e18)
    for i in range(len(airports) - 1):
        A, B = airports[i], airports[i + 1]
        d_ab = hav_m(A['lat'], A['lon'], B['lat'], B['lon'])
        thr = max(50 * 1852.0, 0.2 * d_ab)
        d_ap, d_bp = hav_m(A['lat'], A['lon'], lat, lon), hav_m(B['lat'], B['lon'], lat, lon)
        if min(d_ap, d_bp) <= thr:
            dist = min(d_ap, d_bp)
        else:
            th13, th12 = _bearing(A['lat'], A['lon'], lat, lon), _bearing(A['lat'], A['lon'], B['lat'], B['lon'])
            xt = math.asin(max(-1.0, min(1.0, math.sin(d_ap / R) * math.sin(th13 - th12)))) * R
            at = math.acos(max(-1.0, min(1.0, math.cos(d_ap / R) / max(1e-12, math.cos(xt / R))))) * R
            on_leg = math.cos(th13 - th12) > 0 and at <= d_ab
            dist = abs(xt) if on_leg else 1e18
        ok = dist <= thr
        if ok and dist < best[2]:
            best = (True, i, dist)
    return best[0], best[1]


def _bearing(lat1, lon1, lat2, lon2):
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    return math.atan2(math.sin(dl) * math.cos(p2), math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))


# ------------------------------------------------------------------------------------------------ SFO gates
REGIONAL = {'SKW', 'RPA', 'ENY', 'QXE', 'ASH', 'EDV', 'GJS', 'JIA', 'PDT', 'CPZ'}
# SkyWest, Republic, Envoy, Horizon, Mesa, Endeavor, GoJet, PSA, Piedmont, Compass: ICAO designators verified in the
# VRS standing data airlines.csv (github.com/vradarserver/standing-data airlines/schema-01). They fly under the
# marketing carrier's flight number, and flysfo lists the marketing callsign (e.g. UAL5339, gate_truth §3). Which
# marketing flight a regional ADS-B callsign is, is decided from the data (number + aircraft type + VRS route),
# never from an assumed partnership table.
CS_RE = re.compile(r'^([A-Z]{3})0*(\d+)([A-Z]*)$')
# flysfo type codes that are not ICAO Doc 8643 designators -> the designators ADS-B databases use. flysfo lists
# American Eagle (SkyWest) E-175s as 'E175' (observed 24 Sep 15:24Z, SKW6274 = AAL6274), while ADS-B says 'E75L';
# Doc 8643 designates the Embraer 175 as E75L (long wing) / E75S (short wing).
TYPE_EQUIV = {'E175': {'E75L', 'E75S'}}


def type_match(adsb_t, types):
    return any(adsb_t == t or adsb_t in TYPE_EQUIV.get(t, ()) for t in types)


def norm_cs(c):
    """ADS-B callsigns often zero-pad the number (CAL003, SJX011); flysfo does not (CAL3, SJX11) (gate_truth §8)."""
    c = (c or '').strip().upper()
    m = CS_RE.match(c)
    return m.group(1) + m.group(2) + m.group(3) if m else c


def stand_base(n):
    """SFO AODB stand names add a letter to some gate numbers (A1V, A4T, B5S, C9V, E10U, G13S ...): the gate."""
    m = re.match(r'^([A-G]\d+)[A-Z]?$', n or '')
    return m.group(1) if m else n


def _ts(s):
    return int(dt.datetime.fromisoformat(s).timestamp()) if s else None


def compact_flight(r):
    al, ap = r.get('airline') or {}, r.get('airport') or {}
    kind = 'A' if r.get('flight_kind') == 'Arrival' else 'D' if r.get('flight_kind') == 'Departure' else r.get('flight_kind')
    segs = sorted(r.get('routes') or [], key=lambda x: x.get('route_seq') or 0)
    route = []
    if segs:   # chain the segments: origin of the first leg that is nobody's destination, then follow
        by_o = {(s.get('origin_airport') or {}).get('iata_code'): s for s in segs}
        dests = {(s.get('destination_airport') or {}).get('iata_code') for s in segs}
        start = next((o for o in by_o if o not in dests), None)
        seen = set()
        while start and start not in seen:
            seen.add(start)
            route.append(start)
            nxt = by_o.get(start)
            start = (nxt.get('destination_airport') or {}).get('iata_code') if nxt else None
    return {
        'id': r.get('flight_id'), 'kind': kind, 'cs': r.get('callsign'),
        'fn': f"{al.get('iata_code') or ''} {r.get('flight_number') or ''}".strip(),
        'al': al.get('airline_display_name') or al.get('airline_name'), 'al_icao': al.get('icao_code'), 'al_iata': al.get('iata_code'),
        'type': (r.get('aircraft_transport_type') or {}).get('icao_code'),
        'gate': (r.get('gate') or {}).get('gate_number'), 'term': (r.get('terminal') or {}).get('terminal_code'),
        'stands': [[(s.get('stand') or {}).get('stand_name'), _ts(s.get('start_time')), _ts(s.get('end_time'))] for s in r.get('stands') or []],
        'remark': r.get('remark'),
        'aod': [_ts(r.get('scheduled_aod_time')), _ts(r.get('estimated_aod_time')), _ts(r.get('actual_aod_time'))],
        'blk': [_ts(r.get('scheduled_in_off_block_time')), _ts(r.get('estimated_in_off_block_time')), _ts(r.get('actual_in_off_block_time'))],
        'rwy': [_ts(r.get('scheduled_runway_time')), _ts(r.get('estimated_runway_time')), _ts(r.get('actual_runway_time'))],
        'other': {'iata': ap.get('iata_code'), 'icao': ap.get('icao_code'), 'name': ap.get('airport_name'), 'city': ap.get('airport_city')},
        'route': route, 'linked': r.get('linked_flight_id'),
        'cshare': [f"{(c.get('marketing_airline') or {}).get('iata_code') or ''} {c.get('marketing_flight_number') or ''}".strip() for c in r.get('code_shares') or []],
        'belt': (r.get('baggage_carousel') or {}).get('carousel_name'), 'nature': r.get('flight_nature'),
        'diverted': (r.get('diverted_airport') or {}).get('iata_code') if isinstance(r.get('diverted_airport'), dict) else r.get('diverted_airport'),
    }


def _t_of(v):
    """best of [scheduled, estimated, actual]"""
    return v[2] or v[1] or v[0]


class Gates:
    """flysfo.com flight status (SFO's own gate and stand plan), fetched at most every 10 min while a client asks.

    Terms: none published (gate_truth §7); robots.txt does not exclude the path. So: gzip, an identifying
    User-Agent, conditional GET when the server offers a validator, >= 10 min between fetches (shared with
    tools/live/gatecheck.py through the newest cached file's mtime), only on demand, --no-sfo-gates to disable,
    visible attribution. The raw JSON never leaves this machine (cached in refs/cache/gate_truth, gitignored).
    """
    URL = 'https://www.flysfo.com/flysfo/api/flight-status'
    MIN_INTERVAL = 600.0
    DEMAND_S = 900.0

    def __init__(self, enabled=True, cache_dir=os.path.join(CACHE_DIR, 'gate_truth'), hub=None, routes=None, replay_clock=None):
        self.enabled, self.dir, self.hub, self.routes = enabled, cache_dir, hub, routes
        self.replay = replay_clock          # a Clock: replay mode serves cached snapshots matching the recording
        self.lock = threading.Lock()
        self.flights, self.by_cs = {}, {}
        self.fetched_at = self.last_attempt = 0.0
        self.last_update, self.error, self.fetching = None, None, False
        self.validators = {}
        self.demand = 0.0
        self.snap_path = None
        self.last_fetch = None
        self.n_records = 0
        # resolved regional aliases, kept while the aircraft may still be shown (it can fall silent at its gate): callsign ->
        # (alias record, source-time expiry). Review round 2: SKW5899 -> UAL5899 vanished from /api/gates once the aircraft
        # was silent at F5 inside SFO's own stand window, and the card lost 'per SFO' and 'UA 5899'
        self.alias_mem = {}
        if enabled and not replay_clock:
            self._load_newest()

    # -- cache
    def _files(self):
        fs = glob.glob(os.path.join(self.dir, 'flysfo_api_flight-status_*.json*'))
        return sorted(fs, key=lambda p: re.search(r'_(\d{8}T\d{6}Z)', p).group(1))

    @staticmethod
    def _file_time(p):
        return dt.datetime.strptime(re.search(r'_(\d{8}T\d{6}Z)', p).group(1), '%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).timestamp()

    def _read(self, p):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as f:
            return json.load(f)

    def _load_newest(self):
        fs = self._files()
        if fs and time.time() - self._file_time(fs[-1]) < 4 * 3600:
            try:
                self._ingest(self._read(fs[-1]), self._file_time(fs[-1]), fs[-1])
            except Exception as e:
                self.error = f'cache: {e}'[:200]

    def _ingest(self, d, fetched_at, path=None, union=None):
        recs = [r for r in (d.get('data') or []) if not r.get('is_code_share')]   # code-share duplicates
        flights = dict(union or {})
        for r in recs:
            f = compact_flight(r)
            if f['id']:
                flights[f['id']] = f
        by_cs = {}
        for f in flights.values():
            by_cs.setdefault(norm_cs(f['cs']), []).append(f['id'])
        with self.lock:
            self.flights, self.by_cs = flights, by_cs
            self.fetched_at, self.last_update, self.snap_path = fetched_at, d.get('last_update'), path
            self.n_records = len(recs)

    # -- fetching
    def want(self):
        self.demand = time.time()
        if not self.enabled or self.replay is not None or self.fetching:
            return
        newest = self._files()
        newest_t = os.path.getmtime(newest[-1]) if newest else 0.0
        if newest and newest[-1] != self.snap_path and time.time() - newest_t < self.MIN_INTERVAL:
            self.fetching = True                  # another tool fetched < 10 min ago: use its copy
            threading.Thread(target=self._load_file, args=(newest[-1],), daemon=True).start()
            return
        if time.time() - max(self.last_attempt, newest_t, self.fetched_at) < self.MIN_INTERVAL:
            return
        self.fetching = True
        self.last_attempt = time.time()
        threading.Thread(target=self._fetch, daemon=True).start()

    def _load_file(self, p):
        try:
            self._ingest(self._read(p), self._file_time(p), p)
        except Exception as e:
            self.error = f'cache: {e}'[:200]
        finally:
            self.fetching = False

    def _fetch(self):
        try:
            hdr = {'Accept': 'application/json', 'Accept-Encoding': 'gzip'}
            if self.validators.get('etag'):
                hdr['If-None-Match'] = self.validators['etag']
            if self.validators.get('last-modified'):
                hdr['If-Modified-Since'] = self.validators['last-modified']
            t0 = time.time()
            code, hd, body = http_get(self.URL, timeout=60, headers=hdr)
            self.validators = {k: hd[k] for k in ('etag', 'last-modified') if hd.get(k)}
            self.last_fetch = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0)), 'status': code,
                               'wire_bytes': hd.get('_wire_bytes'), 'content_encoding': hd.get('content-encoding'),
                               'json_bytes': len(body), 'seconds': round(time.time() - t0, 2),
                               'validators_offered': sorted(self.validators) or None}
            if code == 304:
                self.fetched_at = time.time()
                self.error = None
                return
            if code != 200:
                raise IOError(f'HTTP {code}')
            d = json.loads(body)
            ts = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
            os.makedirs(self.dir, exist_ok=True)
            p = os.path.join(self.dir, f'flysfo_api_flight-status_{ts}.json.gz')
            with gzip.open(p, 'wb') as f:
                f.write(body)
            self._ingest(d, time.time(), p)
            self.error = None
        except Exception as e:
            self.error = f'{time.strftime("%H:%M:%S", time.gmtime())}Z {e}'[:200]
        finally:
            self.fetching = False

    def _replay_load(self, T):
        """Replay: the union of every cached snapshot fetched up to 30 min after the recording time T (newest version
        of each flight wins), so the recorded traffic is shown with the plan SFO published at the time."""
        fs = [p for p in self._files() if self._file_time(p) <= T + 1800]
        if not fs:
            return
        if self.snap_path == fs[-1]:
            return
        union, d = {}, None
        for p in fs[-8:]:   # a snapshot reaches ~4 h back; 8 x >= 10 min covers the recent ones
            try:
                d = self._read(p)
            except Exception:
                continue
            for r in d.get('data') or []:
                if not r.get('is_code_share'):
                    f = compact_flight(r)
                    union[f['id']] = f
        if d is None:
            self.snap_path = fs[-1]      # unreadable: do not retry on every request
            return
        self._ingest(d, self._file_time(fs[-1]), fs[-1], union)

    # -- payload
    def payload(self, extra_cs=()):
        if not self.enabled:
            return {'enabled': False, 'reason': 'disabled with --no-sfo-gates', 'attribution': ATTRIBUTION['gates']}
        wall = time.time()
        clock = self.replay or Clock()
        T = clock.to_src(wall)
        if self.replay is not None:
            self._replay_load(T)
        with self.lock:
            flights, by_cs = self.flights, self.by_cs
        W = lambda t: None if t is None else int(round(clock.to_wall(t)))
        out_f, keep = {}, set()

        def sel(ids):
            arrs = [flights[i] for i in ids if flights[i]['kind'] == 'A']
            deps = [flights[i] for i in ids if flights[i]['kind'] == 'D']
            best_a = best_d = None
            ca = cd = 1e18
            for f in arrs:        # arrived (<= 14 h ago) preferred over arriving (<= 6 h ahead), 2:1
                t = _t_of(f['blk']) or _t_of(f['aod'])
                if t is None or not (T - 14 * 3600 <= t <= T + 6 * 3600):
                    continue
                c = (T - t) * 0.5 if t <= T else (t - T)
                if c < ca:
                    best_a, ca = f, c
            for f in deps:        # departing (<= 14 h ahead) preferred over departed (<= 3 h ago), 1:2
                t = _t_of(f['blk']) or _t_of(f['aod'])
                if t is None or not (T - 3 * 3600 <= t <= T + 14 * 3600):
                    continue
                c = (t - T) if t >= T else (T - t) * 2
                if c < cd:
                    best_d, cd = f, c
            return best_a, best_d

        def stand_now(f):
            if not f:
                return None
            for n, a, b in f['stands']:
                if a is not None and b is not None and a - 60 <= T <= b + 60:
                    return {'name': n, 'base': stand_base(n), 'from': W(a), 'to': W(b), 'how': 'window'}
            return None

        by_callsign = {}
        for cs, ids in by_cs.items():
            a, d = sel(ids)
            e = {'flights': ids}
            if a:
                e['arr'] = a['id']
            if d:
                e['dep'] = d['id']
            if a and not d and a.get('linked') in flights:
                e['dep'], e['dep_via'] = a['linked'], 'linked'
            if d and not a:
                la = next((f for f in flights.values() if f.get('linked') == d['id'] and f['kind'] == 'A'), None)
                if la:
                    e['arr'], e['arr_via'] = la['id'], 'linked'
            st = stand_now(flights.get(e.get('arr'))) or stand_now(flights.get(e.get('dep')))
            if st:
                e['stand'] = st
            by_callsign[cs] = e
        # regional operator callsigns (ADS-B) -> marketing flights (flysfo)
        # Scoring (data, not an assumed partner table): +2 when the ADS-B type agrees with SFO's type for the flight, 0 when it
        # differs (flagged: an aircraft-database type must not veto an otherwise unique flight-number match -- review round 2:
        # N670QX is listed as E195 in the adsb.fi database, SFO and Horizon's fleet say E175, and QXE2139 -> ASA2139 was
        # rejected); +2 / -2 when the VRS route agrees / disagrees. Mapped when the top candidate is unique and scores >= 0,
        # or when it is the only candidate and its SFO stand window covers now.
        aliases = {}
        live = self.hub.current_callsigns() if self.hub else {}
        for cs in set(live) | {c.strip().upper() for c in extra_cs if c.strip()}:
            m = CS_RE.match(cs)
            if not m or m.group(1) not in REGIONAL:
                continue
            num = m.group(2)
            cands = [c for c, ids in by_cs.items() if (CS_RE.match(c) and CS_RE.match(c).group(2) == num
                                                         and not CS_RE.match(c).group(3) and CS_RE.match(c).group(1) not in REGIONAL)]
            if not cands:
                continue
            adsb_t = (live.get(cs) or {}).get('t')
            vrs = self.routes.cached(cs) if self.routes else None
            vrs_codes = set((vrs or {}).get('airport_codes', 'unknown').split('-')) - {'unknown', ''}
            scored = []
            for c in cands:
                e = by_callsign.get(c) or {}
                fl = [flights[i] for i in (e.get('arr'), e.get('dep')) if i in flights]
                types = {f['type'] for f in fl if f['type']}
                others = {f['other']['icao'] for f in fl if f['other'].get('icao')}
                chk, score = {}, 0
                if adsb_t and types:
                    tm = type_match(adsb_t, types)
                    chk['type'] = 'agree' if tm else 'differ'
                    if not tm:
                        chk['types'] = {'adsb': adsb_t, 'sfo': sorted(types)}
                    score += 2 if tm else 0
                if vrs_codes and others:
                    ok = 'KSFO' in vrs_codes and bool(vrs_codes & others)
                    chk['route'] = 'agree' if ok else 'differ'
                    score += 2 if ok else -2
                scored.append((score, c, chk))
            scored.sort(key=lambda x: -x[0])
            top = scored[0]
            unique = len(scored) == 1 or top[0] > scored[1][0]
            ok = unique and top[0] >= 0
            how = 'regional flight number'
            if not ok and len(scored) == 1:
                e = by_callsign.get(top[1]) or {}
                st = e.get('stand')
                if st and st.get('from') is not None and st.get('to') is not None:
                    ok, how = True, 'only candidate, SFO stand window covers now'
            rec = {'to': top[1] if ok else None, 'candidates': [s[1] for s in scored], 'checks': top[2], 'score': top[0], 'how': how}
            aliases[cs] = rec
            if ok:
                e = by_callsign.get(top[1]) or {}
                until = max(T + 3 * 3600, ((e.get('stand') or {}).get('to') or 0) and clock.to_src((e.get('stand') or {}).get('to')) + 1800)
                self.alias_mem[cs] = (rec, until)
        # held aliases: resolved earlier for an aircraft that is no longer on the feed (silent at its gate), until 3 h after
        # the resolution or 30 min after its stand window, whichever is later
        for cs, (rec, until) in list(self.alias_mem.items()):
            if until < T:
                del self.alias_mem[cs]
            elif cs not in aliases and rec.get('to') in by_callsign:
                aliases[cs] = dict(rec, held=True)
        for e in by_callsign.values():
            keep.update(i for i in (e.get('arr'), e.get('dep')) if i)
        # stand windows: current and upcoming (a turn's arrival and departure carry the same list: de-duplicate)
        turns = {}
        for f in flights.values():
            for n, a, b in f['stands']:
                if a is None or b is None or b < T - 60 or a > T + 12 * 3600:
                    continue
                t = turns.setdefault((n, a, b), {'from': W(a), 'to': W(b), 'arr': None, 'dep': None, 'type': f['type'], 'cs': []})
                t['arr' if f['kind'] == 'A' else 'dep'] = f['id']
                if f['cs'] not in t['cs']:
                    t['cs'].append(f['cs'])
                keep.add(f['id'])
        by_stand = {}
        for (n, a, b), t in sorted(turns.items(), key=lambda kv: kv[0][1]):
            e = by_stand.setdefault(n, {'base': stand_base(n), 'now': [], 'next': []})
            if a - 60 <= T <= b + 60:
                e['now'].append(t)
            elif len(e['next']) < 2:
                e['next'].append(t)
        for i in keep:
            f = dict(flights[i])
            f['stands'] = [[n, W(a), W(b)] for n, a, b in f['stands']]
            f['aod'], f['blk'], f['rwy'] = [W(x) for x in f['aod']], [W(x) for x in f['blk']], [W(x) for x in f['rwy']]
            out_f[i] = f
        return {
            'enabled': True, 'replay': self.replay is not None, 'now': int(wall),
            'fetched_at': W(self.fetched_at) if self.fetched_at else None, 'last_update': self.last_update,
            'age_s': round(T - self.fetched_at) if self.fetched_at else None,
            'next_fetch_after_s': None if self.replay else round(max(0, self.MIN_INTERVAL - (wall - max(self.last_attempt, self.fetched_at)))),
            'error': self.error, 'records': self.n_records,
            'flights': out_f, 'byCallsign': by_callsign, 'aliases': aliases, 'byStand': by_stand,
            'norm': 'callsign keys: ICAO airline code + flight number without leading zeros + suffix (CAL003 -> CAL3)',
            'verify': {'flysfo': 'https://www.flysfo.com/flight-info/flight-status?type={arrivals|departures}&search={flight number}',
                       'flightaware': 'https://www.flightaware.com/live/flight/{ICAO callsign}',
                       'raw': self.URL},
            'source': 'flysfo.com flight status (SFO AODB gates and stand allocations)', 'attribution': ATTRIBUTION['gates'],
        }

    def status(self):
        return {'enabled': self.enabled, 'replay': self.replay is not None, 'flights': len(self.flights),
                'fetched_at': self.fetched_at or None, 'last_update': self.last_update, 'error': self.error,
                'fetching': self.fetching, 'last_fetch': self.last_fetch,
                'demand_age_s': round(time.time() - self.demand) if self.demand else None}


# ------------------------------------------------------------------------------------------------ METAR
class Metar:
    def __init__(self, replay_clock=None):
        self.cache, self.replay = {}, replay_clock
        self.lock = threading.Lock()

    def _cached_obs(self, T):
        """Replay: the latest cached KSFO METAR observed at or before recording time T (aviationweather JSON files
        saved by tools/live/replay_wx.py and analyze_feeds.py)."""
        best = None
        for p in glob.glob(os.path.join(CACHE_DIR, 'replay', 'wx', 'metar_*.json')) + glob.glob(os.path.join(CACHE_DIR, 'feeds', 'metar_ksfo*.json')):
            try:
                for m in json.load(open(p)):
                    if m.get('obsTime') and m['obsTime'] <= T and (best is None or m['obsTime'] > best['obsTime']):
                        best = m
            except Exception:
                pass
        return best

    def _fill_cache(self):
        """Replay of a recent recording with no cached METAR near its time: save the last 24 h of KSFO METARs once
        (aviationweather.gov JSON, `hours` is its documented look-back) in the replay_wx.py cache, at most every 10 min."""
        if time.time() - getattr(self, '_filled', 0) < 600:
            return
        self._filled = time.time()
        try:
            code, _, body = http_get('https://aviationweather.gov/api/data/metar?ids=KSFO&format=json&hours=24', timeout=20)
            if code == 200 and body.strip().startswith(b'['):
                d = os.path.join(CACHE_DIR, 'replay', 'wx')
                os.makedirs(d, exist_ok=True)
                open(os.path.join(d, time.strftime('metar_ksfo_%Y%m%dT%H%M%SZ.json', time.gmtime())), 'wb').write(body)
        except Exception as e:
            print('metar cache fill failed:', e, file=sys.stderr)

    def get(self, ids, fmt):
        if self.replay is not None and ids == 'KSFO':
            T = self.replay.to_src(time.time())
            m = self._cached_obs(T)
            if (m is None or T - m['obsTime'] > 5400) and time.time() - T < 23 * 3600:
                self._fill_cache()
                m = self._cached_obs(T)
            if m and T - m['obsTime'] <= 5400:   # METARs are hourly (xx56Z); older than 90 min: none is better
                return (json.dumps([m]).encode(), 'application/json') if fmt == 'json' else (m['rawOb'].encode(), 'text/plain')
            raise IOError('no cached KSFO METAR within 90 min of the replay time')   # never today's weather in a replay
        key = (ids, fmt)
        with self.lock:
            c = self.cache.get(key)
            if c and time.time() - c[0] < 60:
                return c[1], c[2]
        code, hd, body = http_get(f'https://aviationweather.gov/api/data/metar?ids={urllib.parse.quote(ids)}&format={fmt}&hours=2', timeout=15)
        if code != 200:
            raise IOError(f'HTTP {code}')
        ctype = 'application/json' if fmt == 'json' else 'text/plain'
        with self.lock:
            self.cache[key] = (time.time(), body, ctype)
        return body, ctype


# ------------------------------------------------------------------------------------------------ replay
def replay_records(root, t_from=None, t_until=None):
    """Recorded provider responses of all providers in time order (streamed hour file by hour file)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
    import recio

    def one(pid):
        for p in sorted(glob.glob(os.path.join(root, f'{pid}_*.jsonl.gz'))):
            h = re.search(r'_(\d{8}_\d{2})\.jsonl', p)
            if h and t_from is not None:
                hs = dt.datetime.strptime(h.group(1), '%Y%m%d_%H').replace(tzinfo=dt.timezone.utc).timestamp()
                if hs + 3600 < t_from:
                    continue
            last = -1.0
            for r in recio.lines(p):
                if 'd' not in r or not isinstance(r.get('d'), dict):
                    continue
                t = r.get('tr') or r['t']
                if (t_from is not None and t < t_from) or t <= last:   # overlapping members: keep time order
                    continue
                if t_until is not None and t > t_until:
                    return
                last = t
                yield t, pid, r
    gens = [one(pid) for pid in PROVIDERS]
    for t, pid, r in heapq.merge(*gens, key=lambda x: x[0]):
        yield t, pid, r


def run_replay(hub, root, speed, t_from, t_until, loop, clock_holder):
    while True:
        it = replay_records(root, t_from, t_until)
        first = next(it, None)
        if first is None:
            print('replay: no records in', root, 'from', t_from)
            return
        clock = Clock(time.time(), first[0], speed)
        clock_holder.wall0, clock_holder.src0, clock_holder.speed = clock.wall0, clock.src0, clock.speed
        print('replay: from', time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(first[0])), f'at {speed}x', flush=True)
        n = 0
        for t, pid, r in _chain(first, it):
            due = clock.to_wall(t)
            dtw = due - time.time()
            if dtw > 0:
                time.sleep(dtw)
            prov = PROVIDERS[pid]
            t0 = clock.to_wall(r['t'])
            hub.ingest(prov, t0, time.time(), r['d'], clock=clock, scale=1.0 / speed)
            n += 1
            hub.replay_pos = t
        print(f'replay: finished ({n} responses)', flush=True)
        if not loop:
            return
        hub.reset()


def _chain(first, it):
    yield first
    yield from it


# ------------------------------------------------------------------------------------------------ HTTP server
DENY_TOP = {'refs', 'tools', 'node_modules', 'out', 'jobs'}          # never served (licensed/cached data, tooling)
DENY_PREFIX = ('docs/qa/ref',)                                       # Google-imagery crops: reference only
GZIP_TYPES = ('.js', '.mjs', '.css', '.html', '.json', '.svg', '.txt', '.csv', '.md')


class StaticGzip:
    def __init__(self):
        self.c, self.lock = {}, threading.Lock()

    def get(self, path):
        st = os.stat(path)
        k = (path, st.st_mtime_ns, st.st_size)
        with self.lock:
            v = self.c.get(path)
            if v and v[0] == k:
                return v[1]
        b = gzip.compress(open(path, 'rb').read(), 6)
        with self.lock:
            self.c[path] = (k, b)
        return b


def make_handler(app):
    hub, gates, routes, metar = app['hub'], app['gates'], app['routes'], app['metar']
    sgz = StaticGzip()

    class H(SimpleHTTPRequestHandler):
        server_version = 'sfo-live-relay/' + VERSION

        def __init__(self, *a, **k):
            super().__init__(*a, directory=ROOT, **k)

        def log_message(self, fmt, *args):
            if app.get('quiet') or not self.path.startswith('/api/') or self.path.startswith('/api/stream'):
                return
            super().log_message(fmt, *args)

        def _send(self, body, ctype='application/json', code=200, extra=None):
            gz = len(body) > 1400 and 'gzip' in (self.headers.get('Accept-Encoding') or '')
            if gz:
                body = gzip.compress(body, 5)
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Cache-Control', 'no-store')
            if gz:
                self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(body)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def _json(self, obj, code=200):
            return self._send(obj if isinstance(obj, bytes) else json.dumps(obj, separators=(',', ':')).encode(), code=code)

        def end_headers(self):
            if not self.path.startswith('/api/'):
                self.send_header('Cache-Control', 'no-cache')
            super().end_headers()

        def _denied(self, upath):
            p = urllib.parse.unquote(upath).lstrip('/')
            parts = [s for s in p.split('/') if s]
            if any(s.startswith('.') for s in parts):
                return True
            return bool(parts) and (parts[0] in DENY_TOP or any(p.startswith(d) for d in DENY_PREFIX))

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            try:
                if u.path == '/api/ping':
                    return self._json({'sfolive': 1, 'v': VERSION, 'mode': hub.mode, 'stream': True, 'delta': True,
                                       'features': {'gates': gates.enabled, 'routes': routes.mode != 'off', 'metar': True,
                                                    'replay': app.get('replay_info')},
                                       'providers': [PROVIDERS[p]['name'] for p in PROVIDERS], 'attribution': ATTRIBUTION})
                if u.path == '/api/adsb':
                    hub.touch()
                    with hub.lock:
                        b = hub.full
                    return self._json(b)
                if u.path == '/api/stream':
                    return self._stream(q.get('delta', ['0'])[0] not in ('0', '', 'false'))
                if u.path == '/api/status':
                    return self._json(app_status(app))
                if u.path == '/api/gates':
                    gates.want()
                    t_w = time.time()
                    while gates.fetching and not gates.flights and time.time() - t_w < 20:   # first fetch ~3 s
                        time.sleep(0.2)
                    cs = ','.join(q.get('cs', [])).split(',')
                    return self._json(gates.payload(cs))
                if u.path == '/api/metar':
                    ids = re.sub(r'[^A-Za-z0-9,]', '', q.get('ids', ['KSFO'])[0])[:32] or 'KSFO'
                    fmt = 'json' if q.get('format', ['raw'])[0] == 'json' else 'raw'
                    try:
                        body, ctype = metar.get(ids, fmt)
                    except Exception as e:
                        return self._json({'error': str(e)[:200]}, 502)
                    return self._send(body, ctype)
                if u.path.startswith('/api/'):
                    return self._json({'error': 'unknown endpoint'}, 404)
            except (BrokenPipeError, ConnectionResetError):
                return
            if self._denied(u.path):
                return self.send_error(404)
            fs = self.translate_path(u.path)
            if os.path.isfile(fs) and fs.endswith(GZIP_TYPES) and 'gzip' in (self.headers.get('Accept-Encoding') or ''):
                try:
                    return self._static_gz(fs, sgz.get(fs))
                except OSError:
                    pass
            return super().do_GET()

        def _static_gz(self, fs, body):
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(fs))
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Vary', 'Accept-Encoding')
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self):
            if self._denied(urllib.parse.urlparse(self.path).path):
                return self.send_error(404)
            return super().do_HEAD()

        def list_directory(self, path):
            self.send_error(404)       # no directory listings

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == '/api/routeset':
                n = int(self.headers.get('Content-Length') or 0)
                try:
                    j = json.loads(self.rfile.read(min(n, 200000)) or b'{}')
                    planes = [p for p in (j.get('planes') or []) if isinstance(p, dict) and p.get('callsign')][:200]
                except ValueError:
                    return self._json({'error': 'bad JSON'}, 400)
                if routes.mode == 'off':
                    return self._json({'error': 'routes disabled'}, 503)
                try:
                    res, src = routes.lookup(planes)
                except Exception as e:
                    return self._json({'error': str(e)[:200]}, 503)   # the client must not cache this as "no route"
                return self._json(res)
            self.send_error(404)

        def _stream(self, delta):
            hub.touch()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Accel-Buffering', 'no')
            self.end_headers()
            with hub.lock:
                hub.clients += 1
                seq, data = hub.seq, hub.full
            last_full = time.time()
            try:
                self.wfile.write(b'retry: 2000\n\nevent: adsb\ndata: ' + data + b'\n\n')
                self.wfile.flush()
                while True:
                    with hub.lock:
                        if hub.seq == seq:
                            hub.cond.wait(15.0)
                        if hub.seq == seq:
                            msg = b': keepalive\n\n'
                        else:
                            if delta and hub.seq == seq + 1 and time.time() - last_full < FULL_EVERY:
                                msg = b'event: delta\ndata: ' + hub.delta + b'\n\n'
                            else:
                                msg = b'event: adsb\ndata: ' + hub.full + b'\n\n'
                                last_full = time.time()
                            seq = hub.seq
                    hub.touch()
                    self.wfile.write(msg)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with hub.lock:
                    hub.clients -= 1

    return H


def app_status(app):
    hub = app['hub']
    return {'relay': {'v': VERSION, 'uptime_s': round(time.time() - app['t_start']), 'ua': UA,
                      'replay': app.get('replay_info'),
                      'replay_position_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(hub.replay_pos)) if getattr(hub, 'replay_pos', None) else None,
                      'record_dir': app.get('record_dir')},
            'providers': {p.p['name']: p.status() for p in hub.pollers.values()},
            'merge': hub.status(), 'gates': app['gates'].status(), 'routes': app['routes'].status()}


def parse_time(s):
    if s is None:
        return None
    if re.match(r'^\d+(\.\d+)?$', s):
        return float(s)
    s = s.replace('Z', '+00:00')
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.timestamp()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--host', default='127.0.0.1', help='0.0.0.0 to open it from a phone on the same Wi-Fi')
    ap.add_argument('--radius', type=int, default=40, help='NM around the SFO ARP (default 40: downwind/base of every approach)')
    ap.add_argument('--no-sfo-gates', action='store_true', help='never contact flysfo.com; /api/gates reports disabled')
    ap.add_argument('--routes', default='auto', choices=['auto', 'api', 'mirror', 'off'],
                    help='auto: adsb.lol routeset API, falling back to the VRS mirror (default)')
    ap.add_argument('--record', help='also append every provider response to this directory (record.py format)')
    ap.add_argument('--replay', help='directory of recordings (tools/live/record.py) to replay instead of polling')
    ap.add_argument('--speed', type=float, default=1.0, help='replay speed factor')
    ap.add_argument('--skip', type=float, default=0.0, help='seconds of the recording to skip')
    ap.add_argument('--from', dest='t_from', help='replay start (UTC ISO time or epoch s), e.g. 2026-09-24T14:00Z')
    ap.add_argument('--until', dest='t_until', help='replay end (UTC ISO time or epoch s)')
    ap.add_argument('--loop', action='store_true', help='restart the replay at its end')
    ap.add_argument('--quiet', action='store_true', help='no request log')
    a = ap.parse_args()

    hub = Hub('replay' if a.replay else 'live')
    replay_clock = Clock() if a.replay else None
    if a.replay:
        replay_clock.src0 = replay_clock.wall0 = time.time()     # replaced when the replay starts
    routes = Routes('off' if a.routes == 'off' else a.routes)
    gates = Gates(enabled=not a.no_sfo_gates, hub=hub, routes=routes, replay_clock=replay_clock)
    metar = Metar(replay_clock)
    app = {'hub': hub, 'gates': gates, 'routes': routes, 'metar': metar, 't_start': time.time(), 'quiet': a.quiet}
    writer = None
    if a.record:
        pidf = os.path.join(a.record, 'recorder.pid')
        if os.path.exists(pidf):
            try:
                other = int(open(pidf).read().strip())
            except ValueError:
                other = None
            if other and other != os.getpid() and pid_alive(other):
                sys.exit(f'--record: tools/live/record.py (pid {other}) is already writing to {a.record}; stop it first '
                         'or record elsewhere (two writers would interleave the hourly gzip files)')
        writer = RecordWriter(a.record)
        hub.ext.append(writer.write)
        app['record_dir'] = a.record
        open(os.path.join(a.record, 'relay_record.pid'), 'w').write(str(os.getpid()))   # record.py checks it
    if a.replay:
        t_from = parse_time(a.t_from)
        if t_from is None:
            first = next(replay_records(a.replay), None)
            t_from = (first[0] if first else 0) + a.skip
        else:
            t_from += a.skip
        app['replay_info'] = {'dir': a.replay, 'speed': a.speed, 'from': t_from, 'loop': a.loop}
        hub.replay_pos = None
        threading.Thread(target=run_replay, args=(hub, a.replay, a.speed, t_from, parse_time(a.t_until), a.loop, replay_clock),
                         daemon=True).start()
        hub.last_client = float('inf')
    else:
        active = (lambda: True) if writer else hub.active
        for pid, prov in PROVIDERS.items():
            p = Poller(prov, hub.on_result, ARP[0], ARP[1], a.radius, active=active)
            hub.wakes.append(p.wake)
            hub.pollers[pid] = p
            p.start()

    srv = ThreadingHTTPServer((a.host, a.port), make_handler(app))
    srv.daemon_threads = True

    def stop(*_):
        if writer:
            writer.close()
        threading.Thread(target=srv.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    host = 'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host
    print(f'SFO Live 3D relay {VERSION}: http://{host}:{a.port}/live.html  ({"replay of " + a.replay if a.replay else "live"})')
    print('ADS-B: adsb.lol (ODbL 1.0) + adsb.fi (personal non-commercial) · gates: '
          + ('flysfo.com (<= 1 fetch / 10 min while asked)' if not a.no_sfo_gates else 'off') + f' · routes: {a.routes}', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if writer:
            writer.close()
            try:
                os.remove(os.path.join(a.record, 'relay_record.pid'))
            except OSError:
                pass


if __name__ == '__main__':
    main()
