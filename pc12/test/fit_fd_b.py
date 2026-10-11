"""Flight deck r1, track B fit checks (30-31), run by test/fit_check.py after its own checks (or standalone:
python3 test/fit_fd_b.py builds the forward skin / glazing and the interior alone).

30. the flight-deck glass (glazing_flightdeck 'glass' / 'glass_windshield'): every interior piece within reach of it --
    the moulded windshield / side-window reveals and their seal lips, the leather sills with their stitching and
    placards (fd_detail_b.glazing_mouldings), the sun visors and rails, the centre-post fittings, the overhead pod --
    stays >= 2 mm clear of the glass (exact point-triangle distances to the glass triangles near each point) and no
    interior triangle crosses it; 30b the new surround fittings hung on the lining (visors, rails, post fittings, pod,
    CB bezels, sill items) each touch their mounting surface (nearest other surface <= 3 mm)
31. the crew seats at full aft travel, both height extremes, both headrest locks, armrests down and up, clear the
    divider's flight-deck fittings (oxygen-mask cups, goggle box, headset hooks, document pocket, latches) and the
    console fittings (armrest pads, map pockets, keypads) by >= 5 mm
"""
from __future__ import annotations

import sys

import numpy as np

if "parts" not in globals():                                     # standalone: forward skin, glazing, interior
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    sys.path.insert(1, str(__import__("pathlib").Path(__file__).resolve().parent))
    from model import interior as _I0, fuselage_parts as _FP0
    parts = {}
    _FP0.build(parts)
    _I0.build_interior(parts)
    fails, opens = [], []

    def report(name, ok, detail="", open_item=False):
        tag = "open" if open_item else ("ok" if ok else "FAIL")
        print(f"  [{tag}] {name}" + (f": {detail}" if detail else ""))
        if open_item:
            opens.append(name)
        elif not ok:
            fails.append(name)
    _STANDALONE = True
else:
    _STANDALONE = False

from scipy.spatial import cKDTree  # noqa: E402
from isect import crossings  # noqa: E402
from model import interior as IB, fd_detail_b as FDB, seats as SB  # noqa: E402


def _pt_tri_k(P, T):
    """Exact distances of points P (n, 3) to the triangles T (n, k, 3, 3) (k candidates per point): (n,) minimum."""
    a, b, c = T[:, :, 0], T[:, :, 1], T[:, :, 2]
    Q = P[:, None, :]
    ab, ac, ap = b - a, c - a, Q - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = Q - b
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = Q - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) < 1e-30, 1e-30, va + vb + vc)
    v, w = vb / den, vc / den
    X = a + v[..., None] * ab + w[..., None] * ac                                         # interior projection
    # region tests (Ericson): vertices / edges
    X = np.where(((d1 <= 0) & (d2 <= 0))[..., None], a, X)
    X = np.where(((d3 >= 0) & (d4 <= d3))[..., None], b, X)
    X = np.where(((d6 >= 0) & (d5 <= d6))[..., None], c, X)
    vab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    tab = d1 / np.where(np.abs(d1 - d3) < 1e-30, 1e-30, d1 - d3)
    X = np.where(vab[..., None], a + tab[..., None] * ab, X)
    vac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    tac = d2 / np.where(np.abs(d2 - d6) < 1e-30, 1e-30, d2 - d6)
    X = np.where(vac[..., None], a + tac[..., None] * ac, X)
    vbc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    tbc = (d4 - d3) / np.where(np.abs((d4 - d3) + (d5 - d6)) < 1e-30, 1e-30, (d4 - d3) + (d5 - d6))
    X = np.where(vbc[..., None], b + tbc[..., None] * (c - b), X)
    return np.linalg.norm(Q - X, axis=-1).min(1)


def _components(m):
    """Connected pieces (vertex labels) of a mesh by shared vertex positions."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    key = np.round(m.V / 2e-5).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    F = inv[m.F]
    n = int(inv.max()) + 1
    A = coo_matrix((np.ones(3 * len(F)), (np.r_[F[:, 0], F[:, 1], F[:, 2]], np.r_[F[:, 1], F[:, 2], F[:, 0]])),
                   shape=(n, n))
    _, lab = connected_components(A, directed=False)
    return lab[inv], inv


# 30 --------------------------------------------------------------------------------- the flight-deck glass
GLASS_T = np.vstack([m.V[m.F] for m, mat in parts["glazing_flightdeck"].meshes if mat in ("glass", "glass_windshield")])
gtree = cKDTree(GLASS_T.mean(1))
INT_FD = [k for k, q in parts.items() if q.step == "interior" and k != "interior_lining" and
          (k in ("flight_deck",) or q.parent == "flight_deck" or k.startswith("seat_pilot") or
           k.startswith("seat_copilot"))] + ["interior_lining"]
worst = (np.inf, None)
n_pts = 0
cross_n = 0
for pid in INT_FD:
    for m, mat in parts[pid].meshes:
        if not len(m.F):
            continue
        P = np.vstack([m.V, 0.5 * (m.V[m.F[:, 0]] + m.V[m.F[:, 1]]), m.V[m.F].mean(1)])
        sel = (P[:, 0] < 4.50) & (P[:, 2] > 1.90)
        if not sel.any():
            continue
        P = P[sel]
        d0, _ = gtree.query(P, distance_upper_bound=0.06)
        near = np.isfinite(d0)
        if not near.any():
            continue
        P = P[near]
        n_pts += len(P)
        _, idx = gtree.query(P, k=16)
        d = _pt_tri_k(P, GLASS_T[idx])
        k = int(np.argmin(d))
        if d[k] < worst[0]:
            worst = (float(d[k]), (pid, mat, P[k]))
        # crossings: the mesh's triangles near the glass against the glass triangles near them
        Tm = m.V[m.F]
        dc, _ = gtree.query(Tm.mean(1), distance_upper_bound=0.05)
        tsel = np.isfinite(dc)
        if tsel.any():
            Tn = Tm[tsel]
            _, gi = gtree.query(Tn.mean(1), k=24)
            G = GLASS_T[np.unique(gi.ravel())]
            VT, VG = Tn.reshape(-1, 3), G.reshape(-1, 3)
            cr = crossings(VT, np.arange(len(VT)).reshape(-1, 3), VG, np.arange(len(VG)).reshape(-1, 3))
            cross_n += len(cr)
d_min, where = worst
report("flight-deck glass: reveals, seal lips, sills, visors, post fittings and every interior piece >= 2 mm clear of "
       "the glass, no crossing", d_min >= 0.002 and cross_n == 0,
       f"{n_pts:,} points within 60 mm of the glass; nearest {1000 * d_min:.1f} mm ({where[0]} / {where[1]} at STA "
       f"{where[2][0]:.3f} BL {where[2][1]:+.3f} WL {where[2][2]:.3f}); {cross_n} crossings" if where else
       "no interior point within 60 mm of the glass")

# 30b ------------------------------------------------------------------------- new surround fittings seated
NEW_MATS = {"fdb_visor", "fdb_cb_glow_blue", "fdb_cb_glow_green", "fdb_cb_glow_yellow", "fdb_cb_glow_white",
            "stitch_thread", "placard_red", "legend_plate", "legend_lit", "panel_silver", "black", "bezel_black",
            "metal_dark", "lens", "seal", "panel_dark", "light_white", "screen", "light_red", "psu_panel",
            # flight deck fix r2: the bronze bus bars, muted placards, the surround's edge bead, the overhead's chrome
            # toggles and smoked button lenses, the CB heads' sleeves
            "busbar_bronze", "placard_red_dim", "trim_satin", "chrome_trim", "annun_off_red", "annun_off_amber",
            "grip_black"}
lin = parts["interior_lining"]
# (+ the flight-deck glass: the windshield's heating bus bars -- flight deck fix r1, fd_detail_b GLAZING_TRIM wire_* --
# are mounted on it, 2.5 mm inside it; check 30 keeps every piece >= 2 mm off the glass, so only a piece within the
# 2-3 mm band beside the glass can be seated by it)
allT = np.vstack([m.V[m.F] for pid in ("interior_lining", "flight_deck", "fd_consoles", "fd_divider", "glazing_flightdeck")
                  if pid in parts for m, _ in parts[pid].meshes if len(m.F)])
loose = []
n_pc = 0
fd_box = lambda V: (V[:, 0] < 4.60) & (V[:, 0] > 3.0)                                 # noqa: E731
for m, mat in lin.meshes:
    if mat not in NEW_MATS or not len(m.F) or not fd_box(m.V).any():
        continue
    lab, inv = _components(m)
    T = m.V[m.F]
    tl = lab[m.F[:, 0]]
    for c in np.unique(tl):
        Tc = T[tl == c]
        if not fd_box(Tc.reshape(-1, 3)).all():
            continue
        n_pc += 1
        lo, hi = Tc.reshape(-1, 3).min(0) - 0.004, Tc.reshape(-1, 3).max(0) + 0.004
        O = allT[np.all((allT.max(1) >= lo) & (allT.min(1) <= hi), 1)]
        # the other surfaces: drop the piece's own triangles (exact matches)
        key_c = {tuple(np.round(t.ravel(), 7)) for t in Tc}
        O = np.array([t for t in O if tuple(np.round(t.ravel(), 7)) not in key_c]) if len(O) else O
        if not len(O):
            loose.append((np.inf, mat, Tc.reshape(-1, 3).mean(0)))
            continue
        S = np.unique(np.round(np.vstack([Tc.reshape(-1, 3), Tc.mean(1)]), 7), axis=0)
        if len(S) > 200:
            S = S[np.random.default_rng(0).choice(len(S), 200, replace=False)]
        k = min(12, len(O))
        ot = cKDTree(O.mean(1))
        _, idx = ot.query(S, k=k)
        idx = idx.reshape(len(S), -1)
        d = float(_pt_tri_k(S, O[idx]).min())
        if d > 0.003:
            loose.append((d, mat, Tc.reshape(-1, 3).mean(0)))
loose.sort(key=lambda r: -r[0])
report(f"surround fittings on the lining seated: every piece ({n_pc}) within 3 mm of its mounting surface", not loose,
       "all seated" if not loose else "; ".join(f"{m_} {1000 * d_:.1f} mm at STA {c_[0]:.3f} BL {c_[1]:+.3f} WL "
                                                f"{c_[2]:.3f}" for d_, m_, c_ in loose[:8]))

# 31 ------------------------------------------------------------------------- crew seats vs the new fittings
FL_ = float(IB.FLOOR["fd_wl"])
fit_T = []
for m, mat in FDB.divider_fittings(FL_) + FDB.console_fittings(FL_):
    if len(m.F):
        fit_T.append(m.V[m.F])
fit_T = np.vstack(fit_T)
ftree = cKDTree(fit_T.mean(1))
c_ = IB.CREW_SEAT
worst31 = (np.inf, None)
for side in (-1, 1):
    for dz in (-float(c_["travel_z"]), float(c_["travel_z"])):
        for hc in c_["head_lock"]:
            for arms in ((False, False), (True, True)):
                ms = SB.crew_seat(side, dx=float(c_["travel_x"]), dz=dz, head_c=float(hc), arm_up=arms, tracks=False,
                                  harness=False)
                V = np.vstack([m.V for m, _ in ms])
                d0, _ = ftree.query(V, distance_upper_bound=0.08)
                near = np.isfinite(d0)
                if not near.any():
                    continue
                Pn = V[near]
                _, idx = ftree.query(Pn, k=min(16, len(fit_T)))
                d = _pt_tri_k(Pn, fit_T[idx])
                k = int(np.argmin(d))
                if d[k] < worst31[0]:
                    worst31 = (float(d[k]), (side, dz, hc, arms, Pn[k]))
d31, w31 = worst31
report("crew seats (full aft, height extremes, both headrest locks, armrests down / up) >= 5 mm clear of the divider "
       "and console fittings", d31 >= 0.005,
       "nothing within 80 mm" if w31 is None else
       f"nearest {1000 * d31:.1f} mm ({'pilot' if w31[0] < 0 else 'co-pilot'}, dz {1000 * w31[1]:+.0f}, headrest "
       f"{w31[2]:.3f}, arms {'up' if w31[3][0] else 'down'}, at STA {w31[4][0]:.3f} BL {w31[4][1]:+.3f} WL "
       f"{w31[4][2]:.3f})")

if _STANDALONE:
    print("FIT FD-B OK" if not fails else f"FIT FD-B FAIL ({len(fails)}): " + "; ".join(fails))
    sys.exit(1 if fails else 0)
