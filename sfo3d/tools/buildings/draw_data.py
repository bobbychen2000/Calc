"""Inputs of the building drawings (tools/buildings/draw.py): the verified specs, the SFO Museum footprints, the NAIP
relief (lean) models and what the 3-D app builds today. Read-only: nothing here writes js/ or data/.

Sources (all in the repo):
  tools/buildings/spec_{tower,itb,domestic,landside}.json  verified specs (tags pub / obs / inf, verification records)
  tools/buildings/itb_naip_measurements.json               ITB roof frame, eave / wing profiles, lenses (obs, NAIP 2024)
  tools/buildings/dom_heights.json                         domestic two-epoch roof faces + leans (obs; heights rescaled
                                                           to the verified |s20| = 1.25 by the spec)
  tools/buildings/landside_naip_measurements.json          landside footprints (min rectangles), DOF points, MOC corners
  data/sfo_airport.json                                    SFO Museum footprints (CDLA-Permissive-1.0)
  data/sfo_buildings.json, js/live/terminals.js, js/live/airport.js   the app today (comparison only)
"""
import json
import math
import os

import numpy as np

from draw_lib import ROOT, ring_area, unit, hdg_vec

TB = os.path.join(ROOT, 'tools', 'buildings')


def _j(*p):
    return json.load(open(os.path.join(*p)))


SPEC_T = _j(TB, 'spec_tower.json')
SPEC_I = _j(TB, 'spec_itb.json')
SPEC_D = _j(TB, 'spec_domestic.json')
SPEC_L = _j(TB, 'spec_landside.json')
ITBM = _j(TB, 'itb_naip_measurements.json')
DOMH = _j(TB, 'dom_heights.json')
LANDM = _j(TB, 'landside_naip_measurements.json')
AIR = _j(ROOT, 'data', 'sfo_airport.json')
BLD = _j(ROOT, 'data', 'sfo_buildings.json')

TV = {v['id']: v for v in SPEC_T['values']}
IV = {v['id']: v for v in SPEC_I['items']}
DV = {v['id']: v for v in SPEC_D['items']}
LV = {v['id']: v for v in SPEC_L['values']}


def verdict(rec):
    v = rec.get('verification') or {}
    return v.get('verdict', '')


# ------------------------------------------------------------------------------------------------ footprints
def sfom(name, key=None):
    """SFO Museum polygons [[outer, holes...], ...] by name from data/sfo_airport.json."""
    for k in (key,) if key else ('terminals', 'boardingAreas', 'structures'):
        for f in AIR[k]:
            if f['name'] == name:
                return f['polys']
    raise KeyError(name)


def outer_rings(name, key=None):
    return [p[0] for p in sfom(name, key)]


def min_rect(pts):
    import cv2
    p = np.asarray(pts, np.float32)
    (cx, cz), (w, h), a = cv2.minAreaRect(p)
    box = cv2.boxPoints(((cx, cz), (w, h), a))
    e = [box[1] - box[0], box[2] - box[1]]
    L = [float(np.hypot(*v)) for v in e]
    i = 0 if L[0] >= L[1] else 1
    v = e[i]
    hdg = math.degrees(math.atan2(v[0], -v[1])) % 180.0
    return dict(c=(float(cx), float(cz)), L=max(L), W=min(L), hdg=hdg, box=box)


def complex_rings():
    """all rings (outer + holes) of the SFO Museum terminal complex."""
    return [r for poly in AIR['terminalComplex'] for r in poly]


# ------------------------------------------------------------------------------------------------ relief (lean) models
# NAIP 2024 frame model fitted to the five FAA DOF high-mast poles west of the ITB (spec_itb naip.k_model alt_frame_model,
# docs/research/buildings_itb.md V.2): imaged shift = h (P - N) / (H - h), N = nadir (world x, z), H = flying height
# above grade. H - h = 3704.8 m at the pole heights (153-157 ft = 46.6-47.9 m) -> H = 3752 m.
_FM = IV['naip.k_model']['alt_frame_model']
NADIR = np.array(_FM['nadir_xz'], float)
H_FLY = _FM['H_minus_h'] + 47.3


def lean_frame(P, h):
    """predicted NAIP 2024 relief shift (world x, z, metres) of a point at height h above P (frame model)."""
    P = np.asarray(P, float)
    return h * (P - NADIR) / (H_FLY - h)


def k_x_model(x):
    """east-only k(x) model of the ITB research (spec naip.k_model): shift_x = k h."""
    m = IV['naip.k_model']['value']
    return m['a'] + m['b'] * x


# domestic per-pier 2024 lean, from the two-epoch solution (dom_heights.json band24, the verified spec heights):
# k24.n = band24 / h - s24.n with s24.n = -0.114 (buildings_domestic.md V.3), along the face normal n (heading n_hdg),
# converted to an east lean by k_east = k24.n / n_x (the along-face component is not measured: east assumed [inf]).
S24N = -0.114
DOM_PIER = {  # spec id of the height -> dom_heights roof id
    'B': ('bab.h_roof', 'ba_b_south'), 'E': ('bae.h_roof', 'ba_e_north'), 'F': ('baf.h_roof_ne_arm', 'ba_f_ne_arm'),
    'D': ('bad.h_roof', 'ba_d_head'), 'C': ('bac.h_roof', 'ba_c_east'),
}


def dom_lean(letter):
    hid, rid = DOM_PIER[letter]
    r = next(x for x in DOMH['roofs'] if x['id'] == rid)
    h = DV[hid]['value']
    if 'band24' not in r:
        return np.array([0.40, 0.0]), h, 'assumed k24.x 0.40 (spec bac.h_roof) [inf]'
    kn = r['band24'] / h + S24N
    nx = math.sin(math.radians(r.get('n_hdg', 117.8)))
    return np.array([kn / nx, 0.0]), h, f'k24.n {kn:.3f} (two-epoch, {rid}) -> east {kn / nx:.3f} [obs/inf]'


def dom_faces(rid):
    """the measured (imaged) roof faces of dom_heights.py ROOFS and the verified offsets -> lean-free roof edge lines."""
    src = open(os.path.join(TB, 'dom_heights.py')).read()
    # ROOFS is a literal list in dom_heights.py; evaluate only that assignment (no NAIP access)
    i = src.index('ROOFS = ['); j = src.index('\n]', i) + 2
    ns = {}
    exec(src[i:j], {'dict': dict}, ns)
    return {R['id']: R for R in ns['ROOFS']}.get(rid)


def offset_line(line, du):
    (x0, z0), (x1, z1) = line; L = math.hypot(x1 - x0, z1 - z0); d = ((x1 - x0) / L, (z1 - z0) / L)
    n = (-d[1], d[0])
    return [[x0 + n[0] * du, z0 + n[1] * du], [x1 + n[0] * du, z1 + n[1] * du]]


def dom_true_edges(spec_id, rid):
    rec = DV[spec_id]['value']; R = dom_faces(rid)
    if R is None: return None
    return dict(n=offset_line(R['n_face'], rec['n_offset_from_line']), m=offset_line(R['m_face'], rec['m_offset_from_line']))


# ------------------------------------------------------------------------------------------------ ITB roof frame
def itb_frame():
    c = IV['roof.corners_obs']['value']
    P = {k: np.array(v, float) for k, v in c.items()}
    centre = (P['NW'] + P['NE'] + P['SE'] + P['SW']) / 4
    ax = unit((P['SW'] + P['SE']) / 2 - (P['NW'] + P['NE']) / 2)    # towards SSE (BA-A)
    vv = np.array([ax[1], -ax[0]])                                    # towards ENE
    L = float(np.hypot(*((P['SW'] + P['SE']) / 2 - (P['NW'] + P['NE']) / 2)))
    W = float(np.hypot(*((P['NE'] + P['SE']) / 2 - (P['NW'] + P['SW']) / 2)))
    return dict(c=centre, ax=ax, v=vv, L=L, W=W, corners=P)


def itb_uv(F, u, v):
    return F['c'] + F['ax'] * u + F['v'] * v


def itb_eave_h(absu):
    """west-eave height AGL vs |u| (spec roof.profile full_curve, NAIP eave relief anchored on the DOF tops), with the
    tip value beyond the last sample; inside |u| 23 m the centre section (photo crown, see itb_crown_h)."""
    fc = IV['roof.profile']['full_curve']
    U = np.array([p['abs_u'] for p in fc]); H = np.array([p['h_agl_m'] for p in fc])
    return np.interp(absu, U, H)


L3_RANGE = (9.6, 14.8)      # level3.floor: 40.1 m minus 100 ft (sfgate2000) .. minus the 83-ft hall height (verification)


def itb_west_wall():
    """True position of the ITB west glass wall in the roof frame (v, m; west eave at -W/2), from the NAIP straight
    facade-base line (itb_naip_measurements eave_profile.base_line_v_median, imaged frame, sd 0.6 m) [obs] moved back by
    the frame-model relief of the height of that base. The base is the glass wall's foot on the elevated departures curb
    (level 3, photos i3 / i4) [inf height: level3.floor 11.5, 9.6-14.8]; v_grade = the reading if the base were at grade."""
    F = itb_frame(); rf = ITBM['roof_frame']; ep = ITBM['eave_profile']
    ci = np.array(rf['centre_imaged_xz'], float); ax = unit(rf['axis_xz']); vv = np.array([ax[1], -ax[0]])
    P = ci + vv * ep['base_line_v_median']
    v_img = float(np.dot(P - F['c'], F['v']))

    def v_at(h):
        return v_img - float(np.dot(lean_frame(P, h), F['v']))
    h = IV['level3.floor']['value']
    return dict(v=v_at(h), v_range=(v_at(L3_RANGE[1]), v_at(L3_RANGE[0])), v_grade=v_img, h_base=h, sd=ep['base_line_v_sd'])


def itb_profile_points():
    fc = IV['roof.profile']['full_curve']
    return [(p['abs_u'], p['h_agl_m']) for p in fc]


# ------------------------------------------------------------------------------------------------ the app today
def app_part(name, kind=None):
    for p in BLD['parts']:
        if p['name'] == name and (kind is None or p['kind'] == kind):
            return p
    return None


APP_STRUCT_H = {'Central Parking Garage': 22, 'Garage A': 21, 'Garage G': 21, 'Long-Term Parking Garage 1': 16,
                'Long-Term Parking Garage 2': 16, 'Rental Car Center': 26, 'Consolidated Administration Campus': 20,
                'Grand Hyatt Hotel': 38, 'Super Bay Hangar Building': 34}   # js/live/airport.js STRUCT_H_BY_NAME
APP_AIRTRAIN_H = 13.0                                                          # js/live/airport.js STRUCT_H.airtrain


def app_tower():
    """js/live/terminals.js buildTower(): shaft lathe profile (r, h above grade), cab and roof, at the vertex mean of the
    SFO Museum atc ring; cab offset +1.6 m east."""
    ring = sfom('Air Traffic Control Tower')[0][0]
    c = np.mean(np.asarray(ring, float), axis=0)
    prof = [(5.6, 14), (5.2, 20), (4.6, 28), (4.2, 36), (4.2, 44), (4.6, 50), (5.6, 54), (7.2, 57.2)]
    r0, lean, ph = 7.4, math.radians(25), 9 * 0.3048
    y0 = 58.4; y1 = y0 + ph * math.cos(lean); r1 = r0 + ph * math.sin(lean)
    cab = dict(floor=[(7.2, 57.2), (7.6, 57.6), (7.6, 58.4)], glass=[(r0, y0), (r1, y1)],
               roof=[(r1 + 0.1, y1), (r1 + 1.6, y1 + 0.35), (r1 + 1.6, y1 + 1.0), (2.5, y1 + 1.5)], mast_top=y1 + 1.4 + 7.0)
    return dict(centre=c, cab_centre=c + np.array([1.6, 0.0]), ibf_roof=14.0, profile=prof, cab=cab, ring=ring)


def app_great_hall():
    """js/live/terminals.js greatHall(): roof on the SFO Museum hall part's axis / centre (data/sfo_buildings.json)."""
    p = max((q for q in BLD['parts'] if q['kind'] == 'hall' and 'International' in q['name']), key=lambda q: q.get('area', 0))
    FTm = 0.3048
    span, cant = 380 * FTm, 160 * FTm
    roofL = span + 2 * cant + 2 * 12; roofW = 210 * FTm + 2 * 9; colS = span / 2

    def top(s):
        a = abs(s)
        t = 0.86 + 0.14 * (a / colS) ** 1.6 if a < colS else 1 - 0.2 * ((a - colS) / (roofL / 2 - colS)) ** 1.3
        return 83 * FTm * t + 1.2

    return dict(c=np.array(p['center'], float), ax=unit(p['axis']), L=roofL, W=roofW, hallL=705 * FTm, hallW=210 * FTm,
                colS=colS, top=top, part_h=p['h'])
