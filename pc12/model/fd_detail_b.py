"""
Flight-deck detail, track B (flight deck r1 GEOM B, owner 2026-10-04: "the details are drastically missing"): the
SURROUND of the flight deck -- the moulded windshield / side-window reveals with their A-pillar, roof and centre-post
mouldings and the black seal at the glass, the padded leather sill under each side window with its stowage slot and
placards, the circuit-breaker panels, the overhead panel and its ceiling pod, the magnetic compass and grab handle on
the centre post, the side consoles / sidewall fittings, the divider's flight-deck face, the headliner fittings (dome
and map lights, speaker grilles, sun visors on rails).

The owned builders of model/flightdeck.py (_consoles, _overhead, _post_trim, _divider) and interior.build_lining call
the builders here.  Dimensions the sheets L6 / L6B draw come from the interior tables (SIDE_CONSOLE, OVERHEAD, LINING,
DIVIDER, CREW_SEAT); the sizes here are builder-level detail tagged [M] (measured on the git-ignored reference photos:
PRO s/n 3001 P1046406 / 08 / 09 / 10, the Pilatus PRO overhead / cockpit / simulator photos, the AOPA studio photos, the
NGX POH figures and panorama measurements in refs/cache/fd_research) or [E].

No markings: every legend is an abstract stroke, rectangle or pictogram (thin quads in the legend colours); no text,
no logos.  Pieces hung on interior_lining (CEILING_GROUPS, the glazing mouldings, the sill) are built with explicit
segment counts (res.coarse()): the light tier does not rebuild that part at RES 2, so both tiers carry the same pieces.
"""
from __future__ import annotations

import math

import numpy as np

from cad import res
from cad.mesh import Mesh, grid_surface, planar_cap
from model import fd_print as PR

# groups of model/flightdeck.build_flightdeck that flightdeck.build hangs on the interior_lining part (the viewer's
# cutaway clips them with the lining): the overhead panel and its pod, the CB panels, the sidewall sills, visors and the
# centre-post fittings
CEILING_GROUPS = ("overhead", "cb_panels", "pod", "sill", "visors", "post", "headliner_fd")

# The flight-deck shared materials (leather_black, stitch_thread, rubber_black, legend_*, annun_*) are
# model/assemble.MATERIALS' 'flight deck shared' block (render/lookdev.py SPEC the same).


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def _orient(m, ref_fn):
    """Flip m if its faces point (on average) against ref_fn(face centres) (a vector per face)."""
    if not len(m.F):
        return m
    fn = m.face_normals()
    C = m.V[m.F].mean(1)
    d = ref_fn(C) if callable(ref_fn) else np.broadcast_to(np.asarray(ref_fn, float), fn.shape)
    return m.flipped() if np.mean(np.sum(fn * d, 1)) < 0 else m


# =====================================================================================================================
# OML frames in the loft parameters (x, t): the lining (interior.build_lining) and the glass patches
# (fuselage_parts.build_glazing) are both built on them
# =====================================================================================================================
def oml_frame(x, t, e=1e-4):
    """OML point(s) P at the loft parameters (x, t), the unit 3-D outward normal N3 and the section-plane normal Nsec
    (x part dropped: the normal the lining is offset along, interior.build_lining), and the tangents dP/dx, dP/dt."""
    from model import fuselage as F
    x, t = np.broadcast_arrays(np.asarray(x, float), np.asarray(t, float))
    P = F.section(x, t % 1.0)
    Px = (F.section(x + e, t % 1.0) - F.section(x - e, t % 1.0)) / (2 * e)
    Pt = (F.section(x, (t + e) % 1.0) - F.section(x, (t - e) % 1.0)) / (2 * e)
    N3 = _unit(np.cross(Px, Pt))
    c = np.stack([x, np.zeros_like(x), F.z_mw(x)], -1)
    N3 = N3 * np.sign(np.sum(N3 * (P - c), -1))[..., None]
    Ns = np.stack([np.zeros_like(x), Pt[..., 2], -Pt[..., 1]], -1)
    Ns = _unit(Ns)
    Ns = Ns * np.sign(np.sum(Ns * (P - c), -1))[..., None]
    return P, N3, Ns, Px, Pt


def lining_depth(Ns):
    """The L6 LINING law's depth inside the OML for section normals Ns (interior.lining_offset)."""
    from model import interior as I
    return I.lining_offset(np.asarray(Ns)[..., 1])


# =====================================================================================================================
# B1 / B2  glazing mouldings: the reveal of every flight-deck pane is a moulded funnel from the lining hole (the pane's
# outline, as interior.build_lining cuts it) to the VISIBLE outline on the glass, which lies inside the pane by a margin
# per edge -- the PRO's broad A-pillars, roof and post mouldings and the oval side-window reveal (the trim hides the
# side window's aft ~0.17 and top ~0.08: NGX panorama S15, AOPA / P1046409 / 10) -- rolled tangent into the lining
# (R ~15 at the narrow edges) and ending in an 8 mm black seal lip 3-4 mm inboard of the glass.
# =====================================================================================================================
GLAZING_TRIM = dict(
    # windshield: margins (side projection, m) of the visible outline inside the pane along the sill / A-pillar / roof
    # edges and at the centre post (|BL|: the post moulding ~94 mm wide at the glass, P1046408 projected through the
    # fitted camera: 102 px at the glareshield, 126 px at the top = |BL| 0.044-0.047; the pillar edges overlaid on the
    # same photo: 2/3 of the way from the lining edge to rev 1's 40 mm, the fit carrying 30-50 px) [M]; radii [E]
    # (flight deck fix r2b: the sill margin 3 -> 34 mm -- through the lowest ~30 mm of the pane the crew eyes looked past
    #  the 9 mm deep seal under the retainer / mask skin's overlap onto the skin's inner face, a sunlit white rim line
    #  under the windshield from both seats; P1046409 / 10 show the hood meeting the glass in a dark line)
    # (flight deck fix r5 FDO4-02 / FID-FD4-02: the A-pillar edges 32 -> 8 mm here and 35 -> 6 mm on the side window's
    #  front edge -- the photo-fitted panel_408b camera puts P1046408's left post at 116 / 108 / 84 px (1920 px frame,
    #  rows 240 / 300 / 360) where the two panes' edges alone are 81 / 75 / 69 px apart: the moulding covers only ~12 mm
    #  (side projection) of glass in all, the side window's glass showing right behind the post; at 32 / 35 mm the
    #  visible edges stood 299 / 278 / 258 px apart, a broad slab; now 126 / 117 / 108 px.  Along the post the reveals
    #  are one round tube, POST_TUBE)
    ws_margin=(0.034, 0.008, 0.042), ws_post=0.047, ws_radii=(0.060, 0.045, 0.0), ws_post_r=0.045,
    # side window: sill / aft / top / front (A-pillar) / lower-front chamfer: the visible opening from inside -- sill
    # WL 2.09-2.11, top 2.43-2.46, aft edge STA 4.15-4.19, front-low corner ~3.56 / 2.15 (S15 panoramas, +-0.03); the
    # front edge 35 mm in (P1046408 overlay: the glass shows up to ~1/3 of the 50 mm tried first) [M]
    # (flight deck fix r2b: the sill 12 -> 19 mm -- just over the seal lip the crew eyes saw the retainer band's glass-side
    #  face through the pane, ~0.3 deg of polished metal: a white line along each side window's sill from both seats)
    sw_margin=(0.019, 0.175, 0.085, 0.006, 0.035), sw_radii=(0.120, 0.105, 0.045, 0.050, 0.050),
    # (first-principles judge r1 FP1-10: 9 mm in -- with the r5 post's 8 mm edge -- it read as a wire floating in the
    #  glass; 4 mm in it runs along the moulding's edge as the laminate's bus bar does)
    wire_d=(0.004,), wire_w=0.0007,   # [E] heating bus bar inside the visible edge (P1046408 / 10): ONE per edge, 9 mm
    #                        in, 0.7 mm, dark bronze (flight deck fix r2 FDO2-06 / FID-FD2-05: the two dark-metal lines
    #                        15 / 23 mm in read as stray wires / cracks across the glass from both seats)
    wire_depth=0.0070,     # 2.5 mm off the glass's inner face (fit_check 30 >= 2 mm; 22: seated within 3 mm)
    seal_w=0.0018,         # [M] black seal lip over the glass: 1.8 mm (P1046409 / 10, AOPA and the PRO simulator photos
    #                        show at most a hairline dark edge at the glass; the 8 mm first tried drew a heavy black outline
    #                        round every pane from the crew seats; flight deck fix FDY r1 FDY-O1-05: the 4 mm lip, seen
    #                        nearly face-on from the design eyes, still drew a hard toon line round the side windows)
    glass_d=0.0090,        # funnel / seal depth inside the OML at the glass (panes 4-5 mm in: >= 3.5 mm clear) [E]
    proud=0.0015,          # the funnel's outer edge 1.5 mm in front of the lining, overlapping its hole edge
    overlap=0.010,         # ... by 10 mm
    k=2.4,                 # profile: depth fraction 1 - (1 - tau)^k (tangent to the lining at its outer edge)
    rows=(0.0, 0.025, 0.065, 0.12, 0.19, 0.28, 0.39, 0.51, 0.64, 0.76, 0.87, 0.95, 1.0),
    step=0.007,            # point spacing along the visible outline
)


def _shift(L, m):
    p, d = L
    return np.asarray(p, float) + m * np.array([-d[1], d[0]]), np.asarray(d, float)


def _line_dist(L, px, pz):
    p, d = L
    return -d[1] * (px - p[0]) + d[0] * (pz - p[1])          # + inside (left of the directed line)


def ws_lines(visible=False):
    from model import cockpit_glazing as CG
    lines, radii = CG.ws_lines()
    if not visible:
        return lines, radii, CG.WS_POST, CG.WS_R["post"]
    g = GLAZING_TRIM
    return [_shift(L, m) for L, m in zip(lines, g["ws_margin"])], list(g["ws_radii"]), g["ws_post"], g["ws_post_r"]


def sw_lines(visible=False):
    from model import cockpit_glazing as CG
    lines, radii = CG.sw_lines()
    if not visible:
        return lines, radii
    g = GLAZING_TRIM
    return [_shift(L, m) for L, m in zip(lines, g["sw_margin"])], list(g["sw_radii"])


def ws_field(x, y, z, visible=False):
    """Windshield (one pane per side) signed distance (negative inside): the pane (cockpit_glazing.windshield_sdf) or
    its visible opening from inside."""
    from model import cockpit_glazing as CG
    lines, radii, post, rp = ws_lines(visible)
    a = CG.convex_rounded_sdf(x, z, lines, radii)
    d = CG.round_intersection(a, post - np.abs(y), rp)
    return np.where((z > 1.95) & (x > 3.0) & (x < 4.3), d, 10.0)


def sw_field(x, y, z, visible=False):
    from model import cockpit_glazing as CG
    lines, radii = sw_lines(visible)
    d = CG.convex_rounded_sdf(x, z, lines, radii)
    return np.where((np.abs(y) > 0.30) & (x > 3.3) & (x < 4.6), d, 10.0)


def _labels(kind, P, visible):
    """Edge label of points P (n, 3) on a pane outline: the nearest edge line (windshield: sill, pillar, roof, post;
    side window: sill, aft, top, front, chamfer)."""
    if kind == "ws":
        lines, _, post, _ = ws_lines(visible)
        D = [_line_dist(L, P[:, 0], P[:, 2]) for L in lines] + [np.abs(P[:, 1]) - post]
    else:
        lines, _ = sw_lines(visible)
        D = [_line_dist(L, P[:, 0], P[:, 2]) for L in lines]
    lab = np.argmin(np.abs(np.array(D)), 0)
    # mode filter: no single-point flickers at the corner bisectors
    for _ in range(2):
        prev, nxt = np.roll(lab, 1), np.roll(lab, -1)
        lab = np.where((prev == nxt) & (lab != prev), prev, lab)
    return lab


def _contour_xt(field, x0, x1, t0, t1, dx=0.003, ds=0.003):
    """Closed zero contour(s) of field(x, y, z) on the OML patch, in loft parameters (x, t) (t may run below 0)."""
    import contourpy
    from model import fuselage as F
    per = float(F.perimeter(0.5 * (x0 + x1)))
    xs = np.linspace(x0, x1, int(math.ceil((x1 - x0) / dx)) + 1)
    ts = np.linspace(t0, t1, int(math.ceil(abs(t1 - t0) * per / ds)) + 1)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = F.section(X, T % 1.0)
    Fv = field(P[..., 0], P[..., 1], P[..., 2])
    out = []
    for L in contourpy.contour_generator(z=Fv).lines(0.0):
        if len(L) < 20:
            continue
        xx = np.interp(L[:, 1], np.arange(len(xs)), xs)
        tt = np.interp(L[:, 0], np.arange(len(ts)), ts)
        Q = np.c_[xx, tt]
        if np.allclose(Q[0], Q[-1]):
            Q = Q[:-1]
        out.append(Q)
    return out


def _arc_resample(Q, P3, n):
    """n points at equal 3-D arc length along the open polyline with params Q (m, 2) and points P3 (m, 3)."""
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P3, axis=0), axis=1))]
    u = np.linspace(0.0, s[-1], n)
    return np.c_[np.interp(u, s, Q[:, 0]), np.interp(u, s, Q[:, 1])]


def _runs(lab):
    """Cyclic runs of equal labels: [(label, start, end_exclusive)] starting at a transition."""
    n = len(lab)
    k0 = int(np.nonzero(lab != np.roll(lab, 1))[0][0])
    lab = np.roll(lab, -k0)
    cuts = np.r_[0, np.nonzero(np.diff(lab))[0] + 1, n]
    return k0, [(int(lab[a]), a, b) for a, b in zip(cuts[:-1], cuts[1:])]


def _pane_pairs(kind, side):
    """Corresponding points (V_i, O_i) in loft parameters on the visible outline and the pane outline of one pane,
    matched edge by edge (anchors at the corner bisectors), equal arc length within each edge; plus each point's edge
    label.  Loops run the same way round.  Built for the starboard pane (cached), mirrored for port (t -> -t)."""
    V, O, L = _pane_pairs_stbd(kind)
    V, O = V.copy(), O.copy()
    if side < 0:
        V[:, 1], O[:, 1] = -V[:, 1], -O[:, 1]
    return V, O, L.copy()


_PAIRS = {}


def _pane_pairs_stbd(kind):
    key = (kind, tuple(GLAZING_TRIM["ws_margin"]), GLAZING_TRIM["ws_post"], tuple(GLAZING_TRIM["sw_margin"]),
           tuple(GLAZING_TRIM["sw_radii"]), GLAZING_TRIM["step"])
    if key not in _PAIRS:
        _PAIRS[key] = _pane_pairs_build(kind)
    return _PAIRS[key]


def _pane_pairs_build(kind):
    from model import fuselage as F
    if kind == "ws":
        box = (3.20, 4.10, 0.0, 0.25)
        fld = lambda vis: (lambda x, y, z: ws_field(x, y, z, vis))          # noqa: E731
    else:
        box = (3.40, 4.45, 0.02, 0.45)
        fld = lambda vis: (lambda x, y, z: sw_field(x, y, z, vis))          # noqa: E731
    loops = {}
    for vis in (False, True):
        cs = _contour_xt(fld(vis), *box)
        Q = max(cs, key=len)
        P3 = F.section(Q[:, 0], Q[:, 1] % 1.0)
        lab = _labels(kind, P3, vis)
        k0, runs = _runs(lab)
        Q, P3 = np.roll(Q, -k0, 0), np.roll(P3, -k0, 0)
        # merge short runs (< 8 points) into their neighbour
        runs = [r for r in runs if r[2] - r[1] >= 8] or runs
        loops[vis] = (Q, P3, runs)
    Qo, Po, ro = loops[False]
    Qv, Pv, rv = loops[True]
    seq_o, seq_v = [r[0] for r in ro], [r[0] for r in rv]
    # same orientation: the label sequences must match cyclically
    def rot_match(a, b):
        for k in range(len(b)):
            if b[k:] + b[:k] == a:
                return k
        return None
    k = rot_match(seq_o, seq_v)
    if k is None:
        Qv, Pv = Qv[::-1].copy(), Pv[::-1].copy()
        lab = _labels(kind, Pv, True)
        k0, rv = _runs(lab)
        Qv, Pv = np.roll(Qv, -k0, 0), np.roll(Pv, -k0, 0)
        rv = [r for r in rv if r[2] - r[1] >= 8] or rv
        seq_v = [r[0] for r in rv]
        k = rot_match(seq_o, seq_v)
        if k is None:
            raise RuntimeError(f"{kind}: pane / visible outline edges do not match: {seq_o} vs {seq_v}")
    rv = rv[k:] + rv[:k]
    V, O, L = [], [], []
    step = GLAZING_TRIM["step"]
    for (lo, a0, b0), (lv, a1, b1) in zip(ro, rv):
        idx_o = np.arange(a0, b0 + 1) % len(Qo)
        idx_v = np.arange(a1, b1 + 1) % len(Qv)
        lv_len = float(np.linalg.norm(np.diff(Pv[idx_v], axis=0), axis=1).sum())
        n = max(3, int(math.ceil(lv_len / step)) + 1)
        V.append(_arc_resample(Qv[idx_v], Pv[idx_v], n)[:-1])
        O.append(_arc_resample(Qo[idx_o], Po[idx_o], n)[:-1])
        L.append(np.full(n - 1, lo))
    return np.vstack(V), np.vstack(O), np.concatenate(L)


def _surface_dir(Px, Pt, gq):
    """3-D unit direction in the tangent plane of a parameter-space direction gq (n, 2)."""
    return _unit(gq[:, :1] * Px + gq[:, 1:] * Pt)


# flight deck fix r5 (FDO4-02 / FID-FD4-02: from the crew stops and at the photo-fitted panel_408b camera the A-pillar was a
# broad flat slab, ~160 mm across at the glass -- the pillar reveals' margins (32 / 35 mm in side projection, ~65-70 mm
# along the steeply inclined skin there) and the lining strip between them, ~50 mm deep with a flat bottom; P1046408
# through its fitted camera shows a round post ~95-110 px across at 1920 px (~70-80 mm) with the side window's glass
# right behind it, P1046409 / 10 / AOPA a slim dark tube): the windshield's pillar edge and the side window's front edge
# now show the glass to within 8 / 6 mm (side projection) of their pane edges (GLAZING_TRIM), and along the post the
# two reveals are one ROUND TUBE -- each column's profile a quarter ellipse from the glass (leaving it square, as the
# reveal did) round to the post's midline (post_axis), `proud` in front of the lining there so the lining strip between
# the panes lies hidden behind it; blended into the standard funnel profile over `fade` of the axis at both ends (the
# post flares into the glareshield / sill and the roof as in the photos) and from `z0` up (below it the side window's
# reveal is the leather sill).  The approved glazing (L2: the panes 25 mm apart in side projection, ~43 mm across the
# skin) is unchanged; the post is ~70 mm across at the glass, ~48 mm deep, its own darker satin 'lining_fd_post' (no edge
# bead along it: its round section carries the highlight).
POST_TUBE = dict(fade=0.16, z0=2.24, proud=0.007, past=0.0015, mat="lining_fd_post")


def _post_tube(kind, side, G, V, O, lab):
    """The A-pillar columns of one pane's funnel grid G (n, rows, 3) re-profiled to the round post (POST_TUBE); returns
    (G, w) with w (n,) the post weight of each column (0: the standard funnel, 1: the tube)."""
    q = POST_TUBE
    w = np.zeros(len(G))
    lab_post = 1 if kind == "ws" else 3                 # the windshield's pillar edge / the side window's front edge
    cols = np.nonzero(lab == lab_post)[0]
    if not len(cols) or q is None:
        return G, w
    c, a, s0, s1, M, N3m = post_axis(side)
    tM = (M - c) @ a
    PV, N3V = oml_frame(V[cols, 0], V[cols, 1])[:2]
    PO = oml_frame(O[cols, 0], O[cols, 1])[0]
    t = (PO - c) @ a
    u = (t - s0) / (s1 - s0)
    from model import seats as S
    wc = S.smoothstep(0.0, q["fade"], u) * S.smoothstep(1.0, 1.0 - q["fade"], u) * \
        S.smoothstep(q["z0"], q["z0"] + 0.03, PO[:, 2])
    Mi = np.stack([np.interp(t, tM, M[:, i]) for i in range(3)], 1)            # the midline point of each column
    Nm = _unit(np.stack([np.interp(t, tM, N3m[:, i]) for i in range(3)], 1))
    Nms = _unit(np.c_[np.zeros(len(Nm)), Nm[:, 1], Nm[:, 2]])
    D = lining_depth(Nms) + q["proud"]                                        # the tube's bottom: in front of the lining
    A = PV - GLAZING_TRIM["glass_d"] * N3V                                     # the funnel's glass end (row 0)
    B = Mi - D[:, None] * Nms                                                  # on the midline: both halves meet there
    Dv = np.sum((B - A) * N3V, 1)[:, None] * N3V                               # straight in from the glass ...
    Lv = (B - A) - Dv                                                          # ... then across to the midline
    R = G.shape[1]
    th = 0.5 * np.pi * np.linspace(0.0, 1.0, R - 1)
    T = np.empty((len(cols), R, 3))
    for r, a_ in enumerate(th):                                                # a quarter ellipse A -> B
        T[:, r] = A + (1.0 - math.cos(a_)) * Lv + math.sin(a_) * Dv
    T[:, R - 1] = B + q["past"] * _unit(Lv)                                    # a hair past the midline (no crack)
    G = G.copy()
    G[cols] = (1.0 - wc)[:, None, None] * G[cols] + wc[:, None, None] * T
    w[cols] = wc
    return G, w


def pane_moulding(kind, side):
    """The moulded reveal of one pane (kind 'ws' windshield, 'sw' side window; side -1 port, +1 starboard): funnel
    (lining_flightdeck) and seal lip ('seal'); returns [(Mesh, material)], the funnel grid (n, rows, 3), the edge label
    of each column and its A-pillar tube weight (POST_TUBE)."""
    g = GLAZING_TRIM
    V, O, lab = _pane_pairs(kind, side)
    # one row per tau (the glass end first), the overlap row last
    taus = np.asarray(g["rows"], float)
    k = g["k"]
    rows = []
    PO, N3O, NsO, PxO, PtO = oml_frame(O[:, 0], O[:, 1])
    PV, N3V, NsV, PxV, PtV = oml_frame(V[:, 0], V[:, 1])
    for tau in taus:
        Q = (1.0 - tau) * V + tau * O
        P, N3, Ns, _, _ = oml_frame(Q[:, 0], Q[:, 1])
        h = 1.0 - (1.0 - tau) ** k
        dl = lining_depth(Ns)
        d = g["glass_d"] + (dl - g["proud"] - g["glass_d"]) * h
        dirn = _unit((1.0 - h) * N3 + h * Ns)
        rows.append(P - d[:, None] * dirn)
    # overlap row: 10 mm on beyond the lining hole edge, 1.5 mm proud of the lining
    gq = O - V
    gq_norm = np.linalg.norm(gq, axis=1, keepdims=True)
    # parameter direction away from the opening: (O - V) where the margin is wide, else the loop's own normal
    tan_q = np.roll(O, -1, 0) - np.roll(O, 1, 0)
    nq = np.c_[tan_q[:, 1], -tan_q[:, 0]]
    nq *= np.sign(np.sum(nq * (O - O.mean(0)), 1))[:, None]
    gq = np.where(gq_norm > 1e-4, gq, nq)
    out_dir = _surface_dir(PxO, PtO, gq)
    out_dir = _unit(out_dir - np.sum(out_dir * N3O, 1)[:, None] * N3O)
    dlO = lining_depth(NsO)
    rows.append(PO + g["overlap"] * out_dir - (dlO - g["proud"])[:, None] * NsO)
    G = np.stack(rows, 1)                                                        # (n, rows, 3)
    G, wpost = _post_tube(kind, side, G, V, O, lab)
    funnel = grid_surface(G, close_u=True)
    anchor = np.repeat(PO[:, None, :], G.shape[1], 1).reshape(-1, 3)

    def away_from_skin(C, A=anchor, GV=G.reshape(-1, 3)):
        from scipy.spatial import cKDTree
        _, i = cKDTree(GV).query(C)
        return C - A[i]
    funnel = _orient(funnel, away_from_skin)
    # seal lip: from the visible edge 8 mm on over the glass, at the funnel's glass depth
    in_dir = _unit(-_surface_dir(PxV, PtV, gq) + 0.0 * N3V)
    in_dir = _unit(in_dir - np.sum(in_dir * N3V, 1)[:, None] * N3V)
    s_out = G[:, 0]
    s_in = PV + g["seal_w"] * in_dir - g["glass_d"] * N3V
    seal = grid_surface(np.stack([s_in, s_out], 1), close_u=True)
    seal = _orient(seal, lambda C: -np.mean(N3V, 0)[None].repeat(len(C), 0))
    out = [(funnel, "lining_flightdeck"), (seal, "seal")]
    if kind == "ws":
        # the windshield's heating bus bars / wires: thin dark lines on the glass's inner side parallel to the A-pillar
        # and centre-post edges (P1046408 / 10 show two or three of them beside each post; flight deck fix r1
        # FID-FD1-09), 2.5 mm inside the glass (fit_check 30 / 22), dark metal (black read as cracks across the glass)
        for k0, k1 in _label_spans(lab, (1, 3), trim=4):
            idx = np.arange(k0, k1)
            for d0 in g["wire_d"]:
                a = PV[idx] + d0 * in_dir[idx] - g["wire_depth"] * N3V[idx]
                b = PV[idx] + (d0 + g["wire_w"]) * in_dir[idx] - g["wire_depth"] * N3V[idx]
                w = grid_surface(np.stack([a, b], 1))
                out.append((_orient(w, lambda C: -np.mean(N3V, 0)[None].repeat(len(C), 0)), "busbar_bronze"))
    return out, G, lab, wpost


def _label_spans(lab, keep, trim=0):
    """Index spans [k0, k1) of the cyclic label sequence `lab` whose label is in `keep`, `trim` points off both ends
    (clear of the corners); spans wrapping the loop's start are left out."""
    out = []
    n = len(lab)
    k = 0
    while k < n:
        if lab[k] in keep:
            j = k
            while j < n and lab[j] == lab[k]:
                j += 1
            whole = (k > 0 or lab[-1] != lab[0]) and (j < n or lab[-1] != lab[0])
            if whole and j - k > 2 * trim + 2:
                out.append((k + trim, j - trim))
            k = j
        else:
            k += 1
    return out


SILL = dict(
    leather_z=2.230,       # [M] side-window reveal in leather below this WL (the sill and the aft-lower corner: AOPA /
    #                        P1046409 -- the stitched leather panel wraps the window bottom up to ~40 % of the aft edge)
    stitch_rows=(10,),     # funnel rows carrying a stitch seam (tau 0.87 on the roll; flight deck fix r1 FDO1-04: one
    #                        tone-on-tone seam -- the photos show no light thread on the sill, the two light seams read
    #                        as white dashed lines round the side windows from the seats)
    # placards on the sill top, (u from the sill's forward end, width, height) [M] AOPA / P1046409 / 10 (abstract):
    # a small black / white placard at the forward end, then two red ones, all on the sill's narrow forward part
    # (x < 3.93, 31-45 mm wide between the stitch rows: aft of it the reveal fans out into the window's aft-lower
    # corner and the placards had drawn as skewed red parallelograms ~2x their size)
    # flight deck fix r1 (FDO1-04): one red placard and a dark one, about half the first build's lengths (from the
    # crew seats, 0.3 m off, the 85 / 95 mm red bands read as broad red stripes along the sill; P1046410 / AOPA show a
    # dark placard group with one red label)
    placards=((0.055, 0.034, 0.014, "white"), (0.098, 0.046, 0.012, "red"), (0.153, 0.040, 0.012, "white")),
)


def glazing_mouldings():
    """Both windshield panes and both side windows: [(Mesh, material)] (interior.build_lining adds them as reveals).
    The side-window reveal is leather below SILL leather_z (the padded sill continuing the glareshield leather, two
    stitch seams, the sill placards), lining above."""
    out = []
    # side-window reveal split at SILL leather_z
    rng = np.random.default_rng(31)
    with res.coarse():
        for kind in ("ws", "sw"):
            for side in (-1, 1):
                ms, G, lab, wpost = pane_moulding(kind, side)
                funnel = ms[0][0]
                if kind == "ws":
                    out += _reveal_zones(G, np.arange(len(G)), funnel, True, wpost)   # inner face / lining / edge bead
                    out += ms[1:]
                    continue
                out.append(ms[1])                                       # seal lip
                zv = G[:, 0, 2]
                low = zv < SILL["leather_z"]
                # contiguous run of 'low' columns (cyclic): the leather part
                n = len(zv)
                k0 = int(np.nonzero(low & ~np.roll(low, 1))[0][0])
                idx = (np.arange(n) + k0) % n
                nlow = int(low.sum())
                il = idx[:nlow + 1]                                     # leather columns (+ the boundary column)
                iu = np.r_[idx[nlow:], idx[0]]                          # lining columns (+ both boundary columns)
                m = grid_surface(G[il])
                out.append((_orient(m, lambda C, f=funnel: _toward(f, C)), "leather_glareshield"))
                out += _reveal_zones(G, iu, funnel, False, wpost)
                Nn = _grid_n(G[il], funnel)
                for r in SILL["stitch_rows"]:
                    out.append((dashes(G[il, r], Nn[:, r]), "panel_grey"))      # tone-on-tone (FDO1-04)
                # placards on the sill top (sill label 0 columns, between the stitch rows)
                sill_cols = np.array([i for i in il if lab[i] == 0])
                if len(sill_cols) > 4:
                    order = np.argsort(G[sill_cols, 0, 0])
                    sc = sill_cols[order]
                    pos = {int(c): k for k, c in enumerate(il)}
                    sm = SurfMap(G[sc][:, 5:10], Nn[[pos[int(i)] for i in sc]][:, 5:10])
                    vmid = 0.5 * sm.sv[-1]
                    # the map's v is the middle column's arc length: scale each placard's v extent by the strip's
                    # local width there, so the placards keep their size
                    wcol = np.linalg.norm(np.diff(G[sc][:, 5:10], axis=1), axis=2).sum(1)
                    for u, w, h, col in SILL["placards"]:
                        if u + w > sm.su[-1]:
                            continue
                        k = sm.sv[-1] / float(np.interp(u + 0.5 * w, sm.su, wcol))
                        hv = h * k
                        # (first-principles A3: printed placards, one decal each; fix r2 FID-FD2-09's muted red)
                        out.append(PR.decal_map(sm, u, vmid - 0.5 * hv, u + w, vmid + 0.5 * hv, 0.0, "plate",
                                                colour="red_dim" if col == "red" else "plate_black", ink="white",
                                                rows=3 if h > 0.014 else 2, cap=1.3, seed=("sill", side, u)))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


# flight deck fix r2 (FDO2-03: the A-pillar / side-window surround read as one huge plain grey slab from the seats; the
# photos -- P1046409 / 10, AOPA -- show a darker inner face toward the glass and a light-catching rolled edge): the funnel
# rows from the glass up to `inner_row` (tau 0.39) in a darker satin (lining_fd_reveal), the rest the lining, and a
# satin edge bead (trim_satin, half-round r `bead_r`, sunk 30 % into the funnel) along that row; the leather sill keeps
# its own finish (its top carries the placards)
REVEAL = dict(inner_row=6, bead_r=0.0028, bead_phi=(-20.0, 200.0, 13), bead_step=0.012)


def _reveal_zones(G, cols, funnel, closed, wpost=None):
    """[(Mesh, material)] of the funnel grid G's columns `cols` (cyclic when `closed`): the inner face, the lining
    beyond it and the edge bead along the row between them; the A-pillar tube's columns (wpost > 0.5, POST_TUBE) one
    piece in its own material, no bead."""
    cols = np.asarray(cols)
    isp = None if wpost is None else wpost[cols] > 0.5
    if isp is None or not isp.any():
        return _reveal_run(G, cols, funnel, closed)
    n = len(cols)
    if closed:                                         # start at the first column after a post run
        k0 = int(np.nonzero(~isp & np.roll(isp, 1))[0][0])
        cols, isp = np.roll(cols, -k0), np.roll(isp, -k0)
    cuts = np.r_[0, np.nonzero(np.diff(isp.astype(int)))[0] + 1, n]
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        ext = cols[a:b + 1] if (b < n) else (np.r_[cols[a:b], cols[0]] if closed else cols[a:b])
        if isp[a]:
            m = grid_surface(G[ext])
            out.append((_orient(m, lambda C, f=funnel: _toward(f, C)), POST_TUBE["mat"]))
        elif len(ext) >= 2:
            out += _reveal_run(G, ext, funnel, False)
    return out


def _reveal_run(G, cols, funnel, closed):
    """_reveal_zones of a run of columns without the post tube."""
    from scipy.spatial import cKDTree
    q = REVEAL
    k = q["inner_row"]
    out = []
    for rows, mat in ((slice(0, k + 1), "lining_fd_reveal"), (slice(k, None), "lining_flightdeck")):
        m = grid_surface(G[cols][:, rows], close_u=closed)
        out.append((_orient(m, lambda C, f=funnel: _toward(f, C)), mat))
    Gc = G[cols]
    Nn = _grid_n(Gc, funnel)
    P, N = Gc[:, k], Nn[:, k]
    # resample the row at ~bead_step (the funnel's columns are ~7 mm apart)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]) if closed else P, axis=0), axis=1))]
    L = s[-1]
    nb = max(4, int(round(L / q["bead_step"])))
    t = np.linspace(0.0, L, nb, endpoint=not closed)
    PP = np.vstack([P, P[:1]]) if closed else P
    NN = np.vstack([N, N[:1]]) if closed else N
    Pb = np.stack([np.interp(t, s, PP[:, i]) for i in range(3)], 1)
    Nb = _unit(np.stack([np.interp(t, s, NN[:, i]) for i in range(3)], 1))
    D = Gc[:, k + 1] - Gc[:, k - 1]                                      # across the row (toward the lining)
    DD = np.vstack([D, D[:1]]) if closed else D
    Db = np.stack([np.interp(t, s, DD[:, i]) for i in range(3)], 1)
    Db = _unit(Db - np.sum(Db * Nb, 1)[:, None] * Nb)
    r = q["bead_r"]
    a0, a1, na = q["bead_phi"]
    ph = np.radians(np.linspace(a0, a1, na))
    C0 = Pb - 0.3 * r * Nb
    B = np.stack([C0 + r * (np.cos(f) * Db + np.sin(f) * Nb) for f in ph], 1)        # (nb, na, 3)
    bead = grid_surface(B, close_u=closed)
    tree = cKDTree(C0)
    out.append((_orient(bead, lambda C: C - C0[tree.query(C)[1]]), "trim_satin"))
    return out


# The A-pillar's axis (flight deck fix r3; the r3 bent vertex normals, satin bead and fasteners on the lining strip went
# with fix r5's round post tube, POST_TUBE: the strip now lies hidden behind it)
_POST_AXES = {}


def post_axis(side):
    """(c, a, s0, s1, M, N): the A-pillar's axis of one side (side -1 port, +1 starboard) -- a point c, the unit
    direction a (up the post), the extent s0..s1 along it -- and the midline points M (12, 3) on the OML with their
    outward normals N."""
    if side in _POST_AXES:
        return _POST_AXES[side]
    edges = []
    for kind, lab in (("ws", 1), ("sw", 3)):
        _, O, L = _pane_pairs(kind, side)
        P = oml_frame(O[L == lab, 0], O[L == lab, 1])[0]
        edges.append(P[np.argsort(P[:, 2])])
    z0 = max(e[:, 2].min() for e in edges) + 0.01
    z1 = min(e[:, 2].max() for e in edges) - 0.01
    zs = np.linspace(z0, z1, 12)
    E = [np.stack([np.interp(zs, e[:, 2], e[:, i]) for i in range(3)], 1) for e in edges]
    M = 0.5 * (E[0] + E[1])
    from model import fuselage as F
    xt = []
    for Pm in M:                                            # the OML normal at each midline point (nearest loft sample)
        xs = np.linspace(Pm[0] - 0.05, Pm[0] + 0.05, 21)
        ts = np.linspace(-0.45, 0.45, 361)
        X, T = np.meshgrid(xs, ts, indexing="ij")
        S = F.section(X, T % 1.0)
        k = np.argmin(np.linalg.norm(S - Pm, axis=-1))
        xt.append((X.ravel()[k], T.ravel()[k]))
    xt = np.array(xt)
    _, N3, _, _, _ = oml_frame(xt[:, 0], xt[:, 1])
    A = M
    c = A.mean(0)
    a = np.linalg.svd(A - c)[2][0]
    a = a if a[2] > 0 else -a
    t = (A - c) @ a
    out = (c, a, float(t.min()), float(t.max()), M, N3)
    _POST_AXES[side] = out
    return out


def _toward(ref, C):
    """Per-point direction of the nearest face normal of `ref` (orient a split copy like its parent)."""
    from scipy.spatial import cKDTree
    Cr = ref.V[ref.F].mean(1)
    _, i = cKDTree(Cr).query(C)
    return ref.face_normals()[i]


def _grid_n(G, ref):
    """Vertex normals of grid G oriented like the mesh `ref`."""
    from cad.mesh import grid_normals
    N = grid_normals(G)
    d = _toward(ref, G.reshape(-1, 3)).reshape(N.shape)
    return N * np.sign(np.sum(N * d, -1, keepdims=True))


# =====================================================================================================================
# small helpers: surface maps, stitching, legend strokes (no text: abstract strokes only)
# =====================================================================================================================
class SurfMap:
    """Arc-length map over a gridded surface G (n, m, 3) with normals Nn (n, m, 3): p(u, v, off) at u along the first
    index, v along the second (metres from G[0, 0] along the grid lines through the given row / column), lifted off
    the surface by `off` along the (interpolated) normal."""

    def __init__(self, G, Nn=None, ref_row=None, ref_col=None):
        self.G = np.asarray(G, float)
        if Nn is None:
            from cad.mesh import grid_normals
            Nn = grid_normals(self.G)
        self.N = Nn
        rr = self.G.shape[1] // 2 if ref_row is None else ref_row
        rc = self.G.shape[0] // 2 if ref_col is None else ref_col
        self.su = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(self.G[:, rr], axis=0), axis=1))]
        self.sv = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(self.G[rc], axis=0), axis=1))]

    def _idx(self, s, S):
        s = np.clip(np.asarray(s, float), S[0], S[-1])
        i = np.clip(np.searchsorted(S, s) - 1, 0, len(S) - 2)
        f = (s - S[i]) / np.maximum(S[i + 1] - S[i], 1e-12)
        return i, f

    def frame(self, u, v):
        u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
        i, fu = self._idx(u.ravel(), self.su)
        j, fv = self._idx(v.ravel(), self.sv)
        G, N = self.G, self.N
        w00, w10, w01, w11 = ((1 - fu) * (1 - fv))[:, None], (fu * (1 - fv))[:, None], ((1 - fu) * fv)[:, None], \
            (fu * fv)[:, None]
        P = w00 * G[i, j] + w10 * G[i + 1, j] + w01 * G[i, j + 1] + w11 * G[i + 1, j + 1]
        Nn = _unit(w00 * N[i, j] + w10 * N[i + 1, j] + w01 * N[i, j + 1] + w11 * N[i + 1, j + 1])
        return P.reshape(u.shape + (3,)), Nn.reshape(u.shape + (3,))

    def p(self, u, v, off=0.0):
        P, N = self.frame(u, v)
        return P + np.asarray(off, float)[..., None] * N if np.ndim(off) else P + off * N

    def patch(self, u0, v0, u1, v1, off, nu=None, nv=None, step=0.01):
        """Patch of the surface over u0..u1 x v0..v1, `off` off it (normals as the surface's)."""
        nu = nu or max(2, int(math.ceil(abs(u1 - u0) / step)) + 1)
        nv = nv or max(2, int(math.ceil(abs(v1 - v0) / step)) + 1)
        U, Vv = np.meshgrid(np.linspace(u0, u1, nu), np.linspace(v0, v1, nv), indexing="ij")
        P, N = self.frame(U, Vv)
        m = grid_surface(P + off * N)
        return _orient(m, lambda C, Nm=N.reshape(-1, 3).mean(0): np.broadcast_to(Nm, C.shape))

    def quads(self, rects, off, seg=0.012):
        """Quads (u0, v0, u1, v1) lifted `off` off the surface (legend strokes, placards): one Mesh.  A rect longer
        than `seg` is split into pieces of at most that length, so it follows the surface: one flat chord across a
        CB block (0.25 m) stood up to ~0.5 mm off the curved lining and buried the strokes laid on it."""
        if not len(rects):
            return None
        R = []
        for u0, v0, u1, v1 in np.asarray(rects, float):
            nu = max(1, int(math.ceil(abs(u1 - u0) / seg)))
            nv = max(1, int(math.ceil(abs(v1 - v0) / seg)))
            uu, vv = np.linspace(u0, u1, nu + 1), np.linspace(v0, v1, nv + 1)
            R += [(uu[i], vv[j], uu[i + 1], vv[j + 1]) for i in range(nu) for j in range(nv)]
        R = np.asarray(R, float)
        U = np.stack([R[:, 0], R[:, 2], R[:, 2], R[:, 0]], 1)
        Vv = np.stack([R[:, 1], R[:, 1], R[:, 3], R[:, 3]], 1)
        P, N = self.frame(U, Vv)
        P = P + off * N
        k = np.arange(len(R)) * 4
        F = np.vstack([np.stack([k, k + 1, k + 2], 1), np.stack([k, k + 2, k + 3], 1)])
        m = Mesh(P.reshape(-1, 3), F)
        return _orient(m, lambda C, Nm=N.reshape(-1, 3).mean(0): np.broadcast_to(Nm, C.shape))


def dashes(P, N, pitch=0.006, dash=0.0036, width=0.0009, raise_=0.0005):
    """Stitching: short raised quads every `pitch` along the polyline P (n, 3) with surface normals N."""
    P, N = np.asarray(P, float), np.asarray(N, float)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if s[-1] < pitch:
        return None
    c = np.arange(0.5 * pitch, s[-1] - 0.5 * dash, pitch)
    quads = []
    for a, b in ((c - 0.5 * dash, c + 0.5 * dash),):
        pa = np.stack([np.interp(a, s, P[:, k]) for k in range(3)], 1)
        pb = np.stack([np.interp(b, s, P[:, k]) for k in range(3)], 1)
        nn = _unit(np.stack([np.interp(c, s, N[:, k]) for k in range(3)], 1))
        t = _unit(pb - pa)
        w = _unit(np.cross(nn, t)) * (0.5 * width)
        lift = nn * raise_
        quads = np.stack([pa - w + lift, pb - w + lift, pb + w + lift, pa + w + lift], 1)
    k = np.arange(len(quads)) * 4
    F = np.vstack([np.stack([k, k + 1, k + 2], 1), np.stack([k, k + 2, k + 3], 1)])
    m = Mesh(quads.reshape(-1, 3), F)
    return _orient(m, lambda C, Nm=N.mean(0): np.broadcast_to(Nm, C.shape))


def legend_rects(u0, v0, w, h, rng, lines=1, fill=0.75, bar=0.32):
    """Abstract legend: `lines` rows of 1-3 short bars (no glyphs) inside the box u0..u0+w, v0..v0+h."""
    out = []
    lh = h / lines
    for k in range(lines):
        vc = v0 + (k + 0.5) * lh
        hh = 0.5 * bar * lh
        n = int(rng.integers(1, 4))
        tot = w * fill * float(rng.uniform(0.6, 1.0))
        gaps = 0.18 * tot / max(n, 1)
        L = (tot - gaps * (n - 1)) / n
        u = u0 + 0.5 * (w - tot)
        for _ in range(n):
            ln = L * float(rng.uniform(0.7, 1.15))
            out.append((u, vc - hh, min(u + ln, u0 + w), vc + hh))
            u += ln + gaps
    return out


def box_outline(u0, v0, u1, v1, t):
    """Four thin rectangles: an outlined box (section frames, label boxes)."""
    return [(u0, v0, u1, v0 + t), (u0, v1 - t, u1, v1), (u0, v0, u0 + t, v1), (u1 - t, v0, u1, v1)]


def lining_map(side, x0, x1, z0, z1, off, nx=None, nz=None, step=0.01):
    """SurfMap over the side-wall lining between stations x0..x1 and water lines z0..z1 (`off` inboard of it): u along
    x (aft), v up."""
    from model import flightdeck as FD
    L = FD.lining()
    nx = nx or max(2, int(math.ceil((x1 - x0) / step)) + 1)
    nz = nz or max(2, int(math.ceil((z1 - z0) / step)) + 1)
    X, Z = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(z0, z1, nz), indexing="ij")
    Y = side * (L.hw(X, Z) - off)
    G = np.stack([X, Y, Z], -1)
    from cad.mesh import grid_normals
    Nn = grid_normals(G)
    Nn = Nn * np.sign(np.sum(Nn * np.array([0.0, -side, 0.0]), -1, keepdims=True))     # inboard
    return SurfMap(G, Nn)


# =====================================================================================================================
# B3  circuit-breaker panels: two panels per side (NGX POH Fig 7-13-2 / 3: FRONT 12 x 4, REAR 11 x 4) on black plates
# set 4 mm back in a panel_dark bezel frame on the side-wall lining, each row a line of small black breaker heads on
# white collars, a label strip (abstract legend cells) and a dim lit bus band; the ledge above with the long stowage
# slot (zip edge), red placards, the map light and the operating-limitations placard (abstract strokes)
# =====================================================================================================================
CB = dict(
    head_r=0.0030, head_h=0.0065, collar=0.0004,   # [M] breaker heads (P1046409 / 10, AOPA): small black, white collar
    # (flight deck fix r2 FID-FD2-09: the heads read as holes in a black field from the seats -- each now stands on a
    #  white collar SLEEVE `sleeve` = (radial width, height) and 3 mm higher, `raise`)
    # (flight deck fix FDY r1 FIDY1-06: the 8 mm heads on 10.4 mm white collars read as a grid of polka-dot knobs from
    #  the co-pilot stop; the AOPA close-up / P1046409 / 10 show small dark heads over thin satin rings, the label cells
    #  the dominant feature: heads r 4 -> 3 mm, the sleeve a thin dark-metal ring, `sleeve_mat`)
    # (flight deck fix FDY r2 FDY-O2-05: from the crew stops the rows still read as bright silver bead chains -- the
    #  satin dark-metal rings mirror the sunlit windshield; the photos' heads are black on dark plates, the rows read
    #  through their lit legend strips: a thinner ring in the satin black)
    sleeve=(0.0005, 0.0016), raise_=0.0030, sleeve_mat="black",
    frame=0.013, frame_proud=0.0065, plate_proud=0.0025,   # [E] bezel frame width, faces (4 mm recess)
    band=0.0026,                                   # [E] lit bus band height
    band_blue=0.0016,                              # [E] the LH blue bands, thinner (FDY r2 FIDY2-05)
    # lit bus bands per row (1-4) [M]: LH rows blue (P1046410, PRO Mexico photo); RH front yellow / green, rear white
    # (P1046409, AOPA studio photo)
    # (flight deck fix r2 FID-FD2-09: LH white -- the blue bands read as diagonal blue lines across the black field from
    #  the pilot seat; the AOPA studio photo shows the lit strips white / green / yellow)
    # (flight deck fix FDY r2 FIDY2-05: back to BLUE on the LH, P1046410's black plate with blue lit bands behind the
    #  white legends and row numbers; thinner than r2's, `band_blue`, so they read as lit strips and not as diagonal lines)
    glow={-1: (("blue",) * 4, ("blue",) * 4), 1: (("yellow", "green", "green", "green"), ("white",) * 4)},
    # label strips per block [M]: backlit white legend cells on the black plate, except the RH rear block's light
    # silver strips with dark legends (AOPA studio photo, P1046409)
    # (flight deck fix FDY r1 FIDY1-06: the dark cells now sit on a dark-grey label strip, `cell_mat`, each framed by
    #  white rules with two rows of legend strokes -- P1046410's LH and P1046409's RH front blocks show dark cells with
    #  white text over the lit bus band, the AOPA RH rear block light silver cells; both consoles kept that way)
    # (flight deck fix FDY r2 FDY-O2-05 / FIDY2-05: the dark-grey cells -- legend_grey, 0.13 -- read as light-grey strips,
    #  rows of silver piano keys, wherever the sun or the side window lit them (150-180 from the pilot stop): the cells
    #  in the plate's satin black, so only the white rules, the legends and the lit bands carry the rows)
    label={-1: ("dark", "dark"), 1: ("dark", "light")}, cell_mat="black",
    slot=(0.010, 0.032),                           # [M] stowage slot height, its centre above the bezel top
)


def _row_layout(h0, h1, rows=4):
    """Per row (from the top): v of the breaker centres, label strip (v0, v1), bus band (v0, v1) -- v up from h0."""
    rh = (h1 - h0) / rows
    out = []
    for r in range(rows):
        top = (h1 - h0) - r * rh
        vk = top - 0.30 * rh
        out.append((vk, (top - 0.80 * rh, top - 0.52 * rh), (top - 0.93 * rh, top - 0.93 * rh + CB["band"])))
    return out


def cb_panels(fl):
    """[(Mesh, material)] of both sides' CB panel pairs, bezels, ledge fittings (group 'cb_panels')."""
    from model import interior as I
    from cad.mesh import cylinder, disk
    SC = I.SIDE_CONSOLE
    x0, x1, h0, h1 = (float(v) for v in SC["cb_panel"])
    xs0, xs1 = (float(v) for v in SC["cb_split"])
    grids = SC["cb_grid"]
    z0, z1 = fl + h0, fl + h1
    fw = CB["frame"]
    out = []
    rng = np.random.default_rng(7)
    with res.coarse():
        for sg in (-1, 1):
            M = lining_map(sg, x0 - fw - 0.002, x1 + fw + 0.002, z0 - fw - 0.002, z1 + fw + 0.002, 0.0, step=0.012)
            # u along x (aft), v up, both from the map's corner
            u = lambda x: (x - (x0 - fw - 0.002))                                  # noqa: E731  (u along x)
            v = lambda z: (z - (z0 - fw - 0.002))                                  # noqa: E731
            a0, a1, b0, b1 = u(x0), u(x1), v(z0), v(z1)
            A0, A1, B0, B1 = a0 - fw, a1 + fw, b0 - fw, b1 + fw
            fp, pp = CB["frame_proud"], CB["plate_proud"]
            # frame: front face (4 bands), outer side walls to the lining, chamfered inner walls down to the plates
            for (p, q, r_, s_) in ((A0, B0, A1, b0), (A0, b1, A1, B1), (A0, b0, a0, b1), (a1, b0, A1, b1)):
                out.append((M.patch(p, q, r_, s_, fp, step=0.02), "panel_dark"))
            ring_o = [(A0, B0), (A1, B0), (A1, B1), (A0, B1)]
            ring_i = [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
            ring_c = [(a0 + 0.002, b0 + 0.002), (a1 - 0.002, b0 + 0.002), (a1 - 0.002, b1 - 0.002), (a0 + 0.002, b1 - 0.002)]
            for ring, o0, o1 in ((ring_o, -0.0008, fp), (ring_i, fp, pp + 0.0015)):
                for k in range(4):
                    (p0, q0), (p1, q1) = ring[k], ring[(k + 1) % 4]
                    n = max(2, int(math.ceil(math.hypot(p1 - p0, q1 - q0) / 0.02)) + 1)
                    U, Vv = np.linspace(p0, p1, n), np.linspace(q0, q1, n)
                    if ring is ring_i:
                        P0 = M.p(U, Vv, o0)
                        Uc = np.linspace(ring_c[k][0], ring_c[(k + 1) % 4][0], n)
                        Vc = np.linspace(ring_c[k][1], ring_c[(k + 1) % 4][1], n)
                        P1 = M.p(Uc, Vc, o1)
                    else:
                        P0, P1 = M.p(U, Vv, o0), M.p(U, Vv, o1)
                    m = grid_surface(np.stack([P0, P1], 1))
                    cen = M.p(0.5 * (a0 + a1), 0.5 * (b0 + b1), 0.0)
                    sgn = 1.0 if ring is ring_o else -1.0
                    out.append((_orient(m, lambda C, c=cen, s_=sgn: s_ * (C - c)), "panel_dark"))
            # the two plates (bezel_black: consistency_2d3d measures the pair's extent on it), the mullion between
            for (pa, pb), (ncol, nrow), glow, lab in zip(((x0, xs0), (xs1, x1)), grids, CB["glow"][sg],
                                                         CB["label"][sg]):
                out.append((M.patch(u(pa), b0, u(pb), b1, pp, step=0.02), "bezel_black"))
                rows = _row_layout(0.0, z1 - z0, nrow)
                du = (pb - pa) / ncol
                legends, white, strips, cells, labels = [], [], [], [], []
                for r, (vk, (l0, l1), (g0, g1)) in enumerate(rows):
                    if glow[r] == "blue":
                        g1 = g0 + CB["band_blue"]
                    out.append((M.quads([(u(pa) + 0.004, b0 + g0, u(pb) - 0.004, b0 + g1)], pp + 0.0007),
                                f"fdb_cb_glow_{glow[r]}"))
                    if lab == "light":                 # a light label strip under the row's legends
                        strips.append((u(pa) + 0.004, b0 + l0 - 0.0006, u(pb) - 0.004, b0 + l1 + 0.0006))
                    else:                              # a dark-grey strip of cells, framed top and bottom
                        cells.append((u(pa) + 0.004, b0 + l0 - 0.0006, u(pb) - 0.004, b0 + l1 + 0.0006))
                        white += [(u(pa) + 0.004, b0 + l1 - 0.0005, u(pb) - 0.004, b0 + l1),
                                  (u(pa) + 0.004, b0 + l0, u(pb) - 0.004, b0 + l0 + 0.0005)]
                    # (first-principles A3) the row's label cells printed: rules, dividers and a two-line pseudo-text
                    # label per breaker, white on the dark cells / black on the light strips
                    labels.append(PR.decal_map(M, u(pa) + 0.004, b0 + l0 - 0.0006, u(pb) - 0.004, b0 + l1 + 0.0006,
                                               pp + (0.0006 if lab == "light" else 0.0005), "cells", ncol=ncol, rows=2,
                                               colour="black" if lab == "light" else "white", lw=0.3,
                                               seed=("cb", sg, round(pa, 3), r)))
                    for c in range(ncol):
                        uc = u(pa) + (c + 0.5) * du
                        P, Nn = M.frame(uc, b0 + vk)
                        P = P + pp * Nn
                        sw_, sh_ = CB["sleeve"]
                        out.append((cylinder(P - 0.0002 * Nn, P + sh_ * Nn, CB["head_r"] + sw_, n=10),
                                    CB["sleeve_mat"]))
                        out.append((cylinder(P + 0.0010 * Nn, P + (CB["head_h"] + CB["raise_"]) * Nn, CB["head_r"],
                                             n=10), "grip_black"))
                    if pa == x0:                       # row marks: 1-4 printed dots on the frame's forward band
                        out.append(PR.decal_map(M, u(pa) - 0.0056, b0 + vk - 0.0070, u(pa) - 0.0024,
                                                b0 + vk - 0.0070 + 0.0032 * (r + 1), fp, "vector",
                                                prims=tuple(("dot", 1.0 + 1.2 * (d % 2), 1.6 + 3.2 * d, 0.55)
                                                            for d in range(r + 1))))
                if strips:                             # light strips under their printed labels
                    out.append((M.quads(strips, pp + 0.0006), "fdb_cb_label"))
                else:                                  # the dark cells under their printed labels
                    out.append((M.quads(cells, pp + 0.0005), CB["cell_mat"]))
                out += labels
            out.append((M.patch(u(xs0) - 0.0005, b0, u(xs1) + 0.0005, b1, fp, step=0.02), "panel_dark"))
            # ledge above: stowage slot with a zip edge, satin edge strip, red placards, map light, limitations placard
            hs, dz = CB["slot"]
            zs = z1 + fw + dz
            Ml = lining_map(sg, x0 - 0.02, x1 + 0.06, zs - 0.03, zs + 0.03, 0.0, step=0.01)
            ul = lambda x: x - (x0 - 0.02)                                        # noqa: E731
            vl = lambda z: z - (zs - 0.03)                                        # noqa: E731
            xa_, xb_ = x0 + 0.035, x1 - 0.020
            out.append((Ml.patch(ul(xa_), vl(zs - 0.5 * hs), ul(xb_), vl(zs + 0.5 * hs), 0.0012, step=0.02), "black"))
            zip_ = [(t, vl(zs) - 0.0009, t + 0.0012, vl(zs) + 0.0009) for t in np.arange(ul(xa_) + 0.004,
                                                                                      ul(xb_) - 0.004, 0.0024)]
            out.append((Ml.quads(zip_, 0.0018), "metal_dark"))
            out.append((Ml.quads([(ul(xa_) + 0.006, vl(zs) - 0.0022, ul(xa_) + 0.026, vl(zs) + 0.0022)], 0.0022),
                        "metal_dark"))                                              # zip pull
            out.append((Ml.patch(ul(xa_) - 0.01, vl(zs - 0.5 * hs - 0.006), ul(xb_) + 0.01,
                                 vl(zs - 0.5 * hs - 0.003), 0.0012, step=0.02), "panel_silver"))
            # (flight deck fix r1 FDO1-04: 70 / 85 mm long -- the AOPA studio photo's pair over the RH panels, ~0.1 m
            # each; the first build's 90 / 120 mm read as long red bars from the crew seats)
            for xp, w, h in ((x0 + 0.20, 0.070, 0.008), (x0 + 0.30, 0.085, 0.009)):
                # (first-principles A3: printed placards -- a muted red plate with white pseudo-text, one decal)
                out.append(PR.decal_map(Ml, ul(xp), vl(zs - 0.5 * hs - 0.016), ul(xp + w),
                                        vl(zs - 0.5 * hs - 0.016 + h), 0.0, "plate", colour="red_dim", ink="white",
                                        rows=1, cap=1.6 if h < 0.0085 else 1.8, seed=("ledge", sg, xp)))
            # map light at the slot's forward end (NGX POH 7-19-2: above the CB panels): black bezel ring, lens
            P, Nn = Ml.frame(ul(x0 + 0.012), vl(zs))
            # (black, not bezel_black: consistency_2d3d measures the CB pair's extent on bezel_black)
            out.append((disk(P + 0.0012 * Nn, Nn, 0.011, n=16, r_inner=0.0075), "black"))
            from cad.mesh import revolve
            out.append((revolve([(0.0, 0.0115), (0.004, 0.0105), (0.006, 0.0078), (0.006, 0.0001)], n=16,
                                axis_origin=P, axis_dir=Nn, cap_ends=False), "black"))
            out.append((disk(P + 0.0045 * Nn, Nn, 0.0076, n=16), "lens"))
            # operating-limitations placard, aft of the slot (black, white strokes) [M] AOPA / P1046409
            Mo = lining_map(sg, x1 - 0.06, x1 + 0.10, zs - 0.06, zs + 0.03, 0.0, step=0.01)
            uo, vo = 0.065, 0.012
            out.append(PR.decal_map(Mo, uo, vo, uo + 0.085, vo + 0.048, 0.0, "plate", colour="plate_black",
                                    ink="white", rows=7, cap=1.5, margin=0.05, fill=0.95, fill2=0.95,
                                    seed=("limits", sg)))                    # printed limitations placard (A3)
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


# =====================================================================================================================
# B4  overhead panel + ceiling pod (Pilatus PRO overhead photo, P1046406 through the fitted cabin_fwd_406 camera, NGX
# POH Fig 7-13-1): a raised panel_dark bezel with large corner radii and a 45 deg chamfer down to the anthracite plate
# 6 mm below its face; the white section frames and bus diagram, abstract legend bars (no lettering); ~25 bat-handle
# toggles in the photo's layout (SYSTEM TEST / FUEL PUMPS / ENGINE, ELECTRICAL POWER MANAGEMENT, MASTER POWER,
# EXTERNAL LIGHTS, PASSENGER WARNING), square FIRE WARN / LAMP / STARTER caps, the guarded RUN lever, white LANDING /
# PULSE paddles, the red MASTER POWER guard, corner screws.  Around it a sculpted pod moulding on the headliner with the
# two eyeball outlets aft of the panel; the SAFETY AUTOLAND cup aft of the pod (OVERHEAD autoland).
# =====================================================================================================================
OVH = dict(
    pod_depth=0.026,        # [E] pod face below the crown line (the panel bezel 9 mm proud of it: OVERHEAD depth)
    pod_margin=(0.035, 0.12, 0.055),   # [M] pod beyond the panel: fwd, aft (round the eyeballs), sides
    pod_r=0.070, pod_edge=0.045,       # [E] pod corner radius, its rolled edge width
    frame=0.009, chamfer=0.006, recess=0.006, corner_r=0.024,   # [M] bezel face width (12 -> 9: first-principles judge r1
    #                                                              FP1-08, a thick CAD ring; P1046406 a slim frame), 45 deg
    #                                                              chamfer, plate recess
    # items: (kind, fs, fa) fractions of the plate (port -> starboard, fwd -> aft), photo px / 1110 x 475 [M]
    toggles=((0.108, 0.437), (0.180, 0.437), (0.209, 0.158),                          # fuel LH / RH, ignition
             (0.426, 0.768), (0.569, 0.788), (0.338, 0.585), (0.428, 0.585), (0.655, 0.583),   # stby, cabin, gen 1, tie, gen 2
             (0.341, 0.410), (0.428, 0.410), (0.649, 0.400),                          # bat 1, ext pwr, bat 2
             (0.300, 0.158), (0.345, 0.158), (0.388, 0.158), (0.430, 0.158), (0.560, 0.158),   # wing, nav, beacon, strobe, taxi
             (0.787, 0.179), (0.854, 0.168)),                                         # no smoking, seat belts
    squares=((0.077, 0.745, "panel_dark"), (0.187, 0.745, "panel_dark"), (0.157, 0.172, "panel_silver")),
    paddles=((0.601, 0.147), (0.644, 0.147)),          # LANDING, PULSE RECOG (white)
    run=(0.090, 0.150),                                 # RUN lever under its guard
    master=(0.849, 0.775, 0.106, 0.196), master_k=0.75,  # red guard: centre fs, fa, size fs, fa; guard / frame
    screws=((0.214, 0.913), (0.780, 0.902), (0.243, 0.095), (0.743, 0.091)),
    # white lines: (fs0, fa0, fs1, fa1, dashed)
    lines=((0.248, 0.33, 0.248, 0.95, 0), (0.03, 0.59, 0.248, 0.59, 0), (0.04, 0.33, 0.93, 0.33, 0),
           (0.266, 0.06, 0.266, 0.33, 0), (0.718, 0.06, 0.718, 0.33, 0),
           (0.347, 0.585, 0.649, 0.585, 0), (0.381, 0.40, 0.381, 0.62, 0), (0.381, 0.62, 0.381, 0.77, 1),
           (0.614, 0.40, 0.614, 0.77, 0), (0.347, 0.40, 0.45, 0.40, 0), (0.45, 0.40, 0.60, 0.40, 1),
           (0.60, 0.40, 0.649, 0.40, 0), (0.381, 0.77, 0.426, 0.77, 1), (0.569, 0.77, 0.614, 0.77, 0)),
    boxes=((0.752, 0.126, 0.887, 0.312), (0.626, 0.116, 0.707, 0.280)),
    titles=((0.12, 0.905, 0.12), (0.49, 0.895, 0.22), (0.86, 0.885, 0.11), (0.15, 0.555, 0.10), (0.15, 0.300, 0.07),
            (0.49, 0.300, 0.14), (0.82, 0.290, 0.13)),
    # bat levers thrown fore (-) / aft (+) of the panel normal, deg, per toggle in order (flight deck fix r2 FDO2-07) [M:
    # the Pilatus PRO overhead photo -- most levers thrown aft on the parked aircraft, a few forward]
    toggle_throw=(-28.0, -28.0, 28.0, 28.0, 28.0, -28.0, 28.0, -28.0, 28.0, 28.0, 28.0, 28.0, 28.0, 28.0, 28.0, -28.0,
                  28.0, 28.0),
)


def knurl_ring(o, axis, ref, r, h, flutes=18, depth=0.0004):
    """A knurled bezel ring / nut (explicit segment count): fd_detail_a.knob with flutes."""
    from model import fd_detail_a as A
    return A.knob(o, axis, ref, r, h, n=4 * flutes, flutes=flutes, depth=depth, chamfer=0.15)


def bat_lever(base, ax, side, L, r0=0.0015, bat=(0.0032, 0.0020), n=12):
    """A toggle's bat lever from `base` along unit `ax` (length L): a round stem r0 swelling over its outer half into a
    flattened bat (half-widths bat = across `side`, along the throw plane) with a rounded end -- a closed revolved body
    squashed along the throw plane; it starts 1 mm inside the bushing (open end hidden)."""
    from cad.mesh import revolve
    ax = _unit(np.asarray(ax, float))
    side = _unit(np.asarray(side, float) - ax * np.dot(side, ax))
    nrm = np.cross(ax, side)
    wa, wb = bat
    s = np.r_[-0.001, np.linspace(0.0, L, 9)]
    k = np.clip((s / L - 0.35) / 0.45, 0.0, 1.0) ** 0.8
    r = r0 + (wa - r0) * k
    tip = [(L + wa * math.sin(t), wa * math.cos(t)) for t in np.radians((30.0, 60.0, 80.0))] + [(L + wa, 0.0)]
    prof = [(float(a), float(b)) for a, b in zip(s, r)] + tip
    m = revolve(prof, n=n, axis_origin=base, axis_dir=ax, ref_dir=side)
    d = m.V - base
    sv = d @ ax
    f = 1.0 - (1.0 - wb / wa) * np.interp(sv, s, k)                    # the throw-plane thickness: round stem, flat bat
    m.V = m.V - np.outer((d @ nrm) * (1.0 - f), nrm)
    return m.compute_normals()


def _ovh_frame():
    """Frame of the overhead panel plate: origin at the panel centre on the bezel face, u along the ceiling slope (aft),
    v to port, w down (toward the crew); (hl, hw) the half sizes along u / v."""
    from model import interior as I, flightdeck as FD
    L = FD.lining()
    OV = I.OVERHEAD
    xa, xb = (float(v) for v in OV["x"])
    w_, dep = float(OV["w"]), float(OV["depth"])
    xs = np.linspace(xa, xb, 6)
    slope = float(np.polyfit(xs, L.crown(xs, 0.0), 1)[0])
    xm = 0.5 * (xa + xb)
    u = _unit([1.0, 0.0, slope])
    f = FD.Fr([xm, 0.0, float(L.crown(xm, 0.0)) - dep], u, [0, -1.0, 0])
    return f, 0.5 * (xb - xa) * math.sqrt(1 + slope ** 2), 0.5 * w_, slope


def _rr_loop(hx, hy, r, nc=6, ne=(10, 4)):
    """Rounded rectangle loop (CCW) with nc points per corner and ne = (points along the x edges, along the y edges)
    between them: the same topology for every size (rings can be stripped)."""
    r = max(min(r, hx - 1e-4, hy - 1e-4), 1e-4)
    out = []
    corners = (((1, 1), 0.0), ((-1, 1), 90.0), ((-1, -1), 180.0), ((1, -1), 270.0))
    for k, ((sx, sy), a0) in enumerate(corners):
        c = np.array([sx * (hx - r), sy * (hy - r)])
        arc = [c + r * np.array([math.cos(a), math.sin(a)]) for a in np.radians(np.linspace(a0, a0 + 90.0, nc))]
        out += arc
        (sx2, sy2), a1 = corners[(k + 1) % 4]
        c2 = np.array([sx2 * (hx - r), sy2 * (hy - r)])
        p0 = arc[-1]
        p1 = c2 + r * np.array([math.cos(math.radians(a1)), math.sin(math.radians(a1))])
        n = ne[0] if k % 2 == 0 else ne[1]
        for t in np.linspace(0, 1, n + 2)[1:-1]:
            out.append(p0 + t * (p1 - p0))
    return np.array(out)


def overhead_panel():
    from cad.mesh import cylinder, superellipsoid, box
    from model import flightdeck as FD
    O = OVH
    f, hl, hw, slope = _ovh_frame()
    out = []
    rng = np.random.default_rng(11)
    P = lambda a, s_, c=0.0: f.p(a, -s_, c)                                       # noqa: E731  (s_ to starboard)
    with res.coarse():
        # bezel: outer wall from the pod face up to the face, face ring, 45 deg chamfer to the plate
        pod_gap = float(_ovh_depth()) - O["pod_depth"] + 0.004
        Ro = _rr_loop(hl, hw, O["corner_r"])
        Ri = _rr_loop(hl - O["frame"], hw - O["frame"], O["corner_r"] - O["frame"])
        Rc = _rr_loop(hl - O["frame"] - O["chamfer"], hw - O["frame"] - O["chamfer"],
                      O["corner_r"] - O["frame"] - O["chamfer"])
        ring = lambda R2, c: f.p(R2[:, 0], R2[:, 1], c)                         # noqa: E731
        o = f.o
        walls = [(ring(Ro, -pod_gap), ring(Ro, 0.0), 1.0), (ring(Ro, 0.0), ring(Ri, 0.0), 0.0),
                 (ring(Ri, 0.0), ring(Rc, -O["recess"]), -1.0)]
        for A, B, sgn in walls:
            m = grid_surface(np.stack([A, B], 1), close_u=True)
            if sgn == 0.0:
                out.append((_orient(m, lambda C: np.broadcast_to(f.w, C.shape)), "panel_dark"))
            else:
                out.append((_orient(m, lambda C, s=sgn: s * ((C - o) - np.outer((C - o) @ f.w, f.w)) + 0.3 * f.w),
                            "panel_dark"))
        # the plate lies O recess under the bezel face (w down)
        hli, hwi = hl - O["frame"] - O["chamfer"], hw - O["frame"] - O["chamfer"]
        out.append((_orient(_fan(ring(Rc, -O["recess"]), f.p(0.0, 0.0, -O["recess"])), f.w), "panel_dark"))
        # fractions -> plate coordinates
        A_ = lambda fa: (fa - 0.5) * 2 * (hli - 0.004)                            # noqa: E731
        S_ = lambda fs: (fs - 0.5) * 2 * (hwi - 0.004)                            # noqa: E731
        Pp = lambda fs, fa, c=0.0: P(A_(fa), S_(fs), -O["recess"] + c)           # noqa: E731
        # (first-principles A3) the plate's printing -- section frames, the bus diagram (dashed where drawn so), section
        # titles, a two-line caption at every switch -- one decal over the whole plate: read from the seats with the
        # text's top aft and its right to starboard (looking up, the head tipped back), in plate mm (s, a)
        lw = 0.7                                                       # mm: a silk-screened line (was 1.2 mm strips)
        W2, H2 = 2 * (hwi - 0.002), 2 * (hli - 0.002)                 # the print's extent (m)
        X = lambda fs: 1000 * (S_(fs) + 0.5 * W2)                     # noqa: E731  (mm from the print's port edge)
        Y = lambda fa: 1000 * (A_(fa) + 0.5 * H2)                     # noqa: E731  (mm from its forward edge)
        prims = []
        for fs0, fa0, fs1, fa1, dash in O["lines"]:
            x0_, y0_, x1_, y1_ = X(fs0), Y(fa0), X(fs1), Y(fa1)
            if dash:
                L = math.hypot(x1_ - x0_, y1_ - y0_)
                for t in np.arange(0.0, L, 6.0):
                    t0_, t1_ = t / L, min(t + 3.5, L) / L
                    prims.append(("seg", x0_ + t0_ * (x1_ - x0_), y0_ + t0_ * (y1_ - y0_), x0_ + t1_ * (x1_ - x0_),
                                  y0_ + t1_ * (y1_ - y0_), lw))
            else:
                prims.append(("seg", x0_, y0_, x1_, y1_, lw))
        for fs0, fa0, fs1, fa1 in O["boxes"]:
            x0_, y0_, x1_, y1_ = X(fs0), Y(fa0), X(fs1), Y(fa1)
            prims += [("seg", x0_, y0_, x0_, y1_, lw), ("seg", x1_, y0_, x1_, y1_, lw), ("seg", x0_, y0_, x1_, y0_, lw),
                      ("seg", x0_, y1_, x1_, y1_, lw)]
        for k_, (fs, fa, wfr) in enumerate(O["titles"]):              # section titles (pseudo-text)
            w = 1000 * wfr * 2 * hwi
            prims.append(("words", X(fs) - 0.5 * w, Y(fa) - 3.0, X(fs) + 0.5 * w, Y(fa) + 3.0, 1, 2.6, ("ovt", k_)))
        for k_, (fs, fa) in enumerate(O["toggles"] + O["paddles"]):   # switch captions: two lines aft of the switch
            prims.append(("words", X(fs) - 11.0, Y(fa) + 13.0, X(fs) + 11.0, Y(fa) + 22.0, 2, 1.7, ("ovs", k_)))
            prims.append(("words", X(fs) - 8.0, Y(fa) - 21.0, X(fs) + 8.0, Y(fa) - 16.0, 1, 1.6, ("ovo", k_)))
        fr_ = FD.Fr(f.o, -f.v, f.u, f.w)
        out.append(PR.decal(fr_, -0.5 * W2, -0.5 * H2, 0.5 * W2, 0.5 * H2, -O["recess"] + PR.LIFT, "vector",
                            prims=tuple(prims)))
        # toggles (flight deck fix r2 FDO2-07: from the seats the first build's levers -- 17 mm straight down with a ball
        # end -- read as hex nuts with small balls lying flat): a knurled bezel ring and a chrome hex nut on the bushing,
        # a chrome BAT lever ~15 mm proud thrown fore or aft (O toggle_throw), swelling into a flattened bat
        for k, (fs, fa) in enumerate(O["toggles"]):
            b = Pp(fs, fa)
            out.append((knurl_ring(b - 0.0004 * f.w, f.w, f.u, 0.0060, 0.0022, flutes=18), "metal_dark"))
            out.append((cylinder(b + 0.0016 * f.w, b + 0.0044 * f.w, 0.0045, n=6), "chrome_trim"))
            out.append((cylinder(b + 0.0040 * f.w, b + 0.0062 * f.w, 0.0026, n=12), "chrome_trim"))
            th = math.radians(O["toggle_throw"][k % len(O["toggle_throw"])])
            out.append((bat_lever(b + 0.0062 * f.w, math.cos(th) * f.w + math.sin(th) * f.u, f.v, 0.0145),
                        "chrome_trim"))
        # square push buttons (FDO2-07: a lens face in a dark rim, not a plain extruded box): the black frame, the
        # cap's dark rim, its smoked lens (unlit) and a legend stroke
        for fs, fa, mat in O["squares"]:
            c = Pp(fs, fa)
            out.append((box(c + 0.002 * f.w, (0.020, 0.020, 0.004), R=f.R), "bezel_black"))
            out.append((box(c + 0.0050 * f.w, (0.0155, 0.0155, 0.003), R=f.R), "black"))
            lens = "annun_off_amber" if mat == "panel_silver" else "annun_off_red"
            out.append((box(c + 0.0066 * f.w, (0.0125, 0.0125, 0.0008), R=f.R), lens))
            out.append(PR.decal(FD.Fr(c, -f.v, f.u, f.w), -0.0050, -0.0050, 0.0050, -0.0010, 0.0070 + PR.LIFT, "words",
                                rows=1, cap=1.3, colour="white", seed=("ovsq", fs, fa)))     # printed on the lens (A3)
        for fs, fa in O["paddles"]:
            c = Pp(fs, fa)
            out.append((cylinder(c - 0.0004 * f.w, c + 0.004 * f.w, 0.0046, n=6), "metal_dark"))
            out.append((box(c + 0.010 * f.w, (0.010, 0.013, 0.012), R=f.R), "yoke_white"))
        fs, fa = O["run"]                                                           # RUN lever and its guard
        c = Pp(fs, fa)
        out.append((box(c + 0.006 * f.w, (0.036, 0.016, 0.010), R=f.R), "bezel_black"))
        out.append((box(c + 0.014 * f.w - 0.004 * f.u, (0.022, 0.011, 0.012), R=f.R), "panel_silver"))
        fs, fa, ws_, wa_ = O["master"]                                              # MASTER POWER guard
        c = Pp(fs, fa)
        # (flight deck fix FDY r1 FIDY1-07: the full-size saturated red block read large and loud from the cabin; the
        # Pilatus overhead photo shows a smaller darker-red guard sitting in a black recess frame: the frame the old
        # footprint 0.7-3.7 mm proud of the plate, the guard O["master_k"] of it standing 2.8 mm out of the frame, in the dim
        # placard red)
        k_ = O["master_k"]
        out.append((box(c + 0.0022 * f.w, (wa_ * 2 * hli, ws_ * 2 * hwi, 0.003), R=f.R), "bezel_black"))
        out.append((box(c + 0.0045 * f.w, (k_ * wa_ * 2 * hli, k_ * ws_ * 2 * hwi, 0.004), R=f.R), "placard_red_dim"))
        out.append((cylinder(c + 0.006 * f.w, c + 0.014 * f.w + 0.003 * f.u, 0.0016, n=8), "panel_silver"))
        out.append((box(c + 0.010 * f.w - 0.009 * f.u, (0.005, 0.017, 0.008), R=f.R), "paint_red"))
        for fs, fa in O["screws"]:
            c = Pp(fs, fa)
            out.append((superellipsoid(c, (0.0035, 0.0035, 0.0015), (1, 1), 4, 8), "metal_dark"))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


def _fan(ring, tip):
    n = len(ring)
    i = np.arange(n)
    return Mesh(np.vstack([ring, np.asarray(tip, float)[None]]), np.stack([i, (i + 1) % n, np.full(n, n)], 1))


def _ovh_depth():
    from model import interior as I
    return float(I.OVERHEAD["depth"])


def overhead_pod():
    """The sculpted pod moulding round the overhead panel on the headliner (lining_flightdeck): a face in the panel's
    plane (OVH pod_depth below the crown line) rolled up into the headliner at its fore / aft ends and blended into it
    (smooth minimum) where the headliner curves down below that plane at the sides; the two eyeball outlets on its aft
    part.  The flat face under the panel keeps the headliner's 28 mm fall across the 0.47 m panel from poking through
    the plate."""
    from model import interior as I, flightdeck as FD
    from cad.mesh import revolve, superellipsoid, trim
    L = FD.lining()
    O = OVH
    OV = I.OVERHEAD
    xa, xb = (float(v) for v in OV["x"])
    mf, ma, ms = O["pod_margin"]
    x0, x1 = xa - mf, xb + ma
    hy = 0.5 * float(OV["w"]) + ms
    R, D = O["pod_edge"], O["pod_depth"]
    xs_fit = np.linspace(xa, xb, 6)
    cf = np.polyfit(xs_fit, L.crown(xs_fit, 0.0), 1)
    k = 0.010                                                       # smooth-minimum blend width

    def z_pod(X, Y):
        e = np.minimum(X - x0, x1 - X)
        rim = np.sin(0.5 * np.pi * np.clip(e / R, 0.0, 1.0)) ** 1.3
        hl = L.crown(X, Y) - 0.0008
        face = np.polyval(cf, X) - D * rim - 0.0008 * (1 - rim)
        face = np.minimum(face, np.polyval(cf, X) - 0.0008)
        h = np.clip(0.5 + 0.5 * (hl - face) / k, 0.0, 1.0)
        return face * h + hl * (1 - h) - k * h * (1 - h)              # smooth min(hl, face)
    out = []
    with res.coarse():
        xs = np.unique(np.r_[np.linspace(x0, x0 + R, 7), np.linspace(x0 + R, x1 - R, 12), np.linspace(x1 - R, x1, 7)])
        ys = np.linspace(-hy, hy, 41)
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        Z = z_pod(X, Y)
        G = np.stack([X, Y, Z], -1)
        m = grid_surface(G)
        depth = (L.crown(m.V[:, 0], m.V[:, 1]) - m.V[:, 2]).ravel()
        m = trim(m, depth - 0.0014, "positive").compact()            # off where it lies on the headliner
        out.append((_orient(m, lambda C: np.broadcast_to([0, 0, -1.0], C.shape)), "lining_flightdeck"))
        # eyeball outlets on the pod's aft part (NGX S15: STA 4.14, BL -0.05 / +0.07; P1046406)
        for by in (-0.060, 0.060):
            x = xb + 0.060
            z = float(z_pod(np.array(x), np.array(by)))
            o = np.array([x, by, z])
            # (first-principles judge r1 FP1-08: the outlets read oversized -- x0.8, a louvred rim of 12 grooves)
            k8 = 0.8
            ring = revolve([(0.0008, k8 * 0.025), (0.004, k8 * 0.0245), (0.006, k8 * 0.0215), (0.0062, k8 * 0.0205),
                            (0.007, k8 * 0.020), (0.007, k8 * 0.0185), (0.0015, k8 * 0.017)],
                           n=36, axis_origin=o, axis_dir=[0, 0, -1.0], cap_ends=False)
            ang_ = np.arctan2(ring.V[:, 1] - by, ring.V[:, 0] - x)
            rad_ = np.hypot(ring.V[:, 1] - by, ring.V[:, 0] - x)
            groove = 1.0 - 0.035 * (0.5 + 0.5 * np.cos(12 * ang_)) * (rad_ > k8 * 0.0195)
            ring.V[:, 0] = x + (ring.V[:, 0] - x) * groove
            ring.V[:, 1] = by + (ring.V[:, 1] - by) * groove
            # draped on the pod face (its aft half lies on the rim's roll-up into the headliner, up to 2 mm higher)
            ring.V[:, 2] += z_pod(ring.V[:, 0], ring.V[:, 1]) - z
            out.append((ring, "bezel_black"))
            out.append((superellipsoid(o + [0.0, 0.0, -0.002], (k8 * 0.0155,) * 3, (1, 1), 8, 14), "black"))
            out.append((revolve([(0.0, k8 * 0.0072), (k8 * 0.008, k8 * 0.0068), (k8 * 0.0105, k8 * 0.0045)], n=12,
                                axis_origin=o + [0, 0, -0.008], axis_dir=_unit([0.25, 0.0, -1.0]), cap_ends=True),
                        "bezel_black"))
    return out


# =====================================================================================================================
# B5  centre post: the post moulding itself is the two windshield reveals' post edges and the lining strip between
# them (90 mm at the glass, P1046408); on it the grab handle from the overhead pod's forward edge down to its V end
# bracket (POH Fig 7-19-1 key 24; P1046406 / 08: satin light grey), the deviation-card holder and the E2B-type magnetic
# compass under it (black housing, recessed dark card with fine white strokes, red lubber line) [M: PRO simulator
# photo, P1046408 V bracket at WL ~2.43-2.46 through the fitted camera]
# =====================================================================================================================
POST = dict(
    bar_r=0.0115,                   # [M] grab handle: a round satin bar, ~1/4 of the post's width at the glass (P1046406
    #                                 / 08 / 10, the Pilatus PRO overhead photo: light satin grey, a dark screw hole
    #                                 near its top)
    stand=0.026,                    # [M] bar axis off the post moulding
    top_x=3.835, end_z=2.435,       # [M] handle from the pod's forward edge down to its V end fitting at this WL
    # V end fitting (P1046408 / 10, PRO simulator): a faceted satin block twice the bar's width, its top cut into a
    # V round the bar, its aft face two planes meeting on the centre line; on a rounded mounting plate on the post
    vend=(0.027, 0.020, 0.026, 0.012, 0.040, 0.30),   # half-width, bottom / top of the wings below / above the bar's
    #                                                    end, notch depth, ridge off the post, ridge fall per m across
    plate=(0.034, 0.042, 0.006, 0.010, 0.005),          # [M] plate half-width, half-length, centre above the bar's end,
    #                                                    corner radius, proud of the post
    card=(0.020, 0.014),            # [M] deviation-card holder half sizes (across, along the post): PRO simulator photo
    compass=(0.026, 0.028, 0.024),  # [E] housing half sizes (across, along the post, off the post): E2B ~2.5 in
    compass_z=2.372,                # [M] housing centre WL (DETAIL compass_z 2.380 kept within 10 mm): the PRO
    #                                 simulator photo's order down the post -- handle, V fitting, card, compass
)


def _post_line(x0, x1, n=40, off=0.0):
    """Points on the windshield centre post's moulding (the lining crown at BL 0) from STA x0 to x1, its inward
    normals (into the cabin) and the tangents; `off` inboard of the moulding."""
    from model import flightdeck as FD
    L = FD.lining()
    xs = np.linspace(x0, x1, n)
    zs = L.crown(xs, 0.0)
    dz = np.gradient(zs, xs)
    T = _unit(np.stack([np.ones_like(xs), np.zeros_like(xs), dz], 1))
    Nin = _unit(np.stack([dz, np.zeros_like(xs), -np.ones_like(xs)], 1))
    Nin *= np.sign(-Nin[:, 2:3])
    P = np.stack([xs, np.zeros_like(xs), zs], 1) + off * Nin
    return P, Nin, T


def _x_at_post_z(z):
    from model import flightdeck as FD
    L = FD.lining()
    xs = np.linspace(3.25, 4.0, 1501)
    return float(xs[np.argmin(np.abs(L.crown(xs, 0.0) - z))])


def post_fittings():
    from cad.mesh import cylinder
    from model import flightdeck as FD
    q = POST
    out = []
    rng = np.random.default_rng(5)
    with res.coarse():
        xe = _x_at_post_z(q["end_z"])
        P, Nin, T = _post_line(xe, q["top_x"], 36, off=q["stand"])
        r = q["bar_r"]
        th = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        G = np.stack([P[i] + r * np.cos(th)[:, None] * [0, 1.0, 0] + r * np.sin(th)[:, None] * Nin[i]
                      for i in range(len(P))])
        bar = grid_surface(G, close_v=True)
        bar = _orient(bar, lambda C: C - P[np.argmin(np.linalg.norm(C[:, None] - P[None], axis=2), 1)])
        out.append((bar, "panel_silver"))
        out.append((_orient(planar_cap(G[-1], T[-1]), T[-1]), "panel_silver"))
        out.append((_orient(planar_cap(G[0], -T[0]), -T[0]), "panel_silver"))
        # standoff at the top (into the pod) and the dark screw hole on the bar's aft face below it
        i = len(P) - 4
        a = P[i] - (q["stand"] + 0.004) * Nin[i]
        out.append((cylinder(a, P[i], 0.008, n=10), "panel_silver"))
        from cad.mesh import disk
        j = len(P) - 9
        out.append((disk(P[j] + (r + 0.0003) * Nin[j], Nin[j], 0.0033, n=10), "black"))
        # mounting plate on the post behind the V end fitting (a rounded pad, 5 mm proud)
        hwv, vb, vt, vn, wr, fall = q["vend"]
        pw, pl, pc, pr, pp = q["plate"]
        Pe, Ne, Te = _post_line(xe - 0.002, xe + 0.002, 3)
        Pe, Ne, Te = Pe[1], Ne[1], Te[1]
        fr = FD.Fr(Pe, [0, 1.0, 0], Te)
        if np.dot(fr.w, Ne) < 0:
            fr = FD.Fr(Pe, [0, -1.0, 0], Te)
        Lp = FD.rrect_loop(pw, pl, pr, 5, cy=pc)
        A, B = fr.p(Lp[:, 0], Lp[:, 1], -0.002), fr.p(Lp[:, 0], Lp[:, 1], pp)
        cen = fr.p(0.0, pc, 0.0)
        out.append((_orient(grid_surface(np.stack([A, B], 1), close_u=True),
                            lambda C, c=cen: (C - c) - np.outer((C - c) @ fr.w, fr.w)), "panel_grey"))
        out.append((_orient(planar_cap(B, fr.w), fr.w), "panel_grey"))
        # V end fitting: outline (across, along the post) round the bar's end, the aft face two planes on the ridge
        Vo = np.array([[0.0, -vb - 0.005], [hwv, -vb], [hwv, vt], [r + 0.001, vn], [0.0, vn],
                       [-(r + 0.001), vn], [-hwv, vt], [-hwv, -vb]])
        wf = lambda uu: wr - fall * np.abs(uu)                                   # noqa: E731
        back = fr.p(Vo[:, 0], Vo[:, 1], pp - 0.001)
        front = fr.p(Vo[:, 0], Vo[:, 1], wf(Vo[:, 0]))
        cv = fr.p(0.0, 0.0, 0.5 * (pp + wr))
        walls = grid_surface(np.stack([back, front], 1), close_u=True)
        walls = _orient(walls, lambda C, c=cv: (C - c) - np.outer((C - c) @ fr.w, fr.w))
        from model.flightdeck import _flat
        out.append((_flat(walls), "panel_silver"))
        for half in ([0, 1, 2, 3, 4], [4, 5, 6, 7, 0]):
            Q = front[half]
            nq = np.cross(Q[1] - Q[0], Q[2] - Q[0])
            nq = nq if np.dot(nq, fr.w) > 0 else -nq
            out.append((_flat(_orient(planar_cap(Q, _unit(nq)), _unit(nq))), "panel_silver"))
        out.append((fr.disk(0.0, -vb + 0.002, 0.0022, wf(0.0) + 0.0002, n=8), "black"))      # screw hole
        # deviation-card holder and compass below the bracket, on the post moulding
        zc = q["compass_z"]
        xc = _x_at_post_z(zc)
        Pc, Nc, Tc = _post_line(xc - 0.002, xc + 0.002, 3)
        Pc, Nc, Tc = Pc[1], Nc[1], Tc[1]
        cw, cl, cd = q["compass"]
        # the housing faces aft toward the crew (10 deg down), on a short bracket from the post
        face = _unit([math.cos(math.radians(10.0)), 0.0, -math.sin(math.radians(10.0))])
        upv = _unit(np.cross(face, [0, 1.0, 0]))
        if upv[2] < 0:
            upv = -upv
        o_c = Pc + (cd + 0.010) * Nc
        fc = FD.Fr(o_c - cd * face, [0, 1.0, 0], upv)
        if np.dot(fc.w, face) < 0:
            fc = FD.Fr(o_c - cd * face, [0, -1.0, 0], upv)
        out.append((cylinder(Pc - 0.002 * Nc, o_c, 0.007, n=8), "black"))
        out.append((fc.se(0, 0, 0, (cw, cl, cd + 0.002), (0.35, 0.35), (8, 16)), "black"))
        # round front bezel (PRO simulator photo: a round black bezel with four screws, a square card window in it)
        from cad.mesh import revolve
        cf = cd + 0.0016
        out.append((revolve([(0.0, 0.0250), (0.0022, 0.0246), (0.0034, 0.0226), (0.0036, 0.0200), (0.0028, 0.0186)],
                            n=24, axis_origin=fc.p(0, 0, cf), axis_dir=fc.w, cap_ends=False), "bezel_black"))
        out.append((fc.disk(0, 0, 0.0190, cf + 0.0006, n=24), "bezel_black"))
        win = FD.rrect_loop(0.0125, 0.0105, 0.003, 4)
        out.append((_orient(planar_cap(fc.p(win[:, 0], win[:, 1], cf + 0.0012), fc.w), fc.w), "screen"))
        marks = []
        for k, uu in enumerate(np.linspace(-0.0105, 0.0105, 15)):
            hgt = 0.0045 if k % 5 == 2 else 0.0022
            marks.append((uu - 0.00022, -0.0015 - hgt, uu + 0.00022, -0.0015))
        marks += [(-0.0095 + 0.0075 * j, 0.0020, -0.0095 + 0.0075 * j + 0.0035, 0.0034) for j in range(3)]  # numerals
        V, F = [], []
        for u0, v0, u1, v1 in marks:
            k = len(V)
            V += [fc.p(u0, v0, cf + 0.0017), fc.p(u1, v0, cf + 0.0017), fc.p(u1, v1, cf + 0.0017),
                  fc.p(u0, v1, cf + 0.0017)]
            F += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
        out.append((_orient(Mesh(np.array(V), np.array(F)), lambda C: np.broadcast_to(fc.w, C.shape)), "light_white"))
        out.append((fc.rect(-0.0003, -0.0095, 0.0003, 0.0095, cf + 0.0021), "light_red"))       # lubber line
        for su, sv in ((-1, -1), (1, -1), (-1, 1), (1, 1)):                                    # bezel screws
            out.append((fc.se(su * 0.0155, sv * 0.0155, cf + 0.0036, (0.0016, 0.0016, 0.0008), (1, 1), (4, 6)),
                        "metal_dark"))
        # card holder between the bracket and the compass: a black frame with a light card (abstract table strokes)
        zh = 0.5 * (zc + cl * Tc[2] + q["end_z"] - 0.024)
        xh = _x_at_post_z(zh)
        Ph, Nh, Th = _post_line(xh - 0.002, xh + 0.002, 3)
        Ph, Nh, Th = Ph[1], Nh[1], Th[1]
        fh = FD.Fr(Ph + 0.003 * Nh, [0, 1.0, 0], Th)
        if np.dot(fh.w, Nh) < 0:
            fh = FD.Fr(Ph + 0.003 * Nh, [0, -1.0, 0], Th)
        cw2, cl2 = q["card"]
        out.append((fh.box(0, 0, 0.0, (2 * cw2, 2 * cl2, 0.006)), "black"))
        out.append((fh.rect(-cw2 + 0.002, -cl2 + 0.002, cw2 - 0.002, cl2 - 0.002, 0.0032), "legend_lit"))
        # the deviation table: 3 rule lines and 5 column lines, fine (0.3 mm)
        lines = [(-cw2 + 0.003, v - 0.00015, cw2 - 0.003, v + 0.00015) for v in np.linspace(-cl2 + 0.004, cl2 - 0.004, 3)]
        lines += [(u - 0.00015, -cl2 + 0.003, u + 0.00015, cl2 - 0.003) for u in np.linspace(-cw2 + 0.009, cw2 - 0.009, 5)]
        V, F = [], []
        for u0, v0, u1, v1 in lines:
            k = len(V)
            V += [fh.p(u0, v0, 0.0036), fh.p(u1, v0, 0.0036), fh.p(u1, v1, 0.0036), fh.p(u0, v1, 0.0036)]
            F += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
        out.append((_orient(Mesh(np.array(V), np.array(F)), lambda C: np.broadcast_to(fh.w, C.shape)), "black"))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


# =====================================================================================================================
# B9  flight-deck headliner: dome / utility lights (NGX S15: STA 4.21, |BL| 0.31-0.33) and round loudspeaker grilles
# (|BL| 0.43) aft of the overhead; Rosen-type sun visors stowed on their rails above each side window (rail STA
# 3.97-4.30, |BL| 0.36-0.49, WL 2.53-2.56, visor ~0.33 long; AOPA visor photo: smoked panel with a satin edge on a
# black rail, the pivot arm and knob at the forward end)
# =====================================================================================================================
HEAD = dict(
    dome=((4.215, 0.320, 0.021),), speaker=((4.215, 0.430, 0.032),),
    # the PRO's centre dome light in a dark square bezel at port, mirroring the SAFETY AUTOLAND cup (P1046406 through
    # the cabin_fwd_406 camera: a round lens in a dark rectangle left of the two eyeballs) [M]
    dome_c=(4.230, -0.170, 0.070),
    visor_x=(3.975, 4.300), visor_bl=(0.375, 0.485), visor_off=0.0085,
    # [M] AOPA visor photo: the forward end nearly round, the aft corners ~R 30; a satin rim ~5 mm wide round the
    # smoked panel (face 1.5 mm below it, its outer wall 3 mm up toward the headliner); the black arm ~1/5 of the
    # visor's width along its outboard edge, 3 mm below the rim, from the pivot clamp at the forward end
    visor_r=(0.045, 0.030), visor_rim=(0.005, 0.0015, 0.003), visor_bar=(0.022, 0.003),
)


def _ceiling_frame(x, y):
    """Frame on the headliner at (x, y): origin on the lining, w down along its normal (into the cabin)."""
    from model import flightdeck as FD
    L = FD.lining()
    e = 0.004
    z = float(L.crown(x, y))
    dzx = float(L.crown(x + e, y) - L.crown(x - e, y)) / (2 * e)
    dzy = float(L.crown(x, abs(y) + e) - L.crown(x, abs(y) - e)) / (2 * e) * np.sign(y if y else 1.0)
    nd = _unit([dzx, dzy, -1.0])
    ux = _unit([1.0, 0.0, dzx])
    return FD.Fr(np.array([x, y, z]), ux, np.cross(nd, ux))


def headliner_fittings():
    from cad.mesh import revolve, disk
    out = []
    with res.coarse():
        for sg in (-1, 1):
            for x, bl, r in HEAD["dome"]:
                f = _ceiling_frame(x, sg * bl)
                if np.dot(f.w, [0, 0, -1.0]) < 0:
                    f = FD_flip(f)
                out.append((revolve([(0.0008, r + 0.006), (0.004, r + 0.005), (0.006, r + 0.002), (0.006, r - 0.001),
                                     (0.004, r - 0.002)], n=20, axis_origin=f.o, axis_dir=f.w,
                                    cap_ends=False), "bezel_black"))
                out.append((disk(f.o + 0.0045 * f.w, f.w, r - 0.0015, n=20), "lens"))
                out.append((disk(f.o + 0.0030 * f.w, f.w, r - 0.0015, n=20), "psu_panel"))
            if sg < 0:
                x, bl, sz = HEAD["dome_c"]
                f = _ceiling_frame(x, bl)
                if np.dot(f.w, [0, 0, -1.0]) < 0:
                    f = FD_flip(f)
                from model import flightdeck as FD
                O2 = FD.rrect_loop(0.5 * sz, 0.5 * sz, 0.012, 4)
                In2 = FD.rrect_loop(0.5 * sz - 0.010, 0.5 * sz - 0.010, 0.006, 4)
                ring = lambda R2, c: f.p(R2[:, 0], R2[:, 1], c)                 # noqa: E731
                for A, B, ref in ((ring(O2, -0.004), ring(O2, 0.010), lambda C: C - f.o),
                                  (ring(O2, 0.010), ring(In2, 0.010), f.w),
                                  (ring(In2, 0.010), ring(In2, 0.003), lambda C: f.o - C)):
                    m = grid_surface(np.stack([A, B], 1), close_u=True)
                    out.append((_orient(m, ref), "panel_dark"))
                out.append((_orient(_fan(ring(In2, 0.003), f.p(0, 0, 0.003)), f.w), "bezel_black"))
                out.append((revolve([(0.0, 0.020), (0.003, 0.019), (0.005, 0.016), (0.005, 0.0001)], n=20,
                                    axis_origin=f.o + 0.003 * f.w, axis_dir=f.w, cap_ends=False), "black"))
                out.append((disk(f.o + 0.0085 * f.w, f.w, 0.0155, n=20), "lens"))
                out.append((disk(f.o + 0.0070 * f.w, f.w, 0.0155, n=20), "psu_panel"))
            for x, bl, r in HEAD["speaker"]:
                f = _ceiling_frame(x, sg * bl)
                if np.dot(f.w, [0, 0, -1.0]) < 0:
                    f = FD_flip(f)
                out.append((revolve([(0.0008, r + 0.004), (0.003, r + 0.003), (0.004, r)], n=24,
                                    axis_origin=f.o, axis_dir=f.w, cap_ends=False), "bezel_black"))
                out.append((disk(f.o + 0.0025 * f.w, f.w, r, n=24), "black"))
                for k, rr in enumerate(np.linspace(0.006, r - 0.004, 5)):
                    out.append((disk(f.o + 0.0032 * f.w, f.w, rr + 0.0012, n=24, r_inner=rr), "metal_dark"))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


def FD_flip(f):
    from model import flightdeck as FD
    return FD.Fr(f.o, f.u, -f.v)


def _visor_rows(x0, x1, y0, y1, rf, ra, n_end=8, n_mid=9):
    """Rows of a rounded-rectangle outline in (x, |y|): row stations x and the span ylo..yhi per row (corner radius rf
    at the forward end, ra at the aft end; the rows crowd into the end radii so the grid's border IS the outline)."""
    th = np.linspace(0.0, 0.5 * np.pi, n_end + 1)
    xf, df = x0 + rf * (1 - np.cos(th)), rf * (1 - np.sin(th))
    xm = np.linspace(x0 + rf, x1 - ra, n_mid)[1:-1]
    xa, da = (x1 - ra * (1 - np.cos(th)))[::-1], (ra * (1 - np.sin(th)))[::-1]
    xs = np.r_[xf, xm, xa]
    d = np.r_[df, np.zeros(len(xm)), da]
    return xs, y0 + d, y1 - d


def _inset2(L2, t):
    """2-D closed loop moved t inward (vertex normals from the neighbours; counter-clockwise or not)."""
    tg = np.roll(L2, -1, 0) - np.roll(L2, 1, 0)
    nrm = np.c_[tg[:, 1], -tg[:, 0]]
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    c = L2.mean(0)
    s = np.sign(np.sum(nrm * (L2 - c), 1))[:, None]                       # outward
    return L2 - t * s * nrm


def visors():
    """Stowed sun visors on their rails above each side window (AOPA visor photo): a smoked panel ('fdb_visor') with
    rounded ends -- nearly round forward, R 30 aft -- in a 5 mm satin rim, carried by a flat black arm along its
    outboard edge (a satin slot line and the slider button on it) from the pivot clamp on a round base plate at the
    forward end."""
    from cad.mesh import cylinder, superellipsoid, revolve, disk
    from model import flightdeck as FD
    L = FD.lining()
    q = HEAD
    out = []
    x0, x1 = q["visor_x"]
    y0, y1 = q["visor_bl"]
    rf, ra = q["visor_r"]
    ov = q["visor_off"]
    rim_w, rim_drop, rim_h = q["visor_rim"]
    bar_w, bar_drop = q["visor_bar"]
    down = lambda C: np.broadcast_to([0, 0, -1.0], C.shape)                 # noqa: E731

    def lift(X, Y, off, sg):
        return np.stack([X, sg * Y, L.crown(X, Y) - off], -1)

    with res.coarse():
        for sg in (-1, 1):
            # smoked panel: rows of the rounded outline, visor_off below the headliner
            xs, ylo, yhi = _visor_rows(x0, x1, y0, y1, rf, ra)
            V = np.linspace(0.0, 1.0, 7)
            X = np.repeat(xs[:, None], len(V), 1)
            Y = ylo[:, None] + (yhi - ylo)[:, None] * V[None]
            out.append((_orient(grid_surface(lift(X, Y, ov, sg)), down), "fdb_visor"))
            # satin rim: a face ring rim_drop below the panel over its outer rim_w, an outer wall up toward the
            # headliner (rim_h) and a short inner lip down onto the panel
            L2 = np.vstack([np.c_[xs, ylo], np.c_[np.full(len(V) - 2, xs[-1]), Y[-1, 1:-1]], np.c_[xs[::-1], yhi[::-1]],
                            np.c_[np.full(len(V) - 2, xs[0]), Y[0, 1:-1][::-1]]])
            I2 = _inset2(L2, rim_w)
            c2 = L2.mean(0)
            Lo = lambda P2, off: lift(P2[:, 0], P2[:, 1], off, sg)            # noqa: E731
            cen3 = Lo(c2[None], ov)[0]
            outward = lambda C, c=cen3: (C - c) * [1.0, 1.0, 0.0]          # noqa: E731
            face = grid_surface(np.stack([Lo(L2, ov + rim_drop), Lo(I2, ov + rim_drop)], 1), close_u=True)
            out.append((_orient(face, down), "panel_silver"))
            wall = grid_surface(np.stack([Lo(L2, ov - rim_h), Lo(L2, ov + rim_drop)], 1), close_u=True)
            out.append((_orient(wall, outward), "panel_silver"))
            lip = grid_surface(np.stack([Lo(I2, ov + rim_drop), Lo(I2, ov - 0.0003)], 1), close_u=True)
            out.append((_orient(lip, lambda C, c=cen3: (c - C) * [1.0, 1.0, 0.0]), "panel_silver"))
            # black arm along the outboard edge: a flat bar bar_drop below the panel, walls up onto it, end caps
            xa_, xb_ = x0 - 0.012, x1 - 0.045
            yb0, yb1 = y1 - bar_w + 0.004, y1 + 0.004
            xb = np.linspace(xa_, xb_, 16)
            Xb, Yb = np.meshgrid(xb, np.linspace(yb0, yb1, 5), indexing="ij")      # follows the crown across
            top_off, bot_off = ov + rim_drop + bar_drop, ov - 0.001
            out.append((_orient(grid_surface(lift(Xb, Yb, top_off, sg)), down), "black"))
            for yy, s_ in ((yb0, -1.0), (yb1, 1.0)):
                A = lift(xb, np.full_like(xb, yy), bot_off, sg)
                B = lift(xb, np.full_like(xb, yy), top_off, sg)
                out.append((_orient(grid_surface(np.stack([A, B], 1)),
                                    lambda C, s=s_ * sg: np.broadcast_to([0, s, 0], C.shape)), "black"))
            for xx, s_ in ((xa_, -1.0), (xb_, 1.0)):
                Q = np.vstack([lift(np.full(2, xx), np.array([yb0, yb1]), bot_off, sg),
                               lift(np.full(2, xx), np.array([yb1, yb0]), top_off, sg)])
                out.append((_orient(planar_cap(Q, [s_, 0, 0]), [s_, 0, 0]), "black"))
            # slot line and the slider button on the bar
            xl = np.linspace(x0 + 0.060, xb_ - 0.025, 10)
            ym = 0.5 * (yb0 + yb1)
            Xl, Yl = np.meshgrid(xl, [ym - 0.0012, ym + 0.0012], indexing="ij")
            out.append((_orient(grid_surface(lift(Xl, Yl, top_off + 0.0006, sg)), down), "panel_silver"))
            xk = x0 + 0.115
            pk = lift(np.array([xk]), np.array([ym]), top_off, sg)[0]
            out.append((revolve([(0.0, 0.0042), (0.0012, 0.0040), (0.0020, 0.0030), (0.0022, 0.0001)], n=10,
                                axis_origin=pk, axis_dir=[0, 0, -1.0], cap_ends=False), "panel_silver"))
            # pivot: round base plate on the headliner, a screw, the clamp block between it and the arm's end
            xp, yp = x0 - 0.004, y1 - 0.004
            f = _ceiling_frame(xp, sg * yp)
            if np.dot(f.w, [0, 0, -1.0]) < 0:
                f = FD_flip(f)
            out.append((revolve([(-0.0005, 0.0150), (0.0018, 0.0148), (0.0028, 0.0135), (0.0030, 0.0001)], n=16,
                                axis_origin=f.o, axis_dir=f.w, cap_ends=False), "black"))
            out.append((disk(f.o + 0.0032 * f.w, f.w, 0.0030, n=8), "panel_silver"))
            pc = f.o + 0.5 * (0.002 + top_off) * f.w + [0.008, -sg * 0.004, 0.0]
            out.append((superellipsoid(pc, (0.011, 0.0085, 0.5 * (top_off - 0.002) + 0.0005), (0.5, 0.5), 6, 10),
                        "black"))
            out.append((cylinder(pc + [0.0, -sg * 0.0095, 0.0], pc + [0.0, sg * 0.0095, 0.0], 0.0022, n=8),
                        "panel_silver"))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


# =====================================================================================================================
# B6  side consoles / sidewall: padded leather armrest pad on the console top aft of the CB panels, a map pocket with an
# elastic edge in the console's inboard face, the keypad at its forward end (P1046409), a sidewall eyeball outlet aft of
# the CB panels; the cup holders / USB of model/flightdeck._consoles stay
# =====================================================================================================================
CONS = dict(
    pad_x=(4.180, 4.400), pad_t=0.012,          # [E] armrest pad on the console top, aft of the CB pair
    pocket=(3.980, 4.330, 0.075, 0.200),        # [E] map pocket on the inboard face: x0, x1, top / bottom below the top
    keypad=(3.700, 0.060),                      # [M] keypad centre x, its centre below the console top (P1046409)
    vent=(4.290, 0.640, 0.020),                 # [E] sidewall eyeball: x, height above the floor, radius
)


def console_fittings(fl):
    from model import interior as I, flightdeck as FD
    from cad.mesh import revolve, superellipsoid, cylinder
    SC = I.SIDE_CONSOLE
    L = FD.lining()
    q = CONS
    zt = fl + float(SC["top_h"])
    yi = float(SC["inner_bl"])
    out = []
    with res.coarse():
        for sg in (-1, 1):
            # armrest pad: a leather pillow on the console top, stitched round its top
            xa, xb = q["pad_x"]
            xm = 0.5 * (xa + xb)
            yo = float(L.hw(xm, zt)) - 0.004
            yc, hw = 0.5 * (yi + 0.004 + yo), 0.5 * (yo - yi - 0.004)
            o = np.array([xm, sg * yc, zt + 0.5 * q["pad_t"] - 0.002])
            out.append((superellipsoid(o, (0.5 * (xb - xa), hw, 0.5 * q["pad_t"] + 0.001), (0.25, 0.3), 8, 20),
                        "leather_dark"))
            th = np.linspace(0, 2 * np.pi, 72)
            c, s_ = np.cos(th), np.sin(th)
            ex, ey = 0.5 * (xb - xa) - 0.008, hw - 0.007
            loop = np.c_[xm + ex * np.sign(c) * np.abs(c) ** 0.3, sg * yc + ey * np.sign(s_) * np.abs(s_) ** 0.3,
                         np.full_like(th, zt + q["pad_t"] - 0.0005)]
            out.append((dashes(loop, np.tile([0, 0, 1.0], (len(loop), 1)), pitch=0.005, dash=0.003, width=0.0008,
                               raise_=0.0004), "stitch_thread"))
            # map pocket on the inboard face: dark panel, a pleated elastic lip along its top
            x0, x1, dt, db = q["pocket"]
            fr = FD.Fr([0.5 * (x0 + x1), sg * (yi - 0.0012), zt - 0.5 * (dt + db)], [1.0, 0, 0], [0, 0, 1.0])
            if np.dot(fr.w, [0, -sg, 0]) < 0:
                fr = FD.Fr(fr.o, [-1.0, 0, 0], [0, 0, 1.0])
            hx, hz = 0.5 * (x1 - x0), 0.5 * (db - dt)
            out.append((fr.rect(-hx, -hz, hx, hz, 0.0), "black"))
            out.append((fr.se(0, hz - 0.004, 0.003, (hx, 0.0045, 0.0035), (0.3, 0.5), (6, 16)), "rubber_black"))
            for k in np.linspace(-hx + 0.03, hx - 0.03, 7):
                out.append((fr.rect(k - 0.0006, -hz + 0.004, k + 0.0006, hz - 0.012, 0.0006), "rubber_black"))
            # keypad at the console's forward inboard face (P1046409): black plate, 3 x 4 small keys
            kx, kdz = q["keypad"]
            fk = FD.Fr([kx, sg * (yi - 0.0012), zt - kdz], [1.0, 0, 0], [0, 0, 1.0])
            if np.dot(fk.w, [0, -sg, 0]) < 0:
                fk = FD.Fr(fk.o, [-1.0, 0, 0], [0, 0, 1.0])
            out.append((fk.box(0, 0, 0.002, (0.048, 0.058, 0.004)), "bezel_black"))
            for i in range(3):
                for j in range(4):
                    out.append((fk.se(-0.013 + 0.013 * i, -0.020 + 0.0133 * j, 0.0048, (0.0045, 0.0042, 0.0016),
                                      (0.3, 0.3), (4, 8)), "grip_black"))
            # sidewall eyeball outlet aft of the CB pair
            vx, vh, vr = q["vent"]
            M = lining_map(sg, vx - 0.03, vx + 0.03, fl + vh - 0.03, fl + vh + 0.03, 0.0, step=0.01)
            P, Nn = M.frame(0.03, 0.03)
            out.append((revolve([(0.0, vr + 0.006), (0.004, vr + 0.005), (0.006, vr + 0.001), (0.006, vr - 0.001),
                                 (0.001, vr - 0.003)], n=20, axis_origin=P, axis_dir=Nn, cap_ends=False), "bezel_black"))
            out.append((superellipsoid(P + 0.002 * Nn, (vr - 0.004,) * 3, (1, 1), 8, 14), "black"))
            out.append((cylinder(P + 0.010 * Nn, P + 0.016 * Nn, 0.0055, n=10), "bezel_black"))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


# =====================================================================================================================
# B8  divider seen from the flight deck (cfsjets NGX 2281 entry photos, NGX POH 7-19-2): a rounded walnut aisle edge
# with a thin satin-titanium inlay, the crew oxygen-mask stowage cup on the forward face of each wall (outboard, next to
# the sidewall: LH box STA 4.44-4.53, BL -0.70, WL 2.09-2.38 measured on the NGX panorama), the smoke-goggle box
# behind the pilot, headset hooks, a clear document pocket (RH), recessed access latches, the curtain track's end caps
# =====================================================================================================================
DIV = dict(
    o2=(0.075, (0.585, 0.700), (2.100, 2.330)),     # [S+M] cup depth along x, |BL| range, WL range
    goggles=(0.050, (0.605, 0.700), (1.985, 2.060)),  # [S] LH smoke-goggle box: depth, |BL|, WL [E] (outboard,
    #                                                   under the mask cup: clear of the headrest at full aft travel)
    hook=(0.285, 2.240),                             # [E] headset hook |BL|, WL (beside the aisle edge)
    pocket=((0.600, 0.720), (1.360, 1.560)),         # [E] RH clear document pocket |BL|, WL (below the extinguisher)
    latch=((0.420, 1.420), (0.420, 1.900)),          # [E] access-panel latch plates |BL|, WL (both walls)
    # (all-lens review r2 FD9-04) [M: P1046406] a satin-framed grille plate high on the RH wall's AFT face, ~0.1 m
    # outboard of its aisle edge (the LH wall carries a placard there): |BL| of its centre, width, height, its centre
    # below the headliner
    grille=(0.440, 0.086, 0.032, 0.080),
)


def divider_fittings(fl):
    from model import interior as I, flightdeck as FD
    from cad.mesh import box, sweep_profile
    DV = I.DIVIDER
    xa = float(DV["x_aft"])
    t = float(DV["t"])
    xf = xa - t
    ob0, ob1 = (float(v) for v in DV["open_bl"])
    L = FD.lining()
    out = []
    # (no random legends here)
    with res.coarse():
        # rounded aisle edges (half-round walnut, the thin titanium inlay), floor to the headliner: the wall faces stop
        # half a thickness short of the drawn opening edge (flightdeck._divider), the round's apex on it
        for sg, edge in ((-1, ob0), (1, ob1)):
            ztop = float(L.crown(xa - 0.5 * t, edge)) - 0.002
            zs = np.linspace(fl + 0.002, ztop, 24)
            r = 0.5 * t
            a = np.linspace(-0.5 * np.pi, 0.5 * np.pi, 11)
            xc, yc = xa - r, edge + sg * r
            G = np.stack([np.c_[xc + r * np.sin(a), yc - sg * r * np.cos(a), np.full(11, z)] for z in zs])
            m = grid_surface(G)
            out.append((_orient(m, lambda C, y_=yc: np.c_[C[:, 0] - xc, C[:, 1] - y_, np.zeros(len(C))]),
                        "veneer_walnut"))
            yi = edge - sg * 0.0003
            strip = np.stack([np.c_[np.full_like(zs, xc - 0.0012), np.full_like(zs, yi), zs],
                              np.c_[np.full_like(zs, xc + 0.0012), np.full_like(zs, yi), zs]], 1)
            out.append((_orient(grid_surface(strip), [0, -sg, 0]), "panel_titanium"))
            # oxygen-mask stowage cup on the forward face, outboard
            d, (y0, y1), (z0, z1) = DIV["o2"]
            ym, hy, zm, hz = 0.5 * (y0 + y1), 0.5 * (y1 - y0), 0.5 * (z0 + z1), 0.5 * (z1 - z0)
            ylim = float(L.hw(xf - 0.5 * d, zm)) - 0.004
            if ym + hy > ylim:
                ym, hy = 0.5 * (y0 + ylim), 0.5 * (ylim - y0)
            fo = FD.Fr([xf - 0.5 * d, sg * ym, zm], [0, sg, 0], [0, 0, 1.0])
            if np.dot(fo.w, [-1.0, 0, 0]) < 0:
                fo = FD.Fr(fo.o, [0, -sg, 0], [0, 0, 1.0])
            out.append((fo.se(0, 0, 0, (hy, hz, 0.5 * d + 0.002), (0.3, 0.3), (8, 16)), "panel_dark"))
            out.append((fo.se(0, 0.03, 0.5 * d - 0.004, (hy - 0.016, hz - 0.060, 0.008), (0.35, 0.35), (6, 14)),
                        "bezel_black"))
            for k in (-1, 1):                                              # the mask's red donning tabs
                out.append((fo.box(k * 0.025, hz - 0.045, 0.5 * d + 0.006, (0.018, 0.012, 0.008)), "paint_red"))
            hose = np.array([fo.p(0.010, -0.030 - 0.03 * k, 0.5 * d + 0.006 + 0.004 * math.sin(k)) for k in range(5)])
            out.append((sweep_profile(hose, np.c_[0.004 * np.cos(np.linspace(0, 2 * np.pi, 8, endpoint=False)),
                                                  0.004 * np.sin(np.linspace(0, 2 * np.pi, 8, endpoint=False))]),
                        "fdb_hose_green"))
            out.append((fo.rect(-hy + 0.010, -hz + 0.010, -hy + 0.050, -hz + 0.024, 0.5 * d + 0.0025), "placard_red"))
            # headset hook beside the aisle edge
            hy_, hz_ = DIV["hook"]
            hk = np.array([[xf - 0.002, sg * hy_, hz_ + 0.012], [xf - 0.030, sg * hy_, hz_ + 0.006],
                           [xf - 0.042, sg * hy_, hz_ - 0.006], [xf - 0.036, sg * hy_, hz_ - 0.020],
                           [xf - 0.026, sg * hy_, hz_ - 0.018]])
            out.append((sweep_profile(hk, np.c_[0.0035 * np.cos(np.linspace(0, 2 * np.pi, 8, endpoint=False)),
                                                0.0035 * np.sin(np.linspace(0, 2 * np.pi, 8, endpoint=False))]),
                        "black"))
            out.append((box([xf - 0.003, sg * hy_, hz_ + 0.012], (0.006, 0.020, 0.030)), "black"))
            # access latch plates (recessed: a dark rounded plate with a satin pull)
            for ly, lz in DIV["latch"]:
                fl_ = FD.Fr([xf - 0.0012, sg * ly, lz], [0, 1.0, 0], [0, 0, 1.0])
                if np.dot(fl_.w, [-1.0, 0, 0]) < 0:
                    fl_ = FD.Fr(fl_.o, [0, -1.0, 0], [0, 0, 1.0])
                out.append((fl_.rect(-0.018, -0.010, 0.018, 0.010, 0.0), "bezel_black"))
                out.append((fl_.se(0, 0, 0.0012, (0.012, 0.0035, 0.0012), (0.4, 0.4), (4, 8)), "panel_silver"))
            # the grille plate on the RH wall's aft face (DIV grille): a satin frame, a dark slot with three slats
            gy, gw, gh, gdz = DIV["grille"]
            fg = FD.Fr([xa + 0.0004, sg * gy, float(L.crown(xa, gy)) - gdz], [0, 1.0, 0], [0, 0, 1.0])
            if np.dot(fg.w, [1.0, 0, 0]) < 0:
                fg = FD.Fr(fg.o, [0, -1.0, 0], [0, 0, 1.0])
            if sg > 0:
                out.append((FD._extrusion(fg.moved(c=0.0010), FD.rrect_loop(0.5 * gw, 0.5 * gh, 0.004, nc=3), 0.002,
                                          bevel=0.0006, nb=1), "panel_silver"))
                out.append((fg.rect(-0.5 * gw + 0.007, -0.5 * gh + 0.006, 0.5 * gw - 0.007, 0.5 * gh - 0.006, 0.0024),
                            "black"))
                for k in (-1, 0, 1):
                    out.append((fg.rect(-0.5 * gw + 0.009, k * 0.0055 - 0.0008, 0.5 * gw - 0.009, k * 0.0055 + 0.0008,
                                        0.0028), "panel_silver"))
            if sg < 0:
                # smoke-goggle box behind the pilot
                d, (gy0, gy1), (gz0, gz1) = DIV["goggles"]
                out.append((box([xf - 0.5 * d, -0.5 * (gy0 + gy1), 0.5 * (gz0 + gz1)], (d, gy1 - gy0, gz1 - gz0)),
                            "panel_dark"))
                out.append((box([xf - d - 0.0005, -0.5 * (gy0 + gy1), 0.5 * (gz0 + gz1)],
                                (0.002, 0.6 * (gy1 - gy0), 0.4 * (gz1 - gz0))), "placard_red"))
            else:
                # clear document pocket (RH), papers inside
                (py0, py1), (pz0, pz1) = DIV["pocket"]
                ylim = float(L.hw(xf - 0.01, 0.5 * (pz0 + pz1))) - 0.006
                py1 = min(py1, ylim)
                out.append((box([xf - 0.004, 0.5 * (py0 + py1), 0.5 * (pz0 + pz1) - 0.01],
                                (0.004, py1 - py0 - 0.02, pz1 - pz0 - 0.05)), "legend_lit"))
                fp = FD.Fr([xf - 0.009, 0.5 * (py0 + py1), 0.5 * (pz0 + pz1)], [0, 1.0, 0], [0, 0, 1.0])
                if np.dot(fp.w, [-1.0, 0, 0]) < 0:
                    fp = FD.Fr(fp.o, [0, -1.0, 0], [0, 0, 1.0])
                out.append((fp.rect(-0.5 * (py1 - py0), -0.5 * (pz1 - pz0), 0.5 * (py1 - py0), 0.5 * (pz1 - pz0), 0.0),
                            "lens"))
                out.append((fp.box(0, 0.5 * (pz1 - pz0) - 0.004, 0.0, (py1 - py0, 0.008, 0.010)), "black"))
                for side_ in (-1, 1):
                    out.append((fp.box(side_ * 0.5 * (py1 - py0), 0.0, -0.002, (0.006, pz1 - pz0, 0.012)), "black"))
        # fire extinguisher (flightdeck._divider: bottle, valve, handle, straps, plate): strap buckles, gauge, pin
        out += extinguisher_fittings(fl)
        # curtain track end caps
        x0c, x1c, y0c, y1c, ztc, xt = I.curtain_bundle()
        for yy in (ob0 - 0.02, ob1 + 0.02):
            zz = float(L.crown(xt, yy)) - 0.008
            out.append((box([xt, yy - np.sign(yy) * 0.004, zz], (0.016, 0.010, 0.028)), "metal_dark"))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]


def extinguisher_fittings(fl):
    """Detail on the fire extinguisher of flightdeck._divider (DIVIDER extinguisher; NGX POH 7-19 / the cfsjets entry
    photos: a red Halon bottle in a quick-release bracket): an over-centre buckle with its lever on each strap, a heel
    cup under the bottle, the pressure gauge on the valve head (silver bezel, white face, green band, needle), the
    safety pin with its pull ring through the handle, and a white instruction label with abstract strokes between the
    straps facing the flight deck."""
    from model import interior as I
    from cad.mesh import box, cylinder, disk, sweep_profile
    ex, ey, ez, ed, eh = (float(v) for v in I.DIVIDER["extinguisher"])
    r = 0.5 * ed
    zb = fl + ez - 0.5 * eh
    out = []
    circ = lambda rr, n: np.c_[rr * np.cos(np.linspace(0, 2 * np.pi, n, endpoint=False)),        # noqa: E731
                               rr * np.sin(np.linspace(0, 2 * np.pi, n, endpoint=False))]
    with res.coarse():
        for zz in (zb + 0.06, zb + eh - 0.07):                          # the straps' buckles (front, toward the deck)
            out.append((box([ex - r - 0.006, ey, zz], (0.008, 0.026, 0.020)), "metal_dark"))
            out.append((box([ex - r - 0.0115, ey + 0.003, zz - 0.003], (0.004, 0.011, 0.030)), "black"))
        xs_ = float(I.DIVIDER["x_aft"]) - float(I.DIVIDER["t"]) - 0.003   # the bracket plate's mid-plane
        out.append((box([0.5 * (ex - r - 0.004 + xs_), ey, zb - 0.004], (xs_ - (ex - r - 0.004), 0.046, 0.008)),
                    "metal_dark"))                                     # heel cup under the bottle
        out.append((box([ex - r - 0.003, ey, zb + 0.010], (0.004, 0.046, 0.028)), "metal_dark"))
        # pressure gauge on the valve head, facing inboard (the aisle)
        zg = zb + eh + 0.014
        gy0, gy1 = ey - 0.010, ey - 0.019
        out.append((cylinder([ex, gy0, zg], [ex, gy1, zg], 0.0095, n=16), "panel_silver"))
        out.append((disk([ex, gy1 - 0.0003, zg], [0, -1.0, 0], 0.0078, n=16), "light_white"))
        th = np.linspace(np.radians(35), np.radians(145), 8)
        V, F = [], []
        for k in range(len(th) - 1):                                    # green band of the dial
            a, b = th[k], th[k + 1]
            q = [(0.0052, a), (0.0068, a), (0.0068, b), (0.0052, b)]
            i0 = len(V)
            V += [[ex + rr * math.cos(t_), gy1 - 0.0006, zg + rr * math.sin(t_)] for rr, t_ in q]
            F += [[i0, i0 + 1, i0 + 2], [i0, i0 + 2, i0 + 3]]
        out.append((_orient(Mesh(np.array(V), np.array(F)), [0, -1.0, 0]), "annun_green"))
        na = np.radians(78)
        nd = np.array([math.cos(na), 0.0, math.sin(na)])
        tn = np.array([-nd[2], 0.0, nd[0]])
        P0 = np.array([ex, gy1 - 0.0009, zg])
        Q = np.array([P0 - 0.0004 * tn, P0 + 0.0004 * tn, P0 + 0.0062 * nd + 0.0002 * tn, P0 + 0.0062 * nd - 0.0002 * tn])
        out.append((_orient(Mesh(Q, np.array([[0, 1, 2], [0, 2, 3]])), [0, -1.0, 0]), "black"))
        # safety pin through the handle and its pull ring hanging inboard
        zp = zb + eh + 0.030
        out.append((cylinder([ex - 0.024, ey + 0.010, zp], [ex - 0.024, ey - 0.014, zp], 0.0015, n=8), "panel_silver"))
        ring = np.c_[np.full(13, ex - 0.024) + 0.0085 * np.sin(np.linspace(0, 2 * np.pi, 13)),
                     np.full(13, ey - 0.016),
                     zp - 0.0085 + 0.0085 * np.cos(np.linspace(0, 2 * np.pi, 13))]
        out.append((sweep_profile(ring, circ(0.0011, 6), cap=False), "panel_silver"))
        # instruction label (white) wrapped on the bottle between the straps, abstract strokes on it
        zl0, zl1 = zb + 0.082, zb + eh - 0.092
        a = np.pi + np.linspace(-0.55, 0.55, 9)
        rl = r + 0.0004
        G = np.stack([np.c_[ex + rl * np.cos(a), ey + rl * np.sin(a), np.full(len(a), z)] for z in (zl0, zl1)], 1)
        out.append((_orient(grid_surface(G), lambda C: (C - [ex, ey, 0.0]) * [1.0, 1.0, 0.0]), "light_white"))
        V, F = [], []
        rs = r + 0.0008
        for j, (zz, frac) in enumerate(((zl1 - 0.012, 0.70), (zl1 - 0.020, 0.85), (zl1 - 0.034, 0.80), (zl1 - 0.046,
                                         0.60), (zl1 - 0.058, 0.85), (zl1 - 0.070, 0.50), (zl0 + 0.020, 0.75))):
            h = 0.0035 if j == 0 else 0.0018
            aa = np.pi + np.linspace(-0.45 * frac, 0.45 * frac, 5)
            i0 = len(V)
            for t_ in aa:
                V += [[ex + rs * math.cos(t_), ey + rs * math.sin(t_), zz], [ex + rs * math.cos(t_), ey + rs * math.sin(t_),
                                                                            zz + h]]
            for k in range(len(aa) - 1):
                b0 = i0 + 2 * k
                F += [[b0, b0 + 2, b0 + 3], [b0, b0 + 3, b0 + 1]]
        out.append((_orient(Mesh(np.array(V), np.array(F)), lambda C: (C - [ex, ey, 0.0]) * [1.0, 1.0, 0.0]), "black"))
    return [(m, mat) for m, mat in out if m is not None and len(m.F)]
