"""Fuselage finder: whiteness profile along a straight pier face (in airport grid coords) -> parked aircraft centrelines."""
import math, sys, json
import numpy as np, cv2
from scipy.signal import find_peaks
from scipy import ndimage as ndi
from common import *
from stview import st_view
from detect import whiteness
def face_profile(name, axis, c, a0, a1, out, band=(7, 22), res=0.25):
    """axis 's': face is the line t=c for s in [a0,a1]; out=+1 means aircraft are at t>c (face looks toward +t).
       axis 't': face is the line s=c for t in [a0,a1]; out=+1 means aircraft at s>c."""
    d0, d1 = band
    if axis == 's':
        tA, tB = (c + out * d0, c + out * d1)
        box = (a0, min(tA, tB), a1, max(tA, tB))
    else:
        sA, sB = (c + out * d0, c + out * d1)
        box = (min(sA, sB), a0, max(sA, sB), a1)
    s0, t0, s1, t1 = box
    im = st_view(name, s0, t0, s1, t1, res)
    W = whiteness(im)
    valid = im.sum(2) > 0
    # profile along the face coordinate
    if axis == 's':
        prof = (W * valid).sum(0) / np.maximum(valid.sum(0), 1); coord = s0 + (np.arange(W.shape[1]) + 0.5) * res
        cover = valid.mean(0)
    else:
        prof = (W * valid).sum(1) / np.maximum(valid.sum(1), 1); coord = t1 - (np.arange(W.shape[0]) + 0.5) * res
        cover = valid.mean(1)
        prof, coord, cover = prof[::-1], coord[::-1], cover[::-1]
    prof = ndi.gaussian_filter1d(prof, 1.0 / res)
    pk, pr = find_peaks(prof, height=0.25, distance=int(20 / res), prominence=0.12)
    return coord, prof, cover, [(float(coord[i]), float(prof[i])) for i in pk]
def nose_along(name, axis, c, pos, out, res=0.25, maxd=40):
    """distance from the face to the first bright pixel run along the centreline (the nose)"""
    if axis == 's':
        box = (pos - 1.5, min(c, c + out * maxd), pos + 1.5, max(c, c + out * maxd))
    else:
        box = (min(c, c + out * maxd), pos - 1.5, max(c, c + out * maxd), pos + 1.5)
    im = st_view(name, *box, res); W = whiteness(im)
    if axis == 's':
        prof = W.mean(1); dist = (box[3] - (np.arange(len(prof)) + 0.5) * res) - c; dist = dist * out
    else:
        prof = W.mean(0); dist = (box[0] + (np.arange(len(prof)) + 0.5) * res) - c; dist = dist * out
    order = np.argsort(dist); prof = ndi.gaussian_filter1d(prof[order], 0.6 / res); dist = dist[order]
    on = np.nonzero(prof > 0.45)[0]
    return float(dist[on[0]]) if len(on) else None
