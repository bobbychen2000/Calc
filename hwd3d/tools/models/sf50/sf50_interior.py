"""
SF50 cabin interior seen through the glazing (simplified): instrument panel with two large displays and touch
controllers (Cirrus: 'Perspective Touch+ by Garmin', 'two Garmin Touchscreen Controllers'), glareshield, two crew
seats, a middle row (2) and an aft bench (3) at the AFM Fig 1-2 stations.  [inf: shapes]
Also the systems details: antennas, AOA vane (AFM 'Nose, Right Side ... AOA Vane'), EVS camera under the nose (AOPA),
windshield TKS spray bar (AOPA / AFM), ice-inspection light, tail cone light housing, static ports.
"""
from __future__ import annotations
import numpy as np

from sf50_kernel import Mesh, superellipsoid, box, cylinder, revolve, disk, planar_cap, sweep_tube, rotation_matrix, Part
import sf50_geom as G
from sf50_wing import lens_bump

IN = G.IN


def seat(x_front, y, z_floor, w=0.50, back_h=0.56, recline=14.0, dark=False):
    """Seat: cushion + back + headrest (superellipsoids), x_front = cushion front edge."""
    cz = z_floor + 0.34
    cush = superellipsoid([x_front + 0.25, y, cz], (0.25, w / 2, 0.07), e=(0.35, 0.35), nu=10, nv=16)
    R = rotation_matrix((0, 1, 0), np.radians(-recline))
    bx = x_front + 0.53
    back = superellipsoid([0, 0, 0], (0.07, w / 2, back_h / 2), e=(0.35, 0.35), nu=10, nv=16, R=R).translated(
        [bx, y, cz + back_h / 2 + 0.02])
    head = superellipsoid([0, 0, 0], (0.05, w * 0.26, 0.08), e=(0.4, 0.4), nu=8, nv=14, R=R).translated(
        [bx + np.sin(np.radians(recline)) * (back_h + 0.06), y, cz + back_h + 0.10])
    base = box([x_front + 0.27, y, z_floor + 0.14], (0.36, w * 0.7, 0.26))
    return Mesh.merge([cush, back, head]), base


def build(parts):
    zf = G.FLOOR_Z
    # ---- panel: curved fascia across the cockpit, glareshield above it
    xs = 2.64
    t = np.linspace(-1, 1, 25)
    xx = xs + 0.10 * t ** 2
    fascia = []
    for z0, z1 in ((1.18, 1.66),):
        y0 = np.array([float(G.side_y(x, z0)) for x in xx]) - 0.06
        y1 = np.array([float(G.side_y(x - 0.03, z1)) for x in xx]) - 0.06
        V = np.vstack([np.stack([xx, y0 * t, np.full_like(t, z0)], 1), np.stack([xx - 0.03, y1 * t, np.full_like(t, z1)], 1)])
        n = len(t)
        F = [[i, i + 1, n + i + 1] for i in range(n - 1)] + [[i, n + i + 1, n + i] for i in range(n - 1)]
        fascia.append(Mesh(V, np.array(F)))
    gs = superellipsoid([2.63, 0, 1.69], (0.15, float(G.side_y(2.63, 1.72)) - 0.06, 0.03), e=(0.3, 0.3), nu=10, nv=24)
    screens = []
    for yc in (-0.25, 0.25):   # two 14-inch class displays [inf: size]
        screens.append(box([xs + 0.10 * (yc / 0.6) ** 2 - 0.018, yc, 1.47], (0.01, 0.31, 0.195)))
    gtc = [box([2.98, yc, 1.10], (0.16, 0.12, 0.02), R=rotation_matrix((0, 1, 0), np.radians(-28))) for yc in (-0.08, 0.08)]
    pedestal = box([2.86, 0, 1.06], (0.40, 0.26, 0.14))
    # side yokes / sticks [inf]
    yokes = [sweep_tube(np.array([[2.78, s * 0.56, 1.22], [2.90, s * 0.56, 1.28], [2.93, s * 0.56, 1.36]]), 0.016, n=10)
             for s in (-1, 1)]
    p = Part("flight_deck", "Flight deck: panel, glareshield, displays, controllers", "interior", group="Interior",
             material_note="Garmin G3000-based Perspective Touch+ (Cirrus) [inf: layout]")
    p.add(Mesh.merge(fascia), "panel_black").add(gs, "panel_black").add(Mesh.merge(screens), "screen")
    p.add(Mesh.merge(gtc), "screen").add(pedestal, "panel_black").add(Mesh.merge(yokes), "black")
    parts[p.id] = p
    # ---- seats at the AFM Fig 1-2 stations
    seats, bases = [], []
    rows = [(119.0 * IN, (-0.31, 0.31), 0.50), (169.0 * IN, (-0.37, 0.37), 0.46), (201.5 * IN, (-0.36, 0.0, 0.36), 0.38)]
    for x0, ys, w in rows:
        for y in ys:
            s_, b_ = seat(x0, y, zf, w=w)
            seats.append(s_)
            bases.append(b_)
    sp = Part("cabin_seats", "Seats: 2 crew + 2 middle + 3 aft bench (AFM Fig 1-2)", "interior", group="Interior",
              material_note="Leather [inf: colour]", qty=7)
    sp.add(Mesh.merge(seats), "leather").add(Mesh.merge(bases), "leather_dark")
    parts[sp.id] = sp


def build_details(parts):
    det, dark, metal = [], [], []
    # blade antennas [inf: positions] - COM1 top, COM2 belly, XPDR belly, GPS puck top
    def blade(x, z_top_of, up=True, h=0.20, L=0.22):
        z0 = float(G.z_top(x)) if up else float(G.z_bot(x))
        sgn = 1 if up else -1
        pts = np.array([[x, 0, z0 - sgn * 0.01], [x + L, 0, z0 - sgn * 0.01], [x + L - 0.02, 0, z0 + sgn * h],
                        [x + L - 0.08, 0, z0 + sgn * h]])
        a = planar_cap(pts + [0, 0.006, 0], (0, 1, 0))
        b = planar_cap(pts - [0, 0.006, 0], (0, -1, 0))
        return Mesh.merge([a, b])
    det.append(blade(5.30, None, True, 0.14, 0.22))
    det.append(blade(3.45, None, False, 0.16, 0.22))
    det.append(blade(6.70, None, False, 0.12, 0.18))
    det.append(superellipsoid([4.70, 0, float(G.z_top(4.70)) + 0.008], (0.07, 0.05, 0.016), e=(0.5, 0.5), nu=8, nv=12))
    # AOA vane on the right side of the nose
    xa, za = 1.95, 1.18
    ya = float(G.side_y(xa, za))
    det.append(cylinder([xa, ya - 0.01, za], [xa, ya + 0.02, za], 0.022, n=14))
    vane = planar_cap(np.array([[xa, ya + 0.02, za - 0.006], [xa + 0.09, ya + 0.02, za - 0.004],
                                [xa + 0.09, ya + 0.02, za + 0.004], [xa, ya + 0.02, za + 0.006]]), (0, 1, 0))
    det.append(Mesh.merge([vane, vane.translated([0, 0.002, 0]).flipped()]))
    # EVS camera under the nose (AOPA: 'infrared camera under the nose')
    xe = 1.16
    dark.append(superellipsoid([xe, 0, float(G.z_bot(xe)) + 0.01], (0.05, 0.035, 0.03), e=(0.6, 0.6), nu=10, nv=14))
    # windshield TKS spray bar ahead of the windshield (AOPA 'a TKS spray bar protects the windshield')
    xs_ = 2.30
    zz = float(G.z_top(xs_)) + 0.012
    metal.append(cylinder([xs_, -0.22, zz], [xs_, 0.22, zz], 0.008, n=8))
    # radome TKS spray nozzle (AFM 'Radome Spray Nozzle') [inf]
    metal.append(superellipsoid([0.98, 0, float(G.z_top(0.98)) + 0.003], (0.015, 0.015, 0.008), e=(0.6, 0.6), nu=6, nv=10))
    # static ports both sides (AFM) [inf: position]
    for s in (-1, 1):
        x0 = 7.6
        metal.append(disk([x0, s * (float(G.side_y(x0, 1.55)) + 0.001), 1.55], (0, s, 0), 0.018, n=14))
    p = Part("details", "Antennas, AOA vane, EVS camera, TKS spray bars, static ports", "details", group="Systems",
             material_note="Positions [inf]; items listed in the AFM walk-around")
    p.add(Mesh.merge(det), "paint_white").add(Mesh.merge(dark), "black").add(Mesh.merge(metal), "metal")
    # ice-inspection light (AFM Kinds of Operation: 1 installed) on the left fuselage ahead of the wing [inf]
    xi, zi = 3.55, 1.30
    yi = -float(G.side_y(xi, zi))
    p.add(lens_bump([xi, yi, zi], (0.3, -1, -0.1), 0.025, 0.012), "lens")
    p.add(lens_bump([xi, yi + 0.003, zi], (0.3, -1, -0.1), 0.018, 0.008), "light_white")
    # tail light (white position light + strobe) at the tail-cone end (AFM 'Tail Lights')
    xt = G.X_TAIL
    zt = 1.59
    p.add(lens_bump([xt - 0.026, 0, zt], (1, 0, 0), 0.030, 0.022), "lens")
    p.add(lens_bump([xt - 0.028, 0, zt], (1, 0, 0), 0.022, 0.016), "light_white")
    p.info["light_anchors"] = {
        "tail": {"p": [xt + 0.01, 0.0, zt], "colour": "white", "src": "AFM walk-around 'Tail Lights'; position lights 3 installed [inf: position]"},
        "strobeTail": {"p": [xt + 0.005, 0.0, zt + 0.03], "colour": "white", "src": "AFM: anti-collision lights 3 installed (2 tips + tail) [inf]"},
        "iceLight": {"p": [xi, yi - 0.01, zi], "colour": "white", "src": "AFM: ice inspection light 1 installed [inf: position]"},
    }
    parts[p.id] = p
