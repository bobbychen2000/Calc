"""SFO ATCT - relative heights from NAIP relief displacement between epochs (no ground truth needed).

Principle: in an orthophoto rectified to a terrain DEM, a point at height h above ground appears displaced by
k_e * h, where the vector k_e (m per m of height) depends on the epoch's flight geometry and varies slowly over the
scene (a ~5 km-wide swath flown ~4.5 km above ground). Between two epochs a and b, a feature at height h therefore
moves by (k_b - k_a) * h. Measuring that inter-epoch shift for the cab roof disc (height H) and for another roof
feature (height h) gives h / H = |shift_h| / |shift_H| (projected on the shift direction), independently of the
unknown k vectors. Ground features must show zero shift (control).

The shifts are measured by normalised cross-correlation of gradient-magnitude images of small patches on the world
grid (0.1 m/px, from tower_naip_epochs.py): a patch from epoch a is searched in epoch b within +-60 m.

Inputs : out/buildings/tower/naip_<year>_tower.png, out/buildings/tower/roof_disc_fits.json
Output : out/buildings/tower/lean_ratio.json (+ printed table)
usage  : python3 tools/buildings/tower_lean_ratio.py
"""
import json, os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'out', 'buildings', 'tower')
X0, Z0, RES = -800.0, 250.0, 0.1

# patches (world x0, x1, z0, z1) - chosen on the grid crops; each is a roof or ground area free of the tower itself
PATCHES = {
    'ground: roadway/curb W of the base building': (-797, -775, 330, 352),
    'ground: apron E of Terminal 2 connector': (-690, -665, 355, 385),
    'base building roof: garden planter + S parapet': (-762, -738, 338, 358),
    'base building roof: roof hatch area': (-745, -728, 328, 342),
    'Terminal 1 roof S of the base building': (-765, -735, 362, 392),
}
PAIRS = [('2016', '2024'), ('2018', '2024'), ('2016', '2022'), ('2018', '2022')]


def grad(img):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 3)
    return cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))


def shift(Ga, Gb, box, search=60.0):
    x0, x1, z0, z1 = box
    c0, c1 = int((x0 - X0) / RES), int((x1 - X0) / RES); r0, r1 = int((z0 - Z0) / RES), int((z1 - Z0) / RES)
    tpl = Ga[r0:r1, c0:c1]
    s = int(search / RES)
    R0, R1 = max(0, r0 - s), min(Gb.shape[0], r1 + s); C0, C1 = max(0, c0 - s), min(Gb.shape[1], c1 + s)
    res = cv2.matchTemplate(Gb[R0:R1, C0:C1], tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    # sub-pixel by parabola
    x, y = loc
    def sub(a, b, c): d = a - 2 * b + c; return 0.0 if abs(d) < 1e-9 else 0.5 * (a - c) / d
    dx = sub(res[y, x - 1], res[y, x], res[y, x + 1]) if 0 < x < res.shape[1] - 1 else 0
    dy = sub(res[y - 1, x], res[y, x], res[y + 1, x]) if 0 < y < res.shape[0] - 1 else 0
    return ((C0 + x + dx - c0) * RES, (R0 + y + dy - r0) * RES), float(mx)


def main():
    G = {y: grad(cv2.imread(os.path.join(OUT, f'naip_{y}_tower.png'))) for y in ('2016', '2018', '2022', '2024')}
    F = json.load(open(os.path.join(OUT, 'roof_disc_fits.json')))['fits']
    out = []
    for a, b in PAIRS:
        cab = np.array([F[b]['cx'] - F[a]['cx'], F[b]['cz'] - F[a]['cz']])
        u = cab / np.linalg.norm(cab)
        row = dict(pair=f'{a}->{b}', cab_shift=cab.round(2).tolist(), cab_shift_len=round(float(np.linalg.norm(cab)), 2),
                   patches={})
        for name, box in PATCHES.items():
            (dx, dz), q = shift(G[a], G[b], box)
            along = dx * u[0] + dz * u[1]
            row['patches'][name] = dict(shift=[round(dx, 2), round(dz, 2)], ncc=round(q, 3),
                                        along=round(along, 2), ratio_to_cab=round(along / np.linalg.norm(cab), 4))
        out.append(row)
        print(row['pair'], 'cab shift', row['cab_shift'], row['cab_shift_len'])
        for n, v in row['patches'].items(): print('   ', f'{n:48s}', v)
    json.dump(dict(principle=__doc__.split('\n\n')[1], patches=PATCHES, results=out),
              open(os.path.join(OUT, 'lean_ratio.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
