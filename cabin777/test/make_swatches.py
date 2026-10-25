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
    # clean, evenly lit dash weave of the seat back (the old crop held the seam shadow + a glint); flap in the same photo
    # gives ~860 px/m -> 140 px = 0.163 m [D]
    'py_back':     ('py_37305', (720, 430, 860, 570), 0.163),
    # white flakes on the charcoal wing of the left seat, square contiguous crop (the old 88 x 122 box was stretched);
    # wing ~0.10 m = 130 px -> 90 px = 0.07 m [D]. Also the Y headrest wings' confetti (y_47306 middle seat, 45 px at
    # 611 px/m = 0.074 m) [D] - both are MONO so the material colour sets charcoal / cobalt
    # w11: 0.09 m (petals ~5-11 mm, ~1 cm on the trim-B backs in py_37302 / san_12) [D]
    'py_confetti': ('py_37305', (238, 140, 328, 230), 0.09),
    # w13 (A): the ears' own tile - notched sakura chips over tiny specks (py_37305 left ear, ~1000 px/m) [D]
    'py_ear':      ('py_37305', (238, 140, 328, 230), 0.07),
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
    # polish B (from_integration r2/r3): THE Room carpet, fine dark heather with light flecks. c_27312's mid-aisle (the
    # suggested crop) is ~4 mm/px and foreshortened ~0.4, so its specks smeared into vertical streaks when stretched to a
    # square tile; c_27315's footwell carpet (bottom right) is seen near-overhead and closer, specks isotropic (autocorr
    # 2 x 1 px vs 1 x 3 px) -> 120 px ~ 0.36 m (speck pitch matched to c_27312 at 255 px/m across the aisle) [D / A];
    # luminance only (the material colour sets the mauve-brown)
    'j_carpet':    ('c_27315', (800, 450, 920, 570), 0.36),
}
# QA r2: Y 5 (was 8), see 03_tex.js PHOTO_ENC; py_back 4: its white dashes are ~4.6x the charcoal ground in linear light
# (py_37301 luminance p10 / p90 100 / 201) and were clipped at 1.5x, which left the dark gaps dominant (pattern read
# inverted); py_confetti 6: white flakes ~220 on a 55-65 ground (py_37305, ~17x linear)
ENC = {'y_tick': 5, 'y_diamond': 5, 'y_fleck': 5, 'y_mosaic': 5, 'py_back': 4, 'py_confetti': 6, 'py_ear': 6}       # default 2 (= ratio x 0.5)
# grey-pattern materials: keep only the luminance pattern (the per-channel ratio of these phone photos is JPEG chroma
# noise and lilac / green casts); the model's material colour sets the hue
MONO = {'f_wood', 'f_tweed', 'j_ash', 'py_back',   # py_back: neutral grey weave (QA r1, wall-balanced py_37305)
        'j_tweed', 'py_confetti', 'j_pillow', 'py_ear', 'j_carpet'}                  # QA r2: chroma of these was a green / purple JPEG cast
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
    hr = np.clip(rng.normal(1, 0.08, rows), 0.8, 1.2); hr *= S / hr.sum(); yr = np.cumsum(hr) - hr / 2   # w13 (B): steadier rows (py_37301 / 37303)
    for r in range(rows):
        for c in range(cols):
            yc = yr[r] + rng.uniform(-0.12, 0.12) * ph
            ln = np.clip(rng.normal(25, 3), 18, 30)          # w8 (B): more varied lengths; w13 (B): more even (TV-static read)
            x0 = c * cw + (cw - ln) / 2 + (cw / 4) * (r % 2) + rng.uniform(-6, 6)
            u = (x[0] - x0) % S
            seg = np.clip(np.minimum(u, ln - u) / 3.0, 0, 1) * (u < ln)   # w11 (A + B): tapered ends (hard bricks)
            band = np.clip((4.3 - np.abs(((y[:, 0] - yc + S / 2) % S) - S / 2)) / 0.9, 0, 1)   # w14 (B): blocks fill ~0.6 of the row (py_37301)
              # w11: ~4.5 mm cells, soft edges (w12 B: 2.0 -> 1.3, w13 B: 0.9)
            lite = np.maximum(lite, band[:, None] * seg[None, :] * np.clip(rng.normal(1, 0.25), 0.5, 1.5) * dim[r, c])
            # w6 (A + B): the navy-slate dash set (py_37301 / 37305 dark-dash cover 7-32 %); w7: on its own band between
            # the light rows so the two sets interlock into a mosaic (A + B)
            band = np.clip((2.8 - np.abs(((y[:, 0] - yr[r] - hr[r] / 2 + S / 2) % S) - S / 2)) / 0.8, 0, 1)
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
    lite *= 0.88 + 0.22 * thr;   # w13 (B): flatter blocks
    dark *= 0.85 + 0.25 * thr   # w12 (A + B): the w11 threads overshot into a melange
    out = (1 + 1.75 * lite) * (1 - 0.7 * dark)     # w7: light ~2.9x, dark ~0.3x the ground; w12 (A + B): back std / float cover to py_37301 / 37305
    out *= 0.88 + 0.24 * thr                       # w11: the ground is woven too (threads read between the blocks, py_37305)
    # brick patches on a 2-col x 2-row lattice (block std/mean ~0.15, py_37305), crisp edges softened 0.5 px
    blk = np.exp(rng.normal(0, 0.18, (rows // 2, cols // 2)))
    blk = _blur_wrap(blk[(np.arange(S) // (2 * ph)).astype(int)][:, (np.arange(S) // (2 * cw)).astype(int)], 3.0)   # w12 (A): no hard square patch
    out *= blk
    mot = _blur_wrap(ratio.mean(2), 24); mot = (mot - mot.mean()) / (mot.std() + 1e-6)
    out *= np.exp(0.05 * mot)                      # very weak low-frequency term only
    out *= np.exp(0.06 * _blur_wrap(rng.normal(0, 1, (S, S)), 0.6) / 0.3)   # fine weave grain
    return np.repeat(out[:, :, None], 3, 2)


def synth_py_confetti(ratio, seed=11, ear=False):
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
    while len(pts) < (26 if ear else 50):   # w13: ear 18 chunky chips (A, py_37305 ~40 per ear); back 50 (B, py_37302 cover 0.09)                          # w5 (A + B): varied chips; w11 (gap): 32 smaller ones (san_12 / py_37305)
        p = rng.uniform(0, S, 2)
        if all(min(abs(p[0] - q[0]), S - abs(p[0] - q[0])) ** 2 + min(abs(p[1] - q[1]), S - abs(p[1] - q[1])) ** 2 > (24 if ear else 21) ** 2 for q in pts): pts.append(p)
    for cy, cx in pts:
        dy = (yy - cy + S / 2) % S - S / 2; dx = (xx - cx + S / 2) % S - S / 2
        a = rng.uniform(0, 2 * np.pi); e = rng.uniform(1.4, 2.2) if ear else rng.uniform(1.8, 3.2)   # w12 (B): 2-3:1 slivers on the trim-B back (py_37302, san_12)
        req = np.clip(np.exp(rng.normal(np.log(7), 0.35)), 4, 12) if ear else np.clip(rng.normal(5.5, 1.8), 3, 8.5)   # w13 (A): ear chips chunky, mixed size (py_37305)
        u = dx * np.cos(a) + dy * np.sin(a); v = -dx * np.sin(a) + dy * np.cos(a)
        th = np.arctan2(v * e, u); rr = np.hypot(u / np.sqrt(e), v * np.sqrt(e))
        k = rng.integers(4, 6) if ear else rng.integers(5, 8); ph0 = rng.uniform(0, 6)
        # polygonal chip: facets from a k-gon, pointed tip at th=0, shallow notch at th=pi (sakura petal)
        poly = (np.cos(np.pi / k) / np.cos((th + ph0) % (2 * np.pi / k) - np.pi / k)) ** 1.0   # sharp facets
        nd = 0.35 if ear and rng.random() < 0.6 else 0.22   # w13 (A): deep notch on the ear chips; w14 (A + B): 60 %, wider, pointed tips
        tip, nw = (0.35, 0.45) if ear else (0.18, 0.25)
        prof = req * poly * (1 + tip * np.cos(th)) * (1 - nd * np.exp(-((np.abs(th) - np.pi) / nw) ** 2))
        out += (4.2 if ear else 4.8) * np.clip(rng.normal(1, 0.15), 0.7, 1.3) * np.clip((prof - rr) / 0.6, 0, 1)   # w11: crisper corners
    for cy, cx in rng.uniform(0, S, (140 if ear else 60, 2)):   # w13 (A): dense tiny specks on the ear
        rr = np.hypot((yy - cy + S / 2) % S - S / 2, (xx - cx + S / 2) % S - S / 2)
        out += rng.uniform(0.3, 0.6) * np.clip((rng.uniform(2, 5) - rr) / 1.0, 0, 1)
    for cy, cx in rng.uniform(0, S, (40 if ear else 0, 2)):   # w12 (B): round mid specks dropped on the back; w14 (B): 40 small bright elongated flecks on the ear
        dy = (yy - cy + S / 2) % S - S / 2; dx = (xx - cx + S / 2) % S - S / 2; a = rng.uniform(0, np.pi); e = rng.uniform(1.3, 2.0)
        rr = np.hypot((dx * np.cos(a) + dy * np.sin(a)) / np.sqrt(e), (-dx * np.sin(a) + dy * np.cos(a)) * np.sqrt(e))
        out += rng.uniform(3.0, 4.0) * np.clip((rng.uniform(2, 3.5) - rr) / 0.8, 0, 1)   # w11: faint (read as snow on the trim-B backs)
    out *= np.exp(0.08 * _blur_wrap(rng.normal(0, 1, (S, S)), 0.8) / 0.25)
    return np.repeat(out[:, :, None], 3, 2)


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


SYNTH = {'py_back': synth_py_back, 'py_confetti': lambda r: synth_py_confetti(r, seed=17),   # w14 (B): seed 17, no stamped Y clusters
         'py_ear': lambda r: synth_py_confetti(r, ear=True), 'j_pillow': synth_j_pillow}


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


# econ wave 3c (fresh eyes): the four Y fabrics are cut DIRECTLY from the official ANA photos (the user's request: "reuse
# the texture of the official website images"). Six re-syntheses over w5-w13 (tick columns, diamond lattices, petal
# flecks, dash bricks) never got past 6-7 with the raters. Each crop is the most frontal, evenly lit patch of that fabric
# in the 930 x 575 photos; scale from the 0.255 m headrest cover (or the 0.43 m back) in the same photo [D].
# name: (photo, box, tile size m, high-pass sigma in source px, rotation deg (PIL, + = ccw), sharpen, contrast exponent,
#        soft floor). The last two match the rendered contrast to the photo's own L p10/p50/p90 at the same scale
#        (JPEG blocks and the upsampling left the darks too deep: c1 tick p10/p50 0.39 vs 0.55 in y_47306; w15 B: then too flat
#        at row distance - tick p90/p50 1.81 vs 2.27, mosaic 1.59 vs 2.14; diamond stars ~20 % too strong) [D]
Y_PHOTO = {
    # middle seat back, chevron tick columns; cover 0.27 m = 165 px -> 611 px/m, 152 px = 0.249 m [D]
    # econ w20 (gap19): the crop's columns lean 7 deg (oblique seat) and cancelled out over a back -> rotated upright; 0.29 m
    # (~13 mm column pitch, y_47300); floor 0.05 so the dark channels reach the photo's p10 [D]
    'y_tick':    ('y_47306', (260, 385, 412, 537), 0.29, 14, 7, 0.15, 0.95, 0.10),     # w20 A: floor 0.05 -> 0.10 (harsh close up)
    # left seat back, harlequin diamonds; seen obliquely: cover 108 px wide (423 px/m) but 133 px tall for 0.235 m
    # (566 px/m) -> the 82 x 115 crop is stretched 1.34x in x to a square 0.203 m [D]
    'y_diamond': ('y_47306', (62, 358, 144, 473), 0.203, 30, 0, 0.3, 0.8, 0.0),
    # y_47300 front-row seat 2 back (the only frontal, evenly lit fleck back): back 0.43 m = 127 px -> 295 px/m, 95 px =
    # 0.32 m; but at 0.32 the fleck pitch in q15 was ~1.2x the photo's, and at 0.27 the flecks read ~1.3 cm against ~0.6 cm
    # (w15 B) and 27 % bright against 11 % -> cores only, tinted pale blue; at 0.18 m they vanished at row distance (w16 A
    # + B: 8 % vs 21 % cover in q15) -> 0.24 m; w17: round pebbles close up and too blue (B/R 2.05 vs 1.62) -> cores
    # near-neutral tint; pinching the cores (w18) lost them at row distance again -> w17 cores [D]
    'y_fleck':   ('y_47300', (352, 308, 447, 403), 0.24, 8, 0, 0.0, 0.8, 0.15),     # w20 (gap19): floor 0.3 flattened the ground
    # right seat back below the cover: dash mosaic; cover 0.255 m = 270 px -> 1059 px/m, 135 px = 0.128 m [D]; rows
    # levelled by 3 deg (perspective tilt)
    'y_mosaic':  ('y_47306', (560, 427, 695, 562), 0.128, 14, 3, 0.3, 1.15, 0.1),
}


def _wrap_resize(x, n, pad=8):
    """resize a periodic h x w image to n x n with bicubic on a wrap-padded copy (a plain resize treats the edges as
    borders - dark dots at the tile corners, c3; a Fourier resample rang round the bright flecks - dark halos, w15 A)"""
    h, w = x.shape
    p = np.pad(x, pad, mode='wrap').astype(np.float32)
    W, H = int(round((w + 2 * pad) * n / w)), int(round((h + 2 * pad) * n / h))
    y = np.asarray(Image.fromarray(p, mode='F').resize((W, H), Image.BICUBIC))
    oy, ox = int(round(pad * n / h)), int(round(pad * n / w))
    return y[oy:oy + n, ox:ox + n]


def _gblur(x, s):
    """gaussian blur with reflected edges (numpy only)"""
    r = int(3 * s) + 1; k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    p = np.pad(x, r, mode='reflect')
    p = np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 0, p)
    return np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 1, p)


def _wrap_cut(a, o):
    """make a crop of (h + o) x (w + o) wrap in source pixels: the o columns past the right edge continue the left edge
    up to a minimum-error seam (image quilting, Efros-Freeman), then the same for rows. c2: a plain wrap left a visible
    vertical line on the tick backs where a stitch column was cut in two"""
    def cut_x(a):
        w = a.shape[1] - o
        e = ((a[:, w:w + o] - a[:, :o]) ** 2).sum(2)
        cost = e.copy(); back = np.zeros(e.shape, int)
        for i in range(1, e.shape[0]):
            for j in range(o):
                lo, hi = max(0, j - 1), min(o, j + 2)
                k = lo + int(np.argmin(cost[i - 1, lo:hi])); back[i, j] = k; cost[i, j] += cost[i - 1, k]
        j = int(np.argmin(cost[-1])); out = a[:, :w].copy()
        for i in range(e.shape[0] - 1, -1, -1):
            out[i, :j] = a[i, w:w + j]; j = back[i, j]
        return out
    a = cut_x(a)
    return cut_x(a.transpose(1, 0, 2)).transpose(1, 0, 2)


def _thin_flecks(e, ep, keep, seed, th=0.2, trim=0.04):
    """drop a random (fixed-seed) share of the fleck components of the excess map e (pixels over th * ep, labelled with
    wrap-around 8-connectivity); a fleck closer to a kept one than 1.2x their summed sizes is dropped first, so
    merged clusters thin out. Dropped components fade over a 1 px rim; kept cores lose their soft skirt (trim * ep)"""
    n = e.shape[0]; lum = e.mean(2); mask = lum > th * ep
    lab = -np.ones(lum.shape, int); comps = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0] >= 0: continue
        k = len(comps); lab[y0, x0] = k; st = [(y0, x0)]; pts = []
        while st:
            y, x = st.pop(); pts.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = (y + dy) % n, (x + dx) % n
                    if mask[yy, xx] and lab[yy, xx] < 0: lab[yy, xx] = k; st.append((yy, xx))
        comps.append(np.array(pts))
    rng = np.random.default_rng(seed); order = rng.permutation(len(comps))
    cen = [np.array([np.angle(np.exp(2j * np.pi * c[:, i] / n).mean()) * n / (2 * np.pi) % n for i in (0, 1)]) for c in comps]
    size = [max(2.0, np.sqrt(len(c))) for c in comps]
    kept, drop = [], np.zeros(len(comps), bool)
    for k in order:
        near = any(np.hypot(*((cen[k] - cen[j] + n / 2) % n - n / 2)) < 1.2 * (size[k] + size[j]) for j in kept)
        if near or len(kept) >= keep * len(comps): drop[k] = True
        else: kept.append(k)
    dm = np.isin(lab, np.nonzero(drop)[0]).astype(np.float32)
    dm = np.maximum(dm, _blur_wrap(dm, 0.7) * 1.5).clip(0, 1)          # 1 px soft rim round the dropped flecks
    out = e * (1 - dm)[..., None]
    print('flecks kept', len(kept), 'of', len(comps))
    return np.maximum(out - trim * ep, 0) / (1 - trim), dm


def y_photo(name):
    """cut a Y fabric tile straight from the photo: lighting removed by dividing by a blurred luminance computed on a
    padded crop (no edge bias, chroma of the pale yarns kept), resampled to 256 px, made periodic, lightly sharpened
    (the sources are ~1-3 mm/px)"""
    photo, box, size, hp, rot, sharp, k, floor = Y_PHOTO[name]
    im = Image.open(os.path.join(root, 'ref/ana', photo + '-lang-multi.jpg')).convert('RGB')
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, center=((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))
    a = (np.asarray(im).astype(np.float32) / 255) ** 2.2
    m = int(3 * hp); x0, y0, x1, y1 = box
    px0, py0 = max(0, x0 - m), max(0, y0 - m)
    P = a[py0:y1 + m, px0:x1 + m]
    # normalised convolution over the fabric only (blue-dominant pixels): the white shell, window and grey cover next to
    # a crop would otherwise lift the blurred light and leave dark rims along the crop edges
    fab = ((P[..., 2] > 1.6 * P[..., 0]) & (P[..., 2] < 0.75)).astype(np.float32)
    low = _gblur(P.mean(2) * fab, hp) / np.maximum(_gblur(fab, hp), 1e-3)
    r = P / np.maximum(low, 1e-4)[..., None]
    o = 12                                              # overlap for the seam cut (the box must leave o px of fabric right / below)
    r = _wrap_cut(r[y0 - py0:y1 - py0 + o, x0 - px0:x1 - px0 + o], o)
    r = np.stack([_wrap_resize(r[..., c], S) for c in range(3)], 2)     # wrapped tile: no edge seam
    # second flattening on the periodic tile (wrap blur): a residual shading gradient inside the crop repeats as a visible
    # grid of light / dark squares (c3 fleck / mosaic)
    r = r / np.maximum(_blur_wrap(r.mean(2), 2.5 * hp * S / (x1 - x0)), 1e-3)[..., None]
    # w30 (w29b-4): a dark cloud repeated at the same spot on every fleck back (low-pass CV 0.055 vs 0.030-0.037) -> a
    # tighter second flattening for the fleck [D]
    if name == 'y_fleck': r = r / np.maximum(_blur_wrap(r.mean(2), 1.2 * hp * S / (x1 - x0)), 1e-3)[..., None]
    if sharp: r = r + sharp * (r - _blur_wrap_rgb(r, 1.5))
    r = np.maximum(r, 0.03) ** k
    if floor: r = np.sqrt(r * r + floor * floor)       # lift the darkest yarn shadows only
    if name == 'y_tick':
        # w16 A: the stitch columns wash out under minification (q15 column CV 0.05-0.07 vs 0.24 in y_47300): lift the
        # photo's own column profile (mean down each column) 1.6x so the dark channels survive the mip chain [D]
        c = r.mean(2).mean(0, keepdims=True); c = c / c.mean()
        r = r * (c ** 0.5)[..., None]   # w31 (w30a-1): 0.3 -> 0.5, the distance contrast without the near-black texels   # w30 (w29a-3 / w29b-2): 0.15 -> 0.3, the column profile is what survives the mip chain (q15 back p90/p10 2.36 vs 2.92 after the deeper ground)   # w20 (gap19): straight columns carry their own profile; 0.6 over-sharpened close up
        m = np.median(r.mean(2)); r = np.where(r.mean(2, keepdims=True) > m, m + 0.72 * (r - m), r)   # w26 (w25a-3): 0.65 dimmed instead of thinning -> 0.72 + edge erosion below; w25 (w23a-2 / w23b-1): 0.8 -> 0.65 (q15 bright 0.12 vs 0.083; ~0.02 per 0.1)   # w21 / w22 B: strokes toward the ground (q15 bright 0.14 vs 0.083 after the -0.5 mip bias)
        # w26 (w25a-3 / w25b-2): strokes 1.5x the photo's coverage, blobs ~1.4x fat -> the stroke rim (above-median pixels with a
        # sub-median 4-neighbour) eases 60 % toward the ground, cores keep their peak [D]
        hi = r.mean(2) > m; core = hi & np.roll(hi, 1, 0) & np.roll(hi, -1, 0) & np.roll(hi, 1, 1) & np.roll(hi, -1, 1)
        r = np.where((hi & ~core)[..., None], m + 0.5 * (r - m), r)   # w31 (w30a-1): 0.55 -> 0.5 (chunky at row distance)   # w30 (w29a-3 / w29b-2): 0.4 -> 0.55 (strokes a hair fine, bright 0.09 vs 0.14)
        # w30 (w29a-3 / w29b-2): the ground was too light (q15 back p10 52-56 vs 30-46, p90/p10 2.1-2.5 vs 2.9-3.4) with the
        # stroke cover on target -> deepen the sub-median channels only [D]
        # w31 (w30a-1 / w30b-2): per-channel it went near-black / ultramarine close up -> scale luminance only, deepening stops at 0.5 m (w32, w31a-1 / w31b-3: 0.42 m, row distance washed);
        # the row-distance contrast now comes from the 0.5-2.5 cm band boost below (tick 0.1 -> 0.35)
        lu = r.mean(2, keepdims=True); r = np.where(lu < m, r * np.maximum(m - 1.25 * (m - lu), np.minimum(lu, 0.42 * m)) / np.maximum(lu, 1e-4), r)
    if name == 'y_diamond':
        # econ w25 (w23b-2): the lattice washed out on the bluer #5f6ba0 ground (e4 bright 0.03 vs 0.11 in y_47306) -> 1.25x [D]
        # w30 (w29a-2 / w29b-7): the stars read bold and few at row distance (q15 back coverage 0.23 vs 0.12, blobs 21 vs 7 px)
        # while the weave between them was faint -> the > 4 px star band 0.7x, the fine weave 1.15x [D]
        m = np.median(r.mean(2)); lo = _blur_wrap_rgb(r, 4); r = np.maximum(m + 0.7 * 1.05 * (lo - m) + 1.15 * (r - lo), 0.03)   # w26 (w25a-1 / w25b-1): 1.25 overshot (e1 p90/50 1.79 vs 1.51)
    if name == 'y_fleck':
        # the 3.4 mm/px source smears each 3-5 mm fleck over ~3 px: keep only the core of the excess over the ground
        # (bright area 27 % -> ~12 %, y_47306 pad 11 %) and tint it pale blue (#9fb0e0 vs white, w15 A) [D]
        g = np.median(r.mean(2)); e = np.maximum(r - g, 0); ep = e.max()
        # econ w25 (w23a-1): the tile carried ~2x the photo's flecks close up (e4 pad coverage 0.29 vs 0.13 in y_47306,
        # merged clusters) and the exponent only dimmed them: drop ~30 % of the fleck components (fixed seed, a kept fleck
        # clears the flecks touching it, so merged clusters break up) and trim the soft skirts, exponent 1.0, flecks 1.1x [D]
        e, dm = _thin_flecks(e, ep, keep=0.8, seed=24, trim=0.0)   # w26 (w25a-2 / w25b-3): keep 0.7 + trim read as dust at row distance
        # a dropped fleck and its dark sharpening halo become the surrounding ground (a flat g read brown) [D]
        base = np.minimum(r, g); dd = np.clip(_blur_wrap(dm, 1.5) * 2.0, 0, 1)
        out = (1 - np.clip(dd * 3, 0, 1)).astype(np.float32)        # the local ground around each dropped fleck fills it
        gl = np.stack([_blur_wrap(base[..., c] * out, 3.0) for c in range(3)], 2) / np.maximum(_blur_wrap(out, 3.0), 1e-3)[..., None]
        r = base * (1 - dd[..., None]) + gl * dd[..., None] + 1.35 * ep * (e / ep) ** 1.0 * np.array([1.02, 1.0, 0.92], np.float32)   # w30 (w29a-7): 1.25 -> 1.35 (q15 fleck p90/p10 0.88x the photo's)   # w25 (w24a-2): distance flecks weak (p90/p10 2.48 vs 3.05)   # w20 A + B: fewer, less blue cores (B/R 3.0 vs 2.54); w22 B: exp 1.2 (bright 0.18 vs 0.153 after the mip bias)   # w20 (gap19): 1.25 thinned the flecks away at row distance
    # w20 (gap19): the 0.5-2.5 cm band (columns, flecks, dashes) is what survives at row distance; boost it in log luminance and
    # damp the < 1.2 mm JPEG grain (tile CV at 150 px/m: tick 0.31 vs 0.46-0.49 in y_47300, fleck 0.31 vs 0.84) [D]
    # w20 A + B: the full boost overshot (q15 tick bright 0.15 vs 0.083, fleck 0.20 vs 0.154) -> half on tick / fleck
    gb, gf = {'y_tick': (0.45, 0.3), 'y_fleck': (0.6, 0.0), 'y_mosaic': (0.6, 0.2)}.get(name, (0.0, 0.0))
    if gb or gf:
        lg = np.log(np.maximum(r.mean(2), 1e-3)); ppm = S / size
        b1, b2, b0 = _blur_wrap(lg, 0.005 * ppm), _blur_wrap(lg, 0.025 * ppm), _blur_wrap(lg, 0.0012 * ppm)
        r = r * np.exp(gb * (b1 - b2) - gf * (lg - b0))[..., None]
    r /= r.reshape(-1, 3).mean(0)
    enc = ENC[name]
    lum = r.mean(2, keepdims=True); lim = enc * 0.95                # clip glints (as make())
    r = np.where(lum > lim, r * lim / np.maximum(lum, 1e-6), r)
    r /= r.reshape(-1, 3).mean(0)
    print(name, 'L p10/50/90', np.percentile(r.mean(2), [10, 50, 90]).round(2))
    Image.fromarray((np.clip(r / enc, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', f'tex_{name}.png'))
    return size


def _blur_wrap_rgb(a, s):
    return np.stack([_blur_wrap(a[..., c], s) for c in range(a.shape[2])], 2)


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


def s_pleat():
    """shell w12: blackout pleat valleys as a mip-mapped stripe tile (the per-row vertex-colour stripe could not filter and
    beat into moire on the 3rd-7th windows; w12a also measured its close-up contrast at cv 0.14 vs 0.33 on omaat_room24).
    07_shell.js shadePanelGeo: 31 pleats over the 0.445 m opening, closed blackout valleys at world y = 0.795846 + k * 0.0144755
    (measured in the page, the same at every window) [D]. The tile holds 8 periods (0.115804 m) on its v axis (world y
    in the triplanar x / z projections), phase-locked to those valleys: a ramp from the lit crest down to a
    valley at ~x0.55 in sRGB (omaat_room24, sRGB cv 0.33-0.35) [V: contrast; A: profile], a faint lit crest and a fine fabric grain."""
    n = 256; period = 0.0144755; size = 8 * period; y0 = 0.795846
    i = np.arange(n)[:, None] + 0.5
    ph = ((i / n * size - y0) / period) % 1.0                       # 0 at a valley
    # w13a: a narrow notch read as grooves on flat slats; omaat_room24 alternates lit and shaded faces ~50/50 -> a ramp:
    # quick rise out of the valley (20 %), lit crest, then a long shaded fall (55 %) back into the next valley [V: profile]
    rise = np.clip(ph / 0.2, 0, 1); fall = np.clip((ph - 0.45) / 0.55, 0, 1)
    f = np.where(ph < 0.2, rise * rise * (3 - 2 * rise), 1 - fall ** 1.3)
    rng = np.random.default_rng(5)
    grain = _blur_wrap(rng.standard_normal((n, n)), 0.8)
    r = (0.27 + 0.73 * f) * (1 + 0.025 * grain / grain.std())       # valley ~x0.55 of the crest in sRGB
    r = np.broadcast_to(r, (n, n)) / r.mean()
    print('s_pleat cv', round(float(r.std()), 3), 'valley/crest', round(float(r.min() / r.max()), 3))
    out = np.clip(np.repeat(r[:, :, None], 3, 2) / 2, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_s_pleat.png'))
    return round(size, 6)


def x_rivet():
    """exterior w17: fastener-row dot tile for the near-wing rows (gap analysis w16: the near flap / spoilers had no fine
    detail, high-pass SD 0.00 vs 1.5-3.0 on KN41's panels with rows). Synthetic, like s_pleat: universal-head fasteners
    ~8 mm across (head + crack ring) at a ~25 mm pitch [A, typical skin-splice pitch; KN41 rows ~4 px apart at ~6 mm/px], each a dark dot
    ~0.72 of the paint in sRGB with a faint lit rim (KN41 near spoiler rows, dark dots on the sunlit grey) [D contrast].
    The tile is 0.2 m = 8 x 8 dots; it is projected from above (triplanar), so a 50 mm strip along a swept row
    picks up a staggered double row. Mean 1 (stored / 2), so at range the mips fade to the strip's own colour."""
    n = 256; size = 0.2; pitch = n // 8
    y, x = np.mgrid[0:n, 0:n] + 0.5
    dx = (x % pitch) - pitch / 2; dy = (y % pitch) - pitch / 2; r = np.hypot(dx, dy) * size / n * 1000   # mm
    f = 1 - 0.30 * np.clip((4.2 - r) / 1.4, 0, 1) + 0.06 * np.exp(-((r - 4.6) / 0.7) ** 2)   # t17: 6 mm dots fell to 1 px specks; ~8 mm (head + paint crack ring) [A]
    rng = np.random.default_rng(7)
    f = f * (1 + 0.01 * _blur_wrap(rng.standard_normal((n, n)), 1.5))
    f = f / f.mean()
    print('x_rivet min/mean', round(float(f.min()), 3), round(float(f.mean()), 3))
    out = np.clip(np.repeat(f[:, :, None], 3, 2) / 2, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_x_rivet.png'))
    return size


def x_cowl():
    """exterior w18: fan-cowl weathering tile (soft grey mottle on the white GE90 cowls, LALF ANA 11A _136: inlet and fan cowl
    panels clear of the access panel, splits and the strake). The x_skin recipe without the flow smear (that streaked the
    cowl vertically through the side projection, gap w16), luminance-only, skewed dark, stored at SD 0.08. Tile 1.5 m
    [A: the 4.2 m cowl spans ~600 px of _136 -> 180 px ~ 1.3 m]"""
    srcs = [('web/exterior/b_lalf_ANA77W_11A_136.jpg', (300, 790, 470, 940)),     # inlet cowl below the access panel
            ('web/exterior/b_lalf_ANA77W_11A_136.jpg', (60, 760, 220, 900))]      # fan cowl above the strake
    acc = 0
    for f, box in srcs:
        im = Image.open(os.path.join(root, 'ref', f)).convert('L').crop(box).filter(ImageFilter.MedianFilter(3))
        im = im.resize((S, S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
        a = (np.asarray(im).astype(np.float32) / 255.0) ** 2.2
        b = np.asarray(im.filter(ImageFilter.GaussianBlur(48))).astype(np.float32) / 255.0
        r = np.clip(a / np.maximum(b ** 2.2, 1e-3), 0.8, 1.2)
        acc = acc + tileable((r / r.mean())[:, :, None])[:, :, 0]
    r = acc / len(srcs)
    r = np.where(r > 1, 1 + (r - 1) * 0.5, r)   # grime darkens
    r = r / r.mean()
    r = 1 + (r - 1) * (0.08 / max(float(r.std()), 1e-4))
    print('x_cowl sd', round(float(r.std()), 4), 'p5/p95', np.percentile(r, [5, 95]).round(3))
    out = np.clip(np.repeat(r[:, :, None], 3, 2) / 2, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(root, 'tex', 'tex_x_cowl.png'))
    return 1.5


if __name__ == '__main__':
    os.makedirs(os.path.join(root, 'tex'), exist_ok=True)
    import json, sys
    # optional names on the command line re-cut only those tiles (the others keep their sizes.json entries)
    only = sys.argv[1:]
    sizes = json.load(open(os.path.join(root, 'tex/sizes.json'))) if only else {}
    sizes.update({k: make(k, *v) for k, v in SW.items() if not only or k in only})
    sizes.update({k: y_photo(k) for k in Y_PHOTO if not only or k in only})
    if not only or 'x_skin' in only: sizes['x_skin'] = x_skin()
    if not only or 'g_alu' in only: sizes['g_alu'] = g_alu()
    if not only or 's_pleat' in only: sizes['s_pleat'] = s_pleat()
    if not only or 'x_rivet' in only: sizes['x_rivet'] = x_rivet()
    if not only or 'x_cowl' in only: sizes['x_cowl'] = x_cowl()
    json.dump(sizes, open(os.path.join(root, 'tex/sizes.json'), 'w'))
    print('swatches', sizes)
