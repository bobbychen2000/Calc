"""3-D position (frame S) of a pixel of a registered SfM video frame, read from the SfM points that project near it.

    python3 -I tools/sfm_pt.py FRAME u,v [u,v ...]          # FRAME = 'frames_all/frames/frame_022100ms.jpg'
    from tools.sfm_pt import xyz; xyz(frame, (u, v), r=6)

The points within r px of the pixel are taken, the front-most depth cluster kept (the surface the pixel sees, not what
is behind it) and their median returned with its spread.  Used to give a landmark picked in one video frame its 3-D
position (survey/landmarks*.json "xyz_S"), so the photos can be registered on it without a second pick.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tools import cams as CAMS  # noqa: E402

_C = {}


def _load():
    if not _C:
        _C['cams'] = CAMS.load(os.path.join(HERE, 'refs', 'cache', 'cams_sfm.json'))
        _C['P'] = np.load(os.path.join(HERE, 'refs', 'cache', 'sfm_points_S.npz'))['P'].astype(float)
    return _C


def xyz(frame, uv, r=6.0, verbose=False):
    D = _load()
    cam = D['cams'][frame]
    uvp, z = CAMS.project(cam, D['P'], depth=True)
    d = np.linalg.norm(uvp - np.asarray(uv, float), axis=1)
    m = (z > 0) & (d < r)
    if m.sum() < 3:
        m = (z > 0) & (d < 2.5 * r)
    if m.sum() < 3:
        return None, None
    zz = z[m]
    near = zz < np.percentile(zz, 30) + max(0.02 * np.median(zz), 0.01)
    Q = D['P'][m][near]
    p = np.median(Q, 0)
    if verbose:
        print('  %d points within %.0f px, %d in the front cluster, spread %s' % (m.sum(), r, near.sum(),
                                                                                   np.round(Q.std(0), 4)))
    return p, Q.std(0)


if __name__ == '__main__':
    fr = sys.argv[1]
    for a in sys.argv[2:]:
        u, v = (float(x) for x in a.split(','))
        p, sd = xyz(fr, (u, v), verbose=True)
        print('(%6.1f, %6.1f) ->' % (u, v), None if p is None else np.round(p, 4))
