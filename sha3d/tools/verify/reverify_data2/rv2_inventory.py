"""Inventory of what the filter drops, derived independently of pin_extract.py. Prints counts only.
usage: python3 -I rv2_inventory.py            (SHA3D_DIR env var optional)
1. tag-rule drops from the raw tiles, by class and geometry kind, and how many intersect the extent;
2. second-order drops: raw tagged nodes / ways / multipolygons that intersect the extent, pass the tag rule and are
   missing from the pinned extract, by feature class;
3. compares the totals with pin_summary.json.
The per-element list (ids, classes, sizes) goes to the local log refs/cache/reverify_data2/inventory_local.json only.
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv2_common as C  # noqa: E402

raw = C.Raw()
feats, els, ext = C.load_pinned()
pinned = {(f['typ'], f['id']) for f in feats}
dg = C.raw_dg = raw.dropped_geoms()

c1 = Counter()
local = {'tag_rule': [], 'second_order': []}
for d in dg:
    inx = d['geom'].intersects(ext)
    c1[(d['typ'], d['cls'], d['kind'], 'in extent' if inx else 'outside')] += 1
    g = d['geom'].intersection(ext) if inx else None
    local['tag_rule'].append(dict(typ=d['typ'], id=d['id'], cls=d['cls'], kind=d['kind'], in_extent=inx,
                                  length_in=round(g.length, 1) if g is not None and d['kind'] == 'line' else None,
                                  area_in=round(g.area, 1) if g is not None and d['kind'] == 'area' else None,
                                  tags=raw.NT.get(d['id']) if d['typ'] == 'node' else raw.WT.get(d['id']) if d['typ'] == 'way' else raw.RT.get(d['id'])))
no_geom = sum(1 for k in raw.drop if not any(d['typ'] == k[0] and d['id'] == k[1] for d in dg))
print('1. tag-rule drops (raw tiles): %d elements, %d without geometry' % (len(raw.drop), no_geom))
for k, v in sorted(c1.items()):
    print('   %-9s %-14s %-6s %-9s %d' % (k + (v,)))
print('   in extent: %d areas, %d lines, %d points' % tuple(
    sum(1 for d in dg if d['kind'] == kind and d['geom'].intersects(ext)) for kind in ('area', 'line', 'point')))

c2 = Counter()
for i, t in raw.NT.items():
    if not t or ('node', i) in raw.drop or ('node', i) in pinned:
        continue
    p = C.Point(raw.xz[i])
    if p.intersects(ext):
        c2[('node', C.cls(t))] += 1
        local['second_order'].append(dict(typ='node', id=i, cls=C.cls(t), tags=t))
for i, t in raw.WT.items():
    if not t or ('way', i) in raw.drop or ('way', i) in pinned:
        continue
    g = raw.way_geom(i)
    if g is not None and g.intersects(ext):
        c2[('way', C.cls(t))] += 1
        local['second_order'].append(dict(typ='way', id=i, cls=C.cls(t), tags=t,
                                          length=round(g.length, 1)))
mp_missing = 0
for i, t in raw.RT.items():
    if t.get('type') != 'multipolygon' or ('relation', i) in raw.drop or ('relation', i) in pinned:
        continue
    g = raw.rel_geom(i)
    if g is not None and not g.is_empty and g.intersects(ext):
        mp_missing += 1
        c2[('relation', C.cls(t))] += 1
        local['second_order'].append(dict(typ='relation', id=i, cls=C.cls(t), tags=t))
print('2. second-order drops (in extent, pass the tag rule, missing from the pinned extract): %d' % sum(c2.values()))
for k, v in sorted(c2.items()):
    print('   %-9s %-40s %d' % (k + (v,)))
summ = json.load(open(os.path.join(C.PIN, 'pin_summary.json')))
ds = summ['dropped_sensitive']
second = sum(v for k, v in ds.items() if k.split(':')[1] not in ('police', 'military', 'armed_police', 'prison', 'gnss')
             and not k.split(':')[1].endswith('_member'))
print('3. pin_summary second-order total %d; mine %d -> %s' % (second, sum(c2.values()),
                                                                 'match' if second == sum(c2.values()) else 'DIFFER'))
C.save_local('inventory_local.json', local)
