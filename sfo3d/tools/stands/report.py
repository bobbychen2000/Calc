"""Regenerate the generated tables of docs/research/stands_rebuild.md (between <!--BEGIN:x--> / <!--END:x--> markers)
from refs/cache/stands/stands_built.json (written by build_stands.py) and data/sfo_stands.json.
Usage: python3 tools/stands/report.py"""
import json, os, re
from collections import Counter
import numpy as np
from common import ROOT, WORK

DOC = os.path.join(ROOT, 'docs', 'research', 'stands_rebuild.md')


def tables():
    B = json.load(open(os.path.join(WORK, 'stands_built.json')))
    D = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    S = B['stands']; out = {}
    vb = Counter('+'.join(s['verified_by']) or 'OSM only' for s in S)
    ps = Counter(s['pos_src'] for s in S)
    na = [s['naip'] for s in S if s.get('naip')]; ad = [s['adsb'] for s in S if s.get('adsb')]
    L = ['| quantity | value |', '|---|---|',
         '| contact stands | %d (%d stands + %d alternative positions: %s) |' % (len(S), sum(1 for s in S if not s.get('alt_of')), sum(1 for s in S if s.get('alt_of')), ', '.join(s['name'] for s in S if s.get('alt_of'))),
         '| position source (pos_src) | %s |' % ', '.join('%s %d' % kv for kv in ps.most_common()),
         '| name source (name_src) | sfo %d |' % len(S),
         '| verified_by | %s |' % ', '.join('%s %d' % kv for kv in vb.most_common()),
         '| src (legacy field) | obs %d, inf %d |' % (sum(s['src'] == 'obs' for s in S), sum(s['src'] == 'inf' for s in S)),
         '| classes | %s |' % ', '.join('%s %d' % kv for kv in sorted(Counter(s['cls'] for s in S).items())),
         '| jet bridges | %d OSM bridges: %d main-deck bridges on %d stands (1: %d, 2: %d), %d upper-deck (`bridges_upper`: %s); no bridge of its own: %s |' % (
             len({b['osm_id'] for s in D['stands'] for b in s['bridges'] + s['bridges_upper']}), sum(len(s['bridges']) for s in D['stands']),
             sum(1 for s in D['stands'] if s['bridges']), *[sum(1 for s in D['stands'] if len(s['bridges']) == k) for k in (1, 2)],
             sum(len(s['bridges_upper']) for s in D['stands']), ', '.join(s['name'] for s in D['stands'] if s['bridges_upper']),
             ', '.join(s['name'] + (' (uses %s)' % s['shares_bridges_of'] if s.get('shares_bridges_of') else '') for s in D['stands'] if not s['bridges']) or '-'),
         '| mutually exclusive pairs | %d |' % (sum(len(s['excl']) for s in D['stands']) // 2),
         '| remote stands (SFO names, ADS-B) | %d: %s |' % (len(D['remote']), ', '.join(r['name'] for r in D['remote'])),
         '| unnamed OSM parking positions (`positions`) | %s |' % ', '.join('%s %d' % kv for kv in Counter(p['zone'] for p in D['positions']).most_common()),
         '| red boxes (NAIP) | %d |' % len(D['redBoxes'])]
    pf = [s.get('paint_after') or s.get('paint') for s in S]; pf = [p for p in pf if p and p['n'] >= 8 and p['rms'] <= 0.3]
    if pf:
        L += ['| painted lead-in vs model axis (NAIP yellow-line fit, 3-22 m behind the nose, clean fits), %d stands | lateral at the nose: median |r| %.2f m, max %.2f m; heading: median |dh| %.2f deg, max %.2f deg; corrected: %s |' % (
            len(pf), np.median([abs(p['lat_nose']) for p in pf]), max(abs(p['lat_nose']) for p in pf), np.median([abs(p['dh']) for p in pf]), max(abs(p['dh']) for p in pf),
            ', '.join('%s (%+.1f m, %+.1f deg)' % (s['disp'], s['paint']['lat_nose'], s['paint']['dh']) for s in S if (s.get('paint') or {}).get('applied')) or '-')]
    if na:
        L += ['| NAIP parked-aircraft reading (by eye, +-1.5 m along / +-0.7 m lateral; lateral 0.0 = within the reading resolution, not a measured zero), %d stands | lateral: median |r| %.1f m, max |r| %.1f m; along: median %.1f m, median |r| %.1f m |' % (
            len(na), np.median([abs(n['resid_lat']) for n in na]), max(abs(n['resid_lat']) for n in na),
            np.median([n['resid_along'] for n in na]), np.median([abs(n['resid_along']) for n in na]))]
    if ad:
        L += ['| ADS-B residual (antenna median in the stand frame), %d stands / %d aircraft | lateral: median |r| %.1f m, max |r| %.1f m; along (antenna behind the nose): median %.1f m, range %.1f..%.1f m; heading: median |dh| %.1f deg |' % (
            len(ad), sum(a['n_aircraft'] for a in ad), np.median([abs(a['lat_med']) for a in ad]), max(abs(a['lat_med']) for a in ad),
            np.median([a['along_med'] for a in ad]), min(a['along_med'] for a in ad), max(a['along_med'] for a in ad),
            np.median([abs(a['dhdg_med']) for a in ad if a['dhdg_med'] is not None]))]
    out['summary'] = '\n'.join(L)
    T = ['| stand | gate | AODB | cls (largest type) | pos_src | verified_by | NAIP resid along/lat m | ADS-B n, along/lat m, dhdg | paint lat m / dh deg | bridges | excl / alt_of / tight | name / position evidence |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    Dn = {s['name']: s for s in D['stands']}
    for s in S:
        d = Dn[s['disp']]; n = s.get('naip'); a = s.get('adsb'); pa = s.get('paint_after') or s.get('paint')
        T.append('| %s | %s | %s | %s (%s)%s%s | %s | %s | %s | %s | %s | %d | %s | %s |' % (
            s['disp'], s['gate'], ' '.join(s['aodb']) or '-', s['cls'], s['largest_type'] or '-', ' span_max %.1f' % s['span_max'] if s.get('span_max') else '',
            ' len_max %.1f' % s['len_max'] if s.get('len_max') else '',
            s['pos_src'], '+'.join(s['verified_by']) or '-',
            '%+.1f / %+.1f%s' % (n['resid_along'], n['resid_lat'], ' (u)' if 'u' in n['flags'] else '') if n else '-',
            '%d, %+.1f / %+.1f, %s' % (a['n_aircraft'], a['along_med'], a['lat_med'], '-' if a['dhdg_med'] is None else '%+.0f' % a['dhdg_med']) if a else '-',
            ('%+.2f / %+.2f%s' % (pa['lat_nose'], pa['dh'], '' if pa['n'] >= 8 and pa['rms'] <= 0.3 else ' (noisy)')) if pa else '-',
            len(d['bridges']) + len(d['bridges_upper']), (' '.join(d['excl']) + (' alt of ' + d['alt_of'] if d.get('alt_of') else '') + (' tight ' + ' '.join(d['tight_with']) if d.get('tight_with') else '')).strip() or '-',
            s['why'].replace('|', '/')))
    out['stands'] = '\n'.join(T)
    R = ['| remote stand | position | pos_src | ADS-B aircraft | OSM residual |', '|---|---|---|---|---|']
    for r in B['remote']:
        R.append('| %s | (%.1f, %.1f) hdg %s | %s | %s | %s |' % (r['name'], r['x'], r['z'], r.get('hdg'), r['pos_src'], '; '.join(r['adsb']['aircraft']),
                                                            '%.1f m' % r['osm_resid_m'] if r.get('osm_resid_m') is not None else r.get('note', '-')))
    out['remote'] = '\n'.join(R)
    P = ['| pair | clearance m (envelope of all accepted types, final limits) | ICAO | SFO plans both at once (overlaps) | handled |', '|---|---|---|---|---|']
    dn = {s['name']: s['disp'] for s in S}
    for p in sorted(B['pairs'], key=lambda p: p[2]):
        a, b, d, need, sim, alt = p[:6]
        if d >= need: continue
        how = p[6] if len(p) > 6 and p[6] else ('kept (below ICAO, above 3 m)' if d >= 3 else 'excl')
        P.append('| %s / %s | %.1f | %.1f | %d | %s |' % (dn.get(a, a), dn.get(b, b), d, need, sim, how))
    out['pairs'] = '\n'.join(P)
    return out


def main():
    doc = open(DOC).read()
    for k, v in tables().items():
        doc = re.sub(r'(<!--BEGIN:%s-->).*?(<!--END:%s-->)' % (k, k), lambda m: m.group(1) + '\n' + v + '\n' + m.group(2), doc, flags=re.S)
    open(DOC, 'w').write(doc)
    print('updated', DOC)


if __name__ == '__main__':
    main()
