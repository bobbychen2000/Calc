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
Close-out round 3 (2026-11-06, finding static-1; each tagged in the pavement `src`, inferred): (a) the candidate region
also covers 60 m round the 5 m cells where ADS-B shows an aircraft on the ground at least twice
(refs/cache/stands/adsb_ground_cells.json, all committed adsb.lol hours) and the grey apron connected to them up to 150 m; (b) cluttered aprons: inside a 25 m window that NAIP shows >= 88 % grey, <= 3 % soil and
vegetation and >= 50 % smooth, every pixel that is not soil / vegetation / a building (SFO Museum or OSM) is pavement;
(c) within 25 m of a vehicle stay, smooth unsaturated pixels, or pixels in a >= 60 % grey / <= 5 % soil window, connected
to the pavement (the ARFF apron); (d) within 10 m of a cell where >= 2 aircraft were on the ground, the window of (b)
also counts bright (V >= 245) grey pixels - a fresh-concrete slab on a taxilane, never a roof under an aircraft; (e) a pixel
in ANY qualifying window of (b) (not only the one centred on it: light shoulders / island borders beside soil) counts when it
is near-neutral, not soil / vegetation / building and locally smooth (2026-11-07). The green
paint also gets the inferred old-J island of FAA AL-375 2611 (finding static-3; paint `src`).
Fix round 2 (2026-11-08, verifier findings v2 / v3 / v5 / v9): the OSM-building / END_ZONES exclusion now holds after the
hole fill, the gaussian step, the footprints and the pads too (OSM buildings and end zones keep exactly the pavement of the
pre-round-3 rules); (f) holes enclosed by the paved union that held ADS-B aircraft (or a vehicle stay), NAIP <= 5 % soil +
vegetation and >= 60 % grey, < 12000 m2, are pavement; (g) the interior of the old-J chart island is paved (inferred); the
pavement file's note / provenance / .js header name its ODbL inputs (OSM, adsb.lol).
Close-out round 5 (2026-11-08, verifier of close-out 3 fix 2): the forecourt of a vehicle stay's building (within PAD_R of
the stay and FC_R of a mapped building: the ARFF apron's striped tan bays) is pavement without the texture / pixel-colour
tests, when its 25 m window is clean (<= 5 % soil, <= 3 % vegetation) and it connects to the pavement (inferred).
Close-out round 7 (2026-11-09, realtime request C5.3): (h) a 25 m parking footprint round every adsb.lol SIGNAL-END point
(tools/imagery/adsb_ground_cells.py `signal_end`: the last ground fix at < 3 kt, then >= 30 min without a position fix - where
the app keeps a silent aircraft parked; ASA503 B39M, 11 h at the west maintenance hangar apron) is pavement where NAIP shows
no vegetation / soil / water and no mapped building, when connected to the pavement and the added piece is <= 5 % soil +
vegetation and >= 60 % grey on NAIP (inferred; `src` m2).

    python3 tools/imagery/paint_pave_naip.py          # writes data/sfo_paint.* and data/sfo_pavement.*
    python3 tools/imagery/paint_pave_naip.py --preview   # + refs/cache/naip/paint_pave_preview.jpg (NAIP pixels; stays local)
    python3 tools/imagery/paint_pave_naip.py --dump F.npz   # + the classification masks (diagnostics; ~3-4 GB RAM: heavy lock)
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


def main(preview=False, dump=None):
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
    # close-out round 3 (2026-11-06, finding static-1) (a): the candidate region also covers AGC_R m round every 5 m cell where
    # ADS-B shows an AIRCRAFT on the ground at least twice (refs/cache/stands/adsb_ground_cells.json, all committed adsb.lol
    # hours, tools/imagery/adsb_ground_cells.py): UAL2480 B752 parked for hours on the light concrete maintenance apron at
    # (-1383, -1917), 30 m off every candidate source (offpave.mask 369,812 frames). NAIP still decides.
    agc = np.zeros((H, W), np.uint8); N_AGC = 0
    agc2 = np.zeros((H, W), np.uint8)               # (d): cells where >= 2 distinct aircraft were on the ground
    try:
        for cx_, cz_, n_, a_ in json.load(open(os.path.join(ROOT, 'refs', 'cache', 'stands', 'adsb_ground_cells.json')))['cells']:
            if n_ < 2: continue
            c_ = P([[cx_, cz_]])[0]
            if 0 <= c_[0] < W and 0 <= c_[1] < H:
                agc[int(c_[1]), int(c_[0])] = 1; N_AGC += 1
                if a_ >= 2: agc2[int(c_[1]), int(c_[0])] = 1
    except (OSError, KeyError, ValueError):
        pass
    cand_old = (dpav < 60) | (oap > 0) | (dcl < 40) | (park > 0)
    dagc = ndi.distance_transform_edt(agc == 0) * RES
    cand = cand_old | (dagc < AGC_R)
    print('candidate region: %.1f ha (+%.1f ha within %.0f m of %d ADS-B aircraft ground cells)' % (cand.sum() * RES * RES / 1e4, (cand & ~cand_old).sum() * RES * RES / 1e4, AGC_R, N_AGC))
    # (b) cluttered aprons: GSE, ULDs, parked cars and parking stripes break the grey + smooth test up (realtime / static
    # R3.2.3 cells: NAIP grey >= 88 % and soil <= 3 % but 48-76 % paved: (-1450, -175), (-1050, 1025), (-1400, -50), the FBO
    # (-800, -925)). Inside a 25 m window whose NAIP pixels are >= ENV_GREY grey (channel spread < 22, 70 < lum, V < 245:
    # not the bright roofs), <= ENV_SOIL soil (R - B > 38, R - G > 5, R > 110) and vegetation (G - R > 6, G > B, lum < 150)
    # each, and >= ENV_SMOOTH smooth (the texture test above: not rip-rap / gravel), every pixel that is not itself soil /
    # vegetation / a mapped building is pavement - the clutter inside a grey envelope. The classes are the reviewers' cell
    # classes; OSM building footprints (except building=roof canopies) are excluded from these additions.
    Bc_, Gc_, Rc_ = img[..., 0].astype(np.int16), img[..., 1].astype(np.int16), img[..., 2].astype(np.int16)
    lum_ = (Bc_ + Gc_ + Rc_) // 3; spr_ = img.max(-1).astype(np.int16) - img.min(-1)
    ggrey = (spr_ < 22) & (lum_ > 70) & (V < 245)
    ggreyb = (spr_ < 22) & (lum_ > 70)              # (d) below: the same without the V cap (bright concrete)
    gsoil = (Rc_ - Bc_ > 38) & (Rc_ - Gc_ > 5) & (Rc_ > 110)
    gveg = (Gc_ - Rc_ > 6) & (Gc_ - Bc_ > 0) & (lum_ < 150)
    ext_px = (spr_ < ENV_EXT_SPR) & (V < 245) & (Rc_ - Bc_ <= ENV_EXT_RB) & (lum_ > 70)   # (e) pixel test, below
    del Bc_, Gc_, Rc_, spr_
    def wmean(m): return cv2.blur(m.astype(np.uint8) * 255, (ENV_WIN, ENV_WIN)).astype(np.float32) / 255.0
    env = (wmean(ggrey) >= ENV_GREY) & (wmean(gsoil) <= ENV_SOIL) & (wmean(gveg) <= ENV_SOIL) & (wmean(lap < 3.5) >= ENV_SMOOTH)
    obld = osm_buildings(fill, H, W)
    ezm = np.zeros((H, W), np.uint8); fill(ezm, end_zone_rings())     # runway end zones: no round-3 additions
    envadd = env & ~gsoil & ~gveg & (lum_ > 40) & (obld == 0) & (ezm == 0)
    # (e) close-out round 3, 2026-11-07 (static-1 residual): the window above is CENTRED on the pixel, so a light paved
    # shoulder / island border next to soil fails it although a 25 m cell containing it passes the reviewers' test (the
    # replay's 25 m cell (-550, -375): NAIP 92 % grey / 1 % soil, 76 % paved, 69 aircraft fixes of 11 aircraft; its island
    # border is light concrete with yellow stripes, which also fail the 3 m texture test). A pixel inside ANY qualifying
    # 25 m window (the window centres dilated by the window) is pavement too when it is itself near-neutral (channel spread
    # < ENV_EXT_SPR and V < 245, R - B <= ENV_EXT_RB, lum > 70: not light soil, water or shadow), not soil / vegetation /
    # a building, and its own 5 m window is >= 50 % smooth (not the rip-rap of the seawalls). Inferred. The runway end zones
    # (blast pads / EMAS beds, js/live/airport.js END_ZONES: the app draws them itself) take no round-3 addition (the
    # first version of (e) paved the light EMAS beds beyond 1L / 1R).
    envany = cv2.dilate(env.astype(np.uint8), np.ones((ENV_WIN + 1, ENV_WIN + 1), np.uint8)) > 0
    sm_loc = cv2.blur((lap < 3.5).astype(np.uint8) * 255, (ENV_EXT_SMW, ENV_EXT_SMW)) >= 128
    envext = envany & ~env & ext_px & sm_loc & ~gsoil & ~gveg & (obld == 0) & (ezm == 0)
    print('  any-window envelope (e): %.2f ha of window pixels' % ((envext & ~envadd & (pav == 0) & (bld == 0)).sum() * RES * RES / 1e4))
    envadd |= envext
    del envany, sm_loc, envext, ext_px
    # (d) bright concrete on a taxilane: V >= 245 is left out of the window above because unmapped bright roofs then
    # classified as apron; but a fresh-concrete slab where aircraft taxi (realtime cell (-1050, 1025) south of Boarding Area
    # B: NAIP 94 % grey / 3 % soil, 772 off-pavement frames of 9 aircraft, a 25 x 50 m slab at V 245-255 with the taxi
    # lead-in line painted across it) is the same pavement. Within AC_R m of a 5 m cell where >= 2 distinct aircraft were on
    # the ground (ADS-B; an aircraft's antenna is never over a roof), the window counts bright grey pixels as grey too.
    envb = (wmean(ggreyb) >= ENV_GREY) & (wmean(gsoil) <= ENV_SOIL) & (wmean(gveg) <= ENV_SOIL) & (wmean(lap < 3.5) >= ENV_SMOOTH)
    near2 = cv2.dilate(agc2, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(AC_R / RES) + 1, 2 * int(AC_R / RES) + 1))) > 0
    envbadd = envb & near2 & ~gsoil & ~gveg & (lum_ > 40) & (obld == 0) & (ezm == 0) & ~envadd
    print('  bright-concrete envelope near aircraft cells (d): %.2f ha of window pixels' % ((envbadd & (pav == 0) & (bld == 0)).sum() * RES * RES / 1e4))
    envadd |= envbadd
    del lum_, envb, near2, envbadd, ggreyb
    # ... and a continuous apron that an aircraft stood on is pavement beyond AGC_R too: grey + smooth (the test above) or
    # cluttered-envelope pixels connected to such pixels inside the ADS-B candidate disc, up to AGC_GROW m from a ground
    # cell (the north cargo apron (-1035, -1863) and the maintenance apron (-1383, -1917) would otherwise end in an arc
    # across open concrete), where the 25 m window holds <= 3 % soil and <= 3 % vegetation (light infield soil, which can
    # pass grey + smooth pixel by pixel, does not grow it); never buildings (SFO Museum / OSM)
    clean_w = (wmean(gsoil) <= ENV_SOIL) & (wmean(gveg) <= ENV_SOIL)
    gro = (envadd | (grey & clean_w)) & (pav == 0) & (bld == 0) & (obld == 0) & (dagc < AGC_GROW)
    lab_, n_ = ndi.label(gro); seed_ = np.unique(lab_[gro & (dagc < AGC_R)]); seed_ = seed_[seed_ > 0]
    cand_agc = np.isin(lab_, seed_); del lab_
    cand = cand | cand_agc
    print('  + %.1f ha of grey apron connected to them (<= %.0f m)' % ((cand_agc & ~cand_old & (dagc >= AGC_R)).sum() * RES * RES / 1e4, AGC_GROW))
    # the hole fill, the parking-point hole fill and the gaussian step (shape()) run twice: on the pre-round-3 pixels
    # (p_old: what the rules up to round 2 give) and on the full set. Fix round 2 (2026-11-08, verifier finding v2): the
    # OSM building footprints (not building=roof) and the app's runway end zones are never filled as holes and never grown
    # into by the smoothing, and at the end every pixel there that p_old does not have is removed - so the round-3 / fix-2
    # rules add NOTHING there (round 1 applied the exclusion before those steps only: OSM way 1473685129, 1,314 m2 with a
    # solar roof at (-1398, -2040), was paved whole by the hole fill, and 907 m2 entered the end zones)
    pcore = np.zeros((H, W), np.uint8)              # the parking points themselves (12 m discs) for the larger hole limit
    for q in pts_:
        if not q: continue
        c_ = P([q])[0]
        if 0 <= c_[0] < W and 0 <= c_[1] < H: cv2.circle(pcore, (int(c_[0]), int(c_[1])), int(12 / RES), 1, -1)
    excl = (obld > 0) | (ezm > 0)
    def shape(p, xf):
        p = ndi.binary_opening(p, iterations=3)
        lab, n = ndi.label(p); sz = ndi.sum(p, lab, range(1, n + 1))
        p = np.isin(lab, 1 + np.nonzero(sz * RES * RES >= 300)[0])
        holes = ndi.binary_fill_holes(p) & ~p
        lh, nh = ndi.label(holes); hs = ndi.sum(holes, lh, range(1, nh + 1))
        hp = ndi.sum(pcore > 0, lh, range(1, nh + 1))
        fillh = np.isin(lh, 1 + np.nonzero((hs * RES * RES < 3000) | ((hs * RES * RES < 12000) & (hp > 0)))[0])
        del lh, holes
        p |= fillh & ~xf if xf is not None else fillh
        pg = ndi.gaussian_filter(p.astype(np.float32), 1.0 / RES) > 0.5
        p = pg & (p | ~xf) if xf is not None else pg
        p &= (pav == 0) | (dpav > 0)
        lab, n = ndi.label(p); sz = ndi.sum(p, lab, range(1, n + 1))
        p = np.isin(lab, 1 + np.nonzero(sz * RES * RES >= 300)[0])
        p |= (holdm > 0) & (pav == 0) & (bld == 0)          # the measured hold bars are on pavement by definition
        return p
    p_old = shape((grey | g) & (pav == 0) & (bld == 0) & cand_old, None)
    p = shape((grey | g | envadd) & (pav == 0) & (bld == 0) & cand, excl)
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
    p |= addf; p_old |= addf
    # close-out round 3 (finding static-1) (c): the ARFF apron (-1569, -600) round the Rescue 41 stay - fire trucks and
    # parking stripes on a tan, smooth surface (HSV S 25-35, texture 0.9) fail grey (S < 32) + smooth, and it is not a hole
    # in the pavement (it borders the station and the service road), so hole filling cannot reach it. Within PAD_R m of a
    # VEHICLE stay, pixels that are smooth (texture < PAD_LAP), unsaturated (S < PAD_SMAX), not vegetation / bare soil /
    # a mapped (SFO Museum or OSM) building, and CONNECTED to the pavement are pavement (not a footprint: FM8's disc on the
    # infield soil adds nothing - its soil is rough, texture 4.7). Inferred.
    pad = np.zeros((H, W), np.uint8)
    for v in vstays:
        c_ = P([[v['x'], v['z']]])[0]
        if 0 <= c_[0] < W and 0 <= c_[1] < H: cv2.circle(pad, (int(c_[0]), int(c_[1])), int(PAD_R / RES), 1, -1)
    # ... or (the striped / cluttered part of the same apron) inside a 25 m window that is >= PAD_GREY grey and <= PAD_SOIL
    # soil / <= ENV_SOIL vegetation (the cell classes of (b)): the ARFF apron round R41 (-1565, -592) 62 % grey / 3 % soil
    # and the OPS44 pad (-320, 1496) 82 % / 1 % qualify; the vehicle discs on the infield soil (FM8 63 %, OPS12 16 %,
    # OPS31 23 %, OPS40 79 % soil) do not
    wsoil_, wveg_ = wmean(gsoil), wmean(gveg)
    padw = (wmean(ggrey) >= PAD_GREY) & (wsoil_ <= PAD_SOIL) & (wveg_ <= ENV_SOIL) & ~gsoil & ~gveg
    padc = (pad > 0) & (((lap < PAD_LAP) & (S < PAD_SMAX)) | padw) & ~vegc & ~soilc & (bld == 0) & (obld == 0) & (pav == 0) & ~p
    padc = ndi.binary_opening(padc, iterations=2)
    lab_, n_ = ndi.label(padc | p | (pav > 0)); keep_ = np.unique(lab_[p | (pav > 0)]); keep_ = keep_[keep_ > 0]
    padadd = padc & np.isin(lab_, keep_)
    print('vehicle-stay pads: +%.2f ha (%d stays)' % (padadd.sum() * RES * RES / 1e4, len(vstays)))
    p |= padadd
    # close-out round 5 (2026-11-08, verifier finding of close-out 3 fix 2): the FORECOURT of a vehicle stay's building - the
    # ARFF apron's striped tan bays between the Rescue 41 station doors and the pavement (426 m2 at (-1563, -598); NAIP median
    # RGB 214 / 203 / 184, spread 20, R - B 30: neither soil (R - B > 38) nor grey, and the parking stripes / fire trucks fail
    # the 3 m texture test - which is why (c) left it; the round-3 text's 'tan reads as soil' was wrong). Within PAD_R of a
    # vehicle stay AND within FC_R m of a mapped building (SFO Museum / OSM footprint), a pixel that is not part of a soil /
    # vegetation patch (soilc / vegc: openings, so thin paint stripes and vehicles do not count) and whose 25 m window holds
    # <= PAD_SOIL soil and <= ENV_SOIL vegetation is pavement - no texture or pixel-colour test - when connected to the
    # pavement; a 1 m closing inside the forecourt fills the stripe gaps. Measured on the round-3 fix-2 masks: +370 m2 at
    # R41, 0 at the other 17 vehicle stays (their discs are not beside a building or are already paved); without the
    # building condition the same relaxation would also pave 101 m2 of dusty verge at OPS15 (874, -842) - rejected. Inferred.
    fcadd = np.zeros((H, W), bool); N_FC = 0
    obd = (bld > 0) | (obld > 0)
    rad = int(PAD_R / RES) + int(FC_R / RES) + 4
    for v in vstays:
        c_ = P([[v['x'], v['z']]])[0]; cx_, cy_ = int(c_[0]), int(c_[1])
        r0_, r1_, c0_, c1_ = max(0, cy_ - rad), min(H, cy_ + rad + 1), max(0, cx_ - rad), min(W, cx_ + rad + 1)
        if r1_ <= r0_ or c1_ <= c0_: continue
        sl_ = (slice(r0_, r1_), slice(c0_, c1_))
        disc_ = np.zeros((r1_ - r0_, c1_ - c0_), np.uint8); cv2.circle(disc_, (cx_ - c0_, cy_ - r0_), int(PAD_R / RES), 1, -1)
        k_ = 2 * int(FC_R / RES) + 1
        fcz = (cv2.dilate(obd[sl_].astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_, k_))) > 0) & (disc_ > 0) & ~obd[sl_]
        if not fcz.any(): continue
        paved_ = p[sl_] | (pav[sl_] > 0)
        cand_ = fcz & (wsoil_[sl_] <= PAD_SOIL) & (wveg_[sl_] <= ENV_SOIL) & ~vegc[sl_] & ~soilc[sl_] & ~paved_
        cand_ = ndi.binary_opening(cand_, iterations=2)
        lab_, n_ = ndi.label(cand_ | paved_); keep_ = np.unique(lab_[paved_]); keep_ = keep_[keep_ > 0]
        add_ = cand_ & np.isin(lab_, keep_)
        add_ |= ndi.binary_closing(add_ | paved_, iterations=2) & fcz & ~vegc[sl_] & ~soilc[sl_] & ~paved_
        if add_.any(): fcadd[sl_] |= add_; N_FC += 1
    print('vehicle-stay forecourts (close-out round 5): +%.0f m2 at %d stays' % (fcadd.sum() * RES * RES, N_FC))
    p |= fcadd; del obd, wsoil_, wveg_
    # (h) close-out round 7 (2026-11-09, realtime request C5.3): ADS-B SIGNAL-END parking footprints. Where an aircraft's
    # position signal ended on the ground (refs/cache/stands/adsb_ground_cells.json `signal_end`: last ground fix at < 3 kt,
    # then >= 30 min without a position fix - the transponder goes off at the stop, so the ground cells hold one or two fixes
    # there) the app keeps the aircraft parked for hours: ASA503 B39M stood 11 h on the light concrete hangar apron at
    # (-2090.5, -687.3) (west maintenance area), off the rendered mask (NAIP there: 98 % grey, S median 24, R - B 18, no
    # soil, but only 54 % 'smooth' - joints / stains - and the 2024 aircraft on it break the 25 m windows). A SE_R disc round
    # each such point is pavement where NAIP shows no vegetation / soil / water and no mapped building (the parking-footprint
    # tests above), when it connects to the pavement and the added piece is clean (<= 5 % soil + vegetation, >= 60 % grey).
    # Inferred; `src` gives the m2.
    try:
        se_ = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'stands', 'adsb_ground_cells.json'))).get('signal_end') or []
    except (OSError, ValueError):
        se_ = []
    sed = np.zeros((H, W), np.uint8); N_SE = 0
    for q in se_:
        c_ = P([[q[0], q[1]]])[0]
        if 0 <= c_[0] < W and 0 <= c_[1] < H: cv2.circle(sed, (int(c_[0]), int(c_[1])), int(SE_R / RES), 1, -1); N_SE += 1
    Bw, Gw, Rw = img[..., 0].astype(np.int16), img[..., 1].astype(np.int16), img[..., 2].astype(np.int16)
    sew_ = (Bw > Rw + 10) & ((Bw + Gw + Rw) // 3 < 120); del Bw, Gw, Rw
    secand = (sed > 0) & ~vegc & ~soilc & ~sew_ & (bld == 0) & (pav == 0) & ~excl & (V > 40) & ~p; del sed, sew_
    lse_, nse_ = ndi.label(secand | p | (pav > 0))
    seadd = secand & np.isin(lse_, np.unique(lse_[p | (pav > 0)])); del lse_, secand
    # each added piece must itself be clean pavement on NAIP (the (f) shares): <= 5 % soil + vegetation (unopened reviewer
    # classes) and >= 60 % grey (incl. bright unsaturated concrete) - the first version also paved dusty verges (20-30 % soil)
    lpe_, npe_ = ndi.label(seadd, np.ones((3, 3), bool)); ipe_ = np.arange(1, npe_ + 1); ape_ = np.maximum(ndi.sum(seadd, lpe_, ipe_), 1)
    sve_ = ndi.sum(gsoil | gveg, lpe_, ipe_) / ape_; gre_ = ndi.sum(ggrey | ((V >= 245) & (S < 32)), lpe_, ipe_) / ape_
    oke_ = (sve_ <= 0.05) & (gre_ >= 0.6)
    print('(h) ADS-B signal-end parking footprints (close-out round 7): %d points, %d of %d pieces clean, +%.0f m2 (dropped %.0f m2)' % (
        N_SE, int(oke_.sum()), npe_, float(ape_[oke_].sum()) * RES * RES, float(ape_[~oke_].sum()) * RES * RES))
    seadd = np.isin(lpe_, ipe_[oke_]); del lpe_
    p |= seadd
    # (f) fix round 2 (2026-11-08, verifier finding v3): holes ENCLOSED by the paved union (this pavement, SFO Museum
    # pavement / the inferred apron, buildings, OSM buildings, the end zones) where aircraft were on the ground (an ADS-B
    # aircraft ground cell with >= 2 fixes inside, rule (a)'s cells) or a vehicle stayed (the ARFF apron), NAIP <= 5 % soil
    # + vegetation, <= 20 % water-blue and >= 60 % grey (the reviewer classes), < 12000 m2 (the parking-point hole limit)
    # are pavement: the north cargo taxilane (-405, -967) - 4,285 m2, 35 fixes, NAIP 92 % grey but only 3 % 'smooth' (the
    # painted centreline and tyre marks fail the texture test) - and the smaller holes the verifier listed. Inferred.
    U_ = p | (pav > 0) | (bld > 0) | excl
    hol = ndi.binary_fill_holes(U_) & ~U_; del U_
    lh, nh = ndi.label(hol); idx_ = np.arange(1, nh + 1)
    ha_ = ndi.sum(hol, lh, idx_); hpx_ = np.maximum(ha_, 1)
    vs_ = np.zeros((H, W), np.uint8)
    for v in vstays:
        c_ = P([[v['x'], v['z']]])[0]
        if 0 <= c_[0] < W and 0 <= c_[1] < H: vs_[int(c_[1]), int(c_[0])] = 1
    Bw, Gw, Rw = img[..., 0].astype(np.int16), img[..., 1].astype(np.int16), img[..., 2].astype(np.int16)
    wat_ = (Bw > Rw + 10) & ((Bw + Gw + Rw) // 3 < 120); del Bw, Gw, Rw
    sv_ = ndi.sum(gsoil | gveg, lh, idx_) / hpx_; gr_ = ndi.sum(ggrey, lh, idx_) / hpx_; wa_ = ndi.sum(wat_, lh, idx_) / hpx_
    ev_ = ndi.sum(agc > 0, lh, idx_) + ndi.sum(vs_ > 0, lh, idx_)
    ok_ = (ha_ * RES * RES < 12000) & (ev_ > 0) & (sv_ <= 0.05) & (wa_ <= 0.2) & (gr_ >= 0.6)
    holeadd = np.isin(lh, idx_[ok_]) & (pav == 0) & (bld == 0) & ~excl
    print('(f) enclosed holes with aircraft / vehicle evidence: %d of %d holes with evidence filled, +%.2f ha' % (
        int(ok_.sum()), int((ev_ > 0).sum()), (holeadd & ~p).sum() * RES * RES / 1e4))
    p |= holeadd; del lh, hol, wat_, vs_
    # (g) fix round 2 (verifier finding v5): the old-J island of FAA AL-375 cycle 2611 is ONE paved island (finding static-3:
    # the chart island, refs/cache/faa/al375_2611_oldJ.json white_polys); the part of it that is neither SFO Museum taxiway
    # pavement, the inferred green paint (below) nor already pavement - the pale interiors inside the painted rings, NAIP
    # 2024 (flown before the rebuild) median RGB 199/207/183, unpainted - is paved too (concrete, inferred)
    FJ_ = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'faa', 'al375_2611_oldJ.json')))
    islm = np.zeros((H, W), np.uint8); fill(islm, FJ_['white_polys'])
    isladd = (islm > 0) & (pav == 0) & (bld == 0) & ~excl & ~p
    print('(g) old-J chart island interior: +%.0f m2 (inferred)' % (isladd.sum() * RES * RES))
    p |= isladd
    # the exclusion of fix round 2: OSM buildings / end zones keep exactly what the pre-round-3 rules gave them
    p = (p & ~excl) | (p_old & excl)
    new_rule = p & ~p_old & ~holeadd & ~isladd & ~fcadd & ~seadd     # round 3 additions (for src)
    r7_rule = p & seadd & ~p_old                      # close-out round 7: signal-end parking footprints (for src)
    r5_rule = p & fcadd & ~p_old                      # close-out round 5: vehicle-stay forecourts (for src)
    f2_rule = p & (holeadd | isladd) & ~p_old       # fix-round-2 additions (for src)
    del p_old
    pave_polys, conc = [], []; SRC_C = []
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
        nr = float(new_rule[m].mean()); n2 = float(f2_rule[m].mean()); a5 = float(r5_rule[m].sum()) * RES * RES
        a7 = float(r7_rule[m].sum()) * RES * RES
        for poly in polys:
            pave_polys.append(poly); conc.append(bool(vmed >= 150))
            s_ = 'naip'
            if nr >= 0.1: s_ += ('; %.0f %% from the close-out round 3 rules (cluttered-apron / any-window / bright-concrete envelope / '
                                 'ADS-B aircraft ground cells / vehicle-stay pad: inferred)' % (100 * nr))
            if n2 >= 0.01: s_ += ('; %.0f %% from the fix-round-2 rules (holes enclosed by pavement with ADS-B aircraft / vehicle evidence, '
                                  'the old-J chart island interior: inferred)' % (100 * n2))
            if a5 > 0: s_ += ('; %.0f m2 from the close-out round 5 rule (vehicle-stay forecourt beside a mapped building: inferred)' % a5)
            if a7 > 0: s_ += ('; %.0f m2 from the close-out round 7 rule (h) (ADS-B signal-end parking footprint, adsb.lol: inferred)' % a7)
            SRC_C.append(s_)
        big.append((round(len(ys) * RES * RES), world((xs.mean(), ys.mean())), round(vmed)))
    big.sort(reverse=True)
    # static close-out (2026-11-04): taxiways built after NAIP 2024 (data/sfo_details.json centrelines with src
    # 'osm_update' and a width: the relocated W) are paved as the centreline buffered by half their (inferred) width -
    # NAIP cannot show them; src per polygon in `src`
    from shapely.geometry import LineString as _LS
    srcs = list(SRC_C)
    for cl_, m_ in zip(Dt.get('centerlines', []), Dt.get('centerlineMeta', [])):
        if m_.get('src') == 'osm_update' and m_.get('width_m') and len(cl_) >= 2:
            g_ = _LS(cl_).buffer(m_['width_m'] / 2, cap_style=2, join_style=1).simplify(0.2)
            pave_polys.append([[[round(x, 2), round(z, 2)] for x, z in list(g_.exterior.coords)[:-1]]]); conc.append(False)
            srcs.append('osm_update %s (%s, width %s)' % (m_.get('osm_id'), m_.get('ref'), m_['width_m']))
    prov = ('tools/imagery/paint_pave_naip.py: colour classification of USDA NAIP 2024 (public domain, flown 2024-05-20, '
            '0.5 m world raster), 24 Sep 2026; static close-out 2026-11-04 (parking-position candidates / footprints, the relocated W); '
            'close-out round 3 2026-11-06 / 07, rules (a)-(e): candidate area round the adsb.lol aircraft ground cells '
            '(refs/cache/stands/adsb_ground_cells.json, ODbL), cluttered-apron / any-window / bright-concrete envelopes, vehicle-stay '
            'pads (adsb.lol stays, ODbL); fix round 2 2026-11-08: (f) holes enclosed by pavement with ADS-B aircraft / vehicle '
            'evidence, (g) the interior of the old-J island of FAA AL-375 cycle 2611 (public domain); close-out round 5 2026-11-08: '
            'vehicle-stay forecourts beside a mapped building (the ARFF bays); close-out round 7 2026-11-09: (h) parking footprints '
            'round the adsb.lol signal-end points (refs/cache/stands/adsb_ground_cells.json signal_end, ODbL); OSM building footprints '
            '(not building=roof; OSM, ODbL) and the runway end zones of js/live/airport.js END_ZONES keep exactly the pre-round-3 '
            'pavement after every step (no round-3 / fix-2 addition there). Per-polygon `src` gives the inferred share')
    # close-out round 3 (2026-11-06, finding static-3): the western remainder of the old taxiway J (deleted in OSM changeset
    # 189525528) lies in ONE island on FAA AL-375 cycle 2611 (tools/xcheck/faa_al375_mask.py white_polys, 5,575 m2) that also
    # takes in the two green-painted islands either side of it; the chart draws painted (paved) islands white too, and
    # airport-operations vehicles cross the band (round-2 verifier: 36 ground fixes from OPS44 / OPS12 / OPS30 / R69, 0
    # aircraft). So the island is one paved surface and its FORMER TAXI SURFACE - the SFO Museum taxiway pavement inside
    # the chart island (the old-J band and its fillets; the painted islands are holes of those polygons) - is drawn with
    # green no-taxi paint like the islands it joins. INFERRED: NAIP 2024 (flown before the rebuild) cannot show it; `src`.
    paint_src = ['naip'] * len(paint_polys)
    from shapely.geometry import Polygon as _SP
    from shapely.ops import unary_union as _SU
    FJ = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'faa', 'al375_2611_oldJ.json')))
    _ret = {(r_['name'], r_['poly']) for r_ in Dt.get('pavementRetired', []) if r_['layer'] == 'taxiways'}
    _isl = _SU([_SP(q).buffer(0) for q in FJ['white_polys']])
    _tw = _SU([_SP(pp[0], pp[1:]).buffer(0) for t in A['taxiways'] for i_, pp in enumerate(t['polys']) if (t['name'], i_) not in _ret])
    _new = _isl.intersection(_tw)
    if paint_polys: _new = _new.difference(_SU([_SP(pp[0], pp[1:]).buffer(0) for pp in paint_polys]))
    N_ISL = [0, 0.0]
    for _g in [g_ for g_ in getattr(_new, 'geoms', [_new]) if g_.geom_type == 'Polygon' and g_.area >= 20.0]:
        _g = _g.simplify(0.2)
        paint_polys.append([[[round(x, 1), round(z, 1)] for x, z in list(_g.exterior.coords)[:-1]]] +
                           [[[round(x, 1), round(z, 1)] for x, z in list(h.coords)[:-1]] for h in _g.interiors if _SP(h).area > 5])
        paint_src.append('inferred: the old-J island of FAA AL-375 cycle 2611 (refs/cache/faa/al375_2611_oldJ.json) on former SFO Museum '
                         'taxiway pavement - one paved island with the two painted islands it joins; vehicles cross it (ADS-B); built after NAIP 2024')
        N_ISL[0] += 1; N_ISL[1] += _g.area
    print('old-J island paint (inferred): %d polygons, %.0f m2' % (N_ISL[0], N_ISL[1]))
    paint = {'frame': GF.FRAME_ID, 'note': 'Green no-taxi island paint (FAA AC 150/5340-1M para 1.5.2) classified on USDA NAIP 2024 '
             '(hue 140-180, S > 55, V > 150; within 30 m of SFO Museum taxiway/runway pavement); src per polygon: naip, or inferred '
             '(the old-J island of FAA AL-375 cycle 2611, built after NAIP 2024).',
             'provenance': ('tools/imagery/paint_pave_naip.py: colour classification of USDA NAIP 2024 (public domain, flown 2024-05-20, '
                            '0.5 m world raster), 24 Sep 2026; close-out round 3 2026-11-06: + the inferred old-J island polygon (FAA AL-375 '
                            'cycle 2611, public domain, on SFO Museum taxiway pavement)'),
             'polys': paint_polys, 'src': paint_src}
    pave = {'frame': GF.FRAME_ID, 'note': 'Paved areas not in the SFO Museum geometry (cargo/maintenance aprons, service roads, '
            'shoulders) classified on USDA NAIP 2024 (grey pixels within 60 m of mapped pavement, of OSM aprons / taxi centrelines '
            '(40 m) or of aircraft parking positions / ADS-B parked stays (60 m; static close-out 2026-11-04), outside mapped buildings); '
            'close-out round 3 (inferred, share in src): (a) also within 60 m of adsb.lol aircraft ground cells and the grey apron '
            'connected to them (150 m); (b) cluttered aprons inside >= 88 % grey / <= 3 % soil 25 m windows; (c) vehicle-stay pads; '
            '(d) bright concrete next to cells with >= 2 aircraft; (e) near-neutral pixels inside any qualifying window; fix round 2: '
            '(f) holes enclosed by pavement that held ADS-B aircraft (or a vehicle stay), NAIP <= 5 % soil / vegetation, >= 60 % grey, '
            '< 12000 m2; (g) the old-J island interior of FAA AL-375 2611; close-out round 5: vehicle-stay forecourts (<= 15 m from a mapped building, '
            'no texture test: the ARFF bays); close-out round 7: (h) 25 m parking footprints round adsb.lol signal-end points (last ground '
            'fix < 3 kt, then >= 30 min silent; no vegetation / soil / water / building, connected, each piece <= 5 % soil + vegetation and >= 60 % grey). OSM building footprints (not building=roof) and the app\'s '
            'runway end zones (END_ZONES) take none of these additions. The relocated W: OSM centreline buffered by its inferred width '
            '(src osm_update). conc = concrete (median V >= 150). Unmapped grey roofs can be included (inferred). Contains information '
            'from OpenStreetMap (c) OpenStreetMap contributors and from adsb.lol, made available under the ODbL 1.0 (docs/ATTRIBUTION.md).',
            'provenance': prov, 'licence': 'ODbL 1.0 (OSM and adsb.lol inputs); NAIP / FAA inputs public domain - docs/ATTRIBUTION.md',
            'polys': pave_polys, 'conc': conc, 'src': srcs}
    HDR = {'paint': '// generated by tools/imagery/paint_pave_naip.py from USDA NAIP 2024 (public domain); one inferred polygon from FAA '
                    'AL-375 2611 (public domain) on SFO Museum taxiway pavement (CDLA-Permissive-1.0, https://cdla.dev/permissive-1-0/; '
                    'changed by sfo3d: clipped to the chart island) - docs/ATTRIBUTION.md',
           'pavement': '// generated by tools/imagery/paint_pave_naip.py from USDA NAIP 2024 (public domain), with candidate areas / '
                       'exclusions from OpenStreetMap (c) OpenStreetMap contributors and from adsb.lol (both ODbL 1.0: contains information '
                       'from OpenStreetMap and adsb.lol, made available under the ODbL) and FAA AL-375 2611 (public domain) - docs/ATTRIBUTION.md'}
    for name, var, res in (('paint', 'PAINT', paint), ('pavement', 'PAVEMENT', pave)):
        blob = json.dumps(res, separators=(',', ':'))
        open(os.path.join(ROOT, 'data', f'sfo_{name}.json'), 'w').write(blob)
        open(os.path.join(ROOT, 'data', f'sfo_{name}.js'), 'w').write(HDR[name] + '\nexport const ' + var + ' = ' + blob + ';\n')
    print('paint: %d polygons, %.1f ha' % (len(paint_polys), g.sum() * RES * RES / 1e4))
    print('pavement: %d polygons, %.1f ha, concrete %d' % (len(pave_polys), p.sum() * RES * RES / 1e4, sum(conc)))
    print('largest pavement components (m2, centre, median V):', big[:12])
    if dump:
        np.savez_compressed(dump, x0=x0, z0=z0, res=RES, grey=grey, cand=cand, p=p, pav=pav > 0, bld=bld > 0, vegc=vegc, soilc=soilc,
                            g=g, foot=foot > 0, park=park > 0, oap=oap > 0, smooth=lap < 3.5, S=S, V=V)
        print('dump ->', dump)
    if preview:
        vis = (img // 2).copy()
        vis[p] = (vis[p] * 0.4 + np.array([40, 200, 255]) * 0.6).astype(np.uint8)
        vis[g] = (vis[g] * 0.3 + np.array([255, 0, 255]) * 0.7).astype(np.uint8)
        cv2.imwrite(os.path.join(ROOT, 'refs', 'cache', 'naip', 'paint_pave_preview.jpg'), cv2.resize(vis, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA))


AGC_R, AGC_GROW = 60.0, 150.0   # m: candidate disc round an ADS-B aircraft ground cell (as the stays), grey-connected growth
ENV_WIN = 50              # px (25 m at 0.5 m): the cluttered-apron window (close-out round 3, finding static-1)
ENV_GREY, ENV_SOIL, ENV_SMOOTH = 0.88, 0.03, 0.5
PAD_R, PAD_LAP, PAD_SMAX = 25.0, 3.0, 45   # vehicle-stay pads: radius (m), texture and HSV saturation limits
PAD_GREY, PAD_SOIL = 0.6, 0.05             # ... or a 25 m window this grey with at most this much soil
SE_R = 25.0               # m: close-out round 7 (h) signal-end parking footprint radius (= the ADS-B parked-stay disc)
FC_R = 15.0               # m: close-out round 5 vehicle-stay forecourt - pad pixels this close to a mapped building (the ARFF bays: <= 12 m)
AC_R = 10.0               # m: (d) bright-concrete envelope only this close to a cell with >= 2 aircraft (2 ADS-B cells' width)
ENV_EXT_SPR, ENV_EXT_RB, ENV_EXT_SMW = 30, 25, 10   # (e) any-window envelope: channel spread, R - B, local smooth window (px = 5 m)


def end_zone_rings():
    """the app's runway end zones (js/live/airport.js END_ZONES / EMAS_SETBACK / EMAS_W, parsed from the file so the two
    cannot drift; RWY_W 60.96 m = js/world/airfield.js) as world rectangles beyond each runway end (FAA NASR ends,
    tools/geo_frame.py RWY_ENDS = js/geo.js; rw index = js/geo.js RUNWAYS order). Blast pad: runway width x len; EMAS:
    (EMAS_W + 4) x (setback + len + 3), the app's own margins."""
    src = open(os.path.join(ROOT, 'js', 'live', 'airport.js')).read()
    body = re.search(r'export const END_ZONES = \[(.*?)\];', src, re.S).group(1)
    setback = float(re.search(r'EMAS_SETBACK = ([0-9.]+)', src).group(1)); emas_w = float(re.search(r'EMAS_W = ([0-9.]+)', src).group(1))
    rings = []
    for z in re.finditer(r'\{([^}]*)\}', body):
        kv = dict((k.strip(), float(v)) for k, v in re.findall(r'(\w+):\s*([-0-9.]+)', z.group(1)))
        a_, b_ = GF.RWY_PAIRS[int(kv['rw'])]; e_, o_ = (a_, b_) if int(kv['end']) == 0 else (b_, a_)
        pe, po = np.array(GF.end_world(e_)), np.array(GF.end_world(o_)); d = (pe - po) / np.linalg.norm(pe - po); n = np.array([-d[1], d[0]])
        L, hw = (kv['len'], 60.96 / 2) if int(kv['type']) == 1 else (setback + kv['len'] + 3, emas_w / 2 + 2)
        rings.append([list(pe + n * hw), list(pe + d * L + n * hw), list(pe + d * L - n * hw), list(pe - n * hw)])
    return rings


def osm_buildings(fill, H, W):
    """OSM building footprints (pinned extract refs/cache/osm/overpass_ksfo_at_*.json, ODbL) except building=roof (open
    canopies over pavement), filled into a mask grown by 1 px - kept out of the close-out round 3 additions only (the
    existing classification is unchanged)"""
    m = np.zeros((H, W), np.uint8)
    meta = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_ksfo_latest.meta.json')))
    for e in json.load(open(os.path.join(ROOT, 'refs', 'cache', 'osm', meta['file'])))['elements']:
        t = e.get('tags') or {}
        if e['type'] != 'way' or 'building' not in t or t['building'] == 'roof' or len(e.get('geometry') or []) < 4: continue
        fill(m, [[GF.wgs84_to_world(q['lat'], q['lon']) for q in e['geometry']]])
    return cv2.dilate(m, np.ones((3, 3), np.uint8))


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
    main('--preview' in sys.argv, sys.argv[sys.argv.index('--dump') + 1] if '--dump' in sys.argv else None)
