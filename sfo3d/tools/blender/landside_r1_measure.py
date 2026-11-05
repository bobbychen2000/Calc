"""Round-1 review measurements of the 3-D landside group (NAIP 2024 + the reference photos, measured by the 3-D group; the
2-D sheets BL-01..03 do not carry these items yet: each one is listed in data/buildings3d/manifest.json#landside as a
'r1_observation' with its tag, and raised with the drawings group in docs/research/buildings3d.md, landside open items).

    python3 tools/blender/landside_r1_measure.py        -> tools/blender/landside_r1_obs.json (read by landside_geom.py)

NAIP 2024 (public domain, refs/cache/naip, flown 2024-05-20 ~13:14 PDT: sun az 186.5 deg, el 72.5 deg, tools/buildings/
dom_sun.py) is used ONLY to measure plan positions / colours (never as a texture). Relief: imaged roofs lean east by
k(x) = 0.7553 + 0.0002753 x metres per metre of height (docs/research/buildings_itb.md s.2.2, draw_data.k_x_model).

Items (tag in brackets):
  cg_roof     Central Parking Garage roof: beige rim / curb polygons [obs NAIP colour segmentation], smooth stall-free lobes
              [obs NAIP: bright, low local variance, >= 150 m2], rooftop stair / elevator / plant boxes [obs NAIP, picked at
              0.125 m/px; size +-2 m; heights inf], parked cars at the NAIP-detected dark / coloured blob positions [obs NAIP]
              (white / silver cars are not separable from the light deck at 0.5 m: added near the detected clusters by the
              fleet share, inf)
  bart        SFO BART station body (Building 497, integral with the Garage G AirTrain station [pub spec garage_g_identity]):
              the north edge of the station complex from the NAIP shadow line [obs], the station roof vault over the AirTrain
              platform [obs NAIP white roof, a2], the 3-track aerial approach from the WSW [obs NAIP rails]; heights [inf, a2
              proportions; unk]
  hyatt       Grand Hyatt slab east face along the podium (relief-corrected NAIP roof edge) [obs NAIP, approx]
  photos      numbers read off the reference photos (l1 station block, i2 drums / towers, l5 camera solve)
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
OUT = os.path.join(HERE, 'landside_r1_obs.json')

SUN = dict(az=186.5, el=72.5, shadow_per_m=0.315, src='tools/buildings/dom_sun.py for 2024-05-20 13:14 PDT (NAIP item m_3712229_ne_10_060_20240520)')

# ------------------------------------------------------------------------------------------------ hand-picked (NAIP 0.125 m/px)
# Central-garage rooftop boxes, IMAGED corners (x0, z0, x1, z1) picked on NAIP 2024 at 8 px/m with a 5-m grid; the roof shift
# used for the deck (+4.0 m east, landside_naip_measurements cg roof_cars) is removed below. kind: 'tower' = stair / elevator
# head (bright or dark roof with shading on its north side), 'plant' = low equipment group.
CG_BOXES = [
    ((-976.0, 186.0, -965.0, 197.0), 'tower', 'N petal end: white roof on the beige pad'),
    ((-977.0, 176.0, -965.0, 186.0), 'plant', 'N petal end: equipment north of the white box'),
    ((-1042.0, 215.0, -1026.0, 230.0), 'tower', 'NW: grey / dark box'),
    ((-911.0, 170.0, -899.0, 195.0), 'tower', 'N: dark-roofed box'),
    ((-870.0, 238.0, -856.0, 250.0), 'tower', 'E petal end: white roof on the beige ring'),
    ((-856.0, 236.0, -841.0, 249.0), 'plant', 'E petal end: equipment'),
    ((-1017.0, 265.0, -1001.0, 285.0), 'tower', 'W of the void: grey box'),
    ((-1000.0, 339.0, -981.0, 364.0), 'tower', 'SW: dark / grey box pair'),
    ((-926.0, 349.0, -914.0, 358.0), 'tower', 'S petal end: white roof on the beige ring'),
    ((-920.0, 365.0, -901.0, 384.0), 'plant', 'S petal end: grey block / equipment'),
    ((-876.0, 301.0, -848.0, 313.0), 'plant', 'SE: equipment group'),
]
TOWER_ABOVE_DECK = 4.5     # stair / elevator head above the deck: one overrun storey [inf] (NAIP shading too short to resolve)
PLANT_ABOVE_DECK = 2.0     # equipment groups [inf]

# BART station complex (Building 497), picked on NAIP 2024 at 6 px/m: the dark band north of the complex is the cast shadow
# (0.27 h north of the wall foot) + the shaded north wall (seen with the east lean: its top images 0.15 h SSE of its foot);
# north wall line = the band's south edge (imaged roof edge) moved 1.0 m NNW (h ~20 m would give 3 m; the SFO Museum guideway
# north edge lies on the band edge: +-2 m) [obs NAIP, approx]; the east end meets the ITB outline (x ~ -1336), the west end is
# where the shared BART / AirTrain corridor enters (x ~ -1592)
BART_NORTH = [(-1592.3, 326.55), (-1555.3, 315.75), (-1463.3, 284.85), (-1380.3, 256.55), (-1336.3, 246.55)]
# the 3-track aerial approach west of the station: rails visible at z 344-362 from x -1592 to the wye at x ~ -2110 [obs NAIP];
# beyond the wye the two branches (north to San Bruno, south loop to Millbrae) are not modelled
BART_APPROACH = dict(x=(-2110.0, -1592.0), z=(344.0, 362.0))
BART_LEVELS = dict(
    track=14.1,      # BART running rails: one level below the AirTrain platform [pub secondary, spec garage_g_station_note];
    #                  the platform at the foot of the station's glazed band (a2: 15.2 m, below) minus 1.1 m platform height [inf]
    band=(15.2, 18.15),   # glazed band on the north face: a2 proportions of the station face between the colonnade foot and
    #                       the AirTrain trough-wall top (20.85 m) [obs a2 ratios 0.127 / 0.273 of the face; heights inf]
    colonnade=4.3,   # open ground storey with columns (a2: columns below the white body, ~0.20 of the face) [obs a2; inf]
    pier_dx=9.0,     # colonnade column spacing (a2: ~12 bays over the vault length) [obs a2 count, inf]
)

# Grand Hyatt: imaged east edge of the slab roof along the podium (white roof, NAIP 8 px/m), relief-corrected by k(x) x 44 m
# (13.4 m east) -> the slab face behind the podium continues the outline's east face from its notch corner (-1639.7, 664.7)
HYATT_SLAB_EAST = dict(imaged=[(-1622.0, 660.0), (-1630.0, 680.0), (-1636.0, 700.0)], shift_x=13.4,
                       corner=(-1639.7, 664.7), src='NAIP 2024 slab-roof edge, relief-corrected (k(x) model); approx +-2 m')

PHOTOS = dict(
    l1_station_block=dict(
        scale='platform-door cabin door ~2.2 m high (100 px at the block face, 45.5 px/m) [inf scale, +-15 %]',
        top_above_platform=11.1, soffit_above_platform=3.1, slot_centre_above_platform=6.5, slot_h=1.2,
        ne_parapet_above_platform=None,   # first reading 12.0 m above the walkway: withdrawn (see note)
        sightline_depth_m=27.0,
        note='photo l1 (Garage A station from the east): a separate low block over both tracks, its top 11.1 m above the AirTrain '
             'walkway, two long dark slots at +6.5 m (one over the south overhang, one over the north portal; none over the '
             'central pier), the south part on two round columns (open under the soffit at +3.1 m); sky above the block: any '
             'part of the garage higher than the block stands >= 27 m behind its east face (camera ~30 m east of the face, eye '
             '+1.6 m). The curved NE garage wall next to it: a first reading of ~12.0 m above the walkway (~31.8 m) was '
             'withdrawn after the camera-matched comparison (render_landside view_l1: camera 28 m east of the face, the block width matched to 0.2 %): the 12.0-m reading took the receding left edge of the curved wall for its top; with the ring at 39.6 the rendered curved end reaches the frame top as in the photo - no conflict, the ring stays [unk, BL-03]'),
    i2_drums=dict(
        scale='drum diameter 32.4 m across 185 px (5.7 px/m) [obs BL-02 B R 16.2]',
        slot_tops_below_ring=[12.3, 18.4, 23.9, 29.4, 34.6], slot_h=1.6, top_opening_below_ring=(5.7, 7.6),
        tower_top_above_ring=3.0,
        note='photo i2 (from the AirTrain west of the garages, looking east): both drums in smooth light metal panels with five long '
             'horizontal dark slots and an open band near the top; white precast stair / elevator towers with small square windows '
             'at both ends of each drum, rising ~3 m above the drum ring; the long faces: continuous perforated screen panels'),
    l5_camera=dict(
        tower_px=dict(left=955, right=1305, top=183, base=949), horizon_y=820, vp_x=647, image=(1920, 1440),
        f_px=1442, f_src='26-mm-equivalent phone lens (diagonal 2400 px / 43.27 mm) [inf]',
        tower_D=4.7, tower_D_src='SFO Museum RCC station polygon: round lobe x -2282.8..-2278.1 at z -1076..-1071.6 [obs]',
        note='the tower subtends 350 px; with D 6.5 [inf, BL-02] the camera would stand inside the RCC; with the polygon lobe D 4.7 '
             'the lateral offset (6.6 m) puts it on the walkway at the guideway east edge (0.3 m inside the polygon): solved '
             'camera (-2276.6, -1092.7), 19.4 m from the tower, bearing 191.7 deg (yaw 185.5), eye 1.73 m above the platform; '
             'tower top (DOF 18.3) 8.6 m above the eye -> platform 8.0 m [obs l5 + DOF, low] (was 5.8 [inf] with D 6.5)'),
)


def k_x(x):
    return 0.7553 + 0.0002753 * x


def cg_roof():
    import cv2
    import draw_lib as DLb
    import landside_geom as G
    from shapely.geometry import Polygon
    from shapely import affinity
    A, T = DLb._naip(); R = T['res']
    full = G.sfom_union('Central Parking Garage')
    sh = (4.0, 0.0)
    x0, z0, x1, z1 = full.bounds
    c0 = int((x0 - T['x0']) / R) - 10; r0 = int((z0 - T['z0']) / R) - 10
    c1 = int((x1 - T['x0']) / R) + 30; r1 = int((z1 - T['z0']) / R) + 10
    im = np.asarray(A[r0:r1, c0:c1])[:, :, ::-1].astype(np.float32)
    H, W = im.shape[:2]
    toW = lambda cc, rr: (T['x0'] + (c0 + cc + 0.5) * R, T['z0'] + (r0 + rr + 0.5) * R)
    f = lambda ring: np.array([[((x - T['x0']) / R - 0.5 - c0), ((z - T['z0']) / R - 0.5 - r0)] for x, z in ring], np.float32)

    def raster(g):
        m = np.zeros((H, W), np.uint8)
        for p in G.polys(g):
            cv2.fillPoly(m, [np.round(f(p.exterior.coords) * 8).astype(np.int32)], 1, shift=3)
            for h in p.interiors: cv2.fillPoly(m, [np.round(f(h.coords) * 8).astype(np.int32)], 0, shift=3)
        return m
    import landside_airtrain as AT
    cut = unary([AT.RAIL] + [AT.ST_POLY[k] for k in ('T1', 'T2', 'T3')]).buffer(2.0)
    deck = raster(affinity.translate(full.buffer(-3.0).difference(cut), *sh))
    void_c = np.array([-930.8, 275.5])
    yy, xx = np.mgrid[0:H, 0:W]
    wx = T['x0'] + (c0 + xx + 0.5) * R - sh[0]; wz = T['z0'] + (r0 + yy + 0.5) * R - sh[1]
    ring = np.hypot(wx - void_c[0], wz - void_c[1]) < 56.0              # void + the helix ring road round it
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    Y = 0.299 * r + 0.587 * g + 0.114 * b
    sat = im.max(-1) - im.min(-1)
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    beige = (((r - b) > 22) & (r > 150) & ((g - b) > 8) & (deck > 0) & ~ring).astype(np.uint8)
    beige = cv2.morphologyEx(beige, cv2.MORPH_OPEN, k3)
    Yb = cv2.blur(Y, (7, 7)); Y2 = cv2.blur(Y * Y, (7, 7)); sd = np.sqrt(np.maximum(Y2 - Yb * Yb, 0))
    lobe = ((Yb > 228) & (sd < 5.0) & (deck > 0) & ~ring).astype(np.uint8)
    lobe = cv2.morphologyEx(lobe, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    lobe = cv2.morphologyEx(lobe, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))

    def vec(mask, min_area, simp=0.6):
        cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = []
        for c in cs:
            if cv2.contourArea(c) * R * R < min_area: continue
            pts = [toW(p[0][0], p[0][1]) for p in c]
            pts = [(x - sh[0], z - sh[1]) for x, z in pts]
            P = Polygon(pts).buffer(0).simplify(simp)
            P = P.intersection(full.buffer(-1.5))
            for q in G.polys(P):
                if q.area >= min_area:
                    out.append([[round(x, 2), round(z, 2)] for x, z in q.exterior.coords])
        return out
    rims = vec(beige, 6.0, 0.4)
    lobes = vec(lobe, 150.0, 1.0)
    # boxes (towers / plant), shift removed
    boxes = []
    for (bx0, bz0, bx1, bz1), kind, note in CG_BOXES:
        boxes.append(dict(rect=[round(bx0 - sh[0], 2), round(bz0, 2), round(bx1 - sh[0], 2), round(bz1, 2)], kind=kind,
                          above_deck=TOWER_ABOVE_DECK if kind == 'tower' else PLANT_ABOVE_DECK, note=note))
    box_mask = raster(unary(Polygon([(b['rect'][0] + sh[0], b['rect'][1]), (b['rect'][2] + sh[0], b['rect'][1]),
                                     (b['rect'][2] + sh[0], b['rect'][3]), (b['rect'][0] + sh[0], b['rect'][3])]).buffer(3.0) for b in boxes))
    # cars: dark or saturated blobs on the deck (not beige / lobes / boxes / ring)
    car = (((Y < 165) | (sat > 48)) & (deck > 0) & ~ring & (beige == 0) & (box_mask == 0)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(car, 8)
    cars = []
    CAR_PX = 34.0                                    # one car blob ~4.7 x 1.8 m = 8.5 m2 = 34 px at 0.5 m
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        w_, h_ = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        if not (9 <= a <= 260) or max(w_, h_) > 40: continue
        ys, xs = np.nonzero(lab == i)
        P = np.c_[xs, ys].astype(float); m0 = P.mean(0); P -= m0
        ev, evec = np.linalg.eigh(np.cov(P.T) + 1e-6 * np.eye(2))
        elong = math.sqrt(ev[1] / max(ev[0], 1e-6))
        v = evec[:, 1]                                                      # image (col, row) long axis
        hdg = math.degrees(math.atan2(v[0], -v[1])) % 180.0                 # world heading (x east, z south)
        rgb = im[lab == i].mean(0)
        k = max(1, int(round(a / CAR_PX)))
        if k == 1 or elong < 1.5:
            x, z = toW(m0[0], m0[1])
            cars.append(dict(x=round(x - sh[0], 2), z=round(z - sh[1], 2), hdg=round(hdg, 1), elong=round(elong, 2), px=int(a),
                             rgb=[int(v_) for v_ in rgb], merged=1))
            continue
        # a merged row of k cars side by side: spread them along the blob's long axis (2.6-m stalls), cars across it
        L = 4.0 * math.sqrt(ev[1])                                          # ~ blob length (px)
        for j in range(k):
            t = (j + 0.5) / k - 0.5
            q = m0 + v * t * L
            x, z = toW(q[0], q[1])
            cars.append(dict(x=round(x - sh[0], 2), z=round(z - sh[1], 2), hdg=round((hdg + 90.0) % 180.0, 1), elong=round(elong, 2),
                             px=int(a), rgb=[int(v_) for v_ in rgb], merged=k))
    return dict(roof_shift=list(sh), rims=rims, lobes=lobes, boxes=boxes, cars=cars,
                stats=dict(rim_m2=round(float(beige.sum()) * R * R, 1), lobe_m2=round(float(lobe.sum()) * R * R, 1),
                           deck_m2=round(float(deck.sum()) * R * R, 1), cars_detected=len(cars)),
                method='beige: R-B > 22, R > 150, G-B > 8 (3-px opening); lobes: 3.5-m mean > 228, s.d. < 5, 7.5-m opening; cars: '
                       'Y < 165 or saturation > 48, 9-260 px blobs (one car per 34 px; merged rows split along the blob axis), outside rims / boxes (+3 m) / the void ring (r < 56 m)')


OSM = os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_ksfo_latest.json')     # ODbL 1.0, (c) OpenStreetMap contributors (SOURCES.json)


def osm_buildings():
    """OpenStreetMap buildings (ODbL; refs/cache/osm/overpass_ksfo_latest.json): the SFO BART station way (cross-check of the NAIP
    plan + its height tags) and the large airport buildings no asset models (review r1, finding 'hangars / cargo')."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import geo_frame as GF
    import landside_geom as G
    import draw_data as DD
    from shapely.geometry import Polygon, box
    d = json.load(open(OSM))
    els = [e for e in d['elements'] if e['type'] == 'way' and e.get('tags', {}).get('building') and len(e.get('geometry') or []) >= 3]
    poly = lambda e: Polygon([GF.wgs84_to_world(p['lat'], p['lon']) for p in e['geometry']]).buffer(0)
    bart = next(e for e in els if e['id'] == 221663595)
    Pb = poly(bart)
    modelled = unary([Polygon(p[0], p[1:]).buffer(0) for f in DD.AIR['structures'] for p in f['polys']] +
                     [Polygon(p[0], p[1:]).buffer(0) for t in DD.AIR['terminals'] + DD.AIR['boardingAreas'] for p in t['polys']] + [Pb] +
                     [G.moc().footprint_w.buffer(5.0)])              # the United MOC (no SFO Museum outline; from NAIP)
    airport = box(-2650, -2650, 1300, 1450)          # airport property window (south of it: Millbrae / Burlingame)
    nm = []
    for e in els:
        P = poly(e)
        if P.area < 2500 or not airport.contains(P.centroid): continue
        if P.intersection(modelled).area > 0.3 * P.area: continue
        t = e['tags']
        nm.append(dict(osm_way=e['id'], name=t.get('name'), building=t.get('building'), aeroway=t.get('aeroway'), levels=t.get('building:levels'),
                       height=t.get('height'), centre_xz=[round(P.centroid.x, 1), round(P.centroid.y, 1)], area_m2=round(P.area)))
    nm.sort(key=lambda r: -r['area_m2'])
    return dict(bart=dict(osm_way=221663595, tags=bart['tags'], poly=[[round(x, 2), round(z, 2)] for x, z in Pb.exterior.coords],
                          licence='ODbL 1.0, (c) OpenStreetMap contributors', timestamp=bart.get('timestamp')),
                not_modelled=nm, licence='ODbL 1.0, (c) OpenStreetMap contributors (refs/cache/osm/SOURCES.json)')


def unary(gs):
    from shapely.ops import unary_union
    return unary_union(list(gs))


def main():
    out = dict(generated_by='tools/blender/landside_r1_measure.py', frame='ltp-nad83-2011 (x east, z south, m from the ARP)', sun=SUN,
               cg_roof=cg_roof(), bart=dict(north=BART_NORTH, approach=BART_APPROACH, levels=BART_LEVELS),
               hyatt_slab_east=HYATT_SLAB_EAST, photos=PHOTOS, osm=osm_buildings(),
               cg_boxes_note='tower heights: TOWER_ABOVE_DECK %.1f m / plant %.1f m above the deck [inf]' % (TOWER_ABOVE_DECK, PLANT_ABOVE_DECK))
    json.dump(out, open(OUT, 'w'), indent=1)
    s = out['cg_roof']['stats']
    print('->', OUT, s, 'rims', len(out['cg_roof']['rims']), 'lobes', len(out['cg_roof']['lobes']))


if __name__ == '__main__':
    main()
