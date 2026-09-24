"""Projection + datum audit for js/geo.js (task (b)).

1. js/geo.js maps lat/lon to world metres with a spherical equirectangular formula
   (M_PER_DEG_LAT = 110990, M_PER_DEG_LON = 111320 * cos(lat0)).  Compare it, over the task AOI
   (lat 37.595..37.640, lon -122.405..-122.350) and at the FAA runway ends, with
     (a) the rigorous local tangent plane (ENU, GRS80 ellipsoid, origin = ARP, pyproj 'topocentric'), and
     (b) UTM zone 10N (EPSG:26910) - the grid NAIP is delivered in.
2. Datum: NAD83(2011) (FAA survey data, NAIP, NOAA imagery) vs WGS 84 as broadcast by GPS today
   (WGS 84 (G2296) is aligned to ITRF2020, WGS 84 (G2139) to ITRF2014; both at the current epoch).
   pyproj/EPSG time-dependent Helmert "ITRF2020 to NAD83(2011) (1)" / "ITRF2014 to NAD83(2011) (1)".
   These model stable-North-America plate rotation only; the Bay Area's own motion relative to stable NA
   (Pacific-NA boundary zone) is NOT included - see docs/research/imagery.md.
3. Also reports the displacement field old-world -> new-world (LTP) that a migration would apply.

Writes refs/cache/naip/projection_audit.json and prints a summary.
usage: python3 tools/imagery/projection_audit.py
"""
import json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import pyproj

A_GRS80, F_GRS80 = 6378137.0, 1 / 298.257222101
E2 = F_GRS80 * (2 - F_GRS80)


def radii(lat):
    s = math.sin(math.radians(lat))
    N = A_GRS80 / math.sqrt(1 - E2 * s * s)
    M = A_GRS80 * (1 - E2) / (1 - E2 * s * s) ** 1.5
    return M, N


def main():
    out = {}
    M, N = radii(ARP_LAT)
    mlat_true = M * math.pi / 180; mlon_true = N * math.cos(math.radians(ARP_LAT)) * math.pi / 180
    out['scale_at_arp'] = dict(
        geojs_m_per_deg_lat=M_PER_DEG_LAT, grs80_m_per_deg_lat=mlat_true, lat_scale_err_ppm=(M_PER_DEG_LAT / mlat_true - 1) * 1e6,
        geojs_m_per_deg_lon=M_PER_DEG_LON, grs80_m_per_deg_lon=mlon_true, lon_scale_err_ppm=(M_PER_DEG_LON / mlon_true - 1) * 1e6)
    print('m/deg lat: geo.js %.1f  GRS80 %.1f  (%.0f ppm)' % (M_PER_DEG_LAT, mlat_true, out['scale_at_arp']['lat_scale_err_ppm']))
    print('m/deg lon: geo.js %.1f  GRS80 %.1f  (%.0f ppm)' % (M_PER_DEG_LON, mlon_true, out['scale_at_arp']['lon_scale_err_ppm']))

    # ---- grid over AOI ----
    la = np.linspace(AOI['lat0'], AOI['lat1'], 91); lo = np.linspace(AOI['lon0'], AOI['lon1'], 111)
    LO, LA = np.meshgrid(lo, la)
    xg, zg = world_geojs(LA, LO)
    xl, zl, _ = world_ltp(LA, LO)
    dx, dz = xg - xl, zg - zl; d = np.hypot(dx, dz)
    r = np.hypot(xl, zl)
    out['aoi_geojs_minus_ltp'] = dict(max_m=float(d.max()), rms_m=float(np.sqrt((d ** 2).mean())),
                                     max_dx_m=float(np.abs(dx).max()), max_dz_m=float(np.abs(dz).max()),
                                     at_max=dict(lat=float(LA.flat[d.argmax()]), lon=float(LO.flat[d.argmax()])))
    # error vs distance from ARP
    bins = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    out['err_vs_radius'] = [dict(r0=b0, r1=b1, max_m=float(d[(r >= b0) & (r < b1)].max()) if ((r >= b0) & (r < b1)).any() else None)
                            for b0, b1 in zip(bins, bins[1:])]
    # affine part vs non-linear part
    Aff = np.c_[xl.ravel(), zl.ravel(), np.ones(xl.size)]
    cx, *_ = np.linalg.lstsq(Aff, xg.ravel(), rcond=None); cz, *_ = np.linalg.lstsq(Aff, zg.ravel(), rcond=None)
    res = np.hypot(Aff @ cx - xg.ravel(), Aff @ cz - zg.ravel())
    out['affine_fit_geojs_from_ltp'] = dict(cx=cx.tolist(), cz=cz.tolist(), nonlinear_residual_max_m=float(res.max()),
                                           nonlinear_residual_rms_m=float(np.sqrt((res ** 2).mean())))
    print('AOI geo.js - LTP: max %.2f m, rms %.2f m; after best affine: max %.2f m' % (d.max(), np.sqrt((d ** 2).mean()), res.max()))
    for e in out['err_vs_radius']: print('   r %4d-%4d m: max %.2f m' % (e['r0'], e['r1'], e['max_m'] or 0))

    # ---- runway ends ----
    rows = {}
    for k, (lat, lon) in RWY_ENDS.items():
        a = world_geojs(lat, lon); b = world_ltp(lat, lon)
        rows[k] = dict(geojs=[float(a[0]), float(a[1])], ltp=[float(b[0]), float(b[1])], diff_m=[float(a[0] - b[0]), float(a[1] - b[1])])
    out['runway_ends'] = rows
    geod = pyproj.Geod(ellps='GRS80')
    rw = {}
    for p, q in RWY_PAIRS:
        (la1, lo1), (la2, lo2) = RWY_ENDS[p], RWY_ENDS[q]
        az, _, L = geod.inv(lo1, la1, lo2, la2)
        g1, g2 = np.array(rows[p]['geojs']), np.array(rows[q]['geojs'])
        Lg = float(np.linalg.norm(g2 - g1)); azg = (math.degrees(math.atan2(g2[0] - g1[0], -(g2[1] - g1[1]))) + 360) % 360
        rw[f'{p}-{q}'] = dict(geodesic_len_m=L, geojs_len_m=Lg, len_err_m=Lg - L, geodesic_az=az % 360, geojs_az=azg, az_err_deg=azg - az % 360)
        print(f'  {p}-{q}: geodesic {L:.2f} m az {az % 360:.3f}; geo.js {Lg:.2f} m ({Lg - L:+.2f}) az {azg:.3f} ({azg - az % 360:+.4f} deg)')
    out['runways'] = rw

    # ---- UTM 10N at ARP ----
    p = pyproj.Proj('EPSG:26910')
    f = p.get_factors(ARP_LON, ARP_LAT)
    E0, N0 = p(ARP_LON, ARP_LAT)
    out['utm10n_at_arp'] = dict(E=E0, N=N0, meridional_scale=f.meridional_scale, parallel_scale=f.parallel_scale,
                                grid_convergence_deg=f.meridian_convergence)
    print('UTM10N at ARP: k = %.6f, grid convergence %.4f deg (grid north is %s of true north)' %
          (f.meridional_scale, f.meridian_convergence, 'east' if f.meridian_convergence > 0 else 'west'))
    # error if UTM E/N were used as world x/-z after a pure translation
    Eg, Ng = p(LO, LA)
    xu, zu = Eg - E0, -(Ng - N0)
    du = np.hypot(xu - xl, zu - zl)
    out['utm_translated_minus_ltp_max_m'] = float(du.max())
    print('  UTM E/N used as world after translation only: max error vs LTP %.1f m (rotation %.3f deg + scale)' % (du.max(), f.meridian_convergence))

    # ---- datum NAD83(2011) -> ITRF2014 / ITRF2020 at several epochs ----
    ecef = {}
    dat = {}
    for tgt, name in [('EPSG:7912', 'ITRF2014 (~WGS84 G2139)'), ('EPSG:9989', 'ITRF2020 (~WGS84 G2296)')]:
        T = pyproj.Transformer.from_crs('EPSG:6319', tgt, always_xy=True)
        dat[name] = {}
        for ep in [2010.0, 2018.8, 2022.38, 2024.38, 2026.73]:
            lo2, la2, h2, _ = T.transform(ARP_LON, ARP_LAT, 0.0, ep)
            dE = (lo2 - ARP_LON) * mlon_true; dN = (la2 - ARP_LAT) * mlat_true
            dat[name][str(ep)] = dict(dE_m=dE, dN_m=dN, dH_m=h2, horiz_m=math.hypot(dE, dN), az_deg=(math.degrees(math.atan2(dE, dN)) + 360) % 360)
            if ep in (2010.0, 2026.73):
                print('  NAD83(2011) -> %s @%.2f: dE %+.3f m dN %+.3f m (|%.3f| m, az %.0f) dH %+.3f m' %
                      (name, ep, dE, dN, math.hypot(dE, dN), dat[name][str(ep)]['az_deg'], h2))
    out['datum_nad83_2011_to_itrf'] = dat
    Tn = pyproj.Transformer.from_crs('EPSG:4269', 'EPSG:4326', always_xy=True)
    lo2, la2 = Tn.transform(ARP_LON, ARP_LAT)
    out['naive_gis_nad83_to_wgs84_shift_m'] = math.hypot((lo2 - ARP_LON) * mlon_true, (la2 - ARP_LAT) * mlat_true)
    print('  default EPSG:4269 -> EPSG:4326 (what most GIS/pyproj do by default): %.3f m  (null transform)' % out['naive_gis_nad83_to_wgs84_shift_m'])

    # ---- migration field: old world (geo.js) -> new world (LTP), for a few representative points ----
    mig = {}
    for nm, (x, z) in dict(ARP=(0, 0), B_pier_tip=(-880, 900), G_pier_tip=(-1560, 100), rwy28R=tuple(rows['28R']['geojs']),
                           rwy10L=tuple(rows['10L']['geojs']), rwy1R=tuple(rows['1R']['geojs'])).items():
        la_, lo_ = ll_geojs(x, z); xn, zn, _ = world_ltp(la_, lo_)
        mig[nm] = dict(old=[float(x), float(z)], new=[float(xn), float(zn)], shift_m=[float(xn - x), float(zn - z)])
    out['migration_examples'] = mig
    json.dump(out, open(os.path.join(CACHE, 'projection_audit.json'), 'w'), indent=1)
    print('wrote', os.path.join(CACHE, 'projection_audit.json'))


if __name__ == '__main__':
    main()
