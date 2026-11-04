"""Boarding Area B (Harvey Milk T1): does the raised central roof run the whole pier? [obs, reproducible]

Review finding r1-23 (docs/drawings/buildings/review_backlog.json): BD-01 / BD-02 drew the raised central roof (19.0 m,
verified on the south half only, docs/research/buildings_domestic.md V.3) over ~60 m at the south tip. This script
repeats the verification's two independent measurements at stations along the WHOLE pier (airport grid t -1256..-940;
the pier runs along t, its ESE outer edge is s = const):

  1. 2020 step shadow  NAIP 2020 (late-afternoon sun from the W, |s20| 1.25): a raised roof casts a shadow on the lower
                       ESE band. Per 2-m station (4-m median strip): the raised edge (bright -> dark, s -391..-386.5),
                       the shadow end (dark -> bright, s -386..-382.6), the strip minimum. Present = the strip is darker
                       than 120 and the raised edge contrast < -50. Step height = shadow length / (s20 - k20).n
                       (0.916 m/m, the verification's south calibration: 4.90 m <-> 19.04 - 13.14 m).
  2. parallax          local 1-D NCC shifts 2020 -> 2024 in 6-m windows (dom_verify.lshift) per 10-m station (20-m
                       strip): the central band (window centres s -416..-390, r > 0.95, 2.5 < p < 5) against the ESE
                       outer lip (steepest-descent edge per row, 2020 vs 2024, as dom_verify.ba_b). Different shifts =
                       different heights: h_central = h_outer x p_central / p_lip, with h_outer = bab.h_roof 13.14 m
                       taken for the whole pier [inf: the outer edge is measured on the south half only].
  3. 2024 WNW edge     NAIP 2024 (lean ~0.34 m/m towards the ESE): the raised roof's WNW wall is seen obliquely as a dark
                       band ending at the imaged roof edge (dark -> bright, s -421..-414); lean-free edge = imaged edge -
                       k24.n x h_central (k24.n 0.342, verification 'central').

Inputs: NAIP 2020 / 2024 epoch rasters on the world grid (refs/cache/buildings/domestic/naip/, dom_naip_epochs.py; local).
Output: tools/buildings/dom_bab_band.json (numbers only; committable). Read by draw_domestic.py (BD-01 / BD-02).
usage: python3 tools/buildings/dom_bab_band.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, 'dom_bab_band.json')
H_OUTER = 13.14            # bab.h_roof (verified, south half)
H_CENTRAL_SOUTH = 19.04    # bab.h_roof_central (verified, south half)
K20N, K24N = 0.169, 0.342  # dom_verify.json ba_b_section['central'] (|s20| 1.25)
SH_PER_M = 4.90 / (H_CENTRAL_SOUTH - H_OUTER)   # (s20 - k20).n, m of 2020 step shadow per m of step


def step_shadow(t0, t1):
    import dom_profile as P
    import dom_verify as V
    s, Pr = V.st_profiles(-400, -370, t0, t1, years=(2020,))
    p = Pr[2020]
    e = P.step(s, p, -391.0, -386.5, -1); f = P.step(s, p, -386.0, -382.6, +1)
    m = (s >= -388) & (s <= -384)
    lo = float(p[m].min())
    ok = bool(e and f and e['contrast'] < -50 and lo < 120 and f['pos'] > e['pos'])
    return dict(t=round((t0 + t1) / 2, 1), present=ok, edge=e['pos'] if e else None, end=f['pos'] if f else None,
                strip_min=round(lo, 1), length=round(f['pos'] - e['pos'], 2) if ok else None)


def lip_shift(t0, t1):
    """ESE outer lip, 2020 -> 2024: median steepest-descent position per 1-m row (as dom_verify.ba_b)."""
    import cv2
    import dom_common as C
    from dom_verify import RES
    out = []
    for yr, lo, hi in ((2020, -386, -378), (2024, -384, -374)):
        img, o = C.crop_st(yr, -400, -370, t0, t1, res=RES)
        G = cv2.GaussianBlur(C.gray(img), (0, 0), 1.5)
        ss = o[0] + (np.arange(G.shape[1]) + 0.5) * RES
        m = (ss >= lo) & (ss <= hi); idx = np.where(m)[0]
        pos = [ss[idx[np.argmin(np.gradient(G[i])[m])]] for i in range(0, G.shape[0], 10)]
        out.append(float(np.median(pos)))
    return round(out[1] - out[0], 2)


def parallax(t0, t1):
    import dom_verify as V
    s, Pr = V.st_profiles(-440, -370, t0, t1, years=(2020, 2024))
    cen = []
    for c0 in np.arange(-416, -389, 2.0):
        d, r = V.lshift(s, Pr[2020], Pr[2024], c0)
        if r > 0.95 and 2.5 < d < 5.0: cen.append(d)
    return dict(t=round((t0 + t1) / 2, 1), p_central=round(float(np.median(cen)), 2) if len(cen) >= 3 else None, n_windows=len(cen),
                p_lip=lip_shift(t0, t1))


def wnw_edge(t0, t1):
    import dom_profile as P
    import dom_verify as V
    s, Pr = V.st_profiles(-440, -405, t0, t1, years=(2024,))
    p = Pr[2024]
    f = P.step(s, p, -421.0, -414.0, +1)
    m = (s >= -424) & (s <= -418)
    lo = float(p[m].min())
    ok = bool(f and f['contrast'] > 60 and lo < 135)
    return dict(t=round((t0 + t1) / 2, 1), present=ok, edge_img=f['pos'] if f else None, band_min=round(lo, 1))


def main():
    sh = [step_shadow(t, t + 4) for t in np.arange(-1256, -940, 2.0)]
    pr = [parallax(t, t + 20) for t in np.arange(-1250, -940, 10.0)]
    wn = [wnw_edge(t, t + 10) for t in np.arange(-1250, -940, 10.0)]
    pres = [x['t'] for x in sh if x['present']]
    # longest run of consecutive stations with the step shadow (gaps <= 6 m: jet bridges / vehicles on the strip)
    runs, cur = [], [pres[0]]
    for t in pres[1:]:
        if t - cur[-1] <= 6.0: cur.append(t)
        else: runs.append(cur); cur = [t]
    runs.append(cur)
    run = max(runs, key=lambda r: r[-1] - r[0])
    L = [x['length'] for x in sh if x['present'] and run[0] <= x['t'] <= run[-1]]
    E = [x['edge'] for x in sh if x['present'] and run[0] <= x['t'] <= run[-1]]
    south = lambda t: -1236 <= t <= -1180
    north = lambda t: -1100 <= t <= -960
    hc = []
    for x in pr:
        if x['p_central'] and x['p_lip'] and x['p_lip'] > 1.0:
            x['h_central_parallax'] = round(H_OUTER * x['p_central'] / x['p_lip'], 2); hc.append(x)
    for x in sh:
        if x['present']: x['h_central_step_shadow'] = round(H_OUTER + x['length'] / SH_PER_M, 2)

    def stat(vals):
        v = np.array([a for a in vals if a is not None], float)
        return dict(median=round(float(np.median(v)), 2), p10=round(float(np.percentile(v, 10)), 2),
                    p90=round(float(np.percentile(v, 90)), 2), n=int(len(v))) if len(v) else None
    summ = {}
    for nm, sel in (('south', south), ('north', north), ('whole', lambda t: run[0] <= t <= run[-1])):
        summ[nm] = dict(step_shadow_len=stat([x['length'] for x in sh if x['present'] and sel(x['t'])]),
                        h_central_step_shadow=stat([x['h_central_step_shadow'] for x in sh if x['present'] and sel(x['t'])]),
                        p_central=stat([x['p_central'] for x in pr if sel(x['t'])]),
                        p_lip=stat([x['p_lip'] for x in pr if sel(x['t'])]),
                        h_central_parallax=stat([x['h_central_parallax'] for x in hc if sel(x['t'])]))
        a, b = summ[nm]['h_central_step_shadow'], summ[nm]['h_central_parallax']
        if a and b: summ[nm]['h_central'] = round(0.5 * (a['median'] + b['median']), 2)
    wok = [x for x in wn if x['present']]
    e24 = float(np.median([x['edge_img'] for x in wok])) if wok else None
    hN = summ['north'].get('h_central', H_CENTRAL_SOUTH)
    rec = dict(generated_by='tools/buildings/dom_bab_band.py', date='2026-11-04',
               inputs='NAIP 2020-05-24 / 2024-05-20 epoch rasters (dom_naip_epochs.py, 0.25 m world grid), airport grid (s, t)',
               method=__doc__.split('\n\n')[1].strip(),
               extent=dict(t_south=run[0] - 2.0, t_north=run[-1] + 2.0, length_m=round(run[-1] - run[0] + 4.0, 1),
                           note='first / last 4-m strip with the 2020 step shadow (+-2 m); gaps <= 6 m bridged. The north '
                                'end is where the straight pier bends towards T1 Center (the oblique north wing beyond it is '
                                'not tested: its edges do not run along t); the south end is ~15-20 m short of the tip'),
               ese_edge=dict(s_imaged_2020=round(float(np.median(E)), 2), sd=round(float(np.std(E)), 2),
                             s_lean_free=round(float(np.median(E)) - K20N * H_CENTRAL_SOUTH, 2),
                             note='imaged 2020 raised-roof edge minus k20.n x 19.04 (verification); constant along the pier'),
               wnw_edge=dict(stations=len(wok), t_range=[min(x['t'] for x in wok), max(x['t'] for x in wok)] if wok else None,
                             s_imaged_2024=round(e24, 2) if e24 else None,
                             s_lean_free=round(e24 - K24N * hN, 2) if e24 else None,
                             note='2024 dark wall band + edge, found where the planted roof wells lie below it (north half); '
                                  'on the south half the band is PV-covered / glazed and not dark: there the 14-m WNW step '
                                  'width of the verification is used [inf]'),
               step_shadow_len_whole=stat(L), summary=summ, stations_step_shadow=sh, stations_parallax=pr, stations_wnw_2024=wn,
               constants=dict(h_outer=H_OUTER, h_central_south=H_CENTRAL_SOUTH, k20_n=K20N, k24_n=K24N,
                              step_shadow_per_m=round(SH_PER_M, 3)))
    json.dump(rec, open(OUT, 'w'), indent=1)
    print('extent t', rec['extent'], '| ESE edge', rec['ese_edge'], '| WNW edge', rec['wnw_edge'])
    for k, v in summ.items(): print(k, v)


if __name__ == '__main__':
    main()
