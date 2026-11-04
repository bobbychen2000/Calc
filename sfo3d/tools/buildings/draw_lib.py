"""Drawing engine for the building sheets (tools/buildings/draw.py): sheets with several views, each at its own scale,
title block, tag legend, notes, scale bars, north arrow; dimension lines, level marks, leaders and point marks whose
style says where the value comes from; NAIP 2024 backgrounds and the edge-offset measurement for the overlays.

Conventions (as tools/drawing/sheets.py):
  * plans are north-up, plotted as (x, -z) in the world frame ltp-nad83-2011 (x east, z south, metres from the ARP);
    elevations / sections are plotted as (u, h): u = metres along the view's horizontal axis, h = metres above grade;
  * ISO paper (A3 / A2 / A1), a 10 mm border and an 82 mm strip on the right (north arrow, tag legend, notes, title
    block); scales are true on paper (1 mm on paper = scale / 1000 m);
  * every number on a sheet carries its tag (spec_*.json 'tag'):
        pub  published by an original source (architect, engineer, SFO, FAA)    black, solid
        obs  measured by us (NAIP, FAA DOF geometry, SFO Museum data, photos)  blue, solid
        inf  inferred / derived arithmetic, not confirmed                         orange, dashed, italic
        unk  not known - placeholder geometry only, no value                      grey, dotted, italic
        app  what the 3-D app builds today (js/, data/) - comparison only        magenta, dash-dot
  * vector sheets (docs/drawings/buildings/) carry no imagery pixels; overlays (out/buildings/drawings/) put the same
    views on NAIP 2024 (USDA, public domain; kept local by the owner's rule).

NAIP 2024 world raster: refs/cache/naip/naip_2024_world_0.5m_bgr.npy (+ .json: col = (x - x0)/res - 0.5,
row = (z - z0)/res - 0.5); flown 2024-05-20; roofs are displaced by relief (see measure_edge and the README).
"""
import datetime
import json
import math
import os
import subprocess
import sys
import textwrap

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle, Polygon as MPoly, FancyArrow, Circle  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

DOCS = os.path.join(ROOT, 'docs', 'drawings', 'buildings')
OUTD = os.path.join(ROOT, 'out', 'buildings', 'drawings')
NAIP_DIR = os.path.join(ROOT, 'refs', 'cache', 'naip')
FT = 0.3048

PAPER = {'A3': (420, 297), 'A2': (594, 420), 'A1': (841, 594)}
BORDER = 10
STRIP = 82
FONT = 'DejaVu Sans'
plt.rcParams.update({'font.family': FONT, 'svg.fonttype': 'none', 'path.simplify': True, 'hatch.linewidth': 0.3})

TAGS = {
    'pub': dict(c='#111111', ls='-', st='normal', lw=0.55, txt='pub - published by an original source (SFO, FAA, architect, engineer)'),
    'obs': dict(c='#0b57a4', ls='-', st='normal', lw=0.55, txt='obs - measured by us (NAIP 2024 / 2020, FAA DOF points, SFO Museum data, photos)'),
    'inf': dict(c='#b35900', ls=(0, (4, 2)), st='italic', lw=0.55, txt='inf - inferred / derived by stated arithmetic; NOT confirmed'),
    'unk': dict(c='#8a8a8a', ls=(0, (1, 1.6)), st='italic', lw=0.5, txt='unknown - placeholder geometry, no source value'),
    'app': dict(c='#c2185b', ls=(0, (6, 2, 1, 2)), st='normal', lw=0.7, txt='app - what the 3-D app builds today (js/, data/)'),
}
CTX = dict(c='#9a9a9a', lw=0.35)       # context geometry (other buildings, SFO Museum outlines not being dimensioned)


def tag_of(t):
    return TAGS.get(t, TAGS['unk'])


def git_rev():
    try:
        h = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], text=True).strip()
        d = subprocess.run(['git', '-C', ROOT, 'diff', '--quiet', '--', 'tools/buildings'], capture_output=True).returncode
        return h + ('+dirty' if d else '')
    except Exception:
        return 'unknown'


# ------------------------------------------------------------------------------------------------ geometry helpers
def ring_area(r):
    r = np.asarray(r, float)
    return 0.5 * float(np.sum(r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]))


def unit(v):
    v = np.asarray(v, float); return v / (np.hypot(*v) or 1.0)


def hdg_vec(h):
    """world (x, z) unit vector of a true heading (deg)."""
    return np.array(GF.hdg_vec(h))


def st2w(s, t):
    return np.array(GF.st_to_world(s, t))


def w2st(x, z):
    return np.array(GF.world_to_st(x, z))


def frame_pt(c, ax, u, v):
    """world point at (u, v) in a building frame: centre c, axis unit ax (u), v = ax rotated +90 deg in (x, -z)
    plotting sense, i.e. v = (-ax_z, ax_x) in world (x, z) when ax points SSE -> v points ENE."""
    ax = unit(ax); vv = np.array([ax[1], -ax[0]])  # v = ax turned 90 deg towards the right of +u (SSE axis -> ENE)
    return np.asarray(c, float) + ax * u + vv * v


# ------------------------------------------------------------------------------------------------ sheet / view
class View:
    def __init__(self, sheet, ax, scale, kind):
        self.sheet, self.ax, self.scale, self.kind = sheet, ax, scale, kind
        self.m = scale / 1000.0  # world metres per paper mm

    # coordinates
    def P(self, p):
        p = np.asarray(p, float)
        if self.kind == 'plan':
            return np.stack([p[..., 0], -p[..., 1]], -1)
        return p

    def mm(self, v):
        return v * self.m

    # primitives
    def poly(self, ring, tag='obs', fc='none', lw=None, z=2, closed=True, alpha=1.0, hatch=None, ls=None, ec=None):
        T = tag_of(tag); q = self.P(np.asarray(ring, float))
        self.ax.add_patch(MPoly(q, closed=closed, fc=fc, ec=ec or T['c'], lw=lw or T['lw'], ls=ls or T['ls'], zorder=z,
                                alpha=alpha, hatch=hatch, joinstyle='round'))

    def ctx(self, ring, fc='#eeeeee', lw=None, z=1, closed=True, ls='-'):
        q = self.P(np.asarray(ring, float))
        self.ax.add_patch(MPoly(q, closed=closed, fc=fc, ec=CTX['c'], lw=lw or CTX['lw'], zorder=z, ls=ls))

    def line(self, pts, tag='obs', lw=None, z=3, color=None, ls=None, alpha=1.0):
        T = tag_of(tag); q = self.P(np.asarray(pts, float))
        self.ax.plot(q[:, 0], q[:, 1], color=color or T['c'], lw=lw or T['lw'], ls=ls or T['ls'], zorder=z, alpha=alpha,
                     solid_capstyle='butt', dash_capstyle='butt')

    def circle(self, c, r, tag='obs', fc='none', lw=None, z=3, ls=None):
        T = tag_of(tag)
        self.ax.add_patch(Circle(tuple(self.P(c)), r, fc=fc, ec=T['c'], lw=lw or T['lw'], ls=ls or T['ls'], zorder=z))

    def text(self, p, s, tag='pub', fs=4.8, ha='center', va='center', rot=0, bg=True, z=8, color=None, weight='normal',
             style=None):
        T = tag_of(tag); q = self.P(p)
        bb = dict(boxstyle='square,pad=0.12', fc='white', ec='none', alpha=0.85) if bg else None
        self.ax.text(q[0], q[1], s, fontsize=fs, ha=ha, va=va, rotation=rot, color=color or T['c'], fontstyle=style or T['st'],
                     zorder=z, bbox=bb, fontweight=weight, rotation_mode='anchor', clip_on=False)

    def dim(self, p0, p1, off_mm, s, tag='pub', fs=4.6, ext=True, z=7, text_off=1.0):
        """aligned dimension p0 -> p1, offset off_mm (paper) to the left of p0 -> p1 in plot space; slash ticks."""
        T = tag_of(tag); a, b = self.P(p0), self.P(p1)
        d = b - a; L = float(np.hypot(*d))
        if L <= 0: return
        t = d / L; n = np.array([-t[1], t[0]]); o = n * self.mm(off_mm)
        A, B = a + o, b + o
        if ext and abs(off_mm) > 0.2:
            sg = np.sign(off_mm)
            for p, Q in ((a, A), (b, B)):
                self.ax.plot([p[0] + n[0] * sg * self.mm(0.8), Q[0] + n[0] * sg * self.mm(1.2)],
                             [p[1] + n[1] * sg * self.mm(0.8), Q[1] + n[1] * sg * self.mm(1.2)], color=T['c'], lw=0.25, zorder=z)
        self.ax.plot([A[0] - t[0] * self.mm(1.0), B[0] + t[0] * self.mm(1.0)], [A[1] - t[1] * self.mm(1.0), B[1] + t[1] * self.mm(1.0)],
                     color=T['c'], lw=0.4, ls=T['ls'], zorder=z)
        k = unit(t + n) * self.mm(1.1)
        for Q in (A, B):
            self.ax.plot([Q[0] - k[0], Q[0] + k[0]], [Q[1] - k[1], Q[1] + k[1]], color=T['c'], lw=0.7, zorder=z)
        ang = math.degrees(math.atan2(t[1], t[0]))
        if ang > 90.5: ang -= 180
        if ang < -89.5: ang += 180
        mid = (A + B) / 2
        sgn = 1 if off_mm >= 0 else -1
        q = mid + n * sgn * self.mm(text_off)
        nn = n * sgn
        # put the text on the outer side of the dimension line
        self.ax.text(q[0], q[1], s, fontsize=fs, ha='center', va='bottom' if np.dot(nn, [-math.sin(math.radians(ang)), math.cos(math.radians(ang))]) >= 0 else 'top',
                     rotation=ang, rotation_mode='anchor', color=T['c'], fontstyle=T['st'], zorder=z + 1,
                     bbox=dict(boxstyle='square,pad=0.08', fc='white', ec='none', alpha=0.8))

    def level(self, u, h, s, tag='pub', side='right', len_mm=18, fs=4.6, z=7, u_line=None):
        """level mark at height h: a line from u over len_mm, a triangle, the text above it."""
        T = tag_of(tag); L = self.mm(len_mm) * (1 if side == 'right' else -1)
        u0 = u if u_line is None else u_line
        self.ax.plot([u0, u + L], [h, h], color=T['c'], lw=0.35, ls=T['ls'], zorder=z)
        self.ax.plot([u + L * 0.85], [h + self.mm(0.9)], marker='v', ms=2.6, color=T['c'], zorder=z)
        self.ax.text(u + L, h + self.mm(0.4), s, fontsize=fs, ha='left' if side == 'right' else 'right', va='bottom',
                     color=T['c'], fontstyle=T['st'], zorder=z + 1,
                     bbox=dict(boxstyle='square,pad=0.08', fc='white', ec='none', alpha=0.8))

    def leader(self, p, dx_mm, dy_mm, s, tag='pub', fs=4.6, ha=None, z=8, va='center', wrap=None):
        T = tag_of(tag); q = self.P(p); e = q + np.array([self.mm(dx_mm), self.mm(dy_mm)])
        if wrap: s = '\n'.join(textwrap.wrap(s, wrap))
        self.ax.plot([q[0], e[0]], [q[1], e[1]], color=T['c'], lw=0.3, zorder=z)
        self.ax.plot([q[0]], [q[1]], marker='o', ms=1.2, color=T['c'], zorder=z)
        self.ax.text(e[0] + self.mm(0.6 if dx_mm >= 0 else -0.6), e[1], s, fontsize=fs, ha=ha or ('left' if dx_mm >= 0 else 'right'),
                     va=va, color=T['c'], fontstyle=T['st'], zorder=z + 1, linespacing=1.15,
                     bbox=dict(boxstyle='square,pad=0.12', fc='white', ec='none', alpha=0.85))

    def mark(self, p, tag='pub', marker='^', ms=3.2, z=9, fc=None):
        T = tag_of(tag); q = self.P(p)
        self.ax.plot([q[0]], [q[1]], marker=marker, ms=ms, mfc=fc if fc is not None else T['c'], mec=T['c'], mew=0.5, zorder=z, ls='none')

    def scalebar(self, x_mm=4, y_mm=4, nice=None):
        """scale bar in the view's lower-left corner (paper mm from the corner)."""
        x0, x1 = self.ax.get_xlim(); y0, y1 = self.ax.get_ylim()
        if nice is None:
            target = 40 * self.m
            nice = max([v for v in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000) if v <= target] or [1])
        X, Y = x0 + self.mm(x_mm), y0 + self.mm(y_mm); w = nice / 4
        for i in range(4):
            self.ax.add_patch(Rectangle((X + i * w, Y), w, self.mm(1.2), fc='k' if i % 2 == 0 else 'white', ec='k', lw=0.3, zorder=20))
        for i in (0, 2, 4):
            self.ax.text(X + i * w, Y - self.mm(0.6), f'{nice * i / 4:g}', fontsize=3.8, ha='center', va='top', zorder=20)
        self.ax.text(X + nice + self.mm(1.5), Y + self.mm(0.6), 'm', fontsize=3.8, va='center', zorder=20)

    def grid(self, step=None, st=True):
        """world x / z grid (light grey) and the airport s / t grid (dashed blue), plan views only."""
        if self.kind != 'plan': return
        x0, x1 = self.ax.get_xlim(); y0, y1 = self.ax.get_ylim()
        span = max(x1 - x0, y1 - y0)
        step = step or next(s for s in (10, 20, 25, 50, 100, 200, 250, 500, 1000) if span / s <= 14)
        for x in np.arange(math.ceil(x0 / step) * step, x1, step):
            self.ax.plot([x, x], [y0, y1], color='#c8c8c8', lw=0.2, zorder=0.4)
            self.ax.text(x, y1 - self.mm(0.5), f'x {x:.0f}', fontsize=3.4, color='#808080', ha='center', va='top', zorder=0.5)
        for y in np.arange(math.ceil(y0 / step) * step, y1, step):
            self.ax.plot([x0, x1], [y, y], color='#c8c8c8', lw=0.2, zorder=0.4)
            self.ax.text(x0 + self.mm(0.5), y, f'z {-y:.0f}', fontsize=3.4, color='#808080', ha='left', va='bottom', zorder=0.5)
        if not st: return
        cs = np.array([[x0, -y0], [x1, -y0], [x1, -y1], [x0, -y1]])
        S, T = w2st(cs[:, 0], cs[:, 1])
        for kind, lo, hi in (('s', S.min(), S.max()), ('t', T.min(), T.max())):
            for v in np.arange(math.ceil(lo / step) * step, hi, step):
                if kind == 's': a = st2w(np.array([v, v]), np.array([T.min() - 50, T.max() + 50]))
                else: a = st2w(np.array([S.min() - 50, S.max() + 50]), np.array([v, v]))
                self.ax.plot(a[0], -a[1], color='#9cc3e0', lw=0.25, ls=(0, (4, 3)), zorder=0.45)
        self.ax.set_xlim(x0, x1); self.ax.set_ylim(y0, y1)

    def background(self, res=None):
        """NAIP 2024 under the view (overlays only)."""
        x0, x1 = self.ax.get_xlim(); y0, y1 = self.ax.get_ylim()
        img = naip_rgb(x0, -y1, x1, -y0, res or max(0.5, self.m * 25.4 / self.sheet.dpi))
        self.ax.imshow(img, extent=[x0, x1, y0, y1], origin='upper', zorder=0.1, interpolation='bilinear')
        self.ax.set_xlim(x0, x1); self.ax.set_ylim(y0, y1)


class Sheet:
    def __init__(self, sid, title, paper='A2', subtitle='', variant='vector', dpi=150):
        self.sid, self.title, self.paper, self.subtitle, self.variant, self.dpi = sid, title, paper, subtitle, variant, dpi
        self.pw, self.ph = PAPER[paper]
        self.fig = plt.figure(figsize=(self.pw / 25.4, self.ph / 25.4))
        self.vw, self.vh = self.pw - 2 * BORDER - STRIP, self.ph - 2 * BORDER
        self.views, self.notes, self.sources, self.scales, self.has_plan = [], [], [], [], False
        self.used_tags = set()

    def view(self, x, y, w, h, scale, centre, title='', kind='plan', frame=True, title_side='bottom'):
        """view at (x, y) mm from the lower-left of the drawing area, w x h mm, true scale 1:scale, centred on centre
        (world (x, z) for plans, (u, h) for elevations)."""
        pw, ph = self.pw, self.ph
        ax = self.fig.add_axes([(BORDER + x) / pw, (BORDER + y) / ph, w / pw, h / ph])
        m = scale / 1000.0
        c = np.asarray(centre, float)
        cx, cy = (c[0], -c[1]) if kind == 'plan' else (c[0], c[1])
        ax.set_xlim(cx - w * m / 2, cx + w * m / 2); ax.set_ylim(cy - h * m / 2, cy + h * m / 2)
        ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.5 if frame else 0); s.set_color('#444444')
        ax.patch.set_alpha(0)
        if title:
            ty = (BORDER + y - 1.0) / ph if title_side == 'bottom' else (BORDER + y + h + 1.0) / ph
            self.fig.text((BORDER + x) / pw, ty, title, fontsize=6.4, fontweight='bold', va='top' if title_side == 'bottom' else 'bottom')
            self.fig.text((BORDER + x + w) / pw, ty, f'1:{scale:g}', fontsize=6.0, ha='right', va='top' if title_side == 'bottom' else 'bottom')
        V = View(self, ax, scale, kind); self.views.append(V); self.scales.append(scale)
        if kind == 'plan': self.has_plan = True
        return V

    def note(self, s):
        self.notes.append(s)

    def _strip(self, imagery):
        pw, ph = self.pw, self.ph
        sx = self.fig.add_axes([(pw - BORDER - STRIP + 2) / pw, BORDER / ph, (STRIP - 2) / pw, self.vh / ph])
        W = STRIP - 2; sx.set_xlim(0, W); sx.set_ylim(0, self.vh); sx.axis('off')
        top = self.vh - 3
        if self.has_plan:
            sx.add_patch(FancyArrow(10, top - 20, 0, 16, width=2.0, head_width=6.5, head_length=6.5, length_includes_head=True, fc='k', ec='k'))
            sx.text(10, top - 1.5, 'N', ha='center', va='bottom', fontsize=8, fontweight='bold')
            sx.text(10, top - 24, 'true north', ha='center', fontsize=4.2)
            for h, nm in ((117.83, '+s (rwy 10->28)'), (27.83, '+t (rwy 1->19)')):
                v = GF.hdg_vec(h); dx, dy = v[0], -v[1]
                sx.annotate('', xy=(36 + dx * 10, top - 12 + dy * 10), xytext=(36, top - 12), arrowprops=dict(arrowstyle='->', color='#2e86c1', lw=0.6))
                sx.text(36 + dx * 13.5, top - 12 + dy * 13.5, nm, fontsize=3.8, color='#2e86c1', ha='center', va='center')
            sx.text(52, top - 4, 'plans: north-up,\nworld x east / z south\n(m from the ARP);\ns / t airport grid\n(dashed blue)', fontsize=3.8, va='top', linespacing=1.2)
            top -= 30
        # tag legend
        sx.text(2, top, 'Line / text style = where the value comes from', fontsize=5.0, fontweight='bold', va='top'); top -= 4.2
        for k in ('pub', 'obs', 'inf', 'unk', 'app'):
            if k not in self.used_tags and k in ('app',): continue
            T = TAGS[k]
            sx.plot([2, 9], [top - 1, top - 1], color=T['c'], lw=0.9, ls=T['ls'])
            sx.text(10.5, top - 1, '\n'.join(textwrap.wrap(T['txt'], 66)), fontsize=4.0, color=T['c'], fontstyle=T['st'], va='center', linespacing=1.1)
            top -= 4.6 if len(T['txt']) <= 66 else 6.6
        sx.text(2, top, 'Values: metres above local grade unless stated; [tag source] after each value;\n'
                        'ranges in ( ); full sources: the spec JSON and research note named below.', fontsize=3.8, va='top', linespacing=1.15)
        top -= 7.5
        # notes
        if self.notes:
            sx.text(2, top, 'Notes', fontsize=5.0, fontweight='bold', va='top'); top -= 3.8
            for i, n in enumerate(self.notes, 1):
                wr = textwrap.wrap(n, 78)
                sx.text(2, top, f'{i}.', fontsize=3.9, va='top')
                sx.text(5.5, top, '\n'.join(wr), fontsize=3.9, va='top', linespacing=1.15)
                top -= 1.6 * len(wr) + 1.4
        # title block
        tb = 46; y0 = 1
        sx.add_patch(Rectangle((0.5, y0), W - 1, tb, fc='white', ec='k', lw=0.8))
        sx.plot([0.5, W - 0.5], [y0 + tb - 13, y0 + tb - 13], color='k', lw=0.5)
        sx.text(2, y0 + tb - 2, 'SFO Live 3D - building drawings (2-D, drawn to verified dimensions)', fontsize=4.6, fontweight='bold', va='top')
        sx.text(2, y0 + tb - 6, '\n'.join(textwrap.wrap(self.title, 44)), fontsize=6.2, fontweight='bold', va='top', linespacing=1.1)
        sc = ', '.join(f'1:{s:g}' for s in sorted(set(self.scales)))
        rows = [f'Sheet {self.sid}   |   {self.paper}   |   scale {sc} (true on {self.paper})',
                f'Variant: {self.variant}   |   imagery: {imagery}',
                self.subtitle,
                'Frame ltp-nad83-2011 (tools/geo_frame.py = js/geo.js): x east, z south, m from the ARP',
                'Data: tools/buildings/spec_*.json (verified 2026-09-26 / 2026-11-04)',
                'Footprints: SFO Museum (CDLA-Permissive-1.0), data/sfo_airport.json',
                'Heights: FAA DOF (public domain), published sources, NAIP measurements',
                ('No imagery pixels on this sheet' if self.variant == 'vector' else
                 'NAIP 2024 (USDA FPAC-BC GEO, public domain) - local copy, not committed'),
                f'Generated {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")}Z by tools/buildings/draw.py, git {git_rev()}']
        ty = y0 + tb - 15
        for r in rows:
            if not r: continue
            for ln in textwrap.wrap(r, 74):
                sx.text(2, ty, ln, fontsize=3.9, va='top'); ty -= 3.1
        return sx

    def finish(self, imagery='none (vector)', outdir=None, fmt=('svg', 'png')):
        self._strip(imagery)
        from matplotlib.patches import Rectangle as R
        self.fig.add_artist(R((BORDER / 2 / self.pw, BORDER / 2 / self.ph), 1 - BORDER / self.pw, 1 - BORDER / self.ph,
                              transform=self.fig.transFigure, fill=False, lw=1.0, ec='k'))
        outdir = outdir or (DOCS if self.variant == 'vector' else OUTD)
        os.makedirs(outdir, exist_ok=True)
        base = os.path.join(outdir, self.sid + ('' if self.variant == 'vector' else '_' + self.variant))
        out = []
        for f in fmt:
            kw = dict(pil_kwargs={'quality': 88}) if f == 'jpg' else {}
            self.fig.savefig(base + '.' + f, dpi=self.dpi, **kw); out.append(base + '.' + f)
        plt.close(self.fig)
        return out


# ------------------------------------------------------------------------------------------------ NAIP
_N = {}


def _naip():
    if 'A' not in _N:
        _N['T'] = json.load(open(os.path.join(NAIP_DIR, 'naip_2024_world_0.5m.json')))
        _N['A'] = np.load(os.path.join(NAIP_DIR, 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r')
    return _N['A'], _N['T']


def naip_available():
    return os.path.exists(os.path.join(NAIP_DIR, 'naip_2024_world_0.5m_bgr.npy'))


def naip_rgb(x0, z0, x1, z1, res=0.5):
    """RGB crop of the world window (z0 < z1), resampled to res m/px (area)."""
    import cv2
    A, T = _naip(); R = T['res']
    c0, r0 = int(math.floor((x0 - T['x0']) / R)), int(math.floor((z0 - T['z0']) / R))
    c1, r1 = int(math.ceil((x1 - T['x0']) / R)), int(math.ceil((z1 - T['z0']) / R))
    img = np.full((r1 - r0, c1 - c0, 3), 40, np.uint8)
    rr0, cc0, rr1, cc1 = max(r0, 0), max(c0, 0), min(r1, A.shape[0]), min(c1, A.shape[1])
    if rr1 > rr0 and cc1 > cc0:
        img[rr0 - r0:rr1 - r0, cc0 - c0:cc1 - c0] = A[rr0:rr1, cc0:cc1]
    if res > R * 1.05:
        f = R / res; img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    img = img[:, :, ::-1]
    # lighten a little so the line work reads on top
    return (img.astype(np.float32) * 0.78 + 255 * 0.22).astype(np.uint8)


def sample_lum(X, Z):
    """bilinear NAIP 2024 luminance (Rec. 601) at world arrays X, Z."""
    import cv2
    A, T = _naip(); R = T['res']
    col = ((np.asarray(X) - T['x0']) / R - 0.5).astype(np.float32)
    row = ((np.asarray(Z) - T['z0']) / R - 0.5).astype(np.float32)
    r0, c0 = int(np.floor(row.min())) - 2, int(np.floor(col.min())) - 2
    r1, c1 = int(np.ceil(row.max())) + 3, int(np.ceil(col.max())) + 3
    if r0 < 0 or c0 < 0 or r1 > A.shape[0] or c1 > A.shape[1]:
        return None
    sub = np.ascontiguousarray(A[r0:r1, c0:c1]).astype(np.float32)
    lum = 0.114 * sub[..., 0] + 0.587 * sub[..., 1] + 0.299 * sub[..., 2]
    return cv2.remap(lum, col - c0, row - r0, cv2.INTER_LINEAR)


def measure_edge(p0, p1, n_out, shift=(0.0, 0.0), half=6.0, step=0.25, trim=0.12):
    """Offset of the strongest straight NAIP 2024 edge parallel to the drawn edge p0 -> p1 (world x, z), searched
    within +-half m of its PREDICTED IMAGED position (drawn edge + shift, shift = relief displacement h x lean).
    Method (as tools/imagery/outline_audit.py): luminance sampled on a strip across the edge (0.25 m), smoothed
    (sigma 0.5 m), |d/dn| per row, MEDIAN along the edge (so only edges parallel to it count), peak + parabola.
    Returns dict(o = signed offset along the outward normal n_out, m; ratio = peak / best peak > 2 m away; strength)."""
    import cv2
    p0 = np.asarray(p0, float) + shift; p1 = np.asarray(p1, float) + shift
    v = p1 - p0; L = float(np.hypot(*v))
    if L < 6: return None
    t = v / L; n = unit(n_out)
    s = np.arange(trim * L, (1 - trim) * L, 0.5); d = np.arange(-half, half + 1e-9, step)
    S, D = np.meshgrid(s, d, indexing='ij')
    X = p0[0] + S * t[0] + D * n[0]; Z = p0[1] + S * t[1] + D * n[1]
    lum = sample_lum(X, Z)
    if lum is None: return None
    lum = cv2.GaussianBlur(lum, (0, 0), 0.5 / step)
    g = np.abs(np.gradient(lum, axis=1)) / step
    prof = np.median(g, axis=0)
    i = int(np.argmax(prof)); pk = float(prof[i])
    di = 0.0
    if 0 < i < len(d) - 1:
        a_, b_, c_ = prof[i - 1], prof[i], prof[i + 1]; den = a_ - 2 * b_ + c_
        if den < 0: di = 0.5 * (a_ - c_) / den
    far = np.abs(d - d[i]) > 2.0
    snd = float(prof[far].max()) if far.any() else 0.0
    return dict(o=round(float(d[i] + di * step), 2), ratio=round(pk / max(snd, 1e-6), 2), strength=round(pk, 1), L=round(L, 1))


def outward_normals(ring):
    """per-edge outward unit normals of a polygon ring (world x, z), any orientation."""
    r = np.asarray(ring, float); a = ring_area(r)
    out = []
    for i in range(len(r)):
        p, q = r[i], r[(i + 1) % len(r)]; d = unit(q - p)
        n = np.array([d[1], -d[0]]) if a > 0 else np.array([-d[1], d[0]])
        out.append(n)
    return out
