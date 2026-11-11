# Long (≈6 min) video pipeline

Records the Full build (out/phone_artifact/pub served on :8771) shot by shot under Xvfb + Mesa llvmpipe, then assembles
chapters, narration (Kokoro-82M via kokoro-onnx), chapter cards and a synthesized music bed. Scripts were run from a
session scratchpad; paths inside them are absolute to that scratchpad and need adjusting to rerun.

- `make_replays.py` trims the embedded replay pack to start `off` s later. The pack is delta-encoded (identity fields
  such as flight / ICAO type are sent once per aircraft), so the first kept event is rewritten with each aircraft's
  full accumulated state; without that, aircraft present at the cut have no type and render as a light only.
- `make_shots.py` -> `shots.json` (54 shots, 8 chapters). Chase shots (`kind: chase`) use the 'high' tier: the
  real-time event wait at 'ultra' fills Chromium's software-GL GPU process past the session memory cap.
- `record2.mjs <id>`: virtual clock + manual rAF, canvas capture to ffmpeg. Liveries at the high tier's 'auto'
  resolution (window.SFO_LIVERY_RES). A shot whose GPU process is OOM-killed after >= 72 frames is kept shortened.
- `run_long.sh`: resumable batch, 3 passes; `watch.sh`: one status line per finished shot.
- `assemble_long.py <dir> <out.mp4>`: xfades, title / chapter / credit / end cards, narration, ducked music, loudnorm.
