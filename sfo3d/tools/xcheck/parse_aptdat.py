"""Parse the X-Plane Scenery Gateway KSFO apt.dat (fetched by fetch_xplane.py) into JSON.

Spec: "Airport Data (apt.dat) 12.00 File Format Specification",
https://developer.x-plane.com/article/airport-data-apt-dat-12-00-file-format-specification/ (cached as
refs/cache/xcheck/xp_apt1200_spec.txt). Row codes parsed (field meanings as the spec's tables state them):
  1     airport header (elevation ft, -, -, ICAO, name)          1302  metadata key value
  100   land runway: width m, surface, shoulder, smoothness, centre lights, edge lights, auto signs, then per end:
        number, lat, lon, displaced threshold length (m), overrun/blast-pad length (m), markings, approach
        lights, TDZ lights, REIL
  102   helipad                                                   14 viewpoint (tower cab)   19 windsock   18 beacon
  110   pavement header (surface, smoothness, texture heading, name); 120 linear feature header (name);
  130   airport boundary; nodes 111 plain, 112 bezier, 113/114 close loop, 115/116 end line;
        nodes 111-114 carry up to two codes: painted line type and lighting type for the segment starting there
  20    taxiway sign (lat, lon, heading, reserved, size, text)   21 lighting object (lat, lon, type, heading,
        glideslope, runway, description)
  1200  taxi routing network header; 1201 node (lat, lon, usage, id, name); 1202 edge (from, to, oneway|twoway,
        taxiway|runway|taxiway_X, name); 1204 active zone for the preceding 1202 (arrival|departure|ils, runways);
        1206 ground-truck edge
  1300  start-up location: lat, lon, true heading "of airplane positioned at this location", type
        (gate|hangar|misc|tie_down), airplane types (pipe-separated), unique name (rest of line)
  1301  ramp start metadata: ICAO width code (A-F), operation type, airline codes (space-separated)
  1400/1401 truck parking / destination; 1500 jetway (lat, lon of "base of telescoping jetway tunnel", heading of
        parked tunnel, style, size code, unused, parked tunnel length m, parked cabin heading)
  1050-1056 ATC frequencies (MHz x 1000 in 12.00: 6-digit, e.g. 118200)
What the 1300 lat/lon denotes: the spec table only says "Latitude of location"; WorldEditor's own geometry code
treats it as the NOSE WHEEL (xptools src/WEDEntities/WED_RampPosition.cpp, GetTips(): variable `nosewheel_loc`,
nose tip drawn `nose_offset` ahead: A 1.0 m, B 2.7, C 4.7, D 9.5, E 8.2, F 8.8; type misc = aircraft centre).
Writes refs/cache/xplane/ksfo_apt_parsed.json. Data: X-Plane Scenery Gateway, GPL v2 or later (pack README/COPYING).
Usage: python3 tools/xcheck/parse_aptdat.py [path/to/apt.dat]
"""
import glob, json, math, os, sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
XP = os.path.join(ROOT, 'refs', 'cache', 'xplane')

LINE_TYPES = {  # apt.dat 12.00 spec, "Line Type Code" table
    0: 'nothing', 1: 'solid yellow (taxiway centreline)', 2: 'broken yellow (misc boundary)',
    3: 'double solid yellow (taxiway edge)', 4: 'runway hold position (2 broken + 2 solid)',
    5: 'other hold (broken + solid)', 6: 'ILS hold (cross-hatched)', 7: 'centreline in runway safety zone',
    8: 'widely separated broken yellow (queue lane)', 9: 'widely separated broken double yellow (queue lane)',
    20: 'solid white (roadway)', 21: 'white chequerboard (roadway)', 22: 'broken white (roadway centreline)',
    101: 'green embedded centreline lights', 102: 'blue taxiway edge lights', 103: 'amber hold-line lights',
    104: 'pulsating amber runway hold lights', 105: 'alternating green/amber centreline (RSA)',
    106: 'red edge lights', 107: 'green lead-off lights', 108: 'green/amber lead-off lights (RSA)'}
for k in range(1, 10): LINE_TYPES[50 + k] = LINE_TYPES[k] + ' + black border'


def norm_hdg(h): return h % 360.0


def parse(path):
    rows = [l.rstrip('\n').split() for l in open(path, encoding='utf-8', errors='replace')]
    raw = [l.rstrip('\n') for l in open(path, encoding='utf-8', errors='replace')]
    out = {'source': os.path.relpath(path, ROOT), 'meta': {}, 'runways': [], 'helipads': [], 'viewpoint': None,
           'windsocks': [], 'beacons': [], 'signs': [], 'lights': [], 'features': [], 'taxi_nodes': {},
           'taxi_edges': [], 'truck_edges': [], 'ramp_starts': [], 'truck_parking': [], 'truck_dest': [],
           'jetways': [], 'freqs': []}
    feat = None; ring = None; last_edge = None; last_ramp = None
    for i, (r, line) in enumerate(zip(rows, raw)):
        if not r: continue
        c = r[0]
        if c == '1':
            out['header'] = {'elev_ft': float(r[1]), 'icao': r[4], 'name': ' '.join(r[5:])}
        elif c == '1302':
            out['meta'][r[1]] = ' '.join(r[2:])
        elif c == '100':
            rw = {'width_m': float(r[1]), 'surface': int(r[2]), 'shoulder': int(r[3]), 'smooth': float(r[4]),
                  'centre_lights': int(r[5]), 'edge_lights': int(r[6]), 'auto_signs': int(r[7]), 'ends': []}
            for k in (8, 17):
                e = r[k:k + 9]
                rw['ends'].append({'id': e[0], 'lat': float(e[1]), 'lon': float(e[2]), 'disp_m': float(e[3]),
                                   'blastpad_m': float(e[4]), 'markings': int(e[5]), 'appr_lights': int(e[6]),
                                   'tdz': int(e[7]), 'reil': int(e[8])})
            out['runways'].append(rw)
        elif c == '102':
            out['helipads'].append({'id': r[1], 'lat': float(r[2]), 'lon': float(r[3]), 'hdg': float(r[4]),
                                    'len': float(r[5]), 'wid': float(r[6])})
        elif c == '14':
            out['viewpoint'] = {'lat': float(r[1]), 'lon': float(r[2]), 'height_ft': float(r[3]), 'name': ' '.join(r[5:])}
        elif c == '19':
            out['windsocks'].append({'lat': float(r[1]), 'lon': float(r[2]), 'lit': int(r[3]), 'name': ' '.join(r[4:])})
        elif c == '18':
            out['beacons'].append({'lat': float(r[1]), 'lon': float(r[2]), 'type': int(r[3]), 'name': ' '.join(r[4:])})
        elif c == '20':
            out['signs'].append({'lat': float(r[1]), 'lon': float(r[2]), 'hdg': norm_hdg(float(r[3])), 'size': int(r[5]),
                                 'text': line.split(None, 6)[6] if len(r) > 6 else ''})
        elif c == '21':
            out['lights'].append({'lat': float(r[1]), 'lon': float(r[2]), 'type': int(r[3]), 'hdg': float(r[4]),
                                  'gs_deg': float(r[5]), 'rwy': r[6], 'desc': ' '.join(r[7:])})
        elif c in ('110', '120', '130'):
            if c == '110':
                feat = {'kind': 'pavement', 'surface': int(r[1]), 'smooth': float(r[2]), 'tex_hdg': float(r[3]),
                        'name': ' '.join(r[4:]), 'rings': []}
            elif c == '120':
                feat = {'kind': 'linear', 'name': ' '.join(r[1:]), 'rings': []}
            else:
                feat = {'kind': 'boundary', 'name': ' '.join(r[1:]), 'rings': []}
            out['features'].append(feat); ring = None
        elif c in ('111', '112', '113', '114', '115', '116') and feat is not None:
            if ring is None: ring = {'closed': False, 'nodes': []}; feat['rings'].append(ring)
            bez = c in ('112', '114', '116')
            n = {'lat': float(r[1]), 'lon': float(r[2])}
            k = 3
            if bez: n['ctl'] = [float(r[3]), float(r[4])]; k = 5
            codes = [int(x) for x in r[k:k + 2]] if c not in ('115', '116') else []
            if codes: n['codes'] = codes
            ring['nodes'].append(n)
            if c in ('113', '114'): ring['closed'] = True; ring = None
            elif c in ('115', '116'): ring = None
        elif c == '1201':
            out['taxi_nodes'][r[4]] = {'lat': float(r[1]), 'lon': float(r[2]), 'usage': r[3], 'name': ' '.join(r[5:])}
        elif c == '1202':
            last_edge = {'a': r[1], 'b': r[2], 'dir': r[3], 'cls': r[4] if len(r) > 4 else '', 'name': ' '.join(r[5:]),
                         'active': []}
            out['taxi_edges'].append(last_edge)
        elif c == '1204' and last_edge is not None:
            last_edge['active'].append({'kind': r[1], 'runways': r[2].split(',') if len(r) > 2 else []})
        elif c == '1206':
            out['truck_edges'].append({'a': r[1], 'b': r[2], 'dir': r[3], 'name': ' '.join(r[4:])})
        elif c == '1300':
            last_ramp = {'lat': float(r[1]), 'lon': float(r[2]), 'hdg_raw': float(r[3]), 'hdg': norm_hdg(float(r[3])),
                         'type': r[4], 'ac_types': r[5].split('|'), 'name': ' '.join(r[6:]), 'line': i + 1}
            out['ramp_starts'].append(last_ramp)
        elif c == '1301' and last_ramp is not None:
            last_ramp.update({'icao_cat': r[1], 'op': r[2] if len(r) > 2 else '', 'airlines': r[3:]})
        elif c == '1400':
            out['truck_parking'].append({'lat': float(r[1]), 'lon': float(r[2]), 'hdg': float(r[3]), 'type': r[4],
                                         'count': r[5], 'name': ' '.join(r[6:])})
        elif c == '1401':
            out['truck_dest'].append({'lat': float(r[1]), 'lon': float(r[2]), 'hdg': float(r[3]), 'types': r[4],
                                      'name': ' '.join(r[5:])})
        elif c == '1500':
            out['jetways'].append({'lat': float(r[1]), 'lon': float(r[2]), 'tunnel_hdg': norm_hdg(float(r[3])),
                                   'style': int(r[4]), 'size': int(r[5]), 'unused': float(r[6]),
                                   'tunnel_len_m': float(r[7]), 'cab_hdg': norm_hdg(float(r[8]))})
        elif c.isdigit() and 1050 <= int(c) <= 1056:
            out['freqs'].append({'code': int(c), 'khz': int(r[1]), 'name': ' '.join(r[2:])})
    # summaries
    lt = Counter(); lights = Counter()
    for f in out['features']:
        for rg in f['rings']:
            for n in rg['nodes']:
                for code in n.get('codes', []):
                    (lights if code >= 100 else lt)[code] += 1
    out['summary'] = {
        'row_counts': dict(Counter(r[0] for r in rows if r)),
        'runways': len(out['runways']), 'ramp_starts': len(out['ramp_starts']),
        'ramp_types': dict(Counter(r['type'] for r in out['ramp_starts'])),
        'ramp_icao_cat': dict(Counter(r.get('icao_cat') for r in out['ramp_starts'])),
        'ramp_ops': dict(Counter(r.get('op') for r in out['ramp_starts'])),
        'jetways': len(out['jetways']), 'jetway_sizes': dict(Counter(j['size'] for j in out['jetways'])),
        'signs': len(out['signs']), 'lights': dict(Counter(l['type'] for l in out['lights'])),
        'taxi_nodes': len(out['taxi_nodes']), 'taxi_edges': len(out['taxi_edges']),
        'taxi_edge_classes': dict(Counter(e['cls'] for e in out['taxi_edges'])),
        'active_zones': sum(len(e['active']) for e in out['taxi_edges']),
        'features': dict(Counter(f['kind'] for f in out['features'])),
        'pavement_surfaces': dict(Counter(f['surface'] for f in out['features'] if f['kind'] == 'pavement')),
        'line_type_segments': {f'{k} {LINE_TYPES.get(k, "NOT IN SPEC TABLE")}': v for k, v in sorted(lt.items())},
        'light_type_segments': {f'{k} {LINE_TYPES.get(k, "NOT IN SPEC TABLE")}': v for k, v in sorted(lights.items())},
        'freqs': out['freqs'],
    }
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(XP, 'apt_*.dat')))[-1]
    d = parse(path)
    fn = os.path.join(XP, 'ksfo_apt_parsed.json')
    json.dump(d, open(fn, 'w'), indent=None, separators=(',', ':'))
    print('wrote', os.path.relpath(fn, ROOT))
    print(json.dumps(d['summary'], indent=1))


if __name__ == '__main__':
    main()
