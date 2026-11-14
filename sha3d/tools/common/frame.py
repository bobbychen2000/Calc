"""World frame of SHA Live 3D (Shanghai Hongqiao, ZSSS / SHA): WGS 84 lat/lon <-> local metres, and the height chain.

Pattern: sfo3d js/geo.js + tools/geo_frame.py and hwd3d tools/common/hwd_frame.py (both read, not imported). Kept: the
frame design (exact local tangent plane on the ellipsoid at a fixed origin, x east / y up / z south, metres, flat world),
ll_to_en / en_to_ll with a fixed-Jacobian Newton inverse, hdg_vec / vec_hdg. Changed: origin (owner decision OD0),
ellipsoid and datum (WGS 84 throughout: no NAD83 shift), frame id, the vertical chain (AIP heights, EGM2008, ellipsoid).
Stdlib only, so that a JS twin (js/geo.js, Phase 2) can copy it constant for constant; tools/common/test_frame.py checks
it against pyproj and against the pinned OSM origin nodes.

World frame (FRAME_ID 'ltp-wgs84-zsss')
--------------------------------------
* Axes as sfo3d: x = east, z = south, y = up, metres.
* Origin (OD0, docs/PLAN.md s.6a): the midpoint of the two end nodes of OSM way 16714125 (runway 18L/36R, the centre of
  RWY 18L/36R, which is how the AIP defines the ARP), taken as the arithmetic mean of the node coordinates:
  N end node 31.2131135 N 121.3354641 E, S end node 31.1825842 N 121.3371157 E -> 31.19784885 N, 121.3362899 E
  (exact; no rounding). The geodesic midpoint of the same two nodes lies 13 mm away (test_frame.py), so the choice
  of "midpoint" does not matter. The origin only defines the metre grid: every feature keeps its WGS 84 coordinates
  and is placed from them.
* Datum: WGS 84, as delivered by OSM, Sentinel-2 / Earth Search (UTM 51N on WGS 84), Umbra GEC and ADS-B. No datum
  shift is applied. Not modelled [inf]: the difference between the WGS 84 realisation of each source and the PRC
  datum CGCS2000 (= ITRF97 at epoch 2000.0). For a fixed point at ZSSS this is the plate motion since 2000.0, about
  0.78 m (0.72 m east, 0.29 m south by 2026.87; PROJ ITRF2014:EURA plate-motion model, computed in test_frame.py; the South China block's own motion relative
  to stable Eurasia is not included) - only relevant if surveyed CGCS2000 coordinates (e.g. AIP THR coordinates, not
  published for ZSSS: "Nil") are ever mixed in.
* Projection: exact local tangent plane (ENU) on the WGS 84 ellipsoid at the origin, at ellipsoidal height 0:
  (lat, lon, h=0) -> ECEF -> east/north at the origin. Flat world: a point at height y is drawn at y above its ground
  point, so the horizontal position never depends on height.
  Errors (measured in test_frame.py against pyproj 3.8.0 / PROJ 9.8.1):
    - identical to PROJ's +proj=topocentric (east/north) to < 1e-6 m;
    - plane distance from the origin vs the WGS 84 geodesic distance: 0.5 mm short at 5 km (d^3 / 6R^2), 0.5 m at
      50 km; the plane is conformal to second order, so shapes and headings are exact at airport scale;
    - the inverse en_to_ll round-trips to < 1e-8 m (float64 floor at ECEF scale);
    - not represented (flat world): the curvature drop of the ellipsoid below the tangent plane, d^2 / 2R = 1.96 m at
      5 km. A distant aircraft is therefore drawn about 2 m (at 5 km) higher than its true geometric direction
      from the origin; this matters only for line-of-sight tests at long range, not for anything on the airfield.
  For comparison, the "111320 m per degree" equirectangular shortcut is 0.40 % long north-south and 0.09 % short
  east-west here (6.8 m north-south at the runway ends) - never use it.

Height chain (y)
----------------
y = height in metres in the AIP's height datum, i.e. numerically the AIP elevations. The AIP (mirror, EFF 2026-07-08,
AD 2.2/2.12) gives AD ELEV 3.0 m and THR / DTHR / TDZ elevations 2.0-2.8 m, and states no datum ("Geoid undulation at
AD ELEV PSN": blank). That the datum is Shanghai's local Wusong height (H_Wusong = H_1985 + 1.680 m, Shanghai planning
bureau notice 2022, docs/phase0/terrain.md row 16) is inferred, not verified.
* FIELD_ELEV_Y = 3.0 (AD ELEV, AIP mirror).
* GROUND_Y = 2.5: NOMINAL flat ground for code without a terrain model = the mean of the eight AIP runway points
  (THR and DTHR of 18L, 36R, 18R, 36L: 2.1 2.0 2.7 2.6 2.6 2.6 2.6 2.7 -> 2.49 m) [inf]. Against those points it is
  0.5 m too high at DTHR 18L and 0.2 m too low at THR 36R / DTHR 36L. Use rwy_profile_y() on the runways.
* Copernicus GLO-30 DEM (EGM2008 heights) -> y: y = H_EGM2008 + K_DEM, K_DEM = +1.30 m: the mean of (AIP elevation -
  DEM) at the eight AIP runway points, sd 0.27 m, n = 8 [obs; all eight DEM samples lie on WorldDEM airport-edited
  planes (EDM code 5) of 1.0 / 1.5 m, and the tile's absolute LE90 is 1.92 m, so K_DEM is only good to about +-2 m].
  Read the other way, if the AIP is Wusong then EGM2008 heights ~ H_1985 + 0.4 m here (1.680 - 1.30) [inf].
* EGM2008 -> ellipsoid: h_WGS84 = H_EGM2008 + N, N = +11.267 m at the origin (bilinear in the NGA 2.5' grid
  us_nga_egm08_25.tif from cdn.proj.org, public domain; terrain.md gave 11.24 at the nearest node). Over the detailed
  extent N varies 11.07-11.47 m; geoid_n(x, z) is a plane fit to the grid, good to 4 mm within +-4 km.
* Hence the ellipsoidal (GNSS / ADS-B alt_geom) height of a world point: h = y - K_DEM + N(x, z) ~ y + 9.97 m at the
  origin. The field (AD ELEV 3.0 m) is at h ~ 12.97 m HAE. (If the AIP is Wusong and EGM2008 equalled the 1985 datum,
  h = y - 1.680 + N would give 9.59 m: the 0.38 m difference is far inside the DEM's +-2 m.)
* Barometric: ATC QNH altitudes are referenced to the aerodrome elevation, so an altitude on QNH ~ y (in metres).
  ADS-B alt_baro is pressure altitude (1013.25 hPa): y_from_pressure_alt() applies a QNH with the ISA lapse rate.
"""
import math

# --------------------------------------------------------------------------------------------------------- constants
FRAME_ID = 'ltp-wgs84-zsss'
ORIGIN_LAT, ORIGIN_LON = 31.19784885, 121.3362899   # OD0: midpoint of OSM way 16714125's end nodes (see header)
ORIGIN_NODES = {'n': ('node', 3336195147, 31.2131135, 121.3354641), 's': ('node', 13556389849, 31.1825842, 121.3371157)}
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
E2 = WGS84_F * (2 - WGS84_F)
D2R = math.pi / 180

# vertical (see header)
Y_REF = ('AIP height datum (metres, AIP mirror AD 2.2 / 2.12; datum not stated; Shanghai Wusong height inferred: '
         'H_Wusong = H_1985 + 1.680 m)')
FIELD_ELEV_Y = 3.0
GROUND_Y = 2.5
AIP_RWY_POINTS = {   # AIP (mirror) AD 2.12 column 6 "THR elevation", m; thr = runway end, dthr = displaced threshold
    '18L': dict(thr=2.1, dthr=2.0, tdz=2.3), '36R': dict(thr=2.7, dthr=2.6, tdz=2.8),
    '18R': dict(thr=2.6, dthr=2.6, tdz=2.6), '36L': dict(thr=2.6, dthr=2.7, tdz=2.6)}
K_DEM = 1.30          # y - H_EGM2008 (Copernicus GLO-30), measured at the 8 AIP runway points [obs, +-2 m]
K_DEM_SD = 0.27
WUSONG_MINUS_1985 = 1.680
GEOID_N0 = 11.267     # EGM2008 undulation at the origin (bilinear, NGA 2.5' grid)
GEOID_DN_DX = 4.184e-5   # m per m east   (plane fit over +-4 km, max residual 4 mm)
GEOID_DN_DZ = 8.77e-6    # m per m south  (= -dN/dnorth; N decreases northward by 8.77e-6 m/m)


def _ecef(lat, lon, h=0.0):
    sl = math.sin(lat * D2R); cl = math.cos(lat * D2R)
    N = WGS84_A / math.sqrt(1 - E2 * sl * sl)
    return ((N + h) * cl * math.cos(lon * D2R), (N + h) * cl * math.sin(lon * D2R), (N * (1 - E2) + h) * sl)


_O = _ecef(ORIGIN_LAT, ORIGIN_LON)
_S0 = math.sin(ORIGIN_LAT * D2R); _C0 = math.cos(ORIGIN_LAT * D2R)
_SL = math.sin(ORIGIN_LON * D2R); _CL = math.cos(ORIGIN_LON * D2R)
_W0 = math.sqrt(1 - E2 * _S0 * _S0)
MLAT = WGS84_A * (1 - E2) / (_W0 ** 3) * D2R      # metres per degree of latitude at the origin (meridian radius)
MLON = WGS84_A / _W0 * _C0 * D2R                    # metres per degree of longitude at the origin


def ll_to_en(lat, lon):
    """WGS 84 lat/lon (deg) -> (east, north) metres in the tangent plane at the origin."""
    x, y, z = _ecef(lat, lon)
    dx = x - _O[0]; dy = y - _O[1]; dz = z - _O[2]
    return (-_SL * dx + _CL * dy, -_S0 * _CL * dx - _S0 * _SL * dy + _C0 * dz)


def ll_to_enu(lat, lon, h=0.0):
    """full ENU incl. up (for checks only; the world is flat - see header)."""
    x, y, z = _ecef(lat, lon, h)
    dx = x - _O[0]; dy = y - _O[1]; dz = z - _O[2]
    return (-_SL * dx + _CL * dy, -_S0 * _CL * dx - _S0 * _SL * dy + _C0 * dz,
            _C0 * _CL * dx + _C0 * _SL * dy + _S0 * dz)


def en_to_ll(e, n):
    """inverse of ll_to_en (point on the ellipsoid, h = 0) -> (lat, lon) deg; fixed-Jacobian Newton, < 1e-8 m."""
    lat = ORIGIN_LAT + n / MLAT; lon = ORIGIN_LON + e / MLON
    for _ in range(12):
        e1, n1 = ll_to_en(lat, lon)
        de = e - e1; dn = n - n1
        lat += dn / MLAT; lon += de / MLON
        if abs(de) + abs(dn) < 1e-10:
            break
    return (lat, lon)


def ll_to_world(lat, lon):
    """WGS 84 lat/lon -> world (x east, z south) metres."""
    e, n = ll_to_en(lat, lon)
    return (e, -n)


def world_to_ll(x, z):
    return en_to_ll(x, -z)


# --------------------------------------------------------------------------------------------- headings
def hdg_vec(h):
    """world (x, z) unit vector of a true heading (deg): [sin h, -cos h]."""
    return (math.sin(h * D2R), -math.cos(h * D2R))


def vec_hdg(dx, dz):
    return math.degrees(math.atan2(dx, -dz)) % 360


# --------------------------------------------------------------------------------------------- heights
def geoid_n(x=0.0, z=0.0):
    """EGM2008 geoid undulation N (m) at world (x, z): plane fit to the NGA 2.5' grid, +-4 mm within 4 km."""
    return GEOID_N0 + GEOID_DN_DX * x + GEOID_DN_DZ * z


def y_from_egm2008(H):
    """Copernicus DEM / EGM2008 orthometric height -> world y (AIP datum) [K_DEM obs, +-2 m]."""
    return H + K_DEM


def egm2008_from_y(y):
    return y - K_DEM


def hae_from_y(y, x=0.0, z=0.0):
    """world y -> WGS 84 ellipsoidal height (GNSS, ADS-B alt_geom), metres."""
    return y - K_DEM + geoid_n(x, z)


def y_from_hae(h, x=0.0, z=0.0):
    return h + K_DEM - geoid_n(x, z)


def y_from_pressure_alt(alt_ft, qnh_hpa):
    """ADS-B alt_baro (pressure altitude, ft, 1013.25 hPa) -> world y (m) using a QNH (hPa) and the ISA troposphere.
    Altitude on QNH ~ height above the AIP datum (QNH is referenced to the aerodrome elevation) [inf]."""
    hp = alt_ft * 0.3048
    # ISA: p(hp) = 1013.25 (1 - hp / 44330.77)^5.25588 ; altitude on QNH = 44330.77 (1 - (p / QNH)^(1/5.25588))
    p = 1013.25 * (1 - hp / 44330.77) ** 5.25588
    return 44330.77 * (1 - (p / qnh_hpa) ** (1 / 5.25588))


# --------------------------------------------------------------------------------------------- JSON frame block
def frame_block():
    """The constants a JS twin needs (written into data/sha_airport.json 'frame')."""
    return {
        'id': FRAME_ID,
        'origin_wgs84': [ORIGIN_LAT, ORIGIN_LON],
        'origin_def': ('OD0: midpoint (arithmetic mean of lat/lon) of the end nodes of OSM way 16714125 (RWY 18L/36R): '
                       'node 3336195147 31.2131135 N 121.3354641 E (v3) and node 13556389849 31.1825842 N 121.3371157 E (v1); '
                       '= centre of RWY 18L/36R, the AIP ARP definition. The AIP ARP itself is printed as '
                       'N31 11.8 E121 20.1 (0.1 min, AIP mirror)'),
        'axes': 'x = east (m), z = south (m), y = up (m); world unit vector of true heading h = (sin h, -cos h)',
        'ellipsoid': {'name': 'WGS 84', 'a': WGS84_A, 'inv_f': 298.257223563},
        'projection': ('exact local tangent plane (ENU) on the WGS 84 ellipsoid at the origin, h = 0: lat/lon -> ECEF '
                       '-> east/north; flat world (y is height above the ground point). Plane vs geodesic distance '
                       '< 0.5 mm within 5 km; curvature drop not drawn (1.96 m at 5 km)'),
        'm_per_deg_lat': round(MLAT, 4), 'm_per_deg_lon': round(MLON, 4),
        'datum_note': ('all inputs are WGS 84 (OSM, Sentinel-2, Umbra, ADS-B); no shift applied. CGCS2000 differs for a '
                       'fixed point by the plate motion since 2000.0 (0.78 m, ITRF2014:EURA model) [inf], not modelled'),
        'y': Y_REF,
        'field_elev_y': FIELD_ELEV_Y,
        'ground_y_nominal': GROUND_Y,
        'ground_y_note': ('nominal flat ground for code without terrain = mean of the 8 AIP (mirror) THR/DTHR '
                          'elevations, 2.49 m [inf]; use the runway profiles on runways'),
        'k_dem_m': K_DEM, 'k_dem_sd_m': K_DEM_SD,
        'k_dem_note': ('y = H_EGM2008 (Copernicus GLO-30 DEM) + k_dem; measured at the 8 AIP runway points (all on '
                       'WorldDEM airport-edited planes) [obs]; DEM LE90 1.92 m, so +-2 m'),
        'geoid_egm2008': {'n0_m': GEOID_N0, 'dn_dx': GEOID_DN_DX, 'dn_dz': GEOID_DN_DZ,
                          'note': 'N(x,z) = n0 + dn_dx*x + dn_dz*z (plane fit to NGA us_nga_egm08_25.tif, +-4 mm '
                                  'within 4 km); h_WGS84 = y - k_dem + N'},
        'hae_minus_y_at_origin_m': round(GEOID_N0 - K_DEM, 3),
        'wusong_minus_1985_m': WUSONG_MINUS_1985,
        'qnh_note': 'altitude on QNH ~ y; ADS-B alt_baro needs QNH (frame.y_from_pressure_alt, ISA) [inf]',
        'ring_convention': 'polygon rings are lists of [x, z]; open (first vertex not repeated)',
        'code': 'tools/common/frame.py (stdlib; tools/common/test_frame.py checks it against pyproj)',
    }
