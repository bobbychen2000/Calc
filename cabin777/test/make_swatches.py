# Cut tileable texture swatches from the official ANA photos (ref/ana, gitignored) -> ref/swatch/tex_*.png.
# Each tile stores colour RELATIVE to its mean (x0.5, so 128 = mean) after removing the photo's lighting gradient;
# the model's material colour still sets the mean, the tile only adds the real weave / grain / fleck pattern.
# build.py embeds ref/swatch/tex_*.png when present (otherwise the procedural layers in 03_tex.js are used).
import os
import numpy as np
from PIL import Image, ImageFilter

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 256
# name: (photo, crop box in the 930x575 image, physical tile size in m (estimated from known seat widths in the same photo),
#        optional rotation in degrees that straightens the grain before cropping)
SW = {
    'y_tick':      ('y_47306', (250, 362, 412, 556), 0.30),
    'y_diamond':   ('y_47306', (48, 382, 162, 536), 0.21),
    'py_back':     ('py_37305', (262, 442, 398, 566), 0.05),
    'py_confetti': ('py_37305', (238, 134, 326, 256), 0.07),
    'j_tweed':     ('c_27302', (112, 172, 238, 298), 0.24),
    'f_tweed':     ('f_17309', (70, 192, 290, 278), 0.30),
    'j_ash':       ('c_27305', (250, 80, 380, 210), 0.26),
    'f_wood':      ('f_17305', (100, 68, 230, 198), 0.28),
    'y_carpet':    ('y_47304', (24, 384, 226, 556), 0.26),
}


def tileable(a):
    """offset-and-blend: cross-fade the tile with a half-period roll so every edge wraps seamlessly"""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    m = np.minimum(np.minimum(xx, w - 1 - xx) / (w * 0.5), np.minimum(yy, h - 1 - yy) / (h * 0.5))
    m = np.clip(m * 2.2, 0, 1)[..., None]
    r = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    return a * m + r * (1 - m)


def make(name, photo, box, size, rot=0):
    im = Image.open(os.path.join(root, 'ref/ana', photo + '-lang-multi.jpg')).convert('RGB')
    if rot == 'auto':
        # dominant grain direction from the structure tensor of the crop; rotate so the grain runs horizontally
        g = np.asarray(im.crop(box).convert('L')).astype(np.float32)
        gy, gx = np.gradient(g)
        th = 0.5 * np.arctan2(2 * (gx * gy).sum(), ((gx * gx) - (gy * gy)).sum())   # gradient direction (across the grain)
        rot = -np.degrees(th)
        print(name, 'straighten', round(float(rot), 1))
    if rot:
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        im = im.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))
    im = im.crop(box)
    im = im.resize((S, S), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    lin = a ** 2.2
    # remove the lighting gradient: divide by a heavy blur (per-channel), keep the local pattern
    blur = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40))).astype(np.float32) / 255.0
    ratio = lin / np.maximum(blur ** 2.2, 1e-3)
    ratio = tileable(ratio)
    # clip specular glints (reflections of cabin lights) so only the material pattern remains
    lum = ratio.mean(2, keepdims=True)
    ratio = np.where(lum > 1.5, ratio * 1.5 / lum, ratio)
    ratio /= ratio.reshape(-1, 3).mean(0)
    out = np.clip(ratio * 0.5, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'ref/swatch', f'tex_{name}.png'))
    return size


if __name__ == '__main__':
    os.makedirs(os.path.join(root, 'ref/swatch'), exist_ok=True)
    sizes = {k: make(k, *v) for k, v in SW.items()}
    import json
    json.dump(sizes, open(os.path.join(root, 'ref/swatch/sizes.json'), 'w'))
    print('swatches', sizes)
