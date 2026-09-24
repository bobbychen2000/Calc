#!/usr/bin/env python3
"""Offline multi-channel signed distance field (MSDF) glyph atlas for the airfield / gate / VDGS signs of the three.js
renderer (live3.html). Output: js/three/assets/msdf_signs.png (RGB = MSDF, A = true SDF) + msdf_signs.json (metrics).

Why offline: the sign strings are data-driven (holds, stands, bridges, aircraft types) but their alphabet is small, so a
per-glyph atlas generated once renders any current or future string crisply at any distance (the current renderer
uses a 70 px Canvas2D bitmap atlas that blurs with mip-mapping; docs/qa/review_pass1.md #15).

Method (after V. Chlumsky, "Shape Decomposition for Multi-channel Distance Fields", 2015):
  1. glyph outlines from the TrueType font with fontTools (lines + quadratic Beziers, curves flattened to 12 segments);
  2. edge colouring: edges between corners (joins turning > TURN_DEG) cycle through
     cyan/magenta/yellow so that each channel sees a different subset of edges at every corner;
  3. per channel, the signed distance to the nearest edge of that channel (sign from the edge orientation);
     alpha = true signed distance to all edges (inside test by the non-zero winding rule);
  4. error correction: texels whose median(R,G,B) disagrees in sign with the true distance get the true distance.
Distances are stored as 0.5 + d / RANGE (0.5 = outline), RANGE in atlas pixels.

Fonts (SIL Open Font Licence 1.1, redistributable; the atlas is a derived rendering):
  sans: Liberation Sans Bold  (/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf) — stands in for the
        "Arial Narrow" bold of js/live/signs.js makeAtlas; the runtime condenses it to the same text width.
  mono: Liberation Mono Bold  (/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf) — VDGS ("Courier New").
Usage: python3 tools/build3/msdf_atlas.py [--size 44] [--range 6]
"""
import argparse, json, math, os
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONTS = {
    'sans': '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    'mono': '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf',
}
CHARS = ''.join(chr(c) for c in range(33, 127))  # printable ASCII (space is advance-only)
TURN_DEG = 20.0  # a join between two source segments that turns by more than this is a corner

def contours_of(glyphset, name):
    pen = RecordingPen(); glyphset[name].draw(pen)
    contours, cur, start = [], [], None
    for op, args in pen.value:
        if op == 'moveTo':
            cur = []; start = args[0]; last = args[0]
        elif op == 'lineTo':
            cur.append(('L', [last, args[0]])); last = args[0]
        elif op == 'qCurveTo':
            pts = list(args); ctrl = pts[:-1]; end = pts[-1]
            if end is None:  # closed contour of only off-curve points (not in these fonts)
                continue
            # expand implied on-curve points between consecutive off-curve points
            seq = [last]
            for i, c in enumerate(ctrl):
                seq.append(c)
                if i < len(ctrl) - 1:
                    n = ctrl[i + 1]; seq.append(((c[0] + n[0]) / 2, (c[1] + n[1]) / 2))
            seq.append(end)
            for i in range(0, len(seq) - 1, 2):
                cur.append(('Q', [seq[i], seq[i + 1], seq[i + 2]]))
            last = end
        elif op == 'curveTo':
            cur.append(('C', [last, args[0], args[1], args[2]])); last = args[2]
        elif op in ('closePath', 'endPath'):
            if cur and last != start: cur.append(('L', [last, start]))
            if cur: contours.append(cur)
            cur = []
    return contours

def flatten(seg, n=12):
    t, p = seg
    if t == 'L': return [p[0], p[1]]
    ts = np.linspace(0, 1, n + 1)
    if t == 'Q':
        a, b, c = map(np.array, p)
        return [tuple((1 - s) ** 2 * a + 2 * (1 - s) * s * b + s * s * c) for s in ts]
    a, b, c, d = map(np.array, p)
    return [tuple((1 - s) ** 3 * a + 3 * (1 - s) ** 2 * s * b + 3 * (1 - s) * s * s * c + s ** 3 * d) for s in ts]

def seg_dir(seg, at_end):
    t, p = seg
    if t == 'L': d = np.subtract(p[1], p[0])
    elif at_end: d = np.subtract(p[-1], p[-2]) if np.any(np.subtract(p[-1], p[-2])) else np.subtract(p[-1], p[0])
    else: d = np.subtract(p[1], p[0]) if np.any(np.subtract(p[1], p[0])) else np.subtract(p[-1], p[0])
    l = np.hypot(*d); return d / l if l > 0 else d

def color_edges(contour):
    """returns list of channel masks (bit0 R, bit1 G, bit2 B) per segment"""
    n = len(contour)
    corners = []
    for i in range(n):
        a = seg_dir(contour[i - 1], True); b = seg_dir(contour[i], False)
        cosang = float(np.dot(a, b))
        if cosang < math.cos(math.radians(TURN_DEG)): corners.append(i)
    WHITE, CYAN, MAGENTA, YELLOW = 7, 6, 5, 3
    if not corners: return [WHITE] * n
    cols = [0] * n; palette = [CYAN, MAGENTA, YELLOW]
    if len(corners) == 1:  # teardrop: split the contour in three
        s = corners[0]
        for k in range(n): cols[(s + k) % n] = palette[min(2, (3 * k) // max(1, n))] if n >= 3 else [MAGENTA, YELLOW][k % 2]
        return cols
    ci = 0
    for k in range(n):
        i = (corners[0] + k) % n
        if k > 0 and i in corners: ci = (ci + 1) % 3
        cols[i] = palette[ci]
    # the last run must differ from the first
    last_start = corners[-1]
    if cols[last_start] == cols[corners[0]]:
        for k in range(last_start, corners[0] + n):
            j = k % n
            if j == corners[0]: break
            cols[j] = palette[(ci + 1) % 3] if palette[(ci + 1) % 3] != cols[corners[0]] else palette[(ci + 2) % 3]
    return cols

def glyph_field(contours, x0, y0, W, H, scale, rng_px):
    """pixel centres (x0 + (i+0.5)/scale, ...) in font units; returns (H, W, 4) float distances in pixels"""
    segs, masks = [], []
    for c in contours:
        cols = color_edges(c)
        for seg, col in zip(c, cols):
            pts = flatten(seg)
            for k in range(len(pts) - 1):
                segs.append((pts[k], pts[k + 1])); masks.append(col)
    S = np.array(segs, dtype=np.float64)  # (n, 2, 2)
    M = np.array(masks)
    xs = x0 + (np.arange(W) + 0.5) / scale; ys = y0 + (np.arange(H) + 0.5) / scale
    PX, PY = np.meshgrid(xs, ys)  # (H, W)
    P = np.stack([PX.ravel(), PY.ravel()], 1)  # (N, 2)
    A = S[:, 0, :]; B = S[:, 1, :]; D = B - A; L2 = np.maximum((D ** 2).sum(1), 1e-12)
    AP = P[:, None, :] - A[None, :, :]  # (N, n, 2)
    t = np.clip((AP * D[None]).sum(2) / L2[None], 0, 1)
    Q = A[None] + t[..., None] * D[None]
    dist = np.hypot(P[:, None, 0] - Q[..., 0], P[:, None, 1] - Q[..., 1])  # (N, n)
    cross = D[None, :, 0] * AP[..., 1] - D[None, :, 1] * AP[..., 0]  # >0: point left of the segment
    # TrueType outer contours run clockwise: the inside is on the right of the direction of travel -> cross < 0
    # inside test (non-zero winding) for the true distance
    wind = np.zeros(len(P))
    for (a, b) in segs:
        ay, by = a[1], b[1]
        up = (ay <= P[:, 1]) & (by > P[:, 1]); dn = (ay > P[:, 1]) & (by <= P[:, 1])
        isl = (b[0] - a[0]) * (P[:, 1] - ay) - (P[:, 0] - a[0]) * (by - ay)
        wind += np.where(up & (isl > 0), 1, 0) - np.where(dn & (isl < 0), 1, 0)
    inside = wind != 0
    true_d = dist.min(1) * np.where(inside, 1, -1)
    out = np.zeros((len(P), 4))
    for ch in range(3):
        sel = (M & (1 << ch)) != 0
        if not sel.any(): out[:, ch] = true_d; continue
        dd = np.where(sel[None], dist, np.inf)
        j = dd.argmin(1); dmin = dd[np.arange(len(P)), j]
        # sign from the nearest segment; ties at shared vertices: take the segment whose infinite line is farther
        sgn = np.where(cross[np.arange(len(P)), j] < 0, 1.0, -1.0)
        out[:, ch] = dmin * sgn
    out[:, 3] = true_d
    # error correction: median sign must match the true inside test
    med = np.median(out[:, :3], axis=1)
    bad = np.sign(med) != np.sign(true_d)
    out[bad, :3] = true_d[bad, None]
    # beyond the distance range the channels carry no corner information: use the true distance there so that
    # mip-mapping and bilinear filtering never average stray single-channel blocks into the outline
    far = np.abs(true_d) * scale > rng_px
    out[far, :3] = true_d[far, None]
    return (out * scale).reshape(H, W, 4)  # font units -> pixels

def build(size, rng_px):
    meta = {'distanceRange': rng_px, 'size': size, 'fonts': {}, 'format': 'msdf+sdf(alpha)', 'yOrigin': 'top',
            'generator': 'tools/build3/msdf_atlas.py', 'sources': {k: os.path.basename(v) for k, v in FONTS.items()}, 'licence': 'fonts: SIL OFL 1.1 (Liberation)'}
    tiles = []
    for fk, path in FONTS.items():
        f = TTFont(path); upm = f['head'].unitsPerEm; gs = f.getGlyphSet(); cmap = f.getBestCmap(); hmtx = f['hmtx']
        os2 = f['OS/2']
        fm = {'unitsPerEm': upm, 'ascender': f['hhea'].ascent / upm, 'descender': f['hhea'].descent / upm, 'capHeight': getattr(os2, 'sCapHeight', 0.716 * upm) / upm, 'glyphs': {}}
        fm['glyphs'][' '] = {'advance': hmtx[cmap[32]][0] / upm}
        scale = size / upm  # px per font unit
        for ch in CHARS:
            cp = ord(ch)
            if cp not in cmap: continue
            gname = cmap[cp]; adv = hmtx[gname][0] / upm
            cs = contours_of(gs, gname)
            if not cs: fm['glyphs'][ch] = {'advance': adv}; continue
            pts = [p for c in cs for s in c for p in s[1]]
            xmin = min(p[0] for p in pts); xmax = max(p[0] for p in pts); ymin = min(p[1] for p in pts); ymax = max(p[1] for p in pts)
            pad = rng_px / scale
            x0 = math.floor((xmin - pad) * scale) / scale; y0 = math.floor((ymin - pad) * scale) / scale
            W = int(math.ceil((xmax + pad - x0) * scale)); H = int(math.ceil((ymax + pad - y0) * scale))
            fld = glyph_field(cs, x0, y0, W, H, scale, rng_px)
            tiles.append((fk, ch, fld[::-1], W, H, x0 / upm, y0 / upm, adv))  # flip rows: image y down
        meta['fonts'][fk] = fm
    # shelf packing
    AW = 1024; x = y = 1; rowh = 0; place = []
    for t in sorted(tiles, key=lambda t: -t[4]):
        fk, ch, fld, W, H = t[:5]
        if x + W + 1 > AW: x = 1; y += rowh + 1; rowh = 0
        place.append((t, x, y)); x += W + 1; rowh = max(rowh, H)
    AH = 1 << int(math.ceil(math.log2(y + rowh + 1)))
    img = np.zeros((AH, AW, 4), dtype=np.float64); img[...] = -rng_px  # outside
    for (fk, ch, fld, W, H, px0, py0, adv), ax, ay in place:
        img[ay:ay + H, ax:ax + W] = fld
        # plane bounds (em units, y up from the baseline) of the texel rectangle
        meta['fonts'][fk]['glyphs'][ch] = {'advance': adv, 'atlas': [ax, ay, W, H], 'plane': [px0, py0, px0 + W / size, py0 + H / size]}
    enc = np.clip(np.round((0.5 + img / (2 * rng_px)) * 255), 0, 255).astype(np.uint8)
    meta['atlas'] = {'width': AW, 'height': AH, 'encoding': 'v = 0.5 + d / (2 * distanceRange), d in atlas px, inside positive'}
    return enc, meta

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--size', type=int, default=44); ap.add_argument('--range', type=float, default=6)
    a = ap.parse_args()
    enc, meta = build(a.size, a.range)
    out = os.path.join(ROOT, 'js', 'three', 'assets'); os.makedirs(out, exist_ok=True)
    Image.fromarray(enc, 'RGBA').save(os.path.join(out, 'msdf_signs.png'), optimize=True)
    with open(os.path.join(out, 'msdf_signs.json'), 'w') as f: json.dump(meta, f, separators=(',', ':'))
    print('atlas', enc.shape, 'glyphs', sum(len(v['glyphs']) for v in meta['fonts'].values()))
