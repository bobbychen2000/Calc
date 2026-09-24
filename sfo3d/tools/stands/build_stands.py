"""Rebuild the SFO stand + jet-bridge set from licence-clean, verifiable sources -> data/sfo_stands.json / .js.

Sources and their roles (details and licences: docs/research/stands_rebuild.md, docs/ATTRIBUTION.md):
  positions / headings   OSM aeroway=parking_position lead-ins (ODbL 1.0), oriented (osm_src.py): stop = last node,
                         heading = last segment. The nose tip of the stand's reference aircraft is put a class-group
                         offset ahead of the OSM stop node, calibrated on NAIP 2024 parked aircraft (median of the
                         readings in stand_table.NAIP_OBS). Exceptions with a NAIP position: stand_table.NAIP_POS.
  names                  SFO's AODB stand names (flysfo feed) and official gate numbers (DataSF chfu-j7tc, PDDL);
                         OSM refs only as the link between the two (stand_table.OVERRIDES lists every exception).
  jet bridges            OSM aeroway=jet_bridge ways (ODbL): building attach point, fixed walkway, rotunda (start
                         of the last segment = parked tunnel), parked cab; assigned by ref / name, else geometrically.
  classes                the largest aircraft type SFO allocates to the stand (flysfo AODB stands[] types, all cached
                         snapshots) + types seen parked there in ADS-B; dimensions from the manufacturers' airport
                         planning documents (tools/models/check_dims.py REF).
  verification           NAIP 2024 (USDA, public domain) readings of parked aircraft (stand_table.NAIP_OBS) and ADS-B
                         parked stays with SFO stand windows (adsb_parked.py): residuals per stand.
  mutual exclusion       stands whose reference aircraft would overlap / come within the physical minimum (3 m) of
                         each other are mutually exclusive ('excl'); pairs SFO plans simultaneously are reported.
Google screenshots are NOT used for anything here.

Outputs: data/sfo_stands.json + .js (committed, ODbL: contains OSM-derived positions), refs/cache/stands/
stands_built.json (full provenance incl. residual tables, gitignored) and a summary on stdout.
Usage: python3 tools/stands/build_stands.py
"""
import json, math, os, re, sys
from collections import Counter, defaultdict
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from common import GF, ROOT, WORK, CACHE, hdg_vec, vec_hdg, hdiff, load_osm, Buildings, building_rings
from osm_src import lead_ins, jet_bridges
import stand_table as TB
sys.path.insert(0, os.path.join(ROOT, 'tools', 'imagery'))
from paintline import Yellow  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, 'tools', 'live')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'models'))
import gatecheck as G  # noqa: E402  (read-only use of the flysfo readers)
from check_dims import REF as ACAP_REF  # noqa: E402
import geom as GM  # noqa: E402
# Aircraft dimensions (review round 2): the app's own geometry (js/aircraft/types.js via geom.APP; its SPEC values are
# the manufacturers' airport-planning numbers, checked by tools/models/check_dims.py), so that classes, limits,
# envelopes and door positions are those the app renders. ACAP_REF only fills designators the app lacks.
REF = {t: {'L': r['L'], 'span': r['span'], 'doors': {i + 1: d for i, d in enumerate(r['doors'])}} for t, r in GM.APP.items() if r['span']}
for t, r in ACAP_REF.items(): REF.setdefault(t, r)

# ------------------------------------------------------------------ aircraft classes (js/live/airport.js CLASS_MAX)
CLASS_MAX = {'B': (28.5, 37), 'C': (36.5, 45), 'CL': (38.5, 48), 'D': (52, 62), 'E': (61, 68), 'EL': (65.5, 77), 'F': (80, 80)}
ORDER = ['B', 'C', 'CL', 'D', 'E', 'EL', 'F']
# reference planform per class = the largest type of the class that SFO parks (REF dims: ACAP documents)
CLS_REF = {'B': 'E75L', 'C': 'A321', 'CL': 'B752', 'D': 'B763', 'E': 'B772', 'EL': 'B77W', 'F': 'A388'}
ALIAS_T = {'E175': 'E75L', 'B787': 'B789', 'B76W': 'B763', 'E295': 'E195'}   # ICAO designators without their own REF
# (B76W: the 767-300ER winglet span, about 51 m, is not in REF; it stays inside class D's 52 m bound either way.
#  E295: E195-E2 dims not in REF; SFO parks it only at B2 next to B738/B39M, which set that stand's class anyway.)
WIDE = {'D', 'E', 'EL', 'F'}
# ICAO clearances between aircraft on stands (ICAO Doc 9157 Part 2, 4th ed. 2005, §3.4.4 = Annex 14 Vol I 3.13.6;
# read from refs/cache/icao/sky3090.pdf p. 3-10): code letter A, B 3.0 m; C 4.5 m; D, E, F 7.5 m (code letter by span:
# C 24-36 m, D 36-52 m, E 52-65 m, F 65-80 m). D-F may be reduced near the terminal/nose and where azimuth guidance
# (VDGS) is provided.
def icao_clear(span): return 3.0 if span < 24 else 4.5 if span < 36 else 7.5
PHYS = 3.0   # below this aircraft-to-aircraft distance two stands are treated as not usable at the same time


def type_cls(t):
    t = ALIAS_T.get(t, t); r = REF.get(t)
    if not r: return None
    for c in ORDER:
        sp, L = CLASS_MAX[c]
        if r['span'] <= sp + 0.6 and r['L'] <= L + 2: return c
    return 'F'


def planform(nose, hdg, cls, t=None):
    """collision planform of type t (else the class reference type) as the app draws it (geom.planform)"""
    return GM.planform(nose, hdg, ALIAS_T.get(t, t) if t else CLS_REF[cls])


def paint_fit(Y, nose, hdg, a0=3.0, a1=22.0, step=1.5):
    """Painted lead-in line behind the nose on NAIP 2024: yellow ridge (+-4 m, averaged over 3 m along) every 1.5 m
    from a0 to a1 m behind the nose; robust straight fit lat = c0 + c1 * along (along negative behind the nose).
    Returns {n, lat_nose (m, + = right of the stand axis), lat_m20, dh (deg, + = clockwise), rms} or None."""
    f = hdg_vec(hdg); pts = []
    for a in np.arange(-a0, -a1 - 1e-9, -step):
        p = (nose[0] + f[0] * a, nose[1] + f[1] * a)
        r = Y.cross_peak(p, f, half=4.0, avg=3.0, step=0.1, min_contrast=10.0)
        if r and r[2] < 0.7 * r[1]: pts.append((float(a), r[0]))
    if len(pts) < 5: return None
    P = np.array(pts)
    for _ in range(3):
        A = np.stack([np.ones(len(P)), P[:, 0]], 1); c = np.linalg.lstsq(A, P[:, 1], rcond=None)[0]
        r = P[:, 1] - A @ c; keep = np.abs(r) < max(0.4, 2.5 * np.median(np.abs(r)))
        if keep.all() or keep.sum() < 5: break
        P = P[keep]
    rms = float(np.sqrt(np.mean(r[keep] ** 2))) if keep.sum() else 9.0
    return {'n': int(len(P)), 'lat_nose': round(float(c[0]), 2), 'lat_m20': round(float(c[0] - 20 * c[1]), 2),
            'dh': round(math.degrees(math.atan(c[1])), 2), 'rms': round(rms, 2)}


def gkey(n):
    m = re.match(r'^([A-Z]*)(\d*)(.*)$', n); return (m.group(1) or 'ZZ', int(m.group(2) or 0), m.group(3))


def local(p, stop, hdg):
    """(along, right) of point p in the frame of a line through `stop` with heading hdg"""
    f = hdg_vec(hdg); rt = (math.cos(math.radians(hdg)), math.sin(math.radians(hdg)))
    d = (p[0] - stop[0], p[1] - stop[1]); return d[0] * f[0] + d[1] * f[1], d[0] * rt[0] + d[1] * rt[1]


def main():
    osm = load_osm(); B = Buildings()
    LI = lead_ins(osm, B); LB = {r['osm_id']: r for r in LI}
    JB = jet_bridges(osm, B)
    # ---------------------------------------------------------------- SFO names and types
    info, lu, recs = G.load_flysfo_all()
    aodb_types = defaultdict(Counter); aodb_turns = defaultdict(set); ivs = defaultdict(list)
    for r in recs:
        t = (r.get('aircraft_transport_type') or {}).get('icao_code'); turn = tuple(sorted([r['flight_id'], r.get('linked_flight_id') or '']))
        for s in r.get('stands') or []:
            n = s['stand']['stand_name']
            if turn not in aodb_turns[n]: aodb_types[n][t] += 1
            aodb_turns[n].add(turn)
            a, b = G.iso(s['start_time']), G.iso(s['end_time'])
            if a and b: ivs[n].append((a, b, turn, t))
    datasf = {g['gate'] for g in json.load(open(os.path.join(CACHE, 'gate_truth', 'datasf_gates_2026.json')))}
    contact_aodb = sorted([n for n in aodb_types if re.match(r'^[A-G]\d{1,2}[A-Z]?$', n)], key=gkey)
    names = set(contact_aodb) | {g for g in datasf if not any(G.stand_base(a) == g for a in contact_aodb)}
    names -= set(TB.DROPPED)
    # ---------------------------------------------------------------- positions
    # NAIP readings corrected for relief displacement (review round 2; tools/stands/naip_relief.py: the imaged aircraft
    # lean east by k * h, k fitted on the parked aircraft themselves). RD[way] = (along_corr, lat_corr or None, group,
    # flags); lat_corr is None where the fuselage centre could not be measured numerically (the by-eye lateral readings
    # are not used any more: they missed the lean).
    RELIEF = json.load(open(os.path.join(WORK, 'naip_relief.json')))
    kR = RELIEF['k']; RD = {}
    import naip_relief as NR
    LB_ = {r['osm_id']: r for r in LI}
    for wid, (al, lat, grp, fl) in TB.NAIP_OBS.items():
        if wid not in LB_ or LB_[wid]['hdg'] is None: continue
        h_ = LB_[wid]['hdg']; m_ = RELIEF['stands'].get(str(wid))
        RD[wid] = (round(al - kR * NR.H_NOSE[grp] * math.sin(math.radians(h_)), 2), m_['lat_corr'] if m_ else None, grp, fl)
    naip_off = {}
    for grp in ('narrow', 'wide'):
        v = [a for a, lat, g, fl in RD.values() if g == grp and 'u' not in fl and (abs(lat) < 3 if lat is not None else True)]
        naip_off[grp] = round(float(np.median(v)), 1)
    stays = json.load(open(os.path.join(WORK, 'adsb_parked.json')))
    by_ref = defaultdict(list)
    for r in LI:
        if r['ref']: by_ref[r['ref']].append(r)
    stands = []; problems = []
    for n in sorted(names, key=gkey):
        base = G.stand_base(n); ov = TB.OVERRIDES.get(n)
        if ov: ways = [LB[i] for i in ov['osm']]
        else:
            ways = [w for w in by_ref.get(n, []) + by_ref.get(base, []) if w['hdg'] is not None]
            ways = list({w['osm_id']: w for w in ways}.values())
            if len(ways) != 1: problems.append((n, 'OSM ways with this ref: %d' % len(ways))); continue
        w = ways[0]
        aodb = [n] if n in contact_aodb else sorted(a for a in contact_aodb if G.stand_base(a) == n and a not in names)
        types = Counter()
        for a in aodb or [n]: types.update(aodb_types.get(a, {}))
        stands.append({'name': n, 'gate': base, 'aodb': aodb, 'osm_way': w, 'why': ov['why'] if ov else 'OSM ref = SFO name',
                       'alias': (ov or {}).get('alias', []), 'types': types})
    # suffix alternates share the base gate: 'alt_of'
    have = {s['name'] for s in stands}
    for s in stands:
        if s['name'] != s['gate'] and s['gate'] in have: s['alt_of'] = s['gate']
    # ---------------------------------------------------------------- per stand geometry, class, evidence
    stays_by = defaultdict(list)
    for st in stays['stays']:
        if st.get('stand'): stays_by[st['stand']].append(st)
    YEL = Yellow(index='mean')
    for s in stands:
        w = s['osm_way']; stop, h_osm = w['stop'], w['hdg']
        unknown = sorted(t for t in s['types'] if t and not type_cls(t))
        sfo_types = [t for t in s['types'] if t and type_cls(t)]
        ev = [st for a in s['aodb'] or [s['name']] for st in stays_by.get(a, [])]
        adsb_types = []
        for it in range(2):
            # class: SFO AODB types, plus (second pass) the types of ADS-B stays that were accepted on this stand's
            # line AND agree with the type SFO planned for that flight (review round 1: C11 and D14 had been raised by
            # stays hundreds of metres away / by a registration flying another flight number)
            tall = sfo_types + adsb_types
            tcls = [type_cls(t) for t in tall]
            cls = max(tcls, key=ORDER.index) if tcls else ('C' if s['gate'][0] in 'BCDEF' else 'E')
            s['cls_src'] = ('sfo types' + (' + adsb types' if adsb_types else '')) if tcls else 'default (no type seen)'
            s['cls'] = cls; s['grp'] = 'wide' if cls in WIDE else 'narrow'
            s['largest_type'] = max(tall, key=lambda t: (ORDER.index(type_cls(t)), REF[ALIAS_T.get(t, t)]['span']), default=None)
            h = h_osm
            f = hdg_vec(h); rt = (math.cos(math.radians(h)), math.sin(math.radians(h)))
            np_ = TB.NAIP_POS.get(s['name'])
            if np_:
                rr_ = RD[w['osm_id']]; al_, la_ = rr_[0], rr_[1] if rr_[1] is not None else np_['lat']
                nose = (stop[0] + f[0] * al_ + rt[0] * la_, stop[1] + f[1] * al_ + rt[1] * la_)
                s['pos_src'] = 'naip'; s['nose_rule'] = 'NAIP parked aircraft, relief-corrected (stand_table.NAIP_POS, naip_relief.py): %+.1f m along, %+.2f m lateral of the OSM stub' % (al_, la_)
            else:
                off = naip_off[s['grp']]
                nose = (stop[0] + f[0] * off, stop[1] + f[1] * off)
                s['pos_src'] = 'osm'; s['nose_rule'] = 'OSM stop + %.1f m (%s-body NAIP calibration)' % (off, s['grp'])
            # painted lead-in line on NAIP (tools/imagery/paintline.py): lateral offset and heading of the paint over
            # the last 3-22 m behind the nose. Applied when the fit is clean (>= 8 samples, rms <= 0.3 m) and
            # disagrees by > 0.8 m or > 1.5 deg (review round 1: D14 3.1 m, C4 1.7 m / 2.5 deg).
            pf = paint_fit(YEL, nose, h)
            s['paint'] = pf
            rd0 = RD.get(w['osm_id'])
            def naip_lat(nz, hh):
                if not rd0 or 'u' in rd0[3] or rd0[1] is None: return None
                fo = hdg_vec(h_osm); ro = (math.cos(math.radians(h_osm)), math.sin(math.radians(h_osm)))
                p_ = (stop[0] + fo[0] * rd0[0] + ro[0] * rd0[1], stop[1] + fo[1] * rd0[0] + ro[1] * rd0[1])
                return abs(local(p_, nz, hh)[1])
            ok_naip = True
            if pf and rd0:
                h2 = (h + pf['dh']) % 360; n2 = (nose[0] + rt[0] * pf['lat_nose'], nose[1] + rt[1] * pf['lat_nose'])
                b0, b1 = naip_lat(nose, h), naip_lat(n2, h2)
                ok_naip = b0 is None or b1 is None or b1 <= b0 + 0.5          # never move a line away from the parked NAIP aircraft
            if pf and ok_naip and pf['n'] >= 8 and pf['rms'] <= 0.3 and (abs(pf['lat_nose']) > 0.8 or abs(pf['dh']) > 1.5) \
                    and abs(pf['lat_nose']) < 4.5 and abs(pf['dh']) < 8 and not np_:
                h = (h + pf['dh']) % 360
                nose = (nose[0] + rt[0] * pf['lat_nose'], nose[1] + rt[1] * pf['lat_nose'])
                f = hdg_vec(h); rt = (math.cos(math.radians(h)), math.sin(math.radians(h)))
                s['pos_src'] = 'osm+paint'; pf['applied'] = True
                s['nose_rule'] += '; moved onto the painted lead-in (NAIP): %+.2f m lateral, %+.2f deg' % (pf['lat_nose'], pf['dh'])
                s['paint_after'] = paint_fit(YEL, nose, h)
            s['nose'] = nose; s['hdg'] = h
            # NAIP residual of the parked aircraft (reading - model nose), in the stand frame
            vb = []
            rd = RD.get(w['osm_id'])
            s.pop('naip', None)
            if rd:
                fo = hdg_vec(h_osm); ro = (math.cos(math.radians(h_osm)), math.sin(math.radians(h_osm)))
                lat_ = rd[1] if rd[1] is not None else 0.0
                p = (stop[0] + fo[0] * rd[0] + ro[0] * lat_, stop[1] + fo[1] * rd[0] + ro[1] * lat_)
                a, c = local(p, nose, h)
                s['naip'] = {'nose_along': rd[0], 'lat': rd[1], 'group_seen': rd[2], 'flags': rd[3], 'resid_along': round(a, 1),
                             'resid_lat': round(c, 1) if rd[1] is not None else None, 'relief_corrected': True}
                # review round 2: only a numerically measured, relief-corrected fuselage centre verifies the line (within
                # 1.5 m; the relief fit leaves 0.7 m rms), never the reading the position was taken from (F15)
                if rd[1] is not None and abs(c) <= 1.5 and 'u' not in rd[3] and not np_: vb.append('naip')
            if s.get('paint') and s['paint']['n'] >= 8 and s['paint']['rms'] <= 0.3:
                pa = s.get('paint_after') or s['paint']
                if abs(pa['lat_nose']) <= 0.8 and abs(pa['dh']) <= 1.5: vb.append('paint')
            good = []; rej = []
            for st in ev:
                a, c = local((st['x'], st['z']), nose, h)
                if abs(c) < 12 and -35 < a < 8: good.append((st, a, c))
                else: rej.append((st['hex'], st.get('callsign'), st.get('type'), round(a, 1), round(c, 1)))
            new_types = []
            for st, a, c in good:
                t = st.get('type')
                if t and type_cls(t) and (not st.get('sfo_type') or not type_cls(st['sfo_type']) or type_cls(st['sfo_type']) == type_cls(t)):
                    new_types.append(t)
            if it == 0 and new_types and max((type_cls(t) for t in new_types), key=ORDER.index) != cls \
                    and ORDER.index(max((type_cls(t) for t in new_types), key=ORDER.index)) > ORDER.index(cls):
                adsb_types = new_types; continue
            break
        s['types_unknown'] = unknown
        # lead-in polyline for the painted stand line (review round 1: curved lead-ins must not be painted as a straight
        # ray): the oriented OSM way; moved with the stand when the painted line corrected it; a straight 40 m line for
        # stands positioned on NAIP (F15, whose OSM way is a stub)
        pts = [tuple(q) for q in w['pts']]
        if s['pos_src'] == 'naip':
            f0 = hdg_vec(h); pts = [(nose[0] - f0[0] * 40, nose[1] - f0[1] * 40), nose]
        elif s['pos_src'] == 'osm+paint':
            th = math.radians(s['paint']['dh']); ro = (math.cos(math.radians(h_osm)), math.sin(math.radians(h_osm)))
            def tr(q):
                vx, vz = q[0] - stop[0], q[1] - stop[1]
                return (stop[0] + vx * math.cos(th) - vz * math.sin(th) + ro[0] * s['paint']['lat_nose'],
                        stop[1] + vx * math.sin(th) + vz * math.cos(th) + ro[1] * s['paint']['lat_nose'])
            pts = [tr(q) for q in pts]
        s['leadin_pts'] = pts
        s['obs_types'] = sorted(set(sfo_types + adsb_types))
        if good:
            per = {}
            for st, a, c in good:
                if st['hex'] not in per or st['n_good'] > per[st['hex']][0]['n_good']: per[st['hex']] = (st, a, c)
            A = [v[1] for v in per.values()]; C = [v[2] for v in per.values()]
            D = [hdiff(v[0]['hdg'], h) for v in per.values() if v[0].get('hdg') is not None]
            s['adsb'] = {'n_aircraft': len(per), 'along_med': round(float(np.median(A)), 1), 'lat_med': round(float(np.median(C)), 1),
                         'lat_absmax': round(float(np.max(np.abs(C))), 1), 'dhdg_med': round(float(np.median(D)), 1) if D else None,
                         'aircraft': sorted('%s %s %s' % (v[0].get('reg'), v[0].get('type'), v[0].get('callsign')) for v in per.values())}
            # review round 2: 1.5 m (was 3 m; G5 had passed at 1.8 m)
            if abs(np.median(C)) <= 1.5 and (not D or abs(np.median(D)) <= 10): vb.append('adsb')
            elif abs(np.median(C)) > 3.0 or (D and abs(np.median(D)) > 10):
                # aircraft SFO put on this stand (stand window) stopped clearly off the model axis: a conflict with the
                # other evidence, recorded instead of being dropped silently (review round 2: D3, D4, D9)
                s['conflict'] = {'with': 'adsb', 'n_aircraft': len(per), 'lat_med': round(float(np.median(C)), 1),
                                 'dhdg_med': round(float(np.median(D)), 1) if D else None, 'aircraft': s['adsb']['aircraft'],
                                 'note': 'parked aircraft with SFO stand windows sit off the model axis; not resolved'}
        else: s.pop('adsb', None)
        if rej: s['adsb_rejected'] = rej
        pbest = {}
        for st, a, c in good:
            if abs(c) <= 3 and (st['hex'] not in pbest or st['n_good'] > pbest[st['hex']][0]['n_good']): pbest[st['hex']] = (st, a, c)
        s['adsb_good'] = [(v[0].get('type') or v[0].get('sfo_type'), v[1]) for v in pbest.values()]
        if s.get('conflict'): s['verified_unconfirmed'] = vb; vb = []      # conflicting evidence: nothing counts as verified
        s['verified_by'] = vb
        # src (legacy observed / inferred): 'obs' only when an aircraft was seen on the line (NAIP or ADS-B); the painted
        # lead-in alone confirms the axis (lateral, heading), not the stop point -> 'inf' (review round 2)
        s['src'] = 'obs' if ('naip' in vb or 'adsb' in vb) else 'inf'
        s['osm_resid'] = None if s['pos_src'] == 'osm' else dict(zip(('along', 'lat'), [round(v, 1) for v in local(stop, nose, h)]))
    # ---------------------------------------------------------------- per-family stop points (review round 2)
    # The app parks every type with its nose at the stand's one nose point, but real stop marks are per type: narrow
    # bodies on stands built for larger types stop well short (ADS-B: 737s at E12, F16, F17, F21, an A319 at G7). For each
    # aircraft family the typical ADS-B reference offset (antenna behind the nose) is the median over all stands of its
    # group; where a family's aircraft on one stand stop more than 5 m (n >= 2) / 10 m (n = 1) off that, the stand gets
    # type_stops[family] = {along (m, - = short of the stand nose), n, src 'adsb'}. geom.stand_env uses them; the app
    # does not yet (request: js/live/traffic.js per-type stop points).
    fam_al = defaultdict(list)
    for s in stands:
        for t, a in s.get('adsb_good', []):
            fm = GM.FAMILY.get(ALIAS_T.get(t, t))
            if fm and type_cls(t) and (type_cls(t) in WIDE) == (s['grp'] == 'wide'): fam_al[fm].append(a)
    fam_ref = {fm: float(np.median(v)) for fm, v in fam_al.items() if len(v) >= 3}
    for s in stands:
        by = defaultdict(list)
        for t, a in s.get('adsb_good', []):
            fm = GM.FAMILY.get(ALIAS_T.get(t, t))
            if fm in fam_ref: by[fm].append(a)
        tsd = {}
        for fm, v in by.items():
            d_ = float(np.median(v)) - fam_ref[fm]
            if (len(v) >= 2 and abs(d_) >= 5) or abs(d_) >= 10:
                tsd[fm] = {'along': round(min(d_, 0.0), 1), 'n': len(v), 'src': 'adsb (median %.1f m vs family %.1f m)' % (float(np.median(v)), fam_ref[fm])}
        s['type_stops'] = {k: v for k, v in tsd.items() if v['along'] < 0} or None
    print('family ADS-B reference offsets', {k: round(v, 1) for k, v in fam_ref.items()})
    print('type_stops', {s['name']: s['type_stops'] for s in stands if s['type_stops']})
    # ---------------------------------------------------------------- mutual exclusion / clearances
    # Review round 1: clearances are computed with the union of EVERY type the app accepts on each stand (geom.py
    # accepted_types / envelope: shorter aircraft of a class carry their wings further forward), not one reference
    # type per class. A pair closer than PHYS (3 m) is made mutually exclusive, unless SFO plans both at the same time;
    # then each stand is limited to the largest span / length SFO (or accepted ADS-B) actually put there
    # ('span_max' / 'len_max'), and only if that still does not clear 3 m the pair becomes exclusive.
    pass  # geom imported at module level
    for s in stands: s['excl'] = []; s['clear'] = {}; s['span_max'] = None; s['len_max'] = None
    def sim_count(a, b):
        n_ = 0
        for x in [q for n0 in a['aodb'] or [a['name']] for q in ivs.get(n0, [])]:
            for y in [q for n1 in b['aodb'] or [b['name']] for q in ivs.get(n1, [])]:
                if x[2] != y[2] and min(x[1], y[1]) - max(x[0], y[0]) > 600: n_ += 1
        return n_
    def is_alt(a, b):
        return a.get('alt_of') == b['name'] or b.get('alt_of') == a['name'] or bool(a.get('alt_of') and a.get('alt_of') == b.get('alt_of'))
    near = [(a, b) for i, a in enumerate(stands) for b in stands[i + 1:] if math.dist(a['nose'], b['nose']) <= 170]
    how = {}
    for a, b in near:
        if is_alt(a, b):
            a['excl'].append(b['name']); b['excl'].append(a['name']); how[(a['name'], b['name'])] = 'alternative positions (excl)'; continue
        d = GM.stand_env(a).distance(GM.stand_env(b))
        if d >= PHYS: continue
        sim = sim_count(a, b)
        if sim:
            for s_ in (a, b):
                ts = [ALIAS_T.get(t, t) for t in s_['obs_types']]
                if not ts: continue
                sp = max(REF[t]['span'] for t in ts); L = max(REF[t]['L'] for t in ts)
                if sp < CLASS_MAX[s_['cls']][0] - 0.6: s_['span_max'] = min(s_['span_max'] or 99, sp)
                if L < CLASS_MAX[s_['cls']][1] - 2: s_['len_max'] = min(s_['len_max'] or 999, L)
            d2 = GM.stand_env(a).distance(GM.stand_env(b))
            if d2 >= PHYS:
                how[(a['name'], b['name'])] = 'span_max / len_max = largest types SFO parks there (clear %.1f m)' % d2; continue
            if d2 > 0.0:
                # SFO really parks both at once, and with the limits the envelopes no longer overlap: making them
                # exclusive would push real, simultaneously parked aircraft off their stands. Kept, reported as a
                # tight pair (our stop points are one per stand, real stop marks are per type).
                how[(a['name'], b['name'])] = 'kept: SFO plans both at once %d times; span/len limits; model clearance %.1f m < 3 m (tight, no overlap)' % (sim, d2)
                a.setdefault('tight', []).append(b['name']); b.setdefault('tight', []).append(a['name']); continue
        a['excl'].append(b['name']); b['excl'].append(a['name'])
        how[(a['name'], b['name'])] = 'excl' + (' (SFO plans both at once %d times, but even its largest types overlap)' % sim if sim else '')
    pairs = []
    for a, b in near:
        d = GM.stand_env(a).distance(GM.stand_env(b))
        need = max(icao_clear(max(REF[t]['span'] for t in GM.accepted_types(a))), icao_clear(max(REF[t]['span'] for t in GM.accepted_types(b))))
        pairs.append((a['name'], b['name'], round(d, 1), need, sim_count(a, b), is_alt(a, b), how.get((a['name'], b['name']))))
        if d < 60: a['clear'][b['name']] = round(d, 1); b['clear'][a['name']] = round(d, 1)
    # ---------------------------------------------------------------- jet bridges
    by_gate = defaultdict(list)
    bmap = {}
    for jb in JB:
        g = None
        if jb['ref'] and re.match(r'^[A-G]\d+[A-Z]?$', jb['ref']): g = jb['ref']
        elif jb.get('name'):
            m = re.match(r'^([A-G]\d+)\b', jb['name']); g = m.group(1) if m else None
        jb['gate'] = G.stand_base(g) if g else None
    # building attach for branches: the parent's first node
    def parent_attach(jb):
        if jb['base_bdist'] < 2.0: return jb['base'], [jb['base']]
        best = None
        for o in JB:
            if o is jb or o['base_bdist'] >= 2.0: continue
            ls = LineString(o['pts']); d = ls.distance(Point(jb['base']))
            if d < 1.5 and (best is None or d < best[0]):
                best = (d, o)
        if best:
            o = best[1]; ls = LineString(o['pts']); u = ls.project(Point(jb['base']))
            walk = [o['pts'][0]]
            acc = 0
            for k in range(1, len(o['pts'])):
                seg = math.dist(o['pts'][k - 1], o['pts'][k])
                if acc + seg >= u: break
                walk.append(o['pts'][k]); acc += seg
            return o['pts'][0], walk + [jb['base']]
        return jb['base'], [jb['base']]
    for jb in JB:
        att, walk = parent_attach(jb)
        jb['attach'] = att; jb['walk'] = walk + list(jb['pts'][1:-1])
        jb['cab'] = jb['pts'][-1]
        # rotunda = start of the parked tunnel = first node of the final segment when the way has a fixed part before
        # it (>= 3 nodes, final segment >= 4 m). The SFO Museum outline includes some fixed walkway fingers, so the
        # building distance is not used here. A two-node way (facade -> cab) has no separate walkway -> None.
        # Review round 1: a branch (base on another bridge's walkway) starts its tunnel at the branch point, and final
        # segments of 4-8 m are fully retracted tunnels (B10), so the threshold is 4 m (was 8 m).
        r0 = jb['pts'][-2] if len(jb['pts']) >= 3 else (jb['pts'][0] if jb['base_bdist'] >= 2.0 and len(walk) > 1 else None)
        jb['rotunda'] = r0 if (r0 is not None and math.dist(r0, jb['cab']) >= 4) else None
    stand_by_name = {s['name']: s for s in stands}
    used = set()
    def door_pt(s, k):
        r = REF[CLS_REF[s['cls']]]; f = hdg_vec(s['hdg']); lt = (-math.cos(math.radians(s['hdg'])), -math.sin(math.radians(s['hdg'])))
        back = {1: 5.5 if s['grp'] == 'narrow' else 6.8, 2: 17.5 if s['grp'] == 'wide' else 14.0}[k]
        return (s['nose'][0] - f[0] * back + lt[0] * r.get('F', 2.5), s['nose'][1] - f[1] * back + lt[1] * r.get('F', 2.5))
    for s in stands:
        s['bridges'] = []
    # Association = optimal assignment (scipy linear_sum_assignment) of OSM bridges to door slots (narrow-body 1,
    # wide-body 2, class F 3). A bridge's pivot = its rotunda (else its building attach point). Feasible only if the
    # pivot or the parked cab is not on the stand's right side (lat < +3 m) and within 8-48 m of the door; cost = pivot-door distance
    # + 10 m when the bridge's OSM ref/name gate differs from the stand's gate/alias (OSM bridge refs are shifted at
    # the B-west pods, so geometry leads). Alternates (B5S ...) are assigned in a second, independent pass.
    from scipy.optimize import linear_sum_assignment
    def pivot(jb): return jb['rotunda'] or jb['attach']
    def slots(pass_alt):
        out = []
        for s in stands:
            if bool(s.get('alt_of')) != pass_alt: continue
            n = 3 if s['cls'] == 'F' else 2 if s['cls'] in WIDE else 1
            nf = sum(1 for v in TB.BRIDGE_FORCE.values() if v == s['name'])      # slots already filled by forced bridges
            for k in range(1 + nf, n + 1): out.append((s, k))
        return out
    def assign(pass_alt):
        SL = slots(pass_alt); C = np.full((len(JB), len(SL)), 1e6)
        for i, jb in enumerate(JB):
            if jb['osm_id'] in TB.BRIDGE_IGNORE or jb['osm_id'] in TB.BRIDGE_FORCE: continue
            # alternates (pass 2) only take bridges no base stand uses: a bridge must exist once in the app
            if pass_alt and jb['osm_id'] in used: continue
            pv = pivot(jb)
            for j, (s, k) in enumerate(SL):
                dp = door_pt(s, min(k, 2)); l_ = min(local(pv, s['nose'], s['hdg'])[1], local(jb['cab'], s['nose'], s['hdg'])[1])
                d = math.dist(pv, dp)
                if l_ >= 3.0 or not (8 <= d <= 48): continue
                same = jb['gate'] and (jb['gate'] == s['gate'] or jb['gate'] in s['alias'] or jb['ref'] == s['name'])
                C[i, j] = d + (0 if same else 10) + (k - 1) * 0.5
        r, c = linear_sum_assignment(C)
        for i, j in zip(r, c):
            if C[i, j] < 1e5:
                s = SL[j][0]; s['bridges'].append(JB[i]); used.add(JB[i]['osm_id'])
                JB[i]['assoc'] = 'ref+geometry' if C[i, j] - (SL[j][1] - 1) * 0.5 < math.dist(pivot(JB[i]), door_pt(s, min(SL[j][1], 2))) + 5 else 'geometry'
    for bid, sn in TB.BRIDGE_FORCE.items():
        jb = next(j for j in JB if j['osm_id'] == bid); st_ = next(s for s in stands if s['name'] == sn)
        st_['bridges'].append(jb); used.add(bid); jb['assoc'] = 'forced (stand_table.BRIDGE_FORCE)'
    assign(False); assign(True)
    for bid, sn in TB.BRIDGE_OVERRIDES.items():
        jb = next(j for j in JB if j['osm_id'] == bid)
        if bid not in used:
            next(s for s in stands if s['name'] == sn)['bridges'].append(jb); used.add(bid); jb['assoc'] = 'override (stand_table)'
    orphan_bridges = [jb for jb in JB if jb['osm_id'] not in used and jb['osm_id'] not in TB.BRIDGE_IGNORE]
    # door numbers: order by distance of the rotunda from the nose along the axis (nearest the nose = door 1)
    for s in stands:
        bs = sorted(s['bridges'], key=lambda jb: -local(jb['cab'], s['nose'], s['hdg'])[0])
        out = []
        for k, jb in enumerate(bs):
            door = min(k + 1, 3)
            out.append({'gate': jb['gate'] or s['gate'], 'attach': [round(v, 2) for v in jb['attach']], 'door': door,
                        'rotunda': [round(v, 2) for v in jb['rotunda']] if jb['rotunda'] else None, 'assoc': jb.get('assoc'), 'cab': [round(v, 2) for v in jb['cab']],
                        'walk': [[round(v, 2) for v in p] for p in jb['walk']], 'osm_id': jb['osm_id']})
        # a third bridge (A380 upper deck, door 3) is kept apart: the app's bridge model docks main-deck doors only
        s['bridge_list'] = [b for b in out if b['door'] <= 2]; s['bridge_upper'] = [b for b in out if b['door'] == 3]
    # ---------------------------------------------------------------- rotunda feasibility (review round 1)
    # An OSM rotunda closer to the door than the shortest apron-drive bridge can retract (9.846 m + 3 m cab, geom.py)
    # or inside the wing sweep of the types SFO parks there is moved back along the OSM fixed walkway (0.5 m steps,
    # at most to 1 m from the building end) until both hold; 'rotunda_osm' keeps the mapped point.
    pass  # geom imported at module level
    from shapely.geometry import Point as _P
    for st in stands:
        obs = [ALIAS_T.get(t, t) for t in st['obs_types']] or [CLS_REF[st['cls']]]
        eo = GM.envelope(st['nose'], st['hdg'], obs)
        for b in st['bridge_list']:
            if not b.get('rotunda'): continue
            doors = [GM.door(st['nose'], st['hdg'], t, GM.dock_door(t, b['door'])) for t in obs if GM.dock_door(t, b['door'])]
            if not doors: continue
            path = [tuple(q) for q in b['walk']] + [tuple(b['rotunda'])]
            def ok(pt, pre):
                if min(math.dist(pt, dp) for dp in doors) - GM.PIVOT_TO_DOOR < GM.EXT_MIN: return False
                g = unary_union([LineString(pre + [pt]).buffer(GM.WALK_W / 2, cap_style=2) if len(pre) else _P(pt).buffer(0.01), _P(pt).buffer(GM.ROT_R)])
                return g.intersection(eo).area <= 0.3
            if ok(path[-1], path[:-1]): continue
            # walk back along the polyline
            segs = list(zip(path[:-1], path[1:]))[::-1]; moved = 0.0; found = None; pre_all = path[:-1]
            for i, (p0, p1) in enumerate(segs):
                L = math.dist(p0, p1); pre = path[:len(path) - 1 - i]
                for sdist in np.arange(0.5, L + 1e-9, 0.5):
                    q = (p1[0] + (p0[0] - p1[0]) * sdist / L, p1[1] + (p0[1] - p1[1]) * sdist / L)
                    if math.dist(q, path[0]) < 1.0: break
                    if ok(q, pre): found = (q, pre, moved + sdist); break
                if found: break
                moved += L
            if found:
                q, pre, dm = found
                b['rotunda_osm'] = b['rotunda']; b['rotunda'] = [round(q[0], 2), round(q[1], 2)]
                b['walk'] = [[round(v, 2) for v in p_] for p_ in pre]; b['rotunda_src'] = 'moved %.1f m back along the OSM walkway (min. extension / wing clearance)' % dm
            else:
                b['rotunda_src'] = 'OSM (too close to the door or inside the wing sweep; the walkway gives no feasible point)'
                problems.append((st['name'], 'rotunda of bridge %s infeasible' % b['osm_id']))
    # ---------------------------------------------------------------- bridge poses (review round 1)
    # cab_pose: OSM maps some bridges docked (cab within 6 m of a door of a type the stand accepts), others parked.
    # stow: a rest (parked) pose for the tunnel end, clear of the envelope (+1 m) of every stand within 150 m -
    #   including the stand's own accepted types, its alternative positions and exclusive neighbours, whose aircraft
    #   taxi in while this bridge rests - of the building and of the other bridges (fixed parts and rests, +0.5 m);
    #   tunnel 9.85-30 m from the pivot; the pose nearest the OSM direction / length is kept.
    # rotunda_max_r: half the distance to the nearest other rotunda, and the clearance to other fixed walkways (2.6 m
    #   wide), capped at the 2.45 m model radius - how small a rotunda must be drawn there.
    bld_poly = unary_union([Polygon(r).buffer(0) for r in building_rings()])
    envs = {st['name']: GM.stand_env(st) for st in stands}
    allb = [(st, b) for st in stands for b in st['bridge_list'] + st['bridge_upper']]
    for st, b in allb:
        best = None
        for k in (1, 2):
            for t in GM.accepted_types(st):
                dp = GM.door(st['nose'], st['hdg'], t, k)
                if dp: best = min(best or 1e9, math.dist(dp, b['cab']))
        b['cab_pose'] = 'docked' if best is not None and best < 6.0 else 'parked'
        b['cab_door_dist'] = round(best, 1) if best is not None else None
    rots = [(id(b), b['rotunda']) for st, b in allb if b.get('rotunda')]
    # (a branch's rotunda lies on its parent's walkway by construction - same building end - so that walkway is skipped)
    walks = [(id(b), tuple(b['attach']), LineString([tuple(q) for q in b['walk']] + [tuple(b.get('rotunda') or b['attach'])])) for st, b in allb
             if len(b['walk']) >= 1 and math.dist(b['walk'][0], b.get('rotunda') or b['attach']) > 0.5]
    for st, b in allb:
        if b.get('rotunda'):
            dm = min([math.dist(b['rotunda'], r) for i, r in rots if i != id(b)] or [99])
            dw = min([w.distance(Point(b['rotunda'])) for i, at, w in walks if i != id(b) and at != tuple(b['attach'])] or [99])
            b['rotunda_max_r'] = round(max(0.0, min(GM.ROT_R, dm / 2 - 0.05, dw - GM.WALK_W / 2 - 0.05)), 2)
    static = []
    for st, b in allb:
        wl, rot, _ = GM.bridge_parts(b, b['cab'])
        static.append((id(b), tuple(b['attach']), unary_union([wl, rot])))
    placed = []
    for st, b in sorted(allb, key=lambda x: gkey(x[0]['name'])):
        pv = b.get('rotunda') or b['attach']
        L0 = math.dist(pv, b['cab']); u0 = ((b['cab'][0] - pv[0]) / max(L0, 1e-6), (b['cab'][1] - pv[1]) / max(L0, 1e-6))
        obst = [envs[o['name']].buffer(1.0) for o in stands if math.dist(o['nose'], pv) < 150]
        obst += [g.buffer(0.5) for i, at, g in static if i != id(b) and at != tuple(b['attach']) and g.distance(Point(pv)) < 80]
        obst += [g.buffer(0.5) for g in placed if g.distance(Point(pv)) < 80]
        from shapely.prepared import prep
        O = prep(unary_union(obst))
        cands = []
        for dd in range(0, 181, 2):
            for sg in ((1, -1) if dd else (1,)):
                a = math.radians(sg * dd); u = (u0[0] * math.cos(a) - u0[1] * math.sin(a), u0[0] * math.sin(a) + u0[1] * math.cos(a))
                for L in np.arange(GM.EXT_MIN, 30.01, 1.0):
                    cp = (pv[0] + u[0] * L, pv[1] + u[1] * L)
                    _, _, tc = GM.bridge_parts(b, cp)
                    tc2 = tc.difference(Point(pv).buffer(max(0.0, b.get('rotunda_max_r') or GM.ROT_R) + 0.3))
                    # the rotunda itself is a fixed part (checked separately by check_stands); the rest pose is judged
                    # outside the rotunda disc
                    if O.intersects(tc2) or tc2.intersection(bld_poly).area > 0.5: continue
                    cost = dd / 10 + abs(L - (L0 if b['cab_pose'] == 'parked' else 12.0)) / 5
                    cands.append((cost, cp, dd * sg, L, tc))
            if cands and dd > 20 and min(c[0] for c in cands) < dd / 10: break
        if cands:
            c = min(cands, key=lambda c: c[0])
            b['stow'] = [round(c[1][0], 2), round(c[1][1], 2)]; b['stow_turn_deg'] = c[2]; b['stow_len'] = round(float(c[3]), 1)
            placed.append(c[4])
        else:
            b['stow'] = None; problems.append((st['name'], 'no stow pose for bridge %s' % b['osm_id']))
    # ---------------------------------------------------------------- remote / cargo / maintenance positions
    contact_ids = {s['osm_way']['osm_id'] for s in stands}
    positions = []
    for r in LI:
        if r['osm_id'] in contact_ids or r['hdg'] is None: continue
        if r['bdist'] < 50 and r['ref'] is None: zone = 'contact-unused'
        elif r['ref'] and re.match(r'^[A-G]\d', r['ref']): zone = 'contact-unused'
        else:
            x, z = r['stop']
            zone = 'north' if z < -550 else ('west' if x < -1700 else 'apron')
        positions.append({'osm_id': r['osm_id'], 'ref': r['ref'], 'stop': r['stop'], 'hdg': r['hdg'], 'zone': zone, 'orient': r['orient']})
    # SFO remote stands with ADS-B evidence (stays with an AODB remote stand window) -> nearest OSM position
    remote = []
    rem_stays = defaultdict(list)
    for st in stays['stays']:
        n = st.get('stand')
        if n and not re.match(r'^[A-G]\d{1,2}[A-Z]?$', n): rem_stays[n].append(st)
    for n, L in sorted(rem_stays.items(), key=lambda kv: gkey(kv[0])):
        per = {}
        for st in L:
            if st['hex'] not in per or st['n_good'] > per[st['hex']]['n_good']: per[st['hex']] = st
        P = np.array([[st['x'], st['z']] for st in per.values()]); m = np.median(P, axis=0)
        spread = float(np.max(np.hypot(*(P - m).T))) if len(P) > 1 else 0.0
        hs = [st['hdg'] for st in per.values() if st.get('hdg') is not None]
        best = min(positions, key=lambda p: math.dist(p['stop'], m)) if positions else None
        dd = math.dist(best['stop'], m) if best else 1e9
        rec = {'name': n, 'adsb': {'n_aircraft': len(per), 'x': round(float(m[0]), 2), 'z': round(float(m[1]), 2), 'spread': round(spread, 1),
                                   'hdg': round(float(np.median(hs)), 1) if hs else None,
                                   'aircraft': sorted('%s %s %s' % (st.get('reg'), st.get('type'), st.get('callsign')) for st in per.values())},
               'types': dict(aodb_types.get(n, {}))}
        if best and dd < 25:
            f = hdg_vec(best['hdg']); rec.update({'x': round(best['stop'][0], 2), 'z': round(best['stop'][1], 2), 'hdg': round(best['hdg'], 2),
                                                  'pos_src': 'osm', 'osm_id': best['osm_id'], 'osm_resid_m': round(dd, 1)})
            best['sfo_name'] = n
        else:
            rec.update({'x': round(float(m[0]), 2), 'z': round(float(m[1]), 2), 'hdg': rec['adsb']['hdg'], 'pos_src': 'adsb',
                        'note': 'no OSM parking position within 25 m (nearest %.0f m)' % dd})
        rec['name_src'] = 'sfo'; rec['verified_by'] = ['adsb']
        remote.append(rec)
    # ---------------------------------------------------------------- write
    res = build_output(stands, remote, positions, naip_off, info, osm)
    full = {'stands': [{k: v for k, v in s.items() if k not in ('osm_way', 'bridges', 'types')} | {
        'types': dict(s['types']), 'osm': {k: s['osm_way'][k] for k in ('osm_id', 'osm_version', 'osm_ts', 'ref', 'stop', 'hdg', 'orient', 'len')}} for s in stands],
        'pairs': pairs, 'problems': problems, 'orphan_bridges': [(jb['osm_id'], jb['ref'], jb.get('name'), [round(v, 1) for v in jb['cab']]) for jb in orphan_bridges],
        'naip_offset': naip_off, 'remote': remote, 'positions': positions}
    json.dump(full, open(os.path.join(WORK, 'stands_built.json'), 'w'), indent=1, default=lambda o: list(o) if isinstance(o, tuple) else str(o))
    summary(stands, remote, positions, pairs, problems, orphan_bridges, naip_off)


def build_output(stands, remote, positions, naip_off, info, osm):
    # Display names (review round 1): `name` keeps its old meaning = the gate number SFO signs show (A1, E10, G13 ...)
    # wherever that is unique; only the alternative positions (B5S, B11S, B16S, C9V - they share a gate with their base
    # stand) keep the AODB name. The AODB names are in `aodb`, the gate number in `gate`.
    gates_n = Counter(s['gate'] for s in stands)
    disp = {s['name']: (s['gate'] if (not s.get('alt_of') and gates_n[s['gate']] == 1) or s['name'] == s['gate'] else s['name']) for s in stands}
    for s in stands: s['disp'] = disp[s['name']]
    out = []
    for s in stands:
        def br(b):
            b = dict(b); b['gate'] = s['gate']      # bridge sign = the stand's gate number (not the OSM ref / AODB name)
            return b
        rec = {'name': disp[s['name']], 'alias': s['alias'], 'letter': s['name'][0], 'nose': [round(v, 2) for v in s['nose']],
               'hdg': round(s['hdg'] % 360, 2), 'cls': s['cls'], 'src': s['src'],
               'bridges': [br(b) for b in s['bridge_list']],
               'bridges_upper': [br(b) for b in s['bridge_upper']], 'shares_bridges_of': disp[s['alt_of']] if s.get('alt_of') and not s['bridge_list'] else None,
               # --- added 24 Sep 2026 (docs/research/stands_rebuild.md)
               'gate': s['gate'], 'aodb': s['aodb'], 'excl': sorted((disp[n] for n in s['excl']), key=gkey), 'alt_of': disp[s['alt_of']] if s.get('alt_of') else None,
               'pos_src': s['pos_src'], 'name_src': 'sfo', 'verified_by': s['verified_by'], 'cls_src': s['cls_src'],
               'largest_type': s['largest_type'], 'obs_types': s['obs_types'], 'span_max': s.get('span_max'), 'len_max': s.get('len_max'),
               'a380': s['cls'] == 'F', 'osm_id': s['osm_way']['osm_id'],
               'tight_with': sorted((disp[n] for n in s.get('tight', [])), key=gkey),
               'conflict': s.get('conflict'), 'type_stops': s.get('type_stops'), 'verified_unconfirmed': s.get('verified_unconfirmed'),
               'resid': {'naip': {k: s['naip'][k] for k in ('resid_along', 'resid_lat')} if s.get('naip') else None,
                         'adsb': {k: s['adsb'][k] for k in ('n_aircraft', 'along_med', 'lat_med', 'dhdg_med')} if s.get('adsb') else None,
                         'paint': s.get('paint_after') or s.get('paint'),
                         'osm': s['osm_resid']},
               'leadin': [[round(v, 2) for v in p] for p in s['leadin_pts']]}
        out.append(rec)
    res = {'frame': GF.FRAME_ID,
           'licence': 'ODbL 1.0 - contains information from OpenStreetMap (c) OpenStreetMap contributors, '
                      'https://www.openstreetmap.org/copyright; see docs/ATTRIBUTION.md',
           'sources': {'osm': 'Overpass, database %s' % osm['osm_base'], 'naip': 'USDA NAIP 2024 (2024-05-20), public domain',
                       'sfo': 'flysfo.com flight-status AODB stand names (%s); DataSF chfu-j7tc gates (PDDL)' % info,
                       'adsb': 'own ADS-B recording, adsb.lol only (ODbL 1.0; adsb.fi data is not used here: its terms forbid licensing), with SFO stand windows'},
           'note': 'Stands rebuilt 24 Sep 2026 by tools/stands/build_stands.py (docs/research/stands_rebuild.md). nose = nose tip '
                   'of the class reference aircraft (OSM stop node + NAIP-calibrated offset: narrow %.1f m, wide %.1f m); '
                   'src=obs: an aircraft was seen parked on this lead-in (NAIP 2024 relief-corrected fuselage within 1.5 m, or '
                   'ADS-B (adsb.lol) with the SFO stand window within 1.5 m / 10 deg), inf: otherwise (verified_by paint = only the '
                   'painted lead-in axis agrees; the stop point is then OSM + calibration). conflict: evidence that disagrees. '
                   'excl: stands that cannot be occupied at the same time.' % (naip_off['narrow'], naip_off['wide']),
           'a380_stands': [r['name'] for r in out if r['a380']],
           'stands': out,
           'remote': [{'name': r['name'], 'x': r['x'], 'z': r['z'], 'hdg': r.get('hdg'), 'pos_src': r['pos_src'], 'name_src': 'sfo',
                       'verified_by': r['verified_by'], 'osm_id': r.get('osm_id')} for r in remote],
           'positions': [{'x': round(p['stop'][0], 2), 'z': round(p['stop'][1], 2), 'hdg': round(p['hdg'], 2), 'zone': p['zone'],
                          'osm_id': p['osm_id'], 'ref': p['ref'], 'sfo': p.get('sfo_name')} for p in positions]}
    try:
        res['redBoxes'] = json.load(open(os.path.join(WORK, 'redboxes_naip.json')))['boxes']
    except FileNotFoundError:
        res['redBoxes'] = []
    js = json.dumps(res, separators=(',', ':'))
    json.dump(res, open(os.path.join(ROOT, 'data', 'sfo_stands.json'), 'w'), separators=(',', ':'))
    open(os.path.join(ROOT, 'data', 'sfo_stands.js'), 'w').write(
        '// generated by tools/stands/build_stands.py - ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap '
        'contributors (docs/ATTRIBUTION.md)\nexport const STANDS = ' + js + ';\n')
    return res


def summary(stands, remote, positions, pairs, problems, orphan_bridges, naip_off):
    print('NAIP nose offsets', naip_off)
    print(len(stands), 'contact stands;', Counter(s['pos_src'] for s in stands), Counter(s['src'] for s in stands),
          Counter(s['cls'] for s in stands))
    print('verified_by', Counter(tuple(s['verified_by']) for s in stands))
    print('bridges', sum(len(s['bridge_list']) for s in stands if not s.get('alt_of')), Counter(len(s['bridge_list']) for s in stands))
    print('no bridge:', [s['name'] for s in stands if not s['bridge_list']])
    print('orphan OSM bridges:', [(jb['osm_id'], jb['ref'], jb.get('name')) for jb in orphan_bridges])
    print('problems:', problems)
    print('remote', len(remote), [(r['name'], r['pos_src']) for r in remote]); print('positions', Counter(p['zone'] for p in positions))
    print('excl:', {s['name']: s['excl'] for s in stands if s['excl']})
    A = [s['adsb'] for s in stands if s.get('adsb')]
    if A:
        print('ADS-B: stands %d, |lat| median %.1f max %.1f, along median %.1f' % (len(A), np.median([abs(a['lat_med']) for a in A]),
              max(abs(a['lat_med']) for a in A), np.median([a['along_med'] for a in A])))
    Nn = [s['naip'] for s in stands if s.get('naip')]
    print('NAIP: stands %d, |resid_lat| median %.1f, |resid_along| median %.1f' % (len(Nn), np.median([abs(n['resid_lat']) for n in Nn if n['resid_lat'] is not None]), np.median([abs(n['resid_along']) for n in Nn])))
    for s in stands:
        if s.get('adsb') and (abs(s['adsb']['lat_med']) > 3 or (s['adsb']['dhdg_med'] is not None and abs(s['adsb']['dhdg_med']) > 10)):
            print('  ADS-B disagrees:', s['name'], s['adsb'])
        if s.get('adsb_rejected'): print('  ADS-B stays far from', s['name'], s['adsb_rejected'][:4])


if __name__ == '__main__':
    main()
