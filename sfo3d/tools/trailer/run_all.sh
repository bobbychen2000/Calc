#!/bin/sh
# trailer batch: one Chromium (Xvfb + Mesa llvmpipe) per shot; skips shots already rendered
cd /home/user/Calc/sfo3d
for s in ${SHOTS:-aerial gates tower night taxi arrival takeoff}; do
  [ -s /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/shot_$s.mp4 ] && { echo "skip $s"; continue; }
  echo "=== $s $(date -u +%T)"
  XGL=1 Q=ultra OUT=/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer timeout 3600 nice -n 5 xvfb-run -a -s "-screen 0 1920x1080x24" node /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/record.mjs $s 2>&1 | grep --line-buffered -v -i willread
  echo "=== $s exit $? $(date -u +%T)"
done
echo ALLDONE
