import sys, json, glob, numpy as np, xml.etree.ElementTree as ET
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common'); import frame as F
from shapely.geometry import MultiPoint, Point, shape, Polygon
from shapely.prepared import prep
# independent extent: convex hull of the relation's outer-way nodes (raw file), buffered 1000 m in a pyproj AEQD frame
from pyproj import Transformer
root = ET.parse('/home/user/Calc/sha3d/refs/cache/osm_pinned_raw/20261114/relation_21913346_full.osm').getroot()
nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.iter('node')}
ways = {w.get('id'): [nd.get('ref') for nd in w.findall('nd')] for w in root.iter('way')}
rel = next(r for r in root.iter('relation') if r.get('id') == '21913346')
roles = [(m.get('type'), m.get('role')) for m in rel.findall('member')]
from collections import Counter; print('relation members (type, role):', Counter(roles))
pts = [nodes[r] for m in rel.findall('member') if m.get('type') == 'way' for r in ways[m.get('ref')]]
aeqd = Transformer.from_crs('EPSG:4326', f'+proj=aeqd +lat_0={F.ORIGIN_LAT} +lon_0={F.ORIGIN_LON} +ellps=WGS84', always_xy=True)
xy = [aeqd.transform(*p) for p in pts]
hull = MultiPoint(xy).convex_hull; ext = hull.buffer(1000, quad_segs=64)
print('independent hull %.3f km2, hull+1km %.3f km2' % (hull.area / 1e6, ext.area / 1e6))
dat = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
ring = dat['extent']['ring']
ring_xy = [aeqd.transform(*F.world_to_ll(x, z)[::-1]) for x, z in ring]
pe = Polygon(ring_xy)
print('committed extent ring area %.3f km2; symmetric difference with mine %.4f km2' % (pe.area / 1e6, pe.symmetric_difference(ext).area / 1e6))
E = prep(ext.buffer(1.0))   # 1 m tolerance
def check_xz(name, arr):
    arr = np.asarray(arr)
    out = 0
    for x, z in arr:
        la, lo = F.world_to_ll(x, z); p = aeqd.transform(lo, la)
        if not E.contains(Point(p)): out += 1
    print(f'{name:40s} points {len(arr):7d}  outside hull+1km: {out}')
def xz_pairs(o, acc):
    if isinstance(o, list):
        if len(o) == 2 and all(isinstance(v, (int, float)) for v in o) and abs(o[0]) < 20000 and abs(o[1]) < 20000:
            acc.append(o); return
        if len(o) >= 4 and len(o) <= 5 and all(isinstance(v, (int, float)) for v in o[:4]):
            acc.append(o[:2]); acc.append(o[2:4]); return
        for v in o: xz_pairs(v, acc)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('lat_lon', 'origin_wgs84', 'lat', 'lon', 'ring_ll', 'bbox_ll', 'axis_unit_xz', 'surface_segments_m', 'points_s_y', 'blast_pad_m', 'strip_m', 'resa_m', 'gate_offset_from_stop_median_uv_m', 'du_range', 'dv_range', 'tail_headings', 'g_uv', 'door_zone_uv', 'shift_umbra_minus_osm_m', 'ref_offset_osm_minus_s2_m', 'normal_EN', 'shift_px_row_col'):
                continue
            xz_pairs(v, acc)
for fn in ('sha_airport.json', 'sha_stands.json', 'sha_taxigraph.json'):
    d = json.load(open('/home/user/Calc/sha3d/data/' + fn)); acc = []
    if fn == 'sha_airport.json':
        for k in list(d.keys()):
            if k in ('frame', 'checks_at_build', 'counts', 'extent'): continue
            sub = []; xz_pairs(d[k], sub)
            if sub: check_xz(fn + ':' + k, sub)
    else:
        for k in d:
            if k in ('checks_at_build', 'counts', 'class_max', 'class_ref', 'params'): continue
            sub = []; xz_pairs(d[k], sub)
            if sub: check_xz(fn + ':' + k, sub)
# lat/lon in airport json
acc = []
def ll(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'lat_lon': acc.append(v)
            elif k == 'osm_end_node': acc.append([v['lat'], v['lon']])
            else: ll(v)
    elif isinstance(o, list):
        for v in o: ll(v)
ll(dat); out = sum(1 for la, lo in acc if not E.contains(Point(aeqd.transform(lo, la))))
print('sha_airport.json lat_lon points', len(acc), 'outside', out)
gj = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson'))
bad = 0; n = 0
for f in gj['features']:
    if not f.get('geometry'): continue
    g = shape(f['geometry'])
    from shapely.ops import transform
    gx = transform(lambda x, y, z=None: aeqd.transform(x, y), g); n += 1
    if not ext.buffer(1.0).contains(gx): bad += 1
print('pinned geojson geometries', n, 'not inside hull+1km (+1 m):', bad)
# meas files: any coordinates?
for fn in sorted(glob.glob('/home/user/Calc/sha3d/data/meas/*.json')):
    d = json.load(open(fn)); txt = json.dumps(d)
    import re
    lls = re.findall(r'\[(3[01]\.\d{4,}), (12[01]\.\d{4,})\]', txt) + re.findall(r'\[(12[01]\.\d{4,}), (3[01]\.\d{4,})\]', txt)
    print(fn.split('/')[-1], 'lat/lon-like pairs:', len(lls))
print('--- records with x/z keys')
for fn in ('sha_airport.json', 'sha_stands.json', 'sha_taxigraph.json'):
    d = json.load(open('/home/user/Calc/sha3d/data/' + fn)); acc = []
    def xz(o):
        if isinstance(o, dict):
            if isinstance(o.get('x'), (int, float)) and isinstance(o.get('z'), (int, float)): acc.append((o['x'], o['z']))
            for v in o.values(): xz(v)
        elif isinstance(o, list):
            for v in o: xz(v)
    xz(d); check_xz(fn + ' {x,z} records', acc)
