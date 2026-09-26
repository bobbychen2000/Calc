"""Domestic terminals - median cross-profiles of straight, grid-aligned roof edges on the NAIP epochs, and sub-pixel
step picking. Used by dom_heights.py (see there for the height equations).

A face is dict(axis, at, a, b, out):
  axis='t' : the edge runs along t (faces ESE, out=+1, or WNW, out=-1); the profile coordinate is s
  axis='s' : the edge runs along s (faces NNE, out=+1, or SSW, out=-1); the profile coordinate is t
  at       : nominal edge coordinate (m); a, b: extent along the edge (m)
The profile is the per-column MEDIAN over all lines across the edge (0.1 m sampling, Gaussian sigma 0.15 m), which
rejects jet bridges, vehicles and aircraft that cover a minority of the edge length. Coordinates are returned in the
grid frame (s or t); `outward` distances are (coord - at) * out.
"""
import numpy as np
import cv2
import dom_common as C

RES = 0.1


def profile(year, face, half=25.0):
    at, a, b = face['at'], min(face['a'], face['b']), max(face['a'], face['b'])
    if face['axis'] == 't':
        img, (s0, t1, res) = C.crop_st(year, at - half, at + half, a, b, res=RES)
        G = cv2.GaussianBlur(C.gray(img), (0, 0), 1.5)
        coord = s0 + (np.arange(G.shape[1]) + 0.5) * res
        prof = np.median(G, axis=0); q25 = np.percentile(G, 25, axis=0); q75 = np.percentile(G, 75, axis=0)
    else:
        img, (s0, t1, res) = C.crop_st(year, a, b, at - half, at + half, res=RES)
        G = cv2.GaussianBlur(C.gray(img), (0, 0), 1.5)
        coord = t1 - (np.arange(G.shape[0]) + 0.5) * res
        prof = np.median(G, axis=1); q25 = np.percentile(G, 25, axis=1); q75 = np.percentile(G, 75, axis=1)
        coord, prof, q25, q75 = coord[::-1], prof[::-1], q25[::-1], q75[::-1]      # ascending t
    return coord, prof, q25, q75


def step(coord, prof, lo, hi, sign, plateau=1.0):
    """sub-pixel position of the strongest step of `sign` (+1 dark->bright, -1 bright->dark, with increasing coord)
    inside [lo, hi]: 50 % crossing between the mean levels `plateau` m before and after the steepest point."""
    m = (coord >= lo) & (coord <= hi)
    idx = np.where(m)[0]
    if len(idx) < 5: return None
    d = np.gradient(prof)
    j = idx[np.argmax(sign * d[idx])]
    n = int(plateau / RES)
    a = prof[max(0, j - n - 3):max(1, j - 3)].mean(); b = prof[j + 3:j + n + 3].mean()
    mid = 0.5 * (a + b)
    k0, k1 = max(0, j - n), min(len(prof) - 1, j + n)
    seg = prof[k0:k1 + 1]; cs = coord[k0:k1 + 1]
    for i in range(len(seg) - 1):
        if (seg[i] - mid) * (seg[i + 1] - mid) <= 0 and seg[i] != seg[i + 1]:
            f = (mid - seg[i]) / (seg[i + 1] - seg[i])
            return dict(pos=round(float(cs[i] + f * RES), 2), contrast=round(float(b - a), 1), grad=round(float(d[j]), 2))
    return dict(pos=round(float(coord[j]), 2), contrast=round(float(b - a), 1), grad=round(float(d[j]), 2))


def show(year, face, half=25.0, every=5):
    c, p, q25, q75 = profile(year, face, half)
    return ' '.join('%.1f:%d' % (c[j], p[j]) for j in range(0, len(c), every))


# ------------------------------------------------------------------------------------ edges of arbitrary direction
def edge_profile(year, p0, p1, half=25.0, res=RES):
    """median profile across the straight edge p0 -> p1 (world x, z). The profile coordinate u runs along the RIGHT-hand
    normal of p0->p1 in the (east, north) plane, i.e. n = (dz, -dx)/|d| ... expressed in world (x, z) as
    n = (-(z1 - z0), (x1 - x0)) / L rotated so that for p0->p1 heading h the normal heading is h + 90 deg.
    Returns (u, prof, n) with u in metres from the line (positive along n)."""
    img, m = C.epoch(year)
    x0, z0 = p0; x1, z1 = p1
    L = float(np.hypot(x1 - x0, z1 - z0)); d = np.array([(x1 - x0) / L, (z1 - z0) / L])
    # heading h of d: world vector (sin h, -cos h); normal at h + 90: (cos h, sin h) = (-d_z, d_x)
    n = np.array([-d[1], d[0]])
    v = np.arange(0, L, res) + res / 2
    u = np.arange(-half, half, res) + res / 2
    V, U = np.meshgrid(v, u)                      # rows = u, cols = v
    X = x0 + V * d[0] + U * n[0]; Z = z0 + V * d[1] + U * n[1]
    c, r = C.w2p(m, X, Z)
    G = cv2.remap(img, c.astype(np.float32), r.astype(np.float32), cv2.INTER_LINEAR)
    G = cv2.GaussianBlur(C.gray(G), (0, 0), 1.5)
    return u, np.median(G, axis=1), n


def heading(vec):
    """true heading (deg) of a world (x, z) vector."""
    return float(np.degrees(np.arctan2(vec[0], -vec[1])) % 360)


def show_edge(year, p0, p1, half=25.0, every=5):
    u, p, n = edge_profile(year, p0, p1, half)
    return 'n_hdg=%.1f ' % heading(n) + ' '.join('%.1f:%d' % (u[j], p[j]) for j in range(0, len(u), every))
