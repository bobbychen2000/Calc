"""2-D signed distance functions used to trim openings into skins (negative inside)."""
import numpy as np


def rrect(px, py, cx, cy, hx, hy, r):
    """Rounded rectangle centred (cx, cy), half sizes (hx, hy), corner radius r."""
    qx = np.abs(px - cx) - (hx - r)
    qy = np.abs(py - cy) - (hy - r)
    ox = np.maximum(qx, 0)
    oy = np.maximum(qy, 0)
    return np.sqrt(ox * ox + oy * oy) + np.minimum(np.maximum(qx, qy), 0) - r


def polygon(px, py, poly):
    """Exact signed distance to a simple polygon (Inigo Quilez)."""
    P = np.stack([np.asarray(px, float), np.asarray(py, float)], -1)
    V = np.asarray(poly, float)
    n = len(V)
    d = np.sum((P - V[0]) ** 2, -1)
    s = np.ones(P.shape[:-1])
    j = n - 1
    for i in range(n):
        e = V[j] - V[i]
        w = P - V[i]
        t = np.clip(np.sum(w * e, -1) / np.dot(e, e), 0, 1)
        b = w - t[..., None] * e
        d = np.minimum(d, np.sum(b * b, -1))
        c1 = P[..., 1] >= V[i][1]
        c2 = P[..., 1] < V[j][1]
        c3 = e[0] * w[..., 1] > e[1] * w[..., 0]
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
        j = i
    return s * np.sqrt(d)


def rounded_polygon(px, py, core, r):
    """Polygon grown by r with round corners (core = inset polygon)."""
    return polygon(px, py, core) - r


def band(sdf, half_width, center=0.0):
    """Region |sdf - center| < half_width as an SDF."""
    return np.abs(sdf - center) - half_width


def rrect_outline(cx, cy, hx, hy, r, n_corner=10):
    """Ordered outline points of a rounded rectangle (counter-clockwise)."""
    pts = []
    corners = [(cx + hx - r, cy + hy - r, 0), (cx - hx + r, cy + hy - r, 90),
               (cx - hx + r, cy - hy + r, 180), (cx + hx - r, cy - hy + r, 270)]
    for (ax, ay, a0) in corners:
        for k in range(n_corner + 1):
            a = np.radians(a0 + 90 * k / n_corner)
            pts.append((ax + r * np.cos(a), ay + r * np.sin(a)))
    return np.array(pts)
