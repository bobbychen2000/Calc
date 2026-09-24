#!/bin/sh
# Traffic audit pipeline (docs/research/traffic_audit.md). Re-run after the recorder has captured more traffic.
# Needs: python3 (numpy, scipy), node >= 18, and a canvas module for the node replay:
#   (cd /some/scratch && npm i @napi-rs/canvas) ; export CANVAS_MODULE=/some/scratch/node_modules/@napi-rs/canvas/index.js
set -e
# freeze the window for a consistent run, e.g.  REPLAY_UNTIL=2026-09-24T09:15:00Z sh tools/live/replay_all.sh
cd "$(dirname "$0")/../.."
python3 tools/live/replay_wx.py fetch || true                   # METAR + D-ATIS snapshot (optional)
python3 tools/live/replay_events.py > refs/cache/replay/events.txt   # ground truth: arrivals, departures, stops, ...
python3 tools/live/replay_datachar.py > /dev/null                # data characterisation -> refs/cache/replay/datachar.json
python3 tools/live/gatecheck.py check --every 120 --json refs/cache/replay/gatecheck_every120.json > /dev/null 2>&1 || true  # SFO stand truth (other agent's tool)
python3 tools/live/replay_feed.py relay5 relay1 lol7             # payload sequences as the app would receive them
[ -f refs/cache/replay/routes.json ] || python3 tools/live/replay_feed.py routes
node tools/live/replay_app.mjs --dump-mask
for v in "relay5 7500 --no-routes app_relay5_noroutes" "relay5 7500 x app_relay5" "relay5 7500 --paved-fixed app_relay5_paved" "relay1 7500 x app_relay1" "lol7 9500 --no-routes app_lol7"; do
  set -- $v; extra=$3; [ "$extra" = x ] && extra=""
  node tools/live/replay_app.mjs --polls refs/cache/replay/polls_$1.jsonl --delay $2 --out refs/cache/replay/$4.jsonl.gz $extra
  python3 tools/live/replay_audit.py refs/cache/replay/$4.jsonl.gz --json refs/cache/replay/audit_$4.json > /dev/null
done
python3 tools/live/replay_latency.py > refs/cache/replay/latency.txt
python3 tools/live/replay_model.py > /dev/null
python3 tools/live/replay_report.py                              # key numbers for the report -> refs/cache/replay/summary.md
