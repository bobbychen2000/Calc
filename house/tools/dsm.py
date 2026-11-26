"""A height map of the whole lot from the top-down photo: the multi-view network's dense depth for that image,
calibrated against the SfM points and landmarks seen in it, and unprojected through the REGISTERED aerial camera.

    python3 -I tools/dsm.py            -> refs/cache/dsm.npz (X, Y grids, Z, colour) + out/tmp/dsm_*.png

The network's depth is smooth and complete but only roughly scaled; SfM is exact but sparse (and blind behind the
house).  Fit  true_depth = d * (c0 + c1 u + c2 v) + c3  on the points both have, then every pixel of the aerial photo
gets a world position.  Use it for roof pitches / heights where no SfM point exists (rear roofs, cabana, yard levels,
tree heights); expect ~0.2-0.4 m of error away from the calibration points.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from tools import cams as CAMS  # noqa: E402

CACHE = os.path.join(HERE, 'refs', 'cache')
IMG = 'photos/p30_b7b282.jpg'


def main():
    d = np.load(os.path.join(CACHE, 'vggt', 'run1.npz'), allow_pickle=True)
    names = [str(n) for n in d['names']]
    i = names.index(IMG)
    w, h, nw, nh, left, top = [int(v) for v in d['pad'][i]]
    dep = d['depth'][i][top:top + nh, left:left + nw].astype(float)          # (nh, nw) network depth
    conf = d['depth_conf'][i][top:top + nh, left:left + nw]
    cam = frame.world_cams()[IMG]
    # calibration points: SfM cloud + solved landmarks, in world metres
    P = frame.to_world(np.load(os.path.join(CACHE, 'sfm_points_S.npz'))['P'].astype(float))
    L = json.load(open(os.path.join(CACHE, 'landmarks_S.json')))
    P = np.vstack([P] + [np.tile(frame.to_world(np.array(v)), (40, 1)) for v in L.values()])   # landmarks weigh more
    uv, z = CAMS.project(cam, P, depth=True)
    ok = (z > 5) & (uv[:, 0] > 2) & (uv[:, 0] < w - 3) & (uv[:, 1] > 2) & (uv[:, 1] < h - 3)
    uv, z = uv[ok], z[ok]
    us, vs = uv[:, 0] * nw / w, uv[:, 1] * nh / h
    dv = dep[np.clip(vs.astype(int), 0, nh - 1), np.clip(us.astype(int), 0, nw - 1)]
    un, vn = us / nw - 0.5, vs / nh - 0.5
    A = np.c_[dv, dv * un, dv * vn, np.ones(len(dv))]
    keep = np.ones(len(dv), bool)
    for _ in range(6):                                                       # robust: drop occlusion mismatches
        c = np.linalg.lstsq(A[keep], z[keep], rcond=None)[0]
        r = A @ c - z
        keep = np.abs(r) < max(0.25, 2.0 * np.median(np.abs(r[keep])))
    print('calibration: %d of %d points, depth = d * (%.4f %+.4f u %+.4f v) %+.3f, residual median %.3f m, p90 %.3f m' % (
        keep.sum(), len(dv), c[0], c[1], c[2], c[3], np.median(np.abs(r[keep])), np.percentile(np.abs(r[keep]), 90)))
    # every network pixel -> world point through the registered camera
    vv, uu = np.mgrid[0:nh, 0:nw]
    depth = dep * (c[0] + c[1] * ((uu + 0.5) / nw - 0.5) + c[2] * ((vv + 0.5) / nh - 0.5)) + c[3]
    pu, pv = (uu + 0.5) * w / nw, (vv + 0.5) * h / nh
    x = (pu - cam['cx']) / cam['f']
    y = (pv - cam['cy']) / cam['f']
    Xc = np.stack([x * depth, y * depth, depth], -1).reshape(-1, 3)
    W = Xc @ cam['R'] + cam['C']
    rgb = np.asarray(Image.open(os.path.join(CACHE, IMG)).convert('RGB').resize((nw, nh), Image.LANCZOS)).reshape(-1, 3)
    np.savez_compressed(os.path.join(CACHE, 'dsm.npz'), P=W.astype(np.float32), col=rgb, conf=conf.reshape(-1),
                        shape=np.array([nh, nw]), coef=c)
    # check against the calibration points and print level statistics
    Z = W[:, 2].reshape(nh, nw)
    print('height range %.2f .. %.2f m' % (np.percentile(Z, 1), np.percentile(Z, 99)))
    out = os.path.join(HERE, 'out', 'tmp')
    zn = np.clip((Z + 1.0) / 13.0, 0, 1)
    Image.fromarray((zn * 255).astype(np.uint8)).resize((nw * 3, nh * 3), Image.NEAREST).save(os.path.join(out, 'dsm_height.png'))
    gy, gx = np.gradient(Z)
    shade = np.clip(0.5 + 2.0 * (gx - gy), 0, 1)
    Image.fromarray((shade * 255).astype(np.uint8)).resize((nw * 3, nh * 3), Image.BICUBIC).save(os.path.join(out, 'dsm_shade.png'))


if __name__ == '__main__':
    main()
