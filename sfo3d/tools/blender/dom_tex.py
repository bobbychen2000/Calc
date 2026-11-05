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
  dom_c_glass_ec  1024x256 24 x 6 m  BA-B electrochromic glass: per-pane tint states (EC_STATES) + caps (review r1) [inf]
  dom_n_curtain24 1024x256 24 x 6 m  the curtain caps on that tile
  dom_c_frit_grey  512    6 x 6 m    BA-E "clear glass with grey frit" [pub bae.facade]: horizontal frit lines [pattern inf]
  dom_c_frit_green 512x512 12 x 9 m  T1 Center landside upper tiers: green frit with the vertical striation of photo d1 and the
                                     tier transom 44 % up (draw_domestic.T1_SPLIT) [obs photo d1, schematic]; NO regular
                                     verticals (the irregular mullions are LOD0 fins, draw_domestic.t1_mullions)
  dom_c_t3w        512    6 x 5.8 m  T3 West fritted IGU window wall (light blue-grey) with its caps [pub materials, module unk]
  dom_c_pv         512    4 x 4 m    PV cells (dark blue) with silver module frames [inf]
  dom_c_glass_c3c 1024    24 x 22.8 m  Courtyard 3 Connector office curtain wall (review r2): six storeys of storey-height panes,
                                     the vertical mullions STAGGERED from floor to floor (pane widths 1.2-4.5 m, a new random
                                     sequence per storey), light frames (0.24-m floor-line horizontals, 0.10-m verticals), very
                                     dark green glass with a subtle per-pane variation (+-4 %) [obs photo a1: rhythm and colours;
                                     widths inf]
  dom_n_c3c       1024    24 x 22.8 m  its frame caps
  dom_n_louvre     256    3 x 3 m    C3C penthouse louvre band: horizontal blades every 0.15 m [inf; band obs photo a1]
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
    'dom_c_glass_ec': (24.0, 6.0),
    'dom_n_curtain24': (24.0, 6.0),
    'dom_c_glass_c3c': (24.0, 22.8),     # review r2: C3C office curtain wall, 6 storeys x 3.8 m (dom_geom.C3C_STOREY)
    'dom_n_c3c': (24.0, 22.8),
    'dom_n_louvre': (3.0, 3.0),           # review r2: C3C penthouse louvre blades
}
CURTAIN = (1.5, 3.0)            # vertical / transom pitch of the generic curtain grid [inf] (dom_geom.MULL = 1.5)
T3W_GRID = (2.0, 3.5)           # T3W: vertical pitch 2.0 m (BD-03 schematic), transom 3.5 m above the band bottom [unk]
T1_TRANSOM = 0.44 * 9.0         # draw_domestic.T1_SPLIT x (T1_HEAD - T1_CANOPY) = 3.96 m above the canopy line [inf photo d1]
CAP_RGB = (176, 180, 184)       # aluminium caps (sRGB) [inf]

CURTAIN_GLASS = {   # base-colour curtain tiles: glass colour (sRGB, = the material's base colour) with light caps
    'dom_c_glass_ec': (44, 58, 70),        # BA-B electrochromic glass (tinted state varies; mid value) [pub glazing, colour inf]
    'dom_c_glass_lowe': (66, 82, 92),      # clerestories / lantern / monitor [inf]
    'dom_c_glass_tint': (40, 54, 58),      # generic tinted gate-room glass (BA-C / D / F, halls airside) [unk]
    'dom_c_glass_clear': (30, 36, 40),     # clear glass: BA-E end wall (dark: unlit interior) [obs photo a1]
    'dom_c_glass_lobby': (112, 120, 122),  # clear glass under the T1 canopy: the lit ticket hall seen through it reads mid-grey
                                           # (photo d1; review r1 - it rendered black) [obs photo d1, value inf; as the ITB glass_hall]
}
# BA-B electrochromic glass (review r1: a uniform near-black band): every 1.5 x 3.0 m pane in one of four tint states (EC glass
# is zoned and tints per pane / zone with the sun) [pub electrochromic, states inf]: sRGB per state and its share
EC_STATES = (((86, 104, 114), 0.30), ((66, 82, 94), 0.35), ((50, 64, 76), 0.25), ((36, 46, 58), 0.10))


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


def curtain_rect(path, pitch, tile, w=1024, h=256):
    """curtain caps normal map on a non-square tile (the 24 x 6 m EC glass tile)."""
    tu, tv = tile
    u, v = _grid(w, h, tu, tv)
    cap = np.maximum(-_groove(_dist(u, pitch[0]), 0.05, 0.03), -_groove(_dist(v, pitch[1]), 0.05, 0.03))
    return _normal_png(cap, tu / w, tv / h, path)


def curtain_colour(path, glass_rgb, pitch=CURTAIN, tile=(6.0, 6.0), size=512, phase_v=0.0):
    tu, tv = tile
    u, v = _grid(size, size, tu, tv)          # square pixels not needed: 512 x 512 for any tile aspect
    cap = ((_dist(u, pitch[0]) < 0.03) | (_dist(v, pitch[1], phase_v) < 0.03)).astype(float)
    col = np.array(glass_rgb, float)[None, None, :] * (1 - cap[..., None]) + np.array(CAP_RGB, float)[None, None, :] * cap[..., None]
    return _rgb_png(col, path)


def ec_colour(path, w=1024, h=256, seed=23):
    """BA-B electrochromic curtain glass, 24 x 6 m tile (16 x 2 panes on the 1.5 x 3.0 m grid): per-pane tint state
    (EC_STATES), a faint vertical reflectance gradient per pane (+-4 %), light caps [inf]."""
    tu, tv = TILES['dom_c_glass_ec']
    u, v = _grid(w, h, tu, tv)
    rng = np.random.default_rng(seed)
    nu, nv = int(round(tu / CURTAIN[0])), int(round(tv / CURTAIN[1]))
    cols = np.array([c for c, _ in EC_STATES], float); p = np.array([q for _, q in EC_STATES]); p = p / p.sum()
    st = rng.choice(len(cols), size=(nv, nu), p=p)
    iu = np.clip((u / CURTAIN[0]).astype(int), 0, nu - 1) + 0 * v.astype(int)
    iv = np.clip((v / CURTAIN[1]).astype(int), 0, nv - 1) + 0 * u.astype(int)
    col = cols[st[iv, iu]]
    fv = np.mod(v, CURTAIN[1]) / CURTAIN[1] + 0 * u
    col = col * (0.96 + 0.08 * fv)[..., None]
    cap = ((_dist(u, CURTAIN[0]) < 0.03) | (_dist(v, CURTAIN[1]) < 0.03)).astype(float)
    col = col * (1 - cap[..., None]) + np.array(CAP_RGB, float)[None, None, :] * cap[..., None]
    return _rgb_png(col, path)


C3C_GLASS = (26, 40, 35)            # sRGB: very dark green (photo a1 median of the glazed face 22 / 32 / 31 incl. ~10 % frames,
                                    # overcast) [obs, low]
C3C_FRAME = (184, 190, 188)         # light aluminium frames (photo a1 ~125 / 132 / 132 under overcast, ~0.7 of the light panels) [obs, low]
C3C_PANES = ((1.2, 0.25), (2.4, 0.30), (3.0, 0.25), (3.6, 0.12), (4.5, 0.08))   # pane width (m), share [inf: photo a1 8x zoom]
C3C_FRAME_H, C3C_FRAME_V = 0.24, 0.10


def c3c_layout(seed=31, storeys=6, storey=3.8, tu=24.0):
    """per storey: the mullion positions (m, 0..tu, wrapping) - a random pane-width sequence with a random start, so that the
    verticals do not line up from floor to floor (photo a1); the last pane is stretched to close the tile seamlessly."""
    rng = np.random.default_rng(seed)
    ws = np.array([w for w, _ in C3C_PANES]); p = np.array([q for _, q in C3C_PANES]); p = p / p.sum()
    out = []
    for k in range(storeys):
        xs, x = [], 0.0
        while x < tu - 1.0:
            xs.append(x); x += float(rng.choice(ws, p=p))
        off = float(rng.uniform(0, tu))
        out.append(sorted(((xx + off) % tu) for xx in xs))
    return out


def _c3c_fields(w, h, seed=31):
    tu, tv = TILES['dom_c_glass_c3c']
    u, v = _grid(w, h, tu, tv)
    st = 3.8
    lay = c3c_layout(seed)
    k = np.clip((v / st).astype(int), 0, len(lay) - 1) + 0 * u.astype(int)          # storey index (v from the band bottom)
    hz = (_dist(v, st) < C3C_FRAME_H / 2).astype(float) + 0 * u                       # floor-line frames
    vert = np.zeros(k.shape); pane = np.zeros(k.shape, int)
    for i, xs in enumerate(lay):
        m = (k == i)
        X = np.array(xs)
        uu = np.broadcast_to(u, k.shape)[m]
        d = np.abs(((uu[:, None] - X[None, :]) + tu / 2) % tu - tu / 2).min(1)
        vert[m] = (d < C3C_FRAME_V / 2).astype(float)
        idx = np.searchsorted(X, uu, side='right') % len(X)
        pane[m] = idx + 100 * i
    return u, v, hz, vert, pane


def c3c_colour(path, w=1024, h=1024, seed=31):
    u, v, hz, vert, pane = _c3c_fields(w, h, seed)
    rng = np.random.default_rng(seed + 1)
    var = {p_: 1.0 + rng.uniform(-0.04, 0.04) for p_ in np.unique(pane)}
    f = np.vectorize(var.get)(pane)
    fv = np.mod(v, 3.8) / 3.8 + 0 * u
    col = np.array(C3C_GLASS, float)[None, None, :] * (f * (1.03 - 0.06 * fv))[..., None]     # slightly lighter low in a pane
    fr = np.clip(hz + vert, 0, 1)
    col = col * (1 - fr[..., None]) + np.array(C3C_FRAME, float)[None, None, :] * fr[..., None]
    return _rgb_png(col, path)


def c3c_normal(path, w=1024, h=1024, seed=31):
    u, v, hz, vert, pane = _c3c_fields(w, h, seed)
    tu, tv = TILES['dom_n_c3c']
    hgt = 0.03 * np.clip(hz + vert, 0, 1)
    import cv2
    hgt = cv2.GaussianBlur(hgt.astype(np.float32), (5, 5), 1.0)
    return _normal_png(hgt, tu / w, tv / h, path)


def louvre_normal(path, size=256):
    tu, tv = TILES['dom_n_louvre']
    u, v = _grid(size, size, tu, tv)
    h = 0.03 * (np.mod(v, 0.15) / 0.15) + 0 * u        # sawtooth: blades tilted down-out
    return _normal_png(h, tu / size, tv / size, path)


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
    tr = (np.abs(v - T1_TRANSOM) < 0.08).astype(float) + 0 * u
    col = col * (1 - tr[..., None]) + np.array([52, 60, 56.0])[None, None, :] * tr[..., None]
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
    out = {k: curtain_colour(p(k), rgb) for k, rgb in CURTAIN_GLASS.items() if k != 'dom_c_glass_ec'}
    out['dom_c_glass_ec'] = ec_colour(p('dom_c_glass_ec'))
    out['dom_n_curtain24'] = curtain_rect(p('dom_n_curtain24'), CURTAIN, TILES['dom_n_curtain24'])
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
        'dom_c_glass_c3c': c3c_colour(p('dom_c_glass_c3c')),
        'dom_n_c3c': c3c_normal(p('dom_n_c3c')),
        'dom_n_louvre': louvre_normal(p('dom_n_louvre')),
    })
    return out


if __name__ == '__main__':
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else 'out/buildings3d/dom_tex'))
