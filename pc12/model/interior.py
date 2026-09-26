"""
Interior (for the cutaway view) and primary structure (for the X-ray view).

Flight deck: PC-12 PRO style Garmin G3000 PRIME -- three 14-in touchscreen
displays and two touchscreen secondary displays on the pedestal, dual yokes.
Cabin: 6-seat executive layout (4-seat club + 2 forward-facing), flat floor at
fuselage.CABIN_FLOOR_WL (5.16 m x 1.52 m x 1.47 m cabin, floor at least 1.30 m wide),
the entry aisle clear of the airstair door (door panel STA 4.65-5.29), baggage area
behind a net at the cargo door.
Structure: fuselage frames at the Pilatus frame stations (fuselage.FRAMES, numbered
frames interpolated between them) interrupted at the openings, stringers, wing spars
and ribs (representative, not the certified structural drawing).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import (Mesh, superellipsoid, box, cylinder, sweep_tube, rotation_matrix, grid_surface,
                      planar_cap, revolve, trim)
from model.parts import Part
from model import fuselage as F
from model import wing as W

FLOOR_Z = F.CABIN_FLOOR_WL        # 1.259: crown 2.769 - lining 0.040 - cabin height 1.470 (decision D1)
LINING = 0.085


def rbox(center, size, e=0.28, R=None, n=14):
    return superellipsoid(center, np.asarray(size) / 2, (e, e), nu=n, nv=n + 6, R=R)


def roty(a):
    return rotation_matrix((0, 1, 0), np.radians(a))


def seat(x, y, facing=+1, floor=FLOOR_Z, width=0.52, crew=False, back_h=0.74, head_w=0.55):
    """facing=+1 forward-facing (back toward +x), -1 aft-facing."""
    f = facing
    parts_leather, parts_frame = [], []
    cz = floor + 0.40
    parts_leather.append(rbox((x, y, cz), (0.50, width, 0.14), e=0.35))
    back_c = np.array([x + f * 0.24, y, floor + 0.41 + back_h / 2])
    parts_leather.append(rbox(back_c, (0.14, width, back_h), e=0.35, R=roty(-f * 12)))
    parts_leather.append(rbox(back_c + [f * 0.07, 0, back_h / 2 + 0.07], (0.12, width * head_w, 0.15), e=0.45,
                              R=roty(-f * 12)))
    for s in (-1, 1):
        parts_leather.append(rbox((x + f * 0.02, y + s * (width / 2 + 0.03), floor + 0.58), (0.42, 0.07, 0.07), e=0.5))
    parts_frame.append(box((x, y, floor + 0.17), (0.34, width * 0.7, 0.30)))
    if crew:
        # 5-point harness shoulder straps
        for sg in (-1, 1):
            parts_frame.append(box(back_c + [-f * 0.08, sg * 0.10, 0.06], (0.01, 0.045, back_h * 0.7)))
    return Mesh.merge(parts_leather), Mesh.merge(parts_frame)


FD_FLOOR_Z = 1.24
EYE_Y = 0.335


def section_limit(x, z, inset):
    """Half-width available inside the lining at station x, water line z."""
    return max(0.0, float(F.side_y(x, z)) - inset)


def fitted_plate(x0, x1, z, inset=0.06, n=16, thick=0.03, y_min=0.0):
    """Horizontal plate following the fuselage section (floors); y_min > 0 leaves a centre slot |y| < y_min."""
    xs = np.linspace(x0, x1, n)
    hw = np.array([min(section_limit(x, z, inset), section_limit(x, z - thick, inset)) for x in xs])
    if y_min <= 0:
        tops = [np.vstack([np.stack([xs, hw, np.full(n, z)], 1), np.stack([xs[::-1], -hw[::-1], np.full(n, z)], 1)])]
    else:
        tops = [np.vstack([np.stack([xs, s * hw, np.full(n, z)], 1), np.stack([xs[::-1], np.full(n, s * y_min), np.full(n, z)], 1)])
                for s in (1, -1)]
    out = []
    for top in tops:
        out += [planar_cap(top, (0, 0, 1)), planar_cap(top - [0, 0, thick], (0, 0, -1))]
    return Mesh.merge(out)


def tunnel_hump(TU, wall=0.02, top_gap=0.025, n_corner=6):
    """Nose-wheel tunnel hump under the centre pedestal: an OPEN shell (side walls from under the flight-deck floor up
    to the top plate, no bottom face), so the stowed nose wheel and drag brace rise into it (M7; a closed box capped
    the tunnel at WL 1.21)."""
    from cad.sdf2d import rrect_outline
    ol = rrect_outline(0.5 * (TU["x0"] + TU["x1"]), 0.0, 0.5 * (TU["x1"] - TU["x0"]) + wall, TU["hy"] + wall, 0.05,
                       n_corner=n_corner)
    z0, z1 = FD_FLOOR_Z - 0.03, TU["z_top"] + top_gap
    n = len(ol)
    k = np.arange(n)
    V = np.vstack([np.c_[ol, np.full(n, z0)], np.c_[ol, np.full(n, z1)]])
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    walls = Mesh(V, Fc)
    c = np.array([0.5 * (TU["x0"] + TU["x1"]), 0.0, 0.5 * (z0 + z1)])
    if np.mean(np.sum((walls.V[walls.F].mean(1) - c) * walls.face_normals(), 1)) < 0:
        walls = walls.flipped()
    return Mesh.merge([walls, planar_cap(np.c_[ol, np.full(n, z1)], (0, 0, 1))])


def build_flightdeck(parts):
    m_leather, m_frame, m_panel, m_metal = [], [], [], []
    screens = {}
    # flight-deck floor (raised over the nose-wheel well), fitted to the section, with the nose-wheel tunnel hump
    # under the centre pedestal (gear.NOSE_TUNNEL: the retracted nose wheel stows there)
    from model.gear import NOSE_TUNNEL as TU
    x_fd0 = 3.26                                       # forward end of the flight-deck floor
    if TU["x0"] > x_fd0 + 1e-3:
        m_frame.append(fitted_plate(x_fd0, TU["x0"], FD_FLOOR_Z, inset=0.07, n=4))
    m_frame.append(fitted_plate(max(TU["x0"], x_fd0), TU["x1"], FD_FLOOR_Z, inset=0.07, n=16, y_min=TU["hy"] + 0.012))
    m_frame.append(fitted_plate(TU["x1"], 4.34, FD_FLOOR_Z, inset=0.07, n=6))
    m_panel.append(tunnel_hump(TU))
    # instrument panel: a tilted plate whose outline follows the fuselage section
    tilt = np.radians(12)
    Rp = roty(-12)
    pc = np.array([3.47, 0, 1.84])
    n_p = Rp @ np.array([1.0, 0, 0])
    up_p = Rp @ np.array([0, 0, 1.0])
    rows = []
    for v in np.linspace(-0.22, 0.20, 9):
        p = pc + v * up_p
        rows.append((v, section_limit(p[0], p[2], 0.085)))
    outline = [pc + v * up_p + w * np.array([0, 1.0, 0]) for v, w in rows] + \
              [pc + v * up_p - w * np.array([0, 1.0, 0]) for v, w in rows[::-1]]
    outline = np.array(outline)
    front = planar_cap(outline + n_p * 0.02, n_p)
    back = planar_cap(outline - n_p * 0.03, -n_p)
    k = len(outline)
    Vs = np.vstack([outline + n_p * 0.02, outline - n_p * 0.03])
    ii = np.arange(k)
    Fs = np.vstack([np.stack([ii, (ii + 1) % k, (ii + 1) % k + k], 1), np.stack([ii, (ii + 1) % k + k, ii + k], 1)])
    m_panel += [front, back, Mesh(Vs, Fs)]
    # glareshield: shelf under the windshield base, fitted to the section
    gz = 2.075
    m_panel.append(fitted_plate(3.40, 3.63, gz, inset=0.10, n=10, thick=0.035))
    # three 14-in touchscreen PDUs (G3000 PRIME)
    for key, y in (("screen_pfd", -0.368), ("screen_mfd", 0.0), ("screen_pfd", 0.368)):
        c = pc + n_p * 0.028 + np.array([0, y, -0.01])
        bezel = box(c, (0.012, 0.35, 0.225), R=Rp)
        glass = box(c + n_p * 0.007, (0.004, 0.312, 0.192), R=Rp)
        m_metal.append(bezel)
        screens.setdefault(key, []).append(glass)
    # centre pedestal with two 7-in touchscreen SDUs + power lever + cursor control
    # the pedestal stands on the tunnel hump (its bottom at the hump top, not inside the tunnel: M7)
    ped_z0, ped_z1 = TU["z_top"] + 0.025, FD_FLOOR_Z + 0.53
    ped_c = np.array([3.80, 0, 0.5 * (ped_z0 + ped_z1)])
    m_panel.append(rbox(ped_c, (0.62, 0.22, ped_z1 - ped_z0), e=0.2))
    Rt = roty(-35)
    for kk, x in enumerate((3.60, 3.84)):
        c = np.array([x, 0, FD_FLOOR_Z + 0.55 - 0.08 * kk])
        m_metal.append(box(c, (0.19, 0.17, 0.03), R=Rt))
        screens.setdefault("screen_sdu", []).append(box(c + Rt @ np.array([0, 0, 0.017]), (0.145, 0.125, 0.004), R=Rt))
    m_metal.append(cylinder((4.00, 0.0, FD_FLOOR_Z + 0.54), (3.96, 0.0, FD_FLOOR_Z + 0.68), 0.012, n=8))
    m_panel.append(rbox((3.96, 0.0, FD_FLOOR_Z + 0.70), (0.05, 0.09, 0.05), e=0.5))
    m_panel.append(rbox((4.02, 0.07, FD_FLOOR_Z + 0.53), (0.07, 0.05, 0.03), e=0.5))     # cursor control device
    # PC-24-style yokes
    for y in (-EYE_Y, EYE_Y):
        m_metal.append(cylinder((3.47, y, 1.66), (3.66, y, 1.70), 0.022, n=12))
        m_panel.append(rbox((3.68, y, 1.73), (0.05, 0.10, 0.11), e=0.4))
        for sg in (-1, 1):
            m_panel.append(cylinder((3.69, y, 1.72), (3.70, y + sg * 0.13, 1.78), 0.018, n=10))
            m_panel.append(cylinder((3.70, y + sg * 0.13, 1.78), (3.68, y + sg * 0.14, 1.86), 0.02, n=10))
        for sg in (-1, 1):   # rudder pedals
            m_frame.append(box((3.38, y + sg * 0.085, FD_FLOOR_Z + 0.10), (0.03, 0.075, 0.17), R=roty(-25)))
    # crew seats: eye point ~ WL 2.36, headrest clear of the roof curvature
    for y in (-EYE_Y, EYE_Y):
        a, b = seat(4.02, y, +1, floor=FD_FLOOR_Z, width=0.44, crew=True, back_h=0.64, head_w=0.50)
        m_leather.append(a)
        m_frame.append(b)
    p = Part("flight_deck", "Flight deck: Garmin G3000 PRIME, PC-24-style yokes, crew seats", "interior",
             explode=(0, 0, 0.0), group="Interior",
             material_note="3 x 14-in touchscreen PDUs, 2 x 7-in touchscreen SDUs",
             info={"avionics": "Garmin G3000 PRIME (PC-12 PRO)", "displays": "3 x 14 in + 2 x 7 in",
                   "design eye": "STA 3,980 / BL +/-335 / WL 2,360 (est.)"})
    p.add(Mesh.merge(m_leather), "leather_dark").add(Mesh.merge(m_frame), "metal_dark")
    p.add(Mesh.merge(m_panel), "panel_black").add(Mesh.merge(m_metal), "metal_dark")
    for key, lst in screens.items():
        for g in lst:
            p.add(g, key)
    parts[p.id] = p


CABIN_X = (4.40, 9.52)                 # cabin floor (cockpit divider -> aft baggage bay)
SEAT_ROWS = ((5.72, -1), (6.98, +1), (7.98, +1))   # (seat centre STA, facing): club pair, club pair, aft pair
SEAT_Y = 0.40
TABLE_X = 6.35
BAGGAGE_NET_X = 8.60


def ledge_spans():
    """Side-ledge x-spans per side, clear of the door panels (and 0.10 m of margin)."""
    from model.fuselage_parts import openings_table
    out = {}
    for side in (-1, 1):
        spans = [(5.10, 8.25)]
        for r in openings_table():
            if r["side"] != side or r["kind"] not in ("door",) or r.get("panel") is None:
                continue
            a, b = r["panel"]["x0"] - 0.10, r["panel"]["x1"] + 0.10
            new = []
            for x0, x1 in spans:
                if b <= x0 or a >= x1:
                    new.append((x0, x1))
                    continue
                if a > x0:
                    new.append((x0, a))
                if b < x1:
                    new.append((b, x1))
            spans = [sp for sp in new if sp[1] - sp[0] > 0.3]
        out[side] = spans
    return out


def build_cabin(parts):
    leather, frame, carpet, wood, lin = [], [], [], [], []
    # floor panels (flat floor at CABIN_FLOOR_WL)
    carpet.append(fitted_plate(*CABIN_X, FLOOR_Z, inset=0.055, n=28))
    # side ledges / cabinets with wood caps, interrupted at the doors
    for s_, spans in ledge_spans().items():
        for x0, x1 in spans:
            xm, L = 0.5 * (x0 + x1), x1 - x0
            lin.append(rbox((xm, s_ * 0.615, FLOOR_Z + 0.21), (L, 0.08, 0.42), e=0.3))
            wood.append(box((xm, s_ * 0.60, FLOOR_Z + 0.425), (L, 0.12, 0.02)))
    # executive seating: 4-seat club (the forward pair faces aft) + 2 forward-facing
    for x, f in SEAT_ROWS:
        for y in (-SEAT_Y, SEAT_Y):
            a, b = seat(x, y, f)
            leather.append(a)
            frame.append(b)
    # club tables
    for y in (-SEAT_Y, SEAT_Y):
        wood.append(rbox((TABLE_X, y * 1.2, FLOOR_Z + 0.68), (0.46, 0.34, 0.03), e=0.4))
    # aft baggage net frame
    for sg in (-1, 1):
        frame.append(cylinder((BAGGAGE_NET_X, sg * 0.55, FLOOR_Z), (BAGGAGE_NET_X, sg * 0.55, FLOOR_Z + 1.15),
                              0.012, n=8))
    frame.append(cylinder((BAGGAGE_NET_X, -0.55, FLOOR_Z + 1.15), (BAGGAGE_NET_X, 0.55, FLOOR_Z + 1.15), 0.012, n=8))
    p = Part("cabin_interior", "Cabin: executive 6-seat interior", "interior", group="Interior",
             material_note="Leather seats, wood veneer ledges",
             info={"cabin": "5.16 x 1.52 x 1.47 m", "floor": f"WL {FLOOR_Z * 1000:.0f}, "
                   f"{F.cabin_floor_width(6.0):.2f} m wide inside the lining", "seats": "6 executive (up to 9)"})
    p.add(Mesh.merge(leather), "leather").add(Mesh.merge(frame), "metal_dark")
    p.add(Mesh.merge(carpet), "carpet").add(Mesh.merge(wood), "wood").add(Mesh.merge(lin), "lining")
    parts[p.id] = p


# ---------------------------------------------------------------------------
# side-wall / headliner lining (flight deck + cabin)
# ---------------------------------------------------------------------------
LINING_X = (3.05, F.STA["aft_pressure_bulkhead"] - 0.01)   # just aft of the firewall -> aft pressure bulkhead
LINING_Z0 = FD_FLOOR_Z - 0.010      # lower edge: at the (flight-deck / cabin) floor, closing the floor-edge slit
LINING_DOOR_MARGIN = 0.008          # hole round the door-panel seams: clear of the 45 mm door slabs (jambs fill it)
LINING_DX = 0.030


def _lining_proxy(m):
    """The OML points under the lining vertices (same loft parameters x, t: UV): the opening fields are evaluated
    there, so every hole lines up with its skin opening."""
    return Mesh(F.section(m.UV[:, 0], m.UV[:, 1] % 1.0), m.F, N=m.N, UV=m.UV)


def build_lining(parts):
    """Side-wall and headliner lining, F.CABIN_LINING (40 mm: the 1.52 m cabin width) inside the OML from the firewall
    to the aft pressure bulkhead, down to the floors: the skins are single-sided and wound outward, so without it the
    glazing showed the back faces of the paint (blue / white) -- through the windshield, the side and cabin windows and
    the open doors (lookdev round 1).  Holes: the windshield, cockpit side windows and cabin windows (the skin's own
    fields, evaluated on the OML under each lining vertex) with a reveal back to the skin opening, and the door-panel
    seams (+ LINING_DOOR_MARGIN; the door jambs close the gap).  Flight deck (x < STA cockpit_aft) mid grey
    'lining_flightdeck', the cabin 'lining'."""
    from cad.mesh import grid_normals, boundary_loops
    from model import fuselage_parts as FP
    from model import cockpit_glazing as CG
    x0, x1 = LINING_X
    extra = [F.STA["cockpit_aft"]] + [cx + s * FP.WIN_HX for xs in FP.FIXED_WINDOWS.values() for cx in xs
                                      for s in (-1, 1)]
    xs = np.unique(np.r_[np.arange(x0, x1, LINING_DX), x1, [e for e in extra if x0 < e < x1]])
    xs = xs[np.r_[True, np.diff(xs) > 2e-3]]
    ts = np.linspace(0.5, 1.5, FP.N_AROUND, endpoint=False)       # seam at the keel (t unwrapped across the crown)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = F.section(X, T % 1.0)
    N = grid_normals(P, close_v=True)
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    m = grid_surface(P - F.CABIN_LINING * N, close_v=True, UV=np.stack([X, T], -1))
    side_of = lambda q: np.sign(q.V[:, 1])                                           # noqa: E731

    def cabin_windows(q):
        d = np.full(q.nv, 10.0)
        for side, stations in FP.FIXED_WINDOWS.items():
            on = side_of(q) * side > 0
            for cx in stations:
                d = np.where(on, np.minimum(d, FP.window_sdf(q.V[:, 0], q.V[:, 2], cx)), d)
        return d
    # glazing holes (sequential single-sided trims, fields re-evaluated on the OML under the trimmed lining)
    glazing = [cabin_windows, lambda q: CG.sidewindow_sdf(q.V[:, 0], q.V[:, 1], q.V[:, 2]),
               lambda q: CG.windshield_sdf(q.V[:, 0], FP.signed_s(q.V[:, 0], q.UV[:, 1]), q.V[:, 2], q.V[:, 1])]
    for f in glazing:
        v = f(_lining_proxy(m))
        if (v < 0).any():
            m = trim(m, v, "positive")
    # reveals: every hole loop (the tube's end rings excluded) joined to the same loop on the OML
    reveals = []
    for loop in boundary_loops(m):
        Lv = m.V[loop]
        if Lv[:, 0].min() < x0 + 1e-3 or Lv[:, 0].max() > x1 - 1e-3:
            continue
        Ov = F.section(m.UV[loop, 0], m.UV[loop, 1] % 1.0)
        n = len(loop)
        i = np.arange(n)
        j = (i + 1) % n
        r = Mesh(np.vstack([Lv, Ov]), np.vstack([np.stack([i, j, n + j], 1), np.stack([i, n + j, n + i], 1)]))
        c = Ov.mean(0)
        if np.mean(np.sum((r.V[r.F].mean(1) - c) * r.face_normals(), 1)) > 0:
            r = r.flipped()                                                           # facing into the opening
        reveals.append(r)
    # door-panel seams (+ margin) and the floors
    for o in (FP.AIRSTAIR, FP.CARGO, FP.EXIT):
        pan = FP.door_panel(o)
        q = _lining_proxy(m)
        v = np.where(side_of(q) * o["side"] > 0, FP.rr((q.V[:, 0], q.V[:, 2]), pan) - LINING_DOOR_MARGIN, 10.0)
        if (v < 0).any():
            m = trim(m, v, "positive")
    m = trim(m, m.V[:, 2] - LINING_Z0, "positive")
    m = m.flipped()                                                                   # front faces toward the cabin
    xa = F.STA["cockpit_aft"]
    p = Part("interior_lining", "Side-wall & headliner lining (flight deck, cabin), window reveals", "interior",
             group="Interior", material_note="Moulded composite lining panels",
             info={"lining": f"{F.CABIN_LINING * 1000:.0f} mm inside the OML (cabin 1.52 m wide)",
                   "extent": f"STA {x0 * 1000:,.0f} - {x1 * 1000:,.0f}, flight deck to STA {xa * 1000:,.0f}"})
    rv = Mesh.merge(reveals)
    for piece, keep, mat in ((m, "negative", "lining_flightdeck"), (rv, "negative", "lining_flightdeck"),
                             (m, "positive", "lining"), (rv, "positive", "lining")):
        q = trim(piece, piece.V[:, 0] - xa, keep).compact()
        q._reveal = piece is rv          # reveals end ON the skin openings (test/fit_check.py checks them apart)
        p.add(q, mat)
    parts[p.id] = p


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def frame_ring(x, depth=0.055, n=144):
    t = np.linspace(0, 1, n, endpoint=False)
    outer = F.section(np.full(n, x), t)
    c = np.array([x, 0, float(F.z_mw(x))])
    d = outer - c
    dn = d / np.linalg.norm(d, axis=1, keepdims=True)
    o = outer - dn * 0.004
    i = outer - dn * (0.004 + depth)
    V = np.vstack([o, i])
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    UV = np.vstack([np.stack([np.full(n, x), t], 1)] * 2)
    return Mesh(V, Fc, UV=UV)


def cut_openings(m, margin=0.03):
    """Interrupt structure at door / window / windshield cut-outs."""
    from model.fuselage_parts import openings_field
    from cad.mesh import trim
    f = openings_field(m) - margin
    return trim(m, f, "positive") if (f < 0).any() else m


def frame_stations():
    """Numbered fuselage frames: the labelled Pilatus frames (fuselage.FRAMES FR10 ... FR40) with the frames between
    them interpolated at equal pitch, plus FR41 ... ahead of the tail-cone closure.  Returns [(name, STA)]."""
    import re
    lab = sorted((int(re.sub(r"\D", "", k)), v) for k, v in F.FRAMES.items() if k.startswith("FR"))
    out = []
    for (n0, x0), (n1, x1) in zip(lab[:-1], lab[1:]):
        for k in range(n0, n1):
            out.append((f"FR{k}", x0 + (x1 - x0) * (k - n0) / (n1 - n0)))
    n, x = lab[-1]
    pitch = (lab[-1][1] - lab[-2][1]) / (lab[-1][0] - lab[-2][0])
    from model import empennage as E
    while x < float(E.tail_cut_x(F.z_bot(min(x, F.STA["tail_end"])))) - 0.05:
        out.append((f"FR{n}", x))
        n, x = n + 1, x + pitch
    return out


RIB_BAY_CLEAR = 0.012          # ribs stop this far outside the main-gear bay liner (plan)
REAR_SPAR = 0.66               # rear-spar chord fraction


def rib_chord_end(y):
    """Aft end (chord fraction) of the wing box at BL y: the rear spar inside the flap / aileron bays (10 mm ahead of
    the cove where the cove reaches further forward), otherwise the trailing-edge rib end (97 %)."""
    if W.Y_FLAP[0] <= y <= W.Y_FLAP[1]:
        return min(REAR_SPAR, float(W.flap_cove(W.section_at(y))[:, 0].min()) - 0.01)
    if W.Y_AIL[0] <= y <= W.Y_AIL[1]:
        return min(REAR_SPAR, min(W.x_end_of_plain(W.section_at(y), float(W.ail_xh(y)))) - 0.01)
    return 0.97


def rib_chord_spans(y, x0=0.02, x1=0.97, min_len=0.02):
    """Chord-fraction spans [(xa, xb)] of the wing rib at BL y (M5): 2-97 % chord, ending at the rear spar (66 %,
    or just ahead of the cove) inside the flap and aileron bays, and cut round the main-gear bay liner
    (bays.main_bay_sdf + RIB_BAY_CLEAR) so no rib crosses the wheel well, leg slot or brace pocket."""
    from model.bays import main_bay_sdf
    x1 = min(x1, rib_chord_end(y))
    s = W.section_at(y)
    xc = np.linspace(x0, x1, 400)
    xs = s.lower(xc)[:, 0]
    ok = main_bay_sdf(xs, np.full_like(xs, y)) > RIB_BAY_CLEAR
    spans, i = [], 0
    while i < len(xc):
        if ok[i]:
            j = i
            while j + 1 < len(xc) and ok[j + 1]:
                j += 1
            if xc[j] - xc[i] >= min_len:
                spans.append((float(xc[i]), float(xc[j])))
            i = j + 1
        else:
            i += 1
    return spans


def build_structure(parts):
    from model import empennage as E
    from model.fuselage_parts import bulkhead, nose_trunnion_notch
    rings = []
    frames = frame_stations()
    for name, x in frames:
        r = frame_ring(x, depth=0.065 if x < 10 else 0.045)
        r = cut_openings(r)
        if (E.tail_cut_field(r.V[:, 0], r.V[:, 2]) > 0).any():
            r = trim(r, E.tail_cut_field(r.V[:, 0], r.V[:, 2]), "negative")
        rings.append(r)
    # stringers: kept above and below the window belt (belt WL 1.995-2.380 -> gap 1.95-2.43), to the tail closure
    strs = []
    x_end = float(E.tail_cut_x(2.2)) - 0.02
    for t in np.linspace(0, 1, 28, endpoint=False):
        z6 = float(F.section(np.array(6.0), np.array(t))[2])
        if 1.95 < z6 < 2.43:
            continue
        xs = np.linspace(3.05, x_end, 110)
        P = F.section(xs, np.full_like(xs, t))
        c = np.stack([xs, np.zeros_like(xs), F.z_mw(xs)], 1)
        d = P - c
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        tube = sweep_tube(P - d * 0.015, 0.008, n=6, cap=False)
        tube.UV = np.stack([tube.V[:, 0], np.full(len(tube.V), t)], 1)
        tube = trim(tube, E.tail_cut_field(tube.V[:, 0], tube.V[:, 2]) + 0.02, "negative")
        strs.append(cut_openings(tube, margin=0.02))
    # pressure bulkheads (forward one notched round the nose-gear trunnion, like the firewall)
    bh = [bulkhead(F.STA["firewall"] + 0.01, 0.97, notch=nose_trunnion_notch, normal=(1, 0, 0)),
          bulkhead(F.STA["aft_pressure_bulkhead"] + 0.01, 0.97, normal=(1, 0, 0))]
    # wing spars (front ~15 %, rear ~66 %) and ribs; the carry-through flattened under the cabin floor (wing.py)
    sp = []
    for frac in (0.15, 0.66):
        rows = []
        ys = np.linspace(-W.SEMI + 0.05, W.SEMI - 0.05, 60)
        for y in ys:
            s = W.section_at(abs(y))
            fr = frac if frac < 0.5 else min(frac, rib_chord_end(abs(y)))     # rear spar ahead of the aileron cove
            lo = s.lower(np.array(fr)) * [1, np.sign(y) if y != 0 else 1, 1]
            up = s.upper(np.array(fr)) * [1, np.sign(y) if y != 0 else 1, 1]
            lo = np.array([lo[0], y, lo[2] + 0.004])
            up = np.array([up[0], y, up[2] - 0.004])
            rows.append(np.linspace(lo, up, 4))
        m = grid_surface(np.array(rows))
        m.V = W.centre_section_clamp(m.V, margin=0.004)
        sp.append(m)
    ribs = []
    for y in list(np.arange(0.9, W.SEMI - 0.2, 0.55)):
        for xa, xb in rib_chord_spans(y):
            s = W.section_at(y)
            xx = np.linspace(xa, xb, max(4, int(np.ceil((xb - xa) / 0.03)) + 1))
            loop = np.vstack([s.lower(xx[::-1]) + [0, 0, 0.004], s.upper(xx[1:]) - [0, 0, 0.004]])
            for sg in (1, -1):
                ribs.append(planar_cap(loop * [1, sg, 1], (0, sg, 0)))
    p = Part("structure", "Primary structure: frames, stringers, spars, ribs", "structure", group="Structure",
             material_note="2024-T3 / 7075-T6, zinc-chromate primed",
             info={"frames": f"{len(frames)}: {frames[0][0]} (STA {frames[0][1] * 1000:.0f}) - {frames[-1][0]} "
                             f"(STA {frames[-1][1] * 1000:.0f}), labelled frames per the Pilatus drawing",
                   "wing": "2-spar box, ribs @ 550 mm"})
    p.add(Mesh.merge(rings + bh), "zinc_chromate").add(Mesh.merge(strs), "zinc_chromate")
    p.add(Mesh.merge(sp + ribs), "interior_green")
    parts[p.id] = p


def build(parts):
    build_flightdeck(parts)
    build_cabin(parts)
    build_lining(parts)
    build_structure(parts)
    return parts
