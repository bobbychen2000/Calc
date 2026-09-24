#!/usr/bin/env python3
"""Analyse the live ADS-B recordings around SFO and regenerate the numbers quoted in docs/research/realtime_feeds.md.

Input:  refs/cache/rec/<provider>_<YYYYmmdd_HH>.jsonl.gz written by tools/live/record.py. One JSON line per request:
        {"t": local time the request was STARTED (s), "p": provider, "d": response} or {"t", "p", "err"}.
        adsb.fi (opendata.adsb.fi/api/v2/lat/../lon/../dist/..) lists aircraft under 'aircraft', 'now' in seconds;
        adsb.lol (api.adsb.lol/v2/point/..) lists them under 'ac', 'now' in milliseconds.
        Also optional OpenSky probes in refs/cache/feeds/opensky/probe*.json (+ .t = request start/end times) and the
        KSFO METARs in refs/cache/feeds/metar_ksfo*.json (aviationweather.gov data API).
Output: a text report on stdout and refs/cache/feeds/analysis.json (gitignored: derived from the providers' data).

Reads the recordings with its own gzip reader: when the recorder is restarted it appends a new gzip member after a
truncated one, which a plain decompressor (and tools/live/recio.py at the time of writing) stops at.

Field meanings follow the readsb JSON documentation (github.com/wiedehopf/readsb README-json.md, commit 843d8e3):
  seen_pos = seconds before 'now' that the position was last updated; type = source of the data (adsb_icao, adsr_icao,
  tisb_*, mlat, mode_s, ...); alt_geom = GNSS altitude "referenced to the WGS84 ellipsoid"; true_heading "usually only
  transmitted on ground"; nav_qnh = altimeter setting (hPa).
Constants:
  ARP 37.6188056 N, 122.3754167 W (FAA 5010 via js/geo.js ARP); runway ends parsed from js/geo.js RWY_ENDS (FAA/AirNav).
  EGM96 geoid undulation at the ARP N = -32.29 m (PROJ grid us_nga_egm96_15.tif from cdn.proj.org, computed with pyproj)
  -> an ellipsoidal (HAE) height is 105.9 ft lower than the MSL height.
  Pressure-altitude -> QNH altitude: H = Hp + 145366.45 * (1 - (1013.25/QNH)^0.190284) ft (standard atmosphere).
All positions are compared in a local tangent plane at the ARP (equirectangular, WGS84 radii) - adequate within 40 NM.

Usage: python3 tools/live/analyze_feeds.py [--from 2026-09-24T07:27] [--to ...] [--hours H] [--no-net] [--quiet]
       python3 tools/live/analyze_feeds.py --markdown           # the tables pasted into docs/research/realtime_feeds.md
       python3 tools/live/analyze_feeds.py --opensky-probe 2    # first make 2 anonymous OpenSky bbox requests (1 credit each)
Times are UTC. Event detection (arrivals, departures, runway, go-arounds, air/ground flag flapping, vanish/appear) runs on
the merged freshest-position stream of both providers.
"""
import argparse, bisect, collections, glob, heapq, json, math, os, re, sys, time, urllib.request, zlib
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
REC = os.path.join(ROOT, 'refs', 'cache', 'rec')
CACHE = os.path.join(ROOT, 'refs', 'cache', 'feeds')
PROVIDERS = ('adsbfi', 'adsblol')
ARP_LAT, ARP_LON = 37.6188056, -122.3754167
GEOID_N_FT = -32.29 / 0.3048            # EGM96 at the ARP (see header)
M_LAT = 111132.954 - 559.822 * math.cos(2 * math.radians(ARP_LAT)) + 1.175 * math.cos(4 * math.radians(ARP_LAT))
M_LON = 111412.84 * math.cos(math.radians(ARP_LAT)) - 93.5 * math.cos(3 * math.radians(ARP_LAT))
NM = 1852.0
VEHICLE_CATS = {'C1', 'C2', 'C3', 'C4', 'C5'}          # emitter categories C1 emergency / C2 service vehicle, C3-C5 obstacles (OpenSky REST doc category list)
VEHICLE_TYPES = {'SERV', 'GRND', 'TWR'}                  # aircraft-database pseudo types: SERV observed in the feeds; GRND/TWR assumed


def en(lat, lon):
    return ((lon - ARP_LON) * M_LON, (lat - ARP_LAT) * M_LAT)


# ---------------------------------------------------------------------------------------------------- reading
HDR = re.compile(b'\x1f\x8b\x08')


def gz_members(raw):
    """Decompress every gzip member; a truncated member (recorder killed) is kept up to where it breaks."""
    cuts = [m.start() for m in HDR.finditer(raw)] + [len(raw)]
    cur, out = None, []
    for a, b in zip(cuts[:-1], cuts[1:]):
        seg = raw[a:b]
        if cur is not None and not cur.eof:
            try:
                out.append(cur.decompress(seg)); continue
            except zlib.error:
                pass                               # this header starts a new member
        if out:
            yield b''.join(out)
        out, cur = [], zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            out.append(cur.decompress(seg))
        except zlib.error:
            cur = None                            # false header match inside compressed data
    if out:
        yield b''.join(out)


def records(provider, t0=None, t1=None, stats=None):
    for path in sorted(glob.glob(os.path.join(REC, f'{provider}_*.jsonl.gz'))):
        with open(path, 'rb') as f:
            raw = f.read()
        for blob in gz_members(raw):
            for line in blob.split(b'\n'):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    if stats is not None: stats['bad_lines'] += 1
                    continue
                t = r.get('t')
                if t is None or (t0 and t < t0) or (t1 and t >= t1):
                    continue
                r['_len'] = len(line)
                yield r


def snapshot(r):
    """-> (now_s, aircraft list) of a successful record, else None."""
    d = r.get('d')
    if not isinstance(d, dict):
        return None
    now = d.get('now') or d.get('ctime')
    if now is None:
        return None
    now = now / 1000.0 if now > 1e11 else float(now)
    return now, (d.get('aircraft') if 'aircraft' in d else d.get('ac')) or []


# ---------------------------------------------------------------------------------------------------- statistics helpers
def pct(vals, qs=(0.1, 0.5, 0.9, 0.99)):
    if not vals:
        return {'n': 0}
    s = sorted(vals); n = len(s)
    return {f'p{int(q * 100)}': round(s[min(n - 1, int(q * (n - 1) + 0.5))], 3) for q in qs} | {'n': n, 'mean': round(sum(s) / n, 3)}


class Hist:
    """Streaming histogram with fixed bin width (keeps memory flat over many hours of 1 Hz data)."""
    def __init__(self, w=0.1): self.w, self.c, self.n = w, collections.Counter(), 0
    def add(self, v): self.c[int(math.floor(v / self.w))] += 1; self.n += 1
    def q(self, qs=(0.1, 0.5, 0.9, 0.99)):
        if not self.n: return None
        out, keys, acc, i = {}, sorted(self.c), 0, 0
        targets = [(q, q * self.n) for q in qs]
        for k in keys:
            acc += self.c[k]
            while i < len(targets) and acc >= targets[i][1]:
                out[f'p{int(targets[i][0] * 100)}'] = round((k + 0.5) * self.w, 3); i += 1
        tot = sum((k + 0.5) * self.w * c for k, c in self.c.items())
        return out | {'n': self.n, 'mean': round(tot / self.n, 3)}
    def frac_above(self, v):
        if not self.n: return None
        return round(sum(c for k, c in self.c.items() if (k * self.w) >= v) / self.n, 4)


def ang(a, b):
    return abs((a - b + 180) % 360 - 180)


# ---------------------------------------------------------------------------------------------------- runways
def runway_ends():
    txt = open(os.path.join(ROOT, 'js', 'geo.js')).read()
    ends = {}
    for m in re.finditer(r"'(\d+[LRC]?)':\s*\{\s*lat:\s*dms\((\d+),\s*([\d.]+)\),\s*lon:\s*-dms\((\d+),\s*([\d.]+)\),\s*elev:\s*([\d.]+),\s*disp:\s*(\d+)", txt):
        name, la, lam, lo, lom, elev, disp = m.groups()
        ends[name] = (int(la) + float(lam) / 60, -(int(lo) + float(lom) / 60), float(elev), int(disp))
    pairs = [('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')]
    rw = {}
    for a, b in pairs:
        pa, pb = en(*ends[a][:2]), en(*ends[b][:2])
        L = math.hypot(pb[0] - pa[0], pb[1] - pa[1]); u = ((pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L)
        for name, p0, uu, disp in ((a, pa, u, ends[a][3]), (b, pb, (-u[0], -u[1]), ends[b][3])):
            hdg = math.degrees(math.atan2(uu[0], uu[1])) % 360
            rw[name] = {'p0': p0, 'u': uu, 'len': L, 'hdg': hdg, 'disp_m': disp * 0.3048}
    return rw


def rw_frame(rw, x, y):
    """along (m from the runway END, + toward the far end), cross (m, + right of the landing direction)."""
    dx, dy = x - rw['p0'][0], y - rw['p0'][1]
    u = rw['u']
    return dx * u[0] + dy * u[1], dx * u[1] - dy * u[0]


def classify_runway(rws, pts, mode):
    """pts: [(x, y, track)] airborne points of an arrival (last before touchdown) or departure (first after lift-off).
    Score each runway direction by the median |cross-track| of points aligned with it and in its approach / climb-out
    corridor. Returns (best, score_m, second, second_score_m, n_points)."""
    scores = []
    for name, rw in rws.items():
        xs = []
        for x, y, trk in pts:
            a, c = rw_frame(rw, x, y)
            if trk is not None and ang(trk, rw['hdg']) > 25:
                continue
            if mode == 'arr' and -9000 <= a <= 600:
                xs.append(abs(c))
            elif mode == 'dep' and rw['len'] * 0.3 <= a <= rw['len'] + 6000:
                xs.append(abs(c))
        if len(xs) >= 2:
            xs.sort(); scores.append((xs[len(xs) // 2], name, len(xs)))
    scores.sort()
    if not scores:
        return None
    best = scores[0]; second = scores[1] if len(scores) > 1 else (None, None, 0)
    return best[1], round(best[0], 1), second[1], (round(second[0], 1) if second[0] is not None else None), best[2]


# ---------------------------------------------------------------------------------------------------- METAR / QNH
def metar_series(t0, t1, net=True):
    files = sorted(glob.glob(os.path.join(CACHE, 'metar_ksfo*.json')))
    obs = {}
    for f in files:
        try:
            for m in json.load(open(f)):
                if m.get('altim'): obs[m['obsTime']] = (m['altim'], m.get('temp'), m.get('rawOb'))
        except Exception:
            pass
    need = not obs or min(obs) > t0 - 3600 or max(obs) < min(t1, time.time()) - 5400
    if net and need:
        hours = min(48, max(2, int((time.time() - t0) / 3600) + 2))
        url = f'https://aviationweather.gov/api/data/metar?ids=KSFO&format=json&hours={hours}'
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sfo-live-3d analysis'}), timeout=20) as r:
                data = json.loads(r.read())
            out = os.path.join(CACHE, f'metar_ksfo_{time.strftime("%Y%m%d_%H%M", time.gmtime())}.json')
            json.dump(data, open(out, 'w'))
            for m in data:
                if m.get('altim'): obs[m['obsTime']] = (m['altim'], m.get('temp'), m.get('rawOb'))
        except Exception as e:
            print('METAR fetch failed:', e, file=sys.stderr)
    return sorted(obs.items())


def qnh_at(series, t):
    if not series: return None
    i = bisect.bisect_right([s[0] for s in series], t) - 1
    return series[max(0, i)][1][0]


def qnh_alt(hp, qnh):
    return hp + 145366.45 * (1 - (1013.25 / qnh) ** 0.190284)


# ---------------------------------------------------------------------------------------------------- OpenSky probe
def opensky_probe(n):
    os.makedirs(os.path.join(CACHE, 'opensky'), exist_ok=True)
    url = 'https://opensky-network.org/api/states/all?lamin=37.2&lomin=-122.9&lamax=38.0&lomax=-121.8'   # 0.88 sq deg: 1 credit
    for i in range(n):
        stem = os.path.join(CACHE, 'opensky', f'probe_{time.strftime("%Y%m%d_%H%M%S", time.gmtime())}')
        t0 = time.time()
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sfo-live-3d/0.1'}), timeout=30) as r:
            body = r.read(); hdr = dict(r.headers)
        t1 = time.time()
        open(stem + '.json', 'wb').write(body); open(stem + '.t', 'w').write(f'{t0} {t1}')
        json.dump(hdr, open(stem + '.hdr.json', 'w'))
        print('opensky probe', stem, 'remaining credits', hdr.get('X-Rate-Limit-Remaining') or hdr.get('x-rate-limit-remaining'))
        if i + 1 < n: time.sleep(15)


def load_opensky():
    out = []
    for f in sorted(glob.glob(os.path.join(CACHE, 'opensky', 'probe*.json'))):
        if f.endswith('.hdr.json'): continue
        tf = f[:-5] + '.t'
        if not os.path.exists(tf): continue
        t0, t1 = map(float, open(tf).read().split()[:2])
        try:
            d = json.load(open(f))
        except ValueError:
            continue
        out.append({'file': os.path.relpath(f, ROOT), 't0': t0, 't1': t1, 'time': d.get('time'), 'states': d.get('states') or []})
    return out


# ---------------------------------------------------------------------------------------------------- main analysis
def analyse(t0, t1, net=True):
    rws = runway_ends()
    meta = {'bad_lines': 0}
    def tagged(i, p):
        for r in records(p, t0, t1, meta):
            yield r['t'], i, p, r
    streams = [tagged(i, p) for i, p in enumerate(PROVIDERS)]
    P = {p: {
        'req': 0, 'ok': 0, 'err': collections.Counter(), 'err_runs': [], '_run': 0, 'ok_t': [], 'lag': Hist(0.05),
        'nows': [], 'dup_now': 0, '_last_now': None, 'n_ac': [], 'seen_pos_all': Hist(0.1), 'seen_pos_gnd': Hist(0.1),
        'seen_pos_app': Hist(0.1), 'age_req_app': Hist(0.1), 'age_req_gnd': Hist(0.1),
        'upd_app': Hist(0.25), 'upd_gnd_moving': Hist(0.25), 'upd_gnd_still': Hist(0.25), 'upd_air_far': Hist(0.25),
        'type_all': collections.Counter(), 'type_gnd': collections.Counter(), 'type_app': collections.Counter(),
        'gnd_fields': collections.Counter(), 'gnd_n': 0, 'gnd_moving_fields': collections.Counter(), 'gnd_moving_n': 0,
        'gnd_still_fields': collections.Counter(), 'gnd_still_n': 0, 'gnd_counts': [], 'no_pos': 0, 'lastpos_only': 0,
        'hdg_quant': collections.Counter(), 'air_fields': collections.Counter(), 'air_n': 0,
        'lowslow_air': 0, 'hexes': set(), 'hexes_gnd': set(), 'nonicao': 0,
        '_last_pos': {}, 'db_fields': collections.Counter(), 'db_n': 0,
        '_prev_t': None, 'gap_n': collections.Counter(), 'gap_err': collections.Counter(), '_win': collections.deque(),
        'bytes': [], 'win_n': collections.Counter(), 'win_err': collections.Counter(), 'still_pos': {}, 'still_runs': [], 'gnd_hdg_ever': {},
    } for p in PROVIDERS}
    last_snap = {}                      # provider -> (t_req, now, {hex: rec})
    X = {'pairs': 0, 'same_msg': 0, 'same_msg_dist': [], 'fresher': collections.Counter(), 'dt_pos': Hist(0.1),
         'dist_extrap_air': [], 'dist_extrap_gnd': [], 'dist_gnd': [], 'only_gnd_seen': Hist(0.5), 'only_gnd_hex': collections.Counter(), 'only': collections.Counter(), 'both': 0, 'only_gnd': collections.Counter(),
         'both_gnd': 0, 'alt_same': 0, 'alt_diff': 0, 'merged_age_app': Hist(0.1), 'single_age_app': {p: Hist(0.1) for p in PROVIDERS},
         'merged_age_gnd': Hist(0.1), 'single_age_gnd': {p: Hist(0.1) for p in PROVIDERS}, 'types_disagree': collections.Counter()}
    # merged (freshest position per hex) state for event detection
    M = {}
    MU = {'app': Hist(0.25), 'gnd_moving': Hist(0.25)}
    events = {'arr': [], 'dep': [], 'goaround': [], 'vanish_gnd': [], 'appear_gnd': [], 'flap': []}
    vehicles = {}
    alt = {'by_hex': {}, 'by_band': {}, 'geom_minus_qnh': [], 'geom_minus_baro_hi': [], 'navqnh_low': [], 'navqnh_high': [], 'navqnh_minus_metar': []}
    first_file = sorted(glob.glob(os.path.join(REC, '*_*.jsonl.gz')))
    t_rec0 = datetime.strptime(os.path.basename(first_file[0]).split('_', 1)[1][:11], '%Y%m%d_%H').replace(tzinfo=timezone.utc).timestamp() if first_file else time.time()
    metars = metar_series(t0 or t_rec0, t1 or time.time(), net)
    osky = load_opensky()
    os_snap = {i: {} for i in range(len(osky))}   # probe idx -> provider -> (|dt|, t, now, acmap)
    first_t, last_t = None, None

    for t, _, p, r in heapq.merge(*streams, key=lambda e: (e[0], e[1])):
        S = P[p]
        first_t = first_t or t; last_t = t
        S['req'] += 1
        snap = snapshot(r)
        is429 = snap is None and '429' in r.get('err', '')
        if S['_prev_t'] is not None:
            g_ = t - S['_prev_t']
            b_ = '<0.98' if g_ < 0.98 else '0.98-1.02' if g_ < 1.02 else '1.02-1.5' if g_ < 1.5 else '1.5-3' if g_ < 3 else '>=3'
            S['gap_n'][b_] += 1; S['gap_err'][b_] += is429
        S['_prev_t'] = t
        W = S['_win']
        while W and t - W[0] > 60: W.popleft()
        k_ = len(W) // 5 * 5
        S['win_n'][k_] += 1; S['win_err'][k_] += is429
        W.append(t)
        if snap is None:
            e = r.get('err', 'no data')
            key = '429' if '429' in e else ('timeout' if 'timed out' in e.lower() else e[:60])
            S['err'][key] += 1; S['_run'] += 1
            continue
        if S['_run']: S['err_runs'].append(S['_run']); S['_run'] = 0
        now, acs = snap
        S['ok'] += 1; S['ok_t'].append(t); S['lag'].add(t - now)
        if S['_last_now'] == now: S['dup_now'] += 1
        else: S['nows'].append(now)
        dup = S['_last_now'] == now
        S['_last_now'] = now
        S['n_ac'].append(len(acs)); S['bytes'].append(r['_len'])
        acmap, gnd_here = {}, 0
        for a in acs:
            hx = (a.get('hex') or '').lower()
            if hx.startswith('~'): S['nonicao'] += 1
            lat, lon = a.get('lat'), a.get('lon')
            typ = a.get('type', '?')
            if lat is None or lon is None:
                if a.get('lastPosition'): S['lastpos_only'] += 1
                else: S['no_pos'] += 1
                continue
            sp = a.get('seen_pos', a.get('seen', 0.0)) or 0.0
            x, y = en(lat, lon); dist = math.hypot(x, y)
            ab = a.get('alt_baro'); gnd = ab == 'ground'
            post = now - sp
            rec = (post, lat, lon, x, y, ab, a.get('gs'), a.get('track'), a.get('true_heading'), typ, a.get('alt_geom'), a)
            acmap[hx] = rec
            if not dup:
                S['type_all'][typ] += 1; S['seen_pos_all'].add(sp); S['hexes'].add(hx)
                S['db_n'] += 1
                for k in ('r', 't', 'desc', 'ownOp', 'year', 'flight'):
                    if a.get(k): S['db_fields'][k] += 1
            near_gnd = gnd and dist <= 3000
            app = (not gnd) and dist <= 10 * NM and isinstance(ab, (int, float)) and ab < 5000
            if not dup:
                if near_gnd:
                    gnd_here += 1; S['hexes_gnd'].add(hx)
                    S['seen_pos_gnd'].add(sp); S['age_req_gnd'].add(t - now + sp); S['type_gnd'][typ] += 1; S['gnd_n'] += 1
                    gs = a.get('gs')
                    moving = gs is not None and gs >= 3
                    still = gs is not None and gs < 1
                    for k in ('gs', 'track', 'true_heading', 'mag_heading', 'flight', 'r', 't', 'category', 'squawk'):
                        if a.get(k) is not None:
                            S['gnd_fields'][k] += 1
                            if moving: S['gnd_moving_fields'][k] += 1
                            if still: S['gnd_still_fields'][k] += 1
                    if a.get('track') is not None or a.get('true_heading') is not None:
                        S['gnd_fields']['track|true_heading'] += 1
                        if moving: S['gnd_moving_fields']['track|true_heading'] += 1
                        if still: S['gnd_still_fields']['track|true_heading'] += 1
                    if moving: S['gnd_moving_n'] += 1
                    if still:
                        S['gnd_still_n'] += 1
                    # stationary runs (gs < 1 kt continuously, no gap > 60 s): positional jitter of parked / holding aircraft
                    run = S['still_pos'].get(hx)
                    if still and run is not None and post - run['t1'] <= 60:
                        run['pts'][round(post, 1)] = (x, y); run['t1'] = post
                    else:
                        if run is not None: S['still_runs'].append(run)
                        S['still_pos'][hx] = {'t0': post, 't1': post, 'pts': {round(post, 1): (x, y)}} if still else None
                    S['gnd_hdg_ever'].setdefault(hx, False)
                    if a.get('track') is not None or a.get('true_heading') is not None: S['gnd_hdg_ever'][hx] = True
                    th = a.get('true_heading')
                    if th is not None:
                        q = th / (360 / 128)
                        S['hdg_quant']['7bit' if abs(q - round(q)) < 0.01 else 'other'] += 1
                    cat, ty = a.get('category'), a.get('t')
                    fl = (a.get('flight') or '').strip()
                    if cat in VEHICLE_CATS or ty in VEHICLE_TYPES or re.match(r'^(OPS|FOLLOW|FIRE|RESCUE|SNOW|TUG)', fl):
                        v = vehicles.setdefault(hx, {'flight': set(), 'r': a.get('r'), 't': ty, 'category': cat, 'ownOp': a.get('ownOp'),
                                                     'types': collections.Counter(), 'seen': collections.Counter(), 'max_gs': 0})
                        if fl: v['flight'].add(fl)
                        v['types'][typ] += 1; v['seen'][p] += 1; v['max_gs'] = max(v['max_gs'], gs or 0)
                        v['ownOp'] = v['ownOp'] or a.get('ownOp'); v['t'] = v['t'] or ty; v['category'] = v['category'] or cat
                if app:
                    S['seen_pos_app'].add(sp); S['age_req_app'].add(t - now + sp); S['type_app'][typ] += 1
                    S['air_n'] += 1
                    for k in ('alt_geom', 'gs', 'track', 'true_heading', 'baro_rate', 'geom_rate', 'nav_qnh', 'flight', 'r', 't', 'squawk'):
                        if a.get(k) is not None: S['air_fields'][k] += 1
                    if dist < 5000 and ab < 150 and (a.get('gs') or 999) < 40: S['lowslow_air'] += 1
            # per-aircraft position update intervals (distinct position times)
            lp = S['_last_pos'].get(hx)
            if lp is None or post > lp[0] + 0.05:
                if lp is not None and post - lp[0] < 120:
                    dt = post - lp[0]
                    if near_gnd:
                        gs = a.get('gs')
                        if gs is not None and gs >= 3: S['upd_gnd_moving'].add(dt)
                        elif gs is not None and gs < 1: S['upd_gnd_still'].add(dt)
                    elif app: S['upd_app'].add(dt)
                    elif not gnd and dist > 20 * NM: S['upd_air_far'].add(dt)
                S['_last_pos'][hx] = (post,)
        if not dup: S['gnd_counts'].append(gnd_here)
        last_snap[p] = (t, now, acmap)

        # ---- altitude / QNH checks (adsb.fi only, to count each report once)
        if p == PROVIDERS[0] and not dup and metars:
            qm = qnh_at(metars, now)
            for hx, rec in acmap.items():
                a = rec[11]; ab = rec[5]
                if not isinstance(ab, (int, float)): continue
                dist = math.hypot(rec[3], rec[4])
                if a.get('nav_qnh') is not None and dist < 30 * NM and now - rec[0] < 5:
                    if ab < 10000: alt['navqnh_low'].append(a['nav_qnh']); alt['navqnh_minus_metar'].append(a['nav_qnh'] - qm)
                    elif ab > 20000: alt['navqnh_high'].append(a['nav_qnh'])
                if rec[10] is not None and dist < 20 * NM and ab < 5000 and qm:
                    # alt_geom minus QNH altitude: ~ geoid offset (-106 ft) if alt_geom is ellipsoidal (HAE), ~0 if MSL,
                    # plus the altimeter's temperature error, which grows with height -> judge the reference below 1000 ft
                    dz = rec[10] - qnh_alt(ab, qm)
                    band = int(ab // 500) * 500 if ab < 2000 else int(ab // 1000) * 1000
                    alt['by_band'].setdefault(band, []).append(dz)
                    if ab < 1000:
                        alt['geom_minus_qnh'].append(dz)
                        alt['by_hex'].setdefault(hx, {'t': a.get('t'), 'version': a.get('version'), 'dz': []})['dz'].append(dz)
                if rec[10] is not None and ab > 25000:
                    alt['geom_minus_baro_hi'].append(rec[10] - ab)

        # ---- cross-provider comparison at matched request times
        q = PROVIDERS[1] if p == PROVIDERS[0] else PROVIDERS[0]
        if q in last_snap and abs(last_snap[q][0] - t) <= 0.6 and not dup:
            tq, nowq, mq = last_snap[q]
            X['pairs'] += 1
            ref = max(now, nowq)
            for hx in set(acmap) | set(mq):
                ra, rb = acmap.get(hx), mq.get(hx)
                if ra and math.hypot(ra[3], ra[4]) > 38 * NM: ra = None      # stay clear of the 40 NM edge
                if rb and math.hypot(rb[3], rb[4]) > 38 * NM: rb = None
                if not ra and not rb: continue
                g = (ra or rb)[5] == 'ground' and math.hypot((ra or rb)[3], (ra or rb)[4]) <= 3000
                if ra and rb:
                    X['both'] += 1
                    if g: X['both_gnd'] += 1
                    fa, fb = (ra, rb) if p == PROVIDERS[0] else (rb, ra)       # fa = adsb.fi, fb = adsb.lol
                    d_t = fa[0] - fb[0]
                    X['dt_pos'].add(d_t)
                    X['fresher']['adsbfi' if d_t > 0.05 else ('adsblol' if d_t < -0.05 else 'same')] += 1
                    if fa[9] != fb[9]: X['types_disagree'][f'{fa[9]}|{fb[9]}'] += 1
                    dist = math.hypot(fa[3] - fb[3], fa[4] - fb[4])
                    if abs(d_t) <= 0.05:
                        X['same_msg'] += 1; X['same_msg_dist'].append(dist)
                        if isinstance(fa[5], (int, float)) and isinstance(fb[5], (int, float)):
                            if fa[5] == fb[5]: X['alt_same'] += 1
                            else: X['alt_diff'] += 1
                    elif fa[5] == 'ground' and (fa[6] or 0) < 1 and (fb[6] or 0) < 1:
                        X['dist_gnd'].append(dist)
                    elif fa[6] is not None and fa[7] is not None and fb[6] is not None and fb[7] is not None and abs(d_t) < 10:
                        old, new = (fb, fa) if d_t > 0 else (fa, fb)
                        dtt = new[0] - old[0]
                        v = old[6] * NM / 3600
                        xo = old[3] + v * dtt * math.sin(math.radians(old[7])); yo = old[4] + v * dtt * math.cos(math.radians(old[7]))
                        (X['dist_extrap_gnd'] if fa[5] == 'ground' else X['dist_extrap_air']).append(math.hypot(new[3] - xo, new[4] - yo))
                    ages = {'adsbfi': ref - fa[0], 'adsblol': ref - fb[0]}
                else:
                    who = 'adsbfi' if (ra if p == PROVIDERS[0] else rb) else 'adsblol'
                    X['only'][who] += 1
                    one = ra or rb
                    if g:
                        X['only_gnd'][who] += 1
                        if who == 'adsbfi': X['only_gnd_seen'].add(ref - one[0]); X['only_gnd_hex'][hx] += 1
                    ages = {who: ref - one[0]}
                one = ra or rb
                is_app = one[5] != 'ground' and isinstance(one[5], (int, float)) and one[5] < 5000 and math.hypot(one[3], one[4]) <= 10 * NM
                if is_app or g:
                    mh, sh = (X['merged_age_app'], X['single_age_app']) if is_app else (X['merged_age_gnd'], X['single_age_gnd'])
                    mh.add(min(ages.values()))
                    for pp in PROVIDERS:
                        if pp in ages: sh[pp].add(ages[pp])

        # ---- OpenSky probe matching (keep the snapshot nearest in time to each probe's reference time)
        for i, pr in enumerate(osky):
            ref_t = pr['time'] or pr['t0']
            dd = abs(now - ref_t)
            cur = os_snap[i].get(p)
            if dd < 30 and (cur is None or dd < cur[0]):
                os_snap[i][p] = (dd, t, now, acmap)

        # ---- merged freshest-position stream + events
        for hx, rec in acmap.items():
            m = M.get(hx)
            if m is not None and rec[0] <= m['post'] + 0.05:
                continue
            post, lat, lon, x, y, ab, gs, trk, th = rec[:9]
            a = rec[11]
            if m is None:
                m = M[hx] = {'post': post, 'air': collections.deque(maxlen=400), 'gnd': None, 'first': post, 'first_gnd': ab == 'ground',
                             'last_gnd': None, 'dep_pts': None, 'cs': None, 'min_app': None, 'events': []}
                if ab == 'ground' and math.hypot(x, y) < 3000 and post - first_t > 300:
                    events['appear_gnd'].append({'hex': hx, 't': post, 'gs': gs, 'flight': (a.get('flight') or '').strip(), 'r': a.get('r'), 'type': rec[9]})
            prev_gnd = m['gnd']
            dtm = post - m['post']
            if dtm < 120:
                if ab == 'ground' and math.hypot(x, y) <= 3000 and (gs or 0) >= 3: MU['gnd_moving'].add(dtm)
                elif ab != 'ground' and isinstance(ab, (int, float)) and ab < 5000 and math.hypot(x, y) <= 10 * NM: MU['app'].add(dtm)
            m['post'] = post; m['cs'] = (a.get('flight') or '').strip() or m['cs']; m['r'] = a.get('r'); m['t'] = a.get('t')
            dist = math.hypot(x, y)
            if ab == 'ground':
                if prev_gnd is False and m['air'] and post - m['air'][-1][0] < 90 and dist < 4500:
                    pts = [(px, py, pt) for (tt, px, py, pa, pt, pg, pv) in m['air'] if post - tt < 150]
                    maxgs = max([pv or 0 for (tt, px, py, pa, pt, pg, pv) in m['air'] if post - tt < 150] or [0])
                    res = classify_runway(rws, pts, 'arr')
                    last = m['air'][-1]
                    ev = {'hex': hx, 'cs': m['cs'], 'r': m['r'], 'type': m['t'], 't_gnd': round(post, 1), 'gap_s': round(post - last[0], 1),
                          'last_air_alt': last[3], 'last_air_alt_geom_msl_ft': round(last[5] - GEOID_N_FT) if last[5] is not None else None, 'rwy': res}
                    if res:
                        a0, c0 = rw_frame(rws[res[0]], x, y)
                        ev['touch_along_m'] = round(a0); ev['touch_cross_m'] = round(c0)
                        ev['first_ground_report_past_threshold_m'] = round(a0 - rws[res[0]]['disp_m'])
                    # an 'airborne' spell below 60 kt is a transponder air/ground flag flapping on the ground, not a landing
                    (events['arr'] if maxgs >= 60 else events['flap']).append(ev | {'max_gs': maxgs})
                    m['min_app'] = None
                m['gnd'] = True; m['last_gnd'] = (post, x, y, gs, a.get('flight'))
            elif isinstance(ab, (int, float)):
                if prev_gnd is True and m['last_gnd'] and post - m['last_gnd'][0] < 90 and dist < 6000:
                    m['dep_pts'] = {'t_air': post, 'gap_s': round(post - m['last_gnd'][0], 1), 'pts': [], 'maxgs': 0}
                m['gnd'] = False
                m['air'].append((post, x, y, ab, trk, rec[10], gs))
                if m['dep_pts'] is not None:
                    if post - m['dep_pts']['t_air'] < 75:
                        m['dep_pts']['pts'].append((x, y, trk)); m['dep_pts']['maxgs'] = max(m['dep_pts']['maxgs'], gs or 0)
                    else:
                        res = classify_runway(rws, m['dep_pts']['pts'], 'dep')
                        (events['dep'] if m['dep_pts']['maxgs'] >= 60 else events['flap']).append({'hex': hx, 'cs': m['cs'], 'r': m['r'], 'type': m['t'], 't_air': round(m['dep_pts']['t_air'], 1),
                                              'gap_s': m['dep_pts']['gap_s'], 'rwy': res})
                        m['dep_pts'] = None
                # go-around: low on an approach corridor (not just after a take-off), then climbing away without a ground report
                recent_gnd = m['last_gnd'] is not None and post - m['last_gnd'][0] < 600
                if dist < 8000 and ab < 700 and trk is not None and not recent_gnd:
                    for name, rw in rws.items():
                        al, cr = rw_frame(rw, x, y)
                        if -6000 < al < rw['len'] and abs(cr) < 250 and ang(trk, rw['hdg']) < 20:
                            if m['min_app'] is None or ab < m['min_app'][1]:
                                m['min_app'] = (post, ab, name)
                if m['min_app'] and ab > m['min_app'][1] + 1000 and post - m['min_app'][0] < 300:
                    events['goaround'].append({'hex': hx, 'cs': m['cs'], 'r': m['r'], 'type': m['t'], 't_low': round(m['min_app'][0], 1),
                                               'min_alt_baro': m['min_app'][1], 'rwy': m['min_app'][2], 't_climb': round(post, 1)})
                    m['min_app'] = None
                if m['min_app'] and post - m['min_app'][0] > 300: m['min_app'] = None
        # aircraft that vanished while on the ground near the ARP (transponder switched off at the gate?)
        if p == PROVIDERS[0] and not dup:
            for hx in list(M):
                m = M[hx]
                if now - m['post'] > 300:
                    if m['gnd'] and m['last_gnd'] and math.hypot(m['last_gnd'][1], m['last_gnd'][2]) < 3000:
                        events['vanish_gnd'].append({'hex': hx, 'cs': m['cs'], 'r': m['r'], 'type': m['t'], 't_last': round(m['post'], 1),
                                                     'last_gs': m['last_gnd'][3]})
                    del M[hx]

    # ------------------------------------------------------------------ summarise
    def jitter(S):
        # per stationary run >= 60 s: 95th percentile distance of the reported positions from their median
        per = []
        for run in S['still_runs'] + [r for r in S['still_pos'].values() if r]:
            pts = run['pts']
            if run['t1'] - run['t0'] < 60 or len(pts) < 10: continue
            xs = sorted(v[0] for v in pts.values()); ys = sorted(v[1] for v in pts.values())
            mx, my = xs[len(xs) // 2], ys[len(ys) // 2]
            d = sorted(math.hypot(v[0] - mx, v[1] - my) for v in pts.values())
            per.append(d[int(0.95 * (len(d) - 1))])
        return pct(per, (0.5, 0.9, 0.99, 1.0)) | {'runs_ge_60s': len(per)}

    out = {'window_utc': [datetime.fromtimestamp(first_t or 0, timezone.utc).isoformat(timespec='seconds'),
                          datetime.fromtimestamp(last_t or 0, timezone.utc).isoformat(timespec='seconds')],
           'hours': round(((last_t or 0) - (first_t or 0)) / 3600, 2), 'bad_lines': meta['bad_lines'], 'providers': {}}
    for p, S in P.items():
        okt = S['ok_t']; gaps = [b - a for a, b in zip(okt, okt[1:])]
        nows = S['nows']; steps = collections.Counter(round(b - a, 1) for a, b in zip(nows, nows[1:]))
        fr = lambda c, n: {k: round(v / n, 3) for k, v in sorted(c.items(), key=lambda kv: -kv[1])} if n else {}
        out['providers'][p] = {
            'requests': S['req'], 'ok': S['ok'], 'errors': dict(S['err']), 'error_rate': round(1 - S['ok'] / max(1, S['req']), 4),
            'error_run_lengths': dict(collections.Counter(S['err_runs'])),
            'ok_interval_s': pct(gaps, (0.5, 0.9, 0.99)) | {'max': round(max(gaps), 1) if gaps else None},
            'distinct_snapshots': len(nows), 'duplicate_snapshots': S['dup_now'], 'now_step_s': dict(steps.most_common(6)),
            'now_fraction_s': dict(collections.Counter(round(n % 1, 1) for n in nows).most_common(4)),
            't_request_minus_now_s': S['lag'].q((0.01, 0.1, 0.5, 0.9, 0.99)),
            'aircraft_per_snapshot': pct(S['n_ac'], (0.1, 0.5, 0.9)),
            'json_bytes_per_response': pct(S['bytes'], (0.5, 0.9)),
            'ground_3km_per_snapshot': pct(S['gnd_counts'], (0.1, 0.5, 0.9)) | {'max': max(S['gnd_counts']) if S['gnd_counts'] else None},
            'distinct_hex_with_pos': len(S['hexes']), 'distinct_hex_ground_3km': len(S['hexes_gnd']),
            'seen_pos_all': S['seen_pos_all'].q(), 'seen_pos_ground_3km': S['seen_pos_gnd'].q(),
            'seen_pos_ground_3km_frac_gt': {s: S['seen_pos_gnd'].frac_above(s) for s in (5, 10, 30)},
            'seen_pos_app_10nm_lt5000ft': S['seen_pos_app'].q(), 'seen_pos_app_frac_gt': {s: S['seen_pos_app'].frac_above(s) for s in (2, 5, 10)},
            'age_at_request_app': S['age_req_app'].q(), 'age_at_request_ground_3km': S['age_req_gnd'].q(),
            'update_interval_app': S['upd_app'].q(), 'update_interval_ground_moving': S['upd_gnd_moving'].q(),
            'update_interval_ground_stationary': S['upd_gnd_still'].q(), 'update_interval_air_beyond_20nm': S['upd_air_far'].q(),
            'type_mix_all': fr(S['type_all'], sum(S['type_all'].values())), 'type_mix_ground_3km': fr(S['type_gnd'], sum(S['type_gnd'].values())),
            'type_mix_app': fr(S['type_app'], sum(S['type_app'].values())),
            'ground_field_presence': fr(S['gnd_fields'], S['gnd_n']), 'ground_moving_field_presence': fr(S['gnd_moving_fields'], S['gnd_moving_n']),
            'ground_stationary_field_presence': fr(S['gnd_still_fields'], S['gnd_still_n']),
            'ground_reports': S['gnd_n'], 'ground_moving_reports': S['gnd_moving_n'], 'ground_stationary_reports': S['gnd_still_n'],
            'ground_true_heading_quantisation': dict(S['hdg_quant']),
            'ground_aircraft_with_heading_at_least_once': [sum(S['gnd_hdg_ever'].values()), len(S['gnd_hdg_ever'])],
            'app_field_presence': fr(S['air_fields'], S['air_n']), 'app_reports': S['air_n'],
            'db_field_presence': fr(S['db_fields'], S['db_n']),
            'airborne_but_low_slow_near_arp': S['lowslow_air'], 'entries_without_position': S['no_pos'], 'entries_lastPosition_only': S['lastpos_only'],
            'non_icao_entries': S['nonicao'],
            'rate429_by_gap_since_previous_request': {b: [S['gap_n'][b], round(S['gap_err'][b] / S['gap_n'][b], 3)] for b in sorted(S['gap_n'])},
            'rate429_by_requests_in_previous_60s': {k: [S['win_n'][k], round(S['win_err'][k] / S['win_n'][k], 3)] for k in sorted(S['win_n'])},
            'stationary_run_position_p95_spread_m': jitter(S),
        }
    same = X['same_msg_dist']
    out['cross'] = {
        'matched_snapshot_pairs': X['pairs'], 'hex_in_both': X['both'], 'hex_only': dict(X['only']),
        'ground_3km_in_both': X['both_gnd'], 'ground_3km_only': dict(X['only_gnd']),
        'fresher_position': dict(X['fresher']), 'pos_time_fi_minus_lol_s': X['dt_pos'].q((0.05, 0.25, 0.5, 0.75, 0.95)),
        'same_report_fraction': round(X['same_msg'] / max(1, X['both']), 3),
        'same_report_distance_m': pct(same, (0.5, 0.9, 0.99)),
        'airborne_distance_after_extrapolation_m': pct(X['dist_extrap_air'], (0.5, 0.9, 0.99)),
        'ground_stationary_distance_different_report_m': pct(X['dist_gnd'], (0.5, 0.9, 0.99)),
        'ground_moving_distance_after_extrapolation_m': pct(X['dist_extrap_gnd'], (0.5, 0.9, 0.99)),
        'ground_3km_only_adsbfi_age_s': X['only_gnd_seen'].q((0.1, 0.5, 0.9)),
        'ground_3km_only_adsbfi_top_hex': dict(X['only_gnd_hex'].most_common(8)),
        'alt_baro_equal_fraction_same_report': round(X['alt_same'] / max(1, X['alt_same'] + X['alt_diff']), 3),
        'source_type_disagreements': dict(X['types_disagree'].most_common(8)),
        'merged_update_interval_app': MU['app'].q(), 'merged_update_interval_ground_moving': MU['gnd_moving'].q(),
        'position_age_app': {'merged_freshest': X['merged_age_app'].q((0.5, 0.9, 0.99))} | {p: X['single_age_app'][p].q((0.5, 0.9, 0.99)) for p in PROVIDERS},
        'position_age_ground_3km': {'merged_freshest': X['merged_age_gnd'].q((0.5, 0.9, 0.99))} | {p: X['single_age_gnd'][p].q((0.5, 0.9, 0.99)) for p in PROVIDERS},
    }
    out['altitude'] = {
        'alt_geom_minus_qnh_alt_below1000ft_ft': pct(alt['geom_minus_qnh'], (0.1, 0.5, 0.9)),
        'alt_geom_minus_qnh_alt_by_band_ft': {b: pct(v, (0.1, 0.5, 0.9)) for b, v in sorted(alt['by_band'].items())},
        'expected_if_alt_geom_is_HAE_ft': round(GEOID_N_FT, 1),
        'per_aircraft_median_ft': sorted([(h, v['t'], v['version'], round(sorted(v['dz'])[len(v['dz']) // 2]), len(v['dz']))
                                          for h, v in alt['by_hex'].items() if len(v['dz']) >= 5], key=lambda r: r[3]),
        'alt_geom_minus_alt_baro_above_FL250_ft': pct(alt['geom_minus_baro_hi'], (0.1, 0.5, 0.9)),
        'nav_qnh_below_10000ft_hPa': pct(alt['navqnh_low'], (0.1, 0.5, 0.9)),
        'nav_qnh_minus_metar_hPa': pct(alt['navqnh_minus_metar'], (0.05, 0.5, 0.95)),
        'nav_qnh_above_FL200_hPa': pct(alt['navqnh_high'], (0.1, 0.5, 0.9)),
        'metars': [(datetime.fromtimestamp(tt, timezone.utc).strftime('%H:%MZ'), v[0], v[2]) for tt, v in metars
                   if (not first_t or tt > first_t - 3600) and (not last_t or tt < last_t + 600)],
    }
    arr, dep = events['arr'], events['dep']
    def rwsum(evs):
        c, amb = collections.Counter(), 0
        for e in evs:
            r = e['rwy']
            if not r: c['unassigned'] += 1; continue
            if r[1] > 100: c['unassigned'] += 1; continue
            if r[3] is not None and r[3] < 150: amb += 1
            c[r[0]] += 1
        return dict(c), amb
    ca, amb_a = rwsum(arr); cd, amb_d = rwsum(dep)
    out['events'] = {
        'arrivals': len(arr), 'arrival_runways': ca, 'arrivals_ambiguous': amb_a,
        'arrival_air_to_ground_gap_s': pct([e['gap_s'] for e in arr], (0.5, 0.9, 1.0)),
        'arrival_last_airborne_alt_baro_ft': pct([e['last_air_alt'] for e in arr], (0.1, 0.5, 0.9)),
        'arrival_last_airborne_alt_geom_as_msl_ft': pct([e['last_air_alt_geom_msl_ft'] for e in arr if e.get('last_air_alt_geom_msl_ft') is not None], (0.1, 0.5, 0.9)),
        'arrival_first_ground_report_past_threshold_m': pct([e['first_ground_report_past_threshold_m'] for e in arr if 'first_ground_report_past_threshold_m' in e], (0.1, 0.5, 0.9)),
        'arrival_rwy_score_m': pct([e['rwy'][1] for e in arr if e['rwy']], (0.5, 0.9, 1.0)),
        'arrival_second_best_m': pct([e['rwy'][3] for e in arr if e['rwy'] and e['rwy'][3] is not None], (0.0, 0.1, 0.5)),
        'departures': len(dep), 'departure_runways': cd, 'departures_ambiguous': amb_d,
        'departure_ground_to_air_gap_s': pct([e['gap_s'] for e in dep], (0.5, 0.9, 1.0)),
        'departure_rwy_score_m': pct([e['rwy'][1] for e in dep if e['rwy']], (0.5, 0.9, 1.0)),
        'go_around_candidates': events['goaround'],
        'air_ground_flag_flaps_below_60kt': len(events['flap']), 'air_ground_flap_aircraft': sorted({e['cs'] or e['hex'] for e in events['flap']}),
        'vanished_on_ground_3km': len(events['vanish_gnd']), 'vanished_last_gs_lt1': sum(1 for e in events['vanish_gnd'] if (e['last_gs'] or 0) < 1),
        'appeared_on_ground_3km': len(events['appear_gnd']), 'appeared_stationary': sum(1 for e in events['appear_gnd'] if (e['gs'] or 0) < 1),
        'arrival_list': arr[:400], 'departure_list': dep[:400],
    }
    out['vehicles'] = [{'hex': h, 'flight': sorted(v['flight']), 'r': v['r'], 't': v['t'], 'category': v['category'], 'ownOp': v['ownOp'],
                        'types': dict(v['types']), 'reports_by_provider': dict(v['seen']), 'max_gs': v['max_gs']} for h, v in sorted(vehicles.items())]
    # OpenSky
    oss = []
    for i, pr in enumerate(osky):
        st = pr['states']; row = {'file': pr['file'], 'request_utc': datetime.fromtimestamp(pr['t0'], timezone.utc).isoformat(timespec='seconds'),
                                  'response_time_field': pr['time'], 'time_field_age_at_response_s': round(pr['t1'] - pr['time'], 1) if pr['time'] else None,
                                  'n_states': len(st), 'on_ground': sum(1 for s in st if s[8]),
                                  'position_source': dict(collections.Counter(s[16] for s in st)),
                                  'time_position_age_s': pct([pr['time'] - s[3] for s in st if s[3]], (0.5, 0.9, 1.0))}
        for p in PROVIDERS:
            sn = os_snap[i].get(p)
            if not sn: continue
            _, tq, nowq, mq = sn
            inbox = {h: r for h, r in mq.items() if 37.2 <= r[1] <= 38.0 and -122.9 <= r[2] <= -121.8}
            common = [h for h in (s[0] for s in st) if h in inbox]
            lagv = [inbox[s[0]][0] - s[3] for s in st if s[0] in inbox and s[3]]
            dists = []
            for s in st:            # provider position dead-reckoned to OpenSky's (integer-second) time_position
                rr_ = inbox.get(s[0])
                if rr_ and s[3] and s[5] is not None and abs(rr_[0] - s[3]) < 10:
                    dtt = s[3] - rr_[0]; v = (rr_[6] or 0) * NM / 3600; tr = math.radians(rr_[7] or 0)
                    xo, yo = rr_[3] + v * dtt * math.sin(tr), rr_[4] + v * dtt * math.cos(tr)
                    xx, yy = en(s[6], s[5]); dists.append(math.hypot(xx - xo, yy - yo))
            row[p] = {'snapshot_now_minus_opensky_time_s': round(nowq - pr['time'], 1) if pr['time'] else None, 'n_in_bbox': len(inbox),
                      'common_hex': len(common), 'provider_pos_time_minus_opensky_time_position_s': pct(lagv, (0.5, 0.9)),
                      'position_distance_at_opensky_time_m': pct(dists, (0.5, 0.9, 1.0)),
                      'ground_3km_provider': sum(1 for r in inbox.values() if r[5] == 'ground' and math.hypot(r[3], r[4]) <= 3000),
                      'ground_3km_opensky': sum(1 for s_ in st if s_[8] and s_[5] is not None and math.hypot(*en(s_[6], s_[5])) <= 3000)}
        oss.append(row)
    out['opensky'] = oss
    out['daytime_snapshot'] = daytime_snapshot()
    return out


def daytime_snapshot():
    """The app's shipped snapshot (data/snapshot.js, 23 Sep 2026 10:51 PDT; provider not recorded): one daytime data point."""
    path = os.path.join(ROOT, 'data', 'snapshot.js')
    if not os.path.exists(path): return None
    s = open(path).read()
    d = json.JSONDecoder().raw_decode(s[s.index('{', s.index('SNAPSHOT')):])[0]
    ac = d.get('ac') or []
    g = [a for a in ac if a.get('alt_baro') == 'ground' and a.get('lat') is not None and math.hypot(*en(a['lat'], a['lon'])) <= 3000]
    sp = [a.get('seen_pos', 0) for a in g]
    return {'now_utc': datetime.fromtimestamp(d['now'] / 1000, timezone.utc).isoformat(timespec='seconds'), '_source': d.get('_source'),
            'aircraft': len(ac), 'ground_3km': len(g), 'ground_seen_pos_s': pct(sp, (0.5, 0.9, 1.0)),
            'ground_with_track': sum(1 for a in g if a.get('track') is not None), 'fields': sorted({k for a in ac for k in a})}


def fmt(out):
    L = []
    w = out['window_utc']
    L.append(f"Window {w[0]} .. {w[1]} UTC ({out['hours']} h); unreadable lines {out['bad_lines']}")
    for p, s in out['providers'].items():
        L.append(f"\n== {p}")
        for k, v in s.items():
            L.append(f"  {k}: {json.dumps(v)}")
    L.append('\n== cross-provider (adsbfi vs adsblol, request times within 0.6 s)')
    for k, v in out['cross'].items(): L.append(f"  {k}: {json.dumps(v)}")
    L.append('\n== altitude / QNH')
    for k, v in out['altitude'].items(): L.append(f"  {k}: {json.dumps(v)}")
    L.append('\n== events (merged freshest-position stream)')
    for k, v in out['events'].items():
        if k.endswith('_list'): continue
        L.append(f"  {k}: {json.dumps(v)}")
    L.append('\n== ground vehicles / non-aircraft (within 3 km, on ground)')
    for v in out['vehicles']: L.append('  ' + json.dumps(v))
    L.append('\n== data/snapshot.js (daytime, single snapshot)')
    L.append('  ' + json.dumps(out.get('daytime_snapshot')))
    L.append('\n== OpenSky probes')
    for v in out['opensky']: L.append('  ' + json.dumps(v))
    return '\n'.join(L)


def markdown(out):
    """Key numbers as Markdown tables (pasted into docs/research/realtime_feeds.md section 4)."""
    P = out['providers']; fi, lol = P['adsbfi'], P['adsblol']; X = out['cross']
    g = lambda d, k: (d or {}).get(k, '-')
    def row(name, f, unit=''):
        return f"| {name} | {f(fi)}{unit} | {f(lol)}{unit} |"
    L = [f"Window **{out['window_utc'][0]} to {out['window_utc'][1]} UTC** ({out['hours']} h), "
         f"{fi['requests']} adsb.fi and {lol['requests']} adsb.lol requests.", '',
         '| Metric | adsb.fi (v2 lat/lon/dist) | adsb.lol (v2/point) |', '|---|---|---|',
         row('Requests OK / errors', lambda d: f"{d['ok']} / {sum(d['errors'].values())} ({', '.join(f'{k}: {v}' for k, v in d['errors'].items()) or 'none'})"),
         row('Error rate', lambda d: f"{d['error_rate'] * 100:.1f} %"),
         row('429 rate when the previous request was 0.98-1.02 s earlier', lambda d: f"{d['rate429_by_gap_since_previous_request'].get('0.98-1.02', ['-', '-'])[1]}"),
         row('429 rate when the previous request was >= 3 s earlier', lambda d: f"{d['rate429_by_gap_since_previous_request'].get('>=3', ['-', '-'])[1]}"),
         row('Distinct snapshots / duplicates (same `now`)', lambda d: f"{d['distinct_snapshots']} / {d['duplicate_snapshots']}"),
         row('Step between distinct `now` values (s: count)', lambda d: ', '.join(f'{k}: {v}' for k, v in list(d['now_step_s'].items())[:3])),
         row('Fractional part of `now` (s: count)', lambda d: ', '.join(f'{k}: {v}' for k, v in d['now_fraction_s'].items())),
         row('Request start minus `now`, p10 / p50 / p90 (s)', lambda d: f"{g(d['t_request_minus_now_s'], 'p10')} / {g(d['t_request_minus_now_s'], 'p50')} / {g(d['t_request_minus_now_s'], 'p90')}"),
         row('Aircraft per response, p50 (p10-p90)', lambda d: f"{g(d['aircraft_per_snapshot'], 'p50')} ({g(d['aircraft_per_snapshot'], 'p10')}-{g(d['aircraft_per_snapshot'], 'p90')})"),
         row('Compact JSON per response, p50 (bytes)', lambda d: f"{g(d['json_bytes_per_response'], 'p50')}"),
         row('On-ground within 3 km of ARP per snapshot, p50 (max)', lambda d: f"{g(d['ground_3km_per_snapshot'], 'p50')} ({g(d['ground_3km_per_snapshot'], 'max')})"),
         row('Distinct hex with position / on ground within 3 km', lambda d: f"{d['distinct_hex_with_pos']} / {d['distinct_hex_ground_3km']}"),
         row('seen_pos, all aircraft p50 / p90 / p99 (s)', lambda d: f"{g(d['seen_pos_all'], 'p50')} / {g(d['seen_pos_all'], 'p90')} / {g(d['seen_pos_all'], 'p99')}"),
         row('seen_pos, airborne < 5000 ft within 10 NM, p50 / p90 / p99 (s)', lambda d: f"{g(d['seen_pos_app_10nm_lt5000ft'], 'p50')} / {g(d['seen_pos_app_10nm_lt5000ft'], 'p90')} / {g(d['seen_pos_app_10nm_lt5000ft'], 'p99')}"),
         row('seen_pos, on ground within 3 km, p50 / p90 / p99 (s)', lambda d: f"{g(d['seen_pos_ground_3km'], 'p50')} / {g(d['seen_pos_ground_3km'], 'p90')} / {g(d['seen_pos_ground_3km'], 'p99')}"),
         row('On ground within 3 km: share with seen_pos > 5 / 10 / 30 s', lambda d: ' / '.join(str(v) for v in d['seen_pos_ground_3km_frac_gt'].values())),
         row('Position age at request start (t - now + seen_pos), approach p50 / p90 (s)', lambda d: f"{g(d['age_at_request_app'], 'p50')} / {g(d['age_at_request_app'], 'p90')}"),
         row('Same, on ground within 3 km, p50 / p90 (s)', lambda d: f"{g(d['age_at_request_ground_3km'], 'p50')} / {g(d['age_at_request_ground_3km'], 'p90')}"),
         row('Interval between new positions, approach p50 / p90 / p99 (s)', lambda d: f"{g(d['update_interval_app'], 'p50')} / {g(d['update_interval_app'], 'p90')} / {g(d['update_interval_app'], 'p99')}"),
         row('Same, taxiing (gs >= 3 kt) p50 / p90 / p99 (s)', lambda d: f"{g(d['update_interval_ground_moving'], 'p50')} / {g(d['update_interval_ground_moving'], 'p90')} / {g(d['update_interval_ground_moving'], 'p99')}"),
         row('Same, stationary (gs < 1 kt) p50 / p90 / p99 (s)', lambda d: f"{g(d['update_interval_ground_stationary'], 'p50')} / {g(d['update_interval_ground_stationary'], 'p90')} / {g(d['update_interval_ground_stationary'], 'p99')}"),
         row('Source mix, all', lambda d: ', '.join(f'{k} {v}' for k, v in d['type_mix_all'].items())),
         row('Source mix, on ground within 3 km', lambda d: ', '.join(f'{k} {v}' for k, v in d['type_mix_ground_3km'].items())),
         row('Source mix, approach', lambda d: ', '.join(f'{k} {v}' for k, v in d['type_mix_app'].items())),
         row('Ground reports with true_heading / track / either (stationary)', lambda d: f"{g(d['ground_stationary_field_presence'], 'true_heading')} / {g(d['ground_stationary_field_presence'], 'track')} / {g(d['ground_stationary_field_presence'], 'track|true_heading')}"),
         row('Same (taxiing)', lambda d: f"{g(d['ground_moving_field_presence'], 'true_heading')} / {g(d['ground_moving_field_presence'], 'track')} / {g(d['ground_moving_field_presence'], 'track|true_heading')}"),
         row('Ground aircraft that sent a heading or track at least once', lambda d: f"{d['ground_aircraft_with_heading_at_least_once'][0]} of {d['ground_aircraft_with_heading_at_least_once'][1]}"),
         row('Ground true_heading on the 360/128 deg grid', lambda d: f"{d['ground_true_heading_quantisation'].get('7bit', 0)} of {sum(d['ground_true_heading_quantisation'].values())}"),
         row('Ground reports with callsign / registration / type', lambda d: f"{g(d['ground_field_presence'], 'flight')} / {g(d['ground_field_presence'], 'r')} / {g(d['ground_field_presence'], 't')}"),
         row('All reports with r / t / desc / ownOp', lambda d: f"{g(d['db_field_presence'], 'r')} / {g(d['db_field_presence'], 't')} / {g(d['db_field_presence'], 'desc')} / {g(d['db_field_presence'], 'ownOp')}"),
         row('Approach reports with alt_geom / nav_qnh / baro_rate / geom_rate', lambda d: f"{g(d['app_field_presence'], 'alt_geom')} / {g(d['app_field_presence'], 'nav_qnh')} / {g(d['app_field_presence'], 'baro_rate')} / {g(d['app_field_presence'], 'geom_rate')}"),
         row('Stationary runs >= 60 s: p95 position spread p50 / p90 / max (m)', lambda d: f"{g(d['stationary_run_position_p95_spread_m'], 'p50')} / {g(d['stationary_run_position_p95_spread_m'], 'p90')} / {g(d['stationary_run_position_p95_spread_m'], 'p100')} (runs {g(d['stationary_run_position_p95_spread_m'], 'runs_ge_60s')})"),
         '', '| Cross-provider (request starts within 0.6 s) | Value |', '|---|---|',
         f"| Matched snapshot pairs | {X['matched_snapshot_pairs']} |",
         f"| Aircraft in both / only adsb.fi / only adsb.lol | {X['hex_in_both']} / {X['hex_only'].get('adsbfi', 0)} / {X['hex_only'].get('adsblol', 0)} |",
         f"| On ground within 3 km: both / only adsb.fi / only adsb.lol | {X['ground_3km_in_both']} / {X['ground_3km_only'].get('adsbfi', 0)} / {X['ground_3km_only'].get('adsblol', 0)} |",
         f"| Fresher position: adsb.lol / same report / adsb.fi | {X['fresher_position'].get('adsblol', 0)} / {X['fresher_position'].get('same', 0)} / {X['fresher_position'].get('adsbfi', 0)} |",
         f"| Position time adsb.fi minus adsb.lol p5 / p50 / p95 (s) | {g(X['pos_time_fi_minus_lol_s'], 'p5')} / {g(X['pos_time_fi_minus_lol_s'], 'p50')} / {g(X['pos_time_fi_minus_lol_s'], 'p95')} |",
         f"| Identical report (same position time): distance p50 / p99 (m); alt_baro equal | {g(X['same_report_distance_m'], 'p50')} / {g(X['same_report_distance_m'], 'p99')}; {X['alt_baro_equal_fraction_same_report']} |",
         f"| Different reports, airborne, after dead-reckoning: p50 / p90 / p99 (m) | {g(X['airborne_distance_after_extrapolation_m'], 'p50')} / {g(X['airborne_distance_after_extrapolation_m'], 'p90')} / {g(X['airborne_distance_after_extrapolation_m'], 'p99')} |",
         f"| Different reports, stationary on ground: p50 / p90 / p99 (m) | {g(X['ground_stationary_distance_different_report_m'], 'p50')} / {g(X['ground_stationary_distance_different_report_m'], 'p90')} / {g(X['ground_stationary_distance_different_report_m'], 'p99')} |",
         f"| Different reports, taxiing, after dead-reckoning: p50 / p90 / p99 (m) | {g(X['ground_moving_distance_after_extrapolation_m'], 'p50')} / {g(X['ground_moving_distance_after_extrapolation_m'], 'p90')} / {g(X['ground_moving_distance_after_extrapolation_m'], 'p99')} |",
         f"| Ground aircraft only in adsb.fi: age p50 / p90 (s) | {g(X['ground_3km_only_adsbfi_age_s'], 'p50')} / {g(X['ground_3km_only_adsbfi_age_s'], 'p90')} |",
         f"| Approach position age vs newest `now`: merged / adsb.fi / adsb.lol, p50 (p90) (s) | {g(X['position_age_app']['merged_freshest'], 'p50')} ({g(X['position_age_app']['merged_freshest'], 'p90')}) / {g(X['position_age_app']['adsbfi'], 'p50')} ({g(X['position_age_app']['adsbfi'], 'p90')}) / {g(X['position_age_app']['adsblol'], 'p50')} ({g(X['position_age_app']['adsblol'], 'p90')}) |",
         f"| Ground (3 km) position age: merged / adsb.fi / adsb.lol, p50 (p90) (s) | {g(X['position_age_ground_3km']['merged_freshest'], 'p50')} ({g(X['position_age_ground_3km']['merged_freshest'], 'p90')}) / {g(X['position_age_ground_3km']['adsbfi'], 'p50')} ({g(X['position_age_ground_3km']['adsbfi'], 'p90')}) / {g(X['position_age_ground_3km']['adsblol'], 'p50')} ({g(X['position_age_ground_3km']['adsblol'], 'p90')}) |",
         f"| Merged stream: interval between new positions, approach / taxiing p50 (p90) (s) | {g(X['merged_update_interval_app'], 'p50')} ({g(X['merged_update_interval_app'], 'p90')}) / {g(X['merged_update_interval_ground_moving'], 'p50')} ({g(X['merged_update_interval_ground_moving'], 'p90')}) |",
         ]
    A = out['altitude']; E = out['events']
    L += ['', '| Altitude / QNH / events | Value |', '|---|---|',
          f"| alt_geom minus QNH-corrected alt_baro, alt_baro < 1000 ft within 20 NM, p10 / p50 / p90 (ft) | {g(A['alt_geom_minus_qnh_alt_below1000ft_ft'], 'p10')} / {g(A['alt_geom_minus_qnh_alt_below1000ft_ft'], 'p50')} / {g(A['alt_geom_minus_qnh_alt_below1000ft_ft'], 'p90')} (n {g(A['alt_geom_minus_qnh_alt_below1000ft_ft'], 'n')}); an ellipsoidal (HAE) alt_geom would give {A['expected_if_alt_geom_is_HAE_ft']}, an MSL one 0 |",
          f"| Same difference by alt_baro band, p50 (n) (ft) | {'; '.join(f'{b}+: {g(v, chr(112) + chr(53) + chr(48))} ({g(v, chr(110))})' for b, v in A['alt_geom_minus_qnh_alt_by_band_ft'].items())} |",
          f"| Per-aircraft median below 1000 ft (hex, type, ADS-B version, ft, n) | {'; '.join(f'{h} {t} v{v}: {m:+d} ({n})' for h, t, v, m, n in A['per_aircraft_median_ft'])} |",
          f"| nav_qnh below 10000 ft within 30 NM, p50 (hPa); minus METAR altimeter p5 / p50 / p95 | {g(A['nav_qnh_below_10000ft_hPa'], 'p50')}; {g(A['nav_qnh_minus_metar_hPa'], 'p5')} / {g(A['nav_qnh_minus_metar_hPa'], 'p50')} / {g(A['nav_qnh_minus_metar_hPa'], 'p95')} (n {g(A['nav_qnh_minus_metar_hPa'], 'n')}) |",
          f"| nav_qnh above FL200, p10 / p50 / p90 (hPa) | {g(A['nav_qnh_above_FL200_hPa'], 'p10')} / {g(A['nav_qnh_above_FL200_hPa'], 'p50')} / {g(A['nav_qnh_above_FL200_hPa'], 'p90')} |",
          f"| METARs used | {'; '.join(f'{a} {b} hPa' for a, b, c in A['metars'])} |",
          f"| Arrivals detected (air-to-ground in merged stream) / by runway / ambiguous | {E['arrivals']} / {E['arrival_runways']} / {E['arrivals_ambiguous']} |",
          f"| Arrival runway fit: median cross-track p50 / max (m); runner-up runway p0 / p50 (m) | {g(E['arrival_rwy_score_m'], 'p50')} / {g(E['arrival_rwy_score_m'], 'p100')}; {g(E['arrival_second_best_m'], 'p0')} / {g(E['arrival_second_best_m'], 'p50')} |",
          f"| Arrival: last airborne alt_baro p50 (ft); alt_geom as MSL (alt_geom + 105.9) p10 / p50 / p90 (ft; runway ends 5.5-13 ft); last-air to first-ground gap p50 / max (s) | {g(E['arrival_last_airborne_alt_baro_ft'], 'p50')}; {g(E['arrival_last_airborne_alt_geom_as_msl_ft'], 'p10')} / {g(E['arrival_last_airborne_alt_geom_as_msl_ft'], 'p50')} / {g(E['arrival_last_airborne_alt_geom_as_msl_ft'], 'p90')}; {g(E['arrival_air_to_ground_gap_s'], 'p50')} / {g(E['arrival_air_to_ground_gap_s'], 'p100')} |",
          f"| Arrival: first ground report past the landing threshold p10 / p50 / p90 (m) | {g(E['arrival_first_ground_report_past_threshold_m'], 'p10')} / {g(E['arrival_first_ground_report_past_threshold_m'], 'p50')} / {g(E['arrival_first_ground_report_past_threshold_m'], 'p90')} |",
          f"| Departures detected / by runway / ambiguous; runway fit p50 (m); ground-to-air gap p50 / max (s) | {E['departures']} / {E['departure_runways']} / {E['departures_ambiguous']}; {g(E['departure_rwy_score_m'], 'p50')}; {g(E['departure_ground_to_air_gap_s'], 'p50')} / {g(E['departure_ground_to_air_gap_s'], 'p100')} |",
          f"| Go-around candidates | {len(E['go_around_candidates'])} |",
          f"| Air/ground flag flapping on the ground (airborne spell with gs < 60 kt; excluded from the counts above): events / aircraft | {E['air_ground_flag_flaps_below_60kt']} / {', '.join(E['air_ground_flap_aircraft']) or '-'} |",
          f"| Reports 'airborne' within 5 km with alt_baro < 150 ft and gs < 40 kt: adsb.fi / adsb.lol | {fi['airborne_but_low_slow_near_arp']} / {lol['airborne_but_low_slow_near_arp']} |",
          f"| Vanished while on ground within 3 km (last gs < 1 kt) / appeared on ground (stationary) | {E['vanished_on_ground_3km']} ({E['vanished_last_gs_lt1']}) / {E['appeared_on_ground_3km']} ({E['appeared_stationary']}) |",
          ]
    L += ['', '| Ground vehicle (hex) | Callsign | Reg (db) | Category | Type (db) | Operator (db) | Source type | Max gs (kt) |', '|---|---|---|---|---|---|---|---|']
    for v in out['vehicles']:
        L.append(f"| {v['hex']} | {', '.join(v['flight'])} | {v['r']} | {v['category']} | {v['t'] or ''} | {v['ownOp'] or ''} | {', '.join(v['types'])} | {v['max_gs']} |")
    L += ['', '| OpenSky probe (UTC) | `time` age at response (s) | States (on ground) | time_position age p50 / max (s) | adsb.fi / adsb.lol in same bbox | Ground within 3 km: OpenSky vs adsb.fi | Position diff vs adsb.fi p50 / max (m) |', '|---|---|---|---|---|---|---|']
    for o in out['opensky']:
        f_ = o.get('adsbfi', {}); l_ = o.get('adsblol', {})
        L.append(f"| {o['request_utc'][11:19]} | {o['time_field_age_at_response_s']} | {o['n_states']} ({o['on_ground']}) | {g(o['time_position_age_s'], 'p50')} / {g(o['time_position_age_s'], 'p100')} | "
                 f"{f_.get('n_in_bbox', '-')} / {l_.get('n_in_bbox', '-')} | {f_.get('ground_3km_opensky', '-')} vs {f_.get('ground_3km_provider', '-')} | "
                 f"{g(f_.get('position_distance_at_opensky_time_m'), 'p50')} / {g(f_.get('position_distance_at_opensky_time_m'), 'p100')} |")
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--from', dest='t0'); ap.add_argument('--to', dest='t1'); ap.add_argument('--hours', type=float)
    ap.add_argument('--no-net', action='store_true', help='do not fetch METARs')
    ap.add_argument('--opensky-probe', type=int, default=0, help='make N anonymous OpenSky bbox requests first (1 credit each)')
    ap.add_argument('--json', default=os.path.join(CACHE, 'analysis.json'))
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--markdown', action='store_true', help='print the key tables as Markdown instead of the full text report')
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    if a.opensky_probe: opensky_probe(a.opensky_probe)
    iso = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp() if s else None
    t0, t1 = iso(a.t0), iso(a.t1)
    if a.hours and not t0: t0 = (t1 or time.time()) - a.hours * 3600
    out = analyse(t0, t1, net=not a.no_net)
    json.dump(out, open(a.json, 'w'), indent=1, default=list)
    if a.markdown: print(markdown(out))
    elif not a.quiet: print(fmt(out))
    print(f"\nwrote {os.path.relpath(a.json, ROOT)}")


if __name__ == '__main__':
    main()
