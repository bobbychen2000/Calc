"""Compare our contact stands (data/sfo_stands.json) with OSM aeroway=parking_position and X-Plane Gateway 1300 ramp
starts, and our jet bridges with OSM aeroway=jet_bridge and X-Plane 1500 jetways.

Reference points (sources quoted in docs/research/stands_xcheck.md section 3):
  ours       `nose` = nose TIP of the stopped aircraft, `hdg` = true heading (tools/sat/stand_defs.py)
  OSM        parking_position node, or the LAST node of the way = "where the nose wheel is parked" (OSM wiki); ways drawn
             the other way round (first node at the building) are detected and flipped, and counted as a data defect
  X-Plane    1300 lat/lon = nose wheel (WED WED_RampPosition::GetTips, `nosewheel_loc`); heading = true heading
So their point should lie BEHIND our nose on the centreline by the nose-tip -> nose-gear distance of the design
aircraft (X-Plane/WED draws nose tip 4.7 m (cat C) ... 9.5 m (cat D) ahead of it). Offsets are reported in our stand's
frame: along (+ = their point ahead of our nose, toward the building), cross (+ = to the right of our centreline, seen
from the cockpit), dhdg = theirs - ours.
Matching: every counterpart within MATCH_R of our nose-wheel estimate with |dhdg| <= MATCH_H is a candidate; the best
is the one minimising dist + 0.1*|dhdg|. Name match is checked separately (a counterpart with our name or one of our
aliases anywhere on the field).
Writes refs/cache/xcheck/stands_result.json and refs/cache/xcheck/tables_stands.md (markdown fragments pulled into the
report by make_report.py).
Usage: python3 tools/xcheck/compare_stands.py
"""
import json, math, os, re, statistics as st
from collections import Counter, defaultdict
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import xcommon as X

OUT = os.path.join(X.ROOT, 'refs', 'cache', 'xcheck')
MATCH_R, MATCH_H = 25.0, 45.0
# nose tip -> nose wheel used only to place our nose-wheel ESTIMATE for matching (WED GetTips nose_offset by ICAO
# code letter; our classes: B->B, C/CL->C, D->D, E/EL->E, F->F). Offsets are always reported from our nose tip.
NOSE_OFF = {'B': 2.7, 'C': 4.7, 'CL': 4.7, 'D': 9.5, 'E': 8.2, 'EL': 8.2, 'F': 8.8}
# door / class geometry as in tools/sat/export_stands.py door_st + tools/sat/stands.py CLS (length, span, fuselage width)
CLS = {'B': (31.7, 26.0, 3.0), 'C': (39.5, 35.9, 3.9), 'CL': (44.5, 35.9, 3.9), 'D': (54.9, 47.6, 5.0),
       'E': (63.7, 60.3, 5.6), 'EL': (73.9, 64.8, 6.2), 'F': (76.3, 68.4, 6.5)}
# tolerances used for the verdicts
TOL_CROSS, TOL_HDG = 3.0, 10.0


def gate_names(s):
    """'Gate A1 A2' -> ['A1','A2'];  'Gate G11-G12' / 'G11-G12' -> ['G11','G12'];  'Terminal G' -> []"""
    s = s.replace('Gate ', '').replace(',', ' ')
    out = []
    for tok in s.split():
        if re.fullmatch(r'[A-G]\d+[A-Z]?', tok): out.append(tok)
        elif re.fullmatch(r'[A-G]\d+-[A-G]?\d+', tok):
            a, b = tok.split('-'); L = a[0]; out += [a, b if b[0].isalpha() else L + b]
    return out


def base_name(n):
    return re.sub(r'[A-Z]$', '', n) if re.fullmatch(r'[A-G]\d+[A-Z]', n) else n


def frame(s):
    f = X.hdg_vec(s['hdg']); r = (-f[1], f[0])  # right-hand side in world (x east, z south): rotate f by +90 (cw from above)
    return f, r


def rel(s, x, z):
    f, r = frame(s); dx, dz = x - s['nose'][0], z - s['nose'][1]
    return dx * f[0] + dz * f[1], dx * r[0] + dz * r[1]


def main():
    A = json.load(open(os.path.join(X.ROOT, 'data', 'sfo_airport.json')))
    polys = []
    for poly in A['terminalComplex']: polys.append(Polygon(poly[0], poly[1:]))
    for b in A['boardingAreas'] + A['terminals']:
        for poly in b['polys']: polys.append(Polygon(poly[0], poly[1:]))
    BLD = unary_union([p.buffer(0) for p in polys])
    D = X.load_stands(); S = D['stands']
    xp = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'xplane', 'ksfo_apt_parsed.json')))
    osm = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')))

    # ---- their positions in our frame
    XP = []
    for i, r in enumerate(xp['ramp_starts']):
        x, z = X.wgs84_to_world(r['lat'], r['lon'])
        XP.append({'src': 'xp', 'i': i, 'label': r['name'], 'names': gate_names(r['name']), 'x': x, 'z': z,
                   'hdg': r['hdg'], 'cat': r.get('icao_cat'), 'type': r['type'], 'airlines': r.get('airlines', []),
                   'bld': BLD.distance(Point(x, z))})
    OS = []; reversed_ways = []
    for i, p in enumerate(osm['parking_positions']):
        pts = [X.wgs84_to_world(*q) for q in p['pts']]
        last, first = pts[-1], pts[0]
        dl, df = BLD.distance(Point(*last)), BLD.distance(Point(*first))
        rev = len(pts) >= 2 and df < 60 and dl - df > 5       # drawn from the stand out to the taxiway
        if rev:
            stop = first; hdg = X.world_hdg(first[0] - pts[1][0], first[1] - pts[1][1]); reversed_ways.append(p['id'])
        else:
            stop = last; hdg = p['hdg']
        OS.append({'src': 'osm', 'i': i, 'label': p['ref'] or '', 'names': [p['ref']] if p['ref'] else [], 'x': stop[0],
                   'z': stop[1], 'hdg': hdg, 'reversed': rev, 'id': p['id'], 'type': p['type'], 'len_m': p['len_m'],
                   'bld': BLD.distance(Point(*stop)), 'ts': p['timestamp'], 'user': p['user']})

    def nw_est(s):
        f, _ = frame(s); o = NOSE_OFF[s['cls']]
        return s['nose'][0] - f[0] * o, s['nose'][1] - f[1] * o

    def cands(s, L):
        ex, ez = nw_est(s); out = []
        for q in L:
            d = math.hypot(q['x'] - ex, q['z'] - ez)
            dh = X.hdg_diff(q['hdg'], s['hdg']) if q['hdg'] is not None else None
            if d <= MATCH_R and (dh is None or abs(dh) <= MATCH_H):
                out.append((d + 0.1 * abs(dh or 0), q))
        out.sort(key=lambda t: t[0]); return [q for _, q in out]

    def row_for(s, q):
        if q is None: return None
        al, cr = rel(s, q['x'], q['z'])
        dh = X.hdg_diff(q['hdg'], s['hdg']) if q['hdg'] is not None else None
        return {'label': q['label'], 'names': q['names'], 'i': q['i'], 'd_nose': round(math.hypot(al, cr), 1),
                'along': round(al, 1), 'cross': round(cr, 1), 'dhdg': None if dh is None else round(dh, 1),
                'reversed': q.get('reversed', False), 'cat': q.get('cat')}

    rows = []
    used = {'xp': defaultdict(list), 'osm': defaultdict(list)}
    for s in S:
        names = [s['name']] + s['alias']
        rec = {'name': s['name'], 'alias': s['alias'], 'cls': s['cls'], 'src': s['src'], 'hdg': s['hdg'],
               'n_bridges': len(s['bridges'])}
        for key, L in (('xp', XP), ('osm', OS)):
            c = cands(s, L)
            best = c[0] if c else None
            rec[key] = row_for(s, best)
            rec[key + '_all'] = [row_for(s, q) for q in c]
            if best: used[key][best['i']].append(s['name'])
            # name match anywhere
            nm = [q for q in L if any(base_name(n) in names for n in q['names'])]
            rec[key + '_byname'] = [row_for(s, q) for q in nm]
        rows.append(rec)

    # ---- verdicts per stand
    def pos_verdict(r, key):
        m = r[key]
        if m is None: return 'no counterpart'
        v = []
        if abs(m['cross']) > TOL_CROSS: v.append(f"lateral {m['cross']:+.1f}")
        if m['dhdg'] is not None and abs(m['dhdg']) > TOL_HDG: v.append(f"heading {m['dhdg']:+.0f}°")
        return ', '.join(v) if v else 'ok'

    def name_verdict(r, key):
        m = r[key]; names = [r['name']] + r['alias']
        if m is None:
            return 'no counterpart'
        theirs = [base_name(n) for n in m['names']]
        if not theirs: return 'unnamed'
        if r['name'] in theirs: return 'same'
        if set(theirs) & set(names): return 'alias'
        return 'DIFFERENT (' + '/'.join(m['names']) + ')'

    for r in rows:
        r['xp_pos'] = pos_verdict(r, 'xp'); r['osm_pos'] = pos_verdict(r, 'osm')
        r['xp_name'] = name_verdict(r, 'xp'); r['osm_name'] = name_verdict(r, 'osm')
        # merged in ours: several distinct named counterparts sit on this stand's candidate list
        r['osm_split'] = sorted({n for q in r['osm_all'] for n in q['names']} - {r['name']})
        r['xp_split'] = sorted({n for q in r['xp_all'] for n in q['names']} - {r['name']})

    # ---- along-track statistics (their point - our nose), by source/class/our src
    stats = {}
    for key in ('xp', 'osm'):
        g = defaultdict(list)
        for r in rows:
            m = r[key]
            if m and abs(m['cross']) <= 6 and (m['dhdg'] is None or abs(m['dhdg']) <= 15):
                g[(r['cls'], r['src'])].append(m['along'])
                g[('all', r['src'])].append(m['along'])
        stats[key] = {f'{k[0]}/{k[1]}': {'n': len(v), 'median': round(st.median(v), 1), 'min': min(v), 'max': max(v)}
                      for k, v in sorted(g.items())}

    # ---- theirs without ours
    def zone(q):
        x, z = q['x'], q['z']
        if q['bld'] <= 45: return 'contact (at a terminal facade)'
        if z < -550: return 'north field (maintenance / cargo / GA)'
        if x < -1650: return 'west field (cargo, west of pier G)'
        return 'terminal apron (remote / hardstand)'
    orphans = {}
    for key, L in (('xp', XP), ('osm', OS)):
        o = []
        for q in L:
            if q['i'] in used[key]: continue
            # also skip if it is a secondary candidate of one of our stands (alternate lead-in of a stand we have)
            near = [r['name'] for r in rows if any(c['i'] == q['i'] for c in r[key + '_all'])]
            o.append({'label': q['label'], 'names': q['names'], 'zone': zone(q), 'hdg': round(q['hdg'], 1) if q['hdg'] is not None else None,
                      'bld': round(q['bld'], 1), 'alt_of': near, 'reversed': q.get('reversed', False),
                      'cat': q.get('cat'), 'type': q.get('type'), 'x': round(q['x'], 1), 'z': round(q['z'], 1),
                      'id': q.get('id'), 'airlines': q.get('airlines')})
        orphans[key] = o

    # ---- bridges: our bridge count vs OSM jet_bridge ways and X-Plane 1500 jetways that end near the stand's doors
    JW = []
    for j in xp['jetways']:
        x, z = X.wgs84_to_world(j['lat'], j['lon']); f = X.hdg_vec(j['tunnel_hdg'])
        JW.append({'base': (x, z), 'cab': (x + f[0] * j['tunnel_len_m'], z + f[1] * j['tunnel_len_m']), 'size': j['size']})
    JB = []
    for j in osm['jet_bridges']:
        pts = [X.wgs84_to_world(*q) for q in j['pts']]
        a, b = pts[0], pts[-1]
        # the aircraft end = the end farther from the building
        if BLD.distance(Point(*a)) > BLD.distance(Point(*b)): a, b = b, a
        JB.append({'root': a, 'end': b, 'ref': j['ref']})

    def doors(s):
        L, B, F = CLS[s['cls']]; f, r = frame(s); left = (-r[0], -r[1])
        d = []
        for back in ([5.2] if s['cls'] in ('B', 'C', 'CL') else [10.0]) + ([0.33 * L] if s['cls'] in ('D', 'E', 'EL', 'F') else []):
            d.append((s['nose'][0] - f[0] * back + left[0] * F / 2, s['nose'][1] - f[1] * back + left[1] * F / 2))
        return d
    for r, s in zip(rows, S):
        ds = doors(s)
        def near_any(p, R=14.0): return min(math.hypot(p[0] - d[0], p[1] - d[1]) for d in ds) <= R
        r['xp_jetways'] = sum(1 for j in JW if near_any(j['cab']))
        r['osm_jetbridges'] = sum(1 for j in JB if near_any(j['end']))
        r['bridge_attach_to_xp_base'] = [round(min(math.hypot(b['attach'][0] - j['base'][0], b['attach'][1] - j['base'][1]) for j in JW), 1)
                                         for b in s['bridges']]

    # ---- ADS-B + SFO AODB evidence (adsb_evidence.py), keyed by our stand name
    ev = {}
    evf = os.path.join(OUT, 'adsb_evidence.json')
    if os.path.exists(evf):
        for e in json.load(open(evf))['rows']:
            if 'ours' in e: ev.setdefault(e['ours']['name'], []).append(e)
    # ---- classification
    for r in rows:
        classify(r, ev.get(r['name'], []))

    # ---- rigid offset between our survey and each source, from the cross-track residuals of good matches on
    # src=obs stands (the along component is excluded: it mixes in the reference-point convention)
    reg = {}
    for key in ('xp', 'osm'):
        A_, b_ = [], []
        for r, s in zip(rows, S):
            m = r[key]
            if r['src'] != 'obs' or m is None or abs(m['cross']) > 6 or (m['dhdg'] is not None and abs(m['dhdg']) > 15): continue
            _, rv = frame(s); A_.append(rv); b_.append(m['cross'])
        if len(A_) >= 3:
            t, *_ = np.linalg.lstsq(np.array(A_), np.array(b_), rcond=None)
            resid = np.array(b_) - np.array(A_) @ t
            reg[key] = {'n': len(A_), 'shift_east_m': round(float(t[0]), 2), 'shift_south_m': round(float(t[1]), 2),
                        'rms_cross_before': round(float(np.sqrt(np.mean(np.array(b_) ** 2))), 2),
                        'rms_cross_after': round(float(np.sqrt(np.mean(resid ** 2))), 2)}

    # per source image of our survey (tools/sat/stand_defs.py 'img'): would a rigid shift of one image explain it?
    try:
        import sys as _sys; _sys.path.insert(0, os.path.join(X.ROOT, 'tools', 'sat')); _sys.path.insert(0, os.path.join(X.ROOT, 'refs', 'cache', 'sat_legacy'))
        import stand_defs as _sd
        IMG = {s_['name']: s_['img'] for s_ in _sd.STANDS}
    except Exception:  # noqa: BLE001
        IMG = {}
    reg_img = {}
    for key in ('xp', 'osm'):
        g = defaultdict(lambda: ([], []))
        for r, s in zip(rows, S):
            m = r[key]
            if m is None or abs(m['cross']) > 20 or (m['dhdg'] is not None and abs(m['dhdg']) > 25): continue
            _, rv = frame(s); g[IMG.get(s['name'], '?')][0].append(rv); g[IMG.get(s['name'], '?')][1].append(m['cross'])
        out = {}
        for im, (A_, b_) in g.items():
            if len(A_) < 3: continue
            t, *_ = np.linalg.lstsq(np.array(A_), np.array(b_), rcond=None)
            rs = np.array(b_) - np.array(A_) @ t
            out[im] = {'n': len(A_), 'shift_east_m': round(float(t[0]), 1), 'shift_south_m': round(float(t[1]), 1),
                       'rms_before': round(float(np.sqrt(np.mean(np.array(b_) ** 2))), 1), 'rms_after': round(float(np.sqrt(np.mean(rs ** 2))), 1)}
        reg_img[key] = out
    reg['per_image'] = reg_img

    # ---- stand names by area: ours vs OSM refs vs X-Plane vs SFO (maps / DataSF / AODB via gate_truth)
    names = {}
    gt = os.path.join(X.ROOT, 'refs', 'cache', 'gate_truth', 'gates_report.json')
    GT = json.load(open(gt))['per_area'] if os.path.exists(gt) else {}
    for L_ in 'ABCDEFG':
        ours_n = sorted({n for s in S if s['letter'] == L_ for n in [s['name']] + s['alias']}, key=nkey)
        osm_n = sorted({base_name(n) for q in OS for n in q['names'] if n[0] == L_}, key=nkey)
        xp_n = sorted({n for q in XP for n in q['names'] if n[0] == L_}, key=nkey)
        g = GT.get(L_, {})
        sfo = sorted({base_name(n) for n in g.get('flysfo_stands', [])} | set(g.get('datasf_gates_used', {}).keys()), key=nkey)
        names[L_] = {'ours_incl_alias': ours_n, 'ours_own': sorted([s['name'] for s in S if s['letter'] == L_], key=nkey),
                     'osm': osm_n, 'xp': xp_n, 'sfo_used': sfo, 'sfo_map': g.get('map_gates', []),
                     'sfo_aodb': g.get('flysfo_stands', [])}

    res = {'params': {'MATCH_R': MATCH_R, 'MATCH_H': MATCH_H, 'NOSE_OFF': NOSE_OFF, 'TOL_CROSS': TOL_CROSS, 'TOL_HDG': TOL_HDG},
           'osm_base': osm['osm_base'], 'xp_scenery': xp['source'], 'rows': rows, 'stats': stats, 'orphans': orphans,
           'osm_reversed_ways': reversed_ways, 'registration': reg, 'names': names,
           'counts': {'ours': len(S), 'xp_ramps': len(XP), 'osm_positions': len(OS), 'xp_jetways': len(JW), 'osm_jet_bridges': len(JB),
                      'osm_with_ref': sum(1 for q in OS if q['names'])}}
    json.dump(res, open(os.path.join(OUT, 'stands_result.json'), 'w'), indent=1)
    write_tables(res)
    print('stands', len(rows), 'osm reversed ways', len(reversed_ways))
    print(json.dumps(stats, indent=1))


def nkey(n):
    m = re.match(r'([A-Z]+)(\d+)(.*)', n)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (n, 0, '')


def ok(m):
    return m is not None and abs(m['cross']) <= TOL_CROSS and (m['dhdg'] is None or abs(m['dhdg']) <= TOL_HDG)


def classify(r, ev):
    """flags (list) + one position verdict + one name verdict for our stand r; ev = ADS-B/SFO evidence rows"""
    x, o = r['xp'], r['osm']
    flags = []
    # position (lateral + heading); along handled separately (reference-point conventions differ)
    if x is None and o is None:
        pos = 'NO COUNTERPART'
    elif ok(o) and (x is None or ok(x)):
        pos = 'agree'
    elif ok(o) and not ok(x):
        pos = 'agree with OSM; X-Plane differs'
    elif ok(x) and not ok(o):
        pos = 'agree with X-Plane; OSM differs' if o is not None else 'agree with X-Plane (no OSM)'
    else:  # neither ok (or one missing and the other not ok)
        if x is not None and o is not None:
            same_side = abs(x['cross']) > TOL_CROSS and abs(o['cross']) > TOL_CROSS and x['cross'] * o['cross'] > 0 \
                and abs(x['cross'] - o['cross']) <= 6
            hx, ho = x['dhdg'] or 0, o['dhdg'] or 0
            same_hdg = abs(hx) > TOL_HDG and abs(ho) > TOL_HDG and hx * ho > 0 and abs(hx - ho) <= 12
            lat_ok_both = abs(x['cross']) <= TOL_CROSS and abs(o['cross']) <= TOL_CROSS
            if same_side or same_hdg or (lat_ok_both and same_hdg):
                pos = 'OURS OFF (OSM and X-Plane agree)'
            else:
                pos = 'unresolved (sources disagree)'
        else:
            pos = 'differs from the only counterpart (' + ('X-Plane' if x else 'OSM') + ')'
    # ADS-B + SFO evidence overrides the reference-vs-reference vote
    adsb = None
    for e in ev:
        oo = e['ours']; fr = oo['adsb_in_our_frame']
        # review round 3: a stay far from the stand (> 12 m across or outside -35..+8 m along) is an aircraft SFO had
        # planned here but that parked elsewhere (plan change, tow) - as in tools/stands/build_stands.py; it says nothing
        # about our stand line and is listed, not voted (with 11 snapshots such stays had turned 15 stands 'OURS OFF')
        if abs(fr['cross']) > 12.0 or not (-35.0 <= fr.get('along', 0.0) <= 8.0):
            r.setdefault('adsb_elsewhere', []).append(e['stand']); continue
        good = abs(fr['cross']) <= 3.0 and (oo['dhdg'] is None or abs(oo['dhdg']) <= 10)
        adsb = f"ADS-B @ {e['stand']}: ours {'OK' if good else 'OFF'} (aircraft {fr['cross']:+.1f} m across our centreline" + \
               (f", Δhdg {oo['dhdg']:+.0f}°" if oo['dhdg'] is not None else ', no heading') + ')'
        if oo.get('as_alias'): adsb += ' [SFO stand is our alias]'
        r.setdefault('adsb_ok', []).append(good)
    if r.get('adsb_ok'):
        pos = ('agree (ADS-B + SFO confirm ours)' if all(r['adsb_ok']) else 'OURS OFF (ADS-B + SFO)') + ' | vote: ' + pos
    # along: their stop point AHEAD of our nose tip in both sources (our nose too far from the building)
    if x and o and x['along'] > 4 and o['along'] > 4: flags.append(f"stop point {min(x['along'], o['along']):.0f}-{max(x['along'], o['along']):.0f} m ahead of our nose in both")
    # names (OSM refs matched SFO's published stand on every ADS-B-evidenced stand; X-Plane's did not)
    def nm(m):
        if m is None: return None
        return [base_name(n) for n in m['names']]
    on, xn = nm(o), nm(x)
    mine = [r['name']] + r['alias']
    all_on = sorted({base_name(n) for q in r['osm_all'] for n in q['names']})
    if r['name'] in all_on and (not on or r['name'] not in on):
        on = [r['name']]  # a second OSM lead-in within the match radius carries our name
    if on:
        name = 'same as OSM' if r['name'] in on else ('OSM = our alias ' + '/'.join(on) if set(on) & set(mine) else 'DIFFERS from OSM (' + '/'.join(on) + ')')
    elif o is not None:
        name = 'OSM position has no ref'
    else:
        name = 'no OSM counterpart'
    if xn and r['name'] not in xn and not (set(xn) & set(mine)): flags.append('X-Plane name ' + '/'.join(x['names']))
    if on and r['name'] not in on and not (set(on) & set(mine)) and pos.split(' | ')[-1].replace('vote: ', '') in ('agree', 'agree with OSM; X-Plane differs'):
        flags.insert(0, 'MISNAMED? position = OSM ' + '/'.join(on))
    split = sorted(set(r['osm_split']) - {r['name']})
    if r['alias']: flags.append('merged: SFO runs ' + '/'.join([r['name']] + r['alias']) + ' as separate stands' +
                                (f" (OSM has {'/'.join(split)} here)" if split else ''))
    elif split: flags.append('OSM has other positions here: ' + '/'.join(split))
    r['verdict'] = {'position': pos, 'name': name, 'adsb': adsb, 'flags': flags}


def f1(v): return '—' if v is None else f'{v:+.1f}'


def write_tables(res):
    rows = res['rows']
    def m_str(m):
        if m is None: return '—'
        lab = (m['label'] or '(no ref)') + (' ⟲' if m.get('reversed') else '')
        return f"{lab}: {m['d_nose']:.1f} m ({f1(m['along'])} / {f1(m['cross'])}" + ('' if m['dhdg'] is None else f", {m['dhdg']:+.0f}°") + ')'
    def byname(r, key):
        m = r[key]
        if m and r['name'] in [base_name(n) for n in m['names']]: return ''
        b = [q for q in r[key + '_byname'] if r['name'] in [base_name(n) for n in q['names']]]
        if not b: return ''
        q = min(b, key=lambda q: q['d_nose'])
        return f" · own name at {q['d_nose']:.0f} m"
    L = ['<!--BEGIN:stands_table-->',
         '| Ours (aliases) | cls · src | OSM best match: ref: dist (along / cross, Δhdg) | X-Plane best match: name: dist (along / cross, Δhdg) · cat | ADS-B + SFO | position verdict | name verdict · flags | bridges ours / XP / OSM |',
         '|---|---|---|---|---|---|---|---|']
    for r in rows:
        v = r['verdict']
        nm = r['name'] + (' (' + '/'.join(r['alias']) + ')' if r['alias'] else '')
        xs = m_str(r['xp']) + byname(r, 'xp') + (f" · {r['xp']['cat']}" if r['xp'] and r['xp'].get('cat') else '')
        L.append('| ' + ' | '.join([nm, f"{r['cls']} · {r['src']}", m_str(r['osm']) + byname(r, 'osm'), xs,
                                   (v['adsb'] or '').replace('ADS-B @ ', ''), v['position'].replace(' | vote: ', ' (vote: ') + (')' if ' | vote: ' in v['position'] else ''),
                                   ' · '.join([v['name']] + v['flags']),
                                   f"{r['n_bridges']} / {r['xp_jetways']} / {r['osm_jetbridges']}"]) + ' |')
    L.append('<!--END:stands_table-->')
    # verdict summary by src
    from collections import Counter
    L.append('<!--BEGIN:verdict_summary-->')
    L.append('| position verdict | obs | inf | total |'); L.append('|---|---|---|---|')
    cnt = Counter((r['verdict']['position'].split(' | ')[0], r['src']) for r in rows)
    for k in sorted({k for k, _ in cnt}, key=lambda k: -sum(cnt[(k, s)] for s in ('obs', 'inf'))):
        L.append(f"| {k} | {cnt[(k, 'obs')]} | {cnt[(k, 'inf')]} | {cnt[(k, 'obs')] + cnt[(k, 'inf')]} |")
    L.append('<!--END:verdict_summary-->')
    # along statistics
    L.append('<!--BEGIN:along_stats-->')
    L.append('| class / our src | X-Plane: n, median along (min…max) m | OSM: n, median along (min…max) m |'); L.append('|---|---|---|')
    keys = sorted(set(res['stats']['xp']) | set(res['stats']['osm']), key=lambda k: (k.startswith('all'), k))
    for k in keys:
        a = res['stats']['xp'].get(k); b = res['stats']['osm'].get(k)
        fmt = lambda t: '—' if not t else f"{t['n']}, {t['median']:+.1f} ({t['min']:+.1f}…{t['max']:+.1f})"
        L.append(f'| {k} | {fmt(a)} | {fmt(b)} |')
    L.append('<!--END:along_stats-->')
    # registration
    L.append('<!--BEGIN:registration-->')
    L.append('| source | image (tools/sat/stand_defs.py) | n | rigid shift E / S (m) | RMS cross before → after (m) |'); L.append('|---|---|---|---|---|')
    for key, lab in (('osm', 'OSM'), ('xp', 'X-Plane')):
        g = res['registration'].get(key)
        if g: L.append(f"| {lab} | all `obs` stands | {g['n']} | {g['shift_east_m']:+.2f} / {g['shift_south_m']:+.2f} | {g['rms_cross_before']:.1f} → {g['rms_cross_after']:.1f} |")
        for im, v in sorted(res['registration']['per_image'].get(key, {}).items()):
            L.append(f"| {lab} | {im} | {v['n']} | {v['shift_east_m']:+.1f} / {v['shift_south_m']:+.1f} | {v['rms_before']:.1f} → {v['rms_after']:.1f} |")
    L.append('<!--END:registration-->')
    # orphans
    L.append('<!--BEGIN:orphans-->')
    L.append('| source | zone | n | names (⟨…⟩ = also a secondary candidate of our stand …; cat = X-Plane ICAO size) |'); L.append('|---|---|---|---|')
    for key, lab in (('osm', 'OSM'), ('xp', 'X-Plane')):
        from collections import defaultdict
        g = defaultdict(list)
        for q in res['orphans'][key]:
            t = q['label'] or '(no ref)'
            if key == 'xp' and q.get('cat'): t += f" [{q['cat']}]"
            if q['alt_of']: t += ' ⟨' + '/'.join(q['alt_of']) + '⟩'
            g[q['zone']].append(t)
        for z in sorted(g):
            items = g[z]; c = Counter(items)
            txt = ', '.join(f'{k} ×{n}' if n > 1 else k for k, n in sorted(c.items(), key=lambda t: nkey(t[0]) if t[0][0].isalpha() and t[0][0] in 'ABCDEFG' and len(t[0]) > 1 and t[0][1].isdigit() else ('~', 0, t[0])))
            L.append(f'| {lab} | {z} | {len(items)} | {txt} |')
    L.append('<!--END:orphans-->')
    # names by area
    L.append('<!--BEGIN:names_table-->')
    L.append('| Area | SFO stands in use (AODB ∪ DataSF, via gate_truth) | ours: own stands | ours: only as alias | OSM refs | X-Plane names | in SFO use but no own stand of ours | X-Plane names not in SFO\'s maps |')
    L.append('|---|---|---|---|---|---|---|---|')
    for a, n in res['names'].items():
        alias_only = sorted(set(n['ours_incl_alias']) - set(n['ours_own']), key=nkey)
        miss = sorted(set(n['sfo_used']) - set(n['ours_own']), key=nkey)
        xp_bad = sorted(set(n['xp']) - set(n['sfo_map']), key=nkey) if n['sfo_map'] else []
        L.append(f"| {a} | {' '.join(n['sfo_used'])} | {' '.join(n['ours_own'])} | {' '.join(alias_only) or '—'} | {' '.join(n['osm'])} | {' '.join(n['xp'])} | {' '.join(miss) or '—'} | {' '.join(xp_bad) or '—'} |")
    L.append('<!--END:names_table-->')
    open(os.path.join(OUT, 'tables_stands.md'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
