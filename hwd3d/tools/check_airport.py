"""Check data/hwd_airport.json (tools/build_airport.py) against its sources and against the FAA design clearances.

New for hwd3d (Phase 1, task G5). Prints a report; exit code 1 if a hard check fails. Writes nothing into the
repository (a copy of the report goes to out/phase1/g5/check_airport.txt, gitignored).

Checks
  1. Runway ends, displaced thresholds, lengths, widths, lighting and approach-aid fields against the FAA NASR rows,
     read again from refs/cache/faa/nasr_2026-10-29_HWD.json (not from hwd_frame's constants): world x / z recomputed
     with hwd_frame.ll_to_world (exact to the 0.01 m rounding), y = elevation ft x 0.3048; traffic side / TPA against
     the Chart Supplement transcription.
  2. Runway pavement against NAIP: the outline is the NASR rectangle (recomputed and compared), and the white runway
     edge stripes are measured again on NAIP 2024 and 2022 (tools/airport/rwy_edges.py; FAA AC 150/5340-1M para 2.8:
     outer stripe edge = edge of the usable runway). Residual = painted edge minus NASR edge per side; tolerance
     EDGE_TOL (one NAIP pixel is 0.6 m).
  3. Taxiway designations, read from the AL-5015 2611 PDF itself (text layer, pdftotext -bbox, mapped through the
     diagram affine): every taxiway label glyph (A, A1, B ... Z1) must lie within LABEL_TOL m of an OSM way with the same
     ref, and the set of label refs must equal the set of OSM refs - hard. Ways whose ref the diagram does not support
     (ref_src 'inf') are listed. Every way with ref A1 / Z1 carries the NASR wingspan limit (100 / 94 ft) - hard.
     NAIP paint per way (rewritten after the round-1 re-check, which found taxiway E zig-zagging between its paint and its
     old position while the earlier 50 m section test passed): the yellow ridges are measured again along every open way's
     final geometry (build_airport.ridge_scan, stations shifted by PAINT_PHASE from the build's). A 20 m window (step
     10 m) with >= 6 ridges, |median| > 1.0 m and IQR <= 0.8 m is off the paint. Hard: (a) no off-paint window anywhere on
     a moved way (round 2: junction tapers included); (a2) a way changed only by a junction attachment has no off-paint
     window that its OSM line lacks; (b1) no zig-zag on any changed way: its displacement from the OSM line is never a
     local extremum more than KINK_M deeper than both points KINK_H m away (no exemption); (b2) no lateral kink in a moved
     way: the second difference over +-10 m of its displacement from the OSM line (khwd_features.json) <= 0.5 m outside
     its recorded junction tapers; (c) every unchanged / attached way with an off-paint window carries
     paint_offset_unsnapped (its offsets recorded). The review build fails (a), (b1), (b2) and (c) (run with --data on it).
     Taxi network topology (round 2, topology_check): every OSM vertex shared by two or more taxiway / taxilane ways is one
     vertex in the data on every member way within TOPO_NODE_M of the node (or a shallow fork: the ending way's built end
     is a vertex of the other within FORK_M, OSM angle < FORK_DEG), and built ways touch or cross only at shared vertices
     (unless OSM already crosses without a node) - hard. The round-1 build fails.
  4. Every parking spot centre on pavement: inside an OSM apron polygon, or within PAVE_TWY m of an OSM taxiway / taxilane
     centreline, or NAIP 2024 grey (median saturation < SAT_MAX and excess green < EG_MAX in a 2 m disc - a
     calibration read on this mosaic: asphalt / concrete aprons 0.04-0.14, grass 0.19-0.36). A spot passing only the
     NAIP test is reported.
  5. No spot centre inside a building footprint (OSM hangars, buildings, tower; point in polygon) - hard.
  6. Spot spacing against the size class: FAA AC 150/5300-13B Chg 1 Table 5-1 recommends a 10 ft (3 m) clearance for
     ADG I and II parking positions and Figure E-2 sets tiedown spacing to "Wingspan plus 10 ft (3 m) for critical
     aircraft" (Figure E-3: "10 ft (3 m) Minimum wing tip separation"); the quotes are asserted against the text of the
     committed extract refs/cache/faa/ac150_5300_13b_chg1_p136_181_284-288.pdf. Since the round-1 re-check every spot is
     a wing + fuselage planform (length / span recounted here from the observed types, FAA ACD, else C172; a disc
     without a heading). For every pair of spots closer than 45 m the planforms at max_span_m keep 10 ft and at
     capacity_span_m CAP_GAP - hard (consistency checks: the build sizes with the same rule); helipad spots take part as
     discs; spots flagged no_design_size are listed and left out of the design-size pair test. Planform vs every
     building / hangar, the spot's own hangar included; only a door spot (verified: <= HGR_DOOR_M from its hangar wall,
     heading to the nearest wall point) may enter its own hangar with its nose, its wing keeping CAP_GAP - hard.
     Independent of the sizing: no two ramp / hangar-apron spots closer than DUP_M - hard; observed types recounted and
     compared with the spots' flags - hard if they disagree; n_observations = NAIP years + adsb.lol sessions and src
     by the >= 2 rule - hard; an independent recount of sessions near every obs spot finds >= 2 - hard. Spot vs
     taxiways: planform (capacity size) vs AC Table 4-1 ADG I object distances (13.6 / 12.0 m), reported per src; hard
     for rule-made spots, which must also be reachable over OSM pavement within CONNECT_M (own Dijkstra, pave_path) and
     carry an 'ok' by-eye review (build_airport.HGR_REVIEW) - hard. The unspotted_aircraft list must not hold an
     aircraft that now has a spot within 5 m - hard. Round 2: every heading-less disc holds the wing + fuselage planform
     at every heading - hard; a presence recount from the gitignored per-aircraft files, without the session numbers
     (presence_recount; SKIPPED without them) finds >= 2 for every obs spot - hard; the omission sweep (omission_sweep)
     finds no NAIP 2024 aircraft-mask part on an OSM apron farther than build_airport.SWEEP_R from every spot and listed
     aircraft without a by-eye verdict (build_airport.SWEEP_REVIEW) - hard. Round 3: NAIP aircraft accounting
     (naip_accounting): every NAIP 2024 aircraft blob of the build's grouping is a spot, a listed aircraft or a by-eye
     verdict, both by-eye centres of a two-aircraft blob (build_airport.TWO_AIRCRAFT_CENTRES) have a spot or a listed
     aircraft within TWO_MATCH_M, and every split-blob spot lies on a by-eye centre - hard; the build's record of the NAIP
     aircraft dropped by the LANE_M rule has none 'NOT ACCOUNTED' - hard; the omission sweep no longer treats a
     two-aircraft review blob as an exclusion point.
  7. Hot spots: the OSM taxiways inside each AL-5015 ellipse against the taxiways the CS hot-spot text names. A
     consistency check of the diagram registration and the OSM refs; HS whose CS text names no taxiway (HS 2, 3, 4) are
     reported as 'not checkable against the CS'.
  8. Holds: NAIP bar vs OSM node offset; distance from the runway centreline per runway.
  9. Data hygiene: every element has src 'obs' / 'inf' and refs that exist in 'sources'; the .js twin carries the same
     object as the .json. D1 (no ADS-B identity in any committed file; since the Phase 1 review): every committed
     ADS-B-derived file (D1_FILES: refs/cache/registry/*.json, data/hwd_airport.*, data/ga_types.json, refs/cache/adsb/*, docs/phase1/*.json,
     docs/*.md) is scanned for identity keys (hex, icao24, callsign, flight, registration, r ...), per-row time keys
     (t, t0, time, seen ...) and epoch-second numbers, N-number-like tokens, and any token equal to a hex address,
     registration or callsign of an aircraft that the pinned adsb.lol recording saw within 5 km of the ARP
     (identity_set, read from sfo3d/refs/cache/rec_pack) - hard; in each session of hwd_parked_stays.json the signal
     starts and ends differ by at most 1 (round 2: power cycles in place) and it spans at most 2 x SESSION_R_M - hard (a
     necessary condition only: the committed file has no time order). Round 3, with the gitignored per-aircraft files
     (session_check_local; SKIPPED without them): committed = local session numbers, one aircraft per session, its
     consecutive events linked by the parked_stays rule (no departure that the recording shows), starts / ends alternating
     in time, no split of a linked pair, and summary.session_joins recounted - hard; the joins that bridge recorder
     outages are reported, not excluded. Spot-id tokens in the data text and in build_airport's by-eye records must name
     spots of the data (spot_id_refs) - hard. SOURCES coverage: every committed data file under
     data/, refs/cache/ (not local/, not .parts/) and docs/phase1/ matches a key (or glob key) of a SOURCES.json in its
     folder or a parent folder - hard; every SOURCES entry has made_by or note - hard; every text / JSON file whose
     SOURCES licence names the ODbL carries the ODbL URI itself - hard; src / *_src values in every committed JSON are
     obs / inf / null (field-documentation maps skipped; the documented ga_types 'none' listed) - hard.
usage: python3 hwd3d/tools/check_airport.py [--data FILE] [--paint-only]
"""
import json, math, os, re, subprocess, sys
from collections import Counter

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.abspath(os.path.join(HERE, '..'))
for p in ('common', 'imagery', 'airport'):
    sys.path.insert(0, os.path.join(HERE, p))
import hwd_frame as F                                                     # noqa: E402
from paintline import Naip                                                # noqa: E402
import rwy_edges                                                          # noqa: E402
import al5015                                                             # noqa: E402
sys.path.insert(0, HERE)
import build_airport as B                                                 # noqa: E402  (constants and the faint-section rule)

FT = 0.3048
EDGE_TOL = 0.6      # m, |median painted edge - NASR edge| per side (one NAIP pixel)
PAVE_TWY = 7.5      # m, half of a 50 ft (TDG 3) taxiway (AC 150/5300-13B Table 4-2) - generous for HWD's taxiways
SAT_MAX, EG_MAX = 0.16, 8.0
WINGTIP = 10 * FT
LABEL_TOL = 15.0    # m: an AL-5015 taxiway label glyph lies beside its taxiway (measured 0.1-11.6 m in the Phase 1 review)
LABEL_FAR = 100.0   # m: label glyphs farther than this from every OSM way are not taxiway labels (legend / notes)
LABEL_ON_M = 8.0    # m: a glyph that is not an OSM ref counts as a diagram taxiway label missing in OSM only this close to an
                    # OSM taxiway centreline (the other single letters of AL-5015 - X closed-surface marks, runway-side
                    # letters, symbol letters, the WEST HANGARS glyphs - lie 14 m or more from every centreline)
PAINT_PHASE = 1.0   # m: the check's ridge stations sit half-way between the build's (FAINT_STEP 2 m from s = 0)
PAINT_WIN_M, PAINT_WIN_N = 20.0, 6   # m, ridges: off-paint windows (round-1 re-check: E was off by 3.3 m over 14-22 m stretches)
PAINT_OFF_M, PAINT_IQR_M = 1.0, 0.8  # m: |median| above this with an IQR at most this = off the paint
KINK_H, KINK_M = 10.0, 0.5           # m: lateral second difference of a move over +-KINK_H m above KINK_M = a kink (the review
                                     # build's E zig-zag: 3.3 m ramps over ~20 m give about 1.6 m; a smooth fit gives < 0.1 m)
TOPO_NODE_M = 8.0   # m: a junction's shared vertex may lie this far from its OSM node (the largest move is 3.5 m) [chosen]
FORK_DEG, FORK_M = 30.0, 20.0   # a shallow fork may meet up to FORK_M m from the OSM node (build_airport J_FORK_DEG / J_FORK_M)
AC_QUOTES = [  # (where, text) - asserted against pdftotext -layout of the committed extract (whitespace-normalised)
    ('Table 5-1. Parking Position Clearance (PDF p. 181, printed 5-7)', 'Table 5-1. Parking Position Clearance.'),
    ('Table 5-1 row', 'I and II 10 ft (3 m)'),
    ('Table 5-1 row', 'III, IV, V, and VI 25 ft (7.6 m)'),
    ('Figure E-2. Tiedown Spacing (PDF p. 287, printed E-5)', 'Wingspan plus 10 ft (3 m) for critical aircraft'),
    ('Figure E-3. Nested Tiedowns (PDF p. 288, printed E-6)', '10 ft (3 m) Minimum wing tip separation'),
    ('E.2.3.4 Tiedown Anchor Layout (PDF p. 286, printed E-4)', 'Provide two wing tiedown anchors at the end of the marked stripe spaced at least half the wingspan of the critical aircraft.'),
    ('E.2.3.2 Tiedown Characteristics (PDF p. 285, printed E-3)', 'Commonly includes a 6-inch (152 mm) yellow striped marking in the shape of a tee to demonstrate the location for wing axis and tail location.'),
    ('Table 4-1 (PDF p. 136, printed 4-10)', 'TSA (maximum ADG wingspan)'),
]
OUT = []


def r1(v): return None if v is None else round(float(v), 1)


def say(s=''):
    print(s); OUT.append(s)


D1_FILES = ['refs/cache/registry/*.json', 'data/hwd_airport.json', 'data/hwd_airport.js', 'data/ga_types.json', 'refs/cache/adsb/*.json', 'refs/cache/adsb/*.txt',
            'docs/phase1/*.json', 'docs/*.md']
ID_KEYS = {'hex', 'icao', 'icao24', 'icao_hex', 'callsign', 'flight', 'registration', 'reg', 'r', 'owner', 'squawk'}
TIME_KEYS = {'t', 't0', 't1', 'time', 'ts', 'utc', 'seen', 'seen_pos', 'now', 'timestamp', 'local_h'}
ADSB_RE = re.compile(r'(adsb|ga_types|hwd_airport|phase1/)')
EPOCH_OK = {'.sampling.span_s[]'}   # hwd_events.json: first / last poll of the whole recording (not per aircraft)


def identity_set(box_m=5000.0):
    """hex, registration (r) and callsign (flight) of every aircraft that reported a position within box_m of the ARP
    in the pinned adsb.lol recording (sfo3d/refs/cache/rec_pack, the input of tools/adsb/): the identities a committed
    file must not contain (D1). Read with lzma/json only; nothing is written."""
    import glob, lzma
    sys.path.insert(0, os.path.join(HERE, 'adsb'))
    pack = os.path.join(os.path.dirname(HWD), 'sfo3d', 'refs', 'cache', 'rec_pack')
    files = sorted(glob.glob(os.path.join(pack, 'adsblol_*.jsonl.xz')))
    hx, rr, fl = set(), set(), set()
    for f in files:
        for line in lzma.open(f, 'rt'):
            r = json.loads(line)
            if r.get('code') != 200: continue
            for a in r['d'].get('ac', []):
                if 'lat' not in a: continue
                x, z = F.wgs84_to_world(a['lat'], a['lon'])
                if math.hypot(x, z) > box_m: continue
                hx.add(a['hex'].lower().lstrip('~'))
                if a.get('r'): rr.add(a['r'].strip().upper())
                if a.get('flight') and a['flight'].strip(): fl.add(a['flight'].strip().upper())
    return hx, rr, fl, len(files)


def d1_scan():
    """D1 (docs/PLAN.md 6a): no committed file holds a per-aircraft identity derived from ADS-B. Scans every committed
    ADS-B-derived file (D1_FILES) for (a) identity keys and per-row time keys in JSON objects, (b) N-number-like
    tokens, (c) any token equal to a hex address, registration or callsign of an aircraft seen within 5 km of the ARP
    in the recording (identity_set), (d) epoch-second numbers (1.6e9-2.1e9) in JSON. Returns the list of problems."""
    import glob
    hx, rr, fl, nf = identity_set()
    say('   D1 identity set from the recording (%d files, aircraft within 5 km of the ARP): %d hex, %d registrations, %d callsigns' % (nf, len(hx), len(rr), len(fl)))
    files = sorted({f for pat in D1_FILES for f in glob.glob(os.path.join(HWD, pat))})
    probs = []

    def walk(o, path, keys, nums, strs):
        if isinstance(o, dict):
            for k, v in o.items():
                keys.add((path, k)); walk(v, path + '.' + k, keys, nums, strs)
        elif isinstance(o, list):
            for v in o: walk(v, path + '[]', keys, nums, strs)
        elif isinstance(o, bool): pass
        elif isinstance(o, (int, float)): nums.append((path, o))
        elif isinstance(o, str): strs.append(o)
    for f in files:
        rel_ = os.path.relpath(f, HWD); txt = open(f, encoding='utf-8').read()
        keys, nums, strs = set(), [], []
        if f.endswith('.json') or f.endswith('.js'):
            body = txt[txt.index('export const HWD_AIRPORT = ') + 27:].rstrip().rstrip(';') if f.endswith('.js') else txt
            walk(json.loads(body), '', keys, nums, strs)
        else:
            strs = [txt]
        tokens = set()
        for st in strs: tokens |= set(re.findall(r'[~A-Za-z0-9-]+', st))
        bad_k = sorted({k for _, k in keys if k in ID_KEYS})
        bad_t = sorted({'%s.%s' % (p_, k) for p_, k in keys if k in TIME_KEYS and '[]' in p_}) if ADSB_RE.search(rel_) else []
        bad_e = sorted({p_ for p_, v in nums if 1.6e9 <= v <= 2.1e9 and p_ not in EPOCH_OK})
        up = {t.upper() for t in tokens}
        bad_n = sorted({t for t in up if re.fullmatch(r'N[1-9][0-9]{0,4}[A-HJ-NP-Z]{0,2}', t) and len(t) >= 3})
        bad_h = sorted({t for t in tokens if len(t.lstrip('~')) == 6 and t.lower().lstrip('~') in hx})
        bad_r = sorted({t for t in up if len(t) >= 4 and t in rr})
        bad_f = sorted({t for t in up if len(t) >= 4 and t in fl})
        hit = {k: v for k, v in (('identity keys', bad_k), ('per-row time keys', bad_t), ('epoch numbers at', bad_e), ('N-number-like', bad_n),
                                 ('hex of a recorded aircraft', bad_h), ('registration of a recorded aircraft', bad_r),
                                 ('callsign of a recorded aircraft', bad_f)) if v}
        say('   D1 %-46s %s' % (rel_, 'clean' if not hit else 'FOUND %s' % {k: v[:6] for k, v in hit.items()}))
        if hit: probs.append((rel_, hit))
    say('   D1: %d committed ADS-B-derived files scanned, %d with a finding' % (len(files), len(probs)))
    return probs


def sources_coverage():
    """every committed data file (git ls-files + untracked, not ignored) under data/, refs/cache/ and docs/phase1/ has a
    key (exact, glob, or one of several comma-separated names) in a SOURCES.json of its folder or a parent folder"""
    import fnmatch
    root = os.path.dirname(HWD)
    ls = subprocess.run(['git', '-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', 'hwd3d/data', 'hwd3d/refs/cache', 'hwd3d/docs/phase1'],
                        capture_output=True, text=True, check=True).stdout.split()
    files = sorted(os.path.relpath(os.path.join(root, f), HWD) for f in ls if os.path.basename(f) != 'SOURCES.json')
    miss = []; entry = {}
    for f in files:
        d = os.path.dirname(f); ok = False
        while True:
            sj = os.path.join(HWD, d, 'SOURCES.json')
            if os.path.exists(sj):
                rel_ = os.path.relpath(f, d) if d else f
                for k, v in json.load(open(sj)).items():
                    if any(fnmatch.fnmatch(rel_, kk.strip()) for kk in k.split(',')): ok = True; entry[f] = (os.path.relpath(sj, HWD), k, v); break
            if ok or not d: break
            d = os.path.dirname(d)
        if not ok: miss.append(f)
    say('   SOURCES coverage: %d committed data files under data/, refs/cache/, docs/phase1/; without a SOURCES.json entry: %d %s' % (len(files), len(miss), miss))
    # provenance residuals (round-1 re-check): every SOURCES entry names its maker or carries a note; every committed text /
    # JSON file whose SOURCES licence names the ODbL carries the licence URI in the file itself
    sjs = sorted(os.path.relpath(os.path.join(root, f), HWD) for f in subprocess.run(['git', '-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', 'hwd3d'],
                 capture_output=True, text=True, check=True).stdout.split() if os.path.basename(f) == 'SOURCES.json')
    nomaker = [(sj, k) for sj in sjs for k, v in json.load(open(os.path.join(HWD, sj))).items() if not k.startswith('_') and not (isinstance(v, dict) and (v.get('made_by') or v.get('note')))]
    say('   SOURCES entries (%d files) without made_by or note: %d %s' % (len(sjs), len(nomaker), nomaker))
    odbl = [f for f in files if f in entry and 'odbl' in json.dumps(entry[f][2]).lower() and f.rsplit('.', 1)[-1] in ('json', 'js', 'txt', 'csv', 'md')]
    nouri = [f for f in odbl if 'opendatacommons.org/licenses/odbl' not in open(os.path.join(HWD, f), encoding='utf-8', errors='replace').read()]
    say('   text / JSON files whose SOURCES licence names the ODbL: %d; without the ODbL URI in the file itself: %d %s' % (len(odbl), len(nouri), nouri))
    return miss + ['SOURCES entry without made_by / note: %s' % (x,) for x in nomaker] + ['no ODbL URI: %s' % f for f in nouri]


def pave_path(x, z, FE, res=1.0):
    """shortest path (m) from an open OSM taxiway / taxilane centreline (+1 m) to (x, z) over OSM pavement (aprons and
    taxi-line buffers of build_airport.PAVE_TWY) around OSM buildings / hangars (+1 m): Dijkstra on an 8-neighbour 1 m grid
    (scipy.sparse.csgraph); an implementation independent of build_airport.taxi_path; None if not reachable within 100 m"""
    from shapely import contains_xy
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    is_open = lambda w: w.get('status', 'open') == 'open' and not w['tags'].get('abandoned') and not w['tags'].get('disused')
    lines = unary_union([LineString(w['w']) for k in ('taxiway', 'taxilane') for w in FE[k] if is_open(w)])
    pav = unary_union([Polygon(a['w']).buffer(0) for a in FE['apron']] + [LineString(w['w']).buffer(B.PAVE_TWY) for k in ('taxiway', 'taxilane') for w in FE[k] if is_open(w)])
    bld = unary_union([Polygon(h['w']).buffer(1.0) for h in FE['hangar']] + [Polygon(b['w']).buffer(1.0) for b in FE['building'] + FE['control_tower'] if len(b.get('w', [])) > 3])
    R = 100.0; xs = np.arange(x - R, x + R + 1e-9, res); zs = np.arange(z - R, z + R + 1e-9, res); X, Z = np.meshgrid(xs, zs)
    m = contains_xy(pav, X, Z) & ~contains_xy(bld, X, Z); src = contains_xy(lines.buffer(1.0), X, Z) & m
    ny, nx = m.shape; idx = np.arange(ny * nx).reshape(ny, nx); rows_, cols_, w_ = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        x0, x1 = (0, nx - dx) if dx >= 0 else (-dx, nx)
        a = idx[0:ny - dy, x0:x1]; b = idx[dy:ny, x0 + dx:x1 + dx]
        ok = m.ravel()[a.ravel()] & m.ravel()[b.ravel()]
        rows_.append(a.ravel()[ok]); cols_.append(b.ravel()[ok]); w_.append(np.full(ok.sum(), math.hypot(dx, dy) * res))
    G = coo_matrix((np.concatenate(w_), (np.concatenate(rows_), np.concatenate(cols_))), shape=(ny * nx, ny * nx)).tocsr()
    sidx = idx[src]
    if not len(sidx): return None
    i, j = int(round((z - zs[0]) / res)), int(round((x - xs[0]) / res))
    d = dijkstra(G, directed=False, indices=[idx[i, j]], limit=R)[0]
    v = float(d[sidx].min())
    return None if not np.isfinite(v) else v


def _disp(osm_pts, built_pts, step=2.0):
    """lateral displacement of a built line from its OSM line, every step m along the OSM line (intersection of the
    OSM normal with the built line within +-8 m; nan where there is none)"""
    O = B.densify(osm_pts, step); SO = B.arclen(O); TO = B.tangents(O); fin = LineString(built_pts)
    so = np.arange(0.0, SO[-1] + 1e-9, step); dl = []
    for s_ in so:
        p_ = np.array([np.interp(s_, SO, O[:, 0]), np.interp(s_, SO, O[:, 1])]); t_ = np.array([np.interp(s_, SO, TO[:, 0]), np.interp(s_, SO, TO[:, 1])]); t_ /= np.hypot(*t_)
        n_ = np.array([-t_[1], t_[0]]); hit = LineString([tuple(p_ - 8 * n_), tuple(p_ + 8 * n_)]).intersection(fin)
        pts_ = [np.array(g.coords[0]) for g in getattr(hit, 'geoms', [hit]) if not g.is_empty and g.geom_type == 'Point']
        dl.append(min((float(np.dot(q_ - p_, n_)) for q_ in pts_), key=abs) if pts_ else np.nan)
    return so, np.array(dl)


def paint_check(D, FE):
    """check 3, NAIP paint per way (see the module docstring); returns the hard failures"""
    hard = []
    # NAIP paint on the final geometry (round-1 re-check: the review build's E was a zig-zag that a 50 m section test
    # passed; round-2 re-check: junction tapers were exempt). Ridges are re-measured with build_airport.ridge_scan at
    # stations shifted by PAINT_PHASE from the build's, on the final line and (for changed ways) on the OSM line.
    N24p = Naip('2024'); hp = [(h['x'], h['z']) for h in D['holds']]
    osm_w = {w['osm']['id']: w for k in ('taxiway', 'taxilane') for w in FE[k]}
    moved_bad = []; unrec = []; worse = []; kinks = []; zig = []; n_win = 0; n_moved = 0; n_adj = 0; n_rec = 0; nways = 0; kmax = []; zmax = []
    def wins_of(P_):
        S_ = B.arclen(P_); T_ = B.tangents(P_)
        ss, fo = B.ridge_scan(N24p, P_, S_, T_, hp, phase=PAINT_PHASE)
        return B.off_windows(ss, fo, win=PAINT_WIN_M, nmin=PAINT_WIN_N, med_min=PAINT_OFF_M, iqr_max=PAINT_IQR_M)
    for w in D['taxiways'] + D['taxilanes']:
        if w['status'] != 'open': continue
        P_ = B.densify(w['pts'], 2.0); S_ = B.arclen(P_)
        if S_[-1] < 8.0: continue
        nways += 1; oid = int(w['id'].split('/')[-1]); O_ = osm_w[oid]['w']
        moved = bool(w['evidence']['naip_paint'].get('snapped_len_m')); n_moved += moved
        so, dl = _disp(O_, w['pts'])
        changed = moved or bool(np.nanmax(np.abs(dl)) > 0.05) if np.isfinite(dl).any() else moved
        adjusted = changed and not moved; n_adj += adjusted
        wins = wins_of(P_); n_win += len(wins)
        if wins and moved: moved_bad.append((w['id'], w['ref'], [(q['s0_m'], q['n'], q['median_m']) for q in wins]))
        elif wins and not w.get('paint_offset_unsnapped'): unrec.append((w['id'], w['ref'], [(q['s0_m'], q['n'], q['median_m']) for q in wins]))
        elif wins: n_rec += 1
        if adjusted and wins:   # a junction attachment must not take a way off its paint: compare with the OSM line
            wo = wins_of(B.densify(O_, 2.0))
            for q in wins:
                pre = [r for r in wo if abs(r['s0_m'] - q['s0_m']) <= PAINT_WIN_M / 2 and abs(r['median_m']) >= abs(q['median_m']) - 0.3]
                if not pre: worse.append((w['id'], q['s0_m'], q['median_m'], [(r['s0_m'], r['median_m']) for r in wo]))
        if not changed: continue
        # (b1) zig-zag, everywhere (no exemption): the displacement from the OSM line returns towards the old position
        #      and leaves it again - a local extremum deeper than KINK_M against both neighbours KINK_H m away
        h = int(round(KINK_H / 2.0)); zw = 0.0; zat = None
        for i in range(h, len(so) - h):
            a_, b_, c_ = dl[i - h], dl[i], dl[i + h]
            if not np.isfinite([a_, b_, c_]).all(): continue
            dep = min(abs(b_ - a_), abs(b_ - c_)) if (b_ - a_) * (b_ - c_) > 0 else 0.0
            if dep > zw: zw, zat = dep, so[i]
        zmax.append((w['id'], w['ref'], round(float(zw), 2)))
        if zw > KINK_M: zig.append((w['id'], w['ref'], round(float(zw), 2), r1(zat)))
        # (b2) lateral kinks of a moved way: second difference over +-KINK_H m outside its recorded junction tapers
        if moved:
            L_ = so[-1]; tz = []
            for j in w['evidence']['naip_paint'].get('junctions', []):
                if j['role'] == 'end' and j.get('taper_m'):
                    tz.append((0.0, j['taper_m']) if j['s_m'] < 1.0 else (L_ - j['taper_m'], L_))
            worst = 0.0
            for i in range(h, len(so) - h):
                if any(a0 - KINK_H < so[i] < a1 + KINK_H for a0, a1 in tz): continue
                v = abs(dl[i + h] - 2 * dl[i] + dl[i - h])
                if np.isfinite(v): worst = max(worst, float(v))
            kmax.append((w['id'], w['ref'], round(worst, 2)))
            if worst > KINK_M: kinks.append((w['id'], w['ref'], round(worst, 2)))
    say('   NAIP 2024 yellow ridges re-measured on the final geometry of %d open ways (stations every %.0f m from s = %.1f m; build_airport.ridge_scan): %d-m windows (step %.0f m) with >= %d ridges, |median| > %.1f m and IQR <= %.1f m = off the paint' % (
        nways, B.FAINT_STEP, PAINT_PHASE, PAINT_WIN_M, PAINT_WIN_M / 2, PAINT_WIN_N, PAINT_OFF_M, PAINT_IQR_M))
    say('   moved ways: %d; off-paint windows anywhere on them (junction tapers included): %d %s' % (n_moved, len(moved_bad), moved_bad))
    say('   ways changed only by a junction attachment: %d; off-paint windows the attachment made (no window at least as far off on the OSM line): %d %s' % (n_adj, len(worse), worse))
    say('   zig-zag (displacement from the OSM line a local extremum > %.2f m deeper than both points %.0f m away; every changed way, no exemption): largest %s; failing: %d %s' % (
        KINK_M, KINK_H, sorted(zmax, key=lambda t: -t[2])[:5], len(zig), zig))
    say('   moved ways: largest lateral second difference of the move over %.0f m (outside the recorded junction tapers) %s; above %.2f m: %d %s' % (KINK_H, kmax, KINK_M, len(kinks), kinks))
    say('   unchanged / attached ways with off-paint windows: %d, all recorded as paint_offset_unsnapped: %s %s' % (n_rec + len(unrec), 'yes' if not unrec else 'NO', unrec))
    if moved_bad: hard.append('moved taxiway off its paint')
    if worse: hard.append('junction attachment off the paint')
    if zig: hard.append('taxiway zig-zag')
    if kinks: hard.append('lateral kink in a moved taxiway')
    if unrec: hard.append('unrecorded paint offset')
    return hard


def topology_check(D, FE):
    """check 3, taxi network topology (round-2 re-check: whole-way moves had left 22 joins without a shared vertex).
    (a) every OSM vertex shared by two or more taxiway / taxilane ways (or closing a closed way) is ONE vertex in the
    data: every member way has a vertex there, all identical (to 0.015 m), within TOPO_NODE_M of the OSM node;
    (b) built ways that touch or cross do so only at a shared vertex, unless their OSM ways already cross without one.
    Returns the hard failures."""
    hard = []
    built = {int(w['id'].split('/')[-1]): w['pts'] for w in D['taxiways'] + D['taxilanes']}
    osm = {w['osm']['id']: w['w'] for k in ('taxiway', 'taxilane') for w in FE[k] if w['osm']['id'] in built}
    nodes = {}
    for o in sorted(osm):
        for i, p in enumerate(osm[o]): nodes.setdefault((p[0], p[1]), []).append((o, i))
    nodes = {k: v for k, v in nodes.items() if len(v) >= 2}
    bad = []; shifts = []; forks = []
    def odir(o, i):
        W_ = np.asarray(osm[o], float); j = i + 1 if i < len(W_) - 1 else i - 1; v = W_[j] - W_[i]; return v / max(1e-9, np.hypot(*v))
    def fork_ok(k, mem):
        # a shallow fork (build_airport J_FORK_*): two OSM ways, one ending on the other's interior at < FORK_DEG; the ending
        # way's built end is a vertex of the other's built line within FORK_M of the OSM node
        if len(mem) != 2: return None
        (a, ia), (b, ib) = mem
        for (o, i), (t, it) in (((a, ia), (b, ib)), ((b, ib), (a, ia))):
            if i not in (0, len(osm[o]) - 1) or it in (0, len(osm[t]) - 1): continue
            ang = math.degrees(math.acos(min(1.0, abs(float(odir(o, i) @ odir(t, it))))))
            e_ = built[o][0] if i == 0 else built[o][-1]; T_ = np.array(built[t])
            on = float(np.min(np.hypot(T_[:, 0] - e_[0], T_[:, 1] - e_[1]))); dk = math.hypot(e_[0] - k[0], e_[1] - k[1])
            if ang < FORK_DEG and on <= 0.015 and dk <= FORK_M: return (k, o, t, r1(ang), r1(dk))
        return None
    for k, mem in sorted(nodes.items()):
        cand = None; ok = True
        for o, _ in mem:
            P = np.array(built[o]); d = np.hypot(P[:, 0] - k[0], P[:, 1] - k[1])
            vs = P[d <= TOPO_NODE_M]
            if not len(vs): ok = False; break
            if cand is None: cand = [tuple(v) for v in vs]
            else: cand = [c for c in cand if np.min(np.hypot(vs[:, 0] - c[0], vs[:, 1] - c[1])) <= 0.015]
        if not ok or not cand:
            fk = fork_ok(k, mem)
            if fk: forks.append(fk); continue
            gap = max(LineString(built[a]).distance(LineString(built[b])) for (a, _) in mem for (b, _) in mem if a != b) if len({o for o, _ in mem}) > 1 else None
            bad.append((k, sorted({o for o, _ in mem}), r1(gap) if gap is not None else None))
        else:
            shifts.append(min(math.hypot(c[0] - k[0], c[1] - k[1]) for c in cand))
    say('   network: %d OSM junction vertices (shared by two or more taxiway / taxilane ways); one shared vertex in the data within %.0f m of the OSM node: %d; NOT shared: %d (%d of them with a gap > 0.05 m between the ways) %s' % (
        len(nodes), TOPO_NODE_M, len(shifts), len(bad), sum(1 for b_ in bad if b_[2] is not None and b_[2] > 0.05), bad[:12]))
    say('   shift of the shared vertices from their OSM node: max %.2f m, %d moved by > 0.05 m' % (max(shifts or [0]), sum(1 for v in shifts if v > 0.05)))
    say('   shallow forks (a way ending on another at < %.0f deg in OSM; its built end is a vertex of the other within %.0f m of the OSM node): %d %s' % (FORK_DEG, FORK_M, len(forks), forks))
    # (b) crossings / touches away from shared vertices
    from shapely.geometry import MultiPoint
    ids = sorted(built); lines = {o: LineString(built[o]) for o in ids}; ext = []; osm_x = set()
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if not lines[a].intersects(lines[b]): continue
            g = lines[a].intersection(lines[b]); pts = [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Point']
            va = np.array(built[a]); vb = np.array(built[b])
            for q in pts:
                x, z = q.coords[0]
                if np.min(np.hypot(va[:, 0] - x, va[:, 1] - z)) <= 0.015 and np.min(np.hypot(vb[:, 0] - x, vb[:, 1] - z)) <= 0.015: continue
                oa, ob = LineString(osm[a]), LineString(osm[b])
                if oa.intersects(ob):
                    og = oa.intersection(ob); ops = [r for r in getattr(og, 'geoms', [og]) if r.geom_type == 'Point']
                    if any(min(math.hypot(r.x - c[0], r.y - c[1]) for c in osm[a]) > 0.05 or min(math.hypot(r.x - c[0], r.y - c[1]) for c in osm[b]) > 0.05 for r in ops):
                        osm_x.add((a, b)); continue
                ext.append((a, b, r1(x), r1(z)))
    say('   built ways touching or crossing away from a shared vertex: %d %s; OSM\'s own crossings without a node (kept): %s' % (len(ext), ext[:12], sorted(osm_x)))
    if bad: hard.append('taxi network: junction without a shared vertex')
    if ext: hard.append('taxi network: crossing away from a vertex')
    return hard


def omission_sweep(D, N):
    """round-2 re-check: the unspotted_aircraft test only caught a listed aircraft that gained a spot, never an omission.
    Own sweep: the NAIP 2024 aircraft mask (gray > tiedowns.AC_D DN over the 4 m median, closed by a 0.75 m disc, as
    tiedowns.Grid) on every OSM apron with buildings (+1 m) cut out; mask parts joined within 1 m; the pixels of a part
    farther than build_airport.SWEEP_R from every spot, listed unspotted aircraft and reviewed NAIP blob form a candidate
    when their area is >= SWEEP_MIN_M2. Each candidate needs a by-eye verdict (build_airport.SWEEP_REVIEW) within
    SWEEP_MATCH_M; a 'spot:<id>' verdict needs that spot within DUP_M + SWEEP_R of the candidate, a 'listed' one a listed
    aircraft within 15 m. Returns (candidates, unmatched, bad verdicts)."""
    import tiedowns as TD
    from scipy import ndimage as nd
    from shapely import contains_xy
    # round 3: a blob reviewed as two aircraft is not an exclusion point (it lies between the aircraft and hid one of R080's
    # two from the sweep); its by-eye centres are spots or listed aircraft, which are exclusion points themselves
    rev = [r for r in json.load(open(os.path.join(HWD, B.NAIP_REVIEW)))['items'] if r['year'] == '2024' and 'x' in r and r['verdict'] != 'two_aircraft']
    E = np.array([(s['x'], s['z']) for s in D['parking']] + [(u['x'], u['z']) for u in D.get('unspotted_aircraft') or []] + [(r['x'], r['z']) for r in rev])
    holes_all = [Polygon(h['ring']).buffer(1.0) for h in D['hangars']] + [Polygon(b['ring']).buffer(1.0) for b in D['buildings'] if b.get('ring')]
    close = np.hypot(*np.mgrid[-3:4, -3:4]) <= 3.0; join = np.hypot(*np.mgrid[-4:5, -4:5]) <= 4.0; R = TD.RES
    cands = []
    for a in D['aprons']:
        pg = Polygon(a['ring']).buffer(0); holes = [h for h in holes_all if h.intersects(pg)]
        x0, z0, x1, z1 = pg.bounds
        xs = np.arange(x0 - 6, x1 + 6, R); zs = np.arange(z0 - 6, z1 + 6, R); X, Z = np.meshgrid(xs, zs)
        I = N.sample(X, Z, 'gray'); acm = nd.binary_closing(I - nd.median_filter(I, size=int(round(4.0 / R))) > TD.AC_D, structure=close)
        inside = contains_xy(pg, X, Z)
        if holes: inside &= ~contains_xy(unary_union(holes), X, Z)
        lab, _ = nd.label(nd.binary_dilation(acm, structure=join)); lab = np.where(acm, lab, 0)
        for i, sl in enumerate(nd.find_objects(lab)):
            if sl is None: continue
            m = (lab[sl] == i + 1) & inside[sl]
            if m.sum() * R * R < B.SWEEP_MIN_M2: continue
            px, pz = X[sl][m], Z[sl][m]
            far = np.min(np.hypot(px[:, None] - E[None, :, 0], pz[:, None] - E[None, :, 1]), axis=1) > B.SWEEP_R
            if far.sum() * R * R < B.SWEEP_MIN_M2: continue
            cands.append((a['id'], round(float(px[far].mean()), 1), round(float(pz[far].mean()), 1), round(float(far.sum() * R * R), 1)))
    spots = {s['id']: s for s in D['parking']}; ua = D.get('unspotted_aircraft') or []
    unmatched = []; badv = []; verd = Counter()
    for c in cands:
        hit = [v for v in B.SWEEP_REVIEW if math.hypot(v[0] - c[1], v[1] - c[2]) <= B.SWEEP_MATCH_M]
        if not hit: unmatched.append(c); continue
        v = min(hit, key=lambda v: math.hypot(v[0] - c[1], v[1] - c[2])); verd[v[2].split(':')[0]] += 1
        if v[2].startswith('spot:'):
            s = spots.get(v[2][5:])
            if s is None or math.hypot(s['x'] - c[1], s['z'] - c[2]) > B.DUP_M + B.SWEEP_R: badv.append((c, v[2]))
        elif v[2] == 'listed':
            if not any(math.hypot(u['x'] - c[1], u['z'] - c[2]) <= 15.0 for u in ua): badv.append((c, v[2]))
        elif v[2] not in ('vehicle', 'paint', 'structure'): badv.append((c, v[2]))
    return cands, unmatched, badv, verd


def naip_accounting(D, N):
    """round-3 re-check: one aircraft of the split review blob R080 had no spot and was not listed (its half was dropped by
    the lane rule and the other half sat on the wingtip junction, so neither the 5 m stale test nor the omission sweep could
    see it). Every NAIP 2024 aircraft blob of the build's grouping (tiedowns.Grid.aircraft on the same mask, extent >=
    build_airport.AC_EXT_MIN, on every OSM apron with buildings cut out) must be accounted for:
      - review verdict vehicle / no_object / duplicate: not an aircraft;
      - review verdict two_aircraft: both by-eye centres (build_airport.TWO_AIRCRAFT_CENTRES) need a spot or a listed
        unspotted aircraft within TWO_MATCH_M;
      - otherwise the blob centroid needs a spot within MERGE_RAMP (the build attaches it), a listed aircraft within
        TWO_MATCH_M, or a by-eye SWEEP_REVIEW verdict within SWEEP_MATCH_M (paint / vehicle / structure, or spot:<id> with
        that spot present).
    And every spot whose ref_point is a split-blob position (naip_by_eye_aircraft_centre, or the older
    naip_blob_half_centroid) lies within TWO_MATCH_M of a by-eye centre. Returns (counts, failures)."""
    import tiedowns as TD
    from scipy import ndimage as nd
    rev = [r for r in json.load(open(os.path.join(HWD, B.NAIP_REVIEW)))['items'] if r['year'] == '2024' and 'x' in r]
    P = D['parking']; ua = D.get('unspotted_aircraft') or []; ids = {s['id'] for s in P}
    holes_all = [Polygon(h['ring']).buffer(1.0) for h in D['hangars']] + [Polygon(b['ring']).buffer(1.0) for b in D['buildings'] if b.get('ring')]
    disk = np.hypot(*np.mgrid[-3:4, -3:4]) <= 3.0
    near = lambda pts, x, z: min([math.hypot(a - x, b - z) for a, b in pts] or [1e9])
    sp_xy = [(s['x'], s['z']) for s in P]; ua_xy = [(u['x'], u['z']) for u in ua]
    cnt = Counter(); bad = []
    for a in D['aprons']:
        pg = Polygon(a['ring']).buffer(0); holes = [h for h in holes_all if h.intersects(pg)]
        x0, z0, x1, z1 = pg.bounds
        g = TD.Grid.__new__(TD.Grid)
        g.xs = np.arange(x0 - 6, x1 + 6, TD.RES); g.zs = np.arange(z0 - 6, z1 + 6, TD.RES); X, Z = np.meshgrid(g.xs, g.zs)
        I = N.sample(X, Z, 'gray'); g.acmask = nd.binary_closing(I - nd.median_filter(I, size=int(round(4.0 / TD.RES))) > TD.AC_D, structure=disk)
        g.poly = pg; g.holes = holes
        for b in TD.Grid.aircraft(g):
            if b['extent'] < B.AC_EXT_MIN: continue
            r = min(rev, key=lambda r: math.hypot(r['x'] - b['x'], r['z'] - b['z']))
            v = r['verdict'] if math.hypot(r['x'] - b['x'], r['z'] - b['z']) <= B.REVIEW_MATCH_M else None
            if v in ('vehicle', 'no_object', 'same_aircraft_as_another_blob'): cnt['not an aircraft (review)'] += 1; continue
            if v == 'two_aircraft':
                C = getattr(B, 'TWO_AIRCRAFT_CENTRES', {}).get(r.get('spot_id_in_review_build'))
                if not C: bad.append(('two-aircraft blob without by-eye centres', r.get('spot_id_in_review_build'), b['x'], b['z'])); continue
                for (x, z) in C:
                    if near(sp_xy, x, z) <= B.TWO_MATCH_M: cnt['two-aircraft centre: spot'] += 1
                    elif near(ua_xy, x, z) <= B.TWO_MATCH_M: cnt['two-aircraft centre: listed'] += 1
                    else: bad.append(('by-eye aircraft centre of blob %s with no spot or listed aircraft within %.0f m' % (r.get('spot_id_in_review_build'), B.TWO_MATCH_M), x, z, round(near(sp_xy, x, z), 1), round(near(ua_xy, x, z), 1)))
                continue
            x, z = b['x'], b['z']
            if near(sp_xy, x, z) <= B.MERGE_RAMP: cnt['blob: spot'] += 1; continue
            if near(ua_xy, x, z) <= B.TWO_MATCH_M: cnt['blob: listed'] += 1; continue
            vv = [w for w in B.SWEEP_REVIEW if math.hypot(w[0] - x, w[1] - z) <= B.SWEEP_MATCH_M]
            if vv and (vv[0][2] in ('paint', 'vehicle', 'structure') or (vv[0][2].startswith('spot:') and vv[0][2][5:] in ids)):
                cnt['blob: by-eye verdict %s' % vv[0][2].split(':')[0]] += 1; continue
            bad.append(('aircraft blob with no spot, listed aircraft or verdict', round(x, 1), round(z, 1), b['extent']))
    cen = [c for C in getattr(B, 'TWO_AIRCRAFT_CENTRES', {}).values() for c in C]
    for s in P:
        if s.get('ref_point') in ('naip_by_eye_aircraft_centre', 'naip_blob_half_centroid'):
            d = near(cen, s['x'], s['z'])
            cnt['split-blob spots'] += 1
            if d > B.TWO_MATCH_M: bad.append(('split-blob spot not on a by-eye aircraft centre', s['id'], round(d, 1)))
    return dict(sorted(cnt.items())), bad


SPOT_ID_RE = re.compile(r'\b[TRHP][EW]\d{3}[NS]\d{3}\b')


def spot_id_refs(D):
    """round-3 re-check: a note named spot RW130N558, which no build had (and a review entry HE383N167 for RE383N167).
    Every spot-id token in the data file's text and in the by-eye records of build_airport (UNSPOTTED_NAIP2024,
    SWEEP_REVIEW, HGR_REVIEW, HGR_REVIEW_REJECT) must name a spot of the data. Returns the missing ones."""
    ids = {s['id'] for s in D['parking']}
    txt = json.dumps({k: v for k, v in D.items() if k != 'parking'}) + json.dumps([{k: v for k, v in s.items() if k != 'id'} for s in D['parking']])
    txt += json.dumps([list(u) for u in B.UNSPOTTED_NAIP2024]) + json.dumps([list(v) for v in B.SWEEP_REVIEW]) + json.dumps(B.HGR_REVIEW) + json.dumps(B.HGR_REVIEW_REJECT)
    return sorted(set(SPOT_ID_RE.findall(txt)) - ids)


PRES_SAME_M, PRES_LEAVE_M = 15.0, 30.0   # m: same place / left (as tools/adsb/parked_stays.py SESSION_R_M / VISIT_LEAVE_M)


def presence_recount(R_, types_of, tspan):
    """independent count of aircraft presences at every obs ramp / hangar-apron spot, from the gitignored per-aircraft
    files (local only; None if absent). Events (stays, signal starts / ends) within the spot's radius (8 m; a type wider
    than build_airport.BIG_SPAN: half its span + 2 m) of the spot or its merged duplicates; per aircraft in time order, a
    new presence starts only when the next event is > PRES_SAME_M m from the previous one or the aircraft has a fix > PRES_LEAVE_M
    m from the previous event in between. Returns ([(spot id, NAIP years, presences)] below N_OBS_MIN, spots, joins)."""
    import pickle
    lf = os.path.join(HWD, 'refs', 'cache', 'local', 'adsb', 'hwd_parked_stays_local.json')
    tf = os.path.join(HWD, 'refs', 'cache', 'local', 'adsb', 'hwd_tracks.pkl')
    if not (os.path.exists(lf) and os.path.exists(tf)): return None
    L = json.load(open(lf)); T = pickle.load(open(tf, 'rb'))['tracks']
    ev = [(s['_hex'], s['_t0'], s['_t1'], s['x'], s['z']) for s in L['stays']] + [(e['_hex'], e['_t'], e['_t'], e['x'], e['z']) for e in L['signal_edges']]
    weak = []; n = 0; joins = 0
    for s in R_:
        if s['src'] != 'obs' or s['ref_point'] == 'rule_point': continue
        n += 1; st = s['strength']
        sp_ = [tspan(t) for t in types_of(s['evidence'])]; sp_ = max([x for x in sp_ if x] or [0.0])
        rr = max(B.MERGE_RAMP, sp_ / 2 + 2.0 if sp_ > B.BIG_SPAN else 0.0)
        pts = [(s['x'], s['z'])] + [(m['x'], m['z']) for m in s['evidence'].get('merged_duplicates', [])]
        near = [e for e in ev if any(math.hypot(e[3] - a, e[4] - b) <= rr for a, b in pts)]
        by = {}
        for e in near: by.setdefault(e[0], []).append(e)
        pres = 0
        for hx, es in by.items():
            es.sort(key=lambda e: (e[1], e[2])); a = T[hx]; pres += 1
            for A, Bv in zip(es, es[1:]):
                m = (a['t'] > A[2]) & (a['t'] < Bv[1])
                left = bool(m.any() and np.hypot(a['x'][m] - A[3], a['z'][m] - A[4]).max() > PRES_LEAVE_M)
                if left or math.hypot(Bv[3] - A[3], Bv[4] - A[4]) > PRES_SAME_M: pres += 1
                else: joins += 1
        if len(st['naip_aircraft_years']) + pres < B.N_OBS_MIN: weak.append((s['id'], len(st['naip_aircraft_years']), pres))
    return weak, n, joins


def session_check_local(ST, L=None, T=None, polls=None):
    """round-3 re-check: check 9 tested only |starts - ends| <= 1 and a 30 m span per session, but the docs claimed that a
    session number never links an aircraft's visits across a departure. With the gitignored per-aircraft files (local
    only; None without them) this verifies, with own code, what the numbers do and do not join:
      - the committed stays / signal edges carry the same session numbers as the local file (same run);
      - each session holds one aircraft; in time order its consecutive events lie <= SESSION_R_M apart, the aircraft has
        no fix farther than VISIT_LEAVE_M from the earlier event and none off the ground in between (no departure that the
        recording shows), and its signal starts and ends alternate (no two starts or two ends in a row);
      - no two consecutive events of one aircraft that meet those conditions are in different sessions (no split);
      - the join statistics of hwd_parked_stays.json summary.session_joins are recounted: signal end -> next start joins,
        how many have no fix in between and bridge more than JOIN_BLIND_S of recorder outage (poll gaps > OUTAGE_S), and
        the outages themselves.
    A departure and return hidden by an outage (or by the aircraft's own signal gap) is joined; this is counted, not
    excluded. Returns (failures, recount) or None."""
    import pickle
    sys.path.insert(0, os.path.join(HERE, 'adsb')); import parked_stays as PS
    if L is None:
        lf = os.path.join(HWD, 'refs', 'cache', 'local', 'adsb', 'hwd_parked_stays_local.json')
        tf = os.path.join(HWD, 'refs', 'cache', 'local', 'adsb', 'hwd_tracks.pkl')
        if not (os.path.exists(lf) and os.path.exists(tf)): return None
        L = json.load(open(lf)); P_ = pickle.load(open(tf, 'rb')); T = P_['tracks']; polls = np.asarray(P_['polls'], float)
    need = {s['_hex'] for s in L['stays']} | {e['_hex'] for e in L['signal_edges']}
    if any('gk' not in T[h] for h in need):   # 'off the ground' = not ground by kinematics (tools/adsb/derive.py, as parked_stays)
        import derive as DV
        cal = DV.calibrate(T)
        for h in sorted(need):
            if 'gk' not in T[h]: T[h]['hex'] = h; DV.derive(T[h], cal)
    ev = [(s['session'], s['_hex'], s['_t0'], s['_t1'], 'stay', s['x'], s['z']) for s in L['stays']] + \
         [(e['session'], e['_hex'], e['_t'], e['_t'], e['kind'], e['x'], e['z']) for e in L['signal_edges']]
    bad = []
    loc = Counter((round(e[5], 2), round(e[6], 2), e[0], 'stay' if e[4] == 'stay' else e[4]) for e in ev)
    com = Counter([(s['x'], s['z'], s['session'], 'stay') for s in ST['stays']] + [(e['x'], e['z'], e['session'], e['kind']) for e in ST['signal_edges']])
    if loc != com: bad.append(('committed vs local session numbers differ', sum((loc - com).values()), sum((com - loc).values())))
    def linked(a, A, B_):
        if math.hypot(A[5] - B_[5], A[6] - B_[6]) > PS.SESSION_R_M: return False
        m = (a['t'] > A[3]) & (a['t'] < B_[2])
        return not (m.any() and (np.hypot(a['x'][m] - A[5], a['z'][m] - A[6]).max() > PS.VISIT_LEAVE_M or (~a['gk'][m]).any()))
    by = {}
    for e in ev: by.setdefault(e[0], []).append(e)
    pc = joins = blind = nofix = 0; multi_ac = notlinked = consec = 0
    for k, v in by.items():
        v.sort(key=lambda e: (e[2], e[3]))
        if len({e[1] for e in v}) > 1: multi_ac += 1; continue
        a = T[v[0][1]]; has = False
        kinds = [e[4] for e in v if e[4] != 'stay']
        if any(x == y for x, y in zip(kinds, kinds[1:])): consec += 1
        for A, B_ in zip(v, v[1:]):
            if not linked(a, A, B_): notlinked += 1
            if A[4] == 'end' and B_[4] == 'start':
                joins += 1; has = True
                m = (a['t'] > A[3]) & (a['t'] < B_[2])
                i0 = np.searchsorted(polls, A[3]); i1 = np.searchsorted(polls, B_[2])
                pp = np.concatenate([[A[3]], polls[i0:i1], [B_[2]]]); dd = np.diff(pp)
                nofix += not m.any()
                if not m.any() and dd[dd > PS.OUTAGE_S].sum() > PS.JOIN_BLIND_S: blind += 1
        pc += has
    split = 0
    byac = {}
    for e in ev: byac.setdefault(e[1], []).append(e)
    for hx, v in byac.items():
        v.sort(key=lambda e: (e[2], e[3]))
        for A, B_ in zip(v, v[1:]):
            if A[0] != B_[0] and linked(T[hx], A, B_): split += 1
    if multi_ac: bad.append(('sessions holding more than one aircraft', multi_ac))
    if notlinked: bad.append(('consecutive events of a session not linked by the rule (> %.0f m apart, or a fix > %.0f m away / airborne in between)' % (PS.SESSION_R_M, PS.VISIT_LEAVE_M), notlinked))
    if consec: bad.append(('sessions with two signal starts or two ends in a row', consec))
    if split: bad.append(('consecutive events of one aircraft linked by the rule but in different sessions', split))
    dp = np.diff(polls); out = dp[dp > PS.OUTAGE_S]
    rec = {'sessions': len(by), 'sessions_with_power_cycle': pc, 'power_cycle_joins': joins, 'power_cycle_joins_without_fix_between': nofix,
           'power_cycle_joins_without_fix_bridging_outage_over_%dh' % round(PS.JOIN_BLIND_S / 3600): blind,
           'recording_span_h': round(float(polls[-1] - polls[0]) / 3600, 1),
           'recorder_outages_over_%ds' % PS.OUTAGE_S: {'n': int(len(out)), 'total_h': round(float(out.sum()) / 3600, 1)}}
    sj = ST['summary'].get('session_joins') or {}
    diff = {k: (v, sj.get(k)) for k, v in rec.items() if k != 'sessions' and sj.get(k) != v}
    if diff: bad.append(('summary.session_joins differs from the recount', diff))
    return bad, rec


def main():
    data = sys.argv[sys.argv.index('--data') + 1] if '--data' in sys.argv else os.path.join(HWD, 'data', 'hwd_airport.json')
    D = json.load(open(data))
    if '--paint-only' in sys.argv:      # check 3's paint part alone, e.g. against an older build (--data)
        FE = json.load(open(os.path.join(HWD, 'refs', 'cache', 'osm', 'khwd_features.json')))['features']
        h = paint_check(D, FE) + topology_check(D, FE); say('RESULT (paint only): %s' % ('passed' if not h else 'FAILED: ' + '; '.join(h))); return 1 if h else 0
    NASR = json.load(open(os.path.join(HWD, 'refs', 'cache', 'faa', 'nasr_2026-10-29_HWD.json')))['tables']
    CS = json.load(open(os.path.join(HWD, 'refs', 'cache', 'faa', 'chart_supplement_HWD.json')))
    FE = json.load(open(os.path.join(HWD, 'refs', 'cache', 'osm', 'khwd_features.json')))['features']
    hard = []
    say('check_airport: data/hwd_airport.json (%d B), frame %s' % (os.path.getsize(os.path.join(HWD, 'data', 'hwd_airport.json')), D['frame']['id']))

    # ------------------------------------------------------------------------------------------- 1. runways vs NASR
    say('\n1. Runways vs FAA NASR (cycle 2026-10-29), recomputed from the NASR rows')
    ends = {r['RWY_END_ID']: r for r in NASR['APT_RWY_END.csv']}; rwys = {r['RWY_ID']: r for r in NASR['APT_RWY.csv']}
    worst = 0.0; nfield = 0; bad = []
    for R in D['runways']:
        nr = rwys[R['id']]
        for k, v in (('length_ft_nasr', int(nr['RWY_LEN'])), ('width_ft', int(nr['RWY_WIDTH'])), ('surface', nr['SURFACE_TYPE_CODE'])):
            nfield += 1
            if R[k] != v: bad.append('%s %s %r != NASR %r' % (R['id'], k, R[k], v))
        nfield += 1
        if R['edge_lights']['type'] != ('MIRL' if nr['RWY_LGT_CODE'] == 'MED' else nr['RWY_LGT_CODE']): bad.append('%s lights' % R['id'])
        for E in R['ends']:
            ne = ends[E['id']]; lat, lon = float(ne['LAT_DECIMAL']), float(ne['LONG_DECIMAL'])
            x, z = F.ll_to_world(lat, lon); d = math.hypot(x - E['x'], z - E['z']); worst = max(worst, d)
            checks = [('lat', E['lat'], lat), ('lon', E['lon'], lon), ('elev_ft', E['elev_ft'], float(ne['RWY_END_ELEV'])),
                      ('y', E['y'], round(float(ne['RWY_END_ELEV']) * FT, 2)), ('marking', E['marking']['type'], ne['RWY_MARKING_TYPE_CODE']),
                      ('vgsi', E['vgsi']['code'], ne['VGSI_CODE']), ('gpa', E['vgsi']['glide_deg'], float(ne['VISUAL_GLIDE_PATH_ANGLE'])),
                      ('tch', E['vgsi']['tch_ft'], int(ne['THR_CROSSING_HGT'])), ('reil', E['reil']['present'], ne.get('RWY_END_LGTS_FLAG') == 'Y'),
                      ('tdz', E['tdz_elev_ft'], float(ne['TDZ_ELEV'])), ('true_aln', E['true_alignment_deg'], int(ne['TRUE_ALIGNMENT']))]
            if ne.get('DISPLACED_THR_LEN'):
                T = E['displaced_threshold']; tx, tz = F.ll_to_world(float(ne['LAT_DISPLACED_THR_DECIMAL']), float(ne['LONG_DISPLACED_THR_DECIMAL']))
                worst = max(worst, math.hypot(tx - T['x'], tz - T['z']))
                checks += [('disp_len', T['len_ft_nasr'], int(ne['DISPLACED_THR_LEN'])), ('thr_elev', T['elev_ft'], float(ne['DISPLACED_THR_ELEV']))]
            else:
                checks.append(('no displaced thr', E['displaced_threshold'], None))
            side = 'right' if E['id'] in CS['derived']['right_traffic'] else 'left'
            checks += [('traffic (CS)', E['traffic_pattern']['side'], side), ('TPA (CS)', E['tpa_ft_msl'], CS['derived']['tpa_ft_msl'][R['id']])]
            if ne.get('RIGHT_HAND_TRAFFIC_PAT_FLAG'):
                checks.append(('traffic (NASR flag)', E['traffic_pattern']['side'], 'right' if ne['RIGHT_HAND_TRAFFIC_PAT_FLAG'] == 'Y' else 'left'))
            for nm, a, b in checks:
                nfield += 1
                if a != b: bad.append('%s %s: file %r, source %r' % (E['id'], nm, a, b))
        # length
        a_, b_ = R['ends'][0], R['ends'][1]; L = math.hypot(b_['x'] - a_['x'], b_['z'] - a_['z'])
        say('   %s: plane length %.2f m vs NASR %d ft = %.2f m (%+.2f m); width %s ft' % (R['id'], L, R['length_ft_nasr'], R['length_ft_nasr'] * FT, L - R['length_ft_nasr'] * FT, R['width_ft']))
    say('   %d fields compared, %d mismatches; worst end / threshold position difference %.4f m (data rounded to 0.01 m)' % (nfield, len(bad), worst))
    for b in bad: say('   MISMATCH ' + b)
    if bad or worst > 0.0051: hard.append('runway fields vs NASR')

    # ------------------------------------------------------------------------------------------- 2. runway pavement vs NAIP
    say('\n2. Runway pavement: NASR rectangle vs NAIP painted edges (AC 150/5340-1M para 2.8)')
    for R in D['runways']:
        a, b = R['id'].split('/'); A = F.rwy_axis(a); W = R['width_ft'] * FT / 2
        o = np.array(A['origin']); d = np.array(A['dir']); rt = np.array(A['right'])
        rect = [o - rt * W, o + rt * W, o + d * A['length'] + rt * W, o + d * A['length'] - rt * W]
        dmax = max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(rect, R['outline']['ring']))
        if dmax > 0.0071: hard.append('%s outline' % R['id'])     # 0.01 m rounding of x and z
        say('   %s outline = NASR rectangle: max vertex difference %.4f m' % (R['id'], dmax))
    for y in ('2024', '2022'):
        N = Naip(y)
        for R in D['runways']:
            m = rwy_edges.measure(N, R['id'])
            for side in ('left', 'right'):
                s = m[side]
                ok = s and abs(s['median_m']) <= EDGE_TOL
                say('   NAIP %s %s %-5s edge (side of %s->%s): residual median %+.3f m, MAD %.3f, p10..p90 %+.2f..%+.2f m, %d/%d stations %s' % (
                    y, R['id'], side, R['id'][:3], R['id'][-3:], s['median_m'], s['mad_m'], s['p10_m'], s['p90_m'], s['n_clean'], m['stations'], 'ok' if ok else 'FAIL'))
                if not ok: hard.append('NAIP edge %s %s %s' % (y, R['id'], side))
            say('   NAIP %s %s painted width %.3f m vs NASR %.3f m; centre offset %+.3f m' % (y, R['id'], m['width_naip_m'], m['nasr_width_m'], m['centre_offset_right_m']))

    # ------------------------------------------------------------------------------------------- 3. taxiway refs
    say('\n3. Taxiway designations vs AL-5015 2611 (labels read from the PDF text layer), and NAIP paint per way')
    W_ = al5015.words(); M_, _ = al5015.affine()
    ways = [w for w in D['taxiways'] if w['status'] == 'open']
    lab = []
    osm_refs = {w['ref'] for w in D['taxiways'] if w['ref']}; other = []
    for w in W_:
        if not re.fullmatch(r'[A-Z][0-9]?', w[0]): continue
        x, z = al5015.px_to_world(M_, (w[1] + w[3]) / 2 * al5015.K, (w[2] + w[4]) / 2 * al5015.K)[0]
        dall = min(LineString(v['pts']).distance(Point(x, z)) for v in ways)
        if w[0] not in osm_refs:
            other.append((w[0], round(dall, 1)))
            if dall <= LABEL_ON_M: lab.append((w[0], float(x), float(z), None))
            continue
        if dall > LABEL_FAR: say('   AL-5015 glyph %r at pdf %.0f,%.0f is %.0f m from every OSM way: not a taxiway label (legend / notes)' % (w[0], w[1], w[2], dall)); continue
        same = [LineString(v['pts']).distance(Point(x, z)) for v in ways if v['ref'] == w[0]]
        lab.append((w[0], float(x), float(z), min(same) if same else None))
    say('   other single-letter glyphs (not OSM refs) and their distance to the nearest open taxiway centreline (m): %s; a taxiway label OSM lacks would lie within %.0f m' % (sorted(other), LABEL_ON_M))
    bad_l = [l for l in lab if l[3] is None or l[3] > LABEL_TOL]
    say('   %d taxiway label glyphs on the diagram; distance to the nearest OSM way with the same ref: %s m; beyond %.0f m: %s' % (
        len(lab), ', '.join('%s %.1f' % (l[0], l[3]) for l in sorted(lab, key=lambda l: l[0]) if l[3] is not None), LABEL_TOL, bad_l or 'none'))
    al = sorted({l[0] for l in lab}); osm = sorted({w['ref'] for w in D['taxiways'] if w['ref']})
    say('   refs on the diagram %s; OSM refs %s; missing in OSM %s; OSM only %s' % (al, osm, sorted(set(al) - set(osm)), sorted(set(osm) - set(al))))
    if osm != al or bad_l: hard.append('taxiway refs vs AL-5015 labels')
    if al != sorted(D['checks_at_build']['taxiway_refs_al5015']): say('   NOTE: the build list taxiway_refs_al5015 %s differs from the PDF labels' % D['checks_at_build']['taxiway_refs_al5015'])
    inf_refs = [(w['id'], w['ref'], w.get('ref_note', '')[:90]) for w in D['taxiways'] if w.get('ref_src') == 'inf']
    say('   ways whose OSM ref the diagram does not support along the way (ref_src inf, read by eye): %d' % len(inf_refs))
    for t in inf_refs: say('      %s %s: %s...' % t)
    for ref, ft in (('A1', 100), ('Z1', 94)):
        ws = [w for w in D['taxiways'] if w['ref'] == ref]; ok = all(w.get('max_wingspan_ft') == ft for w in ws)
        say('   %s: %d way(s), wingspan limit %s ft on all: %s' % (ref, len(ws), ft, ok))
        if not ok or not ws: hard.append('wingspan limit %s' % ref)
    tl = [w for w in D['taxilanes'] if w['ref']]
    say('   taxilanes with a ref: %d (AL-5015 names none)' % len(tl))
    sn = [w for w in D['taxiways'] + D['taxilanes'] if w['evidence']['naip_paint'].get('snapped_len_m')]
    say('   NAIP paint snapping: %d of %d ways moved (%.0f m), largest shift %.2f m: %s' % (len(sn), len(D['taxiways']) + len(D['taxilanes']), sum(w['evidence']['naip_paint']['snapped_len_m'] for w in sn),
                                                                                       max([w['evidence']['naip_paint']['max_shift_m'] for w in sn] or [0]),
                                                                                       ', '.join('%s %s (trigger: %s)' % (w['id'], w['ref'] or '-', ' + '.join((w['evidence']['naip_paint']['faint'].get('fit') or {}).get('trigger', ['?']))) for w in sn)))
    hard += paint_check(D, FE)
    hard += topology_check(D, FE)
    onr = [(w['id'], w['ref'], w['on_runway']['len_m']) for w in D['taxiways'] if w.get('on_runway', {}).get('runway_overlap')]
    say('   taxiway ways with > 50 m inside a NASR runway rectangle (on_runway.runway_overlap): %d %s' % (len(onr), onr))
    # widths (round-1 re-check: obs widths with IQRs of 11-22 m, and values from 1-4 stations under a note saying null)
    wd = [w['width'] for w in D['taxiways'] + D['taxilanes'] if w['status'] == 'open']
    w_obs = [x for x in wd if x.get('naip_src') == 'obs']; w_inf = [x for x in wd if x.get('naip_src') == 'inf']
    w_bad = [x for x in wd if (x.get('naip_src') == 'obs' and (x['naip_stations'] < B.WIDTH_N_MIN or x['naip_grey_iqr_m'] > B.WIDTH_IQR_MAX)) or
             (x['naip_stations'] < B.WIDTH_N_MIN and x.get('naip_grey_width_m') is not None) or (x.get('naip_src') == 'inf' and not x.get('naip_reason'))]
    say('   widths: NAIP grey width obs (>= %d stations, IQR <= %.1f m) on %d of %d open ways (median %s m, IQR %s m); inf with a reason (IQR larger) on %d; no value (< %d stations) on %d; the AC default [inf] is on all. Rule violations: %d' % (
        B.WIDTH_N_MIN, B.WIDTH_IQR_MAX, len(w_obs), len(wd), r1(np.median([x['naip_grey_width_m'] for x in w_obs])) if w_obs else None,
        [x['naip_grey_iqr_m'] for x in w_obs], len(w_inf), B.WIDTH_N_MIN, sum(1 for x in wd if x['naip_grey_width_m'] is None), len(w_bad)))
    if w_bad: hard.append('taxiway width src')

    # ------------------------------------------------------------------------------------------- 4/5. spots on pavement, not in buildings
    say('\n4./5. Parking spots on pavement, not in buildings')
    P = D['parking']
    aprons = prep(unary_union([Polygon(a['ring']).buffer(0) for a in D['aprons']]))
    lanes = prep(unary_union([LineString(w['pts']).buffer(PAVE_TWY) for w in D['taxiways'] + D['taxilanes'] if w['status'] == 'open']))
    blds = [(h['id'], Polygon(h['ring']).buffer(0)) for h in D['hangars']] + [(b['id'], Polygon(b['ring']).buffer(0)) for b in D['buildings'] if b.get('ring')]
    N24 = Naip('2024')
    how = Counter(); off = []; inb = []
    for s in P:
        pt = Point(s['x'], s['z'])
        if aprons.contains(pt): how['OSM apron'] += 1
        elif lanes.contains(pt): how['OSM taxiway/taxilane +-%.1f m' % PAVE_TWY] += 1
        else:
            a = np.linspace(-2, 2, 9); X, Z = np.meshgrid(a + s['x'], a + s['z']); m = np.hypot(X - s['x'], Z - s['z']) <= 2.0
            R_, G_, B_ = (N24.sample(X[m], Z[m], k) for k in 'RGB')
            mx = np.maximum(np.maximum(R_, G_), B_); mn = np.minimum(np.minimum(R_, G_), B_)
            sat = float(np.median((mx - mn) / np.maximum(mx, 1))); eg = float(np.median(G_ - (R_ + B_) / 2))
            if sat < SAT_MAX and eg < EG_MAX: how['NAIP 2024 grey only'] += 1; off.append((s['id'], s['kind'], round(sat, 3), round(eg, 1), 'pass'))
            else: how['NOT on pavement'] += 1; off.append((s['id'], s['kind'], round(sat, 3), round(eg, 1), 'FAIL'))
        for bid, pg in blds:
            if pg.contains(pt): inb.append((s['id'], bid))
    say('   %d spots: %s' % (len(P), dict(how)))
    for o in off: say('   off OSM pavement: %s %s NAIP saturation %.3f, excess green %.1f -> %s' % o)
    say('   spots inside a building footprint: %d %s' % (len(inb), inb))
    if inb: hard.append('spot in building')
    if any(o[4] == 'FAIL' for o in off): hard.append('spot off pavement')

    # ------------------------------------------------------------------------------------------- 6. spacing vs size
    say('\n6. Spot spacing vs size class (FAA AC 150/5300-13B Chg 1)')
    pdf = os.path.join(HWD, 'refs', 'cache', 'faa', 'ac150_5300_13b_chg1_p136_181_284-288.pdf')
    txt = re.sub(r'\s+', ' ', subprocess.run(['pdftotext', '-layout', pdf, '-'], check=True, capture_output=True, text=True).stdout)
    for where, q in AC_QUOTES:
        found = re.sub(r'\s+', ' ', q) in txt
        say('   quote %s "%s": %s' % (where, q, 'found in the official text' if found else 'NOT FOUND'))
        if not found: hard.append('AC quote')
    W = [s for s in P if s['kind'] != 'helipad']; H = [s for s in P if s['kind'] == 'helipad']
    heli_def = min(s['size']['max_rotor_m'] for s in H if s['size'].get('max_rotor_m'))
    gat = json.load(open(os.path.join(HWD, 'data', 'ga_types.json')))['types']
    def tspan(t):
        g = gat.get(t) or {}; v = [x for x in (g.get('wingspan_m'), g.get('wingspan_winglets_m')) if x]
        return max(v) if v else None
    def types_of(ev):
        out = Counter()
        for k in ('types',): out.update({t: n for t, n in (ev.get(k) or {}).items() if t != '?'})
        for k in ('adsb', 'adsb_signal_edges'):
            for a in ev.get(k, []): out.update({t: n for t, n in (a.get('types') or {}).items() if t != '?'})
        for m in ev.get('merged_duplicates', []): out.update(types_of(m['evidence']))
        return out
    c172 = gat['C172']['length_m'] / tspan('C172')
    def ratio(s):
        """fuselage length / span of the widest observed type with both in the FAA ACD, else the C172's (recounted here
        from the evidence, not read from the spot's planform field)"""
        best = None
        for t in sorted(types_of(s['evidence'])):
            sp_ = tspan(t); ln = (gat.get(t) or {}).get('length_m')
            if sp_ and ln and (best is None or sp_ > best[0]): best = (sp_, ln / sp_)
        return best[1] if best else c172
    RAT = {s['id']: ratio(s) for s in W}
    rat_bad = [(s['id'], round(RAT[s['id']], 2), s['size'].get('planform', {}).get('length_per_span')) for s in W if round(RAT[s['id']], 2) != s['size'].get('planform', {}).get('length_per_span')]
    say('   sizing planform (round-1 re-check: the wing alone left out the fuselage): wing segment across the heading + fuselage of span x length/span (FAA ACD of the widest observed type, else C172 %.3f) along it, %.0f %% ahead of the reference point; without a heading a disc of radius span x max(1/2, (1 - that share) x length/span), which holds the planform in every heading. Recounted length/span agrees with every spot\'s planform field: %s' % (
        c172, 100 * B.FUS_FWD_FRAC, 'yes' if not rat_bad else 'NO %s' % rat_bad[:6]))
    if rat_bad: hard.append('planform length/span')

    def shape(s, key='max_span_m', nose=True):
        if s['kind'] == 'helipad': return Point(s['x'], s['z']).buffer((s['size'].get('max_rotor_m') or heli_def) / 2, 32)
        sp = max(s['size'][key], 0.005); r = RAT[s['id']]
        if s['heading'] is None:      # the spot's recorded disc (round 2: radius / span in size.planform.disc_radius_per_span;
            return Point(s['x'], s['z']).buffer(sp * disc_k(s), 64)   # builds before round 2: diameter span x max(1, ratio))
        return headed(s['x'], s['z'], s['heading'], sp, r, nose)
    def disc_k(s):
        k = s['size'].get('planform', {}).get('disc_radius_per_span')
        return k if k is not None else max(1.0, RAT[s['id']]) / 2
    def headed(x, z, hdg, sp, r, nose=True):
        h = math.radians(hdg); u = np.array([math.cos(h), math.sin(h)]); f = np.array([math.sin(h), -math.cos(h)]); c = np.array([x, z])
        L = r * sp
        return unary_union([LineString([tuple(c - u * sp / 2), tuple(c + u * sp / 2)]),
                            LineString([tuple(c + f * (L * B.FUS_FWD_FRAC if nose else 0.0)), tuple(c - f * L * (1 - B.FUS_FWD_FRAC))])])
    # round-2 re-check: the heading-less disc (span x max(1, ratio) across) left the tail of the build's own planform
    # outside. Hard: for every spot without a heading, the disc holds the wing + fuselage planform at every heading (5 deg steps)
    nh_bad = []
    for s in W:
        if s['heading'] is not None: continue
        for key in ('max_span_m', 'capacity_span_m'):
            sp = s['size'][key]
            if sp <= 0.01: continue
            dsc = shape(s, key).buffer(0.005)
            if not all(dsc.contains(headed(s['x'], s['z'], hd, sp, RAT[s['id']])) for hd in range(0, 360, 5)): nh_bad.append((s['id'], key))
    say('   spots without a heading: %d; their recorded disc (size.planform.disc_radius_per_span) holds the wing + fuselage planform at every heading (5 deg steps) at both sizes: %s' % (
        sum(1 for s in W if s['heading'] is None), 'yes' if not nh_bad else 'NO %s' % nh_bad[:8]))
    if nh_bad: hard.append('heading-less disc does not hold the planform')
    # door spots: the only spots whose own hangar may be entered (by the nose); verified here from the geometry
    door_bad = []
    for s in W:
        if not s.get('door_spot'): continue
        pg = dict(blds)[s['hangar']]; pt = Point(s['x'], s['z']); q = pg.exterior.interpolate(pg.exterior.project(pt))
        hd = math.degrees(math.atan2(q.x - s['x'], -(q.y - s['z']))) % 360
        if pg.exterior.distance(pt) > B.HGR_DOOR_M + 0.05 or abs((hd - s['heading'] + 180) % 360 - 180) > 2.0 or s['kind'] != 'hangar_apron':
            door_bad.append((s['id'], round(pg.exterior.distance(pt), 1), round(hd, 1), s['heading']))
    say('   door spots (an aircraft at its hangar door: ADS-B <= %.0f m from the wall, nose in): %d %s; each within %.0f m of its hangar wall and heading to the nearest wall point: %s' % (
        B.HGR_DOOR_M, sum(1 for s in W if s.get('door_spot')), [s['id'] for s in W if s.get('door_spot')], B.HGR_DOOR_M, 'yes' if not door_bad else 'NO %s' % door_bad))
    if door_bad: hard.append('door spot geometry')
    WH = W + H; pos = np.array([[s['x'], s['z']] for s in WH])
    for key, clear, name in (('max_span_m', WINGTIP, 'AC design size (10 ft)'), ('capacity_span_m', B.CAP_GAP, 'capacity size (%.1f m gap)' % B.CAP_GAP)):
        viol = []; mins = []
        for i in range(len(WH)):
            d = np.hypot(*(pos - pos[i]).T)
            for j in np.nonzero((d < 45) & (np.arange(len(WH)) > i))[0]:
                if WH[i]['kind'] == 'helipad' and WH[j]['kind'] == 'helipad': continue      # pads are fixed, mapped geometry
                if key == 'max_span_m' and any(any(f.startswith('no_design_size') for f in WH[k_]['size'].get('flags', [])) for k_ in (i, j)): continue   # listed below
                c = shape(WH[i], key).distance(shape(WH[j], key)); mins.append((c, WH[i]['id'], WH[j]['id']))
                if c < clear - 0.006: viol.append((WH[i]['id'], WH[j]['id'], round(c, 3)))   # 0.006: sizes are floored to 0.01 m
        mn = min(mins)
        say('   %s: %d spot pairs within 45 m (planforms; helipad spots as discs of their rotor size, unknown = %.1f m, the smallest OSM pad); min clearance %.3f m (%s / %s; required %.3f m); violations %d %s' % (
            name, len(mins), heli_def, mn[0], mn[1], mn[2], clear, len(viol), viol[:10]))
        if viol: hard.append('spacing (%s)' % name)
        if key == 'max_span_m':
            nd_ = [(s_['id'], s_['size'].get('limited_by')) for s_ in W if any(f.startswith('no_design_size') for f in s_['size'].get('flags', []))]
            say('   spots with no AC design size (flag no_design_size: not even a point keeps 10 ft from a higher-priority spot / building; left out of the design-size pair test above, kept in the capacity test): %d %s' % (len(nd_), nd_))
            if any(s_['size']['max_span_m'] > 0 for s_ in W if any(f.startswith('no_design_size') for f in s_['size'].get('flags', []))): hard.append('no_design_size flag')
        bv = []
        for s in W:
            for bid, pg in blds:
                if pg.distance(Point(s['x'], s['z'])) > 45: continue
                own_door = bool(s.get('door_spot') and bid == s.get('hangar'))
                c = shape(s, key, nose=not own_door).distance(pg); need = B.CAP_GAP if own_door else clear
                if c < need - 0.006: bv.append((s['id'], bid, round(c, 2)))
        say('   %s: planform vs every building / hangar outline, the spot\'s own hangar included (door spots: without the nose, %.1f m): violations %d %s' % (name, B.CAP_GAP, len(bv), bv[:8]))
        if bv: hard.append('spot shape in building clearance (%s)' % name)
    say('   (consistency checks: the build sizes the spots with this rule; they show the sizes, the helipads and the buildings agree)')
    sz = Counter(s['size'].get('adg') for s in W)
    say('   AC design size classes (ADG of max_span_m): %s; tie-down max span p10/p50/p90 %s m; capacity p10/p50/p90 %s m' % (
        dict(sz), [round(float(v), 2) for v in np.percentile([s['size']['max_span_m'] for s in W if s['kind'] == 'tiedown'], [10, 50, 90])],
        [round(float(v), 2) for v in np.percentile([s['size']['capacity_span_m'] for s in W if s['kind'] == 'tiedown'], [10, 50, 90])]))
    # duplicates (independent of the sizing)
    R_ = [s for s in W if s['kind'] in ('ramp', 'hangar_apron')]; dup = []
    for i in range(len(R_)):
        for j in range(i + 1, len(R_)):
            d = math.hypot(R_[i]['x'] - R_[j]['x'], R_[i]['z'] - R_[j]['z'])
            if d < B.DUP_M: dup.append((R_[i]['id'], R_[j]['id'], round(d, 1)))
    say('   duplicates: ramp / hangar-apron spot pairs closer than %.1f m (one aircraft seen twice): %d %s' % (B.DUP_M, len(dup), dup))
    if dup: hard.append('duplicate spots')
    # observed types recounted from every adsb.lol type in the evidence
    tight_d = []; tight_c = []; flag_bad = []
    for s in W:
        sp = [tspan(t) for t in types_of(s['evidence'])]; sp = [x for x in sp if x]
        o = max(sp) if sp else None
        if o and o > s['size']['max_span_m'] + 0.01: tight_d.append((s['id'], s['zone'], s['size']['max_span_m'], round(o, 2)))
        if o and o > s['size']['capacity_span_m'] + 0.01: tight_c.append((s['id'], s['zone'], s['size']['capacity_span_m'], round(o, 2)))
        fl = s['size'].get('flags', [])
        if bool(o and o > s['size']['max_span_m'] + 0.01) != ('observed_type_wider_than_design' in fl) or (round(o, 2) if o else None) != s['size'].get('observed_max_span_m'):
            flag_bad.append(s['id'])
    say('   finding (not a failure): %d spots where adsb.lol saw a type wider than the AC design size (types recounted from every stay, signal start / end and merged duplicate in the evidence); %d also wider than the capacity size:' % (len(tight_d), len(tight_c)))
    for t in tight_c: say('      %s %s: capacity %.2f m, observed %.2f m' % t)
    say('   the spots\' own observed_max_span_m / flags agree with this recount: %s' % ('yes' if not flag_bad else 'NO %s' % flag_bad))
    if flag_bad: hard.append('observed-type flags')
    td = [s for s in W if s['kind'] == 'tiedown']
    if td:
        pit = sorted({s['evidence']['row_pitch_m'] for s in td})
        say('   tie-down rows: pitch %s m -> AC design span <= pitch - 10 ft = %s m; capacity (1.0 m gap) %s m; a C172 (FAA ACD 36.1 ft = 11.00 m) parked in such a row leaves %s m wingtip clearance' % (
            pit, [round(p - WINGTIP, 2) for p in pit], [round(p - B.CAP_GAP, 2) for p in pit], [round(p - 11.003, 2) for p in pit]))
    fl_all = Counter(f.split(' (')[0] for s in W for f in s['size'].get('flags', []))
    say('   size flags: %s' % dict(fl_all))
    # independent observations (round-1 re-check: a stay and its own signal start / end were counted as 2-3)
    ST = json.load(open(os.path.join(HWD, 'refs', 'cache', 'adsb', 'hwd_parked_stays.json')))
    ev_all = [(e['x'], e['z'], e['session']) for e in ST['stays'] + ST['signal_edges']]
    obs_bad = []; weak = []
    for s in R_:
        st = s['strength']
        if s['ref_point'] == 'rule_point': continue
        n_ = len(st['naip_aircraft_years']) + st.get('adsb_sessions', 0)     # (missing in builds before round 1)
        if n_ != st['n_observations'] or s['src'] != ('obs' if n_ >= B.N_OBS_MIN else 'inf'): obs_bad.append(s['id'])
        if s['src'] == 'obs':   # recount: sessions of committed stays / signal edges within 8 m (a wide type: half its span + 2 m,
            # as build_airport.BIG_SPAN) of the spot or of a merged duplicate
            sp_ = [tspan(t) for t in types_of(s['evidence'])]; sp_ = max([x for x in sp_ if x] or [0.0])
            rr = max(B.MERGE_RAMP, sp_ / 2 + 2.0 if sp_ > B.BIG_SPAN else 0.0)
            pts = [(s['x'], s['z'])] + [(m['x'], m['z']) for m in s['evidence'].get('merged_duplicates', [])]
            ss_ = {k for x, z, k in ev_all if any(math.hypot(x - a, z - b) <= rr for a, b in pts)}
            if len(st['naip_aircraft_years']) + len(ss_) < B.N_OBS_MIN: weak.append((s['id'], st['naip_aircraft_years'], len(ss_), st.get('adsb_sessions')))
    ua = D.get('unspotted_aircraft') or []
    stale = [(u['x'], u['z'], s_['id']) for u in ua for s_ in P if math.hypot(s_['x'] - u['x'], s_['z'] - u['z']) < 5.0]
    say('   parked aircraft on NAIP 2024 without a spot (unspotted_aircraft, by eye): %d (%s); listed ones that now have a spot within 5 m: %d %s' % (
        len(ua), dict(Counter(u['where'] for u in ua)), len(stale), stale))
    if stale: hard.append('unspotted_aircraft list stale')
    cands, unm, badv, verd = omission_sweep(D, N24)
    say('   omission sweep (round-2 re-check; own code): NAIP 2024 aircraft-mask parts on OSM aprons (buildings cut out) more than %.1f m from every spot, listed unspotted aircraft and reviewed NAIP blob, >= %.0f m2: %d; by-eye verdicts (build_airport.SWEEP_REVIEW) %s; without a verdict: %d %s; verdicts that do not fit (spot not within %.0f m / no listed aircraft within 15 m): %d %s - hard' % (
        B.SWEEP_R, B.SWEEP_MIN_M2, len(cands), dict(verd), len(unm), unm[:12], B.DUP_M + B.SWEEP_R, len(badv), badv[:6]))
    if unm or badv: hard.append('omission sweep: NAIP aircraft-mask part without a verdict')
    acc, acc_bad = naip_accounting(D, N24)
    say('   NAIP 2024 aircraft accounting (round 3; the build\'s blob grouping, own matching): every aircraft blob (extent >= %.0f m) on an OSM apron is a spot (within %.0f m), a listed aircraft or a by-eye verdict; both by-eye centres of a two-aircraft blob have a spot or listed aircraft within %.0f m; split-blob spots lie on a by-eye centre: %s; failures: %d %s - hard' % (
        B.AC_EXT_MIN, B.MERGE_RAMP, B.TWO_MATCH_M, acc, len(acc_bad), acc_bad[:8]))
    if acc_bad: hard.append('NAIP aircraft not accounted for')
    ld = D.get('checks_at_build', {}).get('naip_aircraft_dropped_by_lane_rule')
    if ld is None:
        say('   NAIP aircraft dropped by the lane rule: not recorded in this build (round 3 adds the record)')
    else:
        nacc = [(c['x'], c['z']) for c in ld if c['accounted_by'] == 'NOT ACCOUNTED']
        say('   NAIP 2024 aircraft dropped by the lane rule (build record, %.0f m from an open OSM taxi line): %d; listed %d, by-eye verdict %d, not accounted %d %s - hard' % (
            B.LANE_M, len(ld), sum(c['accounted_by'].startswith('listed') for c in ld), sum(c['accounted_by'].startswith('by-eye') for c in ld), len(nacc), nacc))
        if nacc: hard.append('lane-dropped NAIP aircraft not accounted for')
    say('   ramp / hangar-apron src: n_observations = NAIP years with an aircraft + adsb.lol sessions, obs when >= %d: consistent on every spot: %s' % (B.N_OBS_MIN, 'yes' if not obs_bad else 'NO %s' % obs_bad))
    say('   independent recount (distinct sessions of the committed stays / signal edges within 8 m - for a type wider than %.0f m half its span + 2 m - of an obs spot or its merged duplicates, + NAIP years): obs spots below %d: %d %s - hard (round-1 re-check: HE623S150 was obs on one session)' % (B.BIG_SPAN, B.N_OBS_MIN, len(weak), weak))
    if obs_bad: hard.append('spot src vs independent observations')
    if weak: hard.append('obs spot on fewer than %d independent observations (recount)' % B.N_OBS_MIN)
    # presences recounted from the LOCAL per-aircraft files, without the session numbers (round-2 re-check: the recount
    # above reuses the session numbers, so it could not see that they split one aircraft's uninterrupted presence)
    pres = presence_recount(R_, types_of, tspan)
    if pres is None:
        say('   presence recount: SKIPPED (refs/cache/local/adsb/hwd_parked_stays_local.json or hwd_tracks.pkl not present: gitignored, local only)')
    else:
        weak2, n_spots, n_merge = pres
        say('   presence recount from the local per-aircraft files (own code, not the session numbers): one aircraft\'s events at an obs spot are one presence unless it has a fix > %.0f m from the earlier event in between or the two events are > %.0f m apart, however long the gap; %d obs spots, %d same-aircraft event pairs joined; obs spots below %d (NAIP years + presences): %d %s - hard (no identities printed)' % (
            PRES_LEAVE_M, PRES_SAME_M, n_spots, n_merge, B.N_OBS_MIN, len(weak2), weak2))
        if weak2: hard.append('obs spot on fewer than %d independent presences (local recount)' % B.N_OBS_MIN)
    # spot vs taxiway / taxilane centrelines
    twy = unary_union([LineString(w['pts']) for w in D['taxiways'] if w['status'] == 'open'])
    tln = unary_union([LineString(w['pts']) for w in D['taxilanes'] if w['status'] == 'open'])
    rows = Counter(); rule_bad = []; conn_bad = []; rev_bad = []; conn = []
    for s in W:
        g = shape(s, 'capacity_span_m'); dt, dl = g.distance(twy), g.distance(tln)
        inside = dt < B.TWY_OBJ_M or dl < B.TLN_OBJ_M
        rows[(s['src'], s['kind'], 'inside' if inside else 'clear')] += 1
        if s.get('ref_point') == 'rule_point':
            h = math.radians(s['heading']); u = np.array([math.cos(h), math.sin(h)]); f = np.array([math.sin(h), -math.cos(h)]); c = np.array([s['x'], s['z']])
            L = c172 * B.ADG_SPAN['I']
            ol = unary_union([LineString([tuple(c - u * B.ADG_SPAN['I'] / 2), tuple(c + u * B.ADG_SPAN['I'] / 2)]), LineString([tuple(c + f * L * B.FUS_FWD_FRAC), tuple(c - f * L * (1 - B.FUS_FWD_FRAC))])])
            if ol.distance(twy) < B.TWY_OBJ_M - 0.05 or ol.distance(tln) < B.TLN_OBJ_M - 0.05: rule_bad.append((s['id'], round(ol.distance(twy), 1), round(ol.distance(tln), 1)))
            pl = pave_path(s['x'], s['z'], FE); conn.append((s['id'], None if pl is None else round(pl)))
            if pl is None or pl > B.CONNECT_M * 1.06: conn_bad.append((s['id'], pl))
            rv = s['evidence'].get('review_by_eye', '')
            if not rv.startswith('ok') or rv != B.HGR_REVIEW.get(s.get('hangar')): rev_bad.append(s['id'])
    say('   spot planform (capacity size) vs open taxiway / taxilane centrelines, AC 150/5300-13B Table 4-1 ADG I object distance %.1f / %.1f m: %s' % (
        B.TWY_OBJ_M, B.TLN_OBJ_M, ', '.join('%s %s %s: %d' % (k[0], k[1], k[2], v) for k, v in sorted(rows.items()))))
    say('   rule-made (inferred hangar-apron) spots whose ADG I planform is inside that distance: %d %s' % (len(rule_bad), rule_bad))
    say('   rule-made spots: shortest path over OSM pavement around buildings to an open taxiway / taxilane (8-neighbour Dijkstra on a 1 m grid; build limit %.0f m, +6 %% for the two grid metrics): %s; beyond: %d %s' % (B.CONNECT_M, conn, len(conn_bad), conn_bad))
    say('   rule-made spots with an "ok" by-eye review entry (build_airport.HGR_REVIEW): %d of %d; missing / not ok: %s' % (len(conn) - len(rev_bad), len(conn), rev_bad))
    if rule_bad: hard.append('inferred spot vs taxiway clearance')
    if conn_bad: hard.append('inferred spot not connected to the taxi network')
    if rev_bad: hard.append('inferred spot without by-eye review')

    # ------------------------------------------------------------------------------------------- 7. hot spots
    say('\n7. Hot spots: OSM taxiways inside the AL-5015 ellipse vs the CS text')
    for hs in sorted({h['hs'] for h in D['hotspots']}):
        parts = [h for h in D['hotspots'] if h['hs'] == hs]; inside = sorted({r for h in parts for r in h['taxiways_inside_osm']})
        named = sorted(set(re.findall(r'Twy ([A-Z][0-9]?)', parts[0]['text'])))
        verdict = ('not checkable against the CS (its text names no taxiway)' if not named else
                   'consistent' if set(named) <= set(inside) else 'NOT consistent')
        say('   %-5s (%d ellipse%s) inside %s; CS text names %s -> %s' % (hs, len(parts), 's' if len(parts) > 1 else '', inside, named or '-', verdict))
        if named and not set(named) <= set(inside): hard.append('hot spot %s' % hs)
    say('   (a consistency check of the diagram registration and the OSM refs, not an independent survey)')

    # ------------------------------------------------------------------------------------------- 8. holds
    say('\n8. Holding positions')
    hb = [h for h in D['holds'] if h['bar']]
    say('   %d OSM holds, %d with a NAIP 2024 bar; |bar - OSM node| along the taxiway: max %.2f m, median %.2f m' % (len(D['holds']), len(hb), max(abs(h['bar']['offset_from_osm_m']) for h in hb), float(np.median([abs(h['bar']['offset_from_osm_m']) for h in hb]))))
    for rw in sorted({h['runway'] for h in D['holds']}):
        ds = sorted(h['cl_dist_ft'] for h in D['holds'] if h['runway'] == rw and h['dist_to_runway_m'] < 120)
        say('   %s: distance from the runway centreline (ft) %s' % (rw, ds))

    # ------------------------------------------------------------------------------------------- 9. hygiene
    say('\n9. Data hygiene')
    srcs = set(D['sources']); nel = 0; badel = []
    for k in ('runways', 'taxiways', 'taxilanes', 'aprons', 'holds', 'hotspots', 'helipads', 'hangars', 'buildings', 'markers', 'parking', 'al5015_labels', 'not_placed', 'unspotted_aircraft'):
        for e in D[k]:
            nel += 1
            if e.get('src') not in ('obs', 'inf') or not e.get('refs') or not set(e['refs']) <= srcs: badel.append((k, e.get('id') or e.get('what')))
    say('   %d elements; %d without a valid src / refs %s' % (nel, len(badel), badel[:5]))
    if badel: hard.append('src/refs')
    miss_ids = spot_id_refs(D)
    say('   spot ids named in the data text and in build_airport\'s by-eye records that are not spots of the data (round 3): %d %s - hard' % (len(miss_ids), miss_ids))
    if miss_ids: hard.append('spot id references')
    share = Counter(e['src'] for k in ('runways', 'taxiways', 'taxilanes', 'aprons', 'holds', 'hotspots', 'helipads', 'hangars', 'buildings', 'markers', 'parking') for e in D[k])
    say('   element src shares: %s' % dict(share))
    js = open(os.path.join(HWD, 'data', 'hwd_airport.js'), encoding='utf-8').read()
    body = js[js.index('export const HWD_AIRPORT = ') + len('export const HWD_AIRPORT = '):].rstrip().rstrip(';')
    same = json.loads(body) == D
    say('   .js twin carries the same object as the .json: %s' % same)
    if not same: hard.append('js twin')
    d1 = d1_scan()
    if d1: hard.append('D1')
    # session numbers (round 1) must not link an aircraft's separate presences: per session <= 1 signal start, <= 1 end, and
    # all its events within 2 x SESSION_R_M of each other
    import collections
    sys.path.insert(0, os.path.join(HERE, 'adsb'))
    ST = json.load(open(os.path.join(HWD, 'refs', 'cache', 'adsb', 'hwd_parked_stays.json'))); by = collections.defaultdict(list)
    for e in ST['stays']: by[e['session']].append(('stay', e['x'], e['z']))
    for e in ST['signal_edges']: by[e['session']].append((e['kind'], e['x'], e['z']))
    import parked_stays as PS
    # round 2: a session may now hold a parked aircraft's power cycles (end, start, end ...), so starts and ends alternate:
    # their counts differ by at most 1
    sbad = [k for k, v in by.items() if abs(sum(1 for t in v if t[0] == 'start') - sum(1 for t in v if t[0] == 'end')) > 1 or
            max(math.hypot(a[1] - b[1], a[2] - b[2]) for a in v for b in v) > 2 * PS.SESSION_R_M]
    # (round 3: the committed file has no time order, so it cannot tell a power cycle (end, start) from a start then an
    # end; it shows only sessions with both a start and an end, and those with more than one start or end)
    say('   session numbers in refs/cache/adsb/hwd_parked_stays.json (committed file, no time order): %d sessions; %d with both a signal start and an end, %d with more than one start or end; in each, starts and ends differ by <= 1 and all events lie within %.0f m: %s - hard (a necessary condition only: it cannot see time order)' % (
        len(by), sum(1 for v in by.values() if any(t[0] == 'start' for t in v) and any(t[0] == 'end' for t in v)),
        sum(1 for v in by.values() if sum(1 for t in v if t[0] == 'start') > 1 or sum(1 for t in v if t[0] == 'end') > 1),
        2 * PS.SESSION_R_M, 'yes' if not sbad else 'NO %s' % sbad[:10]))
    if sbad: hard.append('D1 session structure')
    sl = session_check_local(ST)
    if sl is None:
        say('   session numbers vs the local per-aircraft files: SKIPPED (refs/cache/local/adsb/ not present: gitignored, local only)')
    else:
        sl_bad, rec = sl
        say('   session numbers vs the local per-aircraft files (round 3; own code, no identity printed): one aircraft per session, consecutive events <= %.0f m apart with no fix > %.0f m away or airborne in between, starts / ends alternating in time, no split of a linked pair, committed = local numbers, summary.session_joins recounted: %s; recount %s - hard' % (
            PS.SESSION_R_M, PS.VISIT_LEAVE_M, 'yes' if not sl_bad else 'NO %s' % sl_bad, json.dumps(rec)))
        say('   what a session number does not show: a departure and return with no fix in between. %d of the %d signal end -> start joins have no fix of the aircraft in between, and %d of them bridge more than %.0f h of recorder outage (poll gaps > %.0f s: %d, %.1f h of the %.1f h recording)' % (
            rec['power_cycle_joins_without_fix_between'], rec['power_cycle_joins'], rec['power_cycle_joins_without_fix_bridging_outage_over_%dh' % round(PS.JOIN_BLIND_S / 3600)],
            PS.JOIN_BLIND_S / 3600, PS.OUTAGE_S, rec['recorder_outages_over_%ds' % PS.OUTAGE_S]['n'], rec['recorder_outages_over_%ds' % PS.OUTAGE_S]['total_h'], rec['recording_span_h']))
        if sl_bad: hard.append('session numbers vs local files')
    miss = sources_coverage()
    if miss: hard.append('SOURCES coverage / provenance')
    # src-like keys in every committed JSON: obs / inf (or null); field-documentation maps are skipped; data/ga_types.json
    # uses 'none' for types without an FAA ACD row (its src_legend) - listed, not a failure
    root = os.path.dirname(HWD); bad_src = []; doc_maps = ('src_legend', 'parking_fields', 'stay_fields', 'hold_fields', 'field_definitions', 'fields')
    for f in sorted(subprocess.run(['git', '-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', 'hwd3d'], capture_output=True, text=True, check=True).stdout.split()):
        if not f.endswith('.json'): continue
        vals = Counter()
        def walk(o, inside_doc=False):
            if isinstance(o, dict):
                for k, v in o.items():
                    if not inside_doc and (k == 'src' or k.endswith('_src')) and not isinstance(v, (dict, list)): vals[(k, v)] += 1
                    walk(v, inside_doc or k in doc_maps or k.endswith('_fields'))
            elif isinstance(o, list):
                for v in o: walk(v, inside_doc)
        walk(json.load(open(os.path.join(root, f))))
        b = {'%s=%r' % k: n for k, n in vals.items() if k[1] not in ('obs', 'inf', None)}
        if b: bad_src.append((os.path.relpath(os.path.join(root, f), HWD), b))
    say('   src / *_src values other than obs / inf / null in committed JSON (field-documentation maps skipped): %s' % (bad_src or 'none'))
    if any(f != 'data/ga_types.json' or set(b) != {"src='none'"} for f, b in bad_src): hard.append('src values')

    say('\nRESULT: %s' % ('ALL HARD CHECKS PASSED' if not hard else 'FAILED: ' + '; '.join(hard)))
    os.makedirs(os.path.join(HWD, 'out', 'phase1', 'g5'), exist_ok=True)
    open(os.path.join(HWD, 'out', 'phase1', 'g5', 'check_airport.txt'), 'w').write('\n'.join(OUT) + '\n')
    return 1 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
