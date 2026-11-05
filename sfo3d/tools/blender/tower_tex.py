"""Procedural detail tiles of the tower asset (tools/blender/build_tower.py): tangent-space normal maps (OpenGL / glTF
convention, +Y = +V = up the wall) generated analytically from groove / louvre height fields, so the panel joints and
louvres are baked into mip-mapped textures instead of geometry (no moire, docs/research/engine.md 7.1). Our own
procedural textures: no imagery of any kind is used.

Cladding tile = 4 joints x 2 panel rows (UV0 of the shaft: joints at u = k / 4, rows at v = k / 2, tower_geom.uv_clad):
  tile_panel_tower  1024 x 1024  normal map: helical joints and row joints as shallow grooves
                    [joints ~1.5-2 cm: inf; rows every 2.467 spec m and ~68 joints around: obs / inf, draw_tower]
  tile_clad_color   1024 x 1024  base colour (sRGB) of the same tile: dark joint lines (the recessed joint in shadow, as the
                    photos show it: t2 at 244 m, t4 at 81 m - dark diagonal and row lines ~1.5-2 px wide and ~30 % darker
                    than the panel at 0.026-0.071 m/px) and a +-5 % tone per panel (the faceted panels read as different
                    tones in t2 / t4) [obs look; line 6.5 cm (u: of a 0.70-m mean panel; 4.3 cm at the waist, 10 cm at the
                    flare) with 0.35 x the panel tone at its centre, and the per-panel tone, are inf: tuned so that the t4
                    render at 0.071 m/px shows the ~30 % dips of the photo]
  tile_slot_color   1024 x 1024  base colour (sRGB) of the flare-slot screens on the same 4 x 2 cladding tile (UV0 of the slot
                    cells): perforated metal, a staggered grid of round holes (dark: the void behind) on a mid-grey sheet
                    [perforated screen obs photo t4 (Famartin 2025-08-12 09:10, 81 m: a fine dot grid in every slot above its
                    glazed lowest pane); hole pitch ~0.05 m and diameter 0.022 m inf (the grid is ~2 px at 0.027 m/px); tone
                    tuned so that the slot / panel display ratio of the t2-matched render meets the photo's ~0.6-0.7 (review
                    round 2, finding 1: the slots rendered as black gashes, 0.1-0.3)]
  tile_louvre       256 x 256  SW wing: 4 horizontal louvre blades per 1.2 m (0.3 m pitch) + a joint every 1.5 m
                    [horizontally louvred face: obs photos t3 / t4; pitch inf]
  tile_panel_ibf    256 x 128  base-building metal panels 3.0 x 1.2 m [module inf]
"""
import numpy as np
from PIL import Image


def _normal_png(height, su, sv, path, strength=1.0):
    """height[r, c] with row 0 = TOP of the image (v = 1); su / sv = metres per pixel along u / v -> normal map PNG."""
    hp = np.pad(height, 1, mode='wrap')
    dhdu = (hp[1:-1, 2:] - hp[1:-1, :-2]) / (2 * su)
    dhdv = -(hp[2:, 1:-1] - hp[:-2, 1:-1]) / (2 * sv)        # rows run downwards; v runs upwards
    n = np.stack([-dhdu * strength, -dhdv * strength, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    img = np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    Image.fromarray(img, 'RGB').save(path, optimize=True)
    return path


def _groove(d, half_w, depth):
    """groove depth profile at distance d (m) from the joint line: rounded V, 0 outside half_w."""
    x = np.clip(np.abs(d) / half_w, 0, 1)
    return -depth * (1 - x * x) ** 2


CLAD_TU, CLAD_TV = 4, 2              # panels per tile (tower_geom.CLAD_TU / CLAD_TV)
PANEL_W, PANEL_H = 0.70, 2.62        # mean panel width (68 joints, r ~7.6 m) and row pitch (2.467 spec m x 1.063, F1), m


def _joint_dist(size):
    """distance (m) of every texel to the nearest helical joint (u) and row joint (v) of the 4 x 2 tile; panel index."""
    W, H = size
    u = (np.arange(W) + 0.5) / W * CLAD_TU; v = (1 - (np.arange(H) + 0.5) / H) * CLAD_TV
    fu, fv = u % 1.0, v % 1.0
    du = np.minimum(fu, 1 - fu)[None, :] * PANEL_W + 0 * v[:, None]
    dv = np.minimum(fv, 1 - fv)[:, None] * PANEL_H + 0 * u[None, :]
    pid = np.floor(v)[:, None].astype(int) * CLAD_TU + np.floor(u)[None, :].astype(int)
    return du, dv, pid


def panel_tower(path, size=(1024, 1024), joint_w=0.02, depth=0.003):
    """normal map of the 4 x 2 cladding tile: shallow rounded grooves at the joints (round 1 had 6 mm deep, 1.8 cm grooves
    at strength 1.5: their upper lips caught the sun as bright arcs; the photos show dark joints, carried by tile_clad_color)."""
    W, H = size
    du, dv, _ = _joint_dist(size)
    h = np.minimum(_groove(du, joint_w, depth), _groove(dv, joint_w, depth))
    return _normal_png(h, PANEL_W * CLAD_TU / W, PANEL_H * CLAD_TV / H, path)


def clad_color(path, rgb, size=(1024, 1024), line_w=0.065, line_k=0.35, tone=0.05, seed=7):
    """base-colour tile (sRGB PNG) of the 4 x 2 cladding tile: panel colour rgb (sRGB 0-255) with a +-tone linear variation
    per panel and dark joint lines (raised-cosine profile, full width line_w, linear colour x line_k at the centre).
    Returns the path and the tile's mean colour (sRGB), i.e. what the cladding reads as from afar (mip-mapped)."""
    W, H = size
    du, dv, pid = _joint_dist(size)
    lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    srgb = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055)
    base = lin(np.asarray(rgb, float) / 255.0)
    rng = np.random.default_rng(seed)
    f = 1.0 + tone * (2 * rng.random(CLAD_TU * CLAD_TV) - 1)
    img = base[None, None, :] * f[pid][..., None]
    d = np.minimum(du, dv)
    w = np.where(d < line_w / 2, 0.5 * (1 + np.cos(np.pi * d / (line_w / 2))), 0.0)
    img = img * (1 - (1 - line_k) * w)[..., None]
    out = np.clip(np.round(srgb(img) * 255), 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGB').save(path, optimize=True)
    mean = srgb(img.reshape(-1, 3).mean(0)) * 255
    return path, [round(float(x), 1) for x in mean]


def slot_color(path, rgb, size=(1024, 1024), n_u=56, n_v=104, hole_d=0.022, hole_k=0.18):
    """base-colour tile (sRGB PNG) of the perforated slot screens on the 4 x 2 cladding tile (2.8 x 5.24 m): sheet colour
    rgb (sRGB 0-255), round holes on a staggered grid (n_u x n_v per tile: ~0.05 m pitch; alternate rows shifted by half a
    pitch), linear colour x hole_k inside a hole (the dark void behind), anti-aliased over one texel. Integer counts per
    tile so that the tile repeats seamlessly. Returns the path and the tile's mean colour (sRGB)."""
    W, H = size
    lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    srgb = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055)
    su, sv = PANEL_W * CLAD_TU / W, PANEL_H * CLAD_TV / H          # metres per texel
    pu, pv = PANEL_W * CLAD_TU / n_u, PANEL_H * CLAD_TV / n_v       # hole pitch along u / v, m
    x = (np.arange(W) + 0.5) * su; y = (np.arange(H) + 0.5) * sv
    X, Y = np.meshgrid(x, y)
    row = np.floor(Y / pv)
    fx = ((X / pu - 0.5 * (row % 2)) % 1.0 - 0.5) * pu
    fy = ((Y / pv) % 1.0 - 0.5) * pv
    d = np.hypot(fx, fy)
    aa = 0.75 * max(su, sv)
    hole = np.clip((hole_d / 2 + aa - d) / (2 * aa), 0, 1)
    base = lin(np.asarray(rgb, float) / 255.0)
    img = base[None, None, :] * (1 - (1 - hole_k) * hole)[..., None]
    out = np.clip(np.round(srgb(img) * 255), 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGB').save(path, optimize=True)
    mean = srgb(img.reshape(-1, 3).mean(0)) * 255
    return path, [round(float(c), 1) for c in mean]


def louvre(path, size=(256, 256), w=1.5, h=1.2, blades=4, joint_w=0.02, depth=0.035):
    W, H = size
    u = (np.arange(W) + 0.5) / W; v = 1 - (np.arange(H) + 0.5) / H
    f = (v * blades) % 1.0                                      # 0 at a blade's foot, 1 at its head
    # blade face slopes outwards towards its foot (sheds rain); a short return at the head
    prof = np.where(f < 0.85, -depth * f / 0.85, -depth * (1 - (f - 0.85) / 0.15))
    hgt = np.repeat(prof[:, None], W, 1)
    du = np.minimum(u, 1 - u)[None, :] * w
    hgt = np.minimum(hgt, _groove(du, joint_w, 0.01) + 0 * hgt)
    return _normal_png(hgt, w / W, h / H, path)


def panel_ibf(path, size=(256, 128), w=3.0, h=1.2, joint_w=0.02, depth=0.008):
    W, H = size
    u = (np.arange(W) + 0.5) / W; v = 1 - (np.arange(H) + 0.5) / H
    du = np.minimum(u, 1 - u)[None, :] * w; dv = np.minimum(v, 1 - v)[:, None] * h
    hgt = np.minimum(_groove(du, joint_w, depth), _groove(dv, joint_w, depth))
    return _normal_png(hgt, w / W, h / H, path)


def make_all(out_dir, clad_rgb=None, slot_rgb=None):
    """normal tiles (+ the cladding / slot-screen base-colour tiles when clad_rgb / slot_rgb are given); returns {name: path}
    and, under '_clad_mean' / '_slot_mean', the tiles' mean sRGB colours."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    out = {
        'tile_panel_tower': panel_tower(os.path.join(out_dir, 'tile_panel_tower.png')),
        'tile_louvre': louvre(os.path.join(out_dir, 'tile_louvre.png')),
        'tile_panel_ibf': panel_ibf(os.path.join(out_dir, 'tile_panel_ibf.png')),
    }
    if clad_rgb is not None:
        out['tile_clad_color'], out['_clad_mean'] = clad_color(os.path.join(out_dir, 'tile_clad_color.png'), clad_rgb)
    if slot_rgb is not None:
        out['tile_slot_color'], out['_slot_mean'] = slot_color(os.path.join(out_dir, 'tile_slot_color.png'), slot_rgb)
    return out


if __name__ == '__main__':
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else 'out/buildings3d/tex', clad_rgb=(152, 156, 162), slot_rgb=(122, 126, 131)))
