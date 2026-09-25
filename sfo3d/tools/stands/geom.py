"""Shared stand / jet-bridge geometry for tools/stands/build_stands.py and check_stands.py (review round 1, 24 Sep 2026).

Aircraft (review round 2: the app's own geometry, not a class shape)
  APP: js/aircraft/types.js after applySpec, dumped by tools/stands/dump_types.mjs to refs/cache/stands/app_types.json
      (re-dumped automatically when types.js is newer): per ICAO designator L, span, fuselage radius R, wing (rootLE,
      rootC, tipC, sweep), tailplane, left main-deck doors, dock2.
  accepted_types(s, app_rule): every APP designator the app lets park on the stand - js/live/traffic.js standFits:
      span <= maxSpan + 0.6 and L <= maxLen + 2 (maxSpan / maxLen = js/live/airport.js CLASS_MAX limited by span_max /
      len_max); with app_rule=True also its oversize clause 'maxSpan >= 64 and span <= 80' (A380 / 747-8 / 777-9 on
      every stand whose maxSpan reaches 64 m - a traffic.js defect, docs/requests/static_geometry_round2.md).
  planform(nose, hdg, t): the ground-physics collision shape of js/live/ground.js inside(): fuselage rectangle
      (0..L, +-R), wing trapezoid (LE = rootLE + |y| tan(sweep), chord rootC -> tipC at the tip), tailplane rectangle
      (hstab.x .. L, +-span/2). envelope(): union over the accepted types, all with the nose at the stand's nose point.
  door(nose, hdg, t, k): left main-deck door k (types.js doors[k-1], on the fuselage side at R).
  dock_door(t, k): L1 -> door 1; L2 -> types.js dock2 (None = the L2 bridge does not dock this type; e.g. the 767-200/
      -300, whose optional 2L door is not in the fleet default).

Jet bridges (apron-drive, Oshkosh AeroTech Jetway sell sheet 2025,
https://oshkoshaerotech.com/hubfs/images/Jetway%20SteelGlass_Truss_Sell-Sheet_2025.pdf, read by the review round 1):
  operational extension (rotunda centre to cab) 9.846 m (smallest model AT2 41/55) to 41.381 m (largest AT3 72/150);
  cab rotation 125 deg standard (92.5 cw / 32.5 ccw), 185 deg optional; rotunda swing +-87.5 deg (175 deg total).
  The operational dimensions run from the rotunda centre to the centre of the CAB PIVOT (sheet footnote); the sheet's full
  retraction 12.224 m minus the operational retraction 9.846 m (AT2 41/55) gives the pivot -> cab spacer distance,
  2.378 m. PIVOT_TO_DOOR = 2.4 m (that distance; the closure/bellows adds a few dm, not modelled) is used everywhere a
  door position is turned into a bridge extension (review round 2: the checker used 3.0 m, geom.py 2.5 m).
  Footprints used here: fixed walkway 2.6 m wide, rotunda diameter 4.9 m, tunnel 2.9 m, cab 3.3 m x 3.6 m.
"""
import math
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

EXT_MIN, EXT_MAX = 9.846, 41.381           # m, rotunda centre -> cab pivot (see above)
CAB_ROT_STD, CAB_ROT_OPT = 92.5, 150.0     # deg; beyond 150 no cab option reaches (185 deg total, asymmetric)
CAB_CW, CAB_CCW = 92.5, 32.5               # review round 3: standard cab 125 deg = 92.5 cw / 32.5 ccw (signed test)
CAB_OPT_HALF = 92.5                        # optional 185 deg cab: +-92.5 (its split is not given; inferred symmetric)
ROT_SWING = 87.5                           # deg either side of the fixed walkway direction (175 deg total)
WALK_W, ROT_R, TUN_W, CAB_L, CAB_W = 2.6, 2.45, 2.9, 3.3, 3.6
PIVOT_TO_DOOR = 2.4                        # m, cab pivot -> door when docked (datasheet 12.224 - 9.846 = 2.378 m, see above)

import json, os, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__)); _ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_APP_JSON = os.path.join(_ROOT, 'refs', 'cache', 'stands', 'app_types.json')
_TYPES_JS = os.path.join(_ROOT, 'js', 'aircraft', 'types.js')
_DUMP = os.path.join(_HERE, 'dump_types.mjs')
if not os.path.exists(_APP_JSON) or os.path.getmtime(_APP_JSON) < max(os.path.getmtime(_TYPES_JS), os.path.getmtime(_DUMP)):
    subprocess.run(['node', _DUMP], check=True, capture_output=True)
APP = json.load(open(_APP_JSON))
ALIAS = {'E175': 'E75L', 'B787': 'B789', 'B76W': 'B763', 'B75W': 'B752', 'E295': 'E195'}   # designators seen at SFO without an APP entry

# Winglets (review round 3). Boeing Commercial Airplanes, Airport Compatibility, "Wingspan Increases Due to the Addition
# of Winglets" (5/2/2014, Aviation Partners Boeing data; https://www.boeing.com/content/dam/boeing/v2/airports/faq/
# wingletspans.pdf, cached refs/cache/boeing3v/wingletspans.pdf, read 25 Sep 2026): 757-200/-300 124'10" (38.0 m) ->
# 134'9" (41.1 m); 767-300ER 156'1" (47.6 m) -> 167'0" (50.9 m) (retrofits). js/aircraft/types.js models the baseline
# spans. The ADS-B / ICAO designators B752 / B753 / B763 do not say whether an airframe carries winglets (SFO's AODB
# writes B75W / B76W for some operators only), so every planform, class and clearance here uses the winglet span: a
# verified upper bound, the fit per airframe is NOT verified (inferred worst case). 'span_app' keeps the types.js span
# for the APP view (what js/live/traffic.js standFits compares).
WINGLET_SPAN = {'B752': 41.1, 'B753': 41.1, 'B763': 50.9}
for _t, _sp in WINGLET_SPAN.items():
    if _t in APP and APP[_t]['span'] and APP[_t]['span'] < _sp:
        APP[_t]['span_app'] = APP[_t]['span']; APP[_t]['span'] = _sp; APP[_t]['winglet'] = True


def span_app(t):
    r = APP[t]; return r.get('span_app', r['span'])


# Oshkosh AeroTech Jetway Glass & Steel Truss apron-drive models (sell sheet 2025, refs/cache/sun_night/
# oshkosh_jetway_steelglass.pdf, re-read 25 Sep 2026 in review round 3): operational retraction / extension, measured
# from the rotunda centre to the centre of the cab pivot. Review round 3: one bridge is ONE model, so its reach is that
# model's range, not 9.846-41.381 m (the smallest model's retraction .. the largest model's extension).
MODELS = [('AT2 41/55', 9.846, 12.264), ('AT2 46/65', 11.370, 15.312), ('AT2 51/75', 12.894, 18.360),
          ('AT2 56/85', 14.418, 21.408), ('AT2 61/95', 15.942, 24.456), ('AT2 66/105', 17.466, 27.504),
          ('AT2 72/116', 19.294, 30.857), ('AT2 77/126', 20.818, 33.905), ('AT2 82/136', 22.342, 36.953),
          ('AT2 88/147', 24.171, 40.306),
          ('AT3 42/70', 10.276, 16.997), ('AT3 47/85', 11.800, 21.569), ('AT3 52/100', 13.324, 26.141),
          ('AT3 58/116', 15.152, 31.018), ('AT3 61/127', 16.219, 34.219), ('AT3 65/133', 17.286, 36.200),
          ('AT3 68/144', 18.353, 39.400), ('AT3 72/150', 19.420, 41.381)]


def choose_model(e_lo, e_hi, tol=0.0):
    """the datasheet model whose operational range covers [e_lo, e_hi] (within tol m), preferring the shortest
    retraction (the bridge can rest closest to the building), then the shortest extension. None if no model covers."""
    ok = [m for m in MODELS if m[1] <= e_lo + tol and m[2] >= e_hi - tol]
    return min(ok, key=lambda m: (m[1], m[2])) if ok else None


def _bs():
    import build_stands as BS
    return BS


def hv(h):
    r = math.radians(h); return (math.sin(r), -math.cos(r))


def rv(h):
    r = math.radians(h); return (math.cos(r), math.sin(r))


def limits(s):
    BS = _bs(); sp, L = BS.CLASS_MAX[s['cls']]
    if s.get('span_max'): sp = min(sp, s['span_max'] + 0.1)
    if s.get('len_max'): L = min(L, s['len_max'] + 0.1)
    return sp, L


def app(t):
    return APP.get(ALIAS.get(t, t))


def accepted_types(s, app_rule=False):
    """types the stand accepts. app_rule=False: the data's rule (class limits, span_max / len_max, and the whitelist
    types_ok where the builder set one); app_rule=True: what js/live/traffic.js standFits does today (no types_ok,
    plus the >= 64 m oversize clause)"""
    sp, L = limits(s); out = []
    if s.get('types_ok') and not app_rule: return [t for t in s['types_ok'] if t in APP]
    for t, r in APP.items():
        if r['span'] is None: continue
        span = span_app(t) if app_rule else r['span']        # the app compares types.js spans (no winglets)
        if (span <= sp + 0.6 and r['L'] <= L + 2) or (app_rule and sp >= 64 and span <= 80): out.append(t)
    return out


def planform(nose, hdg, t, visual=False):
    """js/live/ground.js inside() shape of type t with its nose at `nose` (the app's collision shape: square nose).
    visual=True: the fuselage nose tapers elliptically over types.js Ln, as the rendered airframe does - used where a
    bridge tunnel meets the fuselage near door 1 (the collision rectangle would claim empty air beside the nose)."""
    r = app(t); f, rt = hv(hdg), rv(hdg)
    def P(x, y): return (nose[0] - f[0] * x + rt[0] * y, nose[1] - f[1] * x + rt[1] * y)
    L, R = r['L'], r['R']
    if visual and r.get('Ln'):
        Ln = r['Ln']; xs = [Ln * i / 12 for i in range(13)]
        side = [(x, R * math.sqrt(max(0.0, 1 - (1 - x / Ln) ** 2))) for x in xs]
        parts = [Polygon([P(x, -w) for x, w in side] + [P(L, -R), P(L, R)] + [P(x, w) for x, w in reversed(side)])]
    else: parts = [Polygon([P(0, -R), P(L, -R), P(L, R), P(0, R)])]
    w = r['wing']
    if w:
        b = r['span'] / 2; tn = math.tan(math.radians(w['sweep']))
        for s_ in (-1, 1):
            parts.append(Polygon([P(w['rootLE'], 0), P(w['rootLE'] + b * tn, s_ * b), P(w['rootLE'] + b * tn + w['tipC'], s_ * b), P(w['rootLE'] + w['rootC'], 0)]))
    h = r['hstab']
    if h: parts.append(Polygon([P(h['x'], -h['span'] / 2), P(L, -h['span'] / 2), P(L, h['span'] / 2), P(h['x'], h['span'] / 2)]))
    # engine nacelles (review round 3; types.js eng / rear as js/aircraft/model.js places them): underwing front at the
    # wing leading edge at the engine's z (LE swept from z0 = 0.88 R) minus fwd, nacelle + nozzle 1.12 len long, +-r
    if w:
        tn = math.tan(math.radians(w['sweep']))
        for e in r.get('eng') or []:
            x0 = w['rootLE'] + (e['z'] - 0.88 * R) * tn - e['fwd']
            for s_ in (-1, 1): parts.append(Polygon([P(x0, s_ * e['z'] - e['r']), P(x0 + 1.12 * e['len'], s_ * e['z'] - e['r']),
                                                     P(x0 + 1.12 * e['len'], s_ * e['z'] + e['r']), P(x0, s_ * e['z'] + e['r'])]))
    e = r.get('rear')
    if e:
        for s_ in (-1, 1): parts.append(Polygon([P(e['x'], s_ * e['z'] - e['r']), P(e['x'] + 1.12 * e['len'], s_ * e['z'] - e['r']),
                                                 P(e['x'] + 1.12 * e['len'], s_ * e['z'] + e['r']), P(e['x'], s_ * e['z'] + e['r'])]))
    return unary_union([p.buffer(0) for p in parts])


_ENV = {}


def envelope(nose, hdg, types, buffer=0.0):
    key = (round(nose[0], 2), round(nose[1], 2), round(hdg, 3), tuple(sorted(types)), buffer)
    if key not in _ENV:
        g = unary_union([planform(nose, hdg, t) for t in types])
        _ENV[key] = g.buffer(buffer) if buffer else g
    return _ENV[key]


FAMILY = {}
for _f, _ts in {'B737': 'B736 B737 B738 B739 B37M B38M B39M B3XM', 'A320': 'A319 A19N A320 A20N A321 A21N',
                'B757': 'B752 B753', 'B767': 'B762 B763 B764', 'EJET': 'E170 E75L E75S E190 E195', 'A220': 'BCS1 BCS3',
                'CRJ': 'CRJ2 CRJ7 CRJ9', 'B777': 'B772 B77L B773 B77W B779', 'B787': 'B788 B789 B78X',
                'A330': 'A332 A333 A338 A339', 'A350': 'A359 A35K', 'B747': 'B744 B748', 'A380': 'A388', 'MD11': 'MD11'}.items():
    for _t in _ts.split(): FAMILY[_t] = _f


def nose_for(s, t, per_type=True):
    """nose point of type t on stand s: the stand nose, moved along the axis by the stand's observed per-family stop
    offset (s['type_stops'][family]['along'], ADS-B; build_stands.py) when per_type"""
    ts = (s.get('type_stops') or {}).get(FAMILY.get(ALIAS.get(t, t))) if per_type else None
    if not ts: return tuple(s['nose'])
    f = hv(s['hdg']); a = ts['along']
    return (s['nose'][0] + f[0] * a, s['nose'][1] + f[1] * a)


def stand_env(s, buffer=0.0, app_rule=False, per_type=True, shift=0.0):
    """envelope of every accepted type on stand s. per_type: at the data's per-family stop points (type_stops); False =
    every type at the one stand nose, as js/live/traffic.js parks them today. shift: extra along-axis offset (m, - = short
    of the stop; traffic.js parks up to 25 m short)"""
    ts = accepted_types(s, app_rule); f = hv(s['hdg'])
    groups = {}
    for t in ts:
        n = nose_for(s, t, per_type); groups.setdefault((round(n[0] + f[0] * shift, 2), round(n[1] + f[1] * shift, 2)), []).append(t)
    parts = [envelope(n, s['hdg'], tt, buffer) for n, tt in groups.items()]
    return parts[0] if len(parts) == 1 else unary_union(parts)


def fus_half(t):
    return app(t)['R']


def door(nose, hdg, t, k):
    """left main-deck door k of type t (None if the app has no such door)"""
    r = app(t); ds = r['doors'] if r else []
    if not k or k > len(ds): return None
    d = ds[k - 1]; f, rt = hv(hdg), rv(hdg); w = r['R']
    return (nose[0] - f[0] * d - rt[0] * w, nose[1] - f[1] * d - rt[1] * w)


def dock_door(t, k):
    """which door a bridge with door number k docks on type t (types.js): L1 -> door 1; L2 -> dock2 (None: no docking)"""
    r = app(t)
    if not r or not r['doors']: return None
    if k == 1: return 1
    if k == 2: return r['dock2']
    return None


def bridge_parts(br, cab_pt, pivot=None):
    """shapely footprint of a bridge whose cab end (tunnel end) is at cab_pt: fixed walkway polyline, rotunda disc,
    tunnel pivot -> cab_pt and a cab box beyond it. Returns (walk, rotunda, tunnel+cab)"""
    pv = pivot or br.get('rotunda') or br['attach']
    walk = br.get('walk') or [br['attach']]
    wl = LineString(list(walk) + [pv]).buffer(WALK_W / 2, cap_style=2) if len(walk) >= 1 and math.dist(walk[0], pv) > 0.5 else Point(pv).buffer(0.01)
    rot = Point(pv).buffer(ROT_R) if br.get('rotunda') else Point(pv).buffer(0.01)
    L = math.dist(pv, cab_pt)
    if L < 0.5: return wl, rot, Point(pv).buffer(0.01)
    u = ((cab_pt[0] - pv[0]) / L, (cab_pt[1] - pv[1]) / L)
    tun = LineString([pv, cab_pt]).buffer(TUN_W / 2, cap_style=2)
    ce = (cab_pt[0] + u[0] * CAB_L, cab_pt[1] + u[1] * CAB_L)
    cab = LineString([cab_pt, ce]).buffer(CAB_W / 2, cap_style=2)
    return wl, rot, unary_union([tun, cab])


def angle(a, b):
    """signed angle from vector a to vector b (deg, + = clockwise in x east / z south)"""
    return math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))
