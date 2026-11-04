"""Adversarial fact-check of the landside-building research (docs/research/buildings_landside.md '## Verification',
tools/buildings/spec_landside.json). Research tool: numbers only, written to out/buildings/landside/verify/verify.json
(local); QA crops with NAIP pixels to out/buildings/landside/verify/ (local, never committed). js/ and data/ are read
only (data/sfo_airport.json footprints).

Sections (python3 tools/buildings/landside_verify.py [dof|fp|shadow|text|all]):
  dof     FAA DOF re-check on a NEWER edition than the research used (DAILY_DOF_CSV.ZIP, DOF.CSV of 2026-11-03,
          refs/cache/lighting/): every obstacle inside or within 15 m of each landside footprint (WGS 84 ->
          geo_frame.wgs84_to_world, as DOF_README states WGS 84 is the horizontal datum), AGL, AMSL, ground = AMSL - AGL,
          accuracy, lighting, action and Julian date, plus a box search for the United MOC.
  fp      footprint metrics re-computed independently (shapely minimum rotated rectangle, not cv2.minAreaRect), the
          Central garage void (area-equivalent and min-enclosing diameters) and the AirTrain rail polygon area.
  shadow  INDEPENDENT height method: the shadow on the ground beyond a building's north-facing walls. A shadow lies on
          the ground, so NAIP's relief displacement (the roof lean the research's roof-shift scans rely on) does not
          move it. The sun is computed from a NOAA solar-position algorithm for 2024-05-20 at SFO; the acquisition
          time is not in the NAIP metadata, so it is found from the shadow AZIMUTH of a tall DOF 1A object in the same
          image region (the research's ITB study used one apron pole) -> elevation e; h = L / cot(e). L is measured
          along the shadow direction u from the footprint's north edge (the SFO Museum outline, assumed a ground trace:
          +-1.5 m per imagery.md s.6 -> +-1.5 / cot e in h) to the shadow's far edge (the steepest dark->bright rise of
          the median luminance profile over the middle 80 % of the edge).
  text    quotes re-read in the re-fetched sources (refs/cache/buildings/landside/src/verify_*.txt, fetched by
          landside_fetch.py): each claim's key phrase searched, the matching line printed.

Inputs: refs/cache/naip/naip_2024_world_0.5m_bgr.npy (+ .json), refs/cache/lighting/DAILY_DOF_CSV.ZIP,
        data/sfo_airport.json, refs/cache/buildings/landside/src/verify_*.txt
Output: out/buildings/landside/verify/verify.json, out/buildings/landside/verify/sh_*.jpg (NAIP pixels, local only)
"""
import csv
import io
import json
import math
import os
import re
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from landside_common import G, ROOT, airport, structures  # noqa: E402

FT = 0.3048
VOUT = os.path.join(ROOT, 'out', 'buildings', 'landside', 'verify')
os.makedirs(VOUT, exist_ok=True)
SRC = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'landside', 'src')
DOF_ZIP = os.path.join(ROOT, 'refs', 'cache', 'lighting', 'DAILY_DOF_CSV.ZIP')
RESULT = os.path.join(VOUT, 'verify.json')

FOOTPRINTS = {   # id -> name in data/sfo_airport.json
    'central_garage': 'Central Parking Garage', 'garage_a': 'Garage A', 'garage_g': 'Garage G',
    'ltp_garage_1': 'Long-Term Parking Garage 1', 'ltp_garage_2': 'Long-Term Parking Garage 2',
    'rental_car_center': 'Rental Car Center', 'grand_hyatt': 'Grand Hyatt Hotel',
    'cac': 'Consolidated Administration Campus', 'superbay': 'Super Bay Hangar Building',
}
MOC_BOX = (-1760.0, -2120.0, -1380.0, -1700.0)   # x0, z0, x1, z1: United MOC (no SFO Museum outline)


def load():
    return json.load(open(RESULT)) if os.path.exists(RESULT) else {}


def save(res):
    json.dump(res, open(RESULT, 'w'), indent=1, default=float)


def polys(name):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    s = structures(name=name)[0]
    return unary_union([Polygon(p[0], p[1:]) for p in s['polys']])


# ------------------------------------------------------------------------------------------------------------ DOF
def dof_rows(radius=4500.0):
    with zipfile.ZipFile(DOF_ZIP) as z:
        info = z.getinfo('DOF.CSV')
        f = io.TextIOWrapper(z.open('DOF.CSV'), encoding='latin-1')
        out = []
        for r in csv.DictReader(f):
            if r['STATE'].strip() != 'CA':
                continue
            lat, lon = float(r['LATDEC']), float(r['LONDEC'])
            if abs(lat - 37.6188) > 0.06 or abs(lon + 122.3754) > 0.07:
                continue
            x, zz = G.wgs84_to_world(lat, lon)
            if math.hypot(x, zz) > radius:
                continue
            out.append(dict(oas=r['OAS'].strip(), type=r['TYPE'].strip(), agl=int(r['AGL']), amsl=int(r['AMSL']),
                            light=r['LIGHTING'].strip(), acc=r['ACCURACY'].strip(), action=r['ACTION'].strip(),
                            jdate=r['JDATE'].strip(), study=r['FAA STUDY'].strip(), verified=r['VERIFIED STATUS'].strip(),
                            x=round(x, 1), z=round(zz, 1)))
    return out, '%04d-%02d-%02d' % info.date_time[:3]


def run_dof(res):
    from shapely.geometry import Point, box
    rows, date = dof_rows()
    out = {'dof_csv_date': date, 'n_within_4500m': len(rows), 'buildings': {}}
    for bid, name in FOOTPRINTS.items():
        P = polys(name)
        hits = []
        for o in rows:
            d = P.distance(Point(o['x'], o['z']))
            if d <= 15.0:
                hits.append(dict(o, dist_outside_m=round(d, 1), agl_m=round(o['agl'] * FT, 1),
                                 ground_ft=o['amsl'] - o['agl']))
        out['buildings'][bid] = sorted(hits, key=lambda h: -h['agl'])
    B = box(*MOC_BOX)
    out['buildings']['united_moc_box'] = sorted([dict(o, agl_m=round(o['agl'] * FT, 1), ground_ft=o['amsl'] - o['agl'])
                                                 for o in rows if B.contains(Point(o['x'], o['z']))
                                                 and o['type'] not in ('POLE',)], key=lambda h: -h['agl'])
    res['dof'] = out
    for bid, hits in out['buildings'].items():
        print(bid, [(h['oas'], h['type'], h['agl'], h['amsl'], h['acc'], h['light'], h['action'], h['jdate'],
                     h['x'], h['z'], h.get('dist_outside_m')) for h in hits])


# ------------------------------------------------------------------------------------------------------ footprints
def run_fp(res):
    from shapely.geometry import Polygon
    out = {}
    for bid, name in FOOTPRINTS.items():
        P = polys(name)
        parts = list(P.geoms) if P.geom_type == 'MultiPolygon' else [P]
        main = max(parts, key=lambda p: p.area)
        R = main.minimum_rotated_rectangle
        c = list(R.exterior.coords)[:4]
        e = [np.subtract(c[1], c[0]), np.subtract(c[2], c[1])]
        L = [float(np.hypot(*v)) for v in e]
        i = int(np.argmax(L))
        hdg = math.degrees(math.atan2(e[i][0], -e[i][1])) % 180.0
        holes = [Polygon(h) for p in parts for h in p.interiors]
        hole_info = []
        for h in holes:
            A = h.area
            # minimum enclosing circle diameter (opencv) and area-equivalent diameter
            import cv2
            (cx, cz), r = cv2.minEnclosingCircle(np.asarray(h.exterior.coords, np.float32))
            hole_info.append(dict(area_m2=round(A, 1), d_area_equiv_m=round(2 * math.sqrt(A / math.pi), 2),
                                  d_min_enclosing_m=round(2 * r, 2), centre=(round(cx, 1), round(cz, 1)),
                                  n_vertices=len(h.exterior.coords) - 1))
        out[bid] = dict(area_m2=round(P.area, 1), n_parts=len(parts), main_rect_L=round(max(L), 1),
                        main_rect_W=round(min(L), 1), main_rect_hdg=round(hdg, 1),
                        centroid=(round(P.centroid.x, 1), round(P.centroid.y, 1)), holes=hole_info,
                        bounds=[round(v, 1) for v in P.bounds])
        print(bid, out[bid])
    res['footprints'] = out



# ---------------------------------------------------------------------------------------------------------- sun
def sun_pos(t_utc, lat=37.6188056, lon=-122.3754167):
    """NOAA solar position (Meeus-based 'General Solar Position' spreadsheet algorithm; ~0.01 deg here).
    Returns (elevation deg, azimuth deg from north clockwise). No refraction (0.005 deg at 72 deg)."""
    jd = t_utc.timestamp() / 86400.0 + 2440587.5
    T = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360
    M = math.radians(357.52911 + T * (35999.05029 - 0.0001537 * T))
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    C = (math.sin(M) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(2 * M) * (0.019993 - 0.000101 * T)
         + math.sin(3 * M) * 0.000289)
    om = math.radians(125.04 - 1934.136 * T)
    lam = math.radians(L0 + C - 0.00569 - 0.00478 * math.sin(om))
    eps = math.radians(23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60
                       + 0.00256 * math.cos(om))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    y = math.tan(eps / 2) ** 2
    L0r = math.radians(L0)
    eot = 4 * math.degrees(y * math.sin(2 * L0r) - 2 * e * math.sin(M) + 4 * e * y * math.sin(M) * math.cos(2 * L0r)
                           - 0.5 * y * y * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * M))
    tst = t_utc.hour * 60 + t_utc.minute + t_utc.second / 60 + eot + 4 * lon
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    cz = math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha)
    az = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(dec) * math.cos(la))) + 180) % 360
    return 90 - math.degrees(math.acos(cz)), az


def sun_from_shadow_az(shadow_az):
    """2024-05-20 (NAIP QQDATE): the time at which the shadow points to shadow_az (deg from north, clockwise),
    searched 08:00-16:00 PDT; returns (PDT 'hh:mm', elevation, cot e)."""
    import datetime as dt
    best = None
    for m in range(15 * 60, 23 * 60):
        t = dt.datetime(2024, 5, 20, m // 60, m % 60, tzinfo=dt.timezone.utc)
        el, az = sun_pos(t)
        d = abs(((az + 180) % 360 - shadow_az + 180) % 360 - 180)
        if best is None or d < best[0]:
            best = (d, '%02d:%02d' % (m // 60 - 7, m % 60), el)
    return best[1], round(best[2], 2), round(1 / math.tan(math.radians(best[2])), 4)


def lum_img(x0, z0, x1, z1, res=0.25):
    """Rec. 601 luminance of NAIP on a res grid over [x0,x1] x [z0,z1]; returns (img, X, Z)."""
    from landside_common import sample
    xs = np.arange(x0, x1, res); zs = np.arange(z0, z1, res)
    X, Z = np.meshgrid(xs, zs)
    bgr = sample(X, Z)
    return 0.114 * bgr[..., 0] + 0.587 * bgr[..., 1] + 0.299 * bgr[..., 2], X, Z


def pole_shadow(x, z, h_m, search=12.0, res=0.25):
    """Matched-filter search for a DOF pole's shadow: base b within +-search m of the DOF point, shadow azimuth
    290..70 deg, line length 0.28 h (inside the shadow for any e > 70 deg). Score = mean luminance 1.5 m either side of
    the line minus mean along it. Then the tip = where the luminance along the best line recovers to the side level.
    Returns dict(az, base, tip_len, score)."""
    import cv2
    R = search + 0.45 * h_m
    img, X, Z = lum_img(x - R, z - R, x + R, z + R, res)
    img = cv2.GaussianBlur(img.astype(np.float32), (0, 0), 0.6 / res * 0.5)
    def at(px, pz):
        from scipy.ndimage import map_coordinates
        c = (np.asarray(px, float) - (x - R)) / res; r = (np.asarray(pz, float) - (z - R)) / res
        return map_coordinates(img, [r, c], order=1, mode='nearest')
    Ls = 0.28 * h_m
    s = np.arange(1.0, Ls, 0.25)
    best = None
    bxs = np.arange(-search, search + 1e-9, 0.5)
    for az in np.arange(290.0, 430.0, 1.0):
        a = math.radians(az % 360)
        u = np.array([math.sin(a), -math.cos(a)]); n = np.array([u[1], -u[0]])
        BX, BZ = np.meshgrid(bxs + x, bxs + z)
        P = (BX[..., None] + s * u[0], BZ[..., None] + s * u[1])
        on = at(P[0], P[1]).mean(-1)
        off = 0.5 * (at(P[0] + 1.5 * n[0], P[1] + 1.5 * n[1]).mean(-1) + at(P[0] - 1.5 * n[0], P[1] - 1.5 * n[1]).mean(-1))
        sc = off - on
        i = np.unravel_index(np.argmax(sc), sc.shape)
        if best is None or sc[i] > best[0]:
            best = (float(sc[i]), az % 360, float(BX[i]), float(BZ[i]))
    sc, az, bx, bz = best
    a = math.radians(az); u = np.array([math.sin(a), -math.cos(a)]); n = np.array([u[1], -u[0]])
    t = np.arange(0.0, 0.6 * h_m, 0.25)
    # the luminaire's shadow is wider than the pole's: take a 3-line max darkness (centre +-0.5 m)
    on = np.min([at(bx + t * u[0] + o * n[0], bz + t * u[1] + o * n[1]) for o in (-0.5, 0, 0.5)], axis=0)
    off = 0.5 * (at(bx + t * u[0] + 2.5 * n[0], bz + t * u[1] + 2.5 * n[1]) +
                 at(bx + t * u[0] - 2.5 * n[0], bz + t * u[1] - 2.5 * n[1]))
    dark = (off - on) > 0.5 * sc
    k = np.where(dark)[0]
    tip = float(t[k.max()]) if len(k) else float('nan')
    return dict(shadow_az=az, base=(round(bx, 1), round(bz, 1)), tip_len_m=round(tip, 2), score=round(sc, 1),
                dof=(x, z))


# ------------------------------------------------------------------------------------------------- shadow heights
SHADOW_AZ = 7.0      # deg; refined per building in SHADOW_CASES where the shadow's side edges show it
CANDIDATES = {       # heights (m) drawn as predicted shadow edges on the QA crops, with their claim
    'central_garage': [(22.0, 'model 22'), (24.7, '81 ft pub')],
    'garage_a': [(25.0, '25 photo'), (30.0, '30'), (35.7, '35.7 scan')],
    'garage_g': [(25.0, '25 photo'), (30.0, '30'), (34.7, '34.7 scan')],
    'ltp_garage_1': [(16.0, 'model 16'), (21.0, '21'), (26.2, '86 ft DOF')],
    'ltp_garage_2': [(18.3, '60 ft inf'), (21.0, '21')],
    'rental_car_center': [(16.5, '54 ft DOF'), (20.1, '66 ft pub')],
    'grand_hyatt': [(36.0, '36'), (44.0, '44 inf'), (48.0, '48')],
    'cac': [(16.0, '16'), (19.5, '64 ft inf'), (22.0, '22')],
    'superbay': [(30.0, '30'), (41.1, '135 ft DOF')],
}


def shadow_dir(az=SHADOW_AZ):
    a = math.radians(az)
    return np.array([math.sin(a), -math.cos(a)])


def edge_shadow_profiles(bid, az=SHADOW_AZ, min_len=12.0, min_cos=0.55, d0=-12.0, d1=30.0, step=0.25):
    """Per footprint edge facing the shadow: median luminance profile along the shadow direction u starting on the
    edge line (SFO Museum outline). d_far = steepest dark->bright rise in d = 1..26 m (Gaussian-smoothed 0.5 m),
    d_roof = steepest bright->dark fall in d = -10..d_far-1 (the imaged roof / parapet edge)."""
    from landside_common import sample
    from scipy.ndimage import gaussian_filter1d
    P = polys(FOOTPRINTS[bid])
    parts = list(P.geoms) if P.geom_type == 'MultiPolygon' else [P]
    u = shadow_dir(az)
    out = []
    for part in parts:
        ring = np.asarray(part.exterior.coords)
        ccw = part.exterior.is_ccw          # shapely: in (x, z) axes; outward normal accordingly
        for i in range(len(ring) - 1):
            p0, p1 = ring[i], ring[i + 1]
            t = p1 - p0; L = float(np.hypot(*t))
            if L < min_len:
                continue
            t /= L
            n = np.array([t[1], -t[0]]) if ccw else np.array([-t[1], t[0]])   # outward
            c = float(n @ u)
            if c < min_cos:
                continue
            s = np.arange(0.15 * L, 0.85 * L, 1.0)
            d = np.arange(d0, d1 + 1e-9, step)
            X = p0[0] + s[:, None] * t[0] + d[None, :] * u[0]
            Z = p0[1] + s[:, None] * t[1] + d[None, :] * u[1]
            bgr = sample(X, Z)
            lum = 0.114 * bgr[..., 0] + 0.587 * bgr[..., 1] + 0.299 * bgr[..., 2]
            prof = gaussian_filter1d(np.median(lum, 0), 2.0)
            g = np.gradient(prof, step)
            m = (d >= 1.0) & (d <= 26.0)
            i_far = np.where(m)[0][np.argmax(g[m])]
            m2 = (d >= -10.0) & (d <= d[i_far] - 1.0)
            i_roof = np.where(m2)[0][np.argmin(g[m2])] if m2.any() else i_far
            dark = float(np.median(prof[(d > d[i_roof]) & (d < d[i_far])])) if i_far - i_roof > 2 else float('nan')
            out.append(dict(edge=i, p0=p0.round(1).tolist(), p1=p1.round(1).tolist(), length_m=round(L, 1),
                            n_dot_u=round(c, 3), d_far=round(float(d[i_far]), 2), d_roof=round(float(d[i_roof]), 2),
                            rise=round(float(g[i_far]), 1), fall=round(float(g[i_roof]), 1),
                            lum_beyond=round(float(np.median(prof[(d > d[i_far] + 1) & (d < d[i_far] + 5)])), 1),
                            lum_band=round(dark, 1)))
    return out


def shadow_qa(bid, az=SHADOW_AZ, cot=0.316, pad=45.0, scale=2):
    """QA crop: footprint (cyan) and the shadow edges predicted for each candidate height (h cot e along u)."""
    import cv2
    from landside_common import crop
    P = polys(FOOTPRINTS[bid])
    x0, z0, x1, z1 = P.bounds
    img, f = crop(x0 - pad, z0 - pad, x1 + pad, z1 + pad, scale=scale)
    img = np.ascontiguousarray(img)
    u = shadow_dir(az)
    cols = [(0, 0, 255), (0, 200, 255), (255, 0, 255), (0, 255, 0)]
    parts = list(P.geoms) if P.geom_type == 'MultiPolygon' else [P]
    for part in parts:
        pts = np.array([f(x, z) for x, z in part.exterior.coords], np.int32)
        cv2.polylines(img, [pts], True, (255, 255, 0), 1)
        for k, (h, lab) in enumerate(CANDIDATES.get(bid, [])):
            off = h * cot * u
            pts = np.array([f(x + off[0], z + off[1]) for x, z in part.exterior.coords], np.int32)
            cv2.polylines(img, [pts], True, cols[k % 4], 1)
    for k, (h, lab) in enumerate(CANDIDATES.get(bid, [])):
        cv2.putText(img, lab, (4, 14 + 14 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cols[k % 4], 1)
    cv2.putText(img, f'{bid} az {az} cot {cot}', (4, img.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    path = os.path.join(VOUT, f'sh_{bid}.jpg')
    cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return path


# ------------------------------------------------------------------------------------------- 2-D roof-shift scan
def shift_scan_2d(bid, rng=(-24.0, 24.0), step=0.5):
    """2-D version of the research's roof-shift scan (landside_naip_measure.shift_scan slid the outline EAST only):
    the outline (all rings, edges >= 4 m, sampled every 0.5 m) is slid over (dx, dz) in [rng]^2 and scored by the
    mean |NAIP luminance gradient . edge normal| (0.25 m/px, Gaussian sigma 1 px, Sobel). The best (dx, dz) is the
    imaged roof outline's displacement IF the outline is a ground trace; its direction tests the 'due east' lean that
    the research's height-from-shift values (h = dx / k(x)) assume."""
    import cv2
    from landside_common import crop
    P = polys(FOOTPRINTS[bid])
    parts = list(P.geoms) if P.geom_type == 'MultiPolygon' else [P]
    pts, nrm = [], []
    for part in parts:
        for ring in [part.exterior] + list(part.interiors):
            r = np.asarray(ring.coords)
            for i in range(len(r) - 1):
                a, b = r[i], r[i + 1]; L = np.hypot(*(b - a))
                if L < 4:
                    continue
                t = (b - a) / L
                for s in np.arange(1, L - 1, 0.5):
                    pts.append(a + t * s); nrm.append([-t[1], t[0]])
    pts = np.array(pts); nrm = np.array(nrm)
    x0, z0, x1, z1 = P.bounds
    img, f = crop(x0 - 30, z0 - 30, x1 + 30, z1 + 30, scale=2)
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gz = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    base = np.array([f(*q) for q in pts])               # px for zero shift; 4 px per metre
    v = np.arange(rng[0], rng[1] + 1e-9, step)
    S = np.zeros((len(v), len(v)))
    for j, dz in enumerate(v):
        for i, dx in enumerate(v):
            c = np.round(base + np.array([dx, dz]) * 4.0).astype(int)
            c[:, 0] = np.clip(c[:, 0], 0, gx.shape[1] - 1); c[:, 1] = np.clip(c[:, 1], 0, gx.shape[0] - 1)
            S[j, i] = np.abs(gx[c[:, 1], c[:, 0]] * nrm[:, 0] + gz[c[:, 1], c[:, 0]] * nrm[:, 1]).mean()
    from scipy.ndimage import maximum_filter
    pk = (S == maximum_filter(S, size=7)) & (S > np.percentile(S, 90))
    jj, ii = np.where(pk)
    order = np.argsort(-S[jj, ii])[:5]
    peaks = [dict(dx=float(v[ii[o]]), dz=float(v[jj[o]]), score=round(float(S[jj[o], ii[o]]), 1),
                  shift_m=round(float(np.hypot(v[ii[o]], v[jj[o]])), 1),
                  bearing_deg=round(float(math.degrees(math.atan2(v[ii[o]], -v[jj[o]])) % 360), 0)) for o in order]
    return dict(peaks=peaks, zero_shift_score=round(float(S[np.argmin(abs(v))][np.argmin(abs(v))]), 1))


def run_shift2d(res):
    out = {}
    for bid in FOOTPRINTS:
        out[bid] = shift_scan_2d(bid)
        print(bid, out[bid]['zero_shift_score'], [(p['dx'], p['dz'], p['score'], p['shift_m'], p['bearing_deg'])
                                                  for p in out[bid]['peaks']])
    res['shift2d'] = out


def west_facade_profiles(bid, min_len=8.0, min_cos=0.75, d0=-6.0, d1=26.0, step=0.5, trim=0.15, x_dir=(1.0, 0.0)):
    """NAIP 2024 leans roofs EAST in these frames (shift_scan_2d), so a WEST-facing wall is imaged as a band from its
    base (the SFO Museum outline, if a ground trace) to the imaged roof edge. Per west-facing edge: the median
    luminance profile along +x (east) from the edge line; returned as rounded values every 0.5 m for reading, plus
    the strongest |gradient| positions in d = 2..24 m. h = d_roof / k (k = lean per metre of height in that frame)."""
    from landside_common import sample
    from scipy.ndimage import gaussian_filter1d
    P = polys(FOOTPRINTS[bid])
    parts = list(P.geoms) if P.geom_type == 'MultiPolygon' else [P]
    w = np.array(x_dir)
    out = []
    for part in parts:
        ring = np.asarray(part.exterior.coords); ccw = part.exterior.is_ccw
        for i in range(len(ring) - 1):
            p0, p1 = ring[i], ring[i + 1]; t = p1 - p0; L = float(np.hypot(*t))
            if L < min_len:
                continue
            t /= L
            n = np.array([t[1], -t[0]]) if ccw else np.array([-t[1], t[0]])
            if float(n @ -w) < min_cos:
                continue
            s = np.arange(trim * L, (1 - trim) * L, 0.5)
            d = np.arange(d0, d1 + 1e-9, step)
            X = p0[0] + s[:, None] * t[0] + d[None, :] * w[0]
            Z = p0[1] + s[:, None] * t[1] + d[None, :] * w[1]
            bgr = sample(X, Z)
            lum = 0.114 * bgr[..., 0] + 0.587 * bgr[..., 1] + 0.299 * bgr[..., 2]
            prof = np.median(lum, 0)
            g = np.gradient(gaussian_filter1d(prof, 1.0), step)
            m = (d >= 2) & (d <= 24)
            idx = np.where(m)[0][np.argsort(-np.abs(g[m]))[:3]]
            out.append(dict(edge=i, p0=p0.round(1).tolist(), p1=p1.round(1).tolist(), length_m=round(L, 1),
                            mid=((p0 + p1) / 2).round(1).tolist(), d=d.tolist(),
                            prof=[int(round(v)) for v in prof],
                            strongest=[(float(d[j]), round(float(g[j]), 1)) for j in idx]))
    return out


DRUMS = {   # west helix drums of the International Garages: rows through the drum (z range) where the ribbed west
            # facade is imaged as a band between the outline (base) and the drum's top ring (QA: drums.jpg)
    'garage_a': (540.0, 562.0), 'garage_g': (350.0, 378.0),
}


def drum_heights():
    """Per row: x_base = west-most crossing of the SFO Museum outline (flysfo source, a ground trace); the drum top =
    the strongest dark->light rise of the luminance along +x in d = 8..16 m (facade band -> top ring). h = d / k(x) with
    the ITB pole model k(x) = 0.7553 + 0.0002753 x, calibrated at x = -1622..-1346 (the drums lie at x -1530 / -1585,
    inside that range; pole scatter 0.002)."""
    from shapely.geometry import LineString
    from scipy.ndimage import gaussian_filter1d
    from landside_common import sample
    out = {}
    for bid, (za, zb) in DRUMS.items():
        P = polys(FOOTPRINTS[bid]); ring = (max(P.geoms, key=lambda p: p.area) if P.geom_type != 'Polygon' else P).exterior
        x0 = P.bounds[0]
        rows = []
        for z in np.arange(za, zb + 1e-9, 0.5):
            I = LineString([(x0 - 5, z), (x0 + 40, z)]).intersection(ring)
            xs = sorted(p.x for p in getattr(I, 'geoms', [I])) if not I.is_empty else []
            if not xs:
                continue
            xb = xs[0]; d = np.arange(-2.0, 20.0, 0.25)
            b = sample((xb + d)[None, :], np.full((1, len(d)), z))[0]
            lum = gaussian_filter1d(0.114 * b[:, 0] + 0.587 * b[:, 1] + 0.299 * b[:, 2], 2.0)
            g = np.gradient(lum, 0.25); m = (d >= 8) & (d <= 16)
            j = np.where(m)[0][np.argmax(g[m])]
            k = 0.7553 + 0.0002753 * xb
            rows.append((float(z), round(float(xb), 2), float(d[j]), round(float(g[j]), 1), round(float(d[j] / k), 1)))
        hs = np.array([r[4] for r in rows])
        out[bid] = dict(rows=rows, h_median=round(float(np.median(hs)), 1), h_p25_p75=[round(float(v), 1) for v in np.percentile(hs, [25, 75])],
                        d_median=round(float(np.median([r[2] for r in rows])), 2),
                        k=round(0.7553 + 0.0002753 * float(np.median([r[1] for r in rows])), 3))
        print(bid, {k_: v for k_, v in out[bid].items() if k_ != 'rows'})
    return out


def hyatt_east_edge(z_rows=(640.0, 700.0)):
    """Grand Hyatt: the concave airside (east) facade. On each row z, x_e = the east-most crossing of the SFO Museum
    outline (the facade base IF the outline is a ground trace; its source is 'sfomuseum', possibly imagery-traced);
    the imaged roof edge = the strongest bright->dark fall of the luminance along +x in d = 4..20 m (white PV roof ->
    landscaping / road). h = d / k(x), k from the ITB pole model (x -1610..-1640, 10-30 m beyond its calibrated range)."""
    from shapely.geometry import LineString
    from scipy.ndimage import gaussian_filter1d
    from landside_common import sample
    P = polys(FOOTPRINTS['grand_hyatt']); ring = P.exterior
    rows = []
    for z in np.arange(z_rows[0], z_rows[1] + 1e-9, 1.0):
        I = LineString([(-1700, z), (-1580, z)]).intersection(ring)
        xs = sorted(p.x for p in getattr(I, 'geoms', [I])) if not I.is_empty else []
        if not xs:
            continue
        xe = xs[-1]; d = np.arange(-4.0, 24.0, 0.25)
        b = sample((xe + d)[None, :], np.full((1, len(d)), z))[0]
        lum = gaussian_filter1d(0.114 * b[:, 0] + 0.587 * b[:, 1] + 0.299 * b[:, 2], 2.0)
        g = np.gradient(lum, 0.25); m = (d >= 4) & (d <= 20)
        j = np.where(m)[0][np.argmin(g[m])]
        k = 0.7553 + 0.0002753 * xe
        rows.append((float(z), round(float(xe), 1), float(d[j]), round(float(g[j]), 1), round(float(d[j] / k), 1)))
    hs = np.array([r[4] for r in rows])
    out = dict(rows=rows, h_median=round(float(np.median(hs)), 1),
               h_p25_p75=[round(float(v), 1) for v in np.percentile(hs, [25, 75])])
    print('grand_hyatt east edge', {k_: v for k_, v in out.items() if k_ != 'rows'})
    return out


def superbay_rhythm(shift=(-7.0, -7.5), res=0.25):
    """Superbay roof (NAIP 2024, imaged (-7, -7.5) m from the SFO Museum outline: shift_scan_2d). Building frame:
    a = along the 117.8 deg long axis (WNW->ESE, the cantilever direction), b = along 27.8 deg (NNE, the spine and door
    direction), origin at the outline's minimum-rectangle centre. The luminance is sampled on the roof, a mean profile
    along b is taken for the WNW and ESE cantilever halves separately (|a| = 22..70 m, spine excluded), and the period
    of the bays is the strongest autocorrelation peak at lags 8..40 m. Also the bright spine's width (the |a| span
    where the mean along b exceeds the halves' 85th percentile)."""
    from landside_common import sample
    P = polys(FOOTPRINTS['superbay'])
    R = P.minimum_rotated_rectangle; c = R.centroid
    ea = np.array([math.sin(math.radians(117.83)), -math.cos(math.radians(117.83))])
    eb = np.array([math.sin(math.radians(27.83)), -math.cos(math.radians(27.83))])
    A = np.arange(-85, 85, res); B = np.arange(-70, 70, res)
    AA, BB = np.meshgrid(A, B)
    X = c.x + shift[0] + AA * ea[0] + BB * eb[0]; Z = c.y + shift[1] + AA * ea[1] + BB * eb[1]
    bgr = sample(X, Z); L = 0.114 * bgr[..., 0] + 0.587 * bgr[..., 1] + 0.299 * bgr[..., 2]
    out = {}
    colmean = L[(B > -55) & (B < 55)].mean(0)
    for side, sel in (('WNW', (A < -22) & (A > -70)), ('ESE', (A > 22) & (A < 70))):
        prof = L[:, sel].mean(1); m = (B > -60) & (B < 60)
        p = prof[m] - prof[m].mean()
        ac = np.correlate(p, p, 'full')[len(p) - 1:]; ac /= ac[0]
        lags = np.arange(len(ac)) * res; mm = (lags >= 8) & (lags <= 40)
        i = np.where(mm)[0][np.argmax(ac[mm])]
        # count the dark folds: local minima of the smoothed profile deeper than 5 levels below their neighbours
        from scipy.ndimage import gaussian_filter1d
        from scipy.signal import find_peaks
        sm = gaussian_filter1d(prof, 4)
        mins, _ = find_peaks(-sm, distance=int(8 / res), prominence=4)
        out[side] = dict(period_m=round(float(lags[i]), 2), ac=round(float(ac[i]), 2),
                         period_ft=round(float(lags[i]) / FT, 1),
                         folds_b=[round(float(B[j]), 1) for j in mins],
                         fold_spacing_median_m=round(float(np.median(np.diff(B[mins]))), 2) if len(mins) > 2 else None)
    thr = np.percentile(colmean[(np.abs(A) > 22) & (np.abs(A) < 70)], 85)
    sp = A[(np.abs(A) < 30) & (colmean > thr)]
    out['spine'] = dict(a_from=round(float(sp.min()), 1), a_to=round(float(sp.max()), 1),
                        width_m=round(float(sp.max() - sp.min()), 1)) if len(sp) else None
    # imaged roof extent along a (luminance > ground level) at mid-b
    print('superbay', out)
    return out


def run_shadow(res):
    """North-side shadows (shadow azimuth ~7 deg, cot e 0.313-0.33 for 12:40-13:40 PDT on 2024-05-20; the elevation can
    not exceed 72.59 deg that day) for the buildings whose north edges border open ground at grade. The imaged roof
    edge predicted from the 2-D lean (dx east) is d_pred = dx (east . n) / (u . n) along u; where it matches the
    measured d_roof the outline is a ground trace there and h = d_far / cot e."""
    out = {}
    for bid, dx in (('cac', 5.5), ('ltp_garage_1', 5.5), ('ltp_garage_2', 1.0)):
        P = polys(FOOTPRINTS[bid]); r = np.asarray(P.exterior.coords); ccw = P.exterior.is_ccw
        u = shadow_dir(SHADOW_AZ); rows = []
        for e in edge_shadow_profiles(bid, min_len=8, min_cos=0.55):
            i = e['edge']; t = (r[i + 1] - r[i]) / np.hypot(*(r[i + 1] - r[i]))
            n = np.array([t[1], -t[0]]) if ccw else np.array([-t[1], t[0]])
            pred = dx * n[0] / float(u @ n)
            rows.append(dict(e, d_roof_pred=round(pred, 2),
                             h_m=[round(e['d_far'] / 0.33, 1), round(e['d_far'] / 0.313, 1)]))
        out[bid] = rows
        print(bid, [(x['edge'], x['length_m'], x['d_far'], x['d_roof'], x['d_roof_pred'], x['h_m']) for x in rows])
    import datetime as dt
    out['sun_table'] = [(f'{h - 7:02d}:{m:02d} PDT',) + tuple(round(v, 2) for v in sun_pos(
        dt.datetime(2024, 5, 20, h, m, tzinfo=dt.timezone.utc))) for h, m in
        ((17, 0), (18, 0), (19, 0), (19, 30), (20, 0), (20, 6), (20, 15), (20, 30), (21, 0))]
    res['shadow'] = out


# ------------------------------------------------------------------------------------------- text re-reads
TEXT_CHECKS = [   # (claim id, source file stem in SRC, regex) - the line printed is the evidence quoted in the doc
    ('cg_height', 'verify_radp_deir', r'five-level, 81-foot-tall'),
    ('rcc_height', 'verify_radp_deir', r'66-foot-tall, 1,488,000'),
    ('cg_built', 'verify_radp_appx', r'Years constructed: 1963'),
    ('cg_built', 'verify_radp_appx', r'partially demolished and absorbed'),
    ('cg_built', 'verify_radp_appx', r'completion of the central parking garage in 1980'),
    ('build_years', 'verify_radp_appx', r'^(195|795|780|779|782|1060) +(RADP|N/A)'),
    ('build_years', 'verify_radp_appx', r'Dates listed under Build Year'),
    ('parking_2018', 'verify_radp_appx', r'South Garage [AG] '),
    ('cg_void', 'verify_db_1981', r'200 feet in diameter'),
    ('ga_levels', 'verify_tutor_itb', r'nine-level'),
    ('rcc_levels', 'verify_tutor_rcc', r'five-story'),
    ('rcc_levels', 'verify_conrac_sol', r'five levels of garage'),
    ('ltp2', 'verify_dlr_ltp2', r'six-level|level 5|Louvered towers'),
    ('ltp2', 'verify_enr_ltp2', r'12-ft floor height'),
    ('ltp2', 'verify_dbia_ltp2', r'seismically separated'),
    ('ltp2_built', 'verify_radp_deir', r'completed in 2020'),
    ('clearances', 'verify_flysfo_parking', r'Maximum height'),
    ('stations', 'verify_flysfo_around', r'Level [457]'),
    ('gh', 'verify_dbia_hyatt', r'12-story high rise'),
    ('gh', 'verify_webcor_hyatt', r'12 levels above grade|fourth-floor'),
    ('gh', 'verify_hyatt_pr_2019', r'4\.2-acres'),
    ('cac', 'verify_pw_cac', r'13 feet to 15 feet'),
    ('cac', 'verify_cavagnero_cac', r'four-story steel'),
    ('cac_phase2', 'verify_radp_deir', r'2019-006583ETM|Building 674\) was completed|anticipated to begin in 2025'),
    ('sb', 'verify_weitz_superbay_story', r'Originally built in 1969|four maintenance bays'),
    ('sb', 'verify_weitz_superbay', r'120 feet from the finished floor|420,550'),
    ('sb', 'verify_deep3ds_superbay', r'230 feet|50 foot wide structural bays|140-foot'),
    ('sb', 'verify_sfom_superbay_neg', r'June 12, 1970'),
    ('at', 'verify_flysfo_airtrain_fs', r'Vehicle Size|System Length|Number of Stations'),
    ('at', 'verify_flysfo_pr_2021', r'1,900 feet|over 6 miles'),
    ('at', 'verify_radp_appx', r'35 to 40 feet above ground'),
    ('at', 'verify_wiki_airtrain', r'February 24, 2003'),
]


def run_text(res):
    out = []
    for cid, stem, rx in TEXT_CHECKS:
        path = os.path.join(SRC, stem + '.txt')
        if not os.path.exists(path):
            out.append(dict(claim=cid, source=stem, found=None)); continue
        hits = [ln.strip()[:220] for ln in open(path, errors='replace') if re.search(rx, ln)]
        out.append(dict(claim=cid, source=stem, regex=rx, found=len(hits), lines=hits[:4]))
        print(cid, stem, len(hits), hits[:1])
    res['text'] = out


def qa_figures():
    """The two QA figures the Verification section cites (NAIP pixels; local only):
    drums.jpg - the west helix drums of Garages A / G with the outline shifted east by k*h for h = 0 / 25 / 30 / 36 m;
    sb_rect.jpg - the Superbay roof rectified to the building frame (up = 27.8 deg), ticks every 50 ft (red, left) and
    every 17.3 m (green, right)."""
    import cv2
    from landside_common import crop, sample
    tiles = []
    for bid, box in (('garage_a', (-1540, 525, -1495, 585)), ('garage_g', (-1592, 330, -1547, 390))):
        P = polys(FOOTPRINTS[bid]); x0, z0, x1, z1 = box
        img, f = crop(x0, z0, x1, z1, scale=8); img = np.ascontiguousarray(img)
        k = 0.7553 + 0.0002753 * (x0 + 15)
        parts = list(P.geoms) if P.geom_type == 'MultiPolygon' else [P]
        for h, col in ((0, (255, 255, 0)), (25, (0, 255, 0)), (30, (0, 200, 255)), (36, (0, 0, 255))):
            for part in parts:
                cv2.polylines(img, [np.array([f(x + k * h, z) for x, z in part.exterior.coords], np.int32)], True, col, 1)
        cv2.putText(img, f'{bid} k={k:.3f}: cyan 0, green 25, yellow 30, red 36 m', (6, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        tiles.append(img[:960, :720])
    cv2.imwrite(os.path.join(VOUT, 'drums.jpg'), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 85])
    P = polys(FOOTPRINTS['superbay']); c = P.minimum_rotated_rectangle.centroid
    ea = np.array([math.sin(math.radians(117.83)), -math.cos(math.radians(117.83))])
    eb = np.array([math.sin(math.radians(27.83)), -math.cos(math.radians(27.83))])
    res = 0.4; A = np.arange(-95, 95, res); B = np.arange(-80, 80, res); AA, BB = np.meshgrid(A, B)
    img = np.clip(sample(c.x - 7 + AA * ea[0] + BB * eb[0], c.y - 7.5 + AA * ea[1] + BB * eb[1]), 0, 255)
    img = np.ascontiguousarray(img.astype(np.uint8)[::-1])
    for bb in np.arange(-75, 76, 15.24):
        r = int((80 - bb) / res); cv2.line(img, (0, r), (12, r), (0, 0, 255), 1)
    for bb in np.arange(-69.2, 70, 17.3):
        r = int((80 - bb) / res); cv2.line(img, (img.shape[1] - 12, r), (img.shape[1] - 1, r), (0, 255, 0), 1)
    cv2.imwrite(os.path.join(VOUT, 'sb_rect.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    res = load()
    steps = dict(dof=run_dof, fp=run_fp, shift2d=run_shift2d, shadow=run_shadow, text=run_text,
                 drums=lambda r: r.__setitem__('drums', drum_heights()),
                 superbay=lambda r: r.__setitem__('superbay_rhythm', superbay_rhythm()))
    for k, fn in steps.items():
        if what in (k, 'all'):
            fn(res)
    if what in ('qa', 'all'):
        for bid in FOOTPRINTS:
            shadow_qa(bid)
        qa_figures()
    save(res)
    if what in ('apply', 'all'):
        import landside_verify_apply
        landside_verify_apply.apply()
