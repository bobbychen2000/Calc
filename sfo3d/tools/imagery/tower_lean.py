"""Visual evidence of NAIP relief displacement: the SFO ATC tower (SFO Museum structure kind 'atc') in NAIP 2022 and
2024, colour, 0.2 m sampling, 10 m world grid (yellow every 50 m), SFO Museum 'atc' footprint in red.
The cab (round roof) appears ~38-40 m east of the base in both years (visual reading of the grid, +-3 m).
Writes refs/cache/naip/tower_lean.jpg.   usage: python3 tools/imagery/tower_lean.py
"""
import json, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def main():
    D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    atc = [s for s in D['structures'] if s['kind'] == 'atc'][0]; ring = np.array(atc['polys'][0][0])
    x0, z0, hw, r = -760.0, 300.0, 70.0, 0.2
    X, Z = np.meshgrid(np.arange(x0 - hw, x0 + hw, r) + r / 2, np.arange(z0 - hw, z0 + hw, r) + r / 2)
    tiles = []
    for yr in ('2022', '2024'):
        S = NaipSampler(yr)
        lat, lon = ll_geojs(X, Z); E, N = S.T.transform(lon, lat); cc, rr = S.inv * (E, N)
        im = cv2.remap(S.img, (np.asarray(cc) - 0.5).astype(np.float32), (np.asarray(rr) - 0.5).astype(np.float32),
                       cv2.INTER_LINEAR)[..., ::-1].copy()
        for g in np.arange(-hw, hw + 1, 10):
            p = int((g + hw) / r); col = (0, 255, 255) if g % 50 == 0 else (200, 200, 200)
            cv2.line(im, (p, 0), (p, im.shape[0]), col, 1); cv2.line(im, (0, p), (im.shape[1], p), col, 1)
        cv2.polylines(im, [np.round((ring - [x0 - hw, z0 - hw]) / r).astype(np.int32)], True, (0, 0, 255), 2)
        cv2.putText(im, f'NAIP {yr}: world x {x0 - hw:.0f}..{x0 + hw:.0f}, z {z0 - hw:.0f}..{z0 + hw:.0f}; grid 10 m', (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        tiles.append(im)
    cv2.imwrite(os.path.join(CACHE, 'tower_lean.jpg'), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 90])


if __name__ == '__main__':
    main()
