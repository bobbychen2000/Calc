"""Shared helpers for the landside-building research tools (tools/buildings/landside_*.py).

Purpose: read the NAIP 2024 world raster (refs/cache/naip/naip_2024_world_0.5m_bgr.npy, frame ltp-nad83-2011,
0.5 m/px, x east / z south, metres from the ARP; transform in naip_2024_world_0.5m.json:
col = (x - x0)/res - 0.5, row = (z - z0)/res - 0.5), crop windows around the landside buildings, draw the SFO Museum
outlines (data/sfo_airport.json, CDLA-Permissive-1.0) and FAA DOF obstacles on them.

Outputs that contain NAIP pixels go to out/buildings/landside/ (local, gitignored). NAIP is public domain (USDA FPAC-BC
GEO, credit requested), but the owner's rule keeps imagery overlays out of the repo.
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as G  # noqa: E402

NAIP_DIR = os.path.join(ROOT, 'refs', 'cache', 'naip')
OUT = os.path.join(ROOT, 'out', 'buildings', 'landside')
CACHE = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'landside')
os.makedirs(OUT, exist_ok=True)

_T = json.load(open(os.path.join(NAIP_DIR, 'naip_2024_world_0.5m.json')))
X0, Z0, RES = _T['x0'], _T['z0'], _T['res']
_A = None


def naip():
    global _A
    if _A is None:
        _A = np.load(os.path.join(NAIP_DIR, 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r')
    return _A


def w2p(x, z):
    """world (x, z) -> fractional (col, row) of the full raster (pixel centres at integers)."""
    return (x - X0) / RES - 0.5, (z - Z0) / RES - 0.5


def crop(x0, z0, x1, z1, scale=1):
    """BGR crop of the world window [x0, x1] x [z0, z1] (metres); returns (img, fn world->img px)."""
    A = naip()
    c0, r0 = int(math.floor((x0 - X0) / RES)), int(math.floor((z0 - Z0) / RES))
    c1, r1 = int(math.ceil((x1 - X0) / RES)), int(math.ceil((z1 - Z0) / RES))
    img = np.zeros((r1 - r0, c1 - c0, 3), np.uint8)          # zero padding outside the raster
    rr0, cc0 = max(r0, 0), max(c0, 0)
    rr1, cc1 = min(r1, A.shape[0]), min(c1, A.shape[1])
    if rr1 > rr0 and cc1 > cc0:
        img[rr0 - r0:rr1 - r0, cc0 - c0:cc1 - c0] = A[rr0:rr1, cc0:cc1]
    if scale != 1:
        import cv2
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)

    def f(x, z):
        return (((x - X0) / RES - c0) * scale, ((z - Z0) / RES - r0) * scale)
    return img, f


def airport():
    return json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))


def structures(kind=None, name=None):
    out = []
    for s in airport()['structures']:
        if kind and s['kind'] != kind:
            continue
        if name and s['name'] != name:
            continue
        out.append(s)
    return out


def ring_area(r):
    a = 0.0
    for i in range(len(r)):
        x1, z1 = r[i - 1]; x2, z2 = r[i]
        a += x1 * z2 - x2 * z1
    return abs(a) / 2


def ring_perimeter(r):
    return sum(math.hypot(r[i][0] - r[i - 1][0], r[i][1] - r[i - 1][1]) for i in range(len(r)))


def dof():
    """FAA DOF (DAILY_DOF_CSV extract within 4.5 km of the ARP, refs/cache/lighting/dof_sfo_4500m.json) with world x, z
    recomputed in the current frame (the extract's own x/z columns may be in the legacy frame). The DOF horizontal datum
    is WGS 84 (DOF_README: "WGS 84 is used as the horizontal datum for all DOF data"), hence wgs84_to_world.
    Accuracy codes (DOF_README): 1A = +-20 ft horizontal, +-3 ft vertical; 4D = +-250 ft, +-50 ft."""
    rows = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'lighting', 'dof_sfo_4500m.json')))
    for o in rows:
        o['x'], o['z'] = G.wgs84_to_world(float(o['LATDEC']), float(o['LONDEC']))
    return rows


def min_rect(pts):
    """Minimum-area bounding rectangle of 2-D points: (cx, cz, length, width, angle_deg of the long side, world
    heading convention: 0 = north (-z), clockwise)."""
    import cv2
    p = np.asarray(pts, np.float32)
    (cx, cz), (w, h), a = cv2.minAreaRect(p)
    box = cv2.boxPoints(((cx, cz), (w, h), a))
    e = [box[1] - box[0], box[2] - box[1]]
    L = [float(np.hypot(*v)) for v in e]
    i = 0 if L[0] >= L[1] else 1
    v = e[i]
    hdg = math.degrees(math.atan2(v[0], -v[1])) % 180.0
    return float(cx), float(cz), max(L), min(L), hdg


def st(x, z):
    return G.world_to_st(x, z)


def sample(X, Z):
    """Bilinear NAIP sample (BGR float) at world arrays X, Z (same shape)."""
    import cv2
    A = naip()
    col = ((np.asarray(X) - X0) / RES - 0.5).astype(np.float32)
    row = ((np.asarray(Z) - Z0) / RES - 0.5).astype(np.float32)
    r0, c0 = int(np.floor(row.min())) - 2, int(np.floor(col.min())) - 2
    r1, c1 = int(np.ceil(row.max())) + 3, int(np.ceil(col.max())) + 3
    sub = np.ascontiguousarray(A[r0:r1, c0:c1]).astype(np.float32)
    return cv2.remap(sub, col - c0, row - r0, cv2.INTER_LINEAR)


def edge_profile(p0, p1, out_dir, d0=-15.0, d1=25.0, step=0.25, n_along=60, trim=0.1):
    """Mean luminance profile across the straight edge p0->p1 (world x, z).
    out_dir = +1: the profile coordinate d grows along the edge normal rotated +90 deg from p0->p1 in (x, z)
    (i.e. n = (-dz, dx)/L), -1 the opposite. Returns (d array, mean luminance, 25th pct, 75th pct).
    Luminance = 0.114 B + 0.587 G + 0.299 R (Rec. 601) of the NAIP RGB bands."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    t = p1 - p0; L = np.hypot(*t); t /= L
    n = np.array([-t[1], t[0]]) * out_dir
    s = np.linspace(trim * L, (1 - trim) * L, n_along)
    d = np.arange(d0, d1 + 1e-9, step)
    P = p0[None, None, :] + s[:, None, None] * t[None, None, :] + d[None, :, None] * n[None, None, :]
    bgr = sample(P[..., 0], P[..., 1])
    lum = 0.114 * bgr[..., 0] + 0.587 * bgr[..., 1] + 0.299 * bgr[..., 2]
    return d, lum.mean(0), np.percentile(lum, 25, axis=0), np.percentile(lum, 75, axis=0), n
