"""
Airfoil sections.

* LS(1)-04xx family (NASA GA(W)) sections of the PC-12 wing (Jane's):
    root  LS(1)-0417MOD  (nominally 17 % thick; as drawn 16.7 % at 30 % c)
    tip   LS(1)-0313     (nominally 13 % thick; as drawn 12.8 % at 38 % c)
  Stage 2 (rev B): both are CST (Kulfan class-shape) sections, order 5, fitted TOGETHER to the Pilatus NGX
  drawing's wing sections WR1-WR4 (BL 900 / 5557 / 6658 / 7395), each normalised by its own leading and
  trailing edge (drawing/airfoil_fit.py; the wing blends root -> tip linearly in span, wing.airfoil_at).  The
  drawn sections are classic GA(W) shapes: blunt nose, strong forward camber, maximum thickness at ~30-38 % c,
  a thin aft third with the lower-surface cusp (aft loading).  Fit: our outline within 3.9 mm of every drawn
  section (rms <= 1.5 mm).  The published coordinate tables were not reachable from the build sandbox, so
  these are reconstructions from the drawing, not the certified ordinates.
  Rev A (the model before this refit) used the NACA modified four-digit thickness form with max thickness at
  40 % c plus an aft-loaded mean line: the forward half matched, but aft of ~45 % c it was far too full
  (t/c at 80 % c 9.5 % vs the drawn 5.4 % at the root) -- kept as ls0417mod_rev_a() / ls0313_rev_a().
* NACA 4-digit symmetric sections (exact analytic form) for the empennage.
"""
from __future__ import annotations
from math import comb

import numpy as np


def naca4_thickness(x, t, closed_te=True):
    a4 = -0.1036 if closed_te else -0.1015
    return 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 + a4 * x ** 4)


def modified4_thickness(x, t, M=0.40, I=8.0, te_half=0.0025):
    """NACA modified 4-digit thickness distribution (Abbott & von Doenhoff).

    Forward of M:  y = a0*sqrt(x) + a1*x + a2*x^2 + a3*x^3
    Aft of M:      y = d0 + d1*(1-x) + d2*(1-x)^2 + d3*(1-x)^3
    Scaled to max half-thickness t/2 at x=M.  I = leading-edge radius index.
    """
    d1_tab = {0.2: 0.200, 0.3: 0.234, 0.4: 0.315, 0.5: 0.465, 0.6: 0.700}
    h = t / 2.0
    d0 = te_half
    d1 = d1_tab[round(M, 1)] * (t / 0.2)
    # aft: y(M)=h, y'(M)=0
    s = 1 - M
    A = np.array([[s ** 2, s ** 3], [-2 * s, -3 * s ** 2]])
    b = np.array([h - d0 - d1 * s, d1])
    d2, d3 = np.linalg.solve(A, b)
    # curvature of aft part at M (for continuity)
    ypp_aft = 2 * d2 + 6 * d3 * s
    a0 = 0.296904 * (I / 6.0) * (t / 0.2)
    # forward: y(M)=h, y'(M)=0, y''(M)=ypp_aft
    A = np.array([[M, M ** 2, M ** 3], [1, 2 * M, 3 * M ** 2], [0, 2, 6 * M]])
    b = np.array([h - a0 * np.sqrt(M), -0.5 * a0 / np.sqrt(M), ypp_aft + 0.25 * a0 * M ** -1.5])
    a1, a2, a3 = np.linalg.solve(A, b)
    x = np.asarray(x, float)
    fwd = a0 * np.sqrt(x) + a1 * x + a2 * x ** 2 + a3 * x ** 3
    aft = d0 + d1 * (1 - x) + d2 * (1 - x) ** 2 + d3 * (1 - x) ** 3
    return np.where(x < M, fwd, aft)


def aft_loaded_camber(x, cmax, xc=0.62):
    """Aft-loaded mean line  ~ x^p (1-x)^q, peak cmax at x = xc."""
    q = 0.98
    p = q * xc / (1 - xc)
    x = np.clip(np.asarray(x, float), 0, 1)
    f = x ** p * (1 - x) ** q
    fmax = xc ** p * (1 - xc) ** q
    return cmax * f / fmax


class Airfoil:
    """Callable section: upper(x), lower(x) in chord units (x in [0,1])."""

    def __init__(self, name, thick_fn, camber_fn):
        self.name = name
        self._t = thick_fn
        self._c = camber_fn

    def upper(self, x):
        return self._c(x) + self._t(x)

    def lower(self, x):
        return self._c(x) - self._t(x)

    def thickness(self, x):
        return 2 * self._t(x)

    def camber(self, x):
        return self._c(x)

    def blend(self, other, w, name=None):
        a, b = self, other
        return Airfoil(name or f"{a.name}~{b.name}",
                       lambda x: (1 - w) * a._t(x) + w * b._t(x),
                       lambda x: (1 - w) * a._c(x) + w * b._c(x))

    def loop(self, n=81, x_upper_end=1.0, x_lower_end=1.0):
        """Closed-ish point loop: lower TE -> LE -> upper TE (clockwise in x-z).
        Returns (n_total, 2) points and the x parameter per point."""
        xl = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
        xlo = (xl * x_lower_end)[::-1]
        xup = (xl * x_upper_end)[1:]
        pts = np.vstack([np.stack([xlo, self.lower(xlo)], 1), np.stack([xup, self.upper(xup)], 1)])
        return pts


def cst_surface(x, A, te=0.0, n1=0.5, n2=1.0):
    """Kulfan CST surface  y = x^n1 (1-x)^n2 * sum_i A_i B_i,n(x) + x * te  (x clipped to [0, 1]); the default
    class function (n1 0.5, n2 1.0) gives a round nose and a sharp-or-blunt (te) trailing edge."""
    x = np.clip(np.asarray(x, float), 0.0, 1.0)
    n = len(A) - 1
    S = sum(a * comb(n, i) * x ** i * (1 - x) ** (n - i) for i, a in enumerate(A))
    return x ** n1 * (1 - x) ** n2 * S + x * te


def cst_airfoil(name, coef):
    """Airfoil from CST coefficient sets dict(upper=(...), lower=(...), te=TE thickness / chord): the TE
    midpoint lies on the chord line (LE (0, 0) -> TE (1, 0)), so thickness = (yu - yl) / 2 and
    camber = (yu + yl) / 2 in the Airfoil convention (upper = camber + t, lower = camber - t)."""
    Au, Al, te = coef["upper"], coef["lower"], coef["te"]

    def yu(x):
        return cst_surface(x, Au, 0.5 * te)

    def yl(x):
        return cst_surface(x, Al, -0.5 * te)

    return Airfoil(name, lambda x: 0.5 * (yu(x) - yl(x)), lambda x: 0.5 * (yu(x) + yl(x)))


# Stage 2 rev B: joint fit to the drawing's WR1-WR4 (python3 -m drawing.airfoil_fit fit 5)
CST_LS0417MOD = dict(upper=(0.29595, 0.33900, 0.14823, 0.33503, 0.23125, 0.20159),
                     lower=(-0.18092, -0.16858, -0.09328, -0.31660, -0.02741, 0.11090), te=0.00559)
CST_LS0313 = dict(upper=(0.22137, 0.18626, 0.14993, 0.32496, 0.15082, 0.24125),
                  lower=(-0.15515, -0.07067, -0.18309, -0.10311, -0.12938, 0.16839), te=0.00543)


def ls0417mod():
    return cst_airfoil("LS(1)-0417MOD", CST_LS0417MOD)


def ls0313():
    return cst_airfoil("LS(1)-0313", CST_LS0313)


def ls0417mod_rev_a():
    """Rev A reconstruction (modified four-digit thickness + aft-loaded camber): too full aft of ~45 % c."""
    return Airfoil("LS(1)-0417MOD rev A",
                   lambda x: modified4_thickness(x, 0.17, 0.40, 8.0, 0.0028),
                   lambda x: aft_loaded_camber(x, 0.0240, 0.68))


def ls0313_rev_a():
    return Airfoil("LS(1)-0313 rev A",
                   lambda x: modified4_thickness(x, 0.13, 0.40, 7.5, 0.0022),
                   lambda x: aft_loaded_camber(x, 0.0180, 0.68))


def naca00(t, name=None, closed_te=False):
    return Airfoil(name or f"NACA 00{int(round(t * 100)):02d}",
                   lambda x: naca4_thickness(np.clip(x, 0, 1), t, closed_te),
                   lambda x: 0.0 * np.asarray(x, float))


def naca4(m, p, t, name=None):
    def camber(x):
        x = np.asarray(x, float)
        return np.where(x < p, m / p ** 2 * (2 * p * x - x ** 2),
                        m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
    return Airfoil(name or f"NACA {int(m*100)}{int(p*10)}{int(t*100):02d}",
                   lambda x: naca4_thickness(np.clip(x, 0, 1), t, False), camber)


if __name__ == "__main__":
    for af in (ls0417mod(), ls0313()):
        x = np.linspace(0, 1, 2001)
        th = af.thickness(x)
        i = np.argmax(th)
        # leading-edge radius estimate from y = a0 sqrt(x)
        print(af.name, "t/c=%.4f at x=%.3f" % (th[i], x[i]),
              "upper max=%.4f lower min=%.4f @%.2f" % (af.upper(x).max(), af.lower(x).min(), x[np.argmin(af.lower(x))]),
              "lower@0.9=%.4f TE thick=%.4f" % (af.lower(np.array(0.9)), af.thickness(np.array(1.0))))
