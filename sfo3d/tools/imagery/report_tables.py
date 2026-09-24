"""Print the markdown tables used in docs/research/imagery.md from the JSON outputs in refs/cache/naip/.
usage: python3 tools/imagery/report_tables.py > /tmp/tables.md
"""
import json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE
from screens import REG

J = lambda n: json.load(open(os.path.join(CACHE, n)))


def main():
    ra = J('reg_audit.json'); corr = J('reg_naip.json')
    print('### Per-image residuals (registered - NAIP 2024; x east, z south, metres)\n')
    print('| image | m/px | view | ctrl pts ok/in view | dense ok | median r (x, z) | median abs r | p90 abs r | max | fit: translation at view centre | scale (ppm) | rotation (deg) | rms after fit | s in reg.json -> NAIP-corrected |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n, R in ra['images'].items():
        w = 1290 / R['s']; h = 1860 / R['s']
        if 'fit' not in R:
            print(f"| {n} | {R['m_per_px']:.2f} | {w:.0f} x {h:.0f} m | {R['n_cp_ok']}/{R['n_cp_in_view']} | {R['n_dense_ok']} | too few matches | | | | | | | | |"); continue
        f = R['fit']; c = corr.get(n, {})
        print(f"| {n} | {R['m_per_px']:.2f} | {w:.0f} x {h:.0f} m | {R['n_cp_ok']}/{R['n_cp_in_view']} | {R['n_dense_ok']} | "
              f"({R['median'][0]:+.2f}, {R['median'][1]:+.2f}) | {R['median_abs']:.2f} | {R['p90']:.2f} | {R['max']:.2f} | "
              f"({f['a'][0]:+.2f}, {f['a'][1]:+.2f}) | {f['scale_ppm']:+.0f} | {f['rot_deg']:+.3f} | {f['rms_after']:.2f} | "
              f"{R['s']:.4f} -> {c.get('s', float('nan')):.4f} |")
    print('\n### Named FAA control points (registered - NAIP, and registered - FAA)\n')
    print('| image | point | r vs NAIP (x, z) | abs | r vs FAA (x, z) | abs | NCC |')
    print('|---|---|---|---|---|---|---|')
    for n, R in ra['images'].items():
        for r in R['control_points']:
            if not r['id'].startswith(('RWY', 'X ')) or not r['ok']: continue
            a = r['resid']; b = r.get('resid_vs_faa', a)
            print(f"| {n} | {r['id']} | ({a[0]:+.2f}, {a[1]:+.2f}) | {math.hypot(*a):.2f} | ({b[0]:+.2f}, {b[1]:+.2f}) | {math.hypot(*b):.2f} | {r['ncc']:.2f} |")
    # control point coverage table: points x images
    cps = J('control_points.json')
    seen = {}
    for n, R in ra['images'].items():
        for r in R['control_points']:
            seen.setdefault(r['id'], []).append((n, r))
    print('\n### Control points: where each was measured (accepted matches only)\n')
    print('| id | kind / label | NAIP world (x, z) | images (residual abs, m) |')
    print('|---|---|---|---|')
    for cp in cps:
        rows = [(n, r) for n, r in seen.get(cp['id'], []) if r['ok']]
        if not rows: continue
        lab = cp.get('label', cp['kind'])
        print(f"| {cp['id']} | {lab} | ({cp['naip'][0]:.1f}, {cp['naip'][1]:.1f}) | " +
              ', '.join(f"{n} {math.hypot(*r['resid']):.1f}" for n, r in rows) + ' |')
    se = ra.get('stand_error_estimates', [])
    if se:
        from screens import sim_of
        stands = {x['name']: x for x in json.load(open(os.path.join(os.path.dirname(CACHE), '..', '..', 'data', 'sfo_stands.json')))['stands']}
        print('\n### Estimated stand-position error by source image (from the fitted residual field)\n')
        print('Stands whose nose projects outside the audited map area of their image (rows 340-2200, cols 10-1280) are '
              'extrapolations and counted separately.\n')
        print('| image | stands inside view | median abs err (m) | max (m) | outside view (extrapolated) |')
        print('|---|---|---|---|---|')
        by = {}
        for x in se:
            q = sim_of(x['img']).fwd(np.array([stands[x['stand']]['nose']]))[0]
            inside = 10 <= q[0] <= 1280 and 340 <= q[1] <= 2200
            by.setdefault(x['img'], []).append((x, inside))
        allin = []
        for k, v in sorted(by.items(), key=lambda kv: -np.median([x['err_m'] for x, i in kv[1] if i] or [0])):
            vin = [x['err_m'] for x, i in v if i]; allin += vin
            out = ', '.join(f"{x['stand']} ({x['src']}) {x['err_m']:.1f} m" for x, i in v if not i) or '-'
            print(f"| {k} | {len(vin)} | {np.median(vin):.2f} | {max(vin):.2f} | {out} |")
        a = np.array(allin)
        print(f"\nAll {len(a)} stands inside their image: median {np.median(a):.2f} m, p90 {np.percentile(a, 90):.2f} m, max {a.max():.2f} m; "
              f"> 3 m: {(a > 3).sum()}, > 5 m: {(a > 5).sum()}.")


if __name__ == '__main__':
    main()
