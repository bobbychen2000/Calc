#!/usr/bin/env python3
"""Quick software render of a converted model (data/models/<key>.sfom) with its textures and an optional livery texture
in place of texture 0 (the livery atlas), for checking liveries without a browser or Blender.

Usage: python3 tools/liveries/preview.py <model.sfom> [--livery tex.webp] [--type b739] [--views side,34,front,top,rear34] [--out x.png]
Views: side (port side), stbd (starboard side), 34 (front three-quarter from port, slightly above), rear34, front, top, bottom.
Shading: Lambert with a sky term; no shadows. Model frame: x forward, y up, z starboard.
"""
import argparse, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, sfom
from raster import raster, sample_bilinear


def look(eye, target, up=(0, 1, 0)):
    f = np.asarray(target, float) - eye; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
    return np.stack([r, u, -f])


VIEWS = {  # (azimuth deg from +x toward -z (port) , elevation deg)
    'side': (90, 3), 'stbd': (-90, 3), '34': (40, 14), 'rear34': (140, 14), 'front': (0, 4), 'top': (90, 89), 'bottom': (90, -80),
    'stbd34': (-40, 14), 'rear': (180, 5), 'fin': (100, 8),
}


def render(m, P, tex, view, W=1100, H=560, livery=None, bg=(206, 214, 222), sun=(0.4, 0.8, -0.45), zoom=None):
    idx, UV, N = m['idx'], m['uv'], m['nrm']
    az, el = VIEWS[view] if isinstance(view, str) else view
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.cos(e) * math.cos(a), math.sin(e), -math.cos(e) * math.sin(a)])
    lo, hi = P.min(0), P.max(0); c = (lo + hi) / 2
    if zoom: c = np.array(zoom[0], float)
    R = look(c + d * 200, c, up=(0, 1, 0) if abs(el) < 80 else (1, 0, 0))
    Q = (P - c) @ R.T
    span = zoom[1] if zoom else max(Q[:, 0].ptp() / W, Q[:, 1].ptp() / H) * 1.06
    px = np.stack([W / 2 + Q[:, 0] / span, H / 2 - Q[:, 1] / span], -1)
    tri = px[idx]; dep = -Q[:, 2][idx]
    tid, bary = raster(tri, W, H, depth=dep.astype(np.float32))
    ok = tid >= 0; t = np.maximum(tid, 0)
    Vi = idx[t]
    uv = (UV[Vi] * bary[..., None]).sum(-2); nn = (N[Vi] * bary[..., None]).sum(-2)
    nn /= np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-6)
    # face the camera
    vd = d / np.linalg.norm(d); flip = (nn @ vd) < 0; nn[flip] *= -1
    h = m['head']; mats = h['mats']
    tm = m['tri_mat'][t]
    col = np.ones((H, W, 3), np.float32) * 0.8
    matcol = np.array([mm['color'][:3] for mm in mats], np.float32)
    mtex = np.array([mm['tex'] for mm in mats]); mkind = np.array([mm['kind'] for mm in mats])
    col = matcol[tm].copy()
    for ti, im in enumerate(tex):
        sel = ok & (mtex[tm] == ti)
        if not sel.any(): continue
        img = im
        if ti == 0 and livery is not None: img = livery
        arr = np.asarray(img.convert('RGB')).astype(np.float32) / 255
        col[sel] = col[sel] * sample_bilinear(arr, uv[sel][:, 0] % 1, uv[sel][:, 1] % 1)
    glass = ok & (mkind[tm] == 'glass'); col[glass] = (0.05, 0.06, 0.07)
    lin = common.srgb_to_lin(col)
    L = np.asarray(sun, float); L /= np.linalg.norm(L)
    diff = np.clip(nn @ L, 0, 1)[..., None]; sky = (0.55 + 0.45 * nn[..., 1:2])
    out = lin * (diff * 0.85 + sky * 0.35)
    # simple specular for glass/paint
    hv = L + vd; hv /= np.linalg.norm(hv)
    spec = np.clip(nn @ hv, 0, 1) ** 60 * 0.25
    out = out + spec[..., None] * np.where(glass[..., None], 2.0, 0.6)
    img = common.lin_to_srgb(out / (1 + out * 0.15))
    img[~ok] = np.array(bg) / 255
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def load_for(path, type_key=None):
    m = sfom.load(path)
    P = m['pos']
    if type_key:
        A = common.app(); f = A['types'][type_key]['fit']
        if f and f['stretch']: P = common.apply_stretch(P, m['zone'], f['stretch'])
    return m, P


def sheet(m, P, views, livery=None, W=1100, H=520, title=None):
    ims = [render(m, P, m['textures'], v, W, H, livery) for v in views]
    cols = 2 if len(ims) > 1 else 1; rows = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (cols * W, rows * H + (30 if title else 0)), (255, 255, 255))
    for i, im in enumerate(ims): S.paste(im, ((i % cols) * W, (30 if title else 0) + (i // cols) * H))
    if title: ImageDraw.Draw(S).text((10, 8), title, fill=(0, 0, 0))
    return S


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('model'); ap.add_argument('--livery'); ap.add_argument('--type'); ap.add_argument('--views', default='side,34,stbd34,rear34')
    ap.add_argument('--out', default='preview.png'); ap.add_argument('--w', type=int, default=1100); ap.add_argument('--h', type=int, default=520)
    a = ap.parse_args()
    m, P = load_for(a.model, a.type)
    liv = Image.open(a.livery) if a.livery else None
    sheet(m, P, a.views.split(','), liv, a.w, a.h, title=os.path.basename(a.model) + (' + ' + os.path.basename(a.livery) if a.livery else '')).save(a.out)
    print(a.out)
