"""Bring a VGGT run (tools/vggt_run.py) into the world frame through the frames it shares with the SfM solve.

    python3 -I tools/vggt_align.py refs/cache/vggt/run1.npz

Prints how well VGGT's relative poses agree with SfM on the shared frames, the predicted cameras of the other
images (world metres; compared with the landmark solution where one exists) and writes
    refs/cache/vggt/<run>_cams.json     predicted cameras, world frame, original-pixel intrinsics (initial guesses)
    refs/cache/vggt/<run>_cloud.npz     dense points P (world, float32), colours, confidence, image index
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


def main(path):
    d = np.load(path, allow_pickle=True)
    names = [str(n) for n in d['names']]
    E, K, pad = d['extrinsic'], d['intrinsic'], d['pad']
    Rv = E[:, :, :3]
    Cv = np.einsum('nji,nj->ni', Rv, -E[:, :, 3])              # camera centres in the VGGT frame
    sfm = CAMS.load(os.path.join(CACHE, 'cams_sfm.json'))
    shared = [i for i, n in enumerate(names) if n in sfm]
    print('shared frames:', [names[i] for i in shared])
    # rotation VGGT -> S
    M = sum(sfm[names[i]]['R'].T @ Rv[i] for i in shared)
    U, _, Vt = np.linalg.svd(M)
    Rg = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    cs = np.array([sfm[names[i]]['C'] for i in shared])
    cv = Cv[shared] @ Rg.T
    a, b = cs - cs.mean(0), cv - cv.mean(0)
    s = float((a * b).sum() / (b * b).sum())
    t = cs.mean(0) - s * cv.mean(0)
    print('scale VGGT -> S: %.4f' % s)
    for i in shared:
        Rs = Rv[i] @ Rg.T
        dR = np.degrees(np.arccos(np.clip((np.trace(Rs @ sfm[names[i]]['R'].T) - 1) / 2, -1, 1)))
        dC = np.linalg.norm(s * Rg @ Cv[i] + t - sfm[names[i]]['C']) * frame.FRAME['scale']
        w, h, nw, nh, left, top = pad[i]
        f_orig = K[i, 0, 0] * w / nw
        print('  %-24s rotation off %.2f deg, centre off %.2f m, focal %.0f px (SfM %.0f)' % (
            names[i], dR, dC, f_orig, sfm[names[i]]['f']))
    known = frame.world_cams()
    out = {}
    print('predicted cameras (world metres):')
    for i, n in enumerate(names):
        w, h, nw, nh, left, top = [float(v) for v in pad[i]]
        cam_S = CAMS.make(w, h, K[i, 0, 0] * w / nw, Rv[i] @ Rg.T, s * Rg @ Cv[i] + t)
        cw = frame.cam_to_world(cam_S)
        out[n] = dict(w=int(w), h=int(h), f=cw['f'], R=np.round(cw['R'], 8).tolist(), C=np.round(cw['C'], 4).tolist())
        note = ''
        if n in known and n not in sfm:
            k = known[n]
            dR = np.degrees(np.arccos(np.clip((np.trace(cw['R'] @ k['R'].T) - 1) / 2, -1, 1)))
            note = '   [landmark solution: off %.1f deg, %.1f m, f %.0f]' % (dR, np.linalg.norm(cw['C'] - k['C']), k['f'])
        print('  %-24s %s%s' % (n, CAMS.describe(cw), note))
    base = os.path.splitext(path)[0]
    json.dump(out, open(base + '_cams.json', 'w'), indent=1)
    # dense cloud: VGGT world points -> S -> world
    WP, conf = d['world_points'], d['world_points_conf']
    P, col, cf, idx = [], [], [], []
    for i, n in enumerate(names):
        w, h, nw, nh, left, top = [int(v) for v in pad[i]]
        im = np.asarray(Image.open(os.path.join(CACHE, n)).convert('RGB').resize((nw, nh), Image.BICUBIC))
        sl = (slice(top, top + nh), slice(left, left + nw))
        p = WP[i][sl].reshape(-1, 3).astype(np.float64)
        p = frame.to_world(s * p @ Rg.T + t)
        P.append(p.astype(np.float32))
        col.append(im.reshape(-1, 3))
        cf.append(conf[i][sl].reshape(-1))
        idx.append(np.full(len(p), i, np.int16))
    np.savez_compressed(base + '_cloud.npz', P=np.vstack(P), col=np.vstack(col), conf=np.concatenate(cf),
                        idx=np.concatenate(idx), names=np.array(names))
    print('cloud', sum(len(p) for p in P), 'points ->', base + '_cloud.npz')


if __name__ == '__main__':
    main(sys.argv[1])
