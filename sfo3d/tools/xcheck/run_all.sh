#!/bin/sh
# Regenerate the stand / runway cross-check (docs/research/stands_xcheck.md) from scratch.
# Network: Overpass (OSM), gateway.x-plane.com, nfdc.faa.gov, airnav.com. Everything downloaded lands in refs/cache/
# (gitignored). Step 3 reuses the gate-truth tool (tools/live/gatecheck.py, read-only) on the ADS-B recording and the
# newest flysfo snapshot already cached by that tool; it does not fetch flysfo itself.
set -e
cd "$(dirname "$0")/../.."
python3 tools/xcheck/fetch_osm.py            # 1. OSM raw -> refs/cache/osm/overpass_ksfo_latest.json
python3 tools/xcheck/fetch_xplane.py         #    X-Plane Gateway recommended pack -> refs/cache/xplane/apt_<id>.dat
mkdir -p refs/cache/xcheck/faa
[ -f refs/cache/xcheck/faa/03_Sep_2026_APT_CSV.zip ] || \
  curl -sS -o refs/cache/xcheck/faa/03_Sep_2026_APT_CSV.zip https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip
curl -sS -A 'Mozilla/5.0 sfo3d-xcheck' -o refs/cache/xcheck/faa/airnav_KSFO.html https://www.airnav.com/airport/KSFO
python3 - <<'EOF'
import re, html
s = open('refs/cache/xcheck/faa/airnav_KSFO.html', errors='replace').read()
t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', s, flags=re.S)
t = re.sub(r'<br\s*/?>|</p>|</tr>|</h\d>|</li>', '\n', t); t = re.sub(r'</td>', ' | ', t)
t = re.sub(r'<[^>]+>', '', t); t = html.unescape(t); t = re.sub(r'[ \t]+', ' ', t); t = re.sub(r'\n\s*\n+', '\n', t)
open('refs/cache/xcheck/faa/airnav_KSFO.txt', 'w').write(t)
EOF
python3 tools/xcheck/parse_osm.py            # 2. parse
python3 tools/xcheck/parse_aptdat.py
python3 tools/live/gatecheck.py check --every 120 --json refs/cache/xcheck/gatecheck_every120.json > /dev/null   # 3.
python3 tools/xcheck/adsb_evidence.py > /dev/null
python3 tools/xcheck/compare_stands.py       # 4. compare
python3 tools/xcheck/compare_runways.py > /dev/null
python3 tools/xcheck/figs.py                 # 5. overlays (gitignored, contain ODbL/GPL geometry)
python3 tools/xcheck/make_report.py          # 6. refresh the tables in the report
