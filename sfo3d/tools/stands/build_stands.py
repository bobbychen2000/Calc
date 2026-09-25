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
                         snapshots) + types seen parked there in ADS-B; dimensions, planforms and doors are the app's
                         (js/aircraft/types.js via geom.APP; review round 2), whose SPEC values are the manufacturers'
                         airport-planning numbers (tools/models/check_dims.py).
  per-type stops         type_stops: ADS-B (adsb.lol) families stopping short of the stand nose; types_ok: whitelist
                         where class limits alone would let a simultaneously planned neighbour within 3 m.
  verification           NAIP 2024 (USDA, public domain) readings of parked aircraft (stand_table.NAIP_OBS), corrected
                         for relief displacement (naip_relief.py), and ADS-B parked stays (adsb.lol only) with SFO stand
                         windows (adsb_parked.py): residuals per stand; disagreeing ADS-B -> 'conflict'.
  mutual exclusion       stands whose reference aircraft would overlap / come within the physical minimum (3 m) of
                         each other are mutually exclusive ('excl'); pairs SFO plans simultaneously are reported.
Google screenshots are NOT used for anything here.

Outputs: data/sfo_stands.json + .js (committed, ODbL: contains OSM-derived positions), refs/cache/stands/
stands_built.json (full provenance incl. residual tables, gitignored) and a summary on stdout.
Usage: python3 tools/stands/build_stands.py
"""
import datetime as dt, json, math, os, re, sys
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
# Review round 3: CL is the 757 class = 757-200/-300 WITH winglets (Boeing airport FAQ, geom.WINGLET_SPAN: 41.1 m span;
# 757-300 length 54.43 m). It was (38.5, 48): the baseline 757-200 span, and too short for the 757-300 (C5 / F17 had
# gone to class D for its length). Same table in js/live/airport.js CLASS_MAX.
CLASS_MAX = {'B': (28.5, 37), 'C': (36.5, 45), 'CL': (41.1, 54.5), 'D': (52, 62), 'E': (61, 68), 'EL': (65.5, 77), 'F': (80, 80)}
ORDER = ['B', 'C', 'CL', 'D', 'E', 'EL', 'F']
# reference planform per class = the largest type of the class that SFO parks (REF dims: ACAP documents)
CLS_REF = {'B': 'E75L', 'C': 'A321', 'CL': 'B753', 'D': 'B763', 'E': 'B772', 'EL': 'B77W', 'F': 'A388'}
ALIAS_T = {'E175': 'E75L', 'B787': 'B789', 'B76W': 'B763', 'B75W': 'B752', 'E295': 'E195'}   # ICAO designators without their own REF
# (B76W / B75W: SFO AODB codes of the 767-300 / 757-200 with winglets; geom.py gives B752 / B753 / B763 the winglet span.
#  E295: E195-E2 dims not in REF; SFO parks it only at B2 next to B738/B39M, which set that stand's class anyway.)
WIDE = {'D', 'E', 'EL', 'F'}
# ICAO clearances between aircraft on stands (ICAO Doc 9157 Part 2, 4th ed. 2005, §3.4.4 = Annex 14 Vol I 3.13.6;
# read from refs/cache/icao/sky3090.pdf p. 3-10): code letter A, B 3.0 m; C 4.5 m; D, E, F 7.5 m (code letter by span:
# C 24-36 m, D 36-52 m, E 52-65 m, F 65-80 m). D-F may be reduced near the terminal/nose and where azimuth guidance
# (VDGS) is provided.
def icao_clear(span): return 3.0 if span < 24 else 4.5 if span < 36 else 7.5
CAB_CONV = {}   # review round 3: cab-rotation sense (set in main, written to the output)
PHYS = 3.0   # below this aircraft-to-aircraft distance two stands are treated as not usable at the same time
ROT_FACADE = 3.0   # m, facade -> rotunda centre where the drum stands against the building (inferred: r 2.45 m + connector)


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
    # Types per stand (review round 3): every VERSION of every flight in every cached snapshot counts - a type SFO once
    # planned on a stand shows the stand can take it, even if the flight was later moved (with only the newest version
    # a re-plan had removed G6's B77W and F19's A319 / B752 between runs). Intervals (simultaneous planning) keep the
    # newest version only, so a re-planned turn is not counted twice.
    import glob as _glob
    seen_ = set()
    for path_ in sorted(_glob.glob(os.path.join(G.CACHE, 'flysfo_api_flight-status_*.json*')), key=G.snapshot_time):
        for r in G.load_flysfo(path_)[2]:
            t = (r.get('aircraft_transport_type') or {}).get('icao_code'); turn = tuple(sorted([r['flight_id'], r.get('linked_flight_id') or '']))
            for s in r.get('stands') or []:
                n = s['stand']['stand_name']
                if (n, turn, t) in seen_: continue
                seen_.add((n, turn, t)); aodb_types[n][t] += 1; aodb_turns[n].add(turn)
    for r in recs:
        t = (r.get('aircraft_transport_type') or {}).get('icao_code'); turn = tuple(sorted([r['flight_id'], r.get('linked_flight_id') or '']))
        for s in r.get('stands') or []:
            n = s['stand']['stand_name']
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
            # the last 3-22 m behind the nose. Applied when the fit is clean (>= 7 samples (review round 2; was 8), rms <= 0.3 m) and
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
            if pf and ok_naip and pf['n'] >= 7 and pf['rms'] <= 0.3 and (abs(pf['lat_nose']) > 0.8 or abs(pf['dh']) > 1.5) \
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
                if w['osm_id'] in TB.NAIP_IMAGED: s['naip']['imaged'] = TB.NAIP_IMAGED[w['osm_id']]
                # review round 2: only a numerically measured, relief-corrected fuselage centre verifies the line (within
                # 1.5 m; the relief fit leaves 0.7 m rms), never the reading the position was taken from (F15).
                # Review round 3: the stop point must agree too - an along residual beyond 1.5 m (the reading accuracy)
                # is a conflict (narrow-body stands: the model nose is where that aircraft should have stopped) or, on
                # wide-body stands, unexplained (the imaged type is not identified, so a type-dependent stop is possible);
                # neither verifies. 'u' readings (nose not visible) are not used for either.
                if 'u' not in rd[3] and not np_:
                    if abs(a) > 1.5: s['naip']['along_conflict'] = True
                    elif rd[1] is not None and abs(c) <= 1.5: vb.append('naip')
            if s.get('paint') and s['paint']['n'] >= 7 and s['paint']['rms'] <= 0.3:
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
        # review round 3: provenance of names and classes that rest on no AODB / type evidence (G11: SFO's AODB never
        # names it; DataSF gates G11 / G12 do; its class had no type at all)
        if not s['aodb']:
            s['name_src'] = 'sfo (DataSF gate number only)'
            s['name_note'] = ('SFO\'s AODB (flight-status stands[]) never names this position in the cached snapshots; the name is the '
                              'DataSF chfu-j7tc gate number(s) %s, and pairing those gates with this OSM lead-in is inferred' % ', '.join([s['gate']] + s['alias']))
        if s['cls_src'].startswith('default'):
            rd_ = RD.get(w['osm_id'])
            s['cls_src'] = 'inferred: no type seen (AODB / ADS-B); ' + ('NAIP 2024 shows a %s body on the line (type not identified)' % rd_[2] if rd_ else 'pier default')
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
        if (s.get('naip') or {}).get('along_conflict'):
            # review round 3: the parked NAIP aircraft stopped more than 1.5 m from the model nose (relief-corrected)
            s['conflict_along'] = {'with': 'naip', 'resid_along': s['naip']['resid_along'],
                                   'note': ('narrow-body stand: the imaged aircraft stopped %+.1f m from the model nose (+ = beyond); '
                                            'the stop point is not verified' if s['cls'] in ('B', 'C', 'CL') else
                                            'wide-body stand: the imaged aircraft stopped %+.1f m from the model nose; its type is not '
                                            'identified, so a type-dependent stop mark may explain it - not verified') % s['naip']['resid_along']}
            if s['naip'].get('imaged'): s['conflict_along']['imaged'] = s['naip']['imaged']
        else: s.pop('conflict_along', None)
        s['verified_by'] = vb
        # src (legacy observed / inferred): 'obs' only when an aircraft was seen on the line (NAIP or ADS-B); the painted
        # lead-in alone confirms the axis (lateral, heading), not the stop point -> 'inf' (review round 2). Review round 3:
        # never 'obs' while the NAIP aircraft on the line stopped > 1.5 m from the model nose (the stop point is then
        # contradicted, even if ADS-B confirms the axis laterally); a corroborated per-family stop can explain it (below).
        s['src'] = 'obs' if ('naip' in vb or 'adsb' in vb) and not s.get('conflict_along') else 'inf'
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
        # review round 3: a family stop of 3-5 m that the NAIP aircraft on the same line confirms (its relief-corrected
        # nose within 1.5 m of the ADS-B stop, n >= 2 ADS-B aircraft; B22: three E-Jets 4.3-5.4 m short, NAIP -4.1 m)
        rn = s.get('naip') or {}
        if rn.get('along_conflict') and s['cls'] in ('B', 'C', 'CL'):
            for fm, v in by.items():
                d_ = float(np.median(v)) - fam_ref[fm]
                if fm not in tsd and len(v) >= 2 and d_ <= -3.0 and abs(d_ - rn['resid_along']) <= 1.5 \
                        and max(abs(a_ - fam_ref[fm] - d_) for a_ in v) <= 1.5:
                    tsd[fm] = {'along': round(d_, 1), 'n': len(v), 'src': 'adsb (median %.1f m vs family %.1f m) + naip (%+.1f m)' % (float(np.median(v)), fam_ref[fm], rn['resid_along'])}
                    s['conflict_along']['explained_by'] = fm
                    s['conflict_along']['note'] += '; explained by the %s stop (ADS-B n=%d at %+.1f m agrees)' % (fm, len(v), d_)
        s['type_stops'] = {k: v for k, v in tsd.items() if v['along'] < 0} or None
        if (s.get('conflict_along') or {}).get('explained_by') and ('adsb' in s['verified_by'] or 'naip' in s['verified_by']): s['src'] = 'obs'
    # Stands whose calibrated nose puts the aircraft against the building (review round 2: F16 0.05 m, F17 0.59 m from the
    # Boarding Area F facade; their OSM lead-ins end at the facade) are moved back to the stop ADS-B shows there, when
    # it does: the stand nose takes the family stop (pos_src 'osm+adsb'), the other families keep their offsets.
    bpoly = unary_union([Polygon(r).buffer(0) for r in building_rings()])
    for s in stands:
        if not s['type_stops'] or s['pos_src'] == 'naip': continue
        dB = GM.stand_env(s).distance(bpoly)
        if dB >= 2.0: continue
        fm, v = min(s['type_stops'].items(), key=lambda kv: kv[1]['along'])
        a0 = v['along']; f = hdg_vec(s['hdg'])
        s['nose'] = (s['nose'][0] + f[0] * a0, s['nose'][1] + f[1] * a0)
        s['pos_src'] = s['pos_src'] + '+adsb'
        s['nose_rule'] += '; moved %.1f m back to the stop ADS-B shows for %s (%s; the calibrated nose was %.2f m from the building)' % (-a0, fm, v['src'], dB)
        ts2 = {}
        for k, w in s['type_stops'].items():
            if k != fm and w['along'] - a0 < -1.0: ts2[k] = dict(w, along=round(w['along'] - a0, 1))
        s['type_stops'] = ts2 or None
        print('  moved back from the building:', s['name'], round(a0, 1), 'm')
    print('family ADS-B reference offsets', {k: round(v, 1) for k, v in fam_ref.items()})
    print('type_stops', {s['name']: s['type_stops'] for s in stands if s['type_stops']})
    # ---------------------------------------------------------------- mutual exclusion / clearances
    # Review round 1: clearances are computed with the union of EVERY type the app accepts on each stand (geom.py
    # accepted_types / envelope: shorter aircraft of a class carry their wings further forward), not one reference
    # type per class. A pair closer than PHYS (3 m) is made mutually exclusive, unless SFO plans both at the same time;
    # then each stand is limited to the largest span / length SFO (or accepted ADS-B) actually put there
    # ('span_max' / 'len_max'), and only if that still does not clear 3 m the pair becomes exclusive.
    pass  # geom imported at module level
    for s in stands: s['excl'] = []; s['clear'] = {}; s['span_max'] = None; s['len_max'] = None; s['types_ok'] = None
    def sim_count(a, b):
        n_ = 0
        for x in [q for n0 in a['aodb'] or [a['name']] for q in ivs.get(n0, [])]:
            for y in [q for n1 in b['aodb'] or [b['name']] for q in ivs.get(n1, [])]:
                if x[2] != y[2] and min(x[1], y[1]) - max(x[0], y[0]) > 600: n_ += 1
        return n_
    def expand_ok(s_, obs):
        # review round 3: a whitelist of exact designators refused smaller aircraft SFO also parks there. types_ok = the
        # observed types plus every type whose planform (engines included) at its per-family stop lies inside the
        # envelope of the observed types (within 0.05 m): such a type cannot come closer to a neighbour than they do.
        env = GM.envelope(s_['nose'], s_['hdg'], obs) if not s_.get('type_stops') else unary_union(
            [GM.planform(GM.nose_for(s_, t), s_['hdg'], t) for t in obs])
        envb = env.buffer(0.05); out = set(obs)
        for t, r in GM.APP.items():
            if t in out or not r['span']: continue
            if GM.planform(GM.nose_for(s_, t), s_['hdg'], t).difference(envb).area < 0.01: out.add(t)
        return sorted(out)
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
            # review round 2: still < 3 m with every type inside the limits -> both stands accept only the types SFO /
            # ADS-B actually put there ('types_ok', at their per-family stop points); the app needs the request
            # (js/live/traffic.js standFits: honour g.typesOk) for this to hold at runtime
            for s_ in (a, b):
                if s_['obs_types']: s_['types_ok'] = expand_ok(s_, sorted(set(ALIAS_T.get(t, t) for t in s_['obs_types']) & set(GM.APP)))
            d3 = GM.stand_env(a).distance(GM.stand_env(b))
            if d3 >= PHYS:
                how[(a['name'], b['name'])] = 'types_ok = the types SFO parks there (observed), per-family stops: clear %.1f m (SFO plans both at once %d times)' % (d3, sim)
                continue
            d2 = d3
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
    from shapely.ops import nearest_points
    bld_all = unary_union([Polygon(r).buffer(0) for r in building_rings()])
    for jb in JB:
        att, walk = parent_attach(jb)
        P = [tuple(q) for q in jb['pts']]
        jb['attach'] = att; jb['cab'] = P[-1]
        # Rotunda = start of the parked tunnel. Review round 3 (the rule of rounds 1-2 left 20 bridges without one):
        #  * cab stub: several OSM ways end with a short (< 7.5 m) segment after a long one (>= 8 m) - the cab, drawn
        #    after the tunnel (C3-C11, D16, E4, E5, E7, E12, A4 ...; NAIP shows the tunnel along the long segment). No
        #    apron-drive bridge is that short (the smallest retracts to 12.2 m from the rotunda centre to the end of the
        #    cab spacer, Oshkosh sell sheet), so the tunnel is the long segment: rotunda = its first node, tunnel end
        #    ('tunnel_end') = the stub's first node, cab = the way's end.
        #  * otherwise the first node of the final segment when the way has a fixed part before it;
        #  * a branch (base on another bridge's walkway): the branch point;
        #  * a way that starts ON the facade with the tunnel (two-node ways at the D / E piers, B2, B10): NAIP shows the
        #    tube starting at the facade with no fixed corridor, so the drum stands against the facade: rotunda =
        #    facade end + ROT_FACADE along the way (inferred: drum radius 2.45 m + ~0.5 m connector);
        #  * a way that starts off the building without a parent (F22 L1, 15 m out): rotunda = that start, fixed walkway
        #    from the nearest facade point (inferred; NAIP shows a corridor to the building).
        stub = len(P) >= 3 and math.dist(P[-2], P[-1]) < 7.5 and math.dist(P[-3], P[-2]) >= 8.0
        ri = len(P) - (3 if stub else 2)
        if stub: jb['tunnel_end'] = P[-2]
        if ri >= 1:
            r0 = P[ri]; jb['walk'] = walk + P[1:ri + 1]
            jb['rotunda_src'] = 'OSM node: start of the tunnel' + (' before the cab stub (review round 3)' if stub else ' (first node of the final segment)')
        elif len(walk) > 1:
            r0 = P[0]; jb['walk'] = walk; jb['rotunda_src'] = 'OSM branch point on the parent walkway'
        elif jb['base_bdist'] < 2.0:
            L_ = math.dist(P[0], P[1]); r0 = (P[0][0] + (P[1][0] - P[0][0]) * ROT_FACADE / L_, P[0][1] + (P[1][1] - P[0][1]) * ROT_FACADE / L_)
            jb['walk'] = [P[0]]
            jb['rotunda_src'] = 'inferred: drum against the facade, %.1f m out along the OSM way (no fixed walkway mapped or imaged)' % ROT_FACADE
        else:
            q = nearest_points(bld_all.boundary, Point(P[0]))[0]; jb['attach'] = (q.x, q.y)
            r0 = P[0]; jb['walk'] = [(q.x, q.y)]
            jb['rotunda_src'] = 'inferred: the OSM way starts %.1f m off the building; rotunda there, fixed walkway from the nearest facade point' % jb['base_bdist']
        jb['rotunda'] = r0 if math.dist(r0, jb.get('tunnel_end') or P[-1]) >= 4 else None
        if jb['rotunda'] is None: jb['rotunda_src'] = 'none (tunnel shorter than 4 m)'
        # review round 3: `walk` is the fixed corridor building -> rotunda and always ends AT the rotunda (the facade /
        # off-building rules above had left a one-point walk, which a consumer drawing walk as the corridor lost)
        elif math.dist(jb['walk'][-1], r0) > 0.05: jb['walk'] = list(jb['walk']) + [r0]
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
                        'walk': [[round(v, 2) for v in p] for p in jb['walk']], 'osm_id': jb['osm_id'], 'rotunda_src': jb.get('rotunda_src'),
                        'tunnel_end': [round(v, 2) for v in jb['tunnel_end']] if jb.get('tunnel_end') else None})
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
            doors = [GM.door(GM.nose_for(st, t), st['hdg'], t, GM.dock_door(t, b['door'])) for t in obs if GM.dock_door(t, b['door'])]
            if not doors: continue
            path = [tuple(q) for q in b['walk']]
            if math.dist(path[-1], b['rotunda']) > 0.05: path.append(tuple(b['rotunda']))
            def ok(pt, pre):
                if min(math.dist(pt, dp) for dp in doors) - GM.PIVOT_TO_DOOR < GM.EXT_MIN: return False   # (pivot on the door normal: distance >= this)
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
                b['walk'] = [[round(v, 2) for v in p_] for p_ in list(pre) + [q]]; b['rotunda_src'] = (b.get('rotunda_src') or 'OSM') + '; moved %.1f m back along the walkway (min. extension / wing clearance)' % dm
            else:
                b['rotunda_src'] = (b.get('rotunda_src') or 'OSM') + '; too close to the door or inside the wing sweep, and the walkway gives no feasible point'
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
            # two rotundas < 4 m apart at the end of one fixed walkway (F15, G11): NAIP shows both tunnels leaving one
            # elevated junction at the walkway end - a twin head (inferred), modelled as two small drums (rotunda_max_r)
            twin = [ob for so, ob in allb if ob is not b and ob.get('rotunda') and math.dist(ob['rotunda'], b['rotunda']) < 4.0 and ob['attach'] == b['attach']]
            if twin: b['rotunda_twin_of'] = twin[0]['osm_id']
            dm = min([math.dist(b['rotunda'], r) for i, r in rots if i != id(b)] or [99])
            dw = min([w.distance(Point(b['rotunda'])) for i, at, w in walks if i != id(b) and at != tuple(b['attach'])] or [99])
            b['rotunda_max_r'] = round(max(0.0, min(GM.ROT_R, dm / 2 - 0.05, dw - GM.WALK_W / 2 - 0.05)), 2)
    # ---------------------------------------------------------------- bridge model per bridge (review round 3)
    # One bridge is one datasheet model (geom.MODELS, Oshkosh AeroTech sell sheet): its operational range, not the
    # 9.846-41.381 m span of the whole product line, limits both docking and resting. The model (inferred - SFO's
    # bridge inventory is not published) = the smallest-retracting one that covers every docking of the types SFO /
    # ADS-B put on the stand (and on alternative positions that share its bridges), each at its per-family stop.
    # Where no single model covers them the bridge keeps the range of the model that reaches the longest docking and
    # the stand is listed (review round 3: G7 A319 stop, E12 737 stop, A2 L2, E4 ...). ext_range = the range the app
    # should dock within; dock_types_out = accepted types this bridge cannot dock (it stays at its stow pose).
    sharers = defaultdict(list)
    for o in stands:
        if o.get('alt_of') and not o['bridge_list']: sharers[o['alt_of']].append(o)
    def obs_of(st_):
        return sorted(set(ALIAS_T.get(t, t) for t in st_['obs_types']) & set(GM.APP)) or [CLS_REF[st_['cls']]]
    def dockings(st_, b, types):
        pv = b.get('rotunda') or b['attach']; rt = GM.rv(st_['hdg']); out = []
        for t in types:
            k = GM.dock_door(t, b['door']) if b['door'] <= 2 else None
            dp = GM.door(GM.nose_for(st_, t), st_['hdg'], t, k) if k else None
            if not dp: continue
            cp = (dp[0] - rt[0] * GM.PIVOT_TO_DOOR, dp[1] - rt[1] * GM.PIVOT_TO_DOOR)
            out.append((t, math.dist(pv, cp), cp, st_['name']))
        return out
    for st, b in allb:
        users = [st] + sharers.get(st['name'], [])
        dk = [d_ for u_ in users for d_ in dockings(u_, b, obs_of(u_))]
        acc = [d_ for u_ in users for d_ in dockings(u_, b, GM.accepted_types(u_))]
        b['_acc_docks'] = acc; b['_obs_docks'] = dk
        if b['door'] > 2 or not dk:
            b['model'] = None; b['ext_range'] = [GM.EXT_MIN, GM.EXT_MAX]
            b['model_src'] = 'not modelled (upper-deck bridge: the app docks main-deck doors only)' if b['door'] > 2 else 'no docking type'
            b['dock_types_out'] = []; continue
        lo, hi = min(d_[1] for d_ in dk), max(d_[1] for d_ in dk)
        m = GM.choose_model(lo, hi); tol = ''
        if not m: m = GM.choose_model(lo, hi, 1.0); tol = ' (within 1.0 m: stop-point / rotunda uncertainty)'
        if m:
            b['model'] = m[0]; b['ext_range'] = [m[1], m[2]]
            b['model_src'] = 'inferred: the smallest-retracting datasheet model covering the observed dockings %.1f-%.1f m%s' % (lo, hi, tol)
        else:
            # no model covers every observed docking: the model covering most of them (the rest cannot dock this bridge;
            # listed), then the shortest retraction. The stand is flagged (DATA problem, check_stands ISSUE).
            ex = [d_[1] for d_ in dk]
            mm = max(GM.MODELS, key=lambda mm: (sum(mm[1] - 1.0 <= e_ <= mm[2] + 1.0 for e_ in ex), -mm[1], -mm[2]))
            b['model'] = None; b['ext_range'] = [mm[1], mm[2]]
            short = sorted('%s %.1f' % (d_[0], d_[1]) for d_ in dk if d_[1] < mm[1] - 1.0)
            long_ = sorted('%s %.1f' % (d_[0], d_[1]) for d_ in dk if d_[1] > mm[2] + 1.0)
            b['model_src'] = ('NO single datasheet model covers the observed dockings %.1f-%.1f m; ext_range = %s, the model covering most '
                              'of them (cannot dock: too close %s; too far %s)' % (lo, hi, mm[0], ', '.join(short) or '-', ', '.join(long_) or '-'))
            problems.append((st['name'], 'bridge %s L%d: no single bridge model covers %.1f-%.1f m (%s)' % (b['osm_id'], b['door'], lo, hi, b['model_src'].split('(')[-1].rstrip(')'))))
        e0, e1 = b['ext_range']
        b['dock_types_out'] = sorted(set(d_[0] for d_ in acc if not (e0 - 1.0 <= d_[1] <= e1 + 1.0)))
    # cab rotation (review round 3): the sell sheet gives 125 deg standard = 92.5 deg cw / 32.5 deg ccw, 185 deg optional.
    # Docked, the cab faces the door (fuselage normal); its turn = signed angle tunnel -> cab axis. Which sense the sheet
    # calls cw is not stated: the sense under which more observed dockings fit the standard cab is taken (inferred;
    # CAB_CONV in the output). Per bridge: cab_turn_deg [min, max] (+ = the sheet's cw) and cab_option.
    sg_all = []
    for st, b in allb:
        pv = b.get('rotunda') or b['attach']
        b['_ang'] = []
        for t, e_, cp, sn in b.get('_obs_docks', []):
            if not (b['ext_range'][0] - 1.0 <= e_ <= b['ext_range'][1] + 1.0): continue
            L_ = math.dist(pv, cp); u = ((cp[0] - pv[0]) / L_, (cp[1] - pv[1]) / L_)
            b['_ang'].append((t, GM.angle(u, GM.rv(stand_by_name[sn]['hdg'])))); sg_all.append(b['_ang'][-1][1])
    fitA = sum(-GM.CAB_CCW <= a <= GM.CAB_CW for a in sg_all); fitB = sum(-GM.CAB_CW <= a <= GM.CAB_CCW for a in sg_all)
    CW = 1 if fitA >= fitB else -1
    CAB_CONV.update({'cw_is': 'clockwise seen from above (x east, z south)' if CW == 1 else 'counter-clockwise seen from above',
                     'fit_standard': max(fitA, fitB), 'fit_other_sense': min(fitA, fitB), 'n': len(sg_all),
                     'note': 'inferred: the sense under which more observed dockings fit 92.5 cw / 32.5 ccw (Oshkosh sell sheet)'})
    for st, b in allb:
        A_ = [CW * a for t, a in b.pop('_ang', [])]
        if not A_: continue
        b['cab_turn_deg'] = [round(min(A_), 1), round(max(A_), 1)]
        if all(-GM.CAB_CCW <= a <= GM.CAB_CW for a in A_): b['cab_option'] = 'standard (125 deg)'
        elif all(abs(a) <= GM.CAB_OPT_HALF for a in A_): b['cab_option'] = 'optional 185 deg cab needed (inferred)'
        else:
            b['cab_option'] = 'beyond the optional cab'; problems.append((st['name'], 'bridge %s L%d: cab turn %.0f..%.0f deg' % (b['osm_id'], b['door'], min(A_), max(A_))))
    # docked footprints (tunnel + cab) of every bridge for every accepted type it can dock (within its ext_range + 1 m)
    dockfp = {}
    for st, b in allb:
        e0, e1 = b['ext_range']; dockfp[id(b)] = {}
        for t, e_, cp, sn in b.get('_acc_docks', []):
            if e0 - 1.0 <= e_ <= e1 + 1.0: dockfp[id(b)].setdefault(t, []).append(GM.bridge_parts(b, cp)[2])
        dockfp[id(b)] = {t: unary_union(v) for t, v in dockfp[id(b)].items()}
    static = []
    for st, b in allb:
        wl, rot, _ = GM.bridge_parts(b, b['cab'])
        static.append((id(b), tuple(b['attach']), unary_union([wl, rot])))
    placed = []
    from shapely.prepared import prep
    for st, b in sorted(allb, key=lambda x: gkey(x[0]['name'])):
        pv = b.get('rotunda') or b['attach']
        L0 = math.dist(pv, b['cab']); u0 = ((b['cab'][0] - pv[0]) / max(L0, 1e-6), (b['cab'][1] - pv[1]) / max(L0, 1e-6))
        obst = [envs[o['name']].buffer(1.0) for o in stands if math.dist(o['nose'], pv) < 150]
        obst += [g.buffer(0.5) for i, at, g in static if i != id(b) and at != tuple(b['attach']) and g.distance(Point(pv)) < 80]
        # review round 3: rest poses at least 1.0 m apart (F15 L1 / L2 had rested 0.59 m apart)
        obst += [g.buffer(1.0) for g in placed if g.distance(Point(pv)) < 80]
        # review round 3: other bridges DOCKED while this one rests - a sibling on the same stand for every type this
        # bridge does not dock (F15 / G7 / G13: L1 docks a narrow body, L2 stays at rest), every bridge of another stand
        # for every type it docks (that stand is occupied while this one is empty)
        for so, ob in allb:
            if ob is b or math.dist(ob.get('rotunda') or ob['attach'], pv) > 80: continue
            for t, g in dockfp[id(ob)].items():
                if so is st and b['door'] <= 2 and GM.dock_door(t, b['door']) is not None and t in dockfp[id(b)]: continue
                obst.append(g.buffer(0.5))
        O = prep(unary_union(obst))
        e0, e1 = b['ext_range']; Lmin = max(GM.EXT_MIN, e0); Lmax = max(Lmin, min(30.0, e1))
        Lt = min(max(L0 if b['cab_pose'] == 'parked' else Lmin + 1.0, Lmin), Lmax)
        cands = []
        for dd in range(0, 181, 2):
            for sg in ((1, -1) if dd else (1,)):
                a = math.radians(sg * dd); u = (u0[0] * math.cos(a) - u0[1] * math.sin(a), u0[0] * math.sin(a) + u0[1] * math.cos(a))
                for L in np.arange(Lmin, Lmax + 0.01, 1.0):
                    cp = (pv[0] + u[0] * L, pv[1] + u[1] * L)
                    _, _, tc = GM.bridge_parts(b, cp)
                    tc2 = tc.difference(Point(pv).buffer(max(0.0, b.get('rotunda_max_r') or GM.ROT_R) + 0.3))
                    # the rotunda itself is a fixed part (checked separately by check_stands); the rest pose is judged
                    # outside the rotunda disc (review round 3: building overlap <= 0.1 m2, was 0.5)
                    if O.intersects(tc2) or tc2.intersection(bld_poly).area > 0.1: continue
                    cost = dd / 10 + abs(L - Lt) / 5
                    cands.append((cost, cp, dd * sg, L, tc))
            if cands and dd > 20 and min(c[0] for c in cands) < dd / 10: break
        if cands:
            c = min(cands, key=lambda c: c[0])
            b['stow'] = [round(c[1][0], 2), round(c[1][1], 2)]; b['stow_turn_deg'] = c[2]; b['stow_len'] = round(float(c[3]), 1)
            placed.append(c[4])
        else:
            b['stow'] = None; problems.append((st['name'], 'no stow pose for bridge %s (length %.1f-%.1f m)' % (b['osm_id'], Lmin, Lmax)))
    for st, b in allb: b.pop('_acc_docks', None); b.pop('_obs_docks', None)
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
        # review round 3: no 40 m paved disc any more (js/live/airport.js drew one, across the perimeter wall at 2-2A).
        # The stand carries its class (largest type SFO / ADS-B put there) and 'pave': the envelope of the class's
        # accepted types at the stop + 3 m, clipped to the OSM aeroway=apron polygon(s) it stands on (the airside
        # apron; the GSE lane and the road beyond the wall are outside it). 'pave_outside_apron' = envelope area (m2)
        # outside those aprons (0 = the whole aircraft is on mapped apron).
        tt = [ALIAS_T.get(t, t) for t in list(rec['types']) + [st.get('type') for st in per.values()] if t]
        tt = [t for t in tt if type_cls(t)]
        rec['cls'] = max((type_cls(t) for t in tt), key=ORDER.index) if tt else 'C'
        rec['obs_types'] = sorted(set(tt))
        if rec.get('hdg') is not None:
            pseudo = {'nose': (rec['x'], rec['z']), 'hdg': rec['hdg'], 'cls': rec['cls'], 'span_max': None, 'len_max': None, 'types_ok': None, 'type_stops': None}
            env = GM.stand_env(pseudo)
            aprons = [Polygon(a['w']).buffer(0) for a in osm['aprons'] if len(a['w']) >= 4]
            on = unary_union([a for a in aprons if a.intersects(env)]) if aprons else None
            pv_ = env.buffer(3.0).intersection(on) if on is not None and not on.is_empty else env.buffer(3.0)
            pv_ = max(getattr(pv_, 'geoms', [pv_]), key=lambda g: g.area).simplify(0.2)
            rec['pave'] = [[round(x, 2), round(z, 2)] for x, z in list(pv_.exterior.coords)[:-1]]
            rec['pave_outside_apron'] = round(env.difference(on).area, 1) if on is not None and not on.is_empty else None
        remote.append(rec)
    # review round 3: SFO stand names in the AODB snapshots without a position here, listed instead of dropped silently
    # (G103-G105 were in the pre-rebuild data). ref_point = the SFO Museum gate point of that name (CDLA-Permissive-1.0;
    # a point without heading or stop line - not enough to place an aircraft, so the stand is not modelled).
    sfom = {g['name']: g for g in json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))['gates']}
    placed_names = {r['name'] for r in remote} | {n for s in stands for n in [s['name']] + s['aodb']}
    unplaced = []
    for n in sorted(aodb_types, key=gkey):
        if n in placed_names or not n: continue
        contact = bool(re.match(r'^[A-G]\d{1,2}[A-Z]?$', n))
        if contact and n not in TB.DROPPED: continue
        w_ = sorted(ivs.get(n, []))
        rec = {'name': n, 'kind': 'contact (alternative position)' if contact else 'remote',
               'aodb_turns': len(aodb_turns[n]), 'types': dict(aodb_types[n]),
               'first': dt.datetime.fromtimestamp(w_[0][0], dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ') if w_ else None,
               'last': dt.datetime.fromtimestamp(w_[-1][1], dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ') if w_ else None,
               'ref_point': [sfom[n]['x'], sfom[n]['z']] if n in sfom else None,
               'ref_point_src': 'SFO Museum gate point (CDLA-Permissive-1.0); no heading / stop line' if n in sfom else None,
               'reason': TB.DROPPED.get(n) or ('no ADS-B parked stay with this stand window in the recording, no lead-in '
                                               'identified; ' + ('SFO Museum has a point of this name' if n in sfom else 'no licence-clean position'))}
        unplaced.append(rec)
    li_by = {r['osm_id']: r for r in LI}
    for n, ex in TB.UNPLACED_EXTRA.items():
        if n in placed_names: continue
        li = li_by.get(ex['osm'])
        unplaced.append({'name': n, 'kind': 'contact (SFO Museum name, no AODB allocation seen)', 'aodb_turns': 0, 'types': {},
                         'ref_point': [sfom[n]['x'], sfom[n]['z']] if n in sfom else None,
                         'ref_point_src': 'SFO Museum gate point (CDLA-Permissive-1.0)' if n in sfom else None,
                         'osm_leadin': {'osm_id': ex['osm'], 'stop': [round(v, 2) for v in li['stop']], 'hdg': round(li['hdg'], 2)} if li else None,
                         'reason': ex['why']})
    # ---------------------------------------------------------------- write
    res = build_output(stands, remote, positions, naip_off, info, osm, unplaced)
    full = {'stands': [{k: v for k, v in s.items() if k not in ('osm_way', 'bridges', 'types')} | {
        'types': dict(s['types']), 'osm': {k: s['osm_way'][k] for k in ('osm_id', 'osm_version', 'osm_ts', 'ref', 'stop', 'hdg', 'orient', 'len')}} for s in stands],
        'pairs': pairs, 'problems': problems, 'orphan_bridges': [(jb['osm_id'], jb['ref'], jb.get('name'), [round(v, 1) for v in jb['cab']]) for jb in orphan_bridges],
        'naip_offset': naip_off, 'remote': remote, 'positions': positions, 'unplaced': unplaced}
    json.dump(full, open(os.path.join(WORK, 'stands_built.json'), 'w'), indent=1, default=lambda o: list(o) if isinstance(o, tuple) else str(o))
    summary(stands, remote, positions, pairs, problems, orphan_bridges, naip_off)


def build_output(stands, remote, positions, naip_off, info, osm, unplaced=()):
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
            # review round 2: bridge geometry is OSM-traced and NOT verified on NAIP (the imaged roofs lean east ~0.54 m
            # per m of height, ~3-4 m for a bridge; the parked cab pose changes between images)
            b['geom_src'] = 'osm (traced; not NAIP-verified)'
            return b
        rec = {'name': disp[s['name']], 'alias': s['alias'], 'letter': s['name'][0], 'nose': [round(v, 2) for v in s['nose']],
               'hdg': round(s['hdg'] % 360, 2), 'cls': s['cls'], 'src': s['src'],
               'bridges': [br(b) for b in s['bridge_list']],
               'bridges_upper': [br(b) for b in s['bridge_upper']], 'shares_bridges_of': disp[s['alt_of']] if s.get('alt_of') and not s['bridge_list'] else None,
               # --- added 24 Sep 2026 (docs/research/stands_rebuild.md)
               'gate': s['gate'], 'aodb': s['aodb'], 'excl': sorted((disp[n] for n in s['excl']), key=gkey), 'alt_of': disp[s['alt_of']] if s.get('alt_of') else None,
               'pos_src': s['pos_src'], 'name_src': s.get('name_src', 'sfo'), 'verified_by': s['verified_by'], 'cls_src': s['cls_src'],
               'largest_type': s['largest_type'], 'obs_types': s['obs_types'], 'span_max': s.get('span_max'), 'len_max': s.get('len_max'),
               'a380': s['cls'] == 'F', 'osm_id': s['osm_way']['osm_id'],
               'tight_with': sorted((disp[n] for n in s.get('tight', [])), key=gkey),
               'types_ok': s.get('types_ok'), 'conflict': s.get('conflict'), 'type_stops': s.get('type_stops'), 'verified_unconfirmed': s.get('verified_unconfirmed'),
               'conflict_along': s.get('conflict_along'), 'name_note': s.get('name_note'),
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
           'cab_convention': CAB_CONV,
           'bridge_models': {'source': 'Oshkosh AeroTech Jetway Glass & Steel Truss sell sheet 2025 (operational retraction / extension, rotunda centre -> cab pivot)',
                             'models': [list(m) for m in GM.MODELS]},
           'stands': out,
           'remote': [{'name': r['name'], 'x': r['x'], 'z': r['z'], 'hdg': r.get('hdg'), 'pos_src': r['pos_src'], 'name_src': 'sfo',
                       'verified_by': r['verified_by'], 'osm_id': r.get('osm_id'), 'cls': r.get('cls'), 'obs_types': r.get('obs_types'),
                       'pave': r.get('pave'), 'pave_outside_apron': r.get('pave_outside_apron')} for r in remote],
           # review round 3: SFO stand names (AODB) without a position in this file - not modelled, with the evidence
           'unplaced': list(unplaced),
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
