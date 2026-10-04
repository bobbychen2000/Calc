"""
Fuselage components: skin panels (cowling, forward, centre, aft), glazing,
doors, seals and seams -- all cut from the one lofted outer mould line so every
panel, door and window lies exactly on the same surface.
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, grid_surface, grid_normals, trim, band, boundary_loops, solidify, cap_ring, rotation_about
from cad import sdf2d
from model import fuselage as F
from model.parts import Part
from model import cockpit_glazing as CG

BIG = 10.0
SPLIT_FWD = 4.36          # forward / centre fuselage joint (frame)
SPLIT_AFT = 9.85          # aft pressure bulkhead
N_AROUND = 144

# ---------------------------------------------------------------------------
# opening definitions (side projection x/z)
#
# Stage-2 refit (sheet L3, drawing/openings_sheet.py).  Positions follow the registered Pilatus NGX
# drawing: port openings from its side view, STARBOARD windows from its plan view (the sheet-1
# starboard detail repeats the port stations), cross-checked against photos (window pitch pattern
# within 15 mm after a scale + offset fit, PRO s/n 3001 closed airstair door has no window) and against the
# Pilatus PC-12 technical-data side render (port openings within 7 mm of the drawing, no airstair-door window).
# Door sizes are the published clear openings (passenger door 0.61 x 1.35 m, cargo door 1.35 x 1.32 m, W x H),
# centred on the drawn doors; the drawn door outlines are kept as the panel seams (DOOR_PANELS).
# ---------------------------------------------------------------------------
CABIN_CROWN_WL = float(F.z_top(6.0))       # 2.769: constant cabin section STA 4.6-8.2 (model/fuselage.py)
# cabin windows: 'rectangular' PC-24 style = a Lame curve |dx/a|^n + |dz/b|^n = 1 (drawing: 300 x 385 mm,
# n = 4.23 fits the drawn outline within 0.7 mm; photos: w/h 0.78-0.82)
WIN_W, WIN_H, WIN_N = 0.300, 0.385, 4.2
WIN_HX, WIN_HZ = 0.5 * WIN_W, 0.5 * WIN_H
WIN_R = 0.084                              # corner radius of the best-fit round-cornered rectangle (rms 1.2 mm)
WIN_CROWN_DROP = 0.5815                    # window centre below the cabin crown (drawing: WL 1995-2380)
WIN_CZ = round(CABIN_CROWN_WL - WIN_CROWN_DROP, 4)          # 2.1875
FIXED_WINDOWS = {  # side -> window centre stations (windows in doors / the exit: DOOR_WINDOWS)
    -1: [5.605, 6.200, 6.980],                      # port, aft of the airstair door (side view)
    +1: [5.359, 6.980, 7.730, 8.494],               # starboard, exit window between 1 and 2 (plan view)
}
# Doors carry two outlines (side projection; W x H = projected x / z extents):
#  * the dicts AIRSTAIR / CARGO are the CLEAR OPENINGS: the published sizes (Pilatus PC-12 technical data:
#    passenger door 0.61 W x 1.35 H, cargo door 1.35 W x 1.32 H), sills on the cabin floor, centred on the doors;
#  * DOOR_PANELS are the door-panel SEAMS (the skin cut seen outside): the drawn door outlines of the Pilatus
#    drawing (0.64 x 1.40 and 1.40 x 1.47), confirmed by the Pilatus tech-data side render (seams 0.639 x 1.404
#    and 1.400 wide; its opening pattern fits the drawing within 7 mm).  Stage 3: cut the skin and the door slab
#    along the panel seam, build the jamb (door frame) along the clear opening.
DOOR_SILL_WL = 1.254                       # both clear-opening sills (cabin floor): drawn airstair seam 1229 + 25
AIRSTAIR = dict(side=-1, cx=4.970, cz=DOOR_SILL_WL + 0.675, hx=0.305, hz=0.675, r=0.085,
                hinge="bottom", open_deg=145.0)   # 0.61 x 1.35 m; integral airstair, opens down 145 deg: the open
#                                                   door's free edge lies on the 145 deg line in both MSN 3008 photos
#                                                   130 / 188 through their fitted cameras (outline and free edge; 160
#                                                   before, free edge ~5 cm off the ground: too far); open, the free
#                                                   edge is ~0.29 m off the ground (ground contact would be ~164 deg)
CARGO = dict(side=-1, cx=8.240, cz=DOOR_SILL_WL + 0.660, hx=0.675, hz=0.660, r=0.055,
             hinge="top", open_deg=120.0)         # 1.35 x 1.32 m; opens up ~120 deg (model judging r1 EXT1-02: the
#                                                  free edge projected through the fitted camera port_hangar_130 lies on
#                                                  photo 130's at 120 deg, 135 deg is ~90 px off; Pilatus render with the door
#                                                   open: free edge ~0.99 m above the hinge line)
EXIT = dict(side=+1, cx=6.205, cz=2.2015, hx=0.241, hz=0.3205, r=0.100,
            hinge=None, open_deg=None)     # over-wing emergency exit (plug), drawn 5964-6446 x 1881-2522 = the hatch
#                                            seam: 0.482 x 0.641 projected, 0.696 along the skin (FAR 23.807(b)
#                                            minimum 19 x 26 in); not a FAR-25 Type III (20 x 36 in)
DOOR_PANELS = {                            # door-panel seams (x/z centre, half sizes, corner radius), see above
    "door_airstair": dict(side=-1, cx=4.970, cz=1.929, hx=0.320, hz=0.700, r=0.100),   # 4650-5290 x 1229-2629
    "door_cargo": dict(side=-1, cx=8.240, cz=1.8945, hx=0.700, hz=0.7345, r=0.076),   # 7540-8940 x 1160-2629
    "exit_hatch": EXIT,                                                               # plug: seam = EXIT
}
DOOR_WINDOWS = {"door_airstair": None, "door_cargo": 7.958, "exit_hatch": 6.205}   # None: no window
# small features for the drawings / Stage-3 details (x, z centre, half sizes, radius)
DOOR_DETAILS = {
    "exit_handle": dict(side=+1, cx=6.205, cz=2.478, hx=0.060, hz=0.019, r=0.019),      # release handle
    "airstair_handle": dict(side=-1, cx=4.956, cz=1.710, hx=0.190, hz=0.032, r=0.032),  # sheet 2, +-45 mm
    "cargo_handle": dict(side=-1, cx=8.250, cz=1.650, hx=0.031, hz=0.155, r=0.031),     # sheet 2, +-45 mm
}
DOOR_HINGE_OFFSET = 0.025                  # hinge line inside the panel seam: bottom (airstair) / top (cargo); the
#                                            render shows a second line 25 mm below the cargo-door top seam

# windshield panes (x, s) where s = signed arc length from crown (+ starboard)
WS_CORE = [(3.345, 0.034), (3.470, 0.470), (3.880, 0.455), (3.905, 0.034)]
WS_R = 0.03
# cockpit side window (x, z) core polygon
SW_CORE = [(3.700, 1.985), (4.255, 1.985), (4.255, 2.385), (3.980, 2.430)]
SW_R = 0.045


def rr(p, o):
    return sdf2d.rrect(p[0], p[1], o["cx"], o["cz"], o["hx"], o["hz"], o["r"])


def lame_sdf(px, py, cx, cy, a, b, n):
    """Signed distance (m, negative inside) to the Lame curve |dx/a|^n + |dy/b|^n = 1: first-order
    (Sampson) distance of the degree-1 form G = (|u|^n + |v|^n)^(1/n); exact on the axes and on the curve,
    within a few % of the true distance over the few cm used for trims and seals."""
    u = np.abs(np.asarray(px, float) - cx) / a
    v = np.abs(np.asarray(py, float) - cy) / b
    G = (u ** n + v ** n) ** (1.0 / n)
    Gs = np.maximum(G, 1e-9)
    g = np.sqrt(((u / Gs) ** (n - 1) / a) ** 2 + ((v / Gs) ** (n - 1) / b) ** 2)
    return np.where(G < 1e-9, -min(a, b), (G - 1.0) / np.maximum(g, 1e-9))


def window_sdf(x, z, cx):
    """Cabin window centred at station cx (side projection x/z)."""
    return lame_sdf(x, z, cx, WIN_CZ, WIN_HX, WIN_HZ, WIN_N)


def window_outline(cx, n=240):
    """Closed (n+1, 2) outline (x, z) of the cabin window at station cx."""
    t = np.linspace(0.0, 2 * np.pi, n + 1)
    c, s = np.cos(t), np.sin(t)
    return np.c_[cx + WIN_HX * np.sign(c) * np.abs(c) ** (2.0 / WIN_N),
                 WIN_CZ + WIN_HZ * np.sign(s) * np.abs(s) ** (2.0 / WIN_N)]


def opening_outline(o, n_corner=16):
    """Closed outline (x, z) of a door / exit / detail dict (round-cornered rectangle)."""
    P = sdf2d.rrect_outline(o["cx"], o["cz"], o["hx"], o["hz"], o["r"], n_corner)
    return np.vstack([P, P[:1]])


def door_panel(o):
    """The door-panel seam dict (DOOR_PANELS) of an opening dict (AIRSTAIR / CARGO / EXIT); o itself if none."""
    for pid, od in (("door_airstair", AIRSTAIR), ("door_cargo", CARGO), ("exit_hatch", EXIT)):
        if o is od:
            return DOOR_PANELS.get(pid, o)
    return o


def hinge_line(o):
    """(x0, x1, z) of a door's hinge line in side projection -- on the door panel, DOOR_HINGE_OFFSET inside its
    bottom (airstair) or top (cargo) seam -- or None (EXIT: plug, no hinge)."""
    h = o.get("hinge")
    if h is None:
        return None
    p = door_panel(o)
    z = p["cz"] - p["hz"] + DOOR_HINGE_OFFSET if h == "bottom" else p["cz"] + p["hz"] - DOOR_HINGE_OFFSET
    return p["cx"] - p["hx"], p["cx"] + p["hx"], z


def openings_table():
    """Every fuselage-side opening as a flat record (id, kind, side, cx, cz, w, h, shape, hinge, host): the
    one list the drawings (and Stage-3 consumers: interior reveals, structure cut-outs, livery) read."""
    rows = []
    doors = (("door_airstair", "airstair door", AIRSTAIR), ("door_cargo", "cargo door", CARGO),
             ("exit_hatch", "emergency exit", EXIT))
    for pid, name, o in doors:
        p = DOOR_PANELS.get(pid, o)
        rows.append(dict(id=pid, kind="door" if pid != "exit_hatch" else "exit", name=name, side=o["side"],
                         cx=o["cx"], cz=o["cz"], w=2 * o["hx"], h=2 * o["hz"], shape=f"rrect r{o['r']:.3f}",
                         r=o["r"], hinge=o.get("hinge"), host=None, open_deg=o.get("open_deg"),
                         panel=dict(x0=p["cx"] - p["hx"], x1=p["cx"] + p["hx"], z0=p["cz"] - p["hz"],
                                    z1=p["cz"] + p["hz"], r=p["r"])))
        if DOOR_WINDOWS.get(pid) is not None:
            rows.append(dict(id=pid + "_win", kind="window", name=f"window in {name}", side=o["side"],
                             cx=DOOR_WINDOWS[pid], cz=WIN_CZ, w=WIN_W, h=WIN_H, shape=f"lame n{WIN_N:g}", r=WIN_R,
                             hinge=None, host=pid))
    for side, xs in FIXED_WINDOWS.items():
        for i, cx in enumerate(xs):
            rows.append(dict(id=f"win_{'p' if side < 0 else 's'}{i + 1}", kind="window", name="cabin window",
                             side=side, cx=cx, cz=WIN_CZ, w=WIN_W, h=WIN_H, shape=f"lame n{WIN_N:g}", r=WIN_R,
                             hinge=None, host=None))
    return sorted(rows, key=lambda r: (r["side"], r["cx"]))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
X0, X1 = F.STA["cowl_front"], F.STA["tail_end"]          # the loft range: every x-range below is taken from these
_perim_x = np.linspace(X0, X1, 200)
_perim_v = np.array([F.perimeter(x) for x in _perim_x])


def perim(x):
    return np.interp(x, _perim_x, _perim_v)


def signed_s(x, t):
    tt = np.where(t > 0.5, t - 1.0, t)
    return tt * perim(x)


def skin_grid(xs, ts):
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = F.section(X, T % 1.0)
    UV = np.stack([X, T], -1)                  # t unwrapped (a patch may run across the crown, t < 0)
    return P, UV


def skin_patch(x0, x1, t0, t1, d=0.010):
    xs = np.linspace(x0, x1, max(4, int(np.ceil((x1 - x0) / d)) + 1))
    pm = perim(0.5 * (x0 + x1))
    ts = np.linspace(t0, t1, max(4, int(np.ceil(abs(t1 - t0) * pm / d)) + 1))
    P, UV = skin_grid(xs, ts)
    return grid_surface(P, UV=UV)


def side_patch(o, side, pad=0.03, d=0.010):
    """Dense skin patch covering a side-projected rounded rect."""
    x0, x1 = o["cx"] - o["hx"] - pad, o["cx"] + o["hx"] + pad
    z0, z1 = o["cz"] - o["hz"] - pad, o["cz"] + o["hz"] + pad
    xm = 0.5 * (x0 + x1)
    ta = F.t_of(xm, z0, side)
    tb = F.t_of(xm, z1, side)
    ta, tb = min(ta, tb) - 0.004, max(ta, tb) + 0.004
    return skin_patch(x0, x1, ta, tb, d)


def xz_of(m):
    return m.V[:, 0], m.V[:, 2]


def side_mask(m, side):
    return (m.V[:, 1] * side) > 0.2


def rim(loop_V, loop_N, depth):
    """Inward extrusion of a boundary loop (door jamb / window reveal)."""
    a = loop_V
    b = np.roll(loop_V, -1, 0)
    ai = a - depth * loop_N
    bi = b - depth * np.roll(loop_N, -1, 0)
    n = len(a)
    V = np.vstack([a, b, bi, ai])
    i = np.arange(n)
    Fc = np.vstack([np.stack([i, i + n, i + 2 * n], 1), np.stack([i, i + 2 * n, i + 3 * n], 1)])
    m = Mesh(V, Fc)
    return m


# ---------------------------------------------------------------------------
# SDF fields over the main skin
# ---------------------------------------------------------------------------

def openings_field(m: Mesh):
    """Union of every opening cut into the fuselage skin (negative = hole): the union of openings_fields()."""
    return np.minimum.reduce([f(m) for f in openings_fields()])


def openings_fields():
    """The fuselage-skin openings as separate fields (negative = hole), trimmed one after the other by
    trim_openings(): windows / doors / nose bay (disjoint), then the cockpit side windows, then the windshield.  The
    side-window and windshield holes lie only PILLAR_WIDTH (25 mm) apart across the A-pillar, less than the 30-35 mm
    skin grid; one trim with their V-shaped min() field cut the pillar strip 8-21 mm wide (CONS-03), sequential trims
    (each field re-evaluated on the already trimmed mesh) cut each edge exactly."""
    return [_other_openings_field,
            lambda m: CG.sidewindow_sdf(m.V[:, 0], m.V[:, 1], m.V[:, 2]),
            lambda m: CG.windshield_sdf(m.V[:, 0], signed_s(m.V[:, 0], m.UV[:, 1]), m.V[:, 2], m.V[:, 1])]


def trim_openings(m: Mesh):
    """Cut every opening out of a skin mesh, one field at a time (see openings_fields)."""
    for f in openings_fields():
        v = f(m)
        if (v < 0).any():
            m = trim(m, v, "positive")
    return m


def _other_openings_field(m: Mesh):
    """Cabin windows, door-panel seams, the exit and the nose-gear bay (negative = hole)."""
    x, z = xz_of(m)
    y = m.V[:, 1]
    d = np.full(len(x), BIG)
    for side, stations in FIXED_WINDOWS.items():
        on = (y * side) > 0.2
        for cx in stations:
            d = np.where(on, np.minimum(d, window_sdf(x, z, cx)), d)
    for o in (AIRSTAIR, CARGO, EXIT):              # the skin is cut along the door-panel SEAM (DOOR_PANELS)
        on = (y * o["side"]) > 0.2
        d = np.where(on, np.minimum(d, rr((x, z), door_panel(o))), d)
    # nose-gear bay in the belly
    from model.bays import nose_bay_sdf
    d = np.minimum(d, np.where(z < 1.1, nose_bay_sdf(x, y), BIG))
    return d


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------

def build_skin():
    panels = [door_panel(o) for o in (AIRSTAIR, CARGO)]
    door_edges = [o["cx"] + s * o["hx"] for o in panels for s in (-1, 1)]
    # the chin-inlet step (keel 1.413 -> 1.233) and the raised lip face / nose (x_le 1.118-1.20, nose 14 mm): 2 mm
    # columns; the cheek behind it at 10 mm
    chin = list(np.arange(1.100, 1.262, 0.002)) + list(np.arange(1.262, 1.72, 0.010))
    # the crown's cowl-front blend (fuselage._top, review r4 GEO8-02: 45 -> 24 deg over its first 0.04 m): rows every
    # 6-12 mm ahead of the chin columns (the station grid alone put one row between 1.044 and 1.10)
    chin += [1.050, 1.057, 1.065, 1.075, 1.087]
    from model.bays import NOSE_BAY as _NB                          # nose-bay ends: rows through the corner radii
    bay = [e + sg * k for e, sg in ((_NB["cx"] - _NB["hx"], 1), (_NB["cx"] + _NB["hx"], -1))
           for k in np.linspace(0.0, _NB["r"], 6)]
    xs = F.station_grid(0.030, 0.05, extra=[SPLIT_FWD, *CG.KEY_STATIONS] + door_edges + chin + bay)
    xs = xs[np.r_[True, np.diff(xs) > 2e-4]]                       # drop near-duplicate stations (sliver columns)
    ts = np.linspace(0, 1, N_AROUND, endpoint=False)
    P, UV = skin_grid(xs, ts)
    from model import powerplant as PP
    ic = xs < 1.80
    Xs = PP.chin_shear_x(xs[ic], ts)                               # columns sheared onto the chin lip face
    P[ic] = F.section(Xs, np.broadcast_to(ts[None, :], Xs.shape))
    UV[ic, :, 0] = Xs
    P[ic] = PP.chin_cheek_displace(P[ic])                          # proud chin-inlet lip + cheek (CONS2-01)
    N = grid_normals(P, close_u=False, close_v=True)
    # the sheared columns: analytic normals of the raised skin S(X, t) (dS/dX x dS/dt at the grid points) -- differences
    # along the sheared grid lines cross the steep lip face at different heights from one around-line to the next and
    # tilted the polished lip's normals alternately (review r1 RES1-04: radial streaks round the lip)
    h, k = 2e-4, 2e-4
    T = np.broadcast_to(ts[None, :], Xs.shape)
    Xa, Xb = np.maximum(Xs - h, F.STA["cowl_front"]), Xs + h
    S_ = lambda X, t: PP.chin_cheek_displace(F.section(X, t % 1.0))     # noqa: E731
    Na = np.cross(S_(Xb, T) - S_(Xa, T), S_(Xs, T + k) - S_(Xs, T - k))
    Na /= np.maximum(np.linalg.norm(Na, axis=-1, keepdims=True), 1e-15)
    Na *= np.sign(np.sum(Na * N[ic], -1, keepdims=True) + 1e-12)
    N[ic] = Na

    def sub(x0, x1):
        i0 = int(np.searchsorted(xs, x0 - 1e-9))
        i1 = int(np.searchsorted(xs, x1 + 1e-9))
        return grid_surface(P[i0:i1], close_v=True, N=N[i0:i1], UV=UV[i0:i1])

    return xs, sub


SKIN_ANALYTIC_X = 1.80          # the cowl columns that carry analytic normals (build_skin: the sheared chin columns)
SKIN_ANALYTIC_TOL = 3.0e-3      # m: a vertex further than this from the analytic skin keeps its normal
SKIN_ANALYTIC_PARTS = ("cowl_upper", "cowl_lower", "chin_inlet")
SKIN_FACE_DEG = 50.0            # deg: largest lean of a vertex normal from its faces' (_lean_to_faces)


def skin_project(V, UV, iters=10):
    """Closest points of the raised cowl skin to the points V (n, 3) from their surface parameters UV: (distance (n,),
    unit normals (n, 3), unoriented) -- powerplant.cowl_project."""
    from model import powerplant as PP
    d, N, _ = PP.cowl_project(V, UV, iters)
    return d, N


def skin_analytic_normals(meshes, x_max=SKIN_ANALYTIC_X, tol=SKIN_ANALYTIC_TOL):
    """Give the cowl-skin vertices ahead of x_max (by their UV station) the analytic normal of the raised skin at their
    closest point (skin_project), in place; vertices further than tol from it (liners, the duct) keep theirs.
    build_skin sets them at the grid points, but every trim (the chin-lip iso-lines, the mouth / lip cuts, the
    livery's strokes) and the refinement interpolate between grid normals that turn ~80 deg across the lip's 8 mm
    nose: neighbouring vertices on one iso-line got normals from different columns and the lip's light / dark line
    became a sawtooth, the cowl's reflected streaks above it kinked (review r2 RES2-01).  Returns the count set."""
    n = 0
    for m in meshes:
        if m.UV is None or m.N is None or len(m.UV) != len(m.V):
            continue
        sel = np.nonzero(m.UV[:, 0] < x_max)[0]
        if not len(sel):
            continue
        d, N = skin_project(m.V[sel], m.UV[sel])
        ok = d < tol
        N *= np.where(np.sum(N * m.N[sel], 1) < 0, -1.0, 1.0)[:, None]
        m.N[sel[ok]] = N[ok]
        n += int(ok.sum())
        _lean_to_faces(m, sel[ok])
    return n


def _lean_to_faces(m, idx, max_deg=SKIN_FACE_DEG):
    """Where the mesh does not follow the analytic skin (the lip face's foot crease, the oblique columns of the keel
    step below the shear's polar range: a vertex up to a few mm off it), lean the vertex normals idx no further than
    max_deg from the vertex's area-weighted face normal: the shading then follows the faces that are there."""
    T = m.V[m.F]
    fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    acc = np.zeros_like(m.V)
    for k in range(3):
        np.add.at(acc, m.F[:, k], fn)
    acc = acc[idx]
    L = np.linalg.norm(acc, axis=1)
    ok = L > 1e-14
    a = acc[ok] / L[ok, None]
    a *= 1.0 if np.sum(acc * m.N[idx]) >= 0 else -1.0          # the faces' winding against the normals
    n = m.N[idx[ok]]
    c = np.sum(n * a, 1)
    far = c < np.cos(np.radians(max_deg))
    if not far.any():
        return
    p = n[far] - c[far, None] * a[far]
    pl = np.linalg.norm(p, axis=1, keepdims=True)
    p = np.where(pl > 1e-9, p / np.maximum(pl, 1e-12), 0.0)
    r = np.radians(max_deg)
    m.N[idx[ok][far]] = np.cos(r) * a[far] + np.sin(r) * p


def apply_skin_analytic_normals(parts):
    """skin_analytic_normals on the cowl / chin-inlet parts (model/build.py, after the livery and the refinement)."""
    for pid in SKIN_ANALYTIC_PARTS:
        if pid in parts:
            skin_analytic_normals([m for m, mat in parts[pid].meshes])


def bulkhead(x, scale=0.97, notch=None, normal=(1, 0, 0), n_rings=14):
    """Flat bulkhead in the fuselage section at station x (the section scaled about its max-breadth centre),
    optionally trimmed by notch(V) (negative = cut away)."""
    t = np.linspace(0, 1, N_AROUND, endpoint=False)
    sec = F.section(np.full_like(t, x), t)
    ctr = np.array([x, 0.0, float(F.z_mw(x))])
    u = np.linspace(0.0, 1.0, n_rings)
    P = ctr + (sec[None, :, :] - ctr) * (scale * u)[:, None, None]
    m = grid_surface(P, close_v=True)
    if notch is not None:
        f = notch(m.V)
        if (f < 0).any():
            m = trim(m, f, "positive")
    if np.dot(m.face_normals().mean(0), normal) < 0:
        m = m.flipped()
    m.N = np.tile(np.asarray(normal, float), (len(m.V), 1))
    return m


def nose_trunnion_notch(V):
    """Notch (negative inside) round the nose-gear trunnion and bay in the firewall / forward pressure bulkhead."""
    from model import gear as G
    zt = G.NOSE_PIVOT[2] + 0.075
    return np.maximum(np.abs(V[:, 1]) - 0.165, V[:, 2] - zt)


def nose_bay_field(m: Mesh):
    """Nose-gear bay cut-out in the belly (negative = hole), shared by the lower cowling and the forward fuselage."""
    from model.bays import nose_bay_sdf
    return np.where(m.V[:, 2] < 1.1, nose_bay_sdf(m.V[:, 0], m.V[:, 1]), BIG)


def build(parts_out: dict):
    xs, sub = build_skin()
    from model import powerplant as PP
    from model import empennage as E

    # ---- cowling (upper / lower halves split on the prop axis water line), cowl front -> firewall ----
    cowl = sub(X0, F.STA["firewall"])
    cowl = trim(cowl, PP.cowl_front_field(cowl.V), "positive")    # a constant gap behind the spinner base plane
    cowl = trim(cowl, PP.stack_root_field(cowl.V), "positive")    # annular cut-outs round the exhaust-stack roots
    split = cowl.V[:, 2] - (F.PROP_AXIS_Z + 0.02)
    up = trim(cowl, split, "positive")
    lo = trim(cowl, split, "negative")
    lo = trim(lo, nose_bay_field(lo), "positive")                  # nose-gear bay runs forward of the firewall
    lo, lip = PP.cut_chin_inlet(lo)                                # mouth hole + polished lip ring (chin_inlet part)
    skin_analytic_normals([up, lo, lip])                           # (again after the livery / refinement: build.py)
    parts_out["cowl_upper"] = Part("cowl_upper", "Upper engine cowling", "cowling",
                                   explode=(0, 0, 0.9), group="Powerplant installation",
                                   material_note="Carbon/Nomex honeycomb, Cu mesh")
    parts_out["cowl_upper"].add(up, "paint_white")
    # the dark liner of the annular cut-outs round the exhaust-stack roots (a recess in the cowl skin, split like it)
    liner = Mesh.merge([PP.stack_root_liner(s) for s in (1, -1)])
    sl = liner.V[:, 2] - (F.PROP_AXIS_Z + 0.02)
    liner_up, liner_lo = trim(liner, sl, "positive"), trim(liner, sl, "negative")
    parts_out["cowl_upper"].add(liner_up, "exhaust_soot")
    parts_out["cowl_lower"] = Part("cowl_lower", "Lower engine cowling", "cowling",
                                   explode=(0, 0, -0.8), group="Powerplant installation",
                                   material_note="Carbon/Nomex honeycomb")
    parts_out["cowl_lower"].add(lo, "paint_white").add(liner_lo, "exhaust_soot")
    parts_out["chin_inlet"] = Part("chin_inlet", "Chin air inlet: polished lip, mouth & duct entry", "cowling",
                                   explode=(-0.4, 0, -0.75), group="Powerplant installation",
                                   material_note="Polished lip, electrically de-iced; composite duct")
    # the lip's metal = livery SURFACES['inlet_lip'] (review r4 EXT8-02: its own neutral polished aluminium)
    from model.livery import SURFACES as _LS
    parts_out["chin_inlet"].add(lip, _LS["inlet_lip"])

    # ---- forward fuselage (cockpit) ----
    fwd = sub(F.STA["firewall"], SPLIT_FWD)
    fwd = trim_openings(fwd)
    parts_out["fus_fwd"] = Part("fus_fwd", "Forward fuselage & flight deck shell", "fuselage_fwd",
                                explode=(-0.9, 0, 0.25), group="Fuselage",
                                material_note="2024-T3 skins, frames 10-16")
    parts_out["fus_fwd"].add(fwd, "paint_white")

    # ---- centre fuselage (pressure cabin) ----
    cen = sub(SPLIT_FWD, SPLIT_AFT)
    cen = trim_openings(cen)
    parts_out["fus_center"] = Part("fus_center", "Centre fuselage (pressure cabin)", "fuselage_center",
                                   explode=(0, 0, 0.35), group="Fuselage",
                                   material_note="2024-T3 skin, 5.8 psi max differential")
    parts_out["fus_center"].add(cen, "paint_white")

    # ---- aft fuselage / tail cone: loft to the tail end, cut at the rudder leading edge, closed by a bulkhead ----
    aft = sub(SPLIT_AFT, X1)
    aft = trim(aft, E.tail_cut_field(aft.V[:, 0], aft.V[:, 2]), "negative")
    parts_out["fus_aft"] = Part("fus_aft", "Aft fuselage & tail cone", "fuselage_aft",
                                explode=(1.1, 0, 0.3), group="Fuselage",
                                material_note="Semi-monocoque, frames 33-40; tail-cone closure at the rudder")
    parts_out["fus_aft"].add(aft, "paint_white").add(E.tail_closure(), "paint_white")

    build_glazing(parts_out)
    build_doors(parts_out)
    return parts_out


def _param_box(field, x0, x1, t0, t1, pad=0.0, dx=0.004):
    """(x, t) bounding box of the region field < pad on the OML patch x0..x1, t0..t1 (t may run below 0)."""
    xs = np.arange(x0, x1 + dx, dx)
    ts = np.arange(t0, t1 + 1e-9, dx / 2.0 / float(perim(0.5 * (x0 + x1))) * 2.0)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    Pp = F.section(X, T % 1.0)
    S = np.where(T % 1.0 > 0.5, T % 1.0 - 1.0, T % 1.0) * perim(X)
    f = field(Pp[..., 0], Pp[..., 1], Pp[..., 2], S)
    ins = f < pad
    if not ins.any():
        raise ValueError("glazing field empty on the patch")
    return float(X[ins].min()), float(X[ins].max()), float(T[ins].min()), float(T[ins].max())


def _assert_covers(field, patch_box, box0, what):
    """The glass patch (x, t) box must contain the whole hole (field < 0 on the search box box0)."""
    hx0, hx1, ht0, ht1 = _param_box(field, *box0, pad=0.0)
    px0, px1, pt0, pt1 = patch_box
    if not (px0 <= hx0 and hx1 <= px1 and pt0 <= ht0 and ht1 <= pt1):
        raise AssertionError(f"{what}: glass patch {patch_box} does not cover the hole {(hx0, hx1, ht0, ht1)}")


# cabin-window edge ring (glazing_cabin, door and exit windows): the NGX panes are flush with only a thin, barely
# darker edge (photos 130 / 0517; material review F5): an 8 mm ring (4 mm over the hole, 4 mm on the skin) in the
# glossy dark-grey 'seal_cabin', panes in the two-ply 'glass_cabin'.  The flight-deck frames are the PRO black
# ('seal' = the anti-glare black of the mask, trim_black).
CABIN_RING = (-0.004, 0.004)
# flight-deck pane retainers (VQA r2 LIV2-05, material 'glazing_retainer'): signed-distance band round each pane, over
# the glass / on the skin.  VQA r3: 20 mm (-6 / +14) read as a broad silver frame and turned the 46 mm centre post
# silver (photo 130: a black post with a bright fastener line, thin bright edges round the panes) -> 12 mm (-6 / +6)
GLAZING_RETAINER = (-0.006, 0.006)


def build_glazing(parts_out):
    glass_parts = []
    seals = []
    # cabin windows (fixed)
    for side, stations in FIXED_WINDOWS.items():
        for cx in stations:
            o = dict(cx=cx, cz=WIN_CZ, hx=WIN_HX, hz=WIN_HZ, r=WIN_R)
            p = side_patch(o, side, pad=0.03, d=0.010)
            fn = lambda m, cx=cx: window_sdf(m.V[:, 0], m.V[:, 2], cx)
            glass_parts.append(trim(p, fn(p) - 0.010, "negative").offset(-0.006))
            seals.append(band(p, fn, *CABIN_RING).offset(0.0015))
    # cockpit side windows: patch = the extent of sidewindow_sdf on the OML (+ 25 mm), checked to cover the hole
    sw_glass, sw_seal = [], []
    sw_f = lambda x, y, z, s: CG.sidewindow_sdf(x, y, z)                           # noqa: E731
    for side in (-1, 1):
        box0 = (3.30, 4.60) + ((0.02, 0.45) if side > 0 else (0.55, 0.98))
        x0, x1, t0, t1 = _param_box(sw_f, *box0, pad=0.025)
        _assert_covers(sw_f, (x0, x1, t0, t1), box0, f"side window {side:+d}")
        p = skin_patch(x0, x1, t0, t1, d=0.012)
        fn = lambda m: CG.sidewindow_sdf(m.V[:, 0], m.V[:, 1], m.V[:, 2])       # noqa: E731
        sw_glass.append(trim(p, fn(p) - 0.010, "negative").offset(-0.005))
        sw_seal.append(band(p, fn, *GLAZING_RETAINER).offset(0.0015))
    # windshield (two panes either side of the centre post): the extent of windshield_sdf on the OML (+ 25 mm)
    ws_f = lambda x, y, z, s: CG.windshield_sdf(x, s, z, y)                        # noqa: E731
    box0 = (3.05, 4.30, -0.40, 0.40)
    x0, x1, t0, t1 = _param_box(ws_f, *box0, pad=0.025)
    _assert_covers(ws_f, (x0, x1, t0, t1), box0, "windshield")
    p = skin_patch(x0, x1, t0, t1, d=0.012)
    fn = lambda m: CG.windshield_sdf(m.V[:, 0], signed_s(m.V[:, 0], m.UV[:, 1]), m.V[:, 2], m.V[:, 1])  # noqa: E731
    ws_glass = trim(p, fn(p) - 0.012, "negative").offset(-0.004)
    ws_seal = band(p, fn, *GLAZING_RETAINER).offset(0.0015)

    n_fixed = sum(len(v) for v in FIXED_WINDOWS.values())
    g = Part("glazing_cabin", f"Cabin windows ({n_fixed} fixed, stretched acrylic)", "glazing",
             explode=(0, 0, 0), group="Glazing", qty=n_fixed,
             material_note="Two-ply laminated stretched acrylic")
    g.add(Mesh.merge(glass_parts), "glass_cabin").add(Mesh.merge(seals), "seal_cabin")
    parts_out[g.id] = g
    w = Part("glazing_flightdeck", "Windshield (2 heated panes) & side windows (no DV window, PRO)", "glazing",
             explode=(-0.3, 0, 0.35), group="Glazing", qty=4,
             material_note="Heated laminated glass windshield, acrylic side windows")
    # VQA r2 LIV2-05: the band round each pane is the polished glazing RETAINER (photos 0517 / 82 / 188: a thin bright
    # edge inside the black PRO mask), not more black -- the mask outline (surround_sdf) is unchanged
    w.add(ws_glass, "glass_windshield").add(Mesh.merge(sw_glass), "glass").add(
        Mesh.merge([ws_seal] + sw_seal), "glazing_retainer")
    parts_out[w.id] = w


DOOR_T = 0.045             # door slab thickness
DOOR_GAP = 0.004           # door panel inside the skin cut-out (panel seam)
JAMB_D = 0.060             # [E] opening jamb depth from the door stop (49 -> 109 mm inside the skin)
JAMB_TAN = 0.026           # [E] its outer, tan band (photos 130 / 188, door open) to 75 mm = the doors' inner-lining
#                            faces; the inner band and the stop's cabin side are lining (the cabin view with the doors
#                            closed shows white lining round them: P1046402, review r1 F8)
INNER_BODY = dict(t=0.030, inset=0.008)   # [E] cargo-door inner lining panel (45 -> 75 mm, as the airstair's
#                                           airstair.LINING_D), inside the clear opening: hides the tan jamb band
DOOR_NAMES = {"door_airstair": "Airstair passenger door (0.61 x 1.35 m clear opening)",
              "door_cargo": "Cargo door (1.35 x 1.32 m clear opening)",
              "exit_hatch": "Over-wing emergency exit (plug hatch, right)"}
DOOR_NOTES = {"door_airstair": "Downward-opening, integral steps",
              "door_cargo": "Upward-opening, 120 deg (its gas struts are not modelled: owner decision)",
              "exit_hatch": "Plug type, removed inward (0.48 x 0.64 m projected)"}
DOOR_EXPLODE = {"door_airstair": (0, -0.9, 0), "door_cargo": (0, -1.0, 0.2), "exit_hatch": (0, 0.8, 0.1)}
DOOR_HANDLE = {"door_airstair": "airstair_handle", "door_cargo": "cargo_handle", "exit_hatch": "exit_handle"}
DOORS = (("door_airstair", AIRSTAIR), ("door_cargo", CARGO), ("exit_hatch", EXIT))


def door_pivot(o):
    """Hinge pivot (model axes) of a door dict: on the skin at hinge_line(), rotation about +x by open_deg outward
    (bottom hinge: the top swings out and down; top hinge: the bottom swings out and up).  None for the plug exit."""
    hl = hinge_line(o)
    if hl is None:
        return None
    x0, x1, zh = hl
    side = o["side"]
    xm = 0.5 * (x0 + x1)
    origin = (xm, side * float(F.side_y(xm, zh)), zh)
    ang = np.radians(o["open_deg"]) * (1 if o["hinge"] == "bottom" else -1) * (-side)
    return dict(origin=origin, axis=(1, 0, 0), kind="door", open=float(ang), open_deg=float(o["open_deg"]))


def door_free_edge(o, n=21):
    """(BL, WL) of the lowest point of a hinged door's free edge (the panel seam opposite the hinge, on the OML) in the
    fully open pose: e.g. the airstair's ground clearance open (sheet L3).  None for the plug exit."""
    pv = door_pivot(o)
    if pv is None:
        return None
    pan = door_panel(o)
    xs = np.linspace(pan["cx"] - pan["hx"] + pan["r"], pan["cx"] + pan["hx"] - pan["r"], n)
    ze = pan["cz"] + pan["hz"] if o["hinge"] == "bottom" else pan["cz"] - pan["hz"]
    P = np.c_[xs, [o["side"] * float(F.side_y(x, ze)) for x in xs], np.full(n, ze)]
    M = rotation_about(pv["axis"], pv["open"], pv["origin"])
    Q = P @ M[:3, :3].T + M[:3, 3]
    k = int(np.argmin(Q[:, 2]))
    return float(abs(Q[k, 1])), float(Q[k, 2])


def _loop_near(ring, fn):
    """Boundary loop of `ring` whose points lie closest to the zero set of fn(x, z)."""
    best = None
    for loop in boundary_loops(ring):
        lv = ring.V[loop]
        sd = np.abs(fn(lv[:, 0], lv[:, 2])).mean()
        if best is None or sd < best[0]:
            best = (sd, loop)
    return None if best is None else best[1]


def build_door(pid, o):
    """Door slab cut along the panel seam (DOOR_PANELS), window, handle, steps; pivot from hinge_line / open_deg."""
    side = o["side"]
    pan = door_panel(o)
    p = side_patch(pan, side, pad=0.03, d=0.020)
    skin = trim(p, rr(xz_of(p), pan) + DOOR_GAP, "negative")
    wcx = DOOR_WINDOWS.get(pid)
    if wcx is not None:
        skin = trim(skin, window_sdf(skin.V[:, 0], skin.V[:, 2], wcx), "positive")
    slab_out, slab_in = solidify(skin, DOOR_T, separate=True)
    part = Part(pid, DOOR_NAMES[pid], "doors", pivot=door_pivot(o), explode=DOOR_EXPLODE[pid], group="Doors",
                material_note=DOOR_NOTES[pid],
                info={"clear opening": f"{2 * o['hx']:.2f} x {2 * o['hz']:.2f} m",
                      "panel (seam)": f"{2 * pan['hx']:.2f} x {2 * pan['hz']:.2f} m",
                      "opens": f"{o['open_deg']:.0f} deg" if o.get("open_deg") else "plug, removed inward"})
    part.add(slab_out, "paint_white")
    if pid == "door_airstair":                      # edge band, inner body, integral steps, stanchions (model/airstair)
        from model import airstair
        airstair.build(part, o, skin)
    else:
        part.add(slab_in, "lining")
    if pid == "door_cargo":                         # inner lining panel inside the clear opening (window reveal on)
        ip = side_patch(o, side, pad=0.03, d=0.020)
        ip = trim(ip, rr(xz_of(ip), o) + INNER_BODY["inset"], "negative")
        if wcx is not None:
            ip = trim(ip, window_sdf(ip.V[:, 0], ip.V[:, 2], wcx), "positive")
        ip = ip.offset(-DOOR_T)
        part.add(solidify(ip, INNER_BODY["t"]), "lining")
    if wcx is not None:
        wo = dict(cx=wcx, cz=WIN_CZ, hx=WIN_HX, hz=WIN_HZ, r=WIN_R)
        wp = side_patch(wo, side, pad=0.03, d=0.010)
        fn = lambda m: window_sdf(m.V[:, 0], m.V[:, 2], wcx)                         # noqa: E731
        part.add(trim(wp, fn(wp) - 0.010, "negative").offset(-0.006), "glass_cabin")
        part.add(band(wp, fn, *CABIN_RING).offset(0.0015), "seal_cabin")
    h = DOOR_DETAILS[DOOR_HANDLE[pid]]
    hp = side_patch(h, side, pad=0.01, d=0.004)
    part.add(trim(hp, rr(xz_of(hp), h), "negative").offset(0.0012), "metal_dark")
    return part


def _into_opening(m, o):
    """Rim m wound so its front faces look into the opening o (the renders shade the back faces of a paint as the
    cabin lining, the viewer's cutaway too)."""
    c = np.array([o["cx"], o["side"] * float(F.side_y(o["cx"], o["cz"])), o["cz"]])
    return m.flipped() if np.mean(np.sum((c - m.V[m.F].mean(1)) * m.face_normals(), 1)) < 0 else m


def _hinge_band(o, margin=0.004):
    """f(z) > 0 away from the hinge edge of the clear opening o (side projection): top-hinged doors lose the band
    above the straight top edge's start (cz + hz - r - margin), bottom-hinged ones the band below cz - hz + r + margin."""
    h = o.get("hinge")
    if h == "top":
        z0 = o["cz"] + o["hz"] - o["r"] - margin
        return lambda z: z0 - np.asarray(z, float)
    if h == "bottom":
        z0 = o["cz"] - o["hz"] + o["r"] + margin
        return lambda z: np.asarray(z, float) - z0
    return lambda z: np.ones_like(np.asarray(z, float))


def _runs(keep):
    """Index arrays of the maximal runs of True in a CLOSED boolean loop (wrapping round the end)."""
    keep = np.asarray(keep, bool)
    n = len(keep)
    if keep.all():
        return [np.r_[np.arange(n), 0]]
    if not keep.any():
        return []
    start = int(np.argmin(keep))                  # a False position: the runs do not wrap past it
    idx = (np.arange(n) + start) % n
    out, cur = [], []
    for i in idx:
        if keep[i]:
            cur.append(i)
        elif cur:
            out.append(np.array(cur))
            cur = []
    if cur:
        out.append(np.array(cur))
    return [r for r in out if len(r) > 1]


def _back_face(m, d=0.0008):
    """The back of a single-sided band: a copy d behind it (against its face normals), wound the other way -- the tan
    jamb band faces into the opening, and from the cabin the well showed its back side in the same tan (review r2 F7)."""
    q = m.copy().compute_normals()
    return Mesh(q.V - d * q.N, q.F[:, ::-1].copy()).compute_normals()


def _open_runs(flag):
    """[(indices, value)] of the maximal runs of equal values in an OPEN boolean sequence, each run extended by one
    index into the next so consecutive runs share their boundary point (no gap between the strips)."""
    flag = np.asarray(flag, bool)
    out, i0 = [], 0
    for i in range(1, len(flag) + 1):
        if i == len(flag) or flag[i] != flag[i0]:
            out.append((np.arange(i0, min(i + 1, len(flag))), bool(flag[i0])))
            i0 = i
    return out


def _rim_open(V, N, d0, d1):
    """Strip along an open polyline V (normals N) from depth d0 to d1 inward (a jamb band)."""
    a, b = V - d0 * N, V - d1 * N
    n = len(V)
    i = np.arange(n - 1)
    Fc = np.vstack([np.stack([i, i + 1, n + i + 1], 1), np.stack([i, n + i + 1, n + i], 1)])
    return Mesh(np.vstack([a, b]), Fc)


HINGE_SEAL = dict(depth=DOOR_T + 0.004, reach=DOOR_GAP + 0.006)   # [E] see _hinge_seal


def _hinge_seal(Lv, Ln, pan):
    """Final judge r1 R7: the rubber seal closing the panel-seam gap along a door's HINGE edge from the cabin side -- a
    flat strip at the foot of the dark hinge-gap rim (HINGE_SEAL depth inside the skin), reaching HINGE_SEAL 'reach'
    toward the door (across the DOOR_GAP slot, under the slab's inner edge), facing the cabin.  Without it the cabin
    renders saw the sky through the 4 mm slot as a saturated blue line along the cargo door's top.  The door swings
    OUTWARD from its hinge, so nothing of it ever enters the strip (fit_check door-swing sweeps)."""
    d, w = HINGE_SEAL["depth"], HINGE_SEAL["reach"]
    A = Lv - d * Ln
    T = np.gradient(Lv, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    t = np.cross(Ln, T)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
    cen = np.array([pan["cx"], 0.0, pan["cz"]])
    sg = np.sign(np.sum((cen - Lv)[:, [0, 2]] * t[:, [0, 2]], 1).mean())
    B = A + w * sg * t
    n = len(A)
    i = np.arange(n - 1)
    m = Mesh(np.vstack([A, B]), np.vstack([np.stack([i, i + 1, n + i + 1], 1), np.stack([i, n + i + 1, n + i], 1)]))
    return m.flipped() if np.mean(np.sum(m.face_normals() * Ln.mean(0), 1)) > 0 else m    # faces the cabin


def build_doors(parts_out):
    for pid, o in DOORS:
        parts_out[pid] = build_door(pid, o)
        if pid == "door_airstair":                  # handrail + restraint cables (model/airstair.py child_parts)
            from model import airstair
            for c in airstair.child_parts(o, parent=pid):
                parts_out[c.id] = c
    # seams, skin-edge lips, door stops (flange between the panel seam and the clear opening) and opening jambs.  The
    # lip (the frame edge round the panel seam, DOOR_T + 4 mm deep) carries the livery like the skin beside it (photos
    # 130 / 188: a dark blue lip, then the seal, then the tan / khaki jamb lining; material review F9)
    seams, jambs, stops, lips, jambs_in, stops_in, seals = [], [], [], [], [], [], []
    for pid, o in DOORS:
        pan = door_panel(o)
        p = side_patch(pan, o["side"], pad=0.03, d=0.010)
        fs = lambda m, q=pan: rr((m.V[:, 0], m.V[:, 2]), q)                         # noqa: E731
        seams.append(band(p, fs, 0.0, 0.007).offset(0.0008))
        ring = band(p, fs, 0.0, 0.03)
        loop = _loop_near(ring, lambda x, z, q=pan: rr((x, z), q))
        if loop is not None:
            # along the hinge edge the lip is the dark hinge gap, not painted skin: seen from the cabin over the sill /
            # under the cargo door's top it read as a blue paint line (review r1 C1)
            Lv, Ln = ring.V[loop], ring.N[loop]
            hb = _hinge_band(o, margin=-0.02)(Lv[:, 2]) > 0 if o.get("hinge") else np.ones(len(Lv), bool)
            if hb.all():
                lips.append(_into_opening(rim(Lv, Ln, DOOR_T + 0.004), pan))
            else:
                for a in _runs(hb):
                    lips.append(_into_opening(_rim_open(Lv[a], Ln[a], 0.0, DOOR_T + 0.004), pan))
                for a in _runs(~hb):
                    seams.append(_into_opening(_rim_open(Lv[a], Ln[a], 0.0, DOOR_T + 0.004), pan))
                    seals.append(_hinge_seal(Lv[a], Ln[a], pan))
        if pan is not o:                             # door with a clear opening inside the panel seam
            fo = lambda m, q=o: rr((m.V[:, 0], m.V[:, 2]), q)                        # noqa: E731
            st = trim(trim(p, fs(p) + 0.002, "negative"), fo(trim(p, fs(p) + 0.002, "negative")), "positive")
            # no stop / jamb along the HINGE edge (the hinge is there; the door's inner skin and lining swing through
            # that band: review r1 M2 / M4 sweeps)
            hband = _hinge_band(o)
            st = trim(st, hband(st.V[:, 2]), "positive")
            st = st.offset(-(DOOR_T + 0.004))
            stops.append(st)
            stops_in.append(st.offset(-0.0015))                   # its cabin side: lining
            loop = _loop_near(st, lambda x, z, q=o: rr((x, z), q))
            if loop is not None:
                Lv, Ln = st.V[loop], st.N[loop]
                sx, sz = Lv[:, 0] + (DOOR_T + 0.004) * Ln[:, 0], Lv[:, 2] + (DOOR_T + 0.004) * Ln[:, 2]
                keep = (np.abs(rr((sx, sz), o)) < 0.003) & (hband(sz) > 0)     # on the clear opening, off the hinge
                # the airstair's top (free-edge) and forward jambs are lining over their whole depth: they face the
                # cabin, and through the closed door's 8 mm inner-body gap their tan outer band showed as an arc from
                # the club (review r2 F7, fd_ngx2281 entry photos: white frame); the aft jamb, which faces forward to
                # the photos 130 / 188 cameras with the door open, keeps the tan band
                bottom_hinged = o.get("hinge") == "bottom"
                ztop = o["cz"] + o["hz"] - o["r"] - 0.02
                for a in _runs(keep):
                    Lr, Nr = Lv[a], Ln[a]
                    up = ((Lr[:, 2] + (DOOR_T + 0.004) * Nr[:, 2] > ztop) | (Lr[:, 0] < o["cx"])) & bottom_hinged
                    for seg, in_top in _open_runs(up):
                        if len(seg) < 2:
                            continue
                        if in_top:
                            jambs_in.append(_into_opening(_rim_open(Lr[seg], Nr[seg], 0.0, JAMB_D), o))
                        else:
                            tan = _into_opening(_rim_open(Lr[seg], Nr[seg], 0.0, JAMB_TAN), o)
                            jambs.append(tan)
                            jambs_in.append(_back_face(tan))          # its back, seen from the cabin in the well
                            jambs_in.append(_into_opening(_rim_open(Lr[seg], Nr[seg], JAMB_TAN, JAMB_D), o))
    s = Part("door_frames", "Door surrounds, seals, stops & jambs", "doors", group="Doors",
             material_note="Machined door frames")
    s.add(Mesh.merge(seams + seals), "seam").add(Mesh.merge(jambs), "jamb").add(Mesh.merge(stops), "jamb")
    s.add(Mesh.merge(jambs_in + stops_in), "lining")
    s.add(Mesh.merge(lips), "paint_white")          # unpainted skin material: model/livery.py paints it
    from model import airstair                      # the handrail's jamb bracket / pivot pin, the cables' jamb fittings
    for m, mat in airstair.jamb_fittings(AIRSTAIR):
        s.add(m, mat)
    parts_out[s.id] = s
