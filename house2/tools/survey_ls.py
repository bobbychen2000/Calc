"""Compact listing of a survey file:  python3 tools/survey_ls.py survey/front.json [type,type] [--full ID]"""
import json
import sys

d = json.load(open(sys.argv[1]))
if '--full' in sys.argv:
    want = sys.argv[sys.argv.index('--full') + 1]
    for e in d['elements']:
        if want in e['id']:
            print(json.dumps(e, indent=1))
    sys.exit()
types = sys.argv[2].split(',') if len(sys.argv) > 2 else None
print('OVERVIEW:', d.get('overview', ''))
print()
for e in d['elements']:
    if types and e.get('type') not in types:
        continue
    r = e.get('ref') or {}
    box = r.get('bbox') or (('poly%d' % len(r['poly'])) if r.get('poly') else '')
    xyz = e.get('xyz')
    print('%-34s %-11s %s | %s | size %s | conf %s%s%s' % (
        e['id'], e.get('type', ''), (e.get('on') or '')[:60], (e.get('desc') or '')[:150], e.get('size_est_m'),
        e.get('conf'), ' | ' + (r.get('image', '').split('/')[-1][:10]) + ' ' + str(box) if r else '',
        ' | xyz ' + str(xyz)[:140] if xyz else ''))
print()
for k in ('relations', 'open_questions'):
    print(k.upper())
    for r in d.get(k, []):
        print(' -', r if isinstance(r, str) else json.dumps(r))
