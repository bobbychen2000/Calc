"""Register a listing photo into the video's SfM frame S with learned matches (DISK + LightGlue), guided.

    python3 -I tools/lg_reg.py TARGET FRAME_MS[,FRAME_MS..] [--init LANDMARKS.json] [--iters 3] [--save]
                               [--mode warp|direct|synth] [--free f,k1] [--f F]

TARGET is a path under refs/cache (photos/p29_ddf5dc.jpg).  The photos differ from the video in season, light and
heading (the aerial is winter and turned ~150 deg), which a matcher does not bridge on its own; so the target is first
WARPED into each SfM frame's view by a homography -- from the hand-picked landmarks for the first pass (--init: pairs
target <-> one frame on one plane), afterwards from the SfM points through the current camera -- and matched there.
The frame's pixels take their 3-D position from the SfM points that project near them (tools/sfm_pt: the front-most
cluster), so every match is a 2-D (target) <-> 3-D (S) pair; the camera (pose, f, k1) is a robust fit to them.
--save writes the camera into refs/cache/cams_fixed.json (register.py then treats it as fixed) and the inlier pairs to
refs/cache/lg_pairs/<name>.npz.
"""
import json
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tools import cams as CAMS  # noqa: E402
from tools import lg_match as LG  # noqa: E402

CACHE = os.path.join(HERE, 'refs', 'cache')
FR = 'frames_all/frames/frame_%06dms.jpg'
MASK_FRAME = [(0.0, 0.88, 1.0, 1.0), (0.95, 0.0, 1.0, 0.10), (0.80, 0.86, 1.0, 1.0), (0.0, 0.88, 0.05, 1.0)]


def feats(img, max_side, mask=None, n=4096):
    """DISK features of an RGB array (LG.features works on paths)."""
    import kornia as K
    import torch
    h, w = img.shape[:2]
    s = min(1.0, max_side / max(h, w))
    im = cv2.resize(img, (int(w * s) // 16 * 16, int(h * s) // 16 * 16), interpolation=cv2.INTER_AREA)
    sx, sy = w / im.shape[1], h / im.shape[0]
    t = K.image_to_tensor(np.ascontiguousarray(im), False).float() / 255.0
    with torch.inference_mode():
        f = LG._models()['disk'](t, n, pad_if_not_divisible=True)[0]
    kp = f.keypoints.numpy() * [sx, sy]
    keep = np.ones(len(kp), bool)
    if mask is not None:
        keep &= mask[np.clip(kp[:, 1].astype(int), 0, h - 1), np.clip(kp[:, 0].astype(int), 0, w - 1)] > 0
    return dict(kp=kp[keep], desc=f.descriptors[torch.from_numpy(keep)], size=(w, h), scale=(sx, sy))


class SfM:
    def __init__(self):
        self.cams = CAMS.load(os.path.join(CACHE, 'cams_sfm.json'))
        self.P = np.load(os.path.join(CACHE, 'sfm_points_S.npz'))['P'].astype(float)
        self._vis = {}

    def visible(self, frame):
        """SfM points seen by a frame: their pixels and depths, front-most per 3 px cell (no see-through)."""
        if frame not in self._vis:
            cam = self.cams[frame]
            uv, z = CAMS.project(cam, self.P, depth=True)
            ok = (z > 0) & (uv[:, 0] >= 0) & (uv[:, 0] < cam['w']) & (uv[:, 1] >= 0) & (uv[:, 1] < cam['h'])
            idx = np.nonzero(ok)[0]
            cell = (uv[idx] // 3).astype(int)
            key = cell[:, 0] * 10000 + cell[:, 1]
            order = np.lexsort((z[idx], key))
            k2 = key[order]
            first = np.r_[True, k2[1:] != k2[:-1]]
            zmin = np.repeat(z[idx][order][first], np.diff(np.r_[np.nonzero(first)[0], len(k2)]))
            front = z[idx][order] < zmin * 1.04 + 0.01
            sel = idx[order][front]
            self._vis[frame] = (sel, uv[sel], z[sel], cKDTree(uv[sel]))
        return self._vis[frame]

    def lift(self, frame, uv, r=12.0, kmin=5, tol=0.03):
        """3-D points for frame pixels: inverse depth fitted as a plane in (u, v) over the front-most SfM points within
        r px (exact for a planar patch, so close oblique ground works), laid along the pixel's ray.  NaN where fewer
        than kmin points remain or the fit misses them by > tol (relative): a depth edge, foliage."""
        sel, puv, pz, tree = self.visible(frame)
        cam = self.cams[frame]
        o, d = CAMS.ray(cam, uv)
        dz = d @ cam['R'][2]
        out = np.full((len(uv), 3), np.nan)
        for i, nb in enumerate(tree.query_ball_point(uv, r)):
            if len(nb) < kmin:
                continue
            nb = np.array(nb)
            iz = 1.0 / pz[nb]
            keep = iz > iz.max() * 0.80                      # the front-most surface (within 25 % in depth)
            for _ in range(3):
                if keep.sum() < kmin:
                    break
                A = np.c_[puv[nb][keep] - uv[i], np.ones(keep.sum())]
                coef, *_ = np.linalg.lstsq(A, iz[keep], rcond=None)
                res = np.abs(np.c_[puv[nb] - uv[i], np.ones(len(nb))] @ coef - iz) / iz
                keep = keep & (res < 2.5 * max(np.median(res[keep]), 0.004))
            if keep.sum() < kmin or coef[2] <= 0:
                continue
            res = np.abs(np.c_[puv[nb][keep] - uv[i], np.ones(keep.sum())] @ coef - iz[keep]) / iz[keep]
            if np.sqrt(np.mean(res ** 2)) < tol:
                out[i] = o + d[i] * ((1.0 / coef[2]) / dz[i])
        return out


    def depth_map(self, frame, r=14.0):
        """Dense depth of a frame from its SfM points (linear interpolation of the front-most points, NaN where the
        nearest point is farther than r px or neighbours disagree: sky, depth edges)."""
        from scipy.interpolate import LinearNDInterpolator
        sel, puv, pz, tree = self.visible(frame)
        cam = self.cams[frame]
        h, w = cam['h'], cam['w']
        gu, gv = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
        g = np.c_[gu.ravel(), gv.ravel()]
        D = LinearNDInterpolator(puv, pz)(g)
        dist, _ = tree.query(g)
        D[dist > r] = np.nan
        return D.reshape(h, w)


def h_from_landmarks(path, target, frame):
    d = json.load(open(os.path.join(HERE, path)))
    a, b = [], []
    for k, v in d.items():
        if isinstance(v, dict) and target in v.get('obs', {}) and frame in v['obs']:
            a.append(v['obs'][target])
            b.append(v['obs'][frame])
    H, _ = cv2.findHomography(np.float32(a), np.float32(b), 0)
    return H


def h_from_camera(sfm, cam, frame):
    """Target -> frame homography from the SfM points the frame sees, through the target's current camera."""
    sel, puv, pz, _ = sfm.visible(frame)
    tuv, tz = CAMS.project(cam, sfm.P[sel], depth=True)
    ok = (tz > 0) & (tuv[:, 0] > -200) & (tuv[:, 0] < cam['w'] + 200) & (tuv[:, 1] > -200) & (tuv[:, 1] < cam['h'] + 200)
    if ok.sum() < 30:
        return None
    H, inl = cv2.findHomography(tuv[ok].astype(np.float32), puv[ok].astype(np.float32), cv2.RANSAC, 25.0)
    return H


def match_frame(sfm, timg, frame, H, up=1):
    """Matches target <-> frame through the warp H (target -> frame px), the frame upsampled x up."""
    fimg = cv2.imread(os.path.join(CACHE, frame))[:, :, ::-1]
    fh, fw = fimg.shape[:2]
    S = np.diag([up, up, 1.0])
    W = cv2.warpPerspective(timg, S @ H, (fw * up, fh * up), flags=cv2.INTER_AREA,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    valid = cv2.warpPerspective(np.full(timg.shape[:2], 255, np.uint8), S @ H, (fw * up, fh * up), flags=cv2.INTER_NEAREST)
    valid = cv2.erode(valid, np.ones((9, 9), np.uint8))
    F2 = cv2.resize(fimg, (fw * up, fh * up), interpolation=cv2.INTER_CUBIC)
    fm = np.full((fh * up, fw * up), 255, np.uint8)
    for x0, y0, x1, y1 in MASK_FRAME:
        fm[int(y0 * fh * up):int(y1 * fh * up), int(x0 * fw * up):int(x1 * fw * up)] = 0
    fa = feats(W, 2800, valid, n=8192)
    fb = feats(np.ascontiguousarray(F2), 2800, fm, n=8192)
    pa, pb, _ = LG.match(fa, fb)
    if len(pa) < 8:
        return np.zeros((0, 2)), np.zeros((0, 2))
    pb = pb / up
    pw = pa / up
    # the warped pixels back to the target
    Hi = np.linalg.inv(H)
    q = np.c_[pw, np.ones(len(pw))] @ Hi.T
    pt = q[:, :2] / q[:, 2:]
    # geometric check in the warped view (near a homography there, so F is well conditioned on the 3-D scene)
    Fm, inl = cv2.findFundamentalMat(pw.astype(np.float32), pb.astype(np.float32), cv2.USAC_MAGSAC, 1.5, 0.999, 10000)
    inl = inl.ravel() > 0 if inl is not None else np.zeros(len(pw), bool)
    inl &= np.linalg.norm(pw - pb, axis=1) < 0.08 * max(fw, fh)      # the warp is close: no far jumps
    return pt[inl], pb[inl]


def match_synth(sfm, timg, frame, cam):
    """Matches target <-> frame through a synthetic view: the target re-rendered from the frame's viewpoint over the
    frame's SfM depth.  Returns target pixels (via the synthetic pixel's own 3-D point and the current camera) and the
    frame pixels they match."""
    fc = sfm.cams[frame]
    D = sfm.depth_map(frame)
    h, w = D.shape
    gu, gv = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    o, d = CAMS.ray(fc, np.c_[gu.ravel(), gv.ravel()])
    X = o + d * (D.ravel() / (d @ fc['R'][2]))[:, None]
    ok = np.isfinite(X[:, 0])
    tuv = np.full((len(X), 2), -1.0)
    tuv[ok] = CAMS.project(cam, X[ok])
    th, tw = timg.shape[:2]
    inside = ok & (tuv[:, 0] >= 0) & (tuv[:, 0] < tw - 1) & (tuv[:, 1] >= 0) & (tuv[:, 1] < th - 1)
    if inside.sum() < 2000:
        return np.zeros((0, 2)), np.zeros((0, 2))
    mx = tuv[:, 0].reshape(h, w).astype(np.float32)
    my = tuv[:, 1].reshape(h, w).astype(np.float32)
    syn = cv2.remap(timg, mx, my, cv2.INTER_AREA if False else cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    valid = cv2.erode(inside.reshape(h, w).astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
    fimg = cv2.imread(os.path.join(CACHE, frame))[:, :, ::-1]
    fm = np.full((h, w), 255, np.uint8)
    for x0, y0, x1, y1 in MASK_FRAME:
        fm[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 0
    fa = feats(np.ascontiguousarray(syn), 2800, valid, n=8192)
    fb = feats(np.ascontiguousarray(fimg), 2800, fm, n=8192)
    pa, pb, _ = LG.match(fa, fb)
    if len(pa) < 8:
        return np.zeros((0, 2)), np.zeros((0, 2))
    keep = np.linalg.norm(pa - pb, axis=1) < 0.06 * w
    Fm, inl = cv2.findFundamentalMat(pa.astype(np.float32), pb.astype(np.float32), cv2.USAC_MAGSAC, 1.5, 0.999, 10000)
    if inl is not None:
        keep &= inl.ravel() > 0
    pa, pb = pa[keep], pb[keep]
    if len(pa) == 0:
        return np.zeros((0, 2)), np.zeros((0, 2))
    # target pixel of each synthetic match: bilinear in the map
    pt = np.c_[cv2.remap(mx, pa[:, 0:1].astype(np.float32) - 0.5, pa[:, 1:2].astype(np.float32) - 0.5,
                         cv2.INTER_LINEAR).ravel(),
               cv2.remap(my, pa[:, 0:1].astype(np.float32) - 0.5, pa[:, 1:2].astype(np.float32) - 0.5,
                         cv2.INTER_LINEAR).ravel()]
    good = (pt[:, 0] > 0) & (pt[:, 1] > 0)
    if '--dump' in sys.argv:
        cv2.imwrite(os.path.join(CACHE, 'lg_pairs', 'syn_' + os.path.basename(frame)), np.vstack([syn, fimg])[:, :, ::-1])
    return pt[good], pb[good]


def match_direct(sfm, timg, frame, max_side=1600):
    """Plain matches target <-> frame (views alike: the drone orbit vs the high oblique photo)."""
    fimg = cv2.imread(os.path.join(CACHE, frame))[:, :, ::-1]
    h, w = fimg.shape[:2]
    fm = np.full((h, w), 255, np.uint8)
    for x0, y0, x1, y1 in MASK_FRAME:
        fm[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 0
    fa = feats(timg, max_side, None, n=8192)
    fb = feats(np.ascontiguousarray(fimg), 2800, fm, n=8192)
    pa, pb, inl = LG.match(fa, fb)
    return pa[inl], pb[inl]


def fit_camera(uv, X, w, h, cam0=None, free=('f', 'k1'), f0=None):
    """Robust camera from 2-D <-> 3-D pairs: PnP RANSAC over a focal grid, then refine (pose, f, k1)."""
    best = None
    fs = [cam0['f']] if cam0 is not None else ([f0] if f0 else list(np.geomspace(0.5, 3.0, 14) * max(w, h)))
    for f in fs:
        K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
        ok, rv, tv, inl = cv2.solvePnPRansac(X.astype(np.float64), uv.astype(np.float64), K, None,
                                             reprojectionError=max(4.0, 0.003 * w), iterationsCount=5000,
                                             flags=cv2.SOLVEPNP_EPNP)
        if ok and inl is not None and (best is None or len(inl) > best[0]):
            best = (len(inl), f, rv, tv, inl.ravel())
    n, f, rv, tv, inl = best
    R = cv2.Rodrigues(rv)[0]
    cam = CAMS.make(w, h, f, R, -R.T @ tv.ravel())
    pairs = [(*X[i], *uv[i]) for i in range(len(uv))]
    keep = np.zeros(len(uv), bool)
    keep[inl] = True
    for thr in (12.0, 6.0, 4.0, 3.0):
        cam, _ = CAMS.refine(cam, [pairs[i] for i in np.nonzero(keep)[0]], free=free, f_scale=2.0)
        err = np.linalg.norm(CAMS.project(cam, X) - uv, axis=1)
        keep = err < thr * w / 2500
    err = np.linalg.norm(CAMS.project(cam, X) - uv, axis=1)
    return cam, keep, err


def main():
    args = sys.argv[1:]
    target = args[0]
    frames = [FR % int(m) for m in args[1].split(',')]
    init = args[args.index('--init') + 1] if '--init' in args else None
    iters = int(args[args.index('--iters') + 1]) if '--iters' in args else 3
    mode = args[args.index('--mode') + 1] if '--mode' in args else 'warp'
    free = tuple(args[args.index('--free') + 1].split(',')) if '--free' in args else ('f',)
    free = tuple(x for x in free if x)
    f0 = float(args[args.index('--f') + 1]) if '--f' in args else None
    timg = cv2.imread(os.path.join(CACHE, target))[:, :, ::-1].copy()
    h, w = timg.shape[:2]
    sfm = SfM()
    fixed = CAMS.load(os.path.join(CACHE, 'cams_fixed.json'))
    cam = fixed.get(target)
    for it in range(iters):
        U, X, src = [], [], []
        for fr in frames:
            if fr not in sfm.cams:
                print('  %s: not in the SfM model' % fr.split('/')[-1])
                continue
            if mode == 'direct':
                pt, pf = match_direct(sfm, timg, fr)
                H = 'direct'
            elif cam is None:
                if init is None:
                    raise SystemExit('no camera yet for %s: give --init LANDMARKS.json' % target)
                try:
                    H = h_from_landmarks(init, target, fr)
                except Exception:
                    H = None
            else:
                H = h_from_camera(sfm, cam, fr) if mode == 'warp' else 'synth'
            if H is None:
                print('  %s: no warp' % fr.split('/')[-1])
                continue
            if isinstance(H, str):
                if H == 'synth':
                    pt, pf = match_synth(sfm, timg, fr, cam)
            else:
                pt, pf = match_frame(sfm, timg, fr, H)
            P3 = sfm.lift(fr, pf)
            ok = np.isfinite(P3[:, 0]) & (pt[:, 0] >= 0) & (pt[:, 0] < w) & (pt[:, 1] >= 0) & (pt[:, 1] < h)
            print('  %s: %d matches, %d with 3-D' % (fr.split('/')[-1], len(pt), ok.sum()))
            U.append(pt[ok])
            X.append(P3[ok])
            src += [fr] * int(ok.sum())
        U, X = np.vstack(U), np.vstack(X)
        if len(U) < 12:
            raise SystemExit('too few pairs (%d)' % len(U))
        cam, keep, err = fit_camera(U, X, w, h, cam if it > 0 else None, free=free, f0=f0)
        fwd = cam['R'][2]
        print('iter %d: %d pairs, %d inliers, rms %.2f px (median %.2f); f %.0f k1 %.3f, C %s, fwd %s' % (
            it, len(U), keep.sum(), np.sqrt(np.mean(err[keep] ** 2)), np.median(err[keep]), cam['f'], cam['k1'],
            np.round(cam['C'], 3), np.round(fwd, 3)))
        src = np.array(src)
        for fr in frames:
            m = src == fr
            if m.any():
                print('    %-26s %4d / %4d inliers, median %.2f px' % (fr.split('/')[-1], (keep & m).sum(), m.sum(),
                                                                       np.median(err[m & keep]) if (keep & m).any() else -1))
    rms_k = np.sqrt(np.mean(err[keep] ** 2))
    if '--save' in args and (keep.sum() < 60 or rms_k > 3.0):
        print('NOT saved: %d inliers, rms %.2f px (needs >= 60 and < 3)' % (keep.sum(), rms_k))
    elif '--save' in args:
        fixed = CAMS.load(os.path.join(CACHE, 'cams_fixed.json'))
        fixed[target] = dict(cam, fixed=True, src='lg_reg %d pairs rms %.2f' % (keep.sum(), np.sqrt(np.mean(err[keep] ** 2))))
        CAMS.save(fixed, os.path.join(CACHE, 'cams_fixed.json'))
        os.makedirs(os.path.join(CACHE, 'lg_pairs'), exist_ok=True)
        np.savez_compressed(os.path.join(CACHE, 'lg_pairs', os.path.basename(target) + '.npz'), uv=U[keep], X=X[keep],
                            src=src[keep])
        print('saved', target)


if __name__ == '__main__':
    main()
