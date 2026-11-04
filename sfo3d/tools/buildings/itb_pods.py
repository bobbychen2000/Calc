"""ITB Boarding Areas A and G: the raised roof pods (and the box at the WNW end of BA-G pod 3) traced on NAIP 2024 for
the BI-01 / BI-04 sheets (tools/buildings/draw_itb.py) and the 3-D step. Numbers only are written
(tools/buildings/itb_pods.json); NAIP 2024 (USDA, public domain) is read from refs/cache/naip/ (draw_lib.sample_lum).

Pier frames (as spec_itb.json verification #11, NAIP edge alignment): BA-A heading 208.0 deg, BA-G 297.75 deg.
  s = metres along the pier heading (A: + SSW, away from the ITB; G: + WNW, away from the ITB),
  t = metres across, + towards heading - 90 (A: ESE, G: SSW); origin = centre of the SFO Museum pier outline's
  s / t extent. Traced positions are IMAGED (NAIP 2024-05-20, roofs leaning east by relief).

What is traced [obs] (control values in POD_* below, read on 8-16 px/m pier-frame crops of NAIP; +-0.5-1 m):
  BA-A: 3 D-shaped pods. The curved WNW edge is scanned automatically every metre (inner edge of the dark band =
        visible WNW face + shadow); the ends (straight, across the pier) by eye; the straight ESE side is only a weak
        line (median luminance dip of ~8 grey levels at t 23.5-24.5, present at all three pods and absent between
        them) -> [obs, weak]; photo a2 (Pi.1415926535, 2025, CC BY-SA 4.0; BA-A seen from the east) shows straight near
        walls set back a little from the ESE facade, which agrees.
  BA-G: 3 lens-shaped pods truncated by straight end walls across the pier (ESE end: light parapet line; WNW end:
        dark band = visible WNW face + shadow), curved NNE / SSW edges (apex and end corners by eye, parabolic in
        between [inf shape between the read points]).
  BA-G pod 3 WNW end: a raised box (imaged roof ~8 x 9 m), the only rooftop structure on BA-G whose WNW band is wider
        than the pods' (see heights); it matches the box-shaped cab with a dark window band and antennas on a raised
        roof volume in photo d2 (wbaiv, 2018-09-08, CC BY 4.0) [inf identification: ramp-control cab, cf. "Ramp G
        (West)" in docs/research/atc.md; function not confirmed by any SFO source].

Heights [obs, low]: a raised volume's band on its WNW side is (visible face + shadow) x rise, with the face term from the
relief model (BA-A: draw_data.lean_frame, as draw_measure; BA-G: k(x) east, as spec ba_g.height_roof) and the shadow
term cot(72.4 deg) x (shadow azimuth 6.6 deg . outward normal). Band = half-level width (dark minimum to the roof level
on the inner side), median over the stations listed. Pod tops = main pier roof (spec) + rise; the main roofs carry
their own ranges (A 16.9-18.8, G 13-20). Outlines are relief-corrected with the pod / box top heights.

Usage: python3 tools/buildings/itb_pods.py   (needs refs/cache/naip/naip_2024_world_0.5m_bgr.npy)
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_data as D  # noqa: E402
from draw_lib import sample_lum, hdg_vec  # noqa: E402

OUT = os.path.join(HERE, 'itb_pods.json')
SUN_ELEV, SHADOW_AZ = 72.4, 6.6           # spec naip.sun (NOAA solar position at 13:14 PDT 2024-05-20, verification #27)
COT = 1.0 / math.tan(math.radians(SUN_ELEV))

PIERS = {
    'A': dict(name='Boarding Area A', hdg=208.0, h_main=D.IV['ba_a.height_roof']['value'], h_range=D.IV['ba_a.height_roof']['range_m'],
              relief='frame (draw_data.lean_frame)'),
    'G': dict(name='Boarding Area G', hdg=297.75, h_main=D.IV['ba_g.height_roof']['value'], h_range=D.IV['ba_g.height_roof']['range_m'],
              relief='k(x) east (spec naip.k_model)'),
}

# ---------------------------------------------------------------------------------------------- traced control values
# BA-A pods: ends s (by eye on the crops; the arc band starts / stops there), ESE side t (weak luminance dip)
POD_A = [dict(id='A1', s=(-103.4, -47.5)), dict(id='A2', s=(-15.6, 36.0)), dict(id='A3', s=(68.1, 124.0))]
A_T_ESE = 24.0
# BA-G pods: ESE end s, WNW end s (roof edge = inner side of the end band), NNE / SSW apex t and their s, end-wall t
POD_G = [dict(id='G1', s=(-126.6, -68.25), apex_s=-96.0, t_nne=0.3, t_ssw=25.5, t_end_e=(5.9, 20.3), t_end_w=(6.5, 20.9)),
         dict(id='G2', s=(5.25, 59.5), apex_s=33.0, t_nne=0.4, t_ssw=25.0, t_end_e=(7.1, 20.9), t_end_w=(7.1, 20.3)),
         # G3: its WNW end wall lies UNDER the image of the taller end box; its top edge is the light ridge between the box-face
         # band and the pod-end band of the box profile (s 194.25-194.5), so the pod runs to 194.5 (the NNE edge meets the
         # box image at s ~186, t ~6.5); end-wall t as G1 / G2 [inf]
         dict(id='G3', s=(132.0, 194.5), apex_s=160.0, t_nne=0.25, t_ssw=25.6, t_end_e=(6.5, 19.6), t_end_w=(7.0, 20.5))]
BOX_G = dict(id='G3-box', s=(183.0, 191.25), t=(8.5, 17.5))      # imaged roof of the box at the WNW end of pod 3


def frame(P):
    r = np.asarray(D.outer_rings(P['name'], 'boardingAreas')[0], float)
    ax = hdg_vec(P['hdg']); n = hdg_vec(P['hdg'] - 90.0)
    m = r.mean(0); s = (r - m) @ ax; t = (r - m) @ n
    c = m + ax * (s.min() + s.max()) / 2 + n * (t.min() + t.max()) / 2
    return c, ax, n


def to_world(F, s, t):
    c, ax, n = F
    return c + np.multiply.outer(np.asarray(s, float), ax) + np.multiply.outer(np.asarray(t, float), n)


def lum_grid(F, ss, tt):
    c, ax, n = F
    Sg, Tg = np.meshgrid(ss, tt, indexing='ij')
    return sample_lum(c[0] + Sg * ax[0] + Tg * n[0], c[1] + Sg * ax[1] + Tg * n[1])


def lean_per_m(key, P, h):
    """imaged shift (world x, z) per metre of height at world point P for a top at h."""
    if key == 'A':
        return D.lean_frame(P, h) / h
    return np.array([D.k_x_model(float(P[0])), 0.0])


def band_coef(key, P, h, m_out):
    """band width per metre of rise on the side with outward normal m_out: visible face + shadow beyond its foot."""
    L = lean_per_m(key, P, h); sd = hdg_vec(SHADOW_AZ) * COT
    return max(0.0, -float(L @ m_out)) + max(0.0, float(sd @ m_out))


def half_band(prof, x, inner_side):
    """half-level width of the dark band in prof(x): from the minimum outwards and inwards to the level halfway
    between the minimum and the INNER (roof) level; inner_side = -1 if the roof lies at smaller x."""
    i = int(np.argmin(prof)); lo = float(prof[i])
    dx = x[1] - x[0]; k = int(round(2.0 / dx)); w = int(round(4.0 / dx))
    roof = prof[max(0, i - k - w):max(1, i - k)] if inner_side < 0 else prof[i + k:i + k + w]
    lv = 0.5 * (lo + (float(np.median(roof)) if len(roof) else float(prof.max())))
    a = i
    while a > 0 and prof[a] < lv: a -= 1
    b = i
    while b < len(prof) - 1 and prof[b] < lv: b += 1
    return float(x[b] - x[a]), float(x[a]), float(x[b]), lo


def scan_arc_A(F, s0, s1):
    """BA-A WNW arc: inner (ESE) edge of the dark band, every metre."""
    pts, widths = [], []
    for s in np.arange(math.ceil(s0 + 1.5), s1 - 1.0, 1.0):
        tt = np.arange(-7.0, 8.0, 0.25)
        prof = np.median(lum_grid(F, np.arange(s - 0.5, s + 0.51, 0.25), tt), axis=0)
        w, a, b, lo = half_band(prof, tt, +1)
        if lo < 185: pts.append((float(s), b)); widths.append(w)
    return pts, widths


def parab(s, s_end, s_apex, t_end, t_apex):
    return t_apex + (t_end - t_apex) * ((s - s_apex) / (s_end - s_apex)) ** 2


def ring_G(p):
    (se, sw), sa = p['s'], p['apex_s']
    a1 = np.linspace(se, sa, 12); a2 = np.linspace(sa, sw, 12)[1:]
    nne = [(s, parab(s, se, sa, p['t_end_e'][0], p['t_nne'])) for s in a1] + [(s, parab(s, sw, sa, p['t_end_w'][0], p['t_nne'])) for s in a2]
    ssw = [(s, parab(s, se, sa, p['t_end_e'][1], p['t_ssw'])) for s in a1] + [(s, parab(s, sw, sa, p['t_end_w'][1], p['t_ssw'])) for s in a2]
    return nne + ssw[::-1]


def correct(key, ring_w, h):
    out = []
    for P in ring_w:
        out.append(P - lean_per_m(key, P, h) * h)
    return np.array(out)


def main():
    res = dict(generated_by='tools/buildings/itb_pods.py', imagery='NAIP 2024-05-20 (refs/cache/naip/naip_2024_world_0.5m_bgr.npy), USDA, public domain',
               sun=dict(elev_deg=SUN_ELEV, shadow_az_deg=SHADOW_AZ), piers={}, pods=[], notes=[])
    for key, P in PIERS.items():
        F = frame(P)
        res['piers'][key] = dict(name=P['name'], heading_deg=P['hdg'], centre_xz=[round(float(v), 2) for v in F[0]],
                                 s_axis=[round(float(v), 5) for v in F[1]], t_axis=[round(float(v), 5) for v in F[2]],
                                 h_main_roof=P['h_main'], h_main_range=P['h_range'], relief=P['relief'])
    # ---------------- BA-A
    FA = frame(PIERS['A']); m_wnw = -FA[2]
    for p in POD_A:
        s0, s1 = p['s']
        arc, widths = scan_arc_A(FA, s0, s1)
        band = float(np.median(widths[len(widths) // 4: -len(widths) // 4]))      # middle half of the arc (near-apex stations)
        Pm = to_world(FA, (s0 + s1) / 2, 0.0)
        coef = band_coef('A', Pm, PIERS['A']['h_main'] + 5.0, m_wnw)
        rise = band / coef
        top = PIERS['A']['h_main'] + rise
        t_end0, t_end1 = arc[0][1], arc[-1][1]
        st = [(s0, t_end0)] + arc + [(s1, t_end1), (s1, A_T_ESE), (s0, A_T_ESE)]
        img = to_world(FA, [q[0] for q in st], [q[1] for q in st])
        true = correct('A', img, top)
        apex = min(q[1] for q in arc)
        res['pods'].append(dict(id=p['id'], pier='A', plan='D: curved WNW edge [obs], straight ends [obs], straight ESE side [obs, weak]',
                                length_m=round(s1 - s0, 1), width_m=round(A_T_ESE - apex, 1),
                                band_wnw_m=round(band, 2), band_coef_per_m=round(coef, 3), rise_m=round(rise, 1),
                                top_m=round(top, 1), top_range_m=[round(PIERS['A']['h_range'][0] + rise - 0.5, 1), round(PIERS['A']['h_range'][1] + rise + 0.5, 1)],
                                ring_imaged_pier=[[round(a, 2), round(b, 2)] for a, b in st],
                                ring_imaged_xz=[[round(float(x), 2), round(float(z), 2)] for x, z in img],
                                ring_true_xz=[[round(float(x), 2), round(float(z), 2)] for x, z in true]))
    # ---------------- BA-G
    FG = frame(PIERS['G']); ax = FG[1]
    for p in POD_G:
        sw = p['s'][1]
        ss = np.arange(sw - 8.0, sw + 9.0, 0.25)
        widths = []
        for t0 in (9.0, 12.0, 15.0):
            prof = np.median(lum_grid(FG, ss, np.arange(t0, t0 + 3.0, 0.25)), axis=1)
            widths.append(half_band(prof, ss, -1)[0])
        band = float(np.median(widths))
        Pm = to_world(FG, sw, 13.0)
        coef = band_coef('G', Pm, PIERS['G']['h_main'] + 5.0, ax)
        rise = band / coef; top = PIERS['G']['h_main'] + rise
        st = ring_G(p)
        img = to_world(FG, [q[0] for q in st], [q[1] for q in st])
        true = correct('G', img, top)
        res['pods'].append(dict(id=p['id'], pier='G', plan='lens truncated by straight end walls: ends [obs], apexes [obs], edges parabolic between them [inf]',
                                length_m=round(p['s'][1] - p['s'][0], 1), width_m=round(p['t_ssw'] - p['t_nne'], 1),
                                band_wnw_m=round(band, 2), band_coef_per_m=round(coef, 3), rise_m=round(rise, 1), top_m=round(top, 1),
                                top_range_m=[round(PIERS['G']['h_range'][0] + rise - 0.5, 1), round(PIERS['G']['h_range'][1] + rise + 0.5, 1)],
                                ring_imaged_pier=[[round(a, 2), round(b, 2)] for a, b in st],
                                ring_imaged_xz=[[round(float(x), 2), round(float(z), 2)] for x, z in img],
                                ring_true_xz=[[round(float(x), 2), round(float(z), 2)] for x, z in true]))
    # ---------------- BA-G pod-3 end box. Its WNW band is TWO dark bands split by a narrow light ridge (a ledge / parapet at
    # the pod roof): band 1 = the box face above the pod roof (+ part of its shadow), band 2 = the pod's own end wall + its
    # shadow on the main roof (as pods G1 / G2). Rise of the box above the pod = band 1 / (face + shadow) .. band 1 / face.
    b = BOX_G; ss = np.arange(b['s'][1] - 3.0, b['s'][1] + 9.0, 0.25)
    b1, b2 = [], []
    for t0 in (9.0, 11.0, 13.0):
        prof = np.median(lum_grid(FG, ss, np.arange(t0, t0 + 2.0, 0.25)), axis=1)
        i1 = int(np.argmin(prof)); far = np.abs(ss - ss[i1]) > 1.5
        i2 = int(np.argmin(np.where(far, prof, 1e9))); lo_i, hi_i = sorted((i1, i2))
        r = lo_i + int(np.argmax(prof[lo_i:hi_i + 1]))                    # the light ridge between the two minima
        b1.append(half_band(prof[:r + 1], ss[:r + 1], -1)[0])
        roof = float(np.median(prof[:int(round(1.5 / 0.25))]))           # box roof level (inner side)
        lv = 0.5 * (float(prof[hi_i]) + roof); j = hi_i
        while j < len(prof) - 1 and prof[j] < lv: j += 1
        b2.append(float(ss[j] - ss[r]))
    band1, band2 = float(np.median(b1)), float(np.median(b2))
    Pm = to_world(FG, b['s'][1], 13.0)
    coef = band_coef('G', Pm, PIERS['G']['h_main'] + 8.0, ax)
    face = max(0.0, -float(lean_per_m('G', Pm, 25.0) @ ax))
    rise_pod3 = band2 / coef
    r_lo, r_hi = band1 / coef, band1 / face
    for q in res['pods']:
        if q['id'] == 'G3':        # the pod-3 end wall is behind the box: its rise comes from band 2 (and G1 / G2 agree)
            q['band_wnw_m'] = round(band2, 2); q['band_coef_per_m'] = round(coef, 3); q['rise_m'] = round(rise_pod3, 1)
            q['top_m'] = round(PIERS['G']['h_main'] + rise_pod3, 1)
            q['top_range_m'] = [round(PIERS['G']['h_range'][0] + rise_pod3 - 0.5, 1), round(PIERS['G']['h_range'][1] + rise_pod3 + 0.5, 1)]
            q['note'] = 'rise from band 2 of the end-box profile (the pod end wall + its shadow beside the box)'
    top_lo = PIERS['G']['h_main'] + rise_pod3 + r_lo; top_hi = PIERS['G']['h_main'] + rise_pod3 + r_hi
    top = 0.5 * (top_lo + top_hi)
    st = [(b['s'][0], b['t'][0]), (b['s'][1], b['t'][0]), (b['s'][1], b['t'][1]), (b['s'][0], b['t'][1])]
    img = to_world(FG, [q[0] for q in st], [q[1] for q in st]); true = correct('G', img, top)
    res['pods'].append(dict(id=b['id'], pier='G', plan='box at the WNW end of pod 3, imaged roof ~8 x 9 m [obs]',
                            length_m=round(b['s'][1] - b['s'][0], 1), width_m=round(b['t'][1] - b['t'][0], 1),
                            band_box_face_m=round(band1, 2), band_pod_end_m=round(band2, 2), face_coef_per_m=round(face, 3),
                            band_coef_per_m=round(coef, 3), rise_above_pod_m=[round(r_lo, 1), round(r_hi, 1)],
                            rise_m=[round(rise_pod3 + r_lo, 1), round(rise_pod3 + r_hi, 1)],
                            top_m=round(top, 1), top_main_value_m=[round(top_lo, 1), round(top_hi, 1)],
                            top_range_m=[round(PIERS['G']['h_range'][0] + rise_pod3 + r_lo - 0.5, 1), round(PIERS['G']['h_range'][1] + rise_pod3 + r_hi + 0.5, 1)],
                            identification='box-shaped cab with a dark window band and antennas on a raised roof volume, photo d2 (2018-09-08) [obs photo]; '
                                           'ramp-control cab [inf, not confirmed]; still standing on NAIP 2024-05-20 [obs]',
                            ring_imaged_pier=[[round(a, 2), round(c, 2)] for a, c in st],
                            ring_imaged_xz=[[round(float(x), 2), round(float(z), 2)] for x, z in img],
                            ring_true_xz=[[round(float(x), 2), round(float(z), 2)] for x, z in true]))
    res['notes'] = [
        'rise = band / band_coef; band = half-level width of the dark band on the WNW side (BA-A: the arc near its apex; BA-G: the WNW end wall)',
        'top_range adds the main-roof range of the spec (+-0.5 m for the band); the BA-A pod 1 top is also FAA DOF 06-035352 = 25.91 m [pub]',
        'outlines: imaged (as traced) and true (relief removed with the top height); BA-G outlines carry the unresolved 3-6 m NNE offset of the '
        'SFO Museum G outline only through the frame origin (the traced positions are NAIP-only)']
    json.dump(res, open(OUT, 'w'), indent=1)
    for p in res['pods']:
        print(p['id'], 'L', p['length_m'], 'W', p['width_m'], 'band', p.get('band_wnw_m', (p.get('band_box_face_m'), p.get('band_pod_end_m'))),
              'coef', p['band_coef_per_m'], 'rise', p['rise_m'], 'top', p['top_m'], p['top_range_m'])


if __name__ == '__main__':
    main()
