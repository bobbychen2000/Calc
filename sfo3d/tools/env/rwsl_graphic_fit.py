#!/usr/bin/env python3
"""Locate the REL taxiway labels of the FAA RWSL graphic for SFO in the app world frame (environment_spec.md 5.1 D1).

The graphic (https://www.faa.gov/air_traffic/technology/rwsl/media/SFO.pdf, public domain, cached in
refs/cache/lighting/rwsl_SFO.pdf, SOURCES.json beside it) is schematic. The lighting research placed 27 REL labels in
world coordinates (tools/env/build_lighting_spec.py RWSL_REL_XY, from an affine fit of the graphic's runway polygons to
the NASR runway ends) but missed taxiway N (verifier, docs/research/airfield_lighting.md 15 V23). This tool reads the
label word boxes with poppler's `pdftotext -bbox`, matches the 27 known labels by letter (unique letters first, then
nearest same-letter label after each affine fit), fits a 2-D affine PDF -> world by least squares and maps the
remaining label (N) through it.

Result 2026-11-05: 28 labels; residual of the 27 known anchors median 56 m, max 102 m (the anchors were label tabs,
the boxes are text centres; the graphic is schematic) -> N at world (759, 596), which the builder only uses to pick the
nearest same-name hold (taxiway N, 10R/28L, south side, ~104 m away).

Run: python3 tools/env/rwsl_graphic_fit.py   (needs pdftotext and numpy)
"""
import os, re, subprocess, sys, importlib.util
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PDF = os.path.join(ROOT, 'refs', 'cache', 'lighting', 'rwsl_SFO.pdf')
LETTERS = ('R', 'E', 'C', 'T', 'D', 'K', 'Q', 'F', 'N', 'G', 'H', 'M', 'F2', 'P', 'F1', 'L')


def main():
    html = subprocess.run(['pdftotext', '-bbox', PDF, '-'], capture_output=True, text=True, check=True).stdout
    W = [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in
         re.findall(r'xMin="([\d.]+)" yMin="([\d.-]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]+)<', html)]
    # taxiway labels: inside the drawing band (y 120-505 pt), excluding the runway designators' L/R (>= 16 pt wide)
    # or next to a runway number (10/19/28, rotated designators), and the large north arrow 'N' (outside the band)
    nums = [w for w in W if w[4] in ('10', '19', '28')]
    near_num = lambda w: any(abs((w[0] + w[2]) / 2 - (n[0] + n[2]) / 2) < 25 and abs((w[1] + w[3]) / 2 - (n[1] + n[3]) / 2) < 25 for n in nums)
    labels = [w for w in W if w[4] in LETTERS and 120 < w[1] < 505 and not (w[4] in ('L', 'R') and ((w[2] - w[0]) > 16 or near_num(w)))]
    spec = importlib.util.spec_from_file_location('b', os.path.join(ROOT, 'tools', 'env', 'build_lighting_spec.py'))
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    REL, XY = B.RWSL_REL[:27], B.RWSL_REL_XY[:27]          # the 27 research anchors (N is what we solve for)
    C = [((l[0] + l[2]) / 2, (l[1] + l[3]) / 2) for l in labels]
    uniq = [t for t in set(r[0] for r in REL) if sum(r[0] == t for r in REL) == 1 and sum(l[4] == t for l in labels) == 1]
    pairs = [(next(i for i, l in enumerate(labels) if l[4] == t), next(j for j, r in enumerate(REL) if r[0] == t)) for t in uniq]
    for _ in range(3):
        A = np.array([[C[i][0], C[i][1], 1] for i, _ in pairs]); Y = np.array([XY[j] for _, j in pairs])
        M = np.linalg.lstsq(A, Y, rcond=None)[0]
        used, pairs = set(), []
        for j, (t, _) in enumerate(REL):
            i = min((i for i, l in enumerate(labels) if l[4] == t and i not in used),
                    key=lambda i: np.hypot(*(np.array([C[i][0], C[i][1], 1]) @ M - XY[j])))
            used.add(i); pairs.append((i, j))
    res = [float(np.hypot(*(np.array([C[i][0], C[i][1], 1]) @ M - XY[j]))) for i, j in pairs]
    print('labels %d; affine fit of the 27 anchors: residual median %.0f m, max %.0f m' % (len(labels), np.median(res), max(res)))
    for i in sorted(set(range(len(labels))) - {p[0] for p in pairs}):
        w = (np.array([C[i][0], C[i][1], 1]) @ M).round(0)
        print('new label %s at pdf (%.1f, %.1f) pt -> world [%d, %d]' % (labels[i][4], C[i][0], C[i][1], w[0], w[1]))


if __name__ == '__main__':
    sys.exit(main())
