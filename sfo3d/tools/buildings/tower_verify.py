"""SFO ATCT - adversarial fact-check of the tower research (docs/research/buildings_tower.md s.12 'Verification').

Independent re-measurements, deliberately using methods that differ from the ones in tower_roof_disc.py,
tower_lean_ratio.py and tower_photo_profile.py:

 A. OE/AAA sibling cases 2008-AWP-285/286/287-NRA (re-fetched 2026-09-26, cached as
    refs/cache/buildings/tower/src/verify_oe_case_*.json): proposal sites 13A / 13 / 6B -> world frame.
 B. Photo absolute scale from camera EXIF (focal length / 35-mm equivalent) + camera GPS, instead of the
    '11-ft cab glass panel' scale. EXIF + GPS come from the Wikimedia Commons API (imageinfo metadata, re-fetched
    2026-09-26, cached as refs/cache/buildings/tower/src/commons_exif_verify.json). Two Famartin iPhone photos look at
    the cab from nearly opposite sides (bearings 126 and 319 deg), so the cab diameter implied by each depends on the
    unknown cab x in opposite senses -> a joint (x, D) solve.
 C. Scale-free vertical span 'cab-roof rim -> base-building (IBF) airside parapet' in units of the cab-roof diameter,
    with full pinhole perspective (Famartin 11:57) and near-orthographic (Soufi A380 photo, 1.5-1.75 km).
    Combined with the NAIP height ratio h_IBF / H_rim (~0.20-0.21, tower_lean_ratio.py and the SE-edge offsets in
    buildings_tower.md s.4.2) this gives H_rim for an assumed D, i.e. a consistency test of
    {H_rim = 221 ft, D_cab = 14.3 m, h_IBF = 14.2 m}.
 D. NAIP cab-roof disc: median radial brightness profiles (crescent sector and the opposite sector) around the
    published per-epoch disc centres - where does the bright disc end?
 E. Reproduction of the s.3 x-bound from the SE-wall offsets quoted in s.4.2.

Pixel readings marked 'manual' were read on zoomed crops of the reference photos (refs/cache/buildings/tower/photos,
gitignored, CC BY-SA 4.0: Famartin; Basil D Soufi). Photos are reference only; only numbers leave this script.

Output: out/buildings/tower/verify/verify.json (+ printed tables). No network needed (uses the caches).
usage : python3 tools/buildings/tower_verify.py
"""
import json, math, os, sys
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

SRC = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'tower', 'src')
PH = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'tower', 'photos')
TOW = os.path.join(ROOT, 'out', 'buildings', 'tower')
OUT = os.path.join(TOW, 'verify')
FT = 0.3048
DIAG35 = 43.267                    # mm, diagonal of the 36 x 24 mm frame (EXIF FocalLengthIn35mmFilm is diagonal-based)
CAB_Z = 323.5                      # spec position_cab_roof_centre z (confirmed below, D)
R_ROOF_NEAR = 7.15                 # near-side rim offset from the cab axis (spec d_cab_roof / 2)
RES = {}


def frac(s):
    a, b = str(s).split('/') if '/' in str(s) else (s, 1)
    return float(a) / float(b)


# ------------------------------------------------------------------------------------------------ A. OE/AAA sites
def oe_sites():
    rows = {}
    for seq in (285, 286, 287):
        d = json.load(open(os.path.join(SRC, f'verify_oe_case_2008AWP{seq}NRA.json')))
        p = d['pointConverted']
        x, z = GF.ll_to_world(p['latitude'], p['longitude'])          # letter: NAD83
        rows[d['asn']] = dict(agl_ft=d['heightAglFoot'], amsl_ft=d['structureHeightAmslFoot'],
                              elev_ft=d['elevationFoot'], desc=d['proposalDescription'],
                              world_nad83=[round(x, 2), round(z, 2)])
    print('A. OE/AAA sites (world, NAD83):')
    for k, v in rows.items(): print('  ', k, v['world_nad83'], v['agl_ft'], 'ft AGL', '|', v['desc'][60:140])
    RES['A_oe_sites'] = rows


# ------------------------------------------------------------------------------------------------ B/C. photos
def silhouette_width(img, x0, x1, xmid, rows, blur=1.5):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), blur)
    gx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3))
    best = (0, None)
    for y in rows:
        L = x0 + int(np.argmax(gx[y, x0:xmid])); R = xmid + int(np.argmax(gx[y, xmid:x1]))
        if R - L > best[0]: best = (R - L, (y, L, R))
    return best


PHOTOS = {
    # local file (Commons thumbnail) + its full-res width, silhouette search windows (local px) and manual rows
    'fam1157': dict(title='File:2025-08-12 11 57 15 The control tower at San Francisco International Airport in San '
                          'Mateo County, California.jpg',
                    file='2025-08-12_11_57_15_The_control_tower_at_San_Francisco_International_Airport_in_San_Mateo_.jpg',
                    rim=(660, 1200, 930, range(330, 372, 2)), flare=(500, 1350, 930, range(560, 640, 4)),
                    rim_near_y=290,            # manual: top of the fascia at the tower's centre column (near side)
                    parapet_y=2007,            # manual: IBF airside parapet top where it occludes the shaft
                    hc=4.5),                   # camera height above grade (aircraft cabin window at gate C11; +-1.5)
    'fam0912': dict(title='File:2025-08-12 09 12 13 The control tower at San Francisco International Airport in San '
                          'Mateo County, California.jpg',
                    file='2025-08-12_09_12_13_The_control_tower_at_San_Francisco_International_Airport_in_San_Mateo_.jpg',
                    rim=None, rim_manual=(2028, 2779),   # manual: limb extremes (rim is rolled in this frame)
                    hc=10.0),                  # AirTrain platform level (GPS alt 14 m MSL; +-5)
    'a380': dict(title='File:SFO - New Control Tower & A380.jpg', file='SFO_-_New_Control_Tower_A380.jpg',
                 rim=(1840, 2330, 2085, range(330, 372, 2)), rim_near_y=318,
                 lowest_shaft_y=1730),        # manual: lowest visible shaft (occluded by a dark foreground roof)
}


def photos():
    meta = json.load(open(os.path.join(SRC, 'commons_exif_verify.json')))
    out = {}
    for key, P in PHOTOS.items():
        m = meta[P['title']]; ex = m['exif']
        img = cv2.imread(os.path.join(PH, P['file'])); h_loc, w_loc = img.shape[:2]
        full_w = m['w'] if m['w'] > m['h'] else m['h']; long_loc = max(w_loc, h_loc)
        s = full_w / long_loc                                       # full-res px per local px
        if ex.get('FocalLengthIn35mmFilm'):
            diag_full = math.hypot(m['w'], m['h'])
            pa_full = DIAG35 / ex['FocalLengthIn35mmFilm'] / diag_full   # rad per full-res px
        else:                                                       # Canon 6D: pixel pitch from FocalPlaneXResolution
            pitch_cm = 1 / frac(ex['FocalPlaneXResolution']); pa_full = pitch_cm * 10 / frac(ex['FocalLength'])
        pa = pa_full * s                                            # rad per local px
        rec = dict(model=ex.get('Model'), f_mm=round(frac(ex['FocalLength']), 2), f35=ex.get('FocalLengthIn35mmFilm'),
                   rad_per_local_px=pa, gps=[ex.get('GPSLatitude'), ex.get('GPSLongitude')])
        if P.get('rim'):
            w, (y, L, R) = silhouette_width(img, *P['rim']); rec['rim_px'] = w; rec['rim_row'] = y
        else:
            rec['rim_px'] = P['rim_manual'][1] - P['rim_manual'][0]
        if P.get('flare'):
            w, (y, L, R) = silhouette_width(img, *P['flare']); rec['flare_px'] = w; rec['flare_row'] = y
            rec['flare_over_rim'] = round(rec['flare_px'] / rec['rim_px'], 3)
        if ex.get('GPSLatitude'):
            rec['cam_world'] = [round(v, 1) for v in GF.wgs84_to_world(ex['GPSLatitude'], ex['GPSLongitude'])]
        out[key] = rec
    # --- B. EXIF + GPS diameters as a function of the (uncertain) cab x; joint solve of the two opposite cameras
    def d_cab(key, x, H=67.36):
        r = out[key]; cx, cz = r['cam_world']; d = math.hypot(cx - x, cz - CAB_Z)
        R = math.hypot(d, H - PHOTOS[key]['hc'])
        return r['rim_px'] * r['rad_per_local_px'] * R
    xs = np.arange(-760, -729.9, 1.0)
    f = np.array([d_cab('fam1157', x) - d_cab('fam0912', x) for x in xs])
    i = int(np.argmin(np.abs(f))); xj = float(xs[i])
    B = dict(D_exif_gps_at_x739={k: round(d_cab(k, -739.0), 2) for k in ('fam1157', 'fam0912')},
             D_exif_gps_at_x751={k: round(d_cab(k, -751.0), 2) for k in ('fam1157', 'fam0912')},
             # the two cameras face each other, so the MEAN diameter is almost independent of the unknown cab x
             D_mean_opposite_cameras={str(x): round(0.5 * (d_cab('fam1157', x) + d_cab('fam0912', x)), 2)
                                      for x in (-744.0, -739.0, -734.0)},
             joint_solution=dict(x_cab=xj, D=round(0.5 * (d_cab('fam1157', xj) + d_cab('fam0912', xj)), 2),
                                 note='equal-D solve of two opposite iPhone cameras; GPS +-10 m (iPhone altitudes of '
                                      'the 09:10-09:12 series scatter 14-45 m) -> x +-10 m, D +-0.5 m'))
    # A380: implied camera distance for D = 14.3 vs the Commons {{Location}} template point (not EXIF)
    a = out['a380']; B['a380_distance_for_D14.3_m'] = round(14.3 / (a['rim_px'] * a['rad_per_local_px']), 0)
    B['a380_commons_location_distance_m'] = 1751
    # --- C. scale-free span rim -> IBF parapet (Famartin, perspective) and rim -> lowest shaft (A380, orthographic)
    r = out['fam1157']; P = PHOTOS['fam1157']; cam = np.array(r['cam_world'])
    fpx = 1 / r['rad_per_local_px']; cy = 2560 / 2
    A_, B_ = np.array([-739.3, 357.9]), np.array([-718.5, 318.1])       # SFO Museum SE (airside) edge
    def span_for(H, x=-739.0):
        C = np.array([x, CAB_Z]); M = np.array([C - cam, A_ - B_]).T; t, _ = np.linalg.solve(M, A_ - cam)
        dp = np.linalg.norm(t * (C - cam)); dC = np.linalg.norm(C - cam)
        th_rim = math.atan((H - P['hc']) / (dC - R_ROOF_NEAR)); pitch = th_rim - math.atan((cy - P['rim_near_y']) / fpx)
        th_p = pitch + math.atan((cy - P['parapet_y']) / fpx)
        hp = P['hc'] + dp * math.tan(th_p)
        Dloc = r['rim_px'] * r['rad_per_local_px'] * math.hypot(dC, H - P['hc'])
        return hp, (H - hp) / Dloc, Dloc
    hp, SD, Dl = span_for(67.36)
    C_ = dict(fam1157=dict(parapet_if_rim_67_36=round(hp, 2), span_over_D=round(SD, 3), D_this_photo=round(Dl, 2)),
              a380=dict(span_over_D=round((PHOTOS['a380']['lowest_shaft_y'] - PHOTOS['a380']['rim_near_y'])
                                          / out['a380']['rim_px'], 3),
                        note='lowest visible shaft; occluder is a foreground roof, not certainly the IBF parapet'))
    # H_rim implied by the NAIP ratio rho (IBF roof / cab roof) and a parapet height dp above the roof
    tab = []
    for D in (14.3, 14.7, 15.0, 15.3):
        for rho in (0.20, 0.21, 0.25):
            H = (SD * D + 0.7) / (1 - rho)
            tab.append(dict(D=D, rho=rho, H_rim=round(H, 1), H_ft=round(H / FT), ibf_roof=round(rho * H, 1)))
    C_['H_rim_table'] = tab
    C_['D_needed_for_H_67_36_rho_0_205'] = round(((1 - 0.205) * 67.36 - 0.7) / SD, 2)
    RES['B_photos'] = out; RES['B_exif_scale'] = B; RES['C_span'] = C_
    print('B. photos:', json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'rad_per_local_px'} for k, v in out.items()}))
    print('   EXIF+GPS diameters:', json.dumps(B))
    print('C. span rim->IBF parapet:', json.dumps({k: v for k, v in C_.items() if k != 'H_rim_table'}))
    for row in tab: print('   ', row)


# ------------------------------------------------------------------------------------------------ D. NAIP disc
def naip_disc():
    X0, Z0, R = -800.0, 250.0, 0.1
    fits = json.load(open(os.path.join(TOW, 'roof_disc_fits.json')))['fits']
    sectors = {'2016': (225, 295), '2018': (290, 355), '2022': (215, 295), '2024': (150, 240)}   # dark crescent
    rr = np.arange(3.0, 10.01, 0.25); out = {}
    for y, (a0, a1) in sectors.items():
        g = cv2.cvtColor(cv2.imread(os.path.join(TOW, f'naip_{y}_tower.png')), cv2.COLOR_BGR2GRAY).astype(np.float32)
        cx, cz = fits[y]['cx'], fits[y]['cz']
        def prof(b0, b1):
            acc = []
            for a in np.arange(b0, b1, 1.0):
                t = math.radians(a)
                px = ((cx + rr * math.cos(t)) - X0) / R - 0.5; pz = ((cz + rr * math.sin(t)) - Z0) / R - 0.5
                acc.append(cv2.remap(g, px.astype(np.float32)[None], pz.astype(np.float32)[None], cv2.INTER_LINEAR)[0])
            return np.median(np.array(acc), 0)
        pc, po = prof(a0, a1), prof(a0 + 180, a1 + 180)
        inside = float(np.median(pc[(rr >= 4.5) & (rr <= 5.5)])); j = int(np.argmin(pc[rr >= 6])); vmin = float(pc[rr >= 6][j])
        half = 0.5 * (inside + vmin); k = np.where((rr >= 5.0) & (pc <= half))[0]
        jo = int(np.argmin(po[(rr >= 5.5) & (rr <= 8.5)]))
        out[y] = dict(crescent_r50=float(rr[k[0]]) if len(k) else None, crescent_rmin=float(rr[rr >= 6][j]),
                      opposite_ring_rmin=float(rr[(rr >= 5.5) & (rr <= 8.5)][jo]))
    RES['D_naip_disc'] = out
    print('D. NAIP disc radii (m):', json.dumps(out))


# ------------------------------------------------------------------------------------------------ E. x from SE wall
def x_from_wall():
    # s.4.2 of the research: SE-edge offset of the imaged IBF roof vs the SFO Museum edge (outward normal), cab disc x
    off = {'2016': -0.5, '2018': 1.5, '2022': 10.5, '2024': 9.0}
    cabx = {'2016': -752.75, '2018': -749.70, '2022': -698.75, '2024': -700.85}
    nx = 0.886                                                   # x-component of the SE edge's outward normal
    out = {}
    for rho in (0.20, 0.21):
        out[f'rho_{rho}'] = {y: round(cabx[y] - off[y] / nx / rho, 1) for y in off}
    RES['E_x_from_SE_wall'] = dict(x0_if_outline_is_true_wall=out,
                                   note='x0 = x_cab - (edge offset / 0.886) / rho; an outline error c shifts every x0 '
                                        'by c / (0.886 rho) = 5.4 c')
    print('E. x0 from the SE-wall method (outline taken as exact):', json.dumps(out))


def sensor_bound():
    """F. NAIP 2022 FGDC (refs/cache/buildings/tower/src/verify_naip_fgdc_2022.txt): Leica ContentMapper frame sensor,
    across-track field of view 67.1 deg, 4470 m AGL, 20 % lateral overlap. The relief lean per metre of height can
    therefore not exceed tan(33.55 deg) * Hf / (Hf - h) at the swath edge, which bounds the tower axis from the west:
    x0 >= x_cab_2022 - kmax * H_rim. (2016/2018: ADS100 pushbroom, nadir look angle -> no along-track (N-S) lean.)"""
    Hf = 4470.0; x22 = -698.75
    out = {}
    for H in (63.3, 65.0, 67.36):
        kmax = math.tan(math.radians(67.1 / 2)) * Hf / (Hf - H)
        kmid = 0.9 * kmax                              # seamline in the middle of the 20 % side overlap
        out[str(H)] = dict(kmax=round(kmax, 3), x0_min_hard=round(x22 - kmax * H, 1),
                           x0_min_if_seam_mid_overlap=round(x22 - kmid * H, 1))
    RES['F_sensor_bound'] = out
    print('F. 2022 ContentMapper FOV bound on the axis x:', json.dumps(out))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    oe_sites(); photos(); naip_disc(); x_from_wall(); sensor_bound()
    json.dump(RES, open(os.path.join(OUT, 'verify.json'), 'w'), indent=1, default=float)
    print('->', os.path.relpath(os.path.join(OUT, 'verify.json'), ROOT))
