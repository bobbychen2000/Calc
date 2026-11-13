"""List Sketchfab API v3 search results (JSON files) with licence, author, face count. Usage: python3 -I sketchfab_list.py f1.json [f2.json ...]"""
import json, sys, re
seen = set()
for f in sys.argv[1:]:
    d = json.load(open(f, encoding='utf-8'))
    for r in d.get('results', []):
        if r['uid'] in seen: continue
        seen.add(r['uid'])
        name = r.get('name', '')
        lic = (r.get('license') or {})
        print(f"{r['uid']}\t{lic.get('label') or lic.get('slug') or '-'}\t{r.get('faceCount')}\t{(r.get('user') or {}).get('username')}\t{r.get('publishedAt','')[:10]}\t{name[:70]}")
