#!/bin/sh
# after the running batch: re-render arrival + takeoff with chase cameras, then assemble the trailer
while pgrep -f "trailer/run_all.sh" >/dev/null; do sleep 20; done
rm -f /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/shot_takeoff.mp4 /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/shot_arrival.mp4
SHOTS="arrival takeoff" /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.sh >> /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.log 2>&1
# one retry pass for anything missing (e.g. no event, context loss)
SHOTS="arrival takeoff aerial gates tower night" /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.sh >> /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.log 2>&1
ls /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/shot_*.mp4 >> /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.log
python3 /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/assemble.py /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer >> /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.log 2>&1 && echo TRAILER_READY >> /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.log || echo TRAILER_FAILED >> /tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad/trailer/run_all.log
