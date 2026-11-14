"""B3: ZSSS runway-end and taxiway/apron marking layouts drawn from MH 5001-2021 parameters (our own drawing; the
standard's figures are not reproduced). Choices inside the standard's ranges are marked 'inf' in the legend.

usage: python3 -I sha3d/tools/standards/draw_markings.py OUT.png
"""
import sys, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, RegularPolygon
W_ = '#f4f4f0'; Y_ = '#f2c200'; R_ = '#c8102e'; K_ = '#111111'; PAV = '#5a5d61'; PAV2 = '#7b7e82'; G_ = '#3b5e2b'
def rect(ax, x0, x1, y0, y1, c, z=3, **kw): ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color=c, zorder=z, lw=0, **kw))
def runway_end(ax, W, dthr, pad_len, ap_start, label_num, letter, title, xmax=1060):
    """x = metres from the pavement end along the runway, y = lateral (m). Pad at negative x."""
    hw = W / 2
    rect(ax, -pad_len, 0, -max(hw, 30) if pad_len else 0, max(hw, 30) if pad_len else 0, PAV2, z=1)
    rect(ax, -pad_len - 30, xmax, -hw - 7.5, hw + 7.5, G_, z=0)                  # strip/grass
    rect(ax, 0, xmax, -hw - 7.5, hw + 7.5, PAV2, z=1)                            # shoulders 7.5 m (AIP)
    rect(ax, 0, xmax, -hw, hw, PAV, z=1)
    rect(ax, -pad_len, 0, -hw, hw, PAV2, z=1)
    # pre-threshold chevrons on the blast pad (6.2.25): yellow, >= 0.9 m, 45 deg, pitch 30 m, apex towards the runway
    X = W
    for k in range(10):
        apex = -(6 + X / 4) - 30 * k
        if apex - X / 2 < -pad_len - 1: break
        for s in (-1, 1):
            ax.plot([apex, apex - X / 2], [0, s * X / 2], color=Y_, lw=1.4, zorder=4, solid_capstyle='butt')
    # edge stripes 0.9 m (6.2.7), full length incl. the displaced part
    for s in (-1, 1): rect(ax, 0, xmax, s * hw - (0.9 if s > 0 else 0), s * hw + (0.9 if s < 0 else 0), W_)
    # displaced-threshold area (permanent, fig. 6.2.4(b)): centreline arrows; transverse bar >= 1.8 m at the DTHR
    if dthr > 0:
        rect(ax, dthr, dthr + 1.8, -hw + 0.9, hw - 0.9, W_)
        xa = dthr - 20
        while xa - 30 > 5:
            ax.plot([xa - 30, xa - 6], [0, 0], color=W_, lw=1.3, zorder=3, solid_capstyle='butt')
            ax.add_patch(Polygon([[xa, 0], [xa - 6, 1.5], [xa - 6, -1.5]], color=W_, zorder=3, lw=0))
            xa -= 50
    t0 = dthr + (1.8 if dthr else 0)
    # threshold stripes (6.2.4): start 6 m inside, 45 m long (>= 30, preferably 45), ~1.8 m wide, double centre gap
    n = {18: 4, 23: 6, 30: 8, 45: 12, 60: 16}[W]; lim = min(hw - 3, 27.0); per = n // 2
    s = (lim - per * 1.8) / (per + 1)          # fit spacing (inf): 45 m -> 1.45 m, 60 m -> 1.575 m
    for side in (-1, 1):
        y = s                                   # half of the doubled centre gap = s
        for i in range(per):
            rect(ax, t0 + 6, t0 + 51, side * y if side > 0 else -y - 1.8, side * y + 1.8 if side > 0 else -y, W_); y += 1.8 + s
    # designation (6.2.2, fig. 6.2.2-1(b)): 12 m gap, letter 9 m, 6 m gap, number 9 m (glyph forms not reproduced)
    xl = t0 + 51 + 12
    ax.text(xl + 4.5, 0, letter, rotation=-90, ha='center', va='center', fontsize=7.5, color=W_, family='DejaVu Sans', weight='bold', zorder=5)
    ax.text(xl + 9 + 6 + 4.5, 0, label_num, rotation=-90, ha='center', va='center', fontsize=7.5, color=W_, weight='bold', zorder=5)
    xc = xl + 9 + 6 + 9 + 12
    # centreline (6.2.3): 30 m stripe + 20 m gap (pitch 50-75 m, stripe >= max(gap, 30 m)); CAT I: >= 0.45 m wide
    x = xc
    while x < xmax: ax.plot([x, min(x + 30, xmax)], [0, 0], color=W_, lw=1.3, zorder=3, solid_capstyle='butt'); x += 50   # 0.45 m, drawn >= 1.3 pt
    # aiming point (6.2.5): starts at the visual approach slope origin (PAPI); LDA >= 2400: 45-60 m x 6-10 m, inner gap 18-22.5 m
    apl, apw, apg = 60, 9, (18 if W == 45 else 22.5)
    for side in (-1, 1): rect(ax, t0 - (1.8 if dthr else 0) + ap_start, t0 - (1.8 if dthr else 0) + ap_start + apl, side * apg / 2 if side > 0 else -apg / 2 - apw, side * apg / 2 + apw if side > 0 else -apg / 2, W_)
    # TDZ pattern A (6.2.6): pairs every 150 m from 150 m, 22.5 x 3 m, same inner gap; pairs within 50 m of the aiming point omitted
    thr = t0 - (1.8 if dthr else 0)
    for k in range(1, 7):
        x0 = thr + 150 * k
        a0, a1 = thr + ap_start, thr + ap_start + apl
        if x0 + 22.5 > a0 - 50 and x0 < a1 + 50: continue
        for side in (-1, 1): rect(ax, x0, x0 + 22.5, apg / 2 if side > 0 else -apg / 2 - 3, apg / 2 + 3 if side > 0 else -apg / 2, W_)
    # annotations
    for xx, txt in [(0, 'runway end'), (dthr, f'DTHR +{dthr} m'), (thr + ap_start, f'aiming point at PAPI origin (+{ap_start} m, AIP)')]:
        ax.annotate(txt, (xx, hw + 7.5), (xx, hw + 22), fontsize=7, ha='center', arrowprops=dict(arrowstyle='-', lw=0.6))
    ax.set_xlim(-pad_len - 20, xmax); ax.set_ylim(-hw - 30, hw + 32); ax.set_aspect('equal'); ax.set_yticks([])
    ax.set_title(title, fontsize=9, loc='left'); ax.set_xlabel('m from the pavement end (blast pad negative)', fontsize=7); ax.tick_params(labelsize=7)
fig = plt.figure(figsize=(18, 16))
gs = fig.add_gridspec(5, 6, height_ratios=[1, 1.15, 0.95, 0.75, 0.8], hspace=0.55, wspace=0.25)
ax1 = fig.add_subplot(gs[0, :]); ax2 = fig.add_subplot(gs[1, :])
runway_end(ax1, 45, 100, 60, 474, '18', 'L', 'RWY 18L (36R alike): 45 m wide, THR displaced 100 m, blast pad 60 m (AIP mirror); 12 threshold stripes; TDZ 5 pairs drawn (6th omitted: within 50 m of the aiming point)')
runway_end(ax2, 60, 300, 120, 393, '18', 'R', 'RWY 18R (36L alike): 60 m wide, THR displaced 300 m, blast pad 120 m (AIP mirror); 16 threshold stripes; same TDZ rule')
# ---- detail panels ----
def panel(i, j, title, xl, yl, span=1):
    ax = fig.add_subplot(gs[i, j:j + span]); ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect('equal', adjustable='datalim'); ax.set_xticks([]); ax.set_yticks([])
    ax.set_facecolor('#b9bbbd'); ax.set_title(title, fontsize=7, loc='left'); return ax
# runway-holding pattern A (6.2.10): 4 lines 0.3 m, gaps 0.3 m (2.1 m); dashes 0.9/0.9 m on the runway side; 0.1 m black surround
ax = panel(2, 0, 'Holding A (6.2.10): 4 x 0.3 m, gaps\n0.3 m; dashes 0.9/0.9 m, runway side', (-6, 6), (-3, 3.5))
rect(ax, -6, 6, -1.15, 1.15, K_, z=2)
for k, y in enumerate([-1.05, -0.45, 0.15, 0.75]):
    if k < 2: rect(ax, -6, 6, y, y + 0.3, Y_)
    else:
        x = -6
        while x < 6: rect(ax, x, min(x + 0.9, 6), y, y + 0.3, Y_); x += 1.8
rect(ax, -0.075, 0.075, -3, -1.15 - 0.9, Y_); ax.text(0, 3.0, 'runway  ^', ha='center', fontsize=7)
# pattern B (ladder)
ax = panel(2, 1, 'Holding B (CAT II/III): 0.3 m rails\n1.5 m apart; paired rungs every 3 m', (-6, 6), (-3, 3.5))
rect(ax, -6, 6, -1.15, 1.15, K_, z=2)
for y in (-1.05, 0.75): rect(ax, -6, 6, y, y + 0.3, Y_)
for x0 in (-4.5, -1.5, 1.5, 4.5):
    for dx in (-0.45, 0.15): rect(ax, x0 + dx, x0 + dx + 0.3, -0.75, 0.75, Y_)
# intermediate holding (6.2.11): single dashed line 0.3 m, 0.9/0.9 m; centreline stops 0.9 m short
ax = panel(2, 2, 'Intermediate holding (6.2.11): 0.3 m\ndashes 0.9/0.9 m; CL stops 0.9 m short', (-6, 6), (-3, 3.5))
x = -6
while x < 6: rect(ax, x, min(x + 0.9, 6), -0.15, 0.15, Y_); x += 1.8
for s in (-1, 1): rect(ax, -0.075, 0.075, s * 1.05, s * 3.5, Y_)
# enhanced centreline (6.2.8-6): side dashes 0.15 m, 3 m long, 1 m gap, 0.15 m from the CL, 47 m from pattern A
ax = panel(2, 3, 'Enhanced CL (6.2.8): 0.15 m side dashes\n3 m / 1 m, 0.15 m off CL, 47 m before A', (-1, 11), (-3, 3.5))
rect(ax, -1, 11, -0.075, 0.075, Y_)
for s in (-1, 1):
    x = 0.9
    while x < 11: rect(ax, x, min(x + 3, 11), s * 0.225 - 0.075, s * 0.225 + 0.075, Y_); x += 4
rect(ax, -1, -0.1, -2.5, 2.5, Y_); ax.text(0.2, 2.6, '<- holding A', fontsize=6)
# stand number marking (6.2.16-2): yellow pentagon, characters A = 4 m, plate B = 5 m, point E = 2 m, black border 0.1 m
ax = panel(2, 4, 'Stand number (6.2.16): yellow, black\nchars 4 m; plate 5 m + 2 m; border 0.1 m', (-4.5, 4.5), (-1, 8))
ax.add_patch(Polygon([[-3.2, 0], [3.2, 0], [3.2, 5], [0, 7], [-3.2, 5]], closed=True, facecolor=Y_, edgecolor=K_, lw=1.2, zorder=3))
ax.text(0, 2.5, '213', ha='center', va='center', fontsize=17, weight='bold', color=K_, zorder=4)
# taxiway edge / centreline / apron safety lines
ax = panel(2, 5, 'Twy edge 2 x 0.15 m; CL 0.15 m + black\n0.05 m on concrete; stand safety line red', (-3, 3), (-3, 3))
for y in (-2.4, -2.1): rect(ax, -3, 3, y, y + 0.15, Y_)
rect(ax, -3, 3, -0.125, 0.125, K_); rect(ax, -3, 3, -0.075, 0.075, Y_)
rect(ax, -3, 3, 2.0, 2.1, R_)
for x in (-2.5, -0.5, 1.5): ax.plot([x, x + 0.8], [1.2, 2.0], color=R_, lw=1)
ax.text(-2.9, 1.0, 'red hatched 45 deg, 2 m', fontsize=6)
# signs and markings colours
ax = fig.add_subplot(gs[3, :]); ax.set_xlim(0, 60); ax.set_ylim(0, 5); ax.axis('off')
ax.set_title('Signs (ch. 8, app. H): face 600 mm / text 400 mm for code 3-4 mandatory; info text 300 mm (exit, vacated 400 mm)', fontsize=8, loc='left')
def sign(x, y, w, txt, fc, tc, ec=None):
    ax.add_patch(Rectangle((x, y), w, 1.2, facecolor=fc, edgecolor=ec or fc, lw=1.5)); ax.text(x + w / 2, y + 0.6, txt, color=tc, ha='center', va='center', fontsize=10, weight='bold')
def cap(x, txt): ax.text(x, 2.6, txt, fontsize=7, va='top')
sign(0.3, 3.2, 2.2, 'B2', K_, Y_); sign(2.5, 3.2, 3.6, '18L-36R', R_, W_); cap(0.3, 'location + runway designation\n(mandatory, red/white)')
sign(8.5, 3.2, 2.0, 'B', K_, Y_, Y_); cap(8.5, 'location alone:\nyellow border')
sign(13.5, 3.2, 2.6, '<- A', Y_, K_); sign(16.1, 3.2, 1.6, 'B', K_, Y_); sign(17.7, 3.2, 2.6, 'C ->', Y_, K_); cap(13.5, 'direction assembly\n(left side of the taxiway)')
sign(22.5, 3.2, 3.6, '18R CAT II', R_, W_); cap(22.5, 'CAT II/III holding\n(mandatory)')
sign(28.0, 3.2, 2.0, '231', Y_, K_); cap(28.0, 'stand number sign: chars >= 600 mm,\nmay carry lat/long (1/4 height)')
ax.add_patch(Rectangle((36.0, 3.1), 3.6, 1.4, facecolor=R_)); ax.text(37.8, 3.8, 'NO ENTRY', color=W_, ha='center', va='center', fontsize=9, weight='bold'); cap(36.0, 'no-entry\n(sign or marking)')
ax.add_patch(RegularPolygon((42.5, 3.8), 8, radius=0.8, orientation=math.pi / 8, facecolor=R_, edgecolor=W_, lw=1.5)); ax.text(42.5, 3.8, '停', color=W_, ha='center', va='center', fontsize=10, family='WenQuanYi Zen Hei'); cap(41.5, 'road-holding sign: Chinese text\n(8.6.2), red/white octagon 0.6 m')
sign(49.0, 3.2, 3.0, 'B3 ->', Y_, K_); cap(49.0, 'exit / destination / vacated:\nyellow + black')
# lights colour legend
ax = fig.add_subplot(gs[4, :]); ax.set_xlim(0, 60); ax.set_ylim(0, 6); ax.axis('off')
ax.set_title('Lights (ch. 7): colours and patterns used by the renderer', fontsize=8, loc='left')
rows = [('runway edge', ['w'] * 8 + ['y'] * 3, 'variable white; yellow over the last 600 m; red towards approach before a DTHR'),
        ('runway centreline', ['w'] * 5 + ['r', 'w', 'r', 'w'] + ['r'] * 3, 'white; red/white 900-300 m from the end; red last 300 m; ~15 m'),
        ('threshold / end', ['g'] * 5 + [' '] + ['r'] * 5, 'green threshold (and wing bars); red runway end'),
        ('taxiway CL / edge', ['g', 'y', 'g', 'y', 'g', 'g', ' ', 'b', 'b', 'b'], 'green (green/yellow alternating in ILS area); edge blue'),
        ('stop bar / RGL / REL', ['r'] * 4 + [' ', 'y', ' ', 'y', ' ', 'r', 'r'], 'stop bar red <= 3 m; guard lights yellow flashing 30-60/min; RWSL red')]
cmap = dict(w='#ffffff', y='#ffc000', r='#e00000', g='#00d060', b='#2050ff')
for k, (name, cs, note) in enumerate(rows):
    y = 5.2 - k * 1.1; ax.text(0, y, name, fontsize=7.5, va='center')
    for i, c in enumerate(cs):
        if c != ' ': ax.add_patch(Circle((7.2 + i * 0.7, y), 0.25, color=cmap[c], ec='k', lw=0.4))
    ax.text(16.5, y, note, fontsize=7.5, va='center')
fig.suptitle('ZSSS markings, signs and lights per MH 5001-2021 (CAAC) - our drawing from the standard\'s parameters; runway data from the AIP mirror (short facts).\n'
             'inf choices within the ranges: stripes 45 m long, fitted stripe spacing; aiming point 60 x 9 m; TDZ pattern A; centreline 30/20 m; arrow and chevron detail schematic.', fontsize=9)
fig.savefig(sys.argv[1], dpi=105, bbox_inches='tight')
print('ok')
