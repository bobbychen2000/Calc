#!/usr/bin/env python3
r"""Exact-match identity audit (OD4; docs/phase3/design.md s.3, s.9.1 risk 1, review H4). LOCAL tool: it needs the gitignored
refs/cache/observed_elsewhere/ tables. It prints COUNTS, FILE PATHS AND LINE NUMBERS ONLY, never a matched value.
Exit 1 on any hit, on any forbidden path and on any ERROR (a file or a git object that could not be read, a git command that
failed: round 3, F12 - the audit never treats a failed read as an empty file or a failed listing as no files); exit 2 (no
hit) when a file could not be read completely and needs a review by eye ('REVIEW': an unknown binary or archive format, an
encrypted member, a PDF stream filter it cannot decode, an unknown PNG chunk or bytes after IEND; round 2 F12, round 3 F24),
in every mode and for every path of the repository. A printed path is masked where a component holds a value (round 3).

  python3 -I tools/sim/audit_identity.py --files F [F ...]     the given files (every carrier below)
  python3 -I tools/sim/audit_identity.py --staged              every staged change except deletions (A C M R T U X B), its
                                                               index blob read by id - the lead's commit gate, run before
                                                               every commit (git -c core.quotePath=false, -z, literal
                                                               pathspecs: any path name; round 3, F12)
  python3 -I tools/sim/audit_identity.py --diff [--path P]     tracked changes vs HEAD + untracked, not ignored files (default)
  python3 -I tools/sim/audit_identity.py --docs                every file under sha3d/docs/
  python3 -I tools/sim/audit_identity.py --selftest            planted real values in every carrier and form (temporary
                                                               files outside the repository, deleted; nothing printed)
  python3 -I tools/sim/audit_identity.py --install-hooks       the pre-commit hook (--staged) and the commit-msg hook (--files
                                                               on the message) in the repository's hooks directory, so that
                                                               'git commit', 'commit -a', 'commit <path>' and the message are
                                                               gated (round 4, F12); --print-hooks shows them
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
Round 3 (F13, F26, F27): a second pass over the text with its hard line wraps joined; the time before the date; compact
stamps YYYYMMDD[_-]hhmm[ss] (also in path names); airline NAMES before a number (data/lookup.js AIRLINES); an airline field /
column joined with a flight-number field / column (JSON, CSV, markdown); addresses as hh:hh:hh or decimal in address-named
fields; {"day", "tod_s"}; Excel serials; a date cell and a time cell of one row; Cyrillic / Greek look-alikes; fingerprints
as hex prefixes >= 8 (sha256 / sha1 / md5 / sha512 / git blob id) and base64 (SRI) of every local file and of every overlay
(as printed and canonical JSON), plus the local plan hashes recorded by tools/sim/test_plan.mjs in
out/phase3/local/fingerprints.json; an 'ftime' value counts only in a per-flight context (160 characters).
Round 4 (F12, N1-N3): --staged reads a Git LFS pointer's object from the local LFS store (ERROR when it is missing) and,
under any other clean filter, the work-tree file too (ERROR when it is gone); the identity set must be complete (every
file SOURCES.json lists exists, is loaded and matches its size / sha256; every class non-empty; else 'ERROR identity set
incomplete', exit 1); the non-table local files (README, spot checks, scan logs) are read as free text for designators;
zones as offsets (GMT+0800, '(China Standard Time)'), ctime / git / date(1) layouts, AM / PM, DD.MM.YYYY and DD-MM-YYYY,
zero-padded flight numbers, '+' as a joiner, bidi marks removed, header names that contain airline / carrier / flight /
number, table-shaped JSON (pandas 'split' / 'columns', column arrays), date + seconds-of-day columns; base64 runs tried as
text, UTF-16, zlib / raw deflate / gzip, NumPy, SQLite, GIF and typed arrays (an undecodable run of >= 64 bytes is
REVIEW), hex runs; JPEG to EOI (and after it: REVIEW), every TIFF / Exif tag and sub-IFD with UTF-16 strings (unreferenced
bytes: strings + REVIEW), glTF JSON / images / unknown chunks (REVIEW), gzip FNAME / FCOMMENT, zip and tar comments and pax
headers, PDF string objects (UTF-16BE titles), PostScript glyphshow text; addresses below 0x004000 dropped (no state block).
NOT covered (docs/phase3/plan.md, round 4, lists them): text rendered into image pixels (the app's harness asserts identity
'none' before every committable shot, design s.3 / H5), values split further than the joined forms, unusual encodings
(REVIEW), fingerprints shorter than 8 hex characters or of transformed copies, 'git commit --no-verify' (skips the hooks).
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
SEPS = ' -_./+'                                             # '+' (a URL query 'q=MU+nnnn') like ' ' (round 4, N2)
CELL_GAP = re.compile(r'^(?:[ \t]*\|[ \t]*|[,;\t])$')       # neighbouring markdown-table / CSV / TSV cells (round 2, F13)
MAXRUNS = 3
# zones as written (round 4, N2: any offset): Z / UTC / GMT, UTC+8 / GMT+0800 / UTC-5 style, +08:00 / +0800 / +08 / -05:00,
# 'local' / 'LT' / 'CST' / 'Beijing' / '(China Standard Time)' (UTC+8); a bare '-hh:mm' may also be the end of a range
# ('08:00-09:00'): it is read as that offset AND as UTC and as UTC+8 (zone_offsets)
ZONE = (r'(?:[ \t]?(?P<z>Z(?![A-Za-z])|(?:UTC|GMT)[ \t]?[+-][ \t]?\d{1,2}(?::?\d{2})?(?!\d)|UTC|GMT|[+-]\d{2}(?::?\d{2})?(?!\d)'
        r'|local(?![A-Za-z])|LT(?![A-Za-z])|CST(?![A-Za-z])|Beijing|\(?China Standard Time\)?|Asia/Shanghai))?')
MON = (r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?'
       r'|nov(?:ember)?|dec(?:ember)?)')
MONTHS = {m: i + 1 for i, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'))}
DATE = (r'(?:(?P<y>\d{4})(?P<ds>[-/.])(?P<mo>\d{1,2})(?P=ds)(?P<d>\d{1,2})'                       # 2026-11-12, 2026/11/12
        r'|(?P<d2>\d{1,2})(?:st|nd|rd|th)?[ -]?(?P<mon2>' + MON + r')\.?[ ,-]+(?P<y2>\d{4})'     # 12 Nov 2026, 12-Nov-2026
        r'|(?P<mon3>' + MON + r')\.?[ -](?P<d3>\d{1,2})(?:st|nd|rd|th)?,?[ \t]+(?P<y3>\d{4})'    # Nov 12, 2026
        r'|(?P<a4>\d{1,2})(?P<ds4>[/.-])(?P<b4>\d{1,2})(?P=ds4)(?P<y4>\d{4}))')                 # 12/11/2026, 12.11.2026, 12-11-2026 (both readings; round 4)
DT_SEP = (r'(?:[Tt_]|[ \t]*[,;|\t][ \t]*|[ \t]+(?:at[ \t]+|@[ \t]*)?'
          r'|"?[ \t]*,[ \t]*"?[A-Za-z_]{1,24}"?[ \t]*:[ \t]*"?)')                                  # ..."day":"D","time":"T"
# a 12-hour time with AM / PM (also 'p.m.'; after any Unicode space, normalised to ' ') is mapped to 24 h (round 4, N2)
TIME = (r'(?P<h>\d{1,2}):(?P<mi>\d{2})(?::(?P<s>\d{2})(?:[.,]\d+)?)?(?![\d:])'
        r'(?:[ \t]?(?P<ap>[AaPp]\.?[Mm]\.?)(?![A-Za-z]))?')
DTX = re.compile(r'(?<![\d/.-])' + DATE + DT_SEP + TIME + ZONE, re.I)
# ctime / asctime ('Thu Nov 12 08:15:23 2026'), date(1) ('... 08:15:23 CST 2026'), git's default date ('... 2026 +0800')
# (round 4, N2)
CTIME = re.compile(r'(?<![\w])(?:(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?[ \t]+)?(?P<mon5>' + MON + r')\.?[ \t]+(?P<d5>\d{1,2})'
                   r'[ \t]+' + TIME + r'(?:[ \t]+(?P<z>[A-Za-z]{2,5}|(?:UTC|GMT)?[+-]\d{1,2}(?::?\d{2})?))?[ \t]+(?P<y5>\d{4})'
                   r'(?![\d:])(?:[ \t]+(?P<z2>[+-]\d{2}:?\d{2})(?!\d))?', re.I)
TZ_ABBR = {'Z': [0], 'UT': [0], 'UTC': [0], 'GMT': [0], 'WET': [0], 'BST': [3600], 'CET': [3600], 'CEST': [7200], 'EET': [7200],
           'EEST': [10800], 'MSK': [10800], 'IST': [19800, 7200, 3600], 'ICT': [25200], 'WIB': [25200], 'CST': [28800, -21600],
           'HKT': [28800], 'SGT': [28800], 'AWST': [28800], 'PHT': [28800], 'MYT': [28800], 'KST': [32400], 'JST': [32400],
           'AEST': [36000], 'AEDT': [39600], 'NZST': [43200], 'NZDT': [46800], 'EST': [-18000], 'EDT': [-14400],
           'CDT': [-18000], 'MST': [-25200], 'MDT': [-21600], 'PST': [-28800], 'PDT': [-25200], 'AKST': [-32400],
           'HST': [-36000], 'LOCAL': [28800], 'LT': [28800], 'BEIJING': [28800], 'CHINASTANDARDTIME': [28800],
           'ASIA/SHANGHAI': [28800]}


def zone_offsets(z):
    """a zone as written -> [offsets east of UTC in s, None = also the zone-less readings] | None (no zone or an unknown
    name: the caller reads the time as UTC and as UTC+8) (round 4, N2)"""
    z = (z or '').replace(' ', '').replace('\t', '').strip('()')
    if not z:
        return None
    u = z.upper()
    m = re.fullmatch(r'(UTC|GMT)?([+-])(\d{1,2})(?::?(\d{2}))?', u)
    if m:
        off = (int(m.group(3)) * 3600 + int(m.group(4) or 0) * 60) * (1 if m.group(2) == '+' else -1)
        return [off, None] if (not m.group(1) and m.group(2) == '-') else [off]
    return TZ_ABBR.get(u)
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


GENERIC_NAME = {'airlines', 'airline', 'airways', 'aviation', 'company', 'co', 'co.', 'ltd', 'ltd.', 'limited', 'corporation',
                'corp', 'corp.', 'group', 'inc', 'inc.', 'lines'}


def airline_names(AL):
    """data/lookup.js AIRLINES ('Name|IATA') and the short names of data/sha_sim_inputs.json -> ({name lower: {(ICAO, IATA)}},
    {every ICAO and IATA designator}); a name also without trailing generic words ('China Eastern Airlines' -> 'China
    Eastern') while two or more words remain (round 3, F13)"""
    names, codes = {}, set()
    iata_of = {}
    for icao, v in AL.items():
        parts = (v or '').split('|')
        name = parts[0].strip()
        iata = parts[1].strip() if len(parts) > 1 and re.fullmatch(r'[A-Z0-9]{2}', parts[1].strip()) else None
        iata_of[icao] = iata
        codes.add(icao)
        if iata:
            codes.add(iata)
        w = name.split()
        variants = {name}
        while len(w) > 2 and w[-1].lower().strip(',') in GENERIC_NAME:
            w = w[:-1]
            variants.add(' '.join(w))
        for x in variants:
            if x:
                names.setdefault(x.lower(), set()).add((icao, iata))
    try:
        A = json.load(open(os.path.join(SHA3D, 'data', 'sha_sim_inputs.json'), encoding='utf-8')).get('airlines') or {}
        for icao, v in A.items():
            if isinstance(v, dict) and v.get('short'):
                names.setdefault(v['short'].lower(), set()).add((icao, iata_of.get(icao)))
    except (OSError, ValueError):
        pass
    return names, codes


def add_fingerprints(I, b, label):
    """sha256 / sha1 / md5 / sha512 hex, the git blob id, and the base64 (standard and URL-safe, SRI style) sha256 / sha384 /
    sha512 / sha1 digests of bytes b (round 3, F26): hex prefixes >= FP_MIN, base64 prefixes >= 16"""
    hx = [hashlib.sha256(b).hexdigest(), hashlib.sha1(b).hexdigest(), hashlib.md5(b).hexdigest(), hashlib.sha512(b).hexdigest(),
          hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()]
    for h in hx:
        I.v['fingerprint'].update(h[:k] for k in range(FP_MIN, len(h) + 1))
    for alg in ('sha256', 'sha384', 'sha512', 'sha1'):
        dg = hashlib.new(alg, b).digest()
        for enc in (base64.b64encode, base64.urlsafe_b64encode):
            e = enc(dg).decode().rstrip('=')
            I.b64fp.update(e[:k] for k in range(16, len(e) + 1))
    I.fp_sources[label] = I.fp_sources.get(label, 0) + 1


LOCAL_FP = os.path.join(SHA3D, 'out', 'phase3', 'local', 'fingerprints.json')


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
    d, suf = re.match(r'(\d+)(\D*)$', m.group(2)).groups()
    # as written, without leading zeros, and zero-padded to 3 and 4 digits (timetables / SSIM write 'MU0nnn'; round 4, N2)
    return sorted({iata + x + suf for x in (d, d.lstrip('0') or '0', d.zfill(3), d.zfill(4)) if len(x) <= 4})


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
        self.al_names, self.al_codes = {}, set()     # airline name (lower case) -> {(ICAO, IATA)}; designators (round 3)
        self.b64fp = set()                          # base64 digests of the local files (SRI style), prefixes >= 16 (round 3)
        self.fp_sources = {}                        # counts of the fingerprint sources (printed)
        self.addr_dropped = 0                       # 24-bit values below 0x004000 or ffffff (no aircraft address; round 4)
        self.loaded = {}                            # {local file (relative): how it was loaded} (round 4, N1)

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
            if HEX6.match(a) and a != 'ffffff' and int(a, 16) >= 0x4000:
                self.v[cls].add(a)                   # round 4 (F27): 000000-003fff is no state's ICAO block (placeholders,
            elif HEX6.match(a):                      # small counts such as "'address': 1"), ffffff a placeholder
                self.addr_dropped += 1
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


class IdentitySetError(Exception):
    """the identity set is incomplete (round 4, N1): the audit refuses to run (exit 1) rather than compare with a partial set"""


# the roles of the files of refs/cache/observed_elsewhere/ (round 4, N1): identity TABLES are parsed by structure; the other
# local files (the owner sample's README, the spot checks, the scan logs) are read as FREE TEXT for designators,
# registrations and addresses; a file of any other kind is an ERROR (the audit does not know what it holds)
ROLE_RX = (('day table', re.compile(r'^sha_observed_\d{4}-\d{2}-\d{2}\.json$')),
           ('csv table', re.compile(r'^[^/]+\.csv$')),
           ('scan table', re.compile(r'^scan/cs_[^/]+\.json\.gz$')),
           ('free text', re.compile(r'^(?:README[^/]*\.md|spot_checks[^/]*\.md|scan/scan_[^/]+\.log)$')))
REQUIRED = ('callsign', 'flight', 'registration', 'address', 't_sha', 'ftime', 'uid', 'fingerprint')
FT_REG = re.compile(r'(?<![\w-])(B-\d{4}|B-\d{3}[A-Z]|B-\d{2}[A-Z]{2}|B-\d[A-Z]{2,3}|B-[A-Z]{3}|[A-Z]{1,2}-[A-Z0-9]{3,5})(?![\w-])')
FT_CS = re.compile(r'(?<![\w])([A-Z]{3})[ ]?(\d{1,4}[A-Z]?)(?![\w])')
FT_FL = re.compile(r'(?<![\w])([A-Z][A-Z0-9]|[0-9][A-Z])[ ]?(\d{1,4}[A-Z]?)(?![\w])')
FT_ADDR = re.compile(r'(?i)(?:icao|hex|addr)\w*\W{1,4}([0-9a-f]{6})(?![0-9a-f])')


def load_day_table(I, p, AL):
    d = json.load(open(p, encoding='utf-8'))
    day = d.get('day') or (re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(p)) or [None, None])[1]
    mv = d.get('movements') or []
    for i, m in enumerate(mv):
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
    return len(mv)


def load_csv_table(I, p, AL):
    n = 0
    with open(p, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            n += 1
            cs = row.get('callsign')
            I.add('callsign', cs)
            for fl in flight_of(cs, AL):
                I.add('flight', fl)
            I.add('registration', row.get('registration'))
            I.add('address', row.get('icao24'))
            for m in DTX.finditer(row.get('sha_time_utc_inf') or ''):
                if m.group('s') is not None:
                    I.add('t_sha', dt_epochs(m, utc_default=True)[0])
    return n


def load_scan_table(I, p, AL):
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        d = json.load(f)
    fl = d.get('flights') or []
    for x in fl:
        I.add('callsign', x.get('cs'))
        for y in flight_of(x.get('cs'), AL):
            I.add('flight', y)
        I.add('registration', x.get('r'))
        I.add('address', x.get('icao'))
    return len(fl)


def load_free_text(I, p, AL):
    """designators + numbers (an ICAO prefix of data/lookup.js AIRLINES: a callsign; an IATA prefix: a flight number, also
    with a space), registrations and addresses after an address keyword, from a local file that is not a table"""
    t = open(p, encoding='utf-8', errors='replace').read()
    iatas = {v.split('|')[1].strip() for v in AL.values() if isinstance(v, str) and '|' in v}
    n = 0
    for m in FT_REG.finditer(t):
        I.add('registration', m.group(1))
        n += 1
    for m in FT_CS.finditer(t):
        if m.group(1) in AL:
            cs = m.group(1) + m.group(2)
            I.add('callsign', cs)
            for f in flight_of(cs, AL):
                I.add('flight', f)
            n += 1
    for m in FT_FL.finditer(t):
        if m.group(1) in iatas:
            dg, suf = re.match(r'(\d+)(\D*)$', m.group(2)).groups()
            for x in {dg, dg.lstrip('0') or '0', dg.zfill(3), dg.zfill(4)}:
                if len(x) <= 4:
                    I.add('flight', m.group(1) + x + suf)
            n += 1
    for m in FT_ADDR.finditer(t):
        I.add('address', m.group(1))
        n += 1
    return n


LOADERS = {'day table': load_day_table, 'csv table': load_csv_table, 'scan table': load_scan_table, 'free text': load_free_text}


def load_identities(obs=None):
    """the identity set from the local observed-elsewhere directory. Fail-closed (round 4, N1): IdentitySetError (exit 1)
    unless SOURCES.json exists and lists files, every listed file exists, every file has a known role and was loaded,
    every identity table matches its SOURCES.json size and sha256 and holds records, and every class is non-empty"""
    obs = obs or OBS
    I = IdSet()
    AL = airlines()
    I.al_names, I.al_codes = airline_names(AL)
    I.taxi = taxi_offsets()
    problems, notes = [], []
    if not os.path.isdir(obs):
        raise IdentitySetError('no local refs/cache/observed_elsewhere directory (the audit is a local tool and needs the '
                               'local identity set)')
    if not AL:
        problems.append('data/lookup.js AIRLINES could not be read (no flight numbers, no airline names)')
    if not I.taxi:
        problems.append('data/sha_sim_inputs.json params.taxi could not be read (no tier-2 block times)')
    try:
        src = json.load(open(os.path.join(obs, 'SOURCES.json'), encoding='utf-8'))
        listed = src.get('files') if isinstance(src, dict) else None
        if not isinstance(listed, dict) or not listed:
            problems.append('SOURCES.json lists no files')
            listed = {}
    except (OSError, ValueError) as e:
        problems.append(f'SOURCES.json could not be read ({type(e).__name__})')
        listed = {}
    on_disk = sorted(os.path.relpath(p, obs).replace(os.sep, '/') for p in glob.glob(os.path.join(obs, '**', '*'), recursive=True)
                     if os.path.isfile(p) and os.path.relpath(p, obs) != 'SOURCES.json')
    missing = [r for r in listed if r not in on_disk]
    if missing:
        problems.append(f'{len(missing)} file(s) listed in SOURCES.json are missing')
    unknown, unlisted, rec = 0, 0, {}
    for rel in on_disk:
        role = next((name for name, rx in ROLE_RX if rx.match(rel)), None)
        if role is None:
            unknown += 1
            continue
        p = os.path.join(obs, rel)
        b = open(p, 'rb').read()
        meta = listed.get(rel)
        if meta is None:
            unlisted += 1
        elif not isinstance(meta, dict) or meta.get('bytes') != len(b) or meta.get('sha256') != hashlib.sha256(b).hexdigest():
            (problems if role != 'free text' else notes).append(f'{role} {rel} differs from its SOURCES.json size / sha256')
        try:
            n = LOADERS[role](I, p, AL)
        except Exception as e:
            problems.append(f'{role} {rel} could not be read ({type(e).__name__})')
            continue
        I.files += role != 'free text'
        I.loaded[rel] = role
        rec[role] = rec.get(role, 0) + n
        if n == 0 and role != 'free text':
            problems.append(f'{role} {rel} holds no records')
    if unknown:
        problems.append(f'{unknown} local file(s) of an unknown kind (not loaded; the audit does not know what they hold)')
    not_loaded = [r for r in listed if r in on_disk and r not in I.loaded]
    if not_loaded:
        problems.append(f'{len(not_loaded)} listed file(s) were not loaded')
    if not any(r == 'day table' for r in I.loaded.values()):
        problems.append('no day table sha_observed_<day>.json')
    # fingerprints (round 2, F20; round 3, F26): of every local file, of the overlay of every day table (the
    # observed_overlay.py output as printed and as canonical JSON) and the local plan hashes that tools/sim/test_plan.mjs
    # records in out/phase3/local/fingerprints.json (a committed hash would confirm a byte-exact reconstruction)
    for rel in on_disk + ['SOURCES.json']:
        p = os.path.join(obs, rel)
        if os.path.isfile(p):
            add_fingerprints(I, open(p, 'rb').read(), 'local file')
    overlay = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(obs))), 'tools', 'sim', 'observed_overlay.py')
    for rel in [r for r, k in I.loaded.items() if k == 'day table']:
        day = re.search(r'(\d{4}-\d{2}-\d{2})', rel).group(1)
        r = subprocess.run([sys.executable, '-I', overlay, '--day', day], capture_output=True)
        if r.returncode:
            problems.append(f'tools/sim/observed_overlay.py --day {day} failed (exit {r.returncode}): no overlay fingerprints')
            continue
        ov = json.loads(r.stdout)
        for b in {r.stdout, r.stdout.rstrip(b'\n'), json.dumps(ov, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode(),
                  json.dumps(ov, sort_keys=True, separators=(',', ':')).encode(),
                  json.dumps(ov, separators=(',', ':'), ensure_ascii=False).encode(), json.dumps(ov, indent=2).encode()}:
            add_fingerprints(I, b, 'overlay digest')
    lfp = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(obs))), 'out', 'phase3', 'local', 'fingerprints.json')
    try:
        L = json.load(open(lfp, encoding='utf-8'))
        for h in (L.get('hashes') or {}).values():
            if isinstance(h, str) and re.fullmatch(r'[0-9a-f]{8,128}', h):
                I.v['fingerprint'].update(h[:k] for k in range(FP_MIN, len(h) + 1))
                I.fp_sources['local plan hash'] = I.fp_sources.get('local plan hash', 0) + 1
    except (OSError, ValueError, AttributeError):
        notes.append('no local plan hashes recorded (run node tools/sim/test_plan.mjs, which writes out/phase3/local/'
                     'fingerprints.json)')
    I.finish()
    empty = [c for c in REQUIRED if not I.v[c]]
    if empty:
        problems.append('empty class(es): ' + ', '.join(empty))
    I.summary = (f'local files: {len(listed)} listed in SOURCES.json, {len(on_disk)} on disk; loaded {len(I.loaded)} '
                 f'({", ".join(f"{k} {sum(1 for v in I.loaded.values() if v == k)}" for k, _ in ROLE_RX)}; records '
                 + ', '.join(f'{k} {v}' for k, v in rec.items()) + f'); unlisted {unlisted}; addresses dropped as no '
                 f'aircraft address (< 0x004000, ffffff) {I.addr_dropped}')
    I.notes = notes
    if problems:
        raise IdentitySetError('; '.join(problems))
    return I


def dt_epochs(m, utc_default=False):
    """a DTX / ISO_COMPACT match -> the epoch seconds it can mean: as written with a zone, else as UTC and as UTC+8 local
    (a numeric DD/MM/YYYY date in both readings)"""
    g = m if isinstance(m, dict) else m.groupdict()
    h, mi = int(g['h']), int(g['mi'])
    s = int(g['s']) if g.get('s') is not None else 0
    ap = g.get('ap')
    if ap:                                           # 12-hour clock (round 4, N2): 12 AM = 0 h, 12 PM = 12 h
        if not 1 <= h <= 12:
            return []
        h = h % 12 + (12 if ap[0] in 'Pp' else 0)
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
    elif g.get('y5'):
        dates.append((int(g['y5']), MONTHS[g['mon5'][:3].lower()], int(g['d5'])))
    offs = zone_offsets(g.get('z2') or g.get('z'))
    out = []
    for y, mo, d in dates:
        try:
            naive = int(dt.datetime(y, mo, d, h, mi, s, tzinfo=dt.timezone.utc).timestamp())
        except ValueError:
            continue
        if offs is None:
            out += [naive] if utc_default else [naive, naive - LOCAL_S]
            continue
        for off in offs:
            if off is None:
                out += [naive, naive - LOCAL_S]
            else:
                out.append(naive - off)
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
def cache_status(path, reader=None):
    """None (not a refs/cache path) | 'identity-source' | 'not-redistributable' | 'redistributable' (scanned normally).
    reader(path of a SOURCES.json) -> bytes | None: the work tree by default; the index in --staged (round 3: a SOURCES.json
    that is not in the index does not count)"""
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
        d = read_sources(sp, reader)
        if d is None:
            continue
        r = d.get('redistributable') if isinstance(d, dict) else None
        ok = r is True or (isinstance(r, str) and r.strip().lower().startswith('yes'))
        return 'redistributable' if ok else 'not-redistributable'
    return 'not-redistributable'


def file_reader(root=REPO):
    def rd(sp):
        ap = sp if os.path.isabs(sp) else os.path.join(root, sp)
        try:
            return open(ap, 'rb').read()
        except OSError:
            return None
    return rd


def read_sources(sp, reader=None):
    b = (reader or file_reader())(sp)               # a GitError of the index reader propagates: ERROR (exit 1)
    if b is None:
        return None
    try:
        return json.loads(b.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return None


# ------------------------------------------------------------------------------------------------ text extraction
PNG_IMAGE = {b'IHDR', b'PLTE', b'IDAT', b'IEND', b'tRNS', b'cHRM', b'gAMA', b'sBIT', b'sRGB', b'bKGD', b'hIST', b'pHYs', b'tIME',
             b'acTL', b'fcTL', b'fdAT', b'cICP', b'mDCv', b'cLLi', b'oFFs', b'sTER', b'gIFg'}   # no text (pixels, numbers)
PNG_TEXTISH = {b'sPLT', b'pCAL', b'sCAL', b'gIFx', b'gIFt'}          # standard chunks that can carry a name / text


def png_text(b, X=None, depth=0):
    """-> (text, [REVIEW reasons]) of a PNG: tEXt / zTXt / iTXt / eXIf / iCCP read; the other standard chunks that can
    carry text as strings; every unknown (private) chunk as strings and zlib-inflated strings AND a REVIEW; bytes after
    IEND likewise (round 3, F24); a truncated chunk is a REVIEW"""
    out, why = [], []
    i = 8
    while i + 8 <= len(b):
        n, typ = struct.unpack('>I4s', b[i:i + 8])
        if i + 12 + n > len(b):
            why.append('truncated PNG chunk')
            out.append(strings(b[i:]))
            i = len(b)
            break
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
            elif typ == b'eXIf':                     # an Exif TIFF structure (round 4, N3: every tag, UTF-16)
                r = tiff_parse(data[6:] if data.startswith(b'Exif\x00\x00') else data, X or Extract(), depth)
                out += [r[0]] if r else [strings(data), strings_utf16(data)]
                why += r[1] if r else ['an unreadable PNG eXIf chunk']
            elif typ == b'iCCP':
                k, rest = data.split(b'\x00', 1)
                out.append(k.decode('latin-1') + '\n' + strings(zlib.decompress(rest[1:])))
            elif typ in PNG_TEXTISH:
                out.append(strings(data))
            elif typ not in PNG_IMAGE:
                why.append(f'unknown PNG chunk {typ.decode("latin-1")!r}')
                out.append(strings(data))
                out.append(zlib_strings(data))
        except Exception:
            out.append(strings(data))
            out.append(zlib_strings(data))
        if typ == b'IEND':
            break
    if i < len(b):
        why.append(f'{len(b) - i} bytes after the PNG IEND chunk')
        out.append(strings(b[i:]))
        out.append(zlib_strings(b[i:]))
    return '\n'.join(x for x in out if x), why


def zlib_strings(data):
    """printable strings of a zlib stream found at the start of data or after its first NUL (+1 / +2 bytes)"""
    out = []
    starts = {0}
    k = data.find(b'\x00')
    if k >= 0:
        starts |= {k + 1, k + 2}
    for st in sorted(starts):
        try:
            out.append(strings(zlib.decompressobj().decompress(data[st:], MAXBYTES)))
        except zlib.error:
            pass
    return '\n'.join(out)


def strings(b, n=4):
    return '\n'.join(m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{%d,}' % n, b))


def is_utf8(b):
    try:
        b.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def binary_bytes(seg):
    """bytes of seg that are neither printable ASCII, whitespace nor NUL (the part strings() cannot read)"""
    return len(re.sub(rb'[\x20-\x7e\t\r\n\x00]', b'', seg)) if len(seg) <= (1 << 20) else len(seg)


def num_text(vals, cap=1_000_000):
    """numbers as text for the matcher: integers as written; a float as its floor and rounding when it is epoch-like, else
    repr (round 4, N3: numeric arrays in TIFF tags, NumPy files, base64 typed arrays)"""
    out = []
    for x in vals[:cap]:
        if isinstance(x, float):
            if math.isfinite(x) and 1e8 < abs(x) < 1e14:
                out.append(f'{math.floor(x)} {int(round(x))}')
            elif math.isfinite(x):
                out.append(repr(x))
        else:
            out.append(str(x))
    return ' '.join(out)


# ---- TIFF / Exif (round 4, N3): every IFD of the chain and the Exif / GPS / Interoperability / SubIFD sub-IFDs, every field
# type (ASCII, UTF-16 XP* tags, UserComment with its character code, numbers), the strip / tile / thumbnail data claimed
# (pixels are not read: an admitted limit) and every byte not referenced by a tag read as strings and flagged REVIEW
TIFF_TYPES = {1: ('B', 1), 2: ('B', 1), 3: ('H', 2), 4: ('I', 4), 5: ('I', 8), 6: ('b', 1), 7: ('B', 1), 8: ('h', 2),
              9: ('i', 4), 10: ('i', 8), 11: ('f', 4), 12: ('d', 8), 13: ('I', 4), 16: ('Q', 8), 17: ('q', 8), 18: ('Q', 8)}
TIFF_SUBIFD = (0x8769, 0x8825, 0xA005, 0x014A)
TIFF_XP = (0x9C9B, 0x9C9C, 0x9C9D, 0x9C9E, 0x9C9F)
TIFF_DATA = ((0x111, 0x117), (0x144, 0x145), (0x201, 0x202))
EXIF_DT = re.compile(r'^(\d{4}):(\d{2}):(\d{2})([ T]\d{2}:\d{2}(?::\d{2})?)')


def tiff_value(tag, typ, cnt, v, bo):
    if typ == 2:
        t = v.rstrip(b'\x00').replace(b'\x00', b' ')
        s = t.decode('utf-8') if is_utf8(t) else t.decode('latin-1')
        m = EXIF_DT.match(s.strip())                 # Exif 'YYYY:MM:DD hh:mm:ss' also as an ISO date-time
        return s + (f'\n{m.group(1)}-{m.group(2)}-{m.group(3)}{m.group(4)}' if m else '')
    if typ in (1, 6, 7):
        out = []
        if tag in TIFF_XP:
            out.append(v.decode('utf-16-le', 'replace').replace('\x00', ' '))
        if tag == 0x9286 and len(v) >= 8:            # UserComment: an 8-byte character code, then the text
            code, body = v[:8], v[8:]
            if code.startswith(b'UNICODE'):
                out += [body.decode('utf-16-be', 'replace'), body.decode('utf-16-le', 'replace')]
            elif code.startswith(b'JIS'):
                out.append(body.decode('cp932', 'replace'))
            else:
                out.append(body.replace(b'\x00', b' ').decode('latin-1'))
        out += [strings(v), strings_utf16(v)]
        return '\n'.join(x for x in out if x)
    fmt, size = TIFF_TYPES[typ]
    k = 2 if typ in (5, 10) else 1
    vals = struct.unpack(bo + fmt * (k * cnt), v[:size * cnt]) if cnt <= 65536 else ()
    return num_text(list(vals), 8192)


def tiff_parse(b, X, depth):
    """-> (text, [REVIEW reasons]) of a classic TIFF structure (a .tif, an Exif block, a PNG eXIf chunk), None if b is none"""
    if len(b) < 8 or b[:2] not in (b'II', b'MM'):
        return None
    bo = '<' if b[:2] == b'II' else '>'
    if struct.unpack(bo + 'H', b[2:4])[0] != 42:
        return None
    out, why, claimed, todo, seen = [], [], [(0, 8)], [struct.unpack(bo + 'I', b[4:8])[0]], set()
    while todo:
        off = todo.pop()
        if not off or off in seen:
            continue
        seen.add(off)
        if len(seen) > 2000:
            why.append('more than 2000 TIFF IFDs')
            break
        if off + 2 > len(b):
            why.append('a TIFF IFD offset outside the data')
            continue
        n = struct.unpack(bo + 'H', b[off:off + 2])[0]
        end = off + 2 + 12 * n + 4
        if end > len(b):
            why.append('a truncated TIFF IFD')
            out.append(strings(b[off:]))
            continue
        claimed.append((off, end))
        tags = {}
        for k in range(n):
            e = off + 2 + 12 * k
            tag, typ, cnt = struct.unpack(bo + 'HHI', b[e:e + 8])
            if typ not in TIFF_TYPES:
                why.append(f'unknown TIFF field type {typ}')
                continue
            nb = TIFF_TYPES[typ][1] * cnt
            if nb <= 4:
                v = b[e + 8:e + 8 + nb]
            else:
                vo = struct.unpack(bo + 'I', b[e + 8:e + 12])[0]
                if vo + nb > len(b):
                    why.append('a TIFF field value outside the data')
                    continue
                v = b[vo:vo + nb]
                claimed.append((vo, vo + nb))
            tags[tag] = (typ, cnt, v)
            out.append(tiff_value(tag, typ, cnt, v, bo))
            if tag in TIFF_SUBIFD and typ in (4, 13) and cnt <= 4096:
                todo += list(struct.unpack(bo + 'I' * cnt, v))
        if 0x1D in tags and 0x07 in tags and tags[0x07][0] == 5:        # GPS date stamp + time stamp -> ISO UTC
            r = struct.unpack(bo + 'I' * 6, tags[0x07][2][:24])
            hms = [r[2 * i] // max(1, r[2 * i + 1]) for i in range(3)]
            ds = tags[0x1D][2].rstrip(b'\x00').decode('latin-1').replace(':', '-')
            out.append(f'{ds} {hms[0]:02d}:{hms[1]:02d}:{hms[2]:02d}Z')
        for ot, ct in TIFF_DATA:
            if ot in tags and ct in tags:
                o = struct.unpack(bo + TIFF_TYPES[tags[ot][0]][0] * tags[ot][1], tags[ot][2])
                c = struct.unpack(bo + TIFF_TYPES[tags[ct][0]][0] * tags[ct][1], tags[ct][2])
                for oo, cc in zip(o, c):
                    claimed.append((oo, oo + cc))
                    if ot == 0x201:
                        extract('exif-thumbnail', b[oo:oo + cc], X, depth + 1)
        todo.append(struct.unpack(bo + 'I', b[end - 4:end])[0])
    pos = 0
    for s, e in sorted(claimed) + [(len(b), len(b))]:
        if s > pos + 3:                              # a gap of 4 bytes or more: not referenced by any tag
            seg = b[pos:s]
            if seg.strip(b'\x00'):
                out += [strings(seg), strings_utf16(seg), zlib_strings(seg)]
                if binary_bytes(seg) >= 64:
                    why.append(f'{len(seg)} bytes of the TIFF structure not referenced by any tag')
        pos = max(pos, e)
    return '\n'.join(x for x in out if x), why


# ---- JPEG (round 4, N3): every marker segment before AND after the scans (to EOI), Exif through tiff_parse, XMP, COM; the
# entropy-coded data is pixels (not read); bytes after EOI: a further JPEG (MPO) is extracted, anything else is read as
# strings and flagged REVIEW
def jpeg_segment(mk, seg, X, out, why, depth):
    if mk == 0xE1 and seg.startswith(b'Exif\x00'):
        r = tiff_parse(seg[6:], X, depth)
        if r is None:
            out += [strings(seg), strings_utf16(seg)]
            why.append('an unreadable JPEG Exif segment')
        else:
            out.append(r[0])
            why += r[1]
    elif mk == 0xE1 and seg.startswith(b'http://ns.adobe.com/'):
        t = seg.decode('utf-8', 'replace')
        out += [t, re.sub(r'<[^<>]{0,4000}>', '', t)]
    elif mk == 0xFE:
        out.append(seg.decode('utf-8') if is_utf8(seg) else seg.decode('latin-1'))
    else:
        out += [strings(seg), strings_utf16(seg)]


def jpeg_parse(b, X, depth, carve=False):
    """-> (text, [REVIEW reasons], end offset) of a JPEG"""
    out, why, i, n, eoi = [], [], 2, len(b), None
    while i + 1 < n:
        if b[i] != 0xFF:
            why.append('unexpected bytes between JPEG segments')
            out += [strings(b[i:]), strings_utf16(b[i:])]
            break
        mk = b[i + 1]
        if mk == 0xFF:
            i += 1
            continue
        if mk in (0xD8, 0x01) or 0xD0 <= mk <= 0xD7:
            i += 2
            continue
        if mk == 0xD9:
            eoi = i + 2
            break
        if i + 4 > n:
            why.append('a truncated JPEG')
            break
        L = struct.unpack('>H', b[i + 2:i + 4])[0]
        if i + 2 + L > n:
            why.append('a truncated JPEG segment')
        seg = b[i + 4:i + 2 + L]
        if 0xE0 <= mk <= 0xEF or mk == 0xFE:
            jpeg_segment(mk, seg, X, out, why, depth)
        i += 2 + L
        if mk == 0xDA:                               # entropy-coded data up to the next marker
            j = i
            while True:
                j = b.find(b'\xff', j)
                if j < 0 or j + 1 >= n:
                    j = n
                    break
                nx = b[j + 1]
                if nx == 0x00 or 0xD0 <= nx <= 0xD7:
                    j += 2
                    continue
                if nx == 0xFF:
                    j += 1
                    continue
                break
            i = j
    if eoi is None:
        why.append('no JPEG EOI marker')
        return '\n'.join(x for x in out if x), why, n
    tail = b[eoi:]
    if tail and not carve:
        if tail.startswith(b'\xff\xd8\xff'):
            extract('jpeg-trailer', tail, X, depth + 1)
        elif tail.strip(b'\x00\xff \t\r\n'):
            why.append(f'{len(tail)} bytes after the JPEG EOI marker')
            out += [strings(tail), strings_utf16(tail), zlib_strings(tail)]
    return '\n'.join(x for x in out if x), why, eoi


def png_end(b, off=0):
    """the offset after the IEND chunk of a PNG starting at off, or None"""
    i = off + 8
    while i + 12 <= len(b):
        n, typ = struct.unpack('>I4s', b[i:i + 8])
        i += 12 + n
        if typ == b'IEND':
            return i if i <= len(b) else None
    return None


def gif_parse(b):
    """-> (text, [REVIEW reasons]) of a GIF: comment, plain-text and application extensions read; image data is pixels"""
    out, why, i = [], [], 13
    try:
        if b[10] & 0x80:
            i += 3 * (2 << (b[10] & 7))
        while True:
            c = b[i]
            if c == 0x3B:
                i += 1
                break
            if c == 0x21:
                label, i, data = b[i + 1], i + 2, bytearray()
                while b[i]:
                    data += b[i + 1:i + 1 + b[i]]
                    i += 1 + b[i]
                i += 1
                if label in (0xFE, 0x01, 0xFF):
                    d = bytes(data)
                    out += [d.decode('utf-8') if is_utf8(d) else d.decode('latin-1'), strings(d)]
                elif label != 0xF9:
                    why.append(f'an unknown GIF extension 0x{label:02x}')
                    out.append(strings(bytes(data)))
            elif c == 0x2C:
                fl = b[i + 9]
                i += 10 + (3 * (2 << (fl & 7)) if fl & 0x80 else 0) + 1
                while b[i]:
                    i += 1 + b[i]
                i += 1
            else:
                why.append('a damaged GIF block')
                out.append(strings(b[i:]))
                i = len(b)
                break
    except IndexError:
        why.append('a truncated GIF')
        out.append(strings(b))
        i = len(b)
    if b[i:].strip(b'\x00'):
        why.append(f'{len(b) - i} bytes after the GIF trailer')
        out += [strings(b[i:]), zlib_strings(b[i:])]
    return '\n'.join(x for x in out if x), why


def webp_parse(b, X, depth):
    out, why = [], []
    end = min(len(b), 8 + struct.unpack('<I', b[4:8])[0])
    i = 12
    while i + 8 <= end:
        typ, n = b[i:i + 4], struct.unpack('<I', b[i + 4:i + 8])[0]
        data = b[i + 8:i + 8 + n]
        i += 8 + n + (n & 1)
        if typ == b'EXIF':
            r = tiff_parse(data[6:] if data.startswith(b'Exif\x00\x00') else data, X, depth)
            out.append(r[0] if r else strings(data))
            why += r[1] if r else ['an unreadable WebP EXIF chunk']
        elif typ == b'XMP ':
            out.append(data.decode('utf-8', 'replace'))
        elif typ == b'ICCP':
            out += [strings(data), strings_utf16(data)]
        elif typ not in (b'VP8 ', b'VP8L', b'VP8X', b'ALPH', b'ANIM', b'ANMF'):
            why.append(f'an unknown WebP chunk {typ.decode("latin-1")!r}')
            out += [strings(data), zlib_strings(data)]
    if b[end:].strip(b'\x00'):
        why.append(f'{len(b) - end} bytes after the WebP RIFF data')
        out.append(strings(b[end:]))
    return '\n'.join(x for x in out if x), why


NPY_FMT = {('f', 4): 'f', ('f', 8): 'd', ('i', 1): 'b', ('i', 2): 'h', ('i', 4): 'i', ('i', 8): 'q', ('u', 1): 'B', ('u', 2): 'H',
           ('u', 4): 'I', ('u', 8): 'Q', ('b', 1): '?'}
NPY_UNIT = {'s': 1, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9, 'm': 60, 'h': 3600, 'D': 86400}


def npy_parse(b):
    """-> (text, [REVIEW reasons]) of a NumPy .npy: the header, numeric values (datetime64 converted to epoch s), strings"""
    major = b[6]
    hs, hl = (10, struct.unpack('<H', b[8:10])[0]) if major == 1 else (12, struct.unpack('<I', b[8:12])[0])
    head = b[hs:hs + hl].decode('latin-1')
    data = b[hs + hl:]
    m = re.search(r"'descr':\s*'([<>|=])([a-zA-Z])(\d+)(?:\[(\w+)\])?'", head)
    if not m:
        return head + '\n' + strings(data), ['a NumPy array of a structured or object dtype']
    bo, kind, size, unit = m.group(1), m.group(2), int(m.group(3)), m.group(4)
    end = '>' if bo == '>' else '<'
    cnt = min(len(data) // max(size, 1), 1_000_000)
    if (kind, size) in NPY_FMT:
        return head + '\n' + num_text(list(struct.unpack(end + NPY_FMT[(kind, size)] * cnt, data[:cnt * size]))), []
    if kind in 'Mm' and size == 8:
        vals = struct.unpack(end + 'q' * cnt, data[:cnt * 8])
        f = NPY_UNIT.get(unit or 's', 1)
        return head + '\n' + num_text([float(v) * f for v in vals]), []
    if kind == 'U':
        return head + '\n' + data.decode('utf-32-be' if bo == '>' else 'utf-32-le', 'replace').replace('\x00', ' '), []
    if kind == 'S':
        return head + '\n' + data.replace(b'\x00', b' ').decode('latin-1'), []
    return head + '\n' + strings(data), [f'a NumPy dtype {kind}{size} not read']


def sqlite_text(b):
    """the SQL dump of a SQLite database (Python sqlite3 deserialize); free pages and deleted rows are not read (REVIEW)"""
    import sqlite3
    con = sqlite3.connect(':memory:')
    try:
        con.deserialize(b)
        return '\n'.join(con.iterdump())
    finally:
        con.close()


def glb_parse(b, X, depth):
    """glTF binary (round 4, N3): the JSON chunk as text (base64 data URIs expanded), the BIN chunk as strings and every
    image it holds (bufferViews, else PNG / JPEG signatures) extracted; an unknown chunk or trailing bytes is REVIEW"""
    total = struct.unpack('<I', b[8:12])[0]
    i, js, binc = 12, None, None
    while i + 8 <= min(total, len(b)):
        n, typ = struct.unpack('<I4s', b[i:i + 8])
        data = b[i + 8:i + 8 + n]
        i += 8 + n
        if typ == b'JSON':
            js = data.decode('utf-8', 'replace')
            X.parts.append(js)
            b64_expand(js, X, depth)
        elif typ == b'BIN\x00':
            binc = data
            X.parts += [strings(data), strings_utf16(data)]
        else:
            X.opaque.append(f'an unknown glTF chunk {typ.decode("latin-1")!r}')
            X.parts += [strings(data), strings_utf16(data), zlib_strings(data)]
    if b[i:].strip(b'\x00 '):
        X.opaque.append(f'{len(b) - i} bytes after the glTF chunks')
        X.parts.append(strings(b[i:]))
    if binc is None:
        return
    done = set()
    try:
        G = json.loads(js or '{}')
        for img in G.get('images') or []:
            bv = img.get('bufferView') if isinstance(img, dict) else None
            if isinstance(bv, int) and bv < len(G.get('bufferViews') or []):
                v = G['bufferViews'][bv]
                if v.get('buffer', 0) == 0:
                    o = v.get('byteOffset', 0)
                    extract('gltf-image', binc[o:o + v['byteLength']], X, depth + 1)
                    done.add(o)
    except (ValueError, KeyError, TypeError, AttributeError):
        pass
    for m in re.finditer(rb'\x89PNG\r\n\x1a\n', binc):                   # images not reached through a bufferView
        if m.start() not in done:
            e = png_end(binc, m.start())
            extract('gltf-image', binc[m.start():e or len(binc)], X, depth + 1)
    for m in re.finditer(rb'\xff\xd8\xff[\xe0-\xef\xdb\xfe]', binc):
        if m.start() not in done:
            t, why, _ = jpeg_parse(binc[m.start():], X, depth + 1, carve=True)
            X.parts.append(t)
            X.opaque += why


def gunzip(name, b, X, depth):
    """every member of a gzip file with its header fields (round 4, N3): FNAME (an original file name: scanned like a member
    name), FCOMMENT, FEXTRA; bytes after the last member are REVIEW"""
    i, outs = 0, []
    while i + 10 <= len(b) and b[i:i + 2] == b'\x1f\x8b':
        flg, j = b[i + 3], i + 10
        if flg & 4:
            xl = struct.unpack('<H', b[j:j + 2])[0]
            X.parts.append(strings(b[j + 2:j + 2 + xl]))
            j += 2 + xl
        for bit in (8, 16):
            if flg & bit:
                k = b.index(b'\x00', j)
                s = b[j:k].decode('latin-1')
                X.parts.append(s)
                if bit == 8 and IDENT_NAME.search(s.replace('\\', '/')):
                    X.forbidden += 1
                j = k + 1
        if flg & 2:
            j += 2
        d = zlib.decompressobj(-15)
        outs.append(d.decompress(b[j:], MAXBYTES))
        if not d.eof:
            raise ValueError('truncated gzip member')
        i = len(b) - len(d.unused_data) + 8
    rest = b[i:]
    if rest.strip(b'\x00'):
        X.opaque.append(f'{len(rest)} bytes after the gzip data')
        X.parts += [strings(rest), zlib_strings(rest)]
    return b''.join(outs)


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
            t, why = png_text(b, X, depth)
            X.kinds.append('png-text'); X.parts.append(t); X.opaque += why; return
        if b[:2] == b'\x1f\x8b':
            X.kinds.append('gzip'); extract(name[:-3] if name.endswith('.gz') else name, gunzip(name, b, X, depth), X, depth + 1); return
        if b[:3] == b'BZh' and len(b) > 10 and b[4:10] == b'\x31\x41\x59\x26\x53\x59':
            X.kinds.append('bz2'); extract(name, bz2.decompress(b), X, depth + 1); return
        if b[:6] == b'\xfd7zXZ\x00':
            X.kinds.append('xz'); extract(name, lzma.decompress(b), X, depth + 1); return
        if b[:4] in (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'):
            X.kinds.append('zip')
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                if z.comment:                        # the archive comment and every member comment / extra field (round 4)
                    X.parts.append(z.comment.decode('utf-8', 'replace'))
                for info in z.infolist():
                    X.parts += [info.comment.decode('utf-8', 'replace') if info.comment else '', strings(info.extra)]
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
                X.parts.append('\n'.join(f'{k} {v}' for k, v in (t.pax_headers or {}).items()))
                for ti in t.getmembers():            # pax headers, link targets, owner names (round 4)
                    X.parts += ['\n'.join(f'{k} {v}' for k, v in (ti.pax_headers or {}).items()), ti.linkname, ti.uname, ti.gname]
                    if ti.isfile():
                        member(ti.name, t.extractfile(ti).read())
                    else:
                        X.parts.append(ti.name)
            return
        if b[:5] == b'%PDF-':
            X.kinds.append('pdf'); pdf_text(b, X, depth); return
        if b[:3] == b'\xff\xd8\xff':
            t, why, _ = jpeg_parse(b, X, depth)
            X.kinds.append('jpeg'); X.parts.append(t); X.opaque += why; return
        if b[:4] in (b'II*\x00', b'MM\x00*'):
            r = tiff_parse(b, X, depth)
            if r is not None:
                X.kinds.append('tiff'); X.parts.append(r[0]); X.opaque += r[1]; return
        if b[:4] == b'glTF' and len(b) >= 20:
            X.kinds.append('gltf'); glb_parse(b, X, depth); return
        if b[:6] in (b'GIF87a', b'GIF89a'):
            t, why = gif_parse(b)
            X.kinds.append('gif'); X.parts.append(t); X.opaque += why; return
        if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
            t, why = webp_parse(b, X, depth)
            X.kinds.append('webp'); X.parts.append(t); X.opaque += why; return
        if b[:6] == b'\x93NUMPY':
            t, why = npy_parse(b)
            X.kinds.append('npy'); X.parts.append(t); X.opaque += why; return
        if b[:16] == b'SQLite format 3\x00':
            X.kinds.append('sqlite')
            X.opaque.append('a SQLite database (free pages and deleted rows are not read)')
            X.parts += [strings(b), strings_utf16(b)]
            X.parts.append(sqlite_text(b))
            return
    except Exception as e:                           # a damaged container: what could be read is kept, the rest is REVIEW
        X.opaque.append(f'damaged or unreadable {X.kinds[-1] if X.kinds else "container"} ({type(e).__name__})')
        X.parts.append(strings(b))
        X.parts.append(strings_utf16(b))
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
    if name.lower().endswith(XML_EXT) or txt.lstrip('﻿ \t\r\n')[:1] == '<':
        X.parts.append(re.sub(r'<[^<>]{0,4000}>', '', txt))   # XML / HTML / SVG / OOXML: also the text with the tags removed
    if 'glyphshow' in txt:
        X.parts.append(ps_glyph_text(txt))           # PostScript / EPS text drawn glyph by glyph (matplotlib; round 4)
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
    """printable ASCII runs in UTF-16, little- and big-endian (round 4: BE for ICC 'mluc' tags, PDF strings, XP tags)"""
    le = [m.group().decode('utf-16-le', 'replace') for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}' % n, b)]
    be = [m.group().decode('utf-16-be', 'replace') for m in re.finditer(rb'(?:\x00[\x20-\x7e]){%d,}' % n, b)]
    return '\n'.join(le + be)


B64 = re.compile(r'(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{8,}={0,2}(?![A-Za-z0-9+/=])')
B64ML = re.compile(r'(?<![A-Za-z0-9+/=])(?:[A-Za-z0-9+/]{40,}[ \t]*\r?\n[ \t>#*/;"\',]*)+[A-Za-z0-9+/]{4,}={0,2}(?![A-Za-z0-9+/=])')
HEXRUN = re.compile(r'(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}){16,}(?![0-9A-Fa-f])')
MAGIC = (b'\x89PNG', b'\x1f\x8b', b'PK\x03\x04', b'%PDF-', b'BZh', b'\xfd7zXZ', b'\xff\xd8\xff', b'II*\x00', b'MM\x00*', b'GIF8',
         b'RIFF', b'\x93NUMPY', b'SQLite format 3', b'glTF', b'%!PS', b'\x28\xb5\x2f\xfd', b'7z\xbc\xaf', b'Rar!')
B64_REVIEW = 64                                       # a decoded base64 run of this many bytes that no decoding reads: REVIEW


def decode_blob(label, d, X, depth, review):
    """decoded base64 / hex bytes (round 4, N3): a known container -> extract(); UTF-8 or UTF-16 text -> scanned (and its own
    base64 runs); zlib, raw deflate or gzip -> inflated and extracted; otherwise read as numeric arrays (float64 / float32 /
    int64 / int32, both byte orders: epoch-like values; base64 only) and, from `review` bytes on, flagged REVIEW"""
    if len(d) < 4:
        return
    if d.startswith(MAGIC):
        X.kinds.append(label)
        extract(label, d, X, depth + 1)
        return
    txt, kind = decode_text(d)
    if txt is not None and sum(ch.isprintable() or ch in '\n\r\t' for ch in txt) >= 0.9 * len(txt):
        X.parts.append(txt)
        b64_expand(txt, X, depth + 1)
        return
    for wbits in (15, -15, 31):
        try:
            z = zlib.decompressobj(wbits)
            out = z.decompress(d, MAXBYTES)
        except zlib.error:
            continue
        if out and z.eof:
            X.kinds.append(label + '-deflate')
            extract(label, out, X, depth + 1)
            return
    nums = []                                         # typed arrays (plotly 'bdata', JS Float64Array): base64 only
    for fmt, size in (('d', 8), ('q', 8), ('i', 4)) if label == 'base64' else ():
        if len(d) % size == 0 and len(d) <= (8 << 20):
            for bo in '<>':
                vals = struct.unpack(bo + fmt * (len(d) // size), d)
                ep = [v for v in vals if isinstance(v, (int, float)) and (1.5e9 < v < 2.2e9 or 1.5e12 < v < 2.2e12)]
                if ep:
                    nums.append(num_text(ep))
    if nums:
        X.parts.append('\n'.join(nums))
    if review is not None and len(d) >= review:
        X.opaque.append(f'a {label} run of {len(d)} bytes that is neither text nor a known format (numeric readings scanned)')


def b64_expand(txt, X, depth):
    """base64 runs (data URIs, JSON fields, MIME / PEM blocks wrapped over lines) and hex runs (bytes.hex()) inside text,
    decoded through decode_blob (round 4, N3: every decoding tried; an undecodable base64 run of >= 64 bytes is REVIEW)"""
    if depth >= MAXDEPTH:
        return
    spans = []
    for m in B64ML.finditer(txt):                     # a base64 block wrapped over lines (MIME 76, PEM 64 columns)
        ls = [re.sub(r'[^A-Za-z0-9+/=]', '', x) for x in m.group().split('\n')]
        ls = [x for x in ls if x]
        if len(ls) < 2 or len({len(x) for x in ls[:-1]}) != 1 or len(ls[-1]) > len(ls[0]):
            continue                                  # wrapped blocks have equal lines (the last one shorter)
        body = ''.join(ls).rstrip('=')
        try:
            d = base64.b64decode(body + '=' * (-len(body) % 4), validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        spans.append((m.start(), m.end()))
        decode_blob('base64', d, X, depth, B64_REVIEW)
    for m in B64.finditer(txt):
        if spans and any(a <= m.start() < b for a, b in spans):
            continue                                  # a line of a wrapped block decoded above
        r = m.group()
        body = r.rstrip('=')
        if len(body) % 4 == 1 or not (re.search(r'[A-Z]', body) and re.search(r'[a-z0-9+/]', body)):
            continue
        if re.fullmatch(r'[0-9A-Fa-f]+', body):       # a hex run (a digest): decoded as hex below, never REVIEW
            continue
        try:
            d = base64.b64decode(body + '=' * (-len(body) % 4), validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        decode_blob('base64', d, X, depth, B64_REVIEW)
    for m in HEXRUN.finditer(txt):
        decode_blob('hex', bytes.fromhex(m.group()), X, depth, None)


GLYPH_CHAR = {'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8',
              'nine': '9', 'hyphen': '-', 'minus': '-', 'endash': '-', 'emdash': '-', 'hyphentwo': '-', 'period': '.',
              'comma': ',', 'colon': ':', 'semicolon': ';', 'slash': '/', 'underscore': '_', 'space': ' ', 'parenleft': '(',
              'parenright': ')', 'plus': '+', 'numbersign': '#', 'at': '@', 'ampersand': '&', 'quotesingle': "'",
              'quotedbl': '"', 'bracketleft': '[', 'bracketright': ']', 'equal': '=', 'percent': '%', 'asterisk': '*',
              'bar': '|', 'less': '<', 'greater': '>', 'question': '?', 'exclam': '!', 'nbspace': ' ', 'uni00A0': ' '}
GLYPH = re.compile(r'(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+m\s+/([A-Za-z0-9_.]+)\s+glyphshow|/([A-Za-z0-9_.]+)\s+glyphshow')


def glyph_char(g):
    if len(g) == 1 and g.isalpha():
        return g
    if g in GLYPH_CHAR:
        return GLYPH_CHAR[g]
    m = re.fullmatch(r'uni([0-9A-Fa-f]{4})|u([0-9A-Fa-f]{4,6})', g)
    if m:
        return chr(int(m.group(1) or m.group(2), 16))
    return ''


def ps_glyph_text(txt):
    """PostScript / EPS text drawn glyph by glyph ('x y m /B glyphshow', matplotlib; round 4, N3): the glyphs of each
    gsave ... grestore block joined, without spaces and with a space where the advance is wide (a skipped space glyph)"""
    out = []
    for blk in re.split(r'\bgrestore\b', txt):
        G = [(float(m.group(1)) if m.group(1) else None, glyph_char(m.group(3) or m.group(4))) for m in GLYPH.finditer(blk)]
        if not G:
            continue
        chars = [c for _, c in G]
        out.append(''.join(chars))
        xs = [x for x, _ in G]
        if None not in xs and len(xs) > 2:
            gaps = [b - a for a, b in zip(xs, xs[1:])]
            med = sorted(gaps)[len(gaps) // 2]
            out.append(chars[0] + ''.join((' ' if gp > 1.3 * med else '') + c for gp, c in zip(gaps, chars[1:])))
    return '\n'.join(out)


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


def pdf_str_decode(bs):
    """one PDF string object -> its readings: UTF-16BE / LE by the BOM (matplotlib and reportlab write non-ASCII metadata so),
    else PDFDocEncoding (latin-1), UTF-8 and BOM-less UTF-16BE (round 4, N3)"""
    if bs[:2] == b'\xfe\xff':
        return [bs[2:].decode('utf-16-be', 'replace')]
    if bs[:2] == b'\xff\xfe':
        return [bs[2:].decode('utf-16-le', 'replace')]
    r = [bs.decode('latin-1')]
    if not bs.isascii() and is_utf8(bs):
        r.append(bs.decode('utf-8'))
    if len(bs) >= 8 and bs[0::2].count(0) > 0.3 * len(bs):
        r.append(bs[:len(bs) // 2 * 2].decode('utf-16-be', 'replace'))
    return r


def pdf_object_strings(d):
    """every literal '(...)' and hex '<...>' string of PDF object syntax (the info dictionary, outlines, annotations, form
    fields; outside content streams), decoded by pdf_str_decode (round 4, N3: a UTF-16BE hex title was missed)"""
    out = []
    for t in pdf_tokens(d):
        if t[0] == 's' and t[1]:
            out += pdf_str_decode(t[1])
    return out


def pdf_nonstream(b):
    """the PDF bytes with every stream's data cut out (object syntax only)"""
    out, pos = [], 0
    for m in re.finditer(rb'(?<!end)stream(\r\n|\n|\r)', b):
        if m.start() < pos:
            continue
        en = b.find(b'endstream', m.end())
        if en < 0:
            break
        out.append(b[pos:m.start()])
        pos = en + 9
    out.append(b[pos:])
    return b' '.join(out)


def pdf_text(b, X, depth):
    if re.search(rb'/Encrypt\b', b):
        X.opaque.append('encrypted PDF')
    X.parts.append(strings(b))                       # uncompressed objects: the info dictionary, plain streams
    X.parts.extend(pdf_object_strings(pdf_nonstream(b)))
    decoded = []
    for dtext, raw in pdf_streams(b):
        if re.search(rb'/Subtype\s*/Image', dtext):
            continue
        d = pdf_decode(dtext, raw, X)
        if d is None:
            continue
        decoded.append(d)
        if re.search(rb'/Type\s*/ObjStm', dtext):     # compressed objects (PDF 1.5+): their strings too
            X.parts.extend(pdf_object_strings(d))
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
# zero-width / invisible characters removed (round 4, N2: also the bidi marks LRM / RLM / ALM, the embeddings, overrides and
# isolates U+202A-202E / U+2066-2069, the invisible operators U+2061-2064 and the combining grapheme joiner)
ZEROW = ('​‌‍⁠﻿­᠎‎‏؜‪‫‬‭‮⁦⁧⁨⁩'
         '⁡⁢⁣⁤͏')
# Cyrillic / Greek letters that look like Latin ones (round 3: 'В-nnnn' with a Cyrillic Ve)
CONFUSABLE = dict(zip('АВЕКМНОРСТУХІЈЅаеорсуххіјѕΑΒΕΖΗΙΚΜΝΟΡΤΥΧοκν', 'ABEKMHOPCTYXIJSaeopcyxxijsABEZHIKMNOPTYXokv'))
NORM_TABLE = {**{ord(c): '-' for c in DASHES}, **{ord(c): ' ' for c in USPACES}, **{ord(c): None for c in ZEROW},
              **{ord(k): v for k, v in CONFUSABLE.items()}, 0x2028: '\n', 0x2029: '\n', 0x85: '\n'}


def normalise(t):
    """round 2, F13: decode HTML entities, JSON / JS escapes and %XX, NFKC, Unicode dashes -> '-', spaces -> ' ', zero-width
    characters removed, Cyrillic / Greek look-alikes -> Latin (round 3) (line breaks are kept, so line numbers stay close)"""
    if '&' in t:
        t = html.unescape(t)
    if '\\' in t:
        t = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), t)
        t = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), t)
        t = t.replace('\\/', '/')
    if '%' in t:
        t = re.sub(r'%(2[dD]|20|2[eE]|5[fF]|2[fF]|3[aA]|2[bB])', lambda m: chr(int(m.group(1), 16)), t)
    if not t.isascii():
        t = unicodedata.normalize('NFKC', t).translate(NORM_TABLE)
    return t


def wrap_join(txt):
    """round 3, F13: the text with every single hard line break (plus the next line's indentation and a comment / quote
    prefix '#', '//', '*', '>', '--', ';') joined to one space ('' after a hyphen) -> (joined text, joint positions in it,
    chars removed up to each joint); a blank line (paragraph break) is not joined"""
    out, jpos, cum, last, rem = [], [], [], 0, 0
    for m in JOINT.finditer(txt):
        rep = '' if txt[m.start() - 1] == '-' else ' '
        out.append(txt[last:m.start()])
        jpos.append(m.start() - rem)
        out.append(rep)
        rem += (m.end() - m.start()) - len(rep)
        cum.append(rem)
        last = m.end()
    out.append(txt[last:])
    return ''.join(out), jpos, cum


JOINT = re.compile(r'(?<=\S)[ \t]*\r?\n[ \t]*(?:(?:#|//|\*|>|--|;)[ \t]*)?(?=\S)')


def scan_text(txt, I, allow_flights=None, lines=None, norm=True, wrap=True):
    """-> ({class: n} of hits (allowed flight numbers excluded and counted under 'allowed'), allowed). `lines` (a set) gets
    the line numbers of the hits (never the values). Two passes (round 3, F13): the text as written, then the text with its
    hard line wraps joined (wrap_join), where only hits that span a joint count (no hit is counted twice)."""
    if norm:
        txt = normalise(txt)
    H, allowed = scan_hits(txt, I, allow_flights)
    if wrap and '\n' in txt:
        jt, jpos, cum = wrap_join(txt)
        if jpos:
            H2, _ = scan_hits(jt, I, allow_flights, full=False)
            for c, st, en in H2:
                k = bisect.bisect_right(jpos, st)
                if k < len(jpos) and jpos[k] < en:
                    H.append((c, st + (cum[k - 1] if k else 0), None))
    hits = {c: 0 for c in CLASSES}
    nl = [m.start() for m in re.finditer('\n', txt)] if lines is not None else None
    for c, st, _ in H:
        hits[c] += 1
        if lines is not None:
            lines.add(bisect.bisect_right(nl, st) + 1)
    return hits, allowed


def scan_hits(txt, I, allow_flights=None, full=True):
    """one matching pass over normalised text -> ([(class, start, end)], allowed); full=False (the wrap-joined pass): only
    the forms that can span a line break (run windows, date-times, airline names, address keywords); single tokens, uids,
    table rows and objects (whose pass already spans lines) are left to the first pass"""
    H = []
    box = [0]
    V = I.v
    runs = [(m.start(), m.end(), m.group()) for m in RUN.finditer(txt)]
    ftc = []                                          # ftime candidates: kept only in a per-flight context (round 3, F27)
    nr = len(runs)
    for i in range(nr):
        st0, en0, r0 = runs[i]
        # single run: addresses (also after 0x), fingerprints, epoch s / ms
        a = r0[2:] if (r0[:2] in ('0x', '0X') and len(r0) == 8) else r0
        if full and HEX6.match(a) and a.lower() in V['address'] and address_context(txt, st0, en0, a, r0):
            H.append(('address', st0, en0))
        if full and FP_MIN <= len(r0) <= 128 and r0.lower() in V['fingerprint'] and re.fullmatch(r'[0-9a-fA-F]+', r0):
            H.append(('fingerprint', st0, en0))
        if full and r0.isdigit() and len(r0) in (10, 13):
            if r0 in V['t_sha']:
                H.append(('t_sha', st0, en0))
            elif r0 in V['ftime']:
                ftc.append((st0, en0))
        # windows of 1..3 runs joined by one separator (never across a decimal point, a digit group or a date: a ' ', '.'
        # or '/' between two digits does not join); two runs in neighbouring table / CSV cells join like ' ' (round 2)
        sq, seps = '', ''
        for j in range(i, min(nr, i + MAXRUNS)):
            if j > i:
                gap = txt[runs[j - 1][1]:runs[j][0]]
                if len(gap) == 1 and gap in SEPS:
                    if gap in ' ./+' and runs[j - 1][2][-1].isdigit() and runs[j][2][0].isdigit():
                        break
                    seps += gap
                elif j == i + 1 and CELL_GAP.match(gap) and runs[i][2].isalpha() and not runs[j][2].isalpha():
                    seps += '|'                      # '| B | nnnn |', 'B,nnnn', 'B<tab>nnnn' (letters cell + number cell)
                else:
                    break
            sq += runs[j][2].upper()
            if len(sq) < 4:
                continue
            en = runs[j][1]
            nd = sum(ch.isdigit() for ch in sq)
            if nd:
                loose = any(c in ' ./|+' for c in seps)
                if loose:                    # 'MU nnnn', 'B nnnn', 'CES nnnn': capitals only, not a decimal, enough digits
                    w = txt[st0:en]
                    if w != w.upper() or (en + 1 < len(txt) and txt[en] in '.,' and txt[en + 1].isdigit()):
                        continue
                if '|' in seps:              # neighbouring cells: a registration only ('| B | nnnn |'), prefix of 1-2 letters
                    if sq in V['registration'] and nd >= 3 and len(runs[i][2]) <= 2:
                        H.append(('registration', st0, en))
                    continue
                if sq in V['registration'] and (not loose or nd >= 3):
                    H.append(('registration', st0, en))
                if sq in V['callsign'] and (not loose or nd >= 4 or (nd == 3 and not count_list(txt, st0, en))):
                    H.append(('callsign', st0, en))
                if sq in V['flight'] and (not loose or nd >= 3):
                    if allow_flights is not None and sq in allow_flights:
                        box[0] += 1
                    else:
                        H.append(('flight', st0, en))
            elif sq in I.reg_alpha:          # B-LLL: joined by '-' (any case) or one all-capitals run (not snake_case)
                if (seps and all(c == '-' for c in seps)) or (not seps and runs[j][2].isupper()):
                    H.append(('registration', st0, en))
    # date-times (round 2: more forms, any case; round 3, F13: the time before the date, compact stamps without 'T')
    for rx in (DTX, TDX, ISO_COMPACT, STAMP, STAMP_ISO, CTIME):
        for m in rx.finditer(txt):
            secs = m.group('s') is not None
            for e in dt_epochs(m):
                if secs and e in I.t_sec or not secs and e // 60 in I.t_min:
                    H.append(('t_sha', m.start(), m.end()))
                    break
                if secs and e in I.t2_sec:
                    ftc.append((m.start(), m.end()))
                    break
    H += name_hits(txt, I, allow_flights, box)        # 'China Eastern nnnn' (round 3, F13)
    H += sep_address_hits(txt, I)                     # 'icao24 hh:hh:hh', 'address 11259375' (round 3, F13)
    if not full:
        for st, en in ftc:
            if flight_context(txt, st, en, I):
                H.append(('ftime', st, en))
        return H, box[0]
    for m in UID.finditer(txt):
        if m.group(1) in V['uid']:
            H.append(('uid', m.start(), m.end()))
    H += table_hits(txt, I, allow_flights, box)       # address column, airline + number cells, date + time cells
    H += object_hits(txt, I, allow_flights, box)      # JSON / JS / Python object fields (round 3, F13)
    H += json_table_hits(txt, I, allow_flights, box)  # table-shaped JSON: pandas 'split' / 'columns', column arrays (round 4)
    for m in EXCEL.finditer(txt):                     # an Excel serial date-time, as UTC or as UTC+8 (round 3)
        e = (float(m.group(0)) - 25569.0) * 86400.0
        tol = 1 if len(m.group(2)) <= 5 else 0
        if any(round(e + z) + dd in I.t_sec for z in (0, -LOCAL_S) for dd in range(-tol, tol + 1)):
            H.append(('t_sha', m.start(), m.end()))
    if I.b64fp:                                       # base64 digests (SRI 'sha256-...'; round 3, F26)
        seen = set()
        for rx in (B64STD, B64URL):
            for m in rx.finditer(txt):
                r = re.sub(r'^sha(?:1|256|384|512)-', '', m.group()) if rx is B64URL else m.group()
                if m.end() not in seen and r in I.b64fp:
                    seen.add(m.end())
                    H.append(('fingerprint', m.start(), m.end()))
    for st, en in ftc:                                # round 3, F27
        if flight_context(txt, st, en, I):
            H.append(('ftime', st, en))
    return H, box[0]


FP_MIN = 8                                           # hex fingerprint prefixes (round 3, F26: was 12)
B64STD = re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{16,}')
B64URL = re.compile(r'(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{16,}')
EXCEL = re.compile(r'(?<![\d.])(4[5-7]\d{3})\.(\d{5,12})(?![\d.])')
TDX = re.compile(r'(?<![\d:.])' + TIME + ZONE + r'(?:[ \t]*,[ \t]*|[ \t]+(?:on|of)[ \t]+|[ \t]*[|;\t][ \t]*|[ \t]+)' + DATE
                 + r'(?![\d/.-]\d)', re.I)
STAMP = re.compile(r'(?<!\d)(?<!\d\.)(?P<y>20\d{2})(?P<mo>[01]\d)(?P<d>[0-3]\d)[_-]?(?P<h>[0-2]\d)(?P<mi>[0-5]\d)(?P<s>[0-5]\d)?'
                   + ZONE + r'(?!\d|\.\d)', re.I)
STAMP_ISO = re.compile(r'(?<![\d.])(?P<y>20\d{2})-(?P<mo>[01]\d)-(?P<d>[0-3]\d)[Tt_-](?P<h>[0-2]\d)(?P<hs>[-.h]?)(?P<mi>[0-5]\d)'
                       r'(?:(?P=hs)(?P<s>[0-5]\d))?' + ZONE + r'(?![\d:])', re.I)
CTX_KEY = re.compile(r'(?i)(?<![\w-])["\']?(?:t|tb|ts|tblock|t_block|trwy|t_rwy|tsched|ton|toff|t_?sha|tsha|block|on_?block'
                     r'|off_?block|eta|etd|ata|atd|est|fix|first|last|segs?|obs_far|uid|slot|ident|af|cs|callsign|flight|reg|mv'
                     r'|arr|dep|role|stand)["\']?\s*[:=]')
CTX_WORD = re.compile(r'(?i)\b(?:on[- ]?block|off[- ]?block|block[- ]?time|touch[- ]?down|take[- ]?off|lift[- ]?off|landed|landing'
                      r'|departed|departure|arrival|arrived|push[- ]?back|flight|callsign|call sign|registration|airframe|movement'
                      r'|t_sha|obs_far|tier[- ]?2|observed[- ]elsewhere|stand|(?:first|last)[- ]fix|fix time)\b')
CTX_CODE = re.compile(r'\b([A-Z]{3}|[A-Z][A-Z0-9]|[0-9][A-Z])[ -]?(\d{2,4})[A-Z]?\b')


def flight_context(txt, st, en, I):
    """an 'ftime' candidate counts only in a per-flight context within 160 characters (round 3, F27): a per-flight field
    name ("t":, "tBlock":, "est":, "cs": ...), a word such as 'landed', 'on-block', 'flight', 'stand', or an airline
    designator followed by a number; a lone timestamp (a Wikipedia revision time, a file date) is not one"""
    w = txt[max(0, st - 160):en + 160]
    if CTX_KEY.search(w) or CTX_WORD.search(w):
        return True
    return any(m.group(1) in I.al_codes for m in CTX_CODE.finditer(w))


AL_KEY = re.compile(r'(?i)(?:airline|carrier|operator|op|al|company|prefix|icao|iata|airline[ _-]?(?:icao|iata|code|prefix|id)'
                    r'|carrier[ _-]?(?:code|id)|airlineicao|airlineiata|operator[ _-]?(?:code|icao))')
NUM_KEY = re.compile(r'(?i)(?:number|num|no|nr|flight|flt|fno|fltno|flightno|flight[ _-]?(?:no|num|number|nr|id)|flt[ _-]?(?:no|num|nr))\.?')
AL_VAL = re.compile(r'(?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,3}')
NUM_VAL = re.compile(r'\d{3,4}[A-Z]?')
ADDR_FIELD = re.compile(r'(?i)(?:icao|icao24|icao_?24|hex|addr|address|icao_?addr(?:ess)?|mode[ _-]?s|modes|transponder|24[ _-]?bit'
                        r'|aircraft[ _-]?address|ac[ _-]?addr)')
TOD_KEY = re.compile(r'(?i)(?:tod|tod_?s|sod|s_?o_?d|secs?_?of_?(?:the_?)?day|seconds_?of_?(?:the_?)?day|time_?of_?day(?:_?s)?'
                     r'|t_?of_?day|t_?s|time_?s|day_?s(?:ecs?|econds)?)')
DATE_CELL = re.compile(r'^\s*["\']?' + DATE + r'["\']?\s*$', re.I)
TIME_CELL = re.compile(r'^\s*["\']?' + TIME + ZONE + r'["\']?\s*$', re.I)
SEPHEX = re.compile(r'(?i)^([0-9a-f]{2})([:\- ])([0-9a-f]{2})\2([0-9a-f]{2})$')


def join_code_number(code, num, I, allow_flights, st, en, H, box):
    """an airline designator and a flight number from two fields / cells / words -> callsign or flight hits"""
    code, num = code.strip().upper(), num.strip().upper()
    sq = squash(code + num)
    if len(sq) < 4:
        return
    if sq in I.v['callsign']:
        H.append(('callsign', st, en))
    if sq in I.v['flight'] or squash(code + (num.lstrip('0') or '0')) in I.v['flight']:
        if allow_flights is not None and sq in allow_flights:
            box[0] += 1
        else:
            H.append(('flight', st, en))


def addr_new_forms(v, I):
    """the forms an address can take in an address-named field or column beyond the plain 6-hex run (round 3, F13):
    hh:hh:hh / hh-hh-hh / 'hh hh hh', a decimal integer of the 24-bit value"""
    v = v.strip().strip('"\'`').lower()
    out = []
    m = SEPHEX.match(v)
    if m:
        out.append(m.group(1) + m.group(3) + m.group(4))
    if v.isdigit() and 1 <= len(v) <= 8 and int(v) < (1 << 24):
        out.append('%06x' % int(v))
    return any(x in I.v['address'] for x in out)


def cell_dt_hits(cells, offs, I, H, min_gap=2):
    """a date cell and a time cell of the same table row, two or more columns apart (round 3; adjacent cells are DTX's;
    min_gap 1 for JSON rows, whose neighbouring cells DTX does not join)"""
    ds = [(k, m) for k, m in ((k, DATE_CELL.match(c)) for k, c in enumerate(cells)) if m]
    if not ds:
        return
    ts = [(k, m) for k, m in ((k, TIME_CELL.match(c)) for k, c in enumerate(cells)) if m]
    for kd, md in ds:
        for kt, mt in ts:
            if abs(kd - kt) < min_gap:
                continue
            g = dict(md.groupdict())
            g.update({x: y for x, y in mt.groupdict().items() if y is not None})
            secs = g.get('s') is not None
            for e in dt_epochs(g):
                if secs and e in I.t_sec or not secs and e // 60 in I.t_min:
                    H.append(('t_sha', offs[min(kd, kt)], offs[max(kd, kt)] + 1))
                    break


def table_hits(txt, I, allow_flights, box):
    """CSV / TSV / markdown table rows: the address forms in the column of a header that names an address (round 2: a
    digits-only one however far below the header; round 3: hh:hh:hh, decimal); an airline-code column and a flight-number
    column joined (round 3, F13); a date cell and a time cell of one row, any columns apart (round 3)"""
    H = []
    pos, hdr = 0, None
    sepline = lambda low: all(re.fullmatch(r':?-{2,}:?|', c) for c in low)
    for line in txt.split('\n'):
        d = next((x for x in ('\t', '|', ';', ',') if line.count(x) >= (2 if x == '|' else 1)), None)
        if d is None:
            hdr = None
            pos += len(line) + 1
            continue
        cells = line.split(d)
        offs, o = [], pos
        for c in cells:
            offs.append(o)
            o += len(c) + 1
        low = [c.strip().strip('"\'`*').lower() for c in cells]
        if hdr is not None and hdr[0] == d:
            if not sepline(low):
                row_hits(hdr[1], cells, offs, I, allow_flights, box, H, plain_addr=True)
        elif not sepline(low):
            cols = header_cols(low)
            hdr = (d, cols) if (cols['addr'] or (cols['al'] and cols['num']) or cols['tod']) else None
        if len(cells) >= 3:
            cell_dt_hits(cells, offs, I, H)
        pos += len(line) + 1
    return H


AL_SUB = re.compile(r'(?i)airline|carrier|operator|airways')
NUM_SUB = re.compile(r'(?i)flight|flt|number|(?<![a-z])(?:num|no|nr|fno)(?![a-z])')


def is_al_key(k):
    """an airline-designator column / field name: the AL_KEY names or any name that contains airline / carrier / operator
    ('operating_carrier', 'marketing_airline'; round 4, N2)"""
    return bool(k) and bool(AL_KEY.fullmatch(k) or AL_SUB.search(k))


def is_num_key(k):
    """a flight-number column / field name: the NUM_KEY names or any name that contains flight / number / num / no (round 4)"""
    return bool(k) and not is_al_key(k) and bool(NUM_KEY.fullmatch(k) or NUM_SUB.search(k))


def header_cols(low):
    """the column indices of a header row (lower-case names): address, airline code, flight number, seconds of the day"""
    return {'addr': [k for k, c in enumerate(low) if c and ADDR_FIELD.fullmatch(c)],
            'al': [k for k, c in enumerate(low) if is_al_key(c)],
            'num': [k for k, c in enumerate(low) if is_num_key(c)],
            'tod': [k for k, c in enumerate(low) if c and TOD_KEY.fullmatch(c)]}


def row_hits(cols, cells, offs, I, allow_flights, box, H, plain_addr=False):
    """one data row of a header-named table (CSV / TSV / markdown rows; table-shaped JSON, round 4): an address in an address
    column (6-hex, digits-only, hh:hh:hh, decimal), an airline-code column joined with a flight-number column, and a date
    cell with a seconds-of-day column (round 4, N2: 'day,tod_s' CSV / JSON columns, the day read as UTC and as UTC+8)"""
    n = len(cells)
    for k in cols['addr']:
        if k >= n:
            continue
        raw = cells[k].strip()
        v = raw.strip('"\'`')
        plain = len(v) == 6 and v.isdigit() and v in I.v['address'] and (not plain_addr or raw[:1] not in '"\'`')
        hexv = (not plain_addr) and HEX6.match(v) and v.lower() in I.v['address']
        if plain or hexv or addr_new_forms(v, I):
            H.append(('address', offs[k], offs[k] + len(cells[k])))
    for ka in cols['al']:
        for kn in cols['num']:
            if ka < n and kn < n:
                va, vn = cells[ka].strip().strip('"\''), cells[kn].strip().strip('"\'')
                if AL_VAL.fullmatch(va) and NUM_VAL.fullmatch(vn):
                    join_code_number(va, vn, I, allow_flights, offs[min(ka, kn)], offs[max(ka, kn)] + 1, H, box)
    if cols['tod']:
        for kd, c in enumerate(cells):
            md = DATE_CELL.match(c)
            if not md:
                continue
            g = dict(md.groupdict())
            g.update({'h': '0', 'mi': '0', 's': '0', 'z': None})
            for e0 in dt_epochs(g, utc_default=True):
                for kt in cols['tod']:
                    v = cells[kt].strip().strip('"\'') if kt < n else ''
                    if v.isdigit() and int(v) < 86400 and any(e0 + int(v) + z in I.t_sec for z in (0, -LOCAL_S)):
                        H.append(('t_sha', offs[min(kd, kt)], offs[max(kd, kt)] + 1))


JSON_HDR = ('columns', 'cols', 'fields', 'header', 'headers')
JSON_ROWS = ('data', 'rows', 'values')


def json_tables(obj, budget=2_000_000):
    """the tables of a parsed JSON value (round 4, N2): pandas to_json orient 'split' ({"columns": [...], "data": [[...]]}
    and the like: 'cols' / 'fields' / 'header(s)' with 'rows' / 'values'), orient 'columns' ({col: {index: value}}) and
    column arrays ({col: [values]}, pandas to_dict('list')) -> [(header names, rows)]; records and orient 'index' are
    flat objects (object_hits)"""
    out, stack = [], [obj]
    while stack and budget > 0:
        o = stack.pop()
        budget -= 1
        if isinstance(o, dict):
            keys = {k.lower(): k for k in o if isinstance(k, str)}
            hk = next((keys[k] for k in JSON_HDR if k in keys), None)
            rk = next((keys[k] for k in JSON_ROWS if k in keys), None)
            if hk and rk and isinstance(o[hk], list) and isinstance(o[rk], list):
                hdr = [(h.get('name') or h.get('label') or h.get('id')) if isinstance(h, dict) else h for h in o[hk]]
                rows = [r for r in o[rk] if isinstance(r, list)]
                if rows:
                    out.append((hdr, rows))
                    budget -= sum(len(r) for r in rows)
            cm = [k for k, v in o.items() if isinstance(v, dict) and v and not any(isinstance(x, (dict, list)) for x in v.values())]
            if len(cm) >= 2:
                idx = list(dict.fromkeys(i for k in cm for i in o[k]))
                out.append((cm, [[o[k].get(i) for k in cm] for i in idx]))
                budget -= len(idx) * len(cm)
            ca = [k for k, v in o.items() if isinstance(v, list) and v and not isinstance(v[0], (dict, list))]
            if len(ca) >= 2:
                L = max(len(o[k]) for k in ca)
                out.append((ca, [[o[k][i] if i < len(o[k]) else None for k in ca] for i in range(L)]))
                budget -= L * len(ca)
            stack.extend(v for v in o.values() if isinstance(v, (dict, list)))
        elif isinstance(o, list) and o:
            f = o[0]
            if isinstance(f, (int, float, str, bool)) or f is None:
                continue
            if isinstance(f, list) and f and isinstance(f[0], (int, float)):
                continue                             # a numeric matrix (coordinates)
            stack.extend(x for x in o if isinstance(x, (dict, list)))
    return out


def json_table_hits(txt, I, allow_flights, box):
    """table-shaped JSON (json_tables) in a JSON document or a JS data file ('window.X = {...};'): every row checked like a
    header-named table row (row_hits), and its date and time cells joined (any columns apart) (round 4, N2)"""
    H = []
    s = txt.lstrip()
    st = len(txt) - len(s)
    if s[:1] not in ('{', '['):
        m = re.search(r'=\s*(?=[\[{])', txt[:4096])
        if not m:
            return H
        st, s = m.end(), txt[m.end():]
    if len(s) > (64 << 20):
        return H
    try:
        obj, _ = json.JSONDecoder().raw_decode(s)
    except ValueError:
        return H
    for hdr, rows in json_tables(obj):
        low = [str(h).strip().lower() if h is not None else '' for h in hdr]
        cols = header_cols(low)
        dt_any = any(DATE_CELL.match(str(c)) for r in rows[:20] for c in r if isinstance(c, str))
        if not (cols['addr'] or (cols['al'] and cols['num']) or cols['tod'] or dt_any):
            continue
        for r in rows:
            cells = ['' if v is None else str(v) for v in r]
            offs = [st] * len(cells)
            row_hits(cols, cells, offs, I, allow_flights, box, H)
            if dt_any:
                cell_dt_hits(cells, offs, I, H, min_gap=1)
    return H


OBJ = re.compile(r'\{[^{}]{1,4000}\}')
FIELD = re.compile(r'(?<![\w])["\']?(?P<k>[A-Za-z_][\w -]{0,31}?)["\']?\s*[:=]\s*(?:"(?P<s>[^"\\\n]{0,64})"'
                   r'|\'(?P<s2>[^\'\\\n]{0,64})\'|(?P<n>-?\d+(?:\.\d+)?)(?![\w.]))')


def object_hits(txt, I, allow_flights, box):
    """fields of one flat JSON / JS / Python object (round 3, F13): an airline-code field and a flight-number field
    ({"airline": "CES", "number": "nnnn"}), an address-named field in the new forms (a decimal integer, hh:hh:hh), a date
    field and a seconds-of-day field ({"day": D, "tod_s": n}, the day read as UTC and as UTC+8)"""
    H = []
    if ':' not in txt and '=' not in txt:
        return H
    for om in OBJ.finditer(txt):
        F = []
        for fm in FIELD.finditer(om.group()):
            v = fm.group('s') if fm.group('s') is not None else fm.group('s2') if fm.group('s2') is not None else fm.group('n')
            F.append((fm.group('k').strip().lower(), v or '', om.start() + fm.start(), om.start() + fm.end(), fm.group('n') is not None))
        if not F:
            continue
        als = [f for f in F if is_al_key(f[0]) and AL_VAL.fullmatch(f[1])]
        nums = [f for f in F if is_num_key(f[0]) and NUM_VAL.fullmatch(f[1])]
        for fa in als:
            for fn in nums:
                if fa is not fn:
                    join_code_number(fa[1], fn[1], I, allow_flights, min(fa[2], fn[2]), max(fa[3], fn[3]), H, box)
        for k, v, st, en, isnum in F:
            if ADDR_FIELD.fullmatch(k) and addr_new_forms(v, I):
                H.append(('address', st, en))
        days = [f for f in F if DATE_CELL.match(f[1])]
        if days:
            tods = [f for f in F if f[4] and TOD_KEY.fullmatch(f[0]) and f[1].isdigit() and int(f[1]) < 86400]
            for dd in days:
                g = dict(DATE_CELL.match(dd[1]).groupdict())
                g.update({'h': '0', 'mi': '0', 's': '0', 'z': None})
                for e0 in dt_epochs(g, utc_default=True):
                    for tf in tods:
                        if any(e0 + int(tf[1]) + z in I.t_sec for z in (0, -LOCAL_S)):
                            H.append(('t_sha', min(dd[2], tf[2]), max(dd[3], tf[3])))
    return H


NAME_NUM = re.compile(r'(?<![\w#.])(\d{3,4})([A-Z]?)(?![\w]|[.,]\d)')
NAME_PRE = re.compile(r"((?:[A-Za-z][A-Za-z'&.\-]*[ \t]+){1,7})#?[ \t]*$")
NAME_FILLER = {'flight', 'flt', 'no', 'no.', 'nr', 'nr.', 'number', 'service'}


def name_hits(txt, I, allow_flights, box):
    """an airline NAME before a flight number ('China Eastern nnnn', 'Spring Airlines flight nnnn'; round 3, F13): the
    names of data/lookup.js AIRLINES and the short names of data/sha_sim_inputs.json, also without a trailing 'Airlines' /
    'Airways' / ... when two or more words remain; mapped to the ICAO (callsign) and IATA (flight number) designators"""
    H = []
    if not I.al_names:
        return H
    for m in NAME_NUM.finditer(txt):
        st = m.start()
        if st < 3 or txt[st - 1] not in ' \t#':
            continue
        pm = NAME_PRE.search(txt[max(0, st - 100):st])
        if not pm:
            continue
        words = pm.group(1).split()
        while words and words[-1].lower() in NAME_FILLER:
            words.pop()
        num = m.group(1) + m.group(2)
        for k in range(len(words)):
            name = ' '.join(words[k:])
            codes = I.al_names.get(name.lower())
            if codes:
                for icao, iata in codes:
                    for code in filter(None, (icao, iata)):
                        join_code_number(code, num, I, allow_flights, max(0, st - len(name) - 1), m.end(), H, box)
                break
    return H


SEPADDR = re.compile(r'(?i)(?<![0-9a-f:\-])([0-9a-f]{2})([:\-])([0-9a-f]{2})\2([0-9a-f]{2})(?![0-9a-f]|[:\-][0-9a-f])')
DECADDR = re.compile(r'(?i)(?<![\w])(?:icao[ _-]?24|icao|hex|address|addr|mode[ -]?s|transponder|24[ -]?bit(?: address)?)'
                     r'[^\S\n]*(?:[:=#]|is|of)?[^\S\n]*["\']?(\d{3,8})(?![\dxX.])')


def sep_address_hits(txt, I):
    """'hh:hh:hh' / 'hh-hh-hh' after an address keyword within 48 characters, and a decimal integer right after an address
    keyword ('icao24 11259375', 'address: 11259375') (round 3, F13)"""
    H = []
    if not I.v['address'] or not ADDR_KEY.search(txt):
        return H
    for m in SEPADDR.finditer(txt):
        a = (m.group(1) + m.group(3) + m.group(4)).lower()
        if a in I.v['address'] and ADDR_KEY.search(txt[max(0, m.start() - 48):m.start()]):
            H.append(('address', m.start(), m.end()))
    for m in DECADDR.finditer(txt):
        v = int(m.group(1))
        if v < (1 << 24) and '%06x' % v in I.v['address']:
            H.append(('address', m.start(), m.end()))
    return H


COUNT_NEXT = re.compile(r'[ \t]*[,;)]|[ \t]*\|[ \t]*[A-Z]{3}[ \t]\d')
COUNT_PREV = re.compile(r'(?:[,;(][ \t]*|\|[ \t]*\d+[ \t]*\|[ \t]*)$')


def count_list(txt, st, en):
    """a 3-digit 'AAA nnn' window that reads as a count in a list ('CES nnn, CQH nn', '(CES nnn)', 'x, CES nnn'): not a
    callsign hit (round 2: 3-digit callsigns with a space hit otherwise)"""
    return bool(COUNT_NEXT.match(txt, en) or COUNT_PREV.search(txt[max(0, st - 24):st]))


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


# ------------------------------------------------------------------------------------------------ file sets (git modes)
class GitError(Exception):
    pass


class Git:
    """the git modes, fail-closed (verification fix round 3, F12): path names NUL-separated and unquoted
    (-c core.quotePath=false, -z; they were octal-escaped and quoted before, so 'git show :<quoted>' read 0 bytes),
    literal pathspecs, every status except D (A C M R T U X B; renames as delete + add), staged content read by blob id
    from the index ('git cat-file blob', so a name like '1:x' is not read as a stage), and ANY git failure - a failed
    command, a missing object, an unmerged or intent-to-add entry, a submodule - is an ERROR (exit 1), never an empty
    file list or an empty file."""
    def __init__(self, cwd=REPO, env=None):
        self.cwd, self.env = cwd, env

    def run(self, *a):
        r = subprocess.run(['git', '-c', 'core.quotePath=false', '--literal-pathspecs', '-C', self.cwd, *a],
                           capture_output=True, env=self.env)
        if r.returncode:
            raise GitError(f'git {a[0]} failed (exit {r.returncode}): '
                           + r.stderr.decode('utf-8', 'backslashreplace').strip().replace('\n', ' ')[:200])
        return r.stdout

    def top(self):
        return os.fsdecode(self.run('rev-parse', '--show-toplevel').rstrip(b'\n'))

    def z(self, *a):
        return [os.fsdecode(x) for x in self.run(*a).split(b'\0') if x]

    def staged(self):
        """[(path, git mode, blob id)] of every staged change whose status is not D"""
        tok = self.run('diff', '--cached', '--raw', '-z', '--no-renames', '--no-abbrev', '--diff-filter=d').split(b'\0')
        out, k = [], 0
        while k < len(tok):
            h = tok[k]
            if not h:
                k += 1
                continue
            if not h.startswith(b':') or k + 1 >= len(tok):
                raise GitError('unexpected git diff --raw output')
            f = h[1:].split(b' ')                  # srcmode dstmode srcsha dstsha status
            out.append((os.fsdecode(tok[k + 1]), f[1].decode(), f[3].decode(), f[4].decode()))
            k += 2
        return out

    def blob(self, sha):
        if not sha or not sha.strip('0'):
            raise GitError('the index entry has no blob (unmerged or intent-to-add): resolve or add it before the audit')
        return self.run('cat-file', 'blob', sha)

    def index_blob(self, rel):
        """the staged bytes of one path, or None when the path is not in the index"""
        recs = [x for x in self.run('ls-files', '-s', '-z', '--', rel).split(b'\0') if x]
        for r in recs:
            meta, _, name = r.partition(b'\t')
            mode, sha, stage = meta.decode().split(' ')
            if os.fsdecode(name) == rel and stage == '0' and mode != '160000':
                return self.blob(sha)
        return None

    def common_dir(self):
        return os.fsdecode(self.run('rev-parse', '--path-format=absolute', '--git-common-dir').rstrip(b'\n'))

    def lfs_object(self, oid, size):
        """the bytes of a Git LFS object from the local store ($GIT_COMMON_DIR/lfs/objects/<oid[0:2]>/<oid[2:4]>/<oid>, or
        lfs.storage); a missing or damaged object is an ERROR (round 4, F12: on push it would go to the LFS server unread)"""
        try:
            st = os.fsdecode(self.run('config', '--get', 'lfs.storage').rstrip(b'\n'))
        except GitError:
            st = ''
        base = os.path.join(self.common_dir(), st) if st else os.path.join(self.common_dir(), 'lfs')
        p = os.path.join(base, 'objects', oid[:2], oid[2:4], oid)
        try:
            b = open(p, 'rb').read()
        except OSError:
            raise GitError('a Git LFS pointer whose object is not in the local LFS store (it cannot be audited)')
        if len(b) != size or hashlib.sha256(b).hexdigest() != oid:
            raise GitError('a Git LFS object that does not match its pointer')
        return b

    def filters(self, paths, cached):
        """{path: value of the 'filter' attribute} for the given paths ('git check-attr -z --stdin [--cached] filter'; only
        set values: an unset / unspecified filter is left out)"""
        if not paths:
            return {}
        a = ['check-attr', '-z', '--stdin'] + (['--cached'] if cached else []) + ['filter']
        r = subprocess.run(['git', '-c', 'core.quotePath=false', '-C', self.top(), *a], input=b'\0'.join(map(os.fsencode, paths)) + b'\0',
                           capture_output=True, env=self.env)
        if r.returncode:
            raise GitError(f'git check-attr failed (exit {r.returncode}): ' + r.stderr.decode('utf-8', 'backslashreplace')[:200])
        t = r.stdout.split(b'\0')
        out = {}
        for k in range(0, len(t) - 2, 3):
            v = t[k + 2].decode('utf-8', 'replace')
            if v not in ('unspecified', 'unset', 'set', ''):
                out[os.fsdecode(t[k])] = v
            elif v == 'set':                          # 'filter' set without a driver name: git applies none
                pass
        return out

    def hooks_dir(self):
        return os.fsdecode(self.run('rev-parse', '--path-format=absolute', '--git-path', 'hooks').rstrip(b'\n'))

    def diff_files(self, pathspec):
        """tracked changes vs HEAD (every status except D) + untracked, not ignored files, relative to the top level"""
        names = set(self.z('diff', '--name-only', '-z', '--no-renames', '--diff-filter=d', 'HEAD', '--', pathspec))
        names |= set(self.z('ls-files', '-z', '--others', '--exclude-standard', '--', pathspec))
        return sorted(names)


def staged_items(g):
    top = g.top()
    st = sorted(g.staged())
    names = [n for n, _, _, _ in st]
    flt = {**g.filters(names, cached=False), **g.filters(names, cached=True)}   # work-tree and index .gitattributes (round 4)
    return [(n, 'staged', {'root': top, 'git': g, 'gmode': m, 'sha': sha, 'status': s_, 'filter': flt.get(n)})
            for n, m, sha, s_ in st]


def diff_items(g, pathspec):
    top = g.top()
    return [(n, 'worktree', {'root': top, 'git': g}) for n in g.diff_files(pathspec)]


LFS_HEAD = b'version https://git-lfs.github.com/spec/'


def lfs_pointer(b):
    """(oid, size) of a Git LFS pointer file, else None"""
    if len(b) > 1024 or not b.startswith(LFS_HEAD):
        return None
    o = re.search(rb'^oid sha256:([0-9a-f]{64})\s*$', b, re.M)
    z = re.search(rb'^size (\d+)\s*$', b, re.M)
    return (o.group(1).decode(), int(z.group(1))) if o and z else None


def read_item(mode, meta, p):
    """-> ([bytes, ...], [REVIEW reasons]): what git would commit (staged: the index blob, for a symlink its target text;
    work tree: a symlink's target text, else the file; --files: a symlink's text and the file it points to) and, since round
    4 (F12), what a Git LFS pointer stands for (its object from the local LFS store: on push it goes to the LFS server) and,
    under any other clean filter, the work-tree file the staged blob was made from; raises OSError / GitError on any failure
    (the caller reports ERROR, exit 1); in --files mode a pointer whose object is not in the local store is a REVIEW"""
    why = []
    if mode == 'staged':
        if meta['gmode'] == '160000':
            raise GitError('a submodule (gitlink) entry: its content is not in this repository')
        out = [meta['git'].blob(meta['sha'])]
        ptr = lfs_pointer(out[0]) if meta['gmode'] != '120000' else None
        if ptr:
            out.append(meta['git'].lfs_object(*ptr))
        elif meta.get('filter') and meta['filter'] != 'lfs':
            if os.path.islink(p) or not os.path.isfile(p):
                raise GitError(f'a clean filter ({meta["filter"]}) is set and the work-tree file it was made from is not there')
            out.append(open(p, 'rb').read())
        return out, why
    if os.path.islink(p):
        out = [os.fsencode(os.readlink(p))]
        if mode is None and os.path.isfile(p):
            out.append(open(p, 'rb').read())
        return out, why
    if not os.path.isfile(p):
        raise OSError(f'not a regular file ({"missing" if not os.path.exists(p) else "a directory or special file"})')
    out = [open(p, 'rb').read()]
    ptr = lfs_pointer(out[0])
    if ptr:                                          # an unsmudged LFS pointer in the work tree / a pointer file given
        try:
            out.append((meta.get('git') or Git()).lfs_object(*ptr))
        except GitError as e:
            if mode == 'worktree':
                raise
            why.append(str(e))
    return out, why


# ------------------------------------------------------------------------------------------------ the audit
REVIEW_EXEMPT = ()                                 # repo-relative path prefixes whose REVIEW flag is not gated (round 3: none)


def mask_path(rel, I):
    """a path for printing: every component that holds an identity value is masked (round 3; the audit never prints a
    value, and a path name can carry one); if only the joined path hits, everything below the first directory is masked"""
    parts = rel.split('/')
    out = [p if not sum(scan_text(p, I, wrap=False)[0].values()) else f'<masked {len(p)} chars>' for p in parts]
    if out == parts and sum(scan_text(rel, I, wrap=False)[0].values()):
        out = parts[:1] + ['<masked>']
    return '/'.join(out)


def audit(items, I, allow, net=False, quiet=False, reviewed=(), gate_all=True):
    """items: [(path, mode[, meta])], mode None (--files / --docs: the file as it is), 'worktree' (--diff: what git would
    commit from the work tree) or 'staged' (--staged: the index blob; meta {root, git, gmode, sha}) -> summary dict (counts
    only). A file that could not be read is an ERROR (exit 1); one that could not be read completely is a REVIEW (exit 2) in
    every mode and anywhere in the repository (round 3, F24; REVIEW_EXEMPT is empty) unless cleared."""
    out = (lambda *a: None) if quiet else print
    nallow = net_allow() if net else None
    tot = {c: 0 for c in CLASSES}
    S = {'bad_files': 0, 'forbidden': 0, 'allowed': 0, 'net': 0, 'scanned': 0, 'cache_scanned': 0, 'hit_files': [],
         'review': 0, 'review_cleared': 0, 'path_hits': 0, 'errors': 0}
    rev = {os.path.normpath(os.path.relpath(os.path.abspath(r), REPO)) for r in reviewed}
    for it in items:
        n, mode = it[0], it[1]
        meta = it[2] if len(it) > 2 else {}
        root = meta.get('root', REPO)
        p = n if os.path.isabs(n) else os.path.join(root, n)
        rel = n.replace(os.sep, '/')
        show = mask_path(rel, I)
        # the path itself: every directory and the base name (round 2, F12); a file outside the repository: its base name
        ph, _ = scan_text(rel if not (os.path.isabs(n) or rel.startswith('../')) else os.path.basename(n), I)
        try:
            reader = (lambda sp, g=meta['git']: g.index_blob(sp)) if mode == 'staged' else file_reader(root)
            cs = cache_status(n, reader)
        except GitError as e:
            out(f'  ERROR {show}: {e}')
            S['bad_files'] += 1
            S['errors'] += 1
            continue
        if cs in ('identity-source', 'not-redistributable'):
            S['forbidden'] += 1
            S['bad_files'] += 1
            S['hit_files'].append(n)
            why = ('an observed-elsewhere identity table (never committable, OD4)' if cs == 'identity-source'
                   else 'a refs/cache file whose SOURCES.json does not mark it redistributable')
            out(f'  FORBIDDEN {show}: {why}')
            for c in CLASSES:
                tot[c] += ph[c]
            continue
        try:
            chunks, why_read = read_item(mode, meta, p)
        except (OSError, GitError) as e:              # round 3, F12: a failed read is an ERROR, never an empty file
            out(f'  ERROR {show}: {type(e).__name__}: {e}')
            S['bad_files'] += 1
            S['errors'] += 1
            continue
        X = Extract()
        X.opaque += why_read
        for b in chunks:
            extract(n, b, X)
        b = b''.join(chunks)
        txt, kind = X.text(), X.kind()
        S['scanned'] += 1
        if cs == 'redistributable':
            S['cache_scanned'] += 1
        if X.forbidden:                              # an archive member named as an identity table
            S['forbidden'] += 1
            S['bad_files'] += 1
            S['hit_files'].append(n)
            out(f'  FORBIDDEN {show} [{kind}]: holds {X.forbidden} member(s) named as an observed-elsewhere identity table')
            continue
        sp = section_split(n, b.decode('utf-8', 'replace')) if X.kinds[:1] == ['text'] else None   # the file as text
        L = set()
        if sp:
            h1, al1 = scan_text(sp[0], I, lines=None)
            h2, al2 = scan_text(sp[1], I, allow_flights=allow, lines=None)
            h3, _ = scan_text('\n'.join(p_ for p_ in X.parts[1:] if p_), I, lines=None)   # what was decoded inside the file
            hits = {c: h1[c] + h2[c] + h3[c] for c in CLASSES}
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
                out(f'  HIT  {show} [path name]: ' + ', '.join(f'{c} {ph[c]}' for c in CLASSES if ph[c]))
            if k:
                out(f'  HIT  {show} [{kind}]: ' + ', '.join(f'{c} {hits[c]}' for c in CLASSES if hits[c])
                    + (f' (lines {", ".join(map(str, ln[:8]))}{" ..." if len(ln) > 8 else ""})' if ln else ''))
        for c in CLASSES:
            tot[c] += hits[c] + ph[c]
        if X.opaque:                                 # round 2, F12: not fully readable -> a review by eye (exit 2)
            key = os.path.normpath(os.path.relpath(p, REPO))
            cleared = key in rev or REVIEWED.get(key.replace(os.sep, '/')) == hashlib.sha256(b).hexdigest()
            exempt = (not gate_all) and any(rel.startswith(x) for x in REVIEW_EXEMPT)
            why = '; '.join(sorted(set(X.opaque)))[:200]
            if cleared:
                S['review_cleared'] += 1
                out(f'  reviewed {show} [{kind}]: {why} (cleared by --reviewed / REVIEWED)')
            elif not exempt:
                S['review'] += 1
                out(f'  REVIEW {show} [{kind}]: {why}')
            else:
                out(f'  note {show} [{kind}]: {why} (REVIEW_EXEMPT, not gated)')
        if net and re.search(r'(^|/)(docs|jobs)/', n.replace(os.sep, '/')):
            x = net_scan(txt, nallow)
            S['net'] += x
            if x:
                out(f'  net  {show}: {x} pattern matches outside the allow-list (review by eye; not an exact hit)')
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
        ('other per-flight time, ISO second', 'e3.md', f'last fix {fmt(t2, "%Y-%m-%dT%H:%M:%SZ")}', 'ftime'),
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


def selftest_round3_cases(I, png, reg4, cs, fl, addr, t, fmt):
    """round 3 (F13 forms, F24 PNG chunks, F26 fingerprints, F27 clean control): [(label, file name, bytes | str, class or
    None)]; values from the set in memory, never printed"""
    pre, num = reg4.split('-')
    n4 = cs[3:]                                       # the number of a CESnnnn callsign (its flight is MUnnnn)
    fn = fl[2:]
    L8 = t + LOCAL_S
    t2 = sorted(I.t2_sec)[len(I.t2_sec) // 3]
    excel = (t - dt.datetime(1899, 12, 30, tzinfo=dt.timezone.utc).timestamp()) / 86400.0
    day_tbl = sorted(glob.glob(os.path.join(OBS, 'sha_observed_*.json')))[-1]
    blob = open(day_tbl, 'rb').read()
    day = re.search(r'(\d{4}-\d{2}-\d{2})', day_tbl).group(1)
    ov = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'observed_overlay.py'), '--day', day], capture_output=True).stdout
    ovc = json.dumps(json.loads(ov), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    sri = base64.b64encode(hashlib.sha256(blob).digest()).decode()
    gid = hashlib.sha1(b'blob %d\0' % len(blob) + blob).hexdigest()
    cases = [
        # F13: hard line wraps
        ('flight number split by a hard line wrap "MU\\nnnnn"', 'w1.md', f'the stand of flight {fl[:2]}\n{fn} was 233\n', 'flight'),
        ('callsign split by a hard line wrap "CES\\nnnnn"', 'w2.md', f'the stand of {cs[:3]}\n{n4} was 233\n', 'callsign'),
        ('registration wrapped after its hyphen', 'w3.md', f'parked as {pre}-\n{num} at 233\n', 'registration'),
        ('flight number wrapped inside a "#" comment block', 'w4.py', f'# the flight {fl[:2]}\n#   {fn} parked at 233\nx = 1\n', 'flight'),
        # F13: the time before the date, compact stamps
        ('time before the date "hh:mm:ss UTC on D Mon YYYY"', 't1.md', f'touchdown {fmt(t, "%H:%M:%S")} UTC on {int(fmt(t, "%d"))} {fmt(t, "%b %Y")}', 't_sha'),
        ('time before the date, local minute "hh:mm local, D Mon YYYY"', 't2.md', f'on-block {fmt(L8, "%H:%M")} local, {int(fmt(L8, "%d"))} {fmt(L8, "%b %Y")}', 't_sha'),
        ('compact stamp "YYYYMMDDhhmmss"', 't3.md', f'ts {fmt(t, "%Y%m%d%H%M%S")}', 't_sha'),
        ('compact stamp "YYYYMMDD_hhmmss" in text', 't4.md', f'run {fmt(t, "%Y%m%d_%H%M%S")} utc', 't_sha'),
        ('ISO date + dashed time "YYYY-MM-DD_hh-mm-ss"', 't5.md', f'shot_{fmt(t, "%Y-%m-%d_%H-%M-%S")}.png', 't_sha'),
        # F13: airline names, split callsigns / flights
        ('airline name + number "China Eastern nnnn"', 'a1.md', f'China Eastern {n4} parked at 233', 'callsign'),
        ('full airline name + "flight" + number', 'a2.md', f'the China Eastern Airlines flight {n4} parked at 233', 'callsign'),
        ('JSON: callsign split into airline + number fields', 'a3.json', json.dumps({'airline': 'CES', 'number': n4, 'stand': '233'}), 'callsign'),
        ('CSV: IATA flight split "carrier,flight_no / MU,nnnn"', 'a4.csv', f'carrier,flight_no,stand\nMU,{fn},233\n', 'flight'),
        ('markdown table: airline column and flight-number column apart', 'a5.md', f'| Airline | Stand | Flight no |\n|---|---|---|\n| MU | 233 | {fn} |\n', 'flight'),
        # F13: address forms in address-named fields
        ('address "hh:hh:hh" after a keyword', 'h1.md', f'icao24 {addr[0:2]}:{addr[2:4]}:{addr[4:6]}', 'address'),
        ('address as a decimal integer in JSON {"icao24": n}', 'h2.json', json.dumps({'icao24': int(addr, 16)}), 'address'),
        ('address as a decimal after a keyword in text', 'h3.md', f'mode-s address {int(addr, 16)} seen', 'address'),
        ('address "hh-hh-hh" in an address column', 'h4.csv', f'hex,stand\n{addr[0:2]}-{addr[2:4]}-{addr[4:6]},233\n', 'address'),
        ('Cyrillic homoglyph registration "В-nnnn"', 'h5.md', f'x В{reg4[1:]} y', 'registration'),
        # admitted limits of round 2, now covered
        ('JSON {"day": local date, "tod_s": seconds of the local day}', 'l1.json', json.dumps({'day': fmt(L8, '%Y-%m-%d'), 'tod_s': L8 % 86400, 'airline': 'CES'}), 't_sha'),
        ('Excel serial date in a CSV cell', 'l2.csv', f'airline,t_excel\nCES,{excel:.6f}\n', 't_sha'),
        ('markdown table: date and time two columns apart', 'l3.md', f'| {fmt(t, "%Y-%m-%d")} | CES | {fmt(t, "%H:%M:%S")} |', 't_sha'),
        # F24: PNG chunks
        ('reg in a private PNG chunk "prVt"', 'g1.png', png([(b'prVt', f'reg {reg4}'.encode())]), 'registration'),
        ('reg in a zlib-compressed private PNG chunk', 'g2.png', png([(b'zzZz', zlib.compress(f'reg {reg4}'.encode()))]), 'registration'),
        ('reg in bytes after the PNG IEND', 'g3.png', png([]) + f'reg {reg4}'.encode(), 'registration'),
        ('reg in an iCCP profile description', 'g4.png', png([(b'iCCP', b'icc\x00\x00' + zlib.compress(b'desc ' + reg4.encode()))]), 'registration'),
        # F26: fingerprints
        ('fingerprint: sha256[:16] of an overlay (observed_overlay.py output)', 'p1.md', f'overlay sha256 {hashlib.sha256(ov).hexdigest()[:16]}', 'fingerprint'),
        ('fingerprint: sha256[:12] of an overlay as canonical JSON', 'p2.md', f'canon {hashlib.sha256(ovc).hexdigest()[:12]}', 'fingerprint'),
        ('fingerprint: the git blob id of a day table', 'p3.md', f'blob {gid}', 'fingerprint'),
        ('fingerprint: the SRI base64 sha256 of a day table', 'p4.html', f'<script integrity="sha256-{sri}"></script>', 'fingerprint'),
        ('fingerprint: sha256[:10] of a day table (below the round-2 cut)', 'p5.md', f'sha {hashlib.sha256(blob).hexdigest()[:10]}', 'fingerprint'),
        ('fingerprint: sha1[:8] of a day table', 'p6.md', f'short {hashlib.sha1(blob).hexdigest()[:8]}', 'fingerprint'),
        # clean controls
        ('clean: a lone public revision time equal to a per-flight time (F27)', 'q1.py',
         f"'revisions': {{'Shanghai_Pudong_International_Airport': '1385155113 ({fmt(t2, '%Y-%m-%dT%H:%M:%SZ')})'}},", None),
        ('clean: an airline name, a verb, then a count', 'q2.md', f'China Eastern carried {n4} passengers', None),
        ('clean: a carrier column and a count column', 'q3.csv', f'airline,n\nCES,{n4}\n', None),
        ('clean: an 8-hex short id of no local file', 'q4.md', f'commit {hashlib.sha1(b"clean").hexdigest()[:8]}', None),
        ('clean: a wrapped paragraph without identities', 'q5.md', 'the stand of flight\nnumber 233 was free\n\nCES\n\nlist', None),
        ('clean: a decimal integer after a non-address word', 'q6.md', f'counted {int(addr, 16)} rows', None),
    ]
    try:
        Lf = json.load(open(LOCAL_FP, encoding='utf-8'))
        h = sorted((Lf.get('hashes') or {}).values())
        if h:
            cases.append(('fingerprint: a local plan hash recorded by test_plan.mjs', 'p7.md', f'local plan hash {h[0]}', 'fingerprint'))
    except (OSError, ValueError):
        pass
    return cases


def tiff_le(ifd0, exif=None):
    """a little-endian TIFF for the selftest: ifd0 / exif = [(tag, type, count, value bytes)], exif as a sub-IFD (0x8769)"""
    def ifd(entries, base):
        n = len(entries)
        data_off, head, blob = base + 2 + 12 * n + 4, struct.pack('<H', n), b''
        for tag, typ, cnt, val in sorted(entries):
            if len(val) <= 4:
                head += struct.pack('<HHI', tag, typ, cnt) + val.ljust(4, b'\x00')
            else:
                head += struct.pack('<HHI', tag, typ, cnt) + struct.pack('<I', data_off + len(blob))
                blob += val + b'\x00' * (len(val) & 1)
        return head + b'\x00\x00\x00\x00' + blob
    if exif is None:
        return b'II*\x00' + struct.pack('<I', 8) + ifd(ifd0, 8)
    e0 = ifd0 + [(0x8769, 4, 1, b'\x00\x00\x00\x00')]
    off = 8 + len(ifd(e0, 8))
    e0 = ifd0 + [(0x8769, 4, 1, struct.pack('<I', off))]
    return b'II*\x00' + struct.pack('<I', 8) + ifd(e0, 8) + ifd(exif, off)


def jpeg_min(app=b'', after_scan=b'', trailer=b''):
    """a minimal JPEG marker structure for the selftest (SOI, APP0, [APPn], SOS + entropy bytes, [segments], EOI, [trailer])"""
    seg = lambda mk, data: b'\xff' + bytes([mk]) + struct.pack('>H', len(data) + 2) + data
    return (b'\xff\xd8' + seg(0xE0, b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00') + app + seg(0xDA, b'\x01\x01\x00\x00\x3f\x00')
            + b'\x12\x34\xff\x00\x56' + after_scan + b'\xff\xd9' + trailer)


def glb_min(js, binc=b'', extra=None):
    j = json.dumps(js).encode()
    j += b' ' * (-len(j) % 4)
    bn = binc + b'\x00' * (-len(binc) % 4)
    ch = struct.pack('<I4s', len(j), b'JSON') + j + (struct.pack('<I4s', len(bn), b'BIN\x00') + bn if bn else b'')
    if extra is not None:
        e = extra + b'\x00' * (-len(extra) % 4)
        ch += struct.pack('<I4s', len(e), b'XTRA') + e
    return b'glTF' + struct.pack('<II', 2, 12 + len(ch)) + ch


def selftest_round4_cases(I, png, reg4, cs, fl, t, fmt):
    """round 4 (N2 forms, N3 carriers): [(label, file name, bytes | str, class or None)]; values from the set in memory,
    never printed"""
    pre, num = reg4.split('-')
    L8 = t + LOCAL_S
    T = sorted(x for x in I.t_sec if x % 60 not in (0, 59, 1))
    tp = next(x for x in T if 13 <= ((x + LOCAL_S) // 3600) % 24 <= 23)            # a local afternoon / evening t_sha
    tu = next(x for x in T if 13 <= (x // 3600) % 24 <= 23)                        # a UTC afternoon / evening t_sha
    h12 = lambda e: f'{(int(fmt(e, "%H")) % 12) or 12}:{fmt(e, "%M:%S")}'
    fl3 = sorted(x for x in I.raw['flight'] if re.fullmatch(r'MU[1-9]\d{2}', x))
    rec = json.dumps({'records': [{'cs': cs, 'reg': reg4}]})
    raw = zlib.compressobj(9, zlib.DEFLATED, -15)
    rawd = raw.compress(rec.encode()) + raw.flush()
    npy_head = "{'descr': '<f8', 'fortran_order': False, 'shape': (2,), }"
    npy_head += ' ' * (-(10 + len(npy_head) + 1) % 64) + '\n'
    npy = b'\x93NUMPY\x01\x00' + struct.pack('<H', len(npy_head)) + npy_head.encode() + struct.pack('<2d', float(t), float(t + 600))
    gif = (b'GIF89a\x01\x00\x01\x00\x00\x00\x00' + b'\x21\xfe' + bytes([len(f'cam {reg4}')]) + f'cam {reg4}'.encode() + b'\x00'
           + b'\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b')
    nb = {'cells': [{'cell_type': 'code', 'source': ['show()'], 'metadata': {}, 'outputs': [
        {'output_type': 'display_data', 'metadata': {}, 'data': {'image/gif': base64.b64encode(gif).decode()}}]}], 'nbformat': 4}
    seg = lambda mk, data: b'\xff' + bytes([mk]) + struct.pack('>H', len(data) + 2) + data
    xp = f'cam {reg4}'.encode('utf-16-le') + b'\x00\x00'
    uc = b'UNICODE\x00' + f'cam {reg4}'.encode('utf-16-be')
    iu = f'cam {reg4}'.encode() + b'\x00'
    gz = (lambda body, com: b'\x1f\x8b\x08\x10\x00\x00\x00\x00\x00\x03' + com + b'\x00' + body[0]
          + struct.pack('<II', zlib.crc32(body[1]) & 0xffffffff, len(body[1])))
    def deflate(d):
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        return c.compress(d) + c.flush(), d
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, 'w') as z:
        z.writestr('a.txt', 'stand 233\n')
        z.comment = f'cam {reg4}'.encode()
    zc = zb.getvalue()
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, 'w') as z:
        zi = zipfile.ZipInfo('a.txt')
        zi.comment = f'cam {reg4}'.encode()
        z.writestr(zi, 'stand 233\n')
    zm = zb.getvalue()
    tb = io.BytesIO()
    with tarfile.open(fileobj=tb, mode='w', format=tarfile.PAX_FORMAT) as tf:
        ti = tarfile.TarInfo('a.txt')
        ti.size, ti.pax_headers = 10, {'comment': f'cam {reg4}'}
        tf.addfile(ti, io.BytesIO(b'stand 233\n'))
    def pdf_info(title_obj):
        return ('%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
                '3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n').encode() + b'4 0 obj<</Title ' + title_obj \
            + b'>>endobj\ntrailer<</Root 1 0 R/Info 4 0 R>>\n%%EOF\n'
    u16 = f'stand 233 {reg4}'.encode('utf-16-be')
    ps, x = ['%!PS-Adobe-3.0', '/Sans 10.000 selectfont', 'gsave', '10 20 translate'], 0.0
    for ch in f'stand 233 {reg4}':
        if ch == ' ':
            x += 3.2
            continue
        ps.append(f'{x:g} 0 m /{ch if ch.isalpha() else {"-": "hyphen"}.get(ch, ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][int(ch)] if ch.isdigit() else "period")} glyphshow')
        x += 6.1
    ps.append('grestore')
    try:
        import sqlite3
        con = sqlite3.connect(':memory:')
        con.execute('create table m(reg text)')
        con.execute('insert into m values (?)', (reg4,))
        con.commit()
        sq = con.serialize()
        con.close()
    except (ImportError, AttributeError):
        sq = None
    cases = [
        # N2: date-time forms
        ('t_sha: JS Date.toString in UTC+8 ("... GMT+0800 (China Standard Time)")', 'r1.log', f'landed {fmt(L8, "%a %b %d %Y %H:%M:%S")} GMT+0800 (China Standard Time)', 't_sha'),
        ('t_sha: Python ctime / asctime, UTC', 'r2.log', f'on-block {fmt(t, "%a %b %d %H:%M:%S %Y")}', 't_sha'),
        ('t_sha: git\'s default date with +0800', 'r3.txt', f'Date:   {fmt(L8, "%a %b %d %H:%M:%S %Y")} +0800', 't_sha'),
        ('t_sha: date(1) default with CST', 'r4.log', f'landed at {fmt(L8, "%a %b %d %H:%M:%S")} CST {fmt(L8, "%Y")}', 't_sha'),
        ('t_sha: en-US 12-hour "M/D/YYYY, h:mm:ss PM" (narrow no-break space), local', 'r5.log', f'arrival {int(fmt(tp + LOCAL_S, "%m"))}/{int(fmt(tp + LOCAL_S, "%d"))}/{fmt(tp + LOCAL_S, "%Y")}, {h12(tp + LOCAL_S)} PM', 't_sha'),
        ('t_sha: "YYYY-MM-DD h:mm:ss PM" (spreadsheet), UTC', 'r6.csv', f'stand,on_block\n233,{fmt(tu, "%Y-%m-%d")} {h12(tu)} PM\n', 't_sha'),
        ('t_sha: de-DE "DD.MM.YYYY, hh:mm:ss", local', 'r7.log', f'Landung {fmt(L8, "%d.%m.%Y")}, {fmt(L8, "%H:%M:%S")}', 't_sha'),
        ('t_sha: "DD-MM-YYYY hh:mm:ss", local', 'r8.log', f'landed {fmt(L8, "%d-%m-%Y %H:%M:%S")}', 't_sha'),
        # N2: flight numbers, joiners, invisible characters, headers, JSON tables
        ('flight number joined by "+" in a URL query', 'r10.md', f'see https://example.invalid/search?q={fl[:2]}+{fl[2:]}', 'flight'),
        ('callsign joined by "+" in a file-name-like token', 'r11.md', f'card_{cs[:3]}+{cs[3:]}.png', 'callsign'),
        ('registration with a left-to-right mark U+200E inside', 'r12.md', f'reg {reg4[:4]}‎{reg4[4:]}', 'registration'),
        ('registration with a right-to-left override U+202E and a pop U+202C', 'r13.md', f'reg {pre}‮-‬{num}', 'registration'),
        ('CSV header "operating_carrier,flight_number"', 'r14.csv', f'operating_carrier,flight_number,stand\n{fl[:2]},{fl[2:]},233\n', 'flight'),
        ('CSV header "marketing_airline,flight_num"', 'r15.csv', f'marketing_airline,flight_num,stand\n{fl[:2]},{fl[2:]},233\n', 'flight'),
        ('pandas to_json(orient="split"): airline and number columns', 'r16.json', json.dumps({'columns': ['airline', 'number', 'stand'], 'index': [0], 'data': [[fl[:2], fl[2:], '233']]}), 'flight'),
        ('JSON column arrays {"carrier": [...], "flight_no": [...]}', 'r17.json', json.dumps({'carrier': ['XX', fl[:2]], 'flight_no': ['0000', fl[2:]]}), 'flight'),
        ('CSV day + seconds-of-day columns (local)', 'r18.csv', f'day,tod_s,stand\n{fmt(L8, "%Y-%m-%d")},{L8 % 86400},233\n', 't_sha'),
        ('pandas orient="split": a date column and a time column', 'r19.json', json.dumps({'columns': ['day', 'time'], 'data': [[fmt(t, '%Y-%m-%d'), fmt(t, '%H:%M:%S')]]}), 't_sha'),
        # N3: base64 / hex payloads
        ('base64 of zlib-compressed JSON in a JS data file', 's1.js', f'export const D = "{base64.b64encode(zlib.compress(rec.encode(), 9)).decode()}";', 'registration'),
        ('base64 of raw deflate', 's2.js', f'const D = atob("{base64.b64encode(rawd).decode()}");', 'registration'),
        ('base64 of UTF-16LE text', 's3.json', json.dumps({'note': base64.b64encode(f'stand 233 {reg4}'.encode('utf-16-le')).decode()}), 'registration'),
        ('base64 of a .npy float64 array of t_sha', 's4.json', json.dumps({'npy': base64.b64encode(npy).decode()}), 't_sha'),
        ('base64 float64 typed array ("bdata") of t_sha', 's5.html', '{"x":{"dtype":"f8","bdata":"' + base64.b64encode(struct.pack('<2d', float(t), float(t + 600))).decode() + '"}}', 't_sha'),
        ('hex-encoded JSON payload (bytes.hex())', 's6.txt', f'payload {rec.encode().hex()}', 'registration'),
        ('MIME-wrapped base64 of a gzip JSON', 's7.eml', 'Content-Transfer-Encoding: base64\n\n' + base64.encodebytes(gzip.compress((rec * 3).encode())).decode(), 'registration'),
        ('a Jupyter image/gif output whose GIF comment holds a registration', 's8.ipynb', json.dumps(nb), 'registration'),
        # N3: images
        ('JPEG: text after the EOI marker', 'j1.jpg', jpeg_min(trailer=f'note {reg4}\n'.encode()), 'registration'),
        ('JPEG: a COM segment after the scan', 'j2.jpg', jpeg_min(after_scan=seg(0xFE, f'cam {reg4}'.encode())), 'registration'),
        ('JPEG: Exif XPComment (UTF-16LE)', 'j3.jpg', jpeg_min(app=seg(0xE1, b'Exif\x00\x00' + tiff_le([(0x9C9C, 1, len(xp), xp)]))), 'registration'),
        ('JPEG: Exif UserComment with the UNICODE character code (Exif sub-IFD)', 'j4.jpg', jpeg_min(app=seg(0xE1, b'Exif\x00\x00' + tiff_le([(0x010F, 2, 4, b'cam\x00')], [(0x9286, 7, len(uc), uc)]))), 'registration'),
        ('TIFF: an ASCII tag inside the Exif sub-IFD', 'j5.tif', tiff_le([(0x010F, 2, 4, b'cam\x00')], [(0xA420, 2, len(iu), iu)]), 'registration'),
        ('TIFF: XPComment (BYTE, UTF-16LE) in IFD0', 'j6.tif', tiff_le([(0x9C9C, 1, len(xp), xp)]), 'registration'),
        ('TIFF: a DOUBLE tag holding t_sha', 'j7.tif', tiff_le([(0x9000, 12, 1, struct.pack('<d', float(t)))]), 't_sha'),
        ('TIFF: text in bytes no tag references', 'j8.tif', tiff_le([(0x010F, 2, 4, b'cam\x00')]) + f'note {reg4}'.encode(), 'registration'),
        ('PNG: an eXIf chunk with XPComment (UTF-16LE)', 'j9.png', png([(b'eXIf', tiff_le([(0x9C9C, 1, len(xp), xp)]))]), 'registration'),
        ('GIF: a comment extension', 'j10.gif', gif, 'registration'),
        # N3: glTF, archives, PDF, PostScript
        ('GLB: a base64 text field in the JSON chunk', 'g1.glb', glb_min({'asset': {'version': '2.0'}, 'extras': {'n': base64.b64encode(f'stand 233 {reg4}'.encode()).decode()}}), 'registration'),
        ('GLB: an unknown chunk holding zlib text', 'g2.glb', glb_min({'asset': {'version': '2.0'}}, b'\x00' * 8, zlib.compress(f'stand 233 {reg4}'.encode())), 'registration'),
        ('GLB: an embedded PNG texture with a zTXt chunk (no bufferViews)', 'g3.glb', glb_min({'asset': {'version': '2.0'}, 'images': [{'bufferView': 0}]}, png([(b'zTXt', b'Comment\x00\x00' + zlib.compress(f'cam {reg4}'.encode()))])), 'registration'),
        ('gzip: the FCOMMENT header field', 'g4.gz', gz(deflate(b'stand,233\n'), f'cam {reg4}'.encode()), 'registration'),
        ('zip: the archive comment', 'g5.zip', zc, 'registration'),
        ('zip: a member comment', 'g6.zip', zm, 'registration'),
        ('tar: a pax header', 'g7.tar', tb.getvalue(), 'registration'),
        ('PDF: Info /Title as a UTF-16BE hex string', 'g8.pdf', pdf_info(b'<FEFF' + u16.hex().upper().encode() + b'>'), 'registration'),
        ('PDF: Info /Title as a UTF-16BE literal string with its BOM (matplotlib)', 'g9.pdf', pdf_info(b'(\xfe\xff' + u16 + b')'), 'registration'),
        ('PostScript: text drawn glyph by glyph (glyphshow)', 'g10.ps', '\n'.join(ps) + '\n', 'registration'),
        # clean controls
        ('clean: an address-named field holding a small count (F27)', 'q7.json', json.dumps({'address': 1, 'icao24': 12, 'hex': 255}), None),
        ('clean: a ctime-style date on a day without observations', 'q8.log', 'Fri Nov 20 06:37:05 2026 +0800', None),
        ('clean: a short base64 run of binary bytes (< 64 bytes)', 'q9.json', json.dumps({'k': base64.b64encode(bytes(range(40))).decode()}), None),
    ]
    if fl3:
        f3 = fl3[len(fl3) // 2]
        cases.append(('flight number zero-padded to 4 digits "MU0nnn"', 'r9.md', f'flight {f3[:2]}0{f3[2:]} landed', 'flight'))
        cases.append(('flight number zero-padded, with a space "MU 0nnn"', 'r9b.md', f'| {f3[:2]} 0{f3[2:]} | 233 |', 'flight'))
    if sq:
        cases.append(('a SQLite database in base64 (also REVIEW)', 's9.json', json.dumps({'db': base64.b64encode(sq).decode()}), 'registration'))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for fmt_, nm in (('ps', 'g11.ps'), ('eps', 'g12.eps')):
            fig = plt.figure()
            fig.text(0.5, 0.5, f'stand 233 {reg4}')
            b = io.BytesIO()
            fig.savefig(b, format=fmt_)
            plt.close(fig)
            cases.append((f'matplotlib {fmt_.upper()} text', nm, b.getvalue(), 'registration'))
        fig = plt.figure()
        b = io.BytesIO()
        fig.savefig(b, format='pdf', metadata={'Title': f'Stand 233 – {reg4}'})
        plt.close(fig)
        cases.append(('matplotlib PDF: a non-ASCII metadata title', 'g13.pdf', b.getvalue(), 'registration'))
    except ImportError:
        pass
    return cases


def selftest_round4_review(I, allow, d, png):
    """round 4 (N3): what the audit cannot read completely is REVIEW (exit 2), clean standard files are not (exit 0)"""
    ok = True
    rnd = hashlib.sha512(b'selftest').digest() * 2                              # 128 bytes that are no text and no format
    for label, name, data, want in (
            ('an undecodable base64 run of >= 64 bytes in JSON', 'v1.json', json.dumps({'blob': base64.b64encode(rnd).decode()}), 2),
            ('a JPEG with clean bytes after EOI', 'v2.jpg', jpeg_min(trailer=b'clean trailer bytes'), 2),
            ('a GLB with a clean unknown chunk', 'v3.glb', glb_min({'asset': {'version': '2.0'}}, b'\x00' * 8, b'clean'), 2),
            ('a TIFF with 64+ binary bytes no tag references', 'v4.tif', tiff_le([(0x010F, 2, 4, b'cam\x00')]) + rnd, 2),
            ('a gzip with bytes after the last member', 'v5.gz', gzip.compress(b'clean\n') + rnd[:20], 2),
            ('a clean JPEG (control)', 'v6.jpg', jpeg_min(), 0),
            ('a clean TIFF (control)', 'v7.tif', tiff_le([(0x010F, 2, 4, b'cam\x00'), (0x9C9C, 1, 12, 'clean'.encode('utf-16-le') + b'\x00\x00')]), 0),
            ('a clean GLB with a PNG texture (control)', 'v8.glb', glb_min({'asset': {'version': '2.0'}}, png([])), 0),
            ('a clean GIF (control)', 'v9.gif', b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b', 0)):
        fp = os.path.join(d, name)
        open(fp, 'wb').write(data.encode() if isinstance(data, str) else data)
        S = audit([(fp, None)], I, allow, quiet=True)
        good = S['exit'] == want
        ok &= good
        print(f'  selftest {label} -> exit {want}: {"ok" if good else "FAILED"} (exit {S["exit"]})')
    return ok


def selftest_git(I, allow, reg4):
    """round 3, F12: the git modes in a SCRATCH repository: the work tree under sha3d/out/ (gitignored), the GIT_DIR a
    temporary directory outside the repository; the real index is never touched (checked). Every case goes through the
    same code path as --staged / --diff (mode_items + audit). Returns ok; prints labels and results only."""
    import tempfile, shutil
    os.makedirs(os.path.join(SHA3D, 'out'), exist_ok=True)
    W = tempfile.mkdtemp(prefix='audit_selftest_git_', dir=os.path.join(SHA3D, 'out'))
    G = tempfile.mkdtemp(prefix='audit_selftest_gitdir_')
    real_index = os.path.join(REPO, '.git', 'index')
    h0 = hashlib.sha256(open(real_index, 'rb').read()).hexdigest() if os.path.isfile(real_index) else None
    base = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    base.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_AUTHOR_NAME': 'selftest',
                 'GIT_AUTHOR_EMAIL': 'selftest@example.invalid', 'GIT_COMMITTER_NAME': 'selftest',
                 'GIT_COMMITTER_EMAIL': 'selftest@example.invalid'})
    env = dict(base, GIT_DIR=G, GIT_WORK_TREE=W)
    ok = True
    dirty = f'stand 233 {reg4}\n'
    clean = 'stand 233 clean\n'

    def sh(*a, check=True):
        return subprocess.run(['git', *a], cwd=W, env=env, capture_output=True, check=check)

    def put(rel, body):
        p = os.path.join(W, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if os.path.lexists(p):
            os.remove(p)
        open(p, 'wb').write(body.encode() if isinstance(body, str) else body)

    def run(mode, pathspec='.', g=None):
        try:
            items = mode_items(mode, g or Git(W, env), pathspec=pathspec)
        except GitError:
            return 'git-error', 1
        S = audit(items, I, allow, quiet=True)
        return S['scanned'], S['exit']

    def case(label, got, want_exit):
        nonlocal ok
        good = got[1] == want_exit
        ok &= good
        print(f'  selftest git: {label}: {"ok" if good else "FAILED"} (scanned {got[0]}, exit {got[1]}, want {want_exit})')

    try:
        subprocess.run(['git', 'init', '-q', '--bare', G], env=base, check=True, capture_output=True)
        sh('config', 'core.bare', 'false')
        names = {'ascii': 'q_ascii.md', 'non-ASCII name': 'q_航班.md', 'non-ASCII directory': '航班/q.md',
                 'a name with \'"\'': 'q_"x".md', 'a name with a tab, a backslash and a newline': 'q\tx\\y\nz.md',
                 'a name that reads as a stage spec "1:x"': '1:x.md'}
        # --staged, nothing committed yet: one file at a time
        for k, rel in names.items():
            put(rel, dirty)
            sh('add', '--', rel)
            case(f'--staged, {k}, holding a registration', run('staged'), 1)
            sh('rm', '-q', '--cached', '-f', '--', rel)
            os.remove(os.path.join(W, rel))
        put('q_航班.md', clean)
        sh('add', '--', 'q_航班.md')
        case('--staged, a clean file with a non-ASCII name (control)', run('staged'), 0)
        sh('rm', '-q', '--cached', '-f', '--', 'q_航班.md')
        put('top.bin', bytes(range(256)) * 8)
        sh('add', '--', 'top.bin')
        case('--staged, an unknown binary outside sha3d/ (REVIEW repo-wide)', run('staged'), 2)
        sh('rm', '-q', '--cached', '-f', '--', 'top.bin')
        os.symlink(f'cards/{reg4}.md', os.path.join(W, 'link.md'))
        sh('add', '--', 'link.md')
        case('--staged, a symlink whose target text holds a registration', run('staged'), 1)
        sh('rm', '-q', '--cached', '-f', '--', 'link.md')
        os.remove(os.path.join(W, 'link.md'))
        put('gone.md', 'stand 233 a staged file whose blob is then lost\n')
        sh('add', '--', 'gone.md')
        sha = sh('ls-files', '-s', '--', 'gone.md').stdout.split()[1].decode()
        os.remove(os.path.join(G, 'objects', sha[:2], sha[2:]))
        case('--staged, a staged blob that cannot be read (ERROR, not an empty file)', run('staged'), 1)
        sh('update-index', '--force-remove', '--', 'gone.md')
        os.remove(os.path.join(W, 'gone.md'))
        empty = tempfile.mkdtemp(prefix='audit_selftest_nogit_')
        try:
            case('--staged, a GIT_DIR that is no repository (ERROR, not 0 files)',
                 run('staged', g=Git(W, dict(base, GIT_DIR=empty, GIT_WORK_TREE=W))), 1)
        finally:
            shutil.rmtree(empty, ignore_errors=True)
        # a baseline commit: clean files, a symlink, a file to delete
        for k in ('non-ASCII name', 'non-ASCII directory', 'a name with \'"\''):
            put(names[k], clean)
        put('p.md', clean)
        put('del.md', clean)
        os.symlink('p.md', os.path.join(W, 'notes.md'))
        sh('add', '--', '.')
        sh('commit', '-q', '-m', 'selftest baseline')
        # type change symlink -> file (status T), staged and in the work tree
        os.remove(os.path.join(W, 'notes.md'))
        put('notes.md', dirty)
        case('--diff, a symlink replaced by a file with a registration (status T)', run('diff', 'notes.md'), 1)
        sh('add', '--', 'notes.md')
        case('--staged, a symlink replaced by a file with a registration (status T)', run('staged'), 1)
        sh('reset', '-q', '--', 'notes.md')
        os.remove(os.path.join(W, 'notes.md'))
        os.symlink('p.md', os.path.join(W, 'notes.md'))
        # git add -p: the value only in the index
        put('p.md', dirty)
        sh('add', '--', 'p.md')
        put('p.md', clean)
        case('--staged, the value only in the index (git add -p), work tree clean', run('staged'), 1)
        sh('reset', '-q', '--', 'p.md')
        # --diff of modified tracked files with names git would quote
        for k in ('non-ASCII name', 'non-ASCII directory', 'a name with \'"\''):
            put(names[k], dirty)
            case(f'--diff, a modified tracked file, {k}', run('diff', names[k]), 1)
            put(names[k], clean)
        put('新/n.md', dirty)
        case('--diff, an untracked file in a non-ASCII directory', run('diff', '.'), 1)
        os.remove(os.path.join(W, '新', 'n.md'))
        os.remove(os.path.join(W, 'del.md'))
        case('--diff, a deleted tracked file (status D: nothing to scan, control)', run('diff', 'del.md'), 0)
        case('--diff, the clean work tree (control)', run('diff', '.'), 0)
        # round 4, F12: Git LFS (a pointer in the index, the content in the LFS store), another clean filter, the hooks
        def png1(text):
            ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
            return (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 0, 0, 0, 0)) + ch(b'tEXt', b'Comment\x00' + text)
                    + ch(b'IDAT', zlib.compress(b'\x00\x00')) + ch(b'IEND', b''))
        def ok2(label, good, detail=''):
            nonlocal ok
            ok &= bool(good)
            print(f'  selftest git: {label}: {"ok" if good else "FAILED"}{detail}')
        ptxt = dirty.encode()
        oid = hashlib.sha256(ptxt).hexdigest()
        objp = os.path.join(G, 'lfs', 'objects', oid[:2], oid[2:4], oid)
        os.makedirs(os.path.dirname(objp), exist_ok=True)
        open(objp, 'wb').write(ptxt)
        put('ptr.csv', f'version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {len(ptxt)}\n')
        sh('add', '--', 'ptr.csv')
        case('--staged, an LFS pointer whose object (in the LFS store) holds a registration', run('staged'), 1)
        os.remove(objp)
        case('--staged, an LFS pointer whose object is not in the LFS store (ERROR)', run('staged'), 1)
        sh('rm', '-q', '--cached', '-f', '--', 'ptr.csv')
        os.remove(os.path.join(W, 'ptr.csv'))
        if subprocess.run(['git', 'lfs', 'version'], capture_output=True).returncode == 0:
            sh('lfs', 'install', '--local')
            put('.gitattributes', '*.png filter=lfs diff=lfs merge=lfs -text\n*.csv filter=lfs diff=lfs merge=lfs -text\n')
            put('plot.png', png1(f'cam {reg4}'.encode()))
            put('export.csv', f'stand,reg\n233,{reg4}\n')
            sh('add', '--', '.gitattributes', 'plot.png', 'export.csv')
            isptr = all(lfs_pointer(sh('cat-file', 'blob', ':' + f).stdout) for f in ('plot.png', 'export.csv'))
            case(f'--staged, a PNG and a CSV tracked by git-lfs (index blobs are LFS pointers: {isptr})', run('staged'), 1)
            put('plot.png', png1(b'cam clean'))
            put('export.csv', 'stand,reg\n233,clean\n')
            sh('add', '--', 'plot.png', 'export.csv')
            case('--staged, clean files tracked by git-lfs (control)', run('staged'), 0)
            sh('rm', '-q', '--cached', '-f', '--', '.gitattributes', 'plot.png', 'export.csv')
            for f in ('.gitattributes', 'plot.png', 'export.csv'):
                os.remove(os.path.join(W, f))
        else:
            print('  selftest git: git-lfs is not installed: the git-lfs cases are skipped (the pointer cases above ran)')
        sh('config', 'filter.rot13.clean', 'tr A-Za-z N-ZA-Mn-za-m')
        sh('config', 'filter.rot13.smudge', 'tr A-Za-z N-ZA-Mn-za-m')
        put('.gitattributes', '*.rot filter=rot13\n')
        put('r.rot', dirty)
        sh('add', '--', '.gitattributes', 'r.rot')
        hidden = reg4.encode() not in sh('cat-file', 'blob', ':r.rot').stdout
        case(f'--staged, a clean filter (rot13; the blob hides the value: {hidden}) - the work-tree file is read', run('staged'), 1)
        os.remove(os.path.join(W, 'r.rot'))
        case('--staged, the same with the work-tree file gone (ERROR)', run('staged'), 1)
        sh('rm', '-q', '--cached', '-f', '--', '.gitattributes', 'r.rot')
        os.remove(os.path.join(W, '.gitattributes'))
        inst = install_hooks(Git(W, env))
        ok2('the hooks install into the scratch repository', [n for n, _ in inst] == ['pre-commit', 'commit-msg'])
        put('p.md', dirty)
        r = sh('commit', '-q', '-a', '-m', 'selftest: hook', check=False)
        head = sh('cat-file', 'blob', 'HEAD:p.md').stdout
        ok2('git commit -a with a registration in a tracked file: refused by the pre-commit hook', r.returncode and reg4.encode() not in head,
            f' (git exit {r.returncode})')
        put('p.md', clean)
        put('m.md', clean)
        sh('add', '--', 'm.md')
        r = sh('commit', '-q', '-m', f'selftest: park {reg4} on 233', check=False)
        ok2('a commit message holding a registration: refused by the commit-msg hook', r.returncode, f' (git exit {r.returncode})')
        r = sh('commit', '-q', '-m', 'selftest: a clean note', check=False)
        ok2('a clean commit with a clean message passes both hooks (control)', r.returncode == 0, f' (git exit {r.returncode})')
    except Exception as e:                           # masked: the type and the line only
        import traceback
        ok = False
        print(f'  selftest git: ERROR {type(e).__name__} at line {traceback.extract_tb(e.__traceback__)[-1].lineno}')
    finally:
        shutil.rmtree(W, ignore_errors=True)
        shutil.rmtree(G, ignore_errors=True)
    h1 = hashlib.sha256(open(real_index, 'rb').read()).hexdigest() if os.path.isfile(real_index) else None
    print(f'  selftest git: scratch removed {not os.path.exists(W) and not os.path.exists(G)}; the real index unchanged {h0 == h1}')
    return ok


def selftest_identity_set():
    """round 4, N1: a COPY of this audit in a scratch tree under sha3d/out/ (deleted afterwards) whose observed-elsewhere
    directory is empty, partial, altered or holds an unknown file must refuse to run (exit 1, 'ERROR identity set
    incomplete'); with every local file it runs (exit 0 on a clean file). Labels and results only."""
    import tempfile, shutil
    E = tempfile.mkdtemp(prefix='audit_selftest_idset_', dir=os.path.join(SHA3D, 'out'))
    S = os.path.join(E, 'sha3d')
    ok = True
    files = sorted(os.path.relpath(p, OBS) for p in glob.glob(os.path.join(OBS, '**', '*'), recursive=True) if os.path.isfile(p))
    day = sorted(f for f in files if re.fullmatch(r'sha_observed_\d{4}-\d{2}-\d{2}\.json', f))
    def tree(obs_files, mutate=None):
        shutil.rmtree(S, ignore_errors=True)
        for rel in ('tools/sim/audit_identity.py', 'tools/sim/observed_overlay.py', 'data/lookup.js', 'data/sha_sim_inputs.json',
                    'js/aircraft/types.js', 'js/aircraft/fit.js'):
            os.makedirs(os.path.dirname(os.path.join(S, rel)), exist_ok=True)
            shutil.copy(os.path.join(SHA3D, rel), os.path.join(S, rel))
        o = os.path.join(S, 'refs', 'cache', 'observed_elsewhere')
        os.makedirs(o)
        for f in obs_files:
            os.makedirs(os.path.dirname(os.path.join(o, f)), exist_ok=True)
            shutil.copy(os.path.join(OBS, f), os.path.join(o, f))
        if mutate:
            mutate(o)
        os.makedirs(os.path.join(S, 'out'), exist_ok=True)
        p = os.path.join(S, 'out', 'clean.md')
        open(p, 'w').write('stand 233, aggregate only\n')
        r = subprocess.run([sys.executable, '-I', os.path.join(S, 'tools', 'sim', 'audit_identity.py'), '--files', p],
                           capture_output=True, text=True)
        return r.returncode, 'ERROR identity set incomplete' in r.stdout
    def trunc(o):                                    # still valid JSON, but no longer the bytes SOURCES.json lists
        q = os.path.join(o, day[0])
        open(q, 'ab').write(b'\n')
    try:
        for label, fl, mut, want in (('an empty observed_elsewhere directory', [], None, 1),
                                     ('only SOURCES.json', ['SOURCES.json'], None, 1),
                                     ('SOURCES.json and one day table (the other listed files missing)', ['SOURCES.json', day[-1]], None, 1),
                                     ('every file, one day table altered (differs from SOURCES.json)', files, trunc, 1),
                                     ('every file plus a file of an unknown kind', files, lambda o: open(os.path.join(o, 'x.bin'), 'wb').write(b'\x00\x01'), 1),
                                     ('every local file (control: a clean file passes)', files, None, 0)):
            rc, err = tree(fl, mut)
            good = rc == want and (err if want else not err)
            ok &= good
            print(f'  selftest identity set, {label}: {"ok" if good else "FAILED"} (exit {rc}, refused as incomplete: {err})')
    finally:
        shutil.rmtree(E, ignore_errors=True)
    print(f'  selftest identity set: scratch removed {not os.path.exists(E)}')
    return ok


def selftest(I, allow):
    """the audit must catch real values in every carrier and written form (F1-F3, F8; rounds 2 and 3) and pass clean text;
    values are taken from the identity set in memory, written to a scratch directory under sha3d/out/ (gitignored; the git
    cases also use a temporary GIT_DIR outside the repository), deleted, never printed."""
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
    os.makedirs(os.path.join(SHA3D, 'out'), exist_ok=True)
    d = tempfile.mkdtemp(prefix='audit_selftest_', dir=os.path.join(SHA3D, 'out'))
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
            ('clean: a word + number ("at nnn" style)', 'k4.md', f'stand {fl[:2].lower()} {fl[2:]} m', None),
            ('clean: a count after an ICAO code ("CES nnn, ...")', 'k5.md', f'| {cs3[:3]} {cs3[3:]}, CQH 62 |', None),
            ('clean: a reg split by a decimal ("Bn n.nn" style)', 'k6.md', f'{reg4[0]}{reg4[2]} {reg4[3]}.{reg4[4:]} m', None),
        ]
        cases += selftest_round2_cases(I, png, reg4, cs, cs3, fl, addr_d, t, fmt, uid_ovl)
        cases += selftest_round3_cases(I, png, reg4, cs, fl, addr, t, fmt)
        cases += selftest_round4_cases(I, png, reg4, cs, fl, t, fmt)
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
                                  ('a time stamp "YYYYMMDD_hhmmss" in a file name (round 3)', f'shot_{fmt(t, "%Y%m%d_%H%M%S")}.png', 'hit'),
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
        for label, data, want in (('a PNG with a clean private chunk', png([(b'prVt', b'clean')]), 2),          # round 3, F24
                                  ('a PNG with clean bytes after IEND', png([]) + b'clean trailer', 2),
                                  ('a PNG with standard chunks only (control)', png([(b'pHYs', b'\x00' * 9), (b'tEXt', b'Software\x00x')]), 0)):
            fp = os.path.join(d, 'r3.png')
            open(fp, 'wb').write(data)
            S = audit([(fp, None)], I, allow, quiet=True)
            good = S['exit'] == want
            ok &= good
            print(f'  selftest {label} -> exit {want}: {"ok" if good else "FAILED"} (exit {S["exit"]})')
        ok &= selftest_round4_review(I, allow, d, png)       # round 4, N3
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
    print(f'  selftest scratch directory removed: {not os.path.exists(d)}')
    ok &= selftest_git(I, allow, reg4)
    ok &= selftest_identity_set()
    print('selftest:', 'passed' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


HOOK_MARK = 'sha3d OD4 identity gate'


def hook_texts():
    """the pre-commit and commit-msg hooks (round 4, F12): 'git commit', 'commit -a', 'commit <path>' and the message itself
    are gated, not only a manual --staged run; git runs hooks at the top of the work tree with the commit's index
    (GIT_INDEX_FILE), which --staged reads. 'git commit --no-verify' skips hooks (the lead does not use it)."""
    py, me = sys.executable, os.path.abspath(__file__)
    head = (f'#!/bin/sh\n# {HOOK_MARK} (installed by sha3d/tools/sim/audit_identity.py --install-hooks). It refuses the commit on\n'
            '# an identity hit, a forbidden path, an ERROR (exit 1) or a REVIEW (exit 2); it prints counts and masked paths only.\n')
    return {'pre-commit': head + f'exec "{py}" -I "{me}" --staged\n',
            'commit-msg': head + f'exec "{py}" -I "{me}" --files "$1"\n'}


def install_hooks(g, force=False):
    """write the two hooks into the repository's hooks directory (core.hooksPath respected); an existing hook of another
    origin is not replaced unless force -> [(name, path)]"""
    d = g.hooks_dir()
    os.makedirs(d, exist_ok=True)
    out = []
    for name, txt in hook_texts().items():
        p = os.path.join(d, name)
        if os.path.exists(p) and HOOK_MARK not in open(p, encoding='utf-8', errors='replace').read() and not force:
            raise GitError(f'a {name} hook of another origin exists: merge it by hand or pass --force')
        open(p, 'w', encoding='utf-8').write(txt)
        os.chmod(p, 0o755)
        out.append((name, p))
    return out


def default_git():
    """the repository of the current directory (a hook runs at the top of the work tree it gates), else the one holding
    this script"""
    for c in (os.getcwd(), REPO):
        try:
            return Git(Git(c).top())
        except GitError:
            continue
    return Git(REPO)


def mode_items(mode, g, files=None, pathspec='sha3d'):
    """the items of one mode (main() and the selftest's scratch repositories use the same code path)"""
    if mode == 'files':
        return [(os.path.relpath(os.path.abspath(f), REPO), None) for f in files]
    if mode == 'staged':
        return staged_items(g)
    if mode == 'docs':
        return [(os.path.relpath(p, REPO), None) for p in sorted(glob.glob(os.path.join(SHA3D, 'docs', '**', '*'), recursive=True))
                if os.path.isfile(p)]
    return diff_items(g, pathspec)


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
    ap.add_argument('--install-hooks', action='store_true', help='install the pre-commit (--staged) and commit-msg (--files) hooks')
    ap.add_argument('--print-hooks', action='store_true', help='print the two hooks (nothing is installed)')
    ap.add_argument('--force', action='store_true', help='with --install-hooks: replace hooks of another origin')
    a = ap.parse_args()
    if a.print_hooks:
        for name, txt in hook_texts().items():
            print(f'--- {name}\n{txt}')
        sys.exit(0)
    if a.install_hooks:
        try:
            for name, p in install_hooks(default_git(), a.force):
                print(f'installed {name}: {p}')
        except GitError as e:
            print(f'ERROR: {e}')
            sys.exit(1)
        sys.exit(0)
    try:                                             # a non-UTF-8 path name is printed escaped, never a crash
        sys.stdout.reconfigure(errors='backslashreplace')
    except AttributeError:
        pass

    try:
        I = load_identities()
    except IdentitySetError as e:                    # round 4, N1: never compare with an empty or partial set
        print(f'ERROR identity set incomplete: {e}')
        print('exit 1: the identity set could not be loaded completely (nothing was audited)')
        sys.exit(1)
    allow = published_flights()
    c = I.counts()
    print(f'identity set: {I.total()} values from {I.files} local identity tables '
          f'({", ".join(f"{k} {c[k]}" for k in CLASSES)}; registrations without a digit {len(I.reg_alpha)}); '
          f'published SHA-row flight allow-list {len(allow)}; fingerprint sources '
          + ', '.join(f'{k} {v}' for k, v in sorted(I.fp_sources.items())) + f'; airline names {len(I.al_names)}')
    print(f'  {I.summary}')
    for n in I.notes:
        print(f'  note: {n}')
    if a.selftest:
        selftest(I, allow)
    try:
        items = mode_items('files' if a.files else 'staged' if a.staged else 'docs' if a.docs else 'diff',
                           default_git() if (a.staged or a.diff or not (a.files or a.docs)) else Git(), files=a.files, pathspec=a.path)
    except GitError as e:                            # round 3, F12: a git failure is an ERROR, never 0 files
        print(f'  ERROR git: {e}')
        print('exit 1: the file set could not be listed (nothing was audited)')
        sys.exit(1)
    S = audit(items, I, allow, net=a.net, reviewed=a.reviewed)
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
