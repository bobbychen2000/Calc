"""
Fuselage lines: reference extraction, deviation metrics and the least-squares knot fit.

    python3 -m drawing.lines_fit            # deviations of the current model/fuselage.py vs the drawing
    python3 -m drawing.lines_fit fit        # least-squares refit of the knot values -> prints new tables

The reference is the registered Pilatus drawing (refs/mbp.py, data in the git-ignored refs/cache/).
Only OUR numbers (knot values, deviations) leave this module; the Pilatus polylines are used for
the fit and for the overlay variant of sheet L1 only.

What is fitted (model/fuselage.py control lines, pchip knots at fixed stations):
  crown z_top(x)       side-view crown line x 1.05..9.00; aft of FR33 the frame sections and the
                       dorsal-fin root line (side-view line at the plan-view fin-fillet half-width)
  keel z_bot(x)        side-view keel where the fuselage bottom is visible (not behind the wing-root
                       fairing / main gear, not behind the ventral strake), frame sections; the drawn
                       lower silhouette is a one-sided bound (the fuselage may not protrude below it)
  half_w(x)            plan-view half-breadth 1.05..13.0 (strake tips x 11.65..11.95 ignored)
  z_mw, n/m exponents  frame sections EF1..FR40 (sheet 1, weight 1; sheet-2 phantom cabin section, low
                       weight); EF1 only its upper (cowling) part, the chin-inlet crescent is not OML
Excluded features (reported): chin-inlet crescent (EF1), dorsal fin, ventral strakes, the ventral lobe
under the tail cone (FR40 and the lower silhouette aft of x 11.9), wing-root fairing (sheet-2 sections).
"""
from __future__ import annotations

import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import fuselage as F  # noqa: E402

LINES = F.OML.LINES
LEN_LINES = ("crown", "keel", "half_breadth", "max_breadth_wl")

# ----------------------------------------------------------------------------------------------
# fit specification: fixed knots and tied knots (same value) per control line
# ----------------------------------------------------------------------------------------------
X0, X1 = F.STA["cowl_front"], F.STA["tail_end"]
FIXED = {  # line -> stations whose value is held (spinner concentric at the cowl front, closed tail end)
    "crown": (X0, X1), "keel": (X0, X1), "half_breadth": (X0, X1), "max_breadth_wl": (X0,),
    "n_top": (X0, X1), "m_top": (X0, X1), "n_bot": (X0, X1), "m_bot": (X0, X1),
}
TIES = {  # constant cabin section
    "crown": (4.40, 9.00), "keel": (2.85, 8.20), "half_breadth": (4.60, 9.00), "max_breadth_wl": (4.60, 8.20),
    "n_top": (4.60, 8.20), "m_top": (4.60, 8.20), "n_bot": (4.60, 8.20), "m_bot": (4.60, 8.20),
}
BOUNDS_EXP = (1.4, 7.0)

# section list: name -> (station(s), weight, selector)
SHEET1_SECTIONS = ("EF1", "EF2", "FR10", "FR12", "FR14", "FR16-30", "FR33", "FR36", "FR38", "FR40")
SHEET2_SECTIONS = ("FR19", "FR21", "FR23", "FR25", "FR27", "FR29", "FR31")
STRAKE_TIPS = (11.65, 11.95)


# the previous model (rev A, before the Stage-2 refit; single super-ellipse exponent n = m), for comparisons
REV_A_TABLES = dict(
    crown=[(0.95, 1.945), (1.20, 1.985), (1.60, 2.035), (2.20, 2.100), (2.80, 2.160), (3.30, 2.215), (3.50, 2.352),
           (3.70, 2.478), (3.90, 2.576), (4.10, 2.620), (4.40, 2.630), (9.90, 2.630), (10.50, 2.605), (11.20, 2.530),
           (11.90, 2.440), (12.60, 2.345), (13.30, 2.260), (13.90, 2.195), (14.36, 2.140)],
    keel=[(0.95, 1.365), (1.20, 1.315), (1.60, 1.225), (2.00, 1.140), (2.60, 1.020), (3.00, 0.945), (3.50, 0.855),
          (4.00, 0.812), (4.40, 0.800), (8.80, 0.800), (9.40, 0.838), (10.00, 0.925), (10.80, 1.095), (11.60, 1.310),
          (12.40, 1.540), (13.20, 1.770), (13.90, 1.945), (14.36, 2.045)],
    half_breadth=[(0.95, 0.29), (1.20, 0.370), (1.60, 0.462), (2.20, 0.580), (2.80, 0.680), (3.30, 0.752),
                  (3.80, 0.812), (4.40, 0.842), (5.00, 0.845), (9.40, 0.845), (10.00, 0.830), (10.80, 0.765),
                  (11.60, 0.650), (12.40, 0.505), (13.20, 0.345), (13.90, 0.195), (14.36, 0.045)],
    max_breadth_wl=[(0.95, 1.655), (2.00, 1.662), (3.00, 1.700), (4.40, 1.780), (9.80, 1.780), (11.00, 1.860),
                    (12.20, 1.960), (13.40, 2.040), (14.36, 2.092)],
    n_top=[(0.95, 2.0), (2.00, 2.12), (3.00, 2.34), (3.80, 2.38), (4.60, 2.24), (9.80, 2.20), (12.5, 2.05),
           (14.36, 2.0)],
    n_bot=[(0.95, 2.0), (2.00, 2.18), (4.00, 2.45), (9.00, 2.45), (12.0, 2.25), (14.36, 2.0)],
)
REV_A_TABLES["m_top"], REV_A_TABLES["m_bot"] = REV_A_TABLES["n_top"], REV_A_TABLES["n_bot"]


def rev_a_oml():
    return F.OML(REV_A_TABLES)


# ----------------------------------------------------------------------------------------------
# reference data
# ----------------------------------------------------------------------------------------------
def _crossings(items, x, lo, hi):
    out = []
    for it in items:
        p = it["pts"]
        a, b = p[:-1], p[1:]
        k = np.where((np.minimum(a[:, 0], b[:, 0]) <= x) & (np.maximum(a[:, 0], b[:, 0]) >= x) & (a[:, 0] != b[:, 0]))[0]
        for i in k:
            t = (x - a[i, 0]) / (b[i, 0] - a[i, 0])
            v = a[i, 1] + t * (b[i, 1] - a[i, 1])
            if lo < v < hi:
                out.append(v)
    return np.array(sorted(out))


def _track(items, xs, seed, tol):
    out = np.full(len(xs), np.nan)
    for i, x in enumerate(xs):
        c = _crossings(items, x, -10, 10)
        if len(c):
            j = np.argmin(np.abs(c - seed(x)))
            if abs(c[j] - seed(x)) < tol:
                out[i] = c[j]
    return out


def _slope_cos(x, v):
    g = np.gradient(v, x)
    return 1.0 / np.sqrt(1.0 + g ** 2)


@lru_cache(maxsize=1)
def reference():
    """Fuselage reference data in model coordinates (from the registered Pilatus drawing)."""
    from refs import mbp
    d = mbp.load()
    pr = d["profiles"]
    R = {}
    # --- side crown
    c = pr["side_crown"]
    c = c[np.isfinite(c[:, 1]) & (c[:, 0] >= X0 + 0.012) & (c[:, 0] <= 9.0)]
    R["crown"] = dict(x=c[:, 0], v=c[:, 1], cos=_slope_cos(c[:, 0], c[:, 1]))
    # --- side keel (visible fuselage bottom only)
    k = pr["side_keel"]
    k = k[np.isfinite(k[:, 1]) & (k[:, 0] >= X0 + 0.012) & (k[:, 0] <= 11.90)]
    R["keel"] = dict(x=k[:, 0], v=k[:, 1], cos=_slope_cos(k[:, 0], k[:, 1]))
    # lower silhouette (one-sided bound) where it is NOT the keel: fairing, strake, ventral lobe
    b = pr["side_bottom"]
    b = b[np.isfinite(b[:, 1]) & (b[:, 0] >= 10.70) & (b[:, 0] <= X1 - 0.01)]
    R["lower_sil"] = dict(x=b[:, 0], v=b[:, 1])
    # --- plan half-breadth (mean of both sides), strake tips out
    s, p = pr["plan_hb_stbd"], pr["plan_hb_port"]
    hb = np.nanmean(np.c_[s[:, 1], -p[:, 1]], axis=1)
    m = np.isfinite(hb) & (s[:, 0] >= X0 + 0.012) & (s[:, 0] <= 13.0) & \
        ~((s[:, 0] > STRAKE_TIPS[0]) & (s[:, 0] < STRAKE_TIPS[1]))
    R["half_breadth"] = dict(x=s[m, 0], v=hb[m], cos=_slope_cos(s[m, 0], hb[m]))
    # --- dorsal-fin root line: side-view line (x, z) at the plan-view fin-fillet half-width y
    xs = np.arange(9.25, 12.46, 0.02)
    side_ol = [it for it in d["side"] if it["kind"] == "outline"]
    plan_ol = [it for it in d["plan"] if it["kind"] == "outline"]
    zl = _track(side_ol, xs, lambda x: np.interp(x, [9.0, 9.75, 10.8, 11.85, 12.4], [2.77, 2.74, 2.663, 2.544, 2.44]),
                0.02)
    yd = _track(plan_ol, xs, lambda x: np.interp(x, [9.0, 9.75, 10.8, 11.85, 12.3], [0.03, 0.142, 0.2175, 0.239, 0.252]),
                0.02)
    ok = np.isfinite(zl) & np.isfinite(yd)
    R["fin_root"] = dict(x=xs[ok], y=yd[ok], z=zl[ok])
    # --- sections
    secs = {}
    for name in SHEET1_SECTIONS:
        S = d["sections"][name]
        L = [ln["pts"] for ln in S["lines"] if ln["kind"] == "outline" and len(ln["pts"]) >= 60]
        if name == "EF1":       # cowling circle only (upper part); the chin-inlet crescent is not OML
            P = np.concatenate([q for q in L if q[:, 1].max() > 1.9])
            P = P[P[:, 1] > 1.55]
            w, note = 0.5, "cowling ring only (z > 1.55); chin-inlet crescent excluded"
        elif name in ("FR36", "FR40"):
            P = max(L, key=len)
            w, note = 1.0, "fuselage outline only (dorsal fin, strakes, ventral lobe excluded)"
        elif name == "FR38":
            P = [q for q in L if np.ptp(q[:, 0]) > 1.0][0]
            w, note = 1.0, "fuselage outline only (dorsal fin, strakes excluded)"
        else:
            P = max(L, key=len)
            w, note = 1.0, ""
        if name == "FR16-30":
            lo, hi = S["x_range"]
            xs_ = np.round(np.linspace(float(lo), float(hi), 5), 3)
            w = 0.4
        else:
            xs_ = np.array([round(float(S["x"]), 3)])
        secs[name] = dict(xs=xs_, pts=P, w=w, sheet=1, note=note)
    for name in SHEET2_SECTIONS:
        S = d["sections"][name]
        P = np.concatenate([ln["pts"] for ln in S["lines"] if ln.get("tag") == "phantom"])
        secs[name] = dict(xs=np.array([round(float(S["x"]), 3)]), pts=P, w=0.25, sheet=2,
                          note="sheet 2 phantom (cabin section below WL 2.11), low weight")
    R["sections"] = secs
    return R


# ----------------------------------------------------------------------------------------------
# deviations (normal distances, our numbers)
# ----------------------------------------------------------------------------------------------
def _curve_dist(xd, vd, fn, x0, x1, step=0.001):
    from scipy.spatial import cKDTree
    xs = np.arange(x0, x1 + step / 2, step)
    T = cKDTree(np.c_[xs, fn(xs)])
    dist, _ = T.query(np.c_[xd, vd])
    sgn = np.sign(fn(np.clip(xd, x0, x1)) - vd)
    return dist * np.where(sgn == 0, 1, sgn)


def section_polyline(oml, x, n=7200):
    t = np.linspace(0, 1, n + 1)
    P = oml.section(np.full_like(t, x), t)
    return P[:, 1:]


def _section_dev(oml, x, P):
    from scipy.spatial import cKDTree
    C = section_polyline(oml, x)
    dist, _ = cKDTree(C).query(P)
    # sign: + if the drawn point lies inside ours (we are too big)
    sd = oml.section_distance(np.full(len(P), x), P[:, 0], P[:, 1])
    return dist * np.where(sd < 0, 1, -1)


def deviations(oml=None):
    """Signed normal deviations ours - drawing (m; + = our line outside / above the drawn one)."""
    oml = oml or F._OML
    R = reference()
    out = {}
    x0, x1 = oml.x0, oml.x1
    for key, fn in (("crown", oml.z_top), ("keel", oml.z_bot), ("half_breadth", oml.half_w)):
        r = R[key]
        dev = _curve_dist(r["x"], r["v"], fn, x0, x1)
        if key == "keel":
            dev = -dev                       # + = our keel below the drawn keel (outside)
        out[key] = dict(x=r["x"], dev=dev)
    fr = R["fin_root"]
    zz = oml.z_at(fr["x"], fr["y"], True)
    out["fin_root"] = dict(x=fr["x"], dev=(zz - fr["z"]) * _slope_cos(fr["x"], fr["z"]))
    ls = R["lower_sil"]
    out["lower_sil"] = dict(x=ls["x"], dev=ls["v"] - oml.z_bot(ls["x"]))  # > 0: we protrude below it
    sec = {}
    for name, S in R["sections"].items():
        devs = [_section_dev(oml, x, S["pts"]) for x in S["xs"]]
        worst = max(devs, key=lambda d: np.abs(d).max())
        sec[name] = dict(xs=S["xs"], dev=worst, pts=S["pts"], sheet=S["sheet"], note=S["note"])
    out["sections"] = sec
    return out


def stats(dev):
    a = np.abs(dev)
    return float(np.sqrt(np.mean(dev ** 2))), float(a.max()), int(np.argmax(a))


def summary(oml=None, file=sys.stdout):
    D = deviations(oml)
    rows = []
    for key in ("crown", "keel", "half_breadth", "fin_root"):
        rms, mx, k = stats(D[key]["dev"])
        rows.append((key, len(D[key]["dev"]), rms, mx, f"x={D[key]['x'][k]:.3f} dev={D[key]['dev'][k]*1000:+.1f}"))
    for name, S in D["sections"].items():
        rms, mx, k = stats(S["dev"])
        P = S["pts"][k]
        rows.append((f"{name} @{S['xs'][0]:.3f}" + ("..%.3f" % S["xs"][-1] if len(S["xs"]) > 1 else ""),
                     len(S["dev"]), rms, mx, f"y={P[0]:+.3f} z={P[1]:.3f} dev={S['dev'][k]*1000:+.1f}"))
    ls = D["lower_sil"]
    print(f"{'dataset':24s} {'n':>5s} {'rms mm':>7s} {'max mm':>7s}  worst", file=file)
    for r in rows:
        print(f"{r[0]:24s} {r[1]:5d} {r[2]*1000:7.1f} {r[3]*1000:7.1f}  {r[4]}", file=file)
    print(f"lower silhouette: max protrusion below it {max(ls['dev'].max(), 0)*1000:.1f} mm "
          f"at x={ls['x'][np.argmax(ls['dev'])]:.3f}", file=file)
    return D


# ----------------------------------------------------------------------------------------------
# the fit
# ----------------------------------------------------------------------------------------------
class Packing:
    """Knot tables <-> free parameter vector (fixed knots held, tied knots share one parameter)."""

    def __init__(self, tables):
        self.tables = {k: [list(p) for p in tables[k]] for k in LINES}
        self.slots = []                                # (line, [knot indices]) per parameter
        for k in LINES:
            xs = [p[0] for p in self.tables[k]]
            fixed = {i for i, x in enumerate(xs) if any(abs(x - f) < 1e-9 for f in FIXED.get(k, ()))}
            tie = TIES.get(k)
            tied = [i for i, x in enumerate(xs) if tie and any(abs(x - t) < 1e-9 for t in tie)]
            done = set(fixed)
            if tied:
                self.slots.append((k, tied))
                done |= set(tied)
            for i in range(len(xs)):
                if i not in done:
                    self.slots.append((k, [i]))

    def vector(self):
        return np.array([self.tables[k][ix[0]][1] for k, ix in self.slots])

    def bounds(self):
        lo, hi = [], []
        for k, ix in self.slots:
            v = self.tables[k][ix[0]][1]
            if k in LEN_LINES:
                lo.append(0.02 if k == "half_breadth" else v - 0.4)
                hi.append(v + 0.4)
            else:
                lo.append(BOUNDS_EXP[0])
                hi.append(BOUNDS_EXP[1])
        return np.array(lo), np.array(hi)

    def unpack(self, p):
        T = {k: [list(q) for q in self.tables[k]] for k in LINES}
        for (k, ix), v in zip(self.slots, p):
            for i in ix:
                T[k][i][1] = float(v)
        return T


def residuals(oml, tables, R, w_reg=1.0):
    res = []
    for key, fn, sgn in (("crown", oml.z_top, 1), ("keel", oml.z_bot, 1), ("half_breadth", oml.half_w, 1)):
        r = R[key]
        res.append((fn(r["x"]) - r["v"]) * r["cos"])
    fr = R["fin_root"]
    res.append(0.7 * (oml.z_at(fr["x"], fr["y"], True) - fr["z"]))
    ls = R["lower_sil"]
    res.append(3.0 * np.maximum(ls["v"] - 0.003 - oml.z_bot(ls["x"]), 0.0))
    for name, S in R["sections"].items():
        w = S["w"]
        P = S["pts"]
        for x in S["xs"]:
            res.append(w * oml.section_distance(np.full(len(P), x), P[:, 0], P[:, 1]))
    # ordering sanity: z_top > z_mw + 0.03 > z_bot + 0.06
    xs = np.linspace(oml.x0, oml.x1, 200)
    res.append(10 * np.maximum(oml.z_mw(xs) + 0.03 - oml.z_top(xs), 0))
    res.append(10 * np.maximum(oml.z_bot(xs) + 0.03 - oml.z_mw(xs), 0))
    # smoothness: change of slope between knot intervals
    for k in LINES:
        T = np.array(tables[k])
        if len(T) < 3:
            continue
        s = np.diff(T[:, 1]) / np.diff(T[:, 0])
        lam = 0.004 if k in LEN_LINES else 0.02
        res.append(w_reg * lam * np.diff(s))
    return np.concatenate(res)


def fit(tables=None, verbose=True, max_nfev=60, w_reg=1.0):
    from scipy.optimize import least_squares
    tables = tables or F.CONTROL_LINES
    R = reference()
    pk = Packing(tables)
    p0 = pk.vector()
    lo, hi = pk.bounds()
    p0 = np.clip(p0, lo + 1e-9, hi - 1e-9)

    def fun(p):
        T = pk.unpack(p)
        return residuals(F.OML(T), T, R, w_reg)

    t0 = time.time()
    r0 = fun(p0)
    sol = least_squares(fun, p0, bounds=(lo, hi), x_scale="jac", max_nfev=max_nfev, verbose=0)
    if verbose:
        print(f"fit: {len(p0)} parameters, {len(r0)} residuals, cost {0.5 * r0 @ r0:.3e} -> {sol.cost:.3e} "
              f"({sol.nfev} evaluations, {time.time() - t0:.1f}s)")
    return pk.unpack(sol.x), sol


def _wrap(head, items, indent, width=118):
    out, cur = [], head
    for i, it in enumerate(items):
        piece = it + (", " if i < len(items) - 1 else "")
        if len(cur) + len(piece.rstrip()) > width:
            out.append(cur.rstrip())
            cur = " " * indent
        cur += piece
    out.append(cur)
    return out


def format_tables(T):
    """Python source for the knot tables (the <fitted-tables> block of model/fuselage.py)."""
    def fx(x):
        if abs(x - X0) < 1e-9:
            return "_X0"
        if abs(x - X1) < 1e-9:
            return "_X1"
        return f"{x:.3f}"
    lines = []
    for var, key in (("_top", "crown"), ("_bot", "keel"), ("_hw", "half_breadth"), ("_zmw", "max_breadth_wl")):
        items = [f"({fx(x)}, {v:.3f})" for x, v in T[key]]
        items[-1] += "]"
        lines += _wrap(f"{var} = [", items, len(var) + 4)
    lines.append("# section-law exponents: n = crown/keel flatness, m = side flatness (upper / lower half)")
    items = [fx(x) for x, _ in T["n_top"]]
    items[-1] += "]"
    lines += _wrap("_XN = [", items, 7)
    for var, key in (("_ntop", "n_top"), ("_mtop", "m_top"), ("_nbot", "n_bot"), ("_mbot", "m_bot")):
        items = [f"{v:.2f}" for _, v in T[key]]
        items[-1] += "]))"
        lines += _wrap(f"{var} = list(zip(_XN, [", items, 21)
    return "\n".join(lines)


def write_tables(T, path=None):
    """Replace the <fitted-tables> block of model/fuselage.py with the tables T."""
    path = Path(path or Path(__file__).resolve().parents[1] / "model" / "fuselage.py")
    s = path.read_text()
    a = s.index("# <fitted-tables>")
    a = s.index("\n", a) + 1
    b = s.index("# </fitted-tables>")
    path.write_text(s[:a] + format_tables(T) + "\n" + s[b:])
    print(f"wrote the knot tables into {path}")


def main(argv=None):
    """python3 -m drawing.lines_fit [fit [NFEV] [--write]] | [write]  (write = last fit from out/tmp)"""
    import json
    argv = sys.argv[1:] if argv is None else argv
    js = Path(__file__).resolve().parents[1] / "out" / "tmp" / "lines_fit_tables.json"
    if argv and argv[0] == "fit":
        n = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 60
        print("before:")
        summary()
        T, sol = fit(max_nfev=n)
        print("after:")
        summary(F.OML(T))
        print(format_tables(T))
        js.parent.mkdir(parents=True, exist_ok=True)
        js.write_text(json.dumps(T))
        if "--write" in argv:
            write_tables(T)
    elif argv and argv[0] == "write":
        write_tables(json.loads(js.read_text()))
    else:
        summary()


if __name__ == "__main__":
    main()
