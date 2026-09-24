"""Independent tie-breaker for stand names/positions: parked aircraft seen by ADS-B at a stand that SFO itself publishes.

Input: the JSON written by the gate-truth tool (another agent's tool, used read-only):
    python3 tools/live/gatecheck.py check --every 120 --json refs/cache/xcheck/gatecheck_every120.json
  Each row: an aircraft stationary >= 120 s in our 1 Hz ADS-B recording (refs/cache/rec, adsb.fi / adsb.lol), its
  position (x, z in the app frame; lat/lon), true heading when reported, NACp, and SFO's AODB stand allocation covering
  that time (flysfo.com flight-status JSON, `stands[]`) -> `published_stand`; or, when the transponder sent no
  callsign, the allocation(s) at the stand our matcher picked (`occupancy_at_ours`, weaker evidence).
For each such stand name we measure, relative to the aircraft's ADS-B position and axis (+along = ahead of the antenna,
+cross = right), where ours / OSM / X-Plane put a position with that name. The ADS-B point is the GNSS antenna (on the
fuselage centreline, some metres aft of the nose), so `cross` and heading are the robust comparisons; `along` mixes in
the antenna offset.
Writes refs/cache/xcheck/adsb_evidence.json and the table fragment refs/cache/xcheck/tables_adsb.md.
Usage: python3 tools/xcheck/adsb_evidence.py [gatecheck.json]
"""
import json, math, os, re, sys
import xcommon as X

OUT = os.path.join(X.ROOT, 'refs', 'cache', 'xcheck')


def base(n): return re.sub(r'(?<=\d)[A-Z]$', '', n or '')


def main():
    fn = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'gatecheck_every120.json')
    if not os.path.exists(fn):
        print('no gatecheck output at', fn); return
    G = json.load(open(fn))
    S = {s['name']: s for s in X.load_stands()['stands']}
    alias = {a: s['name'] for s in S.values() for a in s['alias']}
    osm = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')))
    xp = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'xplane', 'ksfo_apt_parsed.json')))
    OS = []
    for p in osm['parking_positions']:
        pts = [X.ll_to_world(*q) for q in p['pts']]
        OS.append({'ref': p['ref'], 'ends': [pts[-1], pts[0]], 'id': p['id']})
    XP = [{'name': r['name'], 'p': X.ll_to_world(r['lat'], r['lon']), 'hdg': r['hdg']} for r in xp['ramp_starts']]
    from compare_stands import gate_names
    seen = {}
    for r in G['rows']:
        stand, how = r.get('published_stand'), 'SFO stand window'
        if not stand and r['verdict'] == 'occupancy-type-match':
            occ = {o[0] for o in r.get('occupancy_at_ours') or []}
            if len(occ) == 1: stand, how = occ.pop(), 'occupancy at our stand (no callsign)'
            else: continue
        if not stand or r.get('excluded'): continue
        key = (r['reg'] or r['hex'], stand)
        if key in seen and seen[key]['how'] == 'SFO stand window': continue
        A = (r['x'], r['z']); h = r.get('true_heading')
        f = X.hdg_vec(h) if h is not None else None
        def rel(P):
            dx, dz = P[0] - A[0], P[1] - A[1]
            if f is None: return {'d': round(math.hypot(dx, dz), 1)}
            return {'d': round(math.hypot(dx, dz), 1), 'along': round(dx * f[0] + dz * f[1], 1), 'cross': round(dx * (-f[1]) + dz * f[0], 1)}
        b = base(stand)
        e = {'flight': r['flight'], 'reg': r['reg'], 'type': r['type'], 'utc': r['T'], 'stand': stand, 'how': how,
             'true_heading': h, 'nac_p': r['nac_p'], 'n_pos': r['n_pos'], 'spread': r['spread'], 'lat': r['lat'], 'lon': r['lon']}
        # ours with that name (own name or alias)
        on = b if b in S else alias.get(b)
        if on:
            s = S[on]; e['ours'] = {'name': on, 'as_alias': on != b, **rel(s['nose']),
                                    'dhdg': round(X.hdg_diff(s['hdg'], h), 1) if h is not None else None}
            # the ADS-B point in OUR stand's frame (needs no ADS-B heading): +along = ahead of our nose, +cross = right
            fs = X.hdg_vec(s['hdg']); dx, dz = A[0] - s['nose'][0], A[1] - s['nose'][1]
            e['ours']['adsb_in_our_frame'] = {'along': round(dx * fs[0] + dz * fs[1], 1), 'cross': round(dx * (-fs[1]) + dz * fs[0], 1)}
        # nearest of ours regardless of name
        nn = min(S.values(), key=lambda s: math.dist(s['nose'], A))
        e['ours_nearest'] = {'name': nn['name'], **rel(nn['nose'])}
        # OSM positions with that ref: use the endpoint nearer the aircraft
        cands = [(min(math.dist(q, A) for q in o['ends']), o) for o in OS if base(o['ref']) == b]
        if cands:
            d, o = min(cands, key=lambda t: t[0]); P = min(o['ends'], key=lambda q: math.dist(q, A))
            e['osm'] = {'ref': o['ref'], 'n_same_ref': len(cands), **rel(P)}
        no = min(OS, key=lambda o: min(math.dist(q, A) for q in o['ends']))
        e['osm_nearest'] = {'ref': no['ref'], **rel(min(no['ends'], key=lambda q: math.dist(q, A)))}
        xc = [q for q in XP if b in gate_names(q['name'])]
        if xc:
            q = min(xc, key=lambda q: math.dist(q['p'], A))
            e['xp'] = {'name': q['name'], **rel(q['p']), 'dhdg': round(X.hdg_diff(q['hdg'], h), 1) if h is not None else None}
        qn = min(XP, key=lambda q: math.dist(q['p'], A))
        e['xp_nearest'] = {'name': qn['name'], **rel(qn['p'])}
        seen[key] = e
    ev = sorted(seen.values(), key=lambda e: e['stand'])
    json.dump({'source': os.path.relpath(fn, X.ROOT), 'flysfo': G.get('flysfo'), 'rows': ev}, open(os.path.join(OUT, 'adsb_evidence.json'), 'w'), indent=1)

    def c(v, k='cross'):
        return '—' if not v else (f"{v['d']:.1f} m" + (f" (x {v[k]:+.1f})" if k in v else ''))
    L = ['<!--BEGIN:adsb_table-->',
         '| SFO stand (evidence) | aircraft (reg, type, flight) | ADS-B hdg | ours, same name (in our stand frame; Δhdg = ours − ADS-B) | ours nearest: dist (cross from aircraft axis) | OSM same ref: dist (cross) | OSM nearest | X-Plane same name: dist (cross) | X-Plane nearest |',
         '|---|---|---|---|---|---|---|---|---|']
    for e in ev:
        o = e.get('ours'); on = e['ours_nearest']
        ours = '— (no stand of ours)' if not o else (f"{o['name']}{' (as alias)' if o['as_alias'] else ''}: ADS-B point {o['adsb_in_our_frame']['along']:+.1f} along / "
                                                        f"{o['adsb_in_our_frame']['cross']:+.1f} cross of our stand" + (f", Δhdg {o['dhdg']:+.0f}°" if o.get('dhdg') is not None else ''))
        L.append('| ' + ' | '.join([
            f"{e['stand']} ({'SFO window' if e['how'].startswith('SFO') else 'occupancy'})",
            f"{e['reg']}, {e['type']}, {e['flight'] or '—'}",
            '—' if e['true_heading'] is None else f"{e['true_heading']:.0f}°",
            ours, f"{on['name']} {c(on)}",
            ('— (no such ref)' if 'osm' not in e else f"{e['osm']['ref']}: {c(e['osm'])}" + (f" [{e['osm']['n_same_ref']} ways]" if e['osm']['n_same_ref'] > 1 else '')),
            f"{e['osm_nearest']['ref'] or '(no ref)'} {c(e['osm_nearest'])}",
            ('— (no such name)' if 'xp' not in e else f"{e['xp']['name']}: {c(e['xp'])}"),
            f"{e['xp_nearest']['name']} {c(e['xp_nearest'])}"]) + ' |')
    L.append('<!--END:adsb_table-->')
    open(os.path.join(OUT, 'tables_adsb.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
