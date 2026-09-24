#!/usr/bin/env python3
"""KSFO weather climatology from 10 years of routine METARs (2016-2025), for docs/research/weather.md section 4.

Input: the Iowa Environmental Mesonet ASOS archive for station SFO (public domain; attribution appreciated,
https://mesonet.agron.iastate.edu/disclaimer.php).  Download once (about 10 MB) with --fetch; the file lands in
refs/cache/weather/ (gitignored).  Every report is decoded with tools/env/metar_decode.py.

Only routine reports are used for frequencies: KSFO routine METARs are issued at hh:56 (observed), so SPECIs
(any other minute) do not bias the counts.  IEM rows tagged IEM_GHCNH (synthesised from GHCN-hourly) are dropped.
Local time = America/Los_Angeles (PST/PDT as clocks show).

Usage:
  python3 tools/env/ksfo_climatology.py --fetch      # download refs/cache/weather/iem_ksfo_2016_2025_metar.csv
  python3 tools/env/ksfo_climatology.py              # print markdown tables (as pasted into weather.md)
  python3 tools/env/ksfo_climatology.py --json out.json
"""
import csv, json, os, statistics, sys, urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import metar_decode as M

SRC = os.path.join(ROOT, 'refs', 'cache', 'weather', 'iem_ksfo_2016_2025_metar.csv')
URL = ('https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=SFO&data=metar&year1=2016&month1=1&day1=1'
       '&year2=2026&month2=1&day2=1&tz=Etc%2FUTC&format=onlycomma&latlon=no&elev=no&missing=M&trace=T&direct=no'
       '&report_type=3&report_type=4')
LA = ZoneInfo('America/Los_Angeles')
MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def load():
    rows = []
    with open(SRC) as f:
        for r in csv.DictReader(f):
            if 'IEM_GHCNH' in r['metar']:
                continue
            t = datetime.strptime(r['valid'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
            rows.append((t, r['metar']))
    return rows


def pct(a, b):
    return 100.0 * a / b if b else float('nan')


def main():
    if '--fetch' in sys.argv:
        req = urllib.request.Request(URL, headers={'User-Agent': 'sfo3d-weather-research/0.1'})
        with urllib.request.urlopen(req, timeout=300) as f, open(SRC, 'wb') as o:
            o.write(f.read())
        print('wrote', SRC)
        return
    rows = load()
    routine = []
    for t, raw in rows:
        if t.minute != 56:
            continue
        d = M.decode_metar(raw, t)
        loc = t.astimezone(LA)
        routine.append((t, loc, d))
    n_all = len(rows)
    out = {'n_reports': n_all, 'n_routine': len(routine), 'first': routine[0][0].isoformat(), 'last': routine[-1][0].isoformat()}

    def cat(d):
        wx = {p for w in d.get('weather', []) if not w.get('vicinity') for p in w.get('phenomena', [])}
        desc = {w.get('descriptor') for w in d.get('weather', []) if not w.get('vicinity')}
        c = d.get('ceiling_ft')
        v = d.get('visibility', {}).get('sm')
        return {
            'cig_lt1000': c is not None and c < 1000,
            'cig_lt2500': c is not None and c < 2500,
            'cig_le3000': c is not None and c <= 3000,
            'vis_lt3': v is not None and v < 3,
            'vis_lt5': v is not None and v < 5,
            # below the charted visual-approach minimums 'SFO 2500'/5' (Quiet Bridge / Tipp Toe, d-TPP 2609):
            'below_2500_5': (c is not None and c < 2500) or (v is not None and v < 5),
            'fg': 'FG' in wx, 'br': 'BR' in wx, 'hz_fu': bool(wx & {'HZ', 'FU'}),
            'precip': bool(wx & {'RA', 'DZ', 'GR', 'GS', 'UP', 'SN', 'PL'}) or 'TS' in desc,
            'ts': 'TS' in desc or any(w.get('descriptor') == 'TS' for w in d.get('weather', [])),
            'fog_gap': 'fog_in_gap' in d['rmk'],
        }

    # ---------- monthly frequencies
    mon = defaultdict(Counter)
    for t, loc, d in routine:
        c = cat(d)
        mon[loc.month]['n'] += 1
        for k, v in c.items():
            mon[loc.month][k] += bool(v)
    out['monthly'] = {MON[m - 1]: {k: round(pct(v, mon[m]['n']), 1) for k, v in mon[m].items() if k != 'n'} | {'n': mon[m]['n']} for m in range(1, 13)}

    # ---------- month x local hour, below 2500 ft / 5 SM
    grid = defaultdict(lambda: [0, 0])
    for t, loc, d in routine:
        g = grid[(loc.month, loc.hour)]
        g[1] += 1
        g[0] += bool(cat(d)['below_2500_5'])
    out['below_2500_5_by_month_hour'] = {MON[m - 1]: [round(pct(*grid[(m, h)]), 0) for h in range(24)] for m in range(1, 13)}

    # ---------- summer low-ceiling heights and clearing time (Jun-Sep)
    heights = [d['ceiling_ft'] for t, loc, d in routine if loc.month in (6, 7, 8, 9) and d.get('ceiling_ft') is not None and d['ceiling_ft'] < 3000]
    q = statistics.quantiles(heights, n=10)
    out['summer_low_ceiling_ft'] = {'n': len(heights), 'p10': q[0], 'p50': statistics.median(heights), 'p90': q[-1]}
    byday = defaultdict(dict)
    for t, loc, d in routine:
        if loc.month in (6, 7, 8, 9):
            c = d.get('ceiling_ft')
            byday[loc.date()][loc.hour] = c is not None and c < 2500
    clear_hours = []
    stratus_days = 0
    for day, hrs in byday.items():
        if hrs.get(7):                                    # low ceiling at ~07:56 local
            stratus_days += 1
            for h in range(8, 20):
                if h in hrs and not hrs[h]:
                    clear_hours.append(h); break
            else:
                clear_hours.append(24)
    ch = sorted(clear_hours)
    out['summer_stratus_clearing'] = {'days': len(byday), 'days_low_at_0756': stratus_days,
                                      'clear_by_local_hour_p25_p50_p75': statistics.quantiles(ch, n=4) if ch else None,
                                      'never_cleared_by_1956': sum(1 for h in ch if h == 24)}
    onset = []
    for day, hrs in byday.items():
        if 14 in hrs and not hrs[14]:
            for h in range(15, 24):
                if hrs.get(h):
                    onset.append(h); break
    out['summer_evening_onset_local_hour'] = {'days_with_onset_after_1456': len(onset),
                                              'p25_p50_p75': statistics.quantiles(onset, n=4) if len(onset) > 3 else None}

    # ---------- wind
    wmon = defaultdict(Counter)
    spd_hour = defaultdict(list)
    for t, loc, d in routine:
        w = d.get('wind')
        if not w or w.get('speed_kt') is None:
            continue
        W = wmon[loc.month]
        W['n'] += 1
        if w['calm']:
            W['calm'] += 1
        elif w['dir_true_deg'] is None:
            W['vrb'] += 1
        else:
            dd = w['dir_true_deg']
            if 230 <= dd <= 320:
                W['w_230_320'] += 1
            elif 90 <= dd <= 220:
                W['se_s_090_220'] += 1
            else:
                W['other'] += 1
        if w.get('gust_kt'):
            W['gust'] += 1
        # Tailwind components on the West-Plan runways (28 arrivals, 01 departures).  SFO runway true headings from the
        # airport grid (js/geo.js, CLAUDE.md): 28 = 297.83, 01 = 27.83.  JO 7110.65 3-5-1 assigns the runway most nearly
        # aligned with the wind when it is 5 kt or more; a >= 5 kt tailwind on BOTH 28 and 01 is used here as the
        # weather proxy for a Southeast Plan (INFERRED proxy, not an FAA/SFO rule).
        if not w['calm'] and w['dir_true_deg'] is not None:
            import math
            dd = math.radians(w['dir_true_deg'])
            t28 = -w['speed_kt'] * math.cos(dd - math.radians(297.83))
            t01 = -w['speed_kt'] * math.cos(dd - math.radians(27.83))
            if t28 >= 5:
                W['tail28_ge5'] += 1
            if t01 >= 5:
                W['tail01_ge5'] += 1
            if t28 >= 5 and t01 >= 5:
                W['tail_both_ge5'] += 1
        if w['speed_kt'] >= 20:
            W['ge20kt'] += 1
        if loc.month in (6, 7, 8):
            spd_hour[loc.hour].append(w['speed_kt'])
    out['wind_monthly_pct'] = {MON[m - 1]: {k: round(pct(v, wmon[m]['n']), 1) for k, v in wmon[m].items() if k != 'n'} for m in range(1, 13)}
    out['summer_mean_speed_by_local_hour_kt'] = [round(statistics.mean(spd_hour[h]), 1) for h in range(24)]
    # ---------- FG events by month and hour
    fg_hour = Counter(loc.hour for t, loc, d in routine if cat(d)['fg'])
    out['fg_by_local_hour'] = [fg_hour[h] for h in range(24)]
    # ---------- RVR reporting runways, remark usage
    rv = Counter(); rm = Counter()
    for t, raw in rows:
        d = M.decode_metar(raw)
        for x in d.get('rvr', []):
            rv[x['runway']] += 1
        for k in ('fog_in_gap', 'fog_bank', 'cig_variable_ft', 'cig_second_location', 'tower_vis_sm', 'surface_vis_sm',
                  'vis_sector', 'vis_variable_sm', 'lower_toward', 'obscuration_layers', 'lightning'):
            if k in d['rmk']:
                rm[k] += 1
        if 'AUTO' in d['modifier']:
            rm['AUTO'] += 1
    out['rvr_runways'] = dict(rv)
    out['remark_counts_all_reports'] = dict(rm)
    if '--json' in sys.argv:
        with open(sys.argv[sys.argv.index('--json') + 1], 'w') as f:
            json.dump(out, f, indent=1, default=str)
    # ---------- markdown
    print(f"Reports: {n_all} (routine hh:56: {len(routine)}), {out['first'][:10]} .. {out['last'][:10]} UTC\n")
    print('| Month | n | CIG<1000 | CIG<2500 | CIG<=3000 | VIS<3 | below 2500/5 | FG | BR | HZ/FU | precip | TS |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for m in MON:
        x = out['monthly'][m]
        print(f"| {m} | {x['n']} | {x['cig_lt1000']} | {x['cig_lt2500']} | {x['cig_le3000']} | {x['vis_lt3']} | {x['below_2500_5']} | {x['fg']} | {x['br']} | {x['hz_fu']} | {x['precip']} | {x['ts']} |")
    print('\nBelow 2500 ft / 5 SM, % of routine METARs, by month (rows) and local clock hour of the :56 report (columns 00..23):\n')
    print('| Month | ' + ' | '.join(f'{h:02d}' for h in range(24)) + ' |')
    print('|---|' + '---|' * 24)
    for m in MON:
        print(f'| {m} | ' + ' | '.join(str(int(v)) for v in out['below_2500_5_by_month_hour'][m]) + ' |')
    print('\nSummer (Jun-Sep) ceilings below 3000 ft:', out['summer_low_ceiling_ft'])
    print('Summer stratus clearing:', out['summer_stratus_clearing'])
    print('Summer evening onset:', out['summer_evening_onset_local_hour'])
    print('\n| Month | W 230-320 | SE-S 090-220 | other | calm | VRB | gust | >=20 kt | tailwind>=5 kt on 28 / 01 / both |')
    print('|---|---|---|---|---|---|---|---|---|')
    for m in MON:
        x = out['wind_monthly_pct'][m]
        al = ' / '.join(str(x.get(k, 0)) for k in ('tail28_ge5', 'tail01_ge5', 'tail_both_ge5'))
        print(f"| {m} | {x.get('w_230_320', 0)} | {x.get('se_s_090_220', 0)} | {x.get('other', 0)} | {x.get('calm', 0)} | {x.get('vrb', 0)} | {x.get('gust', 0)} | {x.get('ge20kt', 0)} | {al} |")
    tot = Counter()
    for m in range(1, 13):
        tot.update(wmon[m])
    out['wind_annual_pct'] = {k: round(pct(v, tot['n']), 1) for k, v in tot.items() if k != 'n'}
    print('Annual:', out['wind_annual_pct'])
    print('\nJun-Aug mean wind speed (kt) by local hour 00..23:', out['summer_mean_speed_by_local_hour_kt'])
    print('FG reports by local hour 00..23:', out['fg_by_local_hour'])
    print('RVR runways:', out['rvr_runways'])
    print('Remark counts (all reports incl. SPECI):', out['remark_counts_all_reports'])


if __name__ == '__main__':
    main()
