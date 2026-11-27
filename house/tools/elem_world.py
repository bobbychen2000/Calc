"""World extents of surveyed elements: their pixel box (survey/<zone>.json, in a registered image) cast onto a
wall plane.   python3 -I tools/elem_world.py ZONE  id=y:VAL | id=x:VAL  [...]
Prints, per element, the box on the plane: along-wall range, height range, width x height."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from tools import cams as CAMS  # noqa: E402

zone = sys.argv[1]
els = {e['id'].split('.', 1)[1]: e for e in json.load(open(os.path.join(HERE, 'survey', zone + '.json')))['elements']}
W = frame.world_cams()
for spec in sys.argv[2:]:
    name, pl = spec.split('=')
    ax, val = pl.split(':')
    e = els[name]
    r = e['ref']
    if r['image'] not in W:
        print('%-30s image %s is not registered' % (name, r['image']))
        continue
    if 'bbox' in r:
        x0, y0, x1, y1 = r['bbox']
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    else:
        pts = r['poly']
    P = CAMS.hit_plane(W[r['image']], pts, **{ax: float(val)})
    a = P[:, 0] if ax == 'y' else P[:, 1]
    print('%-30s %s=%-6s  %s %.2f..%.2f  Z %.2f..%.2f   %.2f x %.2f' % (name, ax, val, 'X' if ax == 'y' else 'Y', a.min(), a.max(),
                                                                    P[:, 2].min(), P[:, 2].max(), a.max() - a.min(), P[:, 2].max() - P[:, 2].min()))
