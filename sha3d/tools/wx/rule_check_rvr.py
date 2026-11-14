"""Check runway-direction rules against the only observed hint of the runway in use in ZSSS METARs: the runway
designators of RVR groups (Rdd[LR]/....) and wind-shear groups (WS Rdd[LR]), which name the runway the report is made
for, normally the runway in use [inf: assumption about the observer's practice].

Every rule is stepped on every report (METAR and SPECI, as a live simulator would see them) of the IEM archive
2023-2026; at a report carrying a single-direction hint the rule's current direction is compared with the hint.

Usage: python3 -I tools/wx/rule_check_rvr.py <sha3d root>
Prints a table and stores it under "rule_check_rvr_ws" in docs/phase1/sources_sim_wx_stats.json.
"""
import collections, json, os, re, sys
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
sys.argv = sys.argv[:1] + [ROOT]
sys.path.insert(0, os.path.join(ROOT, 'tools', 'wx'))
import metar_zsss as M          # noqa: E402
import metar_stats as S         # noqa: E402


def hint(raw):
    dirs = set(m[:2] for m in re.findall(r' R(\d{2}[LR])/[PM]?\d{4}', raw)) | \
           set(m[:2] for m in re.findall(r'WS R(\d{2}[LR])', raw))
    if len(dirs) != 1:
        return None, None
    return dirs.pop(), ('RVR' if re.search(r' R\d{2}[LR]/', raw) else 'WS')


def hysteresis(keep, mx, start='36'):
    r = M.RunwayDirection(start)
    r.TAIL_KEEP_MS, r.TAIL_MAX_MS = keep, mx
    return lambda w, cur: r.step(w)[0]


def preferred(pdir, thr):
    other = '18' if pdir == '36' else '36'
    def f(w, cur):
        c = M.components(w, pdir)
        return (cur or pdir) if c is None else (other if -c[0] > thr else pdir)
    return f


def into_wind(dead=0.5):
    def f(w, cur):
        c = M.components(w, '36')
        if c is None or abs(c[0]) < dead:
            return cur or '36'
        return '36' if c[0] > 0 else '18'
    return f


def evaluate(reps, policy):
    cur, n = None, collections.Counter()
    per_day = collections.defaultdict(collections.Counter)
    for t, d in reps:
        cur = policy(d.get('wind'), cur)
        o, k = hint(d['raw'])
        if o:
            ok = o == cur
            n[k + (':agree' if ok else ':disagree')] += 1
            per_day[t.date()]['agree' if ok else 'disagree'] += 1
    tot = sum(n.values())
    agree = n['RVR:agree'] + n['WS:agree']
    return {'agree': agree, 'n': tot, 'pct': round(100 * agree / tot, 1), 'counts': dict(n),
            'days': len(per_day), 'days_all_agree': sum(1 for v in per_day.values() if not v['disagree'])}


def main():
    reps = S.iem_reports()
    hints = [hint(d['raw']) for _, d in reps]
    obs = collections.Counter(h[0] for h in hints if h[0])
    variants = [('chosen: tail > 1.5 m/s twice or > 4 once (metar_zsss default)', hysteresis(1.5, 4.0))]
    for keep, mx in ((0.5, 2.0), (1.0, 3.0), (1.5, 5.0), (2.0, 4.0), (2.5, 5.0), (3.0, 5.0)):
        variants.append(('tail > %.1f twice or > %.1f once' % (keep, mx), hysteresis(keep, mx)))
    variants += [('into the wind (|head| < 0.5 keeps)', into_wind()),
                 ('prefer 36 unless any tail wind', preferred('36', 0.0)),
                 ('prefer 18 unless any tail wind', preferred('18', 0.0)),
                 ('always 36', lambda w, cur: '36')]
    table = {name: evaluate(reps, p) for name, p in variants}
    res = {'method': 'rules stepped on every IEM report (METAR + SPECI) 2023-01-01..2026-11-13; compared at reports whose '
                     'RVR / WS groups name a single runway direction', 'hints_by_direction': dict(obs),
           'n_hints': sum(obs.values()), 'variants': table}
    p = os.path.join(ROOT, 'docs', 'phase1', 'sources_sim_wx_stats.json')
    st = json.load(open(p))
    st['rule_check_rvr_ws'] = res
    json.dump(st, open(p, 'w'), indent=1, default=str)
    print('hints', dict(obs))
    for name, r in table.items():
        print('%-62s %3d/%3d = %5.1f %%  days all-agree %d/%d  %s' % (name, r['agree'], r['n'], r['pct'],
                                                                     r['days_all_agree'], r['days'], r['counts']))


if __name__ == '__main__':
    main()
