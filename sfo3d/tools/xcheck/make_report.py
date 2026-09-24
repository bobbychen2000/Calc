"""Refresh the generated tables inside docs/research/stands_xcheck.md.

Every block <!--BEGIN:name--> ... <!--END:name--> in the report is replaced by the block of the same name from the
fragment files written by compare_stands.py, compare_runways.py and adsb_evidence.py (refs/cache/xcheck/tables_*.md).
Hand-written text outside the markers is left alone. Also refreshes <!--STAMP--> ... <!--/STAMP--> with the data
versions used (OSM database timestamp, X-Plane scenery id, NASR cycle, recording span of the ADS-B evidence).
Usage: python3 tools/xcheck/make_report.py
"""
import glob, json, os, re
import xcommon as X

DOC = os.path.join(X.ROOT, 'docs', 'research', 'stands_xcheck.md')
FR = os.path.join(X.ROOT, 'refs', 'cache', 'xcheck')


def main():
    blocks = {}
    for fn in sorted(glob.glob(os.path.join(FR, 'tables_*.md'))):
        t = open(fn).read()
        for m in re.finditer(r'<!--BEGIN:(\w+)-->.*?<!--END:\1-->', t, flags=re.S):
            blocks[m.group(1)] = m.group(0)
    doc = open(DOC).read()
    n = 0
    for k, v in blocks.items():
        pat = re.compile(r'<!--BEGIN:' + k + r'-->.*?<!--END:' + k + r'-->', flags=re.S)
        if pat.search(doc):
            doc = pat.sub(lambda _: v, doc); n += 1
    st = json.load(open(os.path.join(FR, 'stands_result.json')))
    rw = json.load(open(os.path.join(FR, 'runways_result.json')))
    ev = json.load(open(os.path.join(FR, 'adsb_evidence.json'))) if os.path.exists(os.path.join(FR, 'adsb_evidence.json')) else {}
    meta = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'osm', 'overpass_ksfo_latest.meta.json')))
    sid = re.sub(r'.*apt_(\d+).*', r'\1', st['xp_scenery'])
    stamp = (f"<!--STAMP-->OSM database {st['osm_base']} (Overpass {meta['endpoint']}, fetched {meta['utc']}); "
             f"X-Plane Gateway scenery pack {sid}; FAA NASR cycle {rw['nasr_eff']}; "
             f"AirNav 'FAA information effective {rw['airnav_eff']}'; ADS-B/SFO evidence: {len(ev.get('rows', []))} stands "
             f"({ev.get('flysfo', '?')})<!--/STAMP-->")
    doc = re.sub(r'<!--STAMP-->.*?<!--/STAMP-->', lambda _: stamp, doc, flags=re.S)
    open(DOC, 'w').write(doc)
    print('replaced', n, 'blocks of', len(blocks))


if __name__ == '__main__':
    main()
