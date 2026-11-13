#!/usr/bin/env python3
"""Live coverage recorder for ZSSS (Phase 0 go/no-go). Polls, within each provider's published limits:
  adsb.lol  /v2/point/LAT/LON/60   every 180 s (ODbL 1.0; keyless quota "500 requests/day per IP",
            https://api.adsb.lol/api/openapi.json, read 2026-11-13 -> 480/day)
  adsb.fi   /api/v2/lat/../lon/../dist/60 every 15 s (personal non-commercial; may not be relicensed -> never committed)
  OpenSky   /api/states/all bbox  every 300 s (anonymous: 400 credits/day; non-commercial terms -> never committed)
Writes one gz JSONL per provider per UTC hour under OUT/<provider>/YYYYmmddHH.jsonl.gz: {"t": unix, "ac": [...]}.
Stdlib only. Usage: python3 -I live_rec.py OUT_DIR HOURS
Centre: OurAirports ZSSS 31.198104 N 121.33426 E, 174 m from the AIP ARP N31°11.8' E121°20.1'
(docs/phase0/aip.md); irrelevant at a 60 NM radius."""
import gzip, json, os, sys, time, urllib.request, ssl

LAT, LON = 31.198104, 121.33426
OUT = sys.argv[1]; HOURS = float(sys.argv[2])
UA = {"User-Agent": "sha3d-coverage-recorder/0.1 (research; low rate)"}
P = {
    "adsblol": (180, f"https://api.adsb.lol/v2/point/{LAT}/{LON}/60", "ac"),
    "adsbfi": (15, f"https://opendata.adsb.fi/api/v2/lat/{LAT}/lon/{LON}/dist/60", "aircraft"),
    "opensky": (300, "https://opensky-network.org/api/states/all?lamin=30.2&lomin=120.2&lamax=32.2&lomax=122.5", "states"),
}
ctx = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt")
nxt = {k: 0 for k in P}; end = time.time() + HOURS * 3600
while time.time() < end:
    now = time.time()
    for k, (iv, url, key) in P.items():
        if now < nxt[k]: continue
        nxt[k] = now + iv
        rec = {"t": round(now, 1)}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20, context=ctx) as r:
                d = json.load(r); rec["ac"] = d.get(key) or []; rec["http"] = r.status
        except Exception as e:
            rec["err"] = str(e)[:200]
        os.makedirs(f"{OUT}/{k}", exist_ok=True)
        with gzip.open(f"{OUT}/{k}/{time.strftime('%Y%m%d%H', time.gmtime(now))}.jsonl.gz", "at") as f:
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")
    time.sleep(1)
