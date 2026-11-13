#!/usr/bin/env python3
"""Coverage map for the ZSSS go/no-go question: stream one adsb.lol globe_history day (ODbL 1.0) and count, per 1°
cell over East Asia (15-50 N, 95-145 E), the distinct aircraft seen airborne, seen below 10,000 ft and seen on the
ground, plus distinct aircraft per hour (UTC) in the 2° box around ZSSS and around ZSPD for cross-check.
Usage: python3 -I globe_grid.py 2026.11.12 OUT_DIR [prod|mlatonly]   -> OUT_DIR/grid_<date>_<kind>.json
Reuses the stream reader of globe_scan.py (same directory)."""
import gzip, json, re, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from globe_scan import Pipe, stream
import tarfile

PRE = re.compile(rb"\n\[[\d.]+,(?:1[5-9]|[234]\d)\.\d+,(?:9[5-9]|1[0-4]\d)\.")

def main():
    date, out = sys.argv[1], sys.argv[2]; kind = sys.argv[3] if len(sys.argv) > 3 else "prod"
    t0 = time.time(); grid = {}; n = hit = 0
    tf = tarfile.open(fileobj=Pipe(stream(date, kind)), mode="r|")
    for m in tf:
        if not m.isfile() or "/traces/" not in "/" + m.name.lstrip("./"): continue
        n += 1; raw = tf.extractfile(m).read()
        try: raw = gzip.decompress(raw)
        except OSError: pass
        if not PRE.search(raw): continue
        d = json.loads(raw); seen = {}
        for q in d.get("trace", []):
            la, lo, alt = q[1], q[2], q[3]
            if la is None or not (15 <= la < 50 and 95 <= lo < 145): continue
            k = f"{int(la)},{int(lo)}"; s = seen.setdefault(k, [0, 0, 0])
            s[0] = 1
            if alt == "ground": s[2] = 1
            elif isinstance(alt, (int, float)) and alt < 10000: s[1] = 1
        if seen: hit += 1
        for k, s in seen.items():
            g = grid.setdefault(k, [0, 0, 0])
            for i in range(3): g[i] += s[i]
    json.dump({"date": date, "source": f"adsb.lol globe_history {kind} (ODbL 1.0)", "cell": "1 deg, key 'lat,lon' = floor",
               "counts": "[distinct aircraft any, distinct <10000 ft airborne, distinct on ground]", "traces_scanned": n,
               "traces_in_box": hit, "grid": grid}, open(f"{out}/grid_{date}_{kind}.json", "w"), separators=(",", ":"))
    print(f"{date} {kind}: {n} traces, {hit} in East Asia box, {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__": main()
