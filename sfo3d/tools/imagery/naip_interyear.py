"""NAIP 2022 vs NAIP 2024 consistency over the airfield (ground-level features only).

Two independent flights / orthorectifications (2022-05-18 and 2024-05-20, both 0.6 m, NAD83 / UTM 10N).
The world-frame grid over the AOI is cut into 200 m tiles; tiles with buildings (SFO Museum footprints + 10 m) or
water are skipped; each remaining tile is compared by phase correlation of gradient images (0.3 m sampling), and
tiles with a clear peak are kept.  The spread of the shifts bounds the relative accuracy of the two orthos on the
ground (roofs excluded - see outline_audit.py for the roof lean).
usage: python3 tools/imagery/naip_interyear.py
"""
import json, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from match import sample_bmask, bright_blobs, grad


def main():
    A, B = NaipSampler('2022'), NaipSampler('2024')
    res, T = 0.3, 200.0
    rows = []
    for z0 in np.arange(-2300, 2500, T):
        for x0 in np.arange(-2500, 2100, T):
            c = np.arange(0, T, res) + res / 2
            X, Z = np.meshgrid(x0 + c, z0 + c)
            if sample_bmask(X, Z).mean() > 0.02: continue
            a, b = A(X, Z), B(X, Z)
            if (a == 0).mean() > 0.01 or (b == 0).mean() > 0.01: continue
            if a.std() < 8: continue                                          # water / featureless
            m = ~(bright_blobs(a, res) | bright_blobs(b, res))
            ga, gb = grad(a, 1.0) * m, grad(b, 1.0) * m
            win = cv2.createHanningWindow(ga.shape[::-1], cv2.CV_32F)
            (dx, dy), r = cv2.phaseCorrelate(ga.astype(np.float32), gb.astype(np.float32), win)
            if r < 0.15: continue
            rows.append(dict(x=float(x0 + T / 2), z=float(z0 + T / 2), dx=float(dx * res), dz=float(dy * res), resp=float(r)))
    d = np.array([[r['dx'], r['dz']] for r in rows]); mag = np.hypot(*d.T)
    out = dict(n=len(rows), median=np.median(d, 0).tolist(), mean=d.mean(0).tolist(), std=d.std(0).tolist(),
               median_abs=float(np.median(mag)), p90=float(np.percentile(mag, 90)), max=float(mag.max()), tiles=rows)
    print(f"{len(rows)} ground tiles: 2024 - 2022 shift median ({out['median'][0]:+.2f}, {out['median'][1]:+.2f}) m, "
          f"std ({out['std'][0]:.2f}, {out['std'][1]:.2f}), |d| median {out['median_abs']:.2f} p90 {out['p90']:.2f} max {out['max']:.2f} m")
    json.dump(out, open(os.path.join(CACHE, 'naip_interyear.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
