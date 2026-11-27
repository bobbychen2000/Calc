"""Pinhole cameras for the reference images: projection, fitting from landmarks, storage.

A camera is {w, h, f, cx, cy, k1, R (3x3 world->camera, OpenCV axes: x right, y down, z forward), C (centre, m)}
in the world frame of model/kit.py.  Fitted cameras live in refs/cache/cams.json, keyed by the image's path
relative to refs/cache (e.g. "photos/p26_08c1ce.jpg").

    from tools import cams
    cam = cams.load()['photos/p26_08c1ce.jpg']
    uv = cams.project(cam, XYZ)                 # (n, 2) pixels, + depth with depth=True
    o, d = cams.ray(cam, [[u, v]])              # world ray through a pixel
    P = cams.hit_plane(cam, [[u, v]], z=0.0)    # where that ray meets a horizontal plane (or x= / y=)
    cam, rms = cams.fit(pairs, w, h, f0=..)     # pairs: [(X, Y, Z, u, v), ...]
"""
from __future__ import annotations

import json
import os

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, 'refs', 'cache')
PATH = os.path.join(CACHE, 'cams.json')


def load(path=PATH):
    if not os.path.exists(path):
        return {}
    d = json.load(open(path))
    for c in d.values():
        c['R'] = np.array(c['R'], float)
        c['C'] = np.array(c['C'], float)
    return d


def save(cams, path=PATH):
    out = {}
    for k, c in cams.items():
        o = dict(c)
        o['R'] = np.asarray(c['R'], float).round(9).tolist()
        o['C'] = np.asarray(c['C'], float).round(5).tolist()
        out[k] = o
    json.dump(out, open(path, 'w'), indent=1, sort_keys=True)


def make(w, h, f, R, C, k1=0.0, cx=None, cy=None, **extra):
    c = dict(w=int(w), h=int(h), f=float(f), cx=float(w / 2 if cx is None else cx),
             cy=float(h / 2 if cy is None else cy), k1=float(k1), R=np.asarray(R, float), C=np.asarray(C, float))
    c.update(extra)
    return c


def project(cam, X, depth=False):
    X = np.asarray(X, float).reshape(-1, 3)
    Xc = (X - cam['C']) @ cam['R'].T
    z = Xc[:, 2]
    zs = np.where(np.abs(z) < 1e-9, 1e-9, z)
    x, y = Xc[:, 0] / zs, Xc[:, 1] / zs
    if cam.get('k1'):
        r2 = x * x + y * y
        x, y = x * (1 + cam['k1'] * r2), y * (1 + cam['k1'] * r2)
    uv = np.stack([cam['f'] * x + cam['cx'], cam['f'] * y + cam['cy']], -1)
    return (uv, z) if depth else uv


def ray(cam, uv):
    """World rays through pixels: (origin C, unit directions (n, 3))."""
    uv = np.asarray(uv, float).reshape(-1, 2)
    x = (uv[:, 0] - cam['cx']) / cam['f']
    y = (uv[:, 1] - cam['cy']) / cam['f']
    if cam.get('k1'):
        for _ in range(8):                      # undo the radial term
            r2 = x * x + y * y
            s = 1 + cam['k1'] * r2
            x = (uv[:, 0] - cam['cx']) / cam['f'] / s
            y = (uv[:, 1] - cam['cy']) / cam['f'] / s
    d = np.stack([x, y, np.ones_like(x)], -1) @ cam['R']
    return cam['C'], d / np.linalg.norm(d, axis=1, keepdims=True)


def hit_plane(cam, uv, x=None, y=None, z=None):
    """Intersect pixel rays with the axis plane x= / y= / z= (exactly one given)."""
    o, d = ray(cam, uv)
    ax, val = [(i, v) for i, v in enumerate((x, y, z)) if v is not None][0]
    t = (val - o[ax]) / d[:, ax]
    return o + t[:, None] * d


def triangulate(obs):
    """Least-squares point from several (cam, (u, v)) observations; returns (X, per-view pixel residuals)."""
    A, b = np.zeros((3, 3)), np.zeros(3)
    for cam, uv in obs:
        o, d = ray(cam, [uv])
        P = np.eye(3) - np.outer(d[0], d[0])
        A += P
        b += P @ o
    X = np.linalg.solve(A, b)
    res = [float(np.linalg.norm(project(cam, X)[0] - np.asarray(uv, float))) for cam, uv in obs]
    return X, res


def _pack(cam, free):
    r = Rotation.from_matrix(cam['R']).as_rotvec()
    p = list(r) + list(cam['C'])
    if 'f' in free:
        p.append(np.log(cam['f']))
    if 'k1' in free:
        p.append(cam['k1'])
    if 'c' in free:
        p += [cam['cx'], cam['cy']]
    return np.array(p, float)


def _unpack(p, cam, free):
    c = dict(cam)
    c['R'] = Rotation.from_rotvec(p[:3]).as_matrix()
    c['C'] = np.array(p[3:6])
    i = 6
    if 'f' in free:
        c['f'] = float(np.exp(p[i]))
        i += 1
    if 'k1' in free:
        c['k1'] = float(p[i])
        i += 1
    if 'c' in free:
        c['cx'], c['cy'] = float(p[i]), float(p[i + 1])
    return c


def refine(cam, pairs, free=('f',), weights=None, loss='soft_l1', f_scale=3.0, lines=()):
    """Non-linear refinement of a camera on landmark pairs [(X, Y, Z, u, v)].

    lines: [((X, Y, Z) a, (X, Y, Z) b, [(u, v), ...])]: image points that must lie on the projection of the
    world segment a-b (for edges whose end points are hidden or out of frame)."""
    P = np.asarray(pairs, float).reshape(-1, 5)
    w = np.ones(len(P)) if weights is None else np.asarray(weights, float)

    def resid(p):
        c = _unpack(p, cam, free)
        r = [((project(c, P[:, :3]) - P[:, 3:]) * w[:, None]).ravel()] if len(P) else []
        for a, b, pts in lines:
            ab = project(c, [a, b])
            d = ab[1] - ab[0]
            n = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-9)
            r.append((np.asarray(pts, float) - ab[0]) @ n)
        return np.concatenate(r)

    sol = least_squares(resid, _pack(cam, free), loss=loss, f_scale=f_scale, x_scale='jac')
    c = _unpack(sol.x, cam, free)
    r = resid(sol.x)
    return c, float(np.sqrt(np.mean(r ** 2)))


def fit(pairs, w, h, f0=None, free=('f',), tries=(0.6, 0.8, 1.0, 1.3, 1.8, 2.5), lines=()):
    """Camera from landmark pairs with no initial pose: EPnP at several focal guesses, then refine."""
    import cv2
    P = np.asarray(pairs, float).reshape(-1, 5)
    best = None
    for k in ([1.0] if f0 else tries):
        f = f0 or k * max(w, h)
        K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
        flag = cv2.SOLVEPNP_EPNP if len(P) >= 5 else cv2.SOLVEPNP_ITERATIVE
        ok, rvec, tvec = cv2.solvePnP(P[:, :3].copy(), P[:, 3:].copy(), K, None, flags=flag)
        if not ok:
            continue
        R = cv2.Rodrigues(rvec)[0]
        cam0 = make(w, h, f, R, -R.T @ tvec.ravel())
        try:
            cam, rms = refine(cam0, P, free=free, lines=lines)
        except Exception:
            continue
        if (project(cam, P[:, :3], depth=True)[1] > 0).all() and (best is None or rms < best[1]):
            best = (cam, rms)
    if best is None:
        raise RuntimeError('camera fit failed')
    return best


def describe(cam):
    """Human-readable pose: position, heading (deg from +Y toward +X), pitch (deg, + = looking up), hfov."""
    fwd = cam['R'][2]
    head = float(np.degrees(np.arctan2(fwd[0], fwd[1])))
    pitch = float(np.degrees(np.arcsin(np.clip(fwd[2], -1, 1))))
    hfov = float(np.degrees(2 * np.arctan(cam['w'] / 2 / cam['f'])))
    return 'C=(%.2f, %.2f, %.2f) heading %.1f pitch %.1f hfov %.1f f=%.0f' % (*cam['C'], head, pitch, hfov, cam['f'])
