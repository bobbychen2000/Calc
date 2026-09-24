"""OSM aeroway=parking_position lead-ins and aeroway=jet_bridge ways as stand sources (ODbL 1.0,
(c) OpenStreetMap contributors; parsed by tools/xcheck/parse_osm.py from the Overpass download of 24 Sep 2026).

Semantics (OSM wiki Tag:aeroway=parking_position, rev. 2785188, 2024-12-05, cached refs/cache/xcheck/
osmwiki_parking_position.wiki): "Draw a way from the relevant taxiway and to the nose wheel position. The direction of
the way indicates the direction a plane should park. This usually means that the last node of the way should be where
the nose wheel is parked."  -> stop = last node, heading = bearing of the last segment.

Orientation: 64+ of the ways at SFO are drawn backwards (docs/research/stands_xcheck.md §2). A way is oriented by two
independent cues, and the result records which one decided:
  taxi  : exactly one end lies on (< 3 m from) an OSM taxiway/taxilane centreline -> that end is the START;
  bldg  : one end is within 60 m of the terminal outline (SFO Museum) and > 5 m closer to it than the other -> that
          end is the STOP (nose in towards the building);
  If both cues exist they must agree (they do for all 266 decided ways, 24 Sep 2026 data); ways with neither cue are
  returned with orient='drawn' (kept as drawn) and must be checked on NAIP.
"""
import math, re
import numpy as np
from common import load_osm, Buildings, vec_hdg

GATE_RE = re.compile(r'^[A-G]\d{1,3}[A-Z]?$')


def _dseg(p, P):
    best = 1e9
    for i in range(len(P) - 1):
        a = P[i]; b = P[i + 1]; ab = b - a; L2 = ab @ ab
        u = 0.0 if L2 < 1e-9 else float(np.clip((p - a) @ ab / L2, 0, 1))
        best = min(best, float(np.hypot(*(p - a - ab * u))))
    return best


def lead_ins(osm=None, B=None):
    osm = osm or load_osm(); B = B or Buildings()
    tw = [np.array(t['w']) for t in osm['taxiways']]
    dtw = lambda p: min(_dseg(np.array(p), P) for P in tw)
    out = []
    for p in osm['parking_positions']:
        w = [tuple(q) for q in p['w']]
        rec = {'osm_id': p['id'], 'osm_type': p['type'], 'osm_version': p['version'], 'osm_ts': p['timestamp'],
               'ref': p['ref'], 'tags': p['tags']}
        if len(w) < 2:
            rec.update({'stop': w[0], 'hdg': None, 'orient': 'node', 'pts': w, 'len': 0.0, 'bdist': round(B.d(*w[0]), 1)})
            out.append(rec); continue
        f, l = w[0], w[-1]
        bf, bl = B.d(*f), B.d(*l); tf, tl = dtw(f), dtw(l)
        by_b = 'rev' if (bf < 60 and bf < bl - 5) else ('fwd' if (bl < 60 and bl < bf - 5) else None)
        by_t = 'fwd' if (tf < 3 and tl > 3) else ('rev' if (tl < 3 and tf > 3) else None)
        if by_b and by_t and by_b != by_t: raise RuntimeError(f'orientation conflict on OSM way {p["id"]}')
        o = by_t or by_b
        how = '+'.join(k for k, v in (('taxi', by_t), ('bldg', by_b)) if v) or 'drawn'
        if o == 'rev': w = w[::-1]
        L = sum(math.dist(w[i], w[i + 1]) for i in range(len(w) - 1))
        # heading of the final straight part: last segment, extended back over collinear segments up to 25 m
        x1, z1 = w[-1]; k = len(w) - 2
        h = vec_hdg(x1 - w[k][0], z1 - w[k][1])
        rec.update({'stop': w[-1], 'hdg': h, 'orient': how, 'reversed': o == 'rev', 'pts': w, 'len': round(L, 1),
                    'last_seg': round(math.dist(w[-1], w[-2]), 1), 'bdist': round(B.d(*w[-1]), 1)})
        out.append(rec)
    return out


def jet_bridges(osm=None, B=None, stops=None):
    """OSM jet bridges oriented building end (base) -> far (cab) end. Base = the end nearer the terminal outline; when
    both ends are within 5 m of the same building distance (5 of 133 ways: branches and two-node stubs), the end
    farther from the nearest stand stop point (OSM lead-in end) is the base - bridges reach out towards the aircraft."""
    osm = osm or load_osm(); B = B or Buildings()
    if stops is None: stops = [r['stop'] for r in lead_ins(osm, B) if r['bdist'] < 60]
    near = lambda p: min(math.dist(p, q) for q in stops) if stops else 0.0
    out = []
    for b in osm['jet_bridges']:
        w = [tuple(q) for q in b['w']]
        d0, d1 = B.d(*w[0]), B.d(*w[-1])
        if abs(d0 - d1) >= 5:
            if d1 < d0: w = w[::-1]
        elif near(w[0]) < near(w[-1]): w = w[::-1]
        out.append({'osm_id': b['id'], 'ref': b['ref'], 'name': b.get('name'), 'tags': b['tags'], 'pts': w,
                    'base': w[0], 'cab': w[-1], 'base_bdist': round(B.d(*w[0]), 1)})
    return out
