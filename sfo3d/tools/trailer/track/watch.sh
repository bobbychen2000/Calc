#!/bin/sh
# wait until the batch moves to the next shot (or finishes), then print one status line per finished shot
T=/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/track
n0=$(grep -c "^=== " $T/run.log)
while [ $(grep -c "^=== " $T/run.log) -le $((n0 + ${STEP:-1} - 1)) ] && ! grep -q ALLDONE $T/run.log; do sleep 20; done
grep -E "^=== |^DONE|PARTIAL|LATE|APPERR|Error|LOST" $T/run.log | tail -4 | cut -c1-160
echo "done: $(ls $T/shots/shot_*.mp4 2>/dev/null | wc -l)/23  $(date -u +%T)"
