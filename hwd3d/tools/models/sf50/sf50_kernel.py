"""
Imports of the pc12 "loftkit" kernel (read-only use of /pc12; run python with -B so nothing is written there) plus
small SF50-specific helpers: airfoils, squircle / polygon SDFs, materials.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PC12 = Path(__file__).resolve().parents[4] / "pc12"
if str(PC12) not in sys.path:
    sys.path.insert(0, str(PC12))

import numpy as np                                                                    # noqa: E402
from cad.mesh import (Mesh, grid_surface, grid_normals, trim, band, boundary_loops, solidify, revolve,  # noqa: E402,F401
                      disk, sweep_tube, sweep_profile, cylinder, superellipsoid, box, planar_cap, cap_ring,
                      rotation_about, rotation_matrix, frame_matrix, loft)
from cad import sdf2d                                                                # noqa: E402,F401
from cad.glb import GLBBuilder, to_gl                                                # noqa: E402,F401
from model.lifting import Section, skin, strip, curve_patch, closed_body, bezier, cos_pts   # noqa: E402,F401
from model.airfoil import Airfoil, naca4_thickness, naca00                           # noqa: E402,F401
from model.parts import Part                                                         # noqa: E402,F401


# ------------------------------------------------------------------------------------------------ airfoils
def naca230_camber(x, m=0.2025, k1=15.957):
    """NACA 230 mean line (Abbott & von Doenhoff, eq. 6.6): design CL 0.3, max camber at 15 % chord."""
    x = np.clip(np.asarray(x, float), 0, 1)
    return np.where(x < m, k1 / 6.0 * (x ** 3 - 3 * m * x ** 2 + m * m * (3 - m) * x), k1 * m ** 3 / 6.0 * (1 - x))


def naca230xx(t, name=None):
    return Airfoil(name or f"NACA 230{int(round(t * 100)):02d}",
                   lambda x: naca4_thickness(np.clip(x, 0, 1), t, closed_te=True), naca230_camber)


# ------------------------------------------------------------------------------------------------ 2-D SDFs
def squircle(px, py, cx, cy, a, b, p):
    """Approximate signed distance (metres) to a super-ellipse |dx/a|^p + |dy/b|^p = 1."""
    u = np.abs(np.asarray(px, float) - cx) / a
    v = np.abs(np.asarray(py, float) - cy) / b
    r = (u ** p + v ** p) ** (1.0 / p)
    return (r - 1.0) * min(a, b)


def rounded_polygon_pts(corners, radii, n=10):
    """Closed outline through `corners` with circular fillets of the given radii (CCW or CW)."""
    C = np.asarray(corners, float)
    m = len(C)
    out = []
    for i in range(m):
        p0, p1, p2 = C[i - 1], C[i], C[(i + 1) % m]
        r = radii[i] if np.ndim(radii) else radii
        a = (p0 - p1) / np.linalg.norm(p0 - p1)
        b = (p2 - p1) / np.linalg.norm(p2 - p1)
        ang = np.arccos(np.clip(np.dot(a, b), -1, 1))
        d = r / np.tan(ang / 2)
        t0 = p1 + a * d
        t1 = p1 + b * d
        bis = (a + b) / np.linalg.norm(a + b)
        c = p1 + bis * (r / np.sin(ang / 2))
        a0 = np.arctan2(*(t0 - c)[::-1])
        a1 = np.arctan2(*(t1 - c)[::-1])
        da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
        for k in range(n + 1):
            th = a0 + da * k / n
            out.append(c + r * np.array([np.cos(th), np.sin(th)]))
    return np.array(out)


def poly_sdf(px, py, pts):
    return sdf2d.polygon(px, py, pts)


def smax(a, b, k=0.02):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.maximum(a, b) + h * h * k * 0.25


def smin(a, b, k=0.02):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


# ------------------------------------------------------------------------------------------------ materials
# name -> (rgba, metallic, roughness).  Names kept compatible with pc12/model/assemble.py where they mean the same thing;
# glass names contain "glass" (js/aircraft/glb.js GLASS_RE), tyres start with "tire", lights with "light_" / "lens".
def _lin(c):
    """sRGB design value -> linear (glTF baseColorFactor is linear)."""
    c = np.asarray(c, float)
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).round(4))


MATERIALS = {
    # paint (original neutral scheme) - design colours in sRGB, stored linear
    "paint_white":   (_lin((0.955, 0.958, 0.958)), 0.0, 0.28),
    "paint_belly":   (_lin((0.720, 0.735, 0.750)), 0.0, 0.34),
    "paint_accent":  (_lin((0.170, 0.280, 0.420)), 0.15, 0.30),     # slate blue
    "paint_stripe":  (_lin((0.600, 0.620, 0.645)), 0.35, 0.32),     # cool grey pin-stripe
    "reg_panel":     (_lin((0.955, 0.958, 0.958)), 0.0, 0.28),      # blank registration area (runtime decal target)
    "trim_black":    ((0.012, 0.013, 0.015), 0.0, 0.18),
    "glass_windshield": ((0.018, 0.024, 0.032, 0.72), 0.0, 0.02),
    "glass_cabin":   ((0.016, 0.020, 0.027, 0.80), 0.0, 0.03),
    "seal":          ((0.020, 0.020, 0.024), 0.0, 0.70),
    "seam":          (_lin((0.350, 0.360, 0.370)), 0.0, 0.60),
    "deice_boot":    (_lin((0.200, 0.205, 0.210)), 0.0, 0.70),
    "metal":         ((0.640, 0.650, 0.670), 0.85, 0.32),
    "inlet_lip":     ((0.780, 0.790, 0.800), 1.0, 0.18),
    "metal_dark":    ((0.250, 0.260, 0.270), 0.80, 0.45),
    "exhaust":       ((0.330, 0.310, 0.290), 0.80, 0.55),
    "inlet_dark":    ((0.020, 0.021, 0.024), 0.30, 0.65),
    "fan":           ((0.420, 0.430, 0.450), 0.90, 0.30),
    "black":         ((0.015, 0.015, 0.018), 0.0, 0.55),
    "tire":          ((0.020, 0.020, 0.022), 0.0, 0.85),
    "wheel":         ((0.700, 0.710, 0.720), 0.60, 0.35),
    "gear_leg":      ((0.660, 0.670, 0.680), 0.70, 0.30),
    "chrome":        ((0.920, 0.930, 0.940), 1.0, 0.08),
    "gear_bay":      (_lin((0.500, 0.515, 0.525)), 0.20, 0.70),
    "lens":          ((0.850, 0.870, 0.900, 0.45), 0.0, 0.05),
    "light_red":     ((0.900, 0.050, 0.050), 0.0, 0.20),
    "light_green":   ((0.050, 0.800, 0.200), 0.0, 0.20),
    "light_white":   ((0.950, 0.950, 0.950), 0.0, 0.10),
    "lining":        (_lin((0.820, 0.810, 0.790)), 0.0, 0.75),
    "carpet":        (_lin((0.280, 0.280, 0.300)), 0.0, 0.95),
    "leather":       (_lin((0.640, 0.610, 0.560)), 0.0, 0.55),
    "leather_dark":  (_lin((0.220, 0.220, 0.230)), 0.0, 0.55),
    "panel_black":   ((0.015, 0.015, 0.017), 0.20, 0.40),
    "screen":        ((0.006, 0.020, 0.045), 0.0, 0.08),
    "composite":     (_lin((0.250, 0.260, 0.270)), 0.10, 0.55),
}
