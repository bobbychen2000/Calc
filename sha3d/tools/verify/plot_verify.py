import csv, sys, os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
cache, out = sys.argv[1], sys.argv[2]
BLUE, ORANGE, AQUA, GRAY = '#2a78d6', '#eb6834', '#1baf7a', '#a3a29c'
SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 9.5, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'axes.titlesize': 10.5, 'axes.titleweight': 'bold', 'axes.titlecolor': INK, 'text.color': INK})
fig, ax = plt.subplots(2, 2, figsize=(13, 8.6), facecolor=SURF)
for a in ax.flat:
    a.set_facecolor(SURF); a.grid(axis='x', color=GRID, lw=0.8); a.set_axisbelow(True)
    for s in ('top', 'right'): a.spines[s].set_visible(False)
# A: SHA vs PVG against official far-end data
A = ax[0, 0]
rows = [('HKIA 13 Nov: all HKG-Shanghai\noperating flights vs DB label', 51, 0, 0),
        ('Taipei Songshan 14 Nov: operated\nTSA-Shanghai flights vs DB label', 12, 0, 0),
        ("B1's identified HKG-SHA movements\n(10+12 Nov) vs HKIA SHA list", 23, 1, 0)]
for i, (lab, ok, absent, bad) in enumerate(rows):
    y = len(rows) - 1 - i
    A.barh(y, ok, color=BLUE, height=0.5); A.barh(y, absent, left=ok + 0.4, color=GRAY, height=0.5)
    A.text(ok + absent + 1.5, y, f'{ok} agree' + (f', {absent} not listed' if absent else '') + f', {bad} contradicted', va='center', color=INK2)
A.set_yticks(range(len(rows))); A.set_yticklabels([r[0] for r in rows][::-1]); A.set_xlim(0, 85)
A.set_xlabel('flights'); A.set_title('A  SHA vs PVG: route-DB labels against official airport data')
# B: runway rule
B = ax[0, 1]
bars = [('chosen rule, in-sample', 86.3, BLUE), ('chosen rule, leave-one-day-out', 78.0, BLUE), ('into the wind (no parameters)', 80.4, AQUA),
        ('literal AIP 3 / 5 m/s', 64.9, ORANGE), ('always RWY 36', 58.3, GRAY)]
for i, (lab, v, c) in enumerate(bars):
    y = len(bars) - 1 - i
    B.barh(y, v, color=c, height=0.5)
    B.text((95.5 if i == 0 else v + 1), y, f'{v:.1f} %', va='center', color=INK2)
B.errorbar(86.3, len(bars) - 1, xerr=[[86.3 - 78.4], [94.1 - 86.3]], fmt='none', ecolor=INK, capsize=3, lw=1)
B.text(1, len(bars) - 1 - 0.42, 'bar: 95 % day-bootstrap interval 78.4-94.1 %', fontsize=8, color=INK2, va='top')
B.set_yticks(range(len(bars))); B.set_yticklabels([b[0] for b in bars][::-1]); B.set_xlim(0, 110)
B.set_xlabel('% agreeing with the runway in RVR/WS groups (168 METARs, 59 days)')
B.set_title('B  ZSSS runway-direction rule: in-sample vs out-of-sample')
# C: sigma distribution and the 7 wrong-leg records
C = ax[1, 0]
sig = []
for day in ('2026-11-10', '2026-11-12'):
    sig += [float(r['sigma_min']) for r in csv.DictReader(open(os.path.join(cache, 'observed_elsewhere', f'sha_observed_{day}.csv'))) if r['method']]
cnt, _, _ = C.hist(sig, bins=[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20], color=BLUE, rwidth=0.92)
top = max(cnt)
bad = sorted([18.6, 11.3, 3.4, 11.3, 3.5, 11.4, 5.4])
ys = [top * (1.08 + 0.055 * (k % 3)) for k in range(len(bad))]
C.plot(bad, ys, 'o', ms=8, color=ORANGE, mec=SURF, mew=2, ls='none')
C.text(0.2, top * 1.27, '7 records with the SHA end on the wrong leg (stale or early callsign):\ntrue error is hours; claimed 1-sigma 3-19 min (orange dots)', color=INK2, fontsize=8.5, va='bottom')
C.axvline(20, color=INK2, lw=1, ls='--'); C.text(19.7, top * 0.9, 'largest claimed\nsigma 18.6 min', ha='right', color=INK2, fontsize=8.5)
C.set_xlabel('claimed 1-sigma of the inferred SHA time (min), 1,091 identified movements'); C.set_ylabel('movements')
C.grid(axis='y', color=GRID, lw=0.8); C.grid(axis='x', visible=False); C.set_ylim(0, top * 1.45)
C.set_title('C  B1 timing: claimed sigma, and records outside it')
# D: M1 sigma used vs validated
D = ax[1, 1]
grp = [('China far end\n(10 movements on 10 Nov)', 16.3, 20.8), ('non-China far end, 10 Nov\n(9.6 used on 12 Nov; 22 movements)', 11.6, 7.0)]
for i, (lab, used, val) in enumerate(grp):
    D.bar(i - 0.18, used, 0.34, color=BLUE); D.bar(i + 0.18, val, 0.34, color=ORANGE)
    D.text(i - 0.18, used + 0.4, f'{used}', ha='center', color=INK2); D.text(i + 0.18, val + 0.4, f'{val}', ha='center', color=INK2)
D.set_xticks(range(len(grp))); D.set_xticklabels([g[0] for g in grp]); D.set_ylim(0, 28)
from matplotlib.patches import Patch
D.legend(handles=[Patch(color=BLUE, label='sigma used (in-sample fit residual)'), Patch(color=ORANGE, label='sigma from held-out validation (1.4826 x median |error|)')], frameon=False, loc='upper right'); D.grid(axis='y', color=GRID, lw=0.8); D.grid(axis='x', visible=False)
D.set_ylabel('1-sigma (min)'); D.set_title('D  B1 method M1: sigma used vs out-of-sample')
fig.suptitle('C2 adversarial check of B1-B3: re-derived numbers (aggregates only; per-flight data stays local)', fontsize=11.5, color=INK, x=0.01, ha='left')
fig.text(0.01, 0.005, 'Sources: adsb.lol globe_history (ODbL 1.0); VRS standing data (CC0); Airport Authority Hong Kong via DATA.GOV.HK; Taipei Songshan Airport, Taiwan OGDL v1.0; '
         'Iowa Environmental Mesonet METAR archive (public domain). All panels: our analysis 2026-11-14.', fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.02, 1, 0.96))
fig.savefig(out, dpi=130, facecolor=SURF)
