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
from model import swatch  # noqa: E402
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
# The sun as in the daylight photographs: on the REAR side of the lot (the aerial's shadows fall toward the street, a
# 3 m pergola throws 5 m), so the street front stands in open shade.  az from +Y toward +X.
SUN = dict(az=351.0, el=32.0)
# photographs cast onto the model in the viewer (web/viewer/photo.js): registered camera, output file, the parts of
# the image never used (0..1 from the top-left: burnt-in titles and watermarks) and a weight
# `cut`: polygons (original pixels) painted in the key colour, which the viewer never uses: things that stand in front
# of the model's surfaces in the photograph (the oak's trunks before the rear walls).  `walls`: cast onto upright
# surfaces only (ground and roofs take the aerial alone: an eye-level camera is fitted on the walls, not the lawn).
KEY = (255, 0, 255)
OAK_P26 = [(1700, 613), (1740, 673), (1787, 733), (1827, 800), (1867, 867), (1920, 933), (1923, 1000), (1895, 1215), (2045, 1215), (2033, 1000), (2053, 913), (2083, 867), (2080, 820), (2100, 767), (2137, 720), (2127, 700), (2107, 660), (2123, 600), (2047, 600), (2013, 660), (2000, 720), (1993, 787), (1993, 867), (1987, 907), (1960, 867), (1920, 827), (1880, 773), (1843, 720), (1810, 660), (1787, 600), (1700, 600)]
PROJECTORS = [
    dict(name='aerial', cam='photos/p30_b7b282.jpg', image='proj_aerial.jpg', masks=[], gain=1.0, clean_lawns=True),
    dict(name='front', cam='frames/seg002_053.jpg', image='proj_front.jpg', masks=[[0.0, 0.66, 1.0, 1.0]], gain=1.0, walls=True),
    dict(name='rear', cam='photos/p26_08c1ce.jpg', image='proj_rear.jpg', masks=[[0.0, 0.0, 0.24, 1.0]], gain=1.0, walls=True,
         cut=[OAK_P26]),
]


def clean_lawns(im, cam):
    """The aerial photograph shows the oak's bare branches over the lawns; cast onto the ground they would lie on the
    grass.  Inside the lawn outlines every pixel that is not grass-green is replaced by grass from nearby."""
    from PIL import Image, ImageDraw
    from scipy import ndimage
    from model.zones import site
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import cams as CAMS
    mask = Image.new('L', im.size, 0)
    d = ImageDraw.Draw(mask)
    for ring, holes in site.LAWNS:
        d.polygon([tuple(q) for q in CAMS.project(cam, np.array(ring, float))], fill=255)
    for ring, holes in site.LAWNS:
        for h in holes:
            d.polygon([tuple(q) for q in CAMS.project(cam, np.array(h, float))], fill=0)
    lawn = np.array(mask) > 0
    a = np.asarray(im, float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    grass = (g > r * 1.10) & (g > b * 0.70) & (r + g + b < 520) & ~((b > 0.85 * g) & (g > 70))      # not the pool's water
    grass = ndimage.binary_erosion(grass, iterations=1)
    bad = lawn & ~grass
    bad = ndimage.binary_dilation(bad, iterations=2) & lawn
    good = lawn & ~bad
    if good.sum() < 1000:
        return im
    idx = ndimage.distance_transform_edt(~good, return_distances=False, return_indices=True)
    rng = np.random.default_rng(5)
    yy, xx = np.nonzero(bad)
    out = a.copy()
    for _ in range(3):                                  # nearest grass, jittered so that the fill keeps a grain
        jy = np.clip(idx[0][yy, xx] + rng.integers(-7, 8, len(yy)), 0, a.shape[0] - 1)
        jx = np.clip(idx[1][yy, xx] + rng.integers(-7, 8, len(yy)), 0, a.shape[1] - 1)
        ok = good[jy, jx]
        out[yy[ok], xx[ok]] = a[jy[ok], jx[ok]]
        yy, xx = yy[~ok], xx[~ok]
    out[yy, xx] = a[idx[0][yy, xx], idx[1][yy, xx]]
    soft = ndimage.gaussian_filter(out, sigma=(1.2, 1.2, 0))
    w = ndimage.gaussian_filter(bad.astype(float), 1.5)[..., None]
    out = out * (1 - w) + soft * w
    print('aerial: %.0f %% of the lawn pixels refilled' % (100.0 * bad.sum() / max(1, lawn.sum())))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


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
        if p.get('clean_lawns'):
            im = clean_lawns(im, c)
        d = ImageDraw.Draw(im)
        for m in p['masks']:
            d.rectangle([m[0] * im.width, m[1] * im.height, m[2] * im.width, m[3] * im.height], fill=KEY)
        for poly in p.get('cut', []):
            d.polygon([tuple(q) for q in poly], fill=KEY, outline=KEY, width=9)
        im.save(os.path.join(HERE, 'out', p['image']), quality=90, subsampling=0)
        out.append(dict(name=p['name'], image=p['image'], masks=p['masks'], gain=p['gain'], walls=bool(p.get('walls')),
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
                swatches=swatch.make(wc) if zones is None else {},
                stats=dict(triangles=int(sum(p.ntri for p in parts)), bytes=n,
                           parts={p.name: p.ntri for p in parts}))
    json.dump(meta, open(os.path.join(HERE, 'out', out + '_meta.json'), 'w'))
    print('wrote out/%s.glb  %d parts  %d triangles  %.2f MB' % (out, len(parts), meta['stats']['triangles'], n / 1e6))
    return parts


if __name__ == '__main__':
    a = sys.argv[1:]
    zones = a[a.index('--zones') + 1].split(',') if '--zones' in a else None
    build(zones, a[a.index('--out') + 1] if '--out' in a else 'house')
