"""Read recorder files: record.py / relay --record hours (.jsonl.gz, including the hour still being written and files
where a killed writer left a truncated gzip member) and the committed sfo3d rec_pack hours (.jsonl.xz).

Forked from sfo3d/tools/live/recio.py @ a967f9b. Kept: the robust gzip member reader. Changed: lines() also reads
.jsonl.xz (lzma; sfo3d tools/cache/sync.py writes the rec_pack with xz -9e; 9 of its 111 hours are empty 32-byte xz
streams, which yield nothing); records() defaults to the rec_pack and adsb.lol only.
"""
import glob, json, lzma, os, zlib

REC_PACK = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..',
                                         'sfo3d', 'refs', 'cache', 'rec_pack'))


def _member(raw, pos, ch):
    """Decompress the gzip member starting at pos in steps of ch bytes.
    -> (output, end position or None when the member is truncated/corrupt, ok)"""
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = bytearray()
    i = pos
    try:
        while i < len(raw) and not d.eof:
            out += d.decompress(raw[i:i + ch])
            i += ch
    except zlib.error:
        return out, None, False
    if d.eof:   # unused_data is the rest of the last chunk fed (not of the file): the member ended at i - len(it)
        return out, min(i, len(raw)) - len(d.unused_data), True
    return out, None, True          # the hour still being written: flushed data, no end marker yet


def _gz_lines(path):
    with open(path, 'rb') as f:
        raw = f.read()
    out = bytearray()
    pos = 0
    while pos < len(raw):
        o, end, ok = _member(raw, pos, 1 << 16)
        if not ok:
            o, _, _ = _member(raw, pos, 1024)
        out += o
        if end is not None:
            pos = end
            continue
        nxt = raw.find(b'\x1f\x8b\x08', pos + 1)
        if nxt < 0:
            break
        out += b'\n'
        pos = nxt
    return bytes(out).split(b'\n')


def _xz_lines(path):
    try:
        with lzma.open(path, 'rb') as f:
            for l in f:
                yield l
    except (lzma.LZMAError, EOFError):
        return                       # a truncated stream: keep what was decodable


def lines(path):
    """Yield the JSON records of one file (.jsonl.gz or .jsonl.xz); undecodable partial lines are skipped."""
    src = _xz_lines(path) if path.endswith('.xz') else _gz_lines(path)
    for l in src:
        if l.strip():
            try:
                yield json.loads(l)
            except ValueError:
                pass   # partial line at a truncation point


def records(provider='adsblol', root=REC_PACK):
    for p in sorted(glob.glob(os.path.join(root, f'{provider}_*.jsonl.gz')) +
                    glob.glob(os.path.join(root, f'{provider}_*.jsonl.xz'))):
        yield from lines(p)
