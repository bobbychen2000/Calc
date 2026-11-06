#!/usr/bin/env python3
"""Where FAA airport diagram AL-375 (SFO), cycle 2611, shows NO pavement along the deleted west end of the old taxiway J
-> refs/cache/faa/al375_2611_oldJ.json (own output; the chart is a US Government work, public domain).

Why (static review round 2, finding v3): OSM changeset 189525528 (25 Sep 2026, the taxiway W relocation) deleted the old
J 155476380 and re-mapped only its eastern 97 m (1562117374). The western remainder (~150 m, to the old W) kept its SFO
Museum pavement ('Taxiway A/F1', 'Taxiway A/B/F' junction polygons) with no recorded decision, while the old F1 crossing
of the same changeset was retired on this chart (tools/build_airfield_details.py PAVEMENT_RETIRE). NAIP 2024 predates
the rebuild, so the chart is the only current source of the pavement outline.

Method:
  1. render page 1 of refs/cache/faa/00375ad_2611.pdf at 600 dpi (pdftoppm, out/faa/al600-1.png; identical to the
     round-2 verifier's render);
  2. coarse affine world -> px from the 8 runway-end pixels picked on that render by the round-2 verifier (ENDS_PX; the
     key -> runway assignment and end order searched, as in its scratch faaJ.py; residual 28-64 px = 35-80 m: the chart's
     runway ends are drawn schematically);
  3. each runway's black band fitted by a trimmed PCA line in an 80 px corridor round the coarse line; the 4 crossings of
     the fitted bands (10L/10R x 1L/1R) <-> the FAA centreline crossings (js/geo.js RWY_ENDS) give the local affine
     (exact on the 4 crossings; the world runway centre points lie 0.1 / 0.3 m (median / max) off the fitted bands);
  4. chart classes under world geometries: grey 180-230 = pavement, white > 240 = no pavement, < 120 = black (runway
     band, text, lines: unknown). Controls: the retired F1 polygons (white expected), the relocated W (grey expected);
  5. the white (no pavement) chart regions touching the old-J remainder corridor (+-CORRIDOR m), opened by 2 px (thin
     white gaps between text strokes are not regions), as world polygons.
Close-out round 3 (2026-11-06, findings static-3 / static-4):
  * the crop round the corridor is 120 m wide (was 40 m, which cut the island off at the north painted island); the
    island is written whole (`white_polys`, `white_touches_crop` says whether it still reaches the crop edge);
  * per retired SFO Museum 'Taxiway F1' polygon (`f1_parts`): the chart's grey (pavement, 180-230; closed by 3 px so
    letter strokes inside a grey area stay grey, opened by 2 px, >= 30 m2) regions inside the part of it that no other
    SFO Museum taxiway / runway polygon covers (`grey_polys`): the builder keeps them paved and retires the rest (white =
    no pavement; black chart lines / text = unknown, not paved on their own); a polygon with less than F1_GREY_KEEP_M2
    of them is retired whole (round-2 verifier: F1 #2 is 40 % grey - the taxiway F fillet at the runway, on no other
    paved source).
Usage: python3 tools/xcheck/faa_al375_mask.py
"""
import hashlib, itertools, json, os, subprocess, sys
import numpy as np, cv2
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as G  # noqa: E402

PDF = os.path.join(ROOT, 'refs', 'cache', 'faa', '00375ad_2611.pdf')
PNG = os.path.join(ROOT, 'out', 'faa', 'al600-1.png')
OUT = os.path.join(ROOT, 'refs', 'cache', 'faa', 'al375_2611_oldJ.json')
DPI = 600
# runway-end pixels on the 600 dpi render (x, y), picked by the round-2 static verifier (2026-11-05, scratch ends_px.json);
# one pair per runway, the assignment / order is searched below
ENDS_PX = {'a': [[948.48, 3340.21], [2381.09, 621.24]], 'b': [[1140.37, 3339.16], [2511.85, 736.31]],
           'c': [[1046.79, 1394.15], [2886.60, 2362.17]], 'd': [[1100.67, 1612.86], [2757.14, 2487.01]]}
CORRIDOR = 12.0          # m: half width of the old-J remainder corridor (taxiway J 75 ft wide = 11.4 m half width, FAA AC
                         # 150/5300-13B TDG 5-6; the chart's islands are drawn to the pavement edge)
OSM_BASE = os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_ksfo_at_20260924T090742Z.json')
OSM_UPD = os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_ksfo_aeroway_at_20261104T180000Z.json')
OLD_J, NEW_J, NEW_W = 155476380, 1562117374, 1562117372
CROP_M = 120.0           # round 3: crop round the corridor for the island (40 m cut the island at the north painted island)
F1_GREY_KEEP_M2 = 50.0   # round 3: an F1 polygon with less chart-grey area than this off other SFO Museum pavement is retired whole


def ways(fn):
    d = json.load(open(fn)); nodes = {e['id']: (e['lat'], e['lon']) for e in d['elements'] if e['type'] == 'node'}
    out = {}
    for e in d['elements']:
        if e['type'] != 'way': continue
        pts = [(g['lat'], g['lon']) for g in e['geometry']] if 'geometry' in e else [nodes[n] for n in e.get('nodes', []) if n in nodes]
        if len(pts) >= 2: out[e['id']] = LineString([G.wgs84_to_world(a, b) for a, b in pts])
    return out


def register(g):
    best = None
    for perm in itertools.permutations(range(4)):
        for flips in itertools.product([0, 1], repeat=4):
            src, dst = [], []
            for ki, k in enumerate('abcd'):
                pa = G.RWY_PAIRS[perm[ki]]; ends = [G.end_world(pa[0]), G.end_world(pa[1])]
                if flips[ki]: ends = ends[::-1]
                src += ends; dst += ENDS_PX[k]
            A = np.hstack([np.array(src), np.ones((8, 1))]); M, *_ = np.linalg.lstsq(A, np.array(dst), rcond=None)
            r = np.linalg.norm(A @ M - np.array(dst), axis=1)
            if best is None or r.max() < best[0]: best = (r.max(), M, r)
    M0, r0 = best[1], best[2]
    P0 = lambda w: np.array([w[0], w[1], 1.0]) @ M0
    black = np.argwhere(g < 60)[:, ::-1].astype(float)
    lines = {}
    for pa in G.RWY_PAIRS:
        a, b = np.array(G.end_world(pa[0])), np.array(G.end_world(pa[1]))
        pa_, pb_ = P0(a), P0(b); L = np.linalg.norm(pb_ - pa_); d = (pb_ - pa_) / L; n = np.array([-d[1], d[0]])
        v = black - pa_; al = v @ d; ac = v @ n
        Q = black[(al > 0.1 * L) & (al < 0.9 * L) & (np.abs(ac) < 80)]
        for _ in range(6):
            c = Q.mean(0); vt = np.linalg.svd(Q - c, full_matrices=False)[2]; nn = np.array([-vt[0][1], vt[0][0]])
            res = (Q - c) @ nn; mad = np.median(np.abs(res - np.median(res)))
            Q = Q[np.abs(res - np.median(res)) < max(6, 2.5 * mad)]
        c = Q.mean(0); lines[pa] = (c, np.linalg.svd(Q - c, full_matrices=False)[2][0])
    def isect(c1, d1, c2, d2): return c1 + np.linalg.solve(np.array([d1, -d2]).T, c2 - c1)[0] * d1
    src, dst = [], []
    for p1 in G.RWY_PAIRS[:2]:
        for p2 in G.RWY_PAIRS[2:]:
            a1, b1 = map(np.array, map(G.end_world, p1)); a2, b2 = map(np.array, map(G.end_world, p2))
            src.append(isect(a1, b1 - a1, a2, b2 - a2)); dst.append(isect(*lines[p1], *lines[p2]))
    A = np.hstack([np.array(src), np.ones((4, 1))]); M, *_ = np.linalg.lstsq(A, np.array(dst), rcond=None)
    sc = float(np.sqrt(abs(np.linalg.det(M[:2]))))
    rr = []
    for pa in G.RWY_PAIRS:
        a, b = np.array(G.end_world(pa[0])), np.array(G.end_world(pa[1])); c, d = lines[pa]; nn = np.array([-d[1], d[0]])
        rr += [abs((np.array([*(a + f * (b - a)), 1.0]) @ M - c) @ nn) / sc for f in np.linspace(0.1, 0.9, 9)]
    diag = {'coarse_end_residual_m': [round(float(v) / sc, 1) for v in r0], 'px_per_m': round(sc, 4),
            'runway_centre_off_band_m': {'median': round(float(np.median(rr)), 2), 'max': round(float(np.max(rr)), 2)}}
    return M, diag


def main():
    if not os.path.exists(PNG):
        os.makedirs(os.path.dirname(PNG), exist_ok=True)
        subprocess.run(['pdftoppm', '-r', str(DPI), '-f', '1', '-l', '1', '-png', PDF, PNG[:-6]], check=True)
    im = cv2.imread(PNG); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    M, diag = register(g)
    Minv = np.linalg.inv(np.vstack([M.T, [0, 0, 1]]))           # px -> world
    def to_px(w): q = np.array([w[0], w[1], 1.0]) @ M; return q
    def chart_class(geom, step=1.0):
        x0, z0, x1, z1 = geom.bounds; v = []
        for x in np.arange(x0, x1, step):
            for z in np.arange(z0, z1, step):
                if geom.contains(Point(x, z)):
                    q = to_px((x, z)); v.append(g[int(round(q[1])), int(round(q[0]))])
        v = np.array(v)
        return {'grey': round(float(((v >= 180) & (v <= 230)).mean()), 3), 'white': round(float((v > 240).mean()), 3),
                'black': round(float((v < 120).mean()), 3)}
    base, upd = ways(OSM_BASE), ways(OSM_UPD)
    rest = base[OLD_J].difference(upd[NEW_J].buffer(3.0))
    rest = max(getattr(rest, 'geoms', [rest]), key=lambda l: l.length)
    mid = LineString([rest.interpolate(0.2, normalized=True), rest.interpolate(0.8, normalized=True)])
    corr = rest.buffer(CORRIDOR, cap_style=2)
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    controls = {'old J remainder, middle 60 %, +-8 m': chart_class(mid.buffer(8, cap_style=2)),
                'relocated W 1562117372 (+-8 m; paved)': chart_class(upd[NEW_W].buffer(8, cap_style=2))}
    for t in A['taxiways']:
        if t['name'] == 'Taxiway F1':
            for i, p in enumerate(t['polys']): controls['Taxiway F1 #%d (retired)' % i] = chart_class(Polygon(p[0], p[1:]).buffer(0))
    # white chart regions touching a world geometry -> world polygons (opened by 2 px: thin white gaps between text
    # strokes are not regions); also whether a kept region reaches the crop edge (then it is cut off)
    def white_regions(geom, crop_m, min_m2=0.0):
        x0, z0, x1, z1 = geom.buffer(crop_m).bounds
        cs = np.array([to_px(c) for c in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))])
        c0, r0 = np.floor(cs.min(0)).astype(int); c1, r1 = np.ceil(cs.max(0)).astype(int)
        white = (g[r0:r1, c0:c1] > 240).astype(np.uint8)
        white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        cnts, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        polys, touch = [], False
        for c in cnts:
            if len(c) < 3: continue
            pts = [tuple((np.array([p[0][0] + c0, p[0][1] + r0, 1.0]) @ Minv.T)[:2]) for p in c]
            pg = Polygon(pts).buffer(0)
            if pg.is_empty or not pg.intersects(geom) or pg.area < min_m2: continue
            xs, ys = c[:, 0, 0], c[:, 0, 1]
            touch |= bool(xs.min() <= 0 or ys.min() <= 0 or xs.max() >= c1 - c0 - 1 or ys.max() >= r1 - r0 - 1)
            polys.append(pg)
        return (unary_union(polys) if polys else Polygon()), touch
    wu, touch = white_regions(corr, CROP_M)
    # round 3 (finding static-4): the white / grey parts of the three retired F1 polygons
    other = unary_union([Polygon(p[0], p[1:]).buffer(0) for k in ('taxiways', 'runways') for t in A[k] for p in t['polys']
                         if not (k == 'taxiways' and t['name'] == 'Taxiway F1')])
    def grey_regions(geom, crop_m=20.0, min_m2=30.0):
        """the chart's grey (pavement) regions inside geom: grey 180-230 closed by 3 px (letter strokes / thin black lines
        inside a grey area stay pavement), opened by 2 px, components >= min_m2"""
        x0, z0, x1, z1 = geom.buffer(crop_m).bounds
        cs = np.array([to_px(c) for c in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))])
        c0, r0 = np.floor(cs.min(0)).astype(int); c1, r1 = np.ceil(cs.max(0)).astype(int)
        sub = g[r0:r1, c0:c1]; gr = ((sub >= 180) & (sub <= 230)).astype(np.uint8)
        gr = cv2.morphologyEx(gr, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)) & (sub <= 240).astype(np.uint8)
        gr = cv2.morphologyEx(gr, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        cnts, _ = cv2.findContours(gr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); polys = []
        for c in cnts:
            if len(c) < 3: continue
            pg = Polygon([tuple((np.array([q[0][0] + c0, q[0][1] + r0, 1.0]) @ Minv.T)[:2]) for q in c]).buffer(0).intersection(geom)
            for q in getattr(pg, 'geoms', [pg]):
                if q.geom_type == 'Polygon' and q.area >= min_m2: polys.append(q)
        return unary_union(polys) if polys else Polygon()
    f1 = {}
    for t in A['taxiways']:
        if t['name'] != 'Taxiway F1': continue
        for i, p in enumerate(t['polys']):
            pg = Polygon(p[0], p[1:]).buffer(0); off = pg.difference(other)
            gk = grey_regions(off); wr, _ = white_regions(pg, 20.0, 20.0)
            f1[str(i)] = {'area_m2': round(pg.area), 'chart_classes': controls['Taxiway F1 #%d (retired)' % i],
                          'white_m2': round(wr.intersection(pg).area), 'grey_kept_m2': round(gk.area),
                          'retire': 'whole' if gk.area < F1_GREY_KEEP_M2 else 'all but the chart-grey part',
                          'grey_polys': [[[round(x, 2), round(z, 2)] for x, z in q.exterior.coords] for q in getattr(gk, 'geoms', [gk])
                                         if q.geom_type == 'Polygon' and not q.is_empty]}
    out = {'source': 'FAA AL-375 (SFO) airport diagram, cycle 2611 (refs/cache/faa/00375ad_2611.pdf), page 1 at %d dpi' % DPI,
           'pdf_sha256': hashlib.sha256(open(PDF, 'rb').read()).hexdigest(), 'licence': 'US Government work, public domain',
           'tool': 'tools/xcheck/faa_al375_mask.py', 'registration': diag,
           'old_j_remainder': [[round(x, 2), round(z, 2)] for x, z in rest.coords], 'corridor_m': CORRIDOR,
           'chart_classes': controls,
           'white_in_corridor_m2': round(wu.intersection(corr).area), 'crop_m': CROP_M, 'white_touches_crop': touch,
           'white_m2': round(wu.area),
           'white_polys': [[[round(x, 2), round(z, 2)] for x, z in p.exterior.coords] for p in getattr(wu, 'geoms', [wu]) if not p.is_empty],
           'f1_grey_keep_m2': F1_GREY_KEEP_M2, 'f1_parts': f1}
    json.dump(out, open(OUT, 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ('white_polys', 'old_j_remainder', 'f1_parts')}, indent=1))
    print('F1:', {k: {kk: vv for kk, vv in v.items() if kk != 'grey_polys'} for k, v in f1.items()})
    print('white polygons %d, wrote %s' % (len(out['white_polys']), os.path.relpath(OUT, ROOT)))


if __name__ == '__main__':
    main()
