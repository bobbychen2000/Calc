# Trim the Full build's replay pack to start `off` seconds later. The pack is delta-encoded: each event's d rows are
# [hex, changed fields, removed fields?] and identity fields (flight, t = ICAO type, r, ...) are sent only once, when an
# aircraft first appears. So the first kept event is rewritten with every aircraft's full accumulated state.
import copy, gzip, json, sys
src, outdir = sys.argv[1], sys.argv[2]; offs = sorted(int(x) for x in sys.argv[3].split(','))
p = json.load(gzip.open(src)); F = p['from']; ev = p['events']
state = {}; i = 0
for o in offs:
    while i < len(ev) and ev[i]['T'] < F + o:
        for row in ev[i]['p']['d']:
            s = state.setdefault(row[0], {}); s.update(row[1])
            for k in (row[2] if len(row) > 2 else []): s.pop(k, None)
        i += 1
    first = copy.deepcopy(ev[i]); rows = []
    for row in first['p']['d']:
        s = dict(state.get(row[0], {})); s.update(row[1])
        for k in (row[2] if len(row) > 2 else []): s.pop(k, None)
        rows.append([row[0], s])
    first['p']['d'] = rows
    q = dict(p); q['events'] = [first] + ev[i + 1:]; q['from'] = first['T']
    with gzip.open(f'{outdir}/replay_{o}.gz', 'wt') as f: json.dump(q, f)
    print(o, len(q['events']), sum(1 for r in rows if 't' in r[1]), '/', len(rows), 'typed')
