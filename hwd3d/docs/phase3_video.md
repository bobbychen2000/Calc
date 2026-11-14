# Phase 3 (OD3) — deterministic video pipeline

Status 2026-11-13. OD3 (docs/PLAN.md §6b) asks for two follow-cam videos of real recorded HWD movements: a **Cirrus SF50
Vision Jet take-off** (case S) and a **Pilatus PC-12 landing** (case P), on runway 28L, with the full-quality renderer
(OD1) and the detailed models. This page describes the pipeline that makes them and the test clips that prove it. The
full videos are not rendered yet (render time, section 7).

**D1.** The videos are type-only: no registration, callsign, operator or ICAO address anywhere (overlay, file names,
logs). The hero aircraft is chosen in the page **by rule** from a type-only replay pack (section 3); its key never leaves
the page closure. No committed file holds a case's date, time or identity: the two job files with the window times are
`out/od3/video_S.json` and `out/od3/video_P.json` (gitignored), and the timings below are video seconds and
event-relative offsets only. Models in the test clips: `js/aircraft/models/sf50.glb` sha256 **49242e41…** and
`js/aircraft/models/pc12.glb` sha256 **c46fe4fb…** (recorded per run in `out/video/<case>/render_log.json`).
**PC-12 test clips SUPERSEDED** (Phase 3a fix round 3 iteration 2): the current pc12.glb is **6e349329…** (cabin floor and layout, nose-gear housing, belly-fairing section, belly antennas changed; `docs/phase3_models.md` section 13); re-render case P on it before publishing.

Labels: **[obs]** measured here; **[inf]** a design choice.

## 1. Files

| File | What |
|---|---|
| `js/video/vclock.js` | Virtual clock (classic script, injected by `page.addInitScript`): `Date`, `performance.now`, `requestAnimationFrame`, timers, seeded `Math.random` (section 2). |
| `js/video/timeline.js` | Frame schedule from the job's segments (data time, speed); linear speed ramps; sub-steps ≤ 1/30 s. Pure module (Node + page). |
| `js/video/director.js` | In-page director: hero by rule, pre-roll, per-frame stepping (engine sub-steps, the app's own frame callback once per output frame), skip-render frames, camera and drawable seams, hero pose + provenance of the current sample, overlay update. |
| `js/video/camera.js` | Scripted cinematic camera: shot kinds, critically damped springs, rule-of-thirds aiming, constraints and the per-shot report. Pure module: planned in Node from the scout trace. |
| `js/video/overlay.js` | Caption overlay and end card (DOM over the canvas; captured with the frame). |
| `tools/video/lib.mjs` | Static server (127.0.0.1, ports 8700–8749), Chromium + SwiftShader, the app boot under the virtual clock. |
| `tools/video/render.mjs` | The driver: `scout`, `plan`, `render`, `encode`, `stills`, `determinism`. |
| `dev/video.html` | Interactive preview of a job (the app + virtual clock + planned camera + overlay, real-time on a laptop GPU; no capture). |
| `out/od3/video_{S,P}.json` | The jobs (gitignored: window times). |
| `out/video/packs/` | The type-only packs (`tools/live/build_replay.py --out out/video/packs`). |
| `out/video/<case>/` | `trace.json`, `cams.json`, `frames/`, test clips, stills, `render_log.json`, `determinism.json` (gitignored). |

```bash
node tools/video/render.mjs out/od3/video_S.json scout     # engine-only run of the whole timeline -> trace.json + events
node tools/video/render.mjs out/od3/video_S.json plan      # camera of every frame -> cams.json + per-shot report
node tools/video/render.mjs out/od3/video_S.json render [--frames=a-b | --test=taxi | --pick=f1,f2,... --dir=picks] [--force]
node tools/video/render.mjs out/od3/video_S.json encode [--frames=a-b | --test=taxi] [--name=clip]
node tools/video/render.mjs out/od3/video_S.json stills [--test=taxi | --name=clip]
node tools/video/render.mjs out/od3/video_S.json determinism --test=det3s [--lead=6]
# preview: python3 -m http.server 8710 --bind 127.0.0.1, then
#   http://127.0.0.1:8710/dev/video.html?job=out/od3/video_S.json&mode=replay&fixedres=1&pack=out/video/packs/pack_vS.json.gz
```
`render` is resumable (a frame already on disk is skipped; the state still advances through it) and splittable: several
processes can each take a `--frames=a-b` range into the same `frames/` directory (each has its own browser and port).

## 2. Method

**The app is not modified.** The driver opens `live.html?mode=replay&fixedres=1&pack=out/video/packs/pack_vS.json.gz` at
1920 × 1080, DPR 1 (`?fixedres=1` pins the render scale: no dynamic resolution, OD1 full quality). The app runs its replay
path: P1's in-page shim (`out/replay/replay_shim.js`) feeds the pack through the live code path (stream feed, engine,
physics, drawables).

**Virtual clock** (`js/video/vclock.js`, installed before any page script):
- `Date.now()` / `new Date()` → a virtual **wall** clock. The epoch is `t0 = (pack.from + lookahead_s) × 1000`, so the
  shim's offset (`Date.now()/1000 − (from + L)` at install) is 0: the engine's wall clock IS the recording clock (+ the
  60-s display lookahead). The tower state, the sun and the METAR follow the recording time (this also removes
  docs/phase2_app.md I3 for the videos).
- `performance.now()` → a separate virtual **frame** clock; `app.js tick()` takes its frame dt from it.
- `requestAnimationFrame` → a queue the driver runs once per output frame (`vclock.frame()`).
- `setTimeout` / `setInterval` with a delay > 0 → timers on the virtual wall timeline, fired in due order, each at its own
  due time (`vclock.advanceTo`): the shim's 200-ms tick, the 60-s METAR refresh, the 0.7-s loading fade, the 20-s imagery
  race at boot. Delay 0 goes to the real `setTimeout` (boot continuations, the shim's history hand-off); the driver lets
  real tasks run between steps (`vclock.settle`).
- `Math.random` → mulberry32 with a fixed seed (`placeholder.js` / `detailed.js` draw a per-drawable `seed`).

**Stepping** (`director.js`). Pre-roll: the engine alone (`traffic.update` + `physics.resolve`, the engine part of
`app.js frame()`) in 0.1-s steps from the epoch to the first frame (~16 min of data for case S: 9,871 steps in ~10 s).
Each output frame `f` of the timeline advances the wall clock by `speed / fps` (1/30 s real time, 8/30 s at 8×) in
`n = ceil(speed)` sub-steps of `h ≤ 1/30 s`; sub-steps 1 … n−1 run the engine alone (no drawing), the last one is the app's
own frame callback (rAF) with the frame clock advanced by `h`, so `frame()` runs `traffic.update(now, h)`,
`physics.resolve(h)`, `views.sync`, the camera, `scene.frame`, `R.render`, `R.present` exactly once. In time-lapse the
app's own per-frame clock (`simT`: strobes, prop / fan animation; the 30-s environment refresh) runs at video rate.
Frames that are not captured (the scout, the skip-ahead before a frame range) run the same callback with `R.render` /
`R.present` stubbed for that call (the camera is computed, nothing is drawn): only GPU work is skipped. The renderer has
no temporal state that reaches the image (no TAA; motion blur is off, `post.shutter = 0`; `R.prev` only feeds motion
vectors), and the test in section 4 confirms it.

**Seams** (all from outside the app, on instances; app changes wanted in section 8):
- *Camera*: `app.js frame()` calls `HWD.rig.update(dt)` then `HWD.rig.camera()` and hands the result to the renderer. The
  director replaces both on the rig instance (`update` → no-op, `camera` → the planned camera of this frame).
- *Detailed model*: `HWD.views.sync` is wrapped; the hero's GA placeholder is replaced by a `DetailedAircraft`
  (`js/aircraft/models.js createAircraft`, model preloaded before the first frame so the swap is synchronous and the same
  in every run); the wrapper also sets `groundRef` (contact shading), the rotor (PC-12 110 rad/s on the ground, 178 in the
  air = the pc12 pivot's 1,700 rpm; SF50 fan 100 / 120 rad/s [inf]) and flaps from `disp.flaps` and the phase (SF50
  15 / 39°, PC-12 15 / 40° take-off / landing [inf]). Other aircraft keep their placeholders.
- *UI*: `body.qa` (the app's own QA class) hides the HUD; `#loading` is hidden by the overlay CSS.

**Two passes.** `scout` runs the whole timeline without drawing and records the hero's pose per frame (position,
heading, pitch, roll, ground speed, height above `site.groundY`, gear, flaps, the app's phase and label, the provenance of
the sample, the other drawn aircraft within 800 m) and derives events (first motion, line-up, roll, lift-off,
touchdown, stop, park). `plan` (Node: `js/video/camera.js` with `buildSite(data/hwd_airport.js)`) computes every frame's
camera from that trace. `render` repeats the same run with the planned cameras and captures. The render run measures
the hero's distance from the scout's pose on every frame: **0.0000 m** in every run so far [obs] (the engine and the
stepping are deterministic). If an engine change lands between scout and render, this check shows it: scout and plan
again.

**Capture and encode.** `page.screenshot` (PNG, 1920 × 1080: the WebGL canvas and the DOM overlay as composited) →
`out/video/<case>/frames/%05d.png`; then `ffmpeg -framerate 30 -i frames/%05d.png -c:v libx264 -crf 16 -preset slow
-pix_fmt yuv420p -r 30 -movflags +faststart`; stills with `ffmpeg -ss`.

## 3. Hero selection and pose

**Rule** (`director.js selectHero`, on the pack the app itself replays): records of the job's type (`t` = `SF50` /
`PC12`) inside the job window, with at least one **ground** fix within 2.5 km of the ARP and the case's event — take-off:
an airborne fix after the first ground fix at HWD; landing: an airborne fix within 15 km before the last ground fix at
HWD. The track with the most ground fixes at HWD wins (ties: pack order). Result [obs]: case S 1 candidate (142 ground
fixes at HWD of 173), case P 1 candidate (60 of 110). The engine track is then `HWD.traffic.tracks.get(key)` inside the
closure.

**Provenance of the current sample** (`sampleSrc`, from the track's own fixes around the display time):
`obs` — between two fixes ≤ 8 s apart (`classifier.js HOLE_S`): "Recorded ADS-B position"; `inf` — inside a recorder
hole (> 8 s) or after the newest fix: "Interpolated between ADS-B fixes · recorder gap of N s"; `rec` — a ground ↔ air
transition inside a hole (the take-off roll and lift-off, or the touchdown, have no fix at all): "Reconstructed (no
ADS-B fix) · N s between the last ground and the first airborne fix". Scout counts [obs]: case S obs 628 / inf 1,916 /
rec 1,215 frames (rec: the end of the taxi, line-up, the whole roll and the first ~10 s of the climb, one 50-s hole);
case P obs 797 / inf 1,033 / rec 1,277 (short final, touchdown and the first part of the roll, one 47-s hole).

## 4. Determinism (proof)

`render.mjs determinism` renders the same frame range three times, each in a fresh browser: A and B identically, C
starting a few frames earlier (so frames before the range are drawn in C and skipped in A / B). Every PNG's sha256 must
match.

| Range | Frames | A = B | A = C | Run |
|---|---|---|---|---|
| case S taxi chase (8×), 0.2 s | 6 | 6 / 6 | 6 / 6 (C drew 3 earlier frames) | first check |
| case S taxi chase (8×), 3.0 s | 90 | **90 / 90** | **90 / 90** (C drew 6 earlier frames) | the proof asked for |

Sources of nondeterminism found and removed: `Math.random` drawable seeds (seeded PRNG); wall-clock timers and rAF
(virtual); the dynamic resolution (`?fixedres=1`); real time leaking into the engine (the virtual epoch; boot under a
frozen clock, so the history burst lands identically); async METAR fetches (the shim's `Response` resolves within the
real tasks `vclock.settle` lets through after every frame). Not removable from the page side, but not observed:
SwiftShader's multi-threaded rasterisation order (the A = B test is the check).

## 5. Scripted camera (`js/video/camera.js`)

Not the app's CameraRig. A shot is a kind plus parameters over a frame range; a new shot is a deliberate cut (spring state
restarts); inside a shot every moving quantity goes through a critically damped spring (`smoothDamp`: x'' = −ω²(x − x*)
− 2ωx', ω = 2 / smoothing time, integrated exactly per frame in video time): the chase heading, the chase offset, the aim,
the dolly position (with the camera car's top speed), the zoom. (A first version used Unity-style SmoothDamp, which zeroes
the velocity when it passes a moving target: the P dolly car stalled at the cut and the aircraft raced across the frame.)
A panning aim is fed forward by the hero's velocity × the smoothing time (the steady lag of such a spring), so a fixed
camera keeps the hero on its framing point: the lift-off / touchdown shots now hold it within 30 px of it (before: up to
430 px behind). A moving camera (chase, dolly) smooths its aim relative to itself.

Kinds: `establish` (fixed / slowly drifting wide camera placed by bearing, distance and height from the hero at the
shot's first or last frame),
`chase` (behind / above / beside in the smoothed heading frame), `dolly` (a camera car on a line parallel to a runway
centreline, lead room in the direction of motion), `fixed` (a point that pans and zooms 30–55° after the hero; at a
runway edge relative to an event from the trace), `tower` (the cab eye, `site.anchors.tower`), `hold` (end card).
Framing by the rule of thirds: each shot puts the hero's centre at a chosen NDC point (`frame: [sx, sy]`).

Constraints on every frame, after smoothing: camera ≥ `site.groundY` + 1.5 m; never inside a building footprint below its
roof (`site.buildingAt`, raised over it); never within the body radius + 3 m of any drawn aircraft (from the trace's
`near` list; pushed out); FOV 30–55° (vertical). A fixed runway-edge camera is moved along the runway until it is 18 m
from every VASI / PAPI unit (`js/world/fixtures_naip.js`, NAIP-measured) and the windsock / segmented circle (the first P
plan put the touchdown camera behind a 28L VASI box: a 1.6-m orange box filled the foreground; moved 20 m). The plan
report, per shot: lowest camera height, largest per-frame move (absolute and relative to the hero), closest aircraft,
closest fixture, the hero's largest |NDC| and off-screen frames, building occlusions of the line of sight, constraint
hits. Current plans [obs]: no off-screen frame, no occluded frame, no constraint had to act, closest aircraft ≥ 12.5 m
from the camera.

## 6. Shot lists (30 fps; video time from the first frame)

The job gives each segment's speed and each shot's start as a data time or as an event of the scout trace plus an offset
(`{"event": "liftoff", "dt": -3.5}`); the times below are the current plans (`out/video/<case>/cams.json`). A speed change
is a 1-s linear ramp (a slow-down ends at the boundary, a speed-up starts there); the overlay shows the segment's factor.

**Case S — SF50 take-off, 28L** (3,797 frames, 2:06.6; low sun from the east-south-east, so the dolly and the
edge camera stand south of the runway with the sun behind them):

| Shot | Video | Speed | What |
|---|---|---|---|
| (a) `a-establish` | 0:00–0:06 | 1× | wide shot of the FBO ramp: 72 m east-south-east of the parked SF50, 12 m up, slow drift; hero on the right third |
| (b) `b-taxi-chase` | 0:06–0:32 | 8× | chase 40 m behind, 16 m up, aim 14 m ahead along the hero's heading; position heading spring 1.0 s (video) |
| `hold-wide` | 0:32–0:39 | 24× | wide static view of the hold / run-up stop, 85 m south-south-east, 14 m up; cut before it moves again |
| `lineup-chase` | 0:39–0:53 | 4× → 1× | chase 34 m behind, 9 m up: to the runway end, line-up |
| (c) `c-roll-dolly` | 0:53–1:19 | 1× | camera car 60 m south of the 28L centreline, 2.2 m up, 12 m behind the hero, top speed 42 m/s: the whole (reconstructed) roll |
| (e) `e-liftoff-edge` | 1:19–1:28 | 1× | fixed runway-edge camera 42 m south, 70 m past the lift-off point, 1.8 m up; from lift-off − 3.5 s; pans, zooms 30–54° |
| (d) `d-climb-chase` | 1:28–2:01 | 1× → 2× | chase 55 m behind, 7 m above, 10 m right, through the left turn; from lift-off + 5 s |
| end card | 2:01–2:07 | — | credits (section 9) |

**Case P — PC-12 landing, 28L** (3,107 frames, 1:43.6; high sun from the south):

| Shot | Video | Speed | What |
|---|---|---|---|
| (d) `d-final-chase` | 0:00–0:33 | 2× → 1× | chase 60 m behind, 6 m up, 9 m left on final (from where the app labels it "Final 28L") |
| (e) `e-touchdown-edge` | 0:33–0:43 | 1× | fixed runway-edge camera 42 m south, ~90 m past the touchdown point (moved 20 m off a VASI bar), 1.8 m up; from touchdown − 7 s |
| (c) `c-roll-dolly` | 0:43–1:04 | 1× | camera car 60 m south of the centreline from touchdown + 3 s through the roll-out (it starts at the hero's speed) |
| (b) `b-taxi-chase` | 1:04–1:24 | 8× | chase 42 m behind, 16 m up: taxi-in to the T-hangar lane |
| (a) `a-ramp-establish` | 1:24–1:38 | 2× | wide shot from the open end of the T-hangar lane, 75 m east-north-east of where it stops (`anchor: 'end'`), 16 m up: it taxis in and parks |
| end card | 1:38–1:44 | — | credits |

Plan checks [obs, both cases, every frame]: hero never off-screen (largest |NDC| 0.48), no line of sight through a building,
no constraint had to act, closest aircraft 12.5 m from the camera, closest light unit 16 m (the S dolly passes the 28L VASI
boxes). On-screen motion of the hero, from the trace and the cameras (px per frame at 1920 × 1080): ≤ 1.3 in the
establishing shots, ≤ 15 in the 8× chases (tight taxi turns at 8×), ≤ 0.8 in the S dolly, ≤ 2.8 in the climb-out / final
chases, ≤ 11 in the fixed edge shots; the largest frame-to-frame change (12.3 px/frame²) is the P touchdown, where the
engine holds the body still for one frame (section 11).

## 7. Render time

One frame = the engine sub-steps + the app's frame (SwiftShader WebGL2, 1920 × 1080, MSAA 4, 4096 shadow maps, the
detailed hero model) + the overlay + `page.screenshot` (PNG) + the write. Measured on this machine (4 CPUs, no GPU) while
two other workflows were also rendering (load average 4–16 during the runs), seconds per frame [obs]:

| Run | Frames | min | median | max | load |
|---|---|---|---|---|---|
| determinism 0.2 s, runs A / B / C | 6 / 6 / 9 | 3.23 / 3.37 / 3.41 | 3.33 / 4.37 / 3.51 | 5.48 / 5.62 / 4.68 | ~1–3 |
| determinism 3 s, run A | 90 | 3.26 | 4.04 | 9.40 | 4–5 |
| determinism 3 s, run B | 90 | 3.21 | 6.52 | 12.73 | 9–16 |
| determinism 3 s, run C | 96 | 3.50 | 7.29 | 13.44 | 9–16 |
| test clip S, taxi chase 8× (first plan) | 105 | 3.33 | 6.14 | 12.71 | 8–12 |
| test clip P, final chase (first plan) | 90 | 4.61 | 7.71 | 11.40 | 8–12 |
| test clips S + P again (final plans), **two processes at once** | 105 / 90 | 5.35 / 5.90 | 8.15 / 9.76 | 12.12 / 16.53 | 8–12 |

On a quiet machine a frame takes **~3.3 s** (the minimum of every run; a probe of the green-ramp view without the model:
1.6 s to render + 0.57 s for `page.screenshot`); with the other workflows rendering, the median is 6–8 s. The end-card
frames need no 3-D frame (0.15–0.5 s). Two processes at once (the last row) finished 195 frames in ~860 s of wall time:
**~4.4 s per frame of throughput** under the same outside load, against 6–8 s for one process. Scout: case S 3,797
frames in 54 s; skip-ahead before a range ~85 frames/s.

**Estimate for the planned lists** (3-D frames: S 3,617, P 2,927; + 180 end-card frames each):

| | at 3.3 s/frame (quiet) | at 6.5 s/frame (as measured under load) |
|---|---|---|
| case S | 3.3 h | 6.5 h |
| case P | 2.7 h | 5.3 h |
| both, one process | 6.0 h | 11.8 h |
| both, two processes (throughput measured under load: 4.4 s/frame) | — | 8.0 h |

**Proposal.** 30 fps (the 1× dolly and the edge pans need it; 24 fps saves 20 % but judders at 6–11 px/frame), case S
2:07 and case P 1:44 as planned — both under 2.5 min. If the time is too long: trim the climb-out chase (33 s → 20 s) and
the final chase (33 s → 22 s), which brings S to ~1:54 and P to ~1:33 (−11 % / −10 % of the frames); render each case as
two `--frames` halves on a quiet machine.

## 8. App changes wanted (for the orchestrator; nothing here was applied)

1. **Phase 3b model wiring** (`js/live/aircraft.js`, `js/live/traffic.js`; the diff is in `docs/phase3_models.md` §3):
   until then the director swaps the hero's drawable from outside, and the engine still places it with the class-rule
   dims (`gaDims`), so the drawn main gear sits 0.448 m (PC-12) / 0.693 m (SF50) off the engine's gear origin along the
   axis (`modelDims` fixes it). The view should also drive `setFlaps` (degrees: `disp.flaps` is 0 / 1 today), `rotor`
   for fixed-wing types and `groundRef`.
2. **An engine-step hook** in `app.js`: `HWD.stepEngine(now, dt)` = the engine part of `frame()` (today `traffic.update`
   + `physics.resolve`). The director calls the two directly for its sub-steps and the pre-roll; a system added to
   `frame()` later would be missed silently.
3. **A no-draw frame**: `HWD.qa.frame({ render: false })` (today the director stubs `R.render` / `R.present` for the call).
4. **A camera override**: `HWD.setCamera(fn | null)` used by `frame()` instead of `rig.camera()` (today the rig instance's
   `camera` / `update` are replaced).
5. **Sample provenance on the track**: `tr.disp.mode` (the target's `o.mode`: `gg:herm`, `route`, `plan:takeoff:…`,
   `aa:geo`, `extrap`) and the gap around the display time. The director re-derives obs / inf / rec from `tr.fx` with a
   copy of `HOLE_S` (8 s).
6. **Classifier labels seen in the videos** (`js/live/classifier.js`): case P is labelled "Overflight (not HWD traffic)"
   on its base leg and the first part of final, until ~1.3 NM out (the video starts where the label turns "Final 28L");
   case S is labelled "Taxiing" about 30 s before it moves (heading changes at its parking spot).

## 9. Overlay and end card

Caption (top left): the type name ("Cirrus SF50 Vision Jet" / "Pilatus PC-12 NGX"), "Hayward Executive (KHWD) · runway
28L", the app's phase label (`phaseLabel`, "(provisional)" dropped) and the scene's local time from the data clock
(`America/Los_Angeles`). Top right: the time-lapse factor of the segment ("8×", "TIME-LAPSE") — hidden at 1×. Bottom
left: the provenance pill (green: recorded ADS-B position; amber: interpolated between fixes, with the gap; orange:
reconstructed, no ADS-B fix). Bottom right: the METAR in force at the scene time (the pack's KHWD reports, remarks cut)
and a one-line credit. End card (last 6 s): what the video is, the D1 sentence, how the holes are filled, and the credits:
the six notices of `docs/ATTRIBUTION.md` "Notices to show in the app" word for word (imported from `js/live/about.js
NOTICES`, tags stripped: OpenStreetMap ODbL, ADSB.lol ODbL, the Hayward data set ODbL, USDA NAIP, FAA NASR / Chart
Supplement / AL-5015 / ACD / ACs / TAF, Mictronics ODC-By), plus the METAR source (NOAA / NWS Aviation Weather Center),
the NAIP ground imagery and the two own models. The end card names no date by default (job `endDate: true` adds it).
The overlay's classes carry a `vv-` prefix (the app's `.inf` / `.obs` tag styles had captured the first version's pill).

## 10. Test clips (what was rendered, and what the stills show)

Both clips at 1920 × 1080, 30 fps, H.264 High, yuv420p, CRF 16, `-preset slow`, faststart [obs, ffprobe]. Three stills
each (10 %, 50 %, 90 % of the clip, `ffmpeg -ss`), all looked at.

| Clip | Frames | Size | Shot | Hero vs scout |
|---|---|---|---|---|
| `out/video/S/test_taxi.mp4` (first plan, first overlay) | 105 (3.5 s), frames 427–531 | 2.07 MB | taxi chase, 8× | 0.0000 m |
| `out/video/P/test_final.mp4` (first plan, first overlay) | 90 (3.0 s), frames 368–457 | 2.71 MB | final chase, 1× | **3.96 m** (engine changed after the scout) |
| `out/video/S/test2_taxi.mp4` (final plan + overlay) | 105 (3.5 s), frames 427–531 | 2.05 MB | taxi chase, 8× | 0.0000 m |
| `out/video/P/test2_final.mp4` (final plan + overlay) | 90 (3.0 s), frames 368–457 | 2.64 MB | final chase, 1× | 0.0000 m (re-scouted) |

What the stills show, honestly:
- **S taxi chase (8×)**: the detailed SF50 (V-tail, the fan nacelle, gear down) on the taxiway centreline, low sun with
  long shadows, the 8× badge, the provenance pill switching between "Interpolated between ADS-B fixes · recorder
  gap of 48 s" and "Recorded ADS-B position" (green) as the 14-s observed windows pass, the scene's local clock and the
  METAR in force (the next hourly report appears only once the scene reaches its observation time: correct). Problems: a hangar's dark shaded wall fills the
  left third (the taxi lane runs along it); the parked business jet beside the lane is a GA placeholder (Phase 3); the
  whole scene is dark-ish in the low sun (exposure is the app's).
- **P final chase (1×)**: the PC-12 (blue cheat line, gear down, beacon / strobe lit) on a ~1.3 NM final to 28L, the
  runway, VASI and the field ahead under a clear sky, "Final 28L", "Reconstructed (no ADS-B fix) · 47 s between the
  last airborne and the first ground fix" (the clip lies in the hole that holds the touchdown). The hero sits ~120 px right
  of centre (the camera is 9 m left), steady over the clip. Problem: from this angle the propeller disc and the flaps are
  not readable.
- **Overlay fixes made after looking at the first clips**: the app's `.inf` / `.obs` tag styles had captured the pill
  (dark monospace text) — classes now prefixed `vv-`; Inter's tabular figures widened the hyphens ("ADS - B", "PC - 12") —
  `tnum` now only on the clock; a hard-edged top scrim — now a full-width gradient.
- Spot frames of every shot of both plans (`render --pick=…`, looked at before the clips): the establishing shots, the
  24× hold, the dolly with lead room, the lift-off / touchdown edge cameras, the climb-out chase and the end card (credits
  legible at 1080p, no date) all frame the hero as planned. Fixed after looking: the first P touchdown camera stood behind
  a 28L VASI box (now the 18-m fixture clearance); the first P ramp shot looked over T-hangar roofs at a half-hidden hero,
  and the second, placed from where the hero was when the shot began, ended with the PC-12 filling the frame 25 m away
  (now placed from where it stops, `anchor: 'end'`: 132 m → 79 m as it taxis in; not re-rendered). Seen and left for the
  owner: the S lift-off edge camera looks east into the low sun, so the SF50 lifts off as a silhouette against the glare
  (`dalong` < 0 puts the camera short of the lift-off point with the sun behind it, the aircraft then seen going away).

## 11. Open items / not verified

- **The full videos are not rendered** (6–12 h of machine time, section 7). Before they are: re-run `scout` and `plan` on
  the then-current engine (the Phase 2 fix round is changing `js/live/traffic.js` under this work: the first P test clip's
  render found the hero up to **3.96 m** away from its scout pose because the engine changed between the two runs; after a
  new scout the deviation is 0 again; the last S spot frames found 0.24 m after another engine edit), then render.
  `render` refuses a `frames/` directory whose `PLAN_STAMP` (sha256 of `cams.json`) belongs to another plan.
- **Engine motion seen in the traces** (P3 / Phase 2 owners; not fixed here): (1) case P, the body stands still for one
  frame (1/30 s at 80 kt) at touchdown — a visible hitch (`out/video/P/trace.json`, the touchdown frame); (2) case P lands
  flat: pitch ≤ 0.3° in the flare; (3) case S lifts off flat: pitch 0 for the whole roll, 0.8° a third of a second after
  lift-off (no rotation); (4) case S, on the runway, at the start of the roll the SF50 yaws ~5° left on the spot and back
  over ~2 s; (5) the roll, lift-off, touchdown and roll-out of both cases lie in one recorder hole each (50 s / 47 s): all
  of it is reconstructed (the overlay says so) — the Phase 2 fixer's take-off / landing reconstruction will change them.
- The Phase 2 fixer's per-second traces (`out/od3/case_*_trace.json`) are not used: the pipeline takes the motion from
  the app's own engine run (scout = render, bit for bit); those traces can serve as an independent check of the scout.
- Classifier labels (section 8, item 6): "Overflight (not HWD traffic)" on the PC-12's base; "Taxiing" ~30 s before the
  SF50 moves.
- The hero is drawn with the detailed model but positioned with the class-rule dims (section 8, item 1); every other
  aircraft is a GA placeholder (a blocky bizjet stands next to the detailed SF50 in the taxi shots).
- **D1 / re-identification (owner decision).** The overlay shows the scene's local time and the METAR, whose day-time
  group carries the day of the month; with the type and the airport, that may be enough to find the flight in public
  ADS-B history. The task asks for both; the end card leaves the date out by default. Options: show the time of day only
  (drop the METAR day-time group), or accept.
- Composition: in the 8× taxi chase of case S a hangar wall fills the left third for a few seconds (the taxi lane runs
  along it); a side offset or a higher camera would clear it. The 24× hold shot and the 2× climb-out are long for what
  happens in them (section 7 proposes trims).
- Not verified: `dev/video.html` on a real GPU (only loaded headless here); the render time with two processes on a
  quiet machine; SwiftShader only (a GPU machine should be several times faster — the pipeline is the same).
- The models changed during this work (Phase 3a fix round 3): every test clip used `sf50.glb` 49242e41… and
  `pc12.glb` c46fe4fb… (each run's hashes are in `out/video/<case>/render_log.json`); a later model build only needs a new
  render (the camera plan does not depend on the model).
