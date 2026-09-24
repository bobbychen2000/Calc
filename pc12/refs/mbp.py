"""
Pilatus PC-12 NGX "Model Building Plan" -> reference geometry registered in MODEL coordinates.

Source: Pilatus drawing no. 190.10.40.432 "PC-12 MODELL ZEICHNUNG / MODEL DRAWING SN2001UP"
(MSN 2001+ = NGX), sheets 1 and 2 (PDF page index 8 and 9), published by Pilatus as a
model-building plan:
    https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf
The PDF and everything derived from it (polylines, cache pickles, debug images) stay in the
git-ignored refs/cache/ and out/tmp/ folders -- the repository is public, only this code is tracked.

Pipeline (automatic and re-runnable; page-level results are cached in refs/cache/ keyed by the PDF
sha256 + CODE_VERSION + a hash of this file, so load() takes a few seconds after the first run):
  1. fetch()             download the PDF if refs/cache/ does not have it
  2. extraction          stroke items -> polylines (Bezier items flattened, duplicates dropped,
                         RDP-merged), dash patterns re-assembled into 'centerline' (dash-dot /
                         long-short) and 'hidden' (dashed) chains, solid pieces joined end-to-end
  3. classification      arrowheads, dimension lines, extension lines, hatch + ground line, stroked
                         label text, reference marks, leaders -> kind 'annotation' with a 'tag';
                         everything else is 'outline'.  'hair' = stroke width 0 (wheels, lamps).
  4. view separation     dilated-raster connectivity of the non-centre-line geometry + seed points
                         on each view's main outline (SEEDS_P8 / SECTION_SEEDS_P8); labels and
                         dimensions join the nearest view; centre lines go to the view they run along
  5. registration        scale = least squares over the 11 labelled frame lines EF1..FR40 (sheet 1,
                         8.45827 mm/pt = 1:23.976, residuals < 0.05 mm) and used for every view;
                         side: z = 0 on the drawn ground line (tyres sit on it), x anchored on the
                         spinner tip = STA 0.39 (default; alternatives 'oml', 'oml_xz', 'aft');
                         plan: own spinner tip + centre line; front: centre line + tyre bottoms
                         (or propeller-circle centre = WL 1.655); frame sections: own centre line +
                         the row reference line, which is the side view's '0' line (WL 1.229);
                         sheet 2 (drawn at ~1:12): scale from its cabin sections, position from
                         the four port cabin windows it shares with sheet 1.
  6. named features      cockpit glazing loops per view (enclosed regions, snapped onto the strokes),
                         cabin windows / doors (side view), fuselage profile lines, sections.

Model coordinates: x = station [m] aft of the W&B datum, y = butt line (+ starboard), z = water line
(ground = 0).  Views: 'side' -> (x, z) seen from PORT; 'plan' -> (x, y) seen from above;
'front' -> (y, z) seen from ahead (starboard = +y is on the viewer's LEFT); frame sections -> (y, z)
at station x (assumed seen from ahead like the front view -- they are symmetric); fin sections
VF -> (x, y) at WL z; tailplane / wing sections HF, WR -> (x, z) at butt line y.

Usage (run from pc12/):
    from refs import mbp
    d = mbp.load()                        # default anchor: spinner tip at STA 0.39
    d['glazing']['side']['sw_port']       # (N, 2) closed polyline in (x, z)
    d['side']                             # [{'pts': (N, 2), 'kind', 'tag', 'hair'}, ...]
    d['meta']['checks']                   # expected vs measured table
    python3 -m refs.mbp [--anchor spinner|oml|oml_xz|aft] [--blender]
                                          # registration table + debug images in out/tmp/mbp/
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
# 1. source PDF
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


def _bbox(P):
    return np.r_[P.min(0), P.max(0)]


def _point_in_poly(p, P):
    x, y = p
    xs, ys = P[:, 0], P[:, 1]
    x1, y1 = np.roll(xs, -1), np.roll(ys, -1)
    c = ((ys > y) != (y1 > y)) & (x < (x1 - xs) * (y - ys) / np.where(y1 != ys, y1 - ys, 1e-12) + xs)
    return bool(c.sum() % 2)


def _area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _circle_fit(P):
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0], c[1]
    r = math.sqrt(max(c[2] + cx * cx + cy * cy, 0.0))
    rms = float(np.sqrt(np.mean((np.hypot(x - cx, y - cy) - r) ** 2)))
    return cx, cy, r, rms


def _arc_fit(P, min_cover=200.0):
    """Circle fit of a (possibly open) arc: (cx, cy, r, rms, coverage_deg) or None."""
    if len(P) < 6 or plen(P) < 10:
        return None
    D = densify(P, 1.0)
    cx, cy, r, rms = _circle_fit(D)
    if not np.isfinite(r) or r <= 0:
        return None
    a = np.sort(np.arctan2(D[:, 1] - cy, D[:, 0] - cx))
    gaps = np.diff(np.r_[a, a[0] + 2 * np.pi])
    cover = 360.0 - math.degrees(gaps.max())
    if cover < min_cover:
        return None
    return cx, cy, r, rms, cover


def _cluster_1d(vals, tol):
    vals = sorted(vals)
    out = []
    for v in vals:
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [float(np.mean(c)) for c in out]


def _clip_seg(P, box):
    """Clip a straight 2-point line to box (x0, y0, x1, y1); None if outside."""
    a, b = P[0], P[-1]
    d = b - a
    t0, t1 = 0.0, 1.0
    for k, lo, hi in ((0, box[0], box[2]), (1, box[1], box[3])):
        if abs(d[k]) < 1e-12:
            if a[k] < lo or a[k] > hi:
                return None
            continue
        ta, tb = (lo - a[k]) / d[k], (hi - a[k]) / d[k]
        t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
    if t1 <= t0:
        return None
    return np.array([a + d * t0, a + d * t1])


# =============================================================================================
# 3. extraction: stroke items -> pieces -> dash chains / joined polylines
# =============================================================================================


def _bezier(p0, p1, p2, p3, n):
    t = np.linspace(0.0, 1.0, n + 1)[:, None]
    P = [np.array([q.x, q.y]) for q in (p0, p1, p2, p3)]
    return (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]


def _read_pieces(page, tol=2e-3, widths=None):
    """Every stroked path item -> consecutive items with coincident ends chained into pieces.
    If `widths` is a list, the stroke width of every piece is appended to it."""
    pieces = []
    for path in page.get_drawings():
        if path.get("type") not in ("s", "fs"):
            continue
        w = float(path.get("width") or 0.0)
        n0 = len(pieces)
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
        if widths is not None:
            widths.extend([w] * (len(pieces) - n0))
    return pieces

DASH_MAX = 24.0      # pt, longest dash of any line type on the sheet (long dash ~8.5 / 16.4 / 21 pt)

DOT_MAX = 0.3        # pt

GAP_MIN, GAP_MAX = 0.8, 5.0


def _dedupe(pieces, tol=0.06):
    """Drop pieces drawn twice (same end points, length and centroid)."""
    from scipy.spatial import cKDTree
    if not pieces:
        return pieces
    sig = []
    for P in pieces:
        a, b = P[0], P[-1]
        if (a[0], a[1]) > (b[0], b[1]):
            a, b = b, a
        c = P.mean(0) if len(P) > 2 else 0.5 * (a + b)
        sig.append([a[0], a[1], b[0], b[1], c[0], c[1], plen(P)])
    sig = np.array(sig)
    drop = set()
    for i, j in sorted(cKDTree(sig).query_pairs(tol)):
        if i not in drop:
            drop.add(j)
    return [P for k, P in enumerate(pieces) if k not in drop]


def _dash_chains(pieces, dash_max=None, gap_max=None):
    """Find dash / dash-dot sequences.  Returns list of (piece index list, kind)."""
    DASH_MAX_ = dash_max or DASH_MAX
    GAP_MAX_ = gap_max or GAP_MAX
    from scipy.spatial import cKDTree
    L = np.array([plen(P) for P in pieces])
    closed = np.array([_is_closed(P) for P in pieces])
    cand = np.where((L <= DASH_MAX_) & ~closed)[0]
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
        for b in tree.query_ball_point(e, GAP_MAX_):
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
        inner = lens[1:-1] if len(lens) > 3 else lens      # end dashes may be truncated
        inner = inner[inner >= DOT_MAX]
        if ndot > 0:
            kind = "centerline"
        elif len(inner) >= 2 and inner.min() < 0.4 * inner.max():
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


def _merge_straight(items, kind, ang_tol=0.05, off_tol=0.12, gap=6.0):
    """Merge duplicated / fragmented straight dashed chains lying on the same line."""
    keep, lines = [], []
    for it in items:
        if it["kind"] != kind:
            keep.append(it)
            continue
        P = it["pts"]
        ch, dev = _straightness(P)
        if ch < 2.0 or dev > 0.1:
            keep.append(it)
            continue
        d = (P[-1] - P[0]) / ch
        if d[0] < -1e-9 or (abs(d[0]) < 1e-9 and d[1] < 0):
            d = -d
        nrm = np.array([-d[1], d[0]])
        lines.append((d, float(nrm @ P[0]), P, it))
    used = [False] * len(lines)
    for i, (d, off, P, it) in enumerate(lines):
        if used[i]:
            continue
        grp = [i]
        used[i] = True
        changed = True
        while changed:
            changed = False
            lo = min(float(lines[k][2] @ d if False else (lines[k][2] @ d).min()) for k in grp)
            hi = max(float((lines[k][2] @ d).max()) for k in grp)
            for j in range(len(lines)):
                if used[j]:
                    continue
                dj, offj, Pj, _ = lines[j]
                if abs(dj @ d) < math.cos(math.radians(ang_tol)) or abs(offj - off) > off_tol:
                    continue
                t = Pj @ d
                if t.min() > hi + gap or t.max() < lo - gap:
                    continue
                grp.append(j)
                used[j] = True
                changed = True
        T = np.concatenate([lines[k][2] @ d for k in grp])
        base = P[0] - (P[0] @ d) * d
        nrm = np.array([-d[1], d[0]])
        offm = np.mean([lines[k][1] for k in grp])
        base = nrm * offm
        seg = np.array([base + T.min() * d, base + T.max() * d])
        keep.append(dict(pts=seg, kind=kind, tag=it["tag"], merged=len(grp)))
    return keep


def _absorb_fragments(items, max_len=DASH_MAX, tol=0.2):
    """Short straight solid pieces lying on a straight centre line (over-drawn dash patterns,
    degenerate quads) are fragments of that centre line: drop them."""
    lines = []
    for it in items:
        if it["kind"] != "centerline" or len(it["pts"]) != 2:
            continue
        a, b = it["pts"]
        L = math.hypot(*(b - a))
        if L < 5:
            continue
        lines.append((a, (b - a) / L, L))
    if not lines:
        return items
    out = []
    for it in items:
        P = it["pts"]
        if it["kind"] in ("outline", "annotation") and it["tag"] in ("outline", "ext") and plen(P) <= max_len:
            ch, dev = _straightness(P)
            if dev < 0.05:
                hit = False
                for a, d, L in lines:
                    rel = P - a
                    t = rel @ d
                    off = np.abs(rel[:, 0] * d[1] - rel[:, 1] * d[0])
                    if off.max() < tol and t.min() > -6 and t.max() < L + 6:
                        hit = True
                        break
                if hit:
                    continue
        out.append(it)
    return out


# =============================================================================================
# 4. annotation classification (arrows, dimensions, extension lines, hatch, stroked text, marks)
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


def _text_words(polys, idx, max_char=16.0, ts=1.0):
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
        ok = (h >= 3.0 * ts) & (h <= 14.0 * ts)
        uf2 = _UF(len(bl))
        c = 0.5 * (lo + hi)
        tree = cKDTree(c)
        for a, b in tree.query_pairs(20.0 * ts):
            if not (ok[a] and ok[b]):
                continue
            if abs(lo[a, ax] - lo[b, ax]) > 0.45 * ts or abs(hi[a, ax] - hi[b, ax]) > 0.45 * ts:
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
        ok = dd[:, 1] < max(10.0, 0.8 * key[1] * 0.3)
        if ok.sum() >= 8:
            out.update(i for (i, _), o in zip(mem, ok) if o)
    return out


def _extract_page(page, dash_max=None, gap_max=None, text_scale=1.0):
    """All stroked geometry of a page -> list of dict(pts, kind, tag) in PAGE points.
    dash_max / gap_max: longest dash and gap of the sheet's line types (pt); text_scale: lettering
    size relative to sheet 1."""
    widths = []
    raw = _read_pieces(page, widths=widths)
    hair_pts = [densify(P, 0.5) for P, w in zip(raw, widths) if w < 0.05]
    pieces = _dedupe([_rdp(P, 0.01) for P in raw])
    chains = _dash_chains(pieces, dash_max, gap_max)
    in_chain = set(i for order, _ in chains for i in order)
    items = []
    for order, kind in chains:
        items.append(dict(pts=_chain_polyline(pieces, order), kind=kind,
                          tag="centerline" if kind == "centerline" else "hidden"))
    items = _merge_straight(_merge_straight(items, "centerline"), "hidden")
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
    # --- extension lines continuing a centre line (station / reference lines): tagged before
    #     joining so they are not welded to the outline corner they end on
    pre_ext = []
    cl = [it["pts"] for it in items if it["kind"] == "centerline" and plen(it["pts"]) >= 60.0]
    if cl:
        from scipy.spatial import cKDTree
        cends, cdir = [], []
        for P in cl:
            for Q in (P, P[::-1]):
                k = min(len(Q) - 1, max(1, int(np.searchsorted(np.cumsum(np.r_[0, np.hypot(*np.diff(Q, axis=0).T)]), 3.0))))
                d = Q[k] - Q[0]
                n = np.linalg.norm(d)
                cends.append(Q[0])
                cdir.append(d / n if n > 0 else np.zeros(2))
        cends = np.array(cends); cdir = np.array(cdir)
        ct = cKDTree(cends)
        keep = []
        for P in rest:
            ch, dev = _straightness(P)
            hit = False
            if ch > 2.0 and dev < 0.05:
                d = (P[-1] - P[0]) / ch
                for e in (P[0], P[-1]):
                    for q in ct.query_ball_point(e, 0.15):
                        if abs(cdir[q] @ d) > 0.9995:
                            hit = True
            (pre_ext if hit else keep).append(P)
        rest = keep
    joined = [_rdp(P, 0.01) for P in _join(rest)]
    # split short polylines whose straight segment is a dimension line (arrow tip on it, parallel):
    # dimension + extension lines drawn as one stroke
    if arrows:
        tips = np.array([a["tip"] for a in arrows]); axes_ = np.array([a["axis"] for a in arrows])
        j2 = []
        for P in joined:
            if 3 <= len(P) <= 6:
                A, B = P[:-1], P[1:]
                D = B - A
                Ln = np.linalg.norm(D, axis=1)
                hit = False
                for k in range(len(A)):
                    if Ln[k] < 5:
                        continue
                    dist = np.array([_seg_point_dist(A[k:k + 1], B[k:k + 1], t)[0][0] for t in tips])
                    par = np.abs(axes_ @ (D[k] / Ln[k])) > 0.998
                    if np.any((dist < 0.3) & par):
                        hit = True
                if hit:
                    j2.extend([np.array([a, b]) for a, b in zip(A, B)])
                    continue
            j2.append(P)
        joined = j2
    joined = joined + pre_ext
    tags = [None] * (len(joined) - len(pre_ext)) + ["ext"] * len(pre_ext)
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
    # --- extension lines ending on a dimension line's end point (dimension + extension strokes)
    dims = [joined[i] for i in range(len(joined)) if tags[i] == "dim"]
    if dims:
        dend = np.array([[P[0], P[-1]] for P in dims]).reshape(-1, 2)
        for i in S:
            if tags[i] is not None:
                continue
            P = joined[i]
            if min(np.hypot(*(dend - P[0]).T).min(), np.hypot(*(dend - P[-1]).T).min()) < 0.1:
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
    text, words = _text_words(joined, free, max_char=16.0 * text_scale, ts=text_scale)
    for i in text:
        tags[i] = "text"
    # --- reference marks: small circles (+ cross) centred on a centre line
    cls = [it["pts"] for it in items if it["kind"] == "centerline"]
    marks = []
    for i, P in enumerate(joined):
        if tags[i] is not None or not _is_closed(P, 0.1):
            continue
        cx, cy, r, rms = _circle_fit(P)
        if not (1.5 < r < 8.0 and rms < 0.1):
            continue
        c = np.array([cx, cy])
        for Q in cls + [joined[k] for k in range(len(joined)) if tags[k] == "ext"]:
            if len(Q) != 2:
                continue
            a, b = Q
            L = math.hypot(*(b - a))
            if L < 1e-6:
                continue
            d = (b - a) / L
            rel = c - a
            if abs(rel[0] * d[1] - rel[1] * d[0]) < 0.3 and -30 < rel @ d < L + 30:
                marks.append((c, r))
                tags[i] = "refmark"
                break
    for i, P in enumerate(joined):
        if tags[i] is None and straight[i] and len(P) == 2:
            for c, r in marks:
                if np.hypot(*(P - c).T).max() < r + 0.3:
                    tags[i] = "refmark"
    # --- isolated glyphs / glyph groups ('0' labels, labels written at an angle) next to reference
    #     marks or dimension arrows: small touching-stroke blobs not touching any larger geometry
    anchors = [c for c, r in marks] + [ar["tip"] for ar in arrows]
    if anchors:
        from scipy.spatial import cKDTree
        at = cKDTree(np.array(anchors))
        ht = cKDTree(np.vstack(hair_pts)) if hair_pts else None
        free = [i for i in range(len(joined)) if tags[i] is None and np.ptp(joined[i], axis=0).max() <= 12.0]
        if free:
            pts, own = [], []
            for i in free:
                D = densify(joined[i], 0.2)
                pts.append(D); own.append(np.full(len(D), i))
            pts = np.vstack(pts); own = np.concatenate(own)
            uf = _UF(len(free)); pos = {i: k for k, i in enumerate(free)}
            for a, b in cKDTree(pts).query_pairs(0.15):
                if own[a] != own[b]:
                    uf.union(pos[own[a]], pos[own[b]])
            lab = uf.labels()
            blobs = {}
            for k, i in enumerate(free):
                blobs.setdefault(lab[k], []).append(i)
            big = [joined[i] for i in range(len(joined)) if np.ptp(joined[i], axis=0).max() > 12.0]
            bigt = cKDTree(np.vstack([densify(P, 0.5) for P in big])) if big else None
            for mem in blobs.values():
                B = np.vstack([joined[i] for i in mem])
                ext = np.ptp(B, axis=0)
                if ext.max() > 11.5 or ext.max() < 3.0:
                    continue
                if ht is not None and np.median(ht.query(densify(B, 0.5), k=1)[0]) < 0.02:
                    continue
                c = 0.5 * (B.min(0) + B.max(0))
                if at.query(c)[0] > 50.0:
                    continue
                if bigt is not None and bigt.query(B, k=1)[0].min() < 1.0:
                    continue
                for i in mem:
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
    items = _absorb_fragments(items, max_len=dash_max or DASH_MAX)
    # hairline flag (stroke width 0: secondary detail such as wheels, lights)
    if hair_pts:
        from scipy.spatial import cKDTree
        ht = cKDTree(np.vstack(hair_pts))
        for it in items:
            D = densify(it["pts"], 0.5) if len(it["pts"]) > 1 else it["pts"]
            it["hair"] = bool(np.median(ht.query(D, k=1)[0]) < 0.02)
    return items, arrows, words


# =============================================================================================
# 5. view separation
# =============================================================================================

# Page-8 seed points (page pt) on the main outline of each view.  They are snapped to the nearest
# outline polyline; everything connected to it (dilated raster, ~4 pt) forms the view core, and
# the remaining small groups (labels, dimensions) join the nearest core within MAX_ATTACH pt.
SEEDS_P8 = {
    "side": [(350.2, 2726.6), (532.2, 2000.0)],          # crown at FR16, the '0' reference line
    "plan": [(1002.0, 1045.0), (1084.0, 300.0), (1084.0, 1700.0)],
    "front": [(1752.0, 2328.0), (1468.0, 2328.0)],       # spinner, T-tail (front view)
    "detail_stbd": [(248.0, 810.0), (300.0, 500.0)],      # starboard cabin side detail over the wing
}

# sections: seed = a point inside the section outline (label centre for the frame sections)
SECTION_SEEDS_P8 = {
    "EF1": (1031.0, 3051.0), "EF2": (1054.0, 2936.0), "FR10": (1053.0, 2773.0),
    "FR12": (1053.0, 2560.0), "FR14": (1053.0, 2334.0),
    "FR16-30": (1346.0, 3047.0), "FR33": (1346.0, 2824.0), "FR36": (1346.0, 2608.0),
    "FR38": (1305.0, 2406.0), "FR40": (1287.0, 2194.0),
    "VF1": (761.0, 1892.0), "VF2": (761.0, 1623.0), "HF1": (808.0, 748.0), "HF2": (651.0, 732.0),
    "WR1": (2194.0, 2512.0), "WR2": (2188.0, 2758.0), "WR3": (2188.0, 2931.0), "WR4": (2188.0, 3110.0),
}

FR_SECTION_STATIONS_MM = {  # labelled FR10-relative stations of the frames (side view chain dims)
    "EF1": -1880, "EF2": -1005, "FR10": 0, "FR12": 500, "FR14": 1000, "FR16": 1510,
    "FR30": 5150, "FR33": 5920, "FR36": 6670, "FR38": 7720, "FR40": 8770,
}

# side view, FR10-relative mm: ranges where the lowest drawn line is NOT the fuselage keel
# (wing-root fairing + main gear; port ventral strake).  Read off this sheet (see _register).
KEEL_HIDDEN_MM = [(2220, 4390), (7640, 8880)]

MAX_ATTACH = 60.0


def _raster_groups(items, W, H, res=1.0, dil=2):
    from scipy import ndimage
    nx, ny = int(W / res) + 3, int(H / res) + 3
    grid = np.zeros((nx, ny), bool)
    pix = []
    for it in items:
        D = densify(it["pts"], 0.5 * res) if len(it["pts"]) > 1 else it["pts"]
        ij = np.clip(np.round(D / res).astype(int), 0, [nx - 1, ny - 1])
        grid[ij[:, 0], ij[:, 1]] = True
        pix.append(ij)
    grid = ndimage.binary_dilation(grid, iterations=dil)
    lab, n = ndimage.label(grid, structure=np.ones((3, 3)))
    glab = []
    for ij in pix:
        v = lab[ij[:, 0], ij[:, 1]]
        glab.append(int(np.bincount(v).argmax()))
    return np.array(glab)


def _snap_item(items, p, kinds=("outline",)):
    best, bi = 1e9, -1
    for i, it in enumerate(items):
        if it["kind"] not in kinds:
            continue
        P = it["pts"]
        lo, hi = P.min(0) - 40, P.max(0) + 40
        if not (lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1]):
            continue
        D = densify(P, 1.0)
        d = np.hypot(*(D - p).T).min()
        if d < best:
            best, bi = d, i
    return bi, best


def _find_section_loops(items):
    """Section outline = the largest closed outline loop (< 450 pt) containing the section seed."""
    loops = {}
    for name, p in SECTION_SEEDS_P8.items():
        best = None
        for i, it in enumerate(items):
            P = it["pts"]
            if it["kind"] != "outline" or not _is_closed(P, 0.5):
                continue
            b = _bbox(P)
            if max(b[2] - b[0], b[3] - b[1]) > 450:
                continue
            if not (b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]) or not _point_in_poly(p, P):
                continue
            a = abs(_area(P))
            if best is None or a > best[0]:
                best = (a, i)
        if best is not None:
            loops[name] = best[1]
    return loops


def _separate(items, W, H):
    """Assign every item a 'view' (side/plan/front/detail_stbd/sec:<name>/sheet).
    Centre lines additionally get 'also': every other view/section they run through."""
    from scipy.spatial import cKDTree
    core_idx = [i for i, it in enumerate(items) if it["kind"] != "centerline"]
    glab_core = _raster_groups([items[i] for i in core_idx], W, H)
    glab = -np.ones(len(items), int)
    glab[core_idx] = glab_core
    views = [None] * len(items)
    # sheet: page frame + whatever is connected to it (title block, zone marks)
    for i in core_idx:
        b = _bbox(items[i]["pts"])
        if b[2] - b[0] > 0.8 * W or b[3] - b[1] > 0.8 * H:
            for j in np.where(glab == glab[i])[0]:
                views[j] = "sheet"
    names_of_group = {}
    sec_loops = _find_section_loops(items)
    sec_seed_item = {}
    for name, p in SECTION_SEEDS_P8.items():
        i = sec_loops.get(name)
        if i is None:
            i, d = _snap_item(items, p, kinds=("outline",))
            if i < 0 or d > 40:
                continue
        sec_seed_item[name] = i
        names_of_group.setdefault(glab[i], set()).add("sec:" + name)
    for view, pts in SEEDS_P8.items():
        for p in pts:
            i, d = _snap_item(items, p, kinds=("outline",))
            if i >= 0 and d < 30 and views[i] != "sheet":
                names_of_group.setdefault(glab[i], set()).add(view)
    sec_box = {n: _bbox(items[i]["pts"]) for n, i in sec_seed_item.items()}

    def nearest_section(P, names):
        c = 0.5 * (P.min(0) + P.max(0))
        best, bd = None, 1e9
        for n in names:
            b = sec_box[n]
            d = math.hypot(max(b[0] - c[0], 0, c[0] - b[2]), max(b[1] - c[1], 0, c[1] - b[3]))
            if d < bd:
                best, bd = n, d
        return best, bd

    for i in core_idx:
        if views[i] is not None:
            continue
        v = names_of_group.get(glab[i])
        if not v:
            continue
        secs = [n[4:] for n in v if n.startswith("sec:")]
        mains = [n for n in v if not n.startswith("sec:")]
        if len(v) == 1:
            views[i] = next(iter(v))
            continue
        n, d = nearest_section(items[i]["pts"], secs) if secs else (None, 1e9)
        if n is not None and (d < 12 or not mains):
            views[i] = "sec:" + n
        else:
            views[i] = mains[0] if mains else "sheet"
    # centre lines: primary view = the core they run along the most; 'also' = others crossed
    cores = {}
    for i in core_idx:
        if views[i] not in (None, "sheet"):
            cores.setdefault(views[i], []).append(densify(items[i]["pts"], 2.0))
    trees = {v: cKDTree(np.vstack(P)) for v, P in cores.items()}
    also = [[] for _ in items]
    for i, it in enumerate(items):
        if it["kind"] != "centerline":
            continue
        D = densify(it["pts"], 2.0)
        score = {v: int((t.query(D, k=1, distance_upper_bound=6.0)[0] < 6.0).sum()) for v, t in trees.items()}
        hits = sorted([(s, v) for v, s in score.items() if s > 0], reverse=True)
        if hits:
            views[i] = hits[0][1]
            also[i] = [v for s, v in hits[1:]]
        else:
            best, bd = "sheet", MAX_ATTACH
            for v, t in trees.items():
                d = t.query(D, k=1)[0].min()
                if d < bd:
                    best, bd = v, d
            views[i] = best
    # attach the remaining core groups (labels, dimensions) to the nearest assigned geometry
    # (centre lines shared by several views -- e.g. a section row's reference line -- excluded)
    cores = {}
    for i in range(len(items)):
        if views[i] not in (None, "sheet") and not also[i]:
            cores.setdefault(views[i], []).append(densify(items[i]["pts"], 2.0))
    trees = {v: cKDTree(np.vstack(P)) for v, P in cores.items()}
    groups = {}
    for i in core_idx:
        if views[i] is None:
            groups.setdefault(glab[i], []).append(i)
    for g, mem in groups.items():
        P = np.vstack([densify(items[i]["pts"], 2.0) for i in mem])
        if len(P) > 400:
            P = P[:: len(P) // 400 + 1]
        best, bd = "sheet", MAX_ATTACH
        for v, t in trees.items():
            d = t.query(P, k=1)[0].min()
            if d < bd:
                best, bd = v, d
        for i in mem:
            views[i] = best
    return views, also, sec_seed_item


# =============================================================================================
# 6. measurements in page coordinates
# =============================================================================================

STATION_ORDER = ["EF1", "EF2", "FR10", "FR12", "FR14", "FR16", "FR30", "FR33", "FR36", "FR38", "FR40"]

# values printed on the sheet (read off the drawing by eye; the stroked text is not OCR'd)
LABELS = dict(
    side_stations=FR_SECTION_STATIONS_MM,
    side_chain=[875, 500, 510, 3640, 770, 750, 1050, 1050],
    side_ref_to_keel=290, side_ref_to_fin_root=683, side_vf1=1380, side_vf2=2690, side_vf1_vf2=1310,
    plan_fr10_to_wing=2820, plan_hf2=2270,
    front_wr1=935, front_track=4530, front_wr2=4675, front_wr3=5780, front_wr4=6520, front_prop_dia=2670,
    span_label=16114, length_label=14400, height_label=4260, area_label_m2=25.81,
)


def _in_view(it, view):
    return it["view"] == view or view in it.get("also", ())


def _dim_ticks(items, arrows, view):
    """For every dimension line of a view: the arrow-tip positions along it."""
    out = []
    for it in items:
        if not (_in_view(it, view) and it["tag"] == "dim"):
            continue
        a, b = it["pts"][0], it["pts"][-1]
        L = math.hypot(*(b - a))
        d = (b - a) / L
        ts = []
        for ar in arrows:
            rel = ar["tip"] - a
            if abs(rel[0] * d[1] - rel[1] * d[0]) < 0.3 and -0.5 < rel @ d < L + 0.5 and abs(ar["axis"] @ d) > 0.99:
                ts.append(float(rel @ d))
        ts = _cluster_1d(ts, 0.3)
        out.append(dict(a=a, b=b, d=d, ticks=ts))
    return out


def _outline_pts(items, view, step=0.5, tags=("outline",), hair=False):
    Ps = [densify(it["pts"], step) for it in items if it["view"] == view and it["kind"] == "outline"
          and it["tag"] in tags and (hair or not it.get("hair"))]
    return np.vstack(Ps) if Ps else np.zeros((0, 2))


def _measure_side(items, arrows):
    m = {}
    V = "side"
    # ---- station lines: straight lines of constant page y reaching the dimension rows
    ys = []
    for it in items:
        if not _in_view(it, V) or not (it["kind"] == "centerline" or it["tag"] == "ext"):
            continue
        P = it["pts"]
        ch, dev = _straightness(P)
        if ch < 40 or dev > 0.1 or np.ptp(P[:, 1]) > 0.05 or P[:, 0].min() > 160:
            continue
        ys.append(float(P[:, 1].mean()))
    ys = sorted(_cluster_1d(ys, 0.5), reverse=True)          # nose first
    if len(ys) != len(STATION_ORDER):
        raise RuntimeError(f"side view: expected {len(STATION_ORDER)} station lines, found {len(ys)}: {ys}")
    st = dict(zip(STATION_ORDER, ys))
    m["station_py"] = st
    v = np.array([FR_SECTION_STATIONS_MM[n] for n in STATION_ORDER], float)
    y = np.array(ys)
    A = np.c_[np.ones_like(v), v]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pt_per_mm = -coef[1]
    s = 1.0 / (pt_per_mm * 1000.0)                               # m per pt
    resid_mm = (y - A @ coef) / pt_per_mm
    m["scale_m_per_pt"] = s
    m["fr10_py_fit"] = float(coef[0])
    m["station_resid_mm"] = dict(zip(STATION_ORDER, [float(r) for r in -resid_mm]))
    # chain dimension ticks (arrow tips) along both dimension rows
    rows = _dim_ticks(items, arrows, V)
    chain = []
    for r in rows:
        if abs(r["d"][0]) < 1e-3 and len(r["ticks"]) >= 2:        # rows run along page y
            t = np.array(r["ticks"])
            chain.append(dict(px=float(r["a"][0]), ticks_py=list(r["a"][1] + t * r["d"][1])))
    m["dim_rows"] = chain
    # ---- ground line, reference line
    g = [it for it in items if _in_view(it, V) and it["tag"] == "ground"]
    if not g:
        raise RuntimeError("side view: ground line not found")
    gl = max(g, key=lambda it: plen(it["pts"]))
    m["ground_px"] = float(gl["pts"][:, 0].mean())
    m["ground_line"] = gl["pts"]
    refs = []
    for it in items:
        if _in_view(it, V) and it["kind"] == "centerline":
            P = it["pts"]
            if np.ptp(P[:, 0]) < 0.05 and np.ptp(P[:, 1]) > 800:
                refs.append(float(P[:, 0].mean()))
    m["ref_px"] = _cluster_1d(refs, 0.5)[0] if refs else None
    # ---- outline extremes (hairline details such as the tail-light lens excluded)
    O = _outline_pts(items, V)
    m["spinner_tip"] = O[np.argmax(O[:, 1])]
    m["aft_most"] = O[np.argmin(O[:, 1])]
    m["top_most"] = O[np.argmin(O[:, 0])]
    m["bottom_most"] = O[np.argmax(O[:, 0])]
    Oh = _outline_pts(items, V, hair=True)
    m["aft_most_incl_hair"] = Oh[np.argmin(Oh[:, 1])]
    # ---- tyres: circles touching the ground line
    circ = []
    for it in items:
        if not (it["view"] == V and it["kind"] == "outline"):
            continue
        f = _arc_fit(it["pts"])
        if f and 12 < f[2] < 50 and f[3] < 0.1:
            circ.append(f)
    tyres = [c for c in circ if abs(c[0] + c[2] - m["ground_px"]) < 2.0]
    tyres.sort(key=lambda c: -c[1])        # nose first
    m["tyres"] = tyres
    # ---- propeller disc (edge-on straight line ahead of EF1)
    pl = []
    for it in items:
        if it["view"] != V or it["kind"] != "outline":
            continue
        P = it["pts"]
        ch, dev = _straightness(P)
        if ch > 200 and dev < 0.5 and P[:, 1].mean() > st["EF1"] and np.ptp(P[:, 0]) > 150:
            pl.append(P)
    m["prop_line"] = max(pl, key=plen) if pl else None
    return m


def _long_centerline(items, view, axis, min_len):
    """Page coordinate of the longest straight centre line of `view` that is constant along
    `axis` (0: constant page x, 1: constant page y)."""
    best = None
    for it in items:
        if not (_in_view(it, view) and it["kind"] == "centerline"):
            continue
        P = it["pts"]
        if np.ptp(P[:, axis]) > 0.05:
            continue
        L = np.ptp(P[:, 1 - axis])
        if L >= min_len and (best is None or L > best[1]):
            best = (float(P[:, axis].mean()), L, P)
    return best


def _refmarks(items, view):
    out = []
    for it in items:
        if _in_view(it, view) and it["tag"] == "refmark" and _is_closed(it["pts"], 0.1):
            cx, cy, r, rms = _circle_fit(it["pts"])
            out.append((cx, cy, r))
    return out


def _measure_plan(items, arrows):
    V = "plan"
    m = {}
    cl = _long_centerline(items, V, 0, 1000)
    m["cl_px"] = cl[0]
    O = _outline_pts(items, V)
    m["spinner_tip"] = O[np.argmax(O[:, 1])]
    m["aft_most"] = O[np.argmin(O[:, 1])]
    m["stbd_tip"] = O[np.argmin(O[:, 0])]
    m["port_tip"] = O[np.argmax(O[:, 0])]
    T = O[O[:, 1] < m["aft_most"][1] + 420]
    m["tail_stbd_tip"] = T[np.argmin(T[:, 0])]
    m["tail_port_tip"] = T[np.argmax(T[:, 0])]
    marks = [r for r in _refmarks(items, V) if abs(r[0] - m["cl_px"]) < 1.0]
    marks.sort(key=lambda r: -r[1])
    m["refmarks"] = marks                        # [0] = FR10 mark near the windshield, [-1] = tail
    m["dims"] = [dict(a=d["a"], b=d["b"], d=d["d"], ticks=d["ticks"]) for d in _dim_ticks(items, arrows, V)]
    return m


def _measure_front(items, arrows):
    V = "front"
    m = {}
    cl = _long_centerline(items, V, 1, 400)
    m["cl_py"] = cl[0]
    O = _outline_pts(items, V)
    m["top_most"] = O[np.argmin(O[:, 0])]
    m["stbd_tip"] = O[np.argmax(O[:, 1])]         # starboard = large page y (viewer's left)
    m["port_tip"] = O[np.argmin(O[:, 1])]
    T = O[O[:, 0] < m["top_most"][0] + 40]
    m["tail_stbd_tip"] = T[np.argmax(T[:, 1])]
    m["tail_port_tip"] = T[np.argmin(T[:, 1])]
    # propeller circle (phantom line)
    best = None
    for it in items:
        if _in_view(it, V) and it["kind"] == "centerline" and len(it["pts"]) > 10:
            f = _arc_fit(it["pts"], min_cover=300)
            if f and 100 < f[2] < 250 and (best is None or f[2] > best[2]):
                best = f
    m["prop_circle"] = best
    # tyre bottoms: lowest outline point near the nose gear and near each main gear
    Oa = _outline_pts(items, V, hair=True)
    low = Oa[:, 0].max()
    tyres = []
    near = Oa[Oa[:, 0] > low - 60]
    # cluster the low points by page y
    order = np.argsort(near[:, 1])
    ys = near[order, 1]
    splits = np.where(np.diff(ys) > 20)[0]
    for grp in np.split(order, splits + 1):
        P = near[grp]
        k = np.argmax(P[:, 0])
        if P[k, 0] > low - 5:
            tyres.append(P[k])
    m["tyre_bottoms"] = tyres
    m["dims"] = [dict(a=d["a"], b=d["b"], d=d["d"], ticks=d["ticks"]) for d in _dim_ticks(items, arrows, V)]
    return m


def _measure_extra(items, arrows, ms, mp, mf):
    """Additional page-level measurements used by the checks."""
    ex = {}
    s = ms["scale_m_per_pt"]
    st = ms["station_py"]
    # firewall / cowling joint: straight outline of constant page y between EF2 and FR10
    best = None
    for it in items:
        if it["view"] != "side" or it["kind"] != "outline":
            continue
        P = it["pts"]
        ch, dev = _straightness(P)
        if dev < 0.05 and np.ptp(P[:, 1]) < 0.05 and np.ptp(P[:, 0]) > 80 and st["FR10"] < P[0, 1] < st["EF2"]:
            if best is None or np.ptp(P[:, 0]) > np.ptp(best[:, 0]):
                best = P
    ex["firewall_py"] = float(best[:, 1].mean()) if best is not None else None
    # side view vertical dimensions (along page x): tick heights above the '0' reference line
    vd = []
    for d in _dim_ticks(items, arrows, "side"):
        if abs(d["d"][1]) < 1e-3 and len(d["ticks"]) >= 1:
            px = d["a"][0] + np.array(d["ticks"]) * d["d"][0]
            vd.append(dict(py=float(d["a"][1]), px=sorted(px.tolist())))
    ex["side_vdims"] = vd
    # WR running dimensions in the front view (dimension line parallel to the wing)
    cl = mf["cl_py"]
    tips = [a["tip"] for a in arrows if abs(a["axis"][1]) > 0.98 and a["tip"][1] > cl + 400
            and 1600 < a["tip"][0] < 1800]
    tips = sorted(tips, key=lambda t: t[1])
    ex["wr_tips"] = tips
    if len(tips) >= 2:
        T = np.array(tips)
        c = np.polyfit(T[:, 1], T[:, 0], 1)            # page x = c0 * py + c1
        ex["wr_line_deg"] = float(math.degrees(math.atan(-c[0])))
        wr1 = None                                     # WR1 station: outboard tick of the 935 dimension
        for dd in mf["dims"]:
            if abs(dd["d"][0]) < 1e-3 and len(dd["ticks"]) == 2:
                yy = sorted(dd["a"][1] + np.array(dd["ticks"]) * dd["d"][1])
                if abs(yy[0] - cl) < 1.0 and yy[1] - cl < 200:
                    wr1 = yy[1]
        ex["wr1_py"] = wr1
        if wr1 is not None:
            o = np.array([np.polyval(c, wr1), wr1])
            ex["wr_origin"] = o
            ex["wr_along_mm"] = [float(np.hypot(*(t - o)) * s * 1000) for t in T]
    return ex


# =============================================================================================
# 7. page-level processing (cached)
# =============================================================================================


def _process(verbose=True):
    import pymupdf
    t0 = time.time()
    pdf = fetch()
    sha = _sha256(pdf)
    doc = pymupdf.open(str(pdf))
    page = doc[8]
    W, H = page.rect.width, page.rect.height
    items, arrows, words = _extract_page(page)
    views, also, sec_seed = _separate(items, W, H)
    for it, v, a in zip(items, views, also):
        it["view"] = v
        it["also"] = a
    ms = _measure_side(items, arrows)
    mp = _measure_plan(items, arrows)
    mf = _measure_front(items, arrows)
    ex = _measure_extra(items, arrows, ms, mp, mf)
    secs = _section_page_data(items, sec_seed)
    faces = {v: _faces(items, v, GLAZING_BOX_P8[v]) for v in ("side", "plan", "front")}
    if verbose:
        print(f"[mbp] page 8: {len(items)} polylines, {len(arrows)} arrows, {len(words)} words "
              f"({time.time() - t0:.1f} s)")
    try:
        p9 = _process_page9(doc[9], ms["scale_m_per_pt"])
    except Exception as e:                     # sheet 2 is optional
        p9 = dict(error=repr(e))
    return dict(version=CODE_VERSION, sha256=sha, page_size=(W, H), items=items, arrows=arrows, words=words,
                meas=dict(side=ms, plan=mp, front=mf, extra=ex), secs=secs, faces=faces, page9=p9,
                source=dict(url=SRC_URL, file=PDF_NAME, drawing="190.10.40.432", page_index=8))


# =============================================================================================
# 8. registration: page -> model coordinates
# =============================================================================================


class Xf:
    """Affine page -> model map for one view: (u, v) = A @ (px, py) + b."""

    def __init__(self, A, b, axes):
        self.A = np.asarray(A, float)
        self.b = np.asarray(b, float)
        self.axes = axes

    def __call__(self, P):
        P = np.asarray(P, float)
        return P @ self.A.T + self.b

    def inv(self, Q):
        Q = np.asarray(Q, float)
        return np.linalg.solve(self.A, (Q - self.b).T).T

    def as_dict(self):
        return dict(A=self.A.tolist(), b=self.b.tolist(), axes=self.axes)


def _xf_side(s, py_fr10, x_fr10, px_ground):
    # x = x_fr10 + (py_fr10 - py) s ;  z = (px_ground - px) s
    return Xf([[0.0, -s], [-s, 0.0]], [x_fr10 + py_fr10 * s, px_ground * s], ("x", "z"))


def _xf_plan(s, py_ref, x_ref, px_cl):
    # x = x_ref + (py_ref - py) s ;  y = (px_cl - px) s   (starboard = page left)
    return Xf([[0.0, -s], [-s, 0.0]], [x_ref + py_ref * s, px_cl * s], ("x", "y"))


def _xf_front(s, py_cl, px_ground):
    # y = (py - py_cl) s  (starboard = large page y = viewer's left) ;  z = (px_ground - px) s
    return Xf([[0.0, s], [-s, 0.0]], [-py_cl * s, px_ground * s], ("y", "z"))


def _model_oml():
    """Model crown / keel control curves (x, z) from model.fuselage, if importable."""
    try:
        sys.path.insert(0, str(ROOT))
        from model import fuselage as F
    except Exception:
        return None
    x = np.arange(0.95, 14.36, 0.01)
    return dict(x=x, top=np.asarray(F.z_top(x), float), bot=np.asarray(F.z_bot(x), float),
                hw=np.asarray(F.half_w(x), float), STA=dict(F.STA), prop_axis_z=float(F.PROP_AXIS_Z))


def _oml_fit(side_pts_xz, oml, fix_dz=False, xmax_crown=9.0, xmax_keel=14.3, xmin=1.0, cap=0.025):
    """Least-squares shift (dx, dz) of the model crown+keel (model.fuselage z_top / z_bot) onto the
    drawing's side outline, scale fixed.  Objective: mean truncated squared distance (cap 25 mm)
    from the shifted model curves to the nearest drawn outline point -- robust to the drawing's
    other lines and to parts of the model curves that are not drawn (crown under the fin).
    Global grid search (1 cm), then a 1 mm grid around the optimum.
    Returns dict(dx, dz, rms_mm (inliers), n_inliers, profile (dx, J) with dz optimised)."""
    from scipy.spatial import cKDTree
    x = oml["x"]
    mc = (x >= xmin) & (x <= xmax_crown)
    mk = (x >= xmin) & (x <= xmax_keel)
    M = np.vstack([np.c_[x[mc], oml["top"][mc]], np.c_[x[mk], oml["bot"][mk]]])
    lab = np.r_[np.zeros(mc.sum()), np.ones(mk.sum())]
    tree = cKDTree(side_pts_xz)

    def J(dx, dz):
        d, _ = tree.query(M + [dx, dz], k=1, distance_upper_bound=cap)
        d = np.minimum(d, cap)
        return float(np.mean(d * d))

    gx = np.arange(-0.40, 0.4001, 0.01)
    gz = [0.0] if fix_dz else np.arange(-0.10, 0.3001, 0.01)
    grid = np.array([[J(a, b) for b in gz] for a in gx])
    k = np.unravel_index(np.argmin(grid), grid.shape)
    dx, dz = gx[k[0]], gz[k[1]]
    fx = np.arange(dx - 0.012, dx + 0.0121, 0.001)
    fz = [0.0] if fix_dz else np.arange(dz - 0.012, dz + 0.0121, 0.001)
    fine = np.array([[J(a, b) for b in fz] for a in fx])
    k2 = np.unravel_index(np.argmin(fine), fine.shape)
    dx, dz = float(fx[k2[0]]), float(fz[k2[1]])
    d, _ = tree.query(M + [dx, dz], k=1)
    inl = d < 0.012
    prof = grid.min(1)
    # competing minima: best objective more than 5 cm away from the optimum
    far = np.abs(gx - dx) > 0.05
    out = dict(dx=dx, dz=dz, J=float(fine.min()), rms_mm=float(np.sqrt(np.mean(d[inl] ** 2)) * 1000) if inl.any() else None,
               n_inliers=int(inl.sum()), n_model=len(M), profile_dx=gx.tolist(), profile_J=prof.tolist(),
               second_best_dx=float(gx[far][np.argmin(prof[far])]) if far.any() else None,
               second_best_ratio=float(prof[far].min() / max(prof.min(), 1e-12)) if far.any() else None,
               crown_inliers=int((inl & (lab == 0)).sum()), keel_inliers=int((inl & (lab == 1)).sum()),
               xmin=xmin, xmax_crown=xmax_crown, xmax_keel=xmax_keel)
    return out

ANCHORS = ("spinner", "oml", "oml_xz", "aft")

MODEL_REF = dict(spinner_tip=0.39, aft_most=14.79, prop_axis_z=1.655, length=14.40, height=4.26, span=16.28,
                 tail_span=5.20, track=4.53, wheelbase=3.48, prop_dia=2.67, prop_clearance=0.32,
                 firewall=3.00, wing_root_le=5.20, lemac=5.323, mac=1.703, dihedral_deg=4.5,
                 nose_gear_pivot=3.08, main_gear_pivot=6.02)


def _map_items(items, view, xf, also=True):
    out = []
    for it in items:
        if it["view"] == view or (also and view in it.get("also", ())):
            out.append(dict(pts=xf(it["pts"]), kind=it["kind"], tag=it["tag"], hair=bool(it.get("hair"))))
    return out


def _register(P, anchor="spinner", front_z="ground"):
    if anchor not in ANCHORS:
        raise ValueError(f"anchor must be one of {ANCHORS}")
    items = P["items"]
    ms, mp, mf, ex = (P["meas"][k] for k in ("side", "plan", "front", "extra"))
    s = ms["scale_m_per_pt"]
    py10 = ms["station_py"]["FR10"]
    gx = ms["ground_px"]
    meta = dict(scale_m_per_pt=s, scale_ratio=s * 1000.0 / PT, nominal_scale=NOMINAL_SCALE,
                scale_vs_nominal=s * 1000.0 / (PT * NOMINAL_SCALE), anchor=anchor, front_z=front_z,
                sha256=P["sha256"], version=P["version"], source=P["source"])
    # ---------------- side view x anchors
    x10 = {"spinner": MODEL_REF["spinner_tip"] + (ms["spinner_tip"][1] - py10) * s,
           "aft": MODEL_REF["aft_most"] - (py10 - ms["aft_most"][1]) * s}
    xf0 = _xf_side(s, py10, x10["spinner"], gx)
    oml = _model_oml()
    fits = {}
    if oml is not None:
        O = xf0(_outline_pts(items, "side", step=1.0))
        O = O[(O[:, 0] > 0.9) & (O[:, 0] < 14.4) & (O[:, 1] > 0.5) & (O[:, 1] < 3.0)]
        fits["x"] = _oml_fit(O, oml, fix_dz=True)                       # (b): z stays on the ground line
        fits["xz"] = _oml_fit(O, oml)                                   # diagnostic: dx and dz free
        fits["nose_x"] = _oml_fit(O, oml, fix_dz=True, xmax_crown=3.1, xmax_keel=3.1)
        x10["oml"] = x10["spinner"] - fits["x"]["dx"]
        x10["oml_xz"] = x10["spinner"] - fits["xz"]["dx"]
    if anchor not in x10:
        raise RuntimeError("model.fuselage not importable: OML anchors unavailable")
    meta["fr10_station"] = {k: float(v) for k, v in x10.items()}
    meta["oml_fit"] = fits
    xs = _xf_side(s, py10, x10[anchor], gx)
    # ---------------- plan: own spinner tip = STA 0.39, shifted like the side view for other anchors
    # (the plan's aft-most point includes the tail-light lens, so it is not used as an anchor)
    xp = _xf_plan(s, mp["spinner_tip"][1], MODEL_REF["spinner_tip"] + (x10[anchor] - x10["spinner"]), mp["cl_px"])
    # ---------------- front: ground at the tyre bottoms, or propeller-circle centre at WL 1.655
    g_tyres = float(np.mean([t[0] for t in mf["tyre_bottoms"]]))
    g_prop = mf["prop_circle"][0] + MODEL_REF["prop_axis_z"] / s
    xfr = _xf_front(s, mf["cl_py"], g_tyres if front_z == "ground" else g_prop)
    meta["front_ground_px"] = dict(tyres=g_tyres, prop=g_prop, disagreement_mm=(g_prop - g_tyres) * s * 1000)
    meta["transforms"] = dict(side=xs.as_dict(), plan=xp.as_dict(), front=xfr.as_dict())
    X = dict(side=xs, plan=xp, front=xfr)
    out = dict(side=_map_items(items, "side", xs), plan=_map_items(items, "plan", xp),
               front=_map_items(items, "front", xfr))
    # ---------------- starboard cabin detail (sheet 1, top left): seen from starboard, nose toward
    # small page y; registered on its FR16 line and its horizontal centre line (= '0' reference)
    det = [it for it in items if it["view"] == "detail_stbd"]
    dcl = [it["pts"] for it in det if it["kind"] == "centerline"]
    fr16 = [P_[0, 1] for P_ in dcl if np.ptp(P_[:, 1]) < 0.05]
    ref = [P_[0, 0] for P_ in dcl if np.ptp(P_[:, 0]) < 0.05]
    z_ref = (gx - ms["ref_px"]) * s
    if fr16 and ref:
        x16 = x10[anchor] + FR_SECTION_STATIONS_MM["FR16"] / 1000.0
        xd = Xf([[0.0, s], [-s, 0.0]], [x16 - fr16[0] * s, z_ref + ref[0] * s], ("x", "z"))
        out["detail_stbd"] = _map_items(items, "detail_stbd", xd)
        meta["transforms"]["detail_stbd"] = xd.as_dict()
        X["detail_stbd"] = xd
    meta["z_ref_line"] = z_ref
    # ---------------- glazing
    glz = {}
    for v in ("side", "plan", "front"):
        glz[v] = _name_glazing(v, [dict(f) for f in P["faces"][v]], X[v])
    out["glazing"] = glz
    out["openings"] = dict(side=_openings_side(items, xs, ms["station_py"], s))
    # ---------------- fuselage profile lines (drawing lines tracked from the nose, seeded on the model)
    prof = {}
    if oml is not None:
        zb = lambda u: np.interp(u, oml["x"], oml["bot"])
        hw = lambda u: np.interp(u, oml["x"], oml["hw"])
        prof["side_crown"] = _profile(items, "side", xs, 1.0, 9.0, pick=lambda u, vs: vs.max())   # nothing above the crown here
        # lowest drawn line along the fuselage (silhouette bottom); the keel proper is hidden behind the
        # wing-root fairing / main gear and behind the port ventral strake in two ranges (verification
        # fix): there the track follows the fairing belly (dips to WL 0.88) and the strake's lower edge
        # (~50-100 mm below the tail-cone keel; the FR38/FR40 sections show the strakes) -> NaN in
        # 'side_keel', full track kept as 'side_bottom'.  Cabin keel behind the fairing = FR16-30 section
        # bottom (WL 0.939, the '0' line - 290).
        prof["side_bottom"] = _track(items, "side", xs, 1.0, 13.6, zb)
        kl = prof["side_bottom"].copy()
        for a, b in KEEL_HIDDEN_MM:
            kl[(kl[:, 0] > x10[anchor] + a / 1000.0) & (kl[:, 0] < x10[anchor] + b / 1000.0), 1] = np.nan
        prof["side_keel"] = kl
        prof["plan_hb_stbd"] = _track(items, "plan", xp, 1.0, 13.0, hw)
        prof["plan_hb_port"] = _track(items, "plan", xp, 1.0, 13.0, lambda u: -hw(u))
    out["profiles"] = prof
    # ---------------- sections (sheet 1) + sheet 2 (port cabin-side detail, fairing sections)
    out["sections"] = _register_sections(P, X, x10[anchor], z_ref, s)
    d9, sec9, m9 = _register_page9(P.get("page9"), s, out["openings"]["side"], x10[anchor], z_ref)
    if d9:
        out["detail_port_sheet2"] = d9
    out["sections"].update(sec9)
    meta["sheet2"] = m9
    out["_sheet2_meta"] = m9
    meta["checks"] = _checks(dict(P, anchor=anchor), X, x10, s, z_ref, fits, out)
    out.pop("_sheet2_meta", None)
    meta["page"] = dict(station_py=ms["station_py"], ground_px=gx, ref_px=ms["ref_px"], plan_cl_px=mp["cl_px"],
                        front_cl_py=mf["cl_py"])
    out["meta"] = meta
    return out


# =============================================================================================
# 9. named features: enclosed regions -> glazing, windows, doors; profile lines
# =============================================================================================

# page boxes (pt) that contain the cockpit glazing of each view (registration-independent)
GLAZING_BOX_P8 = {"side": (330, 2680, 500, 2960), "plan": (990, 1420, 1220, 1620), "front": (1630, 2170, 1725, 2480)}


def _faces(items, view, box, res=8.0, min_area=8.0, include_hidden=False):
    """Enclosed regions of the outline drawing inside page box (x0, y0, x1, y1).
    Returns list of dict(poly (N,2) page pts snapped onto the strokes, area pt^2, centroid)."""
    from scipy import ndimage
    from scipy.spatial import cKDTree
    import contourpy
    x0, y0, x1, y1 = box
    nx, ny = int((x1 - x0) * res) + 3, int((y1 - y0) * res) + 3
    img = np.zeros((nx, ny), bool)
    strokes = []
    for it in items:
        if it["view"] != view or it.get("hair"):
            continue
        if not (it["kind"] == "outline" or (include_hidden and it["kind"] == "hidden")):
            continue
        P = it["pts"]
        if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].max() < y0 or P[:, 1].min() > y1:
            continue
        D = densify(P, 0.4 / res)
        strokes.append(D)
        ij = np.round((D - [x0, y0]) * res).astype(int) + 1
        ok = (ij[:, 0] >= 0) & (ij[:, 0] < nx) & (ij[:, 1] >= 0) & (ij[:, 1] < ny)
        img[ij[ok, 0], ij[ok, 1]] = True
    if not strokes:
        return []
    img = ndimage.binary_dilation(img, iterations=1)
    lab, n = ndimage.label(~img)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    st = cKDTree(np.vstack(strokes))
    out = []
    areas = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    for k in range(1, n + 1):
        if k in border:
            continue
        a = areas[k - 1] / res ** 2
        if a < min_area:
            continue
        mask = ndimage.binary_fill_holes(lab == k)
        gen = contourpy.contour_generator(z=np.pad(mask, 1).astype(float))
        lines = gen.lines(0.5)
        if not lines:
            continue
        L = max(lines, key=len)[:, ::-1]        # contourpy gives (col, row) = (j, i)
        P = (L - 1 - 1) / res + [x0, y0]        # undo pad and the +1 raster offset
        d, j = st.query(P, k=1)
        P = np.where((d < 0.6)[:, None], st.data[j], P)
        P = _rdp(P, 0.02)
        if not _is_closed(P, 1e-6):
            P = np.vstack([P, P[:1]])
        out.append(dict(poly=P, area=float(a), centroid=P[:-1].mean(0)))
    return out


def _name_glazing(view, faces, xf):
    """Name the enclosed glazing regions of a cockpit box."""
    out = {}
    if not faces:
        return out
    F = sorted(faces, key=lambda f: -f["area"])
    for f in F:
        f["m"] = xf(f["poly"])
        f["mc"] = f["m"][:-1].mean(0)
    if view == "side":                       # (x, z): three port-side loops
        F = [f for f in F if f["area"] > 100]
        if len(F) >= 1:
            out["sw_port"] = F[0]["m"]
        rest = F[1:3]
        if rest:
            ws = min(rest, key=lambda f: f["m"][:, 0].min())      # reaches furthest forward
            out["ws_port"] = ws["m"]
            for f in rest:
                if f is not ws:
                    out["dv_port"] = f["m"]
    elif view == "plan":                     # (x, y)
        F = [f for f in F if f["area"] > 100]
        ws = [f for f in F if abs(f["mc"][1]) < 0.45][:2]
        side = [f for f in F if all(f is not w for w in ws)]
        for f in ws:
            out["ws_stbd" if f["mc"][1] > 0 else "ws_port"] = f["m"]
        stbd = [f for f in side if f["mc"][1] > 0]
        port = sorted([f for f in side if f["mc"][1] < 0], key=lambda f: -f["area"])
        if stbd:
            out["sw_stbd"] = stbd[0]["m"]
        if port:
            out["sw_port"] = port[0]["m"]
        if len(port) > 1:
            out["dv_port"] = port[1]["m"]
    elif view == "front":                    # (y, z)
        F = [f for f in F if f["area"] > 100]
        ws = sorted(F, key=lambda f: -f["area"])[:2]
        for f in ws:
            out["ws_stbd" if f["mc"][0] > 0 else "ws_port"] = f["m"]
        side = [f for f in F if all(f is not w for w in ws)]
        stbd = sorted([f for f in side if f["mc"][0] > 0], key=lambda f: -f["area"])
        port = sorted([f for f in side if f["mc"][0] < 0], key=lambda f: -f["area"])
        if stbd:
            out["sw_stbd"] = stbd[0]["m"]
        if port:
            out["sw_port"] = port[0]["m"]
        if len(port) > 1:
            out["dv_port"] = port[1]["m"]
    return out


def _openings_side(items, xf_side, st_py, s):
    """Cabin windows (enclosed rounded rectangles) and doors (door-sized outline polylines, possibly
    open where the wing fairing hides them) in the side view (port side), FR16..FR33+."""
    y0 = st_py["FR33"] - 60
    y1 = st_py["FR16"] + 10
    pxa = xf_side.inv(np.array([[5.0, 2.75]]))[0][0]
    pxb = xf_side.inv(np.array([[5.0, 0.95]]))[0][0]
    out = {}
    doors = []
    for it in items:
        if it["view"] != "side" or it["kind"] != "outline" or it.get("hair"):
            continue
        m = xf_side(it["pts"])
        w, h = np.ptp(m[:, 0]), np.ptp(m[:, 1])
        if 0.5 < w < 1.6 and 1.1 < h < 1.6 and m[:, 1].max() < 2.75 and 4.0 < m[:, 0].mean() < 10.0:
            doors.append(m)
    doors.sort(key=lambda m: m[:, 0].min())
    for m in doors:
        out["door_cargo" if np.ptp(m[:, 0]) > 1.0 else "door_airstair"] = m
    faces = _faces(items, "side", (pxa, y0, pxb, y1), res=4.0, min_area=200)
    wins = []
    for f in faces:
        m = xf_side(f["poly"])
        w = np.ptp(m[:, 0]); h = np.ptp(m[:, 1])
        if 0.2 < w < 0.5 and 0.25 < h < 0.6:
            wins.append(m)
    wins.sort(key=lambda m: m[:, 0].min())
    k = 0
    for m in wins:
        c = m[:-1].mean(0)
        host = [n for n, d in out.items() if n.startswith("door") and d[:, 0].min() < c[0] < d[:, 0].max()
                and d[:, 1].min() < c[1] < d[:, 1].max()]
        if host:
            out[host[0] + "_win"] = m
        else:
            k += 1
            out[f"cabin_win_{k}"] = m
    return out


def _profile(items, view, xf, lo, hi, step=0.01, pick=None):
    """Silhouette-type profile: for every station u in [lo, hi] the crossings of the view's
    outline with the line u = const (model coords); `pick(u, vs)` selects one crossing."""
    segs = []
    for it in items:
        if it["view"] != view or it["kind"] != "outline" or it.get("hair"):
            continue
        Q = xf(it["pts"])
        segs.append(np.stack([Q[:-1], Q[1:]], 1))
    S = np.concatenate(segs)
    a, b = S[:, 0], S[:, 1]
    u0 = np.minimum(a[:, 0], b[:, 0]); u1 = np.maximum(a[:, 0], b[:, 0])
    out = []
    us = np.arange(lo, hi + 1e-9, step)
    for u in us:
        k = np.where((u0 <= u) & (u1 >= u) & (u1 > u0))[0]
        if not len(k):
            out.append(np.nan)
            continue
        t = (u - a[k, 0]) / (b[k, 0] - a[k, 0])
        vs = a[k, 1] + t * (b[k, 1] - a[k, 1])
        v = pick(u, vs) if pick else vs.max()
        out.append(np.nan if v is None else v)
    return np.c_[us, np.array(out, float)]


def _track(items, view, xf, lo, hi, seed, step=0.01, jump=0.02, seed_tol=0.20):
    """Follow one drawn line along u in [lo, hi]: at every station the crossing nearest the previous
    value (|jump| per step); (re)acquired at the crossing nearest seed(u) within seed_tol."""
    segs = []
    for it in items:
        if it["view"] != view or it["kind"] != "outline" or it.get("hair") or np.ptp(it["pts"], axis=0).max() < 15:
            continue
        Q = xf(it["pts"])
        segs.append(np.stack([Q[:-1], Q[1:]], 1))
    S = np.concatenate(segs)
    a, b = S[:, 0], S[:, 1]
    u0 = np.minimum(a[:, 0], b[:, 0]); u1 = np.maximum(a[:, 0], b[:, 0])
    us = np.arange(lo, hi + 1e-9, step)
    out = np.full(len(us), np.nan)
    prev = None
    for n, u in enumerate(us):
        k = np.where((u0 <= u) & (u1 >= u) & (u1 > u0))[0]
        if not len(k):
            prev = None
            continue
        t = (u - a[k, 0]) / (b[k, 0] - a[k, 0])
        vs = a[k, 1] + t * (b[k, 1] - a[k, 1])
        v = None
        if prev is not None:
            j = np.argmin(np.abs(vs - prev))
            if abs(vs[j] - prev) <= jump:
                v = vs[j]
        if v is None:
            j = np.argmin(np.abs(vs - seed(u)))
            if abs(vs[j] - seed(u)) <= seed_tol:
                v = vs[j]
        out[n] = np.nan if v is None else v
        prev = v
    return np.c_[us, out]


def _near(target, tol):
    def f(u, vs):
        t = target(u)
        d = np.abs(vs - t)
        k = np.argmin(d)
        return vs[k] if d[k] < tol else None
    return f


# =============================================================================================
# 10. sections (sheet 1) and sheet 2
# =============================================================================================


def _airfoil_orientation(P, chord_axis=1):
    """+1 if the leading edge is at the large-page-coordinate end of the chord axis, else -1
    (LE = the end nearer the maximum thickness)."""
    c = P[:, chord_axis]
    t = P[:, 1 - chord_axis]
    lo, hi = c.min(), c.max()
    bins = np.linspace(lo, hi, 41)
    th = []
    for a, b in zip(bins[:-1], bins[1:]):
        m = (c >= a) & (c <= b)
        th.append(np.ptp(t[m]) if m.sum() > 1 else 0.0)
    k = int(np.argmax(th))
    return 1 if k > len(th) / 2 else -1


def _crossings(items, view, xf, axis, value, kinds=("outline",), min_size=15.0):
    """Model-coordinate values of the other axis where the view's outline crosses u_axis = value
    (items smaller than min_size pt -- stray glyph strokes, rivets -- ignored)."""
    out = []
    for it in items:
        if it["view"] != view or it["kind"] not in kinds or it.get("hair"):
            continue
        if np.ptp(it["pts"], axis=0).max() < min_size:
            continue
        Q = xf(it["pts"])
        a, b = Q[:-1], Q[1:]
        m = (np.minimum(a[:, axis], b[:, axis]) <= value) & (np.maximum(a[:, axis], b[:, axis]) >= value) \
            & (a[:, axis] != b[:, axis])
        t = (value - a[m, axis]) / (b[m, axis] - a[m, axis])
        out.extend(a[m, 1 - axis] + t * (b[m, 1 - axis] - a[m, 1 - axis]))
    return np.array(sorted(out))


def _section_page_data(items, sec_seed_item):
    """Per section: page geometry + its own centre / reference lines (shared lines clipped)."""
    out = {}
    allcl = [it["pts"] for it in items if it["kind"] == "centerline" and len(it["pts"]) == 2]
    for name in SECTION_SEEDS_P8:
        v = "sec:" + name
        own = [it for it in items if it["view"] == v]
        O = [it for it in own if it["kind"] == "outline" and np.ptp(it["pts"], axis=0).max() > 15]
        if not O:
            continue
        A = np.vstack([it["pts"] for it in O])
        bb = np.r_[A.min(0), A.max(0)]
        box = bb + [-20, -20, 20, 20]
        its = []
        for it in own:                         # long centre lines owned by this section: clip as well
            if it["kind"] == "centerline" and len(it["pts"]) == 2 and \
                    np.ptp(it["pts"], axis=0).max() > 1.5 * max(bb[2] - bb[0], bb[3] - bb[1]) + 40:
                Q = _clip_seg(it["pts"], box)
                if Q is not None:
                    its.append(dict(it, pts=Q))
            else:
                its.append(it)
        for it in items:                       # shared centre lines, clipped to this section
            if it["view"] != v and v in it.get("also", ()):
                Q = _clip_seg(it["pts"], box) if len(it["pts"]) == 2 else None
                if Q is not None:
                    its.append(dict(it, pts=Q, also=[]))
        cy = 0.5 * (bb[1] + bb[3])
        # centre line: constant page y, spanning most of the section height, nearest the centre
        vert = [P for P in allcl if np.ptp(P[:, 1]) < 0.05 and bb[1] - 5 < P[0, 1] < bb[3] + 5
                and np.ptp(P[:, 0]) > 0.4 * (bb[2] - bb[0]) and P[:, 0].min() < bb[2] and P[:, 0].max() > bb[0]]
        cl_py = float(min(vert, key=lambda P: abs(P[0, 1] - cy))[0, 1]) if vert else None
        # reference / chord line: constant page x, covering the section centre, nearest in x
        horz = [P for P in allcl if np.ptp(P[:, 0]) < 0.05 and P[:, 1].min() <= cy <= P[:, 1].max()
                and np.ptp(P[:, 1]) > 0.5 * (bb[3] - bb[1])]
        def xdist(P):
            x = P[0, 0]
            return max(bb[0] - x, 0.0, x - bb[2])
        horz = [P for P in horz if xdist(P) < 60]
        ref = min(horz, key=lambda P: (xdist(P), -np.ptp(P[:, 1]))) if horz else None
        if ref is not None and not any(it["kind"] == "centerline" and len(it["pts"]) == 2 and
                                       np.allclose(it["pts"], ref) for it in its):
            Q = _clip_seg(ref, box)
            if Q is not None:
                its.append(dict(pts=Q, kind="centerline", tag="centerline", hair=False, view=v, also=[]))
        out[name] = dict(items=its, bbox=bb, cl_py=cl_py, ref_px=float(ref[0, 0]) if ref is not None else None,
                         horz=[float(P[0, 0]) for P in horz])
    return out


def _register_sections(P, X, x10, z_ref, s):
    items = P["items"]
    secs = P["secs"]
    out = {}
    xs, xp, xfr = X["side"], X["plan"], X["front"]
    for name, sd in secs.items():
        its = sd["items"]
        rec = dict(name=name, x=None, lines=[], plane=None, const=None, registration="")
        if name.startswith(("EF", "FR")):
            # (y, z) at station x; seen from ahead like the front view (starboard = large page y)
            if sd["cl_py"] is None or sd["ref_px"] is None:
                continue
            if name == "FR16-30":
                rec["x_range"] = (x10 + 1.510, x10 + 5.150)
                rec["x"] = None
            else:
                rec["x"] = x10 + FR_SECTION_STATIONS_MM[name] / 1000.0
            xf = Xf([[0.0, s], [-s, 0.0]], [-sd["cl_py"] * s, z_ref + sd["ref_px"] * s], ("y", "z"))
            rec.update(plane="yz", const=rec["x"], registration="y: own centre line; z: row reference line = "
                       "side-view '0' line (WL %.3f); x: labelled station" % z_ref)
        elif name.startswith("VF"):
            # (x, y) at height z = z_ref + 1.380 / 2.690; x by matching the trailing edge (side view)
            zc = z_ref + (1.380 if name == "VF1" else 2.690)
            A = np.vstack([it["pts"] for it in its if it["kind"] == "outline"])
            ori = _airfoil_orientation(A, 1)          # +1: LE at large page y (like the side view)
            cr = _crossings(items, "side", xs, 1, zc)
            cr = cr[cr > 10.0]
            te_model = cr.max() if len(cr) else None
            te_page = A[:, 1].min() if ori > 0 else A[:, 1].max()
            chord_px = sd["ref_px"] if sd["ref_px"] is not None else float(np.median(sd["horz"])) if sd["horz"] else A[:, 0].mean()
            xf = Xf([[0.0, -s * ori], [-s, 0.0]], [(te_model or 0.0) + te_page * s * ori, chord_px * s], ("x", "y"))
            rec.update(plane="xy", const=zc, z=zc, registration="x: trailing edge = side-view outline at this WL; "
                       "y: chord line", x=None)
            rec["le_x"] = float(xf(A)[:, 0].min())
            rec["side_crossings_x"] = cr.tolist()
        elif name.startswith(("HF", "WR")):
            A = np.vstack([it["pts"] for it in its if it["kind"] == "outline"])
            ori = _airfoil_orientation(A, 1)
            if name.startswith("HF"):
                yc = 0.0 if name == "HF1" else 2.270
                cr = _crossings(items, "plan", xp, 1, yc)
                cr = cr[cr > 11.5]
                if name == "HF1":
                    # HF1 = symmetry-plane section (bullet + stabiliser root).  The plan's bullet ends in a
                    # blunt 40 mm tip (short strokes < min_size), so no plan crossing at y = 0 reaches it and
                    # the elevator hinge line (13.96) was taken as the trailing edge -> HF1 sat 0.88 m too far
                    # forward (verification fix).  Use the side view's bullet end (lens excluded) instead.
                    cr = np.array([float(xs(P["meas"]["side"]["aft_most"][None])[0, 0])])
                # z: section top = front-view silhouette top at this butt line
                zt = _crossings(items, "front", xfr, 0, yc if yc > 0 else 1e-4)
                zt = zt[zt > 3.2]
            else:
                ex = P["meas"]["extra"]
                k = int(name[2]) - 1
                if k == 0:
                    yc = (ex["wr1_py"] - P["meas"]["front"]["cl_py"]) * s if ex.get("wr1_py") else 0.935
                else:
                    tips = ex.get("wr_tips", [])
                    yc = (tips[k - 1][1] - P["meas"]["front"]["cl_py"]) * s if len(tips) >= k else None
                if yc is None:
                    continue
                cr = _crossings(items, "plan", xp, 1, yc)
                cr = cr[(cr > 4.0) & (cr < 9.0)]
                zt = _crossings(items, "front", xfr, 0, yc)
                zt = zt[(zt > 1.0) & (zt < 3.0)]
            te_model = cr.max() if len(cr) else None
            # _crossings() skips hairline items (e.g. the tail-light lens behind the HF1 bullet), so the
            # section's trailing edge must be taken from its non-hair outline as well
            Anh = [it["pts"] for it in its if it["kind"] == "outline" and not it.get("hair")]
            Ate = np.vstack(Anh) if Anh else A
            te_page = Ate[:, 1].min() if ori > 0 else Ate[:, 1].max()
            top_model = zt.max() if len(zt) else None
            top_page = A[:, 0].min()
            xf = Xf([[0.0, -s * ori], [-s, 0.0]],
                    [(te_model or 0.0) + te_page * s * ori, (top_model or 0.0) + top_page * s], ("x", "z"))
            rec.update(plane="xz", const=float(yc), y=float(yc), x=None,
                       registration=("x: tail-bullet end = side-view bullet end (lens excluded)" if name == "HF1" else
                                     "x: trailing edge = plan-view outline at this butt line") +
                       "; z: section top = front-view upper silhouette at this butt line")
            rec["le_x"] = float(xf(A)[:, 0].min())
            rec["te_found"] = te_model is not None
            rec["top_found"] = top_model is not None
        else:
            continue
        rec["lines"] = [dict(pts=xf(it["pts"]), kind=it["kind"], tag=it["tag"], hair=bool(it.get("hair")))
                        for it in its]
        rec["transform"] = xf.as_dict()
        out[name] = rec
    return out

P9_SECTION_ROWS = [["FR19", "FR21", "FR23", "FR25"], ["FR27", "FR29", "FR31"]]

P9_DETAIL_FRAMES = ["FR19", "FR21", "FR23", "FR25", "FR27", "FR29", "FR31"]

P9_DETAIL_BOX = (330.0, 1780.0, 850.0, 2960.0)       # page pt (x0, y0, x1, y1)

P9_SECTIONS_BOX = (950.0, 850.0, 2000.0, 3200.0)


def _process_page9(page, s):
    """Sheet 2 (page index 9): port cabin-side detail FR19..FR31 and the lower-fuselage / wing-root
    fairing sections FR19..FR31.  Drawn at about twice the scale of sheet 1 (line types too), so
    the dash parameters are larger; the scale is determined in _register_page9."""
    items, arrows, words = _extract_page(page, dash_max=40.0, gap_max=7.5, text_scale=2.0)
    inbox = lambda P, b: P[:, 0].min() >= b[0] and P[:, 0].max() <= b[2] and P[:, 1].min() >= b[1] and P[:, 1].max() <= b[3]
    cl = [it for it in items if it["kind"] == "centerline" and len(it["pts"]) == 2]
    # detail: frame lines = straight centre lines of constant page y inside the detail box
    fr = sorted({round(float(it["pts"][0, 1]), 2) for it in cl
                 if inbox(it["pts"], P9_DETAIL_BOX) and np.ptp(it["pts"][:, 1]) < 0.05 and np.ptp(it["pts"][:, 0]) > 100},
                reverse=True)
    detail_fr = dict(zip(P9_DETAIL_FRAMES, fr)) if len(fr) == len(P9_DETAIL_FRAMES) else {}
    # sections: row reference lines (constant page x) and centre lines (constant page y)
    refs = sorted({round(float(it["pts"][0, 0]), 2) for it in cl if inbox(it["pts"], P9_SECTIONS_BOX)
                   and np.ptp(it["pts"][:, 0]) < 0.05 and np.ptp(it["pts"][:, 1]) > 400})
    cls = {}
    for it in cl:
        P = it["pts"]
        if inbox(P, P9_SECTIONS_BOX) and np.ptp(P[:, 1]) < 0.05 and np.ptp(P[:, 0]) > 150:
            row = int(np.argmin([abs(P[:, 0].mean() - r) for r in refs])) if refs else 0
            cls.setdefault(row, set()).add(round(float(P[0, 1]), 2))
    sec_cl = {}
    for row, names in enumerate(P9_SECTION_ROWS):
        ys = sorted(cls.get(row, ()), reverse=True)
        if len(ys) == len(names):
            for n, y in zip(names, ys):
                sec_cl[n] = dict(cl_py=y, ref_px=refs[row] if row < len(refs) else None, row=row)
    for it in items:
        P = it["pts"]
        if inbox(P, P9_DETAIL_BOX):
            it["view"] = "p9_detail"
        elif inbox(P, P9_SECTIONS_BOX) and sec_cl:
            c = P.mean(0)
            cand = [(abs(c[1] - v["cl_py"]) + 1e3 * (abs(c[0] - v["ref_px"]) > 330 if v["ref_px"] else 0), n)
                    for n, v in sec_cl.items()]
            best = min(cand)
            it["view"] = "p9_sec:" + best[1] if best[0] < 260 else "p9_other"
        else:
            it["view"] = "p9_other"
        it["also"] = []
        if it["kind"] == "centerline" and len(P) > 2 and _straightness(P)[1] > 1.0:
            it["kind"], it["tag"] = "hidden", "phantom"        # curved phantom line = hidden fuselage outline
    faces = _faces(items, "p9_detail", P9_DETAIL_BOX, res=3.0, min_area=500)
    return dict(items=items, arrows=arrows, words=words, detail_fr_py=detail_fr, sections=sec_cl, detail_faces=faces)


def _register_page9(p9, s8, openings_side, x10, z_ref):
    """Scale + position of sheet 2 from the port cabin windows it shares with sheet 1's side view."""
    if not p9 or "items" not in p9:
        return {}, {}, {}
    out_meta = {}
    # detail windows (rounded rectangles of window size) -> centres (page)
    wins = []
    for f in p9["detail_faces"]:
        P = f["poly"]
        w, h = np.ptp(P[:, 1]), np.ptp(P[:, 0])          # along page y = station, along page x = height
        if 40 < w < 110 and 60 < h < 130 and 0.5 < w / h < 1.1:
            wins.append((float(P[:-1, 1].mean()), float(P[:-1, 0].mean()), w, h))
    wins.sort(key=lambda t: -t[0])                     # nose first
    s8w = sorted([m for k, m in openings_side.items() if k.startswith("cabin_win") or k == "door_cargo_win"],
                 key=lambda m: m[:, 0].min())
    xs8 = [float(m[:-1].mean(0)[0]) for m in s8w]
    zs8 = [float(m[:-1].mean(0)[1]) for m in s8w]
    if len(wins) != len(xs8) or len(wins) < 3:
        out_meta["error"] = f"window matching failed: {len(wins)} on sheet 2 vs {len(xs8)} on sheet 1"
        return {}, {}, out_meta
    py = np.array([w[0] for w in wins]); x8 = np.array(xs8)
    # scale: the cabin half-breadth of the sheet-2 sections (phantom fuselage outline) = sheet-1 plan value
    hb_pt = []
    for n, v in p9["sections"].items():
        ph = [it["pts"] for it in p9["items"] if it["view"] == "p9_sec:" + n and it["tag"] == "phantom"]
        if ph:
            hb_pt.append(np.abs(np.vstack(ph)[:, 1] - v["cl_py"]).max())
    hb8 = float(np.nanmean(openings_side.get("_hb", [np.nan]))) if "_hb" in openings_side else 0.8451
    s9 = hb8 / float(np.median(hb_pt))
    # position: sheet-2 window centres onto the sheet-1 side-view windows (offset only)
    a = float(np.mean(x8 + s9 * py))
    res = x8 - (a - s9 * py)
    A = np.c_[np.ones_like(py), -py]
    (a_free, s_free), *_ = np.linalg.lstsq(A, x8, rcond=None)
    px = np.array([w[1] for w in wins])
    c = float(np.mean(np.array(zs8) + px * s9))
    # independent scale checks: window size; free two-parameter window-position fit
    w8 = np.mean([np.ptp(m[:, 0]) for m in s8w]); h8 = np.mean([np.ptp(m[:, 1]) for m in s8w])
    out_meta.update(scale_m_per_pt=float(s9), scale_ratio=float(s9 * 1000 / PT), scale_vs_sheet1=float(s9 / s8),
                    scale_source="cabin half-breadth of the sheet-2 sections = sheet-1 plan half-breadth",
                    window_fit_resid_mm=(res * 1000).round(1).tolist(),
                    scale_from_window_width=float(w8 / np.mean([w[2] for w in wins])),
                    scale_from_window_height=float(h8 / np.mean([w[3] for w in wins])),
                    scale_from_window_positions_free_fit=float(s_free))
    xd = Xf([[0.0, -s9], [-s9, 0.0]], [a, c], ("x", "z"))
    fr_x = {n: float(a - s9 * y) for n, y in p9["detail_fr_py"].items()}
    out_meta["frame_stations"] = fr_x
    out_meta["frame_stations_rel_fr10_mm"] = {n: round((v - x10) * 1000, 1) for n, v in fr_x.items()}
    detail = _map_items(p9["items"], "p9_detail", xd)
    secs = {}
    for n, v in p9["sections"].items():
        if v["ref_px"] is None:
            continue
        xf = Xf([[0.0, s9], [-s9, 0.0]], [-v["cl_py"] * s9, z_ref + v["ref_px"] * s9], ("y", "z"))
        its = [it for it in p9["items"] if it["view"] == "p9_sec:" + n]
        O = [it["pts"] for it in its if it["kind"] != "centerline"]
        if O:                                  # clip the row's shared reference line to this section
            A0 = np.vstack(O)
            box = np.r_[A0.min(0) - 20, A0.max(0) + 20]
            its = [dict(it, pts=_clip_seg(it["pts"], box)) if it["kind"] == "centerline" and len(it["pts"]) == 2
                   and _clip_seg(it["pts"], box) is not None else it for it in its]
        lines = [dict(pts=xf(it["pts"]), kind=it["kind"], tag=it["tag"], hair=bool(it.get("hair"))) for it in its]
        ph = [l["pts"] for l in lines if l["tag"] == "phantom"]
        rec = dict(name=n, x=fr_x.get(n), plane="yz", const=fr_x.get(n), lines=lines, transform=xf.as_dict(), sheet=2,
                   registration="scale/x: sheet-2 windows matched to sheet-1 side view; y: own centre line; "
                                "z: row reference line = side-view '0' line (verified by the phantom keel)")
        if ph:
            A_ = np.vstack(ph)
            rec["phantom_keel_z"] = float(A_[:, 1].min())
            rec["phantom_half_breadth"] = float(np.abs(A_[:, 0]).max())
        secs[n] = rec
    out_meta["detail_transform"] = xd.as_dict()
    return detail, secs, out_meta


# =============================================================================================
# 11. checks
# =============================================================================================


def _model_compare(P, X, out):
    """Drawing vs model: expected = value measured on the model (GLB / model.fuselage)."""
    C = []
    try:
        ms = model_samples()
    except Exception as e:
        return [_chk(f"model comparison unavailable: {e!r}", None, None)]
    if not ms:
        return C
    items = P["items"]
    xp, xfr = X["plan"], X["front"]
    for y in (0.95, 2.0, 4.0, 6.0):
        cr = _crossings(items, "plan", xp, 1, y)
        cr = cr[(cr > 4.0) & (cr < 9.0)]
        if len(cr) and f"wing_le_x@{y}" in ms:
            C.append(_chk(f"[vs model] wing LE station at BL {y} (plan)", ms[f"wing_le_x@{y}"], float(cr.min())))
            C.append(_chk(f"[vs model] wing TE station at BL {y} (plan)", ms[f"wing_te_x@{y}"], float(cr.max())))
    for y in (2.0, 4.0, 6.0, 7.395):
        cz = _crossings(items, "front", xfr, 0, y)
        cz = cz[(cz > 0.6) & (cz < 2.8)]
        if len(cz) and f"wing_top_z@{y}" in ms:
            C.append(_chk(f"[vs model] wing top WL at BL {y} (front silhouette)", ms[f"wing_top_z@{y}"], float(cz.max())))
            C.append(_chk(f"[vs model] wing bottom WL at BL {y} (front silhouette)", ms[f"wing_bot_z@{y}"], float(cz.min())))
    for y in (1.0, 2.27):
        cr = _crossings(items, "plan", xp, 1, y)
        cr = cr[(cr > 11.5) & (cr < 15.5)]
        if len(cr):
            C.append(_chk(f"[vs model] tailplane LE station at BL {y} (plan)", ms[f"tail_le_x@{y}"], float(cr.min())))
            C.append(_chk(f"[vs model] tailplane TE station at BL {y} (plan)", ms[f"tail_te_x@{y}"], float(cr.max())))
    cz = _crossings(items, "front", xfr, 0, 1.0)
    cz = cz[cz > 3.3]
    if len(cz):
        C.append(_chk("[vs model] tailplane top WL at BL 1.0 (front)", ms["tail_top_z@1.0"], float(cz.max())))
    C.append(_chk("[vs model] span over winglets (plan)", ms["span"],
                  (P["meas"]["plan"]["port_tip"][0] - P["meas"]["plan"]["stbd_tip"][0]) * P["meas"]["side"]["scale_m_per_pt"]))
    oml = _model_oml()
    prof = out.get("profiles", {})
    if oml is not None:
        for x in (2.0, 3.0, 3.5, 4.0, 5.0, 8.0, 10.0, 11.0, 12.0, 13.0):
            for key, mk, nm in (("side_crown", "top", "crown WL"), ("side_keel", "bot", "keel WL"),
                                ("plan_hb_stbd", "hw", "half-breadth")):
                pr = prof.get(key)
                if pr is None:
                    continue
                v = np.interp(x, pr[:, 0], pr[:, 1], left=np.nan, right=np.nan)
                if np.isfinite(v):
                    C.append(_chk(f"[vs model] fuselage {nm} at x={x}", float(np.interp(x, oml['x'], oml[mk])), float(v)))
    # glazing / openings extents (port side)
    G = out["glazing"].get("side", {})
    if G:
        A = np.vstack(list(G.values()))
        C.append(_chk("[vs model] port flight-deck glazing, fwd-most station", ms["glz_port_x"][0], float(A[:, 0].min()),
                      note="drawing incl. ws+dv+sw (NGX); model PRO (no DV)"))
        C.append(_chk("[vs model] port flight-deck glazing, aft-most station", ms["glz_port_x"][1], float(A[:, 0].max())))
        C.append(_chk("[vs model] port flight-deck glazing, lowest WL", ms["glz_port_z"][0], float(A[:, 1].min())))
        C.append(_chk("[vs model] port flight-deck glazing, highest WL", ms["glz_port_z"][1], float(A[:, 1].max())))
        if "sw_port" in G:
            sw = G["sw_port"]
            C.append(_chk("[vs model] side window sill WL (sw_port bottom)", 1.985, float(sw[:, 1].min()),
                          note="model SW_BOTTOM 1.985"))
            C.append(_chk("[vs model] side window aft edge (sw_port)", 4.268, float(sw[:, 0].max()), note="model SW_REAR 4.268"))
    O = out["openings"].get("side", {})
    for n in ("door_airstair", "door_cargo"):
        if n in O and n + "_x" in ms:
            C.append(_chk(f"[vs model] {n} fwd edge", ms[n + "_x"][0], float(O[n][:, 0].min())))
            C.append(_chk(f"[vs model] {n} aft edge", ms[n + "_x"][1], float(O[n][:, 0].max())))
            C.append(_chk(f"[vs model] {n} sill WL", ms[n + "_z"][0], float(O[n][:, 1].min())))
            C.append(_chk(f"[vs model] {n} top WL", ms[n + "_z"][1], float(O[n][:, 1].max())))
    wins = sorted([P_[:-1].mean(0)[0] for k, P_ in O.items() if k.startswith("cabin_win")])
    mw = [5.52, 6.32, 7.12, 7.92]
    for k, (a, b) in enumerate(zip(mw, wins), 1):
        C.append(_chk(f"[vs model] port cabin window {k} centre station", a, float(b), note="model FIXED_WINDOWS[-1]"))
    if "door_cargo_win" in O:
        C.append(_chk("[vs model] cargo-door window centre station", 8.72, float(O["door_cargo_win"][:-1].mean(0)[0]),
                      note="model DOOR_WINDOWS['door_cargo']"))
    return C


def _chk(name, expected, measured, unit="m", note="", model=None):
    d = None
    if expected is not None and measured is not None:
        d = (measured - expected) * (1000.0 if unit == "m" else 1.0)
    return dict(name=name, expected=expected, measured=measured, delta_mm=d, unit=unit, note=note, model=model)


def _checks(P, X, x10, s, z_ref, fits, out):
    ms, mp, mf, ex = (P["meas"][k] for k in ("side", "plan", "front", "extra"))
    xs, xp, xfr = X["side"], X["plan"], X["front"]
    C = []
    st = ms["station_py"]
    # scale consistency
    res = np.array(list(ms["station_resid_mm"].values()))
    C.append(_chk("Scale fit: FR stations EF1..FR40 (11 lines), max |residual|", 0.0,
                  float(np.abs(res).max()), unit="mm", note=f"s = {s*1000:.5f} mm/pt = 1:{s*1000/PT:.3f}"))
    meas_chain = []
    for row in ms["dim_rows"]:
        if row["px"] < 170:                  # first row: running (ordinate) ticks, covered by the fit
            continue
        t = np.array(sorted(row["ticks_py"], reverse=True))
        meas_chain.extend((np.diff(-t) * s * 1000).tolist())
    for e in LABELS["side_chain"]:
        if meas_chain:
            k = int(np.argmin([abs(m - e) for m in meas_chain]))
            C.append(_chk(f"Side chain dim {e} (arrow tip to arrow tip)", float(e), float(meas_chain.pop(k)), unit="mm"))
    # side view: vertical dimensions above the '0' line
    vv = []
    for d in ex["side_vdims"]:
        for px in d["px"]:
            vv.append((ms["ref_px"] - px) * s * 1000)
    vv = sorted(set(round(v, 1) for v in vv))
    for e in (-290, 683, 1380, 2690):
        m = min(vv, key=lambda v: abs(v - e)) if vv else None
        C.append(_chk(f"Side dim {abs(e)} ({'below' if e < 0 else 'above'} the '0' line)", float(e), m, unit="mm"))
    # lengths
    xt = xs(ms["spinner_tip"][None])[0]
    xa = xs(ms["aft_most"][None])[0]
    xah = xs(ms["aft_most_incl_hair"][None])[0]
    C.append(_chk("Overall length, side (spinner tip -> tail-bullet end)", MODEL_REF["length"], xa[0] - xt[0]))
    C.append(_chk("Overall length, side, incl. tail-light lens", MODEL_REF["length"], xah[0] - xt[0]))
    pt_ = xp(mp["spinner_tip"][None])[0]
    pa_ = xp(mp["aft_most"][None])[0]
    C.append(_chk("Overall length, plan (spinner tip -> aft-most)", MODEL_REF["length"], pa_[0] - pt_[0],
                  note="plan aft-most includes the tail-light lens"))
    C.append(_chk("Spinner tip station (side)", MODEL_REF["spinner_tip"], float(xt[0]), note=f"anchor={P.get('anchor', '')}"))
    C.append(_chk("Aft-most station (side, bullet end)", MODEL_REF["aft_most"], float(xa[0])))
    C.append(_chk("Spinner tip WL (side)", MODEL_REF["prop_axis_z"], float(xt[1])))
    # heights
    C.append(_chk("Height, side (top of tail bullet above drawn ground)", MODEL_REF["height"], float(xs(ms["top_most"][None])[0, 1])))
    C.append(_chk("Height, front", MODEL_REF["height"], float(xfr(mf["top_most"][None])[0, 1])))
    # spans
    sp = (mp["port_tip"][0] - mp["stbd_tip"][0]) * s
    C.append(_chk("Span, plan (over winglets)", MODEL_REF["span"], sp, note="sheet label: SPANNWEITE 16.114 m"))
    C.append(_chk("Span, plan vs sheet label 16.114 m", LABELS["span_label"] / 1000.0, sp))
    C.append(_chk("Span, front", MODEL_REF["span"], (mf["stbd_tip"][1] - mf["port_tip"][1]) * s))
    C.append(_chk("Tailplane span, plan", MODEL_REF["tail_span"], (mp["tail_port_tip"][0] - mp["tail_stbd_tip"][0]) * s))
    C.append(_chk("Tailplane span, front", MODEL_REF["tail_span"], (mf["tail_stbd_tip"][1] - mf["tail_port_tip"][1]) * s))
    # gear
    ty = ms["tyres"]
    if len(ty) == 2:
        (nx, ny, nr, *_), (mx, my, mr, *_) = ty
        C.append(_chk("Wheelbase, side (tyre centres)", MODEL_REF["wheelbase"], (ny - my) * s))
        C.append(_chk("Nose tyre diameter (17.5 in)", 0.4445, 2 * nr * s))
        C.append(_chk("Main tyre diameter (22 in)", 0.5588, 2 * mr * s))
        C.append(_chk("Nose tyre bottom on ground line", 0.0, (ms["ground_px"] - (nx + nr)) * s))
        C.append(_chk("Main tyre bottom on ground line", 0.0, (ms["ground_px"] - (mx + mr)) * s))
        C.append(_chk("Nose wheel axle station", None, float(xs(np.array([[nx, ny]]))[0, 0]),
                      note=f"model nose-gear pivot {MODEL_REF['nose_gear_pivot']}"))
        C.append(_chk("Main wheel axle station", None, float(xs(np.array([[mx, my]]))[0, 0]),
                      note=f"model main-gear pivot {MODEL_REF['main_gear_pivot']}"))
    for d in mf["dims"]:
        yy = sorted(d["a"][1] + np.array(d["ticks"]) * d["d"][1])
        if len(yy) == 2:
            L = (yy[1] - yy[0]) * s
            if L > 3:
                C.append(_chk("Track, front (dimension 4530)", MODEL_REF["track"], L))
            else:
                C.append(_chk("Front dim 935 (centre line -> WR1)", 0.935, L))
    tb = [xfr(t[None])[0] for t in mf["tyre_bottoms"]]
    for t in tb:
        C.append(_chk(f"Front tyre bottom at y={t[0]:+.2f}", 0.0, float(t[1])))
    # propeller
    pc = mf["prop_circle"]
    C.append(_chk("Propeller diameter, front circle", MODEL_REF["prop_dia"], 2 * pc[2] * s, note="label: 2,67 m"))
    cz = float(xfr(np.array([[pc[0], pc[1]]]))[0, 1])
    C.append(_chk("Propeller circle centre WL, front", MODEL_REF["prop_axis_z"], cz))
    C.append(_chk("Propeller circle centre BL, front", 0.0, float(xfr(np.array([[pc[0], pc[1]]]))[0, 0])))
    C.append(_chk("Prop ground clearance, front circle", MODEL_REF["prop_clearance"], cz - pc[2] * s))
    pl = ms["prop_line"]
    if pl is not None:
        Q = xs(pl)
        C.append(_chk("Propeller diameter, side (disc edge-on)", MODEL_REF["prop_dia"], float(np.hypot(*(Q[-1] - Q[0])))))
        C.append(_chk("Prop ground clearance, side", MODEL_REF["prop_clearance"], float(Q[:, 1].min())))
        ang = math.degrees(math.atan2(Q[0, 0] - Q[-1, 0], Q[0, 1] - Q[-1, 1]))
        C.append(_chk("Propeller disc tilt from vertical (side; + = top forward)", None, -ang, unit="deg",
                      note="implies a nose-down thrust line of the same angle"))
        C.append(_chk("Propeller disc centre WL, side", MODEL_REF["prop_axis_z"], float(Q[:, 1].mean())))
    # stations
    C.append(_chk("FR10 station (anchor used)", None, float(x10[P.get("anchor", "spinner")]) if P.get("anchor") in x10 else None))
    for k, v in x10.items():
        C.append(_chk(f"FR10 station under anchor '{k}'", None, float(v)))
    if ex.get("firewall_py"):
        C.append(_chk("Firewall / cowling joint line station (side)", MODEL_REF["firewall"],
                      float(xs(np.array([[ms['ground_px'], ex['firewall_py']]]))[0, 0])))
    fr10_plan = mp["refmarks"][0] if mp["refmarks"] else None
    if fr10_plan is not None:
        xpl = float(xp(np.array([[fr10_plan[0], fr10_plan[1]]]))[0, 0])
        C.append(_chk("FR10 mark station, plan (own spinner anchor) vs side", float(xs(np.array([[0, st['FR10']]]))[0, 0]), xpl))
    for d in mp["dims"]:
        if abs(d["d"][0]) < 1e-3 and len(d["ticks"]) == 2:           # 2820 (along page y)
            L = abs(d["ticks"][1] - d["ticks"][0]) * s
            C.append(_chk("Plan dim 2820 (FR10 -> wing reference line)", 2.820, L))
            yy = d["a"][1] + np.array(d["ticks"]) * d["d"][1]
            xw = float(xp(np.array([[mp['cl_px'], yy.min()]]))[0, 0])
            C.append(_chk("Wing reference line (2820 line) station", None, xw,
                          note=f"model LEMAC {MODEL_REF['lemac']} + 25% MAC = {MODEL_REF['lemac'] + 0.25 * MODEL_REF['mac']:.3f}"))
        if abs(d["d"][1]) < 1e-3:                                      # 2270 (along page x) from the tail mark
            L = abs(d["a"][0] - d["b"][0]) * s
            C.append(_chk("Plan dim 2270 (centre line -> HF2)", 2.270, L))
    # wing root LE / TE at the fuselage junction (plan): crossings of y = +-0.95 .. 1.0
    for yy in (0.95, -0.95):
        cr = _crossings(P["items"], "plan", xp, 1, yy)
        cr = cr[(cr > 4.0) & (cr < 9.0)]
        if len(cr):
            C.append(_chk(f"Wing LE at BL {yy:+.2f} (plan, first crossing aft of 4.0 m)", MODEL_REF["wing_root_le"], float(cr.min()),
                          note="model root LE ~5.20 (LEMAC 5.323)"))
            C.append(_chk(f"Wing TE at BL {yy:+.2f} (plan, last crossing)", None, float(cr.max())))
    # WR running dimensions (front view, along the wing)
    if ex.get("wr_along_mm"):
        for e, m in zip((4675, 5780, 6520), ex["wr_along_mm"]):
            C.append(_chk(f"Front WR running dim {e} (along the wing from WR1)", float(e), float(m), unit="mm"))
        C.append(_chk("Wing reference-line dihedral, front (WR dimension line)", MODEL_REF["dihedral_deg"],
                      ex["wr_line_deg"], unit="deg"))
    # fuselage cross-section (side / plan) in the cabin
    oml = _model_oml()
    prof = out.get("profiles", {})
    for nm, key, lo, hi, mref in (("Cabin crown WL (side, FR16..FR30 mean)", "side_crown", None, None, "top"),
                                  ("Cabin keel WL (side, FR16..FR30 mean)", "side_keel", None, None, "bot")):
        if key in prof and oml is not None:
            a = xs(np.array([[0, st['FR16']]]))[0, 0]
            b = xs(np.array([[0, st['FR30']]]))[0, 0]
            pr = prof[key]
            m = (pr[:, 0] >= a) & (pr[:, 0] <= b) & np.isfinite(pr[:, 1])
            if m.any():
                mv = float(np.interp(0.5 * (a + b), oml["x"], oml[mref]))
                C.append(_chk(nm, mv, float(np.nanmean(pr[m, 1])), note="expected = model value"))
    for key in ("plan_hb_stbd",):
        if key in prof and oml is not None and False:
            pr = prof[key]
            m = (pr[:, 0] >= 6.0) & (pr[:, 0] <= 8.0) & np.isfinite(pr[:, 1])
            if m.any():
                C.append(_chk("Cabin half-breadth (plan, STA 6-8 mean)", 0.845, float(np.nanmean(pr[m, 1])),
                              note="expected = model half_w"))
    zr = z_ref
    C.append(_chk("Side '0' reference line WL", None, zr))
    for k, f in fits.items():
        lbl = {"xz": "crown+keel, dx,dz free", "x": "crown+keel, dz=0", "nose_x": "x<=3.1 only, dz=0"}[k]
        C.append(_chk(f"OML fit ({lbl}): drawing - model dx", 0.0, f["dx"],
                      note=f"dz={f['dz']*1000:+.1f} mm, inliers {f['n_inliers']}/{f['n_model']}, next-best dx "
                           f"{f['second_best_dx']*1000:+.0f} mm (objective x{f['second_best_ratio']:.2f})"))
    C.extend(_model_compare(P, X, out))
    # frame sections vs side view crown / keel
    for name, rec in out.get("sections", {}).items():
        if rec.get("plane") != "yz" or rec.get("x") is None or rec.get("sheet") == 2:
            continue
        L = [l["pts"] for l in rec["lines"] if l["kind"] == "outline" and not l["hair"]]
        if not L:
            continue
        A = np.vstack(L)
        top = A[:, 1].max()
        if rec["x"] > 9.8:            # dorsal fin / ventral strakes: section top/bottom not the fuselage
            continue
        cz = _crossings(P["items"], "side", xs, 0, rec["x"])
        ct = cz[(cz > 1.9) & (cz < 3.0)]
        if len(ct):
            C.append(_chk(f"Section {name} top vs side-view crown at x={rec['x']:.3f}", float(ct.max()), float(top)))
        kp = out.get("profiles", {}).get("side_keel")
        if kp is not None:
            kv = np.interp(rec["x"], kp[:, 0], kp[:, 1], left=np.nan, right=np.nan)
            if np.isfinite(kv):
                C.append(_chk(f"Section {name} bottom vs side-view keel line at x={rec['x']:.3f}", float(kv),
                              float(A[:, 1].min())))
    ds = out.get("detail_stbd")
    if ds:
        L = [l["pts"] for l in ds if l["kind"] == "outline" and np.ptp(l["pts"][:, 0]) > 2.0]
        if L:
            C.append(_chk("Sheet-1 stbd detail: top line WL vs cabin crown", 2.769, float(max(P_[:, 1].max() for P_ in L)),
                          note="detail registered on its FR16 line + horizontal centre line (= '0' line)"))
    # sheet 2
    m9 = out.get("_sheet2_meta") or {}
    if m9.get("scale_m_per_pt"):
        C.append(_chk("Sheet-2 scale (cabin width) vs window width", m9["scale_m_per_pt"] * 1000,
                      m9["scale_from_window_width"] * 1000, unit="mm", note="mm per pt; sheet 2 is drawn at ~1:12"))
        for k, r in enumerate(m9.get("window_fit_resid_mm", []), 1):
            C.append(_chk(f"Sheet-2 window {k} station residual (sheet 1 - sheet 2)", 0.0, r, unit="mm"))
    det = out.get("detail_port_sheet2")
    if det:
        top = max(l["pts"][:, 1].max() for l in det if l["kind"] == "outline" and np.ptp(l["pts"][:, 0]) > 2.0)
        C.append(_chk("Sheet-2 detail crown line WL vs sheet-1 cabin crown", 2.769, float(top),
                      note="sheet 2 z registered on the windows"))
        doors = [l["pts"] for l in det if l["kind"] == "outline" and 0.5 < np.ptp(l["pts"][:, 0]) < 1.6
                 and 1.1 < np.ptp(l["pts"][:, 1]) < 1.6]
        O = out.get("openings", {}).get("side", {})
        for D in doors:
            nm = "door_cargo" if np.ptp(D[:, 0]) > 1.0 else "door_airstair"
            if nm in O:
                C.append(_chk(f"Sheet-2 {nm} fwd edge vs sheet 1", float(O[nm][:, 0].min()), float(D[:, 0].min())))
                C.append(_chk(f"Sheet-2 {nm} aft edge vs sheet 1", float(O[nm][:, 0].max()), float(D[:, 0].max())))
    for n, rec in out.get("sections", {}).items():
        if rec.get("sheet") == 2 and "phantom_keel_z" in rec:
            kv = z_ref - LABELS["side_ref_to_keel"] / 1000.0
            C.append(_chk(f"Sheet-2 section {n}: phantom fuselage keel vs cabin keel line (ref - 290)", kv,
                          rec["phantom_keel_z"], note=f"x={rec['x']:.3f} (sheet-2 frame line)" if rec.get("x") else ""))
            C.append(_chk(f"Sheet-2 section {n}: phantom fuselage half-breadth", 0.8451, rec["phantom_half_breadth"],
                          note="expected = sheet-1 plan cabin half-breadth"))
    return C


# =============================================================================================
# 12. public API
# =============================================================================================

_MEM = {}


def _code_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:10]


def _cache_file(sha):
    """Processed page data, keyed by PDF hash + CODE_VERSION + hash of this source file."""
    return CACHE / f"mbp_{sha[:16]}_v{CODE_VERSION}_{_code_hash()}.pkl"


def processed(force=False, verbose=True):
    """Page-level extraction (cached in refs/cache/ by PDF hash + CODE_VERSION)."""
    pdf = fetch()
    sha = _sha256(pdf)
    if not force and sha in _MEM:
        return _MEM[sha]
    cf = _cache_file(sha)
    if cf.exists() and not force:
        try:
            with open(cf, "rb") as f:
                P = pickle.load(f)
            if P.get("version") == CODE_VERSION and P.get("sha256") == sha and P.get("code") == _code_hash():
                _MEM[sha] = P
                return P
        except Exception:
            pass
    P = _process(verbose=verbose)
    P["code"] = _code_hash()
    for old in CACHE.glob(f"mbp_{sha[:16]}_*.pkl"):          # drop stale caches of this PDF
        if old != cf:
            old.unlink()
    with open(cf, "wb") as f:
        pickle.dump(P, f, protocol=pickle.HIGHEST_PROTOCOL)
    _MEM[sha] = P
    return P


def load(anchor: str = "spinner", front_z: str = "ground", force: bool = False) -> dict:
    """Registered Pilatus drawing in MODEL coordinates.

    anchor : side/plan x anchor -- 'spinner' (spinner tip = STA 0.39, default), 'oml' (least-squares
             fit of the side profile's crown+keel onto model.fuselage, scale fixed, z kept on the drawn
             ground line), 'oml_xz' (same fit with dz free as well; only dx is used), 'aft' (aft-most
             point = STA 14.79).
    front_z: 'ground' (tyre bottoms = WL 0, default) or 'prop' (propeller-circle centre = WL 1.655).

    Returns {'side'|'plan'|'front'|'detail_stbd'|'detail_port_sheet2': [ {pts (N,2), kind, tag, hair} ],
             'sections': {name: {x, lines, plane, const, registration, ...}},
             'glazing': {'side'|'plan'|'front': {'ws_stbd'|'ws_port'|'sw_stbd'|'sw_port'|'dv_port': (N,2) closed}},
             'openings': {'side': {'cabin_win_k'|'door_airstair'|'door_cargo'|'door_cargo_win': (N,2)}},
             'profiles': {'side_crown'|'side_keel'|'plan_hb_stbd'|'plan_hb_port': (N,2), NaN = not drawn,
                          'side_bottom': lowest drawn line (side_keel incl. wing fairing + ventral strake)},
             'meta': {scale_m_per_pt, fr10_station{anchor}, oml_fit, transforms, checks[], sheet2, ...}}
    kind: 'outline' | 'hidden' | 'centerline' | 'annotation' (tag: text, arrow, dim, ext, hatch, ground,
    refmark, leader; 'phantom' for sheet-2 hidden fuselage lines).
    """
    P = processed(force=force)
    return _register(P, anchor=anchor, front_z=front_z)


def report(d, file=None):
    m = d["meta"]
    p = lambda *a: print(*a, file=file)
    p(f"Pilatus drawing {m['source']['drawing']} (sheet 1, page index 8) -> model coordinates")
    p(f"  PDF sha256 {m['sha256'][:16]}..  code v{m['version']}")
    p(f"  scale: {m['scale_m_per_pt']*1000:.5f} mm/pt = 1:{m['scale_ratio']:.3f} "
      f"(nominal 1:24 -> x{m['scale_vs_nominal']:.5f})")
    p(f"  anchor: {m['anchor']}   front z: {m['front_z']}   '0' reference line WL {m['z_ref_line']:.4f}")
    p("  FR10 station under the anchors: " + ", ".join(f"{k} {v:.4f}" for k, v in m["fr10_station"].items()))
    fa = m["fr10_station"]
    if "oml" in fa:
        dd = (fa["oml"] - fa["spinner"]) * 1000
        p(f"  (a) spinner vs (b) OML fit: {dd:+.1f} mm" + ("   ** > 30 mm: FLAG **" if abs(dd) > 30 else ""))
    for k, f in m["oml_fit"].items():
        p(f"  OML fit [{k}]: drawing = model + (dx {f['dx']*1000:+.1f} mm, dz {f['dz']*1000:+.1f} mm), rms "
          f"{f['rms_mm']:.1f} mm, inliers {f['n_inliers']}/{f['n_model']} (crown {f.get('crown_inliers')}, "
          f"keel {f.get('keel_inliers')}); next-best dx {f['second_best_dx']*1000:+.0f} mm with objective "
          f"x{f['second_best_ratio']:.2f}")
    g = m["front_ground_px"]
    p(f"  front view z: tyre bottoms vs prop-centre(WL 1.655) datum disagree by {g['disagreement_mm']:+.1f} mm")
    p("")
    p(f"  {'check':66s} {'expected':>10s} {'measured':>10s} {'delta':>9s}")
    for c in m["checks"]:
        e = "" if c["expected"] is None else f"{c['expected']:.4f}" if c["unit"] == "m" else f"{c['expected']:.2f}"
        v = "" if c["measured"] is None else f"{c['measured']:.4f}" if c["unit"] == "m" else f"{c['measured']:.2f}"
        dl = "" if c["delta_mm"] is None else (f"{c['delta_mm']:+.1f}" + (" mm" if c["unit"] in ("m", "mm") else " " + c["unit"]))
        p(f"  {c['name'][:66]:66s} {e:>10s} {v:>10s} {dl:>9s}  {c['note']}")
    p("")
    for v, G in d["glazing"].items():
        p(f"  glazing {v}: " + ", ".join(f"{k}({len(P_)} pts, {_bbox_str(P_)})" for k, P_ in sorted(G.items())))
    op = d.get("openings", {}).get("side", {})
    if op:
        p("  openings side: " + ", ".join(f"{k} x[{P_[:, 0].min():.2f},{P_[:, 0].max():.2f}] "
                                          f"z[{P_[:, 1].min():.2f},{P_[:, 1].max():.2f}]" for k, P_ in op.items()))
    def where(r):
        if r.get("x_range"):
            return f"x={r['x_range'][0]:.2f}..{r['x_range'][1]:.2f}"
        if r["plane"] == "yz":
            return f"x={r['x']:.3f}"
        return ("z" if r["plane"] == "xy" else "y") + f"={r['const']:.3f}"
    p("  sections: " + ", ".join(f"{k}@{where(r)}" + (" (sheet 2)" if r.get("sheet") == 2 else "")
                                 for k, r in d["sections"].items()))
    s2 = m.get("sheet2") or {}
    if s2.get("scale_m_per_pt"):
        p(f"  sheet 2: scale 1:{s2['scale_ratio']:.3f} (window-size check 1:{s2['scale_from_window_width'] * 1000 / PT:.3f}), "
          "frames " + ", ".join(f"{k} {v:+.0f}" for k, v in s2["frame_stations_rel_fr10_mm"].items()) + " mm rel. FR10")


def _bbox_str(P):
    return f"[{P[:, 0].min():.3f},{P[:, 0].max():.3f}]x[{P[:, 1].min():.3f},{P[:, 1].max():.3f}]"


# =============================================================================================
# 13. model access (out/pc12.glb, model.fuselage) for comparisons and overlays
# =============================================================================================


def read_glb(path=None):
    """out/pc12.glb -> {part_id: [(V (n,3) MODEL coords, F (m,3)), ...]} (node transforms applied)."""
    import struct
    path = Path(path or ROOT / "out" / "pc12.glb")
    data = path.read_bytes()
    n_js = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + n_js])
    binb = data[20 + n_js + 8:]
    ctype = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

    def acc(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        dt = np.dtype(ctype[a["componentType"]])
        nc = ncomp[a["type"]]
        stride = bv.get("byteStride", dt.itemsize * nc)
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        raw = np.frombuffer(binb, dtype=np.uint8, count=stride * (a["count"] - 1) + dt.itemsize * nc, offset=off)
        out = np.lib.stride_tricks.as_strided(raw, shape=(a["count"], nc * dt.itemsize), strides=(stride, 1))
        arr = np.ascontiguousarray(out).view(dt).reshape(a["count"], nc).astype(float)
        if a.get("normalized"):
            arr = arr / float(np.iinfo(dt).max) if dt.kind in "iu" else arr
            if dt.kind == "i":
                arr = np.maximum(arr, -1.0)
        return arr

    def qmat(q):
        x, y, z, w = q
        return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

    def local(n):
        M = np.eye(4)
        if "matrix" in n:
            return np.array(n["matrix"]).reshape(4, 4).T
        S = np.diag(n.get("scale", [1, 1, 1]))
        R = qmat(n.get("rotation", [0, 0, 0, 1]))
        M[:3, :3] = R @ S
        M[:3, 3] = n.get("translation", [0, 0, 0])
        return M

    parts = {}

    def walk(ni, M, part):
        n = js["nodes"][ni]
        M = M @ local(n)
        part = (n.get("extras") or {}).get("part", part)
        if "mesh" in n:
            for prim in js["meshes"][n["mesh"]]["primitives"]:
                V = acc(prim["attributes"]["POSITION"])
                F = acc(prim["indices"]).astype(np.int64).reshape(-1, 3)
                Vw = V @ M[:3, :3].T + M[:3, 3]
                Vm = np.stack([Vw[:, 2], Vw[:, 0], Vw[:, 1]], -1)    # gl (X=y,Y=z,Z=x) -> model
                parts.setdefault(part or n.get("name", "?"), []).append((Vm, F))
        for c in n.get("children", []):
            walk(c, M, part)

    for r in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4), None)
    return parts


def slice_mesh(V, F, axis, c):
    """Intersection points of a triangle mesh with the plane coord[axis] = c."""
    T = V[F]                                   # (m, 3, 3)
    d = T[..., axis] - c
    out = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        m = (d[:, i] * d[:, j]) < 0
        t = d[m, i] / (d[m, i] - d[m, j])
        out.append(T[m, i] + (T[m, j] - T[m, i]) * t[:, None])
    return np.vstack(out) if out else np.zeros((0, 3))

_GLB_CACHE = {}


def model_samples(path=None):
    """A few reference values measured on out/pc12.glb (for the drawing-vs-model table)."""
    path = Path(path or ROOT / "out" / "pc12.glb")
    key = (str(path), path.stat().st_mtime if path.exists() else None)
    if key in _GLB_CACHE:
        return _GLB_CACHE[key]
    if not path.exists():
        return {}
    parts = read_glb(path)

    def pts(names, axis, c):
        P = [slice_mesh(V, F, axis, c) for n in names for V, F in parts.get(n, [])]
        P = [p for p in P if len(p)]
        return np.vstack(P) if P else np.zeros((0, 3))

    def allv(names):
        return np.vstack([V for n in names for V, F in parts.get(n, [])])

    wingS = ["wing_R", "flap_R", "aileron_R", "ail_tab_R"]
    tail = ["stabilizer", "elevator_R", "elevator_L"]
    ms = {}
    for y in (0.95, 2.0, 4.0, 6.0, 7.395):
        p = pts(wingS, 1, y)
        if len(p):
            ms[f"wing_le_x@{y}"] = float(p[:, 0].min())
            ms[f"wing_te_x@{y}"] = float(p[:, 0].max())
            ms[f"wing_top_z@{y}"] = float(p[:, 2].max())
            ms[f"wing_bot_z@{y}"] = float(p[:, 2].min())
    for y in (0.3, 1.0, 2.27):
        p = pts(tail, 1, y)
        if len(p):
            ms[f"tail_le_x@{y}"] = float(p[:, 0].min())
            ms[f"tail_te_x@{y}"] = float(p[:, 0].max())
            ms[f"tail_top_z@{y}"] = float(p[:, 2].max())
    ws = allv(["winglet_R", "winglet_L", "wing_R", "wing_L"])
    ms["span"] = float(ws[:, 1].max() - ws[:, 1].min())
    ts = allv(tail)
    ms["tail_span"] = float(ts[:, 1].max() - ts[:, 1].min())
    ms["tail_le_root_x"] = float(ts[:, 0].min())
    ms["tail_te_x"] = float(ts[:, 0].max())
    g = allv(["glazing_flightdeck"])
    gp = g[g[:, 1] < -0.3]
    ms["glz_port_x"] = (float(gp[:, 0].min()), float(gp[:, 0].max()))
    ms["glz_port_z"] = (float(gp[:, 2].min()), float(gp[:, 2].max()))
    for n in ("door_airstair", "door_cargo", "exit_hatch"):
        if n in parts:
            v = allv([n])
            ms[n + "_x"] = (float(v[:, 0].min()), float(v[:, 0].max()))
            ms[n + "_z"] = (float(v[:, 2].min()), float(v[:, 2].max()))
    _GLB_CACHE[key] = ms
    return ms


# =============================================================================================
# 14. debug images (out/tmp/mbp/)
# =============================================================================================

_COL = dict(outline="k", hidden="tab:orange", centerline="tab:blue", annotation="tab:green")


def plot_page(items, path, clip=None, lw=0.4, dpi=150, size=None, tags=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x0, y0, x1, y1 = clip if clip else (0, 0, 2376, 3362)
    w, h = (y1 - y0), (x1 - x0)
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

_STYLE = dict(outline=dict(color="k", lw=0.6, zorder=5), hidden=dict(color="tab:orange", lw=0.5, ls="--", zorder=4),
              centerline=dict(color="tab:blue", lw=0.4, ls="-.", zorder=3),
              annotation=dict(color="tab:green", lw=0.35, zorder=3))

_GLZ_COL = dict(ws="tab:cyan", sw="tab:blue", dv="tab:purple")

VIEW_AXES = dict(side=(0, 2), plan=(0, 1), front=(1, 2), detail_stbd=(0, 2))


def _model_raster(parts, view, lim, px_per_m, select=None, flip=None):
    """Silhouette image of GLB parts projected on a view plane (PIL polygon fill)."""
    from PIL import Image, ImageDraw
    (u0, u1), (v0, v1) = lim
    W = int((u1 - u0) * px_per_m) + 1
    H = int((v1 - v0) * px_per_m) + 1
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    a, b = VIEW_AXES[view]
    for name, meshes in parts.items():
        if select and not select(name):
            continue
        for V, F in meshes:
            if flip is not None:
                keep = flip(V)
                F = F[keep[F].all(1)]
                if not len(F):
                    continue
            U = (V[:, a] - u0) * px_per_m
            Vv = (v1 - V[:, b]) * px_per_m
            T = np.stack([U[F], Vv[F]], -1)
            m = (T[..., 0].max(1) >= 0) & (T[..., 0].min(1) <= W) & (T[..., 1].max(1) >= 0) & (T[..., 1].min(1) <= H)
            for tri in T[m]:
                dr.polygon([tuple(p) for p in tri], fill=255)
    return np.asarray(img)


def _plot_view(ax, lines, glazing=None, openings=None, lim=None, annot=True, lw_scale=1.0):
    for l in lines:
        k = l["kind"]
        if k == "annotation" and not annot:
            continue
        st = dict(_STYLE[k])
        st["lw"] = st["lw"] * lw_scale * (0.6 if l.get("hair") else 1.0)
        P = l["pts"]
        if lim is not None:
            (u0, u1), (v0, v1) = lim
            if P[:, 0].max() < u0 or P[:, 0].min() > u1 or P[:, 1].max() < v0 or P[:, 1].min() > v1:
                continue
        if len(P) == 1:
            ax.plot(P[:, 0], P[:, 1], ".", color=st["color"], ms=1)
        else:
            ax.plot(P[:, 0], P[:, 1], **st)
    for name, P in (glazing or {}).items():
        c = _GLZ_COL.get(name[:2], "tab:red")
        ax.fill(P[:, 0], P[:, 1], color=c, alpha=0.35, zorder=6, lw=0)
        ax.plot(P[:, 0], P[:, 1], color=c, lw=1.2 * lw_scale, zorder=7)
        c0 = P[:-1].mean(0)
        ax.text(c0[0], c0[1], name, color="navy", fontsize=7, ha="center", va="center", zorder=8)
    for name, P in (openings or {}).items():
        ax.plot(P[:, 0], P[:, 1], color="tab:red", lw=0.9, zorder=7)
        c0 = P[:-1].mean(0)
        ax.text(c0[0], c0[1], name.replace("cabin_", ""), color="tab:red", fontsize=6, ha="center", va="center", zorder=8)


def _grid(ax, lim, major, minor):
    from matplotlib.ticker import MultipleLocator
    (u0, u1), (v0, v1) = lim
    ax.set_xlim(u0, u1)
    ax.set_ylim(v0, v1)
    ax.set_aspect("equal")
    ax.xaxis.set_major_locator(MultipleLocator(major)); ax.yaxis.set_major_locator(MultipleLocator(major))
    ax.xaxis.set_minor_locator(MultipleLocator(minor)); ax.yaxis.set_minor_locator(MultipleLocator(minor))
    ax.grid(True, which="major", lw=0.5, color="0.6")
    ax.grid(True, which="minor", lw=0.2, color="0.85")
    ax.tick_params(labelsize=7)


def debug_images(d, outdir=DEBUG_DIR, glb=True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    m = d["meta"]
    parts = None
    if glb:
        try:
            parts = read_glb()
        except Exception as e:
            print("[mbp] no GLB overlay:", e)
    oml = _model_oml()
    written = []

    def model_bg(ax, view, lim, ppm, select=None, flip=None, color=(0.75, 0.85, 1.0), alpha=0.55, label=None):
        if parts is None:
            return
        img = _model_raster(parts, view, lim, ppm, select=select, flip=flip)
        rgba = np.zeros(img.shape + (4,))
        rgba[..., :3] = color
        rgba[..., 3] = (img > 0) * alpha
        (u0, u1), (v0, v1) = lim
        ax.imshow(rgba, extent=(u0, u1, v0, v1), origin="upper", zorder=1, interpolation="nearest")

    notglz = lambda n: not n.startswith("glazing") and n not in ("cabin_interior", "structure", "flight_deck")
    isglz = lambda n: n == "glazing_flightdeck"
    views = [
        ("side", ((-0.2, 15.3), (-0.2, 4.6)), 1.0, 0.1, 200, "side_full.png", dict(flip=None)),
        ("side", ((2.3, 5.0), (1.4, 3.05)), 0.5, 0.05, 1200, "side_cockpit.png", dict(flip=lambda V: V[:, 1] < 0.05)),
        ("plan", ((-0.2, 15.3), (-8.5, 8.5)), 1.0, 0.1, 150, "plan_full.png", dict(flip=None)),
        ("plan", ((2.6, 5.0), (-1.1, 1.1)), 0.5, 0.05, 1200, "plan_cockpit.png", dict(flip=lambda V: V[:, 2] > 1.9)),
        ("front", ((-8.5, 8.5), (-0.2, 4.6)), 1.0, 0.1, 150, "front_full.png", dict(flip=None)),
        ("front", ((-1.2, 1.2), (1.6, 3.3)), 0.5, 0.05, 1200, "front_cockpit.png", dict(flip=lambda V: V[:, 0] < 4.6)),
    ]
    for view, lim, major, minor, ppm, fname, kw in views:
        (u0, u1), (v0, v1) = lim
        w = 16.0
        h = w * (v1 - v0) / (u1 - u0)
        fig = plt.figure(figsize=(w, h + 0.8))
        ax = fig.add_axes([0.04, 0.05, 0.94, 0.88])
        full = fname.endswith("_full.png")
        model_bg(ax, view, lim, ppm, select=notglz, flip=kw["flip"])
        model_bg(ax, view, lim, ppm, select=isglz, flip=kw["flip"], color=(1.0, 0.55, 0.1), alpha=0.35)
        _plot_view(ax, d[view], glazing=d["glazing"].get(view), lim=lim,
                   openings=d["openings"].get(view) if view == "side" else None, annot=True,
                   lw_scale=0.7 if full else 1.3)
        if view == "side" and oml is not None:
            ax.plot(oml["x"], oml["top"], "r--", lw=0.8, zorder=9, label="model crown/keel (model.fuselage)")
            ax.plot(oml["x"], oml["bot"], "r--", lw=0.8, zorder=9)
        if view == "plan" and oml is not None:
            ax.plot(oml["x"], oml["hw"], "r--", lw=0.8, zorder=9, label="model half-breadth")
            ax.plot(oml["x"], -oml["hw"], "r--", lw=0.8, zorder=9)
        for nm, pr in d["profiles"].items():
            if nm.startswith(view):
                ax.plot(pr[:, 0], pr[:, 1], color="magenta", lw=1.0 if not full else 0.6, zorder=8)
        _grid(ax, lim, major, minor)
        ttl = {"side": "SIDE (from port): x [m] / z [m]", "plan": "PLAN (from above): x [m] / y [m] (+ = starboard)",
               "front": "FRONT (from ahead): y [m] (+ = starboard, viewer's left -> plotted mirrored: +y right) / z [m]"}[view]
        ax.set_title(f"Pilatus 190.10.40.432 registered, {ttl}; anchor={m['anchor']}, scale 1:{m['scale_ratio']:.3f}. "
                     "black: drawing outline, blue fill/orange: drawing / model glazing, grey-blue: model (GLB) "
                     "silhouette, red dashed: model OML control lines, magenta: extracted profile", fontsize=8)
        if view == "front":
            ax.invert_xaxis()           # as seen from ahead: starboard on the viewer's left
        fig.savefig(outdir / fname, dpi=110 if full else 150)
        plt.close(fig)
        written.append(outdir / fname)
    # ---- sheet 2 port cabin detail over the sheet 1 side view
    if d.get("detail_port_sheet2"):
        lim = ((4.3, 9.6), (0.6, 3.0))
        fig = plt.figure(figsize=(16, 16 * 2.4 / 5.3 + 0.6))
        ax = fig.add_axes([0.04, 0.06, 0.94, 0.86])
        _plot_view(ax, d["side"], lim=lim, annot=False)
        for l in d["detail_port_sheet2"]:
            if l["kind"] in ("outline", "hidden"):
                ax.plot(l["pts"][:, 0], l["pts"][:, 1], "-", color="tab:orange", lw=0.9, alpha=0.8, zorder=8)
        for n, x in m.get("sheet2", {}).get("frame_stations", {}).items():
            ax.axvline(x, color="tab:purple", lw=0.6, ls=":")
            ax.text(x, 0.65, n, color="tab:purple", fontsize=7, ha="center")
        _grid(ax, lim, 0.5, 0.1)
        s2 = m.get("sheet2", {})
        ax.set_title("sheet 2 port cabin detail (orange) registered onto the sheet 1 side view (black): scale 1:"
                     f"{s2.get('scale_ratio', 0):.3f} from the sections' cabin width, position from the 4 port windows "
                     f"(residuals {s2.get('window_fit_resid_mm')} mm); purple: FR19..FR31", fontsize=8)
        fig.savefig(outdir / "sheet2_detail_on_side.png", dpi=130)
        plt.close(fig)
        written.append(outdir / "sheet2_detail_on_side.png")
    # ---- frame sections vs model sections
    secs = [(n, r) for n, r in d["sections"].items() if r["plane"] == "yz"]
    if secs:
        n = len(secs)
        cols = 5
        rows = (n + cols - 1) // cols
        fig, axs = plt.subplots(rows, cols, figsize=(3.4 * cols, 3.6 * rows))
        for ax, (name, r) in zip(axs.ravel(), secs):
            for l in r["lines"]:
                st = dict(_STYLE[l["kind"]])
                ax.plot(l["pts"][:, 0], l["pts"][:, 1], **st)
            if oml is not None:
                from model import fuselage as F
                xs_ = [r["x"]] if r["x"] is not None else list(np.linspace(*r["x_range"], 3))
                for x in xs_:
                    if 0.95 <= x <= 14.36:
                        t = np.linspace(0, 1, 361)
                        S = F.section(np.full_like(t, x), t)
                        ax.plot(S[:, 1], S[:, 2], "r--", lw=0.8)
            ax.set_title(f"{name}  x={r['x']:.3f}" if r["x"] is not None else f"{name} x={r['x_range'][0]:.2f}..{r['x_range'][1]:.2f}", fontsize=8)
            ax.set_aspect("equal")
            ax.grid(True, lw=0.3)
            ax.tick_params(labelsize=6)
            ax.invert_xaxis()
        for ax in axs.ravel()[n:]:
            ax.axis("off")
        fig.suptitle("Frame sections (drawing black, model.fuselage.section red dashed); y (+stbd, plotted as seen from "
                     "ahead) / z [m]", fontsize=9)
        fig.tight_layout()
        fig.savefig(outdir / "sections_frames.png", dpi=130)
        plt.close(fig)
        written.append(outdir / "sections_frames.png")
    # ---- airfoil sections
    secs = [(n, r) for n, r in d["sections"].items() if r["plane"] in ("xy", "xz")]
    if secs:
        fig, axs = plt.subplots(len(secs), 1, figsize=(12, 1.6 * len(secs)))
        for ax, (name, r) in zip(np.atleast_1d(axs), secs):
            for l in r["lines"]:
                st = dict(_STYLE[l["kind"]])
                ax.plot(l["pts"][:, 0], l["pts"][:, 1], **st)
            ax.set_aspect("equal")
            ax.grid(True, lw=0.3)
            ax.tick_params(labelsize=6)
            ax.set_title(f"{name}: plane {r['plane']} at {r['plane'][0] if r['plane']=='yz' else ('z' if r['plane']=='xy' else 'y')}"
                         f" = {r['const']:.3f}  ({r['registration']})", fontsize=7)
        fig.tight_layout()
        fig.savefig(outdir / "sections_airfoils.png", dpi=120)
        plt.close(fig)
        written.append(outdir / "sections_airfoils.png")
    return written


def page_images(P, outdir=DEBUG_DIR):
    """Page-coordinate debug plots: classification (kind/tag colours) and view separation."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    plot_page(P["items"], outdir / "page8_kinds.png", tags=True, dpi=110)
    if P.get("page9") and "items" in P["page9"]:
        plot_page(P["page9"]["items"], outdir / "page9_kinds.png", tags=True, dpi=110)
    items = P["items"]
    names = sorted(set(it["view"] for it in items))
    cyc = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    col = {n: ("0.75" if n == "sheet" else cyc[k % len(cyc)]) for k, n in enumerate(names)}
    fig = plt.figure(figsize=(16, 11.3))
    ax = fig.add_axes([0.03, 0.03, 0.95, 0.95])
    for it in items:
        Q = it["pts"]
        ax.plot(Q[:, 1], Q[:, 0], "-", lw=0.3, color=col[it["view"]])
    for n in names:
        A = np.vstack([it["pts"] for it in items if it["view"] == n])
        c = np.median(A, axis=0)
        ax.text(c[1], c[0], n, fontsize=7, color=col[n], ha="center")
    ax.set_xlim(P["page_size"][1], 0)
    ax.set_ylim(P["page_size"][0], 0)
    ax.set_aspect("equal")
    ax.set_title("sheet 1 (page index 8): view separation, page pt (x down, y left; sheet read with nose left)", fontsize=8)
    fig.savefig(outdir / "page8_views.png", dpi=110)
    plt.close(fig)
    return [outdir / "page8_kinds.png", outdir / "page8_views.png", outdir / "page9_kinds.png"]


# =============================================================================================
# 15. Blender (optional): Cycles orthographic renders of out/pc12.glb for overlays
# =============================================================================================

BLENDER_PY = "/opt/venv-blender/bin/python"          # Blender 5 as a Python module (separate venv)

_BLENDER_SCRIPT = r'''
import bpy, sys, json, math, time
args = json.loads(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args["glb"])
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = int(args.get("spp", 16))
try:
    sc.cycles.use_denoising = False
except Exception:
    pass
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 0.9
for rot, e in (((math.radians(35), 0, math.radians(-30)), 3.0), ((math.radians(-60), 0, math.radians(150)), 1.2)):
    ld = bpy.data.lights.new("sun", "SUN"); ld.energy = e
    lo = bpy.data.objects.new("sun", ld); lo.rotation_euler = rot; sc.collection.objects.link(lo)
for o in bpy.data.objects:                 # hide cutaway-only parts (interior, structure)
    n = o.name.split("#")[0]
    if n in args.get("hide", []):
        o.hide_render = True
EUL = {"side": (90, 0, -90), "plan": (0, 0, -90), "front": (90, 0, 180)}
out = {}
for v in args["views"]:
    cd = bpy.data.cameras.new(v["name"]); cd.type = "ORTHO"; cd.ortho_scale = v["ortho"]; cd.clip_end = 200
    co = bpy.data.objects.new(v["name"], cd); sc.collection.objects.link(co)
    xc, yc, zc = v["centre"]                     # MODEL coordinates of the image centre
    loc = {"side": (-40.0, -xc, zc), "plan": (yc, -xc, 40.0), "front": (yc, 40.0, zc)}[v["kind"]]
    co.location = loc
    co.rotation_euler = tuple(math.radians(a) for a in EUL[v["kind"]])
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = v["res"]
    sc.render.resolution_percentage = 100
    sc.render.filepath = v["path"]
    t = time.time()
    bpy.ops.render.render(write_still=True)
    out[v["name"]] = dict(path=v["path"], seconds=time.time() - t)
print("BLENDER_RESULT " + json.dumps(out))
'''


def blender_render(views, glb=None, spp=16, hide=("cabin_interior", "structure", "flight_deck"), timeout=1800):
    """Render orthographic views of the GLB with Blender/Cycles (CPU) in the separate venv.
    views: list of dict(name, kind in side|plan|front, lim=((u0,u1),(v0,v1)) in the view's model axes,
    px_per_m).  Returns {name: dict(path, extent (matplotlib imshow extent in model axes))}."""
    import subprocess
    glb = str(glb or ROOT / "out" / "pc12.glb")
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    spec, res = [], {}
    for v in views:
        (u0, u1), (w0, w1) = v["lim"]
        W = int(round((u1 - u0) * v["px_per_m"])); H = int(round((w1 - w0) * v["px_per_m"]))
        uc, wc = 0.5 * (u0 + u1), 0.5 * (w0 + w1)
        if v["kind"] == "side":
            centre = (uc, 0.0, wc)
        elif v["kind"] == "plan":
            centre = (uc, wc, 0.0)
        else:
            centre = (0.0, uc, wc)
        path = str(DEBUG_DIR / f"blender_{v['name']}.png")
        spec.append(dict(name=v["name"], kind=v["kind"], centre=centre, ortho=max(u1 - u0, w1 - w0), res=(W, H), path=path))
        ps = max(u1 - u0, w1 - w0) / max(W, H)
        hw, hh = W * ps / 2, H * ps / 2
        ext = (uc - hw, uc + hw, wc - hh, wc + hh)
        if v["kind"] == "front":                 # image right = port (-y)
            ext = (uc + hw, uc - hw, wc - hh, wc + hh)
        res[v["name"]] = dict(path=path, extent=ext, kind=v["kind"])
    args = json.dumps(dict(glb=glb, views=spec, spp=spp, hide=list(hide)))
    p = subprocess.run([BLENDER_PY, "-c", _BLENDER_SCRIPT, "--", args], capture_output=True, text=True, timeout=timeout)
    line = [l for l in p.stdout.splitlines() if l.startswith("BLENDER_RESULT ")]
    if p.returncode != 0 or not line:
        raise RuntimeError("blender render failed:\n" + p.stdout[-2000:] + p.stderr[-2000:])
    info = json.loads(line[-1][len("BLENDER_RESULT "):])
    for k, v in info.items():
        res[k]["seconds"] = v["seconds"]
    return res


def blender_overlays(d, spp=16):
    """Blender/Cycles renders of the model with the registered Pilatus drawing drawn on top."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    views = [dict(name="side", kind="side", lim=((-0.3, 15.3), (-0.3, 4.7)), px_per_m=160),
             dict(name="side_cockpit", kind="side", lim=((2.3, 5.0), (1.4, 3.05)), px_per_m=800),
             dict(name="plan_cockpit", kind="plan", lim=((2.6, 5.0), (-1.1, 1.1)), px_per_m=800),
             dict(name="front_cockpit", kind="front", lim=((-1.2, 1.2), (1.6, 3.3)), px_per_m=800),
             dict(name="front", kind="front", lim=((-8.6, 8.6), (-0.3, 4.7)), px_per_m=140)]
    R = blender_render(views, spp=spp)
    written = []
    for v in views:
        r = R[v["name"]]
        img = np.asarray(Image.open(r["path"]))
        key = v["kind"]
        (u0, u1), (w0, w1) = v["lim"]
        full = v["name"] in ("side", "front")
        fig = plt.figure(figsize=(16, 16 * (w1 - w0) / (u1 - u0) + 0.6))
        ax = fig.add_axes([0.04, 0.05, 0.94, 0.88])
        ax.imshow(img, extent=r["extent"], origin="upper", zorder=1, interpolation="bilinear")
        _plot_view(ax, d[key], glazing=d["glazing"].get(key), lim=v["lim"], annot=False, lw_scale=0.7 if full else 1.2,
                   openings=d["openings"].get(key) if key == "side" else None)
        _grid(ax, v["lim"], 1.0 if full else 0.5, 0.1 if full else 0.05)
        if key == "front":
            ax.invert_xaxis()
        ax.set_title(f"Blender/Cycles render of out/pc12.glb ({spp} spp, {r['seconds']:.0f} s) + registered Pilatus "
                     f"190.10.40.432 ({key}, anchor={d['meta']['anchor']}); coloured fills = drawing glazing", fontsize=8)
        fn = DEBUG_DIR / f"blender_overlay_{v['name']}.png"
        fig.savefig(fn, dpi=130)
        plt.close(fig)
        written.append(fn)
    return written


# =============================================================================================
# 16. command line
# =============================================================================================


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m refs.mbp", description=__doc__.split("\n")[1])
    ap.add_argument("--anchor", default="spinner", choices=ANCHORS, help="side/plan x anchor (default spinner)")
    ap.add_argument("--front-z", default="ground", choices=("ground", "prop"), help="front-view z datum")
    ap.add_argument("--force", action="store_true", help="re-extract (ignore refs/cache/)")
    ap.add_argument("--no-images", action="store_true", help="skip the debug images")
    ap.add_argument("--no-glb", action="store_true", help="debug images without the out/pc12.glb silhouette")
    ap.add_argument("--blender", action="store_true", help="also render Blender/Cycles overlays (~2-4 min)")
    ap.add_argument("--spp", type=int, default=16, help="Cycles samples for --blender")
    a = ap.parse_args(argv)
    t0 = time.time()
    d = load(anchor=a.anchor, front_z=a.front_z, force=a.force)
    report(d)
    print(f"\n[mbp] registered in {time.time() - t0:.1f} s (cache: {_cache_file(d['meta']['sha256']).name})")
    if not a.no_images:
        w = debug_images(d, glb=not a.no_glb) + page_images(processed())
        print("[mbp] debug images:", ", ".join(str(p.relative_to(ROOT)) for p in w if Path(p).exists()))
    if a.blender:
        w = blender_overlays(d, spp=a.spp)
        print("[mbp] blender overlays:", ", ".join(str(p.relative_to(ROOT)) for p in w))


if __name__ == "__main__":
    main()
