"""Measure the ZSSS METAR stream and its runway-direction implications; draw the B2 weather plates.

Inputs (downloads, untrusted text; run with python3 -I):
  refs/cache/metar/awc_metar_zsss_24h.raw.txt         aviationweather.gov Data API, last 24 h (raw)
  refs/cache/metar/awc_30d/metar_raw_to_*.txt         aviationweather.gov Data API, 30 days (raw, 7-day queries)
  refs/cache/metar/iem_zsss/zsss_metar_<year>.csv     Iowa Environmental Mesonet ASOS/METAR archive, 2023-2026
Outputs:
  docs/phase1/sources_sim_metar24h.png   24 h timeline (wind components on 18/36, visibility, QNH, trend, rule)
  docs/phase1/sources_sim_flow.png       climatology: inferred share of north flow (RWY 36) by month and local hour
  docs/phase1/sources_sim_wx_stats.json  the measured numbers quoted in sources_sim.md

Usage: python3 -I tools/wx/metar_stats.py <sha3d root>
"""
import collections, csv, datetime as dt, glob, json, math, os, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'wx'))
import metar_zsss as M  # noqa: E402

CACHE = os.path.join(ROOT, 'refs', 'cache', 'metar')
OUT = os.path.join(ROOT, 'docs', 'phase1')
UTC = dt.timezone.utc


def awc_reports(paths, ref_end):
    """Raw AWC lines -> {(time, type, raw)}; the report day-of-month is resolved against the query end time."""
    seen = {}
    for p in paths:
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if not line.startswith(('METAR', 'SPECI')):
                continue
            d = M.decode(line)
            t = resolve(d['day'], d['hour'], d['minute'], ref_end)
            seen[(t, d['type'], line)] = d
    return [(k[0], v) for k, v in sorted(seen.items())]


def resolve(day, hour, minute, ref_end):
    t = ref_end.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
    # walk back month by month until the day fits and lies before ref_end (+1 h slack)
    for back in range(3):
        y, m = t.year, t.month - back
        while m <= 0:
            m += 12; y -= 1
        try:
            c = dt.datetime(y, m, day, hour, minute, tzinfo=UTC)
        except ValueError:
            continue
        if c <= ref_end + dt.timedelta(hours=1):
            return c
    raise ValueError((day, hour, minute))


def iem_reports():
    out = []
    for p in sorted(glob.glob(os.path.join(CACHE, 'iem_zsss', 'zsss_metar_*.csv'))):
        with open(p, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if not row.get('metar') or row['metar'] == 'M':
                    continue
                t = dt.datetime.strptime(row['valid'], '%Y-%m-%d %H:%M').replace(tzinfo=UTC)
                raw = row['metar']
                # IEM strips the METAR/SPECI word; ZSSS routine reports are at :00 and :30 (AWC data), so any other
                # minute is taken as a SPECI [inf]
                typ = 'SPECI' if raw.startswith('SPECI') or t.minute not in (0, 30) else 'METAR'
                d = M.decode(raw if raw.startswith(('METAR', 'SPECI')) else typ + ' ' + raw)
                out.append((t, d))
    # IEM may hold a report twice (routine + special query); keep unique raw per time
    uniq = {}
    for t, d in out:
        uniq[(t, d['raw'])] = (t, d)
    return sorted(uniq.values(), key=lambda x: x[0])


def stream_stats(reps):
    routine = [(t, d) for t, d in reps if d['type'] == 'METAR']
    speci = [(t, d) for t, d in reps if d['type'] == 'SPECI']
    mins = collections.Counter(t.minute for t, _ in routine)
    gaps = collections.Counter()
    for (a, _), (b, _) in zip(routine, routine[1:]):
        gaps[int((b - a).total_seconds() // 60)] += 1
    trend = collections.Counter()
    for _, d in reps:
        kinds = [g['kind'] for g in d['trend']]
        trend['+'.join(kinds) if kinds else 'none'] += 1
    units = collections.Counter(d.get('wind', {}).get('unit') for _, d in reps)
    q = [d['qnh_hpa'] for _, d in reps if 'qnh_hpa' in d]
    vis = [d['vis_m'] for _, d in reps if 'vis_m' in d]
    visc = collections.Counter('CAVOK' if d.get('cavok') else ('9999' if d.get('vis_ge') else
                               ('<1500' if d.get('vis_m', 99999) < 1500 else
                                '1500-4999' if d.get('vis_m', 99999) < 5000 else '5000-9000'))
                               for _, d in reps if 'vis_m' in d)
    rvr = sum(1 for _, d in reps if d.get('rvr'))
    vrb = sum(1 for _, d in reps if d.get('wind', {}).get('variable'))
    calm = sum(1 for _, d in reps if d.get('wind', {}).get('calm'))
    gust = sum(1 for _, d in reps if d.get('wind', {}).get('gust_ms'))
    qnh_inhg = sum(1 for _, d in reps if d.get('qnh_from_inhg'))
    span_h = (reps[-1][0] - reps[0][0]).total_seconds() / 3600 if reps else 0
    return {
        'first_utc': reps[0][0].isoformat() if reps else None, 'last_utc': reps[-1][0].isoformat() if reps else None,
        'span_h': round(span_h, 2), 'n_reports': len(reps), 'n_metar': len(routine), 'n_speci': len(speci),
        'metar_per_day': round(len(routine) / span_h * 24, 2) if span_h else None,
        'speci_per_day': round(len(speci) / span_h * 24, 2) if span_h else None,
        'metar_minute_of_hour': dict(sorted(mins.items())),
        'metar_gap_minutes': dict(sorted(gaps.items())),
        'trend_groups': dict(trend.most_common()),
        'wind_units': {str(k): v for k, v in units.items()},
        'wind_vrb': vrb, 'wind_calm': calm, 'wind_gust': gust,
        'qnh_hpa_min': min(q) if q else None, 'qnh_hpa_max': max(q) if q else None, 'qnh_from_inhg': qnh_inhg,
        'vis_m_min': min(vis) if vis else None, 'vis_classes': dict(visc.most_common()), 'reports_with_rvr': rvr,
    }


def flow_series(reps, start='36'):
    rule = M.RunwayDirection(start)
    out = []
    for t, d in reps:
        # the rule sees every report (METAR and SPECI, as a live simulator would); only routine reports are counted
        r, why = rule.step(d.get('wind'))
        if d['type'] == 'METAR':
            out.append((t, r, why, d))
    return out


def plot_24h(reps24, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    fs = flow_series(reps24)
    ts = [t for t, *_ in fs]
    h36 = [(M.components(d.get('wind'), '36') or (float('nan'),))[0] for *_, d in fs]
    vis = [d.get('vis_m', float('nan')) for *_, d in fs]
    q = [d.get('qnh_hpa', float('nan')) for *_, d in fs]
    rwy = [r for _, r, _, _ in fs]
    fig, ax = plt.subplots(4, 1, figsize=(11, 8.2), sharex=True, gridspec_kw={'height_ratios': [2.2, 1.5, 1.1, 0.6]})
    a = ax[0]
    a.axhline(0, color='#888', lw=0.8)
    a.axhspan(-5, -3, color='#f3c9a1', alpha=0.6, lw=0)
    a.axhspan(-9, -5, color='#e8998d', alpha=0.6, lw=0)
    a.plot(ts, h36, 'o-', color='#1f5fa8', ms=3.5, lw=1.2, label='headwind on RWY 36 (m/s, + = from the north)')
    for t, d in zip(ts, [x[3] for x in fs]):
        w = d.get('wind', {})
        if w.get('variable'):
            a.annotate('VRB', (t, 0.15), fontsize=6, ha='center', color='#555')
    a.set_ylim(-6, 6)
    a.set_ylabel('m/s')
    a.text(0.005, 0.04, 'tailwind on RWY 36: 3-5 m/s band = AIP AD 2.20 2.1.2 tolerance during a change; rule turns at > 1.5 m/s x2 or > 4 m/s', transform=a.transAxes,
           fontsize=7, color='#7a3b2e')
    a.legend(loc='upper right', fontsize=8)
    a.set_title('ZSSS routine METARs, 24 h to %s (aviationweather.gov Data API) [obs]; runway direction [inf]'
                % ts[-1].strftime('%Y-%m-%d %H:%MZ'), fontsize=9.5)
    b = ax[1]
    b.step(ts, vis, where='post', color='#2b7a3d')
    b.set_ylabel('visibility (m)')
    b.set_ylim(0, 10500)
    for t, d in zip(ts, [x[3] for x in fs]):
        for g in d['trend']:
            if g['kind'] in ('BECMG', 'TEMPO'):
                e = g.get('elements', {})
                lab = g['kind'][:1] + (' ' + str(e['vis_m']) if 'vis_m' in e else '') + \
                      (' ' + ','.join('%s%03d' % (s['cover'], (s['base_ft'] or 0) // 100) for s in e.get('sky', [])) if e.get('sky') else '')
                b.annotate(lab, (t, 9300), fontsize=6, rotation=90, ha='center', va='top', color='#6b4a8f')
    b.text(0.005, 0.86, 'purple: trend groups (B = BECMG, T = TEMPO) and their forecast values; all others NOSIG',
           transform=b.transAxes, fontsize=7, color='#6b4a8f')
    c = ax[2]
    c.plot(ts, q, 's-', color='#8a5a00', ms=3)
    c.set_ylabel('QNH (hPa)')
    d_ = ax[3]
    colors = ['#1f5fa8' if r == '36' else '#c0504d' for r in rwy]
    d_.bar(ts, [1] * len(ts), width=1 / 48, color=colors, align='edge')
    d_.set_yticks([])
    d_.set_ylabel('RWY', rotation=0, labelpad=14)
    d_.set_title('inferred direction: blue = 36 (north flow), red = 18 (south flow); rule metar_zsss.RunwayDirection',
                 fontsize=7.5, loc='left')
    d_.xaxis.set_major_formatter(mdates.DateFormatter('%d %H:%MZ'))
    d_.set_xlabel('UTC (local time = UTC+8)', fontsize=8)
    for x in ax:
        x.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_flow(fs_iem, path):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    by_m = collections.defaultdict(lambda: [0, 0])
    by_h = collections.defaultdict(lambda: [0, 0])
    for t, r, why, d in fs_iem:
        loc = t + dt.timedelta(hours=8)
        by_m[loc.month][0] += 1; by_m[loc.month][1] += r == '36'
        by_h[loc.hour][0] += 1; by_h[loc.hour][1] += r == '36'
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ms = list(range(1, 13))
    ax[0].bar(ms, [100 * by_m[m][1] / max(1, by_m[m][0]) for m in ms], color='#1f5fa8', label='RWY 36 (north flow)')
    ax[0].bar(ms, [100 - 100 * by_m[m][1] / max(1, by_m[m][0]) for m in ms],
              bottom=[100 * by_m[m][1] / max(1, by_m[m][0]) for m in ms], color='#c0504d', label='RWY 18 (south flow)')
    ax[0].set_xticks(ms)
    ax[0].set_xticklabels(['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'])
    ax[0].set_ylabel('% of routine METARs')
    ax[0].set_title('Inferred runway direction by month, ZSSS METAR %d-%d (IEM) [inf]' %
                    (fs_iem[0][0].year, fs_iem[-1][0].year), fontsize=9)
    ax[0].legend(fontsize=7, loc='lower left')
    hs = list(range(24))
    ax[1].plot(hs, [100 * by_h[h][1] / max(1, by_h[h][0]) for h in hs], 'o-', color='#1f5fa8')
    ax[1].set_ylim(0, 100)
    ax[1].set_xticks(range(0, 24, 3))
    ax[1].set_xlabel('local hour (UTC+8)')
    ax[1].set_ylabel('% RWY 36')
    ax[1].set_title('... by local hour (all months)', fontsize=9)
    for a in ax:
        a.grid(alpha=0.25)
    fig.text(0.01, 0.01, 'Rule [inf]: keep the direction while tailwind <= 1.5 m/s; turn after 2 reports > 1.5 m/s or 1 > 4 m/s; '
             'calm/VRB keep; start 36; stepped on every METAR/SPECI. Calibrated on 169 reports whose RVR/WS groups name the runway (86.4 % agree).',
             fontsize=7, color='#444')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return ({m: round(100 * by_m[m][1] / max(1, by_m[m][0]), 1) for m in ms},
            {h: round(100 * by_h[h][1] / max(1, by_h[h][0]), 1) for h in hs})


def main():
    now = dt.datetime(2026, 11, 14, 6, 0, tzinfo=UTC)
    r24 = awc_reports([os.path.join(CACHE, 'awc_metar_zsss_24h.raw.txt')], now)
    # each 7-day query file is resolved against its own end time (file name), to place day numbers correctly
    r30 = []
    seen = set()
    for p in sorted(glob.glob(os.path.join(CACHE, 'awc_30d', '*.txt'))):
        end = dt.datetime.strptime(os.path.basename(p)[len('metar_raw_to_'):-4], '%Y%m%d_%H%M').replace(tzinfo=UTC)
        for t, d in awc_reports([p], end):
            if (t, d['raw']) not in seen:
                seen.add((t, d['raw'])); r30.append((t, d))
    r30.sort(key=lambda x: x[0])
    iem = iem_reports()
    stats = {'awc_24h': stream_stats(r24), 'awc_30d': stream_stats(r30), 'iem': stream_stats(iem)}
    # AWC vs IEM completeness over the AWC 30-day window
    t0, t1 = r30[0][0], r30[-1][0]
    iem_win = [(t, d) for t, d in iem if t0 <= t <= t1]
    stats['awc_vs_iem_same_window'] = {'window': [t0.isoformat(), t1.isoformat()],
                                       'awc_reports': len(r30), 'iem_reports': len(iem_win)}
    # runway direction, 24 h and climatology
    fs24 = flow_series(r24)
    stats['rule_24h'] = collections.Counter(r for _, r, _, _ in fs24)
    fs_iem = flow_series(iem)
    changes = sum(1 for a, b in zip(fs_iem, fs_iem[1:]) if a[1] != b[1])
    days = (fs_iem[-1][0] - fs_iem[0][0]).total_seconds() / 86400
    n36 = sum(1 for x in fs_iem if x[1] == '36')
    # sensitivity: start direction and thresholds
    sens = {}
    for keep, mx in ((1.0, 3.0), (1.5, 4.0), (2.0, 4.0), (3.0, 5.0)):
        M.RunwayDirection.TAIL_KEEP_MS, M.RunwayDirection.TAIL_MAX_MS = keep, mx
        f = flow_series(iem)
        sens['keep%.1f_max%.1f' % (keep, mx)] = {
            'pct_36': round(100 * sum(1 for x in f if x[1] == '36') / len(f), 1),
            'changes_per_day': round(sum(1 for a, b in zip(f, f[1:]) if a[1] != b[1]) / days, 2)}
    M.RunwayDirection.TAIL_KEEP_MS, M.RunwayDirection.TAIL_MAX_MS = 1.5, 4.0
    # raw wind statistics: share of reports where 36 has a headwind (>0), and where either direction exceeds 3 m/s tail
    h = [M.components(d.get('wind'), '36') for _, d in iem if d['type'] == 'METAR']
    hv = [c[0] for c in h if c is not None]
    stats['iem_wind'] = {
        'n_with_direction': len(hv), 'n_without_direction(VRB/calm)': len(h) - len(hv),
        'pct_headwind_on_36': round(100 * sum(1 for x in hv if x > 0) / len(hv), 1),
        'pct_abs_along_runway_gt3': round(100 * sum(1 for x in hv if abs(x) > 3) / len(hv), 1),
        'pct_abs_along_runway_gt5': round(100 * sum(1 for x in hv if abs(x) > 5) / len(hv), 1),
        'mean_speed_ms': round(sum(d['wind']['speed_ms'] for _, d in iem if d.get('wind', {}).get('speed_ms') is not None)
                               / sum(1 for _, d in iem if d.get('wind', {}).get('speed_ms') is not None), 2),
    }
    by_m, by_h = plot_flow(fs_iem, os.path.join(OUT, 'sources_sim_flow.png'))
    stats['rule_iem'] = {'pct_36': round(100 * n36 / len(fs_iem), 1), 'changes': changes, 'days': round(days, 1),
                         'changes_per_day': round(changes / days, 2), 'pct_36_by_local_month': by_m,
                         'pct_36_by_local_hour': by_h, 'sensitivity': sens}
    plot_24h(r24, os.path.join(OUT, 'sources_sim_metar24h.png'))
    stats['rule_24h'] = dict(stats['rule_24h'])
    stats['note'] = ('Measured by tools/wx/metar_stats.py on 2026-11-14 from the AWC Data API (24 h and 30 d) and the '
                     'IEM archive (2023-01-01 .. 2026-11-13). Runway direction values are [inf] (rule, not observed).')
    with open(os.path.join(OUT, 'sources_sim_wx_stats.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=1, default=str)
    print(json.dumps(stats, indent=1, default=str)[:6000])


if __name__ == '__main__':
    main()
