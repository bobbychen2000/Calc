"""World frame of SFO Live 3D - the Python twin of js/geo.js (keep the two identical; test: tools/test_geo_frame.py).

World frame (frame id 'ltp-nad83-2011', since 24 Sep 2026)
------------------------------------------------------------
* x = east, z = south, y = up, metres. Origin = FAA airport reference point (ARP).
* Datum: **NAD83(2011)** - the datum of the FAA NASR coordinates ("All US coordinate information provided currently
  references NAD 83", FAA NASR CSV_README.pdf, cycle 2026-09-03; the realisation is not stated, NAD83(2011) inferred
  from the 0.3 m agreement with NAIP, docs/research/imagery.md s.3), of USDA NAIP (EPSG:26910) and of the SFO Museum
  geometry as used here.
* Projection: the exact **local tangent plane (ENU) on the GRS80 ellipsoid** at the ARP, evaluated at ellipsoidal
  height 0: (lat, lon) -> ECEF -> rotate into east/north/up at the ARP -> keep (east, north). The world is flat:
  aircraft at altitude h are drawn at y = h above their ground point, so the horizontal position never depends on h.
  Scale error vs. geodesic distance: < 0.1 mm within 5 km of the ARP, 0.5 m at 50 km (d^3 / 6R^2).
* The inverse (world -> lat/lon) is a fixed-Jacobian Newton iteration (exact local m/deg at the ARP) to < 1e-9 m.

ARP: FAA NASR APT_BASE.csv (cycle 2026-09-03) SFO: 37-37-07.7000N 122-22-31.5000W (LAT_DECIMAL 37.61880555,
LONG_DECIMAL -122.37541666), position source 3RD PARTY SURVEY 2014/10/22. The constants below are those decimals
rounded to 1e-7 deg (< 0.5 mm) and are kept unchanged from the legacy frame so the origin does not move.

WGS 84 inputs (ADS-B, OSM, GNSS): NAD83(2011) -> WGS 84 (G2296) = ITRF2020 at SFO, epoch 2026.73, is a displacement of
dE = -1.568 m, dN = +0.159 m (1.576 m toward azimuth 276 deg; vertical -0.506 m). Verified with pyproj 3.7.2 / PROJ
9.5.1, EPSG transformation "ITRF2020 to NAD83(2011) (1)" (time-dependent Helmert) followed by "WGS 84 (G2296) to
ITRF2020"; WGS 84 (G2139)/ITRF2014 give -1.568 / +0.160. Rate: -1.36 cm/yr east, -1.32 cm/yr north. Spatial
variation: < 1 mm within 5 km, < 1.1 cm within 50 km. PROJ's *default* EPSG:4269/6318 -> EPSG:4326 is a null
transformation - never let a tool apply it silently. Not modelled: intraplate (Bay Area) motion since 2010.0
(NGS HTDP not available here; order 0.2-0.4 m NW, [unverified]).
  wgs84_to_world: project the WGS 84 lat/lon through the same plane, then x += 1.568, z += 0.159.

Legacy frame (frame id 'equirect-v1', everything before 24 Sep 2026)
--------------------------------------------------------------------
x = (lon - lon0) * 111320 * cos(lat0), z = -(lat - lat0) * 110990: a spherical equirectangular approximation that is
0.124 % short east-west (3.4 m over runway 10L/28R). All hand-measured world/grid coordinates made before the switch
(tools/sat/stand_defs.py, tools/sat/work/*.json, reg.json registrations) are in this frame and are converted with
legacy_to_world() = ll_to_world(legacy_world_to_ll()), which is exact (docs/research/imagery.md s.4.4).
"""
import math

# --------------------------------------------------------------------------------------------------------- constants
FRAME_ID = 'ltp-nad83-2011'
ARP_LAT, ARP_LON = 37.6188056, -122.3754167            # FAA NASR ARP (see header)
GRS80_A = 6378137.0
GRS80_F = 1 / 298.257222101
E2 = GRS80_F * (2 - GRS80_F)
D2R = math.pi / 180
FT = 0.3048

# NAD83(2011) -> WGS 84 (G2296) displacement of a fixed ground point at SFO, epoch 2026.73 (see header)
WGS84_EPOCH = 2026.73
WGS84_MINUS_NAD83_E = -1.568
WGS84_MINUS_NAD83_N = +0.159


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
    """NAD83(2011) lat/lon -> world (x east, z south)."""
    e, n = ll_to_en(lat, lon); return (e, -n)


def world_to_ll(x, z):
    return en_to_ll(x, -z)


def wgs84_to_world(lat, lon):
    """WGS 84 (current realisation, e.g. ADS-B / OSM) lat/lon -> world (x, z) in the NAD83(2011) frame."""
    e, n = ll_to_en(lat, lon)
    return (e - WGS84_MINUS_NAD83_E, -(n - WGS84_MINUS_NAD83_N))


def world_to_wgs84(x, z):
    return en_to_ll(x + WGS84_MINUS_NAD83_E, -z + WGS84_MINUS_NAD83_N)


# ------------------------------------------------------------------------ FAA runway ends (identical to js/geo.js)
def dms(d, m): return d + m / 60.0


# FAA NASR APT_RWY_END.csv cycle 2026-09-03 = AirNav (degrees-decimal-minutes), NAD83; elevations ft; displaced ft
RWY_ENDS = {
    '10L': dict(lat=dms(37, 37.724323), lon=-dms(122, 23.603512), elev=5.5, disp=0),
    '28R': dict(lat=dms(37, 36.812017), lon=-dms(122, 21.428467), elev=13.0, disp=300),
    '10R': dict(lat=dms(37, 37.577467), lon=-dms(122, 23.586327), elev=7.1, disp=0),
    '28L': dict(lat=dms(37, 36.702717), lon=-dms(122, 21.500950), elev=12.6, disp=300),
    '1L': dict(lat=dms(37, 36.473872), lon=-dms(122, 22.975710), elev=10.7, disp=640),
    '19R': dict(lat=dms(37, 37.588882), lon=-dms(122, 22.236565), elev=9.2, disp=0),
    '1R': dict(lat=dms(37, 36.379793), lon=-dms(122, 22.862445), elev=11.4, disp=560),
    '19L': dict(lat=dms(37, 37.640532), lon=-dms(122, 22.026650), elev=10.5, disp=0),
}
RWY_PAIRS = (('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L'))


def end_world(name):
    E = RWY_ENDS[name]; return ll_to_world(E['lat'], E['lon'])


# --------------------------------------------------------- airport grid (s along 10L->28R, t along +90 deg left)
def _grid(fwd):
    a = fwd(RWY_ENDS['10L']['lat'], RWY_ENDS['10L']['lon']); b = fwd(RWY_ENDS['28R']['lat'], RWY_ENDS['28R']['lon'])
    h = math.atan2(b[0] - a[0], b[1] - a[1])
    return (math.sin(h), math.cos(h)), (math.sin(h - math.pi / 2), math.cos(h - math.pi / 2)), math.degrees(h)


V, U, HDG_S = _grid(ll_to_en)          # (e, n) unit vectors; HDG_S = true heading of +s (10 -> 28)


def st_to_world(s, t):
    e = s * V[0] + t * U[0]; n = s * V[1] + t * U[1]; return (e, -n)


def world_to_st(x, z):
    e, n = x, -z; return (e * V[0] + n * V[1], e * U[0] + n * U[1])


def hdg_vec(h):
    """world (x, z) unit vector of a true heading (deg): [sin h, -cos h] (js hdgVec)."""
    return (math.sin(h * D2R), -math.cos(h * D2R))


def vec_hdg(dx, dz):
    return math.degrees(math.atan2(dx, -dz)) % 360


# ------------------------------------------------------------------------------------ legacy frame (equirect-v1)
LEGACY_MLAT = 110990.0
LEGACY_MLON = 111320.0 * math.cos(math.radians(ARP_LAT))


def legacy_ll_to_world(lat, lon):
    return ((lon - ARP_LON) * LEGACY_MLON, -((lat - ARP_LAT) * LEGACY_MLAT))


def legacy_world_to_ll(x, z):
    return (ARP_LAT + (-z) / LEGACY_MLAT, ARP_LON + x / LEGACY_MLON)


LEGACY_V, LEGACY_U, LEGACY_HDG_S = _grid(lambda la, lo: (lambda w: (w[0], -w[1]))(legacy_ll_to_world(la, lo)))


def legacy_st_to_legacy_world(s, t):
    e = s * LEGACY_V[0] + t * LEGACY_U[0]; n = s * LEGACY_V[1] + t * LEGACY_U[1]; return (e, -n)


def legacy_world_to_legacy_st(x, z):
    e, n = x, -z; return (e * LEGACY_V[0] + n * LEGACY_V[1], e * LEGACY_U[0] + n * LEGACY_U[1])


def legacy_to_world(x, z):
    """legacy world (x, z) -> world (x, z); exact: legacy inverse -> NAD83 lat/lon -> LTP."""
    return ll_to_world(*legacy_world_to_ll(x, z))


def world_to_legacy(x, z):
    return legacy_ll_to_world(*world_to_ll(x, z))


def legacy_hdg_to_hdg(x, z, hdg, step=10.0):
    """a true heading measured in the legacy frame at legacy point (x, z) -> the same physical direction in the world
    frame (maps a 10 m step through the exact point mapping)."""
    d = hdg_vec(hdg)
    p0 = legacy_to_world(x, z); p1 = legacy_to_world(x + d[0] * step, z + d[1] * step)
    return vec_hdg(p1[0] - p0[0], p1[1] - p0[1])


def legacy_st_to_st(s, t):
    return world_to_st(*legacy_to_world(*legacy_st_to_legacy_world(s, t)))


def st_to_legacy_st(s, t):
    return legacy_world_to_legacy_st(*world_to_legacy(*st_to_world(s, t)))


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


def legacy_to_world_np(x, z):
    import numpy as np
    x = np.asarray(x, float); z = np.asarray(z, float)
    return ll_to_world_np(ARP_LAT + (-z) / LEGACY_MLAT, ARP_LON + x / LEGACY_MLON)


def world_to_legacy_np(x, z):
    lat, lon = world_to_ll_np(x, z)
    return (lon - ARP_LON) * LEGACY_MLON, -((lat - ARP_LAT) * LEGACY_MLAT)
