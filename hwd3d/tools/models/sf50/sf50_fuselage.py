"""
SF50 fuselage: lofted OML skin, openings (windshield, cabin windows, clam-shell cabin door, baggage door, nose-gear
bay), glazing, doors, original neutral livery, blank registration panels, cabin lining.
"""
from __future__ import annotations
import numpy as np

from sf50_kernel import (Mesh, grid_surface, trim, band, boundary_loops, solidify, box, planar_cap, cap_ring,
                         sdf2d, squircle, rounded_polygon_pts, poly_sdf, smax, smin, Part, superellipsoid)
import sf50_geom as G

BIG = 10.0
N_AROUND = 192


# ------------------------------------------------------------------------------------------------ skin
def skin_mesh(xs=None, nt=N_AROUND):
    xs = G.station_grid() if xs is None else xs
    ts = np.linspace(0, 1, nt + 1)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = G.section(X, T)
    UV = np.stack([X, T], -1)
    m = grid_surface(P, UV=UV)
    return m


def skin_patch(x0, x1, t0, t1, d=0.012):
    xs = np.linspace(x0, x1, max(4, int(np.ceil((x1 - x0) / d)) + 1))
    nt = max(4, int(np.ceil(abs(t1 - t0) * 2 * np.pi * 0.85 / d)) + 1)
    ts = np.linspace(t0, t1, nt)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    return grid_surface(G.section(X, T), UV=np.stack([X, T], -1))


def side_patch(x0, x1, z0, z1, side, pad=0.04, d=0.012):
    xm = 0.5 * (x0 + x1)
    ts = [G.t_of(xx, zz, side) for xx in (x0 - pad, xm, x1 + pad) for zz in (z0 - pad, z1 + pad)]
    ta, tb = min(ts) - 0.01, max(ts) + 0.01
    if side < 0:
        ta, tb = max(ta, 0.5), min(tb, 1.0)
    else:
        ta, tb = max(ta, 0.0), min(tb, 0.5)
    return skin_patch(x0 - pad, x1 + pad, ta, tb, d)


# ------------------------------------------------------------------------------------------------ opening fields
def window_sdf(x, z, key):
    cx, cz, a, b, p = G.WINDOWS[key]
    return squircle(x, z, cx, cz, a, b, p)


DOOR_PTS = rounded_polygon_pts([G.DOOR["bf"], G.DOOR["ba"], G.DOOR["ta"], G.DOOR["tf"]], [0.07, 0.07, 0.07, 0.16])


def door_sdf(x, z):
    return poly_sdf(x, z, DOOR_PTS)


def bag_sdf(x, z):
    o = G.BAG_DOOR
    return sdf2d.rrect(x, z, o["cx"], o["cz"], o["hx"], o["hz"], o["r"])


def reg_sdf(x, z):
    o = G.REG_PANEL
    return sdf2d.rrect(x, z, 0.5 * (o["x0"] + o["x1"]), o["zc"], 0.5 * (o["x1"] - o["x0"]), 0.5 * o["h"], 0.03)


def windshield_sdf(x, y, z):
    ay = np.abs(y)
    plan = poly_sdf(x, ay, G.WS_PLAN)
    sill = G.z_sill(x) - z
    post = G.WS_POST - ay
    d = smax(smax(plan, sill, 0.05), post, 0.02)
    return np.where(z > 1.55, d, BIG)


def nose_bay_sdf(x, y, z):
    o = G.NOSE_BAY
    d = sdf2d.rrect(x, y, 0.5 * (o["x0"] + o["x1"]), 0.0, 0.5 * (o["x1"] - o["x0"]), o["hw"], o["r"])
    return np.where(z < 1.0, d, BIG)


def side_window_field(x, y, z):
    """Min over all side windows (port: w2, w3 + door handled separately; starboard: w1-w3)."""
    d = np.full(np.shape(x), BIG)
    for side in (-1, 1):
        on = (y * side) > 0.25
        for k in ("w1", "w2", "w3"):
            if side < 0 and k == "w1":
                continue
            d = np.where(on, np.minimum(d, window_sdf(x, z, k)), d)
    return d


def openings_field(m):
    x, y, z = m.V[:, 0], m.V[:, 1], m.V[:, 2]
    d = side_window_field(x, y, z)
    d = np.minimum(d, windshield_sdf(x, y, z))
    port = y < -0.25
    d = np.where(port, np.minimum(d, door_sdf(x, z) + 0.004), d)
    d = np.where(port, np.minimum(d, bag_sdf(x, z) + 0.004), d)
    d = np.minimum(d, nose_bay_sdf(x, y, z) + 0.003)
    return d


# ------------------------------------------------------------------------------------------------ livery
# Original neutral scheme [inf: own design, no operator / manufacturer scheme]: white, a slate-blue swoosh along the
# lower fuselage side rising toward the tail with a cool-grey pin-stripe above it, light-grey belly.
_SW_C = G.pchip([(1.20, 1.000), (2.0, 1.090), (3.0, 1.190), (4.2, 1.255), (5.5, 1.290), (6.8, 1.330), (8.0, 1.380),
                 (9.2, 1.450), (10.3, 1.530)])
_SW_H = G.pchip([(1.20, 0.000), (1.45, 0.030), (2.2, 0.062), (3.5, 0.078), (5.5, 0.074), (7.5, 0.058), (9.0, 0.036),
                 (9.9, 0.016), (10.3, 0.004)])
_BELLY = G.pchip([(0.9, 0.95), (1.6, 0.86), (2.5, 0.80), (3.6, 0.80), (4.6, 0.84), (6.0, 0.95), (7.5, 1.12),
                  (9.0, 1.30), (10.3, 1.48)])


def swoosh_field(m):
    x, z = m.V[:, 0], m.V[:, 2]
    return np.abs(z - _SW_C(x)) - _SW_H(x)


def stripe_field(m):
    x, z = m.V[:, 0], m.V[:, 2]
    zc = _SW_C(x) + _SW_H(x) + 0.028
    w = 0.0065 * np.clip(_SW_H(x) / 0.05, 0.25, 1.0)
    return np.abs(z - zc) - w


def belly_field(m):
    return m.V[:, 2] - _BELLY(m.V[:, 0])


def split(m, field_fn):
    """-> (inside (field < 0), outside)."""
    f = field_fn(m)
    if (f < 0).sum() == 0:
        return None, m
    if (f >= 0).sum() == 0:
        return m, None
    return trim(m, f, "negative"), trim(m, f, "positive")


# ------------------------------------------------------------------------------------------------ helpers
def rim_from_loop(V, N, depth):
    a = V
    b = np.roll(V, -1, 0)
    ai = a - depth * N
    bi = b - depth * np.roll(N, -1, 0)
    n = len(a)
    VV = np.vstack([a, b, bi, ai])
    i = np.arange(n)
    F = np.vstack([np.stack([i, i + n, i + 2 * n], 1), np.stack([i, i + 2 * n, i + 3 * n], 1)])
    return Mesh(VV, F)


def opening_rims(m, depth=0.03):
    """Inward reveal along every boundary loop of an opening-cut skin patch."""
    out = []
    for loop in boundary_loops(m):
        if len(loop) < 8:
            continue
        out.append(rim_from_loop(m.V[loop], m.N[loop], depth))
    return Mesh.merge(out)


def glass_from(patch, fn, inset=0.006, recess=0.005):
    g = trim(patch, fn(patch) + inset, "negative")
    return g.offset(-recess)


def seal_from(patch, fn, inset=0.006, w=0.010):
    return band(patch, fn, -inset - w, -0.0005).offset(-0.0015)


# ------------------------------------------------------------------------------------------------ build
def build(parts):
    sk = skin_mesh()
    # --- cut every opening
    f_open = openings_field(sk)
    body = trim(sk, f_open, "positive")
    reveal = opening_rims(body, 0.028)

    # --- registration panels (blank, separate parts so the runtime can place a decal)
    reg = {}
    for side, tag in ((-1, "L"), (1, "R")):
        fn = lambda m, s=side: np.where(m.V[:, 1] * s > 0.15, reg_sdf(m.V[:, 0], m.V[:, 2]), BIG)
        inside, body = split(body, fn)
        reg[tag] = inside

    # --- livery splits
    belly, body = split(body, belly_field)
    sw, body = split(body, swoosh_field)
    st, body = split(body, stripe_field)
    # the swoosh may overlap the belly region: keep it on top by splitting the belly as well
    if belly is not None:
        bsw, belly = split(belly, swoosh_field)
        sw = Mesh.merge([sw, bsw])

    # --- panel lines: nose radome joint, CAPS cover (top of the nose, ahead of the windshield) [inf: positions]
    def radome_seam(m):
        return np.abs(m.V[:, 0] - 1.245) - 0.0035

    def caps_seam(m):
        x, y = m.V[:, 0], m.V[:, 1]
        d = sdf2d.rrect(x, y, 1.82, 0.0, 0.40, 0.30, 0.14)
        return np.where(m.V[:, 2] > G.z_mw(x) + 0.05, np.abs(d) - 0.0035, BIG)

    def door_seam(m):
        x, y, z = m.V[:, 0], m.V[:, 1], m.V[:, 2]
        d = np.minimum(np.abs(door_sdf(x, z) - 0.001) - 0.005, np.abs(bag_sdf(x, z) - 0.001) - 0.005)
        return np.where(y < -0.25, d, BIG)

    seams = []
    for fn in (radome_seam, caps_seam, door_seam):
        s_in, body = split(body, fn)
        seams.append(s_in)

    fus = Part("fuselage", "Fuselage shell (one-piece carbon composite)", "fuselage", group="Fuselage",
               material_note="Carbon-fibre / honeycomb sandwich, one-piece pressure shell",
               info={"length": f"{G.LENGTH:.3f} m (TCDS / FAA ACD 30.7 ft)",
                     "max width": f"{2 * float(G.half_w(4.4)):.3f} m [inf: AFM Fig 1-2 outline]",
                     "cabin": "137.8 x 61 x 48.8 in (AFM Fig 1-2)"})
    fus.add(body, "paint_white").add(belly, "paint_belly").add(sw, "paint_accent").add(st, "paint_stripe")
    fus.add(Mesh.merge(seams).offset(-0.0008), "seam").add(reveal, "seal")
    parts[fus.id] = fus
    for tag, m in reg.items():
        side = -1 if tag == "L" else 1
        o = G.REG_PANEL
        xc = 0.5 * (o["x0"] + o["x1"])
        yc = side * float(G.side_y(xc, o["zc"]))
        p = Part(f"reg_panel_{tag}", f"Registration panel, {'left' if side < 0 else 'right'} (blank)", "fuselage",
                 group="Fuselage", material_note="Blank: the runtime draws the registration only for aircraft not "
                 "flagged LADD/PIA (D1); never baked into the model",
                 info={"reg_panel": {"centre": [xc, yc, o["zc"]], "normal": [0.0, float(side), 0.0], "up": [0, 0, 1.0],
                                     "length": round(o["x1"] - o["x0"], 4), "height": o["h"],
                                     "text_dir": [1.0 if side < 0 else -1.0, 0.0, 0.0],
                                     "note": "model axes; text reads left-to-right seen from outside (text_dir), "
                                             "panel follows the curved skin (centre is on the OML)"}})
        p.add(m, "reg_panel")
        parts[p.id] = p

    build_glazing(parts)
    build_doors(parts)
    build_lining(parts, sk)
    build_nose_bay(parts)


def build_glazing(parts):
    # windshield: dense patch over the top of the forward fuselage
    t0, t1 = -0.30, 0.30
    xs = np.linspace(2.30, 3.62, 120)
    ts = np.linspace(t0, t1, 160) % 1.0
    ts = np.r_[np.linspace(0.70, 1.0, 81)[:-1], np.linspace(0.0, 0.30, 81)]
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = G.section(X, T)
    patch = grid_surface(P, UV=np.stack([X, T], -1))
    fn = lambda m: windshield_sdf(m.V[:, 0], m.V[:, 1], m.V[:, 2])
    ws = glass_from(patch, fn, 0.006, 0.006)
    ws_seal = seal_from(patch, fn, 0.004, 0.012)
    # dark windshield surround (frame) just outside the glass [inf: SF50 photos show black frames]
    frame = band(patch, fn, -0.0005, 0.016).offset(0.0006)
    w = Part("windshield", "Windshield: two wrap-around heated panes with centre post", "glazing", group="Glazing",
             qty=2, material_note="Heated laminated windshield, TKS spray bar ahead of it (AOPA)",
             info={"outline": "AFM Fig 1-1 (digitised) [inf]"})
    w.add(ws, "glass_windshield").add(ws_seal, "seal").add(frame, "trim_black")
    parts[w.id] = w

    glass, seals = [], []
    for side in (-1, 1):
        for k in ("w1", "w2", "w3"):
            if side < 0 and k == "w1":
                continue        # in the cabin door (door part)
            cx, cz, a, b, p = G.WINDOWS[k]
            patch = side_patch(cx - a, cx + a, cz - b, cz + b, side, pad=0.03, d=0.010)
            fn = lambda m, k=k: window_sdf(m.V[:, 0], m.V[:, 2], k)
            glass.append(glass_from(patch, fn, 0.004, 0.006))
            seals.append(seal_from(patch, fn, 0.002, 0.010))
    g = Part("cabin_windows", "Cabin windows (port 2 + door window, starboard 3 incl. egress window)", "glazing",
             group="Glazing", qty=5, material_note="Stretched acrylic",
             info={"positions": "AFM Fig 1-1 / 1-2 [inf]", "starboard w1": "emergency egress window (AFM)"})
    g.add(Mesh.merge(glass), "glass_cabin").add(Mesh.merge(seals), "seal")
    parts[g.id] = g


def build_doors(parts):
    side = -1
    xs = [p[0] for p in (G.DOOR["bf"], G.DOOR["ba"], G.DOOR["ta"], G.DOOR["tf"])]
    patch = side_patch(min(xs), max(xs), 0.975, 2.27, side, pad=0.03, d=0.014)
    x, z = patch.V[:, 0], patch.V[:, 2]
    panel = trim(patch, door_sdf(x, z) + 0.004, "negative")
    up, lo = None, None
    fz = lambda m: m.V[:, 2] - G.DOOR_SPLIT_Z
    up = trim(panel, fz(panel) - 0.003, "positive")
    lo = trim(panel, fz(panel) + 0.003, "negative")
    wfn = lambda m: window_sdf(m.V[:, 0], m.V[:, 2], "w1")
    up = trim(up, wfn(up), "positive")
    # upper half (window, hinged at the top, opens up) / lower half (steps inside, hinged at the bottom, opens down)
    for pid, m, hz, ang, nm in (("door_upper", up, 2.255, -np.radians(100.0), "Cabin door, upper half (window)"),
                                ("door_lower", lo, 0.995, np.radians(100.0), "Cabin door, lower half (steps)")):
        o_out, o_in = solidify(m, 0.035, separate=True)
        xh = 0.5 * (G.DOOR["tf"][0] + G.DOOR["ta"][0]) if hz > 2 else 0.5 * (G.DOOR["bf"][0] + G.DOOR["ba"][0])
        yh = side * float(G.side_y(xh, hz))
        p = Part(pid, nm, "doors", pivot=dict(origin=[xh, yh, hz], axis=[1.0, 0, 0], kind="door", open=float(ang)),
                 group="Doors", material_note="Clam-shell door: 'pull the bottom half of the door up and the top half "
                 "down' (AOPA); opening 24.6 x 49.4 in (AFM Fig 1-2)",
                 info={"split": f"z {G.DOOR_SPLIT_Z} m [inf]"})
        # livery on the door skin (same fields as the fuselage)
        belly, rest = split(o_out, belly_field)
        sw, rest = split(rest, swoosh_field)
        st, rest = split(rest, stripe_field)
        p.add(rest, "paint_white").add(belly, "paint_belly").add(sw, "paint_accent").add(st, "paint_stripe")
        p.add(o_in, "lining")
        if pid == "door_upper":
            cx, cz, a, b, pp = G.WINDOWS["w1"]
            wp = side_patch(cx - a, cx + a, cz - b, cz + b, side, pad=0.03, d=0.010)
            p.add(glass_from(wp, wfn, 0.004, 0.006), "glass_cabin").add(seal_from(wp, wfn, 0.002, 0.010), "seal")
            # door handle (flush) [inf]
            p.add(box([4.05, side * float(G.side_y(4.05, 1.70)) - side * 0.004, 1.70], (0.16, 0.012, 0.035)), "metal")
        parts[pid] = p
    # baggage door (port, aft): hinged at the top, opens up [inf: hinge]
    o = G.BAG_DOOR
    bp = side_patch(o["cx"] - o["hx"], o["cx"] + o["hx"], o["cz"] - o["hz"], o["cz"] + o["hz"], side, 0.03, 0.012)
    bd = trim(bp, bag_sdf(bp.V[:, 0], bp.V[:, 2]) + 0.004, "negative")
    o_out, o_in = solidify(bd, 0.025, separate=True)
    zh = o["cz"] + o["hz"] - 0.01
    p = Part("door_baggage", "Baggage door (aft, left)", "doors",
             pivot=dict(origin=[o["cx"], side * float(G.side_y(o["cx"], zh)), zh], axis=[1.0, 0, 0], kind="door",
                        open=float(-np.radians(95.0))),
             group="Doors", material_note="External baggage compartment door, opening 23.0-24.9 x 17.6-19.3 in (AFM Fig 1-2)")
    sw, rest = split(o_out, swoosh_field)
    st, rest = split(rest, stripe_field)
    p.add(rest, "paint_white").add(sw, "paint_accent").add(st, "paint_stripe").add(o_in, "lining")
    parts[p.id] = p


def build_lining(parts, sk):
    """Cabin lining (light), floor (carpet) and bulkheads: what one sees through the glazing."""
    m = sk.copy()
    keep = lambda mm: np.minimum(np.minimum(mm.V[:, 0] - 2.40, 5.86 - mm.V[:, 0]), mm.V[:, 2] - (G.FLOOR_Z + 0.02))
    m = trim(m, keep(m), "positive")
    m = trim(m, openings_field(m) - 0.01, "positive")
    lin = m.offset(-0.045).flipped()
    # floor
    xs = np.linspace(2.45, 5.86, 40)
    hw = np.array([float(G.side_y(x, G.FLOOR_Z + 0.02)) for x in xs]) - 0.05
    V, F = [], []
    for i, (x, h) in enumerate(zip(xs, hw)):
        V += [[x, -h, G.FLOOR_Z], [x, h, G.FLOOR_Z]]
    for i in range(len(xs) - 1):
        a = 2 * i
        F += [[a, a + 1, a + 3], [a, a + 3, a + 2]]
    floor = Mesh(np.array(V), np.array(F))
    if floor.face_normals()[:, 2].mean() < 0:
        floor = floor.flipped()
    # aft bulkhead (cabin / baggage) and forward bulkhead behind the panel
    secs = []
    for xb, nx in ((5.86, -1.0), (2.40, 1.0)):
        t = np.linspace(0, 1, 97)[:-1]
        ring = G.section(np.full_like(t, xb), t)
        ring[:, 1] *= 0.94
        ring[:, 2] = G.z_mw(xb) + (ring[:, 2] - G.z_mw(xb)) * 0.94
        secs.append(planar_cap(ring, (nx, 0, 0)))
    p = Part("cabin_lining", "Cabin lining, floor & bulkheads", "interior", group="Interior",
             material_note="Seen through the glazing")
    p.add(lin, "lining").add(floor, "carpet").add(Mesh.merge(secs), "lining")
    parts[p.id] = p


def build_nose_bay(parts):
    """Nose-gear bay liner (open box in the keel) and the two bay doors (open with the gear down)."""
    o = G.NOSE_BAY
    x0, x1, hw = o["x0"], o["x1"], o["hw"]
    top = 1.06
    xs = np.linspace(x0, x1, 18)
    zk = G.z_bot(xs)
    walls = []
    for s in (-1, 1):
        V = np.vstack([np.stack([xs, np.full_like(xs, s * (hw - 0.004)), zk + 0.02], 1),
                       np.stack([xs, np.full_like(xs, s * (hw - 0.004)), np.full_like(xs, top)], 1)])
        n = len(xs)
        F = [[i, i + 1, n + i + 1] for i in range(n - 1)] + [[i, n + i + 1, n + i] for i in range(n - 1)]
        m = Mesh(V, np.array(F))
        if np.sign(m.face_normals()[:, 1].mean()) != -s:
            m = m.flipped()
        walls.append(m)
    walls.append(box([0.5 * (x0 + x1), 0, top], (x1 - x0, 2 * hw, 0.01)))
    for xe in (x0, x1):
        walls.append(box([xe, 0, 0.5 * (G.z_bot(xe) + top)], (0.01, 2 * hw, top - G.z_bot(xe))))
    bay = Part("nose_bay", "Nose-gear bay", "gear", group="Landing gear", material_note="Bay liner")
    bay.add(Mesh.merge(walls), "gear_bay")
    parts[bay.id] = bay
    # doors: keel skin strips either side of the centre line, hinged at the bay edges [inf: AFM Fig 1-1 shows two
    # doors hanging open below the nose with the gear down]
    for side, tag in ((-1, "L"), (1, "R")):
        t_a = G.t_of(0.5 * (x0 + x1), 0.0, side)
        patch = skin_patch(x0 - 0.02, x1 + 0.02, 0.5 - 0.06, 0.5 + 0.06, 0.010)
        fn = lambda m, s=side: np.where(m.V[:, 1] * s > 0.0015, nose_bay_sdf(m.V[:, 0], m.V[:, 1], m.V[:, 2]), BIG)
        dm = trim(patch, fn(patch) + 0.004, "negative")
        if dm.nf == 0:
            continue
        o_out, o_in = solidify(dm, 0.012, separate=True)
        xh = 0.5 * (x0 + x1)
        zh = float(G.z_bot(xh)) + 0.012
        bel, rest = split(o_out, belly_field)
        door = Part(f"nose_door_{tag}", f"Nose-gear door, {'left' if side < 0 else 'right'}", "gear",
                    pivot=dict(origin=[xh, side * hw, zh], axis=[1.0, 0, 0], kind="gear_door",
                               open=float(side * 85.0), seq="down"),
                    group="Landing gear", material_note="Open whenever the gear is down (AFM Fig 1-1) [inf: angle]")
        door.add(rest, "paint_white").add(bel, "paint_belly").add(o_in, "gear_bay")
        parts[door.id] = door
