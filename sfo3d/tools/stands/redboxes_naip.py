"""Red equipment-staging boxes (painted hollow squares on the ramps) detected by colour on NAIP 2024 (USDA, public
domain, 0.6 m GSD resampled to the 0.5 m world raster). Replaces the detection on the Google screenshots
(tools/sat/redboxes.py), whose coordinates may no longer be committed (owner, 24 Sep 2026).

Method: red mask  R - (G+B)/2 > 30 and R - G > 25 and R > 140 on the 0.5 m raster, closed (2 px) and filled; candidates whose centre (3x3 px) is
mostly red are rejected (vehicles; the boxes are painted outlines); connected
components whose minimum-area rectangle is 2.8-8 m on both sides and roughly square (ratio < 1.6) are boxes; centre,
mean side and angle (mod 90) are kept. Double boxes (two adjacent squares) split into two when the rectangle is ~2:1.
Search area: the terminal aprons (x -1760..-280, z -420..1060, world frame). Output refs/cache/stands/
redboxes_naip.json ({'frame', 'boxes': [[x, z, size, ang]]}) - read by build_stands.py; an overlay for checking goes to
refs/cache/stands/view/redboxes_naip.png. Measured positions only (no NAIP pixels in the output data).
Usage: python3 tools/stands/redboxes_naip.py
"""
import json, math, os
import numpy as np
import cv2
from scipy import ndimage as ndi
from common import Naip, WORK, GF, Buildings, ROOT

BOX = (-1760.0, -420.0, -280.0, 1060.0)
HOLDS = [h['p'] for h in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'sfo_details.json')))['holds']]
FAR = 200.0     # m from the nearest stand / remote stand / OSM parking position (GSE staging areas lie up to ~200 m away)


def plausible(raw, lab, cx, cy, side_px, ang, X, Z, stands):
    """review round 2 filters (about 20 % of the colour detections were dirt, grass, ground equipment or a point between
    two boxes): (1) the painted outline: >= 45 % of the square's perimeter (at the measured size and angle) is red in the
    raw mask (>= 35 %); (2) grey concrete around it: in a ring 0.6-1.2 box sides from the centre the median Lab chroma is < 14 and
    the lightness > 55 % (dirt / grass are warm or dark); (3) the box interior is not strongly coloured (median chroma < 25:
    liveries, vehicles); (4) within FAR (200 m) of a stand or OSM parking position (the staging boxes belong to stands); (5) not next to
    yellow hold markings or within 15 m of a model hold (the red holding-position surface signs); (6) hollow: the
    inside as light as the surroundings (not two red vehicles side by side)."""
    H, W = raw.shape
    th = math.radians(ang); u = np.array([math.cos(th), math.sin(th)]); v = np.array([-u[1], u[0]]); h = side_px / 2
    per = []
    for t in np.linspace(-1, 1, 21):
        for q in (u * h + v * h * t, -u * h + v * h * t, v * h + u * h * t, -v * h + u * h * t):
            i, j = int(round(cy + q[1])), int(round(cx + q[0]))
            if 0 <= i < H and 0 <= j < W: per.append(raw[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2].any())
    if not per or np.mean(per) < 0.35: return False, 'outline'
    yy, xx = np.mgrid[0:H, 0:W]; d = np.hypot(xx - cx, yy - cy)
    ring = (d > 0.6 * side_px * 1.414 / 1.414 + h) & (d < h + 1.2 * side_px)
    ring &= ~raw
    if ring.sum() < 20: return False, 'ring'
    L = lab[..., 0][ring]; C = np.hypot(lab[..., 1][ring] - 128, lab[..., 2][ring] - 128)
    if np.median(C) >= 14 or np.median(L) < 0.55 * 255: return False, 'ground not grey concrete'
    inner = (d < 0.3 * side_px)
    if inner.sum() >= 4:
        Ci = np.hypot(lab[..., 1][inner] - 128, lab[..., 2][inner] - 128)
        if np.median(Ci) >= 25: return False, 'interior not grey'
        # a painted box is hollow: its inside is the same light concrete as outside (two red cars side by side are not)
        if np.median(lab[..., 0][inner]) < np.median(L) - 45: return False, 'interior dark (vehicles)'
    # the red painted holding-position surface signs sit on yellow ladders / centrelines: reject when > 12 % of the ring
    # is yellow paint (Lab b* > 150)
    if np.mean(lab[..., 2][ring] > 150) > 0.12: return False, 'next to yellow hold marking'
    if min(math.dist((X, Z), n) for n in stands) > FAR: return False, 'far from stands'
    if HOLDS and min(math.dist((X, Z), h_) for h_ in HOLDS) < 15: return False, 'painted holding-position sign'
    return True, ''


def main():
    N = Naip(); x0, z0, x1, z1 = BOX
    im, (c0, r0) = N.crop(x0, z0, x1, z1); I = im.astype(np.int32)
    B_, G_, R = I[..., 0], I[..., 1], I[..., 2]
    red = (R - (G_ + B_) / 2 > 30) & (R - G_ > 25) & (R > 140)
    raw = red.copy()
    red = ndi.binary_closing(red, iterations=2); red = ndi.binary_fill_holes(red)
    lab, nl = ndi.label(red)
    res = N.res; Bd = Buildings(); out = []; rejected = []
    lab_im = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    SD = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    # anchors: contact stand noses, SFO remote stands and the OSM parking positions (remote / cargo aprons have boxes too)
    stands = [s_['nose'] for s_ in SD['stands']] + [[r['x'], r['z']] for r in SD.get('remote', [])] + [[p_['x'], p_['z']] for p_ in SD.get('positions', [])]
    for i, sl in enumerate(ndi.find_objects(lab)):
        m = lab[sl] == i + 1
        ys, xs = np.nonzero(m)
        if len(xs) < 12: continue
        cnt = np.stack([xs + sl[1].start, ys + sl[0].start], 1).astype(np.float32)
        (cx, cy), (w, h), ang = cv2.minAreaRect(cnt)
        w *= res; h *= res
        a, b = max(w, h), min(w, h)
        if b < 2.8 or a > 16: continue
        cands = []
        if a / b < 1.6 and a < 8.0: cands = [(cx, cy)]
        elif 1.6 <= a / b < 2.6 and b < 8.0:   # two squares side by side
            th = math.radians(ang if w >= h else ang + 90); d = a / 4 / res
            cands = [(cx + math.cos(th) * d, cy + math.sin(th) * d), (cx - math.cos(th) * d, cy - math.sin(th) * d)]
            a = a / 2
        for px, py in cands:
            ci, cj = int(round(py)), int(round(px))
            if raw[max(ci - 1, 0):ci + 2, max(cj - 1, 0):cj + 2].mean() > 0.5: continue   # solid red object, not an outline
            X, Z = N.world(px + c0, py + r0)
            if Bd.inside(float(X), float(Z)): continue
            sz = (a + b) / 2
            ok, why = plausible(raw, lab_im, px, py, sz / res, ang, float(X), float(Z), stands)
            rec = [round(float(X), 2), round(float(Z), 2), round(sz, 2), round(ang % 90, 1)]
            (out if ok else rejected).append(rec + ([] if ok else [why]))
    json.dump({'frame': GF.FRAME_ID, 'source': 'NAIP 2024 (USDA, public domain), colour detection + plausibility filter', 'boxes': out, 'rejected': rejected},
              open(os.path.join(WORK, 'redboxes_naip.json'), 'w'))
    # overlay for checking
    ov = im.copy()
    for X, Z, s, ang in out:
        c, r = N.px(X, Z); c -= c0; r -= r0
        cv2.drawMarker(ov, (int(c), int(r)), (0, 255, 0), cv2.MARKER_CROSS, 8, 1)
    os.makedirs(os.path.join(WORK, 'view'), exist_ok=True)
    cv2.imwrite(os.path.join(WORK, 'view', 'redboxes_naip.jpg'), ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
    from collections import Counter
    print(len(out), 'boxes; size median %.1f m' % np.median([b[2] for b in out]), '| rejected', len(rejected), Counter(r[4] for r in rejected))


if __name__ == '__main__':
    main()
