# Trailer pipeline (9 Nov 2026)
Scripts as used for the 45-s trailer (paths point at the session scratchpad; adjust SP).
- record.mjs: one shot on the Full build (out/phone_artifact/pub served on :8771), Playwright virtual clock + manual rAF, Xvfb + Mesa llvmpipe (XGL=1), ?quality=ultra, canvas capture into ffmpeg.
- run_all.sh / chain.sh: batch + re-render + assembly. assemble.py: xfades, title/credit/end cards, VO placement, ducked pad, loudnorm.
- say.py + lines.json: narration with Kokoro-82M (Apache-2.0) via kokoro-onnx (MIT).
Known: Chromium GPU process grows ~25-40 MB per 1080p frame under llvmpipe, so shots are capped at <=168 frames.
