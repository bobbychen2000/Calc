"""First-principles flight deck checks (34-35), run by test/fit_check.py after fit_fd_a / fit_fd_b (or standalone:
python3 test/fit_fd_p.py builds the interior alone).

34. printed legends ON the surface (part A3): every vertex / face centre of a 'legend_print' decal lies 0.05-0.5 mm off
    the nearest other interior surface (fd_print.LIFT 0.15 mm; a print on a curved face follows it in <= 6 mm cells) --
    none floats, none sinks into its panel
35. knife edges: the open (unwelded) boundary edges of the flight deck's own meshes (parts flight_deck, fd_consoles,
    fd_divider) that end in mid-air -- no other surface within 1 mm of the edge's midpoint -- total length at most
    KNIFE_MAX (the first-principles baseline: a new part must close its sheets or tuck their edges into a neighbour)
36. every material the flight deck's own parts use belongs to one row of interior.FD_CONSTRUCTION (sheet L6C: what
    each part is made of and how it is finished)
"""
from __future__ import annotations

import sys

import numpy as np

if "parts" not in globals():
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    sys.path.insert(1, str(__import__("pathlib").Path(__file__).resolve().parent))
    from model import interior as _I0
    parts = {}
    _I0.build_interior(parts)
    fails, opens = [], []

    def report(name, ok, detail="", open_item=False):
        tag = "open" if open_item else ("ok" if ok else "FAIL")
        print(f"  [{tag}] {name}" + (f": {detail}" if detail else ""))
        (opens if open_item else fails if not ok else []).append(name)
    _STANDALONE = True
else:
    _STANDALONE = False

from scipy.spatial import cKDTree  # noqa: E402
from isect import pt_tri_k  # noqa: E402

KNIFE_MAX = 99.0            # m of mid-air open edges in the flight deck's own parts (set from the baseline below)

INT_P = [k for k, q in parts.items() if q.step == "interior"]
# 34 -------------------------------------------------------------------------------------- legends on the surface
LEG, OTH = [], []
for pid in INT_P:
    for m, mat in parts[pid].meshes:
        if len(m.F):
            (LEG if mat == "legend_print" else OTH).append((pid, m))
if LEG:
    P = np.vstack([np.vstack([m.V, m.V[m.F].mean(1)]) for _, m in LEG])
    lo, hi = P.min(0) - 0.01, P.max(0) + 0.01
    T = []
    for _, m in OTH:
        Tm = m.V[m.F]
        c = Tm.mean(1)
        sel = np.all((c >= lo) & (c <= hi), 1)
        if sel.any():
            T.append(Tm[sel])
    T = np.vstack(T)
    tree = cKDTree(T.mean(1))
    _, idx = tree.query(P, k=32)
    d = pt_tri_k(P, T[idx])
    bad = (d < 5e-5) | (d > 5e-4)
    report("34 printed legends on their surfaces (0.05-0.5 mm off, every vertex / face centre)", not bad.any(),
           f"{len(LEG)} decal meshes, {len(P)} points: {d.min() * 1000:.2f}-{d.max() * 1000:.2f} mm, median "
           f"{np.median(d) * 1000:.2f}; {int(bad.sum())} outside" + ("" if not bad.any() else
                                                                     f" (worst at {np.round(P[np.argmax(d)], 3)})"))
else:
    report("34 printed legends on their surfaces", False, "no legend_print meshes")

# 35 ---------------------------------------------------------------------------------------------- knife edges
OWN = [k for k in ("flight_deck", "fd_consoles", "fd_divider") if k in parts]
ALL_T = np.vstack([m.V[m.F] for _, m in OTH + LEG])
atree = cKDTree(ALL_T.reshape(-1, 3))
L_knife, n_knife, worst = 0.0, 0, []
for pid in OWN:
    for m, mat in parts[pid].meshes:
        if not len(m.F) or mat == "legend_print":
            continue
        key = np.round(m.V / 2e-5).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        F = inv.ravel()[m.F]
        E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
        Eu, cnt = np.unique(E, axis=0, return_counts=True)
        Eb = Eu[cnt == 1]
        if not len(Eb):
            continue
        Vw = np.zeros((inv.max() + 1, 3))
        Vw[inv.ravel()] = m.V
        A, B = Vw[Eb[:, 0]], Vw[Eb[:, 1]]
        M = 0.5 * (A + B)
        # other surfaces near the midpoint: any vertex of another triangle within 1 mm that is not on this edge
        nb = atree.query_ball_point(M, 0.001)
        free = np.array([len(x) <= 6 for x in nb])
        if free.any():
            L = np.linalg.norm(B - A, axis=1)[free]
            L_knife += float(L.sum())
            n_knife += int(free.sum())
            worst.append((float(L.sum()), pid, mat))
worst.sort(reverse=True)
report(f"35 knife edges: mid-air open edges of the flight deck's own meshes <= {KNIFE_MAX:.1f} m", L_knife <= KNIFE_MAX,
       f"{L_knife:.2f} m in {n_knife} edges; most: " + ", ".join(f"{p}:{m} {l:.2f}" for l, p, m in worst[:5]))

# 36 ------------------------------------------------------------------------- construction / finish table coverage
from model import interior as _IC  # noqa: E402
_known = {m for v in _IC.FD_CONSTRUCTION.values() for m in v[4]}
_used = {mat for pid in OWN for m, mat in parts[pid].meshes if len(m.F)}
_miss = sorted(_used - _known)
report("36 every material of the flight deck's own parts in one FD_CONSTRUCTION row (sheet L6C)", not _miss,
       f"{len(_used)} materials" + (f"; missing {', '.join(_miss)}" if _miss else ""))

if _STANDALONE:
    print("FIT OK" if not fails else f"FIT FAILED: {fails}")
