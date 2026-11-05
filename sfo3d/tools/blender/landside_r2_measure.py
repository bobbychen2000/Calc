"""Round-2 review measurements of the 3-D landside group (reference photos with SOLVED cameras + NAIP 2024; measured by the 3-D
group, not yet on the 2-D sheets BL-01..03: each item is listed in data/buildings3d/manifest.json#landside.review_r2 with its tag
and raised with the drawings group in docs/research/buildings3d.md).

    python3 tools/blender/landside_r2_measure.py       -> tools/blender/landside_r2_obs.json (read by landside_geom.py)

Photos are REFERENCE ONLY (refs/cache/buildings/review_likeness, local): numbers are read off them, nothing is copied.
NAIP 2024 (public domain) is used only for plan positions / colours.

Items (tag in brackets):
  garages   Garage A / G heights from photo a2 with its SOLVED camera (out/buildings3d/itb_a2_camera.json, tools/blender/
            itb_a2_solve.py: 10 picks on BA-G + the Grand Hyatt top 44 m [inf]): the parapet top edge found column by column
            (bright roof deck above, grey parapet band below) and solved for the height of the body outline's near top edge;
            the level rows (dark open strips) solved the same way -> the level pitch; the Garage A drum ring, rooftop penthouse
            and the NE rotunda by overlaying candidate heights (pixel picks below). Camera sensitivity: re-solving with the Hyatt
            at 40 / 48 m moves the garage heights by -2.4 / +2.4 m (cam_sensitivity) [obs a2, low]
  i2        the drum slots and tower windows of photo i2 in units of the level pitch (32 px per level on both; tower 85 px wide
            = 8.9 m at 3.35 m per level) - the r1 reading had scaled them by the drum width (5.7 px/m), which made the levels
            5.6 m and the towers 15 m wide [obs i2]
  bart      SFO BART station north face from a2 with the solved camera: colonnade top, white spandrel, green glazed band, body top
            (four columns, x 1100-1700) [obs a2]
  l5_rake   RCC station tower top: the raked cut plane fitted to the photo-l5 silhouette (sky / tower boundary per column) with
            the r1 l5 camera (landside_r1_obs.json photos.l5_camera) [obs l5]
  cg_roof   Central-garage roof rims (beige curbs) and stall-free lobes re-traced with smooth outlines (mask blurred 1.5 / 3 px
            before contouring, so the bands have crisp curved edges instead of the 0.5-m pixel staircase), the beige colour from
            the beige pixels themselves (the r1 median over a 0.6-m inset mixed in the deck) [obs NAIP 2024]
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
OUT = os.path.join(HERE, 'landside_r2_obs.json')
REF = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'review_likeness')
CAM_A2 = os.path.join(ROOT, 'out', 'buildings3d', 'itb_a2_camera.json')
W2, H2 = 1920, 1280

# ------------------------------------------------------------------------------------------------ a2 picks (photo px, 1920 x 1280)
# columns where the garage's near parapet edge is seen against its own roof deck (Garage A: the north face west of the curved
# NE end; Garage G: the curved east end above the BART / AirTrain station roof); window = rows searched for the edge
A2_COLS = {'garage_a': (list(range(420, 700, 20)), (380, 412)), 'garage_g': ([890, 900, 910, 920, 930, 940, 950, 960], (520, 545))}
DARK = {'garage_a': 105, 'garage_g': 70}       # first dark row under the band (deep level opening; G: the band's dark foot)
BRIGHT = {'garage_a': 172, 'garage_g': 180}  # roof deck brightness above the band
# Garage A penthouse (a2 6x zoom over the NAIP box): base on the deck where the cars stand, open lower storey (dark, braced),
# solid upper part; tops read against the overlays at 26.8 / 29.5 / 33 / 36 m [obs a2]
A2_PENTHOUSE = dict(base='deck (cars on the deck line beside it)', open_top=29.6, top=36.0)
# Garage A NE rotunda (a2: x 161-255, top rim y 350-357; NAIP 2024: a ~17-m disc, its imaged rim centre (-1380.0, 506.3) leaned
# east; a2 puts the cylinder ~20 px (3.6 m) further WNW than the lean-corrected NAIP centre -> half of it taken) [obs a2 / NAIP]
A2_ROTUNDA = dict(D=16.5, top=36.5, naip_rim_centre=(-1380.0, 506.3), centre=(-1397.5, 505.5),
                  note='a2: 94 px wide at 5.8 px/m (16.2 m), the top rim against overlays at 32 / 34 / 36 m: ~36.5; NAIP rim centre '
                       'minus the measured lean (0.449 m/m x 36.5 = 16.4 m) = x -1396.4; a2 fit ~3.6 m further WNW; the reviewer '
                       'located it at the WEST end - looking SSW in a2, the left end of Garage A is its EAST (curved NE) end')
# Garage A drum ring (a2 6x zoom: the curved ring wall at the west end, its base on the deck, its top edge between the 29 and 31
# m overlays) [obs a2, low]
A2_DRUM_RING = 31.0
# i2 profile (x 1720-1820, 1920 x 1440): drum ring top y 561; top opening dark rows 596 / 603; slots (dark) at 640, 675, 707, 738,
# 766; tower windows at the same 32-px spacing; left tower 1605-1690 px wide [obs i2]
I2 = dict(ring_y=561, top_open_y=(596, 603), slots_y=[640, 675, 707, 738, 766], px_per_level=32.0, tower_px=85.0)
# BART north face (a2 profiles x 1100 / 1300 / 1500 / 1700, heights from the solved camera on the OSM north edge)
BART_PICKS = {1100: dict(colonnade_top=6.1, band=(9.3, 13.8), top=17.7), 1300: dict(colonnade_top=5.8, band=(9.3, 13.7), top=17.6),
              1500: dict(colonnade_top=5.4, band=(8.5, 13.3), top=None), 1700: dict(colonnade_top=5.9, band=(9.5, 13.3), top=17.5)}


def a2_proj(cam, X):
    cx, cz, ch, az, el, roll, f = cam['x'], cam['z'], cam['h'], cam['az'], cam['el'], cam['roll'], cam['f_px']
    a, e, r = np.radians(az), np.radians(el), np.radians(roll)
    fwd = np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])
    right = np.array([np.cos(a), np.sin(a), 0.0]); up = np.cross(fwd, right)
    right, up = right * np.cos(r) + up * np.sin(r), up * np.cos(r) - right * np.sin(r)
    d = np.asarray(X, float) - np.array([cx, cz, ch]); zc = d @ fwd
    return np.stack([W2 / 2 + f * (d @ right) / zc, H2 / 2 - f * (d @ up) / zc], 1)


def garages():
    from PIL import Image
    from shapely.geometry import LineString, Polygon
    import draw_landside as DL
    import landside_geom as G
    cam = json.load(open(CAM_A2))['camera']
    im = np.asarray(Image.open(os.path.join(REF, 'a2.jpg')).convert('L'), float)
    out = {}
    for k, (cols, (y0, y1)) in A2_COLS.items():
        GG = DL.ggeom(k); c, a, b, L, Lb = GG['c'], GG['a'], GG['b'], GG['L'], GG['Lb']
        P = G.sfom_union(DL.GAR[k]['nm'])
        cut = Polygon([c + a * (-L / 2 - 60) + b * 200, c + a * (Lb - L / 2) + b * 200, c + a * (Lb - L / 2) - b * 200, c + a * (-L / 2 - 60) - b * 200])
        body = G.largest(P.intersection(cut))
        ls = LineString(body.exterior.coords)
        ring = np.array([ls.interpolate(t).coords[0] for t in np.arange(0, ls.length, 0.25)])
        rows = []
        for x in cols:
            # the grey parapet band sits on the first dark row (top level opening / station roof edge); walk up through the band
            # until the bright roof deck: the near top edge
            p = im[y0:y1 + 20, x - 2:x + 3].mean(1)
            dk = next((i for i in range(len(p)) if p[i] < DARK[k] and i > 4), None)
            if dk is None: continue
            i = dk - 1
            while i > 0 and p[i] < BRIGHT[k]: i -= 1
            ye = y0 + i + 0.5
            # height whose near top edge (max image y of the body ring at this column) is at ye
            hs = np.arange(15.0, 45.0, 0.05); best = None
            for h in hs:
                q = a2_proj(cam, np.c_[ring, np.full(len(ring), h)])
                m = np.abs(q[:, 0] - x) < 1.0
                if not m.any(): continue
                yy = q[m, 1].max()
                if best is None or abs(yy - ye) < best[1]: best = (h, abs(yy - ye))
            rows.append(dict(x=x, edge_y=ye, h=round(float(best[0]), 2)))
        hv = np.array([r['h'] for r in rows])
        core = hv[np.abs(hv - np.median(hv)) < 1.5]           # columns where the edge search stopped on a level row are dropped
        out[k] = dict(parapet_cols=rows, parapet_median=round(float(np.median(hv)), 2), parapet_iqr=[round(float(np.percentile(hv, 25)), 2), round(float(np.percentile(hv, 75)), 2)],
                      parapet=round(float(np.median(core)), 2), parapet_n=int(len(core)), parapet_spread=[round(float(core.min()), 2), round(float(core.max()), 2)])
    # Garage A level rows: deep dark rows at the same heights over x 420-690 (meas. with the near-face base point per column)
    out['garage_a']['level_rows'] = dict(h=[25.3, 22.0, 18.6, 15.3], pitch=3.34, cols='x 420-690 every 30 px (spread <= 0.3 m)',
                                         note='dark open strips 1.6-1.7 m alternating deep / shallow; the deep ones every 3.34 m; with '
                                              'L1 at grade they extrapolate to the 9 levels [pub] (roof deck 8 x 3.34 = 26.7 m)')
    out['garage_a']['penthouse'] = A2_PENTHOUSE
    out['garage_a']['rotunda'] = A2_ROTUNDA
    out['garage_a']['drum_ring'] = A2_DRUM_RING
    out['cam_sensitivity'] = dict(hyatt_40=-2.4, hyatt_48=2.4, no_hyatt='degenerate (camera h 95 m, Hyatt 246 px off)',
                                  src='least squares of tools/blender/itb_a2_solve.py with the Hyatt pick at 40 / 48 m: garage heights move -2.4 / +2.4 m')
    return out


def i2_levels():
    p = I2['px_per_level']
    return dict(slot_centres_below_ring=[round((y - I2['ring_y']) / p, 3) for y in I2['slots_y']],
                top_opening_below_ring=[round((y - I2['ring_y']) / p, 3) for y in I2['top_open_y']],
                tower_w_levels=round(I2['tower_px'] / p, 3), units='level pitches',
                note='i2: tower windows and drum slots share a 32-px spacing (one per level); the left tower (85 px) is 8.9 m wide at 3.34 m '
                     'per level (NAIP: 8 x 8 m boxes) - the r1 drum-width scale (5.7 px/m) made it 15 m wide and the levels 5.6 m')


def l5_rake():
    from PIL import Image
    from scipy.optimize import least_squares
    import landside_airtrain as AT
    r1 = json.load(open(os.path.join(HERE, 'landside_r1_obs.json')))['photos']['l5_camera']
    im = np.asarray(Image.open(os.path.join(REF, 'l5.jpg')).convert('RGB'), float)
    W, H = r1['image']; f = float(r1['f_px'])
    cols = np.arange(960, 1302, 4); top = []
    for x in cols:
        c = im[100:600, x - 1:x + 2].mean(1)
        sky = (c[:, 2] > c[:, 0] + 25) & (c[:, 2] > 140)
        top.append(100 + int(np.argmax(~sky)))
    top = np.array(top, float)
    cam = np.array([-2276.6, -1092.7]); yaw, pitch = math.radians(185.5), math.radians(4.0)
    eye0 = 8.0 + 1.73                                   # the r1 solve: platform 8.0 + eye 1.73 m

    def proj(P, eye):
        fwd = np.array([math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
        right = np.array([math.cos(yaw), math.sin(yaw), 0.0]); up = np.cross(fwd, right)
        d = np.asarray(P, float) - np.array([cam[0], cam[1], eye]); zc = d @ fwd
        return np.stack([W / 2 + f * (d @ right) / zc, H / 2 - f * (d @ up) / zc], 1)
    T = np.array(AT.RCC_TOWER['centre']); r = AT.RCC_TOWER['D'] / 2; ztop = AT.RCC_TOWER['top']

    def sil(q):
        rake, hb, dz, dx = q
        th = np.linspace(0, 2 * np.pi, 720); thhi = math.radians(90 - hb)
        X = T[0] + dx + r * np.cos(th); Z = T[1] - r * np.sin(th)
        h = ztop + dz - rake * (1 - np.cos(th - thhi)) / 2
        p = proj(np.c_[X, Z, h], eye0)
        return np.array([p[np.abs(p[:, 0] - x) < 2.5, 1].min() if (np.abs(p[:, 0] - x) < 2.5).any() else np.nan for x in cols])

    def res(q):
        s = sil(q) - top; s[np.isnan(s)] = 50; return s
    best = None
    for hb in range(0, 360, 30):
        for rake in (0.5, 1.5, 2.5, 4.0):
            s = least_squares(res, [rake, hb, 0.0, 0.0], bounds=([0, -720, -3, -3], [8, 720, 3, 3]))
            if best is None or s.cost < best.cost: best = s
    q = best.x
    flat = float(np.sqrt(np.nanmean((sil([0, 0, 0, 0]) - top) ** 2)))
    old = float(np.sqrt(np.nanmean((sil([2.5, 236.0, 0, 0]) - top) ** 2)))
    return dict(rake=round(float(q[0]), 2), high_bearing=round(float(q[1]) % 360, 1), dz=round(float(q[2]), 2), dx=round(float(q[3]), 2),
                rms_px=round(float(np.sqrt(np.mean(best.fun ** 2))), 1), rms_flat_px=round(flat, 1), rms_r1_px=round(old, 1),
                platform=round(8.0 - float(q[2]), 2),
                note='the top edge is an arch highest mid-left: a cut plane rising TOWARD the camera (north), 2.55 m over the 4.7-m '
                     'diameter; its high point sits dz below the DOF TANK top for the r1 eye -> keeping the top at the DOF value [pub] '
                     'raises the eye / platform by -dz (r1 had a 2.5-m rake toward bearing 236: rms_r1_px)')


def cg_roof():
    """rims / lobes with smooth outlines; beige colour from the beige pixels."""
    import cv2
    import draw_lib as DLb
    import landside_geom as G
    import landside_airtrain as AT
    from shapely.geometry import Polygon
    from shapely import affinity
    from shapely.ops import unary_union
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
    cut = unary_union([AT.RAIL] + [AT.ST_POLY[k] for k in ('T1', 'T2', 'T3')]).buffer(2.0)
    deck = raster(affinity.translate(full.buffer(-3.0).difference(cut), *sh))
    void_c = np.array([-930.8, 275.5])
    yy, xx = np.mgrid[0:H, 0:W]
    wx = T['x0'] + (c0 + xx + 0.5) * R - sh[0]; wz = T['z0'] + (r0 + yy + 0.5) * R - sh[1]
    ring = np.hypot(wx - void_c[0], wz - void_c[1]) < 56.0
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    Y = 0.299 * r + 0.587 * g + 0.114 * b
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    beige = (((r - b) > 22) & (r > 150) & ((g - b) > 8) & (deck > 0) & ~ring).astype(np.uint8)
    beige = cv2.morphologyEx(beige, cv2.MORPH_OPEN, k3)
    core = cv2.erode(beige, k3)                               # beige pixels away from the band edges (colour sample)
    rgb_beige = np.median(im[core > 0], 0) if core.sum() > 50 else np.median(im[beige > 0], 0)
    Yb = cv2.blur(Y, (7, 7)); Y2 = cv2.blur(Y * Y, (7, 7)); sd = np.sqrt(np.maximum(Y2 - Yb * Yb, 0))
    lobe = ((Yb > 228) & (sd < 5.0) & (deck > 0) & ~ring).astype(np.uint8)
    lobe = cv2.morphologyEx(lobe, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    lobe = cv2.morphologyEx(lobe, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))

    def vec(mask, sigma, min_area, simp):
        # smooth outline: blur the 0 / 1 mask, contour the 0.5 level on a 4x upsampled grid (sub-pixel curved edges)
        up = 4
        m = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
        m = cv2.resize(m, (W * up, H * up), interpolation=cv2.INTER_LINEAR)
        mm = (m > 0.5).astype(np.uint8)
        cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        out = []
        for cc in cs:
            if cv2.contourArea(cc) * (R / up) ** 2 < min_area: continue
            pts = [toW((p[0][0] + 0.5) / up - 0.5, (p[0][1] + 0.5) / up - 0.5) for p in cc]
            P = Polygon([(x - sh[0], z - sh[1]) for x, z in pts]).buffer(0).simplify(simp)
            P = P.intersection(full.buffer(-1.5))
            for q in G.polys(P):
                if q.area >= min_area:
                    out.append([[round(x, 2), round(z, 2)] for x, z in q.exterior.coords])
        return out
    rims = vec(beige, 1.2, 6.0, 0.12)
    lobes = vec(lobe, 3.0, 150.0, 0.25)
    return dict(roof_shift=list(sh), rims=rims, lobes=lobes, rim_rgb=[int(round(v)) for v in rgb_beige],
                stats=dict(rim_m2=round(sum(Polygon(q).area for q in rims), 1), lobe_m2=round(sum(Polygon(q).area for q in lobes), 1),
                           beige_px=int(beige.sum()), core_px=int(core.sum())),
                method='r1 masks (beige R-B > 22, R > 150, G-B > 8; lobes 3.5-m mean > 228, s.d. < 5) blurred (1.2 / 3.0 px) and contoured '
                       'at 0.5 on a 4x grid, simplified 0.12 / 0.25 m; rim colour = median of the beige pixels 1 px inside the mask')


def main():
    out = dict(generated_by='tools/blender/landside_r2_measure.py', frame='ltp-nad83-2011 (x east, z south, m from the ARP)',
               a2_camera='out/buildings3d/itb_a2_camera.json (tools/blender/itb_a2_solve.py)',
               garages=garages(), i2=i2_levels(), bart=dict(picks={str(k): v for k, v in BART_PICKS.items()},
                                                           colonnade_top=5.9, band=(9.2, 13.5), top=17.6,
                                                           note='a2 solved camera on the OSM north edge, columns x 1100-1700; the lower '
                                                                'colonnade is hidden behind BA-G (its foot not seen) [obs a2]'),
               l5_rake=l5_rake(), cg_roof=cg_roof())
    json.dump(out, open(OUT, 'w'), indent=1)
    g = out['garages']
    print('->', OUT)
    print(' Garage A parapet', g['garage_a']['parapet'], g['garage_a']['parapet_spread'], g['garage_a']['parapet_n'], ' Garage G parapet', g['garage_g']['parapet'], g['garage_g']['parapet_spread'], g['garage_g']['parapet_n'])
    print(' l5 rake', {k: v for k, v in out['l5_rake'].items() if k != 'note'})
    print(' i2', out['i2']['slot_centres_below_ring'], out['i2']['top_opening_below_ring'])
    print(' cg rims', len(out['cg_roof']['rims']), 'lobes', len(out['cg_roof']['lobes']), out['cg_roof']['rim_rgb'], out['cg_roof']['stats'])


if __name__ == '__main__':
    main()
