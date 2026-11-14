"""Jet bridges at the ZSSS contact stands on the Umbra SAR scene of 2024-06-02 (Umbra SAR Open Data, CC BY 4.0;
UMBRA-05 spotlight 01:46:48Z = 09:46 local, X-band VV, GEC 0.35 m resolution, ~0.22 m pixels). Task A2.

usage: python3 -I sha3d/tools/airport/stand_sar.py SHA3D_DIR OUT_JSON SHEET_PREFIX

Inputs: refs/cache/imagery/umbra_fullres_stands/*.tif (tools/airport/umbra_stand_windows.py), the pinned OSM extract
(stands, lead-ins, aeroway=gate nodes) and data/sha_airport.json (buildings).
Registration: Umbra minus OSM = (+3.07 m E, 0 m N), the single Phase-1 value of tools/common/umbra_reg.py (fix round
2, re-verify N4; median of 41 runway-band stations on the overview, twy_refit.py). A2's own measurement on 6
full-resolution bands (sar_registration.py: 2.9-4.1 m east of the OSM centrelines, mean 3.44 m, applied as +3.4 m before
fix round 2) agrees within a third of the overview pixel; north-south, the paved band across TWY H2 lies 4.1-5.1 m
south of the OSM line in Umbra and 1-7 m (mean 4.0 m) in Sentinel-2, i.e. the same within the S2 spread (0 m applied).
The shift is removed before sampling.
Per candidate contact stand (an OSM gate node within 50 m ahead of the stop, or the stop within 75 m of a terminal):
  - a stand-aligned crop (nose up; u = metres ahead of the stop, v = right), 0.25 m grid, 3x3 incoherent multi-look;
  - a bridge score: the brightest straight strip (2.5 m wide) from the facade side to the door zone. Rays start at the
    gate node G (or, without one, at points 12-40 m ahead of the stop on the left side) and are aimed within +-40 deg of
    the L1-door point D (u = -6 m, v = -2.5 m: left side, ~6 m behind the nose); the score is the median log-amplitude
    along t = 3 m .. 0.8 |GD| minus the 30th percentile of the crop (the dark apron level), in log units.
The bridge decision itself is a visual reading of the crop (tools/airport/bridge_table.py), with the score as support.
Outputs: OUT_JSON (per stand: gate, score, best ray) and contact sheets SHEET_PREFIX_<group>.jpg.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
import umbra_reg as UR  # noqa: E402
from sarwin import SarWindows  # noqa: E402
from stand_geom import OsmStands, from_local, hdiff, to_local, stand_sort_key  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

SHIFT = UR.UMBRA_MINUS_OSM_EN   # the single Phase-1 Umbra registration (tools/common/umbra_reg.py; was +3.4 E before fix round 2)
RES = 0.25
UA, UB = 55.0, -45.0       # crop: u from +55 (ahead) to -45
VW = 45.0                  # v in [-45, 45]
DOOR = (-6.0, -2.5)
DOOR2 = (-21.0, -3.0)          # L2 door zone of a wide-body (~0.32 L of an A330 / 787)
GATE_MEDIAN_UV = (16.7, -21.8)  # median OSM gate offset from the stop at the 2nn stands (measured, see the report)
TERM_H = 25.0                 # terminal height for the layover / shadow zones [inf: HEIGHT_RULES 'terminal' of build_airport]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
GROUPS = [   # contact sheets by pier face (stand name ranges)
    ('t1_north', lambda n: n in ('101', '102', '109', '110', '111', '112')),
    ('t1_west', lambda n: n.startswith('1') and n not in ('101', '102', '109', '110', '111', '112')),
    ('t2_north', lambda n: n.startswith('2') and 218 <= int(n[:3]) <= 231),
    ('t2_middle_n', lambda n: n.startswith('2') and 232 <= int(n[:3]) <= 240),
    ('t2_west', lambda n: n.startswith('2') and 241 <= int(n[:3]) <= 256),
    ('t2_middle_s', lambda n: n.startswith('2') and 257 <= int(n[:3]) <= 266),
    ('t2_south', lambda n: n.startswith('2') and 267 <= int(n[:3]) <= 285),
]


def face_of(n):
    for name, fn in GROUPS:
        try:
            if fn(n):
                return name
        except ValueError:
            pass
    return None


def main(root, out_json, sheet_prefix):
    global SENSOR_AZ, INC
    md = json.load(open(os.path.join(root, 'refs/cache/imagery/umbra_opendata/shanghai_chn_2024-06-02_METADATA.json')))
    SENSOR_AZ = round(md['collects'][0]['angleAzimuthDegrees'], 2); INC = round(md['collects'][0]['angleIncidenceDegrees'], 2)
    O = OsmStands(root)
    A = json.load(open(os.path.join(root, 'data/sha_airport.json')))
    term = [g for f, g in O.terminal_polys() if f['properties']['tags'].get('name:en') in ('Terminal 1', 'Terminal 2')]
    stands = O.stands()
    gates = O.gate_points()
    S = SarWindows(root, SHIFT)
    cand = []
    for s in stands:
        n = s['name']
        g_best = None
        for g in gates:
            u, v = to_local(g['xz'], s['stop'], s['hdg'])
            d = math.hypot(u, v)
            if u > 0 and d < 50 and (g_best is None or d < g_best[0]):
                g_best = (d, u, v, g)
        # T2 rule: stand 2nn <-> gate nn (checked: see the report)
        if n.startswith('2') and len(n) >= 3:
            for g in gates:
                if g['ref'] == str(int(n[1:3])):
                    u, v = to_local(g['xz'], s['stop'], s['hdg'])
                    if u > -5 and math.hypot(u, v) < 60:
                        g_best = (math.hypot(u, v), u, v, g)
        dterm = min(t.boundary.distance(Point(s['stop'])) for t in term)
        if g_best is None and dterm > 75:
            # null sample: a remote stand far from any terminal, scored the same way (no gate node) for the threshold
            if dterm > 150:
                cand.append((s, None, dterm))
            continue
        cand.append((s, g_best, dterm))
    res = {}
    crops = {}

    def scores(L, base, gu, gv):
        """corridor test (left/right symmetry): the strip from the gate node G = (gu, gv) to the L1-door zone D
        (t = 3 m .. 0.7 |GD|, 3 m wide) against its mirror image across the stand axis (v -> -v). A parked aircraft is
        symmetric about the axis and cancels; a bridge on the left side does not."""
        def corridor(du_, dv_, sign, f0=None, f1=0.7):
            dist = math.hypot(du_ - gu, dv_ - gv); b = math.atan2(dv_ - gv, du_ - gu)
            ts = np.arange(3.0 if f0 is None else f0 * dist, max(6.0, f1 * dist), 0.25)
            vals = []
            for off in np.arange(-1.5, 1.51, 0.25):
                uu = gu + ts * math.cos(b) - off * math.sin(b); vv = sign * (gv + ts * math.sin(b) + off * math.cos(b))
                ri = np.clip(((UA - uu) / RES).astype(int), 0, L.shape[0] - 1)
                ci = np.clip(((vv + VW) / RES).astype(int), 0, L.shape[1] - 1)
                vals.append(L[ri, ci])
            return np.array(vals)

        def near(sign):     # near part (t = 3 .. 12 m from G): a retracted bridge
            dist = math.hypot(DOOR[0] - gu, DOOR[1] - gv); b = math.atan2(DOOR[1] - gv, DOOR[0] - gu)
            ts = np.arange(3.0, max(min(12.0, dist), 3.5), 0.25); vals = []
            for off in np.arange(-1.5, 1.51, 0.25):
                uu = gu + ts * math.cos(b) - off * math.sin(b); vv = sign * (gv + ts * math.sin(b) + off * math.cos(b))
                ri = np.clip(((UA - uu) / RES).astype(int), 0, L.shape[0] - 1)
                ci = np.clip(((vv + VW) / RES).astype(int), 0, L.shape[1] - 1)
                vals.append(L[ri, ci])
            return np.array(vals)
        c1 = corridor(*DOOR, 1); m1 = corridor(*DOOR, -1)
        c2 = corridor(*DOOR2, 1, 0.5, 0.85); m2 = corridor(*DOOR2, -1, 0.5, 0.85)   # far half only (diverges from L1)
        return (float(np.median(c1) - np.median(m1)), float(np.median(c2) - np.median(m2)),
                float(np.median(c1) - base), float(np.median(m1) - base),
                float(np.median(near(1)) - np.median(near(-1))))

    def crop(stop, hdg):
        img, U_, V_ = S.patch(stop[0], stop[1], hdg, UA - UB, 2 * VW, RES, back=-UB)
        if np.isnan(img).mean() > 0.2:
            return None, None
        img = np.sqrt(uniform_filter(np.nan_to_num(img) ** 2, 3))
        L = np.log1p(img)
        return L, float(np.percentile(L, 30))
    term_u = unary_union(term)
    for s, g, dterm in cand:
        n = s['name']
        if np.isnan(S.sample_xz(np.array([s['stop'][0]]), np.array([s['stop'][1]])))[0]:
            continue
        L, base = crop(s['stop'], s['hdg'])
        if L is None:
            continue
        gu, gv = (g[1], g[2]) if g is not None else GATE_MEDIAN_UV
        best = scores(L, base, gu, gv)
        rec = {'null_sample': dterm > 150 and g is None, 'gate': ({'ref': g[3]['ref'], 'node': g[3]['node'],
                                                                   'u': round(g[1], 1), 'v': round(g[2], 1),
                                                                   'dist_m': round(g[0], 1)} if g else None),
               'terminal_dist_m': round(dterm, 1), 'bridge_score': round(best[0], 3),
               'bridge2_score': round(best[1], 3), 'near_score': round(best[4], 3),
               'corridor_above_dark': round(best[2], 3), 'mirror_above_dark': round(best[3], 3),
               'g_uv': [round(gu, 1), round(gv, 1)], 'dark_level': round(base, 3), 'face': face_of(n)}
        # close to a terminal with no gate node on the L1 (left) side (corner stands such as 112): also score the
        # corridor from the facade point nearest to the L1-door zone (QA C1 M3; neither the median gate offset nor a
        # gate straight ahead fits a corner stand)
        if dterm < 75 and (g is None or g[2] > -5):
            dpt = from_local(DOOR[0], DOOR[1], s['stop'], s['hdg'])
            fp = term_u.boundary.interpolate(term_u.boundary.project(Point(dpt)))
            fu, fv = to_local((fp.x, fp.y), s['stop'], s['hdg'])
            if math.hypot(fu - DOOR[0], fv - DOOR[1]) <= 60 and fv < 0 and fu < UA - 3:
                fb = scores(L, base, fu, fv)
                rec['facade_point_uv'] = [round(fu, 1), round(fv, 1)]
                rec['facade_score'] = round(fb[0], 3)
                rec['facade_near_score'] = round(fb[4], 3)
        res[n] = rec
        crops[n] = (L, base, g, best)
        print(n, res[n]['gate'] and res[n]['gate']['ref'], res[n]['bridge_score'], flush=True)
    # ------------------------------------------------------------------ terminal-adjacent null (QA C1 M3)
    # pseudo-stands along the terminal facades where there is no bridge: facade points every 4 m whose outward normal
    # is within 30 deg of the face's facade normal, > 25 m from every OSM gate node; the pseudo gate G sits off the
    # facade by the face's median gate-to-facade distance and the pseudo stop at the median gate offset from it; kept
    # when the pseudo stop is > 25 m from every real stop, outside buildings, and its corridor strip and mirror strip are
    # > 8 m from every real gate-to-door corridor. Scored exactly like the candidates.
    gpts = [Point(*gg['xz']) for gg in gates]
    real_corr = []
    for s_, g_, dterm_ in cand:
        if g_ is not None:
            real_corr.append(LineString([g_[3]['xz'], from_local(DOOR[0], DOOR[1], s_['stop'], s_['hdg'])]))
    real_corr_u = unary_union(real_corr).buffer(8.0) if real_corr else None
    stops = [Point(*s_['stop']) for s_ in stands]
    bld = unary_union([Polygon(b['ring']).buffer(0) for b in A['buildings'] if len(b['ring']) >= 3])
    faces = {}
    for fname, fn in GROUPS:
        fs = [s_ for s_, g_, d_ in cand if fn(s_['name']) and g_ is not None]
        if not fs:
            continue
        hd = float(np.degrees(np.arctan2(np.median([math.sin(math.radians(x['hdg'])) for x in fs]),
                                         np.median([math.cos(math.radians(x['hdg'])) for x in fs]))) % 360)
        normal = (hd + 180) % 360           # outward facade normal (towards the apron)
        gdist = float(np.median([term_u.boundary.distance(Point(*g_[3]['xz'])) for s_, g_, d_ in cand
                                 if fn(s_['name']) and g_ is not None]))
        lay = TERM_H / math.tan(math.radians(INC)); shd = TERM_H * math.tan(math.radians(INC))
        faces[fname] = {'stand_heading_deg': round(hd, 1), 'facade_normal_deg': round(normal, 1),
                        'gate_to_facade_median_m': round(gdist, 1), 'assumed_terminal_height_m': TERM_H,
                        'layover_depth_m': round(max(0.0, lay * math.cos(math.radians(normal - SENSOR_AZ))), 1),
                        'shadow_depth_m': round(max(0.0, shd * math.cos(math.radians(normal - (SENSOR_AZ + 180)))), 1),
                        'null_scores': []}
    bnd = term_u.boundary
    segs = []
    for geom in (bnd.geoms if hasattr(bnd, 'geoms') else [bnd]):
        cs = list(geom.coords)
        for a_, b_ in zip(cs[:-1], cs[1:]):
            segs.append((a_, b_))
    for (a_, b_) in segs:
        Ls = math.dist(a_, b_)
        if Ls < 4:
            continue
        tx, tz = (b_[0] - a_[0]) / Ls, (b_[1] - a_[1]) / Ls
        for t_ in np.arange(2.0, Ls - 2.0, 4.0):
            fx, fz = a_[0] + t_ * tx, a_[1] + t_ * tz
            for nx, nz in ((-tz, tx), (tz, -tx)):
                if term_u.contains(Point(fx + 2 * nx, fz + 2 * nz)):
                    continue                          # inward side
                nb = F.vec_hdg(nx, nz)
                for fname, fc_ in faces.items():
                    if abs(hdiff(nb, fc_['facade_normal_deg'])) > 30:
                        continue
                    G = (fx + nx * fc_['gate_to_facade_median_m'], fz + nz * fc_['gate_to_facade_median_m'])
                    if min(Point(G).distance(q) for q in gpts) < 25:
                        continue
                    hd = fc_['stand_heading_deg']
                    stop = from_local(-GATE_MEDIAN_UV[0], -GATE_MEDIAN_UV[1], G, hd)
                    ps = Point(*stop)
                    if min(ps.distance(q) for q in stops) < 25 or bld.contains(ps) or term_u.distance(ps) < 20:
                        continue
                    door = from_local(DOOR[0], DOOR[1], stop, hd)
                    mdoor = from_local(DOOR[0], -DOOR[1], stop, hd); mG = from_local(GATE_MEDIAN_UV[0], -GATE_MEDIAN_UV[1], stop, hd)
                    if real_corr_u is not None and (real_corr_u.intersects(LineString([G, door])) or
                                                    real_corr_u.intersects(LineString([mG, mdoor]))):
                        continue
                    if np.isnan(S.sample_xz(np.array([stop[0]]), np.array([stop[1]])))[0]:
                        continue
                    L, base = crop(stop, hd)
                    if L is None:
                        continue
                    sc_ = scores(L, base, *GATE_MEDIAN_UV)
                    fc_['null_scores'].append([round(sc_[0], 3), round(sc_[1], 3), round(sc_[4], 3)])
    tn = [x for fc_ in faces.values() for x in fc_['null_scores']]
    # contact sheets
    font = ImageFont.truetype(FONT, 15); fsm = ImageFont.truetype(FONT, 12)
    sheets = {}
    nulls_r = [r['bridge_score'] for r in res.values() if r['null_sample']]
    nulls2_r = [r['bridge2_score'] for r in res.values() if r['null_sample']]
    nullsn_r = [r['near_score'] for r in res.values() if r['null_sample']]
    cands = [r['bridge_score'] for r in res.values() if not r['null_sample']]
    use_term = len(tn) >= 20
    nulls = [x[0] for x in tn] if use_term else nulls_r
    nulls2 = [x[1] for x in tn] if use_term else nulls2_r
    nullsn = [x[2] for x in tn] if use_term else nullsn_r
    thr = float(np.percentile(nulls, 95)) if nulls else None
    print('terminal null n %d median %.2f p95 %.2f | remote null n %d p95 %.2f | candidates n %d median %.2f' % (
        len(tn), np.median([x[0] for x in tn]) if tn else float('nan'),
        np.percentile([x[0] for x in tn], 95) if tn else float('nan'), len(nulls_r), np.percentile(nulls_r, 95),
        len(cands), np.median(cands)))
    for gname, fn in GROUPS:
        ns = sorted([n for n in crops if fn(n) and not res[n]['null_sample']], key=stand_sort_key)
        if not ns:
            continue
        tiles = []
        for n in ns:
            L, base, g, best = crops[n]
            v = np.clip((L - base) / 3.2, 0, 1) * 255
            t = Image.fromarray(v.astype(np.uint8)).convert('RGB').resize((int(v.shape[1] * 0.8), int(v.shape[0] * 0.8)))
            dr = ImageDraw.Draw(t); k = 0.8 / RES
            P = lambda u, vv: ((vv + VW) * k, (UA - u) * k)  # noqa: E731
            # stand axis and nose
            dr.line([P(0, 0), P(-40, 0)], fill=(60, 140, 255), width=1)
            dr.ellipse([P(0, 0)[0] - 4, P(0, 0)[1] - 4, P(0, 0)[0] + 4, P(0, 0)[1] + 4], outline=(255, 60, 60), width=2)
            dx, dz = P(*DOOR)
            dr.rectangle([dx - 3, dz - 3, dx + 3, dz + 3], outline=(255, 210, 0), width=1)
            if g is not None:
                gx, gz = P(g[1], g[2]); dr.rectangle([gx - 4, gz - 4, gx + 4, gz + 4], outline=(255, 0, 255), width=2)
                dr.text((gx + 6, gz - 8), 'gate ' + str(g[3]['ref']), fill=(255, 0, 255), font=fsm)
            dr.text((6, 4), '%s  score %.2f' % (n, res[n]['bridge_score']), fill=(255, 255, 0), font=font)
            tiles.append(t)
        w, h = tiles[0].size; cols = min(6, len(tiles)); rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * (w + 6) + 6, rows * (h + 6) + 46), (25, 25, 25))
        for i, t in enumerate(tiles):
            sheet.paste(t, (6 + (i % cols) * (w + 6), 40 + (i // cols) * (h + 6)))
        dr = ImageDraw.Draw(sheet)
        dr.text((8, 8), 'ZSSS %s - Umbra SAR 2024-06-02 09:46 local, stand-aligned (nose up), 100 x 90 m, shift-corrected; '
                'red = OSM stop, yellow = L1 door zone, magenta = OSM gate node.  Umbra SAR Open Data (CC BY 4.0); '
                'OSM (ODbL)' % gname, fill=(230, 230, 230), font=fsm)
        p = '%s_%s.jpg' % (sheet_prefix, gname)
        sheet.save(p, quality=85); sheets[gname] = os.path.basename(p)
    meta = {'what': 'jet bridge evidence per candidate contact stand on the Umbra SAR scene (tools/airport/stand_sar.py)',
            'attribution': ('Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), '
                            'modified; (c) OpenStreetMap contributors (ODbL)'),
            'licence': ('Umbra: CC BY 4.0; measurements on OSM stands: ODbL 1.0 '
                        '(https://opendatacommons.org/licenses/odbl/1-0/)'),
            'registration': UR.UMBRA_REG_NOTE,
            'scene': '2024-06-02T01:46:48Z UMBRA-05 spotlight GEC (task ad hoc/Shanghai_CHN)',
            'shift_umbra_minus_osm_m': SHIFT, 'door_zone_uv': DOOR, 'sheets': sheets,
            'null': {'what': ('the same score on terminal-adjacent pseudo-stands without a bridge (facade points '
                              'between gates, same face orientation; QA C1 M3)' if use_term else
                              'the same score on remote stands > 150 m from a terminal (terminal null too small)'),
                     'source': 'terminal' if use_term else 'remote',
                     'n': len(nulls), 'median': round(float(np.median(nulls)), 3) if nulls else None,
                     'p95': round(thr, 3) if thr else None, 'max': round(max(nulls), 3) if nulls else None,
                     'bridge2_p95': round(float(np.percentile(nulls2, 95)), 3) if nulls2 else None,
                     'near_p95': round(float(np.percentile(nullsn, 95)), 3) if nullsn else None,
                     'per_face_n': {k: len(v['null_scores']) for k, v in faces.items()}},
            'null_remote': {'what': 'the former null: remote stands > 150 m from a terminal (kept for comparison; it '
                                    'has none of the facade layover / shadow of the contact stands)',
                            'n': len(nulls_r), 'median': round(float(np.median(nulls_r)), 3),
                            'p95': round(float(np.percentile(nulls_r, 95)), 3),
                            'bridge2_p95': round(float(np.percentile(nulls2_r, 95)), 3),
                            'near_p95': round(float(np.percentile(nullsn_r, 95)), 3)},
            'scene_geometry': {'sensor_azimuth_deg': SENSOR_AZ, 'incidence_deg': INC,
                               'source': 'refs/cache/imagery/umbra_opendata/shanghai_chn_2024-06-02_METADATA.json',
                               'layover_m_per_m_height': round(1 / math.tan(math.radians(INC)), 4),
                               'shadow_m_per_m_height': round(math.tan(math.radians(INC)), 4)},
            'faces': {k: {kk: vv for kk, vv in v.items() if kk != 'null_scores'} for k, v in faces.items()},
            'stands': res}
    json.dump(meta, open(out_json, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
