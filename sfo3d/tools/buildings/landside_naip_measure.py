"""Landside buildings - NAIP 2024 / SFO Museum / FAA DOF measurements for the research spec
(tools/buildings/spec_landside.json, docs/research/buildings_landside.md). Research tool: it writes numbers only
(tools/buildings/landside_naip_measurements.json) plus QA overlays with NAIP pixels to out/buildings/landside/ (local,
not committed). Nothing in js/ or data/ is read-write; data/sfo_airport.json is read only.

What it measures, per landside building (Central / Domestic garage, International Garages A and G, Long-Term Parking
Garages 1 and 2, Rental Car Center, Grand Hyatt, Consolidated Administration Campus, Superbay hangar):
  1. Footprint metrics of the SFO Museum polygon (data/sfo_airport.json, CDLA-Permissive-1.0): area, perimeter,
     minimum-area rectangle (length, width, heading of the long side, true heading clockwise from north), holes.
  2. FAA Digital Obstacle File (DOF.CSV of 2026-09-18, extract refs/cache/lighting/dof_sfo_4500m.json) obstacles
     inside or within 10 m of the footprint. DOF horizontal datum is WGS 84 (DOF_README) -> geo_frame.wgs84_to_world.
  3. Roof relief shift ("lean"). NAIP is orthorectified to a terrain model, so a roof at height h is imaged displaced
     by k*h away from the frame nadir (docs/research/imagery.md s.6). The tool slides the footprint polygon east
     (dx = 0..30 m, 0.5 m steps) over the NAIP gradient image and scores the mean |gradient . edge normal| along the
     polygon edges (0.25 m/px, Gaussian sigma 1 px, Sobel). The best dx is the roof edge IF the polygon is a true
     ground footprint; h = dx / k(x) with the east-lean model of the ITB study, k(x) = 0.7553 + 0.0002753 * x
     (fitted on five DOF 1A poles of 153-157 ft at x = -1622..-1346, docs/research/buildings_itb.md s.2.2).
     CAVEATS (stated in the spec): the SFO Museum polygon may itself be a roof trace (src 'sfomuseum'); several peaks
     occur (facade base, parapet, rooftop towers, canopies); k(x) is extrapolated outside x = -1622..-1346 and is only
     valid for the NAIP frame that images the terminal area. Results are therefore [obs, low confidence] checks.
  4. Parked cars on roof decks: roof region = footprint shifted by the chosen dx, eroded 3 m; candidate car pixels =
     CIE-Lab distance > 16 from a 9 m median background, opened 3x3 px, blobs 2-250 m^2 with minor extent <= 12 m;
     count = sum over blobs of max(1, round(area / 9 m^2)) (9 m^2 ~ 4.7 x 1.9 m car). White/silver cars on a pale
     deck are partly missed and merged rows are counted by area, so counts are +-30 % (one manual check: LTP Garage 1
     window x -2225..-2185, z -2010..-1970 = 1,600 m^2: 28 cars counted by eye vs 34 by the detector).
     Row direction = perpendicular to the dominant gradient of the blurred car mask (structure tensor).

Usage:  python3 tools/buildings/landside_naip_measure.py            (about 1 min)
Inputs: refs/cache/naip/naip_2024_world_0.5m_bgr.npy + .json (frame ltp-nad83-2011), data/sfo_airport.json,
        refs/cache/lighting/dof_sfo_4500m.json
Outputs: tools/buildings/landside_naip_measurements.json, out/buildings/landside/qa_*.jpg
"""
import json
import math
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from landside_common import (G, OUT, RES, airport, crop, dof, min_rect, ring_area, ring_perimeter,  # noqa: E402
                             structures)

OUT_JSON = os.path.join(HERE, 'landside_naip_measurements.json')
FT = 0.3048

# ITB east-lean model (docs/research/buildings_itb.md s.2.2): k = image shift per metre of height, direction 87-95 deg
K_A, K_B, K_XRANGE = 0.7553, 0.0002753, (-1622.0, -1346.0)

BUILDINGS = [
    # name in data/sfo_airport.json, short id, roof shift used for the roof-deck region (m, x east / z south) and why
    ('Central Parking Garage', 'central_garage', (4.0, 0.0), 'best 1-D/2-D gradient peak (3-5 m); weak'),
    ('Garage A', 'garage_a', (13.0, 0.0), '1-D and 2-D gradient peak'),
    ('Garage G', 'garage_g', (12.0, 0.0), '1-D gradient peak (2-D ambiguous)'),
    ('Long-Term Parking Garage 1', 'ltp_garage_1', (5.5, 0.0), '1-D and 2-D gradient peak'),
    ('Long-Term Parking Garage 2', 'ltp_garage_2', (1.5, 1.5), '2-D gradient peak'),
    ('Rental Car Center', 'rental_car_center', (3.0, 0.0), '1-D gradient peak'),
    ('Grand Hyatt Hotel', 'grand_hyatt', None, 'no roof deck parking'),
    ('Consolidated Administration Campus', 'cac', None, 'no roof deck parking'),
    ('Super Bay Hangar Building', 'superbay', None, 'no roof deck parking'),
]


def k_of_x(x):
    return K_A + K_B * x


def footprint(name):
    s = structures(name=name)[0]
    polys = s['polys']
    A = sum(ring_area(p[0]) - sum(ring_area(h) for h in p[1:]) for p in polys)
    P = sum(ring_perimeter(p[0]) for p in polys)
    allp = np.vstack([np.array(p[0], float) for p in polys])
    main = max(polys, key=lambda p: ring_area(p[0]))
    cx, cz, L, W, hdg = min_rect(main[0])
    holes = []
    for p in polys:
        for h in p[1:]:
            h = np.array(h, float); c = h.mean(0); r = np.hypot(*(h - c).T)
            holes.append(dict(centre=[round(c[0], 1), round(c[1], 1)], mean_diameter_m=round(2 * r.mean(), 1),
                              area_m2=round(ring_area(h), 0)))
    return dict(sfom_id=s['id'], kind=s['kind'], n_polys=len(polys), area_m2=round(A, 0), perimeter_m=round(P, 0),
                bbox=[round(v, 1) for v in (*allp.min(0), *allp.max(0))],
                min_rect=dict(centre=[round(cx, 1), round(cz, 1)], length_m=round(L, 1), width_m=round(W, 1),
                              long_side_heading_deg=round(hdg, 1)),
                holes=holes)


def _inside(pt, r):
    x, z = pt; c = False
    for i in range(len(r)):
        x1, z1 = r[i]; x2, z2 = r[i - 1]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            c = not c
    return c


def _dist(pt, r):
    if _inside(pt, r):
        return 0.0
    best = 1e9
    for i in range(len(r)):
        x1, z1 = r[i]; x2, z2 = r[i - 1]; dx, dz = x2 - x1, z2 - z1; L = dx * dx + dz * dz
        t = 0 if L == 0 else max(0, min(1, ((pt[0] - x1) * dx + (pt[1] - z1) * dz) / L))
        best = min(best, math.hypot(pt[0] - x1 - t * dx, pt[1] - z1 - t * dz))
    return best


def dof_on(name, D, margin=10.0):
    s = structures(name=name)[0]
    out = []
    for o in D:
        d = min(_dist((o['x'], o['z']), p[0]) for p in s['polys'])
        if d <= margin and int(o['AGL']) >= 15:
            out.append(dict(oas=o['OAS'], type=o['TYPE'], agl_ft=int(o['AGL']), amsl_ft=int(o['AMSL']),
                            agl_m=round(int(o['AGL']) * FT, 1), acc=o['ACCURACY'], lighting=o['LIGHTING'],
                            study=o['FAA STUDY'], jdate=o['JDATE'], world=[round(o['x'], 1), round(o['z'], 1)],
                            dist_to_footprint_m=round(d, 1)))
    return sorted(out, key=lambda r: -r['agl_ft'])


def shift_scan(name, dxs=np.arange(-10, 30.01, 0.5)):
    s = structures(name=name)[0]
    r = np.array(max(s['polys'], key=lambda p: ring_area(p[0]))[0], float)
    x0, z0 = r.min(0) - 40; x1, z1 = r.max(0) + 40
    img, f = crop(x0, z0, x1, z1, scale=2)
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gz = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    P = []; N = []
    for i in range(len(r)):
        a = r[i - 1]; b = r[i]; L = np.hypot(*(b - a))
        if L < 4:
            continue
        t = (b - a) / L; n = np.array([-t[1], t[0]])
        for u in np.arange(1, L - 1, 0.5):
            P.append(a + t * u); N.append(n)
    P = np.array(P); N = np.array(N)
    scores = []
    for dx in dxs:
        c = np.array([f(*q) for q in P + np.array([dx, 0.0])])
        ci = np.clip(np.round(c).astype(int), 0, [gx.shape[1] - 1, gx.shape[0] - 1])
        Gv = np.stack([gx[ci[:, 1], ci[:, 0]], gz[ci[:, 1], ci[:, 0]]], -1)
        scores.append(float(np.abs((Gv * N).sum(1)).mean()))
    scores = np.array(scores)
    # local maxima, strongest first
    peaks = [i for i in range(1, len(scores) - 1) if scores[i] >= scores[i - 1] and scores[i] >= scores[i + 1]]
    peaks = sorted(peaks, key=lambda i: -scores[i])[:4]
    cx = float(r[:, 0].mean()); k = k_of_x(cx)
    return dict(k_model=round(k, 3), k_extrapolated=not (K_XRANGE[0] <= cx <= K_XRANGE[1]), centroid_x=round(cx, 1),
                peaks=[dict(dx_m=float(dxs[i]), score=round(float(scores[i]), 1),
                            h_if_true_footprint_m=round(float(dxs[i]) / k, 1) if dxs[i] > 0 else None) for i in peaks],
                profile=[[float(d), round(float(sv), 1)] for d, sv in zip(dxs, scores)])


def roof_cars(name, shift, tag, erode_m=3.0, scale=2, T=16.0):
    s = structures(name=name)[0]
    rings = [np.array(p[0], float) + np.array(shift) for p in s['polys']]
    holes = [np.array(h, float) + np.array(shift) for p in s['polys'] for h in p[1:]]
    allp = np.vstack(rings); x0, z0 = allp.min(0) - 10; x1, z1 = allp.max(0) + 10
    img, f = crop(x0, z0, x1, z1, scale=scale)
    m = np.zeros(img.shape[:2], np.uint8)
    for r in rings:
        cv2.fillPoly(m, [np.array([f(*q) for q in r], np.int32)], 255)
    for h in holes:
        cv2.fillPoly(m, [np.array([f(*q) for q in h], np.int32)], 0)
    px = RES / scale
    kk = int(round(erode_m / px))
    m = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * kk + 1, 2 * kk + 1)))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    ksz = int(round(9.0 / px)) | 1
    bg = np.stack([cv2.medianBlur(lab[..., i].astype(np.uint8), ksz) for i in range(3)], -1).astype(np.float32)
    d = np.sqrt(((lab - bg) ** 2).sum(-1))
    cand = ((d > T) & (m > 0)).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(cand, 8)
    A = st[:, cv2.CC_STAT_AREA] * px * px
    keep = np.zeros(n, bool); cnt = 0
    for i in range(1, n):
        w = st[i, cv2.CC_STAT_WIDTH] * px; h = st[i, cv2.CC_STAT_HEIGHT] * px
        if 2.0 <= A[i] <= 250 and min(w, h) <= 12:
            keep[i] = True; cnt += max(1, int(round(A[i] / 9.0)))
    cm = keep[lbl] & (m > 0)
    area_roof = float((m > 0).sum() * px * px); area_car = float(cm.sum() * px * px)
    gb = cv2.GaussianBlur(cm.astype(np.float32), (0, 0), 2)
    gx = cv2.Sobel(gb, cv2.CV_32F, 1, 0); gz = cv2.Sobel(gb, cv2.CV_32F, 0, 1)
    J = np.array([[(gx * gx).sum(), (gx * gz).sum()], [(gx * gz).sum(), (gz * gz).sum()]])
    w_, v_ = np.linalg.eigh(J); e = v_[:, 1]
    grad_hdg = math.degrees(math.atan2(e[0], -e[1])) % 180
    ov = img.copy(); ov[cm] = (0, 0, 255)
    cs = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]; cv2.drawContours(ov, cs, -1, (0, 255, 255), 1)
    cv2.imwrite(os.path.join(OUT, f'qa_cars_{tag}.jpg'), cv2.addWeighted(ov, 0.5, img, 0.5, 0),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
    return dict(roof_shift_used=list(shift), roof_region_m2=round(area_roof), car_pixels_m2=round(area_car),
                car_pixel_fraction=round(area_car / area_roof, 3), cars_detected=int(cnt),
                cars_per_1000m2=round(1000 * cnt / area_roof, 1),
                car_row_axis_heading_deg=round((grad_hdg + 90) % 180, 0),
                row_axis_coherence=round(float((w_[1] - w_[0]) / (w_[1] + w_[0] + 1e-9)), 2),
                qa=f'out/buildings/landside/qa_cars_{tag}.jpg')


# ------------------------------------------------------------------ United MOC hangars (no SFO Museum footprint)
# Imaged-roof corners picked by eye on NAIP 2024 at 0.25 m/px with a 10 m grid (out/buildings/landside/f_moc_east.png,
# crop_moc.jpg), +-3 m per corner. These are ROOF images (relief shift not removed; DOF heights 116-132 ft would shift a
# roof several metres; the lean direction/magnitude in this NAIP frame was not calibrated). Identities unverified.
MOC_ROOFS = {
    'moc_large_hangar': dict(
        corners_imaged=[(-1683, -2025), (-1606, -2048), (-1528, -1837), (-1604, -1797)],
        dof=['06-035289', '06-035290', '06-035288'],
        note='large multi-bay hangar block, stepped roof (steps at about z -1945 and -1885); apron on the west and '
             'south; biggest single roof of the United Maintenance and Operations Center (MOC)'),
    'moc_barrel_hangars': dict(
        corners_imaged=[(-1640, -1790), (-1560, -1790), (-1540, -1640), (-1630, -1640)],
        dof=[],
        note='two side-by-side barrel-vault (arched-roof) hangar bays south of the large hangar, doors on the west '
             '(aircraft parked on the west apron in NAIP); height not in the DOF'),
}


def moc(D):
    Dm = {o['OAS']: o for o in D}
    out = {}
    for key, v in MOC_ROOFS.items():
        c = np.array(v['corners_imaged'], float)
        cx, cz, L, W, hdg = min_rect(c)
        out[key] = dict(corners_imaged=v['corners_imaged'], area_m2=round(ring_area(c.tolist())),
                        min_rect=dict(centre=[round(cx, 1), round(cz, 1)], length_m=round(L, 1), width_m=round(W, 1),
                                      long_side_heading_deg=round(hdg, 1)),
                        dof=[dict(oas=o, agl_ft=int(Dm[o]['AGL']), agl_m=round(int(Dm[o]['AGL']) * FT, 1),
                                  acc=Dm[o]['ACCURACY'], world=[round(Dm[o]['x'], 1), round(Dm[o]['z'], 1)])
                             for o in v['dof']],
                        note=v['note'])
    return out


def rail():
    s = structures(kind='rail')[0]
    A = sum(ring_area(p[0]) - sum(ring_area(h) for h in p[1:]) for p in s['polys'])
    P = sum(ring_perimeter(p[0]) + sum(ring_perimeter(h) for h in p[1:]) for p in s['polys'])
    allp = np.vstack([np.array(p[0]) for p in s['polys']]); x0, z0 = allp.min(0) - 5; x1, z1 = allp.max(0) + 5
    r = 0.25; W = int((x1 - x0) / r) + 1; H = int((z1 - z0) / r) + 1
    m = np.zeros((H, W), np.uint8)
    for p in s['polys']:
        cv2.fillPoly(m, [((np.array(p[0]) - [x0, z0]) / r).astype(np.int32)], 255)
        for h in p[1:]:
            cv2.fillPoly(m, [((np.array(h) - [x0, z0]) / r).astype(np.int32)], 0)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5) * r
    ridge = (dt == cv2.dilate(dt, np.ones((9, 9)))) & (dt > 1)
    w = 2 * dt[ridge]
    return dict(sfom_id=s['id'], area_m2=round(A), perimeter_m=round(P), centreline_length_est_m=round(P / 2),
                width_percentiles_m={str(q): round(float(v), 1) for q, v in zip((10, 25, 50, 75, 90),
                                                                                np.percentile(w, [10, 25, 50, 75, 90]))},
                bbox=[round(v, 1) for v in (*allp.min(0), *allp.max(0))])


def stations():
    out = []; seen = set()
    for s in structures(kind='airtrain'):
        key = s['name'].lower().replace('garaga', 'garage')
        r = max(s['polys'], key=lambda p: ring_area(p[0]))[0]
        cx, cz, L, W, hdg = min_rect(r)
        out.append(dict(name=s['name'], sfom_id=s['id'], area_m2=round(ring_area(r)), length_m=round(L, 1),
                        width_m=round(W, 1), heading_deg=round(hdg, 1), centre=[round(cx, 1), round(cz, 1)],
                        duplicate_name=key in seen))
        seen.add(key)
    return out


def main():
    D = dof()
    res = dict(generated_by='tools/buildings/landside_naip_measure.py', frame=G.FRAME_ID,
               k_model=dict(a=K_A, b=K_B, x_range=K_XRANGE, src='docs/research/buildings_itb.md s.2.2'),
               buildings={}, moc=moc(D), airtrain_rail=rail(), airtrain_stations=stations())
    for name, tag, shift, why in BUILDINGS:
        b = dict(name=name, footprint=footprint(name), dof=dof_on(name, D), shift_scan=shift_scan(name))
        if shift is not None:
            b['roof_cars'] = roof_cars(name, shift, tag)
            b['roof_cars']['shift_reason'] = why
        res['buildings'][tag] = b
        pk = b['shift_scan']['peaks'][0]
        print(f"{tag:18s} area {b['footprint']['area_m2']:>7} m2  rect {b['footprint']['min_rect']['length_m']:.0f}x"
              f"{b['footprint']['min_rect']['width_m']:.0f} hdg {b['footprint']['min_rect']['long_side_heading_deg']:.0f}"
              f"  dof {len(b['dof'])}  scan peak dx {pk['dx_m']} -> h {pk['h_if_true_footprint_m']}"
              + (f"  cars {b['roof_cars']['cars_detected']} ({b['roof_cars']['cars_per_1000m2']}/1000m2)"
                 if 'roof_cars' in b else ''))
    json.dump(res, open(OUT_JSON, 'w'), indent=1)
    print('wrote', OUT_JSON)


if __name__ == '__main__':
    main()
