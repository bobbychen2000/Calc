"""Generator for data/sfo_paint.{json,js} (green no-taxi island paint) and data/sfo_pavement.{json,js} (paved areas
that are not in the SFO Museum geometry), classified on USDA NAIP 2024 (public domain; 0.5 m world raster of the
0.6 m UTM source flown 2024-05-20, refs/cache/naip/, docs/research/imagery.md). Replaces the Google-screenshot
classification (tools/sat/paint_export.py / pave_export.py / legacy_export.py), which the owner ruled out for
committed coordinates on 24 Sep 2026.

Colour classes (OpenCV HSV, hue in degrees 0-360, S and V 0-255), read on NAIP 24 Sep 2026 (tools/imagery/
paint_pave_naip.py --stats prints them for sample areas):
  green paint   hue 140-180, S > 55, V > 150   (paint pixels next to hold #0 (-1608, -1028): V 186-208, S 69-83;
                                                the bay has the same hue but V 100-130)
  pavement      S < 32 and 55 < V < 245 (grey concrete / asphalt) and smooth (mean |Laplacian| over 3 m < 3.5; runway
                2.3, dry grass / sand 5.8-6.9), or the green paint itself; vegetation, soil and water fall outside
  concrete      pavement component with median V >= 150 (asphalt darker)
Kept only on the airfield: green paint within 30 m of SFO Museum taxiway / runway pavement and not on it (the paint
is on the island pavement between taxiway fillets); extra pavement within 60 m of the SFO Museum paved areas + the
inferred apron (data/sfo_details.json) - or inside OSM aprons / within 40 m of OSM taxi centrelines (review round 3) -,
outside them and outside buildings (SFO Museum structures, terminal
complex, boarding areas; OSM buildings are not used), components >= 300 m2 after a 1.5 m opening, holes (parked
aircraft, vehicles, shadows) < 3000 m2 filled. Roofs of hangars that SFO Museum does not map can classify as
pavement (grey); they are listed by area in the log for review.

    python3 tools/imagery/paint_pave_naip.py          # writes data/sfo_paint.* and data/sfo_pavement.*
    python3 tools/imagery/paint_pave_naip.py --preview   # + refs/cache/naip/paint_pave_preview.jpg (NAIP pixels; stays local)
"""
import json, os, sys
import numpy as np, cv2
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF

META = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
NPY = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy')
RES = META['res']
# processing window (world m): the airfield
X0, Z0, X1, Z1 = -2600.0, -2350.0, 2050.0, 1900.0


def main(preview=False):
    assert META['frame'] == GF.FRAME_ID
    im = np.load(NPY, mmap_mode='r')
    c0 = int(round((X0 - META['x0']) / RES)); r0 = int(round((Z0 - META['z0']) / RES))
    c1 = int(round((X1 - META['x0']) / RES)); r1 = int(round((Z1 - META['z0']) / RES))
    img = np.ascontiguousarray(im[r0:r1, c0:c1]); H, W = img.shape[:2]
    x0 = META['x0'] + c0 * RES; z0 = META['z0'] + r0 * RES      # world of the pixel corner (col 0, row 0)
    def P(ring): return np.array([[(x - x0) / RES - 0.5, (z - z0) / RES - 0.5] for x, z in ring])
    def world(p): return [round(float(x0 + p[0] * RES), 1), round(float(z0 + p[1] * RES), 1)]
    def fill(mask, rings, v=1):
        for ring in rings: cv2.fillPoly(mask, [np.round(P(ring) * 4).astype(np.int32)], v, shift=2)
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    Dt = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    pav = np.zeros((H, W), np.uint8); twr = np.zeros((H, W), np.uint8); bld = np.zeros((H, W), np.uint8)
    for k in ('taxiways', 'runways'):
        for t in A[k]:
            for poly in t['polys']: fill(twr, [poly[0]])
    pav |= twr
    for poly in Dt['apron']:
        fill(pav, [poly[0]])
        for h in poly[1:]: fill(pav, [h], 0)
    for poly in A['terminalComplex']: fill(bld, [poly[0]])
    for b in A['boardingAreas']:
        for poly in b['polys']: fill(bld, [poly[0]])
    for s in A['structures']:
        if s['kind'] in ('garage', 'building', 'hangar', 'hotel', 'atc', 'airtrain'):
            for poly in s['polys']: fill(bld, [poly[0]])
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); Hh = hsv[..., 0].astype(np.int16) * 2; S = hsv[..., 1]; V = hsv[..., 2]
    dtw = ndi.distance_transform_edt(twr == 0) * RES
    dpav = ndi.distance_transform_edt(pav == 0) * RES
    # ------------------------------------------------------------------ green paint
    g = (Hh >= 140) & (Hh <= 180) & (S > 55) & (V > 150)
    g = ndi.binary_closing(g, iterations=2) & ndi.binary_dilation(g, iterations=2)
    g = ndi.binary_opening(g, iterations=1)
    g &= (dtw < 30) & (bld == 0)
    lab, n = ndi.label(g); sz = ndi.sum(g, lab, range(1, n + 1))
    g = np.isin(lab, 1 + np.nonzero(sz * RES * RES >= 40)[0])
    paint_polys = contours(g, 0.5 / RES, 30, world)
    # ------------------------------------------------------------------ extra pavement
    # texture: mean |Laplacian| of the grey level over 3 m (pavement is smooth: 2-3; dry grass / gravel 5-8)
    gl = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lap = cv2.blur(np.abs(cv2.Laplacian(cv2.GaussianBlur(gl, (3, 3), 0), cv2.CV_32F)), (7, 7))
    grey = (S < 32) & (V > 55) & (V < 245) & (lap < 3.5)
    # review round 2: a 3 m band along every hold bar measured on NAIP (data/sfo_details.json holds) is pavement by
    # definition - before, the ladders' outer ends lay on 'sand' in the model: the shoulders break up at the painted edge
    # lines / ladders and fell below the component size limit. (Counting yellow paint pixels as pavement was tried and
    # rejected: bright dry grass has the same hue and added ~25 ha of grass, checked on NAIP.)
    holdm = np.zeros((H, W), np.uint8)
    for h in Dt.get('holds', []):
        a_, b_ = np.array(h['a']), np.array(h['b']); u_ = np.array(h['dir']) * 1.5
        fill(holdm, [[list(a_ - u_), list(b_ - u_), list(b_ + u_), list(a_ + u_)]])
    # review round 3: the candidate region also covers OSM aeroway=apron polygons and the ground within 40 m of an OSM
    # taxiway / taxilane centreline (ODbL). West-field taxilanes lie > 60 m from SFO Museum pavement and were missing -
    # tools/build_airfield_details.py had paved them with 45 m discs wherever an ADS-B aircraft stood (removed); now the
    # NAIP classification itself decides there.
    osm = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')))
    oap = np.zeros((H, W), np.uint8); ocl = np.zeros((H, W), np.uint8)
    for a in osm.get('aprons', []):
        if len(a['pts']) >= 3: fill(oap, [[GF.wgs84_to_world(la, lo) for la, lo in a['pts']]])
    for t in osm.get('taxiways', []):
        q = np.round(P([GF.wgs84_to_world(la, lo) for la, lo in t['pts']]) * 4).astype(np.int32)
        if len(q) >= 2: cv2.polylines(ocl, [q], False, 1, 1, shift=2)
    dcl = ndi.distance_transform_edt(ocl == 0) * RES
    cand = (dpav < 60) | (oap > 0) | (dcl < 40)
    p = (grey | g) & (pav == 0) & (bld == 0) & cand
    p = ndi.binary_opening(p, iterations=3)
    lab, n = ndi.label(p); sz = ndi.sum(p, lab, range(1, n + 1))
    p = np.isin(lab, 1 + np.nonzero(sz * RES * RES >= 300)[0])
    holes = ndi.binary_fill_holes(p) & ~p
    lh, nh = ndi.label(holes); hs = ndi.sum(holes, lh, range(1, nh + 1))
    p |= np.isin(lh, 1 + np.nonzero(hs * RES * RES < 3000)[0])
    p = ndi.gaussian_filter(p.astype(np.float32), 1.0 / RES) > 0.5
    p &= (pav == 0) | (dpav > 0)
    lab, n = ndi.label(p); sz = ndi.sum(p, lab, range(1, n + 1))
    keep = 1 + np.nonzero(sz * RES * RES >= 300)[0]
    p = np.isin(lab, keep)
    p |= (holdm > 0) & (pav == 0) & (bld == 0)          # the measured hold bars are on pavement by definition
    pave_polys, conc = [], []
    lab, n = ndi.label(p)
    big = []
    for L in range(1, n + 1):
        m = lab == L
        ys, xs = np.nonzero(m)
        onhold = bool(holdm[m].any())
        if len(ys) * RES * RES < 300 and not onhold: continue
        sub = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        polys = contours(sub, 0.5 / RES, 4 if onhold else 300, lambda q, ox=xs.min(), oy=ys.min(): world((q[0] + ox, q[1] + oy)))
        vmed = float(np.median(V[m]))
        for poly in polys: pave_polys.append(poly); conc.append(bool(vmed >= 150))
        big.append((round(len(ys) * RES * RES), world((xs.mean(), ys.mean())), round(vmed)))
    big.sort(reverse=True)
    prov = ('tools/imagery/paint_pave_naip.py: colour classification of USDA NAIP 2024 (public domain, flown 2024-05-20, '
            '0.5 m world raster), 24 Sep 2026')
    paint = {'frame': GF.FRAME_ID, 'note': 'Green no-taxi island paint (FAA AC 150/5340-1M para 1.5.2) classified on USDA NAIP 2024 '
             '(hue 140-180, S > 55, V > 150; within 30 m of SFO Museum taxiway/runway pavement).', 'provenance': prov,
             'polys': paint_polys}
    pave = {'frame': GF.FRAME_ID, 'note': 'Paved areas not in the SFO Museum geometry (cargo/maintenance aprons, service roads, '
            'shoulders) classified on USDA NAIP 2024 (grey pixels within 60 m of mapped pavement, outside mapped buildings); '
            'conc = concrete (median V >= 150). Unmapped grey roofs can be included (inferred).', 'provenance': prov,
            'polys': pave_polys, 'conc': conc}
    for name, var, res in (('paint', 'PAINT', paint), ('pavement', 'PAVEMENT', pave)):
        blob = json.dumps(res, separators=(',', ':'))
        open(os.path.join(ROOT, 'data', f'sfo_{name}.json'), 'w').write(blob)
        open(os.path.join(ROOT, 'data', f'sfo_{name}.js'), 'w').write(
            f'// generated by tools/imagery/paint_pave_naip.py from USDA NAIP 2024 (public domain)\nexport const {var} = ' + blob + ';\n')
    print('paint: %d polygons, %.1f ha' % (len(paint_polys), g.sum() * RES * RES / 1e4))
    print('pavement: %d polygons, %.1f ha, concrete %d' % (len(pave_polys), p.sum() * RES * RES / 1e4, sum(conc)))
    print('largest pavement components (m2, centre, median V):', big[:12])
    if preview:
        vis = (img // 2).copy()
        vis[p] = (vis[p] * 0.4 + np.array([40, 200, 255]) * 0.6).astype(np.uint8)
        vis[g] = (vis[g] * 0.3 + np.array([255, 0, 255]) * 0.7).astype(np.uint8)
        cv2.imwrite(os.path.join(ROOT, 'refs', 'cache', 'naip', 'paint_pave_preview.jpg'), cv2.resize(vis, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA))


def contours(mask, tol_px, min_area, world):
    cs, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    if hier is None: return out
    for i, c in enumerate(cs):
        if hier[0][i][3] != -1 or cv2.contourArea(c) * RES * RES < min_area: continue
        rings = [c]; k = hier[0][i][2]
        while k != -1:
            if cv2.contourArea(cs[k]) * RES * RES > 20: rings.append(cs[k])
            k = hier[0][k][0]
        poly = []
        for rr in rings:
            a = cv2.approxPolyDP(rr, tol_px, True)[:, 0, :].astype(np.float64)
            if len(a) >= 3: poly.append([world((q[0] + 0.5, q[1] + 0.5)) for q in a])
        if poly: out.append(poly)
    return out


if __name__ == '__main__':
    main('--preview' in sys.argv)
