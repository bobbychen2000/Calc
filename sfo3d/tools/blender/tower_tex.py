"""Procedural detail tiles of the tower asset (tools/blender/build_tower.py): tangent-space normal maps (OpenGL / glTF
convention, +Y = +V = up the wall) generated analytically from groove / louvre height fields, so the panel joints and
louvres are baked into mip-mapped textures instead of geometry (no moire, docs/research/engine.md 7.1). Our own
procedural textures: no imagery of any kind is used.

One tile = one cladding panel (UV0 of the asset is laid out so that joints fall on integer u / v):
  tile_panel_tower  256 x 512  ACM panel: vertical (helical) joint at u = 0, circumferential row joint at v = 0
                    [joints ~1.5-2 cm: inf; rows every 2.467 spec m and ~68 joints around: obs / inf, draw_tower]
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


def panel_tower(path, size=(256, 512), panel_w=0.70, panel_h=2.62, joint_w=0.018, depth=0.006):
    W, H = size
    u = (np.arange(W) + 0.5) / W; v = 1 - (np.arange(H) + 0.5) / H
    du = np.minimum(u, 1 - u)[None, :] * panel_w; dv = np.minimum(v, 1 - v)[:, None] * panel_h
    h = np.minimum(_groove(du, joint_w, depth), 0) + np.minimum(_groove(dv, joint_w, depth), 0)
    h = np.minimum(h, 0) + 0 * u[None, :]
    h = np.maximum(h, -depth * 1.2)
    return _normal_png(h, panel_w / W, panel_h / H, path)


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


def make_all(out_dir):
    import os
    os.makedirs(out_dir, exist_ok=True)
    return {
        'tile_panel_tower': panel_tower(os.path.join(out_dir, 'tile_panel_tower.png')),
        'tile_louvre': louvre(os.path.join(out_dir, 'tile_louvre.png')),
        'tile_panel_ibf': panel_ibf(os.path.join(out_dir, 'tile_panel_ibf.png')),
    }


if __name__ == '__main__':
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else 'out/buildings3d/tex'))
