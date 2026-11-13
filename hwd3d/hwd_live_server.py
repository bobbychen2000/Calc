#!/usr/bin/env python3
"""Hayward Live 3D (KHWD) - local relay (Python 3 standard library only).

Forked from sfo3d/sfo_live_server.py @ a967f9b.
  Kept:    Http (keep-alive CONNECT-proxy client), Poller (one request in flight, exponential back-off, adaptive floor),
           RecordWriter (record.py format), Clock, Hub merge + hygiene (_merge/_merge_one unchanged in substance),
           Metar (conditional, scheduled upstream fetches), --replay re-timed to wall time, StaticGzip, the handler and
           the SSE fan-out (full + delta events, keepalive).
  Changed: centre = the FAA NASR ARP of HWD, radius 8 NM; adsb.lol polled inside its *documented* quota (Quota class,
           schedule 'budget'; see "adsb.lol limits" below) instead of every 1.0-1.5 s; per-provider snapshot TTL (an
           adsb.lol-only feed polled every 7-60 s, or the recorder's 46-s holes, must not blank the picture between
           polls); Retry-After honoured in full (a daily window can say hours); D1 masking + Mictronics enrichment as the
           last merge step; --record writes adsb.lol only (never adsb.fi); replay reads the committed sfo3d rec_pack
           (.jsonl.xz) and keeps only the HWD window; METAR = KHWD only (routine minute :54, schedule shifted);
           /api/stream?history=S; /api/ident; '/' -> live.html; out/replay/ is served (pack + shim), the rest of out/
           and refs/** never.
  Dropped: FaaRegistry/faa_icao (transport types; the FAA registry download is blocked, PLAN section 2), Routes and
           /api/routeset (GA flights have no published routes), Gates and /api/gates (flysfo.com, SFO only), /api/taf
           (aviationweather.gov returns [] for KHWD: there is no KHWD TAF, docs/phase2_fork_map.md 2.1), the SFO flight /
           stand helpers, --record-sfo-gates.

  python3 hwd_live_server.py [--port 8000] [--host 127.0.0.1] [--radius 8] [--no-adsbfi] [--no-ident]
          [--ident full|type-only] [--replay SRC [--from ISO] [--until ISO] [--speed 1] [--loop] [--lookahead 60]]
          [--record DIR] [--quiet]
     SRC = 'rec_pack' (../sfo3d/refs/cache/rec_pack/adsblol_*.jsonl.xz, read only) or a directory of record.py-format
     files (adsblol_<YYYYMMDD_HH>.jsonl.gz | .jsonl.xz). Then open http://localhost:8000/ (-> live.html).

Endpoints (contract: docs/phase2_fork_map.md 2.1; how to use them: docs/phase2_relay.md)
  /                  302 -> live.html (query kept)
  /api/ping          {"hwdlive": 1, "v", "mode", "stream", "delta", "dataNow", "center", "poll", "features",
                      "providers", "attribution"}  (the app accepts a relay only when hwdlive === 1)
  /api/adsb          latest merged list, readsb jv2 shape {"now", "dataNow", "seq", "total", "_source", "msg", "ac"}
  /api/stream        SSE: "adsb" full events; ?delta=1 adds "delta" events {now, dataNow, seq, ac, gone}; a full event
                     on every seq gap and at least every 30 s; ": keepalive" every 15 s. ?history=S (S <= 120): first
                     replays the full payloads published in the last S seconds, oldest first (so an app that displays
                     `lookahead_s` behind has fixes on both sides of a hole at once, instead of after S seconds).
  /api/metar?ids=KHWD[&format=json]  aviationweather.gov KHWD METARs of the last 3 h, newest first (raw lines by
                     default); replay: only reports observed at or before the replay time, 502 when none within 90 min.
  /api/ident?key=K   identity of an aircraft that is in the relay's current picture (or was, within 10 min): broadcast
                     fields + Mictronics fill. Masked (D1) keys answer type only. 404 for any other key: this is not a
                     registry look-up service for arbitrary addresses.
  /api/status        provider health, quota, latency, 429s, merge/hygiene counters, ident loader state, masked count,
                     replay position. No identities.
  (removed: /api/gates, /api/routeset, /api/taf -> 404)

Data sources, terms and limits (verified 2026-11-13; quotes and hashes in docs/phase2_relay.md section 3)
  adsb.lol  GET https://api.adsb.lol/v2/point/{lat}/{lon}/{nm} (integer radius 0-250). Live OpenAPI description
            (https://api.adsb.lol/api/openapi.json, info.version 0.0.2): "/v2/ ... Metered"; "No key: **500
            requests/day per IP**"; "Over quota returns `429` with a `Retry-After` header. Unkeyed traffic is limited
            per IP; the daily window is a fixed 24h bucket, not midnight UTC." The 429 response: "The window that
            tripped is named in the body (per-second, per-minute, per-hour or per-day for unkeyed traffic ...)". A key
            is sent as `x-api-key` (feeder key: 7,200/day). Only the daily number of unkeyed traffic is published;
            the recorder of sfo3d met a 429 after ~10 polls in each minute (4,782 of 5,541 one-minute bursts, 4-11 Nov
            2026, PLAN section 3) [observed] while making ~7,970 OK polls a day unkeyed (54,537 in 6.84 days,
            refs/cache/adsb/hwd_events.json), so the 500/day limit was not enforced then or is newer (sfo3d's research
            quoted the same URL and info.version as "You can use the API for free"). The docs page
            https://www.adsb.lol/docs/open-data/api (2026-11-13) repeats 500/day but says "the daily window resets at
            00:00 UTC"; a rolling 24-h count <= cap satisfies either reading. A 200 response carries no quota headers
            [observed, 2026-11-13]. So the
            relay counts its own requests (Quota) and polls at >= 6.5 s, stretched so the rest of the rolling-24-h
            budget lasts `--adsblol-horizon` s of watching, and only while a client is connected. Data: ODbL 1.0.
  adsb.fi   GET https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{nm} every 2.0 s ~0.3 s after an even second.
            README (github.com/adsbfi/opendata @ 9fe1c9a): "The public endpoints are rate limited to 1 request per
            second"; "adsb.fi open data is for personal, non-commercial use only. You may not license, sell, rent, or
            lease any part of the data or the service." Live only: never recorded, never packed, never committed.
  METAR     https://aviationweather.gov/api/data/metar (NOAA/NWS AWC, US Government work): "maximum 100 requests per
            minute"; "up to the previous 30 days of data". KHWD routine METAR at hh:54 (215 of 215 routine reports 4-13 Nov
            2026), received 4.1-4.4 min later (p10-p90; one AWC request of 13 Nov) -> 60 s cache from hh:56 to hh:01,
            300 s otherwise.
  identity  Mictronics aircraft database (ODC-By 1.0), local copy refs/cache/local/registry/mictronics_lookup.json
            (gitignored; tools/registry/mictronics_db.py), added inline as `_mx` {r, t, d, op}.

Merge and hygiene (sfo3d feeds 5.2 / traffic_audit 6.2, unchanged): per aircraft key the freshest position wins;
same-report fill; MLAT/TIS-B held 10 s behind ADS-B and jump-tested; on the ground `track`, `track_rate` and the
MLAT-listed fields are dropped (`_drop`); sticky `_veh` (emitter category C1-C7, type SERV/GRND); positions older than
60 s -> `lastPosition`; provenance `_src`, `_prov`, `_pt` (epoch s, relay clock).

D1 (docs/PLAN.md 6a; contract docs/phase2_fork_map.md 2.1) - the LAST step before a record leaves the relay:
  masked when dbFlags & 4 (PIA) or dbFlags & 8 (LADD) - readsb README-json.md (github.com/wiedehopf/readsb, dev @
  88877b9): "military = dbFlags & 1; interesting = dbFlags & 2; PIA = dbFlags & 4; LADD = dbFlags & 8;". Sticky for the
  relay process (a flag seen once masks the aircraft until restart). The Mictronics `flags` field is NOT used: its two
  characters are military and "interesting" (Mictronics readsb webapp aircraft.ts @ e649d2f lines 565-583), not LADD/PIA.
  Masking removes flight, r, ownOp, year, squawk, dbFlags, _mx, _dbalt; keeps t, desc, category, emergency and the
  kinematics; replaces hex by 'x' + 8 hex of HMAC-SHA256(per-process random salt, hex); sets _masked: 1.
  --ident type-only does the same to every aircraft (for anything that may be published).
"""
import argparse, base64, datetime as dt, glob, gzip, heapq, hmac, hashlib, http.client, json, math, os, random, re
import signal, ssl, subprocess, sys, threading, time, urllib.parse, urllib.request
from collections import deque
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

VERSION = '0.1'
ROOT = os.path.dirname(os.path.abspath(__file__))                       # hwd3d/
REPO = os.path.dirname(ROOT)
ARP = (37.65893166, -122.12173888)   # FAA NASR APT_BASE HWD, cycle 2026-10-29 (docs/PLAN.md section 1; js/geo.js ARP)
FIELD_ELEV_FT = 52.1                 # FAA NASR APT_BASE ELEV
RADIUS_NM = 8                        # D6 shows ~5 nm; +3 nm so a track exists before it enters the scope [inf]
# a generic, honest User-Agent (aviationweather.gov asks for a custom one); no names, no repository URL
UA = f'hwd-live-3d-relay/{VERSION} (personal non-commercial visualisation; python-stdlib)'
REC_PACK = os.path.join(REPO, 'sfo3d', 'refs', 'cache', 'rec_pack')     # adsb.lol hours, ODbL 1.0 (read only)
REPLAY_DIR = os.path.join(ROOT, 'out', 'replay')                        # generated, gitignored; served
WX_DIR = os.path.join(REPLAY_DIR, 'wx')                                 # cached KHWD METARs (public domain)
STATE_DIR = os.path.join(REPLAY_DIR, '.state')                          # quota log (dot dir: never served)
MICTRONICS = os.path.join(ROOT, 'refs', 'cache', 'local', 'registry', 'mictronics_lookup.json')

PROVIDERS = {
    # adsb.lol: primary; inside its documented quota (see the module docstring). period = base jitter (>= 6.5 s keeps
    # under the ~10 per minute the recorder met); the Quota stretches it as the 24-h budget runs down.
    'adsblol': dict(id='adsblol', name='adsb.lol', short='lol', home='https://adsb.lol', host='api.adsb.lol',
                    path='/v2/point/{lat:.4f}/{lon:.4f}/{nm:d}', schedule='budget', period=(6.5, 7.5),
                    backoff_first=10.0, backoff_max=600.0, ra_max=86400.0 + 120.0, record=True),
    # adsb.fi: optional, live only (personal non-commercial terms); its snapshot changes on even seconds (sfo3d
    # realtime_feeds 4.2), documented limit 1 request/s
    'adsbfi': dict(id='adsbfi', name='adsb.fi', short='fi', home='https://adsb.fi', host='opendata.adsb.fi',
                   path='/api/v3/lat/{lat:.4f}/lon/{lon:.4f}/dist/{nm:d}', schedule='even', period=2.0, phase=0.3,
                   backoff_first=4.0, backoff_max=60.0, ra_max=3600.0, record=False),
}
ADSBLOL_DAILY = 500         # "No key: 500 requests/day per IP" (adsb.lol OpenAPI 0.0.2, 2026-11-13)
QUOTA_MARGIN = 0.05         # leave 5 % of the daily budget to others on this IP / manual checks [inf]
QUOTA_HORIZON = 3600.0      # stretch the period so the remaining budget lasts this much watching (s) [inf, design]
IDLE_AFTER = 60.0     # stop polling providers when no client has asked for data for this long (s)
MAX_POS_AGE = 60.0    # older positions move to 'lastPosition', as readsb does (README-json.md 'lastPosition')
SNAP_TTL = 45.0       # minimum: ignore a provider's last snapshot once it is this old (provider failing / backing off)
REPLAY_SNAP_TTL = 75.0  # replay of the recorder: its holes are ~46 s, up to 52.4 s in the busy hours (fork map 2.2)
SAME_REPORT_S = 0.2   # two providers' positions within this time are the same report (traffic_audit 6.2.5)
MLAT_HOLD_S = 10.0    # ignore MLAT/TIS-B positions while an ADS-B/ADS-R one is younger than this (6.2.2)
FULL_EVERY = 30.0     # delta streams get a full list at least this often (s)
HISTORY_S = 120.0     # /api/stream?history=S keeps at most this much (s)
IDENT_KEEP_S = 600.0  # /api/ident answers for keys seen in the last 10 min
FORGET_KEEP_S = 600.0  # D1 late-flag forget events are offered to SSE streams / pollers (?since=) this long (fix round 2)

ATTRIBUTION = {
    'adsb': 'Aircraft data: contains information from ADSB.lol (https://adsb.lol), which is made available here under '
            'the Open Database License (ODbL 1.0, https://opendatacommons.org/licenses/odbl/1-0/).',
    'adsbfi': 'and adsb.fi (https://adsb.fi) open data, personal non-commercial use (live only, never stored).',
    'metar': 'Weather: NOAA/NWS Aviation Weather Center (https://aviationweather.gov).',
    'ident': 'Aircraft identity: Mictronics aircraft database (https://github.com/Mictronics/aircraft-database), '
             'Open Data Commons Attribution License 1.0 (https://opendatacommons.org/licenses/by/1-0/).',
}

SRC_RANK = {'adsb_icao': 0, 'adsb_icao_nt': 1, 'adsr_icao': 2, 'tisb_icao': 3, 'adsc': 4, 'mlat': 5, 'other': 6,
            'mode_s': 7, 'adsb_other': 8, 'adsr_other': 9, 'tisb_other': 10, 'tisb_trackfile': 11}   # readsb order
IDENT = ('flight', 'squawk', 'emergency', 'category', 'r', 't', 'desc', 'ownOp', 'year', 'dbFlags', 'alert', 'spi')
PREFER_FI = ('desc', 'ownOp', 'year')                     # adsb.lol omits them (sfo3d feeds 3.1)
DB_FIELDS = ('r', 't', 'desc', 'ownOp', 'year', 'dbFlags')
META = ('seen', 'messages', 'rssi')
DROP_ALWAYS = ('dst', 'dir')                              # distance/bearing from the provider's query point
VOLATILE = ('seen', 'seen_pos', 'messages', 'rssi')       # ignored when deciding whether a record changed
VEH_CAT = re.compile(r'^C[1-7]$')                          # DO-260B emitter category set C: surface vehicles/obstacles
D1_BITS = 4 | 8                                            # readsb: PIA = dbFlags & 4, LADD = dbFlags & 8
D1_DROP = ('flight', 'r', 'ownOp', 'year', 'squawk', 'dbFlags', '_mx', '_dbalt')
CS_ICAO = re.compile(r'^([A-Z]{3})\d')                     # ICAO-style callsign: 3-letter operator designator + digit


def adsb_like(src_type):
    """ADS-B / ADS-R positions (GNSS-derived, broadcast by the aircraft) versus MLAT / TIS-B / Mode S / other."""
    return bool(src_type) and (src_type.startswith('adsb') or src_type.startswith('adsr'))


def hav_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(a)))


NM = 1852.0


def window_filter(lst, radius_nm, max_alt_ft=None, center=ARP):
    """Records of one provider answer inside the HWD window: within radius_nm of the ARP (position or lastPosition),
    and, when max_alt_ft is given, at or below it (alt_baro, else alt_geom) or on the ground. Records without any
    position are dropped (nothing to draw)."""
    out = []
    lim = radius_nm * NM
    for a in lst or []:
        p = _pos(a)
        if p is None or hav_m(center[0], center[1], p[0], p[1]) > lim:
            continue
        if max_alt_ft is not None:
            alt = a.get('alt_baro')
            if alt != 'ground':
                if not isinstance(alt, (int, float)):
                    alt = a.get('alt_geom')
                if isinstance(alt, (int, float)) and alt > max_alt_ft:
                    continue
        out.append(a)
    return out


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
                        BrokenPipeError):
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


# ------------------------------------------------------------------------------------------------ provider quota
class Quota:
    """Our own log of requests to a provider with a published rolling quota (adsb.lol: 500/day per IP unkeyed).

    Counting is ours because a 200 answer carries no quota header [observed]. A rolling 24-h count <= cap keeps every
    fixed 24-h bucket <= cap too (any 24-h interval holds at most `cap` of our requests), whatever the bucket's start.
    Every request counts, 429s included (unknown whether they count upstream: the conservative reading). Persisted
    (times only, no identities) so a relay restart does not reset it. period(): the base cadence, stretched to
    horizon / remaining so that the rest of the budget lasts `horizon` seconds of watching; the period grows as the
    budget runs down (from 475 left at 7.6 s, it takes 3600 x ln(475/n) s to reach n left), and at 0 left polling
    waits until the oldest logged request is 24 h old."""

    def __init__(self, path, daily, window=86400.0, margin=QUOTA_MARGIN, horizon=QUOTA_HORIZON):
        self.path, self.daily, self.window, self.horizon = path, int(daily), float(window), float(horizon)
        self.cap = max(1, int(self.daily * (1.0 - margin)))
        self.log = deque()
        self.blocked_until, self.last_429_body = 0.0, None
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            now = time.time()
            self.log.extend(t for t in sorted(d.get('t', [])) if now - t < self.window)
            self.blocked_until = float(d.get('blocked_until') or 0.0)
        except (OSError, ValueError):
            pass

    def _merge_file(self):
        """Fix round 1: two relays on one IP share the quota file. Before each decision the file is re-read and its request
        times merged with ours (set union), so each process counts the other's requests; the save happens under an exclusive
        lock file (O_EXCL, stale after 10 s) so the two writers do not overwrite each other."""
        if not self.path:
            return
        try:
            with open(self.path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        now = time.time()
        mine = {round(t, 1) for t in self.log}
        for t in d.get('t', []):
            if now - t < self.window and round(t, 1) not in mine:
                self.log.append(t)
        self.log = deque(sorted(self.log))
        self.blocked_until = max(self.blocked_until, float(d.get('blocked_until') or 0.0))

    def _save(self):
        if not self.path:
            return
        lk = self.path + '.lock'
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            for _ in range(50):
                try:
                    fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd); break
                except FileExistsError:
                    try:
                        if time.time() - os.path.getmtime(lk) > 10:
                            os.unlink(lk)
                    except OSError:
                        pass
                    time.sleep(0.02)
            self._merge_file()
            tmp = self.path + '.tmp.%d' % os.getpid()
            with open(tmp, 'w') as f:
                json.dump({'about': 'hwd_live_server.py Quota: our adsb.lol request times (epoch s), rolling 24 h; no '
                                    'identities', 'daily': self.daily, 'cap': self.cap,
                           'blocked_until': self.blocked_until, 't': [round(t, 1) for t in self.log]}, f)
            os.replace(tmp, self.path)
        except OSError as e:
            print('quota save failed:', e, file=sys.stderr)
        finally:
            try:
                os.unlink(lk)
            except OSError:
                pass

    def _prune(self, now):
        while self.log and now - self.log[0] >= self.window:
            self.log.popleft()

    def note(self, t):
        with self.lock:
            self.log.append(t)
            self._prune(t)
            self._save()

    def block(self, until, body=None):
        with self.lock:
            self.blocked_until = max(self.blocked_until, until)
            self.last_429_body = (body or '')[:160] or None
            self._save()

    def left(self, now=None):
        now = time.time() if now is None else now
        with self.lock:
            self._prune(now)
            return self.cap - len(self.log)

    def next_allowed(self, now):
        """Earliest time a request may go out (>= now)."""
        with self.lock:
            self._merge_file()
            self._prune(now)
            t = max(now, self.blocked_until)
            if len(self.log) >= self.cap:
                t = max(t, self.log[len(self.log) - self.cap] + self.window + 1.0)
            return t

    def period(self, base, now=None):
        r = self.left(now)
        return max(base, self.horizon / max(1, r))

    def status(self):
        now = time.time()
        left = self.left(now)
        return {'daily': self.daily, 'cap': self.cap, 'used_24h': self.cap - left, 'left': left,
                'horizon_s': self.horizon, 'period_s': round(self.period(PROVIDERS['adsblol']['period'][0], now), 1),
                'blocked_until': int(self.blocked_until * 1000) if self.blocked_until > now else None,
                'next_allowed_in_s': round(max(0.0, self.next_allowed(now) - now), 1),
                'last_429_body': self.last_429_body}


# ------------------------------------------------------------------------------------------------ provider polling
class Poller(threading.Thread):
    """Polls one provider on its own schedule, one request in flight.

    on_result(prov, t_start, t_recv, status, headers, json_or_None, error_or_None) is called for every request.
    active() -> bool: poll only while true (the relay stops when no client is connected).
    Schedules: 'even' (adsb.fi: even second + phase), 'jitter' (uniform period), 'budget' (adsb.lol: jitter, stretched
    by the Quota, never before Quota.next_allowed)."""

    def __init__(self, prov, on_result, lat=ARP[0], lon=ARP[1], nm=RADIUS_NM, active=lambda: True, wake=None,
                 quota=None, headers=None):
        super().__init__(daemon=True, name='poll-' + prov['id'])
        self.p, self.on_result, self.active = prov, on_result, active
        self.url_path = prov['path'].format(lat=lat, lon=lon, nm=int(nm))
        self.http = Http(prov['host'])
        self.wake = wake or threading.Event()
        self.stop_ev = threading.Event()
        self.phase = prov.get('phase', 0.0)
        self.quota, self.headers = quota, dict(headers or {})
        self.fails = 0
        self.t_first = None
        self.floor = 0.0      # adaptive minimum interval after HTTP 429s (AIMD: x1.5 per 429, x0.9 per success)
        self.next_due = 0.0
        self.lags = deque(maxlen=30)
        self.st = dict(requests=0, ok=0, http429=0, errors=0, dup=0, last_ok=None, last_error=None, last_code=None,
                       backoff_s=0.0, floor_s=0.0, recent=deque(maxlen=1000), latency_ms=deque(maxlen=200),
                       lag_s=deque(maxlen=200), last_now=None)

    @property
    def url(self):
        return f'https://{self.p["host"]}{self.url_path}'

    def base_period(self):
        p = self.p['period']
        return p[1] if isinstance(p, (tuple, list)) else p

    def expected_period(self):
        """The interval the relay expects between this provider's answers now (s): for snapshot TTLs and /api/ping."""
        per = self.base_period()
        if self.quota is not None:
            per = max(per, self.quota.period(self.p['period'][0]))
        return max(per, self.floor, self.st['backoff_s'] or 0.0)

    def _slot_after(self, t):
        """adsb.fi: first 'even second + phase' instant at or after t (local clock)."""
        base = math.floor(t / 2.0) * 2.0 + self.phase
        while base < t:
            base += 2.0
        return base

    def _schedule(self, t0, t1, ok, retry_after=None, status=None):
        """Next request time. Success: the provider's cadence (for 'budget' stretched by the Quota), never faster than
        the adaptive floor. Failure: exponential back-off (backoff_first x 2^n up to backoff_max), and Retry-After in
        full up to ra_max (sfo3d capped it at 300 s; a daily window can name hours, and asking again before it ends is
        "doing something wrong" in adsb.lol's words).

        The floor (sfo3d): adsb.lol's limits are "dynamic" and this egress IP is shared, so each 429 raises the floor
        x1.5 (at least backoff_first) and each success lowers it x0.9 until it is below the normal period again."""
        p = self.p
        if ok:
            self.fails = 0
            self.st['backoff_s'] = 0.0
            if self.floor:
                self.floor *= 0.9
                if self.floor < self.base_period():
                    self.floor = 0.0
            if p['schedule'] == 'even':
                self.next_due = self._slot_after(max(t0 + 1.0, t0 + self.floor - 1.0))   # next even second + phase
            else:
                per = random.uniform(*p['period'])
                if self.quota is not None:
                    per = max(per, self.quota.period(p['period'][0], t1))
                self.next_due = max(t0 + max(per, self.floor), t1 + 0.05)
            self.st['floor_s'] = round(self.floor, 2)
            return
        self.fails += 1
        if status == 429:
            self.floor = min(p['backoff_max'], max(p['backoff_first'], self.floor * 1.5))
        wait = max(min(p['backoff_max'], p['backoff_first'] * 2 ** (self.fails - 1)), self.floor)
        if retry_after:
            wait = max(wait, min(retry_after, p.get('ra_max', 300.0)))
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
            if self.quota is not None:
                self.next_due = max(self.next_due, self.quota.next_allowed(now))
            if self.next_due > now:
                if self.stop_ev.wait(min(self.next_due - now, 5.0)):
                    break
                continue
            t0 = time.time()
            self.t_first = self.t_first or t0
            if self.quota is not None:
                self.quota.note(t0)
            status, hd, js, err, body = None, {}, None, None, b''
            try:
                status, hd, body = self.http.request('GET', self.url_path, headers=self.headers)
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
                if status == 429 and self.quota is not None:
                    txt = body.decode('utf-8', 'replace') if isinstance(body, (bytes, bytearray)) else ''
                    self.quota.block(t1 + min(ra or 0.0, self.p.get('ra_max', 300.0)), txt.strip())
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
                'expected_period_s': round(self.expected_period(), 1), 'keyed': 'x-api-key' in self.headers,
                'quota': self.quota.status() if self.quota is not None else None,
                'last_10min': self._recent(600),
                'next_in_s': round(max(0.0, self.next_due - time.time()), 2) if self.next_due else None}


# ------------------------------------------------------------------------------------------------ recording
class RecordWriter:
    """tools/live/record.py format (sfo3d): one gzip JSON-lines file per provider per UTC hour in `out_dir`, each line
    {"t": request start (s), "tr": response received (s), "p": provider id, "code": HTTP status, "d": response}
    or {..., "err": message, "ra": Retry-After} for failures. Only providers with record=True (adsb.lol): adsb.fi data
    is never written (its terms forbid licensing it; PLAN section 2). The files hold identities: keep them out of git
    and out of the served tree (main() refuses a directory under hwd3d/ that is served)."""

    def __init__(self, out_dir):
        self.dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.files, self.lock = {}, threading.Lock()

    def write(self, pid, t0, t1, status, hd, js, err):
        if not PROVIDERS.get(pid, {}).get('record'):
            return
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


# ------------------------------------------------------------------------------------------------ identity + D1
class Mictronics:
    """Local Mictronics lookup (refs/cache/local/registry/mictronics_lookup.json, written by tools/registry/
    mictronics_db.py build; gitignored): hex -> [registration, icao_type, description, flags]; operators by ICAO
    designator. Loaded in a background thread (20 MB JSON, ~2 s). Optional: the relay works without it."""

    def __init__(self, path=MICTRONICS, enabled=True):
        self.path, self.ready, self.err, self.n = path, False, None, 0
        self.ac, self.ops, self.commit = {}, {}, None
        self.enabled = enabled and os.path.exists(path)
        if self.enabled:
            threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            self.ac, self.ops = d.get('aircraft', {}), d.get('operators', {})
            self.commit = (d.get('commit') or '')[:7] or None
            self.n, self.ready = len(self.ac), True
        except Exception as e:   # noqa: BLE001 (optional data)
            self.err = repr(e)[:200]

    def label(self):
        return f'mictronics {self.commit}' if self.ready else None

    def lookup(self, hx, flight=None):
        """-> {r, t, d, op} with only the fields it knows, or None."""
        if not self.ready:
            return None
        out = {}
        if hx and not hx.startswith('~'):
            row = self.ac.get(hx)
            if row:
                for k, v in zip(('r', 't', 'd'), row[:3]):
                    if v:
                        out[k] = v
        m = CS_ICAO.match((flight or '').strip().upper())
        if m:
            o = self.ops.get(m.group(1))
            if isinstance(o, dict) and o.get('n'):
                out['op'] = o['n']
        return out or None


class D1:
    """D1 masking (docs/PLAN.md 6a; docs/phase2_fork_map.md 2.1). mode 'full': mask LADD/PIA aircraft only;
    'type-only': mask every aircraft. The salt is random per process and never written anywhere."""

    def __init__(self, mode='full', salt=None):
        self.mode = mode
        self.salt = salt or os.urandom(16)
        self.flagged = set()       # sticky: original keys seen with dbFlags & 12 in this process
        self.newly = []            # keys flagged since the last merge (Hub purges what it published for them unmasked)
        self.n_masked = 0

    def key(self, hx):
        return 'x' + hmac.new(self.salt, hx.encode(), hashlib.sha256).hexdigest()[:8]

    def wants(self, hx, rec):
        try:
            f = int(rec.get('dbFlags') or 0)
        except (TypeError, ValueError):
            f = 0
        if f & D1_BITS and hx not in self.flagged:
            self.flagged.add(hx)
            self.newly.append(hx)
        return self.mode == 'type-only' or hx in self.flagged

    def apply(self, hx, rec):
        """-> (output key, record). The record is changed in place (it is the merge's own copy)."""
        if not self.wants(hx, rec):
            return hx, rec
        for k in D1_DROP:
            rec.pop(k, None)
        k = self.key(hx)
        rec['hex'] = k
        # the reason (fix round 1): 'd1' = flagged LADD / PIA; 'type-only' = every aircraft is masked in this run / pack (which
        # aircraft are flagged is then not said - the UI must not claim LADD / PIA for them)
        rec['_masked'] = 'type-only' if self.mode == 'type-only' else 'd1'
        return k, rec


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
    """Latest snapshot per provider -> per-aircraft merge + hygiene -> enrichment + D1 -> JSON payloads, SSE fan-out."""

    def data_now_ms(self, wall=None):
        """The data clock (ms): the recording's time in replay (Clock.to_src), wall time live. None in replay until the
        first record is replayed (the Clock is still the placeholder identity then)."""
        w = time.time() if wall is None else wall
        if self.clock is not None and self.replay_pos is None:
            return None
        return int((self.clock.to_src(w) if self.clock is not None else w) * 1000)

    def __init__(self, mode='live', ident=None, d1=None):
        self.mode = mode
        self.ident = ident               # Mictronics or None
        self.d1 = d1 or D1('full')
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.snaps = {}          # provider id -> dict(t0, recv, now, scale, list, name, ttl)
        self.hist = {}           # key -> per-aircraft memory (last accepted position, last ADS-B time)
        self.vehicles = set()    # sticky vehicle keys
        self.seq = 0
        self.full = self.delta = b''
        self.prev_sig = {}
        self.latest = {'ac': [], 'now': int(time.time() * 1000), 'seq': 0, 'total': 0, '_source': None,
                       'msg': 'waiting for the first provider response'}
        self.full = json.dumps(self.latest, separators=(',', ':')).encode()
        self.history = deque()   # (wall, full payload bytes) of recent publishes, for /api/stream?history=S
        # D1 late flags (fix round 2): every pending forget event (seq, wall, {key: seq the key was first published}) for
        # FORGET_KEEP_S - SSE streams get all events they have not seen yet (not only the newest), /api/adsb?since=S gets
        # the keys a polling client could have seen (published at or before its last answer S)
        self.forget_evs = deque()
        self.pub_first = {}      # unmasked output key -> seq of its first publication (kept while /api/ident holds the key)
        self.idents = {}         # output key -> (wall, identity subset) for /api/ident
        self.last_client = 0.0
        self.clients = 0
        self.wakes = []          # one Event per poller, set when a client shows up
        self.replay_pos = None
        self.clock = None        # replay: the Clock mapping wall -> recording time (data_now_ms); live: None
        self.counters = dict(merges=0, mlat_held=0, mlat_jump=0, ground_track_dropped=0, ground_mlat_fields_dropped=0,
                             same_report_fills=0, pos_to_lastPosition=0, db_type_disagree=0, ident_filled=0)
        self.masked_now = 0
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

    def snap_ttl(self, pid):
        """A provider's snapshot stays in the merge for max(45 s, 1.5 x its expected period + 5 s): adsb.lol inside its
        quota can be polled every 7-60 s, and an aircraft must not vanish between two polls."""
        p = self.pollers.get(pid)
        return max(SNAP_TTL, 1.5 * p.expected_period() + 5.0) if p is not None else SNAP_TTL

    def ingest(self, prov, t0, t1, js, clock=None, scale=1.0, ttl=None):
        now = js.get('now') or js.get('ctime')
        now = (now / 1000.0 if now > 1e11 else float(now)) if now else t0
        if clock is not None:
            now = clock.to_wall(now)
        lst = js.get('ac') if 'ac' in js else js.get('aircraft')
        with self.lock:
            self.snaps[prov['id']] = dict(t0=t0, recv=t1, now=now, scale=scale, list=lst or [], name=prov['name'],
                                          short=prov['short'], ttl=ttl or self.snap_ttl(prov['id']))
            self._merge()

    def reset(self):
        with self.lock:
            self.snaps.clear()
            self.hist.clear()
            self.prev_sig.clear()
            self.history.clear()
            self.forget_evs.clear()
            self.pub_first.clear()

    # -- merge
    def _merge(self):
        wall = time.time()
        C = self.counters
        C['merges'] += 1
        per = {}                                   # key -> [(prov short, snap, record, pos_t, seen_t)]
        for pid, s in self.snaps.items():
            if wall - s['recv'] > s.get('ttl', SNAP_TTL):
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
        out, sigs, fresher, masked = [], {}, {}, 0
        for key, recs in per.items():
            rec = self._merge_one(key, recs, wall)
            if rec is None:
                continue
            fresher[rec['_src']] = fresher.get(rec['_src'], 0) + 1
            okey, rec = self._finish(key, rec)
            masked += 1 if rec.get('_masked') else 0
            sig = json.dumps({k: (v if k != 'lastPosition' else (v.get('lat'), v.get('lon'))) for k, v in rec.items()
                              if k not in VOLATILE}, separators=(',', ':'))
            sigs[okey] = sig
            out.append((okey, rec))
        # forget aircraft not seen for 10 min
        for k in [k for k, h in self.hist.items() if wall - h.get('seen', 0) > 600]:
            del self.hist[k]
        self.fresher, self.masked_now = fresher, masked
        # D1 late flag (fix round 1): a key that a provider's record flagged LADD/PIA only now (another provider's database
        # row had no dbFlags, so it was published unmasked until this merge): its identity is purged everywhere it is still
        # held - /api/ident, the ?history replay - and clients are told to forget it ('forget' in the next payload; the
        # client drops the identity of that track at once). adsb.fi v3 answers do carry dbFlags (one request, 2026-11-13: 2
        # of 78 records; readsb omits the field when it is 0), so this covers the providers' databases disagreeing.
        forget = []
        for hx in self.d1.newly:
            pub = hx in self.prev_sig or hx in self.idents
            self.idents.pop(hx, None)
            tag = ('"hex":"%s"' % hx).encode()
            if any(tag in b for _, b in self.history):
                self.history = deque((w, b) for (w, b) in self.history if tag not in b)
                pub = True
            if pub:
                forget.append(hx)
                C['d1_late_flag'] = C.get('d1_late_flag', 0) + 1
        self.d1.newly = []
        first = {hx: self.pub_first.pop(hx, 0) for hx in forget}
        changed = [r for k, r in out if self.prev_sig.get(k) != sigs[k]]
        gone = [k for k in self.prev_sig if k not in sigs]
        publish = bool(changed or gone or forget) or self.seq == 0
        if publish:                  # a duplicate snapshot (nothing new) is not pushed to streams
            self.seq += 1
        used = sorted({s['name'] for s in self.snaps.values() if wall - s['recv'] <= s.get('ttl', SNAP_TTL)})
        head = {'now': int(wall * 1000), 'dataNow': self.data_now_ms(wall), 'seq': self.seq, 'total': len(out),
                '_source': '+'.join(used) or None, 'msg': 'No error'}
        if forget:
            # sent to clients that were receiving while the key was published - open SSE streams, and polling clients whose
            # last answer (?since=S) came at or after its first publication - never in the full snapshot or the ?history
            # buffer: a client that never saw the key must not learn the address from the forget list
            self.forget_ev = (self.seq, json.dumps({'forget': forget, 'seq': self.seq}, separators=(',', ':')).encode())
            self.forget_evs.append((self.seq, wall, first))
        while self.forget_evs and wall - self.forget_evs[0][1] > FORGET_KEEP_S:
            self.forget_evs.popleft()
        full = dict(head, ac=[r for _, r in out])
        self.latest = full
        self.full = json.dumps(full, separators=(',', ':')).encode()
        if publish:
            for k in sigs:
                if not k.startswith('x'):
                    self.pub_first.setdefault(k, self.seq)
            self.prev_sig = sigs
            self.delta = json.dumps(dict(head, ac=changed, gone=gone), separators=(',', ':')).encode()
            self.history.append((wall, self.full))
            while self.history and wall - self.history[0][0] > HISTORY_S:
                self.history.popleft()
            for k, r in out:
                self.idents[k] = (wall, _ident_subset(k, r))
            for k in [k for k, v in self.idents.items() if wall - v[0] > IDENT_KEEP_S]:
                del self.idents[k]
            for k in [k for k in self.pub_first if k not in self.idents]:
                del self.pub_first[k]
            self.cond.notify_all()
        else:
            self.counters['unchanged'] = self.counters.get('unchanged', 0) + 1

    def adsb_answer(self, since=0):
        """/api/adsb: the full snapshot; with ?since=S (the seq of the poller's last answer) plus 'forget', the keys it was
        shown before a D1 late flag arrived (fix round 2: the poll fallback of js/live/feed.js never got the SSE event)."""
        with self.lock:
            b = self.full
            fk = self.forget_since(since) if since > 0 else []
        if fk:
            b = b[:-1] + b',"forget":' + json.dumps(fk, separators=(',', ':')).encode() + b'}'
        return b

    def forget_since(self, since, upto=None, polled=True):
        """Keys of the forget events after seq `since` (up to `upto`, default now). polled=True (/api/adsb?since=S): only
        keys the client could have seen - first published at or before its last answer S. SSE streams (polled=False) were
        open for every publication since their own seq."""
        upto = self.seq if upto is None else upto
        out = []
        for seq, _w, first in self.forget_evs:
            if since < seq <= upto:
                out += [k for k, f in first.items() if not polled or (0 < f <= since)]
        return sorted(set(out))

    def _finish(self, key, rec):
        """The last merge step: Mictronics `_mx` (unmasked aircraft only), then D1 masking."""
        mx = self.ident.lookup(key, rec.get('flight')) if self.ident is not None else None
        if mx:
            rec['_mx'] = mx
            self.counters['ident_filled'] += 1
        else:
            rec.pop('_mx', None)
        return self.d1.apply(key, rec)      # '~' (non-ICAO) keys carry no dbFlags: masked only in type-only mode

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
                # one database per aircraft, not per report: the providers' databases can disagree and the position
                # winner alternates, so the type would flicker. adsb.fi's value when it has one, else the winner's.
                pick = next((c for c in have if c[0] == 'fi'), None) or next((c for c in have if c[2] is a), None) \
                    or max(have, key=lambda c: c[4])
            else:
                pick = max(have, key=lambda c: c[4])
            out[k] = pick[2][k]
            if k == 't':
                # the other provider's database type when it differs (the app may settle it with the emitter category)
                alt = next((c for c in have if c[0] != pick[0] and c[2].get('t') and c[2].get('t') != out['t']), None)
                if alt:
                    out['_dbalt'] = {'t': alt[2]['t'], 'desc': alt[2].get('desc'), 'p': alt[0]}
                    C['db_type_disagree'] += 1
                else:
                    out.pop('_dbalt', None)
        # dbFlags from any provider record of this aircraft (D1 must see a flag whichever provider carries it)
        fl = 0
        for c in recs:
            try:
                fl |= int(c[2].get('dbFlags') or 0)
            except (TypeError, ValueError):
                pass
        if fl:
            out['dbFlags'] = fl
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
        # 5. vehicles (sticky: vehicles can send reports without a category, sfo3d traffic_audit F8)
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
    def ident_of(self, key):
        with self.lock:
            v = self.idents.get(key)
            return v[1] if v and time.time() - v[0] <= IDENT_KEEP_S else None

    def status(self):
        with self.lock:
            snaps = {s['name']: {'age_s': round(time.time() - s['recv'], 1), 'aircraft': len(s['list']),
                                 'ttl_s': round(s.get('ttl', SNAP_TTL), 1)} for s in self.snaps.values()}
            return {'mode': self.mode, 'seq': self.seq, 'aircraft': self.latest.get('total', 0), 'snapshots': snaps,
                    'position_from': self.fresher, 'vehicles': len(self.vehicles), 'counters': dict(self.counters),
                    'masked_now': self.masked_now, 'masked_flagged_session': len(self.d1.flagged),
                    'd1_mode': self.d1.mode, 'clients': self.clients, 'polling': self.active(),
                    'history_payloads': len(self.history)}


def _ident_subset(k, r):
    """What /api/ident returns for one output record (never identity for a masked one)."""
    if r.get('_masked'):
        return {'key': k, 'masked': True, 't': r.get('t'), 'desc': r.get('desc'), 'category': r.get('category')}
    mx = r.get('_mx') or {}
    out = {'key': k, 'masked': False, 'category': r.get('category')}
    for f, m in (('r', 'r'), ('t', 't'), ('desc', 'd')):
        if r.get(f):
            out[f], out[f + '_src'] = r[f], 'adsb'
        elif mx.get(m):
            out[f], out[f + '_src'] = mx[m], 'mictronics'
    if (r.get('flight') or '').strip():
        out['flight'] = r['flight'].strip()
    if r.get('ownOp'):
        out['op'], out['op_src'] = r['ownOp'], 'adsb'
    elif mx.get('op'):
        out['op'], out['op_src'] = mx['op'], 'mictronics'
    return out


def _pos(a):
    if a.get('lat') is not None and a.get('lon') is not None:
        return float(a['lat']), float(a['lon'])
    lp = a.get('lastPosition')
    if isinstance(lp, dict) and lp.get('lat') is not None:
        return float(lp['lat']), float(lp['lon'])
    return None


# ------------------------------------------------------------------------------------------------ METAR (KHWD)
# Forked from sfo3d's Metar (environment_spec.md 3.3): one upstream JSON fetch serves raw text and JSON, hours=3, on
# demand (the app asks about every 60 s), cache TTL 60 s from hh:56 to hh:01 and 300 s otherwise -- KHWD routine
# METARs are at hh:54 (215 of 215 routine reports 4-13 Nov 2026, plus 40 SPECIs) and reach the API 4.08 / 4.21 /
# 4.37 min later (p10 / p50 / p90 of receiptTime - obsTime; one AWC request of 13 Nov) -- never below the upstream
# "cache-control: max-age", conditional
# (If-None-Match / ETag). AWC: "maximum 100 requests per minute" (https://aviationweather.gov/data/api/, 2026-11-13).
# Upstream errors keep the last good body (header X-Wx-Upstream-Error). Replay: only reports observed at or before the
# replay time (never today's weather in a replay), from out/replay/wx/metar_khwd_*.json; when none is cached within
# 90 min and the time is within AWC's 30-day look-back ("up to the previous 30 days of data"), one targeted request
# (date = T + 1 h, hours = 6) fills the cache. KHWD only; there is no KHWD TAF.
AWC = 'https://aviationweather.gov/api/data/'
STATION = 'KHWD'


def wx_ttl(now=None):
    m = time.gmtime(time.time() if now is None else now).tm_min
    return 60 if (m >= 56 or m <= 1) else 300


def iso_z(t):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


class Metar:
    def __init__(self, replay_clock=None, wx_dir=WX_DIR):
        self.replay, self.wx_dir = replay_clock, wx_dir
        self.lock = threading.Lock()
        self.up = {}
        self._filled = {}

    def cached_list(self, T, hours=3):
        seen = {}
        for p in glob.glob(os.path.join(self.wx_dir, 'metar_khwd_*.json')):
            try:
                with open(p) as f:
                    lst = json.load(f)
                for m in lst:
                    if m.get('obsTime') and T - hours * 3600 <= m['obsTime'] <= T and m.get('rawOb'):
                        seen[(m['obsTime'], m['rawOb'])] = m
            except Exception:
                pass
        return [seen[k] for k in sorted(seen, reverse=True)]

    def fill_cache(self, T):
        """One targeted AWC request for the hours around recording time T (at most once per hour slot)."""
        slot = int(T // 3600)
        if time.time() - self._filled.get(slot, 0) < 600 or time.time() - T > 29.5 * 86400:
            return
        self._filled[slot] = time.time()
        try:
            url = f'{AWC}metar?ids={STATION}&format=json&date={iso_z(T + 3600)}&hours=6'
            code, _, body = http_get(url, timeout=20)
            if code == 200 and body.strip().startswith(b'['):
                os.makedirs(self.wx_dir, exist_ok=True)
                fn = time.strftime('metar_khwd_%Y%m%dT%H00Z.json', time.gmtime(T))
                with open(os.path.join(self.wx_dir, fn), 'wb') as f:
                    f.write(body)
        except Exception as e:
            print('metar cache fill failed:', e, file=sys.stderr)

    def _upstream(self):
        url = AWC + f'metar?ids={STATION}&format=json&hours=3'
        now = time.time()
        with self.lock:
            c = self.up.get('metar')
            if c and now - c['t'] < c['ttl']:
                return c
            etag = c['etag'] if c else None
        hdr = {'If-None-Match': etag} if etag else {}
        try:
            code, hd, body = http_get(url, timeout=15, headers=hdr)
        except Exception as e:
            code, hd, body = None, {}, str(e).encode()
        mx = re.search(r'max-age=(\d+)', hd.get('cache-control', '') or '')
        ttl = max(wx_ttl(now), int(mx.group(1)) if mx else 0)
        with self.lock:
            c = self.up.get('metar')
            if code == 304 and c:
                c.update(t=now, ttl=ttl, err=None, not_modified=c.get('not_modified', 0) + 1)
                return c
            if code == 200 and body.strip().startswith(b'['):
                lst = json.loads(body)
                lst.sort(key=lambda m: m.get('obsTime') or 0, reverse=True)
                c = dict(t=now, ttl=ttl, etag=hd.get('etag'), body=lst, err=None, fetched=now)
                self.up['metar'] = c
                return c
            err = f'HTTP {code}' if code else body.decode(errors='replace')[:120]
            if c:                                   # keep the last good report; retry after 60 s
                c.update(t=now, ttl=60, err=err)
                return c
            raise IOError(err)

    def get(self, ids, fmt):
        """/api/metar: KHWD -> (body, content type, extra headers). Other stations: ValueError (400)."""
        if ids.upper() != STATION:
            raise ValueError('only KHWD is served')
        if self.replay is not None:
            T = self.replay.to_src(time.time())
            L = self.cached_list(T)
            if not L or T - L[0]['obsTime'] > 5400:
                self.fill_cache(T)
                L = self.cached_list(T)
            if L and T - L[0]['obsTime'] <= 5400:   # hourly reports; older than 90 min: none is better
                return ((json.dumps(L).encode(), 'application/json', {}) if fmt == 'json'
                        else ('\n'.join(m['rawOb'] for m in L).encode(), 'text/plain', {}))
            raise IOError('no KHWD METAR within 90 min of the replay time')   # never today's weather in a replay
        c = self._upstream()
        hdr = {'X-Wx-Fetched': str(int(c.get('fetched', 0))), 'X-Wx-Upstream-Error': c['err']} if c.get('err') else {}
        if fmt == 'json':
            return json.dumps(c['body']).encode(), 'application/json', hdr
        return '\n'.join(m['rawOb'] for m in c['body'] if m.get('rawOb')).encode(), 'text/plain', hdr


# ------------------------------------------------------------------------------------------------ replay
def replay_source(src):
    """'rec_pack' -> the committed sfo3d hours (xz); anything else: a directory of record.py-format files."""
    return REC_PACK if src in ('rec_pack', 'rec-pack') else os.path.abspath(src)


def replay_records(root, t_from=None, t_until=None):
    """Recorded adsb.lol responses in time order (streamed hour file by hour file; .jsonl.gz or the rec_pack's
    .jsonl.xz). adsb.fi files are never replayed (the relay never records them; their terms forbid redistribution)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
    import recio
    files = sorted(set(glob.glob(os.path.join(root, 'adsblol_*.jsonl.gz')) +
                       glob.glob(os.path.join(root, 'adsblol_*.jsonl.xz'))))
    last = -1.0
    for p in files:
        h = re.search(r'_(\d{8}_\d{2})\.jsonl', p)
        if h:
            hs = dt.datetime.strptime(h.group(1), '%Y%m%d_%H').replace(tzinfo=dt.timezone.utc).timestamp()
            if t_from is not None and hs + 3600 + 120 < t_from:
                continue
            if t_until is not None and hs - 120 > t_until:
                return
        for r in recio.lines(p):
            if 'd' not in r or not isinstance(r.get('d'), dict):
                continue
            t = r.get('tr') or r['t']
            if (t_from is not None and t < t_from) or t <= last:   # overlapping members: keep time order
                continue
            if t_until is not None and t > t_until:
                return
            last = t
            yield t, 'adsblol', r


def run_replay(hub, root, speed, t_from, t_until, loop, clock_holder, radius_nm):
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
            d = dict(r['d'])
            d['ac'] = window_filter(d.get('ac') if 'ac' in d else d.get('aircraft'), radius_nm)
            hub.ingest(prov, t0, time.time(), d, clock=clock, scale=1.0 / speed, ttl=REPLAY_SNAP_TTL / speed)
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
DENY_TOP = {'refs', 'tools', 'node_modules', 'jobs'}        # never served (licensed/cached/local data, tooling)
DENY_PREFIX = ('docs/qa/ref',)                              # Google-imagery crops (if any): reference only
SERVED_OUT = ('replay',)                                    # out/ is denied except out/replay/ (pack + shim)
GZIP_TYPES = ('.js', '.mjs', '.css', '.html', '.json', '.svg', '.txt', '.csv', '.md')


# fix round 1: an ALLOW-list (the deny-list matched case-sensitively: on a case-insensitive filesystem - macOS APFS, Windows
# NTFS by default - /Refs/cache/local/... and /OUT/... were served). Only the app's own files are served: the page, its
# stylesheet, js/, data/, dev/ (development pages, code only) and out/replay/ (the generated pack + shim). Every part is
# compared lower-cased, and the resolved real path must stay inside one of the allowed directories (no symlink escape).
ALLOW_FILES = {'', 'live.html', 'live.css', 'index.html', 'favicon.ico'}
ALLOW_DIRS = ('js', 'data', 'dev', 'out/replay')


def denied(upath):
    """True for any URL path the static server must not serve."""
    p = urllib.parse.unquote(upath).lstrip('/')
    parts = [s for s in p.replace('\\', '/').split('/') if s]
    low = [s.lower() for s in parts]
    if any(s.startswith('.') or s == '__pycache__' or s == '..' for s in low):
        return True
    if not parts:
        return False
    if len(parts) == 1:
        return low[0] not in ALLOW_FILES
    j = '/'.join(low)
    if not any(j.startswith(d + '/') for d in ALLOW_DIRS):
        return True
    if low[0] in DENY_TOP or any(j.startswith(d) for d in DENY_PREFIX):
        return True
    # the real path (symlinks resolved) must lie inside the allowed directory it names
    real = os.path.realpath(os.path.join(ROOT, *parts))
    for d in ALLOW_DIRS:
        base = os.path.realpath(os.path.join(ROOT, *d.split('/')))
        rl, bl = real.lower(), base.lower()       # (case-insensitive filesystems: /JS/geo.js is js/geo.js)
        if rl == bl or rl.startswith(bl + os.sep):
            return False
    return True


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


def ping_payload(app):
    hub = app['hub']
    lol = hub.pollers.get('adsblol')
    fi = hub.pollers.get('adsbfi')
    ident = app['ident']
    providers = ['adsb.lol'] + (['adsb.fi'] if fi is not None else [])
    att = dict(ATTRIBUTION)
    if fi is None:
        att.pop('adsbfi')
    if not (ident and ident.ready):
        att.pop('ident')
    return {'hwdlive': 1, 'v': VERSION, 'mode': hub.mode, 'stream': True, 'delta': True, 'history': True,
            'dataNow': hub.data_now_ms(),
            'center': {'lat': ARP[0], 'lon': ARP[1], 'radius_nm': app['radius']},
            'poll': {'adsblol_s': round(lol.expected_period(), 1) if lol else None, 'adsbfi': fi is not None,
                     'adsbfi_s': fi.base_period() if fi else None,
                     'quota': lol.quota.status() if lol is not None and lol.quota is not None else None},
            'features': {'metar': STATION, 'taf': None, 'ident': ident.label() if ident else None,
                         'ident_endpoint': bool(ident and ident.ready), 'd1': 'dbFlags & 12', 'd1_mode': hub.d1.mode,
                         'replay': app.get('replay_info')},
            'providers': providers, 'attribution': att}


def make_handler(app):
    hub, metar = app['hub'], app['metar']
    sgz = StaticGzip()

    class H(SimpleHTTPRequestHandler):
        server_version = 'hwd-live-relay/' + VERSION

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
            return self._send(obj if isinstance(obj, bytes) else json.dumps(obj, separators=(',', ':')).encode(),
                              code=code)

        def end_headers(self):
            if not self.path.startswith('/api/'):
                self.send_header('Cache-Control', 'no-cache')
            super().end_headers()

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            try:
                if u.path == '/':
                    self.send_response(302)
                    self.send_header('Location', 'live.html' + (('?' + u.query) if u.query else ''))
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                if u.path == '/api/ping':
                    return self._json(ping_payload(app))
                if u.path == '/api/adsb':
                    hub.touch()
                    try:
                        since = int(q.get('since', ['0'])[0] or 0)
                    except ValueError:
                        since = 0
                    return self._json(hub.adsb_answer(since))
                if u.path == '/api/stream':
                    try:
                        hist = float(q.get('history', ['0'])[0] or 0)
                    except ValueError:
                        hist = 0.0
                    return self._stream(q.get('delta', ['0'])[0] not in ('0', '', 'false'),
                                        max(0.0, min(HISTORY_S, hist)))
                if u.path == '/api/status':
                    return self._json(app_status(app))
                if u.path == '/api/ident':
                    k = (q.get('key', [''])[0] or '').strip().lower()[:24]
                    v = hub.ident_of(k) if k else None
                    if v is None:
                        return self._json({'error': 'not in the current picture'}, 404)
                    return self._json(v)
                if u.path == '/api/metar':
                    ids = re.sub(r'[^A-Za-z0-9,]', '', q.get('ids', [STATION])[0])[:32] or STATION
                    fmt = 'json' if q.get('format', ['raw'])[0] == 'json' else 'raw'
                    try:
                        body, ctype, hdr = metar.get(ids, fmt)
                    except ValueError as e:
                        return self._json({'error': str(e)[:200]}, 400)
                    except Exception as e:
                        return self._json({'error': str(e)[:200]}, 502)
                    dn = {'X-Data-Now': str(hub.data_now_ms())} if hub.data_now_ms() is not None else {}
                    return self._send(body, ctype, extra=dict(hdr, **dn))
                if u.path.startswith('/api/'):
                    return self._json({'error': 'unknown endpoint'}, 404)
            except (BrokenPipeError, ConnectionResetError):
                return
            if denied(u.path):
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
            u = urllib.parse.urlparse(self.path)
            if u.path.startswith('/api/') or denied(u.path):
                return self.send_error(404)
            return super().do_HEAD()

        def do_POST(self):
            self.send_error(404)       # no POST endpoint (sfo3d's /api/routeset is dropped)

        def list_directory(self, path):
            self.send_error(404)       # no directory listings

        def _stream(self, delta, history_s=0.0):
            hub.touch()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Accel-Buffering', 'no')
            self.end_headers()
            with hub.lock:
                hub.clients += 1
                seq, data = hub.seq, hub.full
                now = time.time()
                back = [b for (w, b) in hub.history if now - w <= history_s] if history_s > 0 else []
            last_full = time.time()
            try:
                head = b'retry: 2000\n\n'
                for b in back[:-1]:          # the newest is `data` itself
                    head += b'event: adsb\ndata: ' + b + b'\n\n'
                self.wfile.write(head + b'event: adsb\ndata: ' + data + b'\n\n')
                self.wfile.flush()
                while True:
                    with hub.lock:
                        if hub.seq == seq:
                            hub.cond.wait(15.0)
                        if hub.seq == seq:
                            msg = b': keepalive\n\n'
                        else:
                            # every forget event since this stream's last seq (fix round 2: not only the newest one)
                            fk = hub.forget_since(seq, polled=False)
                            pre = (b'event: forget\ndata: ' + json.dumps({'forget': fk, 'seq': hub.seq}, separators=(',', ':')).encode()
                                   + b'\n\n') if fk else b''
                            if delta and hub.seq == seq + 1 and time.time() - last_full < FULL_EVERY:
                                msg = pre + b'event: delta\ndata: ' + hub.delta + b'\n\n'
                            else:
                                msg = pre + b'event: adsb\ndata: ' + hub.full + b'\n\n'
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
    hub, ident = app['hub'], app['ident']
    return {'relay': {'v': VERSION, 'uptime_s': round(time.time() - app['t_start']), 'ua': UA,
                      'replay': app.get('replay_info'),
                      'replay_position_utc': iso_z(hub.replay_pos) if getattr(hub, 'replay_pos', None) else None,
                      'record_dir': app.get('record_dir'), 'radius_nm': app['radius']},
            'providers': {p.p['name']: p.status() for p in hub.pollers.values()},
            'merge': hub.status(),
            'ident': {'enabled': bool(ident and ident.enabled), 'ready': bool(ident and ident.ready),
                      'aircraft': ident.n if ident else 0, 'source': ident.label() if ident else None,
                      'error': ident.err if ident else None}}


def record_dir_check(path, root=None):
    """May --record write identity-bearing recordings to `path`? -> (ok, reason).
    Fix round 2: inside hwd3d/ only under refs/cache/local/ or out/ (not out/replay/, which is served), compared
    CASE-SENSITIVELY on the resolved path (fix round 1 lower-cased it: on Linux `Refs/Cache/Local/rec` is another directory,
    not covered by .gitignore, and `git add hwd3d` picked it up); and anywhere in a git work tree the directory must be
    ignored by git (`git check-ignore`), so a recording can never be staged. Outside any work tree: allowed."""
    root = os.path.realpath(root or ROOT)
    rd = os.path.realpath(path)
    rel = os.path.relpath(rd, root).replace(os.sep, '/')
    inside = not (rel == '..' or rel.startswith('../'))
    if inside:
        r = rel + '/'
        if not ((r.startswith('refs/cache/local/') or r.startswith('out/')) and not r.lower().startswith('out/replay/')):
            return False, ('inside hwd3d/ use refs/cache/local/<dir> or out/<dir> (exact lower-case spelling; gitignored, '
                           'never served), or a directory outside the repository')
    # the nearest existing ancestor runs git; a probe file name inside the directory is tested (it need not exist)
    anc = rd
    while not os.path.isdir(anc) and os.path.dirname(anc) != anc:
        anc = os.path.dirname(anc)
    probe = os.path.join(rd, 'adsblol_00000000_00.jsonl.gz')
    try:
        r = subprocess.run(['git', '-C', anc, 'check-ignore', '-q', '--no-index', probe], capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return (True, 'git not available; hwd3d path rule only') if inside else (True, 'git not available')
    if r.returncode == 0:
        return True, 'ignored by git'
    if r.returncode == 1:
        return False, f'{rd} is in a git work tree and not ignored by git: `git add` would pick the recordings up'
    return True, 'not in a git work tree'


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


def read_key(a):
    """adsb.lol API key: --adsblol-key-file or $ADSBLOL_API_KEY. Never logged, never written, never committed."""
    if a.adsblol_key_file:
        return open(a.adsblol_key_file).read().strip() or None
    return (os.environ.get('ADSBLOL_API_KEY') or '').strip() or None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--host', default='127.0.0.1', help='0.0.0.0 to open it from a phone on the same Wi-Fi')
    ap.add_argument('--radius', type=int, default=RADIUS_NM, help='NM around the HWD ARP (integer; default 8)')
    ap.add_argument('--no-adsbfi', action='store_true', help='never contact adsb.fi (adsb.lol only)')
    ap.add_argument('--adsblol-daily', type=int, default=None,
                    help=f'adsb.lol requests per rolling 24 h this IP/key may make (default {ADSBLOL_DAILY} unkeyed, '
                         'as documented; set your tier with a key, e.g. 7200 for a feeder key)')
    ap.add_argument('--adsblol-horizon', type=float, default=QUOTA_HORIZON,
                    help='seconds of watching the remaining adsb.lol budget is spread over (default 3600)')
    ap.add_argument('--adsblol-key-file', help='file holding an adsb.lol API key (else $ADSBLOL_API_KEY); sent as x-api-key')
    ap.add_argument('--no-ident', action='store_true', help='do not load the local Mictronics lookup')
    ap.add_argument('--ident', choices=['full', 'type-only'], default='full',
                    help='full: D1 masks LADD/PIA aircraft only (default); type-only: mask every aircraft')
    ap.add_argument('--record', help='also append every adsb.lol response to this directory (record.py format); '
                                     'must not be served: not under hwd3d/ except refs/cache/local/ or out/ (not out/replay)')
    ap.add_argument('--replay', help="'rec_pack' (sfo3d's committed adsb.lol hours) or a directory of recordings")
    ap.add_argument('--speed', type=float, default=1.0, help='replay speed factor')
    ap.add_argument('--skip', type=float, default=0.0, help='seconds of the recording to skip')
    ap.add_argument('--from', dest='t_from', help='replay start (UTC ISO time or epoch s), e.g. 2026-11-08T20:00Z')
    ap.add_argument('--until', dest='t_until', help='replay end (UTC ISO time or epoch s)')
    ap.add_argument('--loop', action='store_true', help='restart the replay at its end')
    ap.add_argument('--lookahead', type=float, default=60.0,
                    help='replay: seconds the app should display behind (features.replay.lookahead_s; default 60)')
    ap.add_argument('--state-dir', default=STATE_DIR, help='where the adsb.lol request log is kept (never served)')
    ap.add_argument('--quiet', action='store_true', help='no request log')
    a = ap.parse_args()

    ident = None if a.no_ident else Mictronics()
    hub = Hub('replay' if a.replay else 'live', ident=ident, d1=D1(a.ident))
    replay_clock = Clock() if a.replay else None
    if a.replay:
        replay_clock.src0 = replay_clock.wall0 = time.time()     # replaced when the replay starts
    metar = Metar(replay_clock)
    hub.clock = replay_clock
    app = {'hub': hub, 'metar': metar, 'ident': ident, 't_start': time.time(), 'quiet': a.quiet, 'radius': a.radius}
    writer = None
    if a.record:
        ok, why = record_dir_check(a.record)
        if not ok:
            sys.exit(f'--record {a.record}: recordings hold identities; {why}')
        rd = os.path.realpath(a.record)
        writer = RecordWriter(rd)
        hub.ext.append(writer.write)
        app['record_dir'] = a.record
    if a.replay:
        root = replay_source(a.replay)
        t_from = parse_time(a.t_from)
        if t_from is None:
            first = next(replay_records(root), None)
            t_from = (first[0] if first else 0) + a.skip
        else:
            t_from += a.skip
        t_until = parse_time(a.t_until)
        app['replay_info'] = {'src': 'rec_pack' if root == REC_PACK else os.path.basename(root),
                              'from': int(t_from * 1000), 'until': int(t_until * 1000) if t_until else None,
                              'speed': a.speed, 'loop': a.loop, 'lookahead_s': a.lookahead}
        hub.replay_pos = None
        threading.Thread(target=run_replay, args=(hub, root, a.speed, t_from, t_until, a.loop, replay_clock, a.radius),
                         daemon=True).start()
        hub.last_client = float('inf')
    else:
        # --record keeps adsb.lol polling with no client (that is what it records); adsb.fi is live-only (never recorded) and
        # is polled only while a client is connected (fix round 1: it was polled every 2 s around the clock)
        active_rec = (lambda: True) if writer else hub.active
        key = read_key(a)
        for pid, prov in PROVIDERS.items():
            if pid == 'adsbfi' and a.no_adsbfi:
                continue
            quota, hdr = None, {}
            if pid == 'adsblol':
                daily = a.adsblol_daily or ADSBLOL_DAILY
                quota = Quota(os.path.join(a.state_dir, 'adsblol_quota.json'), daily, horizon=a.adsblol_horizon)
                if key:
                    hdr['x-api-key'] = key
            p = Poller(prov, hub.on_result, ARP[0], ARP[1], a.radius, active=(hub.active if pid == 'adsbfi' else active_rec), quota=quota, headers=hdr)
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
    print(f'Hayward Live 3D relay {VERSION}: http://{host}:{a.port}/  '
          f'({"replay of " + a.replay if a.replay else "live"}; radius {a.radius} NM; D1 {a.ident})')
    if not a.replay:
        lol = hub.pollers['adsblol']
        print(f'ADS-B: adsb.lol (ODbL 1.0; quota {lol.quota.daily}/24 h, {lol.quota.left()} left, '
              f'{"keyed" if "x-api-key" in lol.headers else "unkeyed"})'
              + ('' if a.no_adsbfi else ' + adsb.fi (personal non-commercial, live only)'), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if writer:
            writer.close()


if __name__ == '__main__':
    main()
