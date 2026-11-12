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
     NAIP paint per way (since the Phase 1 review): the faint yellow centreline ridges are measured again along every
     open way's final geometry; a 50 m section whose ridges agree on an offset (build_airport.faint_sections:
     >= 8 ridges, |median| >= 1.0 m, IQR <= 0.6 m) fails - hard (a median over all ways can hide one offset way).
  4. Every parking spot centre on pavement: inside an OSM apron polygon, or within PAVE_TWY m of an OSM taxiway / taxilane
     centreline, or NAIP 2024 grey (median saturation < SAT_MAX and excess green < EG_MAX in a 2 m disc - a
     calibration read on this mosaic: asphalt / concrete aprons 0.04-0.14, grass 0.19-0.36). A spot passing only the
     NAIP test is reported.
  5. No spot centre inside a building footprint (OSM hangars, buildings, tower; point in polygon) - hard. Since the
     Phase 1 review also the wing shape: at max_span_m it keeps 10 ft from every building / hangar outline, at
     capacity_span_m CAP_GAP (a spot's own hangar excepted for hangar-apron spots) - hard, but a consistency check: the
     build sizes the spots so that this holds.
  6. Spot spacing against the size class: FAA AC 150/5300-13B Chg 1 Table 5-1 recommends a 10 ft (3 m) clearance for
     ADG I and II parking positions and Figure E-2 sets tiedown spacing to "Wingspan plus 10 ft (3 m) for critical
     aircraft" (Figure E-3: "10 ft (3 m) Minimum wing tip separation"); the quotes are asserted against the text of the
     committed extract refs/cache/faa/ac150_5300_13b_chg1_p136_181_284-288.pdf. For every pair of spots closer than
     40 m the wing shapes (a segment of max_span_m across the heading, or a disc of that diameter when the heading is
     unknown) must be >= 10 ft apart - hard; helipad spots take part as discs of their rotor size (or the smallest OSM
     pad when unknown); capacity_span_m must keep CAP_GAP likewise. These are consistency checks (the build derives the
     sizes from the same rule). Independent of the sizing: no two ramp / hangar-apron spots closer than DUP_M (one
     aircraft seen twice) - hard; the observed types are recounted from every adsb.lol type in a spot's evidence
     (stays, signal starts / ends, merged duplicates) and spots whose observed type is wider than max_span_m /
     capacity_span_m are listed (not a failure) and compared with the spot's own flags - hard if they disagree.
     Spot vs taxiways: the distance from each spot's wing shape (capacity size) to open taxiway / taxilane centrelines,
     against AC 150/5300-13B Table 4-1 ADG I object distances (13.6 / 12.0 m), reported per src; hard for rule-made
     (inferred hangar-apron) spots, whose rule promises it.
  7. Hot spots: the OSM taxiways inside each AL-5015 ellipse against the taxiways the CS hot-spot text names. A
     consistency check of the diagram registration and the OSM refs; HS whose CS text names no taxiway (HS 2, 3, 4) are
     reported as 'not checkable against the CS'.
  8. Holds: NAIP bar vs OSM node offset; distance from the runway centreline per runway.
  9. Data hygiene: every element has src 'obs' / 'inf' and refs that exist in 'sources'; the .js twin carries the same
     object as the .json. D1 (no ADS-B identity in any committed file; since the Phase 1 review): every committed
     ADS-B-derived file (D1_FILES: data/hwd_airport.*, data/ga_types.json, refs/cache/adsb/*, docs/phase1/*.json,
     docs/*.md) is scanned for identity keys (hex, icao24, callsign, flight, registration, r ...), per-row time keys
     (t, t0, time, seen ...) and epoch-second numbers, N-number-like tokens, and any token equal to a hex address,
     registration or callsign of an aircraft that the pinned adsb.lol recording saw within 5 km of the ARP
     (identity_set, read from sfo3d/refs/cache/rec_pack) - hard. SOURCES coverage: every committed data file under
     data/, refs/cache/ (not local/, not .parts/) and docs/phase1/ matches a key (or glob key) of a SOURCES.json in its
     folder or a parent folder - hard.
usage: python3 hwd3d/tools/check_airport.py
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


D1_FILES = ['data/hwd_airport.json', 'data/hwd_airport.js', 'data/ga_types.json', 'refs/cache/adsb/*.json', 'refs/cache/adsb/*.txt',
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
    miss = []
    for f in files:
        d = os.path.dirname(f); ok = False
        while True:
            sj = os.path.join(HWD, d, 'SOURCES.json')
            if os.path.exists(sj):
                rel_ = os.path.relpath(f, d) if d else f
                for k in json.load(open(sj)):
                    if any(fnmatch.fnmatch(rel_, kk.strip()) for kk in k.split(',')): ok = True; break
            if ok or not d: break
            d = os.path.dirname(d)
        if not ok: miss.append(f)
    say('   SOURCES coverage: %d committed data files under data/, refs/cache/, docs/phase1/; without a SOURCES.json entry: %d %s' % (len(files), len(miss), miss))
    return miss


def main():
    D = json.load(open(os.path.join(HWD, 'data', 'hwd_airport.json')))
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
                                                                                       ', '.join('%s %s (%s)' % (w['id'], w['ref'] or '-', 'faint rule' if w['evidence']['naip_paint']['faint'].get('snap') else 'strong rule') for w in sn)))
    N24p = Naip('2024'); hp = [(h['x'], h['z']) for h in D['holds']]; off_secs = []; nsec = 0
    for w in D['taxiways'] + D['taxilanes']:
        if w['status'] != 'open': continue
        P_ = B.densify(w['pts'], 2.0); S_ = B.arclen(P_); T_ = B.tangents(P_)
        if S_[-1] < 8.0: continue
        ss = np.arange(0.0, S_[-1] + 1e-9, B.ST_STEP); fo = np.full(len(ss), np.nan)
        for i, s_ in enumerate(ss):
            p_ = np.array([np.interp(s_, S_, P_[:, 0]), np.interp(s_, S_, P_[:, 1])])
            t_ = np.array([np.interp(s_, S_, T_[:, 0]), np.interp(s_, S_, T_[:, 1])]); t_ /= max(1e-9, np.hypot(*t_))
            if B.RWY_MASK.contains(Point(p_)) or any(math.hypot(p_[0] - h[0], p_[1] - h[1]) < B.HOLD_MASK_M for h in hp): continue
            r_ = N24p.cross_peak(p_, t_, half=B.HALF, avg=B.AVG, step=0.1, min_contrast=B.FAINT_C)
            if r_ and r_[2] < B.AMB * r_[1] and N24p.bstar(p_, t_, r_[0], B.AVG) >= B.FAINT_BSTAR_MIN: fo[i] = r_[0]
        secs = B.faint_sections(ss, fo); nsec += len(secs)
        off_secs += [(w['id'], w['ref'], q['s0_m'], q['n'], q['median_m'], q['iqr_m']) for q in secs if q['offset']]
    say('   NAIP 2024 faint yellow centreline per 50 m section on the final geometry: %d sections with >= %d ridges; sections with a consistent offset (|median| >= %.1f m, IQR <= %.1f m): %d %s' % (
        nsec, B.FAINT_SEC_N, B.FAINT_MED_MIN, B.FAINT_IQR_MAX, len(off_secs), off_secs))
    if off_secs: hard.append('taxiway paint offset per section')
    fo_ = [w['evidence']['naip_paint']['faint']['median_offset_m'] for w in D['taxiways'] if w['evidence']['naip_paint'].get('faint', {}).get('median_offset_m') is not None and w['evidence']['naip_paint']['faint']['n'] >= 10]
    if fo_: say('   (for reference: faint ridges of the OSM line before snapping, >= 10 per way, %d taxiways: per-way median offset p10/p50/p90 %+.2f / %+.2f / %+.2f m; this summary hides single ways, hence the section test)' % (len(fo_), *np.percentile(fo_, [10, 50, 90])))
    onr = [(w['id'], w['ref'], w['on_runway']['len_m']) for w in D['taxiways'] if w.get('on_runway', {}).get('runway_overlap')]
    say('   taxiway ways with > 50 m inside a NASR runway rectangle (on_runway.runway_overlap): %d %s' % (len(onr), onr))
    wd = [w['width']['naip_grey_width_m'] for w in D['taxiways'] + D['taxilanes'] if w.get('width', {}).get('naip_src') == 'obs']
    say('   widths: NAIP grey width measured on %d of %d open ways (median %s m); the others carry only the AC default width [inf]' % (
        len(wd), sum(1 for w in D['taxiways'] + D['taxilanes'] if w['status'] == 'open'), r1(np.median(wd)) if wd else None))

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

    def shape(s, key='max_span_m'):
        if s['kind'] == 'helipad': return Point(s['x'], s['z']).buffer((s['size'].get('max_rotor_m') or heli_def) / 2, 32)
        sp = s['size'][key]
        if s['heading'] is None: return Point(s['x'], s['z']).buffer(max(sp / 2, 0.005), 32)
        u = np.array([math.cos(math.radians(s['heading'])), math.sin(math.radians(s['heading']))]); c = np.array([s['x'], s['z']])
        return LineString([tuple(c - u * sp / 2), tuple(c + u * sp / 2)])
    WH = W + H; pos = np.array([[s['x'], s['z']] for s in WH])
    for key, clear, name in (('max_span_m', WINGTIP, 'AC design size (10 ft)'), ('capacity_span_m', B.CAP_GAP, 'capacity size (%.1f m gap)' % B.CAP_GAP)):
        viol = []; mins = []
        for i in range(len(WH)):
            d = np.hypot(*(pos - pos[i]).T)
            for j in np.nonzero((d < 40) & (np.arange(len(WH)) > i))[0]:
                if WH[i]['kind'] == 'helipad' and WH[j]['kind'] == 'helipad': continue      # pads are fixed, mapped geometry
                c = shape(WH[i], key).distance(shape(WH[j], key)); mins.append(c)
                if c < clear - 0.006: viol.append((WH[i]['id'], WH[j]['id'], round(c, 3)))   # 0.006: sizes are floored to 0.01 m
        say('   %s: %d spot pairs within 40 m (helipad spots included as discs of their rotor size, unknown = %.1f m, the smallest OSM pad); min clearance %.3f m (required %.3f m); violations %d %s' % (
            name, len(mins), heli_def, min(mins), clear, len(viol), viol[:10]))
        if viol: hard.append('spacing (%s)' % name)
        bv = []
        for s in W:
            for bid, pg in blds:
                if s['kind'] == 'hangar_apron' and bid == s.get('hangar'): continue
                if pg.distance(Point(s['x'], s['z'])) > 40: continue
                c = shape(s, key).distance(pg)
                if c < clear - 0.006: bv.append((s['id'], bid, round(c, 2)))
        say('   %s: wing shape vs building / hangar outlines (own hangar excepted for hangar-apron spots): violations %d %s' % (name, len(bv), bv[:8]))
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
    # spot vs taxiway / taxilane centrelines
    twy = unary_union([LineString(w['pts']) for w in D['taxiways'] if w['status'] == 'open'])
    tln = unary_union([LineString(w['pts']) for w in D['taxilanes'] if w['status'] == 'open'])
    rows = Counter(); rule_bad = []
    for s in W:
        g = shape(s, 'capacity_span_m'); dt, dl = g.distance(twy), g.distance(tln)
        inside = dt < B.TWY_OBJ_M or dl < B.TLN_OBJ_M
        rows[(s['src'], s['kind'], 'inside' if inside else 'clear')] += 1
        if s.get('ref_point') == 'rule_point':
            u = np.array([math.cos(math.radians(s['heading'])), math.sin(math.radians(s['heading']))]); n_ = np.array([u[1], -u[0]])   # nose direction
            c = np.array([s['x'], s['z']])
            ol = unary_union([LineString([tuple(c - u * B.ADG_SPAN['I'] / 2), tuple(c + u * B.ADG_SPAN['I'] / 2)]), LineString([tuple(c + n_ * B.FUS_FWD), tuple(c - n_ * B.FUS_AFT)])])
            if ol.distance(twy) < B.TWY_OBJ_M - 0.05 or ol.distance(tln) < B.TLN_OBJ_M - 0.05: rule_bad.append((s['id'], round(ol.distance(twy), 1), round(ol.distance(tln), 1)))
    say('   spot wing shape (capacity size) vs open taxiway / taxilane centrelines, AC 150/5300-13B Table 4-1 ADG I object distance %.1f / %.1f m: %s' % (
        B.TWY_OBJ_M, B.TLN_OBJ_M, ', '.join('%s %s %s: %d' % (k[0], k[1], k[2], v) for k, v in sorted(rows.items()))))
    say('   rule-made (inferred hangar-apron) spots whose ADG I outline is inside that distance: %d %s' % (len(rule_bad), rule_bad))
    if rule_bad: hard.append('inferred spot vs taxiway clearance')

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
    for k in ('runways', 'taxiways', 'taxilanes', 'aprons', 'holds', 'hotspots', 'helipads', 'hangars', 'buildings', 'markers', 'parking', 'al5015_labels', 'not_placed'):
        for e in D[k]:
            nel += 1
            if e.get('src') not in ('obs', 'inf') or not e.get('refs') or not set(e['refs']) <= srcs: badel.append((k, e.get('id') or e.get('what')))
    say('   %d elements; %d without a valid src / refs %s' % (nel, len(badel), badel[:5]))
    if badel: hard.append('src/refs')
    share = Counter(e['src'] for k in ('runways', 'taxiways', 'taxilanes', 'aprons', 'holds', 'hotspots', 'helipads', 'hangars', 'buildings', 'markers', 'parking') for e in D[k])
    say('   element src shares: %s' % dict(share))
    js = open(os.path.join(HWD, 'data', 'hwd_airport.js'), encoding='utf-8').read()
    body = js[js.index('export const HWD_AIRPORT = ') + len('export const HWD_AIRPORT = '):].rstrip().rstrip(';')
    same = json.loads(body) == D
    say('   .js twin carries the same object as the .json: %s' % same)
    if not same: hard.append('js twin')
    d1 = d1_scan()
    if d1: hard.append('D1')
    miss = sources_coverage()
    if miss: hard.append('SOURCES coverage')

    say('\nRESULT: %s' % ('ALL HARD CHECKS PASSED' if not hard else 'FAILED: ' + '; '.join(hard)))
    os.makedirs(os.path.join(HWD, 'out', 'phase1', 'g5'), exist_ok=True)
    open(os.path.join(HWD, 'out', 'phase1', 'g5', 'check_airport.txt'), 'w').write('\n'.join(OUT) + '\n')
    return 1 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
