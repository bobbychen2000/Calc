#!/usr/bin/env python3
"""Derive airfield detail features from the SFO Museum geometry (data/sfo_airport.json) for the live 3D app.

Outputs data/sfo_details.json (+ debug PNGs in out/details/):
  apron          ramp pavement polygons: closing of terminal complex + taxiways + remote stands, limited to the
                 terminal surroundings (SFO Museum data has no apron features; this is an inferred outline)
  centerlines    taxiway centerline polylines (skeleton of the taxiway polygons, spurs pruned, smoothed)
  holds          runway holding positions where a taxiway centerline enters a runway's hold zone
                 (FAA standard distance; the exact SFO hold-line distances are not in the source data)
  edges          taxiway edge polylines where the taxiway borders unpaved ground
  masts          apron floodlight mast positions (typical spacing along the ramp boundary)
  roads          ramp service-road lines offset from the terminal face
World frame (matches js/geo.js): x = east, z = south (m), origin = ARP; projection/datum from tools/geo_frame.py
(exact GRS80 local tangent plane, NAD83(2011)). The ADS-B snapshot (WGS 84) goes through geo_frame.wgs84_to_world.
Also writes data/sfo_details.js (the same JSON as an ES module).
"""
import json, math, os, sys
import numpy as np, cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import geo_frame
D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
X0, Z0, X1, Z1, RES = -2800.0, -2450.0, 2050.0, 1900.0, 1.0
W, H = int((X1 - X0) / RES), int((Z1 - Z0) / RES)
FT = 0.3048
HOLD_DIST = 280 * FT        # m from runway centreline (FAA standard value used for large aircraft)
os.makedirs(os.path.join(ROOT, 'out', 'details'), exist_ok=True)

def px(pts): return np.array([[(x - X0) / RES, (z - Z0) / RES] for x, z in pts], np.float64)
def world(p): return [round(float(X0 + p[0] * RES), 2), round(float(Z0 + p[1] * RES), 2)]
def fillpolys(mask, polys, holes=True):
    for poly in polys:
        cv2.fillPoly(mask, [np.round(px(poly[0]) * 16).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=4)
        if holes:
            for h in poly[1:]: cv2.fillPoly(mask, [np.round(px(h) * 16).astype(np.int32)], 0, lineType=cv2.LINE_8, shift=4)
    return mask
def newmask(): return np.zeros((H, W), np.uint8)

# ---------------------------------------------------------------- base masks
TW = newmask()
for t in D['taxiways']: fillpolys(TW, t['polys'], holes=False)
RW = newmask()
for r in D['runways']: fillpolys(RW, r['polys'], holes=False)
TC = newmask(); fillpolys(TC, [[p[0]] for p in D['terminalComplex']], holes=False)   # building incl. courtyards
BLD = newmask()
for s in D['structures']:
    if s['kind'] in ('garage', 'building', 'hangar', 'hotel', 'atc'): fillpolys(BLD, s['polys'], holes=False)
REM = newmask()
for g in D['gates']:
    if g.get('dup'): continue
    if g['level'] != 2 or g.get('variant'):
        cv2.circle(REM, (int((g['x'] - X0) / RES), int((g['z'] - Z0) / RES)), int(38 / RES), 1, -1)
print('masks', W, H, 'tw', TW.sum(), 'rw', RW.sum(), 'tc', TC.sum())

def dist_to(mask):  # distance (m) from every pixel to the mask
    return ndi.distance_transform_edt(mask == 0) * RES

# ---------------------------------------------------------------- apron (inferred ramp)
A0 = ((TC | TW | RW | REM) > 0).astype(np.uint8)
dA = dist_to(A0); R = 150.0
dil = (dA <= R).astype(np.uint8)
closed = (dist_to(1 - dil) > R).astype(np.uint8)          # morphological closing by a 150 m disc
dT = dist_to(TC)
apron = ((closed == 1) & (A0 == 0) & (dT <= 420)).astype(np.uint8)
apron |= ((dT <= 45) & (TC == 0) & (BLD == 0)).astype(np.uint8)                   # ramp directly around the building
apron &= (1 - BLD)
# keep only pieces touching the terminal ramp or remote stands (drop isolated infield slivers)
lab, n = ndi.label(apron | REM)
keep = set(np.unique(lab[(dT <= 60) | (REM > 0)])) - {0}
apron = np.isin(lab, list(keep)).astype(np.uint8) & (1 - TC)
apron = ndi.binary_opening(apron, iterations=3).astype(np.uint8)
PAVED = ((apron | TW | RW | REM) > 0).astype(np.uint8)
print('apron px', apron.sum())

def contours(mask, tol):
    cs, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    if hier is None: return polys
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1: continue  # outer contours only; holes attached below
        if cv2.contourArea(c) < 400: continue
        rings = [c]
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) > 200: rings.append(cs[j])
            j = hier[j][0]
        out = []
        for r in rings:
            a = cv2.approxPolyDP(r, tol / RES, True)[:, 0, :]
            out.append([world((p[0] + 0.5, p[1] + 0.5)) for p in a])
        polys.append(out)
    return polys
apron_polys = contours(apron, 1.2)

# ---------------------------------------------------------------- taxiway centrelines
tw_only = ((TW > 0) & (RW == 0)).astype(np.uint8)
tw_only = ndi.binary_closing(tw_only, iterations=2).astype(np.uint8)
sk = skeletonize(tw_only > 0).astype(np.uint8)
K = np.array([[1, 1, 1], [1, 10, 1], [1, 1, 1]])
def neighbours(img): return ndi.convolve(img, K, mode='constant') - 10
def prune(sk, maxlen, rounds=4):
    for _ in range(rounds):
        nb = neighbours(sk) * sk
        ends = np.argwhere((sk == 1) & (nb == 1))
        removed = 0
        for (y, x) in ends:
            path = [(y, x)]; py, px_ = y, x; prev = None
            while True:
                nxt = [(py + dy, px_ + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and 0 <= py + dy < H and 0 <= px_ + dx < W and sk[py + dy, px_ + dx] and (py + dy, px_ + dx) != prev and (py + dy, px_ + dx) not in path]
                if len(nxt) != 1 or len(path) > maxlen: break
                prev = (py, px_); py, px_ = nxt[0]; path.append((py, px_))
                if (neighbours_at(sk, py, px_) >= 3): break
            if len(path) <= maxlen and neighbours_at(sk, path[-1][0], path[-1][1]) >= 3:
                for (yy, xx) in path[:-1]: sk[yy, xx] = 0
                removed += 1
        if not removed: break
    return sk
def neighbours_at(img, y, x):
    y0, y1, x0, x1 = max(0, y - 1), min(H, y + 2), max(0, x - 1), min(W, x + 2)
    return int(img[y0:y1, x0:x1].sum()) - int(img[y, x])
sk = prune(sk, int(35 / RES))
# trace skeleton into polylines between junctions / ends
nb = neighbours(sk) * sk
node = (sk == 1) & ((nb == 1) | (nb >= 3))
visited = np.zeros_like(sk)
lines = []
def trace(y, x, dy, dx):
    path = [(y, x), (y + dy, x + dx)]; visited[y + dy, x + dx] = 1
    cy, cx = y + dy, x + dx; prev = (y, x)
    while not node[cy, cx]:
        nxt = None
        for oy in (-1, 0, 1):
            for ox in (-1, 0, 1):
                if not (oy or ox): continue
                ny, nx = cy + oy, cx + ox
                if 0 <= ny < H and 0 <= nx < W and sk[ny, nx] and (ny, nx) != prev and (ny, nx) != path[-2] and not (visited[ny, nx] and not node[ny, nx]):
                    if nxt is None or (abs(oy) + abs(ox) < abs(nxt[0] - cy) + abs(nxt[1] - cx)): nxt = (ny, nx)
        if nxt is None: break
        prev = (cy, cx); cy, cx = nxt; path.append((cy, cx))
        if not node[cy, cx]: visited[cy, cx] = 1
        if len(path) > 20000: break
    return path
for (y, x) in np.argwhere(node):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if not (dy or dx): continue
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and sk[ny, nx] and not visited[ny, nx] and not node[ny, nx]:
                lines.append(trace(y, x, dy, dx))
            elif 0 <= ny < H and 0 <= nx < W and node[ny, nx] and (y, x) < (ny, nx):
                lines.append([(y, x), (ny, nx)])
def chaikin(pts, it=2):
    for _ in range(it):
        if len(pts) < 3: return pts
        out = [pts[0]]
        for i in range(len(pts) - 1):
            p, q = np.array(pts[i]), np.array(pts[i + 1])
            out += [tuple(0.75 * p + 0.25 * q), tuple(0.25 * p + 0.75 * q)]
        out.append(pts[-1]); pts = out
    return pts
centerlines = []
for L in lines:
    if len(L) < 3: continue
    c = np.array([[p[1], p[0]] for p in L], np.float32).reshape(-1, 1, 2)
    a = cv2.approxPolyDP(c, 0.6 / RES, False)[:, 0, :]
    pts = chaikin([tuple(p) for p in a], 2)
    wl = [world((p[0] + 0.5, p[1] + 0.5)) for p in pts]
    length = sum(math.dist(wl[i], wl[i + 1]) for i in range(len(wl) - 1))
    if length < 6: continue
    centerlines.append(wl)
print('centerlines', len(centerlines), 'total km', round(sum(sum(math.dist(l[i], l[i + 1]) for i in range(len(l) - 1)) for l in centerlines) / 1000, 1))

# ---------------------------------------------------------------- runways (surveyed ends; same as js/geo.js)
ENDS = {k: (v['lat'], v['lon']) for k, v in geo_frame.RWY_ENDS.items()}   # FAA NASR (NAD83) = js/geo.js RWY_ENDS
ll2w = geo_frame.ll_to_world                  # NAD83(2011) lat/lon -> world (x, z)
RWYS = []
for a, b in (('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')):
    pa, pb = np.array(ll2w(*ENDS[a])), np.array(ll2w(*ENDS[b])); L = np.linalg.norm(pb - pa); d = (pb - pa) / L
    RWYS.append({'a': a, 'b': b, 'pa': pa, 'pb': pb, 'dir': d, 'len': L})
def rw_frame(R, p):
    v = np.array(p) - R['pa']; return float(v @ R['dir']), float(-v[0] * R['dir'][1] + v[1] * R['dir'][0])  # along, cross (right of a->b positive)

# ---------------------------------------------------------------- holding positions
holds = []
def extent(p, n, maxd=45):  # march across pavement from p along +-n
    res = []
    for sg in (1, -1):
        d = 0
        while d < maxd:
            q = p + n * sg * (d + 0.5); ix, iy = int((q[0] - X0) / RES), int((q[1] - Z0) / RES)
            if not (0 <= ix < W and 0 <= iy < H) or not (TW[iy, ix] or apron[iy, ix]): break
            d += 0.5
        res.append(d)
    return res
for cl in centerlines:
    P = np.array(cl)
    for R in RWYS:
        prev = None
        for i in range(len(P)):
            al, cr = rw_frame(R, P[i])
            inside = -150 < al < R['len'] + 150
            cur = abs(cr) if inside else None
            if prev is not None and cur is not None and (prev[1] - HOLD_DIST) * (cur - HOLD_DIST) < 0:
                j = i; a0, c0 = prev[1], cur; t = (HOLD_DIST - a0) / (c0 - a0)
                q = P[j - 1] + (P[j] - P[j - 1]) * t
                tang = P[j] - P[j - 1]; tang = tang / (np.linalg.norm(tang) + 1e-9)
                cross_dir = np.array([-R['dir'][1], R['dir'][0]])
                if abs(tang @ R['dir']) > 0.87: prev = (i, cur); continue   # running parallel to the runway, not entering it
                toward = -np.sign(rw_frame(R, q)[1]) * cross_dir         # unit vector from hold point toward the runway centreline
                if tang @ toward < 0: tang = -tang
                n = np.array([-tang[1], tang[0]])
                e1, e2 = extent(q, n)
                if e1 + e2 < 12: prev = (i, cur); continue
                a_pt, b_pt = q + n * e1, q - n * e2
                # sign text: runway end on the pilot's left first (pilot faces the runway)
                left = np.array([tang[1], -tang[0]])      # left of travel direction in (x east, z south)
                s_left = R['dir'] @ left; name_left, name_right = (R['b'], R['a']) if s_left > 0 else (R['a'], R['b'])  # end lying to the pilot's left first
                # taxiway name at the hold point
                tname = None
                for t in D['taxiways']:
                    for poly in t['polys']:
                        if cv2.pointPolygonTest(px(poly[0]).astype(np.float32).reshape(-1, 1, 2), ((q[0] - X0) / RES, (q[1] - Z0) / RES), False) >= 0:
                            tname = t['name'].replace('Taxiway ', ''); break
                    if tname: break
                holds.append({'p': [round(q[0], 2), round(q[1], 2)], 'a': [round(a_pt[0], 2), round(a_pt[1], 2)], 'b': [round(b_pt[0], 2), round(b_pt[1], 2)],
                              'dir': [round(tang[0], 4), round(tang[1], 4)], 'rwy': R['a'] + '/' + R['b'], 'text': f'{name_left}-{name_right}', 'twy': tname, 'w': round(e1 + e2, 1)})
            prev = (i, cur) if cur is not None else None
# de-duplicate (two centerline pieces can cross the same hold zone)
uniq = []
for h in holds:
    if all(math.dist(h['p'], u['p']) > 18 for u in uniq): uniq.append(h)
holds = uniq
print('holds', len(holds))

# ---------------------------------------------------------------- taxiway edges bordering unpaved ground
edges = []
for t in D['taxiways']:
    for poly in t['polys']:
        for ring in poly:
            run = []
            n = len(ring)
            for i in range(n):
                a, b = np.array(ring[i]), np.array(ring[(i + 1) % n]); L = np.linalg.norm(b - a)
                if L < 0.5: continue
                d = (b - a) / L; nrm = np.array([-d[1], d[0]])
                steps = max(1, int(L / 2.0))
                for k in range(steps + 1):
                    p = a + d * L * k / steps
                    def paved_at(q):
                        ix, iy = int((q[0] - X0) / RES), int((q[1] - Z0) / RES)
                        return 0 <= ix < W and 0 <= iy < H and PAVED[iy, ix] > 0
                    s1, s2 = paved_at(p + nrm * 2.5), paved_at(p - nrm * 2.5)
                    if s1 != s2:
                        inward = nrm if s1 else -nrm
                        run.append([round(float((p + inward * 0.9)[0]), 2), round(float((p + inward * 0.9)[1]), 2)])
                    else:
                        if len(run) > 3: edges.append(run)
                        run = []
            if len(run) > 3: edges.append(run)
# simplify
def simplify(pl, tol):
    c = np.array(pl, np.float32).reshape(-1, 1, 2); a = cv2.approxPolyDP(c, tol, False)[:, 0, :]; return [[round(float(p[0]), 2), round(float(p[1]), 2)] for p in a]
edges = [simplify(e, 0.35) for e in edges if sum(math.dist(e[i], e[i + 1]) for i in range(len(e) - 1)) > 15]
print('edge runs', len(edges))

# ---------------------------------------------------------------- floodlight masts (typical ~120 m spacing along the ramp)
ramp = ((apron | REM) > 0).astype(np.uint8)
inner = (dist_to(1 - ramp) >= 9).astype(np.uint8)
cs, _ = cv2.findContours(inner, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
masts = []
dTW = dist_to(TW | RW)
for c in cs:
    c = c[:, 0, :]
    if len(c) < 60: continue
    acc = 0.0
    for i in range(1, len(c)):
        acc += math.dist(c[i], c[i - 1]) * RES
        if acc >= 120:
            x, y = c[i]
            if dTW[y, x] > 25 and dT[y, x] > 25 and all(math.dist((X0 + x * RES, Z0 + y * RES), m) > 70 for m in masts):
                masts.append([round(X0 + x * RES, 1), round(Z0 + y * RES, 1)]); acc = 0
print('masts', len(masts))

# ---------------------------------------------------------------- service road lines along the terminal face
roads = []
for off in (7.0, 14.5):
    band = ((dT <= off) & (TC == 0)).astype(np.uint8)
    cs, _ = cv2.findContours(band | TC, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs:
        c = c[:, 0, :]; run = []
        for p in c:
            x, y = p
            ok = apron[min(H - 1, y), min(W - 1, x)] and dTW[y, x] > 6
            if ok: run.append(world((x + 0.5, y + 0.5)))
            else:
                if len(run) > 25: roads.append({'off': off, 'pts': simplify(run, 0.5)})
                run = []
        if len(run) > 25: roads.append({'off': off, 'pts': simplify(run, 0.5)})
print('road lines', len(roads))

# ---------------------------------------------------------------- pavement patches where aircraft were observed parked off the mapped ramp
snap = json.loads(open(os.path.join(ROOT, 'data', 'snapshot.js')).read().split('SNAPSHOT = ')[1].split(';\nexport')[0])
patches = []
dP = dist_to(PAVED)
for ac in snap['ac']:
    if ac.get('alt_baro') != 'ground' or (ac.get('gs') or 0) > 3: continue
    x, z = geo_frame.wgs84_to_world(ac['lat'], ac['lon']); ix, iy = int((x - X0) / RES), int((z - Z0) / RES)
    if dP[iy, ix] > 0:
        patches.append([round(x, 1), round(z, 1), 45.0])
print('patches', len(patches))
out = {'attribution': 'Derived from SFO Museum sfomuseum-data-architecture (CDLA-Permissive-1.0); apron outline, holding positions, masts and road lines are inferred (see tools/build_airfield_details.py)',
       'frame': geo_frame.FRAME_ID, 'holdDist': HOLD_DIST, 'apron': apron_polys, 'centerlines': centerlines, 'holds': holds, 'edges': edges, 'masts': masts, 'roads': roads, 'patches': patches}
json.dump(out, open(os.path.join(ROOT, 'data', 'sfo_details.json'), 'w'), separators=(',', ':'))
open(os.path.join(ROOT, 'data', 'sfo_details.js'), 'w').write('// Airfield details derived from SFO Museum geometry by tools/build_airfield_details.py\nexport const DETAILS = ' + json.dumps(out, separators=(',', ':')) + ';\n')
print('wrote', os.path.getsize(os.path.join(ROOT, 'data', 'sfo_details.json')) // 1024, 'KB')

# ---------------------------------------------------------------- debug image
img = np.zeros((H, W, 3), np.uint8); img[:] = (40, 70, 40)
img[apron > 0] = (150, 150, 150); img[TW > 0] = (90, 90, 90); img[RW > 0] = (50, 50, 50); img[REM > 0] = (170, 170, 170); img[TC > 0] = (180, 120, 60); img[BLD > 0] = (140, 90, 50)
for l in centerlines: cv2.polylines(img, [np.round(px(l)).astype(np.int32)], False, (0, 220, 255), 1)
for e in edges: cv2.polylines(img, [np.round(px(e)).astype(np.int32)], False, (0, 160, 255), 1)
for h in holds: cv2.line(img, tuple(np.round(px([h['a']])[0]).astype(int)), tuple(np.round(px([h['b']])[0]).astype(int)), (0, 0, 255), 3)
for m in masts: cv2.circle(img, tuple(np.round(px([m])[0]).astype(int)), 5, (255, 255, 255), -1)
for r in roads: cv2.polylines(img, [np.round(px(r['pts'])).astype(np.int32)], False, (255, 255, 255), 1)
snap = json.loads(open(os.path.join(ROOT, 'data', 'snapshot.js')).read().split('SNAPSHOT = ')[1].split(';\nexport')[0])
for a in snap['ac']:
    if a.get('alt_baro') != 'ground': continue
    x, z = ll2w(a['lat'], a['lon'])
    col = (0, 255, 0) if PAVED[int((z - Z0) / RES), int((x - X0) / RES)] else (255, 0, 255)
    cv2.circle(img, (int((x - X0) / RES), int((z - Z0) / RES)), 9, col, 2)
cv2.imwrite(os.path.join(ROOT, 'out', 'details', 'airfield.png'), img)
cv2.imwrite(os.path.join(ROOT, 'out', 'details', 'airfield_small.png'), cv2.resize(img, (W // 3, H // 3), interpolation=cv2.INTER_AREA))
