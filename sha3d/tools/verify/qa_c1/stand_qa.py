import sys, json, math, numpy as np
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/airport'); sys.path.insert(0, '.')
import frame as F
from acplan import planform, CLS_REF, CLASS_MAX, ORDER
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from collections import Counter, defaultdict
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json'))
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
gj = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson'))
st = S['stands']; by = {s['name']: s for s in st}
# ---------- 1. nose = OSM node; heading = final lead-in segment (independent from pinned geojson)
pp_nodes = {}
for f in gj['features']:
    p = f['properties']; t = p.get('tags', {})
    if p['@type'] == 'node' and t.get('aeroway') == 'parking_position' and t.get('ref'):
        pp_nodes.setdefault(t['ref'], []).append((p['@id'], f['geometry']['coordinates']))
leadways = [f for f in gj['features'] if f['properties']['@type'] == 'way' and f['properties'].get('tags', {}).get('aeroway') == 'parking_position']
print('OSM parking_position ref nodes', sum(len(v) for v in pp_nodes.values()), 'distinct refs', len(pp_nodes), 'dup refs', [k for k, v in pp_nodes.items() if len(v) > 1], 'lead-in ways', len(leadways))
idx = defaultdict(list)
for f in leadways:
    cs = f['geometry']['coordinates']
    for i, c in enumerate(cs):
        idx[(round(c[0], 7), round(c[1], 7))].append((f, i))
hd = []; nose_err = []; noleadin = []
for s in st:
    cand = pp_nodes.get(s['name'])
    if not cand: print('no OSM node for', s['name']); continue
    nid, (lo, la) = cand[0]
    x, z = F.ll_to_world(la, lo); nose_err.append(math.hypot(x - s['nose'][0], z - s['nose'][1]))
    segs = []
    for f, i in idx.get((round(lo, 7), round(la, 7)), []):
        cs = f['geometry']['coordinates']
        for j in (i - 1, i + 1):
            if 0 <= j < len(cs):
                px, pz = F.ll_to_world(cs[j][1], cs[j][0]); L = math.hypot(x - px, z - pz)
                segs.append((L, F.vec_hdg(x - px, z - pz)))
    if not segs: noleadin.append(s['name']); continue
    # candidate headings: arriving segments; choose the one closest to the data heading, also report the longest
    best = min(segs, key=lambda q: abs((q[1] - s['hdg'] + 180) % 360 - 180))
    longest = max(segs, key=lambda q: q[0])
    d_long = (longest[1] - s['hdg'] + 180) % 360 - 180
    d_best = (best[1] - s['hdg'] + 180) % 360 - 180
    hd.append((s['name'], round(d_best, 2), round(d_long, 2), round(longest[0], 1), len(segs)))
nose_err = np.array(nose_err)
print('nose vs OSM node: max %.3f m' % nose_err.max())
print('stands without a lead-in way touching the node:', noleadin)
hb = np.array([h[1] for h in hd]); hl = np.array([h[2] for h in hd])
print('heading vs best-matching arriving segment: max |d| %.3f deg' % np.abs(hb).max())
print('heading vs LONGEST segment at the node: n |d|>5deg:', [(h[0], h[2], h[3], h[4]) for h in hd if abs(h[2]) > 5])
json.dump(hd, open('stand_hd.json', 'w'))
