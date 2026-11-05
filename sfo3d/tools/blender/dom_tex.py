"""Procedural detail tiles of the domestic terminals asset (tools/blender/build_domestic.py): tangent-space normal maps
(OpenGL / glTF convention, +Y = +V) computed analytically from height fields (membrane roll seams, panel joints, curtain-wall
caps, corrugation, PV module frames) and sRGB base-colour tiles (curtain-wall glass with its caps, fritted glass, PV cells).
Baking the fine detail into mip-mapped textures instead of geometry avoids moire (docs/research/engine.md 7.1). Our own
procedural textures: no imagery of any kind is used (NAIP 2024 only gives the roof colours, as numbers).

One tile spans TILE[name] metres of UV_detail. tools/blender/dom_geom.py lays UV_detail out in metres / tile with the SAME
tile sizes (dom_geom.TILE); walls: u = running length along the facade ring, v = height above the band bottom, so a
curtain tile's transoms start at the band bottom and its verticals fall on the LOD0 mullion fins (every `mod` m of the ring).

  dom_n_membrane   512   12 x 12 m   single-ply roof membrane: welded laps every 3.0 m (rolls ~3 m wide) [inf] + faint undulation
  dom_n_panel      512    6 x 6 m    metal panels 3.0 x 1.5 m with 2-cm joints [module inf: not published]
  dom_n_curtain    512    6 x 6 m    curtain-wall caps: verticals every 1.5 m (dom_geom.MULL), transoms every 3.0 m [inf]
  dom_n_t3w        512    6 x 5.8 m  T3 West window wall: verticals every 2.0 m, one transom 3.5 m above the band bottom
                                     (BD-03 view 3 schematic: module not published) [unk / inf]
  dom_n_corr       512    3 x 2.8 m  T3E penthouse "perforated corrugated metal with wide-profile accent stripes" [pub]: 0.2-m
                                     vertical corrugation, a flat accent band every 1.4 m (BD-03 schematic) [inf]
  dom_n_pv         512    4 x 4 m    PV modules 1.0 x 2.0 m with frames (low-tilt racks) [inf]
  dom_c_<glass>    512    6 x 6 m    curtain glass colour + light aluminium caps on the dom_n_curtain grid [inf]
  dom_c_frit_grey  512    6 x 6 m    BA-E "clear glass with grey frit" [pub bae.facade]: horizontal frit lines [pattern inf]
  dom_c_frit_green 512x512 12 x 9 m  T1 Center landside upper tiers: green frit with the vertical striation of photo d1 and the
                                     tier transom 44 % up (draw_domestic.T1_SPLIT) [obs photo d1, schematic]; NO regular
                                     verticals (the irregular mullions are LOD0 fins, draw_domestic.t1_mullions)
  dom_c_t3w        512    6 x 5.8 m  T3 West fritted IGU window wall (light blue-grey) with its caps [pub materials, module unk]
  dom_c_pv         512    4 x 4 m    PV cells (dark blue) with silver module frames [inf]
"""
import os

import numpy as np
from PIL import Image

TILES = {   # name: (metres along U, metres along V); must equal dom_geom.TILE for the materials that use them
    'dom_n_membrane': (12.0, 12.0),
    'dom_n_panel': (6.0, 6.0),
    'dom_n_curtain': (6.0, 6.0),
    'dom_n_t3w': (6.0, 5.8),
    'dom_n_corr': (3.0, 2.8),
    'dom_n_pv': (4.0, 4.0),
    'dom_c_frit_grey': (6.0, 6.0),
    'dom_c_frit_green': (12.0, 9.0),
    'dom_c_t3w': (6.0, 5.8),
    'dom_c_pv': (4.0, 4.0),
}
CURTAIN = (1.5, 3.0)            # vertical / transom pitch of the generic curtain grid [inf] (dom_geom.MULL = 1.5)
T3W_GRID = (2.0, 3.5)           # T3W: vertical pitch 2.0 m (BD-03 schematic), transom 3.5 m above the band bottom [unk]
T1_TRANSOM = 0.44 * 9.0         # draw_domestic.T1_SPLIT x (T1_HEAD - T1_CANOPY) = 3.96 m above the canopy line [inf photo d1]
CAP_RGB = (176, 180, 184)       # aluminium caps (sRGB) [inf]

CURTAIN_GLASS = {   # base-colour curtain tiles: glass colour (sRGB, = the material's base colour) with light caps
    'dom_c_glass_ec': (44, 58, 70),        # BA-B electrochromic glass (tinted state varies; mid value) [pub glazing, colour inf]
    'dom_c_glass_lowe': (66, 82, 92),      # clerestories / lantern / monitor [inf]
    'dom_c_glass_tint': (40, 54, 58),      # generic tinted gate-room glass (BA-C / D / F, halls airside) [unk]
    'dom_c_glass_clear': (30, 36, 40),     # clear glass under the T1 canopy / BA-E end wall (dark: unlit interior) [obs photos d1 / a1]
}


def _normal_png(height, su, sv, path, strength=1.0):
    """height[r, c] with row 0 = TOP of the image (v = 1); su / sv = metres per pixel along u / v."""
    hp = np.pad(height, 1, mode='wrap')
    dhdu = (hp[1:-1, 2:] - hp[1:-1, :-2]) / (2 * su)
    dhdv = -(hp[2:, 1:-1] - hp[:-2, 1:-1]) / (2 * sv)
    n = np.stack([-dhdu * strength, -dhdv * strength, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    img = np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    Image.fromarray(img, 'RGB').save(path, optimize=True)
    return path


def _rgb_png(col, path):
    Image.fromarray(np.clip(np.round(col), 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)
    return path


def _groove(d, half_w, depth):
    x = np.clip(np.abs(d) / half_w, 0, 1)
    return -depth * (1 - x * x) ** 2


def _grid(W, H, tu, tv):
    u = (np.arange(W) + 0.5) / W * tu
    v = (1 - (np.arange(H) + 0.5) / H) * tv
    return u[None, :], v[:, None]


def _dist(x, period, phase=0.0):
    r = np.mod(x - phase, period)
    return np.minimum(r, period - r)


def _noise(size_w, size_h, cells, seed):
    rng = np.random.default_rng(seed)
    k = rng.normal(size=cells)
    im = Image.fromarray(((k - k.min()) / (np.ptp(k) + 1e-9) * 255).astype(np.uint8)).resize((size_w, size_h), Image.BICUBIC)
    return np.array(im, float) / 255.0


def membrane(path, size=512):
    tu, tv = TILES['dom_n_membrane']
    u, v = _grid(size, size, tu, tv)
    h = np.maximum(_groove(_dist(v, 3.0), 0.05, -0.004), 0) + 0 * u          # raised welded laps along u, every 3 m
    h = h + 0.002 * (_noise(size, size, (8, 8), 11) - 0.5)
    return _normal_png(h, tu / size, tv / size, path)


def panel(path, size=512):
    tu, tv = TILES['dom_n_panel']
    u, v = _grid(size, size, tu, tv)
    h = np.minimum(_groove(_dist(u, 3.0), 0.02, 0.008), _groove(_dist(v, 1.5), 0.02, 0.008))
    return _normal_png(h, tu / size, tv / size, path)


def curtain(path, pitch, tile, size=512, phase_v=0.0):
    tu, tv = tile
    u, v = _grid(size, size, tu, tv)          # square pixels not needed: 512 x 512 for any tile aspect
    cap = np.maximum(-_groove(_dist(u, pitch[0]), 0.05, 0.03), -_groove(_dist(v, pitch[1], phase_v), 0.05, 0.03))
    return _normal_png(cap, tu / u.shape[1], tv / v.shape[0], path)


def curtain_colour(path, glass_rgb, pitch=CURTAIN, tile=(6.0, 6.0), size=512, phase_v=0.0):
    tu, tv = tile
    u, v = _grid(size, size, tu, tv)          # square pixels not needed: 512 x 512 for any tile aspect
    cap = ((_dist(u, pitch[0]) < 0.03) | (_dist(v, pitch[1], phase_v) < 0.03)).astype(float)
    col = np.array(glass_rgb, float)[None, None, :] * (1 - cap[..., None]) + np.array(CAP_RGB, float)[None, None, :] * cap[..., None]
    return _rgb_png(col, path)


def frit_grey(path, size=512):
    """BA-E: clear glass with grey frit [pub]: 6-cm frit lines every 0.15 m over the glass (light grey), caps on the curtain
    grid [pattern inf]; reads light grey from a distance (photo a1)."""
    tu, tv = TILES['dom_c_frit_grey']
    u, v = _grid(size, size, tu, tv)
    f = (_dist(v, 0.15) < 0.03).astype(float) + 0 * u
    glass, fr = np.array([52, 62, 68.0]), np.array([168, 172, 174.0])
    col = glass[None, None, :] * (1 - 0.55 * f[..., None]) + fr[None, None, :] * 0.55 * f[..., None]
    cap = ((_dist(u, CURTAIN[0]) < 0.03) | (_dist(v, CURTAIN[1]) < 0.03)).astype(float)
    col = col * (1 - cap[..., None]) + np.array(CAP_RGB, float)[None, None, :] * cap[..., None]
    return _rgb_png(col, path)


def frit_green(path, w=512, h=512):
    """T1 Center landside tiers: light sage-green fritted glass with a fine vertical striation (photo d1) and the tier transom
    (dark 8-cm line) 3.96 m above the canopy line [obs photo d1; values inf]."""
    tu, tv = TILES['dom_c_frit_green']
    u, v = _grid(w, h, tu, tv)
    base = np.array([150, 170, 160.0])
    stri = 0.06 * np.sin(2 * np.pi * u / 0.35) + 0.04 * (_noise(w, 1, (1, 48), 5) - 0.5)
    shade = 1.0 + stri + 0 * v
    col = base[None, None, :] * shade[..., None]
    tr = (np.abs(v - T1_TRANSOM) < 0.05).astype(float) + 0 * u
    col = col * (1 - tr[..., None]) + np.array([62, 74, 68.0])[None, None, :] * tr[..., None]
    return _rgb_png(col, path)


def corrugation(path, size=512):
    tu, tv = TILES['dom_n_corr']
    u, v = _grid(size, size, tu, tv)
    h = 0.012 * np.sin(2 * np.pi * u / 0.2)
    band = (_dist(v, 1.4) < 0.18).astype(float)
    h = h * (1 - band) + 0.004 * band       # accent band: a flat wide-profile strip proud of the corrugation
    return _normal_png(h, tu / u.shape[1], tv / v.shape[0], path)


def pv_normal(path, size=512):
    tu, tv = TILES['dom_n_pv']
    u, v = _grid(size, size, tu, tv)
    h = np.minimum(_groove(_dist(u, 1.0), 0.025, 0.01), _groove(_dist(v, 2.0), 0.03, 0.012))
    return _normal_png(h, tu / size, tv / size, path)


def pv_colour(path, size=512):
    """PV modules 1.0 x 2.0 m: dark blue cells (0.156 m), white cell gaps, silver frames [inf]."""
    tu, tv = TILES['dom_c_pv']
    u, v = _grid(size, size, tu, tv)
    cell = ((_dist(u, 0.1666) < 0.006) | (_dist(v, 0.1666) < 0.006)).astype(float)
    frame = ((_dist(u, 1.0) < 0.02) | (_dist(v, 2.0) < 0.03)).astype(float)
    col = np.zeros(cell.shape + (3,)) + np.array([30, 38, 62.0])
    col = col * (1 - 0.6 * cell[..., None]) + np.array([120, 126, 140.0]) * 0.6 * cell[..., None]
    col = col * (1 - frame[..., None]) + np.array([170, 174, 178.0]) * frame[..., None]
    return _rgb_png(col, path)


def make_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    p = lambda k: os.path.join(out_dir, k + '.png')  # noqa: E731
    out = {k: curtain_colour(p(k), rgb) for k, rgb in CURTAIN_GLASS.items()}
    out.update({
        'dom_n_membrane': membrane(p('dom_n_membrane')),
        'dom_n_panel': panel(p('dom_n_panel')),
        'dom_n_curtain': curtain(p('dom_n_curtain'), CURTAIN, (6.0, 6.0)),
        'dom_n_t3w': curtain(p('dom_n_t3w'), T3W_GRID, TILES['dom_n_t3w'], phase_v=T3W_GRID[1]),
        'dom_n_corr': corrugation(p('dom_n_corr')),
        'dom_n_pv': pv_normal(p('dom_n_pv')),
        'dom_c_frit_grey': frit_grey(p('dom_c_frit_grey')),
        'dom_c_frit_green': frit_green(p('dom_c_frit_green')),
        'dom_c_t3w': curtain_colour(p('dom_c_t3w'), (98, 114, 124), T3W_GRID, TILES['dom_c_t3w'], phase_v=T3W_GRID[1]),
        'dom_c_pv': pv_colour(p('dom_c_pv')),
    })
    return out


if __name__ == '__main__':
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else 'out/buildings3d/dom_tex'))
