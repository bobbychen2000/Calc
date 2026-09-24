"""Tail art and symbols, re-drawn by us for the livery painter (tools/liveries/paint.py).

Nothing here is copied from an airline file: each mark is constructed geometrically (numpy on a supersampled grid, or an
SVG path we wrote, rasterised with cairosvg) to match the shape seen on the airline's official reference images, at the
level of detail visible on an aircraft at airport distances. Trademarks belong to their owners; the app renders them
as a non-commercial depiction (notice in the app's About box, docs/ATTRIBUTION_models.md).

Every function returns a PIL RGBA image (sRGB, transparent background).
"""
import math
import numpy as np
from PIL import Image, ImageDraw

from common import hex_rgb


def _rgba(mask_colors, H, W):
    """compose [(alpha (H, W) float, hex colour), ...] back to front into an RGBA image"""
    out = np.zeros((H, W, 4), np.float32)
    for a, c in mask_colors:
        a = np.clip(a, 0, 1)[..., None]
        col = np.concatenate([hex_rgb(c), [1.0]]).astype(np.float32)
        out = out * (1 - a) + col * a
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')


def _grid(n, ss=1):
    y, x = np.mgrid[0:n * ss, 0:n * ss].astype(np.float32)
    return (x + 0.5) / (n * ss) * 2 - 1, 1 - (y + 0.5) / (n * ss) * 2   # x right, y up in [-1, 1]


def _down(a, ss):
    if ss == 1: return a
    H, W = a.shape; return a.reshape(H // ss, ss, W // ss, ss).mean((1, 3))


def _aa(d, px):
    return np.clip(0.5 - d / px, 0, 1)


# ---------------------------------------------------------------------------------------------- United
def united_globe(n=1024, bg='#0033A0', tile='#6CB2E2', ring='#FFFFFF', ring_w=0.025):
    """United's globe as painted on the 2019 tail (United livery graphic, united.mediaroom.com 24 Apr 2019): a sphere
    seen with its pole tilted to the upper right, Sky Blue tiles separated by United Blue meridian and latitude gaps,
    a thin white ring. Constructed: orthographic sphere, tiles = cells of a lat/lon grid."""
    x, y = _grid(n); px = 2.0 / n
    r = np.hypot(x, y)
    zz = np.sqrt(np.clip(1 - r * r, 0, 1))
    p = np.array([0.55, 0.76, 0.30]); p /= np.linalg.norm(p)          # pole direction (viewer right-up-front)
    e1 = np.cross(p, [0, 0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(p, e1)
    N = np.stack([x, y, zz], -1)
    lat = np.degrees(np.arcsin(np.clip(N @ p, -1, 1)))
    lon = np.degrees(np.arctan2(N @ e2, N @ e1))
    # latitude bands every 12 deg (gap 3.2 deg), meridians every 15 deg (gap narrowing toward the pole)
    fl = np.mod(lat + 3, 15.0); gl = np.minimum(fl, 15.0 - fl)
    fm = np.mod(lon + 6, 12.0); gm = np.minimum(fm, 12.0 - fm) * np.cos(np.radians(lat))
    # soft edges in degrees -> use a fixed ramp
    tile_a = np.clip((gl - 1.5) / 0.5, 0, 1) * np.clip((gm - 2.4) / 0.5, 0, 1) * (lat < 72)
    disk = _aa(r - 1 + ring_w, px)
    ring_a = _aa(r - 1, px) - disk
    return _rgba([(disk, bg), (disk * tile_a, tile), (ring_a, ring)], n, n)


# ---------------------------------------------------------------------------------------------- generic helpers
def svg(path_svg, n=1024):
    import cairosvg, io
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=path_svg.encode(), output_height=n))).convert('RGBA')


def circle(n=512, color='#FFFFFF', ring=None, ring_w=0.08):
    x, y = _grid(n); px = 2.0 / n; r = np.hypot(x, y)
    layers = [(_aa(r - 1, px), ring or color)]
    if ring: layers.append((_aa(r - 1 + ring_w, px), color))
    return _rgba(layers, n, n)


def maple_leaf(n=1024, color='#F01428', bg=None, bg_shape='circle', margin=0.1):
    """11-point maple leaf as on the flag of Canada (construction after the Canadian flag specification, 1964/65:
    the leaf is a public symbol; this is our own polygon approximation)."""
    # half outline (right side) of the flag leaf, in a unit box: x 0..1 (centre 0), y -1..1 (stem at bottom)
    pts = [(0.0, 1.0), (0.13, 0.72), (0.27, 0.80), (0.21, 0.35), (0.40, 0.55), (0.46, 0.42), (0.66, 0.46),
           (0.60, 0.25), (0.68, 0.20), (0.40, -0.02), (0.46, -0.16), (0.04, -0.10), (0.05, -0.56), (0.0, -0.56)]
    poly = [(x, y) for x, y in pts] + [(-x, y) for x, y in reversed(pts[:-1])]
    S = 4 * n; im = Image.new('L', (S, S), 0); d = ImageDraw.Draw(im)
    sc = (1 - margin) * S / 2
    d.polygon([(S / 2 + x * sc, S / 2 - y * sc * 0.97 + 0.05 * sc) for x, y in poly], fill=255)
    a = np.asarray(im.resize((n, n), Image.LANCZOS)).astype(np.float32) / 255
    layers = []
    if bg:
        x, y = _grid(n); px = 2.0 / n
        layers.append((_aa(np.hypot(x, y) - 1, px) if bg_shape == 'circle' else np.ones_like(x), bg))
    layers.append((a, color))
    return _rgba(layers, n, n)


def poly_image(polys, n=1024, aspect=1.0):
    """[(points in [0,1]^2 (x right, y down), hex), ...] -> RGBA image of width n*aspect, height n (4x supersampled)"""
    W = int(n * aspect); ss = 4
    out = np.zeros((n, W, 4), np.float32)
    for pts, c in polys:
        im = Image.new('L', (W * ss, n * ss), 0)
        ImageDraw.Draw(im).polygon([(x * W * ss, y * n * ss) for x, y in pts], fill=255)
        a = np.asarray(im.resize((W, n), Image.LANCZOS)).astype(np.float32)[..., None] / 255
        col = np.concatenate([hex_rgb(c), [1.0]]).astype(np.float32)
        out = out * (1 - a) + col * a
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')
