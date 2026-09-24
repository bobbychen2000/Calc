"""Read recorder files (tools/live/record.py), including the hour still being written (no gzip end marker yet)."""
import json, zlib, glob, os

def lines(path):
    """Decompress chunk by chunk, keeping partial output; on a corrupt/truncated gzip member (recorder killed
    mid-hour, then restarted and appending a new member) resynchronise at the next gzip header."""
    with open(path, 'rb') as f:
        raw = f.read()
    out = bytearray(); pos = 0; CH = 1 << 16
    while pos < len(raw):
        d = zlib.decompressobj(16 + zlib.MAX_WBITS); i = pos; ok = True
        try:
            while i < len(raw) and not d.eof:
                out += d.decompress(raw[i:i + CH]); i += CH
        except zlib.error:
            ok = False
        if ok and d.eof:
            pos = len(raw) - len(d.unused_data)
            continue
        nxt = raw.find(b'\x1f\x8b\x08', pos + 1)
        if nxt < 0:
            break
        out += b'\n'; pos = nxt
    for l in bytes(out).split(b'\n'):
        if l.strip():
            try: yield json.loads(l)
            except ValueError: pass   # partial line at a truncation point

def records(provider=None, root=os.path.join(os.path.dirname(__file__), '..', '..', 'refs', 'cache', 'rec')):
    for p in sorted(glob.glob(os.path.join(root, f'{provider or "*"}_*.jsonl.gz'))):
        yield from lines(p)
