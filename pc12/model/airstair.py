"""
Airstair passenger door D1 (port, bottom-hinged): the door behind its outer skin -- edge, inner body, the integral
steps and the handrails (Stage 3).

The door keeps everything fuselage_parts defines for it: the clear opening AIRSTAIR, the panel seam DOOR_PANELS,
hinge_line / door_pivot (axis, origin, open 145 deg) and the slab DOOR_T.  fuselage_parts.build_door cuts the painted
outer skin along the panel seam (unchanged) and calls build() here for the rest.  Like every part the geometry is
built in the door's CLOSED pose (model axes); the treads are laid out in the OPEN pose, where they are horizontal, and
rotated back about the hinge.  Above the lining panel everything stays inside the clear opening (INSET), clear of the
door stops and the 60 mm jambs.

Reference (refs/cache, not in git): MSN 3008 handover photos 130 / 188 (door open: grey bolted edge band, white
inner face and side stringers, three grey tread trays with dark tops, the bottom step at the free edge, a red inner
handle below the third tray, a polished two-link handrail from a stanchion on the FORWARD stringer to a fitting on
the jamb (final judge r1 S1: the aft stringer has none),
thin restraint cables), NGX s/n 2281 cabin photo (door closed: the dark bottom-step tray at the top, the red lever
below it, a polished rod folded down the door), POH 'integral steps'.  The rail joints were measured on photos 130 /
188 with their fitted cameras (rays through the stringer plane).  The door opens 145 deg (the free edge on the
145 deg line in both photos; it was 160, free edge on the ground): open, the free edge stands ~0.29 m off the ground,
so the bottom step sits at the free edge and the treads divide sill -> bottom step into equal risers.  Source tags:
[S] sourced, [M] measured / proportioned on those photos, [E] estimated, [D] derived from the approved parameters.  No
drawing or interior table carries a step pitch [D].

Door part (rigid, pivot unchanged): edge band + fasteners, flange, lining panel, perimeter frame (side stringers),
treads + pads, bottom step, inner handle, the stanchion (forward stringer, RAIL sides) and the cable clamps.  The
handrail and the restraint cables are pinned at both ends through the whole swing (owner 2026-10-04: stowed inside the
door slab, the upper rod and the cables had turned up to 189 deg about mid-air centres over the last 8 % of the travel
-- "the handrail floats in from the sky"; the NGX s/n 2281 closed-door cabin photo shows the rails folded along the
door's forward edge, a fitting at the jamb):
  door_airstair_rail         lower rod + knee clevis, pinned to the stanchion head B (the door's child, pivot kind
                             'fold'): folded down the door, it rises to the knee at hand height over RAIL 'fold'
  door_airstair_rail_up      upper telescoping rod (the lower rod's child, kind 'stretch': turn + scale along its axis
                             about the knee), always ending on the jamb pivot A
  door_airstair_rail_sleeve  its sleeve on the jamb bracket's pin (a fuselage part, kind 'fold' with an angle table,
                             'follows' the door), always pointing at the knee
  door_airstair_cable        restraint cables from the door clamps to the jamb fittings (the door's child, 'stretch'):
                             straight between the two at every door angle, paying out of the jamb fittings
The jamb bracket, its pivot pin and the cables' jamb fittings are fixed (door_frames, jamb_fittings()).  child_matrix /
posed_matrix pose any of them at a door fraction as the viewer does; 'curve' / 'scale' tables hold the angles / length
factors at N_MOTION + 1 even steps of the door fraction.  The deployed pose is the photo-measured one (B, K, A on the
forward stringer / jamb; A now on the jamb's inner edge, RAIL A_depth).
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
N_RISERS = 5           # [D] sill (cabin floor WL) -> bottom step in N_RISERS - 1 equal risers: 3 treads + the
#                        bottom step at the free edge (photo 188: three grey trays, then the foot area), then the
#                        last (taller) step to the ground (door open 145 deg: ~210 mm risers, the bottom step ~0.42
#                        m up; at the old 160 deg the rule gave sill -> ground in 251 mm risers)
TREAD = dict(depth=0.160,    # [M] tray depth (horizontal, open)
             t=0.012,        # [M] thin grey metal plate (photos 188 / 130: grating plates on open brackets, the white
             #                 inner face showing between them; review r2 F6: 20 mm trays on 45 mm white risers read as a
             #                 solid moulded stair)
             lip=0.012,      # [M] front edge = the plate (no riser)
             nose_r=0.004,   # [E] rounded nosing
             bracket=(0.006, 0.090),   # [E] open side brackets under each plate: thickness, drop along the wall
             embed=0.012,    # [E] into the lining panel
             gap=0.002,      # [E] to the stringer walls
             pad=(0.022, 0.022, 0.020, 0.0022),   # [E] anti-slip pad inset back / front / sides, thickness
             shadow=(0.075, 0.0012, 0.003))   # [M] dark recess under each plate: height down the wall, off it, thick
FOOT = dict(depth=0.215, lip=0.012)   # [M] bottom step at the free edge (foot, photo 188: the step he stands on)
RAIL = dict(r=0.0100,        # [M] polished rods ~20-25 mm (photos 130 / 188, against the 22x8.50 tyre scale); 20 mm
            #                  so the lower rod and the upper rail lie side by side over the 40 mm stringer (the knee
            #                  clevis), between the restraint cable in the jamb gap and the treads (handrail fix
            #                  2026-10-04; it was 25 mm, one rod plane)
            r_up=0.0080,     # [E] upper rail: the polished telescoping rod (slides in the sleeve at the jamb pivot)
            sleeve=(0.0100, 0.30),   # [E] its sleeve: radius, length from the jamb pivot toward the knee
            dx=(+0.0105, -0.0100),   # [D] rod planes about the forward stringer's centre line: the lower rod over its
            #                          aft half (1.5 mm clear of the treads), the upper rail over its forward half (1 mm
            #                          clear of the restraint cable in the 8 mm jamb gap)
            fold=(0.40, 1.00),       # [E] door travel over which the lower rod rises from the stair to the knee
            post_wl=0.70,    # [M] stanchion foot on the stringer at open WL 0.70, between treads 2 and 3: the lower
            #                  rod's end in photos 130 / 188 (pixels 1274,836 / 1069,869) through the fitted cameras,
            #                  door at 145 deg (it was 0.56 with a 130 mm post on the 160 deg door)
            post=0.030,      # [M] a short clevis post: at 145 deg the rod ends lie AT the stringer top (the rays put
            #                  the pin 0-60 mm below it, 17-26 px rms for posts 0-40 mm); 30 mm keeps the eye clear
            post_r=0.009,    # [E] stanchion tube radius (under the lower rod's plane)
            K=(1.59, 1.24),  # [M] knee (BL, WL) in the open pose: photos 130 / 188, rays through the stringer plane
            #                  gave BL 1.58-1.60, WL 1.23-1.29 (the hand grips just above the joint)
            A_wl=1.97,       # [M] jamb fitting WL (photos 188 / 130: WL 2.02 / 1.91 on the fwd jamb)
            A_depth=0.160,   # [E] the upper rail's pivot on a bracket at the fwd jamb's inner edge (jamb: 49-109 mm
            #                  inside the skin), 10 mm over the folded rail on the stringer top: the rail stays pinned
            #                  there through the whole swing (at 0.065, in the jamb face, it lay inside the closed door)
            knee_r=0.016,    # [E] knee clevis (spans both rod planes) / eye fittings
            lug=(0.010, 0.032, 0.012),    # [E] stanchion foot half sizes (x, along, up)
            sides=("fwd",))  # [M] final judge r1 S1: the two-link rail is on the FORWARD stringer only -- both
#                              rails projected through the fitted cameras (livery cams.json port_hangar_130,
#                              vqa/cams_beauty.json nose_188): the forward one lies on the photos' long upper rod and
#                              lower rod (knee at the hand), the aft one on nothing (its upper rod read as a doubled
#                              rail); the aft side carries the restraint cable only (and an unmodelled short strut from
#                              the jamb foot, out/tmp/fix_r1/railproj_*.png)
CABLE = dict(r=0.0030,       # [M] thin restraint cables (photos 188 / 130: thin lines jamb -> stringers)
             C_wl=1.75,      # [M] upper end on the jamb (photo 188: WL 1.75)
             z_low=0.80,     # [M] lower end on the stringer at open WL 0.80, between treads 2 and 3 (photo 188;
             #                 the same place on the door as the 160 deg layout's WL 0.71)
             depth=0.065,    # [E] its jamb fitting in the jamb face (jamb: 49-109 mm inside the skin)
             pin=0.008,      # [E] its clamp pin 8 mm inside the stringer top
             gap=0.004)      # [D] cable plane 4 mm inside the opening edge: in the 8 mm gap between the jamb and the
#                              door's inner body (INSET), so it pays out of the jamb fitting through the whole swing
#                              without touching either
HANDLE = dict(zs=2.31,       # [M] inner door handle between tread 3 and the bottom step (photo 188: red lever there;
              #                  NGX cabin photo: red lever just below the top tray of the closed door)
              x=(4.80, 5.06),  # [E] lever span (station), hub at the aft end
              w=0.034, t=0.018, off=0.024, tilt=12.0, hub_r=0.024)   # [E] section, off the panel, twist (deg)
FASTENERS = dict(pitch=0.065, r=0.0042, h=0.0015)   # [M] fastener row on the grey edge band (photos 130 / 188)
# model judging r1 GR1-06 (photos 130 / 188): the curved door rim is a darker riveted metal band (edge metal_dark with
# steel_dark fasteners; it had read light grey), and every tread throws a dark cavity onto the inner face below it
# (TREAD 'shadow': a dark recess panel under each plate between its brackets)
MAT = dict(edge="metal_dark", flange="metal", body="lining", frame="lining", tread="metal", bracket="metal",
           antislip="metal_dark", rod="chrome", fitting="steel", cable="steel", handle="prop_band_red",
           fastener="steel_dark", shadow="vent_dark")


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
        """Open-pose tread top water lines, top (sill) down: N_RISERS - 1 levels (the last = the bottom step).  The
        bottom step sits at the free edge: its top where the open inner face lies FOOT depth (+ 4 mm) inside the free
        edge's inner end, so the full-depth step ends flush with it; the treads divide sill -> bottom step into equal
        risers [D] (at 160 deg this rule gives 0.27 for the old sill -> ground 0.251)."""
        from model.fuselage_parts import DOOR_SILL_WL
        wb, wz = self.wall()
        k0 = int(np.argmin(wz))
        target = float(wb[k0]) - 0.004 - FOOT["depth"]
        s = np.argsort(wb)                                   # b(z) is monotonic over the open inner face
        z_foot = float(np.interp(target, wb[s], wz[s]))
        n = N_RISERS - 1
        return [DOOR_SILL_WL - (DOOR_SILL_WL - z_foot) * k / n for k in range(1, n + 1)]


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
    # final judge r1 S3: the outer wall is part of the grey bolted edge band seen from the side (photos 130 / 188: a
    # thin metal rim, the white stringers set inside it), not white lining -- the side face had read as a thick slab;
    # A1: the frame's top band too (the photos' bright metal rim round the door, the white lining inside it)
    return [(panel, MAT["body"]), (top, MAT["edge"]), (wo, MAT["edge"]), (wi, MAT["frame"])]


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
        a = np.linspace(0.5 * np.pi, 0.0, 4)[1:]
        nose = [(bf - rn + rn * np.cos(t), zk - rn + rn * np.sin(t)) for t in a]
        lipb = (bf, zk - lip)
        # underside: a plain plate, flat back to the (embedded) wall (review r2 F6: no riser / wedge under it)
        q = _hit_wall(np.array([bf - 0.002, zk - TREAD["t"]]), np.array([-1.0, 0.0]), wb, wz, em)
        zw = np.linspace(q[1], zk, 4)[1:-1]
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
        # open brackets: a thin gusset under each end of the plate, down the inner face (photos 188 / 130)
        bt, bd = TREAD["bracket"]
        zk, bw_, bf_ = tp["z"], tp["b_back"], tp["b_front"]
        wb_, wz_ = door.wall()
        zlo = zk - TREAD["t"] - bd
        G = np.array([(bw_ - TREAD["embed"], zk - TREAD["t"] + 0.001), (bw_ + 0.6 * (bf_ - bw_), zk - TREAD["t"] + 0.001),
                      (float(np.interp(zlo, wz_, wb_)) - TREAD["embed"], zlo)])
        gb, gz = door.closed_bz(G[:, 0], G[:, 1])
        for x0g in (xa + 0.002, xb - 0.002 - bt):
            out += _extrude(np.c_[gb, gz], x0g, x0g + bt, door, [(0, 3, False, MAT["bracket"])], MAT["bracket"])
        # dark recess panel on the inner face under the plate, between its brackets (photos 130 / 188: a shadowed
        # cavity under every tread; model judging r1 GR1-06)
        if not tp["foot"]:
            sh, so, st = TREAD["shadow"]
            zt_, zb_ = zk - TREAD["t"] - 0.0015, zk - TREAD["t"] - sh
            wt, wbm = float(np.interp(zt_, wz_, wb_)), float(np.interp(zb_, wz_, wb_))
            S_ = np.array([(wt + so, zt_), (wt + so + st, zt_), (wbm + so + st, zb_), (wbm + so, zb_)])
            sb, sz = door.closed_bz(S_[:, 0], S_[:, 1])
            out += _extrude(np.c_[sb, sz], xa + bt + 0.003, xb - bt - 0.003, door, [(0, 4, False, MAT["shadow"])],
                            MAT["shadow"])
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
    Cj = np.array(door.bz(CABLE["C_wl"], CABLE["depth"]), float)
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


# The handrail mechanism (owner 2026-10-04: in the viewer the upper rod and the cables had flown in "from the sky" --
# stowed inside the door slab they turned up to 189 deg about mid-air centres over the last 8 % of the swing).  Now
# every piece is pinned at both ends through the whole swing (the NGX s/n 2281 closed-door cabin photo: the rails lie
# folded along the door's forward edge, a fitting at the jamb):
#   lower rod       pinned at the stanchion head B on the door; folded down the door, it rises to the knee about B
#                   over RAIL 'fold' (pivot kind 'fold', the door's child)
#   upper rail      a telescoping rod pinned at the knee (the lower rod's child) and sliding in a sleeve that pivots on
#                   the jamb bracket A: the rod (kind 'stretch': turn + scale along its axis about the knee) always
#                   ends at A, the sleeve (kind 'fold' with an angle table, a fuselage part) always points at the knee
#   restraint cable from the door clamp Cs to the jamb fitting Cj, paying out of the jamb fitting (kind 'stretch', the
#                   door's child): straight between the two at every door angle, taut at full travel
# A 'curve' / 'scale' table holds the angle (rad about the pivot axis) / the length factor at N_MOTION + 1 even steps
# of the door fraction (door angle / its open angle, as the viewer eases it); viewers interpolate linearly.
N_MOTION = 200


def _door_frame(door, P, f):
    """World (b, z) points -> the door's closed-pose frame at door fraction f (the door turned open * f); f < 0 maps
    door-frame points back to the world."""
    c = np.array([door.side * door.pv["origin"][1], door.pv["origin"][2]])    # hinge (b, z)
    return _turn_bz(door, P, c, -door.pv["open"] * f)


def _turn_bz(door, P, c, a):
    """Rotate (b, z) points about centre c by a (model angle about +x)."""
    q = _rot_yz(_yz(door, P), _yz(door, c), a)
    return np.stack([door.side * q[..., 0], q[..., 1]], -1)


def _ang_bz(door, u, v):
    """Model angle about +x from (b, z) direction u to v."""
    return _angle_x(_yz(door, u), _yz(door, v))


def fold_window(f, w):
    """Unfold fraction over a door-travel window w = (w0, w1)."""
    return float(np.clip((f - w[0]) / max(w[1] - w[0], 1e-9), 0.0, 1.0))


_LAYOUT = {}


def rail_layout(door):
    """Handrail geometry in the door's closed-pose frame (b, z) and its motion tables.  points: the open-pose joints
    (B stanchion head, K knee, A jamb pivot, Cs cable clamp, Cj cable jamb end); lo / up / sleeve / cab: pivot (b, z),
    built segment, tables."""
    key = tuple(sorted((k, v) for k, v in door.o.items() if not isinstance(v, (dict, list))))
    if key in _LAYOUT:
        return _LAYOUT[key]
    rp = rail_points(door)
    Bd, Kd = (np.array(door.closed_bz(*rp[k])) for k in ("B", "K"))
    A, Cj = np.array(rp["A"]), np.array(rp["Cj"])                      # fuselage-fixed (world = closed frame)
    Csd = np.array(door.closed_bz(*rp["Cs"]))
    Kf, beta = _fold_lower(door, Bd, Kd)
    F_ = np.linspace(0.0, 1.0, N_MOTION + 1)
    w = RAIL["fold"]
    lo_ang = np.array([beta * fold_window(f, w) for f in F_])
    up_ang, up_scl, sl_ang, cb_ang, cb_scl, knee_w = [], [], [], [], [], []
    u0, s0, c0 = A - Kf, Kf - A, Cj - Csd
    for f, a_lo in zip(F_, lo_ang):
        Ad = _door_frame(door, A, f)                                    # the jamb pivot in the door's frame
        Al = _turn_bz(door, Ad, Bd, -a_lo)                              # ... and in the lower rod's frame
        up_ang.append(_ang_bz(door, u0, Al - Kf))
        up_scl.append(np.linalg.norm(Al - Kf) / np.linalg.norm(u0))
        Kw = _door_frame(door, _turn_bz(door, Kf, Bd, a_lo), -f)       # the knee in the world
        knee_w.append(Kw)
        sl_ang.append(_ang_bz(door, s0, Kw - A))
        Cjd = _door_frame(door, Cj, f)
        cb_ang.append(_ang_bz(door, c0, Cjd - Csd))
        cb_scl.append(np.linalg.norm(Cjd - Csd) / np.linalg.norm(c0))
    unw = lambda a: np.unwrap(np.asarray(a, float))                    # noqa: E731
    lo = dict(pivot=Bd, seg=(Bd, Kf), deployed=(Bd, Kd), open=beta, curve=lo_ang)
    up = dict(pivot=Kf, seg=(Kf, A), deployed=(Kd, A), curve=unw(up_ang), scale=np.asarray(up_scl),
              length=np.linalg.norm(u0) * np.asarray(up_scl))
    sleeve = dict(pivot=A, seg=(A, A + RAIL["sleeve"][1] * s0 / np.linalg.norm(s0)), curve=unw(sl_ang),
                  knee=np.asarray(knee_w))
    cab = dict(pivot=Csd, seg=(Csd, Cj), deployed=(np.array(door.closed_bz(*rp["Cs"])), Cj), curve=unw(cb_ang),
               scale=np.asarray(cb_scl))
    if up["length"].min() < RAIL["sleeve"][1] + 0.08:
        raise RuntimeError(f"airstair: the upper rail closes to {up['length'].min():.3f} m, inside its sleeve")
    _LAYOUT[key] = out = dict(points=rp, lo=lo, up=up, sleeve=sleeve, cab=cab, f=F_)
    return out


def rail_x(door):
    """Station planes: lower rod, upper rail (forward stringer), restraint cables (fwd, aft: in the jamb gaps)."""
    xf = door.frame_x()[0]
    o = door.o
    return dict(lo=xf + RAIL["dx"][0], up=xf + RAIL["dx"][1],
                cab=(o["cx"] - o["hx"] + CABLE["gap"], o["cx"] + o["hx"] - CABLE["gap"]),
                jamb=(o["cx"] - o["hx"], o["cx"] + o["hx"]))


def _xcyl(door, x0, x1, bz, r, n=16):
    """Short cylinder along x over [x0, x1] at (b, z)."""
    p = door.to3(0.0, bz[0], bz[1])
    return cylinder(p + [x0, 0, 0], p + [x1, 0, 0], r, n=n, cap=True)


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
    head = superellipsoid(door.to3(x, *b1) - 0.004 * up, (0.0095, 0.020, 0.020), e=(0.4, 0.4), nu=10, nv=16, R=Rm)
    return [(foot, MAT["fitting"]), (tube, MAT["rod"]), (head, MAT["fitting"])]


def rail_meshes(door):
    """Door-carried pieces [(Mesh, mat)] (stanchion, cable clamps), the fuselage-fixed jamb fittings [(Mesh, mat)] and
    the moving parts' meshes {part id: [(Mesh, mat)]}, all in their built poses (door closed)."""
    lay = rail_layout(door)
    lo, up, sl, cab = lay["lo"], lay["up"], lay["sleeve"], lay["cab"]
    X = rail_x(door)
    r, ru = RAIL["r"], RAIL["r_up"]
    rs, ls = RAIL["sleeve"]
    door_pcs, jamb, low, upp, slv, cbl = [], [], [], [], [], []
    # restraint cables on both sides: built door closed, Cs (door clamp) -> Cj (jamb fitting), in the jamb gap
    Cs, Cj = cab["seg"]
    for xc, xj in zip(X["cab"], X["jamb"]):
        s = np.sign(xc - xj)                                            # into the opening
        cbl.append((cylinder(door.to3(xc, *Cs), door.to3(xc, *Cj), CABLE["r"], n=8), MAT["cable"]))
        x_str = xj + s * (INSET + 0.005)                                # 5 mm into the stringer's outer face
        door_pcs.append((_xcyl(door, *sorted((xc - s * 0.003, x_str)), Cs, CABLE["r"] + 0.003), MAT["fitting"]))
        jamb.append((_xcyl(door, *sorted((xj - s * 0.006, xj + s * 0.0005)), Cj, CABLE["r"] + 0.005),
                     MAT["fitting"]))
    # the two-link rail on the forward stringer
    xl, xu, xj = X["lo"], X["up"], X["jamb"][0]
    door_pcs += _stanchion(door, xl, lay["points"]["zsB"])
    B, Kf = lo["seg"]
    low.append((cylinder(door.to3(xl, *B), door.to3(xl, *Kf), r, n=16), MAT["rod"]))
    low.append((_xcyl(door, xl - r, xl + r, B, r + 0.002), MAT["fitting"]))              # pin eye at the stanchion
    low.append((_xcyl(door, xu - ru - 0.0015, xl + r, Kf, RAIL["knee_r"]), MAT["fitting"]))   # knee clevis
    A = up["seg"][1]
    upp.append((cylinder(door.to3(xu, *Kf), door.to3(xu, *A), ru, n=16), MAT["rod"]))
    s0, s1 = sl["seg"]
    slv.append((cylinder(door.to3(xu, *s0), door.to3(xu, *s1), rs, n=16), MAT["rod"]))
    slv.append((_xcyl(door, xj + 0.0075, xu + rs, s0, rs + 0.003), MAT["fitting"]))      # pivot eye at the jamb
    d = (s1 - s0) / np.linalg.norm(s1 - s0)
    slv.append((cylinder(door.to3(xu, *(s1 - 0.012 * d)), door.to3(xu, *s1), rs + 0.0012, n=16, cap=True),
                MAT["fitting"]))                                                         # gland at the sleeve mouth
    # jamb bracket: a plate on the forward jamb's inner edge carrying the sleeve's pivot pin
    jamb.append((_bracket_plate(door, xj, A), MAT["fitting"]))
    jamb.append((_xcyl(door, xj - 0.004, xj + 0.007, A, 0.006), MAT["fitting"]))         # pivot pin
    return door_pcs, jamb, dict(door_airstair_rail=low, door_airstair_rail_up=upp,
                                door_airstair_rail_sleeve=slv, door_airstair_cable=cbl), lay


def _bracket_plate(door, xj, A):
    """Jamb bracket: a 6.5 mm plate just forward of the opening edge (x <= xj - 1.5 mm, clear of the closed door and
    the cable gap), from inside the jamb (depth 90 mm) out past the pivot A, 56 mm high, rounded."""
    zs, dA = (float(v) for v in door.surf_coords(*A))
    d0, d1 = 0.090, dA + 0.018
    nb, nz = door.normal(zs)
    inw = -door.to3(0.0, nb, nz)                             # inward normal (model)
    al = door.to3(0.0, -nz, nb)                              # along the section
    R = np.stack([[1.0, 0.0, 0.0], inw / np.linalg.norm(inw), al / np.linalg.norm(al)], 1)
    t = 0.0065
    c = door.to3(xj - 0.0015 - 0.5 * t, *door.bz(zs, 0.5 * (d0 + d1)))
    return superellipsoid(c, (0.5 * t, 0.5 * (d1 - d0), 0.028), e=(0.25, 0.5), nu=12, nv=20, R=R)


# ---------------------------------------------------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------------------------------------------------
CHILDREN = {   # id: (name, parent (None: the door part), material note)
    "door_airstair_rail": ("Airstair handrail: lower rod (folds down the door)", None,
                           "Polished stainless rod pinned to the stanchion head, knee clevis at hand height"),
    "door_airstair_rail_up": ("Airstair handrail: upper telescoping rod", "door_airstair_rail",
                              "Polished stainless rod, knee -> sleeve on the jamb bracket"),
    "door_airstair_cable": ("Airstair restraint cables (pay out of the jamb fittings)", None,
                            "Stainless cables, door clamps -> jamb fittings"),
}
SLEEVE_ID = "door_airstair_rail_sleeve"


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
    door_pcs, _, _, _ = rail_meshes(door)
    return out + door_pcs


def jamb_fittings(o):
    """The handrail's fuselage-fixed fittings (jamb bracket + the sleeve's pivot pin, the cables' jamb fittings):
    [(Mesh, material)], added to door_frames by fuselage_parts.build_doors."""
    _, jamb, _, _ = rail_meshes(Door(o))
    return jamb


def build(part, o, skin):
    """fuselage_parts.build_door call site: add the door body, treads, handle and stanchions to the door part."""
    for m, mat in door_meshes(o, skin):
        part.add(m, mat)
    from model.fuselage_parts import DOOR_SILL_WL
    lv = Door(o).levels()
    part.info["steps"] = (f"{N_RISERS - 2} treads + bottom step, {1000 * (DOOR_SILL_WL - lv[0]):.0f} mm risers "
                          f"(sill -> bottom step at WL {1000 * lv[-1]:.0f}, then to the ground)")
    return part


def _tab(a, nd=6):
    return [round(float(v), nd) for v in a]


def child_parts(o, parent="door_airstair"):
    """The moving handrail pieces, built door closed (rails folded down the door): the lower rod (the door's child,
    pivot kind 'fold': open x window(door fraction) about the x-parallel axis through B), the upper telescoping rod (the
    lower rod's child, kind 'stretch'), the restraint cables (the door's child, 'stretch') and the upper rail's sleeve
    (a fuselage part pivoting on the jamb bracket, 'fold' with an angle table).  'stretch': turn by curve(f) about the
    axis through origin, then scale by scale(f) along dir (the built unit direction) about origin, in the parent's
    frame; 'curve' / 'scale' are sampled at N_MOTION + 1 even steps of the door fraction f.  'joints': model points of
    the built pose that a viewer test can follow (the pinned ends)."""
    door = Door(o)
    _, _, meshes, lay = rail_meshes(door)
    X = rail_x(door)
    lo, up, sl, cab = lay["lo"], lay["up"], lay["sleeve"], lay["cab"]

    def P3(x, bz):
        return [float(v) for v in door.to3(x, *bz)]

    def unit(a, b):
        d = door.to3(0.0, *b) - door.to3(0.0, *a)
        return [float(v) for v in d / np.linalg.norm(d)]
    w = RAIL["fold"]
    A, Cj = up["seg"][1], cab["seg"][1]
    specs = {
        "door_airstair_rail": (parent, dict(origin=P3(door.cx, lo["pivot"]), axis=(1, 0, 0), kind="fold",
                                            open=float(lo["open"]), open_deg=float(np.degrees(lo["open"])),
                                            follows=parent, window=[float(w[0]), float(w[1])],
                                            joints=dict(B=P3(X["lo"], lo["seg"][0]), K=P3(X["lo"], lo["seg"][1]))),
                               f"rises {np.degrees(lo['open']):+.1f} deg about the stanchion pin over door travel "
                               f"{w[0]:.2f}-{w[1]:.2f}"),
        "door_airstair_rail_up": ("door_airstair_rail",
                                  dict(origin=P3(X["up"], up["pivot"]), axis=(1, 0, 0), kind="stretch",
                                       follows=parent, dir=unit(*up["seg"]), curve=_tab(up["curve"]),
                                       scale=_tab(up["scale"]), window=[0.0, 1.0],
                                       joints=dict(K=P3(X["up"], up["seg"][0]), A=P3(X["up"], A))),
                                  f"telescopes {up['length'].min():.3f}-{up['length'].max():.3f} m between the knee "
                                  f"and the jamb pivot"),
        "door_airstair_cable": (parent, dict(origin=P3(door.cx, cab["pivot"]), axis=(1, 0, 0), kind="stretch",
                                             follows=parent, dir=unit(*cab["seg"]), curve=_tab(cab["curve"]),
                                             scale=_tab(cab["scale"]), window=[0.0, 1.0],
                                             joints=dict(Cs=P3(X["cab"][0], cab["seg"][0]),
                                                         Cj=P3(X["cab"][0], Cj))),
                                f"pays out {np.linalg.norm(cab['seg'][1] - cab['seg'][0]):.3f} -> "
                                f"{np.linalg.norm(cab['seg'][1] - cab['seg'][0]) * cab['scale'][-1]:.3f} m"),
        SLEEVE_ID: (None, dict(origin=P3(X["up"], A), axis=(1, 0, 0), kind="fold", follows=parent,
                               open=float(sl["curve"][-1]), curve=_tab(sl["curve"]), window=[0.0, 1.0],
                               joints=dict(A=P3(X["up"], A))),
                    f"turns {np.degrees(sl['curve'].min()):+.1f}..{np.degrees(sl['curve'].max()):+.1f} deg on the "
                    f"jamb bracket"),
    }
    names = dict(CHILDREN, **{SLEEVE_ID: ("Airstair handrail: upper rail sleeve (pivots on the jamb bracket)", None,
                                          "Polished stainless tube on the jamb bracket pin")})
    out = []
    for pid, (par, pv, info) in specs.items():
        name, _, note = names[pid]
        p = Part(pid, name, "doors", parent=par, pivot=pv, group="Doors", qty=2 if pid == "door_airstair_cable" else 1,
                 material_note=note, info={"motion": info})
        for m, mat in meshes[pid]:
            p.add(m, mat)
        out.append(p)
    return out


def _interp(tab, f):
    tab = np.asarray(tab, float)
    x = float(np.clip(f, 0.0, 1.0)) * (len(tab) - 1)
    i = min(int(np.floor(x)), len(tab) - 2)
    return float(tab[i] + (x - i) * (tab[i + 1] - tab[i]))


def child_matrix(pivot, f):
    """A moving handrail piece's own transform (model axes, in its parent's frame) at door fraction f: kinds 'fold'
    (curve, else open x window) and 'stretch' (turn + scale along dir about origin)."""
    o = np.asarray(pivot["origin"], float)
    if "curve" in pivot:
        a = _interp(pivot["curve"], f)
    else:
        a = pivot["open"] * fold_window(f, pivot.get("window", (0.0, 1.0)))
    M = rotation_about(pivot["axis"], a, o)
    if pivot.get("kind") == "stretch":
        d = np.asarray(pivot["dir"], float)
        S = np.eye(4)
        S[:3, :3] += (_interp(pivot["scale"], f) - 1.0) * np.outer(d, d)
        S[:3, 3] = o - S[:3, :3] @ o
        M = M @ S
    return M


def follows_door(part, parts, door_id="door_airstair"):
    """True for the parts the door's travel moves: the door's descendants and the parts that follow it."""
    q = part
    while q is not None:
        if q.id == door_id or (q.pivot and q.pivot.get("follows") == door_id):
            return True
        q = parts.get(q.parent) if q.parent else None
    return False


def posed_matrix(pid, parts, door_frac):
    """World transform (model axes) of a part moved by the door's travel at door fraction door_frac: the door's own
    turn for the door, then each moving piece's child_matrix down the parent chain."""
    p = parts[pid]
    pv = p.pivot or {}
    if pv.get("kind") == "door":
        M_own = rotation_about(pv["axis"], pv["open"] * door_frac, pv["origin"])
    elif pv.get("kind") in ("fold", "stretch"):
        M_own = child_matrix(pv, door_frac)
    else:
        M_own = np.eye(4)
    return (posed_matrix(p.parent, parts, door_frac) if p.parent else np.eye(4)) @ M_own


def posed(part, door_frac=1.0, parts=None):
    """Model-axes meshes [(Mesh, mat)] of the door or one of its moving pieces at door fraction door_frac, for previews
    and checks (parts: the part dict, for the pieces' parent chains)."""
    if parts is None:
        from model.fuselage_parts import AIRSTAIR
        parts = {p.id: p for p in child_parts(AIRSTAIR)}
        from model.fuselage_parts import door_pivot
        parts.setdefault("door_airstair", Part("door_airstair", "door", "doors", pivot=door_pivot(AIRSTAIR)))
    M = posed_matrix(part.id, dict(parts, **{part.id: part}), door_frac)
    return [(m.transformed(M), mat) for m, mat in part.meshes]
