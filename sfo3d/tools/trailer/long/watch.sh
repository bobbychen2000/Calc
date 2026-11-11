#!/bin/sh
# wait for the next finished/failed shot (or batch end); print one status line
L=/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/long
n0=$(grep -cE "^DONE|^PARTIAL|^Error:|^NOEVENT|^NOGATE" $L/run_long.log)
until [ $(grep -cE "^DONE|^PARTIAL|^Error:|^NOEVENT|^NOGATE" $L/run_long.log) -gt $n0 ] || grep -q ALLDONE $L/run_long.log || ! pgrep -f run_long.sh >/dev/null; do sleep 20; done
echo "$(grep -E '^DONE|^PARTIAL|^Error:|^NOEVENT|^NOGATE|ALLDONE' $L/run_long.log | tail -1) | shots=$(ls $L/shots/shot_*.mp4 | grep -vc part) | $(pgrep -f run_long.sh >/dev/null && echo running || echo BATCH-STOPPED) | $(date -u +%H:%M) | free=$(df -h / | awk 'NR==2{print $4}')"
