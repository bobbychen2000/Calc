"""Pavement classifier for QA: Umbra overview (+3.0 m E registration, 5 m median) and S2 NDVI (both scenes)."""
import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_img import umbra, s2
from scipy.ndimage import median_filter
U = umbra((3.0, 0.0))
B = {sc: (s2(sc, 'B04'), s2(sc, 'B08')) for sc in ('S2B', 'S2C')}
def umb_med(X, Z, r=2.5):
    # 5x5 m neighbourhood median via offsets
    offs = [(dx, dz) for dx in (-r, -r/2, 0, r/2, r) for dz in (-r, -r/2, 0, r/2, r)]
    vals = np.stack([U.sample(np.asarray(X) + dx, np.asarray(Z) + dz) for dx, dz in offs])
    return np.nanmedian(vals, axis=0)
def ndvi(sc, X, Z):
    b4, b8 = B[sc]; a = b4.sample(X, Z); b = b8.sample(X, Z); return (b - a) / (b + a)
def thresholds(A):
    # pavement: runway centre zones; grass: the strip between the runways away from taxiways (x between rwys, sampled), 
    rw = A['runways']
    P = []; G = []
    for r in rw:
        c = np.array(r['centreline']['pts']); 
        for t in np.linspace(0.1, 0.9, 200):
            p = c[0] + t * (c[1] - c[0]); P.append(p)
    P = np.array(P)
    # grass samples: midway between the two runways shifted +-60 m (B runs at mid?) - use 120 m east of 18R/36L centreline
    c = np.array(rw[1]['centreline']['pts'])
    for off in (110, 130, -120, -140):
        for t in np.linspace(0.1, 0.9, 200):
            p = c[0] + t * (c[1] - c[0]); G.append(p + np.array([off, 0]))
    G = np.array(G)
    up = umb_med(P[:, 0], P[:, 1]); ug = umb_med(G[:, 0], G[:, 1])
    res = {'umb_pave_med': float(np.nanmedian(up)), 'umb_grass_med': float(np.nanmedian(ug)),
           'umb_pave_p95': float(np.nanpercentile(up, 95)), 'umb_grass_p05': float(np.nanpercentile(ug, 5))}
    for sc in ('S2B', 'S2C'):
        npv = ndvi(sc, P[:, 0], P[:, 1]); ng = ndvi(sc, G[:, 0], G[:, 1])
        res[sc] = (float(np.nanmedian(npv)), float(np.nanmedian(ng)), float(np.nanpercentile(npv, 95)), float(np.nanpercentile(ng, 5)))
    return res
if __name__ == '__main__':
    A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
    print(thresholds(A))
