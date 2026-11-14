# Phase 3 (OD3) — deterministic video pipeline

Status 2026-11-14, after **review fix round 1** of the video pipeline (findings F1–F13; section 12 maps each finding to
its fix). OD3 (docs/PLAN.md §6b) asks for two follow-cam videos of real recorded HWD movements: a **Cirrus SF50 Vision
Jet take-off** (case S) and a **Pilatus PC-12 landing** (case P), on runway 28L, with the full-quality renderer (OD1) and
the detailed models. This page describes the pipeline that makes them and the test clips that prove it. The full videos
are not rendered yet (render time, section 7).

**D1.** The videos are type-only: no registration, callsign, operator or ICAO address anywhere (overlay, file names,
logs). The hero aircraft is chosen in the page **by rule** from a type-only replay pack (section 3); its key never leaves
the page closure. No committed file holds a case's date, time or identity: the job files with the window times are
`out/od3/video_S.json` and `out/od3/video_P.json` (gitignored), the timings below are video seconds and event-relative
offsets only, and the PRNG seed of the virtual clock is a neutral constant (`0x5eed`, not a date). **The frames
themselves do show the date and the time** (section 9): the caption clock gives the local time of day to the second, the
METAR line carries its day-time group (day of the month + time) and the end card names the month and year. With the type
and the airport, that may be enough to find the flight in public ADS-B history. Both heroes are masked in the pack as the
pack default (`type-only`), not because of a LADD / PIA flag. Whether a published video shows the date is an **owner
decision**; the job option `timeOnly: true` leaves the time of day only (no METAR day-time group, no month).

Labels: **[obs]** measured here; **[inf]** a design choice.

## 1. Files

| File | What |
|---|---|
| `js/video/vclock.js` | Virtual clock (classic script, injected by `page.addInitScript`): `Date`, `performance.now`, `requestAnimationFrame`, timers, seeded `Math.random` (section 2). |
| `js/video/timeline.js` | Frame schedule from the job's segments (data time, speed); linear speed ramps; sub-steps ≤ 1/30 s; skip segments (cuts in data time). Pure module (Node + page). |
| `js/video/director.js` | In-page director: hero by rule, pre-roll, per-frame stepping, the seams (camera, drawable, engine dt, no-draw frames, motion blur), hero pose + provenance of the current sample, overlay update. |
| `js/video/camera.js` | Scripted cinematic camera: shot kinds, critically damped springs with feed-forward, rule-of-thirds aiming, constraints and the per-shot report (on-screen motion included). Pure module: planned in Node from the scout trace. |
| `js/video/provenance.js` | Provenance class of each sample (obs / inf / rec / nos) and the per-frame caption track (pill + phase line, held ≥ 0.5 s). Pure module. |
| `js/video/overlay.js` | Caption overlay and end card (DOM over the canvas; captured with the frame). |
| `tools/video/lib.mjs` | The frozen app snapshot (copy, manifest, verify, pipeline-only refresh), the static server for it (127.0.0.1, ports 8700–8749, hashes and checks every byte served), Chromium + SwiftShader, the app boot under the virtual clock. |
| `tools/video/render.mjs` | The driver: `snapshot`, `scout`, `plan`, `render`, `encode`, `stills`, `determinism`. |
| `dev/video.html` | Interactive preview of a job (the WORKING TREE's app + virtual clock + planned camera + overlay, real time on a laptop GPU; no capture). |
| `out/od3/video_{S,P}.json` | The jobs (gitignored: window times). |
| `out/video/packs/` | The type-only packs (`tools/live/build_replay.py --out out/video/packs`). |
| `out/video/<case>/app/` | The frozen app snapshot of the case + `MANIFEST.json` (gitignored). |
| `out/video/<case>/` | `trace.json`, `cams.json`, `frames/` (+ `PLAN_STAMP`), clips, stills, `render_log.json`, `determinism.json` (gitignored). |

```bash
node tools/video/render.mjs out/od3/video_S.json snapshot [--refresh | --refresh=video]   # freeze the app (section 2.1)
node tools/video/render.mjs out/od3/video_S.json scout     # engine-only run of the whole timeline -> trace.json + events
node tools/video/render.mjs out/od3/video_S.json plan      # camera + caption of every frame -> cams.json + report + gates
node tools/video/render.mjs out/od3/video_S.json render [--frames=a-b | --test=taxi | --pick=f1,f2,... --dir=picks] [--force] [--clean]
node tools/video/render.mjs out/od3/video_S.json encode [--frames=a-b | --test=taxi] [--name=clip] [--dir=frames]
node tools/video/render.mjs out/od3/video_S.json stills [--test=taxi | --name=clip]
node tools/video/render.mjs out/od3/video_S.json determinism --test=blur [--lead=6]
# preview: python3 -m http.server 8710 --bind 127.0.0.1, then
#   http://127.0.0.1:8710/dev/video.html?job=out/od3/video_S.json&mode=replay&fixedres=1&pack=out/video/packs/pack_vS.json.gz
```
`render` is resumable (a complete frame already on disk is skipped, a missing or damaged one is drawn; the state still
advances through every frame) and splittable: several processes can each take a `--frames=a-b` range into the same
`frames/` directory (each has its own browser and port). Every stage refuses to work on outputs of another snapshot, job
or plan (section 2.1).

## 2. Method

### 2.1 The frozen app snapshot and the stamp chain (finding F1)

Two fix rounds edit the engine (`js/live/traffic.js`) and the models (`js/aircraft/models/*.glb`) while this pipeline
runs; a 6–12-h render that is split or resumed must never mix versions. So **nothing is rendered from the working tree**:

- `snapshot` boots the working tree's app once (a probe: the director, three drawn frames, the overlay), then copies
  `live.html`, `live.css`, `js/**` (the engine, renderer, shaders, the models and `js/video/**` itself), `data/**`, the
  replay shim and the job's pack, plus anything else the probe requested (none so far), byte for byte into
  `out/video/<case>/app/`, and writes `MANIFEST.json`: sha256 of every file, `tree` = sha256 of the sorted
  "path sha" lines, the git head and the number of modified paths. 89 files per case [obs].
- Every later stage re-hashes the snapshot against its manifest first (a changed, missing or added file stops it), serves
  ONLY the snapshot (the server hashes every response: a byte that differs from the manifest, a 404 or a request outside
  the snapshot ends the run), imports the Node-side modules (`timeline`, `camera`, `provenance`, `site`, the airport,
  the fixtures) from it, and reads `vclock.js` from it. The models are hashed when they are served to the page (the bytes
  the page loads), and each render log records those hashes.
- **Stamps, chained:** `trace.json` carries `scoutKey = sha256(snapshot tree + the job's scout fields + seed)`;
  `cams.json` carries `planKey = sha256(scoutKey + sha256(trace.json) + the job's plan fields)`; a frames directory's
  `PLAN_STAMP = sha256(planKey + frame size + shutter + overlay options)`. Every stage recomputes the key it builds on and
  refuses a mismatch: a new snapshot needs a new scout and plan, and `render` / `encode` refuse a frames directory of
  another stamp (`--clean` empties it). Seen working [obs]: after the snapshot was refreshed, `render` refused the old
  P frames ("holds frames of another plan, snapshot or render setting").
- **Hero vs scout, enforced:** every frame of a render (the skip-ahead included) compares the hero's position, phase and
  label with the scout trace; more than `maxDevM` (default **0.01 m**) or a different phase / label aborts the run.
  Every run in this round: **0.00000 m**.
- `snapshot --refresh=video` replaces only `js/video/**` (a fix of the pipeline itself) and keeps the frozen engine,
  renderer, data and models; the manifest records the base tree. Used in this round: the fix rounds had changed
  `traffic.js` and `pc12.glb` since the snapshot was taken, half-way through their own work, so the pipeline fix went
  into the existing snapshot instead of freezing an engine in mid-edit.

Current snapshots [obs]: case S tree `e26c545e9385…` (base `0df6b37af582…`), case P tree `90e710a5a07f…` (base
`baa39ffc2f37…`); both from git `b0d55c1` + 1 modified path; models `sf50.glb` sha256 **49242e41…** and `pc12.glb`
**6e349329…**. Before the full render, take a new snapshot of the then-current app (`snapshot --refresh`), scout and plan
again (section 11).

### 2.2 The app and the virtual clock

**The app is not modified.** The driver opens `live.html?mode=replay&fixedres=1&pack=out/video/packs/pack_vS.json.gz` at
1920 × 1080, DPR 1 (`?fixedres=1` pins the render scale: no dynamic resolution, OD1 full quality), from the snapshot. The
app runs its replay path: P1's in-page shim (`out/replay/replay_shim.js`) feeds the pack through the live code path
(stream feed, engine, physics, drawables).

**Virtual clock** (`js/video/vclock.js`, installed before any page script):
- `Date.now()` / `new Date()` → a virtual **wall** clock. The epoch is `t0 = (pack.from + lookahead_s) × 1000`, so the
  shim's offset is 0: the engine's wall clock IS the recording clock (+ the 60-s display lookahead). The tower state, the
  sun and the METAR follow the recording time.
- `performance.now()` → a separate virtual **frame** clock; `app.js tick()` takes its frame dt from it.
- `requestAnimationFrame` → a queue the driver runs once per output frame (`vclock.frame()`).
- `setTimeout` / `setInterval` with a delay > 0 → timers on the virtual wall timeline, fired in due order, each at its own
  due time; delay 0 goes to the real `setTimeout` (boot continuations); the driver lets real tasks run between steps.
- `Math.random` → mulberry32 with a fixed, neutral seed (`0x5eed`).

### 2.3 Stepping and the animation clock (finding F10)

Pre-roll: the engine alone (`traffic.update` + `physics.resolve`) in 0.1-s steps from the epoch to the first frame (case S
9,871 steps). Each output frame `f` advances the wall clock by `speed / fps` in `n = ceil(speed)` sub-steps of
`h ≤ 1/30 s`; sub-steps 1 … n−1 run the engine alone, the last one is the app's own frame callback (rAF). The director
advances `performance.now()` by **one video frame (1/30 s)** for that callback and, during it only, hands the engine its
own sub-step `h` (`traffic.update` / `physics.resolve` wrapped on the instances). So the app's per-frame clock (`simT`:
propeller and fan angle, strobe and beacon phase; flap and gear lag; the 30-s environment refresh) runs at video rate in
every frame, and the engine steps exactly as before. Before this round the frame dt was `h`, so inside the 1×–2× speed
ramps (`h = speed / 60`) propellers and anti-collision lights ran at down to 52 % of their video-time rate. Probe [obs,
case P, frames 270–320, the 2× → 1× ramp, h down to 0.633/30]: the engine received `h` in every sub-step, `views.sync`
and the frame clock 1/30 s in all 51 frames, no mismatch.

Frames that are not captured (the scout, the skip-ahead before a frame range, the opaque end card) run the same callback
with `R.render` / `R.present` stubbed; the stub computes the camera and sets the renderer's previous camera (`R.prev`)
exactly as `R.render` does, so the motion-blur reference of the first drawn frame of a range, a resume or a pick is the
true previous frame. Everything else (engine, drawables, their motion-vector bookkeeping in `scene.frame` /
`scene.commit`) advances as in a drawn frame.

### 2.4 Seams (all from outside the app, on instances; app changes wanted in section 8)

- *Camera*: `HWD.rig.update` → no-op, `HWD.rig.camera` → the planned camera of this frame.
- *Detailed model*: `HWD.views.sync` is wrapped; the hero's GA placeholder is replaced by a `DetailedAircraft`
  (`js/aircraft/models.js createAircraft`, model preloaded before the first frame), with `groundRef`, the rotor (PC-12
  110 rad/s on the ground, 178 in the air = the pc12 pivot's 1,700 rpm; SF50 fan 100 / 120 rad/s [inf]) and flaps
  (SF50 15 / 39°, PC-12 15 / 40° take-off / landing [inf]).
- *Engine dt*: `traffic.update` / `physics.resolve` wrapped (section 2.3).
- *Motion blur* (finding F4): captured frames get `post.shutter = 0.5` (a 180° shutter: the app's own blur pass,
  `js/renderer.js`, clamped at 3 % of the width) by wrapping `R.render`'s `post` argument for that call; the app's own
  loop keeps 0. At a cut `R.prev` is cleared, so the first frame of a shot carries no camera motion from the last one.
- *UI*: `body.qa` hides the HUD; `#loading` is hidden by the overlay CSS.

### 2.5 Two passes

`scout` runs the whole timeline without drawing and records the hero's pose per frame (position, heading, pitch, roll,
ground speed, height above `site.groundY`, gear, flaps, the app's phase and label, the provenance of the sample, the
other drawn aircraft within 800 m) and derives events (first motion, line-up, roll, lift-off, touchdown, stop, park).
`plan` (Node, the snapshot's `js/video/camera.js` and `provenance.js` with `buildSite(data/hwd_airport.js)`) computes
every frame's camera and caption from that trace and applies the plan gates (section 5). `render` repeats the same run
with the planned cameras and captions and captures; the hero-vs-scout check (section 2.1) aborts it on any difference.

### 2.6 Capture and encode (finding F2)

`page.screenshot` (PNG, 1920 × 1080: the WebGL canvas and the DOM overlay as composited) → written to `%05d.png.part`,
then renamed (a crash never leaves a half-written frame under its name). `encode` checks, before ffmpeg runs, that the
frames directory's `PLAN_STAMP` is this plan's and that **every** frame of the range is on disk and a complete PNG (the
signature, every chunk's CRC, `IEND` last); then `ffmpeg -framerate 30 -start_number a -i frames/%05d.png -frames:v N
-c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -r 30 -movflags +faststart`, where any message at `-loglevel error`
fails the step; then `ffprobe -count_frames` must report exactly N frames (else the clip is renamed `.short`). A failed
encode leaves nothing under the clip's name (`.failed`). Why all three [obs, this round, on a copy of the P test frames]:
a **missing** frame makes the image2 demuxer stop at the gap and exit 0 (the review's finding; now refused before ffmpeg
runs: "1 of 90 frames missing"); a **truncated** frame (a crash mid-write) made ffmpeg 6.1 log a decode error, repeat the
previous frame and exit 0 with the full 90-frame count, so neither the exit code nor the count catches it (now refused by
the PNG check: "1 of 90 frames damaged", and `render` re-draws it on resume); a **CRC-valid but undecodable** frame
passes the PNG check, and ffmpeg again exits 0, but its error output now fails the step ("ffmpeg failed (exit 0, 2 error
line(s))"). The PNG check of 90 frames takes 0.2–0.3 s. And `render` re-draws a damaged frame on resume: frame 400 of the P test range, cut to 30 kB, was found, re-drawn alone (skip-ahead through 368–399) and
came out bit-identical to the original (sha256 `af185a23…`). Stills: `ffmpeg -ss` at 10 / 50 / 90 % of a clip.

## 3. Hero selection and provenance

**Rule** (`director.js selectHero`, on the pack the app itself replays): records of the job's type (`t` = `SF50` /
`PC12`) inside the job window, with at least one **ground** fix within 2.5 km of the ARP and the case's event — take-off:
an airborne fix after the first ground fix at HWD; landing: an airborne fix within 15 km before the last ground fix at
HWD. The track with the most ground fixes at HWD wins. Result [obs]: case S 1 candidate (142 ground fixes at HWD of
173), case P 1 candidate (60 of 110).

**Provenance of the current sample** (`provenance.js sampleSrc`, page side, from the track's own fixes around the display
time; refined over the whole trace by `captionTrack`, plan side) — finding F6:

| Class | When | Pill |
|---|---|---|
| `obs` (green) | between two fixes ≤ 8 s apart (`classifier.js HOLE_S`) | "Recorded ADS-B position" |
| `inf` (amber) | a recorder hole (8–90 s) with no start, stop, take-off or landing in it, or after the newest fix | "Interpolated between ADS-B fixes · recorder gap of N s" |
| `rec` (orange) | a ground ↔ air transition in a hole (the roll and lift-off / the touchdown have no fix at all) | "Reconstructed (no ADS-B fix) · N s between the last ground and the first airborne fix" |
| `rec` | a hole whose fixes say standing → moving or moving → standing: when it starts / stops is the engine's guess | "… · no fix for N s: when it starts to move is inferred" / "… when it stops is inferred" |
| `rec` | a hole whose two fixes both say moving (or both standing) but in which the DRAWN aircraft stands ≥ 2 s and moves: the stop is the engine's choice (new in this round, see below) | "… · no fix for N s: the stop is inferred" / "… the movement is inferred" |
| `nos` (grey) | a gap longer than 90 s with none of the above: the transponder itself was silent, not the recorder's duty cycle | "No ADS-B signal for N s · position inferred" |

The parked-to-taxi start of case S lies in a **274-s** gap with no fix at all; it now reads "Reconstructed (no ADS-B
fix) · no fix for 274 s: when it starts to move is inferred" (before: "Interpolated · recorder gap of 274 s"). Looking at
the S taxi test range showed one more case: the engine stops the SF50 for ~16 s of data in the middle of a 48-s hole whose
two end fixes are both moving (nearest other aircraft 81 m: not a separation stop), and once more for 2 s in the next
hole; those two holes now read "the stop is inferred" (rule above). The caption state is held for at least 0.5 s of video
(15 frames): a shorter state keeps the state before it on screen (at 24× a 14-s observed window passes in 6 frames; the
review saw the pill flip to green for 0.2 s twice); one forward pass over the trace, so it does not depend on where a
render starts. Phase line: the app's label ("(provisional)" dropped), except that a hero standing still on the ground
(< 0.5 kt for ≥ 2 s of data) that the app still calls "Taxiing" is shown as **"Stopped"** [inf: a video rule; the
classifier item is in section 8].

Caption runs in the plans [obs]: case S 24 runs, case P 18 runs, none shorter than 15 frames inside a shot; 30 (S) and
8 (P) frames show a held state. Scout counts of the page-side classes [obs]: case S obs 591 / inf 1,247 / rec 1,882
frames, case P obs 797 / inf 743 / rec 1,567.

## 4. Determinism (proof)

`render.mjs determinism` renders the same frame range three times, each in a fresh browser from the snapshot: A and B
identically, C starting a few frames earlier (so frames before the range are drawn in C and skipped in A / B). Every
PNG's sha256 must match. With motion blur on (shutter 0.5), A = C also proves the no-draw stub keeps the blur reference
right.

| Range | Frames | Shutter | A = B | A = C | Run |
|---|---|---|---|---|---|
| case S taxi chase (8×), 0.2 s | 6 | 0 | 6 / 6 | 6 / 6 (C drew 3 earlier frames) | first check (earlier round) |
| case S taxi chase (8×), 3.0 s | 90 | 0 | 90 / 90 | 90 / 90 (C drew 6 earlier frames) | earlier round |
| case S taxi chase (8×), the fastest whip pan (34 px/frame), 1.0 s | 30 | **0.5** | **30 / 30** | **30 / 30** (C drew 6 earlier frames) | this round, snapshot `0df6b37…` |
| the same, after the pipeline refresh | 30 | **0.5** | **30 / 30** | **30 / 30** (C drew 6 earlier frames) | this round, snapshot `e26c545…` |

Sources of nondeterminism found and removed: `Math.random` drawable seeds (seeded PRNG); wall-clock timers and rAF
(virtual); the dynamic resolution (`?fixedres=1`); real time leaking into the engine (the virtual epoch; boot under a
frozen clock); async METAR fetches (the shim's `Response` resolves within the real tasks `vclock.settle` lets through);
a stale blur reference after skipped frames (the stub sets `R.prev`); the working tree changing under a render (the
snapshot). Not removable from the page side, but not observed: SwiftShader's multi-threaded rasterisation order (the
A = B test is the check).

## 5. Scripted camera (`js/video/camera.js`)

Not the app's CameraRig. A shot is a kind plus parameters over a frame range; a new shot is a deliberate cut (spring state
restarts); inside a shot every moving quantity goes through a critically damped spring (x'' = −ω²(x − x*) − 2ωx',
ω = 2 / smoothing time, integrated exactly per frame in video time).

**Feed-forward.** A critically damped spring follows a moving target with X/T = ω² / (s + ω)²: behind a target moving at v
it settles v × smoothing time behind, and behind an accelerating one further still. So:
- a panning aim (establish, fixed, tower) is fed forward by the hero's velocity × the smoothing time;
- a chase aim is fed forward by its own target's rate (`aimFF`);
- the **dolly camera car** (finding F3) runs on target = s_H + lag + smooth × v + smooth²/4 × a (s_H, v, a: the hero's
  along-track position, velocity and acceleration from the trace, central differences over ±3 frames), which makes the
  car follow s_H + lag exactly, top speed permitting. Before, the target had no feed-forward and the car settled
  v × smooth behind its planned lag: in case S the car meant to run 12 m behind was 63 m behind at lift-off, and in case P
  the car meant to run 8 m behind fell to 48 m behind, swinging the PC-12 208 px across the frame in the 3.7 s after the
  cut. Now [obs, plans]: lag error ≤ **0.64 m** (S) and ≤ **1.25 m** (P, on the cut frame itself), the car never at its
  top speed, the hero's screen x on the thirds line (1,247–1,249 px) for the whole of both dolly shots.

Kinds: `establish` (fixed / slowly drifting wide camera placed by bearing, distance and height from the hero at the
shot's first frame, or its last: `anchor: 'end'`), `chase` (behind / above / beside in the smoothed heading frame),
`dolly` (a camera car on a line parallel to a runway centreline, lead room in the direction of motion), `fixed` (a point
that pans and zooms 30–55° after the hero; at a runway edge relative to an event from the trace), `tower` (the cab eye),
`hold` (end card). Framing by the rule of thirds: each shot puts the hero's centre at a chosen NDC point.

Constraints on every frame, after smoothing: camera ≥ `site.groundY` + 1.5 m; never inside a building footprint below its
roof; never within the body radius + 3 m of any drawn aircraft (pushed out); FOV 30–55° (vertical). A fixed runway-edge
camera is moved along the runway until it is 18 m from every VASI / PAPI unit (NAIP-measured) and the windsock /
segmented circle.

**Plan report and gates** (per shot; `plan` prints them, `cams.json` stores them, and `render` refuses a plan whose gates
failed unless `--nogate`): lowest camera height, largest per-frame move (absolute and relative to the hero), closest
aircraft and fixture, the hero's largest |NDC| and off-screen frames, building occlusions, constraint hits, and the
**on-screen motion**: the hero's screen speed (px/frame) and its change (px/frame²), the background's pan speed from the
camera's rotation alone (px/frame at the frame centre, and the number of frames above 20), the dolly's lag error, and the
hero's **rest jitter** (a hop or a yaw twitch while it stands, finding F5). Gates [inf: design limits], px at 1920 × 1080:

| Kind | hero px/frame | hero px/frame² | pan px/frame | other |
|---|---|---|---|---|
| establish | 4 | 3 | 5 | rest jitter 0 frames |
| chase | 6 | 1.5 | 40 (a 20-px streak at shutter 0.5) | |
| dolly | 4 | 1.5 | 5 | lag error 3 m |
| fixed | 32 | 3 | 50 | |
| tower | 20 | 3 | 30 | |

A job may override a gate per shot, with a `why` that `plan` prints. Two overrides are in use, both for engine motion
(section 8): S `a-establish` rest jitter ≤ 6 frames (the parked SF50 pivots on the spot before the reconstructed taxi
start with 0.07–0.14 m hops, 2–3 px at 72 m) and P `e-touchdown-edge` hero px/frame² ≤ 13 (the one-frame stall at
touchdown, 12.3 px/frame²).

## 6. Shot lists (30 fps; video time from the first frame)

The job gives each segment's speed and each shot's start as a data time or as an event of the scout trace plus an offset
(`{"event": "liftoff", "dt": -3.5}`); the times below are the current plans (`out/video/<case>/cams.json`). A speed change
is a 1-s linear ramp (a slow-down ends at the boundary, a speed-up starts there); a **skip segment** is a cut in data time
(no frame shows it; the engine runs through it) and must coincide with a shot start (`plan` checks). The overlay shows the
segment's factor.

**Case S — SF50 take-off, 28L** (3,720 frames, 2:04.0; low sun from the east-south-east, so the dolly and the edge camera
stand south of the runway with the sun behind them):

| Shot | Frames | Video | Speed | What |
|---|---|---|---|---|
| (a) `a-establish` | 0–180 | 0:00–0:06 | 1× | wide shot of the FBO ramp: 72 m south-east of the parked SF50, 12 m up, slow drift; hero on the right third |
| (b) `b-taxi-chase` | 181–958 | 0:06–0:32 | 1× → 8× | chase 40 m behind, 16 m up, aim 14 m ahead along the smoothed heading; heading spring 3.0 s (video) |
| `hold-wide` | 959–1098 | 0:32–0:36.6 | 24× | (cut: 10 s of data skipped) wide static view of the hold / run-up stop, 85 m south-south-east, 14 m up |
| `lineup-chase` | 1099–1514 | 0:36.6–0:50.5 | 4× → 1× | (cut: 34 s skipped) chase 34 m behind, 9 m up: to the runway end, line-up |
| (c) `c-roll-dolly` | 1515–2295 | 0:50.5–1:16.5 | 1× | camera car 60 m south of the 28L centreline, **5.0 m** up, 12 m behind the hero (held: lag error ≤ 0.64 m), top speed 42 m/s: the whole (reconstructed) roll |
| (e) `e-liftoff-edge` | 2296–2551 | 1:16.5–1:25.1 | 1× | fixed runway-edge camera 42 m south, 70 m past the lift-off point, **4.5 m** up; from lift-off − 3.5 s; pans, zooms 30–54° |
| (d) `d-climb-chase` | 2552–3539 | 1:25.1–1:58.0 | 1× → 2× | chase 55 m behind, 7 m above, 10 m right, through the left turn; from lift-off + 5 s |
| end card | 3540–3719 | 1:58–2:04 | — | credits (section 9) |

The two skip segments cut out engine motion at rest (finding F5): the 10 s around the stop at the hold, where the SF50
"at rest" yawed ~9° and back over 3 frames with a 0.2-m sideways step and later hopped 0.16 m backwards, and the end of
the hold, where a one-frame yaw snap sits at a hole edge. `hold-wide` now starts after them: rest jitter 0 frames [obs].

**Case P — PC-12 landing, 28L** (3,107 frames, 1:43.6; high sun from the south):

| Shot | Frames | Video | Speed | What |
|---|---|---|---|---|
| (d) `d-final-chase` | 0–1001 | 0:00–0:33.4 | 2× → 1× | chase 60 m behind, 6 m up, 9 m left on final (from where the app labels it "Final 28L") |
| (e) `e-touchdown-edge` | 1002–1302 | 0:33.4–0:43.4 | 1× | fixed runway-edge camera 42 m south, 70 m past the touchdown point, **4.5 m** up; from touchdown − 7 s |
| (c) `c-roll-dolly` | 1303–1927 | 0:43.4–1:04.3 | 1× | camera car 60 m south of the centreline, **5.0 m** up, 8 m behind (held: lag error ≤ 1.25 m), from touchdown + 3 s through the roll-out |
| (b) `b-taxi-chase` | 1928–2529 | 1:04.3–1:24.3 | 1× → 8× | chase 42 m behind, 16 m up: taxi-in to the T-hangar lane |
| (a) `a-ramp-establish` | 2530–2926 | 1:24.3–1:37.6 | 2× → 1× | wide shot from the open end of the T-hangar lane, 75 m east-north-east of where it stops (`anchor: 'end'`), 16 m up: it taxis in and parks |
| end card | 2927–3106 | 1:37.6–1:43.6 | — | credits |

**Plan checks [obs, both cases, every frame]:** all gates pass; hero never off-screen (largest |NDC| 0.49), no line of
sight through a building, no constraint had to act, closest aircraft 13.4 m from the camera, closest light unit 16 m (the
S dolly passes the 28L VASI boxes). On-screen motion of the hero (px/frame at 1920 × 1080): ≤ 1.9 in every shot except the
P touchdown edge shot (≤ 9.7 at touchdown) — the 8× chases ≤ 1.5 (S) and ≤ 1.0 (P), the dollies ≤ 0.2 (S) and ≤ 1.9 (P);
its change ≤ 2.7 px/frame² (the P ramp shot, as the PC-12 turns into its spot) except the P touchdown frame (12.3, the
engine's one-frame stall, section 11). Background pan speed from the camera's rotation: ≤ 1.2 px/frame in the establishing shots and the dollies, ≤ 6.2 in the
climb-out and final chases; the fast pans are the S taxi chase (≤ 34.2 px/frame, 96 frames above 20), the S line-up chase
(≤ 24.2, 61 frames), the S lift-off edge (≤ 42.8, 66 frames), the P touchdown edge (≤ 32.5, 54 frames) and the P taxi
chase (≤ 18.6, none above 20): those carry the motion blur (section 2.4), which halves the streak a viewer sees between
two frames (the review measured a mean absolute difference of 15.9 per pixel between two frames of the S whip pan without
blur; with blur, between frames 270 and 271 of the determinism range: 3.3).

## 7. Render time (finding F12)

One frame = the engine sub-steps + the app's frame (SwiftShader WebGL2, 1920 × 1080, MSAA 4, 4096 shadow maps, the
detailed hero model, the motion-blur pass) + the overlay + `page.screenshot` (PNG) + the write. Measured on this machine
(4 CPUs, no GPU), seconds per frame [obs]:

| Run | Frames | min | median | max | load (1 min) |
|---|---|---|---|---|---|
| review: S frames 600–609, shutter 0 | 10 | 3.43 | **3.96** | 5.79 | 2.1–3.5 |
| review: determinism runs, shutter 0 | 30 × 3 | 3.27 / 4.17 / 5.52 | 3.37 / 4.57 / 6.82 | 4.68 / 7.20 / 7.43 | 4–11 |
| this round: determinism A / B / C, shutter 0.5 | 30 / 30 / 36 | 5.88 / 7.69 / 7.13 | 7.63 / 9.48 / 9.85 | 8.74 / 11.84 / 14.71 | 5.9 / 10.1 / 10.5 (median) |
| this round: P test clip (final chase), shutter 0.5 | 90 | 7.02 | 9.24 | 15.09 | 9.5 |
| this round: determinism A / B / C after the refresh, shutter 0.5 | 30 / 30 / 36 | 7.17 / 9.94 / 7.98 | 11.23 / 13.51 / 12.91 | 17.06 / 17.09 / 20.00 | 11.7 / 14.0 / 14.6 |
| this round: S test clip (taxi chase 8×), shutter 0.5 | 105 | 8.25 | 11.47 | 16.57 | 14.0 |
| this round: P test clip again (refreshed snapshot) | 90 | 7.47 | 13.43 | 16.99 | 14.3 |

The other two workflows kept the load at 6–16 for every run of this round (and up to three of these runs overlapped), so
no quiet-machine figure with the blur pass exists; the blur pass is one full-screen pass (not timed separately). The end-card frames need no 3-D frame (0.1–0.5 s).
Skip-ahead before a range: ~100 frames/s; scout: case S 3,720 frames in 42 s.

**Estimate for the planned lists** (3-D frames: S 3,540 + P 2,927 = 6,467; + 360 end-card frames), using the **median**:

| | quiet machine (median 3.96 s/frame) | under the load of this round (load 10–15, median ~11 s/frame) |
|---|---|---|
| case S | 3.9 h | 10.8 h |
| case P | 3.2 h | 8.9 h |
| both, one process | **7.1 h** | 19.8 h |
| + encode (libx264 `-preset slow` at 1080p, measured 7.2 fps at load ~9 and 3.2–3.6 fps at load 14: 90 frames in 12.5–25.3 s, 105 in 32.9 s; 7,186 frames) | + **0.3 h** | + 0.6 h |
| total | **≈ 7.5 h** | ≈ 20 h |

Two processes at once on a quiet machine were not measured (in the earlier round, under load, two processes gave ~4.4 s
of throughput per frame against 6–8 s for one). **Disk:** a frame is 1.4–1.9 MB as PNG (with blur: S taxi chase 1.53 MB, S
whip pan 1.38 MB, P final chase 1.90 MB on average), so the two full frame sets need **~12 GB** (S 3,720 × ~1.5 + P 3,107 ×
1.9); the disk has 24 GB free [obs, df]. The old test-frame directories (`out/video/*/test*_frames`, `picks*`) can be deleted first (~0.7 GB).

**Proposal.** 30 fps (the 1× dolly and the edge pans need it), case S 2:04 and case P 1:44 as planned. If the time is too
long: trim the climb-out chase (33 s → 20 s) and the final chase (33 s → 22 s), which brings S to ~1:51 and P to ~1:33;
render each case as two `--frames` halves.

## 8. App changes wanted (for the orchestrator; nothing here was applied)

1. **Phase 3b model wiring** (`js/live/aircraft.js`, `js/live/traffic.js`; the diff is in `docs/phase3_models.md` §3):
   until then the director swaps the hero's drawable from outside, and the engine still places it with the class-rule
   dims (`gaDims`), so the drawn main gear sits 0.448 m (PC-12) / 0.693 m (SF50) off the engine's gear origin along the
   axis (`modelDims` fixes it). The view should also drive `setFlaps` (degrees: `disp.flaps` is 0 / 1 today), `rotor`
   for fixed-wing types (the app's sync sets `rotor = 0` for every fixed-wing drawable) and `groundRef`.
2. **An engine-step hook** in `app.js`: `HWD.stepEngine(now, dt)` = the engine part of `frame()`. The director calls
   `traffic.update` + `physics.resolve` directly for its sub-steps and the pre-roll; a system added to `frame()` later
   would be missed silently.
3. **A separate animation dt** in `app.js frame()` (finding F10): `frame(wall, { engineDt })` — the engine steps by
   `engineDt`, `simT`, `views.sync`, the rig and the environment timer by `wall`. Today the director wraps
   `traffic.update` / `physics.resolve` on the instances to get the same effect.
4. **A no-draw frame**: `HWD.qa.frame({ render: false })` that computes the camera and sets `R.prev` like `R.render`, but
   draws nothing (today the director stubs `R.render` / `R.present` for the call and sets `R.prev` itself).
5. **Capture post settings**: `HWD.setPost({ shutter })` for captured frames (today the director wraps `R.render`'s
   `post` argument).
6. **A camera override**: `HWD.setCamera(fn | null)` used by `frame()` instead of `rig.camera()` (today the rig
   instance's `camera` / `update` are replaced).
7. **Sample provenance on the track**: `tr.disp.mode` (the target's `o.mode`) and the gap around the display time; the
   director re-derives obs / inf / rec / nos from `tr.fx` with a copy of `HOLE_S` (8 s).
8. **Rest pose stability** (Phase 2 owner, `js/live/traffic.js` / `GroundPhysics`; finding F5): no pose change while the
   engine has an aircraft at rest unless a fix moves it. Seen in case S: the parked SF50 pivots ~45° on the spot with
   0.07–0.14-m hops at 1× before the reconstructed taxi start (frames 56–143 of `a-establish`, gs ≤ 1.3 kt, single-frame
   steps up to 0.138 m, i.e. ~8 kt); at the hold (the review's trace), "at rest" (mode `rest`, gs ≤ 0.66 kt), heading
   120.9° → 112.4° → 111.3° → 120.5° over three frames with a 0.2-m sideways step, then a 0.16-m hop backwards (cut out by
   a skip segment);
   a one-frame yaw snap at the hole edge at the end of the hold (cut out). Check the GroundPhysics separation pushes at
   the hold.
9. **A stop in the middle of a moving hole** (Phase 2 owner, new): in case S the engine stops the taxiing SF50 for ~16 s
   of data inside a 48-s hole whose two end fixes are both moving at 6–9 kt (nearest other aircraft 81 m), then moves on;
   a slower continuous taxi over the hole would match the fixes as well. The video now labels such a hole "Reconstructed ·
   the stop is inferred" (section 3).
10. **Classifier labels seen in the videos** (`js/live/classifier.js`): case P is labelled "Overflight (not HWD traffic)"
    on its base leg and the first part of final, until ~1.3 NM out (the video starts where the label turns "Final 28L");
    case S is labelled "Taxiing" from the first frame of the video, while it still stands (~2 s) and through the
    reconstructed pivot; case P is labelled "Taxiing" for the last 3.9 s while it stands at 0 kt in its parking spot (the
    video shows "Stopped" there, a video rule [inf]; the app should say "Stopped" / "Parked" itself).

## 9. Overlay and end card (findings F7, F8, F9)

Caption (top left): the type name — the ICAO type designator's family name only, **"Cirrus SF50 Vision Jet"** /
**"Pilatus PC-12"**: the pack's records carry the designator (`t`) and no model or variant field (fields of the PC12
records: `_drop, _masked, _prov, _pt, _src, alt_*, baro_rate, category, emergency, geom_rate, gs, lat, lon, mlat, nac_p,
nav_*, nic, seen*, t, tisb, track, true_heading, type`), and `PC12` covers the PC-12/45, /47, /47E (NG), NGX and PRO.
(Before this round the caption said "Pilatus PC-12 NGX", an unverified variant.) Then "Hayward Executive (KHWD) · runway
28L", the phase line (section 3) and the scene's local time from the data clock (`America/Los_Angeles`, to the second).
Top right: the time-lapse factor ("8×", "TIME-LAPSE"), hidden near 1×. Bottom left: the provenance pill (section 3).
Bottom right: the METAR in force at the scene time (the pack's KHWD reports, remarks cut) and a one-line credit.

End card (last 6 s): what the video is; the D1 sentence; how the holes are filled (interpolated / reconstructed / no
signal); **what the drawn model is and what the data does not say** — PC-12: "drawn as a PC-12 PRO (NGX airframe), the
model of this repository; the ADS-B data gives only the ICAO type designator PC12, which covers every PC-12 variant
(PC-12/45, /47, /47E, NGX, PRO), so this aircraft's variant is not known"; SF50: the production generation is not known;
and the credits: the six notices of `docs/ATTRIBUTION.md` "Notices to show in the app" word for word (imported from
`js/live/about.js NOTICES`, tags stripped), the METAR source (NOAA / NWS Aviation Weather Center), the ground imagery —
now word for word the line of the app's About panel, which keeps the caveat of `docs/ATTRIBUTION.md`: "Ground imagery:
USDA NAIP 2024 (…), public domain. The 24 km backdrop beyond the airport is the USDA NAIP image-service mosaic, which
includes undated overview imagery." (before: "USDA NAIP 2024 aerial imagery", which the backdrop is not) — and the two own
models.

**The date (D1, owner decision).** By default the frames show the date and the time: the caption clock (time of day to the
second), the METAR's day-time group (`ddhhmmZ`: the day of the month and the time) and the end card's "recorded ADS-B,
<month> <year>". (The earlier version of this page said "the end card names no date by default"; that was wrong.) Job
options: `timeOnly: true` drops the METAR day-time group and the month (the time of day stays); `endDate: true` puts the
full date and time on the end card. The overlay refuses to capture a frame whose text looks like a track key, a 6-hex
ICAO address or an N-number (a D1 guard). The overlay's classes carry a `vv-` prefix.

## 10. Test clips (what was rendered, and what the stills show)

All clips 1920 × 1080, 30 fps, H.264 High, yuv420p, CRF 16, `-preset slow`, faststart; frame count checked by ffprobe.
Three stills each (10 / 50 / 90 %), all looked at.

| Clip | Frames | Size | Shot | Snapshot | Hero vs scout |
|---|---|---|---|---|---|
| `out/video/S/test_taxi.mp4`, `test2_taxi.mp4` (earlier round) | 105, frames 427–531 | 2.07 / 2.05 MB | taxi chase, 8× | working tree | 0.0000 m |
| `out/video/P/test_final.mp4`, `test2_final.mp4` (earlier round) | 90, frames 368–457 | 2.71 / 2.64 MB | final chase | working tree | 3.96 m / 0.0000 m |
| `out/video/S/test3_taxi.mp4` (this round) | 105, frames 427–531 | 1.68 MB | taxi chase, 8× | `e26c545…` | **0.00000 m** |
| `out/video/P/test3_final.mp4` (this round; rendered on `baa39ff…`, then again on the refreshed `90e710a…`) | 90, frames 368–457 | 2.56 MB | final chase, 1× | `90e710a…` | **0.00000 m** (both) |

What the stills and spot frames show (all looked at; spot frames by `render --pick`, `out/video/<case>/picks4*/`):
- **S taxi chase (8×), test clip**: the detailed SF50 on the taxiway centreline in the low sun with long shadows, the 8×
  badge, the METAR in force. In this range the engine stops the SF50 for ~16 s of data inside a recorder hole (section 3):
  the caption reads "Stopped" and "Reconstructed (no ADS-B fix) · no fix for 48 s: the stop is inferred", then "Taxiing"
  and the green "Recorded ADS-B position" as the observed window passes. Problems: the hangar wall fills the left third,
  the parked business jet beside the lane is a GA placeholder, and the grass right of the taxiway is a soft smear — the
  ground texture at that grazing angle, not the blur (the earlier round's shutter-0 still of the same view shows the same).
- **P final chase (1×), test clip**: "Pilatus PC-12" (no variant), gear down, the beacon lit in one still and dark in the
  next (its cycle), "Final 28L", "Reconstructed (no ADS-B fix) · 47 s between the last airborne and the first ground fix";
  the hero ~120 px right of centre (the camera is 9 m left), steady; the foreground ground 150 m below carries a light
  motion blur. From this angle the propeller disc and the flaps are not readable.
- **Motion blur**: S determinism frames 270 / 271 (the fastest whip pan of the taxi chase, 34 px/frame): the background
  streaks, the SF50 stays sharp; consecutive frames differ by 3.3 on average (the review: 15.9 without blur). S 2440 (the
  lift-off edge camera panning at ~42 px/frame), rendered with and without blur: with it the hangars and the runway
  markings streak along the pan, the SF50 is sharp in both. S 1000 (the static 24× hold shot) is bit-identical with and
  without blur: a still camera gets none.
- **Spot frames**: S 100 (`a-establish`: the parked SF50 on the right third, the pill "Reconstructed · no fix for 274 s:
  when it starts to move is inferred"; a parked GA placeholder sits in the foreground, 34 m from the camera); S 1000
  (`hold-wide`, 24×: the SF50 on the left third at the hold; the ground right of it is a soft smear in both renders);
  S 1600 (the dolly at 5 m: the SF50 starting its roll); S 2380 / 2440 (the edge camera at 4.5 m: the SF50 lifting off
  against the low sun); S 3000 (the climb-out chase in the left turn, 2×); S 3700 (end card); P 1213 (the touchdown edge
  camera at 4.5 m, the 28L VASI boxes 48 m away on the right); **P 1327** (24 frames after the cut into the dolly, the
  frame the review found off its thirds line: the PC-12 now sits on the right thirds line, the background streaked by the
  car's speed); P 1415 (roll-out); P 2214 (8× taxi chase in a turn); **P 2900** ("Stopped" in the T-hangar lane, where the
  app says "Taxiing"); P 3080 (end card: "Pilatus PC-12 · Landing, runway 28L", the model note, the imagery caveat);
  `timeOnly` variants S 1000 / 3700 and P 3080: no METAR day-time group, no month on the end card.
- Fixed after looking in this round: the engine's mid-hole stop was labelled "Interpolated between ADS-B fixes" (now
  "the stop is inferred", section 3). A precaution, not an observed fault: `dev/video.html` now treats frame 0 as a cut,
  so the preview's first frame can never blur against a camera the app rendered during boot (in the renders frame 0 is
  black under the fade-in).

## 11. Open items / not verified

- **The full videos are not rendered** (~7.5 h on a quiet machine, section 7). Before they are: wait until the fix rounds
  have landed, take a new snapshot (`snapshot --refresh`), then `scout`, `plan` (check the gates and the report: shot
  starts given as data times may need moving if the engine's timing changes), `render` (split into `--frames` ranges if
  wanted), `encode`, `stills`.
- **The plan is tied to the exact timeline** (finding F13): the engine is sensitive to its step grid. Runs on an aligned
  grid agree (the review: 1× vs 8× / 24× within 4.5 cm, same phase, label and provenance), but the job's timeline (ramps
  with h < 1/30, a different pre-roll end) differs from a 1× run by up to 0.78 m, and the P touchdown one-frame stall
  depends on the grid. Any change to a segment's speed or start changes the path: scout and plan again (the stamp chain
  enforces it: the job's segments are part of the scout key).
- **Engine motion seen in the traces** (Phase 2 owner; section 8 items 8–10): (1) case P stands still for one frame
  (1/30 s at 80 kt; frame 1213: 0.000 m against 1.38 m in the frames around it) at touchdown — a visible hitch; (2) case P
  lands flat: pitch ≤ 0.3° in the flare; (3) case S lifts off flat: pitch 0.00° on the whole roll, 0.9° a third of a
  second after lift-off (no rotation); (4) case S, at the start of the roll, yaws ~5° left on the spot and back over ~2 s
  (299.2° → 294.4° → 299.7° at 0–6 kt); (5) the roll,
  lift-off, touchdown and roll-out of both cases lie in one recorder hole each (50 s / 47 s): all of it is reconstructed
  (the overlay says so) — the Phase 2 fixer's take-off / landing reconstruction will change them; (6) the parked pivot
  with hops in the opening shot of case S (2–3 px at 72 m; the rest-jitter gate of that shot is raised with a reason);
  (7) the mid-hole stop of the S taxi.
- **Independent check of the scouts** [obs]: the Phase 2 fixer's per-second traces (`out/od3/trace_case_{S,P}.json`, its
  own harness run on its own pack window and step grid, with an earlier engine version) agree with the scouts on
  the ground within 1–3 m (S: taxi median 0.8 m, hold 0.03 m, roll 1.6 m; P: roll 1.1 m, taxi 0.1 m), and in the air
  within 5–20 m (S climb-out median 13.6 m, P final median 4.7 m) — consistent with the step-grid and pack-window
  sensitivity above, not a fault of either.
- **Low cameras** (finding F11): the edge and dolly cameras moved from 1.8–2.2 m to 4.5–5.0 m, so the 1.2-m NAIP ground in
  the lower part of the frame is magnified less (spot frames S 1600, 2380, 2440 and P 1213, 1327, 1415: the runway band
  now fills more of the frame; the near ground is still soft, but less of the frame than at 1.8–2.2 m). The ground near
  the 28L east end (the S hold shot) and beside the S taxi lane looks smeared even with the blur off (bit-identical
  renders): a ground-texture item for the world owner. No z-fighting, shadow acne, LOD pop or fade dither was found by
  the review (the hero's `lodDist` is 8,000 m; alpha 1.0 on every frame); distant hangar edges crawl slightly at
  sub-pixel motion.
- The hero is drawn with the detailed model but positioned with the class-rule dims (section 8, item 1); every other
  aircraft is a GA placeholder (a blocky bizjet stands next to the detailed SF50 in the taxi shots).
- The S lift-off edge camera looks east into the low sun, so the SF50 lifts off as a silhouette against the glare (left for
  the owner). In the 8× taxi chase of case S a hangar wall fills the left third for a few seconds.
- Not verified: `dev/video.html` on a real GPU (loaded headless in this round on the working tree: it boots, pre-rolls,
  steps three frames with the planned camera and the overlay; no page error, no missing file); the render time with the blur pass on a quiet machine and with two
  processes; SwiftShader only (a GPU machine should be several times faster — the pipeline is the same).

## 12. Review findings of fix round 1 and where they are addressed

| # | Finding | Fix | Verified by |
|---|---|---|---|
| F1 | renders not pinned to app / model versions; deviation logged only | frozen snapshot + manifest + checked server; stamp chain trace → plan → frames; abort at 0.01 m; models hashed when served; `--refresh=video` | section 2.1; stale P frames refused; 0.00000 m in every run |
| F2 | encode silently truncates at a missing frame | presence + PNG CRC check + PLAN_STAMP before ffmpeg; ffmpeg error output fails; ffprobe count; atomic writes; resume re-draws damaged frames | section 2.6: missing, truncated and CRC-valid-undecodable frames each refused |
| F3 | dolly car drifts to 63 m / 48 m behind | feed-forward of velocity and acceleration; hero px/frame, px/frame², pan, lag error in the report, gated | section 5: lag error ≤ 0.64 / 1.25 m; hero x 1,247–1,249 px |
| F4 | no motion blur on fast pans; stale blur reference | shutter 0.5 on captured frames; the no-draw stub sets `R.prev`; `R.prev` cleared at cuts | section 4: A = B and A = C with blur |
| F5 | SF50 twitch "at rest" in the hold shot | skip segments cut it; rest-jitter metric and gate; app change wanted | section 6; section 8 item 8 |
| F6 | provenance wording, short pill states, "Taxiing" at 0 kt | `rec` start / stop / pause / shift, `nos` for > 90 s; states held ≥ 0.5 s; "Stopped" | section 3 |
| F7 | seed = the recording date; "no date" claim wrong | neutral seed `0x5eed`; the doc states the date is visible; `timeOnly` option | sections 2.2, 9; `timeOnly` spot frames S 1000 / 3700, P 3080 |
| F8 | "PC-12 NGX" unverified | "Pilatus PC-12"; end card names the drawn model and the unknown variant | P test stills |
| F9 | imagery credit dropped the undated-overview caveat | the About panel's line, word for word | section 9 |
| F10 | animation clock slow in speed ramps | frame clock + `views.sync` at 1/fps, engine at h | section 2.3 probe |
| F11 | low cameras smear the NAIP ground | edge 4.5 m, dolly 5.0 m | section 11, picks |
| F12 | estimate used the minimum | median, encode time, disk budget | section 7 |
| F13 | step-grid sensitivity | the scout key includes the segments; noted | section 11 |
