"""Overlay plots for the stand cross-check: our stands vs OSM parking positions vs X-Plane ramp starts (+ jet bridges).

One PNG per boarding area plus the whole airfield, in the app's world frame (x east, north up), over the SFO Museum
building outlines (data/sfo_airport.json). No imagery.
Legend: ours = black arrow from the stop point (nose) back along the fuselage axis (length 20 m), blue if src=obs,
orange if src=inf; OSM parking_position lead-in ways = green lines, stop node (last node) = green dot, first node =
green 'x'; X-Plane 1300 ramp starts = red triangle pointing along the heading; X-Plane 1500 jetway bases = red '+'
with the parked tunnel drawn; OSM jet_bridge ways = purple; our bridges = grey (attach point -> L1/L2 door).
The figures embed OSM (ODbL) and X-Plane Gateway (GPL v2+) geometry, so they are written to the gitignored
refs/cache/xcheck/fig/ and are not for redistribution without the notices in docs/research/stands_xcheck.md section 7.
Usage: python3 tools/xcheck/figs.py
"""
import json, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import xcommon as X

OUTD = os.path.join(X.ROOT, 'refs', 'cache', 'xcheck', 'fig')


def main():
    os.makedirs(OUTD, exist_ok=True)
    A = json.load(open(os.path.join(X.ROOT, 'data', 'sfo_airport.json')))
    S = X.load_stands()
    xp = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'xplane', 'ksfo_apt_parsed.json')))
    osm = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')))
    rings = []
    for poly in A['terminalComplex']: rings += poly
    for b in A['boardingAreas']:
        for poly in b['polys']: rings += poly
    for s in A['structures']:
        for poly in s['polys']: rings += poly
    twy = []
    for t in A['taxiways']:
        for poly in t['polys']: twy += poly
    areas = {}
    for s in S['stands']:
        L = s['letter']; x, z = s['nose']
        a = areas.setdefault(L, [1e9, 1e9, -1e9, -1e9])
        a[0] = min(a[0], x); a[1] = min(a[1], z); a[2] = max(a[2], x); a[3] = max(a[3], z)
    areas = {k: (v[0] - 80, v[1] - 80, v[2] + 80, v[3] + 80) for k, v in areas.items()}
    areas['ALL'] = (-2000, -900, 1200, 1500)
    areas['NORTH'] = (-1700, -1500, -200, -500)   # north field: maintenance / cargo / GA
    for name, (x0, z0, x1, z1) in areas.items():
        big = name in ('ALL', 'NORTH')
        W = 14 if big else 11
        fig, ax = plt.subplots(figsize=(W, W * (z1 - z0) / (x1 - x0) if x1 > x0 else W))
        for r in twy:
            ax.fill([p[0] for p in r], [-p[1] for p in r], color='#e8e8e8', lw=0)
        for r in rings:
            ax.fill([p[0] for p in r], [-p[1] for p in r], color='#c9d3e0', ec='#7a8aa0', lw=0.6)
        for s in S['stands']:
            x, z = s['nose']; f = X.hdg_vec(s['hdg']); c = '#1f5fbf' if s['src'] == 'obs' else '#e07b00'
            ax.plot([x, x - f[0] * 20], [-z, -(z - f[1] * 20)], color=c, lw=2)
            ax.plot(x, -z, 'o', color=c, ms=4)
            ax.annotate(s['name'] + ('/' + '/'.join(s['alias']) if s['alias'] else ''), (x, -z), fontsize=7 if not big else 4,
                        color=c, xytext=(3, 3), textcoords='offset points')
            for b in s['bridges']:
                ax.plot([b['attach'][0]], [-b['attach'][1]], 's', color='grey', ms=3)
        for p in osm['parking_positions']:
            pts = [X.wgs84_to_world(*q) for q in p['pts']]
            fx, fz = pts[0]; sx, sz = p['stop_w']
            ax.plot([q[0] for q in pts], [-q[1] for q in pts], color='#2a9d3a', lw=0.8, alpha=0.7)
            ax.plot(sx, -sz, 'o', color='#2a9d3a', ms=3)
            ax.plot(fx, -fz, 'x', color='#2a9d3a', ms=3)
            if p['ref']:
                ax.annotate(p['ref'], (sx, -sz), fontsize=6 if not big else 3.5, color='#2a9d3a', xytext=(-10, -8), textcoords='offset points')
        for j in osm['jet_bridges']:
            pts = [X.wgs84_to_world(*q) for q in j['pts']]
            ax.plot([q[0] for q in pts], [-q[1] for q in pts], color='#8e44ad', lw=1.2, alpha=0.8)
        for r in xp['ramp_starts']:
            x, z = X.wgs84_to_world(r['lat'], r['lon']); f = X.hdg_vec(r['hdg'])
            ax.plot(x, -z, marker=(3, 0, -r['hdg']), color='#d62728', ms=6, ls='none')
            ax.plot([x, x - f[0] * 12], [-z, -(z - f[1] * 12)], color='#d62728', lw=0.8)
            ax.annotate(r['name'].replace('Gate ', ''), (x, -z), fontsize=6 if not big else 3.5, color='#d62728', xytext=(3, -10), textcoords='offset points')
        for j in xp['jetways']:
            x, z = X.wgs84_to_world(j['lat'], j['lon']); f = X.hdg_vec(j['tunnel_hdg'])
            ax.plot(x, -z, '+', color='#b22222', ms=5)
            ax.plot([x, x + f[0] * j['tunnel_len_m']], [-z, -(z + f[1] * j['tunnel_len_m'])], color='#b22222', lw=0.8, ls='--')
        ax.set_xlim(x0, x1); ax.set_ylim(-z1, -z0); ax.set_aspect('equal')
        ax.set_title(f'{name}: ours (blue obs / orange inf, dot = nose) | OSM parking_position (green, dot = last node) | '
                     f'X-Plane 1300 (red triangle) + 1500 jetways (red +)\nData: (c) OpenStreetMap contributors (ODbL); '
                     f'X-Plane Scenery Gateway KSFO pack 112022 (GPL v2+); SFO Museum outlines', fontsize=8)
        ax.grid(alpha=0.3)
        fn = os.path.join(OUTD, f'stands_{name}.png')
        fig.savefig(fn, dpi=110 if not big else 160, bbox_inches='tight'); plt.close(fig)
        print('wrote', os.path.relpath(fn, X.ROOT))


if __name__ == '__main__':
    main()
