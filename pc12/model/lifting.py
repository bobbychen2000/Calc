"""
Generic lifting-surface lofting (wing, tailplane, fin, winglet, control surfaces).

A surface is described by a function  section_at(s) -> Section  over a span
parameter s.  A Section places an Airfoil in 3-D with its leading-edge point,
chord, chord direction e_c, thickness direction e_t and twist.  Skin patches,
trailing-edge strips, coves, control-surface bodies and end ribs are all
generated from the same sections, so parts fit together exactly.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from cad.mesh import Mesh, grid_surface, rotation_matrix, cap_ring


@dataclass
class Section:
    le: np.ndarray        # leading-edge point (before twist)
    chord: float
    e_c: np.ndarray       # chord direction (LE -> TE)
    e_t: np.ndarray       # thickness direction (lower -> upper)
    twist: float          # rad, positive = leading edge toward +e_t
    airfoil: object
    pivot_frac: float = 0.25

    def point(self, xc, zc):
        xc = np.asarray(xc, float)
        zc = np.asarray(zc, float)
        e_s = np.cross(self.e_c, self.e_t)          # span axis
        R = rotation_matrix(e_s, -self.twist)       # LE up for positive twist
        q = self.le + self.pivot_frac * self.chord * self.e_c
        loc = ((xc - self.pivot_frac) * self.chord)[..., None] * self.e_c + (zc * self.chord)[..., None] * self.e_t
        return q + loc @ R.T

    def upper(self, xc):
        return self.point(xc, self.airfoil.upper(xc))

    def lower(self, xc):
        return self.point(xc, self.airfoil.lower(xc))

    def camber_pt(self, xc):
        return self.point(xc, self.airfoil.camber(xc))


def cos_pts(n, a=0.0, b=1.0):
    t = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    return a + (b - a) * t


def skin(section_at, s_vals, x_lo_end=1.0, x_up_end=1.0, n=64, x_lo_start=0.0, x_up_start=0.0):
    """Wrapped skin from lower x_lo_end -> LE -> upper x_up_end.
    x_lo_end / x_up_end may be callables of the span parameter s (e.g. a constant-chord control surface on a
    tapered wing, whose cove ends move in chord fraction along the span).
    UV = (s, signed chord position: negative on the lower surface)."""
    rows, uvs = [], []
    for s in s_vals:
        xle = x_lo_end(s) if callable(x_lo_end) else x_lo_end
        xue = x_up_end(s) if callable(x_up_end) else x_up_end
        xl = cos_pts(n, x_lo_start, xle)[::-1]
        xu = cos_pts(n, x_up_start, xue)[1:]
        sec = section_at(s)
        pts = np.vstack([sec.lower(xl), sec.upper(xu)])
        rows.append(pts)
        uvs.append(np.stack([np.full(len(pts), s), np.concatenate([-xl, xu])], 1))
    P = np.array(rows)
    m = grid_surface(P, UV=np.array(uvs))
    return orient(m, section_at, s_vals)


def surface_patch(section_at, s_vals, xs, upper=True):
    """One-sided patch (upper or lower surface) between chord stations xs."""
    rows = []
    for s in s_vals:
        sec = section_at(s)
        rows.append(sec.upper(xs) if upper else sec.lower(xs))
    m = grid_surface(np.array(rows))
    return m


def orient(m: Mesh, section_at, s_vals):
    """Make normals point away from the camber surface (outward)."""
    s = s_vals[len(s_vals) // 2]
    sec = section_at(s)
    c = sec.camber_pt(np.array(0.4))
    # vertex nearest the upper surface at 40 % chord
    u = sec.upper(np.array(0.4))
    i = np.argmin(np.linalg.norm(m.V - u, axis=1))
    if np.dot(m.N[i], u - c) < 0:
        return m.flipped()
    return m


def strip(section_at, s_vals, x_lo, x_up, n=3, crease=True):
    """Ruled strip between the lower point at x_lo and the upper point at x_up
    (blunt trailing edge or cut face)."""
    rows = []
    for s in s_vals:
        sec = section_at(s)
        a = sec.lower(np.array(x_lo))
        b = sec.upper(np.array(x_up))
        rows.append(np.linspace(a, b, n))
    m = grid_surface(np.array(rows))
    # outward = along chord direction (aft) for a TE strip
    sec = section_at(s_vals[0])
    if np.dot(m.N.mean(0), sec.e_c) < 0:
        m = m.flipped()
    return m


def curve_patch(section_at, s_vals, curve_fn, n=12, outward_hint=None):
    """Patch swept through a per-section 2-D curve given in chord units.
    curve_fn(sec) -> (n,2) array of (xc, zc)."""
    rows = []
    for s in s_vals:
        sec = section_at(s)
        c = curve_fn(sec)
        rows.append(sec.point(c[:, 0], c[:, 1]))
    m = grid_surface(np.array(rows))
    if outward_hint is not None:
        sec = section_at(s_vals[len(s_vals) // 2])
        if np.dot(m.N.mean(0), outward_hint(sec)) < 0:
            m = m.flipped()
    return m


def bezier(p0, p1, p2, p3=None, n=12):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = map(np.asarray, (p0, p1, p2))
    if p3 is None:
        return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
    p3 = np.asarray(p3)
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def closed_body(section_at, s_vals, loop_fn, cap=True):
    """Loft a closed section loop (control-surface bodies). loop_fn(sec)->(n,2) chord-unit loop."""
    rows = []
    for s in s_vals:
        sec = section_at(s)
        c = loop_fn(sec)
        rows.append(sec.point(c[:, 0], c[:, 1]))
    P = np.array(rows)
    m = grid_surface(P, close_v=True)
    # orientation: normals away from the loop centroid
    cen = P.mean(1)
    rad = (P - cen[:, None, :]).reshape(-1, 3)
    if len(rad) == len(m.V) and np.mean(np.sum(rad * m.N, 1)) < 0:
        m = m.flipped()
    parts = [m]
    if cap:
        span_dir = P[-1].mean(0) - P[0].mean(0)
        parts.append(cap_ring(P[0], -span_dir))
        parts.append(cap_ring(P[-1], span_dir))
    return Mesh.merge(parts)


def end_rib(sec, loop2d):
    """Flat cap for a section region (chord-unit polygon)."""
    pts = sec.point(loop2d[:, 0], loop2d[:, 1])
    e_s = np.cross(sec.e_c, sec.e_t)
    return pts, e_s
