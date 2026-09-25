"""
Wing aerofoils: reference extraction, shape deviations and the least-squares CST fit.

    python3 -m drawing.airfoil_fit            # shape deviations of model/airfoil.py (and of rev A) vs WR1-WR4
    python3 -m drawing.airfoil_fit fit [N]    # joint least-squares refit (CST order N, default 5) -> new tables

The reference is the registered Pilatus drawing (refs/mbp.py, data in the git-ignored refs/cache/): its wing
sections WR1 (BL 900), WR2 (5557), WR3 (6658) and WR4 (7395).  Only OUR numbers (CST coefficients, deviations in
mm) leave this module.

Shape only: every drawn section is normalised by its own leading edge (the outline point farthest from the
trailing edge) and trailing edge (the aft-most point) -- this removes the section's registration error (WR1 sits
~83 mm / ~410 mm off in x / z on the sheet) and its incidence, which the twist table fits separately.  Our
section at the same butt line is model.wing.airfoil_at(y) in the same chord frame (LE (0, 0), TE (1, 0)).

What is fitted: the root (LS(1)-0417MOD) and tip (LS(1)-0313) CST coefficient sets TOGETHER, each drawn section
entering as the linear span blend wing.airfoil_at uses ((1 - w) root + w tip) -- CST is linear in its
coefficients, so the whole fit is one weighted linear least-squares problem (weights = local chord, i.e. mm).
Upper / lower surfaces are the outline envelope (max / min) at cosine-spaced chord stations; the aileron gap
of WR3 (62.5-72 % c, where the envelope would follow the aileron nose) is excluded.
"""
from __future__ import annotations

import sys
from math import comb
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import airfoil as AF  # noqa: E402
from model import wing as W  # noqa: E402

SECTIONS = ("WR1", "WR2", "WR3", "WR4")
EXCLUDE = {"WR3": ((0.625, 0.72),)}          # aileron gap (the envelope would follow the aileron nose)


def _densify(P, step=0.002):
    P = np.asarray(P, float)
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        k = max(1, int(np.linalg.norm(b - a) / step))
        out.append(a + (b - a) * (np.arange(1, k + 1) / k)[:, None])
    return np.vstack(out)


def drawn_sections(d=None):
    """{name: dict(y, chord, inc_deg, pts=[(N, 2) normalised outline polylines], cloud=(M, 2))} of the drawn
    wing sections in their own chord frame (LE (0, 0), TE (1, 0), + up)."""
    if d is None:
        from drawing.master import mbp_data
        d = mbp_data()
    out = {}
    for n in SECTIONS:
        s = d["sections"][n]
        lines = [np.asarray(ln["pts"], float) for ln in s["lines"] if ln["kind"] == "outline"]
        P = np.vstack([_densify(L) for L in lines])
        te = P[np.argmax(P[:, 0])]
        le = P[np.argmax(np.linalg.norm(P - te, axis=1))]
        c = float(np.linalg.norm(te - le))
        e = (te - le) / c
        nrm = np.array([-e[1], e[0]])

        def norm(Q):
            return np.stack([(Q - le) @ e / c, (Q - le) @ nrm / c], 1)

        out[n] = dict(y=float(s["const"]), chord=c, inc_deg=float(np.degrees(np.arctan2(-e[1], e[0]))),
                      pts=[norm(_densify(L)) for L in lines], cloud=norm(P))
    return out


def envelope(Q, xs):
    """Upper / lower envelope of a normalised point cloud at chord stations xs (NaN where empty)."""
    up = np.full(len(xs), np.nan)
    lo = np.full(len(xs), np.nan)
    for i, x in enumerate(xs):
        if x < 0.004:
            continue
        m = np.abs(Q[:, 0] - x) < min(0.0035, 0.25 * x)
        if m.any():
            up[i], lo[i] = Q[m, 1].max(), Q[m, 1].min()
    return up, lo


def _seg_dist(P, Q):
    A, B = Q[:-1], Q[1:]
    AB = B - A
    L2 = (AB ** 2).sum(1) + 1e-18
    out = np.empty(len(P))
    for i0 in range(0, len(P), 2000):
        p = P[i0:i0 + 2000, None, :]
        t = np.clip(((p - A) * AB).sum(-1) / L2, 0, 1)
        out[i0:i0 + 2000] = np.linalg.norm(p - (A + t[..., None] * AB), axis=-1).min(1)
    return out


def airfoil_loop(af, n=401):
    """Closed (lower TE -> LE -> upper TE) chord-frame loop of an Airfoil."""
    x = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    return np.vstack([np.c_[x[::-1], af.lower(x[::-1])], np.c_[x[1:], af.upper(x[1:])]])


def shape_deviation(sec, af):
    """(max, rms, x at max) in mm: distance of OUR outline (airfoil af in the chord frame, scaled by the drawn
    chord) to the nearest drawn outline line; WR3's aileron gap excluded."""
    L = airfoil_loop(af)
    dd = np.full(len(L), np.inf)
    for P in sec["pts"]:
        if len(P) >= 2:
            dd = np.minimum(dd, _seg_dist(L, P))
    mm = dd * sec["chord"] * 1000.0
    keep = np.ones(len(L), bool)
    for a, b in EXCLUDE.get(sec.get("name"), ()):
        keep &= ~((L[:, 0] > a) & (L[:, 0] < b))
    i = int(np.argmax(np.where(keep, mm, -1)))
    return float(mm[keep].max()), float(np.sqrt(np.mean(mm[keep] ** 2))), float(L[i, 0])


def deviations(d=None, rev_a=False):
    """{name: (max, rms, x_at_max)} mm for the current airfoils (or rev A's)."""
    secs = drawn_sections(d)
    out = {}
    for n, s in secs.items():
        s["name"] = n
        af = W.airfoil_at(s["y"]) if not rev_a else _rev_a_airfoil_at(s["y"])
        out[n] = shape_deviation(s, af)
    return out


def _rev_a_airfoil_at(y):
    w = float(np.clip((y - 0.6) / (W.SEMI - 0.6), 0, 1))
    return AF.ls0417mod_rev_a().blend(AF.ls0313_rev_a(), w)


def fit(N=5, d=None):
    """Joint weighted least-squares CST fit of the root and tip coefficient sets (see the module doc)."""
    secs = drawn_sections(d)
    nA = N + 1
    xs = 0.5 * (1 - np.cos(np.linspace(0, np.pi, 161)))[1:-1]
    x_ = np.clip(xs, 0, 1)
    B = np.stack([comb(N, i) * x_ ** i * (1 - x_) ** (N - i) for i in range(nA)], 1)
    Cx = np.sqrt(x_) * (1 - x_)
    rows, rhs, wts = [], [], []
    for n, s in secs.items():
        w = float(np.clip((s["y"] - 0.6) / (W.SEMI - 0.6), 0, 1))       # = wing.airfoil_at's blend weight
        up, lo = envelope(s["cloud"], xs)
        for k, vals in ((0, up), (1, lo)):
            for i, (x, v) in enumerate(zip(xs, vals)):
                if not np.isfinite(v) or any(a <= x <= b for a, b in EXCLUDE.get(n, ())):
                    continue
                r = np.zeros(4 * nA + 2)
                r[k * nA:(k + 1) * nA] = (1 - w) * Cx[i] * B[i]
                r[(2 + k) * nA:(3 + k) * nA] = w * Cx[i] * B[i]
                sg = 0.5 if k == 0 else -0.5
                r[4 * nA], r[4 * nA + 1] = (1 - w) * sg * x, w * sg * x
                rows.append(r)
                rhs.append(v)
                wts.append(s["chord"])
    A, b, wv = np.array(rows), np.array(rhs), np.array(wts)
    sol = np.linalg.lstsq(A * wv[:, None], b * wv, rcond=None)[0]
    res = (A @ sol - b) * wv * 1000.0
    root = dict(upper=tuple(sol[:nA]), lower=tuple(sol[nA:2 * nA]), te=float(sol[4 * nA]))
    tip = dict(upper=tuple(sol[2 * nA:3 * nA]), lower=tuple(sol[3 * nA:4 * nA]), te=float(sol[4 * nA + 1]))
    return root, tip, res


def main(argv):
    if argv and argv[0] == "fit":
        N = int(argv[1]) if len(argv) > 1 else 5
        root, tip, res = fit(N)
        print(f"CST order {N}: envelope residual rms {np.sqrt(np.mean(res ** 2)):.2f} mm, max {np.abs(res).max():.2f} mm")
        for name, c in (("CST_LS0417MOD", root), ("CST_LS0313", tip)):
            print(f"{name} = dict(upper=({', '.join(f'{v:.5f}' for v in c['upper'])}),")
            print(f"{' ' * len(name)}        lower=({', '.join(f'{v:.5f}' for v in c['lower'])}), te={c['te']:.5f})")
        return
    for lab, ra in (("current", False), ("rev A", True)):
        dev = deviations(rev_a=ra)
        print(lab + ": " + "; ".join(f"{n} max {v[0]:.1f} rms {v[1]:.1f} mm (x/c {v[2]:.2f})" for n, v in dev.items()))
    for n, s in drawn_sections().items():
        af = W.airfoil_at(s["y"])
        x = np.array([0.1, 0.3, 0.7, 0.8, 0.9])
        up, lo = envelope(s["cloud"], x)
        print(f"{n} BL {s['y'] * 1000:.0f} t/c % at 0.1/0.3/0.7/0.8/0.9 c: drawn "
              + "/".join(f"{v * 100:.1f}" for v in up - lo) + "  ours "
              + "/".join(f"{v * 100:.1f}" for v in af.thickness(x)))


if __name__ == "__main__":
    main(sys.argv[1:])
