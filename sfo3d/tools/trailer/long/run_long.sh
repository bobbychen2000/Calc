#!/bin/sh
# long-video batch: one Chromium per shot, resumable (skips finished shots); OUT=${OUT:-/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/long/shots}
cd /home/user/Calc/sfo3d
OUT=${OUT:-/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/long/shots}; mkdir -p $OUT
pgrep -f "http.server 8771" >/dev/null || (setsid nohup python3 -m http.server 8771 --bind 127.0.0.1 --directory out/phone_artifact/pub > /dev/null 2>&1 < /dev/null &)
sleep 2
IDS=${IDS:-$(python3 -c "import json;print(' '.join(s['id'] for s in json.load(open('/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/long/shots.json'))))")}
for pass in 1 2 3; do for s in $IDS; do
  [ -s $OUT/shot_$s.mp4 ] && continue
  echo "=== $s pass$pass $(date -u +%T)"
  OUT=$OUT SHOTS_JSON=/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/long/shots.json REPLAYS=/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/long/replays XGL=1 Q=${Q:-ultra} timeout 3000 nice -n 5 xvfb-run -a -s "-screen 0 1920x1080x24" node /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/long/record2.mjs $s 2>&1 | grep --line-buffered -v -i willread
  pkill -f "chrome-linux64/chrome" 2>/dev/null; rm -f $OUT/shot_$s.part.mp4
done; done
echo ALLDONE $(ls $OUT/shot_*.mp4 2>/dev/null | wc -l)
