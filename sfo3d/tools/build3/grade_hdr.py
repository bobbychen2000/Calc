#!/usr/bin/env python3
"""Offline grading of live3.html HDR dumps (tools/build3/job_review.mjs HDR=1 -> <name>.hdr16 + <name>.hdr.json).

The dump is the resolved TRAA output before exposure and tone mapping (half float RGBA, scene-referred). This script
applies the same display transform as js/three/engine.js (exposure x gain -> AgX with the log-domain contrast look and
look saturation -> saturation -> vignette -> sRGB) for a set of parameters and prints luminance percentiles
(p1, p50, p99, p99.5, p99.9) and optional previews, so the grade can be chosen against targets (review round 1: p1
about 15-30, p99.5 about 245, sunlit white paint 235-245) without re-rendering on the CPU rasteriser.

  python3 tools/build3/grade_hdr.py out/engine2/rv_real_gate_B26_60_1_14 [...] --gain 1.1 --contrast 1.2 --looksat 1.08 --sat 1.05 [--png out.png]
"""
import argparse, json, sys
import numpy as np

S2020 = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0113], [0.0164, 0.0880, 0.8956]])
R2020 = np.array([[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]])
AIN = np.array([[0.856627153315983, 0.0951212405381588, 0.0482516061458583], [0.137318972929847, 0.761241990602591, 0.101439036467562], [0.11189821299995, 0.0767994186031903, 0.811302368396859]])
AOUT = np.array([[1.1271005818144368, -0.11060664309660323, -0.016493938717834573], [-0.1413297634984383, 1.157823702216272, -0.016493938717834257], [-0.14132976349843826, -0.11060664309660294, 1.2519364065950405]])
MIN, MAX = -12.47393, 4.026069
GREY = (np.log2(0.18) - MIN) / (MAX - MIN)


def poly(x):
    x2 = x * x; x4 = x2 * x2
    return 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232


def agx(c, contrast=1.2, looksat=1.08):
    v = np.maximum(c @ S2020.T @ AIN.T, 1e-10)
    x = np.clip(((np.log2(v) - MIN) / (MAX - MIN) - GREY) * contrast + GREY, 0, 1)
    s = poly(x); l = s @ np.array([0.2126, 0.7152, 0.0722])
    s = np.maximum(l[..., None] + (s - l[..., None]) * looksat, 0)
    return np.clip((np.maximum(s @ AOUT.T, 0) ** 2.2) @ R2020.T, 0, 1)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def load(stem):
    meta = json.load(open(stem + '.hdr.json'))
    raw = np.fromfile(stem + '.hdr16', dtype=np.float16 if meta['type'] == 'Uint16Array' else np.float32).astype(np.float32)
    img = raw.reshape(meta['h'], meta['w'], 4)[..., :3]
    return img, meta


def grade(img, expo, gain, contrast, looksat, sat, vignette=0.18):
    t = agx(img * expo * gain, contrast, looksat)
    l = t @ np.array([0.2126, 0.7152, 0.0722])
    t = np.clip(l[..., None] + (t - l[..., None]) * sat, 0, 1)
    h, w = t.shape[:2]; yy, xx = np.mgrid[0:h, 0:w]; d2 = ((xx + 0.5) / w - 0.5) ** 2 + ((yy + 0.5) / h - 0.5) ** 2
    s = np.clip((d2 * 1.6 - 0.15) / 0.7, 0, 1); t = t * (1 - vignette * s * s * (3 - 2 * s))[..., None]
    return srgb(t) * 255


def stats(o8):
    L = o8 @ np.array([0.2126, 0.7152, 0.0722])
    return {k: round(float(np.percentile(L, q)), 1) for k, q in (('p1', 1), ('p50', 50), ('p99', 99), ('p99.5', 99.5), ('p99.9', 99.9))}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stems', nargs='+'); ap.add_argument('--gain', type=float, default=1.0); ap.add_argument('--contrast', type=float, default=1.2)
    ap.add_argument('--looksat', type=float, default=1.08); ap.add_argument('--sat', type=float, default=1.05); ap.add_argument('--png'); ap.add_argument('--flip', action='store_true')
    a = ap.parse_args()
    outs = []
    for st in a.stems:
        img, m = load(st)
        if a.flip: img = img[::-1]
        o = grade(img, m['expo'], a.gain, a.contrast, a.looksat, a.sat)
        print(st.split('/')[-1], 'expo', round(m['expo'], 3), stats(o))
        outs.append(o)
    if a.png:
        from PIL import Image
        Image.fromarray(np.concatenate(outs, 0).astype(np.uint8)).save(a.png)
