"""AIP class comparison with the reference-span mapping (counts only), and real building clearances."""
import sys, os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_stands.py')).read().split('# buildings clearance')[0].replace("for mode in ('ref', 'max_spanmax', 'max_raw'):", "for mode in ('max_spanmax',):"))
bl = [Polygon(b['ring']) for b in A['buildings']] + [Polygon(b['ring']) for b in A['context']['buildings'] if len(b.get('ring') or []) >= 4]
btree = STRtree(bl)
near = []
for n in names:
    d = min([PM[n].distance(bl[j]) for j in btree.query(PM[n].buffer(3.0))] or [99])
    if d < 3.0: near.append((n, round(d, 2)))
print('class-max (span_max) planforms within 3 m of an OSM building: %d %s' % (len(near), near[:10]))
AS = json.load(open(os.path.join(ROOT, 'refs/cache/aip/derived_aip_zsss/stands.json'))); W = AS['wingspan_limit_m']
REF = {c: ST['class_ref'][c]['span_m'] for c in ORDER}
def aipc(x):
    m = re.findall(r'[\d.]+', str(x));
    if not m: return None
    v = float(m[-1]); strict = '＜' in str(x) or '<' in str(x); best = None
    for c in ORDER:
        if (REF[c] < v) if strict else (REF[c] <= v): best = c
    return best
c = Counter(); area = defaultdict(Counter); over2 = []
for s in stands:
    if s['name'] not in W: continue
    a = aipc(W[s['name']]); d = ORDER.index(s['cls']) - ORDER.index(a)
    c['exact' if d == 0 else 'within one' if abs(d) == 1 else 'off by 2+'] += 1
    c['above' if d > 0 else 'below' if d < 0 else 'same'] += 1
    area[s['area']]['above' if d > 0 else 'below' if d < 0 else 'same'] += 1
    if d >= 2: over2.append(s['name'])
    wu = ORDER.index(s['cls']) >= 3; wa = ORDER.index(a) >= 3
    c['wide/narrow agree' if wu == wa else 'we wide, AIP narrow' if wu else 'we narrow, AIP wide'] += 1
    v = float(re.findall(r'[\d.]+', str(W[s['name']]))[-1]); strict = '＜' in str(W[s['name']])
    if s['span_max'] > v or (strict and s['span_max'] >= v): c['span_max >= AIP limit'] += 1
print('vs AIP (mirror), reference-span mapping, local counts:', dict(c))
for k, v in area.items(): print('   ', k, dict(v))
print('2+ classes above the AIP: %d (%s)' % (len(over2), 'names not printed'))
