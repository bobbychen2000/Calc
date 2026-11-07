#!/usr/bin/env python3
"""Taxi graph + extra pavement for the live traffic engine, from OpenStreetMap (ODbL 1.0, (c) OpenStreetMap
contributors, https://www.openstreetmap.org/copyright) -> data/sfo_taxigraph.js (a derived database: it stays ODbL).

Why OSM (docs/research/traffic_audit.md 6.8): real moving ADS-B ground reports fit the OSM aeroway=taxiway/taxilane
centrelines with median 0.8 m / p90 4.2 m, against p90 301 m for data/sfo_details.json (no ramp taxilanes). The
X-Plane gateway graph is GPL v2+ (not used).

Input : refs/cache/osm/ksfo_osm_parsed.json (Overpass extract cached by the xcheck agent; osm_base in the file).
Output: data/sfo_taxigraph.js  = export const TAXIGRAPH = {
          frame, source, licence, attribution,
          edges:   [[x0,z0,x1,z1, wayIndex], ...]      taxiway/taxilane centreline segments (world x,z, 0.1 m)
          ways:    [{ref, kind}]                        per OSM way (kind taxiway|taxilane|runway)
          aprons:  [[[x,z],...], ...]                   aeroway=apron outer rings (pavement where aircraft park)
          leadins: [{ref, pts:[[x,z],..], stop:[x,z], hdg}]  aeroway=parking_position lines (stand lead-in lines;
                                                        stop = the end at the stop point, hdg = parked true heading, deg)
          halfWidth: 7.6 }                              metres; see below
          retired: {taxiways: ['<SFO Museum name>#<polygon index>', ...], rings: [[[x,z],...], ...], why: [...]}
                                                        pavement that no longer exists (close-out round 3, realtime-13)
Positions: OSM is WGS 84 -> tools/geo_frame.py wgs84_to_world (= js/geo.js wgs84ToWorld). Runway centrelines are
added from the FAA ends (tools/geo_frame.py RWY_ENDS, NAD83 -> ll_to_world), not from OSM.
OSM edits after the pinned base (close-out round 3, realtime-13): the static track's decision list is the source --
data/sfo_details.json osmBase.updates (tools/build_airfield_details.py OSM_UPDATES, each edit with its evidence): the
'retired' ways (the old W alignment, the old J, two connectors -- deleted in OSM changeset 189525528) are dropped and the
'added' ways (the relocated W 1562117372, J 1562117374, the lead-on / lead-off arcs of changeset 190952582) are read from
the pinned update extract refs/cache/osm/<osmBase.updates.file>. Retired pavement: data/sfo_details.json pavementRetired
(whole SFO Museum taxiway polygons, geometry from data/sfo_airport.json) and pavementRetiredParts (rings) -- the engine
(js/live/traffic.js TaxiNet.paved) does not count taxiway strips or aprons inside them as paved (the rendered mask,
js/live/airport.js, already leaves them out).
halfWidth: the engine treats points within 7.6 m (25 ft) of a taxiway centreline as paved. 25 ft is half of 50 ft,
the narrowest taxiway width for the jets at SFO per FAA AC 150/5300-13B (taxiway width by Taxiway Design Group:
TDG 3 = 50 ft) [design value, used only as an extra "paved" test for gear points; the rendered pavement is unchanged].
Usage: python3 tools/live/build_taxigraph.py [--out data/sfo_taxigraph.js]
"""
import argparse, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame  # noqa: E402


def w(lat, lon):
    x, z = geo_frame.wgs84_to_world(lat, lon)
    return [round(x, 1), round(z, 1)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--src', default=os.path.join(ROOT, 'refs/cache/osm/ksfo_osm_parsed.json'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'data/sfo_taxigraph.js')); o = ap.parse_args()
    d = json.load(open(o.src))
    det = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    upd = (det.get('osmBase') or {}).get('updates') or {}
    retired_ids, added_ids = set(upd.get('retired') or []), set(upd.get('added') or [])
    upd_ways = []
    if added_ids:
        U = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'osm', upd['file'])))
        for e in U['elements']:
            if e['type'] == 'way' and e['id'] in added_ids and e.get('tags', {}).get('aeroway') in ('taxiway', 'taxilane'):
                upd_ways.append({'id': e['id'], 'tags': e.get('tags', {}), 'pts': [(g['lat'], g['lon']) for g in e['geometry']], 'upd': True})
        assert len(upd_ways) == len(added_ids), 'update extract lacks added ways: %s' % (added_ids - {u['id'] for u in upd_ways})
    ways, edges = [], []
    n_ret = 0
    for t in list(d['taxiways']) + upd_ways:
        if t['id'] in retired_ids: n_ret += 1; continue
        pts = [w(a, b) for a, b in t['pts']]
        if len(pts) < 2: continue
        wi = len(ways); ways.append({'ref': t['tags'].get('ref') or t.get('ref'), 'kind': t['tags'].get('aeroway', 'taxiway'), 'osm': t['id'], **({'upd': upd.get('date')} if t.get('upd') else {})})
        for p, q in zip(pts, pts[1:]):
            if math.hypot(q[0] - p[0], q[1] - p[1]) > 0.05: edges.append([p[0], p[1], q[0], q[1], wi])
    for a, b in geo_frame.RWY_PAIRS:
        p = [round(v, 1) for v in geo_frame.end_world(a)]; q = [round(v, 1) for v in geo_frame.end_world(b)]
        wi = len(ways); ways.append({'ref': f'{a}/{b}', 'kind': 'runway', 'src': 'FAA NASR runway ends'})
        n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) // 200))
        for i in range(n):
            u0, u1 = i / n, (i + 1) / n
            edges.append([round(p[0] + (q[0] - p[0]) * u0, 1), round(p[1] + (q[1] - p[1]) * u0, 1), round(p[0] + (q[0] - p[0]) * u1, 1), round(p[1] + (q[1] - p[1]) * u1, 1), wi])
    aprons = [[w(a, b) for a, b in ap_['pts']] for ap_ in d['aprons'] if len(ap_['pts']) >= 4]
    leadins = []
    for p in d['parking_positions']:
        if p['type'] != 'way' or len(p['pts']) < 2: continue
        pts = [w(a, b) for a, b in p['pts']]
        stop = w(*p['stop'])
        if math.hypot(stop[0] - pts[0][0], stop[1] - pts[0][1]) < 0.5: pts = pts[::-1]     # stop at the end
        a, b = pts[-2], pts[-1]
        hdg = math.degrees(math.atan2(b[0] - a[0], -(b[1] - a[1]))) % 360
        leadins.append({'ref': p['tags'].get('ref'), 'pts': pts, 'stop': pts[-1], 'hdg': round(hdg, 1), 'osm': p['id']})
    # retired pavement (static track decisions, data/sfo_details.json): whole SFO Museum taxiway polygons + parts
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    tw = {t['name']: t for t in A['taxiways']}
    ret = {'taxiways': [], 'rings': [], 'why': []}
    for r in det.get('pavementRetired') or []:
        if r.get('layer') != 'taxiways' or r['name'] not in tw: continue
        ret['taxiways'].append('%s#%d' % (r['name'], r['poly'])); ret['rings'].append(tw[r['name']]['polys'][r['poly']][0]); ret['why'].append(r.get('why'))
    for r in det.get('pavementRetiredParts') or []:
        ret['rings'].append(r['ring']); ret['why'].append(r.get('why'))
    G = {'frame': geo_frame.FRAME_ID, 'source': f"OpenStreetMap via Overpass, osm_base {d.get('osm_base')} ({d.get('endpoint')})"
         + (f"; edits after it from the update extract of {upd.get('date')} (data/sfo_details.json osmBase.updates: {len(added_ids)} added, {len(retired_ids)} retired)" if upd else ''),
         'licence': 'ODbL 1.0', 'attribution': '© OpenStreetMap contributors', 'halfWidth': 7.6,
         'ways': ways, 'edges': edges, 'aprons': aprons, 'leadins': leadins, 'retired': ret}
    head = ('// generated by tools/live/build_taxigraph.py from OpenStreetMap (osm_base %s). Do not edit.\n'
            '// Data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright); this derived\n'
            '// database is licensed under the ODbL 1.0 as well. Runway centrelines: FAA NASR runway ends (js/geo.js).\n') % d.get('osm_base')
    open(o.out, 'w').write(head + 'export const TAXIGRAPH = ' + json.dumps(G, separators=(',', ':')) + ';\n')
    print(f'{o.out}: {len(ways)} ways ({len(upd_ways)} from the update extract, {n_ret} retired ways dropped), {len(edges)} segments, '
          f'{len(aprons)} aprons, {len(leadins)} lead-in lines, {len(ret["rings"])} retired pavement rings, {os.path.getsize(o.out)} B')


if __name__ == '__main__':
    main()
