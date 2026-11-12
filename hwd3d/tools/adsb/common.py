"""Shared inputs, constants and helpers of the HWD ADS-B ground analysis (hwd3d/tools/adsb/, task G4).

New file (not a fork). The record format and the fix-selection ideas come from sfo3d/tools/imagery/adsb_ground_cells.py
and sfo3d/tools/stands/adsb_parked.py @ a967f9b (see the headers of ground_cells.py and parked_stays.py, which fork them).
sfo3d/tools/live/recio.py @ a967f9b is NOT used: it reads the gzip recorder files (refs/cache/rec/*.jsonl.gz) of the live
recorder, while the committed pack is xz (refs/cache/rec_pack/*.jsonl.xz), which lzma reads directly.

Input (pinned)
--------------
sfo3d/refs/cache/rec_pack/adsblol_<YYYYMMDD_HH>.jsonl.xz @ a967f9b: adsb.lol /v2 point-query answers recorded by
sfo3d tools/live/record.py, trimmed to 25 nm / 18,000 ft of SFO (record key 'pack'; sfo3d/refs/cache/README.md). Licence:
ODbL 1.0 ("Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL"). HOURS below lists every
file of the pack (111 files; 9 of them are 32-byte empty xz streams: no polls in that hour) - pinned so the outputs
reproduce. Each line: {'t': request time (unix s), 'tr': response time, 'p': 'adsblol', 'code': HTTP status,
'd': {'now': server time (ms), 'ac': [readsb aircraft objects]}}.

Sampling (measured here, 2026-11-12; see extract.py output 'poll_pattern'): the recorder polls about every 1.3 s until
adsb.lol answers HTTP 429 (rate limit) after ~10 polls, then waits for the next minute: ~14 s observed per 60 s. A fix's
position time is d.now/1000 - seen_pos. Between bursts there is a ~46 s hole in which nothing is observed (the next
burst's first answer carries the newest position only). Every duration below is therefore known to +-~50 s at worst
and short events (a touch-and-go ground roll of 10-20 s) can fall entirely into a hole.

Coordinates: positions go through hwd3d/tools/common/hwd_frame.py wgs84_to_world (ADS-B lat/lon are WGS 84). The reported
position is the aircraft's GNSS antenna position (readsb JSON exposes neither the GPS antenna offset of the operational
status message nor whether the transmitter applied it), not the aircraft centre: for a C172 the roof antenna is order
1-3 m from the planform centre [inferred, not measured].

Pipeline (run in this order; each prints its numbers):
  python3 -I hwd3d/tools/adsb/extract.py        -> refs/cache/local/adsb/hwd_tracks.pkl (gitignored, holds hex)
  python3 -I hwd3d/tools/adsb/events.py         -> refs/cache/adsb/hwd_events.json
  python3 -I hwd3d/tools/adsb/parked_stays.py   -> refs/cache/adsb/hwd_parked_stays.json
  python3 -I hwd3d/tools/adsb/ground_cells.py   -> refs/cache/adsb/hwd_ground_cells.json
  python3 -I hwd3d/tools/adsb/runup_holds.py    -> refs/cache/adsb/hwd_runup_holds.json
  python3 -I hwd3d/tools/adsb/plot_ground.py    -> out/phase1/adsb_ground*.png (gitignored)

Identity (default D1, docs/PLAN.md 6a): the ICAO address ('hex') is used in memory and in the gitignored local cache
(refs/cache/local/adsb/) only, to group fixes into tracks. Committed outputs hold positions, type designators, ADS-B
emitter categories, source classes and counts; no hex, registration, callsign/flight or exact time stamp.
"""
import json, lzma, math, os, sys
import datetime as dt

HWD = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))   # hwd3d/
REPO = os.path.dirname(HWD)
sys.path.insert(0, os.path.join(HWD, 'tools', 'common'))
import hwd_frame as F                                          # noqa: E402

PACK = os.path.join(REPO, 'sfo3d', 'refs', 'cache', 'rec_pack')
PACK_COMMIT = 'a967f9b'
OUT_DIR = os.path.join(HWD, 'refs', 'cache', 'adsb')            # committed aggregates (+ SOURCES.json)
LOCAL = os.path.join(HWD, 'refs', 'cache', 'local', 'adsb')     # gitignored: per-aircraft track cache (holds hex)
PLOTS = os.path.join(HWD, 'out', 'phase1')                      # gitignored: plots for humans
TRACKS = os.path.join(LOCAL, 'hwd_tracks.pkl')
for _d in (OUT_DIR, LOCAL, PLOTS):
    os.makedirs(_d, exist_ok=True)

# every file of sfo3d/refs/cache/rec_pack @ a967f9b (ls on 2026-11-12): 111 hours, 4 Nov 17Z .. 11 Nov 13Z 2026
HOURS = (['20261104_%02d' % h for h in range(17, 24)] +
         ['20261105_%02d' % h for h in range(24)] +
         ['20261106_%02d' % h for h in range(7)] +
         ['20261107_%02d' % h for h in range(1, 24)] +
         ['20261108_%02d' % h for h in range(24)] +
         ['20261109_%02d' % h for h in list(range(14)) + list(range(18, 24))] +
         ['20261110_10', '20261110_22'] +
         ['20261111_%02d' % h for h in range(10, 14)])
assert len(HOURS) == 111

ATTRIBUTION = 'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/).'
LICENCE = ('ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/) - aggregate derived from adsb.lol data (https://adsb.lol, ODbL 1.0); '
           'OSM location labels: (c) OpenStreetMap contributors, ODbL 1.0')

# ------------------------------------------------------------------------------------------------ field and time
FIELD_ELEV_FT = F.FIELD_ELEV_FT                                 # 52.1 ft, NASR APT_BASE ELEV
# Tower hours 0700-2100 local: FAA NASR ATC_BASE (docs/PLAN.md section 1). Local = PST = UTC-8 for the whole recording
# (US DST ended Sun 1 Nov 2026 02:00 local, 15 USC 260a: first Sunday of November).
UTC_OFFSET_H = -8
TOWER_OPEN_H, TOWER_CLOSE_H = 7, 21


def local_dt(t):
    return dt.datetime.utcfromtimestamp(t + UTC_OFFSET_H * 3600)


def tower_open(t):
    h = local_dt(t); hh = h.hour + h.minute / 60 + h.second / 3600
    return TOWER_OPEN_H <= hh < TOWER_CLOSE_H


# ------------------------------------------------------------------------------------------------ source classes
# readsb 'type' field (readsb README-json.md: adsb_icao, adsb_icao_nt, adsr_icao, tisb_icao, adsc, mlat, other, mode_s,
# adsb_other, adsr_other, tisb_other, tisb_trackfile) [list from memory of the readsb docs, not re-read]
SRC_CLASS = {'adsb_icao': '1090', 'adsb_icao_nt': '1090', 'adsb_other': '1090',
             'adsr_icao': 'UAT', 'adsr_other': 'UAT',          # ADS-R = UAT (978 MHz) traffic re-sent on 1090 [inferred]
             'tisb_icao': 'TIS-B', 'tisb_other': 'TIS-B', 'tisb_trackfile': 'TIS-B',
             'mlat': 'MLAT', 'mode_s': 'ModeS', 'adsc': 'ADS-C'}


def src_class(s):
    return SRC_CLASS.get(s or '', 'other')


# ------------------------------------------------------------------------------------------------ type classes
# ICAO type designators of helicopters seen on/near the field (ICAO Doc 8643 descriptions H1P/H2T..., from memory, not
# re-read): B06 Bell 206, B407, EC45 (H145), EC30 (H130), EC35, A109, R22, R44, R66, H60 (S-70/UH-60), AS50, AS55, S76,
# B429, B505, EC55, H500 (MD500), MD52, MD60. ADS-B emitter category A7 = rotorcraft (DO-260B) is used as well.
HELI_TYPES = {'B06', 'B06T', 'B407', 'B427', 'B429', 'B505', 'EC20', 'EC25', 'EC30', 'EC35', 'EC45', 'EC55', 'EC75', 'A109',
              'A119', 'A139', 'A169', 'R22', 'R44', 'R66', 'H60', 'S76', 'S92', 'AS50', 'AS55', 'AS65', 'H500', 'MD52',
              'MD60', 'BK17', 'B212', 'B412', 'UH1', 'H47', 'GYRO'}
_GA = None


def _ga_types():
    global _GA
    if _GA is None:
        _GA = json.load(open(os.path.join(HWD, 'data', 'ga_types.json')))['types']
    return _GA


def type_class(t, cat):
    """-> (class, src): piston_single / piston_twin / turboprop / jet from the FAA ACD row in data/ga_types.json
    (src 'obs': Physical_Class_Engine + Num_Engines); helicopter from HELI_TYPES or category A7 (src 'inf' for the list,
    'obs' for the category); light_other = designator without an ACD row, category A1/A2 (src 'inf'); unknown."""
    if (t and t in HELI_TYPES) or cat == 'A7':
        return 'helicopter', ('obs' if cat == 'A7' else 'inf')
    a = (_ga_types().get(t) or {}).get('acd') if t else None
    if a and a.get('Physical_Class_Engine'):
        e = a['Physical_Class_Engine']; n = a.get('Num_Engines') or 1
        if e == 'Piston': return ('piston_single' if n == 1 else 'piston_twin'), 'obs'
        if e == 'Turboprop': return 'turboprop', 'obs'
        if e == 'Jet': return 'jet', 'obs'
    if t:
        return ('light_other' if cat in ('A1', 'A2', None) else 'other'), 'inf'
    return 'unknown', 'obs'


def is_heli(ac):
    return ac.get('cls') == 'helicopter'


# ------------------------------------------------------------------------------------------------ geometry
RWY_HALF_W = {'10L/28R': F.RWY_DATA['10L/28R']['widthFt'] * F.FT / 2, '10R/28L': F.RWY_DATA['10R/28L']['widthFt'] * F.FT / 2}


def rwy_pos(x, z):
    """-> list of (runway id, along from the 10x end (m), across right of the 10x direction (m), length (m))."""
    out = []
    for a, b in F.RWY_PAIRS:
        al, ac = F.rwy_along_across(a, x, z)
        out.append(('%s/%s' % (a, b), al, ac, F.rwy_axis(a)['length']))
    return out


def on_runway(x, z, margin=8.0, end_margin=60.0):
    """runway id whose paved strip (+margin across, +end_margin beyond the ends) contains (x, z), else None.
    Margin default 8 m: GNSS EPU of NACp 10 is < 10 m (DO-260B NACp table, from memory) [inferred]."""
    best = None
    for rid, al, ac, L in rwy_pos(x, z):
        if -end_margin <= al <= L + end_margin and abs(ac) <= RWY_HALF_W[rid] + margin:
            if best is None or abs(ac) < best[1]: best = (rid, abs(ac))
    return best[0] if best else None


def rwy_end_for(rid, trk):
    """runway end used (e.g. '28L') from the runway id and a track (deg true): 10x for an eastbound track."""
    a, b = rid.split('/')
    hd = F.rwy_axis(a)['hdg']
    d = abs((trk - hd + 180) % 360 - 180)
    return a if d < 90 else b


def load_osm():
    return json.load(open(os.path.join(HWD, 'refs', 'cache', 'osm', 'khwd_features.json')))


def circ_mean(deg, w=None):
    import numpy as np
    a = np.radians(np.asarray(deg, float)); w = np.ones_like(a) if w is None else np.asarray(w, float)
    s = (np.sin(a) * w).sum(); c = (np.cos(a) * w).sum()
    R = math.hypot(s, c) / max(w.sum(), 1e-9)
    return float(np.degrees(np.arctan2(s, c)) % 360), float(R)


def angdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def dur_bucket(s):
    if s < 300: return '< 5 min'
    for lim, name in ((600, '5-10 min'), (1800, '10-30 min'), (3600, '30-60 min'), (3 * 3600, '1-3 h'), (8 * 3600, '3-8 h')):
        if s < lim: return name
    return '>= 8 h'


def write_json(path, obj, compact=False):
    with open(path, 'w') as f:
        if compact: json.dump(obj, f, separators=(',', ':'))
        else: json.dump(obj, f, indent=1)
    return os.path.getsize(path)
