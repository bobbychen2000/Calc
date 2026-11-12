"""Plot the HWD ADS-B ground analysis over NAIP 2024 -> hwd3d/out/phase1/adsb_ground.png (+ adsb_ground_zoom_*.png),
gitignored, for humans. New file (task G4).

Inputs: refs/cache/adsb/hwd_ground_cells.json, hwd_parked_stays.json, hwd_runup_holds.json (this directory's tools),
NAIP 2024 (hwd3d/refs/cache/local/naip GeoTIFF, else the committed JPEG; tools/imagery/common.py load_rgb), FAA NASR
runway ends (hwd_frame.py). NAIP is resampled into the world frame (x east, north up = -z) pixel by pixel through
hwd_frame world -> NAD83 lat/lon -> UTM 10N (nearest neighbour), so overlays and image share one exact frame.
Colours: categorical slots 1-7 of the dataviz skill palette (validated: scripts/validate_palette.js, light mode, CVD
worst adjacent dE 9.1) for type classes, a blue ramp for moving fixes and an orange ramp for stationary fixes.
usage: python3 -I hwd3d/tools/adsb/plot_ground.py
"""
import importlib.util, json, math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                              # noqa: E402

F = C.F
CLS_COL = {'piston_single': '#2a78d6', 'jet': '#eb6834', 'helicopter': '#1baf7a', 'turboprop': '#eda100',
           'unknown': '#e87ba4', 'piston_twin': '#008300', 'light_other': '#6250d6', 'other': '#6250d6'}


def naip_world(x0, x1, z0, z1, res):
    p = os.path.join(C.HWD, 'tools', 'imagery', 'common.py')
    spec = importlib.util.spec_from_file_location('imagery_common', p); IC = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(IC)
    img, geo, src = IC.load_rgb('2024', prefer='tif')
    xs = np.arange(x0 + res / 2, x1, res); zs = np.arange(z0 + res / 2, z1, res)
    X, Z = np.meshgrid(xs, zs)                      # row 0 = smallest z = north
    lat, lon = F.world_to_ll_np(X.ravel(), Z.ravel()); E, N = F.ll_to_utm10_np(lat, lon)
    c = np.clip(np.round((E - geo['e0']) / geo['g'] - 0.5).astype(int), 0, img.shape[1] - 1)
    r = np.clip(np.round((geo['n1'] - N) / geo['g'] - 0.5).astype(int), 0, img.shape[0] - 1)
    rgb = img[r, c, :3].reshape(X.shape + (3,)).astype(np.float32)
    return rgb, os.path.relpath(src, C.HWD)


def draw(ax, ext, res, cells, stays, spots, holds, label_spots=12, dot=9, title=None, sub=None, edges=()):
    import matplotlib.colors as mcolors
    from matplotlib.lines import Line2D
    x0, x1, z0, z1 = ext
    rgb, src = naip_world(x0, x1, z0, z1, res)
    g = rgb.mean(-1) / 255.0
    base = 0.35 + 0.55 * g                                        # lightened greyscale photo: overlays carry the colour
    ax.imshow(np.dstack([base] * 3), extent=(x0, x1, -z1, -z0), origin='upper', interpolation='bilinear')
    # cells -> grids
    cm = 5.0
    nx = int(math.ceil((x1 - x0) / cm)); nz = int(math.ceil((z1 - z0) / cm))
    Mv = np.zeros((nz, nx)); Ms = np.zeros((nz, nx))
    for x, z, nm, ns, na, nh in cells:
        i = int((z - z0) // cm); j = int((x - x0) // cm)
        if 0 <= i < nz and 0 <= j < nx: Mv[i, j] += nm; Ms[i, j] += ns
    ext_c = (x0, x0 + nx * cm, -(z0 + nz * cm), -z0)
    blues = mcolors.LinearSegmentedColormap.from_list('mv', ['#cde2fb', '#86b6ef', '#3987e5', '#1c5cab', '#0d366b'])
    oranges = mcolors.LinearSegmentedColormap.from_list('st', ['#fde0cf', '#f6a77f', '#eb6834', '#b4461b', '#7a2c0e'])
    vmax_m = max(2, np.percentile(Mv[Mv > 0], 99)) if (Mv > 0).any() else 2
    ax.imshow(np.ma.masked_where(Mv <= 0, Mv), extent=ext_c, origin='upper', cmap=blues, alpha=0.85, interpolation='nearest',
              norm=mcolors.LogNorm(vmin=1, vmax=vmax_m))
    vmax_s = max(2, np.percentile(Ms[Ms > 0], 99)) if (Ms > 0).any() else 2
    ax.imshow(np.ma.masked_where(Ms <= 0, Ms), extent=ext_c, origin='upper', cmap=oranges, alpha=0.9, interpolation='nearest',
              norm=mcolors.LogNorm(vmin=1, vmax=vmax_s))
    # runways (NASR ends, NASR width)
    for rid in ('10L/28R', '10R/28L'):
        a, b = rid.split('/'); A = F.end_world(a); B = F.end_world(b); w = C.RWY_HALF_W[rid]
        dx, dz = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dz); nx_, nz_ = -dz / L * w, dx / L * w
        P = [(A[0] + nx_, A[1] + nz_), (B[0] + nx_, B[1] + nz_), (B[0] - nx_, B[1] - nz_), (A[0] - nx_, A[1] - nz_), (A[0] + nx_, A[1] + nz_)]
        ax.plot([p[0] for p in P], [-p[1] for p in P], color='#222222', lw=0.8, alpha=0.8)
        for e, q in ((a, A), (b, B)):
            if x0 < q[0] < x1 and z0 < q[1] < z1:
                ax.text(q[0], -q[1], ' ' + e, fontsize=8, color='#111111', ha='left', va='center',
                        bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.7))
    # hold clusters (>= 3 stops)
    H = [h for h in holds if h['n'] >= 3 and x0 < h['x'] < x1 and z0 < h['z'] < z1]
    ax.scatter([h['x'] for h in H], [-h['z'] for h in H], s=[20 + 6 * h['n'] for h in H], marker='^', facecolors='none',
               edgecolors='#111111', linewidths=1.0, zorder=5)
    # signal ends (transponder off on the ground) / starts (on)
    for kind, mk in (('end', 'x'), ('start', '+')):
        E = [e for e in edges if e['kind'] == kind and x0 < e['x'] < x1 and z0 < e['z'] < z1]
        ax.scatter([e['x'] for e in E], [-e['z'] for e in E], s=dot * 0.9, marker=mk, c='#3a3a38', linewidths=0.8, zorder=5)
    # stays
    S = [s for s in stays if x0 < s['x'] < x1 and z0 < s['z'] < z1]
    ax.scatter([s['x'] for s in S], [-s['z'] for s in S], s=dot, c=[CLS_COL.get(s['cls'], '#888888') for s in S],
               edgecolors='#1a1a19', linewidths=0.4, zorder=6)
    # spots
    P = [p for p in spots if x0 < p['x'] < x1 and z0 < p['z'] < z1]
    for p in P:
        r = max(p['radius'], 2.0)
        ax.add_patch(__import__('matplotlib').patches.Circle((p['x'], -p['z']), r + 1.5, fill=False, ec='white', lw=2.2, zorder=7))
        ax.add_patch(__import__('matplotlib').patches.Circle((p['x'], -p['z']), r + 1.5, fill=False, ec='#111111', lw=1.0, zorder=8))
    for p in sorted(P, key=lambda p: -p['n_visits'])[:label_spots]:
        ax.text(p['x'] + 6, -p['z'] + 6, '%s %dv' % (p['id'], p['n_visits']), fontsize=7, color='#111111', zorder=9,
                bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.75))
    ax.set_xlim(x0, x1); ax.set_ylim(-z1, -z0); ax.set_aspect('equal')
    ax.set_xlabel('x east (m, HWD world frame)'); ax.set_ylabel('north = -z (m)')
    if title: ax.set_title(title, fontsize=12, loc='left')
    used = [k for k in CLS_COL if any(s['cls'] == k for s in S)]
    hs = [Line2D([], [], marker='o', ls='none', mfc=CLS_COL[k], mec='#1a1a19', ms=6, label='stay: ' + k.replace('_', ' ')) for k in used]
    hs += [Line2D([], [], marker='o', ls='none', mfc='none', mec='#111111', ms=9, label='spot (stays clustered, ~4 m)'),
           Line2D([], [], marker='^', ls='none', mfc='none', mec='#111111', ms=8, label='pre-departure stop cluster (>= 3)'),
           Line2D([], [], marker='x', ls='none', mec='#3a3a38', ms=6, label='signal end on the ground (>= 30 min silent)'),
           Line2D([], [], marker='+', ls='none', mec='#3a3a38', ms=7, label='signal start on the ground'),
           Line2D([], [], marker='s', ls='none', mfc='#3987e5', mec='none', ms=8, label='5 m cell: moving fixes (log)'),
           Line2D([], [], marker='s', ls='none', mfc='#eb6834', mec='none', ms=8, label='5 m cell: stationary fixes (log)'),
           Line2D([], [], color='#222222', lw=0.8, label='runway (FAA NASR ends, width)')]
    ax.legend(handles=hs, loc='lower left', fontsize=7.5, framealpha=0.85)
    if sub: ax.text(0.995, 0.005, sub, transform=ax.transAxes, fontsize=6.5, ha='right', va='bottom', color='#333333',
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))
    return src


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    J = lambda n: json.load(open(os.path.join(C.OUT_DIR, n)))
    cells = J('hwd_ground_cells.json')['cells']; ps = J('hwd_parked_stays.json'); rh = J('hwd_runup_holds.json')
    stays, spots, holds, edges = ps['stays'], ps['spots'], rh['clusters'], ps['signal_edges']
    sub = ('ADS-B: adsb.lol (ODbL 1.0), 111 h 4-11 Nov 2026 | Imagery: USDA NAIP 2024 (public domain) | Runways: FAA NASR '
           '2026-10-29 | %d stays, %d spots, %d cells' % (len(stays), len(spots), len(cells)))
    fig, ax = plt.subplots(figsize=(22, 14), dpi=130)
    src = draw(ax, (-950, 980, -800, 660), 1.2, cells, stays, spots, holds, label_spots=15, dot=12,
               title='HWD ground ADS-B: taxi density (5 m cells), stationary stays >= 5 min, parking spots, pre-departure stops',
               sub=sub, edges=edges)
    fig.tight_layout(); out = os.path.join(C.PLOTS, 'adsb_ground.png'); fig.savefig(out); plt.close(fig)
    print('->', out, '| NAIP from', src)
    zooms = {'east_apron': (150, 520, -260, 90), 'west_ramps': (-380, 120, -700, -180), 'rwy28_holds': (300, 840, 0, 520)}
    for k, ext in zooms.items():
        fig, ax = plt.subplots(figsize=(12, 12 * (ext[3] - ext[2]) / (ext[1] - ext[0]) + 0.6), dpi=130)
        draw(ax, ext, 0.3, cells, stays, spots, holds, label_spots=25, dot=22, title='HWD ADS-B ground: %s' % k.replace('_', ' '), sub=sub,
             edges=edges)
        fig.tight_layout(); out = os.path.join(C.PLOTS, 'adsb_ground_zoom_%s.png' % k); fig.savefig(out); plt.close(fig)
        print('->', out)


if __name__ == '__main__':
    main()
