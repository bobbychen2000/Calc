"""Learned feature matching (DISK + LightGlue, kornia, CPU) between two images: robust across seasons / lighting,
where SIFT fails (the winter aerial vs the spring video).

    python3 -I tools/lg_match.py IMG_A IMG_B [OUT.npz] [max_side]     # paths relative to refs/cache
Prints the match count and the fundamental-matrix inliers; OUT.npz holds the inlier pairs (original pixels).
"""
import os
import sys

import cv2
import numpy as np
import torch

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, 'refs', 'cache')
_M = {}


def _models():
    if not _M:
        import kornia.feature as KF
        torch.set_num_threads(4)
        _M['disk'] = KF.DISK.from_pretrained('depth').eval()
        _M['lg'] = KF.LightGlueMatcher('disk').eval()
    return _M


def features(path, max_side=1600, n=4096, mask=None):
    import kornia as K
    img = cv2.imread(os.path.join(CACHE, path))[:, :, ::-1].copy()
    h, w = img.shape[:2]
    s = min(1.0, max_side / max(h, w))
    im = cv2.resize(img, (int(w * s) // 16 * 16, int(h * s) // 16 * 16), interpolation=cv2.INTER_AREA)
    sx, sy = w / im.shape[1], h / im.shape[0]
    t = K.image_to_tensor(im, False).float() / 255.0
    with torch.inference_mode():
        f = _models()['disk'](t, n, pad_if_not_divisible=True)[0]
    kp = f.keypoints.numpy() * [sx, sy]
    keep = np.ones(len(kp), bool)
    if mask is not None:
        for x0, y0, x1, y1 in mask:
            keep &= ~((kp[:, 0] >= x0 * w) & (kp[:, 0] <= x1 * w) & (kp[:, 1] >= y0 * h) & (kp[:, 1] <= y1 * h))
    return dict(kp=kp[keep], desc=f.descriptors[torch.from_numpy(keep)], size=(w, h), scale=(sx, sy))


def _hw(f):
    """(h, w) of the image the keypoints were detected in (the resized one)."""
    return int(round(f['size'][1] / f['scale'][1])), int(round(f['size'][0] / f['scale'][0]))


def match(fa, fb):
    import kornia.feature as KF

    def lafs(f):
        kp = torch.from_numpy(f['kp'] / np.array(f['scale'])).float()[None]
        return KF.laf_from_center_scale_ori(kp, torch.ones(1, kp.shape[1], 1, 1))
    with torch.inference_mode():
        d, idx = _models()['lg'](fa['desc'], fb['desc'], lafs(fa), lafs(fb),
                                 hw1=torch.tensor(_hw(fa)), hw2=torch.tensor(_hw(fb)))
    idx = idx.numpy()
    pa, pb = fa['kp'][idx[:, 0]], fb['kp'][idx[:, 1]]
    if len(pa) < 8:
        return pa, pb, np.zeros(len(pa), bool)
    F, inl = cv2.findFundamentalMat(pa.astype(np.float32), pb.astype(np.float32), cv2.USAC_MAGSAC, 2.0, 0.999, 10000)
    return pa, pb, (inl.ravel() > 0) if inl is not None else np.zeros(len(pa), bool)


PLAYER = [(0.0, 0.86, 1.0, 1.0), (0.95, 0.0, 1.0, 0.12)]


def is_frame(p):
    return p.startswith('frames_all/')


if __name__ == '__main__':
    a, b = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    ms = int(sys.argv[4]) if len(sys.argv) > 4 else 1600
    fa = features(a, ms, mask=PLAYER if is_frame(a) else None)
    fb = features(b, ms, mask=PLAYER if is_frame(b) else None)
    pa, pb, inl = match(fa, fb)
    print('%s <-> %s: %d matches, %d fundamental inliers' % (a, b, len(pa), inl.sum()))
    if out:
        np.savez(out, a=pa[inl], b=pb[inl], names=np.array([a, b]))
