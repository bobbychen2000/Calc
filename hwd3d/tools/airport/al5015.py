"""FAA airport diagram AL-5015 (HWD, d-TPP cycle 2611; refs/cache/faa/05015ad_2611.pdf, public domain) in the world
frame: hot-spot ellipses and area labels, georeferenced by the affine fit of the diagram to the four NASR runway ends
that tools/osm/xcheck_osm_faa.py computed (refs/cache/osm/khwd_osm_xcheck.json al5015.affine_px_to_world; residuals
0.4-0.7 m since the 2026-11-12 fix of the 28R bar end there - 15-31 m before, when the HS 4 ring cut the bar; see
docs/phase1_crosscheck.md). The TPP legend (refs/cache/faa/tpp_frntmatter_2611_p16.pdf) states "Positional
accuracy within +-600 feet unless otherwise noted on the chart", so everything placed from it is inferred (src 'inf'),
although the HWD diagram measures much better than that (runway bars to scale within 0.7 m, hangar blocks 89-99 %
covered by the OSM footprints: tools/plot_overlays.py).

New for hwd3d. Needs pdftoppm and pdftotext (poppler) on PATH; the raster is made in a temporary directory at
DPI 400 (the resolution the affine was fitted at).

Hot spots: the diagram draws each hot spot as a brown ellipse joined by a leader line to a boxed label "HS n"
(colour of the label boxes on the 400 dpi raster: RGB 149, 81, 1). Brown pixels are segmented (R - B > 60,
R > G + 25, G > B + 20), connected components with > 2000 px are taken, the label box (the text-layer bounding box of
"HS" + digit, grown by BOX_PAD px) is cut out of the ring after it is closed (smallest disk of 8-32 px that encloses an
interior: the HS 2 ring is broken by an arrow) and filled; an opening with a
9 px disk removes the thin leader line; the ellipse with the same centre and second moments as the filled region (semi-axes
2 sqrt(eigenvalues of the covariance)) is sampled at 48 points and mapped to the world frame.
"""
import json, math, os, subprocess, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.abspath(os.path.join(HERE, '..', '..'))
PDF = os.path.join(HWD, 'refs', 'cache', 'faa', '05015ad_2611.pdf')
XCHECK = os.path.join(HWD, 'refs', 'cache', 'osm', 'khwd_osm_xcheck.json')
DPI = 400
K = DPI / 72.0
BOX_PAD = 30

# AL-5015 2611 labels used here, with the PDF text-layer words that make them (pdftotext -bbox; points from the top-left
# corner of the 387.36 x 594 pt page) - asserted against the text layer at run time.
LABELS = [
    ('GA TRANSIENT RAMP', [('GA', 120.0, 300.7), ('TRANSIENT', 127.5, 288.4), ('RAMP', 135.0, 296.0)]),
    ('FBO RAMP', [('FBO', 89.5, 307.8), ('RAMP', 97.0, 303.5)]),
    ('FBO RAMP', [('FBO', 193.9, 141.9), ('RAMP', 198.9, 137.4)]),
    ('FBO RAMP', [('FBO', 271.1, 255.3), ('RAMP', 278.6, 246.3)]),
    ('28L RUN-UP', [('28L', 270.3, 96.1), ('RUN-UP', 277.8, 90.7)]),
    ('EAST HANGARS', [('EAST', 230.6, 115.9), ('HANGARS', 236.9, 109.2)]),
    ('TERMINAL/AIRPORT ADMINISTRATION', [('TERMINAL/AIRPORT', 127.9, 155.6), ('ADMINISTRATION', 135.4, 160.0)]),
    ('TWR', [('TWR', 134.3, 254.8)]),
    ('FIRE STATION', [('FIRE', 330.5, 214.6), ('STATION', 338.0, 209.4)]),
]
# "WEST HANGARS" is set letter by letter along a curve in the text layer (W, E, S, T, H, A, N, G, A, R, S at
# x 58-81 pt, y 314-351 pt): its anchor is the mean of these glyph boxes. WEST_HANGARS_BOX (x0, y0, x1, y1 in pt) is that
# glyph range read from pdftotext -bbox, padded by about 3-5 pt by hand (basis: the text layer; labels() asserts that the
# box holds exactly the 11 letters, so a different cycle of the chart fails loudly instead of silently)
WEST_HANGARS_BOX = (55.0, 312.0, 84.0, 356.0)


def words():
    out = subprocess.run(['pdftotext', '-bbox', PDF, '-'], check=True, capture_output=True, text=True).stdout
    import re
    W = []
    for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', out):
        W.append((m.group(5), *map(float, m.group(1, 2, 3, 4))))
    return W


def affine():
    A = json.load(open(XCHECK))['al5015']
    return np.array(A['affine_px_to_world']), A['fit_resid_m']


def px_to_world(M, px, py):
    v = np.c_[np.atleast_1d(px), np.atleast_1d(py), np.ones(np.size(px))] @ M
    return v


def _boxes_xz(M, boxes):
    """text-layer word / glyph boxes (pt) -> world rings (4 corners each, 0.1 m): where the label text is printed"""
    out = []
    for x0, y0, x1, y1 in boxes:
        P = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]) * K
        out.append([[round(float(a), 1), round(float(b), 1)] for a, b in px_to_world(M, P[:, 0], P[:, 1])])
    return out


def labels(W, M):
    """label anchors (centre of the text) and boxes_xz (one world ring per word / glyph of the label text)"""
    out = []
    for text, parts in LABELS:
        boxes = []
        for w, x0, y0 in parts:
            hit = [b for b in W if b[0] == w and abs(b[1] - x0) < 0.3 and abs(b[2] - y0) < 0.3]
            assert len(hit) == 1, 'AL-5015 text layer: word %r at %.1f, %.1f not found' % (w, x0, y0)
            boxes.append(hit[0][1:])
        b = np.array(boxes); cx = (b[:, 0].min() + b[:, 2].max()) / 2; cy = (b[:, 1].min() + b[:, 3].max()) / 2
        xz = px_to_world(M, cx * K, cy * K)[0]
        out.append(dict(text=text, pdf_pt=[round(cx, 1), round(cy, 1)], x=round(float(xz[0]), 1), z=round(float(xz[1]), 1),
                        boxes_xz=_boxes_xz(M, boxes)))
    gl = [b for b in W if len(b[0]) <= 2 and WEST_HANGARS_BOX[0] <= b[1] <= WEST_HANGARS_BOX[2] and WEST_HANGARS_BOX[1] <= b[2] <= WEST_HANGARS_BOX[3]]
    letters = ''.join(sorted(b[0] for b in gl))
    assert sorted('WESTHANGARS') == sorted(letters), 'WEST HANGARS glyphs: %r' % letters
    cx = np.mean([(b[1] + b[3]) / 2 for b in gl]); cy = np.mean([(b[2] + b[4]) / 2 for b in gl])
    xz = px_to_world(M, cx * K, cy * K)[0]
    out.append(dict(text='WEST HANGARS', pdf_pt=[round(float(cx), 1), round(float(cy), 1)], x=round(float(xz[0]), 1), z=round(float(xz[1]), 1),
                    boxes_xz=_boxes_xz(M, sorted(b[1:] for b in gl))))
    return out


def _fit_ellipse(x, y):
    """direct least-squares ellipse fit (Fitzgibbon, Pilu & Fisher 1999; numerically stable form of Halir & Flusser
    1998): always an ellipse. Returns the conic coefficients (a, b, c, d, e, f)."""
    D1 = np.c_[x * x, x * y, y * y]; D2 = np.c_[x, y, np.ones_like(x)]
    S1 = D1.T @ D1; S2 = D1.T @ D2; S3 = D2.T @ D2
    T = -np.linalg.solve(S3, S2.T); Mm = S1 + S2 @ T
    Mm = np.array([Mm[2] / 2, -Mm[1], Mm[0] / 2])
    w, V = np.linalg.eig(Mm); V = np.real(V)
    cond = 4 * V[0] * V[2] - V[1] ** 2
    a1 = V[:, np.argmax(cond)]
    return np.r_[a1, T @ a1]


def _ellipse_params(c):
    a, b, cc, d, e, f = c
    M = np.array([[a, b / 2], [b / 2, cc]]); x0 = np.linalg.solve(2 * M, [-d, -e])
    f0 = f + 0.5 * (d * x0[0] + e * x0[1])
    w, V = np.linalg.eigh(M); ax = np.sqrt(-f0 / w)
    return x0, ax, V


def hotspots(W, M):
    from PIL import Image
    from scipy import ndimage as nd
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(['pdftoppm', '-r', str(DPI), '-png', PDF, os.path.join(td, 'al')], check=True)
        im = np.asarray(Image.open(os.path.join(td, 'al-1.png')).convert('RGB')).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mask = (r - b > 60) & (r > g + 25) & (g > b + 20)
    lab, n = nd.label(mask, structure=np.ones((3, 3)))
    sizes = nd.sum(mask, lab, range(1, n + 1))
    hs_words = [w for w in W if w[0] == 'HS']
    digits = [w for w in W if w[0] in '12345' and len(w[0]) == 1]
    out = []
    for i in [i + 1 for i, s in enumerate(sizes) if s > 2000]:
        ys, xs = np.nonzero(lab == i)
        # the label of this component: an "HS" word whose box lies on it
        lbl = None
        for w in hs_words:
            bx0, by0, bx1, by1 = (np.array(w[1:]) * K)
            if ((xs > bx0 - BOX_PAD) & (xs < bx1 + BOX_PAD) & (ys > by0 - BOX_PAD) & (ys < by1 + BOX_PAD)).any():
                dg = [d for d in digits if abs(d[1] - w[1]) < 0.5 and 0 < w[2] - d[4] < 3.0]
                assert len(dg) == 1, 'HS digit not found'
                lbl = (w, dg[0]); break
        assert lbl is not None, 'hot-spot component without an HS label'
        bx0 = min(lbl[0][1], lbl[1][1]) * K - BOX_PAD; bx1 = max(lbl[0][3], lbl[1][3]) * K + BOX_PAD
        by0 = min(lbl[0][2], lbl[1][2]) * K - BOX_PAD; by1 = max(lbl[0][4], lbl[1][4]) * K + BOX_PAD
        keep = ~((xs > bx0) & (xs < bx1) & (ys > by0) & (ys < by1))
        # filled ellipse: close gaps (smallest disk of 8 / 16 / 24 / 32 px that encloses an interior: the HS 2 ring is
        # broken where the 28L RUN-UP arrow crosses it), fill the interior, cut out the label box, open with a 9 px disk
        # (removes the thin leader line); centre / axes from the second moments of the largest remaining region
        # (a filled ellipse has covariance eigenvalues a^2/4, b^2/4)
        y0_, x0_ = ys.min() - 40, xs.min() - 40                 # margin > the largest closing radius
        sub = np.zeros((ys.max() - y0_ + 41, xs.max() - x0_ + 41), bool); sub[ys - y0_, xs - x0_] = True
        dk = lambda r: np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
        for rad in (8, 16, 24, 32):                             # smallest closing that encloses an interior
            fill = nd.binary_fill_holes(nd.binary_closing(sub, structure=dk(rad)))
            if fill.sum() > 3 * sub.sum(): break
        close_px = rad
        fill[max(0, int(by0) - y0_):max(0, int(by1) - y0_ + 1), max(0, int(bx0) - x0_):max(0, int(bx1) - x0_ + 1)] = False
        fill = nd.binary_opening(fill, structure=dk(9))
        lab2, n2 = nd.label(fill); assert n2 >= 1, 'hot-spot fill failed'
        big = 1 + int(np.argmax(nd.sum(fill, lab2, range(1, n2 + 1)))); yy, xx = np.nonzero(lab2 == big)
        pts = np.c_[xx + x0_, yy + y0_].astype(float); x0 = pts.mean(0)
        w_, V = np.linalg.eigh(np.cov(pts.T)); ax = 2 * np.sqrt(w_)
        n_fill = int(len(pts))
        t = np.linspace(0, 2 * math.pi, 48, endpoint=False)
        P = x0[None] + (np.cos(t)[:, None] * ax[0]) * V[:, 0][None] + (np.sin(t)[:, None] * ax[1]) * V[:, 1][None]
        wz = px_to_world(M, P[:, 0], P[:, 1])
        cen = px_to_world(M, x0[0], x0[1])[0]
        ring = [[round(float(a), 1), round(float(b_), 1)] for a, b_ in wz]
        area = 0.5 * abs(sum(ring[k][0] * ring[k - 1][1] - ring[k - 1][0] * ring[k][1] for k in range(len(ring))))
        out.append(dict(hs='HS %s' % lbl[1][0], centre=[round(float(cen[0]), 1), round(float(cen[1]), 1)], ring=ring,
                        area_m2=round(area), axes_px=[round(float(a), 1) for a in ax],
                        n_px=int(keep.sum()), n_fill=n_fill, close_px=close_px, centre_px=[round(float(x0[0]), 1), round(float(x0[1]), 1)]))
    return sorted(out, key=lambda h: (h['hs'], h['centre']))
