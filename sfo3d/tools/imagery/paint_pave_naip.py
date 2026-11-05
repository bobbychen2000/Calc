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
inferred apron (data/sfo_details.json) - or inside OSM aprons / within 40 m of OSM taxi centrelines (review round 3), or
within 60 m of an aircraft parking position / ADS-B parked stay (static close-out 2026-11-04: north cargo aprons; inside a
position's own footprint every pixel that is not vegetation / bare soil / building counts, so parked aircraft, GSE and
ULDs do not leave holes; round 2, 2026-11-05: only AIRCRAFT stays - an ICAO type that is no vehicle pseudo-type, or an
airline callsign (round 3: no flysfo field) - and bare soil / dry grass (R - B > 38, R > 110) is rejected in the footprints too; round 3:
the vehicle stays seed the 60 m candidate region again, never footprints) -,
outside them and outside buildings (SFO Museum structures, terminal
complex, boarding areas; OSM buildings are not used), components >= 300 m2 after a 1.5 m opening, holes (parked
aircraft, vehicles, shadows) < 3000 m2 filled. Roofs of hangars that SFO Museum does not map can classify as
pavement (grey); they are listed by area in the log for review.

    python3 tools/imagery/paint_pave_naip.py          # writes data/sfo_paint.* and data/sfo_pavement.*
    python3 tools/imagery/paint_pave_naip.py --preview   # + refs/cache/naip/paint_pave_preview.jpg (NAIP pixels; stays local)
"""
import json, math, os, re, sys
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
    # static close-out (2026-11-04; open requests traffic_engine_data.md s.2, realtime_round1/2: the north cargo /
    # maintenance aprons): the candidate region also covers 60 m round every aircraft parking position of
    # data/sfo_stands.json (positions: OSM aeroway=parking_position; remote: SFO remote stands) and every ADS-B parked stay
    # of refs/cache/stands/adsb_parked.json (adsb.lol): the review found 40 of 179 positions with > 50 % of a narrow-body
    # footprint outside the app's pavement (KAL214 B748, CSB805 B762, EVA629, ATN3300 parked there). NAIP decides as
    # everywhere: grey + smooth only. Holes (the parked aircraft, GSE, ULDs) up to 12000 m2 are filled when such a point
    # lies in them (a 747-8 with its shadow exceeds the general 3000 m2 limit).
    St = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    park = np.zeros((H, W), np.uint8)
    pts_ = [[q['x'], q['z']] for q in St.get('positions', []) + St.get('remote', []) if 'x' in q]
    stays = aircraft_stays()
    pts_ += [[v['x'], v['z']] for v in stays]
    # round 3 (2026-11-05, review static r2 v4): the VEHICLE stays (airport-operations / ARFF / service vehicles) seed the
    # candidate region again - vehicles park on pavement, and dropping them in round 2 also dropped ~0.6 ha of real
    # grey pavement round them (the ARFF apron (-1569, -600), a concrete apron (-1373, -1412)). They only widen where NAIP
    # may decide (grey + smooth, which excludes soil / dry grass: S < 32 means R - B < 32); they are NOT footprints (no
    # 25 m disc paved regardless of grey) and NOT parking points for the 12000 m2 hole limit - both stay aircraft-only.
    vstays = vehicle_stays()
    N_PARK = 0
    for q in pts_ + [[v['x'], v['z']] for v in vstays]:
        if not q: continue
        c_ = P([q])[0]
        if 0 <= c_[0] < W and 0 <= c_[1] < H: cv2.circle(park, (int(c_[0]), int(c_[1])), int(60 / RES), 1, -1); N_PARK += 1
    cand = (dpav < 60) | (oap > 0) | (dcl < 40) | (park > 0)
    p = (grey | g) & (pav == 0) & (bld == 0) & cand
    p = ndi.binary_opening(p, iterations=3)
    lab, n = ndi.label(p); sz = ndi.sum(p, lab, range(1, n + 1))
    p = np.isin(lab, 1 + np.nonzero(sz * RES * RES >= 300)[0])
    holes = ndi.binary_fill_holes(p) & ~p
    lh, nh = ndi.label(holes); hs = ndi.sum(holes, lh, range(1, nh + 1))
    p |= np.isin(lh, 1 + np.nonzero(hs * RES * RES < 3000)[0])
    pcore = np.zeros((H, W), np.uint8)              # the parking points themselves (12 m discs) for the larger hole limit
    for q in pts_:
        if not q: continue
        c_ = P([q])[0]
        if 0 <= c_[0] < W and 0 <= c_[1] < H: cv2.circle(pcore, (int(c_[0]), int(c_[1])), int(12 / RES), 1, -1)
    hp = ndi.sum(pcore > 0, lh, range(1, nh + 1))
    p |= np.isin(lh, 1 + np.nonzero((hs * RES * RES < 12000) & (hp > 0))[0])
    p = ndi.gaussian_filter(p.astype(np.float32), 1.0 / RES) > 0.5
    p &= (pav == 0) | (dpav > 0)
    lab, n = ndi.label(p); sz = ndi.sum(p, lab, range(1, n + 1))
    keep = 1 + np.nonzero(sz * RES * RES >= 300)[0]
    p = np.isin(lab, keep)
    p |= (holdm > 0) & (pav == 0) & (bld == 0)          # the measured hold bars are on pavement by definition
    # static close-out (2026-11-04): an aircraft parking position's footprint (OSM position: 38 x 40 m box along its heading;
    # ADS-B parked stay: 25 m disc) is pavement wherever NAIP shows no vegetation / bare soil there and no mapped building:
    # the cluttered aprons (parked aircraft, GSE, ULDs, cars) fail the grey + smooth test (review: 40 of 179 positions > 50 %
    # unpaved; the review's suggestion "fill the holes left by aircraft, GSE and ULDs")
    veg = ((Hh >= 50) & (Hh <= 175) & (S > 35)) | ((Hh >= 15) & (Hh < 50) & (S > 45) & (V < 175))
    foot = np.zeros((H, W), np.uint8)
    for q in St.get('positions', []) + St.get('remote', []):
        if 'x' not in q: continue
        h_ = math.radians(q.get('hdg') or 0.0); f_ = np.array([math.sin(h_), -math.cos(h_)]); r_ = np.array([math.cos(h_), math.sin(h_)])
        c_ = np.array([q['x'], q['z']]) - f_ * 20.0          # the footprint lies behind the stop point
        fill(foot, [[list(c_ + f_ * a + r_ * b) for a, b in ((20, 19), (20, -19), (-20, -19), (-20, 19))]])
    for v in stays:
        c_ = P([[v['x'], v['z']]])[0]
        if 0 <= c_[0] < W and 0 <= c_[1] < H: cv2.circle(foot, (int(c_[0]), int(c_[1])), int(25 / RES), 1, -1)
    vegc = ndi.binary_opening(veg, iterations=2)          # isolated green / brown pixels (paint, vehicles) are not vegetation
    # round 2 (2026-11-05, review static-v2): bare soil / bright dry grass is not pavement either - the HSV vegetation test
    # misses it (tan, V > 175). Reviewer's rule on the BGR raster: R - B > 38 and R > 110 (yellow paint has R ~ G and is
    # thin: removed by the opening, like vehicles)
    Bc, Rc = img[..., 0].astype(np.int16), img[..., 2].astype(np.int16)
    soilc = ndi.binary_opening((Rc - Bc > 38) & (Rc > 110), iterations=2)
    addf = (foot > 0) & ~vegc & ~soilc & (bld == 0) & (pav == 0) & (V > 40)
    print('parking footprints: +%.1f ha pavement (not vegetation / soil, not building); ADS-B stays used %d of %d (aircraft; + %d vehicle stays as candidate seeds only)' % (
        (addf & ~p).sum() * RES * RES / 1e4, len(stays), N_STAYS[0], len(vstays)))
    p |= addf
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
    # static close-out (2026-11-04): taxiways built after NAIP 2024 (data/sfo_details.json centrelines with src
    # 'osm_update' and a width: the relocated W) are paved as the centreline buffered by half their (inferred) width -
    # NAIP cannot show them; src per polygon in `src`
    from shapely.geometry import LineString as _LS
    srcs = ['naip'] * len(pave_polys)
    for cl_, m_ in zip(Dt.get('centerlines', []), Dt.get('centerlineMeta', [])):
        if m_.get('src') == 'osm_update' and m_.get('width_m') and len(cl_) >= 2:
            g_ = _LS(cl_).buffer(m_['width_m'] / 2, cap_style=2, join_style=1).simplify(0.2)
            pave_polys.append([[[round(x, 2), round(z, 2)] for x, z in list(g_.exterior.coords)[:-1]]]); conc.append(False)
            srcs.append('osm_update %s (%s, width %s)' % (m_.get('osm_id'), m_.get('ref'), m_['width_m']))
    prov = ('tools/imagery/paint_pave_naip.py: colour classification of USDA NAIP 2024 (public domain, flown 2024-05-20, '
            '0.5 m world raster), 24 Sep 2026; static close-out 2026-11-04 (parking-position candidates / footprints, the relocated W)')
    paint = {'frame': GF.FRAME_ID, 'note': 'Green no-taxi island paint (FAA AC 150/5340-1M para 1.5.2) classified on USDA NAIP 2024 '
             '(hue 140-180, S > 55, V > 150; within 30 m of SFO Museum taxiway/runway pavement).', 'provenance': prov,
             'polys': paint_polys}
    pave = {'frame': GF.FRAME_ID, 'note': 'Paved areas not in the SFO Museum geometry (cargo/maintenance aprons, service roads, '
            'shoulders) classified on USDA NAIP 2024 (grey pixels within 60 m of mapped pavement, of OSM aprons / taxi centrelines '
            '(40 m) or of aircraft parking positions / ADS-B parked stays (60 m; static close-out 2026-11-04), outside mapped buildings); '
            'conc = concrete (median V >= 150). Unmapped grey roofs can be included (inferred).', 'provenance': prov,
            'polys': pave_polys, 'conc': conc, 'src': srcs}
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


# ADS-B emitter pseudo-types of the readsb / tar1090 aircraft database for things that are not aircraft (ground / service
# / emergency vehicles, towers / obstacles, balloons, UAVs)
NOT_AIRCRAFT = {'SERV', 'GRND', 'EMER', 'TWR', 'BALL', 'UAV', 'SHIP', 'GYRO', 'ULAC', 'GLID', 'PARA'}
N_STAYS = [0]


def _stays():
    try:
        st = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'stands', 'adsb_parked.json')))['stays']
    except (OSError, KeyError, ValueError):
        return []
    N_STAYS[0] = len(st)
    return st


def _typed(v): return bool(v.get('type') and v['type'] not in NOT_AIRCRAFT)
def _prefix(c):
    m = re.match(r'^([A-Z]{3})\d', c or ''); return m.group(1) if m else None


def _is_aircraft(v, stays):
    """an ICAO aircraft type in the feed, or a callsign whose 3-letter operator prefix flies a TYPED aircraft among the
    stays (an airline designator seen on real aircraft: DAL, UAL ...; the airport vehicles OPS / R / FM / KOW never carry
    a type). Round 3: no flysfo-derived field (stand / flight / sfo_type of adsb_parked.py's SFO match) is read, so the
    pavement does not depend on the local flysfo snapshot; same 159 of 177 stays as the round-2 rule (typed or SFO-matched)"""
    ops = {_prefix(c) for w in stays if _typed(w) for c in w.get('callsigns') or []} - {None}
    return _typed(v) or any(_prefix(c) in ops for c in v.get('callsigns') or [])


def aircraft_stays():
    """refs/cache/stands/adsb_parked.json stays that are AIRCRAFT (_is_aircraft: an ICAO aircraft type, not a vehicle
    pseudo-type, or an airline callsign). Round 2 (2026-11-05, review static-v2): the airport-operations vehicles (OPS12 / 14 /
    15 / 31 / 38 / 40 / 44, FM8, R41, R88 - no type, or SERV) and typeless unmatched stays had become 25 m pavement discs
    on the infield soil."""
    st = _stays(); return [v for v in st if _is_aircraft(v, st)]


def vehicle_stays():
    """the other stays (vehicle pseudo-type, or no type and no airline callsign): candidate-region seeds only
    (round 3, review static r2 v4)"""
    st = _stays(); return [v for v in st if not _is_aircraft(v, st)]


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
