"""Moving-traffic physics audit: out/draw/trace.json (jobs/trace2d.mjs - the app in live mode fed by the harness's
mock relay) frame by frame. For every sampled frame the displayed aircraft (rendered planform + heights, as audit.py)
are checked against each other, against the buildings and for gear on the paved raster. Results are aggregated per
pair over time (frames in conflict, first/last time, worst penetration) into out/draw/trace_audit.json.

Caveat: the mock relay moves aircraft in straight lines along their last track, so an aircraft driving off the
pavement or into a building is a property of the mock, not of real ADS-B data; aircraft-aircraft overlaps test what
GroundPhysics is meant to prevent (it nudges moving aircraft apart and relocates stationary ones)."""
import json, os, collections
import numpy as np
import shapely
from common import OUT, scene, ac_instance_geom, gear_points_world
from audit import Ac, ac_obj, static_objects, vertical, depth_of
from measure import PaveMask


def run():
    fp = os.path.join(OUT, 'trace.json')
    if not os.path.exists(fp): print('  no trace.json (run jobs/trace2d.mjs)'); return None
    T = json.load(open(fp)); S = scene(); pave = PaveMask()
    bld = [o for o in static_objects() if o.cat == 'building']
    tree = shapely.STRtree([b.poly for b in bld])
    agg = {}; per_frame = []; t0 = T['frames'][0]['t'] if T['frames'] else 0
    for fi, F in enumerate(T['frames']):
        objs = []
        for a in F['aircraft']:
            g, W = ac_instance_geom(a)
            if g is None: continue
            o = ac_obj(Ac(g, W, f'{a["flight"] or a["hex"]} {a["icao"]}', stand=a['gate'], type_key=a['typeKey']), oid=a['hex'])
            o.extra.update(phase=a['phase'], gs=a['gs'], stale=a['stale']); objs.append((o, a, W))
        n_cf = 0
        def rec(kind, A, B, depth, note, t):
            k = (kind, A, B); r = agg.get(k)
            if r is None: r = agg[k] = dict(kind=kind, a=A, b=B, frames=0, first=t, last=t, depth=0.0, note=note)
            r['frames'] += 1; r['last'] = t; r['depth'] = max(r['depth'], depth)
        t = (F['t'] - t0) / 1000
        for i in range(len(objs)):
            oi, ai, Wi = objs[i]
            for j in range(i + 1, len(objs)):
                oj, aj, _ = objs[j]
                if not oi.poly.intersects(oj.poly): continue
                R = oi.poly.intersection(oj.poly); col, vg = vertical(oi, oj, R)
                if col and depth_of(R) > 0.1:
                    n_cf += 1; A, B = sorted([oi.label, oj.label])
                    rec('aircraft-aircraft', A, B, depth_of(R), f'{ai["phase"]} ({ai["gs"]:.1f} m/s) x {aj["phase"]} ({aj["gs"]:.1f} m/s)', t)
            for k in tree.query(oi.poly):
                b = bld[k]
                if not oi.poly.intersects(b.poly): continue
                R = oi.poly.intersection(b.poly); col, vg = vertical(oi, b, R)
                if col and depth_of(R) > 0.1: n_cf += 1; rec('aircraft-building', oi.label, b.label, depth_of(R), f'{ai["phase"]} ({ai["gs"]:.1f} m/s)', t)
            Td = S['types'].get(ai['typeKey'])
            if Td:
                gp = gear_points_world(Td, Wi); X = np.array([p[0] for p in gp]); Z = np.array([p[1] for p in gp])
                if not pave(X, Z).all(): n_cf += 1; rec('gear-off-pavement', oi.label, 'paved raster', 0.0, f'{ai["phase"]} ({ai["gs"]:.1f} m/s)', t)
        per_frame.append(dict(t=t, aircraft=len(objs), conflicts=n_cf, stats=F.get('stats')))
    out = dict(mode=T['mode'], frames=len(T['frames']), span_s=per_frame[-1]['t'] if per_frame else 0, per_frame=per_frame,
               conflicts=sorted(agg.values(), key=lambda r: (r['kind'] != 'aircraft-aircraft', -r['frames'], -r['depth'])))
    json.dump(out, open(os.path.join(OUT, 'trace_audit.json'), 'w'), indent=0)
    c = collections.Counter(r['kind'] for r in out['conflicts'])
    print(f'  trace: {out["frames"]} frames over {out["span_s"]:.0f} s; conflicts (pairs): {dict(c)}')
    return out


if __name__ == '__main__':
    run()
