"""Procedural detail tiles of the landside asset (tools/blender/build_landside.py): tangent-space normal maps (OpenGL /
glTF convention, +Y = +V) computed analytically from height fields, and base-colour tiles. Our own procedural textures:
no imagery of any kind is used (NAIP 2024 only gives the roof / deck colour FACTORS, build_landside.naip_colours).
Fine detail (panel joints, corrugation, slots, louvres, stall lines) lives in mip-mapped textures instead of geometry so it
does not shimmer (moire) at a distance (docs/research/engine.md 7.1).

One tile spans the metres given in landside_geom.TILES of UV_detail (the geometry lays UV_detail out in metres / tile):
  ls_n_precast      6 x 3 m      architectural precast panels 3.0 x 1.5 m, 2-cm joints [obs photo l1 grid; module inf]
  ls_n_band         6 x 1.6 m    helix-drum bands: horizontal joints every 1.6 m, verticals every 3 m [obs l1 / a2; inf]
  ls_n_board        4 x 2.4 m    board-formed concrete: 0.15-m boards, faint form-tie dots [obs photo l5; module inf]
  ls_c/n_screen     1 panel      perforated metal panel with horizontal slots and a frame [obs photo l1; slot pitch inf]
  ls_n_corrugated   2 x 2 m      trapezoidal metal cladding, 0.20 m pitch, vertical ribs [inf]
  ls_c/n_louvre     3 x 1 m      canted louvre screen: horizontal green-grey blades with dark gaps [obs photo l5]
  ls_c_ribbon       3 x 3 m      ribbon windows: dark glass, mullions every 1.5 m, transom at 2.2 m [obs l5; inf]
  ls_c_hyatt        1.5 x 3.33 m one curtain-wall pane x one floor: blue-green glass, spandrel band, caps [obs photo l4]
  ls_c_glassband    3 x 1.11 m   curved end bay of the Hyatt: horizontal glass bands [obs l4]
  ls_c_cac          3 x 4.572 m  CAC: light panels, one 1.8-m window band per 15-ft floor (reduced window-to-wall [pub]) [inf]
  ls_c_deck         10.4 x 18.6  parking deck: 4 stalls (2.6 m) x one module (5.5 + 7.6 + 5.5 m), white stall lines [inf]
  ls_c_lanes        12 x 11.2 m  RCC ready-return lanes: 4 lanes of 3 m, lane lines, two car pitches [obs NAIP lanes; inf]
  ls_c/n_door       one leaf     hangar door leaf: horizontal panels, leaf edges [inf]
  ls_n_roof         6 x 6 m      standing-seam metal roof, seams every 0.6 m [inf]
  ls_c_pv           4 x 4 m      PV modules 1.0 x 2.0 m, cells [pub PV; layout inf]
  ls_c_glass        3 x 3 m      station glazing: mullions 1.5 m, transom 2.4 m [obs photos; inf]
  ls_c_perf         3 x 3 m      perforated-metal tower skin with frame members [obs photo l5]
  ls_c_spine        3 x 3.6 m    Superbay spine end faces: one office floor, window band [pub 6 levels; inf]
  ls_n_concrete     8 x 8 m      cast concrete: faint pour joints [inf]
"""
import os

import numpy as np
from PIL import Image


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
    return u[None, :] + 0 * v[:, None], v[:, None] + 0 * u[None, :]


def _dist(x, period, off=0.0):
    r = np.mod(x - off, period)
    return np.minimum(r, period - r)


def _noise(W, H, k=8, seed=1):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(k, k))
    a = np.array(Image.fromarray(((a - a.min()) / (np.ptp(a) + 1e-9) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), float) / 255
    return a - 0.5


def mix(a, b, t):
    return np.asarray(a, float)[None, None, :] * (1 - t[..., None]) + np.asarray(b, float)[None, None, :] * t[..., None]


def make_all(out):
    os.makedirs(out, exist_ok=True)
    P = lambda n: os.path.join(out, n + '.png')
    T = {}
    # --- normal maps
    u, v = _grid(512, 256, 6.0, 3.0)
    T['ls_n_precast'] = _normal_png(np.minimum(_groove(_dist(u, 3.0), 0.02, 0.01), _groove(_dist(v, 1.5), 0.02, 0.01)), 6 / 512, 3 / 256, P('ls_n_precast'))
    u, v = _grid(512, 256, 6.0, 1.6)
    T['ls_n_band'] = _normal_png(np.minimum(_groove(_dist(v, 1.6), 0.03, 0.015), _groove(_dist(u, 3.0), 0.015, 0.006)), 6 / 512, 1.6 / 256, P('ls_n_band'))
    u, v = _grid(256, 256, 4.0, 2.4)
    h = 0.002 * np.sin(2 * np.pi * v / 0.15) + _groove(_dist(v, 0.15), 0.006, 0.002) + 0.003 * _noise(256, 256, 16, 3)
    h = np.minimum(h, _groove(np.hypot(_dist(u, 0.6), _dist(v, 0.6, 0.3)), 0.012, 0.006))
    T['ls_n_board'] = _normal_png(h, 4 / 256, 2.4 / 256, P('ls_n_board'))
    u, v = _grid(256, 256, 2.0, 2.0)
    T['ls_n_corrugated'] = _normal_png(0.018 * np.clip(np.sin(2 * np.pi * u / 0.2) * 1.6, -1, 1), 2 / 256, 2 / 256, P('ls_n_corrugated'), 0.7)
    u, v = _grid(256, 256, 6.0, 6.0)
    T['ls_n_roof'] = _normal_png(-_groove(_dist(u, 0.6), 0.02, 0.012) + 0.002 * _noise(256, 256, 8, 4), 6 / 256, 6 / 256, P('ls_n_roof'))
    u, v = _grid(256, 256, 8.0, 8.0)
    T['ls_n_concrete'] = _normal_png(np.minimum(_groove(_dist(u, 8.0), 0.012, 0.006), _groove(_dist(v, 8.0), 0.012, 0.006)) + 0.002 * _noise(256, 256, 12, 5),
                                     8 / 256, 8 / 256, P('ls_n_concrete'))
    # --- perforated screen panel (UV 0..1 = one panel): frame 4 % of the panel, horizontal slots (dark) every 1/14
    u, v = _grid(256, 256, 1.0, 1.0)
    fr = (np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) < 0.035).astype(float)
    slot = ((_dist(v, 1 / 14.0, 0.5 / 14) < 0.022) & (_dist(u, 1 / 6.0, 1 / 12.0) < 0.078)).astype(float) * (1 - fr)
    # perforation (fine holes, unresolved) darkens the metal between the slots: the dark interior shows through [obs l1 / a2]
    T['ls_c_screen'] = _rgb_png(mix((196, 198, 198), (40, 42, 45), slot * 0.95) * (1 - 0.04 * fr[..., None]), P('ls_c_screen'))
    T['ls_n_screen'] = _normal_png(-0.01 * slot + 0.006 * fr, 3 / 256, 1.6 / 256, P('ls_n_screen'))
    # --- louvre screen (3 x 1 m): blades 0.42 m, gaps 0.18 m (two blades per metre is too fine at 1:1000; l5: ~0.6 m pitch)
    u, v = _grid(256, 128, 3.0, 1.0)
    ph = np.mod(v, 0.6) / 0.6
    gap = (ph < 0.25).astype(float)
    shade = 0.85 + 0.15 * ph
    col = mix((128, 146, 140), (30, 34, 34), gap) * np.where(gap > 0, 1.0, shade)[..., None]
    T['ls_c_louvre'] = _rgb_png(col, P('ls_c_louvre'))
    T['ls_n_louvre'] = _normal_png(0.04 * ph * (1 - gap), 3 / 256, 1.0 / 128, P('ls_n_louvre'))
    # --- ribbon windows (3 x 3 m, window head at 3.0 from the band bottom)
    u, v = _grid(256, 256, 3.0, 3.0)
    cap = ((_dist(u, 1.5) < 0.05) | (_dist(v, 3.0) < 0.06) | (np.abs(v - 2.2) < 0.04)).astype(float)
    T['ls_c_ribbon'] = _rgb_png(mix((40, 50, 56), (150, 156, 160), cap) + 6 * _noise(256, 256, 6, 7)[..., None], P('ls_c_ribbon'))
    # --- Hyatt curtain wall (1.5 x 3.333 m): spandrel 0.95 m at the floor line, glass above, caps 5 cm
    p = 44.0 / 13.2
    u, v = _grid(128, 256, 1.5, p)
    sp = (v < 0.95).astype(float)
    capm = ((_dist(u, 1.5) < 0.03) | (_dist(v, p) < 0.04) | (np.abs(v - 0.95) < 0.02)).astype(float)
    glass = (58, 112, 116); spand = (44, 78, 82); capc = (150, 166, 168)
    col = mix(glass, spand, sp)
    col = col * (1 - capm[..., None]) + np.array(capc)[None, None, :] * capm[..., None]
    T['ls_c_hyatt'] = _rgb_png(col, P('ls_c_hyatt'))
    u, v = _grid(256, 128, 3.0, p / 3)
    band = (_dist(v, p / 3) < 0.05).astype(float)
    T['ls_c_glassband'] = _rgb_png(mix((96, 140, 146), (170, 186, 188), band), P('ls_c_glassband'))
    # --- CAC panels with a window band per 15-ft floor (3 x 4.572 m)
    u, v = _grid(256, 384, 3.0, 4.572)
    win = ((v > 1.1) & (v < 2.9)).astype(float)
    mull = (_dist(u, 1.5) < 0.04).astype(float) * win
    joint = ((_dist(u, 3.0) < 0.015) | (_dist(v, 4.572) < 0.015) | (np.abs(v - 1.1) < 0.012) | (np.abs(v - 2.9) < 0.012)).astype(float)
    col = mix((214, 210, 200), (46, 58, 66), win)
    col = col * (1 - 0.55 * mull[..., None]) * (1 - 0.18 * joint[..., None])
    T['ls_c_cac'] = _rgb_png(col, P('ls_c_cac'))
    # --- parking decks (white base: the NAIP deck colour is the material factor; lines 1.25 x brighter, clamped)
    u, v = _grid(512, 512, 10.4, 18.6)
    st = (v < 5.5) | (v > 18.6 - 5.5)
    line = ((_dist(u, 2.6) < 0.06) & st).astype(float)
    stain = np.exp(-(((_dist(u, 2.6, 1.3)) / 0.5) ** 2 + ((np.minimum(_dist(v, 18.6, 2.2), _dist(v, 18.6, 16.4))) / 0.9) ** 2)) * st
    base = 0.80 + 0.03 * _noise(512, 512, 10, 9)
    g = np.clip(base - 0.07 * stain, 0, 1) * (1 - line) + 1.0 * line
    T['ls_c_deck'] = _rgb_png(np.repeat((g * 255)[..., None], 3, -1), P('ls_c_deck'))
    u, v = _grid(512, 512, 12.0, 11.2)
    line = (_dist(u, 3.0) < 0.06).astype(float)
    base = 0.80 + 0.03 * _noise(512, 512, 10, 10)
    g = base * (1 - line) + 1.0 * line
    T['ls_c_lanes'] = _rgb_png(np.repeat((g * 255)[..., None], 3, -1), P('ls_c_lanes'))
    # --- hangar door leaf (UV 0..1 across one leaf, v metres / door height): panels every 1.2 m, leaf edges
    u, v = _grid(256, 512, 1.0, 1.0)
    edge = (np.minimum(u, 1 - u) < 0.012).astype(float)
    pj = (_dist(v, 1.0 / 20) < 0.0025).astype(float)
    col = (np.array([168, 170, 168.0])[None, None, :] * (1 - 0.35 * edge[..., None]) * (1 - 0.12 * pj[..., None]))
    T['ls_c_door'] = _rgb_png(col + 3 * _noise(256, 512, 6, 11)[..., None], P('ls_c_door'))
    T['ls_n_door'] = _normal_png(_groove(np.minimum(u, 1 - u), 0.012, 0.02) + _groove(_dist(v, 1 / 20.0), 0.003, 0.01), 8.25 / 256, 24 / 512, P('ls_n_door'))
    # --- PV (4 x 4 m): modules 1.0 x 2.0 m, frames, cell grid
    u, v = _grid(256, 256, 4.0, 4.0)
    fr = ((_dist(u, 1.0) < 0.025) | (_dist(v, 2.0) < 0.025)).astype(float)
    cell = ((_dist(u, 1 / 6.0) < 0.006) | (_dist(v, 2 / 12.0) < 0.006)).astype(float)
    col = mix((26, 36, 58), (60, 70, 90), cell * 0.6)
    col = col * (1 - fr[..., None]) + np.array([170, 172, 176.0])[None, None, :] * fr[..., None]
    T['ls_c_pv'] = _rgb_png(col, P('ls_c_pv'))
    # --- station glazing (3 x 3 m)
    u, v = _grid(256, 256, 3.0, 3.0)
    cap = ((_dist(u, 1.5) < 0.04) | (np.abs(v - 2.4) < 0.04) | (v < 0.08)).astype(float)
    T['ls_c_glass'] = _rgb_png(mix((70, 92, 100), (190, 194, 196), cap), P('ls_c_glass'))
    # --- perforated tower skin (3 x 3 m): perforation = mid-grey, frame members every 1.5 m / 3 m (lighter)
    u, v = _grid(256, 256, 3.0, 3.0)
    fr = ((_dist(u, 1.5) < 0.05) | (_dist(v, 3.0) < 0.06)).astype(float)
    T['ls_c_perf'] = _rgb_png(mix((132, 128, 116), (196, 198, 198), fr) + 6 * _noise(256, 256, 24, 12)[..., None], P('ls_c_perf'))
    # --- Superbay spine end face: office floor 3.6 m, window band 1.0-2.6 m
    u, v = _grid(256, 256, 3.0, 3.6)
    win = ((v > 1.0) & (v < 2.6)).astype(float)
    mull = (_dist(u, 1.5) < 0.04).astype(float) * win
    col = mix((206, 204, 196), (44, 52, 58), win) * (1 - 0.5 * mull[..., None])
    T['ls_c_spine'] = _rgb_png(col, P('ls_c_spine'))
    return T


if __name__ == '__main__':
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else 'out/buildings3d/landside_tex'))
