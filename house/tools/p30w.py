"""Aerial-photo pixels -> world plan coordinates at a given height:  python3 -I tools/p30w.py Z u,v [u,v ...]
(or world -> pixels:  python3 -I tools/p30w.py px X,Y,Z [...])"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from tools import cams as CAMS  # noqa: E402

cam = frame.world_cams()['photos/p30_b7b282.jpg']
a = sys.argv[1:]
if a[0] == 'px':
    for t in a[1:]:
        p = [float(v) for v in t.split(',')]
        uv = CAMS.project(cam, [p])[0]
        print('(%.2f, %.2f, %.2f) -> (%.0f, %.0f)' % (*p, uv[0], uv[1]))
else:
    z = float(a[0])
    out = []
    for t in a[1:]:
        u, v = [float(x) for x in t.split(',')]
        P = CAMS.hit_plane(cam, [[u, v]], z=z)[0]
        out.append('(%.2f, %.2f)' % (P[0], P[1]))
    print('z=%.2f: ' % z + ' '.join(out))
