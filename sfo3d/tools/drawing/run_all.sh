#!/usr/bin/env bash
# One command for the whole 2-D drawing system:
#   1. extract everything the 3-D app places on the ground (headless app -> out/draw/scene2d.json)
#   2. measure deviations against the imagery (NAIP from refs/cache/naip/ - primary, public; the Google screenshots
#      re-registered to NAIP per screenshot by imreg.py)
#   3. physical clearance audit (bridges, aircraft, buildings, GSE, pavement)
#   4. drawing sheets: docs/drawings/*.svg|png (vector, committable) + out/draw/sheets/* (over imagery, local only)
#   5. docs/drawings/report.md
# Usage: tools/drawing/run_all.sh            (all steps)
#        SKIP_EXTRACT=1 tools/drawing/run_all.sh   (reuse out/draw/scene2d.json + trace.json; the tools refuse a scene
#                                                   in another world frame, report.py a stale one - see common.py)
#        SKIP_TRACE=1 / TRACE=0                    (extract, but no moving-traffic trace)
#        APP_REV=<commit> (default HEAD) | APP_REV=worktree     app source, see below
#        DRAW_OUT=<dir> DRAW_DOCS=<dir>            other output directories (default out/draw, docs/drawings), e.g. to
#                                                   run while another run owns the defaults
# Needs: node + playwright chromium (see CLAUDE.md), python3 with numpy scipy opencv shapely matplotlib pillow
# (pyproj + rasterio for GeoTIFF NAIP). SOFTGL=1 is set for the extraction (Mesa llvmpipe); unset it on a GPU machine.
# About 1-1.5 h on llvmpipe (extraction 5-15 min, trace 15-20 min, deviations 25 min, sheets 35-40 min).
#
# App source: the extraction and the trace serve a clean `git archive` of a commit (APP_REV, default HEAD) from
# $DRAW_OUT/app_snapshot, so that edits other people / agents make to the working tree during the run cannot leak into
# (or half into) the scene; the drawings then describe that commit exactly, and report.py lists the app files that
# differ in the working tree. APP_REV=worktree serves the working tree itself (to check an uncommitted change;
# report.py then refuses a scene whose inputs changed during or after the extraction, unless ALLOW_STALE=1).
# One run per output directory at a time (flock on $DRAW_OUT/.run_all.lock). Edit this file only by writing a new file
# and renaming it over this one: a running bash reads its script by byte offset.
set -euo pipefail
cd "$(dirname "$0")/../.."
export DRAW_OUT=${DRAW_OUT:-$PWD/out/draw}; export DRAW_DOCS=${DRAW_DOCS:-$PWD/docs/drawings}
case "$DRAW_OUT" in /*) ;; *) DRAW_OUT=$PWD/$DRAW_OUT ;; esac; case "$DRAW_DOCS" in /*) ;; *) DRAW_DOCS=$PWD/$DRAW_DOCS ;; esac
mkdir -p "$DRAW_OUT" "$DRAW_DOCS"
exec 9>"$DRAW_OUT/.run_all.lock"
flock -n 9 || { echo "another run_all.sh is writing $DRAW_OUT - wait for it, or set DRAW_OUT / DRAW_DOCS"; exit 1; }
APP_REV=${APP_REV:-HEAD}
if [ "$APP_REV" != worktree ] && [ -z "${SKIP_EXTRACT:-}" ]; then
  SHA=$(git rev-parse --verify "$APP_REV^{commit}")
  PREFIX=$(git rev-parse --show-prefix); TOP=$(git rev-parse --show-toplevel)
  SNAP=$DRAW_OUT/app_snapshot
  if [ "$(cat "$SNAP/.rev" 2>/dev/null)" != "$SHA" ]; then
    rm -rf "$SNAP"; mkdir -p "$SNAP"
    # the app is everything live.html loads: js/, data/, live.html, live.css
    git -C "$TOP" archive --format=tar "$SHA:${PREFIX%/}" js data live.html live.css | tar -x -C "$SNAP"
    echo "$SHA" > "$SNAP/.rev"
  fi
  export ROOT=$SNAP APP_REV_SHA=$SHA
  echo "   app source: git archive of $SHA ($APP_REV) in ${SNAP#$PWD/}"
fi
if [ -z "${SKIP_EXTRACT:-}" ]; then
  echo "== 1/5 extract (headless app, ~5-15 min on llvmpipe)  $(date -u +%H:%M)Z"
  # a failed extraction must not leave the previous scene in place for the later steps to measure
  rm -f "$DRAW_OUT/scene2d.json"
  W=${W:-320} H=${H:-200} SOFTGL=${SOFTGL-1} node livetest.mjs jobs/extract2d.mjs 2>&1 | grep -v "ERR_CERT\|willReadFrequently" || true
  test -s "$DRAW_OUT/scene2d.json" || { echo "extraction failed"; exit 1; }
fi
if [ -z "${SKIP_EXTRACT:-}" ] && [ -z "${SKIP_TRACE:-}" ] && [ "${TRACE:-1}" != 0 ]; then
  echo "== 1b/5 moving-traffic trace (live mode + mock relay, ~15-20 min on llvmpipe)  $(date -u +%H:%M)Z"
  rm -f "$DRAW_OUT/trace.json"
  W=${W:-320} H=${H:-200} SOFTGL=${SOFTGL-1} TRACE_N=${TRACE_N:-40} TRACE_DT=${TRACE_DT:-3} node livetest.mjs jobs/trace2d.mjs 2>&1 | grep -v "ERR_CERT\|willReadFrequently" | tail -3 || true
fi
cd tools/drawing
python3 -W ignore -c "from common import scene, provenance; scene(); p = provenance(); print('   scene: frame', p['frame'], 'git', p['git'], '(' + p['appSource'] + ')', 'extracted', p['generated'][:16], 'stale inputs:', p['stale'], 'changed during extraction:', p['changedDuring'], 'differing in the working tree:', len(p['worktreeChanged']))"
echo "== 2/5 deviations  $(date -u +%H:%M)Z";  python3 -W ignore background.py; python3 -W ignore imreg.py; python3 -W ignore measure.py; python3 -W ignore selftest.py
echo "== 3/5 audit  $(date -u +%H:%M)Z";       python3 -W ignore audit.py; python3 -W ignore trace_audit.py
echo "== 4/5 sheets  $(date -u +%H:%M)Z";      rm -rf "$DRAW_DOCS/crops" "$DRAW_OUT/crops"; python3 -W ignore sheets.py
echo "== 5/5 report  $(date -u +%H:%M)Z";      python3 -W ignore report.py
echo "done $(date -u +%H:%M)Z: ${DRAW_DOCS#$PWD/}/report.md, ${DRAW_DOCS#$PWD/}/*.png|svg, ${DRAW_OUT#$PWD/}/sheets/, ${DRAW_OUT#$PWD/}/crops/"
