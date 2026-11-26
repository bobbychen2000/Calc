"""Register the reference images against the drone SfM model through hand-picked landmarks (a small bundle
adjustment), in the upright, lot-aligned SfM frame "S" (X right from the street, Y into the lot, Z up; arbitrary
scale and origin until tools/frame.py fixes them).

    python3 -I tools/register.py export     # SfM cameras -> refs/cache/cams_sfm.json (S frame)
    python3 -I tools/register.py solve      # survey/landmarks.json -> refs/cache/cams_S.json + landmarks_S.json + report
    python3 -I tools/register.py check IMG  # residual table for one image
    python3 -I tools/register.py where NAME # where a solved landmark should appear in the other registered images
    python3 -I tools/register.py mark IMG OUT.jpg [scale] [x0,y0,x1,y1]   # picks (yellow +) vs solved positions (cyan x)

survey/landmarks.json:  { "name": { "desc": "...", "obs": { "<image rel. to refs/cache>": [u, v], ... } }, ... }
Pixel coordinates are in ORIGINAL pixels of each image.  SfM frames (frames/seg002_033..053, seg141_031..049) are
fixed cameras; every other image gets a camera fitted (focal length free, principal point at the centre).
A landmark needs >= 2 observations to count; a new image needs >= 6 landmarks whose position is already known.
"""
import json
import os
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tools import cams as CAMS  # noqa: E402
from tools import sfm_frame  # noqa: E402

CACHE = os.path.join(HERE, 'refs', 'cache')
LM = os.path.join(HERE, 'survey', 'landmarks.json')


def export():
    cams, P, col, err, ntr = sfm_frame.load()
    B, _ = sfm_frame.upright(cams, P)
    A = B                                          # sfm -> S (X right, Y into the lot, Z up)
    out = {}
    for name, c in cams.items():
        key = 'frames/' + name.split('/')[-1]
        out[key] = CAMS.make(c['w'], c['h'], c['f'], c['R'] @ A.T, A @ c['C'], k1=c['k1'], cx=c['cx'], cy=c['cy'],
                             fixed=True)
    CAMS.save(out, os.path.join(CACHE, 'cams_sfm.json'))
    np.savez_compressed(os.path.join(CACHE, 'sfm_points_S.npz'), P=(P @ A.T).astype(np.float32), col=col, err=err,
                        ntr=ntr)
    print('exported', len(out), 'cameras,', len(P), 'points')
    for k in sorted(out)[::5]:
        print('  ', k, CAMS.describe(out[k]))


def _size(img):
    from PIL import Image
    return Image.open(os.path.join(CACHE, img)).size


def solve(verbose=True):
    fixed = CAMS.load(os.path.join(CACHE, 'cams_sfm.json'))
    lm = json.load(open(LM))
    lm = {k: v for k, v in lm.items() if not k.startswith('_')}
    cams = dict(fixed)
    X = {}
    for _ in range(6):                             # alternate: triangulate what can be, then fit new cameras
        for name, d in lm.items():
            obs = [(cams[i], uv) for i, uv in d['obs'].items() if i in cams]
            if len(obs) >= 2 and name not in X:
                X[name] = CAMS.triangulate(obs)[0]
        new = 0
        imgs = sorted({i for d in lm.values() for i in d['obs']} - set(cams))
        for img in imgs:
            pairs = [list(X[n]) + list(d['obs'][img]) for n, d in lm.items() if n in X and img in d['obs']]
            if len(pairs) >= 6:
                w, h = _size(img)
                try:
                    cams[img], rms = CAMS.fit(pairs, w, h)
                    new += 1
                except Exception as e:
                    print('  fit failed for', img, e)
        if not new:
            break
    free = sorted(set(cams) - set(fixed))
    names = sorted(X)
    obs = [(n, i, np.array(uv, float)) for n in names for i, uv in lm[n]['obs'].items() if i in cams]

    def pack():
        p = []
        for i in free:
            c = cams[i]
            p += list(Rotation.from_matrix(c['R']).as_rotvec()) + list(c['C']) + [np.log(c['f'])]
        for n in names:
            p += list(X[n])
        return np.array(p)

    def unpack(p):
        cc = dict(fixed)
        for k, i in enumerate(free):
            q = p[7 * k:7 * k + 7]
            c = dict(cams[i])
            c['R'] = Rotation.from_rotvec(q[:3]).as_matrix()
            c['C'] = q[3:6]
            c['f'] = float(np.exp(q[6]))
            cc[i] = c
        XX = {n: p[7 * len(free) + 3 * k:7 * len(free) + 3 * k + 3] for k, n in enumerate(names)}
        return cc, XX

    def resid(p):
        cc, XX = unpack(p)
        return np.concatenate([CAMS.project(cc[i], XX[n])[0] - uv for n, i, uv in obs])

    if not obs:
        print('no landmark has two observations in registered images yet (%d landmarks in the file)' % len(lm))
        return cams, X, [], np.zeros(0)
    p0 = pack()
    sol = least_squares(resid, p0, loss='soft_l1', f_scale=4.0, x_scale='jac') if len(p0) else None
    px = sol.x if sol is not None else p0
    cams2, X2 = unpack(px)
    r = resid(px).reshape(-1, 2)
    e = np.linalg.norm(r, axis=1)
    if verbose:
        print('landmarks %d (of %d), images %d fixed + %d fitted, observations %d, rms %.2f px, median %.2f, max %.2f'
              % (len(names), len(lm), len(fixed), len(free), len(obs), np.sqrt((e ** 2).mean()), np.median(e), e.max()))
        for i in free:
            ei = [e[k] for k, o in enumerate(obs) if o[1] == i]
            print('  %-28s n=%2d rms %.2f max %.2f  %s' % (i, len(ei), np.sqrt(np.mean(np.square(ei))), max(ei),
                                                         CAMS.describe(cams2[i])))
        bad = sorted([(e[k], o[0], o[1]) for k, o in enumerate(obs) if e[k] > 6.0], reverse=True)
        for err, n, i in bad[:25]:
            print('  residual %.1f px  %-28s in %s' % (err, n, i))
        skipped = [n for n in lm if n not in X]
        if skipped:
            print('  not triangulated (need 2 registered views):', skipped)
        unreg = sorted({i for d in lm.values() for i in d['obs']} - set(cams2))
        if unreg:
            print('  images not registered (need 6 known landmarks):', unreg)
    CAMS.save(cams2, os.path.join(CACHE, 'cams_S.json'))
    json.dump({n: np.round(X2[n], 5).tolist() for n in names}, open(os.path.join(CACHE, 'landmarks_S.json'), 'w'),
              indent=1)
    return cams2, X2, obs, e


def check(img):
    cams2, X2, obs, e = solve(verbose=False)
    for k, (n, i, uv) in enumerate(obs):
        if i == img:
            p = CAMS.project(cams2[i], X2[n])[0]
            print('%-28s picked (%.0f, %.0f)  model (%.1f, %.1f)  d = (%+.1f, %+.1f)' % (n, uv[0], uv[1], p[0], p[1],
                                                                                    p[0] - uv[0], p[1] - uv[1]))


def where(name):
    """Predicted pixel of a triangulated landmark in every registered image (to find it / to catch a wrong pick)."""
    cams2 = CAMS.load(os.path.join(CACHE, 'cams_S.json'))
    X = json.load(open(os.path.join(CACHE, 'landmarks_S.json')))
    if name not in X:
        print(name, 'is not triangulated yet')
        return
    print(name, 'S =', X[name])
    for i in sorted(cams2):
        uv, z = CAMS.project(cams2[i], X[name], depth=True)
        c = cams2[i]
        if z[0] > 0 and 0 <= uv[0, 0] < c['w'] and 0 <= uv[0, 1] < c['h']:
            if i.startswith('photos/') or i.endswith(('_033.jpg', '_043.jpg', '_053.jpg', '_031.jpg', '_039.jpg',
                                                      '_049.jpg', '_009.jpg', '_025.jpg', '_059.jpg')):
                print('   %-28s (%.0f, %.0f)' % (i, uv[0, 0], uv[0, 1]))


def mark(img, out, scale=1.0, box=None):
    """Draw the picks (yellow +, with names) and the solved model positions (cyan x) of all landmarks in an image.
    box = x0,y0,x1,y1 to draw a crop (original pixels)."""
    from PIL import Image, ImageDraw
    lm = {k: v for k, v in json.load(open(LM)).items() if not k.startswith('_')}
    cams2 = CAMS.load(os.path.join(CACHE, 'cams_S.json'))
    X = json.load(open(os.path.join(CACHE, 'landmarks_S.json')))
    im = Image.open(os.path.join(CACHE, img)).convert('RGB')
    x0, y0, x1, y1 = box or (0, 0, im.width, im.height)
    im = im.crop((x0, y0, x1, y1))
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for n, v in lm.items():
        if img in v['obs']:
            u, w_ = (v['obs'][img][0] - x0) * scale, (v['obs'][img][1] - y0) * scale
            d.line([(u - 9, w_), (u + 9, w_)], fill=(255, 255, 0), width=1)
            d.line([(u, w_ - 9), (u, w_ + 9)], fill=(255, 255, 0), width=1)
            d.text((u + 6, w_ + 4), n, fill=(255, 255, 0))
        if n in X and img in cams2:
            p, z = CAMS.project(cams2[img], X[n], depth=True)
            if z[0] > 0:
                u, w_ = (p[0, 0] - x0) * scale, (p[0, 1] - y0) * scale
                d.line([(u - 6, w_ - 6), (u + 6, w_ + 6)], fill=(0, 255, 255), width=1)
                d.line([(u - 6, w_ + 6), (u + 6, w_ - 6)], fill=(0, 255, 255), width=1)
                if img not in v['obs']:
                    d.text((u + 6, w_ - 12), n, fill=(0, 255, 255))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    im.save(out, quality=90)
    print('wrote', out, im.size)


if __name__ == '__main__':
    if sys.argv[1] == 'export':
        export()
    elif sys.argv[1] == 'solve':
        solve()
    elif sys.argv[1] == 'check':
        check(sys.argv[2])
    elif sys.argv[1] == 'where':
        where(sys.argv[2])
    elif sys.argv[1] == 'mark':
        a = sys.argv
        mark(a[2], a[3], float(a[4]) if len(a) > 4 else 1.0, [int(v) for v in a[5].split(',')] if len(a) > 5 else None)
