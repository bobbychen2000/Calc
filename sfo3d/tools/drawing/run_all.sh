#!/usr/bin/env bash
# One command for the whole 2-D drawing system:
#   1. extract everything the 3-D app places on the ground (headless app -> out/draw/scene2d.json)
#   2. measure deviations against the imagery (Google screenshots; NAIP when refs/cache/naip/ holds it)
#   3. physical clearance audit (bridges, aircraft, buildings, GSE, pavement)
#   4. drawing sheets: docs/drawings/*.svg|png (vector, committable) + out/draw/sheets/* (over imagery, local only)
#   5. docs/drawings/report.md
# Usage: tools/drawing/run_all.sh            (all steps)
#        SKIP_EXTRACT=1 tools/drawing/run_all.sh   (reuse out/draw/scene2d.json)
# Needs: node + playwright chromium (see CLAUDE.md), python3 with numpy scipy opencv shapely matplotlib pillow
# (pyproj + rasterio for GeoTIFF NAIP). SOFTGL=1 is set for the extraction (Mesa llvmpipe); unset it on a GPU machine.
set -euo pipefail
cd "$(dirname "$0")/../.."
if [ -z "${SKIP_EXTRACT:-}" ]; then
  echo "== 1/5 extract (headless app, ~4-6 min on llvmpipe)"
  W=${W:-320} H=${H:-200} SOFTGL=${SOFTGL-1} node livetest.mjs jobs/extract2d.mjs 2>&1 | grep -v "ERR_CERT\|willReadFrequently" || true
  test -s out/draw/scene2d.json || { echo "extraction failed"; exit 1; }
fi
if [ -z "${SKIP_EXTRACT:-}" ] && [ "${TRACE:-1}" != 0 ]; then
  echo "== 1b/5 moving-traffic trace (live mode + mock relay, ~6 min)"
  W=${W:-320} H=${H:-200} SOFTGL=${SOFTGL-1} TRACE_N=${TRACE_N:-40} TRACE_DT=${TRACE_DT:-3} node livetest.mjs jobs/trace2d.mjs 2>&1 | grep -v "ERR_CERT\|willReadFrequently" | tail -3 || true
fi
cd tools/drawing
echo "== 2/5 deviations";  python3 -W ignore background.py; python3 -W ignore measure.py; python3 -W ignore selftest.py
echo "== 3/5 audit";       python3 -W ignore audit.py; python3 -W ignore trace_audit.py
echo "== 4/5 sheets";      rm -rf ../../docs/drawings/crops ../../out/draw/crops; python3 -W ignore sheets.py
echo "== 5/5 report";      python3 -W ignore report.py
echo "done: docs/drawings/report.md, docs/drawings/*.png|svg, out/draw/sheets/, out/draw/crops/"
