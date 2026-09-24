"""
Airfoil sections.

* LS(1)-04xx family (NASA GA(W)) approximations used on the PC-12 wing:
    root  LS(1)-0417MOD  (17 % thick, design Cl 0.4)
    tip   LS(1)-0313     (13 % thick, design Cl 0.3)
  Built from the NACA *modified four-digit* thickness form (max thickness at
  40 % chord, enlarged leading-edge radius) plus an aft-loaded mean line and a
  blunt trailing edge -- the defining traits of the GA(W) sections.  The
  published coordinate tables were not reachable from the build sandbox, so
  these are reconstructions, not the certified ordinates.
* NACA 4-digit symmetric sections (exact analytic form) for the empennage.
"""
from __future__ import annotations
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


def ls0417mod():
    return Airfoil("LS(1)-0417MOD",
                   lambda x: modified4_thickness(x, 0.17, 0.40, 8.0, 0.0028),
                   lambda x: aft_loaded_camber(x, 0.0240, 0.68))


def ls0313():
    return Airfoil("LS(1)-0313",
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
