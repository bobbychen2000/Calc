import math
import numpy as np, cv2
from common import *
from detect import TYPES, nose_tail
def draw(bgr, box, res, dets=(), stands=(), gates=True, grid=20, out=None, scale=1.0, minscore=0.0):
    x0, z0, x1, z1 = box
    im = bgr.copy()
    def p(x, z): return (int(round((x - x0) / res)), int(round((z - z0) / res)))
    # grid
    for gx in range(int(math.ceil(x0 / grid)) * grid, int(x1), grid):
        cv2.line(im, p(gx, z0), p(gx, z1), (90, 90, 90) if gx % 100 else (160, 160, 160), 1)
    for gz in range(int(math.ceil(z0 / grid)) * grid, int(z1), grid):
        cv2.line(im, p(x0, gz), p(x1, gz), (90, 90, 90) if gz % 100 else (160, 160, 160), 1)
    for gx in range(int(math.ceil(x0 / 100)) * 100, int(x1), 100):
        for gz in range(int(math.ceil(z0 / 100)) * 100, int(z1), 100):
            cv2.putText(im, f'{gx},{gz}', (p(gx, gz)[0] + 2, p(gx, gz)[1] + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    for kind, col in (('complex', (60, 60, 255)), ('ba', (120, 255, 60))):
        for r in rings_all(kind):
            pts = np.array([p(*q) for q in r], np.int32)
            cv2.polylines(im, [pts], True, col, 1)
    if gates:
        for g in D['gates']:
            if g.get('dup'): continue
            col = (0, 255, 255) if g['level'] == 2 and not g['variant'] else (255, 120, 255)
            cv2.circle(im, p(g['x'], g['z']), 3, col, -1)
            cv2.putText(im, g['name'], (p(g['x'], g['z'])[0] + 4, p(g['x'], g['z'])[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)
    for d in dets:
        if d[0] < minscore: continue
        (nx, nz), (tx, tz) = nose_tail(d)
        cv2.line(im, p(tx, tz), p(nx, nz), (0, 0, 255), 2)
        cv2.circle(im, p(nx, nz), 4, (0, 0, 255), -1)
        L, B = TYPES[d[1]][:2]; a = math.radians(d[2]); hx, hz = math.sin(a), -math.cos(a)
        wx, wz = d[3] + hx * (L / 2 - TYPES[d[1]][3] * L - 3), d[4] + hz * (L / 2 - TYPES[d[1]][3] * L - 3)
        cv2.line(im, p(wx - hz * B / 2, wz + hx * B / 2), p(wx + hz * B / 2, wz - hx * B / 2), (0, 140, 255), 1)
        cv2.putText(im, f'{d[1]} {d[0]:.2f}', (p(d[3], d[4])[0] + 5, p(d[3], d[4])[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    for s in stands:
        (nx, nz), hd = s['nose'], math.radians(s['hdg'])
        hx, hz = math.sin(hd), -math.cos(hd)
        cv2.arrowedLine(im, p(nx - hx * 30, nz - hz * 30), p(nx, nz), (255, 0, 255), 2, tipLength=0.15)
        cv2.putText(im, s['name'], (p(nx, nz)[0] + 5, p(nx, nz)[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    if scale != 1.0: im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    if out: cv2.imwrite(out, im)
    return im
