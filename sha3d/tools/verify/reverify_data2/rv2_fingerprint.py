"""Search-key test: can the committable DOCUMENTS plus the pinned extract locate a dropped feature? Prints counts only.
usage: python3 -I rv2_fingerprint.py          (SHA3D_DIR env var optional)
An adversary reads only committable files:
  - the ARP text in data/sha_airport.json (aerodrome.arp_aip, 0.1 min);
  - the radial distances of military-tagged OSM elements from the ARP, parsed at run time from the committed phase-0
    document docs/phase0/verify_licences_law.md (this script does not repeat them);
  - what the phase-1 documents say about the kept features next to a dropped feature.
The search criteria taken from those documents (which kept class to walk along, which kept classes must lie near) are
read from the git-ignored local file refs/cache/reverify_data2/fingerprint_local.json, so that this committable script
does not restate them. Each search walks the boundary of the named kept class in 10 m steps, keeps the points inside
the documented radial band (+- band_km) whose neighbourhood meets the criteria, merges them into clusters (300 m) and
reports: number of clusters, the length they cover, and whether one lies within 300 m of the dropped group (yes / no).
No positions are printed.
"""
import json
import math
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv2_common as C  # noqa: E402
from shapely.geometry import Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

cfg_path = os.path.join(C.LOCAL, 'fingerprint_local.json')
if not os.path.exists(cfg_path):
    sys.exit('no local criteria file %s (git-ignored; see docs/phase1/reverify_data2.md)' % cfg_path)
CFG = json.load(open(cfg_path, encoding='utf-8'))
raw = C.Raw()
feats, els, ext = C.load_pinned()
CN = C.committed_nodes(raw, ext)   # kept ways' vertices as committed (fix round 3: rule g)
dg = [d for d in raw.dropped_geoms() if d['geom'].intersects(ext)]
A = json.load(open(os.path.join(C.ROOT, 'data', 'sha_airport.json')))
m = re.match(r'N(\d+) ([\d.]+) E(\d+) ([\d.]+)', A['aerodrome']['arp_aip']['text'])
arp = Point(C.F.ll_to_world(int(m.group(1)) + float(m.group(2)) / 60, int(m.group(3)) + float(m.group(4)) / 60))
doc = open(os.path.join(C.ROOT, 'docs', 'phase0', 'verify_licences_law.md'), encoding='utf-8').read()


def match(t, sel):
    return all((t.get(k) is not None) if v == '*' else t.get(k) == v for k, v in sel.items())


way_of = defaultdict(list)
for f in feats:
    if f['typ'] == 'way':
        for x in CN.get(f['id'], []):
            way_of[x].append(f['id'])
unexpl = []
for f in feats:
    if f['typ'] != 'way' or 'highway' not in f['tags'] or f['id'] not in CN:
        continue
    nds = CN[f['id']]
    for j in range(1, len(nds) - 1):
        x = nds[j]
        if x not in raw.xz or len(way_of[x]) > 1:
            continue
        a, b, c = raw.xz[nds[j - 1]], raw.xz[x], raw.xz[nds[j + 1]]
        t = abs(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]) - math.atan2(c[1] - b[1], c[0] - b[0]))) % 360
        if min(t, 360 - t) < 2:
            unexpl.append(Point(b))
utree = STRtree(unexpl)


def clusters(pts, link=300):
    cl = []
    for p in pts:
        hit = [c for c in cl if any(p.distance(q) <= link for q in c[-5:])]
        if hit:
            hit[0].append(p)
        else:
            cl.append([p])
    return cl


print('documented radial distances parsed from the committed phase-0 doc:',
      {k: len(re.findall(r'[\d.]+', (re.search(v['doc_regex'], doc) or [None, ''])[1] if re.search(v['doc_regex'], doc) else ''))
       for k, v in CFG.items()})
for name, c in CFG.items():
    target = unary_union([d['geom'] for d in dg if (d['cls'] in c['target_classes'] and d['kind'] == c['target_kind'])])
    mm = re.search(c['doc_regex'], doc)
    dists = [float(x) for x in re.findall(r'[\d.]+', mm.group(1))] if mm else []
    walk = unary_union([f['geom'].boundary if f['geom'].geom_type in ('Polygon', 'MultiPolygon') else f['geom']
                        for f in feats if f['geom'] is not None and match(f['tags'], c['walk_along'])]).intersection(ext)
    samples = []
    for part in getattr(walk, 'geoms', [walk]):
        if part.geom_type == 'LineString':
            n = max(1, int(part.length / 10))
            samples += [part.interpolate((i + 0.5) * part.length / n) for i in range(n)]
    near = []
    for crit in c.get('near', []):
        g = [(f['id'], f['geom']) for f in feats if f['geom'] is not None and match(f['tags'], crit['tags'])
             and (not crit.get('named') or f['tags'].get('name'))]
        near.append((crit, g, STRtree([x for i, x in g]) if g else None))
    band, cand = [], []
    for p in samples:
        d = p.distance(arp) / 1000
        if c['band_mode'] == 'each':
            ok = any(abs(d - x) <= c['band_km'] for x in dists)
        else:
            ok = bool(dists) and min(dists) - c['band_km'] <= d <= max(dists) + c['band_km']
        if not ok:
            continue
        band.append(p)
        good = True
        for crit, g, tree in near:
            ids = {g[j][0] for j in tree.query(p.buffer(crit['within_m'])) if g[j][1].distance(p) <= crit['within_m']} if tree else set()
            if len(ids) < crit['min_distinct']:
                good = False
        if c.get('min_unexplained_vertices'):
            r = c['unexplained_within_m']
            if sum(1 for j in utree.query(p.buffer(r)) if unexpl[j].distance(p) <= r) < c['min_unexplained_vertices']:
                good = False
        if good:
            cand.append(p)
    for label, pts in (('radial band only', band), ('radial band + documented neighbours', cand)):
        cl = clusters(pts)
        hit = any(min(q.distance(target) for q in k) <= 300 for k in cl) if not target.is_empty else False
        print('%s, %s: %.1f of %.1f km pass; %d cluster(s); one within 300 m of the dropped group: %s' % (
            name, label, len(pts) * 10 / 1000, walk.length / 1000, len(cl), 'yes' if hit else 'no'))
