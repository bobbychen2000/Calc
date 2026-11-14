"""Aggregates, chart and local per-flight table for observed_elsewhere.py (OD2 tier 2). Called by its __main__.

Committable output: docs/phase1/observed_elsewhere_stats.json, docs/phase1/observed_elsewhere.png (counts, shares,
error statistics only: no callsign, registration, address or track).
Local only: refs/cache/observed_elsewhere/sha_observed_<day>.json / .csv (per-flight identities and inferred times).
"""
import collections, csv, datetime as dt, json, os, statistics as st
import observed_elsewhere as oe

GOOD = ('far_end_match', 'track_consistent')
PLAN_MIX = {'A320 family': (45, 55), '737 family': (23, 37), 'wide-body': (14, 26), 'C919': (1, 5),
            'C909 (ARJ21)': (0, 2)}                     # PLAN §1 "Fleet" row (estimate, not a measurement)
REGIONS = [('Hefei/Nanjing cluster', 29.5, 33.5, 115.0, 120.6), ('Beijing / North China', 35.0, 42.6, 112.0, 120.5),
           ('Pearl River Delta', 21.5, 24.6, 112.0, 115.6), ("Xi'an / Guanzhong", 33.0, 36.6, 105.5, 111.5),
           ('Fujian-Zhejiang coast', 24.6, 29.5, 116.5, 122.6), ('Taiwan', 21.5, 25.6, 119.6, 122.6),
           ('Korea / Yellow Sea', 33.0, 45.0, 122.6, 132.0), ('Japan / East China Sea', 20.0, 33.0, 122.6, 150.0)]


def region(lat, lon):
    for nm, a, b, c, d in REGIONS:
        if a <= lat < b and c <= lon < d:
            return nm
    return 'other mainland China' if oe.mainland(lat, lon) else 'other'


def iso(t):
    return oe.utc(t).strftime('%Y-%m-%dT%H:%M:%SZ') if t else ''


def local_hour(t):
    return (oe.utc(t) + dt.timedelta(hours=8)).hour


def write_local(r):
    os.makedirs(oe.OUT_LOCAL, exist_ok=True)
    base = os.path.join(oe.OUT_LOCAL, f"sha_observed_{r['day']}")
    keep = ('uid', 'cs', 'airline', 'operator', 'icao', 'r', 'r_src', 't', 't_src', 'desc', 'role', 'far', 'route_db',
            'consistency', 'wiki_pair', 'first', 'last', 'segs', 'obs_far', 'est', 'pick', 't_sha', 'sigma_s', 'alt_max')
    recs = [{k: m.get(k) for k in keep} for m in sorted(r['moves'], key=lambda m: m['t_sha'] or m['t_obs'])]
    for x in recs:
        x['src'] = {'identity': 'obs (callsign/address broadcast; reg/type from readsb db or Mictronics)',
                    'far_segment': 'obs', 'route': 'VRS standing data (crowd-sourced)', 'sha_time': 'inf'}
    with open(base + '.json', 'w') as f:
        json.dump({'day': r['day'], 'window_utc': [iso(r['window'][0]), iso(r['window'][1])], 'n': len(recs),
                   'licence': 'derived from adsb.lol globe_history (ODbL 1.0), VRS standing data (CC0), Mictronics '
                              '(ODC-By 1.0); LOCAL ONLY per PLAN 6b (per-flight data observed elsewhere)',
                   'movements': recs}, f, separators=(',', ':'))
    cols = ['day', 'callsign', 'airline', 'operator', 'icao24', 'registration', 'reg_src', 'type', 'type_src', 'role_at_ZSSS',
            'far_end_db', 'route_db', 'db_check', 'wiki_pair', 'first_fix_utc', 'first_lat', 'first_lon', 'first_alt_ft',
            'last_fix_utc', 'last_lat', 'last_lon', 'last_alt_ft', 'n_segments', 'far_end_event', 'far_end_event_utc',
            'sha_time_utc_inf', 'sha_time_local_inf', 'method', 'sigma_min', 'nearest_fix_region']
    with open(base + '.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(cols)
        for m in sorted(r['moves'], key=lambda m: m['t_sha'] or m['t_obs']):
            fe = m['obs_far']; near = m['last'] if m['role'] == 'arr' else m['first']
            w.writerow([r['day'], m['cs'], m['airline'], m.get('operator'), m['icao'], m['r'], m.get('r_src'), m['t'],
                        m.get('t_src'), m['role'], m['far'], m['route_db'], m['consistency'], m['wiki_pair'],
                        iso(m['first'][0]), m['first'][1], m['first'][2], m['first'][3], iso(m['last'][0]), m['last'][1],
                        m['last'][2], m['last'][3], m['nseg'], f"{fe['ap']} ({fe['how']})" if fe else '',
                        iso(fe['t']) if fe else '', iso(m['t_sha']),
                        (oe.utc(m['t_sha']) + dt.timedelta(hours=8)).strftime('%H:%M') if m['t_sha'] else '',
                        m['pick'] or '', round(m['sigma_s'] / 60, 1) if m['sigma_s'] else '', region(near[1], near[2])])
    return base


def day_stats(r, vrs_sha_by_al, far_db):
    M = r['moves']; G = [m for m in M if m['consistency'] in GOOD]
    c = collections.Counter(m['consistency'] for m in M)
    hours = {h: {'arr': 0, 'dep': 0} for h in range(24)}
    for m in G:
        if m['t_sha']:
            hours[local_hour(m['t_sha'])][m['role']] += 1
    al = collections.Counter(m['airline'] for m in G)
    al_cs = collections.defaultdict(set)
    for m in G:
        al_cs[m['airline']].add(m['cs'])
    fam = collections.Counter(oe.family(m['t']) for m in G); typ = collections.Counter(m['t'] or 'unknown' for m in G)
    far = collections.Counter(m['far'] for m in G)
    far_obs = collections.Counter(m['far'] for m in G if m['obs_far'])
    near = [(m['last'] if m['role'] == 'arr' else m['first']) for m in G]
    rnear = [oe.gc_km(p[1], p[2], *oe.ZSSS) for p in near]
    reg = collections.Counter(region(p[1], p[2]) for p in near)
    sig = [m['sigma_s'] / 60 for m in G if m['sigma_s']]
    meth = collections.Counter(m['pick'] or 'none' for m in G)
    wiki = collections.Counter(m['wiki_pair'] for m in G)
    inv = collections.Counter(x['db'] for x in r['inv'])
    inv_nodb_al = collections.Counter(x['airline'] for x in r['inv'] if x['db'] == 'not_in_db')
    # DB-free SHA/PVG discriminator: arrival altitude at the Nanjing edge of coverage
    def edge(ms):
        v = []
        for m in ms:
            if m['role'] != 'arr' or m['consistency'] not in GOOD:
                continue
            p = m['last']
            if 118.6 <= p[2] <= 119.7 and 31.0 <= p[1] <= 32.6 and isinstance(p[3], (int, float)):
                v.append(p[3])
        return v
    es, ep = edge(M), edge(r['pvg'])
    band = lambda v: sum(25900 <= x <= 27300 for x in v)
    return {
        'day': r['day'], 'window_utc': [iso(r['window'][0]), iso(r['window'][1])],
        'archive_days': r['meta'], 'flights_in_box_both_days': r['nflights'],
        'identified_total': len(M), 'by_db_check': dict(c), 'consistent': len(G),
        'consistent_by_role': dict(collections.Counter(m['role'] for m in G)),
        'consistent_share_of_783': round(len(G) / oe.MOVES_PER_DAY, 3), 'consistent_share_of_802': round(len(G) / 802, 3),
        'with_inferred_time': sum(1 for m in G if m['t_sha']), 'distinct_aircraft': len({m['icao'] for m in G}),
        'by_local_hour': hours, 'by_airline': dict(al.most_common()),
        'distinct_callsigns_by_airline': {k: len(v) for k, v in sorted(al_cs.items(), key=lambda x: -len(x[1]))},
        'db_sha_callsigns_by_airline': {k: vrs_sha_by_al.get(k, 0) for k in al},
        'by_family': dict(fam.most_common()), 'by_type': dict(typ.most_common()),
        'type_from': dict(collections.Counter(m.get('t_src') for m in G)),
        'by_far_end_top25': dict(far.most_common(25)),
        'far_end_coverage': {k: [far.get(k, 0), v] for k, v in sorted(far_db.items(), key=lambda x: -x[1]) if v >= 4}, 'far_end_event_observed': len([m for m in G if m['obs_far']]),
        'far_end_event_observed_by_airport_top15': dict(far_obs.most_common(15)),
        'nearest_fix_region': dict(reg.most_common()),
        'nearest_fix_km_q10_q25_q50_q75_q90': [round(oe.q(rnear, p)) for p in (.1, .25, .5, .75, .9)],
        'sigma_min_q10_q25_q50_q75_q90': [round(oe.q(sig, p), 1) for p in (.1, .25, .5, .75, .9)],
        'sigma_le_5_10_20_min': [round(sum(x <= k for x in sig) / len(sig), 3) for k in (5, 10, 20)],
        'method': dict(meth), 'wiki_pair_observed': dict(wiki),
        'pvg_identified_consistent': sum(1 for m in r['pvg'] if m['consistency'] in GOOD),
        'rotation': {'pairs': r['rot']['pairs'], 'sha_turn_min_q10_q50_q90':
                     [oe.q(r['rot']['sha_turn_min'], p) for p in (.1, .5, .9)], 'n_mixed': len(r['rot']['mixed_examples'])},
        'edge_altitude_nanjing': {'sha_arr_n': len(es), 'pvg_arr_n': len(ep),
                                  'sha_alt_q10_q50_q90': [round(oe.q(es, p)) for p in (.1, .5, .9)] if es else None,
                                  'pvg_alt_q10_q50_q90': [round(oe.q(ep, p)) for p in (.1, .5, .9)] if ep else None,
                                  'in_band_25900_27300ft': {'sha': band(es), 'pvg': band(ep)}},
        'inverse_unexplained_db_end_top10': dict(collections.Counter(
            (x['route_db'].split('-')[-1] if x['end'] == 'arr' else x['route_db'].split('-')[0])
            for x in r['inv'] if x['db'] == 'db_other_unexplained').most_common(10)),
        'inverse': {'rule': f'coverage ends (begins) airborne within 60-{oe.INV_R:.0f} km of ZSSS, track within '
                            f'{oe.INV_DEG:.0f} deg of the bearing to (from) ZSSS, no landing (take-off) seen',
                    'n': len(r['inv']), 'by_db': dict(inv), 'not_in_db_by_airline_prefix': dict(inv_nodb_al)},
        'registry': r['reg'],
        'calibration': {'flights_both_ends': len(r['cal']), 'cn_domestic_both_ends': r['n_cal_cn'],
                        'samples': r['samples'], 'samples_cn': r['samples_cn'],
                        'air_time_fit_all': {'a_s': round(r['air'][0]), 'b_s_per_km': round(r['air'][1], 3),
                                             'sigma_s': r['air'][2]},
                        'air_time_fit_cn': {'a_s': round(r['air_cn'][0]), 'b_s_per_km': round(r['air_cn'][1], 3),
                                            'sigma_s': r['air_cn'][2]}},
        'validation': val_stats(r['val']),
    }


def val_stats(V):
    out = {'M1_hkg_tpe_air_time': oe.errstats(V['M1_hkg_tpe']), 'M1_cn_leave_one_route_out': oe.errstats(V['M1_cn_loro'])}
    for k in ('M2_arr_hkg_tpe', 'M2_dep_hkg_tpe', 'M2_arr_cn_loao', 'M2_dep_cn_loao', 'M2_arr_other_loao', 'M2_dep_other_loao'):
        out[k] = {f'{oe.RBINS[i][0]}-{oe.RBINS[i][1]} km': oe.errstats(v) for i, v in sorted(V[k].items())}
    return out


def chart(stats, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
    SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK2,
                         'ytick.color': INK2, 'text.color': INK, 'axes.titlesize': 10, 'axes.titleweight': 'bold'})
    days = stats['days']; nd = len(days)
    fig, ax = plt.subplots(2, 2, figsize=(13, 9), facecolor=SURF)
    for a in ax.flat:
        a.set_facecolor(SURF); a.grid(True, color=GRID, lw=0.6); a.set_axisbelow(True)
        for s in ('top', 'right'): a.spines[s].set_visible(False)
    # (a) per local hour, mean of the days
    a = ax[0, 0]; hrs = list(range(24))
    arr = [st.mean(d['by_local_hour'][h]['arr'] for d in days) for h in hrs]
    dep = [st.mean(d['by_local_hour'][h]['dep'] for d in days) for h in hrs]
    a.bar(hrs, arr, width=0.8, color=BLUE, label='arrivals (identified)', edgecolor=SURF, linewidth=1)
    a.bar(hrs, dep, width=0.8, bottom=arr, color=ORANGE, label='departures (identified)', edgecolor=SURF, linewidth=1)
    a.hlines(oe.MEAN_06_24, 5.6, 23.4, colors=INK2, linestyles='--', lw=1.2)
    a.text(23.4, oe.MEAN_06_24 + 0.8, f'all SHA movements, mean 06-24 h: {oe.MEAN_06_24}/h [inf]', ha='right',
           va='bottom', color=INK2, fontsize=8)
    a.set_ylim(0, 52)
    a.set_xticks(range(0, 24, 2)); a.set_xlim(-0.6, 23.6)
    a.set_xlabel('local hour at SHA (UTC+8) of the inferred landing / take-off')
    a.set_ylabel('movements per hour (mean of %d days)' % nd)
    a.set_title('A  Identified SHA movements per hour')
    a.legend(frameon=False, loc='upper left', bbox_to_anchor=(0.0, 0.84), fontsize=8)
    # (b) by airline
    a = ax[0, 1]
    tot = collections.Counter()
    for d in days:
        for k, v in d['by_airline'].items(): tot[k] += v / nd
    top = tot.most_common(12)[::-1]
    a.barh([k for k, _ in top], [v for _, v in top], color=BLUE, height=0.7)
    for i, (k, v) in enumerate(top):
        a.text(v + 2, i, f'{v:.0f}', va='center', color=INK2, fontsize=8)
    a.set_xlabel('identified movements per day (ICAO airline prefix, mean of %d days)' % nd)
    a.set_title('B  Identified SHA movements by airline')
    # (c) type mix observed vs PLAN estimate
    a = ax[1, 0]
    fams = list(PLAN_MIX)
    obs = []
    for f in fams:
        n = sum(d['by_family'].get(f, 0) for d in days); t = sum(d['consistent'] - d['by_family'].get('unknown', 0) for d in days)
        obs.append(100 * n / t if t else 0)
    y = list(range(len(fams)))[::-1]
    for yi, f in zip(y, fams):
        lo, hi = PLAN_MIX[f]
        a.plot([lo, hi], [yi, yi], color=INK2, lw=6, alpha=0.25, solid_capstyle='butt')
    a.plot([], [], color=INK2, lw=6, alpha=0.25, label='PLAN §1 estimate range [inf]')
    a.scatter(obs, y, s=60, color=ORANGE, zorder=3, edgecolor=SURF, linewidth=1.5, label='observed elsewhere [obs]')
    for yi, v in zip(y, obs):
        a.text(v, yi + 0.25, f'{v:.1f} %', ha='center', va='bottom', fontsize=8, color=INK)
    a.set_yticks(y); a.set_yticklabels(fams); a.set_xlim(0, 60); a.set_ylim(-0.7, len(fams) - 0.3)
    a.set_xlabel('share of identified movements with a known type (%)')
    a.set_title('C  Type mix: observed vs Phase 0 estimate')
    a.legend(frameon=False, loc='lower right', fontsize=8)
    # (d) timing validation: |error| median by distance from SHA end of the nearest fix
    a = ax[1, 1]
    V = days[-1]['validation']
    def series(key, val='abs_p50_min'):
        xs, ys = [], []
        for k, v in V[key].items():
            if v.get('n', 0) >= 15:
                lo, hi = [int(x) for x in k.split(' ')[0].split('-')]
                xs.append((lo + hi) / 2); ys.append(v[val])
        return xs, ys
    for key, col, lab, mk in (('M2_arr_cn_loao', BLUE, 'arrivals, China domestic (leave-one-airport-out)', 'o'),
                              ('M2_dep_cn_loao', ORANGE, 'departures, China domestic (leave-one-airport-out)', 's'),
                              ('M2_arr_hkg_tpe', AQUA, 'arrivals, HKG-TPE held out', '^')):
        xs, ys = series(key)
        a.plot(xs, ys, color=col, lw=2, marker=mk, ms=6, label=lab)
        xs9, ys9 = series(key, 'abs_p90_min')
        a.plot(xs9, ys9, color=col, lw=1, ls='--', marker=mk, ms=4, alpha=0.8)
    a.plot([], [], color=INK2, lw=1, ls='--', label='dashed: 90th percentile')
    a.set_xscale('log'); a.set_xticks([60, 100, 200, 400, 800, 1600, 3000]); a.set_xticklabels(['60', '100', '200', '400', '800', '1600', '3000'])
    a.set_xlabel('distance (km) from the inferred end to the nearest observed fix')
    a.set_ylabel('|predicted - actual| time, minutes (median solid)')
    a.set_title('D  Timing method M2: validated error vs gap length')
    a.legend(frameon=False, fontsize=7.5, loc='upper left')
    fig.suptitle('SHA (ZSSS) movements identified from open ADS-B seen outside the Shanghai coverage gap  '
                 f'({", ".join(d["day"] for d in days)}; adsb.lol globe_history, ODbL; routes VRS standing data, CC0)',
                 fontsize=10.5, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=130, facecolor=SURF)


def main(results):
    vrs = oe.jload(os.path.join(oe.CACHE, 'routes_vrs', 'vrs_index.json.gz'))
    sha_by_al = collections.Counter(al for cs, (al, rt) in vrs['routes'].items() if 'ZSSS' in rt.split('-'))
    pvg_by_al = collections.Counter(al for cs, (al, rt) in vrs['routes'].items() if 'ZSPD' in rt.split('-'))
    far_db = collections.Counter()                       # DB SHA callsigns per far-end airport (both directions)
    for cs, (al, rt) in vrs['routes'].items():
        aps = rt.split('-')
        if aps.count('ZSSS') == 1:
            i = aps.index('ZSSS')
            for j in (i - 1, i + 1):
                if 0 <= j < len(aps): far_db[aps[j]] += 1
    days = []
    for r in results:
        write_local(r)
        days.append(day_stats(r, sha_by_al, far_db))
    blame = os.path.join(oe.CACHE, 'routes_vrs', 'blame_age.json')
    stats = {
        'what': 'OD2 tier 2 "observed elsewhere": Hongqiao (ZSSS) movements identified from open ADS-B outside the '
                'Shanghai coverage gap. Aggregate counts only; per-flight data stays in refs/cache (local).',
        'made_by': 'tools/adsb/scan_callsigns.py + tools/adsb/observed_elsewhere.py',
        'inputs': {'adsb': 'adsb.lol globe_history prod releases (ODbL 1.0)', 'routes': f"VRS standing data {results[0]['vrs_commit']} (CC0 1.0)",
                   'registry': 'Mictronics aircraft-database 479e4d0 (ODC-By 1.0)',
                   'pair_check': 'Wikipedia SHA rev 1385154959, PVG rev 1385155113 destination lists (CC BY-SA 4.0)'},
        'denominator': {'movements_per_day': oe.MOVES_PER_DAY, 'source': 'CAAC Jan-Sep 2026 mean (PLAN §1)',
                        'winter_plan_per_day': 802, 'mean_06_24_per_hour_inf': oe.MEAN_06_24},
        'route_db': {'callsigns_total': len(vrs['routes']), 'sha_callsigns': sum(sha_by_al.values()),
                     'pvg_callsigns': sum(pvg_by_al.values()), 'sha_by_airline': dict(sha_by_al.most_common()),
                     'pair_check_vs_wikipedia': results[0]['pairs'],
                     'last_change_age': oe.jload(blame) if os.path.exists(blame) else None},
        'days': days,
        'attribution': 'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL; routes: '
                       'Virtual Radar Server standing data (CC0 1.0); aircraft data: Mictronics aircraft database (ODC-By 1.0)',
    }
    os.makedirs(oe.OUT_PUB, exist_ok=True)
    with open(os.path.join(oe.OUT_PUB, 'observed_elsewhere_stats.json'), 'w') as f:
        json.dump(stats, f, indent=1, ensure_ascii=False); f.write('\n')
    chart(stats, os.path.join(oe.OUT_PUB, 'observed_elsewhere.png'))
    for d in days:
        print(d['day'], 'identified', d['identified_total'], 'consistent', d['consistent'], d['consistent_by_role'],
              'share', d['consistent_share_of_783'], 'sigma q', d['sigma_min_q10_q25_q50_q75_q90'])
