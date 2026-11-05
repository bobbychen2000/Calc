"""Procedural detail tiles of the ITB asset (tools/blender/build_itb.py): tangent-space normal maps (OpenGL / glTF
convention, +Y = +V) computed analytically from height fields (panel joints, membrane roll seams, mullion caps), and one
base-colour tile for the fritted glass. Baking the fine detail into mip-mapped textures instead of geometry avoids moire
(docs/research/engine.md 7.1). Our own procedural textures: no imagery of any kind is used.

One tile spans TILE metres of UV_detail (itb_geom lays UV_detail out in metres / tile):
  itb_n_membrane  512 x 512   12 x 12 m   roof membrane: roll seams every 3.0 m (single-ply rolls ~3 m wide) [inf]
                                          and a faint low-frequency undulation
  itb_n_panel     512 x 512   6.096 m sq  metal panels 3.048 x 1.524 m (10 x 5 ft) with 2-cm joints [module inf]
  itb_n_curtain   512 x 512   6.096 x 4.4 curtain-wall caps: verticals every 1.524 m (5 ft), horizontals every 2.2 m
                                          [obs photo i4: ~2.2 m transoms, low; 5-ft panes inf]
  itb_c_curtain_* 512 x 512   6.096 x 4.4 curtain-wall base colour (glass + light 6-cm caps on the itb_n_curtain grid) [inf]
                              (tinted end walls / clerestory, dark window bands; the round-0 pier tile is replaced by
                              itb_c_curtain_gate)
  itb_c_frit      256 x 256   3.6 x 3.6 m fritted glass: white frit bands on a 0.9-m period with a narrow clearer joint
                                          (BI-02 V1 draws the bands every 0.9 m) and a pane joint every 1.8 m [obs photo
                                          i4 banding, values inf]
  itb_n_frit      512 x 512   3.6 x 3.6 m normal map of the fritted bays, on the frit's own tile (review r1: the bays used
                                          itb_n_curtain, whose 1.524-m verticals land every 0.9 m on the 3.6-m frit tile and
                                          read as vertical stripes): horizontal transom caps at the 1.8-m pane joints, shallow
                                          vertical butt joints every 1.8 m (photo i3: horizontal frit bands and transoms,
                                          thin verticals ~2 bands apart) [obs photo i3, values inf]
  itb_c_curtain_gate 512 x 512 15.9 x 10.1 m BA-G gate-room curtain wall (photo a2, review r1): one tile = a quarter of the
                                          63.6-m bay x the full 4.6-14.7 m glazing; heavy mullion at the tile edge, a light
                                          one at mid-width, transoms every ~1.7 m and a deeper floor band at mid-height
                                          [obs photo a2, low]; glass = the material colour (a2 median sRGB 39 / 56 / 59)
"""
import os

import numpy as np
from PIL import Image

TILES = {   # name: (metres along U, metres along V)
    'itb_n_membrane': (12.0, 12.0),
    'itb_n_panel': (6.096, 6.096),
    'itb_n_curtain': (6.096, 4.4),
    'itb_c_frit': (3.6, 3.6),
    'itb_n_frit': (3.6, 3.6),
    'itb_c_curtain_gate': (15.9, 10.1),
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


def _groove(d, half_w, depth):
    x = np.clip(np.abs(d) / half_w, 0, 1)
    return -depth * (1 - x * x) ** 2


def _grid(W, H, tu, tv):
    u = (np.arange(W) + 0.5) / W * tu
    v = (1 - (np.arange(H) + 0.5) / H) * tv
    return u[None, :], v[:, None]


def _dist(x, period):
    r = np.mod(x, period)
    return np.minimum(r, period - r)


def membrane(path, size=512):
    tu, tv = TILES['itb_n_membrane']
    u, v = _grid(size, size, tu, tv)
    h = np.maximum(_groove(_dist(v, 3.0), 0.05, -0.004), 0) + 0 * u          # raised welded laps along u, every 3 m
    rng = np.random.default_rng(7)
    k = rng.normal(size=(8, 8))
    lo = np.array(Image.fromarray(((k - k.min()) / (np.ptp(k) + 1e-9) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC), float) / 255
    h = h + 0.002 * (lo - 0.5)
    return _normal_png(h, tu / size, tv / size, path)


def panel(path, size=512):
    tu, tv = TILES['itb_n_panel']
    u, v = _grid(size, size, tu, tv)
    h = np.minimum(_groove(_dist(u, 3.048), 0.02, 0.008), _groove(_dist(v, 1.524), 0.02, 0.008))
    return _normal_png(h, tu / size, tv / size, path)


def curtain(path, size=512):
    tu, tv = TILES['itb_n_curtain']
    u, v = _grid(size, size, tu, tv)
    cap = np.maximum(-_groove(_dist(u, 1.524), 0.05, 0.03), -_groove(_dist(v, 2.2), 0.05, 0.03))
    return _normal_png(cap, tu / size, tv / size, path)


def frit(path, size=256):
    """sRGB base colour: white frit 0.72 of each 0.9-m band, a clearer (darker) 0.18-m strip, pane joints every 1.8 m."""
    tu, tv = TILES['itb_c_frit']
    u, v = _grid(size, size, tu, tv)
    f = np.mod(v, 0.9) / 0.9
    band = np.where(f < 0.8, 1.0, 0.0) + 0 * u
    j = (_dist(u, 1.8) < 0.025).astype(float)
    base_w, base_c = np.array([214, 218, 220.0]), np.array([92, 104, 110.0])
    col = base_c[None, None, :] + (base_w - base_c)[None, None, :] * band[..., None]
    col = col * (1 - 0.35 * j[..., None])
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)
    return path


def frit_normal(path, size=512):
    """normal map on the frit tile (3.6 x 3.6 m): raised 5-cm transom caps every 1.8 m (horizontal pane joints, 2 bands
    per pane) and 1-cm-deep, 2-cm butt joints every 1.8 m (vertical, structural-silicone glazing). The vertical relief is
    kept small on purpose: horizontal structure dominates as in photos i3 / i4."""
    tu, tv = TILES['itb_n_frit']
    u, v = _grid(size, size, tu, tv)
    h = np.maximum(-_groove(_dist(v, 1.8), 0.05, 0.02), 0.0) + _groove(_dist(u, 1.8), 0.02, 0.004)
    return _normal_png(h, tu / size, tv / size, path)


def curtain_gate(path, glass_rgb, size=512, cap_rgb=(150, 156, 160)):
    """BA-G gate-room curtain wall tile (15.9 x 10.1 m, UV origin at the bay start / glazing foot): heavy mullion 0.30 m at
    u 0, light 0.12 m at u 7.95, transoms 0.08 m every 10.1 / 6 m, floor band 0.35 m at mid-height (photo a2) [obs, low]."""
    tu, tv = TILES['itb_c_curtain_gate']
    u, v = _grid(size, size, tu, tv)
    cap = ((_dist(u, tu) < 0.15) | (np.abs(u - tu / 2) < 0.06) | (_dist(v, tv / 6) < 0.04) | (np.abs(v - tv / 2) < 0.175))
    cap = cap.astype(float)
    col = np.array(glass_rgb, float)[None, None, :] * (1 - cap[..., None]) + np.array(cap_rgb, float)[None, None, :] * cap[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)
    return path


CURTAIN_GLASS = {   # base-colour curtain-wall tiles: glass colour (sRGB, = the material's) with light mullion caps
    'itb_c_curtain_tinted': (42, 56, 60),
    'itb_c_curtain_dark': (28, 33, 38),
}
GATE_GLASS = (38, 54, 56)   # glass_gate (photo a2 median 39 / 56 / 59) - build_itb.MATS['glass_gate']


def curtain_colour(path, glass_rgb, size=512, cap_rgb=(176, 180, 184)):
    """sRGB base colour of a curtain wall: glass with light aluminium caps every 1.524 m (vertical) and 2.2 m (horizontal),
    6 cm wide (same grid as itb_n_curtain) [inf]; mip-mapped, so the grid fades instead of aliasing at a distance."""
    tu, tv = TILES['itb_n_curtain']
    u, v = _grid(size, size, tu, tv)
    cap = ((_dist(u, 1.524) < 0.03) | (_dist(v, 2.2) < 0.03)).astype(float)
    col = np.array(glass_rgb, float)[None, None, :] * (1 - cap[..., None]) + np.array(cap_rgb, float)[None, None, :] * cap[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)
    return path


def make_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    extra = {k: curtain_colour(os.path.join(out_dir, k + '.png'), rgb) for k, rgb in CURTAIN_GLASS.items()}
    return {**extra,
        'itb_n_membrane': membrane(os.path.join(out_dir, 'itb_n_membrane.png')),
        'itb_n_panel': panel(os.path.join(out_dir, 'itb_n_panel.png')),
        'itb_n_curtain': curtain(os.path.join(out_dir, 'itb_n_curtain.png')),
        'itb_c_frit': frit(os.path.join(out_dir, 'itb_c_frit.png')),
        'itb_n_frit': frit_normal(os.path.join(out_dir, 'itb_n_frit.png')),
        'itb_c_curtain_gate': curtain_gate(os.path.join(out_dir, 'itb_c_curtain_gate.png'), GATE_GLASS),
    }


if __name__ == '__main__':
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else 'out/buildings3d/itb_tex'))
