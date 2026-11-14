# Independent re-derivation of B2's METAR statistics and the runway-direction rule check (IEM CSVs, public domain).
import csv, sys, os, re, math, collections, statistics
from datetime import datetime
d = sys.argv[1]
recs = []
for y in (2023, 2024, 2025, 2026):
    for r in csv.DictReader(open(os.path.join(d, f'zsss_metar_{y}.csv'))):
        t = datetime.strptime(r['valid'], '%Y-%m-%d %H:%M')
        recs.append((t, r['metar']))
recs.sort()
routine = [x for x in recs if x[0].minute in (0, 30)]
speci = [x for x in recs if x[0].minute not in (0, 30)]
days = (recs[-1][0] - recs[0][0]).total_seconds() / 86400
print('reports', len(recs), 'routine', len(routine), 'speci(off-minute)', len(speci), 'days', round(days, 2), 'routine/day', round(len(routine) / days, 2))
gaps = collections.Counter(int((b[0] - a[0]).total_seconds() / 60) for a, b in zip(routine, routine[1:]))
print('routine gaps', gaps.most_common(5))
tr = collections.Counter()
for t, m in recs:
    if ' NOSIG' in m: tr['NOSIG'] += 1
    elif ' BECMG' in m: tr['BECMG'] += 1
    elif ' TEMPO' in m: tr['TEMPO'] += 1
    else: tr['none'] += 1
n = len(recs); print('trend', {k: (v, round(100 * v / n, 1)) for k, v in tr.items()})
wind_units = collections.Counter(re.search(r'\b(?:\d{3}|VRB)\d{2,3}(?:G\d{2,3})?(MPS|KT)\b', m).group(1) if re.search(r'\b(?:\d{3}|VRB)\d{2,3}(?:G\d{2,3})?(MPS|KT)\b', m) else 'none' for t, m in recs)
print('wind units', wind_units)
q = [int(x) for t, m in recs for x in re.findall(r'\bQ(\d{4})\b', m)]; print('QNH', min(q), max(q), 'A-groups', sum(1 for t, m in recs if re.search(r'\bA\d{4}\b', m)))
cav = sum(1 for t, m in recs if 'CAVOK' in m); print('CAVOK share', round(100 * cav / n, 1))
# runway designators: RVR R18L/.... and WS R18L / WS RWY18L
HDG36 = 357.34
def wind(m):
    body = re.split(r'\s(?:NOSIG|BECMG|TEMPO|RMK)\b', m)[0]
    g = re.search(r'\b(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?MPS\b', body)
    if not g: return None
    if g.group(1) == 'VRB': return ('VRB', int(g.group(2)), None)
    return (int(g.group(1)), int(g.group(2)), int(g.group(3)) if g.group(3) else None)
hints = []
both = 0
for t, m in recs:
    body = re.split(r'\s(?:NOSIG|BECMG|TEMPO|RMK)\b', m)[0]
    des = set(re.findall(r'\bR(\d{2})[LRC]?/[PM]?\d{4}', body)) | set(re.findall(r'\bWS\s(?:R|RWY)(\d{2})[LRC]?\b', body))
    if not des: continue
    s = {'36' if x == '36' else '18' if x == '18' else x for x in des}
    if len(s) > 1: both += 1; continue
    hints.append((t, s.pop(), 'WS' if re.search(r'\bWS\s', body) else 'RVR'))
print('runway hints', len(hints), collections.Counter(h[1] for h in hints), collections.Counter(h[2] for h in hints), 'reports naming both directions', both, 'distinct days', len({h[0].date() for h in hints}))
# rule
def run_rule(T1, T2, recs):
    cur = '36'; cnt = 0; state = {}
    for t, m in recs:
        w = wind(m)
        if w and w[0] != 'VRB':
            sp = max(w[1], w[2] or 0)
            hw36 = sp * math.cos(math.radians(w[0] - HDG36))
            tail = -hw36 if cur == '36' else hw36
            # use gust for tail wind as B2 says "gusts included"
            if tail > T2: cur = '18' if cur == '36' else '36'; cnt = 0
            elif tail > T1:
                cnt += 1
                if cnt >= 2: cur = '18' if cur == '36' else '36'; cnt = 0
            else: cnt = 0
        state[t] = cur
    return state
hint_days = sorted({h[0].date() for h in hints})
res = {}
for T1, T2 in [(1.5, 4.0), (1.5, 5.0), (1.0, 3.0), (2.0, 4.0), (0.5, 2.0), (2.5, 5.0), (3.0, 5.0)]:
    st = run_rule(T1, T2, recs)
    ok = sum(1 for h in hints if st[h[0]] == h[1])
    north = sum(1 for t, m in routine if st[t] == '36') / len(routine)
    ch = sum(1 for a, b in zip(routine, routine[1:]) if st[a[0]] != st[b[0]]) / days
    res[(T1, T2)] = ok
    print(f'rule tail>{T1} twice or >{T2} once: agree {ok}/{len(hints)} = {100*ok/len(hints):.1f} %; north flow {100*north:.1f} %; changes/day {ch:.2f}')
# leave-one-day-out choice of threshold pair (selection on other days, scored on held-out day)
grid = [(a, b) for a in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0) for b in (2.0, 3.0, 4.0, 5.0, 6.0) if b > a]
states = {g: run_rule(*g, recs) for g in grid}
hit = 0
for dd in hint_days:
    train = [h for h in hints if h[0].date() != dd]; test = [h for h in hints if h[0].date() == dd]
    best = max(grid, key=lambda g: sum(states[g][h[0]] == h[1] for h in train))
    hit += sum(states[best][h[0]] == h[1] for h in test)
print('leave-one-day-out agreement', hit, '/', len(hints), f'= {100*hit/len(hints):.1f} %')
best_all = max(grid, key=lambda g: sum(states[g][h[0]] == h[1] for h in hints)); print('best grid pair in-sample', best_all, sum(states[best_all][h[0]] == h[1] for h in hints))
# day-level agreement: fraction of hint-days where all hints agree with the rule
st = states[(1.5, 4.0)]
dayok = collections.defaultdict(list)
for h in hints: dayok[h[0].date()].append(st[h[0]] == h[1])
print('days all agree', sum(all(v) for v in dayok.values()), 'of', len(dayok))
# parameter-free baseline: into the wind, |headwind| < 0.5 m/s keeps the current direction (gusts ignored)
cur = '36'; stb = {}
for t, m in recs:
    w = wind(m)
    if w and w[0] != 'VRB':
        hw36 = w[1] * math.cos(math.radians(w[0] - HDG36))
        if hw36 > 0.5: cur = '36'
        elif hw36 < -0.5: cur = '18'
    stb[t] = cur
okb = sum(1 for h in hints if stb[h[0]] == h[1]); print('into-the-wind baseline', okb, '/', len(hints), f'= {100*okb/len(hints):.1f} %')
# day-cluster bootstrap CI for the chosen rule minus baseline
import random
random.seed(1)
byday = collections.defaultdict(list)
for h in hints: byday[h[0].date()].append((st[h[0]] == h[1], stb[h[0]] == h[1]))
ds = list(byday); diffs = []; accs = []
for _ in range(2000):
    smp = [random.choice(ds) for _ in ds]
    a = [x for dd in smp for x in byday[dd]]
    accs.append(sum(x[0] for x in a) / len(a)); diffs.append((sum(x[0] for x in a) - sum(x[1] for x in a)) / len(a))
accs.sort(); diffs.sort()
print('chosen rule day-bootstrap 95% CI', round(100*accs[50],1), round(100*accs[1949],1), ' rule minus baseline 95% CI (pp)', round(100*diffs[50],1), round(100*diffs[1949],1))
