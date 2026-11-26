"""Openings kit: walls with holes, windows, doors and their glazing.

THE WALL FRAME (every builder here uses it)
    origin  a point on the wall's OUTER face, at the opening's bottom-left corner as seen from outside (world metres)
    right   unit horizontal vector along the wall, pointing to the right as seen from outside
    up      +Z
    out     the wall's outward normal = right x up (pass it only as a check; a mirrored frame is refused)
Local coordinates are written (x, z, y): x along `right`, z up, y along `out` (y > 0 is in front of the wall face,
y < 0 inside the wall).  All sizes are metres.  Works for any wall direction.

HOLES
    Every opening builder returns the rectangular hole it needs in its wall as (x0, z0, x1, z1), relative to ITS
    origin (so normally (0, 0, w, h)); shift() moves it to the wall's own coordinates and wall() cuts it.
    Facade does that book-keeping:   f = Facade(geo, origin, right, w, h);  f.add(window, x, z, 1.6, 1.5, n=2);  f.finish()

WHAT A BUILDER EMITS (material names; looks in web/viewer/looks/glazing.js)
    frame_black       clad frames, sashes, muntin bars          trim_white   casing, sill, drip cap (surfaces family)
    glass             every pane (see GLASS CODES)              door_navy    entry door, its frame and sidelights
    door_wood         mahogany dutch door                        door_garage  carriage garage doors
    hardware_black    levers, pulls                              threshold_bronze   door sills / slider tracks

GLASS CODES
    The glass is ONE quad per sash, behind the muntin bars.  Its look is a shader that fakes a lit room behind the
    pane (interior mapping) under a Fresnel reflection of the sky and tree line, so a pane needs to know where it is
    in "its" room.  That is packed into the pane's UVs (the GLB has no other vertex channel):
        u = 0.25 + x + 16 * (seed % 32 + 32 * wcode)       x: metres from the unit's left edge (< 15.5)
        v = 0.25 + z + 8 * (shade + 10 * room + 40 * hcode)  z: metres above the ROOM's floor (< 7.5)
    wcode = ceil(unit width / 0.5) (1..15), hcode = round((head height above the floor - 1.9) / 0.05) (0..24),
    shade = 0 automatic (a few seeds get a roller shade), 1 none, 2..9 a shade down (code - 1) * 0.3 m from the head,
    room  = ROOM_LIVING 0 (furnished, lit), ROOM_BARE 1 (garage / utility: bare, lit), ROOM_DARK 2 (lights off),
            ROOM_HALL 3 (shallow hall behind a door).
    Builders take: seed (int, one per opening: a different room), floor (height of the opening's bottom above the
    room's floor: 0 for doors, ~0.9 for windows), shade (None automatic, 0 none, 0..1 fraction of the opening
    height covered), room.

BUDGETS (triangles, as built by the test zone): window 2 sashes ~130, 3 sashes ~180, entry ~560, french pair ~200,
slider ~170, garage door ~330, corner glazing 4 + 3 sashes ~400.
"""
from __future__ import annotations

import math

import numpy as np

from model import materials as _materials
from model.kit import Geo, UP, _unit

ROOM_LIVING, ROOM_BARE, ROOM_DARK, ROOM_HALL = 0, 1, 2, 3

# ---- materials of this family (plain PBR fallback for the GLB; the viewer's looks are in glazing.js) -------------
_materials.register('frame_black', color=(0.012, 0.012, 0.014), roughness=0.40, metallic=0.25)
_materials.register('glass', color=(0.016, 0.026, 0.034), roughness=0.05)
_materials.register('door_navy', color=(0.016, 0.023, 0.052), roughness=0.34)
_materials.register('door_garage', color=(0.88, 0.87, 0.84), roughness=0.55)
_materials.register('door_wood', color=(0.105, 0.028, 0.012), roughness=0.38)
_materials.register('hardware_black', color=(0.010, 0.010, 0.011), roughness=0.36, metallic=0.85)
_materials.register('threshold_bronze', color=(0.030, 0.027, 0.024), roughness=0.42, metallic=0.8)


# =====================================================================================================================
# frame + low-level emitters
# =====================================================================================================================
class Frame:
    """The wall frame: o (origin), r (right), u (up), n (out).  p(x, z, y) -> world point."""

    def __init__(self, origin, right, out=None):
        self.o = np.asarray(origin, float)
        r = np.asarray(right, float).copy()
        r[2] = 0.0
        self.r = _unit(r)
        self.u = UP.copy()
        self.n = np.cross(self.r, self.u)
        if out is not None and float(np.dot(self.n, _unit(out))) < 0.9:
            raise ValueError('out must be right x up (right points to the right as seen from OUTSIDE the wall)')

    def p(self, x, z, y=0.0):
        return self.o + self.r * x + self.u * z + self.n * y

    def v(self, x, z, y):
        return self.r * x + self.u * z + self.n * y

    def at(self, x, z, y=0.0):
        return Frame(self.p(x, z, y), self.r)


class _B:
    """Emits quads / boxes / rings in a wall frame.  Local points are (x, z, y)."""

    def __init__(self, geo: Geo, F: Frame):
        self.g, self.F = geo, F

    def quad(self, mat, pts, hint, uv):
        """Four local points (any winding), a local direction the face must look to, four (u, v)."""
        P = np.array([self.F.p(*p) for p in pts])
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if np.linalg.norm(n) < 1e-12:
            n = np.cross(P[2] - P[0], P[3] - P[0])
        n = _unit(n)
        uv = np.asarray(uv, float)
        if float(n @ self.F.v(*hint)) < 0:
            P, uv, n = P[::-1], uv[::-1], -n
        self.g.mesh(mat).add(P, np.tile(n, (4, 1)), uv, [[0, 1, 2], [0, 2, 3]])

    def box(self, mat, x0, x1, z0, z1, y0, y1, faces='flrtb', swap=False):
        """Box x0..x1, z0..z1, y0..y1.  faces: f front (+out, at y1), k back, l left, r right, t top, b bottom.
        UVs in metres: front (x, z), sides (y, z), top / bottom (x, y); swap=True turns them a quarter turn (the
        grain of a horizontal member then runs along it)."""
        for f in faces:
            if f == 'f' or f == 'k':
                y = y1 if f == 'f' else y0
                pts = [(x0, z0, y), (x1, z0, y), (x1, z1, y), (x0, z1, y)]
                uv = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
                hint = (0, 0, 1 if f == 'f' else -1)
            elif f == 'l' or f == 'r':
                x = x0 if f == 'l' else x1
                pts = [(x, z0, y0), (x, z0, y1), (x, z1, y1), (x, z1, y0)]
                uv = [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]
                hint = (-1 if f == 'l' else 1, 0, 0)
            else:
                z = z1 if f == 't' else z0
                pts = [(x0, z, y0), (x1, z, y0), (x1, z, y1), (x0, z, y1)]
                uv = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                hint = (0, 1 if f == 't' else -1, 0)
            if swap:
                uv = [(b, a) for a, b in uv]
            self.quad(mat, pts, hint, uv)

    def ring(self, mat, x0, z0, x1, z1, wl, wr, wb, wt, yb, yf, outer=''):
        """A frame of four members (stiles full height, rails between them): front faces + the faces that look
        into the opening; outer = which outer edge faces to add ('l', 'r', 't', 'b')."""
        o = ''.join(c for c in outer if c in 'tb')
        self.box(mat, x0, x0 + wl, z0, z1, yb, yf, 'fr' + o + ('l' if 'l' in outer else ''))
        self.box(mat, x1 - wr, x1, z0, z1, yb, yf, 'fl' + o + ('r' if 'r' in outer else ''))
        if wb > 0:
            self.box(mat, x0 + wl, x1 - wr, z0, z0 + wb, yb, yf, 'ft' + ('b' if 'b' in outer else ''), swap=True)
        if wt > 0:
            self.box(mat, x0 + wl, x1 - wr, z1 - wt, z1, yb, yf, 'fb' + ('t' if 't' in outer else ''), swap=True)

    def glass(self, G, x0, z0, x1, z1, y, mat='glass'):
        pts = [(x0, z0, y), (x1, z0, y), (x1, z1, y), (x0, z1, y)]
        self.quad(mat, pts, (0, 0, 1), [G.uv(x0, z0), G.uv(x1, z0), G.uv(x1, z1), G.uv(x0, z1)])

    def lite(self, G, x0, z0, x1, z1, yg, lights=0, light_h=0.27, bar=0.028, ybar=None, mat='frame_black',
             glass_mat='glass'):
        """One sheet of glass x0..x1, z0..z1 at depth yg with this house's bar pattern: a horizontal bar light_h
        below the top and `lights` near-square lights above it (lights = 0: a clear pane)."""
        self.glass(G, x0, z0, x1, z1, yg, glass_mat)
        if lights < 1 or z1 - z0 < light_h + bar + 0.12:
            return
        ybar = yg + 0.018 if ybar is None else ybar
        zb = z1 - light_h - bar
        self.box(mat, x0, x1, zb, zb + bar, yg, ybar, 'ftb', swap=True)
        for i in range(1, int(lights)):
            xc = x0 + (x1 - x0) * i / lights
            self.box(mat, xc - bar / 2, xc + bar / 2, zb + bar, z1, yg, ybar, 'flr')

    def panel(self, mat, x0, z0, x1, z1, yf, depth=0.012, bevel=0.022, raised=0.0, margin=0.045):
        """A door panel sunk `depth` behind the face yf inside x0..x1, z0..z1, with a bevelled (sticking) edge;
        raised > 0 adds a raised field `margin` inside the bevel, standing `raised` proud of the sunk ground."""
        self._tray(mat, x0, z0, x1, z1, yf, yf - depth, bevel, fill=raised <= 0)
        if raised > 0:
            a, b = x0 + bevel, x1 - bevel
            c, d = z0 + bevel, z1 - bevel
            yg = yf - depth
            m = margin
            # the sunk ground as a ring round the field, then the field with its own bevel
            self.quad(mat, [(a, c, yg), (b, c, yg), (b - m, c + m, yg), (a + m, c + m, yg)], (0, 0, 1),
                      [(a, c), (b, c), (b - m, c + m), (a + m, c + m)])
            self.quad(mat, [(a + m, d - m, yg), (b - m, d - m, yg), (b, d, yg), (a, d, yg)], (0, 0, 1),
                      [(a + m, d - m), (b - m, d - m), (b, d), (a, d)])
            self.quad(mat, [(a, c, yg), (a + m, c + m, yg), (a + m, d - m, yg), (a, d, yg)], (0, 0, 1),
                      [(a, c), (a + m, c + m), (a + m, d - m), (a, d)])
            self.quad(mat, [(b - m, c + m, yg), (b, c, yg), (b, d, yg), (b - m, d - m, yg)], (0, 0, 1),
                      [(b - m, c + m), (b, c), (b, d), (b - m, d - m)])
            self._tray(mat, a + m, c + m, b - m, d - m, yg, yg + raised, 0.014, fill=True)

    def _tray(self, mat, x0, z0, x1, z1, ya, yb, bevel, fill=True):
        """Four bevel faces from the rectangle at depth ya to the rectangle `bevel` inside it at depth yb (+ it)."""
        a, b, c, d = x0 + bevel, x1 - bevel, z0 + bevel, z1 - bevel
        s = 1.0 if yb < ya else -1.0          # sunk: bevels look inward; raised: outward
        self.quad(mat, [(x0, z0, ya), (x1, z0, ya), (b, c, yb), (a, c, yb)], (0, s, 0.5),
                  [(x0, z0), (x1, z0), (b, c), (a, c)])
        self.quad(mat, [(a, d, yb), (b, d, yb), (x1, z1, ya), (x0, z1, ya)], (0, -s, 0.5),
                  [(a, d), (b, d), (x1, z1), (x0, z1)])
        self.quad(mat, [(x0, z0, ya), (a, c, yb), (a, d, yb), (x0, z1, ya)], (s, 0, 0.5),
                  [(x0, z0), (a, c), (a, d), (x0, z1)])
        self.quad(mat, [(b, c, yb), (x1, z0, ya), (x1, z1, ya), (b, d, yb)], (-s, 0, 0.5),
                  [(b, c), (x1, z0), (x1, z1), (b, d)])
        if fill:
            self.quad(mat, [(a, c, yb), (b, c, yb), (b, d, yb), (a, d, yb)], (0, 0, 1), [(a, c), (b, c), (b, d), (a, d)])

    def planks(self, mat, x0, z0, x1, z1, y, n=6, groove=0.006, depth=0.005):
        """Vertical boards with V grooves between them (tongue-and-groove panel) at depth y."""
        n = max(1, int(n))
        pw = (x1 - x0) / n
        for k in range(n):
            a = x0 + k * pw + (groove if k else 0.0)
            b = x0 + (k + 1) * pw - (groove if k < n - 1 else 0.0)
            self.quad(mat, [(a, z0, y), (b, z0, y), (b, z1, y), (a, z1, y)], (0, 0, 1),
                      [(a, z0), (b, z0), (b, z1), (a, z1)])
            if k < n - 1:
                c = x0 + (k + 1) * pw
                self.quad(mat, [(b, z0, y), (c, z0, y - depth), (c, z1, y - depth), (b, z1, y)], (1, 0, 1),
                          [(b, z0), (c, z0), (c, z1), (b, z1)])
                self.quad(mat, [(c, z0, y - depth), (c + groove, z0, y), (c + groove, z1, y), (c, z1, y - depth)],
                          (-1, 0, 1), [(c, z0), (c + groove, z0), (c + groove, z1), (c, z1)])

    def casing(self, w, h, cw, ct, setback, mat='trim_white', head=None, sill=True, drip=True, ears=0.0,
               sides='lr', ext_l=None, ext_r=None, apron=0.0, sill_proj=0.045, sill_t=0.045, ov=0.002):
        """Flat casing round the hole 0..w, 0..h: jamb boards (width cw, or (left, right)), a head board (height
        head, default the jamb width) with an optional drip cap, a sloped projecting sill (windows) and an apron.
        The boards stand ct proud of the wall face and return `setback` into the hole, onto the unit's frame.
        sides: which jamb boards to build; ext_l / ext_r: how far the head and sill run past the hole."""
        cl, cr = (cw, cw) if np.isscalar(cw) else cw
        head = max(cl, cr) if head is None else head
        el = cl + ears if ext_l is None else ext_l
        er = cr + ears if ext_r is None else ext_r
        if 'l' in sides and cl > 0:
            self.box(mat, -cl, ov, 0.0, h, -setback, ct, 'flr')
        if 'r' in sides and cr > 0:
            self.box(mat, w - ov, w + cr, 0.0, h, -setback, ct, 'flr')
        if head > 0:
            self.box(mat, -el, w + er, h - ov, h + head, -setback, ct, 'fbtlr', swap=True)
            if drip:
                self.box(mat, -el - 0.012, w + er + 0.012, h + head, h + head + 0.014, 0.0, ct + 0.018, 'ftblr',
                         swap=True)
        if sill:
            a, b = -el - 0.02, w + er + 0.02
            zt = -0.008                                   # the nose is 8 mm lower than the back: water runs off
            self.quad(mat, [(a, 0.0, -setback), (b, 0.0, -setback), (b, zt, sill_proj), (a, zt, sill_proj)],
                      (0, 1, 0), [(a, -setback), (b, -setback), (b, sill_proj), (a, sill_proj)])
            self.quad(mat, [(a, -sill_t, sill_proj), (b, -sill_t, sill_proj), (b, zt, sill_proj), (a, zt, sill_proj)],
                      (0, 0, 1), [(a, -sill_t), (b, -sill_t), (b, zt), (a, zt)])
            self.quad(mat, [(a, -sill_t, 0.0), (b, -sill_t, 0.0), (b, -sill_t, sill_proj), (a, -sill_t, sill_proj)],
                      (0, -1, 0), [(a, 0.0), (b, 0.0), (b, sill_proj), (a, sill_proj)])
            for x, s in ((a, -1), (b, 1)):
                self.quad(mat, [(x, -sill_t, 0.0), (x, -sill_t, sill_proj), (x, zt, sill_proj), (x, 0.0, 0.0)],
                          (s, 0, 0), [(0.0, -sill_t), (sill_proj, -sill_t), (sill_proj, zt), (0.0, 0.0)])
            if apron > 0:
                self.box(mat, -cl, w + cr, -sill_t - apron, -sill_t, 0.0, ct * 0.8, 'fblr', swap=True)

    def lever(self, mat, x, z, y, direction=1.0, plate_h=0.24):
        """Lever handle on a long backplate: centre (x, z) on the face at depth y; the lever points along
        direction * right."""
        self.box(mat, x - 0.022, x + 0.022, z - plate_h * 0.62, z + plate_h * 0.38, y, y + 0.007, 'flrtb')
        self.box(mat, x - 0.013, x + 0.013, z - 0.013, z + 0.013, y + 0.007, y + 0.05, 'flrtb')
        a, b = sorted((x - 0.011 * direction, x + 0.125 * direction))
        self.box(mat, a, b, z - 0.010, z + 0.010, y + 0.040, y + 0.056, 'fklrtb')

    def pull(self, mat, x, z, y, h=0.20, w=0.028):
        """Flush pull of a sliding panel: a recessed plate centred at (x, z) on the face at depth y."""
        self.box(mat, x - w / 2, x + w / 2, z - h / 2, z + h / 2, y, y + 0.004, 'flrtb')
        self.box(mat, x - w / 2 + 0.007, x + w / 2 - 0.007, z - h / 2 + 0.03, z + h / 2 - 0.03, y + 0.004, y + 0.0055,
                 'f')


class _GlassCode:
    """UV packing of a pane (see GLASS CODES in the module docstring)."""

    def __init__(self, w, h, floor=0.0, seed=0, shade=None, room=ROOM_LIVING, head=None):
        floor = max(0.0, float(floor))
        head = floor + h if head is None else head
        wcode = int(min(15, max(1, math.ceil(w / 0.5 - 1e-6))))
        hcode = int(min(24, max(0, round((head - 1.9) / 0.05))))
        if shade is None:
            sc = 0
        else:
            sc = 1 + int(min(8, max(0, round(float(shade) * h / 0.3))))
        self.du = 0.25 + 16.0 * (int(seed) % 32 + 32 * wcode)
        self.dv = 0.25 + floor + 8.0 * (sc + 10 * (int(room) % 4) + 40 * hcode)

    def uv(self, x, z):
        return (min(max(x, 0.0), 15.5) + self.du, min(max(z, -0.2), 7.2) + self.dv)


# =====================================================================================================================
# wall with holes
# =====================================================================================================================
def shift(hole, x, z):
    """A hole returned by a builder placed at (x, z) of a wall -> the wall's own coordinates."""
    return (hole[0] + x, hole[1] + z, hole[2] + x, hole[3] + z)


def wall(geo, mat, origin, right, w, h, holes=(), thickness=0.15, out=None, reveal=True, reveal_mat='trim_white',
         uv_origin=None):
    """A wall's outer face w x h (origin = its bottom-left corner seen from outside) with rectangular holes
    [(x0, z0, x1, z1), ...] in wall coordinates, plus the reveal faces of every hole, `thickness` deep.

    Holes may touch or cross the wall's edges (doors down to z = 0, a notch at a corner) and each other: the face
    is rebuilt from the cells the holes leave.  UVs: u = metres along the wall from the origin, v = WORLD z, so
    siding courses line up from wall to wall (uv_origin overrides the point that gets uv (0, 0))."""
    F = Frame(origin, right, out)
    rects = []
    for x0, z0, x1, z1 in holes:
        x0, x1, z0, z1 = max(0.0, x0), min(w, x1), max(0.0, z0), min(h, z1)
        if x1 - x0 > 1e-6 and z1 - z0 > 1e-6:
            rects.append((x0, z0, x1, z1))
    xs = _breaks([0.0, w] + [r[0] for r in rects] + [r[2] for r in rects])
    zs = _breaks([0.0, h] + [r[1] for r in rects] + [r[3] for r in rects])
    filled = [[not any(r[0] - 1e-9 <= (xs[i] + xs[i + 1]) / 2 <= r[2] + 1e-9 and
                       r[1] - 1e-9 <= (zs[j] + zs[j + 1]) / 2 <= r[3] + 1e-9 for r in rects)
               for j in range(len(zs) - 1)] for i in range(len(xs) - 1)]
    uvo = np.array([F.o[0], F.o[1], 0.0]) if uv_origin is None else np.asarray(uv_origin, float)
    for outer, inner in _region_loops(xs, zs, filled):
        geo.poly(mat, [F.p(x, z) for x, z in outer], holes=[[F.p(x, z) for x, z in r] for r in inner], uv_u=F.r,
                 uv_o=uvo)
    if reveal and thickness > 0:
        b = _B(geo, F)
        for x0, z0, x1, z1 in rects:
            if x0 > 1e-6:
                b.box(reveal_mat, x0 - 1.0, x0, z0, z1, -thickness, 0.0, 'r')
            if x1 < w - 1e-6:
                b.box(reveal_mat, x1, x1 + 1.0, z0, z1, -thickness, 0.0, 'l')
            if z1 < h - 1e-6:
                b.box(reveal_mat, x0, x1, z1, z1 + 1.0, -thickness, 0.0, 'b')
            if z0 > 1e-6:
                b.box(reveal_mat, x0, x1, z0 - 1.0, z0, -thickness, 0.0, 't')
    return F


def _breaks(vals):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > 1e-6:
            out.append(float(v))
    return out


def _region_loops(xs, zs, filled):
    """Outlines of the filled cells of a rectilinear grid: [(outer ring, [hole rings])], rings as (x, z) lists,
    outer rings counter-clockwise."""
    nx, nz = len(xs) - 1, len(zs) - 1
    nxt = {}

    def edge(a, b):
        nxt.setdefault(a, []).append(b)

    for i in range(nx):
        for j in range(nz):
            if not filled[i][j]:
                continue
            if j == 0 or not filled[i][j - 1]:
                edge((i, j), (i + 1, j))
            if i == nx - 1 or not filled[i + 1][j]:
                edge((i + 1, j), (i + 1, j + 1))
            if j == nz - 1 or not filled[i][j + 1]:
                edge((i + 1, j + 1), (i, j + 1))
            if i == 0 or not filled[i - 1][j]:
                edge((i, j + 1), (i, j))
    rings = []
    while nxt:
        start = next(iter(nxt))
        ring, cur, prev = [start], start, None
        while True:
            cands = nxt[cur]
            if len(cands) > 1 and prev is not None:        # a pinch: turn left, stay with the same cell
                d = (cur[0] - prev[0], cur[1] - prev[1])
                cands.sort(key=lambda c: -(d[0] * (c[1] - cur[1]) - d[1] * (c[0] - cur[0])))
            b = cands.pop(0)
            if not cands:
                del nxt[cur]
            prev, cur = cur, b
            if cur == start:
                break
            ring.append(cur)
        pts = []
        m = len(ring)
        for k in range(m):                                  # drop the collinear grid vertices
            a, c, e = ring[k - 1], ring[k], ring[(k + 1) % m]
            if (c[0] - a[0]) * (e[1] - c[1]) - (c[1] - a[1]) * (e[0] - c[0]) != 0:
                pts.append((xs[c[0]], zs[c[1]]))
        rings.append(pts)

    def area(r):
        return sum(r[k][0] * r[(k + 1) % len(r)][1] - r[(k + 1) % len(r)][0] * r[k][1] for k in range(len(r))) / 2

    def inside(p, r):
        c = False
        for k in range(len(r)):
            (ax, az), (bx, bz) = r[k], r[(k + 1) % len(r)]
            if (az > p[1]) != (bz > p[1]) and p[0] < ax + (p[1] - az) * (bx - ax) / (bz - az):
                c = not c
        return c

    outers = [[r, []] for r in rings if area(r) > 0]
    for r in rings:
        if area(r) < 0:
            # a point just outside the hole, on the filled side of its first edge
            (ax, az), (bx, bz) = r[0], r[1]
            d = np.array([bx - ax, bz - az])
            d = d / max(np.linalg.norm(d), 1e-12)
            p = ((ax + bx) / 2 - d[1] * 1e-4, (az + bz) / 2 + d[0] * 1e-4)
            for o in outers:
                if inside(p, o[0]):
                    o[1].append(r)
                    break
    return [(o[0], o[1]) for o in outers]


class Facade:
    """A wall that collects its openings:  f = Facade(geo, origin, right, w, h, mat='siding_lap');
    f.add(window, x, z, 1.6, 1.5, n=2, lights=2)  (the builder's own arguments after x, z);  f.finish() cuts the
    wall.  add() returns what the builder returned; f.holes may also be appended to directly."""

    def __init__(self, geo, origin, right, w, h, mat='siding_lap', thickness=0.15, out=None, reveal_mat='trim_white'):
        self.geo, self.F, self.w, self.h, self.mat = geo, Frame(origin, right, out), w, h, mat
        self.thickness, self.reveal_mat, self.holes = thickness, reveal_mat, []

    def add(self, builder, x, z, *args, **kw):
        r = builder(self.geo, self.F.p(x, z), self.F.r, *args, **kw)
        for hole in (r if r and not np.isscalar(r[0]) else [r]):
            self.holes.append(shift(hole, x, z))
        return r

    def finish(self, **kw):
        return wall(self.geo, self.mat, self.F.o, self.F.r, self.w, self.h, self.holes, self.thickness,
                    reveal_mat=self.reveal_mat, **kw)


# =====================================================================================================================
# windows
# =====================================================================================================================
def window(geo, origin, right, w, h, n=2, lights=2, light_h=0.27, widths=None, fixed=(), mull=0.028, frame=0.05,
           stile=0.045, bar=0.028, setback=0.035, casing=0.09, casing_t=0.022, head=None, sill=True, drip=True,
           ears=0.0, apron=0.0, sides='lr', ext_l=None, ext_r=None, seed=0, floor=0.9, shade=None, room=ROOM_LIVING,
           out=None, frame_mat='frame_black', casing_mat='trim_white', glass_mat='glass'):
    """This house's window: a black clad unit w x h (outside of the black frame) of n sashes mulled side by side,
    every sash one tall clear pane under a row of `lights` near-square lights (a number, or one per sash; 0 = a
    clear sash), in a white flat casing with a projecting sloped sill and a drip cap.

    widths: relative sash widths (default equal); fixed: indices of fixed sashes (glass in a slim stop instead of
    a casement sash: the picture centre of a three-part unit); mull: the post between two sashes (0.028 inside one
    frame, ~0.11 between mulled units); light_h: glass height of the top lights; setback: the frame's face behind
    the wall face.  Typical units: 1.65 x 1.5 n=2 (gable rooms), 0.9 x 0.5 n=1 lights=0 (short wide, upper floor),
    0.75 x 1.3 n=1 (single), 0.9 x 2.3 n=1 floor=0.1 (tall narrow).  Returns the hole (0, 0, w, h)."""
    F = Frame(origin, right, out)
    b = _B(geo, F)
    G = _GlassCode(w, h, floor, seed, shade, room)
    yf = -setback
    ys = yf - 0.012                                    # casement sash face
    yg = ys - 0.022                                    # glass
    b.ring(frame_mat, 0.0, 0.0, w, h, frame, frame, frame, frame, yf - 0.09, yf)
    n = max(1, int(n))
    lights = [lights] * n if np.isscalar(lights) else list(lights)
    rel = np.ones(n) if widths is None else np.asarray(widths, float)
    clear = w - 2 * frame - (n - 1) * mull
    ws = clear * rel / rel.sum()
    xa = frame
    for i in range(n):
        xb = xa + ws[i]
        if i:
            b.box(frame_mat, xa - mull, xa, frame, h - frame, ys, yf, 'flr')
        if i in fixed:
            st, sb, face = 0.020, 0.020, yf - 0.006
        else:
            st, sb, face = stile, stile + 0.012, ys
        b.ring(frame_mat, xa, frame, xb, h - frame, st, st, sb, st, yg, face)
        b.lite(G, xa + st, frame + sb, xb - st, h - frame - st, yg, lights[i], light_h, bar, face - 0.003, frame_mat,
               glass_mat)
        xa = xb + mull
    if casing or sill:
        b.casing(w, h, casing, casing_t, setback, casing_mat, head=head, sill=sill, drip=drip, ears=ears,
                 sides=sides, ext_l=ext_l, ext_r=ext_r, apron=apron)
    return (0.0, 0.0, w, h)


def bay_window(geo, origin, right, w=2.87, h=1.98, n=3, lights=2, mull=0.11, fixed=(1,), project=0.0, **kw):
    """The three-part window of the right front wing (under its metal awning): three near-equal sashes with wide
    posts between them, the centre one fixed.  In the photos it sits in the plane of the wall (project = 0); with
    project > 0 it becomes a box bay standing that far out of the wall on white cheeks, a seat board and a head.
    Other arguments as window().  Returns the hole (0, 0, w, h)."""
    if project <= 0:
        return window(geo, origin, right, w, h, n=n, lights=lights, mull=mull, fixed=fixed, **kw)
    F = Frame(origin, right, kw.get('out'))
    b = _B(geo, F)
    mat = kw.get('casing_mat', 'trim_white')
    c = kw.get('casing', 0.09)
    kw = dict(kw, casing=0.0, sill=False)
    window(geo, F.p(0.0, 0.0, project), right, w, h, n=n, lights=lights, mull=mull, fixed=fixed, **kw)
    b.box(mat, -c, 0.002, -c, h + c, 0.0, project + 0.022, 'flr')                    # cheeks
    b.box(mat, w - 0.002, w + c, -c, h + c, 0.0, project + 0.022, 'flr')
    b.box(mat, -c - 0.02, w + c + 0.02, h - 0.002, h + c, 0.0, project + 0.04, 'ftblr', swap=True)   # head
    b.box(mat, -c - 0.02, w + c + 0.02, -c, 0.0, 0.0, project + 0.05, 'ftblr', swap=True)          # seat board
    return (0.0, 0.0, w, h)


def corner_glazing(geo, corner, dir_a, dir_b, wa, wb, h, na=4, nb=3, lights=2, post=0.14, light_h=0.27,
                   seed=0, floor=0.75, shade=None, room=ROOM_LIVING, casing=0.09, setback=0.035,
                   frame_mat='frame_black', casing_mat='trim_white', **kw):
    """The upper-floor glass corner room: two banks of sashes that wrap an outside corner of the building and meet
    at one slim dark corner post, under one head casing and over one sill.

    corner: the building's outer corner point at the glazing's bottom (sill) height; dir_a / dir_b: unit horizontal
    vectors along the two walls, pointing AWAY from the corner; wa / wb: width of each bank measured from the
    corner (the post takes the first `post` of both); h: height; na / nb sashes with `lights` top lights each.
    Both banks look into the same room (seed).  Returns the two holes [(0, 0, wa, h), (0, 0, wb, h)] as distances
    FROM THE CORNER along dir_a and dir_b: in a wall whose right end is the corner the hole is (W - wa, z, W, z + h)."""
    corner = np.asarray(corner, float)
    da, db = _unit(np.asarray(dir_a, float) * (1, 1, 0)), _unit(np.asarray(dir_b, float) * (1, 1, 0))
    G = dict(lights=lights, light_h=light_h, seed=seed, floor=floor, shade=shade, room=room, casing=casing,
             setback=setback, frame_mat=frame_mat, casing_mat=casing_mat, **kw)
    reach = 0.022 + 0.05                                   # the head / sill of one wall runs past the corner
    for d, other, width, n in ((da, db, wa, na), (db, da, wb, nb)):
        o = np.cross(d, UP)
        if o @ other > 0:
            o = -o                                         # outward: away from the other wall's side
        r = np.cross(UP, o)                                # right as seen from outside
        if r @ d > 0:                                      # the corner is this bank's LEFT end
            window(geo, corner + d * post, r, width - post, h, n=n, sides='r', ext_l=post + reach, **G)
            F = Frame(corner, r)
            _B(geo, F).box(frame_mat, 0.0, post, 0.0, h, -setback - post, -setback, 'f')
        else:                                              # ... its RIGHT end
            window(geo, corner + d * width, r, width - post, h, n=n, sides='l', ext_r=post + reach, **G)
            F = Frame(corner + d * post, r)
            _B(geo, F).box(frame_mat, 0.0, post, 0.0, h, -setback - post, -setback, 'f')
    return [(0.0, 0.0, wa, h), (0.0, 0.0, wb, h)]


# =====================================================================================================================
# doors
# =====================================================================================================================
def entry_door(geo, origin, right, w=1.86, h=2.46, door_w=1.0, lights=3, side_lights=2, split=0.93, light_h=0.26,
               hinge='l', setback=0.03, casing=0.055, casing_t=0.02, seed=0, shade=0, room=ROOM_HALL, out=None,
               mat='door_navy', hw_mat='hardware_black', casing_mat='trim_white', glass_mat='glass',
               threshold_mat='threshold_bronze'):
    """The front door: a deep-navy DUTCH door (leaf split at `split`; glazed upper leaf = a tall pane under
    `lights` top lights, lower leaf two raised panels, a ledge on the split, lever on the upper leaf) between two
    direct-glazed sidelights (`side_lights` top lights over a tall pane, a low bottom rail), frame and sidelights
    in the door's colour, in a narrow white casing.  w x h = outside of the frame; door_w = leaf width; hinge 'l' /
    'r' = hinge side seen from outside.  Returns the hole (0, 0, w, h)."""
    F = Frame(origin, right, out)
    b = _B(geo, F)
    G = _GlassCode(w, h, 0.0, seed, shade, room)
    jamb, post, headf, thr = 0.06, 0.07, 0.05, 0.022
    sw = (w - 2 * jamb - 2 * post - door_w) / 2
    yf = -setback
    yb = yf - 0.11
    b.ring(mat, 0.0, 0.0, w, h, jamb, jamb, 0.0, headf, yb, yf)
    b.box(threshold_mat, jamb, w - jamb, 0.0, thr, yb, yf + 0.04, 'ft', swap=True)
    top = h - headf
    xd0 = jamb + sw + post
    xd1 = xd0 + door_w
    # sidelights (direct glazed) and the posts beside the door
    for xa in (jamb, xd1 + post):
        xb = xa + sw
        b.box(mat, (xb if xa == jamb else xa - post), (xb + post if xa == jamb else xa), thr, top, yb, yf, 'flr')
        ys = yf - 0.010
        b.ring(mat, xa, thr, xb, top, 0.022, 0.022, 0.19, 0.035, ys - 0.025, ys)
        b.lite(G, xa + 0.022, thr + 0.19, xb - 0.022, top - 0.035, ys - 0.025, side_lights, light_h + 0.085, 0.028,
               ys - 0.003, mat, glass_mat)
    # the leaf: 3 mm shadow gaps to the posts, the two halves 4 mm apart
    g = 0.003
    a, c = xd0 + g, xd1 - g
    yl = yf - 0.016                                      # leaf face
    ylb = yl - 0.045
    st = 0.135
    # lower leaf
    z0, z1 = thr + 0.004, split
    b.ring(mat, a, z0, c, z1, st, st, 0.20, 0.11, ylb, yl, outer='t')
    mid = 0.11
    xm = (a + c) / 2
    b.box(mat, xm - mid / 2, xm + mid / 2, z0 + 0.20, z1 - 0.11, ylb, yl, 'f')
    for pa, pb in ((a + st, xm - mid / 2), (xm + mid / 2, c - st)):
        b.panel(mat, pa, z0 + 0.20, pb, z1 - 0.11, yl, depth=0.014, bevel=0.02, raised=0.008, margin=0.04)
    # ledge of the dutch split
    b.box(mat, a - 0.002, c + 0.002, split - 0.014, split + 0.020, yl, yl + 0.038, 'ftblr', swap=True)
    # upper leaf
    z0, z1 = split + 0.004, top - g
    b.ring(mat, a, z0, c, z1, st, st, 0.125, 0.14, ylb, yl, outer='b')
    yg = yl - 0.024
    b.lite(G, a + st, z0 + 0.125, c - st, z1 - 0.14, yg, lights, light_h, 0.028, yl - 0.004, mat, glass_mat)
    # lever on the latch stile of the upper leaf
    if hinge == 'l':
        b.lever(hw_mat, c - st / 2, 1.20, yl, direction=-1.0)
    else:
        b.lever(hw_mat, a + st / 2, 1.20, yl, direction=1.0)
    if casing:
        b.casing(w, h, casing, casing_t, setback, casing_mat, sill=False, drip=False)
    return (0.0, 0.0, w, h)


def french_doors(geo, origin, right, w=2.10, h=2.42, leaves=2, lights=3, side_l=0.0, side_r=0.0, side_lights=2,
                 light_h=0.26, handles=True, setback=0.03, casing=0.055, casing_t=0.02, seed=0, shade=None,
                 room=ROOM_LIVING, out=None, frame_mat='frame_black', hw_mat='hardware_black',
                 casing_mat='trim_white', glass_mat='glass', threshold_mat='threshold_bronze'):
    """Glazed french doors of the porch: `leaves` narrow-stile door leaves, each a tall pane under `lights` top
    lights, optionally with fixed sidelights of clear width side_l / side_r (side_lights top lights) mulled on.
    The unit left of the entry: w 2.10, h 2.42, leaves 2, lights 3; right of it: w 2.35, h 2.2, side_r 0.42.
    Returns the hole (0, 0, w, h)."""
    F = Frame(origin, right, out)
    b = _B(geo, F)
    G = _GlassCode(w, h, 0.0, seed, shade, room)
    fr, post, thr = 0.04, 0.05, 0.02
    yf = -setback
    yb = yf - 0.10
    b.ring(frame_mat, 0.0, 0.0, w, h, fr, fr, 0.0, fr, yb, yf)
    b.box(threshold_mat, fr, w - fr, 0.0, thr, yb, yf + 0.04, 'ft', swap=True)
    top = h - fr
    x0, x1 = fr, w - fr
    st, rt, rb = 0.068, 0.072, 0.11
    yl = yf - 0.014
    yg = yl - 0.022

    def sidelight(xa, xb):
        b.ring(frame_mat, xa, thr, xb, top, 0.03, 0.03, rb, 0.035, yg, yf - 0.008)
        b.lite(G, xa + 0.03, thr + rb, xb - 0.03, top - 0.035, yg, side_lights, light_h + 0.037, 0.028, yl - 0.003,
               frame_mat, glass_mat)

    if side_l > 0:
        sidelight(x0, x0 + side_l)
        b.box(frame_mat, x0 + side_l, x0 + side_l + post, thr, top, yb, yf, 'flr')
        x0 += side_l + post
    if side_r > 0:
        sidelight(x1 - side_r, x1)
        b.box(frame_mat, x1 - side_r - post, x1 - side_r, thr, top, yb, yf, 'flr')
        x1 -= side_r + post
    leaves = max(1, int(leaves))
    lw = (x1 - x0) / leaves
    for i in range(leaves):
        a, c = x0 + i * lw + 0.002, x0 + (i + 1) * lw - 0.002
        b.ring(frame_mat, a, thr + 0.004, c, top - 0.003, st, st, rb, rt, yg, yl)
        b.lite(G, a + st, thr + 0.004 + rb, c - st, top - 0.003 - rt, yg, lights, light_h, 0.028, yl - 0.003,
               frame_mat, glass_mat)
        if i:                                              # astragal over the meeting stiles
            b.box(frame_mat, a - 0.012, a + 0.010, thr + 0.004, top - 0.003, yl, yl + 0.008, 'flr')
    if handles and leaves >= 1:
        k = leaves // 2                                    # the active leaf: right of the middle joint
        if leaves == 1:
            b.lever(hw_mat, x1 - st / 2, 1.0, yl, direction=-1.0)
        else:
            b.lever(hw_mat, x0 + k * lw + st / 2 + 0.004, 1.0, yl, direction=1.0)
            b.lever(hw_mat, x0 + k * lw - st / 2 - 0.004, 1.0, yl, direction=-1.0)
    if casing:
        b.casing(w, h, casing, casing_t, setback, casing_mat, sill=False, drip=False)
    return (0.0, 0.0, w, h)


def slider(geo, origin, right, w=3.7, h=2.44, panels=2, lights=5, light_h=0.27, pulls=True, setback=0.03,
           casing=0.055, casing_t=0.02, seed=0, shade=None, room=ROOM_LIVING, out=None, frame_mat='frame_black',
           hw_mat='hardware_black', casing_mat='trim_white', glass_mat='glass', threshold_mat='threshold_bronze'):
    """The big rear multi-panel sliding door: `panels` wide glazed panels on two tracks (the left one in front),
    their meeting stiles overlapping, each panel a tall pane under a row of `lights` top lights; flush pulls on the
    outer stiles, a bronze track sill.  Family room: w 3.7, lights 5; bedroom: w 2.6, lights 3; cabana: w 2.9,
    lights 3.  Returns the hole (0, 0, w, h)."""
    F = Frame(origin, right, out)
    b = _B(geo, F)
    G = _GlassCode(w, h, 0.0, seed, shade, room)
    fr, st, rt, rb, thr = 0.05, 0.085, 0.085, 0.10, 0.03
    yf = -setback
    yb = yf - 0.13
    b.ring(frame_mat, 0.0, 0.0, w, h, fr, fr, 0.0, fr, yb, yf)
    b.box(threshold_mat, fr, w - fr, 0.0, thr, yb, yf + 0.05, 'ft', swap=True)
    panels = max(1, int(panels))
    pw = (w - 2 * fr + (panels - 1) * st) / panels
    top = h - fr
    for i in range(panels):
        a = fr + i * (pw - st)
        c = a + pw
        face = yf - 0.012 - (0.045 if i % 2 else 0.0)
        outer = ('r' if i < panels - 1 and not i % 2 else '') + ('l' if i and not i % 2 else '')
        b.ring(frame_mat, a, thr, c, top, st, st, rb, rt, face - 0.04, face, outer=outer)
        b.lite(G, a + st, thr + rb, c - st, top - rt, face - 0.024, lights, light_h, 0.028, face - 0.003, frame_mat,
               glass_mat)
        if pulls and (i == 0 or i == panels - 1):
            b.pull(hw_mat, (a + st / 2) if i == 0 else (c - st / 2), 1.0, face)
    if casing:
        b.casing(w, h, casing, casing_t, setback, casing_mat, sill=False, drip=False)
    return (0.0, 0.0, w, h)


def dutch_door_wood(geo, origin, right, w=0.91, h=2.44, split=0.98, lights=0, light_h=0.26, hinge='l',
                    setback=0.03, casing=0.08, casing_t=0.022, seed=0, shade=0, room=ROOM_BARE, out=None,
                    mat='door_wood', hw_mat='hardware_black', casing_mat='trim_white', glass_mat='glass',
                    threshold_mat='threshold_bronze'):
    """The mahogany laundry door (rear, far right): a varnished DUTCH door, upper leaf glazed (one pane, or with
    `lights` top lights), lower leaf one raised panel, a ledge on the split, in a white casing with a drip cap.
    Returns the hole (0, 0, w, h)."""
    F = Frame(origin, right, out)
    b = _B(geo, F)
    G = _GlassCode(w, h, 0.0, seed, shade, room)
    jamb, headf, thr = 0.045, 0.045, 0.022
    yf = -setback
    yb = yf - 0.11
    b.ring(mat, 0.0, 0.0, w, h, jamb, jamb, 0.0, headf, yb, yf)
    b.box(threshold_mat, jamb, w - jamb, 0.0, thr, yb, yf + 0.04, 'ft', swap=True)
    g = 0.003
    a, c, top = jamb + g, w - jamb - g, h - headf - g
    yl = yf - 0.016
    ylb = yl - 0.045
    st = 0.115
    z0, z1 = thr + 0.004, split
    b.ring(mat, a, z0, c, z1, st, st, 0.21, 0.12, ylb, yl, outer='t')
    b.panel(mat, a + st, z0 + 0.21, c - st, z1 - 0.12, yl, depth=0.014, bevel=0.022, raised=0.009, margin=0.045)
    b.box(mat, a - 0.002, c + 0.002, split - 0.014, split + 0.020, yl, yl + 0.038, 'ftblr', swap=True)
    z0, z1 = split + 0.004, top
    b.ring(mat, a, z0, c, z1, st, st, 0.13, 0.13, ylb, yl, outer='b')
    b.lite(G, a + st, z0 + 0.13, c - st, z1 - 0.13, yl - 0.024, lights, light_h, 0.028, yl - 0.004, mat, glass_mat)
    xh, d = (c - st / 2, -1.0) if hinge == 'l' else (a + st / 2, 1.0)
    b.lever(hw_mat, xh, split - 0.10, yl, direction=d, plate_h=0.16)
    b.box(hw_mat, xh - 0.022, xh + 0.022, split + 0.15, split + 0.194, yl, yl + 0.012, 'flrtb')    # deadbolt
    if casing:
        b.casing(w, h, casing, casing_t, setback, casing_mat, sill=False, drip=True, ears=0.03)
    return (0.0, 0.0, w, h)


def garage_door(geo, origin, right, w=2.44, h=2.44, leaves=2, lights=3, planks=6, light_h=0.445, setback=0.06,
                casing=0.10, casing_t=0.022, head=0.14, sides='lr', ext_l=None, ext_r=None, seed=0, shade=0,
                room=ROOM_BARE, out=None, mat='door_garage', casing_mat='trim_white', glass_mat='glass',
                seal_mat='frame_black'):
    """One white carriage-style garage door (an overhead door dressed as a pair of swing leaves): each of the
    `leaves` has stiles and rails round a row of `lights` small upright lights at the top and a sunk panel of
    `planks` vertical V-grooved boards below.  w x h = the door (= the hole); casing: jamb trim width or
    (left, right); head: head trim height.  Returns the hole (0, 0, w, h)."""
    F = Frame(origin, right, out)
    b = _B(geo, F)
    G = _GlassCode(w, h, 0.0, seed, shade, room)
    yd = -setback
    b.box(seal_mat, 0.0, w, 0.0, h, yd - 0.035, yd - 0.03, 'f')           # the dark behind the joints
    b.box(seal_mat, 0.0, w, 0.0, 0.012, yd - 0.03, yd + 0.004, 'ft')      # bottom seal
    leaves = max(1, int(leaves))
    lw = w / leaves
    st, rtop, rmid, rbot, g = 0.135, 0.13, 0.12, 0.215, 0.004
    for i in range(leaves):
        a, c = i * lw + g, (i + 1) * lw - g
        z0, z1 = 0.012, h - g
        zl1 = z1 - rtop                                   # lights
        zl0 = zl1 - light_h
        zp1 = zl0 - rmid                                  # plank panel
        zp0 = z0 + rbot
        b.ring(mat, a, z0, c, z1, st, st, rbot, rtop, yd - 0.03, yd, outer='lr')
        b.box(mat, a + st, c - st, zp1, zl0, yd - 0.03, yd, 'ftb', swap=True)
        b.planks(mat, a + st, zp0, c - st, zp1, yd - 0.014, planks)
        b.glass(G, a + st, zl0, c - st, zl1, yd - 0.02, glass_mat)
        m = 0.04
        for k in range(1, int(lights)):
            xc = a + st + (c - a - 2 * st) * k / lights
            b.box(mat, xc - m / 2, xc + m / 2, zl0, zl1, yd - 0.02, yd, 'flr')
    if casing:
        b.casing(w, h, casing, casing_t, setback, casing_mat, head=head, sill=False, drip=False, sides=sides,
                 ext_l=ext_l, ext_r=ext_r)
    return (0.0, 0.0, w, h)


def garage_pair(geo, origin, right, door_w=2.44, h=2.44, pier=0.24, casing=0.10, head=0.14, seed=0, **kw):
    """The two garage doors with the white pier between them, under one head trim.  origin = bottom-left corner of
    the LEFT door.  Returns both holes [(0, 0, door_w, h), (door_w + pier, 0, 2 door_w + pier, h)]."""
    right = np.asarray(right, float)
    o = np.asarray(origin, float)
    garage_door(geo, o, right, door_w, h, casing=(casing, pier / 2 + 0.002), head=head, seed=seed, **kw)
    garage_door(geo, o + _unit(right) * (door_w + pier), right, door_w, h, casing=(pier / 2 + 0.002, casing),
                head=head, seed=seed + 1, **kw)
    return [(0.0, 0.0, door_w, h), (door_w + pier, 0.0, 2 * door_w + pier, h)]


def count(builder, *args, **kw):
    """Triangles one opening costs:  count(window, 1.65, 1.5, n=2)."""
    g = Geo()
    builder(g, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), *args, **kw)
    return g.ntri
