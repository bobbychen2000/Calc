"""Domestic terminals - adversarial fact-check of the research spec (docs/research/buildings_domestic.md, section
"Verification"; tools/buildings/spec_domestic.json).

What it re-does, independently of the research run where possible (NAIP 2020 / 2022 / 2024 world-grid rasters made by
dom_naip_epochs.py; FAA DOF re-fetched; SFO Museum footprints read only):
  1. reproduce   - re-runs dom_heights.measure() on the re-fetched rasters (must equal tools/buildings/dom_heights.json)
  2. sun 2020    - the ATCT shadow axis on NAIP 2020 by a sub-pixel centre-line fit of the shaft/flare shadow (instead
                   of the research's axis-to-blob direction), then the sun-path elevation for that azimuth (dom_sun.py):
                   the |s20| the sun path implies, against the calibrated 1.19
  3. parallax    - local 1-D NCC shifts 2020->2024 and 2022->2024 in 6 m windows across the whole roof width of BA-B and
                   BA-E (the research used one shift per roof). Different shift populations = different roof heights:
                   h_a / h_b = p_a / p_b, independent of the sun and of the leans.
  4. BA-B        - the stepped section that (3) reveals, solved with the research's own band20 / band24 and the
                   shadow cast by the raised central roof on the lower ESE band in 2020
  5. DOF         - every FAA DOF BLDG point the research cites, tested against the SFO Museum outlines (1A = +-20 ft
                   horizontal, so a point > 6 m outside an outline is not on that building)
  6. scale       - all two-epoch heights recomputed with |s20| from the sun path at the re-measured tower azimuth

Outputs: tools/buildings/dom_verify.json (numbers only, committable); out/buildings/domestic/verify/*.jpg (crops with
NAIP pixels: local only). `apply_spec()` writes the verification records into spec_domestic.json (idempotent; also
called by build_spec_domestic.py after it regenerates the spec).

usage: python3 tools/buildings/dom_verify.py [--apply]
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, 'dom_verify.json')
SPEC = os.path.join(HERE, 'spec_domestic.json')
RES = 0.1


# ------------------------------------------------------------------------------------------------------ helpers
def _st2w(s, t):
    import geo_frame as GF
    return (s * GF.V[0] + t * GF.U[0], -(s * GF.V[1] + t * GF.U[1]))


def lshift(u, a, b, c0, half=3.0, maxs=6.0):
    """shift d (m) maximising the NCC of profile a(u) against b(u + d) in the window [c0 - half, c0 + half]."""
    m = (u >= c0 - half) & (u <= c0 + half); idx = np.where(m)[0]; best = None
    for d in np.arange(-maxs, maxs + 1e-6, 0.05):
        j = idx + int(round(d / RES))
        if j.min() < 0 or j.max() >= len(u): continue
        x = a[idx] - a[idx].mean(); y = b[j] - b[j].mean()
        r = float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum() + 1e-9))
        if best is None or r > best[1]: best = (round(float(d), 2), round(r, 3))
    return best


def st_profiles(s0, s1, t0, t1, years=(2020, 2022, 2024)):
    """median s-profiles (rows along t) of each epoch, Gaussian sigma 0.15 m."""
    import cv2, dom_common as C
    P = {}
    for yr in years:
        img, o = C.crop_st(yr, s0, s1, t0, t1, res=RES)
        G = cv2.GaussianBlur(C.gray(img), (0, 0), 1.5)
        P[yr] = np.median(G, axis=0)
    s = s0 + (np.arange(len(P[years[0]])) + 0.5) * RES
    return s, P


# ------------------------------------------------------------------------------------------------- 2. the sun 2020
def tower_shadow_axis(xa=-689, xb=-657):
    """centre line of the ATCT shaft / flare shadow on NAIP 2020 (x xa..xb, where it lies on flat apron)."""
    import cv2, dom_common as C
    img, (x0, z0, res) = C.crop(2020, -700, -640, 300, 340, res=0.05)
    G = cv2.GaussianBlur(C.gray(img), (0, 0), 4.0)
    zs = z0 + (np.arange(G.shape[0]) + 0.5) * res
    rows = []
    for xc in np.arange(xa, xb, 1.0):
        col = G[:, int((xc - x0) / res)]; k = int((319 - z0) / res)
        lo = np.median(col[k - 40:k + 40]); mt = 0.5 * (lo + np.median(col[:60])); mb = 0.5 * (lo + np.median(col[-60:]))
        i = k
        while i > 0 and col[i] < mt: i -= 1
        zt = zs[i] + (mt - col[i]) / (col[i + 1] - col[i]) * res
        i = k
        while i < len(col) - 1 and col[i] < mb: i += 1
        zb = zs[i - 1] + (mb - col[i - 1]) / (col[i] - col[i - 1]) * res
        rows.append((xc, zt, zb))
    R = np.array(rows); xc = R[:, 0]; ctr = 0.5 * (R[:, 1] + R[:, 2])
    A = np.vstack([xc, np.ones(len(xc))]).T
    c, *_ = np.linalg.lstsq(A, ctr, rcond=None); res_ = ctr - A @ c
    se = math.sqrt((res_ ** 2).sum() / (len(xc) - 2) / ((xc - xc.mean()) ** 2).sum())
    ct, *_ = np.linalg.lstsq(A, R[:, 1], rcond=None); cb, *_ = np.linalg.lstsq(A, R[:, 2], rcond=None)
    hdg = math.degrees(math.atan2(1.0, -c[0])) % 360
    return dict(method='sub-pixel 50 %% crossings of both shadow edges every 1 m over x %d..%d (0.05 m/px crop, '
                       'sigma 0.2 m); centre line fitted by least squares' % (xa, xb - 1),
                heading_deg=round(hdg, 2), se_deg=round(math.degrees(se), 2),
                edge_slopes=dict(top=round(float(ct[0]), 3), bottom=round(float(cb[0]), 3)),
                note='the two edges diverge unequally (the shaft / flare is not a circular cylinder), so the centre line '
                     'carries a systematic error of the order of 1 deg beyond the statistical one')


def sun_from_azimuth(shadow_az):
    import dom_sun
    d, dt, az, el = dom_sun.el_at_az((2020, 5, 24), (shadow_az + 180) % 360)
    return dict(shadow_az_deg=shadow_az, sun_el_deg=round(el, 2), utc=dt.strftime('%H:%M'),
                s20_abs=round(1 / math.tan(math.radians(el)), 3))


# ------------------------------------------------------------------------------------- 3./4. parallax and BA-B
def ba_b():
    """BA-B south half, t -1236..-1180 (the research's faces): local parallax across the width + the stepped section."""
    import dom_profile as P, dom_heights as H
    s, Pr = st_profiles(-460, -360, -1236, -1180)
    win = []
    for c0 in np.arange(-432, -388, 2.0):
        a = lshift(s, Pr[2020], Pr[2024], c0); b = lshift(s, Pr[2022], Pr[2024], c0)
        win.append(dict(s2020=float(c0), p_20_24=a[0], r=a[1], p_22_24=b[0], r22=b[1]))
    lowW = [w['p_20_24'] for w in win if -433 <= w['s2020'] <= -425 and w['r'] > 0.95]
    cen = [w['p_20_24'] for w in win if -417 <= w['s2020'] <= -391 and w['r'] > 0.95]
    # ESE outer lip: steepest descent per 1 m row strip, 2020 vs 2024
    import cv2, dom_common as C
    img20, o = C.crop_st(2020, -400, -370, -1236, -1180, res=RES); img24, _ = C.crop_st(2024, -400, -370, -1236, -1180, res=RES)
    G20 = cv2.GaussianBlur(C.gray(img20), (0, 0), 1.5); G24 = cv2.GaussianBlur(C.gray(img24), (0, 0), 1.5)
    ss = o[0] + (np.arange(G20.shape[1]) + 0.5) * RES
    def edge(row, lo, hi):
        m = (ss >= lo) & (ss <= hi); d = np.gradient(row); return ss[np.where(m)[0][np.argmin(d[m])]]
    e20 = np.median([edge(G20[i], -386, -378) for i in range(0, G20.shape[0], 10)])
    e24 = np.median([edge(G24[i], -384, -374) for i in range(0, G24.shape[0], 10)])
    # 2020: raised central roof edge (bright -> dark, +s) and the end of its shadow on the lower ESE band (dark -> bright)
    p20 = np.median(G20, axis=0)
    m_edge = P.step(ss, p20, -390.5, -386.5, -1); sh_end = P.step(ss, p20, -385.0, -382.6, +1)
    step20 = sh_end['pos'] - m_edge['pos']
    HR = {r['id']: r for r in json.load(open(os.path.join(HERE, 'dom_heights.json')))['roofs']}['ba_b_south']
    pO_w = float(np.median(lowW)); pO_e = float(e24 - e20); pO = 0.5 * (pO_w + pO_e); pM = float(np.median(cen))
    return dict(windows=win, p_low_wnw_band=round(pO_w, 2), p_low_ese_lip=round(pO_e, 2), p_low=round(pO, 2),
                p_central=round(pM, 2), ratio_low_central=round(pO / pM, 3),
                ese_lip_2020=round(float(e20), 2), ese_lip_2024=round(float(e24), 2),
                central_edge_2020=m_edge, central_shadow_end_on_low_roof_2020=sh_end, step_shadow_2020=round(step20, 2),
                band20=HR['band20'], band24=HR['band24'], p_research=HR['p'], h_research=HR['h_m'])


def solve_b(B, s20_az, s20_abs):
    import dom_heights as H
    n = H.nvec(117.83); s20 = H.svec(s20_az, s20_abs); s24 = H.svec(H.S24_AZ_SHADOW, H.S24_ABS)
    den = float(np.dot(s20 - s24, n))
    hO = (B['band20'] + B['band24'] - B['p_low']) / den
    k20n = float(np.dot(s20, n)) - B['band20'] / hO
    k24n = B['band24'] / hO + float(np.dot(s24, n))
    hM_par = hO * B['p_central'] / B['p_low']
    hM_sh = hO + B['step_shadow_2020'] / (float(np.dot(s20, n)) - k20n)
    return dict(den=round(den, 3), h_low=round(hO, 2), h_central_parallax=round(hM_par, 2),
                h_central_step_shadow=round(hM_sh, 2), h_central=round(0.5 * (hM_par + hM_sh), 2),
                k20_n=round(k20n, 3), k24_n=round(k24n, 3))


def ba_e():
    s, Pr = st_profiles(-745, -670, -350, -310)
    win = []
    for c0 in np.arange(-730, -688, 2.0):
        a = lshift(s, Pr[2020], Pr[2024], c0)
        win.append(dict(s2020=float(c0), p_20_24=a[0], r=a[1]))
    roof = [w['p_20_24'] for w in win if -718 <= w['s2020'] <= -694 and w['r'] > 0.95]
    return dict(windows=win, p_roof_median=round(float(np.median(roof)), 2), p_roof_n=len(roof),
                p_roof_range=[float(min(roof)), float(max(roof))])


# --------------------------------------------------------------------------------------------------- 5. DOF
def dof_points():
    import dom_common as C
    from shapely.geometry import Point, Polygon
    fp = C.footprints(); polys = {k: [Polygon(r) for r in v] for k, v in fp.items()}
    want = ['06-035320', '06-035321', '06-035322', '06-035323', '06-035330', '06-035331', '06-035332', '06-035351', '06-039216']
    out = {}
    for r in C.load_dof(lambda r: r['oas'] in want):
        p = Point(r['x'], r['z'])
        d, name = min((pp.distance(p), k) for k, v in polys.items() for pp in v)
        out[r['oas']] = dict(type=r['type'], agl_ft=r['agl_ft'], acc=r['acc'], jdate=r['jdate'], x=r['x'], z=r['z'],
                             nearest_outline=name, distance_outside_m=round(d, 1),
                             inside=[k for k, v in polys.items() if any(pp.contains(p) for pp in v)])
    return out


# ----------------------------------------------------------------------------------------------------- main
def main():
    import dom_heights as H
    ref = json.load(open(os.path.join(HERE, 'dom_heights.json')))
    rep = [H.measure(R) for R in H.ROOFS]
    reproduce = {r['id']: dict(h_m=r['h_m'], spec=[x for x in ref['roofs'] if x['id'] == r['id']][0]['h_m']) for r in rep}
    tw = tower_shadow_axis()
    tw['alt_range_-693'] = tower_shadow_axis(-693, -657)['heading_deg']
    sun_research = sun_from_azimuth(H.S20_AZ_SHADOW)
    sun_new = sun_from_azimuth(tw['heading_deg'])
    sun_alt = sun_from_azimuth(tw['alt_range_-693'])
    OPT = dict(calibrated=(H.S20_AZ_SHADOW, H.S20_ABS), central=(88.0, 1.25), sunpath=(tw['heading_deg'], sun_new['s20_abs']))
    sun_cal = dict(s20_abs=H.S20_ABS, note='calibrated in the research (DOF 06-035331 + BA-A pole lean); on the sun path '
                   'it needs a shadow azimuth of ~86.7 deg (el 40.0)')
    # all two-epoch heights at the alternative sun vector (tower azimuth + sun path)
    n_e = H.nvec(117.83); s24 = H.svec(H.S24_AZ_SHADOW, H.S24_ABS)
    alt = {}
    for r in ref['roofs']:
        if 'band24' not in r:          # single face (BA-C): h = (band20 - p) / ((s20 - k24) . n), k24 assumed
            n = H.nvec(r['n_hdg']); k24 = np.array([r['k24_assumed'], 0.0])
            alt[r['id']] = {k: round((r['band20'] - r['p']) / float(np.dot(H.svec(az, a) - k24, n)), 2) for k, (az, a) in OPT.items()}
            continue
        n = n_e if r['id'] == 'ba_e_north' else H.nvec(r['n_hdg'])
        alt[r['id']] = {k: round((r['band20'] + r['band24'] - r['p']) / float(np.dot(H.svec(az, a) - s24, n)), 2)
                        for k, (az, a) in OPT.items()}
    B = ba_b()
    Bs = {k: solve_b(B, az, a) for k, (az, a) in OPT.items()}
    res = dict(generated_by='tools/buildings/dom_verify.py', date='2026-11-04',
               reproduce=reproduce, tower_shadow_2020=tw, sun_2020=dict(research_azimuth=sun_research, remeasured_azimuth=sun_new,
                                                                       remeasured_azimuth_alt_range=sun_alt, calibrated=sun_cal,
                                                                       options={k: dict(shadow_az=v[0], s20_abs=v[1]) for k, v in OPT.items()}),
               heights_at_sunpath_s20=alt, ba_b=B, ba_b_section=Bs, ba_e=ba_e(), dof=dof_points())
    json.dump(res, open(OUT_JSON, 'w'), indent=1)
    print('reproduce', {k: (v['h_m'], v['spec']) for k, v in reproduce.items()})
    print('tower shadow', tw['heading_deg'], '+-', tw['se_deg'], '(alt range', tw['alt_range_-693'], ') | sun path |s20| at research az',
          sun_research['s20_abs'], 'at re-measured az', sun_new['s20_abs'], sun_alt['s20_abs'])
    print('heights at the sun-path s20', alt)
    print('BA-B p low (WNW band, ESE lip) %.2f, %.2f; central %.2f; step shadow %.2f' % (B['p_low_wnw_band'], B['p_low_ese_lip'], B['p_central'], B['step_shadow_2020']))
    print('BA-B section', Bs)
    print('BA-E roof parallax', res['ba_e']['p_roof_median'], res['ba_e']['p_roof_range'])
    for k, v in res['dof'].items(): print(k, v['agl_ft'], v['nearest_outline'], v['distance_outside_m'], v['inside'])
    qa(B)


def qa(B):
    """local QA crop: BA-B ESE edge zone 2020 over 2024 with the solved lines (NAIP pixels: out/ only)."""
    import cv2, dom_common as C
    tiles = []
    for yr in (2020, 2024):
        img, org = C.crop_st(yr, -445, -370, -1215, -1195, res=RES)
        im = img.copy()
        for sv in range(-445, -369):
            x = int((sv + 445) / RES); col = (0, 0, 255) if sv % 5 == 0 else (0, 200, 255)
            cv2.line(im, (x, 0), (x, 8 if sv % 5 else 20), col, 1)
            if sv % 5 == 0: cv2.putText(im, 's%d' % sv, (x + 2, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        cv2.putText(im, 'NAIP %d  BA-B south, airport grid s (ESE right), t -1215..-1195' % yr, (5, im.shape[0] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        tiles.append(im)
    os.makedirs(os.path.join(C.QA_DIR, 'verify'), exist_ok=True)
    C.save_qa('verify/bab_section_2020_2024.jpg', np.vstack(tiles))


# ------------------------------------------------------------------------------------------- spec corrections
def apply_spec(path=SPEC):
    """write verification / correction records into spec_domestic.json (idempotent)."""
    import dom_verify_spec as VS
    VS.apply(path, json.load(open(OUT_JSON)))


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    if '--apply' in sys.argv:
        apply_spec()
    else:
        main()
