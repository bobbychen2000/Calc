"""Build the HWD airport data set: data/hwd_airport.json and its ES-module twin data/hwd_airport.js.

New for hwd3d (Phase 1, task G5). It follows the pattern of sfo3d/tools/build_airfield_details.py @ a967f9b (OSM taxiway
centrelines checked and locally moved onto the paint measured on NAIP, OSM holding positions with NAIP-measured bars,
licence / attribution fields in the file) and of the sfo3d data headers; window_corr() and the measure() loop are forked
from that file (see their docstrings). Everything else is new.

Inputs (all committed; nothing is fetched):
  FAA NASR cycle 2026-10-29       refs/cache/faa/nasr_2026-10-29_HWD.json (via tools/common/hwd_frame.py RWY_ENDS/DATA)
  FAA Chart Supplement SW 2611    refs/cache/faa/chart_supplement_HWD.json (tools/faa/cs_hwd.py)
  FAA AL-5015 cycle 2611          refs/cache/faa/05015ad_2611.pdf (tools/airport/al5015.py; pdftoppm/pdftotext)
  FAA AC 150/5300-13B Chg 1       refs/cache/faa/ac150_5300_13b_chg1_p136_181_284-288.pdf (clearances, quoted)
  FAA AC 150/5340-1M Chg 1        refs/cache/faa/ac150_5340_1m_chg1_p52-54_63.pdf (edge marking, hold marking)
  OSM, pinned 2026-11-12T00:00Z    refs/cache/osm/khwd_features.json (+ khwd_osm_xcheck.json: AL-5015 affine)
  USDA NAIP 2024 / 2022            refs/cache/naip/naip_<year>_hwd_rgb.jpg + .json (tools/imagery/paintline.py)
  adsb.lol aggregates (ODbL)       refs/cache/adsb/hwd_parked_stays.json, hwd_runup_holds.json (tools/adsb/)
  FAA ACD wingspans                data/ga_types.json (tools/types/build_ga_types.py)
Output: data/hwd_airport.json (+ .js twin); a QA plot out/phase1/g5/airport_overview.png (gitignored).
Deterministic: no clock, no randomness (paintline's fit check uses a fixed seed), sorted iteration, rounded floats.

Conventions of the output: world frame of tools/common/hwd_frame.py (x east, z south, metres, origin = NASR ARP;
y = NAVD 88 height in m [inferred datum]); headings in degrees true, clockwise from north; every element has
src 'obs' (seen in a source: surveyed, mapped, measured or observed) or 'inf' (inferred: derived by a rule, a
schematic chart or by eye), 'refs' (keys of the top-level 'sources') and 'evidence'.

Changes from the Phase 1 review (2026-11-12; docs/phase1_data_report.md section 6):
  taxiways   a faint-paint rule moves ways / 50 m sections whose faint yellow ridges agree on an offset (taxiway E
             490634605 was 3.3 m off its paint); per-way faint sections are written; ref_src / ref_note (three OSM refs
             AL-5015 does not support along the way, REF_DIAGRAM); on_runway; width (NAIP grey width where measurable,
             else an AC default marked inf).
  runways    lighting when the tower is closed (VASI SS-SR, PAPI / REIL unavailable, MIRL preset low; NASR LGT_SKED + CS).
  parking    NAIP 2024 blobs take a recorded by-eye verdict (refs/cache/naip/naip_blob_review.json: vehicles, empty
             paint, duplicates and blobs between two aircraft are dropped or split); a ramp / hangar-apron spot is 'obs'
             only with >= 2 independent observations ('strength'); duplicates closer than DUP_M are merged before
             sizing; fixed-wing ADS-B on an OSM helipad is evidence of that pad, not a ramp spot; an ADS-B spot at a
             hangar wall is that hangar's apron spot; inferred hangar aprons need OSM apron (not taxiway buffers) in front
             of the real wall, an ADG I outline outside the AC 150/5300-13B Table 4-1 object distances of open taxiways /
             taxilanes, no NAIP objects and no white roof there, and pass a by-eye rejection list; sizes are solved in
             tiers (painted tie-downs, obs, inf) with buildings and helipads as obstacles, for the AC 10 ft (max_span_m)
             and for a 1.0 m practical gap (capacity_span_m); observed spans from every adsb.lol type in the evidence;
             flags; tie-down aircraft_seen from a planform mask test; ref_point per spot; ids from the rounded position
             (stable across rebuilds), e.g. RE187N279 = ramp spot 187 m east, 279 m north of the ARP.
  other      segmented-circle diameter_src inf; fire-station deviation; not_placed ids generated; not_yet_sourced (signs,
             lighting fixtures, marking geometry, wind cones).
usage: python3 hwd3d/tools/build_airport.py [--no-plot]
"""
import json, math, os, sys
from collections import Counter, defaultdict

import numpy as np
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.abspath(os.path.join(HERE, '..'))
for p in ('common', 'imagery', 'airport'):
    sys.path.insert(0, os.path.join(HERE, p))
import hwd_frame as F                                                     # noqa: E402
from paintline import Naip, find_ladder                                   # noqa: E402
import al5015                                                             # noqa: E402
import rwy_edges                                                          # noqa: E402
import tiedowns as TD                                                     # noqa: E402

FT = 0.3048
OUT_JSON = os.path.join(HWD, 'data', 'hwd_airport.json')
OUT_JS = os.path.join(HWD, 'data', 'hwd_airport.js')
FIG = os.path.join(HWD, 'out', 'phase1', 'g5')


def rel(p): return os.path.relpath(p, HWD)
def r2(v): return None if v is None else round(float(v), 2)
def r1(v): return None if v is None else round(float(v), 1)
def xz(p): return [r2(p[0]), r2(p[1])]
def ring(pts): return [xz(p) for p in pts]


def load(p): return json.load(open(os.path.join(HWD, p)))


NASR = load('refs/cache/faa/nasr_2026-10-29_HWD.json')
CS = load('refs/cache/faa/chart_supplement_HWD.json')
OSMF = load('refs/cache/osm/khwd_features.json')
XCHK = load('refs/cache/osm/khwd_osm_xcheck.json')
STAYS = load('refs/cache/adsb/hwd_parked_stays.json')
GATYPES = load('data/ga_types.json')['types']
FE = OSMF['features']
RMK = [r['REMARK'].strip() for r in NASR['tables']['APT_RMK.csv']]
BASE = NASR['tables']['APT_BASE.csv'][0]

# ------------------------------------------------------------------------------------------------------- sources
SOURCES = {
    'nasr': {'what': 'FAA NASR 28-day subscription, cycle effective 2026-10-29 (APT_BASE, APT_RWY, APT_RWY_END, APT_RMK, ATC, FRQ)',
             'file': 'refs/cache/faa/nasr_2026-10-29_HWD.json', 'url': 'https://nfdc.faa.gov/webContent/28DaySub/extra/29_Oct_2026_APT_CSV.zip',
             'licence': 'U.S. Government work (17 U.S.C. 105), public domain'},
    'cs': {'what': 'FAA Chart Supplement Southwest U.S., 29 OCT 2026 - 24 DEC 2026, HAYWARD EXEC (HWD) entry + hot spot list',
           'file': 'refs/cache/faa/chart_supplement_HWD.json', 'url': 'https://aeronav.faa.gov/afd/29oct2026/sw_174_29OCT2026.pdf',
           'licence': 'U.S. Government work, public domain'},
    'al5015': {'what': 'FAA airport diagram AL-5015 (FAA), d-TPP cycle 2611 (29 Oct - 26 Nov 2026); schematic, "Positional accuracy within +-600 feet" (TPP legend)',
               'file': 'refs/cache/faa/05015ad_2611.pdf', 'url': 'https://aeronav.faa.gov/d-tpp/2611/05015ad.pdf',
               'licence': 'U.S. Government work, public domain'},
    'ac5300': {'what': 'FAA AC 150/5300-13B Airport Design, Change 1 (8/16/2024, errata 4/3/2025): Table 4-1, Table 5-1, Appendix E',
               'file': 'refs/cache/faa/ac150_5300_13b_chg1_p136_181_284-288.pdf',
               'url': 'https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5300-13B-Airport-Design-Chg1-w-errata.pdf',
               'licence': 'U.S. Government work, public domain'},
    'ac5340': {'what': 'FAA AC 150/5340-1M Standards for Airport Markings, consolidated Change 1 (12/23/2020): para 2.8, 2.9.1, 3.3.4.1',
               'file': 'refs/cache/faa/ac150_5340_1m_chg1_p52-54_63.pdf',
               'url': 'https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-1M-Chg-1-Airport-Markings.pdf',
               'licence': 'U.S. Government work, public domain'},
    'osm': {'what': 'OpenStreetMap, database state pinned at %s (Overpass attic query; same state rebuilt from the OSM API)' % OSMF['osm_base'],
            'file': 'refs/cache/osm/khwd_features.json (from %s, sha256 %s)' % (OSMF['source'], OSMF['source_sha256'][:16]),
            'url': 'https://www.openstreetmap.org/copyright', 'licence': 'ODbL 1.0, (c) OpenStreetMap contributors'},
    'naip2024': {'what': 'USDA NAIP 2024 CA, 0.6 m, flown 2024-05-20 (tiles m_3712223_se, m_3712224_sw)', 'file': 'refs/cache/naip/naip_2024_hwd_rgb.jpg',
                 'url': 'https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer',
                 'licence': 'public domain; credit requested: USDA Farm Production and Conservation Business Center, Geospatial Enterprise Operations'},
    'naip2022': {'what': 'USDA NAIP 2022 CA, 0.6 m, flown 2022-05-18/19 (Planetary Computer COGs)', 'file': 'refs/cache/naip/naip_2022_hwd_rgb.jpg',
                 'url': 'https://planetarycomputer.microsoft.com/dataset/naip', 'licence': 'public domain; credit as naip2024'},
    'adsb': {'what': 'own aggregates of the adsb.lol recording 2026-11-04 17Z .. 11-11 13Z (111 h): parked stays, spots, signal starts/ends, run-up/hold stops (no identities, default D1)',
             'file': 'refs/cache/adsb/hwd_parked_stays.json, refs/cache/adsb/hwd_runup_holds.json', 'url': 'https://adsb.lol',
             'licence': 'ODbL 1.0 - Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL'},
    'acd': {'what': 'FAA Aircraft Characteristics Database (October 2024) wingspans per type, via data/ga_types.json', 'file': 'data/ga_types.json',
            'url': 'https://www.faa.gov/airports/engineering/aircraft_char_database/aircraft_data', 'licence': 'U.S. Government work, public domain'},
}

# ---------------------------------------------------------------------------------------------- constants (sourced)
WINGTIP_CLEAR = 10 * FT     # AC 150/5300-13B Chg 1 Table 5-1 "I and II: 10 ft (3 m)"; Fig E-2 "Wingspan plus 10 ft (3 m)"
ADG_SPAN = {'I': 49 * FT, 'II': 79 * FT, 'III': 118 * FT}   # AC 150/5300-13B Table 4-1, TSA (maximum ADG wingspan)
WINGSPAN_LIMIT = {}         # taxiway ref -> (limit ft, NASR remark), from the NASR remarks
for t in RMK:
    if t.startswith('TWY ') and 'WINGSPAN GTR THAN' in t:
        ref = t.split()[1]; ft_ = float(t.split('GTR THAN')[1].split('FT')[0])
        WINGSPAN_LIMIT[ref] = (ft_, t)
assert WINGSPAN_LIMIT.get('Z1', (0,))[0] == 94 and WINGSPAN_LIMIT.get('A1', (0,))[0] == 100, WINGSPAN_LIMIT
AL5015_TWYS = ['A', 'A1', 'B', 'C', 'D', 'E', 'F', 'Z', 'Z1']     # AL-5015 2611 taxiway labels (PLAN.md s.1; G1 check); since the
                                                                 # Phase 1 review check_airport.py re-reads them from the PDF text layer
# OSM taxiway refs that AL-5015 does not support along the way (by eye on AL-5015 2611 at 400 dpi with the ways drawn
# through the diagram affine, out/phase1/review_fix/al_ways_E_D.png and al_ways_F.png, 2026-11-12; agrees with the Phase 1
# review, which read the same on its own registration): ref kept as OSM maps it, ref_src 'inf'
REF_DIAGRAM = {
    490634605: 'OSM only (apron route): the whole way lies north of taxiway A inside the area AL-5015 labels GA TRANSIENT RAMP, where the diagram draws apron and no E; AL-5015 prints E only at and south of A',
    204801016: 'partly OSM only: AL-5015 prints D only where this way meets taxiway A; north of A (about 220 m) the way crosses what the diagram draws as apron (toward the tower), with no D',
    490634609: 'OSM only (apron route): the way runs through the WEST HANGARS / FBO RAMP area of AL-5015, where the diagram draws apron and no F; AL-5015 prints F only south of hot spot HS 3',
}
TWY_WIDTH_DEFAULT = {'taxiway': 35 * FT, 'taxilane': 25 * FT}
# default widths [inf]: AC 150/5300-13B Chg 1 Table 4-2 "Taxiway/Taxilane Width" TDG 2A/2B 35 ft (10.7 m) for taxiways and
# TDG 1A/1B 25 ft (7.6 m) for taxilanes; HWD's design aircraft / TDG per taxiway is not known (no ALP read), so these are
# defaults chosen for a GA airport with business jets, not measurements
GREY_STEP = 6.0     # m between pavement cross profiles (as plot_overlays.py naip_measure (a))
NOT_YET_SOURCED = [
    {'what': 'airfield signs: mandatory (hold-position, runway / taxiway location), direction, destination and the distance-remaining sign positions',
     'known': 'only the NASR remarks "RY 10R HAS LANDING DISTANCE REMAINING SIGNS (LGTD) NORTH SIDE OF RY" / "RY 28L ... SOUTH SIDE OF RY" (runways[].distance_remaining_signs); no sign location, text or direction in any source read so far',
     'candidates': 'NAIP 2024 (sign panels and shadows are 1-3 m objects; uncertain at 0.6 m), FAA sign-siting standards applied as rules (inf), owner photos',
     'src': 'inf', 'refs': ['nasr']},
    {'what': 'lighting fixtures: VASI boxes (10R V4R, 28L V4L), PAPI units (10L / 28R P4L), REIL units (10R, 28L), MIRL edge-light positions, taxiway edge lights or reflectors, the beacon mast',
     'known': 'types, codes, glide angles, TCH and the tower-closed schedule (runways[].ends[].vgsi / reil, runways[].edge_lights .when_tower_closed); the beacon is on the tower [inf] (buildings[].beacon)',
     'candidates': 'NAIP 2024 (VASI / PAPI boxes beside the runway), FAA siting standards applied as rules (inf), owner photos',
     'src': 'inf', 'refs': ['nasr', 'cs']},
    {'what': 'marking geometry beyond hold bars and displaced thresholds: runway designations, threshold / aiming-point / touchdown-zone bars, runway edge and centreline stripes, taxiway centreline and edge lines, ramp and taxilane lines, the painted H circle north of the Green Ramp',
     'known': 'marking types PIR / NPI (NASR); the runway edge stripes, displaced-threshold bars and 16 hold bars measured on NAIP; the Green Ramp tie-down tees (parking)',
     'candidates': 'NAIP 2024 paint detection (the sfo3d markings pipeline), AC 150/5340-1M standard dimensions for the rest (inf)',
     'src': 'inf', 'refs': ['nasr', 'naip2024', 'ac5340']},
    {'what': 'five unlit wind cones (AL-5015 legend symbol "Wind Cone, unlit")',
     'known': 'AL-5015 symbols near 10L, 10R, 28R, 28L and south of 10R/28L; NAIP 2024 shows a 1-2 m object 2.3-6.1 m from each (by eye, docs/phase1_crosscheck.md section 4 #7); OSM maps only the lit windsock',
     'candidates': 'add as obs (diagram symbol + NAIP object) after a closer NAIP read',
     'src': 'inf', 'refs': ['al5015', 'naip2024']},
]
FIT_RES_TXT = None  # 'min-max' residual (m) of the AL-5015 affine at the 4 NASR runway ends, set in main() from khwd_osm_xcheck.json

# paint snapping (window_corr, forked from sfo3d build_airfield_details.py; thresholds as there unless stated)
ST_STEP = 4.0       # m between measuring stations
HALF, AVG = 3.5, 4.0
MIN_C = 10.0        # DN, min(R,G)-B ridge over the profile median (sfo3d: 10)
FAINT_C = 4.0       # DN: faint ridges (worn paint) are measured and reported per way ('faint'), never used to move a line
AMB = 0.6           # second ridge (>= 1.5 m away) must be < AMB x the best (sfo3d: 0.6)
BSTAR_MIN = 9.0     # CIE b* of the ridge colour (white-paint rejection; sfo3d calibration) - HWD distribution in the output
# faint-paint snap (Phase 1 review, 2026-11-12: taxiway E 490634605 lay 3.3 m from its worn centreline paint and the
# strong rule above never moved it). A way, or a 50 m section of it, whose faint yellow ridges agree is moved onto them:
FAINT_SEC_M = 50.0      # m, section length (chosen)
FAINT_SEC_N = 8         # faint ridges per section, or FAINT_WAY_N over the whole way (chosen; 8 of 12-13 stations)
FAINT_WAY_N = 20
FAINT_MED_MIN = 1.0     # m: |median offset| of a section that counts as an offset (chosen; above the 0.6 m NAIP pixel)
FAINT_IQR_MAX = 0.6     # m: IQR of the section's ridges (chosen; one NAIP pixel)
FAINT_BSTAR_MIN = 8.0   # CIE b* of a faint ridge counted here (yellow; worn yellow paint measured 8.6-15 at HWD, white < 5)
HOLD_MASK_M = 12.0  # stations within this of an OSM holding position are not measured (the yellow bar)
HOLD_MIN_C = 20.0   # find_ladder contrast to accept a NAIP bar (sfo3d HOLD_MIN_C 20)
HOLD_SEARCH = 12.0  # m along the taxiway either side of the OSM node


# ------------------------------------------------------------------------------------------------- geometry helpers
def densify(pl, step=2.0):
    P = np.asarray(pl, float); out = [P[0]]
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; L = np.linalg.norm(b - a); n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1): out.append(a + (b - a) * k / n)
    return np.array(out)


def arclen(P): return np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]


def tangents(P):
    T = np.gradient(P, axis=0); l = np.hypot(T[:, 0], T[:, 1]); l[l == 0] = 1; return T / l[:, None]


def runway_poly(rw, margin=0.0):
    a, b = rw.split('/'); A = F.rwy_axis(a); W = F.RWY_DATA[rw]['widthFt'] * FT / 2 + margin
    o = np.array(A['origin']); d = np.array(A['dir']); rt = np.array(A['right']); L = A['length']
    return [o - rt * W, o + rt * W, o + d * L + rt * W, o + d * L - rt * W]


RWY_POLY = {rw: Polygon(runway_poly(rw)) for rw in F.RWY_DATA}
RWY_MASK = prep(unary_union([Polygon(runway_poly(rw, 3.0)) for rw in F.RWY_DATA]))
RWY_NEAR = prep(unary_union([Polygon(runway_poly(rw, 40.0)) for rw in F.RWY_DATA]))
APRON_ALL = prep(unary_union([Polygon(a['w']).buffer(0) for a in FE['apron']]))


def window_corr(ss, offs, min_shift=0.5, mad_max=0.4, clip=None, strict_big=True):
    """Forked from sfo3d/tools/build_airfield_details.py window_corr @ a967f9b (unchanged): per-sample lateral
    correction from the measured paint offsets. For each sample, the samples within +-3 (7-sample window) that found
    paint: at least 4 needed; a local line offset(s) is fitted; the correction is the line's value at the sample when
    the residual MAD < mad_max, the slope < 0.15 and |value| > min_shift; a correction above 1.5 m needs the full window
    with paint and MAD < 0.25. Smoothed (running median 3, moving average 5); masked samples (inf) interpolate."""
    masked = np.isinf(offs); offs = np.where(masked, np.nan, offs)
    corr = np.zeros(len(ss))
    for i in range(len(ss)):
        sl = slice(max(0, i - 3), i + 4); v = offs[sl]; sv = ss[sl]; ok = ~np.isnan(v); v, sv = v[ok], sv[ok]
        if len(v) < 4: continue
        m_ = float(np.median(v)); mad0 = float(np.median(np.abs(v - m_)))
        val, mad = m_, mad0
        if len(v) >= 5 and mad0 >= 0.1:
            b_, a_ = np.polyfit(sv - ss[i], v, 1); r_ = v - (a_ + b_ * (sv - ss[i])); mad1 = float(np.median(np.abs(r_)))
            if mad1 < mad0 and abs(b_) < 0.15: val, mad = float(a_), mad1
        if mad < mad_max and abs(val) > min_shift: corr[i] = val if clip is None else float(np.clip(val, -clip, clip))
        if strict_big and abs(corr[i]) > 1.5 and (len(v) < 7 or mad >= 0.25): corr[i] = 0.0
    if len(corr) >= 3:
        cm = np.array([np.median(corr[max(0, i - 1):i + 2]) for i in range(len(corr))])
        corr = np.array([cm[max(0, i - 2):i + 3].mean() for i in range(len(cm))])
        corr[np.abs(corr) < 0.05] = 0.0
    if masked.any() and (~masked).sum() >= 2:
        corr[masked] = np.interp(ss[masked], ss[~masked], corr[~masked])
    return corr


# ================================================================================================== 1. frame
def frame():
    return {
        'id': F.FRAME_ID, 'origin_nad83': [F.ARP_LAT, F.ARP_LON],
        'axes': 'x = east (m), z = south (m), y = up (m); origin = FAA NASR airport reference point (ARP) of HWD, rounded to 1e-7 deg; exact local tangent plane on GRS80, datum NAD83(2011) [realisation inferred]',
        'y': F.Y_REF, 'field_elev_ft': F.FIELD_ELEV_FT, 'field_elev_y': r2(F.FIELD_ELEV_Y), 'ground_y_nominal': F.GROUND_Y,
        'ground_y_note': 'nominal flat ground for code without terrain (mean of the 6 NASR runway-surface points) [inferred]; use the runway profiles on runways',
        'wgs84_minus_nad83_en_m': [F.WGS84_MINUS_NAD83_E, F.WGS84_MINUS_NAD83_N], 'wgs84_epoch': F.WGS84_EPOCH,
        'wgs84_note': 'OSM and ADS-B (WGS 84) are placed with hwd_frame.wgs84_to_world (x += 1.568, z += 0.162)',
        'heading': 'degrees true, clockwise from north; world unit vector of heading h = (sin h, -cos h)',
        'ring_convention': 'polygon rings are lists of [x, z]; open (first vertex not repeated)',
        'code': 'tools/common/hwd_frame.py = js/geo.js',
    }


# ================================================================================================== 2. runways
VGSI_TYPE = {'P': 'PAPI', 'V': 'VASI'}


def runways(N24, N22):
    tpa = CS['derived']['tpa_ft_msl']; tpa_agl = CS['derived']['tpa_ft_agl']; right = CS['derived']['right_traffic']
    grad = CS['derived']['gradient']; strength = CS['derived']['strength_klb']
    nasr_end = {r['RWY_END_ID']: r for r in NASR['tables']['APT_RWY_END.csv']}
    osm_rw = {r['ref']: r for r in XCHK['runways']}
    lgt = [r['REMARK'].strip() for r in NASR['tables']['APT_RMK.csv'] if r.get('REF_COL_NAME') == 'LGT_SKED']
    cs_lgt = [l for l in CS['entry']['lines'] if 'When twr clsd' in l]
    sked_ev = 'NASR APT_RMK LGT_SKED: %r; CS: %r' % (lgt[0] if lgt else None, cs_lgt[0][cs_lgt[0].index('LGT'):] if cs_lgt and 'LGT' in cs_lgt[0] else None)
    out = []
    for rw, D in sorted(F.RWY_DATA.items()):
        a, b = D['ends']; A = F.rwy_axis(a)
        ends = []
        for e in (a, b):
            E = F.RWY_ENDS[e]; ne = nasr_end[e]; x, z = F.end_world(e)
            thr = None
            if E['thrLat'] is not None:
                tx, tz = F.thr_world(e)
                thr = {'x': r2(tx), 'z': r2(tz), 'y': r2(E['thrElev'] * FT), 'lat': E['thrLat'], 'lon': E['thrLon'],
                       'elev_ft': E['thrElev'], 'len_ft_nasr': E['disp'], 'len_m_surveyed': r2(F.thr_disp_m(e)),
                       'src': 'obs', 'refs': ['nasr', 'cs'],
                       'evidence': 'NASR DISPLACED_THR_LEN %d ft and surveyed LAT/LONG_DISPLACED_THR (3RD PARTY SURVEY 2023/07/05); CS "Thld dsplcd %d´"; the surveyed point lies on the axis (hwd_frame test)' % (E['disp'], E['disp'])}
            v = E['vgsi']
            rh = e in right
            traffic = {'side': 'right' if rh else 'left', 'src': 'obs', 'refs': ['nasr', 'cs'],
                       'evidence': 'NASR RIGHT_HAND_TRAFFIC_PAT_FLAG %r; CS: right traffic %s, left %s (CS prints "Rgt tfc." only for the right-hand ends)' % (
                           ne.get('RIGHT_HAND_TRAFFIC_PAT_FLAG', ''), ', '.join(right), ', '.join(CS['derived']['left_traffic']))}
            ends.append({
                'id': e, 'lat': E['lat'], 'lon': E['lon'], 'x': r2(x), 'z': r2(z), 'y': r2(E['elev'] * FT), 'elev_ft': E['elev'],
                'tdz_elev_ft': E['tdzElev'], 'true_alignment_deg': E['trueAln'], 'bearing_deg': E['brg'],
                'displaced_threshold': thr,
                'marking': {'type': E['marking'], 'cond': ne.get('RWY_MARKING_COND'), 'name': {'PIR': 'precision instrument', 'NPI': 'non-precision instrument'}[E['marking']],
                            'src': 'obs', 'refs': ['nasr'], 'evidence': 'NASR RWY_MARKING_TYPE_CODE / RWY_MARKING_COND'},
                'vgsi': {'code': v, 'type': VGSI_TYPE[v[0]], 'boxes': int(v[1]), 'side': {'L': 'left', 'R': 'right'}[v[2]],
                         'when_tower_closed': ('operates SS-SR' if v[0] == 'V' else 'unavailable'), 'when_tower_closed_evidence': sked_ev,
                         'position': None, 'position_note': 'box / unit positions not sourced yet (see not_yet_sourced)',
                         'glide_deg': E['gpa'], 'tch_ft': E['tch'], 'src': 'obs', 'refs': ['nasr', 'cs'],
                         'evidence': 'NASR VGSI_CODE %s, VISUAL_GLIDE_PATH_ANGLE, THR_CROSSING_HGT; CS "%s(%s)—GA %.1fº TCH %d´" (type confirmed by the CS; boxes / side decoded from the NASR code letters [convention from memory, not re-read])' % (v, VGSI_TYPE[v[0]], v, E['gpa'], E['tch'])},
                'reil': {'present': bool(E['reil']), 'src': 'obs', 'refs': ['nasr', 'cs'], 'evidence': 'NASR RWY_END_LGTS_FLAG %r; CS lists REIL for 10R and 28L' % ne.get('RWY_END_LGTS_FLAG'),
                         'when_tower_closed': 'unavailable' if E['reil'] else None, 'when_tower_closed_evidence': sked_ev if E['reil'] else None},
                'ils': E['ils'],
                'traffic_pattern': traffic,
                'tpa_ft_msl': tpa[rw], 'tpa_ft_agl': tpa_agl[rw],
                'obstacle': ({'type': ne.get('OBSTN_TYPE'), 'hgt_ft': ne.get('OBSTN_HGT'), 'dist_from_thr_ft': ne.get('DIST_FROM_THR'),
                              'cl_offset_ft': ne.get('CNTRLN_OFFSET'), 'cl_dir': ne.get('CNTRLN_DIR_CODE'), 'clearance_slope': ne.get('OBSTN_CLNC_SLOPE')}
                             if ne.get('OBSTN_TYPE') else None),
                'src': 'obs', 'refs': ['nasr'],
                'evidence': 'NASR APT_RWY_END %s (RWY_END_PSN_SOURCE %s %s); world x/z by hwd_frame.ll_to_world, y = RWY_END_ELEV x 0.3048' % (
                    e, ne.get('RWY_END_PSN_SOURCE'), ne.get('RWY_END_PSN_DATE'))})
        # distance-remaining signs (NASR remarks)
        drs = [t for t in RMK if 'DISTANCE REMAINING' in t and t.split()[1] in (a, b)]
        edge = {'2024': rwy_edges.measure(N24, rw), '2022': rwy_edges.measure(N22, rw)}
        o = osm_rw.get(rw, {}).get('wgs84', {})
        outline = runway_poly(rw)
        out.append({
            'id': rw, 'ends': ends, 'length_m': r2(A['length']), 'length_ft_nasr': D['lenFt'], 'width_ft': D['widthFt'], 'width_m': r2(D['widthFt'] * FT),
            'surface': D['surface'], 'treatment': D['treatment'], 'cond': D['cond'],
            'edge_lights': {'type': 'MIRL' if D['lights'] == 'MED' else D['lights'], 'src': 'obs', 'refs': ['nasr', 'cs'],
                            'evidence': 'NASR RWY_LGT_CODE MED (medium intensity); CS "MIRL"; when the tower is closed MIRL 10R/28L preset low, pilot-controlled on CTAF; 10L/28R closed (NASR remarks)',
                            'when_tower_closed': ('preset low intensity; pilot-controlled on CTAF' if rw == '10R/28L' else 'runway closed'),
                            'when_tower_closed_evidence': sked_ev + ('' if rw == '10R/28L' else '; NASR remark "WHEN ATCT CLSD RWY 10L/28R CLSD."')},
            'closed_when_tower_closed': rw == '10L/28R',
            'strength_klb': strength[rw], 'gradient': grad[rw],
            'distance_remaining_signs': drs,
            'outline': {'ring': ring(outline), 'src': 'obs', 'refs': ['nasr', 'naip2024', 'naip2022', 'osm', 'ac5340'],
                        'evidence': {'rule': 'rectangle from the NASR ends (end-to-end, incl. displaced thresholds) and NASR RWY_WIDTH; AC 150/5340-1M para 2.8: the outer edges of the white edge stripes lie on the edge of the usable runway',
                                     'naip_edge_stripes': edge,
                                     'osm': {'way': osm_rw.get(rw, {}).get('osm_id'), 'across_mean_m': o.get('across_mean'), 'across_max_m': o.get('across_max_abs'),
                                             'end_residual_m': {k: v.get('dist') for k, v in o.get('ends', {}).items()},
                                             'width_tag_m': osm_rw.get(rw, {}).get('tags', {}).get('width'),
                                             'note': ('OSM way ends at the 28L displaced threshold (202 m short of the NASR 28L end); not used for the outline' if rw == '10R/28L' else 'OSM centreline only (no area); not used for the outline')}}},
            'src': 'obs', 'refs': ['nasr', 'cs'],
            'evidence': 'NASR APT_RWY %s (RWY_LEN %d ft, RWY_WIDTH %d ft, %s %s); CS "RWY %s: H%dX%d"' % (rw, D['lenFt'], D['widthFt'], D['surface'], D['treatment'], rw.replace('/', '–'), D['lenFt'], D['widthFt']),
        })
    return out


# ================================================================================================== 3. taxiways / taxilanes
def holds_osm():
    return [(h['osm']['id'], h['w'][0]) for h in FE['holding_position']]


def snap_way(N, w, hold_pts):
    """measure the yellow centreline paint along an OSM way (NAIP 2024) and move it locally onto the paint"""
    P = densify(w['w'], 2.0); S = arclen(P); T = tangents(P)
    if S[-1] < 8.0:
        return P, {'stations': 0, 'faint': {}}
    ss = np.arange(0.0, S[-1] + 1e-9, ST_STEP)
    offs = np.full(len(ss), np.nan); foffs = np.full(len(ss), np.nan); bst = []; faint = []
    for i, s_ in enumerate(ss):
        p = np.array([np.interp(s_, S, P[:, 0]), np.interp(s_, S, P[:, 1])])
        t = np.array([np.interp(s_, S, T[:, 0]), np.interp(s_, S, T[:, 1])]); t /= max(1e-9, np.hypot(*t))
        if RWY_MASK.contains(Point(p)) or any(math.hypot(p[0] - h[0], p[1] - h[1]) < HOLD_MASK_M for h in hold_pts):
            offs[i] = np.inf; foffs[i] = np.inf; continue
        r = N.cross_peak(p, t, half=HALF, avg=AVG, step=0.1, min_contrast=FAINT_C)
        if r and r[2] < AMB * r[1]:
            faint.append(r[0])
            b = N.bstar(p, t, r[0], AVG)
            if b >= FAINT_BSTAR_MIN: foffs[i] = r[0]
            if r[1] >= MIN_C:
                bst.append(b)
                if b >= BSTAR_MIN: offs[i] = r[0]
    corr = window_corr(ss, offs)
    # faint-paint snap: sections (or the whole way) whose yellow faint ridges agree on an offset
    secs = faint_sections(ss, foffs)
    whole = faint_whole(foffs)
    qual = np.zeros(len(ss), bool)
    for q in secs:
        if q['offset']: qual |= (ss >= q['s0_m']) & (ss < q['s0_m'] + FAINT_SEC_M)
    if whole: qual[:] = True
    fsnap = None
    if qual.any() and not np.any(corr):
        fo = np.where(qual & ~np.isnan(foffs) & ~np.isinf(foffs), foffs, np.nan); fo[np.isinf(offs)] = np.inf
        corr = window_corr(ss, fo, strict_big=False)
        fsnap = {'rule': 'faint yellow ridges (>= %.0f DN, b* >= %.0f) consistent over %s: |median| >= %.1f m, IQR <= %.1f m, n >= %d per %.0f m section (or n >= %d over the way); window_corr without the strict rule for > 1.5 m' % (
                     FAINT_C, FAINT_BSTAR_MIN, 'the whole way' if whole else 'the sections marked offset', FAINT_MED_MIN, FAINT_IQR_MAX, FAINT_SEC_N, FAINT_SEC_M, FAINT_WAY_N),
                 'whole_way': bool(whole), 'stations_used': int((~np.isnan(fo) & ~np.isinf(fo)).sum()),
                 'residual_after_snap_m': r2(np.median(np.abs(foffs[qual & ~np.isnan(foffs)] - corr[qual & ~np.isnan(foffs)]))) if (qual & ~np.isnan(foffs)).any() else None}
    c = np.interp(S, ss, corr); Nrm = np.stack([-T[:, 1], T[:, 0]], 1)
    Q = P + Nrm * c[:, None]
    paint = ~np.isnan(offs) & ~np.isinf(offs)
    resid_secs = faint_sections(ss, foffs - corr)
    st = {'stations': int(len(ss)), 'masked': int(np.isinf(offs).sum()), 'paint': int(paint.sum()),
          'median_abs_offset_m': r2(np.median(np.abs(offs[paint]))) if paint.any() else None,
          'residual_after_snap_m': r2(np.median(np.abs(offs[paint] - corr[paint]))) if paint.any() else None,
          'snapped_len_m': r1(np.sum(np.diff(S)[(np.abs(c[:-1]) > 0) | (np.abs(c[1:]) > 0)])) if len(S) > 1 else 0.0,
          'max_shift_m': r2(np.max(np.abs(corr))) if len(corr) else 0.0, 'end_shift_m': [r2(c[0]), r2(c[-1])], 'bstar': bst,
          'faint': {'n': len(faint), 'median_offset_m': r2(np.median(faint)) if faint else None,
                    'iqr_m': [r2(v) for v in np.percentile(faint, [25, 75])] if len(faint) >= 4 else None,
                    'yellow_n': int((~np.isnan(foffs) & ~np.isinf(foffs)).sum()), 'sections': secs, 'whole_way_offset': whole,
                    'snap': fsnap, 'sections_after_snap': resid_secs,
                    'offset_left_after_snap': [q for q in resid_secs if q['offset']]}}
    return Q, st


def faint_sections(ss, fo):
    """per FAINT_SEC_M section with >= FAINT_SEC_N yellow faint ridges: median offset, IQR, and whether that counts
    as an offset (|median| >= FAINT_MED_MIN and IQR <= FAINT_IQR_MAX)"""
    out = []
    if not len(ss): return out
    for s0 in np.arange(0.0, ss[-1] + 1e-9, FAINT_SEC_M):
        m = (ss >= s0) & (ss < s0 + FAINT_SEC_M) & ~np.isnan(fo) & ~np.isinf(fo)
        if m.sum() < FAINT_SEC_N: continue
        q = np.percentile(fo[m], [25, 50, 75])
        out.append({'s0_m': r1(s0), 'n': int(m.sum()), 'median_m': r2(q[1]), 'iqr_m': r2(q[2] - q[0]),
                    'offset': bool(abs(q[1]) >= FAINT_MED_MIN and q[2] - q[0] <= FAINT_IQR_MAX)})
    return out


def faint_whole(fo):
    v = fo[~np.isnan(fo) & ~np.isinf(fo)]
    if len(v) < FAINT_WAY_N: return False
    q = np.percentile(v, [25, 50, 75])
    return bool(abs(q[1]) >= max(1.5, FAINT_MED_MIN) and q[2] - q[0] <= FAINT_IQR_MAX)


def grey_width(N, pts):
    """NAIP 2024 pavement width across a way: grey-test cross profiles every GREY_STEP m (method of
    tools/plot_overlays.py naip_measure (a), Phase 1 cross-check); stations within 40 m of a runway or inside an OSM apron
    are skipped. Returns {'n', 'median', 'iqr'} or None."""
    from scipy import ndimage as nd_
    L = LineString(pts); n = int(L.length / GREY_STEP); lat = np.arange(-30.0, 30.01, 0.3); wids = []
    for i in range(1, n):
        s_ = i * GREY_STEP; p = np.array(L.interpolate(s_).coords[0])
        q = np.array(L.interpolate(min(L.length, s_ + 0.5)).coords[0]) - np.array(L.interpolate(max(0, s_ - 0.5)).coords[0])
        t = q / max(np.hypot(*q), 1e-9); nr = np.array([-t[1], t[0]])
        if RWY_NEAR.contains(Point(p)) or APRON_ALL.contains(Point(p)): continue
        X = p[0] + nr[0] * lat; Z = p[1] + nr[1] * lat
        R_, G_, B_ = (N.sample(X, Z, k) for k in 'RGB'); mx = np.maximum(np.maximum(R_, G_), B_); mn = np.minimum(np.minimum(R_, G_), B_)
        pav = ((mx - mn) / np.maximum(mx, 1) < SAT_MAX) & (G_ - (R_ + B_) / 2 < EG_MAX)
        pav = nd_.binary_closing(np.r_[False, pav, False], structure=np.ones(6, bool))[1:-1]
        k0 = len(lat) // 2
        if not pav[k0]:
            cand = [k for k in range(k0 - 5, k0 + 6) if pav[k]]
            if not cand: continue
            k0 = min(cand, key=lambda k: abs(k - len(lat) // 2))
        a = k0
        while a > 0 and pav[a - 1]: a -= 1
        b = k0
        while b < len(lat) - 1 and pav[b + 1]: b += 1
        if a == 0 or b == len(lat) - 1: continue
        wd = lat[b] - lat[a] + 0.3
        if 6.0 <= wd <= 35.0: wids.append(wd)
    if not wids: return None
    return {'n': len(wids), 'median': r1(np.median(wids)), 'iqr': r1(np.subtract(*np.percentile(wids, [75, 25])))}


def simplify(Q, tol=0.05):
    L = LineString([tuple(p) for p in Q]).simplify(tol, preserve_topology=False)
    return [xz(p) for p in L.coords]


def taxiways(N):
    hp = [h for _, h in holds_osm()]
    rmk_a = [t for t in RMK if t.startswith('TWY A NOT VSB')]
    out = {'taxiway': [], 'taxilane': []}; allb = []
    for kind in ('taxiway', 'taxilane'):
        for w in sorted(FE[kind], key=lambda e: e['osm']['id']):
            tags = w['tags']; ref = tags.get('ref'); status = w.get('status', 'open') if kind == 'taxiway' else ('abandoned' if tags.get('abandoned') == 'yes' else ('disused' if tags.get('disused') == 'yes' else 'open'))
            Q, st = snap_way(N, w, hp); allb += st.pop('bstar', [])
            e = {'id': 'osm:way/%d' % w['osm']['id'], 'kind': kind, 'ref': ref, 'status': status,
                 'pts': simplify(Q), 'len_m': r1(w['len_m']),
                 'src': 'obs', 'refs': ['osm', 'naip2024'],
                 'evidence': {'osm': {'id': w['osm']['id'], 'version': w['osm']['version'], 'tags': tags},
                              'naip_paint': st,
                              'geometry': (('OSM centreline moved locally onto the faint NAIP 2024 yellow centreline paint (consistent faint ridges, see naip_paint.faint.snap)' if st['faint'].get('snap') else
                                            'OSM centreline moved locally onto the NAIP 2024 yellow centreline paint where the evidence is clear (window_corr rule)') if st.get('snapped_len_m') else
                                           ('OSM centreline unchanged, but its faint NAIP paint shows a consistent offset (naip_paint.faint.offset_left_after_snap) [flag]' if st['faint'].get('offset_left_after_snap') else
                                            'OSM centreline unchanged (no clear NAIP paint offset)'))}}
            if ref:
                e['ref_check'] = {'al5015': ref in AL5015_TWYS, 'src': 'obs', 'refs': ['osm', 'al5015'],
                                  'evidence': 'OSM ref %r %s the AL-5015 2611 taxiway labels %s' % (ref, 'is among' if ref in AL5015_TWYS else 'is NOT among', AL5015_TWYS)}
                e['ref_src'] = 'inf' if w['osm']['id'] in REF_DIAGRAM else 'obs'
                e['ref_note'] = REF_DIAGRAM.get(w['osm']['id'], 'OSM ref; AL-5015 prints this designation along the taxiway (tools/check_airport.py check 3 maps every AL-5015 taxiway label to the nearest OSM way)')
            L_ = LineString(e['pts']); ins = {rw: L_.intersection(pg).length for rw, pg in sorted(RWY_POLY.items())}
            rw_ = max(ins, key=ins.get)
            if ins[rw_] > 1.0:
                e['on_runway'] = {'runway': rw_, 'len_m': r1(ins[rw_]), 'share': r2(ins[rw_] / max(L_.length, 1e-6)), 'runway_overlap': bool(ins[rw_] >= 50.0),
                                  'src': 'obs', 'refs': ['nasr', 'osm'],
                                  'evidence': 'length of the way inside the NASR runway rectangle; runway_overlap = more than 50 m inside (more than a crossing of the 45.7 m wide runway: a lead-on / lead-off loop or a runway-aligned segment that OSM tags taxiway); Phase 2 taxi graph: treat that part as runway'}
            gw = grey_width(N, e['pts']) if status == 'open' else None
            e['width'] = {'naip_grey_width_m': gw and gw['median'], 'naip_grey_iqr_m': gw and gw['iqr'], 'naip_stations': gw['n'] if gw else 0,
                          'naip_src': 'obs' if gw and gw['n'] >= 5 else None,
                          'naip_note': 'pavement width by the grey test (saturation < %.2f, excess green < %.0f; build SAT_MAX / EG_MAX) on cross profiles every %.0f m, skipping stations within 40 m of a runway or inside an apron; paved shoulders of the same grey are included and concrete that reads tan is missed; null when fewer than 5 stations measured' % (SAT_MAX, EG_MAX, GREY_STEP),
                          'default_m': r2(TWY_WIDTH_DEFAULT[kind]), 'default_src': 'inf',
                          'default_basis': 'AC 150/5300-13B Chg 1 Table 4-2: %s; the TDG of this way is not known (default, not measured)' % ('TDG 2A/2B 35 ft (10.7 m)' if kind == 'taxiway' else 'TDG 1A/1B 25 ft (7.6 m)')}
            if ref in WINGSPAN_LIMIT:
                e['max_wingspan_ft'] = WINGSPAN_LIMIT[ref][0]; e['max_wingspan_m'] = r2(WINGSPAN_LIMIT[ref][0] * FT)
                e['restriction'] = {'text': WINGSPAN_LIMIT[ref][1], 'src': 'obs', 'refs': ['nasr', 'cs']}
            if ref == 'A' and rmk_a:
                e['remark'] = {'text': rmk_a[0], 'src': 'obs', 'refs': ['nasr', 'cs', 'al5015']}
            if status != 'open':
                e['status_evidence'] = 'OSM tag %s=yes' % status + ('; AL-5015 draws "Closed Surface" x marks on this pavement (khwd_osm_xcheck.json, topological match)' if w['osm']['id'] in (1366756208, 289829582) else '; AL-5015 shows no closed marks here [G1]')
            out[kind].append(e)
    return out['taxiway'], out['taxilane'], allb


# ================================================================================================== 4. aprons
# OSM apron -> the AL-5015 labels that name it: (text, pdf_pt of the label [identifies which of the three FBO RAMP], how)
# how = 'text' : a label without a leader, matched by where its text is printed (overlap of its text boxes with the apron
#                polygons is computed and written to the evidence; the diagram is registered to < 1 m since the
#                2026-11-12 fix of the 28R bar end, docs/phase1_crosscheck.md)
#       other  : the label's leader / arrow, read by eye on the registered diagram (out/phase1/overlay_al5015.png)
APRON_AL5015 = {
    246152866: [('GA TRANSIENT RAMP', (129.6, 302.3), 'text')],
    289829587: [('FBO RAMP', (198.5, 146.6), 'leader arrow of the north-east "FBO RAMP" ends inside the polygon (read by eye on the registered diagram)')],
    1366756209: [('FBO RAMP', (277.0, 255.1), 'leader arrow of the south "FBO RAMP" ends inside the polygon (read by eye on the registered diagram)')],
    1366760487: [('28L RUN-UP', (276.1, 99.9), 'leader arrow ends inside the polygon (read by eye on the registered diagram); OSM names it too')],
    1366756195: [('WEST HANGARS', (70.7, 334.6), 'text'), ('FBO RAMP', (95.3, 309.9), 'text')],
}
# GA TRANSIENT RAMP: the text straddles the Green Ramp and the OSM "Helicopter Ramp" (overlaps in the evidence). It is
# matched to the Green Ramp [inf]: the Helicopter Ramp is named by OSM and is the helipad area of the NASR remark
# ("transient helicopter tfc use helipads west of green ramp"), and the Green Ramp is the only apron with tie-down tees
# (NASR: transient tie-downs available). The west "FBO RAMP" text is printed inside apron 1366756195 (the West Hangars
# apron, OSM name=air), between the west box hangars: it names a part of that polygon, so no polygon is called
# "FBO Ramp (west)" (G5 had put that name on apron 1372203784 with the sheared affine; that apron carries no label).
APRON_TEXT_OVERLAP_MIN = 0.02     # report text overlaps of at least 2 % of the label's text area

FBO_QUAL = {'osm:way/289829587': 'FBO Ramp (north-east)', 'osm:way/1366756209': 'FBO Ramp (south)'}
# AL-5015 prints "FBO RAMP" three times; the qualifiers (north-east / south) are ours, from where each label points;
# the third (west) one names a part of the West Hangars apron (see above) and gives no polygon name


def _label(labels, text, pdf_pt):
    hit = [l for l in labels if l['text'] == text and abs(l['pdf_pt'][0] - pdf_pt[0]) < 0.2 and abs(l['pdf_pt'][1] - pdf_pt[1]) < 0.2]
    assert len(hit) == 1, 'AL-5015 label %r at %s not found' % (text, pdf_pt)
    return hit[0]


def _text_overlaps(l):
    """share of the label's text area (union of its word / glyph boxes in the world) that falls in each OSM apron"""
    tb = unary_union([Polygon(b) for b in l['boxes_xz']])
    ov = [(tb.intersection(Polygon(a['w'])).area / tb.area, a['osm']['id']) for a in FE['apron']]
    return sorted([(round(f, 2), oid) for f, oid in ov if f >= APRON_TEXT_OVERLAP_MIN], reverse=True)


def aprons(labels):
    out = []
    lab = {l['text']: l for l in labels}
    for a in sorted(FE['apron'], key=lambda e: e['osm']['id']):
        t = a['tags']; oid = a['osm']['id']
        nm = t.get('name') or t.get('ref'); note = None
        if nm == 'air':
            note = 'OSM name=air (way %d) is not a ramp name (data quality, G1); not used' % oid; nm = None
        als = []
        for text, pt, how in APRON_AL5015.get(oid, []):
            l = _label(labels, text, pt)
            if how == 'text':
                ov = _text_overlaps(l)
                assert oid in [k for _, k in ov], 'AL-5015 label %r: text does not overlap apron %d: %s' % (text, oid, ov)
                how = 'no leader; matched by where the label text is printed on the registered diagram: %s of the text area lies in OSM apron(s) %s%s' % (
                    ' / '.join('%d %%' % round(100 * f) for f, _ in ov), ' / '.join(str(k) for _, k in ov),
                    '' if ov[0][1] == oid else ' - ambiguous, this apron is not the largest share; see the build_airport.py note on GA TRANSIENT RAMP [inf]')
            als.append({'text': text, 'pdf_pt': list(pt), 'how': how, 'src': 'inf', 'refs': ['al5015']})
        al = als[0] if als else None
        name = nm or FBO_QUAL.get('osm:way/%d' % oid) or (al['text'].title() if al and al['text'] != 'WEST HANGARS' else None)
        e = {'id': 'osm:way/%d' % oid, 'name': name, 'osm_name': t.get('name'), 'osm_ref': t.get('ref'),
             'al5015_label': al, 'al5015_labels_more': als[1:] or None,
             'name_src': ('osm' if nm else ('al5015 label + own qualifier (north-east / south) [inf]' if 'osm:way/%d' % oid in FBO_QUAL else None)),
             'ring': ring(a['w'][:-1]), 'area_m2': r1(a['area_m2']), 'surface': t.get('surface'),
             'src': 'obs', 'refs': ['osm'] + (['al5015'] if al else []),
             'evidence': 'OSM aeroway=apron way %d v%d%s' % (oid, a['osm']['version'], ('; ' + note) if note else '')}
        if oid == 246152866:
            e['remark'] = {'text': [t_ for t_ in RMK if 'GREEN RAMP' in t_][0], 'src': 'obs', 'refs': ['nasr', 'cs'],
                           'note': 'NASR / CS name a "green ramp"; OSM ref Green Ramp; the AL-5015 label GA TRANSIENT RAMP is taken for this ramp [inf] (its text also overlaps the OSM Helicopter Ramp, see al5015_label)'}
        out.append(e)
    return out


# ================================================================================================== 5. holding positions
def holds(N):
    ways = [w for k in ('taxiway', 'taxilane') for w in sorted(FE[k], key=lambda e: e['osm']['id'])]
    out = []
    for hid, h in sorted(holds_osm()):
        cand = [w for w in ways if min(math.hypot(p[0] - h[0], p[1] - h[1]) for p in w['w']) < 0.3]
        rw = min(sorted(F.RWY_DATA), key=lambda k: RWY_POLY[k].distance(Point(h)))
        al, ac = F.rwy_along_across(rw.split('/')[0], *h)
        e = {'id': 'osm:node/%d' % hid, 'x': r2(h[0]), 'z': r2(h[1]), 'runway': rw, 'runway_rule': 'nearest NASR runway rectangle',
             'along_m': r1(al), 'cl_dist_m': r1(abs(ac)), 'cl_dist_ft': round(abs(ac) / FT), 'dist_to_runway_m': r1(RWY_POLY[rw].distance(Point(h))),
             'way': ('osm:way/%d' % cand[0]['osm']['id']) if cand else None, 'ref': None, 'bar': None, 'src': 'obs', 'refs': ['osm']}
        ev = ['OSM aeroway=holding_position node %d (no ref tag)' % hid]
        if cand:
            w = cand[0]; e['twy_ref'] = w['tags'].get('ref')
            P = densify(w['w'], 1.0); S = arclen(P); T = tangents(P)
            k = int(np.argmin(np.hypot(*(P - np.array(h)).T))); s0 = S[k]
            lad = find_ladder(N, P, T, S, max(0.0, s0 - HOLD_SEARCH), min(S[-1], s0 + HOLD_SEARCH), half_w=4.0)
            if lad and lad['contrast'] >= HOLD_MIN_C and lad['second'] < 0.6 * lad['contrast']:
                s = lad['s']; p = np.array([np.interp(s, S, P[:, 0]), np.interp(s, S, P[:, 1])])
                t = np.array([np.interp(s, S, T[:, 0]), np.interp(s, S, T[:, 1])]); t /= np.hypot(*t)
                n = np.array([-t[1], t[0]]); sk = math.tan(math.radians(lad['skew_deg']))
                bdir = n + t * sk; bdir /= np.hypot(*bdir)
                e['bar'] = {'x': r2(p[0]), 'z': r2(p[1]), 'dir': [round(float(bdir[0]), 4), round(float(bdir[1]), 4)],
                            'offset_from_osm_m': r2(s - s0), 'contrast': r1(lad['contrast']), 'second': r1(lad['second']),
                            'skew_deg': lad['skew_deg'], 'depth_m': r2(7 * FT), 'src': 'obs', 'refs': ['naip2024', 'ac5340'],
                            'evidence': 'centre of the 7 ft yellow band (AC 150/5340-1M para 3.3.4.1 Pattern A, 12 in lines) found on NAIP 2024 along the taxiway'}
                e['x'], e['z'] = r2(p[0]), r2(p[1]); e['src'] = 'obs'; e['refs'] = ['osm', 'naip2024']
                al, ac = F.rwy_along_across(rw.split('/')[0], *p); e['along_m'] = r1(al); e['cl_dist_m'] = r1(abs(ac)); e['cl_dist_ft'] = round(abs(ac) / FT)
                e['dist_to_runway_m'] = r1(RWY_POLY[rw].distance(Point(p)))
                ev.append('bar measured on NAIP 2024 %.2f m along the taxiway from the OSM node' % (s - s0))
            else:
                ev.append('no clear NAIP 2024 bar (contrast %s)' % (r1(lad['contrast']) if lad else None))
        e['evidence'] = '; '.join(ev)
        out.append(e)
    return out


# ================================================================================================== 6. hot spots
def hotspots(hs_geo):
    desc = CS['hot_spots']['HWD']
    tw = [(w['tags'].get('ref'), LineString(w['w'])) for w in FE['taxiway'] if w['tags'].get('ref')]
    out = []
    by = defaultdict(list)
    for h in hs_geo: by[h['hs']].append(h)
    for hs in sorted(desc):
        parts = by.get(hs, [])
        for i, g in enumerate(parts):
            pg = Polygon(g['ring']); refs_in = sorted({r for r, l in tw if l.intersects(pg)})
            out.append({'id': '%s%s' % (hs.replace(' ', ''), '' if len(parts) == 1 else 'abc'[i]), 'hs': hs, 'text': desc[hs],
                        'ring': g['ring'], 'centre': g['centre'], 'area_m2': g['area_m2'],
                        'taxiways_inside_osm': refs_in, 'src': 'inf', 'refs': ['al5015', 'cs', 'osm'],
                        'evidence': 'brown hot-spot ellipse of AL-5015 2611 (equal-moment ellipse of the filled ring, %d px at %d dpi, diagram centre px %s) mapped by the 4-point affine of the diagram to the NASR runway ends (residuals %s m; chart accuracy +-600 ft); text from the CS hot spot list; OSM taxiway refs inside the ellipse: %s' % (g['n_fill'], al5015.DPI, g['centre_px'], FIT_RES_TXT, ', '.join(refs_in) or 'none')})
        if not parts:
            out.append({'id': hs.replace(' ', ''), 'hs': hs, 'text': desc[hs], 'ring': None, 'src': 'inf', 'refs': ['cs'], 'evidence': 'not found on AL-5015'})
    return out


# ================================================================================================== 7. helipads, hangars, buildings
def helipads():
    rmk = [t for t in RMK if 'HELIPAD' in t]
    out = []
    for h in sorted(FE['helipad'], key=lambda e: e['osm']['id']):
        pg = Polygon(h['w']); c = pg.centroid; mrr = pg.minimum_rotated_rectangle; xs, zs = mrr.exterior.coords.xy
        side = sorted(math.hypot(xs[i + 1] - xs[i], zs[i + 1] - zs[i]) for i in range(2))
        out.append({'id': 'osm:way/%d' % h['osm']['id'], 'x': r2(c.x), 'z': r2(c.y), 'ring': ring(h['w'][:-1]), 'area_m2': r1(h['area_m2']),
                    'size_m': r1(side[0]), 'src': 'obs', 'refs': ['osm'],
                    'evidence': 'OSM aeroway=helipad way %d v%d' % (h['osm']['id'], h['osm']['version']),
                    'remark': {'text': rmk[0] if rmk else None, 'src': 'obs', 'refs': ['nasr', 'cs']}})
    return out


def hangar_kind(pg):
    mrr = pg.minimum_rotated_rectangle; xs, zs = mrr.exterior.coords.xy
    s = [math.hypot(xs[i + 1] - xs[i], zs[i + 1] - zs[i]) for i in range(2)]
    w, l = min(s), max(s); i = 0 if s[0] >= s[1] else 1
    hdg = F.vec_hdg(xs[i + 1] - xs[i], zs[i + 1] - zs[i]) % 180
    fill = pg.area / mrr.area
    kind = 't_hangar_row' if (l / w >= 3.0 and w <= 22.0 and fill >= 0.85) else 'box_hangar'
    return kind, w, l, hdg, fill


def edges_near(poly, d):
    pp = prep(poly.buffer(d)); return [e for e in STAYS['signal_edges'] if pp.contains(Point(e['x'], e['z']))]


def hangars():
    out = []
    for h in sorted(FE['hangar'], key=lambda e: e['osm']['id']):
        pg = Polygon(h['w']).buffer(0); t = h['tags']; nm = t.get('name')
        kind, w, l, hdg, fill = hangar_kind(pg)
        letter = None
        if nm and (nm.startswith('Hangar ') or nm.startswith('Hanagar ')):
            letter = nm.split(' ', 1)[1]
        fbo = nm in ('APP Jet Center', 'Signature Aviation')
        ed = edges_near(pg, 8.0)
        out.append({'id': 'osm:way/%d' % h['osm']['id'], 'name': ('Hangar K' if nm == 'Hanagar K' else nm), 'osm_name': nm, 'letter': letter,
                    'ring': ring(h['w'][:-1]), 'area_m2': r1(h['area_m2']), 'addr': ' '.join(filter(None, [t.get('addr:housenumber'), t.get('addr:street')])) or None,
                    'kind': kind, 'kind_src': 'inf',
                    'kind_evidence': 'footprint: minimum rectangle %.1f x %.1f m (ratio %.1f, fill %.2f); rule: t_hangar_row if ratio >= 3, width <= 22 m and fill >= 0.85, else box_hangar; OSM tags only building=hangar. Doors are not visible on NAIP 2024 / 2022 at 0.6 m (refs/cache/naip/naip_visual_notes.json): no door rhythm' % (w, l, l / w, fill),
                    'long_axis_hdg': r1(hdg), 'width_m': r1(w), 'length_m': r1(l),
                    'role': ('fbo' if fbo else None), 'role_src': ('inf' if fbo else None),
                    'role_evidence': ('OSM name %r is an FBO business name; FBO names are not verified against a current source (PLAN: the city map names APP Jet Center and Meridian Hayward)' % nm) if fbo else None,
                    'adsb_signal_edges_8m': len(ed),
                    'src': 'obs', 'refs': ['osm'] + (['adsb'] if ed else []),
                    'evidence': 'OSM aeroway=hangar way %d v%d%s%s' % (h['osm']['id'], h['osm']['version'],
                                                                         '; name typo "Hanagar K" read as Hangar K [inf]' if nm == 'Hanagar K' else '',
                                                                         '; %d adsb.lol signal starts/ends on the ground within 8 m (aircraft parked at / in it)' % len(ed) if ed else '')})
    return out


TERMINAL_TIP_PX = (690.0, 1479.0)
# AL-5015 2611 rasterised at 400 dpi (al5015.DPI): end pixel of the leader of the TERMINAL/AIRPORT ADMINISTRATION label
# (lowest pixel of the connected black line component, max channel < 110, in the window x 660-740, y 1290-1500;
# measured 2026-11-12 in the Phase 1 cross-check, docs/phase1_crosscheck.md). The search window was chosen by eye around
# the leader; the end pixel inside it is a measurement. The building nearest to it in the world
# (through the diagram affine) is taken as the terminal / administration building [inf].
TERMINAL_MARGIN = 1.5   # the nearest OSM building must be at least this factor closer than any other footprint [chosen]
FIRE_BLOCK_XZ = (298.0, 584.0)   # centre of the AL-5015 FIRE STATION building block in the world frame, read on the
                                 # registered diagram in the Phase 1 cross-check (by eye, +-5 m; docs/phase1_crosscheck.md #9)


def buildings(labels, M):
    lab = {l['text']: l for l in labels}
    out = []
    tip = al5015.px_to_world(M, *TERMINAL_TIP_PX)[0]
    fps = [(Polygon(b['w']).distance(Point(*tip)), b['osm']['id']) for b in FE['building'] + FE['control_tower'] + FE['hangar'] if len(b.get('w', [])) > 3]
    fps.sort()
    assert fps[1][0] >= TERMINAL_MARGIN * fps[0][0] and fps[0][1] in {b['osm']['id'] for b in FE['building']}, 'terminal leader: %s' % fps[:3]
    term_id = fps[0][1]
    term_ev = ('AL-5015 label TERMINAL/AIRPORT ADMINISTRATION: its leader ends at world [%.1f, %.1f] (diagram affine, residuals %s m), %.1f m from this OSM footprint; next nearest: OSM way %d at %.1f m, way %d at %.1f m [inf: the leader end read on the raster, the building by proximity]'
               % (tip[0], tip[1], FIT_RES_TXT, fps[0][0], fps[1][1], fps[1][0], fps[2][1], fps[2][0]))
    tw = FE['control_tower'][0]; pg = Polygon(tw['w'])
    out.append({'id': 'osm:way/%d' % tw['osm']['id'], 'kind': 'control_tower', 'name': 'Hayward ATCT', 'ring': ring(tw['w'][:-1]),
                'height_m': float(tw['tags']['height']) if 'height' in tw['tags'] else None, 'addr': '20301 Skywest Drive',
                'beacon': {'colours': BASE.get('BCN_LENS_COLOR'), 'schedule': BASE.get('BCN_LGT_SKED'), 'src': 'inf', 'refs': ['nasr', 'al5015'],
                           'evidence': 'NASR BCN_LENS_COLOR WG / BCN_LGT_SKED SS-SR; AL-5015 draws the beacon symbol labelled TWR, which the TPP legend reserves for a beacon co-located with the tower (G1) - so the beacon is on the tower [inferred]'},
                'src': 'obs', 'refs': ['osm', 'nasr', 'al5015'],
                'evidence': 'OSM way %d building=yes, man_made=tower, service=aircraft_control, height=%s (no aeroway=control_tower); NASR ATC_BASE ATCT, TWR_OPERATOR_CODE F; AL-5015 "TWR" label at world %s (affine, %.0f m away)' % (
                    tw['osm']['id'], tw['tags'].get('height'), [lab['TWR']['x'], lab['TWR']['z']], pg.centroid.distance(Point(lab['TWR']['x'], lab['TWR']['z'])))})
    fs = FE['fire_station'][0]; P = Point(fs['w'][0])
    host = [b for b in FE['building'] if len(b.get('w', [])) > 3 and Polygon(b['w']).buffer(0).contains(P)]
    out.append({'id': 'osm:node/%d' % fs['osm']['id'], 'kind': 'fire_station', 'name': fs['tags'].get('name'), 'x': r2(P.x), 'z': r2(P.y),
                'ring': ring(host[0]['w'][:-1]) if host else None, 'ring_id': ('osm:way/%d' % host[0]['osm']['id']) if host else None,
                'src': 'obs', 'refs': ['osm', 'al5015'],
                'evidence': 'OSM node %d amenity=fire_station (USGS GNIS import), %.1f m outside the OSM aerodrome polygon; AL-5015 "FIRE STATION" label at world %s (affine, %.0f m away)%s' % (
                    fs['osm']['id'], fs['d_aerodrome_m'], [lab['FIRE STATION']['x'], lab['FIRE STATION']['z']], P.distance(Point(lab['FIRE STATION']['x'], lab['FIRE STATION']['z'])),
                    '; footprint = the OSM building containing the node (way %d) [inf]' % host[0]['osm']['id'] if host else '; no OSM building contains the node: point only'),
                'deviation': {'src': 'inf', 'refs': ['al5015', 'naip2024'], 'candidate_xz': list(FIRE_BLOCK_XZ),
                              'evidence': 'Phase 1 cross-check (docs/phase1_crosscheck.md section 4 #9): AL-5015 draws the FIRE STATION block (about 1,270 m2) at about world %s, where NAIP 2024 shows a building with solar panels (by eye); this OSM node (a GNIS import) lies %.0f m west of it and OSM maps no building there. The node is kept as mapped (obs); the station building is probably at the diagram block [inf]' % (list(FIRE_BLOCK_XZ), math.hypot(P.x - FIRE_BLOCK_XZ[0], P.y - FIRE_BLOCK_XZ[1]))}})
    for b in sorted(FE['building'], key=lambda e: e['osm']['id']):
        if not b.get('in_aerodrome') or len(b.get('w', [])) < 4: continue
        if host and b['osm']['id'] == host[0]['osm']['id']: continue
        e = {'id': 'osm:way/%d' % b['osm']['id'], 'kind': 'building', 'name': b['tags'].get('name'), 'ring': ring(b['w'][:-1]), 'area_m2': r1(b['area_m2']),
             'addr': ' '.join(filter(None, [b['tags'].get('addr:housenumber'), b['tags'].get('addr:street')])) or None,
             'src': 'obs', 'refs': ['osm'], 'evidence': 'OSM building=%s way %d inside the OSM aerodrome polygon; role unknown' % (b['tags'].get('building'), b['osm']['id'])}
        if b['osm']['id'] == term_id:
            e.update({'kind': 'terminal_admin', 'name': e['name'] or 'Terminal / Airport Administration', 'name_src': 'inf', 'name_evidence': term_ev,
                      'refs': ['osm', 'al5015'], 'evidence': 'OSM building=%s way %d inside the OSM aerodrome polygon (footprint); role from AL-5015, see name_evidence' % (b['tags'].get('building'), b['osm']['id'])})
        out.append(e)
    return out


HELI_AREA = (-110.0, -20.0, 160.0, 240.0)   # world x0, x1, z0, z1 around the unmapped helicopter pads south of 10R/28L
                                            # (by eye on NAIP 2024, out/phase1/g5/heli_s.png)


def markers():
    ws = FE['windsock'][0]
    return [{'id': 'osm:node/%d' % ws['osm']['id'], 'kind': 'windsock', 'x': r2(ws['w'][0][0]), 'z': r2(ws['w'][0][1]), 'lighted': BASE.get('WIND_INDCR_FLAG') == 'Y-L',
             'src': 'obs', 'refs': ['osm', 'nasr', 'naip2024'], 'evidence': 'OSM aeroway=windsock node %d; NASR WIND_INDCR_FLAG %s (lighted); NAIP 2024: windsock shadow at the centre of the segmented circle (by eye)' % (ws['osm']['id'], BASE.get('WIND_INDCR_FLAG'))},
            {'id': 'segmented_circle', 'kind': 'segmented_circle', 'x': r2(ws['w'][0][0]), 'z': r2(ws['w'][0][1]), 'diameter_m': 31.5,
             'diameter_src': 'inf', 'diameter_evidence': 'read by eye on a 0.1 m resampling of NAIP 2024 (+-1 m); the circle itself is obs (NASR flag, NAIP)',
             'position_src': 'inf', 'position_evidence': 'centred on the OSM windsock node (the windsock stands at the centre on NAIP 2024, by eye)',
             'src': 'obs', 'refs': ['nasr', 'naip2024'],
             'evidence': 'NASR SEG_CIRCLE_MKR_FLAG %s; NAIP 2024 shows a ring of red/white segments about 31.5 m across centred on the OSM windsock, with two L-shaped traffic-pattern indicators (diameter read by eye on a 0.1 m resampling, +-1 m)' % BASE.get('SEG_CIRCLE_MKR_FLAG')}]


def not_placed(labels, spots):
    heli_area = [s['id'] for s in spots if s['kind'] == 'helipad' and HELI_AREA[0] <= s['x'] <= HELI_AREA[1] and HELI_AREA[2] <= s['z'] <= HELI_AREA[3]]
    return [
        {'what': 'UL94 self-serve fuel island', 'src': 'obs', 'refs': ['nasr', 'cs'], 'evidence': 'NASR FUEL_TYPES 100LL,A,UL94 and remark "AVBL AT SELF-SERVE ISLAND"; CS "UL94 fuel avbl at self-serve island"',
         'why_not_placed': 'no source locates it: OSM has no aviation fuel feature (the 4 OSM amenity=fuel are road filling stations 37-801 m outside the aerodrome), AL-5015 does not draw it, NAIP not interpreted for it'},
        {'what': 'paved helicopter area with four square pads south of runway 10R/28L, around x -60, z 200', 'src': 'obs', 'refs': ['naip2024', 'adsb'],
         'evidence': 'NAIP 2024 (read by eye on a 0.15 m resampling, out/phase1/g5/heli_s.png): a paved area with four light square pads and a parked helicopter; adsb.lol helicopter stays there (parking spots %s sit on it - ids generated at build time; G4: helicopter ground events cluster on unmapped hard surface south of 10R/28L)' % (' / '.join(heli_area) or 'none'),
         'why_not_placed': 'not mapped in OSM (no polygon or helipad); the pads are not digitised here - candidates for an OSM edit or a NAIP digitisation in Phase 2'},
        {'what': 'transient tie-downs (designation)', 'src': 'obs', 'refs': ['nasr'], 'evidence': 'NASR TRNS_STRG_TIE_FLAG Y',
         'why_not_placed': 'no official tie-down numbering found (PLAN Q3); spots below are labelled by zone (D3)'},
    ]


# ================================================================================================== 8. parking spots
def adg_of(span_m):
    for k in ('I', 'II', 'III'):
        if span_m <= ADG_SPAN[k] + 1e-9: return k
    return 'IV+'


def type_span(t):
    g = GATYPES.get(t)
    if not g: return None
    return max(v for v in (g.get('wingspan_m'), g.get('wingspan_winglets_m')) if v is not None) if (g.get('wingspan_m') or g.get('wingspan_winglets_m')) else None


MERGE_TD = 6.0      # m: an ADS-B spot / signal-edge cluster / NAIP blob within this of a tie-down joins it (half the 12.15 m pitch)
MERGE_RAMP = 8.0    # m: candidate ramp spots within this of an existing spot join it (ADS-B spot radius p90 4.1 m, G4)
BIG_SPAN = 15.0     # m: around an ADS-B spot where a type wider than this parked, the merge radius is half its span + 2 m [chosen]
EDGE_LINK = 4.0     # m: single-linkage radius of the signal-edge clusters [chosen: about the ADS-B fix noise p90 on the ground]
EDGE_MIN, EDGE_MIN_HGR = 3, 2   # edges per cluster (on aprons / within HGR_D m of a hangar outline) [chosen]
HGR_D = 10.0        # m: a signal-edge cluster this close to a hangar outline belongs to that hangar [chosen: a wing half-span
                    # plus the antenna offset; sensitivity not tested]
AC_EXT_MIN = 8.0    # m: a NAIP 2024 aircraft blob becomes a candidate only with an extent >= 8 m [chosen: smaller than a GA
                    # single's span; it does NOT reject vehicles (box trucks reach 12.6 m, Phase 1 review) - the by-eye
                    # review NAIP_REVIEW does]
PAVE_TWY = 7.5      # m: pavement test - half of a 50 ft (TDG 3) taxiway, AC 150/5300-13B Table 4-2 (generous for HWD)
SAT_MAX, EG_MAX = 0.16, 8.0   # NAIP 2024 grey test (read on this mosaic: aprons 0.04-0.14 saturation, grass 0.19-0.36)
LANE_M = 4.0        # m: candidates this close to an open OSM taxiway / taxilane centreline are stops, not parking [chosen:
                    # half a TDG 1 taxilane, AC 150/5300-13B Table 4-2 (25 ft)]
# ---- added in answer to the Phase 1 review (2026-11-12)
NAIP_REVIEW = 'refs/cache/naip/naip_blob_review.json'   # by-eye verdicts on NAIP 2024 aircraft blobs (own review, inf)
REVIEW_MATCH_M = 1.0   # m: a blob takes the verdict of a review entry this close (blob centroids are deterministic)
SPLIT_MIN_EXT = 16.0   # m: a blob reviewed as two aircraft is split in two only when its extent is >= this [chosen: two
                       # GA singles wing to wing; smaller blobs hold only parts of each and are dropped]
DUP_M = 9.5         # m: two ramp / hangar-apron spots closer than this are one parking position [chosen: below the span
                    # of the smallest common type (C150 / C152 10.17 m, FAA ACD) minus ~0.7 m of position noise; the
                    # review's duplicates were 8.4 and 8.9 m apart]
N_OBS_MIN = 2       # independent observations (NAIP years with an aircraft + ADS-B stays + signal-edge events) for a
                    # ramp / hangar-apron spot to be 'obs' as a parking position; one sighting = 'inf' (review)
TWY_OBJ_M = 44.5 * FT   # AC 150/5300-13B Chg 1 Table 4-1, ADG I: "Taxiway centerline to fixed or movable object 44.5 ft (13.6 m)"
TLN_OBJ_M = 39.5 * FT   # same table: "Taxilane centerline to fixed or movable object 39.5 ft (12.0 m)"
FUS_FWD, FUS_AFT = 2.0, 6.5   # m: inferred aircraft outline relative to its wing line (C172: length 8.29 m, FAA ACD; the wing
                              # leading edge about 2 m behind the nose [inf, by eye on NAIP 2024 Green Ramp aircraft])
HGR_SPOT_M = 8.0    # m: an inferred hangar-apron spot (wing line) sits this far out from the real hangar wall [chosen: a GA
                    # single's nose-to-wing distance plus room to open the door; the door position is unknown]
HGR_STRIP = (2.0, 14.0)   # m from the wall: the strip in front of the side that must be OSM apron (not taxiway) [chosen]
CAP_GAP = 1.0       # m: wingtip gap of the practical capacity size (the Green Ramp C172s on the 12.15 m pitch leave 1.15 m:
                    # observed use, NAIP 2024 + adsb.lol; the AC design value is the 10 ft of WINGTIP_CLEAR)
SIZE_R = 40.0       # m: spots / obstacles farther apart than this do not limit each other (ADG III span 36 m + clearances)
HGR_ADSB = 5.0      # m: an ADS-B fixed-wing parking spot this close to a hangar outline is that hangar's apron spot (an
                    # aircraft at its door; the review's R056 sat 2.2 m from a T-hangar wall) [chosen]
HGR_ROOF_GRAY = 235.0   # NAIP 2024 median grey (6 x 6 m) above which an inferred spot is on a white roof, not pavement
                        # (measured at the 17 hangar-apron spots of the review build: pavement 154-222, an unmapped white
                        # annex roof 253) [chosen]
# inferred hangar aprons rejected by eye (NAIP 2024, out/phase1/review_fix/sheet_HE244N218_HE457N053_HE375N087_2024.png,
# 2026-11-12): hangar -> what the image shows at the rule point
HGR_REVIEW_REJECT = {
    'osm:way/971132674': 'the rule point falls on an unmapped white annex building attached to the hangar (APP Jet Center)',
    'osm:way/204800998': 'the rule point falls inside a walled yard beside the building, not on an aircraft apron',
}
HGR_OCC_M2 = 3.0    # m2 of the NAIP 2024 bright-object mask inside an inferred hangar-apron outline (+1 m) that rejects it
                    # (vehicles or aircraft there; the review found an inferred spot in a car lot) [chosen, = tiedowns OCC_M2]


def common_min_span():
    """smallest FAA ACD wingspan among the types seen on >= 3 aircraft on the field (data/ga_types.json)"""
    v = [(type_span(t), t) for t, g in GATYPES.items() if (g.get('onfield_aircraft') or 0) >= 3 and type_span(t)]
    return min(v) if v else (None, None)


def _review():
    return [r for r in load(NAIP_REVIEW)['items'] if r['year'] == '2024']


def parking(N24, N22, apr, hgr, bld, helis):
    """tie-down rows (NAIP tees), ADS-B spots, signal-edge clusters, NAIP 2024 parked aircraft (by-eye reviewed),
    helipads, inferred hangar aprons; duplicates merged; src from the number of independent observations"""
    holes_all = [Polygon(h['ring']).buffer(1.0) for h in hgr] + [Polygon(b['ring']).buffer(1.0) for b in bld if b.get('ring')]
    in_bld = prep(unary_union(holes_all))
    apron_pg = {a['id']: Polygon(a['ring']).buffer(0) for a in apr}
    REV = _review(); rev_used = Counter()
    spots = []; td_meta = {}; ac_all = {'2024': [], '2022': []}; dropped = Counter(); acm = {}

    def new(**kw):
        d = dict(_naip=set(), _stays=0, _aircraft=0, _sig=0, _types=Counter(), _merged=[]); d.update(kw); return d
    # ---- a. tie-down rows per apron (both NAIP years)
    for a in apr:
        pg = apron_pg[a['id']]; holes = [h for h in holes_all if h.intersects(pg)]
        G = {'2024': TD.Grid(N24, pg, holes), '2022': TD.Grid(N22, pg, holes)}
        seeds = TD.merge_seeds([(y, G[y].seeds()) for y in ('2024', '2022')])
        rows = TD.rows_of(seeds); pitch, pres = TD.fit_pitch(rows)
        for y in G: ac_all[y] += [dict(b, apron=a['id']) for b in G[y].aircraft()]
        acm[a['id']] = type('AcMask', (), {'xs': G['2024'].xs, 'zs': G['2024'].zs, 'acmask': G['2024'].acmask})   # keep the mask only
        td_meta[a['id']] = {'seeds': len(seeds), 'rows_found': len(rows), 'pitch_m': pitch, 'pitch_resid_median_m': pres}
        if not pitch: continue
        sp = TD.walk_rows(rows, pitch, G, {}, prep(pg.buffer(-1.0)), holes)
        order = sorted(range(len(rows)), key=lambda i: rows[i]['v'] * (1 if abs((rows[i]['th'] - rows[0]['th'] + 180) % 360 - 180) < 90 else -1))
        rank = {ri: n + 1 for n, ri in enumerate(order)}
        td_meta[a['id']]['rows'] = sorted([{'row': rank[i], 'stem_hdg': r1(r['th']), 'seeds': len(r['seeds']), 'seed_years': dict(sorted(Counter(y for s in r['seeds'] for y in s['years']).items())),
                                            'seed_resid_m': r['seed_resid_m']} for i, r in enumerate(rows)], key=lambda r: r['row'])
        bycount = Counter()
        for s in sorted(sp, key=lambda s: (rank[s['row']], s['k'])):
            bycount[rank[s['row']]] += 1
            obs = bool(s['tee_years'])
            seen = sorted(set(s['aircraft_years']) | set(s['aircraft_planform_years']))
            spots.append(new(kind='tiedown', x=s['x'], z=s['z'], heading=(s['stem_hdg'] + 180) % 360, apron=a['id'],
                             row=rank[s['row']], zone_seq=bycount[rank[s['row']]], pitch=pitch, src='obs' if obs else 'inf',
                             refs=['naip2024', 'naip2022', 'ac5300'], _naip=set(seen), _ref='tee_junction',
                             ev={'tee_seen': s['tee_years'], 'tee_ncc': {y: v['ncc'] for y, v in sorted(s['tee'].items())},
                                 'aircraft_seen': seen, 'aircraft_planform_m2': s['aircraft_planform_m2'],
                                 'aircraft_seen_rule': 'NAIP aircraft mask >= %.1f m2 inside the outline of a GA single parked on the tee (tiedowns.Grid.planform), or >= %.1f m2 within %.1f m of the junction' % (TD.PLAN_OCC_M2, TD.OCC_M2, TD.OCC_R),
                                 'row_pitch_m': pitch,
                                 'how': ('painted tee found at this pitch position of the row' if obs else
                                         'pitch position of a tee row (row of >= %d detected tees, apron pitch %.2f m) with no tee visible%s' % (TD.MIN_ROW_SEEDS, pitch, ' (an aircraft parked over it in NAIP %s)' % '/'.join(seen) if seen else ''))}))

    def near_spot(x, z, d, kinds=None):
        best = None
        for i, s in enumerate(spots):
            if kinds and s['kind'] not in kinds: continue
            dd = math.hypot(s['x'] - x, s['z'] - z)
            if dd <= max(d, s.get('_r', 0.0)) and (best is None or dd < best[0]): best = (dd, i)
        return best

    paved_osm = prep(unary_union([apron_pg[k] for k in sorted(apron_pg)] + [LineString(w['w']).buffer(PAVE_TWY) for k in ('taxiway', 'taxilane') for w in FE[k]]))

    def on_pavement(x, z):
        """OSM apron, or <= PAVE_TWY m from an OSM taxiway / taxilane centreline, or NAIP 2024 grey in a 2 m disc
        (median saturation < SAT_MAX and excess green < EG_MAX; asphalt / concrete aprons read 0.04-0.14, grass 0.19-0.36)"""
        if paved_osm.contains(Point(x, z)): return 'osm'
        a_ = np.linspace(-2, 2, 9); X, Z = np.meshgrid(a_ + x, a_ + z); m_ = np.hypot(X - x, Z - z) <= 2.0
        R_, G_, B_ = (N24.sample(X[m_], Z[m_], k) for k in 'RGB')
        mx = np.maximum(np.maximum(R_, G_), B_); mn = np.minimum(np.minimum(R_, G_), B_)
        sat = float(np.median((mx - mn) / np.maximum(mx, 1))); eg = float(np.median(G_ - (R_ + B_) / 2))
        return 'naip_grey' if (sat < SAT_MAX and eg < EG_MAX) else None

    def add(sp, what):
        pv = on_pavement(sp['x'], sp['z'])
        if pv is None: dropped['%s not on pavement (OSM / NAIP grey test)' % what] += 1; return
        if pv == 'naip_grey':
            sp['ev']['pavement'] = 'not on OSM pavement; NAIP 2024 grey (unmapped hard surface)'
            if 'naip2024' not in sp['refs']: sp['refs'] = sp['refs'] + ['naip2024']
        spots.append(sp)

    def attach(i, key, val, dist, stays=0, aircraft=0, sig=0, types=None):
        spots[i]['ev'].setdefault(key, []).append(dict(val, dist_m=r2(dist))); spots[i]['refs'] = sorted(set(spots[i]['refs'] + ['adsb']))
        spots[i]['_stays'] += stays; spots[i]['_aircraft'] += aircraft; spots[i]['_sig'] += sig; spots[i]['_types'].update(types or {})
    on_apron = lambda x, z: next((aid for aid, pg in sorted(apron_pg.items()) if pg.contains(Point(x, z))), None)
    lanes = prep(unary_union([LineString(w['w']).buffer(LANE_M) for k in ('taxiway', 'taxilane') for w in FE[k] if w.get('status', 'open') == 'open' and not w['tags'].get('abandoned') and not w['tags'].get('disused')]))
    # ---- b0. helipad spots (OSM), made before the ADS-B steps so that ADS-B evidence on a pad attaches to its spot
    for h in helis:
        e = {'how': 'centre of the OSM helipad polygon'}
        hs = [p['id'] for p in sorted(STAYS['spots'], key=lambda s: s['id']) if p['kind'] == 'helicopter' and math.hypot(p['x'] - h['x'], p['z'] - h['z']) <= h['size_m'] / 2 + 2]
        if hs: e['adsb_spots'] = hs
        spots.append(new(kind='helipad', x=h['x'], z=h['z'], heading=None, apron=on_apron(h['x'], h['z']), helipad=h['id'], src='obs', refs=['osm'] + (['adsb'] if hs else []),
                         rotor_max_m=h['size_m'], _ref='helipad_polygon_centroid', ev=e))
    heli_pg = [(next(i for i, s_ in enumerate(spots) if s_.get('helipad') == h['id']), Polygon(h['ring']).buffer(2.0)) for h in helis]
    FIXED_NOTE = 'a fixed-wing aircraft parked on this OSM helipad (adsb.lol): the pad is also used as ramp; no separate ramp spot is made (it would overlap the helipad)'

    def on_heli(x, z):
        return next((i for i, pg in heli_pg if pg.contains(Point(x, z))), None)
    hg_pg = [(h['id'], Polygon(h['ring']).buffer(0)) for h in hgr]
    # ---- b. ADS-B parking spots (kind parking / helicopter)
    for p in sorted(STAYS['spots'], key=lambda s: s['id']):
        if p['kind'] == 'runup_or_hold': continue
        types = {t: n for t, n in sorted(p['types'].items()) if t != '?'}
        spans = [type_span(t) for t in types]; spans = [s_ for s_ in spans if s_]
        ev = {'adsb_spot': p['id'], 'stays': p['n_stays'], 'aircraft': p['n_aircraft'], 'radius_m': p['radius'], 'types': types,
              'classes': p['classes'], 'loc': p['loc'], 'loc_detail': p['loc_detail'], 'dur_buckets': p['dur_buckets'], 'max_type_span_m': r2(max(spans)) if spans else None}
        if p['kind'] == 'helicopter':
            hp = sorted(helis, key=lambda h: math.hypot(h['x'] - p['x'], h['z'] - p['z']))[0]
            if math.hypot(hp['x'] - p['x'], hp['z'] - p['z']) <= hp['size_m'] / 2 + 2: continue   # on an OSM helipad: helipad spot below
        else:
            hi = on_heli(p['x'], p['z'])
            if hi is not None:   # a fixed-wing aircraft parked on an OSM helipad: evidence of that helipad's use, not a ramp spot
                attach(hi, 'fixed_wing_adsb', ev, math.hypot(spots[hi]['x'] - p['x'], spots[hi]['z'] - p['z']), types=types); spots[hi]['ev']['fixed_wing_note'] = FIXED_NOTE
                dropped['fixed-wing adsb spot on an OSM helipad (+2 m): kept as evidence on that helipad spot'] += 1; continue
        big = max(spans) / 2 + 2.0 if spans and max(spans) > BIG_SPAN else 0.0     # a wide aircraft: half its span + 2 m
        nb = near_spot(p['x'], p['z'], MERGE_TD, ('tiedown',)) or near_spot(p['x'], p['z'], max(MERGE_RAMP, big), ('ramp', 'helipad'))
        if nb: attach(nb[1], 'adsb', ev, nb[0], stays=p['n_stays'], aircraft=p['n_aircraft'], types=types); continue
        if in_bld.contains(Point(p['x'], p['z'])): dropped['adsb spot inside a building / hangar footprint'] += 1; continue
        if p['kind'] != 'helicopter' and lanes.contains(Point(p['x'], p['z'])): dropped['adsb spot within %.0f m of an open OSM taxiway / taxilane centreline (a stop, not parking)' % LANE_M] += 1; continue
        hd = p.get('hdg_taxi_mean') if (p.get('n_hdg', 0) >= 3 and (p.get('hdg_taxi_R') or 0) >= 0.7) else None
        hw = min(((pg.exterior.distance(Point(p['x'], p['z'])), hid) for hid, pg in hg_pg))
        at_hgr = p['kind'] != 'helicopter' and hw[0] <= HGR_ADSB
        add(new(kind='helipad' if p['kind'] == 'helicopter' else ('hangar_apron' if at_hgr else 'ramp'), x=p['x'], z=p['z'], heading=hd, apron=on_apron(p['x'], p['z']),
                hangar=hw[1] if at_hgr else None,
                refs=['adsb'], adsb_span=max(spans) if spans else None, _r=big, _stays=p['n_stays'], _aircraft=p['n_aircraft'],
                _types=Counter(types), _ref='gnss_antenna',
                ev=dict(ev, how='adsb.lol parking spot: >= 5 min stationary stays clustered (tools/adsb/parked_stays.py); position = GNSS antenna; heading = mean taxi-in heading when >= 3 stays agree (R >= 0.7), else null%s' % (
                    '; %.1f m from the OSM outline of the hangar: an aircraft parked at its door (hangar apron)' % hw[0] if at_hgr else ''))), 'adsb spot')
    # ---- c. signal-edge clusters (aircraft switched on / off on the ground after >= 30 min silence)
    E = [(e['x'], e['z'], e['kind'], e.get('type'), e.get('cls')) for e in STAYS['signal_edges']]
    used = [False] * len(E); clusters = []
    for i in range(len(E)):
        if used[i]: continue
        grp = [i]; used[i] = True; k = 0
        while k < len(grp):
            for j in range(len(E)):
                if not used[j] and math.hypot(E[j][0] - E[grp[k]][0], E[j][1] - E[grp[k]][1]) <= EDGE_LINK: used[j] = True; grp.append(j)
            k += 1
        clusters.append(grp)
    for grp in clusters:
        x = float(np.median([E[j][0] for j in grp])); z = float(np.median([E[j][1] for j in grp]))
        hd = min(((pg.exterior.distance(Point(x, z)), hid) for hid, pg in hg_pg))
        need = EDGE_MIN_HGR if hd[0] <= HGR_D else EDGE_MIN
        if len(grp) < need: continue
        types = dict(sorted(Counter(E[j][3] or '?' for j in grp).items()))
        st_, en_ = sum(1 for j in grp if E[j][2] == 'start'), sum(1 for j in grp if E[j][2] == 'end')
        ev = {'signal_edges': len(grp), 'starts': st_, 'ends': en_, 'types': types}
        tclean = {t: n for t, n in types.items() if t != '?'}
        hi = on_heli(x, z)
        if hi is not None:
            fw = sum(1 for j in grp if E[j][4] != 'helicopter') * 2 > len(grp)
            attach(hi, 'fixed_wing_adsb_signal_edges' if fw else 'adsb_signal_edges', ev, math.hypot(spots[hi]['x'] - x, spots[hi]['z'] - z), sig=0 if fw else max(st_, en_), types=tclean)
            if fw: spots[hi]['ev']['fixed_wing_note'] = FIXED_NOTE
            dropped['signal-edge cluster on an OSM helipad (+2 m): kept as evidence on that helipad spot'] += 1; continue
        nb = near_spot(x, z, MERGE_TD, ('tiedown',)) or near_spot(x, z, MERGE_RAMP if hd[0] > HGR_D else 5.0)
        if nb: attach(nb[1], 'adsb_signal_edges', ev, nb[0], sig=max(st_, en_), types=tclean); continue
        if in_bld.contains(Point(x, z)): dropped['signal-edge cluster inside a building / hangar footprint (+1 m)'] += 1; continue
        if lanes.contains(Point(x, z)): dropped['signal-edge cluster within %.0f m of an open OSM taxiway / taxilane centreline' % LANE_M] += 1; continue
        if hd[0] <= HGR_D:
            add(new(kind='hangar_apron', x=x, z=z, heading=None, apron=on_apron(x, z), hangar=hd[1], refs=['adsb', 'osm'], _sig=max(st_, en_),
                    _types=Counter(tclean), _ref='gnss_antenna',
                    ev=dict(ev, how='>= %d adsb.lol signal starts/ends on the ground within %.0f m (single linkage), %.1f m from the OSM hangar outline: an aircraft parked at / in this hangar' % (EDGE_MIN_HGR, EDGE_LINK, hd[0]))), 'signal-edge cluster')
        elif on_apron(x, z):
            add(new(kind='ramp', x=x, z=z, heading=None, apron=on_apron(x, z), refs=['adsb'], _sig=max(st_, en_), _types=Counter(tclean), _ref='gnss_antenna',
                    ev=dict(ev, how='>= %d adsb.lol signal starts/ends on the ground within %.0f m (single linkage) on an OSM apron' % (EDGE_MIN, EDGE_LINK))), 'signal-edge cluster')
        else:
            dropped['signal-edge cluster off OSM aprons and not near a hangar'] += 1
    # ---- d. parked aircraft on NAIP 2024 (bright blob, extent >= AC_EXT_MIN), with the by-eye review verdict
    for a in sorted(ac_all['2024'], key=lambda a: (a['x'], a['z'])):
        if a['extent'] < AC_EXT_MIN: continue
        rv = min(((math.hypot(r['x'] - a['x'], r['z'] - a['z']), k) for k, r in enumerate(REV)), default=(1e9, None))
        rv = REV[rv[1]] if rv[0] <= REVIEW_MATCH_M else None
        verdict = rv['verdict'] if rv else None
        if rv: rev_used[verdict] += 1
        if verdict in ('vehicle', 'no_object', 'same_aircraft_as_another_blob'):
            dropped['NAIP 2024 blob reviewed by eye: %s' % verdict] += 1; continue
        cands = [(a['x'], a['z'])]
        if verdict == 'two_aircraft':
            if a['extent'] >= SPLIT_MIN_EXT and len(a.get('halves') or []) == 2: cands = [tuple(h) for h in a['halves']]
            else: dropped['NAIP 2024 blob reviewed by eye: centred between two aircraft, extent < %.0f m (not split)' % SPLIT_MIN_EXT] += 1; continue
        for (x, z) in cands:
            blob = {'extent_m': a['extent'], 'area_m2': a['area'], 'review': verdict or 'not reviewed'}
            nt = near_spot(x, z, MERGE_RAMP, ('tiedown',))
            if nt and nt[0] > MERGE_TD and '2024' not in spots[nt[1]]['_naip']: nt = None   # an empty tee 6-8 m away: another aircraft
            nb = nt or near_spot(x, z, MERGE_RAMP, ('ramp', 'hangar_apron', 'helipad'))
            if nb:
                spots[nb[1]]['ev'].setdefault('naip2024_blobs', []).append(dict(blob, dist_m=r2(nb[0])))
                if verdict in ('aircraft', 'two_aircraft') and spots[nb[1]]['kind'] != 'tiedown': spots[nb[1]]['_naip'].add('2024')
                if 'naip2024' not in spots[nb[1]]['refs']: spots[nb[1]]['refs'] = spots[nb[1]]['refs'] + ['naip2024']
                continue
            if lanes.contains(Point(x, z)): dropped['NAIP 2024 aircraft within %.0f m of an open OSM taxiway / taxilane centreline (taxiing or holding)' % LANE_M] += 1; continue
            m = [b for b in ac_all['2022'] if math.hypot(x - b['x'], z - b['z']) <= 3.0]
            add(new(kind='ramp', x=x, z=z, heading=None, apron=a['apron'], refs=['naip2024'] + (['naip2022'] if m else []),
                    _naip={'2024'} | ({'2022'} if m else set()), _ref='naip_blob_centroid' if len(cands) == 1 else 'naip_blob_half_centroid',
                    ev={'how': 'a parked aircraft on NAIP 2024 (bright mask fragments grouped by 1 m: %.1f m extent, %.0f m2; tools/airport/tiedowns.py Grid.aircraft)%s%s' % (
                            a['extent'], a['area'], '; split in two along its major axis (by-eye review: two aircraft)' if len(cands) > 1 else '', '; also there in NAIP 2022' if m else ''),
                        'naip_extent_m': a['extent'], 'naip_review': verdict or 'not reviewed by eye', 'naip_review_note': rv['note'] if rv else None}), 'NAIP aircraft')
    # ---- f. box hangars without an observed hangar-apron spot: one inferred spot in front of a side facing apron
    have = {s.get('hangar') for s in spots if s['kind'] == 'hangar_apron'}
    apr_u = unary_union([apron_pg[k] for k in sorted(apron_pg)])
    is_open = lambda w: w.get('status', 'open') == 'open' and not w['tags'].get('abandoned') and not w['tags'].get('disused')
    twy_u = unary_union([LineString(w['w']) for w in FE['taxiway'] if is_open(w)]); tln_u = unary_union([LineString(w['w']) for w in FE['taxilane'] if is_open(w)])
    for h in hgr:
        if h['kind'] != 'box_hangar' or h['id'] in have: continue
        if h['id'] in HGR_REVIEW_REJECT: dropped['box hangar: inferred apron spot rejected by eye (%s)' % HGR_REVIEW_REJECT[h['id']]] += 1; continue
        pg = Polygon(h['ring']).buffer(0); ext = list(pg.minimum_rotated_rectangle.exterior.coords)
        best = None; why = Counter()
        for i in range(4):
            a_, b_ = np.array(ext[i]), np.array(ext[i + 1]); L = np.linalg.norm(b_ - a_); m_ = (a_ + b_) / 2
            n_ = np.array([-(b_ - a_)[1], (b_ - a_)[0]]) / L
            if pg.contains(Point(m_ + n_ * 1.0)): n_ = -n_
            if L < 12.0: why['side < 12 m'] += 1; continue
            hit = LineString([tuple(m_ + n_ * 40), tuple(m_ - n_ * 40)]).intersection(pg.exterior)    # the real wall on this line
            pts = [np.array(g.coords[0]) for g in getattr(hit, 'geoms', [hit]) if not g.is_empty and g.geom_type == 'Point']
            if not pts: why['no wall on the side normal'] += 1; continue
            wpt = max(pts, key=lambda q_: float(np.dot(q_ - m_, n_)))
            q = wpt + n_ * HGR_SPOT_M
            strip = LineString([tuple(wpt + n_ * HGR_STRIP[0]), tuple(wpt + n_ * HGR_STRIP[1])])
            frac = apr_u.intersection(strip).length / (HGR_STRIP[1] - HGR_STRIP[0])
            if frac <= 0.9: why['strip not OSM apron'] += 1; continue
            if in_bld.intersects(strip): why['strip meets a building'] += 1; continue
            u_ = np.array([-n_[1], n_[0]])
            outline = unary_union([LineString([tuple(q - u_ * ADG_SPAN['I'] / 2), tuple(q + u_ * ADG_SPAN['I'] / 2)]),
                                   LineString([tuple(q - n_ * FUS_FWD), tuple(q + n_ * FUS_AFT)])])
            dt, dl = outline.distance(twy_u), outline.distance(tln_u)
            if dt < TWY_OBJ_M or dl < TLN_OBJ_M: why['aircraft outline inside the AC taxiway / taxilane object distance'] += 1; continue
            occ = mask_area(acm, outline.buffer(1.0))
            if occ >= HGR_OCC_M2: why['NAIP 2024 objects (vehicles / aircraft) inside the outline'] += 1; continue
            g_ = np.linspace(-3, 3, 13); X_, Z_ = np.meshgrid(g_ + q[0], g_ + q[1])
            gray = float(np.median(np.mean([N24.sample(X_, Z_, k) for k in 'RGB'], 0)))
            if gray > HGR_ROOF_GRAY: why['NAIP 2024 white roof at the rule point (grey %.0f)' % gray] += 1; continue
            if best is None or (frac, L) > best[0]: best = ((frac, L), q, n_, L, dt, dl, float(pg.exterior.distance(Point(*q))))
        if best is None:
            dropped['box hangar: no side gives an inferred spot (%s)' % ', '.join('%s %d' % kv for kv in sorted(why.items()))] += 1; continue
        _, q, n_, L, dt, dl, dw = best
        if near_spot(q[0], q[1], MERGE_RAMP): dropped['box hangar whose inferred apron spot falls within %.0f m of an observed spot (kept that one)' % MERGE_RAMP] += 1; continue
        add(new(kind='hangar_apron', x=float(q[0]), z=float(q[1]), heading=F.vec_hdg(-n_[0], -n_[1]), apron=on_apron(q[0], q[1]), hangar=h['id'], src='inf', refs=['osm', 'ac5300'],
                _rule=True, _ref='rule_point',
                ev={'how': 'box hangar with no observed spot: %.0f m out from the real wall, on the normal through the middle of the longest side (%.0f m) whose %.0f-%.0f m strip is OSM apron free of buildings; the outline of an ADG I aircraft parked nose to the hangar keeps %.1f m from open taxiway and %.1f m from open taxilane centrelines (AC 150/5300-13B Table 4-1 ADG I object distances %.1f / %.1f m); door position unknown (NAIP shows no doors)' % (
                    HGR_SPOT_M, L, HGR_STRIP[0], HGR_STRIP[1], dt, dl, TWY_OBJ_M, TLN_OBJ_M), 'wall_dist_m': r2(dw)}), 'inferred hangar apron')
    # ---- g. duplicates: ramp / hangar-apron spots closer than DUP_M are one parking position (strongest evidence kept)
    W = [i for i, s in enumerate(spots) if s['kind'] in ('ramp', 'hangar_apron') and not s.get('_rule')]
    strength = lambda s: (s['_stays'] * 3 + s['_sig'] * 2 + len(s['_naip']), s['kind'] == 'ramp', -s['x'], -s['z'])
    parent = {i: i for i in W}
    def root(i):
        while parent[i] != i: i = parent[i]
        return i
    for a_ in W:
        for b_ in W:
            if a_ < b_ and math.hypot(spots[a_]['x'] - spots[b_]['x'], spots[a_]['z'] - spots[b_]['z']) < DUP_M: parent[root(b_)] = root(a_)
    groups = defaultdict(list)
    for i in W: groups[root(i)].append(i)
    gone = set()
    for g in groups.values():
        if len(g) < 2: continue
        keep = max(g, key=lambda i: strength(spots[i])); K = spots[keep]
        for i in sorted(g):
            if i == keep: continue
            o = spots[i]; d = math.hypot(o['x'] - K['x'], o['z'] - K['z'])
            K['_merged'].append({'kind': o['kind'], 'x': r2(o['x']), 'z': r2(o['z']), 'dist_m': r2(d), 'ref_point': o['_ref'], 'evidence': o['ev']})
            K['_naip'] |= o['_naip']; K['_stays'] += o['_stays']; K['_aircraft'] += o['_aircraft']; K['_sig'] += o['_sig']; K['_types'].update(o['_types'])
            K['refs'] = sorted(set(K['refs']) | set(o['refs']))
            if o.get('adsb_span') and (K.get('adsb_span') or 0) < o['adsb_span']: K['adsb_span'] = o['adsb_span']
            gone.add(i); dropped['duplicate: ramp / hangar-apron spot within %.1f m of a stronger one (merged into it)' % DUP_M] += 1
    spots = [s for i, s in enumerate(spots) if i not in gone]
    # ---- h. src of the parking role from the number of independent observations
    for s in spots:
        n_obs = len(s['_naip']) + s['_stays'] + s['_sig']
        s['strength'] = {'naip_aircraft_years': sorted(s['_naip']), 'adsb_stays': s['_stays'], 'adsb_aircraft_at_most': s['_aircraft'],
                         'adsb_signal_events': s['_sig'], 'tee_years': s['ev'].get('tee_seen', []) if s['kind'] == 'tiedown' else [],
                         'osm_helipad': bool(s.get('helipad')), 'n_observations': n_obs, 'merged_duplicates': len(s['_merged'])}
        if s['kind'] == 'tiedown' or (s['kind'] == 'helipad' and s.get('helipad')) or s.get('_rule'): continue
        s['src'] = 'obs' if n_obs >= N_OBS_MIN else 'inf'
        if s['_merged']: s['ev']['merged_duplicates'] = s['_merged']
    return spots, td_meta, ac_all, dict(sorted(dropped.items())), dict(rev_used)


def mask_area(acm, geom):
    """m2 of the NAIP 2024 aircraft / bright-object mask (tiedowns.Grid.acmask of the aprons) inside geom"""
    tot = 0.0
    for aid in sorted(acm):
        G = acm[aid]; x0, z0, x1, z1 = geom.bounds
        c0, c1 = np.searchsorted(G.xs, [x0, x1]); r0, r1 = np.searchsorted(G.zs, [z0, z1])
        if c1 <= c0 or r1 <= r0: continue
        X, Z = np.meshgrid(G.xs[c0:c1], G.zs[r0:r1]); sub = G.acmask[r0:r1, c0:c1]
        if not sub.any(): continue
        from shapely import contains_xy
        tot += float((sub & contains_xy(geom, X, Z)).sum() * TD.RES ** 2)
        break                                   # the grids of adjacent aprons overlap: count one
    return tot


def _shape(s, span):
    if s['heading'] is None: return Point(s['x'], s['z']).buffer(max(span / 2, 0.005), 32)
    u = np.array([math.cos(math.radians(s['heading'])), math.sin(math.radians(s['heading']))])   # wing axis, perpendicular to the heading
    c = np.array([s['x'], s['z']])
    return LineString([tuple(c - u * span / 2), tuple(c + u * span / 2)])


def wing_shape(s, span): return _shape(s, span)


def _largest(cap, ok):
    """largest span in [0, cap] with ok(span) (ok is monotone: true for small spans); 0.0 if not even a point fits"""
    if ok(cap): return cap
    if not ok(0.0): return 0.0
    lo, hi = 0.0, cap
    for _ in range(40):
        mid = (lo + hi) / 2
        if ok(mid): lo = mid
        else: hi = mid
    return lo


def size_solve(wing, caps, clear, obst, tier):
    """sizes of the wing spots for a wingtip clearance `clear`: (1) each spot alone against its fixed obstacles (buildings,
    helipad discs: obst[k] = [(geom, label)]); (2) tier by tier (0 = painted tie-down rows, 1 = obs, 2 = inf): a spot is
    first fitted around the final shapes of every higher-priority spot within SIZE_R, then the spots of its tier share
    the space pairwise (equal share: the largest common span s, each capped, that keeps the two shapes >= clear apart;
    each spot takes the minimum over its pairs). Every pair and every obstacle then keeps `clear`. Returns sizes and,
    per spot, what limited it: ('obstacle', label, dist) | ('spot', index, dist) | None."""
    n = len(wing); lim = list(caps); by = [None] * n
    pos = np.array([[s['x'], s['z']] for s in wing])
    for k in range(n):
        for g, lab in obst[k]:
            v = _largest(lim[k], lambda sp: wing_shape(wing[k], sp).distance(g) >= clear - 1e-6)
            if v < lim[k] - 1e-9: lim[k] = v; by[k] = ('obstacle', lab, float(g.distance(Point(wing[k]['x'], wing[k]['z']))))
    final = {}
    for t in sorted(set(tier)):
        idx = [k for k in range(n) if tier[k] == t]
        for k in idx:
            d = np.hypot(*(pos - pos[k]).T)
            for j in sorted(final):
                if d[j] >= SIZE_R: continue
                gj = wing_shape(wing[j], final[j])
                v = _largest(lim[k], lambda sp: wing_shape(wing[k], sp).distance(gj) >= clear - 1e-6)
                if v < lim[k] - 1e-9: lim[k] = v; by[k] = ('spot', j, float(d[j]))
        new = list(lim)
        for a in range(len(idx)):
            i = idx[a]; d = np.hypot(*(pos - pos[i]).T)
            for j in idx[a + 1:]:
                if d[j] >= SIZE_R: continue
                ci, cj = lim[i], lim[j]
                ok = lambda sp: wing_shape(wing[i], min(ci, sp)).distance(wing_shape(wing[j], min(cj, sp))) >= clear - 1e-6
                lo = _largest(max(ci, cj), ok)
                for k, o in ((i, j), (j, i)):
                    if lo < new[k] - 1e-9: new[k] = lo; by[k] = ('spot', o, float(d[o]))
        for k in idx: lim[k] = new[k]; final[k] = new[k]
    return lim, by


def finish_spots(spots, apr, hgr, bld):
    """sizes (AC design value and practical capacity, tiered equal share, buildings and helipads as obstacles), observed
    spans, flags, zones, stable ids"""
    heli_def = min(h for h in (s.get('rotor_max_m') for s in spots if s['kind'] == 'helipad' and s.get('helipad')) if h)
    for s in spots:
        if s['kind'] == 'helipad':
            s['size'] = {'max_rotor_m': r1(s.get('rotor_max_m')), 'src': 'obs' if s.get('helipad') else 'inf',
                         'basis': 'smaller side of the OSM helipad polygon' if s.get('helipad') else 'unknown (helicopter ADS-B spot off the OSM helipads)'}
            if not s.get('helipad'): s['size']['max_rotor_m'] = None
            s['_disc'] = s.get('rotor_max_m') if s.get('helipad') else heli_def
            continue
        obs_span = s.get('adsb_span') or None
        cls = adg_of(obs_span) if obs_span and obs_span > ADG_SPAN['I'] else 'I'
        s['_cap'] = ADG_SPAN.get(cls, ADG_SPAN['III'])
        s['_basis'] = ('ADG %s (largest adsb.lol type seen here: %.1f m; AC 150/5300-13B Table 4-1 maximum wingspan)' % (cls, obs_span)) if cls != 'I' else 'ADG I upper bound 49 ft = 14.94 m (AC 150/5300-13B Table 4-1) [default for GA parking]'
    wing = [s for s in spots if s['kind'] != 'helipad']; helis = [s for s in spots if s['kind'] == 'helipad']
    tier = [0 if s['kind'] == 'tiedown' else (1 if s['src'] == 'obs' else 2) for s in wing]
    blds = [(h['id'], Polygon(h['ring']).buffer(0)) for h in hgr] + [(b['id'], Polygon(b['ring']).buffer(0)) for b in bld if b.get('ring')]
    obst = []
    for s in wing:
        P = Point(s['x'], s['z']); o = []
        for bid, pg in blds:
            if bid == s.get('hangar') and s['kind'] == 'hangar_apron': continue      # it parks at / into its own hangar
            if pg.distance(P) < SIZE_R: o.append((pg, bid))
        for h in helis:
            if math.hypot(h['x'] - s['x'], h['z'] - s['z']) < SIZE_R: o.append((Point(h['x'], h['z']).buffer(h['_disc'] / 2, 32), ('helipad', id(h))))
        obst.append(o)
    caps = [s['_cap'] for s in wing]
    des, des_by = size_solve(wing, caps, WINGTIP_CLEAR, obst, tier)
    cap, cap_by = size_solve(wing, caps, CAP_GAP, obst, tier)
    cmin, cmin_t = common_min_span()
    for k, s in enumerate(wing):
        capk = s.pop('_cap'); basis = s.pop('_basis')
        s['size'] = {'max_span_m': r2(math.floor(des[k] * 100) / 100), 'adg': adg_of(des[k]) if des[k] > 0.01 else None, 'src': 'inf', 'basis': basis,
                     'clearance_m': r2(WINGTIP_CLEAR),
                     'capacity_span_m': r2(math.floor(cap[k] * 100) / 100), 'capacity_gap_m': CAP_GAP,
                     'capacity_note': 'practical size: the same rule with a %.1f m wingtip gap (observed use at HWD) instead of the AC 10 ft; use this to place aircraft, max_span_m is the AC design value' % CAP_GAP}
        s['_by'] = (des_by[k] if des[k] < capk - 1e-3 else None, cap_by[k] if cap[k] < capk - 1e-3 else None)
        if s['kind'] == 'tiedown':
            s['size']['rule'] = 'tee row pitch %.2f m - 10 ft = %.2f m (AC 150/5300-13B Fig E-2: tiedown spacing = wingspan plus 10 ft (3 m))' % (s['pitch'], s['pitch'] - WINGTIP_CLEAR)
        occ = {}
        for t, n_ in sorted(s['_types'].items()):
            sp_ = type_span(t)
            if sp_: occ[t] = r2(sp_)
        if occ:
            s['size']['observed_max_span_m'] = max(occ.values()); s['size']['observed_type_spans_m'] = occ
            s['size']['observed_src'] = 'obs: every adsb.lol type seen parked here (stays, signal starts / ends, merged duplicates) -> FAA ACD wingspan (data/ga_types.json)'
        if s['ev'].get('naip_extent_m'): s['size']['naip_blob_extent_m'] = s['ev']['naip_extent_m']
        fl = []
        o = s['size'].get('observed_max_span_m')
        if o and o > s['size']['max_span_m'] + 0.01: fl.append('observed_type_wider_than_design')
        if o and o > s['size']['capacity_span_m'] + 0.01: fl.append('observed_type_wider_than_capacity')
        if cmin and s['size']['capacity_span_m'] < cmin - 0.01: fl.append('capacity_below_smallest_common_type (%s %.2f m)' % (cmin_t, cmin))
        if des[k] < 0.5: fl.append('no_design_size (too close to a building, helipad or a higher-priority spot for the AC rule)')
        s['size']['flags'] = fl
    # zones and stable ids
    hg = {h['id']: h for h in hgr}
    an = {a['id']: FBO_QUAL.get(a['id']) or a['name'] or ((a['al5015_label'] or {}).get('text') or '').title() or None for a in apr}
    kind_order = {'tiedown': 0, 'ramp': 1, 'hangar_apron': 2, 'helipad': 3}
    for s in spots:
        if s['kind'] == 'tiedown': s['zone'] = '%s row %d' % (an[s['apron']] or 'apron %s' % s['apron'].split('/')[-1], s['row'])
        elif s['kind'] == 'hangar_apron':
            h = hg[s['hangar']]; s['zone'] = 'apron of %s' % (h['name'] or 'hangar %s' % s['hangar'].split('/')[-1])
        else:
            base = an.get(s['apron']) if s.get('apron') else None
            if not base:
                hh = min(((Polygon(h['ring']).distance(Point(s['x'], s['z'])), h['id']) for h in hgr))
                base = 'near %s' % (hg[hh[1]]['name'] or 'hangar %s' % hh[1].split('/')[-1])
            s['zone'] = base
    idx = sorted(range(len(spots)), key=lambda i: (kind_order[spots[i]['kind']], spots[i]['zone'], spots[i].get('zone_seq', 0), round(spots[i]['x'], 2), round(spots[i]['z'], 2)))
    newid = {}; seen = Counter()
    for i in idx:
        s = spots[i]; prefix = {'tiedown': 'T', 'ramp': 'R', 'hangar_apron': 'H', 'helipad': 'P'}[s['kind']]
        x, z = int(round(s['x'])), int(round(s['z']))
        sid = '%s%s%03d%s%03d' % (prefix, 'E' if x >= 0 else 'W', abs(x), 'S' if z >= 0 else 'N', abs(z))
        seen[sid] += 1
        newid[i] = sid if seen[sid] == 1 else '%s_%d' % (sid, seen[sid])
    zs = Counter(); out = []
    REFP = {'tee_junction': 'junction of the painted tee = wing / main-gear line (AC 150/5300-13B Fig E-1)',
            'gnss_antenna': 'median ADS-B position = GNSS antenna (1-3 m from the planform centre for a GA single [inferred])',
            'naip_blob_centroid': 'centroid of the NAIP 2024 aircraft-mask blob (about the planform centroid; a high wing may dominate)',
            'naip_blob_half_centroid': 'centroid of one half of a NAIP 2024 blob of two aircraft parked wing to wing',
            'helipad_polygon_centroid': 'centroid of the OSM helipad polygon', 'rule_point': 'rule point: the wing line of an aircraft parked nose to the hangar'}
    for i in idx:
        s = spots[i]
        if s['kind'] == 'tiedown': zone = '%s, tie-down %d' % (s['zone'], s['zone_seq'])
        elif s['kind'] == 'hangar_apron':
            zs[s['zone']] += 1; zone = '%s, spot %d' % (s['zone'], zs[s['zone']])
        else:
            zs[(s['kind'], s['zone'])] += 1; zone = '%s %s %d' % (s['zone'], {'ramp': 'ramp spot', 'helipad': 'helipad'}[s['kind']], zs[(s['kind'], s['zone'])])
        e = {'id': newid[i], 'kind': s['kind'], 'x': r2(s['x']), 'z': r2(s['z']),
             'ref_point': s['_ref'], 'ref_point_def': REFP[s['_ref']],
             'heading': r1(s['heading']) if s['heading'] is not None else None,
             'heading_src': ('inf' if s['kind'] in ('tiedown', 'hangar_apron') else 'obs') if s['heading'] is not None else None,
             'zone': zone, 'zone_note': 'descriptive label (PLAN D3), not an official designation',
             'apron': s.get('apron'), 'size': s['size'], 'src': s['src'],
             'src_rule': ('painted tee seen (obs) / pitch position of a tee row (inf)' if s['kind'] == 'tiedown' else
                          'mapped OSM helipad' if s.get('helipad') else 'rule (no observation)' if s.get('_rule') else
                          'obs when >= %d independent observations (NAIP years with an aircraft + adsb.lol stays + signal-edge events), else inf' % N_OBS_MIN),
             'strength': s['strength'], 'refs': sorted(set(s['refs'])), 'evidence': s['ev']}
        if s['kind'] == 'tiedown':
            e['heading_evidence'] = 'nose away from the tee stem (aircraft parked on the Green Ramp tees sit with the tail over the stem end, NAIP 2024) [inf for the other tees]'
        if s.get('hangar'): e['hangar'] = s['hangar']
        if s.get('helipad'): e['helipad'] = s['helipad']
        out.append((i, e))
    wing_pos = {id(s): k for k, s in enumerate(wing)}
    ids_by_obj = {id(spots[i]): newid[i] for i in idx}
    helis_by = {id(h): ids_by_obj[id(h)] for h in helis}
    def lab(b):
        if b is None: return None
        if b[0] == 'obstacle':
            l = b[1]
            return ('helipad spot %s' % helis_by[l[1]]) if isinstance(l, tuple) else ('building / hangar %s' % l)
        return 'spot %s at %.1f m' % (ids_by_obj[id(wing[b[1]])], b[2])
    for i, e in out:
        s = spots[i]
        if s['kind'] == 'helipad': continue
        db, cb = s.pop('_by')
        if db: e['size']['limited_by'] = 'AC 10 ft wingtip clearance (Table 5-1 ADG I-II; Fig E-2 / E-3) to %s%s' % (lab(db), ' (equal share)' if db[0] == 'spot' and tier[wing_pos[id(s)]] == tier[wing_pos[id(wing[db[1]])]] else '')
        if cb: e['size']['capacity_limited_by'] = '%.1f m gap to %s' % (CAP_GAP, lab(cb))
    return [e for _, e in out]


# ================================================================================================== assemble
def build_env():
    """library versions the numbers were made with (the FFT tee matcher and the poppler raster of AL-5015 may differ
    slightly between versions; within one environment the build is byte-reproducible)"""
    import subprocess, scipy, shapely, PIL
    pv = subprocess.run(['pdftoppm', '-v'], capture_output=True, text=True)
    pv = (pv.stderr or pv.stdout).splitlines()[0].strip()
    return {'python': sys.version.split()[0], 'numpy': np.__version__, 'scipy': scipy.__version__, 'shapely': shapely.__version__,
            'pillow': PIL.__version__, 'poppler': pv}


def main():
    plot = '--no-plot' not in sys.argv
    N24, N22 = Naip('2024'), Naip('2022')
    global FIT_RES_TXT
    W = al5015.words(); M, fit_res = al5015.affine()
    FIT_RES_TXT = '%.1f-%.1f' % (min(fit_res.values()), max(fit_res.values()))
    labels = al5015.labels(W, M); hs_geo = al5015.hotspots(W, M)
    rw = runways(N24, N22)
    tw, tl, bst = taxiways(N24)
    apr = aprons(labels); hd = holds(N24); hs = hotspots(hs_geo)
    hp = helipads(); hg = hangars(); bl = buildings(labels, M); mk = markers()
    sp_raw, td_meta, ac_all, dropped, rev_used = parking(N24, N22, apr, hg, bl, hp)
    sp = finish_spots(sp_raw, apr, hg, bl)
    refs_osm = sorted({w['ref'] for w in tw if w['ref']})
    D = {
        'what': 'Hayward Executive Airport (FAA HWD, ICAO KHWD) airport data set for Hayward Live 3D: runways (FAA NASR), taxiways / taxilanes / aprons / holding positions / helipads / hangars / buildings (OpenStreetMap, checked and locally moved onto USDA NAIP paint), hot spots (FAA AL-5015, inferred geometry), parking spots (NAIP tie-down tees, adsb.lol parked stays, OSM helipads).',
        'licence': 'ODbL 1.0 - this file is a Derivative Database of OpenStreetMap ((c) OpenStreetMap contributors) and of adsb.lol data, made available under the Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/); FAA and USDA NAIP inputs are U.S. public domain. See docs/ATTRIBUTION.md',
        'attribution': ['© OpenStreetMap contributors (ODbL 1.0) - https://www.openstreetmap.org/copyright',
                        'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL 1.0',
                        'Imagery measurements: USDA NAIP 2024 / 2022 (USDA FPAC-BC Geospatial Enterprise Operations), public domain',
                        'FAA NASR (cycle 2026-10-29), Chart Supplement SW (29 Oct 2026), airport diagram AL-5015 (cycle 2611), AC 150/5300-13B Chg 1, AC 150/5340-1M Chg 1 - U.S. Government works'],
        'generator': 'tools/build_airport.py (deterministic; run it to rebuild; tools/check_airport.py checks it)',
        'sources': SOURCES,
        'src_legend': {'obs': 'seen in a source: surveyed (FAA), mapped (OSM), measured on NAIP, or observed by ADS-B', 'inf': 'inferred: by a stated rule, from a schematic chart, by eye, or a default'},
        'parking_fields': {'id': 'kind letter (T tie-down, R ramp, H hangar apron, P helipad) + the rounded position: E/W metres east / west and N/S metres north / south of the ARP; stable as long as the position is',
                           'src': 'role as a parking position: see src_rule (a ramp / hangar-apron spot needs >= %d independent observations to be obs)' % N_OBS_MIN,
                           'strength': 'the observations behind the spot: NAIP years with an aircraft, adsb.lol stays (and at most how many aircraft), signal-edge events (max of starts and ends), tee years, merged duplicates',
                           'ref_point': 'what point of the aircraft the position stands for (ref_point_def)',
                           'size.max_span_m': 'AC 150/5300-13B design value: largest span keeping 10 ft from neighbours (tiered equal share), buildings and helipads [inf]',
                           'size.capacity_span_m': 'the same with a %.1f m gap: the practical size for placing aircraft [inf]' % CAP_GAP,
                           'size.observed_max_span_m': 'widest adsb.lol type seen here (FAA ACD wingspan) [obs]', 'size.flags': 'where the observed type does not fit, or no size fits'},
        'frame': frame(),
        'runways': rw, 'taxiways': tw, 'taxilanes': tl, 'aprons': apr, 'holds': hd, 'hotspots': hs,
        'helipads': hp, 'hangars': hg, 'buildings': bl, 'markers': mk, 'parking': sp,
        'al5015_labels': [dict(l, src='inf', refs=['al5015'], evidence='label anchor = centre of its text-layer words mapped by the diagram affine (residuals %s m at the runway ends); this is where the label text is printed, which the chart sets beside the feature (often with a leader), so it is not the feature position' % FIT_RES_TXT) for l in labels],
        'not_placed': not_placed(labels, sp),
        'not_yet_sourced': NOT_YET_SOURCED,
        'checks_at_build': {
            'taxiway_refs_osm': refs_osm, 'taxiway_refs_al5015': AL5015_TWYS, 'refs_equal': refs_osm == sorted(AL5015_TWYS),
            'paint_bstar_of_ridges': {'n': len(bst), 'p5_p50_p95': [r1(v) for v in np.percentile(bst, [5, 50, 95])] if bst else None, 'threshold': BSTAR_MIN},
            'tiedown_detection': {'params': TD.PARAMS, 'per_apron': td_meta, 'naip_aircraft_blobs': {y: len(v) for y, v in ac_all.items()}},
            'parking_candidates_dropped': dropped,
            'naip_blob_review': {'file': NAIP_REVIEW, 'verdicts_used': rev_used},
            'parking_rules': {'MERGE_TD': MERGE_TD, 'MERGE_RAMP': MERGE_RAMP, 'BIG_SPAN': BIG_SPAN, 'EDGE_LINK': EDGE_LINK, 'EDGE_MIN': EDGE_MIN, 'EDGE_MIN_HGR': EDGE_MIN_HGR, 'HGR_D': HGR_D, 'AC_EXT_MIN': AC_EXT_MIN, 'LANE_M': LANE_M, 'PAVE_TWY': PAVE_TWY, 'SAT_MAX': SAT_MAX, 'EG_MAX': EG_MAX,
                              'REVIEW_MATCH_M': REVIEW_MATCH_M, 'SPLIT_MIN_EXT': SPLIT_MIN_EXT, 'DUP_M': DUP_M, 'N_OBS_MIN': N_OBS_MIN, 'TWY_OBJ_M': r2(TWY_OBJ_M), 'TLN_OBJ_M': r2(TLN_OBJ_M),
                              'FUS_FWD': FUS_FWD, 'FUS_AFT': FUS_AFT, 'HGR_SPOT_M': HGR_SPOT_M, 'HGR_ADSB': HGR_ADSB, 'HGR_OCC_M2': HGR_OCC_M2, 'HGR_ROOF_GRAY': HGR_ROOF_GRAY, 'HGR_REVIEW_REJECT': HGR_REVIEW_REJECT, 'HGR_STRIP': list(HGR_STRIP), 'CAP_GAP': CAP_GAP, 'SIZE_R': SIZE_R,
                              'WINGTIP_CLEAR_m': r2(WINGTIP_CLEAR), 'ADG_SPAN_m': {k: r2(v) for k, v in ADG_SPAN.items()}},
            'wingspan_limits_nasr': {k: v[0] for k, v in sorted(WINGSPAN_LIMIT.items())},
        },
        'build_env': build_env(),
    }
    D['counts'] = {k: len(D[k]) for k in ('runways', 'taxiways', 'taxilanes', 'aprons', 'holds', 'hotspots', 'helipads', 'hangars', 'buildings', 'markers', 'parking')}
    D['counts']['parking_by_kind_src'] = {'%s/%s' % k: v for k, v in sorted(Counter((s['kind'], s['src']) for s in sp).items())}
    s = json.dumps(D, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    open(OUT_JSON, 'w', encoding='utf-8').write(s + '\n')
    hdr = ('// generated by tools/build_airport.py - do not edit. Hayward Executive (KHWD) airport data, world frame %s (tools/common/hwd_frame.py = js/geo.js).\n'
           '// ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap contributors (https://www.openstreetmap.org/copyright) and from\n'
           '// adsb.lol (https://adsb.lol), made available under the Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/);\n'
           '// this derived database is offered under the ODbL 1.0 as well. FAA NASR / Chart Supplement / AL-5015 / ACs and USDA NAIP 2024/2022\n'
           '// (USDA FPAC-BC Geospatial Enterprise Operations) are U.S. public domain. Sources, terms and notices: docs/ATTRIBUTION.md\n') % F.FRAME_ID
    open(OUT_JS, 'w', encoding='utf-8').write(hdr + 'export const HWD_AIRPORT = ' + s + ';\n')
    print('wrote', rel(OUT_JSON), len(s), 'B;', json.dumps(D['counts']))
    if plot: qa_plot(D, N24)


def qa_plot(D, N):
    from PIL import Image, ImageDraw
    os.makedirs(FIG, exist_ok=True)
    x0, x1, z0, z1, res = -1000.0, 1000.0, -850.0, 750.0, 0.8
    xs = np.arange(x0, x1, res); zs = np.arange(z0, z1, res); X, Z = np.meshgrid(xs, zs)
    rgb = np.stack([N.sample(X, Z, k) for k in ('R', 'G', 'B')], -1)
    im = Image.fromarray((np.clip(rgb, 0, 255) * 0.6).astype(np.uint8)); d = ImageDraw.Draw(im)
    P = lambda p: ((p[0] - x0) / res, (p[1] - z0) / res)
    for r in D['runways']: d.polygon([P(p) for p in r['outline']['ring']], outline=(255, 255, 255))
    for a in D['aprons']: d.polygon([P(p) for p in a['ring']], outline=(0, 200, 255))
    for h in D['hangars']: d.polygon([P(p) for p in h['ring']], outline=(255, 140, 0) if h['kind'] == 'box_hangar' else (255, 220, 0))
    for w in D['taxiways']: d.line([P(p) for p in w['pts']], fill=(255, 255, 0) if w['status'] == 'open' else (255, 0, 0), width=1)
    for w in D['taxilanes']: d.line([P(p) for p in w['pts']], fill=(255, 200, 140), width=1)
    for h in D['hotspots']:
        if h['ring']: d.polygon([P(p) for p in h['ring']], outline=(200, 120, 40))
    for h in D['holds']:
        x, y = P((h['x'], h['z'])); d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(255, 0, 0) if h['bar'] else (255, 0, 255))
    col = {'tiedown': (255, 60, 60), 'ramp': (60, 255, 60), 'hangar_apron': (60, 160, 255), 'helipad': (255, 0, 255)}
    for s in D['parking']:
        x, y = P((s['x'], s['z'])); c = col[s['kind']] if s['src'] == 'obs' else tuple(v // 2 + 60 for v in col[s['kind']])
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=c)
    im.save(os.path.join(FIG, 'airport_overview.png'))


if __name__ == '__main__':
    main()
