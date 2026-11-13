#!/bin/sh
# tracking films batch: one Chromium per shot, resumable (skips finished shots), 3 passes; PREVIEW=1 -> stills only into prev/
T=/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/track
cd /home/user/Calc/sfo3d
pgrep -f "http.server 8771" >/dev/null || (setsid nohup python3 -m http.server 8771 --bind 127.0.0.1 --directory out/phone_artifact/pub > /dev/null 2>&1 < /dev/null &)
sleep 2
OUT=$T/shots; [ -n "$PREVIEW" ] && OUT=$T/prev; mkdir -p $OUT
IDS=${IDS:-$(python3 -c "import json;print(' '.join(s['id'] for s in json.load(open('$T/shots3.json'))))")}
for pass in 1 2 3; do for s in $IDS; do
  if [ -n "$PREVIEW" ]; then [ -s $OUT/prev_${s}_100.png ] && continue; else [ -s $OUT/shot_$s.mp4 ] && continue; fi
  echo "=== $s pass$pass $(date -u +%T)"
  OUT=$OUT SHOTS_JSON=$T/shots3.json REPLAYS=$T/replays XGL=1 timeout 3600 nice -n 5 xvfb-run -a -s "-screen 0 1920x1080x24" node $T/record3.mjs $s 2>&1 | grep --line-buffered -v -i willread
  pkill -f "chrome-linux64/chrome" 2>/dev/null; rm -f $OUT/shot_$s.part.mp4
done; done
echo ALLDONE $(date -u +%T)
