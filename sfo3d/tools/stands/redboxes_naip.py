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
Review round 3: every box is then re-fitted with an oriented hollow-square template (refine(): centre +-1.6 m, angle
+-10 deg, side +-0.8 m; score = mean redness on the square outline minus the mean inside and in a ring outside, on a
0.1 m bilinear resampling of the raster), because the component rectangle is pulled off-centre where a vehicle or a
neighbouring box touches the paint (review: 18 of 247 boxes > 1.5 m from the red-pixel centroid). A re-fit that moves
more than 1.6 m or scores lower than the component rectangle keeps the original. 'boxes' = refined, 'boxes_component' =
before; refine_stats compares both with the red-pixel centroid inside box + 1.5 m (the review's test).
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


TEMPLATE_MIN = 8.0   # template score (redness on the outline band minus inside / outside) below which no painted square is there
LINE_W = 0.3         # m, imaged paint line width (the component rectangle is the outer extent; the template the line centre)


def redness(N, cx, cz, half, res=0.1):
    """world-aligned redness patch (R - (G+B)/2, float) of +-half m around (cx, cz) at `res` m; returns (img, x0, z0)"""
    n = int(round(2 * half / res))
    xs = cx - half + (np.arange(n) + 0.5) * res; zs = cz - half + (np.arange(n) + 0.5) * res
    X, Z = np.meshgrid(xs, zs)
    c, r = N.px(X, Z)
    c0, r0 = int(np.floor(c.min())) - 2, int(np.floor(r.min())) - 2
    win = np.asarray(N.im[r0:int(np.ceil(r.max())) + 3, c0:int(np.ceil(c.max())) + 3]).astype(np.float32)
    red = win[..., 2] - (win[..., 0] + win[..., 1]) / 2
    img = cv2.remap(red, (c - c0).astype(np.float32), (r - r0).astype(np.float32), cv2.INTER_LINEAR)
    return img, xs[0], zs[0]


_T = np.linspace(-1, 1, 12)
_OFFS = np.array([-0.2, 0.0, 0.2, -0.9, 0.9])      # outline band (3), inside, outside


def _scores(img, x0, z0, res, C):
    """template scores of many candidates C = [[cx, cz, ang, side], ...] (vectorised). Blurred hollow-square model:
    mean redness in a 0.4 m band on the outline (offsets -0.2 / 0 / +0.2 m) minus the mean of the rings 0.9 m inside
    and 0.9 m outside (NAIP 0.6 m GSD blurs the painted line to ~0.5 m)."""
    C = np.asarray(C, float); th = np.radians(C[:, 2]); u = np.stack([np.cos(th), np.sin(th)], 1); v = np.stack([-u[:, 1], u[:, 0]], 1)
    h = C[:, 3][:, None] / 2 + _OFFS[None, :]                                   # (n, 5)
    # points: (n, 5 offsets, 4 sides, 20)
    sides = []
    for a_, b_ in ((u, v), (v, u)):
        for s1 in (-1, 1):
            p = (s1 * h[:, :, None, None] * a_[:, None, None, :] + (_T[None, None, :, None] * h[:, :, None, None]) * b_[:, None, None, :])
            sides.append(p)
    P = np.concatenate(sides, axis=2)                                          # (n, 5, 80, 2)
    X = C[:, 0][:, None, None] + P[..., 0]; Z = C[:, 1][:, None, None] + P[..., 1]
    cc = ((X - x0) / res).astype(np.float32).reshape(len(C), -1); rr = ((Z - z0) / res).astype(np.float32).reshape(len(C), -1)
    val = np.concatenate([cv2.remap(img, cc[i:i + 20000], rr[i:i + 20000], cv2.INTER_LINEAR, borderValue=0.0)   # (remap: < 32767 rows)
                          for i in range(0, len(C), 20000)]).reshape(X.shape).mean(axis=2)                          # (n, 5)
    return val[:, :3].mean(1) - 0.5 * (val[:, 3] + val[:, 4])


def _score(img, x0, z0, res, cx, cz, ang, side):
    return float(_scores(img, x0, z0, res, [[cx, cz, ang, side]])[0])


def refine(N, box):
    """oriented hollow-square template fit around a detected box [x, z, side, ang] -> (box, score, score at the
    detection's own geometry). The component rectangle's angle is unreliable for a blurred square (minAreaRect of a
    near-circular blob can come out 45 deg off), so the angle is searched over the full 0-90 deg, the side 2.5-7.5 m (line
    centre) and the centre within 1.5 m of the component centre; coarse (3 deg, 0.5 m, 0.5 m) then fine (0.5 deg,
    0.1 m)."""
    x, z, side, ang = box; res = 0.1
    img, x0, z0 = redness(N, x, z, 7.0, res)
    s0 = _score(img, x0, z0, res, x, z, ang, max(3.0, side - LINE_W))
    g = np.stack(np.meshgrid(np.arange(-1.5, 1.51, 0.5), np.arange(-1.5, 1.51, 0.5), np.arange(0, 90, 3.0), np.arange(2.5, 7.51, 0.5), indexing='ij'), -1).reshape(-1, 4)
    g[:, 0] += x; g[:, 1] += z
    sc = _scores(img, x0, z0, res, g); k = int(np.argmax(sc)); bx, bz, ba, bs = g[k]
    f = np.stack(np.meshgrid(np.arange(-0.3, 0.31, 0.1), np.arange(-0.3, 0.31, 0.1), np.arange(-2, 2.01, 0.5), np.arange(-0.3, 0.31, 0.1), indexing='ij'), -1).reshape(-1, 4)
    f += np.array([bx, bz, ba, bs])
    sf = _scores(img, x0, z0, res, f); k2 = int(np.argmax(sf)); bx, bz, ba, bs = f[k2]
    return [round(float(bx), 2), round(float(bz), 2), round(float(bs), 2), round(float(ba) % 90, 1)], float(sf[k2]), s0


def centroid_offset(N, box, m=1.5):
    """the review's test: red-pixel (Lab a* > 145) centroid inside the box + m, distance to the box centre (m)"""
    x, z, side, ang = box; half = side / 2 + m
    img, (c0, r0) = N.crop(x - half - 1, z - half - 1, x + half + 1, z + half + 1)
    a = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 1].astype(float)
    rr, cc = np.nonzero(a > 145)
    if len(rr) < 5: return None
    X, Z = N.world(cc + c0, rr + r0)
    th = math.radians(ang); u = (math.cos(th), math.sin(th)); v = (-u[1], u[0])
    du = (X - x) * u[0] + (Z - z) * u[1]; dv = (X - x) * v[0] + (Z - z) * v[1]
    k = (np.abs(du) <= half) & (np.abs(dv) <= half)
    if k.sum() < 5: return None
    return float(math.hypot(X[k].mean() - x, Z[k].mean() - z))


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
    comp = [list(b) for b in out]; ref = []; moved = 0; keep_comp = []
    for b in comp:
        nb, sn, so = refine(N, b)
        if sn < TEMPLATE_MIN:
            rejected.append(b + ['template: no painted hollow square (best score %.1f)' % sn]); continue
        ref.append(nb); keep_comp.append(b); moved += math.dist(nb[:2], b[:2]) > 0.05
    comp = keep_comp
    # two detections of one double box can converge on the same square: keep the better fit
    dup = set()
    for i in range(len(ref)):
        for j in range(i + 1, len(ref)):
            if j not in dup and i not in dup and math.dist(ref[i][:2], ref[j][:2]) < 0.5 * min(ref[i][2], ref[j][2]): dup.add(j)
    for j in sorted(dup, reverse=True):
        rejected.append(comp[j] + ['duplicate of another box after the template fit']); del ref[j]; del comp[j]
    def stats(bs):
        v = [o for o in (centroid_offset(N, b) for b in bs) if o is not None]
        return {'n': len(v), 'median': round(float(np.median(v)), 2), 'p90': round(float(np.percentile(v, 90)), 2), 'gt1.5': int(sum(o > 1.5 for o in v))}
    rs = {'component': stats(comp), 'refined': stats(ref), 'refitted': moved}
    print('red-pixel centroid vs box centre (box + 1.5 m):', rs)
    out = ref
    json.dump({'frame': GF.FRAME_ID, 'source': 'NAIP 2024 (USDA, public domain), colour detection + plausibility filter + oriented-square template re-fit',
               'boxes': out, 'boxes_component': comp, 'refine_stats': rs, 'rejected': rejected},
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
