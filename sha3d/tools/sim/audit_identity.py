#!/usr/bin/env python3
r"""Exact-match identity audit (OD4; docs/phase3/design.md s.3, s.9.1 risk 1, review H4). LOCAL tool: it needs the gitignored
refs/cache/observed_elsewhere/ tables. It prints COUNTS, FILE PATHS AND LINE NUMBERS ONLY, never a matched value.
Exit 1 on any hit and on any forbidden path; exit 2 (no hit) when a file could not be read completely and needs a review by
eye ('REVIEW': an unknown binary or archive format, an encrypted member, a PDF stream filter it cannot decode; round 2, F12).

  python3 -I tools/sim/audit_identity.py --files F [F ...]     the given files (every carrier below)
  python3 -I tools/sim/audit_identity.py --staged              every staged file (its staged blob, git show :path) - the
                                                               lead's commit gate, run before every commit
  python3 -I tools/sim/audit_identity.py --diff [--path P]     tracked changes vs HEAD + untracked, not ignored files (default)
  python3 -I tools/sim/audit_identity.py --docs                every file under sha3d/docs/
  python3 -I tools/sim/audit_identity.py --selftest            planted real values in every carrier and form (temporary
                                                               files outside the repository, deleted; nothing printed)
  add --net                                                    also the broadened regex net (docs/**, jobs/**; reported)
  add --reviewed P [P ...]                                     paths whose 'REVIEW' flag the lead has cleared by eye for
                                                               this run (still scanned; a hit stays a hit)

Paths under refs/cache/ (verification fix round 1, F1): a path under */refs/cache/observed_elsewhere/** or any file named
sha_observed_<day>.json/.csv is FORBIDDEN (exit 1) in every mode, whatever its content, also as a member of an archive; a
refs/cache file whose nearest SOURCES.json does not mark it redistributable (true or a text starting with 'yes') is
FORBIDDEN too; the other refs/cache files (e.g. metar/awc_days) are scanned like any file.

Identity set: from every refs/cache/observed_elsewhere/sha_observed_*.json (cs, r, icao = the 24-bit address, t_sha, the
source uid and the overlay uid '<day>:<index>'), the derived IATA flight numbers (data/lookup.js AIRLINES), the CSV mirrors
and the owner sample, and every scan/cs_*.json.gz flight (cs, r, icao, derived flight number). Registrations of every format
(B-nnnn, B-nnnL, B-nnLL, B-nnLn, B-LLL, LLnnnn, VH-LLL, ...): those with a digit are kept squashed (B-nnnn -> Bnnnn), those
without a digit (B-LLL) in their own class (F2). Other per-flight times of the day tables (round 2, F13; class 'ftime'):
every est.*.t, the first / last / segment fix times, obs_far.t, and the plan's tier-2 block times t_sha + inS and
t_sha - outS of every side (data/sha_sim_inputs.json params.taxi), as epoch s (floor and round) and ms; a value on a whole
minute is left out of this class (it would equal the obsTime of public METAR reports; residual 1/60).
Path names (round 2, F12): every path (directories and base name, and every member name of an archive) is scanned like text.
Normalisation (round 2, F13) before matching: HTML entities, JSON / JS escapes (\uXXXX, \xXX), %XX, NFKC (full-width
forms, no-break spaces), every Unicode dash -> '-', every Unicode space -> ' ', zero-width characters and soft hyphens removed.
Matching (F3): the text is cut into maximal runs of [A-Za-z0-9]; windows of up to 3 consecutive runs joined by exactly one
of ' -_./' are squashed (separators removed, upper case) and compared with the squashed identity values, so 'B-nnnn',
'Bnnnn', 'B nnnn', 'B_nnnn', 'b.nnnn', 'CES nnnn', 'MU nnnn' all hit; two runs in neighbouring table or CSV cells
('| B | nnnn |', 'B,nnnn', tab; a registration only) join like ' ' (round 2, F13); a digit-free registration hits only as a window joined by '-'
(any case) or as one all-capitals run (ordinary words and identifiers such as 'd.name', 'b_name' never hit); a window
joined by ' ', '.', '/' or a cell boundary hits only in capitals, not before a decimal fraction, with >= 3 digits, and a
callsign of 3 digits ('CES nnn', round 2) not inside a list of counts ('CES nnn, CQH nn'); ' ', '.' and '/' never join two
digits (decimals, digit groups, dates); a 24-bit address hits as one 6-hex run (any case, also after '0x'; never after '#',
a colour; a digits-only one only when quoted, after '0x', after an address keyword such as 'icao' / 'hex' within 48
characters, or in the column of a table / CSV whose header names an address (round 2) - not a JSON number or a decimal
fraction); t_sha hits as a 10- or 13-digit run (epoch s / ms, also as a float) and as a date-time to the second or to the
minute in any of the forms ISO (any case, 'T' / ' '), compact ISO, 'D Mon YYYY', 'Mon D, YYYY', RFC 2822, 'YYYY/MM/DD',
'DD/MM/YYYY' (both readings), with the time after a space, 'T', 'at', or in the next table / CSV / JSON cell (round 2,
F13); with 'Z' / 'UTC' / 'GMT' / '+08:00' / 'UTC+8' / 'local' as written, without a zone read both as UTC and as UTC+8; the
other per-flight times hit as epoch s / ms runs and as date-times to the second. The source and the overlay uid hit as
written, also after a 'word:' prefix (the plan's 'oe:<uid>' and 'cont:<uid>:<n>' slots; round 2); a fingerprint (sha256 /
sha1 / md5 of a local identity file, any prefix of >= 12 hex characters; round 2, F20) as one run. Values that are ICAO
aircraft type designators or shorter than 4 characters are not in the set (they would hit every 'A321'); the type set
includes data/lookup.js TYPE_NAMES.
Carriers (F3, round 2 F12): UTF-8 text, UTF-16 / UTF-32 (BOM, or BOM-less UTF-16 by its NUL pattern), PNG text chunks,
JPEG metadata segments (APPn, COM), TIFF ASCII tags, glTF JSON chunks, gzip / bz2 / xz content, zip containers recursively
(every member and member name: zip, xlsx, docx, pptx, odt, ...; XML / HTML also with the tags removed, so text split
over Word runs or SVG tspans joins), tar archives, PDF (FlateDecode / ASCII85 / ASCIIHex
streams inflated, the text of every Tj / TJ show operator with its ToUnicode maps, object streams, metadata), base64 runs
inside text (decoded and scanned like a file). Any other binary is scanned as printable strings and flagged 'REVIEW'.
NOT covered: text rendered into image pixels (the app's harness asserts identity 'none' before every committable shot,
design s.3 / H5), values split over non-neighbouring cells or encrypted / unusual encodings.
Allow-list (F8): inside data/sha_sim_inputs.(json|js) section 'published' only, the flight numbers of the open-schedule rows
whose origin or destination is SHA (refs/cache/schedules_open/: the rows tools/sim/build_sim_inputs.py uses, with their
codeshares; published schedule facts, data/SOURCES_sim.json); a registration, callsign, address, uid or time there is
still a hit.
"""
import argparse, base64, bisect, bz2, csv, datetime as dt, glob, gzip, hashlib, html, io, json, lzma, math, os, re, struct, \
    subprocess, sys, tarfile, unicodedata, zipfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SHA3D = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(SHA3D)
OBS = os.path.join(SHA3D, 'refs', 'cache', 'observed_elsewhere')
PUB = os.path.join(SHA3D, 'refs', 'cache', 'schedules_open')
RUN = re.compile(r'[A-Za-z0-9]+')
SEPS = ' -_./'
CELL_GAP = re.compile(r'^(?:[ \t]*\|[ \t]*|[,;\t])$')       # neighbouring markdown-table / CSV / TSV cells (round 2, F13)
MAXRUNS = 3
# zones as written: Z / UTC / GMT, UTC+8 style, +08:00 / +0800 / +08, 'local' / 'LT' / 'CST' / 'Beijing' (UTC+8) (any other
# trailing offset, e.g. the '-09:00' of a range '08:00-09:00', is not a zone: the time is then read both as UTC and as UTC+8)
ZONE = (r'(?:[ \t]?(?P<z>Z(?![A-Za-z])|UTC[ \t]?\+[ \t]?0?8(?::?00)?(?!\d)|UTC|GMT|\+08(?::?00)?(?!\d)|\+00(?::?00)?(?!\d)'
        r'|local(?![A-Za-z])|LT(?![A-Za-z])|CST(?![A-Za-z])|Beijing))?')
MON = (r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?'
       r'|nov(?:ember)?|dec(?:ember)?)')
MONTHS = {m: i + 1 for i, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'))}
DATE = (r'(?:(?P<y>\d{4})(?P<ds>[-/.])(?P<mo>\d{1,2})(?P=ds)(?P<d>\d{1,2})'                       # 2026-11-12, 2026/11/12
        r'|(?P<d2>\d{1,2})(?:st|nd|rd|th)?[ -]?(?P<mon2>' + MON + r')\.?[ ,-]+(?P<y2>\d{4})'     # 12 Nov 2026, 12-Nov-2026
        r'|(?P<mon3>' + MON + r')\.?[ -](?P<d3>\d{1,2})(?:st|nd|rd|th)?,?[ \t]+(?P<y3>\d{4})'    # Nov 12, 2026
        r'|(?P<a4>\d{1,2})/(?P<b4>\d{1,2})/(?P<y4>\d{4}))')                                      # 12/11/2026 (both readings)
DT_SEP = (r'(?:[Tt_]|[ \t]*[,;|\t][ \t]*|[ \t]+(?:at[ \t]+|@[ \t]*)?'
          r'|"?[ \t]*,[ \t]*"?[A-Za-z_]{1,24}"?[ \t]*:[ \t]*"?)')                                  # ..."day":"D","time":"T"
TIME = r'(?P<h>\d{1,2}):(?P<mi>\d{2})(?::(?P<s>\d{2})(?:[.,]\d+)?)?(?![\d:])'
DTX = re.compile(r'(?<![\d/.-])' + DATE + DT_SEP + TIME + ZONE, re.I)
ISO_COMPACT = re.compile(r'(?<!\d)(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})T(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})?' + ZONE + r'(?!\d)', re.I)
UID = re.compile(r'(?<![\w.-])(?<!\d:)(\d{4}[.-]\d{2}[.-]\d{2}:\d+(?:#\d+)?)(?![\w#])(?!:\d)')
HEX6 = re.compile(r'^[0-9a-fA-F]{6}$')
NET = [re.compile(r'\bB-[0-9A-Z]{3,5}\b'), re.compile(r'\b(?:[A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])[0-9]{2,4}\b'),
       re.compile(r'\b[A-Z]{3}[0-9]{1,4}[A-Z]?\b')]
CLASSES = ('callsign', 'flight', 'registration', 'address', 't_sha', 'ftime', 'uid', 'fingerprint')
LOCAL_S = 8 * 3600
MAXDEPTH = 6                                       # archive / base64 nesting
MAXBYTES = 1 << 30                                 # decompressed bytes per file (zip bomb guard -> REVIEW)
REVIEWED = {}                                      # {repo-relative path: sha256 of the reviewed bytes}: cleared by the lead


def type_designators():
    s = set()
    for p in ('js/aircraft/types.js', 'js/aircraft/fit.js'):
        try:
            txt = open(os.path.join(SHA3D, p), encoding='utf-8').read()
        except OSError:
            continue
        s |= set(re.findall(r'\b([A-Z][A-Z0-9]{1,3})\s*:', txt))
    try:                                             # every ICAO type designator of data/lookup.js TYPE_NAMES (2,855)
        txt = open(os.path.join(SHA3D, 'data', 'lookup.js'), encoding='utf-8').read()
        s |= set(json.loads(re.search(r'export const TYPE_NAMES = (\{.*?\});', txt, re.S).group(1)))
    except Exception:
        pass
    s |= {'C919', 'C909', 'AJ27', 'ARJ21', 'A320', 'A321', 'A330', 'A350', 'B737', 'B787', 'B777', 'A380'}
    return s


def airlines():
    try:
        txt = open(os.path.join(SHA3D, 'data', 'lookup.js'), encoding='utf-8').read()
        return json.loads(re.search(r'export const AIRLINES = (\{.*?\});', txt, re.S).group(1))
    except Exception:
        return {}


def flight_of(cs, AL):
    m = re.match(r'^([A-Z]{3})(\d{1,4}[A-Z]?)$', (cs or '').strip().upper())
    if not m:
        return []
    v = AL.get(m.group(1))
    if not v or '|' not in v:
        return []
    iata = v.split('|')[1].strip()
    if not re.match(r'^[A-Z0-9]{2}$', iata):
        return []
    n = m.group(2)
    return sorted({iata + n, iata + (n.lstrip('0') or '0')})


def squash(s):
    return re.sub(r'[^A-Z0-9]', '', s.upper())


class IdSet:
    def __init__(self):
        self.v = {c: set() for c in CLASSES}        # squashed upper values (address: lower 6-hex; t_sha / ftime: str s / ms; uid: as is)
        self.reg_alpha = set()                      # digit-free registrations, squashed (B-LLL -> BLLL)
        self.t_sec = set()                          # t_sha epoch s (int)
        self.t_min = set()                          # t_sha epoch minute (s // 60)
        self.t2_sec = set()                         # other per-flight times, epoch s (int; whole minutes left out)
        self.raw = {'registration': set(), 'reg_alpha': set(), 'callsign': set(), 'flight': set()}   # for --selftest only
        self.types = type_designators()
        self.files = 0
        self.taxi = []

    def add_time2(self, val):
        """another per-flight time (round 2, F13): epoch s (floor and round) and ms; a whole minute is left out"""
        try:
            t = float(val)
        except (TypeError, ValueError):
            return
        if not (1.5e9 < t < 2.2e9):
            return
        for x in {math.floor(t), int(round(t))}:
            if x % 60 and str(x) not in self.v['t_sha']:
                self.t2_sec.add(x)
                self.v['ftime'].update({str(x), str(x * 1000)})
        ms = int(round(t * 1000))
        if ms % 60000:
            self.v['ftime'].add(str(ms))

    def add(self, cls, val):
        if val is None:
            return
        val = str(val).strip()
        if not val:
            return
        if cls == 't_sha':
            try:
                t = int(round(float(val)))
            except ValueError:
                return
            self.v[cls].update({str(t), str(t * 1000)})
            self.t_sec.add(t)
            self.t_min.add(t // 60)
            return
        if cls == 'address':
            a = val.lower()
            a = a[2:] if a.startswith('0x') else a
            if HEX6.match(a):
                self.v[cls].add(a)
            return
        if cls == 'uid':
            self.v[cls].add(val)
            return
        u = val.upper()
        sq = squash(u)
        if len(sq) < 4 or u in self.types or sq in self.types or not re.search(r'[A-Z]', sq):
            return
        if not re.search(r'\d', sq):                 # B-LLL, VH-LLL ...: registrations only (F2)
            if cls == 'registration':
                self.reg_alpha.add(sq)
                self.raw['reg_alpha'].add(u)
            return
        self.v[cls].add(sq)
        self.raw[cls].add(u)

    def finish(self):
        """t_sha wins over ftime for the same value (a time is counted once, in the stronger class)"""
        self.t2_sec -= self.t_sec
        self.v['ftime'] -= self.v['t_sha']

    def total(self):
        return sum(len(s) for k, s in self.v.items() if k != 'fingerprint') + len(self.reg_alpha)

    def counts(self):
        c = {k: len(s) for k, s in self.v.items()}
        c['registration'] += len(self.reg_alpha)
        c['fingerprint'] = f'{len(self.v["fingerprint"])} prefixes'
        return c


def taxi_offsets():
    """(inS, outS) of every side of data/sha_sim_inputs.json params.taxi: the plan's block time of an observed movement is
    t_sha + inS (arrival) or t_sha - outS (departure)"""
    try:
        P = json.load(open(os.path.join(SHA3D, 'data', 'sha_sim_inputs.json'), encoding='utf-8'))['params']['taxi']
        return sorted({(int(v['inS']), int(v['outS'])) for v in P.values() if isinstance(v, dict) and 'inS' in v})
    except (OSError, ValueError, KeyError, TypeError):
        return []


def fix_times(m):
    """the other per-flight times of a day-table record: est.*.t, first / last fix, every segment fix, obs_far.t"""
    out = []
    for v in (m.get('est') or {}).values():
        if isinstance(v, dict) and v.get('t') is not None:
            out.append(v['t'])
    for k in ('first', 'last'):
        f = m.get(k)
        if isinstance(f, list) and f and isinstance(f[0], (int, float)):
            out.append(f[0])
    for seg in m.get('segs') or []:
        for f in seg if isinstance(seg, list) else []:
            if isinstance(f, list) and f and isinstance(f[0], (int, float)):
                out.append(f[0])
    of = m.get('obs_far')
    if isinstance(of, dict) and of.get('t') is not None:
        out.append(of['t'])
    return out


def load_identities():
    I = IdSet()
    AL = airlines()
    I.taxi = taxi_offsets()
    if not os.path.isdir(OBS):
        sys.exit('no local refs/cache/observed_elsewhere: the audit needs the local identity set (it is a local tool)')
    for p in sorted(glob.glob(os.path.join(OBS, '*.json'))):
        if os.path.basename(p) == 'SOURCES.json':
            continue
        d = json.load(open(p, encoding='utf-8'))
        I.files += 1
        day = d.get('day') or (re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(p)) or [None, None])[1]
        for i, m in enumerate(d.get('movements') or []):
            I.add('callsign', m.get('cs'))
            for f in flight_of(m.get('cs'), AL):
                I.add('flight', f)
            I.add('registration', m.get('r'))
            I.add('address', m.get('icao'))
            I.add('t_sha', m.get('t_sha'))
            I.add('uid', m.get('uid'))                     # the source uid (archive tag : index)
            if day:
                I.add('uid', f'{day}:{i}')                 # the overlay uid (tools/sim/observed_overlay.py)
            for t in fix_times(m):                         # round 2, F13
                I.add_time2(t)
            if m.get('t_sha') is not None:
                t = int(round(float(m['t_sha'])))
                for inS, outS in I.taxi:
                    I.add_time2(t + inS)
                    I.add_time2(t - outS)
    for p in sorted(glob.glob(os.path.join(OBS, '*.csv'))):
        I.files += 1
        with open(p, encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                cs = row.get('callsign')
                I.add('callsign', cs)
                for fl in flight_of(cs, AL):
                    I.add('flight', fl)
                I.add('registration', row.get('registration'))
                I.add('address', row.get('icao24'))
                for m in DTX.finditer(row.get('sha_time_utc_inf') or ''):
                    if m.group('s') is not None:
                        I.add('t_sha', dt_epochs(m, utc_default=True)[0])
    for p in sorted(glob.glob(os.path.join(OBS, 'scan', '*.json.gz'))):
        I.files += 1
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            d = json.load(f)
        for fl in d.get('flights') or []:
            I.add('callsign', fl.get('cs'))
            for x in flight_of(fl.get('cs'), AL):
                I.add('flight', x)
            I.add('registration', fl.get('r'))
            I.add('address', fl.get('icao'))
    # fingerprints (round 2, F20): sha256 / sha1 / md5 of every local identity file, as hex prefixes of >= 12 characters
    # (a committed hash would confirm a byte-exact reconstruction of a local table)
    for p in sorted(glob.glob(os.path.join(OBS, '**', '*'), recursive=True)):
        if os.path.isfile(p):
            b = open(p, 'rb').read()
            for h in (hashlib.sha256(b).hexdigest(), hashlib.sha1(b).hexdigest(), hashlib.md5(b).hexdigest()):
                I.v['fingerprint'].update(h[:k] for k in range(12, len(h) + 1))
    I.finish()
    return I


def dt_epochs(m, utc_default=False):
    """a DTX / ISO_COMPACT match -> the epoch seconds it can mean: as written with a zone, else as UTC and as UTC+8 local
    (a numeric DD/MM/YYYY date in both readings)"""
    g = m.groupdict()
    h, mi = int(g['h']), int(g['mi'])
    s = int(g['s']) if g.get('s') is not None else 0
    dates = []
    if g.get('y'):
        dates.append((int(g['y']), int(g['mo']), int(g['d'])))
    elif g.get('y2'):
        dates.append((int(g['y2']), MONTHS[g['mon2'][:3].lower()], int(g['d2'])))
    elif g.get('y3'):
        dates.append((int(g['y3']), MONTHS[g['mon3'][:3].lower()], int(g['d3'])))
    elif g.get('y4'):
        a, b = int(g['a4']), int(g['b4'])
        dates += [(int(g['y4']), b, a), (int(g['y4']), a, b)]
    z = (g.get('z') or '').replace(' ', '').replace('\t', '').upper()
    out = []
    for y, mo, d in dates:
        try:
            naive = int(dt.datetime(y, mo, d, h, mi, s, tzinfo=dt.timezone.utc).timestamp())
        except ValueError:
            continue
        if z in ('Z', 'UTC', 'GMT') or z.startswith('+00'):
            out.append(naive)
        elif z:                                      # +08, +08:00, UTC+8, local, LT, CST, Beijing
            out.append(naive - LOCAL_S)
        else:
            out += [naive] if utc_default else [naive, naive - LOCAL_S]
    return out


def published_flights():
    """flight numbers (with codeshares) of the open-schedule rows whose origin / destination is SHA: the same filter as
    tools/sim/build_sim_inputs.py published_rows (F8)"""
    s = set()
    for p in glob.glob(os.path.join(PUB, 'hkia', 'hkia_*.json')):
        arrival = 'arrival-true' in os.path.basename(p)
        for blk in json.load(open(p, encoding='utf-8')):
            for r in blk.get('list') or []:
                ports = (r.get('origin') if arrival else r.get('destination')) or []
                if 'SHA' not in ports:
                    continue
                for f in r.get('flight') or []:
                    s.add(squash(f['no']))
    for p in glob.glob(os.path.join(PUB, 'tsa', 'tsa_*.json')):
        to_tsa = '_arr_' in os.path.basename(p)
        for r in json.load(open(p, encoding='utf-8')):
            if (r.get('UpAirportCode') if to_tsa else r.get('GoalAirportCode')) != 'SHA':
                continue
            s.add(squash(r.get('AirLineIATA', '') + r.get('AirLineNum', '')))
    return s


# ------------------------------------------------------------------------------------------------ refs/cache gate (F1)
def cache_status(path, staged=False):
    """None (not a refs/cache path) | 'identity-source' | 'not-redistributable' | 'redistributable' (scanned normally)"""
    p = path.replace(os.sep, '/')
    if re.search(r'(^|/)sha_observed_\d{4}-\d{2}-\d{2}\.(json|csv)$', p) or re.search(r'(^|/)refs/cache/observed_elsewhere(/|$)', p):
        return 'identity-source'
    m = re.search(r'^(.*?(?:^|/)refs/cache)/(.+)$', p)
    if not m:
        return None
    root, rest = m.group(1), m.group(2).split('/')
    if len(rest) < 2:                                # a file directly in refs/cache/: no SOURCES.json can cover it
        return 'not-redistributable'
    for k in range(len(rest) - 1, 0, -1):            # the nearest SOURCES.json from the file's folder up to refs/cache/<sub>/
        sp = '/'.join([root] + rest[:k] + ['SOURCES.json'])
        d = read_sources(sp, staged)
        if d is None:
            continue
        r = d.get('redistributable') if isinstance(d, dict) else None
        ok = r is True or (isinstance(r, str) and r.strip().lower().startswith('yes'))
        return 'redistributable' if ok else 'not-redistributable'
    return 'not-redistributable'


def read_sources(sp, staged):
    ap = sp if os.path.isabs(sp) else os.path.join(REPO, sp)
    try:
        if staged:
            b = read_staged(os.path.relpath(ap, REPO))
            if b:
                return json.loads(b.decode('utf-8'))
        with open(ap, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------------------------------------ text extraction
def png_text(b):
    out = []
    if not b.startswith(b'\x89PNG\r\n\x1a\n'):
        return None
    i = 8
    while i + 8 <= len(b):
        n, typ = struct.unpack('>I4s', b[i:i + 8])
        data = b[i + 8:i + 8 + n]
        i += 12 + n
        try:
            if typ == b'tEXt':
                out.append(data.replace(b'\x00', b' ').decode('latin-1'))
            elif typ == b'zTXt':
                k, rest = data.split(b'\x00', 1)
                out.append(k.decode('latin-1') + ' ' + zlib.decompress(rest[1:]).decode('latin-1'))
            elif typ == b'iTXt':
                k, rest = data.split(b'\x00', 1)
                flag, method = rest[0], rest[1]
                lang, rest = rest[2:].split(b'\x00', 1)
                tk, txt = rest.split(b'\x00', 1)
                txt = zlib.decompress(txt) if flag else txt
                out.append(' '.join(x.decode('utf-8', 'replace') for x in (k, lang, tk, txt)))
            elif typ == b'eXIf':
                out.append(strings(data))
        except Exception:
            out.append(strings(data))
        if typ == b'IEND':
            break
    return '\n'.join(out)


def strings(b, n=4):
    return '\n'.join(m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{%d,}' % n, b))


def jpeg_text(b):
    """strings of the JPEG metadata segments only (APPn: Exif / XMP / ICC, COM); the entropy-coded image data carries no text"""
    out, i = [], 2
    while i + 4 <= len(b) and b[i] == 0xFF:
        mk = b[i + 1]
        if mk in (0xD8, 0x01) or 0xD0 <= mk <= 0xD7:
            i += 2
            continue
        if mk == 0xD9:
            break
        n = struct.unpack('>H', b[i + 2:i + 4])[0]
        seg = b[i + 4:i + 2 + n]
        if 0xE0 <= mk <= 0xEF or mk == 0xFE:
            out.append(strings(seg))
        if mk == 0xDA:                               # start of scan: image data follows
            break
        i += 2 + n
    return '\n'.join(out)


def tiff_text(b):
    """the ASCII-type (2) tag values of every IFD of a classic TIFF (ImageDescription, GeoAsciiParams, GDAL metadata ...)"""
    try:
        bo = '<' if b[:2] == b'II' else '>'
        if struct.unpack(bo + 'H', b[2:4])[0] != 42:
            return None
        off, out, seen = struct.unpack(bo + 'I', b[4:8])[0], [], set()
        while off and off not in seen and off + 2 <= len(b):
            seen.add(off)
            n = struct.unpack(bo + 'H', b[off:off + 2])[0]
            for k in range(n):
                e = off + 2 + 12 * k
                tag, typ, cnt = struct.unpack(bo + 'HHI', b[e:e + 8])
                if typ == 2:
                    v = b[e + 8:e + 8 + cnt] if cnt <= 4 else b[struct.unpack(bo + 'I', b[e + 8:e + 12])[0]:][:cnt]
                    out.append(v.replace(b'\x00', b' ').decode('latin-1'))
            off = struct.unpack(bo + 'I', b[off + 2 + 12 * n:off + 6 + 12 * n])[0]
        return '\n'.join(out)
    except (struct.error, IndexError):
        return None


class Extract:
    """the text of one file and of everything inside it (round 2, F12): parts (texts), kinds, opaque (REVIEW reasons),
    forbidden (archive members named as an identity table)"""
    def __init__(self):
        self.parts, self.kinds, self.opaque, self.forbidden = [], [], [], 0
        self.budget = MAXBYTES

    def text(self):
        return '\n'.join(p for p in self.parts if p)

    def kind(self):
        k = []
        for x in self.kinds:
            if x not in k:
                k.append(x)
        return '+'.join(k[:4]) + ('+...' if len(k) > 4 else '')


IDENT_NAME = re.compile(r'(^|/)sha_observed_\d{4}-\d{2}-\d{2}\.(json|csv)$|(^|/)observed_elsewhere/')


def extract(name, b, X, depth=0):
    """append the text of the bytes b (named `name`) and of every member inside to X"""
    X.budget -= len(b)
    if X.budget < 0:
        X.opaque.append('more than 1 GiB decompressed')
        return
    if depth > MAXDEPTH:
        X.opaque.append(f'nested deeper than {MAXDEPTH}')
        return
    def member(mname, data):
        X.parts.append(mname)                        # member names are scanned like paths
        if IDENT_NAME.search(mname.replace('\\', '/')):
            X.forbidden += 1
        extract(mname, data, X, depth + 1)
    try:
        if b.startswith(b'\x89PNG\r\n\x1a\n'):
            X.kinds.append('png-text'); X.parts.append(png_text(b)); return
        if b[:2] == b'\x1f\x8b':
            X.kinds.append('gzip'); extract(name[:-3] if name.endswith('.gz') else name, gzip.decompress(b), X, depth + 1); return
        if b[:3] == b'BZh' and len(b) > 10 and b[4:10] == b'\x31\x41\x59\x26\x53\x59':
            X.kinds.append('bz2'); extract(name, bz2.decompress(b), X, depth + 1); return
        if b[:6] == b'\xfd7zXZ\x00':
            X.kinds.append('xz'); extract(name, lzma.decompress(b), X, depth + 1); return
        if b[:4] in (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'):
            X.kinds.append('zip')
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                for info in z.infolist():
                    if info.is_dir():
                        X.parts.append(info.filename)
                        continue
                    if info.flag_bits & 0x1:
                        X.parts.append(info.filename)
                        X.opaque.append('encrypted zip member')
                        continue
                    member(info.filename, z.read(info))
            return
        if len(b) > 262 and b[257:262] == b'ustar':
            X.kinds.append('tar')
            with tarfile.open(fileobj=io.BytesIO(b)) as t:
                for ti in t.getmembers():
                    if ti.isfile():
                        member(ti.name, t.extractfile(ti).read())
                    else:
                        X.parts.append(ti.name)
            return
        if b[:5] == b'%PDF-':
            X.kinds.append('pdf'); pdf_text(b, X, depth); return
        if b[:3] == b'\xff\xd8\xff':
            X.kinds.append('jpeg-metadata'); X.parts.append(jpeg_text(b)); return
        if b[:4] in (b'II*\x00', b'MM\x00*'):
            t = tiff_text(b)
            if t is not None:
                X.kinds.append('tiff-ascii-tags'); X.parts.append(t); return
        if b[:4] == b'glTF' and len(b) >= 20:
            X.kinds.append('gltf')
            n0 = struct.unpack('<I', b[12:16])[0]
            X.parts.append(b[20:20 + n0].decode('utf-8', 'replace'))
            X.parts.append(strings(b[20 + n0:]))
            return
    except Exception as e:                           # a damaged container: what could be read is kept, the rest is REVIEW
        X.opaque.append(f'damaged or unreadable {X.kinds[-1] if X.kinds else "container"} ({type(e).__name__})')
        X.parts.append(strings(b))
        return
    txt, kind = decode_text(b)
    if txt is None:
        X.kinds.append('binary-strings')
        X.opaque.append('unknown binary format (printable strings scanned only)')
        X.parts.append(strings(b))
        X.parts.append(strings_utf16(b))
        return
    X.kinds.append(kind)
    X.parts.append(txt)
    if name.lower().endswith(XML_EXT) or txt.lstrip('\ufeff \t\r\n')[:1] == '<':
        X.parts.append(re.sub(r'<[^<>]{0,4000}>', '', txt))   # XML / HTML / SVG / OOXML: also the text with the tags removed
    b64_expand(txt, X, depth)


XML_EXT = ('.xml', '.svg', '.html', '.htm', '.xhtml', '.rels', '.vml', '.xlsx', '.docx', '.pptx', '.odt', '.ods', '.kml', '.gpx')


def decode_text(b):
    """UTF-32 / UTF-16 by BOM, UTF-8 (with or without BOM), BOM-less UTF-16 by its NUL pattern -> (text, kind) | (None, None)"""
    for bom, enc in ((b'\xff\xfe\x00\x00', 'utf-32-le'), (b'\x00\x00\xfe\xff', 'utf-32-be'), (b'\xff\xfe', 'utf-16-le'),
                     (b'\xfe\xff', 'utf-16-be')):
        if b.startswith(bom):
            try:
                return b[len(bom):].decode(enc), enc
            except UnicodeDecodeError:
                break
    head = b[:4096]
    if len(head) >= 8 and head.count(0) > 0.3 * len(head):  # BOM-less UTF-16 (ASCII text in UTF-16 is also valid UTF-8)
        ev, od = head[0::2], head[1::2]
        for enc, z, nz in (('utf-16-le', od, ev), ('utf-16-be', ev, od)):
            if z.count(0) > 0.6 * len(z) and nz.count(0) < 0.1 * len(nz):
                try:
                    return b[:len(b) // 2 * 2].decode(enc), enc + ' (no BOM)'
                except UnicodeDecodeError:
                    pass
    try:
        return b.decode('utf-8-sig'), 'text'
    except UnicodeDecodeError:
        pass
    return None, None


def strings_utf16(b, n=4):
    return '\n'.join(m.group().decode('utf-16-le', 'replace') for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}' % n, b))


B64 = re.compile(r'(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{8,}={0,2}(?![A-Za-z0-9+/=])')
MAGIC = (b'\x89PNG', b'\x1f\x8b', b'PK\x03\x04', b'%PDF-', b'BZh', b'\xfd7zXZ', b'\xff\xd8\xff', b'II*\x00', b'MM\x00*')


def b64_expand(txt, X, depth):
    """base64 runs (data URIs, JSON fields): a decoded container is extracted like a file, decoded printable text is scanned"""
    if depth >= MAXDEPTH:
        return
    for m in B64.finditer(txt):
        r = m.group()
        body = r.rstrip('=')
        if len(body) % 4 == 1 or not (re.search(r'[A-Z]', body) and re.search(r'[a-z0-9+/]', body)):
            continue
        try:
            d = base64.b64decode(body + '=' * (-len(body) % 4), validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        if d.startswith(MAGIC):
            X.kinds.append('base64')
            extract('base64', d, X, depth + 1)
            continue
        if len(d) >= 4:
            try:
                t = d.decode('utf-8')
            except UnicodeDecodeError:
                continue
            if sum(ch.isprintable() or ch in '\n\t' for ch in t) >= 0.9 * len(t):
                X.parts.append(t)


# ---- PDF (round 2, F12): stream filters, content-stream show operators, ToUnicode maps
PDF_FILTER = re.compile(rb'/(FlateDecode|Fl|ASCII85Decode|A85|ASCIIHexDecode|AHx|LZWDecode|LZW|RunLengthDecode|RL|DCTDecode|DCT'
                        rb'|JPXDecode|CCITTFaxDecode|CCF|JBIG2Decode|Crypt)\b')
PDF_IMAGE = (b'DCTDecode', b'DCT', b'JPXDecode', b'CCITTFaxDecode', b'CCF', b'JBIG2Decode')


def pdf_streams(b):
    """[(dict bytes, raw stream bytes)] of every 'stream ... endstream' of a PDF"""
    out = []
    for m in re.finditer(rb'(?<!end)stream(\r\n|\n|\r)', b):
        st = m.end()
        dstart = b.rfind(b'obj', max(0, m.start() - 8192), m.start())
        dtext = b[dstart + 3 if dstart >= 0 else max(0, m.start() - 2048):m.start()]
        if b'<<' not in dtext:
            continue
        en = b.find(b'endstream', st)
        if en < 0:
            continue
        lm = re.search(rb'/Length\s+(\d+)(?!\d)(?!\s+\d+\s+R)', dtext)
        raw = b[st:st + int(lm.group(1))] if lm and st + int(lm.group(1)) <= en else b[st:en].rstrip(b'\r\n')
        out.append((dtext, raw))
    return out


def pdf_decode(dtext, raw, X):
    """apply the stream's filters -> bytes | None (image data or not decodable: None, the latter flagged)"""
    data = raw
    for f in PDF_FILTER.findall(dtext):
        if f in PDF_IMAGE:
            return None
        try:
            if f in (b'FlateDecode', b'Fl'):
                d = zlib.decompressobj()
                data = d.decompress(data, MAXBYTES)
            elif f in (b'ASCII85Decode', b'A85'):
                t = data.strip()
                t = t[2:] if t.startswith(b'<~') else t
                t = t[:t.find(b'~>')] if b'~>' in t else t
                data = base64.a85decode(re.sub(rb'\s', b'', t))
            elif f in (b'ASCIIHexDecode', b'AHx'):
                t = re.sub(rb'[^0-9A-Fa-f]', b'', data.split(b'>')[0])
                data = bytes.fromhex(t.decode() + ('0' if len(t) % 2 else ''))
            else:
                X.opaque.append(f'PDF stream filter {f.decode()} not decoded')
                return None
        except Exception:
            X.opaque.append(f'PDF stream ({f.decode()}) could not be decoded')
            return None
    return data


def pdf_cmap(d):
    """a ToUnicode CMap -> (code length in bytes, {code int: text})"""
    mp, nbytes = {}, 1
    cs = re.search(rb'begincodespacerange\s*<([0-9A-Fa-f]+)>', d)
    if cs:
        nbytes = max(1, len(cs.group(1)) // 2)
    hx = lambda h: bytes.fromhex(h.decode() + ('0' if len(h) % 2 else ''))
    u16 = lambda h: hx(h).decode('utf-16-be', 'replace')
    for blk in re.findall(rb'beginbfchar(.*?)endbfchar', d, re.S):
        for a, c in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>', blk):
            mp[int(a, 16)] = u16(c)
    for blk in re.findall(rb'beginbfrange(.*?)endbfrange', d, re.S):
        for a, z, rest in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]*>)', blk):
            lo, hi = int(a, 16), int(z, 16)
            if hi - lo > 65536:
                continue
            if rest.startswith(b'['):
                for k, c in enumerate(re.findall(rb'<([0-9A-Fa-f]*)>', rest)):
                    mp[lo + k] = u16(c)
            else:
                base = int(rest[1:-1] or b'0', 16)
                for k in range(hi - lo + 1):
                    mp[lo + k] = chr(base + k) if base + k < 0x110000 else ''
    return nbytes, mp


def pdf_tokens(d):
    """the tokens of a content stream: ('s', bytes) strings, ('[',) ('],) arrays, ('o', name) operators"""
    i, n = 0, len(d)
    WS, DL = b' \t\r\n\f\x00', b'()<>[]{}/%'
    while i < n:
        c = d[i:i + 1]
        if c in (b' ', b'\t', b'\r', b'\n', b'\f', b'\x00'):
            i += 1
        elif c == b'%':
            j = d.find(b'\n', i)
            i = n if j < 0 else j + 1
        elif c == b'(':
            depth, i, buf = 1, i + 1, bytearray()
            while i < n and depth:
                ch = d[i]
                if ch == 0x5c and i + 1 < n:                 # backslash escapes
                    nx = d[i + 1:i + 2]
                    esc = {b'n': b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f', b'(': b'(', b')': b')', b'\\': b'\\'}
                    if nx in esc:
                        buf += esc[nx]; i += 2
                    elif nx.isdigit():
                        m = re.match(rb'[0-7]{1,3}', d[i + 1:i + 4]); buf.append(int(m.group(), 8) & 0xff); i += 1 + len(m.group())
                    elif nx in (b'\n', b'\r'):
                        i += 2 + (1 if d[i + 1:i + 3] == b'\r\n' else 0)
                    else:
                        i += 1
                    continue
                if ch == 0x28:
                    depth += 1
                elif ch == 0x29:
                    depth -= 1
                    if not depth:
                        i += 1
                        break
                buf.append(ch); i += 1
            yield ('s', bytes(buf))
        elif c == b'<':
            if d[i + 1:i + 2] == b'<':
                i += 2
                continue
            j = d.find(b'>', i)
            j = n if j < 0 else j
            h = re.sub(rb'[^0-9A-Fa-f]', b'', d[i + 1:j])
            yield ('s', bytes.fromhex(h.decode() + ('0' if len(h) % 2 else '')))
            i = j + 1
        elif c == b'>':
            i += 1
        elif c == b'[':
            yield ('[',); i += 1
        elif c == b']':
            yield (']',); i += 1
        else:
            j = i + 1 if c in (b'/', b'{', b'}') else i
            while j < n and d[j:j + 1] not in (b' ', b'\t', b'\r', b'\n', b'\f', b'\x00') and d[j:j + 1] not in (b'(', b')', b'<', b'>', b'[', b']', b'{', b'}', b'/', b'%'):
                j += 1
            tok = d[i:j]
            i = max(j, i + 1)
            if c != b'/' and not re.fullmatch(rb'[-+]?(\d+\.?\d*|\.\d+)', tok):
                yield ('o', tok)


def pdf_show_texts(d, cmaps):
    """the text of every show operator (Tj, TJ, ', ") of a content stream: pieces of a TJ array joined, each operator a
    line, every BT ... ET block also as one joined line; each string in every candidate decoding (bytes with NULs dropped,
    and through each ToUnicode map)"""
    def decs(bs):
        out = {bs.replace(b'\x00', b'').decode('latin-1')}
        for nb, mp in cmaps:
            if nb == 2 and len(bs) % 2 == 0:
                out.add(''.join(mp.get(int.from_bytes(bs[k:k + 2], 'big'), '') for k in range(0, len(bs), 2)))
            elif nb == 1:
                out.add(''.join(mp.get(c, chr(c)) for c in bs))
        return out
    lines, block, arr, pend = [], [], None, []
    for t in pdf_tokens(d):
        if t[0] == 's':
            (arr if arr is not None else pend).append(t[1])
        elif t[0] == '[':
            arr = []
        elif t[0] == ']':
            pend, arr = (arr or []), None
        else:
            op = t[1]
            if op in (b'Tj', b'TJ', b"'", b'"') and pend:
                bs = b''.join(pend)
                block.append(bs)
                lines.extend(decs(bs))
            elif op == b'ET' and block:
                lines.extend(decs(b''.join(block)))
                block = []
            elif op == b'BT':
                block = []
            pend = []
    return lines


def pdf_text(b, X, depth):
    if re.search(rb'/Encrypt\b', b):
        X.opaque.append('encrypted PDF')
    X.parts.append(strings(b))                       # uncompressed objects: the info dictionary, plain streams
    decoded = []
    for dtext, raw in pdf_streams(b):
        if re.search(rb'/Subtype\s*/Image', dtext):
            continue
        d = pdf_decode(dtext, raw, X)
        if d is None:
            continue
        decoded.append(d)
    cmaps = [pdf_cmap(d) for d in decoded if b'beginbfchar' in d or b'beginbfrange' in d]
    for d in decoded:
        if re.search(rb'\b(Tj|TJ)\b', d) and b'BT' in d:
            X.parts.extend(pdf_show_texts(d, cmaps))
        if d[:4] in (b'\x89PNG', b'PK\x03\x04') or d.startswith(b'\x1f\x8b'):
            extract('pdf-stream', d, X, depth + 1)
        else:
            X.parts.append(strings(d))               # object streams (/Title ...), XMP metadata, CMaps, embedded files
            X.parts.append(strings_utf16(d))


def to_text(path, b):
    """-> (text, kind) of a file's bytes (the selftest's single-file entry; audit() uses extract() and its REVIEW flags)"""
    X = Extract()
    extract(path, b, X)
    return X.text(), X.kind()


# ------------------------------------------------------------------------------------------------ matching
DASHES = '‐‑‒–—―⁃−➖﹘﹣－˗⸺⸻'
USPACES = '               　'
ZEROW = '​‌‍⁠﻿­᠎'
NORM_TABLE = {**{ord(c): '-' for c in DASHES}, **{ord(c): ' ' for c in USPACES}, **{ord(c): None for c in ZEROW}}


def normalise(t):
    """round 2, F13: decode HTML entities, JSON / JS escapes and %XX, NFKC, Unicode dashes -> '-', spaces -> ' ', zero-width
    characters removed (line breaks are kept, so line numbers stay close)"""
    if '&' in t:
        t = html.unescape(t)
    if '\\' in t:
        t = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), t)
        t = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), t)
        t = t.replace('\\/', '/')
    if '%' in t:
        t = re.sub(r'%(2[dD]|20|2[eE]|5[fF]|2[fF]|3[aA])', lambda m: chr(int(m.group(1), 16)), t)
    if not t.isascii():
        t = unicodedata.normalize('NFKC', t).translate(NORM_TABLE)
    return t


def scan_text(txt, I, allow_flights=None, lines=None, norm=True):
    """-> ({class: n} of hits (allowed flight numbers excluded and counted under 'allowed'), allowed). `lines` (a set) gets
    the line numbers of the hits (never the values)."""
    if norm:
        txt = normalise(txt)
    hits = {c: 0 for c in CLASSES}
    allowed = 0
    V = I.v
    runs = [(m.start(), m.end(), m.group()) for m in RUN.finditer(txt)]
    nl = [m.start() for m in re.finditer('\n', txt)] if lines is not None else None

    def hit(c, pos):
        hits[c] += 1
        if lines is not None:
            lines.add(bisect.bisect_right(nl, pos) + 1)

    nr = len(runs)
    for i in range(nr):
        st0, en0, r0 = runs[i]
        # single run: addresses (also after 0x), epoch s / ms
        a = r0[2:] if (r0[:2] in ('0x', '0X') and len(r0) == 8) else r0
        if HEX6.match(a) and a.lower() in V['address'] and address_context(txt, st0, en0, a, r0):
            hit('address', st0)
        if 12 <= len(r0) <= 64 and r0.lower() in V['fingerprint'] and re.fullmatch(r'[0-9a-fA-F]+', r0):
            hit('fingerprint', st0)
        if r0.isdigit() and len(r0) in (10, 13):
            if r0 in V['t_sha']:
                hit('t_sha', st0)
            elif r0 in V['ftime']:
                hit('ftime', st0)
        # windows of 1..3 runs joined by one separator (never across a decimal point, a digit group or a date: a ' ', '.'
        # or '/' between two digits does not join); two runs in neighbouring table / CSV cells join like ' ' (round 2)
        sq, seps = '', ''
        for j in range(i, min(nr, i + MAXRUNS)):
            if j > i:
                gap = txt[runs[j - 1][1]:runs[j][0]]
                if len(gap) == 1 and gap in SEPS:
                    if gap in ' ./' and runs[j - 1][2][-1].isdigit() and runs[j][2][0].isdigit():
                        break
                    seps += gap
                elif j == i + 1 and CELL_GAP.match(gap) and runs[i][2].isalpha() and not runs[j][2].isalpha():
                    seps += '|'                      # '| B | nnnn |', 'B,nnnn', 'B<tab>nnnn' (letters cell + number cell)
                else:
                    break
            sq += runs[j][2].upper()
            if len(sq) < 4:
                continue
            nd = sum(ch.isdigit() for ch in sq)
            if nd:
                loose = any(c in ' ./|' for c in seps)
                if loose:                    # 'MU nnnn', 'B nnnn', 'CES nnnn': capitals only, not a decimal, enough digits
                    w = txt[st0:runs[j][1]]
                    en = runs[j][1]
                    if w != w.upper() or (en + 1 < len(txt) and txt[en] in '.,' and txt[en + 1].isdigit()):
                        continue
                if '|' in seps:              # neighbouring cells: a registration only ('| B | nnnn |'), prefix of 1-2 letters
                    if sq in V['registration'] and nd >= 3 and len(runs[i][2]) <= 2:
                        hit('registration', st0)
                    continue
                if sq in V['registration'] and (not loose or nd >= 3):
                    hit('registration', st0)
                if sq in V['callsign'] and (not loose or nd >= 4 or (nd == 3 and not count_list(txt, st0, runs[j][1]))):
                    hit('callsign', st0)
                if sq in V['flight'] and (not loose or nd >= 3):
                    if allow_flights is not None and sq in allow_flights:
                        allowed += 1
                    else:
                        hit('flight', st0)
            elif sq in I.reg_alpha:          # B-LLL: joined by '-' (any case) or one all-capitals run (not snake_case)
                if (seps and all(c == '-' for c in seps)) or (not seps and runs[j][2].isupper()):
                    hit('registration', st0)
    for rx in (DTX, ISO_COMPACT):                     # date-times (round 2, F13: more forms, any case)
        for m in rx.finditer(txt):
            secs = m.group('s') is not None
            for e in dt_epochs(m):
                if secs and e in I.t_sec:
                    hit('t_sha', m.start())
                    break
                if not secs and e // 60 in I.t_min:
                    hit('t_sha', m.start())
                    break
                if secs and e in I.t2_sec:
                    hit('ftime', m.start())
                    break
    for m in UID.finditer(txt):
        if m.group(1) in V['uid']:
            hit('uid', m.start())
    for pos in table_addresses(txt, V['address']):    # digits-only addresses in an address column (round 2, F13)
        hit('address', pos)
    return hits, allowed


COUNT_NEXT = re.compile(r'[ \t]*[,;)]|[ \t]*\|[ \t]*[A-Z]{3}[ \t]\d')
COUNT_PREV = re.compile(r'(?:[,;(][ \t]*|\|[ \t]*\d+[ \t]*\|[ \t]*)$')


def count_list(txt, st, en):
    """a 3-digit 'AAA nnn' window that reads as a count in a list ('CES nnn, CQH nn', '(CES nnn)', 'x, CES nnn'): not a
    callsign hit (round 2: 3-digit callsigns with a space hit otherwise)"""
    return bool(COUNT_NEXT.match(txt, en) or COUNT_PREV.search(txt[max(0, st - 24):st]))


def table_addresses(txt, addrs):
    """positions of digits-only 6-digit addresses in the column of a CSV / TSV / markdown table whose header cell names an
    address (icao24, hex, address, mode s ...): a header further than 48 characters above is not seen by address_context"""
    if not addrs or not ADDR_KEY.search(txt):
        return []
    out, pos, col, dl = [], 0, None, None
    for line in txt.split('\n'):
        if col is None or dl not in line:
            col = None
            if ADDR_KEY.search(line):
                for d in ('\t', '|', ';', ','):
                    if d in line:
                        cells = [c.strip().strip('"\'`').lower() for c in line.split(d)]
                        k = next((n for n, c in enumerate(cells) if ADDR_KEY.fullmatch(c) or re.fullmatch(r'(icao|hex|addr|address)[ _-]?(24|hex)?', c)), None)
                        if k is not None:
                            col, dl = k, d
                            break
        else:
            cells = line.split(dl)
            if col < len(cells):
                v = cells[col].strip().strip('"\'`')
                if len(v) == 6 and v.isdigit() and v in addrs:
                    out.append(pos + line.find(v))
        pos += len(line) + 1
    return out


ADDR_KEY = re.compile(r'(icao|hex|addr|mode[ -]?s|transponder|24[ -]?bit)', re.I)


def address_context(txt, st, en, a, run):
    """a 6-hex run that equals a 24-bit address: a colour ('#rrggbb') never counts; a digits-only one counts only when it
    is quoted, written 0x..., or follows an address keyword within 48 characters (a 6-digit JSON number or a decimal
    fraction is not an address)"""
    if st > 0 and txt[st - 1] == '#':
        return False
    if not a.isdigit():
        return True
    if run[:2] in ('0x', '0X'):
        return True
    q0 = txt[st - 1] if st > 0 else ''
    q1 = txt[en] if en < len(txt) else ''
    if q0 in '"\'`' and q0 == q1:
        return True
    if q0 == '.' or q1 == '.':
        return False
    return bool(ADDR_KEY.search(txt[max(0, st - 48):st]))


def net_scan(txt, allow):
    n = 0
    for rx in NET:
        for m in rx.finditer(txt):
            if m.group() not in allow and not re.match(r'^F\d{4}$', m.group()):
                n += 1
    return n


def net_allow():
    s = type_designators()
    try:
        st = json.load(open(os.path.join(SHA3D, 'data', 'sha_stands.json'), encoding='utf-8'))
        s |= {x['name'] for x in st['stands']}
    except Exception:
        pass
    try:
        tg = json.load(open(os.path.join(SHA3D, 'data', 'sha_taxigraph.json'), encoding='utf-8'))
        for L in (tg.get('links') or tg.get('edges') or []):
            if isinstance(L, dict) and L.get('ref'):
                s.add(str(L['ref']))
    except Exception:
        pass
    s |= {'MH5001', 'ZSSS', 'ZSPD', 'GB50', 'WGS84', 'EGM2008', 'UTC8', 'CRJ900', 'CRJ200'}
    return s


def section_split(path, txt):
    """data/sha_sim_inputs.(json|js): -> (text without the 'published' section, published section text) or None"""
    if not re.search(r'data/sha_sim_inputs\.(json|js)$', path.replace(os.sep, '/')):
        return None
    t = txt
    if path.endswith('.js'):
        m = re.search(r'window\.SHA_SIM_INPUTS\s*=\s*(\{.*\})\s*;\s*$', t, re.S)
        if not m:
            return None
        t = m.group(1)
    try:
        d = json.loads(t)
    except ValueError:
        return None
    pub = d.pop('published', None)
    head = re.sub(r'window\.SHA_SIM_INPUTS\s*=.*', '', txt, flags=re.S) if path.endswith('.js') else ''
    return head + json.dumps(d, ensure_ascii=False), json.dumps(pub, ensure_ascii=False)


# ------------------------------------------------------------------------------------------------ file sets
def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True, text=True, check=False).stdout


def files_diff(pathspec):
    names = set(git('diff', '--name-only', 'HEAD', '--', pathspec).split('\n'))
    names |= set(git('ls-files', '--others', '--exclude-standard', '--', pathspec).split('\n'))
    return sorted(n for n in names if n and os.path.isfile(os.path.join(REPO, n)))


def files_staged():
    return sorted(n for n in git('diff', '--cached', '--name-only', '--diff-filter=ACMR').split('\n') if n)


def read_staged(n):
    return subprocess.run(['git', '-C', REPO, 'show', ':' + n], capture_output=True, check=False).stdout


# ------------------------------------------------------------------------------------------------ the audit
def audit(items, I, allow, net=False, quiet=False, reviewed=(), gate_all=True):
    """items: [(repo-relative or absolute path, 'staged' | None)] -> summary dict (counts only). A file that could not be
    read completely is a REVIEW (exit 2) when gate_all (--files) or when it is under sha3d/ (--staged / --diff / --docs)."""
    out = (lambda *a: None) if quiet else print
    nallow = net_allow() if net else None
    tot = {c: 0 for c in CLASSES}
    S = {'bad_files': 0, 'forbidden': 0, 'allowed': 0, 'net': 0, 'scanned': 0, 'cache_scanned': 0, 'hit_files': [],
         'review': 0, 'review_cleared': 0, 'path_hits': 0}
    rev = {os.path.normpath(os.path.relpath(os.path.abspath(r), REPO)) for r in reviewed}
    for n, mode in items:
        p = n if os.path.isabs(n) else os.path.join(REPO, n)
        rel = n.replace(os.sep, '/')
        # the path itself: every directory and the base name (round 2, F12); a file outside the repository: its base name
        ph, _ = scan_text(rel if not (os.path.isabs(n) or rel.startswith('../')) else os.path.basename(n), I)
        cs = cache_status(n, staged=(mode == 'staged'))
        if cs in ('identity-source', 'not-redistributable'):
            S['forbidden'] += 1
            S['bad_files'] += 1
            S['hit_files'].append(n)
            why = ('an observed-elsewhere identity table (never committable, OD4)' if cs == 'identity-source'
                   else 'a refs/cache file whose SOURCES.json does not mark it redistributable')
            out(f'  FORBIDDEN {n}: {why}')
            for c in CLASSES:
                tot[c] += ph[c]
            continue
        try:
            b = read_staged(n) if mode == 'staged' else open(p, 'rb').read()
        except OSError as e:
            out(f'  ERROR {n}: {e}')
            S['bad_files'] += 1
            continue
        X = Extract()
        extract(n, b, X)
        txt, kind = X.text(), X.kind()
        S['scanned'] += 1
        if cs == 'redistributable':
            S['cache_scanned'] += 1
        if X.forbidden:                              # an archive member named as an identity table
            S['forbidden'] += 1
            S['bad_files'] += 1
            S['hit_files'].append(n)
            out(f'  FORBIDDEN {n} [{kind}]: holds {X.forbidden} member(s) named as an observed-elsewhere identity table')
            continue
        sp = section_split(n, txt) if kind == 'text' else None
        L = set()
        if sp:
            h1, al1 = scan_text(sp[0], I, lines=None)
            h2, al2 = scan_text(sp[1], I, allow_flights=allow, lines=None)
            hits = {c: h1[c] + h2[c] for c in CLASSES}
            allowed = al1 + al2
            if sum(hits.values()):                   # line numbers from the file as written (section split loses them)
                scan_text(txt, I, allow_flights=allow, lines=L)
        else:
            hits, allowed = scan_text(txt, I, lines=L)
        S['allowed'] += allowed
        k = sum(hits.values())
        kp = sum(ph.values())
        if k or kp:
            S['bad_files'] += 1
            S['hit_files'].append(n)
            ln = sorted(L)
            if kp:
                S['path_hits'] += kp
                out(f'  HIT  {n} [path name]: ' + ', '.join(f'{c} {ph[c]}' for c in CLASSES if ph[c]))
            if k:
                out(f'  HIT  {n} [{kind}]: ' + ', '.join(f'{c} {hits[c]}' for c in CLASSES if hits[c])
                    + (f' (lines {", ".join(map(str, ln[:8]))}{" ..." if len(ln) > 8 else ""})' if ln else ''))
        for c in CLASSES:
            tot[c] += hits[c] + ph[c]
        if X.opaque:                                 # round 2, F12: not fully readable -> a review by eye (exit 2)
            key = os.path.normpath(os.path.relpath(p, REPO))
            cleared = key in rev or REVIEWED.get(key.replace(os.sep, '/')) == hashlib.sha256(b).hexdigest()
            scope = gate_all or rel.startswith('sha3d/')
            why = '; '.join(sorted(set(X.opaque)))[:200]
            if cleared:
                S['review_cleared'] += 1
                out(f'  reviewed {n} [{kind}]: {why} (cleared by --reviewed / REVIEWED)')
            elif scope:
                S['review'] += 1
                out(f'  REVIEW {n} [{kind}]: {why}')
            else:
                out(f'  note {n} [{kind}]: {why} (outside sha3d/, not gated)')
        if net and re.search(r'(^|/)(docs|jobs)/', n.replace(os.sep, '/')):
            x = net_scan(txt, nallow)
            S['net'] += x
            if x:
                out(f'  net  {n}: {x} pattern matches outside the allow-list (review by eye; not an exact hit)')
    S['tot'] = tot
    S['exit'] = 1 if (sum(tot.values()) or S['bad_files']) else 2 if S['review'] else 0
    return S


def selftest_round2_cases(I, png, reg4, cs, cs3, fl, addr_d, t, fmt, uid_ovl):
    """round 2 (F12 carriers, F13 forms): [(label, file name, bytes | str, class or None)]; values from the set in memory"""
    def zipped(members, method=zipfile.ZIP_DEFLATED):
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w', method) as z:
            for n, data in members:
                z.writestr(n, data)
        return b.getvalue()
    def tarred(name, data):
        b = io.BytesIO()
        with tarfile.open(fileobj=b, mode='w') as tf:
            ti = tarfile.TarInfo(name); ti.size = len(data); tf.addfile(ti, io.BytesIO(data))
        return b.getvalue()
    def pdf(content):
        objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                b'<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>']
        cz = zlib.compress(content)
        objs.append(b'<< /Length 5 0 R /Filter /FlateDecode >>\nstream\n' + cz + b'\nendstream')
        objs.append(str(len(cz)).encode())
        out = b'%PDF-1.4\n'
        for k, o in enumerate(objs):
            out += f'{k + 1} 0 obj\n'.encode() + o + b'\nendobj\n'
        return out + b'trailer\n<< /Root 1 0 R >>\n%%EOF\n'
    pre, num = reg4.split('-')
    fp16 = hashlib.sha256(open(sorted(glob.glob(os.path.join(OBS, 'sha_observed_*.json')))[0], 'rb').read()).hexdigest()[:16]
    t2 = sorted(I.t2_sec)[len(I.t2_sec) // 2]
    inS = I.taxi[0][0] if I.taxi else 0
    tb = next((x for x in sorted(I.t_sec) if (x + inS) % 60 and str(x + inS) in I.v['ftime']), None)
    L8 = t + LOCAL_S
    wm = next(x for x in range(t - t % 60, t + 86400, 60) if x not in I.t_sec and str(x) not in I.v['ftime'])
    xlsx = zipped([('[Content_Types].xml', '<?xml version="1.0"?><Types/>'),
                   ('xl/sharedStrings.xml', f'<?xml version="1.0"?><sst><si><t>registration</t></si><si><t>{reg4}</t></si></sst>')])
    docx = zipped([('word/document.xml', f'<?xml version="1.0"?><w:document><w:body><w:p><w:r><w:t>{pre}-</w:t></w:r>'
                    f'<w:r><w:t>{num}</w:t></w:r></w:p></w:body></w:document>')])
    cases = [
        # F12 carriers
        ('reg in a zip member', 'z1.zip', zipped([('a.txt', f'x {reg4} y')]), 'registration'),
        ('reg in a stored (uncompressed) zip member', 'z2.zip', zipped([('a.txt', f'x {reg4} y')], zipfile.ZIP_STORED), 'registration'),
        ('reg in a zip inside a zip', 'z3.zip', zipped([('in.zip', zipped([('a.txt', f'x {reg4} y')]))]), 'registration'),
        ('reg in an .xlsx shared string', 'z4.xlsx', xlsx, 'registration'),
        ('reg split over two Word runs in a .docx', 'z5.docx', docx, 'registration'),
        ('reg as a zip member NAME', 'z6.zip', zipped([(f'cards/{reg4}.txt', 'clean')]), 'registration'),
        ('reg in a tar member', 'z7.tar', tarred('a.txt', f'x {reg4} y'.encode()), 'registration'),
        ('reg in bz2', 'z8.bz2', bz2.compress(f'x {reg4} y'.encode()), 'registration'),
        ('reg in xz', 'z9.xz', lzma.compress(f'x {reg4} y'.encode()), 'registration'),
        ('reg in a PDF TJ array (kerned pieces)', 'p1.pdf', pdf(f'BT /F1 10 Tf [({pre}) -12 (-{num[:2]}) 8 ({num[2:]})] TJ ET'.encode()), 'registration'),
        ('reg in a PDF 2-byte string', 'p2.pdf', pdf(b'BT /F1 10 Tf [(' + b''.join(b'\x00' + bytes([c]) for c in reg4.encode()) + b')] TJ ET'), 'registration'),
        ('reg in a PDF hex string', 'p3.pdf', pdf(b'BT /F1 10 Tf <' + reg4.encode().hex().encode() + b'> Tj ET'), 'registration'),
        ('reg in UTF-16LE with BOM', 'u1.txt', f'x {reg4} y'.encode('utf-16'), 'registration'),
        ('reg in UTF-16BE with BOM', 'u2.txt', b'\xfe\xff' + f'x {reg4} y'.encode('utf-16-be'), 'registration'),
        ('reg in UTF-16LE without BOM', 'u3.txt', f'note {reg4} here and more'.encode('utf-16-le'), 'registration'),
        ('reg in UTF-32', 'u4.txt', f'x {reg4} y'.encode('utf-32'), 'registration'),
        ('reg base64 in JSON', 'u5.json', json.dumps({'b': base64.b64encode(reg4.encode()).decode()}), 'registration'),
        ('reg in a base64 PNG data URI', 'u6.html', '<img src="data:image/png;base64,' + base64.b64encode(png([(b'tEXt', b'Comment\x00' + reg4.encode())])).decode() + '">', 'registration'),
        ('reg in SVG tspans', 'u7.svg', f'<svg><text><tspan>{pre}-</tspan><tspan>{num}</tspan></text></svg>', 'registration'),
        # F13 forms
        ('reg with an en dash', 'n1.md', f'x {pre}–{num} y', 'registration'),
        ('reg with a no-break space', 'n2.md', f'x {pre} {num} y', 'registration'),
        ('reg as an HTML entity', 'n3.html', f'<p>{pre}&#45;{num}</p>', 'registration'),
        ('reg JSON-escaped', 'n4.json', '{"r": "' + pre + '\\u002d' + num + '"}', 'registration'),
        ('reg URL-encoded', 'n5.md', f'x {pre}%2D{num} y', 'registration'),
        ('reg with a zero-width space', 'n6.md', f'x {pre}-​{num} y', 'registration'),
        ('reg in full-width forms', 'n7.md', 'x ' + ''.join(chr(ord(c) + 0xfee0) if c.isalnum() else c for c in reg4) + ' y', 'registration'),
        ('reg split over a markdown table', 'n8.md', f'| {pre} | {num} |', 'registration'),
        ('reg split over CSV cells', 'n9.csv', f'{pre},{num},x', 'registration'),
        ('callsign 3 digits with a space', 'n10.md', f'x {cs3[:3]} {cs3[3:]} y', 'callsign'),
        ('address digits-only in a CSV column far below the header', 'n11.csv',
         'icao24,col_b,col_c,col_d,col_e,col_f,col_g,col_h\n' + 'a,b,c,d,e,f,g,h\n' * 3 + f'{addr_d},b,c,d,e,f,g,h\n', 'address'),
        ('overlay uid in a plan slot "oe:<uid>"', 'n12.json', json.dumps({'slot': 'oe:' + uid_ovl}), 'uid'),
        ('overlay uid in a continuation slot "cont:<uid>:a0"', 'n13.json', json.dumps({'slot': 'cont:' + uid_ovl + ':a0'}), 'uid'),
        ('t_sha "D Mon YYYY HH:MM local"', 'd1.md', f'landed {int(fmt(L8, "%d"))} {fmt(L8, "%b %Y %H:%M")} local', 't_sha'),
        ('t_sha RFC 2822', 'd2.txt', f'Date: {fmt(t, "%a, %d %b %Y %H:%M:%S")} GMT', 't_sha'),
        ('t_sha "YYYY/MM/DD HH:MM:SS"', 'd3.md', f'at {fmt(t, "%Y/%m/%d %H:%M:%S")} UTC', 't_sha'),
        ('t_sha CSV date column, time column', 'd4.csv', f'day,time_utc,airline\n{fmt(t, "%Y-%m-%d")},{fmt(t, "%H:%M:%S")},CES\n', 't_sha'),
        ('t_sha JSON day and time fields', 'd5.json', json.dumps({'day': fmt(t, '%Y-%m-%d'), 'time': fmt(t, '%H:%M:%S')}), 't_sha'),
        ('t_sha ISO lower-case t / z', 'd6.md', f'at {fmt(t, "%Y-%m-%dt%H:%M:%Sz")}', 't_sha'),
        ('t_sha "Mon D, YYYY HH:MM:SS"', 'd7.md', f'on {fmt(L8, "%b")} {int(fmt(L8, "%d"))}, {fmt(L8, "%Y %H:%M:%S")} Beijing', 't_sha'),
        ('t_sha "DD/MM/YYYY HH:MM:SS"', 'd8.md', f'{fmt(t, "%d/%m/%Y %H:%M:%S")} UTC', 't_sha'),
        ('t_sha in a markdown table: date cell, time cell', 'd9.md', f'| {fmt(t, "%Y-%m-%d")} | {fmt(t, "%H:%M")} |', 't_sha'),
        ('other per-flight time, epoch s', 'e1.json', json.dumps({'t': t2}), 'ftime'),
        ('other per-flight time, epoch float', 'e2.json', f'{{"t": {t2}.37}}', 'ftime'),
        ('other per-flight time, ISO second', 'e3.md', f'fix {fmt(t2, "%Y-%m-%dT%H:%M:%SZ")}', 'ftime'),
        ('fingerprint: the sha256 prefix of a local day table', 'f9.json', json.dumps({'inputs_sha256_16': {'x': fp16}}), 'fingerprint'),
        ('clean: a count table "| AAA | nnn / nnn |"', 'k7.md', f'| {cs3[:3]} | {cs3[3:]} / 834 = **31 %** |', None),
        ('clean: a class and a count in table cells', 'k8.md', f'| B | 12 | C | 140 |', None),
        ('clean: a whole-minute epoch (a METAR obsTime) that is no t_sha', 'k9.json', json.dumps({'obsTime': wm}), None),
        ('clean: a date-time on a day without observations', 'k10.md', 'at 2026-11-20T06:37:05Z and 20 Nov 2026 14:37 local', None),
    ]
    if tb:
        cases.append(('tier-2 block time (t_sha + taxi-in), epoch ms', 'e4.json', json.dumps({'tBlock': (tb + inS) * 1000}), 'ftime'))
    try:                                             # a real matplotlib PDF (Type 3 and Type 42 fonts), when matplotlib is there
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for ft in (3, 42):
            matplotlib.rcParams['pdf.fonttype'] = ft
            fig = plt.figure()
            fig.text(0.5, 0.5, f'stand 233 {reg4}')
            b = io.BytesIO()
            fig.savefig(b, format='pdf')
            plt.close(fig)
            cases.append((f'reg as text in a matplotlib PDF (fonttype {ft})', f'p{ft}.pdf', b.getvalue(), 'registration'))
    except ImportError:
        pass
    return cases


def selftest(I, allow):
    """the audit must catch real values in every carrier and written form (F1-F3, F8) and pass clean text; values are taken
    from the identity set in memory, written to a temporary directory outside the repository, deleted, never printed."""
    import tempfile, shutil
    def pick(s, rx):
        L = sorted(x for x in s if re.fullmatch(rx, x))
        return L[len(L) // 2] if L else None
    reg4 = pick(I.raw['registration'], r'B-\d{4}')
    regL = pick(I.raw['reg_alpha'], r'B-[A-Z]{3}')
    cs = pick(I.raw['callsign'], r'CES\d{4}')
    fl = pick(I.raw['flight'], r'MU\d{4}')
    addr = pick(I.v['address'], r'[0-9]{2}[0-9a-f]*[a-f][0-9a-f]*')
    addr_d = pick(I.v['address'], r'[1-9][0-9]{5}')
    cs3 = pick(I.raw['callsign'], r'CES[1-9]\d{2}')
    T = sorted(x for x in I.t_sec if x % 60 not in (0, 59, 1))
    t = T[len(T) // 2]
    fmt = lambda e, f: dt.datetime.fromtimestamp(e, dt.timezone.utc).strftime(f)
    uids = sorted(I.v['uid'])
    uid_src = next(u for u in uids if re.fullmatch(r'\d{4}\.\d{2}\.\d{2}:\d+', u))
    uid_ovl = next(u for u in uids if re.fullmatch(r'\d{4}-\d{2}-\d{2}:\d+', u))
    fl_pub = sorted(allow & I.v['flight'])[0] if allow & I.v['flight'] else None
    # a digit-free registration's letters as ordinary text that must NOT hit: lower case, no separator, or '.' / ' ' joined
    letters = regL.replace('-', '').lower()
    d = tempfile.mkdtemp(prefix='audit_selftest_')
    ok = True
    try:
        def png(chunks):
            def ch(typ, data):
                return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
            raw = b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 0, 0, 0, 0))
            for typ, data in chunks:
                raw += ch(typ, data)
            return raw + ch(b'IDAT', zlib.compress(b'\x00\x00')) + ch(b'IEND', b'')
        cases = [
            ('reg exact', 'a.txt', f'note {reg4} here', 'registration'),
            ('reg lower case', 'a2.md', f'x {reg4.lower()} y', 'registration'),
            ('reg without hyphen', 'a3.md', f'x {reg4.replace("-", "")} y', 'registration'),
            ('reg with space', 'a4.md', f'x {reg4.replace("-", " ")} y', 'registration'),
            ('reg with underscore', 'a5.md', f'x {reg4.replace("-", "_")} y', 'registration'),
            ('reg in a dotted path', 'a6.js', f'const p = "a/{reg4.replace("-", ".")}/b";', 'registration'),
            ('reg B-LLL', 'b1.md', f'x {regL} y', 'registration'),
            ('reg B-LLL lower case', 'b2.md', f'x {regL.lower()} y', 'registration'),
            ('reg B-LLL all capitals, no hyphen', 'b3.md', f'x {regL.replace("-", "")} y', 'registration'),
            ('reg B-LLL in a PNG tEXt chunk', 'b4.png', png([(b'tEXt', b'Comment\x00' + regL.encode())]), 'registration'),
            ('callsign hyphen-joined', 'c1.md', f'x-{cs}-y', 'callsign'),
            ('callsign with space', 'c2.md', f'x {cs[:3]} {cs[3:]} y', 'callsign'),
            ('flight lower case in JSON', 'c3.json', json.dumps({'f': fl.lower()}), 'flight'),
            ('flight with space', 'c4.md', f'x {fl[:2]} {fl[2:]} y', 'flight'),
            ('flight in an identifier', 'c5.js', f'const {fl}_x = 1;', 'flight'),
            ('address', 'd1.js', f'const a = "{addr}";', 'address'),
            ('address upper case', 'd2.json', json.dumps({'a': addr.upper()}), 'address'),
            ('address 0x', 'd3.js', f'const a = 0x{addr};', 'address'),
            ('t_sha epoch ms', 'e1.csv', f'{t * 1000},1', 't_sha'),
            ('t_sha epoch s float', 'e2.json', f'{{"t": {t}.0}}', 't_sha'),
            ('t_sha ISO second Z', 'f1.txt', f'at {fmt(t, "%Y-%m-%dT%H:%M:%SZ")} here', 't_sha'),
            ('t_sha ISO minute Z', 'f2.md', f'at {fmt(t, "%Y-%m-%dT%H:%MZ")}', 't_sha'),
            ('t_sha ISO minute, no zone', 'f3.md', f'at {fmt(t, "%Y-%m-%d %H:%M")} UTC', 't_sha'),
            ('t_sha local second, no zone', 'f4.md', f'at {fmt(t + LOCAL_S, "%Y-%m-%d %H:%M:%S")} local', 't_sha'),
            ('t_sha local +08:00', 'f5.md', f'at {fmt(t + LOCAL_S, "%Y-%m-%dT%H:%M:%S")}+08:00', 't_sha'),
            ('t_sha local minute UTC+8', 'f6.md', f'at {fmt(t + LOCAL_S, "%Y-%m-%d %H:%M")} UTC+8', 't_sha'),
            ('t_sha compact ISO', 'f7.md', f'id {fmt(t, "%Y%m%dT%H%M%SZ")}', 't_sha'),
            ('source uid', 'g1.md', f'x {uid_src} y', 'uid'),
            ('overlay uid', 'g2.json', json.dumps({'ident': uid_ovl}), 'uid'),
            ('reg in a PNG zTXt chunk', 'h1.png', png([(b'zTXt', b'Comment\x00\x00' + zlib.compress(reg4.encode()))]), 'registration'),
            ('callsign in a PNG iTXt chunk', 'h2.png', png([(b'iTXt', b'Title\x00\x00\x00en\x00\x00' + cs.encode())]), 'callsign'),
            ('reg in a binary', 'h3.bin', b'\x00\x01\x02' + reg4.encode() + b'\xff\xfe', 'registration'),
            ('clean text', 'j1.txt', 'clean text A321 B738 F4551/26 stand 233 2026-11-12 0x1f 08:00-09:00 v2026.11.12-prod-0', None),
            ('clean: B-LLL letters as words', 'j2.js', f'const {letters} = 1; x.{letters[1:]} = b.{letters[1:]}; "{letters}"; b_{letters[1:]}', None),
            ('clean: decimal digits', 'j3.json', json.dumps({'x': [121.336289, 31.197848, 0.5, 1234567]}), None),
            ('address digits-only, quoted', 'k1.json', json.dumps({'a': addr_d}), 'address'),
            ('clean: the same 6 digits as a JSON number / a decimal', 'k2.json', f'[[{addr_d}, 2.7], [1.{addr_d}]]', None),
            ('clean: the address as a colour', 'k3.css', f'a {{ color: #{addr}; }}', None),
            ('clean: a word + number ("at 230" style)', 'k4.md', f'stand {fl[:2].lower()} {fl[2:]} m', None),
            ('clean: a count after an ICAO code ("CES nnn, ...")', 'k5.md', f'| {cs3[:3]} {cs3[3:]}, CQH 62 |', None),
            ('clean: a reg split by a decimal ("B6 0.12" style)', 'k6.md', f'{reg4[0]}{reg4[2]} {reg4[3]}.{reg4[4:]} m', None),
        ]
        cases += selftest_round2_cases(I, png, reg4, cs, cs3, fl, addr_d, t, fmt, uid_ovl)
        for label, name, data, want in cases:
            data = data.encode() if isinstance(data, str) else data
            p = os.path.join(d, name)
            open(p, 'wb').write(data)
            txt, kind = to_text(p, data)
            hits, _ = scan_text(txt or '', I)
            got = [c for c in CLASSES if hits[c]]
            good = (want in got) if want else not got
            ok &= good
            print(f'  selftest {label} [{kind}]: {"ok" if good else "FAILED"} (classes hit: {", ".join(got) or "none"})')
        # round 2, F12: a value in a FILE NAME (clean content) and the REVIEW gate, through audit() as the modes run it
        sub = os.path.join(d, 'names')
        os.makedirs(sub)
        for label, name, want in (('flight number in a file name', f'card_{fl}.png', 'hit'),
                                  ('registration in a file name', f'stand_233_{reg4}.md', 'hit'),
                                  ('registration as a directory name', os.path.join(reg4.replace('-', ''), 'x.md'), 'hit'),
                                  ('clean file name', 'plan_stands.png', 'clean')):
            fp = os.path.join(sub, name)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, 'wb').write(png([]) if name.endswith('.png') else b'clean text\n')
            rel = os.path.relpath(fp, d)
            if os.path.dirname(rel) == 'names' or os.sep not in rel:      # base name: through audit() itself
                S = audit([(fp, None)], I, allow, quiet=True)
                got = 'hit' if S['path_hits'] and S['exit'] == 1 else 'clean' if S['exit'] == 0 else f'exit {S["exit"]}'
            else:                                                           # a directory name: the path matcher
                ph, _ = scan_text(rel.replace(os.sep, '/'), I)
                got = 'hit' if sum(ph.values()) else 'clean'
            good = got == want
            ok &= good
            print(f'  selftest {label}: {"ok" if good else "FAILED"} ({got})')
        blob = os.path.join(d, 'blob.bin')
        open(blob, 'wb').write(bytes(range(256)) * 8)
        S1 = audit([(blob, None)], I, allow, quiet=True)
        S2 = audit([(blob, None)], I, allow, quiet=True, reviewed=[blob])
        good = S1['exit'] == 2 and S1['review'] == 1 and S2['exit'] == 0 and S2['review_cleared'] == 1
        ok &= good
        print(f'  selftest unknown binary -> REVIEW exit 2, --reviewed clears it: {"ok" if good else "FAILED"} (exit {S1["exit"]} / {S2["exit"]})')
        zday = os.path.join(d, 'neutral.zip')                 # a whole day table zipped under a neutral name
        src = sorted(glob.glob(os.path.join(OBS, 'sha_observed_*.json')))[-1]
        bz = io.BytesIO()
        with zipfile.ZipFile(bz, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('t.json', open(src, 'rb').read())
        open(zday, 'wb').write(bz.getvalue())
        S3 = audit([(zday, None)], I, allow, quiet=True)
        bz = io.BytesIO()
        with zipfile.ZipFile(bz, 'w') as z:
            z.writestr('x/sha_observed_2026-11-12.json', '{}')
        open(zday, 'wb').write(bz.getvalue())
        S4 = audit([(zday, None)], I, allow, quiet=True)
        good = S3['exit'] == 1 and sum(S3['tot'].values()) > 100 and S4['forbidden'] == 1 and S4['exit'] == 1
        ok &= good
        print(f'  selftest a day table zipped under a neutral name / an archive member named as a day table: {"ok" if good else "FAILED"}')
        if fl_pub:
            body = {'v': 1, 'published': {'hkg': [{'flight': fl_pub}]}}
            p = os.path.join(d, 'data', 'sha_sim_inputs.json')
            os.makedirs(os.path.dirname(p))
            for where, want_hit in (('published', False), ('outside', True)):
                b = dict(body) if where == 'published' else {'v': 1, 'x': fl_pub, 'published': {}}
                txt = json.dumps(b)
                sp = section_split(p, txt)
                h1, _ = scan_text(sp[0], I)
                h2, al = scan_text(sp[1], I, allow_flights=allow)
                n = sum(h1.values()) + sum(h2.values())
                good = (n > 0) == want_hit
                ok &= good
                print(f'  selftest published flight number {where} the section: {"ok" if good else "FAILED"} (hits {n}, allowed {al})')
        nonsha = sorted(I.v['flight'] - allow)
        if nonsha:                                   # F8: an identity flight number that is not a SHA row stays a hit there
            txt = json.dumps({'hkg': [{'flight': nonsha[len(nonsha) // 2]}]})
            h, al = scan_text(txt, I, allow_flights=allow)
            good = h['flight'] > 0 and al == 0
            ok &= good
            print(f'  selftest a non-SHA flight number inside the published section: {"ok" if good else "FAILED"}')
        # F1: refs/cache paths - the identity tables are forbidden whatever their content; a non-redistributable cache
        # file is forbidden; a redistributable one is scanned (and hits like any file)
        cache = os.path.join(d, 'sha3d', 'refs', 'cache')
        files = {'observed_elsewhere/copy.json': '{"note": "clean"}', 'observed_elsewhere/scan/x.json': '{}',
                 'metar/awc_days/a.json': f'{{"x": "{reg4}"}}', 'metar/awc_days/b.json': '{"x": "clean"}',
                 'notam/n.json': '{"x": "clean"}', 'nosources/z.json': '{}', 'loose.json': '{}'}
        srcs = {'observed_elsewhere': {'redistributable': True}, 'metar': {'redistributable': True},
                'notam': {'redistributable': False}}
        for sub, s in srcs.items():
            os.makedirs(os.path.join(cache, sub), exist_ok=True)
            json.dump(s, open(os.path.join(cache, sub, 'SOURCES.json'), 'w'))
        for rel, body in files.items():
            fp = os.path.join(cache, rel)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, 'w').write(body)
        elsewhere = os.path.join(d, 'out', 'sha_observed_2026-11-12.json')
        os.makedirs(os.path.dirname(elsewhere))
        open(elsewhere, 'w').write('{}')
        want = {'observed_elsewhere/copy.json': 'forbidden', 'observed_elsewhere/scan/x.json': 'forbidden',
                'metar/awc_days/a.json': 'hit', 'metar/awc_days/b.json': 'clean', 'notam/n.json': 'forbidden',
                'nosources/z.json': 'forbidden', 'loose.json': 'forbidden'}
        for rel, w in list(want.items()) + [(elsewhere, 'forbidden')]:
            fp = rel if os.path.isabs(rel) else os.path.join(cache, rel)
            S = audit([(fp, None)], I, allow, quiet=True)
            got = 'forbidden' if S['forbidden'] else 'hit' if sum(S['tot'].values()) else 'clean'
            good = got == w and S['exit'] == (0 if w == 'clean' else 1)
            ok &= good
            show = rel if not os.path.isabs(rel) else 'out/sha_observed_<day>.json'
            print(f'  selftest refs/cache path {show}: {"ok" if good else "FAILED"} ({got}, exit {S["exit"]})')
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print('selftest:', 'passed' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description='exact-match identity audit (prints counts only)')
    ap.add_argument('--selftest', action='store_true', help='check the audit catches real values in every carrier (temporary files)')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--files', nargs='+')
    g.add_argument('--staged', action='store_true')
    g.add_argument('--diff', action='store_true')
    g.add_argument('--docs', action='store_true')
    ap.add_argument('--path', default='sha3d', help='pathspec for --diff (default sha3d)')
    ap.add_argument('--net', action='store_true', help='also run the broadened regex net (reported, not failing)')
    ap.add_argument('--reviewed', nargs='+', default=[], help='paths whose REVIEW flag was cleared by eye for this run')
    a = ap.parse_args()

    I = load_identities()
    allow = published_flights()
    c = I.counts()
    print(f'identity set: {I.total()} values from {I.files} local files '
          f'({", ".join(f"{k} {c[k]}" for k in CLASSES)}; registrations without a digit {len(I.reg_alpha)}); '
          f'published SHA-row flight allow-list {len(allow)}')
    if a.selftest:
        selftest(I, allow)
    if a.files:
        items = [(os.path.relpath(os.path.abspath(f), REPO), None) for f in a.files]
    elif a.staged:
        items = [(n, 'staged') for n in files_staged()]
    elif a.docs:
        items = [(os.path.relpath(p, REPO), None) for p in sorted(glob.glob(os.path.join(SHA3D, 'docs', '**', '*'), recursive=True)) if os.path.isfile(p)]
    else:
        items = [(n, None) for n in files_diff(a.path)]
    S = audit(items, I, allow, net=a.net, reviewed=a.reviewed, gate_all=bool(a.files))
    tot = S['tot']
    print(f'scanned {S["scanned"]} files (refs/cache redistributable {S["cache_scanned"]}): exact hits {sum(tot.values())} '
          f'in {S["bad_files"] - S["forbidden"]} files ({", ".join(f"{k} {tot[k]}" for k in CLASSES)}; in path names '
          f'{S["path_hits"]}); forbidden paths {S["forbidden"]}; needs review {S["review"]} (cleared {S["review_cleared"]}); '
          f'allowed published flight numbers {S["allowed"]}' + (f'; net matches {S["net"]}' if a.net else ''))
    if S['exit'] == 2:
        print('exit 2: no exact hit, but files the audit could not read completely (REVIEW): look at them, then pass --reviewed')
    sys.exit(S['exit'])


if __name__ == '__main__':
    main()
