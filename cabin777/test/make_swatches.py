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
    # w11: 0.09 m (petals ~5-11 mm, ~1 cm on the trim-B backs in py_37302 / san_12) [D]
    'py_confetti': ('py_37305', (238, 140, 328, 230), 0.09),
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
    # room w12: re-cut from a real 1600 px close-up of the aisle-end panels (tpg_60, TPG 2020; ~0.85-0.9 mm/px on the panel,
    # 384 px = 0.32 m [D]): fine straight hairlines (high-pass SD 3.3-4.4 % in sRGB) plus the 1-4 cm light / dark bands of
    # real veneer (6.8 % at 1 cm on tpg_60, 7.3-7.4 % on c_27314 / tpg_81), which the old CG crop lacked (1.2 %) [D]
    'j_ash':       ('web/room/tpg_60.jpg', (880, 270, 1264, 654), 0.32),
    # near-black straight-grain veneer of the suite flank, real photo OMAAT f60 (doors 2 x 0.55 m ~ 1000 px -> 130 px =
    # 0.11 m for 100 px) [D]; the grain already runs along U (horizontal). suite w7: the 100 px corner crop was mostly JPEG
    # blocks and tiled into a brick grid on the flanks -> 170 px from the evenly lit left flank (0.17 m) [D], column-normalised
    # and blurred along the grain like j_ash (f60: long continuous dark streaks)
    'f_wood':      ('web/suite/omaat_f60.jpg', (0, 600, 170, 770), 0.17),
    # room w12: pillow / comforter 45-deg check jacquard, drawn at the period measured on the real photo tpg_46 (see synth_j_pillow) [D]
    'j_pillow':    ('web/room/tpg_46.jpg', (900, 700, 1000, 800), 0.152),
    'y_carpet':    ('y_47304', (24, 384, 226, 556), 0.26),
}
# QA r2: Y 5 (was 8), see 03_tex.js PHOTO_ENC; py_back 4: its white dashes are ~4.6x the charcoal ground in linear light
# (py_37301 luminance p10 / p90 100 / 201) and were clipped at 1.5x, which left the dark gaps dominant (pattern read
# inverted); py_confetti 6: white flakes ~220 on a 55-65 ground (py_37305, ~17x linear)
ENC = {'y_tick': 5, 'y_diamond': 5, 'y_fleck': 5, 'y_mosaic': 5, 'py_back': 4, 'py_confetti': 6}       # default 2 (= ratio x 0.5)
# grey-pattern materials: keep only the luminance pattern (the per-channel ratio of these phone photos is JPEG chroma
# noise and lilac / green casts); the model's material colour sets the hue
MONO = {'f_wood', 'f_tweed', 'j_ash', 'py_back',   # py_back: neutral grey weave (QA r1, wall-balanced py_37305)
        'j_tweed', 'py_confetti', 'j_pillow'}                  # QA r2: chroma of these was a green / purple JPEG cast
# high-pass radius of the lighting / blotch removal (default 40 px on the 256 px tile); py_back: the swatch's low-frequency
# dark blotches dominated the fine white dashes at seat distance (py_37301 / 37305 read as even dashes on charcoal)
HP = {'py_back': 20, 'j_ash': 60}   # room w12: j_ash keeps its 1-4 cm veneer bands
# straight horizontal grain: divide each column by its mean, so only the along-grain streaks remain (the c_27305 crop's
# faint vertical light bands were amplified into a banded look by the QA r2 gain)
COLNORM = {'j_ash', 'f_wood'}
# along-grain (x) box blur, px on the 256 px tile: straightens wavy streaks into continuous hairlines
ALONG = {'j_ash': 6, 'f_wood': 24}   # room w12: the real tpg_60 grain is already straight -> light blur only


def _blur_wrap(a, s):
    """periodic gaussian blur (tile stays seamless)"""
    k = np.fft.fftfreq(a.shape[0])[:, None] ** 2 + np.fft.fftfreq(a.shape[1])[None, :] ** 2
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * s) ** 2 * k)))


def synth_py_back(ratio, seed=7):
    """PY: redrawn crisply from ANA's official photos (user decision: ANA official look; the 2026 trip-report herringbone
    is a later fabric generation). Measured on py_37305 / 37301 (fabric research, ~980-1250 px/m) [D]:
    horizontal light dashes in rows, rows ~6.8 mm apart (24 per 0.163 m tile; py_37305 ~7 mm), dash bands ~0.45 of the
    row pitch with soft edges; dashes loosely in columns (~20 mm, 8 per tile) but jittered +-4 mm and every other row
    shifted 1/4 column (py_37301-03 row-to-row correlation 0.02-0.09 vs 0.43-0.49 for a strict grid, w5 rater A);
    dash length p50 ~11 mm (N(18, 4) px), brightness +-25 %; small darker cells (1 col x 1-2 rows, dashes x0.5-0.7)
    and a few slightly lighter ones; dash ~2.6x the ground ((p90-p10)/p50 0.39-0.51 on py_37301, w5 rater B); fine
    weave grain [D]"""
    rng = np.random.default_rng(seed)
    rows, cols = 20, 8                             # w7: rows 8.2 mm (py_37305 8.15 mm), wide enough to survive the mip
    ph, cw = S / rows, S / cols
    dim = np.ones((rows, cols)); ddim = np.ones((rows, cols))
    dom = rng.random((rows, cols))                 # w6: ~30 % dark-dominant cells (light x0.4), ~15 % light-dominant (dark x0.3)
    dim[dom < 0.36] = 0.35; ddim[dom > 0.88] = 0.4   # w7 (B): more dark-dominant cells
    for _ in range(16):                            # darker cells
        r0, c0 = rng.integers(0, rows), rng.integers(0, cols)
        v = rng.uniform(0.5, 0.7)
        for r in range(r0, r0 + rng.integers(1, 3)): dim[r % rows, c0] = v
    for _ in range(3):                             # slightly lighter cells
        r0, c0 = rng.integers(0, rows), rng.integers(0, cols)
        for r in range(r0, r0 + rng.integers(1, 3)):
            for c in range(c0, c0 + rng.integers(1, 3)): dim[r % rows, c % cols] = 1.15
    y = np.arange(S)[:, None] + 0.5; x = np.arange(S)[None, :] + 0.5
    lite = np.zeros((S, S)); dark = np.zeros((S, S))
    # w8 (A): each row its own pitch N(ph, 0.18 ph), renormalised to the tile (no corduroy beat at cabin distance)
    hr = np.clip(rng.normal(1, 0.18, rows), 0.6, 1.4); hr *= S / hr.sum(); yr = np.cumsum(hr) - hr / 2
    for r in range(rows):
        for c in range(cols):
            yc = yr[r] + rng.uniform(-0.12, 0.12) * ph
            ln = np.clip(rng.normal(19, 7), 8, 32)          # w8 (B): more varied lengths
            x0 = c * cw + (cw - ln) / 2 + (cw / 4) * (r % 2) + rng.uniform(-6, 6)
            u = (x[0] - x0) % S
            seg = np.clip(np.minimum(u, ln - u) / 3.0, 0, 1) * (u < ln)   # w11 (A + B): tapered ends (hard bricks)
            band = np.clip((3.6 - np.abs(((y[:, 0] - yc + S / 2) % S) - S / 2)) / 2.0, 0, 1)   # w11: ~4.5 mm cells, soft edges
            lite = np.maximum(lite, band[:, None] * seg[None, :] * np.clip(rng.normal(1, 0.25), 0.5, 1.5) * dim[r, c])
            # w6 (A + B): the navy-slate dash set (py_37301 / 37305 dark-dash cover 7-32 %); w7: on its own band between
            # the light rows so the two sets interlock into a mosaic (A + B)
            band = np.clip((2.8 - np.abs(((y[:, 0] - yr[r] - hr[r] / 2 + S / 2) % S) - S / 2)) / 1.0, 0, 1)
            ln = np.clip(rng.normal(19, 4), 10, 28)
            u = (x[0] - (x0 + cw / 2 + rng.uniform(-6, 6))) % S
            seg = np.clip(np.minimum(u, ln - u) / 3.0, 0, 1) * (u < ln)
            dark = np.maximum(dark, band[:, None] * seg[None, :] * rng.uniform(0.7, 1.0) * ddim[r, c])
    blob = _blur_wrap(rng.normal(0, 1, (S, S)), 12); blob /= blob.std()
    lite *= np.exp(0.2 * blob - 0.02)               # w8 (B): mottled light patches (py_37305); w9 (A): softer
    # w11 (A + B): each block is woven from fine horizontal thread dashes (py_37305 close-up: 3-4 threads per block,
    # ~1.9 mm pitch, 3-6 mm floats with 1 mm breaks), not a flat rectangle; the block mean is kept [D]
    thr = np.zeros((S, S)); yl = 0.0
    while yl < S:
        pr = np.clip((1.0 - np.abs(((y[:, 0] - yl + S / 2) % S) - S / 2)) / 0.8, 0, 1)
        xs, ln = rng.uniform(0, 8), np.zeros(S)
        while xs < S + 12:
            fl = rng.uniform(5, 10); u = (x[0] - xs) % S
            ln = np.maximum(ln, np.clip(np.minimum(u, fl - u) / 1.5, 0, 1) * (u < fl) * rng.uniform(0.7, 1.0))
            xs += fl + rng.uniform(1.2, 2.2)
        thr = np.maximum(thr, pr[:, None] * ln[None, :]); yl += rng.uniform(2.7, 3.3)
    thr = _blur_wrap(thr, 0.45)
    lite *= 0.45 + 0.85 * thr; dark *= 0.7 + 0.4 * thr
    out = (1 + 1.4 * lite) * (1 - 0.6 * dark)     # w7: light ~2.9x, dark ~0.3x the ground; w11 (A + gap): calmer, bright / median ~1.3 (py_37301 1.24)
    out *= 0.88 + 0.24 * thr                       # w11: the ground is woven too (threads read between the blocks, py_37305)
    # brick patches on a 2-col x 2-row lattice (block std/mean ~0.15, py_37305), crisp edges softened 0.5 px
    blk = np.exp(rng.normal(0, 0.15, (rows // 2, cols // 2)))
    blk = _blur_wrap(blk[(np.arange(S) // (2 * ph)).astype(int)][:, (np.arange(S) // (2 * cw)).astype(int)], 0.5)
    out *= blk
    mot = _blur_wrap(ratio.mean(2), 24); mot = (mot - mot.mean()) / (mot.std() + 1e-6)
    out *= np.exp(0.05 * mot)                      # very weak low-frequency term only
    out *= np.exp(0.06 * _blur_wrap(rng.normal(0, 1, (S, S)), 0.6) / 0.3)   # fine weave grain
    return np.repeat(out[:, :, None], 3, 2)


def synth_py_confetti(ratio, seed=11):
    """PY headrest wings, ANA official (py_37305 left wing, ~1000 px/m) [D]: sakura-petal chips, equivalent diameter p50
    6.5 mm (p25 5.4, p90 8.8), elongation 1.2-1.9, 5-7 jittered sides with one pointed end / a shallow notch, ~14 per
    0.07 m tile (2.2-3.7 per 10 cm^2), 9-12 % of the area, blue-noise spaced >= 12 mm; ~60 small specks 1-3 mm only
    1.5-2x the ground (boucle grain); petals ~6x the ground (linear); the ground is the wing's own mid slate grey"""
    rng = np.random.default_rng(seed)
    out = np.ones((S, S))
    yy, xx = np.mgrid[0:S, 0:S] + 0.5
    # w11 (A + gap): plain charcoal pebble ground with a fine mottle, no dash rows under the petals (py_37305 left ear,
    # san_12 trim-B back) [D]
    mo = _blur_wrap(rng.normal(0, 1, (S, S)), 2.5); out *= np.exp(0.12 * mo / mo.std())
    pts = []
    while len(pts) < 32:                          # w5 (A + B): varied chips; w11 (gap): 32 smaller ones (san_12 / py_37305)
        p = rng.uniform(0, S, 2)
        if all(min(abs(p[0] - q[0]), S - abs(p[0] - q[0])) ** 2 + min(abs(p[1] - q[1]), S - abs(p[1] - q[1])) ** 2 > 24 ** 2 for q in pts): pts.append(p)
    for cy, cx in pts:
        dy = (yy - cy + S / 2) % S - S / 2; dx = (xx - cx + S / 2) % S - S / 2
        a = rng.uniform(0, 2 * np.pi); e = rng.uniform(1.2, 2.4); req = np.clip(rng.normal(5.5, 2), 3, 9)
        u = dx * np.cos(a) + dy * np.sin(a); v = -dx * np.sin(a) + dy * np.cos(a)
        th = np.arctan2(v * e, u); rr = np.hypot(u / np.sqrt(e), v * np.sqrt(e))
        k = rng.integers(5, 8); ph0 = rng.uniform(0, 6)
        # polygonal chip: facets from a k-gon, pointed tip at th=0, shallow notch at th=pi (sakura petal)
        poly = (np.cos(np.pi / k) / np.cos((th + ph0) % (2 * np.pi / k) - np.pi / k)) ** 1.0   # sharp facets
        prof = req * poly * (1 + 0.18 * np.cos(th)) * (1 - 0.22 * np.exp(-((np.abs(th) - np.pi) / 0.25) ** 2))
        out += 6.5 * np.clip(rng.normal(1, 0.15), 0.7, 1.3) * np.clip((prof - rr) / 0.6, 0, 1)   # w11: crisper corners
    for cy, cx in rng.uniform(0, S, (60, 2)):
        rr = np.hypot((yy - cy + S / 2) % S - S / 2, (xx - cx + S / 2) % S - S / 2)
        out += rng.uniform(0.3, 0.6) * np.clip((rng.uniform(2, 5) - rr) / 1.0, 0, 1)
    for cy, cx in rng.uniform(0, S, (30, 2)):      # w5: mid-size specks 3-6 mm (py_37305 petals 3-12 mm)
        rr = np.hypot((yy - cy + S / 2) % S - S / 2, (xx - cx + S / 2) % S - S / 2)
        out += rng.uniform(0.6, 1.0) * np.clip((rng.uniform(2, 3.5) - rr) / 1.0, 0, 1)   # w11: faint (read as snow on the trim-B backs)
    out *= np.exp(0.08 * _blur_wrap(rng.normal(0, 1, (S, S)), 0.8) / 0.25)
    return np.repeat(out[:, :, None], 3, 2)


def synth_y_tick(ratio, seed=3):
    """econ w10 A: the y_47306 crop lacked column structure at row distance (column spread 0.066 vs 0.197 in y_47300).
    w11 A: the fully synthetic vertical bars with navy channels overshot ("digital rain"; matched-scale column variation
    0.183 vs 0.051) - the real weave IS the paired slanted chevron ticks of the photo crop. So: keep the photo crop and
    add only a soft ~15.5 mm column brightness envelope (+-22 %, jittered phase per band) [D]"""
    rng = np.random.default_rng(seed)
    n = ratio.shape[0]
    x = np.arange(n, dtype=np.float32)
    k = max(1, round(n / 15.5))                            # whole periods per 0.26 m tile (1 px ~ 1 mm) -> tileable
    ph = 2 * np.pi * k * x / n
    env = 1 + 0.22 * np.sin(ph + 0.6 * np.sin(2 * np.pi * 3 * x / n + rng.random() * 6.28))
    return ratio * env[None, :, None]


def synth_j_pillow(ratio):
    """THE Room blue pillow + comforter jacquard: a tone-on-tone check of small squares set on the diagonal (kn_17, KN Aviation
    2021 close-up; tpg_46 / tpg_81). Period along the pillow edge 12.5 px in tpg_46 (right O pillow ~295 px for 0.44 m =
    670 px/m) = 1.9 cm [D]; sRGB high-pass p10 / p90 0.85 / 1.15 on kn_17 -> about +-25 % in linear light [D]. The photos are
    too coarse and creased to tile directly, so the check is drawn (8 periods per 256 px tile = 0.152 m) and the photo crop's
    own fine noise is kept on top."""
    n = 256; i, j = np.mgrid[0:n, 0:n]
    a = 32                                          # 45 deg check: period along x / y = 32 px = 1.9 cm
    h = np.where((np.floor((i + j) / a) + np.floor((i - j) / a)) % 2 == 0, 1.0, -1.0)
    h = _blur_wrap(h, 1.5)                          # soft woven edges
    noise = ratio.mean(2) / ratio.mean() - 1
    # room w13a: the checks fade in and out along diagonal bands ~4 checks wide, tone-on-tone (kn_17) [V]
    band = 0.55 + 0.45 * np.cos(2 * np.pi * (i + j) / 128) ** 2
    r = 1 + 0.25 * band * h / np.abs(h).max() + 0.4 * np.clip(noise, -0.1, 0.1)
    return np.repeat(r[:, :, None], 3, 2)


SYNTH = {'py_back': synth_py_back, 'py_confetti': synth_py_confetti, 'y_tick': synth_y_tick, 'j_pillow': synth_j_pillow}


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
    """econ QA w1: the Y diamond variant, synthesised on the tick weave (the old photo crop tiled into snowflakes).
    w5-w8 history: inverted figure/ground (w5), plus-shaped stars on a square grid (w6), soft holed blobs (w8).
    econ w9 (A + B): measured on y_47306 left / y_47302 middle - crisp stepped diamonds ~0.045-0.06 m on a DOMINANT navy
    ground (Otsu light area 0.10-0.22), high contrast (p90/p50 ~2.1, light/dark ~2.2-2.7), each figure made of short
    horizontal light dash runs whose ends follow the 5 mm steps (serrated edges), with bright specks inside; figures sit
    on a broken diagonal lattice (pitch 0.0867, ~35 % of sites empty). Ground: the tick tile quietened to 40 % contrast
    and darkened ~15 % [D]"""
    t = np.asarray(Image.open(os.path.join(root, 'tex/tex_y_tick.png'))).astype(np.float32) / 255 * ENC['y_tick']
    n = S
    v, u = np.mgrid[0:n, 0:n] / n            # tile coords, 0.26 m
    rng = np.random.default_rng(7)
    m = np.zeros((n, n), np.float32)
    step = 0.005 / 0.26
    sites = [((a + o) / 3, (b + o) / 3) for o in (0, 0.5) for a in range(3) for b in range(3)]
    # w10 A + B: a continuous chained lattice of soft, mottled 0.06-0.08 m diamonds (no empty sites; w9's isolated
    # 0.05 m figures read as scattered polka-diamonds); the dash fill is broken ~40 % so the light area stays ~0.2-0.25
    for cu, cv in sites:
        hd = rng.uniform(0.034, 0.039)           # half-diagonal (minus a 5 mm ceil step) -> ~0.06-0.07 m figures; outline cover ~0.6 of the cloth
        for ou in (-1, 0, 1):
            for ov in (-1, 0, 1):
                # w6: ceil, not floor - floor grew every diamond by one step
                du = np.ceil(np.abs(u - cu - ou) / step) * step
                dv = np.ceil(np.abs(v - cv - ov) / step) * step
                m = np.maximum(m, (du / (hd / 0.26) + dv / (hd * 0.87 / 0.26) <= 1).astype(np.float32))
    # dash runs: 2 px light rows with a 1 px dark gap, each run's ends jittered +-1 px so the steps read serrated
    # w11 B: the horizontal dash-run fill read as scanlines -> a soft mottled fill (smoothed ~2 mm noise, ~50 % kept)
    # times the tick strokes, edges feathered over ~3 mm
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
    mot = _blur_wrap(rng.random((n, n)), 2.0); mot = np.clip(0.45 + 0.55 * (mot - np.percentile(mot, 30)) / (np.percentile(mot, 70) - np.percentile(mot, 30)), 0.3, 1)   # tonal mottled fill (y_47306 left: ~33-35 % light at 4 mm blur, gap10)
    tk = t.mean(2) / t.mean()
    m = (m * mot * np.clip(0.6 + 0.4 * tk, 0, 1.4))[..., None]
    tm = t.reshape(-1, 3).mean(0)
    ground = 0.85 * (tm + 0.4 * (t - tm))
    lift = np.array([4.0, 3.8, 3.1], np.float32)          # pale lavender (y_47302 / 47306); w11 B: figure ~1.9x the ground
    ratio = ground * (1 - m) + lift * m
    sp = ((rng.random((n, n)) < 0.10) * (m[..., 0] > 0))[..., None]    # bright specks inside the figures (~8 % of the area figures cover)
    ratio = np.where(sp, np.array([5.0, 4.8, 4.0], np.float32), ratio)
    ratio /= ratio.reshape(-1, 3).mean(0)
    out = np.clip(ratio / ENC['y_diamond'], 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_y_diamond.png'))
    return 0.26


def y_fleck():
    """econ w5 (A high): the fourth Y fabric, the commonest dark one - scattered pale petal-shaped flecks on dark navy
    (y_47300 front-row seats 2 / 4, sans 13 / 14, fr57325 124108). Flecks ~4-7 x 2-3.6 mm at random angles, evenly spread, ~10 % cover,
    near #a9b4d6 on a #27345a ground (sans 14 back L p10/50/90 34/48/87) -> lift (7.5, 6.8, 4.0) over a faint weave
    ground (the tick tile at ~25 % contrast); 0.2 m tile [D]"""
    n = S; size = 0.2; mm = n / (size * 1000)
    t = np.asarray(Image.open(os.path.join(root, 'tex/tex_y_tick.png'))).astype(np.float32) / 255 * ENC['y_tick']
    t = np.asarray(Image.fromarray((np.clip(t / t.max(), 0, 1) * 255).astype(np.uint8)).resize((n, n))).astype(np.float32) / 255
    ground = 0.94 + 0.06 * t / t.reshape(-1, 3).mean(0)   # w11 B: plain navy, the ticks must not read between petals
    rng = np.random.default_rng(11)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    m = np.zeros((n, n), np.float32)
    pts = []
    while m.mean() < 0.11:
        cx, cy = rng.random(2) * n
        # evenly spread (y_47300 seat 2: flecks never clump): reject centres within 6 mm of another (w6 B: 4.5 mm still clumped) (tile-wrapped)
        if any(min(abs(cx - px), n - abs(cx - px)) ** 2 + min(abs(cy - py), n - abs(cy - py)) ** 2 < (5 * mm) ** 2 for px, py in pts): continue
        pts.append((cx, cy))
        a = rng.uniform(2.2, 3.4) * mm; b = a / rng.uniform(2.2, 3.0)      # half-axes; w6 A rounder; w7 A: larger lognormal 4.5-9 x 3-5 mm, ~0.6x the count (y_47300 seats 2 / 4); w10 gap: median 2.3 mm half-axis, 6 mm spacing (render had 20 % too few, 50 % too large vs sans_14)
        th = rng.random() * np.pi
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                dx, dy = x - cx - ox, y - cy - oy
                pu = dx * np.cos(th) + dy * np.sin(th); pv = -dx * np.sin(th) + dy * np.cos(th)
                # petal: an ellipse pinched toward one end
                w = b * (1 - 0.45 * np.clip(pu / a, -1, 1))
                m = np.maximum(m, ((pu / a) ** 2 + (pv / np.maximum(w, 1e-3)) ** 2 <= 1).astype(np.float32))
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))).astype(np.float32)[..., None] / 255
    lift = np.array([7.0, 6.4, 3.9], np.float32)          # w10 gap: flecks ~15 % too bright (q16 read as snow); w11 B -10 %
    ratio = ground * (1 - m) + lift * m
    ratio /= ratio.reshape(-1, 3).mean(0)
    out = np.clip(ratio / ENC['y_fleck'], 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_y_fleck.png'))
    return size


def y_mosaic():
    """econ w6: third Y fabric. w9-w10: cells, bricks, short dashes. econ w11 (A + B): the defining feature is a grid of
    brick-laid rectangular blocks ~28.6 x 18.2 mm (7 x 11 per 0.2 m tile, alternate rows offset half a block), each a
    field of 1-px near-neutral grey-white horizontal dashes in rows ~2 mm apart, laid nearly end to end; neighbouring
    blocks differ strongly in density, drawn irregularly from {0.12, 0.30, 0.55} (not a checker); a 1-px dark seam on
    each block's left and top edge (y_47306 right, y_47303 near back, y_47300 seat-4 pan, sans 14 pan) [D]"""
    n = S; size = 0.2; mm = n / (size * 1000)
    t = np.asarray(Image.open(os.path.join(root, 'tex/tex_y_tick.png'))).astype(np.float32) / 255 * ENC['y_tick']
    ground = 0.94 + 0.06 * t / t.reshape(-1, 3).mean(0)
    rng = np.random.default_rng(5)
    m = np.zeros((n, n), np.float32)
    seam = np.zeros((n, n), np.float32)
    NI, NJ = 7, 11
    cw, ch = n / NI, n / NJ
    for j in range(NJ):
        y0 = int(round(j * ch)); y1 = int(round((j + 1) * ch))
        seam[y0 % n, :] = 1
        for i in range(NI):
            x0 = (i + (0.5 if j % 2 else 0)) * cw
            seam[y0:y1, int(x0) % n] = 1
            dense = rng.choice([0.12, 0.30, 0.55]) * rng.uniform(0.85, 1.15)
            for yy in range(y0 + 2, y1 - 1, 2):
                xa = x0 + 2 + rng.random() * 2
                while xa < x0 + cw - 2:
                    L = int(np.clip(rng.lognormal(np.log(4.0 * mm), 0.45), 1, cw - 4))
                    if rng.random() < dense / 0.55:
                        xs = np.arange(int(xa), min(int(xa) + L, int(x0 + cw) - 1)) % n
                        m[yy, xs] = rng.uniform(0.7, 1.0)
                    xa += L + rng.uniform(0.5, 1.5) * mm
    m = m[..., None]
    lift = np.array([5.2, 5.4, 5.6], np.float32)              # near-neutral grey-white
    ratio = ground * (1 - m) + lift * m
    ratio = ratio * (1 - 0.35 * seam[..., None])
    ratio /= ratio.reshape(-1, 3).mean(0)
    out = np.clip(ratio / ENC['y_mosaic'], 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_y_mosaic.png'))
    return size


def x_skin():
    """exterior w8: wing-skin weathering tile (grime mottle + chordwise streaks) from the sunlit flap panels of ANA JA795A
    (alv IMG_7250, seat 26K, 2026: grey streaky grime on the flap; the KN Aviation 41 crops were JPEG blocks). Panel lines, rivets and JPEG blocks are removed with a median filter, the lighting with a heavy blur; the
    tile is luminance-only (the material sets the Boeing grey). Rows = flow direction (z in the triplanar top projection),
    so the grime is smeared along the rows like the photos' TE streaks. Tile 4 m [A: flap chord ~1.5 m spans ~95 px of the
    7250 crop -> 4 m ~ 250 px]"""
    srcs = [('web/exterior/b_alv_ANA77W_PY_IMG_7250-2-scaled.jpeg', (60, 842, 360, 936)),     # flap panel, clear of its edges
            ('web/exterior/b_alv_ANA77W_PY_IMG_7250-2-scaled.jpeg', (90, 860, 330, 946))]     # same panel, offset (the spoiler crops hold seam lines)
    acc = 0
    for f, box in srcs:
        im = Image.open(os.path.join(root, 'ref', f)).convert('L').crop(box).filter(ImageFilter.MedianFilter(3))
        im = im.resize((S, S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2))
        a = (np.asarray(im).astype(np.float32) / 255.0) ** 2.2
        b = np.asarray(im.filter(ImageFilter.GaussianBlur(64))).astype(np.float32) / 255.0
        r = np.clip(a / np.maximum(b ** 2.2, 1e-3), 0.8, 1.2)   # specks / glints out
        acc = acc + tileable((r / r.mean())[:, :, None])[:, :, 0]
    r = acc / len(srcs)
    # chordwise streaks: box blur along the rows (flow), as in the 7250 flap grime [D]
    k = 28
    r = sum(np.roll(r, d, 0) for d in range(-k // 2, k // 2 + 1)) / (k + 1)
    r = np.where(r > 1, 1 + (r - 1) * 0.5, r)   # w9: skew dark - grime darkens, it does not lighten (photos skew dark, A w9)
    r = r / r.mean()
    # the sunlit 7250 flap is near clipping (SD 0.6 %), so the tile stores the pattern stretched to SD 0.12; 03_tex.js
    # PHOTO_GAIN[27] sets the rendered strength (0.12 x gain) [D]
    r = 1 + (r - 1) * (0.12 / r.std())
    print('x_skin sd', round(float(r.std()), 4), 'p5/p95', np.percentile(r, [5, 95]).round(3))
    out = np.clip(np.repeat(r[:, :, None], 3, 2) / 2, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_x_skin.png'))
    return 4.0


def g_alu():
    """monuments w9: satin galley-insert wear tile (smudges, wipe marks, soft dents) from real ANA 777-300ER galley inserts:
    the oven door face below its handle (SANspotter economy 44, sansY_44) and a cart door (SANspotter PY 38, sans_38),
    both clear of edges, latches and labels. Median filter drops JPEG blocks, a heavy blur removes the lighting;
    luminance-only (the material sets the satin grey), stored at SD 0.10 so PHOTO_GAIN[28] sets the strength. Tile 0.18 m
    [D: oven door 0.30 m wide ~ 190 px in sansY_44 -> the 70 px crop ~ 0.11 m; at 0.3 m the smudges read as stains]"""
    srcs = [('web/monuments/sansY_44.jpg', (535, 95, 605, 165)), ('web/monuments/sans_38.jpg', (600, 700, 740, 840))]
    acc = 0
    for f, box in srcs:
        im = Image.open(os.path.join(root, 'ref', f)).convert('L').crop(box).filter(ImageFilter.MedianFilter(3))
        im = im.resize((S, S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.5))
        a = (np.asarray(im).astype(np.float32) / 255.0) ** 2.2
        b = np.asarray(im.filter(ImageFilter.GaussianBlur(48))).astype(np.float32) / 255.0
        r = np.clip(a / np.maximum(b ** 2.2, 1e-3), 0.75, 1.25)
        r = r / r.mean()
        acc = acc + tileable((1 + (r - 1) / r.std())[:, :, None])[:, :, 0]   # each source at unit SD, then averaged
    r = acc / len(srcs)
    r = np.where(r > 1, 1 + (r - 1) * 0.6, r)   # wear darkens more than it lightens (smudges, sansY_44)
    r = r / r.mean()
    r = 1 + (r - 1) * (0.10 / r.std())
    print('g_alu sd', round(float(r.std()), 4), 'p5/p95', np.percentile(r, [5, 95]).round(3))
    out = np.clip(np.repeat(r[:, :, None], 3, 2) / 2, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_g_alu.png'))
    return 0.18


if __name__ == '__main__':
    os.makedirs(os.path.join(root, 'tex'), exist_ok=True)
    import json, sys
    # optional names on the command line re-cut only those tiles (the others keep their sizes.json entries)
    only = sys.argv[1:]
    sizes = json.load(open(os.path.join(root, 'tex/sizes.json'))) if only else {}
    sizes.update({k: make(k, *v) for k, v in SW.items() if not only or k in only})
    if not only or 'y_diamond' in only: sizes['y_diamond'] = y_diamond()
    if not only or 'y_fleck' in only: sizes['y_fleck'] = y_fleck()
    if not only or 'y_mosaic' in only: sizes['y_mosaic'] = y_mosaic()
    if not only or 'x_skin' in only: sizes['x_skin'] = x_skin()
    if not only or 'g_alu' in only: sizes['g_alu'] = g_alu()
    json.dump(sizes, open(os.path.join(root, 'tex/sizes.json'), 'w'))
    print('swatches', sizes)
