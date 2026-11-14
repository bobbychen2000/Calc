# Hayward Live 3D (KHWD) — project notes for Claude Code

A real-time, interactive 3-D view of **Hayward Executive Airport (KHWD)** driven by live ADS-B traffic. It is the
sibling of `sfo3d/` (SFO Live 3D) and was **forked from sfo3d @ commit a967f9b**. Same stack: plain ES modules + a
custom WebGL2 renderer (no framework, no bundler), offline Python data tools, and a Python-stdlib relay. The repo is
public; Pilatus-style private reference material is not an issue here, but **ADS-B-derived per-aircraft identity is never
committed** (see D1 below).

This file is the project's top-level guide. Phase history, decisions and the data provenance are in `docs/`:
`PLAN.md` (facts, inventory, risks, working defaults D1–D6, phases), `docs/phase2_fork_map.md` (the contract between the
four Phase 2 packages), `docs/phase2_{relay,world,traffic,app}.md` (each package's write-up), `docs/ATTRIBUTION.md`
(every data source, its licence and the notice it needs) and `docs/phase1_data_report.md`.

**Never modify `sfo3d/` or `pc12/`** (read them freely). Wishes for sfo3d go to `docs/requests_to_sfo3d.md`.

## Objective (owner's definition of done, inherited from sfo3d and adapted for a GA field)

A physically plausible, phone-first simulation laid on top of real data. For HWD, the general-aviation realities drive
the design: small aircraft (8–15 m) at 1–1.5 m position error, tie-downs and hangars instead of jet bridges, a
pattern-work classifier (touch-and-go, low approach, run-up, hover-taxi), a tower that closes at night (CTAF 120.2),
and a recorder that saw only ~14 s of every minute, so motion is interpolated between real fixes across ~46 s holes.

## Owner's rules (non-negotiable)

- **Never make unverified key assumptions.** Verify coordinates, dimensions, frequencies, licences and API terms against
  the original source, or mark them inferred. Keep **observed (`obs`) vs inferred (`inf`)** visible in the data and in
  the UI (an "inf" marker on the card and the list).
- **D1 (privacy).** An aircraft flagged **LADD** (`dbFlags & 8`) or **PIA** (`dbFlags & 4`) is shown by **type only** —
  no registration, callsign, operator or address, anywhere in the UI. **No committed file holds a per-aircraft identity
  derived from ADS-B.** The replay/snapshot pack is generated into `out/` (gitignored) by a committed script and is
  never committed; a pack meant for a published artifact defaults to **type-only** for every aircraft.
- **No Google imagery, ever.** The ground texture is USDA NAIP (public domain).
- **Physical plausibility everywhere**: aircraft are solid bodies, on pavement when on the ground, never clipping, with
  real spacing.
- **One quality level: the full-feature, highest-resolution, complex-shading version** (owner decision OD1,
  2026-11-13). No phone "lite" version and no `quality=low` path; the owner checks performance on a laptop. The
  published artifact must still open and be usable on an iPhone (layout + touch, OD2), without phone performance work.
  See `docs/PLAN.md` §6b.

## Coordinates & conventions

- **World frame** `ltp-nad83-2011-hwd` (`js/geo.js`): **x = east, z = south, y = up, metres.** The origin is the NASR
  ARP. **y is the NAVD 88 height**, not a constant ground: runway surfaces run 8.44 m (10R) to 15.88 m (28L). Anything
  on the ground uses **`site.groundY(x, z)`** (P2's `js/world/site.js`), never a constant `GROUND_Y`.
- **Headings at package boundaries are degrees true**, `[0, 360)`. `geo.js hdgVec(deg) = [sin, −cos]`. Inside a module,
  radians are fine (sfo3d's `traffic.js hdgVec` took radians — never mix the two in one file).
- glTF / three convention is not used (hwd3d forks only the WebGL2 `live.html` path, not three.js `live3.html`).
- Times are **epoch milliseconds**; the relay's `_pt` is epoch **seconds**. `displayTime(now) = now − delay`.
- **Track keys** are internal handles (lower-case hex, `~…` anon, `x`+8 hex for a D1-masked aircraft). **No UI text,
  label, URL or log line may contain a key** — the UI uses opaque per-page ids (`window.HWD.qa.idOf`).
- Names: `window.HWD`, `window.__hwdReady` / `__hwdError`, localStorage prefix `hwdlive.`, mode override `HWD_MODE`.

## Run

```bash
pip install playwright   # the harness only; the app and relay need no installs
# the app, served by the relay (adsb.lol inside its 500/day quota, + adsb.fi live only):
python3 hwd_live_server.py                 # http://localhost:8000/  -> live.html (live mode)
python3 hwd_live_server.py --host 0.0.0.0  # open it from a phone on the same Wi-Fi
# a recorded hour, re-timed to wall clock, through the same merge path:
python3 hwd_live_server.py --replay rec_pack --from 2026-11-08T20:00Z --loop
# relay-less (plain static server): the app falls back to the in-page replay pack (out/replay/, P1's shim).
# Bind it to this machine only: http.server has no deny rules and binds every interface by default, so refs/cache/local/
# (identity working files) and out/ (full-ident screenshots / packs) would be served to the LAN.
python3 -m http.server 8000 --bind 127.0.0.1   # http://localhost:8000/live.html?mode=replay

# the replay / snapshot pack (generated, gitignored; type-only by default):
python3 tools/live/build_replay.py         # -> out/replay/pack.json.gz + replay_shim.js (P1)

# harness: static server + relay in replay mode (spawned) OR the in-page shim, headless Chromium, named views
node livetest.mjs jobs/views.mjs                        # desktop 1280x720, RELAY=none uses the shim, RELAY=spawn the relay
MOBILE=1 PREFIX=phone node livetest.mjs jobs/views.mjs  # phone 390x844 @ DPR 1
RELAY=spawn WAIT=80000 node livetest.mjs jobs/relaycheck.mjs   # end-to-end against hwd_live_server.py --replay
#   -> out/phase2/app_*.png ; out/phase2/app_console_<prefix>_<dev>.json (console errors). LOOK at every image.
```

### URL parameters
`?mode=live|replay|snapshot` (default live; falls back to replay when no relay answers) · `?pack=<same-origin path to a .json[.gz]>` ·
`?at=<ISO | minutes>` (snapshot instant) · `?t=<ISO UTC>` / `?metar=<raw>` (QA time machine) ·
`?fixedres=1` (pin the render scale for stills) · `?qa=env` (EnvState HUD).

## Architecture

Four Phase 2 packages, each owning its files and reaching the others only through the contracts in
`docs/phase2_fork_map.md` §2:

- **P1 — relay, replay, taxigraph.** `hwd_live_server.py` (adsb.lol budgeted poll + adsb.fi live, the sfo3d Hub merge,
  Mictronics `_mx` enrichment, **D1 masking as the last step**, `/api/{ping,adsb,stream,metar,ident,status}`),
  `tools/live/**` (pack builder + `replay_shim.js`), `data/hwd_taxigraph.{json,js}`.
- **P2 — world & renderer.** `js/{gl,renderer,scene,math,geom}.js`, `js/shaders/**`, `js/world/{site,grid,…}.js`,
  `js/live/{world,airport,markings,buildings,lights}.js`, `js/env/**` (sun / METAR / night, `render_env.js`).
  `buildSite(airport)` and `buildHwdWorld(R, airport, {site, quality, taxigraph})` are the entry points.
- **P3 — traffic.** `js/live/{traffic,classifier,parking,ground,feed,lookup,aircraft}.js`, `js/aircraft/**`.
  `new Traffic({airport, taxigraph, site, parking})`, `GroundPhysics`, `PhaseClassifier`, `ParkingModel`,
  `AircraftViews` (GA placeholder drawables), `identity()` with D1.
- **P4 — app shell, UI, harness (this package).** `live.html`, `live.css`, `js/live/{entry,app,ui,controls,about,atc,
  stats}.js`, `livetest.mjs`, `jobs/**`, `package.json`, this file and `docs/phase2_app.md`.

**App boot** (`entry.js` → `app.js startApp`): pick the mode and detect the relay (`api/ping` → `{hwdlive:1}`) →
`buildSite` → `buildHwdWorld` → `Scene` → `AppEnv` + `applyEnvToRenderer` → `ParkingModel` → `Traffic` →
`GroundPhysics` → `AircraftViews` → `CameraRig` → feed (`StreamFeed`, or the in-page shim in replay, or the pack's own
events in snapshot). **Per frame**: `traffic.update` → `physics.resolve` → `views.sync` → `rig.update` → (30 s)
environment → `scene.frame` → `R.render` → `scene.commit` → `R.present` → DOM labels → list / status.

**UI** (phone-first): a top bar (brand, feed-status pill, ATC pill with the tower state, clock), five view buttons
(Overview, Tower, Green Ramp, West Hangars, 28L Final), a flight panel that is a side panel on desktops and a peek/open
bottom sheet on phones (Air / Ground / Heli / Over / All tabs, a phase-count line, a runway-movements line, search), a
detail card (registration / type / model / operator / phase / parking spot / runway / tower — withheld for masked
aircraft), follow / chase / free camera, and About / statistics / ATC bottom sheets. `window.HWD.qa` drives the harness.

## Status / next steps

- **Phase 2 is in review** (not yet accepted): P1–P4 built a working app on recorded (shim / relay) and live data,
  phone-first UI, D1 throughout, the ATC link-out (D2), the About panel with every ATTRIBUTION notice. Review fix round 1
  (`docs/phase2_run.md` section 6) reworked the motion engine (`js/live/motion.js`: drivable ground profiles, a geometric
  air-hole curve; take-off / landing plans from the fix's own speed; no ghost parking) and the relay's D1 / serving rules.
  Review fix round 2 (`docs/phase2_run.md` section 7) counts a teleport across an absence of any length and gates it
  at 0, keeps silent ground aircraft drawn at their last position ("No signal", [inf]), replaces the straight air-ground
  chord with turn-limited aligned paths, and sends late-flag forgets to polling clients. The relay's `--record` guard is
  now case-sensitive and checked with git. Phone controls are ≥ 44 px (`jobs/phone_ui.mjs`).
  Review fix round 3 (`docs/phase2_traffic.md` §4 / §7) reconstructs take-offs and landings across recorder holes on
  the runway (type performance, touchdown zone), never leaves a silent aircraft on a runway, keeps landing rolls on
  their runway and routes around parked aircraft. Its recheck (round 3 iteration 2, `docs/phase2_run.md` section 8)
  replaced the late join (take-offs drawn kilometres and minutes behind their reports) by a take-off timed backwards
  from the first airborne fix - or, when none fits, the owner's M3 rule: hidden until that fix, shown there at its
  reported height - keeps runway passes below ~100 ft on the centreline, stops drawing TIS-B echoes beside their
  aircraft, makes the phase labels and the altitude label follow the drawn motion / height, and wires the relay's
  forget horizon (`app.js` onHorizon, `jobs/horizon.mjs`).
  Its second recheck (round 3 iteration 3, `docs/phase2_run.md` section 9) makes the strict harness ingest the opening
  burst as the app does (`--open app`), never flies a reconstructed approach below the type's flying speed (landings
  time-split against an air-speed floor, a roll-out with a U-turn when the next fix back-taxis, unseen touch-and-gos
  across air holes, silent finals continued to an exit), labels the drawn state (no runway label in the air, vertical
  sense, base → final, 'Stopped', debounced roll labels), keeps wings off hangar footprints on taxi routes, treats fast
  ground fixes beside the runway as airborne and gives the card's height above the ground / runway below 300 ft.
  `node tools/traffic/replay_engine.mjs <w> --strict` (windows heli, pat, night, weekday, weekend and the local OD3
  windows od3s / od3p) fails on any teleport, ghost parking, slow lift-offs, hard stops, hops, hovering, helicopters in
  buildings, label contradictions, route samples on grass, misaligned or off-runway lift-offs / touchdowns, silent
  aircraft on runways, a drawn body > 150 m from its reports, low flight off the runways, close air pairs, air
  overspeed / over-climb, fixed-wing planforms in buildings, sub-stall reconstructions, floats over a runway and the
  iteration-3 label gates. It still FAILS on residuals (section 9.4): grass-route samples (1-33 per window), wings over
  footprints (2-57 frames), 1-5 air-overspeed and 3-124 over-climb samples, 6 overlap frames (pat), 3 ghost-parked
  frames (od3s), 1-2 touch-and-go events drawn without contact, 8 sub-stall / 9 float samples (weekend), 1 roll-label
  flicker (weekday) and 3 M3 hidden take-offs whose runway is consistent - an owner decision (hidden fallback for
  time-infeasible take-offs, or replay packs with a 120-s lookahead). See `docs/phase2_app.md` for the integration notes.
- **Phase 3 — aircraft** (`docs/PLAN.md` §7): real GA models (C172, PA-28, SR22, C182, the PC-12 from `pc12/`, a bizjet
  set, three helicopters) with N-number decals, replacing the placeholders. Verify each model's licence.
- **Phase 4 — airport fidelity**: hangar doors, FBO buildings, the fuel island, signs and light fixtures (positions not
  yet sourced), tie-down chains, GSE.
- **Open owner decisions** (do not resolve without the owner): whether a published artifact may carry full identity for
  aircraft not flagged LADD/PIA (default type-only); LiveATC terms (Q2); the east-flow recording gap (every recorded
  hour is west flow); whether a take-off whose runway is consistent but that cannot be timed may stay hidden until its
  first airborne fix (M3), or replay / snapshot packs move to a 120-s lookahead (`docs/phase2_run.md` 9.4).
