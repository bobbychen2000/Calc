"""Split one adsb.lol / readsb aircraft-day trace into coverage segments and flights, and detect observed take-offs and
landings at known airports. Shared by scan_callsigns.py (streaming) and observed_elsewhere.py (analysis).

Trace point layout (wiedehopf/readsb README-json.md, "trace jsons"): [dt, lat, lon, alt ft | "ground" | null, gs kt,
track deg, flags (1 stale, 2 new leg, 4 geom rate, 8 geom alt), vrate fpm, aircraft{} | null, src, geom_alt, ...].

Definitions used throughout (all [inf] rules of ours, not readsb's):
  segment  maximal run of positions with no gap > GAP_S (coverage segment: where the track enters / leaves coverage)
  flight   consecutive segments with one callsign, cut at a readsb new-leg flag, at a ground stop, at a callsign change
           and at gaps > 4 h (observed_elsewhere.split_gaps later cuts SHA/PVG-route flights at gaps longer than the
           leg air time + 30 min, so a short round trip hidden in the coverage gap is not one record)
  dep/arr  observed take-off / landing: a ground->air (air->ground) transition inside a segment, or a segment that
           starts (ends) below LOW_AGL ft above an airport within NEAR_KM; time extrapolated with the vertical rate
"""
import math

GAP_S = 600            # coverage gap that ends a segment
LOW_AGL = 2500         # ft above field: low enough to call a first/last fix a take-off/landing
NEAR_KM = 15.0         # max distance first/last low fix -> airport
GROUND_KM = 6.0        # max distance ground fix -> airport
R_EARTH = 6371.0


def gc_km(la1, lo1, la2, lo2):
    p = math.pi / 180
    a = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 2 * R_EARTH * math.asin(min(1.0, math.sqrt(a)))


def bearing(la1, lo1, la2, lo2):
    p = math.pi / 180
    y = math.sin((lo2 - lo1) * p) * math.cos(la2 * p)
    x = math.cos(la1 * p) * math.sin(la2 * p) - math.sin(la1 * p) * math.cos(la2 * p) * math.cos((lo2 - lo1) * p)
    return (math.atan2(y, x) / p) % 360


def angdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def xtrack_km(la, lo, la1, lo1, la2, lo2):
    """signed cross-track distance of (la, lo) from the great circle 1->2, and along-track fraction (0 at 1, 1 at 2)"""
    d13 = gc_km(la1, lo1, la, lo) / R_EARTH
    t13 = math.radians(bearing(la1, lo1, la, lo)); t12 = math.radians(bearing(la1, lo1, la2, lo2))
    xt = math.asin(max(-1, min(1, math.sin(d13) * math.sin(t13 - t12))))
    at = math.acos(max(-1, min(1, math.cos(d13) / max(1e-12, math.cos(xt)))))
    d12 = gc_km(la1, lo1, la2, lo2)
    sgn = 1 if math.cos(t13 - t12) >= 0 else -1
    return xt * R_EARTH, sgn * at * R_EARTH / max(d12, 1e-9)


class Airports:
    """spatial look-up over airports with an IATA code (VRS standing data airports, CC0)"""
    def __init__(self, airports):
        self.cells = {}
        for icao, (iata, name, lat, lon, alt, cc) in airports.items():
            if not iata or len(icao) != 4:
                continue
            self.cells.setdefault((int(math.floor(lat)), int(math.floor(lon))), []).append((icao, lat, lon, alt))

    def nearest(self, lat, lon, max_km):
        best = None
        ci, cj = int(math.floor(lat)), int(math.floor(lon))
        for i in (ci - 1, ci, ci + 1):
            for j in (cj - 1, cj, cj + 1):
                for icao, la, lo, alt in self.cells.get((i, j), ()):
                    d = gc_km(lat, lon, la, lo)
                    if d <= max_km and (best is None or d < best[1]):
                        best = (icao, d, alt)
        return best


def points(d):
    """[(t, lat, lon, alt, gs, trk, flags, vrate, src, cs_or_None)] for a decoded trace dict"""
    ts = d.get('timestamp', 0); out = []
    for q in d.get('trace', []):
        if q[1] is None:
            continue
        cs = None
        if len(q) > 8 and isinstance(q[8], dict) and q[8].get('flight'):
            cs = q[8]['flight'].strip() or None
        out.append((ts + q[0], q[1], q[2], q[3], q[4], q[5], q[6] or 0, q[7] if len(q) > 7 else None,
                    q[9] if len(q) > 9 else None, cs))
    return out


def _alt(p):
    return p[3] if isinstance(p[3], (int, float)) else None


def _ground(p):
    return p[3] == 'ground'


def segments(pts):
    segs, cur = [], []
    for p in pts:
        if cur and p[0] - cur[-1][0] > GAP_S:
            segs.append(cur); cur = []
        cur.append(p)
    if cur:
        segs.append(cur)
    return segs


def _cut(seg):
    """cut a segment at readsb new-leg flags and at ground->air transitions that follow an air->ground transition"""
    parts, cur, was_air, landed = [], [], False, False
    for p in seg:
        g = _ground(p)
        if cur and (p[6] & 2):
            parts.append(cur); cur = []; was_air = landed = False
        if cur and not g and landed:
            parts.append(cur); cur = []; was_air = landed = False
        if g and was_air:
            landed = True
        if not g:
            was_air = True
        cur.append(p)
    if cur:
        parts.append(cur)
    return parts


def _seg_cs(seg):
    c = {}
    for p in seg:
        if p[9]:
            c[p[9]] = c.get(p[9], 0) + 1
    return max(c, key=c.get) if c else None


def _end(p):
    return [round(p[0], 1), round(p[1], 4), round(p[2], 4), p[3], p[4], p[5], p[7]]


def _takeoff(part, aps):
    """observed take-off at the start of a flight part: ('ground'|'low', airport, t) or None"""
    first = part[0]
    if _ground(first):
        k = next((i for i, p in enumerate(part) if not _ground(p)), None)
        if k is None:
            return None
        g = part[k - 1]; a = part[k]
        ap = aps.nearest(g[1], g[2], GROUND_KM)
        if ap and a[0] - g[0] < 300:
            return {'ap': ap[0], 't': round(a[0], 1), 'how': 'ground', 'gap_s': round(a[0] - g[0])}
        return None
    alt = _alt(first)
    if alt is None:
        return None
    ap = aps.nearest(first[1], first[2], NEAR_KM)
    if not ap or alt - ap[2] > LOW_AGL:
        return None
    vr = first[7] if isinstance(first[7], (int, float)) and first[7] > 300 else 1500
    # need the track to climb (next fixes higher), else it is a low pass / approach
    nxt = [_alt(p) for p in part[1:8] if _alt(p) is not None]
    if nxt and max(nxt) < alt:
        return None
    dt = min(240.0, max(0.0, alt - ap[2]) / vr * 60)
    return {'ap': ap[0], 't': round(first[0] - dt, 1), 'how': 'low', 'agl': round(alt - ap[2]), 'km': round(ap[1], 1)}


def _landing(part, aps):
    last = part[-1]
    if _ground(last):
        k = max((i for i, p in enumerate(part) if not _ground(p)), default=None)
        if k is None:
            return None
        a = part[k]; g = part[k + 1]
        ap = aps.nearest(g[1], g[2], GROUND_KM)
        if ap and g[0] - a[0] < 300:
            return {'ap': ap[0], 't': round(g[0], 1), 'how': 'ground', 'gap_s': round(g[0] - a[0])}
        return None
    alt = _alt(last)
    if alt is None:
        return None
    ap = aps.nearest(last[1], last[2], NEAR_KM)
    if not ap or alt - ap[2] > LOW_AGL:
        return None
    prv = [_alt(p) for p in part[-8:-1] if _alt(p) is not None]
    if prv and min(prv) < alt:
        return None
    vr = -last[7] if isinstance(last[7], (int, float)) and last[7] < -300 else 800
    dt = min(300.0, max(0.0, alt - ap[2]) / vr * 60)
    return {'ap': ap[0], 't': round(last[0] + dt, 1), 'how': 'low', 'agl': round(alt - ap[2]), 'km': round(ap[1], 1)}


def flights(pts, aps):
    """list of flights: {cs, segs: [[entry], [exit]] per coverage segment, dep, arr, n, alt_max, parts}"""
    parts = []
    for seg in segments(pts):
        for part in _cut(seg):
            parts.append(part)
    fl = []
    for part in parts:
        cs = _seg_cs(part)
        prev = fl[-1] if fl else None
        dep = _takeoff(part, aps)
        if prev is not None and dep is None and prev['arr'] is None and not (part[0][6] & 2) \
                and (cs is None or prev['cs'] is None or cs == prev['cs']) and part[0][0] - prev['t1'] < 4 * 3600 \
                and not _ground(part[0]):
            prev['parts'].append(part); prev['t1'] = part[-1][0]
            prev['cs'] = prev['cs'] or cs
            prev['arr'] = _landing(part, aps)
            continue
        fl.append({'cs': cs, 'parts': [part], 't1': part[-1][0], 'dep': dep, 'arr': _landing(part, aps)})
    out = []
    for f in fl:
        air = [p for part in f['parts'] for p in part if not _ground(p)]
        if not air:
            continue   # ground-only (taxi / parked)
        alts = [_alt(p) for p in air if _alt(p) is not None]
        segs = [[_end(part[0]), _end(part[-1])] for part in f['parts']]
        out.append({'cs': f['cs'], 'dep': f['dep'], 'arr': f['arr'], 'segs': segs, 'n': sum(len(x) for x in f['parts']),
                    'alt_max': max(alts) if alts else None, 'parts': f['parts']})
    return out


def thin(part, dt_hi=30.0, dt_lo=8.0):
    """thinned copy of a flight part for local storage: [t, lat, lon, alt, gs, trk, vrate]"""
    out = []; last = None
    for i, p in enumerate(part):
        a = _alt(p)
        keep = i == 0 or i == len(part) - 1 or last is None or (p[6] & 2) or \
            p[0] - last >= (dt_lo if (a is None or a < 10000) else dt_hi)
        if keep:
            out.append([round(p[0], 1), round(p[1], 5), round(p[2], 5), p[3], p[4], p[5], p[7]]); last = p[0]
    return out
