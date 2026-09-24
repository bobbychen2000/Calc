"""Shared helpers for the traffic audit (tools/live/replay_*.py, docs/research/traffic_audit.md).

Everything here mirrors the app so that numbers measured in Python are in the app's own frame:
  * world frame = js/geo.js: x = east, z = south (m), origin = ARP 37.6188056 N 122.3754167 W,
    110990 m/deg lat, 111320*cos(lat0) m/deg lon (same equirectangular approximation as llToWorld);
  * runway ends = js/geo.js RWY_ENDS (FAA/AirNav degrees-minutes, displaced thresholds in ft), parsed from the file
    so this module never drifts from the app;
  * stands = data/sfo_stands.json (surveyed layout, src obs/inf), aircraft sizes = js/aircraft/types.js via node
    (same dump as tools/live/gatecheck.py).
Recordings (tools/live/record.py): one gzip JSON line per request {t: request start (s), p, d: response | err}.
  adsb.fi v2 lat/lon/dist: aircraft under 'aircraft', 'now' in s;  adsb.lol /v2/point: under 'ac', 'now' in ms.
  Position time of a report = now - seen_pos (readsb README-json.md: "seen_pos: how long ago (in seconds before
  "now") the position was last updated").
"""
import glob, gzip, json, math, os, pickle, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
REC = os.path.join(ROOT, 'refs', 'cache', 'rec')
OUT = os.path.join(ROOT, 'refs', 'cache', 'replay')      # derived from the providers' data -> gitignored
sys.path.insert(0, HERE)
from recio import lines  # noqa: E402

FT, KT, NM = 0.3048, 0.514444, 1852.0
ARP_LAT, ARP_LON = 37.6188056, -122.3754167
M_LAT = 110990.0
M_LON = 111320.0 * math.cos(math.radians(ARP_LAT))
GROUND_Y = 3.0
GEOID_N_M = -32.29     # EGM96 undulation at the ARP (docs/research/realtime_feeds.md 4.6, PROJ us_nga_egm96_15.tif)


def ll2w(lat, lon):
    """js/geo.js llToWorld -> (x east, z south) metres."""
    return ((np.asarray(lon) - ARP_LON) * M_LON, -(np.asarray(lat) - ARP_LAT) * M_LAT)


def hdg_vec(h):
    """traffic.js hdgVec: world (x,z) unit vector of a true heading in radians."""
    return np.sin(h), -np.cos(h)


def vec_hdg(x, z):
    return np.arctan2(x, -z)


def wrap_pi(a):
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi


def wrap180(a):
    return (np.asarray(a) + 180.0) % 360.0 - 180.0


# ------------------------------------------------------------------------------------------------ runways
def _rwy_ends():
    src = open(os.path.join(ROOT, 'js', 'geo.js')).read()
    ends = {}
    for m in re.finditer(r"'(\d+[LR])': \{ lat: dms\((\d+), ([\d.]+)\), lon: -dms\((\d+), ([\d.]+)\), elev: ([\d.]+), disp: (\d+) \}", src):
        n, a, b, c, d, e, f = m.groups()
        ends[n] = dict(lat=int(a) + float(b) / 60, lon=-(int(c) + float(d) / 60), elev=float(e), disp=float(f))
    assert len(ends) == 8, ends
    return ends


RWY_ENDS = _rwy_ends()
PAIRS = [('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')]
RUNWAY_WIDTH = 200 * FT


def _runways():
    R = {}
    for a, b in PAIRS:
        pa = ll2w(RWY_ENDS[a]['lat'], RWY_ENDS[a]['lon']); pb = ll2w(RWY_ENDS[b]['lat'], RWY_ENDS[b]['lon'])
        pa = np.array(pa, float); pb = np.array(pb, float)
        L = float(np.hypot(*(pb - pa)))
        for n, s, e in ((a, pa, pb), (b, pb, pa)):
            d = (e - s) / L
            disp = RWY_ENDS[n]['disp'] * FT
            R[n] = dict(name=n, pair=f'{a}/{b}', start=s, end=e, dir=d, len=L, disp=disp, thr=s + d * disp,
                        hdg=float(vec_hdg(d[0], d[1])), hdg_deg=float(np.degrees(vec_hdg(d[0], d[1])) % 360),
                        elev_ft=RWY_ENDS[n]['elev'])
    return R


RWY = _runways()


def rwy_coords(name, x, z):
    """along-track distance from the landing threshold (m, + = past it) and cross-track (m, + = right of centreline)."""
    R = RWY[name]
    dx, dz = np.asarray(x) - R['thr'][0], np.asarray(z) - R['thr'][1]
    a = dx * R['dir'][0] + dz * R['dir'][1]
    c = -dx * R['dir'][1] + dz * R['dir'][0]
    return a, c


def on_runway(x, z, margin_along=40.0, half_width=36.0):
    """runway pair under a point (same test as traffic.js runwayAt: |cross| < 36 m, -40 m .. len+40 m)."""
    for a, b in PAIRS:
        R = RWY[a]
        dx, dz = x - R['start'][0], z - R['start'][1]
        al = dx * R['dir'][0] + dz * R['dir'][1]; c = -dx * R['dir'][1] + dz * R['dir'][0]
        if -margin_along < al < R['len'] + margin_along and abs(c) < half_width:
            return f'{a}/{b}'
    return None


# ------------------------------------------------------------------------------------------------ static data
def load_json(rel):
    return json.load(open(os.path.join(ROOT, rel)))


CLASS_MAX = {'B': (28.5, 37), 'C': (36.5, 45), 'CL': (38.5, 48), 'D': (52, 62), 'E': (61, 68), 'EL': (65.5, 77), 'F': (80, 80)}  # js/live/airport.js


def load_stands():
    S = load_json('data/sfo_stands.json')
    out = []
    for s in S['stands']:
        h = math.radians(s['hdg']); f = (math.sin(h), -math.cos(h))
        span, L = CLASS_MAX.get(s['cls'], CLASS_MAX['C'])
        out.append(dict(name=s['name'], alias=s.get('alias', []), cls=s['cls'], src=s['src'], x=s['nose'][0], z=s['nose'][1],
                        hdg=h, dx=f[0], dz=f[1], maxSpan=span, maxLen=L, bridge=bool(s['bridges']), remote=False))
    for r in S.get('remote', []):
        out.append(dict(name=r['name'], alias=[], cls='E', src='inf', x=r['x'], z=r['z'], hdg=None, dx=0, dz=0, maxSpan=65.5, maxLen=77, bridge=False, remote=True))
    return out


_TYPES_JS = r"""
import { TYPES } from '%s/js/aircraft/types.js';
import { typeForIcao } from '%s/js/live/aircraft.js';
const out = {};
for (const k of process.argv.slice(1)) { const m = typeForIcao(k); const T = m && TYPES[m.t]; if (T) out[k] = { t: m.t, L: T.L, span: T.wing ? T.wing.span : null, xMain: T.xMain, xNose: T.xNose ?? null, track: T.track ?? null }; }
console.log(JSON.stringify(out));
"""


def app_types(icaos):
    """ICAO type designator -> app model sizes (typeForIcao -> TYPES), via node."""
    icaos = sorted(set(i for i in icaos if i))
    try:
        r = subprocess.run(['node', '--input-type=module', '-e', _TYPES_JS % (ROOT, ROOT), '--'] + icaos, capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout)
    except Exception as e:  # pragma: no cover
        print('warning: node type dump failed:', e, file=sys.stderr)
        return {}


def taxiway_polys():
    """[(name, rings, bbox)] of SFO Museum taxiway polygons (data/sfo_airport.json, world x,z)."""
    A = load_json('data/sfo_airport.json')
    out = []
    for t in A['taxiways']:
        for poly in t['polys']:
            r0 = np.array(poly[0]); out.append((t['name'].replace('Taxiway ', ''), [np.array(r) for r in poly], (r0[:, 0].min(), r0[:, 1].min(), r0[:, 0].max(), r0[:, 1].max())))
    return out


def in_ring(r, x, z):
    c = False; n = len(r); j = n - 1
    for i in range(n):
        a, b = r[i], r[j]
        if (a[1] > z) != (b[1] > z) and x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]:
            c = not c
        j = i
    return c


def poly_names_at(P, x, z):
    out = []
    for name, rings, bb in P:
        if x < bb[0] or x > bb[2] or z < bb[1] or z > bb[3]:
            continue
        if in_ring(rings[0], x, z) and not any(in_ring(h, x, z) for h in rings[1:]):
            out.append(name)
    return out


# ------------------------------------------------------------------------------------------------ recordings
FIELDS = ('lat', 'lon', 'alt_baro', 'alt_geom', 'gs', 'track', 'true_heading', 'mag_heading', 'baro_rate', 'geom_rate', 'nav_qnh',
          'type', 'category', 'flight', 'r', 't', 'desc', 'ownOp', 'squawk', 'nic', 'nac_p', 'rc', 'seen', 'seen_pos', 'messages', 'rssi',
          'mlat', 'tisb', 'calc_track', 'track_rate', 'roll', 'dbFlags')


def _window():
    """optional analysis window from the environment: REPLAY_FROM / REPLAY_UNTIL = ISO UTC time or epoch seconds
    (so that every script of a run sees the same recording while the recorder keeps writing)"""
    import datetime as dt
    def parse(v):
        if not v: return None
        try: return float(v)
        except ValueError: return dt.datetime.fromisoformat(v.replace('Z', '+00:00')).timestamp()
    return parse(os.environ.get('REPLAY_FROM')), parse(os.environ.get('REPLAY_UNTIL'))


def snapshots(provider, t0=None, t1=None):
    """yield (request_t, now_s, [aircraft]) for one provider, in file order (within REPLAY_FROM/REPLAY_UNTIL if set)."""
    w0, w1 = _window()
    t0 = max(t0, w0) if t0 and w0 else (t0 or w0); t1 = min(t1, w1) if t1 and w1 else (t1 or w1)
    for p in sorted(glob.glob(os.path.join(REC, f'{provider}_*.jsonl.gz'))):
        for r in lines(p):
            if 'd' not in r:
                continue
            if t0 and r['t'] < t0: continue
            if t1 and r['t'] > t1: continue
            d = r['d']; now = d.get('now')
            if now is None: continue
            now = now / 1000.0 if now > 1e11 else float(now)
            yield r['t'], now, d.get('aircraft', d.get('ac', []))


def request_log(provider):
    """[(t, ok)] for every request (ok False on err)."""
    out = []; w0, w1 = _window()
    for p in sorted(glob.glob(os.path.join(REC, f'{provider}_*.jsonl.gz'))):
        for r in lines(p):
            if (w0 and r['t'] < w0) or (w1 and r['t'] > w1): continue
            out.append((r['t'], 'd' in r, r.get('err')))
    return out


def build_reports(force=False):
    """Merged, de-duplicated position reports per ICAO hex from both providers.
    Returns {hex: list of dict(pt=position time s, prov, req=request time, now, **fields)} sorted by pt.
    A report present in both providers (same position time within 0.05 s) is kept once (first seen), with 'both'=True.
    Cached in refs/cache/replay/reports.pkl keyed on the recording files' sizes."""
    os.makedirs(OUT, exist_ok=True)
    w = _window()
    key = (w,) + tuple((os.path.basename(p), os.path.getsize(p)) for p in sorted(glob.glob(os.path.join(REC, '*.jsonl.gz')))) if not w[1] else \
          (w,) + tuple(sorted(os.path.basename(p) for p in glob.glob(os.path.join(REC, '*.jsonl.gz'))))
    cp = os.path.join(OUT, 'reports.pkl')
    if not force and os.path.exists(cp):
        c = pickle.load(open(cp, 'rb'))
        if c['key'] == key:
            return c['tracks'], c['meta']
    raw = {}
    meta = {'providers': {}}
    for prov in ('adsbfi', 'adsblol'):
        n = 0; tmin = tmax = None
        for req, now, acs in snapshots(prov):
            n += 1; tmin = req if tmin is None else tmin; tmax = req
            for a in acs:
                if a.get('lat') is None or a.get('lon') is None:
                    continue
                hx = str(a.get('hex', '')).lower()
                sp = a.get('seen_pos')
                if sp is None: continue
                pt = now - float(sp)
                rec = {k: a.get(k) for k in FIELDS if k in a}
                rec.update(pt=pt, prov=prov, req=req, now=now)
                raw.setdefault(hx, []).append(rec)
        meta['providers'][prov] = dict(snapshots=n, t0=tmin, t1=tmax)
    tracks = {}
    for hx, L in raw.items():
        L.sort(key=lambda r: (r['pt'], r['now']))
        out = []
        for r in L:
            if out and abs(r['pt'] - out[-1]['pt']) <= 0.05:
                o = out[-1]
                if r['prov'] != o['prov']:
                    o['both'] = True
                # keep the first report but fill fields it lacks (e.g. desc/ownOp only from adsb.fi)
                for k, v in r.items():
                    if k not in o or o[k] is None:
                        o[k] = v
                continue
            out.append(r)
        for r in out:
            x, z = ll2w(r['lat'], r['lon']); r['x'] = float(x); r['z'] = float(z)
            r['ground'] = r.get('alt_baro') == 'ground'
        tracks[hx] = out
    pickle.dump({'key': key, 'tracks': tracks, 'meta': meta}, open(cp, 'wb'), protocol=4)
    return tracks, meta


def is_vehicle(r):
    cat = r.get('category') or ''
    return cat[:1] == 'C' or r.get('t') in ('SERV', 'GRND', 'TWR') or r.get('type') == 'adsb_icao_nt'


def ident(track):
    """most common callsign / reg / type of a report list."""
    from collections import Counter
    def mc(k):
        c = Counter((r.get(k) or '').strip() for r in track if r.get(k)); return c.most_common(1)[0][0] if c else None
    return dict(flight=mc('flight'), reg=mc('r'), icao=mc('t'), desc=mc('desc'), cat=mc('category'), src=mc('type'), op=mc('ownOp'))


def utc(t):
    import datetime as dt
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%H:%M:%S')
