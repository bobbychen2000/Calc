#!/usr/bin/env python3
"""Stream one adsb.lol globe_history day (GitHub release adsblol/globe_history_2026, ODbL 1.0) and keep only the
aircraft traces that pass within R_KM of Shanghai Hongqiao (ZSSS). Nothing but the filtered traces is written.

Usage: python3 -I globe_scan.py 2026.11.12 OUT_DIR [prod|mlatonly]
Output: OUT_DIR/zsss_<date>.json.gz = {"date", "source", "arp", "r_km", "traces": [{icao, r, t, desc, dbFlags, ts,
        pts: [[t_unix, lat, lon, alt|'ground'|None, gs, trk, flags, src, callsign|None], ...]}]}
Trace point layout per readsb (wiedehopf/readsb, globe_history trace_full): [dt, lat, lon, alt, gs, track, flags,
vrate, aircraft{}|null, type, geom_alt, geom_rate, ias, roll].
The ARP is the OurAirports value for ZSSS, to be replaced by the AIP value once verified (docs/PLAN.md §1).
"""
import gzip, json, math, re, subprocess, sys, tarfile, time

ARP = (31.198104, 121.33426)
R_KM = 150.0
BASE = "https://github.com/adsblol/globe_history_2026/releases/download"
# cheap byte prefilter: any "lat,lon" pair inside a box around the ARP (±1.5° lat, ±1.8° lon)
PRE = re.compile(rb"(?:29\.[7-9]|3[012]\.)\d*,(?:119\.[5-9]|12[0-3]\.)")

def dist_km(a, b, c, d):
    p = math.pi / 180
    x = (d - b) * p * math.cos((a + c) / 2 * p); y = (c - a) * p
    return 6371.0 * math.hypot(x, y)

def stream(date, kind):
    tag = f"v{date}-planes-readsb-{kind}-0"
    for suf in ("aa", "ab", "ac", "ad", "ae"):
        url = f"{BASE}/{tag}/{tag}.tar.{suf}"
        p = subprocess.Popen(["curl", "-sS", "-L", "-f", "--retry", "4", url], stdout=subprocess.PIPE)
        got = 0
        while True:
            b = p.stdout.read(1 << 20)
            if not b: break
            got += len(b); yield b
        p.wait()
        if got == 0: return

class Pipe:
    def __init__(self, gen): self.g = gen; self.buf = b""
    def read(self, n=-1):
        while n < 0 or len(self.buf) < n:
            try: self.buf += next(self.g)
            except StopIteration: break
        if n < 0: out, self.buf = self.buf, b""
        else: out, self.buf = self.buf[:n], self.buf[n:]
        return out

def main():
    date, out = sys.argv[1], sys.argv[2]
    kind = sys.argv[3] if len(sys.argv) > 3 else "prod"
    t0 = time.time(); n = hit = 0; traces = []
    tf = tarfile.open(fileobj=Pipe(stream(date, kind)), mode="r|")
    for m in tf:
        if not m.isfile() or "/traces/" not in "/" + m.name.lstrip("./"): continue
        n += 1
        raw = tf.extractfile(m).read()
        try: raw = gzip.decompress(raw)
        except OSError: pass
        if not PRE.search(raw): continue
        d = json.loads(raw); ts = d.get("timestamp", 0); pts = []; cs = None
        for q in d.get("trace", []):
            if q[1] is None: continue
            if isinstance(q[8], dict) and q[8].get("flight"): cs = q[8]["flight"].strip()
            if dist_km(ARP[0], ARP[1], q[1], q[2]) <= R_KM:
                pts.append([round(ts + q[0], 1), q[1], q[2], q[3], q[4], q[5], q[6], q[9] if len(q) > 9 else None, cs])
        if pts:
            hit += 1
            traces.append({"icao": d.get("icao"), "r": d.get("r"), "t": d.get("t"), "desc": d.get("desc"),
                           "dbFlags": d.get("dbFlags"), "ts": ts, "pts": pts})
    res = {"date": date, "source": f"adsb.lol globe_history {kind} (ODbL 1.0)", "arp": ARP, "r_km": R_KM,
           "n_traces_scanned": n, "traces": traces}
    with gzip.open(f"{out}/zsss_{date}_{kind}.json.gz", "wt") as f: json.dump(res, f, separators=(",", ":"))
    print(f"{date} {kind}: scanned {n} traces, {hit} within {R_KM} km, {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__": main()
