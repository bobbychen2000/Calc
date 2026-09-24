"""
Pilatus PC-12 NGX "Model Building Plan" -> reference geometry registered in MODEL coordinates.

Source: Pilatus drawing no. 190.10.40.432 "PC-12 MODELL ZEICHNUNG / MODEL DRAWING SN2001UP"
(MSN 2001+ = NGX), sheets 1 and 2, published by Pilatus as a model-building plan:
    https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf
The PDF and everything derived from it (polylines, debug images) stay in the git-ignored
refs/cache/ and out/tmp/ folders -- the repository is public, only this code is tracked.

Pipeline (all automatic, re-runnable; the processed result is cached by PDF hash + CODE_VERSION):
  1. fetch()                     download the PDF if refs/cache/ does not have it
  2. extraction (page 8 / 9)     stroke items -> polylines (Bezier items flattened), dash patterns
                                 re-assembled into 'centerline' (dash-dot / phantom) and 'hidden'
                                 (dashed) chains, solid pieces joined end-to-end and simplified
  3. classification              arrowheads, dimension lines, extension lines, hatch + ground line,
                                 stroked label text, leaders -> kind 'annotation' (with a 'tag');
                                 the rest is 'outline'
  4. view separation             dilated-raster connectivity + one seed point per view on its main
                                 outline; small groups (labels, dims) go to the nearest view
  5. registration                scale from the labelled frame stations (least squares over the 11
                                 station lines EF1..FR40), side view z from the drawn ground line,
                                 x from the spinner tip (default) or alternative anchors; plan and
                                 front views anchored on their own features (spinner tip,
                                 centre line, ground / propeller centre) with the same scale
  6. named features              cockpit glazing loops per view, cabin windows / doors (side view),
                                 fuselage profile lines near the cockpit, frame sections

Model coordinates: x = station [m] aft of the W&B datum, y = butt line (+ starboard), z = water line
(ground = 0).  Views: 'side' -> (x, z) seen from PORT; 'plan' -> (x, y) seen from above;
'front' -> (y, z) seen from ahead (starboard = +y appears on the viewer's LEFT); sections -> (y, z)
at station x.

Usage:
    from refs import mbp
    d = mbp.load()                       # default anchor: spinner tip at STA 0.39
    d['glazing']['side']['sw_port']      # (N, 2) closed polyline in (x, z)
    python3 -m refs.mbp                  # registration table + debug images in out/tmp/mbp/
"""
from __future__ import annotations

import hashlib
import json
import math
import pickle
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = HERE / "cache"
PDF_NAME = "PC-12-NGX-Model-Building-Plan.pdf"
SRC_URL = ("https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/"
           "PC-12-NGX-Model-Building-Plan.pdf")
DEBUG_DIR = ROOT / "out" / "tmp" / "mbp"
CODE_VERSION = 1

PT = 25.4 / 72.0            # mm per PDF point
NOMINAL_SCALE = 24.0        # "MASSTAB 1:24"

KINDS = ("outline", "hidden", "centerline", "annotation")


# =============================================================================================
# 1. fetch
# =============================================================================================
def pdf_path() -> Path:
    return CACHE / PDF_NAME


def fetch(force: bool = False) -> Path:
    """Download the Pilatus PDF into refs/cache/ (git-ignored) unless it is already there."""
    p = pdf_path()
    if p.exists() and p.stat().st_size > 100_000 and not force:
        return p
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".part")
    req = urllib.request.Request(SRC_URL, headers={"User-Agent": "Mozilla/5.0 (pc12 refs/mbp.py)"})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            f.write(b)
    head = tmp.read_bytes()[:5]
    if head != b"%PDF-":
        tmp.unlink()
        raise RuntimeError(f"download of {SRC_URL} did not return a PDF")
    tmp.replace(p)
    return p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# =============================================================================================
# 2. geometry helpers
# =============================================================================================
def _rdp(P: np.ndarray, eps: float) -> np.ndarray:
    """Ramer-Douglas-Peucker simplification (iterative).  Merges collinear / contiguous pieces."""
    n = len(P)
    if n < 3:
        return P
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a = P[i]
        d = P[j] - a
        L = math.hypot(d[0], d[1])
        seg = P[i + 1:j] - a
        if L < 1e-12:
            dist = np.hypot(seg[:, 0], seg[:, 1])
        else:
            dist = np.abs(seg[:, 0] * d[1] - seg[:, 1] * d[0]) / L
        k = int(np.argmax(dist))
        if dist[k] > eps:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return P[keep]


def plen(P: np.ndarray) -> float:
    if len(P) < 2:
        return 0.0
    d = np.diff(P, axis=0)
    return float(np.hypot(d[:, 0], d[:, 1]).sum())


def _straightness(P: np.ndarray):
    """(chord length, max deviation from the chord)."""
    a, b = P[0], P[-1]
    d = b - a
    L = math.hypot(d[0], d[1])
    if L < 1e-9:
        return 0.0, float(np.hypot(*(P - a).T).max()) if len(P) > 1 else 0.0
    dev = np.abs((P[:, 0] - a[0]) * d[1] - (P[:, 1] - a[1]) * d[0]) / L
    return L, float(dev.max())


def _is_closed(P: np.ndarray, tol: float = 0.05) -> bool:
    return len(P) > 3 and math.hypot(*(P[0] - P[-1])) < tol


def densify(P: np.ndarray, step: float) -> np.ndarray:
    if len(P) < 2:
        return P
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        L = math.hypot(*(b - a))
        n = max(1, int(math.ceil(L / step)))
        t = (np.arange(1, n + 1) / n)[:, None]
        out.append(a + (b - a) * t)
    return np.vstack(out)


def _seg_point_dist(A, B, p):
    """Distance from point p to segments A[i]-B[i] (vectorised) and the parameter t."""
    d = B - A
    L2 = (d * d).sum(1)
    t = np.where(L2 > 0, ((p - A) * d).sum(1) / np.maximum(L2, 1e-18), 0.0)
    t = np.clip(t, 0, 1)
    q = A + d * t[:, None]
    return np.hypot(*(q - p).T), t


class _UF:
    def __init__(self, n):
        self.p = np.arange(n)

    def find(self, a):
        p = self.p
        r = a
        while p[r] != r:
            r = p[r]
        while p[a] != r:
            p[a], a = r, p[a]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)

    def labels(self):
        return np.array([self.find(i) for i in range(len(self.p))])


# =============================================================================================
# 3. extraction: stroke items -> pieces -> dash chains / joined polylines
# =============================================================================================
def _bezier(p0, p1, p2, p3, n):
    t = np.linspace(0.0, 1.0, n + 1)[:, None]
    P = [np.array([q.x, q.y]) for q in (p0, p1, p2, p3)]
    return (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]


def _read_pieces(page, tol=2e-3):
    """Every stroked path item -> consecutive items with coincident ends chained into pieces."""
    pieces = []
    for path in page.get_drawings():
        if path.get("type") not in ("s", "fs"):
            continue
        cur = None
        for it in path["items"]:
            op = it[0]
            if op == "l":
                pts = np.array([[it[1].x, it[1].y], [it[2].x, it[2].y]])
            elif op == "c":
                L = it[1].distance_to(it[2]) + it[2].distance_to(it[3]) + it[3].distance_to(it[4])
                pts = _bezier(it[1], it[2], it[3], it[4], max(2, min(96, int(L / 0.25) + 2)))
            elif op == "re":
                r = it[1]
                pts = np.array([[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1], [r.x0, r.y0]])
            elif op == "qu":
                q = it[1]
                pts = np.array([[q.ul.x, q.ul.y], [q.ur.x, q.ur.y], [q.lr.x, q.lr.y],
                                [q.ll.x, q.ll.y], [q.ul.x, q.ul.y]])
                if np.ptp(pts[:, 0]) < 1e-3 or np.ptp(pts[:, 1]) < 1e-3:   # degenerate quad = line
                    k = np.argmax(((pts - pts[0]) ** 2).sum(1))
                    pts = pts[[0, k]]
            else:
                continue
            if cur is not None and abs(cur[-1][0] - pts[0][0]) < tol and abs(cur[-1][1] - pts[0][1]) < tol:
                cur.extend(pts[1:])
            else:
                if cur is not None:
                    pieces.append(np.array(cur))
                cur = list(pts)
        if cur is not None:
            pieces.append(np.array(cur))
    return pieces


DASH_MAX = 20.0      # pt, longest dash of any line type on the sheet (long dash ~8.5 / 16.4 pt)
DOT_MAX = 0.3        # pt
GAP_MIN, GAP_MAX = 0.8, 5.0


def _dash_chains(pieces):
    """Find dash / dash-dot sequences.  Returns list of (piece index list, kind)."""
    from scipy.spatial import cKDTree
    n = len(pieces)
    L = np.array([plen(P) for P in pieces])
    closed = np.array([_is_closed(P) for P in pieces])
    cand = np.where((L <= DASH_MAX) & ~closed)[0]
    # end records
    rec_pt, rec_t, rec_piece, rec_dot = [], [], [], []
    for i in cand:
        P = pieces[i]
        if L[i] < DOT_MAX:
            rec_pt.append(P.mean(0)); rec_t.append((np.nan, np.nan)); rec_piece.append(i); rec_dot.append(True)
            continue
        chord, dev = _straightness(P)
        if chord < 0.5 * L[i]:          # strongly curved / folded -> not a dash
            continue
        for end in (0, 1):
            Q = P if end == 1 else P[::-1]
            e = Q[-1]
            # outward tangent from a point >= min(0.6, L/2) back along the piece
            back = min(0.6, 0.5 * L[i])
            acc, k = 0.0, len(Q) - 1
            while k > 0 and acc < back:
                acc += math.hypot(*(Q[k] - Q[k - 1]))
                k -= 1
            t = e - Q[k]
            nt = math.hypot(*t)
            if nt < 1e-9:
                continue
            rec_pt.append(e); rec_t.append(t / nt); rec_piece.append(i); rec_dot.append(False)
    rec_pt = np.array(rec_pt); rec_t = np.array(rec_t)
    rec_piece = np.array(rec_piece); rec_dot = np.array(rec_dot)
    tree = cKDTree(rec_pt)
    cos12, cos20 = math.cos(math.radians(12)), math.cos(math.radians(20))
    links = []
    for a in np.where(~rec_dot)[0]:
        e, t = rec_pt[a], rec_t[a]
        for b in tree.query_ball_point(e, GAP_MAX):
            if rec_piece[b] == rec_piece[a]:
                continue
            g = rec_pt[b] - e
            d = math.hypot(*g)
            if d < GAP_MIN:
                continue
            gu = g / d
            if gu @ t < cos12:
                continue
            off = abs(g[0] * t[1] - g[1] * t[0])
            if off > max(0.25, 0.1 * d):
                continue
            if not rec_dot[b] and (rec_t[b] @ -t) < cos20:
                continue
            links.append((d, a, b))
    links.sort()
    cap = {}
    dot_dirs = {}
    adj = {}
    for d, a, b in links:
        if cap.get(a, 0) >= 1:
            continue
        if rec_dot[b]:
            if cap.get(b, 0) >= 2:
                continue
            v = rec_pt[a] - rec_pt[b]
            v = v / np.linalg.norm(v)
            if b in dot_dirs and (dot_dirs[b] @ v) > -0.85:
                continue
            dot_dirs.setdefault(b, v)
        else:
            if cap.get(b, 0) >= 1:
                continue
            # the reverse link must be geometrically valid as well (it is, by symmetry of tests)
        cap[a] = cap.get(a, 0) + 1
        cap[b] = cap.get(b, 0) + 1
        pa, pb = rec_piece[a], rec_piece[b]
        adj.setdefault(pa, set()).add(pb)
        adj.setdefault(pb, set()).add(pa)
    # connected components of the link graph
    seen = set()
    chains = []
    for s in adj:
        if s in seen:
            continue
        comp, stack = [], [s]
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        if len(comp) < 3:
            continue
        # order: start at a piece with a single neighbour (open chain) else anywhere (closed)
        ends = [u for u in comp if len(adj[u]) == 1]
        start = ends[0] if ends else comp[0]
        order, prev, u = [start], None, start
        while True:
            nxt = [v for v in adj[u] if v != prev and v not in order]
            if not nxt:
                break
            prev, u = u, nxt[0]
            order.append(u)
        if len(order) < len(comp):     # branched (should not happen) -> keep the walk
            pass
        lens = L[order]
        ndot = int((lens < DOT_MAX).sum())
        dashes = lens[lens >= DOT_MAX]
        if ndot > 0:
            kind = "centerline"
        elif len(dashes) >= 3 and dashes.max() > 2.5 * np.median(dashes) and dashes.min() < 0.5 * dashes.max():
            kind = "centerline"           # long-short (phantom / chain) line
        else:
            kind = "hidden"
        chains.append((order, kind))
    return chains


def _chain_polyline(pieces, order):
    """Concatenate ordered dash pieces into one polyline (gaps bridged)."""
    out = []
    for k, i in enumerate(order):
        P = pieces[i]
        if len(P) == 1 or plen(P) < DOT_MAX:
            out.append(P.mean(0)[None])
            continue
        if out:
            last = out[-1][-1]
            if np.hypot(*(P[-1] - last)) < np.hypot(*(P[0] - last)):
                P = P[::-1]
        elif k + 1 < len(order):
            Pn = pieces[order[k + 1]]
            cn = Pn.mean(0)
            if np.hypot(*(P[0] - cn)) < np.hypot(*(P[-1] - cn)):
                P = P[::-1]
        out.append(P)
    return np.vstack(out)


def _join(pieces, tol=0.03):
    """Join pieces whose endpoints meet pairwise (node degree 2).  Junctions stay split."""
    from scipy.spatial import cKDTree
    n = len(pieces)
    if n == 0:
        return []
    E = np.array([[P[0], P[-1]] for P in pieces]).reshape(-1, 2)
    uf = _UF(len(E))
    for a, b in cKDTree(E).query_pairs(tol):
        uf.union(a, b)
    lab = uf.labels()
    cnt = np.bincount(lab, minlength=len(E))
    partner = -np.ones(len(E), int)
    order = np.argsort(lab, kind="stable")
    ls = lab[order]
    for k in range(len(order) - 1):
        a, b = order[k], order[k + 1]
        if ls[k] == ls[k + 1] and cnt[ls[k]] == 2:
            partner[a], partner[b] = b, a
    used = np.zeros(n, bool)
    out = []

    def walk(start_piece, start_end):
        """Follow from piece entering at start_end (0 = enter at P[0])."""
        seq = []
        i, ent = start_piece, start_end
        while True:
            used[i] = True
            P = pieces[i] if ent == 0 else pieces[i][::-1]
            seq.append(P if not seq else P[1:])
            ex = 2 * i + (1 - ent)          # exit endpoint index
            q = partner[ex]
            if q < 0:
                break
            j, jent = q // 2, q % 2
            if used[j]:
                break
            i, ent = j, jent
        return np.vstack(seq)

    for i in range(n):
        if used[i]:
            continue
        # walk backwards to a chain start
        j, ent = i, 0
        visited = {i}
        while True:
            q = partner[2 * j + ent]           # endpoint through which we would enter j
            if q < 0:
                break
            k = q // 2
            if k in visited:
                break                          # cycle
            visited.add(k)
            j, ent = k, 1 - (q % 2)
        out.append(walk(j, ent))
    return out


# =============================================================================================
# 4. annotation classification
# =============================================================================================
def _find_arrows(polys, idx):
    """Arrowheads: two sides of equal length 4..16 pt meeting at a sharp tip + a base edge.
    Returns (arrows list of dict(tip, axis, length), set of (poly, edge) consumed)."""
    from scipy.spatial import cKDTree
    edges, eowner = [], []
    for i in idx:
        P = polys[i]
        if len(P) > 6:
            continue
        for k in range(len(P) - 1):
            if math.hypot(*(P[k + 1] - P[k])) > 0.05:
                edges.append((P[k], P[k + 1]))
                eowner.append((i, k))
    if not edges:
        return [], set()
    A = np.array([e[0] for e in edges]); B = np.array([e[1] for e in edges])
    ends = np.vstack([A, B])
    tree = cKDTree(ends)
    m = len(edges)
    arrows, used = [], set()
    base_tree = cKDTree(np.hstack([np.minimum(A, B), np.maximum(A, B)]))  # not used for lookup
    endtree = tree
    for u, v in tree.query_pairs(0.06):
        eu, ev = u % m, v % m
        if eu == ev:
            continue
        s = ends[u]
        a = B[eu] if u < m else A[eu]
        b = B[ev] if v < m else A[ev]
        la, lb = math.hypot(*(a - s)), math.hypot(*(b - s))
        if not (4.0 <= la <= 16.0 and 4.0 <= lb <= 16.0 and 0.8 <= la / lb <= 1.25):
            continue
        cosang = ((a - s) @ (b - s)) / (la * lb)
        ang = math.degrees(math.acos(max(-1.0, min(1.0, cosang))))
        if not (5.0 <= ang <= 36.0):
            continue
        # base edge a-b
        ia = endtree.query_ball_point(a, 0.15)
        ib = set(x % m for x in endtree.query_ball_point(b, 0.15))
        base = [x % m for x in ia if (x % m) in ib and (x % m) not in (eu, ev)]
        if not base:
            continue
        mid = 0.5 * (a + b)
        axis = s - mid
        axis /= np.linalg.norm(axis)
        arrows.append(dict(tip=s.copy(), axis=axis, length=0.5 * (la + lb)))
        used.update([eowner[eu], eowner[ev], eowner[base[0]]])
    # dedupe arrows with the same tip+axis
    uniq = []
    for a in arrows:
        if not any(np.hypot(*(a["tip"] - b["tip"])) < 0.1 and a["axis"] @ b["axis"] > 0.99 for b in uniq):
            uniq.append(a)
    return uniq, used


def _split_edges(P, drop):
    """Remove edge indices `drop` from polyline P -> list of remaining runs."""
    runs, cur = [], [P[0]]
    for k in range(len(P) - 1):
        if k in drop:
            if len(cur) > 1:
                runs.append(np.array(cur))
            cur = [P[k + 1]]
        else:
            cur.append(P[k + 1])
    if len(cur) > 1:
        runs.append(np.array(cur))
    return runs


def _text_words(polys, idx, max_char=16.0):
    """Stroked label text: small blobs aligned in rows (same cap-height extent on one page axis).
    Returns (set of poly indices that are text, list of word boxes (x0,y0,x1,y1,axis))."""
    from scipy.spatial import cKDTree
    small = [i for i in idx if np.ptp(polys[i][:, 0]) <= max_char and np.ptp(polys[i][:, 1]) <= max_char]
    if not small:
        return set(), []
    pts, own = [], []
    for i in small:
        D = densify(polys[i], 0.2)
        pts.append(D)
        own.append(np.full(len(D), i))
    pts = np.vstack(pts); own = np.concatenate(own)
    uf = _UF(len(small))
    pos = {i: k for k, i in enumerate(small)}
    for a, b in cKDTree(pts).query_pairs(0.15):
        if own[a] != own[b]:
            uf.union(pos[own[a]], pos[own[b]])
    lab = uf.labels()
    blobs = {}
    for k, i in enumerate(small):
        blobs.setdefault(lab[k], []).append(i)
    bl = []
    for members in blobs.values():
        P = np.vstack([polys[i] for i in members])
        lo, hi = P.min(0), P.max(0)
        if (hi - lo).max() <= max_char:
            bl.append((lo, hi, members))
    if not bl:
        return set(), []
    lo = np.array([b[0] for b in bl]); hi = np.array([b[1] for b in bl])
    text, words = set(), []
    # axis 0: cap height along page x (rotated text, reads along y); axis 1: along page y
    for ax in (0, 1):
        o = 1 - ax
        h = hi[:, ax] - lo[:, ax]
        ok = (h >= 3.0) & (h <= 14.0)
        uf2 = _UF(len(bl))
        c = 0.5 * (lo + hi)
        tree = cKDTree(c)
        for a, b in tree.query_pairs(20.0):
            if not (ok[a] and ok[b]):
                continue
            if abs(lo[a, ax] - lo[b, ax]) > 0.45 or abs(hi[a, ax] - hi[b, ax]) > 0.45:
                continue
            gap = max(lo[a, o], lo[b, o]) - min(hi[a, o], hi[b, o])
            if gap > 0.9 * h[a] or gap < -0.5:
                continue
            uf2.union(a, b)
        l2 = uf2.labels()
        groups = {}
        for k in range(len(bl)):
            groups.setdefault(l2[k], []).append(k)
        for g in groups.values():
            if len(g) < 2:
                continue
            glo = lo[g].min(0); ghi = hi[g].max(0)
            words.append((glo[0], glo[1], ghi[0], ghi[1], ax))
            for k in g:
                text.update(bl[k][2])
    # punctuation / single glyphs sitting inside or right next to a word box
    for k, (blo, bhi, members) in enumerate(bl):
        if members[0] in text:
            continue
        for (x0, y0, x1, y1, ax) in words:
            ch = (x1 - x0) if ax == 0 else (y1 - y0)
            m = 0.6 * ch
            if blo[0] >= x0 - m and bhi[0] <= x1 + m and blo[1] >= y0 - m and bhi[1] <= y1 + m:
                text.update(members)
                break
    return text, words


def _find_hatch(polys, idx):
    """Hatching: >= 8 parallel straight strokes of equal length, regularly spaced."""
    info = []
    for i in idx:
        P = polys[i]
        if len(P) != 2:
            continue
        d = P[1] - P[0]
        L = math.hypot(*d)
        if not (3.0 <= L <= 40.0):
            continue
        ang = math.degrees(math.atan2(d[1], d[0])) % 180.0
        info.append((i, ang, L, 0.5 * (P[0] + P[1])))
    groups = {}
    for i, ang, L, c in info:
        groups.setdefault((round(ang / 0.5), round(L / 0.3)), []).append((i, c))
    out = set()
    for key, mem in groups.items():
        if len(mem) < 8:
            continue
        C = np.array([c for _, c in mem])
        # members must form a run: each has a neighbour within 10 pt
        from scipy.spatial import cKDTree
        dd, _ = cKDTree(C).query(C, k=2)
        ok = dd[:, 1] < 10.0
        if ok.sum() >= 8:
            out.update(i for (i, _), o in zip(mem, ok) if o)
    return out


def _extract_page(page):
    """All stroked geometry of a page -> list of dict(pts, kind, tag) in PAGE points."""
    raw = _read_pieces(page)
    pieces = [_rdp(P, 0.01) for P in raw]
    chains = _dash_chains(pieces)
    in_chain = set(i for order, _ in chains for i in order)
    items = []
    for order, kind in chains:
        items.append(dict(pts=_chain_polyline(pieces, order), kind=kind,
                          tag="centerline" if kind == "centerline" else "hidden"))
    solid_idx = [i for i in range(len(pieces)) if i not in in_chain]
    arrows, used = _find_arrows(pieces, solid_idx)
    drop = {}
    for i, k in used:
        drop.setdefault(i, set()).add(k)
    rest = []
    for i in solid_idx:
        P = pieces[i]
        if i in drop:
            for k in sorted(drop[i]):
                items.append(dict(pts=P[k:k + 2].copy(), kind="annotation", tag="arrow"))
            rest.extend(_split_edges(P, drop[i]))
        else:
            rest.append(P)
    joined = [_rdp(P, 0.01) for P in _join(rest)]
    tags = [None] * len(joined)
    st = [_straightness(P) for P in joined]
    straight = np.array([(dev < 0.06 and ch > 1.0) for ch, dev in st])
    # --- dimension and extension lines through arrow tips
    S = [i for i in range(len(joined)) if straight[i]]
    if S and arrows:
        A = np.array([joined[i][0] for i in S]); B = np.array([joined[i][-1] for i in S])
        D = B - A
        Dn = D / np.linalg.norm(D, axis=1, keepdims=True)
        for ar in arrows:
            dist, _ = _seg_point_dist(A, B, ar["tip"])
            c = np.abs(Dn @ ar["axis"])
            for k in np.where(dist < 0.3)[0]:
                i = S[k]
                if c[k] > 0.998:
                    tags[i] = "dim"
                elif c[k] < 0.05 and tags[i] is None:
                    tags[i] = "ext"
    # --- extension lines continuing a centre line (station / reference lines)
    cl = [it["pts"] for it in items if it["kind"] == "centerline"]
    if cl:
        from scipy.spatial import cKDTree
        cends = np.array([[P[0], P[-1]] for P in cl]).reshape(-1, 2)
        cdir = []
        for P in cl:
            d = P[-1] - P[0]
            n = np.linalg.norm(d)
            cdir.append(d / n if n > 0 else np.zeros(2))
        cdir = np.repeat(np.array(cdir), 2, axis=0)
        ct = cKDTree(cends)
        for i in S:
            if tags[i] is not None:
                continue
            P = joined[i]
            d = P[-1] - P[0]
            d = d / np.linalg.norm(d)
            for e in (P[0], P[-1]):
                for q in ct.query_ball_point(e, 0.15):
                    if abs(cdir[q] @ d) > 0.9998:
                        tags[i] = "ext"
    # --- hatch + ground line
    free = [i for i in range(len(joined)) if tags[i] is None]
    hatch = _find_hatch(joined, free)
    for i in hatch:
        tags[i] = "hatch"
    if hatch:
        H = np.vstack([joined[i] for i in hatch])
        for i in S:
            if tags[i] is not None or np.hypot(*(joined[i][-1] - joined[i][0])) < 100:
                continue
            dist = np.array([_seg_point_dist(joined[i][:1], joined[i][1:], h)[0][0] for h in H[::2]])
            dist2 = np.array([_seg_point_dist(joined[i][:1], joined[i][1:], h)[0][0] for h in H[1::2]])
            if ((dist < 0.3) | (dist2 < 0.3)).sum() >= 8:
                tags[i] = "ground"
    # --- stroked text
    free = [i for i in range(len(joined)) if tags[i] is None]
    text, words = _text_words(joined, free)
    for i in text:
        tags[i] = "text"
    # --- leaders: short straight lines starting at a word box
    for i in S:
        if tags[i] is not None:
            continue
        P = joined[i]
        if np.hypot(*(P[-1] - P[0])) > 200:
            continue
        for (x0, y0, x1, y1, ax) in words:
            for e in (P[0], P[-1]):
                if x0 - 3 <= e[0] <= x1 + 3 and y0 - 3 <= e[1] <= y1 + 3:
                    tags[i] = "leader"
    for P, t in zip(joined, tags):
        items.append(dict(pts=P, kind="outline" if t is None else "annotation", tag=t or "outline"))
    for it in items:
        it["pts"] = np.asarray(it["pts"], float)
    return items, arrows, words


# =============================================================================================
# debug: page-coordinate plot (rotated so the sheet reads like the paper, nose left)
# =============================================================================================
_COL = dict(outline="k", hidden="tab:orange", centerline="tab:blue", annotation="tab:green")


def plot_page(items, path, clip=None, lw=0.4, dpi=150, size=None, tags=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x0, y0, x1, y1 = clip if clip else (0, 0, 2376, 3362)
    w, h = (y1 - y0), (x1 - x0)
    s = size or 16.0 / max(w, h) * max(w, h)
    fig = plt.figure(figsize=(16, 16 * h / w) if w >= h else (16 * w / h, 16))
    ax = fig.add_axes([0.04, 0.04, 0.94, 0.94])
    for it in items:
        P = it["pts"]
        if clip and (P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].max() < y0 or P[:, 1].min() > y1):
            continue
        c = _COL[it["kind"]]
        if tags and it["kind"] == "annotation":
            c = dict(text="tab:green", arrow="red", dim="tab:purple", ext="tab:olive", hatch="tab:brown",
                     ground="magenta", leader="tab:pink").get(it["tag"], "tab:green")
        if len(P) == 1:
            ax.plot(P[:, 1], P[:, 0], ".", color=c, ms=1)
        else:
            ax.plot(P[:, 1], P[:, 0], "-", color=c, lw=lw)
    ax.set_xlim(y1, y0)
    ax.set_ylim(x1, x0)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.2)
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
