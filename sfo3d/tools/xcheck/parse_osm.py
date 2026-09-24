"""Parse the raw Overpass download (fetch_osm.py) into a compact JSON of the KSFO airfield features we cross-check.

OSM tagging conventions used (quoted from the OSM wiki, https://wiki.openstreetmap.org/wiki/Tag:aeroway=parking_position,
raw wikitext cached as refs/cache/xcheck/osmwiki_parking_position.wiki, last edited 2024-12-05):
  "As a node: Put a node where the nose wheel stops."
  "As a way: Draw a way from the relevant taxiway and to the nose wheel position. The direction of the way indicates
   the direction a plane should park. This usually means that the last node of the way should be where the nose
   wheel is parked."
So for a parking_position way: stop point = LAST node, heading = bearing of the last segment (second-last -> last).
Other features kept: aeroway=gate (nodes, ref), jet_bridge (ways), runway / stopway / blast_pad / displaced_threshold
/ holding_position / taxiway / taxilane / apron / terminal / hangar / tower / control_tower / navigationaid / windsock /
helipad, plus building counts. Coordinates are also given in the app's world frame (js/geo.js llToEN, see xcommon.py).
Writes refs/cache/osm/ksfo_osm_parsed.json.  Data (c) OpenStreetMap contributors, ODbL 1.0.
Usage: python3 tools/xcheck/parse_osm.py
"""
import json, math, os
from collections import Counter
import xcommon as X

SRC = os.path.join(X.ROOT, 'refs', 'cache', 'osm', 'overpass_ksfo_latest.json')
OUT = os.path.join(X.ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')


def geom(e):
    if e['type'] == 'node': return [(e['lat'], e['lon'])]
    if e['type'] == 'way': return [(g['lat'], g['lon']) for g in e.get('geometry', []) if g]
    return []


def prov(e):
    return {k: e.get(k) for k in ('type', 'id', 'version', 'timestamp', 'user', 'changeset')}


def main():
    raw = json.load(open(SRC))
    meta = json.load(open(SRC.replace('.json', '.meta.json')))
    E = raw['elements']
    out = {'source': os.path.relpath(SRC, X.ROOT), 'osm_base': raw['osm3s']['timestamp_osm_base'],
           'endpoint': meta['endpoint'], 'fetched_utc': meta['utc'], 'licence': 'ODbL 1.0, (c) OpenStreetMap contributors',
           'parking_positions': [], 'gates': [], 'jet_bridges': [], 'runways': [], 'stopways': [], 'blast_pads': [],
           'thresholds': [], 'holding_positions': [], 'taxiways': [], 'aprons': [], 'terminals': [], 'hangars': [],
           'towers': [], 'navaids': [], 'windsocks': [], 'helipads': [], 'other_aeroway': Counter(), 'buildings': Counter()}
    for e in E:
        t = e.get('tags', {}); a = t.get('aeroway'); g = geom(e)
        if 'building' in t: out['buildings'][t['building']] += 1
        if not a:
            mm = t.get('man_made')
            if mm == 'tower' and (t.get('tower:type') in ('observation', 'communication') or 'aircraft' in t.get('service', '')):
                out['towers'].append({**prov(e), 'tags': t, 'pts': g})
            elif mm == 'windsock':
                out['windsocks'].append({**prov(e), 'tags': t, 'pts': g})
            continue
        rec = {**prov(e), 'ref': t.get('ref'), 'name': t.get('name'), 'tags': t}
        if a == 'parking_position':
            if not g: continue
            stop = g[-1]
            if len(g) >= 2:
                p0 = X.wgs84_to_world(*g[-2]); p1 = X.wgs84_to_world(*g[-1])
                hdg = X.world_hdg(p1[0] - p0[0], p1[1] - p0[1])
                L = sum(math.dist(X.wgs84_to_world(*g[i]), X.wgs84_to_world(*g[i + 1])) for i in range(len(g) - 1))
            else:
                hdg, L = None, 0.0
            rec.update({'stop': stop, 'stop_w': [round(v, 2) for v in X.wgs84_to_world(*stop)], 'hdg': hdg,
                        'len_m': round(L, 1), 'n_nodes': len(g), 'first': g[0], 'pts': g})
            out['parking_positions'].append(rec)
        elif a == 'gate':
            rec.update({'pt': g[0], 'w': [round(v, 2) for v in X.wgs84_to_world(*g[0])]}); out['gates'].append(rec)
        elif a == 'jet_bridge':
            rec.update({'pts': g, 'ends_w': [[round(v, 2) for v in X.wgs84_to_world(*g[0])], [round(v, 2) for v in X.wgs84_to_world(*g[-1])]]})
            out['jet_bridges'].append(rec)
        elif a in ('runway', 'stopway', 'blast_pad', 'displaced_threshold', 'threshold'):
            rec.update({'pts': g})
            key = {'runway': 'runways', 'stopway': 'stopways', 'blast_pad': 'blast_pads'}.get(a, 'thresholds')
            out[key].append(rec)
        elif a == 'holding_position':
            rec.update({'pts': g}); out['holding_positions'].append(rec)
        elif a in ('taxiway', 'taxilane'):
            rec.update({'pts': g}); out['taxiways'].append(rec)
        elif a == 'apron':
            rec.update({'pts': g}); out['aprons'].append(rec)
        elif a == 'terminal':
            rec.update({'pts': g}); out['terminals'].append(rec)
        elif a == 'hangar':
            rec.update({'pts': g}); out['hangars'].append(rec)
        elif a in ('tower', 'control_tower'):
            rec.update({'pts': g}); out['towers'].append(rec)
        elif a == 'navigationaid':
            rec.update({'pts': g}); out['navaids'].append(rec)
        elif a == 'windsock':
            rec.update({'pts': g}); out['windsocks'].append(rec)
        elif a == 'helipad':
            rec.update({'pts': g}); out['helipads'].append(rec)
        else:
            out['other_aeroway'][a] += 1
    out['other_aeroway'] = dict(out['other_aeroway']); out['buildings'] = dict(out['buildings'])
    out['counts'] = {k: len(v) for k, v in out.items() if isinstance(v, list)}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('wrote', os.path.relpath(OUT, X.ROOT), 'osm_base', out['osm_base'])
    print(json.dumps(out['counts'], indent=1)); print('other aeroway', out['other_aeroway'])


if __name__ == '__main__':
    main()
