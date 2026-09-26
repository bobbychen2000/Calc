"""Domestic terminals - roof-edge / shadow-edge profiles on NAIP, for relief- and shadow-based roof heights.

A straight roof edge aligned with the airport grid is sampled on a rotated crop (dom_common.crop_st, 0.1 m/px):
for every line across the edge (one per 0.1 m along it) the grey profile is read OUTWARD (from roof to apron) and
  * e = roof edge   : strongest bright->dark step within +-`win` m of the nominal edge,
  * f = far edge    : first strong dark->bright step beyond e (end of the dark band = shaded facade + cast shadow),
                      searched up to `maxband` m beyond e.
Rows are rejected when the band is not dark enough (jet bridges, vehicles, aircraft, parked GSE in the shadow) or the
steps are weak. The median over the accepted rows and its robust spread (1.4826 MAD / sqrt(n)) are reported.

Positions are signed coordinates along the outward normal: for faces along t (ESE/WNW) the coordinate is s (ESE +),
for faces along s (NNE/SSW) it is t (NNE +). Returned values are always given as the world-grid coordinate (s or t).

usage (library): measure(year, face) with face = dict(axis='s'|'t', at=<nominal edge coord>, a=<start>, b=<end>,
                  out=+1|-1, win=6, maxband=30)
"""
import numpy as np
import cv2
import dom_common as C

RES = 0.1


def _profiles(year, face):
    """grey profiles, one per row along the edge; returns (P, coords) with P[i, j] at outward distance coords[j]."""
    at, a, b, out = face['at'], face['a'], face['b'], face['out']
    lo, hi = at - face.get('win', 6) - 2, at + face.get('win', 6) + face.get('maxband', 30) + 2
    if out < 0: lo, hi = at - face.get('win', 6) - face.get('maxband', 30) - 2, at + face.get('win', 6) + 2
    if face['axis'] == 't':          # edge runs along t, profile along s
        img, (s0, t1, res) = C.crop_st(year, lo, hi, min(a, b), max(a, b), res=RES)
        G = cv2.GaussianBlur(C.gray(img), (0, 0), 1.5)
        coords = s0 + (np.arange(G.shape[1]) + 0.5) * res
        P = G if out > 0 else G[:, ::-1]
        coords = coords if out > 0 else coords[::-1]
    else:                            # edge runs along s, profile along t (rows = -t)
        img, (s0, t1, res) = C.crop_st(year, min(a, b), max(a, b), lo, hi, res=RES)
        G = cv2.GaussianBlur(C.gray(img), (0, 0), 1.5).T      # rows along s, columns along -t
        coords = t1 - (np.arange(G.shape[1]) + 0.5) * res
        P = G[:, ::-1] if out > 0 else G
        coords = coords[::-1] if out > 0 else coords
    return P, coords


def measure(year, face, band_max_grey=None, min_step=12.0, debug=False):
    P, coords = _profiles(year, face)
    at = face['at']; win = face.get('win', 6); maxband = face.get('maxband', 30); out = face['out']
    u = (coords - at) * out                                   # outward distance from the nominal edge
    D = np.diff(P, axis=1)                                    # outward derivative (per 0.1 m)
    Dk = cv2.blur(D, (7, 1))                                  # 0.7 m difference kernel
    es, fs, bands = [], [], []
    ce = (u[:-1] > -win) & (u[:-1] < win)
    for i in range(P.shape[0]):
        d = Dk[i]
        cand = np.where(ce)[0]
        j = cand[np.argmin(d[cand])]                         # most negative = bright -> dark
        if -d[j] * 7 < min_step: continue
        roof = np.median(P[i, max(0, j - 30):max(1, j - 5)])
        k0, k1 = j + 5, min(len(d) - 1, j + int(maxband / RES))
        if k1 <= k0 + 5: continue
        seg = d[k0:k1]
        k = k0 + int(np.argmax(seg))                          # most positive = dark -> bright
        if d[k] * 7 < min_step: continue
        band = P[i, j + 3:k - 2]
        if band.size < 3: continue
        bmean = np.median(band); ground = np.median(P[i, k + 5:min(P.shape[1], k + 40)])
        if bmean > 0.75 * min(roof, ground): continue         # band not dark enough (obstruction)
        if band_max_grey is not None and bmean > band_max_grey: continue
        es.append(coords[j] + out * RES / 2); fs.append(coords[k] + out * RES / 2); bands.append(bmean)
    es, fs = np.array(es), np.array(fs)
    n = len(es)
    if n < 20:
        return dict(n=n)
    w = (fs - es) * out
    def rob(v):
        med = float(np.median(v)); mad = float(np.median(np.abs(v - med)) * 1.4826)
        return med, mad, mad / np.sqrt(len(v))
    em, es_, ese = rob(es); fm, fs_, fse = rob(fs); wm, ws, wse = rob(w)
    return dict(n=n, rows=int(P.shape[0]), e=round(em, 2), e_sd=round(es_, 2), f=round(fm, 2), f_sd=round(fs_, 2),
                band=round(wm, 2), band_sd=round(ws, 2), band_se=round(wse, 3), e_se=round(ese, 3), f_se=round(fse, 3))


if __name__ == '__main__':
    import json, sys
    face = json.loads(sys.argv[2]); print(measure(int(sys.argv[1]), face))
