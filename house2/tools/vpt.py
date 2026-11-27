"""World points of a photo's pixels from the VGGT run (the per-pixel point maps), in world metres (survey/frame.json).

    python3 -I tools/vpt.py IMAGE u,v [u,v ...]        # original pixels -> X Y Z (median over the nearest VGGT samples)
    from tools.vpt import points; points('photos/hero_721b4a.jpg', [(u, v), ...])
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_D = {}


def _load():
    if not _D:
        d = np.load(os.path.join(HERE, 'refs', 'cache', 'vggt', 'run1.npz'), allow_pickle=True)
        fr = json.load(open(os.path.join(HERE, 'survey', 'frame_vggt.json')))
        _D.update(names=[str(n) for n in d['names']], P=d['world_points'], pad=d['pad'], conf=d['world_points_conf'],
                  R=np.array(fr['R']), o=np.array(fr['origin_vggt']), s=fr['scale'])
    return _D


def points(name, uvs, r=1):
    D = _load()
    i = D['names'].index(name if name.startswith('photos/') else 'photos/' + name)
    w, h, nw, nh, left, top = [float(v) for v in D['pad'][i]]
    out = []
    for u, v in uvs:
        gx, gy = left + u * nw / w - 0.5, top + v * nh / h - 0.5
        ix, iy = int(round(gx)), int(round(gy))
        blk = D['P'][i][max(0, iy - r):iy + r + 1, max(0, ix - r):ix + r + 1].reshape(-1, 3)
        p = np.median(blk, 0)
        out.append((p - D['o']) @ D['R'].T * D['s'])
    return np.array(out)


if __name__ == '__main__':
    name = sys.argv[1]
    uvs = [tuple(float(x) for x in a.split(',')) for a in sys.argv[2:]]
    for (u, v), p in zip(uvs, points(name, uvs)):
        print('(%5.0f, %5.0f) -> X %7.2f  Y %7.2f  Z %6.2f' % (u, v, *p))
