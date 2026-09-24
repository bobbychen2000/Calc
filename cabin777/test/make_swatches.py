# Cut tileable texture swatches from the official ANA photos (ref/ana, gitignored) -> tex/tex_*.png (tracked;
# the page embeds them anyway). Source photos stay in ref/ (gitignored; python3 test/fetch_refs.py re-downloads the ANA set).
# Each tile stores colour RELATIVE to its mean (x0.5, so 128 = mean) after removing the photo's lighting gradient;
# the model's material colour still sets the mean, the tile only adds the real weave / grain / fleck pattern.
# Photo names without a folder are ANA pages (ref/ana/<name>-lang-multi.jpg); 'web/...' names are ref/web/<path>
# (real in-cabin photos, crop boxes in that image's own pixels).
# ENC: swatches whose pattern exceeds 2x the mean (Y: pale ticks ~10x the navy ground in linear light) are stored as
# ratio / ENC instead of ratio / 2; 03_tex.js PHOTO_ENC holds the same factors and photoBase() lifts the material colour
# by ENC/2 so the product is unchanged.
# build.py embeds tex/tex_*.png when present (otherwise the procedural layers in 03_tex.js are used).
import os
import numpy as np
from PIL import Image, ImageFilter

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 256
# name: (photo, crop box in the 930x575 image, physical tile size in m (estimated from known seat widths in the same photo),
#        optional rotation in degrees that straightens the grain before cropping)
SW = {
    # QA r2: the flap of the middle seat (0.27 m) spans 165 px in y_47306 (611 px/m) -> a 162 px crop is 0.26 m [D];
    # square crops (the old 162 x 194 / 114 x 154 boxes were stretched to 256 x 256); the left seat's flap is 125 px
    # (463 px/m) -> 120 px diamond crop = 0.26 m, diamond period ~0.086 m as in y_47302 [D]
    'y_tick':      ('y_47306', (250, 380, 412, 542), 0.26),
    # clean, evenly lit dash weave of the seat back (the old crop held the seam shadow + a glint); flap in the same photo
    # gives ~860 px/m -> 140 px = 0.163 m [D]
    'py_back':     ('py_37305', (720, 430, 860, 570), 0.163),
    # white flakes on the charcoal wing of the left seat, square contiguous crop (the old 88 x 122 box was stretched);
    # wing ~0.10 m = 130 px -> 90 px = 0.07 m [D]. Also the Y headrest wings' confetti (y_47306 middle seat, 45 px at
    # 611 px/m = 0.074 m) [D] - both are MONO so the material colour sets charcoal / cobalt
    'py_confetti': ('py_37305', (238, 140, 328, 230), 0.07),
    # c_27302 seat back 0.64 m ~ 330 px -> 126 px = 0.24 m, but that is a rendering that coarsens the weave; the real
    # in-cabin photos (c_27315, omaat_room_13) read as a fine uniform weave -> tile shrunk to 0.14 (2-3 mm dots) [A]
    'j_tweed':     ('c_27302', (112, 172, 238, 298), 0.14),
    # real photo of the ottoman (OMAAT f11): uniform fine grey weave; ottoman 0.86 m ~ 680 px -> 120 px = 0.15 m [D]
    # (the old crop from render f_17309 carried a zig-zag moire that tiled into a plaid)
    'f_tweed':     ('web/suite/omaat_f11.jpg', (500, 600, 620, 720), 0.15),
    # QA r2: strong straight horizontal streaks of the cabinet door in c_27305 (cabinet 0.34 m = 155 px -> 100 px =
    # 0.22 m) [D], above the door split (the old c_27316 crop was nearly uniform)
    # room QA w1: the 2.2 mm/px source gave 4-8 mm wavy streaks; real veneer shows long straight 1-2 mm hairlines
    # (tt_suite-door-1, c_27305 aisle-end panels) -> blurred along the grain (ALONG) and the tile shrunk to 0.14 m [A]
    'j_ash':       ('c_27305', (262, 88, 362, 188), 0.14),
    # near-black straight-grain veneer of the suite flank, real photo OMAAT f60 (doors 2 x 0.55 m ~ 1000 px -> 130 px =
    # 0.11 m for 100 px) [D]; the grain already runs along U (horizontal)
    'f_wood':      ('web/suite/omaat_f60.jpg', (0, 490, 100, 590), 0.11),
    'y_carpet':    ('y_47304', (24, 384, 226, 556), 0.26),
}
# QA r2: Y 5 (was 8), see 03_tex.js PHOTO_ENC; py_back 4: its white dashes are ~4.6x the charcoal ground in linear light
# (py_37301 luminance p10 / p90 100 / 201) and were clipped at 1.5x, which left the dark gaps dominant (pattern read
# inverted); py_confetti 6: white flakes ~220 on a 55-65 ground (py_37305, ~17x linear)
ENC = {'y_tick': 5, 'y_diamond': 5, 'py_back': 4, 'py_confetti': 6}       # default 2 (= ratio x 0.5)
# grey-pattern materials: keep only the luminance pattern (the per-channel ratio of these phone photos is JPEG chroma
# noise and lilac / green casts); the model's material colour sets the hue
MONO = {'f_wood', 'f_tweed', 'j_ash', 'py_back',   # py_back: neutral grey weave (QA r1, wall-balanced py_37305)
        'j_tweed', 'py_confetti'}                  # QA r2: chroma of these was a green / purple JPEG cast
# high-pass radius of the lighting / blotch removal (default 40 px on the 256 px tile); py_back: the swatch's low-frequency
# dark blotches dominated the fine white dashes at seat distance (py_37301 / 37305 read as even dashes on charcoal)
HP = {'py_back': 20}
# straight horizontal grain: divide each column by its mean, so only the along-grain streaks remain (the c_27305 crop's
# faint vertical light bands were amplified into a banded look by the QA r2 gain)
COLNORM = {'j_ash'}
# along-grain (x) box blur, px on the 256 px tile: straightens wavy streaks into continuous hairlines
ALONG = {'j_ash': 24}


def _blur_wrap(a, s):
    """periodic gaussian blur (tile stays seamless)"""
    k = np.fft.fftfreq(a.shape[0])[:, None] ** 2 + np.fft.fftfreq(a.shape[1])[None, :] ** 2
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * s) ** 2 * k)))


def synth_py_back(ratio, seed=7):
    """PY QA w1/w2: the 140 px photo crop upsampled to 256 renders as soft blobs up close, so the weave is redrawn crisply
    and only the photo's mottling (low-pass of the crop) is kept for the cloud zones. Real cabin close-ups (ref/web/py
    alv_17 / alv_04, san_02) show irregular horizontal cream streaks, 1-4 mm thick and 5-40 mm long with ragged ends,
    loosely rowed at ~8.7 mm (py_37305 y-autocorrelation 7.5 px at 860 px/m), ~35-40 % light coverage on a slate
    ground, lighter and denser in cloud zones, plus scattered cream chips; cream ~4-5x the ground in linear light [D].
    w2: replaces the w1 brick grid of equal dashes (rater A: 'digital', 15 % coverage)"""
    rng = np.random.default_rng(seed)
    mot = _blur_wrap(ratio.mean(2), 9)
    mot = (mot - mot.mean()) / (mot.std() + 1e-6)
    y = np.arange(S)[:, None]; x = np.arange(S)[None, :]
    lite = np.zeros((S, S))
    ph = S / 19                                    # 0.163 m / 19 = 8.6 mm row pitch
    for r in range(19):
        xs = rng.uniform(0, 20)
        while xs < S:
            m = mot[int((r + 0.5) * ph) % S, int(xs) % S]
            p_on = np.clip(0.8 + 0.25 * m, 0.3, 1.0)             # denser streaks in the light cloud zones
            ln = rng.uniform(6, 45) if rng.random() < 0.7 else rng.uniform(3, 8)
            if rng.random() < p_on:
                yc = (r + 0.5) * ph + rng.normal(0, 1.1)
                th = rng.uniform(1.6, 3.6)                          # streak half-thickness (px): 2-4.5 mm total
                sl = rng.normal(0, 0.03)                            # slight slant
                u = (x - xs) % S
                along = np.clip(np.minimum(u, ln - u) / 2.0, 0, 1) * (u < ln)
                dy = ((y - yc - sl * u + S / 2) % S) - S / 2
                rag = 1 + 0.4 * np.interp(u, np.arange(0, S + 5, 5), rng.uniform(-1, 1, len(range(0, S + 5, 5))))   # ragged edges
                across = np.clip((th * rag - np.abs(dy)) / 0.9, 0, 1)
                lite = np.maximum(lite, along * across * np.clip(rng.normal(1.0, 0.18), 0.5, 1.3))
            xs += ln + rng.uniform(1.0, 4.5)
    for cy, cx in rng.uniform(0, S, (60, 2)):     # cream chips, mostly in the light zones
        if mot[int(cy), int(cx)] < -0.3: continue
        rr = np.hypot(((x - cx + S / 2) % S - S / 2) * 0.7, ((y - cy + S / 2) % S - S / 2) / 0.7)
        lite = np.maximum(lite, np.clip((rng.uniform(2.0, 5.0) - rr) / 1.0, 0, 1))
    out = (1 + 3.4 * lite) * np.exp(0.18 * mot)
    return np.repeat(out[:, :, None], 3, 2)


def synth_py_confetti(ratio, seed=11):
    """PY QA w1: crisp white petal flakes instead of the soft upsampled crop. py_37305 wing crop (90 px = 0.07 m):
    ~22 flakes, median 27 px^2 (~4-5 mm), 6-8 % area above 150, ground p10 72 / flakes 200+ sRGB (~12x linear) [D].
    In the cabin views the photo-sized chips read as 2-3 cm blotches against real in-cabin photos (san_01, alv_04: fine
    speckle) -> smaller chips. w2: real wings (alv_04 / alv_17, san_01) carry dense cream speckle, 20-40 % light
    coverage (rater A: 5 % in w1) -> 46 chips + 160 specks [D]"""
    rng = np.random.default_rng(seed)
    out = np.ones((S, S))
    yy, xx = np.mgrid[0:S, 0:S]
    pts = []
    while len(pts) < 46:                           # blue-noise placement (flakes never touch in the photo)
        p = rng.uniform(0, S, 2)
        if all(min(abs(p[0] - q[0]), S - abs(p[0] - q[0])) ** 2 + min(abs(p[1] - q[1]), S - abs(p[1] - q[1])) ** 2 > 24 ** 2 for q in pts): pts.append(p)
    for cy, cx in pts:
        dy = (yy - cy + S / 2) % S - S / 2; dx = (xx - cx + S / 2) % S - S / 2
        a = rng.uniform(0, np.pi); r0 = rng.uniform(4.5, 8.0)
        th = np.arctan2(dy, dx); rr = np.hypot(dx, dy)
        # irregular torn-paper chip: random low harmonics, elongated along a random axis
        lob = 1 + 0.3 * np.cos(2 * (th - a)) + sum(rng.uniform(0, 0.14) * np.cos(k * th + rng.uniform(0, 6)) for k in (3, 4, 5, 7))
        out += 7 * np.clip((r0 * lob - rr) / 1.0, 0, 1)
    for cy, cx in rng.uniform(0, S, (160, 2)):     # small specks between the chips + fine ground grain
        rr = np.hypot((yy - cy + S / 2) % S - S / 2, (xx - cx + S / 2) % S - S / 2)
        out += 5 * np.clip((rng.uniform(1.5, 3.2) - rr) / 1.0, 0, 1)
    out *= np.exp(0.12 * _blur_wrap(rng.normal(0, 1, (S, S)), 1.2) / 0.2)
    return np.repeat(out[:, :, None], 3, 2)


SYNTH = {'py_back': synth_py_back, 'py_confetti': synth_py_confetti}


def tileable(a):
    """offset-and-blend, one axis at a time: cross-fade with a half-period roll along x (mask depends on x only), then the
    result with its roll along y. QA r2: the old 2-D mask used the rolled copy near the corners, where its own seams lie
    -> visible 2 x 2 quadrant seams at 128 px (tex_py_back / j_ash / j_tweed)"""
    h, w = a.shape[:2]
    mx = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w * 0.5) * 2.2, 0, 1)[None, :, None]
    a = a * mx + np.roll(a, w // 2, 1) * (1 - mx)
    my = np.clip(np.minimum(np.arange(h), h - 1 - np.arange(h)) / (h * 0.5) * 2.2, 0, 1)[:, None, None]
    return a * my + np.roll(a, h // 2, 0) * (1 - my)


def make(name, photo, box, size, rot=0):
    fn = os.path.join(root, 'ref', photo) if photo.startswith('web/') else os.path.join(root, 'ref/ana', photo + '-lang-multi.jpg')
    im = Image.open(fn).convert('RGB')
    if rot == 'auto':
        # dominant grain direction from the structure tensor of the crop; rotate so the grain runs horizontally
        g = np.asarray(im.crop(box).convert('L')).astype(np.float32)
        gy, gx = np.gradient(g)
        th = 0.5 * np.arctan2(2 * (gx * gy).sum(), ((gx * gx) - (gy * gy)).sum())   # gradient direction (across the grain)
        rot = 90 - np.degrees(th)       # th = 90 deg for grain that already runs along x
        print(name, 'straighten', round(float(rot), 1))
    if rot:
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        im = im.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))
    im = im.crop(box)
    im = im.resize((S, S), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    lin = a ** 2.2
    # remove the lighting gradient: divide by a heavy blur (per-channel), keep the local pattern
    blur = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(HP.get(name, 40)))).astype(np.float32) / 255.0
    ratio = lin / np.maximum(blur ** 2.2, 1e-3)
    if name in MONO: ratio = np.repeat(ratio.mean(2, keepdims=True), 3, 2)
    if name in ALONG:
        k = ALONG[name]
        ratio = sum(np.roll(ratio, d, 1) for d in range(-k // 2, k // 2 + 1)) / (k + 1)
    if name in COLNORM: ratio = ratio / ratio.mean(0, keepdims=True)
    ratio = tileable(ratio)
    # clip specular glints (reflections of cabin lights) so only the material pattern remains
    # (the Y ticks are real ~10x highlights, so the glint limit scales with the encoding range)
    enc = ENC.get(name, 2)
    lim = 1.5 if enc == 2 else enc * 0.95
    lum = ratio.mean(2, keepdims=True)
    ratio = np.where(lum > lim, ratio * lim / np.maximum(lum, 1e-6), ratio)
    if name in SYNTH: ratio = SYNTH[name](ratio)
    ratio /= ratio.reshape(-1, 3).mean(0)
    out = np.clip(ratio / enc, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', f'tex_{name}.png'))
    return size


def y_diamond():
    """econ QA w1: the Y diamond variant, synthesised on the tick weave. The old photo crop (y_47306 far-left seat, seen
    at ~55 deg and upsampled 2x) tiled into blurry snowflakes. The real fabric (y_47306 left seat, y_47302 middle seat) is
    the same navy tick ground with a staggered lattice of pale, stepped (ikat-like) diamonds: same-row period 0.12 /
    0.095 m, same-column 0.108 m -> 2 per row, 4 staggered rows per 0.26 m tile (0.13 m) [D]; diamonds ~0.08 wide x
    0.074 tall with ~4.5 mm steps, near-touching (w2) [D]; diamond / ground linear ratio R 6.8 G 4.8 B 2.3 (blur-3 p70 / p30, y_47306) and 8.0 / 6.9 / 3.3 (y_47302),
    i.e. pale lavender diamonds -> lift (3.4, 2.7, 1.7) over the tick ground, with the ticks dimmed inside [D]"""
    t = np.asarray(Image.open(os.path.join(root, 'tex/tex_y_tick.png'))).astype(np.float32) / 255 * ENC['y_tick']
    n = S
    v, u = np.mgrid[0:n, 0:n] / n            # tile coords, 0.26 m
    rng = np.random.default_rng(7)
    m = np.zeros((n, n), np.float32)
    step = 0.008 / 0.26                      # ~8 mm weave steps (w3 A: ~10 mm read at cabin distance; 4.5 mm vanished)
    for cu, cv in [(a + (0.25 if r % 2 else 0), 0.125 + 0.25 * r) for r in range(4) for a in (0.0, 0.5)]:
        for ou in (-1, 0, 1):
            for ov in (-1, 0, 1):
                du = np.floor(np.abs(u - cu - ou) / step) * step
                dv = np.floor(np.abs(v - cv - ov) / step) * step
                m = np.maximum(m, (du / (0.040 / 0.26) + dv / (0.037 / 0.26) <= 1).astype(np.float32))
    # ragged ikat edges: a little value noise on the mask, then a 1 px soften
    m = np.clip(m + (rng.random((n, n)) - 0.5) * 0.9 * (np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.FIND_EDGES)) > 0), 0, 1)
    m = (m > 0.5).astype(np.float32)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.4))).astype(np.float32)[..., None] / 255
    # w2: near-touching lattice (~45 % cover, w2 A), ragged edges; lower lift - with the bigger cover the ground darkens
    # after normalising (w2 B: p10/p90 51/142 vs photo 54/120)
    lift = np.array([2.4, 2.0, 1.4], np.float32)
    inside = lift * (0.6 + 0.4 * t)
    ratio = t * (1 - m) + inside * m
    ratio /= ratio.reshape(-1, 3).mean(0)
    out = np.clip(ratio / ENC['y_diamond'], 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_y_diamond.png'))
    return 0.26


if __name__ == '__main__':
    os.makedirs(os.path.join(root, 'tex'), exist_ok=True)
    import json, sys
    # optional names on the command line re-cut only those tiles (the others keep their sizes.json entries)
    only = sys.argv[1:]
    sizes = json.load(open(os.path.join(root, 'tex/sizes.json'))) if only else {}
    sizes.update({k: make(k, *v) for k, v in SW.items() if not only or k in only})
    if not only or 'y_diamond' in only: sizes['y_diamond'] = y_diamond()
    json.dump(sizes, open(os.path.join(root, 'tex/sizes.json'), 'w'))
    print('swatches', sizes)
