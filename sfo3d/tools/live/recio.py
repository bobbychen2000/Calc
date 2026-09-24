"""Read recorder files (tools/live/record.py, sfo_live_server.py --record), including the hour still being written
(no gzip end marker yet) and files where a killed writer left a truncated gzip member before a new one."""
import json, zlib, glob, os


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


def lines(path):
    """Yield the JSON records of one file. On a corrupt/truncated member (writer killed mid-hour, then a new writer
    appended a member) keep everything decodable before the damage (re-read in 1 KiB steps, so at most ~1 KiB of
    compressed data is lost) and resynchronise at the next gzip header."""
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
    for l in bytes(out).split(b'\n'):
        if l.strip():
            try:
                yield json.loads(l)
            except ValueError:
                pass   # partial line at a truncation point


def records(provider=None, root=os.path.join(os.path.dirname(__file__), '..', '..', 'refs', 'cache', 'rec')):
    for p in sorted(glob.glob(os.path.join(root, f'{provider or "*"}_*.jsonl.gz'))):
        yield from lines(p)
