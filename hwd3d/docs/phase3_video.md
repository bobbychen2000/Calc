# Phase 3 (OD3) — deterministic video pipeline

**Status 2026-11-14, fix round 4 iteration 2 (section 14):** the snapshots now hold the final traffic engine (renderer,
models and data still frozen from Phase 3b); both cases re-scouted and re-planned, all gates pass, determinism and spot
stills re-checked. **Phase 3b integration (section 13).** The app now has the hooks this pipeline needed (section 8:
`HWD.stepEngine`, a separate engine dt, a no-draw frame, `HWD.setPost`, `HWD.setCamera`) and draws every PC-12 / SF50 with
its detailed model itself, with gear, flaps, propeller / fan, control surfaces and lights driven from the motion
(`js/live/aircraft.js`, `docs/phase2_app.md` section 11); the director's monkeypatches are gone. Both cases were
re-scouted and re-planned on the current engine, with packs at the 120-s lookahead of decision (c), and 2-s spot clips
were rendered at three key instants per case. Current models: SF50 `sf50.glb` **49242e41…**, PC-12 = the original
`pc12/out/pc12.glb` **87731cce…** (OD4, `docs/phase3_models.md` section 15). The earlier test clips of section 10 show
the models of their round (the PC-12 then was 6e349329…, a retired build). **The full videos are not rendered**: the
orchestrator starts them after the recheck, from a new snapshot (section 11).

Before that: status after **review fix round 1** of the video pipeline (findings F1–F13; section 12 maps each finding to
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
| `js/video/director.js` | In-page director: hero by rule, the model preload, pre-roll, per-frame stepping through the app's hooks (section 2.4: camera, engine dt, no-draw frames, cuts, motion blur), the hero's pose + its driven state (gear, flaps, rotor, controls, lights) + the provenance of the current sample, overlay update. |
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

Current snapshots [obs] (Phase 3b, section 13): case S tree `73209bc0db88…`, case P tree `df19cf8c2cd0…`, both taken
from the working tree (git `b6afcd3` + 10 modified paths) while the round-4 engine fix was in progress, so their engines
differ (`js/live/traffic.js` sha256 `fc8d38d3…` in S, `f2cb1bdd…` in P); models `sf50.glb` **49242e41…** and `pc12.glb`
**87731cce…** in both. (Earlier: S `e26c545e9385…`, P `90e710a5a07f…`, git `b0d55c1`, `pc12.glb` 6e349329….) Before the
full render, take a new snapshot of the then-current app (`snapshot --refresh`), scout and plan again (section 11).

### 2.2 The app and the virtual clock

**The pipeline does not modify the app**: it uses only the app's own hooks (section 2.4). The driver opens `live.html?mode=replay&fixedres=1&pack=out/video/packs/pack_vS.json.gz` at
1920 × 1080, DPR 1 (`?fixedres=1` pins the render scale: no dynamic resolution, OD1 full quality), from the snapshot. The
app runs its replay path: P1's in-page shim (`out/replay/replay_shim.js`) feeds the pack through the live code path
(stream feed, engine, physics, drawables).

**Virtual clock** (`js/video/vclock.js`, installed before any page script):
- `Date.now()` / `new Date()` → a virtual **wall** clock. The epoch is `t0 = (pack.from + lookahead_s) × 1000`, so the
  shim's offset is 0: the engine's wall clock IS the recording clock (+ the pack's display lookahead: 120 s since Phase 3b,
  decision (c); 60 s before). The tower state, the
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
own sub-step `h`, through the app's own frame call `HWD.qa.frame({ wall: 1/30, engineDt: h })` (Phase 3b; before, the
director wrapped `traffic.update` / `physics.resolve` on the instances). So the app's per-frame clock (`simT`:
propeller and fan angle, strobe and beacon phase; flap and gear lag; the 30-s environment refresh) runs at video rate in
every frame, and the engine steps exactly as before. Before this round the frame dt was `h`, so inside the 1×–2× speed
ramps (`h = speed / 60`) propellers and anti-collision lights ran at down to 52 % of their video-time rate. Probe [obs,
case P, frames 270–320, the 2× → 1× ramp, h down to 0.633/30]: the engine received `h` in every sub-step, `views.sync`
and the frame clock 1/30 s in all 51 frames, no mismatch.

Frames that are not captured (the scout, the skip-ahead before a frame range, the opaque end card) are the app's no-draw
frame (`render: false`, Phase 3b; before: `R.render` / `R.present` stubbed by the director): it computes the camera and
sets the renderer's previous camera (`R.prev`) exactly as `R.render` ends, so the motion-blur reference of the first drawn
frame of a range, a resume or a pick is the true previous frame. Everything else (engine, drawables, their motion-vector bookkeeping in `scene.frame` /
`scene.commit`) advances as in a drawn frame.

### 2.4 The app's hooks (Phase 3b; before: seams on the app's instances)

The app's own loop is paused (`HWD.qa.pause(true)`): the director drives every frame.

- *Camera*: `HWD.setCamera(() => the planned camera of this frame)` (before: `HWD.rig.update` → no-op, `HWD.rig.camera`
  replaced).
- *Detailed models*: the app's own views draw every PC12 / SF50 with its `DetailedAircraft` and drive gear, flaps,
  propeller / fan, control surfaces and lights from the motion (`js/live/aircraft.js`; the rules and their [inf] values
  are in `docs/phase2_app.md` section 11). The director only loads both models before the first frame, so no model
  appears at a load-dependent frame. (Before: the director wrapped `HWD.views.sync`, swapped the hero's placeholder for a
  `DetailedAircraft` and set its rotor (PC-12 110 / 178 rad/s, SF50 100 / 120) and flaps (15 take-off, 40 / 39 landing);
  other PC-12s and SF50s stayed placeholders.)
- *Engine dt*: `HWD.qa.frame({ engineDt: h })`; the sub-steps and the pre-roll call `HWD.stepEngine(now, h)` (section 2.3).
- *No-draw frames*: `HWD.qa.frame({ render: false })` (section 2.3).
- *Motion blur* (finding F4): `HWD.setPost({ shutter: 0.5 })` (a 180° shutter: the app's own blur pass, `js/renderer.js`,
  clamped at 3 % of the width), set once by the director; the app's own loop keeps 0. At a cut the frame call carries
  `cut: true`, which clears `R.prev`, so the first frame of a shot carries no camera motion from the last one.
- *UI*: `HWD.qa.hideUI(true)` (`body.qa`) hides the HUD; `#loading` is hidden by the overlay CSS.

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
| case S taxi chase (8×), job test `det3s`, 3.0 s, through the app's hooks with every PC-12 / SF50 drawn by the app | 90 | **0.5** | **90 / 90** | **90 / 90** (C drew 6 earlier frames) | Phase 3b, snapshot `73209bc0…` (A / B / C median 7.5 / 8.7 / 9.1 s per frame, load 8–11) |

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
| (c) `c-roll-dolly` | 1515–2219 | 0:50.5–1:14.0 | 1× | camera car 60 m south of the 28L centreline, **5.0 m** up, 12 m behind the hero (held: lag error ≤ 0.61 m), top speed 42 m/s: the end of the line-up wait (the roll now starts ~5 s into the shot) and the whole (reconstructed) roll |
| (e) `e-liftoff-edge` | 2220–2475 | 1:14.0–1:22.5 | 1× | fixed runway-edge camera 42 m south, 70 m past the lift-off point, **4.5 m** up; from lift-off − 3.5 s; pans, zooms 30–54°: the rotation and the lift-off |
| (d) `d-climb-chase` | 2476–3539 | 1:22.5–1:58.0 | 1× → 2× | chase 45 m behind, **3 m below**, 12 m right (Phase 3b: from below, so the gear retraction is seen; before 55 m behind, 7 m above, 10 m right), through the left turn; from lift-off + 5 s |
| end card | 3540–3719 | 1:58–2:04 | — | credits (section 9) |

The two skip segments cut out engine motion at rest (finding F5): the 10 s around the stop at the hold, where the SF50
"at rest" yawed ~9° and back over 3 frames with a 0.2-m sideways step and later hopped 0.16 m backwards, and the end of
the hold, where a one-frame yaw snap sits at a hole edge. `hold-wide` now starts after them: rest jitter 0 frames [obs].

**Case P — PC-12 landing, 28L** (3,107 frames, 1:43.6; high sun from the south):

| Shot | Frames | Video | Speed | What |
|---|---|---|---|---|
| (d) `d-final-chase` | 0–976 | 0:00–0:32.6 | 2× → 1× | chase 60 m behind, 6 m up, 9 m left on final (from where the app labels it "Final 28L") |
| (e) `e-touchdown-edge` | 977–1277 | 0:32.6–0:42.6 | 1× | fixed runway-edge camera 42 m south, 70 m past the touchdown point, **4.5 m** up; from touchdown − 7 s: the flare and the touchdown |
| (c) `c-roll-dolly` | 1278–1927 | 0:42.6–1:04.3 | 1× | camera car 60 m south of the centreline, **5.0 m** up, 8 m behind (held: lag error ≤ 1.22 m), from touchdown + 3 s through the roll-out |
| (b) `b-taxi-chase` | 1928–2529 | 1:04.3–1:24.3 | 1× → 8× | chase 42 m behind, 16 m up: taxi-in to the T-hangar lane |
| (a) `a-ramp-establish` | 2530–2926 | 1:24.3–1:37.6 | 2× → 1× | wide shot from the open end of the T-hangar lane, 75 m east-north-east of where it stops (`anchor: 'end'`), 16 m up: it taxis in and parks |
| end card | 2927–3106 | 1:37.6–1:43.6 | — | credits |

**Plan checks [obs, both cases, every frame; the Phase 3b re-plan in section 13]:** all gates pass; hero never off-screen (largest |NDC| 0.49), no line of
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
| Phase 3b: S spot clips (3 × 60 picks, one process; app hooks, detailed models in the app) | 180 | 3.72 | 7.42 | 14.24 | 9.1 |
| Phase 3b: P spot clips (3 × 60 picks, one process) | 180 | 3.64 | **4.49** | 8.91 | 6.0 |

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

## 8. App changes: status (Phase 3b, 2026-11-14)

Items 2-6 were applied in `js/live/app.js` and item 1 in `js/live/aircraft.js` (except the `traffic.js` part); the
director now uses them (section 2.4). Items 7-10 belong to the Phase 2 owner (`js/live/traffic.js`, `classifier.js`).

1. **Phase 3b model wiring.** *Done in the views:* every PC12 / SF50 is a `DetailedAircraft`, built from the dims record
   with the model's frame (`withModelFrame`), with flaps (degrees, the model's own settings), rotor, control surfaces,
   lights and `groundRef` driven from the motion (`docs/phase2_app.md` section 11). *Open (engine owner):* `js/live/traffic.js`
   still makes its dims records with `gaDims` (two places), so the engine places the gear origin by the class rule and the
   drawn main gear sits 0.448 m (PC-12) / 0.693 m (SF50) off it along the axis; the two-line change to `modelDims` is in
   `docs/phase3_models.md` section 3.
2. **Engine-step hook** - done: `HWD.stepEngine(now, dt)`.
3. **Separate animation dt** - done: `frame(wall, { engineDt })`; `HWD.qa.frame({ wall, engineDt })`.
4. **No-draw frame** - done: `HWD.qa.frame({ render: false })` (and `cut: true` for a camera cut).
5. **Capture post settings** - done: `HWD.setPost({ shutter })`.
6. **Camera override** - done: `HWD.setCamera(fn | null)`.
7. **Sample provenance on the track** (open, engine): `tr.disp.mode` (the target's `o.mode`) and the gap around the display
   time; the director re-derives obs / inf / rec / nos from `tr.fx` with a copy of `HOLE_S` (8 s).
8. **Rest pose stability** (open, engine; finding F5): no pose change while the engine has an aircraft at rest unless a
   fix moves it. Re-planned on the current engine (section 13), the opening shot of case S measures a rest jitter of
   0 frames (the earlier 6-frame override is kept in the job but no longer needed); the hold is still cut by the two skip
   segments.
9. **A stop in the middle of a moving hole** (open, engine): in case S the engine stopped the taxiing SF50 for ~16 s of
   data inside a 48-s hole whose two end fixes both move; the video labels such a hole "Reconstructed · the stop is
   inferred" (section 3). Not re-checked in this round.
10. **Classifier labels seen in the videos** (open, `js/live/classifier.js`): case S is labelled "Taxiing" from the first
    frame while it still stands; case P "Taxiing" for the last seconds at 0 kt in its parking spot (the video shows
    "Stopped", a video rule [inf]). With the detailed models in the app this also keeps the engine at idle until the phase
    changes (the views shut it down only when parked, in a hangar or silent at rest).

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

**Phase 3b spot clips** (section 13; 2 s = 60 frames each, all 1920 × 1080, 30 fps, shutter 0.5, the planned cameras
of the Phase 3b plans, rendered as picks into `out/video/<case>/spots/` and encoded from there; hero vs scout 0.00000 m
in both runs, 0 page errors; three stills each at 10 / 50 / 90 %, all looked at, plus crops of the aircraft):

| Clip | Frames | Shot | Size | What the stills show |
|---|---|---|---|---|
| `out/video/S/spot_roll.mp4` | 1660–1719 | c-roll-dolly | 0.49 MB | the SF50 lined up at the 28L start (beside the chevrons), gear down, flaps 15, then the first metres of the roll; caption "Lined up" → "Take-off roll", pill "Reconstructed … 50 s between the last ground and the first airborne fix". The 5.4° yaw onto the runway heading at 3 kt (frames 1691–1697, section 11) is hard to see side-on |
| `out/video/S/spot_rotation.mp4` | 2280–2339 | e-liftoff-edge | 0.89 MB | the SF50 at ~80 kt with both wing-tip landing lights lit, then nose up with the nose wheel off (rotation), the main wheels leaving the runway at frame 2325; flaps 15, gear down |
| `out/video/S/spot_gear.mp4` | 2540–2599 | d-climb-chase (from below) | 1.05 MB | from behind and below, 15–25 m up: all three legs down at the start, then the main legs swinging inward and the nose leg folding (gear 0.94 → 0.6); the V-tail and the fan nacelle against the sky |
| `out/video/P/spot_flare.mp4` | 1090–1149 | e-touchdown-edge | 0.81 MB | the PC-12 ~3 m above 28L, landing lights and beacon lit, gear down, flaps 40, the nose rising (pitch 3 → 5°); far (~300 m) in this shot, the crops show the attitude |
| `out/video/P/spot_touchdown.mp4` | 1170–1229 | e-touchdown-edge | 1.14 MB | the main wheels on the runway with the nose still up and the propeller disc, then the nose lowering; the flaps' Fowler gap visible |
| `out/video/P/spot_rollout.mp4` | 1820–1879 | c-roll-dolly | 0.93 MB | the PC-12 side-on at 40 → 30 kt, flaps 40, nose wheel down; caption "Landing roll 28L", pill "… no fix for 48 s: when it stops is inferred"; the landing light goes out at 30 kt (frame 1865) |

Seen in the stills, not fixed here: the landing-light sprites are large white discs by day (the flare shot: each about a
tenth of the wing span across at ~300 m; `js/env/aircraft_lights.js`, P2's day size, already noted in `docs/phase2_traffic.md` §6); the
ground beside the runway is soft at the 4.5–5 m cameras (section 11, low cameras).

## 11. Open items / not verified

- **The full videos are not rendered** (~7.5 h on a quiet machine, section 7; the detailed models of every PC-12 / SF50
  in view and the low climb-out chase add a little). Before they are: wait until the fix rounds have landed, take a new
  snapshot of BOTH cases (`snapshot --refresh`: the Phase 3b snapshots hold two different mid-round engines, section 2.1),
  then `scout`, `plan` (check the gates, the report and the events of section 13: the shot starts are data times or
  events, and the c-roll-dolly of case S may want to start nearer the roll start), `render` (split into `--frames` ranges
  if wanted), `encode`, `stills`. The packs are now the 120-s lookahead ones (decision (c)); the 60-s packs of the earlier
  rounds are kept in `out/video/packs/old60/`.
- **The plan is tied to the exact timeline** (finding F13): the engine is sensitive to its step grid. Runs on an aligned
  grid agree (the review: 1× vs 8× / 24× within 4.5 cm, same phase, label and provenance), but the job's timeline (ramps
  with h < 1/30, a different pre-roll end) differs from a 1× run by up to 0.78 m, and the P touchdown one-frame stall
  depends on the grid. Any change to a segment's speed or start changes the path: scout and plan again (the stamp chain
  enforces it: the job's segments are part of the scout key).
- **Engine motion seen in the traces** (Phase 2 owner; section 8 items 8–10; re-measured on the Phase 3b scouts,
  section 13): (1) the one-frame stand-still of case P at touchdown is gone; instead the roll slows from 1.28 to 1.03 m per
  frame for one frame 1.3 s after touchdown and then speeds up from 74.6 to 76.0 kt (frames 1227–1240; 5.6 px/frame² on
  screen in the edge shot); (2) and (3) were "lands flat" / "lifts off flat": the current engine flares case P (pitch
  0 → 5° over the last 4.8 s, nose down 1.7 s after touchdown) and rotates case S (3 → 8° over the last 2.4 s of the roll,
  9° in the climb); (4) case S stands lined up 5.4° off the runway heading (294.4° against 299.8°) and yaws onto it in
  0.23 s at 3 kt as the roll starts (frames 1691–1697; seen in the roll spot clip); (5) the roll,
  lift-off, touchdown and roll-out of both cases lie in one recorder hole each (50 s / 47 s): all of it is reconstructed
  (the overlay says so) — the Phase 2 fixer's take-off / landing reconstruction will change them; (6) the parked pivot
  with hops in the opening shot of case S (2–3 px at 72 m; the rest-jitter gate of that shot is raised with a reason;
  the Phase 3b re-plan measures 0 frames);
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
- Every PC-12 / SF50 is drawn with its detailed model (Phase 3b), but still positioned with the engine's class-rule dims
  (section 8, item 1: `traffic.js` `modelDims` open); every other type is a GA placeholder (a blocky bizjet stands next
  to the detailed SF50 in the taxi shots).
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

## 13. Phase 3b integration (2026-11-14): app hooks, detailed models in the app, re-scout and spot clips

**What changed.**

- `js/live/app.js`: the hooks of section 8 items 2-6 (`HWD.stepEngine`, `frame(wall, { engineDt, render, cut })`,
  `HWD.qa.frame`, `HWD.setPost`, `HWD.setCamera`; `docs/phase2_app.md` section 11).
- `js/live/aircraft.js`: every PC-12 / SF50 in the app is a `DetailedAircraft` with gear, flaps, propeller / fan,
  control surfaces and lights driven from the drawn motion by inferred rules (`docs/phase2_app.md` section 11 lists them);
  pitch and roll are the engine's `disp.pitch` / `disp.roll`.
- `js/video/director.js`: the monkeypatches are gone (rig, views, engine dt, renderer stubs, the `post` wrap); it pauses
  the app's own loop, preloads both models, and drives each frame through the hooks (section 2.4). The trace records the
  drawable's driven state per frame (`detailed`, `vgear`, `gearUp`, `vflaps`, `flapsTgt`, `rotor`, `running`, `ctl`,
  `lights` as N / B / S / L / T letters).
- The packs `out/video/packs/pack_v{S,P}.json.gz` were rebuilt type-only with `build_replay.py --lookahead 120`
  (decision (c); same windows, same payloads: 285 / 197 events, D1 leak check OK).
- Job S (local): `d-climb-chase` moved below the hero (back 45 m, up -3 m, side 12 m, lead 40 m, fov 36°) so the gear
  retraction is seen (section 6).

**Re-scout on the current engine** (snapshots of section 2.1; the round-4 engine fix was in progress, so this is "the
current engine" of the moment, not a final one). Events and the driven state, from the traces [obs, frames at 30 fps]:

| | Case S (SF50 take-off) | Case P (PC-12 landing) |
|---|---|---|
| events | line-up frame 1452 (48.4 s), roll start 1676 (gs > 0.5 kt), "take-off roll" label 1730, lift-off 2325 (77.5 s) at 85 kt | touchdown 1187 (39.6 s) at 81 kt, stop 2101 |
| before (round-1 snapshot, 60-s packs) | line-up 1416, roll 1549, lift-off 2401 | touchdown 1212 |
| pitch | rotation from frame 2253: 3 → 8° over the last 2.4 s of the roll, 9° in the climb (max 11°) | flare from frame 1044 (8 m up): 0 → 5° over the last 4.8 s, nose down 1.7 s after touchdown |
| gear | retraction commanded at frame 2525 (15 m up, 6.7 s after lift-off), fully up at 2704 (6.0 s later) | down throughout (frame 0 is on short final, 147 m up) |
| flaps | 15° from the line-up (set while lining up, 11°/s), up from frame 2867 (122 m = 400 ft, 23.6 s after lift-off) | 40° on final (below 500 ft), kept through the roll, up from frame 2058 as it taxis (56 s after touchdown) |
| fan / propeller | fan 100 rad/s taxiing, 120 on the roll and in the climb | propeller 178 rad/s on final and the roll, spooling to idle (110) below 30 kt |
| lights | taxi: N B T; lined up: N B S; roll and climb: N B S L | final and roll: N B S L; below 30 kt: landing light off, taxi light on (frame 1865) |
| controls | ailerons up to 0.35 of full travel in the climbing turn (bank to 27°); rudder with the nose-wheel steering on the ground | ailerons <= 0.21 on final |

**Plans** (`plan`, both cases): all gates pass. Case S: rest jitter of the opening shot 0 frames (the 6-frame override of
the job is no longer needed), c-roll-dolly lag error <= 0.61 m, hero px/frame <= 1.8 in every shot but the fast pans
listed in section 6; the low climb-out chase is never lower than 8.4 m above the ground and keeps >= 40.8 m from every
aircraft. Case P: the touchdown edge shot's largest hero acceleration is 5.6 px/frame² (was 12.3 with the one-frame
stand-still of the earlier engine; the job's override of 13 is no longer needed), dolly lag error <= 1.22 m.

**Spot clips** (section 10, "Phase 3b spot clips"): case S roll start, rotation, gear retraction; case P flare,
touchdown, roll-out. They show the engine's rotation and flare attitudes, the gear cycle (from below), the take-off and
landing flaps, the landing lights, beacon and strobes on the drawn model, and the propeller disc. Render: median 7.4 s
(S, load ~9) and 4.5 s (P, load ~6) per frame; hero vs scout 0.00000 m; 0 page errors.

**Determinism** (section 4, last row): the same 90 frames (case S taxi chase at 8×, shutter 0.5) rendered by two fresh
browser runs and by a third that drew 6 earlier frames first: 90 / 90 and 90 / 90 PNGs identical (sha256), hero vs
scout 0.00000 m in all three. The hooks, the no-draw frames, the cut flag and the app-side detailed models keep the
pipeline deterministic.

**After the snapshots** (working tree only, comments only, so the snapshots and their scouts / plans / spot clips
stand): one comment in `js/live/aircraft.js` and the director's header comment on the `models` job option.

**D1.** The packs are type-only (both heroes masked by the pack default); the hero is chosen in the page by rule; no
committed text names a case's date or time (the instants above are video frames and event offsets); the livetest
snapshots and the spot clips, which show the scene clock and the METAR day-time group, stay in `out/` (gitignored).
`python3 -I -B tools/check_airport.py`: ALL HARD CHECKS PASSED (D1 and D1(d) dated-window scans clean, after one
rewording in `docs/phase2_app.md`).

**Open / wanted** (owners elsewhere): `traffic.js` `modelDims` (section 8 item 1); the roll-start yaw of case S and the
one-frame speed dip with a 1.4-kt rise early in the case P roll (section 11); the landing-light day size; sections 8
items 7-10.

## 14. Fix round 4, iteration 2 (finding F9): the snapshots on the final engine (2026-11-14)

**Finding.** The Phase 3b snapshots of section 13 (S tree 73209bc0db88, P df19cf8c2cd0) froze the traffic engine in the
middle of fix round 4, so their scouts, plans and spot clips did not show the engine that round 4 ended with, let alone
this iteration's.

**What changed.** `node tools/video/render.mjs <job> snapshot --refresh=engine` replaces the traffic engine
(`tools/video/lib.mjs` `ENGINE_FILES`: `js/live/{traffic,motion,ground,classifier,parking,feed,lookup}.js`) and the
pipeline (`js/video/**`) from the working tree and keeps everything else of the snapshot frozen - renderer, shaders,
models, data and the app shell - because another workflow (OD4) is editing the renderer and model runtime while this
iteration runs. The manifest records the refresh (`refreshed`, `base` chain), and the stamp chain makes scout and plan
mandatory again. (`--refresh=video` remains: the pipeline only.)

**Snapshots now** (the engine was refreshed three times during the iteration as it changed; only the last is current,
and every number below is from it): S tree **f9f6642666d0**, P tree **be6a2b90f71b**, both holding `traffic.js` sha256
5fd978f57963… - the final engine of `docs/phase2_run.md` section 11 - over the frozen Phase 3b renderer, shaders, models
(pc12.glb 87731cce…, sf50.glb 49242e41…) and data. The OD4 look fixes made since the Phase 3b snapshot are therefore NOT
in these snapshots; a full render that should show them needs a full new snapshot (`--refresh`), then scout and plan.

**Re-scout** (events from the traces; video frames at 30 fps):

| | Case S (SF50 take-off) | Case P (PC-12 landing) |
|---|---|---|
| events now | line-up (label) frame 1523 (50.8 s) at 7.8 kt, roll start 1690 (56.3 s), lift-off 2362 (78.7 s) at 84.9 kt | touchdown 1187 (39.6 s) at 80.8 kt, stop 2101 |
| section 13 (mid-round-4 engine) | line-up 1452, roll start 1676, lift-off 2325 at 85 kt | touchdown 1187 at 81 kt, stop 2101 |
| line-up / roll-out | taxi onto 28L at a constant 7.7-7.8 kt, nose 290.8 → 299.9° monotonically in ~2 s while it joins the centreline, 'Lined up 28L' from frame 1530, 7.8 → 6.8 kt into the rolling start, then the roll | no speed rise in the roll; the observed roll-out runs ~0.9 m off the fix-following target and is pulled onto it near frame 1603 (below) |
| hero not drawn | 0 frames | 0 frames |

**Plans and gates** (`plan`): all gates pass in both cases. Case S: rest jitter 0 frames in every shot, including
`a-establish` (the job's `restJitter: 6` override, written for the parked SF50's pivots of the round-1 engine, is no longer
needed and was removed) and `lineup-chase` (hero ≤ 0.60 px/frame, ≤ 0.03 px/frame², rest jitter 0); c-roll-dolly lag
error ≤ 0.62 m. Case P: `e-touchdown-edge` now ≤ 0.47 px/frame² (its `heroAcc: 13` override for the old one-frame
stand-still at touchdown was removed); `c-roll-dolly` measures 2.52 px/frame² at frame 1603 (limit 1.5), where the
observed roll-out body (51 kt) is pulled 0.9 m onto its fix-following target (braking 3 → 1.4 m/s² within 0.2 s): the job
now carries `heroAcc: 3` for that shot with this reason (an engine residual, open). The job files stay local
(`out/od3/video_{S,P}.json`, gitignored).

**Determinism** (`determinism --frames=1683-1697`, case S at the roll start, shutter 0.5): 15 / 15 PNGs identical
(sha256) between two fresh browser runs, and 15 / 15 identical in a third run that drew 6 earlier frames first.

**Spot stills** (`render --pick=…`, 1920 × 1080, looked at; local in `out/video/{S,P}/picks_r4i2/`, they show the scene
clock and the METAR day-time group): case S frames 1450 (taxi turn toward 28L, 4× time-lapse), 1530 (lined up, the
nose still closing the last degrees onto the runway heading), 1690 (roll start on the centreline), 2300 (late roll,
landing lights on, edge shot) and 2362 (lift-off, nose up, 'Climbing out'); case P frames 1067 (short final, landing
lights), 1150 (flare), 1187 (touchdown), 1250 (landing roll) and 1603 (roll-out dolly, 'Recorded ADS-B position'). Hero vs
scout 0.00000 m, 0 page errors; 4.5 s (S) and 9.4 s (P, load ~9.5) median per frame.

**Not done here.** No clip was encoded (the spot clips of section 13 stand for the mid-round engine only); the full
videos are still the orchestrator's (section 11).
