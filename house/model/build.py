"""Build the house model:  python3 -I model/build.py [--zones a,b] [--out NAME]
-> out/NAME.glb (default house.glb) + out/NAME_meta.json (cameras of the reference images in world metres,
named views, sun, per-part triangle counts).  Each zone module model/zones/<zone>.py has build() -> [Part]."""
import importlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from model.glb import GLB  # noqa: E402
from model import materials as _materials  # noqa: E402

MATERIALS = _materials.MATERIALS

ZONES = ['site', 'house']
VIEWS = {
    'front': dict(label='Front', pos=(4.0, -26.0, 5.5), target=(13.0, 6.0, 3.5), fov=42),
    'aerial': dict(label='Aerial', pos=(-14.0, -24.0, 26.0), target=(13.0, 14.0, 2.0), fov=42),
    'rear': dict(label='Rear', pos=(-2.0, 42.0, 4.0), target=(14.0, 16.0, 3.0), fov=45),
    'pool': dict(label='Pool', pos=(3.0, 44.0, 2.2), target=(22.0, 38.0, 1.5), fov=50),
}
SUN = dict(az=205.0, el=40.0)


def build(zones=None, out='house'):
    parts = []
    views = dict(VIEWS)
    for z in zones or ZONES:
        mod = importlib.import_module('model.zones.' + z)
        ps = mod.build()
        if zones:                                   # a test build: the zone's own views replace the house's
            views = dict(getattr(mod, 'VIEWS', views))
        parts += ps
        print('%-14s %3d parts %8d triangles' % (z, len(ps), sum(p.ntri for p in ps)))
    g = GLB()
    used = set()
    for p in parts:
        g.part(p, MATERIALS)
        used |= {m.mat for m in p.geo.meshes()}
    missing = sorted(used - set(MATERIALS))
    if missing:
        print('materials not in model/materials.py:', missing)
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    n = g.write(os.path.join(HERE, 'out', out + '.glb'))
    vs = [m.V for p in parts for m in p.geo.meshes() if p.group == 'house'] or [m.V for p in parts for m in p.geo.meshes()]
    V = np.vstack(vs) if vs else np.zeros((1, 3))
    cams = {}
    for k, c in frame.world_cams().items():
        cams[k] = dict(w=c['w'], h=c['h'], f=c['f'], R=np.round(c['R'], 8).tolist(), C=np.round(c['C'], 4).tolist())
    meta = dict(glb=out + '.glb', centre=[float(v) for v in (V.min(0) + V.max(0)) / 2], sun=SUN, views=views,
                start=next(iter(views)), cameras=cams,
                stats=dict(triangles=int(sum(p.ntri for p in parts)), bytes=n,
                           parts={p.name: p.ntri for p in parts}))
    json.dump(meta, open(os.path.join(HERE, 'out', out + '_meta.json'), 'w'))
    print('wrote out/%s.glb  %d parts  %d triangles  %.2f MB' % (out, len(parts), meta['stats']['triangles'], n / 1e6))
    return parts


if __name__ == '__main__':
    a = sys.argv[1:]
    zones = a[a.index('--zones') + 1].split(',') if '--zones' in a else None
    build(zones, a[a.index('--out') + 1] if '--out' in a else 'house')
