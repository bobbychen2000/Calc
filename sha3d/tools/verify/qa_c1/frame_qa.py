import sys, json, math, random
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import frame as F
import numpy as np
from pyproj import Transformer, Geod, CRS
# 1 origin vs pinned OSM nodes
gj = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson'))
feats = gj['features']
rw = [f for f in feats if f['properties'].get('@id') == 16714125 or f['properties'].get('@id') == 'way/16714125' or str(f['properties'].get('@id')).endswith('16714125')]
print('runway way features found', len(rw))
for f in rw:
    print(f['properties'].get('@type'), f['properties'].get('@id'), f['properties'].get('@version'), f['properties'].get('ref'), f['geometry']['type'], f['geometry']['coordinates'][0], f['geometry']['coordinates'][-1])
    c0 = f['geometry']['coordinates'][0]; c1 = f['geometry']['coordinates'][-1]
    print('mean', (c0[1]+c1[1])/2, (c0[0]+c1[0])/2, 'frame', F.ORIGIN_LAT, F.ORIGIN_LON)
    g = Geod(ellps='WGS84')
    az, baz, d = g.inv(c0[0], c0[1], c1[0], c1[1])
    print('way length geodesic', d, 'az', az%360)
    # geodesic midpoint
    lon_m, lat_m, _ = g.fwd(c0[0], c0[1], az, d/2)
    print('geodesic mid', lat_m, lon_m, 'dist to origin m', g.inv(lon_m, lat_m, F.ORIGIN_LON, F.ORIGIN_LAT)[2])
# 2 compare to pyproj topocentric (independent)
t = Transformer.from_pipeline(f'+proj=pipeline +step +proj=cart +ellps=WGS84 +step +proj=topocentric +ellps=WGS84 +lat_0={F.ORIGIN_LAT} +lon_0={F.ORIGIN_LON} +h_0=0')
random.seed(1)
mx = 0; mrt = 0
for i in range(2000):
    lat = F.ORIGIN_LAT + random.uniform(-0.06, 0.06); lon = F.ORIGIN_LON + random.uniform(-0.07, 0.07)
    e, n, u = t.transform(lon, lat, 0)
    e2, n2 = F.ll_to_en(lat, lon)
    mx = max(mx, abs(e - e2), abs(n - n2))
    la, lo = F.en_to_ll(e2, n2)
    e3, n3 = F.ll_to_en(la, lo)
    mrt = max(mrt, abs(e3-e2), abs(n3-n2))
    # also lat/lon round trip in degrees
print('max |frame - PROJ topocentric| m', mx, 'max en round trip m', mrt)
# round trip ll->world->ll
x, z = F.ll_to_world(31.2131135, 121.3354641)
print('N end node world', x, z, 'heading N end from origin', F.vec_hdg(x, z))
la, lo = F.world_to_ll(x, z)
print('roundtrip deg err', la-31.2131135, lo-121.3354641)
# heading convention check: point due east
x, z = F.ll_to_world(F.ORIGIN_LAT, F.ORIGIN_LON + 0.01)
print('east point world', x, z, 'hdg', F.vec_hdg(x, z), 'hdg_vec(90)', F.hdg_vec(90))
x, z = F.ll_to_world(F.ORIGIN_LAT + 0.01, F.ORIGIN_LON)
print('north point world', x, z, 'hdg', F.vec_hdg(x, z))
# 3 m per degree check
print('MLAT', F.MLAT, 'MLON', F.MLON)
g = Geod(ellps='WGS84')
print('geod 1e-4 deg lat m', g.inv(F.ORIGIN_LON, F.ORIGIN_LAT, F.ORIGIN_LON, F.ORIGIN_LAT+1e-4)[2]*1e4, 'lon', g.inv(F.ORIGIN_LON, F.ORIGIN_LAT, F.ORIGIN_LON+1e-4, F.ORIGIN_LAT)[2]*1e4)
# 4 geoid
try:
    import rasterio
    import glob
    fs = glob.glob('/home/user/Calc/sha3d/refs/cache/geoid_egm2008/*.tif')
    print('geoid files', fs)
    for fn in fs:
        with rasterio.open(fn) as ds:
            print(ds.bounds, ds.res, ds.crs)
            arr = ds.read(1)
            # bilinear at origin
            col, row = ~ds.transform * (F.ORIGIN_LON, F.ORIGIN_LAT)
            # pixel-is-area: centre at +0.5
            c = col - 0.5; r = row - 0.5
            c0 = int(math.floor(c)); r0 = int(math.floor(r)); fc = c - c0; fr = r - r0
            v = (arr[r0, c0]*(1-fc)*(1-fr) + arr[r0, c0+1]*fc*(1-fr) + arr[r0+1, c0]*(1-fc)*fr + arr[r0+1, c0+1]*fc*fr)
            print('bilinear N at origin (pixel-centre)', v, 'nearest', arr[int(row), int(col)])
            # also using pyproj egm08 grid if available
except Exception as ex:
    print('geoid err', ex)
# pyproj vertical: EPSG:4979 -> 4326+3855
try:
    tv = Transformer.from_crs('EPSG:4979', 'EPSG:9518', always_xy=True)
    print('pyproj egm2008 h->H at origin', tv.transform(F.ORIGIN_LON, F.ORIGIN_LAT, 0))
except Exception as ex:
    print('pyproj vertical', ex)
# 5 geoid plane fit check direction
print('geoid_n(1000,0)', F.geoid_n(1000, 0), 'geoid_n(0,-1000) north', F.geoid_n(0, -1000))
# hae
print('hae_from_y(3.0)', F.hae_from_y(3.0))
print('pressure alt 0ft, qnh 1013.25', F.y_from_pressure_alt(0, 1013.25), 'qnh 1023', F.y_from_pressure_alt(0, 1023.0))
# airport json frame block vs module
d = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
fb = d['frame']; mb = F.frame_block()
for k in mb:
    if fb.get(k) != mb[k]:
        print('frame block mismatch', k, fb.get(k), mb[k])
print('frame keys same', set(fb) == set(mb))
