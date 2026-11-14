"""Build sha3d/data/sha_airport.json and sha_airport.js (window.SHA_AIRPORT) - the Shanghai Hongqiao (ZSSS / SHA) airport
geometry for SHA Live 3D. Deterministic; run it to rebuild:

    python3 -I sha3d/tools/airport/build_airport.py [SHA3D_DIR]

Pattern: hwd3d tools/build_airport.py / data/hwd_airport.json (per-feature id, src, refs, evidence; top-level what /
licence / attribution / generator / sources / src_legend / frame / counts / checks_at_build / not_yet_sourced).
Inputs (all committed, so the build runs from a clean checkout):
  refs/cache/osm_pinned/zsss_osm_pinned.geojson   pinned, filtered, clipped OSM extract (ODbL)  [tools/osm/pin_extract.py]
  data/meas/rwy_ends.json                          runway ends measured on Sentinel-2 + Umbra      [tools/airport/rwy_ends.py]
  data/meas/twy_refit.json                         taxiway centreline re-fit on Sentinel-2 + Umbra [tools/airport/twy_refit.py]
  AIP_* below                                      short cited facts, AIP (mirror) EFF 2026-07-08 (OD3); when the local
                                                   mirror text (refs/cache/aip/derived_aip_zsss/ad2_tables.txt, never
                                                   committed) is present, every fact is probed in it (checks_at_build)
Stands, gates and stand lead-in lines are NOT in this file (task A2).
"""
import datetime
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
import shapely  # noqa: E402
import shapely.ops  # noqa: E402

PINNED = os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')
PIN_SUMMARY = os.path.join(ROOT, 'refs/cache/osm_pinned/pin_summary.json')
RWY_MEAS = os.path.join(ROOT, 'data/meas/rwy_ends.json')
TWY_MEAS = os.path.join(ROOT, 'data/meas/twy_refit.json')
AIP_TXT = os.path.join(ROOT, 'refs/cache/aip/derived_aip_zsss/ad2_tables.txt')
OUT_JSON = os.path.join(ROOT, 'data/sha_airport.json')
OUT_JS = os.path.join(ROOT, 'data/sha_airport.js')

MAG_VAR_W = 5 + 46 / 60          # AIP (mirror) AD 2.2: VAR 5 deg 46 min W (2017), annual change -42 sec
TWY_WIDTH = 23.0                  # AIP (mirror) AD 2.8: 23 m for the main designators (A, B, C, D, N, S, ...)
TWY_SHOULDER_TOTAL = 44.0         # ICAO Annex 14 code E taxiway + shoulders [from memory, inf]
R2 = lambda v: round(float(v), 2)  # noqa: E731

# ------------------------------------------------------------------------------------------------ AIP short facts
# AIP (mirror) = chart.wuhanqing.cn copy of AIP China EFF 2026-07-08, AD 2 ZSSS (OD3: reference only, short facts).
# 'probe' strings must appear verbatim in the local mirror text when it is present (checks_at_build.aip_probes).
AIP_NOTICE = ('AIP China AD 2 ZSSS (CAAC) via an unofficial mirror, EFF 2026-07-08; short cited facts; not covered by ODbL '
              '(the ODbL licence of this file does not apply to this block)')
# Only the values the simulator / renderer uses are kept (QA C1 M2, lead decision under OD3): lengths, widths,
# shoulders and blast pads (rendered), the CONC / ASPH sections (rendered; also the measured edges of rwy_ends.py),
# displaced thresholds / ends, declared distances (incl. intersection take-off), THR / DTHR elevations, PAPI side /
# distance / angle, approach-light type and length (the ALS line is drawn). Not kept: strip, RESA, SWY / CWY,
# grooving, slope chain, TDZ elevation, MEHT, REL taxiways, light remarks, bearings, PCR.
AIP_RWY = {
    '18L/36R': dict(
        length_m=3400, width_m=45, shoulder_m=7.5,
        surface_segments=[[0, 100, 'CONC'], [100, 3300, 'ASPH'], [3300, 3400, 'CONC']],
        blast_pad_m=(60, 60),
        probe=['3400×45', 'CONC (100-3300m)', 'ASPH (3300-3400m)', 'Blast pad: 60×60m on the both ends',
               'THR18L displaced 100m inwards', 'RWY shoulder: 7.5m on each side']),
    '18R/36L': dict(
        length_m=3300, width_m=60, shoulder_m=7.5,
        surface_segments=[[0, 3300, 'CONC']],
        blast_pad_m=(120, 75),
        probe=['3300×60', 'Blast pad: 120×75m on the both ends', 'ENDs of RWY18R/36L displaced 150m inwards',
               'THR18R displaced 300m inwards']),
}
AIP_END = {
    '18L': dict(thr_disp_m=100, end_disp_m=100, elev=dict(thr=2.1, dthr=2.0),
                declared=dict(TORA=3300, TODA=3300, ASDA=3300, LDA=3200),
                intersection=[dict(from_twy='T1', TORA=3188, TODA=3188, ASDA=3188)],
                papi=dict(side='left', inward_of_dthr_m=474, angle_deg=3.0),
                als=dict(type='PALS CAT I', length_m=900),
                probe=['THR 2.1m DTHR 2.0m', '18L | 3300 | 3300 | 3300 | 3200', '18L | 3188 | 3188 | 3188 | - | FM T1',
                       'PAPI LEFT 474m inward DTHR18L 3°', '18L | PALS CAT Ⅰ SFL 900 m']),
    '36R': dict(thr_disp_m=100, end_disp_m=100, elev=dict(thr=2.7, dthr=2.6),
                declared=dict(TORA=3300, TODA=3300, ASDA=3300, LDA=3200),
                intersection=[dict(from_twy='H7', TORA=3188, TODA=3188, ASDA=3188)],
                papi=dict(side='right', inward_of_dthr_m=474, angle_deg=3.0),
                als=dict(type='PALS CAT I', length_m=900),
                probe=['THR 2.7m DTHR 2.6m', '36R | 3300 | 3300 | 3300 | 3200', '36R | 3188 | 3188 | 3188 | - | FM H7',
                       'PAPI RIGHT 474m inward DTHR36R 3°', '36R | PALS CAT Ⅰ SFL 900 m']),
    '18R': dict(thr_disp_m=300, end_disp_m=150, elev=dict(thr=2.6, dthr=2.6),
                declared=dict(TORA=3150, TODA=3210, ASDA=3300, LDA=2850),
                intersection=[dict(from_twy='H2', TORA=2988, TODA=3048, ASDA=3138)],
                papi=dict(side='left', inward_of_dthr_m=393, angle_deg=3.0),
                als=dict(type='PALS CAT I', length_m=840),
                probe=['THR 2.6m DTHR 2.6m', '18R | 3150 | 3210 | 3300 | 2850', '18R | 2988 | 3048 | 3138 | - | FM H2',
                       'PAPI LEFT 393m inward DTHR18R 3°', '18R | PALS CAT Ⅰ SFL 840 m']),
    '36L': dict(thr_disp_m=300, end_disp_m=150, elev=dict(thr=2.6, dthr=2.7),
                declared=dict(TORA=3150, TODA=3210, ASDA=3300, LDA=2850),
                intersection=[dict(from_twy='H6', TORA=2988, TODA=3048, ASDA=3138)],
                papi=dict(side='right', inward_of_dthr_m=393, angle_deg=3.0),
                als=dict(type='PALS CAT I', length_m=900),
                probe=['THR 2.6m DTHR 2.7m', '36L | 3150 | 3210 | 3300 | 2850', '36L | 2988 | 3048 | 3138 | - | FM H6',
                       'PAPI RIGHT 393m inward DTHR36L 3°', '36L | PALS CAT Ⅰ SFL 900 m']),
}
AIP_GENERAL_PROBES = ['N31°11.8′ E121°20.1′ Center of RWY18L/36R', 'ELEV/Reference temperature/Mean low temperature | 3.0 m/',
                      '5°46′W(2017)/-42″',
                      'The distance between RCL18R/36L and RCL18L/36R is 365m, and their north ends aligned',
                      'Control TWR 031 | Control TWR | 111/520 | 47 | LGT',
                      'RWY holding positions(Pattern B) established at both ends of TWY A',
                      '23m : A, B, B1-B8, BN, BS, C, C1-C4, D,']
# AIP (mirror) AD 2.10 obstacles inside the detailed extent that this file uses (position = MAG bearing / distance from
# the centre of RWY 18L/36R, i.e. the scene origin; elevation in the AIP datum). Only these few rows are used.
AIP_OBSTACLES = [
    dict(use='control_tower', type='Control TWR', mag=111, dist=520, elev=47.0, probe='111/520 | 47'),
    dict(use='glide_path_18L', type='Antenna', mag=8, dist=1301, elev=17.0, probe='008/1301 | 17'),
    dict(use='glide_path_36R', type='Antenna', mag=177, dist=1301, elev=17.7, probe='177/1301 | 17.7'),
    dict(use='glide_path_36L', type='Antenna', mag=196, dist=1019, elev=17.8, probe='196/1019 | 17.8'),
    dict(use='glide_path_18R', type='Antenna', mag=349, dist=1019, elev=17.8, probe='349/1019 | 17.8'),
    dict(use='building_check', type='BLDG', mag=122, dist=892, elev=52.0, probe='122/892 | 52'),
    dict(use='tower_check', type='TOWER', mag=145, dist=1022, elev=48.0, probe='145/1022 | 48'),
    dict(use='building_check', type='BLDG', mag=151, dist=1435, elev=51.0, probe='151/1435 | 51'),
    dict(use='building_check', type='BLDG', mag=161, dist=1566, elev=49.0, probe='161/1566 | 49'),
    dict(use='building_check', type='BLDG', mag=148, dist=2056, elev=52.0, probe='148/2056 | 52'),
    dict(use='mast_check', type='Antenna', mag=280, dist=2476, elev=44.0, probe='280/2476 | 44'),
    dict(use='mast_check', type='Antenna', mag=323, dist=2159, elev=44.0, probe='323/2159 | 44'),
]
# phase-0 findings (docs/phase0/geo.md s.4): OSM taxiway runs 5-13 m off the imaged pavement (OSM minus S2, S2B / S2C)
PHASE0_FLAGS = {128706533: ('C4', 12.6, 6.8), 1408578284: ('D', -7.7, -9.7), 520931651: ('H5', 7.6, 6.6),
                128706541: ('B4', 6.4, 5.5), 16714128: ('A2', -5.1, -5.9)}

HEIGHT_RULES = {    # [inf] defaults when neither OSM nor an AIP obstacle gives a height (m above ground)
    'terminal': 25.0, 'hangar_widebody': 32.0, 'hangar': 22.0, 'business_terminal': 12.0, 'vvip': 10.0,
    'tower': 35.0, 'parking': 18.0, 'office': 20.0, 'industrial': 12.0, 'residential': 30.0, 'apartments': 40.0,
    'house': 7.0, 'train_station': 25.0, 'transportation': 20.0, 'roof': 8.0, 'commercial': 20.0, 'hotel': 40.0,
    'default': 12.0}
LEVEL_M = 3.5


UMBRA_ATTR = ('Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), '
              'modified')
LICENCE = ('ODbL 1.0 - this file is a Derivative Database of OpenStreetMap ((c) OpenStreetMap contributors), made '
           'available under the Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/). It also '
           'contains measurements made on modified Copernicus Sentinel data 2026 and on Umbra SAR Open Data (Umbra '
           'Lab, Inc., CC BY 4.0, modified). The aip_facts blocks and the other values labelled "AIP (mirror)" are '
           'short cited facts from an unofficial copy of AIP China AD 2 ZSSS (CAAC), EFF 2026-07-08, used as reference '
           '(owner decision OD3); they are not covered by the ODbL licence of this file, and no AIP list is reproduced.')
ATTRIBUTION = ['(c) OpenStreetMap contributors (ODbL 1.0) - https://www.openstreetmap.org/copyright',
               'Contains modified Copernicus Sentinel data 2026',
               UMBRA_ATTR,
               'Short facts: AIP China AD 2 ZSSS (CAAC), EFF 2026-07-08, read in an unofficial mirror ("AIP (mirror)"); '
               'not covered by the ODbL licence']
AIP_LOG_DIR = os.path.join(ROOT, 'refs/cache/aip_checks')
AIP_LOG_NOTE = ('probed at build time only when the local AIP mirror text exists; the result goes to '
                'refs/cache/aip_checks/%s (local only, never committed), so this file is byte-identical with or '
                'without the mirror (QA C1 L5)')


def write_local_log(name, obj):
    os.makedirs(AIP_LOG_DIR, exist_ok=True)
    with open(os.path.join(AIP_LOG_DIR, name), 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)


def w(lat, lon):
    x, z = F.ll_to_world(lat, lon)
    return [R2(x), R2(z)]


def ring_xz(coords):
    pts = [w(la, lo) for lo, la in coords]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def _vec_world(lo, la):
    try:
        xs, zs = zip(*[F.ll_to_world(b, a) for a, b in zip(lo, la)])
        return list(xs), list(zs)
    except TypeError:
        return F.ll_to_world(la, lo)


def mag_to_true(m):
    return (m - MAG_VAR_W) % 360


def area_xz(ring):
    return abs(Polygon(ring).area) if len(ring) >= 3 else 0.0


def main():
    fc = json.load(open(PINNED))
    pin = json.load(open(PIN_SUMMARY))
    rm = json.load(open(RWY_MEAS))
    tm = json.load(open(TWY_MEAS))
    feats = fc['features']
    by_id = {(f['properties']['@type'], f['properties']['@id']): f for f in feats}
    aip_txt = open(AIP_TXT, encoding='utf-8').read() if os.path.exists(AIP_TXT) else None
    checks = {}

    def tags(f):
        return f['properties']['tags']

    def osm_ev(f, extra=None):
        p = f['properties']
        e = {'osm': {'type': p['@type'], 'id': p['@id'], 'version': p['@version'], 'timestamp': p['@timestamp'],
                     'tags': {k: v for k, v in p['tags'].items() if not k.startswith('name:') or k == 'name:en'}}}
        if p.get('clipped'):
            e['osm']['clipped_to_extent'] = True
        if extra:
            e.update(extra)
        return e

    # ------------------------------------------------------------------ extent + aerodrome boundary
    ext = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/extent_hull1km.geojson')))['features'][0]
    ext_ring = ring_xz(ext['geometry']['coordinates'][0])
    aero_f = by_id[('relation', 21913346)]
    aero_ll = shape(aero_f['geometry'])
    aero_w = shapely.ops.transform(_vec_world, aero_ll)
    aero_polys = list(aero_w.geoms) if aero_w.geom_type == 'MultiPolygon' else [aero_w]

    # ------------------------------------------------------------------ runways
    runways = []
    rw_axes = {}
    local = {}                    # AIP comparisons for the local-only log (L5): never written into the committed file
    for ref in ('18L/36R', '18R/36L'):
        f = next(f for f in feats if tags(f).get('aeroway') == 'runway' and tags(f).get('ref') == ref)
        m = rm['runways'][ref]
        A = AIP_RWY[ref]
        (la0, lo0), (la1, lo1) = m['osm_north_node'], m['osm_south_node']
        a = F.ll_to_world(la0, lo0); b = F.ll_to_world(la1, lo1)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)          # world x/z unit vector, N -> S
        nE = (-u[1], u[0])                                     # world normal pointing east (x>0)
        if nE[0] < 0:
            nE = (-nE[0], -nE[1])
        rw_axes[ref] = (a, u, nE, L)

        def at(s, t=0.0):
            return [R2(a[0] + s * u[0] + t * nE[0]), R2(a[1] + s * u[1] + t * nE[1])]

        def ll_at(s, t=0.0):
            p = at(s, t)
            la, lo = F.world_to_ll(*p)
            return [round(la, 8), round(lo, 8)]
        sN, sS = m['placed_north_end_s_m'], m['placed_south_end_s_m']
        hdg_s = F.vec_hdg(*u)
        first, second = ref.split('/')
        half = A['width_m'] / 2
        outline = [at(sN, -half), at(sS, -half), at(sS, half), at(sN, half)]
        sh = half + A['shoulder_m']
        shoulders = [at(sN, -sh), at(sS, -sh), at(sS, sh), at(sN, sh)]
        bl, bw = A['blast_pad_m']
        blast = [{'end': first, 'ring': [at(sN - bl, -bw / 2), at(sN, -bw / 2), at(sN, bw / 2), at(sN - bl, bw / 2)]},
                 {'end': second, 'ring': [at(sS, -bw / 2), at(sS + bl, -bw / 2), at(sS + bl, bw / 2), at(sS, bw / 2)]}]
        ends = []
        prof = []
        for end_id, s_end, sgn in ((first, sN, +1), (second, sS, -1)):
            E = AIP_END[end_id]
            s_thr = s_end + sgn * E['thr_disp_m']
            s_far_end = (sS if sgn > 0 else sN) - sgn * E['end_disp_m']
            hdg = hdg_s if sgn > 0 else (hdg_s + 180) % 360
            papi_s = s_thr + sgn * E['papi']['inward_of_dthr_m']
            # side of the runway seen from the approach: approach heading = hdg; left of a southbound (hdg ~177) runway is east
            side_sign = (1 if E['papi']['side'] == 'left' else -1) * sgn
            papi_t = side_sign * (half + 15.0)
            als_end = s_thr - sgn * E['als']['length_m']
            meas_key = 'north_end_s_m' if sgn > 0 else 'south_end_s_m'
            osm_s = 0.0 if sgn > 0 else L
            prof += [(s_end, E['elev']['thr']), (s_thr, E['elev']['dthr'])]
            ends.append({
                'id': end_id,
                'heading_true_deg': round(hdg, 3),
                'osm_end_node': {'lat': [la0, la1][0 if sgn > 0 else 1], 'lon': [lo0, lo1][0 if sgn > 0 else 1],
                                 'xz': at(osm_s), 'src': 'obs', 'refs': ['osm'],
                                 'evidence': 'end node of the OSM runway way (pinned extract)'},
                'end': {'xz': at(s_end), 'lat_lon': ll_at(s_end), 's_m': R2(s_end),
                        'beyond_osm_node_m': R2((osm_s - s_end) * sgn),
                        'measured_s_m': m[meas_key], 'src': 'inf', 'refs': ['s2', 'umbra', 'aip_mirror', 'osm'],
                        'evidence': ('physical runway end (start of the runway pavement, AIP "THR"): measured on '
                                     'Sentinel-2 / Umbra at s = %.1f m (data/meas/rwy_ends.json), placed by the rule: %s'
                                     % (m[meas_key], m['placed_rule']))},
                'dthr': {'xz': at(s_thr), 'lat_lon': ll_at(s_thr), 's_m': R2(s_thr),
                         'src': 'inf', 'refs': ['aip_mirror', 'osm', 's2'],
                         'evidence': 'aip_facts.ends.%s.thr_displaced_m measured along the OSM centreline from the '
                                     'placed runway end' % end_id},
                'end_of_tora': {'xz': at(s_far_end), 's_m': R2(s_far_end),
                                'src': 'inf', 'refs': ['aip_mirror'],
                                'evidence': 'aip_facts.ends.%s.end_displaced_m at the far end' % end_id},
                'papi': {'xz': at(papi_s, papi_t), 's_m': R2(papi_s), 'lateral_m': R2(papi_t),
                         'src': 'inf', 'refs': ['aip_mirror'],
                         'evidence': 'side and distance from the DTHR: aip_facts.ends.%s.papi; the lateral offset '
                                     '(runway edge + 15 m) is a placeholder rule, not sourced [inf]' % end_id},
                'approach_lights': {'line': [at(s_thr), at(als_end)], 'src': 'inf', 'refs': ['aip_mirror'],
                                    'evidence': 'type and length: aip_facts.ends.%s.approach_lights; drawn from the DTHR '
                                                'outward along the extended centreline [inf]' % end_id},
            })
        aip_facts = {
            'notice': AIP_NOTICE, 'src': 'obs', 'refs': ['aip_mirror'],
            'length_m': A['length_m'], 'width_m': A['width_m'], 'shoulder_m': A['shoulder_m'],
            'blast_pad_m': list(A['blast_pad_m']), 'surface_segments_m': A['surface_segments'],
            'ends': {e_id: {'thr_displaced_m': AIP_END[e_id]['thr_disp_m'],
                            'end_displaced_m': AIP_END[e_id]['end_disp_m'],
                            'elev_m': dict(AIP_END[e_id]['elev']),
                            'declared_m': dict(AIP_END[e_id]['declared'],
                                               intersection=AIP_END[e_id]['intersection']),
                            'papi': dict(AIP_END[e_id]['papi']),
                            'approach_lights': dict(AIP_END[e_id]['als'])} for e_id in (first, second)},
            'fields': ('AD 2.12 (dimensions, shoulders, blast pads, surface sections, displaced THR / END, THR / DTHR '
                       'elevations: THR = runway end, DTHR = displaced threshold, metres in the AIP datum = world y), '
                       'AD 2.13 (declared distances), AD 2.14 (PAPI, approach lights)'),
            'used_by': 'runway outline / shoulders / blast pads / surface colour, DTHR and end-of-TORA points, PAPI and '
                       'ALS drawing, declared distances and THR heights in the simulator'}
        prof.sort()
        meas_edges = [{k: e[k] for k in ('edge', 's', 's2_per_scene', 'umbra', 'implied_end_s') if k in e}
                      for e in m['edges'] if e.get('s') is not None]
        local[ref] = {'osm_heading_true_deg': round(hdg_s, 3)}
        runways.append({
            'id': ref, 'osm': {'way': f['properties']['@id'], 'version': f['properties']['@version'],
                               'width_tag': tags(f).get('width'), 'length_m': m['osm_length_m']},
            'heading_true_deg': round(hdg_s, 3), 'axis_unit_xz': [round(u[0], 6), round(u[1], 6)],
            'aip_facts': aip_facts,
            'profile_y': {'points_s_y': [[R2(sv), y] for sv, y in prof], 'src': 'inf', 'refs': ['aip_mirror'],
                          'evidence': 'linear between the AIP (mirror) THR and DTHR elevations of both ends '
                                      '(aip_facts; the AIP slope chain is not transcribed); s from the OSM north end '
                                      'node'},
            'centreline': {'pts': [at(sN), at(sS)], 'src': 'obs', 'refs': ['osm', 's2', 'umbra'],
                           'evidence': 'OSM way axis (straight to < 0.1 m), extended to the placed ends'},
            'outline': {'ring': outline, 'src': 'inf', 'refs': ['aip_mirror', 'osm', 's2'],
                        'evidence': 'rectangle: placed ends x aip_facts.width_m on the OSM axis'},
            'shoulders': {'ring': shoulders, 'src': 'inf', 'refs': ['aip_mirror'],
                          'evidence': 'aip_facts.shoulder_m on each side'},
            'blast_pads': [dict(bp, src='inf', refs=['aip_mirror', 's2', 'umbra'],
                                evidence='aip_facts.blast_pad_m beyond each end (18R/36L outer edges measured on S2/'
                                         'Umbra 120 m beyond the ends, data/meas/rwy_ends.json)') for bp in blast],
            'ends': ends,
            'measurement': {'edges': meas_edges, 'measured_length_m': m['measured_length_m'],
                            'measured_minus_aip_m': m['measured_minus_aip_m'],
                            'placed_minus_measured_south_m': m.get('placed_minus_measured_south_m'),
                            'osm_vs_imagery_note': 'docs/phase0/geo.md s.5: X-Plane ends lie 11.0 (18L), 0.2 (36R), '
                                                   '15.8 (18R), 11.5 (36L) m beyond the OSM end nodes; S2 showed the '
                                                   'north ends 9-13 m beyond. This build measures %.1f / %.1f m.'
                                                   % (-m['north_end_s_m'], m['south_end_s_m'] - m['osm_length_m']),
                            'src': 'obs', 'refs': ['s2', 'umbra'],
                            'evidence': 'tools/airport/rwy_ends.py -> data/meas/rwy_ends.json'},
            'src': 'obs', 'refs': ['osm', 'aip_mirror', 's2', 'umbra'],
            'evidence': 'OSM centreline (way %d v%d); dimensions, declared distances, elevations and lighting in '
                        'aip_facts (AIP (mirror) short facts, own notice); ends measured on Sentinel-2 and Umbra'
                        % (f['properties']['@id'], f['properties']['@version'])})
    # checks: separation, alignment
    (aE, uE, nEE, LE), (aW, uW, nEW, LW) = rw_axes['18L/36R'], rw_axes['18R/36L']
    sepN = (aE[0] - aW[0]) * nEW[0] + (aE[1] - aW[1]) * nEW[1]
    bS = (aE[0] + LE * uE[0], aE[1] + LE * uE[1])
    sepS = abs(((bS[0] - aW[0]) * nEW[0] + (bS[1] - aW[1]) * nEW[1]))
    checks['runways'] = {
        'centreline_separation_m': {'at_18L_end': R2(sepN), 'at_36R_end': R2(sepS),
                                    'aip': 365, 'aip_note': 'AIP (mirror) AD 2.24: "365m, and their north ends aligned"'},
        'north_end_alignment_m': rm['north_end_alignment'],
        'ends_placed_beyond_osm_nodes_m': {e['id']: e['end']['beyond_osm_node_m'] for r in runways for e in r['ends']},
        'measured_minus_aip_length_m': {r['id']: r['measurement']['measured_minus_aip_m'] for r in runways},
    }

    # ------------------------------------------------------------------ taxiways / taxilanes (with S2 re-fit)
    moves = tm['vertex_moves']
    runs_by_way = {}
    for r in tm['runs']:
        runs_by_way.setdefault(r['way'], []).append(r)
    aprons_ll = [shape(f['geometry']) for f in feats if tags(f).get('aeroway') == 'apron']
    apron_union_ll = unary_union(aprons_ll)

    def moved_coords(coords):
        out, nm, mx = [], 0, 0.0
        for lo, la in coords:
            k = f'{lo:.7f},{la:.7f}'
            if k in moves:
                lo2, la2 = moves[k]['to']; nm += 1
                mx = max(mx, math.hypot(moves[k]['dE'], moves[k]['dN']))
                out.append([lo2, la2])
            else:
                out.append([lo, la])
        return out, nm, mx

    taxiways, taxilanes = [], []
    for f in feats:
        t = tags(f)
        if t.get('aeroway') not in ('taxiway', 'taxilane') and not (t.get('aeroway') == 'construction'
                                                                     and t.get('construction') == 'taxiway'):
            continue
        g = f['geometry']
        lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates'] if g['type'] == 'MultiLineString' else []
        if not lines:
            continue
        ll = LineString(lines[0]) if len(lines) == 1 else shape(g)
        in_apron = ll.intersection(apron_union_ll).length / max(ll.length, 1e-12)
        if t.get('aeroway') == 'taxilane':
            kind, krule = 'taxilane', 'OSM aeroway=taxilane'
        elif 'ref' not in t and in_apron > 0.5:
            kind, krule = 'taxilane', 'OSM aeroway=taxiway without ref, %.0f %% inside an OSM apron [inf]' % (100 * in_apron)
        else:
            kind, krule = 'taxiway', 'OSM aeroway=taxiway' + (' with ref' if 'ref' in t else ' without ref, outside the aprons')
        status = 'construction' if (t.get('aeroway') == 'construction' or 'construction' in t) else 'open'
        pts_all, nmoved, maxmove = [], 0, 0.0
        for c in lines:
            mc, nm, mx = moved_coords(c)
            nmoved += nm; maxmove = max(maxmove, mx)
            pts_all.append([w(la, lo) for lo, la in mc])
        length = sum(LineString(p).length for p in pts_all if len(p) > 1)
        wid = f['properties']['@id']
        runs = runs_by_way.get(wid, [])
        refit = None
        own = any(r['refit'] for r in runs)
        if runs:
            refit = {'runs': [{k: r.get(k) for k in ('v0', 'v1', 'length_m', 'measured', 'offset_m', 'sources_used',
                                                      'source_spread_m', 'rule', 'refit', 'width_s2_m')} for r in runs],
                     'own_run_refit': own,
                     'rule': 'offset_m = imaged pavement centre minus OSM along the run normal (east/north '
                             'positive), relative to the common OSM-S2 registration and the runway-band Umbra '
                             'registration; measured when >= 2 of S2B / S2C / Umbra agree within 2 m, or (runs >= 150 m) '
                             'Umbra and one S2 scene within 2.5 m; moved when |offset| >= 3.5 m '
                             '(tools/airport/twy_refit.py)',
                     'src': 'obs', 'refs': ['s2', 'umbra'], 'evidence': 'data/meas/twy_refit.json'}
        flag = None
        single = [r['single_source_flag'] for r in runs if r.get('single_source_flag')]
        dissent = ['run v%d-v%d moved %+.2f m by %s; %s disagree%s by > 2.5 m' % (
            r['v0'], r['v1'], r['offset_m'], '+'.join(r['sources_used']),
            ', '.join('%s %+.1f m' % kv for kv in sorted(r['dissent'].items())), 's' if len(r['dissent']) == 1 else '')
            for r in runs if r.get('refit') and r.get('dissent')]
        veto = [r['umbra_veto'] for r in runs if r.get('umbra_veto')]
        if wid in PHASE0_FLAGS or single or dissent or veto:
            flag = {}
            if veto:
                flag['umbra_veto'] = veto
                flag['umbra_veto_note'] = ('two S2 scenes agree on a move that the sharper Umbra centre contradicts: '
                                           'left at the OSM position (re-verify N2); check on a better image')
            if dissent:
                flag['dissent'] = dissent
                flag['dissent_note'] = 'a third source disagrees with the two that moved the run: check on a better image'
            if wid in PHASE0_FLAGS:
                rf, a_, b_ = PHASE0_FLAGS[wid]
                done = any(r['refit'] for r in runs)
                flag['phase0'] = 'docs/phase0/geo.md: OSM minus S2 %+.1f m (S2B) / %+.1f m (S2C) on run %s' % (a_, b_, rf)
                flag['status'] = ('moved onto the imaged pavement (see refit)' if done else
                                  'not moved: fewer than 2 sources gave an agreeing centre in this build')
            if single:
                flag['single_source'] = single
                flag['single_source_note'] = ('one source sees an offset >= 3.5 m but no second source agrees: left at '
                                              'the OSM position (QA C1 M1); candidates for a better image')
        rec = {'id': 'osm:way/%d' % wid, 'kind': kind, 'kind_rule': krule, 'ref': t.get('ref'), 'status': status,
               'oneway': t.get('oneway') == 'yes', 'bridge': t.get('bridge') == 'yes',
               'pts': pts_all[0] if len(pts_all) == 1 else None, 'parts': pts_all if len(pts_all) > 1 else None,
               'len_m': round(length, 1),
               'width_m': TWY_WIDTH if kind == 'taxiway' else None,
               'width_src': 'inf' if kind == 'taxiway' else None,
               'width_note': ('23 m rule: AIP (mirror) AD 2.8 gives 23 m for the main designators (A, B, C, D, N, S, '
                              'BN, BS ...); links such as the H crossings, the A1-A4 rapid exits and the D / K links '
                              'are wider (values not transcribed; see width_s2_m)') if kind == 'taxiway' else None,
               'width_s2_m': max((r['width_s2_m'] for r in runs if r.get('width_s2_m')), default=None),
               'refit': refit, 'flag': flag,
               'vertices_moved': nmoved, 'max_move_m': R2(maxmove),
               'moved_note': (None if not nmoved else 'own straight run(s) re-fitted to the imaged pavement' if own else
                              'only vertices next to a re-fitted neighbouring way were moved: the shared junction '
                              'vertex and, along this way, the move tapered to zero over 40 m '
                              '(data/meas/twy_refit.json vertex_moves, kind run / taper)'),
               'src': 'obs', 'refs': ['osm'] + (['s2', 'umbra'] if nmoved else []),
               'evidence': osm_ev(f)}
        (taxiways if kind == 'taxiway' else taxilanes).append(rec)
    checks['taxiway_refit'] = dict(tm['summary'], phase0_flags={
        PHASE0_FLAGS[k][0]: ('moved' if any(r['refit'] for r in runs_by_way.get(k, [])) else 'not moved')
        for k in PHASE0_FLAGS})
    checks['taxiway_refs'] = sorted({t['ref'] for t in taxiways if t['ref']}, key=lambda s: (s[0], len(s), s))

    # ------------------------------------------------------------------ holding positions
    holds = []
    twy_lines = [(t, LineString(t['pts'])) for t in taxiways + taxilanes if t['pts'] and len(t['pts']) > 1]
    for f in feats:
        if tags(f).get('aeroway') != 'holding_position':
            continue
        lo, la = f['geometry']['coordinates']
        k = f'{lo:.7f},{la:.7f}'
        moved = k in moves
        if moved:
            lo, la = moves[k]['to']
        x, z = F.ll_to_world(la, lo)
        best = None
        for ref, (a, u, nE, L) in rw_axes.items():
            dx, dz = x - a[0], z - a[1]
            along = dx * u[0] + dz * u[1]; cl = dx * nE[0] + dz * nE[1]
            if best is None or abs(cl) < abs(best[2]):
                best = (ref, along, cl)
        p = Point(x, z)
        on = min(twy_lines, key=lambda tl: tl[1].distance(p))
        holds.append({'id': 'osm:node/%d' % f['properties']['@id'], 'x': R2(x), 'z': R2(z),
                      'lat_lon': [round(la, 8), round(lo, 8)], 'runway': best[0], 'along_m': R2(best[1]),
                      'cl_dist_m': R2(best[2]), 'side': 'west' if best[2] < 0 else 'east',
                      'on_way': on[0]['id'], 'twy_ref': on[0]['ref'], 'on_way_dist_m': R2(on[1].distance(p)),
                      'designator': None, 'moved_with_refit': moved,
                      'src': 'obs', 'refs': ['osm'],
                      'evidence': osm_ev(f, {'note': 'OSM aeroway=holding_position (no ref / designator in OSM); '
                                                     'runway = nearest centreline'})})
    cl = sorted(abs(h['cl_dist_m']) for h in holds)
    checks['holds'] = {'n': len(holds), 'cl_dist_m_min_median_max': [cl[0], cl[len(cl) // 2], cl[-1]] if cl else None,
                       'by_runway_side': {k: sum(1 for h in holds if f"{h['runway']} {h['side']}" == k)
                                          for k in sorted({f"{h['runway']} {h['side']}" for h in holds})}}

    # ------------------------------------------------------------------ aprons, helipads
    aprons, helipads = [], []
    for f in feats:
        t = tags(f)
        if t.get('aeroway') in ('apron', 'helipad') and f['geometry']['type'] in ('Polygon', 'MultiPolygon'):
            gw = shapely.ops.transform(_vec_world, shape(f['geometry']))
            polys = list(gw.geoms) if gw.geom_type == 'MultiPolygon' else [gw]
            rec = {'id': 'osm:%s/%d' % (f['properties']['@type'], f['properties']['@id']),
                   'ring': [[R2(x), R2(z)] for x, z in list(polys[0].exterior.coords)[:-1]],
                   'holes': [[[R2(x), R2(z)] for x, z in list(h.coords)[:-1]] for h in polys[0].interiors] or None,
                   'area_m2': round(gw.area, 1), 'src': 'obs', 'refs': ['osm'], 'evidence': osm_ev(f)}
            if t['aeroway'] == 'apron':
                rec['osm_ref'] = t.get('ref')
                rec['name_note'] = ('OSM ref "%s" (2015 tag; matches the AIP apron numbering 2/4/6 in AD 2.8 "Apron Nr. '
                                    '4, 6" [inf])' % t['ref']) if t.get('ref') else 'no ref (east apron, T1 side)'
                aprons.append(rec)
            else:
                helipads.append(rec)

    # ------------------------------------------------------------------ surfaces (derived)
    twy_buf, sh_buf = [], []
    rw_polys = [Polygon(r['outline']['ring']) for r in runways]
    rw_sh = unary_union([Polygon(r['shoulders']['ring']) for r in runways] +
                        [Polygon(bp['ring']) for r in runways for bp in r['blast_pads']])
    apron_w = unary_union([Polygon(a['ring']) for a in aprons])
    for t in taxiways:
        for p in ([t['pts']] if t['pts'] else t['parts']):
            if len(p) > 1:
                ls = LineString(p)
                twy_buf.append(ls.buffer(TWY_WIDTH / 2, cap_style='flat', join_style='round'))
                sh_buf.append(ls.buffer(TWY_SHOULDER_TOTAL / 2, cap_style='flat', join_style='round'))
    twy_surf = unary_union(twy_buf).difference(unary_union(rw_polys)).simplify(0.3)
    twy_sh = unary_union(sh_buf).difference(unary_union(rw_polys + [rw_sh, apron_w])).difference(twy_surf).simplify(0.3)

    def rings_of(g, src, refs, ev):
        gs = list(g.geoms) if hasattr(g, 'geoms') else [g]
        out = []
        for pg in gs:
            if pg.is_empty or pg.area < 5:
                continue
            out.append({'ring': [[R2(x), R2(z)] for x, z in list(pg.exterior.coords)[:-1]],
                        'holes': [[[R2(x), R2(z)] for x, z in list(h.coords)[:-1]] for h in pg.interiors if
                                  Polygon(h).area > 5] or None, 'src': src, 'refs': refs, 'evidence': ev})
        return out
    ev_rw = 'runway rectangle: placed ends x aip_facts.width_m on the OSM axis (runways[].outline)'
    ev_sh = ('runway shoulders (aip_facts.shoulder_m) and blast pads (aip_facts.blast_pad_m) on the placed ends, minus '
             'the runway rectangles')
    ev_tw = ('OSM taxiway centrelines (after the re-fit, data/meas/twy_refit.json) buffered to %.0f m (AIP (mirror) '
             'AD 2.8 main-designator width), minus the runways' % TWY_WIDTH)
    ev_ts = ('taxiway shoulders to %.0f m total (ICAO code E [from memory]; Sentinel-2 median NDVI width of the measured '
             'runs: %.1f m) minus runways, runway shoulders, aprons and taxiway pavement'
             % (TWY_SHOULDER_TOTAL, tm['summary']['width_s2_median_m']))
    surfaces = {
        'runway': [{'runway': r['id'], 'ring': r['outline']['ring'], 'src': 'inf', 'refs': ['aip_mirror', 'osm', 's2'],
                    'evidence': ev_rw} for r in runways],
        'runway_shoulders_blast_pads': rings_of(rw_sh.difference(unary_union(rw_polys)), 'inf', ['aip_mirror', 'osm'],
                                                ev_sh),
        'taxiway': rings_of(twy_surf, 'inf', ['osm', 'aip_mirror', 's2', 'umbra'], ev_tw),
        'taxiway_shoulders': rings_of(twy_sh, 'inf', ['osm'], ev_ts),
    }

    # ------------------------------------------------------------------ AIP obstacle positions (few rows)
    obst = []
    for o in AIP_OBSTACLES:
        tb = mag_to_true(o['mag'])
        x, z = F.hdg_vec(tb)
        obst.append(dict(o, true_brg=round(tb, 2), xz=[R2(o['dist'] * x), R2(o['dist'] * z)]))

    # ------------------------------------------------------------------ buildings
    def b_kind(t):
        a = t.get('aeroway'); b = t.get('building')
        nm = t.get('name', '') + ' ' + t.get('name:en', '')
        if a == 'terminal':
            if '公务机' in nm:
                return 'business_terminal'
            if 'VVIP' in nm:
                return 'vvip'
            return 'terminal'
        if a == 'hangar' or b == 'hangar':
            return 'hangar'
        if t.get('man_made') == 'tower':
            return 'tower'
        if t.get('amenity') == 'parking' or t.get('parking'):
            return 'parking'
        if t.get('tourism') == 'hotel':
            return 'hotel'
        if b in HEIGHT_RULES:
            return b
        return 'building'

    buildings, context_buildings = [], []
    aero_buf = aero_w.buffer(60)
    ROLE_IDS = {'osm:way/93184730', 'osm:relation/21913345', 'osm:way/469610770', 'osm:way/1443258835',
                'osm:way/327613444', 'osm:relation/21913196', 'osm:way/1576039982', 'osm:way/1576039987'}
    obst_pts = [(o, Point(*o['xz'])) for o in obst if o['use'] in ('building_check', 'tower_check', 'mast_check')]
    bfeats = []
    for f in feats:
        t = tags(f)
        if f['geometry'] is None or f['geometry']['type'] not in ('Polygon', 'MultiPolygon'):
            continue
        if not ('building' in t or t.get('aeroway') in ('terminal', 'hangar')):
            continue
        bfeats.append((f, shapely.ops.transform(_vec_world, shape(f['geometry']))))
    nearest_b = {}                     # obstacle index -> id of the nearest footprint within 25 m
    for k_, (o, p) in enumerate(obst_pts):
        d_, f_ = min(((gw_.distance(p), f_) for f_, gw_ in bfeats), key=lambda q: q[0])
        if d_ <= 25:
            nearest_b[k_] = f_['properties']['@id']
    for f, gw in bfeats:
        t = tags(f)
        if gw.is_empty:
            continue
        polys = list(gw.geoms) if gw.geom_type == 'MultiPolygon' else [gw]
        kind = b_kind(t)
        hgt, hsrc, hev = None, None, None
        if t.get('height'):
            try:
                hgt, hsrc, hev = float(t['height'].split()[0]), 'obs', 'OSM height tag'
            except ValueError:
                pass
        if hgt is None and t.get('building:levels'):
            try:
                lv = float(t['building:levels'])
                hgt, hsrc, hev = round(lv * LEVEL_M + 1.0, 1), 'inf', 'OSM building:levels %g x %.1f m + 1 m' % (lv, LEVEL_M)
            except ValueError:
                pass
        aipm = None
        for k_, (o, p) in enumerate(obst_pts):
            d = gw.distance(p)
            if nearest_b.get(k_) == f['properties']['@id']:
                aipm = dict(type=o['type'], elev_m=o['elev'], dist_to_footprint_m=R2(d))
                if o['type'] == 'Antenna':
                    aipm['note'] = 'an antenna (AIP elevation = antenna top), not used as the building height'
                elif hgt is None:
                    hgt, hsrc = round(o['elev'] - F.GROUND_Y, 1), 'inf'
                    hev = ('AIP (mirror) AD 2.10 obstacle (%s, elevation %.1f m) %.0f m from this footprint; height = '
                           'elevation - ground_y %.1f [inf: match by position, bearing rounded to 1 deg]'
                           % (o['type'], o['elev'], d, F.GROUND_Y))
        area = gw.area
        if hgt is None:
            rk = kind
            if kind == 'hangar':
                rk = 'hangar_widebody' if area > 12000 else 'hangar'
            hgt = HEIGHT_RULES.get(rk, HEIGHT_RULES['default']); hsrc = 'inf'
            hev = 'rule by kind "%s": %.0f m (HEIGHT_RULES in build_airport.py; no OSM height, levels or AIP obstacle)' % (rk, hgt)
        name = t.get('name'); name_en = t.get('name:en')
        rec = {'id': 'osm:%s/%d' % (f['properties']['@type'], f['properties']['@id']), 'kind': kind,
               'name': name, 'name_en': name_en,
               'ring': [[R2(x), R2(z)] for x, z in list(polys[0].exterior.coords)[:-1]],
               'more_rings': [[[R2(x), R2(z)] for x, z in list(pg.exterior.coords)[:-1]] for pg in polys[1:]] or None,
               'area_m2': round(area, 1), 'height_m': hgt, 'height_src': hsrc, 'height_evidence': hev,
               'aip_obstacle_match': aipm, 'src': 'obs', 'refs': ['osm'], 'evidence': osm_ev(f)}
        if gw.intersects(aero_buf) or rec['id'] in ROLE_IDS or kind in ('terminal', 'hangar', 'tower',
                                                                          'business_terminal', 'vvip'):
            buildings.append(rec)
        else:
            cb = {k: rec[k] for k in ('id', 'kind', 'name', 'name_en', 'ring', 'more_rings', 'area_m2', 'height_m',
                                      'height_src', 'height_evidence', 'aip_obstacle_match', 'src')}
            cb['evidence'] = {'osm': {k: rec['evidence']['osm'][k] for k in ('type', 'id', 'version')}}
            if rec['evidence']['osm'].get('clipped_to_extent'):
                cb['evidence']['osm']['clipped_to_extent'] = True
            context_buildings.append(cb)
    # roles for named airport buildings
    roles = {
        'osm:way/93184730': ('T1', 'Terminal 1 (OSM building=hall, source=estimation)'),
        'osm:relation/21913345': ('T2', 'Terminal 2 (OSM relation re-created 2026-11-06; piers are part of this outline)'),
        'osm:way/469610770': ('FBO', 'Hongqiao business aviation terminal (OSM name 虹桥公务机楼); FBO opened 2010 '
                                     '(field.md / avinex 2010: terminal 3,100 m2)'),
        'osm:way/1443258835': ('VVIP', 'East-area VVIP terminal (OSM name)'),
        'osm:way/327613444': ('MU_hangar', 'China Eastern Airlines hangar (OSM name 中国东方航空公司机库); AIP (mirror) AD 2.4: '
                                           '"China Eastern Airlines hangar: two B747-400 and two narrow body aircraft"'),
        'osm:relation/21913196': ('MU_base_office', 'China Eastern office building (OSM operator 中国东方航空)'),
        'osm:way/1576039982': ('tower_sw_1', 'untyped man_made=tower building in the south-west (added 2026-11-06); '
                                             'role unknown (possibly a west tower: unverified)'),
        'osm:way/1576039987': ('tower_sw_2', 'second untyped man_made=tower building next to it (same edit)'),
    }
    for b in buildings:
        if b['id'] in roles:
            b['role'], b['role_note'] = roles[b['id']]
            b['role_src'] = 'obs' if b['role'] in ('T1', 'T2', 'FBO', 'VVIP', 'MU_hangar', 'MU_base_office') else 'inf'
        elif b['kind'] == 'hangar':
            b['role'] = 'hangar'
            b['role_note'] = ('OSM aeroway=hangar without name; AIP (mirror) AD 2.4 lists a small hangar (one A300), a '
                              'big hangar (two B747-400 + two narrow-body), the China Eastern hangar and business '
                              'aircraft hangars Nr.1 / Nr.2 (one B737-300 + one GULF V each); which OSM hangar is which '
                              'is inferred from size only: %s'
                              % ('big / wide-body (> 12,000 m2)' if b['area_m2'] > 12000 else
                                 'business aircraft hangar size (< 6,000 m2)' if b['area_m2'] < 6000 else 'medium'))
            b['role_src'] = 'inf'
    # control tower (OSM node; AIP obstacle)
    twr_f = by_id[('node', 3342630333)]
    lo, la = twr_f['geometry']['coordinates']
    tx, tz = F.ll_to_world(la, lo)
    o = next(o for o in obst if o['use'] == 'control_tower')
    d_aip = math.hypot(tx - o['xz'][0], tz - o['xz'][1])
    control_tower = {'id': 'osm:node/3342630333', 'x': R2(tx), 'z': R2(tz), 'lat_lon': [la, lo],
                     'height_m': round(o['elev'] - F.GROUND_Y, 1), 'top_elev_m': o['elev'],
                     'height_src': 'inf',
                     'height_evidence': ('AIP (mirror) AD 2.10 "Control TWR" elevation 47 m (lit) minus ground_y %.1f m '
                                         '[the AIP gives elevation, not height]' % F.GROUND_Y),
                     'aip_position_check_m': R2(d_aip),
                     'aip_position_note': ('AIP bearing 111 MAG / 520 m from the RWY 18L/36R centre -> %.2f deg true '
                                           '(VAR 5 deg 46 min W) -> world (%.1f, %.1f); OSM node %.1f m from it '
                                           '(bearing rounded to 1 deg = +-4.5 m across, distance rounding +-0.5 m)'
                                           % (o['true_brg'], o['xz'][0], o['xz'][1], d_aip)),
                     'form': None, 'form_note': 'cab and shaft form not sourced (not_yet_sourced)',
                     'src': 'obs', 'refs': ['osm', 'aip_mirror'], 'evidence': osm_ev(twr_f)}
    checks['control_tower_osm_vs_aip_m'] = R2(d_aip)
    # inferred glide-path antennas (AIP obstacle rows)
    navaids = []
    for o in obst:
        if not o['use'].startswith('glide_path'):
            continue
        end_id = o['use'].split('_')[-1]
        r = next(r for r in runways if end_id in r['id'])
        a, u, nE, L = rw_axes[r['id']]
        e = next(e for e in r['ends'] if e['id'] == end_id)
        dx, dz = o['xz'][0] - a[0], o['xz'][1] - a[1]
        along = dx * u[0] + dz * u[1]; lat_ = dx * nE[0] + dz * nE[1]
        sgn = 1 if end_id == r['id'].split('/')[0] else -1
        la_, lo_ = F.world_to_ll(*o['xz'])
        navaids.append({'id': 'gp:' + end_id, 'kind': 'ils_glide_path_antenna', 'runway_end': end_id,
                        'x': o['xz'][0], 'z': o['xz'][1], 'lat_lon': [round(la_, 7), round(lo_, 7)],
                        'top_elev_m': o['elev'], 'height_m': round(o['elev'] - F.GROUND_Y, 1),
                        'beyond_dthr_m': R2((along - e['dthr']['s_m']) * sgn),
                        'from_centreline_m': R2(lat_), 'side': 'east' if lat_ > 0 else 'west',
                        'src': 'inf', 'refs': ['aip_mirror'],
                        'evidence': ('AIP (mirror) AD 2.10 obstacle "%s", %d deg MAG / %d m from the RWY 18L/36R centre, '
                                     'elevation %.1f m -> world position (+-%.0f m across from the 1 deg rounding); '
                                     'read as the %s glide-path antenna because it lies %.0f m beyond that DTHR and '
                                     '%.0f m beside the centreline [inf]'
                                     % (o['type'], o['mag'], o['dist'], o['elev'], o['dist'] * math.radians(0.5),
                                        end_id, (along - e['dthr']['s_m']) * sgn, abs(lat_)))})
    checks['aip_obstacles_matched_to_buildings'] = [
        {'type': b['aip_obstacle_match']['type'], 'elev_m': b['aip_obstacle_match']['elev_m'], 'building': b['id'],
         'kind': b['kind'], 'dist_m': b['aip_obstacle_match']['dist_to_footprint_m']}
        for b in buildings + context_buildings if b.get('aip_obstacle_match')]
    matched = {(m['type'], m['elev_m']) for m in checks['aip_obstacles_matched_to_buildings']}
    checks['aip_obstacles_unmatched'] = [
        {'type': o['type'], 'elev_m': o['elev'], 'xz': o['xz'], 'note': 'no OSM building footprint within 25 m'}
        for o in obst if o['use'] in ('building_check', 'tower_check', 'mast_check') and (o['type'], o['elev']) not in matched
        and Polygon(ext_ring).contains(Point(*o['xz']))]

    # ------------------------------------------------------------------ context within the extent
    road_cls = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'motorway_link', 'trunk_link', 'primary_link',
                'secondary_link', 'tertiary_link'}
    rail_cls = {'rail', 'subway', 'light_rail', 'monorail', 'narrow_gauge', 'construction'}
    ctx = {'roads': [], 'rail': [], 'water_lines': [], 'water_areas': [], 'hub': [], 'buildings': context_buildings}

    def lines_xz(g):
        ls = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
        return [[w(la, lo) for lo, la in c] for c in ls]
    for f in feats:
        t = tags(f); g = f['geometry']
        if g is None:
            continue
        pid = 'osm:%s/%d' % (f['properties']['@type'], f['properties']['@id'])
        cev = {'osm': {'type': f['properties']['@type'], 'id': f['properties']['@id'],
                       'version': f['properties']['@version']}}
        if f['properties'].get('clipped'):
            cev['osm']['clipped_to_extent'] = True
        if t.get('highway') in road_cls and g['type'] in ('LineString', 'MultiLineString'):
            ctx['roads'].append({'id': pid, 'class': t['highway'], 'ref': t.get('ref'), 'name': t.get('name'),
                                 'name_en': t.get('name:en'), 'layer': t.get('layer'), 'bridge': t.get('bridge'),
                                 'tunnel': t.get('tunnel'), 'oneway': t.get('oneway'), 'lanes': t.get('lanes'),
                                 'lines': lines_xz(g), 'src': 'obs', 'evidence': cev})
        elif t.get('railway') in rail_cls and g['type'] in ('LineString', 'MultiLineString') and \
                (t['railway'] != 'construction' or t.get('construction') in rail_cls):
            ctx['rail'].append({'id': pid, 'railway': t['railway'], 'service': t.get('service'), 'name': t.get('name'),
                                'name_en': t.get('name:en'), 'layer': t.get('layer'), 'bridge': t.get('bridge'),
                                'tunnel': t.get('tunnel'), 'lines': lines_xz(g), 'src': 'obs', 'evidence': cev})
        elif t.get('waterway') in ('river', 'canal', 'ditch', 'drain', 'stream') and g['type'] in ('LineString', 'MultiLineString'):
            ctx['water_lines'].append({'id': pid, 'waterway': t['waterway'], 'name': t.get('name'),
                                       'name_en': t.get('name:en'), 'tunnel': t.get('tunnel'), 'lines': lines_xz(g),
                                       'src': 'obs', 'evidence': cev})
        elif (t.get('natural') == 'water' or t.get('water') or t.get('waterway') == 'riverbank') and \
                g['type'] in ('Polygon', 'MultiPolygon'):
            gw = shapely.ops.transform(_vec_world, shape(g))
            for pg in (gw.geoms if gw.geom_type == 'MultiPolygon' else [gw]):
                ctx['water_areas'].append({'id': pid, 'water': t.get('water'), 'name': t.get('name'),
                                           'ring': [[R2(x), R2(z)] for x, z in list(pg.exterior.coords)[:-1]],
                                           'area_m2': round(pg.area, 1), 'src': 'obs', 'evidence': cev})
        if (t.get('railway') == 'station' or t.get('public_transport') == 'station' or
                t.get('building') in ('train_station', 'transportation')):
            c = shape(g).representative_point()
            ctx['hub'].append({'id': pid, 'name': t.get('name'), 'name_en': t.get('name:en'),
                               'kind': t.get('station') or t.get('building') or t.get('railway'),
                               'xz': w(c.y, c.x), 'src': 'obs', 'evidence': cev})

    # ------------------------------------------------------------------ AIP probes (local mirror only)
    probes = AIP_GENERAL_PROBES + [p for r in AIP_RWY.values() for p in r['probe']] + \
        [p for e in AIP_END.values() for p in e['probe']] + [o['probe'] for o in AIP_OBSTACLES]
    checks['aip_probes'] = {'n': len(probes), 'where': AIP_LOG_NOTE % 'build_airport.json'}
    if aip_txt:
        miss = [p for p in probes if p not in aip_txt]
        write_local_log('build_airport.json', {'aip_probes': {'n': len(probes), 'found': len(probes) - len(miss),
                                                              'missing': miss},
                                               'osm_runway_headings_true_deg': local,
                                               'mirror_text': 'refs/cache/aip/derived_aip_zsss/ad2_tables.txt'})
    checks['origin'] = {'frame_origin': [F.ORIGIN_LAT, F.ORIGIN_LON],
                        'osm_nodes': pin['origin_nodes_check'],
                        'midpoint_matches': all(abs(v) < 1e-12 for v in (
                            (pin['origin_nodes_check']['3336195147'][0] + pin['origin_nodes_check']['13556389849'][0]) / 2
                            - F.ORIGIN_LAT,
                            (pin['origin_nodes_check']['3336195147'][1] + pin['origin_nodes_check']['13556389849'][1]) / 2
                            - F.ORIGIN_LON))}
    checks['extent_km2'] = pin['extent']['area_km2']
    checks['sensitive_filter'] = {'dropped_total': sum(pin['dropped_sensitive'].values()),
                                  'by_class': pin['dropped_sensitive'], 'note': pin['dropped_note']}
    checks['k_dem'] = {'k_dem_m': F.K_DEM, 'sd_m': F.K_DEM_SD, 'note': 'frame.py header'}

    # ------------------------------------------------------------------ assemble
    out = {
        'what': ('Shanghai Hongqiao International Airport (ZSSS / SHA) airport geometry for SHA Live 3D: runways (OSM '
                 'centrelines; ends measured on Sentinel-2 and Umbra SAR; dimensions, displaced thresholds, declared '
                 'distances, THR elevations and lighting as short facts from an unofficial AIP mirror, in one '
                 'aip_facts block per runway with its own notice), taxiways and '
                 'taxilanes (OSM, re-fitted to Sentinel-2 where measured), holding positions, aprons, helipads, '
                 'derived surface polygons, buildings with heights (OSM / AIP obstacle / rule), the control tower, '
                 'inferred glide-path antennas, the aerodrome boundary, and context (Hongqiao transport hub, roads, '
                 'rail, canals, buildings) inside the detailed extent. No stands (task A2).'),
        'licence': LICENCE,
        'attribution': ATTRIBUTION,
        'build_note': ('built from committed inputs only; a clean checkout without the local AIP mirror gives the same '
                       'bytes (the AIP probes go to a local log, checks_at_build.aip_probes; QA C1 L5)'),
        'generator': 'tools/airport/build_airport.py (deterministic; python3 -I tools/airport/build_airport.py)',
        'built_utc': None,
        'sources': {
            'osm': {'what': 'OpenStreetMap API 0.6, downloaded %s - %s, filtered and clipped (refs/cache/osm_pinned/)'
                            % tuple(pin['downloaded_utc']),
                    'file': 'refs/cache/osm_pinned/zsss_osm_pinned.geojson', 'licence': 'ODbL 1.0',
                    'url': 'https://www.openstreetmap.org/copyright'},
            'aip_mirror': {'what': 'AIP China AD 2 ZSSS, EFF 2026-07-08, unofficial mirror chart.wuhanqing.cn (AD 2.24 '
                                   'text); official eAIP not read (login; owner decision OD3)',
                           'file': 'refs/cache/aip/ (local only, never committed)', 'licence': 'none published; '
                           'short cited facts only', 'status': 'AIP (mirror)',
                           'note': 'AMDT 12/2026 (effective 26 Nov 2026) changes the WDI positions at ZSSS; not reflected'},
            's2': {'what': 'Sentinel-2 L2A tile 51RUQ, S2B 2026-10-14 and S2C 2026-02-21 (Earth Search COG crops, cut '
                           'to the detailed extent: tools/geo/s2_cut_extent.py)',
                   'file': 'refs/cache/s2/', 'licence': 'Copernicus Sentinel data legal notice',
                   'attribution': 'Contains modified Copernicus Sentinel data 2026'},
            'umbra': {'what': 'Umbra SAR Open Data, UMBRA-05 spotlight 2024-06-02T01:46:48Z, GEC (1.4 m overview)',
                      'file': 'refs/cache/imagery/umbra_opendata/umbra_gec_ovr4.tif (local)', 'licence': 'CC BY 4.0',
                      'licence_url': 'https://creativecommons.org/licenses/by/4.0/', 'attribution': UMBRA_ATTR},
            'rwy_meas': {'file': 'data/meas/rwy_ends.json', 'tool': 'tools/airport/rwy_ends.py'},
            'twy_meas': {'file': 'data/meas/twy_refit.json', 'tool': 'tools/airport/twy_refit.py'},
        },
        'src_legend': {'obs': 'seen in a source: mapped in OSM, measured by us on Sentinel-2 / Umbra, or read in the AIP '
                              '(mirror) (refs say which)',
                       'inf': 'inferred: by a stated rule, from a rounded position, or a default'},
        'frame': F.frame_block(),
        'extent': {'ring': ext_ring, 'area_km2': pin['extent']['area_km2'], 'src': 'inf',
                   'evidence': 'convex hull of OSM aerodrome relation 21913346 + 1 km (PLAN s.6b Q3 default)'},
        'aerodrome': {'id': 'osm:relation/21913346', 'rings': [[[R2(x), R2(z)] for x, z in list(p.exterior.coords)[:-1]]
                                                               for p in aero_polys],
                      'area_km2': round(aero_w.area / 1e6, 3), 'icao': 'ZSSS', 'iata': 'SHA',
                      'elev_m': {'value': F.FIELD_ELEV_Y, 'src': 'obs', 'refs': ['aip_mirror'],
                                 'note': 'AD ELEV 3.0 m (AIP mirror AD 2.2); OSM ele=3 (source=wikipedia)'},
                      'arp_aip': {'text': 'N31 11.8 E121 20.1, centre of RWY18L/36R', 'src': 'obs', 'refs': ['aip_mirror'],
                                  'note': 'printed to 0.1 min (+-90 m); the scene origin (OD0) is the OSM centre of '
                                          'RWY 18L/36R'},
                      'mag_var': {'text': '5 deg 46 min W (2017), -42 sec/yr', 'value_w_deg': round(MAG_VAR_W, 4),
                                  'src': 'obs', 'refs': ['aip_mirror']},
                      'src': 'obs', 'refs': ['osm'], 'evidence': osm_ev(aero_f)},
        'runways': runways,
        'taxiways': taxiways,
        'taxilanes': taxilanes,
        'holds': holds,
        'aprons': aprons,
        'helipads': helipads,
        'surfaces': surfaces,
        'control_tower': control_tower,
        'navaids': navaids,
        'buildings': buildings,
        'context': ctx,
        'not_yet_sourced': [
            {'what': 'stands, gates, stand lead-in lines, jet bridges, VDGS', 'known': 'task A2', 'src': 'inf'},
            {'what': 'holding-position designators and the runway-holding-position distance per taxiway',
             'known': 'OSM: 37 untagged holding_position nodes, all west of 18R/36L; AIP: pattern B holds at both ends of '
                      'TWY A; no designators', 'candidates': 'official ADC / ground movement chart (eAIP login)',
             'src': 'inf'},
            {'what': 'taxiway widths of the links (H1-H7 crossings, A1-A4 rapid exits, D and K links)',
             'known': 'AIP (mirror) AD 2.8 lists them (not transcribed, OD3); Sentinel-2 NDVI widths per measured run '
                      '(width_s2_m, incl. shoulders)', 'src': 'inf'},
            {'what': 'building heights', 'known': 'no OSM height tags at the airport; AIP obstacles give the tower '
                     'and a few buildings; the rest are HEIGHT_RULES defaults', 'candidates': 'Umbra SAR layover / '
                     'shadow (tried at the tower: inconclusive at 0.35 m because of sidelobes, docs/phase1/airport.md), '
                     'open-licence photos', 'src': 'inf'},
            {'what': 'control tower form (shaft, cab); the role of the two SW towers (west tower?)',
             'known': 'east tower position and elevation (OSM + AIP); SW towers are untyped OSM buildings', 'src': 'inf'},
            {'what': 'piers of T1 / T2 as separate volumes, terminal roof shapes',
             'known': 'OSM has one outline per terminal (T1 source=estimation)', 'src': 'inf'},
            {'what': 'markings, signs, lighting fixture positions (PALS bars, edge / centreline lights, RWSL)',
             'known': 'AIP (mirror) ALS type / length and PAPI (runways[].aip_facts); light remarks, REL taxiways and '
                      'colours are not transcribed (QA C1 M2: only values the simulator / renderer uses)',
             'candidates': 'ICAO Annex 14 / CAAC standards (Q11)', 'src': 'inf'},
            {'what': 'localizer antennas, DME, wind direction indicators, RVR / wind sensors',
             'known': 'AIP (mirror) gives WDI / sensor positions as offsets (not transcribed; WDI positions change with '
                      'AMDT 12 on 26 Nov 2026)', 'src': 'inf'},
            {'what': 'official runway threshold coordinates', 'known': 'AIP AD 2.12: "Nil"', 'src': 'inf'},
            {'what': 'runway longitudinal profile', 'known': 'profile_y is linear between the THR and DTHR elevations; '
                     'the AIP slope chain is not transcribed (QA C1 M2)', 'src': 'inf'},
        ],
        'checks_at_build': checks,
    }
    out['counts'] = {k: len(out[k]) for k in ('runways', 'taxiways', 'taxilanes', 'holds', 'aprons', 'helipads',
                                              'buildings', 'navaids')}
    out['counts']['taxiways_with_ref'] = sum(1 for t in taxiways if t['ref'])
    out['counts']['taxiways_refit'] = sum(1 for t in taxiways if t['refit'] and t['refit']['own_run_refit'])
    out['counts']['taxiways_touched_at_junctions'] = sum(1 for t in taxiways + taxilanes if t['vertices_moved'] and
                                                         not (t['refit'] and t['refit']['own_run_refit']))
    out['counts']['context'] = {k: len(v) for k, v in ctx.items()}
    out['counts']['buildings_height_src'] = {s: sum(1 for b in buildings if b['height_src'] == s) for s in ('obs', 'inf')}
    out['counts']['surface_polygons'] = {k: len(v) for k, v in surfaces.items() if isinstance(v, list) and k != 'refs'}
    # built_utc: newest input timestamp, so the output is deterministic for fixed inputs
    out['built_utc'] = pin['downloaded_utc'][1]
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    s = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    with open(OUT_JSON, 'w', encoding='utf-8') as fh:
        fh.write(s)
    with open(OUT_JS, 'w', encoding='utf-8') as fh:
        fh.write('// generated by tools/airport/build_airport.py - do not edit. Shanghai Hongqiao (ZSSS / SHA) airport data, '
                 'world frame %s (tools/common/frame.py).\n' % F.FRAME_ID)
        fh.write('// ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap contributors '
                 '(https://www.openstreetmap.org/copyright), made available under the Open Database License 1.0\n'
                 '// (https://opendatacommons.org/licenses/odbl/1-0/). Contains modified Copernicus Sentinel data 2026. '
                 + UMBRA_ATTR + '.\n// aip_facts / "AIP (mirror)": short cited facts from AIP China AD 2 ZSSS (CAAC) via an '
                 'unofficial mirror, EFF 2026-07-08; not covered by ODbL.\n')
        fh.write('window.SHA_AIRPORT = ' + s + ';\n')
    print(json.dumps(out['counts'], indent=1, ensure_ascii=False))
    print(json.dumps(checks, indent=1, ensure_ascii=False)[:6000])
    print('bytes', len(s))


if __name__ == '__main__':
    main()
