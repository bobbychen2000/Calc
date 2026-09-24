#!/usr/bin/env python3
"""Cross-check the app's stand/gate label for parked aircraft against SFO's own published gate and stand allocation.

Ground truth used (details, URLs and terms: docs/research/gate_truth.md):
  * flysfo.com flight status JSON  https://www.flysfo.com/flysfo/api/flight-status  -- the endpoint the official
    flight-status page (https://www.flysfo.com/flight-info/flight-status) loads in the browser. Per flight: ICAO-style
    callsign (marketing carrier + number), gate, and the AODB stand allocation list `stands[]` with start/end times
    (a towed aircraft has several). A snapshot spans about 4 h back to 12 h ahead (observed 24 Sep 2026), so one fetch
    validates every parked sample of the preceding ~4 h of recording; fetch at least every 4 h to cover a whole day.
  * DataSF "SFO Gate and Stand Assignment Information" (chfu-j7tc, PDDL) for the official list of gate numbers.

Our side (reimplemented exactly from the app, nothing imported from js/ at run time except the aircraft size table):
  * js/geo.js llToEN (ARP 37.6188056 N, -122.3754167 E; 110990 m/deg lat; 111320*cos(lat) m/deg lon); world x = E, z = -N
  * js/live/traffic.js gateScore/matchGate/standFits (antenna = nose - 0.2 L along the stand heading; lateral limit
    min(18, 0.35 span_max + 4) m, along limit 20 m, score |lat| + 0.35 |along|; heading gate 35 deg when a true heading
    is reported; remote stands: distance < 40 m, score d + 4); taxiway polygons and runways excluded as in the app.
    Not reproduced: the app's occupancy arbitration and neighbour blocking (they depend on live state) -- this tool
    reports the best and the runner-up stand instead and flags two aircraft picking the same stand.
  * js/live/airport.js CLASS_MAX, js/aircraft/types.js TYPES, js/live/aircraft.js TYPE_MODELS/BIZ_LEN (dumped with node).
  * --js runs the app's own Traffic.matchGate in node on the same reports and reports any difference (none on 24 Sep).

Usage (from the repo root):
  python3 tools/live/gatecheck.py fetch                 # one flysfo snapshot (gzip ~0.5 MB) -> refs/cache/gate_truth/
  python3 tools/live/gatecheck.py check [--at 2026-09-24T07:31:00Z | --every 60 [--since ...]] [--still 120] [--js]
                                        [--json out.json] [--md out.md]
  python3 tools/live/gatecheck.py gates [--json out.json]   # official gate/stand names (maps, DataSF, AODB) vs ours,
                                                           # plus merged stands that SFO allocates simultaneously
Be polite to flysfo.com (no published terms; see the doc): `fetch` refuses to run more often than every 10 minutes (the
official page downloads the same ~10 MB feed twice per page view); there is no need to poll it.
Verdicts: agree / alias (SFO's stand = our stand or one of its aliases), DISAGREE, no-match (SFO has a stand, our matcher
none), class-rejected (geometry fits but the app's size class refuses the type), off-stand (pushed back / taxiing /
waiting), agree (gate) (no stand window, published gate = our stand), occupancy-type-match (no callsign: SFO has a
flight of the same type allocated to our stand).
"""
import argparse, bisect, datetime as dt, glob, gzip, json, math, os, re, subprocess, sys, time, urllib.request, zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'refs', 'cache', 'gate_truth')
REC = os.path.join(ROOT, 'refs', 'cache', 'rec')
FLYSFO_URL = 'https://www.flysfo.com/flysfo/api/flight-status'
DATASF_URL = 'https://data.sf.gov/resource/chfu-j7tc.json'
UA = 'sfo-live-3d gatecheck/0.1 (personal non-commercial visualisation; occasional manual check)'
MIN_FETCH_INTERVAL = 600  # s

# ------------------------------------------------------------------ js/geo.js (exact)
ARP_LAT, ARP_LON = 37.6188056, -122.3754167
M_PER_DEG_LAT = 110990.0
M_PER_DEG_LON = 111320.0 * math.cos(ARP_LAT * math.pi / 180)
def ll_to_en(lat, lon): return ((lon - ARP_LON) * M_PER_DEG_LON, (lat - ARP_LAT) * M_PER_DEG_LAT)
def ll_to_world(lat, lon): e, n = ll_to_en(lat, lon); return e, -n          # llToWorld -> [e, h, -n]
dms = lambda d, m: d + m / 60
RWY_ENDS = {  # js/geo.js RWY_ENDS (FAA / AirNav), only what runwayAt needs
    '10L': (dms(37, 37.724323), -dms(122, 23.603512)), '28R': (dms(37, 36.812017), -dms(122, 21.428467)),
    '10R': (dms(37, 37.577467), -dms(122, 23.586327)), '28L': (dms(37, 36.702717), -dms(122, 21.500950)),
    '1L': (dms(37, 36.473872), -dms(122, 22.975710)), '19R': (dms(37, 37.588882), -dms(122, 22.236565)),
    '1R': (dms(37, 36.379793), -dms(122, 22.862445)), '19L': (dms(37, 37.640532), -dms(122, 22.026650)),
}
RWYS = []
for a, b in (('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')):
    for p, q in ((a, b), (b, a)):
        fe, fn = ll_to_en(*RWY_ENDS[p]); te, tn = ll_to_en(*RWY_ENDS[q]); L = math.hypot(te - fe, tn - fn)
        RWYS.append(((fe, -fn), ((te - fe) / L, -(tn - fn) / L), L))
def runway_at(x, z):  # traffic.js runwayAt
    for (sx, sz), (dx, dz), L in RWYS:
        rx, rz = x - sx, z - sz; a = rx * dx + rz * dz; c = -rx * dz + rz * dx
        if -40 < a < L + 40 and abs(c) < 36: return True
    return False

# ------------------------------------------------------------------ js/live/traffic.js + airport.js (exact)
ANT = 0.2
CLASS_MAX = {'B': (28.5, 37), 'C': (36.5, 45), 'CL': (38.5, 48), 'D': (52, 62), 'E': (61, 68), 'EL': (65.5, 77), 'F': (80, 80)}
DEG = math.pi / 180
def wrap_pi(a):
    a = (a + math.pi) % (2 * math.pi)
    return a - math.pi

def load_stands():
    d = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    gates = []
    for s in d['stands']:
        h = s['hdg'] * DEG; span, ln = CLASS_MAX.get(s['cls'], CLASS_MAX['C'])
        gates.append(dict(name=s['name'], alias=s.get('alias') or [], cls=s['cls'], src=s['src'], x=s['nose'][0], z=s['nose'][1],
                          dx=math.sin(h), dz=-math.cos(h), hdg=h, maxSpan=span, maxLen=ln, wide=span > 40, bridge=bool(s['bridges']),
                          remote=False, bridges=[b['gate'] for b in s['bridges']]))
    for r in d.get('remote') or []:
        gates.append(dict(name=r['name'], alias=[], cls='E', src='?', x=r['x'], z=r['z'], dx=0, dz=0, hdg=None, maxSpan=65.5, maxLen=77,
                          wide=True, bridge=False, remote=True, bridges=[]))
    return gates

def load_taxiways():
    P = []
    for t in json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json'))).get('taxiways') or []:
        for poly in t['polys']:
            xs = [p[0] for p in poly[0]]; zs = [p[1] for p in poly[0]]
            P.append((poly, (min(xs), min(zs), max(xs), max(zs))))
    return P
def in_ring(r, x, z):
    c = False; j = len(r) - 1
    for i in range(len(r)):
        a, b = r[i], r[j]
        if (a[1] > z) != (b[1] > z) and x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]: c = not c
        j = i
    return c
def in_polys(P, x, z):
    for rings, bb in P:
        if x < bb[0] or x > bb[2] or z < bb[1] or z > bb[3]: continue
        if in_ring(rings[0], x, z) and not any(in_ring(h, x, z) for h in rings[1:]): return True
    return False

_TYPES_JS = r"""
import { TYPES } from '%s/js/aircraft/types.js';
import fs from 'fs';
const src = fs.readFileSync('%s/js/live/aircraft.js', 'utf8');
const TM = eval('(' + src.match(/export const TYPE_MODELS = (\{[\s\S]*?\n\});/)[1] + ')');
const BZ = eval('(' + src.match(/const BIZ_LEN = (\{[\s\S]*?\});/)[1] + ')');
const out = {};
for (const [k, v] of Object.entries(TM)) { const T = TYPES[v.t]; if (T) out[k] = { t: v.t, L: T.L, span: T.wing ? T.wing.span : null }; }
const C = TYPES.crj2;
for (const [k, L] of Object.entries(BZ)) if (!out[k]) out[k] = { t: 'biz_' + k, L, span: C.wing.span * L / C.L };
console.log(JSON.stringify(out));
"""
def load_types():
    """ICAO type -> {L, span} exactly as the app sizes it (TYPE_MODELS -> TYPES, business jets scaled from crj2)."""
    p = os.path.join(CACHE, 'app_types.json')
    srcs = [os.path.join(ROOT, 'js', 'aircraft', 'types.js'), os.path.join(ROOT, 'js', 'live', 'aircraft.js')]
    if os.path.exists(p) and os.path.getmtime(p) > max(os.path.getmtime(s) for s in srcs): return json.load(open(p))
    try:
        out = subprocess.run(['node', '--input-type=module', '-e', _TYPES_JS % (ROOT, ROOT)], capture_output=True, text=True, timeout=60)
        d = json.loads(out.stdout); os.makedirs(CACHE, exist_ok=True); json.dump(d, open(p, 'w')); return d
    except Exception as e:
        print('warning: could not dump the app type table with node (%s); using default lengths' % e, file=sys.stderr); return {}

def stand_fits(g, T):  # traffic.js standFits
    if not T or g['remote'] or not g['maxSpan']: return True
    span = T['span'] if T.get('span') else 36
    if span <= g['maxSpan'] + 0.6 and T['L'] <= g['maxLen'] + 2: return True
    return g['maxSpan'] >= 64 and span <= 80

def gate_score(g, x, z, T):  # traffic.js gateScore -> (score, lat, along) or None
    if g['bridge']:
        L = T['L'] if T else (63 if g['wide'] else 38)
        ex, ez = g['x'] - g['dx'] * ANT * L, g['z'] - g['dz'] * ANT * L
        rx, rz = x - ex, z - ez
        along = -(rx * g['dx'] + rz * g['dz']); lat = -rx * g['dz'] + rz * g['dx']
        lat_max = min(18, 0.35 * g['maxSpan'] + 4)
        if abs(lat) > lat_max or abs(along) > 20: return None
        return abs(lat) + 0.35 * abs(along), lat, along
    d = math.hypot(x - g['x'], z - g['z'])
    return (d + 4, d, 0.0) if d < 40 else None

def match_stands(gates, taxi, x, z, T, hd_true, fits=True):
    """All candidate stands sorted by score, as traffic.js matchGate ranks them (without occupancy/blocking).
    fits=False skips the size-class test (diagnostics: would the position match if the class allowed the type?)."""
    if in_polys(taxi, x, z): return 'taxiway', []
    if runway_at(x, z): return 'runway', []
    c = []
    for g in gates:
        if fits and not stand_fits(g, T): continue
        if g['bridge'] and hd_true is not None and abs(wrap_pi(hd_true * DEG - g['hdg'])) > 35 * DEG: continue
        s = gate_score(g, x, z, T)
        if s: c.append((s[0], s[1], s[2], g))
    c.sort(key=lambda q: q[0])
    return None, c

def nearest_stand(gates, x, z, T, hd_true):
    """Diagnostics: the contact stand whose expected antenna point is nearest, with lateral/along error and heading
    difference, ignoring the app's acceptance limits."""
    best = None
    for g in gates:
        if not g['bridge']: continue
        L = T['L'] if T else (63 if g['wide'] else 38)
        ex, ez = g['x'] - g['dx'] * ANT * L, g['z'] - g['dz'] * ANT * L
        rx, rz = x - ex, z - ez; d = math.hypot(rx, rz)
        if best is None or d < best[0]:
            best = (d, g['name'], -rx * g['dz'] + rz * g['dx'], -(rx * g['dx'] + rz * g['dz']),
                    None if hd_true is None else math.degrees(wrap_pi(hd_true * DEG - g['hdg'])))
    return dict(name=best[1], dist=round(best[0], 1), lat=round(best[2], 1), along=round(best[3], 1),
                dhdg=None if best[4] is None else round(best[4], 1))

# ------------------------------------------------------------------ recorder (robust reader)
def _members(path):
    """Decode every gzip member of a recorder file; a truncated/corrupt member (e.g. a killed writer) keeps what decoded."""
    raw = open(path, 'rb').read(); out = []
    for m in re.finditer(b'\x1f\x8b\x08', raw):
        d = zlib.decompressobj(16 + zlib.MAX_WBITS); buf = []
        try:
            for i in range(m.start(), len(raw), 1 << 16):
                buf.append(d.decompress(raw[i:i + (1 << 16)]))
                if d.eof: break
        except zlib.error:
            pass
        out.append(b''.join(buf))
    return out

def read_records(provider, t0=None, t1=None):
    seen = set()
    for p in sorted(glob.glob(os.path.join(REC, f'{provider}_*.jsonl.gz'))):
        h = re.search(r'_(\d{8}_\d{2})\.jsonl', p).group(1)
        hs = dt.datetime.strptime(h, '%Y%m%d_%H').replace(tzinfo=dt.timezone.utc).timestamp()
        if (t1 is not None and hs > t1) or (t0 is not None and hs + 3600 < t0): continue
        for blob in _members(p):
            for line in blob.split(b'\n'):
                if not line.strip(): continue
                try: r = json.loads(line)
                except ValueError: continue
                if 'd' not in r: continue
                if (t0 is not None and r['t'] < t0) or (t1 is not None and r['t'] > t1): continue
                k = (r['p'], r['t'])
                if k in seen: continue   # overlapping members written twice
                seen.add(k); yield r

class Tracks:
    """All reports of both providers near SFO, per aircraft, deduplicated by position time (read once)."""
    def __init__(self, t0=None, t1=None):
        self.h = {}
        for prov in ('adsbfi', 'adsblol'):
            for r in read_records(prov, t0, t1):
                d = r['d']; ac = d.get('aircraft') if 'aircraft' in d else d.get('ac')
                for a in ac or []:
                    if 'lat' not in a or (a.get('seen_pos') or 0) > 30: continue
                    x, z = ll_to_world(a['lat'], a['lon'])
                    if math.hypot(x, z) > 6000: continue
                    tpos = round(r['t'] - (a.get('seen_pos') or 0), 1)
                    self.h.setdefault(a['hex'], {}).setdefault(tpos, dict(a, tpos=tpos, prov=prov, x=x, z=z))
        self.t = {k: sorted(v) for k, v in self.h.items()}
        self.times = sorted(r['t'] for p in ('adsbfi', 'adsblol') for r in read_records(p, t0, t1))
    def last(self, hx, T, window):
        ts = self.t[hx]; i = bisect.bisect_right(ts, T) - 1
        return self.h[hx][ts[i]] if i >= 0 and ts[i] >= T - window else None
    def last_moving(self, hx, T, gs=5):
        """Last time (<= T) the aircraft reported gs >= 5 kt or was airborne."""
        for t in reversed(self.t[hx][:bisect.bisect_right(self.t[hx], T)]):
            a = self.h[hx][t]
            if a.get('alt_baro') != 'ground' or (a.get('gs') or 0) >= gs: return t
        return None
    def last_callsign(self, hx, T, maxage=4 * 3600):
        for t in reversed(self.t[hx][:bisect.bisect_right(self.t[hx], T)]):
            if t < T - maxage: break
            f = (self.h[hx][t].get('flight') or '').strip()
            if f and not f.startswith('.'): return f
        return None
    def still_since(self, hx, T):
        ts = self.t[hx][:bisect.bisect_right(self.t[hx], T)]
        if not ts: return None
        a0 = self.h[hx][ts[-1]]; since = ts[-1]
        for t in reversed(ts):
            a = self.h[hx][t]
            if math.hypot(a['x'] - a0['x'], a['z'] - a0['z']) > 5 or a.get('alt_baro') != 'ground': break
            since = t
        return since

def parked_at(tracks, T, window, stands, still_span=300):
    """Aircraft whose last report in [T-window, T] is on the ground, gs < 1 kt, within 150 m of a surveyed stand.
    Position = median of the reports with gs < 1 kt over the last `still_span` s: parked ADS-B positions scatter by
    tens of metres (observed: AAL2506 at B24, NACp 8-9, 27 m spread), so a single report can pick a neighbour stand."""
    out = []
    for hx in tracks.t:
        a = tracks.last(hx, T, window)
        if not a or a.get('alt_baro') != 'ground': continue
        if a.get('gs') is not None and a['gs'] >= 1: continue
        ts = tracks.t[hx]; i1 = bisect.bisect_right(ts, T); i0 = bisect.bisect_left(ts, T - still_span)
        pts = [tracks.h[hx][t] for t in ts[i0:i1]]
        pts = [p for p in pts if p.get('alt_baro') == 'ground' and (p.get('gs') or 0) < 1]
        if pts:
            xs = sorted(p['x'] for p in pts); zs = sorted(p['z'] for p in pts)
            a = dict(a, x=xs[len(xs) // 2], z=zs[len(zs) // 2], n_pos=len(pts), spread=round(max(xs[-1] - xs[0], zs[-1] - zs[0]), 1))
            hs = [p['true_heading'] for p in pts if p.get('true_heading') is not None]
            if hs: a['true_heading'] = sorted(hs)[len(hs) // 2]
            a['lat'] = ARP_LAT - a['z'] / M_PER_DEG_LAT; a['lon'] = ARP_LON + a['x'] / M_PER_DEG_LON
        if min(math.hypot(a['x'] - g['x'], a['z'] - g['z']) for g in stands) > 150: continue
        out.append(a)
    return out

# ------------------------------------------------------------------ flysfo feed
def iso(s): return dt.datetime.fromisoformat(s).timestamp() if s else None

def fetch(force=False):
    os.makedirs(CACHE, exist_ok=True)
    prev = sorted(glob.glob(os.path.join(CACHE, 'flysfo_api_flight-status_*.json*')))
    if prev and not force and time.time() - os.path.getmtime(prev[-1]) < MIN_FETCH_INTERVAL:
        print('last snapshot is less than %d min old: %s (use --force)' % (MIN_FETCH_INTERVAL // 60, prev[-1])); return prev[-1]
    req = urllib.request.Request(FLYSFO_URL, headers={'User-Agent': UA, 'Accept': 'application/json', 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read(); enc = r.headers.get('Content-Encoding')
    body = gzip.decompress(raw) if enc == 'gzip' else raw
    json.loads(body)  # validate
    p = os.path.join(CACHE, 'flysfo_api_flight-status_%s.json.gz' % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    with gzip.open(p, 'wb') as f: f.write(body)
    print('saved', p, len(raw), 'bytes on the wire,', len(body), 'bytes JSON'); return p

def snapshot_time(path):
    return dt.datetime.strptime(re.search(r'_(\d{8}T\d{6}Z)', path).group(1), '%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).timestamp()

def load_flysfo_all():
    """Union of every cached snapshot, the newest version of each flight winning (a snapshot only reaches ~4 h back)."""
    ps = sorted(glob.glob(os.path.join(CACHE, 'flysfo_api_flight-status_*.json*')), key=snapshot_time)
    if not ps: sys.exit('no flysfo snapshot in %s: run `gatecheck.py fetch` first' % CACHE)
    by = {}
    for p in ps:
        for r in load_flysfo(p)[2]: by[r['flight_id']] = r
    path, lu, _ = load_flysfo(ps[-1])
    return '%d snapshots, newest %s' % (len(ps), os.path.basename(path)), lu, list(by.values())

def load_flysfo(path=None):
    if not path:
        c = sorted(glob.glob(os.path.join(CACHE, 'flysfo_api_flight-status_*.json*')), key=lambda p: re.search(r'_(\d{8}T\d{6}Z)', p).group(1))
        if not c: sys.exit('no flysfo snapshot in %s: run `gatecheck.py fetch` first' % CACHE)
        path = c[-1]
    op = gzip.open if path.endswith('.gz') else open
    d = json.load(op(path, 'rt'))
    recs = [r for r in d['data'] if not r.get('is_code_share')]  # code-share duplicates carry is_code_share: true
    return path, d.get('last_update'), recs

REGIONAL = {'SKW', 'RPA', 'ASH', 'ENY', 'QXE', 'EDV', 'GJS', 'JIA', 'PDT', 'CPZ'}  # operate for UA/AA/DL/AS under marketing numbers
def stand_base(n):
    """SFO AODB stand names add a suffix letter to some gate numbers (A1V, A4T, B5S, C9V, E10U, G13S ...); strip it."""
    m = re.match(r'^([A-G]\d+)[A-Z]?$', n or '')
    return m.group(1) if m else n

def stand_at(rec, T):
    """(stand name, start, end, how) of a flight's AODB stand allocation covering T; how = 'window' or 'nearest'."""
    st = [(s['stand']['stand_name'], iso(s['start_time']), iso(s['end_time'])) for s in rec.get('stands') or []]
    for n, a, b in st:
        if a is not None and b is not None and a - 60 <= T <= b + 60: return n, a, b, 'window'
    if not st: return None
    return min(st, key=lambda q: min(abs(T - (q[1] or T)), abs(T - (q[2] or T)))) + ('nearest',)

def norm_cs(c):
    """ADS-B callsigns often zero-pad the number (CAL003, SJX011); flysfo does not (CAL3, SJX11)."""
    c = (c or '').strip().upper(); m = re.match(r'^([A-Z]{3})0*(\d+)([A-Z]*)$', c)
    return m.group(1) + m.group(2) + m.group(3) if m else c

def flights_for(recs, callsign):
    cs = norm_cs(callsign)
    hit = [r for r in recs if norm_cs(r.get('callsign')) == cs]
    if hit or not cs: return hit, 'callsign'
    m = re.match(r'^([A-Z]{3})(\d+)[A-Z]?$', cs)
    if m and m.group(1) in REGIONAL:
        hit = [r for r in recs if r['flight_number'].lstrip('0') == m.group(2).lstrip('0') and r['airline']['iata_code'] in ('UA', 'AA', 'DL', 'AS')]
        return hit, 'regional number'
    return [], 'none'

def published_for(recs, by_id, a, T, moved=None):
    """The flight(s) the aircraft is on at T: arrival already blocked in / departure not yet off block, following
    linked_flight_id (the AODB's arrival->departure turn link)."""
    fl, how = flights_for(recs, a.get('flight'))
    arr = [r for r in fl if r['flight_kind'] == 'Arrival' and (iso(r.get('actual_in_off_block_time')) or iso(r.get('estimated_in_off_block_time')) or 9e18) <= T + 600]
    dep = [r for r in fl if r['flight_kind'] == 'Departure' and (iso(r.get('actual_in_off_block_time')) or 9e18) >= T - 120
           and (iso(r.get('estimated_in_off_block_time')) or iso(r.get('scheduled_in_off_block_time')) or 0) >= T - 6 * 3600]
    arr.sort(key=lambda r: iso(r.get('actual_in_off_block_time')) or 0); dep.sort(key=lambda r: iso(r.get('estimated_in_off_block_time')) or 0)
    # an arrival that blocked in before the aircraft last moved is not the one it is parked from (same number re-used,
    # a later leg, or a tow): drop it
    if moved is not None: arr = [r for r in arr if (iso(r.get('actual_in_off_block_time')) or iso(r.get('estimated_in_off_block_time')) or 0) >= moved - 300]
    A = arr[-1] if arr else None; D = dep[0] if dep else None
    if A and not D and A.get('linked_flight_id') in by_id: D = by_id[A['linked_flight_id']]
    if D and not A:
        for r in recs:
            if r.get('linked_flight_id') == D['flight_id'] and r['flight_kind'] == 'Arrival': A = r
    return A, D, how

def occupancy(recs, T):
    """AODB stand allocations covering T: stand name -> [(flight_id, type, callsign)]."""
    occ = {}
    for r in recs:
        for s in r.get('stands') or []:
            a, b = iso(s['start_time']), iso(s['end_time'])
            if a is not None and b is not None and a - 60 <= T <= b + 60:
                occ.setdefault(s['stand']['stand_name'], []).append((r['flight_id'], (r.get('aircraft_transport_type') or {}).get('icao_code'), r.get('callsign')))
    return occ

# ------------------------------------------------------------------ check
def check(T, window, recs, gates, taxi, types, tracks, min_still=120):
    by_id = {r['flight_id']: r for r in recs}
    occ = occupancy(recs, T)
    rows = []
    for a in sorted(parked_at(tracks, T, window, gates), key=lambda a: (a.get('flight') or '~', a.get('r') or '')):
        moved = tracks.last_moving(a['hex'], T); since = tracks.still_since(a['hex'], T)
        if since is None or T - since < min_still: continue   # parked = stationary (within 5 m) for min_still seconds
        if not (a.get('flight') or '').strip():  # transponders often drop the callsign at the gate: use the last one seen
            cs = tracks.last_callsign(a['hex'], T)
            if cs: a = dict(a, flight=cs, flight_from_history=True)
        T_ = types.get(a.get('t') or '') or None
        where, cand = match_stands(gates, taxi, a['x'], a['z'], T_, a.get('true_heading'))
        best = cand[0] if cand else None; second = cand[1] if len(cand) > 1 else None
        geo_only = None
        if not cand and not where:
            _, c2 = match_stands(gates, taxi, a['x'], a['z'], T_, a.get('true_heading'), fits=False)
            if c2: geo_only = c2[0][3]['name']
        A, D, how = published_for(recs, by_id, a, T, moved)
        pub = []  # (source, stand, how, gate)
        for rec in (A, D):
            if not rec: continue
            s = stand_at(rec, T)
            pub.append(dict(flight=rec['flight_id'], kind=rec['flight_kind'], gate=(rec.get('gate') or {}).get('gate_number'),
                            stand=s[0] if s else None, stand_how=s[3] if s else None, type=(rec.get('aircraft_transport_type') or {}).get('icao_code'),
                            remark=rec.get('remark'), stands=[x['stand']['stand_name'] for x in rec.get('stands') or []]))
        ours = best[3] if best else None
        names = ({ours['name'], *ours['alias'], *ours['bridges']} if ours else set())
        occ_here = []
        if ours:
            for sn, lst in occ.items():
                if stand_base(sn) in names: occ_here += [(sn,) + q for q in lst]
        # published stand at T for this aircraft: arrival's covering window, else the departure's, else gates
        cover = [p for p in pub if p['stand_how'] == 'window']
        pstand = cover[0]['stand'] if cover else None
        verdict = None
        near = nearest_stand(gates, a['x'], a['z'], T_, a.get('true_heading'))
        if pstand:
            if not ours and not geo_only and (where or near['dist'] > 45):
                verdict = 'off-stand (SFO window %s still open: pushed back / towed?)' % pstand
            elif not ours: verdict = 'no-match' + (' (' + where + ')' if where else '') + (
                ' (class-rejected; geometry matches %s)' % geo_only if geo_only else '')
            elif stand_base(pstand) == ours['name']: verdict = 'agree'
            elif stand_base(pstand) in names: verdict = 'alias'
            else: verdict = 'DISAGREE'
        elif pub:
            # no stand allocation covering T: fall back to the published gate of the arrival (after block-in), else
            # of the departure
            g = next((p['gate'] for p in pub if p['kind'] == 'Arrival' and p['gate']), None) or next((p['gate'] for p in pub if p['gate']), None)
            if not ours: verdict = 'off-stand' if not geo_only else 'class-rejected (geometry matches %s, published gate %s)' % (geo_only, g)
            elif not g: verdict = 'no-window'
            elif g == ours['name']: verdict = 'agree (gate)'
            elif g in names: verdict = 'alias (gate)'
            else: verdict = 'DISAGREE (gate %s)' % g
        elif occ_here:
            types_here = {q[2] for q in occ_here}
            verdict = 'occupancy-type-match' if a.get('t') in types_here else 'occupancy-type-differs'
        elif not ours:
            verdict = ('class-rejected (geometry matches %s)' % geo_only) if geo_only else 'off-stand' + (' (' + where + ')' if where else '')
        else:
            same = sorted({sn for sn, lst in occ.items() for q in lst if q[1] == a.get('t')})
            verdict = 'no allocation at our stand; same-type allocations: ' + (','.join(same) or 'none')
        rows.append(dict(hex=a['hex'], flight=(a.get('flight') or '').strip(), reg=a.get('r'), type=a.get('t'), op=a.get('ownOp'), prov=a['prov'],
                         lat=round(a['lat'], 6), lon=round(a['lon'], 6), nac_p=a.get('nac_p'), n_pos=a.get('n_pos'), spread=a.get('spread'), x=round(a['x'], 1), z=round(a['z'], 1), true_heading=a.get('true_heading'), gs=a.get('gs'),
                         excluded=where, ours=ours['name'] if ours else None, ours_alias=(ours['alias'] if ours else []), ours_src=ours['src'] if ours else None,
                         ours_cls=ours['cls'] if ours else None, score=round(best[0], 1) if best else None, lat_err=round(best[1], 1) if best else None,
                         along_err=round(best[2], 1) if best else None, second=second[3]['name'] if second else None,
                         second_score=round(second[0], 1) if second else None, match_how=how, published=pub, published_stand=pstand,
                         occupancy_at_ours=occ_here, verdict=verdict, geometry_only_match=geo_only, last_moving=moved, still_since=since, tpos=a['tpos'],
                         nearest=near))
    dup = {}
    for r in rows:
        if r['ours']: dup.setdefault(r['ours'], []).append(r['hex'])
    for r in rows: r['shared_stand'] = len(dup.get(r['ours'], [])) > 1 if r['ours'] else False
    return rows

def md_table(rows, T):
    t = dt.datetime.fromtimestamp(T, dt.timezone.utc)
    L = ['| UTC | flight (ADS-B) | reg | type | published (flysfo) | published stand @T | our stand (+alias) | src/cls | lat/along err (m) | runner-up | verdict |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        pub = '; '.join(f"{p['flight']} gate {p['gate']} stands {'/'.join(p['stands']) or '-'}" for p in r['published']) or (
            'occupancy: ' + ', '.join(f'{q[0]} {q[1]} {q[2]}' for q in r['occupancy_at_ours']) if r['occupancy_at_ours'] else '-')
        ours = (r['ours'] or r['excluded'] or '-') + (' (' + ','.join(r['ours_alias']) + ')' if r['ours_alias'] else '') + (' [shared]' if r['shared_stand'] else '')
        n = r.get('nearest') or {}
        err = f"{r['lat_err']}/{r['along_err']}" if r['lat_err'] is not None else (
            f"nearest {n['name']}: {n['lat']}/{n['along']}" + (f", hdg {n['dhdg']:+.0f}°" if n.get('dhdg') is not None else '') if n else '-')
        L.append(f"| {t:%H:%M} | {r['flight'] or '-'} | {r['reg'] or '-'} | {r['type'] or '-'} | {pub} | {r['published_stand'] or '-'} | {ours} | "
                 f"{r['ours_src'] or '-'}/{r['ours_cls'] or '-'} | {err} | {r['second'] or '-'} | {r['verdict'] or '-'} |")
    return '\n'.join(L)

# ------------------------------------------------------------------ official names
MAPS = {  # official printable terminal maps, https://www.flysfo.com/maps/static-maps (hold-room gate labels)
    'T1 (B, C) eff. 11/2025': 'https://www.flysfo.com/sites/default/files/2025-11/251027_SFO_Tabloid_Face%20A_T1_Web.pdf',
    'T2 (D) eff. 11/2025': 'https://www.flysfo.com/sites/default/files/2025-11/251027_SFO_Tabloid_Face%20A_T2_Web.pdf',
    'T3 (E, F) eff. 11/2025': 'https://www.flysfo.com/sites/default/files/2025-11/251027_SFO_Tabloid_Face%20A_T3_Web.pdf',
    'INTL (A, G) eff. 7/2026': 'https://www.flysfo.com/sites/default/files/2026-09/260701_SFO_Tabloid_Face%20A_INTL_WEB.pdf',
}
def map_gate_labels():
    """Gate labels printed in the map area of the official terminal maps (grid refs and the directory excluded)."""
    import pymupdf
    out = {}
    for k, u in MAPS.items():
        p = os.path.join(CACHE, 'map_' + os.path.basename(u).replace('%20', '_'))
        if not os.path.exists(p): open(p, 'wb').write(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60).read())
        pg = pymupdf.open(p)[0]; W, H = pg.rect.width, pg.rect.height; intl = 'INTL' in k
        xmax, ymax = (W, H * 990 / 1210) if intl else (W * 1500 / 1870, H)
        own = set(re.findall(r'[A-G]', k.split('(')[1]))
        out[k] = sorted({w[4] for w in pg.get_text('words') if re.fullmatch(r'[A-G]\d{1,3}', w[4]) and w[4][0] in own
                         and W * 30 / 1870 <= w[0] <= xmax and H * 260 / 1210 <= w[1] <= ymax}, key=gkey)
    return out
gkey = lambda s: (re.sub(r'\d.*', '', s), int((re.findall(r'\d+', s) or ['0'])[0]), s)

def gates_report(recs_all):
    ours = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    our_names = {s['name'] for s in ours['stands']} | {r['name'] for r in ours.get('remote') or []}
    our_alias = {a for s in ours['stands'] for a in (s.get('alias') or [])} | {b['gate'] for s in ours['stands'] for b in s['bridges']}
    p = os.path.join(CACHE, 'datasf_gates_all.json')
    if not os.path.exists(p):
        u = DATASF_URL + '?' + urllib.parse.urlencode({'$select': 'gate,count(*) as n,min(time) as first,max(time) as last', '$group': 'gate', '$limit': 50000})
        open(p, 'wb').write(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60).read())
    datasf = {r['gate']: int(r['n']) for r in json.load(open(p)) if r.get('gate')}
    maps = map_gate_labels(); mapped = {g for v in maps.values() for g in v}
    fs_gates = {(r.get('gate') or {}).get('gate_number') for r in recs_all} - {None}
    fs_stands = {s['stand']['stand_name'] for r in recs_all for s in r.get('stands') or []}
    per_area = {}
    for L in 'ABCDEFG':
        per_area[L] = dict(
            map_gates=[g for g in sorted(mapped, key=gkey) if g[0] == L],
            datasf_gates_used={g: n for g, n in sorted(datasf.items(), key=lambda kv: gkey(kv[0])) if g[0] == L},
            flysfo_stands=[s for s in sorted(fs_stands, key=gkey) if s[0] == L],
            ours=[(s['name'], s.get('alias') or []) for s in sorted(ours['stands'], key=lambda s: gkey(s['name'])) if s['letter'] == L]
                 + [(r['name'], []) for r in ours.get('remote') or [] if r['name'][0] == L])
    return dict(maps=maps, per_area=per_area,
                flysfo_remote_stands=[s for s in sorted(fs_stands, key=gkey) if not re.match(r'^[A-G]\d+[A-Z]?$', s) or int(re.findall(r'\d+', s)[0]) > 30],
                flysfo_suffixed_stands=[s for s in sorted(fs_stands, key=gkey) if re.match(r'^[A-G]\d+[A-Z]$', s)],
                ours_not_on_maps=sorted(our_names - mapped - fs_stands, key=gkey),
                ours_not_used_in_datasf_or_flysfo=sorted(our_names - set(datasf) - {stand_base(s) for s in fs_stands} - fs_stands, key=gkey),
                map_gates_missing_in_ours=sorted(mapped - our_names - our_alias, key=gkey),
                map_gates_only_as_alias=sorted((mapped - our_names) & our_alias, key=gkey),
                datasf_used_not_own_stand_in_ours=sorted(set(datasf) - our_names, key=gkey),
                flysfo_contact_stands_not_own_stand_in_ours=sorted({stand_base(s) for s in fs_stands if re.match(r'^[A-G]\d{1,2}[A-Z]?$', s)} - our_names, key=gkey))

def simultaneous(recs_all, min_overlap=600, now=None):
    """For each of our stands that carries aliases: pairs of member gate numbers that SFO's stand plan gives to two
    different aircraft turns at the same time (overlap > min_overlap s). Such pairs are physically separate stands."""
    ivs = {}
    for r in recs_all:
        turn = tuple(sorted([r['flight_id'], r.get('linked_flight_id') or '']))
        for st in r.get('stands') or []:
            a, b = iso(st['start_time']), iso(st['end_time'])
            if a is not None and b is not None:
                ivs.setdefault(stand_base(st['stand']['stand_name']), set()).add((a, b, turn, st['stand']['stand_name'],
                                                                              (r.get('aircraft_transport_type') or {}).get('icao_code')))
    out = []
    for s in json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']:
        names = [s['name']] + (s.get('alias') or [])
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                A, B = ivs.get(names[i], set()), ivs.get(names[j], set()); ex = None; n = 0; past = 0
                for a in A:
                    for b in B:
                        if a[2] == b[2]: continue
                        lo, hi = max(a[0], b[0]), min(a[1], b[1])
                        if hi - lo > min_overlap:
                            n += 1; past += bool(now and lo < now - min_overlap)
                            if ex is None: ex = dict(frm=dt.datetime.fromtimestamp(lo, dt.timezone(dt.timedelta(hours=-7))).strftime('%d %H:%M'),
                                                     to=dt.datetime.fromtimestamp(hi, dt.timezone(dt.timedelta(hours=-7))).strftime('%d %H:%M'),
                                                     a=(a[2][0] or a[2][1], a[3], a[4]), b=(b[2][0] or b[2][1], b[3], b[4]))
                out.append(dict(ours=s['name'], cls=s['cls'], src=s['src'], pair=(names[i], names[j]), alloc=(len(A), len(B)), overlaps=n, overlaps_started_before_fetch=past, example=ex))
    return out

_MATCH_JS = r"""// Cross-check: run the app's own Traffic.matchGate (js/live/traffic.js) on gatecheck rows.
import fs from 'fs';
import { STANDS } from '%(root)s/data/sfo_stands.js';
import { AIRPORT } from '%(root)s/data/sfo_airport.js';
import { standGates } from '%(root)s/js/live/airport.js';
import { Traffic } from '%(root)s/js/live/traffic.js';
import { typeForIcao } from '%(root)s/js/live/aircraft.js';
const rows = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).rows;
const t = new Traffic({ gates: standGates(STANDS), airport: AIRPORT, persist: false });
const out = [];
for (const r of rows) {
  const m = typeForIcao(r.type);
  const tr = { hex: r.hex, model: m ? { t: m.t } : null };
  const hd = r.true_heading != null ? r.true_heading * Math.PI / 180 : 0;
  const f = { x: r.x, z: r.z, hd, hdReal: r.true_heading != null };
  const g = t.matchGate(tr, f);
  out.push({ hex: r.hex, flight: r.flight, py: r.ours, js: g ? g.name : null, jsScore: tr.gateScore ?? null, pyScore: r.score });
}
console.log(JSON.stringify(out));
"""
def crosscheck_js(rows):
    """Run the app's own Traffic.matchGate (node) on the same reports; returns {hex+T: stand or None}."""
    src = os.path.join(CACHE, 'jsmatch.mjs'); inp = os.path.join(CACHE, 'jsmatch_in.json')
    open(src, 'w').write(_MATCH_JS % {'root': ROOT})
    json.dump({'rows': rows}, open(inp, 'w'), default=str)
    out = subprocess.run(['node', src, inp], capture_output=True, text=True, timeout=300)
    return json.loads(out.stdout)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['fetch', 'check', 'gates'])
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--at', help='UTC time (ISO) to evaluate; default = last recorded report')
    ap.add_argument('--since', help='with --every: first UTC time (default: recording start)')
    ap.add_argument('--every', type=int, help='evaluate every N seconds over the recording')
    ap.add_argument('--window', type=int, default=120, help='seconds of reports to aggregate per evaluation')
    ap.add_argument('--still', type=int, default=120, help='an aircraft counts as parked after this many seconds within 5 m')
    ap.add_argument('--flysfo', help='flysfo snapshot file (default: newest)')
    ap.add_argument('--json'); ap.add_argument('--md')
    ap.add_argument('--js', action='store_true', help="also run the app's own Traffic.matchGate (node) and compare")
    o = ap.parse_args()
    if o.cmd == 'fetch': fetch(o.force); return
    path, lu, recs = load_flysfo(o.flysfo) if o.flysfo else load_flysfo_all()
    if o.cmd == 'gates':
        allrecs = []  # every snapshot fetched so far: more stand names seen
        for p in sorted(glob.glob(os.path.join(CACHE, 'flysfo_api_flight-status_*.json*'))): allrecs += load_flysfo(p)[2]
        newest = max(glob.glob(os.path.join(CACHE, 'flysfo_api_flight-status_*.json*')), key=snapshot_time)
        r = gates_report(allrecs); r['merged_stands_simultaneous'] = simultaneous(recs, now=snapshot_time(newest)); print(json.dumps(r, indent=1))
        if o.json: json.dump(r, open(o.json, 'w'), indent=1)
        return
    gates, taxi, types = load_stands(), load_taxiways(), load_types()
    tracks = Tracks(); ts = tracks.times
    if not ts: sys.exit('no recorder data in ' + REC)
    toT = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    if o.every:
        t0 = toT(o.since) if o.since else ts[0] + o.window
        times = [t for t in range(int(t0), int(ts[-1]) + 1, o.every)]
    else:
        times = [toT(o.at) if o.at else ts[-1]]
    print(f'flysfo: {os.path.basename(path)} (last_update "{lu}", {len(recs)} operating flights)', file=sys.stderr)
    allrows, md = [], []
    for T in times:
        rows = check(T, o.window, recs, gates, taxi, types, tracks, o.still)
        for r in rows: r['T'] = T
        allrows += rows; md.append(md_table(rows, T))
    # one line per aircraft+stand episode: keep the first evaluation of each (hex, ours, published_stand)
    seen, uniq = set(), []
    for r in allrows:
        k = (r['hex'], r['ours'], r['published_stand'])
        if k not in seen: seen.add(k); uniq.append(r)
    from collections import Counter
    lines = md_table([], times[0]).split('\n')
    for r in uniq: lines.append(md_table([r], r['T']).split('\n')[2])
    print('\n'.join(lines))
    if o.js:
        js = crosscheck_js(uniq); bad = [q for q, r in zip(js, uniq) if q['js'] != r['ours']]
        for q, r in zip(js, uniq): r['app_js_match'] = q['js']
        print('app matchGate (node) agrees with this reimplementation on %d/%d rows' % (len(uniq) - len(bad), len(uniq)), bad or '', file=sys.stderr)
    print('verdicts (unique aircraft/stand episodes):', dict(Counter(r['verdict'] for r in uniq)), file=sys.stderr)
    if o.json: json.dump(dict(flysfo=os.path.basename(path), last_update=lu, times=times, rows=uniq), open(o.json, 'w'), indent=1, default=str)
    if o.md: open(o.md, 'w').write('\n'.join(md) + '\n')

if __name__ == '__main__':
    import urllib.parse
    main()
