"""
Airstair passenger door D1 (port, bottom-hinged): the door behind its outer skin -- edge, inner body, the integral
steps and the handrails (Stage 3).

The door keeps everything fuselage_parts defines for it: the clear opening AIRSTAIR, the panel seam DOOR_PANELS,
hinge_line / door_pivot (axis, origin, open 160 deg) and the slab DOOR_T.  fuselage_parts.build_door cuts the painted
outer skin along the panel seam (unchanged) and calls build() here for the rest.  Like every part the geometry is
built in the door's CLOSED pose (model axes); the treads are laid out in the OPEN pose, where they are horizontal, and
rotated back about the hinge.  Above the lining panel everything stays inside the clear opening (INSET), clear of the
door stops and the 60 mm jambs.

Reference (refs/cache, not in git): MSN 3008 handover photos 130 / 188 (door open: grey bolted edge band, white
inner face and side stringers, three grey tread trays with dark tops, the bottom step at the free edge, a red inner
handle below the third tray, polished two-link handrails from stanchions on the stringers to fittings on the jamb,
thin restraint cables), NGX s/n 2281 cabin photo (door closed: the dark bottom-step tray at the top, the red lever
below it, a polished rod folded down the door), POH 'integral steps'.  The rail joints were measured on photos 130 /
188 with their fitted cameras (rays through the stringer plane).  Source tags: [S] sourced, [M] measured /
proportioned on those photos, [E] estimated, [D] derived from the approved parameters.  No drawing or interior table
carries a step pitch: the treads divide the drawn sill height (fuselage_parts.DOOR_SILL_WL) into N_RISERS equal
risers [D].

Door part (rigid, pivot unchanged): edge band + fasteners, flange, lining panel, perimeter frame (side stringers),
treads + pads, bottom step, inner handle, the two stanchions.  Handrails: a rigid door cannot carry a folding handrail,
so the moving pieces are child parts of door_airstair that FOLD about their own x-parallel pivot, in the door's frame
(pivot kind 'fold', 'follows': 'door_airstair', 'window': the door-travel fraction over which they unfold, 'open': the
angle at full unfold):
  door_airstair_rail     lower rods + knee fittings, pinned to the stanchion heads; built folded down the door
                         (the closed-door cabin photo), unfolded they rise to the knee at hand height
  door_airstair_rail_up  upper rods, knee -> jamb fitting; built stowed INSIDE the door slab (hidden when closed)
  door_airstair_cable    restraint cables, jamb -> stringer clamp; built stowed inside the door slab
With the door open and every child at pivot.open the pieces meet (the lower rod's knee is the upper rod's end, the
fittings sit on the jambs).  A viewer / renderer that does not animate 'fold' leaves them as built (lower rods folded
down the stair, upper rods and cables hidden), which still reads as a closed-up handrail.
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, grid_surface, planar_cap, cylinder, superellipsoid, rotation_about
from model import fuselage as F
from model.parts import Part

# ---------------------------------------------------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------------------------------------------------
INSET = 0.008          # [E] inner body / stringers inside the clear opening AIRSTAIR (jamb + door-stop clearance)
LINING_D = 0.075       # [E] inner lining panel depth below the OML (slab DOOR_T 45 + 30 mm inner body; the cabin
#                        side-wall lining is 85 mm: the stringers stand 55 mm proud of it when closed)
FRAME = dict(w=0.040,        # [M] side stringers ~40 mm wide (photo 188: white strips beside the trays)
             h=0.065,        # [M] standing 65 mm off the lining panel along the sides
             h_sill=0.010,   # [E] flush sill member at the hinge edge (top of the stair)
             h_top=0.030,    # [E] low member at the free edge (bottom of the stair, under the foot step)
             blend=(0.0, 0.060))   # [E] height blend beyond the corner arcs (sill end: within the arc, so the
#                                    folded rail rests on a full-height stringer; free edge: 60 mm further)
N_RISERS = 5           # [D] sill (cabin floor WL) -> ground in equal risers: 3 treads + the bottom step at the free
#                        edge (photo 188: three grey trays, then the foot area; 1254 / 5 = 251 mm risers)
TREAD = dict(depth=0.160,    # [M] tray depth (horizontal, open)
             t=0.020,        # [E] top plate + frame
             lip=0.045,      # [M] front lip (photo 188: tall grey tray fronts)
             nose_r=0.008,   # [E] rounded nosing
             embed=0.012,    # [E] into the lining panel
             gap=0.002,      # [E] to the stringer walls
             pad=(0.022, 0.022, 0.020, 0.0022))   # [E] anti-slip pad inset back / front / sides, thickness
FOOT = dict(depth=0.215, lip=0.030)   # [M] bottom step at the free edge (foot, photo 188: the step he stands on)
RAIL = dict(r=0.0125,        # [M] polished rods ~25 mm (photos 130 / 188, against the 22x8.50 tyre scale)
            post_wl=0.56,    # [M] stanchion foot on the stringer at open WL 0.56, between treads 2 and 3 (photo 188)
            post=0.130,      # [M] stanchion height over the stringer top: its head (the lower rod's pivot) at BL
            #                  1.18-1.21, WL 0.62-0.71 in photos 130 / 188
            post_r=0.014,    # [E] stanchion tube radius
            K=(1.59, 1.24),  # [M] knee (BL, WL) in the open pose: photos 130 / 188, rays through the stringer plane
            #                  gave BL 1.58-1.60, WL 1.23-1.29 (the hand grips just above the joint)
            A_wl=1.97,       # [M] jamb fitting WL (photos 188 / 130: WL 2.02 / 1.91 on the fwd jamb)
            A_depth=0.065,   # [E] fittings bolted to the jamb face (jamb: 49-109 mm inside the skin)
            knee_r=0.017, knee_l=0.050,   # [E] knee / eye fittings
            lug=(0.020, 0.032, 0.012))    # [E] stanchion foot half sizes (x, along, up)
CABLE = dict(r=0.0030,       # [M] thin restraint cables (photos 188 / 130: thin lines jamb -> stringers)
             C_wl=1.75,      # [M] upper end on the jamb (photo 188: WL 1.75)
             z_low=0.71,     # [M] lower end on the stringer at open WL 0.71 (photo 188, between treads 2 and 3)
             pin=0.008)      # [E] its clamp pin 8 mm inside the stringer top
HANDLE = dict(zs=2.31,       # [M] inner door handle between tread 3 and the bottom step (photo 188: red lever there;
              #                  NGX cabin photo: red lever just below the top tray of the closed door)
              x=(4.80, 5.06),  # [E] lever span (station), hub at the aft end
              w=0.034, t=0.018, off=0.024, tilt=12.0, hub_r=0.024)   # [E] section, off the panel, twist (deg)
FASTENERS = dict(pitch=0.065, r=0.0042, h=0.0015)   # [M] fastener row on the grey edge band (photos 130 / 188)
MAT = dict(edge="metal", flange="lining", body="lining", frame="lining", tread="metal", bracket="lining",
           antislip="black", rod="chrome", fitting="steel", cable="steel", handle="prop_band_red",
           fastener="metal_dark")


# ---------------------------------------------------------------------------------------------------------------------
# door frame: section of the OML at the door (constant over STA 4.6-8.2) and the open pose
# ---------------------------------------------------------------------------------------------------------------------
class Door:
    """Geometry context of the airstair door: clear opening o, panel seam pan, side, the hinge rotation."""

    def __init__(self, o):
        from model.fuselage_parts import door_panel, door_pivot
        self.o, self.pan, self.side = o, door_panel(o), o["side"]
        self.cx = o["cx"]
        zs = np.linspace(o["cz"] - o["hz"] - 0.05, o["cz"] + o["hz"] + 0.05, 25)
        for x in (self.pan["cx"] - self.pan["hx"], self.pan["cx"] + self.pan["hx"]):
            dev = np.abs(F.side_y(x, zs) - F.side_y(self.cx, zs)).max()
            assert dev < 5e-4, f"airstair: the OML section varies over the door ({dev * 1000:.1f} mm)"
        self.pv = door_pivot(o)
        self.M = rotation_about((1, 0, 0), self.pv["open"], self.pv["origin"])     # closed -> open
        self.Mi = np.linalg.inv(self.M)
        # tabulated section (b = |y|, z) and its outward normal, for fast surface coordinates of arbitrary points
        self._zs = np.linspace(o["cz"] - o["hz"] - 0.25, o["cz"] + o["hz"] + 0.12, 4001)
        self._bs = self.b(self._zs)
        self._nb, self._nz = self.normal(self._zs)

    # -- section law (b = |y| at water line z), outward unit normal (nb, nz) in the (b, z) plane
    def b(self, z):
        return F.side_y(self.cx, np.asarray(z, float))

    def normal(self, z):
        z = np.asarray(z, float)
        h = 1e-4
        db = (self.b(z + h) - self.b(z - h)) / (2 * h)
        n = np.hypot(1.0, db)
        return 1.0 / n, -db / n

    def bz(self, zs, d):
        """(b, z) of the point at depth d (m, along the inward normal) under the OML point at water line zs."""
        nb, nz = self.normal(zs)
        return self.b(zs) - d * nb, np.asarray(zs, float) - d * nz

    def p3(self, x, zs, d):
        """Model-axes point(s) at station x, surface water line zs, depth d (closed pose)."""
        b, z = self.bz(zs, d)
        x, b, z = np.broadcast_arrays(np.asarray(x, float), b, z)
        return np.stack([x, self.side * b, z], -1)

    def surf_coords(self, b, z):
        """(zs, depth) of (b, z) points: the foot of the normal on the section curve (fixed point on the table)."""
        b, z = np.asarray(b, float), np.asarray(z, float)
        zs = z.copy()
        for _ in range(6):
            bs = np.interp(zs, self._zs, self._bs)
            nb = np.interp(zs, self._zs, self._nb)
            nz = np.interp(zs, self._zs, self._nz)
            d = (bs - b) * nb + (zs - z) * nz
            zs = z + d * nz
        return zs, d

    # -- closed <-> open pose ((b, z) at the door station, or model points)
    def open_bz(self, b, z):
        P = np.stack(np.broadcast_arrays(np.full_like(np.asarray(b, float), self.cx), self.side * np.asarray(b, float),
                                         np.asarray(z, float)), -1)
        Q = P @ self.M[:3, :3].T + self.M[:3, 3]
        return self.side * Q[..., 1], Q[..., 2]

    def closed_bz(self, b, z):
        P = np.stack(np.broadcast_arrays(np.full_like(np.asarray(b, float), self.cx), self.side * np.asarray(b, float),
                                         np.asarray(z, float)), -1)
        Q = P @ self.Mi[:3, :3].T + self.Mi[:3, 3]
        return self.side * Q[..., 1], Q[..., 2]

    def to3(self, x, b, z):
        return np.stack(np.broadcast_arrays(np.asarray(x, float), self.side * np.asarray(b, float),
                                            np.asarray(z, float)), -1)

    # -- clear opening / stringers (side projection x, zs)
    def corners(self):
        o = self.o
        return (o["cx"] - o["hx"] + o["r"], o["cx"] + o["hx"] - o["r"],
                o["cz"] - o["hz"] + o["r"], o["cz"] + o["hz"] - o["r"])

    def frame_x(self):
        """(x0, x1) of the stringer centre lines (fwd, aft)."""
        o, c, w = self.o, INSET, FRAME["w"]
        return o["cx"] - o["hx"] + c + 0.5 * w, o["cx"] + o["hx"] - c - 0.5 * w

    def tread_x(self):
        o, c, w, g = self.o, INSET, FRAME["w"], TREAD["gap"]
        return o["cx"] - o["hx"] + c + w + g, o["cx"] + o["hx"] - c - w - g

    def frame_h(self, zs):
        """Stringer height over the lining panel at surface water line zs (sill -> sides -> free edge)."""
        x0, x1, z0, z1 = self.corners()
        r = self.o["r"] - INSET
        zb, zt = z0 - r, z1 + r
        bl_s, bl_t = FRAME["blend"]
        s_b = _smooth((np.asarray(zs, float) - zb) / (r + bl_s))
        s_t = _smooth((zt - np.asarray(zs, float)) / (r + bl_t))
        h = FRAME["h_sill"] + (FRAME["h"] - FRAME["h_sill"]) * s_b
        return FRAME["h_top"] + (h - FRAME["h_top"]) * s_t

    # -- open-pose inner face (lining panel) as a b(z) function
    def wall(self):
        """Open-pose inner face (lining panel depth) as (b, z) sorted by z, over the inset opening only."""
        m = INSET + 0.006
        zs = np.linspace(self.o["cz"] - self.o["hz"] + m, self.o["cz"] + self.o["hz"] - m, 800)
        b, z = self.bz(zs, LINING_D)
        bo, zo = self.open_bz(b, z)
        k = np.argsort(zo)
        return bo[k], zo[k]

    def levels(self):
        """Open-pose tread top water lines, top (sill) down: N_RISERS - 1 levels (the last = the bottom step)."""
        from model.fuselage_parts import DOOR_SILL_WL
        return [DOOR_SILL_WL * (1.0 - k / N_RISERS) for k in range(1, N_RISERS)]


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------------------------------
# mesh helpers
# ---------------------------------------------------------------------------------------------------------------------
def _orient(m: Mesh):
    """Wind every face to agree with its vertex normals."""
    fn = np.cross(m.V[m.F[:, 1]] - m.V[m.F[:, 0]], m.V[m.F[:, 2]] - m.V[m.F[:, 0]])
    bad = np.sum(fn * m.N[m.F].sum(1), 1) < 0
    m.F[bad] = m.F[bad][:, ::-1]
    return m


def _strip(A, B, smooth=True, close=False):
    """Quad strip between two corresponding polylines A, B (n, 3): shared vertices (smooth along the strip) or
    separate vertices per quad (flat).  The caller sets the normals and winds the faces (_orient)."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    n = len(A)
    idx = np.arange(n if close else n - 1)
    j = (idx + 1) % n
    if smooth:
        V = np.vstack([A, B])
        Fc = np.vstack([np.stack([idx, j, n + j], 1), np.stack([idx, n + j, n + idx], 1)])
        m = Mesh(V, Fc)
    else:
        V = np.vstack([A[idx], A[j], B[j], B[idx]])
        k = len(idx)
        q = np.arange(k)
        Fc = np.vstack([np.stack([q, k + q, 2 * k + q], 1), np.stack([q, 2 * k + q, 3 * k + q], 1)])
        m = Mesh(V, Fc)
    return m


def _extrude(P2, x0, x1, door, segs, caps_mat):
    """Prism of the closed-pose (b, z) polygon P2 (n, 2) between stations x0, x1.  segs = [(i0, i1, smooth, mat)]
    partition the polygon edges i0..i1 (inclusive vertex indices, wrapping); returns [(Mesh, mat)] with end caps."""
    P2 = np.asarray(P2, float)
    n = len(P2)
    area = 0.5 * np.sum(P2[:, 0] * np.roll(P2[:, 1], -1) - np.roll(P2[:, 0], -1) * P2[:, 1])
    ccw = area > 0
    out = []
    for i0, i1, smooth, mat in segs:
        cnt = i1 - i0 if i1 > i0 else (i1 - i0) % n          # (0, n): the whole loop
        ids = [(i0 + k) % n for k in range(cnt + 1)]
        if len(ids) < 2:
            continue
        Q = P2[ids]
        e = np.diff(Q, axis=0)
        en = np.stack([e[:, 1], -e[:, 0]], 1) if ccw else np.stack([-e[:, 1], e[:, 0]], 1)   # outward edge normals
        en /= np.maximum(np.linalg.norm(en, axis=1, keepdims=True), 1e-12)
        A = door.to3(x0, Q[:, 0], Q[:, 1])
        B = door.to3(x1, Q[:, 0], Q[:, 1])
        if smooth and len(Q) > 2:
            vn = np.vstack([en[:1], en[:-1] + en[1:], en[-1:]])
            vn /= np.linalg.norm(vn, axis=1, keepdims=True)
            m = _strip(A, B, smooth=True)
            N3 = door.to3(0.0, vn[:, 0], vn[:, 1])
            m.N = np.vstack([N3, N3])
        else:
            m = _strip(A, B, smooth=False)
            N3 = door.to3(0.0, en[:, 0], en[:, 1])
            m.N = np.vstack([N3, N3, N3, N3])
        out.append((_orient(m), mat))
    if caps_mat:
        for x, s in ((x0, -1.0), (x1, 1.0)):
            cap = planar_cap(door.to3(x, P2[:, 0], P2[:, 1]), (s, 0.0, 0.0))
            out.append((cap, caps_mat))
    return out


def _rr_loop(door, inset, n_arc=10, n_side=None, n_h=8):
    """Concentric round-cornered-rectangle loop (x, zs) of the clear opening inset by `inset`, CCW in the side view,
    sampled so that loops of different insets correspond point by point (shared corner centres).  Also returns the
    row structure used by the lining panel: (loop, rows) with rows = [(zs, x_left, x_right)] bottom -> top."""
    x0, x1, z0, z1 = door.corners()
    r = door.o["r"] - inset
    if n_side is None:
        n_side = max(8, int(np.ceil((z1 - z0) / 0.018)))
    xb = np.linspace(x0, x1, n_h + 1)
    zsd = np.linspace(z0, z1, n_side + 1)
    a = np.linspace(0.0, 0.5 * np.pi, n_arc + 1)[1:-1]                       # arc interior angles
    pts = [np.c_[xb, np.full_like(xb, z0 - r)]]                                            # bottom, -> +x
    pts.append(np.c_[x1 + r * np.sin(a), z0 - r * np.cos(a)])                              # BR arc
    pts.append(np.c_[np.full_like(zsd, x1 + r), zsd])                                      # right, up
    pts.append(np.c_[x1 + r * np.cos(a), z1 + r * np.sin(a)])                              # TR arc
    pts.append(np.c_[xb[::-1], np.full_like(xb, z1 + r)])                                  # top, -> -x
    pts.append(np.c_[x0 - r * np.sin(a), z1 + r * np.cos(a)])                              # TL arc
    pts.append(np.c_[np.full_like(zsd, x0 - r), zsd[::-1]])                                # left, down
    pts.append(np.c_[x0 - r * np.cos(a), z0 - r * np.sin(a)])                              # BL arc
    loop = np.vstack(pts)
    # rows (bottom -> top): the left side of the loop (BL arc, left side, TL arc), mirrored about the centre line
    ad = a[::-1]
    left_z = np.r_[z0 - r, z0 - r * np.sin(ad), zsd, z1 + r * np.sin(a), z1 + r]
    left_x = np.r_[x0, x0 - r * np.cos(ad), np.full_like(zsd, x0 - r), x0 - r * np.cos(a), x0]
    # (bottom row / top row span the straight edges x0..x1)
    xm = 0.5 * (x0 + x1)
    rows = [(z, xl, 2 * xm - xl) for z, xl in zip(left_z, left_x)]
    return loop, rows


def _row_grid(door, rows, n_u, depth_fn):
    """Grid over the rows (zs, x_left, x_right), n_u + 1 columns, at depth depth_fn(zs) -> Mesh (normals: inward)."""
    Z = np.array([r[0] for r in rows])
    XL = np.array([r[1] for r in rows])
    XR = np.array([r[2] for r in rows])
    u = np.linspace(0.0, 1.0, n_u + 1)
    X = XL[:, None] + (XR - XL)[:, None] * u[None, :]
    ZS = np.broadcast_to(Z[:, None], X.shape)
    P = door.p3(X, ZS, depth_fn(ZS))
    nb, nz = door.normal(ZS)
    m = grid_surface(P, N=-door.to3(0.0, nb, nz))   # facing the cabin (inward) in the closed pose
    return _orient(m)


# ---------------------------------------------------------------------------------------------------------------------
# door body
# ---------------------------------------------------------------------------------------------------------------------
def _slab_back(skin, door_t):
    """Inner face (flange) and rim (edge band) of the door slab behind the outer skin (as cad.mesh.solidify builds
    them; kept apart here for their materials)."""
    from cad.mesh import boundary_loops
    inner = skin.offset(-door_t).flipped()
    c = skin.V.mean(0)
    rims = []
    for loop in boundary_loops(skin):
        a = skin.V[loop]
        m = _strip(a, a - door_t * skin.N[loop], smooth=True, close=True)
        # normals: the side-view outward direction of the seam loop (the edge band faces the jamb)
        t = np.roll(a, -1, 0) - np.roll(a, 1, 0)
        n = np.stack([t[:, 2], np.zeros(len(a)), -t[:, 0]], 1)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        sgn = np.sign(np.sum(n * (a - c) * [1, 0, 1], 1).mean())
        m.N = np.vstack([sgn * n, sgn * n])
        rims.append(_orient(m))
    return inner, Mesh.merge(rims)


def _fasteners(skin, door_t):
    """A row of fastener heads round the edge band (the slab rim), mid-depth, FASTENERS pitch."""
    from cad.mesh import boundary_loops
    heads = []
    c = skin.V.mean(0)
    for loop in boundary_loops(skin):
        a = skin.V[loop]
        n = skin.N[loop]
        seg = np.linalg.norm(np.roll(a, -1, 0) - a, axis=1)
        s = np.r_[0.0, np.cumsum(seg)]
        closed = np.vstack([a, a[:1]])
        ncl = np.vstack([n, n[:1]])
        tan = np.roll(a, -1, 0) - np.roll(a, 1, 0)             # side-view normal of the seam loop (as _slab_back)
        sv = np.stack([tan[:, 2], np.zeros(len(a)), -tan[:, 0]], 1)
        sv /= np.maximum(np.linalg.norm(sv, axis=1, keepdims=True), 1e-12)
        sv *= np.sign(np.sum(sv * (a - c) * [1, 0, 1], 1).mean())
        svc = np.vstack([sv, sv[:1]])
        for t in np.arange(0.5 * FASTENERS["pitch"], s[-1], FASTENERS["pitch"]):
            p = np.array([np.interp(t, s, closed[:, k]) for k in range(3)])
            nn = np.array([np.interp(t, s, ncl[:, k]) for k in range(3)])
            nn /= np.linalg.norm(nn)
            q = p - 0.5 * door_t * nn
            out = np.array([np.interp(t, s, svc[:, k]) for k in range(3)])     # normal to the edge band (it used
            out -= nn * np.dot(out, nn)                        # to point from the door centre: heads cut the lips)
            out /= np.linalg.norm(out)
            heads.append(cylinder(q - 0.0005 * out, q + FASTENERS["h"] * out, FASTENERS["r"], n=8))
    return Mesh.merge(heads)


def inner_body(door):
    """Lining panel + perimeter frame (side stringers, sill and free-edge members): [(Mesh, mat)]."""
    from model.fuselage_parts import DOOR_T
    c, w = INSET, FRAME["w"]
    outer, _ = _rr_loop(door, c)
    inner, rows = _rr_loop(door, c + w)
    zs_o = outer[:, 1]
    h = door.frame_h(zs_o)                                   # per loop point (outer loop's zs for both loops)
    top_d = LINING_D + h
    # lining panel (inside the inner loop)
    panel = _row_grid(door, rows, 10, lambda zs: np.full_like(zs, LINING_D))
    # frame top band between the loops
    A = door.p3(outer[:, 0], outer[:, 1], top_d)
    B = door.p3(inner[:, 0], inner[:, 1], top_d)
    top = _strip(A, B, smooth=True, close=True)
    nb, nz = door.normal(np.r_[outer[:, 1], inner[:, 1]])
    top.N = -door.to3(0.0, nb, nz)
    _orient(top)
    # walls: outer (DOOR_T -> top, facing the jamb), inner (top -> panel, facing the door centre)
    wo = _strip(door.p3(outer[:, 0], outer[:, 1], DOOR_T - 0.001), A, smooth=True, close=True)
    wi = _strip(B, door.p3(inner[:, 0], inner[:, 1], LINING_D), smooth=True, close=True)
    for m, sgn in ((wo, 1.0), (wi, -1.0)):
        L = outer if m is wo else inner
        tx = np.roll(L[:, 0], -1) - np.roll(L[:, 0], 1)
        tz = np.roll(L[:, 1], -1) - np.roll(L[:, 1], 1)
        nx, nzs = tz, -tx                                     # outward in the side view (CCW loop)
        nn = np.hypot(nx, nzs)
        nx, nzs = sgn * nx / nn, sgn * nzs / nn
        nb_, nz_ = door.normal(L[:, 1])
        # side-view outward direction -> 3-D (x, along the surface up = the section tangent)
        tb, tzz = -nz_, nb_                                   # section tangent (increasing zs) in (b, z)
        N3 = np.stack([nx, door.side * nzs * tb, nzs * tzz], -1)
        N3 /= np.linalg.norm(N3, axis=1, keepdims=True)
        m.N = np.vstack([N3, N3])
        _orient(m)
    return [(panel, MAT["body"]), (top, MAT["frame"]), (wo, MAT["frame"]), (wi, MAT["frame"])]


def inner_handle(door):
    """Red inner door handle: a lever lying on the lining panel, its hub at the aft end: [(Mesh, mat)]."""
    h = HANDLE
    zs = h["zs"]
    nb, nz = door.normal(zs)
    up = -door.to3(0.0, nb, nz)
    al = door.to3(0.0, -nz, nb)
    up, al = up / np.linalg.norm(up), al / np.linalg.norm(al)
    a = np.radians(h["tilt"])
    ex = np.cos(a) * np.array([1.0, 0, 0]) + np.sin(a) * al
    ey = np.cross(up, ex)
    x0, x1 = h["x"]
    L = x1 - x0
    hub = door.p3(x1 - 0.03, zs, LINING_D)
    c = hub - 0.5 * (L - 0.03) * ex + (h["off"]) * up
    lever = superellipsoid(c, (0.5 * L, 0.5 * h["w"], 0.5 * h["t"]), e=(0.3, 0.3), nu=10, nv=20,
                           R=np.stack([ex, ey, up], 1))
    boss = cylinder(hub - 0.004 * up, hub + (h["off"] + 0.012) * up, h["hub_r"], n=20)
    return [(lever, MAT["handle"]), (boss, MAT["fitting"])]


# ---------------------------------------------------------------------------------------------------------------------
# treads
# ---------------------------------------------------------------------------------------------------------------------
def _hit_wall(p, d, wb, wz, embed):
    """First t > 0 where p + t d crosses the (embedded) open-pose wall b = wb(z) - embed."""
    def g(t):
        q = p + t * d
        return q[0] - (np.interp(q[1], wz, wb) - embed)
    ts = np.linspace(0.0, 0.6, 601)
    gv = np.array([g(t) for t in ts])
    k = np.nonzero(np.sign(gv[1:]) != np.sign(gv[:-1]))[0]
    if not len(k):
        return p + 0.6 * d
    a, b_ = ts[k[0]], ts[k[0] + 1]
    for _ in range(40):
        m = 0.5 * (a + b_)
        if np.sign(g(m)) == np.sign(g(a)):
            a = m
        else:
            b_ = m
    return p + 0.5 * (a + b_) * d


def tread_profiles(door):
    """Open-pose (b, z) profiles of the treads, top (sill) down, the last = the bottom step.  Each: dict(poly, i_top,
    i_front, z, b_back, b_front) -- poly CCW-agnostic, vertex runs: top plate 0..i_top, nosing + lip ..i_front, then the
    underside / bracket back to 0 along the wall."""
    wb, wz = door.wall()
    lv = door.levels()
    em = TREAD["embed"]
    out = []
    for k, zk in enumerate(lv):
        foot = k == len(lv) - 1
        bw = float(np.interp(zk, wz, wb))
        if foot:                                        # flush with the free edge (inner face end)
            bf = min(bw + FOOT["depth"], float(wb[np.argmin(wz)]) - 0.004)
            lip = FOOT["lip"]
        else:
            bf, lip = bw + TREAD["depth"], TREAD["lip"]
        rn = TREAD["nose_r"]
        top = [(bw - em, zk), (bf - rn, zk)]
        a = np.linspace(0.5 * np.pi, 0.0, 6)[1:]
        nose = [(bf - rn + rn * np.cos(t), zk - rn + rn * np.sin(t)) for t in a]
        lipb = (bf, zk - lip)
        # underside: 45 deg back to the wall, then along the (embedded) wall up to the top
        q = _hit_wall(np.array(lipb), np.array([-1.0, -1.0]) / np.sqrt(2.0), wb, wz, em)
        zw = np.linspace(q[1], zk, 12)[1:-1]
        wall = [(float(np.interp(z, wz, wb)) - em, z) for z in zw]
        poly = top + nose + [lipb, (float(q[0]), float(q[1]))] + wall
        out.append(dict(poly=np.array(poly), i_top=1, i_front=len(top) + len(nose), z=zk, b_back=bw, b_front=bf,
                        foot=foot))
    return out


def treads(door):
    """Tread trays (metal top + nosing + lip, lining bracket / underside) and anti-slip pads: [(Mesh, mat)]."""
    xa, xb = door.tread_x()
    out = []
    pb, pf, ps, pt = TREAD["pad"]
    for tp in tread_profiles(door):
        P = tp["poly"]
        bc, zc = door.closed_bz(P[:, 0], P[:, 1])
        P2 = np.c_[bc, zc]
        n = len(P2)
        segs = [(0, tp["i_top"], False, MAT["tread"]),
                (tp["i_top"], tp["i_front"], True, MAT["tread"]),
                (tp["i_front"], tp["i_front"] + 1, False, MAT["bracket"]),
                (tp["i_front"] + 1, n, True, MAT["bracket"])]
        out += _extrude(P2, xa, xb, door, segs, MAT["bracket"])
        # anti-slip pad (open pose: a thin plate on the top)
        zk = tp["z"]
        Q = np.array([(tp["b_back"] + pb, zk - 0.001), (tp["b_front"] - pf, zk - 0.001),
                      (tp["b_front"] - pf, zk + pt), (tp["b_back"] + pb, zk + pt)])
        bc, zc = door.closed_bz(Q[:, 0], Q[:, 1])
        out += _extrude(np.c_[bc, zc], xa + ps, xb - ps, door, [(0, 4, False, MAT["antislip"])], MAT["antislip"])
    return out


# ---------------------------------------------------------------------------------------------------------------------
# handrails: joints in the open pose, the pieces in their folded / stowed (built) poses, the fold pivots
# ---------------------------------------------------------------------------------------------------------------------
def _frame_top(door, zs, extra=0.0):
    """Closed-pose (b, z) of the stringer top (+ extra above it) at surface water line zs."""
    return door.bz(zs, LINING_D + door.frame_h(zs) + extra)


def _zs_at_open_z(door, z_open, extra=0.0):
    """Surface water line zs of the stringer-top point whose open-pose water line is z_open."""
    zs = np.linspace(door.o["cz"] - door.o["hz"], door.o["cz"] + door.o["hz"], 2000)
    _, zo = door.open_bz(*_frame_top(door, zs, extra))
    k = np.argsort(zo)
    return float(np.interp(z_open, zo[k], zs[k]))


def _post(door, zs):
    """Stanchion base (stringer top) and head (the lower rod's pivot), closed-pose (b, z), at surface water line zs:
    the head stands RAIL post off the stringer top along the surface normal."""
    top = LINING_D + float(door.frame_h(zs))
    return np.array(door.bz(zs, top - 0.004), float), np.array(door.bz(zs, top + RAIL["post"]), float)


def rail_points(door):
    """Open-pose (b, z) of the handrail joints (the same on both sides): B stanchion head (lower rod pivot), K knee,
    A jamb fitting; restraint cable jamb end Cj and stringer clamp Cs.  zsB, zsC: their surface water lines."""
    zs = np.linspace(door.o["cz"] - door.o["hz"], door.o["cz"] + door.o["hz"], 2000)
    base = np.stack(door.bz(zs, LINING_D + door.frame_h(zs)), -1)
    zo = door.open_bz(base[:, 0], base[:, 1])[1]
    k = np.argsort(zo)
    zsB = float(np.interp(RAIL["post_wl"], zo[k], zs[k]))                  # stanchion foot
    B = np.array(door.open_bz(*_post(door, zsB)[1]))
    K = np.array(RAIL["K"], float)
    A = np.array(door.bz(RAIL["A_wl"], RAIL["A_depth"]), float)           # fuselage-fixed (open pose = world)
    zsC = _zs_at_open_z(door, CABLE["z_low"], -CABLE["pin"])
    Cs = np.array(door.open_bz(*_frame_top(door, zsC, -CABLE["pin"])))
    Cj = np.array(door.bz(CABLE["C_wl"], RAIL["A_depth"]), float)
    return dict(B=B, K=K, A=A, Cs=Cs, Cj=Cj, zsB=zsB, zsC=zsC)


def _yz(door, bz):
    bz = np.asarray(bz, float)
    return np.stack([door.side * bz[..., 0], bz[..., 1]], -1)


def _rot_yz(P, c, a):
    """Rotate model (y, z) points P about centre c by a (right-handed about +x)."""
    ca, sa = np.cos(a), np.sin(a)
    d = np.asarray(P, float) - c
    return c + np.stack([ca * d[..., 0] - sa * d[..., 1], sa * d[..., 0] + ca * d[..., 1]], -1)


def _angle_x(u, v):
    """Right-handed angle about +x from u to v (model y, z)."""
    return float(np.arctan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1]))


def _fold_lower(door, Bd, Kd):
    """Lower rod folded from the stanchion head Bd toward the hinge edge, along the door at the head's depth (the
    NGX cabin photo: the folded rod runs down the door toward the floor): (K folded (b, z), angle about +x folded ->
    deployed)."""
    zsB, dB = (float(v) for v in door.surf_coords(Bd[0], Bd[1]))
    L = float(np.linalg.norm(Kd - Bd))
    dz = np.linspace(-1.4, -0.05, 2701)
    T = np.stack(door.bz(zsB + dz, dB), -1)
    Ls = np.linalg.norm(T - Bd, axis=1)
    k = np.nonzero(np.diff(np.sign(Ls - L)))[0]
    if not len(k):
        raise RuntimeError("airstair: no fold position for the lower rail")
    k = k[-1]                                                  # the crossing nearest the stanchion
    t = (L - Ls[k]) / (Ls[k + 1] - Ls[k])
    Kf = T[k] + t * (T[k + 1] - T[k])
    yB = _yz(door, Bd)
    return Kf, _angle_x(_yz(door, Kf) - yB, _yz(door, Kd) - yB)


def _stow(door, p, q, r, r_end, prefer=None, need=0.0015):
    """Stowed pose of one straight piece p -> q (deployed, door frame (b, z); radius r, end fittings r_end) inside the
    door body at the stringer: depth r .. stringer top - r (2 mm margins), inside the inset outline.  The piece turns
    about an x-parallel axis; returns dict(pivot=(y, z), open=angle stowed -> deployed, seg=(p_s, q_s), margin).
    Coarse-to-fine search over the stowed midpoint (surface zs, depth) and direction (along the door +- 25 deg); of
    the stows with at least `need` margin the one whose turning centre lies nearest `prefer` (b, z) is taken, so the
    piece swings about a natural point (the stanchion head, the cable clamp) instead of sliding."""
    x0, x1, z0, z1 = door.corners()
    ri = door.o["r"] - INSET
    zlo, zhi = z0 - ri, z1 + ri
    t = np.linspace(0.0, 1.0, 33)
    R = np.where((t < 0.04) | (t > 0.96), r_end, r) + 0.002
    L = float(np.linalg.norm(np.asarray(q) - np.asarray(p)))
    Yp, Yq = _yz(door, p), _yz(door, q)
    pref = None if prefer is None else _yz(door, prefer)

    def evaluate(zc, dep, dang):
        zc, dep, dang = (np.asarray(v, float).ravel() for v in np.broadcast_arrays(zc, dep, dang))
        mb, mz = door.bz(zc, dep)
        nb, nz = door.normal(zc)
        th = np.arctan2(nb, -nz) + dang                        # the section tangent (b, z) = (-nz, nb), + offset
        D = np.stack([np.cos(th), np.sin(th)], -1)
        M = np.stack([mb, mz], -1)
        P = M[:, None, :] + (t[None, :, None] - 0.5) * L * D[:, None, :]
        zs, d = door.surf_coords(P[..., 0], P[..., 1])
        top = LINING_D + door.frame_h(zs)
        m = np.minimum.reduce([d - R, top - d - R, zs - zlo - R, zhi - zs - R]).min(1)
        # turning centre stowed -> deployed
        Sp, Sq = _yz(door, M - 0.5 * L * D), _yz(door, M + 0.5 * L * D)
        u, v = Sq - Sp, Yq - Yp
        a = np.arctan2(u[:, 0] * v[1] - u[:, 1] * v[0], u[:, 0] * v[0] + u[:, 1] * v[1])
        ca, sa = np.cos(a), np.sin(a)
        rhs = Yp[None, :] - np.stack([ca * Sp[:, 0] - sa * Sp[:, 1], sa * Sp[:, 0] + ca * Sp[:, 1]], -1)
        det = (1 - ca) ** 2 + sa ** 2
        c = np.stack([((1 - ca) * rhs[:, 0] - sa * rhs[:, 1]) / np.maximum(det, 1e-12),
                      (sa * rhs[:, 0] + (1 - ca) * rhs[:, 1]) / np.maximum(det, 1e-12)], -1)
        dist = np.zeros(len(m)) if pref is None else np.linalg.norm(c - pref, axis=1)
        J = np.where(m >= need, np.minimum(m, 0.004) - 0.01 * dist, -1.0 + m)
        return J, m, M, D

    g = np.meshgrid(np.linspace(zlo + 0.1, zhi - 0.1, 40), np.linspace(0.02, 0.13, 12),
                    np.radians(np.r_[np.arange(-25, 26, 2.5), 180 + np.arange(-25, 26, 2.5)]), indexing="ij")
    J, m, M, D = evaluate(*g)
    k = int(np.argmax(J))
    zc, dep, da = (v.ravel()[k] for v in g)
    for span in ((0.03, 0.012, np.radians(3.0)), (0.006, 0.003, np.radians(0.6))):
        g = np.meshgrid(zc + np.linspace(-span[0], span[0], 9), dep + np.linspace(-span[1], span[1], 9),
                        da + np.linspace(-span[2], span[2], 9), indexing="ij")
        J2, m2, M2, D2 = evaluate(*g)
        k2 = int(np.argmax(J2))
        if J2[k2] >= J[k]:
            J, m, M, D, k = J2, m2, M2, D2, k2
            zc, dep, da = (v.ravel()[k] for v in g)
    best, mid, dirv = float(m[k]), M[k], D[k]
    if best < 0.0:
        raise RuntimeError(f"airstair: a handrail piece does not stow inside the door body ({best * 1000:.1f} mm)")
    ps, qs = mid - 0.5 * L * dirv, mid + 0.5 * L * dirv
    Sp, Sq = _yz(door, ps), _yz(door, qs)
    a = _angle_x(Sq - Sp, Yq - Yp)
    ca, sa = np.cos(a), np.sin(a)
    Rm = np.array([[ca, -sa], [sa, ca]])
    c = np.linalg.solve(np.eye(2) - Rm, Yp - Rm @ Sp)
    assert np.allclose(_rot_yz(Sq, c, a), Yq, atol=1e-6)
    return dict(pivot=c, open=a, seg=(ps, qs), margin=best)


_LAYOUT = {}


def rail_layout(door):
    """Deployed and built (folded / stowed) handrail geometry, closed-pose door frame (b, z), and the fold pivots
    (model y, z centres; angle about +x built -> deployed)."""
    key = tuple(sorted((k, v) for k, v in door.o.items() if not isinstance(v, (dict, list))))
    if key in _LAYOUT:
        return _LAYOUT[key]
    rp = rail_points(door)
    Bd, Kd, Ad, Csd, Cjd = (np.array(door.closed_bz(*rp[k])) for k in ("B", "K", "A", "Cs", "Cj"))
    Kf, beta = _fold_lower(door, Bd, Kd)
    lo = dict(pivot=_yz(door, Bd), open=beta, seg=(Bd, Kf), deployed=(Bd, Kd))
    up = _stow(door, Kd, Ad, 0.92 * RAIL["r"], RAIL["r"] + 0.004, prefer=Bd)
    # unfold the long way round (|open| > 180 deg): the short way swept the rod ends through the lower fuselage, the
    # belly fairing, the sill and the cabin floor edge (review r1 M1); this way the arc stays outboard of the skin
    up["open"] = float(up["open"] - 2.0 * np.pi * np.sign(up["open"]))
    up["deployed"] = (Kd, Ad)
    cab = _stow(door, Cjd, Csd, CABLE["r"], CABLE["r"] + 0.004, prefer=Csd)
    cab["deployed"] = (Cjd, Csd)
    _LAYOUT[key] = out = dict(points=rp, lo=lo, up=up, cab=cab)
    return out


def _bracket(door, x, bz, r):
    """Jamb fitting at the fuselage end of a rail / cable: an eye on the rod line bridged to the jamb face (the clear
    opening's fwd / aft edge), built at the rod's (deployed / stowed) position."""
    o = door.o
    xj = o["cx"] - o["hx"] - 0.003 if x < o["cx"] else o["cx"] + o["hx"] + 0.003
    p = door.to3(0.0, bz[0], bz[1])
    x0, x1 = sorted((xj, x + np.sign(x - xj) * 0.012))
    return cylinder(p + [x0, 0, 0], p + [x1, 0, 0], r, n=16, cap=True)


def _eye(door, x, bz, r, half):
    """Joint fitting: a short cylinder along x at (b, z)."""
    p = door.to3(0.0, bz[0], bz[1])
    return cylinder(p + [x - half, 0, 0], p + [x + half, 0, 0], r, n=16, cap=True)


def _stanchion(door, x, zs):
    """Stanchion (door-carried): foot plate on the stringer top, tube up to the head clevis that carries the lower
    rod's pin: [(Mesh, mat)]."""
    hx, hl, hu = RAIL["lug"]
    b0, b1 = _post(door, zs)
    nb, nz = door.normal(zs)
    up = -door.to3(0.0, nb, nz)                              # off the stringer (closed pose: inboard)
    al = door.to3(0.0, -nz, nb)                              # along the stringer
    Rm = np.stack([[1.0, 0.0, 0.0], al / np.linalg.norm(al), up / np.linalg.norm(up)], 1)
    foot = superellipsoid(door.to3(x, *b0) + 0.004 * up, (hx, hl, hu), e=(0.3, 0.3), nu=10, nv=16, R=Rm)
    tube = cylinder(door.to3(x, *b0), door.to3(x, *b1) - 0.012 * up, RAIL["post_r"], n=16)
    head = superellipsoid(door.to3(x, *b1) - 0.004 * up, (0.022, 0.020, 0.020), e=(0.4, 0.4), nu=10, nv=16, R=Rm)
    return [(foot, MAT["fitting"]), (tube, MAT["rod"]), (head, MAT["fitting"])]


def rail_meshes(door):
    """Door-carried stanchions [(Mesh, mat)] and the three children's meshes in their built (folded / stowed) poses."""
    lay = rail_layout(door)
    lo, up, cab = lay["lo"], lay["up"], lay["cab"]
    r = RAIL["r"]
    posts, low, upp, cbl = [], [], [], []
    zsB = lay["points"]["zsB"]
    for x in door.frame_x():
        posts += _stanchion(door, x, zsB)
        B, K = lo["seg"]
        low.append((cylinder(door.to3(x, *B), door.to3(x, *K), r, n=16), MAT["rod"]))
        low.append((_eye(door, x, B, r + 0.002, 0.022), MAT["fitting"]))    # inside the clear opening (was 0.030:
        #                                                         2 mm past it, through the side jamb as the door opens)
        low.append((_eye(door, x, K, RAIL["knee_r"], 0.5 * RAIL["knee_l"]), MAT["fitting"]))
        Ks, As = up["seg"]
        upp.append((cylinder(door.to3(x, *Ks), door.to3(x, *As), 0.92 * r, n=16), MAT["rod"]))
        upp.append((_bracket(door, x, As, r + 0.004), MAT["fitting"]))
        Cj, Cs = cab["seg"]
        cbl.append((cylinder(door.to3(x, *Cj), door.to3(x, *Cs), CABLE["r"], n=8), MAT["cable"]))
        cbl.append((_bracket(door, x, Cj, CABLE["r"] + 0.004), MAT["fitting"]))
        cbl.append((_eye(door, x, Cs, CABLE["r"] + 0.004, 0.010), MAT["fitting"]))
    return posts, dict(door_airstair_rail=low, door_airstair_rail_up=upp, door_airstair_cable=cbl), lay


# ---------------------------------------------------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------------------------------------------------
CHILDREN = {   # id: (name, layout key, unfold window (door travel), material note)
    "door_airstair_rail": ("Airstair handrails: lower rods (fold down the door)", "lo", (0.40, 1.0),
                           "Polished stainless rods pinned to the stanchion heads, knee at hand height"),
    "door_airstair_rail_up": ("Airstair handrails: upper rods (stow in the door)", "up", (0.92, 1.0),
                              "Polished stainless rods, knee -> door-frame (jamb) fitting"),
    "door_airstair_cable": ("Airstair restraint cables (stow in the door)", "cab", (0.92, 1.0),
                            "Stainless cables, door-frame (jamb) -> upper stringers"),
}


def door_meshes(o, skin):
    """Everything of the door behind its outer skin, closed pose: [(Mesh, material)].  skin = the painted outer skin
    patch fuselage_parts.build_door cut along the panel seam (normals outward)."""
    from model.fuselage_parts import DOOR_T
    door = Door(o)
    flange, rim = _slab_back(skin, DOOR_T)
    out = [(rim, MAT["edge"]), (flange, MAT["flange"]), (_fasteners(skin, DOOR_T), MAT["fastener"])]
    out += inner_body(door)
    out += treads(door)
    out += inner_handle(door)
    posts, _, _ = rail_meshes(door)
    return out + posts


def build(part, o, skin):
    """fuselage_parts.build_door call site: add the door body, treads, handle and stanchions to the door part."""
    for m, mat in door_meshes(o, skin):
        part.add(m, mat)
    from model.fuselage_parts import DOOR_SILL_WL
    part.info["steps"] = (f"{N_RISERS - 2} treads + bottom step, {1000 * DOOR_SILL_WL / N_RISERS:.0f} mm risers "
                          f"(sill -> ground)")
    return part


def child_parts(o, parent="door_airstair"):
    """The folding handrail pieces as child parts of the door, built folded / stowed (pivot kind 'fold': rotate by
    open * smooth(window(door fraction)) about the x-parallel axis through origin, in the door's frame)."""
    door = Door(o)
    _, meshes, lay = rail_meshes(door)
    out = []
    for pid, (name, key, win, note) in CHILDREN.items():
        c = lay[key]["pivot"]
        a = float(lay[key]["open"])
        pv = dict(origin=(float(door.cx), float(c[0]), float(c[1])), axis=(1, 0, 0), kind="fold", open=a,
                  open_deg=float(np.degrees(a)), follows=parent, window=[float(win[0]), float(win[1])])
        p = Part(pid, name, "doors", parent=parent, pivot=pv, group="Doors", qty=2, material_note=note,
                 info={"unfolds": f"{np.degrees(a):+.1f} deg about x over door travel {win[0]:.2f}-{win[1]:.2f}"})
        for m, mat in meshes[pid]:
            p.add(m, mat)
        out.append(p)
    return out


def fold_fraction(pivot, door_frac):
    """A child's unfold fraction at door fraction door_frac: clamp((f - w0) / (w1 - w0), 0, 1) over its window."""
    w0, w1 = pivot["window"]
    return float(np.clip((door_frac - w0) / (w1 - w0), 0.0, 1.0))


def posed(part, door_frac=1.0):
    """Model-axes meshes [(Mesh, mat)] of the door or one of its children at door fraction door_frac (door at
    open * f, a child at open * fold_fraction(f)), for previews and checks."""
    from model.fuselage_parts import AIRSTAIR, door_pivot
    pv = door_pivot(AIRSTAIR)
    M = rotation_about(pv["axis"], pv["open"] * door_frac, pv["origin"])
    if part.pivot and part.pivot.get("kind") == "fold":
        cp = part.pivot
        M = M @ rotation_about(cp["axis"], cp["open"] * fold_fraction(cp, door_frac), cp["origin"])
    return [(m.transformed(M), mat) for m, mat in part.meshes]
