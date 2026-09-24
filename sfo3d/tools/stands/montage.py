"""Oriented NAIP 2024 patches of stands for visual verification: each tile is rotated so the stand's lead-in points
UP (nose toward the top), centred on the stand axis; grid ticks every 5 m along (0 = the reference stop point, cyan
cross) and across; optional overlays of measured nose / axis. Tiles embed NAIP pixels -> refs/cache/stands/ only.
Library: tile(N, stop, hdg, ...) and montage(tiles, cols)."""
import math
import cv2
import numpy as np
from common import hdg_vec

AHEAD, BEHIND, HALF = 20.0, 70.0, 32.0     # metres shown ahead of / behind the stop point, half width
RES = 0.2                                   # m per tile pixel


def tile(N, stop, hdg, label='', marks=(), lines=(), ahead=AHEAD, behind=BEHIND, half=HALF, res=RES):
    """marks: [(along, right, colour)] ; lines: [((a0, r0), (a1, r1), colour)] in stand coordinates (m)"""
    L = ahead + behind
    cx = stop[0] + hdg_vec(hdg)[0] * (ahead - behind) / 2; cz = stop[1] + hdg_vec(hdg)[1] * (ahead - behind) / 2
    img, U, V = N.patch(cx, cz, hdg, L, 2 * half, res)
    img = img.copy()
    H, W = img.shape[:2]
    def P(a, r): return (int(round((r + half) / res - 0.5)), int(round((ahead - a) / res - 0.5)))
    for a in range(-int(behind) // 5 * 5, int(ahead) + 1, 5):
        y = P(a, 0)[1]; c = (0, 200, 255) if a == 0 else (90, 90, 90)
        cv2.line(img, (0, y), (8 if a % 10 else 16, y), c, 1); cv2.line(img, (W - (8 if a % 10 else 16), y), (W, y), c, 1)
        if a % 10 == 0: cv2.putText(img, str(a), (18, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (60, 60, 60), 1, cv2.LINE_AA)
    for r in range(-int(half) // 5 * 5, int(half) + 1, 5):
        x = P(0, r)[0]; cv2.line(img, (x, H - (8 if r % 10 else 14)), (x, H), (90, 90, 90), 1)
    # stand axis (dotted)
    x0 = P(0, 0)[0]
    for y in range(0, H, 6): cv2.line(img, (x0, y), (x0, y + 2), (255, 200, 0), 1)
    cv2.drawMarker(img, P(0, 0), (255, 255, 0), cv2.MARKER_CROSS, 14, 1)
    for (a0, r0), (a1, r1), c in lines: cv2.line(img, P(a0, r0), P(a1, r1), c, 1, cv2.LINE_AA)
    for a, r, c in marks: cv2.drawMarker(img, P(a, r), c, cv2.MARKER_TILTED_CROSS, 12, 2)
    cv2.rectangle(img, (0, 0), (W - 1, 16), (255, 255, 255), -1)
    cv2.putText(img, label, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def montage(tiles, cols=4, pad=4):
    if not tiles: return None
    h, w = tiles[0].shape[:2]; rows = (len(tiles) + cols - 1) // cols
    M = np.full((rows * (h + pad) + pad, cols * (w + pad) + pad, 3), 40, np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols); M[pad + r * (h + pad):pad + r * (h + pad) + h, pad + c * (w + pad):pad + c * (w + pad) + w] = t
    return M
