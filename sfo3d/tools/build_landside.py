#!/usr/bin/env python3
"""Landside roads and surface car parks from OpenStreetMap -> data/sfo_landside.json / .js (static fix-up, 26 Sep 2026).

Why: review round 4 found js/live/airport.js painting a hand-drawn, unsourced landside into the ground bake (a 236 m
disc round the terminal centre, freeway bands and rectangles as "parking"). This replaces it with mapped geometry.

Source: OSM ways highway=* and amenity=parking, Overpass download 26 Sep 2026 03:04 UTC (database 2026-09-26T03:03Z),
cached in refs/cache/osm/overpass_landside_*.json (query and endpoint in overpass_landside_latest.meta.json).
Licence: ODbL 1.0 - contains information from OpenStreetMap (c) OpenStreetMap contributors (docs/ATTRIBUTION.md).

What is kept (landside only):
  * roads: highway in ROAD_CLASSES, NOT tunnel / building_passage / layer < 0; bridge=yes / layer >= 1 are kept with
    `elevated` true (their footprint is paved ground; the app does not draw them as at-grade roads); clipped OUT of the
    airside (OSM aeroway=apron polygons, SFO Museum taxiway / runway polygons, the terminal complex, the ramp outline of
    sfo_details.json, each + 2 m), so apron service lanes (paint on concrete) are not drawn as roads;
  * parking: amenity=parking areas, kind 'parking' (surface / street_side / unset) or 'garage' (multi-storey: its
    footprint is paved / built ground), clipped the same way.
Widths (roads are OSM centrelines): OSM `width` where tagged (1 way); else `lanes` x 3.6 m (inferred: the FHWA 12 ft
lane); else a per-class default (DEFAULT_W, inferred - OSM has no width) - `w_src` says which.
Static close-out (2026-11-04): access=no service paths on the airfield -> `airside_paths` (concrete, width / offset measured
on NAIP 2024; were drawn as 4 m landside asphalt); `level` > 0 / 'Level N' names / aisles inside multi-storey garages are
elevated (only their footprint is paved ground). The OSM extract is pinned (tools/xcheck/fetch_osm.py, database
2026-09-26T03:03:01Z).
Round 3 (2026-11-05, review static r2 v1): roads wider than the narrow-band window (the asphalt perimeter road along the
Bay, apron / cargo service roads) are measured as a wide paved run (measure_road), gaps of a road bridged (inferred), drawn
paths clipped at SFO Museum runway / taxiway pavement, `material` = OSM surface (asphalt / concrete) or concrete (inferred).
Close-out round 3 (2026-11-06): the wide-run test of every way NOT tagged surface=asphalt also needs a per-pixel channel
spread < ROAD_SPX (smooth light infield soil had widened 3 m concrete paths to 5-8.5 m, finding static-5); an undrawn gap
between two road pieces of a way is bridged when NAIP shows no soil / vegetation / water along the OSM line (<= 5 %;
finding static-6, the 92 m stretch of 1182574242).
Fix round 2 (2026-11-08, verifier finding v4): a light band on a non-asphalt way whose core is soil-coloured (per-pixel
channel spread >= ROAD_SPX: light segments broken by soil / grass) is not drawn; the asphalt wide-run test also needs a per-pixel spread < ROAD_SAT
(the soil verge beside the perimeter road is 37-65); every drawn piece with > 15 % of its footprint on soil-coloured pixels
(per-pixel spread > 34, the verifier's measure) is narrowed until it is not, or not drawn.
Frame: tools/geo_frame.py (= js/geo.js) world x east / z south.
Usage: python3 tools/build_landside.py
"""
import json, os, sys
import numpy as np
from shapely.geometry import LineString, Polygon, MultiLineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import geo_frame as GF  # noqa: E402

CACHE = os.path.join(ROOT, 'refs', 'cache', 'osm')
ROAD_CLASSES = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link',
                'tertiary', 'tertiary_link', 'unclassified', 'residential', 'service'}
# inferred carriageway widths (m) where OSM has neither width nor lanes: 2 lanes of 3.6 m for through roads, one lane
# plus margin for links / service roads / parking aisles
DEFAULT_W = {'motorway': 7.2, 'trunk': 7.2, 'primary': 7.2, 'secondary': 7.2, 'tertiary': 7.2, 'unclassified': 6.0,
             'residential': 6.0, 'motorway_link': 4.5, 'trunk_link': 4.5, 'primary_link': 4.5, 'secondary_link': 4.5,
             'tertiary_link': 4.5, 'service': 4.0}


def world(geom):
    return [GF.wgs84_to_world(g['lat'], g['lon']) for g in geom]


def num(v):
    try: return float(str(v).split(';')[0].replace('m', '').strip())
    except (TypeError, ValueError): return None


AIRFIELD_M, AIRFIELD_TW_M = 250, 120     # airfield zone for access=no service paths (runway centreline / taxiway pavement)
_NAIP = {}


def _naip():
    if not _NAIP:
        m = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
        _NAIP.update(m=m, im=np.load(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r'))
    return _NAIP


def _profile(p, t, half, step=0.25):
    """NAIP 2024 grey level / channel spread across the line through p (direction t): offsets -half..+half (step m), each
    sample averaged over 3 m along the line -> (o, g, sat, tex = grey-level std over those 3 m, spx = median over those 3 m
    of the PER-PIXEL channel spread) or None outside the raster"""
    from scipy.ndimage import map_coordinates
    N = _naip(); m = N['m']; res, x0, z0 = m['res'], m['x0'], m['z0']
    t = np.asarray(t, float) / np.linalg.norm(t); n = np.array([-t[1], t[0]])
    o = np.arange(-half, half + 1e-9, step); a = np.linspace(-1.5, 1.5, 7)
    O, Aa = np.meshgrid(o, a); X = p[0] + O * n[0] + Aa * t[0]; Z = p[1] + O * n[1] + Aa * t[1]
    r = (Z - z0) / res - 0.5; c = (X - x0) / res - 0.5
    r0, c0 = int(np.floor(r.min())) - 1, int(np.floor(c.min())) - 1
    if r0 < 0 or c0 < 0: return None
    sub = np.asarray(N['im'][r0:int(np.ceil(r.max())) + 2, c0:int(np.ceil(c.max())) + 2], np.float32)
    chf = [map_coordinates(sub[..., k], [r - r0, c - c0], order=1, mode='nearest') for k in range(3)]
    ch = [v.mean(0) for v in chf]
    spx = np.median(np.max(chf, 0) - np.min(chf, 0), 0)      # close-out round 3: per-pixel channel spread, median along
    return o, (ch[0] + ch[1] + ch[2]) / 3, np.max(ch, 0) - np.min(ch, 0), ((chf[0] + chf[1] + chf[2]) / 3).std(0), spx


ROAD_HALF = 14.0         # m: half window of the road profile (wider than the widest perimeter / service road + its offset)
ROAD_SAT = 34.0          # NAIP max-min channel spread below which a sample can be pavement: the asphalt perimeter road 8-31
                         # (dusty lanes 25-31), concrete 3-17; dry grass / soil 40-70 on the same profiles (measured, round 3)
ROAD_TEX = 3.5           # grey-level std over the 3 m along the line below which a sample can be pavement: the road 0-1.5,
                         # light infield soil 4-28, rip-rap 5-28 (same profiles)
ROAD_G = 150.0           # NAIP grey level above which ...: the road 160-215; Bay water 95-130 and the dark rip-rap 100-140
ROAD_GAP = 1.0           # m: darker gaps this short inside the run (lane / edge paint, joints, a vehicle shadow) are closed
ROAD_NEAR = 3.0          # m: the run must reach this close to the OSM line (or to the narrow band, when one was found)
ROAD_W_MIN = 3.0         # m: narrower runs are bands / strips (measure_band's domain)
ROAD_WIDER = 1.5         # m: a road run this much wider than the narrow band replaces it (the band was an edge strip on it)


ROAD_SPX = 22.0          # close-out round 3 (finding static-5): per-pixel channel spread (median over 3 m along) below which a
                         # sample of a NON-asphalt way can be pavement. The 3 m-averaged spread (ROAD_SAT) lets smooth light
                         # infield soil pass (its per-pixel colour is mottled, the average is not): measured on the round-2
                         # verifier's pieces, the concrete path cores 8-17 and soil flanks 25-60 (1182574236/5, 1182574227/4,
                         # 1182574229/3, 1182574227/40), while the OSM surface=asphalt perimeter road is dusty (flanks 20-29)
                         # and keeps the ROAD_SAT test (same value as FLANK_SAT: asphalt / concrete 3-17)


def measure_road(p, t, seed=0.0, half=ROAD_HALF, step=0.25, strict=False):
    """round 3 (review static r2 v1): a WIDE paved band across the line through p - the asphalt perimeter / service roads
    (6-12 m) that measure_band's +-6 m window cannot hold (it returned None, 'band wider than the window', or the 1.75 m
    light edge strip on the road). Samples with channel spread < ROAD_SAT and grey > ROAD_G (pavement, not dry grass / soil /
    water / dark rip-rap), gaps <= ROAD_GAP closed; the run through the sample nearest `seed` (within ROAD_NEAR); its edges
    refined to the half-maximum between the run's median grey and the 1.5 m beyond each edge (a blurred step's edge).
    -> (centre offset m (+ = right of t, measure_band's normal), width m, median channel spread) | 'wide' (the run reaches
    the window: the road lies inside wider pavement / light ground) | None.
    strict (close-out round 3, finding static-5; every way not tagged surface=asphalt): each sample must also have a
    per-pixel channel spread < ROAD_SPX - the run stops where smooth light soil begins (was: 2-5 m too wide on soil)"""
    r = _profile(p, t, half, step)
    if r is None: return None
    o, g, sat, tex, spx = r
    pv = (sat < ROAD_SAT) & (g > ROAD_G) & (tex < ROAD_TEX)
    if strict: pv &= spx < ROAD_SPX                            # close-out round 3: not on a surface=asphalt way
    else: pv &= spx < ROAD_SAT                                 # fix round 2 (verifier v4): asphalt too, per pixel (soil verge 37-65)
    idx = np.where(pv)[0]
    if not len(idx): return None
    k = int(round(ROAD_GAP / step))
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= k + 1: pv[a:b] = True
    near = np.where(pv & (np.abs(o - seed) <= ROAD_NEAR))[0]
    if not len(near): return None
    c = near[np.argmin(np.abs(o[near] - seed))]; i0 = i1 = c
    while i0 > 0 and pv[i0 - 1]: i0 -= 1
    while i1 < len(o) - 1 and pv[i1 + 1]: i1 += 1
    if i0 == 0 or i1 == len(o) - 1: return 'wide'
    core = float(np.median(g[i0:i1 + 1])); fl = int(round(1.5 / step))
    thl = (core + float(np.median(g[max(0, i0 - fl):i0]))) / 2; thr = (core + float(np.median(g[i1 + 1:i1 + 1 + fl]))) / 2
    while i0 < c and g[i0] < thl: i0 += 1
    while i1 > c and g[i1] < thr: i1 -= 1
    return float((o[i0] + o[i1]) / 2), float(o[i1] - o[i0] + step), float(np.median(sat[i0:i1 + 1]))


def measure_band(p, t, half=6.0, step=0.25, info=False):
    """bright, unsaturated band across the line through p (direction t) on NAIP 2024: grey level profile over +-half m,
    averaged over 3 m along; the band = the contiguous run round the brightest sample above (grass median + 60 % of the
    contrast). -> (centre offset m (+ = right of t), width m) or None (no band: contrast < 25 grey levels or saturated).
    info=True adds a third value: True when a flank (0.5-2.5 m beyond either band edge) is itself unsaturated ground
    (>= 60 % of its samples with max-min channel spread < FLANK_SAT) - the band is then a light line INSIDE wider
    pavement (road edge / lane paint, a kerb), not a path across the field (round 2: 2.7 km of 1-1.5 m 'paths' were
    such lines on the asphalt perimeter road)"""
    from scipy.ndimage import map_coordinates
    N = _naip(); m = N['m']; res, x0, z0 = m['res'], m['x0'], m['z0']
    t = np.asarray(t, float) / np.linalg.norm(t); n = np.array([-t[1], t[0]])
    o = np.arange(-half, half + 1e-9, step); a = np.linspace(-1.5, 1.5, 7)
    O, Aa = np.meshgrid(o, a); X = p[0] + O * n[0] + Aa * t[0]; Z = p[1] + O * n[1] + Aa * t[1]
    r = (Z - z0) / res - 0.5; c = (X - x0) / res - 0.5
    r0, c0 = int(np.floor(r.min())) - 1, int(np.floor(c.min())) - 1
    if r0 < 0 or c0 < 0: return None
    sub = np.asarray(N['im'][r0:int(np.ceil(r.max())) + 2, c0:int(np.ceil(c.max())) + 2], np.float32)
    ch = [map_coordinates(sub[..., k], [r - r0, c - c0], order=1, mode='nearest').mean(0) for k in range(3)]
    g = (ch[0] + ch[1] + ch[2]) / 3; sat = np.max(ch, 0) - np.min(ch, 0)
    bg = np.median(g); k = int(np.argmax(g)); con = g[k] - bg
    if con < 25 or sat[k] > 35: return None
    thr = bg + 0.6 * con; i0 = k; i1 = k
    while i0 > 0 and g[i0 - 1] >= thr: i0 -= 1
    while i1 < len(g) - 1 and g[i1 + 1] >= thr: i1 += 1
    if i0 == 0 or i1 == len(g) - 1: return None               # band wider than the window: not a path
    if not info: return float((o[i0] + o[i1]) / 2), float(o[i1] - o[i0] + step)
    fl = int(round(0.5 / step)), int(round(2.5 / step))
    paved = any(len(f) and np.mean(f < FLANK_SAT) >= 0.6 for f in (sat[max(0, i0 - fl[1]):max(0, i0 - fl[0])], sat[i1 + fl[0]:i1 + fl[1]]))
    return float((o[i0] + o[i1]) / 2), float(o[i1] - o[i0] + step), bool(paved)


def band_core_spx(p, t, off, half=0.5):
    """fix round 2 (verifier finding v4): median PER-PIXEL channel spread over the band's central +-half m (3 m along) - a
    light band on a NON-asphalt way whose core is warm / soil-coloured (spread >= ROAD_SPX: 1157838876 parts 1 / 3 / 8,
    core medians 28-33, b* 12-14 while the concrete paths are 8-17: light segments broken by soil / grass on NAIP) is not a
    continuous paved surface"""
    r = _profile(p, t, abs(off) + half + 0.5, 0.25)
    if r is None: return None
    o, g, sat, tex, spx = r
    k = np.abs(o - off) <= half
    return float(np.median(spx[k])) if k.any() else None


FOOT_SAT = 34.0          # fix round 2 (verifier v4): per-pixel channel spread above which a footprint pixel is soil / dry grass
FOOT_MAX = 0.15          # ... a drawn piece may have at most this share of such pixels in its footprint (else narrowed / dropped)


def footprint_soil(pts, w):
    """share of the NAIP 2024 pixels inside the drawn footprint (centreline buffered by w / 2, flat caps) with a per-pixel
    channel spread > FOOT_SAT (the round-3 verifier's pathfoot measure)"""
    from matplotlib.path import Path
    N = _naip(); m = N['m']; res, x0, z0 = m['res'], m['x0'], m['z0']
    pg = LineString(pts).buffer(w / 2, cap_style=2)
    bx0, bz0, bx1, bz1 = pg.bounds
    c0, c1 = int((bx0 - x0) / res), int((bx1 - x0) / res) + 1; r0, r1 = int((bz0 - z0) / res), int((bz1 - z0) / res) + 1
    sub = np.asarray(N['im'][r0:r1, c0:c1], np.float32); cc, rr = np.meshgrid(np.arange(c0, c1), np.arange(r0, r1))
    q = np.c_[x0 + (cc.ravel() + 0.5) * res, z0 + (rr.ravel() + 0.5) * res]
    ins = np.zeros(len(q), bool)
    for g in getattr(pg, 'geoms', [pg]): ins |= Path(np.array(g.exterior.coords)).contains_points(q)
    ins = ins.reshape(cc.shape)
    if not ins.any(): return 0.0
    return float(((sub.max(-1) - sub.min(-1)) > FOOT_SAT)[ins].mean())


def footprint_fix(paths):
    """fix round 2 (verifier finding v4): a drawn piece with more than FOOT_MAX of its footprint on soil-coloured pixels is
    narrowed (0.25 m steps, centre kept, not below PATH_W_MIN) until it is not - its extra width lay on the soil beside the
    imaged band (1182574227/28: a 6.62 m box from 4 junction profiles) - or, if even PATH_W_MIN fails, not drawn (the band
    itself is soil-coloured)"""
    n_n = n_d = 0
    for r in paths:
        if not r['drawn'] or not r.get('w'): continue
        f0 = footprint_soil(r['pts'], r['w'])
        if f0 <= FOOT_MAX: continue
        w = r['w']
        while w - 0.25 >= PATH_W_MIN - 1e-9 and footprint_soil(r['pts'], w) > FOOT_MAX: w -= 0.25
        f1 = footprint_soil(r['pts'], w)
        if f1 <= FOOT_MAX:
            r['w_src'] += ('; narrowed %.2f -> %.2f m: %.0f %% of the drawn footprint was soil-coloured (per-pixel channel spread > %.0f), '
                           'now %.0f %% (fix round 2)' % (r['w'], w, 100 * f0, FOOT_SAT, 100 * f1)); r['w'] = round(w, 2); n_n += 1
        else:
            r.update(drawn=False, w=None, w_src=r['w_src'] + ('; not drawn: %.0f %% of its footprint is soil-coloured (per-pixel channel spread > '
                                                                '%.0f) even at %.2f m (fix round 2)' % (100 * f1, FOOT_SAT, PATH_W_MIN)))
            for k in ('offset_range', 'naip_frac_part', 'kind_naip', 'bridged', 'material_src'): r.pop(k, None)
            n_d += 1
    print('footprint soil test (fix round 2): %d pieces narrowed, %d no longer drawn' % (n_n, n_d))


PATH_STEP = 2.5          # m between NAIP profiles along an airside path
PATH_OUTLIER = 1.0       # m: a profile whose band centre is this far from the local median (+-20 m) is another feature
PATH_SMOOTH = 12.5       # m: half window of the running median of the band centre (piecewise offset, not one per way)
PATH_GAP = 15.0          # m: shorter runs without an imaged band inside an imaged stretch are bridged (crossings, shadows)
PATH_MIN = 10.0          # m: shortest imaged stretch drawn
PATH_W_MIN = 1.75        # m: a narrower imaged band is a paint line / kerb, not a vehicle path (inferred: a 0.5 m NAIP pixel
                         # blurs a 4-12 in line to 0.75-1.5 m; the narrowest airside vehicles are ~2 m wide)
FLANK_SAT = 22.0         # NAIP max-min channel spread below which a flank counts as pavement (asphalt / concrete 3-17,
                         # dry grass / soil 30-50 on the profiles of round 2; measured, tools/build_landside.py notes)


ROAD_OUTLIER = 2.0       # m: road stations whose centre is this far from the local median (+-20 m) are dropped (edge noise)
ROAD_W_OUTLIER = 2.5     # m: ... or whose width is this far from the local median road width (a light shoulder / apron)
ROAD_BRIDGE = 250.0      # m: longest 'inside wider pavement' / 'light line' gap of a road that is bridged (inferred continuity)
ROAD_BRIDGE_ANY = 30.0   # m: any shorter gap between two road pieces is bridged
W_STEP = 1.5             # m: a drawn stretch is cut where its running median width changes by more (one width per entry)
W_PIECE = 25.0           # m: shortest such piece
SURFACES = {'asphalt': 'asphalt', 'concrete': 'concrete', 'concrete:plates': 'concrete', 'concrete:lanes': 'concrete'}


ROAD_CLEAN_MAX = 0.05     # close-out round 3 (finding static-6): an undrawn gap between two drawn road pieces of a way (<=
                          # ROAD_BRIDGE m) is bridged when at most this share of NAIP samples along the bridged line is soil /
                          # vegetation / water - whatever share of its profiles reached the road window (OSM 1182574242 part 14:
                          # 92 m of the continuous imaged asphalt road at (624, -944), 35 % 'wide')


ROAD_BRIDGE_CLEAN = 400.0  # m: longest such clean gap (the 'inside wider pavement' gaps of 155476060 run 302-320 m)


def clean_line(ls, a, b, o0, o1, step=2.0, half=1.5):
    """share of NAIP 2024 samples (every `step` m along the OSM line between stations a and b, offset interpolated o0 -> o1,
    and +-half m across) that are soil / dry grass (R - B > 38, R - G > 5, R > 110), vegetation (G - R > 6, G > B, lum <
    150) or water / dark rip-rap (lum < 125) - the round-2 verifier's classes; None outside the raster"""
    N = _naip(); m = N['m']; res, x0, z0 = m['res'], m['x0'], m['z0']; im = N['im']; L = ls.length; bad = n = 0
    for v in np.arange(a, b + 1e-9, step):
        q0 = ls.interpolate(max(0, v - 2)); q1 = ls.interpolate(min(L, v + 2)); q = ls.interpolate(v)
        tt = np.array([q1.x - q0.x, q1.y - q0.y]); tt /= max(1e-9, np.linalg.norm(tt)); nn = np.array([-tt[1], tt[0]])
        off = np.interp(v, [a, b], [o0, o1])
        for d in np.arange(-half, half + 1e-9, 0.5):
            x, z = q.x + (off + d) * nn[0], q.y + (off + d) * nn[1]
            rr, cc = int((z - z0) / res), int((x - x0) / res)
            if not (0 <= rr < im.shape[0] and 0 <= cc < im.shape[1]): return None
            bb, gg, r_ = (float(u) for u in im[rr, cc]); lum = (r_ + gg + bb) / 3
            n += 1; bad += ((r_ - bb > 38) and (r_ - gg > 5) and (r_ > 110)) or ((gg - r_ > 6) and (gg > bb) and (lum < 150)) or (lum < 125)
    return bad / n if n else None


def measure_path(e, ls, t):
    """airside service path -> list of stretches (dicts). NAIP 2024 profiles every PATH_STEP m: the narrow bright band
    (measure_band, +-6 m: the 2-3 m concrete infield paths) and the wide paved run (measure_road, +-14 m: the 6-12 m
    asphalt perimeter / service roads); per station the road run replaces the band when it is >= ROAD_WIDER m wider (the
    band was a light strip ON the road) or when there is no band. Outliers off the local median dropped; the drawn centre =
    OSM station + running-median offset along the SAME normal measure_band uses (n = [-t_z, t_x], + = right of travel in
    the x-east / z-south world frame); drawn only where NAIP images the band / road (stretches; gaps < PATH_GAP m bridged),
    width = median width of each near-constant-width piece of the stretch, `kind_naip` 'band' | 'road' by the stretch
    majority; road gaps bridged (inferred, `bridged`); material = OSM surface where tagged (obs), else concrete (inferred,
    as round 1: a light neutral band / run on NAIP).
    Round 2 (2026-11-05, review static-v1): the round-1 code moved the whole way by ONE median offset with shapely
    parallel_offset, whose 'right' is right in a y-UP frame = LEFT in this z-south frame - the drawn bands ended ~2x the
    offset from the imaged path. Shapely's side convention is no longer used.
    Round 3 (2026-11-05, review static r2 v1): the asphalt perimeter road along the Bay (OSM 112508632, 6-12 m) was wider
    than measure_band's window: 4.06 of its 4.91 km were not drawn (3.57 km on no other paved source) and the rest were
    1.75 m edge strips. measure_road measures it (and every other road wider than measure_band's window)."""
    from shapely.ops import substring
    L = ls.length
    surf = SURFACES.get(t.get('surface'))
    S = np.arange(PATH_STEP / 2, L, PATH_STEP) if L > PATH_STEP else np.array([L / 2])
    Q = np.zeros((len(S), 2)); N = np.zeros((len(S), 2)); O = np.full(len(S), np.nan); Wd = np.full(len(S), np.nan)
    LINE = np.zeros(len(S), bool); ROAD = np.zeros(len(S), bool); WIDE = np.zeros(len(S), bool); SOIL = np.zeros(len(S), bool)
    for i, s_ in enumerate(S):
        q0 = ls.interpolate(max(0, s_ - 2)); q1 = ls.interpolate(min(L, s_ + 2)); q = ls.interpolate(s_)
        tt = np.array([q1.x - q0.x, q1.y - q0.y]); Q[i] = (q.x, q.y)
        nt = np.linalg.norm(tt)
        if nt < 1e-6: continue
        tt /= nt; N[i] = (-tt[1], tt[0])                       # measure_band's normal
        r = measure_band((q.x, q.y), tt, info=True)
        band = r if (r and not r[2] and r[1] >= PATH_W_MIN) else None
        if band and surf != 'asphalt':                          # fix round 2 (verifier v4): a soil-coloured band is a dirt track
            cs = band_core_spx((q.x, q.y), tt, band[0])
            if cs is not None and cs >= ROAD_SPX: band = None; SOIL[i] = True
        rr = measure_road((q.x, q.y), tt, seed=r[0] if r else 0.0, strict=surf != 'asphalt')
        WIDE[i] = rr == 'wide'
        if isinstance(rr, tuple) and rr[1] >= ROAD_W_MIN and (band is None or rr[1] >= band[1] + ROAD_WIDER):
            O[i], Wd[i] = rr[0], rr[1]; ROAD[i] = True
        elif band: O[i], Wd[i] = band[0], band[1]
        elif r and not SOIL[i]: LINE[i] = True                 # a light line inside wider pavement / a paint line: not a path band
    ok = ~np.isnan(O)
    for _ in range(2):                                         # drop profiles that caught another bright feature
        idx = np.where(ok)[0]
        if not len(idx): break
        loc = [idx[np.abs(S[idx] - S[i]) <= 20.0] for i in idx]
        med = np.array([np.median(O[l_]) for l_ in loc])
        tol = np.where(ROAD[idx], ROAD_OUTLIER, PATH_OUTLIER)
        bad = np.abs(O[idx] - med) > tol
        for j, (i, l_) in enumerate(zip(idx, loc)):            # road widths: a station off the local road median width
            lr = l_[ROAD[l_]]
            if ROAD[i] and len(lr) >= 3 and abs(Wd[i] - np.median(Wd[lr])) > ROAD_W_OUTLIER: bad[j] = True
        ok[idx[bad]] = False
    idx = np.where(ok)[0]
    n_ok = len(idx); frac = n_ok / len(S)
    # stretches: stations within 2 profiles of an accepted one; runs merged across gaps < PATH_GAP
    cov = np.zeros(len(S), bool)
    for i in idx: cov[max(0, i - 2):i + 3] = True
    runs, i = [], 0
    while i < len(S):
        if cov[i]:
            j = i
            while j + 1 < len(S) and cov[j + 1]: j += 1
            runs.append([i, j]); i = j + 1
        else: i += 1
    merged = []
    for r in runs:
        if merged and (S[r[0]] - S[merged[-1][1]]) < PATH_GAP: merged[-1][1] = r[1]
        else: merged.append(r)
    good = [r for r in merged if S[r[1]] - S[r[0]] + PATH_STEP >= PATH_MIN and ok[r[0]:r[1] + 1].sum() >= 3]
    base = {'osm_id': e['id'], 'kind': 'airside_path', 'surface_osm': t.get('surface'), 'access': t.get('access'),
            'naip_frac': round(frac, 2)}
    out, cur = [], 0.0
    def undrawn(a, b):
        if b - a < 1.0: return
        g = substring(ls, a, b)
        if g.geom_type != 'LineString' or g.length < 1.0: return
        k = (S >= a) & (S <= b); fl = float(LINE[k].mean()) if k.any() else 0.0; fw = float(WIDE[k].mean()) if k.any() else 0.0
        fs = float(SOIL[k].mean()) if k.any() else 0.0
        out.append({**base, 'material': surf or 'concrete', 'part': len(out), 'w': None, 'offset_m': 0.0, 'drawn': False,
                    'w_src': ('NAIP: a light line inside wider pavement (%.0f %% of the profiles) - a wider road / apron edge, not a path '
                              'band; not drawn' % (100 * fl)) if fl >= 0.3 else
                             ('NAIP: the light band is soil-coloured / broken by soil and grass (per-pixel channel spread >= %.0f at its '
                              'core, %.0f %% of the profiles) - not a continuous paved surface; not drawn (fix round 2)' % (ROAD_SPX, 100 * fs)) if fs >= 0.3 else
                             ('NAIP: the paved run reaches +-%.0f m (%.0f %% of the profiles) - inside wider pavement / light ground; '
                              'not drawn' % (ROAD_HALF, 100 * fw)) if fw >= 0.3 else 'NAIP shows no band here: not drawn',
                    **({'paved_line_frac': round(fl, 2)} if fl > 0 else {}), **({'wide_frac': round(fw, 2)} if fw > 0 else {}),
                    'pts': [[round(x, 1), round(z, 1)] for x, z in g.simplify(0.3).coords], '_s': (a, b), '_f': fl + fw})
    def material(road):
        return (surf, 'osm surface=%s' % t['surface']) if surf else ('concrete', 'inferred: OSM untagged; a light neutral band / run on NAIP 2024 (as round 1)')
    for a, b in good:
        sa = 0.0 if a == 0 else S[a] - PATH_STEP / 2; sb = L if b == len(S) - 1 else S[b] + PATH_STEP / 2
        undrawn(cur, sa); cur = sb
        ii = np.arange(a, b + 1); acc = idx[(idx >= a) & (idx <= b)]
        road = bool(ROAD[acc].mean() >= 0.5)
        # the stretch's majority kind only - on a surface=asphalt way (its narrow bands are light edge / lane strips ON the
        # road). Close-out round 3 (finding static-5): on every other way the band and the (strict) road run measure the
        # same imaged path, so all accepted stations count; majority-only had sized 1182574236 pieces 4 / 6 (49 / 30 m, on a
        # 2.5-3.25 m band) from 4 junction profiles each (5.25 m, a third of the footprint on soil)
        if surf == 'asphalt': acc = acc[ROAD[acc] == road]
        sm = np.array([np.median(O[acc[np.abs(S[acc] - S[k]) <= PATH_SMOOTH]]) if np.any(np.abs(S[acc] - S[k]) <= PATH_SMOOTH) else np.nan for k in acc])
        sS = S[ii]; off = np.interp(sS, S[acc], sm)            # piecewise offset, flat beyond the first / last profile
        P = Q[ii] + off[:, None] * N[ii]
        # pieces of near-constant width (one width per drawn entry): cut where the running median width (+-2 PATH_SMOOTH)
        # leaves the piece's median by > W_STEP; pieces >= W_PIECE m
        wm = np.array([np.median(Wd[acc[np.abs(S[acc] - S[k]) <= 2 * PATH_SMOOTH]]) for k in acc])
        cuts, st = [], 0
        for j in range(1, len(acc)):
            if abs(wm[j] - np.median(wm[st:j])) > W_STEP and S[acc[j]] - S[acc[st]] >= W_PIECE and S[acc[-1]] - S[acc[j]] >= W_PIECE:
                cuts.append(j); st = j
        bounds = [0] + cuts + [len(acc)]
        mat, msrc = material(road)
        for q_, (j0, j1) in enumerate(zip(bounds[:-1], bounds[1:])):
            s0 = sS[0] if q_ == 0 else (S[acc[j0 - 1]] + S[acc[j0]]) / 2
            s1 = sS[-1] if j1 == len(acc) else (S[acc[j1 - 1]] + S[acc[j1]]) / 2
            kk = (sS > s0 + 1e-6) & (sS < s1 - 1e-6)
            ends = [np.array([[np.interp(v, sS, P[:, 0]), np.interp(v, sS, P[:, 1])]]) for v in (s0, s1)]
            Pq = np.vstack([ends[0], P[kk], ends[1]])
            aq = acc[j0:j1]; oq = np.concatenate([[np.interp(s0, sS, off)], off[kk], [np.interp(s1, sS, off)]])
            w = float(np.median(Wd[aq]))
            g = LineString(Pq).simplify(0.3)
            out.append({**base, 'material': mat, 'material_src': msrc, 'part': len(out), 'w': round(w, 2), 'offset_m': round(float(np.median(oq)), 2),
                        'offset_range': [round(float(oq.min()), 2), round(float(oq.max()), 2)], 'drawn': True,
                        'kind_naip': 'road' if road else 'band', 'naip_frac_part': round(len(aq) / max(1, int(((sS >= s0) & (sS <= s1)).sum())), 2),
                        'w_src': ('NAIP 2024 median width of the paved run (measure_road, %d profiles)' if road else
                                  'NAIP 2024 median band width (%d profiles)') % len(aq),
                        'pts': [[round(x, 1), round(z, 1)] for x, z in g.coords], '_s': (s0, s1), '_o': (oq[0], oq[-1])})
    undrawn(cur, L)
    # round 3: a ROAD continues where NAIP shows it inside wider light pavement / ground (the run reaches the window) or a
    # light line on it, and across short gaps - the OSM way is continuous. Such undrawn gaps between two road pieces of the
    # way (<= ROAD_BRIDGE m; any gap <= ROAD_BRIDGE_ANY m), and at the way's ends next to a road piece, are drawn along the
    # OSM line with the offset interpolated between the neighbours' end offsets and the narrower neighbour width, capped
    # at the way's median road width at an end (width / position inferred; `bridged` true)
    rw = [o_['w'] for o_ in out if o_['drawn'] and o_['kind_naip'] == 'road']
    w_way = float(np.median(rw)) if rw else None
    def isroad(o_): return o_ is not None and o_['drawn'] and o_.get('kind_naip') == 'road'
    for k, o_ in enumerate(out):
        if o_['drawn']: continue
        a_, b_ = o_['_s']; prv = out[k - 1] if k > 0 else None; nxt = out[k + 1] if k + 1 < len(out) else None
        inner = isroad(prv) and isroad(nxt); end = (k == 0 and isroad(nxt)) or (k == len(out) - 1 and isroad(prv))
        if not (inner or end): continue
        o0 = prv['_o'][1] if isroad(prv) else nxt['_o'][0]; o1 = nxt['_o'][0] if isroad(nxt) else prv['_o'][1]
        clean = None
        if inner and b_ - a_ <= ROAD_BRIDGE_CLEAN and not ((o_['_f'] >= 0.5 and b_ - a_ <= ROAD_BRIDGE) or b_ - a_ <= ROAD_BRIDGE_ANY):
            clean = clean_line(ls, a_, b_, o0, o1)     # close-out round 3 (finding static-6)
            if clean is None or clean > ROAD_CLEAN_MAX: continue
        elif not ((b_ - a_ <= ROAD_BRIDGE and o_['_f'] >= 0.5) or (inner and b_ - a_ <= ROAD_BRIDGE_ANY)): continue
        w = min(x['w'] for x in (prv, nxt) if isroad(x)) if inner else min(w_way, (prv if isroad(prv) else nxt)['w'])
        ss = np.linspace(a_, b_, max(2, int(np.ceil((b_ - a_) / PATH_STEP)) + 1)); P = []
        for v in ss:
            q0 = ls.interpolate(max(0, v - 2)); q1 = ls.interpolate(min(L, v + 2)); q = ls.interpolate(v)
            tt = np.array([q1.x - q0.x, q1.y - q0.y]); tt /= max(1e-9, np.linalg.norm(tt)); nn = np.array([-tt[1], tt[0]])
            P.append(np.array([q.x, q.y]) + np.interp(v, [a_, b_], [o0, o1]) * nn)
        mat, msrc = material(True)
        out[k] = {**base, 'material': mat, 'material_src': msrc, 'part': k, 'w': round(w, 2), 'offset_m': round(float((o0 + o1) / 2), 2),
                  'offset_range': [round(float(min(o0, o1)), 2), round(float(max(o0, o1)), 2)], 'drawn': True, 'kind_naip': 'road', 'bridged': True,
                  'w_src': ('inferred: the road continues (OSM way; NAIP %s); width = the narrower neighbouring piece%s, offset interpolated' % (
                      o_['w_src'].replace('; not drawn', '').replace('NAIP: ', '').replace('NAIP ', ''), '' if inner else ' capped at the way median'))
                           + ('; NAIP along the line: %.0f %% soil / vegetation / water (<= %.0f %%: bridged, close-out round 3)' % (100 * clean, 100 * ROAD_CLEAN_MAX) if clean is not None else ''),
                  'pts': [[round(x, 1), round(z, 1)] for x, z in LineString(P).simplify(0.3).coords], '_s': (a_, b_), '_o': (o0, o1)}
    for k, o_ in enumerate(out):
        o_['part'] = k; o_.pop('_s', None); o_.pop('_o', None); o_.pop('_f', None)
    if not out:
        out.append({**base, 'material': surf or 'concrete', 'part': 0, 'w': None, 'offset_m': 0.0, 'drawn': False, 'w_src': 'NAIP shows no band: not drawn',
                    'pts': [[round(x, 1), round(z, 1)] for x, z in ls.simplify(0.3).coords]})
    return out


def clip_paved(paths, clip):
    """round 3: drawn airside paths stop at SFO Museum runway / taxiway pavement (the runway / taxiway surface is drawn by
    that layer; a service road crossing a taxiway is part of its pavement): the part of a drawn centreline inside `clip`
    becomes an undrawn entry. 'part' is renumbered along each way."""
    from shapely.ops import substring
    from shapely.prepared import prep
    pc = prep(clip); out = []
    for r in paths:
        ls = LineString(r['pts'])
        if not r['drawn'] or not pc.intersects(ls) or ls.intersection(clip).length < 1.0: out.append(r); continue
        # stations every 0.5 m: inside / outside, runs -> pieces (shorter than 2 m drawn runs merge into the clipped part)
        n = max(2, int(ls.length / 0.5)); ss = np.linspace(0, ls.length, n + 1); mid = (ss[:-1] + ss[1:]) / 2
        ins = np.array([clip.contains(ls.interpolate(v)) for v in mid])
        runs, i = [], 0
        while i < len(ins):
            j = i
            while j + 1 < len(ins) and ins[j + 1] == ins[i]: j += 1
            runs.append([bool(ins[i]), ss[i], ss[j + 1]]); i = j + 1
        for k_ in range(len(runs)):                            # drawn slivers < 2 m between clipped runs: clipped
            if not runs[k_][0] and runs[k_][2] - runs[k_][1] < 2.0 and len(runs) > 1: runs[k_][0] = True
        mergedr = []
        for q in runs:
            if mergedr and mergedr[-1][0] == q[0]: mergedr[-1][2] = q[2]
            else: mergedr.append(q)
        for inside, a, b in mergedr:
            g = substring(ls, a, b)
            if g.geom_type != 'LineString' or g.length < 0.5: continue
            pts = [[round(x, 1), round(z, 1)] for x, z in g.coords]
            if inside:
                out.append({**{k: v for k, v in r.items() if k not in ('w', 'offset_range', 'naip_frac_part', 'kind_naip', 'bridged', 'material_src')},
                            'w': None, 'drawn': False, 'pts': pts,
                            'w_src': 'on SFO Museum runway / taxiway pavement (that layer draws the surface): not drawn'})
            else: out.append({**r, 'pts': pts})
    cnt = {}
    for r in out: r['part'] = cnt.get(r['osm_id'], 0); cnt[r['osm_id']] = r['part'] + 1
    return out


def main():
    meta = json.load(open(os.path.join(CACHE, 'overpass_landside_latest.meta.json')))
    d = json.load(open(os.path.join(CACHE, meta['file'])))
    osm_air = json.load(open(os.path.join(CACHE, 'ksfo_osm_parsed.json')))
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    air = [Polygon([GF.wgs84_to_world(la, lo) for la, lo in a['pts']]).buffer(0) for a in osm_air['aprons'] if len(a['pts']) >= 4]
    for group in (A['taxiways'], A['runways']):
        for t in group:
            for poly in t['polys']: air.append(Polygon(poly[0], poly[1:]).buffer(0))
    for poly in A['terminalComplex']: air.append(Polygon(poly[0], poly[1:]).buffer(0))      # with its holes: the central landside (garage, loop roads) is a hole
    # the ramp outline of data/sfo_details.json (apron between the terminals; airside service lanes there are paint on
    # concrete, not roads)
    for poly in json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))['apron']: air.append(Polygon(poly[0], poly[1:]).buffer(0))
    airside = unary_union(air).buffer(2.0)
    # the app bakes the ground only inside APT_RECT (js/world/airfield.js: s0 -2800, t0 -1760, w 4700, h 3220 m in the
    # airport grid); everything is clipped to that rectangle (+50 m)
    s0, t0, w_, h_ = -2800.0, -1760.0, 4700.0, 3220.0
    rect = Polygon([GF.st_to_world(s0 - 50, t0 - 50), GF.st_to_world(s0 + w_ + 50, t0 - 50), GF.st_to_world(s0 + w_ + 50, t0 + h_ + 50), GF.st_to_world(s0 - 50, t0 + h_ + 50)])
    airside = airside.union(rect.exterior.buffer(0.01)).union(Polygon([(-1e5, -1e5), (1e5, -1e5), (1e5, 1e5), (-1e5, 1e5)]).difference(rect))
    roads, parks, paths = [], [], []
    n_elev = n_air = 0
    # static close-out (2026-11-04): (1) AIRSIDE service paths. OSM highway=service + access=no ways on the airfield (within
    # AIRFIELD_M of a runway centreline or of SFO Museum taxiway pavement) are the infield / perimeter vehicle paths, not
    # landside roads (review: 16.2 km painted as 4 m asphalt across the grass; NAIP shows ~2.5 m neutral concrete bands, their
    # centre a median 1.25 m off the OSM line). They go to `airside_paths`, each with its width and lateral offset MEASURED
    # on NAIP 2024 (bright band across the line, measure_band) and material concrete; a path NAIP does not show is kept
    # with drawn false. (2) Upper-level aisles: `level` > 0, a name 'Level N' (N >= 2) or a way inside a multi-storey
    # garage footprint (OSM parking=multi-storey / SFO Museum garage) is elevated (review: 677 m of 'Garage Level 4/5
    # Parking Aisle' drawn at grade, 400 m inside the Central Parking Garage).
    rw_lines = [LineString([GF.end_world(a), GF.end_world(b)]) for a, b in GF.RWY_PAIRS]
    tw_union = unary_union([Polygon(poly[0], poly[1:]).buffer(0) for t in A['taxiways'] for poly in t['polys']])
    garages = [Polygon(world(e['geometry'])).buffer(0) for e in d['elements'] if e['type'] == 'way' and 'geometry' in e
               and e.get('tags', {}).get('amenity') == 'parking' and e['tags'].get('parking') == 'multi-storey' and len(e['geometry']) >= 4]
    garages += [Polygon(poly[0]).buffer(0) for s_ in A['structures'] if s_['kind'] == 'garage' for poly in s_['polys']]
    garage_u = unary_union(garages)
    import re as _re
    for e in d['elements']:
        t = e.get('tags', {})
        if e['type'] != 'way' or 'geometry' not in e: continue
        if t.get('highway') in ROAD_CLASSES and t.get('area') != 'yes':
            lay = num(t.get('layer')) or 0.0
            if t.get('tunnel', 'no') != 'no' or lay < 0 or t.get('covered') == 'yes':
                n_elev += 1; continue
            # elevated roads (terminal departures level, flyovers): kept as kind 'elevated' - their FOOTPRINT is paved
            # ground in the bake (the viaducts stand on roads / pavement), but they are not drawn as an at-grade road
            elev = t.get('bridge', 'no') != 'no' or lay >= 1
            ls = LineString(world(e['geometry']))
            if ls.length < 1.0: continue
            lvl = num(t.get('level')); mN = _re.search(r'\bLevel\s*(\d+)', t.get('name', '') or '')
            elev_why = None
            if not elev and lvl is not None and lvl > 0: elev, elev_why = True, 'level %s' % t['level']
            elif not elev and mN and int(mN.group(1)) >= 2: elev, elev_why = True, 'name %s' % t['name']
            elif not elev and t.get('service') == 'parking_aisle' and garage_u.contains(ls.interpolate(0.5, normalized=True)) \
                    and ls.intersection(garage_u).length > 0.8 * ls.length:
                elev, elev_why = True, 'parking aisle inside a multi-storey garage footprint'
            if t.get('highway') == 'service' and t.get('access') == 'no' and \
                    (min(r.distance(ls) for r in rw_lines) < AIRFIELD_M or tw_union.distance(ls) < AIRFIELD_TW_M):
                paths.extend(measure_path(e, ls, t)); continue
            keep = ls.difference(airside)
            if keep.is_empty: n_air += 1; continue
            parts = list(keep.geoms) if isinstance(keep, MultiLineString) else [keep] if keep.geom_type == 'LineString' else []
            w = num(t.get('width')); src = 'osm width'
            if w is None and num(t.get('lanes')):
                w = num(t['lanes']) * 3.6; src = 'osm lanes x 3.6 m (inferred lane width)'
            if w is None:
                w = DEFAULT_W[t['highway']] + (2.0 if t.get('service') == 'parking_aisle' else 0.0); src = 'class default (inferred)'
            for p in parts:
                if p.length < 2.0: continue
                roads.append({'osm_id': e['id'], 'kind': t['highway'], 'w': round(w, 1), 'w_src': src, 'elevated': elev,
                              **({'elevated_why': elev_why} if elev_why else {}),
                              'pts': [[round(x, 1), round(z, 1)] for x, z in p.simplify(0.5).coords]})
        elif t.get('amenity') == 'parking' and t.get('parking') in (None, 'surface', 'street_side', 'lane', 'multi-storey'):
            pts = world(e['geometry'])
            if len(pts) < 4 or pts[0] != pts[-1] and np.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.5: continue
            pg = Polygon(pts).buffer(0).difference(airside)
            for g in (getattr(pg, 'geoms', None) or [pg]):
                if g.is_empty or g.area < 50: continue
                parks.append({'osm_id': e['id'], 'kind': 'garage' if t.get('parking') == 'multi-storey' else 'parking', 'access': t.get('access'),
                              'pts': [[round(x, 1), round(z, 1)] for x, z in list(g.simplify(0.5).exterior.coords)[:-1]]})
    retired = {(r_['name'], r_['poly']) for r_ in json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json'))).get('pavementRetired', []) if r_['layer'] == 'taxiways'}
    clip = unary_union([Polygon(poly[0], poly[1:]).buffer(0) for r_ in A['runways'] for poly in r_['polys']] +
                       [Polygon(poly[0], poly[1:]).buffer(0) for t_ in A['taxiways'] for i_, poly in enumerate(t_['polys']) if (t_['name'], i_) not in retired])
    paths = clip_paved(paths, clip)
    footprint_fix(paths)
    # round 3: NAIP 2024 grey level (0-255, median along the drawn centreline, every 2 m) per drawn path - the imaged tone
    # for the renderer (the OSM-asphalt perimeter road images as light as the concrete paths: medians ~198 vs ~206)
    N_ = _naip(); m_ = N_['m']
    for r_ in paths:
        if not r_['drawn']: continue
        ls_ = LineString(r_['pts']); v_ = []
        for s_ in np.arange(0, ls_.length + 1e-9, 2.0):
            q_ = ls_.interpolate(s_); rr_ = int((q_.y - m_['z0']) / m_['res']); cc_ = int((q_.x - m_['x0']) / m_['res'])
            if 0 <= rr_ < N_['im'].shape[0] and 0 <= cc_ < N_['im'].shape[1]: v_.append(float(np.asarray(N_['im'][rr_, cc_], np.float32).mean()))
        if v_: r_['naip_grey'] = round(float(np.median(v_)))
    res = {'frame': GF.FRAME_ID,
           'licence': 'ODbL 1.0 - contains information from OpenStreetMap (c) OpenStreetMap contributors, '
                      'https://www.openstreetmap.org/copyright; see docs/ATTRIBUTION.md',
           'source': 'OSM %s, database %s (%s; pinned, tools/xcheck/fetch_osm.py)' % (', '.join(meta['endpoint']) if isinstance(meta['endpoint'], list) else meta['endpoint'], meta['osm_base'], meta['file']),
           'note': 'landside roads (OSM centrelines with widths: osm width / lanes x 3.6 m / class default - see w_src; '
                   'elevated = bridge / layer >= 1: only their footprint counts as paved ground, not an at-grade road) and car '
                   'parks (kind parking = surface, garage = multi-storey footprint), clipped out of the airside (OSM aprons, '
                   'SFO Museum taxiways / runways / terminal complex, the ramp outline of sfo_details.json, + 2 m); tunnels '
                   'and layer < 0 are not included. Generated by '
                   'tools/build_landside.py; replaces the hand-drawn landside() of js/world/airfield.js in the live app.',
           'roads': roads, 'parking': parks, 'airside_paths': paths,
           'airside_paths_note': ('OSM highway=service + access=no on the airfield (within %d m of a runway centreline or %d m of SFO Museum '
                                  'taxiway pavement): infield / perimeter vehicle paths, concrete; one entry per stretch (`part`): drawn where '
                                  'NAIP 2024 images the band (measure_band every %.1f m across the OSM line; gaps < %.0f m bridged), its centre '
                                  'moved by the running-median band offset (+-%.1f m; offset_m = stretch median, offset_range) along '
                                  'measure_band\'s own normal, w = median band width; drawn false where NAIP shows no band (static close-out '
                                  '2026-11-04; piecewise offset with the corrected side, round 2 2026-11-05). Round 3 (2026-11-05): roads '
                                  'wider than the band window measured as a paved run across +-%.0f m (kind_naip road; one width per '
                                  'near-constant-width piece), road gaps inside wider pavement / light ground or < %.0f m bridged along the OSM '
                                  'line (bridged, inferred), drawn parts clipped at SFO Museum runway / taxiway pavement; material = OSM '
                                  'surface (asphalt / concrete; obs) else concrete (inferred) - only concrete goes into the concrete layer; naip_grey = NAIP 2024 grey '
                                  'level (0-255) along the drawn line, the imaged tone' % (
                                      AIRFIELD_M, AIRFIELD_TW_M, PATH_STEP, PATH_GAP, PATH_SMOOTH, ROAD_HALF, ROAD_BRIDGE_ANY))}
    json.dump(res, open(os.path.join(ROOT, 'data', 'sfo_landside.json'), 'w'), separators=(',', ':'))
    open(os.path.join(ROOT, 'data', 'sfo_landside.js'), 'w').write(
        '// generated by tools/build_landside.py - ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap '
        'contributors (docs/ATTRIBUTION.md)\nexport const LANDSIDE = ' + json.dumps(res, separators=(',', ':')) + ';\n')
    from collections import Counter
    print('roads %d (%s), parking %d, elevated / tunnel skipped %d, airside-only skipped %d' % (
        len(roads), dict(Counter(r['w_src'].split(' (')[0] for r in roads)), len(parks), n_elev, n_air))
    print('airside paths: %d ways, %d stretches (%.1f km; drawn %d, %.1f km; median measured width %.2f m, median |offset| %.2f m); elevated by level / name / garage: %d (%.0f m)' % (
        len({p_['osm_id'] for p_ in paths}), len(paths), sum(LineString(p_['pts']).length for p_ in paths) / 1000, sum(p_['drawn'] for p_ in paths),
        sum(LineString(p_['pts']).length for p_ in paths if p_['drawn']) / 1000,
        float(np.median([p_['w'] for p_ in paths if p_['drawn']] or [0])), float(np.median([abs(p_['offset_m']) for p_ in paths if p_['drawn']] or [0])),
        sum(1 for r in roads if r.get('elevated_why')), sum(LineString(r['pts']).length for r in roads if r.get('elevated_why'))))
    print('wrote data/sfo_landside.json / .js (%d KB)' % (os.path.getsize(os.path.join(ROOT, 'data', 'sfo_landside.js')) // 1024))


if __name__ == '__main__':
    main()
