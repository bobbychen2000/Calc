"""The SfM drone model -> an upright, house-aligned (still unscaled) frame, with diagnostic plots.

    python3 -I tools/sfm_frame.py            # writes refs/cache/sfm/frame.json + out/tmp/sfm_top.png / sfm_front.png

Up: from the vanishing point of the house's vertical edges in several frames (both drone shots face almost the
same way, so 'the gimbal keeps the horizon level' alone leaves the pitch open).  Heading: the rotation about up
that makes the plan view of the points most axis-aligned (roof edges, walls, fences are parallel to the lot).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFM = os.path.join(HERE, 'refs', 'cache', 'sfm')


def load(model='1', skip=('v1_',)):
    import pycolmap
    r = pycolmap.Reconstruction(os.path.join(SFM, 'sparse', model))
    cams = {}
    for im in r.images.values():
        if im.name.split('/')[-2].startswith(skip):
            continue
        T = im.cam_from_world() if callable(im.cam_from_world) else im.cam_from_world
        R = np.asarray(T.rotation.matrix())
        t = np.asarray(T.translation)
        cam = r.cameras[im.camera_id]
        cams[im.name] = dict(R=R, C=-R.T @ t, f=float(cam.params[0]), cx=float(cam.params[1]), cy=float(cam.params[2]),
                             k1=float(cam.params[3]), w=cam.width, h=cam.height)
    keep_ids = {im.image_id for im in r.images.values() if not im.name.split('/')[-2].startswith(skip)}
    P, C, E, N = [], [], [], []
    for p in r.points3D.values():
        n = sum(1 for e in p.track.elements if e.image_id in keep_ids)
        if n >= 2:
            P.append(p.xyz)
            C.append(p.color)
            E.append(p.error)
            N.append(n)
    return cams, np.array(P), np.array(C), np.array(E), np.array(N)


def vertical_vp(path, f, cx, cy, k1=0.0):
    """Down direction in the camera frame from the vanishing point of the near-vertical line segments of a frame
    (columns, wall corners, window jambs).  Returns (unit vector with y > 0, inlier count, segment count)."""
    import cv2
    g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    h, w = g.shape
    g[int(0.60 * h):, :int(0.55 * w)] = cv2.blur(g, (31, 31))[int(0.60 * h):, :int(0.55 * w)]   # burnt-in titles
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    seg = lsd.detect(g)[0].reshape(-1, 4)
    d = seg[:, 2:] - seg[:, :2]
    L = np.linalg.norm(d, axis=1)
    ang = np.degrees(np.arctan2(np.abs(d[:, 0]), np.abs(d[:, 1])))        # 0 = image-vertical
    seg, L = seg[(L > 45) & (ang < 28)], L[(L > 45) & (ang < 28)]
    # homogeneous lines in normalised camera coordinates
    def norm(p):
        return np.stack([(p[:, 0] - cx) / f, (p[:, 1] - cy) / f, np.ones(len(p))], -1)
    a, b2 = norm(seg[:, :2]), norm(seg[:, 2:])
    lines = np.cross(a, b2)
    lines /= np.linalg.norm(lines[:, :2], axis=1, keepdims=True)
    mid = (a + b2) / 2
    rng = np.random.default_rng(0)
    best = (0, None)
    for _ in range(3000):
        i, j = rng.choice(len(lines), 2, replace=False, p=L / L.sum())
        v = np.cross(lines[i], lines[j])
        if np.linalg.norm(v) < 1e-9:
            continue
        v /= np.linalg.norm(v)
        # angle between each segment and the direction from its midpoint to the vanishing point
        dirv = v[None, :2] - mid[:, :2] * v[2]
        dirs = b2[:, :2] - a[:, :2]
        cosang = np.abs((dirv * dirs).sum(1)) / (np.linalg.norm(dirv, axis=1) * np.linalg.norm(dirs, axis=1) + 1e-12)
        inl = np.degrees(np.arccos(np.clip(cosang, 0, 1))) < 0.6
        score = L[inl].sum()
        if score > best[0]:
            best = (score, inl)
    inl = best[1]
    # least squares: the direction most orthogonal to the inlier lines' normals (weighted by length)
    A = lines[inl] * L[inl, None]
    v = np.linalg.svd(A)[2][-1]
    if v[1] < 0:
        v = -v
    return v / np.linalg.norm(v), int(inl.sum()), len(seg)


def upright(cams, P, frames=('seg002_033', 'seg002_039', 'seg002_045', 'seg002_051', 'seg141_033', 'seg141_039',
                             'seg141_045')):
    """Rotation sfm -> provisional upright axes (rows x', y', z' = up) and the spread of the up estimates (deg)."""
    ups = []
    for name, c in cams.items():
        if not name.split('/')[-1].startswith(frames):
            continue
        path = os.path.join(SFM, 'images', name)
        down, n_in, n = vertical_vp(path, c['f'], c['cx'], c['cy'])
        ups.append(-(down @ c['R']))
        print('   vertical VP %-40s inliers %3d / %3d' % (name, n_in, n))
    ups = np.array(ups)
    up = ups.mean(0)
    up /= np.linalg.norm(up)
    spread = float(np.degrees(np.arccos(np.clip(ups @ up, -1, 1))).max())
    # horizontal basis
    a = np.cross(up, [1, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(up, a)
    B = np.stack([a, b, up])               # rows: provisional x, y, z
    Q = P @ B.T
    # heading from the HOUSE only: the dense roof points (far neighbours pull an all-points histogram elsewhere)
    med = np.median(Q[:, :2], 0)
    near = np.linalg.norm(Q[:, :2] - med, axis=1) < 0.75 * np.percentile(np.linalg.norm(Q[:, :2] - med, axis=1), 60)
    zr = np.percentile(Q[near, 2], [55, 99.5])
    roof = Q[near & (Q[:, 2] > zr[0]) & (Q[:, 2] < zr[1])]
    best = None
    for ang in np.radians(np.arange(0, 90, 0.1)):
        c, s_ = np.cos(ang), np.sin(ang)
        x = roof[:, 0] * c + roof[:, 1] * s_
        y = -roof[:, 0] * s_ + roof[:, 1] * c
        score = 0.0
        for v in (x, y):
            h, _ = np.histogram(v, bins=300, range=np.percentile(v, [0.5, 99.5]))
            p = h / h.sum()
            score += (p * p).sum()         # peaky histograms = ridges / eaves / shingle rows line up with the axes
        if best is None or score > best[0]:
            best = (score, ang)
    fwd = np.mean([c['R'][2] for c in cams.values()], 0) @ B.T
    out = None
    for quarter in range(4):               # of the four axis-aligned frames take the one whose +Y is the view direction
        ang = best[1] + quarter * np.pi / 2
        c, s_ = np.cos(ang), np.sin(ang)
        Rz = np.array([[c, s_, 0], [-s_, c, 0], [0, 0, 1]])
        f = Rz @ fwd
        if out is None or f[1] > out[0]:
            out = (f[1], Rz)
    return out[1] @ B, spread


def plots(Q, col, out):
    from PIL import Image
    lo, hi = np.percentile(Q, 0.5, 0), np.percentile(Q, 99.5, 0)
    for name, (i, j, k) in {'top': (0, 1, 2), 'front': (0, 2, 1), 'side': (1, 2, 0)}.items():
        W = 1400
        s = W / (hi[i] - lo[i])
        H = int((hi[j] - lo[j]) * s) + 1
        img = np.full((H, W + 1, 3), 20, np.uint8)
        order = np.argsort(Q[:, k])
        u = ((Q[order, i] - lo[i]) * s).astype(int)
        v = (H - 1 - (Q[order, j] - lo[j]) * s).astype(int)
        ok = (u >= 0) & (u <= W) & (v >= 0) & (v < H)
        for du in (0, 1):
            for dv in (0, 1):
                uu, vv = np.clip(u[ok] + du, 0, W), np.clip(v[ok] + dv, 0, H - 1)
                img[vv, uu] = col[order][ok]
        Image.fromarray(img).save(os.path.join(out, 'sfm_%s.png' % name))


def main():
    cams, P, col, err, ntr = load()
    B, flat = upright(cams, P)
    Q = P @ B.T
    print('cameras', len(cams), 'points', len(P), 'up spread (deg)', round(flat, 2))
    rolls = [np.degrees(np.arcsin(c['R'][0] @ B[2])) for c in cams.values()]
    print('camera roll about the horizon (deg): mean %.2f, max |%.2f|' % (np.mean(rolls), np.max(np.abs(rolls))))
    for n in sorted(cams):
        if n.endswith(('_033.jpg', '_053.jpg', '_031.jpg', '_049.jpg')):
            c = cams[n]
            Cq = c['C'] @ B.T
            f = c['R'][2] @ B.T
            print('  %-40s C=%s fwd=%s pitch %.1f' % (n, np.round(Cq, 3).tolist(), np.round(f, 3).tolist(),
                                                      np.degrees(np.arcsin(f[2]))))
    print('aligned bbox 1/99 %:', np.percentile(Q, 1, 0).round(3).tolist(), np.percentile(Q, 99, 0).round(3).tolist())
    out = os.path.join(HERE, 'out', 'tmp')
    plots(Q, col, out)
    json.dump({'B': B.tolist()}, open(os.path.join(SFM, 'frame0.json'), 'w'))


if __name__ == '__main__':
    main()
