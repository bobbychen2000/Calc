"""SFO ATCT - fit the cab-roof disc (seen from above) in each NAIP epoch: centre and diameter.

A circle seen from above keeps its size under relief displacement (to +-1.5 %: the camera is ~4.5 km above ground and
the roof ~67 m up), so the fitted diameter is a lean-independent measurement of the cab roof's outer edge. The fitted
centre is displaced by the lean of that epoch (docs/research/buildings_tower.md s.4).

Method: grey image on the world grid (0.1 m/px, from tower_naip_epochs.py); Sobel gradient; for every candidate centre
within +-4 m of a hand seed (0.1 m steps) and radius 5-12 m (0.05 m steps) score = mean of the *radial* gradient
component (outward, bright disc -> darker surround, sign chosen per epoch) sampled at 360 points on the circle, using
only the 60 % best-agreeing points (the cab glass crescent and shadows break parts of the rim). The best score wins;
a +-0.1 m / +-0.05 m refinement follows. The seeds are the visual positions of the disc in each crop.

Inputs : out/buildings/tower/naip_<year>_tower.png   (tower_naip_epochs.py)
Outputs: out/buildings/tower/roof_disc_fits.json, out/buildings/tower/roof_disc_<year>.jpg (fit overlay, local)
usage  : python3 tools/buildings/tower_roof_disc.py
"""
import json, os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'out', 'buildings', 'tower')
X0, Z0, RES = -800.0, 250.0, 0.1          # window of tower_naip_epochs.py (WIN x0, z0) and its resolution
# hand seeds (world x, z) read off the 5 m grid crops naip_<year>_tower_grid.jpg
SEEDS = {'2016': (-750.0, 324.5), '2018': (-750.5, 325.0), '2022': (-698.5, 322.8), '2024': (-700.0, 322.5)}


def fit(gray, seed, rmin=5.0, rmax=12.0):
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), 3)       # 0.3 m blur (NAIP GSD 0.6 m)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gz = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    th = np.linspace(0, 2 * np.pi, 360, endpoint=False); ct, st = np.cos(th), np.sin(th)

    def score(cx, cz, r):
        px = (cx + r * ct - X0) / RES - 0.5; pz = (cz + r * st - Z0) / RES - 0.5
        sx = cv2.remap(gx, px.astype(np.float32)[None], pz.astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        sz = cv2.remap(gz, px.astype(np.float32)[None], pz.astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        rad = -(sx * ct + sz * st)                                   # bright inside -> positive
        k = int(0.6 * len(rad)); return float(np.mean(np.sort(rad)[-k:]))

    best = (-1e9, None)
    for cx in np.arange(seed[0] - 4, seed[0] + 4.01, 0.25):
        for cz in np.arange(seed[1] - 4, seed[1] + 4.01, 0.25):
            for r in np.arange(rmin, rmax + 0.01, 0.25):
                s = score(cx, cz, r)
                if s > best[0]: best = (s, (cx, cz, r))
    cx0, cz0, r0 = best[1]
    for cx in np.arange(cx0 - 0.3, cx0 + 0.31, 0.05):
        for cz in np.arange(cz0 - 0.3, cz0 + 0.31, 0.05):
            for r in np.arange(r0 - 0.3, r0 + 0.31, 0.05):
                s = score(cx, cz, r)
                if s > best[0]: best = (s, (cx, cz, r))
    # radius profile at the best centre (score vs r) -> second rim (inner ring) candidates
    cx, cz, r = best[1]
    prof = [(round(rr, 2), round(score(cx, cz, rr), 1)) for rr in np.arange(3.0, 12.01, 0.25)]
    return dict(cx=round(cx, 2), cz=round(cz, 2), r=round(r, 2), d=round(2 * r, 2), score=round(best[0], 1)), prof


def main():
    res = {}
    for year, seed in SEEDS.items():
        p = os.path.join(OUT, f'naip_{year}_tower.png')
        if not os.path.exists(p): continue
        im = cv2.imread(p); gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        f, prof = fit(gray, seed)
        f['radius_profile'] = prof
        res[year] = f
        th = np.linspace(0, 2 * np.pi, 720)
        pts = np.stack([(f['cx'] + f['r'] * np.cos(th) - X0) / RES, (f['cz'] + f['r'] * np.sin(th) - Z0) / RES], -1)
        cv2.polylines(im, [pts.astype(np.int32)], True, (0, 0, 255), 1)
        c = ((f['cx'] - X0) / RES, (f['cz'] - Z0) / RES)
        cv2.drawMarker(im, (int(c[0]), int(c[1])), (0, 0, 255), cv2.MARKER_CROSS, 20, 1)
        x0, y0 = int(c[0] - 150), int(c[1] - 150)
        crop = im[max(0, y0):y0 + 300, max(0, x0):x0 + 300]
        cv2.imwrite(os.path.join(OUT, f'roof_disc_{year}.jpg'), cv2.resize(crop, (600, 600), interpolation=cv2.INTER_CUBIC))
        print(year, {k: v for k, v in f.items() if k != 'radius_profile'})
    json.dump(dict(method=__doc__.split('\n\n')[2], window=dict(x0=X0, z0=Z0, res=RES), seeds=SEEDS, fits=res),
              open(os.path.join(OUT, 'roof_disc_fits.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
