#!/bin/sh
# Validate the live traffic engine (js/live/traffic.js + ground.js) on REAL recorded traffic:
#   1. tools/live/build_stream.py  -- the relay's own merge replayed offline -> the SSE event sequence + SFO's plan
#   2. tools/live/replay_events.py -- ground truth (arrivals, departures, go-arounds, stops, push-backs)
#   3. tools/live/replay_engine.mjs -- the app's engine in node on a simulated clock (variants below)
#   4. tools/live/replay_score.py  -- phase / runway / touchdown / liftoff / stand-vs-SFO / kinematics / overlaps
# Usage: sh tools/live/replay_engine_all.sh 2026-09-24T15:25:30Z 2026-09-24T16:30:00Z refs/cache/replay_day2
# Needs CANVAS_MODULE=/abs/path/node_modules/@napi-rs/canvas/index.js (see replay_engine.mjs).
set -e
cd "$(dirname "$0")/../.."
FROM=$1; UNTIL=$2; D=${3:-refs/cache/replay_engine}
mkdir -p "$D"
python3 tools/live/build_stream.py --from "$FROM" --until "$UNTIL" --out "$D/stream.jsonl.gz" > "$D/build.log"
REPLAY_FROM=$FROM REPLAY_UNTIL=$UNTIL python3 tools/live/replay_events.py --json "$D/events.json" > "$D/events.txt"
node tools/live/replay_engine.mjs --stream "$D/stream.jsonl.gz" --out "$D/engine.jsonl.gz" > "$D/engine.log" 2>&1 &
node tools/live/replay_engine.mjs --stream "$D/stream.jsonl.gz" --no-plan --out "$D/engine_noplan.jsonl.gz" > "$D/engine_noplan.log" 2>&1 &
DELAY=1500 node tools/live/replay_engine.mjs --stream "$D/stream.jsonl.gz" --out "$D/engine_d15.jsonl.gz" > "$D/engine_d15.log" 2>&1 &
wait
for v in engine engine_noplan engine_d15; do
  REPLAY_FROM=$FROM REPLAY_UNTIL=$UNTIL python3 tools/live/replay_score.py "$D/$v.jsonl.gz" --json "$D/score_$v.json" > "$D/score_$v.txt"
done
echo "scores: $D/score_*.json"
