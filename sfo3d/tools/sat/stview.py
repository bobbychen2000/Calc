"""Airport-grid-aligned rectified views (s -> right along heading 117.8, t -> up along heading 27.8)."""
import math, sys, json
import numpy as np, cv2
from common import *
from rectify import sim_of, U as UP_LIST
# airport grid frame (same as js/geo.js, from tools/geo_frame.py): V = unit (e,n) along hdg 10L->28R, U = V rotated
# -90 deg. Current world frame; the legacy (equirect-v1) grid is available as legacy_w2st / legacy_st2w.
V, UV, HDGV = GF.V, GF.U, GF.HDG_S
def w2st(x, z):
    e, n = x, -z
    return (e * V[0] + n * V[1], e * UV[0] + n * UV[1])
def st2w(s, t):
    e = s * V[0] + t * UV[0]; n = s * V[1] + t * UV[1]
    return (e, -n)
legacy_w2st, legacy_st2w = GF.legacy_world_to_legacy_st, GF.legacy_st_to_legacy_world
def st_view(name, s0, t0, s1, t1, res=0.25, bottom=2200):
    img = cv2.imread([u for u in UP_LIST if name in u][0])
    W, H = int((s1 - s0) / res), int((t1 - t0) / res)
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    S = s0 + (jj + 0.5) * res; T = t1 - (ii + 0.5) * res
    e = S * V[0] + T * UV[0]; n = S * V[1] + T * UV[1]
    P = sim_of(name).fwd(np.stack([e.ravel(), (-n).ravel()], 1)).astype(np.float32)
    mx = P[:, 0].reshape(H, W); my = P[:, 1].reshape(H, W)
    out = cv2.remap(img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    return out
def st_px(s, t, s0, t1, res): return (int(round((s - s0) / res)), int(round((t1 - t) / res)))
def annotate(im, s0, t0, s1, t1, res, grid=10, lab=50, gates=True, marks=()):
    im = im.copy()
    P = lambda s, t: st_px(s, t, s0, t1, res)
    for gs in range(int(math.ceil(s0 / grid)) * grid, int(s1) + 1, grid):
        c = (200, 200, 200) if gs % lab == 0 else (110, 110, 110)
        cv2.line(im, P(gs, t0), P(gs, t1), c, 1)
    for gt in range(int(math.ceil(t0 / grid)) * grid, int(t1) + 1, grid):
        c = (200, 200, 200) if gt % lab == 0 else (110, 110, 110)
        cv2.line(im, P(s0, gt), P(s1, gt), c, 1)
    for gs in range(int(math.ceil(s0 / lab)) * lab, int(s1) + 1, lab):
        for gt in range(int(math.ceil(t0 / lab)) * lab, int(t1) + 1, lab):
            q = P(gs, gt); cv2.putText(im, f's{gs} t{gt}', (q[0] + 2, q[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)
    for kind, col in (('complex', (60, 60, 255)), ('ba', (120, 255, 60))):
        for r in rings_all(kind):
            pts = np.array([P(*w2st(*q)) for q in r], np.int32)
            cv2.polylines(im, [pts], True, col, 1, cv2.LINE_AA)
    if gates:
        for g in D['gates']:
            if g.get('dup'): continue
            col = (0, 255, 255) if g['level'] == 2 and not g['variant'] else (255, 120, 255)
            q = P(*w2st(g['x'], g['z'])); cv2.circle(im, q, 3, col, -1)
            cv2.putText(im, g['name'], (q[0] + 4, q[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)
    for m in marks:
        q = P(m[0], m[1]); cv2.drawMarker(im, q, (255, 0, 255), cv2.MARKER_CROSS, 14, 2)
        if len(m) > 2: cv2.putText(im, str(m[2]), (q[0] + 5, q[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1, cv2.LINE_AA)
    return im
def view(name, s0, t0, s1, t1, res=0.25, out=None, **kw):
    im = st_view(name, s0, t0, s1, t1, res)
    im = annotate(im, s0, t0, s1, t1, res, **kw)
    cv2.imwrite(out or SP + f'st_{name}.png', im)
    return im
if __name__ == '__main__':
    a = sys.argv
    view(a[1], *[float(v) for v in a[2:6]], res=float(a[6]) if len(a) > 6 else 0.25, out=a[7] if len(a) > 7 else None)
