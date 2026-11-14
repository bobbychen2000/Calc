"""Inferred hourly movement profile for ZSSS (arrivals and departures per local hour), for the simulator.

No hourly profile is published (docs/phase0/field.md 1.3). This derives one [inf] from the aggregate counts of task B1
("observed elsewhere": SHA movements identified from open ADS-B outside the Shanghai gap, with inferred SHA-side times,
about 70 % of the daily movements; docs/phase1/observed_elsewhere_stats.json, aggregates only):

  profile(h, role) = mean over the analysed days of identified(h, role)  x  (daily target / mean identified per day)

i.e. the unidentified ~30 % are assumed to share the identified flights' hourly shape. Hours 01-05 local stay 0
(no scheduled flights 00-06, AD 2.3 / field.md); the 00 h arrivals are kept (delays). Daily targets: 783.4 (CAAC Jan-Sep
2026 mean, verified) and 802 (SAA winter 2026/27 plan, secondary).

Usage: python3 -I tools/sim/hourly_profile.py <sha3d root>
Writes docs/phase1/sources_sim_hourly.png and docs/phase1/sources_sim_hourly.json.
"""
import json, os, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT = os.path.join(ROOT, 'docs', 'phase1')


def main():
    st = json.load(open(os.path.join(OUT, 'observed_elsewhere_stats.json'), encoding='utf-8'))
    days = st['days']
    H = range(24)
    obs = {r: [sum(d['by_local_hour'][str(h)][r] for d in days) / len(days) for h in H] for r in ('arr', 'dep')}
    per_day = sum(sum(v) for v in obs.values())
    res = {'basis': 'B1 observed-elsewhere aggregates, days ' + ', '.join(d['day'] for d in days) +
           '; uniform scaling of the identified hourly shape to the daily target [inf]',
           'identified_per_day_mean': round(per_day, 1), 'identified_by_local_hour': obs, 'profiles': {}}
    for name, target in (('caac_2026_jan_sep_783', 783.4), ('saa_winter_2026_802', 802.0)):
        k = target / per_day
        prof = {r: [round(v * k, 1) for v in obs[r]] for r in obs}
        tot = [prof['arr'][h] + prof['dep'][h] for h in H]
        pk = max(H, key=lambda h: tot[h])
        # rolling 60-min peak cannot be resolved from hourly bins; report the busiest clock hour
        res['profiles'][name] = {'daily_target': target, 'scale': round(k, 3), 'arr': prof['arr'], 'dep': prof['dep'],
                                 'total': [round(x, 1) for x in tot], 'busiest_hour_local': pk,
                                 'busiest_hour_movements': round(tot[pk], 1),
                                 'mean_06_24': round(sum(tot[6:24]) / 18, 1)}
    json.dump(res, open(os.path.join(OUT, 'sources_sim_hourly.json'), 'w'), indent=1)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    p = res['profiles']['caac_2026_jan_sep_783']
    fig, ax = plt.subplots(figsize=(11, 4.6))
    x = list(H)
    ax.bar([h - 0.2 for h in x], p['arr'], width=0.4, color='#4f81bd', label='arrivals, inferred profile (783.4/day)')
    ax.bar([h + 0.2 for h in x], p['dep'], width=0.4, color='#c0504d', label='departures, inferred profile')
    ax.step([h - 0.5 for h in x] + [23.5], [obs['arr'][h] + obs['dep'][h] for h in x] + [0], where='post',
            color='#555', lw=1.2, label='identified (obs elsewhere, mean of 2 days, ~70 %)')
    ax.plot(x, p['total'], 'k.-', lw=1, ms=5, label='inferred total per hour')
    ax.axhline(43, color='#e39a3b', ls='--', lw=1)
    ax.text(0.2, 43.8, 'declared capacity 43/h (CAAC 2011)', fontsize=7.5, color='#a0601a')
    ax.axhline(59, color='#7a52a1', ls=':', lw=1)
    ax.text(0.2, 59.8, 'peak hour 59 (caacnews 2021)', fontsize=7.5, color='#7a52a1')
    ax.plot([6, 24], [44.6, 44.6], color='#9bbb59', lw=1.5)
    ax.text(18.2, 41.6, 'flat 06-24 mean 44.6/h', fontsize=7.5, color='#5d7a2a')
    ax.axvspan(0.5, 5.5, color='#eeeeee', zorder=0)
    ax.text(1.1, 30, 'no scheduled\nflights 00-06\n(AD 2.3)', fontsize=7.5, color='#666')
    ax.set_xticks(x)
    ax.set_xlabel('local hour (UTC+8), start of hour')
    ax.set_ylabel('movements per hour')
    ax.set_ylim(0, 66)
    ax.set_xlim(-0.6, 23.6)
    ax.legend(fontsize=7.5, loc='upper right', ncol=2)
    ax.set_title('ZSSS hourly movement profile [inf]: shape of %0.0f identified movements/day (task B1) scaled x%.2f to '
                 '783.4/day; busiest hour %02d h = %.0f movements' % (per_day, p['scale'], p['busiest_hour_local'],
                                                                       p['busiest_hour_movements']), fontsize=9)
    ax.grid(axis='y', alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'sources_sim_hourly.png'), dpi=110)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ('scale', 'busiest_hour_local', 'busiest_hour_movements',
                                                                  'mean_06_24', 'total')} for k, v in res['profiles'].items()}))


if __name__ == '__main__':
    main()
