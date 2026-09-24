"""
Original livery (not a manufacturer or operator scheme): white airframe, cool-grey
belly, a navy swoosh that runs from the cowling along the lower fuselage and
sweeps up the tail cone onto the fin, with a thin brass pinstripe above it.

Applied geometrically: every painted skin is trimmed along the livery curves
(side-projection signed fields) so colour boundaries are exact edges rather
than texture pixels.
"""
from __future__ import annotations
import numpy as np
from cad.mesh import Mesh, trim, pchip

_L = [(0.9, 1.43), (1.6, 1.39), (2.6, 1.35), (4.0, 1.30), (6.0, 1.28), (8.0, 1.28), (9.5, 1.33),
      (10.5, 1.50), (11.5, 1.76), (12.5, 2.06), (13.3, 2.40), (14.0, 2.78), (14.9, 3.28)]
_U = [(0.9, 1.49), (1.6, 1.465), (2.6, 1.455), (4.0, 1.455), (6.0, 1.475), (8.0, 1.52), (9.5, 1.66),
      (10.5, 1.95), (11.5, 2.29), (12.5, 2.64), (13.3, 2.99), (14.0, 3.36), (14.9, 3.86)]
_B = [(0.9, 1.30), (2.0, 1.15), (3.0, 1.06), (4.4, 1.00), (8.8, 1.00), (10.0, 1.06), (11.0, 1.20),
      (12.0, 1.42), (13.0, 1.68), (14.4, 2.02)]
L_, U_, B_ = pchip(*zip(*_L)), pchip(*zip(*_U)), pchip(*zip(*_B))
PIN = (0.028, 0.048)

LIVERY_LINES = dict(swoosh_lower=_L, swoosh_upper=_U, belly=_B)


def fields(V, UV=None):
    x, z = V[:, 0], V[:, 2]
    band = np.maximum(L_(x) - z, z - U_(x))
    pin = np.maximum(U_(x) + PIN[0] - z, z - (U_(x) + PIN[1]))
    belly = z - B_(x)
    out = {"paint_accent": band, "paint_stripe": pin, "paint_belly": belly}
    if UV is not None:
        from model import cockpit_glazing as CG
        from model.fuselage_parts import signed_s
        s = signed_s(x, UV[:, 1])
        out["trim_black"] = CG.surround_sdf(x, V[:, 1], z, s)
    return out


def paint_mesh(m: Mesh, order=("paint_stripe", "paint_accent", "paint_belly"), cockpit=False):
    """Split a white mesh into livery regions -> list of (mesh, material)."""
    out = []
    rest = m
    if cockpit:
        order = ("trim_black",) + tuple(order)
    for mat in order:
        if rest.nf == 0:
            break
        f = fields(rest.V, rest.UV if cockpit else None)[mat]
        if not (f < 0).any():
            continue
        inside = trim(rest, f, "negative")
        rest = trim(rest, f, "positive")
        if inside.nf:
            out.append((inside, mat))
    if rest.nf:
        out.append((rest, "paint_white"))
    return out


PAINTED = ["cowl_upper", "cowl_lower", "fus_fwd", "fus_center", "fus_aft", "fin", "rudder",
           "door_airstair", "door_cargo", "exit_hatch", "dorsal_fin", "chin_inlet"]


def apply(parts):
    for pid in PAINTED:
        if pid not in parts:
            continue
        p = parts[pid]
        new = []
        for m, mat in p.meshes:
            if mat == "paint_white" and not getattr(m, "_no_paint", False):
                new += paint_mesh(m, cockpit=(pid == "fus_fwd"))
            else:
                new.append((m, mat))
        p.meshes = new
    # accent-coloured winglets
    for side in ("L", "R"):
        pid = f"winglet_{side}"
        if pid in parts:
            parts[pid].meshes = [(m, "paint_accent" if mat == "paint_white" else mat) for m, mat in parts[pid].meshes]
    return parts
