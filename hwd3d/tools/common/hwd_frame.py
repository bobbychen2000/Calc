"""World frame of Hayward Live 3D (KHWD) - the Python twin of js/geo.js (keep the two identical;
test: tools/common/test_hwd_frame.py, which also checks both against pyproj and the FAA NASR rows).

Forked from sfo3d/tools/geo_frame.py @ a967f9b. Kept: the frame design (exact local tangent plane on GRS80 at the ARP,
NAD83(2011), x east / y up / z south, metres), ll_to_en / en_to_ll, the WGS 84 displacement handling, hdg_vec / vec_hdg
and the numpy conveniences. Changed: origin = HWD ARP, frame id, datum displacement recomputed for HWD at epoch 2026.86,
FAA runway data for 10L/28R and 10R/28L (NASR cycle 2026-10-29), explicit vertical reference (y = NAVD 88 height),
new helpers: UTM zone 10N (EPSG:26910, for NAIP) in closed form, runway axis along/across, runway surface profile.
Dropped (SFO only): the airport s/t grid, the legacy 'equirect-v1' frame and its migration, approach lights.

World frame (frame id 'ltp-nad83-2011-hwd')
-------------------------------------------
* x = east, z = south, y = up, metres. Origin = FAA airport reference point (ARP) of HWD.
* Datum: NAD83(2011). FAA NASR coordinates are NAD 83 (sfo3d read the FAA NASR CSV_README: "All US coordinate
  information provided currently references NAD 83"; the realisation is not stated - NAD83(2011) is inferred, as in
  sfo3d, from the 0.3 m NASR-NAIP agreement at SFO). USDA NAIP is delivered in EPSG:26910 (NAD83 / UTM 10N).
* Projection: exact local tangent plane (ENU) on the GRS80 ellipsoid at the ARP, at ellipsoidal height 0:
  (lat, lon) -> ECEF -> east/north at the ARP. Flat world: an aircraft at height h is drawn at y = h above its ground
  point, so the horizontal position never depends on h. Scale error vs geodesic distance < 0.1 mm within 5 km of the
  ARP, 0.5 m at 50 km (d^3 / 6R^2). The inverse is a fixed-Jacobian Newton iteration to < 1e-9 m.
* ARP: FAA NASR APT_BASE (cycle 2026-10-29) HWD: 37-39-32.154N 122-07-18.26W, LAT_DECIMAL 37.65893166,
  LONG_DECIMAL -122.12173888 (ARPT_PSN_SOURCE 3RD PARTY SURVEY 2023/07/05). The constants below are those decimals
  rounded to 1e-7 deg: the origin lies 4.4 mm north and 1.8 mm west of the NASR decimal point (3.7 mm N, 1.0 mm W of the
  DMS value). The origin is only a reference; every feature is placed from its own coordinates.

Vertical reference (y)
----------------------
* y = orthometric height in metres above NAVD 88 (~ mean sea level), i.e. y = NASR elevation (ft) * 0.3048. NASR gives
  "MSL" elevations; that they are NAVD 88 is inferred (FAA AC 150/5300-18 airport surveys use NAVD 88 - from memory,
  not re-read; the NASR CSV README could not be re-read either: nfdc.faa.gov returned HTTP 503 on 2026-11-12).
  This differs from sfo3d, whose y is elevation - 4.0 m + GROUND_Y 3 (sfo3d tools/env/build_reservoirs.py): at HWD the
  surface is not flat - the runway ends lie at 27.7 to 52.1 ft (8.44 to 15.88 m) - so y keeps the true heights.
* FIELD_ELEV_FT = 52.1 ft (NASR APT_BASE ELEV, the highest point of the landing surfaces) -> FIELD_ELEV_Y 15.880 m.
* GROUND_Y = 11.4 m is a NOMINAL flat-ground level for code that has no terrain model yet (forked sfo3d code places
  objects at GROUND_Y): the mean of the six NASR runway-surface elevations (4 ends + 2 displaced thresholds, 37.38 ft
  = 11.39 m) [inferred]. Against those points it is 2.96 m too high at the 10R end and 4.48 m too low at the 28L end.
  Use rwy_surface_y() on the runways; replace both with a USGS 3DEP terrain model (PLAN Phase 2).
* Not provided: ellipsoidal heights (ADS-B alt_geom is HAE on WGS 84) -> NAVD 88 needs the GEOID18 grid [open].

WGS 84 inputs (ADS-B, OSM, GNSS)
--------------------------------
NAD83(2011) -> WGS 84 (G2296) = ITRF2020 at the HWD ARP, epoch 2026.86 (12 Nov 2026), is a displacement of a fixed
ground point of dE = -1.568 m, dN = +0.162 m (1.576 m toward azimuth 276 deg; vertical -0.512 m). Computed in this
frame with pyproj 3.8.0 / PROJ 9.8.1, Transformer EPSG:6319 -> EPSG:10605 = "Inverse of ITRF2020 to NAD83(2011) (1)"
(time-dependent coordinate-frame Helmert, t0 2010.0) + "Inverse of WGS 84 (G2296) to ITRF2020 (1)" (zero
parameters) - the chain sfo3d documents (geo_frame.py). Unrounded: dE -1.56753, dN +0.16210, dH -0.51171 m.
Rate: -1.37 cm/yr east, -1.31 cm/yr north. Spatial variation of the displacement: 0.6 mm within ~5 km, 5.6 mm within
~50 km. Sanity check: the same pyproj gives -1.5679 / +0.1589 at the SFO ARP @ 2026.73, sfo3d's -1.568 / +0.159
(PROJ 9.5.1). PROJ's *default* EPSG:4269 -> EPSG:4326 is "NAD83 to WGS 84 (1)" = +proj=noop, a null transformation
(checked by the test) - never let a tool apply it silently. Not modelled: intraplate (Bay Area) motion since 2010.0 (NGS HTDP not available; order 0.2-0.4 m NW,
[unverified], as in sfo3d).
  wgs84_to_world: project the WGS 84 lat/lon through the same plane, then x += 1.568, z += 0.162.

UTM zone 10N (EPSG:26910 = NAD83 / UTM 10N; NAIP)
-------------------------------------------------
utm10_to_ll / ll_to_utm10: transverse Mercator on GRS80 (k0 0.9996, lon0 -123, false easting 500 km) by the Krueger
n-series to 6th order (coefficients and the tau/tau' Newton step from C.F.F. Karney, "Transverse Mercator with an
accuracy of a few nanometres", J. Geodesy 85 (2011) 475-485). The test checks it against pyproj EPSG:26910 (PROJ 9.8.1
+proj=utm +zone=10 +ellps=GRS80) to 1 mm both ways (measured agreement 2-4 nm within 50 km). NAIP E/N are treated
as NAD83(2011) coordinates, as in sfo3d. Never use UTM E/N as world x/-z after a shift: the grid is rotated
(meridian convergence +0.537 deg at the ARP) and scaled (k 0.999674 at the ARP; pyproj factors).
"""
import math

# --------------------------------------------------------------------------------------------------------- constants
FRAME_ID = 'ltp-nad83-2011-hwd'
ARP_LAT, ARP_LON = 37.6589317, -122.1217389            # FAA NASR APT_BASE LAT/LONG_DECIMAL, rounded (see header)
GRS80_A = 6378137.0
GRS80_F = 1 / 298.257222101
E2 = GRS80_F * (2 - GRS80_F)
D2R = math.pi / 180
FT = 0.3048                                           # international foot (exact)

# vertical reference (see header): y = NAVD 88 height in metres [NAVD 88 inferred]
Y_REF = 'NAVD 88 orthometric height (m) [inferred from NASR MSL elevations]'
FIELD_ELEV_FT = 52.1                                  # FAA NASR APT_BASE ELEV (3RD PARTY SURVEY 2023/07/05)
FIELD_ELEV_Y = FIELD_ELEV_FT * FT                     # 15.880 m
GROUND_Y = 11.4                                       # nominal flat ground [inferred]: mean of 6 NASR runway points


def elev_ft_to_y(ft):
    """NASR / chart elevation (ft MSL) -> world y (m)."""
    return ft * FT


# NAD83(2011) -> WGS 84 (G2296) displacement of a fixed ground point at the HWD ARP, epoch 2026.86 (see header)
WGS84_EPOCH = 2026.86
WGS84_MINUS_NAD83_E = -1.568
WGS84_MINUS_NAD83_N = +0.162
WGS84_MINUS_NAD83_H = -0.512                          # ellipsoidal height (information only; y is NAVD 88)
WGS84_RATE_E = -0.0137                                # m/yr
WGS84_RATE_N = -0.0131


def _ecef(lat, lon):
    sl = math.sin(lat * D2R); cl = math.cos(lat * D2R)
    N = GRS80_A / math.sqrt(1 - E2 * sl * sl)
    return (N * cl * math.cos(lon * D2R), N * cl * math.sin(lon * D2R), N * (1 - E2) * sl)


_O = _ecef(ARP_LAT, ARP_LON)
_S0 = math.sin(ARP_LAT * D2R); _C0 = math.cos(ARP_LAT * D2R)
_SL = math.sin(ARP_LON * D2R); _CL = math.cos(ARP_LON * D2R)
_W0 = math.sqrt(1 - E2 * _S0 * _S0)
MLAT = GRS80_A * (1 - E2) / (_W0 ** 3) * D2R          # metres per degree of latitude at the ARP (meridian radius)
MLON = GRS80_A / _W0 * _C0 * D2R                        # metres per degree of longitude at the ARP


def ll_to_en(lat, lon):
    """NAD83(2011) lat/lon (deg) -> (east, north) metres in the world plane."""
    x, y, z = _ecef(lat, lon)
    dx = x - _O[0]; dy = y - _O[1]; dz = z - _O[2]
    return (-_SL * dx + _CL * dy, -_S0 * _CL * dx - _S0 * _SL * dy + _C0 * dz)


def en_to_ll(e, n):
    """inverse of ll_to_en (point on the ellipsoid, h = 0) -> (lat, lon) deg."""
    lat = ARP_LAT + n / MLAT; lon = ARP_LON + e / MLON
    for _ in range(12):
        e1, n1 = ll_to_en(lat, lon)
        de = e - e1; dn = n - n1
        lat += dn / MLAT; lon += de / MLON
        if abs(de) + abs(dn) < 1e-10: break
    return (lat, lon)


def ll_to_world(lat, lon):
    """NAD83(2011) lat/lon (FAA NASR, NAIP) -> world (x east, z south)."""
    e, n = ll_to_en(lat, lon); return (e, -n)


def world_to_ll(x, z):
    return en_to_ll(x, -z)


def wgs84_to_world(lat, lon):
    """WGS 84 (current realisation: ADS-B, OSM, GNSS) lat/lon -> world (x, z) in the NAD83(2011) frame."""
    e, n = ll_to_en(lat, lon)
    return (e - WGS84_MINUS_NAD83_E, -(n - WGS84_MINUS_NAD83_N))


def world_to_wgs84(x, z):
    return en_to_ll(x + WGS84_MINUS_NAD83_E, -z + WGS84_MINUS_NAD83_N)


# ---------------------------------------------------------------- UTM zone 10N (EPSG:26910), Krueger series order 6
UTM10_K0, UTM10_LON0, UTM10_FE, UTM10_FN = 0.9996, -123.0, 500000.0, 0.0
_N = GRS80_F / (2 - GRS80_F)
_E = math.sqrt(E2)
_n2, _n3, _n4, _n5, _n6 = _N ** 2, _N ** 3, _N ** 4, _N ** 5, _N ** 6
_TM_A = GRS80_A / (1 + _N) * (1 + _n2 / 4 + _n4 / 64 + _n6 / 256)   # rectifying radius
_ALPHA = (
    _N / 2 - 2 * _n2 / 3 + 5 * _n3 / 16 + 41 * _n4 / 180 - 127 * _n5 / 288 + 7891 * _n6 / 37800,
    13 * _n2 / 48 - 3 * _n3 / 5 + 557 * _n4 / 1440 + 281 * _n5 / 630 - 1983433 * _n6 / 1935360,
    61 * _n3 / 240 - 103 * _n4 / 140 + 15061 * _n5 / 26880 + 167603 * _n6 / 181440,
    49561 * _n4 / 161280 - 179 * _n5 / 168 + 6601661 * _n6 / 7257600,
    34729 * _n5 / 80640 - 3418889 * _n6 / 1995840,
    212378941 * _n6 / 319334400)
_BETA = (
    _N / 2 - 2 * _n2 / 3 + 37 * _n3 / 96 - _n4 / 360 - 81 * _n5 / 512 + 96199 * _n6 / 604800,
    _n2 / 48 + _n3 / 15 - 437 * _n4 / 1440 + 46 * _n5 / 105 - 1118711 * _n6 / 3870720,
    17 * _n3 / 480 - 37 * _n4 / 840 - 209 * _n5 / 4480 + 5569 * _n6 / 90720,
    4397 * _n4 / 161280 - 11 * _n5 / 504 - 830251 * _n6 / 7257600,
    4583 * _n5 / 161280 - 108847 * _n6 / 3991680,
    20648693 * _n6 / 638668800)


def ll_to_utm10(lat, lon):
    """NAD83 lat/lon (deg) -> UTM 10N (E, N) metres (EPSG:26910)."""
    phi = lat * D2R; lam = (lon - UTM10_LON0) * D2R
    tau = math.tan(phi)
    sig = math.sinh(_E * math.atanh(_E * tau / math.sqrt(1 + tau * tau)))
    taup = tau * math.sqrt(1 + sig * sig) - sig * math.sqrt(1 + tau * tau)
    xip = math.atan2(taup, math.cos(lam))
    etap = math.asinh(math.sin(lam) / math.sqrt(taup * taup + math.cos(lam) ** 2))
    xi = xip; eta = etap
    for j in range(1, 7):
        a = _ALPHA[j - 1]
        xi += a * math.sin(2 * j * xip) * math.cosh(2 * j * etap)
        eta += a * math.cos(2 * j * xip) * math.sinh(2 * j * etap)
    return (UTM10_FE + UTM10_K0 * _TM_A * eta, UTM10_FN + UTM10_K0 * _TM_A * xi)


def utm10_to_ll(E, N):
    """UTM 10N (E, N) metres (EPSG:26910) -> NAD83 lat/lon (deg)."""
    xi = (N - UTM10_FN) / (UTM10_K0 * _TM_A); eta = (E - UTM10_FE) / (UTM10_K0 * _TM_A)
    xip = xi; etap = eta
    for j in range(1, 7):
        b = _BETA[j - 1]
        xip -= b * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        etap -= b * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    taup = math.sin(xip) / math.sqrt(math.sinh(etap) ** 2 + math.cos(xip) ** 2)
    lam = math.atan2(math.sinh(etap), math.cos(xip))
    tau = taup
    for _ in range(8):                                  # Newton for tau from tau' (Karney 2011)
        sig = math.sinh(_E * math.atanh(_E * tau / math.sqrt(1 + tau * tau)))
        ti = tau * math.sqrt(1 + sig * sig) - sig * math.sqrt(1 + tau * tau)
        dt = (taup - ti) / math.sqrt(1 + ti * ti) * (1 + (1 - E2) * tau * tau) / ((1 - E2) * math.sqrt(1 + tau * tau))
        tau += dt
        if abs(dt) < 1e-14: break
    return (math.atan(tau) / D2R, UTM10_LON0 + lam / D2R)


def utm10_to_world(E, N):
    """NAIP / EPSG:26910 (E, N) -> world (x, z)."""
    return ll_to_world(*utm10_to_ll(E, N))


def world_to_utm10(x, z):
    return ll_to_utm10(*world_to_ll(x, z))


# --------------------------------------------------------------------------------------------- headings
def hdg_vec(h):
    """world (x, z) unit vector of a true heading (deg): [sin h, -cos h] (js hdgVec)."""
    return (math.sin(h * D2R), -math.cos(h * D2R))


def vec_hdg(dx, dz):
    return math.degrees(math.atan2(dx, -dz)) % 360


# --------------------------------------------------- FAA runway ends (identical to js/geo.js RWY_ENDS / RWY_DATA)
# FAA NASR APT_RWY_END.csv, cycle effective 2026-10-29 (refs/cache/faa/nasr_2026-10-29_HWD.json), all 4 ends surveyed
# "3RD PARTY SURVEY" 2023/07/05. Fields: lat/lon = LAT_DECIMAL / LONG_DECIMAL (NAD 83; they agree with the DMS fields to
# < 1 mm); elev = RWY_END_ELEV ft; disp = DISPLACED_THR_LEN ft (0 = none); thrLat/thrLon/thrElev = the surveyed displaced
# threshold (LAT/LONG_DISPLACED_THR_DECIMAL, DISPLACED_THR_ELEV ft; None = not displaced); tdzElev = TDZ_ELEV ft (highest
# elevation of the first 3000 ft of the landing surface); vgsi = VGSI_CODE (P4L = 4-box PAPI left, V4R / V4L = 4-box VASI
# right / left); gpa = VISUAL_GLIDE_PATH_ANGLE deg; tch = THR_CROSSING_HGT ft; marking = RWY_MARKING_TYPE_CODE (PIR
# precision, NPI non-precision); rhTraffic = RIGHT_HAND_TRAFFIC_PAT_FLAG == 'Y' (28L: the field is empty in NASR, read as
# the standard left-hand pattern, 14 CFR 91.126(b)(1) [inferred from the empty field; cross-check the Chart Supplement
# "RP" entry in Phase 1]); trueAln = TRUE_ALIGNMENT deg
# (NASR rounds to whole degrees); ils = ILS_TYPE; reil = RWY_END_LGTS_FLAG == 'Y' (runway end identifier lights);
# brg = geodesic forward azimuth (deg true, GRS80) from this end to the opposite end, pyproj 3.8.0 Geod.inv on the NASR
# decimals (computed 2026-11-12; checked by the test to 1e-4 deg).
RWY_ENDS = {
    '10L': dict(lat=37.66247844, lon=-122.12726369, elev=28.1, disp=0, thrLat=None, thrLon=None, thrElev=None,
                tdzElev=36.9, vgsi='P4L', gpa=3.0, tch=29, marking='NPI', rhTraffic=False, trueAln=120, ils=None,
                reil=False, brg=119.85699),
    '28R': dict(lat=37.65822866, lon=-122.11795213, elev=37.1, disp=0, thrLat=None, thrLon=None, thrElev=None,
                tdzElev=37.2, vgsi='P4L', gpa=3.0, tch=44, marking='NPI', rhTraffic=True, trueAln=300, ils=None,
                reil=False, brg=299.86268),
    '10R': dict(lat=37.66204722, lon=-122.12979350, elev=27.7, disp=826, thrLat=37.66091861, thrLon=-122.12731986,
                thrElev=29.3, tdzElev=41.7, vgsi='V4R', gpa=3.0, tch=25, marking='PIR', rhTraffic=True, trueAln=120,
                ils=None, reil=True, brg=119.85159),
    '28L': dict(lat=37.65426300, lon=-122.11273616, elev=52.1, disp=676, thrLat=37.65518672, thrLon=-122.11475980,
                thrElev=50.0, tdzElev=50.0, vgsi='V4L', gpa=4.0, tch=35, marking='PIR', rhTraffic=False, trueAln=300,
                ils='LOC/DME', reil=True, brg=299.86201),
}
# FAA NASR APT_RWY.csv (same cycle): RWY_LEN / RWY_WIDTH ft (length 3RD PARTY SURVEY 2023/07/05), SURFACE_TYPE_CODE,
# TREATMENT_CODE, COND, RWY_LGT_CODE (MED = medium-intensity edge lights, MIRL), GROSS_WT_SW / _DW (x 1000 lb).
RWY_DATA = {
    '10L/28R': dict(ends=('10L', '28R'), lenFt=3108, widthFt=75, surface='ASPH', treatment='NONE', cond='GOOD',
                    lights='MED', gwSW=13, gwDW=None),
    '10R/28L': dict(ends=('10R', '28L'), lenFt=5694, widthFt=150, surface='ASPH', treatment='GRVD', cond='EXCELLENT',
                    lights='MED', gwSW=30, gwDW=75),
}
RWY_PAIRS = (('10L', '28R'), ('10R', '28L'))
_OPP = {a: b for a, b in RWY_PAIRS}; _OPP.update({b: a for a, b in RWY_PAIRS})


def end_en(name):
    E = RWY_ENDS[name]; return ll_to_en(E['lat'], E['lon'])


def end_world(name):
    E = RWY_ENDS[name]; return ll_to_world(E['lat'], E['lon'])


def rwy_axis(name):
    """axis of the runway used from end `name`: origin = that end, dir = unit vector toward the opposite end,
    right = unit vector to the right of dir (pilot's right on take-off / landing from `name`), all world (x, z);
    length = end-to-end plane length (m); hdg = plane heading of dir (deg true at the ARP meridian)."""
    a = end_world(name); b = end_world(_OPP[name])
    dx = b[0] - a[0]; dz = b[1] - a[1]; L = math.hypot(dx, dz)
    d = (dx / L, dz / L)
    return dict(end=name, opp=_OPP[name], origin=a, dir=d, right=(-d[1], d[0]), length=L, hdg=vec_hdg(dx, dz))


def rwy_along_across(name, x, z):
    """world (x, z) -> (along, across) metres: along from end `name` toward the opposite end, across > 0 to the right."""
    A = rwy_axis(name); px = x - A['origin'][0]; pz = z - A['origin'][1]
    return (px * A['dir'][0] + pz * A['dir'][1], px * A['right'][0] + pz * A['right'][1])


def rwy_to_world(name, along, across=0.0):
    A = rwy_axis(name)
    return (A['origin'][0] + along * A['dir'][0] + across * A['right'][0],
            A['origin'][1] + along * A['dir'][1] + across * A['right'][1])


def thr_world(name):
    """landing threshold (x, z): the surveyed NASR displaced threshold if any (it lies on the axis to 1 mm), else the end."""
    E = RWY_ENDS[name]
    return ll_to_world(E['thrLat'], E['thrLon']) if E['thrLat'] is not None else end_world(name)


def thr_disp_m(name):
    """displacement (m) of the landing threshold along the axis, from the surveyed position (NASR DISPLACED_THR_LEN
    rounds to whole ft; the surveyed points give 825.63 ft for 10R (826) and 675.56 ft for 28L (676))."""
    return rwy_along_across(name, *thr_world(name))[0] if RWY_ENDS[name]['thrLat'] is not None else 0.0


def rwy_profile(name):
    """NASR surveyed surface points along the runway used from `name`: [(along m, y m), ...] ascending along:
    the two ends and any displaced thresholds."""
    opp = _OPP[name]; L = rwy_axis(name)['length']; pts = [(0.0, RWY_ENDS[name]['elev'] * FT)]
    if RWY_ENDS[name]['thrLat'] is not None: pts.append((thr_disp_m(name), RWY_ENDS[name]['thrElev'] * FT))
    if RWY_ENDS[opp]['thrLat'] is not None: pts.append((L - thr_disp_m(opp), RWY_ENDS[opp]['thrElev'] * FT))
    pts.append((L, RWY_ENDS[opp]['elev'] * FT))
    return sorted(pts)


def rwy_surface_y(name, along):
    """runway surface y (m NAVD 88) at `along` metres from end `name`: linear between the NASR surveyed points
    (exact at the points, [inferred] between them - e.g. 10R TDZ_ELEV 41.7 ft says the profile is not linear)."""
    P = rwy_profile(name)
    if along <= P[0][0]: return P[0][1]
    for (a0, y0), (a1, y1) in zip(P, P[1:]):
        if along <= a1: return y0 + (y1 - y0) * (along - a0) / (a1 - a0)
    return P[-1][1]


def _runway(a, b):
    D = RWY_DATA[f'{a}/{b}']; A = rwy_axis(a)
    return dict(id=f'{a}/{b}', ends=(a, b), a=end_world(a), b=end_world(b), width=D['widthFt'] * FT,
                length=A['length'], lengthNasr=D['lenFt'] * FT, hdgA=A['hdg'],
                dispA=thr_disp_m(a), dispB=thr_disp_m(b), elevA=RWY_ENDS[a]['elev'] * FT, elevB=RWY_ENDS[b]['elev'] * FT)


RUNWAYS = [_runway(a, b) for a, b in RWY_PAIRS]


# --------------------------------------------------------------------------------------------- numpy conveniences
def np_map(fn, X, Z):
    """apply a scalar (a, b) -> (c, d) function elementwise to array-likes (returns two numpy arrays)."""
    import numpy as np
    X = np.asarray(X, float); Z = np.asarray(Z, float)
    out = np.array([fn(float(a), float(b)) for a, b in zip(X.ravel(), Z.ravel())]).reshape(X.shape + (2,)) if X.size else np.zeros(X.shape + (2,))
    return out[..., 0], out[..., 1]


def ll_to_world_np(lat, lon):
    """vectorised ll_to_world (same formulas; numpy float64)."""
    import numpy as np
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    sl = np.sin(lat * D2R); cl = np.cos(lat * D2R)
    N = GRS80_A / np.sqrt(1 - E2 * sl * sl)
    dx = N * cl * np.cos(lon * D2R) - _O[0]; dy = N * cl * np.sin(lon * D2R) - _O[1]; dz = N * (1 - E2) * sl - _O[2]
    e = -_SL * dx + _CL * dy; n = -_S0 * _CL * dx - _S0 * _SL * dy + _C0 * dz
    return e, -n


def world_to_ll_np(x, z):
    import numpy as np
    x = np.asarray(x, float); z = np.asarray(z, float)
    lat = ARP_LAT + (-z) / MLAT; lon = ARP_LON + x / MLON
    for _ in range(12):
        X1, Z1 = ll_to_world_np(lat, lon)
        de = x - X1; dn = -(z - Z1)
        lat = lat + dn / MLAT; lon = lon + de / MLON
        if float(np.max(np.abs(de) + np.abs(dn), initial=0.0)) < 1e-10: break
    return lat, lon


def wgs84_to_world_np(lat, lon):
    x, z = ll_to_world_np(lat, lon)
    return x - WGS84_MINUS_NAD83_E, z + WGS84_MINUS_NAD83_N


def ll_to_utm10_np(lat, lon):
    """vectorised ll_to_utm10 (same series)."""
    import numpy as np
    phi = np.asarray(lat, float) * D2R; lam = (np.asarray(lon, float) - UTM10_LON0) * D2R
    tau = np.tan(phi)
    sig = np.sinh(_E * np.arctanh(_E * tau / np.sqrt(1 + tau * tau)))
    taup = tau * np.sqrt(1 + sig * sig) - sig * np.sqrt(1 + tau * tau)
    xip = np.arctan2(taup, np.cos(lam)); etap = np.arcsinh(np.sin(lam) / np.sqrt(taup * taup + np.cos(lam) ** 2))
    xi = xip.copy(); eta = etap.copy()
    for j in range(1, 7):
        a = _ALPHA[j - 1]
        xi = xi + a * np.sin(2 * j * xip) * np.cosh(2 * j * etap)
        eta = eta + a * np.cos(2 * j * xip) * np.sinh(2 * j * etap)
    return UTM10_FE + UTM10_K0 * _TM_A * eta, UTM10_FN + UTM10_K0 * _TM_A * xi


def utm10_to_ll_np(E, N):
    import numpy as np
    xi = (np.asarray(N, float) - UTM10_FN) / (UTM10_K0 * _TM_A); eta = (np.asarray(E, float) - UTM10_FE) / (UTM10_K0 * _TM_A)
    xip = xi.copy(); etap = eta.copy()
    for j in range(1, 7):
        b = _BETA[j - 1]
        xip = xip - b * np.sin(2 * j * xi) * np.cosh(2 * j * eta)
        etap = etap - b * np.cos(2 * j * xi) * np.sinh(2 * j * eta)
    taup = np.sin(xip) / np.sqrt(np.sinh(etap) ** 2 + np.cos(xip) ** 2)
    lam = np.arctan2(np.sinh(etap), np.cos(xip))
    tau = taup.copy()
    for _ in range(8):
        sig = np.sinh(_E * np.arctanh(_E * tau / np.sqrt(1 + tau * tau)))
        ti = tau * np.sqrt(1 + sig * sig) - sig * np.sqrt(1 + tau * tau)
        dt = (taup - ti) / np.sqrt(1 + ti * ti) * (1 + (1 - E2) * tau * tau) / ((1 - E2) * np.sqrt(1 + tau * tau))
        tau = tau + dt
        if float(np.max(np.abs(dt), initial=0.0)) < 1e-14: break
    return np.arctan(tau) / D2R, UTM10_LON0 + lam / D2R


def utm10_to_world_np(E, N):
    """vectorised utm10_to_world (NAIP pixel centres -> world)."""
    return ll_to_world_np(*utm10_to_ll_np(E, N))


def world_to_utm10_np(x, z):
    return ll_to_utm10_np(*world_to_ll_np(x, z))
