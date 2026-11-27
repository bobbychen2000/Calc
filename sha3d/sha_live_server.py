#!/usr/bin/env python3
# forked from sfo3d@e3218d6 sfo_live_server.py (design and helpers; SFO specifics removed, see below)
"""SHA Live 3D - local relay (Python 3 standard library only).

forked from sfo3d@e3218d6 sfo_live_server.py (design: one-off urllib client with a fixed User-Agent, the METAR upstream
cache with conditional requests, the gzip static cache, the deny rules, the handler shape and the /api/ping contract).
Stripped of every SFO specific: no SFO ARP or 40 NM radius, no FAA registry, no flysfo gate plan (/api/gates), no KSFO
METAR/TAF schedule, no adsb.fi poller (its terms forbid relicensing), no OpenSky (never called), no SSE stream or
merge (there is one provider and it polls every 180 s at the fastest), no replay of SFO recordings, and the owner's
repository URL is NOT in the User-Agent (docs/phase0/arch.md R9; the hwd3d pattern of a generic UA).

Serves the app and relays the few live data SHA can use, so the browser never talks to a provider directly:

  python3 sha_live_server.py [--port 8000] [--host 127.0.0.1]     then open http://localhost:8000/
  python3 sha_live_server.py --adsb                                 also relay adsb.lol (OFF by default, see below)
  python3 sha_live_server.py --no-metar                             never contact aviationweather.gov (offline)
  python3 sha_live_server.py --no-identity                          never serve the local identity overlay
  python3 sha_live_server.py --host 0.0.0.0 --identity-lan          also serve it to the LAN (personal use only, OD4)

Endpoints (also under /sha3d/api/..., where the page's relative 'api/...' URLs land; js/live/relay.js)
  /, /sha3d/          302 -> /sha3d/live.html?relay=1 (the plain WebGL2 page, working default Q7), query string kept
  /api/ping           {"shalive": 1, "v", "mode": "live", "dataNow", "features", "providers", "attribution", "ua"}
  /api/metar?ids=ZSSS[&format=json]   ZSSS METAR/SPECI of the last 26 h, newest first. JSON keeps only the identity and
                      time fields and the RAW TEXT {icaoId, metarType, obsTime, reportTime, receiptTime, rawOb}: the AWC
                      JSON weather fields are lossy for ZSSS (wspd = knots rounded from MPS, visib "6+" for 9999, wdir
                      "VRB"; docs/phase1/sources_sim.md s.3.3), so clients decode rawOb (js/env/wx/metar_zsss.js).
                      Upstream: aviationweather.gov Data API, at most ONE request per 10 min (conditional), cached;
                      only ZSSS is relayed (no open proxy). Headers X-Wx-Fetched (epoch s), X-Wx-Upstream-Error.
  /api/taf?ids=ZSSS[&format=json]     the current ZSSS TAF {icaoId, issueTime, validTimeFrom, validTimeTo, rawTAF};
                      same limit (one upstream request per 10 min)
  /api/adsb           adsb.lol point query around ZSSS, OPPORTUNISTIC: an upstream request is made only when a client
                      asks and the last one is at least 180 s old (adsb.lol keyless quota: 500 requests / day / IP, and the
                      local recorder may share the IP), and never more than --adsb-daily-max in any 24 h (default 200,
                      counted in out/relay/.state/, survives restarts). OFF unless --adsb: then {"enabled": false, "ac": []}.
                      Only records of type 'adsb_icao' are relayed, each labelled src 'obs' (observed); every other type
                      (mlat, tisb_*, adsr_*, mode_s, other, ...) is dropped and only counted in "excluded" (PLAN s.4:
                      never count 'other' as observed; the task keeps adsb_icao only).
  /api/status         upstream health, cache ages, quota use
  /api/observed_elsewhere?day=YYYY-MM-DD   LOCAL identity overlay (OD4; Phase 3 design s.3): the allow-listed fields of
                      refs/cache/observed_elsewhere/sha_observed_<day>.json through tools/sim/observed_overlay.py, never a
                      static path (refs/ stays unservable). {"available": false} when the day has no local file, with
                      --no-identity, or when the relay listens beyond loopback (--host) or the client is not on loopback,
                      unless --identity-lan is given; a malformed day is rejected (400). /api/ping lists the days in
                      features.identity. Nothing is cached on disk. DNS-rebinding guard (P3-A fix round 1, F4): without
                      --identity-lan the request's Host header must name localhost / 127.x / [::1] (with --identity-lan:
                      an IP literal, localhost or this machine's own host name), and a browser request marked
                      Sec-Fetch-Site: cross-site is refused; otherwise {"available": false} and features.identity [].

Static files: an allow-list (sha3d/live.html, live.css, js/**, data/**, and sfo3d's aircraft models and livery textures,
which the app loads by URL from ../sfo3d/data/), never refs/ (third-party caches), tools/, docs/, out/, jobs/ or dot
files. The relay serves the repository root so that ../sfo3d/data/models/ resolves from /sha3d/live.html.

Attribution strings for each provider: ATTRIBUTION below (also in /api/ping and the About panel, js/live/about.js).
"""
import argparse, datetime as dt, gzip, ipaddress, json, os, re, socket, sys, threading, time, urllib.error, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

VERSION = '0.1'
HERE = os.path.dirname(os.path.abspath(__file__))          # sha3d/
REPO = os.path.dirname(HERE)                                # repository root (serves /sha3d/... and /sfo3d/data/...)
APP_DIR = os.path.basename(HERE)                            # 'sha3d'
# frame origin = centre of RWY 18L/36R from the OSM runway ends (owner decision OD0; tools/common/frame.py, js/geo.js)
ZSSS = (31.19784885, 121.3362899)
# a generic, honest User-Agent (aviationweather.gov asks for a custom one); no names, no e-mail, no repository URL
UA = f'sha-live-3d-relay/{VERSION} (personal non-commercial visualisation; python-stdlib)'
AWC_BASE = 'https://aviationweather.gov/api/data/'          # NOAA/NWS Aviation Weather Center Data API
ADSBLOL_BASE = 'https://api.adsb.lol'                       # adsb.lol API (ODbL 1.0)
WX_MIN_INTERVAL = 600.0          # s: at most one upstream METAR request and one TAF request per 10 min (task P2e)
WX_HOURS = 26                    # METAR look-back requested, one upstream call (ZSSS every 30 min: ~53 reports, ~24 kB); 26 h =
                                 # the operating day + the 2 h runway-timeline anchor (Phase 3 design s.1.4, package P3-A)
ADSB_MIN_INTERVAL = 180.0        # s: adsb.lol never more often than this (PLAN s.6b Q10; keyless 500 / day)
ADSB_BACKOFF_MAX = 3600.0        # s: after HTTP 429 / errors the interval doubles up to this
ADSB_KEEP = ('hex', 'type', 'flight', 'r', 't', 'desc', 'lat', 'lon', 'alt_baro', 'alt_geom', 'gs', 'track', 'true_heading',
             'baro_rate', 'geom_rate', 'squawk', 'emergency', 'category', 'nav_qnh', 'seen_pos', 'seen', 'nic', 'version')
STATE_DIR = os.path.join(HERE, 'out', 'relay', '.state')    # gitignored (sha3d/.gitignore 'out/'), never served

ATTRIBUTION = {
    'metar': 'Weather: NOAA/NWS Aviation Weather Center (https://aviationweather.gov) data; the ZSSS reports are issued by '
             'the CAAC aviation meteorological service. Not official NOAA material.',
    'adsb': 'Aircraft positions (observed; only when the relay runs with --adsb): contains information from ADSB.lol '
            '(https://adsb.lol), made available under the Open Database License (ODbL 1.0, '
            'https://opendatacommons.org/licenses/odbl/1-0/). Only ADS-B (adsb_icao) records are shown as observed.',
}
PROVIDERS = {
    'awc': {'name': 'aviationweather.gov (NOAA/NWS AWC)', 'use': 'ZSSS METAR / TAF', 'limit': '1 request / 10 min each',
            'attribution': ATTRIBUTION['metar']},
    'adsblol': {'name': 'adsb.lol', 'use': 'observed aircraft near ZSSS (opportunistic point query)',
                'limit': '>= 180 s between requests, daily cap', 'attribution': ATTRIBUTION['adsb']},
}


def utc(t):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t)) if t else None


# ------------------------------------------------------------------------------------------------ HTTP client
def http_get(url, timeout=15.0, headers=None):
    """One request (urllib: honours HTTPS_PROXY / NO_PROXY). -> (status, {lower-case header: value}, body bytes).
    HTTP errors are returned, not raised. Every request carries the generic User-Agent."""
    h = {'User-Agent': UA, 'Accept-Encoding': 'gzip', 'Accept': 'application/json, text/plain;q=0.9'}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, hd, body = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        status, hd, body = e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b''
    if hd.get('content-encoding') == 'gzip' and body:
        body = gzip.decompress(body)
    return status, hd, body


# ------------------------------------------------------------------------------------------------ METAR / TAF
METAR_KEEP = ('icaoId', 'metarType', 'obsTime', 'reportTime', 'receiptTime', 'rawOb')
TAF_KEEP = ('icaoId', 'issueTime', 'bulletinTime', 'validTimeFrom', 'validTimeTo', 'rawTAF')


class Wx:
    """ZSSS METAR and TAF from the AWC Data API: one cached upstream entry per kind, refreshed on demand at most every
    WX_MIN_INTERVAL seconds (conditional If-None-Match / If-Modified-Since; on an error the last good list is kept and
    the next attempt again waits WX_MIN_INTERVAL). ZSSS reports every 30 min (:00 / :30), so 10 min is ample."""

    def __init__(self, base=AWC_BASE, enabled=True, min_interval=WX_MIN_INTERVAL):
        self.base, self.enabled, self.min_interval = base, enabled, min_interval
        self.lock = threading.Lock()
        self.up = {}               # kind -> {t (last attempt), fetched, etag, lastmod, body (list), err, requests}
        self.fetching = {}         # kind -> Event while an upstream request is in flight

    def _url(self, kind):
        if kind == 'metar':
            return f'{self.base}metar?ids=ZSSS&format=json&hours={WX_HOURS}'
        return f'{self.base}taf?ids=ZSSS&format=json'          # (the TAF endpoint has no 'hours' parameter)

    def get(self, kind):
        """-> cache entry dict (body = list, newest first). Raises IOError when nothing good was ever fetched."""
        if not self.enabled:
            raise IOError('weather relay disabled (--no-metar)')
        now = time.time()
        with self.lock:
            c = self.up.get(kind)
            due = c is None or now - c['t'] >= self.min_interval
            ev = self.fetching.get(kind)
            mine = due and ev is None
            if mine:
                ev = self.fetching[kind] = threading.Event()
        if not mine:
            if ev is not None and (c is None or not c.get('body')):
                ev.wait(20.0)                           # first fetch in flight: wait for it instead of failing
                with self.lock:
                    c = self.up.get(kind)
            if c and c.get('body') is not None:
                return c
            raise IOError((c or {}).get('err') or 'no ZSSS report yet')
        try:
            return self._fetch(kind, now)
        finally:
            with self.lock:
                self.fetching.pop(kind, None)
            ev.set()

    def _fetch(self, kind, now):
        with self.lock:
            c = self.up.get(kind)
            hdr = {}
            if c and c.get('etag'):
                hdr['If-None-Match'] = c['etag']
            if c and c.get('lastmod'):
                hdr['If-Modified-Since'] = c['lastmod']
        try:
            code, hd, body = http_get(self._url(kind), timeout=15, headers=hdr)
        except Exception as e:
            code, hd, body = None, {}, (type(e).__name__ + ': ' + str(e)).encode()
        with self.lock:
            c = self.up.get(kind) or {'requests': 0, 'body': None, 'fetched': None}
            c['t'] = now
            c['requests'] = c.get('requests', 0) + 1
            c['last_code'] = code
            if code == 304 and c.get('body') is not None:
                c.update(err=None, fetched=now, not_modified=c.get('not_modified', 0) + 1)
            elif code == 200 and body.strip().startswith(b'['):
                lst = json.loads(body)
                keep, key = (METAR_KEEP, 'obsTime') if kind == 'metar' else (TAF_KEEP, 'issueTime')
                lst = [{k: m[k] for k in keep if k in m} for m in lst if isinstance(m, dict) and m.get('icaoId', 'ZSSS') == 'ZSSS']
                lst.sort(key=lambda m: m.get(key) or 0, reverse=True)
                c.update(body=lst, err=None, fetched=now, etag=hd.get('etag'), lastmod=hd.get('last-modified'))
            elif code == 204 or (code == 200 and not body.strip()):
                c.update(body=c.get('body') or [], err=None, fetched=now)       # no report in the window
            else:
                c['err'] = f'HTTP {code}' if code else body.decode(errors='replace')[:160]
            self.up[kind] = c
            if c.get('body') is None:
                raise IOError(c['err'] or 'no ZSSS report yet')
            return c

    def payload(self, kind, fmt):
        c = self.get(kind)
        extra = {'X-Wx-Fetched': str(int(c.get('fetched') or 0))}
        if c.get('err'):
            extra['X-Wx-Upstream-Error'] = c['err']
        if fmt == 'json':
            return json.dumps(c['body'], separators=(',', ':')).encode(), 'application/json', extra
        field = 'rawOb' if kind == 'metar' else 'rawTAF'
        lines = [m[field] for m in c['body'] if m.get(field)]
        if kind == 'taf':
            lines = lines[:1]
        return '\n'.join(lines).encode(), 'text/plain; charset=utf-8', extra

    def status(self):
        with self.lock:
            out = {}
            for k in ('metar', 'taf'):
                c = self.up.get(k)
                out[k] = None if not c else {'requests': c.get('requests'), 'last_attempt_utc': utc(c.get('t')),
                                             'fetched_utc': utc(c.get('fetched')), 'last_code': c.get('last_code'),
                                             'reports': len(c['body']) if c.get('body') is not None else None,
                                             'error': c.get('err'), 'not_modified': c.get('not_modified', 0)}
            return {'enabled': self.enabled, 'min_interval_s': self.min_interval, **out}


# ------------------------------------------------------------------------------------------------ adsb.lol (optional)
class Adsb:
    """Opportunistic adsb.lol point query around ZSSS. Never on a timer: an upstream request happens only inside a client's
    /api/adsb call, when the last request is >= interval old (>= 180 s; doubled after a 429 or an error, up to 1 h, or
    longer per Retry-After) and fewer than daily_max requests were made in the last 24 h (persisted in STATE_DIR so a
    restart cannot reset it). Concurrent callers get the cached list while one request is in flight."""

    def __init__(self, enabled=False, base=ADSBLOL_BASE, radius_nm=60, interval=ADSB_MIN_INTERVAL, daily_max=200, state_dir=STATE_DIR):
        self.enabled = bool(enabled)
        self.base = base.rstrip('/')
        self.radius_nm = int(max(1, min(250, radius_nm)))
        self.interval = max(ADSB_MIN_INTERVAL, float(interval))     # the 180 s floor cannot be lowered
        self.cur_interval = self.interval
        self.daily_max = int(max(0, daily_max))
        self.state_file = os.path.join(state_dir, 'adsblol_requests.json')
        self.lock = threading.Lock()
        self.busy = False
        self.last_req = 0.0
        self.not_before = 0.0
        self.last = None              # last good payload (dict)
        self.last_code, self.last_error = None, None
        self.requests = self._load()

    @property
    def path(self):
        return f'/v2/point/{ZSSS[0]:.4f}/{ZSSS[1]:.4f}/{self.radius_nm:d}'

    def _load(self):
        try:
            ts = [float(t) for t in json.load(open(self.state_file)).get('requests', [])]
        except Exception:
            ts = []
        cut = time.time() - 86400
        ts = [t for t in ts if t > cut]
        if ts:
            self.last_req = max(ts)
        return ts

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp = self.state_file + '.tmp'
            json.dump({'what': 'adsb.lol request times (epoch s) of this relay in the last 24 h (quota guard)', 'requests': self.requests}, open(tmp, 'w'))
            os.replace(tmp, self.state_file)
        except Exception as e:
            print('adsb quota state not saved:', e, file=sys.stderr)

    def _due(self, now):
        self.requests = [t for t in self.requests if t > now - 86400]
        if len(self.requests) >= self.daily_max:
            return False, 'daily cap reached'
        if now < max(self.last_req + self.cur_interval, self.not_before):
            return False, 'interval'
        return True, None

    def get(self):
        if not self.enabled:
            return self._payload(time.time(), note='adsb.lol relay is OFF (start the relay with --adsb to enable it)')
        now = time.time()
        with self.lock:
            due, why = self._due(now)
            go = due and not self.busy
            if go:
                self.busy = True
                self.last_req = now
                self.requests.append(now)
                self._save()
        if go:
            try:
                self._fetch(now)
            finally:
                with self.lock:
                    self.busy = False
        return self._payload(time.time())

    def _fetch(self, t0):
        try:
            code, hd, body = http_get(self.base + self.path, timeout=15, headers={'Accept': 'application/json'})
        except Exception as e:
            code, hd, body = None, {}, (type(e).__name__ + ': ' + str(e)).encode()
        with self.lock:
            self.last_code = code
            js = None
            if code == 200:
                try:
                    js = json.loads(body)
                except ValueError:
                    js = None
            if isinstance(js, dict) and isinstance(js.get('ac', []), list):
                self.cur_interval = self.interval
                self.last_error = None
                now_s = js.get('now') or js.get('ctime') or t0 * 1000
                now_s = now_s / 1000.0 if now_s > 1e11 else float(now_s)
                kept, excluded = [], {}
                for a in js.get('ac') or []:
                    if not isinstance(a, dict):
                        continue
                    ty = a.get('type') or 'unknown'
                    if ty != 'adsb_icao':
                        excluded[ty] = excluded.get(ty, 0) + 1
                        continue
                    r = {k: a[k] for k in ADSB_KEEP if k in a}
                    if 'hex' in r:
                        r['hex'] = str(r['hex']).lower()
                    r['src'] = 'obs'                         # observed (ADS-B), labelled per record
                    r['_src'] = 'adsb.lol'
                    if a.get('seen_pos') is not None:
                        r['_pt'] = round(now_s - float(a['seen_pos']), 2)    # absolute position time, epoch s
                    kept.append(r)
                self.last = {'now': int(now_s * 1000), 'fetched': t0, 'ac': kept, 'excluded': excluded,
                             'upstream_total': len(js.get('ac') or [])}
            else:
                self.last_error = f'HTTP {code}' if code else body.decode(errors='replace')[:160]
                self.cur_interval = min(ADSB_BACKOFF_MAX, self.cur_interval * 2)
                ra = hd.get('retry-after')
                try:
                    if ra:
                        self.not_before = t0 + min(float(ra), 86400.0)
                except ValueError:
                    pass

    def _payload(self, now, note=None):
        with self.lock:
            L = self.last or {}
            nxt = max(self.last_req + self.cur_interval, self.not_before) - now if self.enabled else None
            return {'enabled': self.enabled, 'provider': 'adsb.lol', 'note': note, 'ac': L.get('ac', []),
                    'now': L.get('now'), 'fetched_utc': utc(L.get('fetched')), 'excluded': L.get('excluded', {}),
                    'upstream_total': L.get('upstream_total'), 'radius_nm': self.radius_nm,
                    'min_interval_s': self.interval, 'interval_s': self.cur_interval,
                    'next_request_in_s': round(max(0.0, nxt), 1) if nxt is not None else None,
                    'requests_24h': len([t for t in self.requests if t > now - 86400]), 'daily_max': self.daily_max,
                    'last_code': self.last_code, 'last_error': self.last_error,
                    'labels': 'every record in ac is observed ADS-B (type adsb_icao); other types are dropped',
                    'attribution': ATTRIBUTION['adsb']}

    def status(self):
        p = self._payload(time.time())
        p.pop('ac', None)
        return p


# ------------------------------------------------------------------------------------------------ identity overlay (local)
OBS_DIR = os.path.join(HERE, 'refs', 'cache', 'observed_elsewhere')      # gitignored; never served as a static path
OVERLAY_TOOL = os.path.join(HERE, 'tools', 'sim', 'observed_overlay.py')
DAY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
LOOPBACK = ('127.0.0.1', '::1', 'localhost')


def is_loopback(h):
    h = (h or '').strip('[]')
    return h in LOOPBACK or h.startswith('127.') or h == '::ffff:127.0.0.1'


def host_name(h):
    """the name part of a Host header ('[::1]:8000' -> '::1', 'localhost:8000' -> 'localhost'), lower case"""
    h = (h or '').strip().lower()
    if h.startswith('['):
        return h[1:h.index(']')] if ']' in h else h[1:]
    if h.count(':') == 1:
        h = h.split(':', 1)[0]
    return h.rstrip('.')


def is_ip(h):
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


def is_loopback_name(name):
    """a Host header name that can only mean this machine: 'localhost' or a loopback IP literal (never '127.0.0.1.x.example')"""
    if name == 'localhost':
        return True
    try:
        a = ipaddress.ip_address(name)
    except ValueError:
        return False
    return a.is_loopback or (getattr(a, 'ipv4_mapped', None) is not None and a.ipv4_mapped.is_loopback)


def own_names():
    n = set()
    try:
        for x in (socket.gethostname(), socket.getfqdn()):
            if x:
                n |= {x.lower(), x.lower() + '.local'}
    except OSError:
        pass
    return n


class Identity:
    """The observed-elsewhere identity overlay (OD4: shown only locally, never committed). Served only on loopback unless
    --identity-lan; off with --no-identity. The overlay is built in memory by tools/sim/observed_overlay.py (imported by
    path) and cached per file mtime."""

    def __init__(self, enabled=True, lan=False, host='127.0.0.1', obs_dir=OBS_DIR):
        self.enabled, self.lan, self.host, self.obs_dir = bool(enabled), bool(lan), host, obs_dir
        self.lock = threading.Lock()
        self.cache = {}
        self.mod = None

    def _tool(self):
        if self.mod is None:
            import importlib.util
            spec = importlib.util.spec_from_file_location('sha_observed_overlay', OVERLAY_TOOL)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            self.mod = m
        return self.mod

    def allowed(self, client, host_header=None, fetch_site=None):
        """(ok, reason). host_header / fetch_site: the request's Host and Sec-Fetch-Site headers (DNS-rebinding guard, P3-A
        fix round 1, F4): a page served from another name that resolves to 127.0.0.1 reaches the relay as a loopback client
        but with its own name in Host; a browser marks a cross-site request with Sec-Fetch-Site: cross-site."""
        if not self.enabled:
            return False, 'identity overlay off (--no-identity)'
        if not self.lan and (not is_loopback(self.host) or not is_loopback(client)):
            return False, 'identity overlay is served on loopback only (add --identity-lan to serve it to the LAN)'
        if host_header is not None:
            name = host_name(host_header)
            ok = is_loopback_name(name) if not self.lan else (is_loopback_name(name) or is_ip(name) or name in own_names())
            if not ok:
                return False, ('identity overlay is served only to requests addressed to localhost / 127.0.0.1 / [::1] '
                               '(Host header; DNS-rebinding guard)' if not self.lan else
                               'identity overlay (LAN) is served only to requests addressed to an IP address or this host\'s name')
        if (fetch_site or '').strip().lower() == 'cross-site':
            return False, 'identity overlay is not served to cross-site browser requests (Sec-Fetch-Site)'
        return True, None

    def days(self):
        try:
            return self._tool().days(self.obs_dir) if self.enabled else []
        except Exception:
            return []

    def get(self, day):
        if not DAY_RE.match(day or '') or day not in self.days():
            return None
        f = os.path.join(self.obs_dir, f'sha_observed_{day}.json')
        try:
            k = os.stat(f).st_mtime_ns
        except OSError:
            return None
        with self.lock:
            c = self.cache.get(day)
            if c and c[0] == k:
                return c[1]
        ov = self._tool().overlay(day, self.obs_dir)
        with self.lock:
            self.cache[day] = (k, ov)
        return ov

    def banner(self):
        if not self.enabled:
            return 'off (--no-identity)'
        d = self.days()
        where = 'LAN (--identity-lan)' if self.lan else ('loopback only' if is_loopback(self.host) else 'not served (--host beyond loopback without --identity-lan)')
        return f'{where}, local days {d if d else "none"}'


# ------------------------------------------------------------------------------------------------ static files
GZIP_TYPES = ('.js', '.mjs', '.css', '.html', '.json', '.svg', '.txt')
ALLOW = (                                       # (prefix, is_dir) relative to the repository root
    (f'{APP_DIR}/live.html', False), (f'{APP_DIR}/live.css', False), (f'{APP_DIR}/js/', True), (f'{APP_DIR}/data/', True),
    ('sfo3d/data/models/', True), ('sfo3d/data/liveries/', True),
)


def allowed(upath):
    p = urllib.parse.unquote(upath).lstrip('/')
    parts = [s for s in p.split('/') if s]
    if not parts or any(s.startswith('.') or s == '..' for s in parts):
        return False
    p = '/'.join(parts)
    return any((p.startswith(a) if d else p == a) for a, d in ALLOW)


class StaticGzip:
    def __init__(self):
        self.c, self.lock = {}, threading.Lock()

    def get(self, path):
        st = os.stat(path)
        k = (st.st_mtime_ns, st.st_size)
        with self.lock:
            v = self.c.get(path)
            if v and v[0] == k:
                return v[1]
        b = gzip.compress(open(path, 'rb').read(), 6)
        with self.lock:
            self.c[path] = (k, b)
        return b


# ------------------------------------------------------------------------------------------------ HTTP server
def make_handler(app):
    wx, adsb = app['wx'], app['adsb']
    ident = app.get('identity') or Identity(enabled=False)
    sgz = StaticGzip()

    class H(SimpleHTTPRequestHandler):
        server_version = 'sha-live-relay/' + VERSION
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.js': 'text/javascript', '.mjs': 'text/javascript',
                          '.json': 'application/json', '.sfom': 'application/octet-stream', '.webp': 'image/webp'}

        def __init__(self, *a, **k):
            super().__init__(*a, directory=REPO, **k)

        def log_message(self, fmt, *args):
            if app.get('quiet') or '/api/' not in self.path:
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

        def _json(self, obj, code=200, extra=None):
            return self._send(json.dumps(obj, separators=(',', ':')).encode(), code=code, extra=extra)

        def end_headers(self):
            if '/api/' not in self.path:
                self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            super().end_headers()

        def _api(self, u):
            p = u.path
            if p.startswith('/' + APP_DIR + '/api/'):
                p = p[len(APP_DIR) + 1:]
            return p if p.startswith('/api/') else None

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            try:
                if u.path in ('/', '/' + APP_DIR, '/' + APP_DIR + '/'):
                    qs = u.query if 'relay=' in u.query else ('relay=1' + ('&' + u.query if u.query else ''))
                    self.send_response(302)
                    self.send_header('Location', f'/{APP_DIR}/live.html?{qs}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                api = self._api(u)
                if api == '/api/ping':
                    return self._json({'shalive': 1, 'v': VERSION, 'mode': 'live', 'dataNow': int(time.time() * 1000),
                                       'features': {'metar': wx.enabled, 'taf': wx.enabled, 'adsb': adsb.enabled, 'replay': None,
                                                    'identity': ident.days() if ident.allowed(self.client_address[0], self.headers.get('Host'), self.headers.get('Sec-Fetch-Site'))[0] else []},
                                       'adsb_min_interval_s': adsb.interval, 'wx_min_interval_s': wx.min_interval,
                                       'providers': [v['name'] for k, v in PROVIDERS.items() if (k != 'adsblol' or adsb.enabled) and (k != 'awc' or wx.enabled)],
                                       'attribution': ATTRIBUTION, 'ua': UA})
                if api in ('/api/metar', '/api/taf'):
                    ids = re.sub(r'[^A-Za-z0-9,]', '', q.get('ids', ['ZSSS'])[0]).upper()[:32] or 'ZSSS'
                    if ids != 'ZSSS':
                        return self._json({'error': 'only ZSSS is relayed'}, 400)
                    fmt = 'json' if q.get('format', ['raw'])[0] == 'json' else 'raw'
                    try:
                        body, ctype, extra = wx.payload('metar' if api == '/api/metar' else 'taf', fmt)
                    except Exception as e:
                        return self._json({'error': str(e)[:200]}, 502)
                    return self._send(body, ctype, extra=extra)
                if api == '/api/adsb':
                    return self._json(adsb.get())
                if api == '/api/observed_elsewhere':
                    day = (q.get('day') or [''])[0]
                    if not DAY_RE.match(day):
                        return self._json({'available': False, 'error': 'day must be YYYY-MM-DD'}, 400)
                    ok, why = ident.allowed(self.client_address[0], self.headers.get('Host'), self.headers.get('Sec-Fetch-Site'))
                    if not ok:
                        return self._json({'available': False, 'reason': why})
                    ov = ident.get(day)
                    if ov is None:
                        return self._json({'available': False, 'reason': 'no local observed-elsewhere file for this day'})
                    return self._json({**ov, 'available': True})
                if api == '/api/status':
                    return self._json({'relay': {'v': VERSION, 'uptime_s': round(time.time() - app['t_start']), 'ua': UA,
                                                 'origin': {'lat': ZSSS[0], 'lon': ZSSS[1]}},
                                       'weather': wx.status(), 'adsb': adsb.status()})
                if api is not None:
                    return self._json({'error': 'unknown endpoint'}, 404)
            except (BrokenPipeError, ConnectionResetError):
                return
            if not allowed(u.path):
                return self.send_error(404)
            fs = self.translate_path(u.path)
            if os.path.isfile(fs) and fs.endswith(GZIP_TYPES) and 'gzip' in (self.headers.get('Accept-Encoding') or ''):
                try:
                    body = sgz.get(fs)
                    self.send_response(200)
                    self.send_header('Content-Type', self.guess_type(fs))
                    self.send_header('Content-Encoding', 'gzip')
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Vary', 'Accept-Encoding')
                    self.end_headers()
                    self.wfile.write(body)
                    return
                except OSError:
                    pass
            return super().do_GET()

        def do_HEAD(self):
            u = urllib.parse.urlparse(self.path)
            if self._api(u) is not None or not allowed(u.path):
                return self.send_error(404)
            return super().do_HEAD()

        def do_POST(self):
            self.send_error(405)

        def list_directory(self, path):
            self.send_error(404)       # no directory listings

    return H


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--host', default='127.0.0.1', help='0.0.0.0 to open it from a phone on the same network')
    ap.add_argument('--no-metar', action='store_true', help='never contact aviationweather.gov (no live weather)')
    ap.add_argument('--adsb', action='store_true', help='relay adsb.lol (OFF by default: keyless quota 500 / day / IP, shared with any recorder)')
    ap.add_argument('--adsb-interval', type=float, default=ADSB_MIN_INTERVAL, help='s between adsb.lol requests (>= 180; lower values are raised to 180)')
    ap.add_argument('--adsb-radius-nm', type=int, default=60, help='point-query radius around ZSSS (NM, 1-250; default 60)')
    ap.add_argument('--adsb-daily-max', type=int, default=200, help='adsb.lol requests in any 24 h (default 200 of the 500 keyless quota)')
    ap.add_argument('--no-identity', action='store_true', help='never serve the local observed-elsewhere identity overlay')
    ap.add_argument('--identity-lan', action='store_true', help='serve the identity overlay beyond loopback (with --host; personal use only, OD4)')
    ap.add_argument('--identity-dir', default=OBS_DIR, help=argparse.SUPPRESS)       # tests: a temporary directory
    ap.add_argument('--state-dir', default=STATE_DIR, help=argparse.SUPPRESS)
    ap.add_argument('--awc-base', default=AWC_BASE, help=argparse.SUPPRESS)          # tests: a local mock
    ap.add_argument('--adsb-base', default=ADSBLOL_BASE, help=argparse.SUPPRESS)     # tests: a local mock
    ap.add_argument('--wx-interval', type=float, default=WX_MIN_INTERVAL, help=argparse.SUPPRESS)   # tests only; never < 600 live
    ap.add_argument('--quiet', action='store_true', help='no request log')
    a = ap.parse_args(argv)
    wx_iv = a.wx_interval if a.awc_base != AWC_BASE else max(WX_MIN_INTERVAL, a.wx_interval)   # the 10-min floor holds upstream
    app = {'wx': Wx(base=a.awc_base, enabled=not a.no_metar, min_interval=wx_iv),
           'adsb': Adsb(enabled=a.adsb, base=a.adsb_base, radius_nm=a.adsb_radius_nm, interval=a.adsb_interval,
                        daily_max=a.adsb_daily_max, state_dir=a.state_dir),
           'identity': Identity(enabled=not a.no_identity, lan=a.identity_lan, host=a.host, obs_dir=a.identity_dir),
           't_start': time.time(), 'quiet': a.quiet}
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(app))
    srv.daemon_threads = True
    host = 'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host
    port = srv.server_address[1]
    print(f'SHA Live 3D relay {VERSION}: http://{host}:{port}/  (-> /{APP_DIR}/live.html?relay=1)')
    print(f'weather: {"aviationweather.gov ZSSS, <= 1 request / 10 min" if not a.no_metar else "off"} · '
          f'adsb.lol: {"on, >= %d s between requests, <= %d / 24 h, %d NM" % (app["adsb"].interval, app["adsb"].daily_max, app["adsb"].radius_nm) if a.adsb else "off"} · '
          f'UA: {UA}', flush=True)
    print(f'identity overlay (observed elsewhere, OD4): {app["identity"].banner()}', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
