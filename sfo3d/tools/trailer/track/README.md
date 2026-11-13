# Tracking films (arrival + departure), 1080p

Two films that follow one aircraft each through the Full build's replay of the 8 Nov 2026 20:46-21:26Z recording
(out/phone_artifact/pub/data/replay.wasm), rendered on the high tier (prepass AO, TRAA, bloom, SSR, 2048 shadows):

- arrival: UAL900 B789 N71112 (LHR-SFO): bay approach, final over the 28R approach lights, touchdown, rollout, taxi
  (time-lapse), pull-in and jet-bridge docking at G7 (2:29)
- departure: UAL857 B77W N2639U (SFO-PVG): G13, pushback, taxi to 28R (time-lapse), line-up, take-off roll, rotation,
  climb-out (2:44)

Pipeline (paths in the scripts point at the session scratchpad; adjust T=):
1. `make_shots3.py shots3.json`: shot list from the ADS-B track (recording time `start` s after the pack's first event,
   `speed` = recorded s per video s, labelled on screen; camera chase / orbit / spot with zoom `frame` in metres).
   Lighting: `?t=` per shot from a late-afternoon base (the traffic is the real 12:46-13:26 PST recording; the end card
   says so).
2. `long/make_replays.py` trims the replay pack at each shot's `off` (= start - 200 s: the page loads in 70-140 s while
   the replay runs).
3. `run_track.sh` (resumable, 3 passes; `PREVIEW=1` renders 5 stills per shot at 960x540) runs `record3.mjs` per shot
   under Xvfb + llvmpipe; `watch.sh` wakes the session per shot.
4. `cards_track.mjs` (labels, badges, titles, end card) and `assemble_track.py <dir> arr|dep out.mp4`.

Known: the ultra tier OOMs the software-GL GPU process near the terminals (memcg 14.3 GB), so all shots use high; shots
that lose the context after >= 96 frames are kept short (a_taxi, a_taxi2, a_pull2, a_dock2, d_push2, d_taxi2, d_taxi3,
d_roll). The painted registration on the 787 model's livery (N61115) is not the aircraft's (N71112); the caption is.
