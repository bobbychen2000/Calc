"""Persist the download cache (refs/cache, gitignored) into git, as far as licences and sizes allow.

Why: a recreated container loses everything gitignored (2026-11-04: five weeks of downloads, the September ADS-B
recordings and the workflow journals were lost). The owner asked for the cached data to be committed.

The repository is PUBLIC (github.com/bobbychen2000/Calc), so a file is committed only when we may redistribute it:
  commit   our own outputs (measurements, extracted tables), public-domain sources (USDA NAIP provenance, FAA, BTS),
           ODbL (OSM, adsb.lol -- attribution in refs/cache/README.md), GPL / CC0 / CC-BY(-SA) sources recorded as such
           in a SOURCES.json next to the file; at most MAX_MB per file (GitHub refuses > 100 MB; big blobs slow every
           clone of this shared repo).
  pack     adsb.lol recordings: a trimmed copy (aircraft within PACK_NM of SFO and at most PACK_FT, or on the ground;
           every field kept) in refs/cache/rec_pack/, committed; tools/cache/restore.sh puts it back into rec/.
  local    everything else stays on disk only and is listed in refs/MANIFEST.json with its size, SHA-256, licence
           class and source URL (when known), so it can be re-fetched and checked: rasters reproducible from public
           sources (NAIP: tools/cache/restore.sh), manufacturer documents, photos without an open licence, the user's
           Google screenshots, flysfo responses (no published terms), adsb.fi recordings (adsb.fi terms: personal,
           non-commercial use; not to be licensed on -- docs/research/realtime_feeds.md 3.2), access tokens.

SOURCES.json (optional, any directory under refs/cache): {"<file name or glob>": {"url": ..., "licence": ...}}.
A licence starting with one of OPEN_LICENCES makes an image / document committable.

usage: python3 tools/cache/sync.py            # trims new recordings, stages committable files (git add -f),
                                              # writes refs/MANIFEST.json; then commit as usual
       python3 tools/cache/sync.py --dry-run  # print the plan only
"""
import argparse, fnmatch, glob, gzip, hashlib, json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'refs', 'cache')
MAX_MB = 25
PACK_NM, PACK_FT = 25.0, 18000
OPEN_LICENCES = ('public domain', 'pd', 'cc0', 'cc-by', 'cc by', 'odbl', 'gpl', 'lgpl', 'mit', 'bsd', 'apache',
                 'cdla-permissive', 'us government work')
TEXT_EXT = {'.json', '.geojson', '.csv', '.tsv', '.txt', '.md', '.py', '.svg', '.xml', '.osm', '.yaml', '.yml', '.dat',
            '.log', '.npz'}

# (path glob relative to refs/cache, class, reason) -- first match wins
RULES = [
    ('naip/token.json', 'local', 'short-lived access token'),
    ('**/token*.json', 'local', 'access token'),
    ('rec/adsblol_*.jsonl.gz', 'pack', 'ODbL (adsb.lol); trimmed copy in rec_pack/'),
    ('rec/adsbfi_*', 'local', 'adsb.fi terms: personal non-commercial use, not to be licensed on'),
    ('rec/*', 'local', 'recorder state'),
    ('rec_pack/*', 'commit', 'ODbL (adsb.lol), trimmed'),
    ('naip/*.tif', 'local', 'USDA NAIP (public domain), large: rebuilt by tools/cache/restore.sh'),
    ('naip/*.npy', 'local', 'derived NAIP array, large'),
    ('naip/*', 'commit', 'USDA NAIP (public domain) provenance / derived'),
    ('sat_legacy/*', 'local', "the user's Google Maps screenshots: reference only, never redistributed"),
    ('gate_truth/*', 'local', 'flysfo.com responses: no published terms'),
    ('acap/*', 'local', 'manufacturer airport-planning documents (copyright)'),
    ('boeing/*', 'local', 'manufacturer documents (copyright)'),
    ('livref/*', 'local', 'livery reference photos (copyright)'),
    ('pbb/*', 'local', 'manufacturer datasheets (copyright)'),
    ('*/src/*', 'local?', 'fetched third-party page / document (copyright) unless SOURCES.json says open'),
    ('*/photos/*', 'local?', 'third-party photo (copyright) unless SOURCES.json says open'),
    ('*/pages/*', 'local?', 'fetched third-party page (copyright) unless SOURCES.json says open'),
    ('*.html', 'local?', 'fetched third-party page (copyright) unless SOURCES.json says open'),
    ('*.[Zz][Ii][Pp]', 'local', 'bulk archive, re-fetchable (extracts are committed)'),
    ('lighting/*', 'commit', 'FAA data (US government work)'),
    ('faa/*', 'commit', 'FAA data (US government work)'),
    ('bts/*', 'commit', 'US DOT BTS data (US government work)'),
    ('osm/*', 'commit', 'OpenStreetMap (ODbL)'),
    ('xplane/*', 'commit', 'X-Plane Scenery Gateway (GPL)'),
    ('stands/*', 'commit', 'our own outputs'),
    ('xcheck/*', 'commit', 'our own outputs'),
    ('replay*/*', 'commit', 'our own outputs'),
    ('engine/*', 'commit', 'our own outputs'),
    ('weather/*', 'commit', 'NOAA / aviationweather.gov (US government work)'),
    ('sun_night/*', 'commit', 'our own outputs'),
    ('feeds/*', 'commit', 'our own outputs'),
]
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.tif', '.tiff', '.pdf', '.heic', '.bmp'}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def sources_for(path):
    """SOURCES.json entries of the file's directory and its parents (nearest wins)."""
    d, name = os.path.dirname(path), os.path.basename(path)
    while d.startswith(CACHE):
        sp = os.path.join(d, 'SOURCES.json')
        if os.path.exists(sp):
            try:
                src = json.load(open(sp))
            except Exception:
                src = {}
            rel = os.path.relpath(path, d)
            for k, v in src.items():
                if fnmatch.fnmatch(rel, k) or fnmatch.fnmatch(name, k):
                    return v
        d = os.path.dirname(d)
    return None


def classify(rel, path):
    ext = os.path.splitext(rel)[1].lower()
    src = sources_for(path)
    lic = (src or {}).get('licence') or (src or {}).get('license') or ''
    for pat, cls, why in RULES:
        if fnmatch.fnmatch(rel, pat):
            if cls == 'local?':
                cls = 'commit' if lic and lic.lower().startswith(OPEN_LICENCES) else 'local'
                why = f'licence: {lic}' if cls == 'commit' else why
            break
    else:
        # unlisted directories: our own data/text outputs commit; images / documents only with an open licence
        if lic and lic.lower().startswith(OPEN_LICENCES):
            cls, why = 'commit', f'licence: {lic}'
        elif ext in IMAGE_EXT:
            cls, why = 'local', 'image / document without an open licence in SOURCES.json'
        elif ext in TEXT_EXT or os.path.basename(rel) == 'SOURCES.json':
            cls, why = 'commit', 'our own outputs / provenance (text)'
        else:
            cls, why = 'local', 'unclassified binary'
    if cls == 'commit' and os.path.getsize(path) > MAX_MB * 1e6:
        cls, why = 'local', f'{why}; larger than {MAX_MB} MB'
    return cls, why, src


def trim_pack(src, dst):
    """adsb.lol hour file -> trimmed copy (aircraft within PACK_NM / below PACK_FT or on the ground)."""
    import zlib
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
    raw = open(src, 'rb').read()
    lines, d = [], zlib.decompressobj(31)
    buf = b''
    pos = 0
    while pos < len(raw):      # concatenated gzip members (recorder restarts); a truncated tail is dropped
        try:
            buf += d.decompress(raw[pos:])
        except zlib.error:
            break
        if d.eof:
            pos = len(raw) - len(d.unused_data)
            d = zlib.decompressobj(31)
            if not raw[pos:]:
                break
        else:
            break
    tmp = dst + '.tmp'
    with gzip.open(tmp, 'wt', compresslevel=9) as out:
        for line in buf.decode('utf-8', 'replace').splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            ac = (r.get('d') or {}).get('ac')
            if isinstance(ac, list):
                keep = []
                for a in ac:
                    alt = a.get('alt_baro')
                    near = a.get('dst') is None or a['dst'] <= PACK_NM
                    low = alt == 'ground' or (isinstance(alt, (int, float)) and alt <= PACK_FT) or alt is None
                    if near and low:
                        keep.append(a)
                r['d']['ac'] = keep
                r['pack'] = f'trimmed: dst<={PACK_NM}nm, alt<={PACK_FT}ft or ground'
            out.write(json.dumps(r, separators=(',', ':')) + '\n')
    os.replace(tmp, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if not os.path.isdir(CACHE):
        print('no refs/cache'); return
    # 1. trim complete adsb.lol hours (not the hour being written) into rec_pack/
    pack_dir = os.path.join(CACHE, 'rec_pack')
    os.makedirs(pack_dir, exist_ok=True)
    hours = sorted(glob.glob(os.path.join(CACHE, 'rec', 'adsblol_*.jsonl.gz')))
    for p in hours[:-1]:       # the newest file is still being written by the recorder
        dst = os.path.join(pack_dir, os.path.basename(p))
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(p):
            if not a.dry_run:
                trim_pack(p, dst)
            print(f'pack {os.path.relpath(p, ROOT)} -> {os.path.relpath(dst, ROOT)}')
    # 2. workflow journals (results of finished agents; Workflow resumeFromRunId replays them) -> .wf/journals/
    jd = os.path.join(ROOT, '.wf', 'journals')
    for j in glob.glob('/root/.claude/projects/*/*/subagents/workflows/wf_*/journal.jsonl'):
        run = os.path.basename(os.path.dirname(j))
        dst = os.path.join(jd, run + '.jsonl')
        if not a.dry_run and (not os.path.exists(dst) or open(dst, 'rb').read() != open(j, 'rb').read()):
            os.makedirs(jd, exist_ok=True)
            open(dst, 'wb').write(open(j, 'rb').read())
    # 3. classify everything
    manifest, add = {}, []
    for dp, dn, fn in os.walk(CACHE):
        for f in fn:
            path = os.path.join(dp, f)
            rel = os.path.relpath(path, CACHE)
            if f.endswith('.tmp') or f.startswith('_'):
                continue
            cls, why, src = classify(rel, path)
            if cls == 'commit':
                add.append(path)
            else:
                manifest[rel] = {'class': cls, 'why': why, 'bytes': os.path.getsize(path), 'sha256': sha256(path),
                                 **({'url': src.get('url')} if src and src.get('url') else {})}
    # keep entries of files that are gone locally (they were seen once; the manifest is the record)
    mp = os.path.join(ROOT, 'refs', 'MANIFEST.json')
    old = json.load(open(mp)) if os.path.exists(mp) else {}
    for k, v in old.get('files', {}).items():
        if k not in manifest and not os.path.exists(os.path.join(CACHE, k)):
            manifest[k] = {**v, 'missing_locally': True}
    doc = {'about': 'Files under refs/cache that are NOT committed (licence or size), with their hashes. '
                    'Written by tools/cache/sync.py; restore what can be rebuilt with tools/cache/restore.sh.',
           'files': dict(sorted(manifest.items()))}
    print(f'commit {len(add)} files ({sum(os.path.getsize(p) for p in add) / 1e6:.1f} MB), '
          f'local {len(manifest)} ({sum(v["bytes"] for v in manifest.values()) / 1e6:.1f} MB)')
    if a.dry_run:
        for p in add:
            print('  +', os.path.relpath(p, ROOT))
        return
    json.dump(doc, open(mp, 'w'), indent=1)
    rels = [os.path.relpath(mp, ROOT), *[os.path.relpath(p, ROOT) for p in add]]
    for i in range(0, len(rels), 500):
        subprocess.run(['git', 'add', '-f', '--', *rels[i:i + 500]], cwd=ROOT, check=True)
    if os.path.isdir(os.path.join(ROOT, '.wf')):
        subprocess.run(['git', 'add', '-f', '--', '.wf'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
