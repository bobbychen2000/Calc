"""Domestic terminals - roof heights above the apron from NAIP 2020 + 2024 shadows and relief (no lidar is available).

Why two epochs (docs/research/imagery.md s.6, docs/research/buildings_domestic.md s.4):
  * NAIP 2020 (2020-05-24) was flown late in the afternoon: sun azimuth ~267 deg, elevation ~40 deg, long shadows
    towards the ESE. NAIP 2024 (2024-05-20) was flown at ~13:15 PDT: sun az 186.6 deg, el 72.5 deg (FAA DOF pole
    06-034826, tools/buildings/itb_naip_measurements.json), short shadows towards the NNE.
  * Both are orthorectified to a terrain DEM, so a roof point at height h is imaged displaced by k_e * h (k_e: unknown
    2-D vector per epoch that varies over the scene - frame/strip geometry).

Per roof we measure, on grid-aligned straight edges (median cross-profiles, dom_profile.py, 0.1 m sampling):
  band20 = f20 - e20   outward width of the dark band (roof edge -> end of the cast shadow on the apron) on the face
                       whose outward normal n points away from the 2020 sun (ESE / ENE faces)          = h (s20 - k20).n
  band24 = e24m - f24m width of the dark band on the opposite face (normal -n) in 2024 (shaded facade + shadow)
                                                                                                       = h (k24 - s24).n
  p      = shift of the same roof edge / roof texture between 2020 and 2024 along n                  = h (k24 - k20).n
Adding the first two and subtracting the third eliminates BOTH unknown lean vectors:
            h = (band20 + band24 - p) / ((s20 - s24) . n)
The sun vectors are s = cot(el) * (sin az_s, -cos az_s) in world (x east, z south), az_s = sun azimuth + 180.
The local leans follow as by-products: k24.n = band24/h + s24.n, k20.n = s20.n - band20/h (sanity: 0 < k < 0.7).

Calibration of |s20| (the only scale-setting constant): NAIP 2020 carries no acquisition time. The ATCT shadow gives the
shadow azimuth (87.4 +- 1.5 deg); on the 2020-05-24 sun path that is el 38.3-40.9 deg, |s20| = 1.15-1.29 (dom_sun.py).
Two independent height controls fix it (see CAL below): FAA DOF 06-035331 (Boarding Area F north-east arm roof,
34 ft AGL, accuracy 1A = +-3 ft) and Boarding Area A with k24 from the FAA DOF poles (ITB research,
tools/buildings/itb_naip_measurements.json). Both give |s20| = 1.18-1.20; we use 1.19 +- 0.03.

Outputs: tools/buildings/dom_heights.json (numbers only) and QA plots out/buildings/domestic/h_<id>.png (profiles with
the picked edges; no imagery pixels). usage: python3 tools/buildings/dom_heights.py
"""
import json, math, os
import numpy as np
import dom_profile as P
import dom_common as C

S20_AZ_SHADOW = 87.4          # deg, ATCT shadow direction on NAIP 2020 (this study, tower_2020_shadow.jpg)
S20_ABS = 1.19                # m of shadow per m of height (calibrated, see header); +- 0.03
S20_ABS_SD = 0.03
S24_AZ_SHADOW = 6.6           # deg, from the ITB research (DOF pole 06-034826 shadow on NAIP 2024)
S24_ABS = 1 / math.tan(math.radians(72.5))


def svec(az_shadow, mag):
    a = math.radians(az_shadow); return np.array([math.sin(a), -math.cos(a)]) * mag


def nvec(hdg):
    a = math.radians(hdg); return np.array([math.sin(a), -math.cos(a)])


# ------------------------------------------------------------------------------------------------------------ roofs
# Each roof: the 2020-shadow face (line p0->p1 whose clockwise normal is the outward normal n) and the opposite face
# (line q0->q1 whose clockwise normal is -n). Windows are in the profile coordinate u (m, + outward along that face's
# normal): e = roof edge (bright -> dark going outward), f = far edge of the dark band (dark -> bright).
# p: 'edge' = e24n - e20n on the n face; or a number (m) measured by 1-D correlation of roof texture (see notes).
ROOFS = [
    dict(id='ba_a_body', name='Boarding Area A (ITB) main body - CONTROL', x=-1230,
         n_face=((-1249.72, 740.58), (-1220.8, 685.73)), win20=dict(e=(0, 4), f=(18, 26)), win24n=None,
         m_face=((-1256.18, 667.08), (-1285.1, 721.92)), win24m=dict(e=(-9, -4), f=(0, 5)),
         p=7.55, p_note='WNW roof edge 2020 -800.8 -> 2024 -793.3 (s) and edge+width check on the ESE side; 1-D '
                        'correlation of the edge profiles 7.6 m'),
    dict(id='ba_b_south', name='Boarding Area B, south half (gates B19-B27 side), outer roof edge', x=-905,
         n_face=((-918.9, 915.03), (-889.98, 860.18)), win20=dict(e=(2, 6), f=(13, 20)), win24n=None,
         m_face=((-931.55, 838.26), (-960.47, 893.1)), win24m=dict(e=(-3, 2), f=(4, 9)),
         p=3.35, p_note='outer roof edge 2020 -381.9 -> 2024 -378.6 (s) = 3.3 m; PV rows 1-D correlation 3.4 m '
                        '(r 0.73): the dark ESE perimeter strip and the PV field shift alike, i.e. same height'),
    dict(id='ba_e_north', name='Boarding Area E, north part (gates E1-E6 side)', x=-800,
         n_face=None, win20=None, win24n=None, m_face=None, win24m=None, p=2.4,
         manual=dict(band20=11.3, band24=6.5, p=2.4, note='s-profiles t -350..-310: fascia edge 2020 -686.2, shadow end '
                     '-674.9; 2024 WNW band -733.0 .. -726.5; roof texture shift 2.5 m (r 0.70), fascia edge shift 2.2 m')),
    dict(id='ba_f_ne_arm', name='Boarding Area F north-east arm (F1-F3 side) - CONTROL vs FAA DOF 06-035331', x=-1030,
         n_face=((-1040.2, -152.5), (-1015.9, -198.9)), win20=dict(e=(1, 5), f=(10, 16)), win24n=dict(e=(3, 8)),
         m_face=((-1037.2, -215.1), (-1063.7, -165.1)), win24m=dict(e=(-7, -2), f=(-2, 3)), p='edge'),
    dict(id='ba_d_head', name='Boarding Area D head (gates D10-D16 end) - faces 90 m apart, LOW confidence', x=-520,
         n_face=((-493.6, 222.4), (-475.6, 188.5)), win20=dict(e=(-2, 1), f=(9, 14)), win24n=dict(e=(5, 9)),
         m_face=((-563.1, 102.4), (-580.1, 134.5)), win24m=dict(e=(-8, -3), f=(-2, 2)), p='edge'),
    dict(id='ba_c_east', name='Boarding Area C, east half, NNE face (single face, assumed k24) - LOW confidence', x=-640,
         single=dict(line=((-619.6, 425.3), (-665.0, 401.5)), e20=(-3, 1), f20=(4, 9), e24=(1, 4), k24x=0.40, k24x_sd=0.06)),
]
# the B-south WNW face (m_face) is the main roof edge at s = -433.3 (2024) between t -1245 and -1160; line given in
# world coordinates with its clockwise normal pointing WNW.


def pick(year, line, win, key, sign):
    u, prof, n = P.edge_profile(year, line[0], line[1], half=30.0)
    r = P.step(u, prof, win[0], win[1], sign)
    return r, n


def measure(R):
    s20 = svec(S20_AZ_SHADOW, S20_ABS); s24 = svec(S24_AZ_SHADOW, S24_ABS)
    out = dict(id=R['id'], name=R['name'], x=R['x'])
    if R.get('single'):
        S = R['single']; line = S['line']
        e20, n = pick(2020, line, S['e20'], 'e', -1); f20, _ = pick(2020, line, S['f20'], 'f', +1)
        e24, _ = pick(2024, line, S['e24'], 'e', -1)
        b20 = f20['pos'] - e20['pos']; p = e24['pos'] - e20['pos']
        k24 = np.array([S['k24x'], 0.0])
        den = float(np.dot(s20 - k24, n)); h = (b20 - p) / den
        dden = abs(S['k24x_sd'] * n[0]) + abs(np.dot(svec(S20_AZ_SHADOW, S20_ABS_SD), n))
        sd = math.hypot(0.35 * 1.7 / den, h * dden / den)
        out.update(method='single face: h = (band20 - p) / ((s20 - k24).n), k24 assumed', e20=e20, f20=f20, e24=e24,
                   n_hdg=round(P.heading(n), 1), band20=round(b20, 2), p=round(p, 2), den=round(den, 3),
                   h_m=round(h, 2), h_sd_m=round(sd, 2), h_ft=round(h / C.FT, 1), k24_assumed=S['k24x'])
        return out
    if R.get('manual'):
        M = R['manual']; b20, b24, p = M['band20'], M['band24'], M['p']; nE = nvec(117.83)
        out.update(method_note=M['note'])
    else:
        e20, n = pick(2020, R['n_face'], R['win20']['e'], 'e', -1)
        f20, _ = pick(2020, R['n_face'], R['win20']['f'], 'f', +1)
        e24m, nm = pick(2024, R['m_face'], R['win24m']['e'], 'e', -1)   # outward on m face = -n ; roof inside
        f24m, _ = pick(2024, R['m_face'], R['win24m']['f'], 'f', +1)
        b20 = f20['pos'] - e20['pos']
        b24 = f24m['pos'] - e24m['pos']
        if R['p'] == 'edge':
            e24n, _ = pick(2024, R['n_face'], R['win24n']['e'], 'e', -1)
            p = e24n['pos'] - e20['pos']; out['e24n'] = e24n
        else:
            p = R['p']
        nE = n
        out.update(e20=e20, f20=f20, e24m=e24m, f24m=f24m, n_hdg=round(P.heading(n), 1))
    den = float(np.dot(s20 - s24, nE))
    h = (b20 + b24 - p) / den
    # uncertainty: 0.35 m per picked edge (4 edges) + |s20| +- 0.03
    dden = abs(np.dot(svec(S20_AZ_SHADOW, S20_ABS + S20_ABS_SD) - s24, nE) - den)
    sd = math.hypot(0.35 * 2 / den, h * dden / den)
    # band24 = h (k24 - s24).n  ->  k24.n = band24/h + s24.n
    k24n = b24 / h + float(np.dot(s24, nE))
    k20n = float(np.dot(s20, nE)) - b20 / h
    out.update(band20=round(b20, 2), band24=round(b24, 2), p=round(p, 2), den=round(den, 3), h_m=round(h, 2),
               h_sd_m=round(sd, 2), h_ft=round(h / C.FT, 1), k24_n=round(k24n, 3), k20_n=round(k20n, 3),
               k24_x_if_east=round(k24n / nE[0], 3), p_check=round(h * (k24n - k20n), 2))
    return out


def main():
    res = [measure(R) for R in ROOFS]
    meta = dict(generated_by='tools/buildings/dom_heights.py', s20=dict(az_shadow=S20_AZ_SHADOW, abs=S20_ABS, sd=S20_ABS_SD),
                s24=dict(az_shadow=S24_AZ_SHADOW, abs=round(S24_ABS, 4)),
                equation='h = (band20 + band24 - p) / ((s20 - s24) . n)', roofs=res)
    json.dump(meta, open(os.path.join(os.path.dirname(__file__), 'dom_heights.json'), 'w'), indent=1)
    for r in res:
        if 'k24_n' not in r:
            print('%-14s h = %5.2f +- %.2f m (%5.1f ft)  band20 %.2f p %.2f den %.3f (single face)' % (
                r['id'], r['h_m'], r['h_sd_m'], r['h_ft'], r['band20'], r['p'], r['den'])); continue
        print('%-14s h = %5.2f +- %.2f m (%5.1f ft)  band20 %.2f band24 %.2f p %.2f den %.3f  k24.n %.3f k20.n %.3f'
              % (r['id'], r['h_m'], r['h_sd_m'], r['h_ft'], r['band20'], r['band24'], r['p'], r['den'], r['k24_n'], r['k20_n']))


if __name__ == '__main__':
    main()


# ------------------------------------------------------------------------------------------------ derived geometry
def true_edges(R, r):
    """lean-free roof-edge positions (world lines) from the measured image edges and the solved leans:
    n face: true = e20 - (k20.n) h  (2020 image);  m face: true = e24m + (k24.n) h  (2024 image, outward = -n)."""
    if 'k24_n' not in r or R.get('manual'): return None
    def offset_line(line, du):
        (x0, z0), (x1, z1) = line; L = math.hypot(x1 - x0, z1 - z0); d = ((x1 - x0) / L, (z1 - z0) / L)
        n = (-d[1], d[0])
        return [[round(x0 + n[0] * du, 2), round(z0 + n[1] * du, 2)], [round(x1 + n[0] * du, 2), round(z1 + n[1] * du, 2)]]
    un = r['e20']['pos'] - r['k20_n'] * r['h_m']
    um = r['e24m']['pos'] + r['k24_n'] * r['h_m']
    return dict(n_line=offset_line(R['n_face'], un), n_offset_from_line=round(un, 2),
                m_line=offset_line(R['m_face'], um), m_offset_from_line=round(um, 2))


def qa(R, r, te):
    import cv2
    pts = [p for p in (R.get('n_face') or ()) + (R.get('m_face') or ())]
    if R.get('single'): pts = list(R['single']['line'])
    if not pts: return
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    x0, x1, z0, z1 = min(xs) - 45, max(xs) + 45, min(zs) - 45, max(zs) + 45
    for yr in (2020, 2024):
        img, o = C.crop(yr, x0, x1, z0, z1, res=0.25)
        im = C.grid_overlay(img, o, step=10, label=50)
        P_ = lambda x, z: (int(round((x - x0) / 0.25)), int(round((z - z0) / 0.25)))
        for key, col in (('n_face', (0, 0, 255)), ('m_face', (255, 0, 0))):
            if R.get(key): cv2.line(im, P_(*R[key][0]), P_(*R[key][1]), col, 1)
        if te:
            for key in ('n_line', 'm_line'):
                cv2.line(im, P_(*te[key][0]), P_(*te[key][1]), (0, 255, 0), 2)
        cv2.putText(im, '%s %d  h=%.1f+-%.1f m' % (r['id'], yr, r['h_m'], r['h_sd_m']), (8, im.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        C.save_qa(f'h_{r["id"]}_{yr}.jpg', im)


def main2():
    d = json.load(open(os.path.join(os.path.dirname(__file__), 'dom_heights.json')))
    byid = {R['id']: R for R in ROOFS}
    for r in d['roofs']:
        R = byid[r['id']]; te = true_edges(R, r)
        if te: r['true_edges'] = te
        qa(R, r, te)
    json.dump(d, open(os.path.join(os.path.dirname(__file__), 'dom_heights.json'), 'w'), indent=1)


if __name__ == '__main__':
    main2()
