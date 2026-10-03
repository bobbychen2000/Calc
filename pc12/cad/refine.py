"""
loftkit.refine -- curvature-adaptive refinement of tessellated surfaces (the 'higher resolution' pass).

The builders sample their analytic surfaces on (u, v) grids and carry analytic / grid vertex normals.  refine()
splits every edge whose curve, implied by the edge's two end points and their normals, bows more than a tolerance
from the straight chord -- the cubic edge curve of PN triangles (Vlachos et al. 2001):

    P(1/2) = (Pa + Pb) / 2 - (wab Na + wba Nb) / 8,     wab = (Pb - Pa) . Na,   wba = (Pa - Pb) . Nb

so a flat region keeps its triangles, a tight radius gets many, and the new vertices lie on the smooth surface the
normals describe.  A second criterion (turn_deg) splits an edge whose end normals turn more than a few degrees while it
still bows more than min_sag: a small radius sampled every 30 deg bows only a fraction of a millimetre, but its flat
facets show in the shading and on the silhouette at the viewer's close range (a circle sampled every 22.5 deg: the chord misses the arc by 1.9 % of the radius, the PN midpoint
by 0.06 %).  Original vertices never move.  Triangles are split 1 -> 2 / 3 / 4 by the pattern of their split edges,
so the mesh stays conforming (no T-junctions, no cracks).

Edges are found across ALL meshes of a group (a part: its paint regions, patches and trims are separate meshes that
share boundary vertices), by position: a boundary shared by two meshes is refined once, both copies get the same new
point, so painted stroke edges, patch seams and trim lines stay watertight.  Per edge:

  * smooth (two faces, end normals agree within CREASE_DEG): the PN midpoint from the averaged end normals;
  * crease (two faces, normals differ, e.g. a tube's end ring against its flat cap): the bow is reconstructed from
    both sides -- each side's PN bow gives the component of the edge curve's curvature along that side's normal,
    the two components fix the vector -- so a tube end stays round and the cap follows it; a sharp fold (the two
    normals nearly opposite: a trailing edge, a thin plate's rim) stays straight;
  * open boundary (one face: a hole, a trim line, an open end, an edge another part meets): kept exactly as built --
    its in-surface bend is not known, and parts are fitted to each other along their boundaries;
  * non-manifold: kept as built.

Normals only describe a smooth surface where it was sampled finely enough, so a face's edges are bowed only if the
face is a well-sampled curved patch: its vertex normals within FACE_DEV_DEG of it and straddling it (DEV_RATIO), the
mesh bending round it about as much as they turn (BEND_RATIO), no S on its edges (S_DEG), the edge's normals turning
less than MAX_TURN_DEG; the bow is also capped so the two new sub-triangles tilt no further than the face's own
normals lean (slivers do not fold) and at bow_max.  Everything else (boxes and hexagons drawn with averaged corner
normals, coarse kinked profiles, flat faces carrying a chamfer's normal, clamped regions) stays exactly as built.

Each new vertex gets the PN quadratic normal of its own side, its UV (if any) is interpolated linearly.
"""
from __future__ import annotations

import numpy as np

from .mesh import Mesh

CREASE_DEG = 12.0         # end normals of the two faces closer than this: one smooth surface
FACE_DEV_DEG = 18.0       # a vertex normal further than this from a face's normal: the face is not a well-sampled
#                           curved patch (a 12-gon tube, 15 deg, is one; an octagon, 22.5 deg, a box or a coarse
#                           kinked profile drawn with averaged normals stays as built: bowing it makes bumps)
MAX_TURN_DEG = 32.0       # an edge whose end normals turn more than this is not bowed (PN error at 30 deg: 0.2 % R)
S_DEG = 2.5               # an edge whose end normals lean to opposite sides of its chord by more than this (an S, an
#                           inflection inside one edge) marks its faces as not well sampled: a kinked profile drawn
#                           with averaged normals has one on every edge across the kink, a smooth surface hardly ever
DEV_RATIO = 0.75          # ... and a face whose vertex normals stray from it by more than DEV_RATIO x the turn between
#                           them: on a sampled smooth surface they straddle the face (about half the turn),
#                           a flat face carrying a corner-averaged or pre-clamp normal leans one way (bowing it would
#                           push a seat base 3 mm into the floor, a clamped carry-through up through its limit)
BEND_RATIO = 0.5          # ... and a face round which the mesh bends (largest dihedral to a neighbour) less than half as
#                           much as its vertex normals turn
EPS_ANG = np.radians(0.05)
FOLD_DEG = 150.0          # crease sharper than this (normals nearly opposite): a fold, kept straight


def _unit(a):
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    return a / np.where(n < 1e-300, 1.0, n)


def pn_midpoint_bow(Pa, Pb, Na, Nb):
    """Displacement of the PN cubic edge curve's midpoint from the chord midpoint (arrays (k, 3))."""
    e = Pb - Pa
    wab = np.sum(e * Na, 1)
    wba = -np.sum(e * Nb, 1)
    return -(wab[:, None] * Na + wba[:, None] * Nb) / 8.0


def pn_mid_normal(Pa, Pb, Na, Nb):
    """PN quadratic normal at the edge midpoint."""
    e = Pb - Pa
    s = Na + Nb
    L2 = np.maximum(np.sum(e * e, 1), 1e-300)
    v = 2.0 * np.sum(e * s, 1) / L2
    return _unit(s - v[:, None] * e)


def refine(meshes, tol=0.0001, levels=3, min_len=0.0004, field=None, field_levels=None, field_near=0.5,
           keep_boundary=False, bow_max=0.001, turn_deg=None, min_sag=2e-5):
    """Refine a group of meshes (list of Mesh; returns new meshes in the same order).

    tol         sagitta (m): split an edge whose PN curve bows more than tol from its chord
    levels      at most this many passes (each halves the split edges)
    min_len     never split edges shorter than this
    field       optional fn(V) -> (n, k) values of k trim fields: an edge is split (up to field_levels passes) where
                one of them changes sign along it, or where |value| < field_near * edge length at both ends of the
                edge (a feature narrower than the edge) -- the zero sets the caller trims along afterwards are then
                cut on a fine mesh
    keep_boundary  never split open-boundary edges (one face): for a mesh that shares its boundary with meshes that
                are not refined with it (a skin piece refined before it is trimmed), so the seam stays conforming
    bow_max     an edge whose curve would bow more than this is sampled too coarsely for its normals to be trusted
                (a long flat skid whose end normals carry the chamfer next door would sag through the floor): kept
                straight
    turn_deg    also split a bowable edge whose end normals turn more than this (deg) where it bows more than min_sag
                (m): the facets of small radii (a cushion's rounded rim, a grip, a lip) whatever their sagitta
    """
    meshes = list(meshes)
    field_levels = levels if field_levels is None else field_levels
    if not meshes or (levels <= 0 and (field is None or field_levels <= 0)):
        return [m.copy() for m in meshes]
    nm = len(meshes)
    # global arrays
    V = np.vstack([m.V for m in meshes]) if nm else np.zeros((0, 3))
    N = np.vstack([m.N for m in meshes])
    has_uv = [m.UV is not None and len(m.UV) == len(m.V) for m in meshes]
    UV = np.vstack([m.UV if h else np.zeros((len(m.V), 2)) for m, h in zip(meshes, has_uv)])
    vm = np.concatenate([np.full(len(m.V), i, np.int64) for i, m in enumerate(meshes)])
    off = np.cumsum([0] + [len(m.V) for m in meshes])
    F = np.vstack([m.F + off[i] for i, m in enumerate(meshes)]) if nm else np.zeros((0, 3), np.int64)
    fm = np.concatenate([np.full(len(m.F), i, np.int64) for i, m in enumerate(meshes)])
    cos_crease = np.cos(np.radians(CREASE_DEG))
    cos_dev = np.cos(np.radians(FACE_DEV_DEG))
    cos_fold = np.cos(np.radians(FOLD_DEG))
    cos_turn = np.cos(np.radians(MAX_TURN_DEG))
    cos_split = None if turn_deg is None else np.cos(np.radians(turn_deg))

    for level in range(max(levels, field_levels if field is not None else 0)):
        nf = len(F)
        if nf == 0:
            break
        curv_on = level < levels
        field_on = field is not None and level < field_levels
        # ---- weld by position (1 um): group id per vertex
        key = np.round(V * 1e6).astype(np.int64)
        _, g = np.unique(key, axis=0, return_inverse=True)
        g = g.ravel()
        ng = int(g.max()) + 1 if len(g) else 0
        # ---- face edges: occurrence o = 3 f + k, edge (F[f, k], F[f, k+1])
        A = F.reshape(-1)
        B = F[:, [1, 2, 0]].reshape(-1)
        ga, gb = g[A], g[B]
        swap = ga > gb
        va = np.where(swap, B, A)                   # endpoint with the lower group id
        vb = np.where(swap, A, B)
        lo, hi = np.minimum(ga, gb), np.maximum(ga, gb)
        ekey = lo * ng + hi
        uk, eid, cnt = np.unique(ekey, return_inverse=True, return_counts=True)
        eid = eid.ravel()
        ne = len(uk)
        occ_cnt = cnt[eid]
        Pa, Pb = V[va], V[vb]
        Na, Nb = N[va], N[vb]
        e = Pb - Pa
        L = np.linalg.norm(e, axis=1)
        # face normals, and whether the face's vertex normals describe a curved patch around it
        v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        fn = _unit(np.cross(v1 - v0, v2 - v0))
        fn_ok = np.ones(nf, bool)
        dev = np.zeros(nf)
        for k in range(3):
            ck = np.sum(N[F[:, k]] * fn, 1)
            fn_ok &= ck > cos_dev
            dev = np.maximum(dev, np.arccos(np.clip(ck, -1.0, 1.0)))
        turn = np.zeros(nf)
        for i, j in ((0, 1), (1, 2), (2, 0)):
            turn = np.maximum(turn, np.arccos(np.clip(np.sum(N[F[:, i]] * N[F[:, j]], 1), -1.0, 1.0)))
        fn_ok &= dev <= DEV_RATIO * turn + EPS_ANG
        occ_face = np.repeat(np.arange(nf), 3)
        wab, wba = np.sum(e * Na, 1), -np.sum(e * Nb, 1)
        s_edge = (wab * wba < 0) & (np.minimum(np.abs(wab), np.abs(wba)) > L * np.sin(np.radians(S_DEG)))
        fn_ok &= ~s_edge.reshape(nf, 3).any(1)
        # ---- the occurrences of each edge
        order = np.argsort(eid, kind="stable")
        first = np.zeros(ne, np.int64)
        first[1:] = np.cumsum(cnt)[:-1]
        o1 = order[first]                                   # first occurrence of each edge
        o2 = order[np.minimum(first + 1, len(order) - 1)]   # second (only meaningful where cnt == 2)
        # the mesh must bend round the face (across its smooth edges: a crease to the next surface does not count)
        # about as much as its vertex normals turn: a flat region (coplanar neighbours) whose normals carry a rounding
        # from next door -- a seat base on the floor, a carry-through clamped flat -- is not bowed
        two_ = cnt == 2
        j1, j2 = o1[two_], o2[two_]
        sm_ = (np.sum(Na[j1] * Na[j2], 1) > cos_crease) & (np.sum(Nb[j1] * Nb[j2], 1) > cos_crease)
        fa_, fb_ = occ_face[j1[sm_]], occ_face[j2[sm_]]               # across smooth edges only (not creases)
        dih = np.arccos(np.clip(np.sum(fn[fa_] * fn[fb_], 1), -1.0, 1.0))
        bend = np.zeros(nf)
        np.maximum.at(bend, fa_, dih)
        np.maximum.at(bend, fb_, dih)
        fn_ok &= bend >= BEND_RATIO * turn - EPS_ANG
        occ_ok = fn_ok[occ_face] & (L > 0) & (np.sum(Na * Nb, 1) > cos_turn)
        # per occurrence: its own PN bow and the mean normal of its side
        bow = pn_midpoint_bow(Pa, Pb, Na, Nb)
        nbar = _unit(Na + Nb)
        s_occ = np.sum(bow * nbar, 1)
        d = np.zeros((ne, 3))
        bowable = np.zeros(ne, bool)
        two = cnt == 2                                      # (one face: an open boundary, kept as built)
        i1, i2 = o1[two], o2[two]
        c_a = np.sum(Na[i1] * Na[i2], 1)                    # same endpoint (va has the lower group id on both)
        c_b = np.sum(Nb[i1] * Nb[i2], 1)
        smooth = (c_a > cos_crease) & (c_b > cos_crease)
        na_m, nb_m = _unit(Na[i1] + Na[i2]), _unit(Nb[i1] + Nb[i2])
        d_s = pn_midpoint_bow(Pa[i1], Pb[i1], na_m, nb_m)
        c = np.sum(nbar[i1] * nbar[i2], 1)
        den = np.maximum(1.0 - c * c, 1e-12)
        s1, s2 = s_occ[i1], s_occ[i2]
        x = (s1 - c * s2) / den
        y = (s2 - c * s1) / den
        d_c = x[:, None] * nbar[i1] + y[:, None] * nbar[i2]
        crease_ok = (~smooth) & (c > cos_fold) & (den > np.sin(np.radians(CREASE_DEG)) ** 2)
        dd = np.where(smooth[:, None], d_s, np.where(crease_ok[:, None], d_c, 0.0))
        d[two] = dd
        bowable[two] = (smooth | crease_ok) & occ_ok[i1] & occ_ok[i2]
        Le = L[o1]
        dn = np.linalg.norm(d, axis=1)
        bowable &= dn <= bow_max
        # the new point may tilt the two sub-triangles next to it no further than the face's own vertex normals lean
        # (+ 2 deg): a sliver (small height over a long edge) must not fold -- cap |d| at h tan(dev + 2 deg) of each
        # face beside the edge, and at a quarter of the edge
        area2 = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
        h_occ = area2[occ_face] / np.maximum(L, 1e-300)
        cap_occ = h_occ * np.tan(np.minimum(dev[occ_face] + np.radians(2.0), np.radians(15.0)))
        cap = np.minimum(0.25 * Le, cap_occ[o1])
        cap[two] = np.minimum(cap[two], cap_occ[o2[two]])
        d *= np.minimum(1.0, cap / np.maximum(dn, 1e-300))[:, None]
        d[~bowable] = 0.0
        dn = np.linalg.norm(d, axis=1)
        # ---- split decision per edge
        split = np.zeros(ne, bool)
        if curv_on:
            split |= bowable & (dn > tol)
            if cos_split is not None:
                ct = np.sum(Na * Nb, 1)                      # end-normal turn per occurrence; the edge's: the larger
                c_edge = ct[o1].copy()
                c_edge[two] = np.minimum(ct[i1], ct[i2])
                split |= bowable & (c_edge < cos_split) & (dn > min_sag)
        if field_on:
            fv = np.asarray(field(V), float)
            if fv.ndim == 1:
                fv = fv[:, None]
            fa, fb = fv[va[o1]], fv[vb[o1]]
            cross = np.any((fa < 0) != (fb < 0), axis=1)
            near = np.any((np.abs(fa) < field_near * Le[:, None]) & (np.abs(fb) < field_near * Le[:, None]), axis=1)
            split |= cross | near
        split &= Le > min_len
        if keep_boundary:
            split &= cnt >= 2
        if not split.any():
            break
        # ---- new vertices: one per (mesh, original vertex pair) on a split edge
        occ_split = split[eid]
        so = np.nonzero(occ_split)[0]
        a_s, b_s = np.minimum(A[so], B[so]), np.maximum(A[so], B[so])
        vkey = np.stack([vm[A[so]], a_s, b_s], 1)
        uvk, inv = np.unique(vkey, axis=0, return_inverse=True)
        inv = inv.ravel()
        nn = len(uvk)
        rep = np.zeros(nn, np.int64)
        rep[inv] = so                                        # one occurrence per new vertex
        ed = eid[rep]
        Pm = 0.5 * (V[A[rep]] + V[B[rep]]) + d[ed]
        Nm = pn_mid_normal(V[A[rep]], V[B[rep]], N[A[rep]], N[B[rep]])
        # an un-bowed (crease / fold) split keeps its own side's plain mean normal
        flat = ~bowable[ed]
        if flat.any():
            Nm[flat] = _unit(N[A[rep[flat]]] + N[B[rep[flat]]])
        UVm = 0.5 * (UV[A[rep]] + UV[B[rep]])
        base = len(V)
        mid_of_occ = np.full(3 * nf, -1, np.int64)
        mid_of_occ[so] = base + inv
        V = np.vstack([V, Pm])
        N = np.vstack([N, Nm])
        UV = np.vstack([UV, UVm])
        vm = np.concatenate([vm, uvk[:, 0]])
        # ---- re-triangulate
        M = mid_of_occ.reshape(nf, 3)                      # midpoint of edge k = (F[:, k], F[:, k+1]) or -1
        S = M >= 0
        pat = S[:, 0] * 1 + S[:, 1] * 2 + S[:, 2] * 4
        newF, newM = [F[pat == 0]], [fm[pat == 0]]
        for r in range(3):                                   # one split edge: edge r
            sel = pat == (1 << r)
            if not sel.any():
                continue
            a, b, cc = F[sel, r], F[sel, (r + 1) % 3], F[sel, (r + 2) % 3]
            m_ = M[sel, r]
            newF += [np.stack([a, m_, cc], 1), np.stack([m_, b, cc], 1)]
            newM += [fm[sel]] * 2
        for r in range(3):                                   # two split edges: r and r+1 (edge r+2 kept)
            sel = pat == ((1 << r) | (1 << ((r + 1) % 3)))
            if not sel.any():
                continue
            a, b, cc = F[sel, r], F[sel, (r + 1) % 3], F[sel, (r + 2) % 3]
            mab, mbc = M[sel, r], M[sel, (r + 1) % 3]
            # corner triangle at b, then the quad a, mab, mbc, cc split along its shorter diagonal
            d1 = np.linalg.norm(V[a] - V[mbc], axis=1)
            d2 = np.linalg.norm(V[mab] - V[cc], axis=1)
            use1 = (d1 <= d2)[:, None]
            t1 = np.where(use1, np.stack([a, mab, mbc], 1), np.stack([a, mab, cc], 1))
            t2 = np.where(use1, np.stack([a, mbc, cc], 1), np.stack([mab, mbc, cc], 1))
            newF += [np.stack([mab, b, mbc], 1), t1, t2]
            newM += [fm[sel]] * 3
        sel = pat == 7
        if sel.any():
            a, b, cc = F[sel, 0], F[sel, 1], F[sel, 2]
            m0, m1, m2 = M[sel, 0], M[sel, 1], M[sel, 2]
            newF += [np.stack([a, m0, m2], 1), np.stack([m0, b, m1], 1), np.stack([m2, m1, cc], 1),
                     np.stack([m0, m1, m2], 1)]
            newM += [fm[sel]] * 4
        F = np.vstack(newF)
        fm = np.concatenate(newM)

    # ---- back to one mesh per input mesh
    out = []
    for i, m in enumerate(meshes):
        vi = np.nonzero(vm == i)[0]
        fi = F[fm == i]
        remap = np.full(len(V), -1, np.int64)
        remap[vi] = np.arange(len(vi))
        mm = Mesh(V[vi], remap[fi], N[vi], UV[vi] if has_uv[i] else None)
        for attr, val in vars(m).items():         # builder flags (_reveal, _no_paint, ...) travel with the mesh
            if attr.startswith("_"):
                setattr(mm, attr, val)
        out.append(mm)
    return out
