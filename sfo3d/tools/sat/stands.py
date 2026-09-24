"""Stand design helper: silhouettes of parked aircraft (per class) drawn over grid-aligned satellite views."""
import math, json, sys
import numpy as np, cv2
from common import *
from stview import st_view, annotate, st_px, w2st, st2w, HDGV
# class envelopes: (length, span, representative planform params)  -- ICAO aerodrome reference code letters
CLS = {
    'B': (31.7, 26.0, 3.0, 0.40, 4.6, 1.2, 27, 9.0),      # CRJ900 / E175
    'C': (39.5, 35.9, 3.9, 0.37, 6.3, 1.5, 27, 12.5),     # A320/737-800 (A321/737-9 up to 44.5 m)
    'CL': (44.5, 35.9, 3.9, 0.39, 6.3, 1.5, 27, 12.5),    # A321neo / 737-9 / 757-200 (38 m)
    'D': (54.9, 47.6, 5.0, 0.36, 8.6, 2.0, 31, 18.6),     # 767-300
    'E': (63.7, 60.3, 5.6, 0.35, 10.0, 2.3, 32, 19.4),    # A330-300 / 787-9 / 777-200
    'EL': (73.9, 64.8, 6.2, 0.36, 11.0, 2.4, 33, 21.5),   # 777-300ER / A350-1000
    'F': (76.3, 68.4, 6.5, 0.33, 13.0, 3.0, 37, 22.2),    # 747-8
}
CLEAR = {'B': 3.0, 'C': 4.5, 'CL': 4.5, 'D': 7.5, 'E': 7.5, 'EL': 7.5, 'F': 7.5}  # ICAO Annex 14 stand clearances
def hdg_to_st(h):
    a = math.radians(HDGV - h)  # angle in (s,t) plane counter-clockwise from +s
    return (math.cos(a), math.sin(a))
def st_to_hdg(ds, dt):
    return (HDGV - math.degrees(math.atan2(dt, ds))) % 360
def planform_st(nose, hdg, cls):
    """polygon rings (fuselage, wings, tail) in (s,t) for an aircraft with its nose at `nose`, heading `hdg`"""
    L, B, F, xle, cr, ct, sw, bh = CLS[cls]
    f = hdg_to_st(hdg); r = (f[1], -f[0])  # right-hand side (clockwise from forward in s,t with t 'up')
    def P(x, y):  # x: right of centreline, y: aft distance from nose
        return (nose[0] - f[0] * y + r[0] * x, nose[1] - f[1] * y + r[1] * x)
    tan = math.tan(math.radians(sw)); yl = xle * L
    polys = [[P(-F / 2, F), P(0, 0), P(F / 2, F), P(F / 2, L * 0.86), P(0, L), P(-F / 2, L * 0.86)]]
    for sgn in (-1, 1):
        polys.append([P(0, yl), P(sgn * B / 2, yl + tan * B / 2), P(sgn * B / 2, yl + tan * B / 2 + ct), P(0, yl + cr)])
        yh = L * 0.84
        polys.append([P(0, yh), P(sgn * bh / 2, yh + tan * bh / 2 * 1.1), P(sgn * bh / 2, yh + tan * bh / 2 * 1.1 + 1.2), P(0, L * 0.98)])
    return polys
def envelope_st(nose, hdg, cls, clear=True):
    L, B = CLS[cls][:2]; c = CLEAR[cls] if clear else 0
    f = hdg_to_st(hdg); r = (f[1], -f[0])
    def P(x, y): return (nose[0] - f[0] * y + r[0] * x, nose[1] - f[1] * y + r[1] * x)
    return [P(-B / 2 - c, -c), P(B / 2 + c, -c), P(B / 2 + c, L + c), P(-B / 2 - c, L + c)]
def draw_stands(im, s0, t0, s1, t1, res, stands, env=True):
    P = lambda s, t: st_px(s, t, s0, t1, res)
    ov = im.copy()
    for st in stands:
        col = (255, 0, 255) if not st.get('ok') else (0, 255, 0)
        for poly in planform_st(st['nose'], st['hdg'], st['cls']):
            cv2.fillPoly(ov, [np.array([P(*q) for q in poly], np.int32)], col)
    im = cv2.addWeighted(ov, 0.35, im, 0.65, 0)
    for st in stands:
        col = (255, 0, 255) if not st.get('ok') else (0, 255, 0)
        for poly in planform_st(st['nose'], st['hdg'], st['cls']):
            cv2.polylines(im, [np.array([P(*q) for q in poly], np.int32)], True, col, 1, cv2.LINE_AA)
        if env:
            cv2.polylines(im, [np.array([P(*q) for q in envelope_st(st['nose'], st['hdg'], st['cls'])], np.int32)], True, (0, 200, 255), 1, cv2.LINE_AA)
        q = P(*st['nose']); cv2.circle(im, q, 4, (0, 0, 255), -1)
        cv2.putText(im, st['name'], (q[0] + 6, q[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(im, st['name'], (q[0] + 6, q[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        for b in st.get('bridges', []):
            q = P(*b); cv2.drawMarker(im, q, (0, 128, 255), cv2.MARKER_DIAMOND, 10, 2)
    return im
def stand_view(name, box, stands, res=0.25, out=None, gates=True, env=True):
    s0, t0, s1, t1 = box
    im = st_view(name, s0, t0, s1, t1, res)
    im = annotate(im, s0, t0, s1, t1, res, gates=gates)
    im = draw_stands(im, s0, t0, s1, t1, res, stands, env)
    cv2.imwrite(out or SP + 'stands.png', im)
