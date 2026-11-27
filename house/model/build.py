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
# photographs cast onto the model in the viewer (web/viewer/photo.js): registered camera, output file, the parts of
# the image never used (0..1 from the top-left: burnt-in titles and watermarks) and a weight
PROJECTORS = [
    dict(name='aerial', cam='photos/p30_b7b282.jpg', image='proj_aerial.jpg', masks=[], gain=1.0),
    dict(name='front', cam='frames/seg002_053.jpg', image='proj_front.jpg', masks=[[0.0, 0.66, 1.0, 1.0]], gain=1.0),
]


def projectors(cams):
    """Copy the projector photographs (masked parts blacked out) next to the model; returns the meta entries."""
    from PIL import Image, ImageDraw
    out = []
    for p in PROJECTORS:
        c = cams.get(p['cam'])
        src = os.path.join(HERE, 'refs', 'cache', p['cam'])
        if c is None or not os.path.exists(src):
            continue
        im = Image.open(src).convert('RGB')
        d = ImageDraw.Draw(im)
        for m in p['masks']:
            d.rectangle([m[0] * im.width, m[1] * im.height, m[2] * im.width, m[3] * im.height], fill=(0, 0, 0))
        im.save(os.path.join(HERE, 'out', p['image']), quality=90)
        out.append(dict(name=p['name'], image=p['image'], masks=p['masks'], gain=p['gain'],
                        cam=dict(w=c['w'], h=c['h'], f=float(c['f']), cx=float(c.get('cx', c['w'] / 2)),
                                 cy=float(c.get('cy', c['h'] / 2)), k1=float(c.get('k1', 0.0) or 0.0),
                                 R=np.round(c['R'], 8).tolist(), C=np.round(c['C'], 4).tolist())))
    return out


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
    wc = frame.world_cams()
    for k, c in wc.items():
        cams[k] = dict(w=c['w'], h=c['h'], f=c['f'], R=np.round(c['R'], 8).tolist(), C=np.round(c['C'], 4).tolist())
    meta = dict(glb=out + '.glb', centre=[float(v) for v in (V.min(0) + V.max(0)) / 2], sun=SUN, views=views,
                start=next(iter(views)), cameras=cams, projectors=projectors(wc) if zones is None else [],
                stats=dict(triangles=int(sum(p.ntri for p in parts)), bytes=n,
                           parts={p.name: p.ntri for p in parts}))
    json.dump(meta, open(os.path.join(HERE, 'out', out + '_meta.json'), 'w'))
    print('wrote out/%s.glb  %d parts  %d triangles  %.2f MB' % (out, len(parts), meta['stats']['triangles'], n / 1e6))
    return parts


if __name__ == '__main__':
    a = sys.argv[1:]
    zones = a[a.index('--zones') + 1].split(',') if '--zones' in a else None
    build(zones, a[a.index('--out') + 1] if '--out' in a else 'house')
