"""Draw the B2 NOTAM plate: ZSSS NOTAM effects on a calendar, and the runway availability of one night as the
simulator should apply it (AIP night rule + NOTAMs + the no-scheduled-flights window).

Input: the local JSON written by tools/notam/notam_summary.py. Output: docs/phase1/sources_sim_notam.png.
Usage: python3 -I tools/notam/notam_plate.py <zsss_notams.json> <out.png> [night YYYY-MM-DD (local date of the evening)]
"""
import datetime as dt, json, sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402

UTC = dt.timezone.utc
# Fix round 1: the plate shows only the NOTAMs the simulator applies (sources_sim.md §4.2); the AIRAC AMDT 12 trigger is
# drawn as a dashed line. Expired (F4548-50) and cosmetic (F3202) effects are left out.
APPLIED = ('F4551/26', 'F4552/26', 'F4313/26', 'F4301/26', 'F4275/26', 'F4276/26')


def t(s):
    if s in (None, 'PERM'):
        return dt.datetime(2027, 2, 15, tzinfo=UTC)
    return dt.datetime.strptime(s, '%Y-%m-%dT%H:%MZ').replace(tzinfo=UTC)


def active(eff, when):
    """Is a sim effect active at datetime `when` (UTC)?"""
    if not (t(eff['from_utc']) <= when <= t(eff['to_utc'])):
        return False
    if eff.get('daily_utc'):
        a, b = eff['daily_utc']
        hm = when.hour * 100 + when.minute
        return int(a) <= hm < int(b)
    return True


def runway_state(effs, when):
    """-> {(rwy, 'arr'|'dep'): (ok, reason)} for 18L/36R and 18R/36L at `when` (UTC). AIP (mirror) AD 2.20 2.1.1
    and 2.1.6; NOTAM effects rwy_closed / rwy_no_landing; local hours 00-06 carry no scheduled flights (AD 2.3)."""
    st = {}
    for rwy in ('18L/36R', '18R/36L'):
        for op in ('arr', 'dep'):
            ok, why = True, 'mainly ' + ('arrivals' if rwy == '18L/36R' else 'departures') + ' (AD 2.20 2.1.1)'
            if rwy == '18R/36L' and op == 'arr' and 16 <= when.hour < 23:
                ok, why = False, 'no landing 1600-2300 UTC exc. ALTN (AD 2.20 2.1.6)'
            for e in effs:
                if e.get('target') != rwy or not active(e, when):
                    continue
                if e['effect'] == 'rwy_closed':
                    ok, why = False, 'NOTAM %s CLSD' % e['notam']
                elif e['effect'] == 'rwy_no_landing' and op == 'arr':
                    ok, why = False, 'NOTAM %s no landing' % e['notam']
            st[(rwy, op)] = (ok, why)
    return st


def main(src, out, night='2026-11-14'):
    d = json.load(open(src, encoding='utf-8'))
    effs = [e for e in d['sim'] if e['notam'] in APPLIED]
    fig = plt.figure(figsize=(12, 7.0))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.25, 1.0], hspace=0.42)
    # ---- (A) calendar
    a = fig.add_subplot(gs[0])
    rows = []
    for e in effs:
        lab = {'rwy_closed': 'RWY %s closed', 'rwy_no_landing': 'RWY %s no landing', 'stand_closed': 'stand %s closed',
               'twy_closed': 'TWY closures%s', 'wip_area': 'WIP%s', 'rapid_exit_distances': 'rapid-exit distances%s',
               'visual_approach': 'visual approach rules%s'}[e['effect']]
        tgt = e['target'] if isinstance(e['target'], str) and e['effect'] in ('rwy_closed', 'rwy_no_landing', 'stand_closed') else ''
        if e['effect'] == 'wip_area':
            tgt = ' ' + e['target'].split(',')[0].replace(' NORTH OF RWY18L DTHR', ' N of DTHR 18L').replace('M-', '-')
        rows.append(((lab % tgt) + ('  [%s-%sZ daily]' % tuple(e['daily_utc']) if e.get('daily_utc') else ''), e))
    x0, x1 = dt.datetime(2026, 10, 25, tzinfo=UTC), dt.datetime(2027, 1, 20, tzinfo=UTC)
    colors = {'rwy_closed': '#c0504d', 'rwy_no_landing': '#e39a3b', 'stand_closed': '#7a52a1', 'twy_closed': '#d98880',
              'wip_area': '#8c8c8c', 'rapid_exit_distances': '#4f81bd', 'visual_approach': '#4f81bd'}
    for i, (lab, e) in enumerate(rows):
        s, f = max(t(e['from_utc']), x0), min(t(e['to_utc']), x1)
        hatch = '////' if e.get('daily_utc') else None
        a.barh(i, (f - s).total_seconds() / 86400, left=mdates.date2num(s), height=0.6, color=colors[e['effect']],
               hatch=hatch, edgecolor='white' if hatch else None, lw=0)
        a.text(mdates.date2num(x0) + 0.5, i, '%s  (%s)' % (lab, e['notam']), va='center', fontsize=7.2)
    now = dt.datetime(2026, 11, 14, 6, 0, tzinfo=UTC)
    a.axvline(mdates.date2num(now), color='k', lw=1)
    a.text(mdates.date2num(now), len(rows) - 0.3, ' today 14 Nov', fontsize=7)
    a.axvline(mdates.date2num(dt.datetime(2026, 11, 25, 16, tzinfo=UTC)), color='#555', ls='--', lw=0.8)
    a.text(mdates.date2num(dt.datetime(2026, 11, 25, 16, tzinfo=UTC)), -0.9, ' AIRAC AMDT 12: wind-direction indicators move', fontsize=7)
    a.set_xlim(mdates.date2num(x0), mdates.date2num(x1))
    a.set_ylim(-1.2, len(rows))
    a.set_yticks([])
    a.invert_yaxis()
    a.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 10, 20]))
    a.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    a.set_title('(A) ZSSS NOTAM effects the simulator applies, from the eAIP NOTAM Summary (in force %s; issued later: '
                'not covered) [our paraphrase, inf reading]; hatched = daily window only' % d['in_force_at'], fontsize=8.5,
                loc='left')
    a.grid(axis='x', alpha=0.3)
    # ---- (B) one night, 10-min resolution
    b = fig.add_subplot(gs[1])
    loc0 = dt.datetime.strptime(night, '%Y-%m-%d').replace(tzinfo=UTC) + dt.timedelta(hours=12 - 8)   # 12:00 local
    keys = [('18L/36R', 'arr'), ('18L/36R', 'dep'), ('18R/36L', 'arr'), ('18R/36L', 'dep')]
    step = dt.timedelta(minutes=10)
    n = int(dt.timedelta(hours=24) / step)
    for i in range(n):
        when = loc0 + i * step
        st = runway_state(effs, when)
        lh = (when + dt.timedelta(hours=8)).hour
        for j, k in enumerate(keys):
            ok, why = st[k]
            c = '#9bbb59' if ok else ('#c0504d' if 'NOTAM' in why else '#e39a3b')
            if ok and ((k[0] == '18L/36R' and k[1] == 'dep') or (k[0] == '18R/36L' and k[1] == 'arr')):
                c = '#d7e4bd'   # allowed but not the runway's main role
            b.barh(j, 1 / 144, left=i / 144, color=c, height=0.7, lw=0)
        b.barh(4, 1 / 144, left=i / 144, height=0.7, lw=0, color='#bfbfbf' if 0 <= lh < 6 else '#4f81bd')
    b.set_yticks(range(5))
    b.set_yticklabels(['18L/36R landings', '18L/36R take-offs', '18R/36L landings', '18R/36L take-offs',
                       'scheduled flights'], fontsize=8)
    b.invert_yaxis()
    ticks = [i / 24 for i in range(0, 25, 2)]
    b.set_xticks(ticks)
    b.set_xticklabels([('%02d L\n%02dZ' % ((12 + h) % 24, (4 + h) % 24)) for h in range(0, 25, 2)], fontsize=7)
    b.set_xlim(0, 1)
    b.set_title('(B) Night of %s (local) as the simulator should run it [inf]: green = main role, pale green = allowed, '
                'orange = AIP restriction, red = NOTAM closure; grey = no scheduled flights 00-06 local' % night,
                fontsize=8.5, loc='left')
    b.text(0, -0.25, 'AIP (mirror) AD 2.20: 2.1.1 18R/36L mainly departures, 18L/36R mainly arrivals (departures by ATC '
           'clearance); 2.1.6 no landing on 18R/36L 1600-2300 UTC except alternates. NOTAM F4551/26: 18L/36R closed '
           '1700-2200 UTC daily, 10-29 Nov.', fontsize=6.8, transform=b.transAxes, color='#333')
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main(*sys.argv[1:])
