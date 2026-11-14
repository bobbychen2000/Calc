# OD4 (owner request 2026-11-14): side-by-side comparison of the pc12 project's own three.js viewer (reference) with the
# hwd3d renderer at the same cameras, plus pixel read-backs of the materials the reference look depends on.
#   python3 -I -B tools/models/pc12/look_compare.py --ref=out/pc12_ref_viewer/shots --hwd=out/pc12_look/after \
#       --out=out/pc12_look [--tag=after] [--refkind=dev]
# Inputs: <ref>/<refkind>_<cam>.png (out/pc12_ref_viewer/render_ref.mjs) and <hwd>/hwd_<cam>.png (dev/model_shot.mjs
# --jobs=out/pc12_look/jobs_ref.json --format=png). Writes <out>/cmp_<tag>_<cam>.jpg (reference | hwd3d, 1920 x 540, labelled)
# and <out>/measure_<tag>.json: for each camera, the median sRGB of the pixels of each material class (navy cheatline, gold
# pin-stripe, near-black trim / glass / seals / tyres, white paint), classified by colour in the REFERENCE image and read at
# the same pixels in both (identical cameras).
# Read-only on everything but <out>. Pillow + numpy only.
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('--ref', required=True); ap.add_argument('--hwd', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--tag', default='after'); ap.add_argument('--refkind', default='dev')
ap.add_argument('--cams', default='front34,side,rear34,cockpit,nose,tail,hwd_front34,hwd_rear34,hwd_side,hwd_nose,hwd_tail')
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)


def classes(img):
    """boolean masks of the livery / trim classes by colour (sRGB 8-bit). Navy: blue-dominant, darker than 140 and clearly
    bluer than grey; gold: R > B + 30 and G > B + 20 (the brass pin-stripe); dark: all channels < 60 (trim_black, seals,
    glass, tyres); white: all > 150 and channel spread < 18."""
    f = img.astype(np.int32); r, g, b = f[..., 0], f[..., 1], f[..., 2]
    mx, mn = f.max(-1), f.min(-1)
    navy = (b > r + 18) & (b > g + 6) & (b < 200) & (mx < 200)
    gold = (r > b + 30) & (g > b + 20) & (r > 60)
    dark = mx < 60
    white = (mn > 150) & (mx - mn < 18)
    return {'navy': navy, 'gold': gold, 'dark': dark, 'white': white}


def stats(img, mask):
    n = int(mask.sum())
    if n < 20: return {'n': n}
    px = img[mask]
    return {'n': n, 'median': [int(v) for v in np.median(px, 0)], 'p90': [int(v) for v in np.percentile(px, 90, 0)], 'p10': [int(v) for v in np.percentile(px, 10, 0)]}


out = {}
for cam in [c for c in a.cams.split(',') if c]:
    fr, fh = os.path.join(a.ref, f'{a.refkind}_{cam}.png'), os.path.join(a.hwd, f'hwd_{cam}.png')
    if not (os.path.exists(fr) and os.path.exists(fh)):
        print('skip', cam, 'missing', fr if not os.path.exists(fr) else fh); continue
    R = np.asarray(Image.open(fr).convert('RGB')); H = np.asarray(Image.open(fh).convert('RGB'))
    # the cameras are identical, so the reference (uniform background (223,227,230) / grid) classifies the aircraft's
    # pixels and the SAME pixels are read in the hwd3d image. Masks are eroded by 2 px (no edge pixels); the background
    # and the grid are excluded from 'white' (exact background colour +-3 and the low-saturation grid greys)
    cr = classes(R)
    bg = (np.abs(R.astype(np.int32) - np.array([223, 227, 230])).max(-1) <= 3)
    cr['white'] &= ~bg
    def erode(m, n=2):
        m = m.copy()
        for _ in range(n):
            m[1:, :] &= m[:-1, :]; m[:-1, :] &= m[1:, :]; m[:, 1:] &= m[:, :-1]; m[:, :-1] &= m[:, 1:]
        return m
    cr = {k: erode(v) for k, v in cr.items()}
    out[cam] = {'ref': {k: stats(R, v) for k, v in cr.items()}, 'hwd': {k: stats(H, v) for k, v in cr.items()}}
    W2, H2 = 960, 540
    sheet = Image.new('RGB', (W2 * 2, H2), (0, 0, 0))
    sheet.paste(Image.fromarray(R).resize((W2, H2), Image.LANCZOS), (0, 0)); sheet.paste(Image.fromarray(H).resize((W2, H2), Image.LANCZOS), (W2, 0))
    d = ImageDraw.Draw(sheet)
    for x, t in ((6, f'reference: pc12 viewer ({a.refkind}.html), {cam}'), (W2 + 6, f'hwd3d dev/model.html ({a.tag}), {cam}')):
        d.rectangle([x - 4, 2, x + 7 * len(t), 18], fill=(0, 0, 0)); d.text((x, 4), t, fill=(255, 220, 120))
    sheet.save(os.path.join(a.out, f'cmp_{a.tag}_{cam}.jpg'), quality=90)
    s = out[cam]
    print(cam, ' '.join(f"{k}: ref {s['ref'][k].get('median')} n{s['ref'][k]['n']} | hwd {s['hwd'][k].get('median')} n{s['hwd'][k]['n']}" for k in ('navy', 'gold', 'dark', 'white')))
json.dump(out, open(os.path.join(a.out, f'measure_{a.tag}.json'), 'w'), indent=1)
