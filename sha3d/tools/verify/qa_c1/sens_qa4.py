import sys, json, glob
sys.path.insert(0, '/home/user/Calc/sha3d/tools/law'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import osm_sensitive as S, frame as F
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, LineString
RAW = '/home/user/Calc/sha3d/refs/cache/osm_pinned_raw/20261114'
nodes = {}; ways = {}; wt = {}
for fn in sorted(glob.glob(RAW + '/*.osm')):
    for el in ET.parse(fn).getroot():
        if el.tag == 'node': nodes[el.get('id')] = (float(el.get('lat')), float(el.get('lon')))
        elif el.tag == 'way':
            ways[el.get('id')] = [n.get('ref') for n in el.findall('nd')]; wt[el.get('id')] = {x.get('k'): x.get('v') for x in el.findall('tag')}
gj = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson'))
keptways = {str(f['properties']['@id']) for f in gj['features'] if f['properties']['@type'] == 'way'}
for w, t in wt.items():
    r = S.sensitive_reason(t)
    if r not in ('prison', 'armed_police'): continue
    pn = set(ways[w])
    xz = [F.ll_to_world(*nodes[n]) for n in ways[w]]
    per = Polygon(xz).length
    for w2 in keptways:
        if w2 in ways and len(set(ways[w2]) & pn) >= 2:
            sh = set(ways[w2]) & pn
            print(r, 'perimeter', round(per), 'kept way shares', len(sh), 'nodes with the dropped outline; its tags keys:', sorted(wt[w2].keys()))
