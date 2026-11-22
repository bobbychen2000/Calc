"""Numerics for the RH explainer video.

Everything the video shows as a number or a curve is computed here and cached in
data/zeta_data.npz + data/numbers.json.  Two independent routes are used wherever
possible: our own vectorised numpy implementation (Euler-Maclaurin zeta, Hardy Z,
sieve, explicit formula) and mpmath as the reference; the script asserts they agree,
and asserts the first zeros against the published values (Odlyzko's tables / LMFDB).

    python3 zeta.py          # ~1 min; writes data/
"""
import json
import math
import os
import sys
import time

import mpmath as mp
import numpy as np
from scipy.optimize import brentq
from scipy.special import expi, loggamma

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# Bernoulli numbers B_2k (exact), k = 1..16
B2K = [float(mp.bernoulli(2 * k)) for k in range(1, 17)]
FACT2K = [math.factorial(2 * k) for k in range(1, 17)]


# --------------------------------------------------------------------------------------
# zeta
# --------------------------------------------------------------------------------------
def zeta_em(s, N=None, K=14):
    """Euler-Maclaurin zeta for Re s > -K roughly; vectorised over complex arrays.

    zeta(s) = sum_{n<N} n^-s + N^(1-s)/(s-1) + N^-s/2
              + sum_k B_2k/(2k)! * s(s+1)...(s+2k-2) * N^(-s-2k+1)  + remainder
    The remainder is about |s+2K| ... / (2 pi N)^(2K); N defaults to max(30, |t|/2 + 30).
    """
    s = np.asarray(s, dtype=complex)
    if N is None:
        tmax = float(np.max(np.abs(s.imag))) if s.size else 0.0
        N = int(max(30, tmax / 2 + 30))
    n = np.arange(1, N, dtype=float)
    flat = s.ravel()
    out = np.empty_like(flat)
    logn = np.log(n)
    logN = math.log(N)
    CH = 4096
    for i in range(0, flat.size, CH):
        ss = flat[i:i + CH]
        acc = np.exp(-np.outer(ss, logn)).sum(axis=1)
        NmS = np.exp(-ss * logN)
        acc = acc + N * NmS / (ss - 1) + 0.5 * NmS
        poch = ss.copy()  # s(s+1)...(s+2k-2), starts with k=1: s
        Npow = NmS / N  # N^(-s-1)
        for k in range(1, K + 1):
            acc = acc + B2K[k - 1] / FACT2K[k - 1] * poch * Npow
            poch = poch * (ss + 2 * k - 1) * (ss + 2 * k)
            Npow = Npow / (N * N)
        out[i:i + CH] = acc
    return out.reshape(s.shape)


def zeta(s):
    """zeta on the whole plane (except s = 1): Euler-Maclaurin for Re s >= 1/2, the
    functional equation zeta(s) = 2^s pi^(s-1) sin(pi s/2) Gamma(1-s) zeta(1-s) otherwise."""
    s = np.asarray(s, dtype=complex)
    out = np.empty_like(s)
    right = s.real >= 0.5
    if right.any():
        out[right] = zeta_em(s[right])
    left = ~right
    if left.any():
        sl = s[left]
        z1 = zeta_em(1 - sl)
        # 2^s pi^(s-1) sin(pi s / 2) Gamma(1-s), in logs where it matters
        lg = loggamma(1 - sl)
        fac = np.exp(sl * math.log(2) + (sl - 1) * math.log(math.pi) + lg) * np.sin(np.pi * sl / 2)
        out[left] = fac * z1
    out[s == 0] = -0.5  # zeta(0) = -1/2 (the functional equation is 0 * inf there)
    return out


def theta_rs(t):
    """Riemann-Siegel theta: arg Gamma(1/4 + i t/2) - (t/2) log pi (continuous branch)."""
    t = np.asarray(t, dtype=float)
    return np.imag(loggamma(0.25 + 0.5j * t)) - 0.5 * t * math.log(math.pi)


def hardy_z(t):
    """Hardy's Z(t) = exp(i theta(t)) zeta(1/2 + i t): real, |Z| = |zeta| on the line."""
    t = np.asarray(t, dtype=float)
    z = np.exp(1j * theta_rs(t)) * zeta_em(0.5 + 1j * t)
    return z.real, np.max(np.abs(z.imag) / (1 + np.abs(z.real)))


def find_zeros(tmax, step=0.01):
    """Heights of the zeros of zeta on the critical line in (0, tmax]: sign changes of Z
    on a fine grid, refined with Brent's method."""
    t = np.arange(1.0, tmax + step, step)
    zt, imag_err = hardy_z(t)
    assert imag_err < 1e-8, imag_err
    idx = np.nonzero(np.sign(zt[:-1]) * np.sign(zt[1:]) < 0)[0]
    f = lambda x: float(hardy_z(np.array([x]))[0][0])
    return np.array([brentq(f, t[i], t[i + 1], xtol=1e-13, rtol=1e-15) for i in idx])


# Published zero heights (A. Odlyzko, "The first 100 zeros of the Riemann zeta function,
# accurate to over 1000 decimal places", www-users.cse.umn.edu/~odlyzko/zeta_tables/),
# truncated to 12 decimals.
PUBLISHED = [14.134725141734, 21.022039638771, 25.010857580145, 30.424876125859,
             32.935061587739, 37.586178158825, 40.918719012147, 43.327073280914,
             48.005150881167, 49.773832477672]


# --------------------------------------------------------------------------------------
# primes
# --------------------------------------------------------------------------------------
def sieve(n):
    is_p = np.ones(n + 1, dtype=bool)
    is_p[:2] = False
    for p in range(2, int(n ** 0.5) + 1):
        if is_p[p]:
            is_p[p * p::p] = False
    return np.nonzero(is_p)[0]


def li(x):
    """Logarithmic integral li(x) = Ei(ln x) (principal value from 0)."""
    return expi(np.log(np.asarray(x, dtype=float)))


def von_mangoldt_psi(primes, xmax):
    """Chebyshev psi(x) = sum_{p^k <= x} log p, as jump points (x_j, psi just after x_j)."""
    pts = []
    for p in primes:
        if p > xmax:
            break
        pk = p
        while pk <= xmax:
            pts.append((pk, math.log(p)))
            pk *= p
    pts.sort()
    xs = np.array([a for a, _ in pts], dtype=float)
    ps = np.cumsum([b for _, b in pts])
    return xs, ps


def psi_explicit(x, gammas):
    """psi_0(x) = x - sum_rho x^rho / rho - log(2 pi) - 1/2 log(1 - x^-2), with the
    zeros rho = 1/2 + i gamma taken in conjugate pairs (2 Re x^rho / rho)."""
    x = np.asarray(x, dtype=float)
    lx = np.log(x)
    acc = x - math.log(2 * math.pi) - 0.5 * np.log(1 - x ** -2.0)
    for g in gammas:
        rho = 0.5 + 1j * g
        acc = acc - 2 * np.real(np.exp(rho * lx) / rho)
    return acc


# --------------------------------------------------------------------------------------
# finite fields: the elliptic curve 37a1, y^2 + y = x^3 - x
# --------------------------------------------------------------------------------------
def legendre_table(p):
    sq = np.zeros(p, dtype=np.int64)
    sq[(np.arange(1, p) ** 2) % p] = 1
    tab = np.where(sq == 1, 1, -1)
    tab[0] = 0
    return tab


def count_37a(p):
    """Number of points (incl. the point at infinity) of y^2 + y = x^3 - x over F_p, p odd.
    Completing the square: (2y+1)^2 = 4x^3 - 4x + 1."""
    x = np.arange(p, dtype=np.int64)
    rhs = (4 * x * x % p * x - 4 * x + 1) % p
    L = legendre_table(p)
    return int(1 + p + L[rhs].sum())


def count_37a_brute(p):
    n = 1
    for x in range(p):
        r = (x ** 3 - x) % p
        for y in range(p):
            if (y * y + y) % p == r:
                n += 1
    return n


# --------------------------------------------------------------------------------------
def main():
    os.makedirs(DATA, exist_ok=True)
    t0 = time.time()
    mp.mp.dps = 30
    nums = {}

    # 1. our zeta against mpmath on random points of the plane (both branches)
    rng = np.random.default_rng(1859)
    pts = (rng.uniform(-12, 8, 60) + 1j * rng.uniform(-60, 60, 60))
    pts = pts[np.abs(pts - 1) > 0.3]
    ours = zeta(pts)
    ref = np.array([complex(mp.zeta(complex(p))) for p in pts])
    rel = np.max(np.abs(ours - ref) / np.maximum(1e-30, np.abs(ref)))
    print(f"zeta vs mpmath on {len(pts)} points: max rel err {rel:.2e}")
    assert rel < 1e-9, rel
    # special values
    assert abs(zeta(np.array([2.0]))[0] - math.pi ** 2 / 6) < 1e-13
    assert abs(zeta(np.array([-1.0]))[0] + 1 / 12) < 1e-13
    assert abs(zeta(np.array([0.0]))[0] + 0.5) < 1e-15
    for k in (2, 4, 6, 8):  # trivial zeros
        assert abs(zeta(np.array([-float(k)]))[0]) < 1e-12
    nums["zeta2"] = math.pi ** 2 / 6

    # 2. zeros on the critical line, our Z(t) vs mpmath.zetazero vs the published table
    TMAX = 1500.0
    gam = find_zeros(TMAX)
    print(f"{len(gam)} zeros with 0 < t <= {TMAX} ({time.time()-t0:.1f} s)")
    for i, g in enumerate(PUBLISHED):
        assert abs(gam[i] - g) < 2e-12, (i, gam[i], g)
    ref100 = np.array([float(mp.zetazero(n).imag) for n in range(1, 101)])
    err100 = np.max(np.abs(gam[:100] - ref100))
    print(f"first 100 zeros vs mpmath.zetazero: max abs err {err100:.2e}; 100th = {gam[99]:.12f}")
    assert err100 < 1e-9
    # completeness: the count must equal N(T) from the argument principle (mpmath.nzeros)
    for T in (100.0, 236.6, 1000.0, TMAX):
        n_ours = int(np.sum(gam <= T))
        n_ref = int(mp.nzeros(T))
        print(f"N({T}) ours {n_ours}  mpmath {n_ref}")
        assert n_ours == n_ref, (T, n_ours, n_ref)
    nums["zeros_first10"] = [round(float(g), 6) for g in gam[:10]]
    nums["zero_100"] = round(float(gam[99]), 6)
    nums["n_zeros_below_100"] = int(np.sum(gam < 100))
    nums["n_zeros_total"] = int(len(gam))
    nums["tmax"] = TMAX

    # 3. Hardy Z(t) and |zeta(1/2+it)| curves for plotting
    tz = np.linspace(0, 60, 6001)
    tz[0] = 1e-6
    zt, _ = hardy_z(tz)
    tline = np.linspace(0, 100, 10001)
    zline = zeta_em(0.5 + 1j * tline)
    # partial-sum spiral for s = 1/2 + 14.1347i (does NOT converge; shown as a contrast)
    # and for s = 2 + 3i (converges)
    s_conv = 2 + 3j
    n = np.arange(1, 2001)
    spiral_conv = np.concatenate([[0], np.cumsum(n ** -s_conv)])
    nums["zeta_2p3i"] = [float(zeta(np.array([s_conv]))[0].real), float(zeta(np.array([s_conv]))[0].imag)]
    assert abs(spiral_conv[-1] - complex(mp.zeta(s_conv))) < 1e-3  # tail ~ N^(1-sigma)/|s-1|

    # 4. domain-colouring grid of zeta over sigma in [-15, 9], t in [-3, 41] (equal aspect,
    #    25 samples per unit): the trivial zeros along the bottom, the first 8 zeros in the strip
    sig = np.linspace(-15, 9, 601)
    tt = np.linspace(-3, 41, 1101)
    S, T = np.meshgrid(sig, tt)
    G = S + 1j * T
    G[np.abs(G - 1) < 1e-9] += 1e-6
    Zg = zeta(G)
    print(f"domain grid {Zg.shape} done ({time.time()-t0:.1f} s)")

    # 5. primes, pi(x), li(x), psi(x)
    XMAX = 1_000_000
    primes = sieve(XMAX)
    nums["pi_1e6"] = int(len(primes))
    assert len(primes) == 78498  # pi(10^6), OEIS A006880
    assert int(np.sum(primes <= 100)) == 25 and int(np.sum(primes <= 1000)) == 168
    xs_pi = np.array([10 ** k for k in range(1, 7)], dtype=float)
    pi_tab = [int(np.searchsorted(primes, x, side="right")) for x in xs_pi]
    li_tab = li(xs_pi)
    nums["pi_table"] = [[int(x), p, float(l), float(x / math.log(x))] for x, p, l in zip(xs_pi, pi_tab, li_tab)]
    assert abs(li(np.array([1e6]))[0] - float(mp.li(1e6))) < 1e-6
    # pi(x) - li(x) against the RH-conditional Schoenfeld bound sqrt(x) log(x) / (8 pi)
    xg = np.unique(np.round(np.geomspace(2657, XMAX, 4000)).astype(int))
    pig = np.searchsorted(primes, xg, side="right")
    dev = pig - li(xg)
    bound = np.sqrt(xg) * np.log(xg) / (8 * math.pi)
    assert np.all(np.abs(dev) < bound)
    nums["pi_minus_li_max_ratio_to_schoenfeld"] = float(np.max(np.abs(dev) / bound))
    xpsi, psival = von_mangoldt_psi(primes, 200000)
    # explicit formula with K zero pairs, sampled on a grid for x in [2, 100]
    xe = np.linspace(2, 100, 4901)
    psi_true_e = np.array([psival[np.searchsorted(xpsi, x, side="right") - 1] if x >= 2 else 0 for x in xe])
    recon = {}
    for K in (0, 1, 3, 10, 30, 100, 1000):
        recon[K] = psi_explicit(xe, gam[:K])
    # sanity: with 1000 zero pairs the reconstruction is close away from the jumps
    away = np.ones_like(xe, dtype=bool)
    for pk in xpsi[xpsi <= 100]:
        away &= np.abs(xe - pk) > 0.6
    err_rec = np.max(np.abs(recon[1000][away] - psi_true_e[away]))
    print(f"explicit formula, 1000 zero pairs: max |err| away from jumps {err_rec:.3f}")
    assert err_rec < 0.6, err_rec
    nums["explicit_err_1000"] = float(err_rec)
    # psi(x) - x versus sqrt(x) up to 2e5
    xg2 = np.geomspace(10, 200000, 3000)
    psi_g2 = psival[np.searchsorted(xpsi, xg2, side="right") - 1]
    nums["psi_minus_x_over_sqrtx_max"] = float(np.max(np.abs(psi_g2 - xg2) / np.sqrt(xg2)))

    # 6. Hasse-Weil: y^2 + y = x^3 - x over F_p (LMFDB 37.a1); a_p = p + 1 - N_p
    for p in (3, 5, 7, 11, 13):
        assert count_37a(p) == count_37a_brute(p)
    pl = [int(p) for p in primes if 3 <= p <= 5000 and p != 37]
    Np = np.array([count_37a(p) for p in pl])
    ap = np.array(pl) + 1 - Np
    # LMFDB 37.a1 q-expansion: q - 2q^2 - 3q^3 + 2q^4 - 2q^5 + 6q^6 - q^7 + 6q^9 + 4q^10 - 5q^11 ...
    assert list(ap[:4]) == [-3, -2, -1, -5], ap[:4]  # a_3, a_5, a_7, a_11
    assert np.all(np.abs(ap) <= 2 * np.sqrt(pl))
    nums["hasse_examples"] = [[p, int(n), int(a), round(2 * math.sqrt(p), 3)] for p, n, a in zip(pl[:8], Np[:8], ap[:8])]
    nums["hasse_max_ratio"] = float(np.max(np.abs(ap) / (2 * np.sqrt(pl))))
    nums["hasse_n_primes"] = len(pl)

    # 7. theta function symmetry theta(1/t) = sqrt(t) theta(t), theta(t) = sum_{n in Z} exp(-pi n^2 t)
    def theta(t):
        nn = np.arange(-60, 61)
        return np.exp(-math.pi * np.outer(np.atleast_1d(t), nn ** 2)).sum(axis=1)
    tth = np.geomspace(0.05, 20, 400)
    assert np.max(np.abs(theta(1 / tth) - np.sqrt(tth) * theta(tth)) / theta(1 / tth)) < 1e-12

    np.savez_compressed(
        os.path.join(DATA, "zeta_data.npz"),
        gammas=gam, tz=tz, zt=zt, tline=tline, zline=zline,
        spiral_conv=spiral_conv, dom_sig=sig, dom_t=tt, dom_z=Zg.astype(np.complex64),
        primes=primes, xg=xg, dev=dev, bound=bound,
        xpsi=xpsi, psival=psival, xe=xe, psi_true_e=psi_true_e,
        **{f"recon_{K}": v for K, v in recon.items()},
        xg2=xg2, psi_g2=psi_g2, hw_p=np.array(pl), hw_ap=ap, hw_np=Np,
        tth=tth, theta_t=theta(tth),
    )
    with open(os.path.join(DATA, "numbers.json"), "w") as f:
        json.dump(nums, f, indent=1)
    print(json.dumps(nums, indent=1)[:2000])
    print(f"done in {time.time()-t0:.1f} s")


if __name__ == "__main__":
    sys.exit(main())
