"""Two-link folding strut (over-centre drag/side brace) kinematics, shared by
the CAD verification and the viewer (the viewer re-implements solve_knee in JS)."""
import numpy as np
from cad.mesh import rotation_about


def solve_knee(A, B, L1, L2, axis, bend_ref):
    """Knee K of a two-link chain A-K-B in the plane normal to `axis`.
    bend_ref: a direction in that plane; the solution on its side is chosen."""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    d = B - A
    d = d - axis * np.dot(d, axis)
    D = np.linalg.norm(d)
    D = min(D, L1 + L2 - 1e-9)
    u = d / max(D, 1e-12)
    a = (L1 ** 2 - L2 ** 2 + D ** 2) / (2 * D)
    h = np.sqrt(max(L1 ** 2 - a ** 2, 0.0))
    perp = np.cross(axis, u)
    if np.dot(perp, bend_ref) < 0:
        perp = -perp
    return A + a * u + h * perp


def pose(A, B0, K0, gear_origin, gear_axis, gear_angle, L1, L2, axis, bend_ref):
    M = rotation_about(gear_axis, gear_angle, gear_origin)
    B = M[:3, :3] @ B0 + M[:3, 3]
    return B, solve_knee(A, B, L1, L2, axis, bend_ref)
