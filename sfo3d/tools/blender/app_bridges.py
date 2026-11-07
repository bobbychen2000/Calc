"""The app's jet-bridge levels and fixed solids for the 3-D building tools (close-out round 3, fix round 2: verifier
findings v1 / v6).

Source: tools/blender/app_bridges.json, written by `node tools/blender/app_bridges.mjs` from js/live/gates.js itself
(DEPARTURE_LEVELS per pier, the rotunda floor Hr, the fixed walkway polyline with its floor heights and the rest solids;
heights above the apron). The JSON records the SHA-256 of its inputs; `stale()` lists the inputs that changed since, and
the build / verify scripts report it (re-run the .mjs after any gates.js / sfo_stands change - it takes ~1 min, no browser).
Cross-checked 2026-11-07 against the browser extraction out/draw/scene2d.json of 10:35Z (git e87c2d2): 131 / 131 bridges,
Hb / Hr / rotR within 0.0005 m.

Levels (js/live/gates.js DEPARTURE_LEVELS, as tagged there): A / B 5.4 [inf], C 3.2 [inf], D 3.65 [obs, low],
E / F 4.88 [pub T3 L2], G 2.7 [obs, low].
"""
import hashlib
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PATH = os.path.join(HERE, 'app_bridges.json')
WALK_W, WALK_H = 2.6, 3.0           # js/live/gates.js WALK_W / WALK_H
WALK_LO = 0.3                       # gates.js ownWalk solids: floor - 0.3 .. floor + WALK_H
DRUM_LO, DRUM_HI = 0.3, 3.3         # gates.js solidsQ rotunda: G + Hr - 0.3 .. G + Hr + 3.3

_J = None


def load():
    global _J
    if _J is None:
        _J = json.load(open(PATH))
        _J['by_key'] = {(b['stand'], b['door'], b['upper']): b for b in _J['bridges']}
    return _J


def stale():
    """inputs whose SHA-256 differs from the one recorded in the dump ([] = current)."""
    J = load()
    out = []
    for p, h in J['inputs'].items():
        fp = os.path.join(ROOT, p)
        if not os.path.exists(fp) or hashlib.sha256(open(fp, 'rb').read()).hexdigest() != h: out.append(p)
    return out


def level(letter):
    """the pier's bridge level (DEPARTURE_LEVELS[letter]) -> dict(h, tag, src)."""
    J = load()
    return J['departure_levels'].get(letter) or dict(h=5.4, tag='inf', src='gates.js default DEPARTURE_LEVEL')


def bridge(stand, door, upper=False):
    return load()['by_key'].get((stand, door, bool(upper)))


def bridges(letters=None, upper=None):
    return [b for b in load()['bridges'] if (letters is None or b['letter'] in letters) and (upper is None or b['upper'] == upper)]


def _proj(walk, x, z):
    """arc length along the walk polyline [[x, y, z], ...] of the point nearest (x, z), and that point's floor."""
    best, s_acc = None, 0.0
    for i in range(1, len(walk)):
        ax, ay, az = walk[i - 1]; bx, by, bz = walk[i]
        dx, dz = bx - ax, bz - az; L2 = dx * dx + dz * dz; L = math.sqrt(L2)
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        px, pz = ax + dx * t, az + dz * t
        d = math.hypot(x - px, z - pz)
        if best is None or d < best[0]: best = (d, s_acc + t * L, ay + (by - ay) * t)
        s_acc += L
    return best


def floor_at(b, x, z):
    """the app walkway floor (above the apron) at the point of b's walk polyline nearest world (x, z) (gates.js walkY:
    linear from Hb at walk[0] to Hr at the rotunda)."""
    if len(b['walk']) < 2: return b['Hb']
    return _proj(b['walk'], x, z)[2]


def section(b, pts):
    """(floor_min, floor_max, lo, hi) of the app walkway over the walk points nearest the world points pts: lo / hi = the
    walkway solid's bottom / top (floor - 0.3 .. floor + 3.0)."""
    fl = [floor_at(b, x, z) for x, z in pts]
    return min(fl), max(fl), min(fl) - WALK_LO, max(fl) + WALK_H


def walkway_slices(b, step=1.0):
    """the bridge's rest fixed-walkway solids cut into <= step-m slices along the walkway, each with the band of the walkway
    solid THERE (floor - 0.3 .. floor + 3.0 at the slice ends; the solid boxes carry one min-max band per segment, which on a
    sloping walkway reaches below the floor of its high end): [(corners [(x, z) x 4], lo, hi)] above the apron."""
    out = []
    for so in b['rest']:
        if so['part'] != 'walkway': continue
        ux, uz = so['u']; vx, vz = -uz, ux; cx, cz = so['c']; hl, hw = so['hl'], so['hw']
        n = max(1, int(math.ceil(2.0 * hl / step)))
        for i in range(n):
            a0, a1 = -hl + 2.0 * hl * i / n, -hl + 2.0 * hl * (i + 1) / n
            P = [(cx + ux * a + vx * w, cz + uz * a + vz * w) for a, w in ((a0, -hw), (a1, -hw), (a1, hw), (a0, hw))]
            f = [floor_at(b, cx + ux * a, cz + uz * a) for a in (a0, a1)]
            out.append((P, max(so['lo'], min(f) - WALK_LO), min(so['hi'], max(f) + WALK_H)))
    return out


def drum_band(b):
    """the rotunda drum's height band above the apron (gates.js: Hr - 0.3 .. Hr + 3.3)."""
    return b['Hr'] - DRUM_LO, b['Hr'] + DRUM_HI


if __name__ == '__main__':
    J = load()
    print(len(J['bridges']), 'bridges; generated', J['generated'], '; stale inputs:', stale() or 'none')
    for k, v in J['departure_levels'].items(): print(' ', k, v['h'], v['tag'])
